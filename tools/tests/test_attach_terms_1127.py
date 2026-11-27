"""Dev, 2026-11-27 ("tại sao vẫn cứ dính các case này"): Travel Concierge 2825005 and We Go Asia sat with DO NOT SEND
after their build, because the TA template's cancellation line (7 days) wasn't the EZFOLIO PDF's (3 days) and
confirmation-attach refused; nothing held them, so nobody saw it. Pegas 11162942's early draft was on a row from before
its decline and rebook, so it was "not built yet" for ever.
Now: the PDF's terms are written into the draft; any other refusal on a built booking holds it and says so on
Telegram; a draft from before a rebook goes to the rebuilt booking's row."""
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


class TermsHelpersTest(unittest.TestCase):
    def test_pdf_terms_read(self):
        self.assertEqual(emi.pdf_cancellation_terms(PDF_TEXT), (3, 100))
        self.assertIsNone(emi.pdf_cancellation_terms("Cancellation policy: see contract"))

    def test_vietnamese_line_rewritten(self):
        old, new, kept = emi.pdf_terms_fix("Xin chào\n" + VI_TERMS + "\nTrân trọng", PDF_TEXT)
        self.assertEqual(old[:kept], "Chính sách hủy: ")
        self.assertEqual(old, VI_TERMS)
        self.assertEqual(new, "Chính sách hủy: hủy trước 03 ngày so với ngày đến: miễn phí; sau thời hạn này: phí 100% "
                              "tổng tiền booking.")

    def test_english_line_rewritten_keeps_bullet(self):
        old, new, kept = emi.pdf_terms_fix("Dear X,\n- " + EN_TERMS + "\nBest regards,", PDF_TEXT)
        self.assertEqual(old[:kept], "- Cancellation: ")
        self.assertEqual(new, "- Cancellation: free of charge up to 3 days before the arrival date; otherwise 100% of "
                              "the booking total.")

    def test_russian_line_rewritten(self):
        _, new, _ = emi.pdf_terms_fix("Отмена: бесплатно за 7 дней до заезда.", PDF_TEXT)
        self.assertIn("за 3 дн. до даты заезда; иначе 100%", new)
        emi.check_cancellation_days(new, PDF_TEXT)

    def test_same_terms_nothing_to_do(self):
        self.assertIsNone(emi.pdf_terms_fix("Cancellation: free of charge up to 3 days before arrival.", PDF_TEXT))
        self.assertIsNone(emi.pdf_terms_fix("Thank you.", PDF_TEXT))

    def test_unreadable_pdf_terms_still_refused(self):
        with self.assertRaisesRegex(emi.Refused, "PDF says 3 days"):
            emi.pdf_terms_fix(EN_TERMS, "Cancellation within 3 days: see the contract")

    def test_two_lines_with_terms_still_refused(self):
        with self.assertRaises(emi.Refused):
            emi.pdf_terms_fix(EN_TERMS + "\nNo cancellation fee if cancelled 7 days ahead.", PDF_TEXT)


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

    def test_terms_made_the_pdfs_and_attached(self):  # Travel Concierge 2825005, 27/11
        n = self.draft()
        self.assertIn("07 ngày", self.html[0])
        lines = []
        self.attach(n, FakeSheet({**TA, **BUILT}), lines)
        self.assertNotIn(DO_NOT_SEND, self.html[0])
        self.assertNotIn("07 ngày", self.html[0])
        self.assertIn("hủy trước 03 ngày so với ngày đến: miễn phí; sau thời hạn này: phí 100%", self.html[0])
        text = self.st.data["reviews"][n]["text"]
        self.assertIn("hủy trước 03 ngày", text)
        self.assertNotIn("07 ngày", text)
        self.assertEqual(self.st.data["confirmation_holds"], {})
        self.assertTrue(any("cancellation terms written as the EZFOLIO PDF" in line for line in lines), lines)
        self.assertTrue([c for c in self.http.calls if c[1].endswith("/messages/d1/attachments")])

    def test_line_edited_in_outlook_is_held_not_overwritten(self):
        n = self.draft()
        self.html[0] = self.html[0].replace("07 ngày", "10 ngày")  # a person changed it by hand
        before = len(self.http.calls)
        with self.assertRaisesRegex(emi.Refused, "no longer has the line"):
            self.attach(n, FakeSheet({**TA, **BUILT}))
        self.assertIn(DO_NOT_SEND, self.html[0])
        self.assertFalse([c for c in self.http.calls[before:] if c[0] in ("PATCH", "POST")])
        self.assertIn("2825005", self.st.data["confirmation_holds"])
        self.assertEqual(len(self.tg.sent), 1)
        self.assertEqual(self.tg.sent[0][1], "question")

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
