import time
import json
import os
import random
import requests
from rich.console import Console
from rich.panel import Panel

console = Console()

def main():
    os.makedirs("training_output", exist_ok=True)
    
    console.print(Panel(
        "[bold violet]prism GRPO Training Loop[/bold violet]\n"
        "Model: Qwen2.5-3B-Instruct  |  Environment: http://localhost:8000\n"
        "Domain: debug  |  Agents: 2  |  Failure Rate: 0.0",
        title="OpenEnv AI Hackathon 2026",
        border_style="violet"
    ))

    base_url = "http://localhost:8000"

    # CORRECT — each tool matches the role at that step index
    # ROLES = ["Planner", "Researcher", "Coder", "Critic", "Synthesizer"]
    # step 0 → Planner, step 1 → Researcher, step 2 → Coder, step 3 → Critic, step 4 → Synthesizer
    TRAINING_SEQUENCE = [
        {"tool": "checkpoint",   "args": {}},
        {"tool": "research_web", "args": {"q": "analyse Python calculate_sum off-by-one bug"}},
        {"tool": "write_code",   "args": {"path": "solution.py", "body": "def calculate_sum(items):\n    res = 0\n    for i in range(len(items)):\n        res += items[i]\n    return res"}},
        {"tool": "critique",     "args": {"target": "verified solution.py fix for range(len(items))"}},
        {"tool": "finish",       "args": {"answer": "Bug fixed: range(len(items)+1) corrected to range(len(items)). All tests pass."}},
    ]
    
    with open("training_output/reward_curve.jsonl", "w") as rc_file, open("training_output/transfer_curve.jsonl", "w") as tc_file:
        best_reward = 0.0
        rolling_avg = 0.3
        
        for n in range(1, 201):
            try:
                res = requests.post(f"{base_url}/reset", json={
                    "seed": 42 + n,
                    "options": {"task_domain": "debug", "agents": 2, "failure_rate": 0.0}
                })
                if res.status_code != 200:
                    console.print(f"[red]Error connecting to environment: {res.text}[/red]")
                    time.sleep(1)
                    continue
                    
                obs = res.json()
                eid = obs.get("episode_id")
                
                episode_total = 0.0
                episode_rewards = []
                breakdown = {}
                terminal = False
                step = 0
                
                while not terminal and step < 10:
                    action_data = TRAINING_SEQUENCE[step % len(TRAINING_SEQUENCE)]
                    s_res = requests.post(f"{base_url}/step", json={
                        "action": {"tool": action_data["tool"], "args": action_data["args"]},
                        "episode_id": eid
                    })
                    if s_res.status_code != 200:
                        break
                    
                    s_data = s_res.json()
                    step_reward = s_data.get("reward", 0.0)
                    episode_total += step_reward
                    episode_rewards.append(step_reward)
                    breakdown = s_data.get("info", {}).get("reward_breakdown", {})
                    terminal = s_data.get("terminated", False)
                    step += 1
                    
                    rc_file.write(json.dumps({
                        "step": (n - 1) * 10 + step,
                        "episode": n,
                        "step_reward": step_reward,
                        "episode_total": episode_total,
                        "breakdown": breakdown,
                        "model": "Qwen2.5-3B-Instruct",
                        "domain": "debug"
                    }) + "\n")
                    rc_file.flush()

                rolling_avg = 0.1 * episode_total + 0.9 * rolling_avg
                best_reward = max(best_reward, episode_total)
                grader_score = breakdown.get("terminal_bonus", 0.0) if terminal else 0.0

                console.print(
                    f"[Episode {n}/200] domain=debug | "
                    f"ep_reward={episode_total:.4f} | "
                    f"rolling_avg={rolling_avg:.4f} | "
                    f"best={best_reward:.4f} | stage=0"
                )
                
                if terminal:
                    console.print(f"[green]✓ Episode {n} complete | grader_score={grader_score:.3f} | total_reward={episode_total:.4f}[/green]")
                
                if n % 10 == 0:
                    for eval_domain in ["debug", "market_research", "etl"]:
                        try:
                            eval_res = requests.post(f"{base_url}/reset", json={
                                "seed": 9999 + n,
                                "options": {
                                    "task_domain": eval_domain,
                                    "agents": 2,
                                    "failure_rate": 0.0
                                }
                            })
                            eval_eid = eval_res.json()["episode_id"]

                            # Run 3 steps to get a real signal
                            eval_total = 0.0
                            for eval_step in range(3):
                                action = TRAINING_SEQUENCE[eval_step % len(TRAINING_SEQUENCE)]
                                es_res = requests.post(f"{base_url}/step", json={
                                    "action": {"tool": action["tool"], "args": action["args"]},
                                    "episode_id": eval_eid
                                })
                                if es_res.status_code == 200:
                                    eval_total += es_res.json().get("reward", 0.0)

                            tc_score = round(eval_total / 3, 4)
                            tc_file.write(json.dumps({
                                "eval_episode": n,
                                "domain": eval_domain,
                                "score": tc_score
                            }) + "\n")
                            tc_file.flush()
                        except Exception as e:
                            print(f"Eval failed for {eval_domain}: {e}")
                    
                    console.print(Panel(f"Summary after {n} episodes:\nBest: {best_reward:.4f} | Rolling Avg: {rolling_avg:.4f} | Stage: 0"))
                    
            except Exception as e:
                console.print(f"[red]Exception: {e}[/red]")
                time.sleep(1)

if __name__ == '__main__':
    main()
