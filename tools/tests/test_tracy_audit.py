"""Tracy's audit of 29/10/2026 (test/TRACY AUDIT 29.10.26.md): a best-answer draft with a '[CHECK BEFORE SENDING]'
line, no Karen in drafts, phishing senders dropped, forwards made once, reply all, the stop-sales list, and a
sheet without tracy_status whose EZFOLIO columns Emi never writes."""
import os
import shutil
import unittest
from datetime import date
from types import SimpleNamespace

from tools import availability as avail
from tools import emi, sim
from tools.graph_mail import text_to_html
from tools.intake_sheet import IntakeSheet, SheetContractError
from tools.sim_mail import SimMail
from tools.state import State
from tools.tests.test_availability import data as avail_data
from tools.tests.test_replies import Base, GOOD, SOURCE, args
from tools.tests.test_tools import FakeHttp, mail_with

CHECK = "[CHECK BEFORE SENDING: late check-out fee is my reading of the FAQ]"


class CheckLineTest(unittest.TestCase):
    def test_check_line_on_top_passes_and_is_bold_red(self):
        text = f"{CHECK}\nDear Zion,\n\nLate check-out until 18:00 is 50% of one night.\n\nBest regards,\nReservations Team"
        emi.check_no_gaps(text, "m1")
        html = text_to_html(text)
        self.assertIn('<b><span style="color:#FF0000">[CHECK BEFORE SENDING:', html)
        self.assertNotIn("background", html)

    def test_check_line_anywhere_else_refused(self):
        with self.assertRaises(emi.Refused) as e:
            emi.check_no_gaps(f"Dear Zion,\n\n{CHECK}\n\nBest regards,\nReservations Team")
        self.assertIn("one line at the very top", str(e.exception))

    def test_gap_inside_still_refused_and_points_to_the_check_line(self):
        with self.assertRaises(emi.Refused) as e:
            emi.check_no_gaps(f"{CHECK}\nDear Zion,\n\nPool: [indoor or outdoor: hotel to confirm]\n", "m1")
        self.assertIn("[CHECK BEFORE SENDING:", str(e.exception))

    def test_karen_never_named(self):
        with self.assertRaises(emi.Refused) as e:
            emi.check_no_gaps("Dear Zion,\n\nKaren will confirm.\n\nBest regards,\nReservations Team")
        self.assertIn("never put Karen's name", str(e.exception))
        emi.check_no_gaps("Dear Zion,\n\nWe confirm.\n\nBest regards,\nReservations Team")


class PhishingTest(unittest.TestCase):
    def test_fake_booking_senders_are_not_listed(self):
        st = State(os.devnull + "-none")
        st.mark_scanned("2026-10-29T00:00:00Z")
        mail, _ = mail_with([("GET", "/mailFolders/inbox/messages", {"value": [
            {"id": "p1", "receivedDateTime": "2026-10-29T01:00:00Z", "subject": "New booking",
             "from": {"emailAddress": {"address": "care@mail.myjorney.com"}}},
            {"id": "p2", "receivedDateTime": "2026-10-29T01:05:00Z", "subject": "New booking",
             "from": {"emailAddress": {"address": "VIP@mail.voyageandco.com"}}},
            {"id": "ok", "receivedDateTime": "2026-10-29T01:10:00Z", "subject": "Booking",
             "from": {"emailAddress": {"address": "ops@agency.vn"}}}]})])
        lines = []
        msgs, _ = emi.inbox_new(mail, st, out=lines.append)
        self.assertEqual([m["id"] for m in msgs], ["ok"])
        self.assertNotIn("myjorney", "\n".join(lines))


