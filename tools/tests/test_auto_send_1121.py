"""Auto-send, dev 2026-11-21, on the drafts left in Outlook that day:
- "Email của khách - họ hỏi booking của mình đã nhận được chưa thì cũng cho auto gửi nếu đã có trong intake sheet rồi"
  → kind booking_status, sent when the booking is on the sheet (Shana Sherin, Booking.com 5023617148, #1546).
- The cancellation reply once the CANCEL rows are on the sheet (Travel Concierge 2817840/2817841, #1552), and the
  confirmation still in Drafts for that booking (#1547) goes to Deleted Items.
- A pick-up reply gives one answer, never both (Utegelova/Gelnara Trip.com 1539369445053786, #1550).
- A send to a no-reply address bounces: held (MG cancellation to noreply@mgbedbank.com, #1539)."""
import unittest

from tools import emi
from tools.graph_mail import auto_send_refusal
from tools.tests.test_auto_send_1119 import ALL, AutoSendTest as Base

ENV = ALL + ",booking_status,cancellation"
STATUS = ("Dear Ms. Sherin,\n\nThank you for your message. We confirm that your Booking.com reservation 5023617148 "
          "for 29/11/2026 – 02/12/2026 is in our system.\n\nBest regards,\nReservations Team")
CANCEL = ("Dear Mrs. Toktubayeva,\n\nThank you for your email. We confirm that reservation No. 2817840 has been "
          "cancelled in our system without charge.\n\nBest regards,\nReservations Team")
BOTH = ("Dear Utegelova/Gelnara,\n\nComplimentary one-way airport pick-up applies when the amount paid for the "
        "booking is above USD 250. Please confirm the paid amount for this booking before sending this reply.\n\n"
        "If the booking is below that amount, airport pick-up is available as a paid transfer at VND 200,000 one "
        "way.\n\nBest regards,\nReservations Team")


def r(n, ref, action="NEW", channel="OTA", at="20/11/2026 18:00"):
    return {"_row": n, "action": action, "booking_ref": ref, "channel_type": channel, "received_at": at,
            "guest_names": "SHANA SHERIN", "arrival": "29/11/2026", "departure": "02/12/2026"}


class AutoSend1121Test(Base):
    def setUp(self):
        super().setUp()
        self.env(ENV)
        self.rows = []

    def reply(self, kind, text, ref="TEST-1512", row_="52"):
        orig = emi.draft_reply

        def with_rows(mail, st, args, tg=None, out=print):
            return orig(mail, st, args, tg=tg, out=out, rows=lambda: list(self.rows))
        emi.draft_reply = with_rows
        try:
            return super().reply(kind, text, ref=ref, row_=row_)
        finally:
            emi.draft_reply = orig

    def test_booking_status_on_the_sheet_is_sent(self):
        self.rows = [r(2500, "Booking.com 5023617148 / SynXis 92777EF003559")]
        d = self.reply("booking_status", STATUS, ref="Booking.com 5023617148 / SynXis 92777EF003559")
        self.assertTrue(self.mail._meta(d["id"])["sent"])
        self.assertIn("Đã trả lời khách: đã nhận booking", self.tg.sent[-1][0])

    def test_booking_status_not_on_the_sheet_or_cancelled_or_agency_is_refused(self):
        with self.assertRaises(emi.Refused):
            self.reply("booking_status", STATUS, ref="Booking.com 5023617148")
        with self.assertRaises(emi.Refused):
            self.reply("booking_status", STATUS, ref="")
        self.rows = [r(1, "X1"), r(2, "X1", action="CANCEL", at="21/11/2026 08:00"), r(3, "TA9", channel="TA")]
        for ref in ("X1", "TA9"):
            with self.assertRaises(emi.Refused):
                self.reply("booking_status", STATUS, ref=ref)

    def test_cancellation_with_its_cancel_rows_is_sent_and_the_confirmation_goes(self):
        self.rows = [r(2400, "2817840", channel="TA")]
        conf = self.reply("confirmation", "Dear Liana,\n\nThank you for choosing HAYA.\n\nBest regards", ref="2817840")
        conf_n = str(self.st.data["next_review"] - 1)
        self.rows.append(r(2410, "2817840", action="CANCEL", channel="TA", at="21/11/2026 06:04"))
        d = self.reply("cancellation", CANCEL, ref="2817840")
        self.assertTrue(self.mail._meta(d["id"])["sent"])
        self.assertEqual(self.st.data["reviews"][conf_n]["status"], "replaced")
        self.assertIsNone(self.mail.get_draft(conf["id"]))

    def test_cancellation_without_cancel_rows_or_ref_is_held(self):
        self.rows = [r(2400, "2817841", channel="TA")]
        for ref in ("", "2817841"):  # no ref first: one open draft per email or per booking
            d = self.reply("cancellation", CANCEL, ref=ref)
            self.assertFalse(self.mail._meta(d["id"]).get("sent"), ref)
            self.assertEqual(self.last()["status"], emi.REVIEW_OPEN)
            self.assertIn("Chưa tự gửi", self.tg.sent[-1][0])

    def test_pickup_with_both_answers_is_refused(self):
        self.pickup("CHECK", ref="Trip.com 1539369445053786")
        with self.assertRaises(emi.Refused):
            self.reply("pickup", "[CHECK BEFORE SENDING: guest paid not shown, confirm free or paid]\n\n" + BOTH,
                       ref="Trip.com 1539369445053786")


class PickupBothTest(unittest.TestCase):
    def test_the_rule_as_a_condition_is_caught(self):
        # PICKUP_BOTH's \b were backspace characters from c6a2495 to 26/11: this branch never matched
        with self.assertRaises(emi.Refused):
            emi.check_pickup_one_answer("If your booking total is above USD 250, the transfer is free; "
                                        "otherwise it is 200,000 VND.")
        emi.check_pickup_one_answer("Your airport pick-up is complimentary. The driver will wait at arrivals.")


class NoReplyTest(unittest.TestCase):
    def test_a_no_reply_recipient_is_never_auto_sent(self):
        self.assertIn("no-reply", auto_send_refusal("cancellation", ["noreply@mgbedbank.com"], [], [], "Dear"))
        self.assertIn("no-reply", auto_send_refusal("cancellation", ["a@x.com"], ["no-reply@agoda.com"], [], "Dear"))
        self.assertEqual(auto_send_refusal("booking_status", ["5023617148-d8pb@guest.booking.com"], [], [], "Dear"), "")


if __name__ == "__main__":
    unittest.main()
