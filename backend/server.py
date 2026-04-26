from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
import time
import csv
import os
import wandb
import json
from dotenv import load_dotenv

load_dotenv() # Load API keys from .env

from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from openenv.core import HTTPEnvServer

from .environment import PrismEnv
from . import llm_router, state
from .icl_trainer import build_icl_prompt_injection, get_improvement_plan
from envs.prism import PrismAction, PrismObservation

console = Console()

class PrismServer(HTTPEnvServer):
    def __init__(self):
        super().__init__(
            env=lambda: PrismEnv(),
            action_cls=PrismAction,
            observation_cls=PrismObservation
        )

app = FastAPI(title="Prism RL Environment")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Environment Registry for Multi-Episode Support
ENVS: Dict[str, PrismEnv] = {}

# ICL Training History: "{provider}/{model}/{domain}" -> history
_icl_history: Dict[str, dict] = {}

# Latest diagnostic feedback per episode for dashboard display
_latest_feedback: Dict[str, dict] = {}

# Track processed episode IDs to avoid double-counting in ICL history
_processed_icl_episodes: set = set()

@app.post("/reset")
async def reset_episode(seed: int = 42, options: dict = Body(None)):
    # Use seed from body if provided, otherwise use query param
    final_seed = options.get("seed", seed) if options else seed
    
    # Safety check for task_domain to prevent Pydantic validation crashes
    if options and "task_domain" in options:
        valid_domains = ["debug", "market_research", "etl"]
        if options["task_domain"] not in valid_domains:
            options["task_domain"] = "debug"

    eid = str(uuid.uuid4())
    env = PrismEnv()
    env.episode_id = eid
    obs = env.reset(seed=final_seed, options=options)
    # Ensure eid is set in the observation
    obs.episode_id = eid
    ENVS[eid] = env
    return {"observation": obs.model_dump(), "reward": 0.0, "done": False, "info": {}}

@app.post("/step")
async def step_episode(payload: dict = Body(...)):
    eid = payload.get("episode_id")
    action_data = payload.get("action")
    
    # Robust episode lookup
    env = None
    if eid and eid in ENVS:
        env = ENVS[eid]
    elif ENVS:
        # Fallback to the most recently active environment
        eid = list(ENVS.keys())[-1]
        env = ENVS[eid]
    else:
        # Create a default environment if none exist
        eid = "default"
        env = PrismEnv()
        env.reset()
        ENVS[eid] = env
            
    obs = await env.step_async(action_data)
    
    # Track ICL history when episode terminates
    if obs.done and eid not in _processed_icl_episodes:
        active_config = llm_router.get_model_config(eid)
        if active_config.get("active_provider") and active_config.get("active_model"):
            _processed_icl_episodes.add(eid)
            model_key = f"{active_config['active_provider']}/{active_config['active_model']}/{env.task_domain}"
            if model_key not in _icl_history:
                _icl_history[model_key] = {
                    "diagnostic_history": [],
                    "breakdown_history": [],
                    "prev_score": 0.0,
                    "improvement_plan": "",
                    "icl_injection": "",
                    "run_count": 0,
                }
            entry = _icl_history[model_key]
            # Collect breakdowns from state's episode curves
            episode_breakdowns = []
            if eid and eid in state._episode_curves:
                episode_breakdowns = [
                    r["breakdown"] for r in state._episode_curves[eid]
                ]
            last_diagnostic = obs.info.get("feedback", "")
            entry["diagnostic_history"].append(last_diagnostic)
            
            # FIX: Do not extend. Overwrite with the latest episode's breakdowns 
            # so old failures don't drag down the average in the next analysis.
            entry["breakdown_history"] = episode_breakdowns[-15:]
            
            entry["prev_score"] = obs.reward
            entry["run_count"] += 1
            # Keep history capped at 3 episodes
            entry["diagnostic_history"] = entry["diagnostic_history"][-3:]
            entry["breakdown_history"] = entry["breakdown_history"][-15:]
            
            # Save ICL history locally
            try:
                os.makedirs("history", exist_ok=True)
                
                # PHASE A / E — Terminal Summary
                score = obs.reward
                is_trained = bool(llm_router.get_icl_injection(eid))
                
                panel_title = "EPISODE COMPLETE — [green]TRAINED[/green]" if is_trained else "EPISODE COMPLETE — [yellow]BASELINE[/yellow]"
                panel_color = "green" if is_trained else "yellow"
                
                summary_text = (
                    f"Model: [bold]{active_config['active_model']}[/bold]\n"
                    f"Domain: {env.task_domain}  |  Steps: {env.step_count}\n"
                    f"Final Reward: [bold]{score:.4f}[/bold]\n"
                    f"Feedback: [dim]{last_diagnostic}[/dim]"
                )
                
                if is_trained:
                    prev_score = entry.get("score_history", [0])[0] if entry.get("score_history") else entry.get("prev_score", 0)
                    if prev_score > 0:
                        improvement = ((score - prev_score) / prev_score) * 100
                        summary_text += f"\n[bold green]Improvement: {improvement:+.1f}%[/bold green]"

                console.print(Panel(summary_text, title=panel_title, border_style=panel_color))
                
                entry["score_history"] = entry.get("score_history", [])
                entry["score_history"].append(score)
                entry["score_history"] = entry["score_history"][-5:]
                
                # PERSIST TO ARCHIVE (For Evaluation Archive)
                archive_data = {
                    "model": active_config["active_model"],
                    "provider": active_config["active_provider"],
                    "domain": env.task_domain,
                    "final_reward": score,
                    "steps": env.step_count,
                    "terminated": True,
                    "icl_active": is_trained,
                    "breakdown": breakdown,
                    "timestamp": time.time()
                }
                with open(f"history/{eid}.json", "w") as af:
                    json.dump(archive_data, af, indent=2)
                
                # Update ICL History Index
                with open("history/icl_history.json", "w") as f:
                    json.dump(_icl_history, f, indent=2)
            except Exception as e:
                console.print(f"[dim yellow]! Failed to save ICL history: {e}[/dim yellow]")
    
    # Store latest feedback for dashboard display
    feedback_text = obs.info.get("feedback", "")
    breakdown = obs.info.get("reward_breakdown", {})
    if eid:
        _latest_feedback[eid] = {
            "feedback": feedback_text,
            "reward": obs.reward,
            "step": env.step_count,
            "done": obs.done,
            "breakdown": breakdown,
        }
    
    return {
        "observation": obs.model_dump(),
        "reward": obs.reward,
        "done": obs.done,
        "info": obs.info
    }

