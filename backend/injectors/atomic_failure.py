import random

class AtomicFailureInjector:
    def __init__(self):
        self.failure_rate = 0.0

    def reset(self, failure_rate: float):
        """Store failure rate for this episode: 0.0, 0.2, or 0.5."""
        self.failure_rate = failure_rate

    def should_fail(self) -> bool:
        """Returns True with probability = failure_rate."""
        if self.failure_rate <= 0:
            return False
        return random.random() < self.failure_rate
