import httpx
import anyio
import json
import os

ENV_BASE_URL = "http://localhost:8000"

async def run_evaluation(n_episodes_per_domain: int = 5):
    print("Starting Evaluation Harness...")
    results = {}
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for domain in ["debug", "market_research", "etl"]:
            domain_scores = []
            print(f"Evaluating domain: {domain}")
            
            for i in range(n_episodes_per_domain):
                # Reset with specific domain
                res = await client.post(f"{ENV_BASE_URL}/reset", json={
                    "seed": 1000 + i,
                    "options": {"task_domain": domain, "agents": 2, "failure_rate": 0.0}
                })
                
                done = False
                total_reward = 0.0
                while not done:
                    # Dummy agent strategy for eval
                    action = {"tool": "finish", "args": {"answer": "evaluating"}}
                    step_res = await client.post(f"{ENV_BASE_URL}/step", json=action)
                    step_data = step_res.json()
                    total_reward += step_data["reward"]
                    done = step_data["terminated"]
                
                domain_scores.append(total_reward)
            
            results[domain] = sum(domain_scores) / len(domain_scores)
            
    print("\nEvaluation Results:")
    for domain, score in results.items():
        print(f"  {domain:15}: {score:.4f}")
        
    return results

if __name__ == "__main__":
    anyio.run(run_evaluation)
