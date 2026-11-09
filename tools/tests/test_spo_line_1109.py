"""Odeon SGODOAMY4_11_1 (09/11): the voucher's SPOCode line "7 * (Contract Revise Rates)" has no C[...] offer, so
to-price took the whole line for an unknown code and the row went on the sheet with no rate."""
import unittest
from datetime import date

from tools import emi
from tools import operator_rates as o


class SpoLineTest(unittest.TestCase):
    def test_plain_contract_line_is_none(self):
        self.assertEqual(emi._spo("7 * (Contract Revise Rates)"), ["none"])
        self.assertEqual(emi._spo("10 * (Contract Revise Rates) + 3 * (Contract Revise Rates )"), ["none"])

    def test_lines_with_offers_untouched(self):
        line = "10 * (Contract Revise Rates(C[D45REB10%]) (C[S10P09]) ) + 3 * (Contract Revise Rates(C[S10P09]) )"
        self.assertEqual(emi._spo(line), [line])
        self.assertEqual(emi._spo("EB,FS001"), ["EB", "FS001"])
        self.assertEqual(emi._spo("none"), ["none"])
        self.assertIsNone(emi._spo(None))

    def test_unknown_code_still_stops(self):
        with self.assertRaises(o.RateError):
            o.price("Odeon", date(2026, 12, 10), date(2026, 12, 20), "DLX-SV", 2, [], booked=date(2026, 11, 4),
                    spo=emi._spo("7 * (Contract Revise Rates(C[X99]))"))

    def test_sgodoamy4_priced_at_the_contract(self):
        q = o.price("Odeon", date(2026, 11, 27), date(2026, 12, 4), "DLX-SV", 2, [], booked=date(2026, 11, 8),
                    spo=emi._spo("7 * (Contract Revise Rates)"))
        self.assertEqual(q["total"], 15400000)


if __name__ == "__main__":
    unittest.main()
