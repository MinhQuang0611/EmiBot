"""Acceptance tests from openclaw-setup-brief.md, run against the real mailbox and sheet.

    python -m tools.acceptance mail-read                 # test 2: 5 newest inbox emails
    python -m tools.acceptance attachments <message_id>  # test 3: list attachments of one email
    python -m tools.acceptance send-blocked              # test 6: the tool refuses to send
    python -m tools.acceptance draft-reply <message_id>  # test 4: draft a reply on a TEST thread
    python -m tools.acceptance attach-pdf <draft_id> <file.pdf>  # test 5
    python -m tools.acceptance sheet-header              # header vs test/fixtures/intake-columns.csv
    python -m tools.acceptance sheet-roundtrip           # test 7: write TEST-EMI row, then delete it

Run them in this order and stop at the first failure. Only draft-reply, attach-pdf and
sheet-roundtrip write anything; draft-reply must target a test email sent from haya@haya-hotels.com (or EMI_TEST_SENDER).
"""
import csv
from email import policy
from email.parser import BytesParser
import os
import sys

from . import config
from .graph_mail import GraphMail, SendBlocked

FIXTURE = os.path.join(os.path.dirname(__file__), "..", "test", "fixtures", "intake-columns.csv")


def mail_read():
    mail = config.mail()
    q = mail._query(select="subject,from,receivedDateTime", orderby="receivedDateTime desc", top="5")
    for m in mail._call("GET", f"/mailFolders/inbox/messages?{q}").get("value", []):
        print(m["receivedDateTime"], m["from"]["emailAddress"]["address"], "|", m["subject"])


def attachments(message_id):
    for a in config.mail().list_attachments(message_id):
        print(a.get("name"), a.get("contentType"), a.get("size"), "inline" if a.get("isInline") else "")


def send_blocked():
    mail = GraphMail("x@example.com", token=lambda: "unused",
                     http=lambda *a, **k: sys.exit("FAIL: a send request reached the network"))
    for path in ("/sendMail", "/messages/abc/send", "/messages/abc/reply", "/messages/abc/forward",
                 "/messages/abc/replyAll"):
        try:
            mail._call("POST", path)
            sys.exit(f"FAIL: {path} was not blocked")
        except SendBlocked:
            pass
    missing = [n for n in ("send", "send_mail", "reply", "forward") if hasattr(GraphMail, n)]
    if missing:
        sys.exit(f"FAIL: GraphMail has send-like methods {missing}")
    print("PASS: every send endpoint is refused and GraphMail has no send method")


def draft_reply(message_id):
    mail = config.mail()
    src = mail.get_message_text(message_id)
    sender = src["from"]["emailAddress"]["address"].lower()
    allowed = os.environ.get("EMI_TEST_SENDER", "haya@haya-hotels.com").lower()
    if sender != allowed:
        sys.exit(f"refusing: test drafts only reply to {allowed} (EMI_TEST_SENDER), this is from {sender}")
    d = mail.create_reply_draft(message_id, "TEST - Emi draft. Do not send.")
    check = mail._call("GET", f"/messages/{d['id']}?$select=isDraft,categories,conversationId")
    ok = check["isDraft"] and "Emi" in check["categories"] and check["conversationId"] == src["conversationId"]
    print(("PASS" if ok else "FAIL"), "draft", d["id"], check)


def attach_pdf(draft_id, path):
    with open(path, "rb") as f:
        config.mail().add_attachment(draft_id, os.path.basename(path), f.read())
    print("PASS: attached; open the draft in Outlook and check the PDF opens")


def sheet_header():
    with open(FIXTURE, encoding="utf-8-sig") as f:
        expected = next(csv.reader(f))
    missing, extra = config.sheet().check_header(expected)
    print("On fixture, not on sheet:", missing or "none")
    print("On sheet, not on fixture:", extra or "none")
    print("Replace test/fixtures/intake-columns.csv with the real header if these differ.")


def sheet_roundtrip():
    sh = config.sheet()
    if sh.find_by_ref("TEST-EMI"):
        sys.exit("a TEST-EMI row already exists; delete it by hand first")
    sh.append_rows([{"action": "NEW", "booking_ref": "TEST-EMI", "company": "TEST - delete me",
                     "notes": "Emi acceptance test 7"}])
    rows = sh.find_by_ref("TEST-EMI")
    if len(rows) != 1:
        sys.exit(f"FAIL: expected 1 TEST-EMI row, found {len(rows)}")
    print("written at row", rows[0]["_row"], "tracy_status =", rows[0].get("tracy_status"))
    sh.delete_test_row(rows[0]["_row"])
    print("PASS" if not sh.find_by_ref("TEST-EMI") else "FAIL: row still there")


