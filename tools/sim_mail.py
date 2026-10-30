"""A stand-in for GraphMail that reads test emails from .eml files and writes drafts to files.

Set EMI_SIM_DIR=<folder> and every tools.emi command works on <folder>/inbox/*.eml instead of
sales@: nothing is read from or written to the real mailbox. Drafts go to <folder>/drafts/, run
state to <folder>/state.json. The intake sheet is still the configured (sandbox) sheet.
Used to test NEW / CHANGE / CANCEL handling end to end without sending real emails.
"""
import glob
import hashlib
import json
import os
import re
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses, parseaddr, parsedate_to_datetime
from datetime import timezone

from .graph_mail import SendBlocked, reply_subject, text_to_html


def _thread_key(subject):
    s = subject or ""
    while True:
        t = re.sub(r"^\s*(re|fw|fwd|tr|trả lời|chuyển tiếp)\s*:\s*", "", s, flags=re.I)
        if t == s:
            return t.strip().lower()
        s = t


def _addr(pair):
    name, address = pair
    return {"emailAddress": {"name": name, "address": address}}


class SimMail:
    def __init__(self, folder):
        self.folder = folder
        self.drafts = os.path.join(folder, "drafts")
        self._messages = None

    # --- reading ---

    def _load(self):
        if self._messages is None:
            self._messages = {}
            for path in sorted(glob.glob(os.path.join(self.folder, "inbox", "*.eml"))):
                with open(path, "rb") as f:
                    msg = BytesParser(policy=policy.default).parse(f)
                mid = "sim-" + os.path.splitext(os.path.basename(path))[0]
                sent = parsedate_to_datetime(msg["Date"]).astimezone(timezone.utc)
                body = msg.get_body(preferencelist=("plain", "html"))
                text = body.get_content() if body else ""
                files = [p for p in msg.iter_attachments()]
                self._messages[mid] = {
                    "id": mid, "subject": str(msg["Subject"] or ""),
                    "from": _addr(parseaddr(str(msg["From"]))),
                    "toRecipients": [_addr(a) for a in getaddresses([str(msg["To"] or "")])],
                    "ccRecipients": [_addr(a) for a in getaddresses([str(msg["Cc"] or "")]) if a[1]],
                    "receivedDateTime": sent.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "conversationId": "sim-" + hashlib.sha1(_thread_key(str(msg["Subject"])).encode()).hexdigest()[:10],
                    "hasAttachments": bool(files), "isDraft": False,
                    "body": {"content": text}, "uniqueBody": {"content": text},
                    "_attachments": [{"@odata.type": "#microsoft.graph.fileAttachment", "name": a.get_filename(),
                                      "contentType": a.get_content_type(), "isInline": False,
                                      "data": a.get_payload(decode=True) or b""} for a in files],
                }
        return self._messages

    def _public(self, m):
        return {k: v for k, v in m.items() if not k.startswith("_")}

    def list_inbox_since(self, since_iso):
        # Every test email, oldest first; the run state's processed list keeps re-runs from repeating them.
        return sorted((self._public(m) for m in self._load().values()), key=lambda m: m["receivedDateTime"])

    def has_new_inbox_mail(self, since_iso):
        return bool(self._load())

    def get_message_text(self, message_id):
        return self._public(self._load()[message_id])

    def get_thread(self, conversation_id, text=False):
        return sorted((self._public(m) for m in self._load().values() if m["conversationId"] == conversation_id),
                      key=lambda m: m["receivedDateTime"])

    def list_attachments(self, message_id):
        return list(self._load()[message_id]["_attachments"])

    def search(self, text, top=10):
        t = text.lower()
        hits = [self._public(m) for m in self._load().values()
                if t in m["subject"].lower() or t in m["body"]["content"].lower()]
        return sorted(hits, key=lambda m: m["receivedDateTime"], reverse=True)[:top]

    # --- drafts, to files ---

    def _write_draft(self, kind, message_id, to, text, cc=(), subject=None):
        os.makedirs(self.drafts, exist_ok=True)
        n = len(glob.glob(os.path.join(self.drafts, "*.json"))) + 1
        did = f"sim-draft-{n:03d}"
        src = self._load().get(message_id, {})
        if subject is None:
            subject = src.get("subject", "")
            prefix = "RE: " if kind == "reply" else "FW: "
            if not subject.upper().startswith(prefix.strip()):
                subject = prefix + subject
        meta = {"id": did, "kind": kind, "in_reply_to": message_id, "subject": subject,
                "to": list(to), "cc": list(cc), "attachments": [], "text": text}
        with open(os.path.join(self.drafts, did + ".json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        cc_line = f"<br><b>Cc:</b> {', '.join(cc)}" if cc else ""
        with open(os.path.join(self.drafts, did + ".html"), "w", encoding="utf-8") as f:
            f.write(f"<p><b>To:</b> {', '.join(to)}{cc_line}<br><b>Subject:</b> {meta['subject']}</p>\n"
                    f"{text_to_html(text)}")
        return {"id": did}

    def reply_draft_with_text(self, message_id, text, reply_all=False, to=None, cc=None):
        """Same as GraphMail: to=[...] replaces the recipients and the subject loses its 'Fw:'."""
        m = self._load()[message_id]
        if to:
            return self._write_draft("reply", message_id, list(to), text, cc=list(cc or []),
                                     subject=reply_subject(m["subject"]))
        sender = m["from"]["emailAddress"]["address"]
        if reply_all:
            # as Graph's createReplyAll: the sender plus the other To, the Cc kept, the mailbox itself left out
            ours = os.environ.get("EMI_MAILBOX", "sales@haya-hotels.com").lower()
            to = [sender] + [a for a in (r["emailAddress"]["address"] for r in m.get("toRecipients", []))
                             if a.lower() not in (ours, sender.lower())]
            cc = [a for a in (r["emailAddress"]["address"] for r in m.get("ccRecipients", [])) if a.lower() != ours]
            return self._write_draft("reply", message_id, to, text, cc=cc)
        return self._write_draft("reply", message_id, [sender], text)

    def forward_draft_with_text(self, message_id, to, text):
        return self._write_draft("forward", message_id, list(to), text)

    def create_new_draft(self, to, subject, body_text, cc=()):
        return self._write_draft("new", None, list(to), body_text, cc=list(cc), subject=subject)

    def _meta(self, draft_id):
        path = os.path.join(self.drafts, draft_id + ".json")
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _save(self, meta):
        with open(os.path.join(self.drafts, meta["id"] + ".json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    def add_attachment(self, draft_id, name, data, content_type="application/pdf"):
        meta = self._meta(draft_id)
        with open(os.path.join(self.drafts, f"{draft_id}--{name}"), "wb") as f:
            f.write(data)
        meta["attachments"].append({"name": name, "contentType": content_type, "bytes": len(data)})
        self._save(meta)

    # --- review (tools.emi review-*) ---

    def get_draft(self, draft_id):
        meta = self._meta(draft_id)
        if meta is None or meta.get("deleted") or meta.get("sent"):
            return None
        return {"id": draft_id, "subject": meta["subject"], "isDraft": True,
                "toRecipients": [{"emailAddress": {"address": a}} for a in meta["to"]],
                "ccRecipients": [{"emailAddress": {"address": a}} for a in meta.get("cc", [])],
                "categories": meta.get("categories", ["Emi"]), "hasAttachments": bool(meta["attachments"])}

    def approve_draft(self, draft_id):
        meta = self._meta(draft_id)
        if meta is None or meta.get("deleted"):
            raise PermissionError(f"{draft_id} is no longer in Drafts")
        meta["categories"] = ["Emi", "Emi approved"]
        self._save(meta)

    def send_draft(self, draft_id):
        meta = self._meta(draft_id)
        if meta is None or meta.get("deleted") or meta.get("sent"):
            raise PermissionError(f"{draft_id} is no longer in Drafts")
        if "[check before sending" in meta.get("text", "").lower():
            raise SendBlocked(f"{draft_id} still has its [CHECK BEFORE SENDING] line; not sent")
        meta["sent"] = True  # kept on disk, like Outlook's Sent Items
        self._save(meta)

    def delete_draft(self, draft_id):
        meta = self._meta(draft_id)
        if meta is None or meta.get("deleted"):
            raise PermissionError(f"{draft_id} is no longer in Drafts")
        meta["deleted"] = True  # kept on disk, like Outlook's Deleted Items
        self._save(meta)

    def list_draft_attachments(self, draft_id):
        meta = self._meta(draft_id) or {"attachments": []}
        out = []
        for a in meta["attachments"]:
            with open(os.path.join(self.drafts, f"{draft_id}--{a['name']}"), "rb") as f:
                out.append({"@odata.type": "#microsoft.graph.fileAttachment", "name": a["name"],
                            "contentType": a["contentType"], "isInline": False, "data": f.read()})
        return out
