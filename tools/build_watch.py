"""Bookings the EZFOLIO build tool stopped on, and rows it hasn't picked up (dev, 2026-11-07).

    python -m tools.emi build-stuck            # list them (read-only)
    python -m tools.precheck confirmations     # also sends the Telegram questions, once per stop (alert below)

06/11: Church Travels BKK 10/1 (rows 1623/1624, error: TPL and QPL full 11-15/01), Footprint 031P0127J (needs_review:
TPL full one night), Amara #30124, Ohmyhotel 28286's cancellation, Pegas 11124455 and Odeon 8649178 (voucher fields
blank). The build tool wrote why it stopped in ez_status / ez_note / ez_error and nobody read it: no PDF came, so job 2
never drafted, and the agencies chased. What to do there (overbook, another room type, decline, fix the group) is not
Emi's call, it is Karen's or Long's. So each stop goes to Karen on Telegram once, as a question E-nnn on the booking's
email; her answer is what Emi then drafts to the agency (karen-answer), or Long fixes it and job 2 confirms the PDF.

21/11 (dev, on E-638, MG AGIN0116572611657606: "với các case mà hết phòng thì từ chối luôn chứ"): a new booking the
build tool could not place because EZFOLIO has no room for it (the type and the type above both 0, nothing free the
whole stay) is no question: Emi declines it at once, CANCEL rows + the decline draft, like Karen's 20/11 rule for
on-request bookings with no availability. Kind 'full'; an open question already asked about it is closed. Room for
only part of it is declined too, the whole booking (dev, same day: "cũng từ chối luôn"). A type free the whole stay or
a change on a built booking still goes to Karen.

25/11 (dev, Booking.com 5349803632, live row 2572): never an OTA or B2B booking. Emi wrote CANCEL "No availability"
for a SynXis booking nobody had cancelled; the guest arrived. An OTA booking stays as the OTA sent it ('stuck', a
question to Karen) and gets a CANCEL row only from the OTA's own cancellation email.

21/11 (dev, on SynXis 92777EE002243 (Agoda), live row 1082, "not picked up for 444 hours"): Agoda 698918623 is two
rooms, one SynXis number each (2243, 2244). Its cancellation came as Agoda's notice (row 1081, ref Agoda 698918623 /
SynXis 2244) and as SynXis's notice for 2243 (row 1082). The build tool cancelled group 28281 from row 1081 and touched
row 1082 a minute before (ez_processed_at 03/11 10:10) without writing a status. Two things here:
- a CANCEL whose booking another CANCEL row already cancelled in EZFOLIO (same company, guest and stay, ez_status
  done) is covered: nothing to wait for (`covered`);
- rows the build tool ran on but left without a status are not "not picked up": kind 'silent', told once, for a
  person to look at in EZFOLIO.
"""
import re
from datetime import datetime, timedelta, timezone

from . import operators, payments

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


# The build tool's own words when EZFOLIO has no room (E-638, 21/11; Church Travels 06/11): "không đủ 2 phòng cho
# 21/12/2026 - 27/12/2026 (DLX-SV còn 0, SUITE-SV còn 0). Trống trọn cả kỳ: không phòng nào. Hết DLX-SV đêm …"
# Only these two say the build tool looked past the booked type: a bare "Hết phòng TPL đêm 13/01" (Footprint
# 031P0127J, 06/11) doesn't, and stays Karen's.
NO_ROOM = re.compile(r"không đủ\s+\d+\s+phòng|Trống trọn cả kỳ:\s*không phòng nào", re.I)
WHOLE_STAY = re.compile(r"Trống trọn cả kỳ:\s*([^.;]*)", re.I)
DECLINE_REASON = "No availability: booking cannot be accommodated"


def no_room(note):
    """True when the build tool says EZFOLIO can't hold the whole booking (dev 21/11: declined at once). Room for only
    part of it ("không đủ 2 phòng (DLX-SV còn 1 …)") is declined too, the whole booking (dev, same day: "cũng từ
    chối luôn"). A type free the whole stay is still Karen's: another room type could take it."""
    note = " ".join((note or "").split())
    if not NO_ROOM.search(note):
        return False
    whole = WHOLE_STAY.search(note)
    return not whole or "không phòng nào" in whole.group(1).lower()


def is_ota(r):
    """An OTA or B2B site's booking (dev, 2026-11-25, Booking.com 5349803632 / SynXis 92777EF003597, live row 2572:
    the build tool found no room on 22/11, Emi wrote a CANCEL row "No availability" on its own; there was no
    cancellation email, SynXis's modification of 21/11 still said Confirmed and the guest landed 25/11 — group 31516
    made by hand. "Emi nhận email OTA như nào thì phải nhập đúng như vậy. Họ có email hủy thì [mới] log cancel
    row"). An OTA booking is never declined by Emi: it is what the OTA sent until the OTA's own cancellation."""
    return (r.get("channel_type") or "").strip().upper() == "OTA" or payments.ota_company(r.get("company"))


def on_cancelled_group(r):
    return r.get("action") == "CHANGE" and _status(r) == "no_change" and bool(CANCELLED_GROUP.search(r.get("ez_note") or ""))


