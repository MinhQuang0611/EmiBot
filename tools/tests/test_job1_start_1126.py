"""job1-start (dev, 2026-11-26, tokens): job 1's precheck, auto-replies closed by code and inbox-new in one shell call."""
import os
import tempfile
import unittest
from unittest import mock

from tools import auto_reply, emi
from tools.state import State


class FakeMail:
    def __init__(self, msgs, headers=None):
        self.msgs, self.headers = msgs, headers or {}

    def has_new_inbox_mail(self, since, skip_noise=False):
        return any(m["receivedDateTime"] >= since for m in self.msgs)

    def list_inbox_since(self, since, with_files=False):
        return [m for m in self.msgs if m["receivedDateTime"] >= since]

    def message_headers(self, message_id):
        return self.headers.get(message_id, {})


def msg(mid, subject, at="2026-11-26T05:00:00Z"):
    return {"id": mid, "subject": subject, "receivedDateTime": at,
            "from": {"emailAddress": {"name": "X", "address": "x@agency.vn"}}}


class Job1StartTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("EMI_TEST_ONLY_FROM", None)
        work = tempfile.mkdtemp()
        for p in (mock.patch.object(emi, "WORK_DIR", work), mock.patch.object(emi.config, "SIM_DIR", "")):
            p.start()
            self.addCleanup(p.stop)
        self.st = State(os.path.join(work, "state.json"))
        self.st.mark_scanned("2026-11-26T04:00:00Z")
        self.lines = []

    def test_quiet(self):
        self.assertEqual(emi.job1_start(FakeMail([]), self.st, out=self.lines.append), [])
        self.assertEqual(self.lines, ["quiet"])

    def test_work_comes_first_then_the_list(self):
        got = emi.job1_start(FakeMail([msg("m1", "Booking request 12/12")]), self.st, out=self.lines.append)
        self.assertEqual([m["id"] for m in got], ["m1"])
        self.assertEqual(self.lines[0], "work")
        self.assertTrue(any(s.startswith("scan_started=") for s in self.lines))
        self.assertTrue(any("Booking request 12/12" in s for s in self.lines))

    def test_auto_replies_alone_are_closed_and_the_clock_moves(self):
        mail = FakeMail([msg("a1", "Automatic reply: Stop Sale Chart"), msg("a2", "Ticket Received 5031128")],
                        headers={"a2": {"Auto-Submitted": "auto-replied"}})
        self.assertEqual(emi.job1_start(mail, self.st, out=self.lines.append), [])
        self.assertEqual(self.lines[-1], "quiet")
        self.assertEqual(self.st.data["processed"]["a1"]["outcome"], auto_reply.OUTCOME)
        self.assertTrue(emi.NO_REPLY_OK.search(auto_reply.OUTCOME))  # done/day-check accept it
        self.assertGreater(self.st.data["last_scan"], "2026-11-26T04:00:00Z")
        self.assertEqual(State(self.st.path).data["processed"].keys(), {"a1", "a2"})  # saved

    def test_auto_reply_beside_real_mail(self):
        mail = FakeMail([msg("a1", "Out of Office: Re: Booking"), msg("m1", "New booking TIQI")])
        got = emi.job1_start(mail, self.st, out=self.lines.append)
        self.assertEqual([m["id"] for m in got], ["m1"])
        self.assertIn("work", self.lines)
        self.assertEqual(self.st.data["last_scan"], "2026-11-26T04:00:00Z")  # the model moves it after its run


if __name__ == "__main__":
    unittest.main()
