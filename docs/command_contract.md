# Standard command contract

Single reference for clients (e.g. Clawrunner, adapters) calling the orchestrator. See also [command_endpoint_proposal.md](command_endpoint_proposal.md).

---

## Endpoint

`POST /command`

## Request body

| Field        | Type           | Required | Description |
|--------------|----------------|----------|-------------|
| `command`    | string         | Yes      | Registered tool name (e.g. `echo`, `healthcheck`). Resolved directly to a tool in the registry. |
| `arguments`  | object         | Yes      | Key-value arguments passed to the tool as kwargs. May be `{}` if the tool takes no arguments. |
| `request_id` | string or null | No       | Optional correlation ID; returned in the response for tracing. |

Example:

```json
{ "command": "echo", "arguments": { "message": "hi" }, "request_id": "req-abc" }
```

## Response body

Always a `ToolResult` JSON (HTTP 200):

| Field               | Type            | Description |
|---------------------|-----------------|-------------|
| `success`           | boolean         | True if the tool ran without throwing. |
| `output`            | any             | Tool return value (e.g. dict); null if success is false. |
| `error`             | string or null  | Error message if success is false. |
| `tool_name`         | string          | The tool that was run. |
| `duration_seconds`  | number          | Execution time. |
| `request_id`        | string or null  | Echo of the request request_id if provided. |

## Semantics

The orchestrator resolves `command` to a registered tool by name and runs it via the tool runner with `arguments`. One request produces one ToolResult. Unknown tool names result in `success: false` and an error message.
