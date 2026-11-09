"""Dev, 2026-11-09 (Odeon 4801957): built 08/11 23:55, and draft #652 still had no PDF and no group code at noon the
next day. confirmation-attach refused an Odeon draft without our proforma invoice, which a person makes and nobody
had, so job 2 said "chờ invoice" every 15 minutes and then held the booking. Now the EZFOLIO PDF and the build's
facts go on as soon as the row is built, and a red DO NOT SEND UNTIL INVOICE IS ATTACHED line holds the draft until
the invoice is on (by confirmation-attach --attach, or by a person in Outlook)."""
import base64
import os
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

from tools import emi, payments, review
from tools.graph_mail import DO_NOT_SEND, NO_INVOICE, email_html
from tools.state import State
from tools.tests.test_tools import mail_with

VN = timezone(timedelta(hours=7))
LINK = "https://drive.google.com/file/d/1O9F933lwdLR-MTNQBXM04CO6got3u1rL/view?usp=drivesdk"
ODEON = {"action": "NEW", "received_at": "08/11/2026 23:21", "source_email": "ODEON VOUCHERS 08.11",
         "channel_type": "Tour operator", "company": "Odeon", "booking_ref": "4801957",
         "guest_names": "SUMINSKI TOMASZ NORBERT; SUMINSKA MAJA JULIA; SUMINSKA POLA MAJA", "arrival": "10/12/2026",
         "departure": "20/12/2026", "room_code": "TPL", "rooms": "1", "total_vnd": "22657500", "status": "Definite",
         "_row": 1711}
BUILT = {"ezfolio_group_code": "30931", "confirmation_no": "26560", "pdf_link": LINK, "ez_status": "done",
         "ez_processed_at": "2026-11-08T23:55:54"}
BODY = ("Dear Odeon Reservations Team,\n\nThank you for your booking.\n\nBooking reference: 4801957\n"
        "Group code: #[GROUP CODE]\nConfirmation number: [CONF NO]\nStay: 10/12/2026 – 20/12/2026 (10 nights)\n"
        "Room: 1 Triple Room with Balcony, breakfast included\n\nTotal: VND 22,657,500, including breakfast, VAT and "
        "service charge.\n\nPayment: 100% is due by 30/11/2026 under the Odeon contract.\n\nBest regards,\n"
        "Reservations Team\nHAYA Hotel Phu Quoc, Trademark Collection by Wyndham\nsales@haya-hotels.com")
TO = dict(to="vietnamreservations@odeontours.com", cc="vietnamaccounts@odeontours.com",
          subject="Odeon Reservation confirmation 4801957")


class FakeSheet:
    def __init__(self, *rows):
        self.data = [dict(r) for r in rows]

    def rows(self):
        return [dict(r) for r in self.data]


