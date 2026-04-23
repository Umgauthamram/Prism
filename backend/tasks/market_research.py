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
    # Heuristic rubric
    score = 0.0
    if len(agent_answer.split()) > 100: score += 0.25 # completeness
    if "source:" in agent_answer.lower() or "http" in agent_answer.lower(): score += 0.25 # citations
    if "confidence:" in agent_answer.lower(): score += 0.25 # calibration
    if "competitor" in agent_answer.lower(): score += 0.25 # coverage
    return score
