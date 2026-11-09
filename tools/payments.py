"""Which TA bookings owe money, which reminder is due, and which built bookings were never confirmed.

Karen, 2026-11-04: "Emi cũng đang không chase payment của khách nữa". The rules were written on 2026-10-08
(skills/confirmation-replies.md) but no command ever ran them, and job 2 was never switched on either.

The deposit clock starts when the confirmation really left sales@, so everything starts from the Sent mail: the first
message from the mailbox that carries the booking's group code. People also confirm from Outlook, so Emi's own draft
records aren't enough, and a code exists only once the booking is built, so no earlier mail can carry it.

Tour operators pay under their contract and OTAs are paid by the OTA: never chased. Direct guests pay 100% before
check-in and have no reminder rule (docs/rate-knowledge/direct.md).
"""
import re
import unicodedata
from datetime import date, datetime, time, timedelta, timezone

from . import intake_schema as schema
from . import operators
from .graph_mail import is_internal

VN = timezone(timedelta(hours=7))
DEPOSIT_HOURS = 48
REMIND_AT_HOURS = 40  # the deposit reminder goes 8 hours before the deadline
BALANCE_DAYS = 7      # balance due this many days before check-in; reminder the day before, from 09:00
FIRST_RUN_HOUR, LAST_RUN_HOUR = 7, 21  # the hourly check's window, Vietnam time
CONFIRM_FROM = date(2026, 10, 30)      # Emi's first day on the live sheet: older bookings were confirmed by hand
CHANGE_FROM = date(2026, 11, 5)        # changes built before this were confirmed by hand (dev, 05/11, Amara #30124)
SEARCH_TOP = 25


