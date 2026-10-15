"""Offline tests for the simulated mailbox (tools/sim_mail.py) on the real scenario files."""
import json
import os
import shutil
import tempfile
import unittest

from tools import sim
from tools.sim_mail import SimMail


class SimMailTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        shutil.copytree(os.path.join(sim.scenario_dir("new-change-cancel"), "inbox"), os.path.join(self.dir, "inbox"))
        self.mail = SimMail(self.dir)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_inbox_threads_and_search(self):
        ids = [m["id"] for m in self.mail.list_inbox_since("2030-01-01T00:00:00Z")]
        self.assertEqual(ids, ["sim-01-new-1512", "sim-02-change-1511", "sim-03-cancel-1512"])
        cancel = self.mail.get_message_text("sim-03-cancel-1512")
        thread = self.mail.get_thread(cancel["conversationId"], text=True)
        self.assertEqual([m["id"] for m in thread], ["sim-01-new-1512", "sim-03-cancel-1512"])
        self.assertEqual(cancel["receivedDateTime"], "2026-10-15T08:00:00Z")
        self.assertEqual([m["id"] for m in self.mail.search("TEST-1511")], ["sim-02-change-1511"])

    def test_drafts_go_to_files_not_graph(self):
        d = self.mail.reply_draft_with_text("sim-03-cancel-1512", "Kính gửi anh/chị Minh,\n\nBest,\nHAYA Team")
        self.mail.add_attachment(d["id"], "conf.pdf", b"%PDF")
        with open(os.path.join(self.dir, "drafts", d["id"] + ".json"), encoding="utf-8") as f:
            meta = json.load(f)
        self.assertEqual(meta["subject"], "RE: TEST - Đặt phòng TEST-1512")
        self.assertEqual(meta["to"], ["nguyenminhquang061105@gmail.com"])
        self.assertEqual(meta["attachments"][0]["name"], "conf.pdf")
        self.assertFalse(hasattr(self.mail, "_call"))  # no route to Graph at all

    def test_amounts_match_whatever_the_separator(self):
        for written in ("2,100,000 VND", "2.100.000 VND", "2100000"):
            self.assertIn(sim._digits("2.100.000"), sim._digits(written))
        self.assertNotIn(sim._digits("2.100.000"), sim._digits("2,500,000"))


if __name__ == "__main__":
    unittest.main()
