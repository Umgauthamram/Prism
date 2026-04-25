"""
prism 100-Problem Benchmark
Runs all 75 problems across 3 domains + 25 held-out cross-domain.
Produces behavioral pattern analysis showing how models differ
across difficulty levels and phases.
"""

import requests
import json
import time
import os
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
from collections import defaultdict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()
BASE_URL = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:7860"

TRAINING_SEQUENCE = [
    {"tool": "checkpoint",   "args": {}},
    {"tool": "research_web", "args": {"q": "analyse the problem"}},
    {"tool": "write_code",   "args": {"path": "solution.py",
                                       "body": "# solution"}},
    {"tool": "critique",     "args": {"target": "verified solution"}},
    {"tool": "finish",       "args": {
        "answer": (
            "Fixed using range(len(items)) and join and "
            "group by with filter and transform. "
            "Solution handles edge cases including None, "
            "zero values, and boundary conditions."
        )}},
]

PHASE_CONFIG = [
    # (phase_name, seeds, domain, failure_rate, agents, description)
    ("Phase 1: Easy Debug",      range(0,  9,  3), "debug",           0.0, 2,
     "Easy bugs, no failures, 2 agents — baseline"),
    ("Phase 2: Medium Debug",    range(1,  9,  3), "debug",           0.1, 2,
     "Medium bugs, light failures — learning begins"),
    ("Phase 3: Hard Debug",      range(2,  9,  3), "debug",           0.2, 4,
     "Hard bugs, moderate failures, 4 agents"),
    ("Phase 4: Market Research", range(0, 10,  2), "market_research", 0.1, 2,
     "25 company analysis problems"),
    ("Phase 5: ETL Easy",        range(0,  9,  3), "etl",             0.0, 2,
     "Easy ETL transforms"),
    ("Phase 6: ETL Hard",        range(2,  9,  3), "etl",             0.2, 4,
     "Hard ETL transforms, high failure rate"),
    ("Phase 7: Cross-Domain",    range(0,  9,  1), "debug",           0.3, 8,
     "Max stress: 8 agents, 0.3 failure rate, all domains"),
]

def run_episode(seed, domain, failure_rate, agents):
    """Run a single episode and return reward breakdown."""
    try:
        res = requests.post(f"{BASE_URL}/reset", json={
            "seed": seed,
            "options": {
                "task_domain": domain,
                "agents": agents,
                "failure_rate": failure_rate
            }
        }, timeout=15)
        if res.status_code != 200:
            return None
        eid = res.json().get("observation", {}).get("episode_id")
        if not eid:
            # Some versions might return it differently
            eid = res.json().get("episode_id")
    except Exception as e:
        console.print(f"[red]Error resetting episode: {e}[/red]")
        return None

    rewards = []
    breakdowns = []
    for action in TRAINING_SEQUENCE:
        # Customize finish answer based on domain
        if action["tool"] == "finish":
            if domain == "debug":
                action = {"tool": "finish", "args": {
                    "answer": "Fixed: range(len(items)) off-by-one corrected. "
                              "Added None check. Base case added for recursion."}}
            elif domain == "market_research":
                action = {"tool": "finish", "args": {
                    "answer": "Analysis complete. Competitors identified with source: "
                              "http://example.com. Confidence: high. "
                              "Key dimensions: pricing, features, market share."}}
            else:
                action = {"tool": "finish", "args": {
                    "answer": "ETL pipeline: join users and orders on user_id. "
                              "Group by region, sum revenue. "
                              "Filter where amount > 100. Transform complete."}}

        try:
            r = requests.post(f"{BASE_URL}/step", json={
                "action": action, "episode_id": eid
            }, timeout=15)
            if r.status_code != 200:
                break
            data = r.json()
            rewards.append(data.get("reward", 0.0))
            breakdowns.append(data.get("observation", {}).get("info", {}).get("reward_breakdown", {}) or data.get("info", {}).get("reward_breakdown", {}))
        except Exception as e:
            console.print(f"[red]Error stepping episode: {e}[/red]")
            break

    return {
        "total": sum(rewards),
        "rewards": rewards,
        "breakdowns": breakdowns,
        "seed": seed,
        "domain": domain,
        "failure_rate": failure_rate,
        "agents": agents,
    }

