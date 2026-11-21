"""Anex weekly debt reconciliation, "đối chiếu công nợ" (dev, 2026-11-21; contract 81/26-27, Điều 8.2 and 8.3).

Every Monday the previous week's Anex check-outs (Monday to Sunday) go to Anex accounting in one email, the way
sales@ sent them on 26/10, 07/11 and 18/11 (docs/email-style/anex-doi-chieu-cong-no.md). What goes in it:
  1. the reconciliation .xlsx in Anex's own layout ("Haya Hotel Phu Quoc done.xlsx", the one Anex asked for again
     on 16/11), made here;
  2. one VAT invoice PDF per booking: a person at HAYA sends it into sales@, Emi finds it there;
  3. each booking's EZFOLIO confirmation ("Hợp đồng" PDF).
The bookings, folios and amounts come from EZFOLIO's weekly Anex reports in Drive (config.ANEX_REPORTS_FOLDER_ID,
one folder per week, made Monday ~06:15): "FDR002 Departure" (group, folio, confirm, room, nights, check-in/out,
the Hợp đồng link) and "CAR007C1 Báo cáo đặt phòng" (Công nợ = what each folio bills Anex). Not the intake sheet:
bookings made before it are not on it (19–25/10: 9 Anex groups checked out, the sheet had none, the 26/10 email
named one). A folio with no Công nợ (the 0 room of a group, extras paid in cash) is not a line.

The Monday 09:00 run (`python -m tools.emi anex-recon`, Monday only) drafts the email once everything is there; a
report, VAT or confirmation still missing → a Telegram line naming what is missing (no email to staff yet), and no
draft; that week is taken again the next Monday. Nothing is sent: a person presses Send. The hard copies (VAT
invoice, folio, reservation) go by post once Anex confirms: a person.

Pure functions here; Drive, mailbox and sheet steps are in emi.run_anex_recon.
"""
import csv
import io
import re
from datetime import date, timedelta

KIND = "anex_recon"
TO = ("nhan.nt@anextour.com", "hotelaccount.vn@anextour.com")
CC = ("ctyphuongnguyenpq.rev@gmail.com", "ctyphuongnguyenpq.hayarev@gmail.com")
ANEX_TAX_CODE = "4201598852"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DEPARTURE = "FDR002 Departure"
DEBTS = "CAR007C1 Báo cáo đặt phòng"

SELLER = "CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC – HAYA HOTEL PHU QUOC (TRADEMARK COLLECTION BY WYNDHAM)"
SELLER_ADDRESS = "Tổ 5, đường Trần Hưng Đạo, khu phố 7 Dương Đông, Đặc khu Phú Quốc, Tỉnh An Giang, Việt Nam"
SELLER_TEL = "MST: 1702051744   –   Khách sạn: 82 Trần Hưng Đạo, Dương Đông, Phú Quốc   –   Tel: (+84) 975 398 375"
BUYER = "CÔNG TY TNHH THƯƠNG MẠI VÀ DU LỊCH ANEX VIỆT NAM"
BUYER_ADDRESS = "Tầng 6 và 7, tòa nhà VNPT Khánh Hòa, 50 Lê Thánh Tôn, Phường Nha Trang, Tỉnh Khánh Hòa, Việt Nam"
BANK = [("Bank name (Ngân Hàng):", "NGÂN HÀNG TMCP NGOẠI THƯƠNG VIỆT NAM (VIETCOMBANK) - CHI NHÁNH PHÚ QUỐC"),
        ("Bank address (Địa chỉ ngân hàng):",
         "Số 1A đường Hùng Vương, khu phố 1 Dương Đông, Đặc khu Phú Quốc, Tỉnh An Giang, Việt Nam"),
        ("Account name (Tên TK):", "CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC"),
        ("Account number in VND (Số TK VND):", "1020729617"),
        ("SWIFT:", "")]
HEADERS = ["Inv. Date\n(Ngày hóa đơn)", "Invoice No.\n(Số hóa đơn)", "RSVN No.\n(Số booking ANEX)",
           "Folio No.\n(Số Folio)", "Check-in\n(Ngày bắt đầu)", "Check-out\n(Ngày kết thúc)",
           "Room Type/ Service\n(Loại phòng/ Dịch vụ)", "Quan.\n(Số lượng)", "Nights\n(Số đêm)", "Price\n(Đơn giá)",
           "Total\n(Tổng tiền)"]