@app.get("/state")
def get_current_state(episode_id: Optional[str] = None):
    # Handle both query param and empty string/null
    eid = episode_id if episode_id else None
    
    if not eid and ENVS:
        eid = list(ENVS.keys())[-1]
    
    if eid and eid in ENVS:
        env_state = ENVS[eid].state
        # Attach latest diagnostic feedback
        fb = _latest_feedback.get(eid, {})
        env_state["feedback"] = fb.get("feedback", "")
        env_state["last_reward"] = fb.get("reward", 0.0)
        return env_state
    
    # Return a blank state instead of 404 to keep dashboard happy
    return {
        "task_graph": {},
        "world_model": {},
        "last_tool_output": {},
        "agent_role": "Planner",
        "step": 0,
        "terminated": False,
        "feedback": "",
        "last_reward": 0.0
    }

# Model Management Endpoints
@app.get("/models/config")
def get_models_config(episode_id: Optional[str] = None):
    return llm_router.get_model_config(episode_id)

@app.post("/models/config")
def set_models_config(payload: dict = Body(...)):
    return llm_router.set_model_config(
        payload.get("provider"),
        payload.get("model"),
        payload.get("api_key"),
        payload.get("episode_id")
    )

@app.get("/models/available")
def get_available():
    return llm_router.get_available_providers()

@app.post("/models/test")
async def test_model_connection(payload: dict = Body(...)):
    return await llm_router.test_connection(
        payload.get("provider"),
        payload.get("model"),
        payload.get("api_key")
    )

@app.get("/models/comparison")
def get_comparison():
    return llm_router.get_model_comparison()

# Initialize PrismServer (keep it for other endpoints)
prism_server = PrismServer()
prism_server.register_routes(app)

# Ensure history directory exists
os.makedirs("history", exist_ok=True)