class OdeonInvoiceTest(unittest.TestCase):
    def setUp(self):
        self._mode = os.environ.pop("EMI_DRAFT_MODE", None)
        self.addCleanup(lambda: os.environ.__setitem__("EMI_DRAFT_MODE", self._mode) if self._mode else None)
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.body = os.path.join(self.dir.name, "b.txt")
        with open(self.body, "w", encoding="utf-8") as f:
            f.write(BODY)
        self.invoice = os.path.join(self.dir.name, "Invoice_4801957.pdf")
        with open(self.invoice, "wb") as f:
            f.write(b"%PDF-1.4 invoice")
        self.st = State(os.path.join(self.dir.name, "s.json"))
        self.html, self.files = [""], []

        def new_draft(b):
            self.html[0] = b["body"]["content"]
            return {"id": "d1", "subject": b["subject"]}

        def attach(b):
            self.files.append({"@odata.type": "#microsoft.graph.fileAttachment", "name": b["name"],
                               "contentBytes": b["contentBytes"], "isInline": False})
            return {}

        self.mail, self.http = mail_with([
            ("POST", "/messages/d1/attachments", attach),
            ("GET", "/messages/d1/attachments", lambda _: {"value": list(self.files)}),
            ("POST", "/messages", new_draft),
            ("GET", "/messages/d1?$select=id", {"id": "d1", "isDraft": True, "categories": ["Emi"],
                                                "toRecipients": []}),
            ("GET", "/messages/d1?$select=body", lambda _: {"body": {"content": self.html[0]}}),
            ("PATCH", "/messages/d1", lambda b: self.html.__setitem__(0, b["body"]["content"]) if "body" in b else {}),
        ])

    def args(self, **kw):
        a = dict(message_id="m1", row=1711, body=self.body, all=False, attach=[], before_pdf=True, replaces="", **TO)
        a.update(kw)
        return SimpleNamespace(**a)

    def fake_pdf(self, sheet, row, out=print):
        path = os.path.join(self.dir.name, "conf.pdf")
        with open(path, "wb") as f:
            f.write(b"%PDF-1.4 conf")
        return path, "4801957 confirmation.pdf", "application/pdf", b"%PDF-1.4 conf"

    def attach(self, n, attach=(), lines=None):
        with mock.patch.object(emi, "pdf_fetch", self.fake_pdf):
            emi.confirmation_attach(self.mail, FakeSheet({**ODEON, **BUILT}), self.st,
                                    SimpleNamespace(n=n, attach=list(attach)),
                                    out=(lines.append if lines is not None else lambda *_: None),
                                    now=datetime(2026, 11, 9, 7, 0, tzinfo=VN))

    def early_draft(self):
        emi.draft_confirmation(self.mail, FakeSheet(ODEON), self.st, self.args(), out=lambda *_: None)
        return "1"

    def names(self):
        return [a["name"] for a in self.files]

    def test_pdf_goes_on_without_the_invoice_red_line_swapped(self):
        n = self.early_draft()
        self.assertIn(DO_NOT_SEND, self.html[0])
        lines = []
        self.attach(n, lines=lines)
        self.assertEqual(self.names(), ["4801957 confirmation.pdf"])
        self.assertIn("#30931", self.html[0])
        self.assertIn("26560", self.html[0])
        self.assertNotIn(DO_NOT_SEND, self.html[0])
        self.assertIn('color:#FF0000">' + NO_INVOICE, self.html[0])  # still bold red
        r = self.st.data["reviews"][n]
        self.assertFalse(r["awaiting_pdf"])
        self.assertTrue(r["awaiting_invoice"])
        self.assertTrue(r["text"].startswith(NO_INVOICE))
        self.assertIn("confirmation-attach 1 --attach emi-work/out/Invoice_4801957.pdf", lines[-1])
        # the booking has its confirmation now: job 2 owes it no other, the invoice wait shows in its report
        self.assertEqual(self.st.confirmation_drafted(), {("4801957", 1711)})
        self.assertEqual(self.st.awaiting_pdf(), {})
        out = []
        with mock.patch.object(payments, "needs_confirmation", lambda *a, **k: []):
            emi.run_confirmations_due(self.mail, FakeSheet({**ODEON, **BUILT}), self.st, out=out.append)
        self.assertTrue(any(line.startswith("INVOICE #1 4801957") for line in out), out)

    def test_accept_refused_until_the_invoice_then_invoice_attach(self):
        n = self.early_draft()
        self.attach(n)
        with self.assertRaises(review.ReviewError) as e:
            review.accept(self.mail, self.st, None, n, out=lambda *_: None)
        self.assertIn("invoice", str(e.exception))
        with self.assertRaises(emi.Refused):  # nothing to add
            self.attach(n)
        self.attach(n, attach=[self.invoice])
        self.assertEqual(self.names(), ["4801957 confirmation.pdf", "Invoice_4801957.pdf"])
        self.assertNotIn(NO_INVOICE, self.html[0])
        self.assertFalse(self.st.data["reviews"][n]["awaiting_invoice"])
        self.assertFalse(self.st.data["reviews"][n]["text"].startswith("["))
        review.accept(self.mail, self.st, None, n, out=lambda *_: None)
        self.assertEqual(self.st.data["reviews"][n]["status"], "approved")

    def test_invoice_attached_by_a_person_in_outlook_lets_accept_through(self):
        n = self.early_draft()
        self.attach(n)
        self.files.append({"@odata.type": "#microsoft.graph.fileAttachment", "name": "HAYA - 30931.pdf",
                           "contentBytes": base64.b64encode(b"%PDF").decode(), "isInline": False})
        review.accept(self.mail, self.st, None, n, out=lambda *_: None)
        self.assertNotIn(NO_INVOICE, self.html[0])
        self.assertEqual(self.st.data["reviews"][n]["status"], "approved")

    def test_with_the_invoice_both_go_on_at_once(self):
        n = self.early_draft()
        self.attach(n, attach=[self.invoice])
        self.assertEqual(self.names(), ["4801957 confirmation.pdf", "Invoice_4801957.pdf"])
        self.assertNotIn(NO_INVOICE, self.html[0])
        self.assertNotIn(DO_NOT_SEND, self.html[0])
        self.assertFalse(self.st.data["reviews"][n].get("awaiting_invoice"))

    def test_built_odeon_without_invoice_is_drafted_with_its_pdf(self):
        # Odeon 4799222 (09/11): built, no draft at all, "chờ invoice" on every run
        body = os.path.join(self.dir.name, "built.txt")
        with open(body, "w", encoding="utf-8") as f:
            f.write(BODY.replace("#[GROUP CODE]", "#30931").replace("[CONF NO]", "26560"))
        with mock.patch.object(emi, "pdf_fetch", self.fake_pdf):
            emi.draft_confirmation(self.mail, FakeSheet({**ODEON, **BUILT}), self.st,
                                   self.args(before_pdf=False, body=body), out=lambda *_: None)
        self.assertEqual(self.names(), ["4801957 confirmation.pdf"])
        self.assertIn('color:#FF0000">' + NO_INVOICE, self.html[0])
        self.assertTrue(self.st.data["reviews"]["1"]["awaiting_invoice"])
        self.assertEqual(self.st.confirmation_drafted(), {("4801957", 1711)})

    def test_rewrite_keeps_the_invoice_line(self):
        n = self.early_draft()
        self.attach(n)
        text = self.st.data["reviews"][n]["text"].replace(NO_INVOICE, "").replace("Thank you for your booking.",
                                                                                   "Thank you.")
        with mock.patch.object(review, "_write", lambda mail, r, t: {"id": "d1"}), \
                mock.patch.object(self.mail, "delete_draft", lambda *_: None):
            review.rewrite(self.mail, self.st, None, n, text, out=lambda *_: None)
        self.assertTrue(self.st.data["reviews"][n]["text"].startswith(NO_INVOICE))
        self.assertEqual(self.st.data["reviews"][n]["text"].count(NO_INVOICE), 1)

    def test_job2_finds_the_draft_when_rows_moved(self):
        n = self.early_draft()
        moved = {**ODEON, **BUILT, "_row": 1717}  # the build tool inserted 6 rows above

        class NoMail:
            def search(self, *a, **k):
                return []

        with mock.patch.object(payments, "find_confirmation", lambda *a, **k: None):
            items = payments.needs_confirmation([moved], emi.booking_state, emi._parts, NoMail(), self.st,
                                                "sales@haya-hotels.com", date(2026, 11, 9))
        self.assertEqual(items[0].get("attach"), n)

    def test_invoice_line_is_red_and_only_ever_first(self):
        self.assertIn('<span style="color:#FF0000">' + NO_INVOICE, email_html(NO_INVOICE + "\n\nDear X,"))
        emi.check_no_gaps(NO_INVOICE + "\n\nDear X,")
        with self.assertRaises(emi.Refused):
            emi.check_no_gaps("Dear X,\n\n" + NO_INVOICE)


if __name__ == "__main__":
    unittest.main()
