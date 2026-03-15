"""Tool runner: register tools, run with timeout, return ToolResult, log each run. See docs/tool_runner_design.md."""
import logging
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 30.0


class ToolResult(BaseModel):
    """Structured result of a tool execution."""

    success: bool
    output: Any = None
    error: str | None = None
    tool_name: str
    duration_seconds: float = Field(ge=0)
    request_id: str | None = None


class ToolRegistry:
    """In-memory registry mapping tool names to callables and metadata."""

    def __init__(self) -> None:
        self._tools: dict[str, tuple[Callable[..., Any], str]] = {}

    def register(
        self,
        name: str,
        execute: Callable[..., Any],
        description: str = "",
    ) -> None:
        """Register a tool by name. Overwrites if name already exists."""
        self._tools[name] = (execute, description)

    def get(self, name: str) -> tuple[Callable[..., Any], str] | None:
        """Return (execute, description) for the tool, or None if not found."""
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, str]]:
        """Return list of minimal tool info: name and description."""
        return [
            {"name": name, "description": desc}
            for name, (_, desc) in self._tools.items()
        ]


class ToolRunner:
    """Executes registered tools with validation, timeout, and logging."""

    def __init__(
        self,
        registry: ToolRegistry,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._registry = registry
        self._timeout = timeout_seconds
        self._executor = ThreadPoolExecutor(max_workers=1)  # one at a time for easy debugging

    def run(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        request_id: str | None = None,
    ) -> ToolResult:
        """Validate, execute with timeout, and return a structured result. Logs each run."""
        start = time.perf_counter()
        tool = self._registry.get(tool_name)

        if tool is None:
            duration = time.perf_counter() - start
            result = ToolResult(
                success=False,
                error=f"Unknown tool: {tool_name!r}",
                tool_name=tool_name,
                duration_seconds=round(duration, 4),
                request_id=request_id,
            )
            logger.warning(
                "tool_run tool=%s duration=%.3fs success=false error=unknown_tool",
                tool_name,
                duration,
            )
            return result

        execute, _ = tool

        def run_tool() -> Any:
            return execute(**arguments)

        try:
            future: Future[Any] = self._executor.submit(run_tool)
            output = future.result(timeout=self._timeout)
            duration = time.perf_counter() - start
            result = ToolResult(
                success=True,
                output=output,
                error=None,
                tool_name=tool_name,
                duration_seconds=round(duration, 4),
                request_id=request_id,
            )
            logger.info(
                "tool_run tool=%s duration=%.3fs success=true",
                tool_name,
                duration,
            )
            return result
        except TimeoutError:
            duration = time.perf_counter() - start
            result = ToolResult(
                success=False,
                error=f"Tool execution timed out after {self._timeout}s",
                tool_name=tool_name,
                duration_seconds=round(duration, 4),
                request_id=request_id,
            )
            logger.warning(
                "tool_run tool=%s duration=%.3fs success=false error=timeout",
                tool_name,
                duration,
            )
            return result
        except Exception as e:
            duration = time.perf_counter() - start
            result = ToolResult(
                success=False,
                error=str(e),
                tool_name=tool_name,
                duration_seconds=round(duration, 4),
                request_id=request_id,
            )
            logger.error(
                "tool_run tool=%s duration=%.3fs success=false error=%s",
                tool_name,
                duration,
                str(e),
            )
            return result
