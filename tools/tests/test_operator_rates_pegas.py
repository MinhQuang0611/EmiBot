"""Offline tests for tools/operator_rates.py against the real docs/rate-knowledge/pegas-rates.json."""
import unittest
from datetime import date

from tools import operator_rates as o


def pegas(arr, dep, room, adults, kids=(), booked=date(2026, 9, 1), **kw):
    return o.price("Pegas", arr, dep, room, adults, list(kids), booked=booked, **kw)


class PegasTest(unittest.TestCase):
    def test_seasons_and_holidays(self):
        q = pegas(date(2026, 12, 22), date(2026, 12, 28), "STD", 2, booked=date(2026, 12, 1))
        self.assertEqual([n["season"] for n in q["nights"]],
                         ["high", "high", "holiday", "holiday", "holiday", "high"])
        self.assertEqual(q["release_days"], 21)

    def test_eb_room_only_from_november(self):
        # 50 days ahead -> 15%, room only; child surcharge untouched
        q = pegas(date(2026, 11, 20), date(2026, 11, 23), "STD", 2, [7], booked=date(2026, 10, 1))
        self.assertEqual(q["net"]["room"], round(1900000 * 0.85) * 3)
        self.assertEqual(q["net"]["child"], 300000 * 3)
        # October stay: outside the EB window
        q = pegas(date(2026, 10, 20), date(2026, 10, 23), "STD", 2, booked=date(2026, 8, 1))
        self.assertEqual(q["net"]["room"], 1900000 * 3)

    def test_single_bonus_night_not_multiplied_includes_meals(self):
        q = pegas(date(2027, 3, 1), date(2027, 3, 21), "TPL", 3, booked=date(2027, 2, 20), meal="HB")
        free = [x for x in q["offers"] if x[0] == "free"][0]
        self.assertEqual(free[2]["room"], 1800000)
        self.assertEqual(free[2]["meal"], 400000 * 3)
        self.assertEqual(q["net"]["meal"], 400000 * 3 * 19)

    def test_child_always_charged_infant_free(self):
        self.assertEqual(pegas(date(2026, 11, 20), date(2026, 11, 22), "STD", 1, [8])["gross"]["child"], 600000)
        self.assertEqual(pegas(date(2026, 11, 20), date(2026, 11, 22), "STD", 2, [2])["gross"]["child"], 0)
        q = pegas(date(2026, 11, 20), date(2026, 11, 22), "STD", 2, [8, 1])
        self.assertTrue(any("capacity" in g for g in q["gaps"]))

    def test_child_meal_half(self):
        q = pegas(date(2026, 11, 20), date(2026, 11, 22), "STD", 2, [5], meal="FB")
        self.assertEqual(q["gross"]["meal"], (800000 * 2 + 400000) * 2)

    def test_quad_normal_misprint_is_a_gap(self):
        q = pegas(date(2027, 3, 10), date(2027, 3, 12), "QPL", 4, booked=date(2027, 3, 1))
        self.assertEqual(q["gross"]["room"], 2590000 * 2)
        self.assertTrue(any("2,590,00 0" in g for g in q["gaps"]))

    def test_outside_contract(self):
        with self.assertRaises(o.RateError):
            pegas(date(2027, 4, 29), date(2027, 5, 2), "STD", 2)

    def test_no_spo(self):
        with self.assertRaises(o.RateError):
            pegas(date(2026, 11, 20), date(2026, 11, 22), "STD", 2, spo=["EB"])


if __name__ == "__main__":
    unittest.main()
