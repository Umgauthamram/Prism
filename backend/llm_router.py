import time
import json
import httpx
import asyncio
from typing import Optional, Dict, List, Any

# Supported Providers and Models
PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"]
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "models": ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash", "gemini-1.5-pro"]
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o-mini", "gpt-4o"]
    }
}

# Global in-memory state
_episode_configs: Dict[str, Dict[str, str]] = {} # eid -> {provider, model}
_api_keys: Dict[str, str] = {}
_model_results: Dict[str, List[Dict[str, Any]]] = {}

def set_model_config(provider: str, model: str, api_key: str, episode_id: Optional[str] = None) -> dict:
    if provider not in PROVIDERS:
        return {"success": False, "message": "Unsupported provider"}
    if model not in PROVIDERS[provider]["models"]:
        return {"success": False, "message": f"Model {model} not supported for {provider}"}
    
    _api_keys[provider] = api_key
    
    if episode_id:
        _episode_configs[episode_id] = {"provider": provider, "model": model}
    
    key = f"{provider}/{model}"
    if key not in _model_results:
        _model_results[key] = []
        
    return {"success": True, "provider": provider, "model": model}

def get_model_config(episode_id: Optional[str] = None) -> dict:
    config = _episode_configs.get(episode_id, {}) if episode_id else {}
    return {
        "active_provider": config.get("provider"),
        "active_model": config.get("model"),
        "providers": {p: {"configured": p in _api_keys} for p in PROVIDERS}
    }

def get_available_providers() -> dict:
    return PROVIDERS

async def test_connection(provider: str, model: str, api_key: str) -> dict:
    start_time = time.time()
    try:
        async with httpx.AsyncClient() as client:
            if provider == "gemini":
                url = f"{PROVIDERS[provider]['base_url']}/models/{model}:generateContent?key={api_key}"
                payload = {"contents": [{"parts": [{"text": "Reply with the single word OK"}]}]}
                resp = await client.post(url, json=payload, timeout=10.0)
            else:
                # Groq and OpenAI use the same chat completions format
                url = f"{PROVIDERS[provider]['base_url']}/chat/completions"
                headers = {"Authorization": f"Bearer {api_key}"}
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": "Reply with the single word OK"}],
                    "max_tokens": 10
                }
                resp = await client.post(url, json=payload, headers=headers, timeout=10.0)
            
            latency = int((time.time() - start_time) * 1000)
            if resp.status_code == 200:
                return {"success": True, "response": "OK", "latency_ms": latency}
            else:
                return {"success": False, "response": f"Error {resp.status_code}: {resp.text}", "latency_ms": latency}
    except Exception as e:
        return {"success": False, "response": str(e), "latency_ms": int((time.time() - start_time) * 1000)}

async def call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 256, episode_id: Optional[str] = None) -> str:
    config = _episode_configs.get(episode_id)
    if not config:
        return "LLM_ERROR: No model configured for this episode"
    
    provider = config["provider"]
    model = config["model"]
    api_key = _api_keys.get(provider)
    if not api_key:
        return "LLM_ERROR: No API key for active provider"
    
    try:
        async with httpx.AsyncClient() as client:
            if provider == "gemini":
                url = f"{PROVIDERS[provider]['base_url']}/models/{model}:generateContent?key={api_key}"
                full_prompt = f"{system_prompt}\n\nUser Input: {user_prompt}"
                payload = {"contents": [{"parts": [{"text": full_prompt}]}]}
                resp = await client.post(url, json=payload, timeout=30.0)
                if resp.status_code != 200:
                    return f"LLM_ERROR: {resp.status_code} - {resp.text}"
                data = resp.json()
                try:
                    return data['candidates'][0]['content']['parts'][0]['text']
                except (KeyError, IndexError) as e:
                    return f"LLM_ERROR: Unexpected response format: {str(e)}"
            else:
                url = f"{PROVIDERS[provider]['base_url']}/chat/completions"
                headers = {"Authorization": f"Bearer {api_key}"}
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "max_tokens": max_tokens
                }
                resp = await client.post(url, json=payload, headers=headers, timeout=30.0)
                if resp.status_code != 200:
                    return f"LLM_ERROR: {resp.status_code} - {resp.text}"
                data = resp.json()
                return data['choices'][0]['message']['content']
    except Exception as e:
        return f"LLM_ERROR: {str(e)}"

async def generate_agent_action(observation: dict, role: str, allowed_tools: dict) -> dict:
    task_graph = observation.get('task_graph', {})
    pending_tasks = [k for k, v in task_graph.items() if v["status"] == "pending"]
    
    system_prompt = f"""You are a {role} agent in a Prism RL environment.
OBJECTIVE: Complete all tasks in the Task Graph as efficiently as possible.

AVAILABLE TOOLS: {json.dumps(allowed_tools, indent=2)}

CRITICAL GUIDELINES:
1. DEPENDENCIES: You cannot finish a task until its dependencies are met. Look at the 'Task Graph' carefully.
2. PROGRESSION: To mark a task as DONE, you MUST use a logic tool (like 'replan', 'assign', 'decompose') and include "task_done": "task_id" in your arguments.
3. TECHNICAL: If your role is Coder, you must 'write_code' then 'run_tests'. 'run_tests' marks itself done if successful.
4. COMPLETION: You MUST complete ALL PENDING TASKS before using the 'finish' tool. Using 'finish' with pending tasks will result in a heavy penalty.
5. FORMAT: Respond ONLY with valid JSON: {{"tool": "...", "args": {{...}}}}

Current Domain: {observation.get('task_domain', 'unknown')}
Pending Tasks: {", ".join(pending_tasks) if pending_tasks else "NONE - USE FINISH TOOL NOW"}"""

    user_prompt = f"""STATE UPDATE:
- Task Graph Status: {json.dumps(task_graph, indent=2)}
- World Model (Shared State): {json.dumps(observation.get('world_model', {}), indent=2)}
- Result of Last Action: {json.dumps(observation.get('last_tool_output', {}), indent=2)}

What is the best next action for the {role} to maximize total reward and complete the next pending task?"""

    start_time = time.time()
    response_text = await call_llm(system_prompt, user_prompt, episode_id=observation.get("episode_id"))
    latency = int((time.time() - start_time) * 1000)
    
    config = _episode_configs.get(observation.get("episode_id"), {})

    try:
        # Simple extraction if LLM adds markdown backticks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        action = json.loads(response_text)
    except:
        # Fallback per role
        fallbacks = {
            "Planner": {"tool": "checkpoint", "args": {}},
            "Researcher": {"tool": "research_web", "args": {"q": "task context"}},
            "Coder": {"tool": "run_tests", "args": {}},
            "Critic": {"tool": "critique", "args": {}},
            "Synthesizer": {"tool": "finish", "args": {}}
        }
        action = fallbacks.get(role, {"tool": "checkpoint", "args": {}})

    return {
        "tool": action.get("tool"),
        "args": action.get("args", {}),
        "model_used": config.get("model"),
        "provider_used": config.get("provider"),
        "latency_ms": latency
    }

def record_model_result(episode_id: str, step: int, total_reward: float, breakdown: dict):
    config = _episode_configs.get(episode_id)
    if not config:
        return
    
    key = f"{config['provider']}/{config['model']}"
    if key not in _model_results:
        _model_results[key] = []
        
    _model_results[key].append({
        "step": step,
        "total": total_reward,
        "breakdown": breakdown
    })

def get_model_comparison() -> dict:
    return {"models": _model_results}