def period(today):
    """Last week, Monday to Sunday."""
    first = today - timedelta(days=today.weekday() + 7)
    return first, first + timedelta(days=6)


def week_folder(first, last):
    """The name of the week's folder in the reports folder: '2026-11-09_2026-11-15'."""
    return f"{first:%Y-%m-%d}_{last:%Y-%m-%d}"


def subject(first, last):
    return f"HAYA HOTEL PQ ĐỐI CHIẾU CÔNG NỢ GIAI ĐOẠN {first:%d/%m} - {last:%d/%m/%Y}"


def file_name(first, last):
    return f"HAYA_ANEX_DOI_CHIEU_{first:%d.%m}-{last:%d.%m.%Y}.xlsx"


def money(n):
    return f"{n:,}".replace(",", ".")


def _int(s):
    digits = "".join(c for c in str(s or "") if c.isdigit())
    return int(digits) if digits else 0


def _day(s):
    """'02/11/2026 13:48' or '02/11/2026' -> date."""
    m = re.match(r"\s*(\d{1,2})/(\d{1,2})/(\d{4})", str(s or ""))
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def is_departure(name):
    return (name or "").startswith(DEPARTURE)


def is_debts(name):
    return (name or "").startswith(DEBTS)


# --- EZFOLIO's weekly reports ---

def parse_departure(text):
    """FDR002 Departure: one dict per room (folio), keyed by the header row (Group, Tên group, Folio, Confirm, Phòng,
    Hạng, Công ty, Đêm / Khách, BF, Khách, Số khách, Check-in, Checkout, Balance, Hợp đồng, Bill, Bill tổng đoàn)."""
    rows = list(csv.reader(io.StringIO(text or "")))
    at = next((i for i, r in enumerate(rows) if r and r[0].strip() == "Group" and "Folio" in r), None)
    if at is None and re.search(r"Không có booking", text or "", re.I):
        return []  # 02–08/11: "Ghi chú / Không có booking của Anex trả phòng từ … tại HAYA HOTEL"
    if at is None:
        raise ValueError(f"{DEPARTURE}: no header row with 'Group' and 'Folio'")
    head = [h.strip() for h in rows[at]]
    return [dict(zip(head, (c.strip() for c in r))) for r in rows[at + 1:] if r and r[0].strip()]


def parse_debts(text):
    """CAR007C1: {folio: amount billed to Anex}, the Công nợ column (negative in the report, positive here)."""
    rows = list(csv.reader(io.StringIO(text or "")))
    at = next((i for i, r in enumerate(rows) if r and r[0].strip() == "Mã xác nhận đoàn"), None)
    if at is None or at + 1 >= len(rows) or "Công nợ" not in [c.strip() for c in rows[at + 1]]:
        raise ValueError(f"{DEBTS}: no 'Mã xác nhận đoàn' header with a 'Công nợ' column")
    col = [c.strip() for c in rows[at + 1]].index("Công nợ")
    out = {}
    for r in rows[at + 2:]:
        if not r or not r[0].strip():
            continue
        if r[0].strip().lower().startswith("grand total"):
            break
        folio = r[1].strip() if len(r) > 1 else ""
        if folio and len(r) > col:
            out[folio] = out.get(folio, 0) + _int(r[col])
    return out


REF = re.compile(r"(?:ANEX|\bRef\b|reference|M[AÃ]\s*[DĐ]O[AÀ]N)\D{0,20}(\d{9})\b", re.I)


def ref_in(text):
    m = REF.search(text or "")
    return m.group(1) if m else ""


NOTES = re.compile(r"(?:Ghi chú|Notice)\s*:?\s*(.*?)\s*(?:CHI TIẾT GIÁ PHÒNG|RATE DETAILS)", re.S | re.I)
ANEX_NUMBER = re.compile(r"(?<!\d)(11\d{7})(?!\d)")  # Anex numbers: 9 digits, 112… / 113…
ROOM_LINE = re.compile(r"([A-Z][A-Z ]*?)\s+(\d+)\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(\d+)\s+(\d+)\s+"
                       r"([\d,]+)\s+([\d,]+)")
PALMA = re.compile(r"palma", re.I)


