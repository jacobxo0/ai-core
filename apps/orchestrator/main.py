"""AI-CORE Orchestrator — main FastAPI application.

Wires together: ToolRunner, MemoryStore, ModelGateway, Scheduler, and all tools.
All tool execution flows through _run_command; every run is persisted to memory.
"""
import logging
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from services.tool_runner import ToolRegistry, ToolResult, ToolRunner
from services.memory import MemoryStore
from services.gateway import ModelGateway
from services.scheduler import Scheduler
from adapters.webhook import router as webhook_router, set_run_fn as _set_webhook_run_fn

import tools.echo as _echo
import tools.healthcheck as _healthcheck
import tools.system_info as _system_info
import tools.run_check as _run_check
import tools.fetch_url as _fetch_url
import tools.query_runs as _query_runs
import tools.suggest_fix as _suggest_fix
import tools.ollama_health as _ollama_health

# ── Logging ───────────────────────────────────────────────────────────────────

_log_dir = Path("data/logs")
_log_dir.mkdir(parents=True, exist_ok=True)
_fh = logging.FileHandler(_log_dir / "ai_core.log", encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
for _ns in ("services", "adapters", "apps"):
    _l = logging.getLogger(_ns)
    _l.addHandler(_fh)
    _l.setLevel(logging.DEBUG)

logger = logging.getLogger("apps.orchestrator")

# ── Services ──────────────────────────────────────────────────────────────────

registry  = ToolRegistry()
runner    = ToolRunner(registry, timeout_seconds=30)
memory    = MemoryStore("data/memory.db")
gateway   = ModelGateway()
scheduler = Scheduler()

# Wire services into tools that need them
_query_runs.set_memory(memory)
_suggest_fix.set_memory(memory)
_suggest_fix.set_gateway(gateway)

# ── Tool registration ─────────────────────────────────────────────────────────

registry.register("echo",        _echo.execute,        description="Echoes the given message.")
registry.register("healthcheck", _healthcheck.execute,  description="Returns system health status.")
registry.register("system_info", _system_info.execute,  description="CPU, memory, disk, and platform info.")
registry.register("run_check",   _run_check.execute,    description="Runs a shell command and returns output. Local use only.")
registry.register("fetch_url",   _fetch_url.execute,    description="HTTP GET a URL; returns status and body preview.")
registry.register("query_runs",  _query_runs.execute,   description="Query recent tool runs from the memory store.")
registry.register("suggest_fix",   _suggest_fix.execute,   description="Ask the model gateway to suggest a fix for a tool error.")
registry.register("ollama_health", _ollama_health.execute, description="Check if Ollama is reachable and list available models.")

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI-CORE",
    version="0.2.0",
    description="Local-first AI orchestration platform.",
)
app.include_router(webhook_router)

# ── Core runner ───────────────────────────────────────────────────────────────

def _run_command(
    tool_name: str,
    arguments: dict[str, Any],
    request_id: str | None = None,
) -> ToolResult:
    """Single execution path. All interfaces go through here."""
    result = runner.run(tool_name, arguments, request_id)
    memory.write_run(result)
    return result

_set_webhook_run_fn(_run_command)

# ── Lifecycle ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def _startup() -> None:
    interval = int(os.getenv("SCHEDULE_HEALTHCHECK", "300"))
    scheduler.add_job("healthcheck_periodic", "healthcheck", {}, interval)
    if gateway.is_configured():
        ollama_interval = int(os.getenv("SCHEDULE_OLLAMA_HEALTH", "600"))
        scheduler.add_job("ollama_health_periodic", "ollama_health", {}, ollama_interval)
    scheduler.start(_run_command)
    logger.info(
        "startup version=0.2.0 tools=%d scheduler_jobs=%d",
        len(registry.list_tools()),
        len(scheduler.list_jobs()),
    )

@app.on_event("shutdown")
async def _shutdown() -> None:
    scheduler.stop()
    logger.info("shutdown")

# ── Request models ────────────────────────────────────────────────────────────

class ExecuteRequest(BaseModel):
    tool: str
    arguments: dict[str, Any] = {}

class CommandRequest(BaseModel):
    command: str
    arguments: dict[str, Any] = {}
    request_id: Optional[str] = None

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", summary="Root health check")
def root() -> dict[str, Any]:
    stats = memory.stats()
    return {
        "status": "AI core running",
        "version": "0.2.0",
        "tools": len(registry.list_tools()),
        "scheduler_running": scheduler.running,
        "memory": stats,
    }

@app.get("/tools", summary="List registered tools")
def list_tools() -> dict[str, Any]:
    return {"tools": registry.list_tools()}

@app.get("/scheduler", summary="List scheduled jobs")
def list_scheduler_jobs() -> dict[str, Any]:
    return {"jobs": scheduler.list_jobs(), "running": scheduler.running}

@app.post("/command", summary="Execute a tool by name")
def command(req: CommandRequest) -> dict[str, Any]:
    return _run_command(req.command, req.arguments, req.request_id).model_dump()

@app.post("/tools/execute", summary="Execute a tool (legacy alias for /command)")
def tools_execute(req: ExecuteRequest) -> dict[str, Any]:
    return _run_command(req.tool, req.arguments).model_dump()

