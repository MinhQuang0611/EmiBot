"""What each tour operator needs beyond the generic intake (dev, 2026-10-29; skills/tour-operators.md): where
replies and confirmations go, how it pays, what accounting owes it, and the on-request rule. Prices are in
tools/operator_rates.py; this file is the procedure.
"""
from datetime import date, timedelta

# skills/tour-operators.md step 5: an on-request booking (release passed or allotment used up)
ON_REQUEST_OCCUPANCY = 60.0   # % on any night of the stay ...
ON_REQUEST_DAYS = 30          # ... with check-in more than this many days away -> reject
DECLINE_REASON = "On request booking cannot be accommodated"

OPERATORS = {
    "Anex": {
        "contract": "81/26-27/PQ-HAYA/AL",
        "robots": ("@ms.anextour.com",),
        "reply_to": ("reservation@anexvietnam.com",),
        "steps": [
            "Emails come from a no-reply robot: every reply goes to reservation@anexvietnam.com "
            "(draft-reply does this by itself).",
            "Every Anex email gets a reply draft, the NEW, CHANGED and CANCELLED robot emails included.",
            "The robot email asks to confirm through a link: someone still has to click it, an email reply "
            "doesn't count. Say so in the scan report.",
            "'On request' and 'Partly Allotment' bookings go through the on-request rule (on-request).",
        ],
        "accounting": [
            "Every day: e-invoice for that day's check-outs to hotelaccount.vn@anextour.com "
            "(checkouts --company Anex --from <today>).",
            "Every Monday: last week's check-outs, Monday to Sunday, to hotelaccount.vn@anextour.com. Once Anex "
            "confirms, hard copies of the VAT invoice, folio and reservation go by post.",
            "Anex pays two weeks at a time, on Friday of the third week. A check-out invoiced in a later month "
            "isn't paid: every invoice goes out by month-end.",
        ],
    },
    "Odeon": {
        "contract": "1033494 (W26/S27)",
        "confirm_to": ("vietnamreservations@odeontours.com", "vietnamaccounts@odeontours.com"),
        "confirm_subject": "Odeon Reservation confirmation {ref}",
        "decline_subject": "Voucher {ref} – Declined (on request)",
        "invoice": {"number": "HAYA - {group}", "due_days_before": 10, "file": "Invoice_{ref}.pdf"},
        "steps": [
            "Front office logs in to the Odeon extranet, downloads the voucher and sends it to sales@.",
            "Read the voucher: Odeon ref, guests, room type, dates, meal plan, guests, SPO code. Price with "
            "exactly the offer the SPO code applies (to-price --operator Odeon --spo <code>); SCO / SSO 5% only "
            "when the voucher shows that code.",
            "Allotment -> NEW row. On request -> on-request first.",
            "Rejected -> CANCEL row (what_changed 'On request booking cannot be accommodated') and a new email "
            "to both Odeon addresses: voucher no. X is declined, outside our allotment, on-request bookings "
            "can't be accepted at the moment (draft-new).",
            "Built: check the EZFOLIO PDF against the voucher (held bookings are approved by Long first).",
            "Proforma invoice from the Google Sheets template, number 'HAYA - <group>', due 10 days before "
            "check-in, saved as Invoice_<ref>.pdf (invoice-data <ref> gives the figures).",
            "Confirmation: a new email to both Odeon addresses with both PDFs, the EZFOLIO confirmation and the "
            "invoice (draft-confirmation ... --to ... --subject ... --attach Invoice_<ref>.pdf).",
            "Someone presses Confirm on hotelextranet.odeontours.com. Who: not decided yet — say so in the report.",
        ],
        "accounting": ["Invoice at least 15 days before check-in to vietnamaccounts@odeontours.com (contract); "
                       "Odeon pays 100% 10 days before check-in."],
    },
    "Crystal Bay": {
        "contract": "00145/26-27/PQC-HAYAHOTEL/ALLOT",
        "invoice_to": ("payment.acc@crystalbaytours.com",),
        "invoice": {"number": "HAYA - {group}", "due_days_before": 3, "file": "Invoice_{ref}.pdf"},
        "steps": [
            "Bookings come through Crystal Bay's online system and confirm by themselves inside the allotment.",
            "Anything outside the allotment is answered within 24 hours, with the on-request rule.",
            "Cut-off: 10 days before arrival; 21 days from 1 Nov to 28 Feb and on public holidays.",
            "Before arrival: the invoice goes with the confirmation to payment.acc@crystalbaytours.com; they pay "
            "by bank transfer at least 3 days before check-in.",
        ],
        "accounting": [
            "VAT invoice issued on the check-out date and sent within 2 working days; late = HAYA pays any tax "
            "penalty.",
            "Every Monday: invoice last week's check-outs (Monday to Sunday) with a signed and stamped debt "
            "reconciliation and the booking report (checkouts --company 'Crystal Bay').",
        ],
    },
    "Pegas": {
        "contract": "0002PQ011026 (W26/S27)",
        "invoice": {"number": "HAYA - {group}", "due_days_before": 7, "send_days_before": 14,
                    "file": "Invoice_{ref}.pdf"},
        "steps": [
            "Proforma invoice at least 14 days before check-in.",
            "Pegas pays 100% by bank transfer at least 7 days before check-in and emails the slip. Paid late "
            "without a word -> the booking can be released: that is Karen's call, never Emi's.",
        ],
        "accounting": ["VAT invoice issued on the check-out date.",
                       "Every week: a signed and stamped debt reconciliation (checkouts --company Pegas)."],
    },
    "Selfie": {
        "contract": "2026–2027 (no number on the file)",
        "steps": [
            "Priced from the Selfie contract (to-price --operator Selfie).",
            "So far every Selfie booking shows 'On request', so each one goes through on-request. Open with "
            "Karen: is that real, or just how their system labels every booking?",
        ],
        "accounting": ["Selfie pays 100% 7 days before arrival."],
    },
    "Fun and Sun": {
        "contract": "none this season",
        "steps": ["No contract: nothing to price. Rate blank, 'no Fun and Sun contract this season' in "
                  "missing_info, flag to Karen."],
        "accounting": [],
    },
}

