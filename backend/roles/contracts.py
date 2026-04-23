ROLES = ["Planner", "Researcher", "Coder", "Critic", "Synthesizer"]

ROLE_CONTRACTS = {
    "Planner": ["decompose", "assign", "replan", "checkpoint", "rollback"],
    "Researcher": ["research_web", "read_schema", "write_world"],
    "Coder": ["write_code", "run_tests", "db_preflight", "db_commit"],
    "Critic": ["critique", "flag_hallucination", "request_replan"],
    "Synthesizer": ["merge", "finish", "flag_gap"],
}
