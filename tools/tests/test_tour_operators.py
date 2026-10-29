"""Offline tests for the tour operator procedure (skills/tour-operators.md, dev 2026-10-29): the on-request rule,
Anex robot replies, Odeon's new-email confirmation with two PDFs, CHANGE rows that carry their own rate and
notes, check-out lists and proforma figures."""
import base64
import os
import tempfile
import unittest
from datetime import date
from types import SimpleNamespace
from unittest import mock

from tools import emi, operators
from tools.state import State
from tools.tests.test_emi import (BOOKING, DLX, REAL_HEADER, ConfirmationPdfTest, appended, chip, real_sheet,
                                  sheet_row)
from tools.tests.test_tools import mail_with

ODEON_BOOKING = dict(BOOKING, channel_type="Tour operator", company="Odeon", booking_ref="TEST-OD-4609701",
                     status="Definite", ezfolio_group_code="31000", confirmation_no="C-9",
                     **dict(DLX, rate_source="Odeon contract"))
ODEON_BODY = ("Dear Odeon Tours Vietnam Reservations Team,\n\nThank you for your reservation.\n\n"
              "Ref: TEST-OD-4609701\nGroup code: #31000\n\nPlease find attached our confirmation.\n\n"
              "Best regards,\nReservations Team")


def occupancy(pcts, start=date(2026, 12, 10)):
    nights = [date.fromordinal(start.toordinal() + i) for i in range(len(pcts))]
    return {"occupancy": dict(zip(nights, pcts))}


class OnRequestTest(unittest.TestCase):
    TODAY = date(2026, 10, 29)

    def test_no_room_rejects(self):
        v, why = operators.on_request(occupancy([40]), ["DLX-SV: none left on 10/12"], date(2026, 12, 10), self.TODAY)
        self.assertEqual(v, "REJECT")
        self.assertIn("no availability", why[0])

    def test_over_60_far_away_rejects(self):
        v, why = operators.on_request(occupancy([55, 61]), [], date(2026, 12, 10), self.TODAY)
        self.assertEqual(v, "REJECT")
        self.assertIn("11/12 (61%)", why[0])

    def test_over_60_but_close_asks_karen(self):
        v, _ = operators.on_request(occupancy([70], start=date(2026, 11, 20)), [], date(2026, 11, 20), self.TODAY)
        self.assertEqual(v, "ASK KAREN")

    def test_free_and_quiet_asks_karen(self):
        v, _ = operators.on_request(occupancy([60, 45]), [], date(2026, 12, 10), self.TODAY)
        self.assertEqual(v, "ASK KAREN")  # exactly 60% is not over 60%


class AnexRobotTest(unittest.TestCase):
    def setUp(self):
        self._mode = os.environ.pop("EMI_DRAFT_MODE", None)
        self.addCleanup(lambda: os.environ.__setitem__("EMI_DRAFT_MODE", self._mode) if self._mode else None)
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def test_reply_to_the_robot_goes_to_the_reservations_desk(self):
        mail, http = mail_with([
            ("GET", "/messages/m1", {"from": {"emailAddress": {"address": "vn.robot@ms.anextour.com"}},
                                     "subject": "NEW RESERVATION No: 112888584"}),
            ("POST", "/createReply", {"id": "d1", "subject": "RE: NEW RESERVATION No: 112888584"}),
            ("GET", "/messages/d1?$select=body", {"body": {"content": "<html><body></body></html>"}})])
        body = os.path.join(self.dir.name, "b.txt")
        with open(body, "w", encoding="utf-8") as f:
            f.write("Dear Anex Reservation Team,\n\nThank you for your reservation.\n\nBest regards,\nReservations Team")
        a = SimpleNamespace(message_id="m1", body=body, all=False, kind="reply", ref="112888584", row="", to="",
                            cc="", internal=False)
        emi.draft_reply(mail, State(os.path.join(self.dir.name, "s.json")), a, out=lambda *_: None)
        patch = next(b for m, u, b in http.calls if m == "PATCH" and b and "toRecipients" in b)
        self.assertEqual(patch["toRecipients"], [{"emailAddress": {"address": "reservation@anexvietnam.com"}}])

    def test_robot_lookup(self):
        self.assertEqual(operators.robot_operator("VN.Robot@ms.anextour.com"), "Anex")
        self.assertIsNone(operators.robot_operator("reservation@anexvietnam.com"))


