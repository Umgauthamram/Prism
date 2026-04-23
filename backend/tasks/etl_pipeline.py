import random

def generate_task(seed: int) -> dict:
    rng = random.Random(seed)
    return {
        "input_schemas": {"users": ["id", "name", "email"], "orders": ["id", "user_id", "amount"]},
        "transform_spec": "Join users and orders on user_id, group by name, sum amount",
        "target_schema": ["name", "total_amount"],
        "ground_truth_output": [{"name": "Alice", "total_amount": 150}],
        "domain": "etl"
    }

def grade(agent_answer: str, task: dict) -> float:
    # Simulated execution check
    if "join" in agent_answer.lower() and "group by" in agent_answer.lower():
        return 1.0
    if "select" in agent_answer.lower():
        return 0.5
    return 0.0
