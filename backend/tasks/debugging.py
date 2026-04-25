import random
from dataclasses import dataclass
from typing import Callable

@dataclass
class BugTemplate:
    name: str
    difficulty: str          # "easy", "medium", "hard"
    buggy_code: str
    fixed_code: str
    bug_report: str
    fix_keywords: list[str]  # words that must appear in answer to get 0.95

BUG_TEMPLATES = [

  # ── EASY (difficulty 1-3) ─────────────────────────────────
  BugTemplate(
    name="off_by_one_range",
    difficulty="easy",
    buggy_code="""def calculate_sum(items):
    res = 0
    for i in range(len(items) + 1):
        res += items[i]
    return res""",
    fixed_code="""def calculate_sum(items):
    res = 0
    for i in range(len(items)):
        res += items[i]
    return res""",
    bug_report="IndexError on non-empty lists. Loop iterates one too many times.",
    fix_keywords=["range(len(items))", "off-by-one"]
  ),

  BugTemplate(
    name="wrong_comparison_operator",
    difficulty="easy",
    buggy_code="""def is_adult(age):
    return age => 18""",
    fixed_code="""def is_adult(age):
    return age >= 18""",
    bug_report="SyntaxError: invalid syntax on comparison operator.",
    fix_keywords=[">=", "greater than or equal"]
  ),

  BugTemplate(
    name="missing_return",
    difficulty="easy",
    buggy_code="""def double(x):
    result = x * 2""",
    fixed_code="""def double(x):
    result = x * 2
    return result""",
    bug_report="Function returns None instead of doubled value.",
    fix_keywords=["return result", "return"]
  ),

  BugTemplate(
    name="wrong_variable_name",
    difficulty="easy",
    buggy_code="""def greet(name):
    message = f"Hello, {nane}!"
    return message""",
    fixed_code="""def greet(name):
    message = f"Hello, {name}!"
    return message""",
    bug_report="NameError: name 'nane' is not defined.",
    fix_keywords=["name", "typo", "NameError"]
  ),

  BugTemplate(
    name="integer_division",
    difficulty="easy",
    buggy_code="""def average(nums):
    return sum(nums) / len(nums) if nums else 0""",
    fixed_code="""def average(nums):
    return sum(nums) / len(nums) if nums else 0.0""",
    bug_report="Returns integer 0 for empty list instead of float 0.0.",
    fix_keywords=["0.0", "float"]
  ),

  BugTemplate(
    name="none_check_missing",
    difficulty="easy",
    buggy_code="""def get_length(s):
    return len(s)""",
    fixed_code="""def get_length(s):
    if s is None:
        return 0
    return len(s)""",
    bug_report="TypeError when None is passed: object of type 'NoneType' has no len().",
    fix_keywords=["None", "is None", "NoneType"]
  ),

  BugTemplate(
    name="string_concatenation_type",
    difficulty="easy",
    buggy_code="""def build_message(count):
    return "Total items: " + count""",
    fixed_code="""def build_message(count):
    return "Total items: " + str(count)""",
    bug_report="TypeError: can only concatenate str to str, not int.",
    fix_keywords=["str(count)", "str(", "convert"]
  ),

  BugTemplate(
    name="list_append_vs_extend",
    difficulty="easy",
    buggy_code="""def merge_lists(a, b):
    result = []
    result.append(a)
    result.append(b)
    return result""",
    fixed_code="""def merge_lists(a, b):
    result = []
    result.extend(a)
    result.extend(b)
    return result""",
    bug_report="Returns list of lists instead of flat merged list.",
    fix_keywords=["extend", "flatten", "append vs extend"]
  ),

  # ── MEDIUM (difficulty 4-6) ──────────────────────────────
  BugTemplate(
    name="mutable_default_argument",
    difficulty="medium",
    buggy_code="""def add_item(item, items=[]):
    items.append(item)
    return items""",
    fixed_code="""def add_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items""",
    bug_report="List accumulates across calls due to mutable default argument.",
    fix_keywords=["None", "mutable default", "items=None"]
  ),

  BugTemplate(
    name="dict_key_error",
    difficulty="medium",
    buggy_code="""def get_user_score(data, user_id):
    return data[user_id]""",
    fixed_code="""def get_user_score(data, user_id):
    return data.get(user_id, 0)""",
    bug_report="KeyError when user_id not in dict. Should return 0 as default.",
    fix_keywords=["get(", ".get(user_id", "default", "KeyError"]
  ),

  BugTemplate(
    name="recursive_no_base_case",
    difficulty="medium",
    buggy_code="""def factorial(n):
    return n * factorial(n - 1)""",
    fixed_code="""def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)""",
    bug_report="RecursionError: maximum recursion depth exceeded. Missing base case.",
    fix_keywords=["base case", "if n <= 1", "n == 0", "RecursionError"]
  ),

  BugTemplate(
    name="float_comparison",
    difficulty="medium",
    buggy_code="""def is_equal(a, b):
    return a == b""",
    fixed_code="""def is_equal(a, b):
    return abs(a - b) < 1e-9""",
    bug_report="Float comparison fails: 0.1 + 0.2 == 0.3 returns False.",
    fix_keywords=["abs(", "epsilon", "1e-9", "float precision"]
  ),

  BugTemplate(
    name="off_by_one_slice",
    difficulty="medium",
    buggy_code="""def last_n(items, n):
    return items[-n+1:]""",
    fixed_code="""def last_n(items, n):
    return items[-n:]""",
    bug_report="Returns n-1 items instead of last n items.",
    fix_keywords=["items[-n:]", "slice", "off-by-one"]
  ),

  BugTemplate(
    name="shallow_copy_mutation",
    difficulty="medium",
    buggy_code="""def add_default(d, key, value):
    new_d = d
    new_d[key] = value
    return new_d""",
    fixed_code="""def add_default(d, key, value):
    new_d = d.copy()
    new_d[key] = value
    return new_d""",
    bug_report="Mutates original dict because assignment creates reference not copy.",
    fix_keywords=["copy()", ".copy()", "shallow copy", "reference"]
  ),

  BugTemplate(
    name="loop_variable_closure",
    difficulty="medium",
    buggy_code="""def make_adders(nums):
    adders = []
    for n in nums:
        adders.append(lambda x: x + n)
    return adders""",
    fixed_code="""def make_adders(nums):
    adders = []
    for n in nums:
        adders.append(lambda x, n=n: x + n)
    return adders""",
    bug_report="All lambdas capture same variable n (last value). Default arg fixes closure.",
    fix_keywords=["n=n", "closure", "default argument", "lambda"]
  ),

  BugTemplate(
    name="string_immutability",
    difficulty="medium",
    buggy_code="""def replace_char(s, idx, char):
    s[idx] = char
    return s""",
    fixed_code="""def replace_char(s, idx, char):
    return s[:idx] + char + s[idx+1:]""",
    bug_report="TypeError: 'str' object does not support item assignment.",
    fix_keywords=["immutable", "slice", "s[:idx]", "concatenation"]
  ),

  BugTemplate(
    name="integer_overflow_check",
    difficulty="medium",
    buggy_code="""def safe_divide(a, b):
    return a / b""",
    fixed_code="""def safe_divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b""",
    bug_report="ZeroDivisionError when b=0. No guard clause.",
    fix_keywords=["b == 0", "ZeroDivisionError", "ValueError", "guard"]
  ),

  # ── HARD (difficulty 7-9) ────────────────────────────────
  BugTemplate(
    name="generator_exhaustion",
    difficulty="hard",
    buggy_code="""def process(data):
    gen = (x * 2 for x in data)
    count = len(list(gen))
    total = sum(gen)
    return total / count""",
    fixed_code="""def process(data):
    doubled = [x * 2 for x in data]
    count = len(doubled)
    total = sum(doubled)
    return total / count if count > 0 else 0""",
    bug_report="Generator exhausted after list(gen). sum(gen) returns 0.",
    fix_keywords=["list comprehension", "exhausted", "generator", "doubled"]
  ),

  BugTemplate(
    name="race_condition_global",
    difficulty="hard",
    buggy_code="""counter = 0
def increment():
    global counter
    temp = counter
    counter = temp + 1""",
    fixed_code="""import threading
counter = 0
lock = threading.Lock()
def increment():
    global counter
    with lock:
        counter += 1""",
    bug_report="Race condition in concurrent access. Counter value unpredictable.",
    fix_keywords=["Lock", "threading", "race condition", "atomic"]
  ),

  BugTemplate(
    name="regex_catastrophic_backtracking",
    difficulty="hard",
    buggy_code="""import re
def validate_email(email):
    pattern = r'^([a-zA-Z0-9]+)*@[a-zA-Z0-9]+\.[a-zA-Z]+$'
    return bool(re.match(pattern, email))""",
    fixed_code="""import re
def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))""",
    bug_report="Catastrophic backtracking on malformed input. Pattern has nested quantifiers.",
    fix_keywords=["backtracking", "ReDoS", "quantifier", "pattern"]
  ),

  BugTemplate(
    name="memory_leak_circular_ref",
    difficulty="hard",
    buggy_code="""class Node:
    def __init__(self, val):
        self.val = val
        self.parent = None
        self.children = []
    def add_child(self, child):
        child.parent = self
        self.children.append(child)""",
    fixed_code="""import weakref
class Node:
    def __init__(self, val):
        self.val = val
        self._parent = None
        self.children = []
    @property
    def parent(self):
        return self._parent() if self._parent else None
    def add_child(self, child):
        child._parent = weakref.ref(self)
        self.children.append(child)""",
    bug_report="Circular reference prevents garbage collection. Use weakref for parent.",
    fix_keywords=["weakref", "circular reference", "garbage collection"]
  ),

  BugTemplate(
    name="async_blocking_call",
    difficulty="hard",
    buggy_code="""import asyncio
import time
async def fetch_data(url):
    time.sleep(2)
    return f"data from {url}" """,
    fixed_code="""import asyncio
async def fetch_data(url):
    await asyncio.sleep(2)
    return f"data from {url}" """,
    bug_report="time.sleep blocks entire event loop. Use asyncio.sleep in async functions.",
    fix_keywords=["asyncio.sleep", "blocking", "event loop", "await"]
  ),

  BugTemplate(
    name="sql_injection",
    difficulty="hard",
    buggy_code="""def get_user(conn, username):
    query = f"SELECT * FROM users WHERE name = '{username}'"
    return conn.execute(query)""",
    fixed_code="""def get_user(conn, username):
    query = "SELECT * FROM users WHERE name = ?"
    return conn.execute(query, (username,))""",
    bug_report="SQL injection vulnerability. User input directly in query string.",
    fix_keywords=["parameterized", "SQL injection", "?", "placeholder"]
  ),

  BugTemplate(
    name="incorrect_complexity",
    difficulty="hard",
    buggy_code="""def find_duplicates(items):
    duplicates = []
    for i in range(len(items)):
        for j in range(i+1, len(items)):
            if items[i] == items[j] and items[i] not in duplicates:
                duplicates.append(items[i])
    return duplicates""",
    fixed_code="""def find_duplicates(items):
    seen = set()
    duplicates = set()
    for item in items:
        if item in seen:
            duplicates.add(item)
        seen.add(item)
    return list(duplicates)""",
    bug_report="O(n³) solution causes timeout on large inputs. Use set for O(n).",
    fix_keywords=["set", "O(n)", "seen", "complexity", "hash"]
  ),
]

