"""Bookings sold after our stop sale (dev, 2026-11-26, on MG AGIN303795261 / HB2611523303, 3 QPL 02-04/01/2027,
mailed 25/11 23:49, and Tiket 80887501, 26-30/12: both sold on nights the chart had stopped since 21/11).
Dev: "booking từ các trang online đổ về tuy nhiên mình đã thông báo stop sales thì Emi ... phải email lại cho họ và
thông báo là booking này mình không nhận được do mình đã stop sales rồi". Chosen the same day: no row on the intake
sheet, the partner gets 24 hours after the chart to close its dates, the decline is a draft a person sends.
- what the partners were told is read from the charts in Sent Items (.xlsx), into spans per room code and night;
- sheet-append refuses such a NEW (STOP SALE LEAK) and keeps the leak for the decline;
- draft-reply --kind stop_sale_decline goes to the partner's stop-sale addresses, names the booking and the stop sale;
- done takes "STOP SALE LEAK" with its decline and no row; day-check doesn't call it missing."""
import io
import os
import shutil
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

from tools import day_check, emi
from tools import stop_sales as ss
from tools.state import State
from tools.tests.test_auto_send_1119 import AutoSendTest as Base

VN = timezone(timedelta(hours=7))
HEADER = ["Đêm", "Thứ", "Hạng", "Trạng thái", "Phòng mở", "Gồm các hạng"]
MG_REF = "MG AGIN303795261 / HB2611523303"


def chart(lines, as_dates=False):
    from openpyxl import Workbook
    wb = Workbook()
    wb.active.title = "Stop sale HAYA"
    ws = wb.create_sheet(ss.LIST_TAB)
    ws.append(HEADER)
    for night, room, codes, status in lines:
        ws.append([datetime(night.year, night.month, night.day) if as_dates else f"{night:%d/%m/%Y}",
                   f"{night:%a}", room, status, 0, codes])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


QPL = [(date(2027, 1, d), "Quadruple", "QPL", "STOPPED") for d in (2, 3)]
TPL = [(date(2026, 12, 27), "Triple", "TPL + TPL-SV", "NEW - 21/11/2026")]


class FakeSent:
    def __init__(self, mails):
        self.mails, self.fetched = mails, []

    def list_sent_since(self, since):
        return [m for m in self.mails if m["sentDateTime"] >= since]

    def list_attachments(self, mid):
        self.fetched.append(mid)
        return next(m for m in self.mails if m["id"] == mid)["files"]


def sent(mid, at, data, subject=None):
    return {"id": mid, "sentDateTime": at, "hasAttachments": True,
            "subject": subject or ss.subject(date(2026, 11, 21)),
            "files": [{"name": "Stop-Sale-HAYA-2026-11-21.xlsx", "data": data}]}


def booking(**kw):
    r = {"action": "NEW", "company": "MG", "booking_ref": MG_REF, "room_code": "QPL", "arrival": "02/01/2027",
         "departure": "04/01/2027", "received_at": "25/11/2026 23:49", "internal_notes": ""}
    r.update(kw)
    return r


