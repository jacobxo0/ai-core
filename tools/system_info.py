"""System info tool — returns CPU, memory, disk, and platform details."""
import platform
import sys
from typing import Any

import psutil


def execute() -> dict[str, Any]:
    cpu_percent = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk_path = "C:\\" if sys.platform == "win32" else "/"
    disk = psutil.disk_usage(disk_path)

    return {
        "cpu_percent": cpu_percent,
        "memory": {
            "total_gb": round(mem.total / 1_073_741_824, 2),
            "used_gb": round(mem.used / 1_073_741_824, 2),
            "available_gb": round(mem.available / 1_073_741_824, 2),
            "percent": mem.percent,
        },
        "disk": {
            "path": disk_path,
            "total_gb": round(disk.total / 1_073_741_824, 2),
            "used_gb": round(disk.used / 1_073_741_824, 2),
            "free_gb": round(disk.free / 1_073_741_824, 2),
            "percent": round(disk.percent, 1),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "python_version": platform.python_version(),
        },
        "cpu_count": psutil.cpu_count(logical=True),
    }
