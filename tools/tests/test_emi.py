"""Offline tests for the job commands in tools/emi.py and tools/attachments.py."""
import base64
import io
import os
import tempfile
import unittest
import zipfile
from types import SimpleNamespace

from tools import attachments, emi
from tools import intake_schema as schema
from tools.intake_sheet import IntakeSheet
from tools.state import State
from tools.tests.test_tools import FakeHttp, mail_with

HEADER = ["action", "booking_ref", "guest_names", "company", "arrival", "departure", "rate_per_night_vnd",
          "room_code", "rooms", "missing_info", "tracy_status", "pdf_link"]


def sheet_with(data_rows):
    http = FakeHttp([("GET", "!1:1", {"values": [HEADER]}), ("GET", "!A3:", {"values": data_rows})])
    return IntakeSheet("SID", lambda m, u, body=None: http(m, u, body=body)), http


def b64(data):
    return base64.b64encode(data).decode()


class InboxNewTest(unittest.TestCase):
    def test_skips_processed_and_reports_scan_start(self):
        st = State(os.devnull + "-none")
        st.mark_scanned("2026-10-15T00:00:00Z")
        st.mark_processed("m1", "intake NEW SB-1")
        mail, http = mail_with([("GET", "/mailFolders/inbox/messages", {"value": [
            {"id": "m1", "receivedDateTime": "2026-10-15T01:00:00Z", "subject": "old"},
            {"id": "m2", "receivedDateTime": "2026-10-15T03:12:00Z", "subject": "NEW BOOKING",
             "from": {"emailAddress": {"name": "Sao Bien", "address": "sb@x.vn"}}, "hasAttachments": True}]})])
        lines = []
        msgs, started = emi.inbox_new(mail, st, out=lines.append)
        self.assertEqual([m["id"] for m in msgs], ["m2"])
        text = "\n".join(lines)
        self.assertIn(f"scan_started={started}", text)
        self.assertIn("15/10/2026 10:12", text)  # Vietnam time
        self.assertIn("[attachments]", text)
        self.assertIn("receivedDateTime ge 2026-10-15T00:00:00Z", http.calls[0][1])

    def test_first_scan_looks_back_24_hours(self):
        mail, http = mail_with([("GET", "/mailFolders/inbox/messages", {"value": []})])
        lines = []
        emi.inbox_new(mail, State(os.devnull + "-none"), out=lines.append)
        self.assertIn("first scan", lines[0])
        self.assertIn("receivedDateTime ge ", http.calls[0][1])


class ShowTest(unittest.TestCase):
    def test_thread_bodies_and_attachments(self):
        target = {"id": "m2", "conversationId": "c1"}
        thread = {"value": [
            {"id": "m1", "receivedDateTime": "2026-10-14T02:00:00Z", "subject": "Booking",
             "from": {"emailAddress": {"address": "sales@haya-hotels.com"}},
             "uniqueBody": {"content": "Our offer: 1,150,000"}, "body": {"content": "FULL m1"}},
            {"id": "d9", "isDraft": True, "body": {"content": "someone's draft"}},
            {"id": "m2", "receivedDateTime": "2026-10-15T02:00:00Z", "subject": "RE: Booking", "hasAttachments": True,
             "from": {"emailAddress": {"address": "sb@x.vn"}},
             "uniqueBody": {"content": "short"}, "body": {"content": "We confirm.\n> Our offer: 1,150,000"}}]}
        atts = {"value": [
            {"@odata.type": "#microsoft.graph.fileAttachment", "name": "rooming.csv", "contentBytes": b64(b"name,room\nAn,DLX")},
            {"@odata.type": "#microsoft.graph.fileAttachment", "name": "logo.png", "isInline": True, "contentBytes": b64(b"x" * 100)},
            {"@odata.type": "#microsoft.graph.itemAttachment", "name": "fwd.eml"}]}
        mail, http = mail_with([("GET", "/messages/m2/attachments", atts), ("GET", "/messages?", thread),
                                ("GET", "/messages/m2", target)])
        lines = []
        with tempfile.TemporaryDirectory() as d:
            emi.show(mail, "m2", work_dir=d, out=lines.append)
            saved = os.listdir(attachments.message_dir(d, "m2"))
        text = "\n".join(lines)
        self.assertIn("Our offer: 1,150,000", text)        # earlier message: unique part
        self.assertNotIn("FULL m1", text)
        self.assertIn("We confirm.", text)                 # target: full body
        self.assertNotIn("someone's draft", text)
        self.assertIn("name,room\nAn,DLX", text)
        self.assertIn("not a file, not saved", text)
        self.assertEqual(saved, ["rooming.csv"])           # inline logo skipped
        thread_call = next(c for c in http.calls if "/messages?" in c[1])
        self.assertIn("conversationId eq 'c1'", thread_call[1])


