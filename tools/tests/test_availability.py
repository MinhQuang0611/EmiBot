"""Future Availability sheet (dev, 2026-10-27): rooms free per room type per night, 0 = none left."""
import unittest
from datetime import date
from types import SimpleNamespace
from unittest import mock

from tools import availability as avail
from tools import emi

TITLE = "Future Availability — HAYA — 2026-12-30_2027-02-23"
ROWS = [
    ["Room Type", "Number Of Rooms", "30/12 Wednesday", "31/12 Thursday", "01/01 Friday", "02/01 Saturday"],
    ["STD - STANDARD GARDEN", "10", "2", "0", "1", "3"],
    ["DLX-SV - DELUXE SEAVIEW", "20", "5", "4", "6", "6"],
    ["TPL-SV - TRIPLE - PARTIAL SV", "6", "-1", "2", "2", "2"],
    ["Total Availability Rooms", "85", "9", "18", "20", "36"],
    ["Summary"],
    ["Sellable Rooms", "(4)=(1)-(2)", "84", "84", "84", "84"],
    ["Occupancy %", "-11", "89.29%", "45.00%", "30.00%", "57.14%"],
]


def data():
    return avail.parse(TITLE, ROWS)


class ParseTest(unittest.TestCase):
    def test_room_rows_and_year_rollover(self):
        d = data()
        self.assertEqual(d["dates"], [date(2026, 12, 30), date(2026, 12, 31), date(2027, 1, 1), date(2027, 1, 2)])
        self.assertEqual(sorted(d["rooms"]), ["DLX-SV", "STD", "TPL-SV"])
        self.assertEqual(d["rooms"]["TPL-SV"]["name"], "TRIPLE - PARTIAL SV")
        self.assertEqual(d["occupancy"][date(2026, 12, 30)], 89.29)

    def test_title_without_window_refused(self):
        with self.assertRaises(avail.AvailabilityError):
            avail.parse("Future Availability", ROWS)


class CheckTest(unittest.TestCase):
    def test_zero_and_overbooked_are_none_left(self):
        r = avail.check(data(), date(2026, 12, 30), date(2027, 1, 2), today=date(2026, 12, 29))
        self.assertEqual(r["rooms"]["STD"]["none_left"], [date(2026, 12, 31)])
        self.assertEqual(r["rooms"]["TPL-SV"]["none_left"], [date(2026, 12, 30)])
        self.assertEqual(r["rooms"]["DLX-SV"]["min_free"], 4)
        self.assertEqual(avail.fits(r, {"DLX-SV": 4}), [])
        self.assertIn("only 4 free", avail.fits(r, {"DLX-SV": 5})[0])
        self.assertIn("none left on 31/12", avail.fits(r, {"STD": 1})[0])

    def test_stop_sale_only_more_than_14_days_ahead(self):
        stay = (date(2026, 12, 30), date(2027, 1, 1))
        self.assertEqual(avail.check(data(), *stay, today=date(2026, 12, 20))["stop_sale"], [])
        self.assertEqual(avail.check(data(), *stay, today=date(2026, 12, 1))["stop_sale"], [date(2026, 12, 30)])

    def test_outside_the_window_refused(self):
        with self.assertRaises(avail.AvailabilityError) as e:
            avail.check(data(), date(2027, 1, 2), date(2027, 1, 4), today=date(2026, 12, 1))
        self.assertIn("03/01/2027", str(e.exception))


