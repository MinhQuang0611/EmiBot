"""Dev, 2026-11-27 ("tại sao vẫn cứ dính các case này"): Travel Concierge 2825005 and We Go Asia sat with DO NOT SEND
after their build, because the TA template's cancellation line (7 days) wasn't the EZFOLIO PDF's (3 days) and
confirmation-attach refused; nothing held them, so nobody saw it. Pegas 11162942's early draft was on a row from before
its decline and rebook, so it was "not built yet" for ever.
Then, the same day (EZFOLIO group 31347): "phần term sẽ đổi thành free trong 7 ngày thay vì 3 ngày như trước, thế nên
các câu hỏi về phí hủy sẽ ko cần hỏi lại". HAYA's terms are the template's 7 days: the email's cancellation line is no
longer compared with or rewritten from the PDF, a question about it is refused, and questions-sweep closes the old ones
and clears their holds. Any other refusal on a built booking still holds it and says so on Telegram; a draft from
before a rebook goes to the rebuilt booking's row."""
import os
import tempfile
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest import mock

from tools import attachments, emi
from tools.graph_mail import DO_NOT_SEND
from tools.state import State
from tools.tests.test_confirmation_before_pdf_1107 import BUILT, VN, FakeSheet, outlook_mail

PDF_TEXT = ("III. Cancellation Policy:\n1. The cancellation is free of charge 3 days prior to the date of arrival\n"
            "2. Otherwise, 100% the total amount as cancellation fee will be applied.\n"
            "Notice: All above rates quoted are VND, inclusive of 10% Government Tax, 5% Service Charge.")
VI_TERMS = ("Chính sách hủy: hủy trước 07 ngày so với ngày đến: miễn phí; hủy trong vòng 3–6 ngày: phí 01 đêm; hủy "
            "trong vòng 3 ngày: phí 50% tổng tiền booking; no-show: 100%.")
EN_TERMS = ("Cancellation: free of charge more than 7 days before check-in; 3–6 days: 1 night charge; within 3 days: "
            "50% of the booking total; no-show: 100%.")
TA = {"action": "NEW", "received_at": "26/11/2026 10:00", "source_email": "Booking request",
      "channel_type": "TA", "company": "Travel Concierge", "booking_ref": "2825005", "guest_names": "NGUYEN VAN A",
      "arrival": "20/12/2026", "departure": "22/12/2026", "room_code": "DLX-SV", "rooms": "1",
      "total_vnd": "3400000", "status": "Definite", "_row": 2790}
BODY = ("Kính gửi chị Lan,\n\nKhách sạn xin xác nhận đặt phòng như sau:\n\nMã đoàn: #[GROUP CODE]\n"
        "Số xác nhận: [CONF NO]\nTổng tiền: 3.400.000 VND (đã bao gồm ăn sáng và 8% VAT)\n\n"
        "– Đặt cọc 50% = 1.700.000 VND trước [DEPOSIT DEADLINE] (giờ Việt Nam, UTC+7), 48 giờ kể từ khi "
        "nhận xác nhận này.\n\n" + VI_TERMS + "\n\nTên tài khoản: CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC\n"
        "Số tài khoản: 1020729617\n\nTrân trọng,\nReservations Team")


class Tg:
    def __init__(self):
        self.sent = []

    def send(self, text, buttons=None, topic=None):
        self.sent.append((text, topic))
        return len(self.sent)


HOST_TERMS = (
    "For HT 2702 17-21, please confirm whether to accept GrandViet Tour's split 50% deposit schedule for 4 rooms first "
    "and 3 rooms at the end of November 2026, provide guest counts and rooming list, and confirm the cancellation terms: "
    "PDF free until 3 days before arrival then 100%, versus draft #728's TA terms.",
    "PDF EZFOLIO ghi hủy miễn phí trước 3 ngày, sau đó 100%, nhưng điều khoản trong email/draft đang là 7 ngày, 3–6 "
    "ngày và 3 ngày. Xin xác nhận điều khoản nào áp dụng trước khi hoàn tất draft #838.",
    "NPKM00750000002: Chính sách hủy trong draft là miễn phí trước 7 ngày, 3–6 ngày phí 1 đêm, dưới 3 ngày 50%; PDF "
    "EZFOLIO ghi miễn phí trước 3 ngày, sau đó 100%. Cần xác nhận điều khoản áp dụng trước khi đính PDF.",
    "For SI781720A, the email cancellation terms are 6/7 days, while the EZFOLIO PDF says free cancellation until 3 days "
    "before arrival and then 100%. Which terms apply?",
    "2816829: The agency booking gives 7-day cancellation terms, while the EZFOLIO PDF gives free cancellation until 3 "
    "days before arrival then 100%. Which terms should we confirm?",
    "2825005: cancellation terms conflict — original TA booking says 7-day terms; EZFOLIO PDF says free until 3 days, "
    "then 100%. Please confirm which terms apply.",
    "PDF cancellation terms are free until 3 days before arrival then 100%; original booking email states 6/7-day "
    "terms. Confirm which terms apply.",
    "confirmation-attach #838 refused: the email gives cancellation 7 days but the EZFOLIO PDF says 3 days")
