"""A person's review of each draft Emi writes: #n numbers, a Telegram notice per draft, and the answers.

Two modes (EMI_DRAFT_MODE):
    telegram -> the draft lives only on Telegram (text and attachments kept on the host) until someone presses
                Accept; only then is it saved in Outlook Drafts. Nothing reaches Outlook for a denied draft.
    outlook  -> the draft is saved in Outlook Drafts at once and the notice points at it.

    accept  -> the draft is in Outlook Drafts with the 'Emi approved' category. It is NOT sent: a person still
               opens Drafts and presses Send (AGENTS.md rule 1; the mail token has no Mail.Send).
    deny    -> the draft is dropped (an Outlook draft goes to Deleted Items, recoverable). A denied confirmation
               or reminder is not proposed again by the next run; Rewrite is the way to correct one.
    rewrite -> the reviewer's comments, written in by Emi; same #n, version + 1, same Telegram message.
    info    -> everything about #n (typed `xem n`, not a button: the notice already shows the draft).

An Outlook draft a person sends or deletes straight in Outlook shows up as 'gone' in review-list.
"""
import os
import re
from datetime import datetime, timedelta, timezone

from .graph_mail import CHECK_LINE, SendBlocked, clean_subject, reply_subject
from .state import REVIEW_OPEN
from .telegram import esc

VN = timezone(timedelta(hours=7))
PENDING = "pending-"  # draft id of a draft that exists only on Telegram so far

KIND_LABEL = {
    "confirmation": "Xác nhận booking", "reply": "Trả lời", "forward": "Chuyển tiếp",
    "inquiry": "Báo giá / tư vấn", "request": "Yêu cầu của khách", "deposit_reminder": "Nhắc đặt cọc",
    "balance_reminder": "Nhắc thanh toán", "decline": "Từ chối booking on request",
}
PREVIEW = 2800  # characters of the draft shown in the notice; review-info shows all of it


class ReviewError(Exception):
    pass


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _vn(iso):
    return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone(VN).strftime(
        "%d/%m %H:%M")


def _addresses(recipients):
    return [x["emailAddress"]["address"] for x in recipients or [] if x.get("emailAddress", {}).get("address")]


def in_outlook(r):
    return bool(r.get("draft_id")) and not r["draft_id"].startswith(PENDING)


def _headline(n, r):
    ref = f" · {r['ref']}" + (f" (dòng {r['row']})" if r.get("row") else "") if r.get("ref") else ""
    version = f" · v{r['version']}" if r["version"] > 1 else ""
    return f"Draft #{n} — {KIND_LABEL.get(r['kind'], r['kind'])}{ref}{version}"


def _buttons(n):
    # Info is not a button: the notice already shows the whole draft. Only Accept / Deny end a review.
    return [[("Accept", f"emi review accept {n}"), ("Deny", f"emi review deny {n}")],
            [("Rewrite", f"emi review rewrite {n}")]]


def as_email(text):
    """The draft as the reader will see it in Outlook: **Label:** in bold (graph_mail.text_to_html does the
    same), '•' lists and blank lines kept. Telegram HTML."""
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", esc(text))


def notify(tg, n, r, note="", in_place=False):
    """Send the notice for #n, or with in_place=True rewrite the existing one (text and buttons) so one
    draft keeps one message. Falls back to a new message if the old one can't be edited."""
    if tg is None:
        return None
    text = r["text"] if len(r["text"]) <= PREVIEW else r["text"][:PREVIEW] + f"\n… (nhắn: xem {n} để đọc hết)"
    lines = [f"✉️ <b>{esc(_headline(n, r))}</b>",
             f"<b>Gửi:</b> {esc(', '.join(r['to']))}"]
    if r.get("cc"):
        lines.append(f"<b>Cc:</b> {esc(', '.join(r['cc']))}")
    lines.append(f"<b>Tiêu đề:</b> {esc(r['subject'])}")
    if r.get("attachments"):
        lines.append(f"<b>Đính kèm:</b> {esc(', '.join(r['attachments']))}")
    if note:
        lines.append(f"<b>Đã sửa theo:</b> {esc(note)}")
    where = ("Đã nằm trong Outlook Drafts. Accept = duyệt (vẫn phải bấm Send trong Outlook)." if in_outlook(r) else
             "Chưa có trong Outlook. Accept = lưu vào Outlook Drafts (vẫn phải bấm Send).")
    lines += ["", "<b>Nội dung email:</b>", f"<blockquote>{as_email(text)}</blockquote>",
              f"{where} Rewrite = nhắn ý kiến sửa, hoặc <code>rewrite {n} ý kiến</code>"]
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
    except Exception as e:  # the draft is kept either way; review-list still shows it
        r["tg_error"] = f"{type(e).__name__}: {e}"[:300]
    return r.get("tg")


