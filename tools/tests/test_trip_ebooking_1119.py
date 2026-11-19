"""Trip.com's price is the net on its Ebooking voucher, not SynXis's (dev, 2026-11-19).

Trip.com pays HAYA by VCC. SynXis's "Total Cost with Tax" is the price before Trip.com's "Pay Now & Save"
(-10% / -20%): row 847, Trip.com 1433815683617600 / SynXis 92777EF003129, carried 3,719,250 against the 3,347,324
Trip.com pays; rows 1785-1786, 2089-2090, 2309-2310 and 2326 the same way. tools/intake_schema.py check_row."""
import unittest

from tools.tests.test_intake_consistency import check, has


def trip_notes(item6):
    return ("1. Trip.com – Ref 1433815683617600\n2. JAMIL HUSSAIN\n3. 13/11/2026 – 15/11/2026\n"
            "4. 1 Deluxe Seaview – 2 adults, 0 children, BB\n5. Non-smoking room\n"
            f"6. {item6}\n7. Invoice: prepaid by Trip.com (VCC)\n8. No VAT info")


def trip(item6, **kw):
    return check(**dict(company="Trip.com", rate_source="OTA net", missing_info="",
                        booking_ref="Trip.com 1433815683617600 / SynXis 92777EF003129",
                        notes=trip_notes(item6), **kw))[0]


class TripEbookingTest(unittest.TestCase):
    def test_synxis_figure_refused(self):
        errors = trip("Net 1,859,625 × 2 nights × 1 room = 3,719,250 VND (SynXis Total Cost with Tax)")
        self.assertTrue(has(errors, "notes: item 6 on a Trip.com row"), errors)

    def test_ebooking_net_passes(self):
        errors = trip("Trip.com Ebooking net 1,673,662 × 2 nights × 1 room = 3,347,324 VND")
        self.assertFalse(has(errors, "notes: item 6 on a Trip.com row"), errors)

    def test_provisional_synxis_passes(self):
        errors = trip("SynXis total, provisional, no Trip.com Ebooking yet: 1,859,625 × 2 nights × 1 room = 3,719,250 VND")
        self.assertFalse(has(errors, "notes: item 6 on a Trip.com row"), errors)

    def test_change_row_too_cancel_not(self):
        bad = "Net 1,859,625 × 2 nights × 1 room = 3,719,250 VND"
        self.assertTrue(has(trip(bad, action="CHANGE"), "notes: item 6 on a Trip.com row"))
        self.assertFalse(has(trip(bad, action="CANCEL"), "notes: item 6 on a Trip.com row"))

    def test_other_otas_untouched(self):
        errors = check(company="Expedia", rate_source="OTA net", notes="")[0]
        self.assertFalse(has(errors, "notes: item 6 on a Trip.com row"))


if __name__ == "__main__":
    unittest.main()
