import random

MARKET_TASKS = [
    # (company, category, key_dimensions, min_competitors)
    ("Notion",        "productivity software",       ["pricing", "collaboration", "integrations"], 5),
    ("Linear",        "project management",          ["speed", "developer_focus", "roadmap"],      5),
    ("Snowflake",     "cloud data warehousing",      ["cost", "performance", "ecosystem"],         4),
    ("Datadog",       "observability",               ["apm", "logs", "pricing"],                   5),
    ("Figma",         "design tools",                ["collaboration", "prototyping", "plugins"],   4),
    ("Vercel",        "frontend deployment",         ["dx", "pricing", "edge_network"],            4),
    ("PlanetScale",   "database-as-a-service",       ["branching", "scaling", "mysql_compat"],     3),
    ("Retool",        "internal tools",              ["connectors", "no_code", "pricing"],         4),
    ("Segment",       "customer data platform",      ["integrations", "privacy", "real_time"],     4),
    ("Amplitude",     "product analytics",           ["funnels", "retention", "pricing"],          4),
    ("Sentry",        "error monitoring",            ["alerting", "source_maps", "pricing"],       4),
    ("LaunchDarkly",  "feature flags",               ["targeting", "experimentation", "sdk"],      3),
    ("Contentful",    "headless CMS",                ["api", "localization", "pricing"],           4),
    ("Algolia",       "search-as-a-service",         ["relevance", "speed", "pricing"],            4),
    ("Stripe",        "payment infrastructure",      ["docs", "fraud", "global"],                  4),
    ("Twilio",        "communications API",          ["sms", "voice", "pricing"],                  4),
    ("Auth0",         "identity platform",           ["mfa", "compliance", "pricing"],             3),
    ("Supabase",      "backend-as-a-service",        ["postgres", "realtime", "storage"],          4),
    ("Grafana",       "observability dashboards",    ["datasources", "alerting", "open_source"],   4),
    ("dbt",           "data transformation",         ["lineage", "testing", "cloud"],              3),
    ("Airbyte",       "data integration",            ["connectors", "open_source", "cloud"],       4),
    ("Monte Carlo",   "data observability",          ["ml_detection", "lineage", "pricing"],       3),
    ("Weights & Biases","ML experiment tracking",   ["visualizations", "artifacts", "pricing"],   4),
    ("Modal",         "serverless GPU compute",      ["cold_start", "pricing", "sdk"],             3),
    ("Hugging Face",  "ML model hub",                ["models", "spaces", "enterprise"],           3),
]

def generate_task(seed: int) -> dict:
    rng = random.Random(seed)
    idx = seed % len(MARKET_TASKS)
    company, category, dimensions, min_competitors = MARKET_TASKS[idx]

    # Vary which dimensions are weighted most for this seed
    weighted_dim = rng.choice(dimensions)

    return {
        "company": company,
        "category": category,
        "key_dimensions": dimensions,
        "weighted_dimension": weighted_dim,
        "min_competitors": min_competitors,
        "domain": "market_research"
    }

def grade(agent_answer: str, task: dict) -> float:
    answer_lower = agent_answer.lower()
    score = 0.10  # base

    # Completeness: enough words
    word_count = len(agent_answer.split())
    if word_count > 80:  score += 0.20
    elif word_count > 40: score += 0.10

    # Citations
    if any(kw in answer_lower for kw in ["source:", "http", "according to", "cited"]):
        score += 0.15

    # Confidence calibration
    if any(kw in answer_lower for kw in ["confidence:", "high confidence", "estimated"]):
        score += 0.15

    # Competitor coverage
    if "competitor" in answer_lower or "vs" in answer_lower:
        score += 0.15

    # Key dimensions mentioned
    dims_covered = sum(
        1 for d in task.get("key_dimensions", [])
        if d.replace("_", " ") in answer_lower or d in answer_lower
    )
    dim_ratio = dims_covered / max(len(task.get("key_dimensions", [])), 1)
    score += dim_ratio * 0.15

    return round(min(score, 0.90), 3)