REAL_HEADER = open(os.path.join(os.path.dirname(__file__), "..", "..", "test", "fixtures", "intake-columns.csv"),
                   encoding="utf-8").readline().strip().split(",")
ROOM_CODES = [["DLX-SV", "DELUXE SEAVIEW", "HAYA"], ["TPL", "TRIPLE", "HAYA"],
              ["TW-DLX", "TWIN DELUXE", "HAYA", "Never for agencies"]]


def real_sheet(data_rows=(), codes=True):
    rules = [("GET", "!1:1", {"values": [REAL_HEADER]}), ("GET", "!A3:", {"values": [list(r) for r in data_rows]})]
    if codes:
        rules.insert(0, ("GET", "Room codes", {"values": ROOM_CODES}))
    http = FakeHttp(rules)
    return IntakeSheet("SID", lambda m, u, body=None: http(m, u, body=body)), http


def appended(http):
    call = next((c for c in http.calls if ":append" in c[1]), None)
    return None if call is None else [dict(zip(REAL_HEADER, v)) for v in call[2]["values"]]


BOOKING = {"action": "NEW", "received_at": "15/10/2026 11:56", "source_email": "TEST - Đặt phòng mới TEST-1510",
           "property": "HAYA", "channel_type": "TA", "company": "Công ty TEST Travel", "booking_ref": "TEST-1510",
           "guest_names": "Nguyễn Văn Test; TBA", "nationality": "Vietnam", "arrival": "20/11/2026",
           "departure": "22/11/2026", "nights": "2", "status": "Tentative", "priority": "Normal",
           "missing_info": "Full guest names; adults per room"}
DLX = {"room_code": "DLX-SV", "rooms": "2", "meal_plan": "BB", "rate_source": "TA card",
       "rate_per_night_vnd": "2000000", "Average rate per night after discount": "2000000", "total_vnd": "8000000"}
TPL = dict(DLX, room_code="TPL", rooms="1", rate_per_night_vnd="2300000",
           **{"Average rate per night after discount": "2300000", "total_vnd": "4600000"})


