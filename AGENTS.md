# Agent Instructions: Prism Environment

This repository follows the **OpenEnv** specification. When working on this codebase, adhere to these rules:

### 1. Verification Workflow
- **Always** start the FastAPI server before testing the dashboard: `uvicorn backend.server:app --port 8000`.
- Verify the backend with `curl http://localhost:8000/health` before assuming bugs are in the frontend.
- Backend tests must pass `/reset` and `/step` before frontend modifications.

### 2. Implementation Standards
- **Python**: All functions must be type-annotated. No untyped dicts in signatures.
- **Tools**: All tool results MUST include `{"success": bool, "data": any, "latency_ms": int}`.
- **Rewards**: Every reward component must be a float clamped to the interval `(0.01, 0.99)` for numerical stability in RL training.
- **TypeScript**: `strict` mode is mandatory. Use `any` only as a last resort (preferably never).
- **API**: All data fetching in the frontend MUST go through `website/lib/api.ts`.

### 3. Repository Structure
- `backend/`: Core environment logic, injectors, and task generators.
- `website/`: Next.js dashboard for real-time training visualization.
- `training/`: Reference training scripts and evaluation harnesses.
- `Dockerfile`: Multi-stage build for unified deployment.

### 4. Reward & Injectors
The environment is designed to be adversarial. `Injector 1` (Coordination) and `Injector 2` (Atomic Failure) are active components that the agent must learn to mitigate to maximize reward. Do not "soften" these injectors; they are core to the training objective.
