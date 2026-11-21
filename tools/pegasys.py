"""Pegas provider site (Pegasys, provider.pegasys.pegast.com): Emi presses Confirm on a Pegas booking itself (dev,
2026-11-20: "giờ Emi cần tự confirm trên extranet Pegas"). Until now it was a person's job, a report line "Pegas <ref>:
đổi trạng thái trên provider.pegasys" (skills/tour-operators.md).

The requests are the ones captured on Palma's side, where they run for real since 11/11:
  1. GET  /Login                                  -> __RequestVerificationToken + cookie
  2. POST /Login {username, password, rememberMe} -> {"isSucceeded": true} + the login cookie
  3. GET  /HotelBookings/<bookingId>/<serviceGuid> -> data-version, #Status, #ConfirmationNumber
  4. POST /HotelServiceListView/Confirm           -> New -> Confirmed (Changed -> Confirmed changes)
  5. POST /HotelServiceEditView/UpdateConfirmationNumber
The serviceGuid is only in the link of the robot's mail (pegasys-notifications@pegast.su, "New reservation from Pegas
Touristik (#<id>, …)"). expectedVersion is read fresh before every write, and the page is read again after it.

When (Palma's rule, kept): only once HAYA's confirmation has gone to Pegas, never on a decline or a cancellation.
Here that is: the booking's latest robot notice, a mail from sales@ to Pegas after it with a file (the EZFOLIO PDF;
a before-PDF draft sent bare doesn't count), the booking built on the intake sheet and not cancelled, and the site
saying New or Changed. Anything else is left alone.

Reading (dev, 2026-11-20): every robot mail is only a link, and when Pegas's own "New booking #… for …" mail doesn't
come (11120333, 03/11) the page is the booking's only source. parse_details / render_details read it for intake:
`show` prints it under a robot mail, `pegas-booking <id>` on its own. Needs only the account, not EMI_PEGAS_CONFIRM.

Pressing is off unless EMI_PEGAS_CONFIRM=1 with EMI_PEGAS_USER / EMI_PEGAS_PASSWORD (secrets: .env on the host only).
Confirmation #: the EZFOLIO group code, as Palma does (dev, 2026-11-20: "trước tiên cứ ghi như Palma"): EMI_PEGAS_CONF_NO=group.
=conf writes the EZFOLIO confirmation no. instead; unset = the field is left as it is.
"""
import html
import http.cookiejar
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

from . import operators
from .graph_mail import is_internal

BASE = "https://provider.pegasys.pegast.com"
ROBOT = "pegasys-notifications@pegast.su"
LINK = re.compile(r"https?://provider\.pegasys\.pegast\.com/HotelBookings/(\d+)/([0-9A-Fa-f][0-9A-Fa-f-]{30,40}[0-9A-Fa-f])")
CONFIRMABLE = ("New", "Changed")
CONFIRMED = ("Confirmed", "Confirmed changes")
TIMEZONE = "-420"  # Vietnam, as the browser sends it
DAYS = 30          # robot notices this far back are looked at
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


class PegasysError(Exception):
    pass


def enabled():
    return os.environ.get("EMI_PEGAS_CONFIRM", "") == "1"


def conf_field():
    """'group' | 'conf' | '' (Karen hasn't said what goes in Confirmation #)."""
    v = os.environ.get("EMI_PEGAS_CONF_NO", "").strip().lower()
    return v if v in ("group", "conf") else ""


def from_env():
    user, password = os.environ.get("EMI_PEGAS_USER", ""), os.environ.get("EMI_PEGAS_PASSWORD", "")
    if not (user and password):
        raise PegasysError("EMI_PEGAS_USER / EMI_PEGAS_PASSWORD not set on the host")
    return Pegasys(user, password)


def _input_value(page, element_id):
    tag = re.search(rf'<input\b[^>]*\bid="{re.escape(element_id)}"[^>]*>', page, re.I)
    if not tag:
        return None
    v = re.search(r'\bvalue="([^"]*)"', tag.group(0), re.I)
    return html.unescape(v.group(1)).strip() if v else ""


