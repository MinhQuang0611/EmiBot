# Direct — Bảng giá khách lẻ (đặt thẳng với khách sạn)

Nguồn: `docs/RATE TABLES/HAYA HOTEL - DIRECT BOOKINGS.pdf` (1 trang, có text layer; kiểm lại bằng ảnh trang). Chép lại 2026-10-19.
Hiệu lực in trên file: **01/03/2026 – 31/05/2026**. ⚠ Đã hết hạn so với mọi ngày ở hiện tại — Karen chưa nói bảng này còn dùng được. Cho tới khi Karen xác nhận, không đưa giá trong file này vào thư gửi khách.
Dùng cho: `channel_type = Direct` (cá nhân, không qua công ty). Không dùng cho TA, tour operator, OTA.

## Giá phòng (VND / phòng / đêm)
Đã gồm 8% VAT và phí quẹt thẻ.

| Hạng phòng (tên trên file) | Mã | Khách | Ngày thường | Ngày Lễ, Tết |
|---|---|---|---|---|
| STANDARD GARDEN | STD | 2 | 2.150.000 | 2.800.000 |
| SUPERIOR DOUBLE/TWIN | SUP-DBL / SUP-TWN | 2 | 2.400.000 | 3.150.000 |
| DELUXE SEA VIEW | DLX-SV | 2 | 3.000.000 | 3.900.000 |
| SUITE SEA VIEW | SUITE-SV | 2 | 3.600.000 | 4.700.000 |
| TRIPLE | TPL | 3 | 3.600.000 | 4.700.000 |
| QUADRUPLE FAMILY | QPL | 4 | 4.450.000 | 5.800.000 |

- Chỉ có 2 cột giá: ngày thường và ngày Lễ, Tết. Không chia mùa như bảng TA.
- File không ghi ngày nào là "Ngày Lễ, Tết". `quote` dùng danh sách ngày lễ của bảng TA (giả định — cần Karen xác nhận).
- Không có TW-DLX, APT trên file. Khách lẻ hỏi các hạng này → chuyển Karen.
- Không có tối thiểu số đêm, không có phụ thu ở 1 đêm, không có ưu đãi đoàn / đặt sớm / ở dài.

## Phụ thu ăn sáng (VND / người / đêm)
| | Ngày thường | Ngày Lễ, Tết |
|---|---|---|
| Người lớn (từ 12 tuổi) | 500.000 | 600.000 |
| Trẻ em 3 – dưới 12 tuổi | 350.000 | 500.000 |
| Trẻ em dưới 3 tuổi | Miễn phí | Miễn phí |

⚠ File không ghi giá phòng đã gồm ăn sáng hay chưa. `quote` đang hiểu: giá phòng gồm ăn sáng cho số khách của phòng (cột Khách); bé ngủ chung giường trả phụ thu trẻ em ở bảng trên — giống cách bảng TA tính. Cần Karen xác nhận trước khi báo giá.

## Nhận phòng sớm / trả phòng muộn
Nhận phòng sau 14:00, trả phòng trước 12:00.

| Nhận phòng | Trả phòng | Phụ thu |
|---|---|---|
| Trước 6:00 | Sau 18:00 | 100% |
| 6:00 – 12:00 | 15:00 – 18:00 | 50% |
| 12:00 – 14:00 | 12:00 – 15:00 | 25% |

File không ghi 100% / 50% / 25% là của giá gì (hiểu thông thường: giá phòng 1 đêm). Khách hỏi → trả lời theo bảng, kèm "tùy tình trạng phòng"; con số cụ thể chuyển Karen.

## Thanh toán
- Khách thanh toán **100% trước khi nhận phòng**. Không có cọc 50% / 48 giờ như TA.
- Nhắc cọc 40 giờ / nhắc số dư 7 ngày trong `skills/confirmation-replies.md` là luật của TA, không áp cho khách lẻ.

## Bao gồm
Nước suối, trà, cà phê trong phòng; wifi, hồ bơi, phòng gym.

## Không có trên file — chuyển Karen
- **Chính sách hủy cho khách lẻ.** `cancel-fee` từ chối booking Direct; khách lẻ hủy → Karen. (Thư thật duy nhất gửi khách lẻ — Mr. Hindol Roy, 07/10/2026, xem `skills/email-templates.md` — ghi "thanh toán toàn bộ trước ngày hủy miễn phí, 7 ngày trước check-in". Một thư không phải là chính sách.)
- Giá đưa đón cho khách lẻ (bảng TA có, nhưng là giá cho đại lý).
- Giá TW-DLX, APT; giá cho ngày sau 31/05/2026.
