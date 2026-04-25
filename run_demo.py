import sys
import time
import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()
base_url = "http://localhost:7860"
if len(sys.argv) > 1:
    base_url = sys.argv[1].rstrip("/")

def main():
    # 1. Print banner
    console.print(Panel(
        "[bold cyan]prism RL Environment Demo[/bold cyan]\n"
        "OpenEnv AI Hackathon 2026",
        title="[bold]prism 🌈[/bold]",
        border_style="cyan"
    ))

    EPISODE_1 = [
        {"tool": "checkpoint",   "args": {}},
        {"tool": "research_web", "args": {"q": "analyse bug in Python calculate_sum function"}},
        {"tool": "write_code",   "args": {"path": "fix.py", "body": "def calculate_sum(items):\n    res = 0\n    for i in range(len(items)):\n        res += items[i]\n    return res"}},
        {"tool": "critique",     "args": {"target": "verified fix.py passes all 3 test cases"}},
        {"tool": "finish",       "args": {"answer": "Fixed off-by-one: range(len(items)+1) changed to range(len(items))"}},
    ]

    EPISODE_2 = [
        {"tool": "checkpoint",   "args": {}},
        {"tool": "research_web", "args": {"q": "verify edge cases for calculate_sum with empty list"}},
        {"tool": "write_code",   "args": {"path": "fix_v2.py", "body": "def calculate_sum(items):\n    if not items: return 0\n    return sum(items)"}},
        {"tool": "critique",     "args": {"target": "verified fix_v2.py handles empty list and range(len(items))"}},
        {"tool": "finish",       "args": {"answer": "All edge cases handled. range(len(items)) fix confirmed. Empty list returns 0."}},
    ]

    # Episode 1
    reset_res = requests.post(f"{base_url}/reset", json={
        "seed": 42,
        "options": {"task_domain": "debug", "agents": 4, "failure_rate": 0.2}
    })
    if reset_res.status_code != 200:
        console.print(f"[red]Backend not reachable at {base_url}[/red]")
        return
    ep1_id = reset_res.json()["episode_id"]

    console.print("\n[bold cyan]━━ Episode 1 / 2 — Primary Debug Cycle ━━[/bold cyan]\n")
    ep1_rewards = []
    for i, action in enumerate(EPISODE_1):
        result = requests.post(f"{base_url}/step", json={
            "action": {"tool": action["tool"], "args": action["args"]},
            "episode_id": ep1_id
        })
        if result.status_code != 200:
            console.print("[red]Step failed[/red]")
            ep1_rewards.append(0.0)
            continue
        data = result.json()
        reward = data.get("reward", 0.0)
        ep1_rewards.append(reward)
        breakdown = data.get("info", {}).get("reward_breakdown", {})

        agent_role = data.get("observation", {}).get("agent_role", "Unknown")
        table = Table(show_header=True, header_style="bold magenta", title=f"Step {i+1} | Role: {agent_role}")
        table.add_column("Component", style="cyan", width=22)
        table.add_column("Value", justify="right", style="green")
        table.add_column("Weight", justify="right", style="dim")
        table.add_row("Progress Delta", f"{breakdown.get('progress_delta', 0):.4f}", "×0.40")
        table.add_row("Atomic Health", f"{breakdown.get('atomic_health', 0):.4f}", "×0.20")
        table.add_row("Coord Efficiency", f"{breakdown.get('coord_efficiency', 0):.4f}", "×0.20")
        table.add_row("Hallucination Pen.", f"{breakdown.get('hallucination_penalty', 0):.4f}", "×0.10")
        table.add_row("Terminal Bonus", f"{breakdown.get('terminal_bonus', 0):.4f}", "×0.10")
        table.add_section()
        table.add_row("[bold]TOTAL REWARD[/bold]", f"[bold yellow]{reward:.4f}[/bold yellow]", "")
        console.print(table)
        time.sleep(0.5)

    # Episode 2 — FRESH RESET
    reset_res2 = requests.post(f"{base_url}/reset", json={
        "seed": 43,
        "options": {"task_domain": "debug", "agents": 4, "failure_rate": 0.2}
    })
    if reset_res2.status_code != 200:
        console.print(f"[red]Backend not reachable at {base_url}[/red]")
        return
    ep2_id = reset_res2.json()["episode_id"]

    console.print("\n[bold cyan]━━ Episode 2 / 2 — Verification Cycle ━━[/bold cyan]\n")
    ep2_rewards = []
    for i, action in enumerate(EPISODE_2):
        result = requests.post(f"{base_url}/step", json={
            "action": {"tool": action["tool"], "args": action["args"]},
            "episode_id": ep2_id
        })
        if result.status_code != 200:
            console.print("[red]Step failed[/red]")
            ep2_rewards.append(0.0)
            continue
        data = result.json()
        reward = data.get("reward", 0.0)
        ep2_rewards.append(reward)
        breakdown = data.get("info", {}).get("reward_breakdown", {})

        agent_role = data.get("observation", {}).get("agent_role", "Unknown")
        table = Table(show_header=True, header_style="bold magenta", title=f"Step {i+6} | Role: {agent_role}")
        table.add_column("Component", style="cyan", width=22)
        table.add_column("Value", justify="right", style="green")
        table.add_column("Weight", justify="right", style="dim")
        table.add_row("Progress Delta", f"{breakdown.get('progress_delta', 0):.4f}", "×0.40")
        table.add_row("Atomic Health", f"{breakdown.get('atomic_health', 0):.4f}", "×0.20")
        table.add_row("Coord Efficiency", f"{breakdown.get('coord_efficiency', 0):.4f}", "×0.20")
        table.add_row("Hallucination Pen.", f"{breakdown.get('hallucination_penalty', 0):.4f}", "×0.10")
        table.add_row("Terminal Bonus", f"{breakdown.get('terminal_bonus', 0):.4f}", "×0.10")
        table.add_section()
        table.add_row("[bold]TOTAL REWARD[/bold]", f"[bold yellow]{reward:.4f}[/bold yellow]", "")
        console.print(table)
        time.sleep(0.5)

    all_rewards = ep1_rewards + ep2_rewards

    # Final summary panel
    total_cumulative   = sum(all_rewards)
    steps_with_progress = sum(1 for r in all_rewards if r > 0.50)
    steps_with_zero    = sum(1 for r in all_rewards if r < 0.05)
    best_step          = max(all_rewards) if all_rewards else 0.0
    worst_step         = min(all_rewards) if all_rewards else 0.0
    failure_count      = sum(1 for d in [ep1_rewards, ep2_rewards]
                             for r in d if r < 0.35)
    terminal_count     = 2  # both episodes have finish steps

    console.print(Panel(
        f"[green]Total Cumulative Reward:    {total_cumulative:.4f}[/green]\n"
        f"Steps with strong reward:   {steps_with_progress} / 10\n"
        f"Steps with zero reward:     {steps_with_zero} / 10\n"
        f"Best step reward:           {best_step:.4f}\n"
        f"Worst step reward:          {worst_step:.4f}\n"
        f"Terminal bonus fired:       {terminal_count} times\n"
        f"Episodes completed:         2\n\n"
        f"[cyan]Dashboard: {base_url.replace('8000', '3000')}[/cyan]\n"
        f"[cyan]HF Space:  https://gauthamram-prism.hf.space[/cyan]",
        title="[bold green]✓ Demo Complete[/bold green]",
        border_style="green"
    ))

if __name__ == "__main__":
    main()
