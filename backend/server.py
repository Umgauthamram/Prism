from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
import time
import csv
import os
import wandb
import json

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
console = Console()

from .environment import PrismEnv
from . import llm_router
from .curriculum import CurriculumManager
from .injectors import DomainShiftInjector

app = FastAPI(title="Prism RL Environment")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State
_episodes: Dict[str, PrismEnv] = {}
_active_episode_id: Optional[str] = None
_reward_curve: List[Dict[str, Any]] = []
_rolling_reward: float = 0.0
_total_episodes: int = 0
_curriculum = CurriculumManager()
_domain_shift = DomainShiftInjector()

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
        console.print(f"[yellow]⚠️ W&B Initialization failed: {e}[/yellow]")

def log_to_csv(model_name: str, provider: str, final_reward: float, steps: int):
    file_path = "tournament_history.csv"
    file_exists = os.path.isfile(file_path)
    with open(file_path, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "model", "provider", "final_reward", "steps"])
        writer.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), model_name, provider, round(final_reward, 4), steps])

class ResetRequest(BaseModel):
    seed: Optional[int] = 42
    options: Optional[Dict[str, Any]] = {}

class StepRequest(BaseModel):
    action: Dict[str, Any]
    episode_id: Optional[str] = None

class ModelConfigRequest(BaseModel):
    provider: str
    model: str
    api_key: str
    episode_id: Optional[str] = None

class ModelTestRequest(BaseModel):
    provider: str
    model: str
    api_key: str

@app.get("/health")
def health():
    return {"status": "ok", "project": "prism", "timestamp": time.time()}

@app.post("/reset")
def reset(req: ResetRequest):
    global _active_episode_id, _total_episodes, _reward_curve
    env = PrismEnv()
    
    obs = env.reset(req.seed, req.options)
    eid = obs["episode_id"]
    
    _episodes[eid] = env
    _active_episode_id = eid
    _total_episodes += 1
    _reward_curve = [] # Clear the curve for the new model run
    
    console.print(Panel(
        f"[bold cyan]EPISODE RESET[/bold cyan]\n"
        f"Domain: [yellow]{env.task_domain}[/yellow]  "
        f"Agents: [green]{env.agents}[/green]  "
        f"Failure Rate: [red]{env.failure_rate}[/red]  "
        f"Seed: [blue]{req.seed}[/blue]\n"
        f"Episode ID: [dim]{eid[:8]}...[/dim]",
        title="[bold]prism RL Environment[/bold]",
        border_style="cyan"
    ))
    
    return obs

