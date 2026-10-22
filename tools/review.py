"""A person's review of each draft Emi saves: #n numbers, a Telegram notice per draft, and the four answers.

    accept  -> the draft gets the 'Emi approved' category in Outlook. It is NOT sent: a person still opens
               Drafts and presses Send (AGENTS.md rule 1; the mail token has no Mail.Send).
    deny    -> the draft goes to Outlook's Deleted Items (recoverable); a denied confirmation or reminder can
               be drafted again.
    rewrite -> Emi writes a new text from the reviewer's comments; a new draft on the same thread replaces the
               old one, attachments carried over, same #n, version + 1, new notice.
    info    -> everything about #n: status, source email, the full text, history (a typed command, not a
               button: the notice already shows the draft).

Drafts a person sends or deletes straight in Outlook show up as 'gone' in review-list.
"""
from datetime import datetime, timedelta, timezone

from .state import REVIEW_OPEN
from .telegram import esc

VN = timezone(timedelta(hours=7))

KIND_LABEL = {
    "confirmation": "Xác nhận booking", "reply": "Trả lời", "forward": "Chuyển tiếp",
    "inquiry": "Báo giá / tư vấn", "deposit_reminder": "Nhắc đặt cọc", "balance_reminder": "Nhắc thanh toán",
}
PREVIEW = 2800  # characters of the draft shown in the notice; review-info shows all of it


class ReviewError(Exception):
    pass


def _vn(iso):
    return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone(VN).strftime(
        "%d/%m %H:%M")


def _addresses(draft):
    return [r["emailAddress"]["address"] for r in (draft or {}).get("toRecipients", [])]


def _headline(n, r):
    ref = f" · {r['ref']}" + (f" (dòng {r['row']})" if r.get("row") else "") if r.get("ref") else ""
    version = f" · v{r['version']}" if r["version"] > 1 else ""
    return f"Draft #{n} — {KIND_LABEL.get(r['kind'], r['kind'])}{ref}{version}"


def _buttons(n):
    # Info is not a button: the notice already shows the whole draft. Only Accept / Deny end a review.
    return [[("Accept", f"emi review accept {n}"), ("Deny", f"emi review deny {n}")],
            [("Rewrite", f"emi review rewrite {n}")]]


def notify(tg, n, r, note="", in_place=False):
    """Send the notice for #n, or with in_place=True rewrite the existing one (text and buttons) so one
    draft keeps one message. Falls back to a new message if the old one can't be edited."""
    if tg is None:
        return None
    text = r["text"] if len(r["text"]) <= PREVIEW else r["text"][:PREVIEW] + f"\n… (nhắn: xem {n} để đọc hết)"
    lines = [f"✉️ <b>{esc(_headline(n, r))}</b>",
             f"<b>Gửi:</b> {esc(', '.join(r['to']))}",
             f"<b>Tiêu đề:</b> {esc(r['subject'])}"]
    if r.get("attachments"):
        lines.append(f"<b>Đính kèm:</b> {esc(', '.join(r['attachments']))}")
    if note:
        lines.append(f"<b>Đã sửa theo:</b> {esc(note)}")
    lines += ["", f"<blockquote expandable>{esc(text)}</blockquote>",
              f"Accept = duyệt (vẫn phải bấm Send trong Outlook). Rewrite = nhắn ý kiến sửa, "
              f"hoặc <code>rewrite {n} ý kiến</code>"]
    if in_place and r.get("tg"):
        try:
            tg.edit(r["tg"], "\n".join(lines), _buttons(n))
            r.pop("tg_error", None)
            return r["tg"]
        except Exception:
            pass  # too old or deleted: send a fresh one
    try:
        r["tg"] = tg.send("\n".join(lines), _buttons(n))
        r.pop("tg_error", None)
    except Exception as e:  # the draft is saved either way; review-list still shows it
        r["tg_error"] = f"{type(e).__name__}: {e}"[:300]
    return r.get("tg")


