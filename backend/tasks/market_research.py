import random

def generate_task(seed: int) -> dict:
    rng = random.Random(seed)
    banks = [
        ("Notion", "productivity"),
        ("Linear", "project management"),
        ("Snowflake", "data warehousing"),
        ("Datadog", "observability")
    ]
    company, category = rng.choice(banks)
    return {
        "company": company,
        "category": category,
        "domain": "market_research"
    }


def grade(agent_answer: str, task: dict) -> float:
    score = 0.10  # base score — never returns raw 0.0
    if len(agent_answer.split()) > 30: score += 0.20
    if "source:" in agent_answer.lower() or "http" in agent_answer.lower(): score += 0.20
    if "confidence:" in agent_answer.lower(): score += 0.20
    if "competitor" in agent_answer.lower(): score += 0.20
    return min(score, 0.90)  # never returns raw 1.0
