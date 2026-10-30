"""Offline tests for tools/operator_rates.py against the real docs/rate-knowledge/crystalbay-rates.json."""
import unittest
from datetime import date

from tools import operator_rates as o


def cb(arr, dep, room, adults, kids=(), booked=date(2026, 10, 25), **kw):
    return o.price("Crystal Bay", arr, dep, room, adults, list(kids), booked=booked, **kw)


class CrystalBayTest(unittest.TestCase):
    def test_seasons(self):
        q = cb(date(2026, 10, 31), date(2026, 11, 2), "STD", 2, booked=date(2026, 10, 1))
        self.assertEqual([n["season"] for n in q["nights"]], ["normal", "high"])
        self.assertEqual(q["gross"]["room"], 1250000 + 1900000)

    def test_holiday_child_breakfast_rate(self):
        q = cb(date(2026, 12, 24), date(2026, 12, 25), "STD", 2, [7], booked=date(2026, 12, 1))
        self.assertEqual(q["nights"][0]["season"], "holiday")
        self.assertEqual(q["gross"]["child"], 450000)
        q = cb(date(2026, 12, 24), date(2026, 12, 25), "STD", 2, [4], booked=date(2026, 12, 1))
        self.assertEqual(q["gross"]["child"], 250000)

    def test_one_adult_one_child_is_the_double_rate(self):
        q = cb(date(2026, 11, 20), date(2026, 11, 22), "STD", 1, [8])
        self.assertEqual((q["gross"]["child"], q["total"]), (0, 1900000 * 2))

    def test_eb_applies_on_holidays_room_only(self):
        q = cb(date(2026, 12, 24), date(2026, 12, 27), "STD", 2, [7], booked=date(2026, 10, 1))  # 84 days
        self.assertEqual(q["net"]["room"], round(2450000 * 0.85) * 3)
        self.assertEqual(q["net"]["child"], 450000 * 3)

    def test_bonus_night_includes_child_surcharge(self):
        q = cb(date(2026, 11, 20), date(2026, 11, 30), "STD", 2, [7], booked=date(2026, 11, 1))  # 19 days: no EB
        self.assertEqual(q["net"]["room"], 1900000 * 9)
        self.assertEqual(q["net"]["child"], 300000 * 9)
        self.assertEqual(q["release_days"], 21)

    def test_release_normal_season(self):
        q = cb(date(2027, 3, 20), date(2027, 3, 22), "STD", 2, booked=date(2027, 3, 12))
        self.assertEqual((q["release_days"], q["inside_release"]), (10, False))


if __name__ == "__main__":
    unittest.main()
