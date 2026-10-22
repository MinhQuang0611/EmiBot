"""What each intake-sheet column takes, and a check of a row before it is written.

The sheet itself is the source of truth for the words: row 2 (column instructions), the
"Room codes" tab (the room_code dropdown) and the "Rules" tab are read live by `sheet-schema`.
This file holds only what code can check: which columns are per booking or per room type,
allowed values, formats, and the required-field rule from the Rules tab.
"""
import re
import urllib.parse
from datetime import datetime

# Columns that differ between the rows of one booking (one row per room type). Everything else is shared.
ROOM_LEVEL = ("room_code", "rooms", "adults", "children", "child_ages", "meal_plan", "rate_source",
              "rate_per_night_vnd", "discount_promo", "Average rate per night after discount", "surcharge",
              "Surcharge amount", "total_vnd", "notes", "Remaining amount")
# Filled by someone else, never by Emi on a new row.
NOT_EMI = ("ezfolio_group_code", "tracy_status", "pdf_link")
# Filled later from payment slips (sheet-update), not when the booking first arrives.
PAYMENT = ("COD", "Payment 1", "Payment 1 date + time", "Payment 2", "Payment 2 date + time")

# Rules tab: "on every booking row (NEW or CHANGE) ... must NEVER be blank", else named in missing_info.
REQUIRED_BOOKING_ROW = ("company", "arrival", "departure", "room_code", "rooms", "rate_per_night_vnd",
                        "Average rate per night after discount")
ALWAYS = ("action", "received_at", "source_email", "property", "channel_type", "booking_ref",
          "guest_names", "nationality", "status", "priority")

ENUMS = {
    "action": ("NEW", "CHANGE", "CANCEL"),
    "property": ("HAYA",),  # Palma is not Emi's (AGENTS.md rule 11)
    "channel_type": ("TA", "OTA", "Direct", "Tour operator"),
    # "<operator> contract" for every tour operator with a contract this season (booking-intake.md, Rates).
    # Fun and Sun has none. The sheet's own instruction still lists only "Anex contract".
    "rate_source": ("TA card", "Anex contract", "Odeon contract", "Pegas contract", "Crystal Bay contract",
                    "Selfie contract", "OTA net", "Special (Karen)", "Other"),
    "status": ("Definite", "Tentative", "Cancelled"),
    "priority": ("Normal", "Urgent"),
}
PREFIX_ENUMS = {"prepaid": ("Yes", "No")}  # "Yes (paid on OTA)", "No (agency invoice)" are fine
DATES = ("arrival", "departure", "hold_until")
DATETIMES = ("received_at",)
INTEGERS = ("nights", "rooms", "adults", "children")
AMOUNTS = ("rate_per_night_vnd", "Average rate per night after discount", "Surcharge amount", "total_vnd",
           "Payment 1", "Payment 2", "Remaining amount")
AGENCY_CHANNELS = ("TA", "Tour operator")
RATE_FLOOR = 1_000_000  # VND per room-night; an OTA rate under it is flagged (MEMORY, inbox-triage.md §3)
NEVER_FOR_AGENCIES = ("TW-DLX",)  # MEMORY: never TW-DLX or APT to agencies
# Where the detail goes instead, added to an enum error ("Tour operator (Anex)", "OTA net (Expedia remittance)").
ENUM_HINTS = {"channel_type": "; the operator's or OTA's name goes in company",
              "rate_source": "; how the rate was worked out goes in notes item 6"}

# One spelling per channel in `company`: the tour operators and OTAs named in MEMORY.md (2026-10-09).
# The sheet wants the name "exactly as in Ezfolio"; Karen has not confirmed these against EZFOLIO's list yet.
# Values: other spellings seen or likely, written the way _norm() leaves them.
CANONICAL_COMPANIES = {
    "Anex": ("anex tour", "anextour"),
    "Odeon": ("odeon tours",),
    "Pegas": ("pegas touristik", "pegast"),
    "Crystal Bay": ("crystalbay",),
    "Selfie": ("selfie travel",),
    "Fun and Sun": ("fun sun", "funsun", "funandsun"),
    "Booking.com": ("booking com",),
    "Agoda": (),
    "Expedia": (),
    "Trip.com": ("trip com", "ctrip"),
    "Traveloka": (),
    "MG": ("mg bedbank", "mgbedbank", "mg holiday", "mg holidays"),
    "Ohmyhotel": ("oh my hotel",),
    "MakeMyTrip": ("make my trip",),
    "Dida Travel": ("dida",),
    "Mytour": ("my tour",),
    "VNTrip": ("vn trip",),
    "SynXis": ("sabre synxis",),
}
# Dropped from the end of a company name before matching: "BOOKING.COM BV", "Agoda Company Pte Ltd".
LEGAL_SUFFIXES = {"bv", "ltd", "llc", "inc", "pte", "co", "company", "limited", "jsc", "gmbh", "corp",
                  "corporation", "plc", "sa", "ag"}
