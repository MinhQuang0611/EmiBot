"""Free or paid airport pick-up: the whole booking against USD 250 (hotel-info.md, Karen 04/11, dev 06/11).

Booking.com and other OTAs reach SynXis one room at a time: a 2-room booking is two SynXis numbers, two NEW rows,
and the guest's later messages land on one of them only. On 06/11 Emi priced two 2-room Booking.com bookings on
one room each and told both guests the pick-up was paid (Erkinbek Uzakbaev 6907944253: SynXis 003193 + 003194,
11,520,000; Adrian Sequeira 5337759531: Booking.com says 2 rooms, the sheet has 003205 only). This module finds
every room of the booking, adds them up and gives one outcome.
"""
import re

FREE_FROM_VND = 6_750_000      # above USD 250 at any rate up to 27,000 (hotel-info.md)
PAID_BELOW_VND = 6_000_000     # below USD 250 at any rate down to 24,000
THRESHOLD_USD = 250
PAID_PRICE = "200,000 VND one way (4-seat car, hotel-info.md)"

FREE, PAID, CHECK, TA = "FREE", "PAID", "CHECK", "TA"
_NOT_NAMES = {"guest", "of", "tba", "mr", "mrs", "ms", "miss", "and", "the"}


def _num(v):
    d = re.sub(r"\D", "", str(v or ""))
    return int(d) if d else 0


def _names(r):
    return {t for t in re.split(r"[^\w]+", (r.get("guest_names") or "").lower())
            if len(t) >= 3 and not t.isdigit() and t not in _NOT_NAMES and not t.startswith("tba")}


def _legs(rows, parts):
    """Rows grouped into separate reservations: rows whose reference numbers overlap are one leg."""
    legs = []   # [(set of parts, [rows])]
    for r in rows:
        p = set(parts(r.get("booking_ref")))
        joined = [leg for leg in legs if leg[0] & p]
        for leg in joined:
            legs.remove(leg)
            p |= leg[0]
        legs.append((p, [x for leg in joined for x in leg[1]] + [r]))
    for _, leg_rows in legs:
        leg_rows.sort(key=lambda r: (r.get("_sheet") == "live", r.get("_row", 0)))
    return [leg_rows for _, leg_rows in legs]


def _current(leg_rows):
    """The leg as it stands: the rows of its last email (one per room type); [] once cancelled."""
    last = leg_rows[-1]
    if last.get("action") == "CANCEL":
        return []
    key = (last.get("action"), last.get("received_at"))
    # Two emails in the same minute share a key (Adrian Sequeira, live rows 1599 + 1600, 06/11 10:29). One email
    # never has two identical room lines (sheet-append refuses them), so an identical line is the other email's.
    seen, out = set(), []
    for r in leg_rows:
        line = (r.get("room_code"), r.get("rooms"), r.get("rate_per_night_vnd"), r.get("total_vnd"))
        if (r.get("action"), r.get("received_at")) == key and line not in seen:
            seen.add(line)
            out.append(r)
    return out


def _rooms(rows):
    return sum(_num(r.get("rooms")) or 1 for r in rows)


def _kind(rows):
    """'guest' when total_vnd is what the guest paid, else 'net' or 'provisional'."""
    src = " ".join((r.get("rate_source") or "") for r in rows).lower()
    missing = " ".join((r.get("missing_info") or "") for r in rows).lower()
    if "provisional" in missing or "provisional" in src:
        return "provisional"
    channel = (rows[0].get("channel_type") or "").strip()
    if "guest total" in src or channel == "Direct":
        return "guest"
    return "net"


