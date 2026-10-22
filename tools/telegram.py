"""Telegram notices for drafts waiting on a person: one message per draft, with Accept / Deny / Rewrite / Info
buttons. Sending only — the same bot is Emi's OpenClaw Telegram channel, which receives the button presses
(as "callback_data: emi review <action> <n>") and the replies, and runs `tools.emi review-*`.

Off unless a chat id and a bot token are set. A failed notice never stops a draft: the draft is in Outlook
either way, and `review-list` shows it.

Token, first found: EMI_TELEGRAM_BOT_TOKEN, the file EMI_TELEGRAM_TOKEN_FILE (default secrets/telegram-bot-token),
or channels.telegram.botToken in OpenClaw's own config (~/.openclaw/openclaw.json), so the bot token lives
in one place on the host.
"""
import html
import json
import os

from . import httpjson

API = "https://api.telegram.org"
LIMIT = 4096
ROOT = os.path.join(os.path.dirname(__file__), "..")


def _openclaw_token():
    path = os.environ.get("OPENCLAW_CONFIG_PATH") or os.path.join(os.path.expanduser("~"), ".openclaw", "openclaw.json")
    try:
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        return ""
    tg = cfg.get("channels", {}).get("telegram", {})
    return tg.get("botToken") or tg.get("accounts", {}).get("default", {}).get("botToken") or ""


def token():
    if os.environ.get("EMI_TELEGRAM_BOT_TOKEN"):
        return os.environ["EMI_TELEGRAM_BOT_TOKEN"]
    path = os.environ.get("EMI_TELEGRAM_TOKEN_FILE") or os.path.join(ROOT, "secrets", "telegram-bot-token")
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    return _openclaw_token()


class Telegram:
    def __init__(self, chat_id, bot_token, http=httpjson.request, log_dir=None):
        self.chat_id = chat_id
        self.bot_token = bot_token
        self.http = http
        self.log_dir = log_dir  # SIM mode: also keep a copy of every notice here

    def _call(self, method, body):
        if self.log_dir:
            os.makedirs(self.log_dir, exist_ok=True)
            n = len(os.listdir(self.log_dir)) + 1
            with open(os.path.join(self.log_dir, f"{n:03d}-{method}.json"), "w", encoding="utf-8") as f:
                json.dump(body, f, ensure_ascii=False, indent=2)
        if not self.bot_token:
            return {"message_id": None}
        resp = self.http("POST", f"{API}/bot{self.bot_token}/{method}", body=body)
        return resp.get("result") or {}

    def send(self, text, buttons=None):
        """HTML text; buttons = [[(label, callback_value), ...], ...]. Returns Telegram's message id."""
        body = {"chat_id": self.chat_id, "text": text[:LIMIT], "parse_mode": "HTML",
                "disable_web_page_preview": True}
        if buttons:
            body["reply_markup"] = {"inline_keyboard": [[{"text": t, "callback_data": v} for t, v in row]
                                                        for row in buttons]}
        return self._call("sendMessage", body).get("message_id")

    def mark(self, message_id, note):
        """Take the buttons off an earlier notice and say what happened to it."""
        if not message_id:
            return
        self._call("editMessageReplyMarkup", {"chat_id": self.chat_id, "message_id": message_id,
                                               "reply_markup": {"inline_keyboard": []}})
        self._call("sendMessage", {"chat_id": self.chat_id, "text": note[:LIMIT], "parse_mode": "HTML",
                                   "reply_to_message_id": message_id, "allow_sending_without_reply": True})


def from_env(sim_dir=None):
    chat = os.environ.get("EMI_TELEGRAM_CHAT_ID")
    if sim_dir:  # SIM run: notices go to files; to Telegram too only when EMI_SIM_TELEGRAM is set
        tok = token() if chat and os.environ.get("EMI_SIM_TELEGRAM") else ""
        return Telegram(chat or "sim", tok, log_dir=os.path.join(sim_dir, "telegram"))
    if not chat:
        return None
    tok = token()
    return Telegram(chat, tok) if tok else None


def esc(text):
    return html.escape(text or "", quote=False)
