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
    python -m tools.emi sheet-append <booking.json>       # new booking: {"booking": {...}, "room_lines": [{...}, ...]}
    python -m tools.emi sheet-update <row> <fields.json>  # change named cells on one row
    python -m tools.emi draft-reply <message_id> <body.txt> [--all] [--kind K --ref R --row N]
    python -m tools.emi draft-forward <message_id> <to> <body.txt> [--kind K --ref R --row N]
    python -m tools.emi draft-attach <draft_id> <file>
    python -m tools.emi forget-confirmation <ref> <row>   # only after a person deleted that confirmation draft
    python -m tools.emi quote --arrival DD/MM/YYYY --departure DD/MM/YYYY --adults N [--children "13;5"] [--rooms N] [--room-type X] [--alloc "STD:3,TPL:1"] [--twin] [--indian] [--channel TA|Direct]
    python -m tools.emi cancel-fee <booking_ref> [--cancelled-at "DD/MM/YYYY HH:MM"] [--no-show]  # TA cancellation charge
    python -m tools.emi pdf-fetch <row>                   # download the file behind pdf_link, print it next to the row
    python -m tools.emi draft-confirmation <message_id> <row> <body.txt> [--all]  # reply draft + the EZFOLIO PDF
    python -m tools.emi status                            # scan clock and counts
    python -m tools.emi sim-reset <scenario>              # test/sim/<scenario>: fresh test inbox, old TEST rows removed
    python -m tools.emi sim-check <scenario>              # grade sheet + drafts after a run with EMI_SIM_DIR set

Every draft stays in Drafts with the Emi category. Nothing here can send (graph_mail refuses).
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
from . import quote as quoting
from . import cancel_fee as cancelling
from . import sim
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


def sheet_append(sheet, data, out=print):
    records = expand_booking(data)
    if not records:
        raise Refused("no rows given")
    for rec in records:
        ref = str(rec.get("booking_ref", "")).strip().lower()
        # Rules tab: a CHANGE or CANCEL is a new row with the same booking_ref; only NEW must be unique.
        if ref and rec.get("action") == "NEW" and sheet.find_by_ref(ref):
            raise Refused(f"booking_ref {rec['booking_ref']!r} is already on the sheet: this is not a NEW "
                          f"booking. Use action CHANGE (new rows, what_changed filled) or sheet-update for a fix")
    sheet_check(sheet, records, out=out)
    sheet.append_rows(records)
    out(f"appended {len(records)} row(s). Check them below; fix a wrong cell with sheet-update <row> by column name.")
    for ref in dict.fromkeys(rec["booking_ref"] for rec in records if rec.get("booking_ref")):
        for r in sheet.find_by_ref(ref):
            out(f"row {r['_row']}: " + json.dumps({k: v for k, v in r.items() if v and k != "_row"},
                                                  ensure_ascii=False))


def sheet_update(sheet, row, fields, out=print):
    if not fields:
        raise Refused("no fields given")
    current = next((r for r in sheet.rows() if r["_row"] == int(row)), None)
    if current is None:
        raise Refused(f"row {row} is empty or not a data row")
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
    out("\nROOM CODES (room_code). Match the name in the email against the 'agencies call it' name:")
    for code, (name, note) in codes.items():
        alias = f" — agencies call it \"{ta_names[code]}\"" if code in ta_names else ""
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


def draft_reply(mail, st, args, out=print):
    if args.kind == "confirmation" and not (args.ref and args.row):
        raise Refused("a confirmation draft needs --ref and --row")
    d = mail.reply_draft_with_text(args.message_id, read_text(args.body), reply_all=args.all)
    _record(st, d, args)
    out(f"draft saved in Drafts: {d['id']}")
    return d


def draft_forward(mail, st, args, out=print):
    to = [a.strip() for a in args.to.split(",") if a.strip()]
    d = mail.forward_draft_with_text(args.message_id, to, read_text(args.body))
    _record(st, d, args)
    out(f"forward draft saved in Drafts: {d['id']} (to {', '.join(to)})")
    return d


def draft_attach(mail, draft_id, path, out=print):
    with open(path, "rb") as f:
        data = f.read()
    ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
    mail.add_attachment(draft_id, os.path.basename(path), data, content_type=ctype)
    out(f"attached {os.path.basename(path)} to {draft_id}")


# --- inquiries (no booking yet) ---

OTHER_CHANNELS = {
    "Tour operator": "quote from that operator's own contract in docs/rate-knowledge/<name>.md (anex, crystalbay, "
                     "odeon, pegas, selfie); Fun and Sun has no contract — Karen",
    "OTA": "OTAs book through their own systems; an OTA inquiry by email goes to Karen",
}


def run_quote(args, out=print):
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
    out(quoting.render(q))
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


