"""Price a stay and suggest room allocations from the TA rate table, so an inquiry reply never
rests on mental arithmetic. Data: docs/rate-knowledge/ta-rates.json (copied from ta.md).

What this does not know, it says, in `gaps`: availability and stop-sale (the FUTURE AVAILABILITY
file is not connected), 2027 holidays, dates outside the table, channels other than TA.
"""
import json
import math
import os
from datetime import date, datetime, timedelta

DATA = os.path.join(os.path.dirname(__file__), "..", "docs", "rate-knowledge", "ta-rates.json")


class QuoteError(Exception):
    pass


def load(path=DATA):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_date(s):
    try:
        return datetime.strptime(s.strip(), "%d/%m/%Y").date()
    except ValueError:
        raise QuoteError(f"{s!r} is not DD/MM/YYYY") from None


def _iso(s):
    return date.fromisoformat(s)


def nights(arrival, departure, data):
    """[(night_date, season, holiday_name)], gaps."""
    if departure <= arrival:
        raise QuoteError("departure must be after arrival")
    gaps = []
    by_month = {m: s for s, months in data["seasons_by_month"].items() for m in months}
    hols = [(_iso(h["from"]), _iso(h["to"]), h["name"]) for h in data["holidays"]]
    known_until = _iso(data["holidays_known_until"])
    out = []
    d = arrival
    while d < departure:
        hol = next((name for a, b, name in hols if a <= d <= b), None)
        out.append((d, "holiday" if hol else by_month[d.month], hol))
        d += timedelta(days=1)
    if any(n > known_until for n, _, _ in out):
        gaps.append(f"holiday dates after {known_until:%d/%m/%Y} are not on the TA table: nights after that are "
                    f"priced by the month's season. If any falls on a likely holiday (Tết, 26/4, 30/4–1/5, 2/9, "
                    f"24–26/12, 31/12), Karen must confirm the holiday rate before quoting")
    if arrival < _iso(data["valid_from"]):
        gaps.append(f"arrival is before the TA table starts ({_iso(data['valid_from']):%d/%m/%Y})")
    return out, gaps


def _assign_children(adults_eq, kid_ages, capacity, slots):
    """Fill spare beds with the oldest children (no surcharge), the rest share a bed in a child slot.
    Returns (kids_as_persons, kids_in_slots) or None if they don't fit."""
    spare = capacity - adults_eq
    if spare < 0:
        return None
    kids = sorted(kid_ages, reverse=True)
    as_persons, in_slots = kids[:spare], kids[spare:]
    if len(in_slots) > slots:
        return None
    return as_persons, in_slots


def _price(alloc, night_list, rooms_by_code, data, adults_eq, kids_in_slots, indian):
    """Total and lines for one allocation {code: count}."""
    child = data["children"]
    roh = sum(n for c, n in alloc.items() if rooms_by_code[c]["persons"] == 2) >= data["roh"]["min_rooms"]
    room_total = 0
    lines = []
    for code, count in alloc.items():
        room = rooms_by_code[code]
        priced = rooms_by_code[data["roh"]["rate_like"]] if roh and room["persons"] == 2 else room
        per_night = [priced["rates"][season] for _, season, _ in night_list]
        if indian:
            per_night = [round(r * (100 + data["indian_surcharge_pct"]) / 100) for r in per_night]
        subtotal = sum(per_night) * count
        room_total += subtotal
        lines.append({"code": code, "name_vi": room["name_vi"], "name_en": room["name_en"], "count": count,
                      "rates": sorted(set(per_night)), "subtotal": subtotal})
    surcharge_kids = [a for a in kids_in_slots if child["free_under"] <= a < child["adult_from"]]
    child_total = sum(child["surcharge_per_night"][s] for _, s, _ in night_list) * len(surcharge_kids)
    one_night = 0
    if len(night_list) < data["min_nights"]:
        guests = adults_eq + len(kids_in_slots)
        one_night = sum(data["one_night_surcharge_per_guest"][s] for _, s, _ in night_list) * guests
    return {"rooms": lines, "room_total": room_total, "child_surcharge": child_total,
            "children_charged": surcharge_kids, "one_night_surcharge": one_night,
            "total": room_total + child_total + one_night, "roh": roh}