def _mark(tg, r, note):
    if tg is None or not r.get("tg"):
        return
    try:
        tg.mark(r["tg"], note)
    except Exception:
        pass


# --- a new draft ---

def opened(mail, st, tg, draft_id, *, how, source, kind, ref="", row=0, text, reply_all=False, to=None,
           cc=None, override=False, attachments=()):
    """Outlook mode: called right after the draft is saved in Outlook. Returns the review number.
    override=True: a reply whose recipients were set by --to (the draft is rebuilt with them on rewrite)."""
    d = mail.get_draft(draft_id) or {}
    n = st.open_review(draft_id, how=how, source=source, reply_all=reply_all, kind=kind, ref=ref, row=row,
                       to=_addresses(d.get("toRecipients")) or list(to or []),
                       cc=_addresses(d.get("ccRecipients")) or list(cc or []), to_override=bool(override),
                       subject=d.get("subject", ""), text=text, attachments=list(attachments), files=[])
    notify(tg, n, st.data["reviews"][n])
    return n


def propose(mail, st, tg, store, *, how, source, kind, ref="", row=0, text, reply_all=False, to=None,
            cc=None, files=(), mailbox="", new_subject=""):
    """Telegram mode: nothing goes to Outlook. The draft (text + files under store/<n>/) waits for Accept.
    files = [(name, bytes, content_type)]. Returns the review number; the draft id is 'pending-<n>'.
    A reply with to=[...] goes to exactly to / cc (the real sender of a mail our staff forwarded in), and its
    subject is 'RE: <original subject>' without the 'Fw:'; Accept writes it into Outlook the same way."""
    src = mail.get_message_text(source)
    subject = ("FW: " + clean_subject(src.get("subject", ""))) if how == "forward" else reply_subject(src.get("subject", ""))
    override = how == "reply" and bool(to)
    if how == "new":  # a new email, e.g. Odeon's confirmation: the subject and recipients given
        subject, recipients = new_subject, list(to or [])
    elif how == "forward":
        recipients = list(to or [])
    elif override:
        recipients = list(to)
    else:
        recipients = _addresses([src.get("from")])
        if reply_all:
            others = _addresses(src.get("toRecipients")) + _addresses(src.get("ccRecipients"))
            recipients += [a for a in others if a.lower() != mailbox.lower() and a not in recipients]
    n = st.open_review(None, how=how, source=source, reply_all=reply_all, kind=kind, ref=ref, row=row,
                       to=recipients, cc=list(cc or []) if override or how == "new" else [], to_override=override,
                       subject=subject, text=text, attachments=[], files=[])
    r = st.data["reviews"][n]
    r["draft_id"] = PENDING + n
    for name, data, ctype in files:
        _keep_file(r, store, n, name, data, ctype)
    notify(tg, n, r)
    return n


def _keep_file(r, store, n, name, data, ctype):
    folder = os.path.join(store, n)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)
    with open(path, "wb") as f:
        f.write(data)
    r["files"].append({"name": name, "path": os.path.abspath(path), "contentType": ctype})
    r["attachments"].append(name)


