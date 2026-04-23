STAGES = [
    {"stage": 0, "failure_rate": 0.0, "agents": 2, "domains": ["debug"], "threshold": 0.45},
    {"stage": 1, "failure_rate": 0.2, "agents": 2, "domains": ["debug", "etl"], "threshold": 0.55},
    {"stage": 2, "failure_rate": 0.2, "agents": 4, "domains": ["debug", "etl", "market_research"], "threshold": 0.65},
    {"stage": 3, "failure_rate": 0.5, "agents": 8, "domains": ["debug", "etl", "market_research"], "threshold": 0.75},
]

class CurriculumManager:
    def __init__(self):
        self.stage = 0
        self.reward_history = []
        self.ema_reward = 0.0
        self.alpha = 0.1
        self.window_size = 20

    def update(self, reward: float) -> int:
        if not self.reward_history:
            self.ema_reward = reward
        else:
            self.ema_reward = self.alpha * reward + (1 - self.alpha) * self.ema_reward
        
        self.reward_history.append(reward)
        if len(self.reward_history) > self.window_size:
            self.reward_history.pop(0)

        current_stage_config = STAGES[self.stage]
        if self.ema_reward > current_stage_config["threshold"] and self.stage < len(STAGES) - 1:
            self.stage += 1
            
        return self.stage

    @property
    def threshold(self) -> float:
        return STAGES[self.stage]["threshold"]

    @property
    def config(self) -> dict:
        stage_cfg = STAGES[self.stage]
        return {
            "failure_rate": stage_cfg["failure_rate"],
            "agents": stage_cfg["agents"],
            "task_domain": stage_cfg["domains"][0]
        }

    def get_history(self) -> list:
        return STAGES[:self.stage + 1]
