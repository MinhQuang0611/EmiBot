"""Outlook access for sales@haya-hotels.com through Microsoft Graph. Draft-only.

Emi never sends (AGENTS.md rule 1). This module has no send method, and `_call` refuses any
Graph endpoint that sends, so a prompt can't talk its way into sending. The app registration
must also be granted Mail.Read + Mail.ReadWrite only, never Mail.Send (openclaw-setup-brief.md step 3).
"""
import base64
import html
import json
import os
import re
import time
import urllib.parse

from . import httpjson

GRAPH = "https://graph.microsoft.com/v1.0"
EMI_CATEGORY = "Emi"
APPROVED_CATEGORY = "Emi approved"  # a person pressed Accept on Telegram; still a draft until someone sends it

# Graph actions that send mail immediately. The create* versions only make drafts.
SEND_ACTIONS = {"send", "sendmail", "reply", "replyall", "forward"}

# Graph rejects inline attachments over 3 MB; larger ones need an upload session (not built).
MAX_INLINE_ATTACHMENT = 3 * 1024 * 1024


class SendBlocked(Exception):
    pass


class ClientCredentialsToken:
    """App-only token for an app registration scoped to the sales mailbox."""

    def __init__(self, tenant_id, client_id, client_secret, http=httpjson.request):
        self.url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        self.client_id = client_id
        self.client_secret = client_secret
        self.http = http
        self._token = None
        self._expires = 0

    def __call__(self):
        if not self._token or time.time() > self._expires - 300:
            resp = self.http("POST", self.url, form={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
            })
            self._token = resp["access_token"]
            self._expires = time.time() + int(resp.get("expires_in", 3600))
        return self._token


