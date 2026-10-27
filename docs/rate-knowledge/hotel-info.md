# Hotel info — thông tin khách sạn để trả lời khách

Tờ thông tin ngắn Emi dùng khi khách hoặc đại lý hỏi về khách sạn (giờ nhận/trả phòng, tiện ích, gửi hành lý…). Làm 2026-10-22 từ file TA và file Direct; thêm 2026-10-27 từ **FAQ khách lẻ** (`docs/FAQ/HAYA PALMA - FAQ.xlsx`, tab "Khách lẻ", **chỉ cột "Answer HAYA"** — cột Palma không phải của mình). Mỗi dòng ghi nguồn.
**File gốc là chuẩn.** Thông tin nào không có ở đây thì Emi **không biết** — xem mục "Chưa biết" ở cuối.

FAQ viết cho **khách lẻ / khách OTA**, phần lớn là tin nhắn Zalo/WhatsApp mẫu. Emi lấy **thông tin** trong đó, còn câu chữ trong thư vẫn theo `skills/email-templates.md` (giọng HAYA, "Best, / HAYA Team", ngôn ngữ của người gửi). Đại lý (TA) và tour operator vẫn theo bảng giá / hợp đồng của họ khi hai nguồn khác nhau.

## Liên hệ và vị trí
| | Thông tin | Nguồn |
|---|---|---|
| Tên | HAYA Hotel Phu Quoc, Trademark Collection by Wyndham | file TA trang 1; mẫu thư trong `skills/email-templates.md` |
| Địa chỉ | 82 Tran Hung Dao Str, Duong Dong, Phu Quoc, An Giang | footer file Direct (`direct.md`); file TA ghi "…, Phu Quoc Island"; FAQ ghi "…, Kien Giang" (tên tỉnh cũ) |
| Google Maps | https://maps.app.goo.gl/U1cbWvUg5sodEe3H8 | FAQ "Reservation welcome message" |
| Vị trí | Trung tâm Dương Đông, mặt tiền Trần Hưng Đạo (khu thương mại chính) | file TA trang 1; FAQ "Location" |
| Bãi biển | Bãi Dương Đông, bãi công cộng, 300–500 m, đi bộ 5–10 phút | FAQ "How far is the beach"; file TA: khoảng 300 m, 10 phút |
| Ăn uống gần khách sạn | Việt: Xin Chao, Chợ đêm Phú Quốc · Ấn Độ: Maharaja Lounge, Ganesh · Âu: Pizza Camia, The Home Pizza · Café/bar: Highlands Coffee, Chuon Chuon Bistro | FAQ "What restaurants are nearby" |
| Từ sân bay | Taxi 15–20 phút, khoảng 200.000 VND | FAQ "Booking confirmation (OTA)" |
| Lễ tân (máy bàn) | +84 2973 977 786 (front desk); +84 2973 977 768 (desk line 1) | file TA trang 1. ⚠ Footer file Direct in thiếu số: "+84 2973 977" |
| Lễ tân (di động, Zalo "Haya Pq") | +84 869 522 296 | file TA trang 1; footer file Direct. FAQ để trống số lễ tân |
| Sales hotline (Zalo / WhatsApp "Haya Res Pq") | +84 975 398 375 | file TA trang 1; FAQ |
| Email / web | sales@haya-hotels.com · www.haya-hotels.com · FB/Insta @hayahotel.pq | file TA trang 1; footer file Direct |

