"""Model gateway. Abstracts Ollama (and future cloud APIs) behind a single interface.
All model calls go through here — no raw Ollama URLs in tool or orchestrator code.
"""
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "llama3.2"
_GENERATE_PATH = "/api/generate"


class ModelGateway:
    """Thin wrapper around Ollama's /api/generate. Returns None if not configured."""

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "")).rstrip("/")
        self.default_model = os.getenv("OLLAMA_DEFAULT_MODEL", _DEFAULT_MODEL)

    def is_configured(self) -> bool:
        return bool(self.base_url)

    def complete(
        self,
        prompt: str,
        model: str | None = None,
        max_tokens: int = 512,
        timeout: float = 30.0,
    ) -> str | None:
        """Send prompt to Ollama, return generated text. Returns None if not configured."""
        if not self.is_configured():
            logger.debug("gateway_not_configured prompt_len=%d", len(prompt))
            return None

        model = model or self.default_model
        url = self.base_url + _GENERATE_PATH
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens},
        }

        try:
            resp = httpx.post(url, json=payload, timeout=timeout)
            resp.raise_for_status()
            text = resp.json().get("response", "").strip()
            logger.info(
                "gateway_complete model=%s prompt_len=%d response_len=%d",
                model, len(prompt), len(text),
            )
            return text
        except httpx.TimeoutException:
            logger.error("gateway_timeout model=%s url=%s", model, url)
            raise
        except httpx.HTTPStatusError as exc:
            logger.error("gateway_http_error status=%d model=%s", exc.response.status_code, model)
            raise
        except Exception as exc:
            logger.error("gateway_error model=%s error=%s", model, exc)
            raise

    def status(self) -> dict[str, Any]:
        """Return gateway configuration status (no secrets exposed)."""
        return {
            "configured": self.is_configured(),
            "base_url": self.base_url if self.is_configured() else None,
            "default_model": self.default_model,
        }
