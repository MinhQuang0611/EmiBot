"""The commands Emi's scheduled jobs call. One fixed command per step, so the agent never has
to write its own Python to reach the mailbox or the sheet (schedule.md says which job uses which).

    python -m tools.emi inbox-new                         # emails since the last scan, not yet handled
    python -m tools.emi show <message_id>                 # whole thread + attachments saved and read
    python -m tools.emi mail-find <text>                  # emails matching text (ref, subject, sender): their ids
    python -m tools.emi done <message_id> <outcome>       # mark one email handled
    python -m tools.emi mark-scanned <scan_started>       # end of job 1: move the scan clock
    python -m tools.emi sheet-schema                      # every column: level, required, allowed values, sheet instruction
    python -m tools.emi sheet-access                      # the sheet Emi writes to, and whether it has edit access
    python -m tools.emi sheet-template <NEW|CHANGE|CANCEL> <file.json>  # empty booking JSON to fill
    python -m tools.emi sheet-check <booking.json>        # check a filled booking without writing
    python -m tools.emi sheet-find <text>                 # rows by ref, guest name, confirmation no., or arrival DD/MM/YYYY
                                                          #   (Emi's sheet + the live sheet, read only)
    python -m tools.emi direct-ref                        # next booking_ref for a direct guest, HAYA-D + number
    python -m tools.emi sheet-rows <first> [<last>]       # rows as they are on the sheet, filled cells only
    python -m tools.emi sheet-audit [--from-row N]        # rows already on the sheet that break the sheet-check rules
    python -m tools.emi sheet-append <booking.json>       # new booking: {"booking": {...}, "room_lines": [{...}, ...]}
    python -m tools.emi sheet-update <row> <fields.json>  # change named cells on one row
    python -m tools.emi draft-reply <message_id> <body.txt> [--to A[,B] [--cc C] | --sender-only] [--kind K --ref R --row N]
                                                          # reply all by default, To and Cc kept
    python -m tools.emi draft-forward <message_id> <to> <body.txt> [--kind K --ref R --row N]
    python -m tools.emi draft-attach <draft_id> <file>
    python -m tools.emi forget-confirmation <ref> <row>   # only after a person deleted that confirmation draft
    python -m tools.emi quote --arrival DD/MM/YYYY --departure DD/MM/YYYY --adults N [--children "13;5"] [--rooms N] [--room-type X] [--alloc "STD:3,TPL:1"] [--twin] [--indian] [--channel TA|Direct]
    python -m tools.emi stop-sales                        # room types with 1 room or fewer left: stop-sales email due
    python -m tools.emi cancel-fee <booking_ref> [--cancelled-at "DD/MM/YYYY HH:MM"] [--no-show]  # TA cancellation charge
    python -m tools.emi pdf-fetch <row>                   # download the file behind pdf_link, print it next to the row
    python -m tools.emi draft-confirmation <message_id> <row> <body.txt> [--all | --to A [--cc C]] [--subject S] [--attach F]
                                                          # reply + EZFOLIO PDF; --subject: a new email (Odeon)
    python -m tools.emi draft-new <message_id> <to> <subject> <body.txt> [--cc C] [--kind K --ref R --row N] [--attach F]
                                                          # a new email, not a reply (Odeon decline)
    python -m tools.emi to-info <operator>                # tour operator: the steps and what differs for this one
    python -m tools.emi to-price --operator X --arrival D --departure D --room CODE --adults N [--children "7;1"]
                                 [--rooms N] [--meal BB|HB|FB] --booked D [--spo "EB,FS001"]  # contract price
    python -m tools.emi on-request --arrival D --departure D --alloc "DLX-SV:1"  # reject / ask Karen
    python -m tools.emi checkouts --company X (--from D [--to D] | --last-week)  # check-outs for operator invoicing
    python -m tools.emi invoice-data <booking_ref>        # proforma figures: number, due date, lines
    python -m tools.emi ask-karen <message_id> "<question>" [--ref R]  # an uncertain fact: ask; the draft carries a CHECK line
    python -m tools.emi karen-answer <E-001> "<answer>"   # her answer: then write the draft for that email
    python -m tools.emi questions [--all]                 # questions to Karen still open (--all: answered too)
    python -m tools.emi status                            # scan clock and counts
    python -m tools.emi review-list [--all]               # drafts #n waiting for a person (Telegram notices)
    python -m tools.emi review-info <n>                   # one draft: source email, full text, history
    python -m tools.emi review-ask <n>                    # Rewrite pressed: prints the question to send, remembers #n
    python -m tools.emi review-awaiting                   # which draft the next message is feedback for
    python -m tools.emi review-accept <n> [--by NAME]     # tag 'Emi approved' — NOT sent; a person presses Send
    python -m tools.emi review-deny <n> [--reason R]      # draft to Deleted Items
    python -m tools.emi review-rewrite <n> <body.txt> --feedback "reviewer's words"  # new draft replaces old
    python -m tools.emi review-notify <n>                 # notice + buttons back in place (or sent again)
    python -m tools.emi sim-reset <scenario>              # test/sim/<scenario>: fresh test inbox, old TEST rows removed
    python -m tools.emi sim-check <scenario>              # grade sheet + drafts after a run with EMI_SIM_DIR set

Every draft stays in Drafts with the Emi category. Nothing here can send (graph_mail refuses).
A draft is the complete best answer (Tracy audit 29/10): a '[...: hotel to confirm]' gap inside the text is refused.
What is uncertain goes in one first line '[CHECK BEFORE SENDING: ...]' (bold red in the draft) and to Karen with
ask-karen. Karen's name is never in a draft.

A reply goes to whoever sent the email. When that is our own staff (haya@haya-hotels.com forwarding a guest's or
agency's mail into sales@), draft-reply refuses: reply to the real sender, the From: in the quoted header, with
--to <address> (--cc haya@haya-hotels.com so front office sees the answer). draft-forward refuses anything to
front office (haya@): requests go in the row's notes, which front office reads in EZFOLIO (dev 30/10).
Exit 0 = done, 2 = refused or failed (reason on stderr).
"""
import argparse
import json
import mimetypes
import re
import os
import sys
from datetime import datetime, timedelta, timezone

from . import attachments, config, drive
from .graph_mail import is_internal
from . import quote as quoting
from . import cancel_fee as cancelling
from . import operator_rates as op_rates
from . import operators
from . import availability as avail
from . import review, sim
from . import intake_schema as schema
from .state import REVIEW_OPEN, now_iso

VN = timezone(timedelta(hours=7))
WORK_DIR = os.environ.get("EMI_WORK_DIR", "emi-work")
FIRST_SCAN_LOOKBACK = timedelta(hours=24)   # inbox-triage.md: no last scan -> the last 24 hours
# Fake "new booking" senders (Tracy audit 29/10): never listed, logged, drafted, clicked or reported.
PHISHING_SENDERS = {"care@mail.myjorney.com", "vip@mail.voyageandco.com"}


class Refused(Exception):
    pass


def vn(iso):
    """'2026-10-15T03:12:00Z' -> '15/10/2026 10:12' Vietnam time."""
    if not iso:
        return ""
    dt = datetime.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    return dt.astimezone(VN).strftime("%d/%m/%Y %H:%M")


def addr(r):
    e = (r or {}).get("emailAddress", {})
    return f"{e.get('name', '')} <{e.get('address', '')}>".strip()


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def read_text(path):
    with open(path, encoding="utf-8") as f:
        text = f.read().strip()
    if not text:
        raise Refused(f"{path} is empty")
    return text


# --- inbox ---

def inbox_new(mail, st, out=print):
    started = now_iso()
    since = st.data["last_scan"]
    if since is None:
        since = (datetime.now(timezone.utc) - FIRST_SCAN_LOOKBACK).strftime("%Y-%m-%dT%H:%M:%SZ")
        out(f"first scan: no last_scan saved, reading the last {FIRST_SCAN_LOOKBACK.total_seconds() / 3600:.0f} hours")
    msgs = [m for m in mail.list_inbox_since(since) if not st.is_processed(m["id"])
            and _sender(m) not in PHISHING_SENDERS]
    if config.SIM_DIR:
        out(f"SIM MODE: emails from {config.SIM_DIR}/inbox, drafts to files — the real mailbox is not touched")
    only = [] if config.SIM_DIR else [a.strip().lower() for a in os.environ.get("EMI_TEST_ONLY_FROM", "").split(",")
                                      if a.strip()]
    if only:
        # Test phase: real mail in the window is left alone (not read, not marked). Remove the variable to go live.
        skipped = [m for m in msgs if _sender(m) not in only]
        msgs = [m for m in msgs if _sender(m) in only]
        out(f"TEST MODE (EMI_TEST_ONLY_FROM): only mail from {', '.join(only)}; "
            f"{len(skipped)} other email(s) in the window ignored")
    out(f"scan_started={started}")
    out(f"since={since} ({vn(since)} Vietnam time)")
    out(f"new emails: {len(msgs)}")
    for m in msgs:
        clip = " [attachments]" if m.get("hasAttachments") else ""
        out(f"\n- id: {m['id']}\n  received: {vn(m['receivedDateTime'])}\n  from: {addr(m.get('from'))}"
            f"\n  subject: {m.get('subject', '')}{clip}")
    return msgs, started


def mail_find(mail, text, out=print):
    hits = mail.search(text)
    out(f"emails found: {len(hits)} (newest first)")
    for m in hits:
        out(f"\n- id: {m['id']}\n  received: {vn(m.get('receivedDateTime'))}\n  from: {addr(m.get('from'))}"
            f"\n  subject: {m.get('subject', '')}")
    return hits