def _mark(tg, r, note):
    if tg is None or not r.get("tg"):
        return
    try:
        tg.mark(r["tg"], note)
    except Exception:
        pass


def opened(mail, st, tg, draft_id, *, how, source, kind, ref="", row=0, text, reply_all=False, to=None,
           attachments=()):
    """Called right after a draft is saved. Returns the review number."""
    d = mail.get_draft(draft_id) or {}
    n = st.open_review(draft_id, how=how, source=source, reply_all=reply_all, kind=kind, ref=ref, row=row,
                       to=_addresses(d) or list(to or []), subject=d.get("subject", ""), text=text,
                       attachments=list(attachments))
    notify(tg, n, st.data["reviews"][n])
    return n


def attached(st, draft_id, name):
    n = st.review_by_draft(draft_id)
    if n:
        st.data["reviews"][n].setdefault("attachments", []).append(name)
    return n


def _pending(mail, st, n):
    n, r = st.review(n)
    if r["status"] != REVIEW_OPEN:
        raise ReviewError(f"#{n} is already {r['status']}")
    if mail.get_draft(r["draft_id"]) is None:
        st.close_review(n, "gone", "no longer in Drafts: sent or deleted in Outlook")
        raise ReviewError(f"#{n} is no longer in Drafts: a person sent or deleted it in Outlook")
    return n, r


ASK = ("Dạ, anh/chị muốn chỉnh sửa nội dung nào trong email này (draft #{n}) ạ? Anh/chị cứ nhắn ý kiến, "
       "Emi sẽ viết lại và cập nhật ngay trên tin nhắn draft.")


def ask(mail, st, tg, n, out=print):
    """Rewrite pressed: remember that the reviewer's next message is the feedback for #n, put the buttons back,
    and print the question Emi sends as its reply."""
    n, r = _pending(mail, st, n)
    st.data["awaiting_feedback"] = n
    notify(tg, n, r, in_place=True)
    out(ASK.format(n=n))


def awaiting(st, out=print):
    n = st.data.get("awaiting_feedback")
    if n and st.data["reviews"].get(n, {}).get("status") == REVIEW_OPEN:
        out(f"#{n} is waiting for the reviewer's feedback: their message is what to change in draft #{n}")
        return n
    out("no draft is waiting for feedback")
    return None


def _done_waiting(st, n):
    if st.data.get("awaiting_feedback") == n:
        st.data["awaiting_feedback"] = None


def accept(mail, st, tg, n, by="", out=print):
    n, r = _pending(mail, st, n)
    mail.approve_draft(r["draft_id"])
    st.close_review(n, "approved", by)
    _done_waiting(st, n)
    msg = f"✅ #{n} đã duyệt. Draft nằm trong Outlook › Drafts (nhãn 'Emi approved'): mở và bấm Send."
    _mark(tg, r, msg)
    out(msg)


def deny(mail, st, tg, n, reason="", by="", out=print):
    n, r = _pending(mail, st, n)
    mail.delete_draft(r["draft_id"])
    st.close_review(n, "denied", " — ".join(x for x in (reason, by) if x))
    _done_waiting(st, n)
    st.data["drafts"].pop(r["draft_id"], None)
    if r["kind"] == "confirmation" and r.get("ref"):
        st.forget_confirmation(r["ref"], r["row"])  # a corrected confirmation may be drafted again
    elif r["kind"] in ("deposit_reminder", "balance_reminder"):
        st.data["reminders"].pop(f"{r['ref']}|{r['kind'].split('_')[0]}", None)
    msg = f"❌ #{n} đã bỏ: draft chuyển vào Deleted Items của Outlook." + (f" Lý do: {reason}" if reason else "")
    _mark(tg, r, esc(msg))
    out(msg)


