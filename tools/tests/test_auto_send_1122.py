"""Auto-send, dev 2026-11-22, on the reply to Trip.com Lodging Support Center (stop-sale chart thread, "Dear
Sapphire, Thank you for your email. We look forward to welcoming your guests."): "Email đơn giản cảm ơn Khách thì ko
cần phải duyệt. Được auto gửi" → kind thanks, sent at once when it is only the thank-you of email-templates.md 9."""
import unittest

from tools import emi
from tools.graph_mail import thanks_refusal
from tools.tests.test_auto_send_1119 import ALL, AutoSendTest as Base

SIGN = "\n\nBest regards,\nReservations Team\nHAYA Hotel Phu Quoc, Trademark Collection by Wyndham\nsales@haya-hotels.com"
SAPPHIRE = "Dear Sapphire,\n\nThank you for your email. We look forward to welcoming your guests." + SIGN
VI = ("Kính gửi anh/chị,\n\nKhách sạn đã nhận được, xin cảm ơn anh/chị.\n\nTrân trọng,\nReservations Team\n"
      "HAYA Hotel Phu Quoc, Trademark Collection by Wyndham\nsales@haya-hotels.com")
NOT_SIMPLE = [
    "Dear Sapphire,\n\nThank you. We look forward to welcoming your guests on 29/11/2026." + SIGN,
    "Dear Sapphire,\n\nThank you for your email. Could you please send the rooming list?" + SIGN,
    "Dear Sapphire,\n\nThank you. We can offer a 10% discount next time." + SIGN,
    "Dear Sapphire,\n\nThank you. We confirm the booking for your guests." + SIGN,
    "Dear Sapphire,\n\nThank you. Please send the payment slip for the deposit." + SIGN,
    "Dear Sapphire,\n\nWe look forward to welcoming your guests." + SIGN,  # no thank-you in it
]


class AutoSend1122Test(Base):
    def setUp(self):
        super().setUp()
        self.env(ALL + ",thanks")

    def test_the_plain_thank_you_is_sent(self):
        for text in (SAPPHIRE, VI):
            with self.subTest(text=text[:20]):
                self.setUp()
                d = self.reply("thanks", text, ref="", row_="")
                self.assertTrue(self.mail._meta(d["id"])["sent"])
                self.assertEqual(self.last()["status"], "sent")
                self.assertIn("Đã gửi thư cảm ơn", self.tg.sent[-1][0])

    def test_more_than_a_thank_you_is_refused(self):
        for text in NOT_SIMPLE:
            with self.subTest(text=text[:60]):
                with self.assertRaises(emi.Refused):
                    self.reply("thanks", text, ref="", row_="")

    def test_not_named_in_the_flag_stays_a_draft(self):
        self.env(ALL)
        d = self.reply("thanks", SAPPHIRE, ref="", row_="")
        self.assertFalse(self.mail._meta(d["id"]).get("sent"))
        self.assertEqual(self.last()["status"], emi.REVIEW_OPEN)

    def test_a_check_line_holds_it(self):
        d = self.reply("thanks", "[CHECK BEFORE SENDING: is this the right thread]\n\n" + SAPPHIRE, ref="", row_="")
        self.assertFalse(self.mail._meta(d["id"]).get("sent"))
        self.assertIn("Chưa tự gửi", self.tg.sent[-1][0])


class ThanksTextTest(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(thanks_refusal(SAPPHIRE), "")
        self.assertEqual(thanks_refusal(VI), "")
        self.assertEqual(thanks_refusal("Dear Ms. Lan,\n\nThank you, we appreciate it.\n\nBest,\nReservations Team"), "")

    def test_too_long(self):
        long = "Dear Sir,\n\nThank you for your email. " + "We look forward to welcoming your guests. " * 8 + SIGN
        self.assertIn("line or two", thanks_refusal(long))


if __name__ == "__main__":
    unittest.main()
