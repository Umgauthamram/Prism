import random

def generate_task(seed: int) -> dict:
    rng = random.Random(seed)
    bug_types = [
        "off-by-one error", 
        "wrong comparison operator", 
        "missing null check", 
        "bad return statement", 
        "wrong variable name"
    ]
    bug = rng.choice(bug_types)
    
    codebase = {
        "calculate_sum": "def calculate_sum(items):\n    res = 0\n    for i in range(len(items) + 1): # bug here\n        res += items[i]\n    return res"
    }
    
    tests = [
        {"input": [1, 2, 3], "expected_output": 6},
        {"input": [], "expected_output": 0},
        {"input": [10], "expected_output": 10},
    ]
    
    return {
        "code": codebase,
        "tests": tests,
        "bug_report": f"Fail with {bug} in calculate_sum",
        "domain": "debug"
    }

def grade(agent_answer: str, task: dict) -> float:
    # Simulated grading: if answer contains 'range(len(items))', it's fixed
    if "range(len(items))" in agent_answer:
        return 0.95
    return 0.3 # Partial credit for trying
