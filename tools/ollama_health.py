"""Ollama health tool — checks if the Ollama service is reachable and lists available models."""
import os
from typing import Any

import httpx


def execute(base_url: str = "") -> dict[str, Any]:
    url = (base_url or os.getenv("OLLAMA_BASE_URL", "")).rstrip("/")
    if not url:
        return {
            "reachable": False,
            "configured": False,
            "error": "OLLAMA_BASE_URL not set",
            "models": [],
        }

    try:
        resp = httpx.get(f"{url}/api/tags", timeout=5.0)
        resp.raise_for_status()
        data = resp.json()
        models = [m.get("name") for m in data.get("models", [])]
        return {
            "reachable": True,
            "configured": True,
            "base_url": url,
            "model_count": len(models),
            "models": models,
        }
    except httpx.ConnectError:
        return {
            "reachable": False,
            "configured": True,
            "base_url": url,
            "error": f"cannot connect to {url} — is Ollama running and bound to 0.0.0.0?",
            "models": [],
        }
    except httpx.TimeoutException:
        return {
            "reachable": False,
            "configured": True,
            "base_url": url,
            "error": f"timeout connecting to {url}",
            "models": [],
        }
    except Exception as exc:
        return {
            "reachable": False,
            "configured": True,
            "base_url": url,
            "error": str(exc),
            "models": [],
        }