## Nhận phòng / trả phòng
- **Nhận phòng từ 14:00, trả phòng trước 12:00.** Nguồn: `direct.md`, `ta.md` (trang 4 file TA), FAQ.
- **Giờ nhận phòng: 14:00 đến nửa đêm** (FAQ "Check-in"). Khách đến **sau nửa đêm**: cột HAYA không nói → "Chưa biết" (cột Palma có câu về bảo vệ, không dùng cho HAYA).
- **Khách đến muộn trong khoảng đó (ví dụ 21:00) là nhận phòng bình thường**, không phải nhận phòng sớm hay trả phòng muộn. Không có phụ thu, không viết "tùy tình trạng phòng". Đây là để Emi hiểu, **không viết vào thư**: thư chỉ nói đã ghi nhận giờ đến và lễ tân sẽ chờ đón ("our front office will be expecting you" / "lễ tân sẽ chờ đón anh/chị"), không giải thích giờ nhận phòng hay phụ thu khi khách không hỏi (`skills/email-templates.md` mục 5). Giờ đến luôn chuyển cho lễ tân (`skills/department-forwards.md`).
- **Đến sớm, gửi hành lý:** khách đến trước 14:00 được gửi hành lý ở khách sạn rồi quay lại nhận phòng. Nhận phòng sớm tùy tình trạng phòng và có phụ thu. Nguồn: FAQ "Early check in". FAQ không nói phí gửi hành lý: không viết là miễn phí hay có phí. Gửi hành lý **sau khi trả phòng**: FAQ không nói → "Chưa biết".
- **Phụ thu nhận phòng sớm / trả phòng muộn** — chỉ khi nhận phòng **trước 14:00** hoặc trả phòng **sau 12:00**:

  | Nhận phòng | Trả phòng | Phụ thu |
  |---|---|---|
  | Trước 6:00 | Sau 18:00 | 100% |
  | 6:00 – 12:00 | 15:00 – 18:00 | 50% |
  | 12:00 – 14:00 | 12:00 – 15:00 | 25% |

  Nguồn: bảng giá khách lẻ (`direct.md`); file TA in cùng bảng (`ta.md`). FAQ chỉ nói "có phụ thu, tùy tình trạng phòng". ⚠ Không file nào ghi 100% / 50% / 25% là của giá gì. Cho tới khi Karen xác nhận, khách hỏi **số tiền** phụ thu thì chưa soạn thư: hỏi Karen bằng `ask-karen`. Khách chỉ hỏi "có nhận phòng sớm được không" → trả lời theo FAQ (gửi hành lý, tùy tình trạng phòng, có phụ thu), không nêu số.
- **Đặt cọc khi nhận phòng:** 2.000.000 VND/phòng hoặc để lại CMND/CCCD/hộ chiếu/bằng lái; trả lại khi trả phòng sau khi thanh toán hết phí phát sinh. Nguồn: file TA trang 5 (mục VIII). Viết cho đại lý; chưa rõ có áp cho khách lẻ / khách OTA không — hỏi Karen trước khi nói với khách lẻ.

## Thanh toán (khách lẻ / khách OTA trả tại khách sạn)
Nguồn: FAQ "Booking confirmation (OTA)", "Payment".
- Trả khi nhận phòng, bằng **tiền mặt VND** hoặc **thẻ** (thẻ phụ thu **3%**). Khách sạn **không nhận USD tiền mặt**: khách nên đổi tiền trước.
- Khách Booking.com: có thể trả bằng thẻ đã khai trên Booking.com.
- Khách xin link trả trước: có **PayPal qua mã QR**, nhưng có phí giao dịch cho cả hai bên; khuyên trả bằng thẻ trên Booking.com hoặc tiền mặt VND khi nhận phòng.
- Đại lý (TA) và tour operator: không áp phần này — cọc 50% / còn lại 7 ngày trước khi đến, chuyển khoản (`confirmation-replies.md`).

