"""The stop-sale chart for the B2B and OTA sites, from Long's tool (dev, 2026-11-21).

Emi no longer works the list out from the Future Availability sheet (dev, 2026-11-05 to 21/11). Long's tool writes
two HAYA sheets every hour into a Drive folder (config.STOP_SALE_FOLDER_ID), each named with the Vietnam date:
"Stop Sale — HAYA — 2026-11-21" (a merged type with 1 room or fewer free is stopped) and
"Stop Sale OTA — HAYA — 2026-11-21" (50% of the free rooms open to the channel, rounded down; 0 = stopped). The older
copies go into its Backup folder. The partners get the OTA one (dev, 21/11), as Long made it, exported to .xlsx.

Two tabs: "Stop sale HAYA" (the monthly colour chart the partners read) and "Danh sách", one line per stopped night
and room type with its status: STOPPED, "NEW - dd/mm/yyyy" (stopped since Long's last version) or
"REOPENED - dd/mm/yyyy" (open again). Emi reads "Danh sách" to know what is closed and sends the chart only when the
closed nights differ from the list the partners last got (dev, 21/11: 09:00, 12:00, 17:00; "only send if there are
changes between each version. do not send email if everything stays the same"). A night that has passed is no change.
The 24/12/2026-06/01/2027 close (dev, 14/11) is in Long's chart: every type 0 on those nights.
"""
import re
import urllib.parse
from datetime import date, datetime, timezone

SHEETS = "https://sheets.googleapis.com/v4/spreadsheets"
DRIVE = "https://www.googleapis.com/drive/v3/files"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
# "Stop Sale OTA — HAYA — 2026-11-21": OTA, HAYA (never Palma, which shares the folder), the Vietnam date.
TITLE = re.compile(r"^\s*Stop\s+Sale\s+OTA\s*[—–-]+\s*HAYA\s*[—–-]+\s*(\d{4})-(\d{2})-(\d{2})\s*$", re.I)
LIST_TAB = "Danh sách"
# Long's tool writes a new version every hour (xx:33-xx:48); one older than this means it has stopped.
MAX_AGE_HOURS = 3
PROPERTY = "HAYA Hotel Phu Quoc"
SUBJECT = "Stop Sale / Sold Out Room Type Chart"
MAX_LISTED = 40  # changed lines written out in the email; the chart has them all
# Bcc: the partners compete, and HAYA's own list went out with an empty To (10/09).
# Dev, 2026-11-13: WebBeds' second and third, Traveloka's last five and Trip.com's khoi.duong added; HotelBeds dropped.
RECIPIENTS = (
    "suppliers@webbeds.com", "Stopsales.APAC@webbeds.com", "tuankhang.truong@webbeds.com",  # WebBeds
    "info.partner@tiket.com",  # Tiket
    "hotelsupport@trip.com", "khoi.duong@trip.com",  # Trip.com B2B
    "roomupdate@mgholiday.com",  # MG
    "phuong.truong@traveloka.com", "hotel@traveloka.com", "loi.le@traveloka.com", "hotel-mm-vn@traveloka.com",
    "phuong.tran@traveloka.com", "long.duong@traveloka.com", "dung.huynh@traveloka.com",  # Traveloka
    "booking@ohmyhotel.com", "stopsell@ohmyhotel.com",  # OhMyHotel
)


class StopSaleError(Exception):
    pass


def file_date(name):
    """The Vietnam date in an OTA HAYA file's name, or None for any other file (Palma's, the plain chart)."""
    m = TITLE.match(name or "")
    return date(*(int(x) for x in m.groups())) if m else None


def latest(call, folder_id):
    """The newest "Stop Sale OTA — HAYA" sheet directly in the folder (not its Backup): latest date in the name,
    then latest made."""
    q = urllib.parse.quote(f"'{folder_id}' in parents and trashed=false "
                           "and mimeType='application/vnd.google-apps.spreadsheet'")
    files = call("GET", f"{DRIVE}?q={q}&fields=files(id,name,createdTime)&orderBy=createdTime%20desc&pageSize=50"
                        "&supportsAllDrives=true&includeItemsFromAllDrives=true").get("files", [])
    ota = [f for f in files if file_date(f.get("name"))]
    if not ota:
        raise StopSaleError(f"no 'Stop Sale OTA — HAYA' sheet in Drive folder {folder_id} (shared with Emi's "
                            f"service account?)")
    return max(ota, key=lambda f: (file_date(f["name"]), f.get("createdTime", "")))