@app.on_event("startup")
async def startup_event():
    # Initialize a global W&B run for the tournament/evaluation
    try:
        if os.getenv("WANDB_API_KEY"):
            wandb.init(
                project=os.getenv("WANDB_PROJECT", "prism-eval"),
                entity=os.getenv("WANDB_ENTITY"),
                name=f"tournament-{time.strftime('%m%d-%H%M')}",
                job_type="evaluation",
                mode="online" if os.getenv("WANDB_API_KEY") else "disabled"
            )
    except Exception as e:
        console.print(f"[yellow]! W&B Initialization failed: {e}[/yellow]")
        
    # Load ICL history if exists
    global _icl_history
    if os.path.exists("history/icl_history.json"):
        try:
            with open("history/icl_history.json", "r") as f:
                _icl_history.update(json.load(f))
            console.print(f"[green]✓ Loaded ICL history ({len(_icl_history)} models)[/green]")
        except Exception as e:
            console.print(f"[dim yellow]! Failed to load ICL history: {e}[/dim yellow]")

    # Rebuild Domain Shift History from Archive
    if os.path.exists("history"):
        count = 0
        
        # FIX: Sort files by modification time so the oldest episodes are processed first
        # and the newest episode overwrites `prev_score` last.
        history_files = [f for f in os.listdir("history") if f.endswith(".json") and f != "icl_history.json"]
        history_files.sort(key=lambda x: os.path.getmtime(os.path.join("history", x)))
        
        for f in history_files:
            try:
                with open(f"history/{f}", "r") as hf:
                    data = json.load(hf)
                    if "domain" in data and "final_reward" in data and "model" in data:
                        # 1. Update Domain Shift Benchmarks
                        state._domain_shift.record(
                            data["domain"], 
                            data["final_reward"], 
                            int(data.get("timestamp", time.time()))
                        )
                        state._total_episodes += 1
                        
                        # 2. Update ICL History Index with the LATEST score
                        m_key = f"{data.get('provider', 'unknown')}/{data['model']}/{data['domain']}"
                        if m_key not in _icl_history:
                            _icl_history[m_key] = {
                                "diagnostic_history": [],
                                "breakdown_history": [],
                                "prev_score": 0.0,
                                "score_history": [],
                                "improvement_plan": "",
                                "icl_injection": "",
                                "run_count": 0,
                            }
                        
                        # Update to the latest score found in archive
                        curr_score = data["final_reward"]
                        _icl_history[m_key]["prev_score"] = curr_score
                        _icl_history[m_key]["run_count"] += 1
                        
                        if "breakdown" in data:
                            _icl_history[m_key]["breakdown_history"] = [data["breakdown"]]
                        
                        count += 1
            except:
                continue
        if count > 0:
            console.print(f"[green]✓ Rebuilt Benchmark history from {count} records[/green]")

@app.get("/health")
def health_check():
    return {"status": "ok", "project": "prism"}

# Metrics Endpoint (using state.py)
@app.get("/metrics")
def get_metrics():
    console.print(
        f"[dim]Metrics polled | "
        f"episodes={state._total_episodes} | "
        f"rolling_reward={state._rolling_reward:.3f} | "
        f"stage={state._curriculum.stage}[/dim]"
    )
    return {
        "reward_curve": state._reward_curve,
        "transfer_scores": state._domain_shift.get_scores(),
        "current_stage": state._curriculum.stage,
        "next_threshold": state._curriculum.threshold,
        "rolling_reward": state._rolling_reward,
        "total_episodes": state._total_episodes,
        "curriculum_stages": state._curriculum.get_history()
    }

# History Endpoints
@app.get("/history")
def list_history():
    history = []
    if not os.path.exists("history"):
        return []
    for f in os.listdir("history"):
        if f.endswith(".json") and f != "icl_history.json":
            try:
                with open(f"history/{f}", "r") as hf:
                    data = json.load(hf)
                    # Basic validation that this is a tournament result
                    if "model" in data and "final_reward" in data:
                        history.append({
                            "id": f.replace(".json", ""),
                            "model": data["model"],
                            "provider": data["provider"],
                            "domain": data["domain"],
                            "final_reward": data["final_reward"],
                            "steps": data["steps"],
                            "timestamp": os.path.getmtime(f"history/{f}")
                        })
            except Exception as e:
                console.print(f"[dim yellow]! Skipping malformed history file {f}: {e}[/dim yellow]")
    return sorted(history, key=lambda x: x["timestamp"], reverse=True)