## Ăn sáng và tiện ích
| | Thông tin | Nguồn |
|---|---|---|
| Ăn sáng | 06:30–10:30, buffet | `MEMORY.md` (Key facts), `skills/inquiries-and-quotes.md`; FAQ |
| Món chay | Buffet sáng có món chay: pancake, waffle, yến mạch, hummus và rau sống, rau xào/nướng, phở/bún chay, cơm chiên, mì xào, quầy trứng. Yêu cầu ăn kiêng khác: báo trước, khách sạn cố gắng đáp ứng (không hứa) | FAQ "Vegetarian options" |
| Ăn sáng có trong giá không | TA: có. Khách lẻ: ⚠ file Direct không ghi, chờ Karen. Tour operator: theo hợp đồng của hãng | `ta.md`, `direct.md` |
| Hồ bơi | Có; 9:00–22:00, miễn phí | file TA trang 4 (`ta.md`); FAQ "Amenities" |
| Phòng gym, wifi | Miễn phí | `ta.md`, `direct.md`; FAQ |
| Trong phòng | Trà, cà phê, nước suối bổ sung mỗi ngày; dầu gội, dầu xả, sữa tắm, xà phòng rửa tay; bàn chải và kem đánh răng, tăm bông; máy sấy tóc, tủ lạnh mini, két sắt. Dao cạo, lược: xin ở lễ tân | FAQ "Amenities"; `ta.md` (2 chai nước suối, trà, cà phê mỗi ngày) |
| Hút thuốc | Tất cả phòng **không hút thuốc**; lễ tân chỉ khu vực hút thuốc gần nhất | FAQ "Smoking" |
| Đỗ xe | **Không có bãi đỗ ô tô** tại khách sạn. Xe máy: tùy chỗ trống | FAQ "Booking confirmation (OTA)" |
| Giặt ủi | 80.000 VND/kg | FAQ "Reservation welcome message" |
| Thuê xe máy | Nửa ngày 100.000 VND; cả ngày 150.000 VND | FAQ "Reservation welcome message" |
| Vé, tour | Cáp treo Sunset Town + Cầu Hôn + Aquatopia 850.000 · Combo VinWonders + VinSafari (1 ngày) 1.500.000 · VinSafari 850.000 · VinWonders 950.000 · Tour 3/4 đảo 720.000–800.000 (VND/người) | FAQ "Can I book a tour", "Reservation welcome message" |
| Bữa trưa / tối | Có gói ăn trưa, ăn tối tại khách sạn — FAQ không ghi giá: khách hỏi giá → "Chưa biết" | FAQ "Booking confirmation (OTA)" |
| Khăn đi biển | Mượn ở lễ tân | `ta.md` |
| Café | Khách ở khách sạn được voucher giảm 20% đồ ăn uống tại Café | `ta.md` (bảng TA — chưa rõ có áp cho khách lẻ) |
| Trang trí honeymoon / sinh nhật | **Khách lẻ:** trang trí phòng 600.000 VND (~25 USD); trang trí + 1 chai vang 800.000 VND (~33 USD); khách báo ngày muốn làm. **Đại lý:** 500.000 VND/lần (bảng TA) | FAQ "Honeymoon / birthday package"; `ta.md` |
| Số phòng | 85 phòng, hơn 50% view biển, 100% có cửa sổ và ban công | file TA trang 1; sheet tồn phòng ghi "Physical Rooms 85" (2026-10-27). ⚠ `MEMORY.md` ghi 83 — số đúng là 85 |
| Thời tiết | Mùa khô 11–4 (nắng, 25–30°C, biển êm — đẹp nhất); tháng 5 và 10 chuyển mùa, mưa rào ngắn; mùa mưa 6–9, mưa chiều ngắn, ít đông. Đi được quanh năm | FAQ "Weather" |
| Visa | Phú Quốc là điểm đến đầu tiên ở Việt Nam → không cần visa; từ Phú Quốc đi tiếp nơi khác → miễn visa tối đa 30 ngày; nhập cảnh ở thành phố khác trước rồi mới tới Phú Quốc → cần visa. Luôn kèm câu khuyên khách tự kiểm tra lại lịch trình | FAQ "Visa" |

