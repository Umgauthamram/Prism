"""
In-Context Learning (ICL) Trainer for prism RL Environment.

When a model scores below threshold, this module:
1. Analyses the diagnostic feedback from the failed episode
2. Builds an improved system prompt that includes the failures
3. Re-runs the episode with the enriched prompt
4. Compares before/after scores to show improvement

This is Zero-Shot RL via prompt engineering — valid and impressive.
The environment creates the training signal; the LLM uses it.
"""

from typing import Optional, List, Dict
import json
import time

# ICL prompt templates per domain and failure pattern
ICL_IMPROVEMENTS = {

    "debug": {
        "low_progress": """
[ANALYSIS: TASK GRAPH STALL]
Your last attempt failed to advance nodes from 'pending' to 'done'.
CORRECTION: 
- After research_web, immediately use assign(task_done='analyse_bug') or similar.
- Do not spend more than 3 steps on research. 
- CRITICAL: Use the 'finish' tool immediately after 'verify' is marked 'done'.
- STEP EFFICIENCY: Every step where you don't move a task from 'pending' to 'done' is a WASTED step. You must finish the graph in under 15 steps total.
""",
        "low_atomic": """
LEARNING FROM PREVIOUS ATTEMPT:
Your last attempt caused orphaned side effects (atomic_health was low).
CORRECTION: ALWAYS call db_preflight(spec) before db_commit.
ALWAYS call checkpoint() after every 3 successful steps.
If Injector 2 fires, call rollback() immediately before any further writes.
""",
        "high_hallucination": """
LEARNING FROM PREVIOUS ATTEMPT:
Your last attempt had high hallucination rate.
CORRECTION: Every claim in the world_model must be verifiable.
The bug fix must directly address the bug_report keywords.
Do not invent error messages or stack traces that were not in the input.
""",
        "low_grader": """
LEARNING FROM PREVIOUS ATTEMPT:
Your last finish() answer was graded low.
CORRECTION: The answer MUST contain the fix_keywords from the task.
For debugging tasks: state the exact code change made (e.g. 'range(len(items)+1) -> range(len(items))').
Include: what the bug was, what you changed, and why it fixes it.
""",
    },

    "market_research": {
        "low_progress": """
LEARNING FROM PREVIOUS ATTEMPT:
Your last attempt failed to advance the research workflow.
CORRECTION: 
1. Step 1 must identify at least 5 competitors.
2. Step 2 must gather data on each across ALL key_dimensions.
3. Step 3 must score each dimension and assign confidence levels.
4. CRITICAL: DO NOT call finish() until EVERY node in the task_graph is marked as 'done'.
5. Do not skip directly to finish without covering all 5 dimensions.
""",
        "low_grader": """
LEARNING FROM PREVIOUS ATTEMPT:
Your last finish() answer was graded low for market_research.
CORRECTION: The answer MUST contain ALL of these:
- 'competitor' (name at least 5)
- 'source:' followed by a URL or publication name
- 'confidence:' with a level (high/medium/low)
- Coverage of the key_dimensions from the task
Structure: "1. [Competitor]: [dimension analysis]. source: [URL]. confidence: [level]."
""",
        "high_hallucination": """
LEARNING FROM PREVIOUS ATTEMPT:
Your Critic flagged hallucinated claims.
CORRECTION: Do not fabricate market share percentages.
Use phrases like 'estimated market share based on [source]'.
Every claim about pricing, features, or positioning needs a source.
Unverified claims get flagged and reduce your hallucination_penalty score.
""",
        "low_atomic": """
LEARNING FROM PREVIOUS ATTEMPT:
Your research pipeline caused orphaned state updates (atomic_health was low).
CORRECTION: Checkpoint after each competitor analysis round.
Use db_preflight before committing market data to prevent partial writes.
""",
    },

    "etl": {
        "low_progress": """
LEARNING FROM PREVIOUS ATTEMPT:
Your last attempt did not advance the ETL pipeline construction.
CORRECTION: 
1. Step 1 MUST parse input_schemas and identify all columns.
2. Step 2 MUST write the transform with the exact operation specified.
3. CRITICAL: DO NOT call finish() until EVERY node in the task_graph is marked as 'done'.
4. The transform spec tells you exactly what to do — follow it literally.
""",
        "low_grader": """
LEARNING FROM PREVIOUS ATTEMPT:
Your last finish() answer was graded low for the ETL task.
CORRECTION: The answer MUST contain the solution_keywords from the task.
For JOIN tasks: say "join [table1] and [table2] on [key]".
For GROUP BY: say "group by [column], aggregate [function]".
For WINDOW: say "partition by [column] over [window_spec]".
Schema must exactly match target_schema columns — no extras, no missing.
""",
        "low_atomic": """
LEARNING FROM PREVIOUS ATTEMPT:
Your ETL pipeline caused orphaned DB writes (atomic_health was low).
CORRECTION: Register every db_commit with db_preflight first.
For ETL bulk writes: preflight the entire batch before starting.
If a write fails, the preflight inverse operation will clean up partial state.
""",
        "high_hallucination": """
LEARNING FROM PREVIOUS ATTEMPT:
Your ETL pipeline used columns that don't exist in the input schema.
CORRECTION: Only reference column names that appear in input_schemas.
Verify every column reference against the actual schema before using it.
""",
    },
}


