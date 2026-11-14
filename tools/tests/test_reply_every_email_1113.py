"""Every email gets its reply, a no-reply sender too (dev, 2026-11-13).

10/11 16:38–16:39: three SynXis notices for Trip.com 1653718335673330 (JAMIL HUSSAIN, 13–15/11, 92777EF003348–3350)
went to Karen as E-377/378/379 "không nêu quốc tịch; cần xác nhận quốc tịch trước khi ghi row", were marked done with
"no row written", nobody answered, and the booking reached the sheet on 12/11 only because Karen saw it. The dev:
"TẤT CẢ CÁC EMAIL ĐỀU PHẢI CÓ REPLY HẾT NHÉ. Ghi noreply thì vẫn phải reply" — to the email printed in the booking,
the confirmation with the PDF; no reply only for spam, OTP, machine alerts, internal and Palma mail."""
import os
import unittest
from datetime import date
from types import SimpleNamespace

from tools import emi, payments
from tools import intake_schema as schema
from tools.tests.test_intake_consistency import check, has
from tools.state import State
from tools.tests.test_payments import MAILBOX, FakeMail, row

SYNXIS = "NOREPLYWyndhamReservations@synxis.com"
NOTICE_3350 = """The following reservation has been brought to you by Wyndham Hotels and Resorts, booked through SynXis CRS.
Confirmation Number/Cancellation Number: 92777EF003350 /
Reservation Status: Confirmed
Arrival : Friday, November 13, 2026
Corp Name: CTrip - Trip.com Collect
Total Cost with Tax: VND 3,719,250.00
Last Name : HUSSAIN
First Name : JAMIL
Country :
Email : lodgingsupport@trip.com
"""
SUBJECT = "SynXis Res Confirmed (92777EF003350 )"


class Mail:
    def __init__(self, sender, body="", subject=SUBJECT):
        self.msg = {"from": {"emailAddress": {"address": sender}}, "subject": subject,
                    "body": {"content": body}}

    def get_message_text(self, message_id):
        return self.msg


def recipients(sender, body="", **kw):
    args = SimpleNamespace(message_id="m1", to="", cc="", internal=False, all=False, **kw)
    return emi.reply_recipients(Mail(sender, body), args, "confirmation")


class NoReplySenderTest(unittest.TestCase):
    def test_no_reply_addresses(self):
        for a in (SYNXIS, "noreply@agoda.com", "no-reply@booking.com", "do-not-reply@expedia.com",
                  "DoNotReply@trip.com", "hotel.noreply@traveloka.com"):
            self.assertTrue(emi.is_no_reply(a), a)
        for a in ("lodgingsupport@trip.com", "reply.desk@agency.vn", "sales@haya-hotels.com", ""):
            self.assertFalse(emi.is_no_reply(a), a)

    def test_the_email_printed_in_the_booking(self):
        self.assertEqual(emi.booking_email(NOTICE_3350), "lodgingsupport@trip.com")
        # ours and other robots are skipped
        self.assertEqual(emi.booking_email("Email: sales@haya-hotels.com\nE-mail : noreply@x.com\nEmail: g@x.com"),
                         "g@x.com")
        self.assertEqual(emi.booking_email("Email :\nCity :"), "")

    def test_a_synxis_notice_now_gets_only_the_intake_note(self):
        # Karen 14/11 replaced this day's rule: no reply to the booking email, ota-note on the SynXis thread
        for body in (NOTICE_3350, "Last Name : HUSSAIN\nEmail :\n"):
            with self.assertRaises(emi.Refused) as e:
                recipients(SYNXIS, body)
            self.assertIn("ota-note", str(e.exception))

    def test_another_robot_is_answered_to_the_booking_email(self):
        self.assertEqual(recipients("noreply@hotelnotice.example", NOTICE_3350), (["lodgingsupport@trip.com"], []))
        self.assertEqual(recipients("noreply@hotelnotice.example", "Email :\n"), (None, None))

    def test_an_agency_is_answered_as_before(self):
        self.assertEqual(recipients("res@agency.vn", "Email: other@x.com"), (None, None))

    def test_tour_operator_robots_keep_their_desk(self):
        to, _ = recipients("vn.robot@ms.anextour.com", "Email: guest@x.com")
        self.assertEqual(to, ["reservation@anexvietnam.com"])


