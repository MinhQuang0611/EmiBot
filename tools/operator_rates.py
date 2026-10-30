"""Price a tour operator booking from that operator's own contract, offers included, so the intake row's rate
fields and notes item 6 never rest on mental arithmetic (dev, 2026-10-29: skills/tour-operators.md step 3).
Data: docs/rate-knowledge/<operator>-rates.json, copied from <operator>.md. Each operator hears only its own
rates (docs/rate-knowledge/README.md rule 1).

One call prices one room line (one room type = one sheet row): adults and child ages are per room, `rooms`
multiplies. What the contract doesn't settle is a GAP line, for Karen.

JSON shape (every amount VND; a per-season amount is {season: n} or one number for all seasons):
  operator, label, rate_source, valid_from, valid_to
  periods       [{from, to, season}]                 every night of a stay must fall in one
  holidays      [{from, to, name}] + holiday_season  a holiday night takes holiday_season over its period
  release_days  {season: days}                        cut-off; the stay's longest one counts
  rooms         {room_code: {name, persons, rates {season: n}, capacity [[adults, children], ...], allotment}}
  children      {infant_under, adult_from, free_if_spare_bed, bands [{from, to, per_night}]}
  meals         {base, supplements {HB|FB: [{from, to, per_night}]}}   per person per night, by age
  early_bird    {tiers [{min_days, pct}], on [room|child|meal], stay_windows, booked_windows, except_seasons}
  free_nights   {every, multiply, which: cheapest|last|unspecified, on [room|child|meal], stay_windows}
  combine       cascade | cumulative | unknown        free nights and early bird together
  spo           {required, eb_tokens, free_tokens, codes {CODE: {pct, on}}}   Odeon: offers come from the voucher
  payment, gaps  a string is always printed; {text, room?, child_ages?: [from, to], nights?: [from, to]} only
                 when every condition given holds: that room, a child of that age without a spare bed, a night there
"""
import json
import os
import re
from datetime import date, datetime, timedelta

KNOWLEDGE = os.path.join(os.path.dirname(__file__), "..", "docs", "rate-knowledge")
FILES = {"Anex": "anex-rates.json", "Crystal Bay": "crystalbay-rates.json", "Odeon": "odeon-rates.json",
         "Pegas": "pegas-rates.json", "Selfie": "selfie-rates.json"}
NO_CONTRACT = {"Fun and Sun": "Fun and Sun has no contract this season: leave the rate blank, "
                              "'no Fun and Sun contract this season' in missing_info, and flag it to Karen"}
PARTS = ("room", "child", "meal")


class RateError(Exception):
    pass


def load(operator):
    if operator in NO_CONTRACT:
        raise RateError(NO_CONTRACT[operator])
    if operator not in FILES:
        raise RateError(f"no contract file for {operator!r}; tour operators with one: {', '.join(sorted(FILES))}")
    path = os.path.join(KNOWLEDGE, FILES[operator])
    if not os.path.exists(path):
        raise RateError(f"{FILES[operator]} is not written yet: price {operator} from "
                        f"docs/rate-knowledge/{FILES[operator].replace('-rates.json', '.md')} and mark it 'to check'")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_date(s):
    try:
        return datetime.strptime(s.strip(), "%d/%m/%Y").date()
    except ValueError:
        raise RateError(f"{s!r} is not DD/MM/YYYY") from None


def _d(s):
    return date.fromisoformat(s)


def _in(windows, d):
    return any(_d(a) <= d <= _d(b) for a, b in windows)


def _amount(v, season):
    if isinstance(v, dict):
        if season not in v:
            raise RateError(f"no amount for season {season!r} in {v}")
        return v[season]
    return v


def season_of(data, night):
    for h in data.get("holidays", ()):
        if _d(h["from"]) <= night <= _d(h["to"]):
            return data["holiday_season"], h["name"]
    for p in data["periods"]:
        if _d(p["from"]) <= night <= _d(p["to"]):
            return p["season"], None
    return None, None


def nights(data, arrival, departure):
    if departure <= arrival:
        raise RateError("departure must be after arrival")
    out, outside = [], []
    d = arrival
    while d < departure:
        season, hol = season_of(data, d)
        if season is None:
            outside.append(d)
        out.append((d, season, hol))
        d += timedelta(days=1)
    if outside:
        raise RateError(f"nights {', '.join(f'{n:%d/%m/%Y}' for n in outside)} are outside the {data['label']} "
                        f"({_d(data['valid_from']):%d/%m/%Y}–{_d(data['valid_to']):%d/%m/%Y}): no contract rate, Karen")
    return out


def _band(bands, age, season):
    for b in bands:
        if b["from"] <= age < b["to"]:
            return _amount(b["per_night"], season)
    raise RateError(f"no band for age {age} in {bands}")


