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
from tools.tests.test_emi import BOOKING, DLX, REAL_HEADER, appended, real_sheet
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

    def test_second_reply_names_the_older_one(self):
        a = dict(message_id="sim-01-request", all=False, kind="request", ref="TEST-REF-1", row="", to="", cc="",
                 internal=False)
        emi.draft_reply(self.mail, self.st, SimpleNamespace(body=self.body(GOOD), **a), out=self.lines.append)
        self.assertFalse(any(x.startswith("NOTE:") for x in self.lines))
        emi.draft_reply(self.mail, self.st, SimpleNamespace(body=self.body(GOOD), **a), out=self.lines.append)
        self.assertTrue(any(x.startswith("NOTE: #1 still pending for TEST-REF-1") for x in self.lines))
        self.assertEqual(self.st.data["reviews"]["1"]["status"], "pending")  # nothing changed, only said


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
