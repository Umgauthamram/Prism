import asyncio
import httpx
import os
import json
import sys
from dotenv import load_dotenv

load_dotenv()

ENV_BASE_URL = os.getenv("NEXT_PUBLIC_ENV_URL", "http://127.0.0.1:8000")
if len(sys.argv) > 1:
    ENV_BASE_URL = sys.argv[1].rstrip("/")
GROQ_KEY = os.getenv("GROQ_API_KEY")
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")

MODELS = [
    {"provider": "groq", "model": "llama-3.3-70b-versatile", "key": GROQ_KEY},
    {"provider": "gemini", "model": "gemini-2.0-flash", "key": GOOGLE_KEY}
]

async def run_contestant(client: httpx.AsyncClient, config: dict):
    provider = config["provider"]
    model = config["model"]
    api_key = config["key"]
    
    if not api_key:
        print(f"⚠️ Skipping {model} (No API key found)")
        return

    print(f"🏁 Starting {model}...")
    
    # 1. Reset Episode
    res = await client.post(f"{ENV_BASE_URL}/reset", json={
        "seed": 42,
        "options": {"task_domain": "debug", "agents": 2, "failure_rate": 0.0}
    })
    obs = res.json()
    episode_id = obs["observation"]["episode_id"]
    
    # 2. Configure Model for this episode
    await client.post(f"{ENV_BASE_URL}/models/config", json={
        "provider": provider,
        "model": model,
        "api_key": api_key,
        "episode_id": episode_id
    })
    
    done = False
    total_reward = 0.0
    steps = 0
    
    while not done and steps < 50:
        # Action is dummy, backend overrides with LLM
        res = await client.post(f"{ENV_BASE_URL}/step", json={
            "action": {"tool": "checkpoint", "args": {}},
            "episode_id": episode_id
        })
        
        if res.status_code != 200:
            print(f"❌ Error in {model}: Backend returned {res.status_code}: {res.text}")
            break
            
        try:
            data = res.json()
        except Exception:
            print(f"❌ Error in {model}: Received non-JSON response: {res.text[:200]}")
            break
        
        if "reward" not in data:
            print(f"❌ Error in {model}: Missing 'reward' in response: {data}")
            break

        reward = data["reward"]
        total_reward += reward
        done = data["done"]
        steps += 1
        
        # Live print status
        print(f"  [{model[:8]}] Step {steps:2d} | Reward: {reward:.2f} | Total: {total_reward:.2f}")
        await asyncio.sleep(0.5) # Small delay for readable logs

    print(f"🏆 {model} Finished! Final Reward: {total_reward:.2f}")
    return total_reward

async def main():
    print("════════════════════════════════════════════════════════════")
    print("                PRISM MULTI-MODEL TOURNAMENT                ")
    print("════════════════════════════════════════════════════════════\n")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Run all models concurrently
        tasks = [run_contestant(client, m) for m in MODELS]
        results = await asyncio.gather(*tasks)
        
    print("\n" + "═"*60)
    print("FINAL STANDINGS:")
    for m, score in zip(MODELS, results):
        if score:
            print(f"  {m['model']:30}: {score:.4f}")
    print("═"*60)

if __name__ == "__main__":
    asyncio.run(main())