@app.post("/history/clear")
def clear_history():
    if os.path.exists("history"):
        for f in os.listdir("history"):
            try:
                os.remove(f"history/{f}")
            except:
                pass
    _icl_history.clear()
    state._reward_curve.clear()
    state._total_episodes = 0
    state._domain_shift.history.clear()
    state._domain_shift.transfer_points.clear()
    return {"status": "success", "message": "History cleared"}

@app.get("/history/{eid}")
def get_history_detail(eid: str):
    path = f"history/{eid}.json"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="History not found")
    with open(path, "r") as f:
        return json.load(f)

# Model Router Endpoints
@app.get("/models/active")
def get_active_models():
    return llm_router.get_model_comparison()["models"].keys()

@app.get("/models/available")
def get_available_models():
    return llm_router.get_available_providers()

@app.get("/models/config")
def get_model_config(episode_id: Optional[str] = None):
    return llm_router.get_model_config(episode_id)

class ModelConfigRequest(BaseModel):
    provider: str
    model: str
    api_key: str
    episode_id: Optional[str] = None

@app.post("/models/config")
def set_model_config(req: ModelConfigRequest):
    return llm_router.set_model_config(req.provider, req.model, req.api_key, req.episode_id)

class ModelTestRequest(BaseModel):
    provider: str
    model: str
    api_key: str

@app.post("/models/test")
async def test_connection(req: ModelTestRequest):
    return await llm_router.test_connection(req.provider, req.model, req.api_key)

@app.get("/models/comparison")
def get_model_comparison():
    return llm_router.get_model_comparison()

# ── ICL Training Endpoints ──────────────────────────────────

@app.post("/icl/analyse")
def icl_analyse(payload: dict = Body(...)):
    """Analyse a model's weaknesses and generate an improvement plan."""
    model_key = payload.get("model_key", "")
    domain = payload.get("domain", "debug")
    
    entry = _icl_history.get(model_key, {
        "diagnostic_history": [],
        "breakdown_history": [],
        "prev_score": 0.0,
        "run_count": 0,
    })
    
    model_name = model_key.rsplit("/", 1)[0] if "/" in model_key else model_key
    
    plan = get_improvement_plan(
        diagnostic_history=entry.get("diagnostic_history", []),
        breakdown_history=entry.get("breakdown_history", []),
        domain=domain,
        model_name=model_name,
        prev_score=entry.get("prev_score", 0.0),
    )
    
    # Build ICL injection for preview
    icl_injection = build_icl_prompt_injection(
        diagnostic_history=entry.get("diagnostic_history", []),
        domain=domain,
        breakdown_history=entry.get("breakdown_history", []),
    )
    
    # Store in history
    if model_key in _icl_history:
        _icl_history[model_key]["improvement_plan"] = plan
        _icl_history[model_key]["icl_injection"] = icl_injection
    
    # Extract weaknesses list for frontend
    weaknesses = []
    bh = entry.get("breakdown_history", [])
    if bh:
        avg_pd = sum(b.get("progress_delta", 0.5) for b in bh) / len(bh)
        avg_ah = sum(b.get("atomic_health", 0.5) for b in bh) / len(bh)
        avg_hp = sum(b.get("hallucination_penalty", 0.5) for b in bh) / len(bh)
        last_tb = bh[-1].get("terminal_bonus", 0.01)
        if avg_pd < 0.08:
            weaknesses.append(f"Task graph not advancing (progress_delta avg: {avg_pd:.3f})")
        if avg_ah < 0.65:
            weaknesses.append(f"Transaction discipline failing (atomic_health avg: {avg_ah:.3f})")
        if avg_hp < 0.75:
            weaknesses.append(f"Hallucination detected (hallucination_penalty avg: {avg_hp:.3f})")
        if last_tb < 0.40:
            weaknesses.append(f"Final answer quality low (terminal_bonus: {last_tb:.3f})")
    
    return {
        "prev_score": entry.get("prev_score", 0.0),
        "improvement_plan": plan,
        "weaknesses": weaknesses,
        "ready_to_train": len(weaknesses) > 0,
        "run_count": entry.get("run_count", 0),
    }

