"""Deposit-deadline extension (dev, 2026-11-07): granted at once, 17:00 two days after the request, or the agency's
own sooner time; never shorter than the deadline they have. payments-due reads the new deadline from COD."""
import unittest
from datetime import date, datetime

from tools import emi, payments
from tools.payments import VN


def vn(d, m, h=0, mi=0):
    return datetime(2026, m, d, h, mi, tzinfo=VN)


class ExtensionDeadlineTest(unittest.TestCase):
    def test_saturday_request_gets_monday_17(self):
        when, _ = payments.extension_deadline(vn(7, 11, 10, 30))
        self.assertEqual(when, vn(9, 11, 17))

    def test_late_night_request_counts_from_its_own_day(self):
        when, _ = payments.extension_deadline(vn(7, 11, 23, 50))
        self.assertEqual(when, vn(9, 11, 17))

    def test_sooner_wish_is_granted_as_asked(self):
        when, why = payments.extension_deadline(vn(7, 11, 10), wanted=vn(8, 11, 12))
        self.assertEqual(when, vn(8, 11, 12))
        self.assertIn("asked for", why)

    def test_later_wish_is_capped_at_two_days(self):
        when, why = payments.extension_deadline(vn(7, 11, 10), wanted=vn(12, 11, 17))
        self.assertEqual(when, vn(9, 11, 17))
        self.assertIn("later than the limit", why)

    def test_never_shortens_the_current_deadline(self):
        when, why = payments.extension_deadline(vn(7, 11, 10), current=vn(9, 11, 20))
        self.assertEqual(when, vn(9, 11, 20))
        self.assertIn("nothing to move", why)


class CodTest(unittest.TestCase):
    COD = "Deposit extended to 09/11/2026 17:00 (asked 07/11); balance by 03/12/2026"

    def test_payments_due_reads_the_extended_deadline(self):
        self.assertEqual(payments.fixed_deadline(self.COD), vn(9, 11, 17))

    def test_balance_date_still_read(self):
        self.assertEqual(payments.balance_date(self.COD, date(2026, 12, 10)), date(2026, 12, 3))

    def test_the_48_hour_text_is_not_a_fixed_deadline(self):
        self.assertIsNone(payments.fixed_deadline("48h after confirmation is received (deposit 50%); balance by "
                                                  "03/12/2026"))


class CommandTest(unittest.TestCase):
    def run_cmd(self, *argv):
        lines = []
        args = emi.parser().parse_args(["deposit-extension", *argv])
        return emi.run_deposit_extension(args, out=lines.append), "\n".join(lines)

    def test_prints_cod_and_vietnamese_weekday(self):
        when, text = self.run_cmd("--asked", "07/11/2026 10:30", "--balance-by", "03/12/2026")
        self.assertEqual(when, vn(9, 11, 17))
        self.assertIn("COD: Deposit extended to 09/11/2026 17:00 (asked 07/11); balance by 03/12/2026", text)
        self.assertIn("trước 17:00 thứ Hai ngày 09/11/2026 (giờ Việt Nam, UTC+7)", text)

    def test_date_only_wish_means_17h(self):
        when, _ = self.run_cmd("--asked", "07/11/2026 08:00", "--wanted", "08/11/2026")
        self.assertEqual(when, vn(8, 11, 17))

    def test_bad_time_refused(self):
        with self.assertRaises(emi.Refused):
            self.run_cmd("--asked", "Monday")


if __name__ == "__main__":
    unittest.main()
