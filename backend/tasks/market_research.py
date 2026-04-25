import random


def generate_task(seed: int) -> dict:
    rng = random.Random(seed)
    banks = [
        ("Notion", "productivity"),
        ("Linear", "project management"),
        ("Snowflake", "data warehousing"),
        ("Datadog", "observability"),
        ("Vercel", "frontend deployment"),
        ("Supabase", "backend-as-a-service"),
    ]
    company, category = rng.choice(banks)
    return {
        "company": company,
        "category": category,
        "domain": "market_research",
    }


def grade(agent_answer: str, task: dict) -> float:
    """Multi-factor grading for market research domain."""
    score = 0.10  # base score — never returns raw 0.0
    answer_lower = agent_answer.lower()

    # Length / depth of analysis
    word_count = len(agent_answer.split())
    if word_count > 50:
        score += 0.10
    if word_count > 100:
        score += 0.05

    # Mentions the target company?
    company = task.get("company", "").lower()
    if company and company in answer_lower:
        score += 0.15

    # Mentions the category?
    category = task.get("category", "").lower()
    if category and category in answer_lower:
        score += 0.10

    # Citation / source awareness
    if "source:" in answer_lower or "http" in answer_lower:
        score += 0.15

    # Confidence calibration
    if "confidence:" in answer_lower:
        score += 0.10

    # Competitor analysis
    if "competitor" in answer_lower:
        score += 0.10

    # Structured format (numbered lists, bullets)
    if any(marker in agent_answer for marker in ["1.", "- ", "• ", "* "]):
        score += 0.10

    return min(score, 0.90)  # never returns raw 1.0