def sent_dump(mail, days, path, own_chars=3000, quoted_chars=800, out=print):
    """HAYA's sent mail of the last `days` days, to learn how the team writes each kind of reply. Read-only.
    Per message: time, to/cc, subject, its own text and the start of what it answers. Emi's own drafts
    (category Emi) are marked, so they can be left out of the style study."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    msgs = mail.list_sent_since(since)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    emi_n = 0
    with open(path, "w", encoding="utf-8") as f:
        for i, m in enumerate(msgs, 1):
            full = mail.get_message_bodies(m["id"])
            own = (full.get("uniqueBody") or {}).get("content", "").strip()
            body = (full.get("body") or {}).get("content", "").strip()
            quoted = body[len(own):].strip() if own and body.startswith(own[:50]) else ""
            by_emi = "Emi" in (full.get("categories") or [])
            emi_n += by_emi
            cc = ", ".join(addr(r) for r in full.get("ccRecipients", []))
            f.write(f"\n##### {i} | {vn(m.get('sentDateTime'))} | {'EMI DRAFT' if by_emi else 'staff'}\n"
                    f"to: {', '.join(addr(r) for r in full.get('toRecipients', []))}\n"
                    + (f"cc: {cc}\n" if cc else "")
                    + f"subject: {full.get('subject', '')}\n--- text\n{own[:own_chars]}\n"
                    + (f"--- answering\n{quoted[:quoted_chars]}\n" if quoted else ""))
    out(f"sent since {vn(since)}: {len(msgs)} message(s), {emi_n} written by Emi -> {os.path.abspath(path)} "
        f"({os.path.getsize(path)} bytes)")
    return len(msgs)


def _sender(m):
    return (m.get("from") or {}).get("emailAddress", {}).get("address", "").lower()


def show(mail, message_id, work_dir=None, out=print):
    work_dir = work_dir or WORK_DIR
    target = mail.get_message_text(message_id)
    thread = [m for m in mail.get_thread(target["conversationId"], text=True) if not m.get("isDraft")]
    if not any(m["id"] == message_id for m in thread):
        thread.append(target)
    out(f"thread: {len(thread)} message(s), oldest first. Target = the one marked >>>.")
    for m in thread:
        is_target = m["id"] == message_id
        mark = ">>> " if is_target else ""
        out(f"\n===== {mark}{vn(m.get('receivedDateTime'))} | from {addr(m.get('from'))}")
        out(f"to: {', '.join(addr(r) for r in m.get('toRecipients', []))}")
        if m.get("ccRecipients"):
            out(f"cc: {', '.join(addr(r) for r in m['ccRecipients'])}")
        out(f"subject: {m.get('subject', '')}")
        out(f"id: {m['id']}")
        # Target: full body, so quoted history from outside this mailbox is still there.
        # Earlier messages: only their own new text.
        body = (m.get("body") if is_target else m.get("uniqueBody") or m.get("body")) or {}
        out("")
        out(body.get("content", "").strip())
        if m.get("hasAttachments"):
            _show_attachments(mail, m["id"], work_dir, out)


def _show_attachments(mail, message_id, work_dir, out):
    folder = attachments.message_dir(work_dir, message_id)
    for att in mail.list_attachments(message_id):
        if "data" not in att:
            out(f"\n[attachment {att.get('name')!r}: {att.get('@odata.type', '')} — not a file, not saved]")
            continue
        if attachments.skip(att):
            continue
        path = attachments.save(folder, att)
        out(f"\n[attachment saved: {os.path.abspath(path)} ({len(att['data'])} bytes)]")
        out(attachments.clip(attachments.extract_text(path, att["data"])))


# --- sheet ---

def live_rows(live, out=print):
    """The live intake sheet's rows, read only (dev 30/10); [] with a GAP line when it can't be read."""
    if live is None:
        return []
    try:
        return live.rows()
    except Exception as e:  # not shared yet (403), network: look on Emi's own sheet only, and say so
        out(f"GAP: live intake sheet not readable ({str(e).splitlines()[0][:120]}) — looked on Emi's sheet only; "
            "a booking from before 22/10 may be there")
        return []


def direct_ref(sheet, live=None, out=print):
    """The next booking_ref for a direct guest: HAYA-D + a running number, counted over Emi's sheet and the live
    one (dev 30/10, live sheet row 2). The live sheet must be readable: a number taken there must not repeat."""
    rows = sheet.rows()
    if live is not None:
        try:
            rows += live.rows()
        except Exception as e:
            raise Refused(f"live intake sheet not readable ({str(e).splitlines()[0][:120]}): a direct booking's "
                          "number can't be picked without it") from None
    nums = [m.group(1) for r in rows for p in schema.ref_parts(r.get("booking_ref") or "")
            if (m := re.fullmatch(r"HAYA-D(\d+)", p.strip(), re.I))]
    width = max([3] + [len(n) for n in nums])
    ref = f"HAYA-D{max([0] + [int(n) for n in nums]) + 1:0{width}d}"
    out(f"{ref}  (highest so far: {max(nums, key=int) if nums else 'none'}). Write the row with sheet-append "
        f"before asking for the next one.")
    return ref


def _where(r):
    return f"live row {r['_row']}" if r.get("_sheet") == "live" else f"row {r['_row']}"


def sheet_find(sheet, text, out=print, live=None):
    """booking_ref, guest_names or confirmation_no containing text, or arrival equal to it (DD/MM/YYYY): a guest
    writing with the OTA's own number and a Cyrillic name is found by the arrival date (dev 30/10, Booking.com
    5486733008, on the sheet only as SynXis 92777EF003114 'Anna Ivanova')."""
    t = text.strip().lower()
    match = lambda r: (any(t in r.get(c, "").lower() for c in ("booking_ref", "guest_names", "confirmation_no"))
                       or t == r.get("arrival", "").strip())
    hits = [r for r in sheet.rows() if match(r)]
    found_live = [r for r in live_rows(live, out) if match(r)]
    out(f"rows found: {len(hits)}" + (f" on Emi's sheet, {len(found_live)} on the live sheet (read only; "
                                       "'_sheet': 'live')" if live is not None else ""))
    for r in hits + found_live:
        out(json.dumps({k: v for k, v in r.items() if v}, ensure_ascii=False))
    return hits + found_live


def expand_booking(data):
    """{"booking": {shared columns}, "room_lines": [{room columns}, ...]} -> one row per room type.
    A plain list of rows (or one row) passes through unchanged."""
    if isinstance(data, dict) and "room_lines" in data:
        shared = data.get("booking") or {}
        lines = data["room_lines"]
        if not lines:
            raise Refused("room_lines is empty: one entry per room type")
        return [{**shared, **line} for line in lines]
    return [data] if isinstance(data, dict) else list(data)


BACKDATED_DAYS = 2


def _earlier_arrivals(sheet, records):
    """{booking_ref: arrivals on its rows already on the sheet}, read only when a CHANGE needs it (F-04)."""
    refs = {rec.get("booking_ref") for rec in records if rec.get("action") == "CHANGE" and rec.get("booking_ref")}
    if not refs:
        return {}
    rows = sheet.rows()
    return {ref: {str(r.get("arrival", "")).strip() for r in rows if _parts(r.get("booking_ref")) & _parts(ref)
                  and str(r.get("arrival", "")).strip()} for ref in refs}


def check_rows(sheet, records, fresh=True):
    """Check every row against tools/intake_schema.py; all problems at once, so one fix covers them.
    fresh=True: rows about to be written (not sheet-update of a row already there)."""
    codes = schema.room_codes(sheet)
    errors, warnings = [], []
    earlier = _earlier_arrivals(sheet, records)
    for i, rec in enumerate(records, 1):
        unknown = sorted(set(rec) - set(sheet.header) - {"_row"})
        label = f"row {i} ({rec.get('room_code') or 'no room_code'})"
        if unknown:
            errors.append(f"{label}: not sheet columns {unknown} — run sheet-schema for the exact names")
        e, w = schema.check_row(rec, codes, earlier_arrivals=earlier.get(rec.get("booking_ref")))
        if not fresh:  # a row written before 30/10 without COD: updating another cell isn't blocked by it
            w += [x for x in e if x.startswith("COD:")]
            e = [x for x in e if not x.startswith("COD:")]
        received = schema._date(rec.get("received_at") or "", "%d/%m/%Y %H:%M")
        if fresh and rec.get("action") == "NEW" and received and (
                (_today_vn() - received.date()).days > BACKDATED_DAYS):
            # audit 30/10 (F-03): NEW rows dated back to the original email for bookings HAYA already had
            w.append(f"received_at: {rec['received_at']} — a NEW dated {(_today_vn() - received.date()).days} days "
                     f"back. If the thread shows HAYA already has this booking (its confirmation, a confirmation "
                     f"number or group code, a modification, a payment, the guest in house), it is in EZFOLIO: "
                     f"CHANGE rows with 'original booking not on the sheet', not NEW (booking-intake.md)")
        errors += [f"{label}: {x}" for x in e]
        warnings += [f"{label}: {x}" for x in w]
    if len({r.get("booking_ref", "") for r in records}) > 1:
        errors.append("rows of one booking must share one booking_ref")
    return errors, warnings


def sheet_check(sheet, data, out=print):
    records = expand_booking(data)
    errors, warnings = check_rows(sheet, records)
    for w in warnings:
        out(f"WARNING {w}")
    if errors:
        raise Refused("fix these, then run sheet-check again:\n  " + "\n  ".join(errors))
    out(f"OK: {len(records)} row(s) pass the checks")
    return records


def sheet_rows(sheet, first, last=None, out=print):
    """Rows first..last as they are on the sheet, filled cells only. Read-only."""
    rows = [r for r in sheet.rows() if r["_row"] >= first and (last is None or r["_row"] <= last)]
    for r in rows:
        out(f"row {r['_row']}: " + json.dumps({k: v for k, v in r.items() if v and k != "_row"}, ensure_ascii=False))
    out(f"{len(rows)} row(s)")


def sheet_audit(sheet, first_row=3, out=print):
    """Check rows already on the sheet (from first_row on) with the same rules as sheet-check, one line each.
    For finding rows written before a rule existed, or by hand."""
    codes = schema.room_codes(sheet)
    bad = 0
    rows = [r for r in sheet.rows() if r["_row"] >= first_row]
    for r in rows:
        e, w = schema.check_row(r, codes)
        if not (e or w):
            continue
        bad += bool(e)
        out(f"row {r['_row']} {r.get('action', '')} {r.get('booking_ref') or '(no ref)'} "
            f"{r.get('room_code') or ''}".rstrip()
            + "".join(f"\n  ERROR {x}" for x in e) + "".join(f"\n  warning {x}" for x in w))
    out(f"\n{len(rows)} row(s) checked from row {first_row}: {bad} with errors")
    return bad


def _parts(ref):
    """The reference numbers in a booking_ref, for matching. Rows written the live sheet's way name the channel
    before each number ('Booking.com 5486733008 / SynXis 92777EF003114', 'SynXis 92777EF002779 (Booking.com
    5550972513)', 'MG AGSG0528672610514149 / HB2610327806'): each number counts on its own. A TA code with
    spaces ('Thu1230 TVR149') stays whole, and dates ('23/11-26/11') never count."""
    ref = (ref or "").strip()
    out = {p.lower() for p in schema.ref_parts(ref)}
    if re.match(r"[^\d\s]+\s", ref):
        out |= {n.lower() for n in schema.ref_numbers(ref)
                if re.search(r"[A-Za-z]", n) or len(re.sub(r"\D", "", n)) >= 6}
    return out


def booking_state(rows, ref):
    """The booking as it stands: the rows of the last email written for this ref (one per room type).
    Each number counts on its own: '1783017402' finds '1783017402 / 92777EF002717'."""
    mine = _parts(ref)
    hits = [r for r in rows if mine and _parts(r.get("booking_ref")) & mine]
    if not hits:
        return []
    key = (hits[-1].get("action"), hits[-1].get("received_at"))
    state = []
    for r in reversed(hits):
        if (r.get("action"), r.get("received_at")) != key:
            break
        state.insert(0, r)
    return state


# Copied from the booking's current rows onto a CHANGE / CANCEL row where left blank (Rules tab: "repeat the
# full new booking details for CHANGE"). Live sheet 2026-10-27: CHANGE rows with no company, channel, rates or
# adults; CANCEL rows with no group code and without the Indian or child surcharge. Not copied: what the new
# email itself says (transfer, requests, status, notes).
CARRY_BOOKING = ("channel_type", "company", "contact_person", "company_email", "ezfolio_group_code",
                 "confirmation_no", "guest_names", "nationality", "arrival", "departure", "nights", "prepaid",
                 "invoice_details", "COD", "Payment 1", "Payment 1 date + time", "Payment 2",
                 "Payment 2 date + time")
CARRY_ROOM = ("room_code", "rooms", "meal_plan")
# Copied as a block, only when its first column is blank: a change that sets a new rate (a surcharge waived)
# must not get the old surcharge back.
CARRY_BLOCKS = (("adults", "children", "child_ages"),
                ("rate_per_night_vnd", "rate_source", "discount_promo", "Average rate per night after discount",
                 "surcharge", "Surcharge amount", "total_vnd"))


# Tracy audit 29/10: Karen's EZFOLIO tool copies only the LATEST CHANGE row's notes into the Notice, so every
# CHANGE row (not only a tour operator's) holds the full notes 1-8 and its own rate fields.
CHANGE_OWN = ("notes", "rate_source", "rate_per_night_vnd", "Average rate per night after discount", "total_vnd",
              "status", "nights", "meal_plan")


def _blank(v):
    return not str(v if v is not None else "").strip()


def carry_over(records, state, out=print):
    """Fill the blanks of CHANGE / CANCEL rows from the booking's current rows; returns the rows to write.
    A CANCEL given as one line with no room_code becomes one CANCEL row per room line of the booking."""
    if not state:
        return records
    if (len(records) == 1 and records[0].get("action") == "CANCEL" and _blank(records[0].get("room_code"))
            and len(state) > 1):
        records = [dict(records[0], room_code=r.get("room_code", "")) for r in state]
    for rec in records:
        if rec.get("action") not in ("CHANGE", "CANCEL"):
            continue
        same = [r for r in state if r.get("room_code") == rec.get("room_code")]
        if not same and _blank(rec.get("room_code")) and len(state) == 1:
            same = state
        cols = [k for k in CARRY_BOOKING if _blank(rec.get(k))]
        if same:
            cols += [k for k in CARRY_ROOM if _blank(rec.get(k))]
            for block in CARRY_BLOCKS:
                if _blank(rec.get(block[0])):
                    cols += [k for k in block if _blank(rec.get(k))]
        src = (same or state)[0]
        filled = [k for k in cols if not _blank(src.get(k))]
        for k in filled:
            rec[k] = src[k]
        if rec["action"] == "CANCEL":
            rec["Remaining amount"] = "0"  # dev 30/10: 22 CANCEL rows kept the full total
        if filled:
            out(f"{rec['action']} {rec.get('room_code') or ''}: blanks copied from {_where(src)}: "
                f"{', '.join(filled)}")
    return records


def fill_group_code(records, rows, group_cols, out=print):
    """CHANGE / CANCEL rows carry the group code in every group-code column (Tracy audit 29/10). Not on the
    booking's latest rows -> any earlier row of the booking (the NEW row usually has it)."""
    for rec in records:
        if rec.get("action") not in ("CHANGE", "CANCEL"):
            continue
        code = next((rec.get(c) for c in group_cols if not _blank(rec.get(c))), "")
        if not code:
            mine = _parts(rec.get("booking_ref"))
            earlier = [r for r in rows if mine and _parts(r.get("booking_ref")) & mine
                       and any(not _blank(r.get(c)) for c in group_cols)]
            if earlier:
                src = earlier[-1]
                code = next(src[c] for c in group_cols if not _blank(src.get(c)))
                out(f"{rec['action']} {rec.get('room_code') or ''}: group code {code} from row {src['_row']}")
        if code:
            for c in group_cols:
                if _blank(rec.get(c)):
                    rec[c] = code
    return records


