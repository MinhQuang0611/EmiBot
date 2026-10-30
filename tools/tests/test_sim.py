"""Offline tests for the simulated mailbox (tools/sim_mail.py) on the real scenario files."""
import json
import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace

from tools import emi, review, sim
from tools.sim_mail import SimMail
from tools.state import State
from tools.telegram import Telegram


class SimMailTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        shutil.copytree(os.path.join(sim.scenario_dir("new-change-cancel"), "inbox"), os.path.join(self.dir, "inbox"))
        self.mail = SimMail(self.dir)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_inbox_threads_and_search(self):
        ids = [m["id"] for m in self.mail.list_inbox_since("2030-01-01T00:00:00Z")]
        self.assertEqual(ids, ["sim-01-new-1512", "sim-02-change-1511", "sim-03-cancel-1512"])
        cancel = self.mail.get_message_text("sim-03-cancel-1512")
        thread = self.mail.get_thread(cancel["conversationId"], text=True)
        self.assertEqual([m["id"] for m in thread], ["sim-01-new-1512", "sim-03-cancel-1512"])
        self.assertEqual(cancel["receivedDateTime"], "2026-10-15T08:00:00Z")
        self.assertEqual([m["id"] for m in self.mail.search("TEST-1511")], ["sim-02-change-1511"])

    def test_drafts_go_to_files_not_graph(self):
        d = self.mail.reply_draft_with_text("sim-03-cancel-1512", "Kính gửi anh/chị Minh,\n\nBest,\nHAYA Team")
        self.mail.add_attachment(d["id"], "conf.pdf", b"%PDF")
        with open(os.path.join(self.dir, "drafts", d["id"] + ".json"), encoding="utf-8") as f:
            meta = json.load(f)
        self.assertEqual(meta["subject"], "RE: TEST - Đặt phòng TEST-1512")
        self.assertEqual(meta["to"], ["nguyenminhquang061105@gmail.com"])
        self.assertEqual(meta["attachments"][0]["name"], "conf.pdf")
        self.assertFalse(hasattr(self.mail, "_call"))  # no route to Graph at all

    def test_amounts_match_whatever_the_separator(self):
        for written in ("2,100,000 VND", "2.100.000 VND", "2100000"):
            self.assertIn(sim._digits("2.100.000"), sim._digits(written))
        self.assertNotIn(sim._digits("2.100.000"), sim._digits("2,500,000"))


class NoRows:
    def find_by_ref(self, ref):
        return []


GOOD_REPLY = ("Dear Guest,\n\nThank you for your email. We have noted your request for two rooms on the same floor, "
              "subject to availability, and your arrival at around 21:00 on 14/11/2026: our front office will be "
              "expecting you. Check-out is at 12:00; late check-out is subject to availability and charged at "
              "[% of one night's room rate: hotel to confirm]. [luggage storage after check-out: hotel to confirm]"
              "\n\nWe look forward to welcoming you.\n\nBest,\nHAYA Team")
OLD_STYLE = ("Dear Guest,\n\nThank you for your email about your stay from 14/11/2026 to 17/11/2026.\n\nWe have noted "
             "your arrival at around 21:00 on 14/11/2026 and will pass it to our front office. Check-in is from 14:00, "
             "so an evening arrival is a normal check-in with no extra charge.\n\nBest,\nHAYA Team")
BAD_REPLY = ("Dear 유정아,\n\nThe luggage-storage policy is not shown in the reservation record currently "
             "available to us.\n\nBest,\nHAYA Team")
CHECK_REPLY = ("[CHECK BEFORE SENDING: late check-out % basis and luggage storage are not in hotel-info.md]\n"
               "Dear Guest,\n\nThank you for your email. We have noted your request for two rooms on the same floor, "
               "subject to availability, and your arrival at around 21:00 on 14/11/2026. Check-out is at 12:00; late "
               "check-out is subject to availability and charged by the hour of departure. You are welcome to leave "
               "your luggage with us after check-out.\n\nWe look forward to welcoming you.\n\nBest regards,\n"
               "Reservations Team")
