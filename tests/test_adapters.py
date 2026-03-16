"""Tests for adapters — webhook router and CLI argument parser."""
import unittest
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from fastapi import FastAPI

from adapters.webhook import router, set_run_fn
from adapters.cli import _parse_arguments
from services.tool_runner import ToolResult


def _make_tool_result(tool="echo", success=True):
    return ToolResult(
        success=success,
        output={"echoed": "hi"},
        error=None if success else "boom",
        tool_name=tool,
        duration_seconds=0.001,
        request_id=None,
    )


class TestWebhookAdapter(unittest.TestCase):
    def setUp(self):
        # Fresh app for each test to avoid shared state issues
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)

    def test_status_endpoint(self):
        resp = self.client.get("/webhook/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("adapter", data)
        self.assertEqual(data["adapter"], "webhook")

    def test_trigger_without_runner_returns_503(self):
        set_run_fn(None)
        resp = self.client.post("/webhook/trigger", json={"command": "echo", "arguments": {}})
        self.assertEqual(resp.status_code, 503)

    def test_trigger_calls_run_fn(self):
        mock_fn = MagicMock(return_value=_make_tool_result("echo"))
        set_run_fn(mock_fn)
        resp = self.client.post(
            "/webhook/trigger",
            json={"command": "echo", "arguments": {"message": "hi"}, "source": "test"},
        )
        self.assertEqual(resp.status_code, 200)
        mock_fn.assert_called_once()
        call_args = mock_fn.call_args[0]
        self.assertEqual(call_args[0], "echo")
        self.assertEqual(call_args[1], {"message": "hi"})

    def test_trigger_request_id_passthrough(self):
        mock_fn = MagicMock(return_value=_make_tool_result("echo"))
        set_run_fn(mock_fn)
        self.client.post(
            "/webhook/trigger",
            json={"command": "echo", "arguments": {}, "request_id": "custom-id-123"},
        )
        call_args = mock_fn.call_args[0]
        self.assertEqual(call_args[2], "custom-id-123")

    def test_trigger_generates_request_id_from_source(self):
        mock_fn = MagicMock(return_value=_make_tool_result("echo"))
        set_run_fn(mock_fn)
        self.client.post(
            "/webhook/trigger",
            json={"command": "echo", "arguments": {}, "source": "github"},
        )
        call_args = mock_fn.call_args[0]
        self.assertTrue(call_args[2].startswith("webhook:github"))


class TestCLIArgParser(unittest.TestCase):
    def test_string_value(self):
        result = _parse_arguments(["--message", "hello world"])
        self.assertEqual(result, {"message": "hello world"})

    def test_flag_only(self):
        result = _parse_arguments(["--verbose"])
        self.assertEqual(result, {"verbose": True})

    def test_json_coercion_bool(self):
        result = _parse_arguments(["--failed_only", "true"])
        self.assertEqual(result, {"failed_only": True})

    def test_json_coercion_int(self):
        result = _parse_arguments(["--limit", "10"])
        self.assertEqual(result, {"limit": 10})

    def test_multiple_args(self):
        result = _parse_arguments(["--message", "hi", "--timeout", "5"])
        self.assertEqual(result, {"message": "hi", "timeout": 5})

    def test_hyphen_to_underscore(self):
        result = _parse_arguments(["--failed-only", "true"])
        self.assertEqual(result, {"failed_only": True})

    def test_empty(self):
        result = _parse_arguments([])
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