def verify_appended(sheet, records):
    """Read the sheet back after a write: every row written must be there with its key cells (Tracy audit 29/10:
    re-read, write, verify)."""
    keys = ("action", "booking_ref", "received_at", "room_code", "total_vnd")
    rows = sheet.rows()
    missing = [rec for rec in records
               if not any(all(str(r.get(k, "")).strip() == str(rec.get(k, "") or "").strip() for k in keys)
                          for r in rows)]
    if missing:
        raise Refused(f"wrote {len(records)} row(s) but {len(missing)} not found on the sheet afterwards "
                      f"({', '.join(str(m.get('room_code') or '?') for m in missing)}): check with sheet-find "
                      f"before writing again, never append twice")


def sheet_append(sheet, data, out=print, live=None):
    records = expand_booking(data)
    if not records:
        raise Refused("no rows given")
    rows = None
    elsewhere = None  # the live sheet's rows, read once: a booking from before 22/10 is only there (dev 30/10)
    cancelled_here = {p for rec in records if rec.get("action") == "CANCEL" for p in _parts(rec.get("booking_ref"))}
    for rec in records:
        ref = str(rec.get("booking_ref", "")).strip()
        if not ref:
            continue
        if rows is None:
            rows = sheet.rows()
            elsewhere = live_rows(live, out)
        state = booking_state(rows, ref) or booking_state(elsewhere, ref)
        if rec.get("action") == "NEW" and state:
            # Rules tab: a CHANGE or CANCEL is a new row with the same booking_ref; only NEW must be unique.
            # Except a cancel-and-rebuild (GD0512, 26/10): CANCEL rows and NEW rows from the same email.
            rebuild = bool(_parts(ref) & cancelled_here) or (
                state[0].get("action") == "CANCEL" and state[0].get("received_at") == rec.get("received_at"))
            if not rebuild:
                hit = next(r for r in rows + elsewhere if _parts(r.get("booking_ref")) & _parts(ref))
                raise Refused(f"booking_ref {ref!r}: {', '.join(sorted(_parts(hit['booking_ref']) & _parts(ref)))} "
                              f"is already on the {'live ' if hit.get('_sheet') == 'live' else ''}sheet "
                              f"({_where(hit)}): this is not a NEW booking. Use action CHANGE (new rows, what_changed "
                              f"filled)" + ("" if hit.get("_sheet") == "live" else f", or sheet-update row "
                              f"{hit['_row']} to add the other number") + ". A cancel-and-rebuild: the CANCEL rows "
                              "and the NEW rows in one file")
        if rec.get("action") == "CHANGE" and not any(rec.get(p) for p in schema.PAYMENT) and state and all(
                r.get("action") == "NEW" and r.get("_sheet") != "live" for r in state):
            # dev 30/10: the live sheet folds news into the NEW row until the booking is built (Victoria
            # INBOM04540000001: nationality and adults went into NEW row 803, no CHANGE row)
            mine = [r for r in rows + elsewhere if _parts(r.get("booking_ref")) & _parts(ref)]
            if not any(schema.is_built(r) for r in mine):
                raise Refused(f"{ref} isn't built yet (no pdf_link on either sheet): news before the build goes into "
                              f"the NEW row — sheet-update {' and '.join(str(r['_row']) for r in state)} with the "
                              f"cells this email changes, as the live sheet does. A CHANGE row once it's built; a "
                              f"payment is always a CHANGE row")
        if rec.get("action") == "CHANGE":
            missing = [k for k in CHANGE_OWN if _blank(rec.get(k))]
            if missing:
                raise Refused(f"CHANGE {rec.get('room_code') or ''}: fill {', '.join(missing)} on this row, not "
                              f"copied from the old rows. The build tool copies only the latest CHANGE row's notes "
                              f"into the Notice: notes 1-8 in full, rate fields as the booking now stands "
                              f"(tour operator: to-price)")
        if rec.get("action") == "CANCEL" and state and state[0].get("action") == "CANCEL":
            # 2026-10-27: operators' cancel notices for bookings already closed as declined on request
            raise Refused(f"booking_ref {ref!r} is already cancelled (row {state[0]['_row']}, "
                          f"{state[0].get('received_at', '')}): no second CANCEL row; mark the email done")
    if rows is not None and any(r.get("action") in ("CHANGE", "CANCEL") for r in records):
        ref0 = records[0].get("booking_ref")
        records = carry_over(records, booking_state(rows, ref0) or booking_state(elsewhere, ref0), out=out)
        records = fill_group_code(records, rows + elsewhere, sheet.group_code_columns(), out=out)
    sheet_check(sheet, records, out=out)
    sheet.append_rows(records)
    verify_appended(sheet, records)
    out(f"appended {len(records)} row(s), read back from the sheet. Check them below; fix a wrong cell with "
        f"sheet-update <row> by column name.")
    for ref in dict.fromkeys(rec["booking_ref"] for rec in records if rec.get("booking_ref")):
        for r in sheet.find_by_ref(ref):
            out(f"row {r['_row']}: " + json.dumps({k: v for k, v in r.items() if v and k != "_row"},
                                                  ensure_ascii=False))


