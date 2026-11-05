"""Rooms still free per room type per night, from HAYA's Future Availability sheet (dev, 2026-10-27).

The sheet: row 1 = "Room Type", "Number Of Rooms", then one column per night ("27/10 Tuesday"); one row per
room type ("STD - STANDARD GARDEN", total, then the rooms free that night); below them a summary block with
an "Occupancy %" row. The year is not in the cells: it comes from the window in the title
("Future Availability — HAYA — 2026-10-27_2027-02-23"). A cell of 0 means none left; below 0 is overbooked,
also none left.
"""
import re
import urllib.parse
from datetime import date, timedelta

SHEETS = "https://sheets.googleapis.com/v4/spreadsheets"
DRIVE = "https://www.googleapis.com/drive/v3/files"
# Each export is a new file, so the sheet is found in its Drive folder, never by a fixed ID: Emi read the trashed copy
# of 30/10 for days and told Aya Batyrova rooms were free that had gone (Karen, 04/11). The file's name says the day
# it starts from (dev, 04/11); a newest file dated before yesterday says nothing about what is free today.
MAX_AGE_DAYS = 1
WINDOW = re.compile(r"(\d{4})-(\d{2})-(\d{2})_(\d{4})-(\d{2})-(\d{2})")
# inquiries-and-quotes.md: a night over 50% occupancy is not offered when check-in is more than 14 days away.
STOP_SALE_OCCUPANCY = 50.0
STOP_SALE_DAYS = 14


class AvailabilityError(Exception):
    pass


def is_haya(name):
    """The folder holds Palma's export beside HAYA's, and other files. Only HAYA's is ever read (dev, 2026-11-04)."""
    return (bool(re.search(r"\bHAYA\b", name, re.I)) and "future availability" in name.lower()
            and "palma" not in name.lower())


def window(name):
    """(first night, last night) from a name like '… — 2026-11-04_2027-03-03'; None when it has no such dates."""
    m = WINDOW.search(name)
    if not m:
        return None
    g = [int(x) for x in m.groups()]
    return date(*g[:3]), date(*g[3:])


def latest_haya(call, folder_id):
    """The HAYA export whose name starts latest (dev, 04/11: the dates in the file decide). Refuses when there is
    none rather than guess at another file."""
    q = urllib.parse.quote(f"'{folder_id}' in parents and trashed=false "
                           "and mimeType='application/vnd.google-apps.spreadsheet'")
    files = call("GET", f"{DRIVE}?q={q}&fields=files(id,name)&orderBy=createdTime%20desc&pageSize=50"
                        "&supportsAllDrives=true&includeItemsFromAllDrives=true").get("files", [])
    haya = [f for f in files if is_haya(f.get("name", "")) and window(f["name"])]
    if not haya:
        raise AvailabilityError(f"no HAYA Future Availability sheet in Drive folder {folder_id}")
    # max keeps the first of equals: the hourly export repeats the same name, and the list is newest first
    return max(haya, key=lambda f: window(f["name"]))


def load(call, folder_id):
    """Read the first tab of the newest HAYA sheet in the folder with the service-account transport and parse it."""
    f = latest_haya(call, folder_id)
    meta = call("GET", f"{SHEETS}/{f['id']}?fields=sheets.properties.title")
    tab = meta["sheets"][0]["properties"]["title"]
    rng = urllib.parse.quote(f"'{tab}'!A1:ZZ80", safe="")
    data = parse(f["name"], call("GET", f"{SHEETS}/{f['id']}/values/{rng}").get("values", []))
    data["as_of"] = data["start"]
    return data


def stale(data, now):
    """'' while the sheet is fresh, else the words saying how old it is. now: an aware datetime."""
    as_of = data.get("as_of")
    if as_of is None or (now.date() - as_of).days <= MAX_AGE_DAYS:
        return ""
    return f"dated {as_of:%d/%m/%Y}, {(now.date() - as_of).days} day(s) ago"


def _int(v):
    try:
        return int(str(v).strip())
    except ValueError:
        return None


