"""Telegram notices for drafts waiting on a person: one message per draft, with Accept / Deny / Rewrite / Info
buttons. Sending only — the same bot is Emi's OpenClaw Telegram channel, which receives the button presses
(as "callback_data: emi review <action> <n>") and the replies, and runs `tools.emi review-*`.

Off unless a chat id and a bot token are set. A failed notice never stops a draft: the draft is in Outlook
either way, and `review-list` shows it.

Token, first found: EMI_TELEGRAM_BOT_TOKEN, the file EMI_TELEGRAM_TOKEN_FILE (default secrets/telegram-bot-token),
or channels.telegram.botToken in OpenClaw's own config (~/.openclaw/openclaw.json), so the bot token lives
in one place on the host.

Topics (dev, 2026-11-17: "chia nhóm tele ra làm theo các tab … để dễ xử lý"): the group is a forum and every notice
goes to the tab of its kind (TOPICS). EMI_TELEGRAM_TOPICS=email=12,draft=34,question=56,report=78 holds each tab's
message_thread_id; `python -m tools.emi tg-topics --create` makes the missing tabs and writes that line into .env.
A kind with no tab, or a tab deleted in Telegram, goes to the group's General as before.
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


# kind -> (tab name in the group, its first message saying what goes there)
TOPICS = {
    "email": ("📥 Email tới", "Mỗi email mới vào sales@ một dòng; khi Emi xử lý xong, dòng đó ghi kết quả (row, draft #). "
                             "Dòng còn ⏳ = email chưa xử lý."),
    "draft": ("✉️ Draft chờ duyệt", "Mỗi draft Emi viết: Accept / Deny / Rewrite. Slip đã chuyển kế toán cũng báo ở đây."),
    "question": ("❓ Hỏi đáp", "Câu hỏi cho Karen (E-nnn) và booking build tool không nhập được. "
                              "Trả lời: E-nnn <câu trả lời>."),
    "report": ("📊 Báo cáo", "Kiểm tra cuối ngày, stop sell không chạy được và các cảnh báo khác."),
}
TOPICS_ENV = "EMI_TELEGRAM_TOPICS"


def topics_from_env():
    """EMI_TELEGRAM_TOPICS 'email=12,draft=34' -> {'email': 12, 'draft': 34}. Unknown kinds and bad ids are left out."""
    out = {}
    for part in (os.environ.get(TOPICS_ENV) or "").split(","):
        k, _, v = part.partition("=")
        k, v = k.strip().lower(), v.strip()
        if k in TOPICS and v.isdigit():
            out[k] = int(v)
    return out


def topics_line(topics):
    return ",".join(f"{k}={topics[k]}" for k in TOPICS if k in topics)


class Telegram:
    def __init__(self, chat_id, bot_token, http=httpjson.request, log_dir=None, topics=None):
        self.chat_id = chat_id
        self.bot_token = bot_token
        self.http = http
        self.log_dir = log_dir  # SIM mode: also keep a copy of every notice here
        self.topics = dict(topics or {})  # kind -> message_thread_id

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

    @staticmethod
    def _keyboard(buttons):
        return {"inline_keyboard": [[{"text": t, "callback_data": v} for t, v in row] for row in buttons or []]}

    def _send(self, body, topic):
        """sendMessage into the tab of `topic`; a tab deleted or never made in the group -> General, not lost."""
        thread = self.topics.get(topic) if topic else None
        if thread:
            body["message_thread_id"] = thread
        try:
            return self._call("sendMessage", body)
        except httpjson.HttpError as e:
            if not thread or "thread not found" not in (e.body or "").lower():
                raise
            body.pop("message_thread_id")
            return self._call("sendMessage", body)

    def send(self, text, buttons=None, topic=None):
        """HTML text; buttons = [[(label, callback_value), ...], ...]; topic = a TOPICS kind (its tab), None =
        General. Returns Telegram's message id."""
        body = {"chat_id": self.chat_id, "text": text[:LIMIT], "parse_mode": "HTML",
                "disable_web_page_preview": True}
        if buttons:
            body["reply_markup"] = self._keyboard(buttons)
        return self._send(body, topic).get("message_id")

    def chat_info(self):
        """Telegram's own view of the chat: title, type, is_forum (Topics on)."""
        return self._call("getChat", {"chat_id": self.chat_id})

    def create_topic(self, name):
        """A new tab in the group (the group has Topics on; the bot is an admin allowed to manage topics).
        Returns its message_thread_id."""
        return self._call("createForumTopic", {"chat_id": self.chat_id, "name": name}).get("message_thread_id")

    def edit(self, message_id, text, buttons=None):
        """Replace an earlier notice's text and buttons in place. Unchanged content is not an error."""
        body = {"chat_id": self.chat_id, "message_id": message_id, "text": text[:LIMIT], "parse_mode": "HTML",
                "disable_web_page_preview": True, "reply_markup": self._keyboard(buttons)}
        try:
            self._call("editMessageText", body)
        except httpjson.HttpError as e:
            if "message is not modified" not in e.body:
                raise
        return message_id

    def mark(self, message_id, note, topic=None):
        """Take the buttons off an earlier notice and say what happened to it, under it in its tab."""
        if not message_id:
            return
        self._call("editMessageReplyMarkup", {"chat_id": self.chat_id, "message_id": message_id,
                                               "reply_markup": {"inline_keyboard": []}})
        self._send({"chat_id": self.chat_id, "text": note[:LIMIT], "parse_mode": "HTML",
                    "reply_to_message_id": message_id, "allow_sending_without_reply": True}, topic)


def from_env(sim_dir=None):
    chat = os.environ.get("EMI_TELEGRAM_CHAT_ID")
    if sim_dir:  # SIM run: notices go to files; to Telegram too only when EMI_SIM_TELEGRAM is set
        tok = token() if chat and os.environ.get("EMI_SIM_TELEGRAM") else ""
        return Telegram(chat or "sim", tok, log_dir=os.path.join(sim_dir, "telegram"), topics=topics_from_env())
    if not chat:
        return None
    tok = token()
    return Telegram(chat, tok, topics=topics_from_env()) if tok else None


def esc(text):
    return html.escape(text or "", quote=False)
