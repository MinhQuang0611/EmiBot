"""The hourly "HAYA intake audit" floods the mailbox search (dev, 2026-11-21, Travel Concierge 2793131 #30487).

From 18/11 an audit lands in sales@ every hour, naming every open booking's ref and group code. Graph's search is
newest first, so the first 25 hits for "30487" were all audits: the confirmation sent on 28/10 never came back,
payments-due put the booking on "NO CONFIRMATION FOUND", and its 3,300,000 balance (due 18/11) got no reminder.
"""
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from tools import emi, payments
from tools.graph_mail import is_search_noise
from tools.state import State
from tools.tests.test_tools import mail_with

VN = timezone(timedelta(hours=7))
MAILBOX = "sales@haya-hotels.com"
KAREN_GMAIL = "karen@gmail.example"


def audit(n):
    return {"id": f"audit{n}", "subject": f"HAYA intake audit {n:02d}:50 21/11", "hasAttachments": False,
            "receivedDateTime": f"2026-11-21T{n % 24:02d}:50:00Z", "from": {"emailAddress": {"address": KAREN_GMAIL}}}


class NoiseTest(unittest.TestCase):
    def test_audit_subjects(self):
        for s in ("HAYA intake audit 10:55 19/11", "RE: HAYA intake audit 10:55 19/11", "Fwd: haya intake audit"):
            self.assertTrue(is_search_noise({"subject": s}), s)
        for s in ("NEW RESERVATION(S): 2793131", "Payment deposit 50% BK 2793131", "Audit of rooming list", ""):
            self.assertFalse(is_search_noise({"subject": s}), s)

    def test_search_leaves_out_audits_and_asks_for_more(self):
        real = {"id": "slip", "subject": "Payment BK 2793131", "from": {"emailAddress": {"address": "acct1@tc.vn"}}}
        mail, http = mail_with([("GET", "/messages?", {"value": [audit(n) for n in range(30)] + [real]})])
        self.assertEqual([m["id"] for m in mail.search("30487", top=25)], ["slip"])
        self.assertIn("$top=50", http.calls[0][1])

    def test_a_search_for_the_audit_still_finds_it(self):
        mail, _ = mail_with([("GET", "/messages?", {"value": [audit(1), audit(2)]})])
        self.assertEqual(len(mail.search("HAYA intake audit")), 2)

    def test_search_sent_reads_sent_items_only(self):
        mail, http = mail_with([("GET", "/mailFolders/sentitems/messages?", {"value": [
            {"id": "conf", "subject": "RE: NEW RESERVATION(S): 2793131", "from": {"emailAddress": {"address": MAILBOX}}}]})])
        self.assertEqual([m["id"] for m in mail.search_sent("30487")], ["conf"])
        self.assertIn("/mailFolders/sentitems/messages?", http.calls[0][1])
        self.assertIn('$search="30487"', http.calls[0][1])


class FloodedMail:
    """The whole-mailbox search returns only audits (what Graph did for #30487); Sent Items has the confirmation."""

    def __init__(self):
        self.sent_searches = 0

    def search(self, text, top=10):
        return [audit(n) for n in range(top)]

    def search_sent(self, text, top=10):
        self.sent_searches += 1
        return [{"id": "conf", "subject": "RE: NEW RESERVATION(S): 2793131", "hasAttachments": True,
                 "sentDateTime": "2026-10-28T05:00:00Z", "from": {"emailAddress": {"address": MAILBOX}}}]

    def get_message_bodies(self, message_id):
        return {"body": {"content": "Group code: #30487"},
                "toRecipients": [{"emailAddress": {"address": "res9@tc.vn"}}], "ccRecipients": []}


def concierge(n, **kw):
    """Live rows 665 / 829 / 2321, cut down: deposit paid, 10,200,000 of the 13,500,000 balance paid, 3,300,000 left."""
    base = {"_row": n, "action": "CHANGE", "received_at": "17/11/2026 16:20", "channel_type": "TA",
            "company": "Travel Concierge", "booking_ref": "2793131", "ezfolio_group_code": "30487",
            "arrival": "25/11/2026", "departure": "05/12/2026", "total_vnd": "27000000", "status": "Definite",
            "pdf_link": "https://drive/x", "Payment 1": "13500000", "Payment 2": "10200000",
            "Remaining amount": "3300000", "COD": "Remaining 3,300,000 VND outstanding (balance was due 18/11/2026)"}
    return {**base, **kw}


