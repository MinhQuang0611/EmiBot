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
    python -m tools.emi pdf-fetch <row>                   # download the file behind pdf_link, print it next to the row
    python -m tools.emi draft-confirmation <message_id> <row> <body.txt> [--all]  # reply draft + the EZFOLIO PDF
    python -m tools.emi status                            # scan clock and counts

Every draft stays in Drafts with the Emi category. Nothing here can send (graph_mail refuses).
Exit 0 = done, 2 = refused or failed (reason on stderr).
"""
import argparse
import json
import mimetypes
import os
import sys
from datetime import datetime, timedelta, timezone

from . import attachments, config, drive
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
    only = [a.strip().lower() for a in os.environ.get("EMI_TEST_ONLY_FROM", "").split(",") if a.strip()]
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


def show(mail, message_id, work_dir=WORK_DIR, out=print):
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
    out("\nROOM CODES (room_code):")
    for code, (name, note) in codes.items():
        out(f"- {code} = {name}" + (f" — {note}" if note else ""))
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


# --- confirmation PDF (job 2) ---

ROW_SUMMARY = ("booking_ref", "company", "guest_names", "arrival", "departure", "nights", "room_code", "rooms",
               "adults", "children", "rate_per_night_vnd", "Average rate per night after discount", "total_vnd")


def _row(sheet, row):
    r = next((x for x in sheet.rows() if x["_row"] == int(row)), None)
    if r is None:
        raise Refused(f"row {row} is empty or not a data row")
    return r


def pdf_fetch(sheet, row, work_dir=WORK_DIR, out=print):
    """Download the file behind pdf_link on one row; print it next to the row so they can be compared."""
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


def draft_confirmation(mail, sheet, st, args, out=print):
    """Reply on the sender's thread with the build tool's own PDF attached. Never a PDF Emi made."""
    r = _row(sheet, args.row)
    ref = r.get("booking_ref", "")
    if (ref, int(args.row)) in st.confirmation_drafted():
        raise Refused(f"{ref} row {args.row} already has a confirmation draft")
    body = read_text(args.body)
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
    s = sub.add_parser("pdf-fetch"); s.add_argument("row", type=int)
    s = sub.add_parser("draft-confirmation")
    s.add_argument("message_id"); s.add_argument("row", type=int); s.add_argument("body")
    s.add_argument("--all", action="store_true", help="reply all")
    sub.add_parser("status")
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
        elif c == "pdf-fetch":
            pdf_fetch(config.sheet(), args.row)
        elif c == "draft-confirmation":
            draft_confirmation(config.mail(), config.sheet(), st, args)
            st.save()
        elif c == "draft-attach":
            draft_attach(config.mail(), args.draft_id, args.file)
        elif c == "status":
            status(st)
    except Exception as e:
        print(f"ERROR ({args.cmd}): {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