class OdeonConfirmationTest(unittest.TestCase):
    def setUp(self):
        self.helper = ConfirmationPdfTest("test_file_id_from_drive_links")
        self.helper.setUp()
        self.addCleanup(self.helper.tearDown)
        self.helper.row = sheet_row(**ODEON_BOOKING)
        with open(self.helper.body, "w", encoding="utf-8") as f:
            f.write(ODEON_BODY)
        self.invoice = os.path.join(self.helper.dir.name, "Invoice_TEST-OD-4609701.pdf")
        with open(self.invoice, "wb") as f:
            f.write(b"%PDF-1.4 invoice")
        p = mock.patch.object(emi, "WORK_DIR", self.helper.dir.name)
        p.start()
        self.addCleanup(p.stop)
        self._mode = os.environ.pop("EMI_DRAFT_MODE", None)
        self.addCleanup(lambda: os.environ.__setitem__("EMI_DRAFT_MODE", self._mode) if self._mode else None)

    def args(self, **kw):
        a = dict(message_id="m1", row=3, body=self.helper.body, all=False, to="", cc="", subject="", attach=[])
        a.update(kw)
        return SimpleNamespace(**a)

    def test_reply_refused_new_email_with_both_pdfs(self):
        mail, http = mail_with([("POST", "/messages", {"id": "d9", "subject": "Odeon Reservation confirmation"})])
        st = State(os.path.join(self.helper.dir.name, "s.json"))
        sheet = self.helper.sheet(chip(ConfirmationPdfTest.URL))
        with self.assertRaises(emi.Refused) as e:
            emi.draft_confirmation(mail, sheet, st, self.args(), out=lambda *_: None)
        self.assertIn("vietnamaccounts@odeontours.com", str(e.exception))
        self.assertEqual(http.calls, [])
        emi.draft_confirmation(mail, sheet, st, self.args(
            to="vietnamreservations@odeontours.com", cc="vietnamaccounts@odeontours.com",
            subject="Odeon Reservation confirmation TEST-OD-4609701", attach=[self.invoice]), out=lambda *_: None)
        new = next(b for m, u, b in http.calls if m == "POST" and u.endswith("/messages"))
        self.assertEqual(new["subject"], "Odeon Reservation confirmation TEST-OD-4609701")
        self.assertEqual(new["body"]["contentType"], "HTML")
        names = [b["name"] for m, u, b in http.calls if u.endswith("/messages/d9/attachments")]
        self.assertEqual(names, ["TEST-1511 confirmation.pdf", "Invoice_TEST-OD-4609701.pdf"])
        att = [b for m, u, b in http.calls if u.endswith("/messages/d9/attachments")][1]
        self.assertEqual(base64.b64decode(att["contentBytes"]), b"%PDF-1.4 invoice")
        self.assertEqual(st.data["reviews"]["1"]["operator"], "Odeon")

    def test_operator_text_needs_group_code_not_bank(self):
        emi.check_operator_confirmation(ODEON_BODY, "TEST-OD-4609701", "31000")
        with self.assertRaises(emi.Refused):
            emi.check_operator_confirmation(ODEON_BODY.replace("#31000", ""), "TEST-OD-4609701", "31000")


class DraftNewTest(unittest.TestCase):
    def setUp(self):
        self._mode = os.environ.pop("EMI_DRAFT_MODE", None)
        self.addCleanup(lambda: os.environ.__setitem__("EMI_DRAFT_MODE", self._mode) if self._mode else None)
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.body = os.path.join(self.dir.name, "b.txt")
        with open(self.body, "w", encoding="utf-8") as f:
            f.write("Dear Odeon Tours Vietnam Reservations Team,\n\nVoucher no. 4609701 is declined.\n\n"
                    "Best regards,\nReservations Team")

    def args(self, **kw):
        a = dict(message_id="m1", to="vietnamreservations@odeontours.com,vietnamaccounts@odeontours.com", cc="",
                 subject="Voucher 4609701 – Declined (on request)", body=self.body, kind="decline", ref="4609701",
                 row="", attach=[])
        a.update(kw)
        return SimpleNamespace(**a)

    def test_new_email_draft(self):
        mail, http = mail_with([("POST", "/messages", {"id": "d5"})])
        st = State(os.path.join(self.dir.name, "s.json"))
        emi.draft_new(mail, st, self.args(), out=lambda *_: None)
        new = next(b for m, u, b in http.calls if m == "POST")
        self.assertEqual([r["emailAddress"]["address"] for r in new["toRecipients"]],
                         ["vietnamreservations@odeontours.com", "vietnamaccounts@odeontours.com"])
        self.assertEqual(st.data["reviews"]["1"]["how"], "new")

    def test_refusals(self):
        mail, http = mail_with()
        st = State(os.path.join(self.dir.name, "s.json"))
        for kw in ({"to": "haya@haya-hotels.com"}, {"kind": "confirmation"}, {"attach": [self.body]}):
            with self.assertRaises(emi.Refused, msg=kw):
                emi.draft_new(mail, st, self.args(**kw), out=lambda *_: None)
        self.assertEqual(http.calls, [])