def attached(st, draft_id, name, data=None, ctype=None, store=None):
    """A file added to draft #n after it was written (draft-attach)."""
    n = st.review_by_draft(draft_id)
    if n is None:
        return None
    r = st.data["reviews"][n]
    if draft_id.startswith(PENDING):
        _keep_file(r, store, n, name, data, ctype)
    else:
        r.setdefault("attachments", []).append(name)
    return n


def _repoint(st, old, new):
    """Every record that pointed at draft `old` now points at `new`."""
    if old in st.data["drafts"]:
        st.data["drafts"][new] = st.data["drafts"].pop(old)
    for bucket in ("confirmations", "reminders"):
        for v in st.data[bucket].values():
            if v.get("draft_id") == old:
                v["draft_id"] = new


def _write(mail, r, text):
    """The draft for review r, written into Outlook: a forward, a new email, a reply to whoever sent the
    source, or a reply to the addresses --to gave."""
    if r["how"] == "forward":
        return mail.forward_draft_with_text(r["source"], r["to"], text)
    if r["how"] == "new":
        return mail.create_new_draft(r["to"], r["subject"], text, cc=r.get("cc") or [])
    if r.get("to_override"):
        return mail.reply_draft_with_text(r["source"], text, to=r["to"], cc=r.get("cc") or [])
    return mail.reply_draft_with_text(r["source"], text, reply_all=r.get("reply_all", False))


def _to_outlook(mail, st, r):
    """Accept in Telegram mode: write the draft into Outlook Drafts now, files attached."""
    d = _write(mail, r, r["text"])
    for f in r.get("files", []):
        with open(f["path"], "rb") as fh:
            mail.add_attachment(d["id"], f["name"], fh.read(), content_type=f["contentType"])
    _repoint(st, r["draft_id"], d["id"])
    r["draft_id"] = d["id"]
    return d


# --- the reviewer's answers ---

def _pending(mail, st, n):
    n, r = st.review(n)
    if r["status"] != REVIEW_OPEN:
        raise ReviewError(f"#{n} is already {r['status']}")
    if in_outlook(r) and mail.get_draft(r["draft_id"]) is None:
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


def _approvers():
    """EMI_APPROVERS: who may Accept, comma-separated Telegram names / @usernames / user ids (dev, 2026-10-30:
    Karen confirms). Unset = anyone in the chat."""
    return [a.strip().lstrip("@").lower() for a in os.environ.get("EMI_APPROVERS", "").split(",") if a.strip()]


def send_on_accept():
    """EMI_SEND_ON_ACCEPT=1 (dev, 2026-10-30): Karen's Accept sends the draft. Needs EMI_APPROVERS and the
    Mail.Send sign-in. Off = Accept only tags it and a person presses Send."""
    return os.environ.get("EMI_SEND_ON_ACCEPT", "") == "1"


def accept(mail, st, tg, n, by="", out=print):
    allowed = _approvers()
    send = send_on_accept()
    if send and not allowed:
        raise ReviewError("EMI_SEND_ON_ACCEPT=1 needs EMI_APPROVERS (Karen's Telegram name); nothing sent")
    if allowed and (by or "").strip().lstrip("@").lower() not in allowed:
        raise ReviewError(f"#{str(n).lstrip('#')}: only {', '.join(allowed)} can Accept"
                          + (f", not {by}" if by else " (no --by given)") + ". The draft stays pending.")
    n, r = _pending(mail, st, n)
    if send and CHECK_LINE.lower() in (r.get("text") or "").lower():
        raise ReviewError(f"#{n} còn dòng {CHECK_LINE} …]: Emi không gửi. Rewrite #{n} để bỏ dòng đó, rồi Accept lại.")
    new = not in_outlook(r)
    if new:
        _to_outlook(mail, st, r)
    if send:
        try:
            mail.send_draft(r["draft_id"])
        except SendBlocked as e:
            raise ReviewError(f"#{n} chưa gửi: {e}") from None
        st.close_review(n, "sent", by)
        _done_waiting(st, n)
        msg = f"#{n} đã gửi ({by})." + (" Thư nằm trong Outlook › Sent Items." if not new else "")
        _mark(tg, r, esc(msg))
        out(msg)
        return
    mail.approve_draft(r["draft_id"])
    st.close_review(n, "approved", by)
    _done_waiting(st, n)
    msg = (f"#{n} đã duyệt" + (" và lưu vào Outlook › Drafts" if new else ", draft trong Outlook › Drafts")
           + " (nhãn 'Emi approved'). Mở Outlook và bấm Send.")
    _mark(tg, r, esc(msg))
    out(msg)


