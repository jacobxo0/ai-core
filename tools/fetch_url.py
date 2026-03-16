"""Fetch URL tool — HTTP GET a URL and return status + body preview."""
from typing import Any

import httpx


def execute(url: str = "", timeout: int = 10) -> dict[str, Any]:
    if not url or not url.strip():
        return {"success": False, "error": "no url provided"}

    try:
        resp = httpx.get(url.strip(), timeout=int(timeout), follow_redirects=True)
        return {
            "success": resp.is_success,
            "status_code": resp.status_code,
            "url": str(resp.url),
            "content_type": resp.headers.get("content-type", ""),
            "body_preview": resp.text[:1000],
            "elapsed_ms": round(resp.elapsed.total_seconds() * 1000, 1),
        }
    except httpx.TimeoutException:
        return {"success": False, "error": f"request timed out after {timeout}s"}
    except httpx.RequestError as exc:
        return {"success": False, "error": f"request error: {exc}"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
