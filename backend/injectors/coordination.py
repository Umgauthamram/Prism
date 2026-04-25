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

    def record_token(self, content: str, useful: bool) -> None:
        tokens = max(len(str(content).split()), 1)
        self.total_tokens += tokens
        if useful:
            self.useful_tokens += tokens
        else:
            # Overhead counts as 30% useful to prevent efficiency collapse
            self.useful_tokens += max(1, int(tokens * 0.30))
        if self.total_tokens > 0:
            result = self.useful_tokens / self.total_tokens
            self._last_efficiency = max(0.01, min(0.99, result))

    def efficiency(self) -> float:
        if self.total_tokens == 0:
            return self._last_efficiency
        result = self.useful_tokens / self.total_tokens
        result = max(0.01, min(0.99, result))  # clamp at source
        self._last_efficiency = result
        return result