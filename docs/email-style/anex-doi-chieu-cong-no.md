# Anex — đối chiếu công nợ thứ Hai (mẫu từ Sent của sales@)

Tìm ngày 21/11/2026 qua `mail-find` / `show` trên hotpink-bee. Hợp đồng 81/26-27, Điều 8.2 (chuyển khoản) và 8.3 (danh sách thứ Hai → Anex xác nhận → gửi bản cứng → Anex trả 2 tuần một lần vào thứ Sáu tuần thứ 3).

## Các thư đã gửi

| Ngày gửi | Giai đoạn trả phòng | Booking | Tổng | Ghi chú |
|---|---|---|---|---|
| T2 26/10 16:58 | 19/10 – 25/10 | 112883549, đoàn 29301 / XN 25557, HĐ C26MPN 888 | 18.283.500 | Đúng mẫu Anex (sheet "HAYA") |
| T7 07/11 20:59 | 26/10 – 01/11 | 112797913, đoàn 28371 / XN 24931, folio 64562, HĐ C26MPN 936 | 13.515.000 | Bảng tự làm, **không** theo mẫu Anex |
| T2 16/11 16:23 | Anex trả lời (nhan.nt@) | | | "Team làm công nợ theo file cũ năm trước giúp mình nhé." + file mẫu `Haya Hotel Phu Quoc done.xlsx` |
| T4 18/11 09:07 | 02/11 – 08/11 | không có booking | 0 | Vẫn gửi, bảng trống theo mẫu |
| T4 18/11 16:53 | 26/10 – 01/11 (gửi lại) | như 07/11 | 13.515.000 | Trả lời trong thread, theo mẫu năm trước |

Không thấy thư cho tuần 09/11 – 15/11 (báo cáo EZFOLIO: đoàn 29512 + 27269, 37.565.000 VND).

## Địa chỉ
- To: `nhan.nt@anextour.com` (Nhan Nguyen, Accounting Dept), `hotelaccount.vn@anextour.com`
- Cc: `ctyphuongnguyenpq.rev@gmail.com`, `ctyphuongnguyenpq.hayarev@gmail.com`
- Subject: `HAYA HOTEL PQ ĐỐI CHIẾU CÔNG NỢ GIAI ĐOẠN DD/MM - DD/MM/YYYY` (thứ Hai – Chủ nhật tuần trước). Gửi lại thì trả lời trong thread cũ (`RE:`).

