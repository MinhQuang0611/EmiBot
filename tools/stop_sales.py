"""The daily stop-sell list for the B2B and OTA sites (dev, 2026-11-05).

Room types are first merged into the names the partners sell (MAPPED). A merged type with 1 room or fewer free on a
night is STOP SELL for that night. The PDF follows docs/Stop-Sell-Room-Types-HAYA--AGENCY-through-Feb2027 plus a last
column, NEW UPDATE, filled only on the day a line changes. The list is made every day; the partners get it only when
it differs from the day before.
"""
import os
from datetime import date

# Sheet code -> the name the partners see. None = never on the list (apartments aren't sold through them).
MAPPED = {
    "STD": "STANDARD DOUBLE",
    "STD-TWN": "SUPERIOR TWIN",
    "SUP-TWN": "SUPERIOR TWIN",
    "SUP-DBL": "SUPERIOR DOUBLE",
    "DLX-SV": "DELUXE SEAVIEW",
    "TW-DLX": "DELUXE SEAVIEW",
    "SUITE-SV": "SUITE SEAVIEW",
    "TPL": "TRIPLE",
    "TPL-SV": "TRIPLE",
    "QPL": "QUADRUPLE",
    "APT-02": None,
    "APT-04": None,
}
STOP_AT = 1
PROPERTY = "HAYA Hotel Phu Quoc"
SUBJECT = "Stop Sale / Sold Out Room Type Chart"
# Bcc: the partners compete, and HAYA's own list went out with an empty To (10/09).
RECIPIENTS = (
    "suppliers@webbeds.com",  # WebBeds
    "e.zhang@hbxgroup.com",  # HotelBeds
    "info.partner@tiket.com",  # Tiket
    "hotelsupport@trip.com",  # Trip.com B2B
    "roomupdate@mgholiday.com",  # MG
    "phuong.truong@traveloka.com", "hotel@traveloka.com",  # Traveloka
    "booking@ohmyhotel.com", "stopsell@ohmyhotel.com",  # OhMyHotel
)
STOP_SELL, OPEN = "STOP SELL", "OPEN"
NEW, REOPENED = "NEW", "REOPENED"


def code_problem(data):
    """'' when the sheet's room codes are exactly the mapped ones. A code added or gone would change what a merged
    type adds up to, so the list isn't made from it."""
    codes = set(data["rooms"])
    unknown, missing = sorted(codes - set(MAPPED)), sorted(set(MAPPED) - codes)
    if not unknown and not missing:
        return ""
    return "room codes differ from the stop-sell map" + (f", new: {', '.join(unknown)}" if unknown else "") \
        + (f", gone: {', '.join(missing)}" if missing else "")


def closed(data, today):
    """{(night, merged room type)} from today on with STOP_AT or fewer rooms free, the merged rows added together:
    an overbooked -1 beside 3 free leaves 2."""
    free = {}
    for code, r in data["rooms"].items():
        room = MAPPED[code]
        if room is None:
            continue
        for night, rooms in r["free"].items():
            if night >= today and rooms is not None:
                free[night, room] = free.get((night, room), 0) + rooms
    return {key for key, rooms in free.items() if rooms <= STOP_AT}


def lines(now, before, data, today):
    """The report's rows, by night then room type. before=None: the first list ever, nothing to compare with.
    A night that came back shows once as OPEN, so a partner can see what changed; past nights just drop off."""
    before = before if before is not None else now
    stamp = f"{today:%d %b %Y}"
    rows = [{"night": n, "room": r, "status": STOP_SELL, "update": "" if (n, r) in before else f"{NEW} - {stamp}"}
            for n, r in now]
    rows += [{"night": n, "room": r, "status": OPEN, "update": f"{REOPENED} - {stamp}"}
             for n, r in before - now if n >= today and n in data["dates"]]
    return sorted(rows, key=lambda x: (x["night"], x["room"]))


def to_state(nights):
    return sorted([n.isoformat(), r] for n, r in nights)


def from_state(saved):
    return {(date.fromisoformat(n), r) for n, r in saved}


def counts(rows):
    """(new stop-sell lines, reopened lines)."""
    return sum(r["update"].startswith(NEW) for r in rows), sum(r["status"] == OPEN for r in rows)


def subject(today):
    return f"{SUBJECT} - {PROPERTY} - {today:%d %b %Y}"


def body(rows, today, first):
    new, reopened = counts(rows)
    change = []
    if new:
        change.append(f"{new} new stop sell line(s)")
    if reopened:
        change.append(f"{reopened} line(s) reopened")
    update = "" if first else f" Changes since the last list ({', '.join(change)}) are marked in the NEW UPDATE column."
    return (f"Dear Partner,\n\nPlease find attached the stop sell list for {PROPERTY} as of {today:%d %b %Y}.{update}\n\n"
            "Please close the room types and dates marked STOP SELL, and open those marked OPEN.\n\n"
            "Best regards,\nReservations Team\nHAYA Hotel Phu Quoc, Trademark Collection by Wyndham\n"
            "sales@haya-hotels.com")


def write_pdf(rows, path):
    """The form of the agreed Excel list, landscape, header repeated on every page."""
    from reportlab.lib import colors, pagesizes
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

    blue, red, green, grid = (colors.HexColor(c) for c in ("#1F4E79", "#C00000", "#2E7D32", "#BFBFBF"))
    data = [["Property", "Date", "Date (ISO)", "Room Type", "Status", "NEW UPDATE"]]
    style = [("FONT", (0, 0), (-1, -1), "Helvetica", 10), ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 10),
             ("BACKGROUND", (0, 0), (-1, 0), blue), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
             ("ALIGN", (0, 0), (-1, 0), "CENTER"), ("ALIGN", (4, 1), (4, -1), "CENTER"),
             ("FONT", (4, 1), (4, -1), "Helvetica-Bold", 10), ("TEXTCOLOR", (4, 1), (4, -1), colors.white),
             ("GRID", (0, 0), (-1, -1), 0.5, grid), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    for i, r in enumerate(rows, 1):
        data.append([PROPERTY, f"{r['night']:%d %b %Y}", r["night"].isoformat(), r["room"], r["status"], r["update"]])
        style.append(("BACKGROUND", (4, i), (4, i), red if r["status"] == STOP_SELL else green))
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    doc = SimpleDocTemplate(path, pagesize=pagesizes.landscape(pagesizes.A4), title="HAYA Stop Sell List",
                            author=PROPERTY, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm,
                            bottomMargin=12 * mm)
    doc.build([Table(data, colWidths=[w * mm for w in (50, 28, 26, 62, 28, 72)], repeatRows=1, rowHeights=7 * mm,
                     style=TableStyle(style))])