def parse(title, rows):
    span = window(title)
    if not span:
        raise AvailabilityError(f"sheet title {title!r} has no date window like 2026-10-27_2027-02-23")
    start, end = span
    if not rows or len(rows[0]) < 3:
        raise AvailabilityError("availability sheet is empty")
    dates, year = [], start.year
    for cell in rows[0][2:]:
        dm = re.match(r"\s*(\d{1,2})/(\d{1,2})", cell)
        if not dm:
            break
        d = date(year, int(dm.group(2)), int(dm.group(1)))
        if dates and d < dates[-1]:  # 31/12 -> 01/01
            year += 1
            d = d.replace(year=year)
        dates.append(d)
    if not dates or dates[0] != start:
        raise AvailabilityError(f"first night column {dates[0] if dates else 'none'} does not match the title's "
                                f"window start {start:%d/%m/%Y}")
    rooms, occupancy = {}, {}
    for r in rows[1:]:
        label = (r[0] if r else "").strip()
        if " - " in label and len(r) > 2 and _int(r[1]) is not None:
            code, name = (x.strip() for x in label.split(" - ", 1))
            rooms[code] = {"name": name, "total": _int(r[1]),
                           "free": {d: _int(v) for d, v in zip(dates, r[2:]) if _int(v) is not None}}
        elif label.lower().startswith("occupancy"):
            occupancy = {d: float(v.strip().rstrip("%")) for d, v in zip(dates, r[2:]) if v.strip()}
    if not rooms:
        raise AvailabilityError("no room-type rows found (expected 'STD - STANDARD GARDEN', ...)")
    return {"title": title, "start": start, "end": end, "dates": dates, "rooms": rooms, "occupancy": occupancy}


def check(data, arrival, departure, today):
    """Per room type: the fewest rooms free on any night of the stay and the nights with none left;
    plus the stop-sale nights. Refuses a stay outside the sheet's window."""
    nights = [arrival + timedelta(days=i) for i in range((departure - arrival).days)]
    outside = [n for n in nights if n not in data["dates"]]
    if outside:
        raise AvailabilityError(f"nights {', '.join(f'{n:%d/%m/%Y}' for n in outside)} are outside the "
                                f"availability sheet ({data['start']:%d/%m/%Y}–{data['end']:%d/%m/%Y}): "
                                f"availability unknown, ask Karen")
    rooms = {}
    for code, r in data["rooms"].items():
        free = [r["free"].get(n) for n in nights]
        known = [f for f in free if f is not None]
        rooms[code] = {"name": r["name"], "min_free": min(known) if known else None,
                       "none_left": [n for n, f in zip(nights, free) if f is not None and f <= 0]}
    far = (arrival - today).days > STOP_SALE_DAYS
    stop = [n for n in nights if far and data["occupancy"].get(n, 0) > STOP_SALE_OCCUPANCY]
    return {"nights": nights, "rooms": rooms, "stop_sale": stop,
            "occupancy": {n: data["occupancy"].get(n) for n in nights}}


def fits(result, alloc):
    """Problems with selling this allocation ({code: rooms}); empty list = every room is free every night."""
    problems = []
    for code, count in alloc.items():
        r = result["rooms"].get(code)
        if r is None:
            problems.append(f"{code}: not on the availability sheet")
        elif r["none_left"]:
            problems.append(f"{code}: none left on {', '.join(f'{n:%d/%m}' for n in r['none_left'])}")
        elif r["min_free"] is not None and r["min_free"] < count:
            problems.append(f"{code}: {count} asked, only {r['min_free']} free on the fullest night")
    return problems


def render(data, result):
    out = [f"AVAILABILITY ({data['title']}), nights {result['nights'][0]:%d/%m/%Y}–{result['nights'][-1]:%d/%m/%Y}:"]
    for code, r in result["rooms"].items():
        if r["none_left"]:
            state = "NONE LEFT on " + ", ".join(f"{n:%d/%m}" for n in r["none_left"])
        else:
            state = f"free every night, fewest {r['min_free']}" + (" (LAST ROOM)" if r["min_free"] == 1 else "")
        out.append(f"  {code} {r['name']}: {state}")
    occ = ", ".join(f"{n:%d/%m} {v:.0f}%" for n, v in result["occupancy"].items() if v is not None)
    if occ:
        out.append(f"  occupancy: {occ}")
    if result["stop_sale"]:
        out.append(f"STOP-SALE: {', '.join(f'{n:%d/%m}' for n in result['stop_sale'])} over "
                   f"{STOP_SALE_OCCUPANCY:.0f}% with check-in more than {STOP_SALE_DAYS} days away — not offered")
    return "\n".join(out)
