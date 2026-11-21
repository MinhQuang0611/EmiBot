"""Dev 21/11, live row 2521 (Turtle Adventure TA-08Jan2027-GGT06): HAYA quoted on 07/11, the agency answered on 13/11
"Vui lòng cung cấp số tài khoản để kế toán bên em cọc cho booking này". Emi replied with the bank account and asked
for names, no NEW row. The deposit of 21/11 went in as a CHANGE "original booking not on the sheet"; the build tool
found no group anywhere and stopped. Now: a reply giving the bank account needs a booking on the sheet, and a TA or
direct CHANGE with no group code, no confirmation number and no word of HAYA's confirmation is refused.
"""
import unittest
from types import SimpleNamespace
from unittest import mock

from tools import emi

TURTLE = "TA-08Jan2027-GGT06"
BANK_REPLY = ("Kính gửi chị Hoàng Lộc,\n\nThông tin tài khoản thanh toán:\n"
              "Tên tài khoản: CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC\nSố tài khoản: 1020729617\n"
              "Ngân hàng: Vietcombank, CN Phú Quốc\n\nTrân trọng,\nReservations Team")


class BankDetailsTest(unittest.TestCase):
    def test_bank_account_to_a_booking_not_on_the_sheet_is_refused(self):
        for ref in (TURTLE, ""):
            with self.assertRaises(emi.Refused) as c:
                emi.check_bank_details_booked(BANK_REPLY, "reply", ref, lambda: [])
            self.assertIn("NEW rows first", str(c.exception))
            self.assertIn("draft-confirmation --before-pdf", str(c.exception))

    def test_booking_on_the_sheet_passes(self):
        rows = [{"_row": 2521, "action": "NEW", "received_at": "21/11/2026 00:57", "booking_ref": TURTLE}]
        emi.check_bank_details_booked(BANK_REPLY, "reply", TURTLE, lambda: rows)

    def test_other_replies_and_kinds_untouched(self):
        never = lambda: self.fail("the sheet is read only when the account number is in the text")  # noqa: E731
        emi.check_bank_details_booked("Dear Ms Ho,\n\nThank you.", "reply", "", never)
        for kind in ("confirmation", "deposit_reminder", "balance_reminder", "cancellation"):
            emi.check_bank_details_booked(BANK_REPLY, kind, "", never)


class ChangeWithoutOriginalTest(unittest.TestCase):
    ROW = {"action": "CHANGE", "channel_type": "TA", "company": "Turtle Adventure", "booking_ref": TURTLE,
           "what_changed": "Payment 1 received 4,000,000",
           "missing_info": "original booking not on the sheet; ezfolio_group_code and confirmation_no not available"}

    def errors(self, **kw):
        sheet = SimpleNamespace(header=list(self.ROW) + ["ezfolio_group_code", "confirmation_no", "internal_notes"])
        with mock.patch.object(emi.schema, "room_codes", return_value=None), \
                mock.patch.object(emi.schema, "check_row", return_value=([], [])), \
                mock.patch.object(emi, "_earlier_arrivals", return_value={}):
            errors, _ = emi.check_rows(sheet, [dict(self.ROW, **kw)])
        return [e for e in errors if "Quote accepted" in e]

    def test_row_2521_refused(self):
        self.assertTrue(self.errors())
        self.assertTrue(self.errors(channel_type="Direct"))

    def test_haya_confirmation_shown_passes(self):
        self.assertFalse(self.errors(ezfolio_group_code="29575"))
        self.assertFalse(self.errors(confirmation_no="25100"))
        self.assertFalse(self.errors(internal_notes="HAYA confirmed on 02/10 (sales@ confirmation with PDF)"))

    def test_ota_and_operators_untouched(self):
        # an OTA booking reaches HAYA by SynXis before the sheet existed: no EZFOLIO proof in the thread is normal
        self.assertFalse(self.errors(channel_type="OTA"))
        self.assertFalse(self.errors(channel_type="Tour operator"))


if __name__ == "__main__":
    unittest.main()
