"""Anex weekly reconciliation (dev, 2026-11-21): bookings, folios and amounts from EZFOLIO's weekly reports in Drive,
VAT PDFs from sales@, the Hợp đồng PDFs; Monday 09:00 drafts once all are there, else a Telegram line."""
import io
import unittest
from datetime import date
from unittest import mock

from tools import anex_recon as ar
from tools import emi
from tools.tests.test_replies import Base

# The text pypdf gives for HAYA's VAT invoice 888 to Anex (26/10/2026), as show printed it.
VAT_888 = """HÓA ĐƠN GIÁ TRỊ GIA TĂNG
Ngày 26 tháng 10 năm 2026
Tên người bán
:
CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC
Tên người mua
:
CÔNG TY TNHH THƯƠNG MẠI VÀ DU LỊCH ANEX VIỆT NAM
Mã số thuế
:
4 2 0 1 5 9 8 8 5 2
Số hộ chiếu:
Số bảng kê:
Ký hiệu
:
C26MPN
Số
:
888
Tổng tiền thanh toán bằng số
18.283.500
"""
OTHER_VAT = VAT_888.replace("ANEX VIỆT NAM", "PEGAS").replace("4 2 0 1 5 9 8 8 5 2", "0 3 1 2 3")

# FDR002 Departure and CAR007C1 for 19–25/10, as Drive exports them (cut to three groups).
DEPARTURE = """Group,Tên group,Folio,Confirm,Phòng,Hạng,Công ty,Đêm / Khách,BF,Khách,Số khách,Check-in,Checkout,Balance,Hợp đồng,Bill,Bill tổng đoàn
29301,TISHCHENKO NATALIA / BACHURINA MARIIA / BACHURINA LARISA - ANEX 112883549,65979,25557,412CR,STD-TWN,ANEX TOUR,10 Night - 1 Guest,BF,Mr. TISHCHENKO,1,15/10/2026 12:00,25/10/2026 10:00,0,https://drive.google.com/file/d/HOPDONG29301xxxxxxxxxxxx/view,,
29301,TISHCHENKO NATALIA / BACHURINA MARIIA / BACHURINA LARISA - ANEX 112883549,65855,25557,413CR,STD,ANEX TOUR,10 Night - 3 Guest,BF,Mr. TISHCHENKO,3,15/10/2026 12:00,25/10/2026 10:00,0,https://drive.google.com/file/d/HOPDONG29301xxxxxxxxxxxx/view,,
29692,"MELNIK EVGENII,",66355,25821,311,STD,ANEX TOUR,10 Night - 2 Guest,BF,"Mr. MELNIK EVGENII,",2,11/10/2026 11:15,21/10/2026 09:36,0,https://drive.google.com/file/d/HOPDONG29692xxxxxxxxxxxx/view,,
28371,SIKORSKAIA IULIIA,64562,24931,801,SUITE-SV,ANEX TOUR,11 Night - 1 Guest,BF,Mr. SIKORSKAIA IULIIA,1,18/10/2026 03:31,24/10/2026 11:10,0,https://drive.google.com/file/d/HOPDONG28371xxxxxxxxxxxx/view,,
"""
DEBTS = """HAYA HOTEL,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
CAR007BÁO CÁO ĐẶT PHÒNG ĐÃ TRẢ COPY,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
Mã xác nhận đoàn,Đặt phòng,Tên khách,Số phòng,Chi tiết dịch vụ,,,,,,,,,,Doanh thu,Đặt cọc,,,,,Thanh toán,,,,,,,Hoàn tiền,,,Số dư
,,,,Tiền phòng,Phụ thu người lớn,Phụ thu trẻ em,Early check in,Late check out,Thuê xe,Tiền ăn,Minibar,Giặt là,Khác,,Tiền mặt,Thẻ tín dụng,Chuyển khoản,Khác,,Tiền mặt,Thẻ tín dụng,Công nợ,Chuyển khoản,Thẻ trả trước,QR Code,Khác,Tiền mặt,Chuyển khoản,Khác,
29301,65855,Mr. TISHCHENKO,413CR,18.283.500,0,0,0,0,0,0,0,0,0,18.283.500,0,0,0,0,,0,0,-18.283.500,0,0,0,0,0,0,0,0
29692,66355,"Mr. MELNIK EVGENII,",311,8.010.000,0,0,0,0,0,0,0,0,0,8.010.000,0,0,0,0,,0,0,-8.010.000,0,0,0,0,0,0,0,0
28371,64562,Mr. SIKORSKAIA IULIIA,801,13.515.000,0,0,0,0,0,0,0,80.000,0,13.595.000,0,0,0,0,,-80.000,0,-13.515.000,0,0,0,0,0,0,0,0
Grand Total,,,,39.808.500,0,0,0,0,0,0,0,0,0,39.808.500,0,0,0,0,,0,0,-39.808.500,0,0,0,0,0,0,0,0
"""
EMPTY_WEEK = """Ghi chú
"Không có booking của Anex trả phòng từ 02/11/2026 tới 08/11/2026 tại HAYA HOTEL (báo cáo FDR002)"
"""
CONTRACTS = {
    "HOPDONG29301xxxxxxxxxxxx": """GROUP BOOKING CONFIRMATION
Group code: 29301
Notice:
Anex reference: 112883549. Tour operator: ANEX BLAGOVESHCHENSK.
RATE DETAILS
Period
Room Type Number of Room Arrival Date Departure Date Guest(s) Night(s) Rate Total Room
QUADRUPLE 1 15/10/2026 25/10/2026 2 10 1,828,350 18,283,500
STANDARD
TWIN 1 15/10/2026 25/10/2026 1 10 0 0
Total 2   3 20  18,283,500""",
    "HOPDONG29692xxxxxxxxxxxx": """XÁC NHẬN ĐẶT PHÒNG ĐOÀN
Mã đoàn: 29692
Ghi chú:
No. 112876126. std
Khách Palma qua
CHI TIẾT GIÁ PHÒNG
Số khách Số đêm Giá phòng Tổng tiền
STANDARD
GARDEN 1 11/10/2026 21/10/2026 2 10 801,000 8,010,000""",
    "HOPDONG28371xxxxxxxxxxxx": """XÁC NHẬN ĐẶT PHÒNG ĐOÀN
Mã đoàn: 28371
Ghi chú:
MA DOAN: 112797913 CI/CO: 17-28/10/2026
CHI TIẾT GIÁ PHÒNG
Số khách Số đêm Giá phòng Tổng tiền
STANDARD
GARDEN 1 17/10/2026 28/10/2026 1 11 1,228,636 13,515,000""",
}

