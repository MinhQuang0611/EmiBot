# Cách HAYA trả lời email — ghi chú từ thư đã gửi (13–27/10/2026)

Nguồn: thư mục Sent của sales@haya-hotels.com, 13/10–27/10/2026, khoảng 350 thư (`python -m tools.emi sent-dump --days 14`). Đọc kỹ ~45 thư tiêu biểu theo từng loại. Tên khách, số tiền cụ thể đã thay bằng `[ ]` trong khung mẫu; số mã ví dụ giữ lại để dễ đối chiếu với Sent.

**Đây là ghi chú, chưa phải luật.** `skills/email-templates.md` vẫn là bản Emi đang dùng. Mục "Khác với Emi hiện tại" ở cuối liệt kê chỗ cần sửa; chỗ nào đụng luật Karen đã chốt (chữ ký, miễn phí, hỏi chuyến bay) thì cần Karen duyệt trước khi đổi.

---

## A. Khung chung của mọi thư

**1. Chào**
- Tiếng Việt, đại lý: `Kính gửi chị [Tên],` · có nhiều người nhận: `Kính gửi chị [Tên] và chị [Tên],` · gửi cả công ty: `Kính gửi chị [Tên] và Quý Đối tác [Đại lý],` · không biết tên: `Kính gửi Quý Đối tác,` · phòng kế toán: `Kính gửi Phòng Kế toán [Đại lý],`
- Tiếng Anh, đại lý: `Dear Ms. [Name],` · `Dear Mr. [Name] and [Agency] team,` · `Dear [Agency] team,` / `Dear Anex Reservation Team,` / `Dear Rezlive Confirmations Team,` · hai người: `Dear Nikita, Dear Pankaj,`
- Khách lẻ / khách OTA: `Dear Ms [Surname],` / `Dear Mr. [Surname],` · không rõ giới tính: `Dear Ms/Mr [Surname],` · không có tên: `Dear Guest,` / `Dear Sir / Madam,` / `Dear Valued Guest,`

**2. Câu mở — một câu, cảm ơn đúng việc họ vừa làm**
- VI: `HAYA Hotel Phu Quoc, Trademark Collection by Wyndham xin (chân thành) cảm ơn [chị / Quý Đối tác] đã [gửi booking cho khách sạn / gửi ủy nhiệm chi / phản hồi / quan tâm và liên hệ với khách sạn].`
- EN đại lý: `Thank you for choosing HAYA Hotel Phu Quoc, Trademark Collection by Wyndham.` (xác nhận booking) · `Greetings from HAYA Hotel Phu Quoc, Trademark Collection by Wyndham, and thank you for your email.` (reconfirm, HCN, hỏi giá)
- EN khách: `Thank you for your message.` / `Thank you for your email.` — rồi vào việc ngay.

**3. Câu dẫn vào khối thông tin**
- VI: `Khách sạn xin xác nhận đặt phòng như sau:` · `Vui lòng xem thông tin xác nhận đặt phòng:` · `Khách sạn xin gửi lại báo giá cập nhật … như sau:`
- EN: `Please find the booking confirmation below:` · `We confirm that the following reservation is held in our system as Definite:` · `We have noted the guest's request as follows:`