def _same_stay(a, b):
    return all((a.get(k) or "").strip() == (b.get(k) or "").strip() for k in ("arrival", "departure"))


def covered(state, rows):
    """The CANCEL row of the same booking under another number that the build tool has already done (dev 21/11,
    Agoda 698918623: rows 1081 done, group 28281 cancelled; row 1082 the second room's SynXis number). Same company,
    same stay, a guest name in common. None when the state isn't a cancellation or nothing covers it."""
    if not all(r.get("action") == "CANCEL" for r in state):
        return None
    mine = {r["_row"] for r in state}
    head = state[0]
    company, names = payments._plain(head.get("company")).strip(), payments._names(state)
    if not company or not names:
        return None
    return next((r for r in rows if r["_row"] not in mine and r.get("action") == "CANCEL"
                 and _status(r) in payments.BUILT_STATUSES and _same_stay(r, head)
                 and payments._plain(r.get("company")).strip() == company and payments._names([r]) & names), None)


def stuck(rows, state_of, now):
    """One item per booking whose latest email's rows the build tool stopped on ('stuck'), hasn't touched for
    more than WAIT ('waiting'), or ran on and left without a status ('silent'). A later email's rows replace the
    earlier ones (the build tool marks those out_of_scope), so only the latest rows count. Bookings already past
    their arrival, and cancellations another row has already cancelled in EZFOLIO (`covered`), are left out."""
    items = []
    for state in operators.bookings(rows, state_of):
        head = state[0]
        if head.get("action") == "EXISTING BOOKING":
            continue
        arrival = operators._date(head.get("arrival"))
        if arrival and arrival < now.date():
            continue
        if covered(state, rows):
            continue
        bad = [r for r in state if (_status(r) in STUCK or (not _status(r) and (r.get("ez_error") or "").strip())
                                    or on_cancelled_group(r))
               and not any(d in (r.get("ez_note") or "") for d in DECIDED)]
        if bad:
            note = next((x for r in bad for x in ((r.get("ez_error") or "").strip(), (r.get("ez_note") or "").strip())
                         if x), "")
            stamp = max((r.get("ez_processed_at") or "") for r in bad) or head.get("received_at", "")
            # dev 21/11: a new booking with no room in EZFOLIO is declined at once, not asked. Never an OTA's
            # (dev 25/11, R2572): it stays a question, Emi writes no CANCEL row of its own
            kind = ("full" if all(r.get("action") == "NEW" for r in state) and no_room(note) and not is_ota(head)
                    else "stuck")
        elif all(not _status(r) for r in state):
            got = _received(head)
            if not got or got < WATCH_FROM or now - got < WAIT:
                continue
            ran = max((r.get("ez_processed_at") or "").strip() for r in state)
            if ran:  # the build tool ran on it and wrote nothing (row 1082, 03/11 10:10): not "not picked up"
                kind, note, stamp = "silent", f"build tool ran {ran}, wrote no ez_status", ran
            else:
                kind, note, stamp = "waiting", "", head.get("received_at", "")
        else:
            continue
        ref = (head.get("booking_ref") or "").strip()
        items.append({"kind": kind, "ref": ref, "company": head.get("company", ""), "channel": head.get("channel_type", ""),
                      "action": head.get("action", ""), "rows": [r["_row"] for r in state],
                      "received": head.get("received_at", ""), "subject": head.get("source_email", ""),
                      "status": ", ".join(sorted({_status(r) or "blank" for r in state})), "note": " ".join(note.split()),
                      # 'full' once per booking: the build tool retries and rewrites ez_processed_at every ~45 min
                      # (E-638 came back 09:15, 10:00 on 21/11)
                      "key": f"{ref}|full" if kind == "full" else f"{ref}|{kind}|{stamp}", "hours": _hours(head, now)})
    return items