class OperatorChangeRowTest(unittest.TestCase):
    CHANGE = dict(action="CHANGE", received_at="30/10/2026 09:00", source_email="Re: TEST-OD-4609701",
                  booking_ref="TEST-OD-4609701", what_changed="Dates 20–22/11 → 21–23/11", property="HAYA",
                  status="Definite", priority="Normal", arrival="21/11/2026", departure="23/11/2026")

    def test_change_without_its_own_rate_and_notes_refused(self):
        sh, http = real_sheet([sheet_row(**ODEON_BOOKING)])
        with self.assertRaises(emi.Refused) as e:
            emi.sheet_append(sh, {"booking": self.CHANGE, "room_lines": [{"room_code": "DLX-SV"}]},
                             out=lambda *_: None)
        self.assertIn("notes", str(e.exception))
        self.assertIsNone(appended(http))

    def test_change_with_rate_and_notes_written(self):
        sh, http = real_sheet([sheet_row(**ODEON_BOOKING)])
        notes = "\n".join(["1. Odeon – Ref TEST-OD-4609701", "2. TEST GUEST – Russia", "3. 21/11/2026 – 23/11/2026",
                           "4. 2 Deluxe Sea View – 4 adults, 0 children", "5. None",
                           "6. Odeon contract: 2,200,000 × 2 night(s) = 4,400,000; = 4,400,000, BB, incl. tax",
                           "7. Invoice: none stated"])
        line = {"room_code": "DLX-SV", "rate_source": "Odeon contract", "rate_per_night_vnd": "2200000",
                "Average rate per night after discount": "2200000", "total_vnd": "8800000", "notes": notes}
        emi.sheet_append(sh, {"booking": self.CHANGE, "room_lines": [line]}, out=lambda *_: None)
        self.assertEqual(appended(http)[0]["company"], "Odeon")


def rows(*specs):
    out = []
    for i, cells in enumerate(specs, 3):
        out.append(dict({h: "" for h in REAL_HEADER}, _row=i, **cells))
    return out


class CheckoutsTest(unittest.TestCase):
    def test_checkouts_by_company_and_date_skip_cancelled_and_moved(self):
        base = dict(action="NEW", company="Anex", received_at="01/10/2026 10:00", tracy_status="Entered",
                    room_code="DLX-SV", rooms="1", total_vnd="4400000", arrival="03/11/2026")
        sheet_rows = rows(
            dict(base, booking_ref="A1", departure="05/11/2026", ezfolio_group_code="30001"),
            dict(base, booking_ref="A2", departure="05/11/2026"),
            dict(base, booking_ref="A2", action="CANCEL", received_at="02/10/2026 10:00", departure="05/11/2026"),
            dict(base, booking_ref="A3", departure="05/11/2026"),
            dict(base, booking_ref="A3", action="CHANGE", received_at="03/10/2026 10:00", departure="08/11/2026"),
            dict(base, booking_ref="O1", company="Odeon", departure="05/11/2026"))
        hits = operators.checkouts(sheet_rows, emi.booking_state, "Anex", date(2026, 11, 5), date(2026, 11, 5))
        self.assertEqual([s[0]["booking_ref"] for s in hits], ["A1"])
        text = operators.render_checkouts(hits, "Anex", date(2026, 11, 5), date(2026, 11, 5))
        self.assertIn("group #30001", text)
        self.assertIn("TOTAL 4,400,000 VND", text)
        week = operators.checkouts(sheet_rows, emi.booking_state, "anex", date(2026, 11, 2), date(2026, 11, 8))
        self.assertEqual([s[0]["booking_ref"] for s in week], ["A1", "A3"])

    def test_last_week_is_monday_to_sunday(self):
        self.assertEqual(emi._monday_last_week(date(2026, 10, 29)), date(2026, 10, 19))  # Thursday
        self.assertEqual(emi._monday_last_week(date(2026, 10, 26)), date(2026, 10, 19))  # Monday


class InvoiceDataTest(unittest.TestCase):
    def test_odeon_proforma(self):
        state = rows(dict(ODEON_BOOKING, total_vnd="8000000"))
        d = operators.invoice_data(state)
        self.assertEqual((d["number"], d["file"], d["due"], d["total"]),
                         ("HAYA - 31000", "Invoice_TEST-OD-4609701.pdf", date(2026, 11, 10), 8000000))
        self.assertIn("Payment due: 10/11/2026", operators.render_invoice(d))

    def test_pegas_has_a_send_by_date_and_no_group_waits(self):
        state = rows(dict(ODEON_BOOKING, company="Pegas"))
        d = operators.invoice_data(state)
        self.assertEqual((d["due"], d["send_by"]), (date(2026, 11, 13), date(2026, 11, 6)))
        with self.assertRaises(KeyError):
            operators.invoice_data(rows(dict(ODEON_BOOKING, ezfolio_group_code="")))
        with self.assertRaises(KeyError):
            operators.invoice_data(rows(dict(ODEON_BOOKING, company="Anex")))


class ToPriceCommandTest(unittest.TestCase):
    def test_cli_prices_and_refuses(self):
        a = emi.parser().parse_args(["to-price", "--operator", "Odeon", "--arrival", "20/11/2026", "--departure",
                                     "22/11/2026", "--room", "STD", "--adults", "2", "--booked", "01/09/2026"])
        with self.assertRaises(emi.Refused):
            emi.to_price(a, out=lambda *_: None)  # Odeon without the voucher's SPO code
        a.spo = "EB"
        lines = []
        q = emi.to_price(a, out=lines.append)
        self.assertEqual(q["total"], round(1900000 * 0.85) * 2)
        self.assertIn("total_vnd: 3230000", lines[0])

    def test_info_for_every_operator(self):
        for op in operators.OPERATORS:
            self.assertIn("COMMON STEPS", operators.info(op))


if __name__ == "__main__":
    unittest.main()
