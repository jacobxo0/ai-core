"""Tests for new operational tools."""
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch


class TestSystemInfo(unittest.TestCase):
    def test_returns_expected_keys(self):
        from tools.system_info import execute
        result = execute()
        self.assertIn("cpu_percent", result)
        self.assertIn("memory", result)
        self.assertIn("disk", result)
        self.assertIn("platform", result)
        self.assertIn("cpu_count", result)

    def test_memory_keys(self):
        from tools.system_info import execute
        result = execute()
        mem = result["memory"]
        for key in ("total_gb", "used_gb", "available_gb", "percent"):
            self.assertIn(key, mem)

    def test_disk_keys(self):
        from tools.system_info import execute
        result = execute()
        disk = result["disk"]
        for key in ("total_gb", "used_gb", "free_gb", "percent"):
            self.assertIn(key, disk)


class TestRunCheck(unittest.TestCase):
    def test_successful_command(self):
        from tools.run_check import execute
        # Use a cross-platform command
        cmd = "echo hello"
        result = execute(command=cmd)
        self.assertIn("returncode", result)
        self.assertIn("stdout", result)
        self.assertTrue(result["success"])

    def test_no_command(self):
        from tools.run_check import execute
        result = execute(command="")
        self.assertFalse(result["success"])
        self.assertIn("error", result)

    def test_failing_command(self):
        from tools.run_check import execute
        # Exit 1 on all platforms
        result = execute(command="exit 1", timeout=5)
        self.assertIn("returncode", result)

    def test_timeout(self):
        import sys
        from tools.run_check import execute
        # Sleep longer than timeout
        cmd = "python -c \"import time; time.sleep(5)\"" if sys.platform == "win32" else "sleep 5"
        result = execute(command=cmd, timeout=1)
        self.assertFalse(result["success"])
        self.assertIn("timed out", result["error"])


class TestFetchUrl(unittest.TestCase):
    def test_no_url(self):
        from tools.fetch_url import execute
        result = execute(url="")
        self.assertFalse(result["success"])
        self.assertIn("error", result)

    def test_successful_fetch(self):
        from tools.fetch_url import execute
        import httpx

        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.status_code = 200
        mock_resp.url = "https://example.com"
        mock_resp.headers = {"content-type": "text/html"}
        mock_resp.text = "<html>ok</html>"
        mock_resp.elapsed.total_seconds.return_value = 0.1

        with patch("tools.fetch_url.httpx.get", return_value=mock_resp):
            result = execute(url="https://example.com")

        self.assertTrue(result["success"])
        self.assertEqual(result["status_code"], 200)
        self.assertIn("body_preview", result)

    def test_timeout_error(self):
        from tools.fetch_url import execute
        import httpx

        with patch("tools.fetch_url.httpx.get", side_effect=httpx.TimeoutException("timeout")):
            result = execute(url="https://example.com", timeout=1)

        self.assertFalse(result["success"])
        self.assertIn("timed out", result["error"])


class TestQueryRuns(unittest.TestCase):
    def test_no_memory_configured(self):
        import tools.query_runs as qr
        original = qr._memory
        qr._memory = None
        try:
            result = qr.execute()
            self.assertFalse(result["success"])
            self.assertIn("not configured", result["error"])
        finally:
            qr._memory = original

    def test_with_mock_memory(self):
        import tools.query_runs as qr
        mock_mem = MagicMock()
        mock_mem.query_runs.return_value = [{"tool_name": "echo", "success": 1}]
        mock_mem.stats.return_value = {"total_runs": 1, "failed_runs": 0, "unique_tools": 1}

        original = qr._memory
        qr.set_memory(mock_mem)
        try:
            result = qr.execute(limit=5)
            self.assertEqual(result["count"], 1)
            self.assertEqual(len(result["runs"]), 1)
        finally:
            qr.set_memory(original)


class TestSuggestFix(unittest.TestCase):
    def test_no_gateway_configured(self):
        import tools.suggest_fix as sf
        original_gw = sf._gateway
        sf._gateway = None
        try:
            result = sf.execute(error="something broke", tool_name="echo")
            self.assertFalse(result["success"])
            self.assertIn("not configured", result["error"])
        finally:
            sf._gateway = original_gw

    def test_gateway_not_configured_instance(self):
        import tools.suggest_fix as sf
        from services.gateway import ModelGateway
        mock_gw = ModelGateway(base_url="")  # not configured

        original_gw = sf._gateway
        sf.set_gateway(mock_gw)
        try:
            result = sf.execute(error="err", tool_name="echo")
            self.assertFalse(result["success"])
        finally:
            sf.set_gateway(original_gw)

    def test_gateway_configured_returns_suggestion(self):
        import tools.suggest_fix as sf
        mock_gw = MagicMock()
        mock_gw.is_configured.return_value = True
        mock_gw.complete.return_value = "Try restarting the service."

        original_gw = sf._gateway
        sf.set_gateway(mock_gw)
        try:
            result = sf.execute(error="connection refused", tool_name="healthcheck")
            self.assertTrue(result["success"])
            self.assertEqual(result["suggestion"], "Try restarting the service.")
        finally:
            sf.set_gateway(original_gw)


if __name__ == "__main__":
    unittest.main()
