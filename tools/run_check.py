"""Run check tool — executes a shell command and returns its output.
WARNING: runs arbitrary shell commands. Intended for local/trusted use only.
"""
import subprocess
from typing import Any


def execute(command: str = "", timeout: int = 10) -> dict[str, Any]:
    if not command or not command.strip():
        return {"success": False, "error": "no command provided"}

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=int(timeout),
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout[:2000],
            "stderr": result.stderr[:500],
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"command timed out after {timeout}s"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
