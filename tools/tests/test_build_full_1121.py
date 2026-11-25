"""Dev 21/11, on E-638 (MG AGIN0116572611657606 / HB2611488385, row 2516): "với các case mà hết phòng thì từ chối luôn
chứ". The build tool found no room in EZFOLIO for 21–27/12 (DLX-SV 0, SUITE-SV 0, nothing free the whole stay) and Emi
asked Karen every 45 minutes. A new booking with no room at all is declined at once: CANCEL rows + the decline draft,
no question, and an open question about it is closed. A partial fit or a change still goes to Karen.

Dev 25/11 (Booking.com 5349803632 / SynXis 92777EF003597, live row 2572): never an OTA or B2B booking — MG included.
Emi wrote CANCEL "No availability" with no cancellation email and the guest arrived. An OTA booking stays a question;
a CANCEL row only from the OTA's own cancellation email. The fixtures below are a travel agency's booking.
"""
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

from tools import build_watch, emi
from tools.state import State

VN = timezone(timedelta(hours=7))
NOW = datetime(2026, 11, 21, 10, 0, tzinfo=VN)
MAILBOX = "sales@haya-hotels.com"
E638 = ("không đủ 2 phòng cho 21/12/2026 - 27/12/2026 (DLX-SV còn 0, SUITE-SV còn 0). Trống trọn cả kỳ: không phòng "
        "nào. Hết DLX-SV đêm 25/12–26/12; hạng nâng SUITE-SV cũng hết (đêm 25/12–26/12). Agent tự tạo group khi có "
        "phòng trống lại (huỷ, đổi ngày) hoặc Chuẩn bị chỗ nhả được phòng. Cần chắc chỗ thì quản lý quyết: nhận "
        "overbook, xếp hạng khác")


def r(n, **kw):
    base = {"_row": n, "action": "NEW", "received_at": "20/11/2026 21:10", "channel_type": "TA", "company": "Victoria Tour",
            "booking_ref": "VT 2112-27", "arrival": "21/12/2026",
            "departure": "27/12/2026", "room_code": "DLX-SV", "rooms": "2", "ez_status": "needs_review",
            "ez_note": E638, "ez_processed_at": "2026-11-21T09:10:00", "source_email": "Booking VT 2112-27"}
    return {**base, **kw}


class FakeTg:
    def __init__(self):
        self.sent = []

    def send(self, text, buttons=None, topic=None):
        self.sent.append(text)
        return len(self.sent)


class FakeMail:
    def search(self, text, top=10):
        return [{"id": "vt-mail", "from": {"emailAddress": {"address": "sales@victoriatour.vn"}}}]