def sheet_update(sheet, row, fields, work_dir=None, out=print):
    """Correct or update a NEW row not yet built: a wrong cell, or news from a later email (nationality, pax,
    names, a request) — the live sheet folds those into the NEW row until the build (dev 30/10). After the build,
    and for a payment at any time, a CHANGE row instead.
    The row as it was is saved to <work_dir>/sheet-backup first, and read back after (Tracy audit 29/10)."""
    if not fields:
        raise Refused("no fields given")
    current = next((r for r in sheet.rows() if r["_row"] == int(row)), None)
    if current is None:
        raise Refused(f"row {row} is empty or not a data row")
    pay = sorted(set(fields) & {"Payment 1", "Payment 1 date + time", "Payment 2", "Payment 2 date + time"})
    if pay:
        raise Refused(f"{pay}: a payment is a CHANGE row (sheet-template CHANGE, what_changed 'Payment 1 "
                      f"received …'), not an edit of row {row}")
    if schema.is_built(current):
        raise Refused(f"row {row} is already built in EZFOLIO (pdf_link or tracy_status set): write a CHANGE row, "
                      f"or report the wrong cell to Karen")
    group = sorted(set(fields) & set(sheet.group_code_columns()))
    if group and current.get("action") != "CANCEL":
        raise Refused(f"{group}: the group code is written only on CHANGE / CANCEL rows (sheet-append carries it), "
                      f"or when Karen asks")
    merged = {k: v for k, v in {**current, **fields}.items() if k != "_row"}
    errors, warnings = check_rows(sheet, [merged], fresh=False)
    for w in warnings:
        out(f"WARNING {w}")
    if errors:
        raise Refused(f"row {row} would not pass the checks after this update:\n  " + "\n  ".join(errors))
    folder = os.path.join(work_dir or WORK_DIR, "sheet-backup")
    os.makedirs(folder, exist_ok=True)
    backup = os.path.join(folder, f"row{int(row)}-{datetime.now(VN):%Y%m%d-%H%M%S}.json")
    with open(backup, "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=1)
    sheet.update_cells(int(row), fields)
    after = next((r for r in sheet.rows() if r["_row"] == int(row)), {})
    wrong = [k for k, v in fields.items() if str(after.get(k, "")).strip() != str(v).strip()]
    if wrong:
        raise Refused(f"row {row} read back after the update does not show {wrong}; the row as it was is in "
                      f"{backup}. Report to Karen, don't retry blindly")
    out(f"updated row {row}: {sorted(fields)} (read back OK; backup {backup})")


def sheet_schema(sheet, out=print):
    """Every column with where it goes, what it takes and the sheet's own instruction (row 2)."""
    instr = schema.instructions(sheet)
    out("COLUMNS (exact names). level: booking = same on every row of the booking; room_lines = one per room type;")
    out("build tool / payment (later) = not filled when a booking first arrives.")
    for h in sheet.header:
        req = ("REQUIRED (NEW/CHANGE)" if h in schema.REQUIRED_BOOKING_ROW else
               "never blank" if h in schema.ALWAYS else "")
        allowed = (f"one of {list(schema.ENUMS[h])}" if h in schema.ENUMS else
                   "starts with Yes / No" if h in schema.PREFIX_ENUMS else
                   "DD/MM/YYYY" if h in schema.DATES else "DD/MM/YYYY HH:MM" if h in schema.DATETIMES else
                   "whole number" if h in schema.INTEGERS else "VND digits only" if h in schema.AMOUNTS else
                   "VND digits, minus allowed (rounding)" if h in schema.SIGNED_AMOUNTS else
                   "Room codes tab, below" if h == "room_code" else "")
        out(f"- {h} | {schema.level(h)} | {req} | {allowed} | {instr.get(h, '')}".replace(" |  |", " |"))
    codes = schema.room_codes(sheet) or {}
    # Agencies write the TA table's names ("Standard Double"), EZFOLIO's names differ ("STANDARD GARDEN").
    ta_names = {r["code"]: r["name_en"] for r in quoting.load()["rooms"]}
    ta_names.setdefault("STD-TWN", "Standard Twin (quoted at the Superior Twin rate)")
    # OTA listings use their own names; the live sheet maps them like this (2026-10-27).
    ota_names = {"TW-DLX": "Deluxe Twin Sea View", "TPL": "Triple City View", "DLX-SV": "Deluxe Double Sea View"}
    out("\nROOM CODES (room_code). Match the name in the email against the 'agencies call it' name:")
    for code, (name, note) in codes.items():
        alias = f" — agencies call it \"{ta_names[code]}\"" if code in ta_names else ""
        alias += f" — OTAs call it \"{ota_names[code]}\"" if code in ota_names else ""
        out(f"- {code} = {name}{alias}" + (f" — {note}" if note else ""))
    out("A room name in the email that matches none of these → leave room_code blank and name it in missing_info.")
    out("\nRULES (Rules tab):")
    for r in schema.rules(sheet):
        out(f"- {r}")
    out("\nWrite a booking with: sheet-template NEW <file>, fill it, sheet-check <file>, then sheet-append <file>.")


def sheet_template(sheet, action, path, out=print):
    if action not in schema.ENUMS["action"]:
        raise Refused(f"action must be one of {list(schema.ENUMS['action'])}")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(schema.template(sheet, action), f, ensure_ascii=False, indent=2)
    out(f"wrote {path}: fill the values (one room_lines entry per room type), delete nothing, "
        f"leave unknowns blank and name them in missing_info")


# --- drafts ---

def _record(st, draft, args):
    st.record_draft(draft["id"], args.ref or "", int(args.row or 0), args.kind)


def telegram_first(tg):
    """EMI_DRAFT_MODE=telegram: drafts go to Telegram only and reach Outlook on Accept. Without a working
    Telegram set-up the draft goes straight to Outlook, so no draft is ever lost."""
    return os.environ.get("EMI_DRAFT_MODE", "outlook").lower() == "telegram" and tg is not None


def pending_store():
    return os.path.join(config.SIM_DIR or WORK_DIR, "pending")


def _addresses(text):
    return [a.strip() for a in (text or "").split(",") if a.strip()]


def _sender_of(mail, message_id):
    return (mail.get_message_text(message_id).get("from") or {}).get("emailAddress", {}).get("address", "")


# Drafts that speak to a guest or an agency. They never go to our own staff, --internal or not.
GUEST_KINDS = ("request", "inquiry", "confirmation", "cancellation", "deposit_reminder", "balance_reminder")

FORWARDED_IN = ("this email is from {sender}, our own staff, not the guest or agency: a reply would go back to "
                "{sender}. If it is a forward (Fw:), the real sender is the 'From:' line in the quoted header: "
                "reply to that address with --to <address> --cc {sender} (skills/email-templates.md, 'Who the "
                "reply goes to'). Only if you really are answering a colleague: --internal (--kind reply).")


def reply_recipients(mail, args, kind):
    """(to, cc) for a reply: the --to / --cc lists, or (None, None) to let the mailbox answer the sender.
    Refuses a reply that would land on our own staff: the bug of 2026-10-22, when replies to guests whose
    mail front office had forwarded in went to haya@haya-hotels.com."""
    to, cc = _addresses(getattr(args, "to", "")), _addresses(getattr(args, "cc", ""))
    internal = getattr(args, "internal", False)
    if cc and not to:
        raise Refused("--cc goes with --to: name the main recipient too")
    if to and getattr(args, "all", False):
        raise Refused("--to sets the recipients itself: drop --all and list everyone in --to / --cc")
    if internal and kind in GUEST_KINDS:
        raise Refused(f"--internal is for a reply to a colleague; a {kind} draft goes to the guest or agency")
    if to:
        ours = [a for a in to if is_internal(a)]
        if ours and not internal:
            raise Refused(f"--to {', '.join(ours)} is our own address. Put the guest's or agency's address in --to "
                          f"(the 'From:' of the forwarded mail) and our colleague in --cc")
        return to, cc
    sender = _sender_of(mail, args.message_id)
    robot = operators.robot_operator(sender)
    if robot:
        # tour-operators.md: Anex mails from a no-reply robot; replies go to its reservations desk
        return list(operators.OPERATORS[robot]["reply_to"]), []
    if is_internal(sender) and not internal:
        raise Refused(FORWARDED_IN.format(sender=sender))
    return None, None


def _to_line(to, cc):
    if not to:
        return ""
    return f" (to {', '.join(to)}" + (f", cc {', '.join(cc)}" if cc else "") + ")"


# '[Indoor or outdoor: hotel to confirm]', '[giá đưa đón: khách sạn xác nhận]': a fact Emi doesn't have.
GAP = re.compile(r"\[[^\]\n]*(?:to confirm|xác nhận)[^\]\n]*\]", re.I)
# Tracy audit 29/10: the uncertain part of a best-answer draft is named in one first line, bold red in Outlook.
CHECK_LINE = re.compile(r"^\[CHECK BEFORE SENDING:[^\]\n]+\]$")
KAREN = re.compile(r"\bKaren\b", re.I)


def check_no_gaps(text, message_id="<message_id>"):
    """A draft is the complete best answer (Tracy audit 29/10; before that, dev 2026-10-22: no draft until
    Karen answers). A gap inside the text is refused; what is uncertain goes in one first line
    '[CHECK BEFORE SENDING: …]' and to Karen with ask-karen. Karen's name is never in a draft."""
    lines = text.strip().splitlines()
    first = lines[0].strip() if lines else ""
    body = "\n".join(lines[1:]) if CHECK_LINE.match(first) else text
    misplaced = [x.strip() for x in body.splitlines() if x.strip().upper().startswith("[CHECK BEFORE SENDING")]
    if misplaced:
        raise Refused(f"'[CHECK BEFORE SENDING: …]' is one line at the very top of the draft, nothing else on it, "
                      f"closed with ']': {' | '.join(misplaced)}")
    gaps = list(dict.fromkeys(GAP.findall(body)))
    if gaps:
        raise Refused(f"the text still has {len(gaps)} gap(s): {' | '.join(gaps)}. Write the best full answer "
                      f"instead, and name what is uncertain in a first line '[CHECK BEFORE SENDING: <what to check>]'; "
                      f"then ask-karen {message_id} \"<the uncertain fact, as a question>\" --ref <ref>.")
    if KAREN.search(text):
        raise Refused("the draft names Karen: never put Karen's name in a draft (Tracy audit 29/10). The sign-off "
                      "is Reservations Team; an internal note says 'khách sạn' / 'sales'.")


def reply_all_default(args, to):
    """Always reply all, keeping To and Cc (Tracy audit 29/10), unless --to sets the recipients itself or
    --sender-only asks for the sender alone."""
    return not to and not getattr(args, "sender_only", False)


def draft_reply(mail, st, args, tg=None, out=print):
    if args.kind == "confirmation" and not (args.ref and args.row):
        raise Refused("a confirmation draft needs --ref and --row")
    text = read_text(args.body)
    check_no_gaps(text, args.message_id)
    to, cc = reply_recipients(mail, args, args.kind)
    args.all = reply_all_default(args, to)
    note_pending_same(st, "reply", args.kind, args.ref, to, out=out)
    if telegram_first(tg):
        n = review.propose(mail, st, tg, pending_store(), how="reply", source=args.message_id, kind=args.kind,
                           ref=args.ref, row=int(args.row or 0), text=text, reply_all=args.all,
                           to=to, cc=cc, mailbox=config.MAILBOX)
        st.record_draft(review.PENDING + n, args.ref or "", int(args.row or 0), args.kind)
        out(f"draft #{n} sent to Telegram for review, not in Outlook until Accept: {review.PENDING}{n}"
            + _to_line(to, cc))
        return {"id": review.PENDING + n}
    d = mail.reply_draft_with_text(args.message_id, text, reply_all=args.all, to=to, cc=cc)
    _record(st, d, args)
    n = review.opened(mail, st, tg, d["id"], how="reply", source=args.message_id, kind=args.kind, ref=args.ref,
                      row=int(args.row or 0), text=text, reply_all=args.all, to=to, cc=cc, override=bool(to))
    out(f"draft #{n} saved in Drafts: {d['id']}" + _to_line(to, cc))
    return d


FRONT_OFFICE = "haya@haya-hotels.com"


def check_no_front_office_forward(to):
    """dev 30/10: front office reads a booking's requests in its EZFOLIO notes, so nothing is forwarded to haya@."""
    if FRONT_OFFICE in {a.lower() for a in to or []}:
        raise Refused(f"no forwards to front office ({FRONT_OFFICE}): put the requests in the row's special_requests "
                      "and notes item 5 (a CHANGE row for a booking already on the sheet); front office sees them in "
                      "EZFOLIO (department-forwards.md)")


def note_pending_same(st, how, kind, ref, to, out=print):
    """Audit 30/10 (F-10): an older draft of the same kind for the same booking and recipient still waits on
    Telegram. Nothing is changed; the report tells the reviewer which one to deny."""
    if not ref:
        return []
    lower = {a.lower() for a in to or []}
    older = [n for n, r in st.data["reviews"].items()
             if r.get("status") == REVIEW_OPEN and r.get("how") == how and r.get("kind") == kind
             and (r.get("ref") or "") == ref and (not lower or lower & {a.lower() for a in r.get("to") or []})]
    if older:
        out(f"NOTE: {', '.join('#' + n for n in older)} still pending for {ref} ({how}, {kind}). If this draft "
            f"replaces it, say in the report: 'deny {', '.join('#' + n for n in older)}, replaced by the new one'")
    return older


def draft_forward(mail, st, args, tg=None, out=print):
    to = _addresses(args.to)
    text = read_text(args.body)
    check_no_gaps(text, args.message_id)
    sender = _sender_of(mail, args.message_id)
    if is_internal(sender) and sender.lower() in [a.lower() for a in to]:
        raise Refused(f"{sender} forwarded this email to us: it already has it. Don't forward it back. Answer the "
                      f"guest or agency with draft-reply --to <the quoted From: address> --cc {sender}")
    check_no_front_office_forward(to)
    note_pending_same(st, "forward", args.kind, args.ref, to, out=out)
    lower = {a.lower() for a in to}
    for n, r in st.data["reviews"].items():
        # Slips and Palma mail are forwarded once (Tracy audit 29/10); a denied draft may be redone
        if (r.get("how") == "forward" and r.get("source") == args.message_id and r.get("status") != "denied"
                and lower & {a.lower() for a in r.get("to") or []}):
            raise Refused(f"this email already has a forward to {', '.join(sorted(lower & {a.lower() for a in r['to']}))}"
                          f" (draft #{n}, {r.get('status')}): never forward twice")
    if telegram_first(tg):
        n = review.propose(mail, st, tg, pending_store(), how="forward", source=args.message_id, kind=args.kind,
                           ref=args.ref, row=int(args.row or 0), text=text, to=to)
        st.record_draft(review.PENDING + n, args.ref or "", int(args.row or 0), args.kind)
        out(f"forward draft #{n} sent to Telegram for review, not in Outlook until Accept: {review.PENDING}{n} "
            f"(to {', '.join(to)})")
        return {"id": review.PENDING + n}
    d = mail.forward_draft_with_text(args.message_id, to, text)
    _record(st, d, args)
    n = review.opened(mail, st, tg, d["id"], how="forward", source=args.message_id, kind=args.kind, ref=args.ref,
                      row=int(args.row or 0), text=text, to=to)
    out(f"forward draft #{n} saved in Drafts: {d['id']} (to {', '.join(to)})")
    return d


def draft_attach(mail, st, draft_id, path, out=print):
    with open(path, "rb") as f:
        data = f.read()
    name = os.path.basename(path)
    ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
    if draft_id.startswith(review.PENDING):
        if review.attached(st, draft_id, name, data, ctype, store=pending_store()) is None:
            raise Refused(f"no draft {draft_id}")
        out(f"attached {name} to {draft_id} (goes into Outlook with the draft on Accept)")
        return
    mail.add_attachment(draft_id, name, data, content_type=ctype)
    review.attached(st, draft_id, name)
    out(f"attached {name} to {draft_id}")


def _review_n(text):
    m = re.fullmatch(r"#?(\d+)", text.strip())
    if not m:
        raise Refused(f"a draft number looks like 12 or #12 — got {text!r}")
    return m.group(1)


# --- inquiries (no booking yet) ---

OTHER_CHANNELS = {
    "Tour operator": "to-price --operator <Anex|Crystal Bay|Odeon|Pegas|Selfie> prices from that operator's own "
                     "contract; Fun and Sun has no contract — Karen",
    "OTA": "OTAs book through their own systems; an OTA inquiry by email goes to Karen",
}


def _today_vn():
    return datetime.now(VN).date()


def load_availability(out=print):
    """The availability sheet, or None with a GAP line when it can't be read."""
    try:
        return config.availability()
    except Exception as e:  # sheet not shared, network, layout changed: the quote still prints its prices
        out(f"GAP: availability sheet not readable ({e}) — availability and stop-sale NOT checked; "
            f"a person must check before sending")
        return None


AVAILABILITY_GAP_NEXT = ("AVAILABILITY NOT CHECKED: write the row as the email asks, with 'availability: not checked "
                         "– Future Availability sheet not readable' in missing_info, and carry on with the run "
                         "(mark-scanned as usual); one line for Karen at the top of the report")


def run_availability(args, data, out=print):
    try:
        result = avail.check(data, quoting.parse_date(args.arrival), quoting.parse_date(args.departure), _today_vn())
    except (avail.AvailabilityError, quoting.QuoteError) as e:
        raise Refused(str(e)) from None
    out(avail.render(data, result))
    if args.alloc:
        alloc = {k.strip(): int(v) for k, v in (part.split(":") for part in args.alloc.split(","))}
        problems = avail.fits(result, alloc)
        out("FITS: " + args.alloc if not problems else "DOES NOT FIT: " + "; ".join(problems))
    return result


def run_stop_sales(data, out=print):
    """Room types down to 1 room or fewer on a night (Tracy audit 29/10): close them on the B2B and OTA sites
    with a stop-sales email drafted in sales@, in the form and to the recipients of HAYA's past ones."""
    low = avail.low_inventory(data, _today_vn())
    out(avail.render_low(data, low))
    if low:
        out("Next: mail-find \"stop sale\" for HAYA's last stop-sales email (Sent Items): same recipients, same "
            "form, these room types and dates. draft-new <that email's id> <its recipients> \"<its subject form>\" "
            "<body> --kind stop_sales. Dates already closed in an earlier stop-sales email: not again. No past "
            "email found -> ask-karen for the recipients.")
    return low


def run_quote(args, out=print, availability=None):
    if args.channel not in quoting.TABLES:
        raise Refused(f"quote covers the TA and direct-guest tables only. "
                      f"{args.channel}: {OTHER_CHANNELS.get(args.channel, 'Karen')}")
    try:
        kids = [int(x) for x in re.split(r"[;,\s]+", args.children.strip()) if x] if args.children else []
    except ValueError:
        raise Refused(f"--children takes ages separated by ';', e.g. '13;5' — got {args.children!r}") from None
    alloc = None
    if args.alloc:
        try:
            alloc = {k.strip(): int(v) for k, v in (part.split(":") for part in args.alloc.split(","))}
        except ValueError:
            raise Refused(f"--alloc looks like 'STD:3,TPL:1' — got {args.alloc!r}") from None
    try:
        q = quoting.quote(quoting.parse_date(args.arrival), quoting.parse_date(args.departure), args.adults, kids,
                          rooms=args.rooms, room_type=args.room_type, alloc=alloc, twin=args.twin, indian=args.indian,
                          data=quoting.load_channel(args.channel))
    except quoting.QuoteError as e:
        raise Refused(str(e)) from None
    result = None
    if availability is not None:
        try:
            result = avail.check(availability, q["arrival"], q["departure"], _today_vn())
        except avail.AvailabilityError as e:
            q["gaps"] = [g for g in q["gaps"] if not g.startswith("availability")] + [str(e)]
        else:
            q["gaps"] = [g for g in q["gaps"] if not g.startswith("availability")]
    out(quoting.render(q))
    if result is not None:
        out("\n" + avail.render(availability, result))
        for label, o in q["options"]:
            problems = avail.fits(result, o["alloc"])
            if result["stop_sale"]:
                # rooms may be free, but the rule says the dates are not offered at all
                problems = [f"stop-sale on {', '.join(f'{n:%d/%m}' for n in result['stop_sale'])}"] + problems
            out(f"OPTION {label}: " + ("AVAILABLE" if not problems else "NOT AVAILABLE — " + "; ".join(problems)))
    q["availability"] = result
    return q


def run_cancel_fee(sheet, args, out=print, live=None):
    rows = [r for r in sheet.rows() if _parts(r.get("booking_ref")) & _parts(args.booking_ref)]
    if not rows:
        rows = [r for r in live_rows(live, out) if _parts(r.get("booking_ref")) & _parts(args.booking_ref)]
        if rows:
            out(f"booking found on the live sheet only (live rows {', '.join(str(r['_row']) for r in rows)})")
    if not rows:
        raise Refused(f"no rows for booking_ref {args.booking_ref!r} on the sheet")
    if args.cancelled_at:
        try:
            when = datetime.strptime(args.cancelled_at.strip(), "%d/%m/%Y %H:%M")
        except ValueError:
            raise Refused("--cancelled-at is 'DD/MM/YYYY HH:MM' Vietnam time, from the cancellation email") from None
    else:
        when = datetime.now(VN).replace(tzinfo=None)
    try:
        c = cancelling.cancel_fee(rows, when, no_show=args.no_show)
    except (cancelling.CancelFeeError, quoting.QuoteError) as e:
        raise Refused(str(e)) from None
    out(cancelling.render(c))
    return c


# --- confirmation PDF (job 2) ---

ROW_SUMMARY = ("booking_ref", "company", "guest_names", "arrival", "departure", "nights", "room_code", "rooms",
               "adults", "children", "rate_per_night_vnd", "Average rate per night after discount", "total_vnd")


def _row(sheet, row):
    r = next((x for x in sheet.rows() if x["_row"] == int(row)), None)
    if r is None:
        raise Refused(f"row {row} is empty or not a data row")
    return r


def pdf_fetch(sheet, row, work_dir=None, out=print):
    """Download the file behind pdf_link on one row; print it next to the row so they can be compared."""
    work_dir = work_dir or WORK_DIR
    r = _row(sheet, row)
    url = sheet.link_in_cell(int(row), "pdf_link")
    if not url:
        raise Refused(f"row {row} has no pdf_link: the booking isn't built yet, no confirmation (AGENTS.md rule 2)")
    fid = drive.file_id(url)
    if not fid:
        raise Refused(f"row {row}: pdf_link is not a Google Drive file link: {url}")
    name, mime, data = drive.download(sheet.call, fid)
    folder = os.path.join(work_dir, "confirmations")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, attachments.safe_name(f"{r.get('booking_ref') or 'row'}-row{row}-{name}"))
    with open(path, "wb") as f:
        f.write(data)
    out(f"saved: {os.path.abspath(path)} ({mime}, {len(data)} bytes)")
    out("row: " + json.dumps({k: r.get(k, "") for k in ROW_SUMMARY if r.get(k)}, ensure_ascii=False))
    out("file text (check every date, room, rate and total against the row):")
    out(attachments.clip(attachments.extract_text(path, data)))
    return path, name, mime, data


