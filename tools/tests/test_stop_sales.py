"""Long's stop-sale chart to the partners (dev, 2026-11-21): Emi reads the newest "Stop Sale OTA — HAYA" sheet in the
Drive folder, sends it as .xlsx only when the closed nights differ from the last list, and sends it itself when
EMI_AUTO_SEND names stop_sales."""
import json
import os
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

from tools import emi, review
from tools import stop_sales as ss
from tools.graph_mail import GraphMail, auto_send_refusal
from tools.tests.test_replies import Base, SOURCE

TODAY = date(2026, 11, 21)
HEADER = ["Đêm", "Thứ", "Hạng", "Trạng thái", "Phòng mở", "Gồm các hạng"]
XLSX_BYTES = b"PK\x03\x04 chart"


def line(night, room, status="STOPPED"):
    return [f"{night:%d/%m/%Y}", f"{night:%a}", room, status, "0", "X"]


def n(day):
    return TODAY + timedelta(days=day)


class FakeDrive:
    """The Drive and Sheets calls stop_sales makes, on a folder of named sheets."""

    def __init__(self, files, lists):
        self.files, self.lists, self.exported = files, lists, []

    def __call__(self, method, url, body=None, raw=False):
        if "/export?" in url:
            self.exported.append(url)
            return XLSX_BYTES
        if "/values/" in url:
            fid = url.split("/spreadsheets/")[1].split("/")[0]
            return {"values": self.lists[fid]}
        return {"files": self.files}


def folder(rows, name="Stop Sale OTA — HAYA — 2026-11-21", created="2026-11-21T04:43:42Z", fid="ota1"):
    files = [{"id": "plain", "name": "Stop Sale — HAYA — 2026-11-21", "createdTime": created},
             {"id": "palma", "name": "Stop Sale OTA — Palma — 2026-11-21", "createdTime": created},
             {"id": fid, "name": name, "createdTime": created}]
    return FakeDrive(files, {fid: [HEADER] + rows, "plain": [HEADER], "palma": [HEADER]})


class ReadTest(Base):
    def test_only_the_haya_ota_file_is_read(self):
        drive = folder([line(n(0), "Standard Double"), line(n(1), "Superior Twin", "NEW - 21/11/2026"),
                        line(n(2), "Triple", "REOPENED - 21/11/2026")])
        data = ss.load(drive, "F")
        self.assertEqual(data["id"], "ota1")
        self.assertEqual(data["date"], TODAY)
        self.assertEqual(data["closed"], {(n(0), "Standard Double"), (n(1), "Superior Twin")})

    def test_newest_by_name_date_then_made(self):
        files = [{"id": "a", "name": "Stop Sale OTA — HAYA — 2026-11-20", "createdTime": "2026-11-21T09:00:00Z"},
                 {"id": "b", "name": "Stop Sale OTA — HAYA — 2026-11-21", "createdTime": "2026-11-21T01:00:00Z"},
                 {"id": "c", "name": "Stop Sale OTA — HAYA — 2026-11-21", "createdTime": "2026-11-21T04:00:00Z"}]
        self.assertEqual(ss.latest(FakeDrive(files, {}), "F")["id"], "c")

    def test_no_file_or_an_unknown_status_stops_the_list(self):
        with self.assertRaises(ss.StopSaleError):
            ss.latest(FakeDrive([{"id": "p", "name": "Stop Sale — HAYA — 2026-11-21"}], {}), "F")
        with self.assertRaises(ss.StopSaleError):
            ss.parse_list([HEADER, line(n(0), "Triple", "MAYBE")])
        with self.assertRaises(ss.StopSaleError):
            ss.parse_list([["Date", "Room"], line(n(0), "Triple")])

    def test_stale_chart(self):
        data = {"date": TODAY, "created": datetime(2026, 11, 21, 4, 43, tzinfo=timezone.utc)}
        self.assertEqual(ss.stale(data, datetime(2026, 11, 21, 5, 0, tzinfo=timezone.utc), TODAY), "")
        self.assertIn("hours ago", ss.stale(data, datetime(2026, 11, 21, 10, 0, tzinfo=timezone.utc), TODAY))
        self.assertIn("not today", ss.stale(data, datetime(2026, 11, 21, 5, 0, tzinfo=timezone.utc), n(1)))

    def test_emi_s_own_room_names_match_long_s(self):
        before = {(n(0), "DELUXE SEAVIEW"), (n(0), "SUITE SEAVIEW"), (n(1), "STANDARD DOUBLE")}
        now = {(n(0), "Deluxe Sea View"), (n(0), "Suite Sea View"), (n(1), "Standard Double")}
        self.assertEqual(ss.changes(now, before, TODAY), ([], []))