def build_icl_prompt_injection(
    diagnostic_history: List[str],
    domain: str,
    breakdown_history: List[dict],
) -> str:
    """
    Builds the ICL injection text based on failure patterns.
    This gets prepended to the system prompt for the next episode.
    """
    if not diagnostic_history:
        return ""

    # Identify which patterns failed
    avg_pd = sum(b.get("progress_delta", 0.5) for b in breakdown_history) / max(len(breakdown_history), 1)
    avg_ah = sum(b.get("atomic_health", 0.5) for b in breakdown_history) / max(len(breakdown_history), 1)
    avg_hp = sum(b.get("hallucination_penalty", 0.5) for b in breakdown_history) / max(len(breakdown_history), 1)
    last_tb = breakdown_history[-1].get("terminal_bonus", 0.01) if breakdown_history else 0.01

    domain_improvements = ICL_IMPROVEMENTS.get(domain, ICL_IMPROVEMENTS["debug"])
    injections = []

    if avg_pd < 0.08:
        inj = domain_improvements.get("low_progress", "")
        if inj:
            injections.append(inj)
    if avg_ah < 0.65:
        inj = domain_improvements.get("low_atomic", "")
        if inj:
            injections.append(inj)
    if avg_hp < 0.75:
        inj = domain_improvements.get("high_hallucination", "")
        if inj:
            injections.append(inj)
    if last_tb < 0.40:
        inj = domain_improvements.get("low_grader", "")
        if inj:
            injections.append(inj)

    if not injections:
        return ""

    last_diagnostic = diagnostic_history[-1] if diagnostic_history else ""

    return f"""
╔══════════════════════════════════════════════╗
║  IN-CONTEXT LEARNING — PREVIOUS RUN ANALYSIS ║
╚══════════════════════════════════════════════╝

WHAT WENT WRONG IN YOUR LAST ATTEMPT:
{last_diagnostic}

LEARNING FROM PREVIOUS ATTEMPT (CORRECTIONS):
{''.join(injections)}

PERFORMANCE BOOSTING ACTIVE:
This run is being monitored for ICL optimization. 
Your objective is to achieve a 1.5x score improvement over the baseline.
Focus on sequential task completion and high-quality final answer structure.
"""


def get_improvement_plan(
    diagnostic_history: List[str],
    breakdown_history: List[dict],
    domain: str,
    model_name: str,
    prev_score: float,
) -> str:
    """
    Returns a human-readable improvement plan shown to the user
    in the dashboard before they click 'Start Training'.
    """
    avg_pd = sum(b.get("progress_delta", 0.5) for b in breakdown_history) / max(len(breakdown_history), 1)
    avg_ah = sum(b.get("atomic_health", 0.5) for b in breakdown_history) / max(len(breakdown_history), 1)
    avg_hp = sum(b.get("hallucination_penalty", 0.5) for b in breakdown_history) / max(len(breakdown_history), 1)
    last_tb = breakdown_history[-1].get("terminal_bonus", 0.01) if breakdown_history else 0.01

    weaknesses = []
    fixes = []

    if avg_pd < 0.08:
        weaknesses.append(f"Task graph not advancing (progress_delta avg: {avg_pd:.3f})")
        fixes.append("Inject step-by-step task advancement instructions into system prompt")
    if avg_ah < 0.65:
        weaknesses.append(f"Transaction discipline failing (atomic_health avg: {avg_ah:.3f})")
        fixes.append("Inject checkpoint/preflight/rollback protocol reminders")
    if avg_hp < 0.75:
        weaknesses.append(f"Hallucination detected (hallucination_penalty avg: {avg_hp:.3f})")
        fixes.append("Inject claim verification requirements into system prompt")
    if last_tb < 0.40:
        weaknesses.append(f"Final answer quality low (terminal_bonus: {last_tb:.3f})")
        fixes.append("Inject domain-specific answer structure requirements")

    if not weaknesses:
        return f"{model_name} is already performing well (score: {prev_score:.4f}). No training needed."

    weakness_lines = "\n".join(f"  * {w}" for w in weaknesses)
    fix_lines = "\n".join(f"  > {f}" for f in fixes)

    plan = (
        f"MODEL: {model_name}\n"
        f"DOMAIN: {domain}\n"
        f"PREVIOUS SCORE: {prev_score:.4f}\n"
        f"TARGET SCORE: {min(prev_score + 0.15, 3.50):.4f}\n"
        f"\n"
        f"WEAKNESSES IDENTIFIED:\n{weakness_lines}\n"
        f"\n"
        f"WHAT WE WILL INJECT INTO THE MODEL'S PROMPT:\n{fix_lines}\n"
        f"\n"
        f"METHOD: In-Context Learning (ICL) / Zero-Shot RL\n"
        f"The diagnostic feedback from your failed episode is injected\n"
        f"directly into the model's system prompt for the next run.\n"
        f"No gradient updates. No fine-tuning. The model 'learns' from\n"
        f"the feedback in-context.\n"
        f"\n"
        f"WARNING: This improvement only applies within this session.\n"
        f"The model's weights are not updated. Closing the browser or\n"
        f"switching episodes resets all learned behavior."
    )
    return plan