@app.post("/step")
async def step(req: StepRequest):
    global _active_episode_id, _rolling_reward
    try:
        eid = req.episode_id or _active_episode_id
        if not eid or eid not in _episodes:
            raise HTTPException(status_code=404, detail="Episode not found")
            
        env = _episodes[eid]
        obs, reward, terminated, truncated, info = await env.step(req.action)
        
        breakdown = info.get("reward_breakdown", {"total": reward})
        table = Table(show_header=True, header_style="bold magenta", title=f"Step {env.step_count} | Role: {env.agent_role}")
        table.add_column("Component", style="cyan", width=22)
        table.add_column("Value", justify="right", style="green")
        table.add_column("Weight", justify="right", style="dim")
        table.add_row("Progress Delta", f"{breakdown.get('progress_delta', 0):.4f}", "×0.40")
        table.add_row("Atomic Health", f"{breakdown.get('atomic_health', 0):.4f}", "×0.20")
        table.add_row("Coord Efficiency", f"{breakdown.get('coord_efficiency', 0):.4f}", "×0.20")
        table.add_row("Hallucination Pen.", f"{breakdown.get('hallucination_penalty', 0):.4f}", "×0.10")
        table.add_row("Terminal Bonus", f"{breakdown.get('terminal_bonus', 0):.4f}", "×0.10")
        table.add_section()
        table.add_row("[bold]TOTAL REWARD[/bold]", f"[bold yellow]{reward:.4f}[/bold yellow]", "")
        console.print(table)
        
        if env.injected_failure_flag:
            console.print("[bold red]⚠ INJECTED FAILURE ACTIVE — Atomic Failure Injector triggered[/bold red]")
            
        if info.get("error") == "role_contract_violation":
            console.print(f"[red]✗ ROLE VIOLATION: {env.agent_role} tried '{req.action.get('tool')}' — reward zeroed[/red]")
        
        # Update global metrics
        _reward_curve.append({
            "step": env.step_count,
            "total": reward,
            "breakdown": info.get("reward_breakdown", {"total": reward})
        })
        if len(_reward_curve) > 200:
            _reward_curve.pop(0)
            
        _rolling_reward = 0.1 * reward + 0.9 * _rolling_reward
        _curriculum.update(reward)
        
        if terminated:
            _domain_shift.record(env.task_domain, reward, _total_episodes)
            # Log to local history CSV
            config = llm_router.get_model_config(eid)
            if config["active_model"]:
                log_to_csv(config["active_model"], config["active_provider"], reward, env.step_count)
                
                # Save full trajectory to history folder (Safely)
                try:
                    history_data = {
                        "model": config["active_model"],
                        "provider": config["active_provider"],
                        "domain": env.task_domain,
                        "final_reward": reward,
                        "steps": env.step_count,
                        "trajectory": [p for p in _reward_curve if p.get("episode_id") == eid or True]
                    }
                    with open(f"history/{eid}.json", "w") as f:
                        json.dump(history_data, f)
                except Exception as history_err:
                    print(f"⚠️ Failed to save history for {eid}: {history_err}")

                # Also log to W&B
                try:
                    wandb.log({
                        f"eval/{config['active_model']}/reward": reward,
                        f"eval/{config['active_model']}/steps": env.step_count,
                        "episode": _total_episodes
                    })
                except:
                    pass
            
        return {
            "observation": obs,
            "reward": reward,
            "terminated": terminated,
            "truncated": truncated,
            "info": info,
            "episode_id": eid
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/state")
def get_state(episode_id: Optional[str] = None):
    eid = episode_id or _active_episode_id
    if not eid or eid not in _episodes:
        return None
    return _episodes[eid].state()

@app.get("/metrics")
def get_metrics():
    console.print(
        f"[dim]📊 metrics polled | "
        f"episodes={_total_episodes} | "
        f"rolling_reward={_rolling_reward:.3f} | "
        f"stage={_curriculum.stage}[/dim]"
    )
    return {
        "reward_curve": _reward_curve,
        "transfer_scores": _domain_shift.get_scores(),
        "current_stage": _curriculum.stage,
        "next_threshold": _curriculum.threshold,
        "rolling_reward": _rolling_reward,
        "total_episodes": _total_episodes,
        "curriculum_stages": _curriculum.get_history()
    }

# History Endpoints
@app.get("/history")
def list_history():
    history = []
    if not os.path.exists("history"):
        return []
    for f in os.listdir("history"):
        if f.endswith(".json"):
            with open(f"history/{f}", "r") as hf:
                data = json.load(hf)
                history.append({
                    "id": f.replace(".json", ""),
                    "model": data["model"],
                    "provider": data["provider"],
                    "domain": data["domain"],
                    "final_reward": data["final_reward"],
                    "steps": data["steps"],
                    "timestamp": os.path.getmtime(f"history/{f}")
                })
    return sorted(history, key=lambda x: x["timestamp"], reverse=True)

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
    # Return a list of models currently being tracked for the comparison chart
    return llm_router.get_model_comparison()["models"].keys()
@app.get("/models/available")
def get_available_models():
    return llm_router.get_available_providers()

@app.get("/models/config")
def get_model_config(episode_id: Optional[str] = None):
    return llm_router.get_model_config(episode_id)

@app.post("/models/config")
def set_model_config(req: ModelConfigRequest):
    return llm_router.set_model_config(req.provider, req.model, req.api_key, req.episode_id)

@app.post("/models/test")
async def test_connection(req: ModelTestRequest):
    return await llm_router.test_connection(req.provider, req.model, req.api_key)

@app.get("/models/comparison")
def get_model_comparison():
    return llm_router.get_model_comparison()

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(static_dir, "index.html"))
    
    @app.get("/{full_path:path}")
    async def serve_frontend_routes(full_path: str):
        file_path = os.path.join(static_dir, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(static_dir, "index.html"))
