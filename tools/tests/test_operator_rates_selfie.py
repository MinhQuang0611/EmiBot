"""Offline tests for tools/operator_rates.py against the real docs/rate-knowledge/selfie-rates.json."""
import unittest
from datetime import date

from tools import operator_rates as o


def selfie(arr, dep, room, adults, kids=(), booked=date(2026, 9, 1), **kw):
    return o.price("Selfie", arr, dep, room, adults, list(kids), booked=booked, **kw)


class SelfieTest(unittest.TestCase):
    def test_seasons_and_holiday(self):
        q = selfie(date(2026, 10, 30), date(2026, 11, 2), "STD", 2, booked=date(2026, 10, 10))
        self.assertEqual([n["season"] for n in q["nights"]], ["low", "low", "high"])
        q = selfie(date(2027, 4, 29), date(2027, 5, 2), "STD", 2, booked=date(2027, 4, 1))
        self.assertEqual([n["season"] for n in q["nights"]], ["low", "holiday", "holiday"])

    def test_eb_on_room_only(self):
        # 80 days ahead -> 15% off the room, the child's breakfast unchanged
        q = selfie(date(2026, 11, 20), date(2026, 11, 23), "DLX-SV", 2, [7])
        self.assertEqual(q["net"]["room"], round(2200000 * 0.85) * 3)
        self.assertEqual(q["net"]["child"], 250000 * 3)
        q = selfie(date(2026, 11, 20), date(2026, 11, 23), "STD", 2, booked=date(2026, 10, 15))
        self.assertEqual(q["net"]["room"], round(1900000 * 0.9) * 3)  # 36 days -> 10%

    def test_child_breakfast(self):
        self.assertEqual(selfie(date(2026, 11, 20), date(2026, 11, 22), "STD", 1, [8])["gross"]["child"], 0)
        self.assertEqual(selfie(date(2026, 11, 20), date(2026, 11, 22), "STD", 2, [4])["gross"]["child"], 200000)
        self.assertEqual(selfie(date(2026, 11, 20), date(2026, 11, 22), "STD", 2, [2])["gross"]["child"], 0)
        self.assertEqual(selfie(date(2026, 11, 20), date(2026, 11, 22), "STD", 2, [1])["infants"], [1])

    def test_single_bonus_night_not_multiplied(self):
        q = selfie(date(2027, 3, 1), date(2027, 3, 21), "STD", 2, booked=date(2027, 2, 25))  # 20 nights, no EB
        free = [x for x in q["offers"] if x[0] == "free"][0]
        self.assertEqual(free[2]["room"], 1900000)
        self.assertEqual(q["net"]["room"], 1900000 * 19)

    def test_bonus_night_includes_meals_and_cheapest(self):
        # 25/3–4/4: 7 high + 3 low nights; the free night is a low one, its HB too
        q = selfie(date(2027, 3, 25), date(2027, 4, 4), "STD", 2, booked=date(2027, 3, 20), meal="HB")
        free = [x for x in q["offers"] if x[0] == "free"][0]
        self.assertEqual(free[2]["room"], 1250000)
        self.assertEqual(free[2]["meal"], 600000 * 2)

    def test_eb_with_bonus_night_is_a_gap(self):
        q = selfie(date(2026, 11, 20), date(2026, 11, 30), "STD", 2)
        self.assertEqual(q["net"]["room"], round(1900000 * 0.85) * 9)
        self.assertTrue(any("combines with the free night" in g for g in q["gaps"]))
        self.assertTrue(any("stop-sale" in g for g in q["gaps"]))
        self.assertTrue(any("HAYA signature" in g for g in q["gaps"]))

    def test_release_14_days(self):
        q = selfie(date(2026, 12, 24), date(2026, 12, 26), "STD", 2, booked=date(2026, 12, 15))
        self.assertEqual((q["release_days"], q["inside_release"]), (14, False))

    def test_no_spo(self):
        with self.assertRaises(o.RateError):
            selfie(date(2026, 11, 20), date(2026, 11, 22), "STD", 2, spo=["EB"])


if __name__ == "__main__":
    unittest.main()
