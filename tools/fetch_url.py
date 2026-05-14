"""Fetch URL tool — HTTP GET or POST a URL and return status + body."""
from typing import Any

import httpx


def execute(
    url: str = "",
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: int = 15,
) -> dict[str, Any]:
    if not url or not url.strip():
        return {"success": False, "error": "no url provided"}

    method = method.upper()
    if method not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
        return {"success": False, "error": f"unsupported method: {method}"}

    try:
        with httpx.Client(follow_redirects=True, timeout=int(timeout)) as client:
            kwargs: dict[str, Any] = {"headers": headers or {}}
            if body is not None:
                kwargs["json"] = body
            resp = client.request(method, url.strip(), **kwargs)

        try:
            json_body = resp.json()
        except Exception:
            json_body = None

        return {
            "success": resp.is_success,
            "status_code": resp.status_code,
            "url": str(resp.url),
            "content_type": resp.headers.get("content-type", ""),
            "body": json_body if json_body is not None else resp.text[:2000],
            "elapsed_ms": round(resp.elapsed.total_seconds() * 1000, 1),
        }
    except httpx.TimeoutException:
        return {"success": False, "error": f"request timed out after {timeout}s"}
    except httpx.RequestError as exc:
        return {"success": False, "error": f"request error: {exc}"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
