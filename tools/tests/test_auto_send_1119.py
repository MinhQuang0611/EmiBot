"""The auto-send list (Karen, 2026-11-19: "Các email được auto send, không cần phải chị Karen duyệt"): payment
reminders, the OTA intake note and the airport pick-up answer are sent by Emi with nobody pressing Send, each kind
only when named in EMI_AUTO_SEND. Anything unsure leaves the normal draft with the reason on Telegram, as for the
slips (test_forward_slip.py). Every other kind still waits for a person."""
import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from tools import emi, sim
from tools.graph_mail import FRONT_OFFICE, GraphMail, SendBlocked, auto_send_refusal
from tools.httpjson import HttpError
from tools.sim_mail import SimMail
from tools.state import State
from tools.tests.test_ota_note_1114 import Mail as NoteMail, Sheet, row
from tools.tests.test_reply_every_email_1113 import NOTICE_3350, SUBJECT, SYNXIS

SOURCE = "sim-01-new-1512"
ALL = "deposit_reminder,balance_reminder,ota_note,pickup"
REMINDER = ("Dear Sir/Madam,\n\nThis is a kind reminder that the deposit of 5,000,000 VND for booking TEST-1512 is due "
            "on 21/11/2026 17:00 (Vietnam time, UTC+7).\n\nCould you please send us the payment slip?\n\n"
            "Best regards,\nReservations Team")
FREE = ("Dear Mr. Lee,\n\nWe are pleased to confirm that we can arrange your complimentary airport pick-up.\n\n"
        "Best regards,\nReservations Team")
PAID = ("Dear Mr. Lee,\n\nPick-up is available as a paid transfer at 200,000 VND one way.\n\n"
        "Best regards,\nReservations Team")


class FakeTelegram:
    def __init__(self):
        self.sent = []

    def send(self, text, buttons=None, topic=None):
        self.sent.append((text, buttons))
        return len(self.sent)


class AutoSendTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        shutil.copytree(os.path.join(sim.scenario_dir("new-change-cancel"), "inbox"), os.path.join(self.dir, "inbox"))
        self.mail = SimMail(self.dir)
        self.st = State(os.path.join(self.dir, "state.json"))
        self.tg = FakeTelegram()
        self.lines = []
        self.env(ALL)

    def env(self, value, mode="outlook"):
        p = mock.patch.dict(os.environ, {"EMI_AUTO_SEND": value, "EMI_DRAFT_MODE": mode})
        p.start()
        self.addCleanup(p.stop)

    def reply(self, kind, text, ref="TEST-1512", row_="52"):
        path = os.path.join(self.dir, "body.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        args = SimpleNamespace(message_id=SOURCE, body=path, kind=kind, ref=ref, row=row_, replaces="",
                               to="", cc="", internal=False, sender_only=False, subject_suffix="")
        return emi.draft_reply(self.mail, self.st, args, tg=self.tg, out=self.lines.append)

    def pickup(self, outcome, ref="TEST-1512"):
        self.st.data.setdefault("pickups", {})[ref] = {"outcome": outcome, "why": "", "at": "2026-11-19T10:00:00"}

    def last(self):
        return self.st.data["reviews"][str(self.st.data["next_review"] - 1)]

    def test_a_deposit_reminder_is_sent_with_nothing_to_press(self):
        d = self.reply("deposit_reminder", REMINDER)
        self.assertTrue(self.mail._meta(d["id"])["sent"])
        self.assertEqual(self.last()["status"], "sent")
        text, buttons = self.tg.sent[-1]
        self.assertIn("Đã gửi nhắc đặt cọc", text)
        self.assertIsNone(buttons)
        self.assertEqual(len(self.tg.sent), 1)
        self.assertTrue(self.st.reminder_drafted("TEST-1512", "deposit"))  # one reminder per deadline still holds

    def test_a_kind_not_named_in_the_flag_stays_a_draft(self):
        self.env("ota_note")
        d = self.reply("deposit_reminder", REMINDER)
        self.assertFalse(self.mail._meta(d["id"]).get("sent"))
        self.assertEqual(self.last()["status"], emi.REVIEW_OPEN)

    def test_kinds_outside_the_list_are_never_sent(self):
        self.env(ALL + ",reply,confirmation,request,decline")
        self.assertEqual(emi.auto_send_kinds(), set(ALL.split(",")))
        d = self.reply("reply", "Dear Sir,\n\nThank you.\n\nBest regards,\nReservations Team")
        self.assertFalse(self.mail._meta(d["id"]).get("sent"))

    def test_a_check_line_holds_it_with_the_reason(self):
        d = self.reply("balance_reminder", "[CHECK BEFORE SENDING: balance figure]\n\n" + REMINDER)
        self.assertFalse(self.mail._meta(d["id"]).get("sent"))
        self.assertEqual(self.last()["status"], emi.REVIEW_OPEN)
        self.assertIn("CHECK BEFORE SENDING", self.tg.sent[-1][0])
        self.assertIsNotNone(self.tg.sent[-1][1])  # Accept / Deny buttons as for any draft

    def test_a_failed_send_leaves_the_draft(self):
        with mock.patch.object(self.mail, "send_auto_draft", side_effect=HttpError(403, "u", "denied")):
            d = self.reply("deposit_reminder", REMINDER)
        self.assertIsNotNone(self.mail.get_draft(d["id"]))
        self.assertEqual(self.last()["status"], emi.REVIEW_OPEN)
        self.assertIn("gửi lỗi", self.tg.sent[-1][0])

    def test_telegram_mode_does_not_hold_an_auto_kind(self):
        self.env(ALL, mode="telegram")
        d = self.reply("deposit_reminder", REMINDER)
        self.assertTrue(self.mail._meta(d["id"])["sent"])

    def test_pickup_needs_its_pickup_run(self):
        with self.assertRaises(emi.Refused):
            self.reply("pickup", FREE)
        with self.assertRaises(emi.Refused):
            self.reply("pickup", FREE, ref="")

    def test_pickup_free_and_paid_are_sent(self):
        self.pickup("FREE")
        d = self.reply("pickup", FREE)
        self.assertTrue(self.mail._meta(d["id"])["sent"])
        self.assertIn("Đã gửi trả lời đón sân bay", self.tg.sent[-1][0])
        self.pickup("PAID", ref="TEST-2")
        d = self.reply("pickup", PAID, ref="TEST-2")
        self.assertTrue(self.mail._meta(d["id"])["sent"])

    def test_pickup_check_or_mismatch_is_held(self):
        for outcome, text, ref in (("CHECK", FREE, "R1"), ("TA", PAID, "R2"), ("FREE", PAID, "R3"),
                                   ("PAID", FREE, "R4")):
            self.pickup(outcome, ref=ref)
            d = self.reply("pickup", text, ref=ref)
            self.assertFalse(self.mail._meta(d["id"]).get("sent"), outcome)
            self.assertEqual(self.last()["status"], emi.REVIEW_OPEN)


