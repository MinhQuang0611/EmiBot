"""The Telegram group split into tabs (dev, 2026-11-17): each notice goes to its kind's tab, the email tab gets a line
per email that `done` rewrites with the outcome, and tg-topics makes / records the tabs."""
import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from tools import emi, httpjson, inbox_notices, sim, telegram
from tools.sim_mail import SimMail
from tools.state import State
from tools.telegram import Telegram

TABS = {"email": 11, "draft": 22, "question": 33, "report": 44}


class FakeHttp:
    def __init__(self, fail_thread=False):
        self.calls = []
        self.fail_thread = fail_thread
        self.next_topic = 100
        self.forum = True

    def __call__(self, method, url, headers=None, body=None, **kw):
        name = url.rsplit("/", 1)[-1]
        self.calls.append((name, dict(body or {})))
        if self.fail_thread and name == "sendMessage" and "message_thread_id" in (body or {}):
            raise httpjson.HttpError(400, url, '{"ok":false,"description":"Bad Request: message thread not found"}')
        if name == "getChat":
            return {"ok": True, "result": {"id": 42, "title": "HAYA Emi", "type": "supergroup", "is_forum": self.forum}}
        if name == "createForumTopic":
            self.next_topic += 1
            return {"ok": True, "result": {"message_thread_id": self.next_topic, "name": body["name"]}}
        return {"ok": True, "result": {"message_id": 500 + len(self.calls)}}

    def of(self, method):
        return [b for n, b in self.calls if n == method]