def sheet_smoke_write():
    """Write a clearly fictional row and leave it visible for manual inspection."""
    sh = config.sheet()
    ref = "TEST-EMI-VISIBLE"
    if sh.find_by_ref(ref):
        sys.exit(f"{ref} already exists; refusing to add a duplicate")
    sh.append_rows([{
        "action": "NEW",
        "received_at": "09/10/2026 12:00",
        "source_email": "SMOKE TEST ONLY - fictional booking; do not build",
        "property": "HAYA",
        "channel_type": "Direct",
        "company": "SMOKE TEST - DO NOT BUILD",
        "contact_person": "Test User",
        "company_email": "test@example.com",
        "booking_ref": ref,
        "guest_names": "TEST GUEST",
        "nationality": "Vietnam",
        "arrival": "15/11/2026",
        "departure": "16/11/2026",
        "nights": "1",
        "room_code": "TEST ONLY",
        "rooms": "1",
        "adults": "1",
        "children": "0",
        "meal_plan": "RO",
        "status": "Tentative",
        "notes": "SMOKE TEST ONLY. Fictional data; do not build in EZFOLIO.",
        "missing_info": "SMOKE TEST ONLY — fictional row; do not build",
        "priority": "Normal",
    }])
    rows = sh.find_by_ref(ref)
    if len(rows) != 1:
        sys.exit(f"FAIL: expected exactly one {ref} row after writing; found {len(rows)}")
    row = rows[0]
    print(f"PASS: kept visible smoke-test row at row {row['_row']}; booking_ref={ref}; tracy_status={row.get('tracy_status')}")


def sheet_email_smoke_write(path=None):
    """Clone known fields from a local email fixture to a visibly marked sandbox row."""
    path = path or os.path.join(os.path.dirname(__file__), "..", "test", "emails",
                                "Fw_ NEW BOOKING OBT071026MB.eml")
    with open(path, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)
    ref = "TEST-OBT071026MB"
    sh = config.sheet()
    if sh.find_by_ref(ref):
        sys.exit(f"{ref} already exists; refusing to add a duplicate")
    sh.append_rows([{
        "action": "NEW",
        "received_at": "08/10/2026 14:11",
        "source_email": f"SMOKE TEST ONLY — {msg.get('subject', '').strip()}",
        "property": "HAYA",
        "channel_type": "TA",
        "company": "CÔNG TY TNHH DU LỊCH VÀ DỊCH VỤ TRỰC TUYẾN VIỆT NAM",
        "contact_person": "Mai Hương",
        "company_email": "sales1.onlinebooking@gmail.com",
        "booking_ref": ref,
        "guest_names": "Nguyễn Chí Công",
        "nationality": "Vietnam",
        "arrival": "08/10/2026",
        "departure": "09/10/2026",
        "nights": "1",
        "room_code": "DBL (TEST; mapping unverified)",
        "rooms": "1",
        "adults": "1",
        "children": "0",
        "rate_source": "Other",
        "rate_per_night_vnd": "1150000",
        "total_vnd": "1150000",
        "status": "Definite",
        "invoice_details": "CÔNG TY TNHH DU LỊCH VÀ DỊCH VỤ TRỰC TUYẾN VIỆT NAM; MST 0108916292",
        "notes": "SMOKE TEST ONLY — cloned from email fixture. Original ref OBT071026MB. Prior HAYA reply in thread states VND 1,150,000/room/night.",
        "missing_info": "SMOKE TEST ONLY — do not build. Past arrival date. DBL room-code mapping and meal plan unverified. Attached transfer proof is not confirmation funds were received.",
        "priority": "Normal",
    }])
    rows = sh.find_by_ref(ref)
    if len(rows) != 1:
        sys.exit(f"FAIL: expected exactly one {ref} row after writing; found {len(rows)}")
    row = rows[0]
    print(f"PASS: kept email smoke-test row at row {row['_row']}; booking_ref={ref}; tracy_status={row.get('tracy_status')}")


COMMANDS = {"mail-read": mail_read, "attachments": attachments, "send-blocked": send_blocked,
            "draft-reply": draft_reply, "attach-pdf": attach_pdf,
            "sheet-header": sheet_header, "sheet-roundtrip": sheet_roundtrip,
            "sheet-smoke-write": sheet_smoke_write,
            "sheet-email-smoke-write": sheet_email_smoke_write}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        sys.exit(__doc__)
    COMMANDS[sys.argv[1]](*sys.argv[2:])
