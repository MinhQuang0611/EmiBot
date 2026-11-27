"""No holding replies (AGENTS rule 9), dev 2026-11-26 on Odeon 1462822 (#31528): Odeon asked for our proforma invoice
"in the attached format"; Emi answered "The proforma invoice will follow in Odeon's attached format" and forwarded
the request to accounting. dev: "nói rất nhiều lần là không được ghi câu chữ như là 'chúng tôi sẽ kiểm tra lại'.
Trong trường hợp này Emi đã biết làm invoice cho Odeon thì phải gửi luôn".
- every draft refuses "will follow", "we'll check", "get back to you", "sẽ kiểm tra", "sẽ gửi sau";
- only 6b (Odeon notice) and 6c (on request) keep their own "our reservations team will get back to you" sentence,
  and never on an invoice matter;
- --kind invoice makes the proforma (invoice-make) and attaches it to the reply; not made → no draft."""
import os

from tools import emi
from tools.tests.test_auto_send_1119 import AutoSendTest as Base

HOLD = ("Dear Nhu,\n\nGreetings from HAYA Hotel Phu Quoc, Trademark Collection by Wyndham, and thank you for your "
        "email.\n\nWe have noted your request for the proforma invoice for Odeon reservation 1462822. The proforma "
        "invoice will follow in Odeon's attached format.\n\nBest regards,\nReservations Team")
INVOICE = ("Dear Nhu,\n\nThank you for your email.\n\nPlease find attached our proforma invoice HAYA - 31528 for "
           "reservation 1462822 (voucher 1153646), 02/01/2027 – 09/01/2027.\n\nBest regards,\nReservations Team")
NOTE_6B = ("Dear Odeon Tours Vietnam Reservations Team,\n\nThank you very much for your email regarding reservation "
           "4788749.\n\nWe have received the information with thanks, and our reservations team will get back to you "
           "as soon as possible.\n\nThank you for your kind cooperation.\n\nBest regards,\nReservations Team")
NOTE_6C = ("Dear Anex Reservation Team,\n\nThank you very much for your reservation request no. 113002157 and for "
           "choosing HAYA Hotel Phu Quoc.\n\nWe have received your request, and our reservations team is now reviewing "
           "it. We will get back to you as soon as possible.\n\nThank you for your patience, and we look forward to "
           "welcoming your guests.\n\nBest regards,\nReservations Team")


class NoHoldingTest(Base):
    def invoice_reply(self, text, made, attach=()):
        path = os.path.join(self.dir, "body.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        from types import SimpleNamespace
        args = SimpleNamespace(message_id="sim-01-new-1512", body=path, kind="invoice", ref="1462822", row="",
                               replaces="", to="", cc="", internal=False, sender_only=False, subject_suffix="",
                               attach=list(attach))
        return emi.draft_reply(self.mail, self.st, args, tg=self.tg, out=self.lines.append,
                               make_invoice=lambda ref: made)

    def pdf(self, name):
        p = os.path.join(self.dir, name)
        with open(p, "wb") as f:
            f.write(b"%PDF-1.4 test")
        return p

    def test_will_follow_is_refused(self):
        with self.assertRaises(emi.Refused) as e:
            self.reply("reply", HOLD)
        self.assertIn("HOLDING REPLY", str(e.exception))
        self.assertIn("--kind invoice", str(e.exception))

    def test_other_holding_words_are_refused(self):
        for line in ("We will check and get back to you.", "We'll check availability and revert.",
                     "Chúng tôi sẽ kiểm tra lại và phản hồi.", "Khách sạn sẽ gửi sau.",
                     "The invoice will be sent shortly.", "Мы проверим и свяжемся с вами."):
            with self.assertRaises(emi.Refused, msg=line):
                self.reply("reply", f"Dear Sir,\n\n{line}\n\nBest regards,\nReservations Team")

    def test_6b_and_6c_keep_their_sentence(self):
        self.reply("reply", NOTE_6B, ref="4788749")
        self.reply("reply", NOTE_6C, ref="113002157")

    def test_the_received_sentence_is_never_the_answer_to_an_invoice_ask(self):
        text = NOTE_6B.replace("regarding reservation 4788749", "asking for the proforma invoice for 1462822")
        with self.assertRaises(emi.Refused):
            self.reply("reply", text, ref="1462822")

    def test_kind_invoice_attaches_the_proforma(self):
        d = self.invoice_reply(INVOICE, self.pdf("Invoice_1462822.pdf"), attach=[self.pdf("31528.pdf")])
        names = [a["name"] for a in self.mail._meta(d["id"])["attachments"]]
        self.assertEqual(names, ["Invoice_1462822.pdf", "31528.pdf"])
        self.assertEqual(self.last()["kind"], "invoice")
        self.assertFalse(self.mail._meta(d["id"]).get("sent"))  # not on the auto-send list: a person sends it

    def test_kind_invoice_without_an_invoice_makes_no_draft(self):
        with self.assertRaises(emi.Refused) as e:
            self.invoice_reply(INVOICE, None)
        self.assertIn("NO INVOICE", str(e.exception))
        self.assertFalse(self.st.data.get("reviews"))

    def test_kind_invoice_says_it_is_attached(self):
        with self.assertRaises(emi.Refused):
            self.invoice_reply("Dear Nhu,\n\nHere is the invoice.\n\nBest regards", self.pdf("Invoice_1462822.pdf"))
