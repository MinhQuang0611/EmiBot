"""End-of-day check (dev, 2026-11-14): "Cuối ngày thì AI cũng phải tự check lại là nó làm đúng hay sai. Ví dụ 23:30
--> sẽ vào từng email một để kiểm tra lại là đã log vào intake sheet chưa." Came the same day as Karen's "rất nhiều
New booking hoặc cancel bị miss".

    python -m tools.emi day-check [--hours 25]     # the list, read only (job 6's first step)
    python -m tools.day_check <job6-automation-id> # 23:30 command job: the check, a Telegram line, job 6 on work

Every email in the inbox of the last `hours` hours (and any email of the 3 days before that never marked done) is
put against Emi's record (done + outcome, drafts) and the intake sheet. No model: the agent (job 6) is woken only
when a line needs a look, and opens those emails one by one.
  MISSING  never handled; an OTA notice with no row or a cancellation with no CANCEL row; an outcome naming rows
           the sheet doesn't have.
  CHECK    a booking-like email with no row and no reason in its outcome; a cancellation with no CANCEL row; an
           OTA notice without its intake note; a booking-like email closed as noise.
  OK       everything else. Emails younger than RECENT are left to job 1 (still in hand), not judged.
"""
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone

RECENT = timedelta(minutes=20)
BOOKING_SUBJECT = re.compile(r"book|reserv|đặt phòng|dat phong|xác nhận|xac nhan|confirm|voucher|rooming|cancel|huỷ|"
                             r"hủy|\bres\b|amend|modif|thay đổi|UNC|ủy nhiệm|uỷ nhiệm|payment|thanh toán|deposit|cọc",
                             re.I)
CANCEL_SUBJECT = re.compile(r"cancel|huỷ|hủy|\bhuy\b", re.I)
NOISE_OUTCOME = re.compile(r"^\s*NO REPLY:\s*(spam|OTP|alert)", re.I)
ROWS_CLAIMED = re.compile(r"\b(?:NEW|CHANGE|CANCEL)\b[^;]{0,40}\brows?\b|\brows?\s+\d{2,}", re.I)
# an outcome that says why no row was written: an inquiry, a duplicate, a question to Karen, a forward…
NO_ROW_REASON = re.compile(r"inquiry|quote|báo giá|duplicate|trùng|same booking|already|đã có|\bE-\d+|on request|"
                           r"forward|Palma|NO REPLY|ANSWERED BY STAFF|sheet-update|updated row|không cần row|no row "
                           r"needed|hỏi giá|special request|yêu cầu đặc biệt|pick-?up|đưa đón|upgrade|"
                           r"extension|gia hạn|reminder|nhắc|invoice|hoá đơn|hóa đơn|VAT|not a booking",
                           re.I)


def _vn_minute(iso):
    from .emi import vn
    return vn(iso)


def linked_rows(m, outcome, rows):
    """The rows written from this email: its booking numbers (subject, outcome) or its arrival minute (received_at is
    always the time `show` printed for the email, booking-intake.md)."""
    from .emi import booking_numbers, rows_for_numbers
    numbers = booking_numbers(m.get("subject", "")) | booking_numbers(outcome)
    hits = rows_for_numbers(rows, numbers) if numbers else []
    when = _vn_minute(m.get("receivedDateTime", ""))
    seen = {(r.get("_sheet", ""), r.get("_row")) for r in hits}
    hits += [r for r in rows if when and (r.get("received_at") or "").strip() == when
             and (r.get("_sheet", ""), r.get("_row")) not in seen]
    return hits


