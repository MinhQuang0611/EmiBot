"""Dev, 2026-11-27: "với các mail mà nội dung chỉ có thank you thì không cần reply lại". done takes
'NO REPLY: thanks' only when the email's own text (uniqueBody, no quoted thread) is a plain thank-you: no file,
figure, question, ask or booking matter. Anything more still gets its reply."""
import os
import tempfile
import unittest

from tools import emi
from tools.graph_mail import inbound_thanks_refusal
from tools.state import State


def msg(text, files=False):
    return {"uniqueBody": {"content": text}, "body": {"content": text + "\n\nFrom: sales@haya-hotels.com\nold"},
            "hasAttachments": files, "from": {"emailAddress": {"address": "res1@travelconcierge.vn"}},
            "subject": "RE: Booking confirmation 2825005"}


PLAIN = (
    "Dear HAYA team,\n\nWell received with thanks.\n\nBest regards,\nLan Nguyen\nReservation Executive\n"
    "M: +84 909 123 456 | lan@travelconcierge.vn",
    "Thank you for your confirmation!\n\nLiana Troshyna\nVietnam Travel Concierge\nwww.travelconcierge.vn",
    "Cảm ơn bạn nhiều nhé!",
    "Chào em,\nChị cảm ơn em đã xác nhận.\nTrân trọng,\nHương\nĐT: 0909 000 111",
    "Спасибо!",
    "Noted with thanks.\n\nOn Thu, 27 Nov 2026 at 10:00, HAYA Reservations <sales@haya-hotels.com> wrote:\n> Total 3,400,000 VND?",
)
NOT_ONLY = (
    "Thank you. Please add breakfast for 2 pax.",
    "Thanks! Could you send the invoice?",
    "Thanks, we will pay the deposit tomorrow.",
    "Thank you, the guest arrives on 12/12.",
    "Cảm ơn em, em đổi giúp chị sang phòng Twin nhé.",
    "Please find the rooming list attached.",
    "Received.",
)


class InboundThanksTest(unittest.TestCase):
    def test_plain_thanks(self):
        for text in PLAIN:
            self.assertEqual(inbound_thanks_refusal(msg(text)), "", text)

    def test_more_than_thanks(self):
        for text in NOT_ONLY:
            self.assertNotEqual(inbound_thanks_refusal(msg(text)), "", text)

    def test_files_mean_a_reply(self):
        self.assertIn("files", inbound_thanks_refusal(msg("Thank you!", files=True)))


class DoneTest(unittest.TestCase):
    def setUp(self):
        self.st = State(os.path.join(tempfile.mkdtemp(), "state.json"))

    def done(self, outcome, m):
        emi.check_email_answered(self.st, "m1", outcome, lambda: m, out=lambda *_: None, load_bodies=lambda: m)

    def test_thanks_closed_without_a_reply(self):
        self.done("NO REPLY: thanks", msg(PLAIN[0]))
        self.done("DAY CHECK: NO REPLY: thanks — only says thank you", msg("Thank you!"))

    def test_more_than_thanks_refused(self):
        with self.assertRaisesRegex(emi.Refused, "NOT ONLY THANKS"):
            self.done("NO REPLY: thanks", msg(NOT_ONLY[0]))

    def test_other_emails_still_need_their_reply(self):
        with self.assertRaisesRegex(emi.Refused, "NO REPLY DRAFTED.*NO REPLY: thanks"):
            self.done("read it", msg(NOT_ONLY[1]))


if __name__ == "__main__":
    unittest.main()