HOST_NOT_TERMS = (
    "Agoda 724017135: email ghi hủy miễn phí trước 1 ngày, PDF EZFOLIO ghi trước 3 ngày. Xin xác nhận điều khoản nào "
    "áp dụng.",
    "Agoda email states cancellation free until 1 day before arrival; EZFOLIO PDF states 3 days. Confirm the "
    "applicable cancellation terms.",
    "365 Travel now requests a refund of the VND 7,650,000 deposit to the supplied VietinBank account. The booking was "
    "cancelled without charge, but EZFOLIO is needs_review because the deposit remains. May we approve the refund and "
    "draft it to accounting?")


class TermsQuestionTest(unittest.TestCase):
    def setUp(self):
        self.st = State(os.path.join(tempfile.mkdtemp(), "state.json"))

    def test_terms_questions_recognised(self):
        for q in ("Greentours 0349-IN 1211: the PDF's cancellation terms (free until 3 days, then 100%) differ from the "
                  "TA terms in #838. Which terms apply?",
                  "Cancellation 7 days in the template, 3 days in the EZFOLIO PDF: which line goes in the email?",
                  "AAT261113 cancelled exactly 7 days before arrival: which line of the cancellation table applies?",
                  "Chính sách hủy: template 7 ngày, PDF 3 ngày?"):
            self.assertTrue(emi.is_cancel_terms_question(q), q)
        for q in HOST_TERMS:  # the open ones on hotpink-bee, 27/11
            self.assertTrue(emi.is_cancel_terms_question(q), q)
        for q in ("Direct guest Mr Roy cancels 3 days before arrival: what cancellation fee do we charge?",
                  "Direct guest cancels 7 days before arrival: what fee?",
                  "Anex 113031070 cancelled: is the contract fee 100%?",
                  "Which rate for the Indian guests?") + HOST_NOT_TERMS:
            self.assertFalse(emi.is_cancel_terms_question(q), q)

    def test_ask_karen_refuses_it(self):
        with self.assertRaisesRegex(emi.Refused, "CANCELLATION TERMS ARE NOT A QUESTION"):
            emi.ask_karen(self.st, None, "m1", "The PDF says free cancellation 3 days, our email 7 days: which terms?",
                          ref="2825005", out=lambda *_: None)
        self.assertEqual(self.st.open_questions(), {})

    def test_sweep_closes_old_questions_and_clears_terms_holds(self):
        terms = self.st.ask("0349-IN 1211", "The PDF's cancellation terms (3 days, then 100%) differ from the TA "
                                            "template's 7 days. Which apply?", "m1")
        other = self.st.ask("TA444", "Which rate for the Indian guests?", "m2")
        self.st.data["questions"][other]["asked_at"] = "2026-11-27T03:00:00Z"
        self.st.data["confirmation_holds"] = {
            "0349-IN 1211": {"pdf_link": "x", "reason": "confirmation-attach #838 refused: the email gives "
                             "cancellation 7 days but the EZFOLIO PDF says 3 days"},
            "AMARA": {"pdf_link": "y", "reason": "PDF 14 rooms, email 12 rooms"}}
        lines = []
        close, keep = emi.sweep_questions(SimpleNamespace(rows=lambda: []), self.st, apply=True, out=lines.append,
                                          now=datetime(2026, 11, 27, 12, 0, tzinfo=VN))
        self.assertEqual([q for q, _, _ in close], [terms])  # closed though younger than two days
        self.assertIn("cancellation terms settled", self.st.data["questions"][terms]["closed"]["reason"])
        self.assertEqual(list(self.st.open_questions()), [other])
        self.assertEqual(list(self.st.data["confirmation_holds"]), ["AMARA"])
        self.assertTrue(any(line.startswith("CLEAR HOLD 0349-IN 1211") for line in lines), lines)


