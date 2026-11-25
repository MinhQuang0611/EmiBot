"""Dev 26/11: 667M tokens in 7 days on Emi. Job 2 was woken 303 times by the 15-minute check, 35 of them for work it
could do; the rest re-read the same waiting list. Job 1 was started 114 times for Tracy's hourly "HAYA intake audit"
alone. Now the check wakes job 2 only for work it wasn't woken for, and the watcher doesn't start job 1 for an audit
alone (job 1 still reads it on its next run).
"""
import json
import os
import tempfile
import unittest
from types import SimpleNamespace

from tools import precheck
from tools.graph_mail import GraphMail
from tools.tests.test_tools import FakeHttp


class WakeTest(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "confirm-wake.json")
        self.clock = [1_000_000.0]
        self.said = []

    def wake(self, keys):
        return precheck.should_wake(keys, self.path, now=lambda: self.clock[0], out=self.said.append)

    def test_same_list_wakes_once(self):
        a, b = '["confirm","A",[],""]', '["hold","B",[]]'
        self.assertTrue(self.wake([a, b]))
        self.clock[0] += 15 * 60
        self.assertFalse(self.wake([a, b]))
        self.assertIn("not woken", self.said[0])
        self.assertFalse(self.wake([b, a]))  # order doesn't matter

    def test_new_item_or_new_stamp_wakes(self):
        self.assertTrue(self.wake(['["confirm","A",["t1|x"],""]']))
        self.clock[0] += 900
        self.assertTrue(self.wake(['["confirm","A",["t2|x"],""]']))  # PDF remade: new ez_processed_at
        self.clock[0] += 900
        self.assertTrue(self.wake(['["confirm","A",["t2|x"],""]', '["hold","B",["E-716"]]']))  # Karen answered

    def test_progress_wakes_again_then_stops(self):
        keys = [f'["confirm","{n}",[],""]' for n in "ABCDEFG"]  # more than job 2's 5 a run
        self.assertTrue(self.wake(keys))
        self.clock[0] += 900
        self.assertTrue(self.wake(keys[5:]))  # the run did 5: the rest at once
        self.clock[0] += 900
        self.assertFalse(self.wake(keys[5:]))  # nothing done last time: wait

    def test_again_after_four_hours_and_quiet_clears(self):
        self.assertTrue(self.wake(["k"]))
        self.clock[0] += precheck.WAKE_AGAIN + 1
        self.assertTrue(self.wake(["k"]))
        self.assertFalse(self.wake([]))
        self.clock[0] += 900
        self.assertTrue(self.wake(["k"]))  # gone and back: new

    def test_holds_to_look_carries_answers(self):
        st = SimpleNamespace(data={"confirmation_holds": {"R1": {}, "R2": {}},
                                   "questions": {"E-1": {"booking_ref": "R1", "answer": None},
                                                 "E-2": {"booking_ref": "R2", "answer": "ok"}}})
        self.assertEqual(precheck.holds_to_look(st), [("R2", ["E-2"])])  # R1 waits on Karen: no wake


class AuditAloneTest(unittest.TestCase):
    def check(self, subjects):
        http = FakeHttp([("GET", "/mailFolders/inbox/messages", {"value": [{"id": str(i), "subject": s}
                                                                          for i, s in enumerate(subjects)]})])
        return GraphMail("me", token=lambda: "tok", http=http).has_new_inbox_mail("2026-11-26T00:00:00Z",
                                                                                 skip_noise=True)

    def test_audit_alone_is_not_new_mail(self):
        self.assertFalse(self.check(["HAYA intake audit 23:52 25/11"]))
        self.assertFalse(self.check(["HAYA intake audit 00:45 26/11", "Fwd: HAYA intake audit 01:45 26/11"]))
        self.assertTrue(self.check(["HAYA intake audit 00:45 26/11", "SynXis Res Confirmed (92777EF003647 )"]))
        self.assertTrue(self.check(["Booking request 12/12"]))

    def test_job_1_itself_still_counts_the_audit(self):
        st = SimpleNamespace(data={"last_scan": "2026-11-26T00:00:00Z"})
        mail = SimpleNamespace(has_new_inbox_mail=lambda since, skip_noise=False: not skip_noise)
        self.assertFalse(precheck.inbox_has_work(mail, st))  # the watcher: audit alone
        self.assertTrue(precheck.inbox_has_work(mail, st, leftovers=True))  # job 1's own first step


if __name__ == "__main__":
    unittest.main()
