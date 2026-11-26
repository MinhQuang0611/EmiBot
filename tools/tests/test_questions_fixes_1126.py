"""Dev, 2026-11-26 ("sửa 4 lỗi code"): 243 questions to Karen open; the questions-sweep dry run and the list showed four
code faults. (1) The sweep closed questions as "booking cancelled" on the very CANCEL row they asked about while the
build tool was stuck on it (365 Travel row 2622, E-676/E-678; SynXis 92777EE002243 row 1082, E-627/E-646), and as
"draft gone" a price question whose booking was waiting to be built (Turtle Adventure, E-645). (2) RATE MOVED asked
Karen eleven times about Trip.com prices brought down to the Ebooking net, the 19/11 rule (E-705–E-717). (3) A PDF
total 1–2 đồng off the sheet's, EZFOLIO rounding, became a question (Crystal Bay 1107315/1107316, E-668/E-728).
(4) invoice-make refused Odeon 1462822 because the row said "Công ty du lịch ODEON" (E-731)."""
import os
import tempfile
import unittest
from datetime import date, datetime, timezone

from tools import emi, intake_schema, operators, payments
from tools.state import State
from tools.tests.test_odeon_invoice_1109 import BUILT, ODEON
from tools.tests.test_questions_sweep_1118 import NOW, TODAY, Sheet, row


class SweepCancelAndPriceTest(unittest.TestCase):
    def setUp(self):
        self.st = State(os.path.join(tempfile.mkdtemp(), "state.json"))

    def ask(self, ref, text, mid=""):
        qid = self.st.ask(ref, text, mid)
        self.st.data["questions"][qid]["asked_at"] = "2026-11-13T03:00:00Z"
        return qid

    def sweep(self, rows):
        return emi.sweep_questions(Sheet(rows), self.st, apply=False, out=lambda *_: None, today=TODAY, now=NOW)

    def test_cancel_the_build_tool_stopped_on_is_kept(self):
        q = self.ask("365S01", "The EZFOLIO build tool stopped on booking 365S01 (CANCEL rows 2622)")
        close, keep = self.sweep([row("365S01", channel_type="TA", ez_status="done", pdf_link="x"),
                                  row("365S01", action="CANCEL", at="05/11/2026 09:00", channel_type="TA",
                                      ez_status="needs_review")])
        self.assertEqual(close, [])
        self.assertEqual([k for k, _, _ in keep], [q])

    def test_cancel_run_with_no_result_is_kept(self):  # row 1082: ez_processed_at, no ez_status
        q = self.ask("SynXis 92777EE002243 (Agoda)", "Cancellation row 1082 not picked up. How to proceed?")
        close, _ = self.sweep([row("SynXis 92777EE002243 (Agoda)", action="CANCEL", channel_type="OTA",
                                   company="Agoda", ez_processed_at="2026-11-03T10:10:00")])
        self.assertEqual(close, [])
        self.assertTrue(q in self.st.open_questions())

    def test_cancel_done_in_ezfolio_closes(self):
        q = self.ask("TA222", "Fee for this cancellation?")
        close, _ = self.sweep([row("TA222"), row("TA222", action="CANCEL", at="05/11/2026 09:00", ez_status="done")])
        self.assertEqual([(k, why) for k, _, why in close], [(q, "booking cancelled (row 4, done in EZFOLIO)")])

    def test_cancel_covered_by_the_ota_numbers_own_cancel_row_closes(self):
        q = self.ask("SynXis 92777EE002243", "Not picked up?")
        common = dict(action="CANCEL", channel_type="OTA", company="Agoda", guest_names="SERGII POPAS",
                      arrival="10/12/2026", dep="13/12/2026")
        close, _ = self.sweep([row("Agoda 698918623 / SynXis 92777EE002244", ez_status="done", **common),
                               row("SynXis 92777EE002243", **common)])
        self.assertEqual([k for k, _, _ in close], [q])

    def test_emis_own_no_room_cancel_on_an_ota_booking_settles_nothing(self):  # dev 25/11, rows 2573 / 2633
        q = self.ask("SynXis 92777EF003594 (Trip.com)", "Guest asks for late check-out")
        close, keep = self.sweep([row("SynXis 92777EF003594 (Trip.com)", channel_type="OTA", company="Trip.com"),
                                  row("SynXis 92777EF003594 (Trip.com)", action="CANCEL", at="05/11/2026 09:00",
                                      channel_type="OTA", company="Trip.com", ez_status="done",
                                      what_changed="No availability: booking cannot be accommodated")])
        self.assertEqual(close, [])
        self.assertEqual([k for k, _, _ in keep], [q])

    def test_price_question_on_an_unbuilt_booking_outlives_its_draft(self):  # E-645
        price = self.ask("TA-08Jan2027-GGT06", "Which price stands: 2,000,000/night or the TA card with +20%?",
                         mid="m1")
        other = self.ask("TA777", "Is the pool heated?", mid="m2")
        self.st.data["reviews"]["1548"] = {"source": "m1", "status": "gone", "history": []}
        self.st.data["reviews"]["1549"] = {"source": "m2", "status": "gone", "history": []}
        close, keep = self.sweep([row("TA-08Jan2027-GGT06", dep="12/01/2027"), row("TA777", dep="12/01/2027")])
        self.assertEqual([k for k, _, _ in close], [other])
        self.assertEqual([k for k, _, _ in keep], [price])

    def test_price_question_closes_with_its_draft_once_built(self):
        q = self.ask("TA888", "Which total should we confirm?", mid="m1")
        self.st.data["reviews"]["7"] = {"source": "m1", "status": "sent", "history": []}
        close, _ = self.sweep([row("TA888", dep="12/01/2027", ez_status="done", pdf_link="x")])
        self.assertEqual([k for k, _, _ in close], [q])


