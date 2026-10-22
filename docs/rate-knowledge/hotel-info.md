# Hotel info — thông tin khách sạn để trả lời khách

Tờ thông tin ngắn Emi dùng khi khách hoặc đại lý hỏi về khách sạn (giờ nhận/trả phòng, tiện ích, gửi hành lý…). Làm 2026-10-22, **chỉ** từ những gì đã có trong repo; mỗi dòng ghi nguồn.
**PDF gốc là chuẩn.** Thông tin nào không có ở đây thì Emi **không biết** — xem mục "Chưa biết" ở cuối.

## Liên hệ và vị trí
| | Thông tin | Nguồn |
|---|---|---|
| Tên | HAYA Hotel Phu Quoc, Trademark Collection by Wyndham | file TA trang 1; mẫu thư trong `skills/email-templates.md` |
| Địa chỉ | 82 Tran Hung Dao Str, Duong Dong, Phu Quoc, An Giang | footer file Direct (`direct.md`); file TA ghi "…, Phu Quoc Island" |
| Vị trí | Trung tâm Dương Đông, mặt tiền Trần Hưng Đạo (phía biển); cách bãi biển khoảng 300 m, 10 phút đi bộ | file TA trang 1 |
| Lễ tân (máy bàn) | +84 2973 977 786 (front desk); +84 2973 977 768 (desk line 1) | file TA trang 1. ⚠ Footer file Direct in thiếu số: "+84 2973 977" |
| Lễ tân (di động, Zalo "Haya Pq") | +84 869 522 296 | file TA trang 1; footer file Direct |
| Sales hotline (Zalo "Haya Res Pq") | +84 975 398 375 | file TA trang 1 |
| Email / web | sales@haya-hotels.com · www.haya-hotels.com · FB/Insta @hayahotel.pq | file TA trang 1; footer file Direct |

## Nhận phòng / trả phòng
- **Nhận phòng sau 14:00, trả phòng trước 12:00.** Nguồn: `direct.md`, `ta.md` (trang 4 file TA).
- **Khách đến muộn (ví dụ 21:00) là nhận phòng bình thường**, không phải nhận phòng sớm hay trả phòng muộn. Không có phụ thu, không viết "tùy tình trạng phòng". Đây là để Emi hiểu, **không viết vào thư**: thư chỉ nói đã ghi nhận giờ đến và lễ tân sẽ chờ đón ("our front office will be expecting you" / "lễ tân sẽ chờ đón anh/chị"), không giải thích giờ nhận phòng hay phụ thu khi khách không hỏi (`skills/email-templates.md` mục 5). Giờ đến luôn chuyển cho lễ tân (`skills/department-forwards.md`). Khách **hỏi** lễ tân có trực 24 giờ không → xem "Chưa biết".
- **Phụ thu nhận phòng sớm / trả phòng muộn** — chỉ khi nhận phòng **trước 14:00** hoặc trả phòng **sau 12:00**:

  | Nhận phòng | Trả phòng | Phụ thu |
  |---|---|---|
  | Trước 6:00 | Sau 18:00 | 100% |
  | 6:00 – 12:00 | 15:00 – 18:00 | 50% |
  | 12:00 – 14:00 | 12:00 – 15:00 | 25% |

  Nguồn: bảng giá khách lẻ (`direct.md`); file TA in cùng bảng (`ta.md`). ⚠ Cả hai file **không ghi** 100% / 50% / 25% là của giá gì. Hiểu thông thường: giá phòng 1 đêm. Cho tới khi Karen xác nhận, khách hỏi phụ thu thì chưa soạn thư: hỏi Karen bằng `ask-karen`; số tiền cụ thể không tự tính (khách OTA: Emi không có giá phòng của họ).
- **Đặt cọc khi nhận phòng:** 2.000.000 VND/phòng hoặc để lại CMND/CCCD/hộ chiếu/bằng lái; trả lại khi trả phòng sau khi thanh toán hết phí phát sinh. Nguồn: file TA trang 5 (mục VIII). Viết cho đại lý; chưa rõ có áp cho khách lẻ / khách OTA không — hỏi Karen trước khi nói với khách lẻ.

## Ăn sáng và tiện ích
| | Thông tin | Nguồn |
|---|---|---|
| Ăn sáng | 06:30–10:30 | `MEMORY.md` (Key facts), `skills/inquiries-and-quotes.md` |
| Ăn sáng có trong giá không | TA: có. Khách lẻ: ⚠ file không ghi, chờ Karen. Tour operator: theo hợp đồng của hãng | `ta.md`, `direct.md` |
| Hồ bơi | 9:00–22:00, miễn phí | file TA trang 4 (`ta.md`) |
| Phòng gym, wifi | Miễn phí | `ta.md`, `direct.md` |
| Trong phòng | 2 chai nước suối, trà, cà phê mỗi ngày; đồ dùng phòng tắm | `ta.md` (`direct.md`: nước suối, trà, cà phê) |
| Khăn đi biển | Mượn ở lễ tân | `ta.md` |
| Café | Khách ở khách sạn được voucher giảm 20% đồ ăn uống tại Café | `ta.md` (bảng TA — chưa rõ có áp cho khách lẻ) |
| Setup honeymoon / sinh nhật | 500.000 VND/lần | `ta.md` (giá cho đại lý) |
| Số phòng | 85 phòng, hơn 50% view biển, 100% có cửa sổ và ban công | file TA trang 1. ⚠ `MEMORY.md` ghi 83 phòng — đừng nêu số phòng khi Karen chưa xác nhận |

