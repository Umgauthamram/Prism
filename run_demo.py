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
    
    # 2. POST /reset
    console.print("[dim]Initializing episode...[/dim]")
    res = requests.post(f"{base_url}/reset", json={
        "seed": 42,
        "options": {"task_domain": "debug", "agents": 4, "failure_rate": 0.2}
    })
    
    if res.status_code != 200:
        console.print(f"[red]Backend not reachable at {base_url}[/red]")
        return
        
    obs = res.json()
    eid = obs.get("episode_id")
    
    # 3. Print observation table
    obs_table = Table(title="Initial Observation")
    obs_table.add_column("Key")
    obs_table.add_column("Value")
    for k, v in obs.items():
        if k != "task_graph":
            obs_table.add_row(k, str(v))
    console.print(obs_table)
    
    # 4. Loop 10 steps
    # Sensible default tool per role
    role_tools = {
        "Planner": "decompose",
        "Researcher": "research_web",
        "Coder": "write_code",
        "Critic": "critique",
        "Synthesizer": "finish"
    }
    
    total_cumulative_reward = 0.0
    final_breakdown = {}
    
    for i in range(1, 11):
        # Fetch current state to get agent_role
        state_res = requests.get(f"{base_url}/state?episode_id={eid}")
        state = state_res.json() if state_res.status_code == 200 else {}
        agent_role = state.get("agent_role", "Planner")
        
        tool = role_tools.get(agent_role, "research_web")
        if i == 10:
            tool = "finish"
            
        args = {"q": "python bug", "path": "main.py", "body": "print('fixed')", "target": "code", "answer": "done!"}
        
        step_res = requests.post(f"{base_url}/step", json={
            "tool": tool,
            "args": args,
            "episode_id": eid
        })
        
        if step_res.status_code != 200:
            console.print("[red]Step failed[/red]")
            continue
            
        step_data = step_res.json()
        reward = step_data.get("reward", 0.0)
        total_cumulative_reward += reward
        final_breakdown = step_data.get("info", {}).get("reward_breakdown", {})
        
        table = Table(show_header=True, header_style="bold magenta", title=f"Step {i} | Role: {agent_role}")
        table.add_column("Component", style="cyan", width=22)
        table.add_column("Value", justify="right", style="green")
        table.add_column("Weight", justify="right", style="dim")
        table.add_row("Progress Delta", f"{final_breakdown.get('progress_delta', 0):.4f}", "×0.40")
        table.add_row("Atomic Health", f"{final_breakdown.get('atomic_health', 0):.4f}", "×0.20")
        table.add_row("Coord Efficiency", f"{final_breakdown.get('coord_efficiency', 0):.4f}", "×0.20")
        table.add_row("Hallucination Pen.", f"{final_breakdown.get('hallucination_penalty', 0):.4f}", "×0.10")
        table.add_row("Terminal Bonus", f"{final_breakdown.get('terminal_bonus', 0):.4f}", "×0.10")
        table.add_section()
        table.add_row("[bold]TOTAL REWARD[/bold]", f"[bold yellow]{reward:.4f}[/bold yellow]", "")
        console.print(table)
        
        time.sleep(0.5)

    # 5. Print final summary
    console.print(Panel(
        f"Total Cumulative Reward: {total_cumulative_reward:.4f}\n"
        f"Orphaned Side Effects (Atomic Health): {final_breakdown.get('atomic_health', 1.0):.4f}\n"
        f"Coordination Efficiency: {final_breakdown.get('coord_efficiency', 0.0):.4f}",
        title="[bold green]Demo Complete[/bold green]"
    ))
    
    # 6.
    console.print("[bold blue]Open http://localhost:3000 to see the live dashboard[/bold blue]")

if __name__ == "__main__":
    main()