def _when(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(VN)


def _group(rows):
    return next((v for r in rows for v in (r.get("ezfolio_group_code"), r.get("Group code")) if (v or "").strip()), "")


def total_of(state):
    return sum(operators._amount(r.get("total_vnd")) for r in state)


def paid_of(hits, state):
    """What has been paid. The columns don't always say it on the latest rows (a CHANGE row with Payment 1 blank but
    Remaining halved, live row 1103), so: the most any one email's rows show as paid, or total − Remaining. Each
    email's own total − Remaining counts too: RHK BG15963 (07/11) paid 19,400,000 by 28/10 (rows 688–689, 40,200,000
    with 20,800,000 left), and the 04/11 change wrote Remaining on one room row only, so the latest rows alone said 0."""
    by_email, batches = {}, {}
    for r in hits:
        key = (r.get("action"), r.get("received_at"))
        by_email[key] = by_email.get(key, 0) + (operators._amount(r.get("Payment 1"))
                                                + operators._amount(r.get("Payment 2")))
        batches.setdefault(key, []).append(r)
    for (action, _), batch in batches.items():
        if action == "CANCEL" or not all(str(r.get("Remaining amount") or "").strip() for r in batch):
            continue  # a CANCEL row's Remaining is 0 with nothing paid
        by_email[(action, _)] = max(by_email[(action, _)], total_of(batch) - sum(
            operators._amount(r.get("Remaining amount")) for r in batch))
    paid = max(by_email.values(), default=0)
    left = [r.get("Remaining amount") for r in state]
    if left and all(str(x or "").strip() for x in left):
        paid = max(paid, total_of(state) - sum(operators._amount(x) for x in left))
    return min(paid, total_of(state))


BARE_DATE = re.compile(r"^(\d{2}/\d{2}/\d{4})(?: (\d{2}):(\d{2}))?$")
BALANCE_DATE = re.compile(r"balance[^;]*?(\d{2}/\d{2}/\d{4})", re.I)


# 'Deposit extended to 09/11/2026 17:00 (asked 07/11)', and the form written before deposit-extension existed:
# 'Deposit deadline extended to 12/11/2026 (agency request)' (Threeland 31-130127, 05/11), a date alone = 23:59.
EXTENDED = re.compile(r"^deposit (?:deadline )?extended to (\d{2}/\d{2}/\d{4})(?: (\d{2}):(\d{2}))?", re.I)
EXTEND_DAYS, EXTEND_HOUR = 2, 17


def extension_deadline(asked_at, wanted=None, current=None):
    """An agency asks to move its deposit deadline (dev, 2026-11-07): granted, no question to Karen. The new deadline
    is 17:00 two days after the day the request came (Sat 07/11 -> Mon 09/11 17:00), or the agency's own time when
    that is sooner. Never earlier than the deadline they already have. Returns (deadline, why)."""
    standard = datetime.combine(asked_at.date() + timedelta(days=EXTEND_DAYS), time(EXTEND_HOUR), tzinfo=VN)
    deadline, why = standard, f"17:00, {EXTEND_DAYS} days after the request ({asked_at:%d/%m})"
    if wanted is not None and asked_at < wanted < standard:
        deadline, why = wanted, "the time the agency asked for (sooner than the 2-day limit)"
    elif wanted is not None and wanted >= standard:
        why += f"; they asked for {wanted:%H:%M %d/%m/%Y}, later than the limit"
    if current is not None and current >= deadline:
        return current, f"their current deadline is already {current:%H:%M %d/%m/%Y}: nothing to move"
    return deadline, why


def fixed_deadline(cod):
    """A COD that is only a date ('06/11/2026', '17/10/2026 14:00'): the agreed deadline, not the 48-hour clock.
    Also an extension: 'Deposit extended to 09/11/2026 17:00 (asked 07/11); balance by 03/12/2026'."""
    cod = (cod or "").strip()
    m = EXTENDED.match(cod)
    if m:
        day = operators._date(m.group(1))
        clock = time(int(m.group(2)), int(m.group(3))) if m.group(2) else time(23, 59)
        return datetime.combine(day, clock, tzinfo=VN) if day else None
    m = BARE_DATE.match(cod)
    if not m:
        return None
    day = operators._date(m.group(1))
    if day is None:
        return None
    clock = time(int(m.group(2)), int(m.group(3))) if m.group(2) else time(23, 59)
    return datetime.combine(day, clock, tzinfo=VN)


def balance_date(cod, arrival):
    m = BALANCE_DATE.search(cod or "")
    return (operators._date(m.group(1)) if m else None) or arrival - timedelta(days=BALANCE_DAYS)


def lookahead(now):
    """After the last run of the day, a 40-hour mark falling overnight is drafted now: by morning it may be too late
    (confirmation-replies.md)."""
    if now.hour >= LAST_RUN_HOUR:
        return datetime.combine(now.date() + timedelta(days=1), time(FIRST_RUN_HOUR), tzinfo=VN) - now
    if now.hour < FIRST_RUN_HOUR:
        return datetime.combine(now.date(), time(FIRST_RUN_HOUR), tzinfo=VN) - now
    return timedelta()


def _addr(m):
    return ((m.get("from") or {}).get("emailAddress") or {}).get("address", "").lower()


def _text(full):
    return (full.get("body") or {}).get("content", "") or ""


def _list(recipients):
    return [r["emailAddress"]["address"] for r in recipients or [] if r.get("emailAddress", {}).get("address")]


def find_confirmation(mail, code, mailbox, parts=()):
    """{id, sent_at, to, cc, slips} for the first mail sales@ sent with this group code, or None. slips = what the
    agency has sent since with an attachment, which may be a payment the sheet doesn't show yet. The code may be only
    in the PDF (Anex 112970549, 04/11: the mail search finds it there, the body doesn't have it): then the mail must
    have an attachment and name the booking (parts = its reference numbers)."""
    hits = [m for m in mail.search(code, top=SEARCH_TOP)]
    when = lambda m: m.get("sentDateTime") or m.get("receivedDateTime") or ""
    ours = sorted((m for m in hits if _addr(m) == mailbox.lower()), key=lambda m: (not m.get("hasAttachments"), when(m)))
    for m in ours:
        full = mail.get_message_bodies(m["id"])
        words = f"{m.get('subject', '')} {_text(full)}".lower()
        if code not in _text(full) and not (m.get("hasAttachments") and any(p in words for p in parts)):
            continue  # the number matched inside something else
        sent = _when(when(m))
        slips = [x["id"] for x in hits if x.get("hasAttachments") and not is_internal(_addr(x))
                 and _addr(x) != mailbox.lower() and _when(when(x)) > sent]
        return {"id": m["id"], "sent_at": sent, "to": [a for a in _list(full.get("toRecipients")) if not is_internal(a)],
                "cc": _list(full.get("ccRecipients")), "slips": slips}
    return None


BACKFILL = "EXISTING BOOKING"
# The OTAs and B2B sites of the channel rule (MEMORY, 2026-10-09): paid by their own terms, never chased. The 05/11
# backfill wrote Ohmyhotel, MG, Mytour and Dida as "TA", and a CHANGE copies channel_type from the booking's rows.
OTA_COMPANIES = ("SynXis", "Agoda", "Expedia", "Trip.com", "Oh My Hotel", "MG", "MakeMyTrip", "Traveloka",
                 "Dida Travel", "Mytour", "VNTrip", "Booking.com")
# Karen via the dev, 2026-11-07, on draft #613 (Ohmyhotel V26062610072H01): "chase payment thì chỉ chase với công ty
# du lịch thôi. Các trang online không cần phải chase do có payment VCC rồi". The B2B sites of the stop-sell list
# (tools/stop_sales.py) and RezLive, which relays Ohmyhotel, pay by VCC too, even when a row calls them "TA".
B2B_KEYS = ("webbeds", "dotw", "hotelbeds", "hbx", "bedsonline", "tiket", "tiketcom", "rezlive", "travclan")
_OTA_KEYS = tuple(k for k, canon in schema._COMPANY_KEYS.items() if canon in OTA_COMPANIES) + B2B_KEYS


def ota_company(name):
    """An online site, never chased: 'MG', 'MY TOUR', 'CÔNG TY TNHH OHMYHOTEL&CO VN' (the name inside a legal name),
    'WebBeds FZ LLC' -> True. Only a travel company (TA) gets a payment reminder."""
    if schema.canonical_company(name or "") in OTA_COMPANIES:
        return True
    words = f" {schema._norm(name or '')} "
    return any(f" {k} " in words for k in _OTA_KEYS)


def own_state(rows, ref, parts_of):
    """The booking as Emi's own rows leave it, without the EZFOLIO backfill. The backfill of 05/11 19:46 (RER004,
    256 rows, action EXISTING BOOKING) has no COD and no payment columns: written after a booking's own rows it
    hid them (Mytour H6844730: NEW 'N/A (OTA prepaid)', then a backfill row 'TA'). [] when the backfill is all
    there is: a booking confirmed by hand months ago, whose payments the sheet never recorded (Ohmyhotel
    V26062610072H01, 07/11: a deposit reminder for a deadline of 29/06)."""
    mine = parts_of(ref)
    own = [r for r in rows if r.get("action") != BACKFILL and mine & parts_of(r.get("booking_ref"))]
    if not own:
        return []
    key = (own[-1].get("action"), own[-1].get("received_at"))
    state = []
    for r in reversed(own):
        if (r.get("action"), r.get("received_at")) != key:
            break
        state.insert(0, r)
    return state


def due(rows, state_of, parts_of, mail, st, mailbox, now):
    """Sorted by arrival. remind: reminders to draft now. slip: looks paid, read it first. no_confirmation: built, but
    no mail with the group code. overdue: deadline passed and its one reminder already went. short_notice: booked
    inside the 7 days, Karen sets the date. paid_unsent: a reminder in Drafts for a booking paid since. backfill: a
    TA booking known only from the EZFOLIO backfill, not chased (no payment record on the sheet)."""
    out = {"remind": [], "slip": [], "no_confirmation": [], "overdue": [], "short_notice": [], "paid_unsent": [],
           "backfill": []}
    soon = now + lookahead(now)
    for state in operators.bookings(rows, state_of):
        if any(r.get("action") == BACKFILL for r in state):
            backfill = state
            state = own_state(rows, (state[0].get("booking_ref") or "").strip(), parts_of)
            if not state:
                head = backfill[0]
                arrival = operators._date(head.get("arrival"))
                if (head.get("channel_type") == "TA" and not ota_company(head.get("company"))
                        and not operators.cancelled(backfill) and arrival and arrival > now.date()):
                    out["backfill"].append({"ref": (head.get("booking_ref") or "").strip(), "row": head["_row"],
                                            "company": head.get("company", ""), "arrival": arrival})
                continue
        head = state[0]
        ref = (head.get("booking_ref") or "").strip()
        arrival = operators._date(head.get("arrival"))
        if head.get("channel_type") != "TA" or ota_company(head.get("company")) or operators.cancelled(state) \
                or not arrival or arrival <= now.date():
            continue
        if (head.get("status") or "").strip() == "Tentative":
            continue
        mine = parts_of(ref)
        hits = [r for r in rows if mine & parts_of(r.get("booking_ref"))]
        code, total = _group(hits), total_of(state)
        if not code or not total or not any((r.get("pdf_link") or "").strip() for r in hits):
            continue  # not built: nobody has been told to pay yet
        paid = paid_of(hits, state)
        item = {"ref": ref, "row": head["_row"], "company": head.get("company", ""), "group": code, "total": total,
                "paid": paid, "arrival": arrival, "cod": head.get("COD", "")}
        if paid >= total:
            _flag_paid(st, mail, item, "deposit", out)
            _flag_paid(st, mail, item, "balance", out)
            continue
        cod = (head.get("COD") or "").strip()
        if cod.lower().startswith(("n/a", "paid in full")):
            continue
        if cod.lower().startswith("full payment"):
            out["short_notice"].append(item)
            continue
        fixed = fixed_deadline(cod)
        half = (total + 1) // 2
        if paid >= half:
            _flag_paid(st, mail, item, "deposit", out)
        balance_day = balance_date(cod, arrival)
        balance_from = datetime.combine(balance_day - timedelta(days=1), time(9), tzinfo=VN)
        if soon >= balance_from:
            which = "balance"
        elif paid < half:
            which = "deposit"
        else:
            continue
        sent = find_confirmation(mail, code, mailbox, mine)
        if sent is None:
            out["no_confirmation"].append(item)
            continue
        if which == "deposit":
            deadline = fixed or sent["sent_at"] + timedelta(hours=DEPOSIT_HOURS)
            if soon < deadline - timedelta(hours=DEPOSIT_HOURS - REMIND_AT_HOURS):
                continue
            passed = now > deadline
            words = f"{deadline:%H:%M} on {deadline:%d/%m/%Y}, Vietnam time (UTC+7)"
            amount = half - paid
        else:
            passed = now.date() > balance_day
            words = f"before {balance_day:%d/%m/%Y}"
            amount = total - paid
        item.update(which=which, amount=amount, deadline=words, passed=passed, sent=sent)
        if st.reminder_drafted(ref, which):
            if passed:
                out["overdue"].append(item)
            continue
        out["slip" if sent["slips"] else "remind"].append(item)
    for bucket in out.values():
        bucket.sort(key=lambda i: i["arrival"])
    return out


def _flag_paid(st, mail, item, which, out):
    """confirmation-replies.md: a slip has arrived and the reminder is still unsent → flag it for deletion."""
    entry = st.data["reminders"].get(f"{item['ref']}|{which}")
    if not entry or str(entry["draft_id"]).startswith("pending-") or mail.get_draft(entry["draft_id"]) is None:
        return
    out["paid_unsent"].append(dict(item, which=which, review=st.review_by_draft(entry["draft_id"])))


def _rooms(batch):
    """What a confirmation states: dates, room types and the total. A payment or a name changes none of these."""
    rooms = sorted((r.get("room_code") or "", r.get("rooms") or "") for r in batch if (r.get("rooms") or "") != "0")
    return batch[0].get("arrival"), batch[0].get("departure"), rooms, total_of(batch)


# Words in guest_names that aren't a name: titles, placeholders.
NOT_A_NAME = {"mr", "mrs", "ms", "miss", "mstr", "master", "dr", "chd", "child", "inf", "infant", "tba", "tbc", "tbu",
              "and", "va", "other", "others", "guest", "guests", "pax"}
PAYMENT_COLUMNS = ("Payment 1", "Payment 1 date + time", "Payment 2", "Payment 2 date + time")


def _plain(text):
    t = unicodedata.normalize("NFKD", (text or "").lower().replace("đ", "d"))
    return "".join(c for c in t if not unicodedata.combining(c))


def _names(batch):
    """The guests' names as a set of words: 'MR.PERIC/DRAGAN' = 'Dragan Peric', 'Lê' = 'Le'."""
    return {w for r in batch for w in re.findall(r"[a-z]+", _plain(r.get("guest_names")))
            if len(w) > 1 and w not in NOT_A_NAME}


def _pax(batch):
    if any(not (r.get("adults") or "").strip() for r in batch):
        return None  # a backfilled row without pax: unknown, not a change
    return sorted((r.get("room_code") or "", operators._amount(r.get("adults")), operators._amount(r.get("children")))
                  for r in batch)


def _meals(batch):
    meals = {(r.get("meal_plan") or "").strip().upper() for r in batch}
    return None if "" in meals else meals


def _paid(batch):
    return sorted(tuple((r.get(c) or "").strip() for c in PAYMENT_COLUMNS) for r in batch)


def _rooms_only(batch):
    return _rooms(batch)[:3]  # dates and rooms, without the total


def booking_changed(before, batch):
    """Did this email change what the agency booked: dates, rooms or total; or, with a payment left alone, the guests'
    names (dev 07/11: Ohmyhotel #27984, Mekong MVN29835, a name change built and never answered), pax or meal plan.
    Names given for a 'TBA' booking or added to a rooming list are not a change: the reply to those is job 1's."""
    if _rooms(batch) != _rooms(before):
        return True
    if _paid(batch) != _paid(before):
        return False  # a payment email; it was answered with the slip thank-you in job 1
    old, new = _names(before), _names(batch)
    if old and new and not old <= new:
        return True
    return any(a is not None and b is not None and a != b
               for a, b in ((f(before), f(batch)) for f in (_pax, _meals)))


def _batches(hits):
    batches = []
    for r in hits:
        key = (r.get("action"), r.get("received_at"))
        if batches and batches[-1][0] == key:
            batches[-1][1].append(r)
        else:
            batches.append((key, [r]))
    return batches


def last_change_pair(hits):
    """(rows before, rows of the last email that changed the booking), or (None, None). Each email writes the whole
    booking, so comparing one email's rows with the one before shows what really changed."""
    found = (None, None)
    batches = _batches(hits)
    for (_, before), (key, batch) in zip(batches, batches[1:]):
        if key[0] == "CHANGE" and booking_changed(before, batch):
            found = (before, batch)
    return found


def last_change(hits):
    """The rows of the last email that changed the booking (booking_changed); None if nothing did."""
    return last_change_pair(hits)[1]


# An OTA confirms its own guests; a person at a B2B or bed bank (Ohmyhotel's operations desk, WebBeds) who asked for a
# change waits for our answer. Guest relay addresses, robots and a guest's own mailbox are not that.
NOT_AN_AGENCY = re.compile(r"no-?reply|do-?not-?reply|notification|robot|@guest\.booking\.com|messaging|"
                           r"@(gmail|yahoo|hotmail|outlook|icloud|live|qq|163|mail|yandex)\.", re.I)


def asked_by_agency(batch):
    sender = (batch[0].get("company_email") or "").strip()
    return "@" in sender and not NOT_AN_AGENCY.search(sender)


def _codes(r):
    return {(r.get(c) or "").strip() for c in ("ezfolio_group_code", "Group code")} - {""}


def confirmed_since(mail, code, mailbox, since):
    """A mail from sales@ to the agency with an attachment since the change was built: Emi's draft sent, or a person's.
    Slips forwarded to accounting carry the code and a file too, so only mail to outside counts."""
    for m in mail.search(code, top=SEARCH_TOP):
        when = m.get("sentDateTime") or m.get("receivedDateTime") or ""
        if _addr(m) != mailbox.lower() or not m.get("hasAttachments") or _when(when) < since:
            continue
        if any(not is_internal(a) for a in _list(mail.get_message_bodies(m["id"]).get("toRecipients"))):
            return True
    return False


def built_at(batch):
    """When the build tool finished these rows (the sheet's time is Vietnam time). None until every row is done with
    its PDF. The PDF keeps its Drive link when it is remade, so ez_processed_at is the signal, not the link."""
    if any(r.get("ez_status") != "done" or not (r.get("pdf_link") or "").strip() for r in batch):
        return None
    try:
        return datetime.fromisoformat(max(r.get("ez_processed_at") or "" for r in batch)[:19]).replace(tzinfo=VN)
    except ValueError:
        return None


def _held(st, ref, row):
    """Job 2 stopped on this PDF (a mismatch, an invoice awaited) and told Karen: not every hour. A remade PDF has the
    same link and a new ez_processed_at."""
    hold = st.data["confirmation_holds"].get(ref)
    processed = row.get("ez_processed_at", "")
    return bool(hold) and hold.get("pdf_link") == row.get("pdf_link") and hold.get("processed", processed) == processed


def needs_confirmation(rows, state_of, parts_of, mail, st, mailbox, today):
    """Bookings built since Emi went live that sales@ hasn't confirmed: a NEW never confirmed, one line on its NEW row,
    or a change of dates, rooms or total built and not yet confirmed, one line on the change's first row (dev, 05/11:
    the reply to a change is the new confirmation with the PDF). An OTA confirms to the guest itself."""
    drafted = st.confirmation_drafted()
    done = {ref for ref, _ in drafted}
    out, groups_seen = [], set()
    for state in operators.bookings(rows, state_of):
        head = state[0]
        ref = (head.get("booking_ref") or "").strip()
        channel = head.get("channel_type") or ""
        arrival = operators._date(head.get("arrival"))
        ota = channel == "OTA"
        if not (ota or channel in ("TA", "Direct") or channel.startswith("Tour operator")) or operators.cancelled(state):
            continue
        if not arrival or arrival < today:
            continue
        mine = parts_of(ref)
        hits = [r for r in rows if mine & parts_of(r.get("booking_ref"))]
        code = _group(hits)
        if code:
            # Ohmyhotel #27984 (06/11): the name change went on the sheet under the group code as its ref, the
            # booking under the OTA number; both are one booking.
            mine_rows = {r["_row"] for r in hits}
            hits = [r for r in rows if r["_row"] in mine_rows or code in _codes(r)]
            if code in groups_seen:
                continue
            groups_seen.add(code)
        before, changed = last_change_pair(hits)
        if changed and code:
            since = built_at(changed)
            first = changed[0]
            if ota and not asked_by_agency(changed):
                continue
            if (since and since.date() >= CHANGE_FROM and not _held(st, ref, first)
                    and not any(row == r["_row"] for _, row in drafted for r in changed)
                    and not confirmed_since(mail, code, mailbox, since)):
                item = {"ref": ref, "row": first["_row"], "company": head.get("company", ""), "group": code,
                        "arrival": arrival, "subject": first.get("source_email", ""), "channel": channel,
                        "rows": [r["_row"] for r in changed], "total": total_of(changed),
                        "change": first.get("what_changed", "")}
                if _rooms_only(changed) == _rooms_only(before) and total_of(before) and total_of(changed) and \
                        total_of(changed) != total_of(before):
                    # Ohmyhotel #27984: a name change carried a provisional TA-card rate and the build tool put it
                    # into EZFOLIO, 1,487,500 -> 1,900,000. The PDF then matches the wrong row.
                    item["rate_moved"] = (total_of(before), total_of(changed))
                out.append(item)
            continue  # changed since the NEW: its first confirmation is not what is owed
        if ota or not total_of(state):
            continue
        if ref in done:
            continue
        new = next((r for r in hits if r.get("action") == "NEW" and (r.get("pdf_link") or "").strip()), None)
        if new is None:
            continue
        received = operators._date((new.get("received_at") or "").split(" ")[0])
        if not code or not received or received < CONFIRM_FROM or _held(st, ref, new):
            continue
        if find_confirmation(mail, code, mailbox, mine) is None:
            out.append({"ref": ref, "row": new["_row"], "company": head.get("company", ""), "group": code,
                        "arrival": arrival, "subject": new.get("source_email", ""), "channel": channel,
                        "rows": [r["_row"] for r in state], "total": total_of(state)})
    waiting = st.awaiting_pdf()
    for i in out:
        # a confirmation drafted before the PDF (dev, 07/11): job 2 puts the PDF on it, no second draft
        draft = next((d for (ref, row), d in waiting.items() if ref == i["ref"] and row in i["rows"]), None)
        if draft is None:
            # the build tool inserts rows above, so the row the draft was written on may have moved: the same booking
            # with one waiting draft is that draft (a second confirmation draft would be refused anyway)
            same = [d for (ref, _), d in waiting.items() if ref == i["ref"]]
            draft = same[0] if len(same) == 1 else None
        if draft:
            i["attach"] = st.review_by_draft(draft)
    return sorted(out, key=lambda i: i["arrival"])


def money(n):
    return f"{n:,.0f}"


def _safe(ref):
    return re.sub(r"[^A-Za-z0-9_-]+", "-", ref).strip("-")[:40]


def render(result, now):
    r = result
    out = [f"PAYMENTS {now:%d/%m/%Y %H:%M}: {len(r['remind'])} reminder(s) to draft, {len(r['slip'])} to read first, "
           f"{len(r['overdue'])} overdue after their reminder"]
    for label, bucket in (("REMIND", r["remind"]), ("READ FIRST", r["slip"])):
        for i in bucket:
            s = i["sent"]
            late = " LATE: deadline already passed, the reminder never went" if i["passed"] else ""
            kind = f"{i['which']}_reminder"
            out.append(f"{label} {i['which']} | {i['company']} | ref {i['ref']} | row {i['row']} | group #{i['group']} | "
                       f"total {money(i['total'])} | paid {money(i['paid'])} | amount due {money(i['amount'])} | "
                       f"deadline {i['deadline']} | confirmation sent {s['sent_at']:%d/%m/%Y %H:%M}{late}")
            if label == "READ FIRST":
                out.append(f"  mail with an attachment since the confirmation, may be the payment: show "
                           f"{' , show '.join(s['slips'])}. A slip → the usual CHANGE row + forward-slip, no reminder. "
                           f"Not a slip → the reminder below")
            cc = f" --cc {','.join(s['cc'])}" if s["cc"] else ""
            out.append(f"  draft-reply {s['id']} emi-work/out/{_safe(i['ref'])}-{i['which']}.txt --to "
                       f"{','.join(s['to'])}{cc} --kind {kind} --ref \"{i['ref']}\" --row {i['row']} --subject-suffix "
                       f"\"- PAYMENT REMINDER #{i['group']}\" (Vietnamese thread: \"- NHẮC THANH TOÁN #{i['group']}\")")
    for i in r["overdue"]:
        out.append(f"OVERDUE {i['which']} | {i['company']} | ref {i['ref']} | row {i['row']} | group #{i['group']} | "
                   f"amount due {money(i['amount'])} | deadline {i['deadline']}: reminder already drafted. Report to "
                   f"Karen; nothing cancelled, no second reminder")
    for i in r["short_notice"]:
        out.append(f"SHORT NOTICE | {i['company']} | ref {i['ref']} | row {i['row']} | group #{i['group']} | "
                   f"unpaid {money(i['total'] - i['paid'])} | arrival {i['arrival']:%d/%m/%Y}: booked inside 7 days, "
                   f"Karen sets the deadline. Report line")
    for i in r["no_confirmation"]:
        out.append(f"NO CONFIRMATION FOUND | {i['company']} | ref {i['ref']} | row {i['row']} | group #{i['group']}: "
                   f"built, unpaid, and no mail from sales@ has the group code, so the deposit clock hasn't started")
    for i in r["paid_unsent"]:
        out.append(f"PAID, REMINDER STILL IN DRAFTS | ref {i['ref']} | {i['which']} | draft #{i['review']}: report "
                   f"line 'deny #{i['review']}', so it isn't sent by mistake")
    if r.get("backfill"):
        refs = ", ".join(f"{i['ref']} ({i['company']}, {i['arrival']:%d/%m})" for i in r["backfill"])
        out.append(f"NOT CHASED, BACKFILL ONLY: {len(r['backfill'])} TA booking(s) known only from the EZFOLIO "
                   f"backfill (EXISTING BOOKING rows: confirmed by hand before, no payment record on the sheet): {refs}. "
                   f"One report line, no reminder")
    return "\n".join(out)


def render_confirmations(items):
    out = [f"CONFIRMATIONS DUE: {len(items)} booking(s) built and not confirmed from sales@"]
    for i in items:
        change = i.get("change")
        out.append(f"{'CONFIRM' if change is None else 'CONFIRM CHANGE'} | {i['channel']} | {i['company']} | ref {i['ref']} | row {i['row']} | group #{i['group']} | "
                   f"arrival {i['arrival']:%d/%m/%Y} | booking rows {', '.join(map(str, i['rows']))}, total "
                   f"{money(i['total'])}: the PDF covers all of them | original email: {i['subject']}"
                   + (f" | what changed: {change}" if change else ""))
        if i.get("attach"):
            out.append(f"  ATTACH: draft #{i['attach']} was written before the PDF. confirmation-attach {i['attach']}"
                       f" (the PDF, group code, confirmation no. and deposit deadline go on it; no new draft)")
        if i.get("rate_moved"):
            was, now = i["rate_moved"]
            out.append(f"  RATE MOVED {money(was)} → {money(now)} with the same dates and rooms. A price the agency or "
                       f"Karen agreed (what_changed says so) → confirm as usual. Anything else (a name or pax change "
                       f"that brought a provisional rate) → no draft: confirmation-hold {i['ref']} {i['row']} \"rate "
                       f"moved\" and ask-karen, the price in EZFOLIO may be wrong")
    return "\n".join(out)
