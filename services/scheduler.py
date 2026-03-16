"""In-process cron scheduler. Triggers registered jobs at fixed intervals via the same run_fn path."""
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class ScheduledJob:
    name: str
    tool_name: str
    arguments: dict[str, Any]
    interval_seconds: int
    next_run: float = field(default_factory=time.time)  # run on first tick
    last_run: float | None = None
    run_count: int = 0


class Scheduler:
    """Runs scheduled jobs in a daemon background thread. Calls run_fn(tool, args, request_id)."""

    _TICK = 1.0  # seconds between loop iterations

    def __init__(self) -> None:
        self._jobs: list[ScheduledJob] = []
        self._run_fn: Callable | None = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    # ── Configuration ─────────────────────────────────────────────────────────

    def add_job(
        self,
        name: str,
        tool_name: str,
        arguments: dict[str, Any],
        interval_seconds: int,
    ) -> None:
        """Register a recurring job. Replaces any existing job with the same name."""
        self._jobs = [j for j in self._jobs if j.name != name]
        self._jobs.append(ScheduledJob(name, tool_name, arguments, interval_seconds))
        logger.info(
            "scheduler_job_added name=%s tool=%s interval=%ds",
            name, tool_name, interval_seconds,
        )

    def remove_job(self, name: str) -> None:
        self._jobs = [j for j in self._jobs if j.name != name]
        logger.info("scheduler_job_removed name=%s", name)

    def list_jobs(self) -> list[dict[str, Any]]:
        return [
            {
                "name": j.name,
                "tool_name": j.tool_name,
                "interval_seconds": j.interval_seconds,
                "run_count": j.run_count,
                "next_run_in": max(0.0, round(j.next_run - time.time(), 1)),
            }
            for j in self._jobs
        ]

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self, run_fn: Callable) -> None:
        """Start the scheduler background thread. run_fn(tool_name, arguments, request_id)."""
        self._run_fn = run_fn
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="scheduler")
        self._thread.start()
        logger.info("scheduler_started jobs=%d", len(self._jobs))

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        logger.info("scheduler_stopped")

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ── Loop ──────────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            now = time.time()
            for job in list(self._jobs):
                if now >= job.next_run:
                    self._fire(job)
            self._stop_event.wait(self._TICK)

    def _fire(self, job: ScheduledJob) -> None:
        request_id = f"scheduler:{job.name}:{uuid.uuid4().hex[:8]}"
        job.last_run = time.time()
        job.next_run = job.last_run + job.interval_seconds
        job.run_count += 1
        logger.info(
            "scheduler_fire name=%s tool=%s request_id=%s run_count=%d",
            job.name, job.tool_name, request_id, job.run_count,
        )
        if self._run_fn is None:
            logger.warning("scheduler_no_run_fn name=%s", job.name)
            return
        try:
            self._run_fn(job.tool_name, job.arguments, request_id)
        except Exception as exc:
            logger.error("scheduler_run_error name=%s error=%s", job.name, exc)