**4. Khối thông tin — `Nhãn: giá trị`, mỗi dòng một mục, không dòng trống giữa các mục**
- Thứ tự (VI): Mã đoàn → Số xác nhận → Mã đặt phòng → Tên đoàn / Tên khách / Khách đại diện → Đại lý du lịch → Quốc tịch → Thời gian lưu trú → Hạng phòng → Số lượng khách → Đơn giá / Chi tiết giá → Tổng tiền.
- Thứ tự (EN): Group code → Confirmation number → Agency reference → Group name / Guest(s) → Travel agency → Stay → Room → Guests → Rate → Total.
- Bedbank / reconfirm (EN): Hotel confirmation number → (Hotel) group code → Your reference / Supplier reference → Guest(s) → Stay → Room → Meal plan → Payment / Status.
- Mã đoàn luôn có `#`: `#30287`. Số xác nhận không có `#`.
- Ngày: `14/01/2027 – 17/01/2027 (3 đêm)` / `29/10/2026 – 09/11/2026 (11 nights)`.
- Số đếm có số 0 đầu trong thư tiếng Việt: `02 phòng`, `03 trẻ em (07, 05, 05 tuổi)`, `trước 07 ngày`.
- Phòng ghi tên đầy đủ và loại giường khi cần: `01 phòng Superior Double Pool View (Superior hướng hồ bơi, giường đôi 1m8)`, `1 Standard Double (one double bed)`.
- Nhiều hạng phòng / nhiều mức giá: mỗi hạng một dòng gạch `–` (VI) hoặc bullet (EN), **có phép tính**:
  `– Standard Double: 2.040.000 VND/phòng/đêm × 02 phòng × 3 đêm = 12.240.000 VND`
  `29/10 – 31/10/2026: VND 1,050,000 per room per night × 3 nights = VND 3,150,000`
- Tổng: `Tổng tiền: 37.350.000 VND (đã bao gồm ăn sáng và 8% VAT)` · `Total: VND 16,750,000, including breakfast, VAT and service charge.`
- Phụ thu nêu rõ lý do trong ngoặc ngay ở dòng giá: `(đã bao gồm phụ thu 20% áp dụng cho khách quốc tịch Ấn Độ)`, `Phụ thu trẻ em (4 tuổi, ngủ chung giường với bố mẹ): 350.000 VNĐ/bé/đêm`.

**5. Tiền**: VI `13.500.000 VND` · EN `VND 16,750,000` (có thư viết `6,000,000 VND`; dùng `VND …` cho thống nhất).

**6. Thanh toán và ngân hàng** (xem mục B1). Luôn có dòng nội dung chuyển khoản `Tên Công ty + Mã đoàn #[mã]` và câu xin gửi UNC.

**7. Câu nhờ / việc tiếp theo** — một câu, lịch sự, cụ thể: `Chị vui lòng gửi giúp khách sạn danh sách tên khách và quốc tịch của đoàn.` · `Please send us the guest names when available.`

**8. Câu kết** (một câu, theo người đọc)
- Khách sắp đến: `We look forward to welcoming you.` / `…welcoming you and your family to HAYA Hotel Phu Quoc.` / `We wish you a safe trip and look forward to seeing you soon.`
- Đại lý / bedbank: `We look forward to welcoming the guests.` / `Xin chân thành cảm ơn sự hợp tác của Quý Đối tác.`
- Từ chối / hết phòng: `We hope to welcome your guests on another occasion.` / `We apologise for the inconvenience and look forward to your next booking.`

**9. Chữ ký** — dạng gặp nhiều nhất:
```
Trân trọng,                         Best regards,
Reservations Team                   Reservations Team
HAYA Hotel Phu Quoc, Trademark Collection by Wyndham
sales@haya-hotels.com
```
Biến thể đã gặp: `Bộ phận Đặt phòng` thay cho `Reservations Team` (thư tiếng Việt), thêm dòng `Sales: (+84) 97 5398 375 | Reception: (+84) 86 952 2296`. **Không thư nào ký "Best, / HAYA Team".**

**10. Định dạng**: thư thuần, nhãn không in đậm trong nội dung đã gửi (bản text); danh sách dùng bullet Outlook hoặc `–` / `-`; đoạn cách nhau một dòng trống. Không emoji.

---

## B. Từng tình huống