class AttachTest(unittest.TestCase):
    def setUp(self):
        self._mode = os.environ.pop("EMI_DRAFT_MODE", None)
        self.addCleanup(lambda: os.environ.__setitem__("EMI_DRAFT_MODE", self._mode) if self._mode else None)
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.body = os.path.join(self.dir.name, "b.txt")
        with open(self.body, "w", encoding="utf-8") as f:
            f.write(BODY)
        self.st = State(os.path.join(self.dir.name, "s.json"))
        self.html = ["<html><body><div>quoted thread</div></body></html>"]
        self.mail, self.http = outlook_mail(self.html)
        self.tg = Tg()

    def draft(self, row=None):
        row = row or TA
        args = SimpleNamespace(message_id="m1", row=row["_row"], body=self.body, all=False, to="", cc="", subject="",
                               attach=[], before_pdf=True, replaces="")
        emi.draft_confirmation(self.mail, FakeSheet(row), self.st, args, out=lambda *_: None)
        return "1"

    def fake_pdf(self, sheet, row, out=print):
        path = os.path.join(self.dir.name, "conf.pdf")
        with open(path, "wb") as f:
            f.write(b"%PDF-1.4 conf")
        return path, "31579.pdf", "application/pdf", b"%PDF-1.4 conf"

    def attach(self, n, sheet, lines=None):
        out = (lines.append if lines is not None else (lambda *_: None))
        with mock.patch.object(emi, "pdf_fetch", self.fake_pdf), \
                mock.patch.object(attachments, "extract_text", lambda *a: PDF_TEXT):
            emi.confirmation_attach(self.mail, sheet, self.st, SimpleNamespace(n=n, attach=[]), tg=self.tg, out=out,
                                    now=datetime(2026, 11, 27, 10, 0, tzinfo=VN))

    def test_template_terms_kept_with_a_3_day_pdf(self):  # Travel Concierge 2825005; group 31347's PDF, 27/11
        n = self.draft()
        self.assertIn("07 ngày", self.html[0])
        lines = []
        self.attach(n, FakeSheet({**TA, **BUILT}), lines)
        self.assertNotIn(DO_NOT_SEND, self.html[0])
        self.assertIn(VI_TERMS.split(": ", 1)[1], self.html[0])
        self.assertNotIn("03 ngày", self.html[0])
        self.assertIn(VI_TERMS, self.st.data["reviews"][n]["text"])
        self.assertEqual(self.st.data["confirmation_holds"], {})
        self.assertFalse([t for t, topic in self.tg.sent if topic == "question"])  # no ⚠️ hold notice
        self.assertTrue([c for c in self.http.calls if c[1].endswith("/messages/d1/attachments")])

    def test_terms_line_a_person_edited_is_left_alone(self):
        n = self.draft()
        self.html[0] = self.html[0].replace("07 ngày", "10 ngày")  # a person changed it by hand
        self.attach(n, FakeSheet({**TA, **BUILT}))
        self.assertNotIn(DO_NOT_SEND, self.html[0])
        self.assertIn("10 ngày", self.html[0])
        self.assertEqual(self.st.data["confirmation_holds"], {})

    def test_refusal_on_a_built_booking_holds_it_once(self):
        n = self.draft()
        built = FakeSheet({**TA, **BUILT, "confirmation_no": ""})
        for _ in range(2):
            with self.assertRaisesRegex(emi.Refused, "confirmation_no"):
                self.attach(n, built)
        hold = self.st.data["confirmation_holds"]["2825005"]
        self.assertIn(f"confirmation-attach #{n} refused", hold["reason"])
        self.assertEqual(hold["pdf_link"], BUILT["pdf_link"])
        self.assertEqual(len(self.tg.sent), 1)  # once, not every run
        self.assertTrue(self.st.data["reviews"][n]["awaiting_pdf"])

    def test_not_built_yet_is_no_hold(self):
        n = self.draft()
        with self.assertRaises(emi.Refused):
            self.attach(n, FakeSheet({**TA, "ez_status": ""}))
        self.assertEqual(self.st.data["confirmation_holds"], {})
        self.assertEqual(self.tg.sent, [])

    def test_draft_from_before_a_rebook_goes_to_the_rebuilt_row(self):  # Pegas 11162942, 26–27/11
        n = self.draft()
        cancel = {**TA, "action": "CANCEL", "status": "Cancelled", "received_at": "26/11/2026 13:45", "_row": 2800}
        rebook = {**TA, **BUILT, "received_at": "26/11/2026 16:48", "_row": 2806,
                  "internal_notes": "Rebooked after cancellation row 2800"}
        lines = []
        self.attach(n, FakeSheet(TA, cancel, rebook), lines)
        self.assertIn("#30901", self.html[0])
        self.assertEqual(self.st.confirmation_drafted(), {("2825005", 2806)})
        self.assertEqual(self.st.awaiting_pdf(), {})
        self.assertTrue(any("row 2806" in line for line in lines), lines)

    def test_plain_unbuilt_row_with_no_rebook_still_waits(self):
        n = self.draft()
        later = {**TA, "action": "CHANGE", "received_at": "26/11/2026 12:00", "_row": 2795}
        with self.assertRaisesRegex(emi.Refused, "isn't built yet"):
            self.attach(n, FakeSheet(TA, later))


if __name__ == "__main__":
    unittest.main()
