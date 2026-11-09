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

from tools import config, emi, invoice, operators, payments, review
from tools.graph_mail import DO_NOT_SEND, NO_INVOICE, email_html
from tools.state import State
from tools.tests.test_tools import mail_with

VN = timezone(timedelta(hours=7))
LINK = "https://drive.google.com/file/d/1O9F933lwdLR-MTNQBXM04CO6got3u1rL/view?usp=drivesdk"
ODEON = {"action": "NEW", "received_at": "08/11/2026 23:21", "source_email": "ODEON VOUCHERS 08.11",
         "channel_type": "Tour operator", "company": "Odeon", "booking_ref": "4801957",
         "guest_names": "SUMINSKI TOMASZ NORBERT; SUMINSKA MAJA JULIA; SUMINSKA POLA MAJA", "arrival": "10/12/2026",
         "departure": "20/12/2026", "room_code": "TPL", "rooms": "1", "total_vnd": "22657500", "status": "Definite",
         "nights": "10", "adults": "3", "children": "0", "meal_plan": "BB", "rate_per_night_vnd": "2650000",
         "Average rate per night after discount": "2265750", "_row": 1711}
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
        p = mock.patch.object(config, "invoice_book", lambda: None)  # no workbook: on the host .env sets one
        p.start()
        self.addCleanup(p.stop)

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
        self.assertIn("confirmation-attach 1 (it runs invoice-make)", lines[-1])
        self.assertIn("NO INVOICE 4801957: EMI_ODEON_INVOICE_BOOK is not set", lines[0])
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


class FakeBook:
    """The invoice workbook: tabs as in "HAYA Odeon Invoices 2026 - 2027" on 09/11."""

    def __init__(self, editable=True, existing=None):
        self.tab_list = [{"sheetId": 1, "title": "Sheet1", "index": 0}, {"sheetId": 2, "title": "4777887", "index": 1},
                         {"sheetId": 3, "title": "4609701", "index": 2}]
        self.cells, self.copied, self.editable, self.exported, self.formatted = {}, [], editable, [], []
        if existing:
            self.tab_list.append({"sheetId": 9, "title": existing[0], "index": 3})
            self.cells[existing[0]] = {"L8": existing[1], "K22": existing[2]}

    def tabs(self):
        return list(self.tab_list)

    def values(self, tab, a1):
        got = self.cells.get(tab.strip("'"), {})
        return [[got.get(a1.split(":")[0], "")]]

    def can_edit(self):
        return self.editable

    def duplicate(self, source_id, title, index):
        self.copied.append((source_id, title, index))
        self.tab_list.append({"sheetId": 50, "title": title, "index": index})
        return 50

    def write(self, tab, values):
        self.cells.setdefault(tab, {}).update(values)

    def finish(self, gid):
        self.formatted.append(gid)

    def pdf(self, gid):
        self.exported.append(gid)
        return b"%PDF-1.4 invoice " + str(gid).encode()


class InvoiceMakeTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.data = operators.invoice_data(emi.booking_state([{**ODEON, **BUILT}], "4801957"))

    def test_amount_in_words_as_the_hotel_writes_it(self):
        # the words on the invoices HAYA sent: 4777887, PVFBNYGE7_11_1, 4762629, 716532, 4609701
        self.assertEqual(invoice.in_words(17040000), "SEVENTEEN MILLION FORTY THOUSAND VIETNAMESE DONG")
        self.assertEqual(invoice.in_words(17552500),
                         "SEVENTEEN MILLION FIVE HUNDRED AND FIFTY-TWO THOUSAND FIVE HUNDRED VIETNAMESE DONG")
        self.assertEqual(invoice.in_words(23850000),
                         "TWENTY-THREE MILLION EIGHT HUNDRED AND FIFTY THOUSAND VIETNAMESE DONG")
        self.assertEqual(invoice.in_words(37620000),
                         "THIRTY-SEVEN MILLION SIX HUNDRED AND TWENTY THOUSAND VIETNAMESE DONG")
        self.assertEqual(invoice.in_words(22335000),
                         "TWENTY-TWO MILLION THREE HUNDRED AND THIRTY-FIVE THOUSAND VIETNAMESE DONG")

    def test_cells_of_4801957(self):
        c, total = invoice.cells(self.data, date(2026, 11, 9))
        self.assertEqual(total, 22657500)
        self.assertEqual((c["L8"], c["M8"], c["N8"]), ("HAYA - 30931", "09/11/2026", "30/11/2026"))
        self.assertEqual([c[f"{x}13"] for x in "BCDEFGHIJKLMN"],
                         ["10.12.2026", "20.12.2026", "Bed & Breakfast", "",
                          "SUMINSKI TOMASZ NORBERT,SUMINSKA MAJA JULIA,SUMINSKA POLA MAJA,", "HAYA HOTEL", 4801957,
                          "TRIPLE ROOM", 1, 10, "3", 2265750, 22657500])
        self.assertEqual({c[f"{x}{r}"] for x in "BCDEFGHIJKLMN" for r in range(14, 18)}, {""})  # old lines cleared
        self.assertEqual(c["C20"], "TWENTY-TWO MILLION SIX HUNDRED AND FIFTY-SEVEN THOUSAND FIVE HUNDRED VIETNAMESE DONG")
        self.assertEqual(c["B23"], "Payment to be settled by: 30/11/2026")
        self.assertNotIn("K22", c)  # the SUM formula stays, and the bank block is never written

    def test_ref_and_file_from_a_long_booking_ref(self):
        row = {**ODEON, **BUILT, "booking_ref": "Odeon 4799222 (Coral Travel Poland; Voucher 1151155; Ref 1238448)"}
        d = operators.invoice_data(emi.booking_state([row], row["booking_ref"]))
        self.assertEqual((d["voucher"], d["file"]), ("4799222", "Invoice_4799222.pdf"))

    def test_make_copies_the_latest_tab_writes_and_exports(self):
        book, lines = FakeBook(), []
        path = invoice.make(book, self.data, date(2026, 11, 9), self.dir.name, out=lines.append)
        self.assertEqual(book.copied, [(1, "4801957", 3)])  # the template Sheet1 (dev 09/11), placed last
        self.assertEqual(book.formatted, [50])
        self.assertEqual(book.cells["4801957"]["M12"], "Rate (VND)")
        self.assertEqual(book.cells["4801957"]["K21"], "Net amount VND:")
        self.assertEqual(book.cells["4801957"]["L8"], "HAYA - 30931")
        self.assertTrue(path.endswith("Invoice_4801957.pdf"))
        with open(path, "rb") as f:
            self.assertTrue(f.read().startswith(b"%PDF"))
        self.assertIn("new tab 4801957, copied from the template Sheet1", lines[0])

    def test_tab_made_before_is_exported_not_rewritten(self):
        book = FakeBook(existing=("4801957", "HAYA - 30931", "22,657,500 VND"))
        invoice.make(book, self.data, date(2026, 11, 9), self.dir.name, out=lambda *_: None)
        self.assertEqual((book.copied, book.exported), ([], [9]))
        other = FakeBook(existing=("4801957", "HAYA - 30931", "20,000,000 VND"))
        with self.assertRaises(invoice.InvoiceError):
            invoice.make(other, self.data, date(2026, 11, 9), self.dir.name, out=lambda *_: None)
        self.assertEqual(other.exported, [])

    def test_not_shared_as_editor_nothing_made(self):
        book = FakeBook(editable=False)
        with self.assertRaises(invoice.InvoiceError) as e:
            invoice.make(book, self.data, date(2026, 11, 9), self.dir.name, out=lambda *_: None)
        self.assertIn("Editor", str(e.exception))
        self.assertEqual(book.copied, [])

    def test_lines_must_add_up_to_the_booking(self):
        with self.assertRaises(invoice.InvoiceError):
            invoice.cells(dict(self.data, total=1), date(2026, 11, 9))