class ConfirmationFoundTest(unittest.TestCase):
    def test_the_confirmation_comes_from_sent_items(self):
        mail = FloodedMail()
        found = payments.find_confirmation(mail, "30487", MAILBOX, {"2793131"})
        self.assertEqual(found["id"], "conf")
        self.assertEqual(found["slips"], [])  # audits are no payment
        self.assertEqual(mail.sent_searches, 1)

    def test_travel_concierge_gets_its_balance_reminder(self):
        rows = [concierge(665, action="NEW", received_at="27/10/2026 19:27", **{"Payment 1": "", "Payment 2": "",
                                                                                   "Remaining amount": "27000000"}),
                concierge(2321)]
        out = payments.due(rows, emi.booking_state, emi._parts, FloodedMail(), State(tempfile.mktemp(suffix="-state.json")), MAILBOX,
                           datetime(2026, 11, 21, 14, 35, tzinfo=VN))
        self.assertEqual(out["no_confirmation"], [])
        [item] = out["remind"]
        self.assertEqual((item["ref"], item["which"], item["amount"]), ("2793131", "balance", 3300000))
        self.assertTrue(item["passed"])  # the balance date (18/11) is gone: the reminder goes marked LATE


if __name__ == "__main__":
    unittest.main()


class DayCheckOutcomeTest(unittest.TestCase):
    """Job 6, 20/11 23:30: 'DAY CHECK: NO REPLY: alert' was refused, four emails stayed on the day check."""

    def test_day_check_prefix_keeps_the_no_reply_reasons(self):
        st = State(tempfile.mktemp(suffix="-state.json"))
        for outcome in ("DAY CHECK: NO REPLY: alert", "DAY CHECK: ANSWERED BY STAFF 20/11 10:24", "NO REPLY: spam"):
            emi.check_email_answered(st, "m1", outcome, lambda: {})  # no Refused
        with self.assertRaises(emi.Refused):
            emi.check_email_answered(st, "m1", "DAY CHECK: looked at it", lambda: {})


class CountingMail(FloodedMail):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def search(self, text, top=10):
        self.calls += 1
        return super().search(text, top)

    def search_sent(self, text, top=10):
        self.calls += 1
        return super().search_sent(text, top)

    def get_message_bodies(self, message_id):
        self.calls += 1
        return super().get_message_bodies(message_id)


class ConfirmationCacheTest(unittest.TestCase):
    """dev, 2026-11-21: payments-due took 36 s on the host; the agent's shell call stops at 30 s."""

    ROWS = [concierge(2321)]
    NOW = datetime(2026, 11, 21, 15, 0, tzinfo=VN)

    def test_a_known_confirmation_costs_no_mail_call(self):
        cache, mail = {}, CountingMail()
        first = payments.find_confirmation(mail, "30487", MAILBOX, {"2793131"}, cache=cache, slips=False)
        used = mail.calls
        again = payments.find_confirmation(mail, "30487", MAILBOX, {"2793131"}, cache=cache, slips=False)
        self.assertEqual(mail.calls, used)
        self.assertEqual((again["id"], again["sent_at"]), (first["id"], first["sent_at"]))
        self.assertNotIn("slips", again)

    def test_an_overdue_booking_is_not_searched_for_slips(self):
        st = State(tempfile.mktemp(suffix="-state.json"))
        st.record_draft("d1", "2793131", 2321, "balance_reminder")
        cache = {}
        payments.due(self.ROWS, emi.booking_state, emi._parts, CountingMail(), st, MAILBOX, self.NOW, cache=cache)
        mail = CountingMail()
        out = payments.due(self.ROWS, emi.booking_state, emi._parts, mail, st, MAILBOX, self.NOW, cache=cache)
        self.assertEqual([i["ref"] for i in out["overdue"]], ["2793131"])
        self.assertEqual(mail.calls, 0)

    def test_payments_due_keeps_what_it_found(self):
        work = tempfile.mkdtemp()

        class Sheet:
            def rows(self):
                return ConfirmationCacheTest.ROWS

        st = State(tempfile.mktemp(suffix="-state.json"))
        emi.run_payments_due(CountingMail(), Sheet(), st, out=lambda *_: None, now=self.NOW, work_dir=work)
        with open(os.path.join(work, emi.CONFIRMATIONS_FOUND), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["30487"]["id"], "conf")
        mail = CountingMail()
        out = emi.run_payments_due(mail, Sheet(), st, out=lambda *_: None, now=self.NOW, work_dir=work)
        self.assertEqual(mail.calls, 1)  # only the slips search of the reminder about to go
        self.assertEqual([i["ref"] for i in out["remind"]], ["2793131"])