class SheetCommandsTest(unittest.TestCase):
    def test_booking_with_room_lines_becomes_one_row_per_room(self):
        sh, http = real_sheet()
        emi.sheet_append(sh, {"booking": BOOKING, "room_lines": [DLX, TPL]}, out=lambda *_: None)
        got = [(r["booking_ref"], r["room_code"], r["rooms"], r["arrival"], r["tracy_status"]) for r in appended(http)]
        self.assertEqual(got, [("TEST-1510", "DLX-SV", "2", "20/11/2026", "Pending"),
                               ("TEST-1510", "TPL", "1", "20/11/2026", "Pending")])
        with self.assertRaises(emi.Refused):
            emi.sheet_append(sh, {"booking": BOOKING, "room_lines": []}, out=lambda *_: None)

    def test_row_without_room_is_refused_unless_named_in_missing_info(self):
        # 2026-10-15: row 50 went in with no room_code/rate because any missing_info text excused it
        bare = {k: v for k, v in DLX.items() if k not in ("room_code", "rate_per_night_vnd")}
        sh, http = real_sheet()
        with self.assertRaises(emi.Refused) as e:
            emi.sheet_append(sh, {"booking": BOOKING, "room_lines": [bare]}, out=lambda *_: None)
        self.assertIn("room_code: required", str(e.exception))
        self.assertIsNone(appended(http))
        named = dict(BOOKING, missing_info="REQUIRED blank: room_code – not stated; rate_per_night_vnd – no room")
        sh, http = real_sheet()
        emi.sheet_append(sh, {"booking": named, "room_lines": [bare]}, out=lambda *_: None)
        self.assertEqual(len(appended(http)), 1)

    def test_all_problems_reported_at_once(self):
        bad = dict(BOOKING, arrival="2026-11-20", channel_type="Agency", property="Palma")
        line = dict(DLX, rate_per_night_vnd="2.000.000", room_code="DLX")
        sh, http = real_sheet()
        with self.assertRaises(emi.Refused) as e:
            emi.sheet_append(sh, {"booking": bad, "room_lines": [line]}, out=lambda *_: None)
        msg = str(e.exception)
        for part in ("arrival: '2026-11-20' is not DD/MM/YYYY", "channel_type: 'Agency' not allowed",
                     "property: 'Palma' not allowed", "rate_per_night_vnd: '2.000.000' must be digits only",
                     "room_code: 'DLX' is not on the Room codes tab"):
            self.assertIn(part, msg)
        self.assertIsNone(appended(http))

    def test_nights_children_and_agency_room_rules(self):
        cases = [(dict(BOOKING, nights="3"), DLX, "nights: 3 but arrival→departure is 2"),
                 (BOOKING, dict(DLX, children="2", child_ages="9"), "child_ages: 1 ages for 2 children"),
                 (BOOKING, dict(DLX, room_code="TW-DLX"), "never sold to agencies"),
                 (dict(BOOKING, source_email="see https://x"), DLX, "no links or email IDs"),
                 (dict(BOOKING, pdf_link="x"), DLX, "pdf_link: filled by the build tool")]
        for booking, line, expected in cases:
            sh, _ = real_sheet()
            with self.assertRaises(emi.Refused, msg=expected) as e:
                emi.sheet_check(sh, {"booking": booking, "room_lines": [line]}, out=lambda *_: None)
            self.assertIn(expected, str(e.exception))

    def test_total_mismatch_is_only_a_warning(self):
        sh, _ = real_sheet()
        lines = []
        emi.sheet_check(sh, {"booking": BOOKING, "room_lines": [dict(DLX, total_vnd="7000000")]}, out=lines.append)
        self.assertTrue(any(x.startswith("WARNING") and "total_vnd" in x for x in lines))

    def test_new_with_existing_ref_refused_change_allowed(self):
        existing = [["NEW", "", "", "", "", "", "", "", "TEST-1510"]]
        sh, http = real_sheet(existing)
        with self.assertRaises(emi.Refused):
            emi.sheet_append(sh, {"booking": BOOKING, "room_lines": [DLX]}, out=lambda *_: None)
        change = dict(BOOKING, action="CHANGE", what_changed="Dates 20–22 Nov → 21–23 Nov",
                      arrival="21/11/2026", departure="23/11/2026",
                      missing_info="ezfolio_group_code: not known yet")
        sh, http = real_sheet(existing)
        emi.sheet_append(sh, {"booking": change, "room_lines": [DLX]}, out=lambda *_: None)
        self.assertEqual(appended(http)[0]["action"], "CHANGE")

    def test_unknown_room_codes_tab_skips_that_check(self):
        sh, _ = real_sheet(codes=False)
        emi.sheet_check(sh, {"booking": BOOKING, "room_lines": [dict(DLX, room_code="ANY")]}, out=lambda *_: None)

    def test_update_checks_the_merged_row(self):
        row = [BOOKING.get(h, DLX.get(h, "")) for h in REAL_HEADER]
        sh, http = real_sheet([row])
        with self.assertRaises(emi.Refused):
            emi.sheet_update(sh, 3, {"arrival": "20-11-2026"}, out=lambda *_: None)
        emi.sheet_update(sh, 3, {"guest_names": "Nguyễn Văn Test; Trần Thị Test"}, out=lambda *_: None)
        self.assertTrue(any("values:batchUpdate" in c[1] for c in http.calls))

    def test_template_splits_booking_and_room_columns(self):
        sh, _ = real_sheet()
        t = schema.template(sh, "NEW")
        self.assertIn("arrival", t["booking"])
        self.assertIn("room_code", t["room_lines"][0])
        for col in ("tracy_status", "pdf_link", "ezfolio_group_code", "Payment 1"):
            self.assertNotIn(col, t["booking"])
            self.assertNotIn(col, t["room_lines"][0])
        self.assertIn("ezfolio_group_code", schema.template(sh, "CHANGE")["booking"])

    def test_find_by_ref_or_guest(self):
        sh, _ = sheet_with([["NEW", "SB-2", "Nguyen An"], ["NEW", "AN-9", "Ivan Petrov"]])
        self.assertEqual(len(emi.sheet_find(sh, "petrov", out=lambda *_: None)), 1)
        self.assertEqual(len(emi.sheet_find(sh, "sb-2", out=lambda *_: None)), 1)


class DraftCommandsTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.body = os.path.join(self.dir.name, "body.txt")
        with open(self.body, "w", encoding="utf-8") as f:
            f.write("Dear Ms. Hương,\n\nCan you please confirm <the dates>?\n\nBest,\nHAYA Team")

    def tearDown(self):
        self.dir.cleanup()

    def test_reply_text_goes_inside_body_with_line_breaks(self):
        mail, http = mail_with([("POST", "/createReply", {"id": "d1"}),
                                ("GET", "/messages/d1?$select=body",
                                 {"body": {"content": "<html><body dir=\"ltr\"><p>quoted</p></body></html>"}})])
        st = State(os.path.join(self.dir.name, "s.json"))
        args = SimpleNamespace(message_id="m1", body=self.body, all=False, kind="reply", ref="SB-2", row="")
        emi.draft_reply(mail, st, args, out=lambda *_: None)
        patch = [c for c in http.calls if c[0] == "PATCH" and "body" in (c[2] or {})][0][2]["body"]["content"]
        self.assertTrue(patch.startswith('<html><body dir="ltr"><div'))
        self.assertIn("Dear Ms. Hương,<br>\n<br>\nCan you please confirm &lt;the dates&gt;?", patch)
        self.assertTrue(patch.endswith("<p>quoted</p></body></html>"))
        self.assertIn("d1", st.data["drafts"])
        self.assertFalse(any(c[1].endswith(("/send", "/reply")) for c in http.calls))

    def test_confirmation_needs_ref_and_row(self):
        mail, http = mail_with()
        args = SimpleNamespace(message_id="m1", body=self.body, all=False, kind="confirmation", ref="SB-2", row="")
        with self.assertRaises(emi.Refused):
            emi.draft_reply(mail, State(os.devnull + "-none"), args, out=lambda *_: None)
        self.assertEqual(http.calls, [])


class StateProcessedTest(unittest.TestCase):
    def test_mark_scanned_forgets_week_old_ids(self):
        st = State(os.devnull + "-none")
        st.data["processed"] = {"old": {"at": "2026-10-01T00:00:00Z", "outcome": "x"},
                                "new": {"at": "2026-10-14T00:00:00Z", "outcome": "y"}}
        st.mark_scanned("2026-10-15T00:00:00Z")
        self.assertEqual(list(st.data["processed"]), ["new"])

    def test_mark_scanned_cli_rejects_non_timestamp(self):
        self.assertEqual(emi.main(["mark-scanned", "now"]), 2)


class ExtractTextTest(unittest.TestCase):
    def test_xlsx(self):
        from openpyxl import Workbook
        wb = Workbook()
        wb.active.title = "Rooming"
        wb.active.append(["Guest", "Room"])
        wb.active.append(["Ivan Petrov", "DLX-SV"])
        buf = io.BytesIO()
        wb.save(buf)
        text = attachments.extract_text("r.xlsx", buf.getvalue())
        self.assertIn("--- sheet Rooming ---", text)
        self.assertIn("Ivan Petrov\tDLX-SV", text)

    def test_docx(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("word/document.xml", "<w:document><w:p><w:r><w:t>Voucher 123</w:t></w:r></w:p></w:document>")
        self.assertIn("Voucher 123", attachments.extract_text("v.docx", buf.getvalue()))

    def test_broken_pdf_returns_note(self):
        self.assertTrue(attachments.extract_text("x.pdf", b"not a pdf").startswith("(could not read file"))

    def test_image_and_safe_name(self):
        self.assertIn("open the file", attachments.extract_text("slip.jpg", b"..."))
        self.assertEqual(attachments.safe_name('a/b:c?.pdf'), "a_b_c_.pdf")


if __name__ == "__main__":
    unittest.main()
