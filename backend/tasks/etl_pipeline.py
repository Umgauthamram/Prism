import random
from dataclasses import dataclass

@dataclass
class ETLTemplate:
    name: str
    difficulty: str
    input_schemas: dict
    transform_spec: str
    target_schema: list
    solution_keywords: list[str]

ETL_TEMPLATES = [
  # ── EASY ──────────────────────────────────────────────────
  ETLTemplate("simple_join", "easy",
    {"users": ["id","name","email"], "orders": ["id","user_id","amount"]},
    "Join users and orders on user_id, return name and amount",
    ["name", "amount"],
    ["join", "user_id", "inner join"]),

  ETLTemplate("filter_threshold", "easy",
    {"transactions": ["id","amount","status"]},
    "Filter transactions where amount > 100 and status = 'completed'",
    ["id", "amount"],
    ["filter", "where", "amount > 100"]),

  ETLTemplate("group_sum", "easy",
    {"sales": ["region","product","revenue"]},
    "Group by region, sum revenue",
    ["region", "total_revenue"],
    ["group by", "sum", "aggregate"]),

  ETLTemplate("rename_columns", "easy",
    {"raw": ["usr_id","usr_nm","eml"]},
    "Rename: usr_id→user_id, usr_nm→username, eml→email",
    ["user_id","username","email"],
    ["rename", "alias", "as"]),

  ETLTemplate("deduplicate", "easy",
    {"logs": ["user_id","event","timestamp"]},
    "Deduplicate by user_id keeping most recent timestamp",
    ["user_id","event","timestamp"],
    ["deduplicate", "distinct", "max(timestamp)"]),

  ETLTemplate("type_cast", "easy",
    {"raw_data": ["id","created_at","score"]},
    "Cast created_at to DATE, score to FLOAT",
    ["id","created_at","score"],
    ["cast", "to_date", "float", "convert"]),

  ETLTemplate("null_fill", "easy",
    {"products": ["id","name","price","discount"]},
    "Replace NULL discount with 0.0",
    ["id","name","price","discount"],
    ["coalesce", "fillna", "null", "default"]),

  ETLTemplate("sort_limit", "easy",
    {"products": ["id","name","sales_count"]},
    "Top 10 products by sales_count descending",
    ["id","name","sales_count"],
    ["order by", "limit", "top", "sort desc"]),

  # ── MEDIUM ────────────────────────────────────────────────
  ETLTemplate("multi_join", "medium",
    {"users":["id","name"],"orders":["id","user_id","product_id"],
     "products":["id","name","price"]},
    "Join all three tables, return user_name, product_name, total spent",
    ["user_name","product_name","total_spent"],
    ["join", "three tables", "multiple join"]),

  ETLTemplate("conditional_column", "medium",
    {"orders": ["id","amount","country"]},
    "Add tax column: 20% if country=UK, 10% if country=US, else 0",
    ["id","amount","country","tax"],
    ["case when", "conditional", "tax"]),

  ETLTemplate("window_function", "medium",
    {"sales": ["rep_id","month","revenue"]},
    "Add running total revenue per rep using window function",
    ["rep_id","month","revenue","running_total"],
    ["window", "over", "partition by", "cumsum"]),

  ETLTemplate("pivot_table", "medium",
    {"surveys": ["user_id","question","answer"]},
    "Pivot questions as columns, each user a row",
    ["user_id","q1","q2","q3"],
    ["pivot", "transpose", "column"]),

  ETLTemplate("string_extract", "medium",
    {"urls": ["id","url"]},
    "Extract domain from url, strip www prefix",
    ["id","domain"],
    ["extract", "split", "substring", "regex"]),

  ETLTemplate("date_diff", "medium",
    {"subscriptions": ["user_id","start_date","end_date"]},
    "Add duration_days column as end_date minus start_date",
    ["user_id","start_date","end_date","duration_days"],
    ["datediff", "date difference", "duration"]),

  ETLTemplate("nested_json_flatten", "medium",
    {"events": ["id","payload"]},
    "Flatten JSON payload column: extract user_id, action, timestamp",
    ["id","user_id","action","timestamp"],
    ["flatten", "json", "parse", "extract"]),

  ETLTemplate("anti_join", "medium",
    {"all_users":["id","email"],"churned":["user_id"]},
    "Return users who have NOT churned (anti-join)",
    ["id","email"],
    ["anti join", "not in", "left join where null"]),

  # ── HARD ──────────────────────────────────────────────────
  ETLTemplate("slowly_changing_dimension", "hard",
    {"current":["id","value","updated_at"],
     "history":["id","value","valid_from","valid_to"]},
    "SCD Type 2: track full history with valid_from/valid_to dates",
    ["id","value","valid_from","valid_to","is_current"],
    ["SCD", "type 2", "history", "slowly changing"]),

  ETLTemplate("sessionization", "hard",
    {"events": ["user_id","event_time","page"]},
    "Group events into sessions (30 min gap = new session)",
    ["user_id","session_id","start_time","end_time","page_count"],
    ["session", "gap", "lag", "30 minutes"]),

  ETLTemplate("graph_traversal_etl", "hard",
    {"edges": ["from_id","to_id","weight"]},
    "Find all reachable nodes from node_id=1 within 2 hops",
    ["node_id","hop_count","path"],
    ["graph", "traversal", "recursive", "CTE"]),

  ETLTemplate("fuzzy_dedup", "hard",
    {"contacts": ["id","name","email","phone"]},
    "Deduplicate contacts using fuzzy name matching (Levenshtein<3)",
    ["canonical_id","name","email","phone","duplicate_count"],
    ["fuzzy", "levenshtein", "similarity", "dedup"]),

  ETLTemplate("fuzzy_dedup", "hard",
    {"contacts": ["id","name","email","phone"]},
    "Deduplicate contacts using fuzzy name matching (Levenshtein<3)",
    ["canonical_id","name","email","phone","duplicate_count"],
    ["fuzzy", "levenshtein", "similarity", "dedup"]),

  ETLTemplate("time_series_fill", "hard",
    {"metrics": ["device_id","timestamp","value"]},
    "Fill gaps in time series with linear interpolation",
    ["device_id","timestamp","value","interpolated"],
    ["interpolat", "fill", "time series", "linear"]),

  ETLTemplate("ml_feature_pipeline", "hard",
    {"raw": ["user_id","purchase_history","browse_history","demographics"]},
    "Extract: recency, frequency, monetary value, top category",
    ["user_id","recency_days","frequency","monetary","top_category"],
    ["feature", "RFM", "recency", "frequency", "monetary"]),

  ETLTemplate("streaming_aggregation", "hard",
    {"stream": ["event_id","user_id","event_type","ts"]},
    "5-minute tumbling window count of events per user per type",
    ["window_start","window_end","user_id","event_type","count"],
    ["tumbling window", "streaming", "5 minute", "window"]),

  ETLTemplate("cross_database_merge", "hard",
    {"postgres_users":["id","email"],"mysql_orders":["order_id","email","total"]},
    "Merge across two source systems matching on email, handle conflicts",
    ["unified_id","email","total_orders","conflict_flag"],
    ["merge", "conflict", "cross-database", "resolution"]),

  ETLTemplate("anomaly_flagging", "hard",
    {"metrics": ["ts","metric_name","value"]},
    "Flag values > 3 standard deviations from rolling 24h mean",
    ["ts","metric_name","value","rolling_mean","is_anomaly"],
    ["anomaly", "standard deviation", "rolling", "z-score"]),
]