class OtaNoteSendTest(unittest.TestCase):
    def setUp(self):
        p = mock.patch.dict(os.environ, {"EMI_DRAFT_MODE": "outlook", "EMI_AUTO_SEND": "ota_note"})
        p.start()
        self.addCleanup(p.stop)
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        self.st = State(os.path.join(tmp, "state.json"))
        self.mail = NoteMail({"m1": (SYNXIS, SUBJECT, NOTICE_3350, "2026-11-10T09:38:00Z")})
        self.sent = []

        def send(did, kind):
            dr = self.mail.drafts[did]
            why = auto_send_refusal(kind, dr["to"] or [], dr["cc"] or [], [], dr["text"])
            if why:
                raise SendBlocked(why)
            self.sent.append(did)
        self.mail.send_auto_draft = send

    def note(self):
        args = SimpleNamespace(message_id="m1", ref="SynXis 92777EF003350 (Trip.com 1653718335673330)", replaces="")
        return emi.ota_note(self.mail, Sheet([row(1937), row(1938)]), self.st, args, out=lambda *_: None)

    def test_the_note_goes_to_front_office_at_once_and_only_once(self):
        d = self.note()
        self.assertEqual(self.sent, [d["id"]])
        self.assertEqual(self.mail.drafts[d["id"]]["to"], [FRONT_OFFICE])
        self.assertEqual(next(iter(self.st.data["reviews"].values()))["status"], "sent")
        with self.assertRaises(emi.Refused):
            self.note()


class RefusalTest(unittest.TestCase):
    def test_what_is_never_sent(self):
        ok = auto_send_refusal("deposit_reminder", ["agency@example.com"], ["boss@example.com"], [], "Dear")
        self.assertEqual(ok, "")
        self.assertEqual(auto_send_refusal("ota_note", [FRONT_OFFICE], [], [], "Kính gửi"), "")
        for args in (("confirmation", ["a@example.com"], [], [], "x"),
                     ("deposit_reminder", [], [], [], "x"),
                     ("deposit_reminder", ["a@example.com"], [], ["b@example.com"], "x"),
                     ("deposit_reminder", ["haya@haya-hotels.com"], [], [], "x"),
                     ("pickup", ["a@example.com"], [], [], "[CHECK BEFORE SENDING: x]\nDear"),
                     ("pickup", ["a@example.com"], [], [], "[DO NOT SEND UNTIL PDF IS ATTACHED]\nDear"),
                     ("ota_note", ["guest@example.com"], [], [], "x"),
                     ("ota_note", [FRONT_OFFICE], ["x@example.com"], [], "x")):
            self.assertNotEqual(auto_send_refusal(*args), "", args)


class GraphAutoSendTest(unittest.TestCase):
    def mail(self, to=("agency@example.com",), body="Dear", categories=("Emi",)):
        self.posts = []

        content = body

        def http(method, url, headers=None, body=None, **kw):
            if method == "POST":
                self.posts.append(url)
                return {}
            if "$select=toRecipients" in url:
                return {"toRecipients": [{"emailAddress": {"address": a}} for a in to], "ccRecipients": [],
                        "bccRecipients": [], "body": {"content": content}}
            return {"id": "d1", "isDraft": True, "categories": list(categories)}
        return GraphMail("sales@haya-hotels.com", token=lambda: "t", http=http)

    def test_posts_send_for_an_auto_kind(self):
        self.mail().send_auto_draft("d1", "balance_reminder")
        self.assertTrue(self.posts[0].endswith("/messages/d1/send"))

    def test_refuses_other_kinds_and_other_drafts(self):
        with self.assertRaises(SendBlocked):
            self.mail().send_auto_draft("d1", "confirmation")
        with self.assertRaises(PermissionError):
            self.mail(categories=()).send_auto_draft("d1", "balance_reminder")
        with self.assertRaises(SendBlocked):
            self.mail(body="<b>[CHECK BEFORE SENDING: x]</b>").send_auto_draft("d1", "pickup")
        self.assertEqual(self.posts, [])


if __name__ == "__main__":
    unittest.main()
