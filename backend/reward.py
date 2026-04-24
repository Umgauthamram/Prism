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
    grader_score: float
) -> Tuple[float, Dict[str, float]]:
    
    # progress_delta (0.40)
    progress_delta = (done_count - prev_done_count) / total_tasks if total_tasks > 0 else 0
    
    # atomic_health (0.20)
    atomic_health = 1.0 - (orphaned_side_effects / total_side_effects) if total_side_effects > 0 else 1.0
    
    # coord_efficiency (0.20) - passed directly from injector
    
    # hallucination_penalty (0.10)
    hallucination_penalty = 1.0 - hallucination_rate
    
    # terminal_bonus (0.10)
    terminal_bonus = grader_score if terminal else 0.0
    
    # Formula
    r = (0.40 * _clamp(progress_delta) + 
         0.20 * _clamp(atomic_health) + 
         0.20 * _clamp(coord_efficiency) + 
         0.10 * _clamp(hallucination_penalty) + 
         0.10 * _clamp(terminal_bonus))
    
    breakdown = {
        "progress_delta": round(float(progress_delta), 4),
        "atomic_health": round(float(atomic_health), 4),
        "coord_efficiency": round(float(coord_efficiency), 4),
        "hallucination_penalty": round(float(hallucination_penalty), 4),
        "terminal_bonus": round(float(terminal_bonus), 4)
    }
    
    return round(float(r), 4), breakdown