# What every confirmation must carry (skills/email-templates.md "Rules that apply to every email").
CONFIRMATION_MUST_HAVE = (
    ("1020729617", "the bank account number"),
    ("CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC", "the bank account name"),
    (("giờ Việt Nam", "Vietnam time"), "the deposit deadline in Vietnam time"),
    (("bao gồm ăn sáng", "including breakfast"), "the total's inclusion line"),
    # Sign-off as the sales mailbox writes it (dev, 2026-10-27; replaces Karen's "Best, / HAYA Team" of 08/10)
    ("Reservations Team", "the sign-off 'Trân trọng, / Best regards, + Reservations Team / HAYA Hotel Phu Quoc…'"),
)


def check_confirmation_text(body):
    missing = [what for needle, what in CONFIRMATION_MUST_HAVE
               if not any(n in body for n in (needle if isinstance(needle, tuple) else (needle,)))]
    if missing:
        raise Refused("the confirmation text doesn't follow skills/email-templates.md (section 1 for a new booking, "
                      f"2 for a change): missing {', '.join(missing)}. Rewrite it from the template; no draft made.")
    # Greeting says anh/chị (gender unknown): no lone "chị"/"anh" may be left from the template further down.
    if re.search(r"\banh\s*/\s*chị\b", body, re.I):
        lone = [line.strip() for line in body.splitlines()
                if re.search(r"(?<![/\w])(chị|anh)(?!\s*/)\b", re.sub(r"\banh\s*/\s*chị\b", "", line, flags=re.I),
                             re.I)]
        if lone:
            raise Refused("greeting is 'anh/chị' but these lines still say chị or anh alone — write Anh/Chị: "
                          + " | ".join(lone))


