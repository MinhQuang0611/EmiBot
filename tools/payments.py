"""Which TA bookings owe money, which reminder is due, and which built bookings were never confirmed.

Karen, 2026-11-04: "Emi cũng đang không chase payment của khách nữa". The rules were written on 2026-10-08
(skills/confirmation-replies.md) but no command ever ran them, and job 2 was never switched on either.

The deposit clock starts when the confirmation really left sales@, so everything starts from the Sent mail: the first
message from the mailbox that carries the booking's group code. People also confirm from Outlook, so Emi's own draft
records aren't enough, and a code exists only once the booking is built, so no earlier mail can carry it.

Tour operators pay under their contract and OTAs are paid by the OTA: never chased. Direct guests pay 100% before
check-in and have no reminder rule (docs/rate-knowledge/direct.md).
"""
import re
from datetime import date, datetime, time, timedelta, timezone

from . import operators
from .graph_mail import is_internal

VN = timezone(timedelta(hours=7))
DEPOSIT_HOURS = 48
REMIND_AT_HOURS = 40  # the deposit reminder goes 8 hours before the deadline
BALANCE_DAYS = 7      # balance due this many days before check-in; reminder the day before, from 09:00
FIRST_RUN_HOUR, LAST_RUN_HOUR = 7, 21  # the hourly check's window, Vietnam time
CONFIRM_FROM = date(2026, 10, 30)      # Emi's first day on the live sheet: older bookings were confirmed by hand
SEARCH_TOP = 25