class UpgradeTest(unittest.TestCase):
    """Dev 05/11, Celia Li: a sea-view upgrade is checked on the sheet and priced from the rate table."""
    def setUp(self):
        for name, value in (("_today_vn", date(2026, 12, 29)), ("_stale", None)):
            patcher = mock.patch.object(emi, name, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def run_it(self, data_=None, **kw):
        base = dict(arrival="30/12/2026", departure="01/01/2027", booked="STD", adults=2, rooms=1, children="",
                    indian=False, channel="TA")
        lines = []
        emi.run_upgrade(SimpleNamespace(**{**base, **kw}), data() if data_ is None else data_, out=lines.append)
        return "\n".join(lines)

    def rates(self, channel="TA"):
        from tools import quote as quoting
        rooms = {r["code"]: r["rates"] for r in quoting.load_channel(channel)["rooms"]}
        return rooms

    def test_free_type_shows_the_difference_a_full_type_none(self):
        text = self.run_it()
        self.assertIn("OPTION DLX-SV", text)
        self.assertRegex(text, r"DLX-SV [^\n]*AVAILABLE \| surcharge [\d.,]+ VND × 2 night\(s\) × 1 room\(s\) = ")
        self.assertRegex(text, r"SUITE-SV [^\n]*NOT AVAILABLE — SUITE-SV: not on the availability sheet")

    def test_more_rooms_than_are_free(self):
        self.assertIn("6 asked, only 4 free", self.run_it(rooms=6, adults=12))

    def test_nothing_free_says_so(self):
        full = avail.parse(TITLE, ROWS[:2] + [["DLX-SV - DELUXE SEAVIEW", "20", "0", "0", "0", "0"]] + ROWS[3:])
        self.assertIn("NO SEA VIEW FREE", self.run_it(full))

    def test_ota_uses_the_ta_card(self):
        self.assertEqual(self.run_it(channel="OTA").split("\n")[1:], self.run_it().split("\n")[1:])
        self.assertIn("the OTA has no table", self.run_it(channel="OTA"))

    def test_direct_uses_its_own_table(self):
        self.assertIn("direct-guest", self.run_it(channel="Direct"))

    def test_stale_sheet_is_not_a_promise(self):
        with mock.patch.object(emi, "_stale", return_value="3 days old"):
            text = self.run_it()
        self.assertIn("NOT VERIFIED", text)
        self.assertIn("AVAILABILITY STALE", text)
        self.assertNotIn("NO SEA VIEW FREE", text)

    def test_tour_operator_goes_to_karen(self):
        with self.assertRaises(emi.Refused):
            self.run_it(channel="Tour operator")

    def test_booked_sea_view_is_not_offered_again(self):
        self.assertNotIn("OPTION DLX-SV", self.run_it(booked="DLX-SV"))


class QuoteWithAvailabilityTest(unittest.TestCase):
    def setUp(self):
        # the day before the stay: no stop-sale unless a test says otherwise
        patcher = mock.patch.object(emi, "_today_vn", return_value=date(2026, 12, 29))
        patcher.start()
        self.addCleanup(patcher.stop)

    def args(self, **kw):
        base = dict(channel="TA", children="", alloc=None, arrival="30/12/2026", departure="01/01/2027", adults=2,
                    rooms=None, room_type=None, twin=False, indian=False)
        return SimpleNamespace(**{**base, **kw})

    def test_each_option_says_whether_it_is_free(self):
        lines = []
        q = emi.run_quote(self.args(alloc="STD:1"), out=lines.append, availability=data())
        text = "\n".join(lines)
        self.assertIn("OPTION as asked: NOT AVAILABLE — STD: none left on 31/12", text)
        self.assertFalse(any(g.startswith("availability") for g in q["gaps"]))
        lines = []
        emi.run_quote(self.args(alloc="DLX-SV:1"), out=lines.append, availability=data())
        self.assertIn("OPTION as asked: AVAILABLE", "\n".join(lines))

    def test_stop_sale_is_not_available(self):
        lines = []
        with mock.patch.object(emi, "_today_vn", return_value=date(2026, 12, 1)):
            emi.run_quote(self.args(alloc="DLX-SV:1"), out=lines.append, availability=data())
        self.assertIn("OPTION as asked: NOT AVAILABLE — stop-sale on 30/12", "\n".join(lines))

    def test_without_the_sheet_the_gap_stays(self):
        lines = []
        emi.run_quote(self.args(), out=lines.append)
        self.assertIn("GAP: availability", "\n".join(lines))


if __name__ == "__main__":
    unittest.main()
