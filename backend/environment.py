import uuid
import random
from typing import Dict, Any, Tuple, Optional, List
from openenv.core import Environment
from .roles.contracts import ROLES, ROLE_CONTRACTS
from .tools import registry
from .injectors.atomic_failure import AtomicFailureInjector
from .injectors.coordination import CoordinationInjector
from .reward import compute_reward
from .tasks import debugging, market_research, etl_pipeline
from .rubric import DebuggingRubric, MarketResearchRubric
from . import llm_router, state
from envs.prism import PrismObservation, PrismAction
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import wandb
import time

console = Console()

class PrismEnv(Environment[PrismAction, PrismObservation, dict]):
    def __init__(self):
        super().__init__()
        self.episode_id = None
        self.task_domain = None
        self.agents = None
        self.failure_rate = None
        
        self.task_graph = {}
        self.world_model = {}
        self.last_tool_output = None
        self.checkpoint_id = None
        self.agent_role = None
        self.injected_failure_flag = False
        self.step_count = 0
        self.terminated = False
        
        self.atomic_injector = AtomicFailureInjector()
        self.coord_injector = CoordinationInjector()
        
        self.fs_dict = {}
        self.preflights = {}
        self.checkpoints = {}
        
        self.task_data = None
        self.orphaned_side_effects = 0
        self.total_side_effects = 0
        self.prev_done_count = 0
        self.steps_since_checkpoint = 0

    def reset(self, seed: int = 42, options: dict = None) -> PrismObservation:
        if options is None:
            options = {}
        random.seed(seed)
        self.episode_id = str(uuid.uuid4())
        self.task_domain = options.get("task_domain", "debug")
        self.agents = options.get("agents", 2)
        self.failure_rate = options.get("failure_rate", 0.0)
        
        self.atomic_injector.reset(self.failure_rate)
        self.coord_injector.reset(self.agents)
        
        self.task_graph = self._build_task_graph(self.task_domain)
        self.world_model = {}
        self.last_tool_output = None
        self.injected_failure_flag = False
        self.step_count = 0
        self.terminated = False
        self.orphaned_side_effects = 0
        self.total_side_effects = 0
        self.prev_done_count = 0
        
        # Don't wipe the global reward curve — other episodes may be running
        # state._total_episodes is incremented in state.update_metrics when terminated=True
        
        # Domain specific task gen
        if self.task_domain == "debug":
            self.task_data = debugging.generate_task(seed)
        elif self.task_domain == "market_research":
            self.task_data = market_research.generate_task(seed)
        else:
            self.task_data = etl_pipeline.generate_task(seed)
            
        self.agent_role = ROLES[0]
        
        # Initial checkpoint
        cp_res = registry.checkpoint(self.episode_id, 0, self.world_model, self.task_graph, self.checkpoints)
        self.checkpoint_id = cp_res["data"]["checkpoint_id"]
        
        console.print(Panel(
            f"[bold cyan]EPISODE RESET[/bold cyan]\n"
            f"Domain: [yellow]{self.task_domain}[/yellow]  "
            f"Agents: [green]{self.agents}[/green]  "
            f"Failure Rate: [red]{self.failure_rate}[/red]  "
            f"Seed: [blue]{seed}[/blue]\n"
            f"Episode ID: [dim]{self.episode_id[:8]}...[/dim]",
            title="[bold]prism RL Environment[/bold]",
            border_style="cyan"
        ))
        
        return self._obs()

    def step(self, action: PrismAction | dict, timeout_s: Optional[float] = None, **kwargs: Any) -> PrismObservation:
        """Sync step is not implemented, use step_async."""
        raise NotImplementedError("Use step_async")

    async def step_async(self, action: PrismAction | dict, timeout_s: Optional[float] = None, **kwargs: Any) -> PrismObservation:
        if isinstance(action, PrismAction):
            action_dict = action.model_dump()
        else:
            action_dict = action

        model_used = None
        provider_used = None
        llm_latency_ms = None

        # If llm_router has an active model, override the action
        active_config = llm_router.get_model_config(self.episode_id)
        if active_config["active_provider"] and active_config["active_model"]:
            llm_action = await llm_router.generate_agent_action(
                observation=self._obs_dict(),
                role=self.agent_role,
                allowed_tools=ROLE_CONTRACTS[self.agent_role]
            )
            action_dict = {"tool": llm_action["tool"], "args": llm_action["args"]}
            model_used = llm_action["model_used"]
            provider_used = llm_action["provider_used"]
            llm_latency_ms = llm_action["latency_ms"]
            
            # Use the AI's tool for the rest of the logic
            tool = action_dict.get("tool")
            args = action_dict.get("args", {})
        else:
            tool = action_dict.get("tool")
            args = action_dict.get("args", {})
        
        prev_done_count = sum(1 for v in self.task_graph.values() if v["status"] == "done")
        prev_running_count = sum(1 for v in self.task_graph.values() if v["status"] == "running")
        
        reward = 0.0
        breakdown = {}
        info = {}

        if self.step_count >= 25:
            reward, breakdown = compute_reward(
                done_count=sum(1 for v in self.task_graph.values() if v["status"] == "done"),
                prev_done_count=sum(1 for v in self.task_graph.values() if v["status"] == "done"),
                total_tasks=len(self.task_graph),
                orphaned_side_effects=self.orphaned_side_effects,
                total_side_effects=max(1, self.total_side_effects),
                coord_efficiency=self.coord_injector.efficiency(),
                hallucination_rate=0.0,
                terminal=False,
                grader_score=0.0,
                prev_running_count=0,
                steps_since_checkpoint=self.steps_since_checkpoint
            )
            self.terminated = True
            return self._obs(reward=reward, done=True, info={"reward_breakdown": breakdown})

        # Role Contract Check (with fallback to keep episode alive)
        if tool not in ROLE_CONTRACTS[self.agent_role]:
            # Automatically swap to an allowed tool for this role if AI/UI makes a mistake
            old_tool = tool
            tool = ROLE_CONTRACTS[self.agent_role][0]
            args = {}
            console.print(f"[yellow]⚠ {self.agent_role} tried '{old_tool}' (forbidden) - Swapped to '{tool}'[/yellow]")
        
        # Log which model is acting if applicable
        eid_prefix = f"[{self.episode_id[:4]}]" if self.episode_id else ""
        model_prefix = f"({model_used[:8]})" if model_used else ""
        if self.step_count % 5 == 0:
            console.print(f"[dim]{eid_prefix}{model_prefix} Step {self.step_count} | Role: {self.agent_role}[/dim]")

        # Atomic Failure Injection
        self.injected_failure_flag = False
        if self.atomic_injector.should_fail():
            self.injected_failure_flag = True
            self.orphaned_side_effects += 1
            self.total_side_effects += 1
            # Still compute reward — failure is reflected in atomic_health
            reward, breakdown = compute_reward(
                done_count=prev_done_count,  # nothing changed
                prev_done_count=prev_done_count,
                total_tasks=len(self.task_graph),
                orphaned_side_effects=self.orphaned_side_effects,
                total_side_effects=max(1, self.total_side_effects),
                coord_efficiency=self.coord_injector.efficiency(),
                hallucination_rate=0.0,
                terminal=False,
                grader_score=0.0,
                prev_running_count=prev_running_count,
                steps_since_checkpoint=self.steps_since_checkpoint
            )
            self.step_count += 1
            self.agent_role = ROLES[self.step_count % len(ROLES)]
            console.print("[bold red]! INJECTED FAILURE ACTIVE - Atomic Failure Injector triggered[/bold red]")
            return self._obs(reward=reward, done=False, info={"reward_breakdown": breakdown})

        # Tool execution
        result = self._execute_tool(tool, args)
        self.last_tool_output = result
        
        # Reward components
        done_count = sum(1 for n in self.task_graph.values() if n["status"] == "done")
        running_count = sum(1 for n in self.task_graph.values() if n["status"] == "running")
        
        grader_score = 0.0
        if tool == "finish":
            grader_score = result.get("data", {}).get("grader_score", 0.0)
            
        reward, breakdown = compute_reward(
            done_count=done_count,
            prev_done_count=prev_done_count,
            total_tasks=len(self.task_graph),
            orphaned_side_effects=self.orphaned_side_effects,
            total_side_effects=max(1, self.total_side_effects),
            coord_efficiency=self.coord_injector.efficiency(),
            hallucination_rate=result.get("data", {}).get("hallucination_rate", 0.0) if tool == "critique" else 0.0,
            terminal=(tool == "finish"),
            grader_score=grader_score,
            prev_running_count=prev_running_count,
            steps_since_checkpoint=self.steps_since_checkpoint,
            rubric_dims=result.get("data", {}).get("dimensions", {}) if result else {}
        )
        
        # Log to Rich Table
        table = Table(show_header=True, header_style="bold magenta", title=f"Step {self.step_count} | Role: {self.agent_role}")
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

        # Update termination status
        if tool == "finish" or self.step_count >= 24:
            self.terminated = True

        # Update global metrics
        state.update_metrics(self.step_count, reward, breakdown, self.terminated, self.task_domain, self.episode_id)
        
        # Record model result if active
        llm_router.record_model_result(self.episode_id, self.step_count, reward, breakdown)

        self.prev_done_count = done_count
        self.step_count += 1
        self.agent_role = ROLES[self.step_count % len(ROLES)]

        self.steps_since_checkpoint += 1
        
        # W&B Logging
        if self.terminated and active_config["active_model"]:
            try:
                wandb.log({
                    f"eval/{active_config['active_model']}/reward": reward,
                    f"eval/{active_config['active_model']}/steps": self.step_count,
                    "episode_id": self.episode_id
                })
            except:
                pass

        return self._obs(reward=reward, done=self.terminated, info={"reward_breakdown": breakdown})

    @property
    def state(self) -> dict:
        return {
            "task_graph": self.task_graph,
            "world_model": self.world_model,
            "last_tool_output": self.last_tool_output,
            "checkpoint_id": self.checkpoint_id,
            "agent_role": self.agent_role,
            "injected_failure_flag": self.injected_failure_flag,
            "episode_id": self.episode_id,
            "step": self.step_count,
            "task_domain": self.task_domain,
            "agents": self.agents,
            "failure_rate": self.failure_rate,
            "terminated": self.terminated
        }

    def _obs(self, reward: float = 0.0, done: bool = False, info: dict = None) -> PrismObservation:
        return PrismObservation(
            **self.state,
            reward=reward,
            done=done,
            info=info or {}
        )

    def _obs_dict(self, reward: float = 0.0, done: bool = False) -> dict:
        return self._obs(reward, done).model_dump()

    def _first_ready_pending(self) -> str | None:
        for task_id, node in self.task_graph.items():
            if node["status"] != "pending":
                continue
            all_deps_done = all(
                self.task_graph.get(d, {}).get("status") == "done"
                for d in node["dependencies"]
            )
            if all_deps_done:
                return task_id
        return None

    def _first_running(self) -> str | None:
        for task_id, node in self.task_graph.items():
            if node["status"] == "running":
                return task_id
        return None

    def _execute_tool(self, tool: str, args: dict) -> dict:
        if tool == "research_web":
            self.total_side_effects += 1
            res = registry.research_web(args.get("q", ""))
            self.coord_injector.record_token(args.get("q", ""), useful=True)
            
            # Start the first pending task if nothing is running
            running = self._first_running()
            if not running:
                ready = self._first_ready_pending()
                if ready:
                    self.task_graph[ready]["status"] = "running"
                    res["data"] = f"researching: {args.get('q','')} | task {ready} now running"
            return res
        elif tool == "write_code":
            self.total_side_effects += 1
            res = registry.write_code(args.get("path", ""), args.get("body", ""), self.fs_dict)
            self.coord_injector.record_token(
                args.get("body", "") + args.get("path", ""), useful=True
            )
            running = self._first_running()
            if running:
                self.task_graph[running]["status"] = "done"
            else:
                ready = self._first_ready_pending()
                if ready:
                    self.task_graph[ready]["status"] = "done"
            return res
        elif tool == "run_tests":
            self.total_side_effects += 1
            res = registry.run_tests(args.get("path", ""), self.task_graph)
            self.coord_injector.record_token(
                f"running tests on {args.get('path', '')}", useful=True
            )
            running = self._first_running()
            if running:
                self.task_graph[running]["status"] = "done"
                res["data"] = f"tests passed | task {running} completed"
            else:
                ready = self._first_ready_pending()
                if ready:
                    self.task_graph[ready]["status"] = "done"
            return res
        elif tool == "db_preflight":
            return registry.db_preflight(args.get("spec", {}), self.preflights)
        elif tool == "db_commit":
            self.total_side_effects += 1
            res = registry.db_commit(args.get("preflight_id", ""), self.preflights)
            running = self._first_running()
            if running:
                self.task_graph[running]["status"] = "done"
            else:
                ready = self._first_ready_pending()
                if ready:
                    self.task_graph[ready]["status"] = "done"
            return res
        elif tool == "checkpoint":
            self.total_side_effects += 1
            res = registry.checkpoint(self.episode_id, self.step_count, self.world_model, self.task_graph, self.checkpoints)
            self.checkpoint_id = res["data"]["checkpoint_id"]
            # Checkpointing world model is coordination overhead
            self.coord_injector.record_token(
                f"checkpoint at step {self.step_count}", useful=False
            )
            self.steps_since_checkpoint = 0
            return res
        elif tool == "rollback":
            res = registry.rollback(args.get("checkpoint_id", ""), self.checkpoints)
            if res["success"]:
                self.world_model = res["data"]["world_model"]
                self.task_graph = res["data"]["task_graph"]
                self.steps_since_checkpoint = 0
            return res
        elif tool == "critique":
            self.total_side_effects += 1
            # Critique reads world model — partly useful, partly overhead
            self.coord_injector.record_token(
                args.get("target", ""), useful=False
            )
            return registry.critique(args.get("target", ""))
        elif tool == "finish":
            # Use multi-dimensional Rubric
            rubric = None
            if self.task_domain == "debug":
                rubric = DebuggingRubric("DebugEval")
            elif self.task_domain == "market_research":
                rubric = MarketResearchRubric("ResearchEval")
            else:
                # Fallback for ETL
                rubric = DebuggingRubric("ETLEval")
                
            res_obj = rubric.evaluate(args.get("answer", ""), self.task_data)
            score = res_obj.score
            
            return {
                "success": True, 
                "data": {
                    "grader_score": score, 
                    "reasoning": res_obj.reasoning,
                    "dimensions": res_obj.dimensions,
                    "answer": args.get("answer", "")
                }, 
                "latency_ms": 50
            }
        elif tool in ["decompose", "assign", "replan", "write_world", "merge", "flag_hallucination", "request_replan", "flag_gap"]:
            # Logic tools that update state
            if "update" in args:
                self.world_model.update(args["update"])
                self.coord_injector.record_token(
                    str(args["update"]), useful=True
                )
            if "task_done" in args and args["task_done"] in self.task_graph:
                node = self.task_graph[args["task_done"]]
                # STRICT DEPENDENCY CHECK
                met = all(self.task_graph[d]["status"] == "done" for d in node["dependencies"])
                if met:
                    node["status"] = "done"
                else:
                    return {"success": False, "error": f"Dependency violation: {args['task_done']} requires {node['dependencies']}", "latency_ms": 10}
            return {"success": True, "data": "State updated", "latency_ms": 10}
        
        return {"success": False, "error": f"Unknown tool {tool}", "latency_ms": 0}

    def _build_task_graph(self, domain: str) -> dict:
        nodes = []
        if domain == "debug":
            nodes = ["analyse_bug", "locate_code", "write_fix", "run_tests", "verify"]
        elif domain == "market_research":
            nodes = ["identify_competitors", "gather_data", "analyse_dimensions", "score_confidence", "synthesise"]
        else: # etl
            nodes = ["parse_schemas", "write_transforms", "validate_output", "run_pipeline", "report"]
            
        graph = {}
        for i, node in enumerate(nodes):
            graph[node] = {
                "status": "pending",
                "dependencies": [nodes[i-1]] if i > 0 else []
            }
        return graph
