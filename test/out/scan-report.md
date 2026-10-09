# Báo cáo quét — test local, 08/10/2026
Nguồn: `test/emails/` (9 email). Không gọi mail, sheet hay Drive thật. Xử lý theo thứ tự giờ nhận. Email 05 và 07 ghi ngày 09/10/2026, sau ngày chạy test; vẫn xử lý như email mới.

## Cần Karen xử lý
| # | Việc | Vì sao |
|---|---|---|
| 1 | **SB2611-047: UNC 9.150.000 VND không khớp 50%** | 50% tiền phòng theo giá trong email = 9.525.000; nếu gồm phụ thu trẻ em = 10.050.000. Có thể đại lý tính Deluxe Seaview 2.200.000 thay vì 2.450.000. Chưa đối chiếu được vì bảng giá TA trống. |
| 2 | **Agoda 1122334455: giá net 850.000/đêm**, dưới sàn 1.000.000 | Có thể cài khuyến mãi sai. |
| 3 | **BWT-5521 (Bluewave Tours) xin hủy** | Cần Karen OK hủy. Booking chưa có trong sheet. "Family room" không phải hạng phòng HAYA. Đại lý hỏi phí hủy, chưa có điều kiện hủy. Chưa soạn xác nhận hủy. |
| 4 | **LJ-88213 (Lotus Journeys) xin giá tốt hơn** + trang trí kỷ niệm ngày cưới | Giảm giá và quà miễn phí do Karen quyết định, cần bố mẹ duyệt. Nháp trả lời để 2 chỗ trống cho phần này. |
| 5 | **Northstar DMC hỏi giá 10–14/01/2027**: chưa soạn trả lời | Thiếu file FUTURE AVAILABILITY và bảng giá TA. Không soạn thư hẹn "sẽ kiểm tra". Xem phần Hỏi giá bên dưới. |
| 6 | **Palma, Coral Travel**: 2 Bungalow 15–18/12/2026 | Email của Palma, Emi không xử lý. Karen chuyển cho bên Palma. |

## Booking mới / thay đổi / hủy
| Booking | Loại | Dòng intake | Còn thiếu |
|---|---|---|---|
| SB2611-047 Sao Biển Travel | NEW (đã cập nhật theo email đổi ngày) | 2 dòng: 2 SD, 1 DLX Seaview. 21/11–24/11/2026, 3 đêm | Giá chưa đối chiếu; room_code; trẻ 5 tuổi ở phòng nào; giờ đến 14:00 có còn đúng cho ngày mới không |
| LJ-88213 Lotus Journeys | NEW | 1 dòng: 2 DLX Seaview, đến 05/12/2026 | Ngày đi, số khách, tên khách, giá (+20% khách Ấn Độ), room_code |
| Agoda 1122334455 / SynXis 77665544 | NEW, OTA | 1 dòng (2 email cùng 1 booking, nhập 1 lần). 14–16/11/2026 | room_code; giá dưới sàn |
| BWT-5521 Bluewave Tours | CANCEL | 1 dòng | Karen OK; mã đoàn và số xác nhận trong EZFOLIO |

Email 05 (đổi ngày SB2611-047): Tracy chưa nhập booking (Pending), nên Emi sửa thẳng 2 dòng NEW thay vì thêm dòng CHANGE. Ngày cũ ghi trong notes.

Không dòng nào sẵn sàng cho Tracy: dòng nào cũng còn `missing_info`, ít nhất là room_code (thiếu `room-codes.csv`).

## Thanh toán
| Booking | Số tiền trên UNC | Thời gian | Trạng thái |
|---|---|---|---|
| SB2611-047 | 9.150.000 VND, cọc | 09/10/2026 16:12 | Đã ghi vào payment_1 (dòng SD). UNC chưa phải xác nhận đã nhận tiền. **Chưa chuyển kế toán**: booking chưa có mã đoàn, theo quy định giữ lại tới khi Tracy nhập. Số tiền không khớp, xem mục 1. |

## Bản nháp trong `test/out/drafts/`
| File | Gửi cho | Tình trạng |
|---|---|---|
| `02-reply-lotus-journeys-LJ-88213.txt` | Lotus Journeys | Xin bổ sung ngày đi, số khách, tên khách. Còn 2 chỗ trống (giá, trang trí kỷ niệm) chờ Karen. |

## Chưa soạn, và lý do
| Việc | Lý do |
|---|---|
| Xác nhận SB2611-047, LJ-88213 | Chưa có `pdf_link`, tức PMS chưa cập nhật. |
| Trả lời Agoda / SynXis | Email OTA không trả lời. |
| Xác nhận hủy BWT-5521 | Chưa có OK của Karen, Tracy chưa hủy. |
| Chuyển lễ tân (`haya@haya-hotels.com`): SB2611-047 cùng tầng, giờ đến, danh sách khách; Agoda tầng cao, không hút thuốc | Ghi chú chuyển tiếp phải có mã đoàn, mà chưa có mã đoàn. Đến sớm nhất 14/11, còn thời gian. Soạn khi Tracy nhập xong. Nếu Karen muốn chuyển ngay không cần mã đoàn, báo Emi. |
| Chuyển kế toán UNC SB2611-047 | Chưa có mã đoàn. |
| Nhắc cọc | Chưa gửi xác nhận nào nên chưa bắt đầu tính 48 giờ. |

## Hỏi giá: Northstar DMC, 10–14/01/2027 (4 đêm, mùa Winter)
Phần đã có câu trả lời:
- Phòng có em 13 tuổi: 13 tuổi tính như người lớn, nên phòng 3 người lớn: chào phòng Triple (không có thì Quadruple).
- 3 phòng 2 người lớn: chào hạng rẻ nhất còn phòng.
- Nâng 1 phòng lên căn hộ miễn phí: không. APT không bán cho đại lý.

Phần còn thiếu: file FUTURE AVAILABILITY (còn phòng không, có dừng bán không), bảng giá TA, chính sách đưa đón sân bay (chưa có trong hồ sơ của Emi). Có 3 thứ này là Emi soạn được trả lời đầy đủ.

## Thiếu trong môi trường test
- `fixtures/ta-rates-2026.csv` trống, thiếu `room-codes.csv`, `intake-column-rules.csv`, `availability.pdf`.
- `intake-columns.csv` là header tạm. Giá trị cột `status`, `priority`, `channel_type` là Emi chọn, chưa đối chiếu dòng 2 của sheet thật.
- Skill `anti-ai-slop` không có trong project; nháp chưa qua bước này.
