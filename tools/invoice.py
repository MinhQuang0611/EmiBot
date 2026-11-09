"""Odeon's proforma invoice, made by Emi (dev's Odeon process, step 5; done by hand until 2026-11-09).

The workbook "HAYA Odeon Invoices 2026 - 2027" holds one tab per invoice, named by the Odeon reference. A new one is a
copy of the template tab Sheet1 (dev, 2026-11-09: "đây là mẫu"; layout, Odeon's address and the company's VND account,
Vietcombank 1020729617) with the booking's cells written over, then exported as Invoice_<ref>.pdf. Sheet1 still prints
USD, so the copy gets "Rate (VND)", "Net amount VND:" and a VND number format on the amounts. The cells, read from
tabs 4777887 / 716532:
  L8 invoice no. "HAYA - <group>", M8 invoice date, N8 due date (10 days before check-in)
  rows 13-17, one per room type: B arrival "DD.MM.YYYY", C departure, D service type, F pax names, G "HAYA HOTEL",
      H Odeon ref, I accommodation, J rooms, K nights, L pax ("2" or "2+2"), M rate per room per night, N amount
  K22 =SUM(N13:N17) (kept), C20 amount in words, B23 "Payment to be settled by: DD/MM/YYYY"
Emi never changes the bank block, Odeon's address or the layout: they come from the template.
"""
import os
import urllib.parse
from datetime import datetime, timedelta, timezone

SHEETS = "https://sheets.googleapis.com/v4/spreadsheets"
FIRST, LAST = 13, 17  # the line rows K22's SUM covers
SERVICE = {"BB": "Bed & Breakfast", "HB": "Half Board", "FB": "Full Board", "RO": "Room Only"}
# As on the invoices HAYA sent (4777887, 716532, 4762629, 2112774); the rest from the Odeon contract's room names.
ACCOMMODATION = {"STD": "STANDARD DOUBLE WITH WINDOW", "SUP-DBL": "SUPERIOR DOUBLE WITH BALCONY",
                 "SUP-TWN": "SUPERIOR TWIN WITH BALCONY", "DLX-SV": "DELUXE SEA VIEW WITH BALCONY",
                 "TPL": "TRIPLE ROOM", "QPL": "QUADRUPLE WITH BALCONY", "SUITE-SV": "SUITE SEA VIEW WITH BALCONY"}
TEMPLATE_TAB = "Sheet1"  # the template every invoice is copied from (dev, 2026-11-09)
VND = '#,##0" VND"'  # the amounts' format on the invoices sent in VND (tab 4609701)


class InvoiceError(Exception):
    pass


# --- amount in words, as the hotel writes it: "SEVENTEEN MILLION FIVE HUNDRED AND FIFTY-TWO THOUSAND ... DONG" ---
ONES = ("ZERO ONE TWO THREE FOUR FIVE SIX SEVEN EIGHT NINE TEN ELEVEN TWELVE THIRTEEN FOURTEEN FIFTEEN SIXTEEN "
        "SEVENTEEN EIGHTEEN NINETEEN").split()
TENS = "_ _ TWENTY THIRTY FORTY FIFTY SIXTY SEVENTY EIGHTY NINETY".split()


