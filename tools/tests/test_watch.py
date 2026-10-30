"""Offline tests for the mail watcher (tools/watch.py) and the cached access token."""
import json
import os
import tempfile
import time
import unittest
from types import SimpleNamespace

from tools import watch
from tools.graph_mail import DeviceCodeToken


class FakeMail:
    def __init__(self, new):
        self.new = new

    def has_new_inbox_mail(self, since):
        return self.new


class WatchTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.lock = os.path.join(self.dir, "watch.json")
        self.st = SimpleNamespace(data={"last_scan": "2026-10-22T05:00:21Z"})
        self.calls = []
        self.clock = [1000.0]

    def fake_run(self, argv, **kw):
        self.calls.append(argv)
        return SimpleNamespace(returncode=0, stdout="{ok: true}", stderr="")

    def check(self, new):
        return watch.check(FakeMail(new), self.st, "job-1", run=self.fake_run, now=lambda: self.clock[0],
                           lock_path=self.lock, out=lambda *_: None)

    def test_quiet_starts_nothing(self):
        self.assertEqual(self.check(False), "quiet")
        self.assertEqual(self.calls, [])

    def test_new_mail_starts_job_once_while_it_runs(self):
        self.assertEqual(self.check(True), "started")
        self.assertEqual(self.calls[0][-3:], ["automations", "run", "job-1"])
        self.clock[0] += 60
        self.assertEqual(self.check(True), "running")  # scan clock hasn't moved: job 1 still at it
        self.assertEqual(len(self.calls), 1)

    def test_starts_again_after_the_run_finished_or_died(self):
        self.check(True)
        self.st.data["last_scan"] = "2026-10-22T05:10:00Z"  # job 1 finished and moved the clock
        self.assertEqual(self.check(True), "started")
        self.clock[0] += watch.RUN_WINDOW + 1  # this one never finishes
        self.assertEqual(self.check(True), "started")
        self.assertEqual(len(self.calls), 3)

    def test_failed_start_is_an_error_and_leaves_no_lock(self):
        def bad(argv, **kw):
            return SimpleNamespace(returncode=1, stdout="", stderr="gateway unreachable")
        with self.assertRaises(RuntimeError):
            watch.check(FakeMail(True), self.st, "job-1", run=bad, lock_path=self.lock, out=lambda *_: None)
        self.assertFalse(os.path.exists(self.lock))


class CachedTokenTest(unittest.TestCase):
    def test_access_token_reused_from_cache_file(self):
        path = os.path.join(tempfile.mkdtemp(), "tok.json")
        with open(path, "w") as f:
            json.dump({"refresh_token": "r", "access_token": "a1", "expires_at": time.time() + 3000}, f)

        def http(*a, **k):
            raise AssertionError("no token request while the cached access token is valid")
        self.assertEqual(DeviceCodeToken("c", path, http=http)(), "a1")

    def test_expired_cache_refreshes_and_keeps_refresh_token(self):
        path = os.path.join(tempfile.mkdtemp(), "tok.json")
        with open(path, "w") as f:
            json.dump({"refresh_token": "r", "access_token": "old", "expires_at": time.time() - 10}, f)
        tok = DeviceCodeToken("c", path, http=lambda *a, **k: {"access_token": "new", "expires_in": 3600})
        self.assertEqual(tok(), "new")
        with open(path) as f:
            self.assertEqual(json.load(f)["refresh_token"], "r")


if __name__ == "__main__":
    unittest.main()
