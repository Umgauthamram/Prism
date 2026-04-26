import time
import json
import httpx
import asyncio
import os
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
_api_keys: Dict[str, str] = {
    "groq": os.getenv("GROQ_API_KEY", ""),
    "gemini": os.getenv("GOOGLE_API_KEY", ""),
    "openai": os.getenv("OPENAI_API_KEY", "")
}
_model_results: Dict[str, List[Dict[str, Any]]] = {}

# ICL injection state: episode_id -> prompt injection text
_icl_injections: Dict[str, str] = {}

def set_icl_injection(episode_id: str, injection: str) -> None:
    """Store an ICL prompt injection for a specific episode."""
    _icl_injections[episode_id] = injection

def get_icl_injection(episode_id: str) -> str:
    """Retrieve the ICL prompt injection for a specific episode."""
    return _icl_injections.get(episode_id, "")

def set_model_config(provider: str, model: str, api_key: str, episode_id: Optional[str] = None) -> dict:
    if provider not in PROVIDERS:
        return {"success": False, "message": "Unsupported provider"}
    if model not in PROVIDERS[provider]["models"]:
        return {"success": False, "message": f"Model {model} not supported for {provider}"}
    
    if api_key and api_key != "SAVED":
        _api_keys[provider] = api_key
    
    key = f"{provider}/{model}"
    if episode_id:
        _episode_configs[episode_id] = {"provider": provider, "model": model}
        # Clear previous data for this model since a new tournament run is starting
        _model_results[key] = []
    elif key not in _model_results:
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
    
    role_warning = ""
    if role == "Synthesizer" and pending_tasks:
        role_warning = "\n⚠️ WARNING: You are the Synthesizer. DO NOT use the 'finish' tool yet. There are still pending tasks. Use 'merge' or 'flag_gap' instead to keep the episode alive."

    # Get ICL injection for this episode if any
    icl_text = get_icl_injection(observation.get("episode_id", ""))

    system_prompt = f"""{icl_text}You are a high-performance {role} agent in the Prism RL Environment.
OBJECTIVE: You must successfully complete EVERY task in the Task Graph. {role_warning}

TASK GRAPH RULES:
1. SEQUENTIAL PROGRESS: Look at the 'Task Graph' below. You MUST complete tasks in order of their dependencies.
2. COMPLETION PROTOCOL: To finish a task, you must use a tool that either explicitly marks it done (like 'run_tests') or use a logic tool (like 'replan', 'assign', 'decompose') and include "task_done": "task_id" in the 'args' dictionary.
3. ROLE BOUNDARIES: You are currently the {role}. Only use tools allowed for your role. If you need to switch, the environment will rotate your role in the next step.
4. NO PREMATURE EXIT: Do NOT use the 'finish' tool until ALL tasks in the graph have a status of "done". Using 'finish' early is a CRITICAL FAILURE and results in zero terminal bonus.
5. STRATEGY: If a task is 'pending' and its dependencies are 'done', that is your target. If you are a Coder, use 'write_code' then 'run_tests'. If you are a Planner, use 'assign' or 'checkpoint'.

AVAILABLE TOOLS FOR {role.upper()}:
{json.dumps(allowed_tools, indent=2)}

FORMAT: You must respond ONLY with a single JSON object: {{"tool": "...", "args": {{...}}}}

CURRENT STATE:
- Domain: {observation.get('task_domain', 'unknown')}
- Pending Tasks: {", ".join(pending_tasks) if pending_tasks else "NONE - ALL TASKS COMPLETE. USE 'finish' TOOL NOW."}"""

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
        if not isinstance(action, dict):
            raise ValueError("Parsed action is not a dictionary")
    except:
        # Fallback per role
        fallbacks = {
            "Planner": {"tool": "checkpoint", "args": {}},
            "Researcher": {"tool": "research_web", "args": {"q": "task context"}},
            "Coder": {"tool": "run_tests", "args": {}},
            "Critic": {"tool": "critique", "args": {}},
            "Synthesizer": {"tool": "finish", "args": {"answer": "Task complete fallback"}}
        }
        action = fallbacks.get(role, {"tool": "checkpoint", "args": {}})

    config = _episode_configs.get(observation.get("episode_id"), {})
    model_used = config.get("model", "unknown")
    provider_used = config.get("provider", "unknown")

    # Removed premature record_model_result call. 
    # environment.py already records the true result at the end of the step.
    
    return {
        "tool": action.get("tool"),
        "args": action.get("args", {}),
        "model_used": model_used,
        "provider_used": provider_used,
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
