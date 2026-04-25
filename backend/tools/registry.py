import time
import uuid

def research_web(q: str):
    """Simulates web search for market research."""
    time.sleep(0.1)
    results = [
        {"name": f"Competitor {i}", "market_share": f"{10+i}%", "key_feature": f"Feature {i}"}
        for i in range(1, 4)
    ]
    return {"success": True, "data": results, "latency_ms": 150}

def write_code(path: str, body: str, fs_dict: dict):
    """Writes to sandboxed in-memory filesystem."""
    fs_dict[path] = body
    return {"success": True, "data": f"Wrote to {path}", "latency_ms": 50}

def run_tests(path: str, task_graph: dict):
    """Simulates pytest execution."""
    # Simple logic: if file exists, some tests pass
    passed = 5
    failed = 0
    exit_code = 0
    
    # The tool should NOT mark tasks as done automatically.
    # The agent must use 'replan' or 'assign' with 'task_done' explicitly.
            
    return {"success": True, "data": {"passed": passed, "failed": failed, "exit_code": exit_code}, "latency_ms": 300}

def db_preflight(spec: dict, preflights: dict):
    """Registers a side-effectful DB operation."""
    preflight_id = f"pf_{uuid.uuid4().hex[:8]}"
    preflights[preflight_id] = spec
    return {"success": True, "data": {"preflight_id": preflight_id}, "latency_ms": 20}

def db_commit(preflight_id: str, preflights: dict):
    """Executes a previously registered preflight operation."""
    if preflight_id not in preflights:
        return {"success": False, "error": "Invalid preflight_id", "latency_ms": 10}
    
    spec = preflights.pop(preflight_id)
    return {"success": True, "data": f"Committed operation: {spec}", "latency_ms": 100}

def checkpoint(episode_id: str, step: int, world_model: dict, task_graph: dict, checkpoints: dict):
    """Snapshots current world_model and task_graph."""
    cp_id = f"cp_{episode_id}_{step}"
    checkpoints[cp_id] = {
        "world_model": world_model.copy(),
        "task_graph": {k: v.copy() for k, v in task_graph.items()}
    }
    return {"success": True, "data": {"checkpoint_id": cp_id}, "latency_ms": 50}

def rollback(checkpoint_id: str, checkpoints: dict):
    """Restores world_model and task_graph."""
    if checkpoint_id not in checkpoints:
        return {"success": False, "error": "Checkpoint not found", "latency_ms": 10}
    
    data = checkpoints[checkpoint_id]
    return {"success": True, "data": data, "latency_ms": 200}

def critique(target: str):
    """Scores an output for hallucination with realistic variation."""
    import random
    base = 0.05 if "verified" in target.lower() else 0.15
    # Add noise so hallucination varies every call
    noise = random.uniform(-0.08, 0.20)
    hallucination_rate = max(0.01, min(0.45, base + noise))
    confidence = round(random.uniform(0.72, 0.96), 2)
    return {
        "success": True,
        "data": {
            "hallucination_rate": round(hallucination_rate, 3),
            "confidence": confidence
        },
        "latency_ms": random.randint(180, 450)
    }


def finish(answer: str, grader_func, task_data: dict):
    """Terminates the episode and triggers grader."""
    raw_score = grader_func(answer, task_data)
    score = max(0.01, min(0.99, float(raw_score)))  # clamp at source
    return {"success": True, "data": {"grader_score": score, "answer": answer}, "latency_ms": 50}