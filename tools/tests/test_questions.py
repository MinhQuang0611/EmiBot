"""A draft only with every fact in it (dev, 2026-10-22): a '[...: hotel to confirm]' gap is refused by every draft
command, and the missing fact goes to Karen with ask-karen / karen-answer. tools/emi.py."""
import os
import tempfile
import unittest

from tools import emi
from tools.state import State
from tools.telegram import Telegram

POOL = ("Dear Zion,\n\nSwimming Pool [number/name: hotel to confirm]\n1. Pool type\n"
        "[Indoor or outdoor: hotel to confirm]\n\nBest,\nHAYA Team")
POOL_VI = "Chào anh/chị,\n\nGiá đưa đón: [giá đưa đón: khách sạn xác nhận].\n\nBest,\nHAYA Team"


class GapTest(unittest.TestCase):
    def test_english_and_vietnamese_gaps_refused(self):
        with self.assertRaises(emi.Refused) as e:
            emi.check_no_gaps(POOL, "m1")
        self.assertIn("2 gap(s): [number/name: hotel to confirm] | [Indoor or outdoor: hotel to confirm]",
                      str(e.exception))
        self.assertIn("ask-karen m1", str(e.exception))
        with self.assertRaises(emi.Refused):
            emi.check_no_gaps(POOL_VI)

    def test_complete_text_and_ordinary_brackets_pass(self):
        emi.check_no_gaps("Dear Zion,\n\nOur outdoor pool is open 09:00-22:00, free for guests.\n\nBest,\nHAYA Team")
        emi.check_no_gaps("FW: [TEST] Đặt phòng – [URGENT] booking 0410STE251026")


class QuestionTest(unittest.TestCase):
    def setUp(self):
        d = tempfile.mkdtemp()
        self.st = State(os.path.join(d, "state.json"))
        self.sent = []
        self.tg = Telegram("42", "TOKEN", http=lambda m, url, body=None, **k: self.sent.append(body) or
                           {"ok": True, "result": {"message_id": len(self.sent)}})
        self.lines = []

    def ask(self, q="Is the pool indoor or outdoor, and how many pools?", mid="m1"):
        return emi.ask_karen(self.st, self.tg, mid, q, ref="R1", out=self.lines.append)

    def test_ask_records_and_posts_once(self):
        self.assertEqual(self.ask(), "E-001")
        self.assertEqual(self.ask(), "E-001")  # same question for the same email: not asked twice
        self.assertEqual(len(self.sent), 1)
        self.assertIn("E-001 — câu hỏi cho Karen", self.sent[0]["text"])
        q = self.st.data["questions"]["E-001"]
        self.assertEqual((q["message_id"], q["booking_ref"], q["answer"]), ("m1", "R1", None))

    def test_question_must_be_words_not_a_gap(self):
        with self.assertRaises(emi.Refused):
            self.ask("[pool type: hotel to confirm]")

    def test_answer_releases_the_email_when_all_answered(self):
        self.ask()
        self.ask("Is the pool heated?")
        emi.karen_answer(self.st, "e-001", "1 outdoor pool on the 2nd floor", out=self.lines.append)
        self.assertIn("the same email still waits on E-002: no draft yet", self.lines)
        emi.karen_answer(self.st, "E-002", "No", out=self.lines.append)
        self.assertTrue(any(x.startswith("every question for email m1 is answered") for x in self.lines))
        self.assertEqual(self.st.open_questions(), {})

    def test_unknown_question_refused(self):
        with self.assertRaises(emi.Refused):
            emi.karen_answer(self.st, "E-009", "yes", out=self.lines.append)

    def test_questions_listing(self):
        self.ask()
        emi.questions(self.st, out=self.lines.append)
        self.assertTrue(self.lines[-2].startswith("E-001 [open]"))
        self.assertIn("email m1", self.lines[-2])


if __name__ == "__main__":
    unittest.main()
