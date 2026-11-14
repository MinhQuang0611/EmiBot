"""End-of-day check at 23:30 (dev, 2026-11-14): every email of the day against Emi's record and the intake sheet,
so a booking or a cancellation that never reached the sheet is found the same day."""
import os
import unittest
from datetime import datetime, timezone
from unittest import mock

from tools import day_check
from tools.state import State
from tools.tests.test_ota_note_1114 import Mail, row
from tools.tests.test_reply_every_email_1113 import SYNXIS

NOW = datetime(2026, 11, 14, 16, 30, tzinfo=timezone.utc)  # 23:30 Vietnam time


def msg(sender, subject, received):
    return (sender, subject, "", received)


class DayCheckTest(unittest.TestCase):
    def setUp(self):
        self.st = State(os.devnull + "-none")
        self.lines = []

    def run_check(self, messages, rows):
        return day_check.run(Mail(messages), self.st, rows, now=NOW, out=self.lines.append)

    def marks(self, result):
        return {i["id"]: i["mark"] for i in result["items"]}

    def test_the_cases(self):
        messages = {
            # TA booking with its row (linked by the arrival minute)
            "ta": msg("res@agency.vn", "Booking Hoang family 20/11", "2026-11-14T02:05:00Z"),
            # TA booking closed with a reason, no row needed
            "inq": msg("sale@agency.vn", "Báo giá phòng tháng 12", "2026-11-14T03:00:00Z"),
            # never handled
            "lost": msg("op@agency.vn", "Đặt phòng đoàn 15 khách", "2026-11-14T04:00:00Z"),
            # SynXis cancellation handled but no CANCEL row
            "cx": msg(SYNXIS, "SynXis Res Cancelled (92777EF003350 )", "2026-11-14T05:00:00Z"),
            # agency cancellation, no CANCEL row, no question to Karen
            "tacx": msg("res@agency.vn", "Cancel booking Hoang family", "2026-11-14T06:00:00Z"),
            # outcome names rows the sheet doesn't have
            "claim": msg("res@other.vn", "Xác nhận đặt phòng", "2026-11-14T07:00:00Z"),
            # a booking closed as spam
            "spam": msg("res@third.vn", "New reservation request", "2026-11-14T08:00:00Z"),
            # plain noise
            "news": msg("promo@shop.com", "Sale 50%", "2026-11-14T09:00:00Z"),
            # still in hand
            "fresh": msg("res@agency.vn", "Booking new", "2026-11-14T16:25:00Z"),
            # two days ago, never done: listed too
            "old": msg("res@agency.vn", "Booking old", "2026-11-12T09:00:00Z"),
        }
        self.st.mark_processed("ta", "NEW rows 2100-2101 TA Hoang")
        self.st.mark_processed("inq", "inquiry answered #900")
        self.st.mark_processed("cx", "cancel noted")
        self.st.mark_processed("tacx", "reply #901")
        self.st.mark_processed("claim", "NEW row 2200 written")
        self.st.mark_processed("spam", "NO REPLY: spam")
        self.st.mark_processed("news", "NO REPLY: spam")
        rows = [row(2100, ref="TVR100", received_at="14/11/2026 09:05"),
                row(2101, ref="TVR100", received_at="14/11/2026 09:05"),
                row(1937)]
        result = self.run_check(messages, rows)
        self.assertEqual(self.marks(result), {"lost": "MISSING", "cx": "MISSING", "tacx": "CHECK", "claim": "MISSING",
                                              "spam": "CHECK", "old": "MISSING"})
        self.assertEqual((result["OK"], result["RECENT"]), (3, 1))
        text = "\n".join(self.lines)
        self.assertIn("never handled (not done)", text)
        self.assertIn("OTA cancellation with no CANCEL row", text)
        self.assertIn("id: lost", text)

    def test_an_ota_notice_needs_its_note(self):
        messages = {"n": msg(SYNXIS, "SynXis Res Confirmed (92777EF003350 )", "2026-11-14T05:00:00Z")}
        self.st.mark_processed("n", "NEW row 1937")
        self.st.data["processed"]["n"]["at"] = "2026-11-14T08:00:00Z"  # after the rule went live
        result = self.run_check(messages, [row(1937)])
        self.assertEqual(self.marks(result), {"n": "CHECK"})
        self.st.data["reviews"]["950"] = {"draft_id": "d", "status": "open", "source": "n", "kind": "ota_note"}
        self.assertEqual(self.run_check(messages, [row(1937)])["OK"], 1)

    def test_a_day_check_reason_closes_a_check_not_a_miss(self):
        messages = {"tacx": msg("res@agency.vn", "Cancel booking Hoang family", "2026-11-14T06:00:00Z"),
                    "cx": msg(SYNXIS, "SynXis Res Cancelled (92777EF003350 )", "2026-11-14T05:00:00Z")}
        self.st.mark_processed("tacx", "DAY CHECK: agency withdrew the cancellation in its next mail")
        self.st.mark_processed("cx", "DAY CHECK: fine")
        self.assertEqual(self.marks(self.run_check(messages, [row(1937)])), {"cx": "MISSING"})

    def test_an_ota_notice_handled_before_the_rule_needs_no_note(self):
        messages = {"n": msg(SYNXIS, "SynXis Res Confirmed (92777EF003350 )", "2026-11-14T05:00:00Z")}
        self.st.mark_processed("n", "NEW row 1937")
        self.st.data["processed"]["n"]["at"] = "2026-11-14T05:10:00Z"  # before ota-note existed
        self.assertEqual(self.run_check(messages, [row(1937)])["OK"], 1)

    def test_rows_named_in_the_outcome(self):
        self.assertEqual(day_check.named_rows("booking already row 2005; asked Karen E-470"), {2005})
        self.assertEqual(day_check.named_rows("NEW rows 1937-1939 Trip.com"), {1937, 1938, 1939})
        for refused in ("CHANGE row not written because the original booking is absent",
                        "CHANGE row refused: notes requires unknown meal plan",
                        "CHANGE row could not be appended because original booking and rate details are absent"):
            self.assertEqual(day_check.named_rows(refused), set(), refused)
        # 13/11 Agoda 1077442446 'booking already row 2005': the row is there under its SynXis number
        messages = {"a": msg("no-reply@agoda.com", "Agoda Booking ID 1077442446 - CONFIRMED", "2026-11-14T04:49:00Z"),
                    "i": msg("bookings@imity.example", "Re: Request for Early Check-in and Payment Details",
                             "2026-11-14T05:21:00Z"),
                    "w": msg("res@dmc.example", "Re: Availability - PAYMENT REMINDER #30640", "2026-11-14T08:49:00Z")}
        self.st.mark_processed("a", "booking already row 2005; asked Karen E-470")
        self.st.mark_processed("i", "early check-in; CHANGE row not written because original booking absent; E-408")
        self.st.mark_processed("w", "Payment slip logged row 2007; draft #867")
        for k in ("a", "i", "w"):
            self.st.data["processed"][k]["at"] = "2026-11-14T06:00:00Z"
        rows = [row(2005, ref="SynXis 92777EF003400 (Agoda)")]
        self.assertEqual(self.marks(self.run_check(messages, rows)), {"i": "CHECK", "w": "MISSING"})

    def test_machine_mail_closed_as_noise_is_fine(self):
        messages = {"b": msg("MicrosoftExchange329e@haya-hotels.com", "Undeliverable: RE: Booking confirmed", "2026-11-14T03:47:00Z"),
                    "o": msg("danniel@mgbedbank.example", "Out of Office RE: Booking Details AGTH0259", "2026-11-14T03:48:00Z"),
                    "s": msg("noreply-email@booking.com", "Reservations with today's or tomorrow's arrival date for Haya",
                             "2026-11-14T01:44:00Z"),
                    "r": msg("res@third.vn", "New reservation request", "2026-11-14T08:00:00Z")}
        for k in messages:
            self.st.mark_processed(k, "NO REPLY: alert")
        self.assertEqual(self.marks(self.run_check(messages, [])), {"r": "CHECK"})

    def test_the_telegram_line(self):
        ok = {"OK": 40, "CHECK": 0, "MISSING": 0, "RECENT": 2, "items": []}
        self.assertIn("tất cả đã xử lý", day_check.summary(ok, "14/11"))
        bad = {"OK": 38, "CHECK": 1, "MISSING": 1, "RECENT": 0,
               "items": [{"mark": "MISSING", "subject": "SynXis Res Cancelled <x>"}, {"mark": "CHECK", "subject": "B"}]}
        text = day_check.summary(bad, "14/11")
        self.assertIn("1 bị sót, 1 cần xem lại", text)
        self.assertIn("Sót: SynXis Res Cancelled &lt;x&gt;", text)

    def test_the_job_starts_job_6_only_on_work(self):
        calls = []
        fake = mock.Mock(side_effect=lambda cmd, **kw: calls.append(cmd) or mock.Mock(returncode=0, stdout="", stderr=""))
        for result, started in (({"OK": 3, "CHECK": 0, "MISSING": 0, "RECENT": 0, "items": []}, False),
                                ({"OK": 3, "CHECK": 0, "MISSING": 1, "RECENT": 0,
                                  "items": [{"mark": "MISSING", "subject": "x"}]}, True)):
            calls.clear()
            with mock.patch.object(day_check, "run", return_value=result), \
                    mock.patch("tools.config.state"), mock.patch("tools.config.sheet"), \
                    mock.patch("tools.config.live_sheet", return_value=None), mock.patch("tools.config.mail"), \
                    mock.patch("tools.config.telegram", return_value=None), \
                    mock.patch.object(day_check.subprocess, "run", fake):
                self.assertEqual(day_check.main(["job6"]), 0)
            self.assertEqual(bool(calls), started)


if __name__ == "__main__":
    unittest.main()