class ChartTest(unittest.TestCase):
    def test_partners_by_company(self):
        self.assertEqual(ss.partner("MG"), "MG")
        self.assertEqual(ss.partner("Tiket.com"), "Tiket")
        self.assertEqual(ss.partner("CÔNG TY TNHH OHMYHOTEL&CO VN"), "OhMyHotel")
        self.assertEqual(ss.partner("WebBeds FZ LLC"), "WebBeds")
        self.assertEqual(ss.partner("Agoda"), "")  # not on the stop-sale list: SynXis sells its rooms
        self.assertEqual(len(ss.RECIPIENTS), 16)

    def test_sent_chart_read_with_its_room_codes(self):
        for as_dates in (False, True):
            closed, codes = ss.read_chart_xlsx(chart(QPL + TPL, as_dates))
            self.assertIn((date(2027, 1, 3), "Quadruple"), closed)
            self.assertEqual(codes["Triple"], ("TPL", "TPL-SV"))
            pairs, unknown = ss.closed_codes(closed, codes)
            self.assertIn(("TPL-SV", date(2026, 12, 27)), pairs)
            self.assertEqual(unknown, [])

    def test_a_room_without_codes_uses_the_names(self):
        pairs, unknown = ss.closed_codes({(date(2027, 1, 3), "Deluxe Sea View"), (date(2027, 1, 3), "Villa")}, {})
        self.assertEqual(pairs, {("DLX-SV", date(2027, 1, 3)), ("TW-DLX", date(2027, 1, 3))})
        self.assertEqual(unknown, ["Villa"])

    def test_spans_and_the_24_hours(self):
        spans = {}
        ss.apply_sent(spans, {("QPL", date(2027, 1, 2)), ("QPL", date(2027, 1, 3))}, "2026-11-21T02:00:00Z")
        at = lambda d, h: datetime(2026, 11, d, h, tzinfo=VN)  # noqa: E731
        self.assertEqual(len(ss.leaks(spans, "QPL", date(2027, 1, 2), date(2027, 1, 4), at(25, 23))), 2)
        self.assertEqual(ss.leaks(spans, "QPL", date(2027, 1, 2), date(2027, 1, 4), at(21, 20)), [])  # inside 24 h
        self.assertEqual(ss.leaks(spans, "TPL", date(2027, 1, 2), date(2027, 1, 4), at(25, 23)), [])
        # reopened on 24/11: a booking of 25/11 is fine, one of 23/11 was a leak
        ss.apply_sent(spans, {("QPL", date(2027, 1, 2))}, "2026-11-24T02:00:00Z")
        self.assertEqual([n for n, _, _ in ss.leaks(spans, "QPL", date(2027, 1, 2), date(2027, 1, 4), at(25, 23))],
                         [date(2027, 1, 2)])
        self.assertEqual(len(ss.leaks(spans, "QPL", date(2027, 1, 2), date(2027, 1, 4), at(23, 12))), 2)
        # stopped again: a new span, counted from its own send
        ss.apply_sent(spans, {("QPL", date(2027, 1, 2)), ("QPL", date(2027, 1, 3))}, "2026-11-25T10:00:00Z")
        self.assertEqual(len(spans["QPL|2027-01-03"]), 2)


class HistoryTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.st = State(os.path.join(self.dir, "state.json"))
        self.lines = []

    def test_sync_reads_each_sent_chart_once_in_order(self):
        mail = FakeSent([sent("b", "2026-11-24T02:00:00Z", chart(QPL[:1])),
                         sent("a", "2026-11-21T02:00:00Z", chart(QPL + TPL)),
                         sent("r", "2026-11-22T03:00:00Z", chart([]), subject="RE: " + ss.subject(date(2026, 11, 21)))])
        h = emi.sync_stop_sale_history(mail, self.st, out=self.lines.append)
        self.assertEqual(h["spans"]["QPL|2027-01-03"], [["2026-11-21T02:00:00Z", "2026-11-24T02:00:00Z"]])
        self.assertEqual(h["spans"]["QPL|2027-01-02"], [["2026-11-21T02:00:00Z", None]])
        self.assertNotIn("r", mail.fetched)  # a partner's reply on the thread is not a chart
        emi.sync_stop_sale_history(mail, self.st, out=self.lines.append)
        self.assertEqual(mail.fetched, ["a", "b"])  # nothing read twice
        self.assertIn("STOP SALE HISTORY", self.lines[0])

    def test_check_command(self):
        emi.sync_stop_sale_history(FakeSent([sent("a", "2026-11-21T02:00:00Z", chart(QPL))]), self.st,
                                   out=self.lines.append)
        hits = emi.print_stop_sale_check(self.st, "MG|QPL|02/01/2027|04/01/2027|25/11/2026 23:49",
                                         out=self.lines.append)
        self.assertEqual(len(hits), 2)
        self.assertIn("LEAK 02/01/2027 since 21/11/2026 09:00", self.lines[-1])
        self.assertEqual(emi.print_stop_sale_check(self.st, "Agoda|QPL|02/01/2027|04/01/2027|25/11/2026 23:49",
                                                   out=self.lines.append), [])


