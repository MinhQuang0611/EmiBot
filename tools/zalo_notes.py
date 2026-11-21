"""What Sunny already told an agency or guest on Zalo (dev, 2026-11-21: "các thông tin booking cần checking thêm cái
thông tin khách hàng đã req trước qua Zalo chưa").

Sunny writes one JSON line per thing she said into /data/shared/haya-notes.jsonl on the host (haya-notes.counter
holds her last N-number). A line:
  {"id": "N2", "at": "2026-11-05 21:35", "by": "sunny", "type": "sold_out", "agency": "VICTORIA TOUR",
   "guest": "...", "stay": "2026-11-08/2026-11-16", "rooms": "1 Twin", "said": "Đã báo HAYA hết phòng ...",
   "expect": "Mail đặt HAYA cho ... → cảnh báo người duyệt: Zalo đã báo hết", "src": "Zalo ...", "draft": "D957"}
`expect` is Sunny's instruction for the email side: what a booking email that follows should match, and to warn the
reviewer when it doesn't. Emi only reads the file; Sunny owns it.
"""
import json
import re
import unicodedata
from datetime import date

TYPES = {"sold_out": "đã báo hết phòng", "quote": "đã báo giá"}

# words every agency name shares: they say nothing about which agency it is
_GENERIC = {"tour", "tours", "travel", "travels", "du", "lich", "dl", "cong", "ty", "cty", "tnhh", "mtv", "company",
            "co", "ltd", "jsc", "and", "the", "haya", "hotel", "hotels", "zalo", "tm", "wyndham", "dmc", "group", "vn",
            "vietnam", "viet", "nam", "trademark", "collection", "by", "phu", "quoc", "pq"}
_MONEY = re.compile(r"\d{1,3}(?:[.,]\d{3})+")


def fold(s):
    """Lower case, no accents, đ -> d, anything not a letter or digit -> space."""
    s = unicodedata.normalize("NFD", str(s or "").replace("đ", "d").replace("Đ", "D"))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return " ".join(re.findall(r"[a-z0-9]+", s))


def load(path):
    """(notes, gap): every readable line of the file; gap says why there are none (file missing, unreadable)."""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        return [], f"Zalo notes not found at {path} (EMI_ZALO_NOTES): not checked"
    except OSError as e:
        return [], f"Zalo notes unreadable at {path}: {e}"
    notes = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            n = json.loads(line)
        except ValueError:
            continue  # Sunny may be writing the last line right now
        if isinstance(n, dict):
            notes.append(n)
    return notes, ""


def _iso(s):
    try:
        return date.fromisoformat(str(s).strip()[:10])
    except ValueError:
        return None


def _dmy(s):
    try:
        d, m, y = (int(x) for x in str(s).strip().split("/"))
        return date(y, m, d)
    except (ValueError, TypeError):
        return None


def stay(note):
    """(arrival, departure) of the note, or None."""
    parts = str(note.get("stay") or "").split("/")
    if len(parts) != 2:
        return None
    a, d = _iso(parts[0]), _iso(parts[1])
    return (a, d) if a and d else None


def _agency_words(name):
    return set(fold(name).split()) - _GENERIC


def same_agency(a, b):
    """One name's telling words all in the other's: 'VICTORIA TOUR' = 'Victoria Tour & Travel JSC'."""
    x, y = _agency_words(a), _agency_words(b)
    return bool(x and y) and (x <= y or y <= x)


def same_guest(a, b):
    """'THIEU DUNG' = 'Thiều Văn Dũng': the shorter name's words all in the longer one, two words at least
    (one shared word, a surname alone, says too little), or the same single word on both sides."""
    x, y = set(fold(a).split()), set(fold(b).split())
    if not x or not y:
        return False
    small, big = (x, y) if len(x) <= len(y) else (y, x)
    return small <= big and (len(small) >= 2 or x == y)


def match(notes, agency="", guests=(), arrival=None, departure=None):
    """The notes about this booking: the agency or a guest the same, and the stays overlapping when both have dates.
    A note with no stay counts only on a guest's name (an agency alone has many bookings).
    Matched on the agency alone, a note with exactly this stay wins over the rest (dev, 2026-11-21, Victoria Tour
    NPKM00750000002 22–26/11: nine notes overlapped, six of them sold-outs for other requests; only N111's quote and
    N124's block were this booking): the overlapping ones are shown only when no note has exactly these dates."""
    if isinstance(guests, str):
        guests = [g for g in re.split(r"[;\n]", guests) if g.strip()]
    hits = []
    for n in notes:
        by_guest = bool(n.get("guest")) and any(same_guest(n["guest"], g) for g in guests)
        by_agency = bool(agency and n.get("agency")) and same_agency(n["agency"], agency)
        if not (by_guest or by_agency):
            continue
        s = stay(n)
        if s and arrival and departure:
            if not (s[0] < departure and arrival < s[1]):
                continue
        elif not by_guest:
            continue  # no dates to put side by side: the agency's name alone isn't this booking
        hits.append((n, by_guest))
    exact = {id(n) for n, by_guest in hits if not by_guest and stay(n) == (arrival, departure)}
    if exact:
        return [n for n, by_guest in hits if by_guest or id(n) in exact]
    return [n for n, _ in hits]


def _money(text):
    return {int(re.sub(r"\D", "", m)) for m in _MONEY.findall(str(text or ""))}


def describe(n, rates=()):
    """One line for Emi's output and the reviewer: what Sunny said, when, and what she asked the email side to check.
    rates: the booking's per-night rates; a quote note naming none of them says so."""
    s = stay(n)
    when = f"{s[0]:%d/%m}–{s[1]:%d/%m/%Y}" if s else "no dates"
    who = " · ".join(x for x in (n.get("agency"), n.get("guest")) if x)
    line = (f"Zalo {n.get('id', '?')} ({n.get('at', '')}, {n.get('by', 'sunny')}) {TYPES.get(n.get('type'), n.get('type', ''))}"
            f" — {who}, {when}: {n.get('said', '')}")
    rates = {int(r) for r in rates if r}
    if n.get("type") == "quote" and rates:
        quoted = _money(n.get("said"))
        if quoted and not rates & quoted:
            line += (f" ⚠️ GIÁ KHÁC: sheet {', '.join(f'{r:,}' for r in sorted(rates))} / Zalo "
                     f"{', '.join(f'{q:,}' for q in sorted(quoted))}")
    if n.get("expect"):
        line += f" → {n['expect']}"
    return line


def for_rows(notes, rows):
    """The notes about a booking from its intake rows (cancelled rows left out), one line each."""
    live = [r for r in rows if r.get("action") != "CANCEL"] or list(rows)
    if not live:
        return []
    agency = next((r.get("company") for r in live if r.get("company")), "")
    guests = [g for r in live for g in re.split(r"[;\n]", str(r.get("guest_names") or "")) if g.strip()]
    arr = min((d for d in (_dmy(r.get("arrival")) for r in live) if d), default=None)
    dep = max((d for d in (_dmy(r.get("departure")) for r in live) if d), default=None)
    rates = {int(d) for d in (re.sub(r"\D", "", str(r.get("rate_per_night_vnd") or "")) for r in live) if d}
    return [describe(n, rates) for n in match(notes, agency, guests, arr, dep)]


def parse_dmy(s):
    return _dmy(s) if s else None