class DeviceCodeToken:
    """Delegated token, signed in once with a device code. No client secret.

    EMI_AUTH=device: personal Outlook.com test mailbox (tenant "consumers").
    EMI_AUTH=delegated: the HAYA tenant, signed in as sales@ itself (same pattern as Sunny).
    First run prints a link and a code to sign in with; the refresh token is cached in
    `cache_path` (mode 600) so later runs don't ask again. Scope is Mail.ReadWrite only, no Mail.Send.
    """

    SCOPE = "offline_access https://graph.microsoft.com/Mail.ReadWrite"

    def __init__(self, client_id, cache_path, tenant="consumers", http=httpjson.request, out=print):
        self.base = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0"
        self.client_id = client_id
        self.cache_path = cache_path
        self.http = http
        self.out = out
        self._token = None
        self._expires = 0

    def _read_cache(self):
        try:
            with open(self.cache_path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def _save(self, resp):
        self._token = resp["access_token"]
        self._expires = time.time() + int(resp.get("expires_in", 3600))
        # The access token is cached too (same 600 file), so a check every minute (tools.watch) reuses it for
        # its hour instead of redeeming the refresh token on every run.
        rt = resp.get("refresh_token") or self._read_cache().get("refresh_token")
        if rt:
            fd = os.open(self.cache_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"refresh_token": rt, "access_token": self._token, "expires_at": self._expires}, f)

    def _cached_access(self):
        c = self._read_cache()
        if c.get("access_token") and time.time() < float(c.get("expires_at", 0)) - 300:
            self._token, self._expires = c["access_token"], float(c["expires_at"])
            return True
        return False

    def signed_in_as(self):
        """The account the token belongs to (upn / preferred_username claim), lower-cased."""
        claims = jwt_claims(self())
        return (claims.get("upn") or claims.get("preferred_username") or "").lower()

    def _refresh(self):
        try:
            with open(self.cache_path, encoding="utf-8") as f:
                rt = json.load(f)["refresh_token"]
        except (OSError, ValueError, KeyError):
            return False
        try:
            self._save(self.http("POST", f"{self.base}/token", form={
                "client_id": self.client_id, "grant_type": "refresh_token",
                "refresh_token": rt, "scope": self.SCOPE}))
            return True
        except httpjson.HttpError:
            return False

    def _device_login(self):
        dc = self.http("POST", f"{self.base}/devicecode", form={"client_id": self.client_id, "scope": self.SCOPE})
        self.out(dc["message"])
        interval = int(dc.get("interval", 5))
        deadline = time.time() + int(dc.get("expires_in", 900))
        while time.time() < deadline:
            time.sleep(interval)
            try:
                self._save(self.http("POST", f"{self.base}/token", form={
                    "client_id": self.client_id, "device_code": dc["device_code"],
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code"}))
                return
            except httpjson.HttpError as e:
                if "authorization_pending" in e.body:
                    continue
                if "slow_down" in e.body:
                    interval += 5
                    continue
                raise
        raise RuntimeError("device code sign-in timed out")

    # Two-step sign-in for shells that kill background processes when a command ends:
    # start() saves the device code next to the cache and prints the message; once the person has
    # signed in, finish() redeems it. No process has to stay alive in between.
    def _pending_path(self):
        return self.cache_path + ".pending"

    def start(self):
        dc = self.http("POST", f"{self.base}/devicecode", form={"client_id": self.client_id, "scope": self.SCOPE})
        fd = os.open(self._pending_path(), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"device_code": dc["device_code"], "expires_at": time.time() + int(dc.get("expires_in", 900))}, f)
        self.out(dc["message"])

    def finish(self):
        """True once signed in; False while the person hasn't finished yet. Raises if expired or refused."""
        try:
            with open(self._pending_path(), encoding="utf-8") as f:
                pending = json.load(f)
        except (OSError, ValueError):
            pending = {}
        if "device_code" not in pending:
            raise RuntimeError("no pending sign-in; run the start step first")
        if time.time() > pending["expires_at"]:
            raise RuntimeError("the sign-in code expired; run the start step again")
        try:
            self._save(self.http("POST", f"{self.base}/token", form={
                "client_id": self.client_id, "device_code": pending["device_code"],
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code"}))
        except httpjson.HttpError as e:
            if "authorization_pending" in e.body or "slow_down" in e.body:
                return False
            raise
        # Redeemed: the device code is single-use, so blank the pending file (no delete needed).
        with open(self._pending_path(), "w", encoding="utf-8") as f:
            f.write("{}")
        return True

    def __call__(self):
        if not self._token or time.time() > self._expires - 300:
            if not self._cached_access() and not self._refresh():
                self._device_login()
        return self._token


def jwt_claims(token):
    """Payload of a JWT, unverified. Only used to show who signed in; {} if it isn't a JWT."""
    try:
        payload = token.split(".")[1]
        return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except (IndexError, ValueError):
        return {}


BULLET = re.compile(r"^\s*(?:[•*\-–])\s+")
# "Mã đoàn: #29519", "Lưu ý:" — a short label at the start of a line, bold in HAYA's sent emails.
LABEL = re.compile(r"^([^\s:*•\-–][^:]{0,34}?):(\s|$)")


def text_to_html(text):
    """Plain text to the HTML HAYA's own sent confirmations use: a blank line starts a paragraph,
    a single line break stays a <br>, **label** is bold, lines starting with •, -, * or – are a list."""
    def inline(s, labels=True):
        if s.strip().upper().startswith("[CHECK BEFORE SENDING"):
            # Tracy audit 29/10: bold red, no highlight; the person sending deletes it
            return f'<b><span style="color:#FF0000">{html.escape(s.strip())}</span></b>'
        if labels and "**" not in s:
            # Text written without markup still gets HAYA's bold labels.
            m = LABEL.match(s)
            if m and not re.search(r"https?$|\d$", m.group(1)):
                s = f"**{m.group(1)}:**{s[m.end(1) + 1:]}"
        return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(s))

    out = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.split("\n")
        para, items = [], []
        for line in lines + [None]:
            if line is not None and BULLET.match(line):
                if para:
                    out.append("<p>" + "<br>\n".join(para) + "</p>")
                    para = []
                items.append("<li>" + inline(BULLET.sub("", line), labels=False) + "</li>")
                continue
            if items:
                out.append("<ul>" + "".join(items) + "</ul>")
                items = []
            if line is not None:
                para.append(inline(line))
        if para:
            out.append("<p>" + "<br>\n".join(para) + "</p>")
    return "\n".join(out)


def _is_send_path(path):
    last = urllib.parse.urlparse(path).path.rstrip("/").rsplit("/", 1)[-1]
    return last.lower() in SEND_ACTIONS


def _recipients(addresses):
    return [{"emailAddress": {"address": a}} for a in addresses]


# Our own mailboxes. An email from one of these is staff, not a guest or agency: usually front office (haya@)
# forwarding a guest's mail into sales@. Replying to it would answer our own colleague.
INTERNAL_DOMAINS = ("haya-hotels.com", "palmahotel.vn")

_PREFIX = re.compile(r"^\s*(re|aw|sv|fw|fwd|tr|trả lời|chuyển tiếp)\s*:\s*", re.I)


def is_internal(address):
    a = (address or "").strip().lower()
    return any(a.endswith("@" + d) or a.endswith("." + d) for d in INTERNAL_DOMAINS)


def reply_subject(subject):
    """'Fw: RE: SI781659A - …' -> 'RE: SI781659A - …': one RE, no forward marks. Used when a reply goes to the
    original sender of a mail our own staff forwarded in, so the agency sees its own subject back."""
    s = subject or ""
    while True:
        t = _PREFIX.sub("", s)
        if t == s:
            return "RE: " + s.strip()
        s = t


class GraphMail:
    def __init__(self, mailbox, token, http=httpjson.request):
        # "me" = the signed-in personal test mailbox (DeviceCodeToken); otherwise app-only on a named mailbox.
        self.base = f"{GRAPH}/me" if mailbox == "me" else f"{GRAPH}/users/{urllib.parse.quote(mailbox)}"
        self.token = token
        self.http = http

    def _call(self, method, path, body=None, headers=None):
        if _is_send_path(path):
            raise SendBlocked(f"Emi does not send email: refused {method} {path}")
        url = path if path.startswith("https://") else self.base + path
        h = {"Authorization": f"Bearer {self.token()}"}
        h.update(headers or {})
        return self.http(method, url, headers=h, body=body)

    def _pages(self, path):
        resp = self._call("GET", path)
        yield from resp.get("value", [])
        while resp.get("@odata.nextLink"):
            resp = self._call("GET", resp["@odata.nextLink"])
            yield from resp.get("value", [])

    @staticmethod
    def _query(**params):
        return urllib.parse.urlencode({f"${k}": v for k, v in params.items()}, quote_via=urllib.parse.quote)

    # --- reading ---

    def list_folder_since(self, folder, since_iso, field="receivedDateTime"):
        """Messages in a well-known folder (inbox, drafts, sentitems) at or after since_iso (UTC, ...Z)."""
        q = self._query(
            filter=f"{field} ge {since_iso}",
            orderby=f"{field} asc",
            select="id,subject,from,toRecipients,receivedDateTime,sentDateTime,conversationId,hasAttachments,categories",
            top="50",
        )
        return list(self._pages(f"/mailFolders/{folder}/messages?{q}"))

    def get_message_bodies(self, message_id):
        """One message with body and uniqueBody (its own text, without the quoted history) as plain text."""
        q = self._query(select="id,subject,from,toRecipients,ccRecipients,sentDateTime,categories,body,uniqueBody")
        return self._call("GET", f"/messages/{message_id}?{q}", headers={"Prefer": 'outlook.body-content-type="text"'})

    def list_inbox_since(self, since_iso):
        return self.list_folder_since("inbox", since_iso)

    def list_sent_since(self, since_iso):
        return self.list_folder_since("sentitems", since_iso, field="sentDateTime")

    def search(self, text, top=10):
        """Messages anywhere in the mailbox matching text (subject, body, sender), newest first."""
        q = self._query(search=f'"{text.replace(chr(34), "")}"', select="id,subject,from,receivedDateTime,isDraft",
                        top=str(top))
        return [m for m in self._call("GET", f"/messages?{q}").get("value", []) if not m.get("isDraft")]

    def has_new_inbox_mail(self, since_iso):
        q = self._query(filter=f"receivedDateTime ge {since_iso}", select="id", top="1")
        return bool(self._call("GET", f"/mailFolders/inbox/messages?{q}").get("value"))

    def list_drafts(self, only_emi=False):
        q = self._query(select="id,subject,toRecipients,createdDateTime,lastModifiedDateTime,categories,conversationId", top="50")
        drafts = list(self._pages(f"/mailFolders/drafts/messages?{q}"))
        if only_emi:
            drafts = [d for d in drafts if EMI_CATEGORY in d.get("categories", [])]
        return drafts

    def get_message_text(self, message_id):
        return self._call("GET", f"/messages/{message_id}",
                          headers={"Prefer": 'outlook.body-content-type="text"'})

    def get_thread(self, conversation_id, text=False):
        """Every message in the conversation, oldest first. text=True: bodies as plain text,
        plus uniqueBody (the part not quoted from earlier messages)."""
        if text:
            q = self._query(filter=f"conversationId eq '{conversation_id}'",
                            select="id,subject,from,toRecipients,ccRecipients,receivedDateTime,isDraft,"
                                   "hasAttachments,body,uniqueBody")
            msgs = self._text_pages(f"/messages?{q}")
        else:
            q = self._query(filter=f"conversationId eq '{conversation_id}'")
            msgs = self._pages(f"/messages?{q}")
        return sorted(msgs, key=lambda m: m.get("receivedDateTime", ""))

    def _text_pages(self, path):
        h = {"Prefer": 'outlook.body-content-type="text"'}
        resp = self._call("GET", path, headers=h)
        yield from resp.get("value", [])
        while resp.get("@odata.nextLink"):
            resp = self._call("GET", resp["@odata.nextLink"], headers=h)
            yield from resp.get("value", [])

    def list_attachments(self, message_id):
        """File attachments with decoded bytes under 'data'. Inline logos come back too; caller filters."""
        out = []
        for a in self._pages(f"/messages/{message_id}/attachments"):
            if a.get("@odata.type") == "#microsoft.graph.fileAttachment" and a.get("contentBytes"):
                a = dict(a, data=base64.b64decode(a["contentBytes"]))
            out.append(a)
        return out

    list_draft_attachments = list_attachments

    # --- drafting (never sending) ---

    def _tag(self, draft_id):
        self._call("PATCH", f"/messages/{draft_id}", body={"categories": [EMI_CATEGORY]})

    def create_reply_draft(self, message_id, comment, reply_all=False):
        """Draft a reply on the sender's thread. `comment` sits above the quoted thread."""
        action = "createReplyAll" if reply_all else "createReply"
        draft = self._call("POST", f"/messages/{message_id}/{action}", body={"comment": comment})
        self._tag(draft["id"])
        return draft

    def create_forward_draft(self, message_id, to, comment):
        draft = self._call("POST", f"/messages/{message_id}/createForward",
                           body={"toRecipients": _recipients(to), "comment": comment})
        self._tag(draft["id"])
        return draft

    def _prepend_text(self, draft_id, text):
        """Put the text above the quoted thread of a fresh reply/forward draft, formatted by text_to_html."""
        draft = self._call("GET", f"/messages/{draft_id}?$select=body")
        original = draft.get("body", {}).get("content", "")
        ours = ('<div style="font-family:Calibri,Arial,sans-serif;font-size:11pt">'
                + text_to_html(text) + "</div><br>\n")
        m = re.search(r"<body[^>]*>", original, re.I)
        content = original[:m.end()] + ours + original[m.end():] if m else ours + original
        self._call("PATCH", f"/messages/{draft_id}", body={"body": {"contentType": "HTML", "content": content}})

    def reply_draft_with_text(self, message_id, text, reply_all=False, to=None, cc=None):
        """Reply draft on the sender's thread with a multi-line plain-text answer on top.
        to=[...] replaces the recipients Graph picked (createReply answers whoever sent the message, which for a
        mail forwarded in by our own front office is front office): To and Cc become exactly to / cc, and the
        subject becomes 'RE: <original subject>' without the 'Fw:'."""
        draft = self.create_reply_draft(message_id, "", reply_all=reply_all)
        if to:
            fields = {"toRecipients": _recipients(to), "ccRecipients": _recipients(cc or [])}
            if draft.get("subject"):
                fields["subject"] = reply_subject(draft["subject"])
            self._call("PATCH", f"/messages/{draft['id']}", body=fields)
        self._prepend_text(draft["id"], text)
        return draft

    def forward_draft_with_text(self, message_id, to, text):
        draft = self.create_forward_draft(message_id, to, "")
        self._prepend_text(draft["id"], text)
        return draft

    def create_new_draft(self, to, subject, body_text, cc=()):
        """A new email (not a reply): Odeon's confirmation and decline go out this way (tour-operators.md)."""
        html_body = ('<div style="font-family:Calibri,Arial,sans-serif;font-size:11pt">'
                     + text_to_html(body_text) + "</div>")
        draft = self._call("POST", "/messages", body={
            "subject": subject,
            "body": {"contentType": "HTML", "content": html_body},
            "toRecipients": _recipients(to),
            "ccRecipients": _recipients(cc),
            "categories": [EMI_CATEGORY],
        })
        return draft

    def update_draft(self, draft_id, **fields):
        """PATCH a draft Emi owns, e.g. a refreshed deposit deadline in the body."""
        draft = self._call("GET", f"/messages/{draft_id}?$select=isDraft,categories")
        if not draft.get("isDraft") or EMI_CATEGORY not in draft.get("categories", []):
            raise PermissionError(f"{draft_id} is not an unsent Emi draft; leaving it alone")
        return self._call("PATCH", f"/messages/{draft_id}", body=fields)

    def get_draft(self, draft_id):
        """The draft, or None when it is gone from Drafts (a person sent or deleted it in Outlook)."""
        try:
            d = self._call("GET", f"/messages/{draft_id}?$select=id,subject,toRecipients,isDraft,categories,"
                                  "hasAttachments,parentFolderId")
        except httpjson.HttpError as e:
            if e.status == 404:
                return None
            raise
        return d if d.get("isDraft") else None

    def _own_draft(self, draft_id):
        d = self.get_draft(draft_id)
        if d is None:
            raise PermissionError(f"{draft_id} is no longer in Drafts: a person sent or deleted it")
        if EMI_CATEGORY not in d.get("categories", []):
            raise PermissionError(f"{draft_id} is not an Emi draft; leaving it alone")
        return d

    def approve_draft(self, draft_id):
        """Tag the draft 'Emi approved' so whoever opens Drafts sees it was reviewed. It is not sent."""
        d = self._own_draft(draft_id)
        cats = [c for c in d.get("categories", []) if c != APPROVED_CATEGORY] + [APPROVED_CATEGORY]
        self._call("PATCH", f"/messages/{draft_id}", body={"categories": cats})

    def delete_draft(self, draft_id):
        """Remove an Emi draft from Drafts. Outlook keeps it in Deleted Items, so a person can get it back."""
        self._own_draft(draft_id)
        self._call("DELETE", f"/messages/{draft_id}")

    def add_attachment(self, draft_id, name, data, content_type="application/pdf"):
        if len(data) > MAX_INLINE_ATTACHMENT:
            raise ValueError(f"{name} is {len(data)} bytes; over 3 MB needs an upload session (not built)")
        return self._call("POST", f"/messages/{draft_id}/attachments", body={
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": name,
            "contentType": content_type,
            "contentBytes": base64.b64encode(data).decode(),
        })