### B1. Xác nhận booking mới — đại lý (TA)
Nguồn: #254 Footprint 141C0127Y (VI), #36 Travel Concierge 2779479 (EN), #45 Tripackers (EN).
```
Kính gửi chị [Tên] và Quý Đối tác [Đại lý],

HAYA Hotel Phu Quoc, Trademark Collection by Wyndham xin chân thành cảm ơn Quý Đối tác đã gửi booking cho khách sạn. Khách sạn xin xác nhận đặt phòng như sau:

Mã đoàn: #[mã đoàn]
Số xác nhận: [số]
Mã đặt phòng: [mã đại lý]
Tên khách: [tên / sẽ bổ sung sau (TBU)]
Quốc tịch: [quốc tịch]
Thời gian lưu trú: [DD/MM/YYYY] – [DD/MM/YYYY] ([n] đêm)
Số khách: [n] người lớn và [0n] trẻ em ([tuổi] tuổi)
Hạng phòng: [0n] phòng [hạng] + … (tổng [n] phòng), bao gồm ăn sáng

Đơn giá ([mùa / ghi chú phụ thu]):
– [Hạng]: [giá] VND/phòng/đêm × [0n] phòng × [n] đêm = [tiền] VND
– Phụ thu trẻ em (ngủ chung giường với bố mẹ): 350.000 VND × [0n] trẻ × [n] đêm = [tiền] VND
Tổng tiền: [tổng] VND (đã bao gồm ăn sáng và 8% VAT)

Thanh toán: đặt cọc 50% = [tiền] VND trong vòng 48 giờ kể từ khi nhận xác nhận này (booking sẽ tự động hủy nếu khách sạn không nhận được tiền cọc); thanh toán 50% còn lại = [tiền] VND trước ngày [DD/MM/YYYY] (7 ngày trước ngày đến). Nhờ chị ghi tên công ty + mã đoàn #[mã đoàn] trong nội dung chuyển khoản và gửi lại ủy nhiệm chi giúp khách sạn.

Chính sách hủy: [theo bảng TA]

Thông tin tài khoản thanh toán:
Tên tài khoản: CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC
Số tài khoản: 1020729617
Ngân hàng: Vietcombank, CN Phú Quốc

[Chị vui lòng gửi giúp danh sách tên khách khi có.]

Trân trọng,
Reservations Team
HAYA Hotel Phu Quoc, Trademark Collection by Wyndham
sales@haya-hotels.com
```
- EN giống hệt về thứ tự; `Payment terms:` thành 2 bullet (50% deposit … by [HH:MM] on [DD/MM/YYYY], Vietnam time / remaining 50% 7 days before check-in (by [date])) + `The booking will be automatically released without further notice if the deposit is not received by the deadline.`
- Khi đại lý đặt sai hạng so với yêu cầu (ví dụ xin twin nhưng đặt Standard Double): xác nhận đúng hạng đã đặt, rồi một đoạn `Room type note:` đưa giá hạng thay thế để họ chọn (#36).
- Có chính sách hủy trong thư (#254): `hủy trước 7 ngày: miễn phí; 3–6 ngày: phí 01 đêm; trong 3 ngày: 50%; no-show: 100%`.

### B2. Xác nhận thay đổi / tạo lại đoàn
Nguồn: #202 PZL06270114X (VI), #5 Victoria (báo giá cập nhật).
- Câu đầu nói thay đổi gì: `…xác nhận thay đổi cơ cấu phòng cho đoàn như sau. Đoàn đã được tạo lại với mã đoàn mới; mã đoàn cũ #29530 đã được hủy.`
- Hạng phòng ghi cả cũ → mới: `3 Superior Twin + 1 Triple (thay cho 5 Superior Twin)`.
- Báo giá thay thế báo giá trước: `Báo giá này thay thế báo giá phòng Deluxe Seaview Double gửi lúc 11:20 ngày 13/10/2026.`
- Ngày đến còn dưới 7 ngày: `Do ngày nhận phòng là [date] (còn chưa đến 07 ngày), khách sạn đề nghị Quý Đối tác thanh toán 100% tổng tiền trước ngày khách đến.`

### B3. Nhận UNC / slip thanh toán từ đại lý
Nguồn: #256 Travel Concierge (VI), #326 Threeland (VI), #9 Greentours (VI), #120 Tripackers (EN), #229 Amara (VI).
```
Kính gửi [chị Tên / Phòng Kế toán Đại lý],

HAYA Hotel Phu Quoc, Trademark Collection by Wyndham xin cảm ơn Quý Công ty đã gửi ủy nhiệm chi thanh toán cho booking:

Mã đặt phòng: [mã]
Mã đoàn: #[mã đoàn]
Tên khách: [tên]
Thời gian lưu trú: [ngày] – [ngày] ([n] đêm)
Tổng tiền: [tổng] VND
[Đã nhận cọc 50%: [tiền] VND (tiền về tài khoản khách sạn ngày [date])]
[Số tiền còn lại: [tiền] VND, vui lòng thanh toán trước ngày [date]]

Khách sạn đã chuyển ủy nhiệm chi cho bộ phận Kế toán để đối chiếu và sẽ phản hồi khi tiền về tài khoản.

Thông tin xuất hóa đơn đã được ghi nhận: [Tên công ty] – MST [mã] – [địa chỉ] – hóa đơn gửi [email]; [yêu cầu riêng: ghi số booking, xuất ngày check-out …].

Trân trọng,
Reservations Team
…
```
- **Chưa đối chiếu thì không viết "đã nhận tiền"**: `đã chuyển cho bộ phận kế toán kiểm tra` / EN `Our accounting team will check that the amount has been credited to our account, and we will confirm once it is reconciled.` Chỉ viết `đã nhận được tiền cọc (tiền về tài khoản ngày …)` khi kế toán đã xác nhận (#326).
- Số trên UNC thiếu so với 50%: nói số đã nhận và số còn thiếu.
- UNC chưa được duyệt (#7): `bộ phận kế toán khách sạn cho biết UNC này chưa được duyệt và đến nay khách sạn chưa nhận được khoản thanh toán. Chị vui lòng kiểm tra lại giúp em và gửi lại UNC đã được duyệt/hoàn tất…`

### B4. Chuyển UNC cho kế toán (nội bộ)
Nguồn: #67 An0109. Gửi `accountant@palmahotel.vn`, tiêu đề `Fw: [tiêu đề gốc] – UNC cọc #[mã đoàn]`.
```
Mã đoàn: #[mã đoàn]

Dear chị, em gửi UNC đặt cọc của [Đại lý] cho booking [mã] (mã đoàn #[mã], conf [số]).

Tổng đoàn: [tổng] VNĐ
Cọc 50% theo hợp đồng: [tiền] VNĐ
Số trên UNC ([ngân hàng], [ngày giờ]): [tiền] VNĐ — [đủ / thiếu [tiền] so với 50%]
Số tham chiếu: [số] | Mã GD: [mã]
Nội dung CK: [nội dung]
Tài khoản nhận: 1020729617 Vietcombank

Nhờ chị đối chiếu số tiền vào tài khoản và xuất hóa đơn VAT theo:
[TÊN CÔNG TY]
MST: [mã]
[Địa chỉ]
Email: [email]

UNC đính kèm.

Trân trọng,
Reservations team / HAYA Hotel Phu Quoc
sales@haya-hotels.com
```
- Giọng nội bộ: "Dear chị", "em gửi", "nhờ chị". Dòng đầu là mã đoàn để kế toán tìm nhanh.

### B5. Nhắc thanh toán (lần 1, lần 2, lần cuối)
Nguồn: #218, #217 Victoria (VI), #216 Travel Concierge (EN), #339 final (EN).
```
Kính gửi chị [Tên],

HAYA Hotel Phu Quoc, Trademark Collection by Wyndham xin gửi chị lời nhắc thanh toán cho đặt phòng sau. Đến nay bộ phận kế toán khách sạn chưa nhận được khoản thanh toán nào:

Mã đoàn: #[mã]
Số xác nhận: [số]
Mã đặt phòng: [mã]
Khách đại diện: [tên] ([n] người lớn)
Đại lý du lịch: [đại lý]
Thời gian lưu trú: [ngày] – [ngày] ([n] đêm)
Hạng phòng: [phòng]
Tổng tiền: [tổng] VND (bao gồm ăn sáng và VAT 8%)
Đã thanh toán: 0 VND
Số tiền cần thanh toán: [tiền] VND ([50% / 100%])
Hạn thanh toán: [trước ngày nhận phòng DD/MM/YYYY / HH:MM ngày DD/MM/YYYY]

Thông tin tài khoản thanh toán:
Tên tài khoản: CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC
Số tài khoản: 1020729617
Ngân hàng: Vietcombank, CN Phú Quốc

Nội dung chuyển khoản: Tên Công ty + Mã đoàn #[mã]. Sau khi chuyển khoản, chị vui lòng gửi ủy nhiệm chi (UNC) qua email để khách sạn đối chiếu.

Nếu đã thanh toán, chị vui lòng gửi giúp UNC và bỏ qua email này.

Trân trọng,
Reservations Team
…
```
- Tiêu đề: thêm `- NHẮC THANH TOÁN #[mã đoàn]` / `- PAYMENT REMINDER #[mã]` / `- FINAL PAYMENT REMINDER #[mã]` vào cuối tiêu đề gốc.
- EN mở: `This is a friendly payment reminder for the booking below. Our accounting team has not yet received any payment:`
- Lần 2/cuối (EN): `Following our reminders of 22/10 and 25/10, we have still not received any payment for the booking below:` + khối bullet + `If payment is not received by [HH:MM] on [DD/MM/YYYY] (Vietnam time), the booking will be cancelled.` — câu hủy là quyết định của Karen, Emi không tự đặt.

### B6. Tour operator: xác nhận, hủy, từ chối on-request
Nguồn: #205 Odeon, #29 / #44 / #299 Anex, #243 Pegas, #252 Selfie.
- **Xác nhận (Odeon)**: thư mới, tiêu đề `Odeon Reservation confirmation [ref]`.
  ```
  Dear Odeon Tours Vietnam Reservations Team,

  Thank you for your reservation.

  We are pleased to confirm the following booking at HAYA Hotel Phu Quoc – Trademark Collection by Wyndham:

  Ref [ref] ([Sunmar / Coral], voucher [số])
  Guests: [tên]
  Dates: [ngày] – [ngày] ([n] nights)
  Room: 1 [hạng], [n] adults
  Meal plan: BB
  Hotel confirmation no.: [số]
  Group code: #[mã]

  Please find attached our confirmation and invoice.
  ```
- **Hủy (Anex)**: `We confirm that reservation No. [số] ([khách], [phòng], [ngày]) has been cancelled in our system without charge.` + Group code / Confirmation number + `Please let us know if you need anything else.` Nếu khách có booking mới thay thế: `Please note that the guests' new reservation No. [số] remains confirmed under group #[mã].`
  - "without charge" chỉ khi Karen đã quyết là không phí (luật 7).
- **Từ chối on-request**: tiêu đề `Bookings [số] / [số] – Declined (on request)`.
  ```
  Dear Pegas team,

  Thank you for your reservation requests.

  Unfortunately we are unable to accommodate the following on-request bookings:

  Booking no.: [số]
  Guests: [tên]
  Room: 1 [hạng], [n] adults
  Stay: [ngày] – [ngày] ([n] nights)

  Kindly decline these requests in your system. We apologise for the inconvenience and look forward to your next booking.
  ```
- **Thông báo hủy cho booking đã từ chối** (#299): `We acknowledge the cancellation of reservation No. [số] … This on-request booking had already been declined by the hotel and was never confirmed, so there is no hotel group code and no cancellation charge. Reservation No. [số] is closed on our side.`
- HAYA **có trả lời** địa chỉ robot của Anex / Selfie (`vn.robot@`, `mailrobot@`), cc `reservation@anexvietnam.com`.

### B7. Bedbank / OTA hỏi số xác nhận (HCN) hoặc reconfirm
Nguồn: #51 RezLive, #126 BiziTrip, #323 TBO, #301 Within Earth, #138 (khách Agoda), #345 Arbitrip.
```
Dear [Bedbank] Team,

Greetings from HAYA Hotel Phu Quoc, Trademark Collection by Wyndham, and thank you for your email. [We confirm that the following reservation is held in our system as Definite: / Please find the hotel confirmation for the booking below:]

Hotel confirmation number: [số] (hotel group code #[mã])
[TBO Booking ID / Your reference]: [ref]
Supplier reference: [ref] ([MG Bedbank / …])
Guest(s): [tên] ([quốc tịch])
Stay: [ngày] – [ngày] ([n] nights)
Room: 01 [hạng] – [n] adults
Meal plan: Breakfast included
Payment: [prepaid by the booking agency / covered by the third-party supplier]

We look forward to welcoming the guests.
```
- Thư thường do lễ tân (haya@) forward vào → trả lời thẳng người gửi gốc, **cc haya@haya-hotels.com**.
- Có thể thêm `The confirmation number is valid for all nights of the stay.` và `Please find our booking confirmation attached.`
- Booking chưa có trong EZFOLIO: HAYA từng viết "our reservations team is checking… we will send the HCN as soon as possible" (#289) — **Emi không viết câu chờ** (AGENTS.md luật 9): không soạn thư, báo trong report "chờ EZFOLIO".

### B8. Yêu cầu đặc biệt từ bedbank / đại lý (giường, nôi em bé, ăn kiêng)
Nguồn: #11 Ohmyhotel, #224 RezLive, #285 Jain meal.
- Ngắn: `We have noted the request for booking [ref] (hotel code [mã]): a baby cot will be provided in the room for the 6-month-old infant, free of charge.`
- Có khối booking ngắn rồi một dòng cho yêu cầu: `Special request – king-size bed: noted. We will do our best to arrange it, subject to availability at check-in.`
- Nhiều yêu cầu: mỗi yêu cầu một đoạn có nhãn đầu dòng: `Room allocation: …`, `Jain meal: vegetarian options are available at our breakfast. We have noted your pure vegetarian Jain (VJML) requirements … and passed them to our kitchen team.`
- Nôi em bé miễn phí là chính sách đã có của HAYA (#11) — ghi vào `hotel-info.md` sau khi Karen xác nhận.

### B9. Khách OTA nhắn qua Booking.com / Expedia / Agoda / Trip.com
Nguồn: #10, #240, #297 (Booking.com), #34 (Expedia), #201 (Agoda), #75 (Trip.com).
```
Dear Ms [Surname],

Thank you for your message.

We have noted [your request for a non-smoking room away from the elevator, with two single beds,] for your stay [in a Deluxe Sea View room] from [16] to [19 October 2026]. We will do our best to arrange this for you, subject to availability at check-in.

We look forward to welcoming you.

Kind regards,
Reservations Team
HAYA Hotel Phu Quoc, Trademark Collection by Wyndham
sales@haya-hotels.com
```
- Luôn tiếng Anh (tin nhắn đến qua Booking.com bằng tiếng Việt chỉ là khung của Booking.com; khách viết tiếng gì thì xem nội dung khách).
- Đến sớm: `Our standard check-in time is 14:00; we will try to have your room ready earlier, subject to availability. If it is not yet ready when you arrive, you are welcome to leave your luggage with us and enjoy the hotel facilities in the meantime.`
- Báo giờ đến (#297): nhắc lại booking ngắn (mã, ngày, phòng, giờ đến) + `Check-in time is from 14:00, so your room will be ready for you on arrival.`
- **Đến khuya (#75): `Rest assured that our hotel staff is available 24/7 to assist you with check-in.`** → lễ tân trực 24/7: cập nhật `hotel-info.md` (đang ở mục "Chưa biết").
- Agoda gửi yêu cầu thay khách (#201): `Dear Agoda team,` + khối bullet (Agoda booking ID, Hotel group code, Guest, Stay, Request) + câu trả lời.

### B10. Đưa đón sân bay
Nguồn: #89 (Klook, 7 phòng), #114 (Agoda), #308 (miễn phí), #21 (Booking.com).
- **Không đủ điều kiện miễn phí**: `Complimentary one-way airport pick-up applies only when the booking total is above USD 250 (about 6,600,000 VND). Your booking is below that threshold, so pick-up is available as a paid transfer at [giá] VND one way.` (#114) · Klook: `complimentary airport pick-up is only included with bookings made on selected channels, such as Booking.com. Unfortunately, it does not apply to your current reservations.` (#89)
- **Giá xe**: 4 chỗ 200.000 VND/chiều (FAQ); **xe 16 chỗ 350.000 VND/chiều** (#89, #114) — giá xe 16 chỗ chưa có trong `hotel-info.md` (bảng TA ghi 400.000 cho đại lý).
- **Đủ điều kiện** (#308): `We are pleased to confirm that we can arrange your complimentary airport pick-up…` + khối booking + `Pick-up date: …` + `Our driver will meet you in the arrival hall after you have cleared immigration and collected your baggage.`
- Để đặt xe, HAYA hỏi: số chuyến bay, giờ hạ cánh, số WhatsApp, (số khách, số vali). Đây là khi **khách đã xin đưa đón** — không mâu thuẫn với luật "không tự hỏi chuyến bay" của Emi.

### B11. Hỏi giá — đại lý
Nguồn: #294 Explore Vietnam (EN), #5 Victoria (VI), #213 (hết phòng), #264 (xin hợp đồng), #220 (đoàn).
- **Có phòng**: khối "Stay / Rooms / Guests" bằng bullet, rồi **bảng các hạng phòng** (hạng + giường, giá/đêm, tổng n đêm), rồi `Notes:` bullet: giá net VND gồm ăn sáng, hồ bơi, gym, 8% VAT · loại giường · `Rates are subject to availability at the time of confirmation.` · thanh toán · chính sách hủy · giờ nhận/trả phòng. Kết: `To proceed, please confirm your preferred room type together with the guests' full names…`
- **Hết phòng**: hai câu, không chào hạng khác khi cả khách sạn hết: `Unfortunately, the hotel is fully booked for 8-11 November 2026, so we are unable to offer a room for these dates. We hope to welcome your guests on another occasion.`
- **Xin hợp đồng / hợp tác** (#264): cảm ơn, đồng ý hợp tác, `Bộ phận Kinh doanh sẽ gửi … bảng giá hợp đồng năm 2026 – 2027 … trong thời gian sớm nhất` — đây là việc của Karen; Emi chỉ báo Karen, không hứa gửi.
- **Đoàn, ngày chưa rõ** (#220): HAYA đã hỏi lại chi tiết trước; luật của dev 22/10 là **trả giá ngay** cho khoảng ngày họ nói (`inquiries-and-quotes.md`) — giữ luật của Emi.

### B12. Hỏi giá — khách lẻ
Nguồn: #187 (VI), #276 (EN), #313 (EN).
- VI (#187): danh sách `•` hạng phòng – giường – giá/đêm, `Tổng 2 đêm (…): … VND/phòng, đã bao gồm ăn sáng và 8% VAT.`, gợi ý hạng rẻ hơn một dòng, rồi danh sách đánh số những gì cần để đặt (hạng chọn, họ tên, số người lớn/trẻ em), `Quý khách vui lòng thanh toán 100% trước khi nhận phòng.`
- EN (#276): hết hạng khách hỏi → nói thẳng, đưa hạng thay thế; trả lời từng câu khách hỏi theo danh sách đánh số; `As availability is limited during this period, we recommend confirming at your earliest convenience.`
- Có xin lỗi khi trả lời chậm: `…xin lỗi chị vì phản hồi chậm.`

---

## C. Khác với Emi hiện tại (`skills/email-templates.md`) — cần sửa

| Emi đang làm | HAYA đang gửi | Đề xuất |
|---|---|---|
| Ký `Best,` / `HAYA Team` (luật Karen 08/10) | `Trân trọng,` / `Best regards,` + `Reservations Team` + `HAYA Hotel Phu Quoc, Trademark Collection by Wyndham` + `sales@haya-hotels.com` | Đổi theo Sent — **cần Karen duyệt** vì trái quyết định 08/10 |
| Nhãn in đậm `**Mã đoàn:**`, dòng trống giữa các nhóm | Nhãn thường, các dòng liền nhau, một dòng trống giữa các khối | Bỏ in đậm, gom khối như Sent |
| `Kính gửi chị [Tên]` + câu cảm ơn cố định | Câu mở cảm ơn đúng việc vừa làm (gửi booking / gửi UNC / phản hồi) | Câu mở theo việc |
| VI: tự gọi "HAYA" | VI: chủ yếu "Khách sạn"; nội bộ "em" | Thư đối ngoại dùng "Khách sạn"; "HAYA" khi mở câu bằng tên đầy đủ |
| Giá: một dòng "Đơn giá" | Mỗi hạng một dòng có phép tính `giá × phòng × đêm = tiền` | Thêm phép tính |
| Không có chính sách hủy trong xác nhận | Có (#254, #294) | Thêm dòng chính sách hủy TA |
| Nhắc thanh toán: chưa có mẫu khớp | Mẫu B5 (tiêu đề `- NHẮC THANH TOÁN #mã`, "Đã thanh toán / Số tiền cần thanh toán / Hạn") | Dùng mẫu B5 |
| Forward kế toán: chưa có khung | Mẫu B4 | Dùng mẫu B4 |
| Từ chối on-request / xác nhận hủy tour operator | Mẫu B6 | Dùng mẫu B6 |
| HCN / reconfirm | Mẫu B7, cc haya@ | Dùng mẫu B7 |

**Những gì Sent làm mà Emi KHÔNG làm theo** (luật cứng):
- Hứa miễn phí: "early check-in … free of charge" (#10), nôi em bé miễn phí (#11) → chỉ khi là chính sách đã ghi; còn lại Karen (luật 8).
- Thư chờ: "our team is checking… we will send … as soon as possible" (#289), "Bộ phận Kinh doanh sẽ gửi … trong thời gian sớm nhất" (#264) → Emi không soạn thư chờ (luật 9).
- Tự hỏi chuyến bay / giờ đến khi khách không xin đưa đón (#294 "flight details") → luật 22/10 của dev.
- Câu "booking will be cancelled" có giờ cụ thể (#339) → Karen quyết.
- Tên tài khoản cũ `CÔNG TY TNHH MTV DU LỊCH PHUONG NGUYỄN` (#45) → luôn dùng tên mới `CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC`.
- Hạn 50% còn lại "48 giờ trước ngày nhận phòng" (#326) khác luật "7 ngày trước" → giữ 7 ngày, báo Karen nếu thấy thư như vậy.

**Thông tin mới để thêm vào `hotel-info.md`** (sau khi Karen xác nhận):
- Lễ tân hỗ trợ nhận phòng 24/7 (#75).
- Xe 16 chỗ đón sân bay: 350.000 VND/chiều cho khách lẻ (#89, #114).
- Nôi em bé: miễn phí (#11).
- Khách Klook không được đưa đón miễn phí; Booking.com được (#89).