def generate_task(seed: int) -> dict:
    rng = random.Random(seed)
    idx = seed % len(ETL_TEMPLATES)
    t = ETL_TEMPLATES[idx]
    return {
        "input_schemas": t.input_schemas,
        "transform_spec": t.transform_spec,
        "target_schema": t.target_schema,
        "template_name": t.name,
        "difficulty": t.difficulty,
        "solution_keywords": t.solution_keywords,
        "ground_truth_output": [{"example": "row1"}],
        "domain": "etl"
    }

def grade(agent_answer: str, task: dict) -> float:
    answer_lower = agent_answer.lower()
    keywords = task.get("solution_keywords", [])
    difficulty = task.get("difficulty", "easy")

    matches = sum(1 for kw in keywords if kw.lower() in answer_lower)
    keyword_ratio = matches / max(len(keywords), 1)

    if keyword_ratio >= 0.75:   base_score = 0.88
    elif keyword_ratio >= 0.50: base_score = 0.68
    elif keyword_ratio >= 0.25: base_score = 0.48
    else:                        base_score = 0.20

    difficulty_bonus = {"easy": 0.0, "medium": 0.02, "hard": 0.04}
    score = base_score + difficulty_bonus.get(difficulty, 0.0)

    return round(min(score, 0.90), 3)