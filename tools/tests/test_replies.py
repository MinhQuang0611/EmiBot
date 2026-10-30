"""Offline tests for who a reply goes to (tools/emi.py draft-reply / draft-confirmation --to, --cc, the internal-
sender guard) and the test/sim/forwarded-request scenario.

Live run 2026-10-22: front office (haya@haya-hotels.com) forwarded a RezLive request and a guest's email into
sales@; Emi's replies went to haya@, and a 'forward to front office' went back to haya@ too."""
import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from tools import config, emi, review, sim
from tools.graph_mail import is_internal, reply_subject
from tools.sim_mail import SimMail
from tools.state import State
from tools.telegram import Telegram
from tools.tests.test_review import FakeHttp as TelegramHttp
from tools.tests.test_tools import mail_with

SOURCE = "sim-01-fw-rezlive"
GUEST = "ssr@rezlive.example"
FRONT = "haya@haya-hotels.com"
GOOD = ("Dear Reconfirmation Team,\n\nThank you for your email. We have noted the king-size bed request for "
        "Mr. TEST JOHN SIMGUEST and Ms. TEST ANNA SIMGUEST, 08/11/2026 – 11/11/2026. The Deluxe Double has one "
        "1.8 m bed; we will do our best to arrange it, subject to availability at check-in.\n\nTrân trọng,\nReservations Team")


class NoRows:
    def find_by_ref(self, ref):
        return []


def args(body, **kw):
    a = dict(message_id=SOURCE, body=body, all=False, kind="request", ref="TEST-AGIN0116572610466700", row="",
             to="", cc="", internal=False)
    a.update(kw)
    return SimpleNamespace(**a)