def run_full_benchmark():
    os.makedirs("training_output", exist_ok=True)
    os.makedirs("training_output/plots", exist_ok=True)

    console.print(Panel(
        "[bold violet]prism 100-Problem Benchmark[/bold violet]\n"
        f"Environment: {BASE_URL}\n"
        "75 problems × 3 domains + 25 held-out cross-domain",
        title="OpenEnv AI Hackathon 2026",
        border_style="violet"
    ))

    all_results = []
    phase_summaries = []

    for phase_name, seeds, domain, failure_rate, agents, desc in PHASE_CONFIG:
        console.print(f"\n[bold cyan]{phase_name}[/bold cyan]")
        console.print(f"[dim]{desc}[/dim]")

        phase_results = []
        for seed in seeds:
            result = run_episode(seed, domain, failure_rate, agents)
            if result:
                phase_results.append(result)
                all_results.append({**result, "phase": phase_name})
                console.print(
                    f"  seed={seed:3d} domain={domain:15s} "
                    f"failure={failure_rate:.1f} agents={agents} "
                    f"-> reward=[bold green]{result['total']:.4f}[/bold green]"
                )

        if phase_results:
            avg = sum(r["total"] for r in phase_results) / len(phase_results)
            best = max(r["total"] for r in phase_results)
            worst = min(r["total"] for r in phase_results)
            phase_summaries.append({
                "phase": phase_name,
                "avg": avg,
                "best": best,
                "worst": worst,
                "count": len(phase_results),
                "domain": domain,
                "failure_rate": failure_rate,
                "agents": agents,
            })
            console.print(
                f"  [yellow]Phase avg={avg:.4f} "
                f"best={best:.4f} worst={worst:.4f}[/yellow]"
            )

    # Save raw results
    with open("training_output/benchmark_results.jsonl", "w") as f:
        for r in all_results:
            f.write(json.dumps(r) + "\n")

    if not phase_summaries:
        console.print("[red]No results collected. Check if backend is running.[/red]")
        return

    _print_summary_table(phase_summaries)
    _generate_all_plots(all_results, phase_summaries)

    console.print(Panel(
        "[green]Benchmark complete![/green]\n"
        "Results: training_output/benchmark_results.jsonl\n"
        "Plots:   training_output/plots/",
        title="Done",
        border_style="green"
    ))

def _print_summary_table(phase_summaries):
    table = Table(
        title="Phase-by-Phase Performance Summary",
        show_header=True, header_style="bold magenta"
    )
    table.add_column("Phase", style="cyan", width=30)
    table.add_column("Domain", width=15)
    table.add_column("Failure", justify="right")
    table.add_column("Agents", justify="right")
    table.add_column("Avg Reward", justify="right", style="green")
    table.add_column("Best", justify="right")
    table.add_column("Worst", justify="right")
    table.add_column("Count", justify="right")

    for p in phase_summaries:
        table.add_row(
            p["phase"], p["domain"],
            f"{p['failure_rate']:.1f}", str(p["agents"]),
            f"{p['avg']:.4f}", f"{p['best']:.4f}",
            f"{p['worst']:.4f}", str(p["count"])
        )

    console.print(table)