def quote(arrival, departure, adults, kid_ages=(), rooms=None, room_type=None, alloc=None,
          twin=False, indian=False, data=None):
    data = data or load()
    if adults < 1:
        raise QuoteError("at least one adult")
    rooms_by_code = {r["code"]: r for r in data["rooms"]}
    for code in [room_type] + list((alloc or {}).keys()):
        if code and code in data["never_for_agencies"]:
            raise QuoteError(f"{code} is never offered to agencies")
        if code and code not in rooms_by_code:
            raise QuoteError(f"{code} is not on the TA table; use one of {sorted(rooms_by_code)}")
    night_list, gaps = nights(arrival, departure, data)
    adult_from = data["children"]["adult_from"]
    adults_eq = adults + sum(1 for a in kid_ages if a >= adult_from)
    kids = [a for a in kid_ages if a < adult_from]
    two_p = room_type if room_type and rooms_by_code[room_type]["persons"] == 2 else ("SUP-TWN" if twin else "STD")

    def option(al):
        al = {c: n for c, n in al.items() if n}
        cap = sum(rooms_by_code[c]["persons"] * n for c, n in al.items())
        count = sum(al.values())
        if count == 0 or count > adults_eq:  # every room needs an adult or a 12+ guest
            return None
        if rooms and count != rooms:
            return None
        fit = _assign_children(adults_eq, kids, cap, count * data["child_slot_per_room"])
        if fit is None:
            return None
        as_persons, in_slots = fit
        p = _price(al, night_list, rooms_by_code, data, adults_eq, in_slots, indian)
        p.update(alloc=al, room_count=count, kids_as_persons=as_persons, kids_sharing_bed=in_slots)
        return p

    options = []
    if alloc:
        o = option(alloc)
        if o is None:
            raise QuoteError(f"{alloc} does not fit {adults} adults + children {list(kid_ages)}: "
                             f"each room takes its persons plus 1 child under 12, and needs an adult")
        options.append(("as asked", o))
    else:
        people = adults_eq + len(kids)
        top = math.ceil(people / 2) + 1
        cands = []
        types = [room_type] if room_type and rooms_by_code[room_type]["persons"] > 2 else None
        for q in range(0, math.ceil(people / 4) + 2):
            for t in range(0, math.ceil(people / 3) + 2):
                for d in range(0, top + 1):
                    if types and d:
                        continue
                    if types == ["TPL"] and q or types == ["QPL"] and t:
                        continue
                    o = option({two_p: d, "TPL": t, "QPL": q})
                    if o:
                        cands.append(o)
        if not cands:
            raise QuoteError("no allocation fits: check the room count and the guests")
        cheapest = min(cands, key=lambda o: (o["total"], o["room_count"]))
        fewest = min(cands, key=lambda o: (o["room_count"], o["total"]))
        options.append(("cheapest", cheapest))
        if fewest["alloc"] != cheapest["alloc"]:
            options.append(("fewest rooms", fewest))
        doubles = [o for o in cands if set(o["alloc"]) == {two_p}]
        if doubles:
            d = min(doubles, key=lambda o: o["total"])
            if all(d["alloc"] != o["alloc"] for _, o in options):
                options.append((f"only {rooms_by_code[two_p]['name_en']}", d))
        if not room_type and not twin:
            base = cheapest["alloc"]
            if base.get("STD"):
                up = option({**{c: n for c, n in base.items() if c != "STD"}, "DLX-SV": base["STD"]})
                if up:
                    options.append(("sea-view upgrade (paid)", up))

    notes = []
    if any(o["roh"] for _, o in options):
        notes.append(data["roh"]["note"])
    if len(night_list) < data["min_nights"]:
        notes.append(f"minimum {data['min_nights']} nights: a 1-night stay carries the per-guest surcharge shown")
    if indian:
        notes.append(data["indian_note"])
    gaps.append("availability and stop-sale NOT checked: the FUTURE AVAILABILITY file is not connected — "
                "a person must check before sending")
    return {"arrival": arrival, "departure": departure, "nights": night_list, "adults": adults,
            "kid_ages": list(kid_ages), "options": options, "notes": notes, "gaps": gaps, "data": data}


def money(n):
    return f"{n:,.0f}".replace(",", ".")


def render(q):
    out = [f"STAY {q['arrival']:%d/%m/%Y} – {q['departure']:%d/%m/%Y}, {len(q['nights'])} night(s); "
           f"{q['adults']} adult(s)" + (f", children aged {q['kid_ages']}" if q["kid_ages"] else "")]
    for d, season, hol in q["nights"]:
        out.append(f"  night {d:%d/%m/%Y}: {season}" + (f" ({hol})" if hol else ""))
    for label, o in q["options"]:
        out.append(f"\nOPTION — {label}: {o['room_count']} room(s), total {money(o['total'])} VND")
        for r in o["rooms"]:
            rate = " / ".join(money(x) for x in r["rates"])
            out.append(f"  {r['count']} × {r['code']} {r['name_vi']}: {rate} VND/room/night → {money(r['subtotal'])}")
        if o["kids_as_persons"]:
            out.append(f"  children counted in a bed of their own (no surcharge): ages {o['kids_as_persons']}")
        if o["kids_sharing_bed"]:
            out.append(f"  children sharing a bed: ages {o['kids_sharing_bed']}")
        if o["child_surcharge"]:
            out.append(f"  child surcharge (ages {o['children_charged']}): {money(o['child_surcharge'])}")
        if o["one_night_surcharge"]:
            out.append(f"  1-night surcharge: {money(o['one_night_surcharge'])}")
        out.append(f"  rooms {money(o['room_total'])} + surcharges "
                   f"{money(o['child_surcharge'] + o['one_night_surcharge'])} = {money(o['total'])} VND; "
                   f"deposit 50% = {money(o['total'] // 2)}")
    d = q["data"]
    out.append(f"\nINCLUDED: {d['includes']}. Check-in {d['check_in']}, check-out {d['check_out']}, "
               f"breakfast {d['breakfast']}. Payment: {d['deposit']}.")
    for n in q["notes"]:
        out.append(f"NOTE: {n}")
    for g in q["gaps"]:
        out.append(f"GAP: {g}")
    return "\n".join(out)