def rewrite(mail, st, tg, n, text, feedback="", check=None, out=print):
    n, r = _pending(mail, st, n)
    if check:
        check(text)
    old = r["draft_id"]
    files = [a for a in mail.list_draft_attachments(old)
             if a.get("@odata.type") == "#microsoft.graph.fileAttachment" and not a.get("isInline") and a.get("data")]
    if r["how"] == "forward":
        d = mail.forward_draft_with_text(r["source"], r["to"], text)
    else:
        d = mail.reply_draft_with_text(r["source"], text, reply_all=r.get("reply_all", False))
    for a in files:
        mail.add_attachment(d["id"], a["name"], a["data"], content_type=a.get("contentType") or "application/pdf")
    mail.delete_draft(old)
    # every record that pointed at the old draft now points at the new one
    if old in st.data["drafts"]:
        st.data["drafts"][d["id"]] = st.data["drafts"].pop(old)
    for bucket in ("confirmations", "reminders"):
        for v in st.data[bucket].values():
            if v.get("draft_id") == old:
                v["draft_id"] = d["id"]
    r["history"].append({"at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "status": "rewritten", "note": feedback, "old_text": r["text"]})
    r.update(draft_id=d["id"], text=text, version=r["version"] + 1, attachments=[a["name"] for a in files])
    notify(tg, n, r, note=feedback, in_place=True)  # same message, new text, buttons kept
    _done_waiting(st, n)
    out(f"#{n} rewritten as v{r['version']}: new draft {d['id']} (old one moved to Deleted Items), "
        f"{len(files)} attachment(s) carried over")
    return d


def info(mail, st, n, out=print):
    n, r = st.review(n)
    live = mail.get_draft(r["draft_id"]) if r["status"] == REVIEW_OPEN else None
    if r["status"] == REVIEW_OPEN and live is None:
        st.close_review(n, "gone", "no longer in Drafts: sent or deleted in Outlook")
    out(_headline(n, r))
    out(f"status: {r['status']}" + (" (still in Drafts)" if live else ""))
    out(f"to: {', '.join(r['to'])}")
    out(f"subject: {r['subject']}")
    if r.get("attachments"):
        out(f"attachments: {', '.join(r['attachments'])}")
    out(f"opened: {_vn(r['opened_at'])} (giờ Việt Nam)")
    try:
        src = mail.get_message_text(r["source"])
        frm = src.get("from", {}).get("emailAddress", {})
        body = (src.get("uniqueBody") or src.get("body") or {}).get("content", "").strip()
        out(f"\nSOURCE EMAIL: {frm.get('name', '')} <{frm.get('address', '')}> | {src.get('subject', '')} | "
            f"{src.get('receivedDateTime', '')}")
        out(body[:1500] + ("\n…" if len(body) > 1500 else ""))
    except Exception as e:
        out(f"\nSOURCE EMAIL: could not read ({type(e).__name__})")
    out("\nDRAFT TEXT:")
    out(r["text"])
    for h in r["history"]:
        out(f"history: {_vn(h['at'])} {h['status']}" + (f" — {h['note']}" if h.get("note") else ""))
    return r


def listing(mail, st, everything=False, out=print):
    shown = 0
    for n, r in sorted(st.data["reviews"].items(), key=lambda kv: int(kv[0])):
        if r["status"] == REVIEW_OPEN and mail.get_draft(r["draft_id"]) is None:
            st.close_review(n, "gone", "no longer in Drafts: sent or deleted in Outlook")
        if r["status"] != REVIEW_OPEN and not everything:
            continue
        shown += 1
        out(f"#{n} [{r['status']}] {KIND_LABEL.get(r['kind'], r['kind'])}"
            + (f" {r['ref']}" if r.get("ref") else "") + f" → {', '.join(r['to'])} | {r['subject']} | "
            f"{_vn(r['opened_at'])}" + (f" | v{r['version']}" if r["version"] > 1 else ""))
    if not shown:
        out("no drafts waiting for review" if not everything else "no reviews yet")
