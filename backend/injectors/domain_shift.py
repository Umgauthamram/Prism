from dataclasses import dataclass
from typing import List, Dict

@dataclass
class TransferPoint:
    eval_episode: int
    domain: str
    score: float

class DomainShiftInjector:
    def __init__(self):
        self.history: Dict[str, List[float]] = {}
        self.transfer_points: List[TransferPoint] = []
        self.current_episode = 0

    def record(self, domain: str, score: float, episode: int):
        if domain not in self.history:
            self.history[domain] = []
        self.history[domain].append(score)
        self.current_episode = episode
        
        # Log transfer point
        self.transfer_points.append(TransferPoint(
            eval_episode=episode,
            domain=domain,
            score=score
        ))

    def get_scores(self) -> List[dict]:
        return [
            {"eval_episode": p.eval_episode, "domain": p.domain, "score": p.score}
            for p in self.transfer_points
        ]