class AutoInvoiceTest(OdeonInvoiceTest):
    """With the workbook set, confirmation-attach makes the invoice itself: both PDFs, no red line left."""

    def setUp(self):
        super().setUp()
        self.book = FakeBook()
        p = mock.patch.object(config, "invoice_book", lambda: self.book)
        p.start()
        self.addCleanup(p.stop)
        w = mock.patch.object(emi, "WORK_DIR", self.dir.name)
        w.start()
        self.addCleanup(w.stop)

    def attach(self, n, attach=(), lines=None):
        with mock.patch.object(emi, "pdf_fetch", self.fake_pdf):
            emi.confirmation_attach(self.mail, FakeSheet({**ODEON, **BUILT}), self.st,
                                    SimpleNamespace(n=n, attach=list(attach)),
                                    out=(lines.append if lines is not None else lambda *_: None),
                                    now=datetime(2026, 11, 9, 7, 0, tzinfo=VN))

    def test_pdf_goes_on_without_the_invoice_red_line_swapped(self):
        n = self.early_draft()
        self.attach(n)
        self.assertEqual(self.names(), ["4801957 confirmation.pdf", "Invoice_4801957.pdf"])
        self.assertNotIn(NO_INVOICE, self.html[0])
        self.assertNotIn(DO_NOT_SEND, self.html[0])
        self.assertFalse(self.st.data["reviews"][n].get("awaiting_invoice"))
        review.accept(self.mail, self.st, None, n, out=lambda *_: None)

    def test_accept_refused_until_the_invoice_then_invoice_attach(self):
        pass  # the invoice is on at once here

    def test_invoice_attached_by_a_person_in_outlook_lets_accept_through(self):
        pass

    def test_rewrite_keeps_the_invoice_line(self):
        pass

    def test_built_odeon_without_invoice_is_drafted_with_its_pdf(self):
        body = os.path.join(self.dir.name, "built.txt")
        with open(body, "w", encoding="utf-8") as f:
            f.write(BODY.replace("#[GROUP CODE]", "#30931").replace("[CONF NO]", "26560"))
        with mock.patch.object(emi, "pdf_fetch", self.fake_pdf):
            emi.draft_confirmation(self.mail, FakeSheet({**ODEON, **BUILT}), self.st,
                                   self.args(before_pdf=False, body=body), out=lambda *_: None)
        self.assertEqual(self.names(), ["4801957 confirmation.pdf", "Invoice_4801957.pdf"])
        self.assertNotIn(NO_INVOICE, self.html[0])

    def test_workbook_not_editable_falls_back_to_the_red_line(self):
        self.book.editable = False
        n = self.early_draft()
        lines = []
        self.attach(n, lines=lines)
        self.assertEqual(self.names(), ["4801957 confirmation.pdf"])
        self.assertIn(NO_INVOICE, self.html[0])
        self.assertTrue(any("NO INVOICE 4801957" in line and "Editor" in line for line in lines), lines)
        self.book.editable = True  # shared later: the next confirmation-attach makes it and finishes the draft
        self.attach(n)
        self.assertEqual(self.names(), ["4801957 confirmation.pdf", "Invoice_4801957.pdf"])
        self.assertNotIn(NO_INVOICE, self.html[0])


if __name__ == "__main__":
    unittest.main()
