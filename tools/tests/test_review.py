"""Offline tests for draft review (tools/review.py): Telegram notice, accept, deny, rewrite, info, gone."""
import json
import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace

from tools import emi, review, sim
from tools.graph_mail import GraphMail
from tools.sim_mail import SimMail
from tools.state import State
from tools.telegram import Telegram

CONFIRMATION = ("Kính gửi anh/chị Minh,\n\n**Mã đặt phòng:** TEST-1512\n**Tổng tiền:** 4.200.000 VND, "
                "bao gồm ăn sáng, VAT và phí dịch vụ.\nHạn cọc: 17:00 ngày 17/10/2026 (giờ Việt Nam, UTC+7)\n"
                "CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC — 1020729617\n\nBest,\nHAYA Team")


class FakeHttp:
    def __init__(self):
        self.calls = []

    def __call__(self, method, url, headers=None, body=None, **kw):
        self.calls.append((method, url.rsplit("/", 1)[-1], body))
        return {"ok": True, "result": {"message_id": 100 + len(self.calls)}}

    def sent(self, method="sendMessage"):
        return [b for m, u, b in self.calls if u == method]


class ReviewTest(unittest.TestCase):
    def setUp(self):
        # Outlook mode unless a test says otherwise: the host's .env sets EMI_DRAFT_MODE=telegram.
        self._mode = os.environ.pop("EMI_DRAFT_MODE", None)
        self.addCleanup(lambda: os.environ.__setitem__("EMI_DRAFT_MODE", self._mode) if self._mode else None)
        self.dir = tempfile.mkdtemp()
        shutil.copytree(os.path.join(sim.scenario_dir("new-change-cancel"), "inbox"), os.path.join(self.dir, "inbox"))
        self.mail = SimMail(self.dir)
        self.st = State(os.path.join(self.dir, "state.json"))
        self.http = FakeHttp()
        self.tg = Telegram("42", "TOKEN", http=self.http)
        self.lines = []
        self.body = os.path.join(self.dir, "body.txt")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def write(self, text):
        with open(self.body, "w", encoding="utf-8") as f:
            f.write(text)
        return self.body

    def reply(self, text="Kính gửi anh/chị Minh,\n\nHAYA đã nhận.\n\nBest,\nHAYA Team", kind="reply"):
        args = SimpleNamespace(message_id="sim-01-new-1512", body=self.write(text), all=False, kind=kind,
                               ref="TEST-1512" if kind != "reply" else "", row="52" if kind != "reply" else "")
        return emi.draft_reply(self.mail, self.st, args, tg=self.tg, out=self.lines.append)

    def test_every_draft_gets_a_number_and_a_notice_with_three_buttons(self):
        d = self.reply()
        self.assertIn("draft #1 saved", self.lines[-1])
        msg = self.http.sent()[0]
        self.assertEqual(msg["chat_id"], "42")
        self.assertIn("Draft #1", msg["text"])
        self.assertIn("RE: TEST - Đặt phòng TEST-1512", msg["text"])
        self.assertIn("HAYA đã nhận.", msg["text"])
        values = [b["callback_data"] for row in msg["reply_markup"]["inline_keyboard"] for b in row]
        self.assertEqual(values, ["emi review accept 1", "emi review deny 1", "emi review rewrite 1"])
        labels = [b["text"] for row in msg["reply_markup"]["inline_keyboard"] for b in row]
        self.assertEqual(labels, ["Accept", "Deny", "Rewrite"])
        self.assertEqual(self.st.data["reviews"]["1"]["draft_id"], d["id"])

    def test_notice_shows_the_email_as_outlook_will(self):
        self.reply(CONFIRMATION, kind="confirmation")
        text = self.http.sent()[0]["text"]
        self.assertIn("<b>Mã đặt phòng:</b> TEST-1512", text)
        self.assertNotIn("**", text)
        self.assertNotIn("expandable", text)  # whole email visible, not folded away

    def test_guest_request_has_its_own_label(self):
        self.reply("Dear Guest,\n\nNoted.\n\nBest,\nHAYA Team", kind="request")
        self.assertIn("Draft #1 — Yêu cầu của khách", self.http.sent()[0]["text"])

    def test_accept_tags_but_never_sends(self):
        d = self.reply()
        review.accept(self.mail, self.st, self.tg, "1", out=self.lines.append)
        self.assertEqual(self.st.data["reviews"]["1"]["status"], "approved")
        self.assertIn("Emi approved", self.mail.get_draft(d["id"])["categories"])
        self.assertIn("bấm Send", self.lines[-1])
        self.assertEqual(len(self.http.sent("editMessageReplyMarkup")), 1)  # buttons removed
        with self.assertRaises(review.ReviewError):  # decided once
            review.deny(self.mail, self.st, self.tg, "1")

    def test_deny_removes_draft_and_keeps_the_confirmation_blocked(self):
        d = self.reply(CONFIRMATION, kind="confirmation")
        self.assertIn(("TEST-1512", 52), self.st.confirmation_drafted())
        review.deny(self.mail, self.st, self.tg, "#1", reason="sai giá", out=self.lines.append)
        self.assertIsNone(self.mail.get_draft(d["id"]))
        self.assertIn(("TEST-1512", 52), self.st.confirmation_drafted())  # the hourly run won't propose it again
        self.assertIn("sai giá", self.st.data["reviews"]["1"]["history"][-1]["note"])

    def test_rewrite_replaces_draft_keeps_number_and_attachment(self):
        d = self.reply(CONFIRMATION, kind="confirmation")
        self.mail.add_attachment(d["id"], "TEST-1512.pdf", b"%PDF-1.4 x")
        review.attached(self.st, d["id"], "TEST-1512.pdf")
        new_text = CONFIRMATION.replace("HAYA Team", "HAYA Team\n\nP.S. Phòng tầng cao theo yêu cầu.")
        new = review.rewrite(self.mail, self.st, self.tg, "1", new_text, feedback="thêm dòng tầng cao",
                             check=emi.check_confirmation_text, out=self.lines.append)
        r = self.st.data["reviews"]["1"]
        self.assertEqual((r["draft_id"], r["version"], r["status"]), (new["id"], 2, "pending"))
        self.assertIsNone(self.mail.get_draft(d["id"]))
        self.assertEqual([a["name"] for a in self.mail.list_draft_attachments(new["id"])], ["TEST-1512.pdf"])
        self.assertEqual(self.st.data["confirmations"]["TEST-1512|52"]["draft_id"], new["id"])
        self.assertEqual(len(self.http.sent()), 1)  # no second message: the first one is edited in place
        edit = self.http.sent("editMessageText")[-1]
        self.assertEqual(edit["message_id"], r["tg"])
        self.assertIn("v2", edit["text"])
        self.assertIn("thêm dòng tầng cao", edit["text"])
        self.assertEqual(len(edit["reply_markup"]["inline_keyboard"]), 2)  # buttons still on
        self.assertEqual(self.http.sent("editMessageReplyMarkup"), [])

    def test_rewrite_button_asks_and_remembers_until_saved(self):
        self.reply()
        review.ask(self.mail, self.st, self.tg, "1", out=self.lines.append)
        self.assertIn("muốn chỉnh sửa nội dung nào trong email này (draft #1)", self.lines[-1])
        self.assertEqual(review.awaiting(self.st, out=self.lines.append), "1")
        self.assertEqual(len(self.http.sent("editMessageText")), 1)  # buttons put back on the notice
        review.rewrite(self.mail, self.st, self.tg, "1", "Kính gửi anh/chị Minh,\n\nMới.\n\nBest,\nHAYA Team",
                       feedback="ngắn hơn", out=self.lines.append)
        self.assertIsNone(review.awaiting(self.st, out=self.lines.append))

    def test_rewrite_of_confirmation_still_checked(self):
        self.reply(CONFIRMATION, kind="confirmation")
        with self.assertRaises(emi.Refused):
            review.rewrite(self.mail, self.st, self.tg, "1", "Chào anh, ok.", check=emi.check_confirmation_text)
        self.assertEqual(self.st.data["reviews"]["1"]["version"], 1)

    def test_draft_gone_from_outlook(self):
        d = self.reply()
        self.mail.delete_draft(d["id"])  # a person deleted (or sent) it in Outlook
        review.listing(self.mail, self.st, out=self.lines.append)
        self.assertEqual(self.lines[-1], "no drafts waiting for review")
        self.assertEqual(self.st.data["reviews"]["1"]["status"], "gone")
        with self.assertRaises(review.ReviewError):
            review.accept(self.mail, self.st, self.tg, "1")

    def test_info_shows_source_and_full_text(self):
        self.reply()
        review.info(self.mail, self.st, "1", out=self.lines.append)
        text = "\n".join(self.lines)
        self.assertIn("SOURCE EMAIL", text)
        self.assertIn("TEST-1512", text)
        self.assertIn("HAYA đã nhận.", text)

    def test_telegram_down_never_stops_a_draft(self):
        def broken(*a, **k):
            raise OSError("no network")
        self.tg = Telegram("42", "TOKEN", http=broken)
        d = self.reply()
        self.assertIsNotNone(self.mail.get_draft(d["id"]))
        self.assertIn("no network", self.st.data["reviews"]["1"]["tg_error"])

    def test_no_telegram_configured(self):
        self.tg = None
        self.reply()
        self.assertEqual(self.st.data["reviews"]["1"]["status"], "pending")


