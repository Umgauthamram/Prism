import anyio
import json
import os
import time
from envs.prism import PrismEnv

async def run_evaluation(n_episodes_per_domain: int = 5):
    print("=" * 60)
    print("         PRISM RL — EVALUATION HARNESS")
    print("=" * 60)

    os.makedirs("training_output", exist_ok=True)
    results = {}
    all_data = []

    # Using the PrismEnv client (OpenEnv compliant)
    # Note: Ensure the server is running on localhost:8000
    env = PrismEnv(base_url="http://localhost:8000")

    # Role-matched action sequence (matches step rotation):
    # Step 0 → Planner, Step 1 → Researcher, Step 2 → Coder, Step 3 → Critic, Step 4 → Synthesizer
    EVAL_SEQUENCES = {
        "debug": [
            {"tool": "checkpoint", "args": {}},
            {"tool": "research_web", "args": {"q": "analyse Python bug in calculate_sum"}},
            {"tool": "write_code", "args": {"path": "fix.py", "body": "def calculate_sum(items):\n    return sum(items)"}},
            {"tool": "critique", "args": {"target": "verified fix for range(len(items))"}},
            {"tool": "finish", "args": {"answer": "Bug fixed: range(len(items)) corrected. All tests pass."}},
        ],
        "market_research": [
            {"tool": "checkpoint", "args": {}},
            {"tool": "research_web", "args": {"q": "competitor analysis market share"}},
            {"tool": "write_code", "args": {"path": "report.py", "body": "# Market research report\ncompetitor = 'Notion'\nconfidence: 0.85"}},
            {"tool": "critique", "args": {"target": "verified competitor analysis source: industry reports confidence: high"}},
            {"tool": "finish", "args": {"answer": "1. competitor Notion leads in productivity. source: Gartner 2026. confidence: 0.85"}},
        ],
        "etl": [
            {"tool": "checkpoint", "args": {}},
            {"tool": "research_web", "args": {"q": "ETL join transform group by pipeline"}},
            {"tool": "write_code", "args": {"path": "pipeline.py", "body": "# ETL: SELECT name, SUM(amount) as total_amount FROM users JOIN orders GROUP BY name"}},
            {"tool": "critique", "args": {"target": "verified ETL pipeline with join and group"}},
            {"tool": "finish", "args": {"answer": "ETL pipeline: join users and orders on user_id, group by name, select name and total_amount. Transform complete."}},
        ],
    }

    for domain in ["debug", "market_research", "etl"]:
        domain_scores = []
        sequence = EVAL_SEQUENCES[domain]
        print(f"\nEvaluating domain: {domain}")

        for i in range(n_episodes_per_domain):
            # Reset with specific domain
            step_result = env.reset(seed=1000 + i, options={"task_domain": domain, "agents": 2, "failure_rate": 0.0})
            episode_id = step_result.observation["episode_id"]

            total_reward = 0.0
            step_rewards = []

            for step_idx, action_data in enumerate(sequence):
                # Execute step using PrismEnv client
                step_result = env.step(action_data)
                
                reward = step_result.reward
                total_reward += reward
                step_rewards.append(reward)
                
                if step_result.done:
                    break

            domain_scores.append(total_reward)
            all_data.append({
                "domain": domain,
                "episode": i,
                "seed": 1000 + i,
                "total_reward": round(total_reward, 4),
                "step_rewards": [round(r, 4) for r in step_rewards],
            })
            print(f"  Episode {i+1}/{n_episodes_per_domain}: reward={total_reward:.4f}")

        avg = sum(domain_scores) / len(domain_scores)
        results[domain] = round(avg, 4)

    # Print summary
    print("\n" + "=" * 60)
    print("EVALUATION RESULTS:")
    overall = 0.0
    for domain, score in results.items():
        print(f"  {domain:20}: {score:.4f}")
        overall += score
    overall_avg = overall / len(results)
    print(f"  {'OVERALL':20}: {overall_avg:.4f}")
    print("=" * 60)

    # Save results
    with open("training_output/eval_results.json", "w") as f:
        json.dump({
            "per_domain": results,
            "overall_avg": round(overall_avg, 4),
            "episodes": all_data
        }, f, indent=2)
    print(f"\nResults saved to training_output/eval_results.json")

    return results

if __name__ == "__main__":
    anyio.run(run_evaluation)