## Đưa đón sân bay / bến tàu
Giá 1 chiều cho **đại lý (TA)**, từ `ta.md`: sân bay–Haya ngày thường 200.000 (4 chỗ) / 250.000 (7 chỗ) / 400.000 (16 chỗ); ngày lễ 300.000 / 400.000 / 650.000. Bến tàu: xem `ta.md` (cột ngày lễ in sai, ⚠ hỏi Karen).
- Không miễn phí. Không có giá cho khách lẻ / khách OTA (`direct.md`, "Không có trên file") → hỏi Karen (`ask-karen`), chưa soạn thư.
- Không **hỏi** khách có cần đưa đón không (`skills/email-templates.md`, luật đã tạm dừng). Khách tự hỏi → trả lời theo trên.

## Giường theo hạng phòng
Nguồn: bảng giá TA (`ta.md`, cột "Giường"). Dùng khi khách hỏi loại giường: nếu hạng phòng đã đặt có sẵn giường khách muốn, thư nói thẳng cỡ giường thay vì "tùy tình trạng phòng".

| Hạng phòng | Giường | Ghi chú cho thư |
|---|---|---|
| Standard Double | 1 giường 1m6 | Không phải giường king. Khách xin giường king → chỉ có ở hạng khác, có chênh lệch giá: không hứa, không tự đổi, báo Karen (AGENTS.md luật 8) |
| Superior Twin | 2 giường 1m2 | Phòng 2 giường đơn |
| Superior Double Pool View | 1 giường 1m8 | 1m8 = cỡ king |
| Deluxe Double Seaview | 1 giường 1m8 | 1m8 = cỡ king. "Deluxe Double" trên voucher đại lý/B2B hiểu là hạng này (bảng TA chỉ có một hạng Deluxe Double; ⚠ giả định của dev 2026-10-22, chờ Karen xác nhận) |
| Suite Seaview | 1 giường 2m | |
| Triple | 1 giường 1m2 + 1 giường 1m6 | |
| Quadruple | 2 giường 1m8 | |

Tên hạng phòng trên OTA/SynXis khác tên trên bảng TA (ví dụ "Standard Garden View (1 Queen Bed)", "Suite Sea View (1 King Bed)"): dùng đúng tên trên voucher khi viết thư, cỡ giường theo bảng trên chỉ khi chắc chắn là cùng hạng phòng.

## Yêu cầu xếp phòng (cùng tầng, phòng thông nhau, loại giường, tầng cao…)
Không có quy định trong file nào. Cách trả lời đã dùng: **"đã ghi nhận và chuyển lễ tân, tùy tình trạng phòng"** — không hứa. Luôn chuyển cho lễ tân (`skills/department-forwards.md`). Không phải là yêu cầu miễn phí/nâng hạng; nếu khách xin nâng hạng phòng → Karen (AGENTS.md luật 8).

## Chưa biết — hỏi Karen
Emi không có thông tin này. Khách hỏi tới thì **không soạn thư**: hỏi Karen bằng `ask-karen`, soạn sau khi Karen trả lời (`karen-answer`), và ghi câu hỏi vào báo cáo scan (dev, 2026-10-22). Không để ô `[…: khách sạn xác nhận]` trong thư — lệnh draft sẽ từ chối. Không bao giờ viết câu kiểu "thông tin này không có trong hồ sơ của chúng tôi".
- **Gửi hành lý** trước khi nhận phòng / sau khi trả phòng: có không, có tính phí không.
- **Lễ tân trực 24 giờ?** Khách đến sau nửa đêm được nhận phòng thế nào.
- **% phụ thu nhận sớm / trả muộn là của giá gì** (xem trên), và áp cho khách OTA theo giá nào.
- **Chính sách hủy cho khách lẻ**; giá đưa đón cho khách lẻ / khách OTA (`direct.md`).
- **Ăn sáng có trong giá khách lẻ không**; ngày Lễ, Tết của bảng Direct; bảng Direct sau 31/05/2026 (`direct.md`).
- **Đặt cọc 2.000.000 VND/phòng khi nhận phòng** có áp cho khách lẻ / khách OTA không.
- **Số phòng**: 85 (file TA) hay 83 (`MEMORY.md`).
- **Hồ bơi**: mấy hồ, trong nhà hay ngoài trời, ở tầng nào, có tên không (chỉ biết giờ mở và miễn phí).
- Bãi đỗ xe, thú cưng, hút thuốc, giặt ủi, nhà hàng ngoài bữa sáng, phòng cho người khuyết tật, giờ yên tĩnh: không có trong file nào.
