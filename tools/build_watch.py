"""Bookings the EZFOLIO build tool stopped on, and rows it hasn't picked up (dev, 2026-11-07).

    python -m tools.emi build-stuck            # list them (read-only)
    python -m tools.precheck confirmations     # also sends the Telegram questions, once per stop (alert below)

06/11: Church Travels BKK 10/1 (rows 1623/1624, error: TPL and QPL full 11-15/01), Footprint 031P0127J (needs_review:
TPL full one night), Amara #30124, Ohmyhotel 28286's cancellation, Pegas 11124455 and Odeon 8649178 (voucher fields
blank). The build tool wrote why it stopped in ez_status / ez_note / ez_error and nobody read it: no PDF came, so job 2
never drafted, and the agencies chased. What to do there (overbook, another room type, decline, fix the group) is not
Emi's call, it is Karen's or Long's. So each stop goes to Karen on Telegram once, as a question E-nnn on the booking's
email; her answer is what Emi then drafts to the agency (karen-answer), or Long fixes it and job 2 confirms the PDF.
"""
import re
from datetime import datetime, timedelta, timezone

from . import operators

VN = timezone(timedelta(hours=7))
STUCK = ("needs_review", "error")
WATCH_FROM = datetime(2026, 10, 30, tzinfo=VN)  # Emi on the live sheet: older rows were never the build tool's
DECIDED = ("quản lý đã từ chối",)  # a manager already answered the build tool: nothing to ask
WAIT = timedelta(hours=4)  # schedule.md job 2 step 5: rows waiting on the build tool longer than this go to Karen
NOTE_CHARS = 350
TG_LIMIT = 3800  # under Telegram's 4096 with the header


def _received(r):
    try:
        return datetime.strptime((r.get("received_at") or "").strip(), "%d/%m/%Y %H:%M").replace(tzinfo=VN)
    except ValueError:
        return None


def _status(r):
    return (r.get("ez_status") or "").strip()


# Dev, 2026-11-12, Pegas 11131133 row 1864: a CHANGE on a group the build tool had cancelled gets ez_status no_change,
# "group 31000 đã huỷ (CX) … bản sửa này không còn cần làm". No PDF comes and nobody is told. If the booking is wanted
# again it is a rebuild (NEW rows, sheet-append's "Rebooked after cancellation row N"); that is Karen's call.
CANCELLED_GROUP = re.compile(r"đã hu[ỷỳ]|\(CX\)", re.I)


def on_cancelled_group(r):
    return r.get("action") == "CHANGE" and _status(r) == "no_change" and bool(CANCELLED_GROUP.search(r.get("ez_note") or ""))


def stuck(rows, state_of, now):
    """One item per booking whose latest email's rows the build tool stopped on ('stuck'), or hasn't touched for
    more than WAIT ('waiting'). A later email's rows replace the earlier ones (the build tool marks those
    out_of_scope), so only the latest rows count. Bookings already past their arrival are left out."""
    items = []
    for state in operators.bookings(rows, state_of):
        head = state[0]
        if head.get("action") == "EXISTING BOOKING":
            continue
        arrival = operators._date(head.get("arrival"))
        if arrival and arrival < now.date():
            continue
        bad = [r for r in state if (_status(r) in STUCK or (not _status(r) and (r.get("ez_error") or "").strip())
                                    or on_cancelled_group(r))
               and not any(d in (r.get("ez_note") or "") for d in DECIDED)]
        if bad:
            note = next((x for r in bad for x in ((r.get("ez_error") or "").strip(), (r.get("ez_note") or "").strip())
                         if x), "")
            stamp = max((r.get("ez_processed_at") or "") for r in bad) or head.get("received_at", "")
            kind = "stuck"
        elif all(not _status(r) for r in state):
            got = _received(head)
            if not got or got < WATCH_FROM or now - got < WAIT:
                continue
            kind, note, stamp = "waiting", "", head.get("received_at", "")
        else:
            continue
        ref = (head.get("booking_ref") or "").strip()
        items.append({"kind": kind, "ref": ref, "company": head.get("company", ""), "channel": head.get("channel_type", ""),
                      "action": head.get("action", ""), "rows": [r["_row"] for r in state],
                      "received": head.get("received_at", ""), "subject": head.get("source_email", ""),
                      "status": ", ".join(sorted({_status(r) or "blank" for r in state})), "note": " ".join(note.split()),
                      "key": f"{ref}|{kind}|{stamp}", "hours": _hours(head, now)})
    return items


