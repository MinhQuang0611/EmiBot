"""Tracy's check of the live sheet, 31/10: a second partial cancel refused (Sobiesiak), one slip on every room
row (Footprint 845-847), an MG reminder written as a row (868), '1 adults' (870), the VAT line left out of
item 8 (845-847), Vietnam for Pakistani guests (860-861)."""
import unittest

from tools import emi
from tools.tests.test_emi import BOOKING, BUILT, DLX, TPL, TPL_BUILT, appended, real_sheet, sheet_row
from tools.tests.test_intake_consistency import NOTES, check, has


class PartialCancelTest(unittest.TestCase):
    TWO = dict(BUILT, rooms="2", booking_ref="Booking.com 5714547701 / SynXis 92777EF003106 + 92777EF003107")
    CANCEL = dict(action="CANCEL", received_at="31/10/2026 00:30", source_email="SynXis Res Cancelled",
                  booking_ref="Booking.com 5714547701 / SynXis 92777EF003106 + 92777EF003107", property="HAYA",
                  status="Cancelled", priority="Normal", what_changed="Cancelled SynXis 92777EF003107",
                  rooms="1", room_code="DLX-SV", **{"Cancellation Amount": "0",
                                                    "Cancellation Reason": "Cancelled by guest – notice 31/10/2026"})

    def test_second_room_of_two_can_be_cancelled(self):
        first = dict(self.TWO, **{k: v for k, v in self.CANCEL.items()})
        sh, http = real_sheet([sheet_row(**self.TWO), sheet_row(**first)])
        second = dict(self.CANCEL, received_at="31/10/2026 03:10", what_changed="Cancelled SynXis 92777EF003106")
        emi.sheet_append(sh, {"booking": second, "room_lines": [{"room_code": "DLX-SV", "rooms": "1"}]},
                         out=lambda *_: None)
        self.assertEqual([r["action"] for r in appended(http)], ["CANCEL"])

    def test_third_cancel_refused_once_every_room_is_cancelled(self):
        first = dict(self.TWO, **self.CANCEL)
        second = dict(first, received_at="31/10/2026 03:10")
        sh, http = real_sheet([sheet_row(**self.TWO), sheet_row(**first), sheet_row(**second)])
        with self.assertRaises(emi.Refused) as e:
            emi.sheet_append(sh, {"booking": dict(self.CANCEL, received_at="31/10/2026 05:00"),
                                  "room_lines": [{"room_code": "DLX-SV", "rooms": "1"}]}, out=lambda *_: None)
        self.assertIn("already cancelled", str(e.exception))
        self.assertIsNone(appended(http))


class SlipSharedOutTest(unittest.TestCase):
    def test_one_slip_split_over_the_room_rows(self):
        data = {"booking": {"Payment 1": "6300000", "Payment 1 date + time": "30/10/2026 16:36"},
                "room_lines": [dict(DLX), dict(TPL)]}
        lines = []
        got = emi.split_payments(data, out=lines.append)["room_lines"]
        self.assertEqual([(r["Payment 1"], r["Payment 1 date + time"], r["Remaining amount"]) for r in got],
                         [("4000000", "30/10/2026 16:36", "4000000"), ("2300000", "30/10/2026 16:36", "2300000")])
        self.assertIn("shared out", lines[0])

    def test_rounding_on_the_first_row_and_shares_given_per_line_kept(self):
        got = emi.split_payments({"booking": {"Payment 1": "1000001"},
                                  "room_lines": [dict(DLX), dict(TPL)]}, out=lambda *_: None)["room_lines"]
        self.assertEqual(sum(int(r["Payment 1"]) for r in got), 1000001)
        own = {"booking": {}, "room_lines": [dict(DLX, **{"Payment 1": "1"}), dict(TPL, **{"Payment 1": "2"})]}
        self.assertIs(emi.split_payments(own), own)

    def test_change_rows_on_the_sheet_sum_to_the_slip(self):
        sh, http = real_sheet([sheet_row(**BUILT), sheet_row(**TPL_BUILT)])
        own = lambda line: {k: line[k] for k in ("room_code", "notes", "rate_source", "rate_per_night_vnd",
                                                  "Average rate per night after discount", "total_vnd", "meal_plan")}
        change = dict(action="CHANGE", received_at="25/10/2026 13:56", source_email="Re: TEST-1510",
                      booking_ref="TEST-1510", what_changed="Payment 1 received", property="HAYA", status="Definite",
                      priority="Normal", nights="2", **{"Payment 1": "6300000", "Payment 1 date + time": "x"})
        emi.sheet_append(sh, {"booking": change, "room_lines": [own(DLX), own(TPL)]}, out=lambda *_: None)
        self.assertEqual([r["Payment 1"] for r in appended(http)], ["4000000", "2300000"])


class RowChecksTest(unittest.TestCase):
    def test_mg_reminder_is_no_row(self):
        errors, _ = check(source_email="REMINDER - AGIN0116572610360398 does not have Hotel Confirmation")
        self.assertTrue(has(errors, "source_email: an MG 'REMINDER"))

    def test_one_adults(self):
        errors, _ = check(notes=NOTES.replace("1 adult, 0 children", "1 adults, 0 children"))
        self.assertIn("notes: '1 adults' — write '1 adult'", errors)
        self.assertFalse(has(check()[0], "notes: '1"))

    def test_item_8_carries_the_tax_id(self):
        inv = "Công ty TNHH TM & Du Lịch Dấu Chân – MST 0101148059 – Hà Nội – vat@footprint.vn"
        errors, _ = check(invoice_details=inv)
        self.assertTrue(has(errors, "notes: item 8 is the VAT line"))
        ok = NOTES.replace("8. No VAT info", "8. VAT invoice: " + inv)
        self.assertFalse(has(check(invoice_details=inv, notes=ok)[0], "notes: item 8"))

    def test_vietnam_only_with_no_clue_in_the_names(self):
        self.assertTrue(has(check(nationality="Vietnam", guest_names="HAROON OMAR; ABDUL RAHIM MALIK")[0],
                            "nationality: Vietnam"))
        for names in ("Nguyễn Văn An", "Trần Thị B; TBA", "TBA", "1 guest TBA"):
            self.assertFalse(has(check(nationality="Vietnam", guest_names=names)[0], "nationality"), names)


if __name__ == "__main__":
    unittest.main()
