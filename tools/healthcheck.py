"""Healthcheck tool: returns status and component list for operational checks."""


def execute() -> dict:
    """Return a small structured payload for health/readiness checks."""
    return {
        "status": "ok",
        "components": ["orchestrator", "tool_runner"],
    }
