"""The daily stop-sell list (dev, 2026-11-05): merged room types, a PDF every day, a draft only when it changed."""
import json
import os
from datetime import date, timedelta
from types import SimpleNamespace
from unittest import mock

from pypdf import PdfReader

from tools import availability as avail
from tools import emi, review
from tools import stop_sales as ss
from tools.graph_mail import GraphMail
from tools.tests.test_replies import Base, SOURCE

D1 = date(2026, 12, 30)
NIGHTS = [D1 + timedelta(days=i) for i in range(4)]
PLENTY = 5


def sheet(**cells):
    """Every mapped code with PLENTY free every night; cells={'STD': [0, 5, 5, 5]} overrides a row. - is _ in a key."""
    rooms = {c: {"name": c, "total": 9, "free": dict(zip(NIGHTS, cells.get(c.replace("-", "_"), [PLENTY] * 4)))}
             for c in ss.MAPPED}
    return {"title": "Future Availability — HAYA — 2026-12-30_2027-04-01", "dates": NIGHTS, "rooms": rooms}


class MergeTest(Base):
    def test_merged_rows_are_added_before_the_limit(self):
        d = sheet(STD_TWN=[1, 0, 0, 2], SUP_TWN=[0, 2, 1, -1], TPL=[-1, 5, 5, 5], TPL_SV=[3, 5, 5, 5], QPL=[2, 1, 0, -1])
        self.assertEqual(ss.closed(d, D1), {
            (NIGHTS[0], "SUPERIOR TWIN"), (NIGHTS[2], "SUPERIOR TWIN"), (NIGHTS[3], "SUPERIOR TWIN"),
            (NIGHTS[1], "QUADRUPLE"), (NIGHTS[2], "QUADRUPLE"), (NIGHTS[3], "QUADRUPLE")})

    def test_twin_deluxe_goes_with_deluxe_seaview(self):
        d = sheet(TW_DLX=[0, 1, 1, 1], DLX_SV=[1, 1, 0, 5])
        self.assertEqual(ss.closed(d, D1), {(NIGHTS[0], "DELUXE SEAVIEW"), (NIGHTS[2], "DELUXE SEAVIEW")})

    def test_apartments_are_never_on_the_list(self):
        self.assertEqual(ss.closed(sheet(APT_02=[0] * 4, APT_04=[0] * 4), D1), set())

    def test_nights_before_today_left_out(self):
        self.assertEqual(ss.closed(sheet(STD=[0, 5, 5, 0]), NIGHTS[1]), {(NIGHTS[3], "STANDARD DOUBLE")})

    def test_a_room_code_not_in_the_map_stops_the_list(self):
        d = sheet()
        d["rooms"]["NEW-X"] = d["rooms"].pop("TPL-SV")
        self.assertEqual(ss.code_problem(sheet()), "")
        self.assertIn("new: NEW-X", ss.code_problem(d))
        self.assertIn("gone: TPL-SV", ss.code_problem(d))


