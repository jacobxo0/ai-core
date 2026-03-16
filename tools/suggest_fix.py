"""Suggest fix tool — uses model gateway + incident history to suggest a fix."""
from typing import Any

_memory = None
_gateway = None


def set_memory(memory) -> None:
    global _memory
    _memory = memory


def set_gateway(gateway) -> None:
    global _gateway
    _gateway = gateway


def execute(
    error: str = "",
    tool_name: str = "",
    context_limit: int = 5,
) -> dict[str, Any]:
    if _gateway is None or not _gateway.is_configured():
        return {
            "success": False,
            "error": "model gateway not configured (set OLLAMA_BASE_URL)",
            "suggestion": None,
        }

    # Gather past failures for context
    context_runs: list[dict] = []
    if _memory:
        context_runs = _memory.query_runs(
            failed_only=True,
            limit=int(context_limit),
            tool_name=tool_name or None,
        )

    context_str = ""
    if context_runs:
        context_str = "\nPast similar failures:\n" + "\n".join(
            f"  - tool={r['tool_name']} error={r['error']} at={r['timestamp']}"
            for r in context_runs
        )

    prompt = (
        f"You are an AI assistant helping debug tool execution failures in an orchestration system.\n"
        f"Current error:\n"
        f"  tool: {tool_name or 'unknown'}\n"
        f"  error: {error or 'no error message provided'}\n"
        f"{context_str}\n"
        f"Suggest a concise fix or next debugging step in 2-3 sentences:"
    )

    try:
        suggestion = _gateway.complete(prompt, max_tokens=256)
        return {
            "success": True,
            "suggestion": suggestion,
            "context_runs_used": len(context_runs),
        }
    except Exception as exc:
        return {"success": False, "error": str(exc), "suggestion": None}
