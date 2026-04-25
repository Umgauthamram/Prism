import random


def generate_task(seed: int) -> dict:
    rng = random.Random(seed)
    return {
        "input_schemas": {
            "users": ["id", "name", "email"],
            "orders": ["id", "user_id", "amount"],
        },
        "transform_spec": "Join users and orders on user_id, group by name, sum amount",
        "target_schema": ["name", "total_amount"],
        "ground_truth_output": [{"name": "Alice", "total_amount": 150}],
        "domain": "etl",
    }


def grade(agent_answer: str, task: dict) -> float:
    """Multi-factor grading for ETL pipeline domain."""
    score = 0.10  # base score — never returns raw 0.0
    answer_lower = agent_answer.lower()

    # Core transformation awareness
    if "join" in answer_lower:
        score += 0.20
    if "group" in answer_lower:
        score += 0.20

    # Target schema columns mentioned
    target_schema = task.get("target_schema", [])
    for col in target_schema:
        if col.lower() in answer_lower:
            score += 0.08

    # Transform / map awareness
    if "transform" in answer_lower or "map" in answer_lower:
        score += 0.10

    # SQL-like keywords
    sql_keywords = ["select", "from", "where", "insert", "aggregate"]
    if any(kw in answer_lower for kw in sql_keywords):
        score += 0.10

    # Non-trivial answer
    if len(agent_answer) > 30:
        score += 0.05

    return min(score, 0.90)  # never returns raw 1.0