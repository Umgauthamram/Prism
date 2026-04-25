---
title: prism — Multi-Agent RL Reliability Environment
emoji: 🌈
colorFrom: purple
colorTo: blue
sdk: docker
app_port: 7860
pinned: true
tags:
  - openenv
  - reinforcement-learning
  - multi-agent
  - llm
  - meta-hackathon-2026
---

# 🌈 prism — Multi-Agent RL Reliability Environment

> OpenEnv-native RL environment that stress-tests LLM agents on three 
> empirically-documented failure modes of multi-agent systems — making 
> coordination failure, non-atomic recovery, and domain transfer 
> trainable signals instead of just observable weaknesses.

**Meta × PyTorch × Hugging Face · OpenEnv AI Hackathon 2026**

![OpenEnv Compatible](https://img.shields.io/badge/OpenEnv-Compatible-green)
![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue)
![Docker Ready](https://img.shields.io/badge/Docker-Ready-blue)
![HF Space Live](https://img.shields.io/badge/HF%20Space-Live-purple?link=https://huggingface.co/spaces/umgauthamram/prism-rl-env)

---

## Section 1: Overview

Reliability in multi-agent LLM systems is often bottlenecked by a "coordination tax" that scales poorly beyond a few concurrent agents. In production, three specific failure modes dominate: coordination overhead leading to redundant work, non-atomic failures that leave the system in an inconsistent state after a mid-task crash, and the "narrow specialist" trap where an agent's learned reliability improvements in one domain fail to transfer to another. These are not merely theoretical challenges; they are the documented blockers preventing the deployment of long-horizon autonomous systems in enterprise environments.

**prism** reframes these failures as measurable, trainable signals. The environment places agents in a sandboxed workspace assigned professional tasks like software debugging, market research, or ETL pipeline construction. Three difficulty injectors—Coordination Stress, Atomic Failure, and Domain Shift—deliberately manufacture these failure modes during episodes. Every injection produces a dense, scored reward signal that directly penalizes unreliable behavior. The environment is packaged as a single Docker image conforming to the OpenEnv Gymnasium-style HTTP API, making it drop-in compatible with state-of-the-art training frameworks like GRPO, PPO, TRL, SkyRL, and Oumi.

What makes **prism** novel is its focus on the reliability gap itself. Instead of just tracking task success, it uses a 5-component shaped reward model to incentivize transaction-like discipline and information-efficient communication. The environment supports model-agnostic evaluation via a live Next.js dashboard, allowing developers to switch between Groq (Llama), Gemini, and OpenAI models in real-time and compare their reward curves side-by-side.

---

## Section 2: Environment At A Glance

| Property          | Value                                      |
|-------------------|--------------------------------------------|
| Protocol          | OpenEnv / Gymnasium-style HTTP API         |
| Primary Theme     | Multi-Agent Interactions                   |
| Secondary Theme   | Long-Horizon Planning                      |
| Tertiary Theme    | Self-Improving Systems                     |
| Task Domains      | Software Debugging, Market Research, ETL   |
| Agent Roles       | Planner, Researcher, Coder, Critic, Synthesizer |
| Reward Type       | Dense, shaped, 5-component per step        |
| Reward Range      | (0.01, 0.99) soft-clamped                  |
| Max Steps/Episode | 50                                         |
| Docker Port       | 7860                                       |
| HF Space          | [huggingface.co/spaces/umgauthamram/prism-rl-env](https://huggingface.co/spaces/umgauthamram/prism-rl-env) |

---

## Section 3: Quickstart

### 3a — Fastest path (HF Space, zero install)

The environment is live on Hugging Face Spaces. No installation required. Use the API directly:

**Check Health**
```bash
curl http://localhost:8000/health
```
*Expected Output:* `{"status": "ok", "project": "prism", "timestamp": 1713945600.0}`

**Reset Episode**
```bash
curl -X POST http://localhost:8000/reset \
  -H "Content-Type: application/json" \
  -d '{"seed": 42, "options": {"task_domain": "debug", "agents": 2, "failure_rate": 0.0}}'
```
*Expected Output:*
```json
{
  "task_graph": {
    "analyse_bug": {"status": "pending", "dependencies": []},
    "locate_code": {"status": "pending", "dependencies": ["analyse_bug"]},
    "write_fix": {"status": "pending", "dependencies": ["locate_code"]},
    "run_tests": {"status": "pending", "dependencies": ["write_fix"]},
    "verify": {"status": "pending", "dependencies": ["run_tests"]}
  },
  "world_model": {},
  "agent_role": "Planner",
  "episode_id": "8f3e2a1b-...",
  "step": 0,
  "task_domain": "debug",
  "terminated": false
}
```

**Take Step**
```bash
curl -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{"action": {"tool": "research_web", "args": {"q": "analyse bug report"}}, "episode_id": "EP_ID"}'
```
*Expected Output:*
```json
{
  "observation": { "step": 1, "agent_role": "Researcher", ... },
  "reward": 0.4821,
  "terminated": false,
  "truncated": false,
  "info": {
    "reward_breakdown": {
      "progress_delta": 0.1000,
      "atomic_health": 0.99,
      "coord_efficiency": 0.85,
      "hallucination_penalty": 0.99,
      "terminal_bonus": 0.01
    }
  }
}
```

**Get Metrics**
```bash
curl http://localhost:8000/metrics
```
*Expected Output:*
```json
{
  "reward_curve": [{"step": 1, "total": 0.4821, "breakdown": {...}}],
  "transfer_scores": [],
  "current_stage": 0,
  "rolling_reward": 0.4821
}
```

### 3b — Local Docker (recommended for training)
```bash
docker pull umgauthamram/prism-rl-env
docker run -p 7860:7860 umgauthamram/prism-rl-env
# Open http://localhost:7860
```

Or build from source:
```bash
git clone https://github.com/umgauthamram/prism-rl-env
cd prism-rl-env
docker compose up --build
```

### 3c — Local development (backend + frontend separately)
```bash
# Terminal 1 — Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.server:app --reload --port 7860

# Terminal 2 — Dashboard
cd website
npm install
npm run dev
# Open http://localhost:3000
```

### 3d — Run the live demo script
```bash
python run_demo.py
```
This script executes a full 10-step episode and prints a rich terminal output showing the step-by-step reward breakdown per component (Progress, Atomic Health, Coordination, etc.) using the `rich` library.

---

## Section 4: Environment Structure

```
prism/
├── backend/
│   ├── server.py          — FastAPI: /reset /step /state /health /metrics
│   ├── environment.py     — PrismEnv core (Gymnasium-style)
│   ├── reward.py          — Dense 5-component reward computation
│   ├── curriculum.py      — Outer loop difficulty scheduler
│   ├── llm_router.py      — Multi-model routing (Groq/Gemini/OpenAI)
│   ├── injectors/
│   │   ├── coordination.py   — Injector 1: coordination stress
│   │   ├── atomic_failure.py — Injector 2: mid-task crashes
│   │   └── domain_shift.py   — Injector 3: cross-domain transfer
│   ├── tasks/
│   │   ├── debugging.py      — Task domain 1 + pytest grader
│   │   ├── market_research.py — Task domain 2 + rubric grader
│   │   └── etl_pipeline.py   — Task domain 3 + schema grader
│   ├── roles/
│   │   └── contracts.py   — Role-action contract enforcement
│   └── tools/
│       └── registry.py    — All 9 tool implementations
├── training/
│   ├── grpo_train.py      — Reference GRPO training loop
│   └── evaluate.py        — Held-out transfer evaluation
├── website/               — Next.js TypeScript live dashboard
├── run_demo.py            — Terminal demo script
├── Dockerfile             — Single-image build (backend + frontend)
├── docker-compose.yml
└── requirements.txt
```

---

## Section 5: OpenEnv API Reference

### reset()

**Signature:**
`POST /reset`

**Body:** 
`{ "seed": int, "options": { "task_domain": str, "agents": int, "failure_rate": float } }`

**Parameters:**
| Parameter    | Type  | Values                          | Default |
|--------------|-------|---------------------------------|---------|
| seed         | int   | any integer                     | 42      |
| task_domain  | str   | "debug", "market_research", "etl" | "debug" |
| agents       | int   | 2, 4, 8                         | 2       |
| failure_rate | float | 0.0, 0.2, 0.5                   | 0.0     |

**Returns:**
```json
{
  "task_graph": { "analyse_bug": {"status": "pending", "dependencies": []}, ... },
  "world_model": {},
  "last_tool_output": null,
  "checkpoint_id": "cp_uuid_0",
  "agent_role": "Planner",
  "injected_failure_flag": false,
  "episode_id": "8f3e2a1b-...",
  "step": 0,
  "task_domain": "debug",
  "agents": 2,
  "failure_rate": 0.0,
  "terminated": false
}
```

### step()

**Signature:**
`POST /step`

**Body:** 
`{ "action": { "tool": str, "args": dict } }`

**Returns:** `{ obs, reward, terminated, truncated, info }`
- `reward` is always a float in `(0.01, 0.99)`.
- `info` always contains `reward_breakdown` with all 5 components.

**Action Space:**
| Tool           | Role        | Args                  | Description              |
|----------------|-------------|-----------------------|--------------------------|
| research_web   | Researcher  | q: str                | Web search simulation    |
| write_code     | Coder       | path: str, body: str  | Write to sandboxed fs    |
| run_tests      | Coder       | path: str             | Execute pytest           |
| db_preflight   | Coder       | spec: dict            | Register DB op + inverse |
| db_commit      | Coder       | preflight_id: str     | Execute pre-registered op|
| checkpoint     | Planner     | (none)                | Snapshot world model     |
| rollback       | Planner     | checkpoint_id: str    | Restore prior snapshot   |
| critique       | Critic      | target: str           | Score for hallucination  |
| finish         | Synthesizer | answer: str           | Terminate + grade episode|

### state()

**Signature:** `GET /state`

**Returns:** Full internal state snapshot.
```json
{
  "task_graph": { ... },
  "world_model": { "key": "value" },
  "agent_role": "Coder",
  "step": 12,
  "terminated": false
}
```

**Observation Fields:**
| Field                 | Type   | Description                           |
|-----------------------|--------|---------------------------------------|
| task_graph            | dict   | Subtasks with status and dependencies |
| world_model           | dict   | Shared facts across all agents        |
| last_tool_output      | dict   | Result of most recent tool call       |
| checkpoint_id         | str    | Last stable state boundary            |
| agent_role            | str    | Current active role                   |
| injected_failure_flag | bool   | True when Injector 2 is active        |
| episode_id            | str    | UUID for this episode                 |
| step                  | int    | Current step number                   |
| task_domain           | str    | Active domain                         |
| agents                | int    | Active agent count                    |
| failure_rate          | float  | Active failure rate                   |

### Extra endpoints
- `GET /health` → `{"status": "ok"}`
- `GET /metrics` → Reward curves, transfer scores, curriculum stage info.
- `GET /models/available` → All supported providers and models.
- `POST /models/config` → Set active provider, model, and API key.
- `POST /models/test` → Test an API key before activating.

---

## Section 6: The Three Difficulty Injectors

### Injector 1 — Coordination Stress
**Targets:** Multi-Agent Interactions theme

Spawns N agents (2, 4, or 8) operating in parallel. Each agent sees only role-relevant observations. The environment tracks every token of inter-agent communication and penalizes excessive or redundant information passing.

```python
coord_efficiency = useful_work_tokens / (useful_work_tokens + coordination_tokens)
```
Agents that effectively utilize the shared `world_model` without redundant search queries score near 1.0. Agents that duplicate requests or produce high-noise communication score near 0.0.

### Injector 2 — Atomic Failure
**Targets:** Long-Horizon Planning theme

With probability p ∈ {0, 0.2, 0.5}, the environment kills a tool call mid-execution, simulating partial DB writes or corrupted file states.

```python
atomic_health = 1.0 - (orphaned_side_effects / total_side_effects)
```
Agents that use `db_preflight` and `checkpoint` before committing changes can use `rollback` to return to a clean state. The reward gradient directly pushes agents toward transaction-like discipline.

### Injector 3 — Domain Shift
**Targets:** Self-Improving Systems theme

Tasks are drawn from 3 distinct domains with held-out validation sets. A transfer score is logged every 50 episodes to measure generalization.

```python
transfer_score = held_out_same_domain_perf - first_seen_other_domain_perf
```
A rising transfer score proves genuine cross-domain generalization, while a flat score indicates narrow specialization. This is visible in real-time on the dashboard's transfer chart.

---

## Section 7: Reward Model

### Formula
```python
# Weighted Progress calculation
progress = (done_count + 0.5 * running_count) / total_tasks

r_t = 0.40 * progress_delta(t)
    + 0.20 * atomic_health(t)
    + 0.20 * coord_efficiency(t)
    + 0.10 * hallucination_penalty(t)
    + 0.10 * terminal_bonus(t)

# Soft clamp applied to every component for numerical stability in RL
component = max(0.01, min(0.99, raw_value))
```

### Component table

| Component            | Weight | Signal Source                     | Nonzero When          |
|----------------------|--------|-----------------------------------|-----------------------|
| progress_delta       | 0.40   | Weighted completion fraction Δ    | Node starts/finishes  |
| atomic_health        | 0.20   | 1 - orphaned/total side effects   | Every step            |
| coord_efficiency     | 0.20   | useful / (total + overhead)       | Every step (30% floor)|
| hallucination_penalty| 0.10   | 1 - critique flagged claim rate   | Every step            |
| terminal_bonus       | 0.10   | Grader score on finish step       | Final step only       |

### Anti-gaming design
The components are designed in natural tension. Maximizing `coord_efficiency` by simply doing nothing causes `progress_delta` to collapse. To prevent efficiency from crashing to zero during necessary planning, **overhead actions (checkpoint, rollback)** contribute 30% towards useful tokens. **Running nodes** contribute 50% of a completed node's value to the progress delta, encouraging agents to transition tasks into active states immediately. No degenerate policy can maximize the composite reward; reliability must be balanced with task progress.

---

## Section 8: Task Domains

### Domain 1: Software Debugging
- **Input:** Python codebase (200-400 lines), failing tests, and bug report.
- **Goal:** Passing test suite with no regressions.
- **Grader:** Automated pytest exit code on held-out test set (binary 0 or 1).
- **Stresses:** Coder-Critic loop, atomic failure recovery during test environment corruption.

### Domain 2: Competitive Market Research  
- **Input:** Company name, product category, and simulated web search access.
- **Goal:** Structured competitive analysis with sourced claims.
- **Grader:** Rubric-scored on completeness, citation validity, and confidence calibration.
- **Stresses:** Long-horizon parallel search and hallucination control.

### Domain 3: ETL Pipeline Construction
- **Input:** Source table schemas and target transformation spec.
- **Goal:** Working ETL script producing target schema on held-out data.
- **Grader:** Schema diff (binary) and row-level equality check (graded).
- **Stresses:** Merge logic between Researcher and Coder, transaction coordination on partial writes.

---

## Section 9: Agent Roles and Contracts

| Role        | Allowed Tools                                    | Responsibility                        |
|-------------|--------------------------------------------------|---------------------------------------|
| Planner     | decompose, assign, replan, checkpoint, rollback  | Task graph. Owns checkpoint boundaries|
| Researcher  | research_web, read_schema, write_world           | External info. Typed world model facts|
| Coder       | write_code, run_tests, db_preflight, db_commit   | Code. Pre-flights all side effects    |
| Critic      | critique, flag_hallucination, request_replan     | Validates every output                |
| Synthesizer | merge, finish, flag_gap                          | Final deliverable. Flags uncertainty  |

The environment enforces these contracts at the step boundary. Any violation results in an immediate reward of `0.0`, training agents to respect role boundaries and coordination protocols.

---

## Section 10: Curriculum Learning

| Stage | failure_rate | agents | domains                    | advances when EMA > |
|-------|-------------|--------|----------------------------|---------------------|
| 0     | 0.0         | 2      | debug                      | 0.45                |
| 1     | 0.2         | 2      | debug, etl                 | 0.55                |
| 2     | 0.2         | 4      | debug, etl, market_research| 0.65                |
| 3     | 0.5         | 8      | all + held-out eval        | 0.75                |

Difficulty is parameterized at reset time, allowing for seamless curriculum learning. The environment uses an Exponential Moving Average (EMA, α=0.1) over the last 20 episodes to trigger stage advancement.

---

## Section 11: Multi-Model Evaluation

The dashboard supports live model switching for evaluation. Configure Groq, Gemini, or OpenAI models from the Model Selector panel. All models are evaluated under identical seeded conditions. The "Model Agnosticism Proof" chart overlays their reward curves, providing direct performance comparisons.

| Provider | Models Available                                              |
|----------|---------------------------------------------------------------|
| Groq     | llama-3.3-70b-versatile, llama-3.1-8b-instant, mixtral-8x7b-32768 |
| Gemini   | gemini-2.0-flash, gemini-1.5-pro, gemini-1.5-flash            |
| OpenAI   | gpt-4o, gpt-4o-mini                                          |

---

## Section 12: Training Integration

### GRPO with TRL
```python
from envs.prism import PrismAction, PrismEnv

async with PrismEnv(base_url="http://localhost:7860") as env:
    obs = await env.reset(seed=42, options={
        "task_domain": "debug",
        "agents": 2,
        "failure_rate": 0.0
    })
    while not done:
        action = policy.act(obs)
        result = await env.step(PrismAction(tool=action.tool, args=action.args))
        reward = result.reward
        done = result.observation.done
```

### Reference training script
```bash
python training/grpo_train.py --model Qwen/Qwen2.5-3B-Instruct --episodes 200
```
This script saves `reward_curve.jsonl` (per-step logs) and `transfer_curve.jsonl` (eval checkpoints) to the `training_output/` directory.

---

## Section 13: OpenEnv Compliance Checklist

- [x] **Gymnasium-style API:** step(), reset(), state() over HTTP.
- [x] **Isolated execution:** Each episode sandboxed with ephemeral state.
- [x] **Docker packaging:** Single Dockerfile exposing port 7860.
- [x] **Hugging Face Space:** Deployed at [umgauthamram-prism-rl-env](https://huggingface.co/spaces/umgauthamram/prism-rl-env).
- [x] **Reproducibility:** Fully seeded randomness in reset().
- [x] **Scalable rollouts:** Stateless HTTP for horizontal scaling.
- [x] **Novel environment:** Targets coordination, atomicity, and transfer.
- [x] **Automated graders:** All three domains fully automated.
- [x] **Dense reward:** Per-step shaped signal.
- [x] **Role contracts:** Enforced at the environment boundary.
- [x] **Curriculum learning:** Parameterized difficulty at reset.
- [x] **Transfer measurement:** Built-in logging every 50 episodes.

---

## Section 14: Local Development

### Prerequisites
Python 3.11+, Node.js 20+, Docker.

### Backend
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.server:app --reload --port 7860
```

### Frontend
```bash
cd website && npm install && npm run dev
```

### Verify
```bash
python run_demo.py
```

---

## Section 15: Project Context

- **Hackathon:** Meta × PyTorch × Hugging Face OpenEnv AI Hackathon 2026
- **Round:** 2 — 48-hour Finale
- **Submission Date:** April 25–26, 2026
- **Author:** Raushan Raj

**Themes Addressed:**
- **Primary:** Multi-Agent Interactions (Coordination Injector)
- **Secondary:** Long-Horizon Planning (Atomic Failure Injector)
- **Tertiary:** Self-Improving Systems (Domain Shift + Curriculum)