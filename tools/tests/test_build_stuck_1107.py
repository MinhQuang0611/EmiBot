"""Dev 07/11: rows on the sheet, no reply to the agency.

- The build tool stopped (needs_review / error) and wrote why; nobody read it, so no PDF, no confirmation, and the
  agencies chased (Church Travels BKK 10/1, Footprint 031P0127J, Pegas 11124455, Odeon 8649178).
- A name change built in EZFOLIO never got its reply: job 2 only knew dates, rooms and totals (Ohmyhotel #27984,
  Mekong MVN29835), and the Ohmyhotel rows had the group code as their ref.
- That name change carried a provisional TA-card rate, and the build tool wrote it into EZFOLIO.
"""
import os
import unittest
from datetime import date, datetime, timedelta, timezone

from tools import build_watch, emi, payments
from tools.state import State

VN = timezone(timedelta(hours=7))
NOW = datetime(2026, 11, 7, 9, 0, tzinfo=VN)
MAILBOX = "sales@haya-hotels.com"


def r(n, **kw):
    base = {"_row": n, "action": "NEW", "received_at": "06/11/2026 15:30", "channel_type": "TA",
            "company": "The Church Travels", "booking_ref": "BKK 10/1", "arrival": "10/01/2027",
            "departure": "16/01/2027", "room_code": "TPL", "rooms": "2", "total_vnd": "33120000",
            "source_email": "BKK 10/1"}
    return {**base, **kw}


class StuckTest(unittest.TestCase):
    def stuck(self, rows, now=NOW):
        return build_watch.stuck(rows, emi.booking_state, now)

    def test_build_tool_error_is_listed_with_its_reason(self):
        rows = [r(1623, room_code="SUP-DBL", ez_status="error", ez_error="không đủ 2 phòng (TPL còn 0, QPL còn 0)",
                  ez_processed_at="2026-11-07T05:45:17"), r(1624, ez_status="error", ez_error="không đủ 2 phòng")]
        [i] = self.stuck(rows)
        self.assertEqual((i["kind"], i["rows"]), ("stuck", [1623, 1624]))
        self.assertIn("QPL còn 0", i["note"])
        self.assertIn("STUCK | TA | The Church Travels | ref BKK 10/1", build_watch.render([i]))

    def test_a_later_built_email_replaces_the_stop(self):
        rows = [r(1, ez_status="needs_review", ez_note="cần người"),
                r(2, action="CHANGE", received_at="07/11/2026 08:00", ez_status="done", pdf_link="x")]
        self.assertEqual(self.stuck(rows), [])

    def test_not_picked_up_after_four_hours(self):
        rows = [r(1, received_at="07/11/2026 04:30")]
        self.assertEqual(self.stuck(rows, NOW)[0]["kind"], "waiting")
        self.assertEqual(self.stuck(rows, datetime(2026, 11, 7, 8, 0, tzinfo=VN)), [])

    def test_left_out(self):
        for rows in ([r(1, received_at="05/10/2026 13:37")],  # before the build tool: never its row
                     [r(1, ez_status="needs_review", ez_note="agent: quản lý đã từ chối kế hoạch của agent")],
                     [r(1, ez_status="needs_review", arrival="01/11/2026")],
                     [r(1, action="EXISTING BOOKING", ez_status="needs_review")],
                     [r(1, ez_status="done", pdf_link="x")]):
            self.assertEqual(self.stuck(rows), [], rows)

    def test_a_stuck_cancellation_counts(self):
        rows = [r(1595, action="CANCEL", ez_status="needs_review", ez_note="chờ quản lý duyệt trên web")]
        self.assertEqual(self.stuck(rows)[0]["action"], "CANCEL")


class FakeTg:
    def __init__(self):
        self.sent = []

    def send(self, text, buttons=None):
        self.sent.append(text)
        return len(self.sent)


class FakeMail:
    def search(self, text, top=10):
        return [{"id": "ours", "from": {"emailAddress": {"address": MAILBOX}}},
                {"id": "agency-mail", "from": {"emailAddress": {"address": "info@thechurchtravels.com"}}}]


