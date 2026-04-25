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
    score = 0.10  # base score — never returns raw 0.0
    if "join" in agent_answer.lower() or "transform" in agent_answer.lower():
        score += 0.40
    if "group" in agent_answer.lower():
        score += 0.35
    if "select" in agent_answer.lower() and score <= 0.15:
        score += 0.35
    return min(score, 0.90)  # never returns raw 1.0