# Difficulty ordering for curriculum
DIFFICULTY_ORDER = {
    "easy": 0,
    "medium": 1,
    "hard": 2
}

def generate_task(seed: int) -> dict:
    rng = random.Random(seed)

    # Select difficulty based on seed range for curriculum learning
    if seed % 3 == 0:
        difficulty = "easy"
    elif seed % 3 == 1:
        difficulty = "medium"
    else:
        difficulty = "hard"

    # Filter templates by difficulty
    candidates = [t for t in BUG_TEMPLATES if t.difficulty == difficulty]
    if not candidates:
        candidates = BUG_TEMPLATES

    template = candidates[seed % len(candidates)]

    return {
        "code": {template.name: template.buggy_code},
        "tests": _generate_tests(template, rng),
        "bug_report": template.bug_report,
        "template_name": template.name,
        "difficulty": template.difficulty,
        "fix_keywords": template.fix_keywords,
        "domain": "debug"
    }

def _generate_tests(template: BugTemplate, rng: random.Random) -> list:
    # Generate 3-5 test cases based on template name
    tests = [
        {"input": "basic", "expected_output": "pass"},
        {"input": "edge_case", "expected_output": "pass"},
        {"input": "stress", "expected_output": "pass"},
    ]
    return tests

def grade(agent_answer: str, task: dict) -> float:
    answer_lower = agent_answer.lower()
    fix_keywords = task.get("fix_keywords", [])
    difficulty = task.get("difficulty", "easy")

    # Check how many fix keywords appear in the answer
    matches = sum(
        1 for kw in fix_keywords
        if kw.lower() in answer_lower
    )
    keyword_ratio = matches / max(len(fix_keywords), 1)

    # Base score from keyword matching
    if keyword_ratio >= 0.75:
        base_score = 0.90
    elif keyword_ratio >= 0.50:
        base_score = 0.70
    elif keyword_ratio >= 0.25:
        base_score = 0.50
    else:
        base_score = 0.25

    # Difficulty multiplier — harder problems score higher when correct
    difficulty_bonus = {"easy": 0.0, "medium": 0.03, "hard": 0.05}
    score = base_score + difficulty_bonus.get(difficulty, 0.0)

    return round(min(score, 0.90), 3)