def _below_thousand(n):
    words = []
    if n >= 100:
        words.append(f"{ONES[n // 100]} HUNDRED")
        n %= 100
        if n:
            words.append("AND")
    if n >= 20:
        words.append(TENS[n // 10] + (f"-{ONES[n % 10]}" if n % 10 else ""))
    elif n:
        words.append(ONES[n])
    return " ".join(words)


def in_words(amount):
    amount = int(amount)
    if amount <= 0:
        raise InvoiceError(f"amount {amount} can't be invoiced")
    parts = []
    for size, name in ((10 ** 9, "BILLION"), (10 ** 6, "MILLION"), (10 ** 3, "THOUSAND"), (1, "")):
        chunk, amount = divmod(amount, size)
        if chunk:
            parts.append((_below_thousand(chunk) + f" {name}").strip())
    return " ".join(parts) + " VIETNAMESE DONG"


# --- the booking's cells ---
def _num(text):
    s = str(text or "").replace(",", "").replace(" ", "").strip()
    try:
        return int(round(float(s))) if s else 0
    except ValueError:
        raise InvoiceError(f"{text!r} is not a number") from None


def _dots(ddmmyyyy):
    return (ddmmyyyy or "").strip().replace("/", ".")


def _pax(adults, children):
    a, c = _num(adults), _num(children)
    return str(a) if not c else f"{a}+{c}"


def _names(guest_names):
    names = [n.strip() for n in (guest_names or "").replace("\n", ";").split(";") if n.strip()]
    return "".join(f"{n}," for n in names)


def lines(data):
    """One invoice line per room type, from invoice_data's rows (operators.invoice_data)."""
    out = []
    for x in data["rows"]:
        code = (x.get("room_code") or "").strip()
        if code not in ACCOMMODATION:
            raise InvoiceError(f"room code {code!r} has no Odeon room name: one of {', '.join(ACCOMMODATION)}")
        meal = (x.get("meal_plan") or "BB").strip().upper()
        if meal not in SERVICE:
            raise InvoiceError(f"meal plan {meal!r}: one of {', '.join(SERVICE)}")
        rooms, nights, total = _num(x.get("rooms")), _num(x.get("nights")), _num(x.get("total_vnd"))
        if not (rooms and nights and total):
            raise InvoiceError(f"row {x.get('_row')}: rooms, nights and total_vnd are needed ({rooms}, {nights}, "
                               f"{total})")
        rate = _num(x.get("Average rate per night after discount") or x.get("rate_per_night_vnd"))
        if rate * rooms * nights != total:
            # the line must add up on the invoice: the rate is what the total gives, the total is the sheet's
            rate = round(total / (rooms * nights))
        out.append([_dots(x.get("arrival")), _dots(x.get("departure")), SERVICE[meal], "", _names(x.get("guest_names")),
                    "HAYA HOTEL", int(data["voucher"]) if data["voucher"].isdigit() else data["voucher"],
                    ACCOMMODATION[code], rooms, nights,
                    _pax(x.get("adults"), x.get("children")), rate, total])
    if not out:
        raise InvoiceError("no rows to invoice")
    if len(out) > LAST - FIRST + 1:
        raise InvoiceError(f"{len(out)} room types: the invoice has {LAST - FIRST + 1} lines")
    return out


def cells(data, today):
    """{A1: value} for one invoice: every cell Emi writes, the unused line rows blanked."""
    body = lines(data)
    total = sum(line[-1] for line in body)
    if total != data["total"]:
        raise InvoiceError(f"the lines add up to {total:,}, the booking to {data['total']:,}")
    due = data["due"].strftime("%d/%m/%Y")
    out = {"L8": data["number"], "M8": today.strftime("%d/%m/%Y"), "N8": due, "C20": in_words(total),
           "B23": f"Payment to be settled by: {due}", "M12": "Rate (VND)", "K21": "Net amount VND:"}
    for i in range(LAST - FIRST + 1):
        row = body[i] if i < len(body) else [""] * 13
        for j, value in enumerate(row):
            out[f"{chr(ord('B') + j)}{FIRST + i}"] = value
    return out, total


# --- the workbook ---
def _q(a1):
    return urllib.parse.quote(a1, safe="")


class InvoiceBook:
    """The invoice workbook through the service account's Sheets transport (needs Editor on it)."""

    def __init__(self, book_id, call):
        self.id, self.call = book_id, call

    def tabs(self):
        resp = self.call("GET", f"{SHEETS}/{self.id}?fields=sheets.properties(sheetId,title,index)")
        return [s["properties"] for s in resp.get("sheets", [])]

    def values(self, tab, a1):
        resp = self.call("GET", f"{SHEETS}/{self.id}/values/{_q(f'{tab}!{a1}')}")
        return resp.get("values", [])

    def duplicate(self, source_id, title, index):
        resp = self.call("POST", f"{SHEETS}/{self.id}:batchUpdate", body={"requests": [{"duplicateSheet": {
            "sourceSheetId": source_id, "newSheetName": title, "insertSheetIndex": index}}]})
        return resp["replies"][0]["duplicateSheet"]["properties"]["sheetId"]

    def finish(self, gid):
        """The amounts N13:N17 and the total K22 in VND (the template formats them as dollars), and the pax names
        F13:F17 wrapped with the rows grown to fit (three names were cut off, 4801957)."""
        def cell(r0, r1, c0, c1, fmt, fields):
            return {"repeatCell": {"range": {"sheetId": gid, "startRowIndex": r0, "endRowIndex": r1,
                                             "startColumnIndex": c0, "endColumnIndex": c1},
                                   "cell": {"userEnteredFormat": fmt}, "fields": fields}}
        vnd = {"numberFormat": {"type": "NUMBER", "pattern": VND}}
        requests = [cell(FIRST - 1, LAST, 13, 14, vnd, "userEnteredFormat.numberFormat"),
                    cell(21, 22, 10, 11, vnd, "userEnteredFormat.numberFormat"),
                    cell(FIRST - 1, LAST, 5, 6, {"wrapStrategy": "WRAP", "verticalAlignment": "MIDDLE"},
                         "userEnteredFormat.wrapStrategy,userEnteredFormat.verticalAlignment"),
                    {"autoResizeDimensions": {"dimensions": {"sheetId": gid, "dimension": "ROWS",
                                                             "startIndex": FIRST - 1, "endIndex": LAST}}}]
        self.call("POST", f"{SHEETS}/{self.id}:batchUpdate", body={"requests": requests})

    def write(self, tab, values):
        data = [{"range": f"'{tab}'!{a1}", "values": [[v]]} for a1, v in values.items()]
        self.call("POST", f"{SHEETS}/{self.id}/values:batchUpdate", body={"valueInputOption": "RAW", "data": data})

    def pdf(self, gid):
        url = (f"https://docs.google.com/spreadsheets/d/{self.id}/export?format=pdf&gid={gid}&size=A4&portrait=false"
               "&fitw=true&gridlines=false&printtitle=false&sheetnames=false&pagenum=UNDEFINED&top_margin=0.5"
               "&bottom_margin=0.5&left_margin=0.5&right_margin=0.5")
        data = self.call("GET", url, raw=True)
        if not data.startswith(b"%PDF"):
            raise InvoiceError("the export didn't come back as a PDF")
        return data

    def can_edit(self):
        resp = self.call("GET", f"https://www.googleapis.com/drive/v3/files/{self.id}"
                                "?fields=capabilities(canEdit)&supportsAllDrives=true")
        return bool(resp.get("capabilities", {}).get("canEdit"))


def make(book, data, today, out_dir, out=print):
    """Invoice_<ref>.pdf for one booking, saved in out_dir; returns its path. A tab already named by the reference is
    the invoice made before (by a person or by Emi): it is exported as it is when its number and total are this
    booking's, and refused otherwise, never written over."""
    tabs = book.tabs()
    voucher = data["voucher"]
    have = next((t for t in tabs if t["title"].strip() == voucher), None)
    want, total = cells(data, today)
    if have:
        got = book.values(f"'{have['title']}'", "K22:L22")
        number = (book.values(f"'{have['title']}'", "L8") or [[""]])[0][0]
        amount = _num((got[0][0] if got and got[0] else "").replace("VND", ""))
        if number.strip() != data["number"] or amount != total:
            raise InvoiceError(f"tab {voucher} is already there with {number or 'no number'} / {amount:,} VND, the "
                               f"booking is {data['number']} / {total:,} VND: a person checks that tab. Nothing changed")
        gid, how = have["sheetId"], f"tab {voucher} made before, exported as it is"
    else:
        if not book.can_edit():
            raise InvoiceError("the invoice workbook is not shared with Emi's service account as Editor: nothing made")
        source = next((t for t in tabs if t["title"] == TEMPLATE_TAB), None)
        if source is None:
            raise InvoiceError(f"the workbook has no template tab {TEMPLATE_TAB}: nothing made")
        gid = book.duplicate(source["sheetId"], voucher, max(t["index"] for t in tabs) + 1)
        book.write(voucher, want)
        book.finish(gid)
        how = f"new tab {voucher}, copied from the template {TEMPLATE_TAB}"
    data_pdf = book.pdf(gid)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, data["file"])
    with open(path, "wb") as f:
        f.write(data_pdf)
    out(f"INVOICE {data['number']} | {voucher} | {total:,} VND | due {data['due']:%d/%m/%Y} | {how} | saved {path}")
    return path


def render_check(data, today):
    """What make() would write, for a person or a dry run."""
    want, total = cells(data, today)
    rows = [f"{a1}={v}" for a1, v in want.items() if v != ""]
    return f"{data['number']} {data['voucher']} {total:,} VND\n" + "\n".join(rows)


def today_vn():
    return datetime.now(timezone(timedelta(hours=7))).date()