def _hours(head, now):
    got = _received(head)
    return int((now - got).total_seconds() // 3600) if got else None


def render(items):
    out = [f"BUILD STUCK: {sum(i['kind'] == 'stuck' for i in items)} booking(s) the build tool stopped on, "
           f"{sum(i['kind'] == 'full' for i in items)} with no room to decline, "
           f"{sum(i['kind'] == 'waiting' for i in items)} not picked up after {int(WAIT.total_seconds() // 3600)} h, "
           f"{sum(i['kind'] == 'silent' for i in items)} run with no result"]
    for i in items:
        waited = f", email {i['hours']} h ago" if i["hours"] is not None else ""
        out.append(f"{LABEL[i['kind']]} | {i['channel']} | {i['company']} | ref {i['ref']} | "
                   f"{i['action']} rows {', '.join(map(str, i['rows']))} | ez_status {i['status']}{waited} | "
                   f"email: {i['subject']}" + (f" | build tool: {i['note'][:NOTE_CHARS]}" if i["note"] else ""))
    return "\n".join(out)


LABEL = {"stuck": "STUCK", "full": "DECLINE", "waiting": "WAITING", "silent": "NO RESULT"}


def decline_steps(i):
    """What job 2 does for a 'full' item (dev 21/11). Printed under its DECLINE line by build-stuck."""
    return (f"Next: decline now, no question to Karen (dev 21/11: no room = decline). CANCEL rows for ref {i['ref']} "
            f"(status Cancelled, what_changed \"{DECLINE_REASON}\", Cancellation Amount 0, Cancellation Reason "
            f"\"No availability in EZFOLIO, declined <DD/MM>\", internal_notes \"Build tool: no room (rows "
            f"{', '.join(map(str, i['rows']))}); declined at once (dev 21/11)\"), then the decline draft on the "
            f"booking's email (mail-find {i['ref'].split(' / ')[0]}): draft-reply <id> <body> --kind decline --ref "
            f"<ref> (email-templates.md 9b; tour operator: section 6's decline). Then done <id> \"no room, "
            f"declined: CANCEL rows …, decline #n\". Never an OTA or B2B booking (dev 25/11): no CANCEL row "
            f"until the OTA's own cancellation email.")


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
    """What Karen is asked, in plain English (dev, 18/11; USER.md: explainable to her parents)."""
    who = f"{i['company']} {i['ref']}".strip()
    return (f"The EZFOLIO build tool stopped on booking {who} (row {', '.join(map(str, i['rows']))}, email "
            f"{i['received']}): {i['note'][:NOTE_CHARS] or 'no reason given'}. The agency has had no reply yet. What "
            f"do Karen/Long decide (accept the overbooking, change the room type, decline, fix it in EZFOLIO), so Emi "
            f"can draft the reply?")


def alert(st, tg, mail, items, mailbox, out=print):
    """Telegram, once per stop (key = ref + kind + when the build tool wrote it): a stuck booking becomes a question
    E-nnn (st.ask, answered with karen-answer like any other); a booking with no room ('full', dev 21/11) is told as
    declined, no question, and an open one about it is closed; rows not picked up become one line in a notice.
    Nothing is recorded while Telegram is off, so the next run tries again. Returns the items sent."""
    seen = st.data.setdefault("build_alerts", {})
    new = [i for i in items if i["key"] not in seen]
    if not new or tg is None:
        if new:
            out(f"build-stuck: {len(new)} new, Telegram off: not sent")
        return []
    lines = []
    for i in new:
        asked = _open_question(st, i["ref"]) if i["kind"] in ("stuck", "full") else None
        if i["kind"] == "full":
            if asked:  # E-638 (21/11): asked before the rule; no answer is needed now
                st.close_question(asked, "no room in EZFOLIO: declined at once (dev 21/11)")
            qid = None
            lines.append(f"🚫 {_esc(i['company'])} <b>{_esc(i['ref'])}</b> (row {', '.join(map(str, i['rows']))}, "
                         f"email {_esc(i['received'])}): no room in EZFOLIO — "
                         f"{_esc(i['note'][:NOTE_CHARS]) or 'no reason given'}\nEmi declines it: CANCEL rows + the "
                         f"decline draft for review" + (f" ({asked} closed, no answer needed)" if asked else ""))
        elif asked:
            qid = asked
            lines.append(f"↩️ <b>{qid}</b> (asked, no answer yet) · {_esc(i['company'])} <b>{_esc(i['ref'])}</b>: "
                         f"{_esc(i['note'][:NOTE_CHARS]) or 'no reason given'}")
        elif i["kind"] == "stuck":
            qid = st.ask(i["ref"], question(i), _email_for(mail, i, mailbox))
            lines.append(f"❓ <b>{qid}</b> · {_esc(i['company'])} <b>{_esc(i['ref'])}</b> (row "
                         f"{', '.join(map(str, i['rows']))}, email {_esc(i['received'])})\n"
                         f"{_esc(i['note'][:NOTE_CHARS]) or 'no reason given'}")
        elif i["kind"] == "silent":
            qid = None
            lines.append(f"🔍 {_esc(i['company'])} <b>{_esc(i['ref'])}</b> ({i['action']} row "
                         f"{', '.join(map(str, i['rows']))}, email {_esc(i['received'])}): EZFOLIO {_esc(i['note'])}. "
                         f"Someone checks the booking in EZFOLIO and fills ez_status")
        else:
            qid = None
            lines.append(f"⏳ {_esc(i['company'])} <b>{_esc(i['ref'])}</b> (row {', '.join(map(str, i['rows']))}): "
                         f"email {_esc(i['received'])}, not picked up by the EZFOLIO build tool after {i['hours']} hours")
        seen[i["key"]] = {"at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "question": qid}
    head = ("⚠️ <b>Bookings not built in EZFOLIO</b> — the agency has no confirmation yet.\n"
            "Reply <code>E-… &lt;your decision&gt;</code>; Emi drafts the agency's reply from it.\n")
    chunk = head
    for line in lines:
        if len(chunk) + len(line) + 2 > TG_LIMIT:
            tg.send(chunk, topic="question")
            chunk = ""
        chunk += "\n" + line + "\n"
    tg.send(chunk, topic="question")
    out(f"build-stuck: {len(new)} sent to Telegram")
    return new