class Base(unittest.TestCase):
    def setUp(self):
        self._mode = os.environ.pop("EMI_DRAFT_MODE", None)  # the host .env sets telegram; tests choose
        self.addCleanup(lambda: os.environ.__setitem__("EMI_DRAFT_MODE", self._mode) if self._mode else None)
        self.work = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.work, True)
        self.dir = sim.run_dir(self.work, "forwarded-request")
        shutil.copytree(os.path.join(sim.scenario_dir("forwarded-request"), "inbox"), os.path.join(self.dir, "inbox"))
        self.mail = SimMail(self.dir)
        self.st = State(os.path.join(self.dir, "state.json"))
        for target, name, value in ((emi, "WORK_DIR", self.dir), (config, "SIM_DIR", None)):
            p = mock.patch.object(target, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.http = TelegramHttp()
        self.tg = None
        self.lines = []

    def body(self, text=GOOD, name="body.txt"):
        path = os.path.join(self.work, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def reply(self, **kw):
        return emi.draft_reply(self.mail, self.st, args(self.body(), **kw), tg=self.tg, out=self.lines.append)

    def grade(self):
        self.st.save()
        lines = []
        ok = sim.check(NoRows(), "forwarded-request", self.work, out=lines.append)
        return ok, "\n".join(lines)


class HelpersTest(unittest.TestCase):
    def test_internal_addresses(self):
        for a in ("haya@haya-hotels.com", "Sales@HAYA-hotels.com", "accountant@palmahotel.vn", "x@mail.palmahotel.vn"):
            self.assertTrue(is_internal(a), a)
        for a in ("ssr@rezlive.com", "apkamath@yahoo.in", "x@guest.trip.com", "notpalmahotel.vn@gmail.com", ""):
            self.assertFalse(is_internal(a), a)

    def test_reply_subject_drops_forward_marks(self):
        self.assertEqual(reply_subject("Fw: REZ6AD9A3A2: Hotel Booking Special Service Request"),
                         "RE: REZ6AD9A3A2: Hotel Booking Special Service Request")
        self.assertEqual(reply_subject("RE: Fw: RE: SI781659A - HAYA HOTEL PHU QUOC"), "RE: SI781659A - HAYA HOTEL PHU QUOC")
        self.assertEqual(reply_subject("TR: Chuyển tiếp: Đặt phòng"), "RE: Đặt phòng")
        self.assertEqual(reply_subject("  Tin nhắn từ Robert Pupp,  khách của Hotels.com "),
                         "RE: Tin nhắn từ Robert Pupp, khách của Hotels.com")


class RecipientGuardTest(Base):
    def test_reply_to_a_mail_forwarded_in_by_front_office_is_refused(self):
        with self.assertRaises(emi.Refused) as e:
            self.reply()
        self.assertIn(FRONT, str(e.exception))
        self.assertIn("--to", str(e.exception))
        self.assertFalse(os.path.isdir(os.path.join(self.dir, "drafts")))  # nothing written

    def test_reply_with_to_goes_to_the_original_sender(self):
        d = self.reply(to=GUEST, cc=FRONT)
        meta = self.mail._meta(d["id"])
        self.assertEqual((meta["to"], meta["cc"]), ([GUEST], [FRONT]))
        self.assertEqual(meta["subject"], "RE: TEST-REZ6AD9A3A2: Hotel Booking Special Service Request")
        r = self.st.data["reviews"]["1"]
        self.assertEqual((r["to"], r["cc"], r["to_override"]), ([GUEST], [FRONT], True))
        self.assertIn(f"(to {GUEST}, cc {FRONT})", self.lines[-1])

    def test_to_must_be_the_guest_not_our_staff(self):
        with self.assertRaises(emi.Refused) as e:
            self.reply(to=FRONT)
        self.assertIn("our own address", str(e.exception))

    def test_cc_alone_and_to_with_all_are_refused(self):
        with self.assertRaises(emi.Refused):
            self.reply(cc=FRONT)
        with self.assertRaises(emi.Refused):
            self.reply(to=GUEST, all=True)

    def test_internal_only_for_a_plain_reply_to_a_colleague(self):
        with self.assertRaises(emi.Refused):
            self.reply(internal=True)  # kind request: always a guest or agency
        d = self.reply(internal=True, kind="reply", ref="")
        self.assertEqual(self.mail._meta(d["id"])["to"], [FRONT])

    def test_forward_back_to_the_colleague_who_forwarded_it_is_refused(self):
        a = SimpleNamespace(message_id=SOURCE, to=FRONT, body=self.body("**Booking:** x"), kind="forward", ref="",
                            row="")
        with self.assertRaises(emi.Refused) as e:
            emi.draft_forward(self.mail, self.st, a, out=self.lines.append)
        self.assertIn("Don't forward it back", str(e.exception))
        a.to = "accountant@palmahotel.vn"  # another department is fine
        emi.draft_forward(self.mail, self.st, a, out=self.lines.append)

    def test_external_sender_unchanged(self):
        shutil.copytree(os.path.join(sim.scenario_dir("operational-request"), "inbox"),
                        os.path.join(self.dir, "inbox"), dirs_exist_ok=True)
        self.mail = SimMail(self.dir)
        d = emi.draft_reply(self.mail, self.st, args(self.body(), message_id="sim-01-request"), out=self.lines.append)
        meta = self.mail._meta(d["id"])
        self.assertEqual((meta["to"], meta["subject"]), (["sim-guest-kr@example.com"], "RE: Hello"))


class TelegramModeTest(Base):
    def setUp(self):
        super().setUp()
        os.environ["EMI_DRAFT_MODE"] = "telegram"
        self.addCleanup(os.environ.pop, "EMI_DRAFT_MODE", None)
        self.tg = Telegram("42", "TOKEN", http=self.http)

    def test_override_shown_on_telegram_and_applied_on_accept(self):
        d = self.reply(to=GUEST, cc=FRONT)
        self.assertEqual(d["id"], "pending-1")
        r = self.st.data["reviews"]["1"]
        self.assertEqual((r["to"], r["cc"]), ([GUEST], [FRONT]))
        self.assertEqual(r["subject"], "RE: TEST-REZ6AD9A3A2: Hotel Booking Special Service Request")
        notice = self.http.sent()[0]["text"]
        self.assertIn(f"<b>Gửi:</b> {GUEST}", notice)
        self.assertIn(f"<b>Cc:</b> {FRONT}", notice)
        self.assertNotIn("Fw:", notice)
        review.rewrite(self.mail, self.st, self.tg, "1", GOOD.replace("Thank you", "Many thanks"), feedback="x",
                       out=self.lines.append)
        review.accept(self.mail, self.st, self.tg, "1", out=self.lines.append)
        meta = self.mail._meta(self.st.data["reviews"]["1"]["draft_id"])
        self.assertEqual((meta["to"], meta["cc"]), ([GUEST], [FRONT]))
        self.assertEqual(meta["subject"], "RE: TEST-REZ6AD9A3A2: Hotel Booking Special Service Request")
        self.assertIn("Many thanks", meta["text"])

    def test_refused_before_anything_reaches_telegram(self):
        with self.assertRaises(emi.Refused):
            self.reply()
        self.assertEqual(self.http.sent(), [])


class OutlookRewriteTest(Base):
    def test_rewrite_keeps_the_overridden_recipients(self):
        self.reply(to=GUEST, cc=FRONT)
        new = review.rewrite(self.mail, self.st, None, "1", GOOD + "\n", feedback="x", out=self.lines.append)
        meta = self.mail._meta(new["id"])
        self.assertEqual((meta["to"], meta["cc"]), ([GUEST], [FRONT]))


class GraphRecipientsTest(unittest.TestCase):
    def test_graph_reply_patches_recipients_and_subject(self):
        mail, http = mail_with([
            ("GET", "/messages/m1", {"from": {"emailAddress": {"address": FRONT}}, "subject": "Fw: X"}),
            ("POST", "/createReply", {"id": "d1", "subject": "RE: Fw: REZ6AD9A3A2: Special Request"}),
            ("GET", "/messages/d1?$select=body", {"body": {"content": "<html><body></body></html>"}})])
        mail.reply_draft_with_text("m1", "Dear Team,\n\nNoted.\n\nTrân trọng,\nReservations Team", to=[GUEST], cc=[FRONT])
        patch = next(b for m, u, b in http.calls if m == "PATCH" and b and "toRecipients" in b)
        self.assertEqual(patch["toRecipients"], [{"emailAddress": {"address": GUEST}}])
        self.assertEqual(patch["ccRecipients"], [{"emailAddress": {"address": FRONT}}])
        self.assertEqual(patch["subject"], "RE: REZ6AD9A3A2: Special Request")
        self.assertFalse(any(u.endswith(("/send", "/reply")) for m, u, b in http.calls))

    def test_graph_draft_reply_refuses_internal_sender(self):
        mail, http = mail_with([("GET", "/messages/m1", {"from": {"emailAddress": {"address": FRONT}}})])
        with tempfile.TemporaryDirectory() as d:
            body = os.path.join(d, "b.txt")
            with open(body, "w", encoding="utf-8") as f:
                f.write("Dear Team,\n\nTrân trọng,\nReservations Team")
            with self.assertRaises(emi.Refused):
                emi.draft_reply(mail, State(os.devnull + "-none"),
                                SimpleNamespace(message_id="m1", body=body, all=False, kind="reply", ref="", row=""),
                                out=lambda *_: None)
        self.assertFalse(any(m == "POST" for m, u, b in http.calls))

    def test_cli_has_the_options(self):
        a = emi.parser().parse_args(["draft-reply", "m1", "b.txt", "--to", GUEST, "--cc", FRONT, "--kind", "request"])
        self.assertEqual((a.to, a.cc, a.internal), (GUEST, FRONT, False))
        a = emi.parser().parse_args(["draft-confirmation", "m1", "5", "b.txt", "--to", GUEST])
        self.assertEqual((a.to, a.cc), (GUEST, ""))


class ConfirmationRecipientsTest(unittest.TestCase):
    """draft-confirmation on a booking request front office forwarded in: --to the agency, never haya@."""

    def setUp(self):
        from tools.tests.test_emi import ConfirmationPdfTest, chip
        self.helper = ConfirmationPdfTest("test_file_id_from_drive_links")
        self.helper.setUp()
        self.addCleanup(self.helper.tearDown)
        self.sheet = self.helper.sheet(chip(ConfirmationPdfTest.URL))
        p = mock.patch.object(emi, "WORK_DIR", self.helper.dir.name)
        p.start()
        self.addCleanup(p.stop)
        self._mode = os.environ.pop("EMI_DRAFT_MODE", None)
        self.addCleanup(lambda: os.environ.__setitem__("EMI_DRAFT_MODE", self._mode) if self._mode else None)

    def mail(self):
        return mail_with([
            ("GET", "/messages/m1", {"from": {"emailAddress": {"address": FRONT}}, "subject": "Fw: SI781659A"}),
            ("POST", "/createReply", {"id": "d1", "subject": "RE: Fw: RE: SI781659A"}),
            ("GET", "/messages/d1?$select=body", {"body": {"content": "<html><body></body></html>"}})])

    def test_refused_without_to_and_addressed_with_it(self):
        mail, http = self.mail()
        st = State(os.path.join(self.helper.dir.name, "s.json"))
        a = SimpleNamespace(message_id="m1", row=3, body=self.helper.body, all=False, to="", cc="")
        with self.assertRaises(emi.Refused):
            emi.draft_confirmation(mail, self.sheet, st, a, out=lambda *_: None)
        self.assertFalse(any(m == "POST" for m, u, b in http.calls))
        a.to, a.cc = "resa2@vietbanmai.example", FRONT
        emi.draft_confirmation(mail, self.sheet, st, a, out=lambda *_: None)
        patch = next(b for m, u, b in http.calls if m == "PATCH" and b and "toRecipients" in b)
        self.assertEqual(patch["toRecipients"], [{"emailAddress": {"address": "resa2@vietbanmai.example"}}])
        self.assertEqual(patch["subject"], "RE: SI781659A")
        self.assertTrue(any(u.endswith("/messages/d1/attachments") for m, u, b in http.calls))


class ForwardedRequestScenarioTest(Base):
    def test_scenario_email_is_a_forward_from_front_office(self):
        m = self.mail.get_message_text(SOURCE)
        self.assertEqual(m["from"]["emailAddress"]["address"], FRONT)
        self.assertIn(f"<{GUEST}>", m["body"]["content"])

    def test_reply_to_the_original_sender_passes(self):
        self.reply(to=GUEST, cc=FRONT)
        ok, report = self.grade()
        self.assertTrue(ok, report)
        for line in (f"PASS a reply to {GUEST}", "PASS no reply to @haya-hotels.com",
                     f"PASS no forward to {FRONT}", "PASS drafts of kind 'request': 1"):
            self.assertIn(line, report)
        self.assertIn(f"cc {FRONT}", report)

    def test_live_run_of_2026_10_22_fails(self):
        # What happened before the guard: reply straight to the forwarder, and a forward back to it.
        self.mail.reply_draft_with_text(SOURCE, "Dear Reconfirmation Team,\n\nThank you for your email about the "
                                                "stay from 08/11/2026 to 11/11/2026.\n\nBest,")
        self.mail.forward_draft_with_text(SOURCE, [FRONT], "**Booking:** TEST-AGIN0116572610466700")
        ok, report = self.grade()
        self.assertFalse(ok)
        for line in (f"FAIL a reply to {GUEST}: none", "FAIL no reply to @haya-hotels.com",
                     f"FAIL no forward to {FRONT}", "FAIL no draft says 'Thank you for your email about'"):
            self.assertIn(line, report)


if __name__ == "__main__":
    unittest.main()