def deny(mail, st, tg, n, reason="", by="", out=print):
    n, r = _pending(mail, st, n)
    was_in_outlook = in_outlook(r)
    if was_in_outlook:
        mail.delete_draft(r["draft_id"])
    st.close_review(n, "denied", " — ".join(x for x in (reason, by) if x))
    _done_waiting(st, n)
    # The confirmation / reminder record stays, so the next hourly run doesn't propose the same draft again.
    msg = f"#{n} đã bỏ" + (": draft chuyển vào Deleted Items của Outlook." if was_in_outlook else
                           ", không lưu gì vào Outlook.") + (f" Lý do: {reason}" if reason else "")
    _mark(tg, r, esc(msg))
    out(msg)


def rewrite(mail, st, tg, n, text, feedback="", check=None, out=print):
    n, r = _pending(mail, st, n)
    if check:
        check(text)
    r["history"].append({"at": now_iso(), "status": "rewritten", "note": feedback, "old_text": r["text"]})
    if not in_outlook(r):  # Telegram only: just the text changes
        r.update(text=text, version=r["version"] + 1)
        notify(tg, n, r, note=feedback, in_place=True)
        _done_waiting(st, n)
        out(f"#{n} rewritten as v{r['version']} (Telegram only; saved in Outlook on Accept)")
        return None
    old = r["draft_id"]
    files = [a for a in mail.list_draft_attachments(old)
             if a.get("@odata.type") == "#microsoft.graph.fileAttachment" and not a.get("isInline") and a.get("data")]
    d = _write(mail, r, text)
    for a in files:
        mail.add_attachment(d["id"], a["name"], a["data"], content_type=a.get("contentType") or "application/pdf")
    mail.delete_draft(old)
    _repoint(st, old, d["id"])
    r.update(draft_id=d["id"], text=text, version=r["version"] + 1, attachments=[a["name"] for a in files])
    notify(tg, n, r, note=feedback, in_place=True)  # same message, new text, buttons kept
    _done_waiting(st, n)
    out(f"#{n} rewritten as v{r['version']}: new draft {d['id']} (old one moved to Deleted Items), "
        f"{len(files)} attachment(s) carried over")
    return d


def _check_gone(mail, st, n, r):
    if r["status"] == REVIEW_OPEN and in_outlook(r) and mail.get_draft(r["draft_id"]) is None:
        st.close_review(n, "gone", "no longer in Drafts: sent or deleted in Outlook")


def info(mail, st, n, out=print):
    n, r = st.review(n)
    _check_gone(mail, st, n, r)
    out(_headline(n, r))
    where = "in Outlook Drafts" if in_outlook(r) else "Telegram only, not in Outlook until Accept"
    out(f"status: {r['status']}" + (f" ({where})" if r["status"] == REVIEW_OPEN else ""))
    out(f"to: {', '.join(r['to'])}")
    if r.get("cc"):
        out(f"cc: {', '.join(r['cc'])}")
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
        _check_gone(mail, st, n, r)
        if r["status"] != REVIEW_OPEN and not everything:
            continue
        shown += 1
        out(f"#{n} [{r['status']}] {KIND_LABEL.get(r['kind'], r['kind'])}"
            + (f" {r['ref']}" if r.get("ref") else "") + f" → {', '.join(r['to'])} | {r['subject']} | "
            f"{_vn(r['opened_at'])}" + (f" | v{r['version']}" if r["version"] > 1 else "")
            + ("" if in_outlook(r) or r["status"] != REVIEW_OPEN else " | Telegram only"))
    if not shown:
        out("no drafts waiting for review" if not everything else "no reviews yet")
