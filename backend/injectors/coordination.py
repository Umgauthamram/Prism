class CoordinationInjector:
    def __init__(self):
        self.total_tokens = 0
        self.useful_tokens = 0
        self.agents = 2
        self._last_efficiency = 0.99

    def reset(self, agents: int):
        self.total_tokens = 0
        self.useful_tokens = 0
        self.agents = agents
        self._last_efficiency = 0.99  # start at max (no waste yet)

    def record_token(self, content: str, useful: bool):
        tokens = len(content.split())
        self.total_tokens += tokens
        if useful:
            self.useful_tokens += tokens

    def efficiency(self) -> float:
        if self.total_tokens == 0:
            return self._last_efficiency  # hold last known value
        result = self.useful_tokens / self.total_tokens
        self._last_efficiency = result  # update last known
        return result