def judge(m, st, rows, now):
    """(mark, reasons, rows) for one email."""
    from .emi import is_ota_notice, is_ota_robot_notice, notice_action, _sender
    received = datetime.strptime(m["receivedDateTime"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    done = st.data["processed"].get(m["id"])
    if done is None and now - received < RECENT:
        return "RECENT", ["just arrived, job 1 has it"], []
    sender, subject = _sender(m), m.get("subject", "")
    outcome = (done or {}).get("outcome", "")
    hits = linked_rows(m, outcome, rows)
    actions = {r.get("action") for r in hits}
    missing, check = [], []
    if done is None:
        missing.append("never handled (not done)")
    ota = is_ota_notice(sender, subject)
    if ota:
        action = notice_action(subject)
        if not hits:
            missing.append("OTA notice with no row on the sheet")
        elif action == "CANCEL" and "CANCEL" not in actions:
            missing.append("OTA cancellation with no CANCEL row")
        elif action == "CHANGE" and "CHANGE" not in actions:
            check.append("OTA modification with no CHANGE row (fine only if the NEW row was updated before the build)")
        if done is not None and is_ota_robot_notice(sender, subject):
            notes = {n for n, r in st.data["reviews"].items() if r.get("kind") == "ota_note" and r.get("status") != "denied"}
            if not any(st.data["reviews"][n].get("source") == m["id"] for n in notes) \
                    and not set(re.findall(r"#(\d+)", outcome)) & notes:
                check.append("OTA notice without its intake note (ota-note)")
    elif done is not None:
        if NOISE_OUTCOME.search(outcome) and BOOKING_SUBJECT.search(subject):
            check.append("closed as noise, but the subject looks like a booking")
        elif ROWS_CLAIMED.search(outcome) and not hits:
            missing.append("the outcome names rows, the sheet has none for this email")
        elif CANCEL_SUBJECT.search(subject) and "CANCEL" not in actions and not re.search(r"\bE-\d+", outcome):
            check.append("a cancellation with no CANCEL row and no question to Karen")
        elif BOOKING_SUBJECT.search(subject) and not hits and not NO_ROW_REASON.search(outcome):
            check.append("looks like a booking, no row, and the outcome doesn't say why")
    mark = "MISSING" if missing else "CHECK" if check else "OK"
    return mark, missing + check, hits


def run(mail, st, rows, hours=25, now=None, out=print):
    """Every email of the window judged; returns {'OK': n, 'CHECK': n, 'MISSING': n, 'RECENT': n, 'items': [...]}."""
    from .emi import _dedupe, _leftover_since, vn, addr, PHISHING_SENDERS, _sender
    now = now or datetime.now(timezone.utc)
    since = (now - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = _dedupe(rows)
    msgs = [m for m in mail.list_inbox_since(_leftover_since(since)) if _sender(m) not in PHISHING_SENDERS]
    msgs = [m for m in msgs if m["receivedDateTime"][:19] >= since[:19] or not st.is_processed(m["id"])]
    result = {"OK": 0, "CHECK": 0, "MISSING": 0, "RECENT": 0, "items": []}
    out(f"emails since {vn(since)} Vietnam time (plus older ones never done): {len(msgs)}")
    for m in msgs:
        mark, reasons, hits = judge(m, st, rows, now)
        result[mark] += 1
        if mark in ("OK", "RECENT"):
            continue
        done = st.data["processed"].get(m["id"])
        result["items"].append({"id": m["id"], "mark": mark, "subject": m.get("subject", ""), "reasons": reasons})
        where = ", ".join(f"{r['_row']} {r.get('action', '')}" for r in hits[-6:]) or "-"
        out(f"\n{mark} {vn(m['receivedDateTime'])} {addr(m.get('from'))}\n  subject: {m.get('subject', '')}"
            f"\n  id: {m['id']}\n  rows: {where}" + (f"\n  done: {done['outcome'][:160]}" if done else "")
            + f"\n  → {'; '.join(reasons)}")
    out(f"\nOK {result['OK']}, CHECK {result['CHECK']}, MISSING {result['MISSING']}, still in hand {result['RECENT']}")
    return result


def summary(result, day):
    """The Telegram line, in Vietnamese, plain enough for Karen's parents."""
    total = sum(result[k] for k in ("OK", "CHECK", "MISSING", "RECENT"))
    head = f"🔎 Kiểm tra cuối ngày {day}: {total} email"
    if not (result["CHECK"] or result["MISSING"]):
        busy = f" ({result['RECENT']} email vừa đến, đang xử lý)" if result["RECENT"] else ""
        return head + ", tất cả đã xử lý và đã ghi vào intake sheet" + busy + "."
    from .telegram import esc
    lines = [head + f": {result['OK']} đúng, {result['MISSING']} bị sót, {result['CHECK']} cần xem lại. "
                    "Emi đang mở lại từng email này để sửa, sẽ báo kết quả."]
    for i in result["items"][:15]:
        tag = "Sót" if i["mark"] == "MISSING" else "Xem lại"
        lines.append(f"• {tag}: {esc(i['subject'][:70])}")
    if len(result["items"]) > 15:
        lines.append(f"… và {len(result['items']) - 15} email nữa")
    return "\n".join(lines)


def main(argv):
    """23:30 command job: the check, one Telegram line, and job 6 started when a line needs a look."""
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    from . import config
    from .emi import live_rows, VN
    try:
        st = config.state()
        rows = config.sheet().rows() + live_rows(config.live_sheet(), out=lambda *_: None)
        result = run(config.mail(), st, rows, out=lambda *_: None)
    except Exception as e:
        print(f"day-check failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    tg = config.telegram()
    if tg is not None:
        try:
            tg.send(summary(result, datetime.now(VN).strftime("%d/%m")))
        except Exception as e:  # the check stands either way
            print(f"telegram failed: {e}", file=sys.stderr)
    if not (result["CHECK"] or result["MISSING"]):
        print("NO_REPLY")
        return 0
    exe = shutil.which("openclaw") or "openclaw"
    res = subprocess.run([exe, "automations", "run", argv[0]], capture_output=True, text=True, timeout=90)
    if res.returncode != 0:
        print(f"could not start job 6: {(res.stderr or res.stdout).strip()[-300:]}", file=sys.stderr)
        return 2
    print(json.dumps({"MISSING": result["MISSING"], "CHECK": result["CHECK"], "started": "job 6"}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
