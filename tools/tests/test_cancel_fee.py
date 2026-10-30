"""Offline tests for tools/cancel_fee.py against the real ta-rates.json."""
import unittest
from datetime import datetime

from tools import cancel_fee as cf


def row(**kw):
    base = {"action": "NEW", "channel_type": "TA", "company": "TEST Travel", "booking_ref": "TEST-1511",
            "arrival": "05/12/2026", "departure": "08/12/2026", "received_at": "15/10/2026 14:05"}
    return {**base, **kw}


ROWS = [row(_row=50, room_code="DLX-SV", rooms="1", **{"Average rate per night after discount": "2000000"}),
        row(_row=51, room_code="SUP-DBL", rooms="2", **{"Average rate per night after discount": "1900000"})]


def at(s):
    return datetime.strptime(s, "%d/%m/%Y %H:%M")


class CancelFeeTest(unittest.TestCase):
    def test_tiers_normal_season(self):
        cases = [("15/10/2026 10:00", 0), ("01/12/2026 09:00", 5800000), ("02/12/2026 09:00", 5800000),
                 ("03/12/2026 23:00", 8700000), ("05/12/2026 08:00", 8700000)]
        for when, fee in cases:
            self.assertEqual(cf.cancel_fee(ROWS, at(when))["fee"], fee, when)

    def test_exactly_seven_days_is_left_to_karen(self):
        c = cf.cancel_fee(ROWS, at("28/11/2026 09:00"))
        self.assertIsNone(c["fee"])
        self.assertIn("either 0 VND", c["how"])
        self.assertIn("5.800.000", c["how"])
        self.assertTrue(any("Karen decides" in g for g in c["gaps"]))

    def test_holiday_stay_uses_holiday_column(self):
        rows = [row(arrival="23/12/2026", departure="26/12/2026", room_code="STD", rooms="1",
                    **{"Average rate per night after discount": "2000000"})]
        c = cf.cancel_fee(rows, at("01/12/2026 09:00"))   # 22 days out, holiday column: 50%
        self.assertEqual(c["fee"], 2000000 * 3 // 2)
        self.assertTrue(c["holiday"])

    def test_no_show_full_charge(self):
        self.assertEqual(cf.cancel_fee(ROWS, at("05/12/2026 20:00"), no_show=True)["fee"], 17400000)

    def test_latest_change_rows_replace_new_rows(self):
        change = row(action="CHANGE", received_at="20/10/2026 09:00", room_code="STD", rooms="1",
                     **{"Average rate per night after discount": "1700000"})
        c = cf.cancel_fee(ROWS + [change, row(action="CANCEL", received_at="21/10/2026 09:00")],
                          at("01/12/2026 09:00"))
        self.assertEqual(c["fee"], 1700000)

    def test_payments_counted_once_and_compared(self):
        paid = {"Payment 1": "8700000", "Payment 1 date + time": "16/10/2026 10:00"}
        rows = [dict(ROWS[0], **paid), dict(ROWS[1], **paid)]
        c = cf.cancel_fee(rows, at("01/12/2026 09:00"))
        self.assertEqual(c["paid_total"], 8700000)
        self.assertIn("paid − charge = 2.900.000", cf.render(c))

    def test_refusals(self):
        with self.assertRaises(cf.CancelFeeError):
            cf.cancel_fee([row(channel_type="Tour operator", company="Pegas")], at("01/11/2026 09:00"))
        with self.assertRaises(cf.CancelFeeError):
            cf.cancel_fee(ROWS, at("06/12/2026 09:00"))
        with self.assertRaises(cf.CancelFeeError):
            cf.cancel_fee([row(action="CANCEL")], at("01/11/2026 09:00"))


if __name__ == "__main__":
    unittest.main()
