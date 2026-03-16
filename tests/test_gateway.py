"""Tests for services/gateway.py — ModelGateway."""
import unittest
from unittest.mock import MagicMock, patch

from services.gateway import ModelGateway


class TestModelGatewayUnconfigured(unittest.TestCase):
    def setUp(self):
        self.gw = ModelGateway(base_url="")

    def test_not_configured(self):
        self.assertFalse(self.gw.is_configured())

    def test_complete_returns_none_when_not_configured(self):
        result = self.gw.complete("test prompt")
        self.assertIsNone(result)

    def test_status_configured_false(self):
        s = self.gw.status()
        self.assertFalse(s["configured"])
        self.assertIsNone(s["base_url"])


class TestModelGatewayConfigured(unittest.TestCase):
    def setUp(self):
        self.gw = ModelGateway(base_url="http://localhost:11434")

    def test_is_configured(self):
        self.assertTrue(self.gw.is_configured())

    def test_status_configured_true(self):
        s = self.gw.status()
        self.assertTrue(s["configured"])
        self.assertEqual(s["base_url"], "http://localhost:11434")

    def test_complete_calls_ollama_and_returns_text(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "  try restarting it  "}
        mock_resp.raise_for_status = MagicMock()

        with patch("services.gateway.httpx.post", return_value=mock_resp) as mock_post:
            result = self.gw.complete("fix this error", model="llama3.2", max_tokens=128)

        self.assertEqual(result, "try restarting it")
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        self.assertIn("/api/generate", call_kwargs[0][0])

    def test_complete_raises_on_http_error(self):
        import httpx

        with patch("services.gateway.httpx.post", side_effect=httpx.TimeoutException("timed out")):
            with self.assertRaises(httpx.TimeoutException):
                self.gw.complete("prompt")


if __name__ == "__main__":
    unittest.main()