@app.get("/runs", summary="Query tool run history")
def get_runs(
    failed: bool = Query(False, description="Return only failed runs"),
    limit: int = Query(20, ge=1, le=200, description="Max runs to return"),
    tool: Optional[str] = Query(None, description="Filter by tool name"),
) -> dict[str, Any]:
    runs = memory.query_runs(failed_only=failed, limit=limit, tool_name=tool)
    return {"runs": runs, "count": len(runs)}

@app.get("/gateway/status", summary="Model gateway configuration status")
def gateway_status() -> dict[str, Any]:
    return gateway.status()

@app.get("/ui", response_class=HTMLResponse, summary="Live run dashboard", include_in_schema=False)
def ui() -> str:
    runs  = memory.query_runs(limit=100)
    stats = memory.stats()

    rows = ""
    for r in runs:
        ok    = r["success"]
        icon  = "&#10003;" if ok else "&#10007;"
        color = "#3a3" if ok else "#c33"
        err   = r.get("error") or ""
        rid   = r.get("request_id") or ""
        dur   = f"{round(r.get('duration_seconds') or 0, 3)}s"
        ts    = (r.get("timestamp") or "")[:19].replace("T", " ")
        rows += (
            f"<tr>"
            f"<td>{ts}</td>"
            f"<td><code>{r['tool_name']}</code></td>"
            f'<td style="color:{color};font-weight:bold;text-align:center">{icon}</td>'
            f'<td style="color:#c77;font-size:12px">{err}</td>'
            f'<td style="color:#666;font-size:11px">{rid}</td>'
            f'<td style="text-align:right">{dur}</td>'
            f"</tr>\n"
        )

    jobs_html = ""
    for j in scheduler.list_jobs():
        jobs_html += (
            f"<tr><td><code>{j['name']}</code></td>"
            f"<td><code>{j['tool_name']}</code></td>"
            f'<td style="text-align:right">{j["interval_seconds"]}s</td>'
            f'<td style="text-align:right">{j["run_count"]}</td>'
            f'<td style="text-align:right">{j["next_run_in"]}s</td></tr>\n'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>AI-CORE</title>
  <meta http-equiv="refresh" content="30">
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:monospace;background:#0d0d0d;color:#ccc;padding:2rem;font-size:14px}}
    h1{{color:#5af;margin-bottom:.25rem;font-size:1.4rem}}
    h2{{color:#888;font-size:.9rem;margin:1.5rem 0 .5rem;text-transform:uppercase;letter-spacing:.08em}}
    .meta{{color:#555;font-size:12px;margin-bottom:1.5rem}}
    .stats{{display:flex;gap:1.5rem;margin-bottom:1.5rem;flex-wrap:wrap}}
    .stat{{background:#141414;border:1px solid #222;border-radius:6px;padding:.6rem 1rem}}
    .stat .val{{font-size:1.4rem;color:#5af;font-weight:bold}}
    .stat .lbl{{font-size:11px;color:#555;margin-top:2px}}
    table{{border-collapse:collapse;width:100%;margin-bottom:2rem}}
    th,td{{padding:5px 10px;border:1px solid #1a1a1a;text-align:left}}
    th{{background:#151515;color:#666;font-size:12px}}
    tr:hover{{background:#111}}
    code{{color:#fc8;font-size:13px}}
    a{{color:#5af;text-decoration:none}}
    a:hover{{text-decoration:underline}}
  </style>
</head>
<body>
  <h1>AI-CORE</h1>
  <p class="meta">
    v0.2.0 &nbsp;&middot;&nbsp; auto-refresh every 30s &nbsp;&middot;&nbsp;
    <a href="/docs">API docs</a> &nbsp;&middot;&nbsp;
    <a href="/runs">JSON /runs</a> &nbsp;&middot;&nbsp;
    <a href="/scheduler">scheduler</a>
  </p>

  <div class="stats">
    <div class="stat"><div class="val">{stats["total_runs"]}</div><div class="lbl">total runs</div></div>
    <div class="stat"><div class="val">{stats["failed_runs"]}</div><div class="lbl">failed runs</div></div>
    <div class="stat"><div class="val">{stats["unique_tools"]}</div><div class="lbl">tools used</div></div>
    <div class="stat"><div class="val">{"on" if scheduler.running else "off"}</div><div class="lbl">scheduler</div></div>
    <div class="stat"><div class="val">{"yes" if gateway.is_configured() else "no"}</div><div class="lbl">model gateway</div></div>
  </div>

  <h2>Scheduled jobs</h2>
  <table>
    <thead><tr><th>Job</th><th>Tool</th><th>Interval</th><th>Runs</th><th>Next in</th></tr></thead>
    <tbody>{jobs_html or "<tr><td colspan='5' style='color:#444'>no jobs configured</td></tr>"}</tbody>
  </table>

  <h2>Last 100 runs</h2>
  <table>
    <thead><tr><th>Time (UTC)</th><th>Tool</th><th>OK</th><th>Error</th><th>Request ID</th><th>Duration</th></tr></thead>
    <tbody>{rows or "<tr><td colspan='6' style='color:#444'>no runs yet</td></tr>"}</tbody>
  </table>
</body>
</html>"""