def contract_info(text):
    """What the group's Hợp đồng PDF (EZFOLIO's confirmation) says: {ref, palma, rooms}. The notes carry the Anex
    number in whatever form front office typed it ('No. 112876126', 'MÃ: 112886543', 'REV no: 112800648', 'Anex
    reference: 112883549'); 'Palma chuyển qua' marks an Anex booking of Palma's moved to HAYA (8 of the 9 groups of
    19–25/10, which the 26/10 email left out). rooms = the booked types, as Anex knows them (the departure report
    has the room given: 28371 booked Standard Garden, stayed in a suite)."""
    notes = NOTES.search(text or "")
    notes = " ".join(notes.group(1).split()) if notes else ""
    ref = ANEX_NUMBER.search(notes) or ANEX_NUMBER.search(text or "")
    flat = " ".join((text or "").split())
    start = max(flat.find("CHI TIẾT GIÁ PHÒNG"), flat.find("RATE DETAILS"), 0)
    rooms = [{"room": m.group(1).strip().title(), "rooms": int(m.group(2)), "nights": int(m.group(6)),
              "total": _int(m.group(8))} for m in ROOM_LINE.finditer(flat[start:])]
    return {"ref": ref.group(1) if ref else "", "palma": bool(PALMA.search(notes)), "notes": notes, "rooms": rooms}


def apply_contract(b, info):
    """The Hợp đồng's facts onto a booking built from the reports: its Anex number when the group name has none,
    the booked room type on each folio line (by amount; one priced type → every line), Palma's move."""
    if not b["ref"]:
        b["ref"] = info["ref"]
    b["palma"] = info["palma"]
    priced = [r for r in info["rooms"] if r["total"]]
    for x in b["lines"]:
        same = [r for r in priced if r["total"] == x["total"]]
        pick = same[0] if same else (priced[0] if len({r["room"] for r in priced}) == 1 else None)
        if pick:
            x["room"] = pick["room"]
    rooms = {}
    for x in b["lines"]:
        rooms[x["room"]] = rooms.get(x["room"], 0) + 1
    b["rooms_text"] = " + ".join(f"{n} {room}" for room, n in rooms.items())
    return b


def _nights(text):
    m = re.match(r"\s*(\d+)", text or "")
    return int(m.group(1)) if m else 0


def bookings_from_reports(departure, debts, room_names):
    """(bookings, left_out): one booking per group, a line per folio that bills Anex. left_out = groups whose folios
    bill nothing (paid otherwise): named in the run's output, not in the email."""
    groups = {}
    for r in departure:
        groups.setdefault(r.get("Group", ""), []).append(r)
    out, left = [], []
    for group, rs in groups.items():
        h = rs[0]
        name = h.get("Tên group", "")
        lines = []
        for r in rs:
            amount = debts.get(r.get("Folio", ""), 0)
            if not amount:
                continue
            nights = _nights(r.get("Đêm / Khách"))
            checkout = _day(r.get("Checkout"))
            checkin = checkout - timedelta(days=nights) if checkout and nights else _day(r.get("Check-in"))
            code = (r.get("Hạng") or "").strip()
            lines.append({"folio": r.get("Folio", ""), "room": room_names.get(code, code or "Room"), "rooms": 1,
                          "nights": nights, "price": amount // nights if nights else amount, "total": amount,
                          "checkin": checkin, "checkout": checkout})
        if not lines:
            left.append({"group": group, "name": name})
            continue
        rooms = {}
        for x in lines:
            rooms[x["room"]] = rooms.get(x["room"], 0) + 1
        out.append({"group": group, "conf": h.get("Confirm", ""), "ref": ref_in(name),
                    "guests": re.sub(r"\s*-\s*ANEX\b.*$", "", name, flags=re.I).strip(" ,"),
                    "pax": sum(_int(r.get("Số khách")) for r in rs if debts.get(r.get("Folio", ""))),
                    "arrival": min(x["checkin"] for x in lines if x["checkin"]),
                    "departure": max(x["checkout"] for x in lines if x["checkout"]),
                    "nights": max(x["nights"] for x in lines), "lines": lines,
                    "rooms_text": " + ".join(f"{n} {room}" for room, n in rooms.items()),
                    "total": sum(x["total"] for x in lines), "contract": h.get("Hợp đồng", ""), "palma": False})
    out.sort(key=lambda b: (b["departure"], b["group"]))
    return out, left


# --- the VAT invoice PDF (FAST e-invoice, as accounting issues it) ---

