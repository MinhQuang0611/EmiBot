"""Dev, 2026-11-26: "Sao đến bây giờ EMI vẫn chưa xác nhận được Pegas". Pegas 11162942 (17–29/12, 1 TPL, Allotment)
was still New on Pegasys. The build tool found no room (row 2756); Emi declined it at once (CANCEL row 2758, 13:45),
though the contract's allotment owes those rooms; Karen took it back with a CHANGE dated 13:09, the email's time, which
the build tool left out_of_scope as older than the CANCEL. No group, no PDF, no confirmation: nothing for pegas-confirm
to press, and its dry run said only "nothing to confirm".

Now: an allotment booking with no room is a question, never a decline; a booking cancelled before it was ever built is
taken back with NEW rows "Rebooked after cancellation row N", dated after the CANCEL; and pegas-confirm names the
reason for every booking it leaves alone."""
import os
import tempfile
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest import mock

from tools import build_watch, emi, pegasys
from tools.state import State
from tools.tests.test_build_full_1121 import E638, NOW, r
from tools.tests.test_emi import BOOKING, TPL, real_sheet
from tools.tests.test_pegasys_1120 import MAILBOX, NOW as PNOW, FakeMail, notice, row, sent, state_of


def pegas_rows():
    base = dict(channel_type="Tour operator", company="Pegas", booking_ref="Pegas 11162942", arrival="17/12/2026",
                departure="29/12/2026", room_code="TPL", rooms="1")
    return [dict(base, _row=2756, action="NEW", received_at="26/11/2026 13:09", internal_notes="Allotment",
                 ez_status="no_change", ez_note="agent: booking đã huỷ ở dòng 2758 trước khi tạo group, không tạo"),
            dict(base, _row=2758, action="CANCEL", received_at="26/11/2026 13:45",
                 internal_notes="Build tool: no room (rows 2756); declined at once (dev 21/11)", ez_status="no_change",
                 ez_note="agent: không có group còn hiệu lực trên Ezfolio (chưa từng nhập hoặc đã huỷ)"),
            dict(base, _row=2760, action="CHANGE", received_at="26/11/2026 13:09", ez_status="out_of_scope",
                 internal_notes="Allotment: Yes (entire stay period). Reinstated by Karen after erroneous "
                                "no-availability cancellation row 2758.")]


class AllotmentIsNeverDeclinedTest(unittest.TestCase):
    def test_tour_operator_allotment_with_no_room_is_a_question(self):
        for notes in ("Allotment", "Allotment: Yes (entire stay period)"):
            [i] = build_watch.stuck([r(2756, channel_type="Tour operator", company="Pegas",
                                       booking_ref="Pegas 11162942", internal_notes=notes)], emi.booking_state, NOW)
            self.assertEqual(i["kind"], "stuck", notes)

    def test_on_request_or_a_travel_agency_is_still_declined(self):
        for kw in ({"channel_type": "Tour operator", "company": "Pegas", "booking_ref": "Pegas 1",
                    "internal_notes": "Allotment: No (on request), accepted by Karen E-700"},
                   {}):
            [i] = build_watch.stuck([r(2756, **kw)], emi.booking_state, NOW)
            self.assertEqual(i["kind"], "full", kw)


class TakenBackAfterOurDeclineTest(unittest.TestCase):
    def test_never_built_cancel_is_a_rebook(self):
        self.assertEqual(emi.cancelled_in_ezfolio(pegas_rows(), "Pegas 11162942")["_row"], 2758)
        # a CANCEL on a booking that has a group still needs the build tool's done
        built = [dict(row, ez_status="done") if row["_row"] == 2756 else row for row in pegas_rows()]
        self.assertIsNone(emi.cancelled_in_ezfolio(built, "Pegas 11162942"))

    def test_sheet_append_takes_new_rows_dated_after_the_cancel(self):
        live = SimpleNamespace(rows=lambda: [dict(x, booking_ref="TEST-1510", _sheet="live") for x in pegas_rows()])
        new = dict(BOOKING, status="Definite", **TPL)
        sh, _ = real_sheet()
        with self.assertRaises(emi.Refused) as e:  # no rebook note: refused, and told how
            emi.sheet_append(sh, [dict(new, received_at="26/11/2026 17:00")], out=lambda *_: None, live=live)
        self.assertIn("Rebooked after cancellation row 2758", str(e.exception))
        sh, _ = real_sheet()
        with self.assertRaises(emi.Refused) as e:  # dated as the email (13:09): the CANCEL would read as newer
            emi.sheet_append(sh, [dict(new, received_at="26/11/2026 13:09",
                                       internal_notes="Allotment. Rebooked after cancellation row 2758")],
                             out=lambda *_: None, live=live)
        self.assertIn("not after the CANCEL row 2758", str(e.exception))
        sh, _ = real_sheet()
        with mock.patch.object(emi, "sheet_check"), mock.patch.object(emi, "verify_appended"), \
                mock.patch.object(sh, "append_rows") as put:
            emi.sheet_append(sh, [dict(new, received_at="26/11/2026 17:00",
                                       internal_notes="Allotment. Rebooked after cancellation row 2758")],
                             out=lambda *_: None, live=live)
        self.assertEqual([x["action"] for x in put.call_args[0][0]], ["NEW"])


class PegasConfirmSaysWhyTest(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(self.path)
        self.st = State(self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def lines(self, mail, rows):
        return pegasys.due(mail, rows, state_of, self.st, MAILBOX, PNOW)[1]

    def test_each_booking_left_alone_has_its_reason(self):
        n = notice("n1", "11138234", "2026-11-18T02:00:00Z")
        [line] = self.lines(FakeMail(n), [row(1, ez_status="needs_review", pdf_link="")])
        self.assertIn("WAITING, not built", line)
        self.assertIn("needs_review", line)
        [line] = self.lines(FakeMail(n), [row(1)])
        self.assertIn("WAITING, no mail with a file", line)
        [line] = self.lines(FakeMail(n), [row(1), row(2, action="CANCEL")])
        self.assertIn("cancelled on the sheet", line)
        self.st.data["pegasys"]["bookings"]["11138234"] = {"notice_at": "2026-11-18T02:00:00Z", "status": "Confirmed"}
        [line] = self.lines(FakeMail(n, sent("s1", "11138234", "2026-11-18T09:00:00Z")), [row(1)])
        self.assertIn("done (Confirmed", line)


if __name__ == "__main__":
    unittest.main()