def _token(page):
    tag = re.search(r'<input\b[^>]*\bname="__RequestVerificationToken"[^>]*>', page, re.I)
    v = re.search(r'\bvalue="([^"]*)"', tag.group(0), re.I) if tag else None
    return html.unescape(v.group(1)) if v else ""


def parse_booking(page):
    """{version, status, confirmation_number, token} from a booking page; None when it isn't one (the login page)."""
    art = re.search(r'<article\b[^>]*\bdata-version="([^"]*)"', page, re.I) or \
        re.search(r'\bdata-version="([^"]*)"', page, re.I)
    status = _input_value(page, "Status")
    if not art or status is None:
        return None
    return {"version": html.unescape(art.group(1)), "status": status,
            "confirmation_number": _input_value(page, "ConfirmationNumber") or "", "token": _token(page)}


def _plain(fragment):
    """Text of an HTML fragment, one line per block, blank lines dropped."""
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", fragment)
    s = re.sub(r"(?i)<br\s*/?>|</(div|li|p|tr|td|th)>", "\n", s)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    return [ln for ln in (re.sub(r"\s+", " ", x).strip() for x in s.split("\n")) if ln]


def _block(page, header):
    """The HTML of one k-block, from its k-header to the next block's header."""
    m = re.search(rf'<div class="k-header">\s*{re.escape(header)}\s*</div>(.*?)(?=<div class="k-header">|$)', page, re.S)
    return m.group(1) if m else ""


def _age(born, on):
    try:
        b, d = (datetime.strptime(x, "%d.%m.%Y").date() for x in (born, on))
    except ValueError:
        return None
    return d.year - b.year - ((d.month, d.day) < (b.month, b.day))


