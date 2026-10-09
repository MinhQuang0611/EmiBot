"""Offline tests: fake HTTP, no mailbox or sheet touched.  python -m unittest discover tools/tests"""
import base64
import os
import tempfile
import unittest
import urllib.parse

from tools.graph_mail import DeviceCodeToken, GraphMail, SendBlocked, MAX_INLINE_ATTACHMENT
from tools.httpjson import HttpError
from tools.intake_sheet import IntakeSheet, SheetContractError, col_letter, missing_required
from tools.state import State
from tools import precheck


class FakeHttp:
    """Records calls; answers from a list of (method, url-substring, response) rules."""

    def __init__(self, rules=()):
        self.rules = list(rules)
        self.calls = []

    def __call__(self, method, url, headers=None, body=None, **_):
        self.calls.append((method, urllib.parse.unquote(url), body))
        for m, frag, resp in self.rules:
            if m == method and frag in urllib.parse.unquote(url):
                return resp(body) if callable(resp) else resp
        return {}


def mail_with(rules=()):
    http = FakeHttp(rules)
    return GraphMail("sales@haya-hotels.com", token=lambda: "tok", http=http), http


class GraphMailTest(unittest.TestCase):
    def test_send_endpoints_refused_before_network(self):
        mail, http = mail_with()
        for path in ("/sendMail", "/messages/1/send", "/messages/1/reply", "/messages/1/replyAll",
                     "/messages/1/forward", "/messages/1/SEND/", "https://graph.microsoft.com/v1.0/me/sendMail"):
            with self.assertRaises(SendBlocked, msg=path):
                mail._call("POST", path)
        self.assertEqual(http.calls, [])

    def test_create_variants_allowed(self):
        mail, http = mail_with([("POST", "/createReply", {"id": "d1"}), ("POST", "/createForward", {"id": "d2"})])
        mail.create_reply_draft("m1", "hi")
        mail.create_forward_draft("m1", ["accountant@palmahotel.vn"], "slip")
        posted = [c[1] for c in http.calls if c[0] == "POST"]
        self.assertTrue(any(u.endswith("/messages/m1/createReply") for u in posted))
        self.assertTrue(any(u.endswith("/messages/m1/createForward") for u in posted))
        tags = [c for c in http.calls if c[0] == "PATCH"]
        self.assertEqual([t[2] for t in tags], [{"categories": ["Emi"]}] * 2)

    def test_me_mailbox_uses_me_path(self):
        http = FakeHttp([("GET", "/mailFolders/inbox/messages", {"value": []})])
        GraphMail("me", token=lambda: "tok", http=http).has_new_inbox_mail("2026-10-09T00:00:00Z")
        self.assertTrue(http.calls[0][1].startswith("https://graph.microsoft.com/v1.0/me/mailFolders/inbox"))

    def test_no_send_method_on_class(self):
        for name in dir(GraphMail):
            self.assertNotIn(name.lower(), {"send", "send_mail", "reply", "forward", "reply_all"})

    def test_paging_follows_next_link(self):
        nxt = "https://graph.microsoft.com/v1.0/users/x/page2"
        mail, _ = mail_with([("GET", "page2", {"value": [{"id": "b"}]}),
                             ("GET", "/mailFolders/inbox/messages", {"value": [{"id": "a"}], "@odata.nextLink": nxt})])
        self.assertEqual([m["id"] for m in mail.list_inbox_since("2026-10-08T00:00:00Z")], ["a", "b"])

    def test_inbox_filter_in_query(self):
        mail, http = mail_with()
        mail.list_inbox_since("2026-10-08T01:00:00Z")
        self.assertIn("$filter=receivedDateTime ge 2026-10-08T01:00:00Z", http.calls[0][1])

    def test_update_draft_only_on_emi_drafts(self):
        mail, _ = mail_with([("GET", "/messages/d9", {"isDraft": True, "categories": []})])
        with self.assertRaises(PermissionError):
            mail.update_draft("d9", subject="x")
        mail, http = mail_with([("GET", "/messages/d9", {"isDraft": True, "categories": ["Emi"]})])
        mail.update_draft("d9", subject="x")
        self.assertEqual(http.calls[-1][0], "PATCH")

    def test_attachment_base64_and_size_limit(self):
        mail, http = mail_with()
        mail.add_attachment("d1", "conf.pdf", b"%PDF-1.4")
        self.assertEqual(base64.b64decode(http.calls[0][2]["contentBytes"]), b"%PDF-1.4")
        with self.assertRaises(ValueError):
            mail.add_attachment("d1", "big.pdf", b"x" * (MAX_INLINE_ATTACHMENT + 1))

    def test_attachments_decoded(self):
        mail, _ = mail_with([("GET", "/attachments", {"value": [
            {"@odata.type": "#microsoft.graph.fileAttachment", "name": "unc.jpg",
             "contentBytes": base64.b64encode(b"img").decode()}]})])
        self.assertEqual(mail.list_attachments("m1")[0]["data"], b"img")