class RunTest(Base):
    def setUp(self):
        super().setUp()
        self.now = datetime(2026, 11, 21, 5, 0, tzinfo=timezone.utc)  # 12:00 in Vietnam
        p = mock.patch.object(emi, "_today_vn", lambda: TODAY)
        p.start()
        self.addCleanup(p.stop)
        real = ss.stale
        p = mock.patch.object(ss, "stale", lambda data, now, today: real(data, self.now, today))
        p.start()
        self.addCleanup(p.stop)
        # the host's .env names stop_sales in EMI_AUTO_SEND (since 21/11): a test that doesn't set it means "off"
        p = mock.patch.dict(os.environ, {"EMI_AUTO_SEND": ""})
        p.start()
        self.addCleanup(p.stop)

    def run_with(self, rows, tg=None, **kw):
        drive = folder(rows, **kw)
        self.lines = []
        out = emi.run_stop_sales(self.mail, self.st, tg, ss.load(drive, "F"), drive, out=self.lines.append)
        return drive, out

    def drafts(self):
        return [r for r in self.st.data["reviews"].values() if r["kind"] == "stop_sales"]

    def test_first_list_goes_with_long_s_chart_as_xlsx(self):
        drive, _ = self.run_with([line(n(0), "Standard Double")])
        d = self.drafts()[0]
        self.assertEqual(d["to"], [])
        self.assertEqual(d["bcc"], list(ss.RECIPIENTS))
        self.assertEqual(d["attachments"], ["Stop-Sale-HAYA-2026-11-21.xlsx"])
        meta = self.mail._meta(d["draft_id"])
        self.assertEqual(meta["attachments"][0]["contentType"], ss.XLSX)
        self.assertEqual(len(drive.exported), 1)
        self.assertIn("ota1/export?mimeType=application%2Fvnd.openxmlformats", drive.exported[0])
        self.assertEqual(self.st.data["stop_sales_report"]["file_id"], "ota1")

    def test_same_closed_nights_no_email(self):
        rows = [line(n(0), "Standard Double"), line(n(2), "Triple")]
        self.run_with(rows)
        drive, _ = self.run_with(rows, fid="ota2", created="2026-11-21T04:50:00Z")
        self.assertEqual(len(self.drafts()), 1)
        self.assertEqual(drive.exported, [])
        self.assertIn("no change", self.lines[-1])

    def test_long_s_new_marks_alone_are_not_a_change(self):
        self.run_with([line(n(0), "Standard Double")])
        self.run_with([line(n(0), "Standard Double", "NEW - 21/11/2026")], fid="ota2")
        self.assertEqual(len(self.drafts()), 1)

    def test_a_new_stop_and_a_reopen_are_listed(self):
        self.run_with([line(n(0), "Standard Double"), line(n(3), "Triple")])
        self.run_with([line(n(0), "Standard Double"), line(n(5), "Superior Twin", "NEW - 21/11/2026"),
                       line(n(3), "Triple", "REOPENED - 21/11/2026")], fid="ota2")
        text = self.drafts()[-1]["text"]
        self.assertIn("New stop sale:\n- 26 Nov 2026 (Thu): Superior Twin", text)
        self.assertIn("Re-open:\n- 24 Nov 2026 (Tue): Triple", text)
        self.assertEqual(self.st.data["reviews"]["1"]["status"], "replaced")

    def test_a_passed_night_is_no_change(self):
        self.st.data["stop_sales_report"] = {"rows": ss.to_state({(n(-1), "Triple"), (n(0), "Triple")})}
        self.run_with([line(n(0), "Triple")])
        self.assertEqual(self.drafts(), [])

    def test_stale_chart_no_email_and_the_last_list_stands(self):
        self.now = datetime(2026, 11, 21, 10, 0, tzinfo=timezone.utc)
        self.assertIsNone(self.run_with([line(n(0), "Triple")])[1])
        self.assertIn("STOP SALES NOT CHECKED", self.lines[0])
        self.assertEqual(self.st.data.get("stop_sales_report"), {})

    def test_preview_changes_nothing(self):
        drive = folder([line(n(0), "Triple")])
        emi.run_stop_sales(None, self.st, None, ss.load(drive, "F"), drive, preview=True, out=lambda x: None)
        self.assertEqual(self.drafts(), [])
        self.assertEqual(drive.exported, [])

    def test_auto_send_when_named(self):
        with mock.patch.dict(os.environ, {"EMI_AUTO_SEND": "stop_sales"}):
            self.run_with([line(n(0), "Triple")])
        r = self.drafts()[0]
        self.assertEqual(r["status"], "sent")
        self.assertTrue(self.mail._meta(r["draft_id"])["sent"])

    def test_not_named_stays_a_draft(self):
        with mock.patch.dict(os.environ, {"EMI_AUTO_SEND": "ota_note"}):
            self.run_with([line(n(0), "Triple")])
        self.assertFalse(self.mail._meta(self.drafts()[0]["draft_id"]).get("sent"))

    def test_telegram_mode_without_auto_waits_for_accept(self):
        tg = mock.Mock()
        tg.send.return_value = 7
        with mock.patch.dict(os.environ, {"EMI_DRAFT_MODE": "telegram"}):
            self.run_with([line(n(0), "Triple")], tg=tg)
        r = self.drafts()[0]
        self.assertTrue(r["draft_id"].startswith(review.PENDING))
        self.assertIn("Bcc:", tg.send.call_args[0][0])

    def test_chart_that_will_not_attach_takes_the_draft_back_out(self):
        with mock.patch.object(self.mail, "add_attachment", side_effect=OSError("boom")), \
                self.assertRaises(OSError):
            self.run_with([line(n(0), "Triple")])
        self.assertIsNone(self.mail.get_draft("sim-draft-001"))
        self.assertEqual(self.st.data.get("stop_sales_report"), {})

    def test_unreadable_folder_is_a_gap(self):
        with mock.patch.object(emi.config, "stop_sale_transport", side_effect=RuntimeError("HTTP 403")):
            data, why = emi.load_stop_sale()
        self.assertIsNone(data)
        self.assertIn("HTTP 403", why)

    def test_nobody_writes_a_list_by_hand(self):
        a = SimpleNamespace(message_id=SOURCE, to="roomupdate@mgholiday.com", cc="", subject="Stop Sale update",
                            body=self.body("Dear Partner,"), kind="reply", ref="", row="", attach=[], replaces="")
        with self.assertRaises(emi.Refused) as e:
            emi.draft_new(self.mail, self.st, a, out=self.lines.append)
        self.assertIn("daily stop-sales command", str(e.exception))


class RefusalTest(Base):
    def test_stop_sales_only_bcc_to_the_partner_list(self):
        bcc = [a.lower() for a in ss.RECIPIENTS]
        self.assertEqual(auto_send_refusal("stop_sales", [], [], bcc, "Dear Partner"), "")
        self.assertIn("partner list", auto_send_refusal("stop_sales", ["x@y.com"], [], bcc, "Dear Partner"))
        self.assertIn("partner list", auto_send_refusal("stop_sales", [], [], bcc + ["x@y.com"], "Dear Partner"))
        self.assertIn("Bcc", auto_send_refusal("pickup", ["x@y.com"], [], bcc, "Dear Partner"))


class GraphBccTest(Base):
    def test_bcc_reaches_graph(self):
        calls = []

        def http(method, url, headers=None, body=None):
            calls.append(json.loads(json.dumps(body)))
            return {"id": "d1"}

        GraphMail("sales@haya-hotels.com", lambda: "t", http=http).create_new_draft([], "S", "B", bcc=["a@x.com"])
        self.assertEqual(calls[0]["bccRecipients"], [{"emailAddress": {"address": "a@x.com"}}])
        self.assertEqual(calls[0]["toRecipients"], [])