@app.post("/icl/train")
def icl_train(payload: dict = Body(...)):
    """Inject ICL learning context into the model's next episode."""
    provider = payload.get("provider", "")
    model = payload.get("model", "")
    domain = payload.get("domain", "debug")
    episode_id = payload.get("episode_id", "")
    
    model_key = f"{provider}/{model}/{domain}"
    entry = _icl_history.get(model_key, {})
    
    # Build ICL injection from history
    icl_injection = build_icl_prompt_injection(
        diagnostic_history=entry.get("diagnostic_history", []),
        domain=domain,
        breakdown_history=entry.get("breakdown_history", []),
    )
    
    # Store the injection in llm_router for this episode
    if episode_id:
        llm_router.set_icl_injection(episode_id, icl_injection)
    
    # Also store in history
    if model_key in _icl_history:
        _icl_history[model_key]["icl_injection"] = icl_injection
    
    # Extract the actual diagnostic and corrections for display
    last_diag = entry.get("diagnostic_history", [""])[-1] if entry.get("diagnostic_history") else ""
    
    # Build a clean summary of what was injected
    corrections = []
    bh = entry.get("breakdown_history", [])
    if bh:
        avg_pd = sum(b.get("progress_delta", 0.5) for b in bh) / len(bh)
        avg_ah = sum(b.get("atomic_health", 0.5) for b in bh) / len(bh)
        avg_hp = sum(b.get("hallucination_penalty", 0.5) for b in bh) / len(bh)
        last_tb = bh[-1].get("terminal_bonus", 0.01)
        if avg_pd < 0.08:
            corrections.append("Task advancement instructions injected")
        if avg_ah < 0.65:
            corrections.append("Checkpoint/preflight/rollback protocol injected")
        if avg_hp < 0.75:
            corrections.append("Claim verification requirements injected")
        if last_tb < 0.40:
            corrections.append("Domain-specific answer structure injected")
    
    # PHASE C Terminal Output
    console.print(Panel(
        f"[bold green]ICL TRAINING APPLIED[/bold green] — {model}\n"
        f"Injection: {len(icl_injection)} tokens prepended to system prompt\n"
        f"Weaknesses targeted: {len(corrections)}\n"
        + "\n".join([f"  • {c}" for c in corrections]) +
        f"\n\n[dim]Episode {episode_id} ready for trained run[/dim]",
        title="[bold white]PHASE C: TRAINING[/bold white]",
        border_style="green"
    ))

    return {
        "ready": True,
        "injection_preview": icl_injection[:300] if icl_injection else "",
        "last_diagnostic": last_diag,
        "corrections_applied": corrections,
        "injection_length": len(icl_injection) if icl_injection else 0,
    }

@app.get("/icl/history")
def icl_history():
    """Return ICL training history summaries."""
    summary = {}
    for key, entry in _icl_history.items():
        summary[key] = {
            "prev_score": entry.get("prev_score", 0.0),
            "run_count": entry.get("run_count", 0),
            "last_diagnostic": entry["diagnostic_history"][-1] if entry.get("diagnostic_history") else "",
        }
    return summary

