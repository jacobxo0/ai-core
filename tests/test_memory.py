"""Tests for services/memory.py — MemoryStore."""
import os
import tempfile
import unittest

from services.memory import MemoryStore
from services.tool_runner import ToolResult


def _make_result(tool="echo", success=True, error=None, request_id=None, duration=0.001):
    return ToolResult(
        success=success,
        output={"msg": "hi"} if success else None,
        error=error,
        tool_name=tool,
        duration_seconds=duration,
        request_id=request_id,
    )


class TestMemoryStore(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.store = MemoryStore(self._tmp.name)

    def tearDown(self):
        # Explicitly close all connections before deletion (required on Windows)
        self.store = None
        try:
            os.unlink(self._tmp.name)
        except PermissionError:
            pass  # Windows: SQLite WAL may still hold handle; file is temp, OS will clean it

    def test_write_and_query_all(self):
        self.store.write_run(_make_result("echo", success=True))
        self.store.write_run(_make_result("healthcheck", success=True))
        runs = self.store.query_runs()
        self.assertEqual(len(runs), 2)
        self.assertEqual({r["tool_name"] for r in runs}, {"echo", "healthcheck"})

    def test_failed_only_filter(self):
        self.store.write_run(_make_result("echo", success=True))
        self.store.write_run(_make_result("echo", success=False, error="boom"))
        runs = self.store.query_runs(failed_only=True)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["error"], "boom")

    def test_tool_name_filter(self):
        self.store.write_run(_make_result("echo"))
        self.store.write_run(_make_result("healthcheck"))
        self.store.write_run(_make_result("echo"))
        runs = self.store.query_runs(tool_name="echo")
        self.assertEqual(len(runs), 2)
        self.assertTrue(all(r["tool_name"] == "echo" for r in runs))

    def test_limit(self):
        for _ in range(10):
            self.store.write_run(_make_result("echo"))
        runs = self.store.query_runs(limit=3)
        self.assertEqual(len(runs), 3)

    def test_request_id_stored(self):
        self.store.write_run(_make_result("echo", request_id="req-abc"))
        runs = self.store.query_runs()
        self.assertEqual(runs[0]["request_id"], "req-abc")

    def test_stats(self):
        self.store.write_run(_make_result("echo", success=True))
        self.store.write_run(_make_result("echo", success=False, error="err"))
        self.store.write_run(_make_result("healthcheck", success=True))
        stats = self.store.stats()
        self.assertEqual(stats["total_runs"], 3)
        self.assertEqual(stats["failed_runs"], 1)
        self.assertEqual(stats["unique_tools"], 2)

    def test_empty_store(self):
        runs = self.store.query_runs()
        self.assertEqual(runs, [])
        stats = self.store.stats()
        self.assertEqual(stats["total_runs"], 0)


if __name__ == "__main__":
    unittest.main()