class NationalityIsNoQuestionTest(unittest.TestCase):
    def ask(self, q):
        st = State(os.devnull + "-none")
        return emi.ask_karen(st, None, "m1", q, ref="SynXis 92777EF003350 (Trip.com)", out=lambda *_: None)

    def test_the_10_11_question_is_refused(self):
        for q in ("Booking Trip.com/SynXis 92777EF003350 không nêu quốc tịch; cần xác nhận quốc tịch trước khi ghi row.",
                  "Thiếu quốc tịch khách JAMIL HUSSAIN, ghi gì?", "Nationality missing for 92777EF003350",
                  "The notice has no nationality: which one?"):
            with self.assertRaises(emi.Refused, msg=q) as e:
                self.ask(q)
            self.assertIn("THIẾU: Country", str(e.exception))
            self.assertNotIn("Pakistan", str(e.exception))

    def test_other_questions_still_go(self):
        self.assertEqual(self.ask("Khách Ấn Độ: đại lý báo giá chưa có +20%, nhận giá nào?"), "E-001")


class MissingGoesToColumnAJTest(unittest.TestCase):
    """Dev, 13/11 on row 1937: the row is written all the same and what is missing is listed in column AJ
    (transfer), never guessed (no nationality from the name) and never in missing_info, which stops the build."""

    def test_blank_nationality_with_the_aj_line_passes(self):
        errors, _ = check(nationality="", guest_names="JAMIL HUSSAIN", transfer="THIẾU: Country")
        self.assertFalse(has(errors, "nationality"), errors)

    def test_aj_line_under_pickup_details(self):
        transfer = "Complimentary airport pick-up, one way; flight 9G702 arriving 14:35\nTHIẾU: Country; Số WhatsApp; SL vali"
        self.assertEqual(schema.missing_listed(transfer), ["country", "số whatsapp", "sl vali"])
        errors, _ = check(nationality="", guest_names="JAMIL HUSSAIN", transfer=transfer)
        self.assertFalse(has(errors, "nationality"), errors)

    def test_blank_nationality_without_it_is_refused(self):
        errors, _ = check(nationality="", guest_names="JAMIL HUSSAIN")
        self.assertTrue(has(errors, "nationality: never blank"), errors)
        self.assertTrue(any("THIẾU: Country" in e for e in errors))

    def test_vietnam_as_a_guess_points_to_aj(self):
        errors, _ = check(nationality="Vietnam", guest_names="JAMIL HUSSAIN")
        self.assertTrue(any(e.startswith("nationality: Vietnam") and "THIẾU: Country" in e for e in errors), errors)

    def test_soft_gaps_never_in_missing_info(self):
        for note in ("nationality not given", "quốc tịch", "WhatsApp number", "flight details", "số vali"):
            errors, _ = check(missing_info=note)
            self.assertTrue(has(errors, "missing_info:"), note)
        errors, _ = check(missing_info="REQUIRED blank: rate_per_night_vnd – no rate in the email")
        self.assertFalse(any("transfer (column AJ)" in e for e in errors), errors)

    def test_an_empty_aj_line_is_refused(self):
        errors, _ = check(transfer="THIẾU:   ")
        self.assertTrue(has(errors, "transfer: 'THIẾU:'"), errors)


