import logging
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

from services import ToolRegistry, ToolRunner
from tools.echo import execute as echo_execute
from tools.healthcheck import execute as healthcheck_execute

app = FastAPI()

# Ensure data/logs exists and add file handler for tool execution logs
_log_dir = Path("data/logs")
_log_dir.mkdir(parents=True, exist_ok=True)
_file_handler = logging.FileHandler(_log_dir / "ai_core.log", encoding="utf-8")
_file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
_logger = logging.getLogger("services")
_logger.addHandler(_file_handler)
_logger.setLevel(logging.INFO)

# Default registry and runner; register built-in tools at startup
registry = ToolRegistry()
registry.register("echo", echo_execute, description="Echoes the given message.")
registry.register("healthcheck", healthcheck_execute, description="Returns status and component list for operational checks.")
runner = ToolRunner(registry)


class ExecuteRequest(BaseModel):
    tool: str
    arguments: dict = {}


class CommandRequest(BaseModel):
    command: str
    arguments: dict = {}
    request_id: str | None = None


def _run_command(tool_name: str, arguments: dict, request_id: str | None = None) -> dict:
    """Resolve tool by name, run via runner, return ToolResult as JSON. Single place for execution."""
    result = runner.run(tool_name, arguments, request_id=request_id)
    return result.model_dump()


@app.get("/")
def root():
    return {"status": "AI core running"}


@app.get("/tools")
def list_tools():
    return {"tools": registry.list_tools()}


@app.post("/tools/execute")
def run_tool(request: ExecuteRequest):
    return _run_command(request.tool, request.arguments)


@app.post("/command")
def command(request: CommandRequest):
    """Run a registered tool by name. command = tool name, arguments = kwargs for the tool."""
    return _run_command(request.command, request.arguments, request_id=request.request_id)
