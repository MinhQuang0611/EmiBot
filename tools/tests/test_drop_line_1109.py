"""The red stop line comes off a draft whatever order Outlook saved its tags in (#686, 09/11: an empty red paragraph
was left on top of the confirmation)."""
import unittest

from tools.graph_mail import DO_NOT_SEND, NO_INVOICE, drop_line

P = '<p class="elementToProof" style="margin:0px 0px 12pt; color:rgb(0,0,0)">'
DEAR = P + "Dear Odeon Reservations Team,</p>"


class DropLineTest(unittest.TestCase):
    def test_outlook_order_span_then_b(self):
        html = P + '<span style="color:rgb(255,0,0)"><b>' + NO_INVOICE + "</b></span></p>" + DEAR
        self.assertEqual(drop_line(html, NO_INVOICE), DEAR)

    def test_emi_order_b_then_span(self):
        html = P + '<b><span style="color:#FF0000">' + DO_NOT_SEND + "</span></b></p>\r\n" + DEAR
        self.assertEqual(drop_line(html, DO_NOT_SEND), DEAR)

    def test_empty_red_shell_left_before_goes(self):
        html = P + '<span style="color:rgb(255,0,0)"><b></b></span></p>' + DEAR
        self.assertEqual(drop_line(html, NO_INVOICE), DEAR)

    def test_other_paragraphs_kept(self):
        body = DEAR + "<p><br></p>" + P + "<b>Total:</b> VND 1</p>" + P + '<span style="color:rgb(0,0,0)"></span></p>'
        self.assertEqual(drop_line(body, NO_INVOICE), body)


class OperatorRefTest(unittest.TestCase):
    def test_odeon_short_ref_is_enough(self):
        from tools import emi
        long_ref = "Odeon 4799222 (Coral Travel Poland; Voucher 1151155; Ref 1238448)"
        emi.check_operator_confirmation("Booking reference: 4799222\nGroup code: #30930\nReservations Team",
                                        long_ref, "30930")
        with self.assertRaises(emi.Refused):
            emi.check_operator_confirmation("Booking reference: 47992\nGroup code: #30930\nReservations Team",
                                            long_ref, "30930")


if __name__ == "__main__":
    unittest.main()