class DoneNeedsAReplyTest(unittest.TestCase):
    def setUp(self):
        self.st = State(os.devnull + "-none")
        self.lines = []

    def check(self, outcome, sender=SYNXIS, subject=SUBJECT, mid="m1"):
        msg = Mail(sender, NOTICE_3350, subject).msg
        emi.check_email_answered(self.st, mid, outcome, lambda: msg, out=self.lines.append)

    def test_the_10_11_outcome_is_refused(self):
        self.st.ask("SynXis 92777EF003350 (Trip.com)", "quốc tịch?", "m1")
        with self.assertRaises(emi.Refused) as e:
            self.check("Trip.com/SynXis 92777EF003350 waits on Karen E-377: nationality absent; no row written")
        self.assertIn("OTA BOOKING WITHOUT A ROW", str(e.exception))

    def test_an_ota_notice_never_waits_on_karen(self):
        self.st.ask("SynXis 92777EF003350 (Trip.com)", "something", "m1")
        with self.assertRaises(emi.Refused) as e:
            self.check("waits on Karen E-001")
        self.assertIn("NO OTA NOTE", str(e.exception))

    def test_rows_and_the_note_pass(self):  # Karen 14/11: the intake note, not a confirmation (test_ota_note_1114)
        self.st.data["reviews"]["760"] = {"draft_id": "d1", "status": "open", "source": "m1", "kind": "ota_note"}
        self.check("NEW row 1937 Trip.com 1653718335673330 / SynXis 92777EF003350; note #760")

    def test_rows_without_a_draft_are_refused(self):
        with self.assertRaises(emi.Refused) as e:
            self.check("NEW row 1937 Trip.com 1653718335673330 / SynXis 92777EF003350")
        self.assertIn("NO OTA NOTE", str(e.exception))

    def test_the_other_email_of_the_same_booking_names_its_draft(self):
        self.st.data["reviews"]["760"] = {"draft_id": "d1", "status": "open", "source": "agoda-mail", "kind": "ota_note"}
        self.check("SynXis copy of Agoda 1783017402, row 1937; same booking as #760")
        with self.assertRaises(emi.Refused):
            self.check("SynXis copy, same booking as #999")  # no such draft

    def test_the_four_exceptions_and_staff_answers(self):
        for outcome in ("NO REPLY: spam (newsletter)", "NO REPLY: OTP SynXis passcode", "NO REPLY: alert Daikin 502",
                        "NO REPLY: internal chatter", "NO REPLY: Palma, forwarded #712",
                        "ANSWERED BY STAFF 12/11 10:02 (Sent Items)"):
            self.check(outcome, sender="x@y.com", subject="whatever")
        with self.assertRaises(emi.Refused):
            self.check("NO REPLY: the guest didn't ask anything", sender="guest@gmail.com", subject="Hello")

    def test_on_request_may_wait_on_karen(self):
        self.st.ask("Pegas 11131133", "QPL on request: nhận không?", "m2")
        self.check("Pegas 11131133 on request, waits on Karen E-001", sender="pegasys-notifications@pegast.su",
                   subject="New booking 11131133", mid="m2")

    def test_a_guest_writing_through_booking_com_is_not_an_ota_notice(self):
        self.assertFalse(emi.is_ota_notice("123-abc@guest.booking.com", "Booking 5859857089: a message"))
        self.assertTrue(emi.is_ota_notice(SYNXIS, SUBJECT))
        self.assertTrue(emi.is_ota_notice("noreply@agoda.com", "Agoda Booking ID 1783017402 - CONFIRMED"))
        self.assertFalse(emi.is_ota_notice("noreply@synxis.com", "Your one-time passcode"))

    def test_unreadable_email_is_a_gap_not_a_pass(self):
        def boom():
            raise RuntimeError("401 token")
        with self.assertRaises(emi.Refused):
            emi.check_email_answered(self.st, "m1", "row 1937", boom, out=self.lines.append)
        self.assertTrue(any(x.startswith("GAP:") for x in self.lines))


ROW_1937 = {"channel_type": "OTA", "company": "Trip.com", "booking_ref": "Trip.com 1653718335673330 / SynXis 92777EF003350",
            "total_vnd": "3347324", "rate_per_night_vnd": "1859625", "Average rate per night after discount": "1673662",
            "ezfolio_group_code": "31065"}
