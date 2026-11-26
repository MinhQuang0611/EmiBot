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
    """new: True = one email that has waited long enough, False = none, or the list itself."""
    NEW_MAIL_PAGE = 50

    def __init__(self, new, headers=None):
        if new is True:
            new = [{"id": "x1", "subject": "Booking request", "receivedDateTime": "1970-01-01T00:00:00Z"}]
        self.new = new or []
        self.headers = headers or {}
        self.header_calls = []

    def new_inbox_mail(self, since):
        return list(self.new)

    def message_headers(self, message_id):
        self.header_calls.append(message_id)
        return self.headers.get(message_id, {})


class WatchTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.lock = os.path.join(self.dir, "watch.json")
        self.st = SimpleNamespace(data={"last_scan": "2026-10-22T05:00:21Z"})
        self.calls = []
        self.clock = [1000.0]
        self.closed = []

    def fake_run(self, argv, **kw):
        self.calls.append(argv)
        return SimpleNamespace(returncode=0, stdout="{ok: true}", stderr="")

    def check(self, new, mail=None):
        return watch.check(mail or FakeMail(new), self.st, "job-1", run=self.fake_run, now=lambda: self.clock[0],
                           lock_path=self.lock, out=lambda *_: None, closer=self.closed.extend,
                           cache_path=os.path.join(self.dir, "auto-reply.json"))

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

    def test_already_running_elsewhere_is_not_a_failure(self):
        # dev, 2026-11-21: on 20/11 the watcher failed five times while the 3-hourly job 1 run was working
        def run(argv, **kw):
            self.calls.append(argv)
            return SimpleNamespace(returncode=1, stderr="", stdout='{\n  "ok": true,\n  "ran": false,\n  '
                                                                  '"reason": "already-running"\n}')
        res = watch.check(FakeMail(True), self.st, "job-1", run=run, now=lambda: self.clock[0],
                          lock_path=self.lock, out=lambda *_: None, cache_path=os.path.join(self.dir, "a.json"))
        self.assertEqual(res, "running")
        self.assertFalse(os.path.exists(self.lock))  # not ours: the next minute checks again

    def test_other_start_failures_still_fail(self):
        def run(argv, **kw):
            return SimpleNamespace(returncode=1, stderr="gateway unreachable", stdout="")
        with self.assertRaises(RuntimeError):
            watch.check(FakeMail(True), self.st, "job-1", run=run, now=lambda: self.clock[0],
                        lock_path=self.lock, out=lambda *_: None, cache_path=os.path.join(self.dir, "a.json"))

    def with_runs(self, entries):
        def run(argv, **kw):
            self.calls.append(argv)
            if "runs" in argv:
                return SimpleNamespace(returncode=0, stdout="banner\n" + json.dumps({"entries": entries}), stderr="")
            return SimpleNamespace(returncode=0, stdout="{ok: true}", stderr="")
        self.fake_run = run

    def test_next_batch_starts_once_a_run_ended_with_progress(self):
        # 30/10: runs took 3-10 of 17 emails each, then the lock held the rest for 25 minutes
        self.st.data["processed"] = {}
        self.check(True)
        self.st.data["processed"] = {"m1": {}, "m2": {}}
        self.with_runs([])  # still running: no finished run since the start
        self.clock[0] += 120
        self.assertEqual(self.check(True), "running")
        self.with_runs([{"runAtMs": 1000 * 1000 + 500}])
        self.assertEqual(self.check(True), "started")
        self.assertEqual(self.calls[-1][-3:], ["automations", "run", "job-1"])

    def test_run_without_progress_waits_out_the_window(self):
        self.st.data["processed"] = {"m1": {}}
        self.check(True)
        self.with_runs([{"runAtMs": 1000 * 1000 + 500}])  # finished, but handled nothing
        self.clock[0] += 120
        self.assertEqual(self.check(True), "running")
        self.assertFalse(any("runs" in c for c in self.calls))

    def test_failed_start_is_an_error_and_leaves_no_lock(self):
        def bad(argv, **kw):
            return SimpleNamespace(returncode=1, stdout="", stderr="gateway unreachable")
        with self.assertRaises(RuntimeError):
            watch.check(FakeMail(True), self.st, "job-1", run=bad, lock_path=self.lock, out=lambda *_: None,
                        cache_path=os.path.join(self.dir, "a.json"))
        self.assertFalse(os.path.exists(self.lock))


def at(epoch):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


