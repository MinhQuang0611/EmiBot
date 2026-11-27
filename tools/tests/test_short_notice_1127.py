"""Dev, 2026-11-27 (Travel Concierge 2825005, MALTSEVA OLGA, 05-11/12, group 31579): the confirmation went 27/11 14:05
with "50% deposit by 14:05 on 29/11" and "the remaining 50% by 28/11", and at 15:03 job 3 auto-sent a balance reminder
asking for 100% by 28/11. Booked 8-9 days ahead, the 48-hour deposit deadline falls after the balance date.
Now (dev chose "cách 1"): payments-due puts such a booking under SHORT NOTICE (no reminder, Karen sets the date), and
the confirmation's payment terms are one line, full payment by the deadline."""
import tempfile
import unittest
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone

from tools import emi, payments
from tools.state import State
from tools.tests.test_payments import FakeMail, MAILBOX, row

VN = timezone(timedelta(hours=7))

EN = ("Dear Ms. Toktubayeva,\n\nPlease find the booking confirmation below and the attached PDF:\n\n"
      "Total: VND 10,200,000, including breakfast, VAT and service charge.\n\nPayment terms:\n"
      "– 50% deposit (VND 5,100,000) by [DEPOSIT DEADLINE], Vietnam time (UTC+7), 48 hours after receiving this "
      "confirmation.\n"
      "– The remaining 50% (VND 5,100,000) is payable 7 days before check-in (by 28/11/2026).\n"
      "The booking will be automatically released without further notice if the deposit is not received by the "
      "deadline.\n\nBank details:\nAccount name: CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC\n"
      "Account number: 1020729617\n\nBest regards,\nReservations Team")
VI = ("Kính gửi chị Lan,\n\nTổng tiền: 3.400.000 VND (đã bao gồm ăn sáng và 8% VAT)\n\nThanh toán:\n"
      "– Đặt cọc 50% = 1.700.000 VND trước [DEPOSIT DEADLINE] (giờ Việt Nam, UTC+7), 48 giờ kể từ khi nhận xác nhận "
      "này.\n"
      "– Thanh toán 50% còn lại = 1.700.000 VND trước ngày 28/11/2026 (07 ngày trước ngày đến).\n"
      "Booking sẽ tự động hủy nếu khách sạn không nhận được tiền cọc đúng hạn.\n\n"
      "Số tài khoản: 1020729617\n\nTrân trọng,\nReservations Team")
TA = {"channel_type": "TA", "company": "Vietnam Travel Concierge", "arrival": "05/12/2026", "departure": "11/12/2026"}
DUE = datetime(2026, 11, 29, 14, 5, tzinfo=VN)


class FullPaymentLineTest(unittest.TestCase):
    def test_english_split_becomes_one_line(self):
        text = emi._apply_full_payment(EN, emi.full_payment_fix(EN, TA, DUE))
        self.assertIn("– Full payment (VND 10,200,000) by 14:05 on 29/11/2026, Vietnam time (UTC+7), 48 hours after "
                      "receiving this confirmation.", text)
        self.assertNotIn("50%", text)
        self.assertNotIn("[DEPOSIT DEADLINE]", text)
        self.assertIn("if the full payment is not received", text)
        emi.check_confirmation_text(text)

    def test_vietnamese_split_becomes_one_line(self):
        text = emi._apply_full_payment(VI, emi.full_payment_fix(VI, TA, DUE))
        self.assertIn("– Thanh toán 100% = 3.400.000 VND trước 14:05 ngày 29/11/2026 (giờ Việt Nam, UTC+7), 48 giờ kể "
                      "từ khi nhận xác nhận này.", text)
        self.assertNotIn("50%", text)
        self.assertIn("không nhận được đủ tiền thanh toán đúng hạn", text)

    def test_deadline_before_the_balance_date_keeps_the_split(self):
        self.assertEqual(emi.full_payment_fix(EN, dict(TA, arrival="15/12/2026"), DUE), ([], []))

    def test_deadline_at_or_after_check_in_is_check_in_day_14h(self):
        text = emi._apply_full_payment(EN, emi.full_payment_fix(EN, dict(TA, arrival="29/11/2026"), DUE))
        self.assertIn("Full payment (VND 10,200,000) by 14:00 on 29/11/2026, Vietnam time (UTC+7), before check-in.",
                      text)

    def test_ota_and_tour_operator_untouched(self):
        for kind in ({"channel_type": "OTA"}, {"channel_type": "Tour operator"}, {"company": "Ohmyhotel"}):
            self.assertEqual(emi.full_payment_fix(EN, dict(TA, **kind), DUE), ([], []))

    def test_unreadable_split_is_refused(self):
        two = EN.replace("– The remaining", "– 50% deposit (VND 5,100,000) again\n– The remaining")
        with self.assertRaisesRegex(emi.Refused, "not before the balance date"):
            emi.full_payment_fix(two, TA, DUE)

    def test_outlook_pieces_after_the_bullet(self):
        changes, drops = emi.full_payment_fix(EN, TA, DUE)
        old, new, kept = changes[0]
        self.assertTrue(old[kept:].startswith("50% deposit"))
        self.assertTrue(new[kept:].startswith("Full payment"))
        line, b_kept = drops[0]
        self.assertTrue(line[b_kept:].startswith("The remaining 50%"))


