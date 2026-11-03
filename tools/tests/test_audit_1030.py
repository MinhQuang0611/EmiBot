"""Fixes from the audit of 30/10/2026 (emi-work/audit/2026-10-30-findings.md): front-office notes without the
intake sheet (F-01), an unreadable availability sheet doesn't stop the run (F-02), back-dated NEW rows warned
(F-03), a CHANGE keeps the booking's past arrival (F-04), Indian +20% (F-05), payment columns in the CHANGE
template (F-08), older pending drafts named (F-10), inferred nationality not missing info (F-13), quiet precheck
exits 0 for the agent (F-15)."""
import io
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from types import SimpleNamespace
from unittest import mock

from tools import config, emi, precheck, sim
from tools import intake_schema as schema
from tools.sim_mail import SimMail
from tools.state import State
from tools.tests.test_emi import BOOKING, DLX, REAL_HEADER, TPL, appended, real_sheet
from tools.tests.test_intake_consistency import check, has
from tools.tests.test_replies import GOOD
from tools.tests.test_tools import mail_with


class SimBase(unittest.TestCase):
    def setUp(self):
        self._mode = os.environ.pop("EMI_DRAFT_MODE", None)
        self.addCleanup(lambda: os.environ.__setitem__("EMI_DRAFT_MODE", self._mode) if self._mode else None)
        self.work = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.work, True)
        self.dir = sim.run_dir(self.work, "operational-request")
        shutil.copytree(os.path.join(sim.scenario_dir("operational-request"), "inbox"), os.path.join(self.dir, "inbox"))
        self.mail = SimMail(self.dir)
        self.st = State(os.path.join(self.dir, "state.json"))
        for target, name, value in ((emi, "WORK_DIR", self.dir), (config, "SIM_DIR", None)):
            p = mock.patch.object(target, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.lines = []

    def body(self, text, name="b.txt"):
        path = os.path.join(self.work, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path


class NoFrontOfficeForwardTest(SimBase):
    """dev 30/10: #205 (Agoda 1791966280, four requests) forwarded to haya@; the reviewer logged the requests in the
    booking's EZFOLIO notes instead, which is where front office sees them. Forwards are for payment slips."""

    def fwd(self, text, to):
        a = SimpleNamespace(message_id="sim-01-request", to=to, body=self.body(text), kind="forward",
                            ref="1791966280", row="")
        return emi.draft_forward(self.mail, self.st, a, out=self.lines.append)

    def test_forward_to_front_office_refused(self):
        for to in ("haya@haya-hotels.com", "HAYA@haya-hotels.com", "accountant@palmahotel.vn, haya@haya-hotels.com"):
            with self.assertRaisesRegex(emi.Refused, "notes item 5"):
                self.fwd("**Booking:** 1791966280 — chưa có mã đoàn\n**Yêu cầu:**\n• Phòng không hút thuốc", to)

    def test_slip_to_accounting_passes(self):
        self.fwd("Mã đoàn: #30511\n\nDear chị, em gửi UNC đặt cọc của Travel Concierge.", "accountant@palmahotel.vn")

    def test_skill_has_no_front_office_forward(self):
        path = os.path.join(os.path.dirname(__file__), "..", "..", "skills", "department-forwards.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertNotIn("Nhờ lễ tân", text)
        self.assertIn("EZFOLIO", text)


class PendingSameDraftTest(SimBase):
    """F-10: #183, #185, #188 — three replies on one booking all left pending."""

    def test_second_reply_refused_unless_it_replaces_the_older_one(self):
        # audit 03/11 replaces F-10's note: three Odeon drafts, an old reply sent after the new decision
        a = dict(message_id="sim-01-request", all=False, kind="request", ref="TEST-REF-1", row="", to="", cc="",
                 internal=False)
        old = emi.draft_reply(self.mail, self.st, SimpleNamespace(body=self.body(GOOD), **a), out=self.lines.append)
        with self.assertRaisesRegex(emi.Refused, "#1 .*--replaces 1"):
            emi.draft_reply(self.mail, self.st, SimpleNamespace(body=self.body(GOOD), **a), out=self.lines.append)
        with self.assertRaisesRegex(emi.Refused, "--replaces #7"):
            emi.draft_reply(self.mail, self.st, SimpleNamespace(body=self.body(GOOD), replaces="1,7", **a),
                            out=self.lines.append)
        emi.draft_reply(self.mail, self.st, SimpleNamespace(body=self.body(GOOD), replaces="1", **a),
                        out=self.lines.append)
        self.assertEqual(self.st.data["reviews"]["1"]["status"], "replaced")
        self.assertIsNone(self.mail.get_draft(old["id"]))  # out of Drafts, can't be sent by mistake
        self.assertEqual(self.st.data["reviews"]["2"]["status"], "pending")

    def test_accepted_but_unsent_draft_counts_too(self):
        a = dict(message_id="sim-01-request", all=False, kind="request", ref="TEST-REF-2", row="", to="", cc="",
                 internal=False)
        emi.draft_reply(self.mail, self.st, SimpleNamespace(body=self.body(GOOD), **a), out=self.lines.append)
        self.st.close_review("1", "approved", "Karen")
        with self.assertRaisesRegex(emi.Refused, "#1"):
            emi.draft_reply(self.mail, self.st, SimpleNamespace(body=self.body(GOOD), **a), out=self.lines.append)

    def test_other_booking_or_kind_not_blocked(self):
        a = dict(message_id="sim-01-request", all=False, kind="request", ref="TEST-REF-3", row="", to="", cc="",
                 internal=False)
        emi.draft_reply(self.mail, self.st, SimpleNamespace(body=self.body(GOOD), **a), out=self.lines.append)
        emi.draft_reply(self.mail, self.st, SimpleNamespace(body=self.body(GOOD), **dict(a, ref="TEST-REF-4")),
                        out=self.lines.append)
        emi.draft_reply(self.mail, self.st, SimpleNamespace(body=self.body(GOOD), **dict(a, kind="cancellation")),
                        out=self.lines.append)

    def test_html_tags_refused(self):
        a = dict(message_id="sim-01-request", all=False, kind="request", ref="TEST-REF-5", row="", to="", cc="",
                 internal=False)
        with self.assertRaisesRegex(emi.Refused, "HTML tags"):
            emi.draft_reply(self.mail, self.st, SimpleNamespace(body=self.body(GOOD.replace("\n\n", "<br><br>", 1)),
                                                                **a), out=self.lines.append)


class ChangeArrivalTest(unittest.TestCase):
    """F-04: Anex 112797913 in house 17-28/10, Traveloka payment after the stay — refused as a wrong year."""

    def test_check_row(self):
        past = dict(action="CHANGE", what_changed="Payment 1 received", ezfolio_group_code="1",
                    received_at="27/10/2026 17:43", arrival="17/10/2026", departure="19/10/2026")
        self.assertFalse(has(check(**past)[0], "arrival"))  # earlier rows not looked up: a warning only
        self.assertTrue(has(check(**past)[1], "arrival: 17/10/2026 is before the email"))
        row = dict(schema_row(), **past)
        self.assertFalse(has(schema.check_row(row, earlier_arrivals={"17/10/2026"})[0], "arrival"))
        self.assertTrue(has(schema.check_row(row, earlier_arrivals={"17/10/2025"})[0], "arrival"))
        # a NEW is still refused: "12 Nov" written as 12/11/2025
        self.assertTrue(has(check(arrival="12/11/2025", departure="14/11/2025", received_at="24/10/2026 18:28")[0],
                            "arrival: 12/11/2025 is before the email"))

    def existing(self):
        new = dict(BOOKING, received_at="10/10/2026 10:00", arrival="17/10/2026", departure="19/10/2026",
                   missing_info="", pdf_link="https://drive.google.com/built")
        return [[new.get(h, DLX.get(h, "")) for h in REAL_HEADER]]

    def change(self, **kw):
        c = dict(BOOKING, action="CHANGE", received_at="27/10/2026 17:43", what_changed="Payment 1 received 4,000,000",
                 arrival="", departure="", missing_info="ezfolio_group_code: not known yet")
        c.update(kw)
        return {"booking": c, "room_lines": [DLX]}

    def test_payment_after_the_stay_is_written(self):
        sh, http = real_sheet(self.existing())
        emi.sheet_append(sh, self.change(), out=lambda *_: None)
        self.assertEqual(appended(http)[0]["arrival"], "17/10/2026")

    def test_change_bringing_a_wrong_year_is_refused(self):
        sh, http = real_sheet(self.existing())
        with self.assertRaises(emi.Refused) as e:
            emi.sheet_append(sh, self.change(arrival="17/10/2025", departure="19/10/2025"), out=lambda *_: None)
        self.assertIn("earlier rows arrive 17/10/2026", str(e.exception))
        self.assertIsNone(appended(http))


def schema_row():
    from tools.tests.test_intake_consistency import ROW
    return dict(ROW)


class BackdatedNewTest(unittest.TestCase):
    """F-03: rows 74, 157, 196, 329 — NEW rows dated back to the original email for bookings HAYA had."""

    def lines(self, received):
        sh, _ = real_sheet()
        out = []
        with mock.patch.object(emi, "_today_vn", return_value=date(2026, 10, 30)):
            emi.sheet_check(sh, {"booking": dict(BOOKING, received_at=received), "room_lines": [DLX]}, out=out.append)
        return [x for x in out if "a NEW dated" in x]

    def test_old_received_at_warned(self):
        self.assertTrue(self.lines("25/09/2026 10:00"))
        self.assertFalse(self.lines("29/10/2026 23:34"))


class IndianRateTest(unittest.TestCase):
    """F-05: row 374 (nationality changed to India, rate left 1,700,000), rows 302-303."""
    TA = dict(channel_type="TA", company="Victoria DMC", rate_source="TA card", nationality="India", notes="",
              missing_info="")

    def test_no_plus_20_refused(self):
        self.assertTrue(has(check(**self.TA)[0], "rate_per_night_vnd: Indian guest"))
        self.assertTrue(has(check(**dict(self.TA, nationality="India"))[0], "rate_per_night_vnd: Indian guest"))

    def test_plus_20_or_flag_passes(self):
        self.assertFalse(has(check(**dict(self.TA, surcharge="+20% Indian guests (incl. in rate)"))[0],
                             "rate_per_night_vnd: Indian"))
        self.assertFalse(has(check(**dict(self.TA, missing_info="rate: Indian +20% not in the agency's rate"))[0],
                             "rate_per_night_vnd: Indian"))
        self.assertFalse(has(check(**dict(self.TA, nationality="Vietnam"))[0], "rate_per_night_vnd: Indian"))
        self.assertFalse(has(check(**dict(self.TA, channel_type="OTA", company="Agoda", rate_source="OTA net"))[0],
                             "rate_per_night_vnd: Indian"))


class InferredNationalityTest(unittest.TestCase):
    def test_inferred_is_not_missing_info(self):
        self.assertTrue(has(check(missing_info="nationality inferred from guest name")[0], "missing_info: 'nationality"))


class ChangeTemplateTest(unittest.TestCase):
    def test_change_template_has_payment_columns(self):
        sh, _ = real_sheet()
        self.assertIn("Payment 1", schema.template(sh, "CHANGE")["booking"])
        self.assertIn("Payment 2 date + time", schema.template(sh, "CHANGE")["booking"])
        self.assertNotIn("Payment 1", schema.template(sh, "NEW")["booking"])


class QuietPrecheckTest(unittest.TestCase):
    """F-15: 48 safety-net runs shown as 'Bash failed' because quiet exits 1."""

    def run_main(self, argv):
        st = State(os.devnull + "-none")
        st.mark_scanned("2026-10-30T00:00:00Z")
        mail, _ = mail_with([("GET", "/mailFolders/inbox/messages", {"value": []})])
        out = io.StringIO()
        with mock.patch.object(precheck.config, "state", return_value=st), \
                mock.patch.object(precheck.config, "mail", return_value=mail), redirect_stdout(out):
            return precheck.main(argv), out.getvalue().strip()

    def test_agent_flag_exits_0_when_quiet(self):
        self.assertEqual(self.run_main(["inbox", "--agent"]), (0, "quiet"))
        self.assertEqual(self.run_main(["inbox"]), (1, "quiet"))  # deploy/run-job.sh still reads exit 1


class AvailabilityUnreadableTest(unittest.TestCase):
    """F-02: HTTP 404 on the Future Availability sheet stopped runs 29/10 08:19 and 17:01."""

    def test_gap_and_carry_on(self):
        for argv, word in ((["availability", "--arrival", "01/12/2026", "--departure", "03/12/2026"],
                            "AVAILABILITY NOT CHECKED"), (["stop-sales"], "STOP SALES NOT CHECKED")):
            out = io.StringIO()
            with mock.patch.object(emi.config, "availability", side_effect=RuntimeError("HTTP 404")), \
                    redirect_stdout(out):
                self.assertEqual(emi.main(argv), 0, argv)
            self.assertIn("GAP: availability sheet not readable", out.getvalue())
            self.assertIn(word, out.getvalue())


if __name__ == "__main__":
    unittest.main()


def hit(items, needle):
    return any(needle in x for x in items)


class Audit0311RowTest(unittest.TestCase):
    """Audit 03/11: what landed in the EZFOLIO Notice (Jimit Gathani 1093, Travel Concierge 1119, Booking.com 1099),
    and the PMQ Loan1107TUS payment rows 1090-1091 and 1097."""

    def notes(self, items=None):
        base = {1: "Booking.com – Ref Booking.com 5010113979 / SynXis 92777EF002898", 2: "JIMIT GATHANI – India",
                3: "04/11/2026 – 07/11/2026", 4: "1 Quadruple – 4 adults, 0 children, BB", 5: "Arrival about 15:30",
                6: "Booking.com guest total 2,462,400 × 3 nights × 1 room = 7,387,200 VND",
                7: "Invoice: prepaid by Booking.com", 8: "No VAT info"}
        base.update(items or {})
        return "\n".join(f"{k}. {v}" for k, v in sorted(base.items()))

    def row(self, **kw):
        r = dict(schema_row(), company="Booking.com", channel_type="OTA", rate_source="Booking.com guest total",
                 booking_ref="Booking.com 5010113979 / SynXis 92777EF002898", guest_names="JIMIT GATHANI; guest TBA",
                 notes=self.notes())
        r.update(kw)
        return schema.check_row(r)[0]

    def test_clean_row_passes(self):
        self.assertFalse(hit(self.row(), "notes"))

    def test_internal_words_refused(self):
        self.assertTrue(hit(self.row(notes=self.notes(
            {7: "Payment slip 11,400,000 VND, pending accounting reconciliation"})), "internal_notes"))
        self.assertTrue(hit(self.row(notes=self.notes({5: "Guest disputes the price; verify the total"})),
                            "internal_notes"))

    def test_meal_plan_in_item_4(self):
        self.assertTrue(hit(self.row(notes=self.notes({4: "1 Quadruple – 4 adults, 0 children"})), "item 4"))

    def test_every_guest_in_item_2(self):
        names = "MR IBADULLA DAMIR; MR SEREDA YEVGENIY"
        self.assertTrue(hit(self.row(guest_names=names, notes=self.notes({2: "MR IBADULLA DAMIR – Russia"})),
                            "missing MR SEREDA YEVGENIY"))
        self.assertFalse(hit(self.row(guest_names=names, notes=self.notes({2: f"{names} – Russia"})), "item 2"))

    def test_booking_com_item_6_not_net(self):
        net = "Net 2,176,000 × 4 nights × 1 room = 8,704,000 VND (what Booking.com pays the hotel)"
        self.assertTrue(hit(self.row(notes=self.notes({6: net})), "guest total"))
        # every other OTA writes the net
        self.assertFalse(hit(self.row(company="Agoda", rate_source="OTA net", booking_ref="Agoda 1793076340",
                                      notes=self.notes({1: "Agoda – Ref Agoda 1793076340", 6: net})), "guest total"))

    def test_collect_and_prepaid_on_one_row_refused(self):
        self.assertTrue(hit(self.row(notes=self.notes({6: "Booking.com guest total 7,387,200 VND. Hotel collects",
                                                         7: "OTA prepaid; no payment due at hotel"})), "prepaid"))
        self.assertFalse(hit(self.row(COD="N/A (Booking.com – card guarantee, collect at hotel)",
                                      notes=self.notes({7: "Invoice: Booking.com – card guarantee, collect at hotel"})),
                             "prepaid"))


class Audit0311PaymentRowsTest(unittest.TestCase):
    def test_remaining_for_the_booking_shared_over_room_rows(self):
        data = {"booking": {"Remaining amount": "12450000"},
                "room_lines": [{"room_code": "DLX-SV", "total_vnd": "18000000"},
                               {"room_code": "TPL-SV", "total_vnd": "6900000"}]}
        out = emi.split_payments(data, out=lambda *_: None)
        left = [int(x["Remaining amount"]) for x in out["room_lines"]]
        self.assertEqual(sum(left), 12450000)
        self.assertEqual(left, [9000000, 3450000])
        self.assertNotIn("Remaining amount", out["booking"])

    def test_payment_change_repeats_every_room_type(self):
        built = dict(BOOKING, pdf_link="https://drive.google.com/built", missing_info="", ezfolio_group_code="28655")
        sh, http = real_sheet([[built.get(h, DLX.get(h, "")) for h in REAL_HEADER],
                               [built.get(h, TPL.get(h, "")) for h in REAL_HEADER]])
        change = dict(BOOKING, action="CHANGE", received_at="03/11/2026 09:20", what_changed="Balance paid",
                      missing_info="", **{"Payment 1": "12450000", "Payment 1 date + time": "02/11/2026 10:00"})
        with self.assertRaisesRegex(emi.Refused, "repeats every room type.*TPL"):
            emi.sheet_append(sh, {"booking": change, "room_lines": [DLX]}, out=lambda *_: None)
        self.assertFalse(appended(http))


class CancellationDaysTest(unittest.TestCase):
    def test_email_days_must_be_the_pdfs(self):
        pdf = "Cancellation policy: free cancellation up to 3 days before arrival."
        with self.assertRaisesRegex(emi.Refused, "7 days.*PDF says 3 days"):
            emi.check_cancellation_days("Free cancellation until 7 days before arrival.", pdf)
        emi.check_cancellation_days("Free cancellation until 3 days before arrival.", pdf)
        emi.check_cancellation_days("Hủy miễn phí trước 3 ngày.", pdf)
        emi.check_cancellation_days("Thank you for your booking.", pdf)  # no terms in the email: nothing to compare