VAT_MARK = re.compile(r"GI[ÁA]\s*TR[ỊI]\s*GIA\s*T[ĂA]NG", re.I)
SERIAL = re.compile(r"Ký\s*hiệu\s*:?\s*([A-Z0-9]{4,10})")
NUMBER = re.compile(r"Ký\s*hiệu\s*:?\s*[A-Z0-9]{4,10}\s*Số\s*:?\s*(\d{1,8})\b")
NUMBER_ANY = re.compile(r"(?<!\w)Số\s*:\s*(\d{1,8})\b")
ISSUED = re.compile(r"Ngày\s*(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})")
TOTAL = re.compile(r"Tổng\s*tiền\s*thanh\s*toán\s*bằng\s*số\s*:?\s*([\d.,]+)")


def parse_vat(text):
    """{serial, number, issued, total} for a VAT invoice to Anex, None for any other file."""
    flat = " ".join((text or "").split())
    if not VAT_MARK.search(flat):
        return None
    if ANEX_TAX_CODE not in re.sub(r"\s", "", text) and "ANEX" not in flat.upper():
        return None
    serial, number = SERIAL.search(flat), NUMBER.search(flat) or NUMBER_ANY.search(flat)
    issued, total = ISSUED.search(flat), TOTAL.search(flat)
    when = None
    if issued:
        try:
            when = date(int(issued.group(3)), int(issued.group(2)), int(issued.group(1)))
        except ValueError:
            when = None
    return {"serial": serial.group(1) if serial else "", "number": number.group(1) if number else "",
            "issued": when, "total": _int(total.group(1)) if total else 0}


def match_vats(bookings, files):
    """{group: file} — files = [{message_id, received, name, subject, text, vat}], the VAT invoices found.
    A file belongs to the booking whose Anex number is in its name, its email's subject or its own text, or whose
    group code stands alone in its name or subject; a file naming no booking goes to the one booking with exactly its
    amount. Sent twice → the latest."""
    out, by_amount = {}, {}
    for b in bookings:
        by_amount.setdefault(b["total"], []).append(b["group"])
    for f in sorted(files, key=lambda f: f.get("received") or ""):
        hay = re.sub(r"\s", "", f"{f.get('name')} {f.get('subject')} {f.get('text')}")
        label = f"{f.get('name')} {f.get('subject')}"
        named = [b["group"] for b in bookings
                 if (b["ref"] and b["ref"] in hay) or (b["group"] and re.search(rf"(?<!\d){b['group']}(?!\d)", label))]
        if not named and f["vat"]["total"] and len(by_amount.get(f["vat"]["total"], [])) == 1:
            named = by_amount[f["vat"]["total"]]
        for g in named:
            out[g] = f
    return out


def invoice_label(vat):
    when = f", ngày {vat['issued']:%d/%m/%Y}" if vat.get("issued") else ""
    return f"{vat.get('serial') or 'HĐ'} số {vat.get('number') or '?'}{when}"


# --- the email ---

