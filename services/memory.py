"""Memory / incident store. Persists every tool run to SQLite for query and observability."""
import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from services.tool_runner import ToolResult

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name        TEXT    NOT NULL,
    success          INTEGER NOT NULL,
    error            TEXT,
    request_id       TEXT,
    timestamp        TEXT    NOT NULL,
    duration_seconds REAL,
    output_summary   TEXT
);
CREATE INDEX IF NOT EXISTS idx_runs_tool    ON runs(tool_name);
CREATE INDEX IF NOT EXISTS idx_runs_success ON runs(success);
CREATE INDEX IF NOT EXISTS idx_runs_ts      ON runs(timestamp);
"""


class MemoryStore:
    """SQLite-backed store for tool run history and incident tracking."""

    def __init__(self, db_path: str = "data/memory.db") -> None:
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.db_path = db_path
        self._init_db()
        logger.info("memory_store_init db=%s", db_path)

    # ── Internal ──────────────────────────────────────────────────────────────

    @contextmanager
    def _conn(self):
        """Context manager that opens, yields, commits, and closes the connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    # ── Write ─────────────────────────────────────────────────────────────────

    def write_run(self, result: ToolResult) -> None:
        """Persist a ToolResult to the runs table."""
        output_summary: str | None = None
        if result.output is not None:
            try:
                raw = json.dumps(result.output, default=str)
                output_summary = raw[:500]
            except Exception:
                output_summary = str(result.output)[:500]

        ts = datetime.now(timezone.utc).isoformat()
        try:
            with self._conn() as conn:
                conn.execute(
                    """INSERT INTO runs
                       (tool_name, success, error, request_id, timestamp, duration_seconds, output_summary)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        result.tool_name,
                        int(result.success),
                        result.error,
                        result.request_id,
                        ts,
                        result.duration_seconds,
                        output_summary,
                    ),
                )
        except Exception as exc:
            logger.error("memory_write_error error=%s", exc)

    # ── Query ─────────────────────────────────────────────────────────────────

    def query_runs(
        self,
        failed_only: bool = False,
        limit: int = 20,
        tool_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return recent runs ordered newest-first. Filters: failed_only, tool_name."""
        conditions: list[str] = []
        params: list[Any] = []

        if failed_only:
            conditions.append("success = 0")
        if tool_name:
            conditions.append("tool_name = ?")
            params.append(tool_name)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        params.append(max(1, int(limit)))

        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM runs {where} ORDER BY timestamp DESC LIMIT ?",
                params,
            ).fetchall()
        return [dict(row) for row in rows]

    def stats(self) -> dict[str, Any]:
        """Return aggregate stats: total runs, total failures, unique tools."""
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            failed = conn.execute("SELECT COUNT(*) FROM runs WHERE success=0").fetchone()[0]
            tools = conn.execute("SELECT COUNT(DISTINCT tool_name) FROM runs").fetchone()[0]
        return {"total_runs": total, "failed_runs": failed, "unique_tools": tools}