def release(data, night_list, booked):
    """(cut-off days for this stay, days booked ahead, inside the allotment window?)."""
    rel = data.get("release_days") or {}
    days = max((rel.get(s, 0) for _, s, _ in night_list), default=0)
    ahead = (night_list[0][0] - booked).days
    return days, ahead, ahead >= days


def _offers(data, spo, ahead, gaps):
    """Which offers apply: (eb_pct or None, free nights on?, [(code, pct, on)]). Odeon: only what the voucher's
    SPO code says (skills/tour-operators.md, Odeon step 3). Others: everything the contract gives."""
    eb, tiers = data.get("early_bird"), (data.get("early_bird") or {}).get("tiers", ())
    tier = max((t["pct"] for t in tiers if ahead >= t["min_days"]), default=0)
    conf = data.get("spo")
    if spo is not None and not conf:
        raise RateError(f"{data['operator']} vouchers carry no SPO code: its offers are worked out from the contract "
                        f"(leave out --spo)")
    if not conf or not conf.get("required"):
        return (tier or None) if eb else None, bool(data.get("free_nights")), []
    if spo is None:
        raise RateError(f"{data['operator']} is priced with exactly the offer the voucher's SPO code applies: pass "
                        f"--spo <code[,code]> as printed on the voucher, or --spo none")
    eb_pct, free, extra = None, False, []
    for token in [t.strip().upper() for t in spo if t.strip()]:
        if token == "NONE":
            continue
        m = re.fullmatch(r"([A-Z]+)(\d+)?%?", token.replace(" ", ""))
        word, num = (m.group(1), m.group(2)) if m else (token, None)
        if word in conf.get("eb_tokens", ()):
            eb_pct = int(num) if num else tier
            if num and int(num) != tier:
                gaps.append(f"voucher SPO {token} gives {num}% early booking; booked {ahead} days ahead the contract "
                            f"tier is {tier}%. Priced at the voucher's {num}% — Karen to check")
            if not eb_pct:
                gaps.append(f"voucher SPO {token} but booked only {ahead} days ahead: no early-booking tier applies")
        elif token in conf.get("free_tokens", ()):
            free = True
        elif token in conf.get("codes", {}):
            c = conf["codes"][token]
            extra.append((token, c["pct"], c["on"]))
            if c.get("note"):
                gaps.append(c["note"])
        else:
            raise RateError(f"SPO code {token!r} is not in the {data['label']}: known "
                            f"{sorted(conf.get('eb_tokens', [])) + sorted(conf.get('free_tokens', [])) + sorted(conf.get('codes', {}))}"
                            f" — Karen")
    return eb_pct, free, extra