class DropLineTest(unittest.TestCase):
    def test_list_item_and_br_line_dropped(self):
        from tools.graph_mail import drop_line
        html = "<ul><li style='x'>A</li><li style='x'>The remaining 50% (VND 1)</li></ul>"
        self.assertEqual(drop_line(html, "The remaining 50% (VND 1)"), "<ul><li style='x'>A</li></ul>")
        html = "<p>Line one<br>\nThe remaining 50% (VND 1)<br>\nLine three</p>"
        self.assertEqual(drop_line(html, "The remaining 50% (VND 1)"), "<p>Line one<br>\nLine three</p>")


class PaymentsDueTest(unittest.TestCase):
    def rows(self, arrival, balance):
        return [row(5, booking_ref="2825005", ezfolio_group_code="31579", arrival=arrival, departure="11/12/2026",
                    total_vnd="10200000", **{"Remaining amount": "10200000"},
                    COD=f"48h after confirmation is received (deposit 50%); balance by {balance}")]

    def test_deposit_deadline_after_balance_date_is_short_notice(self):
        st = State(tempfile.mktemp(suffix="-state.json"))
        r = payments.due(self.rows("05/12/2026", "28/11/2026"), emi.booking_state, emi._parts,
                         FakeMail(sent_at="2026-11-27T07:05:00Z", code="31579"), st, MAILBOX,
                         datetime(2026, 11, 27, 15, 0, tzinfo=VN))
        self.assertEqual(r["remind"], [])
        self.assertEqual([i["ref"] for i in r["short_notice"]], ["2825005"])
        text = payments.render(r, datetime(2026, 11, 27, 15, 0, tzinfo=VN))
        self.assertIn("deposit deadline 14:05 29/11/2026 is not before the balance date 28/11/2026", text)
        self.assertIn("Karen sets the deadline, no reminder", text)

    def test_ten_days_ahead_is_chased_as_before(self):
        st = State(tempfile.mktemp(suffix="-state.json"))
        r = payments.due(self.rows("09/12/2026", "02/12/2026"), emi.booking_state, emi._parts,
                         FakeMail(sent_at="2026-11-27T07:05:00Z", code="31579"), st, MAILBOX,
                         datetime(2026, 11, 29, 9, 0, tzinfo=VN))
        self.assertEqual(r["short_notice"], [])
        self.assertEqual([i["which"] for i in r["remind"]], ["deposit"])


class AttachShortNoticeTest(unittest.TestCase):
    """The early draft of 2825005 itself: confirmation-attach on 27/11 14:05 puts one full-payment line in Outlook."""

    def setUp(self):
        import os
        from tools.tests.test_attach_terms_1127 import AttachTest, PDF_TEXT, TA as ROW
        from tools.tests.test_confirmation_before_pdf_1107 import outlook_mail
        self._mode = os.environ.pop("EMI_DRAFT_MODE", None)
        self.addCleanup(lambda: os.environ.__setitem__("EMI_DRAFT_MODE", self._mode) if self._mode else None)
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.body = os.path.join(self.dir.name, "b.txt")
        with open(self.body, "w", encoding="utf-8") as f:
            f.write(VI.replace("Kính gửi chị Lan,", "Kính gửi chị Lan,\n\nMã đoàn: #[GROUP CODE]\nSố xác nhận: [CONF NO]")
                    .replace("Số tài khoản", "Tên tài khoản: CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC\nSố tài khoản"))
        self.st = State(os.path.join(self.dir.name, "s.json"))
        self.html = ["<html><body><div>quoted thread</div></body></html>"]
        self.mail, self.http = outlook_mail(self.html)
        self.row = dict(ROW, arrival="05/12/2026", departure="11/12/2026")
        self.harness = AttachTest()
        self.harness.dir, self.harness.body, self.harness.st = self.dir, self.body, self.st
        self.harness.mail, self.harness.http, self.harness.tg = self.mail, self.http, None
        self.pdf_text = PDF_TEXT

    def test_outlook_draft_gets_one_payment_line(self):
        from unittest import mock
        from tools import attachments
        from tools.graph_mail import DO_NOT_SEND
        from tools.tests.test_confirmation_before_pdf_1107 import BUILT, FakeSheet
        n = self.harness.draft(self.row)
        self.assertIn("50% còn lại", self.html[0])
        lines = []
        with mock.patch.object(emi, "pdf_fetch", self.harness.fake_pdf),                 mock.patch.object(attachments, "extract_text", lambda *a: self.pdf_text):
            emi.confirmation_attach(self.mail, FakeSheet({**self.row, **BUILT}), self.st,
                                    SimpleNamespace(n=n, attach=[]), out=lines.append,
                                    now=datetime(2026, 11, 27, 14, 5, tzinfo=VN))
        self.assertNotIn(DO_NOT_SEND, self.html[0])
        self.assertNotIn("50%", self.html[0])
        self.assertIn("Thanh toán 100% = 3.400.000 VND trước 14:05 ngày 29/11/2026", self.html[0])
        self.assertNotIn("<li", self.html[0].split("100% = 3.400.000")[1].split("</ul>")[0])  # no empty bullet left
        text = self.st.data["reviews"][n]["text"]
        self.assertIn("Thanh toán 100% = 3.400.000 VND", text)
        self.assertNotIn("50%", text)
        self.assertTrue(any("payment terms written as one line" in x for x in lines), lines)


if __name__ == "__main__":
    unittest.main()
