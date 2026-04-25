import random

CODEBASES = [
    {
        "name": "calculate_sum",
        "buggy": (
            "def calculate_sum(items):\n"
            "    res = 0\n"
            "    for i in range(len(items) + 1):  # bug here\n"
            "        res += items[i]\n"
            "    return res"
        ),
        "fix_pattern": "range(len(items))",
        "tests": [
            {"input": [1, 2, 3], "expected_output": 6},
            {"input": [], "expected_output": 0},
            {"input": [10], "expected_output": 10},
        ],
    },
    {
        "name": "find_max",
        "buggy": (
            "def find_max(lst):\n"
            "    if len(lst) == 0:\n"
            "        return None\n"
            "    mx = lst[0]\n"
            "    for i in range(1, len(lst)):\n"
            "        if lst[i] > mx:\n"
            "            mx = lst[i]\n"
            "    return mx + 1  # bug: spurious +1"
        ),
        "fix_pattern": "return mx",
        "tests": [
            {"input": [3, 1, 4], "expected_output": 4},
            {"input": [7], "expected_output": 7},
        ],
    },
    {
        "name": "flatten_list",
        "buggy": (
            "def flatten(nested):\n"
            "    result = []\n"
            "    for item in nested:\n"
            "        if isinstance(item, list):\n"
            "            result.append(item)  # bug: should extend\n"
            "        else:\n"
            "            result.append(item)\n"
            "    return result"
        ),
        "fix_pattern": "result.extend",
        "tests": [
            {"input": [[1, 2], [3]], "expected_output": [1, 2, 3]},
        ],
    },
    {
        "name": "count_words",
        "buggy": (
            "def count_words(text):\n"
            "    words = text.split(' ')\n"
            "    counts = {}\n"
            "    for w in words:\n"
            "        counts[w] = counts.get(w, 0)  # bug: missing +1\n"
            "    return counts"
        ),
        "fix_pattern": "counts.get(w, 0) + 1",
        "tests": [
            {"input": "a b a", "expected_output": {"a": 2, "b": 1}},
        ],
    },
]


def generate_task(seed: int) -> dict:
    rng = random.Random(seed)
    codebase = rng.choice(CODEBASES)
    bug_types = [
        "off-by-one error",
        "wrong comparison operator",
        "missing null check",
        "bad return statement",
        "wrong variable name",
    ]
    bug = rng.choice(bug_types)

    return {
        "code": {codebase["name"]: codebase["buggy"]},
        "tests": codebase["tests"],
        "bug_report": f"Fail with {bug} in {codebase['name']}",
        "fix_pattern": codebase["fix_pattern"],
        "function_name": codebase["name"],
        "domain": "debug",
    }


def grade(agent_answer: str, task: dict) -> float:
    """Multi-factor grading for debugging domain."""
    score = 0.10  # base score — never returns raw 0.0
    answer_lower = agent_answer.lower()

    # Primary: does the answer contain the correct fix pattern?
    fix_pattern = task.get("fix_pattern", "range(len(items))")
    if fix_pattern.lower() in answer_lower:
        score += 0.30

    # Secondary: does the answer mention the function being fixed?
    func_name = task.get("function_name", "calculate_sum")
    if func_name in answer_lower:
        score += 0.15

    # Structural: contains a function definition?
    if "def " in agent_answer:
        score += 0.15

    # Testing awareness: mentions tests or assertions?
    if "test" in answer_lower or "assert" in answer_lower:
        score += 0.10

    # Effort: non-trivial answer length?
    if len(agent_answer) > 50:
        score += 0.10

    return min(score, 0.90)  # never returns raw 1.0