def parse_details(page):
    """Everything the booking page shows (dev, 2026-11-20: the robot's mail is only a link; when Pegas's own "New
    booking #… for …" mail doesn't come, as for 11120333 on 03/11, the page is the only source). No price and no
    allotment / on-request on the page."""
    head = parse_booking(page) or {}
    fields = {}
    for label, value in re.findall(r"<label[^>]*>(.*?)</label>\s*<div[^>]*>(.*?)</div>", _block(page, "Booking"), re.S):
        k, v = " ".join(_plain(label)), " ".join(_plain(value))
        fields.setdefault(k, v)
    requests = [" ".join(_plain(li)) for li in re.findall(r"<li[^>]*>(.*?)</li>", _block(page, "Special Requests"), re.S)]
    guests = []
    table = _block(page, "Guests")
    body = re.split(r"</thead>", table, maxsplit=1)[-1]
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.S):
        cells = [_plain(td) for td in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(cells) < 9:
            continue
        g = {"title": " ".join(cells[0]), "last": " ".join(cells[1]), "first": " ".join(cells[2]),
             "born": " ".join(cells[3]), "age": " ".join(cells[4]), "document": cells[5], "info": " ".join(cells[6]),
             "arrival": " ".join(cells[7]), "departure": " ".join(cells[8])}
        g["age_at_checkin"] = _age(g["born"], fields.get("Check-in", ""))
        guests.append(g)
    msgs = [x for x in _plain(re.split(r'<div[^>]*id="new-message-window"', _block(page, "Messages"))[0])
            if x not in ("New message", "No messages.", "Send")]
    return {**{k: v for k, v in head.items() if k != "token"}, "fields": fields, "requests": requests,
            "guests": guests, "messages": msgs}


CANCELLED = ("Cancellation request", "Cancelled", "Cancellation confirmed")


def render_details(booking_id, d):
    f = d["fields"]
    status = d.get("status", "?")
    out = [f"PEGASYS BOOKING {booking_id} — status on the site: {status}"
           + (" (CANCELLED BY PEGAS)" if status in CANCELLED or "cancel" in status.lower() else "")]
    out.append(f"Check-in {f.get('Check-in', '?')} → check-out {f.get('Check-out', '?')}, {f.get('Nights', '?')} nights")
    out.append(f"Room: {f.get('Room', '?')} | Accommodation: {f.get('Accommodation', '?')} | Meal: {f.get('Meal', '?')}")
    out.append(f"Market: {f.get('Market', '')} | Package: {f.get('Package', '')} | Booked {f.get('Booking date', '')}"
               f" | Last update {f.get('Last update', '')}")
    if d.get("confirmation_number"):
        out.append(f"Confirmation # on the site: {d['confirmation_number']}")
    out.append(f"Guests ({len(d['guests'])}; age at check-in from the date of birth):")
    for g in d["guests"]:
        doc = " ".join(g["document"])
        line = f"  {g['title']} {g['last']} {g['first']}, born {g['born']}"
        line += f" (age {g['age_at_checkin']} at check-in)" if g["age_at_checkin"] is not None else f" (age {g['age']})"
        line += f", document {doc}" if doc else ""
        line += f", arrival {g['arrival']}" if g["arrival"] else ""
        line += f", departure {g['departure']}" if g["departure"] else ""
        line += f", note: {g['info']}" if g["info"] else ""
        out.append(line)
    out.append("Special requests: " + ("; ".join(d["requests"]) if d["requests"] else "none"))
    out.append("Messages: " + (" / ".join(d["messages"]) if d["messages"] else "none"))
    out.append("NOT ON THE PAGE: the price (to-price --operator Pegas) and allotment / on request (Pegas's own "
               "'New booking #… for …' mail; none -> on request, skills/tour-operators.md step 5). The document's "
               "first word is the guest's citizenship.")
    return out


def find_link(mail, st, booking_id):
    """(booking_id, guid) of a booking from the robot links already read, else from the mailbox."""
    for v in (_rec(st)["links"].values() if st else ()):
        if v and v[0] == str(booking_id):
            return v[0], v[1]
    for m in mail.search(str(booking_id), top=25):
        found = LINK.search(html.unescape(mail.get_message_html(m["id"])))
        if found and found.group(1) == str(booking_id):
            return found.group(1), found.group(2)
    return None


class Pegasys:
    """One session on the provider site; the cookie jar lives as long as the object."""

    def __init__(self, user, password, base=BASE, opener=None, timeout=60):
        self.user, self.password, self.base, self.timeout = user, password, base.rstrip("/"), timeout
        self.opener = opener or urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.logged_in = False

    def _open(self, method, path, body=None, headers=None):
        h = {"User-Agent": UA, "Accept": "text/html,application/json,*/*"}
        h.update(headers or {})
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            h["Content-Type"] = "application/json; charset=utf-8"
        req = urllib.request.Request(self.base + path, data=data, headers=h, method=method)
        try:
            with self.opener.open(req, timeout=self.timeout) as resp:
                return resp.geturl(), resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            raise PegasysError(f"HTTP {e.code} on {method} {path}: "
                               f"{e.read().decode(errors='replace')[:300]}") from None

    def _post(self, path, body, token=""):
        h = {"X-Requested-With": "XMLHttpRequest", "ClientTimezone": TIMEZONE}
        if token:
            h["RequestVerificationToken"] = token
        _, text = self._open("POST", path, body, h)
        try:
            resp = json.loads(text) if text.strip() else {}
        except ValueError:
            raise PegasysError(f"{path}: not JSON ({text[:200]!r})") from None
        if not resp.get("isSucceeded"):
            raise PegasysError(f"{path}: {json.dumps(resp, ensure_ascii=False)[:300]}")
        return resp

    def login(self):
        _, page = self._open("GET", "/Login")
        token = _token(page)
        if not token:
            raise PegasysError("login page has no __RequestVerificationToken")
        self._post("/Login", {"username": self.user, "password": self.password, "rememberMe": True}, token)
        self.logged_in = True

    def booking(self, booking_id, guid):
        """The booking page's version, Status and Confirmation #; logs in first, or again once when the session
        ran out (the page comes back as the login form)."""
        if not self.logged_in:
            self.login()
        for attempt in (1, 2):
            url, page = self._open("GET", f"/HotelBookings/{booking_id}/{guid}")
            b = parse_booking(page)
            if b is not None:
                return b
            if attempt == 1 and ("/login" in url.lower() or "password" in page.lower()):
                self.login()
                continue
            break
        raise PegasysError(f"booking {booking_id}: page has no data-version / Status (link wrong or layout changed)")

    def details(self, booking_id, guid):
        """parse_details of the booking page (read only)."""
        self.booking(booking_id, guid)  # logs in, and again if the session ran out
        _, page = self._open("GET", f"/HotelBookings/{booking_id}/{guid}")
        return parse_details(page)

    def confirm(self, booking_id, guid, version, token=""):
        self._post("/HotelServiceListView/Confirm",
                   {"bookingId": int(booking_id), "hotelServiceGuid": guid, "expectedVersion": version,
                    "displayOptions": "SSRs, SpecialFares", "showHotelName": "False"}, token)

    def set_confirmation_number(self, booking_id, guid, version, number, last="", token=""):
        self._post("/HotelServiceEditView/UpdateConfirmationNumber",
                   {"bookingId": int(booking_id), "hotelServiceGuid": guid, "expectedVersion": version,
                    "confirmationNumber": number, "lastConfirmationNumber": last}, token)


# --- which bookings are due ---

def _iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rec(st):
    return st.data.setdefault("pegasys", {"links": {}, "bookings": {}})


def notices(mail, st, now, days=DAYS):
    """{booking_id: {guid, at, message_id, subject}} from the latest robot mail with a booking link, per booking.
    Each mail's link is read once and kept in the state (pegasys.links)."""
    rec = _rec(st)
    links = rec["links"]
    since = _iso(now - timedelta(days=days))
    latest = {}
    for m in mail.list_from_since(ROBOT, since):
        mid = m["id"]
        if mid not in links:
            found = LINK.search(html.unescape(mail.get_message_html(mid)))
            links[mid] = [found.group(1), found.group(2), m.get("receivedDateTime", "")] if found else None
        hit = links[mid]
        if not hit:
            continue
        bid, guid, at = hit[0], hit[1], m.get("receivedDateTime") or hit[2]
        if bid not in latest or at > latest[bid]["at"]:
            latest[bid] = {"guid": guid, "at": at, "message_id": mid, "subject": m.get("subject", "")}
    for mid in [k for k, v in links.items() if v and v[2] and v[2] < since]:
        del links[mid]  # older than the window: never looked at again
    return latest


def sent_confirmation(mail, booking_id, mailbox, after_iso, search_top=25):
    """The first mail from sales@ to an outside address, with a file, naming the booking, sent after the notice."""
    from .payments import REMINDER_SUBJECT, _addr, _list, search_ours
    for m in sorted(search_ours(mail, booking_id, top=search_top), key=lambda m: m.get("sentDateTime") or ""):
        sent = m.get("sentDateTime") or m.get("receivedDateTime") or ""
        if (_addr(m) != mailbox.lower() or not m.get("hasAttachments") or sent <= after_iso
                or REMINDER_SUBJECT.search(m.get("subject", ""))):
            continue
        full = mail.get_message_bodies(m["id"])
        if any(not is_internal(a) for a in _list(full.get("toRecipients"))):
            return {"id": m["id"], "sent_at": sent, "subject": m.get("subject", "")}
    return None


def due(mail, rows, state_of, st, mailbox, now, days=DAYS):
    """(items to press, lines to report). An item: {booking_id, guid, notice_at, sent, group, conf_no, ref}."""
    from .payments import BUILT_STATUSES
    items, lines = [], []
    done = _rec(st)["bookings"]
    for bid, n in sorted(notices(mail, st, now, days).items()):
        rec = done.get(bid) or {}
        if rec.get("notice_at", "") >= n["at"] and rec.get("status") in CONFIRMED + ("skipped",):
            continue  # already pressed (or left alone) for this notice
        ref = f"Pegas {bid}"
        state = state_of(rows, ref)
        if not state:
            lines.append(f"PEGAS {bid}: not on the intake sheet, not confirmed on Pegasys")
            continue
        if operators.cancelled(state):
            continue  # a cancellation is never pressed (Palma's rule)
        built = [r for r in state if (r.get("ez_status") or "").strip().lower() in BUILT_STATUSES
                 and (r.get("pdf_link") or "").strip()]
        if not built:
            continue  # not built yet: no confirmation can have gone
        sent = sent_confirmation(mail, bid, mailbox, n["at"])
        if not sent:
            continue  # the confirmation hasn't left sales@ yet
        group = next((v.strip().lstrip("#") for r in state for v in (r.get("ezfolio_group_code"), r.get("Group code"))
                      if (v or "").strip()), "")
        conf = next(((r.get("confirmation_no") or "").strip() for r in state if (r.get("confirmation_no") or "").strip()), "")
        items.append({"booking_id": bid, "guid": n["guid"], "notice_at": n["at"], "notice": n["subject"],
                      "sent": sent, "group": group, "conf_no": conf, "ref": state[0].get("booking_ref") or ref})
    return items, lines


# --- pressing ---

def wanted_number(item, field):
    return {"group": item.get("group", ""), "conf": item.get("conf_no", "")}.get(field, "")


def press(client, item, field="", dry_run=False):
    """Confirm one booking on the site and (field set) write its Confirmation #. Returns (status, line)."""
    bid, guid = item["booking_id"], item["guid"]
    b = client.booking(bid, guid)
    before = b["status"]
    if before not in CONFIRMABLE + CONFIRMED:
        return "skipped", f"PEGAS {bid}: Pegasys says '{before}', not pressed"
    if dry_run:
        return before, f"PEGAS {bid}: Pegasys '{before}'" + (" -> would press Confirm" if before in CONFIRMABLE else "")
    if before in CONFIRMABLE:
        client.confirm(bid, guid, b["version"], b["token"])
        b = client.booking(bid, guid)
        if b["status"] not in CONFIRMED:
            raise PegasysError(f"booking {bid}: pressed Confirm, the page still says '{b['status']}'")
    line = f"PEGAS {bid}: {before} -> {b['status']}" if before in CONFIRMABLE else f"PEGAS {bid}: already {before}"
    number = wanted_number(item, field)
    if not field:
        line += "; Confirmation # left as it is (what HAYA writes there: Karen)"
    elif not number:
        line += f"; Confirmation # not written: no {'group code' if field == 'group' else 'confirmation no.'} on the row"
    elif b["confirmation_number"] == number:
        line += f"; Confirmation # already {number}"
    else:
        client.set_confirmation_number(bid, guid, b["version"], number, b["confirmation_number"], b["token"])
        after = client.booking(bid, guid)
        if after["confirmation_number"] != number:
            raise PegasysError(f"booking {bid}: wrote Confirmation # {number}, the page says "
                               f"'{after['confirmation_number']}'")
        b = after
        line += f"; Confirmation # {number}"
    return b["status"], line


def run(items, client, st, field="", dry_run=False, tg=None, out=print):
    """Press every item; record each in the state; one Telegram line per booking pressed or failed."""
    from .telegram import esc
    done = _rec(st)["bookings"]
    for item in items:
        bid = item["booking_id"]
        try:
            status, line = press(client, item, field, dry_run)
        except (PegasysError, OSError) as e:
            line = f"PEGAS {bid}: NOT CONFIRMED on Pegasys, a person must press it ({e})"
            out(line)
            if tg and not dry_run and done.get(bid, {}).get("failed_for") != item["notice_at"]:
                done.setdefault(bid, {})["failed_for"] = item["notice_at"]
                _tg(tg, f"⚠️ {esc(line)}", "report")
            continue
        out(line)
        if dry_run:
            continue
        done[bid] = {"guid": item["guid"], "notice_at": item["notice_at"], "status": status,
                     "at": _iso(datetime.now(timezone.utc)), "sent_id": item["sent"]["id"], "ref": item["ref"]}
        if status != "skipped" and tg:
            _tg(tg, f"✅ {esc(line)}\n(thư xác nhận đã gửi {esc(item['sent']['sent_at'])}: {esc(item['sent']['subject'])})",
                "draft")
        elif tg:
            _tg(tg, f"ℹ️ {esc(line)}", "report")


def _tg(tg, text, topic):
    try:
        tg.send(text, topic=topic)
    except Exception:  # a failed notice never undoes a press; the line is in the run's output
        pass
