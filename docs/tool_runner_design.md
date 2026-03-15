# Tool Runner — Minimal Design Proposal

## Goal

- **Register** tools by name so the orchestrator can discover and invoke them.
- **Execute** tools safely: time limit, no traceback leakage, one structured result per run.
- **Log** every execution (tool name, duration, success/failure) for debugging and auditing.

Keep the design simple, explicit, and easy to debug.

---

## Contract

### 1. Registry

- **Register**: `register(name, execute, description="")` — store a callable under a string name. Overwriting the same name is allowed.
- **Lookup**: `get(name)` → the tool entry or `None`.
- **List**: `list_tools()` → list of `{name, description}` for all registered tools.

No file I/O, no plugins; the orchestrator (or tests) register tools at startup.

### 2. Execution

- **Input**: `run(tool_name, arguments)` where `arguments` is a dict passed as `**kwargs` to the tool.
- **Output**: Always a single **ToolResult** (see below). No exceptions thrown to the caller; failures are reflected in the result.
- **Safety**: Run in a dedicated thread with a **timeout** (e.g. 30s). On timeout or exception, return a failed result with a short error message (no raw traceback).

### 3. ToolResult (structured result)

| Field              | Type   | Purpose |
|--------------------|--------|--------|
| `success`          | bool   | Whether the tool completed without error. |
| `output`           | any    | Return value on success; `None` on failure. |
| `error`            | str?   | Short message on failure; `None` on success. |
| `tool_name`        | str    | Name of the tool that was run. |
| `duration_seconds` | float  | Wall-clock time for the run. |

Optional: `request_id` for correlation later. Keep it optional so the scaffold stays minimal.

### 4. Logging

- One log line per execution, after the run finishes.
- Include: `tool_name`, `duration_seconds`, `success`, and on failure the `error` message.
- Do not log full arguments (may be sensitive).
- Use a single logger (e.g. `services.tool_runner`); the orchestrator can attach a file handler to `data/logs/`.

---

## Flow (single run)

1. Receive `(tool_name, arguments)`.
2. Look up tool; if missing → immediate failed result + log warning.
3. Submit `execute(**arguments)` to a worker thread; wait with timeout.
4. On success: build result with `output`, log info.
5. On timeout or exception: build result with `error`, log warning/error.
6. Return the same result type in all cases so callers can branch on `success` only.

---

## Smallest useful scaffold

- **One result type**: `ToolResult` (Pydantic).
- **One registry**: in-memory dict; `register` / `get` / `list_tools`.
- **One runner**: `ToolRunner(registry).run(tool_name, arguments)` → `ToolResult`; internal timeout and logging only.
- **One example tool**: e.g. `echo` with `execute(message="")` → `{"echoed": message}`.
- **HTTP**: orchestrator exposes `GET /tools` and `POST /tools/execute`; no extra layers.

No auth, no rate limit, no persistence of results in this scaffold. Easy to add later.

---

## Implementation

| Piece        | Location |
|-------------|----------|
| Design      | This document. |
| Registry + Runner + ToolResult | `services/tool_runner.py` |
| Public API  | `services/__init__.py` (re-export) |
| Example tool| `tools/echo.py` |
| Wiring      | `apps/orchestrator/main.py` (registry, runner, routes, log file) |

Debugging: set log level to INFO and watch `tool_run tool=... duration=... success=...`; use `ToolResult.success` and `ToolResult.error` in code or responses.

---

## Tests

- **Location**: `tests/test_tool_runner.py` (stdlib `unittest`; no extra deps).
- **Run from project root**: `python -m unittest discover -s tests -v`
- **Coverage**: successful execution, unknown tool, tool failure (exception), timeout behavior.