def check(rows, ref, parts, ota_rooms=None, paid_vnd=None, paid_usd=None):
    """rows: every intake row (Emi's sheet + live). parts: booking_ref -> its reference numbers.
    Returns {"outcome", "why", "legs": [...], "total", "rooms", "kind", "notes"}."""
    mine = set(parts(ref))
    hits = [r for r in rows if mine & set(parts(r.get("booking_ref")))]
    if not hits:
        return None
    anchor = next((r for r in reversed(hits) if r.get("action") != "CANCEL"), hits[-1])
    names, arr, dep = _names(anchor), anchor.get("arrival"), anchor.get("departure")
    company = (anchor.get("company") or "").strip().lower()
    hit_ids = {id(r) for r in hits}
    # The booking's other rooms: same guest, same dates, same company, another reference number.
    siblings = [r for r in rows if id(r) not in hit_ids and names and _names(r) & names
                and r.get("arrival") == arr and r.get("departure") == dep
                and (r.get("company") or "").strip().lower() == company]
    notes = []
    legs = []
    for leg_rows in _legs(hits + siblings, parts):
        now = _current(leg_rows)
        if not now:
            continue
        legs.append({"rows": now, "by_name": all(id(r) not in hit_ids for r in leg_rows),
                     "total": sum(_num(r.get("total_vnd")) for r in now), "rooms": _rooms(now), "kind": _kind(now)})
    total = sum(leg["total"] for leg in legs)
    rooms = sum(leg["rooms"] for leg in legs)
    kinds = {leg["kind"] for leg in legs}
    kind = "guest" if kinds == {"guest"} else ("provisional" if "provisional" in kinds else "net")
    if any(leg["by_name"] for leg in legs):
        notes.append("rooms marked 'same guest and dates' were matched by name and dates, not by number: "
                     "check they belong to this booking")
    res = {"legs": legs, "total": total, "rooms": rooms, "kind": kind, "notes": notes,
           "anchor": anchor}

    channel = (anchor.get("channel_type") or "").strip()
    if channel == "TA":
        return dict(res, outcome=TA, why="a travel agency's booking: no free pick-up, transfer at the TA price list "
                                         "(hotel-info.md)")
    if channel == "Tour operator":
        return dict(res, outcome=CHECK, why="tour operator booking: pick-up terms are in the contract, not the "
                                            "USD 250 rule: ask-karen")
    if not legs:
        return dict(res, outcome=CHECK, why="every room of this booking is cancelled on the sheet")

    if paid_usd is not None:
        return dict(res, outcome=FREE if paid_usd > THRESHOLD_USD else PAID,
                    why=f"guest paid USD {paid_usd:,.2f} (from the email)")
    if paid_vnd is not None:
        return dict(res, **_by_vnd(paid_vnd, "guest paid (from the email)"))

    short = ota_rooms is not None and ota_rooms > rooms
    if short:
        notes.append(f"the OTA says {ota_rooms} rooms, the sheet has {rooms}: a room is missing from the sheet. "
                     "Find its SynXis/OTA email (mail-find <surname>), write the row, then run pickup again")
    if total >= FREE_FROM_VND and kind in ("guest", "net"):
        # what the guest paid is never below the net, and the missing rooms only add to it
        return dict(res, outcome=FREE, why=f"{_vnd(total)} for {rooms} room(s) "
                                            f"({'guest total' if kind == 'guest' else 'net: the guest paid more'})")
    if kind == "provisional":
        return dict(res, outcome=CHECK, why="the figure on the sheet is a provisional TA-card price, not what the "
                                            "guest paid: read the booking email / voucher and pass --paid-vnd or "
                                            "--paid-usd")
    if short:
        return dict(res, outcome=CHECK, why=f"{_vnd(total)} covers only {rooms} of {ota_rooms} rooms")
    if kind == "net":
        return dict(res, outcome=CHECK, why=f"{_vnd(total)} is the hotel's net, not what the guest paid: read the "
                                            "voucher (Agoda: 'Reference sell rate (incl. taxes & fees)') and pass "
                                            "--paid-vnd; nothing there -> ask-karen")
    decided = _by_vnd(total, f"guest total for {rooms} room(s)")
    if decided["outcome"] == PAID and channel == "OTA" and ota_rooms is None:
        # Paid is the answer that goes wrong when a room is missing: never without the OTA's own room count.
        return dict(res, outcome=CHECK, why=f"{_vnd(total)} for {rooms} room(s) on the sheet: run again with "
                                            "--ota-rooms N, N = the OTA's own room count (Booking.com message "
                                            "'Tổng số phòng' / 'Total rooms', voucher, SynXis 'Room Quantity' "
                                            "of every number)")
    return dict(res, **decided)


def _by_vnd(amount, what):
    if amount >= FREE_FROM_VND:
        return {"outcome": FREE, "why": f"{_vnd(amount)} {what}"}
    if amount < PAID_BELOW_VND:
        return {"outcome": PAID, "why": f"{_vnd(amount)} {what}"}
    return {"outcome": CHECK, "why": f"{_vnd(amount)} {what}: between 6,000,000 and 6,750,000, depends on the "
                                     "exchange rate -> ask-karen"}


def _vnd(n):
    return f"{n:,} VND"


def render(res, where):
    a = res["anchor"]
    head = {FREE: "PICK-UP: FREE, one way (email-templates.md 7, free form; no CHECK line)",
            PAID: f"PICK-UP: PAID, {PAID_PRICE} (email-templates.md 7, paid form)",
            TA: "PICK-UP: TA booking, not free",
            CHECK: "PICK-UP: CHECK (CHECK BEFORE SENDING line + ask-karen; still one outcome in the draft)"}
    lines = [head[res["outcome"]], f"why: {res['why']}",
             f"booking: {a.get('guest_names')} {a.get('arrival')}–{a.get('departure')} {a.get('company') or ''}".rstrip()]
    for leg in res["legs"]:
        r = leg["rows"][-1]
        lines.append(f"  {where(r)}: {r.get('booking_ref')} — {leg['rooms']} room(s) "
                     f"{', '.join(x.get('room_code') or '?' for x in leg['rows'])}, {_vnd(leg['total'])} "
                     f"({leg['kind']})" + ("  [same guest and dates]" if leg["by_name"] else ""))
    lines.append(f"total: {_vnd(res['total'])}, {res['rooms']} room(s)")
    lines += [f"note: {n}" for n in res["notes"]]
    return "\n".join(lines)
