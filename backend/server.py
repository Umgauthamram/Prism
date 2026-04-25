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
from openenv.core import HTTPEnvServer

from .environment import PrismEnv
from . import llm_router, state
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
    obs = env.reset(seed=final_seed, options=options)
    # Ensure eid is set in both the env and the observation
    env.episode_id = eid
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
        return ENVS[eid].state
    
    # Return a blank state instead of 404 to keep dashboard happy
    return {
        "task_graph": {},
        "world_model": {},
        "last_tool_output": {},
        "agent_role": "Planner",
        "step": 0,
        "terminated": False
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