COMMON_STEPS = [
    "Booking arrives in sales@. Sent only to haya@ -> front office forwards it to sales@ first.",
    "Read it: ref, guests and nationality, room type, dates, meal plan, guest count, allotment or on request.",
    "Price it from that operator's own contract (to-price): early bird, stay/pay and surcharges, the full "
    "calculation in notes item 6.",
    "Allotment: NEW row, one row per room type.",
    "On request (release passed or allotment used up): on-request. No availability, or occupancy over 60% with "
    "check-in more than 30 days away -> reject: CANCEL row 'On request booking cannot be accommodated' + decline "
    "draft. Anything else -> ask Karen before logging it.",
    "The build tool builds it and puts the PDF link in pdf_link (column AQ). Held -> Long approves it. Check the "
    "PDF against the booking.",
    "Confirmation: a reply draft on the original thread with the group code and the EZFOLIO PDF.",
    "Changes and cancels: CHANGE / CANCEL rows; every CHANGE row has a fully rewritten notes and its rate "
    "fields filled (sheet-append refuses one without).",
]


def known(company):
    return company in OPERATORS


def is_robot(operator, address):
    a = (address or "").strip().lower()
    return any(a.endswith(r) for r in OPERATORS.get(operator, {}).get("robots", ()))


def robot_operator(address):
    """The operator whose no-reply robot sent this, or None."""
    return next((op for op in OPERATORS if is_robot(op, address)), None)


def info(operator):
    if operator not in OPERATORS:
        raise KeyError(f"{operator!r} is not a tour operator; known: {', '.join(OPERATORS)}")
    o = OPERATORS[operator]
    out = [f"{operator} — contract {o['contract']}", "", "COMMON STEPS (every tour operator):"]
    out += [f"  {i}. {s}" for i, s in enumerate(COMMON_STEPS, 1)]
    out += ["", f"{operator.upper()} — what differs:"] + [f"  - {s}" for s in o["steps"]]
    if o.get("accounting"):
        out += ["", "ACCOUNTING (not Emi's to send; check-out lists and drafts only when asked):"]
        out += [f"  - {s}" for s in o["accounting"]]
    return "\n".join(out)


# --- on request ---

def on_request(result, problems, arrival, today):
    """('REJECT' | 'ASK KAREN', reasons). result = availability.check(), problems = availability.fits()."""
    if problems:
        return "REJECT", [f"no availability: {'; '.join(problems)}"]
    away = (arrival - today).days
    occ = result["occupancy"]
    unknown = [n for n, v in occ.items() if v is None]
    high = [(n, v) for n, v in occ.items() if v is not None and v > ON_REQUEST_OCCUPANCY]
    if high and away > ON_REQUEST_DAYS:
        return "REJECT", [f"occupancy over {ON_REQUEST_OCCUPANCY:.0f}% on "
                          f"{', '.join(f'{n:%d/%m} ({v:.0f}%)' for n, v in high)} and check-in {away} days away "
                          f"(more than {ON_REQUEST_DAYS})"]
    why = [f"rooms free every night; check-in {away} days away"]
    if high:
        why.append(f"occupancy over {ON_REQUEST_OCCUPANCY:.0f}% on {', '.join(f'{n:%d/%m}' for n, _ in high)} "
                   f"but check-in is within {ON_REQUEST_DAYS} days")
    if unknown:
        why.append(f"occupancy not on the sheet for {', '.join(f'{n:%d/%m}' for n in unknown)}")
    return "ASK KAREN", why


# --- check-outs and invoices, from the intake sheet ---

def _date(s):
    try:
        d, m, y = (int(x) for x in str(s).strip().split("/"))
        return date(y, m, d)
    except (ValueError, TypeError):
        return None


def _amount(s):
    digits = "".join(c for c in str(s or "") if c.isdigit())
    return int(digits) if digits else 0


