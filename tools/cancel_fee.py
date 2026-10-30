"""Cancellation charge for a TA booking, worked out from its intake rows and the TA policy in
docs/rate-knowledge/ta-rates.json. It informs Karen's decision and the cancellation email; it never
cancels anything (AGENTS.md rule 7). Where the policy is unclear it says so instead of choosing.
"""
from datetime import datetime

from . import quote as quoting

AGENCY_CONTRACTS = {"anex", "crystal bay", "odeon", "pegas", "selfie", "coral", "sunmar"}


class CancelFeeError(Exception):
    pass


def _num(v):
    v = str(v or "").strip()
    return int(v) if v.isdigit() else 0


def current_rows(rows):
    """The booking as it stands: the rows of the latest CHANGE, else the NEW rows. CANCEL rows don't count."""
    live = [r for r in rows if r.get("action") in ("NEW", "CHANGE")]
    if not live:
        raise CancelFeeError("no NEW or CHANGE row for this booking_ref on the sheet")
    changes = [r for r in live if r.get("action") == "CHANGE"]
    if not changes:
        return live
    last = max(r.get("received_at", "") for r in changes)
    return [r for r in changes if r.get("received_at", "") == last]


def payments(rows):
    """Payments recorded on the rows, each (amount, date) counted once even if repeated on every row."""
    seen = set()
    for r in rows:
        for col, when in (("Payment 1", "Payment 1 date + time"), ("Payment 2", "Payment 2 date + time")):
            amount = _num(r.get(col))
            if amount:
                seen.add((amount, r.get(when, "")))
    return sorted(seen, key=lambda x: x[1])


def cancel_fee(rows, cancelled_at, data=None, no_show=False):
    data = data or quoting.load()
    policy = data["cancellation"]
    rows = current_rows(rows)
    gaps, notes = [], []
    channel = {r.get("channel_type", "") for r in rows}
    company = " ".join(r.get("company", "") for r in rows).lower()
    if channel != {"TA"} or any(c in company for c in AGENCY_CONTRACTS):
        raise CancelFeeError(f"channel {sorted(channel)} / {rows[0].get('company')}: the TA policy doesn't apply. "
                             f"Tour operators use the cancellation table in their own docs/rate-knowledge/<name>.md; "
                             f"OTA cancellations follow the OTA's terms — report to Karen")
    arrival = quoting.parse_date(rows[0]["arrival"])
    departure = quoting.parse_date(rows[0]["departure"])
    night_list, _ = quoting.nights(arrival, departure, data)
    holiday = any(s == "holiday" for _, s, _ in night_list)
    days = (arrival - cancelled_at.date()).days

    lines = []
    room_total = first_night = 0
    for r in rows:
        rate = _num(r.get("Average rate per night after discount")) or _num(r.get("rate_per_night_vnd"))
        rooms = _num(r.get("rooms"))
        if not rate or not rooms:
            gaps.append(f"row {r.get('_row')} ({r.get('room_code')}): no rate or room count — can't price it")
            continue
        n = len(night_list)
        room_total += rate * rooms * n
        first_night += rate * rooms
        lines.append(f"{rooms} × {r.get('room_code')} at {quoting.money(rate)} × {n} night(s) = "
                     f"{quoting.money(rate * rooms * n)}")

    def charge(rule):
        if rule.get("free"):
            return 0, "free cancellation"
        if "first_nights" in rule:
            return first_night * rule["first_nights"], f"{rule['first_nights']} night(s) of every room"
        return room_total * rule["pct_of_rooms"] // 100, f"{rule['pct_of_rooms']}% of the room charge"

    column = "holiday" if holiday else "normal"
    if holiday:
        notes.append(policy["holiday_column_note"])
    if no_show:
        fee, how = charge(policy["no_show"])
        basis = "no show"
    elif days < 0:
        raise CancelFeeError("the cancellation is after check-in: that's an early departure or no show — Karen")
    else:
        basis = f"{days} day(s) before check-in, {column} column"
        tier = next((t for t in policy["tiers"]
                     if days >= t["min_days"] and (t["max_days"] is None or days <= t["max_days"])), None)
        if tier is None:
            # On no line of the table (exactly 7 days): show the line either side, Karen picks.
            above = min((t for t in policy["tiers"] if t["min_days"] > days), key=lambda t: t["min_days"])
            below = max((t for t in policy["tiers"] if t["max_days"] is not None and t["max_days"] < days),
                        key=lambda t: t["max_days"])
            (fa, ha), (fb, hb) = charge(above[column]), charge(below[column])
            fee, how = None, f"UNCLEAR — either {quoting.money(fa)} VND ({ha}) or {quoting.money(fb)} VND ({hb})"
            gaps.append(f"{days} days before check-in: {policy['unclear_note']} Karen decides which line applies")
        else:
            fee, how = charge(tier[column])

    paid = payments(rows)
    paid_total = sum(a for a, _ in paid)
    notes.append(policy["deposit_note"])
    return {"booking_ref": rows[0].get("booking_ref"), "rows": [r.get("_row") for r in rows],
            "arrival": arrival, "departure": departure, "cancelled_at": cancelled_at, "days": days,
            "holiday": holiday, "basis": basis, "how": how, "lines": lines, "room_total": room_total,
            "fee": fee, "paid": paid, "paid_total": paid_total, "gaps": gaps, "notes": notes}


def render(c):
    m = quoting.money
    out = [f"BOOKING {c['booking_ref']} (sheet rows {c['rows']}): {c['arrival']:%d/%m/%Y} – {c['departure']:%d/%m/%Y}"
           + (" — includes holiday nights" if c["holiday"] else ""),
           f"CANCELLED {c['cancelled_at']:%d/%m/%Y %H:%M} (Vietnam time): {c['basis']}"]
    out += [f"  {line}" for line in c["lines"]]
    out.append(f"  room charge {m(c['room_total'])} VND")
    out.append(f"CHARGE: {c['how']}" if c["fee"] is None else f"CHARGE: {m(c['fee'])} VND ({c['how']})")
    if c["paid"]:
        out.append("PAID (sheet): " + "; ".join(f"{m(a)} on {d or '?'}" for a, d in c["paid"]) +
                   f" = {m(c['paid_total'])} VND")
        if c["fee"] is not None:
            diff = c["paid_total"] - c["fee"]
            out.append(f"  paid − charge = {m(diff)} VND" +
                       (" (would be refundable — Karen decides)" if diff > 0 else ""))
    else:
        out.append("PAID (sheet): nothing recorded in Payment 1 / Payment 2")
    for n in c["notes"]:
        out.append(f"NOTE: {n}")
    for g in c["gaps"]:
        out.append(f"GAP: {g}")
    out.append("Nothing is cancelled by this command. A CANCEL row + Karen's OK come first (AGENTS.md rule 7).")
    return "\n".join(out)