class OperationalRequestScenarioTest(unittest.TestCase):
    """test/sim/operational-request: sim-check grades kinds and forwards, in Outlook and Telegram draft mode."""

    def setUp(self):
        self._mode = os.environ.pop("EMI_DRAFT_MODE", None)
        self.addCleanup(lambda: os.environ.__setitem__("EMI_DRAFT_MODE", self._mode) if self._mode else None)
        self.work = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.work, True)
        self.dir = sim.run_dir(self.work, "operational-request")
        shutil.copytree(os.path.join(sim.scenario_dir("operational-request"), "inbox"), os.path.join(self.dir, "inbox"))
        self.mail = SimMail(self.dir)
        self.st = State(os.path.join(self.dir, "state.json"))
        self._work_dir = emi.WORK_DIR
        emi.WORK_DIR = self.dir
        self.addCleanup(setattr, emi, "WORK_DIR", self._work_dir)
        self.tg = None

    def body(self, name, text):
        path = os.path.join(self.work, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def draft(self, text, kind, forward_to=None):
        args = SimpleNamespace(message_id="sim-01-request", body=self.body(kind + ".txt", text), all=False,
                               kind=kind, ref="TEST-26090313011477ES1", row="", to=forward_to or "")
        fn = emi.draft_forward if forward_to else emi.draft_reply
        return fn(self.mail, self.st, args, tg=self.tg, out=lambda *_: None)

    def grade(self):
        self.st.save()
        lines = []
        ok = sim.check(NoRows(), "operational-request", self.work, out=lines.append)
        return ok, "\n".join(lines)

    def test_email_reads_with_the_korean_name_and_both_refs(self):
        m = self.mail.get_message_text("sim-01-request")
        self.assertEqual(m["from"]["emailAddress"]["name"], "유정아")
        self.assertEqual(m["subject"], "Hello")
        self.assertIn("TEST-2609031300E485ES1", m["body"]["content"])

    def ask(self):
        emi.ask_karen(self.st, self.tg, "sim-01-request", "Late check-out 25/50/100%: of what rate? Luggage storage "
                      "after check-out: offered, and is it free?", ref="TEST-26090313011477ES1", out=lambda *_: None)

    def test_reply_with_gaps_refused_best_answer_with_check_line_instead(self):
        # Tracy's audit 29/10: a complete best answer, the doubt in a CHECK line on top, Karen asked
        with self.assertRaises(emi.Refused) as e:
            self.draft(GOOD_REPLY, "request")
        self.assertIn("2 gap(s)", str(e.exception))
        self.assertIn("ask-karen sim-01-request", str(e.exception))
        self.draft(CHECK_REPLY, "request")
        self.ask()
        with self.assertRaises(emi.Refused):  # dev 30/10: requests go in the row's notes, not to front office
            self.draft("**Yêu cầu:**\n• 2 phòng cùng tầng", "forward", forward_to="haya@haya-hotels.com")
        ok, report = self.grade()
        self.assertTrue(ok, report)
        self.assertIn("PASS no forward to haya@haya-hotels.com", report)
        self.assertIn("PASS drafts of kind 'request': 1", report)
        self.assertIn("PASS questions to Karen: 1", report)

    def test_no_question_fails(self):
        self.draft(CHECK_REPLY, "request")
        ok, report = self.grade()
        self.assertFalse(ok)
        self.assertIn("FAIL questions to Karen: 0", report)

    def test_robotic_reply_fails(self):
        self.draft(OLD_STYLE, "request")  # draft #3 of the live run, 2026-10-22
        ok, report = self.grade()
        self.assertFalse(ok)
        for line in ("FAIL no draft says 'normal check-in'", "FAIL no draft says 'no extra charge'",
                     "FAIL no draft says 'Thank you for your email about'"):
            self.assertIn(line, report)

    def test_first_live_run_fails(self):
        self.draft(BAD_REPLY, "inquiry")  # draft #2 as it was: wrong kind, blind-spot sentences
        ok, report = self.grade()
        self.assertFalse(ok)
        for line in ("FAIL no draft says 'available to us'", "FAIL no draft says 'not shown in'",
                     "FAIL questions to Karen: 0",
                     "FAIL drafts of kind 'inquiry': 1", "FAIL no draft says 'Dear 유정아'"):
            self.assertIn(line, report)

    def test_telegram_mode_drafts_are_graded_from_the_reviews(self):
        os.environ["EMI_DRAFT_MODE"] = "telegram"
        self.addCleanup(os.environ.pop, "EMI_DRAFT_MODE", None)
        self.tg = Telegram("42", "TOKEN", http=lambda *a, **k: {"ok": True, "result": {"message_id": 1}})
        self.assertEqual(self.draft(BAD_REPLY, "request")["id"], "pending-1")
        self.assertFalse(os.path.isdir(os.path.join(self.dir, "drafts")))  # nothing in Outlook yet
        ok, report = self.grade()
        self.assertFalse(ok)
        self.assertIn("FAIL no draft says 'available to us' (found in ['#1'])", report)
        review.deny(self.mail, self.st, self.tg, "1", out=lambda *_: None)  # a denied draft no longer counts
        self.draft(CHECK_REPLY, "request")
        self.ask()
        ok, report = self.grade()
        self.assertTrue(ok, report)


if __name__ == "__main__":
    unittest.main()
