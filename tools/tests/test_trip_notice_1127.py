"""An OTA robot's booking notice is known in any language (dev, 2026-11-27, Trip.com 1359049748321348).

"Trip.com - Thông báo đơn đặt mới: 1359049748321348" from auto_reservation@trip.com matched no English subject word and
its sender wasn't named no-reply, so ota-note refused it and the model answered with draft-reply --kind reply to the
robot. A reply kind is never auto-sent, so it sat in Drafts. The dev: "regex thế này dễ sót lắm". Now: a robot (by
name or by the Auto-Submitted header) mailing a booking number is a notice whatever the words, unless it is money or a
report; and draft-reply refuses an OTA robot's notice even with --to, so a miss can't end in a stuck draft."""
import unittest
from types import SimpleNamespace

from tools import emi
from tools.graph_mail import auto_send_refusal
from tools.tests.test_ota_note_1114 import Base, Mail

TRIP = "auto_reservation@trip.com"
NEW = "Trip.com - Thông báo đơn đặt mới: 1359049748321348"
ROW = {"_row": 2801, "action": "NEW", "booking_ref": "Trip.com 1359049748321348", "guest_names": "NGUYEN VAN A",
       "arrival": "05/12/2026", "departure": "07/12/2026", "rooms": "1", "room_code": "DLX-SV",
       "channel_type": "OTA", "company": "Trip.com"}
AUTO = {"Auto-Submitted": "auto-generated"}


class Sheet:
    def rows(self):
        return [dict(ROW)]


class HeaderMail(Mail):
    def __init__(self, messages, headers=None):
        super().__init__(messages)
        self.headers = headers or {}

    def message_headers(self, mid):
        return self.headers.get(mid, {})


class ClassifyTest(unittest.TestCase):
    def test_trip_subjects_with_their_action(self):
        for subject, action in ((NEW, "NEW"), ("Trip.com - Thông báo hủy đơn: 1359049748321348", "CANCEL"),
                                ("Trip.com - Thông báo thay đổi đơn: 1359049748321348", "CHANGE"),
                                ("Trip.com - Thong bao don dat moi: 1359049748321348", "NEW")):
            self.assertTrue(emi.is_ota_robot_notice(TRIP, subject), subject)
            self.assertEqual(emi.notice_action(subject), action)

    def test_any_language_by_the_booking_number_from_a_robot(self):
        for subject in ("Новое бронирование 1359049748321348", "신규 예약 1359049748321348",
                        "新订单 1359049748321348", "Pemesanan baru 1359049748321348",
                        "Trip.com 1359049748321348"):  # no words at all: the number from a robot is enough
            self.assertTrue(emi.is_ota_robot_notice(TRIP, subject), subject)

    def test_a_robot_by_header_only(self):
        sender = "reservations@agoda.com"  # not named as a robot
        self.assertFalse(emi.is_ota_robot_notice(sender, "1359049748321348"))
        self.assertTrue(emi.is_ota_robot_notice(sender, "1359049748321348", AUTO))
        self.assertFalse(emi.is_ota_robot(sender, {"Auto-Submitted": "auto-replied"}))  # an out-of-office

    def test_money_and_reports_from_a_robot_are_not_notices(self):
        for subject in ("Agoda Remittance Advice 20261127001", "Payout 1359049748321348",
                        "Hoá đơn tháng 11 - 2026110001", "Thông báo thanh toán 1359049748321348",
                        "Monthly performance report 202611"):
            self.assertFalse(emi.is_ota_notice("no-reply@agoda.com", subject), subject)

    def test_people_and_guests_are_not_robots(self):
        self.assertFalse(emi.is_ota_notice("abc@guest.trip.com", NEW))
        self.assertFalse(emi.is_ota_robot("lodgingsupport@trip.com"))
        self.assertFalse(emi.is_ota_robot_notice("khoi.duong@trip.com", "Câu hỏi về đơn đặt 1359049748321348"))
        self.assertFalse(emi.is_ota_notice("lodgingsupport@trip.com", "RE: Stop Sale / Sold Out Room Type Chart"))

    def test_mg_and_tiket_robots(self):
        self.assertTrue(emi.is_ota_robot_notice("noreply@mgbedbank.com", "AGIN0116572611657606 / HB2611488385"))
        self.assertTrue(emi.is_ota_robot_notice("no-reply@tiket.com", "Pesanan baru 80887501"))


class ReplyTest(Base):
    def args(self, **kw):
        return SimpleNamespace(message_id="m1", to="", cc="", internal=False, all=False, **kw)

    def test_draft_reply_is_refused(self):
        mail = HeaderMail({"m1": (TRIP, NEW, "", "2026-11-27T10:00:00Z")})
        with self.assertRaisesRegex(emi.Refused, "OTA NOTICE"):
            emi.reply_recipients(mail, self.args(), "reply")

    def test_refused_with_an_address_given_by_hand_too(self):
        mail = HeaderMail({"m1": (TRIP, NEW, "", "2026-11-27T10:00:00Z")})
        args = self.args()
        args.to = "auto_reservation@trip.com"
        with self.assertRaisesRegex(emi.Refused, "OTA NOTICE"):
            emi.reply_recipients(mail, args, "thanks")

    def test_refused_for_a_robot_known_by_its_header(self):
        mail = HeaderMail({"m1": ("reservations@agoda.com", "1359049748321348", "", "2026-11-27T10:00:00Z")},
                          headers={"m1": AUTO})
        with self.assertRaisesRegex(emi.Refused, "OTA NOTICE"):
            emi.reply_recipients(mail, self.args(), "reply")

    def test_a_person_at_the_ota_still_gets_a_reply(self):
        mail = HeaderMail({"m1": ("lodgingsupport@trip.com", "Guest request 1359049748321348", "", "2026")})
        self.assertEqual(emi.reply_recipients(mail, self.args(), "reply"), (None, None))

    def test_ota_note_goes_to_front_office_and_is_auto_sendable(self):
        mail = HeaderMail({"m1": (TRIP, NEW, "", "2026-11-27T10:00:00Z")})
        emi.ota_note(mail, Sheet(), self.st, SimpleNamespace(message_id="m1", ref="Trip.com 1359049748321348",
                                                              replaces=""), out=self.lines.append)
        (d,) = mail.drafts.values()
        self.assertEqual(d["to"], [emi.FRONT_OFFICE])
        self.assertIn("dòng 2801", d["text"])
        self.assertEqual(auto_send_refusal("ota_note", d["to"], [], [], d["text"]), "")

    def test_done_wants_the_note(self):
        msg = {"from": {"emailAddress": {"address": TRIP}}, "subject": NEW}
        with self.assertRaisesRegex(emi.Refused, "NO OTA NOTE"):
            emi.check_email_answered(self.st, "m1", "NEW rows 2801", lambda: msg, out=self.lines.append)

    def test_done_wants_the_note_for_a_robot_known_by_its_header(self):
        msg = {"from": {"emailAddress": {"address": "reservations@agoda.com"}}, "subject": "1359049748321348"}
        with self.assertRaisesRegex(emi.Refused, "NO OTA NOTE"):
            emi.check_email_answered(self.st, "m1", "NEW rows 2801", lambda: msg, out=self.lines.append,
                                     load_headers=lambda: AUTO)


if __name__ == "__main__":
    unittest.main()
