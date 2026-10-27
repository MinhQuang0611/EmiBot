"""Offline tests for the job commands in tools/emi.py and tools/attachments.py."""
import base64
import io
import os
import tempfile
import urllib.parse
import unittest
import zipfile
from types import SimpleNamespace
from unittest import mock

from tools import attachments, drive, emi
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
    def setUp(self):
        # The host's .env may have test mode on; these tests set it themselves.
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("EMI_TEST_ONLY_FROM", None)

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

    def test_test_mode_reads_only_the_test_sender(self):
        st = State(os.devnull + "-none")
        st.mark_scanned("2026-10-15T07:00:00Z")
        mail, _ = mail_with([("GET", "/mailFolders/inbox/messages", {"value": [
            {"id": "real", "receivedDateTime": "2026-10-15T07:01:00Z", "from": {"emailAddress": {"address": "ops@agency.vn"}}},
            {"id": "test", "receivedDateTime": "2026-10-15T07:05:00Z", "from": {"emailAddress": {"address": "Dev@Gmail.com"}}}]})])
        lines = []
        with mock.patch.dict(os.environ, {"EMI_TEST_ONLY_FROM": "dev@gmail.com"}):
            msgs, _ = emi.inbox_new(mail, st, out=lines.append)
        self.assertEqual([m["id"] for m in msgs], ["test"])
        self.assertIn("1 other email(s) in the window ignored", "\n".join(lines))
        self.assertFalse(st.is_processed("real"))  # left alone, not marked

    def test_mail_find_lists_ids_without_drafts(self):
        mail, http = mail_with([("GET", "/messages?", {"value": [
            {"id": "m1", "subject": "TEST - Đặt phòng TEST-1511", "receivedDateTime": "2026-10-15T07:05:00Z",
             "from": {"emailAddress": {"address": "dev@gmail.com"}}},
            {"id": "d1", "subject": "RE: TEST-1511", "isDraft": True}]})])
        lines = []
        hits = emi.mail_find(mail, 'TEST-1511"', out=lines.append)
        self.assertEqual([m["id"] for m in hits], ["m1"])
        self.assertIn('$search="TEST-1511"', http.calls[0][1])

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
DLX = {"room_code": "DLX-SV", "rooms": "2", "adults": "4", "meal_plan": "BB", "rate_source": "TA card",
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

    def test_total_with_surcharge_is_no_warning(self):
        sh, _ = real_sheet()
        lines = []
        line = dict(DLX, **{"Surcharge amount": "1050000", "total_vnd": "9050000"})
        emi.sheet_check(sh, {"booking": BOOKING, "room_lines": [line]}, out=lines.append)
        self.assertFalse(any(x.startswith("WARNING") and "total_vnd" in x for x in lines))

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

    def test_new_refused_when_one_of_its_numbers_is_on_the_sheet(self):
        sh, _ = real_sheet([["NEW", "", "", "", "", "", "", "", "1783017402 / 92777EF002717"]])
        with self.assertRaises(emi.Refused) as e:
            emi.sheet_append(sh, {"booking": dict(BOOKING, booking_ref="92777EF002717"), "room_lines": [DLX]},
                             out=lambda *_: None)
        self.assertIn("92777ef002717 is already on the sheet", str(e.exception))

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


def sheet_row(**cells):
    return [cells.get(h, "") for h in REAL_HEADER]


BUILT = dict(BOOKING, status="Definite", ezfolio_group_code="30255", confirmation_no="C-1", **DLX)
TPL_BUILT = dict(BUILT, **TPL)


class FollowUpRowsTest(unittest.TestCase):
    """Live sheet vs sandbox, 2026-10-27: follow-ups folded into old rows, CHANGE / CANCEL rows missing the
    group code, company, rates and pax, declined bookings cancelled twice, a cancel-and-rebuild refused."""
    CHANGE = dict(action="CHANGE", received_at="25/10/2026 13:56", source_email="Re: TEST-1510",
                  booking_ref="TEST-1510", what_changed="Payment 1 received", property="HAYA", status="Definite",
                  priority="Normal", **{"Payment 1": "4000000", "Payment 1 date + time": "25/10/2026 13:50"})

    def test_change_row_gets_the_bookings_details(self):
        sh, http = real_sheet([sheet_row(**BUILT), sheet_row(**TPL_BUILT)])
        lines = []
        emi.sheet_append(sh, {"booking": self.CHANGE, "room_lines": [{"room_code": "DLX-SV"}, {"room_code": "TPL"}]},
                         out=lines.append)
        rows = appended(http)
        self.assertEqual([(r["company"], r["channel_type"], r["ezfolio_group_code"], r["adults"],
                           r["rate_per_night_vnd"], r["Payment 1"]) for r in rows],
                         [("Công ty TEST Travel", "TA", "30255", "4", "2000000", "4000000"),
                          ("Công ty TEST Travel", "TA", "30255", "4", "2300000", "4000000")])
        self.assertTrue(any("blanks copied from row 3" in x for x in lines))

    def test_a_new_rate_keeps_its_own_surcharge(self):
        # Indian surcharge waived: the old "+20%" must not come back with the copied columns
        sh, http = real_sheet([sheet_row(**dict(BUILT, surcharge="+20% Indian guests"))])
        line = {"room_code": "DLX-SV", "rate_per_night_vnd": "2000000",
                "Average rate per night after discount": "2000000", "total_vnd": "8000000"}
        emi.sheet_append(sh, {"booking": dict(self.CHANGE, what_changed="Indian surcharge waived"),
                              "room_lines": [line]}, out=lambda *_: None)
        self.assertEqual(appended(http)[0]["surcharge"], "")

    def test_cancel_without_room_becomes_one_row_per_room_type(self):
        sh, http = real_sheet([sheet_row(**BUILT), sheet_row(**TPL_BUILT)])
        cancel = dict(self.CHANGE, action="CANCEL", what_changed="Cancelled by agency", status="Cancelled")
        emi.sheet_append(sh, {"booking": cancel, "room_lines": [{}]}, out=lambda *_: None)
        self.assertEqual([(r["action"], r["room_code"], r["total_vnd"], r["ezfolio_group_code"])
                          for r in appended(http)],
                         [("CANCEL", "DLX-SV", "8000000", "30255"), ("CANCEL", "TPL", "4600000", "30255")])

    def test_second_cancel_refused(self):
        closed = dict(BUILT, action="CANCEL", received_at="24/10/2026 09:00", status="Cancelled",
                      what_changed="On request booking cannot be accommodated")
        sh, http = real_sheet([sheet_row(**BUILT), sheet_row(**closed)])
        cancel = dict(self.CHANGE, action="CANCEL", what_changed="Cancelled by operator", status="Cancelled")
        with self.assertRaises(emi.Refused) as e:
            emi.sheet_append(sh, {"booking": cancel, "room_lines": [{}]}, out=lambda *_: None)
        self.assertIn("already cancelled (row 4", str(e.exception))
        self.assertIsNone(appended(http))

    def test_cancel_and_rebuild_in_one_file(self):
        sh, http = real_sheet([sheet_row(**BUILT)])
        cancel = dict(BUILT, action="CANCEL", received_at="26/10/2026 20:15", status="Cancelled",
                      what_changed="Cancelled and rebuilt as a new group", source_email="GD0512")
        new = dict(BOOKING, received_at="26/10/2026 20:15", status="Definite", **TPL)
        emi.sheet_append(sh, [cancel, new], out=lambda *_: None)
        self.assertEqual([r["action"] for r in appended(http)], ["CANCEL", "NEW"])

    def test_payment_and_built_rows_are_not_edited(self):
        sh, _ = real_sheet([sheet_row(**BUILT)])
        with self.assertRaises(emi.Refused) as e:
            emi.sheet_update(sh, 3, {"Payment 1": "4000000"}, out=lambda *_: None)
        self.assertIn("a payment is a CHANGE row", str(e.exception))
        sh, _ = real_sheet([sheet_row(**dict(BUILT, tracy_status="Entered", pdf_link="x.pdf"))])
        with self.assertRaises(emi.Refused) as e:
            emi.sheet_update(sh, 3, {"guest_names": "Omar"}, out=lambda *_: None)
        self.assertIn("already built in EZFOLIO", str(e.exception))


def chip(uri):
    return {"sheets": [{"data": [{"rowData": [{"values": [{"formattedValue": "conf.pdf", "chipRuns": [
        {"chip": {"richLinkProperties": {"uri": uri, "mimeType": "application/pdf"}}}]}]}]}]}]}


class ConfirmationPdfTest(unittest.TestCase):
    URL = "https://drive.google.com/file/d/1GweAj-7rXEtOT9lLsQkZF65_Hq3nGedU/view?usp=drive_link"
    FID = "1GweAj-7rXEtOT9lLsQkZF65_Hq3nGedU"

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.body = os.path.join(self.dir.name, "body.txt")
        with open(self.body, "w", encoding="utf-8") as f:
            f.write("Dear Mr. Minh,\n\n**Total:** VND 7,050,000, including breakfast, VAT and service charge.\n\n"
                    "• 50% deposit by 14:00 on 17/10/2026, Vietnam time.\n\n"
                    "**Account name:** CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC\n**Account number:** 1020729617\n\n"
                    "Best,\nHAYA Team")
        self.row = [BOOKING.get(h, DLX.get(h, "")) for h in REAL_HEADER]

    def tearDown(self):
        self.dir.cleanup()

    def sheet(self, cell, mime="application/pdf", data=b"%PDF-1.4 conf"):
        def http(method, url, body=None, raw=False):
            u = urllib.parse.unquote(url)
            if "fields=sheets.data.rowData" in u:
                return cell
            if "alt=media" in u:
                self.assertTrue(raw)
                return data
            if "/drive/v3/files/" in u:
                return {"name": "TEST-1511 confirmation.pdf", "mimeType": mime}
            if "!1:1" in u:
                return {"values": [REAL_HEADER]}
            if "!A3:" in u:
                return {"values": [self.row]}
            return {}
        return IntakeSheet("SID", http)

    def args(self):
        return SimpleNamespace(message_id="m1", row=3, body=self.body, all=False)

    def test_file_id_from_drive_links(self):
        self.assertEqual(drive.file_id(self.URL), self.FID)
        self.assertEqual(drive.file_id(f"https://drive.google.com/open?id={self.FID}"), self.FID)
        self.assertIsNone(drive.file_id("https://example.com/conf.pdf"))

    def test_link_in_cell_reads_chip_hyperlink_or_text(self):
        self.assertEqual(self.sheet(chip(self.URL)).link_in_cell(3, "pdf_link"), self.URL)
        hyper = {"sheets": [{"data": [{"rowData": [{"values": [{"hyperlink": self.URL, "formattedValue": "x"}]}]}]}]}
        self.assertEqual(self.sheet(hyper).link_in_cell(3, "pdf_link"), self.URL)
        empty = {"sheets": [{"data": [{"rowData": [{"values": [{"formattedValue": "conf.pdf"}]}]}]}]}
        self.assertIsNone(self.sheet(empty).link_in_cell(3, "pdf_link"))

    def test_no_pdf_link_no_draft(self):
        mail, http = mail_with()
        empty = {"sheets": [{"data": [{"rowData": [{}]}]}]}
        with self.assertRaises(emi.Refused):
            emi.draft_confirmation(mail, self.sheet(empty), State(os.devnull + "-none"), self.args(), out=lambda *_: None)
        self.assertEqual(http.calls, [])

    def test_not_a_pdf_no_draft(self):
        mail, http = mail_with()
        with mock.patch.object(emi, "WORK_DIR", self.dir.name), self.assertRaises(emi.Refused) as e:
            emi.draft_confirmation(mail, self.sheet(chip(self.URL), mime="image/png", data=b"\x89PNG"),
                                   State(os.devnull + "-none"), self.args(), out=lambda *_: None)
        self.assertIn("not a PDF", str(e.exception))
        self.assertEqual(http.calls, [])

    def test_pdf_attached_to_reply_draft_and_recorded(self):
        mail, http = mail_with([("POST", "/createReply", {"id": "d1"}),
                                ("GET", "/messages/d1?$select=body", {"body": {"content": "<html><body></body></html>"}})])
        st = State(os.path.join(self.dir.name, "s.json"))
        with mock.patch.object(emi, "WORK_DIR", self.dir.name):
            emi.draft_confirmation(mail, self.sheet(chip(self.URL)), st, self.args(), out=lambda *_: None)
        att = next(c for c in http.calls if c[1].endswith("/messages/d1/attachments"))[2]
        self.assertEqual((att["name"], att["contentType"]), ("TEST-1511 confirmation.pdf", "application/pdf"))
        self.assertEqual(base64.b64decode(att["contentBytes"]), b"%PDF-1.4 conf")
        self.assertEqual(st.confirmation_drafted(), {("TEST-1510", 3)})
        with mock.patch.object(emi, "WORK_DIR", self.dir.name), self.assertRaises(emi.Refused):
            emi.draft_confirmation(mail, self.sheet(chip(self.URL)), st, self.args(), out=lambda *_: None)
        # a person deleted that draft: forgetting it allows a new one
        self.assertTrue(st.forget_confirmation("TEST-1510", 3))
        self.assertNotIn("d1", st.data["drafts"])
        self.assertFalse(st.forget_confirmation("TEST-1510", 3))
        with mock.patch.object(emi, "WORK_DIR", self.dir.name):
            emi.draft_confirmation(mail, self.sheet(chip(self.URL)), st, self.args(), out=lambda *_: None)


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
        self.assertIn("<p>Dear Ms. Hương,</p>\n<p>Can you please confirm &lt;the dates&gt;?</p>", patch)
        self.assertTrue(patch.endswith("<p>quoted</p></body></html>"))
        self.assertIn("d1", st.data["drafts"])
        self.assertFalse(any(c[1].endswith(("/send", "/reply")) for c in http.calls))

    def test_text_to_html_bold_lists_paragraphs(self):
        from tools.graph_mail import text_to_html
        h = text_to_html("Kính gửi chị Ân,\n\n**Mã đoàn:** #29519\n**Số xác nhận:** 25694\n\n"
                         "**Điều khoản thanh toán:**\n\n• Đặt cọc 50% <ngay>\n• 50% còn lại\nĐặt phòng sẽ tự hủy.\n\nBest,\nHAYA Team")
        self.assertNotIn("**", h)
        self.assertIn("<p><b>Mã đoàn:</b> #29519<br>\n<b>Số xác nhận:</b> 25694</p>", h)
        self.assertIn("<ul><li>Đặt cọc 50% &lt;ngay&gt;</li><li>50% còn lại</li></ul>\n<p>Đặt phòng sẽ tự hủy.</p>", h)
        self.assertTrue(h.endswith("<p>Best,<br>\nHAYA Team</p>"))

    def test_labels_bold_without_markup(self):
        # 2026-10-15: Emi wrote the template without ** — labels must still come out bold.
        from tools.graph_mail import text_to_html
        h = text_to_html("Vui lòng xem thông tin xác nhận đặt phòng và PDF đính kèm như sau:\n\n"
                         "Mã đoàn: #29519\nTổng tiền: 18.450.000 VND\n\nLưu ý:\n\n"
                         "• Hạn 15:24 ngày 17/10/2026\nHạn giữ phòng 15:24 hôm nay")
        self.assertIn("<b>Mã đoàn:</b> #29519<br>\n<b>Tổng tiền:</b> 18.450.000 VND", h)
        self.assertIn("<p><b>Lưu ý:</b></p>", h)
        self.assertIn("<p>Vui lòng xem", h)                 # long sentence ending in ':' is not a label
        self.assertIn("<li>Hạn 15:24 ngày 17/10/2026</li>", h)  # no bold inside list items
        self.assertIn("<p>Hạn giữ phòng 15:24 hôm nay</p>", h)  # a time is not a label

    def test_confirmation_text_must_follow_template(self):
        with self.assertRaises(emi.Refused) as e:
            emi.check_confirmation_text("Kính gửi anh Minh,\nĐây là email test.\nBest,\nHAYA Team")
        self.assertIn("bank account number", str(e.exception))
        emi.check_confirmation_text("hạn giữ phòng 14:00 ngày 17/10/2026 (giờ Việt Nam)\n"
                                    "Tổng tiền: 1 VND, bao gồm ăn sáng, VAT và phí dịch vụ.\n"
                                    "CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC 1020729617\nBest,\nHAYA Team")

    def test_anh_chi_greeting_leaves_no_lone_chi(self):
        base = ("Kính gửi anh/chị Minh,\nhạn giữ phòng 15:42 ngày 17/10/2026 (giờ Việt Nam, UTC+7)\n"
                "Tổng tiền: 1 VND, bao gồm ăn sáng, VAT và phí dịch vụ.\n"
                "CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC 1020729617\n• 50% còn lại vui lòng thanh toán\n")
        # TEST-1511, 2026-10-15: the VAT line kept the template's "Chị vui lòng"
        with self.assertRaises(emi.Refused) as e:
            emi.check_confirmation_text(base + "Chị vui lòng bổ sung mã số thuế.\nBest,\nHAYA Team")
        self.assertIn("Chị vui lòng bổ sung mã số thuế.", str(e.exception))
        emi.check_confirmation_text(base + "Anh/Chị vui lòng bổ sung mã số thuế.\nBest,\nHAYA Team")
        emi.check_confirmation_text(base.replace("anh/chị", "chị") + "Chị vui lòng bổ sung.\nBest,\nHAYA Team")

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
