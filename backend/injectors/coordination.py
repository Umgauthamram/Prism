class CoordinationInjector:
    def __init__(self):
        self.total_tokens = 0
        self.useful_tokens = 0
        self.agents = 2

    def reset(self, agents: int):
        self.total_tokens = 0
        self.useful_tokens = 0
        self.agents = agents

    def record_token(self, content: str, useful: bool):
        tokens = len(content.split())
        self.total_tokens += tokens
        if useful:
            self.useful_tokens += tokens

    def efficiency(self) -> float:
        if self.total_tokens == 0:
            return 1.0
        return self.useful_tokens / self.total_tokens
