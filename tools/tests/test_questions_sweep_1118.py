"""Old questions to Karen that no longer wait on her (dev, 2026-11-18: "cho Emi rà và đóng mấy câu cũ đi"; 442 open,
asked 30/10–18/11). questions-sweep closes what the sheet or the state shows settled; question-close one by one."""
import os
import tempfile
import unittest
from datetime import date, datetime, timezone

from tools import emi, karen_memory
from tools.state import State


class Sheet:
    def __init__(self, rows):
        self._rows = rows

    def rows(self):
        return [dict(r, _row=i + 3) for i, r in enumerate(self._rows)]


def row(ref, action="NEW", dep="25/11/2026", at="01/11/2026 10:00", **k):
    return dict(booking_ref=ref, action=action, departure=dep, received_at=at, **k)


TODAY = date(2026, 11, 18)
NOW = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)


class SweepTest(unittest.TestCase):
    def setUp(self):
        self.st = State(os.path.join(tempfile.mkdtemp(), "state.json"))
        self.lines = []

    def ask(self, ref, text, mid="", days_ago=5):
        qid = self.st.ask(ref, text, mid)
        self.st.data["questions"][qid]["asked_at"] = f"2026-11-{18 - days_ago:02d}T03:00:00Z"
        return qid

    def sweep(self, rows, apply=True):
        return emi.sweep_questions(Sheet(rows), self.st, apply=apply, out=self.lines.append, today=TODAY, now=NOW)

    def test_stay_over_cancelled_and_built_are_closed(self):
        over = self.ask("TA111", "Late check-out fee?")
        gone = self.ask("TA222", "Fee for this cancellation?")
        built = self.ask("TA333", "Hệ thống nhập EZFOLIO dừng ở booking TA333: hết phòng. Quyết định thế nào?")
        live = self.ask("TA444", "Which rate for the Indian guests?")
        rows = [row("TA111", dep="10/11/2026"),
                row("TA222"), row("TA222", action="CANCEL", at="05/11/2026 09:00", ez_status="done"),
                row("TA333", ez_status="done", pdf_link="https://drive/x.pdf"),
                row("TA444")]
        close, keep = self.sweep(rows)
        self.assertEqual([q for q, _, _ in close], [over, gone, built])
        self.assertEqual([q for q, _, _ in keep], [live])
        self.assertEqual(list(self.st.open_questions()), [live])
        self.assertIn("stay over (departure 10/11/2026)", self.st.data["questions"][over]["closed"]["reason"])

    def test_superseded_and_draft_handled_are_closed(self):
        old = self.ask("TA555", "Deposit deadline?", mid="m1", days_ago=6)
        new = self.ask("TA555", "Deposit deadline, again?", mid="m1", days_ago=4)
        emi.karen_answer(self.st, new, "48 hours", out=self.lines.append)
        handled = self.ask("", "Is the pool heated?", mid="m2")
        self.st.data["reviews"]["12"] = {"source": "m2", "status": "gone", "history": []}
        waiting = self.ask("", "Can we offer the meeting room?", mid="m3")
        self.st.data["reviews"]["13"] = {"source": "m3", "status": "pending", "history": []}
        close, keep = self.sweep([row("TA555")])
        reasons = {q: why for q, _, why in close}
        self.assertEqual(reasons[old], f"Karen answered {new} on the same email")
        self.assertIn("draft #12 is gone", reasons[handled])
        self.assertEqual([q for q, _, _ in keep], [waiting])

    def test_held_booking_and_young_questions_are_kept(self):
        held = self.ask("TA666", "Which cancellation terms?")
        self.st.data["confirmation_holds"]["TA666"] = {"reason": "terms differ"}
        young = self.ask("TA777", "Fee?", days_ago=0)
        close, keep = self.sweep([row("TA666", dep="01/11/2026"), row("TA777", dep="01/11/2026")])
        self.assertEqual(close, [])
        self.assertEqual([(q, why) for q, _, why in keep], [(held, "confirmation held on TA666")])
        self.assertIn(young, self.st.open_questions())

    def test_without_apply_nothing_changes(self):
        q = self.ask("TA111", "Late check-out fee?")
        self.sweep([row("TA111", dep="10/11/2026")], apply=False)
        self.assertIn(q, self.st.open_questions())
        self.assertIn("nothing changed", self.lines[0])

    def test_closed_is_not_an_answer_and_karen_can_still_answer(self):
        q = self.ask("TA888", "Pool heated?")
        emi.question_close(self.st, q, "answered by front office on the email", out=self.lines.append)
        self.assertNotIn(q, self.st.open_questions())
        self.assertEqual(karen_memory.answered(self.st), {})
        with self.assertRaises(emi.Refused):
            emi.question_close(self.st, q, "again", out=self.lines.append)
        with self.assertRaises(emi.Refused):
            emi.reword_question(self.st, None, q, "Is the pool heated?", out=self.lines.append)
        emi.karen_answer(self.st, q, "yes, 28 degrees", out=self.lines.append)
        self.assertNotIn("closed", self.st.data["questions"][q])
        emi.questions(self.st, everything=True, out=self.lines.append)
        self.assertTrue(any(l.startswith(f"{q} [answered]") for l in self.lines))

    def test_close_refused_on_a_held_booking(self):
        q = self.ask("TA666", "Which terms?")
        self.st.data["confirmation_holds"]["TA666"] = {"reason": "terms differ"}
        with self.assertRaises(emi.Refused) as e:
            emi.question_close(self.st, q, "moot", out=self.lines.append)
        self.assertIn("confirmation-hold TA666 0 --clear", str(e.exception))

    def test_duplicate_on_a_held_booking_closes_while_one_stays(self):  # dev 18/11, Odeon 1326004734 ×6
        old = self.ask("Odeon 1326004734", "SPO code?")
        new = self.ask("Odeon 1326004734", "SPO code and arrival date?")
        self.st.data["confirmation_holds"]["Odeon 1326004734"] = {"reason": "price"}
        emi.question_close(self.st, old, f"duplicate, merged into {new}", out=self.lines.append)
        self.assertEqual(list(self.st.open_questions()), [new])
        with self.assertRaises(emi.Refused):
            emi.question_close(self.st, new, "moot", out=self.lines.append)


if __name__ == "__main__":
    unittest.main()
