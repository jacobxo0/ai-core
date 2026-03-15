"""Minimal tests for the tool runner. Run from project root: python -m unittest discover -s tests -v"""
import time
import unittest

from fastapi.testclient import TestClient

from apps.orchestrator.main import app
from services.tool_runner import ToolRegistry, ToolResult, ToolRunner


def _ok_tool(x: int = 0) -> dict:
    """Stub that returns a dict."""
    return {"value": x}


def _failing_tool() -> None:
    """Stub that raises."""
    raise ValueError("tool failed")


def _slow_tool(seconds: float = 1.0) -> str:
    """Stub that sleeps then returns."""
    time.sleep(seconds)
    return "done"


class TestToolRunner(unittest.TestCase):
    """Tool runner: success, unknown tool, failure, timeout."""

    def setUp(self) -> None:
        self.registry = ToolRegistry()
        self.registry.register("ok", _ok_tool, "Returns input.")
        self.registry.register("fail", _failing_tool, "Raises.")
        self.registry.register("slow", _slow_tool, "Sleeps.")
        self.runner = ToolRunner(self.registry, timeout_seconds=0.2)

    def test_successful_execution(self) -> None:
        result = self.runner.run("ok", {"x": 42})
        self.assertTrue(result.success)
        self.assertIsNone(result.error)
        self.assertEqual(result.tool_name, "ok")
        self.assertEqual(result.output, {"value": 42})
        self.assertGreaterEqual(result.duration_seconds, 0)

    def test_unknown_tool(self) -> None:
        result = self.runner.run("nonexistent", {})
        self.assertFalse(result.success)
        self.assertIn("Unknown tool", result.error or "")
        self.assertEqual(result.tool_name, "nonexistent")
        self.assertIsNone(result.output)

    def test_tool_failure(self) -> None:
        result = self.runner.run("fail", {})
        self.assertFalse(result.success)
        self.assertIn("tool failed", result.error or "")
        self.assertEqual(result.tool_name, "fail")
        self.assertIsNone(result.output)

    def test_timeout_behavior(self) -> None:
        result = self.runner.run("slow", {"seconds": 1.0})
        self.assertFalse(result.success)
        self.assertIn("timed out", result.error or "")
        self.assertEqual(result.tool_name, "slow")


class TestToolRegistry(unittest.TestCase):
    """Registry: register, get, list_tools."""

    def test_register_and_get(self) -> None:
        r = ToolRegistry()
        self.assertIsNone(r.get("x"))
        r.register("x", _ok_tool, "desc")
        entry = r.get("x")
        self.assertIsNotNone(entry)
        self.assertEqual(entry[1], "desc")

    def test_list_tools(self) -> None:
        r = ToolRegistry()
        r.register("a", _ok_tool, "first")
        r.register("b", _ok_tool, "second")
        listed = r.list_tools()
        names = [t["name"] for t in listed]
        self.assertIn("a", names)
        self.assertIn("b", names)
        self.assertEqual(len(listed), 2)


class TestCommandEndpoint(unittest.TestCase):
    """POST /command: command + arguments -> ToolResult shape."""

    def test_command_echo_returns_tool_result_shape(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/command",
            json={"command": "echo", "arguments": {"message": "hi"}},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("success", data)
        self.assertIn("tool_name", data)
        self.assertIn("duration_seconds", data)
        self.assertEqual(data["tool_name"], "echo")
        self.assertTrue(data["success"])
        self.assertEqual(data.get("output"), {"echoed": "hi"})

    def test_command_unknown_returns_failed_result(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/command",
            json={"command": "nonexistent", "arguments": {}},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("Unknown tool", data.get("error") or "")

    def test_command_request_id_returned_in_result(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/command",
            json={
                "command": "echo",
                "arguments": {"message": "hi"},
                "request_id": "req-123",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("request_id"), "req-123")
        self.assertTrue(data["success"])

    def test_command_healthcheck_returns_status_and_components(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/command",
            json={"command": "healthcheck", "arguments": {}},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["tool_name"], "healthcheck")
        output = data.get("output")
        self.assertIsInstance(output, dict)
        self.assertEqual(output.get("status"), "ok")
        self.assertIn("components", output)
        self.assertIsInstance(output["components"], list)
