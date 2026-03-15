# AI-CORE Next Phase Plan

## 1. Current foundation

**Implemented and stable:**

- **Orchestrator** (`apps/orchestrator/main.py`): FastAPI app with `GET /`, `GET /tools`, `POST /tools/execute`, `POST /command`. Single execution path via `_run_command(tool_name, arguments)` returning `ToolResult` as JSON. Log file handler for `data/logs/ai_core.log` on the `services` logger.
- **Tool runner** (`services/tool_runner.py`): `ToolRegistry` (register, get, list_tools), `ToolRunner.run(tool_name, arguments, request_id=None)` with configurable timeout (default 30s), `ToolResult` (success, output, error, tool_name, duration_seconds, request_id). One structured log line per run (INFO/WARNING/ERROR). ThreadPoolExecutor with max_workers=1 for serialized, debuggable execution.
- **Example tool**: `tools/echo.py` — `execute(message="")` → `{"echoed": message}`. Registered at startup.
- **Tests** (`tests/test_tool_runner.py`): stdlib unittest. Covers: successful execution, unknown tool, tool failure, timeout; registry register/get/list_tools; `POST /command` (echo success, unknown tool failure). Run from project root: `python -m unittest discover -s tests -v`.
- **Docs**: `docs/tool_runner_design.md`, `docs/command_endpoint_proposal.md`. No scheduler, memory, or LLM code.

**Stable to build on:** ToolResult contract, registry/runner API, single `_run_command` path, one-log-per-run behavior.

**Gaps before “minimal orchestration platform”:**

- Command request body does not yet include optional `request_id` (ToolResult supports it; orchestrator does not pass it).
- Only one tool (echo); no “useful” non-demo tool (e.g. healthcheck).
- No single documented “standard command contract” (request/response shape and semantics).

**Technical risks:**

- **Single worker**: Runner uses one thread; concurrent requests queue. Acceptable for current scale; revisit if load grows.
- **No argument validation**: Tools receive `**arguments`; invalid keys may raise. Tool runner catches and returns error string; no schema validation yet. Document and add later if needed.
- **Import path**: Tests assume run from project root so `services` and `apps` resolve. Document in README/tests; keep `apps/__init__.py` and `apps/orchestrator/__init__.py` in place.

---

## 2. Next implementation goals

1. **Complete the command contract**: Add optional `request_id` to the command request and pass it through to `ToolResult` for correlation and debugging.
2. **One useful non-demo tool**: Add a healthcheck tool (e.g. returns status, optional dependency checks) so the platform has a real operational tool beyond echo.
3. **Standard command contract**: Document the canonical request/response for `POST /command` (and optionally `/tools/execute`) so clients and future components have one reference.

No scheduler, memory, model gateway, or external adapters in this phase.

---

## 3. Recommended build order

1. **Add optional `request_id` to command** — Extend `CommandRequest` with `request_id: str | None = None`; pass it into `_run_command` and thence to `runner.run(..., request_id=...)`. Returned `ToolResult` already includes `request_id`. No new services or concepts.
2. **Add healthcheck tool** — New tool in `tools/` (e.g. `healthcheck.py`) that returns a small structured payload (e.g. status, version or component list). Register it in the orchestrator. Add a test that calls it via the runner or `/command`.
3. **Document standard command contract** — Add a short section in `docs/` or extend `command_endpoint_proposal.md`: exact request body (command, arguments, optional request_id), response body (ToolResult fields), and that command is resolved directly to a registered tool name.

---

## 4. Why this order is safest

- **request_id first**: Zero new concepts; completes the existing ToolResult/command contract and improves traceability. Easy to test (send request_id, assert it in response).
- **Healthcheck second**: First real tool beyond echo; validates the tool pipeline end-to-end without touching scheduler or memory. Keeps the “one useful tool” requirement satisfied before any new subsystems.
- **Document contract third**: Locks the current behavior as the standard so future work (scheduler, adapters) can depend on a stable command API. No code change to execution path.

Deferring scheduler, memory, and gateway until the command surface is stable and at least two tools exist keeps the foundation minimal and debuggable.

---

## 5. What to postpone

- **Scheduler** — When to run what; cron-like or queue. Postpone until command contract and at least one useful tool are in place.
- **Memory / incident store** — Persisted context or failure history. Postpone until we have a concrete use case (e.g. “remember last N failures”).
- **Model gateway / Ollama** — LLM integration. Postpone per constraints.
- **External adapters** — OpenClaw, CLI, webhooks. Postpone until core command flow is stable.
- **Background workers, Celery, Redis, Kafka, event buses, vector DBs, LangChain** — Not in scope; avoid unless justified as the smallest safe next step.
- **Multi-agent systems** — Out of scope for this phase.

---

## 6. Testing strategy

- **Keep stdlib unittest**; no pytest unless already in use (currently not). Run from project root: `python -m unittest discover -s tests -v`.
- **After request_id**: Add one test that POSTs `/command` with `request_id` set and asserts the same value in the response JSON.
- **After healthcheck**: Add a test that runs the healthcheck tool (via runner or `/command`) and asserts success and expected keys in output.
- **No new test framework or coverage tool** in this phase; keep tests minimal and fast.

---

## 7. Logging / observability strategy

- **Keep current behavior**: One log line per tool run in `services.tool_runner` (tool name, duration, success, error if any). No argument logging. Orchestrator continues to attach a file handler to `data/logs/ai_core.log` for the services logger.
- **Optional**: When `request_id` is present, include it in the log line (e.g. `request_id=%s`) for correlation. Implement only if adding request_id to the request body; do not add separate tracing infra.

---

## 8. Smallest useful orchestration milestone

We can call the system a **minimal orchestration platform** when:

- One canonical command endpoint: `POST /command` with body `{ "command": str, "arguments": dict, "request_id": str | null }`.
- Every command is resolved to a registered tool by name and executed via the existing tool runner; response is always a `ToolResult` (success, output, error, tool_name, duration_seconds, request_id).
- At least two tools are registered: one demo (echo) and one useful (e.g. healthcheck).
- All existing tests pass, plus one test for request_id and one for the new tool.
- Standard command contract is documented.

No scheduler, memory, or LLM are required for this milestone.
