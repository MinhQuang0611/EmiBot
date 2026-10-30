"""dev 30/10: Emi reads HAYA's live intake sheet (read only) to find bookings from before 22/10 and their group
codes, still writing to its own sheet; Cancellation Amount / Cancellation Reason; HAYA-D refs for direct guests."""
import unittest
from datetime import datetime
from types import SimpleNamespace

from tools import cancel_fee as cancelling
from tools import emi
from tools import intake_schema as schema
from tools.intake_sheet import IntakeSheet, ReadOnlySheet, SheetContractError
from tools.tests.test_emi import appended, real_sheet
from tools.tests.test_tools import FakeHttp

# The live header as the dev pasted it, 30/10/2026
LIVE_HEADER = ("action	received_at	source_email	property	channel_type	company	contact_person	company_email	"
               "booking_ref	ezfolio_group_code	confirmation_no	what_changed	guest_names	nationality	arrival	"
               "departure	nights	room_code	rooms	adults	children	child_ages	meal_plan	rate_source	"
               "rate_per_night_vnd	discount_promo	Average rate per night after discount	surcharge	"
               "Surcharge amount	total_vnd	status	hold_until	prepaid	invoice_details	arrival_time	transfer	"
               "special_requests	notes	internal_notes	missing_info	priority	Group code	pdf_link	COD 	"
               "Payment 1	Payment 1 date + time	Payment 2	Payment 2 date + time	Remaining amount	"
               "Cancellation Amount	Cancellation Reason	ez_status	ez_error	ez_note	ez_processed_at").split("\t")

TIQI = {"action": "NEW", "received_at": "18/10/2026 10:00", "source_email": "BK FROM TIQI - HAYA HOTEL PHU QUOC",
        "property": "HAYA", "channel_type": "TA", "company": "Tiqi Travel", "booking_ref": "TIQI-2311",
        "guest_names": "MR LI WEI", "nationality": "China", "arrival": "23/11/2026", "departure": "26/11/2026",
        "nights": "3", "room_code": "TPL", "rooms": "2", "adults": "4", "meal_plan": "BB", "rate_source": "TA card",
        "rate_per_night_vnd": "1700000", "Average rate per night after discount": "1700000", "total_vnd": "10200000",
        "status": "Definite", "prepaid": "No", "priority": "Normal", "Group code": "30455",
        "pdf_link": "https://drive.google.com/x", "Remaining amount": "10200000"}


def live_sheet(rows=(), broken=False):
    def data(_):
        if broken:
            raise RuntimeError("HTTP 403 for https://sheets.googleapis.com/...: The caller does not have permission")
        return {"values": [[r.get(h.strip(), "") for h in LIVE_HEADER] for r in rows]}
    http = FakeHttp([("GET", "!1:1", {"values": [LIVE_HEADER]}), ("GET", "!A3:", data)])
    return ReadOnlySheet(IntakeSheet("LIVE", lambda m, u, body=None: http(m, u, body=body))), http


class LiveLookupTest(unittest.TestCase):
    def setUp(self):
        self.lines = []

    def test_found_on_the_live_sheet_only(self):
        sh, _ = real_sheet()
        live, _ = live_sheet([TIQI])
        hits = emi.sheet_find(sh, "tiqi", out=self.lines.append, live=live)
        self.assertEqual([h["_sheet"] for h in hits], ["live"])
        self.assertEqual(hits[0]["ezfolio_group_code"], "30455")  # the bot's Group code column
        self.assertIn("0 on Emi's sheet, 1 on the live sheet", self.lines[0])

    def test_unreadable_live_sheet_is_a_gap_not_a_stop(self):
        sh, _ = real_sheet()
        live, _ = live_sheet(broken=True)
        self.assertEqual(emi.sheet_find(sh, "tiqi", out=self.lines.append, live=live), [])
        self.assertTrue(any(x.startswith("GAP: live intake sheet not readable (HTTP 403") for x in self.lines))

    def test_live_sheet_is_read_only(self):
        live, http = live_sheet([TIQI])
        for call in (lambda: live.append_rows([TIQI]), lambda: live.update_cells(3, {"notes": "x"})):
            with self.assertRaises(SheetContractError):
                call()
        self.assertFalse([c for c in http.calls if c[0] != "GET"])

    def test_new_refused_for_a_booking_already_on_the_live_sheet(self):
        # tarapb (30/10): a NEW for a booking the live sheet already had
        sh, http = real_sheet()
        live, _ = live_sheet([TIQI])
        new = {k: v for k, v in TIQI.items() if k not in ("Group code", "pdf_link")}
        with self.assertRaises(emi.Refused) as e:
            emi.sheet_append(sh, new, out=self.lines.append, live=live)
        self.assertIn("already on the live sheet (live row 3)", str(e.exception))
        self.assertIsNone(appended(http))

    def test_live_refs_carry_the_channel_name(self):
        # live rows 800 and 812 (30/10): the channel in front of each number
        sh, http = real_sheet()
        live, _ = live_sheet([dict(TIQI, booking_ref="MG AGSG0528672610514149 / HB2610327806")])
        new = {k: v for k, v in TIQI.items() if k not in ("Group code", "pdf_link")}
        with self.assertRaises(emi.Refused):
            emi.sheet_append(sh, dict(new, booking_ref="AGSG0528672610514149"), out=self.lines.append, live=live)
        state = emi.booking_state([dict(TIQI, booking_ref="Booking.com 5486733008 / SynXis 92777EF003114")],
                                  "5486733008")
        self.assertEqual(len(state), 1)
        self.assertFalse(emi._parts("Thu1230 TVR149") & emi._parts("Thu1230 TVR150"))  # a TA code stays whole

    def test_cancel_of_a_live_booking_carries_its_details_and_group_code(self):
        sh, http = real_sheet()
        live, _ = live_sheet([TIQI])
        cancel = {"action": "CANCEL", "received_at": "30/10/2026 10:54",
                  "source_email": "Re: BK FROM TIQI - HAYA HOTEL PHU QUOC - 23/11-26/11", "property": "HAYA",
                  "booking_ref": "TIQI-2311", "what_changed": "Cancelled by agency", "status": "Cancelled",
                  "priority": "Normal"}
        emi.sheet_append(sh, cancel, out=self.lines.append, live=live)
        row = appended(http)[0]
        self.assertEqual((row["company"], row["room_code"], row["ezfolio_group_code"]), ("Tiqi Travel", "TPL", "30455"))
        self.assertEqual(row["Remaining amount"], "0")
        self.assertTrue(any("copied from live row 3" in x for x in self.lines))


