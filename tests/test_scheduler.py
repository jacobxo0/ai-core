"""Tests for services/scheduler.py — Scheduler."""
import threading
import time
import unittest

from services.scheduler import Scheduler


class TestScheduler(unittest.TestCase):
    def test_add_and_list_jobs(self):
        s = Scheduler()
        s.add_job("job1", "healthcheck", {}, 60)
        s.add_job("job2", "echo", {"message": "hi"}, 120)
        jobs = s.list_jobs()
        self.assertEqual(len(jobs), 2)
        names = {j["name"] for j in jobs}
        self.assertEqual(names, {"job1", "job2"})

    def test_replace_job_with_same_name(self):
        s = Scheduler()
        s.add_job("job1", "echo", {}, 60)
        s.add_job("job1", "healthcheck", {}, 30)
        jobs = s.list_jobs()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["tool_name"], "healthcheck")

    def test_remove_job(self):
        s = Scheduler()
        s.add_job("job1", "echo", {}, 60)
        s.add_job("job2", "healthcheck", {}, 60)
        s.remove_job("job1")
        self.assertEqual(len(s.list_jobs()), 1)

    def test_job_fires_run_fn(self):
        """Job with interval=0 should fire immediately on first tick."""
        fired = threading.Event()
        calls = []

        def mock_run(tool_name, arguments, request_id):
            calls.append((tool_name, request_id))
            fired.set()

        s = Scheduler()
        s.add_job("test_job", "echo", {"message": "hi"}, interval_seconds=9999)
        # Force next_run to now so it fires immediately
        s._jobs[0].next_run = time.time() - 1
        s.start(mock_run)

        fired.wait(timeout=3.0)
        s.stop()

        self.assertTrue(len(calls) >= 1)
        self.assertEqual(calls[0][0], "echo")
        self.assertTrue(calls[0][1].startswith("scheduler:test_job:"))

    def test_start_and_stop(self):
        s = Scheduler()
        s.add_job("j", "echo", {}, 9999)
        s.start(lambda *a: None)
        self.assertTrue(s.running)
        s.stop()
        self.assertFalse(s.running)

    def test_not_running_before_start(self):
        s = Scheduler()
        self.assertFalse(s.running)


if __name__ == "__main__":
    unittest.main()
