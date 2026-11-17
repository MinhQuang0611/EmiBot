"""The '📥 Email tới' tab (dev, 2026-11-17): one line per email in sales@ the moment inbox-new lists it, and the same
line rewritten with the outcome when `done` marks the email. A line still showing ⏳ is an email nobody has handled.

Only when the group has its email tab (EMI_TELEGRAM_TOPICS email=…): without one, these lines would flood General.
Which email got which line is kept in <work dir>/tg-inbox.json, not in the state file: inbox-new runs without the
state lock. A Telegram failure never stops a scan or a `done`.
"""
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone

from .telegram import esc

FILE = "tg-inbox.json"
KEEP = timedelta(days=10)
OUTCOME_CHARS = 600


def _path(work_dir):
    return os.path.join(work_dir, FILE)


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save(path, data):
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tg-inbox-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def line(m, when, missed=False):
    frm = (m.get("from") or {}).get("emailAddress") or {}
    who = frm.get("name") or ""
    address = frm.get("address") or ""
    sender = f"{esc(who)} &lt;{esc(address)}&gt;" if who and who != address else esc(address or who or "?")
    return (f"📥 <b>{esc(when)}</b> · {sender}\n{esc(m.get('subject') or '(không tiêu đề)')}"
            + (" 📎" if m.get("hasAttachments") else "")
            + ("\n⚠️ sót từ lần quét trước, chưa ai xử lý" if missed else ""))


def on(tg):
    return tg is not None and "email" in (getattr(tg, "topics", None) or {})


def announce(tg, msgs, work_dir, vn, missed_ids=(), out=print):
    """A line in the email tab for each listed email that has none yet. Returns how many went."""
    if not on(tg) or not msgs:
        return 0
    path = _path(work_dir)
    data = _load(path)
    cutoff = (datetime.now(timezone.utc) - KEEP).strftime("%Y-%m-%dT%H:%M:%SZ")
    data = {k: v for k, v in data.items() if v.get("at", "") >= cutoff}
    sent = 0
    try:
        for m in msgs:
            if m["id"] in data:
                continue
            text = line(m, vn(m["receivedDateTime"]), missed=m["id"] in missed_ids)
            mid = tg.send(text + "\n⏳ chờ Emi xử lý", topic="email")
            data[m["id"]] = {"tg": mid, "text": text, "at": _now(), "done": False}
            sent += 1
    except Exception as e:  # the scan goes on; the emails left get their line next run
        out(f"Telegram email tab: {type(e).__name__}: {str(e)[:200]}")
    _save(path, data)
    return sent


def settle(tg, message_id, outcome, work_dir, out=print):
    """`done` on an email: its line shows what was done instead of ⏳."""
    if not on(tg):
        return False
    path = _path(work_dir)
    data = _load(path)
    entry = data.get(message_id)
    if not entry or not entry.get("tg"):
        return False
    outcome = " ".join(outcome.split())
    if len(outcome) > OUTCOME_CHARS:
        outcome = outcome[:OUTCOME_CHARS] + "…"
    try:
        tg.edit(entry["tg"], f"{entry['text']}\n✅ {esc(outcome)}")
    except Exception as e:  # the email is marked done either way
        out(f"Telegram email tab: {type(e).__name__}: {str(e)[:200]}")
        return False
    entry.update(done=True, outcome=outcome, done_at=_now())
    _save(path, data)
    return True