# nationality: full English country name. Codes seen or likely on vouchers, for the error message.
COUNTRY_CODES = {
    "VN": "Vietnam", "VNM": "Vietnam", "IN": "India", "IND": "India", "RU": "Russia", "RUS": "Russia",
    "KR": "South Korea", "KOR": "South Korea", "CN": "China", "CHN": "China", "TW": "Taiwan", "TWN": "Taiwan",
    "JP": "Japan", "JPN": "Japan", "MY": "Malaysia", "MYS": "Malaysia", "SG": "Singapore", "SGP": "Singapore",
    "TH": "Thailand", "THA": "Thailand", "PH": "Philippines", "PHL": "Philippines", "ID": "Indonesia",
    "IDN": "Indonesia", "HK": "Hong Kong", "HKG": "Hong Kong", "US": "United States", "USA": "United States",
    "UK": "United Kingdom", "GB": "United Kingdom", "GBR": "United Kingdom", "AU": "Australia",
    "AUS": "Australia", "CA": "Canada", "CAN": "Canada", "DE": "Germany", "DEU": "Germany", "GER": "Germany",
    "FR": "France", "FRA": "France", "KZ": "Kazakhstan", "KAZ": "Kazakhstan", "UZ": "Uzbekistan",
    "UZB": "Uzbekistan", "IR": "Iran", "IRN": "Iran", "IL": "Israel", "ISR": "Israel",
    "AE": "United Arab Emirates", "ARE": "United Arab Emirates", "UAE": "United Arab Emirates",
}
REF_EXAMPLE = "'1783017402 / 92777EF002717'"
NOTES_EXAMPLE = "'1. Booking.com – Ref 5374635524'"


def _norm(name):
    """'BOOKING.COM BV' -> 'bookingcom bv'; 'Fun&Sun' -> 'fun and sun'."""
    s = str(name).lower().replace("&", " and ").replace(".", "")
    return " ".join(re.sub(r"[^\w]+", " ", s).split())


_COMPANY_KEYS = {}
for _canon, _aliases in CANONICAL_COMPANIES.items():
    for _key in (_norm(_canon),) + _aliases:
        _COMPANY_KEYS[_key] = _canon


def _match_company(name):
    """(canonical name, extra words) for a known channel, else (None, '')."""
    words = _norm(name).split()
    while len(words) > 1 and words[-1] in LEGAL_SUFFIXES:
        words.pop()
    s = " ".join(words)
    for key in sorted(_COMPANY_KEYS, key=len, reverse=True):
        if s == key or s.startswith(key + " "):
            return _COMPANY_KEYS[key], s[len(key):].strip().title()
    return None, ""


def canonical_company(name):
    """The one spelling for a known channel, or None. 'ANEX KHABAROVSK' -> 'Anex', 'BOOKING.COM BV' -> 'Booking.com'.
    A known name followed by more words (an office, a city) still counts: the extra goes in notes item 1."""
    return _match_company(name)[0]


def ref_parts(booking_ref):
    """The separate reference numbers in one booking_ref: '1783017402 / 92777EF002717' -> both.
    For the duplicate check: an OTA email and its SynXis notice each carry one of them."""
    return [p.strip() for p in str(booking_ref).split(" / ") if p.strip()]


def _ref_problems(ref):
    found = []
    if re.search(r"[()]", ref):
        found.append("brackets")
    norm = _norm(ref)
    words = sorted({_COMPANY_KEYS[k] for k in _COMPANY_KEYS if re.search(rf"(?<!\w){re.escape(k)}(?!\w)", norm)})
    if words:
        found.append("the channel name " + "/".join(words))
    return found


