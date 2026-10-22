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

    def test_every_draft_gets_a_number_and_a_notice_with_four_buttons(self):
        d = self.reply()
        self.assertIn("draft #1 saved", self.lines[-1])
        msg = self.http.sent()[0]
        self.assertEqual(msg["chat_id"], "42")
        self.assertIn("Draft #1", msg["text"])
        self.assertIn("RE: TEST - Đặt phòng TEST-1512", msg["text"])
        self.assertIn("HAYA đã nhận.", msg["text"])
        values = [b["callback_data"] for row in msg["reply_markup"]["inline_keyboard"] for b in row]
        self.assertEqual(values, ["emi review accept 1", "emi review deny 1", "emi review rewrite 1",
                                  "emi review info 1"])
        self.assertEqual(self.st.data["reviews"]["1"]["draft_id"], d["id"])

    def test_accept_tags_but_never_sends(self):
        d = self.reply()
        review.accept(self.mail, self.st, self.tg, "1", out=self.lines.append)
        self.assertEqual(self.st.data["reviews"]["1"]["status"], "approved")
        self.assertIn("Emi approved", self.mail.get_draft(d["id"])["categories"])
        self.assertIn("bấm Send", self.lines[-1])
        self.assertEqual(len(self.http.sent("editMessageReplyMarkup")), 1)  # buttons removed
        with self.assertRaises(review.ReviewError):  # decided once
            review.deny(self.mail, self.st, self.tg, "1")

    def test_deny_removes_draft_and_frees_the_confirmation(self):
        d = self.reply(CONFIRMATION, kind="confirmation")
        self.assertIn(("TEST-1512", 52), self.st.confirmation_drafted())
        review.deny(self.mail, self.st, self.tg, "#1", reason="sai giá", out=self.lines.append)
        self.assertIsNone(self.mail.get_draft(d["id"]))
        self.assertNotIn(("TEST-1512", 52), self.st.confirmation_drafted())
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
        last = self.http.sent()[-1]["text"]
        self.assertIn("v2", last)
        self.assertIn("thêm dòng tầng cao", last)

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
