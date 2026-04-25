from typing import Tuple, Dict

def _clamp(x: float) -> float:
    """Soft clamp to (0.01, 0.99) for numerical stability."""
    return max(0.01, min(0.99, x))

def compute_reward(
    done_count: int,
    prev_done_count: int,
    total_tasks: int,
    orphaned_side_effects: int,
    total_side_effects: int,
    coord_efficiency: float,
    hallucination_rate: float,
    terminal: bool,
    grader_score: float,
    running_count: int = 0,
    prev_running_count: int = 0,
    steps_since_checkpoint: int = 0,
    rubric_dims: Dict[str, float] = None
) -> Tuple[float, Dict[str, float]]:

    total_tasks = max(total_tasks, 1)
    total_side_effects = max(total_side_effects, 1)

    # Compute all components clamped
    weighted_progress = (done_count + 0.5 * running_count)
    prev_weighted     = (prev_done_count + 0.5 * prev_running_count)
    raw_delta = (weighted_progress - prev_weighted) / total_tasks
    progress_delta      = _clamp(raw_delta)
    
    # NEW: Atomic health now reflects 'entropy risk'
    # It decays by 2% per step since the last checkpoint, encouraging proactive state management
    risk_factor = min(0.20, steps_since_checkpoint * 0.02)
    atomic_health       = _clamp(1.0 - (orphaned_side_effects / total_side_effects) - risk_factor)
    
    coord               = _clamp(coord_efficiency)
    hallucination_pen   = _clamp(1.0 - hallucination_rate)
    terminal_bonus      = _clamp(grader_score) if terminal else _clamp(0.0)

    r = (0.40 * progress_delta +
         0.20 * atomic_health +
         0.20 * coord +
         0.10 * hallucination_pen +
         0.10 * terminal_bonus)

    # breakdown uses the SAME clamped values the formula uses
    rubric = rubric_dims or {}
    breakdown = {
        "progress_delta":        round(progress_delta, 4),
        "atomic_health":         round(atomic_health, 4),
        "coord_efficiency":      round(coord, 4),
        "hallucination_penalty": round(hallucination_pen, 4),
        "terminal_bonus":        round(terminal_bonus, 4),
        "rubric_accuracy":       round(rubric.get("Accuracy", 0.0), 4),
        "rubric_reliability":    round(rubric.get("Reliability", 0.0), 4),
        "rubric_efficiency":     round(rubric.get("Efficiency", 0.0), 4)
    }

    return round(float(r), 4), breakdown
