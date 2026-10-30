"""Offline tests for tools/quote.py against the real docs/rate-knowledge/ta-rates.json."""
import unittest
from datetime import date

from tools import quote as q


def opts(result):
    return dict(result["options"])


class SeasonTest(unittest.TestCase):
    def test_seasons_and_holidays_per_night(self):
        nights, gaps = q.nights(date(2026, 4, 29), date(2026, 5, 3), q.load())
        self.assertEqual([(d.day, s) for d, s, _ in nights], [(29, "normal"), (30, "holiday"), (1, "holiday"), (2, "normal")])
        self.assertEqual([g for g in gaps if "holiday dates" in g], [])

    def test_2027_beyond_known_holidays_is_a_gap(self):
        _, gaps = q.nights(date(2027, 2, 5), date(2027, 2, 8), q.load())
        self.assertTrue(any("Karen must confirm" in g for g in gaps))


class QuoteTest(unittest.TestCase):
    def test_sample_inquiry_as_asked(self):
        # test/emails/08-inquiry-en.txt: 3 rooms 2 adults + 1 room 2 adults and a 13-year-old (= adult)
        r = q.quote(date(2027, 1, 10), date(2027, 1, 14), 8, [13], alloc={"STD": 3, "TPL": 1})
        o = opts(r)["as asked"]
        self.assertEqual(o["room_total"], (1700000 * 3 + 2300000) * 4)
        self.assertEqual(o["child_surcharge"], 0)
        self.assertTrue(any("availability" in g for g in r["gaps"]))

    def test_family_two_kids_goes_triple_not_two_doubles(self):
        # 2 adults + 7 and 2 years: one double takes only 1 child -> a Triple (7yo in a bed, 2yo free)
        r = q.quote(date(2026, 11, 20), date(2026, 11, 22), 2, [7, 2])
        o = opts(r)["cheapest"]
        self.assertEqual(o["alloc"], {"TPL": 1})
        self.assertEqual(o["kids_as_persons"], [7])
        self.assertEqual(o["child_surcharge"], 0)
        self.assertEqual(o["total"], 2300000 * 2)

    def test_child_sharing_bed_is_charged_holiday_rate(self):
        r = q.quote(date(2026, 12, 24), date(2026, 12, 26), 2, [5], alloc={"DLX-SV": 1})
        o = opts(r)["as asked"]
        self.assertEqual(o["child_surcharge"], 400000 * 2)
        self.assertEqual(o["room_total"], 2600000 * 2)

    def test_under_three_free(self):
        o = opts(q.quote(date(2026, 11, 20), date(2026, 11, 22), 2, [2], alloc={"STD": 1}))["as asked"]
        self.assertEqual((o["child_surcharge"], o["total"]), (0, 1700000 * 2))

    def test_one_night_surcharge(self):
        o = opts(q.quote(date(2026, 10, 20), date(2026, 10, 21), 2, alloc={"STD": 1}))["as asked"]
        self.assertEqual(o["one_night_surcharge"], 250000 * 2)

    def test_indian_plus_20_on_rooms_only(self):
        o = opts(q.quote(date(2027, 1, 4), date(2027, 1, 6), 2, [4], alloc={"DLX-SV": 1}, indian=True))["as asked"]
        self.assertEqual(o["room_total"], 2400000 * 2)  # TA example Thu1230: 2,000,000 +20% = 2,400,000
        self.assertEqual(o["child_surcharge"], 350000 * 2)

    def test_roh_over_15_doubles(self):
        r = q.quote(date(2026, 10, 10), date(2026, 10, 12), 32, alloc={"DLX-SV": 16})
        o = opts(r)["as asked"]
        self.assertTrue(o["roh"])
        self.assertEqual(o["room_total"], 1050000 * 16 * 2)

    def test_room_count_and_refusals(self):
        r = q.quote(date(2026, 11, 20), date(2026, 11, 22), 4, rooms=2)
        self.assertTrue(all(o["room_count"] == 2 for _, o in r["options"]))
        for kwargs in ({"alloc": {"TW-DLX": 1}}, {"alloc": {"STD": 1}}, {"room_type": "APT"}):
            with self.assertRaises(q.QuoteError):
                q.quote(date(2026, 11, 20), date(2026, 11, 22), 3, **kwargs)
        with self.assertRaises(q.QuoteError):
            q.quote(date(2026, 11, 22), date(2026, 11, 20), 2)

    def test_render_has_totals_and_gaps(self):
        text = q.render(q.quote(date(2026, 11, 20), date(2026, 11, 22), 2, [7]))
        self.assertIn("deposit 50%", text)
        self.assertIn("GAP: availability", text)
        self.assertNotIn("OUT OF DATE", text)  # Karen: the 2026 TA table runs on into 2027


class DirectTest(unittest.TestCase):
    def setUp(self):
        self.data = q.load_channel("Direct")

    def test_rates_child_and_holiday_from_the_direct_pdf(self):
        o = opts(q.quote(date(2026, 4, 29), date(2026, 5, 1), 2, [5], alloc={"STD": 1}, data=self.data))["as asked"]
        self.assertEqual(o["room_total"], 2150000 + 2800000)  # 29/4 normal, 30/4 holiday (TA holiday list)
        self.assertEqual(o["child_surcharge"], 350000 + 500000)
        self.assertEqual(o["one_night_surcharge"], 0)

    def test_no_ta_rules(self):
        o = opts(q.quote(date(2026, 4, 10), date(2026, 4, 11), 32, alloc={"DLX-SV": 16},
                         indian=True, data=self.data))["as asked"]
        self.assertFalse(o["roh"])
        self.assertEqual(o["room_total"], 3000000 * 16)  # no ROH, no +20%, no 1-night surcharge
        self.assertEqual(o["one_night_surcharge"], 0)

    def test_out_of_date_and_full_payment_in_render(self):
        text = q.render(q.quote(date(2026, 11, 20), date(2026, 11, 22), 2, data=self.data))
        self.assertIn("RATES OUT OF DATE", text)
        self.assertIn("100% before check-in", text)
        self.assertNotIn("deposit 50%", text)
        inside = q.render(q.quote(date(2026, 4, 10), date(2026, 4, 12), 2, data=self.data))
        self.assertNotIn("OUT OF DATE", inside)

    def test_rooms_not_on_the_direct_table(self):
        with self.assertRaises(q.QuoteError):
            q.quote(date(2026, 4, 10), date(2026, 4, 12), 2, alloc={"TW-DLX": 1}, data=self.data)
        with self.assertRaises(q.QuoteError):
            q.load_channel("OTA")


if __name__ == "__main__":
    unittest.main()