## Đưa đón sân bay / bến tàu
- **Đại lý (TA)**, giá 1 chiều từ `ta.md`: sân bay–Haya ngày thường 200.000 (4 chỗ) / 250.000 (7 chỗ) / 400.000 (16 chỗ); ngày lễ 300.000 / 400.000 / 650.000. Bến tàu: xem `ta.md` (cột ngày lễ in sai, ⚠ hỏi Karen). Không miễn phí.
- **Khách lẻ / khách OTA** (FAQ "Airport pick-up (charge)", "Reservation welcome message"): sân bay 200.000 VND/chiều. Để đặt: số hiệu chuyến bay, giờ hạ cánh, số vali, số WhatsApp.
- **Miễn phí 1 chiều cho booking trên 250 USD** (FAQ "Booking confirmation (OTA)", "Free airport pick up"): chỉ **một chiều** — đón ở sân bay khi đến **hoặc** tiễn ra sân bay khi về, khách chọn một. Đây là chính sách in sẵn của HAYA, nên Emi được nói khi khách hỏi; nhưng chỉ khi tổng booking trên row (đổi ra USD) rõ ràng trên 250 USD. Không chắc (tỷ giá, booking sát ngưỡng, không có tổng) → Karen.
- Không **hỏi** khách có cần đưa đón không, không hỏi giờ đến (`skills/email-templates.md`, luật đã tạm dừng — FAQ có mẫu "Arrival time" và lời mời đặt dịch vụ, Emi **không** dùng). Khách tự hỏi → trả lời theo trên.

## Hủy, đổi booking OTA — chỉ để Karen quyết (AGENTS.md luật 7, 8)
FAQ có các mẫu dưới đây. Đây là **cách HAYA thường xử lý**, không phải quyền của Emi: mỗi email kiểu này thành dòng CANCEL/CHANGE + câu hỏi cho Karen, **chưa soạn thư** tới khi Karen trả lời.
- Booking **không hoàn tiền**, khách hủy **hơn 2 tuần** trước ngày đến: HAYA thường chấp nhận hủy miễn phí và nhờ khách để lại đánh giá Google cho đội sales. **Trong 2 tuần**: không hoàn, thu đủ tiền.
- Booking **linh hoạt**: hủy miễn phí.
- Khách muốn đổi số phòng / số đêm: nhờ khách tự sửa ở "Manage Booking" trên Booking.com. FAQ có thêm phương án hủy rồi đặt lại trực tiếp với **giảm 10%** — đó là giảm giá: Emi **không bao giờ** tự đưa ra (luật 8), chỉ báo Karen.
- **Overbook** (HAYA hết phòng mà OTA vẫn nhận booking): mẫu FAQ là đề nghị khách chuyển sang Palma. Karen quyết; Emi không tự đề nghị.
- **Thẻ bị từ chối** (booking không hoàn tiền): mẫu FAQ xin khách cập nhật thẻ trong 24 giờ, nếu không có thể hủy theo chính sách. Emi soạn thư này chỉ khi Karen hoặc lễ tân báo thẻ bị từ chối; không tự hủy.
- **Xin đánh giá** sau kỳ ở: FAQ có mẫu cho Booking.com — không phải việc của Emi trên email.

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
- **Khách đến sau nửa đêm** nhận phòng thế nào; lễ tân có trực 24 giờ không (FAQ HAYA chỉ ghi nhận phòng đến nửa đêm).
- **Gửi hành lý sau khi trả phòng**; gửi hành lý có tính phí không.
- **% phụ thu nhận sớm / trả muộn là của giá gì** (xem trên), và áp cho khách OTA theo giá nào.
- **Chính sách hủy cho khách lẻ đặt trực tiếp** (FAQ chỉ có booking OTA); giá đưa đón cho khách lẻ ngoài sân bay (bến tàu).
- **Ăn sáng có trong giá khách lẻ đặt trực tiếp không**; ngày Lễ, Tết của bảng Direct; bảng Direct sau 31/05/2026 (`direct.md`).
- **Đặt cọc 2.000.000 VND/phòng khi nhận phòng** có áp cho khách lẻ / khách OTA không.
- **Hồ bơi**: mấy hồ, trong nhà hay ngoài trời, ở tầng nào (chỉ biết có hồ, giờ mở và miễn phí).
- **Giá gói ăn trưa / tối**.
- Thú cưng, phòng cho người khuyết tật, giờ yên tĩnh: không có trong file nào.
