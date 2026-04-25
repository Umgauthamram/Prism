from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal


# ── Action ────────────────────────────────────────────────
class PrismAction(BaseModel):
    """
    A single tool call by an agent in the prism environment.
    The tool must be in the ROLE_CONTRACTS for the current agent_role,
    otherwise reward=0 and a role_contract_violation error is returned.
    """
    tool: str = Field(
        description="Tool name. Must match current agent role contract.",
        examples=["checkpoint", "research_web", "write_code",
                  "critique", "finish"]
    )
    args: Dict[str, Any] = Field(
        default_factory=dict,
        description="Tool arguments. Keys depend on the tool.",
        examples=[
            {"q": "analyse Python bug"},
            {"path": "fix.py", "body": "def f(): return True"},
            {"answer": "range(len(items)) fix applied"},
        ]
    )


# ── Observation ───────────────────────────────────────────
class TaskNode(BaseModel):
    status: Literal["pending", "running", "done", "failed"]
    dependencies: list[str]


class PrismObservation(BaseModel):
    """
    What the agent sees after each step.
    Returned by reset() and step().
    """
    task_graph: Dict[str, TaskNode] = Field(
        description="Dependency-ordered subtask list with current status."
    )
    world_model: Dict[str, Any] = Field(
        default_factory=dict,
        description="Shared facts and results. Single source of truth."
    )
    last_tool_output: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Result of most recent tool call."
    )
    checkpoint_id: str = Field(
        description="Last stable state boundary for rollback."
    )
    agent_role: Literal[
        "Planner", "Researcher", "Coder", "Critic", "Synthesizer"
    ] = Field(description="Current active agent role.")
    injected_failure_flag: bool = Field(
        description="True when Injector 2 (Atomic Failure) is active."
    )
    episode_id: str = Field(description="UUID for this episode.")
    step: int = Field(description="Current step number.")
    task_domain: Literal["debug", "market_research", "etl"]
    agents: Literal[2, 4, 8]
    failure_rate: float
    terminated: bool = False
    reward: float = Field(default=0.0, ge=0.0, le=1.0)
    done: bool = False
    info: Dict[str, Any] = Field(default_factory=dict)


# ── State ────────────────────────────────────────────────
class PrismState(BaseModel):
    """
    Full internal episode state. Returned by state() endpoint.
    Used by dashboard for live monitoring.
    """
    episode_id: str
    step_count: int
    task_domain: str
    agents: int
    failure_rate: float
    task_graph: Dict[str, TaskNode]
    world_model: Dict[str, Any]
    orphaned_side_effects: int
    total_side_effects: int
    terminated: bool
    injected_failure_flag: bool
    agent_role: str
    checkpoint_id: str