def check_operator_confirmation(body, ref="", group=""):
    """A tour operator's confirmation (tour-operators.md step 7): the group code and the operator's ref, the
    sign-off. No deposit or bank block: operators pay under their contract."""
    need = [("Reservations Team", "the sign-off 'Best regards, / Reservations Team / HAYA Hotel Phu Quoc…'")]
    if group:
        need.append((f"#{group.lstrip('#')}", f"the group code #{group.lstrip('#')}"))
    if ref:
        need.append((ref.split("/")[0].strip(), f"the operator's ref {ref.split('/')[0].strip()}"))
    missing = [what for needle, what in need if needle not in body]
    if missing:
        raise Refused("the confirmation text doesn't follow skills/email-templates.md section 6: missing "
                      f"{', '.join(missing)}. No draft made.")


def confirmation_check(row):
    """The text check for this row's confirmation: tour operator or agency/guest."""
    if row.get("channel_type") == "Tour operator":
        return lambda body: check_operator_confirmation(body, row.get("booking_ref", ""),
                                                        row.get("ezfolio_group_code", ""))
    return check_confirmation_text


def read_pdfs(paths):
    """[(name, bytes, 'application/pdf')] for --attach: our own invoice PDFs, never a confirmation Emi made."""
    files = []
    for p in paths or ():
        with open(p, "rb") as f:
            data = f.read()
        if not data.startswith(b"%PDF"):
            raise Refused(f"--attach {p} is not a PDF")
        files.append((os.path.basename(p), data, "application/pdf"))
    return files


def new_recipients(args):
    to, cc = _addresses(args.to), _addresses(args.cc)
    if not to:
        raise Refused("a new email needs --to (or the <to> argument)")
    ours = [a for a in to + cc if is_internal(a)]
    if ours:
        raise Refused(f"{', '.join(ours)} is our own address: a new email from Emi goes to the operator or agency")
    return to, cc


def draft_confirmation(mail, sheet, st, args, tg=None, out=print):
    """Reply on the sender's thread with the build tool's own PDF attached. Never a PDF Emi made.
    --subject: a new email instead of a reply (Odeon, tour-operators.md); --attach: our proforma invoice too."""
    r = _row(sheet, args.row)
    ref = r.get("booking_ref", "")
    if (ref, int(args.row)) in st.confirmation_drafted():
        raise Refused(f"{ref} row {args.row} already has a confirmation draft")
    body = read_text(args.body)
    check_no_gaps(body, args.message_id)
    confirmation_check(r)(body)
    company = r.get("company", "")
    subject, attach = getattr(args, "subject", ""), getattr(args, "attach", None) or []
    if company == "Odeon":
        odeon = operators.OPERATORS["Odeon"]
        missing = [a for a in odeon["confirm_to"] if a not in _addresses(args.to) + _addresses(args.cc)]
        if not subject or missing or not attach:
            raise Refused(f"Odeon's confirmation is a new email to {' and '.join(odeon['confirm_to'])} with both "
                          f"PDFs: --to {','.join(odeon['confirm_to'])} --subject "
                          f"\"{odeon['confirm_subject'].format(ref=ref.split('/')[0].strip())}\" "
                          f"--attach Invoice_<ref>.pdf (invoice-data {ref})")
    extra = read_pdfs(attach)
    _, name, mime, data = pdf_fetch(sheet, args.row, out=out)
    if mime != "application/pdf":
        raise Refused(f"pdf_link on row {args.row} is {mime}, not a PDF: the confirmation must be the PDF "
                      f"exported from EZFOLIO. No draft made.")
    files = [(name, data, "application/pdf")] + extra
    if subject:
        to, cc = new_recipients(args)
        how = "new"
    else:
        to, cc = reply_recipients(mail, args, "confirmation")
        args.all = reply_all_default(args, to)
        how = "reply"
    # kept on the review so a Rewrite is checked the same way
    meta = {"operator": company if r.get("channel_type") == "Tour operator" else "",
            "group": r.get("ezfolio_group_code", "")}
    if telegram_first(tg):
        n = review.propose(mail, st, tg, pending_store(), how=how, source=args.message_id, kind="confirmation",
                           ref=ref, row=int(args.row), text=body, reply_all=args.all, mailbox=config.MAILBOX,
                           to=to, cc=cc, files=files, new_subject=subject or "")
        st.data["reviews"][n].update(meta)
        st.record_draft(review.PENDING + n, ref, int(args.row), "confirmation")
        out(f"confirmation draft #{n} sent to Telegram for review with {len(files)} PDF(s), not in Outlook until "
            f"Accept: {review.PENDING}{n}")
        return {"id": review.PENDING + n}
    if how == "new":
        d = mail.create_new_draft(to, subject, body, cc=cc)
    else:
        d = mail.reply_draft_with_text(args.message_id, body, reply_all=args.all, to=to, cc=cc)
    for fname, fdata, ctype in files:
        mail.add_attachment(d["id"], fname, fdata, content_type=ctype)
    st.record_draft(d["id"], ref, int(args.row), "confirmation")
    n = review.opened(mail, st, tg, d["id"], how=how, source=args.message_id, kind="confirmation", ref=ref,
                      row=int(args.row), text=body, reply_all=args.all, to=to, cc=cc, override=bool(to),
                      attachments=[f[0] for f in files])
    st.data["reviews"][n].update(meta)
    out(f"confirmation draft #{n} saved in Drafts with {len(files)} PDF(s) attached: {d['id']}" + _to_line(to, cc))
    return d


def draft_new(mail, st, args, tg=None, out=print):
    """A new email, not a reply: Odeon's on-request decline goes to both Odeon addresses (tour-operators.md)."""
    if args.kind == "confirmation":
        raise Refused("a confirmation goes through draft-confirmation (it checks the EZFOLIO PDF): "
                      "draft-confirmation <message_id> <row> <body> --to … --subject … --attach …")
    text = read_text(args.body)
    check_no_gaps(text, args.message_id)
    to, cc = new_recipients(args)
    files = read_pdfs(args.attach)
    if telegram_first(tg):
        n = review.propose(mail, st, tg, pending_store(), how="new", source=args.message_id, kind=args.kind,
                           ref=args.ref, row=int(args.row or 0), text=text, to=to, cc=cc, files=files,
                           new_subject=args.subject)
        st.record_draft(review.PENDING + n, args.ref or "", int(args.row or 0), args.kind)
        out(f"new email draft #{n} sent to Telegram for review, not in Outlook until Accept: {review.PENDING}{n}"
            + _to_line(to, cc))
        return {"id": review.PENDING + n}
    d = mail.create_new_draft(to, args.subject, text, cc=cc)
    for fname, fdata, ctype in files:
        mail.add_attachment(d["id"], fname, fdata, content_type=ctype)
    _record(st, d, args)
    n = review.opened(mail, st, tg, d["id"], how="new", source=args.message_id, kind=args.kind, ref=args.ref,
                      row=int(args.row or 0), text=text, to=to, cc=cc, attachments=[f[0] for f in files])
    out(f"new email draft #{n} saved in Drafts: {d['id']}" + _to_line(to, cc))
    return d


# --- tour operators (skills/tour-operators.md) ---

def _ages(text):
    try:
        return [int(x) for x in re.split(r"[;,\s]+", text.strip()) if x] if text else []
    except ValueError:
        raise Refused(f"--children takes ages separated by ';', e.g. '7;1' — got {text!r}") from None


def to_price(args, out=print):
    try:
        q = op_rates.price(args.operator, op_rates.parse_date(args.arrival), op_rates.parse_date(args.departure),
                           args.room, args.adults, _ages(args.children), rooms=args.rooms, meal=args.meal,
                           booked=op_rates.parse_date(args.booked),
                           spo=re.split(r"[,;]", args.spo) if args.spo is not None else None)
    except op_rates.RateError as e:
        raise Refused(str(e)) from None
    out(op_rates.render(q))
    if not q["inside_release"]:
        out(f"\nAFTER RELEASE: treat it as on request — on-request --arrival {args.arrival} --departure "
            f"{args.departure} --alloc \"{args.room}:{args.rooms}\"")
    return q


def run_on_request(args, data, out=print):
    if not args.alloc:
        raise Refused("--alloc names the rooms asked for, e.g. 'DLX-SV:1'")
    result = run_availability(args, data, out=out)
    alloc = {k.strip(): int(v) for k, v in (part.split(":") for part in args.alloc.split(","))}
    verdict, why = operators.on_request(result, avail.fits(result, alloc), quoting.parse_date(args.arrival),
                                        _today_vn())
    out(f"\nON REQUEST: {verdict} — {'; '.join(why)}")
    if verdict == "REJECT":
        out(f"Next: CANCEL rows (status Cancelled, what_changed \"{operators.DECLINE_REASON}\"), then the decline "
            f"draft (email-templates.md section 6): Odeon -> draft-new to "
            f"{','.join(operators.OPERATORS['Odeon']['confirm_to'])} --kind decline; others -> draft-reply "
            f"--kind decline on the operator's email.")
    else:
        out("Next: no row yet. ask-karen <message_id> \"<booking, dates, rooms: can we accept it?>\" --ref <ref>, "
            "then done <message_id> \"waiting on Karen E-…\". Her yes -> NEW rows; her no -> the REJECT path.")
    return verdict


