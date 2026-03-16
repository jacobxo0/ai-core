"""Query runs tool — query recent tool runs from the memory store."""
from typing import Any

_memory = None


def set_memory(memory) -> None:
    global _memory
    _memory = memory


def execute(
    failed_only: bool = False,
    limit: int = 20,
    tool_name: str = "",
) -> dict[str, Any]:
    if _memory is None:
        return {"success": False, "error": "memory store not configured", "runs": []}

    runs = _memory.query_runs(
        failed_only=bool(failed_only),
        limit=int(limit),
        tool_name=tool_name or None,
    )
    stats = _memory.stats()
    return {"runs": runs, "count": len(runs), "stats": stats}
