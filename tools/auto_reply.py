"""Auto-replies closed by code, no model (dev, 2026-11-26: Emi's tokens).

An out-of-office or an autoresponder ("Automatic reply: …", a ticket system's "we have received your email") answering
one of our own emails started a whole job 1 run (~300k tokens) only to be marked "NO REPLY: alert". Now the mail
watcher and `job1-start` mark them done themselves, with the same outcome, and put the ✅ line in the 📥 tab.

Only a real auto-reply: its subject says so, or its headers carry `Auto-Submitted: auto-replied` / `X-Autoreply` /
`X-Autorespond` / `Precedence: auto_reply`. `Auto-Submitted: auto-generated` is NOT one: SynXis and the OTAs' robots
send their booking notices with it. A bounce (Undeliverable, mailer-daemon) is not one either: the model still reads
it, since one of our emails didn't arrive.
"""
import calendar
import json
import os
import re
import time

OUTCOME = "NO REPLY: alert — auto-reply, closed by code (no model)"

SUBJECT = re.compile(
    r"^\s*\[?\s*(?:automatic\s+reply|auto(?:matic)?[\s-]*(?:reply|response|answer|antwort)|autoreply|autoresponse|"
    r"out\s+of\s+(?:the\s+)?office|trả\s+lời\s+tự\s+động|tự\s+động\s+trả\s+lời|автоматический\s+ответ|автоответ|"
    r"réponse\s+automatique|respuesta\s+automática|risposta\s+automatica|abwesenheitsnotiz|自动回复|自動回覆|"
    r"自動応答|자동\s*회신|자동\s*응답)(?=\W|$)", re.I)

KEEP = 3 * 24 * 3600  # how long a "not an auto-reply" answer is remembered (the watcher asks every minute)


def by_subject(subject):
    return bool(SUBJECT.search(subject or ""))


def by_headers(headers):
    """headers: {lower-case name: value}."""
    h = {k.lower(): (v or "").strip().lower() for k, v in (headers or {}).items()}
    return (h.get("auto-submitted", "").startswith("auto-replied") or "x-autoreply" in h or "x-autorespond" in h
            or h.get("precedence", "") == "auto_reply")


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def find(mail, msgs, cache_path=None, now=time.time):
    """The auto-replies among msgs. Headers are read once per email (cache_path keeps the answer for KEEP)."""
    cache = _load(cache_path) if cache_path else {}
    found = []
    for m in msgs:
        if by_subject(m.get("subject")):
            found.append(m)
            continue
        if m["id"] not in cache:
            try:
                cache[m["id"]] = {"auto": by_headers(mail.message_headers(m["id"])), "at": now()}
            except Exception:  # headers not readable: the model reads it, as before
                cache[m["id"]] = {"auto": False, "at": now()}
        if cache[m["id"]]["auto"]:
            found.append(m)
    if cache_path:
        cache = {k: v for k, v in cache.items() if now() - v.get("at", 0) < KEEP}
        os.makedirs(os.path.dirname(os.path.abspath(cache_path)), exist_ok=True)
        tmp = cache_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cache, f)
        os.replace(tmp, cache_path)
    return found


def close(st, msgs, tg=None, work_dir="emi-work", vn=lambda s: s, out=print):
    """Mark each one done (the caller holds the state lock and saves) and give it its ✅ line in the 📥 tab."""
    from . import inbox_notices
    for m in msgs:
        st.mark_processed(m["id"], OUTCOME)
        out(f"closed by code: {m.get('subject', '')!r} from "
            f"{((m.get('from') or {}).get('emailAddress') or {}).get('address', '?')} ({OUTCOME})")
    if msgs and tg is not None:
        inbox_notices.announce(tg, msgs, work_dir, vn, out=out)
        for m in msgs:
            inbox_notices.settle(tg, m["id"], OUTCOME, work_dir, out=out)


def received_epoch(m):
    return calendar.timegm(time.strptime(m["receivedDateTime"][:19], "%Y-%m-%dT%H:%M:%S"))