def _monday_last_week(today):
    return today - timedelta(days=today.weekday() + 7)


def run_checkouts(sheet, args, out=print):
    if args.last_week:
        first = _monday_last_week(_today_vn())
        last = first + timedelta(days=6)
    elif args.from_:
        first = quoting.parse_date(args.from_)
        last = quoting.parse_date(args.to) if args.to else first
    else:
        raise Refused("--from DD/MM/YYYY [--to DD/MM/YYYY], or --last-week (Monday to Sunday)")
    hits = operators.checkouts(sheet.rows(), booking_state, args.company, first, last)
    out(operators.render_checkouts(hits, args.company, first, last))
    return hits


def run_invoice_data(sheet, ref, out=print):
    state = booking_state(sheet.rows(), ref)
    if not state:
        raise Refused(f"no rows for booking_ref {ref!r} on the sheet")
    if operators.cancelled(state):
        raise Refused(f"{ref} is cancelled on the sheet: no invoice")
    try:
        d = operators.invoice_data(state)
    except KeyError as e:
        raise Refused(str(e).strip("'\"")) from None
    out(operators.render_invoice(d))
    return d


def run_review(mail, st, tg, args, out=print):
    """review-list / -info / -accept / -deny / -rewrite / -notify. State is saved even when one refuses,
    so a draft found gone from Outlook stays marked gone."""
    try:
        if args.cmd == "review-list":
            review.listing(mail, st, everything=args.all, out=out)
            return
        if args.cmd == "review-awaiting":
            review.awaiting(st, out=out)
            return
        n = _review_n(args.n)
        if args.cmd == "review-info":
            review.info(mail, st, n, out=out)
        elif args.cmd == "review-ask":
            review.ask(mail, st, tg, n, out=out)
        elif args.cmd == "review-accept":
            review.accept(mail, st, tg, n, by=args.by, out=out)
        elif args.cmd == "review-deny":
            review.deny(mail, st, tg, n, reason=args.reason, by=args.by, out=out)
        elif args.cmd == "review-rewrite":
            _, r = st.review(n)
            text = read_text(args.body)
            check_no_gaps(text, r.get("source") or "<message_id>")
            check = None
            if r["kind"] == "confirmation":
                check = (check_confirmation_text if not r.get("operator") else
                         lambda body: check_operator_confirmation(body, r.get("ref", ""), r.get("group", "")))
            review.rewrite(mail, st, tg, n, text, feedback=args.feedback, check=check, out=out)
        elif args.cmd == "review-notify":  # put the notice and its buttons back (Telegram down, buttons gone)
            n, r = st.review(n)
            if tg is None:
                raise Refused("Telegram is not set up: EMI_TELEGRAM_CHAT_ID and the bot token")
            if r["status"] != "pending":
                raise Refused(f"#{n} is already {r['status']}: no buttons to put back")
            out(f"notice for #{n} sent, buttons on" if review.notify(tg, n, r, in_place=True)
                else f"not sent: {r.get('tg_error', '?')}")
    except (review.ReviewError, KeyError, PermissionError) as e:
        raise Refused(str(e).strip("'\"")) from None
    finally:
        st.save()


# --- questions to Karen: a fact Emi doesn't have, so the email waits instead of getting a draft with a gap ---

def ask_karen(st, tg, message_id, question, ref="", out=print):
    question = " ".join(question.split())
    if not question:
        raise Refused("the question is empty")
    if GAP.search(question):
        raise Refused("write the question in words, not as a '[...: hotel to confirm]' gap")
    for qid, q in st.open_questions().items():
        if q.get("message_id") == message_id and q["ask"] == question:
            out(f"{qid} already asked for this email, still open: {question}")
            return qid
    qid = st.ask(ref, question, message_id)
    text = (f"❓ <b>{qid} — câu hỏi cho Karen</b>" + (f" · {review.esc(ref)}" if ref else "")
            + f"\n{review.esc(question)}\n\nTrả lời: <code>{qid} &lt;câu trả lời&gt;</code>. "
            f"Draft đã có dòng CHECK BEFORE SENDING; Emi sửa draft sau khi có câu trả lời.")
    sent = tg.send(text) if tg is not None else None
    out(f"{qid} asked" + (" on Telegram" if sent else " (Telegram off: put it in the scan report)")
        + f"; the draft for this email carries '[CHECK BEFORE SENDING: …]' until karen-answer {qid}")
    return qid


def karen_answer(st, qid, answer, out=print):
    qid = qid.strip().upper()
    if not answer.strip():
        raise Refused("the answer is empty")
    if qid not in st.data["questions"]:
        raise Refused(f"no question {qid}; open ones: {', '.join(st.open_questions()) or 'none'}")
    st.answer(f"{qid} {answer.strip()}")
    q = st.data["questions"][qid]
    waiting = [k for k, v in st.open_questions().items() if q.get("message_id") and v.get("message_id") == q["message_id"]]
    out(f"{qid} answered: {answer.strip()}")
    out(f"question was: {q['ask']}")
    if waiting:
        out(f"the same email still waits on {', '.join(waiting)}: keep the CHECK line")
    elif q.get("message_id"):
        out(f"every question for email {q['message_id']} is answered: rewrite its draft without the CHECK line "
            f"(review-rewrite <n>, or a new draft if none was made yet: show it, then "
            f"draft-reply / draft-forward). A lasting hotel fact also goes to MEMORY.md and the scan report.")
    return qid


def questions(st, everything=False, out=print):
    qs = st.data["questions"] if everything else st.open_questions()
    if not qs:
        out("no questions to Karen" + ("" if everything else " open"))
    for qid, q in qs.items():
        line = f"{qid} [{'answered' if q['answer'] is not None else 'open'}] {vn(q['asked_at'])}"
        line += f" · {q['booking_ref']}" if q.get("booking_ref") else ""
        line += f" · email {q['message_id']}" if q.get("message_id") else ""
        out(line)
        out(f"  Q: {q['ask']}")
        if q["answer"] is not None:
            out(f"  A: {q['answer']} ({vn(q['answered_at'])})")


def status(st, out=print):
    d = st.data
    out(f"last_scan: {d['last_scan']} ({vn(d['last_scan'])} Vietnam time)" if d["last_scan"] else "last_scan: never")
    out(f"processed emails remembered: {len(d['processed'])}")
    if os.environ.get("EMI_TEST_ONLY_FROM"):
        out(f"TEST MODE: inbox-new only reads mail from {os.environ['EMI_TEST_ONLY_FROM']}")
    out(f"drafts recorded: {len(d['drafts'])}, confirmations: {len(d['confirmations'])}, reminders: {len(d['reminders'])}")
    out(f"open questions to Karen: {len(st.open_questions())}")
    waiting = [n for n, r in d["reviews"].items() if r["status"] == "pending"]
    out(f"drafts waiting for review: {len(waiting)}" + (f" (#{', #'.join(waiting)})" if waiting else ""))
    out("telegram notices: " + ("on" if os.environ.get("EMI_TELEGRAM_CHAT_ID") else "off (EMI_TELEGRAM_CHAT_ID not set)"))
    out("draft mode: " + ("telegram (Outlook only on Accept)" if os.environ.get("EMI_DRAFT_MODE", "").lower() == "telegram"
                          else "outlook (saved in Drafts at once)"))


def _recipient_args(s):
    s.add_argument("--to", default="", help="comma-separated: reply to these instead of the email's sender, e.g. "
                                            "the real sender of a mail our staff forwarded in (quoted From: line)")
    s.add_argument("--cc", default="", help="comma-separated, with --to; e.g. the colleague who forwarded it")