def _notes_problems(rec, g):
    """NOTES RULE: exactly 7 lines, numbered 1. to 7., item 1 = '<company> – Ref <booking_ref>'."""
    lines = [x.strip() for x in g("notes").splitlines() if x.strip()]
    nums = [m.group(1) for m in (re.match(r"([0-9]+)\.\s", x) for x in lines) if m]
    if nums != list("1234567") or len(lines) != 7:
        return [f"notes: NOTES RULE wants exactly 7 lines numbered '1. ' to '7. ', one item per line "
                f"(found {len(lines)} line(s), numbered {nums or 'none'}); format in booking-intake.md"]
    want = []
    if g("company") and not lines[0][3:].startswith(g("company")):
        want.append(f"start with the company {g('company')!r}")
    if g("booking_ref") and f"Ref {g('booking_ref')}" not in lines[0]:
        want.append(f"contain 'Ref {g('booking_ref')}'")
    if want:
        return [f"notes: item 1 should " + " and ".join(want) + f", e.g. {NOTES_EXAMPLE}"]
    return []


def _blank(v):
    return not str(v if v is not None else "").strip()


def _date(v, fmt):
    try:
        return datetime.strptime(str(v).strip(), fmt)
    except ValueError:
        return None


def check_row(rec, room_codes=None):
    """(errors, warnings) for one row. Errors block the write; warnings are printed."""
    errors, warnings = [], []
    g = lambda k: str(rec.get(k, "") if rec.get(k) is not None else "").strip()
    action = g("action")
    note = g("missing_info")
    built = g("tracy_status") in ("Entered", "Problem")  # the build tool has been at this row

    # 2026-10-22, row 79: only source_email "s", typed by hand. Not a booking; say so instead of 9 errors.
    filled = [k for k in rec if k != "_row" and g(k) and not (k == "tracy_status" and g(k) == "Pending")]
    if len(filled) <= 2:
        return ([f"row: only {len(filled)} cell(s) filled ({', '.join(filled) or 'none'}) — an accidental "
                 f"partial write, not a booking. Write the whole booking with sheet-append; a stray row "
                 f"already on the sheet goes to Karen to delete"], [])

    for k in ALWAYS:
        if k == "booking_ref" and g("channel_type") == "Direct":
            continue  # a direct guest has no agency code
        if k == "nationality" and "nationality" in note.lower():
            continue  # only a source market / residence given: blank, named in missing_info
        if _blank(rec.get(k)):
            errors.append(f"{k}: never blank" + {
                "guest_names": " (TBA if names not given)",
                "nationality": " — from the passport or nationality field (or the names); if the email gives "
                               "only a market or country of residence, write 'nationality – only source market "
                               "<X> given' in missing_info"}.get(k, ""))
    direct = g("channel_type") == "Direct"
    if direct and g("company"):
        # 2026-10-22: row 57 had the guest's own name as company and "new company" in missing_info
        errors.append("company: blank for a Direct booking (an individual, no company); "
                      "the sender's name goes in contact_person")
    if direct and "new company" in note.lower():
        errors.append("missing_info: no 'new company' on a Direct booking — there is no company")
    if action in ("NEW", "CHANGE"):
        for k in REQUIRED_BOOKING_ROW:
            # Direct: company stays blank but is still named in missing_info — the sheet says never blank,
            # and which EZFOLIO account direct guests go under is Karen's to say.
            if _blank(rec.get(k)) and k not in note:
                errors.append(f"{k}: required on a {action} row. Fill it, or write "
                              f"'REQUIRED blank: {k} – <reason>' in missing_info")
    if action in ("CHANGE", "CANCEL"):
        if _blank(rec.get("what_changed")):
            errors.append(f"what_changed: required for {action} (CANCEL: the reason)")
        if _blank(rec.get("ezfolio_group_code")) and "ezfolio_group_code" not in note:
            errors.append(f"ezfolio_group_code: required for {action}; if unknown, name it in missing_info")

    for k, allowed in ENUMS.items():
        if g(k) and g(k) not in allowed:
            errors.append(f"{k}: {g(k)!r} not allowed; use one of {list(allowed)}{ENUM_HINTS.get(k, '')}")
    for k, allowed in PREFIX_ENUMS.items():
        if g(k) and not g(k).startswith(allowed):
            errors.append(f"{k}: must start with {' or '.join(allowed)}")
    for k in DATES:
        # hold_until: an agency's time limit often has an hour ("07/10/2026 17:00"); dropping it would
        # make the hold look a day long. Arrival/departure are dates only.
        if g(k) and not _date(g(k), "%d/%m/%Y") and not (k == "hold_until" and _date(g(k), "%d/%m/%Y %H:%M")):
            errors.append(f"{k}: {g(k)!r} is not DD/MM/YYYY" + (" (or DD/MM/YYYY HH:MM)" if k == "hold_until" else ""))
    for k in DATETIMES:
        if g(k) and not _date(g(k), "%d/%m/%Y %H:%M"):
            errors.append(f"{k}: {g(k)!r} is not DD/MM/YYYY HH:MM (Vietnam time)")
    for k in INTEGERS:
        if g(k) and not g(k).isdigit():
            errors.append(f"{k}: {g(k)!r} must be a whole number")
    for k in AMOUNTS:
        if g(k) and not g(k).isdigit():
            errors.append(f"{k}: {g(k)!r} must be digits only, VND, no dots/commas (e.g. 2000000)")

    a, d = _date(g("arrival"), "%d/%m/%Y"), _date(g("departure"), "%d/%m/%Y")
    if a and d:
        if d <= a:
            errors.append("departure: must be after arrival")
        elif g("nights").isdigit() and int(g("nights")) != (d - a).days:
            errors.append(f"nights: {g('nights')} but arrival→departure is {(d - a).days}")
    if g("children").isdigit():
        ages = [x for x in re.split(r"\s*;\s*", g("child_ages")) if x]
        if int(g("children")) and ages and len(ages) != int(g("children")):
            errors.append(f"child_ages: {len(ages)} ages for {g('children')} children")
        if int(g("children")) == 0 and ages:
            errors.append("child_ages: must be blank when children is 0")

    if g("room_code"):
        if room_codes is not None and g("room_code") not in room_codes:
            errors.append(f"room_code: {g('room_code')!r} is not on the Room codes tab; use one of {sorted(room_codes)}")
        if g("room_code") in NEVER_FOR_AGENCIES and g("channel_type") in AGENCY_CHANNELS:
            errors.append(f"room_code: {g('room_code')} is never sold to agencies")
    if re.search(r"https?://|AAMk", g("source_email") + " " + g("notes")):
        errors.append("source_email/notes: no links or email IDs")
    for k in NOT_EMI:
        # Once the build tool has set Entered/Problem its own cells are filled; a later sheet-update
        # (a payment slip) must still pass. intake_sheet refuses Emi writing tracy_status/pdf_link anyway.
        if g(k) and not (k == "tracy_status" and g(k) == "Pending") and action == "NEW" and not built:
            errors.append(f"{k}: filled by the build tool, leave blank on a NEW row")

    # booking_ref: the reference number(s) only, so the duplicate check (exact match) and sheet-find
    # (substring) find the booking from either the OTA's email or its SynXis notice.
    ref_bad = _ref_problems(g("booking_ref")) if g("booking_ref") else []
    if ref_bad:
        msg = (f"booking_ref: {g('booking_ref')!r} has {' and '.join(ref_bad)} in it. Write the reference "
               f"number(s) only, two joined by ' / ', e.g. {REF_EXAMPLE}; the channel goes in company")
        if g("pdf_link") or built:
            # The confirmation record is keyed by booking_ref + row: renaming a built row could re-draft it.
            warnings.append(msg + " (row already built: leave it, Karen decides)")
        else:
            errors.append(msg)
    canon, extra = _match_company(g("company")) if g("company") and not direct else (None, "")
    if canon and g("company") != canon:
        warnings.append(f"company: {g('company')!r} is {canon!r} — write {canon!r}, one spelling per channel "
                        f"(the EZFOLIO name, Karen to confirm); a legal suffix (BV, Ltd) is dropped"
                        + (f", the office goes in notes item 1: '1. {canon} ({extra}) – Ref {g('booking_ref')}'"
                           if extra else ""))
    if canon == "SynXis":
        warnings.append("company: SynXis is the channel manager; write the OTA the notice names "
                        "(Booking.com, Expedia, Agoda…) and SynXis only if it names none")
    # 2026-10-22, row 63: "new company" on a Booking.com row. The named channels are already in EZFOLIO.
    if canon and re.search(r"\bnew company\b", note, re.I):
        errors.append(f"missing_info: no 'new company' — {canon} is a known channel already in EZFOLIO")

    # MEMORY rate floor: an OTA rate under 1,000,000 VND/room-night is likely a promotion mistake
    # (2026-10-22, rows 58 and 76: MG at 935,000 and 841,500, not flagged).
    if g("channel_type") == "OTA" and action in ("NEW", "CHANGE"):
        low = sorted({int(g(k)) for k in ("rate_per_night_vnd", "Average rate per night after discount")
                      if g(k).isdigit() and int(g(k)) < RATE_FLOOR})
        if low and "rate floor" not in note.lower():
            msg = (f"missing_info: OTA rate {' / '.join(f'{x:,}' for x in low)} VND/night is under the "
                   f"{RATE_FLOOR:,} floor; add 'rate floor: <rate> VND/night under 1,000,000 – likely "
                   f"promotion mistake' to missing_info so it reaches Karen")
            (warnings if built else errors).append(msg)
    for part in re.split(r"\s*[;,/]\s*", g("nationality")):
        if re.fullmatch(r"[A-Za-z]{2,3}", part):
            name = COUNTRY_CODES.get(part.upper())
            errors.append(f"nationality: {part!r} is a code; write the full English country name"
                          + (f" ({name!r})" if name else ""))

    if action in ("NEW", "CHANGE") and g("notes"):
        warnings += _notes_problems(rec, g)
    if action == "CANCEL" and g("notes") and not g("notes").startswith("Cancellation charge"):
        warnings.append("notes: a CANCEL row's notes is the one line 'Cancellation charge (<policy>): <amount> "
                        "VND — <days> days before check-in, <rule>. Paid: <amount>.' (booking-intake.md)")
    avg, rooms, nights, total = (g("Average rate per night after discount"), g("rooms"), g("nights"), g("total_vnd"))
    extra = g("Surcharge amount") or "0"
    if all(x.isdigit() for x in (avg, rooms, nights, total, extra)):
        want = int(avg) * int(rooms) * int(nights) + int(extra)
        if want != int(total):
            plus = f" + surcharge {extra}" if extra != "0" else ""
            warnings.append(f"total_vnd: {total} ≠ {avg} × {rooms} rooms × {nights} nights{plus} "
                            f"= {want}; fine only if the email states a different total")
    return errors, warnings