TODAY = date(2026, 10, 26)  # Monday: the week reconciled is 19/10 – 25/10


class FakeSheet:
    call = object()

    def __init__(self, data=()):
        self.data = list(data)

    def rows(self):
        return self.data


class FakeDrive:
    """The reports folder: one week folder per {name: (departure csv, debts csv or None)}."""

    def __init__(self, weeks):
        self.weeks = weeks

    def children(self, call, folder_id):
        if folder_id == emi.config.ANEX_REPORTS_FOLDER_ID:
            return [{"id": f"w:{n}", "name": n, "mimeType": "application/vnd.google-apps.folder"} for n in self.weeks]
        dep, debts = self.weeks[folder_id[2:]]
        files = [{"id": f"dep:{folder_id}", "name": "FDR002 Departure — HAYA — Anex — x",
                  "mimeType": "application/vnd.google-apps.spreadsheet"}]
        if debts is not None:
            files.append({"id": f"debts:{folder_id}", "name": "CAR007C1 Báo cáo đặt phòng — HAYA — Anex — x",
                          "mimeType": "application/vnd.google-apps.spreadsheet"})
        return files

    def export_csv(self, call, fid):
        kind, folder = fid.split(":", 1)
        dep, debts = self.weeks[folder[2:]]
        return dep if kind == "dep" else debts

    def download(self, call, fid):
        return f"FDR002 Hợp đồng — {fid}.pdf", "application/pdf", b"%PDF " + fid.encode()


class FakeTg:
    def __init__(self):
        self.sent = []

    def send(self, text, buttons=None, topic=None):
        self.sent.append((topic, text))