class ForwardOnceTest(Base):
    def fwd(self, to="accountant@palmahotel.vn"):
        a = SimpleNamespace(message_id=SOURCE, to=to, body=self.body("**Booking:** x"), kind="forward", ref="", row="")
        return emi.draft_forward(self.mail, self.st, a, out=self.lines.append)

    def test_second_forward_to_the_same_address_refused(self):
        self.fwd()
        with self.assertRaises(emi.Refused) as e:
            self.fwd()
        self.assertIn("never forward twice", str(e.exception))
        self.fwd("booking@palmahotel.vn")  # another address is a different forward

    def test_denied_forward_may_be_redone(self):
        self.fwd()
        self.st.data["reviews"]["1"]["status"] = "denied"
        self.fwd()


class ReplyAllTest(Base):
    def test_reply_keeps_to_and_cc_by_default(self):
        shutil.copytree(os.path.join(sim.scenario_dir("operational-request"), "inbox"),
                        os.path.join(self.dir, "inbox"), dirs_exist_ok=True)
        self.mail = SimMail(self.dir)
        d = emi.draft_reply(self.mail, self.st, args(self.body(GOOD), message_id="sim-01-request"),
                            out=self.lines.append)
        self.assertTrue(self.st.data["reviews"]["1"]["reply_all"])
        self.assertEqual(self.mail._meta(d["id"])["to"][0], "sim-guest-kr@example.com")
        d = emi.draft_reply(self.mail, self.st, args(self.body(GOOD), message_id="sim-01-request", sender_only=True),
                            out=self.lines.append)
        self.assertFalse(self.st.data["reviews"]["2"]["reply_all"])


class StopSalesTest(unittest.TestCase):
    def test_one_room_or_fewer_listed_with_ranges(self):
        d = avail_data()
        low = avail.low_inventory(d, date(2026, 12, 30))
        self.assertIn("TPL-SV", low)  # -1 on 30/12
        for code, nights in low.items():
            self.assertTrue(all(d["rooms"][code]["free"][n] <= 1 for n in nights), code)
        self.assertEqual(avail.low_inventory(d, date(2027, 1, 3)), {})  # nothing from a date past the window
        self.assertIn("STOP SALES NEEDED", avail.render_low(d, low))
        self.assertEqual(avail._ranges([date(2027, 1, 1), date(2027, 1, 2), date(2027, 1, 5)]),
                         ["01/01/2027–02/01/2027", "05/01/2027"])


class SheetWithoutTracyStatusTest(unittest.TestCase):
    def sheet(self, header):
        http = FakeHttp([("GET", "!1:1", {"values": [header]})])
        return IntakeSheet("SID", lambda m, u, body=None: http(m, u, body=body)), http

    def test_append_on_the_live_layout(self):
        header = ["action", "booking_ref", "ezfolio_group_code", "pdf_link"]
        sh, http = self.sheet(header)
        sh.append_rows([{"action": "NEW", "booking_ref": "X1", "tracy_status": "Pending"}])
        call = next(c for c in http.calls if ":append" in c[1])
        self.assertEqual(call[2]["values"], [["NEW", "X1", "", ""]])

    def test_columns_51_to_55_and_ez_columns_never_written(self):
        header = [f"c{i}" for i in range(1, 51)] + ["ez_status", "ez_build", "ez_error", "ez_at", "ez_by", "c56"]
        sh, _ = self.sheet(header)
        for col in ("ez_error", "ez_by", "pdf_link"):
            with self.assertRaises(SheetContractError, msg=col):
                sh.update_cells(5, {col: "x"})
        renamed = [f"c{i}" for i in range(1, 51)] + ["status A", "status B", "error", "at", "by"]
        sh, _ = self.sheet(renamed)
        with self.assertRaises(SheetContractError):
            sh.append_rows([{"c1": "NEW", "error": "x"}])

    def test_group_code_columns(self):
        sh, _ = self.sheet(["action", "ezfolio_group_code", "Group code (EZ)", "booking_ref"])
        self.assertEqual(sh.group_code_columns(), ["ezfolio_group_code", "Group code (EZ)"])


if __name__ == "__main__":
    unittest.main()
