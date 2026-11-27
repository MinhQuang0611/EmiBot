"""dev, 2026-11-27 (#2018/#2019 left in Drafts): job 3's model ran `EMI_AUTO_SEND= … draft-reply --kind
balance_reminder`, and the blank variable won over the host's .env. Now the .env alone decides EMI_AUTO_SEND."""
import os
import tempfile
import unittest
from unittest import mock

from tools import config, emi

ON = "deposit_reminder,balance_reminder,ota_note,thanks"


class EnvFileDecidesTest(unittest.TestCase):
    def load(self, env_text, **environ):
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False, encoding="utf-8") as f:
            f.write(env_text)
        self.addCleanup(os.remove, f.name)
        with mock.patch.dict(os.environ, environ, clear=False):
            for k in ("EMI_AUTO_SEND", "EMI_TEST_OTHER"):
                if k not in environ:
                    os.environ.pop(k, None)
            config.load_env(f.name)
            return os.environ.get("EMI_AUTO_SEND"), os.environ.get("EMI_TEST_OTHER"), emi.auto_send_kinds()

    def test_blank_on_the_command_line_does_not_turn_it_off(self):
        value, _, kinds = self.load(f"EMI_AUTO_SEND={ON}\n", EMI_AUTO_SEND="")
        self.assertEqual(value, ON)
        self.assertIn("balance_reminder", kinds)

    def test_a_narrower_list_on_the_command_line_does_not_win_either(self):
        value, _, kinds = self.load(f"EMI_AUTO_SEND={ON}\n", EMI_AUTO_SEND="ota_note")
        self.assertEqual(value, ON)
        self.assertIn("deposit_reminder", kinds)

    def test_blank_in_env_file_is_off(self):
        value, _, kinds = self.load("EMI_AUTO_SEND=\n", EMI_AUTO_SEND=ON)
        self.assertEqual(value, "")
        self.assertEqual(kinds, set())

    def test_not_in_env_file_keeps_the_environment(self):
        value, _, _ = self.load("EMI_MAILBOX=sales@haya-hotels.com\n", EMI_AUTO_SEND="ota_note")
        self.assertEqual(value, "ota_note")

    def test_other_variables_still_lose_to_the_environment(self):
        _, other, _ = self.load("EMI_TEST_OTHER=from-file\n", EMI_TEST_OTHER="from-env")
        self.assertEqual(other, "from-env")
        _, other, _ = self.load("EMI_TEST_OTHER=\n", EMI_TEST_OTHER="from-env")
        self.assertEqual(other, "from-env")


if __name__ == "__main__":
    unittest.main()
