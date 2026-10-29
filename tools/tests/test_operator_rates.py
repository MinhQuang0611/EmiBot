"""Offline tests for tools/operator_rates.py against the real docs/rate-knowledge/odeon-rates.json."""
import unittest
from datetime import date

from tools import operator_rates as o


def odeon(arr, dep, room, adults, kids=(), booked=date(2026, 9, 1), spo=("none",), **kw):
    return o.price("Odeon", arr, dep, room, adults, list(kids), booked=booked, spo=list(spo), **kw)


class OdeonTest(unittest.TestCase):
    def test_spo_code_is_required(self):
        with self.assertRaises(o.RateError) as e:
            o.price("Odeon", date(2026, 11, 20), date(2026, 11, 23), "STD", 2, booked=date(2026, 9, 1))
        self.assertIn("--spo", str(e.exception))

    def test_no_spo_no_offer_even_when_booked_early(self):
        q = odeon(date(2026, 11, 20), date(2026, 11, 23), "STD", 2)
        self.assertEqual(q["offers"], [])
        self.assertEqual(q["total"], 1900000 * 3)

    def test_eb_tier_from_booking_date(self):
        # 80 days ahead -> 15%, room and child surcharge
        q = odeon(date(2026, 11, 20), date(2026, 11, 23), "DLX-SV", 2, [7], spo=["EB"])
        self.assertEqual(q["net"]["room"], round(2200000 * 0.85) * 3)
        self.assertEqual(q["net"]["child"], round(300000 * 0.85) * 3)
        q = odeon(date(2026, 11, 20), date(2026, 11, 23), "STD", 2, booked=date(2026, 10, 15), spo=["EB"])
        self.assertEqual(q["net"]["room"], round(1900000 * 0.95) * 3)  # 36 days -> 5%

    def test_eb_not_on_period_c(self):
        q = odeon(date(2026, 12, 30), date(2027, 1, 2), "STD", 2, booked=date(2026, 9, 1), spo=["EB"])
        self.assertEqual(q["net"]["room"], round(1900000 * 0.85) + 2450000 * 2)

    def test_voucher_pct_wins_with_a_gap(self):
        q = odeon(date(2026, 11, 20), date(2026, 11, 23), "STD", 2, spo=["EB10"])
        self.assertEqual(q["net"]["room"], round(1900000 * 0.9) * 3)
        self.assertTrue(any("Karen to check" in g for g in q["gaps"]))

    def test_free_night_multiplied_cheapest_meals_still_charged(self):
        q = odeon(date(2027, 3, 25), date(2027, 4, 14), "STD", 2, spo=["FS001"], meal="HB")
        # 20 nights: 25–31/3 B (1,900,000), 1–13/4 A (1,250,000) -> 2 free A nights
        free = [x for x in q["offers"] if x[0] == "free"][0]
        self.assertEqual(free[2]["room"], 1250000 * 2)
        self.assertEqual(q["net"]["meal"], 600000 * 2 * 20)

    def test_cascade_free_night_then_eb(self):
        q = odeon(date(2026, 11, 20), date(2026, 11, 30), "STD", 2, spo=["EB", "FS001"])
        self.assertEqual(q["net"]["room"], round(1900000 * 0.85) * 9)

    def test_sco_only_when_given_and_flagged(self):
        q = odeon(date(2026, 11, 20), date(2026, 11, 23), "STD", 2, spo=["SCO"])
        self.assertEqual(q["net"]["room"], round(1900000 * 0.95) * 3)
        self.assertTrue(any("SCO" in g for g in q["gaps"]))

    def test_unknown_spo_refused(self):
        with self.assertRaises(o.RateError):
            odeon(date(2026, 11, 20), date(2026, 11, 23), "STD", 2, spo=["XYZ"])

    def test_child_spare_bed_rules(self):
        # 1 adult + 1st child free; 2 adults + 1st child 3–11.99 charged; 2–2.99 free; infant free, not counted
        self.assertEqual(odeon(date(2026, 11, 20), date(2026, 11, 22), "STD", 1, [8])["gross"]["child"], 0)
        self.assertEqual(odeon(date(2026, 11, 20), date(2026, 11, 22), "STD", 2, [8])["gross"]["child"], 600000)
        self.assertEqual(odeon(date(2026, 11, 20), date(2026, 11, 22), "STD", 2, [2])["gross"]["child"], 0)
        q = odeon(date(2026, 11, 20), date(2026, 11, 22), "TPL", 2, [9, 5])  # 1st free, 2nd charged
        self.assertEqual(q["charged_kids"], [5])
        q = odeon(date(2026, 11, 20), date(2026, 11, 22), "STD", 2, [1])
        self.assertEqual((q["infants"], q["gross"]["child"]), ([1], 0))

    def test_over_capacity_is_a_gap(self):
        q = odeon(date(2026, 11, 20), date(2026, 11, 22), "SUP-TWN", 2, [8])
        self.assertTrue(any("capacity" in g for g in q["gaps"]))

    def test_release_window(self):
        q = odeon(date(2026, 11, 20), date(2026, 11, 22), "STD", 2, booked=date(2026, 11, 10))
        self.assertEqual((q["release_days"], q["ahead"], q["inside_release"]), (14, 10, False))
        q = odeon(date(2027, 2, 6), date(2027, 2, 8), "STD", 2, booked=date(2027, 1, 20))
        self.assertEqual((q["release_days"], q["inside_release"]), (21, False))

    def test_outside_contract(self):
        with self.assertRaises(o.RateError):
            odeon(date(2027, 10, 30), date(2027, 11, 2), "STD", 2)

    def test_row_fields_add_up(self):
        q = odeon(date(2026, 11, 20), date(2026, 12, 1), "DLX-SV", 2, [7], rooms=2, spo=["EB", "FS001"])
        f = o.row_fields(q)
        self.assertEqual(f["rate_source"], "Odeon contract")
        self.assertEqual(int(f["total_vnd"]), q["total_room"] * 2)
        self.assertEqual(int(f["Surcharge amount"]), q["net"]["child"] * 2)
        self.assertTrue(f["notes item 6"].startswith("6. Odeon contract: 2,200,000 × 11 night(s)"))
        self.assertIn(f"× 2 rooms = {o.money(q['total'])}", f["notes item 6"])


class OtherOperatorsTest(unittest.TestCase):
    def test_fun_and_sun_has_no_contract(self):
        with self.assertRaises(o.RateError) as e:
            o.load("Fun and Sun")
        self.assertIn("Karen", str(e.exception))

    def test_spo_refused_for_operators_without_codes(self):
        data = dict(o.load("Odeon"), spo=None, operator="Pegas")
        with self.assertRaises(o.RateError):
            o.price("Pegas", date(2026, 11, 20), date(2026, 11, 22), "STD", 2, booked=date(2026, 9, 1),
                    spo=["EB"], data=data)


if __name__ == "__main__":
    unittest.main()
