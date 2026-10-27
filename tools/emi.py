"""The commands Emi's scheduled jobs call. One fixed command per step, so the agent never has
to write its own Python to reach the mailbox or the sheet (schedule.md says which job uses which).

    python -m tools.emi inbox-new                         # emails since the last scan, not yet handled
    python -m tools.emi show <message_id>                 # whole thread + attachments saved and read
    python -m tools.emi mail-find <text>                  # emails matching text (ref, subject, sender): their ids
    python -m tools.emi done <message_id> <outcome>       # mark one email handled
    python -m tools.emi mark-scanned <scan_started>       # end of job 1: move the scan clock
    python -m tools.emi sheet-schema                      # every column: level, required, allowed values, sheet instruction
    python -m tools.emi sheet-template <NEW|CHANGE|CANCEL> <file.json>  # empty booking JSON to fill
    python -m tools.emi sheet-check <booking.json>        # check a filled booking without writing
    python -m tools.emi sheet-find <text>                 # rows whose booking_ref or guest_names contain text
    python -m tools.emi sheet-rows <first> [<last>]       # rows as they are on the sheet, filled cells only
    python -m tools.emi sheet-audit [--from-row N]        # rows already on the sheet that break the sheet-check rules
    python -m tools.emi sheet-append <booking.json>       # new booking: {"booking": {...}, "room_lines": [{...}, ...]}
    python -m tools.emi sheet-update <row> <fields.json>  # change named cells on one row
    python -m tools.emi draft-reply <message_id> <body.txt> [--all | --to A[,B] [--cc C]] [--kind K --ref R --row N]
    python -m tools.emi draft-forward <message_id> <to> <body.txt> [--kind K --ref R --row N]
    python -m tools.emi draft-attach <draft_id> <file>
    python -m tools.emi forget-confirmation <ref> <row>   # only after a person deleted that confirmation draft
    python -m tools.emi quote --arrival DD/MM/YYYY --departure DD/MM/YYYY --adults N [--children "13;5"] [--rooms N] [--room-type X] [--alloc "STD:3,TPL:1"] [--twin] [--indian] [--channel TA|Direct]
    python -m tools.emi cancel-fee <booking_ref> [--cancelled-at "DD/MM/YYYY HH:MM"] [--no-show]  # TA cancellation charge
    python -m tools.emi pdf-fetch <row>                   # download the file behind pdf_link, print it next to the row
    python -m tools.emi draft-confirmation <message_id> <row> <body.txt> [--all | --to A [--cc C]]  # reply + EZFOLIO PDF
    python -m tools.emi ask-karen <message_id> "<question>" [--ref R]  # a fact is missing: ask, no draft yet
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
A draft is written only with every fact in it: a text with a '[...: hotel to confirm]' gap is refused, and the
missing fact goes to Karen with ask-karen instead (dev, 2026-10-22).

A reply goes to whoever sent the email. When that is our own staff (haya@haya-hotels.com forwarding a guest's or
agency's mail into sales@), draft-reply refuses: reply to the real sender, the From: in the quoted header, with
--to <address> (--cc haya@haya-hotels.com so front office sees the answer). draft-forward refuses to send an
email back to the colleague who forwarded it to us.
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
from . import availability as avail
from . import review, sim
from . import intake_schema as schema
from .state import now_iso

VN = timezone(timedelta(hours=7))
WORK_DIR = os.environ.get("EMI_WORK_DIR", "emi-work")
FIRST_SCAN_LOOKBACK = timedelta(hours=24)   # inbox-triage.md: no last scan -> the last 24 hours


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
    msgs = [m for m in mail.list_inbox_since(since) if not st.is_processed(m["id"])]
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

def sheet_find(sheet, text, out=print):
    t = text.strip().lower()
    hits = [r for r in sheet.rows()
            if t in r.get("booking_ref", "").lower() or t in r.get("guest_names", "").lower()]
    out(f"rows found: {len(hits)}")
    for r in hits:
        out(json.dumps({k: v for k, v in r.items() if v}, ensure_ascii=False))
    return hits


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


def check_rows(sheet, records):
    """Check every row against tools/intake_schema.py; all problems at once, so one fix covers them."""
    codes = schema.room_codes(sheet)
    errors, warnings = [], []
    for i, rec in enumerate(records, 1):
        unknown = sorted(set(rec) - set(sheet.header) - {"_row"})
        label = f"row {i} ({rec.get('room_code') or 'no room_code'})"
        if unknown:
            errors.append(f"{label}: not sheet columns {unknown} — run sheet-schema for the exact names")
        e, w = schema.check_row(rec, codes)
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
    return {p.lower() for p in schema.ref_parts(ref or "")}


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
        if filled:
            out(f"{rec['action']} {rec.get('room_code') or ''}: blanks copied from row {src['_row']}: "
                f"{', '.join(filled)}")
    return records


def sheet_append(sheet, data, out=print):
    records = expand_booking(data)
    if not records:
        raise Refused("no rows given")
    rows = None
    cancelled_here = {p for rec in records if rec.get("action") == "CANCEL" for p in _parts(rec.get("booking_ref"))}
    for rec in records:
        ref = str(rec.get("booking_ref", "")).strip()
        if not ref:
            continue
        if rows is None:
            rows = sheet.rows()
        state = booking_state(rows, ref)
        if rec.get("action") == "NEW" and state:
            # Rules tab: a CHANGE or CANCEL is a new row with the same booking_ref; only NEW must be unique.
            # Except a cancel-and-rebuild (GD0512, 26/10): CANCEL rows and NEW rows from the same email.
            rebuild = bool(_parts(ref) & cancelled_here) or (
                state[0].get("action") == "CANCEL" and state[0].get("received_at") == rec.get("received_at"))
            if not rebuild:
                hit = next(r for r in rows if _parts(r.get("booking_ref")) & _parts(ref))
                raise Refused(f"booking_ref {ref!r}: {', '.join(sorted(_parts(hit['booking_ref']) & _parts(ref)))} "
                              f"is already on the sheet (row {hit['_row']}): this is not a NEW booking. Use action "
                              f"CHANGE (new rows, what_changed filled), or sheet-update row {hit['_row']} to add "
                              f"the other number. A cancel-and-rebuild: the CANCEL rows and the NEW rows in one file")
        if rec.get("action") == "CANCEL" and state and state[0].get("action") == "CANCEL":
            # 2026-10-27: operators' cancel notices for bookings already closed as declined on request
            raise Refused(f"booking_ref {ref!r} is already cancelled (row {state[0]['_row']}, "
                          f"{state[0].get('received_at', '')}): no second CANCEL row; mark the email done")
    if rows is not None and any(r.get("action") in ("CHANGE", "CANCEL") for r in records):
        records = carry_over(records, booking_state(rows, records[0].get("booking_ref")), out=out)
    sheet_check(sheet, records, out=out)
    sheet.append_rows(records)
    out(f"appended {len(records)} row(s). Check them below; fix a wrong cell with sheet-update <row> by column name.")
    for ref in dict.fromkeys(rec["booking_ref"] for rec in records if rec.get("booking_ref")):
        for r in sheet.find_by_ref(ref):
            out(f"row {r['_row']}: " + json.dumps({k: v for k, v in r.items() if v and k != "_row"},
                                                  ensure_ascii=False))


def sheet_update(sheet, row, fields, out=print):
    """Correct a cell on a row not yet built. News about the booking (a payment, a pick-up, a name) is a
    CHANGE row instead: each row is the record of one email (live sheet 2026-10-27)."""
    if not fields:
        raise Refused("no fields given")
    current = next((r for r in sheet.rows() if r["_row"] == int(row)), None)
    if current is None:
        raise Refused(f"row {row} is empty or not a data row")
    pay = sorted(set(fields) & {"Payment 1", "Payment 1 date + time", "Payment 2", "Payment 2 date + time"})
    if pay:
        raise Refused(f"{pay}: a payment is a CHANGE row (sheet-template CHANGE, what_changed 'Payment 1 "
                      f"received …'), not an edit of row {row}")
    if current.get("tracy_status") in ("Entered", "Problem"):
        raise Refused(f"row {row} is already built in EZFOLIO ({current['tracy_status']}): write a CHANGE row, "
                      f"or report the wrong cell to Karen")
    merged = {k: v for k, v in {**current, **fields}.items() if k != "_row"}
    errors, warnings = check_rows(sheet, [merged])
    for w in warnings:
        out(f"WARNING {w}")
    if errors:
        raise Refused(f"row {row} would not pass the checks after this update:\n  " + "\n  ".join(errors))
    sheet.update_cells(int(row), fields)
    out(f"updated row {row}: {sorted(fields)}")


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
GUEST_KINDS = ("request", "inquiry", "confirmation", "deposit_reminder", "balance_reminder")

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
    if is_internal(sender) and not internal:
        raise Refused(FORWARDED_IN.format(sender=sender))
    return None, None


def _to_line(to, cc):
    if not to:
        return ""
    return f" (to {', '.join(to)}" + (f", cc {', '.join(cc)}" if cc else "") + ")"


# '[Indoor or outdoor: hotel to confirm]', '[giá đưa đón: khách sạn xác nhận]': a fact Emi doesn't have.
GAP = re.compile(r"\[[^\]\n]*(?:to confirm|xác nhận)[^\]\n]*\]", re.I)


def check_no_gaps(text, message_id="<message_id>"):
    """Only a complete email becomes a draft (dev, 2026-10-22: a draft with '[Indoor or outdoor: hotel to
    confirm]' reached Telegram). A fact Emi doesn't have goes to Karen as a question; the draft waits."""
    gaps = list(dict.fromkeys(GAP.findall(text)))
    if gaps:
        raise Refused(f"the text still has {len(gaps)} gap(s): {' | '.join(gaps)}. No draft is written with a "
                      f"missing fact. Ask Karen: ask-karen {message_id} \"<the missing fact, as a question>\" "
                      f"--ref <ref>, then done {message_id} \"waiting on Karen E-...\". Write the draft after "
                      f"karen-answer.")


def draft_reply(mail, st, args, tg=None, out=print):
    if args.kind == "confirmation" and not (args.ref and args.row):
        raise Refused("a confirmation draft needs --ref and --row")
    text = read_text(args.body)
    check_no_gaps(text, args.message_id)
    to, cc = reply_recipients(mail, args, args.kind)
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


def draft_forward(mail, st, args, tg=None, out=print):
    to = _addresses(args.to)
    text = read_text(args.body)
    check_no_gaps(text, args.message_id)
    sender = _sender_of(mail, args.message_id)
    if is_internal(sender) and sender.lower() in [a.lower() for a in to]:
        raise Refused(f"{sender} forwarded this email to us: it already has it. Don't forward it back. Answer the "
                      f"guest or agency with draft-reply --to <the quoted From: address> --cc {sender}")
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
    "Tour operator": "quote from that operator's own contract in docs/rate-knowledge/<name>.md (anex, crystalbay, "
                     "odeon, pegas, selfie); Fun and Sun has no contract — Karen",
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


def run_cancel_fee(sheet, args, out=print):
    rows = sheet.find_by_ref(args.booking_ref)
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


def draft_confirmation(mail, sheet, st, args, tg=None, out=print):
    """Reply on the sender's thread with the build tool's own PDF attached. Never a PDF Emi made."""
    r = _row(sheet, args.row)
    ref = r.get("booking_ref", "")
    if (ref, int(args.row)) in st.confirmation_drafted():
        raise Refused(f"{ref} row {args.row} already has a confirmation draft")
    body = read_text(args.body)
    check_no_gaps(body, args.message_id)
    check_confirmation_text(body)
    _, name, mime, data = pdf_fetch(sheet, args.row, out=out)
    if mime != "application/pdf":
        raise Refused(f"pdf_link on row {args.row} is {mime}, not a PDF: the confirmation must be the PDF "
                      f"exported from EZFOLIO. No draft made.")
    to, cc = reply_recipients(mail, args, "confirmation")
    if telegram_first(tg):
        n = review.propose(mail, st, tg, pending_store(), how="reply", source=args.message_id, kind="confirmation",
                           ref=ref, row=int(args.row), text=body, reply_all=args.all, mailbox=config.MAILBOX,
                           to=to, cc=cc, files=[(name, data, "application/pdf")])
        st.record_draft(review.PENDING + n, ref, int(args.row), "confirmation")
        out(f"confirmation draft #{n} sent to Telegram for review with the PDF, not in Outlook until Accept: "
            f"{review.PENDING}{n}")
        return {"id": review.PENDING + n}
    d = mail.reply_draft_with_text(args.message_id, body, reply_all=args.all, to=to, cc=cc)
    mail.add_attachment(d["id"], name, data, content_type="application/pdf")
    st.record_draft(d["id"], ref, int(args.row), "confirmation")
    n = review.opened(mail, st, tg, d["id"], how="reply", source=args.message_id, kind="confirmation", ref=ref,
                      row=int(args.row), text=body, reply_all=args.all, to=to, cc=cc, override=bool(to),
                      attachments=[name])
    out(f"confirmation draft #{n} saved in Drafts with the PDF attached: {d['id']}" + _to_line(to, cc))
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
            check = check_confirmation_text if r["kind"] == "confirmation" else None
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
            f"Emi soạn thư sau khi có câu trả lời.")
    sent = tg.send(text) if tg is not None else None
    out(f"{qid} asked" + (" on Telegram" if sent else " (Telegram off: put it in the scan report)")
        + f"; no draft for this email until karen-answer {qid}")
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
        out(f"the same email still waits on {', '.join(waiting)}: no draft yet")
    elif q.get("message_id"):
        out(f"every question for email {q['message_id']} is answered: write its draft now (show it, then "
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
    s = sub.add_parser("sheet-template"); s.add_argument("action"); s.add_argument("file")
    s = sub.add_parser("sheet-check"); s.add_argument("file")
    s = sub.add_parser("sheet-find"); s.add_argument("text")
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
            s.add_argument("--all", action="store_true", help="reply all")
            _recipient_args(s)
            s.add_argument("--internal", action="store_true",
                           help="the reply really is for our own colleague (haya@, palmahotel.vn); kind reply only")
        s.add_argument("--kind", default="reply" if name == "draft-reply" else "forward",
                       help="reply, forward, confirmation, deposit_reminder, balance_reminder, inquiry, request")
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
    s = sub.add_parser("cancel-fee", help="TA cancellation charge for a booking on the sheet")
    s.add_argument("booking_ref")
    s.add_argument("--cancelled-at", help="'DD/MM/YYYY HH:MM' Vietnam time the cancellation email arrived (default now)")
    s.add_argument("--no-show", action="store_true")
    s = sub.add_parser("pdf-fetch"); s.add_argument("row", type=int)
    s = sub.add_parser("forget-confirmation"); s.add_argument("ref"); s.add_argument("row", type=int)
    s = sub.add_parser("draft-confirmation")
    s.add_argument("message_id"); s.add_argument("row", type=int); s.add_argument("body")
    s.add_argument("--all", action="store_true", help="reply all")
    _recipient_args(s)
    s = sub.add_parser("ask-karen", help="a fact for the reply is missing: ask Karen, write no draft yet")
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
        elif c == "sheet-template":
            sheet_template(config.sheet(), args.action, args.file)
        elif c == "sheet-check":
            sheet_check(config.sheet(), read_json(args.file))
        elif c == "sheet-find":
            sheet_find(config.sheet(), args.text)
        elif c == "sheet-rows":
            sheet_rows(config.sheet(), args.first, args.last)
        elif c == "sheet-audit":
            sheet_audit(config.sheet(), args.from_row)
        elif c == "sheet-append":
            sheet_append(config.sheet(), read_json(args.file))
        elif c == "sheet-update":
            sheet_update(config.sheet(), args.row, read_json(args.file))
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
                return 2
            run_availability(args, data)
        elif c == "cancel-fee":
            run_cancel_fee(config.sheet(), args)
        elif c == "pdf-fetch":
            pdf_fetch(config.sheet(), args.row)
        elif c == "draft-confirmation":
            draft_confirmation(config.mail(), config.sheet(), st, args, tg=config.telegram())
            st.save()
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