def _when(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(VN)


def _group(rows):
    return next((v for r in rows for v in (r.get("ezfolio_group_code"), r.get("Group code")) if (v or "").strip()), "")


def total_of(state):
    return sum(operators._amount(r.get("total_vnd")) for r in state)


def paid_of(hits, state):
    """What has been paid. The columns don't always say it on the latest rows (a CHANGE row with Payment 1 blank but
    Remaining halved, live row 1103), so: the most any one email's rows show as paid, or total − Remaining."""
    by_email = {}
    for r in hits:
        key = (r.get("action"), r.get("received_at"))
        by_email[key] = by_email.get(key, 0) + (operators._amount(r.get("Payment 1"))
                                                + operators._amount(r.get("Payment 2")))
    paid = max(by_email.values(), default=0)
    left = [r.get("Remaining amount") for r in state]
    if left and all(str(x or "").strip() for x in left):
        paid = max(paid, total_of(state) - sum(operators._amount(x) for x in left))
    return min(paid, total_of(state))


BARE_DATE = re.compile(r"^(\d{2}/\d{2}/\d{4})(?: (\d{2}):(\d{2}))?$")
BALANCE_DATE = re.compile(r"balance[^;]*?(\d{2}/\d{2}/\d{4})", re.I)


def fixed_deadline(cod):
    """A COD that is only a date ('06/11/2026', '17/10/2026 14:00'): the agreed deadline, not the 48-hour clock."""
    m = BARE_DATE.match((cod or "").strip())
    if not m:
        return None
    day = operators._date(m.group(1))
    if day is None:
        return None
    clock = time(int(m.group(2)), int(m.group(3))) if m.group(2) else time(23, 59)
    return datetime.combine(day, clock, tzinfo=VN)


def balance_date(cod, arrival):
    m = BALANCE_DATE.search(cod or "")
    return (operators._date(m.group(1)) if m else None) or arrival - timedelta(days=BALANCE_DAYS)


def lookahead(now):
    """After the last run of the day, a 40-hour mark falling overnight is drafted now: by morning it may be too late
    (confirmation-replies.md)."""
    if now.hour >= LAST_RUN_HOUR:
        return datetime.combine(now.date() + timedelta(days=1), time(FIRST_RUN_HOUR), tzinfo=VN) - now
    if now.hour < FIRST_RUN_HOUR:
        return datetime.combine(now.date(), time(FIRST_RUN_HOUR), tzinfo=VN) - now
    return timedelta()


def _addr(m):
    return ((m.get("from") or {}).get("emailAddress") or {}).get("address", "").lower()


def _text(full):
    return (full.get("body") or {}).get("content", "") or ""


def _list(recipients):
    return [r["emailAddress"]["address"] for r in recipients or [] if r.get("emailAddress", {}).get("address")]


def find_confirmation(mail, code, mailbox):
    """{id, sent_at, to, cc, slips} for the first mail sales@ sent with this group code, or None. slips = what the
    agency has sent since with an attachment, which may be a payment the sheet doesn't show yet."""
    hits = [m for m in mail.search(code, top=SEARCH_TOP)]
    when = lambda m: m.get("sentDateTime") or m.get("receivedDateTime") or ""
    ours = sorted((m for m in hits if _addr(m) == mailbox.lower()), key=lambda m: (not m.get("hasAttachments"), when(m)))
    for m in ours:
        full = mail.get_message_bodies(m["id"])
        if code not in _text(full):  # the number can match inside something else
            continue
        sent = _when(when(m))
        slips = [x["id"] for x in hits if x.get("hasAttachments") and not is_internal(_addr(x))
                 and _addr(x) != mailbox.lower() and _when(when(x)) > sent]
        return {"id": m["id"], "sent_at": sent, "to": [a for a in _list(full.get("toRecipients")) if not is_internal(a)],
                "cc": _list(full.get("ccRecipients")), "slips": slips}
    return None


def due(rows, state_of, parts_of, mail, st, mailbox, now):
    """Sorted by arrival. remind: reminders to draft now. slip: looks paid, read it first. no_confirmation: built, but
    no mail with the group code. overdue: deadline passed and its one reminder already went. short_notice: booked
    inside the 7 days, Karen sets the date. paid_unsent: a reminder in Drafts for a booking paid since."""
    out = {"remind": [], "slip": [], "no_confirmation": [], "overdue": [], "short_notice": [], "paid_unsent": []}
    soon = now + lookahead(now)
    for state in operators.bookings(rows, state_of):
        head = state[0]
        ref = (head.get("booking_ref") or "").strip()
        arrival = operators._date(head.get("arrival"))
        if head.get("channel_type") != "TA" or operators.cancelled(state) or not arrival or arrival <= now.date():
            continue
        if (head.get("status") or "").strip() == "Tentative":
            continue
        mine = parts_of(ref)
        hits = [r for r in rows if mine & parts_of(r.get("booking_ref"))]
        code, total = _group(hits), total_of(state)
        if not code or not total or not any((r.get("pdf_link") or "").strip() for r in hits):
            continue  # not built: nobody has been told to pay yet
        paid = paid_of(hits, state)
        item = {"ref": ref, "row": head["_row"], "company": head.get("company", ""), "group": code, "total": total,
                "paid": paid, "arrival": arrival, "cod": head.get("COD", "")}
        if paid >= total:
            _flag_paid(st, mail, item, "deposit", out)
            _flag_paid(st, mail, item, "balance", out)
            continue
        cod = (head.get("COD") or "").strip()
        if cod.lower().startswith(("n/a", "paid in full")):
            continue
        if cod.lower().startswith("full payment"):
            out["short_notice"].append(item)
            continue
        fixed = fixed_deadline(cod)
        half = (total + 1) // 2
        if paid >= half:
            _flag_paid(st, mail, item, "deposit", out)
        balance_day = balance_date(cod, arrival)
        balance_from = datetime.combine(balance_day - timedelta(days=1), time(9), tzinfo=VN)
        if soon >= balance_from:
            which = "balance"
        elif paid < half:
            which = "deposit"
        else:
            continue
        sent = find_confirmation(mail, code, mailbox)
        if sent is None:
            out["no_confirmation"].append(item)
            continue
        if which == "deposit":
            deadline = fixed or sent["sent_at"] + timedelta(hours=DEPOSIT_HOURS)
            if soon < deadline - timedelta(hours=DEPOSIT_HOURS - REMIND_AT_HOURS):
                continue
            passed = now > deadline
            words = f"{deadline:%H:%M} on {deadline:%d/%m/%Y}, Vietnam time (UTC+7)"
            amount = half - paid
        else:
            passed = now.date() > balance_day
            words = f"before {balance_day:%d/%m/%Y}"
            amount = total - paid
        item.update(which=which, amount=amount, deadline=words, passed=passed, sent=sent)
        if st.reminder_drafted(ref, which):
            if passed:
                out["overdue"].append(item)
            continue
        out["slip" if sent["slips"] else "remind"].append(item)
    for bucket in out.values():
        bucket.sort(key=lambda i: i["arrival"])
    return out


def _flag_paid(st, mail, item, which, out):
    """confirmation-replies.md: a slip has arrived and the reminder is still unsent → flag it for deletion."""
    entry = st.data["reminders"].get(f"{item['ref']}|{which}")
    if not entry or str(entry["draft_id"]).startswith("pending-") or mail.get_draft(entry["draft_id"]) is None:
        return
    out["paid_unsent"].append(dict(item, which=which, review=st.review_by_draft(entry["draft_id"])))


def needs_confirmation(rows, state_of, parts_of, mail, st, mailbox, today):
    """Bookings built since Emi went live that sales@ never confirmed. One line per booking, on its NEW row. An OTA
    confirms to the guest itself; a change's confirmation is still read from the row by hand."""
    done = {ref for ref, _ in st.confirmation_drafted()}
    out = []
    for state in operators.bookings(rows, state_of):
        head = state[0]
        ref = (head.get("booking_ref") or "").strip()
        channel = head.get("channel_type") or ""
        arrival = operators._date(head.get("arrival"))
        if not (channel in ("TA", "Direct") or channel.startswith("Tour operator")) or operators.cancelled(state):
            continue
        if not arrival or arrival < today or not total_of(state) or ref in done:
            continue
        mine = parts_of(ref)
        hits = [r for r in rows if mine & parts_of(r.get("booking_ref"))]
        new = next((r for r in hits if r.get("action") == "NEW" and (r.get("pdf_link") or "").strip()), None)
        if new is None:
            continue
        received = operators._date((new.get("received_at") or "").split(" ")[0])
        code = _group(hits)
        if not code or not received or received < CONFIRM_FROM:
            continue
        if find_confirmation(mail, code, mailbox) is None:
            out.append({"ref": ref, "row": new["_row"], "company": head.get("company", ""), "group": code,
                        "arrival": arrival, "subject": new.get("source_email", ""), "channel": channel})
    return sorted(out, key=lambda i: i["arrival"])


def money(n):
    return f"{n:,.0f}"


def _safe(ref):
    return re.sub(r"[^A-Za-z0-9_-]+", "-", ref).strip("-")[:40]


def render(result, now):
    r = result
    out = [f"PAYMENTS {now:%d/%m/%Y %H:%M}: {len(r['remind'])} reminder(s) to draft, {len(r['slip'])} to read first, "
           f"{len(r['overdue'])} overdue after their reminder"]
    for label, bucket in (("REMIND", r["remind"]), ("READ FIRST", r["slip"])):
        for i in bucket:
            s = i["sent"]
            late = " LATE: deadline already passed, the reminder never went" if i["passed"] else ""
            kind = f"{i['which']}_reminder"
            out.append(f"{label} {i['which']} | {i['company']} | ref {i['ref']} | row {i['row']} | group #{i['group']} | "
                       f"total {money(i['total'])} | paid {money(i['paid'])} | amount due {money(i['amount'])} | "
                       f"deadline {i['deadline']} | confirmation sent {s['sent_at']:%d/%m/%Y %H:%M}{late}")
            if label == "READ FIRST":
                out.append(f"  mail with an attachment since the confirmation, may be the payment: show "
                           f"{' , show '.join(s['slips'])}. A slip → the usual CHANGE row + forward-slip, no reminder. "
                           f"Not a slip → the reminder below")
            cc = f" --cc {','.join(s['cc'])}" if s["cc"] else ""
            out.append(f"  draft-reply {s['id']} emi-work/out/{_safe(i['ref'])}-{i['which']}.txt --to "
                       f"{','.join(s['to'])}{cc} --kind {kind} --ref \"{i['ref']}\" --row {i['row']} --subject-suffix "
                       f"\"- PAYMENT REMINDER #{i['group']}\" (Vietnamese thread: \"- NHẮC THANH TOÁN #{i['group']}\")")
    for i in r["overdue"]:
        out.append(f"OVERDUE {i['which']} | {i['company']} | ref {i['ref']} | row {i['row']} | group #{i['group']} | "
                   f"amount due {money(i['amount'])} | deadline {i['deadline']}: reminder already drafted. Report to "
                   f"Karen; nothing cancelled, no second reminder")
    for i in r["short_notice"]:
        out.append(f"SHORT NOTICE | {i['company']} | ref {i['ref']} | row {i['row']} | group #{i['group']} | "
                   f"unpaid {money(i['total'] - i['paid'])} | arrival {i['arrival']:%d/%m/%Y}: booked inside 7 days, "
                   f"Karen sets the deadline. Report line")
    for i in r["no_confirmation"]:
        out.append(f"NO CONFIRMATION FOUND | {i['company']} | ref {i['ref']} | row {i['row']} | group #{i['group']}: "
                   f"built, unpaid, and no mail from sales@ has the group code, so the deposit clock hasn't started")
    for i in r["paid_unsent"]:
        out.append(f"PAID, REMINDER STILL IN DRAFTS | ref {i['ref']} | {i['which']} | draft #{i['review']}: report "
                   f"line 'deny #{i['review']}', so it isn't sent by mistake")
    return "\n".join(out)


def render_confirmations(items):
    out = [f"CONFIRMATIONS DUE: {len(items)} booking(s) built and never confirmed from sales@"]
    for i in items:
        out.append(f"CONFIRM | {i['channel']} | {i['company']} | ref {i['ref']} | row {i['row']} | group #{i['group']} | "
                   f"arrival {i['arrival']:%d/%m/%Y} | original email: {i['subject']}")
    return "\n".join(out)
