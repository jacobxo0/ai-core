# AI-Core

Local-first AI orchestration system.

## Purpose

Run agents, tools, and schedulers locally with minimal external dependency. Orchestration, execution, and (optionally) LLM inference stay on your machine; Ollama and SQLite support integration when needed.

## Architecture principles

- **Modular services** — Orchestrator, runner, scheduler, memory, and gateway are separate concerns; compose via clear interfaces.
- **Tool-based execution** — Work is done by registered tools; the runner executes them safely (timeouts, structured results, logging).
- **Explicit logging** — Tool runs and key events are logged; logs go to `data/logs/` and the configured handlers.
- **Simple before complex** — Add features only when needed; keep APIs and data flows easy to follow.

## Core components

| Component   | Role |
|------------|------|
| **Orchestrator** | Main API and workflow entrypoint (FastAPI). Exposes `/`, `GET /tools`, `POST /tools/execute`, and `POST /command` (canonical command API). |
| **Runner**       | Tool runner service. Registers tools, runs them with timeouts and validation, returns structured results, logs executions. |
| **Scheduler**    | When to run what (cron-like or queue-based). *Planned.* |
| **Memory**       | Persisted context for agents (e.g. SQLite). *Planned.* |
| **Gateway**      | Adapter layer to LLMs (e.g. Ollama). *Planned.* |

## Tech stack

- **Python** — Runtime.
- **FastAPI** — HTTP API and orchestrator.
- **SQLite** — Local persistence (e.g. memory, artifacts). *Planned.*
- **Ollama** — Local LLM integration. *Planned.*

## Repository layout

- **apps/orchestrator** — Orchestrator app and routes.
- **services** — Shared services (e.g. tool runner).
- **tools** — Tool implementations (e.g. `echo`).
- **adapters** — Pluggable backends (e.g. Ollama). *Planned.*
- **prompts** — Prompt templates for agents. *Planned.*
- **infra** — Config and deployment. *Planned.*
- **data** — Logs, SQLite DBs, artifacts (gitignored).

## Quick start

1. **Install** (from project root): `py -m pip install -r requirements.txt`  
   On Windows, use `py` if `python` is not in PATH.
2. **Optional:** Copy `.env.example` to `.env` and adjust if needed (no env vars required for minimal run).
3. **Start:** `py -m uvicorn apps.orchestrator.main:app --host 0.0.0.0 --port 8000`
4. **Try:**  
   - `GET /` → `{"status":"AI core running"}`  
   - `GET /tools` → list of tools (echo, healthcheck)  
   - `POST /command` with `{"command": "healthcheck", "arguments": {}}` or `{"command": "echo", "arguments": {"message": "hello"}}`  
   - See [docs/command_contract.md](docs/command_contract.md) for the full request/response contract.

**Tests** (from project root): `py -m unittest discover -s tests -v`

## Deploy til Railway

AI-CORE er klar til deploy (Dockerfile, `requirements.txt`, `0.0.0.0` + `PORT`). Fuld beskrivelse: [docs/deployment_plan.md](docs/deployment_plan.md).

1. **Push** — `git push origin main` så repoet er på GitHub.
2. **Railway** — Nyt projekt → Deploy from GitHub repo → vælg AI-CORE. Railway bygger fra Dockerfile.
3. **Domain** — Generate Domain for servicen; notér URL (fx `https://ai-core-xxx.railway.app`).
4. **Bind Clawrunner** — I Clawrunner: sæt miljøvariabel **AI_CORE_URL** til den URL fra skridt 3.
