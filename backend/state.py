from typing import List, Dict, Any, Optional
from .curriculum import CurriculumManager
from .injectors import DomainShiftInjector

# Global Metrics
_reward_curve: List[Dict[str, Any]] = []
_rolling_reward: float = 0.0
_total_episodes: int = 0
_curriculum = CurriculumManager()
_domain_shift = DomainShiftInjector()

# Per-episode reward curves so tournament models don't overwrite each other
_episode_curves: Dict[str, List[Dict[str, Any]]] = {}
_last_active_episode: Optional[str] = None

def reset_metrics():
    global _reward_curve
    _reward_curve = []

def update_metrics(step: int, reward: float, breakdown: Dict[str, Any], terminated: bool, task_domain: str = None, episode_id: str = None):
    global _reward_curve, _rolling_reward, _total_episodes, _last_active_episode
    
    # Track per-episode reward curves
    if episode_id:
        if episode_id not in _episode_curves:
            _episode_curves[episode_id] = []
        _episode_curves[episode_id].append({
            "step": step,
            "total": reward,
            "breakdown": breakdown
        })
        _last_active_episode = episode_id
        # The global _reward_curve always shows the LAST active episode's data
        _reward_curve = _episode_curves[episode_id]
    else:
        # Fallback for non-tournament single-episode usage
        if step == 0:
            _reward_curve = []
        _reward_curve.append({
            "step": step,
            "total": reward,
            "breakdown": breakdown
        })
        if len(_reward_curve) > 200:
            _reward_curve.pop(0)
        
    _rolling_reward = 0.1 * reward + 0.9 * _rolling_reward
    _curriculum.update(reward)
    
    if terminated and task_domain:
        _total_episodes += 1
        _domain_shift.record(task_domain, reward, _total_episodes)