class AlertTest(unittest.TestCase):
    ROWS = [r(1624, ez_status="error", ez_error="TPL còn 0", ez_processed_at="2026-11-07T05:45:20")]

    def test_once_per_stop_as_a_question_on_the_agency_email(self):
        st, tg = State(os.devnull + "-none"), FakeTg()
        items = build_watch.stuck(self.ROWS, emi.booking_state, NOW)
        self.assertEqual(len(build_watch.alert(st, tg, FakeMail(), items, MAILBOX, out=lambda *_: None)), 1)
        [(qid, q)] = st.open_questions().items()
        self.assertEqual((q["message_id"], q["booking_ref"]), ("agency-mail", "BKK 10/1"))
        self.assertIn(qid, tg.sent[0])
        self.assertIn("TPL còn 0", tg.sent[0])
        self.assertEqual(build_watch.alert(st, tg, FakeMail(), items, MAILBOX, out=lambda *_: None), [])
        self.assertEqual(len(tg.sent), 1)

    def test_the_build_tool_stopping_again_is_a_new_stop(self):
        st, tg = State(os.devnull + "-none"), FakeTg()
        build_watch.alert(st, tg, FakeMail(), build_watch.stuck(self.ROWS, emi.booking_state, NOW), MAILBOX,
                          out=lambda *_: None)
        again = [dict(self.ROWS[0], ez_processed_at="2026-11-07T10:00:00")]
        items = build_watch.stuck(again, emi.booking_state, NOW)
        self.assertEqual(len(build_watch.alert(st, tg, FakeMail(), items, MAILBOX, out=lambda *_: None)), 1)

    def test_no_second_question_when_one_is_open(self):
        # Footprint 06/11: E-297 was asked from job 1 when the agency chased
        st, tg = State(os.devnull + "-none"), FakeTg()
        qid = st.ask("031P0127J", "đổi ngày dừng ở EZFOLIO", "m1")
        rows = [r(1177, booking_ref="031P0127J", ez_status="needs_review", ez_note="Hết phòng TPL đêm 13/01")]
        build_watch.alert(st, tg, FakeMail(), build_watch.stuck(rows, emi.booking_state, NOW), MAILBOX,
                          out=lambda *_: None)
        self.assertEqual(list(st.open_questions()), [qid])
        self.assertIn(f"{qid}</b> (đã hỏi", tg.sent[0])

    def test_telegram_off_records_nothing(self):
        st = State(os.devnull + "-none")
        items = build_watch.stuck(self.ROWS, emi.booking_state, NOW)
        self.assertEqual(build_watch.alert(st, None, FakeMail(), items, MAILBOX, out=lambda *_: None), [])
        self.assertEqual((st.data.get("build_alerts"), st.open_questions()), ({}, {}))


def c(n, **kw):
    base = {"_row": n, "action": "NEW", "received_at": "02/11/2026 10:00", "channel_type": "TA", "company": "Mekong",
            "booking_ref": "MVN29835", "ezfolio_group_code": "28632", "arrival": "18/11/2026",
            "departure": "21/11/2026", "room_code": "DLX-SV", "rooms": "3", "adults": "6", "meal_plan": "BB",
            "total_vnd": "18000000", "guest_names": "SAGARIKA; other guests TBA", "pdf_link": "https://drive/x",
            "source_email": "Hold/MVN29835", "company_email": "contract.vn@mekongvacations.com"}
    return {**base, **kw}


BUILT = dict(action="CHANGE", received_at="06/11/2026 11:34", ez_status="done",
             ez_processed_at="2026-11-06T12:32:36+07:00")


class NoMail:
    def search(self, text, top=10):
        return []