class CancellationColumnsTest(unittest.TestCase):
    CANCEL = dict(action="CANCEL", received_at="30/10/2026 10:54", source_email="Re: BK", property="HAYA",
                  channel_type="TA", company="Tiqi Travel", booking_ref="TIQI-2311", guest_names="MR LI WEI",
                  nationality="China", status="Cancelled", priority="Normal", what_changed="Cancelled by agency",
                  **{"Remaining amount": "0"})

    def errors(self, **cells):
        return schema.check_row(dict(self.CANCEL, **cells))[0]

    def test_amount_never_blank_zero_is_fine(self):
        self.assertTrue(any(e.startswith("Cancellation Amount") for e in
                            self.errors(**{"Cancellation Amount": "", "Cancellation Reason": "x – notice 30/10/2026"})))
        self.assertFalse(any(e.startswith("Cancellation") for e in
                             self.errors(**{"Cancellation Amount": "0", "Cancellation Reason": "Guest changed plans "
                                                                                               "– notice 30/10/2026"})))

    def test_reason_carries_the_notice_date(self):
        self.assertTrue(any(e.startswith("Cancellation Reason") for e in
                            self.errors(**{"Cancellation Amount": "0", "Cancellation Reason": "Guest changed plans"})))

    def test_sheet_without_the_columns_is_not_asked(self):
        self.assertFalse(any(e.startswith("Cancellation") for e in self.errors()))

    def test_cancel_fee_per_row(self):
        rows = [dict(TIQI, _row=3), dict(TIQI, _row=4, room_code="DLX-SV", rooms="1", rate_per_night_vnd="2000000",
                                         **{"Average rate per night after discount": "2000000"})]
        c = cancelling.cancel_fee(rows, datetime(2026, 11, 19, 9, 0))  # 4 days before: one night of every room
        self.assertEqual(c["fee"], 2 * 1700000 + 2000000)
        self.assertEqual([(code, fee) for _, code, fee in c["per_row"]], [("TPL", 3400000), ("DLX-SV", 2000000)])
        self.assertIn("CANCELLATION AMOUNT per CANCEL row (digits): TPL: 3400000; DLX-SV: 2000000",
                      cancelling.render(c))


class DirectRefTest(unittest.TestCase):
    def test_next_number_over_both_sheets(self):
        sh, _ = real_sheet([["NEW", "", "", "HAYA", "Direct", "", "", "", "HAYA-D007"]])
        live, _ = live_sheet([dict(TIQI, booking_ref="HAYA-D011", channel_type="Direct")])
        self.assertEqual(emi.direct_ref(sh, live=live, out=lambda *_: None), "HAYA-D012")

    def test_first_one_and_unreadable_live(self):
        sh, _ = real_sheet()
        self.assertEqual(emi.direct_ref(sh, out=lambda *_: None), "HAYA-D001")
        live, _ = live_sheet(broken=True)
        with self.assertRaises(emi.Refused):
            emi.direct_ref(sh, live=live, out=lambda *_: None)

    def test_direct_new_row_needs_the_haya_d_ref(self):
        row = dict(action="NEW", channel_type="Direct", booking_ref="", guest_names="X", nationality="Vietnam")
        self.assertTrue(any(e.startswith("booking_ref: a Direct booking") for e in schema.check_row(row)[0]))
        self.assertFalse(any(e.startswith("booking_ref") for e in
                             schema.check_row(dict(row, booking_ref="HAYA-D012"))[0]))


if __name__ == "__main__":
    unittest.main()