class TelegramFirstTest(unittest.TestCase):
    """EMI_DRAFT_MODE=telegram: nothing reaches Outlook until Accept."""
    write = ReviewTest.write
    def setUp(self):
        ReviewTest.setUp(self)
        os.environ["EMI_DRAFT_MODE"] = "telegram"
        self._work = emi.WORK_DIR
        emi.WORK_DIR = self.dir

    def tearDown(self):
        os.environ.pop("EMI_DRAFT_MODE", None)
        emi.WORK_DIR = self._work
        ReviewTest.tearDown(self)

    def outlook_drafts(self):
        return [p for p in os.listdir(os.path.join(self.dir, "drafts"))] if os.path.isdir(
            os.path.join(self.dir, "drafts")) else []

    def test_draft_only_on_telegram_until_accept(self):
        d = ReviewTest.reply(self, CONFIRMATION, kind="confirmation")
        self.assertEqual(d["id"], "pending-1")
        self.assertEqual(self.outlook_drafts(), [])
        r = self.st.data["reviews"]["1"]
        self.assertEqual((r["to"], r["subject"]), (["nguyenminhquang061105@gmail.com"], "RE: TEST - Đặt phòng TEST-1512"))
        self.assertIn("Chưa có trong Outlook", self.http.sent()[0]["text"])
        emi.draft_attach(self.mail, self.st, "pending-1", self.write("PDF bytes"), out=self.lines.append)
        review.rewrite(self.mail, self.st, self.tg, "1", CONFIRMATION + " ", feedback="x",
                       check=emi.check_confirmation_text, out=self.lines.append)
        self.assertEqual(self.outlook_drafts(), [])  # a rewrite stays on Telegram too
        review.accept(self.mail, self.st, self.tg, "1", out=self.lines.append)
        r = self.st.data["reviews"]["1"]
        self.assertFalse(r["draft_id"].startswith("pending-"))
        live = self.mail.get_draft(r["draft_id"])
        self.assertIn("Emi approved", live["categories"])
        self.assertEqual([a["name"] for a in self.mail.list_draft_attachments(r["draft_id"])], ["body.txt"])
        self.assertEqual(self.st.data["confirmations"]["TEST-1512|52"]["draft_id"], r["draft_id"])
        self.assertIn("lưu vào Outlook", self.lines[-1])

    def test_deny_leaves_outlook_untouched(self):
        ReviewTest.reply(self)
        review.deny(self.mail, self.st, self.tg, "1", out=self.lines.append)
        self.assertEqual(self.outlook_drafts(), [])
        self.assertIn("không lưu gì vào Outlook", self.lines[-1])

    def test_no_telegram_falls_back_to_outlook(self):
        self.tg = None
        d = ReviewTest.reply(self)
        self.assertFalse(d["id"].startswith("pending-"))
        self.assertIsNotNone(self.mail.get_draft(d["id"]))


class GraphReviewTest(unittest.TestCase):
    def graph(self, draft):
        calls = []

        def http(method, url, headers=None, body=None, **kw):
            calls.append((method, url))
            return draft if method == "GET" else {}
        return GraphMail("sales@haya-hotels.com", lambda: "t", http=http), calls

    def test_only_emi_drafts_are_touched(self):
        mail, calls = self.graph({"id": "x", "isDraft": True, "categories": []})  # e.g. Sunny's draft
        for f in (mail.approve_draft, mail.delete_draft):
            with self.assertRaises(PermissionError):
                f("x")
        self.assertEqual([m for m, _ in calls], ["GET", "GET"])

    def test_approve_adds_category_delete_uses_delete(self):
        mail, calls = self.graph({"id": "x", "isDraft": True, "categories": ["Emi"]})
        mail.approve_draft("x")
        mail.delete_draft("x")
        self.assertEqual([m for m, _ in calls], ["GET", "PATCH", "GET", "DELETE"])

    def test_sent_message_is_not_a_draft(self):
        mail, _ = self.graph({"id": "x", "isDraft": False, "categories": ["Emi"]})
        self.assertIsNone(mail.get_draft("x"))


if __name__ == "__main__":
    unittest.main()