GOOD = """Dear Trip.com team,

Thank you for your booking with HAYA Hotel Phu Quoc, Trademark Collection by Wyndham. Please find the confirmation below and the PDF attached.

Group code: #31065
Booking reference: Trip.com 1653718335673330 / SynXis 92777EF003350
Guest name: JAMIL HUSSAIN
Stay: 13/11/2026 – 15/11/2026 (2 nights)
Room: 1 Standard Garden View, 2 adults, breakfast included
Payment: prepaid through Trip.com
Cancellation: non-refundable

Best regards,
Reservations Team
HAYA Hotel Phu Quoc, Trademark Collection by Wyndham
sales@haya-hotels.com"""


class OtaConfirmationTextTest(unittest.TestCase):
    def test_the_form_passes(self):
        emi.confirmation_check(ROW_1937)(GOOD)

    def test_no_bank_block_no_deposit(self):
        with self.assertRaises(emi.Refused):
            emi.confirmation_check(ROW_1937)(GOOD + "\nAccount number: 1020729617")
        with self.assertRaises(emi.Refused):
            emi.confirmation_check(ROW_1937)(GOOD.replace("Payment: prepaid", "50% deposit by 15/11, prepaid"))

    def test_never_the_net_figure(self):
        for amount in ("3,347,324", "3.347.324", "1,859,625", "1,673,662"):
            with self.assertRaises(emi.Refused, msg=amount) as e:
                emi.confirmation_check(ROW_1937)(GOOD.replace("Payment: prepaid", f"Total: VND {amount}, prepaid"))
            self.assertIn("net", str(e.exception))

    def test_the_booking_number_and_the_sign_off(self):
        with self.assertRaises(emi.Refused):
            emi.confirmation_check(ROW_1937)(GOOD.replace("Trip.com 1653718335673330 / SynXis 92777EF003350", "—"))
        with self.assertRaises(emi.Refused):
            emi.confirmation_check(ROW_1937)(GOOD.replace("Reservations Team", "HAYA"))

    def test_an_agency_keeps_its_own_check(self):
        with self.assertRaises(emi.Refused):
            emi.confirmation_check({**ROW_1937, "channel_type": "TA"})(GOOD)


def ota(n, received, **kw):
    return row(n, **{**dict(channel_type="OTA", company="Trip.com", booking_ref=f"SynXis 92777EF00{n} (Trip.com)",
                            ezfolio_group_code=str(31000 + n), received_at=received, arrival="20/11/2026",
                            departure="22/11/2026", total_vnd="3347324", COD="N/A (OTA prepaid by VCC)",
                            ez_status="done", ez_processed_at="2026-11-13T10:00:00"), **kw})


def owed(rows, st=None):
    st = st or State(os.devnull + "-none")
    return payments.needs_confirmation(rows, emi.booking_state, emi._parts, FakeMail(code="none"), st, MAILBOX,
                                       date(2026, 11, 13))


class OtaConfirmationOwedTest(unittest.TestCase):
    def test_an_ota_booking_is_owed_no_confirmation_any_more(self):  # Karen 14/11: the intake note only
        self.assertEqual(owed([ota(3400, "13/11/2026 09:00")]), [])

    def test_older_ota_bookings_are_not_chased_back(self):
        self.assertEqual(owed([ota(3350, "10/11/2026 16:38")]), [])

    def test_an_ota_change_is_owed_only_when_a_person_asked(self):
        rows = [ota(3401, "13/11/2026 08:00"),
                ota(3402, "13/11/2026 09:00", action="CHANGE", booking_ref="SynXis 92777EF003401 (Trip.com)",
                    ezfolio_group_code="34401", departure="23/11/2026", total_vnd="5020986",
                    what_changed="Departure 22/11 → 23/11", company_email=SYNXIS)]
        rows[0]["ezfolio_group_code"] = "34401"
        self.assertEqual(owed(rows), [])  # the SynXis modification itself: its intake note only
        rows[1]["company_email"] = "ops@trip-agent.example"  # a person at the agency asked: still confirmed
        self.assertEqual([i.get("change") for i in owed(rows)], ["Departure 22/11 → 23/11"])


if __name__ == "__main__":
    unittest.main()
