"""Offline tests for forward-slip: a payment slip to accounting sent with nobody pressing Send (dev, 2026-11-04).
Everything else stays a draft, and anything unsure leaves a normal draft for a person."""
import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from tools import emi, sim
from tools.graph_mail import ACCOUNTING, GraphMail, SendBlocked
from tools.httpjson import HttpError
from tools.sim_mail import SimMail
from tools.state import State

SOURCE = "sim-01-new-1512"
NOTE = "Mã đoàn: #123\n\nDear chị, em gửi UNC đặt cọc.\n\nTrân trọng,\nReservations team / HAYA Hotel Phu Quoc"


class FakeTelegram:
    def __init__(self):
        self.sent = []

    def send(self, text, buttons=None):
        self.sent.append((text, buttons))
        return len(self.sent)


class ForwardSlipTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        shutil.copytree(os.path.join(sim.scenario_dir("new-change-cancel"), "inbox"), os.path.join(self.dir, "inbox"))
        self.mail = SimMail(self.dir)
        self.st = State(os.path.join(self.dir, "state.json"))
        self.tg = FakeTelegram()
        self.lines = []
        env = mock.patch.dict(os.environ, {"EMI_SEND_SLIPS": "1"})
        env.start()
        self.addCleanup(env.stop)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def slip(self, text=NOTE):
        path = os.path.join(self.dir, "note.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        args = SimpleNamespace(message_id=SOURCE, body=path, kind="forward", ref="TEST-1512", row="52")
        return emi.forward_slip(self.mail, self.st, args, tg=self.tg, out=self.lines.append)

    def test_sent_at_once_to_accounting_with_nothing_to_press(self):
        d = self.slip()
        self.assertTrue(self.mail._meta(d["id"])["sent"])
        self.assertIsNone(self.mail.get_draft(d["id"]))
        r = self.st.data["reviews"]["1"]
        self.assertEqual((r["status"], r["to"]), ("sent", [ACCOUNTING]))
        text, buttons = self.tg.sent[-1]
        self.assertIn("Đã chuyển kế toán", text)
        self.assertIsNone(buttons)
        self.assertEqual(len(self.tg.sent), 1)

    def test_flag_off_leaves_a_normal_draft(self):
        with mock.patch.dict(os.environ, {"EMI_SEND_SLIPS": ""}):
            d = self.slip()
        self.assertIsNotNone(self.mail.get_draft(d["id"]))
        self.assertEqual(self.st.data["reviews"]["1"]["status"], "pending")
        self.assertIsNotNone(self.tg.sent[-1][1])  # Accept / Deny / Rewrite

    def test_second_forward_of_the_same_email_is_refused(self):
        self.slip()
        with self.assertRaises(emi.Refused):
            self.slip()
        self.assertEqual(len(self.st.data["reviews"]), 1)

    def test_a_check_line_is_held_as_a_draft(self):
        d = self.slip("[CHECK BEFORE SENDING: số tiền]\n\n" + NOTE)
        self.assertIsNotNone(self.mail.get_draft(d["id"]))
        self.assertEqual(self.st.data["reviews"]["1"]["status"], "pending")
        self.assertIn("Chưa tự gửi", self.tg.sent[-1][0])
        self.assertIn("CHECK BEFORE SENDING", self.tg.sent[-1][0])
        self.assertNotIn("gửi lỗi", self.tg.sent[-1][0])  # stopped by the check, not by the send failing
        self.assertIsNotNone(self.tg.sent[-1][1])

    def test_a_forward_already_in_sent_items_is_held(self):
        subject = self.mail.get_message_text(SOURCE)["subject"]
        self.mail.sent_by_hand.append({"subject": "Fw: " + subject + " – UNC cọc #123",
                                       "toRecipients": [{"emailAddress": {"address": ACCOUNTING}}]})
        d = self.slip()
        self.assertIsNotNone(self.mail.get_draft(d["id"]))
        self.assertIn("Sent Items", self.lines[-1])

    def test_unreadable_sent_items_is_held(self):
        with mock.patch.object(self.mail, "list_sent_since", side_effect=HttpError(503, "u", "down")):
            d = self.slip()
        self.assertIsNotNone(self.mail.get_draft(d["id"]))
        self.assertEqual(self.st.data["reviews"]["1"]["status"], "pending")

    def test_a_failed_send_leaves_the_draft_and_says_why(self):
        # what a token without Mail.Send gets
        with mock.patch.object(self.mail, "send_slip_forward", side_effect=HttpError(403, "u", "denied")):
            d = self.slip()
        self.assertIsNotNone(self.mail.get_draft(d["id"]))
        self.assertEqual(self.st.data["reviews"]["1"]["status"], "pending")
        self.assertIn("gửi lỗi", self.tg.sent[-1][0])

    def test_state_is_saved_before_the_send(self):
        with mock.patch.object(self.st, "save", wraps=self.st.save) as save:
            with mock.patch.object(self.mail, "send_slip_forward", side_effect=lambda _: save.assert_called()):
                self.slip()

    def test_draft_forward_still_only_drafts(self):
        path = os.path.join(self.dir, "note.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(NOTE)
        args = SimpleNamespace(message_id=SOURCE, to=ACCOUNTING, body=path, kind="forward", ref="", row="")
        d = emi.draft_forward(self.mail, self.st, args, tg=self.tg, out=self.lines.append)
        self.assertIsNotNone(self.mail.get_draft(d["id"]))
        self.assertTrue(any("forward-slip" in x for x in self.lines))

    def test_cli_has_no_way_to_name_another_address(self):
        with self.assertRaises(SystemExit), mock.patch("sys.stderr"):
            emi.parser().parse_args(["forward-slip", SOURCE, "note.txt", "--to", "someone@example.com"])


class GraphSendTest(unittest.TestCase):
    def mail(self, to=(ACCOUNTING,), cc=(), bcc=(), body="note", categories=("Emi",)):
        def rcpt(addrs):
            return [{"emailAddress": {"address": a}} for a in addrs]

        self.posts = []

        def http(method, url, headers=None, body_=None, **kw):
            if method == "POST":
                self.posts.append(url)
                return {}
            if "$select=toRecipients" in url:
                return {"toRecipients": rcpt(to), "ccRecipients": rcpt(cc), "bccRecipients": rcpt(bcc),
                        "body": {"content": body}}
            return {"id": "d1", "isDraft": True, "categories": list(categories)}

        return GraphMail("sales@haya-hotels.com", token=lambda: "t", http=lambda m, u, headers=None, body=None, **k:
                         http(m, u, headers, body))

    def test_posts_send_for_accounting_alone(self):
        self.mail().send_slip_forward("d1")
        self.assertEqual(len(self.posts), 1)
        self.assertTrue(self.posts[0].endswith("/messages/d1/send"))

    def test_refuses_anything_else(self):
        for kw in ({"to": ("guest@example.com",)}, {"to": (ACCOUNTING, "guest@example.com")},
                   {"cc": ("guest@example.com",)}, {"bcc": ("guest@example.com",)},
                   {"body": "<b>[CHECK BEFORE SENDING: x]</b>"}):
            with self.assertRaises(SendBlocked):
                self.mail(**kw).send_slip_forward("d1")
            self.assertEqual(self.posts, [])

    def test_refuses_a_draft_that_is_not_emis(self):
        with self.assertRaises(PermissionError):
            self.mail(categories=()).send_slip_forward("d1")
        self.assertEqual(self.posts, [])

    def test_call_still_blocks_every_send_path(self):
        with self.assertRaises(SendBlocked):
            self.mail()._call("POST", "/messages/d1/send")


if __name__ == "__main__":
    unittest.main()