def body(first, last, bookings, vats):
    span = f"{first:%d/%m/%Y} – {last:%d/%m/%Y}"
    bank = ("Thông tin chuyển khoản (Điều 8.2 Hợp đồng):\n"
            "- Người thụ hưởng: CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC\n"
            "- Số tài khoản (VND): 1020729617\n"
            "- Ngân hàng: Vietcombank – Chi nhánh Phú Quốc")
    sign = "Trân trọng,\nReservations Team\nHAYA Hotel Phu Quoc, Trademark Collection by Wyndham\nsales@haya-hotels.com"
    if not bookings:
        return "\n\n".join([
            "Dear Team,",
            f"HAYA Hotel Phu Quoc xin gửi bảng đối chiếu công nợ giai đoạn {span} theo mẫu file năm trước.",
            "Trong giai đoạn này, khách sạn không có booking ANEX trả phòng tại HAYA Hotel Phu Quoc (đã đối chiếu "
            "báo cáo departure).",
            "TỔNG GIÁ TRỊ ĐỀ NGHỊ ĐỐI CHIẾU (đã bao gồm VAT): 0 VND.",
            bank,
            "Kính đề nghị Quý Công ty kiểm tra và xác nhận bảng đối chiếu này.",
            f"Đính kèm: bảng đối chiếu công nợ giai đoạn {first:%d/%m} – {last:%d/%m/%Y}.",
            sign])
    lines = []
    for b in bookings:
        who = b["guests"] or "khách"
        if b["pax"]:
            who += f" ({b['pax']} khách)"
        folios = ", ".join(x["folio"] for x in b["lines"])
        lines.append(f"Booking ANEX {b['ref']}: mã đoàn {b['group']} / số XN {b['conf'] or '?'}, folio {folios}, "
                     f"{who}, {b['arrival']:%d/%m} – {b['departure']:%d/%m/%Y}, {b['rooms_text']}, {b['nights']} đêm, "
                     f"{money(b['total'])} VND, hóa đơn VAT {invoice_label(vats[b['group']]['vat'])}.")
    total = sum(b["total"] for b in bookings)
    numbers = ", ".join(vats[b["group"]]["vat"].get("number") or "?" for b in bookings)
    groups = ", ".join(b["group"] for b in bookings)
    return "\n\n".join([
        "Dear Team,",
        f"HAYA Hotel Phu Quoc xin gửi bảng đối chiếu công nợ giai đoạn {span} theo mẫu file năm trước, kèm hóa đơn "
        f"VAT và xác nhận đặt phòng.",
        "\n".join(lines),
        f"TỔNG GIÁ TRỊ ĐỀ NGHỊ ĐỐI CHIẾU (đã bao gồm VAT): {money(total)} VND.",
        "Theo Điều 8.3 Hợp đồng, sau khi công nợ được xác nhận, khách sạn gửi bản cứng Hóa đơn – Folio – Đơn đặt "
        "phòng; Quý Công ty thanh toán số tiền đã xác nhận theo chu kỳ thanh toán quy định trong Hợp đồng.",
        bank,
        "Kính đề nghị Quý Công ty:\n"
        "1. Kiểm tra và xác nhận công nợ qua email để khách sạn gửi bản cứng Hóa đơn – Folio – Đơn đặt phòng;\n"
        "2. Thanh toán theo thời hạn trong Hợp đồng và gửi giúp ủy nhiệm chi / chứng từ chuyển khoản sau khi thanh "
        "toán.",
        f"Đính kèm: bảng đối chiếu công nợ, hóa đơn VAT số {numbers} và xác nhận đặt phòng {groups}.",
        sign])


def missing(bookings, vats, confirmations):
    """[(booking, [what is missing])] — confirmations = {group: (name, bytes)}, the Hợp đồng PDFs downloaded."""
    out = []
    for b in bookings:
        gaps = []
        if not b["ref"]:
            gaps.append("số booking ANEX")
        if b["group"] not in vats:
            gaps.append("hóa đơn VAT")
        if b["group"] not in confirmations:
            gaps.append("PDF xác nhận (Hợp đồng)")
        if gaps:
            out.append((b, gaps))
    return out


def reminder(first, last, gaps, esc=lambda s: s):
    """The Telegram line when something is still missing at the Monday 09:00 run."""
    head = (f"📑 Đối chiếu công nợ Anex {first:%d/%m} – {last:%d/%m/%Y}: chưa gửi được, còn thiếu "
            f"{len(gaps)} booking:")
    rows = [f"• Đoàn {esc(b['group'])} (ANEX {esc(b['ref'] or '?')}, {esc(b['guests'] or 'khách')}, trả phòng "
            f"{b['departure']:%d/%m}, {money(b['total'])} VND): thiếu {esc(', '.join(what))}" for b, what in gaps]
    ask = []
    if any("hóa đơn VAT" in w for _, w in gaps):
        ask.append("Nhờ kế toán gửi file hóa đơn VAT (PDF) vào sales@haya-hotels.com, tên file hoặc tiêu đề có số "
                   "booking ANEX hoặc mã đoàn.")
    if any(w.startswith(("PDF xác nhận", "số booking")) for _, ws in gaps for w in ws):
        ask.append("Hợp đồng PDF hoặc số booking ANEX không tìm thấy trong báo cáo EZFOLIO của tuần: kiểm tra thư "
                   "mục báo cáo trên Drive.")
    return "\n".join([head] + rows + ask)


def palma_line(first, last, moved, esc=lambda s: s):
    """Telegram: the Palma bookings moved to HAYA, left out of the email (Palma reconciles them, as on 26/10)."""
    names = "; ".join(f"đoàn {esc(b['group'])} (ANEX {esc(b['ref'] or '?')}, {money(b['total'])} VND)" for b in moved)
    return (f"📑 Đối chiếu công nợ Anex {first:%d/%m} – {last:%d/%m/%Y}: {len(moved)} đoàn khách Palma chuyển qua "
            f"không đưa vào thư (Palma đối chiếu): {names}.")