def notes(item6):
    return "\n".join(["1. Trip.com", "2. -", "3. -", "4. -", "5. -", item6, "7. -", "8. No VAT info"])


class TripcomNetTest(unittest.TestCase):
    SYNXIS = [{"company": "Trip.com", "total_vnd": "4835025", "notes": notes("6. SynXis total, provisional, no "
                                                                               "Trip.com Ebooking yet")}]
    EBOOKING = [{"company": "Trip.com", "total_vnd": "3384518", "notes": notes("6. Trip.com Ebooking net 3,384,518")}]

    def test_cut_to_the_ebooking_net_is_not_a_rate_move(self):  # E-705, SynXis 92777EF003603
        self.assertTrue(payments.tripcom_net_fix("SynXis 92777EF003603 (Trip.com)", self.SYNXIS, self.EBOOKING))

    def test_a_rise_still_goes_to_karen(self):  # E-711, 13,500,000 -> 17,500,000
        up = [dict(self.EBOOKING[0], total_vnd="17500000")]
        down = [dict(self.SYNXIS[0], total_vnd="13500000")]
        self.assertFalse(payments.tripcom_net_fix("Trip.com 1128152496978370", down, up))

    def test_second_cut_on_an_ebooking_figure_still_goes_to_karen(self):  # 003442: 13,389,300 was already Ebooking
        before = [dict(self.EBOOKING[0], total_vnd="13389300")]
        after = [dict(self.EBOOKING[0], total_vnd="10711436")]
        self.assertFalse(payments.tripcom_net_fix("SynXis 92777EF003442 (Trip.com)", before, after))

    def test_other_ota_or_no_ebooking_word_is_a_rate_move(self):
        agoda = [dict(r, company="Agoda") for r in self.SYNXIS], [dict(r, company="Agoda") for r in self.EBOOKING]
        self.assertFalse(payments.tripcom_net_fix("Agoda 1", *agoda))
        vague = [dict(self.EBOOKING[0], notes=notes("6. Net per VCC"))]
        self.assertFalse(payments.tripcom_net_fix("SynXis 1 (Trip.com)", self.SYNXIS, vague))

    def test_rendered_without_a_hold(self):
        item = {"ref": "SynXis 92777EF003603 (Trip.com)", "row": 2700, "company": "Trip.com", "group": "31500",
                "arrival": date(2026, 12, 1), "subject": "s", "channel": "OTA", "rows": [2700], "total": 3384518,
                "change": "price to Ebooking net", "tripcom_net": (4835025, 3384518)}
        text = payments.render_confirmations([item])
        self.assertIn("TRIP.COM EBOOKING NET 4,835,025", text)
        self.assertNotIn("RATE MOVED", text)


class PdfRoundingTest(unittest.TestCase):
    ROW = {"action": "NEW", "total_vnd": "10625000", "rooms": "1", "nights": "4"}

    def test_one_dong_off_is_the_same_total(self):  # E-668
        line = emi.pdf_rounding_line([self.ROW], [10625000, 10624999, 2656250])
        self.assertIn("PDF TOTAL = SHEET TOTAL (ROUNDING)", line)
        self.assertIn("10,624,999 (-1)", line)
        self.assertIn("no question to Karen", line)

    def test_room_nights_widen_the_margin(self):  # AERA-sized: 20 rooms x 4 nights
        big = [{"action": "NEW", "total_vnd": "64700000", "rooms": "20", "nights": "4"}]
        self.assertIn("(+60)", emi.pdf_rounding_line(big, [64700060]))

    def test_real_differences_and_exact_matches_print_nothing(self):
        self.assertEqual(emi.pdf_rounding_line([self.ROW], [10625000]), "")
        self.assertEqual(emi.pdf_rounding_line([self.ROW], [10600000]), "")  # AERA-like: a real gap
        self.assertEqual(emi.pdf_rounding_line([dict(self.ROW, total_vnd="")], [10624999]), "")


class OdeonCompanyTest(unittest.TestCase):
    def test_vietnamese_company_prefix_is_dropped(self):
        for name in ("Công ty du lịch ODEON", "CÔNG TY TNHH DU LỊCH ODEON TOURS", "Cty Odeon"):
            self.assertEqual(intake_schema.canonical_company(name), "Odeon", name)
        self.assertEqual(intake_schema.canonical_company("Cty Anex"), "Anex")
        self.assertIsNone(intake_schema.canonical_company("Công ty du lịch Phương Nguyễn"))
        self.assertIsNone(intake_schema.canonical_company("Công ty"))

    def test_invoice_data_takes_the_row_as_odeon(self):  # E-731, Odeon 1462822
        state = emi.booking_state([{**ODEON, **BUILT, "company": "Công ty du lịch ODEON"}], "4801957")
        self.assertEqual(operators.operator_name(state[0]["company"]), "Odeon")
        d = operators.invoice_data(state)
        self.assertEqual((d["company"], d["number"]), ("Odeon", "HAYA - 30931"))

    def test_invoice_make_no_longer_refuses_it(self):
        sheet = Sheet([{**ODEON, **BUILT, "company": "Công ty du lịch ODEON"}])
        self.assertEqual(emi._invoice_state(sheet, "4801957")["company"], "Odeon")
        with self.assertRaises(emi.Refused):
            emi._invoice_state(Sheet([{**ODEON, **BUILT, "company": "Pegas"}]), "4801957")


if __name__ == "__main__":
    unittest.main()