class PureTest(unittest.TestCase):
    def test_vat_invoice_is_read(self):
        v = ar.parse_vat(VAT_888)
        self.assertEqual((v["serial"], v["number"], v["issued"], v["total"]),
                         ("C26MPN", "888", date(2026, 10, 26), 18283500))

    def test_vat_to_another_buyer_and_other_files_are_not_anex_invoices(self):
        self.assertIsNone(ar.parse_vat(OTHER_VAT))
        self.assertIsNone(ar.parse_vat("GROUP BOOKING CONFIRMATION ANEX TOUR"))

    def test_period_and_week_folder(self):
        self.assertEqual(ar.period(date(2026, 11, 23)), (date(2026, 11, 16), date(2026, 11, 22)))
        self.assertEqual(ar.week_folder(date(2026, 11, 9), date(2026, 11, 15)), "2026-11-09_2026-11-15")

    def test_debts_are_the_cong_no_column_per_folio(self):
        self.assertEqual(ar.parse_debts(DEBTS), {"65855": 18283500, "66355": 8010000, "64562": 13515000})

    def test_empty_week_departure_is_no_booking(self):
        self.assertEqual(ar.parse_departure(EMPTY_WEEK), [])
        with self.assertRaises(ValueError):
            ar.parse_departure("something else")

    def test_one_booking_per_group_folio_at_zero_left_out(self):
        bookings, left = ar.bookings_from_reports(ar.parse_departure(DEPARTURE), ar.parse_debts(DEBTS),
                                                  emi.ROOM_NAMES_VI)
        self.assertEqual(left, [])
        b = next(b for b in bookings if b["group"] == "29301")
        self.assertEqual((b["ref"], b["conf"], b["total"], b["pax"], [x["folio"] for x in b["lines"]]),
                         ("112883549", "25557", 18283500, 3, ["65855"]))
        self.assertEqual((b["arrival"], b["departure"], b["nights"]), (date(2026, 10, 15), date(2026, 10, 25), 10))
        self.assertEqual(b["guests"], "TISHCHENKO NATALIA / BACHURINA MARIIA / BACHURINA LARISA")
        s = next(b for b in bookings if b["group"] == "28371")
        self.assertEqual(s["lines"][0]["checkin"], date(2026, 10, 13))  # check-out − nights, not the 03:31 arrival
        self.assertEqual(s["total"], 13515000)  # the laundry paid in cash isn't Anex's

    def test_contract_gives_ref_booked_room_and_palma(self):
        i = ar.contract_info(CONTRACTS["HOPDONG29692xxxxxxxxxxxx"])
        self.assertEqual((i["ref"], i["palma"]), ("112876126", True))
        self.assertEqual(i["rooms"], [{"room": "Standard Garden", "rooms": 1, "nights": 10, "total": 8010000}])
        q = ar.contract_info(CONTRACTS["HOPDONG29301xxxxxxxxxxxx"])
        self.assertEqual((q["ref"], q["palma"]), ("112883549", False))
        self.assertEqual([r["room"] for r in q["rooms"]], ["Quadruple", "Standard Twin"])

    def test_booked_type_replaces_the_room_given(self):
        bookings, _ = ar.bookings_from_reports(ar.parse_departure(DEPARTURE), ar.parse_debts(DEBTS),
                                               emi.ROOM_NAMES_VI)
        s = next(b for b in bookings if b["group"] == "28371")
        self.assertEqual(s["lines"][0]["room"], "Suite Seaview")
        ar.apply_contract(s, ar.contract_info(CONTRACTS["HOPDONG28371xxxxxxxxxxxx"]))
        self.assertEqual((s["lines"][0]["room"], s["rooms_text"]), ("Standard Garden", "1 Standard Garden"))
        q = next(b for b in bookings if b["group"] == "29301")
        ar.apply_contract(q, ar.contract_info(CONTRACTS["HOPDONG29301xxxxxxxxxxxx"]))
        self.assertEqual(q["lines"][0]["room"], "Quadruple")  # matched by amount among two types

    def test_vat_matched_by_ref_or_group_else_by_unique_amount(self):
        b = [{"ref": "112883549", "group": "29301", "total": 18283500},
             {"ref": "112797913", "group": "28371", "total": 13515000},
             {"ref": "", "group": "29512", "total": 1}]
        vat = ar.parse_vat(VAT_888)
        by_ref = {"name": "ANEX HAYA_25.10_112883549.pdf", "subject": "", "text": "", "vat": dict(vat, total=5)}
        by_amount = {"name": "hoadon.pdf", "subject": "VAT", "text": "", "vat": dict(vat, total=13515000)}
        by_group = {"name": "VAT doan 29512.pdf", "subject": "", "text": "", "vat": dict(vat, total=7)}
        got = ar.match_vats(b, [by_ref, by_amount, by_group])
        self.assertEqual((got["29301"], got["28371"], got["29512"]), (by_ref, by_amount, by_group))

    def test_same_amount_twice_is_not_guessed(self):
        b = [{"ref": "1", "group": "a", "total": 500}, {"ref": "2", "group": "b", "total": 500}]
        f = {"name": "x.pdf", "subject": "", "text": "", "vat": {"total": 500}}
        self.assertEqual(ar.match_vats(b, [f]), {})


