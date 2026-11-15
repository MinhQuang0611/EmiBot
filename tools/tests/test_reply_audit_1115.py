"""reply-audit (dev, 2026-11-15): "CÁC EMAIL 13/11 - CHO EMI CHẠY REPLY HẾT NHÉ, thấy sót nhiều lắm". Every inbox
email since a day against Sent Items and Emi's drafts: SENT, DRAFTED, DELETED, NO REPLY; noise not listed."""
import os
import unittest

from tools import emi
from tools.state import State

SYNXIS = "noreply@synxis.com"


class Mail:
    def __init__(self, inbox, sent):
        self.inbox, self.sent = inbox, sent

    def list_inbox_since(self, since):
        return [{"id": i, "from": {"emailAddress": {"address": s}}, "subject": subj, "receivedDateTime": rcv,
                 "conversationId": conv} for i, s, subj, rcv, conv in self.inbox]

    def list_sent_since(self, since):
        return [{"id": f"s{n}", "subject": subj, "sentDateTime": when, "conversationId": conv}
                for n, (subj, when, conv) in enumerate(self.sent)]


class ReplyAuditTest(unittest.TestCase):
    def setUp(self):
        self.st = State(os.devnull + "-none")
        self.lines = []

    def review(self, n, source, status, kind="reply"):
        self.st.data["reviews"][str(n)] = {"source": source, "status": status, "kind": kind, "how": "reply"}

    def test_each_kind_of_answer(self):
        mail = Mail([("a", "agency@x.vn", "Booking 123456", "2026-11-13T02:00:00Z", "c-a"),        # staff replied
                     ("b", "guest@gmail.com", "Question", "2026-11-13T03:00:00Z", "c-b"),         # draft waiting
                     ("c", "agency@y.vn", "Re: dates", "2026-11-13T04:00:00Z", "c-c"),            # draft deleted
                     ("d", "agency@z.vn", "Payment 778899", "2026-11-13T05:00:00Z", "c-d"),       # nothing
                     ("e", "mailer-daemon@x.com", "Undeliverable: hi", "2026-11-13T06:00:00Z", "c-e"),
                     ("f", SYNXIS, "SynXis Res Confirmed (92777EF003350 )", "2026-11-13T07:00:00Z", "c-f"),
                     ("g", SYNXIS, "SynXis Res Confirmed (92777EF003351 )", "2026-11-13T08:00:00Z", "c-g"),
                     ("h", "promo@shop.com", "Sale", "2026-11-13T09:00:00Z", "c-h"),
                     ("i", "res@odeon.com", "Voucher 4788749", "2026-11-13T10:00:00Z", "c-i"),    # new-email reply
                     ("j", "agency@q.vn", "Re: old", "2026-11-13T11:00:00Z", "c-j")],             # reply BEFORE it
                    [("RE: Booking 123456", "2026-11-13T02:30:00Z", "c-a"),
                     ("Re: old", "2026-11-13T10:00:00Z", "c-j"),
                     ("Odeon Reservation confirmation 4788749", "2026-11-13T12:00:00Z", "other"),
                     ("RE: SynXis Res Confirmed (92777EF003351 )", "2026-11-13T09:00:00Z", "c-g")])
        self.review(1, "b", "pending")
        self.review(2, "c", "gone")
        self.review(3, "f", "approved", kind="ota_note")
        self.review(4, "g", "gone", kind="confirmation")  # 13/11-rule confirmation sent, but no intake note
        self.st.mark_processed("d", "payment row 2001")
        self.st.mark_processed("h", "NO REPLY: spam")
        counts, work = emi.reply_audit(mail, self.st, "2026-11-12T17:00:00Z", out=self.lines.append)
        text = "\n".join(self.lines)
        self.assertEqual(counts, {"SENT": 2, "DRAFTED": 2, "DELETED": 1, "NO REPLY": 3, "noise": 2})
        marks = {w["id"]: w["mark"] for w in work}
        self.assertEqual(marks, {"b": "DRAFTED", "c": "DELETED", "d": "NO REPLY", "f": "DRAFTED", "g": "NO REPLY",
                                 "j": "NO REPLY"})
        self.assertIn("OTA notice without its intake note", text)
        self.assertIn("never marked done", text)        # j
        self.assertNotIn("Undeliverable", text)
        self.assertNotIn("Sale", text)

    def test_subject_without_a_number_never_matches_another_thread(self):
        mail = Mail([("a", "guest@gmail.com", "Booking request", "2026-11-13T02:00:00Z", "c-a")],
                    [("RE: Booking request", "2026-11-13T03:00:00Z", "someone-else")])
        counts, _ = emi.reply_audit(mail, self.st, "2026-11-12T17:00:00Z", out=self.lines.append)
        self.assertEqual(counts["NO REPLY"], 1)


if __name__ == "__main__":
    unittest.main()