class NameChangeTest(unittest.TestCase):
    def due(self, rows):
        return payments.needs_confirmation(rows, emi.booking_state, emi._parts, NoMail(), State(os.devnull + "-none"),
                                           MAILBOX, date(2026, 11, 7))

    def test_a_built_name_change_is_owed_its_confirmation(self):
        rows = [c(5), c(1610, guest_names="MR RAKESH GARG; MRS ALKA GARG", what_changed="Lead guest changed", **BUILT)]
        [i] = [x for x in self.due(rows) if x.get("change") is not None]
        self.assertEqual((i["row"], i["change"]), (1610, "Lead guest changed"))

    def test_names_given_for_tba_or_written_another_way_are_not_a_change(self):
        for before, after in (("TBA", "Mr Rakesh Garg"), ("MR.PERIC/DRAGAN", "Dragan Peric"),
                              ("Lê Văn An", "LE VAN AN; TRAN THI BICH")):
            rows = [c(5, guest_names=before), c(9, guest_names=after, **BUILT)]
            self.assertEqual([x for x in self.due(rows) if x.get("change") is not None], [], (before, after))

    def test_a_payment_email_is_not_a_change(self):
        rows = [c(5), c(9, guest_names="Someone Else", **{**BUILT, "Payment 1": "9000000"})]
        self.assertEqual([x for x in self.due(rows) if x.get("change") is not None], [])

    def test_ota_name_change_asked_by_the_b2b_desk_under_the_group_code(self):
        # Ohmyhotel #27984: booking under its number (row 1436), the name change under the group code (row 1594)
        ota = dict(channel_type="OTA", company="Oh My Hotel", company_email="vnoperation@ohmyhotel.com",
                   arrival="26/11/2026", departure="01/12/2026", room_code="SUP-DBL", rooms="1", adults="2")
        rows = [c(1436, action="EXISTING BOOKING", booking_ref="S26082711291H01", ezfolio_group_code="27984",
                  guest_names="MR.PERIC/DRAGAN", total_vnd="7437500", **ota),
                c(1594, booking_ref="27984", ezfolio_group_code="27984", guest_names="Darinka Kerecki",
                  total_vnd="9500000", what_changed="Guest name DRAGAN PERIC → Darinka Kerecki", **{**BUILT, **ota})]
        [i] = self.due(rows)
        self.assertEqual((i["ref"], i["row"], i["rate_moved"]), ("S26082711291H01", 1594, (7437500, 9500000)))
        self.assertIn("RATE MOVED 7,437,500 → 9,500,000", payments.render_confirmations([i]))

    def test_ota_guest_messages_get_no_confirmation(self):
        ota = dict(channel_type="OTA", company="Booking.com", company_email="x123@guest.booking.com")
        rows = [c(5, **ota), c(9, guest_names="Someone Else", **{**BUILT, **ota})]
        self.assertEqual(self.due(rows), [])


GROUP_COLS = ["ezfolio_group_code", "Group code"]


class KnownRateTest(unittest.TestCase):
    BOOKING = {"_row": 1436, "action": "EXISTING BOOKING", "booking_ref": "S26082711291H01", "Group code": "27984",
               "room_code": "SUP-DBL", "rate_per_night_vnd": "1487500", "notes": "6. Rate/total TBA"}

    def change(self, **kw):
        return {**{"action": "CHANGE", "booking_ref": "27984", "ezfolio_group_code": "27984", "room_code": "SUP-DBL",
                   "rate_per_night_vnd": "1900000", "notes": "6. TA card rate, provisional, no price from Oh My Hotel"},
                **kw}

    def test_provisional_rate_never_replaces_the_bookings_price(self):
        with self.assertRaises(emi.Refused) as e:
            emi.keep_known_rate([self.change()], [self.BOOKING], GROUP_COLS)
        self.assertIn("1,487,500 per night", str(e.exception))

    def test_allowed(self):
        for rec, rows in ((self.change(rate_per_night_vnd="1487500"), [self.BOOKING]),  # the booking's own price
                          (self.change(), []),                                          # no price known anywhere
                          (self.change(notes="6. New price from Oh My Hotel 1,900,000"), [self.BOOKING]),
                          (self.change(room_code="DLX-SV"), [self.BOOKING])):
            emi.keep_known_rate([rec], rows, GROUP_COLS)