def bookings(rows, state_of):
    """Every booking on the sheet as it stands now (state_of = emi.booking_state), one entry each, sheet order."""
    seen, out = set(), []
    for r in rows:
        ref = (r.get("booking_ref") or "").strip()
        if not ref:
            continue
        state = state_of(rows, ref)
        if not state or state[-1]["_row"] in seen:
            continue
        seen.add(state[-1]["_row"])
        out.append(state)
    return out


def cancelled(state):
    return any(r.get("action") == "CANCEL" or r.get("status") == "Cancelled" for r in state)


def checkouts(rows, state_of, company, first, last):
    """Bookings of `company` checking out first..last (inclusive), not cancelled."""
    hits = []
    for state in bookings(rows, state_of):
        head = state[0]
        if head.get("company", "").strip().lower() != company.strip().lower() or cancelled(state):
            continue
        dep = _date(head.get("departure"))
        if dep and first <= dep <= last:
            hits.append(state)
    return sorted(hits, key=lambda s: (_date(s[0]["departure"]), s[0].get("booking_ref", "")))


def render_checkouts(hits, company, first, last):
    span = f"{first:%d/%m/%Y}" + (f" – {last:%d/%m/%Y}" if last != first else "")
    out = [f"CHECK-OUTS {company} {span}: {len(hits)} booking(s)"]
    total = 0
    for s in hits:
        h = s[0]
        amount = sum(_amount(r.get("total_vnd")) for r in s)
        total += amount
        rooms = ", ".join(f"{r.get('rooms') or '?'} {r.get('room_code') or '?'}" for r in s)
        built = {r.get("tracy_status") for r in s}
        flag = "" if built == {"Entered"} else f"  [tracy_status {', '.join(sorted(b or 'blank' for b in built))}]"
        out.append(f"- Ref {h.get('booking_ref')} | group #{h.get('ezfolio_group_code') or '?'} | "
                   f"{h.get('guest_names') or 'TBA'} | {h.get('arrival')} – {h.get('departure')} | {rooms} | "
                   f"{amount:,} VND{flag}")
    out.append(f"TOTAL {total:,} VND (sum of total_vnd; the invoice uses the folio, check against EZFOLIO)")
    return "\n".join(out)


def invoice_data(state):
    """The proforma figures for one booking (Odeon, Crystal Bay, Pegas): number, due date, lines."""
    h = state[0]
    op = OPERATORS.get(h.get("company", ""), {})
    inv = op.get("invoice")
    if not inv:
        raise KeyError(f"{h.get('company')!r} has no proforma invoice in skills/tour-operators.md")
    group = h.get("ezfolio_group_code", "").strip().lstrip("#")
    arrival = _date(h.get("arrival"))
    if not group:
        raise KeyError(f"{h.get('booking_ref')}: no ezfolio_group_code on the row yet — the invoice number is "
                       f"'HAYA - <group>': wait for the build tool")
    if arrival is None:
        raise KeyError(f"{h.get('booking_ref')}: arrival {h.get('arrival')!r} is not DD/MM/YYYY")
    ref = h.get("booking_ref", "").split("/")[0].strip()
    lines = [{"room_code": r.get("room_code"), "rooms": r.get("rooms"), "nights": r.get("nights"),
              "rate": r.get("Average rate per night after discount") or r.get("rate_per_night_vnd"),
              "surcharge": r.get("surcharge"), "surcharge_amount": r.get("Surcharge amount"),
              "total": _amount(r.get("total_vnd"))} for r in state]
    d = {"number": inv["number"].format(group=group), "file": inv["file"].format(ref=ref),
         "due": arrival - timedelta(days=inv["due_days_before"]), "due_rule": f"{inv['due_days_before']} days "
         f"before check-in", "company": h.get("company"), "ref": h.get("booking_ref"), "group": group,
         "guests": h.get("guest_names"), "arrival": h.get("arrival"), "departure": h.get("departure"),
         "lines": lines, "total": sum(x["total"] for x in lines)}
    if inv.get("send_days_before"):
        d["send_by"] = arrival - timedelta(days=inv["send_days_before"])
    return d


def render_invoice(d):
    out = [f"PROFORMA {d['number']} — {d['company']} Ref {d['ref']}, group #{d['group']}",
           f"Guests: {d['guests']}", f"Stay: {d['arrival']} – {d['departure']}"]
    for x in d["lines"]:
        out.append(f"  {x['rooms']} × {x['room_code']} × {x['nights']} night(s) @ {x['rate']}"
                   + (f" + {x['surcharge']} ({x['surcharge_amount']})" if x["surcharge"] else "")
                   + f" = {x['total']:,} VND")
    out.append(f"Total: {d['total']:,} VND")
    out.append(f"Payment due: {d['due']:%d/%m/%Y} ({d['due_rule']})")
    if d.get("send_by"):
        out.append(f"Send the proforma by: {d['send_by']:%d/%m/%Y}")
    out.append(f"Save the PDF as: {d['file']}")
    out.append("The Google Sheets invoice template is not connected to Emi: a person fills it with these figures "
               "and exports the PDF; then attach it with draft-confirmation --attach.")
    return "\n".join(out)
