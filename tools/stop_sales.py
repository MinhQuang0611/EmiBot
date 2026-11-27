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
import io
import re
import urllib.parse
from datetime import date, datetime, timedelta, timezone

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
# Dev, 2026-11-27: Tiket's mai.do added.
# name: (the stop-sale addresses, the words of the company on an intake row). The addresses are also where a booking
# sold after the stop sale is declined (dev, 2026-11-26).
PARTNERS = {
    "WebBeds": (("suppliers@webbeds.com", "Stopsales.APAC@webbeds.com", "tuankhang.truong@webbeds.com"),
                ("webbeds", "dotw")),
    "Tiket": (("info.partner@tiket.com", "mai.do@tiket.com"), ("tiket", "tiketcom", "tiket com")),
    "Trip.com": (("hotelsupport@trip.com", "khoi.duong@trip.com"), ("trip com", "tripcom", "ctrip")),
    "MG": (("roomupdate@mgholiday.com",), ("mg", "mgholiday", "mg holiday", "mgbedbank", "mg bedbank")),
    "Traveloka": (("phuong.truong@traveloka.com", "hotel@traveloka.com", "loi.le@traveloka.com",
                   "hotel-mm-vn@traveloka.com", "phuong.tran@traveloka.com", "long.duong@traveloka.com",
                   "dung.huynh@traveloka.com"), ("traveloka",)),
    "OhMyHotel": (("booking@ohmyhotel.com", "stopsell@ohmyhotel.com"), ("ohmyhotel", "oh my hotel")),
}
RECIPIENTS = tuple(a for addresses, _ in PARTNERS.values() for a in addresses)


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


# ---- What the partners were told, and bookings they sold anyway (dev, 2026-11-26) ----
# MG AGIN303795261 (3 QPL 02-04/01/2027, mailed 25/11 23:49) and Tiket 80887501 (26-30/12) were sold on nights the
# chart had stopped since 21/11. Dev: "booking từ các trang online đổ về tuy nhiên mình đã thông báo stop sales thì
# Emi ... phải email lại cho họ và thông báo là booking này mình không nhận được do mình đã stop sales rồi"; no row
# on the intake sheet, a draft a person sends, and the partner gets 24 hours to close the dates on its side.
# The record is the chart itself as it left sales@ (Sent Items, the .xlsx), so a draft a person sent late counts
# from when it really went.
GRACE = timedelta(hours=24)
ATTACHMENT = re.compile(r"^Stop-Sale-HAYA-\d{4}-\d{2}-\d{2}\.xlsx$", re.I)
# Long's "Gồm các hạng" column names the room codes of each line; these are for a chart without it.
ROOM_CODES = {"STANDARDDOUBLE": ("STD",), "SUPERIORDOUBLE": ("SUP-DBL",), "SUPERIORTWIN": ("SUP-TWN", "STD-TWN"),
              "TRIPLE": ("TPL", "TPL-SV"), "QUADRUPLE": ("QPL",), "DELUXESEAVIEW": ("DLX-SV", "TW-DLX"),
              "SUITESEAVIEW": ("SUITE-SV",)}


def _words(text):
    return f" {re.sub(r'[^a-z0-9]+', ' ', str(text or '').lower()).strip()} "


def partner(company):
    """The stop-sale partner a row's company is, or ''. 'MG' -> 'MG', 'CÔNG TY TNHH OHMYHOTEL&CO VN' -> 'OhMyHotel'."""
    words = _words(company)
    for name, (_, keys) in PARTNERS.items():
        if any(_words(k) in words for k in keys):
            return name
    return ""


def is_chart_mail(subject):
    """A chart Emi sent, not a partner's reply on its thread ("RE: Stop Sale / …")."""
    return str(subject or "").strip().lower().startswith(SUBJECT.lower())


def parse_codes(rows):
    """{room type: (room codes)} from the "Gồm các hạng" column: "TPL + TPL-SV" -> ("TPL", "TPL-SV")."""
    out = {}
    for r in rows[1:]:
        r = list(r) + [""] * 6
        room, codes = str(r[2] or "").strip(), [c.strip().upper() for c in re.split(r"[+,]", str(r[5] or ""))]
        if room and any(codes):
            out.setdefault(room, set()).update(c for c in codes if c)
    return {k: tuple(sorted(v)) for k, v in out.items()}


def read_chart_xlsx(data):
    """(closed {(night, room)}, {room: codes}) from a sent chart's "Danh sách" tab."""
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    if LIST_TAB not in wb.sheetnames:
        raise StopSaleError(f"no '{LIST_TAB}' tab in the chart (tabs: {wb.sheetnames})")
    rows = [["" if c is None else (f"{c:%d/%m/%Y}" if isinstance(c, (date, datetime)) else str(c)) for c in r]
            for r in wb[LIST_TAB].iter_rows(values_only=True)]
    return parse_list(rows), parse_codes(rows)


def closed_codes(closed, codes):
    """({(room code, night)}, [room types with no codes]): each closed line by the codes it stands for."""
    pairs, unknown = set(), set()
    for night, room in closed:
        mine = codes.get(room) or ROOM_CODES.get(key(room))
        if not mine:
            unknown.add(room)
            continue
        pairs.update((c, night) for c in mine)
    return pairs, sorted(unknown)


def span_key(code, night):
    return f"{code.upper()}|{night.isoformat()}"


def apply_sent(spans, pairs, at):
    """One chart sent at `at` (ISO, UTC): what it closes stays or starts closed, what it leaves out is open from then.
    spans: {"QPL|2027-01-03": [[since, until or None], ...]}."""
    now = {span_key(c, n) for c, n in pairs}
    for k, sp in spans.items():
        if sp and sp[-1][1] is None and k not in now:
            sp[-1][1] = at
    for k in now:
        sp = spans.setdefault(k, [])
        if not sp or sp[-1][1] is not None:
            sp.append([at, None])


def prune(spans, today):
    for k in [k for k in spans if date.fromisoformat(k.split("|")[1]) < today - timedelta(days=7)]:
        del spans[k]


def _when(text):
    return datetime.fromisoformat(str(text).replace("Z", "+00:00"))


def leaks(spans, code, arrival, departure, received):
    """[(night, code, since)] of a booking's nights the partners had been told were stopped for at least GRACE when
    it came in (received: an aware datetime), and still were."""
    out, night = [], arrival
    while night < departure:
        for since, until in (spans or {}).get(span_key(code, night), []):
            if _when(since) + GRACE <= received and (until is None or _when(until) > received):
                out.append((night, code.upper(), _when(since)))
                break
        night += timedelta(days=1)
    return out