class OwnRefTest(unittest.TestCase):
    """Emi wrote the group code as booking_ref on CHANGE / CANCEL rows (1594, 1595, 1611, 1614, 1615, 1617-1619,
    1641); the build tool matches by booking_ref and stopped."""
    AMARA = {"_row": 446, "action": "NEW", "booking_ref": "AMARA 14-16/12 (no agency code)",
             "ezfolio_group_code": "30124", "room_code": "STD"}

    def test_the_group_code_becomes_the_bookings_ref(self):
        rec = {"action": "CHANGE", "booking_ref": "30124", "room_code": "SUP-TWN"}
        self.assertEqual(emi.own_ref(rec, [self.AMARA], GROUP_COLS, out=lambda *_: None),
                         "AMARA 14-16/12 (no agency code)")
        self.assertEqual((rec["booking_ref"], rec["ezfolio_group_code"], rec["Group code"]),
                         ("AMARA 14-16/12 (no agency code)", "30124", "30124"))

    def test_a_number_from_the_build_tools_reconciliation(self):
        existing = {"_row": 1462, "action": "EXISTING BOOKING", "booking_ref": "V26090710084H01",
                    "Group code": "28286"}
        rec = {"action": "CANCEL", "booking_ref": "28286", "Group code": "28286"}
        self.assertEqual(emi.own_ref(rec, [existing], GROUP_COLS, out=lambda *_: None), "V26090710084H01")

    def test_left_alone(self):
        only_code = {"_row": 1500, "action": "EXISTING BOOKING", "booking_ref": "29287", "Group code": "29287"}
        for rec, rows in (({"action": "CHANGE", "booking_ref": "29287"}, [only_code]),  # the code is all there is
                          ({"action": "NEW", "booking_ref": "30124"}, [self.AMARA]),
                          ({"action": "CHANGE", "booking_ref": "30124", "Group code": "28000"}, [self.AMARA]),
                          ({"action": "CHANGE", "booking_ref": "AMARA 14-16/12 (no agency code)"}, [self.AMARA])):
            before = rec["booking_ref"]
            self.assertEqual(emi.own_ref(rec, rows, GROUP_COLS, out=lambda *_: None), before, rec)


class RepeatTest(unittest.TestCase):
    """Ohmyhotel S26082711291H01: the same name change written at 06:29 (row 1594) and again at 16:42 (row 1634)."""
    ROW = {"_row": 1594, "action": "CHANGE", "received_at": "06/11/2026 06:29", "booking_ref": "S26082711291H01",
           "guest_names": "Darinka Kerecki", "arrival": "26/11/2026", "departure": "01/12/2026",
           "room_code": "SUP-DBL", "rooms": "1", "adults": "2", "rate_per_night_vnd": "1487500",
           "total_vnd": "7437500"}

    def again(self, **kw):
        return {**{k: v for k, v in self.ROW.items() if k != "_row"}, "received_at": "06/11/2026 16:42",
                "what_changed": "Guest name DRAGAN PERIC → Darinka Kerecki", **kw}

    def test_the_same_change_twice_is_refused(self):
        with self.assertRaises(emi.Refused) as e:
            emi.check_not_a_repeat([self.again(guest_names="DARINKA  kerecki")], [self.ROW])
        self.assertIn("repeats row 1594", str(e.exception))

    def test_the_change_written_into_special_requests_is_still_a_repeat(self):
        first = dict(self.ROW, what_changed="Guest name DRAGAN PERIC → Darinka Kerecki; no price change")
        with self.assertRaises(emi.Refused):
            emi.check_not_a_repeat([self.again(special_requests="Name amendment requested; no price change.",
                                               what_changed="Guest name DRAGAN PERIC → Darinka Kerecki; none")],
                                   [first])

    def test_allowed(self):
        for rec in (self.again(guest_names="Darinka Kerecki; Marko Kerecki"),
                    self.again(special_requests="late check-out"),
                    self.again(what_changed="Payment 1 received 3,718,750"),
                    self.again(**{"Payment 1": "3718750"})):
            emi.check_not_a_repeat([rec], [self.ROW])
        emi.check_not_a_repeat([self.again()], [])


class RowMovedTest(unittest.TestCase):
    def test_a_row_that_now_holds_another_booking_is_refused(self):
        now = {"_row": 1617, "booking_ref": "6734710024", "company": "Booking.com", "Group code": "29201"}
        with self.assertRaises(emi.Refused) as e:
            emi.check_row_is(now, "BKK 10/1", GROUP_COLS)
        self.assertIn("rows were inserted above", str(e.exception))
        for ref in ("6734710024", "29201", None):
            emi.check_row_is(now, ref, GROUP_COLS)


if __name__ == "__main__":
    unittest.main()