def _night(text):
    try:
        return datetime.strptime(text.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def parse_list(rows):
    """{(night, room type)} closed, from the "Danh sách" tab: STOPPED and NEW lines are closed, REOPENED lines open.
    A header or status Emi doesn't know stops the list: guessing what is closed is worse than no email."""
    if not rows or [c.strip() for c in rows[0][:4]] != ["Đêm", "Thứ", "Hạng", "Trạng thái"]:
        raise StopSaleError(f"'{LIST_TAB}' tab header is not Đêm / Thứ / Hạng / Trạng thái: "
                            f"{(rows or [[]])[0][:6]}")
    shut = set()
    for i, r in enumerate(rows[1:], 2):
        r = list(r) + [""] * 4
        if not any(c.strip() for c in r[:4]):
            continue
        night, room, status = _night(r[0]), r[2].strip(), r[3].strip().upper()
        if night is None or not room:
            raise StopSaleError(f"'{LIST_TAB}' row {i} not readable: {r[:4]}")
        if status.startswith(("STOPPED", "NEW")):
            shut.add((night, room))
        elif not status.startswith("REOPENED"):
            raise StopSaleError(f"'{LIST_TAB}' row {i}: status {r[3]!r} is not STOPPED / NEW / REOPENED")
    return shut


def load(call, folder_id):
    """{id, name, date, created (aware datetime), closed}: the newest OTA chart and what it closes."""
    f = latest(call, folder_id)
    rng = urllib.parse.quote(f"'{LIST_TAB}'!A1:F3000", safe="")
    rows = call("GET", f"{SHEETS}/{f['id']}/values/{rng}").get("values", [])
    created = f.get("createdTime")
    return {"id": f["id"], "name": f["name"], "date": file_date(f["name"]), "closed": parse_list(rows),
            "created": datetime.fromisoformat(created.replace("Z", "+00:00")) if created else None}


def export_xlsx(call, fid):
    """The whole chart as Excel, both tabs and the colours, exactly as Long's tool made it."""
    return call("GET", f"{DRIVE}/{fid}/export?mimeType={urllib.parse.quote(XLSX, safe='')}", raw=True)


def stale(data, now, today):
    """'' while the chart is today's and fresh, else why not. now: an aware datetime."""
    if data["date"] != today:
        return f"Long's newest chart is dated {data['date']:%d/%m/%Y}, not today"
    if data["created"] is not None:
        hours = (now - data["created"].astimezone(timezone.utc)).total_seconds() / 3600
        if hours > MAX_AGE_HOURS:
            return f"Long's newest chart was made {hours:.0f} hours ago (his tool makes one every hour)"
    return ""


def key(room):
    """Room names compared without case or spaces: Emi's own lists said "DELUXE SEAVIEW", Long's "Deluxe Sea View"."""
    return re.sub(r"[^A-Z]", "", room.upper())


def changes(now, before, today):
    """(newly stopped, reopened), each [(night, room)] sorted, nights from today on. before=None: the first list."""
    if before is None:
        return sorted(x for x in now if x[0] >= today), []
    old = {(n, key(r)) for n, r in before}
    new_keys = {(n, key(r)) for n, r in now}
    return (sorted((n, r) for n, r in now if n >= today and (n, key(r)) not in old),
            sorted((n, r) for n, r in before if n >= today and (n, key(r)) not in new_keys))


def to_state(nights):
    return sorted([n.isoformat(), r] for n, r in nights)


def from_state(saved):
    return {(date.fromisoformat(n), r) for n, r in saved}


def subject(today):
    return f"{SUBJECT} - {PROPERTY} - {today:%d %b %Y}"


def attachment_name(today):
    return f"Stop-Sale-HAYA-{today.isoformat()}.xlsx"


def _listed(lines):
    out = [f"- {n:%d %b %Y} ({n:%a}): {r}" for n, r in lines[:MAX_LISTED]]
    if len(lines) > MAX_LISTED:
        out.append(f"- and {len(lines) - MAX_LISTED} more, in the attached chart")
    return "\n".join(out)


def body(new, reopened, today, first):
    parts = [f"Dear Partner,\n\nPlease find attached the stop sale chart for {PROPERTY}, updated on "
             f"{today:%d %b %Y}."]
    if first:
        parts.append("Please close every room type and date marked as stopped in the chart.")
    else:
        if new:
            parts.append("New stop sale:\n" + _listed(new))
        if reopened:
            parts.append("Re-open:\n" + _listed(reopened))
        parts.append("Please close the room types and dates marked as stopped in the chart, and re-open those "
                     "listed above.")
    parts.append("Best regards,\nReservations Team\nHAYA Hotel Phu Quoc, Trademark Collection by Wyndham\n"
                 "sales@haya-hotels.com")
    return "\n\n".join(parts)
