# Fixtures — bản copy local của dữ liệu thật

Chưa có số liệu thật. Lấy từ Karen rồi điền vào. Emi không tự điền.

| File | Lấy từ đâu | Trạng thái |
|---|---|---|
| `intake-columns.csv` | Dòng 1 của tab Intake, sheet "HAYA Ezfolio Booking Intake v2" | **Thật** (dev dán, 2026-10-09). 48 cột. Header gốc là `COD ` có dấu cách cuối, code đã strip nên ghi là `COD`. |
| `intake-column-rules.csv` | Dòng 2 của tab Intake (hướng dẫn từng cột) | **Thật** (dev dán, 2026-10-09). Dòng 1 = header, dòng 2 = hướng dẫn. |
| `intake-examples.csv` | 3 dòng mẫu từ sheet (GADT, Thu1230 TVR149, An0109) | **Thật** (dev dán, 2026-10-09). Mẫu tham khảo định dạng, có vài chỗ không nhất quán (xem `memory/2026-10-09.md`). |
| `room-codes.csv` | Tab Room codes | **Chưa có** |
| `ta-rates-2026.csv` | Bảng giá TA 2026 (đã gồm VAT 8% và ăn sáng) | **Trống.** Chưa điền thì Emi không đối chiếu được giá và sẽ ghi vào `missing_info`. |
| `availability.pdf` | File mới nhất trong thư mục "FUTURE AVAILABILITY" | **Chưa có.** Cần để test trả lời hỏi giá. |