class NoRoomTest(unittest.TestCase):
    def test_what_counts_as_no_room(self):
        for note in (E638, "không đủ 2 phòng (TPL còn 0, QPL còn 0)", "không đủ 1 phòng",
                     # one of two fits: the whole booking is declined too (dev 21/11, "cũng từ chối luôn")
                     "không đủ 2 phòng (DLX-SV còn 1, SUITE-SV còn 0)",
                     "không đủ 3 phòng (DLX-SV còn 1, SUITE-SV còn 1). Trống trọn cả kỳ: không phòng nào"):
            self.assertTrue(build_watch.no_room(note), note)
        for note in ("không đủ 2 phòng (DLX-SV còn 0). Trống trọn cả kỳ: SUP-DBL 3",  # another type fits: Karen
                     "Hết phòng TPL đêm 13/01",  # didn't say it looked at the type above (Footprint 06/11)
                     "voucher thiếu tên khách", ""):
            self.assertFalse(build_watch.no_room(note), note)

    def test_new_booking_is_full_a_change_is_still_stuck(self):
        [i] = build_watch.stuck([r(2516), r(2517)], emi.booking_state, NOW)
        self.assertEqual((i["kind"], i["rows"]), ("full", [2516, 2517]))
        self.assertIn("DECLINE | TA | Victoria Tour", build_watch.render([i]))
        steps = build_watch.decline_steps(i)
        self.assertIn(build_watch.DECLINE_REASON, steps)
        self.assertIn("--kind decline", steps)
        built = r(2400, ez_status="done", ez_note="", pdf_link="x", received_at="10/11/2026 09:00")
        change = r(2516, action="CHANGE")
        [i] = build_watch.stuck([built, change], emi.booking_state, NOW)
        self.assertEqual(i["kind"], "stuck")

    def test_ota_booking_is_never_declined(self):
        # dev 25/11: R2572 (Booking.com via SynXis) and E-638 (MG): a question, never Emi's own CANCEL
        for kw in ({"channel_type": "OTA", "company": "Booking.com",
                    "booking_ref": "SynXis 92777EF003597 (Booking.com)"},
                   {"channel_type": "OTA", "company": "MG", "booking_ref": "MG AGIN0116572611657606 / HB2611488385"},
                   {"channel_type": "TA", "company": "WebBeds FZ LLC", "booking_ref": "WB 123456"}):
            [i] = build_watch.stuck([r(2565, **kw)], emi.booking_state, NOW)
            self.assertEqual(i["kind"], "stuck", kw)
            self.assertIn("STUCK |", build_watch.render([i]))

    def test_sheet_append_refuses_an_ota_cancel_of_our_own(self):
        def errors(**kw):
            row = {"action": "CANCEL", "channel_type": "OTA", "company": "Booking.com",
                   "booking_ref": "SynXis 92777EF003597 (Booking.com)", **kw}
            sheet = SimpleNamespace(header=list(row) + ["Cancellation Reason", "internal_notes", "what_changed"])
            with mock.patch.object(emi.schema, "room_codes", return_value=None),                     mock.patch.object(emi.schema, "check_row", return_value=([], [])),                     mock.patch.object(emi, "_earlier_arrivals", return_value={}):
                return [e for e in emi.check_rows(sheet, [row])[0] if "R2572" in e]
        # row 2572 as Emi wrote it
        self.assertTrue(errors(what_changed=build_watch.DECLINE_REASON,
                               **{"Cancellation Reason": "No availability in EZFOLIO – notice 22/11/2026"}))
        self.assertTrue(errors(company="MG", internal_notes="Build tool: no room (rows 2516); declined at once"))
        # the OTA's own cancellation passes; a travel agency's decline is still Emi's to write
        self.assertFalse(errors(what_changed="Cancelled by guest (SynXis cancellation notice)",
                                **{"Cancellation Reason": "Guest cancelled via Booking.com – notice 24/11/2026"}))
        self.assertFalse(errors(channel_type="TA", company="Victoria Tour", what_changed=build_watch.DECLINE_REASON))

    def test_declined_once_no_question_and_the_open_one_closed(self):
        st, tg = State(tempfile.mktemp(suffix="-state.json")), FakeTg()
        qid = st.ask("VT 2112-27", "build tool stopped", "vt-mail")  # asked before the rule, like E-638
        items = build_watch.stuck([r(2516)], emi.booking_state, NOW)
        self.assertEqual(len(build_watch.alert(st, tg, FakeMail(), items, MAILBOX, out=lambda *_: None)), 1)
        self.assertEqual(st.open_questions(), {})
        self.assertIn("declined at once", st.data["questions"][qid]["closed"]["reason"])
        self.assertIn("🚫", tg.sent[0])
        self.assertIn(f"{qid} closed", tg.sent[0])
        self.assertEqual(build_watch.alert(st, tg, FakeMail(), items, MAILBOX, out=lambda *_: None), [])
        # the build tool's retry rewrites ez_processed_at: still told once
        retried = build_watch.stuck([r(2516, ez_processed_at="2026-11-21T09:55:00")], emi.booking_state, NOW)
        self.assertEqual(build_watch.alert(st, tg, FakeMail(), retried, MAILBOX, out=lambda *_: None), [])
        self.assertEqual(len(tg.sent), 1)

    def test_build_stuck_prints_the_decline_steps(self):
        lines = []

        class Sheet:
            def rows(self):
                return [r(2516)]

        emi.run_build_stuck(Sheet(), State(tempfile.mktemp(suffix="-state.json")), out=lines.append)
        text = "\n".join(lines)
        self.assertIn("DECLINE |", text)
        self.assertIn("no question to Karen", text)


if __name__ == "__main__":
    unittest.main()
