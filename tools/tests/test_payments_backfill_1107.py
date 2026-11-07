"""payments-due and the EZFOLIO backfill (dev, 2026-11-07). The 05/11 19:46 backfill (RER004, EXISTING BOOKING rows,
no COD, no payment columns) put 58 bookings into job 3: a deposit reminder to Ohmyhotel for a deadline of 29/06
(V26062610072H01, draft #613), reminders to MG and Mytour (OTAs written as "TA"), and ~40 "no confirmation found"
lines. Same run: RHK BG15963 shown unpaid after a 19,400,000 deposit, Threeland 31-130127's extension not read."""
import os
import unittest
from datetime import datetime

from tools import payments
from tools.state import State
from tools.tests.test_payments import FakeMail, VN, due, row


def backfill(n, **kw):
    base = dict(action="EXISTING BOOKING", received_at="05/11/2026 19:46", company="Worldwide Gateway DMC",
                booking_ref="WWGDMC_VN_261115", ezfolio_group_code="30742", **{"Remaining amount": "", "COD": ""},
                source_email="RER004 Reservation Booked backfill 05/11 (booking date 15/09/2026)")
    return row(n, **{**base, **kw})


NOW = datetime(2026, 11, 7, 15, 0, tzinfo=VN)


class BackfillTest(unittest.TestCase):
    def test_backfill_only_is_listed_not_chased(self):
        r = due([backfill(1405)], FakeMail(), now=NOW)
        self.assertEqual((r["remind"], r["no_confirmation"], r["overdue"]), ([], [], []))
        self.assertEqual([i["ref"] for i in r["backfill"]], ["WWGDMC_VN_261115"])
        self.assertIn("NOT CHASED, BACKFILL ONLY: 1", payments.render(r, NOW))

    def test_ota_written_as_ta_is_not_even_listed(self):
        rows = [backfill(1443, company="CÔNG TY TNHH OHMYHOTEL&CO VN", booking_ref="V26062610072H01"),
                backfill(1355, company="MG", booking_ref="AGIN0116572610356183", ezfolio_group_code="29458")]
        r = due(rows, FakeMail(), now=NOW)
        self.assertEqual(sum(len(b) for b in r.values()), 0)
        self.assertNotIn("BACKFILL", payments.render(r, NOW))

    def test_backfill_after_own_rows_does_not_hide_them(self):
        # Mytour H6844730: NEW row 48 says OTA prepaid; the backfill row 1391 after it says "TA"
        rows = [row(48, channel_type="OTA", company="Mytour (VNTravel)", booking_ref="H6844730 / MT1406527499",
                    COD="N/A (OTA prepaid)"),
                backfill(1391, company="MY TOUR", booking_ref="H6844730")]
        r = due(rows, FakeMail(), now=NOW)
        self.assertEqual(sum(len(b) for b in r.values()), 0)

    def test_own_change_after_backfill_is_chased_from_its_own_rows(self):
        # Travel Indochina RRH171126-ANDREW01: backfill, then Emi's CHANGE with Remaining written
        rows = [backfill(1418, company="TRAVEL INDOCHINA VIETNAM", booking_ref="RRH171126-ANDREW01"),
                row(1659, action="CHANGE", received_at="07/11/2026 13:57", company="TRAVEL INDOCHINA VIETNAM",
                    booking_ref="RRH171126-ANDREW01", **{"Remaining amount": "18000000"})]
        r = due(rows, FakeMail(sent_at="2026-11-04T03:00:00Z"), now=NOW)
        self.assertEqual([(i["ref"], i["row"]) for i in r["remind"]], [("RRH171126-ANDREW01", 1659)])
        self.assertEqual(r["backfill"], [])

    def test_ota_company_on_an_own_ta_row_is_not_chased(self):
        r = due([row(5, company="CÔNG TY TNHH OHMYHOTEL&CO VN")], FakeMail(), now=NOW)
        self.assertEqual(r["remind"], [])

    def test_ota_company_names(self):
        for name in ("MG", "MY TOUR", "DIDA TOUR", "CÔNG TY TNHH OHMYHOTEL&CO VN", "Agoda Company Pte Ltd"):
            self.assertTrue(payments.ota_company(name), name)
        for name in ("Worldwide Gateway DMC", "Threeland Travel", "CTY VICTORIA", "Asian Classic Travels", ""):
            self.assertFalse(payments.ota_company(name), name)


class PaidTest(unittest.TestCase):
    def test_an_earlier_emails_total_less_remaining_counts(self):
        # RHK BG15963: 28/10 rows 40,200,000 with 20,800,000 left; 04/11 change 38,800,000, Remaining on one row only
        hits = [row(688, action="CHANGE", received_at="28/10/2026 07:56", total_vnd="21800000",
                    **{"Remaining amount": "2400000"}),
                row(689, action="CHANGE", received_at="28/10/2026 07:56", total_vnd="18400000",
                    **{"Remaining amount": "18400000"}),
                row(1174, action="CHANGE", received_at="04/11/2026 17:24", total_vnd="20400000",
                    **{"Remaining amount": "19400000"}),
                row(1175, action="CHANGE", received_at="04/11/2026 17:24", total_vnd="18400000",
                    **{"Remaining amount": ""})]
        self.assertEqual(payments.paid_of(hits, hits[2:]), 19400000)

    def test_a_cancel_rows_zero_remaining_is_not_a_payment(self):
        hits = [row(634, action="CANCEL", received_at="26/10/2026 20:15", **{"Remaining amount": "0"}),
                row(635, received_at="26/10/2026 20:15")]
        self.assertEqual(payments.paid_of(hits, hits[1:]), 0)


class OldExtensionTest(unittest.TestCase):
    def test_deposit_deadline_extended_to_a_date(self):
        cod = "Deposit deadline extended to 12/11/2026 (agency request); prior SENT 06/11 12:19 still also restated"
        self.assertEqual(payments.fixed_deadline(cod), datetime(2026, 11, 12, 23, 59, tzinfo=VN))

    def test_threeland_is_not_overdue_before_its_new_deadline(self):
        st = State(os.devnull + "-none")
        cod = "Deposit deadline extended to 12/11/2026 (agency request)"
        r = due([row(1328, COD=cod)], FakeMail(), st=st, now=NOW)
        self.assertEqual((r["remind"], r["overdue"]), ([], []))


if __name__ == "__main__":
    unittest.main()
