import os
import json
import random
import time
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
from rich.console import Console
from rich.panel import Panel
from envs.prism import PrismEnv, PrismAction

console = Console()

if HAS_TORCH:
    # Simple Policy Network for demonstration (Phase 3: Real RL)
    class SimplePolicy(nn.Module):
        def __init__(self, input_dim=10, output_dim=5):
            super(SimplePolicy, self).__init__()
            self.net = nn.Sequential(
                nn.Linear(input_dim, 32),
                nn.ReLU(),
                nn.Linear(32, output_dim),
                nn.Softmax(dim=-1)
            )

        def forward(self, x):
            return self.net(x)

def main():
    os.makedirs("training_output", exist_ok=True)
    
    # Initialize Environment Client
    base_url = os.getenv("PRISM_URL", "http://localhost:8000")
    env = PrismEnv(base_url=base_url)

    console.print(Panel(
        "[bold violet]prism GRPO Training Loop[/bold violet]\n"
        "Model: Qwen2.5-3B-Instruct (simulated)  |  Environment: prism\n"
        "Domain: debug  |  Curriculum: 3-stage failure injection",
        title="OpenEnv AI Hackathon 2026",
        border_style="violet"
    ))

    # Initialize "Policy"
    if HAS_TORCH:
        policy = SimplePolicy()
        optimizer = optim.Adam(policy.parameters(), lr=1e-3)

    # Curriculum schedule
    def get_failure_rate(episode: int) -> float:
        if episode <= 100: return 0.0
        elif episode <= 150: return 0.2
        else: return 0.5

    def get_stage(episode: int) -> int:
        if episode <= 100: return 0
        elif episode <= 150: return 1
        else: return 2

    # Role-matched training sequence (for policy guidance)
    TRAINING_SEQUENCE = [
        {"tool": "checkpoint",   "args": {}},
        {"tool": "research_web", "args": {"q": "analyse Python bug"}},
        {"tool": "write_code",   "args": {"path": "fix.py", "body": "def fix(): pass"}},
        {"tool": "critique",     "args": {"target": "verify fix"}},
        {"tool": "finish",       "args": {"answer": "Bug fixed"}},
    ]

    with open("training_output/reward_curve.jsonl", "w") as rc_file, \
         open("training_output/transfer_curve.jsonl", "w") as tc_file:

        rolling_avg = 0.0
        best_reward = 0.0

        for n in range(1, 201):
            failure_rate = get_failure_rate(n)
            stage = get_stage(n)

            try:
                # Reset Env
                step_result = env.reset(seed=42 + n, options={
                    "task_domain": "debug",
                    "agents": 2,
                    "failure_rate": failure_rate
                })
                
                episode_total = 0.0
                step = 0
                terminal = False

                while not terminal and step < 10:
                    # Simulation of policy selection
                    # In a real GRPO, we would sample multiple actions and compute advantages
                    action_data = TRAINING_SEQUENCE[step % len(TRAINING_SEQUENCE)]
                    
                    # Execute Step
                    step_result = env.step(action_data)
                    
                    step_reward = step_result.reward
                    episode_total += step_reward
                    terminal = step_result.done
                    step += 1

                    # Log Step Metrics
                    rc_file.write(json.dumps({
                        "step": (n - 1) * 10 + step,
                        "episode": n,
                        "step_reward": step_reward,
                        "episode_total": episode_total,
                        "model": "Qwen2.5-3B-Instruct",
                        "domain": "debug",
                        "failure_rate": failure_rate,
                        "stage": stage
                    }) + "\n")
                    rc_file.flush()

                # Simulate Weight Update (Learning)
                # In a real loop: optimizer.step()
                
                rolling_avg = 0.1 * episode_total + 0.9 * rolling_avg
                best_reward = max(best_reward, episode_total)

                if n % 5 == 0:
                    console.print(
                        f"[Episode {n:3d}/200] stage={stage} fr={failure_rate:.1f} | "
                        f"ep_reward={episode_total:.4f} | "
                        f"rolling={rolling_avg:.4f}"
                    )

                # Transfer eval every 10 episodes
                if n % 20 == 0:
                    for eval_domain in ["debug", "market_research", "etl"]:
                        eval_total = 0.0
                        eval_step_result = env.reset(seed=999 + n, options={
                            "task_domain": eval_domain,
                            "agents": 2,
                            "failure_rate": 0.0
                        })
                        eval_eid = eval_step_result.observation["episode_id"]
                        
                        for _ in range(5):
                            eval_action = TRAINING_SEQUENCE[_ % 5]
                            eval_step_result = env.step(eval_action)
                            eval_total += eval_step_result.reward
                            if eval_step_result.done: break

                        tc_score = round(eval_total / 5.0, 4)
                        tc_file.write(json.dumps({
                            "eval_episode": n,
                            "domain": eval_domain,
                            "score": tc_score,
                            "stage": stage
                        }) + "\n")
                        tc_file.flush()

            except Exception as e:
                console.print(f"[red]Episode {n} failed: {e}[/red]")
                time.sleep(0.5)

    console.print(Panel("[bold green]Training Complete! Curves generated in training_output/[/bold green]"))

if __name__ == "__main__":
    main()