def price(operator, arrival, departure, room, adults, kid_ages=(), rooms=1, meal="BB", booked=None, spo=None,
          data=None):
    data = data or load(operator)
    if room not in data["rooms"]:
        raise RateError(f"{room} is not on the {data['label']}: rooms {', '.join(data['rooms'])}")
    if adults < 1 or rooms < 1:
        raise RateError("at least one adult and one room")
    if booked is None:
        raise RateError("the booking date is needed for the early booking and the cut-off: --booked DD/MM/YYYY "
                        "(the voucher's booking date, else the day the email arrived)")
    r = data["rooms"][room]
    night_list = nights(data, arrival, departure)
    gaps = [g for g in data.get("gaps", ()) if isinstance(g, str)]
    gaps += [g for code, g in data.get("room_gaps", {}).items() if code == room]
    rel_days, ahead, inside = release(data, night_list, booked)
    if ahead < 0:
        raise RateError(f"booked {booked:%d/%m/%Y} is after arrival {arrival:%d/%m/%Y}")

    ch = data["children"]
    kids = sorted(kid_ages, reverse=True)
    adults_eq = adults + sum(1 for a in kids if a >= ch["adult_from"])
    kids = [a for a in kids if a < ch["adult_from"]]
    infants = [a for a in kids if a < ch["infant_under"]]
    counted = [a for a in kids if a >= ch["infant_under"]]
    cap = r.get("capacity")
    if cap and not any(adults_eq <= a and len(counted) <= c for a, c in cap):
        gaps.append(f"{adults_eq} adult(s) + children {counted} is over the {room} capacity "
                    f"{' or '.join(f'{a}A+{c}C' for a, c in cap)} — check the voucher, Karen")
    # A child takes a spare bed (no charge) while the adults leave one: 1 adult + 1 child in a double.
    charged = [a for i, a in enumerate(counted)
               if not (ch.get("free_if_spare_bed") and adults_eq + i < r["persons"])]

    for g in data.get("gaps", ()):
        if isinstance(g, dict) and g.get("room", room) == room                 and ("child_ages" not in g or any(g["child_ages"][0] <= a < g["child_ages"][1] for a in charged))                 and ("nights" not in g or any(_in([g["nights"]], d) for d, _, _ in night_list)):
            gaps.append(g["text"])

    plan = (meal or data["meals"]["base"]).upper()
    supp = None
    if plan != data["meals"]["base"]:
        supp = data["meals"].get("supplements", {}).get(plan)
        if supp is None:
            raise RateError(f"meal plan {plan} is not in the {data['label']}: "
                            f"{[data['meals']['base']] + list(data['meals'].get('supplements', {}))}")
    persons = [ch["adult_from"]] * adults_eq + kids

    per = []
    for d, season, hol in night_list:
        per.append({"date": d, "season": season, "holiday": hol,
                    "room": _amount(r["rates"][season], season),
                    "child": sum(_band(ch["bands"], a, season) for a in charged),
                    "meal": sum(_band(supp, a, season) for a in persons) if supp else 0})
    gross = {p: sum(n[p] for n in per) for p in PARTS}

    eb_pct, free_on, extra = _offers(data, spo, ahead, gaps)
    lines = []
    paid = [dict(n) for n in per]

    fn = data.get("free_nights")
    free_dates = []
    if fn and free_on:
        eligible = [i for i, n in enumerate(per) if not fn.get("stay_windows") or _in(fn["stay_windows"], n["date"])]
        k = (len(eligible) // fn["every"]) if fn.get("multiply") else int(len(eligible) >= fn["every"])
        if k:
            value = lambda i: sum(per[i][p] for p in fn["on"])
            if fn["which"] == "last":
                pick = eligible[-k:]
            else:
                pick = sorted(eligible, key=lambda i: (value(i), -i))[:k]
                if fn["which"] == "unspecified" and len({value(i) for i in eligible}) > 1:
                    gaps.append("the contract doesn't say which night is free; priced the cheapest — Karen to check")
            off = {p: 0 for p in PARTS}
            for i in pick:
                for p in fn["on"]:
                    off[p] += paid[i][p]
                    paid[i][p] = 0
            free_dates = sorted(per[i]["date"] for i in pick)
            lines.append(("free", f"stay {fn['every']} pay {fn['every'] - 1}"
                          + (" (multiplied)" if fn.get("multiply") else "")
                          + f": {k} free night(s) {', '.join(f'{d:%d/%m}' for d in free_dates)}", off))

    eb = data.get("early_bird")
    if eb and eb_pct:
        if not eb.get("booked_windows") or _in(eb["booked_windows"], booked):
            ok = [i for i, n in enumerate(per)
                  if (not eb.get("stay_windows") or _in(eb["stay_windows"], n["date"]))
                  and n["season"] not in eb.get("except_seasons", ())]
            off = {p: 0 for p in PARTS}
            for i in ok:
                for p in eb["on"]:
                    cut = round(paid[i][p] * eb_pct / 100)
                    off[p] += cut
                    paid[i][p] -= cut
            skipped = len(per) - len(ok)
            if any(off.values()):
                lines.append(("eb", f"early booking {eb_pct}% (booked {ahead} days ahead)"
                              + (f", not on {skipped} night(s) outside its dates" if skipped else ""), off))
            if free_dates and data.get("combine") == "unknown":
                gaps.append(f"the {data['label']} doesn't say whether early booking combines with the free night; "
                            f"priced with both — Karen to confirm")
        else:
            gaps.append(f"booked {booked:%d/%m/%Y}: outside the early booking sale window — no early booking")

    for code, pct, on in extra:
        off = {p: 0 for p in PARTS}
        for n in paid:
            for p in on:
                cut = round(n[p] * pct / 100)
                off[p] += cut
                n[p] -= cut
        lines.append(("spo", f"SPO {code} {pct}%", off))

    net = {p: sum(n[p] for n in paid) for p in PARTS}
    return {"operator": data["operator"], "data": data, "room": room, "room_name": r["name"], "rooms": rooms,
            "adults": adults_eq, "kid_ages": sorted(kid_ages, reverse=True), "charged_kids": charged,
            "infants": infants, "meal": plan, "nights": per, "gross": gross, "offers": lines, "net": net,
            "total_room": sum(net.values()), "total": sum(net.values()) * rooms, "booked": booked,
            "ahead": ahead, "release_days": rel_days, "inside_release": inside,
            "allotment": r.get("allotment"), "gaps": gaps}


def money(n):
    return f"{n:,.0f}"


def _rates_text(per, part="room"):
    """'2,200,000 × 7' or '1,750,000 × 3 (A) + 2,200,000 × 4 (B)'."""
    groups = []
    for n in per:
        key = (n[part], n["season"])
        if groups and groups[-1][0] == key:
            groups[-1][1] += 1
        else:
            groups.append([key, 1])
    if len({k[0] for k, _ in groups}) == 1:
        return f"{money(groups[0][0][0])} × {len(per)} night(s)"
    return " + ".join(f"{money(v)} × {c} ({s})" for (v, s), c in groups)


def row_fields(q):
    """Suggested values for the intake row's rate columns and notes item 6."""
    d, n, rooms = q["data"], len(q["nights"]), q["rooms"]
    rates = [x["room"] for x in q["nights"]]
    rate = rates[0] if len(set(rates)) == 1 else round(sum(rates) / n)
    promo = "; ".join(text for _, text, _ in q["offers"])
    sur = []
    if q["gross"]["child"]:
        sur.append(f"Child {_rates_text(q['nights'], 'child')} (ages {q['charged_kids']})")
    if q["gross"]["meal"]:
        sur.append(f"{q['meal']} supplement {_rates_text(q['nights'], 'meal')}")
    calc = [f"{d['rate_source']}: {_rates_text(q['nights'])} = {money(q['gross']['room'])}"]
    if q["gross"]["child"]:
        calc.append(f"+ child {money(q['gross']['child'])}")
    if q["gross"]["meal"]:
        calc.append(f"+ {q['meal']} {money(q['gross']['meal'])}")
    for _, text, off in q["offers"]:
        calc.append(f"{text} −{money(sum(off.values()))}")
    calc.append(f"= {money(q['total_room'])}" + (f" × {rooms} rooms = {money(q['total'])}" if rooms > 1 else ""))
    return {
        "rate_source": d["rate_source"],
        "rate_per_night_vnd": str(rate),
        "discount_promo": promo,
        "Average rate per night after discount": str(round(q["net"]["room"] / n)),
        "surcharge": "; ".join(sur),
        "Surcharge amount": str((q["net"]["child"] + q["net"]["meal"]) * rooms) if sur else "",
        "total_vnd": str(q["total"]),
        "meal_plan": q["meal"],
        "notes item 6": "6. " + "; ".join(calc) + f", {q['meal']}, {d.get('includes', 'incl. tax')}",
    }


def render(q):
    d = q["data"]
    out = [f"RATES: {d['label']} ({q['operator']} only — never quoted to anyone else)",
           f"STAY {q['nights'][0]['date']:%d/%m/%Y} – {q['nights'][-1]['date'] + timedelta(days=1):%d/%m/%Y}, "
           f"{len(q['nights'])} night(s); {q['rooms']} × {q['room']} {q['room_name']}; per room {q['adults']} adult(s)"
           + (f", children {q['kid_ages']}" if q["kid_ages"] else "") + f"; {q['meal']}"]
    runs = []  # consecutive nights priced the same: one line
    for n in q["nights"]:
        key = (n["season"], n["holiday"], n["room"], n["child"], n["meal"])
        if runs and runs[-1][0] == key:
            runs[-1][2] = n["date"]
        else:
            runs.append([key, n["date"], n["date"]])
    for (season, hol, room, child, meal), first, last in runs:
        when = f"{first:%d/%m/%Y}" if first == last else f"{first:%d/%m/%Y}–{last:%d/%m/%Y}"
        extra = "".join(f", {p} {money(v)}" for p, v in (("child", child), ("meal", meal)) if v)
        out.append(f"  nights {when}: {season}" + (f" ({hol})" if hol else "") + f" — room {money(room)}{extra}")
    g = q["gross"]
    out.append(f"GROSS per room: room {money(g['room'])}"
               + (f" + child {money(g['child'])} (ages charged {q['charged_kids']})" if g["child"] else "")
               + (f" + {q['meal']} {money(g['meal'])}" if g["meal"] else ""))
    if q["infants"]:
        out.append(f"  free (under {d['children']['infant_under']}): ages {q['infants']}")
    for _, text, off in q["offers"]:
        parts = ", ".join(f"{p} −{money(v)}" for p, v in off.items() if v)
        out.append(f"OFFER {text}: {parts or 'nothing to take off'}")
    if not q["offers"]:
        out.append("OFFER none applies")
    out.append(f"TOTAL per room {money(q['total_room'])}" + (f" × {q['rooms']} rooms" if q["rooms"] > 1 else "")
               + f" = {money(q['total'])} VND")
    state = "inside" if q["inside_release"] else "AFTER RELEASE (on request)"
    out.append(f"CUT-OFF {q['release_days']} days; booked {q['booked']:%d/%m/%Y}, {q['ahead']} days before arrival "
               f"→ {state}. Allotment for {q['room']}: {q['allotment']}")
    if d.get("payment"):
        out.append(f"PAYMENT: {d['payment']}")
    out.append("\nROW FIELDS (copy; check against the voucher):")
    for k, v in row_fields(q).items():
        out.append(f"  {k}: {v}")
    for gap in q["gaps"]:
        out.append(f"GAP: {gap}")
    return "\n".join(out)
