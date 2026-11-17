"""Karen's answers kept for next time (dev, 2026-11-17): karen-answer writes karen-answers.md next to the state, and
ask-karen doesn't ask a question she has already answered. tools/karen_memory.py, tools/emi.py."""
import os
import tempfile
import unittest

from tools import emi, karen_memory
from tools.state import State
from tools.telegram import Telegram


class KarenMemoryTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.st = State(os.path.join(self.dir, "state.json"))
        self.sent = []
        self.tg = Telegram("42", "TOKEN", http=lambda m, url, body=None, **k: self.sent.append(body) or
                           {"ok": True, "result": {"message_id": len(self.sent)}})
        self.lines = []

    def ask(self, q, mid="m1", ref="R1", **kw):
        return emi.ask_karen(self.st, self.tg, mid, q, ref=ref, out=self.lines.append, **kw)

    def test_answer_is_written_to_the_file(self):
        self.ask("Hồ bơi trong nhà hay ngoài trời, có mấy hồ?")
        emi.karen_answer(self.st, "E-001", "1 hồ ngoài trời tầng 2", out=self.lines.append)
        path = os.path.join(self.dir, "karen-answers.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("E-001 · R1", text)
        self.assertIn("Karen: 1 hồ ngoài trời tầng 2", text)
        self.assertTrue(any("MEMORY.md" in l and "kept for next time" in l for l in self.lines))

    def test_same_question_on_another_email_is_refused_with_her_answer(self):
        self.ask("Is the pool indoor or outdoor, and how many pools?")
        emi.karen_answer(self.st, "E-001", "1 outdoor pool on the 2nd floor", out=self.lines.append)
        with self.assertRaises(emi.Refused) as e:
            self.ask("How many pools, indoor or outdoor?", mid="m2", ref="R2")
        self.assertIn("KAREN ALREADY ANSWERED", str(e.exception))
        self.assertIn("1 outdoor pool on the 2nd floor", str(e.exception))
        self.assertEqual(len(self.sent), 1)
        # accents and Vietnamese wording don't hide it either
        self.ask("Phụ thu trẻ em 10 tuổi ở cùng 1 người lớn phòng Standard Double?", mid="m3", ref="R3")
        emi.karen_answer(self.st, "E-002", "Không phụ thu", out=self.lines.append)
        with self.assertRaises(emi.Refused):
            self.ask("phu thu tre em 10 tuoi o cung 1 nguoi lon phong Standard Double", mid="m4", ref="R4")

    def test_again_asks_with_the_reason(self):
        self.ask("Is the pool indoor or outdoor, and how many pools?")
        emi.karen_answer(self.st, "E-001", "1 outdoor pool", out=self.lines.append)
        qid = self.ask("How many pools, indoor or outdoor?", mid="m2", ref="R2", again="new pool opened in 2027")
        self.assertEqual(qid, "E-002")
        self.assertIn("Hỏi lại vì khác E-001: new pool opened in 2027", self.st.data["questions"]["E-002"]["ask"])

    def test_unrelated_question_goes_and_a_near_one_is_shown(self):
        self.ask("Is the pool indoor or outdoor, and how many pools?")
        emi.karen_answer(self.st, "E-001", "1 outdoor pool", out=self.lines.append)
        self.assertEqual(self.ask("Do you allow pets in the rooms?", mid="m2", ref="R2"), "E-002")
        self.assertFalse(any("SIMILAR" in l for l in self.lines))
        self.assertEqual(self.ask("Is the outdoor pool heated in January?", mid="m3", ref="R3"), "E-003")
        self.assertTrue(any("SIMILAR ONE: E-001" in l for l in self.lines))

    def test_karen_answers_lists_and_searches(self):
        self.ask("Is the pool indoor or outdoor, and how many pools?")
        emi.karen_answer(self.st, "E-001", "1 outdoor pool", out=self.lines.append)
        out = []
        emi.karen_answers(self.st, "pool outdoor", out=out.append)
        self.assertIn("KAREN ANSWERS: 1", out[0])
        out = []
        emi.karen_answers(self.st, "", out=out.append)
        self.assertTrue(out[1].startswith("- E-001"))

    def test_score_ignores_accents(self):
        self.assertGreater(karen_memory.score("Đặt cọc hạn chót", "dat coc han chot"), 0.99)


if __name__ == "__main__":
    unittest.main()
