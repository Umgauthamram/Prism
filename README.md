# prism 🌈

**Prism** is an OpenEnv-native Reinforcement Learning environment designed for training reliable, multi-agent LLM systems. Submission for the Meta × PyTorch × Hugging Face OpenEnv AI Hackathon 2026.

## Failure Modes Addressed
- **Multi-Agent Coordination Stress**: Trains agents to use structured shared-state protocols instead of noisy peer-to-peer negotiation.
- **Long-Horizon Planning Failures**: Evaluates the ability to recover from atomic failures (crashes, timeouts) using transaction discipline (checkpoints, rollbacks).
- **Domain Specialization**: Forces cross-domain generalization through a dynamic curriculum that shifts tasks and increases scale as the agent improves.

## Quickstart
```bash
# 1. Start the backend
uvicorn backend.server:app --port 8000 --reload

# 2. Start the dashboard (in a new tab)
cd website && npm run dev

# 3. Start training (in a third tab)
python training/grpo_train.py
```

## API Reference
| Endpoint | Method | Body | Response |
|----------|--------|------|----------|
| `/reset` | POST | `{"seed": int, "options": dict}` | Initial Observation |
| `/step` | POST | `{"action": {"tool": str, "args": dict}}` | Step Result (obs, reward, etc) |
| `/state` | GET | None | Full episode snapshot |
| `/metrics` | GET | None | Reward history and transfer scores |

## Reward Model
| Component | Weight | Measure |
|-----------|--------|---------|
| Progress Delta | 0.40 | Forward progress in task graph |
| Atomic Health | 0.20 | Transaction discipline (checkpoints vs orphans) |
| Coord Efficiency | 0.20 | Information density in shared state |
| Hallucination | 0.10 | Factual consistency (from Critic tool) |
| Terminal Bonus | 0.10 | Task-specific grader score |

## Task Domains
- **Software Debugging**: Fixing Python logic bugs. Grader: Automated test pass rate.
- **Market Research**: Competitive analysis. Grader: Rubric-based information coverage.
- **ETL Pipeline**: Data transformation script construction. Grader: Schema and row-level accuracy.

## Curriculum Stages
| Stage | Failure Rate | Agents | Domains | Threshold |
|-------|--------------|--------|---------|-----------|
| 0 | 0.0 | 2 | Debug | 0.45 |
| 1 | 0.2 | 2 | Debug, ETL | 0.55 |
| 2 | 0.2 | 4 | All Three | 0.65 |
| 3 | 0.5 | 8 | All + Held-out | 0.75 |

## Docker
```bash
docker compose up --build
```

## OpenEnv Compliance
- [x] Implements `/reset`, `/step`, `/state`.
- [x] `step()` returns standard OpenEnv tuple.
- [x] Scalar reward emitted every step.
- [x] Deterministic episode generation via seed.
- [x] Exposes port 8000 for training integration.



python -m venv .venv

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
uvicorn backend.server:app --reload --port 8000


docker compose up --build


Tip for your presentation:
In your hackathon video or write-up, you can use that screenshot to explain:

"Our environment (Prism) uses a multi-agent coordination reward. Here we see an agent that managed to run tests and verify, but failed to properly document the fix (write_fix), leading to a lower overall reward. Our RL training loop specifically targets these coordination gaps."