## Nội dung thư (tiếng Việt)
1. `Dear Team,`
2. `HAYA Hotel Phu Quoc xin gửi bảng đối chiếu công nợ giai đoạn DD/MM/YYYY – DD/MM/YYYY kèm hóa đơn VAT và xác nhận đặt phòng.` (dev, 21/11, after #1575; not "theo mẫu file năm trước")
3. Bảng tóm tắt, một dòng mỗi booking: Số booking ANEX | Mã đoàn / Số XN | Khách (số khách) | Nhận – Trả phòng | Phòng | Số đêm | Thành tiền (VND) | Hóa đơn VAT (`C26MPN số NNN, ngày DD/MM/YYYY`). Dòng cuối: `TỔNG CÔNG NỢ (đã bao gồm VAT)`.
   Tuần không có booking: `Trong giai đoạn này, khách sạn không có booking ANEX trả phòng tại HAYA Hotel Phu Quoc (đã đối chiếu báo cáo departure).` + `TỔNG GIÁ TRỊ ĐỀ NGHỊ ĐỐI CHIẾU (đã bao gồm VAT): 0 VND.`
4. Điều 8.3: sau khi Anex xác nhận, khách sạn gửi bản cứng Hóa đơn – Folio – Đơn đặt phòng; Anex trả số đã xác nhận của hai tuần liền kề vào thứ Sáu tuần thứ 3 → `dự kiến được thanh toán vào thứ Sáu, ngày DD/MM/YYYY` (thư 26/10: tuần 19–25/10 → 06/11).
5. Thông tin chuyển khoản (Điều 8.2): CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC, 1020729617, Vietcombank – Chi nhánh Phú Quốc.
6. `Kính đề nghị Quý Công ty:` 1. kiểm tra và xác nhận công nợ qua email để khách sạn gửi bản cứng; 2. thanh toán đúng hạn và gửi ủy nhiệm chi / chứng từ chuyển khoản.
7. `Đính kèm: bảng đối chiếu công nợ, hóa đơn VAT số NNN và xác nhận đặt phòng <mã đoàn>.`
8. `Trân trọng,` / Reservations Team / HAYA Hotel Phu Quoc, Trademark Collection by Wyndham / sales@haya-hotels.com

## File đính kèm
1. **Bảng đối chiếu .xlsx theo mẫu của Anex** (`Haya Hotel Phu Quoc done.xlsx`, sheet "Proforma Invoice sample"; HAYA đặt tên `HAYA_ANEX_DOI_CHIEU_DD.MM-DD.MM.YYYY.xlsx`, mỗi tab một giai đoạn):
   - Đầu trang: HOTEL NAME (CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC – HAYA HOTEL PHU QUOC (TRADEMARK COLLECTION BY WYNDHAM)), Address, Tel/MST 1702051744; `PROFORMA INVOICE / HÓA ĐƠN TẠM TÍNH`; Invoice no; Invoiced date; Khách hàng `CÔNG TY TNHH THƯƠNG MẠI VÀ DU LỊCH ANEX VIỆT NAM`; contact hotelaccount.vn@anextour.com; MST 4201598852; địa chỉ Tầng 6 và 7, tòa nhà VNPT Khánh Hòa, 50 Lê Thánh Tôn, Phường Nha Trang, Tỉnh Khánh Hòa.
   - Cột: Inv. Date | Invoice No. | RSVN No. (số booking ANEX) | Folio No. | Check-in | Check-out | Room Type/Service | Quan. | Nights | Price | Total. Nhóm "Accommodation/ Tiền phòng".
   - Dòng tổng: `Total grand amount INCLUSIVE VAT tax`.
   - Khối "Please settle payment before" + ngân hàng Vietcombank CN Phú Quốc, tài khoản 1020729617; chữ ký Prepared by (Account Receivables) / Verified by (Director Of Finance) / Acknowledged by (General Manager).
2. **Hóa đơn VAT PDF** từ hệ thống FAST e-invoice của kế toán (ký hiệu C26MPN, VAT 8%), tên kiểu `VAT_C26MPN_<số>_<DD.MM.YYYY>.pdf`.
3. **Xác nhận đặt phòng PDF** từ EZFOLIO, tên kiểu `Confirm_Reservation_HAYA_<số Anex>_<mã đoàn>.pdf`.

## Dữ liệu cần và nguồn (dev, 21/11)
Báo cáo EZFOLIO hằng tuần trên Drive, thư mục `1RJyGQzU_nQWZN5K09tAUo2skKhkyBnJs`, mỗi tuần một thư mục `YYYY-MM-DD_YYYY-MM-DD` (tạo sáng thứ Hai ~06:15):

| Trường | Nguồn |
|---|---|
| Đoàn, folio, số XN, hạng phòng được xếp, số đêm, check-in/out | `FDR002 Departure — HAYA — Anex — <tuần>` (một dòng một phòng) |
| Số tiền Anex phải trả | `CAR007C1 Báo cáo đặt phòng`, cột **Công nợ** theo folio (folio 0 đồng hoặc chỉ có dịch vụ trả tiền mặt thì không có) |
| Số booking ANEX, hạng phòng **đã đặt** | PDF `FDR002 Hợp đồng — … — <đoàn>.pdf` (phần Ghi chú / CHI TIẾT GIÁ PHÒNG); nếu không có thì intake sheet theo mã đoàn |
| Hoá đơn VAT | nhân viên gửi PDF vào sales@ |
| Bill (folio) | `FDR002 Bill — … — <đoàn> — <folio>.pdf` — bản cứng gửi bưu điện |

Ghi chú "Palma chuyển qua" trong Hợp đồng = booking Anex của Palma chuyển sang HAYA: 8/9 đoàn tuần 19–25/10, thư 26/10 không đưa vào. HAYA đối chiếu các đoàn này (dev, 21/11), đưa vào thư như booking khác.

## Chưa thấy trong hộp thư
- Thư Anex **xác nhận** công nợ (chỉ có thư 16/11 đòi làm lại theo mẫu).
- Bước gửi bản cứng Hóa đơn – Folio – Đơn đặt phòng (gửi bưu điện, không qua email).