def parser():
    p = argparse.ArgumentParser(prog="python -m tools.emi", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inbox-new")
    s = sub.add_parser("show"); s.add_argument("message_id")
    s = sub.add_parser("mail-find"); s.add_argument("text")
    s = sub.add_parser("sent-dump", help="HAYA's sent mail of the last N days to a text file (read-only)")
    s.add_argument("--days", type=int, default=14)
    s.add_argument("--out", default=os.path.join(WORK_DIR, "sent-dump.txt"))
    s = sub.add_parser("done"); s.add_argument("message_id"); s.add_argument("outcome", nargs="+")
    s = sub.add_parser("mark-scanned"); s.add_argument("scan_started")
    sub.add_parser("sheet-schema")
    sub.add_parser("sheet-access", help="which sheet Emi writes to and whether it may")
    s = sub.add_parser("sheet-template"); s.add_argument("action"); s.add_argument("file")
    s = sub.add_parser("sheet-check"); s.add_argument("file")
    s = sub.add_parser("sheet-find"); s.add_argument("text")
    sub.add_parser("direct-ref", help="next booking_ref for a direct guest: HAYA-D + number")
    s = sub.add_parser("sheet-rows", help="rows FIRST..LAST as they are on the sheet (read-only)")
    s.add_argument("first", type=int); s.add_argument("last", type=int, nargs="?")
    s = sub.add_parser("sheet-audit", help="check rows already on the sheet with the sheet-check rules")
    s.add_argument("--from-row", type=int, default=3)
    s = sub.add_parser("sheet-append"); s.add_argument("file")
    s = sub.add_parser("sheet-update"); s.add_argument("row", type=int); s.add_argument("file")
    for name in ("draft-reply", "draft-forward"):
        s = sub.add_parser(name)
        s.add_argument("message_id")
        if name == "draft-forward":
            s.add_argument("to", help="comma-separated addresses")
        s.add_argument("body", help="UTF-8 text file with the message")
        if name == "draft-reply":
            s.add_argument("--all", action="store_true", help="reply all (the default now; kept for old calls)")
            s.add_argument("--sender-only", action="store_true", help="reply to the sender alone, not reply all")
            _recipient_args(s)
            s.add_argument("--internal", action="store_true",
                           help="the reply really is for our own colleague (haya@, palmahotel.vn); kind reply only")
        s.add_argument("--kind", default="reply" if name == "draft-reply" else "forward",
                       help="reply, forward, confirmation, cancellation, deposit_reminder, balance_reminder, "
                            "inquiry, request")
        s.add_argument("--ref", default="")
        s.add_argument("--row", default="")
    s = sub.add_parser("draft-attach"); s.add_argument("draft_id"); s.add_argument("file")
    s = sub.add_parser("quote", help="price a stay and suggest rooms from the TA or direct-guest table")
    s.add_argument("--arrival", required=True, help="DD/MM/YYYY")
    s.add_argument("--departure", required=True, help="DD/MM/YYYY")
    s.add_argument("--adults", type=int, required=True)
    s.add_argument("--children", default="", help="ages separated by ';', e.g. '13;5;2'")
    s.add_argument("--rooms", type=int, help="number of rooms the sender asked for")
    s.add_argument("--room-type", help="room code the sender named, e.g. DLX-SV")
    s.add_argument("--alloc", help="price exactly this allocation, e.g. 'STD:3,TPL:1'")
    s.add_argument("--twin", action="store_true", help="two separate beds wanted")
    s.add_argument("--indian", action="store_true", help="Indian guests: +20%% on room rate")
    s.add_argument("--channel", default="TA", choices=["TA", "Tour operator", "OTA", "Direct"])
    s = sub.add_parser("availability", help="rooms free per room type for a stay (Future Availability sheet)")
    s.add_argument("--arrival", required=True, help="DD/MM/YYYY")
    s.add_argument("--departure", required=True, help="DD/MM/YYYY")
    s.add_argument("--alloc", help="check this allocation fits, e.g. 'STD:3,TPL:1'")
    sub.add_parser("stop-sales", help="room types with 1 room or fewer left per night: stop-sales email due")
    s = sub.add_parser("cancel-fee", help="TA cancellation charge for a booking on the sheet")
    s.add_argument("booking_ref")
    s.add_argument("--cancelled-at", help="'DD/MM/YYYY HH:MM' Vietnam time the cancellation email arrived (default now)")
    s.add_argument("--no-show", action="store_true")
    s = sub.add_parser("pdf-fetch"); s.add_argument("row", type=int)
    s = sub.add_parser("forget-confirmation"); s.add_argument("ref"); s.add_argument("row", type=int)
    s = sub.add_parser("draft-confirmation")
    s.add_argument("message_id"); s.add_argument("row", type=int); s.add_argument("body")
    s.add_argument("--all", action="store_true", help="reply all (the default now; kept for old calls)")
    s.add_argument("--sender-only", action="store_true", help="reply to the sender alone, not reply all")
    _recipient_args(s)
    s.add_argument("--subject", default="", help="a new email with this subject instead of a reply (Odeon)")
    s.add_argument("--attach", action="append", default=[], help="another PDF to attach, e.g. our proforma invoice")
    s = sub.add_parser("draft-new", help="a new email, not a reply (Odeon decline)")
    s.add_argument("message_id", help="the email this is about")
    s.add_argument("to", help="comma-separated addresses")
    s.add_argument("subject"); s.add_argument("body", help="UTF-8 text file with the message")
    s.add_argument("--cc", default="")
    s.add_argument("--kind", default="reply", help="decline, reply, forward …")
    s.add_argument("--ref", default=""); s.add_argument("--row", default="")
    s.add_argument("--attach", action="append", default=[], help="a PDF to attach")
    s = sub.add_parser("to-info", help="a tour operator's steps and what differs for it")
    s.add_argument("operator")
    s = sub.add_parser("to-price", help="price a tour operator booking from its own contract")
    s.add_argument("--operator", required=True, choices=sorted(op_rates.FILES) + sorted(op_rates.NO_CONTRACT))
    s.add_argument("--arrival", required=True, help="DD/MM/YYYY")
    s.add_argument("--departure", required=True, help="DD/MM/YYYY")
    s.add_argument("--room", required=True, help="room code, e.g. DLX-SV")
    s.add_argument("--rooms", type=int, default=1)
    s.add_argument("--adults", type=int, required=True, help="per room")
    s.add_argument("--children", default="", help="ages per room separated by ';', e.g. '7;1'")
    s.add_argument("--meal", default="BB", help="BB, HB or FB")
    s.add_argument("--booked", required=True, help="DD/MM/YYYY the operator made the booking (voucher date)")
    s.add_argument("--spo", help="Odeon: the voucher's SPO code(s), e.g. 'EB,FS001', 'SCO', or 'none'")
    s = sub.add_parser("on-request", help="tour operator on-request booking: reject or ask Karen")
    s.add_argument("--arrival", required=True, help="DD/MM/YYYY")
    s.add_argument("--departure", required=True, help="DD/MM/YYYY")
    s.add_argument("--alloc", required=True, help="rooms asked for, e.g. 'DLX-SV:1,STD:2'")
    s = sub.add_parser("checkouts", help="an operator's bookings checking out in a date range (not cancelled)")
    s.add_argument("--company", required=True, help="as in the sheet's company column, e.g. Anex")
    s.add_argument("--from", dest="from_", help="DD/MM/YYYY")
    s.add_argument("--to", help="DD/MM/YYYY, default = --from")
    s.add_argument("--last-week", action="store_true", help="last Monday to Sunday")
    s = sub.add_parser("invoice-data", help="proforma invoice figures for a tour operator booking")
    s.add_argument("booking_ref")
    s = sub.add_parser("ask-karen", help="a fact for the reply is uncertain: ask Karen; the draft has a CHECK line")
    s.add_argument("message_id"); s.add_argument("question", nargs="+"); s.add_argument("--ref", default="")
    s = sub.add_parser("karen-answer", help="record Karen's answer to E-001; then write the waiting draft")
    s.add_argument("qid"); s.add_argument("answer", nargs="+")
    s = sub.add_parser("questions", help="questions to Karen still open")
    s.add_argument("--all", action="store_true", help="also the answered ones")
    sub.add_parser("status")
    s = sub.add_parser("review-list", help="drafts waiting for a person's accept / deny / rewrite")
    s.add_argument("--all", action="store_true", help="also the ones already decided")
    sub.add_parser("review-awaiting", help="which draft the reviewer's next message is feedback for")
    for name in ("review-info", "review-ask", "review-accept", "review-deny", "review-rewrite", "review-notify"):
        s = sub.add_parser(name); s.add_argument("n", help="draft number, e.g. 12 or #12")
        if name == "review-deny":
            s.add_argument("--reason", default="")
        if name == "review-rewrite":
            s.add_argument("body", help="UTF-8 text file with the whole new text")
            s.add_argument("--feedback", default="", help="the reviewer's words, as given")
        if name in ("review-accept", "review-deny"):
            s.add_argument("--by", default="", help="who decided, e.g. the Telegram name")
    s = sub.add_parser("sim-reset", help="fresh copy of a test scenario + remove its old TEST rows")
    s.add_argument("scenario")
    s = sub.add_parser("sim-check", help="grade the sheet and drafts after a simulated run")
    s.add_argument("scenario")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        st = config.state()
        c = args.cmd
        if c == "inbox-new":
            inbox_new(config.mail(), st)
        elif c == "show":
            show(config.mail(), args.message_id)
        elif c == "mail-find":
            mail_find(config.mail(), args.text)
        elif c == "sent-dump":
            sent_dump(config.mail(), args.days, args.out)
        elif c == "done":
            st.mark_processed(args.message_id, " ".join(args.outcome))
            st.save()
            print("marked handled")
        elif c == "mark-scanned":
            datetime.strptime(args.scan_started, "%Y-%m-%dT%H:%M:%SZ")  # the scan_started= value, nothing else
            st.mark_scanned(args.scan_started)
            st.save()
            print(f"last_scan = {args.scan_started}")
        elif c == "sheet-schema":
            sheet_schema(config.sheet())
        elif c == "sheet-access":
            s = config.sheet()
            name, ok = s.can_edit()
            print(f"Emi writes to: {name} ({config.SHEET_ID}, tab {config.SHEET_TAB}), {len(s.header)} columns, "
                  + ("edit access OK" if ok else "NO edit access: share it with the service account as Editor"))
        elif c == "sheet-template":
            sheet_template(config.sheet(), args.action, args.file)
        elif c == "sheet-check":
            sheet_check(config.sheet(), read_json(args.file))
        elif c == "sheet-find":
            sheet_find(config.sheet(), args.text, live=config.live_sheet())
        elif c == "direct-ref":
            direct_ref(config.sheet(), live=config.live_sheet())
        elif c == "sheet-rows":
            sheet_rows(config.sheet(), args.first, args.last)
        elif c == "sheet-audit":
            sheet_audit(config.sheet(), args.from_row)
        elif c == "sheet-append":
            sheet_append(config.sheet(), read_json(args.file), live=config.live_sheet())
        elif c == "sheet-update":
            sheet_update(config.sheet(), args.row, read_json(args.file), work_dir=WORK_DIR)
        elif c == "draft-reply":
            draft_reply(config.mail(), st, args, tg=config.telegram())
            st.save()
        elif c == "draft-forward":
            draft_forward(config.mail(), st, args, tg=config.telegram())
            st.save()
        elif c.startswith("review-"):
            run_review(config.mail(), st, config.telegram(), args)
        elif c == "forget-confirmation":
            if not st.forget_confirmation(args.ref, args.row):
                raise Refused(f"no confirmation draft recorded for {args.ref} row {args.row}")
            st.save()
            print(f"forgot the confirmation draft for {args.ref} row {args.row}; delete the draft itself in Outlook")
        elif c == "quote":
            run_quote(args, availability=load_availability())
        elif c == "availability":
            data = load_availability()
            if data is None:
                # audit 30/10 (F-02): an unreadable sheet is a gap, not a failed run — the row is still written
                print(AVAILABILITY_GAP_NEXT)
                return 0
            run_availability(args, data)
        elif c == "stop-sales":
            data = load_availability()
            if data is None:
                print("STOP SALES NOT CHECKED: one line in the report; carry on with the run")
                return 0
            run_stop_sales(data)
        elif c == "cancel-fee":
            run_cancel_fee(config.sheet(), args, live=config.live_sheet())
        elif c == "pdf-fetch":
            pdf_fetch(config.sheet(), args.row)
        elif c == "draft-confirmation":
            draft_confirmation(config.mail(), config.sheet(), st, args, tg=config.telegram())
            st.save()
        elif c == "draft-new":
            draft_new(config.mail(), st, args, tg=config.telegram())
            st.save()
        elif c == "to-info":
            try:
                print(operators.info(args.operator))
            except KeyError as e:
                raise Refused(str(e).strip("'\"")) from None
        elif c == "to-price":
            to_price(args)
        elif c == "on-request":
            data = load_availability()
            if data is None:
                print("ON REQUEST: can't decide without the availability sheet — ask Karen")
                return 2
            run_on_request(args, data)
        elif c == "checkouts":
            run_checkouts(config.sheet(), args)
        elif c == "invoice-data":
            run_invoice_data(config.sheet(), args.booking_ref)
        elif c == "draft-attach":
            draft_attach(config.mail(), st, args.draft_id, args.file)
            st.save()
        elif c == "sim-reset":
            sim.reset(config.sheet(), args.scenario, WORK_DIR)
        elif c == "sim-check":
            if not sim.check(config.sheet(), args.scenario, WORK_DIR):
                return 2
        elif c == "ask-karen":
            ask_karen(st, config.telegram(), args.message_id, " ".join(args.question), ref=args.ref)
            st.save()
        elif c == "karen-answer":
            karen_answer(st, args.qid, " ".join(args.answer))
            st.save()
        elif c == "questions":
            questions(st, everything=args.all)
        elif c == "status":
            status(st)
    except Exception as e:
        print(f"ERROR ({args.cmd}): {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
