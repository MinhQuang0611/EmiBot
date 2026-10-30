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
# Filled by someone else, never by Emi on a new row. tracy_status was deleted from the live sheet on 12/10
# (Tracy audit 29/10): the build tool filling pdf_link is what marks a row built. The SANDBOX still has it.
NOT_EMI = ("ezfolio_group_code", "tracy_status", "pdf_link")
BUILT_STATUSES = ("Entered", "Problem")
# Filled later from payment slips (sheet-update), not when the booking first arrives.
PAYMENT = ("COD", "Payment 1", "Payment 1 date + time", "Payment 2", "Payment 2 date + time")

# Rules tab: "on every booking row (NEW or CHANGE) ... must NEVER be blank", else named in missing_info.
REQUIRED_BOOKING_ROW = ("company", "arrival", "departure", "room_code", "rooms", "rate_per_night_vnd",
                        "Average rate per night after discount", "adults", "meal_plan")
ALWAYS = ("action", "received_at", "source_email", "property", "channel_type", "booking_ref",
          "guest_names", "nationality", "status", "priority")

ENUMS = {
    "action": ("NEW", "CHANGE", "CANCEL"),
    "property": ("HAYA",),  # Palma is not Emi's (AGENTS.md rule 11)
    "channel_type": ("TA", "OTA", "Direct", "Tour operator"),
    # "<operator> contract" for every tour operator with a contract this season (booking-intake.md, Rates).
    # Fun and Sun has none. The sheet's own instruction still lists only "Anex contract".
    # Booking.com: the guest total (commission settled monthly); every other OTA: the net (live sheet, 2026-10-27).
    "rate_source": ("TA card", "Anex contract", "Odeon contract", "Pegas contract", "Crystal Bay contract",
                    "Selfie contract", "Booking.com guest total", "OTA net", "Special (Karen)", "Other"),
    "status": ("Definite", "Tentative", "Cancelled"),
    "priority": ("Normal", "Urgent"),
}
PREFIX_ENUMS = {"prepaid": ("Yes", "No")}  # "Yes (paid on OTA)", "No (agency invoice)" are fine
DATES = ("arrival", "departure", "hold_until")
DATETIMES = ("received_at",)
INTEGERS = ("nights", "rooms", "adults", "children")
AMOUNTS = ("rate_per_night_vnd", "Average rate per night after discount", "total_vnd",
           "Payment 1", "Payment 2", "Remaining amount")
# Surcharge amount carries the rounding difference too, which can be negative (Tracy audit 29/10: "-3").
SIGNED_AMOUNTS = ("Surcharge amount",)
AGENCY_CHANNELS = ("TA", "Tour operator")
NEVER_FOR_AGENCIES = ("TW-DLX",)  # MEMORY: never TW-DLX or APT to agencies
# Where the detail goes instead, added to an enum error ("Tour operator (Anex)", "OTA net (Expedia remittance)").
ENUM_HINTS = {"channel_type": "; the operator's or OTA's name goes in company",
              "rate_source": "; how the rate was worked out goes in notes item 6"}

# One spelling per channel in `company`: the tour operators and OTAs named in MEMORY.md (2026-10-09).
# The sheet wants the name "exactly as in Ezfolio"; Karen has not confirmed these against EZFOLIO's list yet.
# Values: other spellings seen or likely, written the way _norm() leaves them.
CANONICAL_COMPANIES = {
    "Anex": ("anex tour", "anextour"),
    # Odeon's contract also covers Coral Travel, Sunmar and Odeonbeds (docs/rate-knowledge/odeon.md);
    # the live sheet writes those bookings under Odeon (12169345 Vitkup, 2026-10-26), the brand in notes item 1.
    "Odeon": ("odeon tours", "odeonbeds", "coral travel", "sunmar"),
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
    "Oh My Hotel": ("ohmyhotel",),  # the live sheet's spelling; RezLive only relays its bookings
    "MakeMyTrip": ("make my trip",),
    "Dida Travel": ("dida",),
    "Mytour": ("my tour",),
    "VNTrip": ("vn trip",),
    "SynXis": ("sabre synxis",),
    # Wyndham Rewards free nights: company Wyndham, rate 0 (Monteiro, live sheet 2026-10-27).
    "Wyndham": ("wyndham rewards", "wyndham hotels and resorts"),
}
# Dropped from the end of a company name before matching: "BOOKING.COM BV", "Agoda Company Pte Ltd".
LEGAL_SUFFIXES = {"bv", "ltd", "llc", "inc", "pte", "co", "company", "limited", "jsc", "gmbh", "corp",
                  "corporation", "plc", "sa", "ag"}