class LeakTest(Base):
    def setUp(self):
        super().setUp()
        emi.sync_stop_sale_history(FakeSent([sent("a", "2026-11-21T02:00:00Z", chart(QPL))]), self.st,
                                   out=lambda *_: None)

    def test_sheet_append_refuses_the_leak_and_writes_nothing(self):
        with self.assertRaises(emi.Refused) as e:
            emi.sheet_append(None, [booking()], out=self.lines.append, st=self.st)  # no sheet touched
        msg = str(e.exception)
        self.assertIn("STOP SALE LEAK", msg)
        self.assertIn("NO ROW", msg)
        self.assertIn("roomupdate@mgholiday.com", msg)
        self.assertEqual(self.st.data["stop_sale_leaks"][MG_REF]["since"], "21/11/2026 09:00")

    def test_not_a_leak(self):
        for rec in (booking(received_at="21/11/2026 20:00"),  # inside the 24 hours
                    booking(booking_ref="SynXis 92777EF003700 (Trip.com)", company="Trip.com"),  # our channel manager
                    booking(company="Agoda"),  # never told by email
                    booking(room_code="STD"),
                    booking(action="CHANGE"),
                    booking(internal_notes="Accepted by Karen despite stop sale E-750")):
            emi.check_stop_sale_leak(self.st, [rec], out=self.lines.append)
        self.assertNotIn("stop_sale_leaks", self.st.data)

    def test_no_history_is_said(self):
        self.st.data.pop("stop_sales_history")
        emi.check_stop_sale_leak(self.st, [booking()], out=self.lines.append)
        self.assertIn("STOP SALE NOT CHECKED", self.lines[-1])

    def leak(self):
        with self.assertRaises(emi.Refused):
            emi.check_stop_sale_leak(self.st, [booking()], out=self.lines.append)

    def decline(self, text, ref=MG_REF):
        path = os.path.join(self.dir, "body.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        args = SimpleNamespace(message_id="sim-01-new-1512", body=path, kind="stop_sale_decline", ref=ref, row="",
                               replaces="", to="", cc="", internal=False, sender_only=False, subject_suffix="")
        return emi.draft_reply(self.mail, self.st, args, tg=self.tg, out=self.lines.append)

    TEXT = ("Dear MG Reservations Team,\n\nThank you for booking AGIN303795261 (HB2611523303), 3 Quadruple rooms, "
            "02/01/2027 – 04/01/2027.\n\nWe are unable to accept this booking: Quadruple rooms on 02/01/2027 and "
            "03/01/2027 have been on stop sale in the chart we sent you on 21/11/2026 at 09:00 (Vietnam time, "
            "UTC+7).\n\nPlease cancel this booking on your side.\n\nBest regards,\nReservations Team")

    def test_decline_goes_to_the_partner_and_waits_for_a_person(self):
        self.leak()
        d = self.decline(self.TEXT)
        r = self.last()
        self.assertEqual(r["kind"], "stop_sale_decline")
        self.assertEqual(r["to"], ["roomupdate@mgholiday.com"])
        self.assertFalse(self.mail._meta(d["id"]).get("sent"))

    def test_decline_only_for_a_leak_and_saying_why(self):
        with self.assertRaises(emi.Refused):
            self.decline(self.TEXT)  # sheet-append never found it
        self.leak()
        with self.assertRaises(emi.Refused):
            self.decline(self.TEXT.replace("stop sale", "full"))
        with self.assertRaises(emi.Refused):
            self.decline(self.TEXT.replace("AGIN303795261 (HB2611523303)", "your booking"))

    def test_done_takes_the_leak_with_its_decline(self):
        self.leak()
        load = lambda: {"from": {"emailAddress": {"address": "noreply@mgbedbank.com"}},  # noqa: E731
                        "subject": "New booking AGIN303795261"}
        with self.assertRaises(emi.Refused) as e:
            emi.check_email_answered(self.st, "sim-01-new-1512", "STOP SALE LEAK: no row", load)
        self.assertIn("WITHOUT ITS DECLINE", str(e.exception))
        self.decline(self.TEXT)
        n = self.st.data["next_review"] - 1
        emi.check_email_answered(self.st, "sim-01-new-1512", f"STOP SALE LEAK: declined #{n}, no row", load)
        emi.check_email_answered(self.st, "other-id", f"STOP SALE LEAK: partner cancelled, declined #{n}", load)

    def test_day_check_does_not_call_it_missing(self):
        self.assertTrue(day_check.STOP_SALE_OUTCOME.search("STOP SALE LEAK: declined #12, no row"))
        self.assertTrue(day_check.NO_ROW_REASON.search("STOP SALE LEAK: declined #12, no row"))


if __name__ == "__main__":
    unittest.main()
