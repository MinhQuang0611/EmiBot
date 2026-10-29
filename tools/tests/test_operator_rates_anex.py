"""Offline tests for tools/operator_rates.py against the real docs/rate-knowledge/anex-rates.json."""
import unittest
from datetime import date

from tools import operator_rates as o


def anex(arr, dep, room, adults, kids=(), booked=date(2026, 11, 1), **kw):
    return o.price("Anex", arr, dep, room, adults, list(kids), booked=booked, **kw)


class AnexTest(unittest.TestCase):
    def test_seasons(self):
        q = anex(date(2027, 2, 27), date(2027, 3, 2), "STD", 2, booked=date(2027, 2, 20))  # 7 days: no EB
        self.assertEqual([n["season"] for n in q["nights"]], ["high", "high", "low"])
        self.assertEqual(q["total"], 1900000 * 2 + 1250000)

    def test_holiday_nights(self):
        q = anex(date(2026, 12, 23), date(2026, 12, 25), "DLX-SV", 2, booked=date(2026, 12, 20))
        self.assertEqual([n["season"] for n in q["nights"]], ["high", "holiday"])
        self.assertEqual(q["total"], 2200000 + 2900000)
        self.assertEqual(q["release_days"], 21)

    def test_eb_tiers_room_only(self):
        for booked, pct in ((date(2026, 12, 1), 5), (date(2026, 11, 20), 10), (date(2026, 11, 1), 15)):
            q = anex(date(2027, 1, 10), date(2027, 1, 12), "STD", 2, [8], booked=booked)
            self.assertEqual(q["net"]["room"], round(1900000 * (100 - pct) / 100) * 2, pct)
            self.assertEqual(q["net"]["child"], 250000 * 2)  # breakfast surcharge not discounted

    def test_last_nights_free_multiplied_room_only(self):
        q = anex(date(2027, 2, 20), date(2027, 3, 12), "STD", 2, [7], booked=date(2027, 2, 15))
        free = [x for x in q["offers"] if x[0] == "free"][0]
        self.assertEqual(free[2], {"room": 1250000 * 2, "child": 0, "meal": 0})  # 10–11/03, low
        self.assertEqual(q["net"]["child"], 250000 * 20)

    def test_child_breakfast(self):
        d = (date(2027, 3, 10), date(2027, 3, 12))
        self.assertEqual(anex(*d, "STD", 1, [9])["gross"]["child"], 0)        # 1A+1C: double rate
        self.assertEqual(anex(*d, "STD", 2, [9])["gross"]["child"], 500000)   # 2A+1C 6–11.99: ABF
        self.assertEqual(anex(*d, "STD", 2, [4])["gross"]["child"], 0)        # 2A+1C 2–5.99: double rate
        self.assertEqual(anex(*d, "TPL", 3, [8])["gross"]["child"], 500000)   # 3A+1C 6–11.99: ABF
        self.assertEqual(anex(*d, "TPL", 2, [8, 9])["charged_kids"], [8])     # 2A+2C both 6–11: one ABF

    def test_hb_supplement_by_age(self):
        q = anex(date(2027, 3, 10), date(2027, 3, 11), "STD", 2, [4], meal="HB")
        self.assertEqual(q["gross"]["meal"], 600000 * 2 + 150000)

    def test_no_spo(self):
        with self.assertRaises(o.RateError):
            anex(date(2027, 3, 10), date(2027, 3, 12), "STD", 2, spo=["EB"])


if __name__ == "__main__":
    unittest.main()
