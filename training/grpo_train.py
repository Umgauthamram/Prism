import json
import time
import httpx
import random
import os
from dotenv import load_dotenv

load_dotenv()

# Config
ENV_BASE_URL = os.getenv("NEXT_PUBLIC_ENV_URL", "http://localhost:8000")
N_EPISODES = int(os.getenv("N_EPISODES", 200))
EVAL_EVERY = 50
OUTPUT_DIR = "./training_output"
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-3B-Instruct")

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def log_to_jsonl(filename, data):
    with open(os.path.join(OUTPUT_DIR, filename), "a") as f:
        f.write(json.dumps(data) + "\n")

async def train():
    print("Starting Prism RL Training (GRPO Reference)...")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        rolling_avg = 0.0
        
        for ep in range(1, N_EPISODES + 1):
            # 1. Reset
            res = await client.post(f"{ENV_BASE_URL}/reset", json={"seed": ep})
            obs = res.json()
            
            episode_reward = 0.0
            done = False
            step = 0
            
            # 2. Episode Loop
            while not done and step < 50:
                # Simulated Policy Selection
                # In a real scenario, this would call the LLM
                action = {
                    "tool": "checkpoint" if step == 0 else "research_web",
                    "args": {"q": "competitors", "content": "searching for info", "useful": True}
                }
                
                # If coder role, try writing code
                role = obs.get("agent_role")
                if role == "Coder":
                    action = {"tool": "write_code", "args": {"path": "solution.py", "body": "fixed code"}}
                elif role == "Synthesizer" and step > 5:
                    action = {"tool": "finish", "args": {"answer": "verified solution"}}

                res = await client.post(f"{ENV_BASE_URL}/step", json=action)
                step_res = res.json()
                
                obs = step_res["obs"]
                reward = step_res["reward"]
                done = step_res["terminated"]
                
                episode_reward += reward
                
                # Log step
                log_to_jsonl("reward_curve.jsonl", {
                    "episode": ep,
                    "step": step,
                    "total": reward,
                    "breakdown": step_res["info"]["reward_breakdown"]
                })
                
                step += 1
            
            rolling_avg = 0.1 * episode_reward + 0.9 * rolling_avg
            
            # 3. Log Episode
            metrics_res = await client.get(f"{ENV_BASE_URL}/metrics")
            metrics = metrics_res.json()
            
            print(f"Ep {ep:03d} | Reward: {episode_reward:.2f} | Rolling: {rolling_avg:.2f} | Stage: {metrics['current_stage']}")
            
            # 4. Evaluation
            if ep % EVAL_EVERY == 0:
                print(f"Running evaluation at episode {ep}...")
                # In a real scenario, call evaluate.py logic here
                for domain in ["debug", "market_research", "etl"]:
                    score = random.uniform(0.3, 0.8) # Simulated eval score
                    log_to_jsonl("transfer_curve.jsonl", {
                        "eval_episode": ep,
                        "domain": domain,
                        "score": score
                    })

if __name__ == "__main__":
    import anyio
    anyio.run(train)
