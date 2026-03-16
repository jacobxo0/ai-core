# AI-CORE stabilization and execution plan

Principal-architect view: take control of the current situation, verify real state, stabilize local workflow, and stop scope creep until the core is solid.

---

## 1. Strategic intent (current phase)

**Goal right now:** Stabilize the local dev workflow, verify repo state, verify Python execution on Windows, verify tests and app startup, verify command flow, and align documentation with implementation.

**Not in scope until the core is verified and documented:**

- Scheduler, memory store, model gateway, Ollama, OpenClaw integration, UI, Redis/Kafka/Celery/vector DB/LangChain, microservices, agent swarms.

AI-CORE is a local-first orchestration platform and eventual personal AI operating layer. It is not a chatbot, not tightly coupled to OpenClaw, and must not hardwire model logic throughout the codebase. It should evolve from a small, debuggable local core.

---

## 2. Verified current state (as of this plan)

| Area | State |
|------|--------|
| **Orchestrator** | FastAPI app in `apps/orchestrator/main.py`. Routes: `GET /`, `GET /tools`, `POST /tools/execute`, `POST /command`. Single execution path via `_run_command()` → `ToolResult` JSON. |
| **Tool runner** | `services/tool_runner.py`: ToolRegistry, ToolRunner, timeout (default 30s), ToolResult (success, output, error, tool_name, duration_seconds, request_id). One log line per run. |
| **Tools** | `echo` (tools/echo.py), `healthcheck` (tools/healthcheck.py). Both registered at startup. |
| **Command contract** | `POST /command` accepts `{ "command": str, "arguments": dict, "request_id": str \| null }`. Response: ToolResult. Documented in `docs/command_contract.md`. |
| **Logging** | File handler: `data/logs/ai_core.log` (services logger). Directory created at startup. |
| **Tests** | `tests/test_tool_runner.py`: 10 tests (runner, registry, command endpoint including echo, healthcheck, request_id, unknown tool). Run with `py -m unittest discover -s tests -v`. |
| **Dependencies** | `requirements.txt`: fastapi, uvicorn, pydantic, httpx (for TestClient). Install: `py -m pip install -r requirements.txt`. |
| **Deploy** | Dockerfile (Python 3.11-slim, PORT/0.0.0.0), .dockerignore. Docs: deployment_plan.md, openclaw-railway-reference.md. |
| **Docs** | architecture_roadmap.md, next_phase_plan.md, command_contract.md, command_endpoint_proposal.md, tool_runner_design.md. |

**Environment facts:**

- On Windows, `python` is not reliably in PATH in some shells; **`py`** works (Python 3.11).
- Use **`py -m pip`**, **`py -m uvicorn`**, **`py -m unittest`** for install, run, and tests.
- Git: may or may not be initialized in the project folder; if you see "not a git repository", run `git init` in the repo root and add remote when ready to push.

---

## 3. Exact verification runbook

Run these in order from the **project root** (`c:\...\AI-core` or your actual repo path). All commands assume Windows with `py` available.

| Step | Command | Expected outcome |
|------|---------|-------------------|
| 1 | `py -m pip install -r requirements.txt` | Install completes without error. |
| 2 | `py -m unittest discover -s tests -v` | 10 tests, all OK. |
| 3 | `py -m uvicorn apps.orchestrator.main:app --host 0.0.0.0 --port 8000` | Server starts; no traceback. |
| 4 | (Browser or curl) `GET http://localhost:8000/` | `{"status":"AI core running"}`. |
| 5 | `GET http://localhost:8000/tools` | JSON with `tools` array containing echo and healthcheck. |
| 6 | `POST http://localhost:8000/command` body `{"command":"healthcheck","arguments":{}}` | 200, ToolResult with `success: true`, `output.status: "ok"`, `output.components` array. |
| 7 | `POST http://localhost:8000/command` body `{"command":"echo","arguments":{"message":"hi"},"request_id":"req-1"}` | 200, ToolResult with `request_id: "req-1"`, `output.echoed: "hi"`. |

If any step fails, fix that before changing scope or adding features.

---

## 4. Local dev workflow (canonical)

1. **Open terminal** at project root.
2. **Install (once or after dependency change):**  
   `py -m pip install -r requirements.txt`
3. **Run tests:**  
   `py -m unittest discover -s tests -v`
4. **Start app:**  
   `py -m uvicorn apps.orchestrator.main:app --host 0.0.0.0 --port 8000`  
   (Use `--reload` only if you want auto-restart on code change; not required for stability.)
5. **Hit** `GET /`, `GET /tools`, `POST /command` as above.

No `python` or `uvicorn` in PATH required; `py -m` is the contract.

---

## 5. Documentation alignment

- **README.md** must reflect: (1) use `py` on Windows for pip/uvicorn/unittest, (2) `POST /command` as the primary command API (in addition to `/tools/execute`), (3) healthcheck tool exists, (4) tests require `httpx` (in requirements.txt). Quick start should not assume `python` or bare `uvicorn` on Windows.
- **docs/command_contract.md** is the single reference for `POST /command` request/response; keep it in sync with `CommandRequest` and `ToolResult` in code.
- **docs/next_phase_plan.md** and **docs/architecture_roadmap.md** describe future phases; do not implement scheduler, memory, gateway, or adapters until the verification runbook passes and README is updated.

---

## 6. Gaps and fixes (no new features)

| Gap | Fix |
|-----|-----|
| README says `python` and `uvicorn` | Update to `py -m pip`, `py -m uvicorn`, `py -m unittest` and note Windows. Add `POST /command` and healthcheck. |
| README quick start shows only `/tools/execute` | Add `/command` example (e.g. healthcheck). |
| Git repo possibly not initialized | If `git status` fails with "not a git repository", run `git init` in repo root; add `.gitignore` (already present); add remote when ready. |
| `.env` | Optional; copy `.env.example` to `.env` if you need env vars. No env vars required for minimal run. |

---

## 7. Out of scope until stable

Do **not** add or design in code/docs for this phase:

- Scheduler, memory/incident store, model gateway, Ollama, OpenClaw wiring, web UI, CLI adapter, webhooks, Redis/Kafka/Celery/vector DB/LangChain, multi-agent systems, background workers.

The "self-improving cycle" and remote interfaces are later. Current phase: **stable local core, verified runbook, aligned docs.**

---

## 8. Success criteria for this phase

- [x] All 7 runbook steps pass on the machine(s) you use. *(Verified: install, 10 tests OK, server start, GET /, GET /tools, POST /command healthcheck, POST /command echo+request_id.)*
- [x] README quick start uses `py` and includes `/command` and healthcheck.
- [x] No new features merged until the runbook is green and README is updated.
- [x] Git state clear: repo initialiseret, første commit. Til deploy: tilføj remote (`git remote add origin <url>`), evt. `git branch -M main`, og `git push -u origin main`.

After that, the next phase (e.g. one more tool, scheduler stub, or deployment) can be planned from a known-good base.
