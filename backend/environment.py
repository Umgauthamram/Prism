import uuid
import random
from typing import Dict, Any, Tuple
from .roles.contracts import ROLES, ROLE_CONTRACTS
from .tools import registry
from .injectors.atomic_failure import AtomicFailureInjector
from .injectors.coordination import CoordinationInjector
from .reward import compute_reward
from .tasks import debugging, market_research, etl_pipeline
from . import llm_router

class PrismEnv:
    def __init__(self):
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

    def reset(self, seed: int, options: dict) -> dict:
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
        
        return self._obs()

    async def step(self, action: dict) -> Tuple[dict, float, bool, bool, dict]:
        model_used = None
        provider_used = None
        llm_latency_ms = None

        # If llm_router has an active model, override the action
        active_config = llm_router.get_model_config(self.episode_id)
        if active_config["active_provider"] and active_config["active_model"]:
            llm_action = await llm_router.generate_agent_action(
                observation=self._obs(),
                role=self.agent_role,
                allowed_tools=ROLE_CONTRACTS[self.agent_role]
            )
            action = {"tool": llm_action["tool"], "args": llm_action["args"]}
            model_used = llm_action["model_used"]
            provider_used = llm_action["provider_used"]
            llm_latency_ms = llm_action["latency_ms"]

        tool = action.get("tool")
        args = action.get("args", {})
        
        prev_done_count = sum(1 for v in self.task_graph.values() if v["status"] == "done")
        
        if self.step_count >= 50:
            return self._obs(), 0.0, True, False, {"error": "max_steps_exceeded"}

        # Role Contract Check
        if tool not in ROLE_CONTRACTS[self.agent_role]:
            self.step_count += 1
            self.agent_role = ROLES[self.step_count % len(ROLES)]
            return self._obs(), 0.0, False, False, {"error": "role_contract_violation"}

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
            )
            self.step_count += 1
            self.agent_role = ROLES[self.step_count % len(ROLES)]
            info = {
                "reward_breakdown": breakdown,
                "episode_id": self.episode_id,
                "step": self.step_count,
                "injected_failure": True,
                "model_used": model_used,
                "llm_latency_ms": llm_latency_ms,
            }
            return self._obs(), reward, False, False, info

        # Coordination tracking
        if tool in ["research_web", "write_world"] or "content" in args:
            content = args.get("content") or args.get("q") or str(args.get("update", ""))
            if content:
                self.coord_injector.record_token(str(content), args.get("useful", True))

        # Tool execution
        result = self._execute_tool(tool, args)
        self.last_tool_output = result
        
        # Reward components
        done_count = sum(1 for n in self.task_graph.values() if n["status"] == "done")
        
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
            grader_score=grader_score
        )
        
        self.prev_done_count = done_count
        self.step_count += 1
        self.agent_role = ROLES[self.step_count % len(ROLES)]
        
        # Record model result if active
        llm_router.record_model_result(self.episode_id, self.step_count, reward, breakdown)
        
        self.terminated = (tool == "finish") or (self.step_count >= 50)
        info = {
            "reward_breakdown": breakdown, 
            "episode_id": self.episode_id,
            "model_used": model_used,
            "provider_used": provider_used,
            "llm_latency_ms": llm_latency_ms
        }
        
        return self._obs(), reward, self.terminated, False, info

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

    def _obs(self) -> dict:
        return self.state()

    def _execute_tool(self, tool: str, args: dict) -> dict:
        if tool == "research_web":
            res = registry.research_web(args.get("q", ""))
            # Advance task graph: pending → running for first eligible node
            for k, v in self.task_graph.items():
                if v["status"] == "pending":
                    deps_met = all(
                        self.task_graph[d]["status"] == "done"
                        for d in v["dependencies"]
                    )
                    if deps_met:
                        v["status"] = "running"
                        break
            return res
        elif tool == "write_code":
            self.total_side_effects += 1
            res = registry.write_code(args.get("path", ""), args.get("body", ""), self.fs_dict)
            # Advance task graph: running → done, or pending → done
            advanced = False
            for k, v in self.task_graph.items():
                if v["status"] == "running":
                    v["status"] = "done"
                    advanced = True
                    break
            if not advanced:
                for k, v in self.task_graph.items():
                    if v["status"] == "pending":
                        v["status"] = "done"
                        break
            return res
        elif tool == "run_tests":
            self.total_side_effects += 1
            res = registry.run_tests(args.get("path", ""), self.task_graph)
            # Advance task graph: running → done, or pending → done
            advanced = False
            for k, v in self.task_graph.items():
                if v["status"] == "running":
                    v["status"] = "done"
                    advanced = True
                    break
            if not advanced:
                for k, v in self.task_graph.items():
                    if v["status"] == "pending":
                        v["status"] = "done"
                        break
            return res
        elif tool == "db_preflight":
            return registry.db_preflight(args.get("spec", {}), self.preflights)
        elif tool == "db_commit":
            self.total_side_effects += 1
            return registry.db_commit(args.get("preflight_id", ""), self.preflights)
        elif tool == "checkpoint":
            res = registry.checkpoint(self.episode_id, self.step_count, self.world_model, self.task_graph, self.checkpoints)
            self.checkpoint_id = res["data"]["checkpoint_id"]
            return res
        elif tool == "rollback":
            res = registry.rollback(args.get("checkpoint_id", ""), self.checkpoints)
            if res["success"]:
                self.world_model = res["data"]["world_model"]
                self.task_graph = res["data"]["task_graph"]
            return res
        elif tool == "critique":
            return registry.critique(args.get("target", ""))
        elif tool == "finish":
            # Flip all remaining "running" nodes to "done" before grading
            for k, v in self.task_graph.items():
                if v["status"] == "running":
                    v["status"] = "done"
            g_func = None
            if self.task_domain == "debug": g_func = debugging.grade
            elif self.task_domain == "market_research": g_func = market_research.grade
            else: g_func = etl_pipeline.grade
            return registry.finish(args.get("answer", ""), g_func, self.task_data)
        elif tool in ["decompose", "assign", "replan", "write_world", "merge", "flag_hallucination", "request_replan", "flag_gap"]:
            # Logic tools that update state
            if "update" in args:
                self.world_model.update(args["update"])
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