def _hours(head, now):
    got = _received(head)
    return int((now - got).total_seconds() // 3600) if got else None


def render(items):
    out = [f"BUILD STUCK: {sum(i['kind'] == 'stuck' for i in items)} booking(s) the build tool stopped on, "
           f"{sum(i['kind'] == 'waiting' for i in items)} not picked up after {int(WAIT.total_seconds() // 3600)} h"]
    for i in items:
        waited = f", email {i['hours']} h ago" if i["hours"] is not None else ""
        out.append(f"{'STUCK' if i['kind'] == 'stuck' else 'WAITING'} | {i['channel']} | {i['company']} | ref {i['ref']} | "
                   f"{i['action']} rows {', '.join(map(str, i['rows']))} | ez_status {i['status']}{waited} | "
                   f"email: {i['subject']}" + (f" | build tool: {i['note'][:NOTE_CHARS]}" if i["note"] else ""))
    return "\n".join(out)


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _numbers(ref):
    return {p for p in re.split(r"[\s/,;()]+", ref or "") if sum(c.isdigit() for c in p) >= 4}


def _open_question(st, ref):
    """An open E-nnn already about this booking (Footprint 06/11: E-297 asked from job 1 when the agency chased)."""
    mine = _numbers(ref)
    return next((qid for qid, q in st.open_questions().items() if mine & _numbers(q.get("booking_ref"))), None)


def _email_for(mail, item, mailbox):
    """The newest email about the booking that isn't ours: the one Karen's answer will be drafted on."""
    parts = sorted((p for p in re.split(r"[\s/,;()]+", item["ref"]) if sum(c.isdigit() for c in p) >= 4),
                   key=len, reverse=True)
    for text in parts[:1] + [item["subject"]]:
        if not text:
            continue
        try:
            hits = mail.search(text, top=10)
        except Exception:
            return ""
        for m in hits:
            sender = (m.get("from") or {}).get("emailAddress", {}).get("address", "").lower()
            if sender and sender != mailbox.lower():
                return m["id"]
    return ""


def question(i):
    """What Karen is asked, in plain Vietnamese (USER.md: explainable to her parents)."""
    who = f"{i['company']} {i['ref']}".strip()
    return (f"Hệ thống nhập EZFOLIO dừng ở booking {who} (dòng {', '.join(map(str, i['rows']))}, email {i['received']}): "
            f"{i['note'][:NOTE_CHARS] or 'không ghi lý do'}. Đại lý chưa được trả lời. Karen/Long quyết định thế nào "
            f"(nhận overbook, đổi hạng phòng, từ chối, sửa trên EZFOLIO) để Emi viết draft trả lời?")


def alert(st, tg, mail, items, mailbox, out=print):
    """Telegram, once per stop (key = ref + kind + when the build tool wrote it): a stuck booking becomes a question
    E-nnn (st.ask, answered with karen-answer like any other); rows not picked up become one line in a notice.
    Nothing is recorded while Telegram is off, so the next run tries again. Returns the items sent."""
    seen = st.data.setdefault("build_alerts", {})
    new = [i for i in items if i["key"] not in seen]
    if not new or tg is None:
        if new:
            out(f"build-stuck: {len(new)} new, Telegram off: not sent")
        return []
    lines = []
    for i in new:
        asked = _open_question(st, i["ref"]) if i["kind"] == "stuck" else None
        if asked:
            qid = asked
            lines.append(f"↩️ <b>{qid}</b> (đã hỏi, chưa có trả lời) · {_esc(i['company'])} <b>{_esc(i['ref'])}</b>: "
                         f"{_esc(i['note'][:NOTE_CHARS]) or 'không ghi lý do'}")
        elif i["kind"] == "stuck":
            qid = st.ask(i["ref"], question(i), _email_for(mail, i, mailbox))
            lines.append(f"❓ <b>{qid}</b> · {_esc(i['company'])} <b>{_esc(i['ref'])}</b> (dòng "
                         f"{', '.join(map(str, i['rows']))}, email {_esc(i['received'])})\n"
                         f"{_esc(i['note'][:NOTE_CHARS]) or 'không ghi lý do'}")
        else:
            qid = None
            lines.append(f"⏳ {_esc(i['company'])} <b>{_esc(i['ref'])}</b> (dòng {', '.join(map(str, i['rows']))}): "
                         f"email {_esc(i['received'])}, sau {i['hours']} giờ hệ thống nhập EZFOLIO chưa xử lý")
        seen[i["key"]] = {"at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "question": qid}
    head = ("⚠️ <b>Booking chưa nhập được vào EZFOLIO</b> — đại lý chưa có xác nhận.\n"
            "Trả lời <code>E-… &lt;quyết định&gt;</code>; Emi viết draft trả lời đại lý theo quyết định đó.\n")
    chunk = head
    for line in lines:
        if len(chunk) + len(line) + 2 > TG_LIMIT:
            tg.send(chunk)
            chunk = ""
        chunk += "\n" + line + "\n"
    tg.send(chunk)
    out(f"build-stuck: {len(new)} sent to Telegram")
    return new
