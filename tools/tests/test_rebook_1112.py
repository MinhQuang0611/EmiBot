"""Dev, 2026-11-12, two confirmation drafts that never got their PDF.

Odeon V9SLHPMH5_11_1 (row 1738): front office made group 30948 by hand, the build tool wrote ez_status 'existing' with
the PDF; and the guest arrived 09/11, so confirmations-due skipped the booking and its early draft sat.

Pegas 11131133: QPL on request declined (CANCEL row 1845, group 31000 cancelled in EZFOLIO), then TPL sent in the
allotment under the same number. "phải build lại": NEW rows, a new group, a new confirmation; the CHANGE row 1864 got
ez_status no_change and no PDF."""
import os
import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest import mock

from tools import build_watch, emi, payments
from tools.state import State
from tools.tests.test_emi import BOOKING, TPL, appended, real_sheet
from tools.tests.test_payments import MAILBOX, VN, FakeMail, row

PDF = "https://drive.google.com/file/d/10iTcVvpuTtEMDmP6mYERS2NiY-quEeAX/view"


def odeon(**kw):
    return row(1738, **{**dict(channel_type="Tour operator", company="Odeon", booking_ref="V9SLHPMH5_11_1",
               ezfolio_group_code="30948", received_at="09/11/2026 15:14", arrival="09/11/2026",
               departure="20/11/2026", total_vnd="18900000", pdf_link=PDF, ez_status="existing",
               ez_processed_at="2026-11-10T08:27:26"), **kw})


def pegas():
    base = dict(channel_type="Tour operator", company="Pegas", booking_ref="Pegas 11131133", arrival="07/01/2027",
                departure="19/01/2027", pdf_link=PDF)
    return [row(1833, **base, ezfolio_group_code="31000", received_at="10/11/2026 18:32", room_code="QPL",
                total_vnd="29452500", ez_status="done", ez_processed_at="2026-11-10T18:43:44"),
            row(1845, **base, action="CANCEL", status="Cancelled", ezfolio_group_code="31000",
                received_at="10/11/2026 18:32", room_code="QPL", total_vnd="29452500", ez_status="done",
                ez_processed_at="2026-11-11T11:23:51+07:00", what_changed="On request booking cannot be accommodated"),
            row(1864, **base, action="CHANGE", ezfolio_group_code="31000", received_at="11/11/2026 12:20",
                room_code="TPL", total_vnd="24777500", ez_status="no_change", ez_processed_at="2026-11-11T12:33:25",
                ez_note="agent: group 31000 đã huỷ (CX), booking đã có dòng huỷ (dòng 1845): bản sửa này không còn "
                        "cần làm", what_changed="Room category Quadruple Family → Triple City View")]


def due(rows, st, today=date(2026, 11, 12)):
    return payments.needs_confirmation(rows, emi.booking_state, emi._parts, FakeMail(code="other"), st, MAILBOX, today)


class ExistingGroupTest(unittest.TestCase):
    def test_existing_with_its_pdf_is_built(self):
        self.assertIsNotNone(payments.built_at([odeon()]))
        self.assertIsNone(payments.built_at([odeon(pdf_link="")]))
        self.assertTrue(emi._built(odeon()))

    def test_an_early_draft_is_finished_after_arrival(self):
        st = State(os.devnull + "-none")
        self.assertEqual(due([odeon()], st), [])  # in house, nothing drafted: no confirmation owed any more
        st.record_draft("d1", "V9SLHPMH5_11_1", 1738, "confirmation", awaiting_pdf=True)
        st.data["reviews"]["700"] = {"draft_id": "d1", "status": "open"}
        items = due([odeon()], st)
        self.assertEqual([(i["ref"], i["row"]) for i in items], [("V9SLHPMH5_11_1", 1738)])
        self.assertEqual(items[0]["attach"], "700")


class RebookTest(unittest.TestCase):
    def test_since_rebook(self):
        rows = pegas() + [row(1900, booking_ref="Pegas 11131133", received_at="12/11/2026 09:00", room_code="TPL")]
        self.assertEqual([r["_row"] for r in payments.since_rebook(rows)], [1900])
        self.assertEqual([r["_row"] for r in payments.since_rebook(pegas())], [1833, 1845, 1864])

    def test_the_cancelled_group_owes_nothing_the_rebuild_owes_its_confirmation(self):
        st = State(os.devnull + "-none")
        st.record_draft("d0", "Pegas 11131133", 1833, "confirmation")  # #740, the QPL confirmation
        self.assertEqual(due(pegas(), st), [])
        new = row(1900, channel_type="Tour operator", company="Pegas", booking_ref="Pegas 11131133",
                  ezfolio_group_code="31050", received_at="12/11/2026 09:00", arrival="07/01/2027",
                  departure="19/01/2027", room_code="TPL", total_vnd="24777500", pdf_link=PDF, ez_status="done",
                  ez_processed_at="2026-11-12T10:00:00")
        items = due(pegas() + [new], st)
        self.assertEqual([(i["row"], i["group"]) for i in items], [(1900, "31050")])
        st.record_draft("d2", "Pegas 11131133", 1900, "confirmation")
        self.assertEqual(due(pegas() + [new], st), [])

    def test_sheet_append_takes_a_new_on_a_cancelled_group_only_when_told(self):
        live = SimpleNamespace(rows=lambda: [dict(r, booking_ref="TEST-1510", _sheet="live") for r in pegas()])
        new = dict(BOOKING, received_at="12/11/2026 09:00", status="Definite", **TPL)
        sh, http = real_sheet()
        with self.assertRaises(emi.Refused) as e:
            emi.sheet_append(sh, [new], out=lambda *_: None, live=live)
        self.assertIn("Rebooked after cancellation row 1845", str(e.exception))
        sh, http = real_sheet()
        # the test sheet has no internal_notes column (the live one has); the gate is what is tested here
        with mock.patch.object(emi, "sheet_check"), mock.patch.object(emi, "verify_appended"), \
                mock.patch.object(sh, "append_rows") as put:
            emi.sheet_append(sh, [dict(new, internal_notes="Rebooked after cancellation row 1845")],
                             out=lambda *_: None, live=live)
        self.assertEqual([r["action"] for r in put.call_args[0][0]], ["NEW"])

    def test_not_a_rebook_while_the_group_lives(self):
        rows = pegas()
        rows[1] = dict(rows[1], ez_status="")  # the CANCEL not done in EZFOLIO yet
        self.assertIsNone(emi.cancelled_in_ezfolio(rows, "Pegas 11131133"))
        self.assertEqual(emi.cancelled_in_ezfolio(pegas(), "Pegas 11131133")["_row"], 1845)


class CancelledGroupStopTest(unittest.TestCase):
    def test_a_change_on_a_cancelled_group_goes_to_karen(self):
        items = build_watch.stuck(pegas(), emi.booking_state, datetime(2026, 11, 12, 10, 0, tzinfo=VN))
        self.assertEqual([(i["kind"], i["rows"]) for i in items], [("stuck", [1864])])
        self.assertIn("đã huỷ (CX)", items[0]["note"])

    def test_a_plain_no_change_is_not_a_stop(self):
        rows = pegas()
        rows[2] = dict(rows[2], ez_note="không có gì thay đổi")
        self.assertEqual(build_watch.stuck(rows, emi.booking_state, datetime(2026, 11, 12, 10, 0, tzinfo=VN)), [])


if __name__ == "__main__":
    unittest.main()