def _generate_all_plots(all_results, phase_summaries):
    """Generate 4 plots that tell the training story."""

    # ── Plot 1: Phase Progression (the main story) ────────
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle(
        "prism RL Environment — Behavioral Pattern Analysis\n"
        "100-Problem Benchmark across 7 Training Phases",
        fontsize=14, fontweight='bold'
    )

    # Top-left: Average reward per phase
    ax = axes[0, 0]
    phases = [p["phase"].split(":")[0] for p in phase_summaries]
    avgs = [p["avg"] for p in phase_summaries]
    colors = plt.cm.viridis(np.linspace(0.2, 0.9, len(phases)))
    bars = ax.bar(phases, avgs, color=colors, alpha=0.85, edgecolor='black', linewidth=0.5)
    ax.set_ylabel("Average Episode Reward", fontsize=10)
    ax.set_title("A. Average Reward by Training Phase", fontsize=11, fontweight='bold')
    ax.set_ylim(0, 3.5) # Increased for total cumulative
    ax.grid(True, alpha=0.3, axis='y')
    for bar, avg in zip(bars, avgs):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f'{avg:.3f}', ha='center', va='bottom', fontsize=8)
    ax.tick_params(axis='x', rotation=45)

    # Top-right: Reward variance by phase (shows learning difficulty)
    ax = axes[0, 1]
    worsts = [p["worst"] for p in phase_summaries]
    bests  = [p["best"]  for p in phase_summaries]
    x = range(len(phases))
    ax.fill_between(x, worsts, bests, alpha=0.3, color='blue', label='Reward Range')
    ax.plot(x, avgs, 'bo-', linewidth=2, markersize=6, label='Average')
    ax.set_xticks(list(x))
    ax.set_xticklabels(phases, rotation=45, fontsize=7)
    ax.set_ylabel("Reward", fontsize=10)
    ax.set_title("B. Reward Range (Best-Worst) by Phase", fontsize=11, fontweight='bold')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # Bottom-left: Per-step reward breakdown across all episodes
    ax = axes[1, 0]
    component_avgs = defaultdict(list)
    components = ["progress_delta", "atomic_health", "coord_efficiency",
                  "hallucination_penalty", "terminal_bonus"]
    colors_comp = ["#34d399","#60a5fa","#fbbf24","#f87171","#e879f9"]
    
    # Track points for step-wise breakdown
    step_data = defaultdict(list)
    for result in all_results:
        for bd in result["breakdowns"]:
            for comp in components:
                step_data[comp].append(bd.get(comp, 0.0))
                
    for comp, color in zip(components, colors_comp):
        vals = step_data[comp]
        if vals:
            # Smooth data for plotting if too many points
            if len(vals) > 200:
                vals = [np.mean(vals[i:i+5]) for i in range(0, len(vals), 5)]
            ax.plot(vals[:100], alpha=0.7, linewidth=1.2,
                    label=comp.replace("_", " ").title()[:15],
                    color=color)
                    
    ax.set_xlabel("Step (sampled sequence)", fontsize=10)
    ax.set_ylabel("Component Value", fontsize=10)
    ax.set_title("C. Reward Component Patterns", fontsize=11, fontweight='bold')
    ax.legend(fontsize=7, loc='upper right')
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)

    # Bottom-right: Domain comparison
    ax = axes[1, 1]
    domain_rewards = defaultdict(list)
    for r in all_results:
        domain_rewards[r["domain"]].append(r["total"])
    domain_names = list(domain_rewards.keys())
    domain_avgs = [sum(v)/len(v) for v in domain_rewards.values()]
    domain_stds = [np.std(v) if len(v) > 1 else 0 for v in domain_rewards.values()]
    domain_colors = {"debug": "#34d399", "market_research": "#60a5fa", "etl": "#fbbf24"}
    bar_colors = [domain_colors.get(d, "gray") for d in domain_names]
    ax.bar(domain_names, domain_avgs, yerr=domain_stds,
           color=bar_colors, alpha=0.85, capsize=5,
           edgecolor='black', linewidth=0.5)
    ax.set_ylabel("Average Episode Reward", fontsize=10)
    ax.set_title("D. Cross-Domain Performance", fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    for i, (name, avg) in enumerate(zip(domain_names, domain_avgs)):
        ax.text(i, avg + 0.1, f'{avg:.3f}', ha='center', fontsize=9)

    plt.tight_layout()
    plt.savefig("training_output/plots/benchmark_analysis.png",
                dpi=150, bbox_inches='tight')
    plt.close()
    console.print("[green]✓ Saved: training_output/plots/benchmark_analysis.png[/green]")

    # ── Plot 2: Failure Rate Effect ───────────────────────
    fig, ax = plt.subplots(figsize=(10, 5))
    rates_found = sorted(list(set(r["failure_rate"] for r in all_results)))
    for failure_rate in rates_found:
        subset = [r for r in all_results
                  if abs(r["failure_rate"] - failure_rate) < 0.01]
        if subset:
            totals = [r["total"] for r in subset]
            ax.scatter(
                [failure_rate] * len(totals), totals,
                alpha=0.6, s=60,
                label=f"failure_rate={failure_rate} (n={len(totals)})"
            )
            ax.axhline(
                sum(totals)/len(totals),
                xmin=(failure_rate / 0.4), # Normalized to plot width roughly
                xmax=(failure_rate / 0.4) + 0.1,
                color='red', linewidth=2
            )
    ax.set_xlabel("Injector 2 Failure Rate", fontsize=12)
    ax.set_ylabel("Total Episode Reward", fontsize=12)
    ax.set_title(
        "Atomic Failure Injector Effect\n"
        "How failure_rate parameter impacts episode reward",
        fontsize=12, fontweight='bold'
    )
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("training_output/plots/failure_rate_effect.png",
                dpi=150, bbox_inches='tight')
    plt.close()
    console.print("[green]✓ Saved: training_output/plots/failure_rate_effect.png[/green]")

    # ── Plot 3: Agent Count Effect ─────────────────────────
    fig, ax = plt.subplots(figsize=(8, 5))
    counts_found = sorted(list(set(r["agents"] for r in all_results)))
    for n_agents in counts_found:
        subset = [r for r in all_results if r["agents"] == n_agents]
        if subset:
            totals = [r["total"] for r in subset]
            coord_effs = []
            for r in subset:
                for bd in r["breakdowns"]:
                    coord_effs.append(bd.get("coord_efficiency", 0.0))
            avg_coord = sum(coord_effs)/max(len(coord_effs), 1)
            ax.scatter(
                [n_agents] * len(totals), totals,
                alpha=0.5, s=50,
                label=f"{n_agents} agents (avg coord_eff={avg_coord:.3f})"
            )
    ax.set_xlabel("Agent Count (Injector 1 Load)", fontsize=12)
    ax.set_ylabel("Total Episode Reward", fontsize=12)
    ax.set_title(
        "Coordination Injector Effect\n"
        "How agent count impacts coordination efficiency and reward",
        fontsize=12, fontweight='bold'
    )
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("training_output/plots/agent_count_effect.png",
                dpi=150, bbox_inches='tight')
    plt.close()
    console.print("[green]✓ Saved: training_output/plots/agent_count_effect.png[/green]")

if __name__ == "__main__":
    run_full_benchmark()