# nationality: a 3-letter code, e.g. VNM (Karen, 29/10, via Tracy's audit). Codes and names seen or likely on
# vouchers, to suggest the code when a name or a 2-letter code is written.
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
# country name -> its 3-letter code: 'Vietnam' -> 'VNM'
NATIONALITY_CODES = {name.lower(): code for code, name in COUNTRY_CODES.items() if len(code) == 3 and code != "GER"}
NATIONALITY_CODES.update({"viet nam": "VNM", "korea": "KOR", "england": "GBR", "united states of america": "USA"})
NATIONALITY_FALLBACK = "VNM"  # no nationality and no clue in the names (Rules tab)
REF_EXAMPLE = "'1783017402 / 92777EF002717'"
NOTES_EXAMPLE = "'1. Booking.com – Ref 5374635524'"
NOTES_ITEMS = 8  # the EZFOLIO Notice, items 1-8; item 8 = VAT invoice (Tracy audit 29/10)


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
    """NOTES RULE: exactly 8 lines, numbered 1. to 8., item 1 = '<company> – Ref <booking_ref>',
    item 8 = '8. VAT invoice: …' or '8. No VAT info'."""
    lines = [x.strip() for x in g("notes").splitlines() if x.strip()]
    nums = [m.group(1) for m in (re.match(r"([0-9]+)\.\s", x) for x in lines) if m]
    if nums != [str(i) for i in range(1, NOTES_ITEMS + 1)] or len(lines) != NOTES_ITEMS:
        return [f"notes: NOTES RULE wants exactly {NOTES_ITEMS} lines numbered '1. ' to '{NOTES_ITEMS}. ', one item "
                f"per line (found {len(lines)} line(s), numbered {nums or 'none'}); format in booking-intake.md"]
    if not re.match(r"8\.\s+(VAT invoice:\s*\S|No VAT info\s*$)", lines[7]):
        return ["notes: item 8 is '8. VAT invoice: <company, MST, address, invoice email>' or '8. No VAT info'"]
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


def is_built(rec):
    """The build tool has been at this row: pdf_link filled (live sheet), or tracy_status Entered/Problem
    (SANDBOX, which still has the column)."""
    return bool(str(rec.get("pdf_link") or "").strip()) or str(rec.get("tracy_status") or "").strip() in BUILT_STATUSES


def nationality_problem(value):
    """None if every part is a 3-letter code ('VNM', 'VNM; RUS'), else what to write instead."""
    for part in (p for p in re.split(r"\s*[;,/]\s*", str(value).strip()) if p):
        if re.fullmatch(r"[A-Z]{3}", part):
            continue
        if re.fullmatch(r"[A-Za-z]{2,3}", part) and part.upper() in COUNTRY_CODES:
            code = NATIONALITY_CODES.get(COUNTRY_CODES[part.upper()].lower())
        else:
            code = NATIONALITY_CODES.get(part.lower())
        return (f"nationality: {part!r} — write the 3-letter code" + (f" {code!r}" if code else ", e.g. 'VNM'")
                + " (the booking's nationality, else the passport, else the guest's name, else VNM)")
    return None


def _date(v, fmt):
    try:
        return datetime.strptime(str(v).strip(), fmt)
    except ValueError:
        return None


