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
    "rate_source": ("TA card", "Anex contract", "OTA net", "Special (Karen)", "Other"),
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
NEVER_FOR_AGENCIES = ("TW-DLX",)  # MEMORY: never TW-DLX or APT to agencies


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

    for k in ALWAYS:
        if k == "booking_ref" and g("channel_type") == "Direct":
            continue  # a direct guest has no agency code
        if _blank(rec.get(k)):
            errors.append(f"{k}: never blank" + (" (TBA if names not given)" if k == "guest_names" else ""))
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
            errors.append(f"{k}: {g(k)!r} not allowed; use one of {list(allowed)}")
    for k, allowed in PREFIX_ENUMS.items():
        if g(k) and not g(k).startswith(allowed):
            errors.append(f"{k}: must start with {' or '.join(allowed)}")
    for k in DATES:
        if g(k) and not _date(g(k), "%d/%m/%Y"):
            errors.append(f"{k}: {g(k)!r} is not DD/MM/YYYY")
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
        if g(k) and not (k == "tracy_status" and g(k) == "Pending") and action == "NEW":
            errors.append(f"{k}: filled by the build tool, leave blank on a NEW row")

    if action in ("NEW", "CHANGE") and g("notes") and not g("notes").startswith("1."):
        warnings.append("notes: NOTES RULE wants the EZFOLIO Notice numbered 1–7, one item per line")
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