class BatchAndAutoReplyTest(unittest.TestCase):
    """Dev, 2026-11-26 (tokens): job 1 waits until the oldest email has been in the inbox 10 minutes, so the
    emails of those minutes share one run; auto-replies are closed by code and start nothing."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.st = SimpleNamespace(data={"last_scan": "2026-11-26T00:00:00Z", "processed": {}})
        self.calls, self.closed = [], []
        self.clock = [1_795_650_000.0]

    def run_(self, argv, **kw):
        self.calls.append(argv)
        return SimpleNamespace(returncode=0, stdout="{ok: true}", stderr="")

    def check(self, mail):
        return watch.check(mail, self.st, "job-1", run=self.run_, now=lambda: self.clock[0],
                           lock_path=os.path.join(self.dir, "watch.json"), out=lambda *_: None,
                           closer=self.closed.extend, cache_path=os.path.join(self.dir, "auto-reply.json"))

    def msg(self, mid, subject, age):
        return {"id": mid, "subject": subject, "receivedDateTime": at(self.clock[0] - age),
                "from": {"emailAddress": {"address": "a@b.c"}}}

    def test_waits_for_the_batch_then_starts_once(self):
        mail = FakeMail([self.msg("m1", "Booking request", 120)])
        self.assertEqual(self.check(mail), "waiting")
        mail.new.append(self.msg("m2", "Re: Booking request", 30))
        self.clock[0] += 7 * 60
        self.assertEqual(self.check(mail), "waiting")
        self.assertEqual(self.calls, [])
        self.clock[0] += 60  # m1 has now waited 10 minutes
        self.assertEqual(self.check(mail), "started")
        self.assertEqual(len(self.calls), 1)

    def test_audit_and_done_emails_start_nothing(self):
        self.st.data["processed"] = {"m2": {}}
        mail = FakeMail([self.msg("m1", "HAYA intake audit 12:46 26/11", 3600),
                         self.msg("m2", "Booking request", 3600)])
        self.assertEqual(self.check(mail), "quiet")
        self.assertEqual(self.calls, [])

    def test_a_full_page_starts_at_once(self):
        mail = FakeMail([self.msg(f"m{i}", "Booking", 10) for i in range(50)])
        self.assertEqual(self.check(mail), "started")

    def test_auto_reply_by_subject_is_closed_by_code(self):
        mail = FakeMail([self.msg("a1", "Automatic reply: Stop Sale Chart HAYA 26/11", 3600)])
        self.assertEqual(self.check(mail), "quiet")
        self.assertEqual([m["id"] for m in self.closed], ["a1"])
        self.assertEqual(self.calls, [])
        self.assertEqual(mail.header_calls, [])  # the subject is enough

    def test_auto_reply_by_header_read_once(self):
        mail = FakeMail([self.msg("a1", "Ticket Received 5031128", 3600), self.msg("m1", "Booking request", 60)],
                        headers={"a1": {"auto-submitted": "auto-replied"}})
        self.assertEqual(self.check(mail), "waiting")  # a1 closed; m1 is a minute old
        self.assertEqual([m["id"] for m in self.closed], ["a1"])
        mail.new = mail.new[1:]
        self.clock[0] += 60
        self.check(mail)
        self.assertEqual(mail.header_calls, ["a1", "m1"])  # m1's answer is kept, not asked again

    def test_robot_notices_are_not_auto_replies(self):
        from tools import auto_reply
        self.assertFalse(auto_reply.by_headers({"Auto-Submitted": "auto-generated"}))  # SynXis, OTAs
        self.assertTrue(auto_reply.by_headers({"Auto-Submitted": "auto-replied (vacation)"}))
        self.assertTrue(auto_reply.by_headers({"X-Autoreply": "yes"}))
        self.assertFalse(auto_reply.by_subject("Undeliverable: Stop Sale Chart"))  # a bounce: the model reads it
        self.assertFalse(auto_reply.by_subject("SynXis Res Confirmed (92777EF003647 )"))
        self.assertFalse(auto_reply.by_subject("Re: automatic reply needed for booking?"))
        for s in ("Automatic reply: Booking 123", "Auto-Reply: Stop sale", "[Auto Reply] Re: Stop Sale", "Out of Office: x",
                  "Trả lời tự động: Xác nhận", "Автоматический ответ: Бронь", "自动回复: Stop Sale"):
            self.assertTrue(auto_reply.by_subject(s), s)


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