@app.post("/icl/analyse-all")
def icl_analyse_all(payload: dict = Body(...)):
    """Analyse ALL models that have run in a given domain. Used for tournament training."""
    domain = payload.get("domain", "debug")
    
    results = {}
    for key, entry in _icl_history.items():
        # key format: "provider/model/domain"
        parts = key.split("/")
        if len(parts) >= 3 and parts[-1] == domain:
            model_name = "/".join(parts[:-1])
            
            plan = get_improvement_plan(
                diagnostic_history=entry.get("diagnostic_history", []),
                breakdown_history=entry.get("breakdown_history", []),
                domain=domain,
                model_name=model_name,
                prev_score=entry.get("prev_score", 0.0),
            )
            
            icl_injection = build_icl_prompt_injection(
                diagnostic_history=entry.get("diagnostic_history", []),
                domain=domain,
                breakdown_history=entry.get("breakdown_history", []),
            )
            
            # Extract weaknesses
            weaknesses = []
            bh = entry.get("breakdown_history", [])
            if bh:
                avg_pd = sum(b.get("progress_delta", 0.5) for b in bh) / len(bh)
                avg_ah = sum(b.get("atomic_health", 0.5) for b in bh) / len(bh)
                avg_hp = sum(b.get("hallucination_penalty", 0.5) for b in bh) / len(bh)
                avg_ce = sum(b.get("coord_efficiency", 0.5) for b in bh) / len(bh)
                last_tb = bh[-1].get("terminal_bonus", 0.01)
                
                if avg_pd < 0.12:
                    weaknesses.append(f"Task graph stalled (progress avg: {avg_pd:.3f})")
                if avg_ce < 0.60:
                    weaknesses.append(f"High coordination overhead (efficiency: {avg_ce:.3f})")
                if avg_ah < 0.70:
                    weaknesses.append(f"Atomic safety risk (health avg: {avg_ah:.3f})")
                if avg_hp < 0.80:
                    weaknesses.append(f"Factuality issues (penalty avg: {avg_hp:.3f})")
                if last_tb < 0.50:
                    weaknesses.append(f"Final submission below quality threshold (bonus: {last_tb:.3f})")
                
                # Check for any pending tasks specifically
                pending_count = 0
                if bh and "task_graph" in bh[-1]:
                    pending_count = sum(1 for v in bh[-1]["task_graph"].values() if v.get("status") == "pending")
                
                if pending_count > 0:
                    weaknesses.append(f"Task graph incomplete ({pending_count} tasks pending)")
                
                # Check if 'verify' was specifically missed
                last_diag = entry.get("diagnostic_history", [""])[-1].lower()
                if "verify" in last_diag and "skipped" in last_diag:
                    weaknesses.append("Verification step was bypassed")
            
            results[key] = {
                "model_name": model_name,
                "prev_score": entry.get("prev_score", 0.0),
                "improvement_plan": plan,
                "weaknesses": weaknesses,
                "ready_to_train": len(weaknesses) > 0,
                "run_count": entry.get("run_count", 0),
                "last_diagnostic": entry.get("diagnostic_history", [""])[-1] if entry.get("diagnostic_history") else "",
            }
    
    return {"domain": domain, "models": results, "total_models": len(results)}

@app.post("/icl/train-all")
def icl_train_all(payload: dict = Body(...)):
    """Train ALL models for a given domain by injecting ICL context into their next episodes."""
    domain = payload.get("domain", "debug")
    episode_ids = payload.get("episode_ids", {})  # { "provider/model": "episode_id" }
    
    trained = {}
    for key, entry in _icl_history.items():
        parts = key.split("/")
        if len(parts) >= 3 and parts[-1] == domain:
            model_key_short = "/".join(parts[:-1])  # "provider/model"
            
            icl_injection = build_icl_prompt_injection(
                diagnostic_history=entry.get("diagnostic_history", []),
                domain=domain,
                breakdown_history=entry.get("breakdown_history", []),
            )
            
            # Inject into the episode if provided
            eid = episode_ids.get(model_key_short, "")
            if eid:
                llm_router.set_icl_injection(eid, icl_injection)
            
            entry["icl_injection"] = icl_injection
            
            # Extract corrections applied for this model
            corrections = []
            bh = entry.get("breakdown_history", [])
            if bh:
                avg_pd = sum(b.get("progress_delta", 0.5) for b in bh) / len(bh)
                avg_ah = sum(b.get("atomic_health", 0.5) for b in bh) / len(bh)
                avg_hp = sum(b.get("hallucination_penalty", 0.5) for b in bh) / len(bh)
                last_tb = bh[-1].get("terminal_bonus", 0.01)
                if avg_pd < 0.08:
                    corrections.append("Task advancement instructions")
                if avg_ah < 0.65:
                    corrections.append("Checkpoint/rollback protocol")
                if avg_hp < 0.75:
                    corrections.append("Claim verification rules")
                if last_tb < 0.40:
                    corrections.append("Answer structure requirements")
            
            last_diag = entry.get("diagnostic_history", [""])[-1] if entry.get("diagnostic_history") else ""
            
            trained[key] = {
                "model_name": model_key_short,
                "injected": bool(eid),
                "last_diagnostic": last_diag,
                "corrections_applied": corrections,
                "injection_length": len(icl_injection) if icl_injection else 0,
            }
    
    return {"domain": domain, "trained_models": trained, "total_trained": len(trained)}

# Static Files
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

static_dir = os.path.join(os.path.dirname(__file__), "..", "website", "out")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    # Fallback for development if 'out' doesn't exist
    static_dir_alt = os.path.join(os.path.dirname(__file__), "..", "static")
    if os.path.exists(static_dir_alt):
        app.mount("/", StaticFiles(directory=static_dir_alt, html=True), name="static")
