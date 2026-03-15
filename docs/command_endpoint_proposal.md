# Command Endpoint — Smallest Useful Proposal

## Goal

Expose a single HTTP endpoint that accepts a **command** (e.g. run a named tool with arguments) and returns the tool result. This is the minimal “do one thing” API for the orchestrator beyond the existing `GET /` and `GET /tools` / `POST /tools/execute`.

## Why “command”

- One request = one intent: “run this tool with these arguments.”
- Fits agents and scripts that send a single action per request.
- No extra concepts (no jobs, queues, or sessions) in this step.

## Smallest useful shape

**Endpoint**: `POST /command` (or keep reusing `POST /tools/execute` and treat it as the command endpoint; see below).

**Request body** (same as today):

```json
{
  "tool": "<registered_tool_name>",
  "arguments": { ... }
}
```

**Response**: The existing `ToolResult` as JSON (success, output, error, tool_name, duration_seconds, optional request_id).

So the **smallest useful command endpoint** is: keep the current `POST /tools/execute` contract and optionally **alias** it as `POST /command` for clarity (same handler, same request/response). No new types, no new services.

## Optional alias

- Add `POST /command` that accepts the same body and calls the same `runner.run(...)` logic; return the same `ToolResult` JSON.
- Implementation: one extra route that delegates to the same function as `POST /tools/execute`, or a shared helper that both routes call.

## What we are not adding yet

- No “command history” or persistence.
- No multi-step or composite commands.
- No auth, no rate limiting.
- No separate command service or queue; the orchestrator stays the single entrypoint.

## Summary

- **Smallest useful**: Treat `POST /tools/execute` as the command endpoint, or add `POST /command` as an alias with identical behavior.
- **Request**: `{ "tool": string, "arguments": object }`.
- **Response**: `ToolResult` JSON.
- No extra architecture; implement by either documenting “use `/tools/execute` for commands” or adding one route that reuses the same handler.