class DailyTest(Base):
    def setUp(self):
        super().setUp()
        self.today = D1
        for name, value in (("_stale", lambda data: ""), ("_today_vn", lambda: self.today)):
            p = mock.patch.object(emi, name, value)
            p.start()
            self.addCleanup(p.stop)

    def run_day(self, data, day=None, tg=None, **kw):
        self.today = day or self.today
        self.lines = []
        return emi.run_stop_sales(self.mail, self.st, tg, data, out=self.lines.append, **kw)

    def drafts(self):
        return [r for r in self.st.data["reviews"].values() if r["kind"] == "stop_sales"]

    def pdf(self):
        path = os.path.join(self.dir, "stop-sales", f"Stop-Sell-HAYA-{self.today.isoformat()}.pdf")
        return "\n".join(p.extract_text() for p in PdfReader(path).pages)

    def test_first_list_goes_out_with_the_column_empty(self):
        rows = self.run_day(sheet(STD=[0, 5, 5, 5]))
        self.assertEqual([r["update"] for r in rows], [""])
        d = self.drafts()[0]
        self.assertEqual(d["to"], [])
        self.assertEqual(d["bcc"], list(ss.RECIPIENTS))
        self.assertEqual(d["attachments"], ["Stop-Sell-HAYA-2026-12-30.pdf"])
        self.assertIn("as of 30 Dec 2026", d["text"])
        self.assertNotIn("NEW UPDATE", d["text"])
        text = self.pdf()
        for word in ("NEW UPDATE", "HAYA Hotel Phu Quoc", "30 Dec 2026", "2026-12-30", "STANDARD DOUBLE", "STOP SELL"):
            self.assertIn(word, text)

    def test_nothing_closed_and_nothing_to_compare_no_draft(self):
        self.run_day(sheet())
        self.assertEqual(self.drafts(), [])

    def test_no_change_no_draft_but_the_pdf_is_made(self):
        d = sheet(STD=[0, 0, 5, 5])
        self.run_day(d)
        self.run_day(d, day=NIGHTS[1])  # the 30/12 line falling away is not an update
        self.assertEqual(len(self.drafts()), 1)
        self.assertIn("no change", self.lines[-1])
        self.assertIn("31 Dec 2026", self.pdf())

    def test_a_new_line_is_marked_that_day_only(self):
        self.run_day(sheet(STD=[0, 5, 5, 5]))
        rows = self.run_day(sheet(STD=[0, 5, 0, 5]), day=NIGHTS[0] + timedelta(days=1))
        self.assertEqual([(r["night"], r["update"]) for r in rows],
                         [(NIGHTS[2], "NEW - 31 Dec 2026")])
        self.assertIn("1 new stop sell line(s)", self.drafts()[-1]["text"])
        self.assertIn("NEW - 31 Dec 2026", self.pdf())
        rows = self.run_day(sheet(STD=[0, 5, 0, 5]), day=NIGHTS[2])
        self.assertEqual([r["update"] for r in rows], [""])

    def test_a_reopened_line_shows_once_then_goes(self):
        self.run_day(sheet(STD=[5, 0, 0, 5]))
        rows = self.run_day(sheet(STD=[5, 0, 5, 5]), day=NIGHTS[1])
        self.assertEqual([(r["night"], r["status"], r["update"]) for r in rows],
                         [(NIGHTS[1], "STOP SELL", ""), (NIGHTS[2], "OPEN", "REOPENED - 31 Dec 2026")])
        self.assertIn("1 line(s) reopened", self.drafts()[-1]["text"])
        self.run_day(sheet(STD=[5, 0, 5, 5]), day=NIGHTS[2])
        self.assertEqual(self.st.data["stop_sales_report"]["rows"], [])

    def test_second_run_the_same_day_does_nothing(self):
        self.run_day(sheet(STD=[0, 5, 5, 5]))
        self.assertIsNone(self.run_day(sheet(STD=[0, 0, 0, 0])))
        self.assertIn("already made", self.lines[0])
        self.assertEqual(len(self.drafts()), 1)

    def test_a_new_list_replaces_the_unsent_one(self):
        self.run_day(sheet(STD=[0, 5, 5, 5]))
        self.run_day(sheet(STD=[0, 0, 5, 5]), day=NIGHTS[0] + timedelta(days=1))
        self.assertEqual(self.st.data["reviews"]["1"]["status"], "replaced")
        self.assertEqual(self.st.data["reviews"]["2"]["status"], "pending")

    def test_preview_changes_nothing(self):
        self.run_day(sheet(STD=[0, 5, 5, 5]), preview=True)
        self.assertEqual(self.drafts(), [])
        self.assertEqual(self.st.data["stop_sales_report"], {})

    def test_stale_sheet_or_new_code_no_list_and_the_day_stays_open(self):
        d = sheet()
        d["rooms"].pop("QPL")
        self.assertIsNone(self.run_day(d))
        self.assertIn("STOP SALES NOT CHECKED: room codes differ", self.lines[0])
        with mock.patch.object(emi, "_stale", lambda data: "dated 01/10/2026, 90 day(s) ago"):
            self.assertIsNone(self.run_day(sheet(STD=[0] * 4)))
        self.assertIn("STOP SALES NOT CHECKED: availability sheet dated", self.lines[0])
        self.assertEqual(self.st.data["stop_sales_report"], {})

    def test_a_pdf_that_will_not_attach_takes_the_draft_back_out(self):
        with mock.patch.object(self.mail, "add_attachment", side_effect=OSError("boom")), \
                self.assertRaises(OSError):
            self.run_day(sheet(STD=[0, 5, 5, 5]))
        self.assertIsNone(self.mail.get_draft("sim-draft-001"))
        self.assertEqual(self.st.data["stop_sales_report"], {})

    def test_rewrite_keeps_the_bcc(self):
        self.run_day(sheet(STD=[0, 5, 5, 5]))
        review.rewrite(self.mail, self.st, None, "1", "Dear Partner,\n\nNew text.", out=self.lines.append)
        draft = self.mail._meta(self.st.data["reviews"]["1"]["draft_id"])
        self.assertEqual(draft["bcc"], list(ss.RECIPIENTS))

    def test_telegram_mode_waits_for_accept_with_the_pdf(self):
        tg = mock.Mock()
        tg.send.return_value = 7
        with mock.patch.dict(os.environ, {"EMI_DRAFT_MODE": "telegram"}):
            self.run_day(sheet(STD=[0, 5, 5, 5]), tg=tg)
        r = self.drafts()[0]
        self.assertTrue(r["draft_id"].startswith(review.PENDING))
        self.assertEqual(r["attachments"], ["Stop-Sell-HAYA-2026-12-30.pdf"])
        self.assertIn("Bcc:", tg.send.call_args[0][0])

    def test_nobody_writes_a_list_by_hand(self):
        a = SimpleNamespace(message_id=SOURCE, to="roomupdate@mgholiday.com", cc="", subject="Stop Sale update",
                            body=self.body("Dear Partner,"), kind="reply", ref="", row="", attach=[], replaces="")
        with self.assertRaises(emi.Refused) as e:
            emi.draft_new(self.mail, self.st, a, out=self.lines.append)
        self.assertIn("daily stop-sales command", str(e.exception))
        a = SimpleNamespace(message_id=SOURCE, kind="stop_sales", ref="", row="", body=self.body("x"), replaces="")
        with self.assertRaises(emi.Refused):
            emi.draft_reply(self.mail, self.st, a, out=self.lines.append)


class GraphBccTest(Base):
    def test_bcc_reaches_graph(self):
        calls = []

        def http(method, url, headers=None, body=None):
            calls.append(json.loads(json.dumps(body)))
            return {"id": "d1"}

        GraphMail("sales@haya-hotels.com", lambda: "t", http=http).create_new_draft([], "S", "B", bcc=["a@x.com"])
        self.assertEqual(calls[0]["bccRecipients"], [{"emailAddress": {"address": "a@x.com"}}])
        self.assertEqual(calls[0]["toRecipients"], [])


class ParsedSheetTest(Base):
    def test_a_real_parse_gives_merged_lines(self):
        rows = [["Room Type", "Number Of Rooms", "30/12 Wednesday", "31/12 Thursday"]]
        names = {c: f"{c} - X" for c in ss.MAPPED}
        rows += [[names[c], "5", "0" if c in ("STD-TWN", "SUP-TWN") else "2", "2"] for c in ss.MAPPED]
        data = avail.parse("Future Availability — HAYA — 2026-12-30_2027-01-01", rows)
        self.assertEqual(ss.code_problem(data), "")
        self.assertEqual(ss.closed(data, D1), {(D1, "SUPERIOR TWIN")})