def report_missing(first, last, why):
    return (f"📑 Đối chiếu công nợ Anex {first:%d/%m} – {last:%d/%m/%Y}: chưa làm được, báo cáo EZFOLIO của tuần "
            f"chưa đọc được ({why}).")


# --- the .xlsx, in Anex's layout ---

def build_xlsx(first, last, bookings, vats, made_on):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, Side

    wb = Workbook()
    ws = wb.active
    ws.title = f"{first:%d.%m}-{last:%d.%m.%y}"
    bold = Font(bold=True)
    thin = Side(style="thin")
    box = Border(left=thin, right=thin, top=thin, bottom=thin)
    for col, width in zip("ABCDEFGHIJKL", (2, 13, 12, 16, 11, 13, 13, 26, 9, 8, 13, 15)):
        ws.column_dimensions[col].width = width

    ws["B1"], ws["C1"] = "HOTEL NAME:", SELLER
    ws["B2"], ws["C2"] = "Address:", SELLER_ADDRESS
    ws["B3"], ws["C3"] = "Tel/Fax:", SELLER_TEL
    ws["C5"] = "PROFORMA INVOICE / HÓA ĐƠN TẠM TÍNH"
    ws["C5"].font = Font(bold=True, size=14)
    ws["C6"] = "INVOICE NO/ SỐ PHIẾU:"
    ws["C7"], ws["G7"] = "INVOICED DATE/ NGÀY LẬP:", made_on
    ws["G7"].number_format = "dd/mm/yyyy"
    ws["C8"], ws["G8"] = "CUSTOME/ KHÁCH HÀNG:", BUYER
    ws["C9"], ws["G9"] = "CONTACT PERSON/ NGƯỜI LIÊN HỆ:", TO[1]
    ws["F10"], ws["G10"] = "TAX CODE/ MÃ SỐ THUẾ:", ANEX_TAX_CODE
    ws["C11"], ws["G11"] = "ADDRESS/ ĐỊA CHỈ:", BUYER_ADDRESS
    ws["C12"] = f"Giai đoạn trả phòng: {first:%d/%m/%Y} – {last:%d/%m/%Y}"

    row = 14
    for i, h in enumerate(HEADERS):
        c = ws.cell(row=row, column=2 + i, value=h)
        c.font, c.border = bold, box
        c.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center")
    ws.row_dimensions[row].height = 32
    row += 1
    ws.cell(row=row, column=2, value="Accommodation/ Tiền phòng").font = bold
    row += 1
    grand = 0
    for b in bookings:
        vat = vats[b["group"]]["vat"]
        for x in b["lines"]:
            values = [vat.get("issued"), _int(vat.get("number")) or vat.get("number"), _int(b["ref"]) or b["ref"],
                      _int(x["folio"]) or x["folio"], x["checkin"], x["checkout"], x["room"], x["rooms"], x["nights"],
                      x["price"], x["total"]]
            for i, v in enumerate(values):
                c = ws.cell(row=row, column=2 + i, value=v)
                c.border = box
                if isinstance(v, date):
                    c.number_format = "dd/mm/yyyy"
                elif i >= 9:
                    c.number_format = "#,##0"
            grand += x["total"]
            row += 1
    ws.cell(row=row, column=2, value=" Total grand amount  INCLUSIVE VAT tax (Tổng tiền đã bao gồm thuế VAT):"
            ).font = bold
    c = ws.cell(row=row, column=12, value=grand)
    c.font, c.number_format, c.border = bold, "#,##0", box
    row += 2
    ws.cell(row=row, column=3, value="Please settle payment before:")
    ws.cell(row=row, column=8, value="to our bank account with below details:")
    row += 1
    ws.cell(row=row, column=3, value="Vui lòng thanh toán trước:")
    ws.cell(row=row, column=8, value=" bằng hình thức chuyển khoản theo tài khoản ngân hàng ở dưới:")
    row += 1
    for label, value in BANK:
        ws.cell(row=row, column=7, value=label)
        ws.cell(row=row, column=8, value=value)
        row += 1
    row += 1
    for col, a, b in ((3, "Prepared by", "Account Receivables"), (6, "Verified by", "Director Of Finance"),
                      (9, "Acknowledged by", "General Manager")):
        ws.cell(row=row, column=col, value=a).font = bold
        ws.cell(row=row + 1, column=col, value=b)
    ws.cell(row=row + 5, column=2, value="THANK YOU FOR YOUR BUSINESS!").font = bold
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