class RunTest(Base):
    def setUp(self):
        super().setUp()
        self.inbox = []
        self.mail.list_inbox_since = lambda since, with_files=False: [m for m, _ in self.inbox
                                                                      if m["receivedDateTime"] >= since]
        self.mail.list_attachments = lambda mid: [{"name": n, "data": d, "isInline": False}
                                                  for m, fs in self.inbox if m["id"] == mid for n, d in fs]
        self.texts = {b"%PDF " + k.encode(): v for k, v in CONTRACTS.items()}
        p = mock.patch.object(emi.attachments, "search_text", lambda name, data: self.texts.get(data, ""))
        p.start()
        self.addCleanup(p.stop)
        self.drive = FakeDrive({"2026-10-19_2026-10-25": (DEPARTURE, DEBTS)})
        for fn in ("children", "export_csv", "download"):
            p = mock.patch.object(emi.drive, fn, getattr(self.drive, fn))
            p.start()
            self.addCleanup(p.stop)
        self.sheet = FakeSheet()
        self.tgs = FakeTg()

    def vat_email(self, name, received="2026-10-25T09:00:00Z", text=VAT_888):
        data = b"%PDF vat " + name.encode()
        self.texts[data] = text
        self.inbox.append(({"id": f"m{len(self.inbox)}", "receivedDateTime": received, "subject": "VAT Anex",
                            "from": {"emailAddress": {"address": "ketoan@haya-hotels.com"}}}, [(name, data)]))

    def run_(self, today=TODAY):
        self.lines = []
        return emi.run_anex_recon(self.mail, self.sheet, self.st, self.tgs, today=today, work_dir=self.dir,
                                  out=self.lines.append)

    def drafts(self):
        return [r for r in self.st.data["reviews"].values() if r["kind"] == ar.KIND]

    def reports(self):
        return [t for topic, t in self.tgs.sent if topic == "report"]

    def test_vat_missing_reminds_on_telegram_and_drafts_nothing(self):
        self.vat_email("ANEX HAYA_25.10_112883549.pdf")
        self.assertEqual(self.run_(), {"2026-10-19": "waiting"})
        self.assertEqual(self.drafts(), [])
        waiting = [t for t in self.reports() if "chưa gửi được" in t][0]
        self.assertIn("Đoàn 28371", waiting)
        self.assertIn("thiếu hóa đơn VAT", waiting)
        self.assertNotIn("Đoàn 29301", waiting)
        self.assertEqual(self.st.data["anex_recon"]["2026-10-19"]["status"], "waiting")

    def test_palma_move_is_reconciled_by_haya_like_the_others(self):
        self.run_()
        waiting = "\n".join(t for t in self.reports() if "chưa gửi được" in t)
        self.assertIn("Đoàn 29692 (ANEX 112876126", waiting)  # its VAT is asked for like any other
        self.assertFalse([t for t in self.reports() if "Palma" in t])
        self.assertIn("PALMA MOVE, included", "\n".join(self.lines))

    def test_everything_there_one_draft_with_xlsx_vat_and_confirmations(self):
        self.vat_email("ANEX HAYA_25.10_112883549.pdf")
        self.vat_email("hoadon 28371.pdf", text=VAT_888.replace("888", "936").replace("18.283.500", "13.515.000"))
        self.vat_email("VAT 112876126.pdf", text=VAT_888.replace("888", "901").replace("18.283.500", "8.010.000"))
        self.assertEqual(self.run_(), {"2026-10-19": "drafted"})
        d = self.drafts()[0]
        self.assertEqual((d["to"], d["cc"]), (list(ar.TO), list(ar.CC)))
        self.assertEqual(d["subject"], "HAYA HOTEL PQ ĐỐI CHIẾU CÔNG NỢ GIAI ĐOẠN 19/10 - 25/10/2026")
        self.assertEqual(d["attachments"], ["HAYA_ANEX_DOI_CHIEU_19.10-25.10.2026.xlsx",
                                            "VAT 112876126.pdf", "Confirm_Reservation_HAYA_112876126_29692.pdf",
                                            "hoadon 28371.pdf", "Confirm_Reservation_HAYA_112797913_28371.pdf",
                                            "ANEX HAYA_25.10_112883549.pdf",
                                            "Confirm_Reservation_HAYA_112883549_29301.pdf"])
        self.assertIn("Booking ANEX 112883549: mã đoàn 29301 / số XN 25557, folio 65855", d["text"])
        self.assertIn("1 Quadruple, 10 đêm, 18.283.500 VND, hóa đơn VAT C26MPN số 888, ngày 26/10/2026", d["text"])
        self.assertIn("1 Standard Garden", d["text"])
        self.assertIn("Booking ANEX 112876126: mã đoàn 29692", d["text"])
        self.assertIn("HAYA Hotel Phu Quoc xin gửi bảng đối chiếu công nợ giai đoạn 19/10/2026 – 25/10/2026 kèm hóa đơn "
                      "VAT và xác nhận đặt phòng.", d["text"])
        self.assertIn("TỔNG GIÁ TRỊ ĐỀ NGHỊ ĐỐI CHIẾU (đã bao gồm VAT): 39.808.500 VND.", d["text"])
        self.assertEqual(self.st.data["anex_recon"]["2026-10-19"]["palma_moves"], ["29692"])
        self.assertEqual(self.run_(), {"2026-10-19": "drafted"})  # run again: nothing new
        self.assertEqual(len([d for d in self.drafts() if "19/10" in d["subject"]]), 1)

    def test_xlsx_is_anex_s_own_file_filled_in(self):
        from openpyxl import load_workbook
        bookings, _ = ar.bookings_from_reports(ar.parse_departure(DEPARTURE), ar.parse_debts(DEBTS),
                                               emi.ROOM_NAMES_VI)
        b = ar.apply_contract(next(x for x in bookings if x["group"] == "29301"),
                              ar.contract_info(CONTRACTS["HOPDONG29301xxxxxxxxxxxx"]))
        vats = {"29301": {"vat": ar.parse_vat(VAT_888)}}
        ws = load_workbook(io.BytesIO(ar.build_xlsx(date(2026, 10, 19), date(2026, 10, 25), [b], vats, TODAY))).active
        row = [ws[f"{c}17"].value for c in "BCDEFGHIJKL"]
        self.assertEqual(row[1:4] + row[6:9] + row[10:], [888, 112883549, 65855, "Quadruple", 1, 10, 18283500])
        self.assertEqual([d.date() for d in (row[0], row[4], row[5])],
                         [date(2026, 10, 26), date(2026, 10, 15), date(2026, 10, 25)])
        self.assertEqual(row[9], "=L17/(I17*J17)")
        self.assertEqual(ws["L18"].value, "=I18*J18*K18")  # unused lines stay as the template has them
        self.assertEqual(ws["L27"].value, "=SUM(L17:L26)")
        self.assertEqual(ws["G9"].value.date(), TODAY)
        self.assertEqual(ws["G10"].value, ar.BUYER)
        self.assertEqual((ws["H17"].font.name, ws["H17"].font.sz), ("Cambria", 8))
        self.assertEqual(ws.title, "19.10-25.10.26")
        self.assertIn("$B$2:$L$56", ws.print_area)

    def test_more_than_ten_lines_push_the_total_down(self):
        from openpyxl import load_workbook
        lines = [{"folio": str(70000 + i), "room": "Standard Garden", "rooms": 1, "nights": 2, "price": 100,
                  "total": 200, "checkin": date(2026, 10, 20), "checkout": date(2026, 10, 22)} for i in range(13)]
        b = {"group": "1", "ref": "112000001", "lines": lines}
        out = ar.build_xlsx(date(2026, 10, 19), date(2026, 10, 25), [b], {"1": {"vat": ar.parse_vat(VAT_888)}}, TODAY)
        ws = load_workbook(io.BytesIO(out)).active
        self.assertEqual(ws["E29"].value, 70012)
        self.assertEqual(ws["L30"].value, "=SUM(L17:L29)")
        self.assertTrue(str(ws["B30"].value).strip().startswith("Total grand amount"))
        self.assertIn("B30:K30", [str(m) for m in ws.merged_cells.ranges])
        self.assertIn("$B$2:$L$59", ws.print_area)
        self.assertEqual(ws["D59"].value, None)
        self.assertEqual(ws["B59"].value, "THANK YOU FOR YOUR BUSINESS!")

    def test_no_report_folder_yet_waits_and_says_so(self):
        self.assertEqual(self.run_(date(2026, 11, 23)), {"2026-11-16": "waiting"})
        self.assertIn("báo cáo EZFOLIO của tuần chưa đọc được", self.reports()[0])
        self.assertIn("2026-11-16_2026-11-22", self.reports()[0])

    def test_week_with_no_anex_checkout_is_sent_at_zero(self):
        self.drive.weeks["2026-11-02_2026-11-08"] = (EMPTY_WEEK, None)
        self.assertEqual(self.run_(date(2026, 11, 9)), {"2026-11-02": "drafted"})
        d = self.drafts()[0]
        self.assertIn("không có booking ANEX trả phòng", d["text"])
        self.assertIn("0 VND", d["text"])
        self.assertEqual(d["attachments"], ["HAYA_ANEX_DOI_CHIEU_02.11-08.11.2026.xlsx"])

    def test_waiting_week_is_taken_again_the_next_monday(self):
        self.run_()
        self.vat_email("ANEX HAYA_25.10_112883549.pdf", received="2026-10-28T09:00:00Z")
        self.vat_email("VAT 28371.pdf", received="2026-10-28T09:00:00Z",
                       text=VAT_888.replace("18.283.500", "13.515.000"))
        self.vat_email("VAT 29692.pdf", received="2026-10-28T09:00:00Z",
                       text=VAT_888.replace("18.283.500", "8.010.000"))
        self.drive.weeks["2026-10-26_2026-11-01"] = (EMPTY_WEEK, None)
        self.assertEqual(self.run_(date(2026, 11, 2)), {"2026-10-19": "drafted", "2026-10-26": "drafted"})

    def test_ref_from_the_intake_sheet_when_reports_have_none(self):
        dep = DEPARTURE.replace(" - ANEX 112883549", "")
        self.texts[b"%PDF HOPDONG29301xxxxxxxxxxxx"] = "no notes"
        self.drive.weeks["2026-10-19_2026-10-25"] = (dep, DEBTS)
        self.sheet = FakeSheet([{"ezfolio_group_code": "#29301", "booking_ref": "Anex 112883549"}])
        self.run_()
        self.assertNotIn("Đoàn 29301 (ANEX ?", "\n".join(self.reports()))

    def test_redo_makes_the_week_again_and_drops_the_old_draft(self):
        self.vat_email("ANEX HAYA_25.10_112883549.pdf")
        self.vat_email("hoadon 28371.pdf", text=VAT_888.replace("888", "936").replace("18.283.500", "13.515.000"))
        self.vat_email("VAT 112876126.pdf", text=VAT_888.replace("888", "901").replace("18.283.500", "8.010.000"))
        self.run_()
        old = str(self.st.data["anex_recon"]["2026-10-19"]["n"])
        self.lines = []
        got = emi.run_anex_recon(self.mail, self.sheet, self.st, self.tgs, today=TODAY, work_dir=self.dir,
                                 out=self.lines.append, redo=True)
        self.assertEqual(got, {"2026-10-19": "drafted"})
        new = str(self.st.data["anex_recon"]["2026-10-19"]["n"])
        self.assertNotEqual(new, old)
        self.assertEqual(self.st.data["reviews"][old]["status"], "replaced")
        self.assertEqual(self.st.data["reviews"][new]["status"], "pending")

    def test_preview_changes_nothing(self):
        self.lines = []
        got = emi.run_anex_recon(self.mail, self.sheet, self.st, None, today=TODAY, preview=True, work_dir=self.dir,
                                 out=self.lines.append)
        self.assertEqual(got, {"2026-10-19": "missing"})
        self.assertEqual(self.st.data.get("anex_recon"), {})
        self.assertIn("VAT MISSING", "\n".join(self.lines))


if __name__ == "__main__":
    unittest.main()
