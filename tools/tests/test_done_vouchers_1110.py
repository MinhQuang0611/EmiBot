"""done refuses an email whose attached voucher was never written (dev, 2026-11-10): front office's 05/11 17:47 email
carried two Odeon vouchers; on 08/11 Emi wrote row 1710 for 4799222 and marked the email done with "SGODOAMY4_11_1
voucher PDF missing", so OV613LLPX_11_1 had no row until Odeon's reminder made one with guests TBA."""
import os
import tempfile
import unittest

from tools import attachments, emi
from tools.tests.test_attachments_pdf import pdf

# As pypdf reads Odeon's extranet print on the host (show, 10/11).
ODEON_4799222 = """Reservation Date 04.11.2026 17:28:08
VoucherNo 1151155 Reference No 1238448
Operator Voucher No 4799222 ProviderReservationNo
Market Poland Operator Coral Travel Poland
SPOCode 10 * (Contract Revise Rates(C[D30REB5%]) (C[S10P09]) )
Reservation 4799222 - HAYA HOTEL PHU QUOC"""
ODEON_OV613 = """Reservation Date 03.11.2026 17:34:29
VoucherNo 1151077 Reference No 1238366
Operator Voucher No OV613LLPX_11_1 ProviderReservationNo
Market Global Operator Odeonbeds All Market
SPOCode 10 * (Contract Revise Rates(C[D45REB10%]) (C[S10P09]) ) + 3 * (Contract Revise Rates(C[S10P09]) )
Reservation OV613LLPX_11_1 - HAYA HOTEL PHU QUOC"""
F1 = "hotelextranet.odeontours.com_Accommodation_HotelExtranet_PrintReservation_IDs=8649178.pdf"
F2 = "hotelextranet.odeontours.com_Accommodation_HotelExtranet_PrintReservation_IDs=8646781.pdf"
ROW_1710 = {"booking_ref": "Odeon 4799222 (Coral Travel Poland; Voucher 1151155; Ref 1238448)"}
ROW_1777 = {"booking_ref": "OV613LLPX_11_1"}


class VouchersInTest(unittest.TestCase):
    def test_odeon_print(self):
        self.assertEqual(emi.vouchers_in(F2, ODEON_OV613), [("Odeon", "OV613LLPX_11_1", ["1151077", "1238366"])])
        self.assertEqual(emi.vouchers_in(F1, ODEON_4799222), [("Odeon", "4799222", ["1151155", "1238448"])])

    def test_label_next_to_the_field_is_not_a_ref(self):
        self.assertEqual(emi.vouchers_in("x.pdf", "Operator Voucher No ProviderReservationNo\nOV613LLPX_11_1"), [])

    def test_other_files_have_none(self):
        self.assertEqual(emi.vouchers_in("slip.pdf", "UNC 1020729617 so tien 5,000,000"), [])


class DoneCheckTest(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.mkdtemp()
        emi._write_index(self.work, {"id": "fo-0511"}, [{"name": F1, "text": ODEON_4799222},
                                                         {"name": F2, "text": ODEON_OV613}])
        self.loads = 0

    def rows(self, rows):
        def load():
            self.loads += 1
            return rows
        return load

    def check(self, outcome, rows):
        lines = []
        emi.check_vouchers_handled("fo-0511", outcome, self.rows(rows), work_dir=self.work, out=lines.append)
        return "\n".join(lines)

    def test_the_08_11_run_is_refused(self):
        with self.assertRaises(emi.Refused) as e:
            self.check("Odeon 4799222 logged row 1710; SGODOAMY4_11_1 voucher PDF missing, E-331", [ROW_1710])
        self.assertIn("VOUCHER NOT HANDLED: Odeon OV613LLPX_11_1", str(e.exception))
        self.assertIn(F2, str(e.exception))
        self.assertNotIn("4799222 (", str(e.exception))

    def test_both_on_the_sheet(self):
        self.check("both vouchers logged", [ROW_1710, ROW_1777])

    def test_named_in_the_outcome_no_sheet_read(self):
        self.check("4799222 row 1710; OV613LLPX_11_1 asked Karen E-274", [])
        self.assertEqual(self.loads, 0)

    def test_voucher_number_in_the_outcome_counts(self):
        self.check("row 1710; voucher 1151077 duplicate of row 1777", [ROW_1710])

    def test_sheet_unreadable_outcome_only(self):
        with self.assertRaises(emi.Refused):
            self.check("Odeon 4799222 logged row 1710", None)
        self.check("4799222 row 1710, OV613LLPX_11_1 row 1791", None)

    def test_email_without_files_passes(self):
        emi.check_vouchers_handled("no-files", "inquiry answered", self.rows([]), work_dir=self.work)
        self.assertEqual(self.loads, 0)

    def test_files_saved_by_an_older_show_are_read(self):
        # emails shown before 10/11 have their PDFs in emi-work but no index
        folder = attachments.message_dir(self.work, "old-email")
        os.makedirs(folder)
        with open(os.path.join(folder, "v.pdf"), "wb") as f:
            f.write(pdf(b"BT /F1 12 Tf 20 100 Td (Operator Voucher No OV613LLPX_11_1 ProviderReservationNo) Tj ET"))
        with self.assertRaises(emi.Refused):
            emi.check_vouchers_handled("old-email", "done", self.rows([ROW_1710]), work_dir=self.work)


if __name__ == "__main__":
    unittest.main()