# --- live descriptions from the sheet ---

def _tab(sheet, tab, a1):
    rng = urllib.parse.quote(f"'{tab}'!{a1}", safe="")
    return sheet.call("GET", f"{sheet.base}/values/{rng}").get("values", [])


def room_codes(sheet, prop="HAYA"):
    """{code: (EZFOLIO name, agency note)} from the Room codes tab; None if the tab can't be read."""
    try:
        rows = _tab(sheet, "Room codes", "A2:D100")
    except Exception:
        return None
    codes = {r[0].strip(): (r[1] if len(r) > 1 else "", r[3] if len(r) > 3 else "")
             for r in rows if r and r[0].strip() and (len(r) < 3 or r[2].strip() in ("", prop))}
    return codes or None


def rules(sheet):
    try:
        return [r[0] for r in _tab(sheet, "Rules", "A2:A100") if r and r[0].strip()]
    except Exception:
        return []


def instructions(sheet):
    """Row 2 of the intake tab: header name -> instruction."""
    row = sheet.call("GET", f"{sheet.base}/values/{sheet._range('2:2')}").get("values", [[]])[0]
    return {h: (row[i].strip() if i < len(row) else "") for i, h in enumerate(sheet.header)}


def level(col):
    if col in NOT_EMI:
        return "build tool"
    if col in PAYMENT:
        return "payment (later)"
    return "room_lines" if col in ROOM_LEVEL else "booking"


def template(sheet, action="NEW"):
    """Empty booking JSON with every column Emi fills, split the way sheet-append takes it."""
    cols = [h for h in sheet.header if level(h) in ("booking", "room_lines")]
    booking = {h: "" for h in cols if level(h) == "booking"}
    booking.update(action=action, property="HAYA", priority="Normal")
    if action in ("CHANGE", "CANCEL"):
        booking.update(ezfolio_group_code="", what_changed="")
    line = {h: "" for h in cols if level(h) == "room_lines"}
    return {"booking": booking, "room_lines": [line]}