HEADER = ["action", "booking_ref", "company", "arrival", "departure", "rate_per_night_vnd",
          "room_code", "rooms", "payment_1_vnd", "tracy_status", "pdf_link"]


def sheet_with(data_rows, extra_rules=()):
    rules = list(extra_rules) + [
        ("GET", "!1:1", {"values": [HEADER]}),
        ("GET", "!A3:", {"values": data_rows}),
        ("GET", "fields=sheets.properties", {"sheets": [{"properties": {"title": "Intake", "sheetId": 77}}]}),
    ]
    http = FakeHttp(rules)
    return IntakeSheet("SID", lambda m, u, body=None: http(m, u, body=body)), http


class IntakeSheetTest(unittest.TestCase):
    def test_col_letter(self):
        self.assertEqual([col_letter(i) for i in (0, 25, 26, 51, 52)], ["A", "Z", "AA", "AZ", "BA"])

    def test_rows_mapped_by_header_with_row_numbers(self):
        sh, _ = sheet_with([["NEW", "SB-1", "Sao Bien"], [], ["CHANGE", "AN-2"]])
        rows = sh.rows()
        self.assertEqual([(r["booking_ref"], r["_row"]) for r in rows], [("SB-1", 3), ("AN-2", 5)])
        self.assertEqual(rows[1]["company"], "")

    def test_find_by_ref_case_insensitive(self):
        sh, _ = sheet_with([["NEW", "sb2611-047"]])
        self.assertEqual(len(sh.find_by_ref(" SB2611-047 ")), 1)

    def test_append_sets_pending_and_orders_columns(self):
        sh, http = sheet_with([])
        sh.append_rows([{"booking_ref": "SB-1", "company": "Sao Bien", "action": "NEW"}])
        method, url, body = http.calls[-1]
        self.assertIn(":append?valueInputOption=RAW", url)
        row = body["values"][0]
        self.assertEqual(row[:3], ["NEW", "SB-1", "Sao Bien"])
        self.assertEqual(row[HEADER.index("tracy_status")], "Pending")

    def test_append_rejects_unknown_and_build_tool_columns(self):
        sh, _ = sheet_with([])
        with self.assertRaises(SheetContractError):
            sh.append_rows([{"booking_ref": "x", "my_new_column": "1"}])
        with self.assertRaises(SheetContractError):
            sh.append_rows([{"booking_ref": "x", "pdf_link": "http://..."}])
        with self.assertRaises(SheetContractError):
            sh.append_rows([{"booking_ref": "x", "tracy_status": "Entered"}])

    def test_update_cells_targets_single_cells(self):
        sh, http = sheet_with([])
        sh.update_cells(7, {"payment_1_vnd": "1150000"})
        body = http.calls[-1][2]
        self.assertEqual(body["data"], [{"range": "'Intake'!I7", "values": [["1150000"]]}])
        with self.assertRaises(SheetContractError):
            sh.update_cells(7, {"tracy_status": "Entered"})
        with self.assertRaises(SheetContractError):
            sh.update_cells(2, {"company": "x"})

    def test_delete_only_test_rows(self):
        sh, http = sheet_with([["NEW", "SB-1"], ["NEW", "TEST-EMI"]])
        with self.assertRaises(SheetContractError):
            sh.delete_test_row(3)
        sh.delete_test_row(4)
        req = http.calls[-1][2]["requests"][0]["deleteDimension"]["range"]
        self.assertEqual((req["sheetId"], req["startIndex"], req["endIndex"]), (77, 3, 4))

    def test_awaiting_confirmation_skips_drafted(self):
        r = ["NEW", "SB-1", "", "", "", "", "", "", "", "Entered", "https://drive/x"]
        sh, _ = sheet_with([r, r[:1] + ["AN-2"] + r[2:]])
        self.assertEqual([x["booking_ref"] for x in sh.rows_awaiting_confirmation({("SB-1", 3)})], ["AN-2"])

    def test_missing_required(self):
        self.assertEqual(missing_required({"company": "A", "arrival": "1", "departure": "2",
                                           "rate_per_night_vnd": "", "room_code": "SD", "rooms": "2"}),
                         ["rate_per_night_vnd"])


class StateTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "s.json")

    def tearDown(self):
        self.dir.cleanup()

    def test_roundtrip_and_question_ids(self):
        s = State(self.path)
        self.assertEqual(s.ask("AN-1", "cancel?"), "E-001")
        self.assertEqual(s.ask("PMQ-2", "extend?"), "E-002")
        s.save()
        s2 = State(self.path)
        self.assertEqual(list(s2.open_questions()), ["E-001", "E-002"])
        self.assertEqual(s2.ask("x", "y"), "E-003")

    def test_bare_yes_only_with_one_open_question(self):
        s = State(self.path)
        s.ask("A", "a?")
        s.ask("B", "b?")
        self.assertIsNone(s.answer("yes"))
        self.assertEqual(s.answer("e-002 offer the Quadruple"), "E-002")
        self.assertEqual(s.data["questions"]["E-002"]["answer"], "offer the Quadruple")
        self.assertEqual(s.answer("yes"), "E-001")

    def test_drafts_and_reminders(self):
        s = State(self.path)
        s.record_draft("d1", "SB-1", 3, "confirmation")
        s.record_draft("d2", "SB-1", 3, "deposit_reminder")
        self.assertEqual(s.confirmation_drafted(), {("SB-1", 3)})
        self.assertTrue(s.reminder_drafted("SB-1", "deposit"))
        self.assertFalse(s.reminder_drafted("SB-1", "balance"))


class PrecheckTest(unittest.TestCase):
    def test_inbox(self):
        st = State(os.devnull + "-none")
        mail, _ = mail_with([("GET", "/mailFolders/inbox/messages", {"value": []})])
        self.assertTrue(precheck.inbox_has_work(mail, st))  # never scanned
        st.mark_scanned("2026-10-08T00:00:00Z")
        self.assertFalse(precheck.inbox_has_work(mail, st))
        mail, _ = mail_with([("GET", "/mailFolders/inbox/messages", {"value": [{"id": "a"}]})])
        self.assertTrue(precheck.inbox_has_work(mail, st))

    def test_confirmations(self):
        st = State(os.devnull + "-none")
        r = ["NEW", "SB-1", "", "", "", "", "", "", "", "Entered", "https://drive/x"]
        sh, _ = sheet_with([r])
        self.assertTrue(precheck.confirmations_have_work(sh, st))
        st.record_draft("d1", "SB-1", 3, "confirmation")
        self.assertFalse(precheck.confirmations_have_work(sh, st))


if __name__ == "__main__":
    unittest.main()


class DeviceCodeTokenTest(unittest.TestCase):
    def test_cached_refresh_token_skips_sign_in_and_scope_has_no_send(self):
        with tempfile.TemporaryDirectory() as d:
            cache = os.path.join(d, "tok.json")
            with open(cache, "w") as f:
                f.write('{"refresh_token": "old"}')
            http = FakeHttp([("POST", "/token", {"access_token": "AT", "refresh_token": "new", "expires_in": 3600})])
            tok = DeviceCodeToken("cid", cache, http=http, out=lambda m: self.fail("asked to sign in"))
            self.assertEqual(tok(), "AT")
            self.assertNotIn("Send", DeviceCodeToken.SCOPE)
            with open(cache) as f:
                self.assertIn("new", f.read())

    def test_device_login_polls_until_authorized(self):
        with tempfile.TemporaryDirectory() as d:
            answers = iter([HttpError(400, "t", '{"error":"authorization_pending"}'),
                            {"access_token": "AT2", "refresh_token": "r", "expires_in": 3600}])

            def http(method, url, **kw):
                if url.endswith("/devicecode"):
                    return {"message": "go sign in", "device_code": "dc", "interval": 0, "expires_in": 60}
                a = next(answers)
                if isinstance(a, Exception):
                    raise a
                return a
            msgs = []
            tok = DeviceCodeToken("cid", os.path.join(d, "none.json"), http=http, out=msgs.append)
            self.assertEqual(tok(), "AT2")
            self.assertEqual(msgs, ["go sign in"])
