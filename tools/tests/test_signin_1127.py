"""26/11 17:15–00:00: the refresh token was refused, every command waited 15 minutes for a device-code sign-in, the
state lock stayed held, and the mail watcher was switched off after 10 timeouts (dev, 27/11)."""
import io
import json
import os
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from types import SimpleNamespace
from unittest import mock

from tools import precheck, signin, state, watch
from tools.graph_mail import DeviceCodeToken, SignInNeeded
from tools.httpjson import HttpError
from tools.tests.test_watch import FakeMail

REFUSED = json.dumps({"error": "invalid_grant", "error_description":
                      "AADSTS50173: The provided grant has expired due to it being revoked.\r\nTrace ID: x"})


class FakeTg:
    def __init__(self):
        self.sent = []

    def send(self, text, buttons=None, topic=None):
        self.sent.append((topic, text))
        return len(self.sent)


class RefusedRefreshTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.cache = os.path.join(self.dir, "tok.json")
        with open(self.cache, "w") as f:
            json.dump({"refresh_token": "r", "access_token": "old", "expires_at": time.time() - 10}, f)
        self.urls = []

    def http(self, method, url, **kw):
        self.urls.append(url)
        raise HttpError(400, url, REFUSED)

    def test_refused_refresh_raises_at_once_with_microsofts_words(self):
        tok = DeviceCodeToken("cid", self.cache, http=self.http, out=lambda m: self.fail("asked to sign in"),
                              interactive=False)
        started = time.time()
        with self.assertRaises(SignInNeeded) as cm:
            tok()
        self.assertLess(time.time() - started, 2)
        self.assertIn("AADSTS50173", str(cm.exception))
        self.assertIn("mail-login-start", str(cm.exception))
        self.assertNotIn("Trace ID", str(cm.exception))
        self.assertFalse(any(u.endswith("/devicecode") for u in self.urls))  # no sign-in code asked for

    def test_default_is_not_interactive(self):
        with mock.patch.dict(os.environ, {"EMI_DEVICE_LOGIN": ""}):
            self.assertFalse(DeviceCodeToken("cid", self.cache).interactive)
        with mock.patch.dict(os.environ, {"EMI_DEVICE_LOGIN": "1"}):
            self.assertTrue(DeviceCodeToken("cid", self.cache).interactive)

    def test_no_cache_at_all_says_so(self):
        tok = DeviceCodeToken("cid", os.path.join(self.dir, "none.json"), http=self.http, interactive=False)
        with self.assertRaisesRegex(SignInNeeded, "no refresh token cached"):
            tok()


class ScopeKeptTest(unittest.TestCase):
    """26/11 09:15 UTC: the cached scope became the code's SCOPE (Files.Read.All, no Mail.Send) -> AADSTS65001."""
    SIGNED_IN = "offline_access https://graph.microsoft.com/Mail.ReadWrite https://graph.microsoft.com/Mail.Send"

    def setUp(self):
        self.cache = os.path.join(tempfile.mkdtemp(), "tok.json")
        with open(self.cache, "w") as f:
            json.dump({"refresh_token": "r", "access_token": "old", "expires_at": time.time() - 10,
                       "scope": self.SIGNED_IN}, f)
        self.asked = []

    def http(self, method, url, form=None, **kw):
        self.asked.append(form["scope"])
        return {"access_token": "new", "refresh_token": "r2", "expires_in": 3600}

    def test_file_read_empty_mid_write_keeps_the_signed_in_scope(self):
        tok = DeviceCodeToken("cid", self.cache, http=self.http, interactive=False)
        # cached-access check and refresh read the real file; the save's read lands on another process's truncate
        reads = iter([None, None, {}])
        real = tok._read_cache
        tok._read_cache = lambda: (lambda v: real() if v is None else v)(next(reads, None))
        self.assertEqual(tok(), "new")
        with open(self.cache) as f:
            saved = json.load(f)
        self.assertEqual(saved["scope"], self.SIGNED_IN)
        self.assertEqual(saved["refresh_token"], "r2")
        saved["expires_at"] = time.time() - 10  # an hour later: the next refresh asks for the same scope
        with open(self.cache, "w") as f:
            json.dump(saved, f)
        DeviceCodeToken("cid", self.cache, http=self.http, interactive=False)()
        self.assertEqual(self.asked, [self.SIGNED_IN, self.SIGNED_IN])  # never Files.Read.All

    def test_no_temp_file_left(self):
        DeviceCodeToken("cid", self.cache, http=self.http, interactive=False)()
        self.assertEqual(os.listdir(os.path.dirname(self.cache)), ["tok.json"])


class AlertTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.clock = [1000.0]
        self.tg = FakeTg()

    def alert(self, err="refused AADSTS50173"):
        return signin.alert(SignInNeeded(err), self.tg, self.dir, now=lambda: self.clock[0], out=lambda s: None)

    def test_once_per_six_hours_in_the_report_tab(self):
        self.assertTrue(self.alert())
        self.assertEqual(self.tg.sent[0][0], "report")
        self.assertIn("AADSTS50173", self.tg.sent[0][1])
        self.clock[0] += 3600
        self.assertFalse(self.alert())
        self.clock[0] += signin.EVERY
        self.assertTrue(self.alert())
        self.assertEqual(len(self.tg.sent), 2)

    def test_new_words_are_posted_at_once(self):
        self.alert()
        self.assertTrue(self.alert("refused AADSTS700082"))

    def test_no_telegram_no_crash(self):
        self.assertFalse(signin.alert(SignInNeeded("x"), None, self.dir, out=lambda s: None))


class JobsStayQuietTest(unittest.TestCase):
    """The minute and 15-minute checks don't fail (OpenClaw turns an automation off after 10 failed runs): they post
    the line and pick up again by themselves after the sign-in."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.tg = FakeTg()

    def test_watcher(self):
        def refused(*a, **k):
            raise SignInNeeded("refused AADSTS50173")
        out = io.StringIO()
        with mock.patch.object(watch, "check", refused), mock.patch.object(watch, "_telegram", lambda: self.tg), \
                mock.patch.object(watch, "_work_dir", lambda: self.dir), mock.patch.object(watch.config, "mail"), \
                mock.patch.object(watch.config, "state"), redirect_stdout(out), redirect_stderr(io.StringIO()):
            rc = watch.main(["job-1"])
        self.assertEqual(rc, 0)
        self.assertIn("NO_REPLY", out.getvalue())
        self.assertEqual(len(self.tg.sent), 1)

    def test_precheck(self):
        def refused(*a, **k):
            raise SignInNeeded("refused AADSTS50173")
        out = io.StringIO()
        with mock.patch.object(precheck, "payments_have_work", refused), \
                mock.patch.object(watch, "_telegram", lambda: self.tg), mock.patch.object(watch, "_work_dir", lambda: self.dir), \
                mock.patch.object(precheck.config, "mail"), mock.patch.object(precheck.config, "sheet"), \
                mock.patch.object(precheck.config, "state"), redirect_stdout(out), redirect_stderr(io.StringIO()):
            self.assertEqual(precheck.main(["payments"]), 1)
            self.assertEqual(precheck.main(["payments", "--agent"]), 0)
        self.assertIn("quiet", out.getvalue())
        self.assertEqual(len(self.tg.sent), 1)  # the second run within six hours posts nothing


class WatcherLockTest(unittest.TestCase):
    def test_state_busy_leaves_auto_replies_for_the_next_minute(self):
        d = tempfile.mkdtemp()
        calls = []
        st = SimpleNamespace(data={"last_scan": "2026-11-26T10:15:29Z", "processed": {}})
        mail = FakeMail([{"id": "a1", "subject": "Automatic reply: Stop Sale", "receivedDateTime": "2026-11-26T10:20:00Z",
                          "from": {"emailAddress": {"address": "a@b.c"}}}])
        res = watch.check(mail, st, "job-1", run=lambda argv, **k: calls.append(argv), now=time.time,
                          lock_path=os.path.join(d, "watch.json"), out=lambda *_: None, closer=lambda msgs: False,
                          cache_path=os.path.join(d, "auto-reply.json"))
        self.assertEqual(res, "busy")
        self.assertEqual(calls, [])
        self.assertNotIn("a1", st.data["processed"])

    def test_watcher_waits_far_less_than_its_own_timeout(self):
        self.assertLessEqual(watch.LOCK_WAIT, 30)


class LockHolderTest(unittest.TestCase):
    def test_the_timeout_names_the_holder(self):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "emi-state.json")
        with open(path + ".lock", "w") as f:
            json.dump({"pid": 4242, "since": "2026-11-26T10:28:00Z", "cmd": "emi.py done AAMk… NO REPLY"}, f)
        self.assertEqual(state._holder(path),
                         " (by pid 4242, `emi.py done AAMk… NO REPLY`, since 26/11 17:28 Vietnam time)")

    def test_an_empty_lock_file_says_nothing(self):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "emi-state.json")
        open(path + ".lock", "w").close()
        self.assertEqual(state._holder(path), "")

    @unittest.skipIf(state.fcntl is None, "flock: Linux only (the host)")
    def test_holder_written_and_named_to_the_next_command(self):
        import subprocess
        import sys
        d = tempfile.mkdtemp()
        path = os.path.join(d, "emi-state.json")
        code = ("import sys,time; sys.argv=['emi.py','stop-sales-history','--rebuild']; from tools import state; "
                f"state.hold_lock({path!r}); print('held', flush=True); time.sleep(5)")
        p = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(p.stdout.readline().strip(), "held")
            state._held.pop(path, None)
            with self.assertRaisesRegex(TimeoutError, r"by pid \d+, `emi.py stop-sales-history --rebuild`"):
                state.hold_lock(path, wait=0.3)
        finally:
            p.kill()
            p.wait()


if __name__ == "__main__":
    unittest.main()