class TopicsTest(unittest.TestCase):
    def setUp(self):
        self._mode = os.environ.pop("EMI_DRAFT_MODE", None)
        self.addCleanup(lambda: os.environ.__setitem__("EMI_DRAFT_MODE", self._mode) if self._mode else None)
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        shutil.copytree(os.path.join(sim.scenario_dir("new-change-cancel"), "inbox"), os.path.join(self.dir, "inbox"))
        self.mail = SimMail(self.dir)
        self.st = State(os.path.join(self.dir, "state.json"))
        self.http = FakeHttp()
        self.tg = Telegram("42", "TOKEN", http=self.http, topics=TABS)
        self.lines = []

    def test_env_line_is_read_and_written_back_in_order(self):
        with mock.patch.dict(os.environ, {"EMI_TELEGRAM_TOPICS": " draft=22, email=11,bogus=5,report=x"}):
            topics = telegram.topics_from_env()
        self.assertEqual(topics, {"draft": 22, "email": 11})
        self.assertEqual(telegram.topics_line(topics), "email=11,draft=22")

    def test_no_tabs_set_means_general_as_before(self):
        Telegram("42", "TOKEN", http=self.http).send("x", topic="draft")
        self.assertNotIn("message_thread_id", self.http.of("sendMessage")[0])

    def test_a_draft_notice_and_its_closing_note_go_to_the_draft_tab(self):
        body = os.path.join(self.dir, "b.txt")
        with open(body, "w", encoding="utf-8") as f:
            f.write("Kính gửi anh/chị Minh,\n\nHAYA đã nhận.\n\nTrân trọng,\nReservations Team")
        args = SimpleNamespace(message_id="sim-01-new-1512", body=body, all=False, kind="reply", ref="", row="")
        emi.draft_reply(self.mail, self.st, args, tg=self.tg, out=self.lines.append)
        emi.review.deny(self.mail, self.st, self.tg, "1", out=self.lines.append)
        sent = self.http.of("sendMessage")
        self.assertEqual([m["message_thread_id"] for m in sent], [22, 22])
        self.assertIn("Draft #1", sent[0]["text"])

    def test_a_question_for_karen_goes_to_the_question_tab(self):
        emi.ask_karen(self.st, self.tg, "sim-01-new-1512", "Giá phòng cho ngày lễ là bao nhiêu?", out=self.lines.append)
        self.assertEqual(self.http.of("sendMessage")[0]["message_thread_id"], 33)

    def test_a_deleted_tab_falls_back_to_general(self):
        tg = Telegram("42", "TOKEN", http=FakeHttp(fail_thread=True), topics=TABS)
        self.assertTrue(tg.send("x", topic="report"))
        sent = tg.http.of("sendMessage")
        self.assertEqual(len(sent), 2)
        self.assertNotIn("message_thread_id", sent[1])

    def test_each_email_gets_one_line_and_done_writes_its_outcome(self):
        work = os.path.join(self.dir, "work")
        msgs = self.mail.list_inbox_since("2000-01-01T00:00:00Z")[:2]
        self.assertEqual(inbox_notices.announce(self.tg, msgs, work, emi.vn), 2)
        self.assertEqual(inbox_notices.announce(self.tg, msgs, work, emi.vn), 0)  # listed again: no second line
        sent = self.http.of("sendMessage")
        self.assertEqual([m["message_thread_id"] for m in sent], [11, 11])
        self.assertIn("⏳", sent[0]["text"])
        self.assertTrue(inbox_notices.settle(self.tg, msgs[0]["id"], "NEW row 52, draft #3", work))
        edit = self.http.of("editMessageText")[0]
        self.assertEqual(edit["message_id"], 501)  # the first line sent, edited in place
        self.assertIn("✅ NEW row 52, draft #3", edit["text"])
        self.assertNotIn("⏳", edit["text"])
        self.assertFalse(inbox_notices.settle(self.tg, "never-listed", "x", work))

    def test_no_email_tab_no_email_lines(self):
        tg = Telegram("42", "TOKEN", http=self.http, topics={"draft": 22})
        msgs = self.mail.list_inbox_since("2000-01-01T00:00:00Z")
        self.assertEqual(inbox_notices.announce(tg, msgs, os.path.join(self.dir, "w"), emi.vn), 0)
        self.assertEqual(self.http.calls, [])

    def test_inbox_new_posts_the_lines(self):
        with mock.patch.object(emi, "WORK_DIR", os.path.join(self.dir, "work")):
            msgs, _ = emi.inbox_new(self.mail, self.st, out=self.lines.append, tg=self.tg)
        self.assertEqual(len(self.http.of("sendMessage")), len(msgs))

    def test_create_makes_the_missing_tabs_and_saves_them(self):
        tg = Telegram("42", "TOKEN", http=self.http, topics={"draft": 22})
        saved = []
        emi.tg_topics(tg, create=True, out=self.lines.append, save_env=saved.append)
        made = [b["name"] for b in self.http.of("createForumTopic")]
        self.assertEqual(made, [telegram.TOPICS[k][0] for k in ("email", "question", "report")])
        self.assertEqual(saved[-1], "email=101,draft=22,question=102,report=103")
        firsts = self.http.of("sendMessage")
        self.assertEqual([m["message_thread_id"] for m in firsts], [101, 102, 103])

    def test_set_records_tabs_made_by_hand(self):
        tg = Telegram("42", "TOKEN", http=self.http)
        saved = []
        emi.tg_topics(tg, assign="email=7,question=9", out=self.lines.append, save_env=saved.append)
        self.assertEqual(saved, ["email=7,question=9"])
        self.assertEqual([n for n, _ in self.http.calls], ["getChat"])
        with self.assertRaises(emi.Refused):
            emi.tg_topics(tg, assign="inbox=7", out=self.lines.append, save_env=saved.append)

    def test_topics_off_is_said_before_anything_is_made(self):
        self.http.forum = False
        with self.assertRaises(emi.Refused) as e:
            emi.tg_topics(Telegram("42", "TOKEN", http=self.http), create=True, out=self.lines.append,
                          save_env=lambda line: None)
        self.assertIn("Topics off", str(e.exception))
        self.assertEqual(self.http.of("createForumTopic"), [])
        self.assertIn("HAYA Emi", self.lines[0])

    def test_a_group_without_topics_gets_the_reason(self):
        def refuse(method, url, body=None, **kw):
            raise httpjson.HttpError(400, url, '{"description":"Bad Request: the chat is not a forum"}')
        with self.assertRaises(emi.Refused) as e:
            emi.tg_topics(Telegram("42", "TOKEN", http=refuse), create=True, out=self.lines.append,
                          save_env=lambda line: None)
        self.assertIn("Manage topics", str(e.exception))


if __name__ == "__main__":
    unittest.main()
