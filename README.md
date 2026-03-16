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

| Component       | Role |
|----------------|------|
| **Orchestrator** | Main API entrypoint (FastAPI). `POST /command`, `GET /tools`, `GET /runs`, `GET /ui`, `GET /scheduler`. |
| **Runner**       | Tool runner — executes tools with timeout, returns `ToolResult`, logs every run. |
| **Memory**       | SQLite incident store (`data/memory.db`). Persists every run; queryable via `/runs` or `query_runs` tool. |
| **Scheduler**    | In-process cron — triggers tools on configurable intervals. Healthcheck every 5 min by default. |
| **Gateway**      | Model gateway — wraps Ollama behind a single interface. Set `OLLAMA_BASE_URL` to enable. |
| **Adapters**     | CLI (`py -m adapters.cli`) and Webhook (`POST /webhook/trigger`) — both translate to the same `/command` contract. |

## Tech stack

- **Python 3.11** — Runtime.
- **FastAPI** — HTTP API and orchestrator.
- **SQLite** — Local persistence for run history (`data/memory.db`).
- **psutil** — System metrics for `system_info` tool.
- **Ollama** — Optional local LLM via `OLLAMA_BASE_URL` (model gateway).

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
2. **Optional:** Copy `.env.example` to `.env` and adjust (no env vars required for minimal run).
3. **Start:** `py -m uvicorn apps.orchestrator.main:app --host 0.0.0.0 --port 8000`
4. **Try:**

| What | How |
|------|-----|
| Root status | `GET /` |
| List tools | `GET /tools` |
| Run a tool | `POST /command` `{"command":"healthcheck","arguments":{}}` |
| System info | `POST /command` `{"command":"system_info","arguments":{}}` |
| Run history | `GET /runs?failed=false&limit=20` |
| Live dashboard | `GET /ui` (browser) |
| Scheduler status | `GET /scheduler` |
| Model gateway | `GET /gateway/status` |
| CLI adapter | `py -m adapters.cli healthcheck` |
| Webhook | `POST /webhook/trigger` `{"command":"echo","arguments":{"message":"hi"}}` |

**Tests** (from project root): `py -m unittest discover -s tests -v`
Currently: **57 tests, all passing.**

## Registered tools

| Tool | Description |
|------|-------------|
| `echo` | Echoes a message (demo) |
| `healthcheck` | System health status |
| `system_info` | CPU, memory, disk, platform |
| `run_check` | Run a shell command (local only) |
| `fetch_url` | HTTP GET a URL |
| `query_runs` | Query run history from memory store |
| `suggest_fix` | Ask Ollama to suggest a fix (requires `OLLAMA_BASE_URL`) |

**Værktøjer til terminal/agent:** Hvis `git` eller `py` ikke findes i PATH, kør install-kommandoerne i [docs/agent_tools_setup.md](docs/agent_tools_setup.md) én gang og genstart terminalen.

## Deploy til Railway

AI-CORE er klar til deploy (Dockerfile, `requirements.txt`, `0.0.0.0` + `PORT`). Fuld beskrivelse: [docs/deployment_plan.md](docs/deployment_plan.md).

1. **Push** — Tilføj remote: `git remote add origin <din-repo-url>`, evt. `git branch -M main`, derefter `git push -u origin main`.
2. **Railway** — Nyt projekt → Deploy from GitHub repo → vælg AI-CORE. Railway bygger fra Dockerfile.
3. **Domain** — Generate Domain for servicen; notér URL (fx `https://ai-core-xxx.railway.app`) som **AI_CORE_URL**.
4. **Bind Clawrunner** — I Clawrunner (Railway): sæt miljøvariabel **AI_CORE_URL** til den URL. Se [docs/openclaw_installation_plan.md](docs/openclaw_installation_plan.md) for hvad der mangler for at få det helt oppe (domain, webhook, stabil gateway).