# What every confirmation must carry (skills/email-templates.md "Rules that apply to all of them").
CONFIRMATION_MUST_HAVE = (
    ("1020729617", "the bank account number"),
    ("CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC", "the bank account name"),
    (("giờ Việt Nam", "Vietnam time"), "the deposit deadline in Vietnam time"),
    (("bao gồm ăn sáng, VAT và phí dịch vụ", "including breakfast, VAT and service charge"), "the total's inclusion line"),
    ("HAYA Team", "the sign-off 'Best, / HAYA Team'"),
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


def draft_confirmation(mail, sheet, st, args, out=print):
    """Reply on the sender's thread with the build tool's own PDF attached. Never a PDF Emi made."""
    r = _row(sheet, args.row)
    ref = r.get("booking_ref", "")
    if (ref, int(args.row)) in st.confirmation_drafted():
        raise Refused(f"{ref} row {args.row} already has a confirmation draft")
    body = read_text(args.body)
    check_confirmation_text(body)
    _, name, mime, data = pdf_fetch(sheet, args.row, out=out)
    if mime != "application/pdf":
        raise Refused(f"pdf_link on row {args.row} is {mime}, not a PDF: the confirmation must be the PDF "
                      f"exported from EZFOLIO. No draft made.")
    d = mail.reply_draft_with_text(args.message_id, body, reply_all=args.all)
    mail.add_attachment(d["id"], name, data, content_type="application/pdf")
    st.record_draft(d["id"], ref, int(args.row), "confirmation")
    out(f"confirmation draft saved in Drafts with the PDF attached: {d['id']}")
    return d


def status(st, out=print):
    d = st.data
    out(f"last_scan: {d['last_scan']} ({vn(d['last_scan'])} Vietnam time)" if d["last_scan"] else "last_scan: never")
    out(f"processed emails remembered: {len(d['processed'])}")
    if os.environ.get("EMI_TEST_ONLY_FROM"):
        out(f"TEST MODE: inbox-new only reads mail from {os.environ['EMI_TEST_ONLY_FROM']}")
    out(f"drafts recorded: {len(d['drafts'])}, confirmations: {len(d['confirmations'])}, reminders: {len(d['reminders'])}")
    out(f"open questions to Karen: {len(st.open_questions())}")


def parser():
    p = argparse.ArgumentParser(prog="python -m tools.emi", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inbox-new")
    s = sub.add_parser("show"); s.add_argument("message_id")
    s = sub.add_parser("mail-find"); s.add_argument("text")
    s = sub.add_parser("done"); s.add_argument("message_id"); s.add_argument("outcome", nargs="+")
    s = sub.add_parser("mark-scanned"); s.add_argument("scan_started")
    sub.add_parser("sheet-schema")
    s = sub.add_parser("sheet-template"); s.add_argument("action"); s.add_argument("file")
    s = sub.add_parser("sheet-check"); s.add_argument("file")
    s = sub.add_parser("sheet-find"); s.add_argument("text")
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
        s.add_argument("--kind", default="reply" if name == "draft-reply" else "forward",
                       help="reply, forward, confirmation, deposit_reminder, balance_reminder, inquiry")
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
    s = sub.add_parser("cancel-fee", help="TA cancellation charge for a booking on the sheet")
    s.add_argument("booking_ref")
    s.add_argument("--cancelled-at", help="'DD/MM/YYYY HH:MM' Vietnam time the cancellation email arrived (default now)")
    s.add_argument("--no-show", action="store_true")
    s = sub.add_parser("pdf-fetch"); s.add_argument("row", type=int)
    s = sub.add_parser("forget-confirmation"); s.add_argument("ref"); s.add_argument("row", type=int)
    s = sub.add_parser("draft-confirmation")
    s.add_argument("message_id"); s.add_argument("row", type=int); s.add_argument("body")
    s.add_argument("--all", action="store_true", help="reply all")
    sub.add_parser("status")
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
        elif c == "sheet-append":
            sheet_append(config.sheet(), read_json(args.file))
        elif c == "sheet-update":
            sheet_update(config.sheet(), args.row, read_json(args.file))
        elif c == "draft-reply":
            draft_reply(config.mail(), st, args)
            st.save()
        elif c == "draft-forward":
            draft_forward(config.mail(), st, args)
            st.save()
        elif c == "forget-confirmation":
            if not st.forget_confirmation(args.ref, args.row):
                raise Refused(f"no confirmation draft recorded for {args.ref} row {args.row}")
            st.save()
            print(f"forgot the confirmation draft for {args.ref} row {args.row}; delete the draft itself in Outlook")
        elif c == "quote":
            run_quote(args)
        elif c == "cancel-fee":
            run_cancel_fee(config.sheet(), args)
        elif c == "pdf-fetch":
            pdf_fetch(config.sheet(), args.row)
        elif c == "draft-confirmation":
            draft_confirmation(config.mail(), config.sheet(), st, args)
            st.save()
        elif c == "draft-attach":
            draft_attach(config.mail(), args.draft_id, args.file)
        elif c == "sim-reset":
            sim.reset(config.sheet(), args.scenario, WORK_DIR)
        elif c == "sim-check":
            if not sim.check(config.sheet(), args.scenario, WORK_DIR):
                return 2
        elif c == "status":
            status(st)
    except Exception as e:
        print(f"ERROR ({args.cmd}): {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