def check_row(rec, room_codes=None, earlier_arrivals=None):
    """(errors, warnings) for one row. Errors block the write; warnings are printed.
    earlier_arrivals: the arrival dates on the booking's rows already on the sheet (a CHANGE's past arrival is
    fine when it is one of them: a guest in house, a payment after the stay); None = not looked up."""
    errors, warnings = [], []
    g = lambda k: str(rec.get(k, "") if rec.get(k) is not None else "").strip()
    action = g("action")
    note = g("missing_info")
    built = is_built(rec)

    # 2026-10-22, row 79: only source_email "s", typed by hand. Not a booking; say so instead of 9 errors.
    filled = [k for k in rec if k != "_row" and g(k) and not (k == "tracy_status" and g(k) == "Pending")]
    if len(filled) <= 2:
        return ([f"row: only {len(filled)} cell(s) filled ({', '.join(filled) or 'none'}) — an accidental "
                 f"partial write, not a booking. Write the whole booking with sheet-append; a stray row "
                 f"already on the sheet goes to Karen to delete"], [])

    for k in ALWAYS:
        if k == "booking_ref" and g("channel_type") == "Direct":
            continue  # a direct guest has no agency code
        if _blank(rec.get(k)):
            errors.append(f"{k}: never blank" + {
                "guest_names": " (TBA if names not given)",
                "nationality": f" — the booking's nationality, else the passport, else inferred from the guest's "
                               f"name; no clue at all: {NATIONALITY_FALLBACK}"}.get(k, ""))
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
    for k in SIGNED_AMOUNTS:
        if g(k) and not re.fullmatch(r"-?\d+", g(k)):
            errors.append(f"{k}: {g(k)!r} must be digits only, VND, a minus sign allowed for a rounding "
                          f"difference (e.g. 1050000, -3)")

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
        # A row read from the sheet carries _row; a row about to be written doesn't, so its pdf_link is Emi's.
        on_sheet = "_row" in rec or g("tracy_status") in BUILT_STATUSES
        if g(k) and not (k == "tracy_status" and g(k) == "Pending") and action == "NEW" and not on_sheet:
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

    if action in ("NEW", "CHANGE") and g("rate_source") in ("OTA net", "Booking.com guest total"):
        want = "Booking.com guest total" if canon == "Booking.com" else "OTA net"
        if g("rate_source") != want:
            errors.append(f"rate_source: {g('rate_source')!r} on a {g('company') or 'non-Booking.com'} row; write "
                          f"{want!r} (Booking.com pays the guest total, every other OTA the net)")
    received = _date(g("received_at"), "%d/%m/%Y %H:%M")
    if action in ("NEW", "CHANGE") and a and received and a.date() < received.date():
        # 2026-10-24, Footprint 211Q1126Y: "12 Nov" written as 12/11/2025
        wrong_year = (f"arrival: {g('arrival')} is before the email ({g('received_at')[:10]}). A date with no "
                      f"year is the next one after the email: check the year")
        if action == "NEW":
            errors.append(wrong_year)
        elif earlier_arrivals and g("arrival") not in earlier_arrivals:
            # audit 30/10 (F-04): an in-house guest's update or a payment after the stay keeps the booking's own
            # arrival; only a CHANGE that brings a new arrival in the past is a typo
            errors.append(wrong_year + f"; the booking's earlier rows arrive {', '.join(sorted(earlier_arrivals))}")
        elif not earlier_arrivals:
            warnings.append(wrong_year + " (fine for a guest in house or a payment after the stay)")
    if action in ("NEW", "CHANGE") and g("status") == "Tentative" and not g("hold_until"):
        warnings.append("status: Tentative is only for a hold the sender asked for, with its time limit in "
                        "hold_until; a booking request or voucher is Definite")
    # audit 30/10 (F-05, rows 302-303, 374): Indian guests on the TA card without the +20%
    if (action in ("NEW", "CHANGE") and not built and g("channel_type") == "TA" and g("rate_source") == "TA card"
            and g("nationality").upper() in ("IND", "INDIA", "INDIAN") and "20%" not in g("surcharge")
            and not re.search(r"indian|ấn độ|\+20%", note, re.I)):
        errors.append("rate_per_night_vnd: Indian guest on the TA card — the rate is the card rate +20% "
                      "(1,700,000 → 2,040,000) and surcharge says '+20% Indian guests (incl. in rate)'. If the "
                      "agency's rate or total leaves the +20% out, don't pick one: name it in missing_info "
                      "('rate: Indian +20% not in the agency's rate') for Karen (AGENTS rule 4)")
    # audit 30/10 (F-13, rows 373, 375): a non-blank missing_info stops the build; an inferred code is not missing
    if action in ("NEW", "CHANGE") and not built and re.search(r"nationality inferred", note, re.I):
        errors.append("missing_info: 'nationality inferred …' is not missing info (inferring from the name is step "
                      "3 of the rule) and it stops the build: take it out; say it in the scan report if needed")
    nat = nationality_problem(g("nationality")) if g("nationality") else None
    if nat:
        # rows written before 29/10 carry the full name: a CHANGE copying it is not blocked
        (errors if action == "NEW" and not built else warnings).append(nat)

    if action in ("NEW", "CHANGE") and g("notes"):
        warnings += _notes_problems(rec, g)
    if action == "CANCEL" and g("notes") and not g("notes").startswith("Cancellation charge"):
        warnings.append("notes: a CANCEL row's notes is the one line 'Cancellation charge (<policy>): <amount> "
                        "VND — <days> days before check-in, <rule>. Paid: <amount>.' (booking-intake.md)")
    avg, rooms, nights, total = (g("Average rate per night after discount"), g("rooms"), g("nights"), g("total_vnd"))
    extra = g("Surcharge amount") or "0"
    if all(x.isdigit() for x in (avg, rooms, nights, total)) and re.fullmatch(r"-?\d+", extra):
        want = int(avg) * int(rooms) * int(nights) + int(extra)
        if want != int(total):
            plus = f" + surcharge {extra}" if extra != "0" else ""
            diff = int(total) - want
            warnings.append(f"total_vnd: {total} ≠ {avg} × {rooms} rooms × {nights} nights{plus} = {want}. If "
                            f"{total} is the email's or contract's exact total, the {diff:+d} is rounding: add it "
                            f"to 'Surcharge amount' and 'Rounding {diff:+d}' to surcharge (booking-intake.md)")
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
    if action == "CHANGE":
        # audit 30/10 (F-08): a payment slip is a CHANGE row with the payment columns filled (schedule.md step 4)
        booking.update({h: "" for h in sheet.header if h in PAYMENT})
    line = {h: "" for h in cols if level(h) == "room_lines"}
    return {"booking": booking, "room_lines": [line]}
