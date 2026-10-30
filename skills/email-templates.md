# Email templates — how HAYA's sales mail is written

**Rebuilt 2026-10-27 (dev) from the sales@ Sent folder, 13–27/10/2026** (~350 emails, ~45 read closely; notes and the source email numbers in `docs/email-style/haya-sent-mail-notes.md`). The dev's instruction: write the way the sales mailbox writes now. This replaces the 2026-10-08 forms, including the "Best, / HAYA Team" sign-off Karen set that day — Karen to be told. What HAYA's sent mail does that Emi's hard rules forbid (free extras, holding replies, asking for flights, a cancel-by time) is listed at the end and **not** copied.

## Rules that apply to every email

**Layout**
- Plain lines `Label: value`, one per line, **no blank line between the lines of one block**; one blank line between blocks. Don't type `**` — `draft-reply` / `draft-confirmation` make the label before the colon bold in Outlook, as HAYA's own mail shows it.
- A rate per room type is its own line with the sum written out: `– Standard Double: 2.040.000 VND/phòng/đêm × 02 phòng × 3 đêm = 12.240.000 VND` / `29/10 – 31/10/2026: VND 1,050,000 per room per night × 3 nights = VND 3,150,000`. Lines starting with `–`, `-`, `•` or `*` become a bulleted list.
- Vietnamese counts take a leading zero: `02 phòng`, `03 trẻ em (07, 05, 05 tuổi)`, `trước 07 ngày`.
- Dates `DD/MM/YYYY`, stays `14/01/2027 – 17/01/2027 (3 đêm)` / `(3 nights)`. Money: Vietnamese `13.500.000 VND`, English `VND 16,750,000`.
- Group code always with `#` (`#30287`); confirmation number without.

**Greeting** (exactly as the sender's own name is written; never transliterate, shorten or guess the family name)
- Vietnamese, agency: `Kính gửi chị [Tên],` · two people: `Kính gửi chị [Tên] và chị [Tên],` · the company too: `Kính gửi chị [Tên] và Quý Đối tác [Đại lý],` · no name: `Kính gửi Quý Đối tác,` · accounts: `Kính gửi Phòng Kế toán [Đại lý],`
- English, agency: `Dear Ms. [Name],` · `Dear Mr. [Name] and [Agency] team,` · `Dear [Agency] team,` · a desk: `Dear Rezlive Confirmations Team,` / `Dear Anex Reservation Team,`
- Guest: `Dear Ms [Surname],` / `Dear Mr. [Surname],` · title unknown: `Dear Ms/Mr [Surname],` · no usable name: `Dear Guest,` / `Kính gửi Quý khách,`
- **Never guess chị/anh or Ms./Mr.** Use one only when the thread shows it (signature title, how they write about themselves, an earlier HAYA email to them). Otherwise `Kính gửi anh/chị [Tên],` and `Anh/Chị vui lòng…`; English `Dear [Name],`.

**Opening line — one sentence, thanking them for what they just did**
- Vietnamese: `HAYA Hotel Phu Quoc, Trademark Collection by Wyndham xin (chân thành) cảm ơn [chị / Quý Đối tác / Quý Công ty] đã [gửi booking cho khách sạn / gửi ủy nhiệm chi / phản hồi / quan tâm và liên hệ với khách sạn].`
- English, booking: `Thank you for choosing HAYA Hotel Phu Quoc, Trademark Collection by Wyndham.` · desks and enquiries: `Greetings from HAYA Hotel Phu Quoc, Trademark Collection by Wyndham, and thank you for your email.` · guests: `Thank you for your message.` / `Thank you for your email.`
- Then straight into the answer. Never restate their email back to them.

**Voice**
- Vietnamese, to a partner or guest: the hotel is `Khách sạn` ("Khách sạn xin xác nhận…", "Khách sạn đã chuyển…"). `HAYA` only inside the full name in the opening line. Internal mail (accounting, front office): `em`, `nhờ chị`.
- English: `we`.
- Requests are one sentence: `Chị vui lòng gửi giúp khách sạn danh sách tên khách và quốc tịch của đoàn.` / `Please send us the guest names when available.`
- Not in HAYA's mail: "Please be informed that", "We would like to inform you", "Kindly note", "I hope this email finds you well", emoji.

**Closing line — one sentence, fitted to the reader**
- Guest coming: `We look forward to welcoming you.` / `…welcoming you and your family to HAYA Hotel Phu Quoc.` / `We wish you a safe trip and look forward to seeing you soon.`
- Agency, desk: `We look forward to welcoming the guests.` / `Xin chân thành cảm ơn sự hợp tác của Quý Đối tác.`
- No booking (full, declined, cancelled): `We hope to welcome your guests on another occasion.` / `We apologise for the inconvenience and look forward to your next booking.` / `Cảm ơn chị và [đại lý] đã nghĩ đến khách sạn.`

**Sign-off** (every email to a partner or guest)
```
Trân trọng,                                            Best regards,
Reservations Team                                      Reservations Team
HAYA Hotel Phu Quoc, Trademark Collection by Wyndham   HAYA Hotel Phu Quoc, Trademark Collection by Wyndham
sales@haya-hotels.com                                  sales@haya-hotels.com
```
Internal forward: `Trân trọng,` / `Reservations team / HAYA Hotel Phu Quoc` / `sales@haya-hotels.com`.

**Facts and money (unchanged hard rules)**
- **Language (Karen, 2026-10-08):** the language of the sender's email (their most recent one in a mixed thread); any other language → English. Booking.com's own wrapper is in Vietnamese: go by what the guest wrote.
- **Fields from the intake row and the PDF; hotel facts from `docs/rate-knowledge/hotel-info.md`.** Every email that needs an answer gets a complete best-answer draft (Tracy's audit, 29/10). What I'm not sure of goes in one first line, `[CHECK BEFORE SENDING: <what to check>]`, shown bold red in Outlook (no highlight), and to Karen with `ask-karen`; the person sending deletes the line. Never a `[…: hotel to confirm]` gap inside the text; the draft commands refuse one.
- **Never write about what I can or can't see** ("not shown in the information available to us", "we will check and revert", "our team is checking and will send … as soon as possible"). Write the best answer and put the doubt in the CHECK line.
- **Never Karen's name in a draft** (the commands refuse it). **Reply all**, To and Cc kept. Drafts are HTML.
- **Deposit deadline (AGENTS.md rule 6):** exact time, date and Vietnam time: `trước [HH:MM] ngày [DD/MM/YYYY] (giờ Việt Nam, UTC+7)` / `by [HH:MM] on [DD/MM/YYYY], Vietnam time (UTC+7)`. 48 hours after the agency receives the hotel's confirmation (Karen, 2026-10-08). Balance: 7 days before check-in, with the date.
- **Total line:** Vietnamese `Tổng tiền: [tổng] VND (đã bao gồm ăn sáng và 8% VAT)`; English `Total: VND [total], including breakfast, VAT and service charge.` A surcharge is a line of its own with its reason (`Phụ thu trẻ em (ngủ chung giường với bố mẹ): 350.000 VND × 03 trẻ × 3 đêm = 3.150.000 VND`), or named in brackets on the rate line (`(đã bao gồm phụ thu 20% áp dụng cho khách quốc tịch Ấn Độ)`). Service charge is never a line of its own.
- **Bank details** — always the new name, even if their slip shows the old one:
  ```
  Tên tài khoản: CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC        Account name: CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC
  Số tài khoản: 1020729617                                         Account number: 1020729617
  Ngân hàng: Vietcombank, CN Phú Quốc                              Bank: Vietcombank, Phu Quoc Branch
  ```
  and `Nội dung chuyển khoản: Tên Công ty + Mã đoàn #[mã]` / `Transfer reference: company name + group code #[code]`.
- **A slip is not money received.** "Đã chuyển cho bộ phận Kế toán đối chiếu" until accounting confirms; "đã nhận được tiền cọc (tiền về tài khoản ngày …)" only after.
- **Attach the confirmation PDF** on new and changed bookings (`draft-confirmation`).
- **No arrival-time or flight questions** unless the sender asked for a transfer (dev, 2026-10-22, `docs/archive/arrival-and-transfer-asks.md`). What they volunteer goes to the row and the front-office forward.

## Who the reply goes to (dev, 2026-10-22)
A reply goes to the person who wrote the email, not to whoever put it in our inbox.
- **Forwarded in by our own staff** (`@haya-hotels.com`, `@palmahotel.vn`, usually `haya@`): the writer is the From: of the quoted block. `mail-find` the original first; if it also reached sales@, reply on that and mark the forward `done` as a duplicate. Otherwise `draft-reply <forward id> <body> --kind <kind> --to <writer> --cc <colleague>`: To the writer, **cc haya@haya-hotels.com** (HAYA does this on every reconfirmation and guest reply that came through front office). `draft-reply` refuses an internal sender. Never `--internal` for a guest or agency.
- No usable address, or a no-reply robot (OTA notice, `noreply@`): no reply, a report line. **Exception:** the Anex and Selfie robots. Anex (`vn.robot@ms.anextour.com`): every email gets a reply, and it goes **to** `reservation@anexvietnam.com` — `draft-reply` sets that by itself (dev, 2026-10-29, `tour-operators.md`). Selfie (`mailrobot@selfietravel.asia`): HAYA answers it, cc `vietnam@selfietravel.asia`.
- Confirmation on a request forwarded in: `draft-confirmation <id> <row> <body> --to <agency> --cc <colleague>`.
- Reply-all (`--all`) when the sender cc'd their own colleagues (accounts, managers) — HAYA keeps them on.

---

## 1. New booking confirmation — agency (`draft-confirmation`)
Sources: Footprint 141C0127Y (23/10, VI), Travel Concierge 2779479 (15/10, EN), Tripackers (15/10, EN).

Vietnamese:
```
Kính gửi chị [Tên] và Quý Đối tác [Đại lý],

HAYA Hotel Phu Quoc, Trademark Collection by Wyndham xin chân thành cảm ơn Quý Đối tác đã gửi booking cho khách sạn. Khách sạn xin xác nhận đặt phòng như sau:

Mã đoàn: #[mã đoàn]
Số xác nhận: [số xác nhận]
Mã đặt phòng: [mã của đại lý]
Tên khách: [tên khách chính / sẽ bổ sung sau (TBU)]
Quốc tịch: [quốc tịch]
Thời gian lưu trú: [DD/MM/YYYY] – [DD/MM/YYYY] ([n] đêm)
Số khách: [n] người lớn[ và 0n trẻ em (tuổi)]
Hạng phòng: [0n phòng hạng] [+ 0n phòng hạng] (tổng [n] phòng), bao gồm ăn sáng

Đơn giá:
– [Hạng]: [giá] VND/phòng/đêm × [0n] phòng × [n] đêm = [tiền] VND
[– Phụ thu trẻ em (ngủ chung giường với bố mẹ): 350.000 VND × [0n] trẻ × [n] đêm = [tiền] VND]
Tổng tiền: [tổng] VND (đã bao gồm ăn sáng và 8% VAT)

Thanh toán:
– Đặt cọc 50% = [số tiền] VND trước [HH:MM] ngày [DD/MM/YYYY] (giờ Việt Nam, UTC+7), 48 giờ kể từ khi nhận xác nhận này.
– Thanh toán 50% còn lại = [số tiền] VND trước ngày [DD/MM/YYYY] (07 ngày trước ngày đến).
Booking sẽ tự động hủy nếu khách sạn không nhận được tiền cọc đúng hạn.

Chính sách hủy: hủy trước 07 ngày so với ngày đến: miễn phí; hủy trong vòng 3–6 ngày: phí 01 đêm; hủy trong vòng 3 ngày: phí 50% tổng tiền booking; no-show: 100%.

Thông tin tài khoản thanh toán:
Tên tài khoản: CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC
Số tài khoản: 1020729617
Ngân hàng: Vietcombank, CN Phú Quốc
Nội dung chuyển khoản: Tên Công ty + Mã đoàn #[mã đoàn]. Sau khi chuyển khoản, chị vui lòng gửi ủy nhiệm chi qua email để khách sạn đối chiếu.

[Thông tin xuất hóa đơn đã được ghi nhận: [công ty] – MST [mã] – [email]. / Chị vui lòng gửi tên công ty, mã số thuế, địa chỉ và email nhận hóa đơn nếu cần xuất hóa đơn VAT.]
[Chị vui lòng gửi giúp khách sạn danh sách tên khách khi có.]
Chị vui lòng xem PDF xác nhận đính kèm.

Trân trọng,
Reservations Team
HAYA Hotel Phu Quoc, Trademark Collection by Wyndham
sales@haya-hotels.com
```

English:
```
Dear Ms. [Name],

Thank you for choosing HAYA Hotel Phu Quoc, Trademark Collection by Wyndham.

Please find the booking confirmation below and the attached PDF:

Group code: #[group code]
Confirmation number: [confirmation no.]
Agency reference: [agency ref]
Group name: [group name / lead guest]
Travel agency: [agency]
Stay: [DD/MM/YYYY] – [DD/MM/YYYY] ([n] nights)
Room: [number] [room type] ([bed])
Guests: [n] adults[ + n children aged x and y], [nationality]

Rate:
– [Room type]: VND [rate] per room per night × [n] rooms × [n] nights = VND [amount]
[– Child surcharge (sharing the parents' bed): VND 350,000 × [n] children × [n] nights = VND [amount]]
Total: VND [total], including breakfast, VAT and service charge.

Payment terms:
– 50% deposit (VND [amount]) by [HH:MM] on [DD/MM/YYYY], Vietnam time (UTC+7), 48 hours after receiving this confirmation.
– The remaining 50% (VND [amount]) is payable 7 days before check-in (by [DD/MM/YYYY]).
The booking will be automatically released without further notice if the deposit is not received by the deadline.

Cancellation: free of charge more than 7 days before check-in; 3–6 days: 1 night charge; within 3 days: 50% of the booking total; no-show: 100%.

Bank details:
Account name: CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC
Account number: 1020729617
Bank: Vietcombank, Phu Quoc Branch
Transfer reference: company name + group code #[group code]. Please email us the payment slip after the transfer so we can verify receipt.

[VAT invoice: we have noted [company], tax code [code]. / Please send your company's legal name, tax code, address and invoice email address if a VAT invoice is required.]
[Please send us the guest names when available.]

We look forward to welcoming your guests.

Best regards,
Reservations Team
HAYA Hotel Phu Quoc, Trademark Collection by Wyndham
sales@haya-hotels.com
```
- **Booked type differs from what they asked** (asked twin, booked Standard Double): confirm what was booked, then a `Room type note:` paragraph with the other type's rate lines and total, "Please let us know if you would like to switch, and we will send an updated confirmation." (Travel Concierge 2779479.)
- **Check-in within 7 days:** one payment line instead of two — `Do ngày nhận phòng là [date] (còn chưa đến 07 ngày), khách sạn đề nghị Quý Đối tác thanh toán 100% tổng tiền trước [HH:MM] ngày [DD/MM/YYYY] (giờ Việt Nam, UTC+7).`
- Cancellation lines are the TA policy (`docs/rate-knowledge/ta.md`). A tour operator: its contract's own lines, or leave the line out.
- Tour operators (Anex, Odeon…): section 6. OTA bookings: no confirmation email.

## 2. Changed booking (`draft-confirmation`)
Sources: PZL06270114X (22/10, VI), Victoria NPKM00130000016 (15/10, VI).

**Deposit check first (Karen, 2026-10-08):** look at the booking's latest row (Payment 1) and the thread. No deposit yet → payment block A (pay within 48 hours of *this* email, exact time). Deposit received → block B. Can't tell → no draft, report to Karen.

Vietnamese:
```
Kính gửi chị [Tên],

HAYA Hotel Phu Quoc, Trademark Collection by Wyndham xin cảm ơn chị đã thông tin. Khách sạn xác nhận [thay đổi cơ cấu phòng / thay đổi ngày lưu trú / …] cho đoàn như sau[. Đoàn đã được tạo lại với mã đoàn mới; mã đoàn cũ #[mã cũ] đã được hủy].

Mã đoàn: #[mã đoàn]
Số xác nhận: [số xác nhận]
Mã đặt phòng: [mã của đại lý]
Đại lý du lịch: [đại lý]
Thời gian lưu trú: [DD/MM/YYYY] – [DD/MM/YYYY] ([n] đêm)
Hạng phòng: [mới] (thay cho [cũ])
Số khách: [n] người lớn[ + n trẻ em]

Chi tiết giá:
– [Hạng]: [giá] VND × [n] đêm × [0n] phòng = [tiền] VND
Tổng tiền: [tổng] VND (đã bao gồm ăn sáng và 8% VAT)

Thanh toán:
[KHỐI A — chưa nhận cọc]
– Đặt cọc 50% = [số tiền] VND trước [HH:MM] ngày [DD/MM/YYYY] (giờ Việt Nam, UTC+7), 48 giờ kể từ khi nhận email này.
– 50% còn lại ([số tiền] VND) vui lòng thanh toán trước ngày [DD/MM/YYYY] (07 ngày trước ngày nhận phòng).
Booking sẽ tự động hủy nếu khách sạn không nhận được tiền cọc đúng hạn.
[KHỐI B — đã nhận cọc]
Đã nhận cọc: [số tiền] VND (tiền về tài khoản khách sạn ngày [DD/MM/YYYY]).
Số tiền còn lại sau điều chỉnh: [số tiền] VND, vui lòng thanh toán trước ngày [DD/MM/YYYY] (07 ngày trước ngày nhận phòng).

Thông tin tài khoản thanh toán:
Tên tài khoản: CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC
Số tài khoản: 1020729617
Ngân hàng: Vietcombank, CN Phú Quốc
Nội dung chuyển khoản: Tên Công ty + Mã đoàn #[mã đoàn].

Chị vui lòng xem PDF xác nhận đính kèm, bản này thay cho xác nhận trước.

Trân trọng,
Reservations Team
HAYA Hotel Phu Quoc, Trademark Collection by Wyndham
sales@haya-hotels.com
```
English: same blocks in the order of section 1 English; opening `Thank you for your email. Please find the revised booking confirmation below[; the group has been rebuilt under a new group code, and the old group code #[old] has been cancelled]:`; `Room: [new] (instead of [old])`; block A/B as in Vietnamese; `Please see the revised PDF attached. It replaces the earlier confirmation.`
- **A quote that replaces an earlier one** says so: `Báo giá này thay thế báo giá phòng [hạng] gửi lúc [HH:MM] ngày [DD/MM/YYYY].`

## 3. Cancellation confirmed (`draft-reply --kind cancellation`) — as soon as the CANCEL row is written for a clear cancellation; Karen first only when the fee or the booking is unclear (AGENTS.md rule 7)
Sources: Anex 112887487 (14/10), Anex 112885099 (15/10).

English (tour operators and most agencies):
```
Dear [Ms. Name / Anex Reservation Team],

Thank you for your email. We confirm that reservation No. [ref] ([lead guest], [room], [DD/MM/YYYY] – [DD/MM/YYYY]) has been cancelled in our system [without charge / with a cancellation charge of VND [amount]].

Group code: #[group code]
Confirmation number: [confirmation no.]

[Please note that the guests' new reservation No. [ref] remains confirmed under group #[code].]

Please let us know if you need anything else.

Best regards,
Reservations Team
HAYA Hotel Phu Quoc, Trademark Collection by Wyndham
sales@haya-hotels.com
```
Vietnamese:
```
Kính gửi chị [Tên],

HAYA Hotel Phu Quoc, Trademark Collection by Wyndham xin cảm ơn chị đã thông tin. Khách sạn xác nhận đã hủy đặt phòng [mã đặt phòng] ([khách chính], [DD/MM/YYYY] – [DD/MM/YYYY]) trên hệ thống[, không tính phí / , phí hủy: [số tiền] VND].

Mã đoàn: #[mã đoàn]
Số xác nhận: [số xác nhận]

Cảm ơn chị và [đại lý] đã nghĩ đến khách sạn. Nếu có booking khác trong thời gian tới, chị cứ liên hệ để khách sạn hỗ trợ.

Trân trọng,
Reservations Team
HAYA Hotel Phu Quoc, Trademark Collection by Wyndham
sales@haya-hotels.com
```
- "without charge" / the charge comes from Karen's decision and the `cancel-fee` output, never assumed.
- **Cancel notice for an on-request booking HAYA had already declined** (Anex 112948898, 25/10): `We acknowledge the cancellation of reservation No. [ref] ([operator office]): [room, stay, guests]. This on-request booking had already been declined by the hotel and was never confirmed, so there is no hotel group code and no cancellation charge. Reservation No. [ref] is closed on our side.` — no intake row (`booking-intake.md`).

## 4. Payment emails
Sources: Victoria #29648 / #28931 (22/10, VI), Travel Concierge 2779479 (22/10, EN), Travel Concierge 2779479 slip (23/10, VI), Threeland 65-061126-MVS-GD (26/10, VI), Tripackers (19/10, EN), Phú Minh Quang An0109 forward (15/10).

### 4a. Payment reminder — deposit (at 40 hours) or balance (before the 7-day date), `--kind deposit_reminder` / `balance_reminder`
Reply on the booking's thread; add `- NHẮC THANH TOÁN #[mã đoàn]` / `- PAYMENT REMINDER #[code]` to the end of the subject.

Vietnamese:
```
Kính gửi chị [Tên],

HAYA Hotel Phu Quoc, Trademark Collection by Wyndham xin gửi chị lời nhắc thanh toán cho đặt phòng sau. Đến nay bộ phận kế toán khách sạn chưa nhận được [khoản đặt cọc / khoản thanh toán 50% còn lại]:

Mã đoàn: #[mã đoàn]
Số xác nhận: [số]
Mã đặt phòng: [mã]
Khách đại diện: [tên] ([n] người lớn)
Đại lý du lịch: [đại lý]
Thời gian lưu trú: [DD/MM/YYYY] – [DD/MM/YYYY] ([n] đêm)
Hạng phòng: [phòng]
Tổng tiền: [tổng] VND (đã bao gồm ăn sáng và 8% VAT)
Đã thanh toán: [số tiền] VND
Số tiền cần thanh toán: [số tiền] VND ([50% / 100%])
Hạn thanh toán: [HH:MM] ngày [DD/MM/YYYY] (giờ Việt Nam, UTC+7)

Thông tin tài khoản thanh toán:
Tên tài khoản: CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC
Số tài khoản: 1020729617
Ngân hàng: Vietcombank, CN Phú Quốc

Nội dung chuyển khoản: Tên Công ty + Mã đoàn #[mã đoàn]. Sau khi chuyển khoản, chị vui lòng gửi ủy nhiệm chi (UNC) qua email để khách sạn đối chiếu.

Nếu đã thanh toán, chị vui lòng gửi giúp UNC và bỏ qua email này.

Trân trọng,
Reservations Team
HAYA Hotel Phu Quoc, Trademark Collection by Wyndham
sales@haya-hotels.com
```
English: `Dear Ms. [Name],` / `Greetings from HAYA Hotel Phu Quoc, Trademark Collection by Wyndham.` / `This is a friendly payment reminder for the booking below. Our accounting team has not yet received [the deposit / the remaining 50%]:` then the same lines (Group code, Confirmation number, Agency reference, Guests, Stay, Room, Total, Paid to date, Amount due, Deadline: [HH:MM] on [DD/MM/YYYY], Vietnam time (UTC+7)), bank details, `Please include your company name + group code #[code] in the transfer reference, and email us the payment slip after the transfer so we can verify receipt.` / `If payment has already been made, please send us the slip and disregard this reminder.`
- One reminder per deadline (Monica's default). A second or "final" reminder, and any "the booking will be cancelled if…" line, is Karen's decision: report, don't draft.

### 4b. Payment slip received — to the agency (`--kind reply`)
```
Kính gửi [chị Tên / Phòng Kế toán Đại lý],

HAYA Hotel Phu Quoc, Trademark Collection by Wyndham xin cảm ơn Quý Công ty đã gửi ủy nhiệm chi thanh toán cho booking:

Mã đặt phòng: [mã]
Mã đoàn: #[mã đoàn]
Tên khách: [tên]
Thời gian lưu trú: [DD/MM/YYYY] – [DD/MM/YYYY] ([n] đêm)
Tổng tiền: [tổng] VND
Số tiền trên ủy nhiệm chi: [số tiền] VND ([ngày giờ chuyển])
[Số tiền còn lại: [số tiền] VND, vui lòng thanh toán trước ngày [DD/MM/YYYY] (07 ngày trước ngày nhận phòng).]

Khách sạn đã chuyển ủy nhiệm chi cho bộ phận Kế toán để đối chiếu và sẽ phản hồi khi tiền về tài khoản.

[Thông tin xuất hóa đơn đã được ghi nhận: [công ty] – MST [mã] – [địa chỉ] – hóa đơn gửi [email][; yêu cầu: ghi số booking, xuất ngày check-out …].]

Trân trọng,
Reservations Team
HAYA Hotel Phu Quoc, Trademark Collection by Wyndham
sales@haya-hotels.com
```
English: `Thank you for your email and the payment receipt.` / `We have received your transfer receipt for VND [amount], the [50% deposit / balance] for the booking below. Our accounting team will check that the amount has been credited to our account, and we will confirm once it is reconciled.` + the booking lines + `Deposit received (pending reconciliation): VND [amount]` / `Balance: VND [amount], due 07 days prior to check-in (by [DD/MM/YYYY])`.
- The slip is short of 50%: say the amount on the slip and how much is still due.
- Only after accounting confirmed the money arrived: `Khách sạn xác nhận đã nhận được tiền cọc cho booking sau:` … `Đã nhận cọc 50%: [số tiền] VND (tiền về tài khoản khách sạn ngày [DD/MM/YYYY])`.

### 4c. Slip forwarded to accounting (`draft-forward accountant@palmahotel.vn --kind forward`)
Subject: `Fw: [original subject] – UNC cọc #[mã đoàn]` (or `– UNC thanh toán #[mã đoàn]`).
```
Mã đoàn: #[mã đoàn]

Dear chị, em gửi UNC [đặt cọc / thanh toán] của [Đại lý] cho booking [mã] (mã đoàn #[mã đoàn], conf [số xác nhận]).

Tổng đoàn: [tổng] VNĐ
Cọc 50% theo hợp đồng: [số tiền] VNĐ
Số trên UNC ([ngân hàng], [DD/MM/YYYY HH:MM]): [số tiền] VNĐ — [đủ 50% / thiếu [số tiền] so với 50%]
Số tham chiếu: [số] | Mã GD: [mã]
Nội dung CK: [nội dung]
Tài khoản nhận: 1020729617 Vietcombank

Nhờ chị đối chiếu số tiền vào tài khoản [và xuất hóa đơn VAT theo:
[TÊN CÔNG TY]
MST: [mã]
[Địa chỉ]
Email: [email]]

UNC đính kèm.

Trân trọng,
Reservations team / HAYA Hotel Phu Quoc
sales@haya-hotels.com
```

## 5. Request or update on an existing booking (`--kind request`)
Sources: Booking.com Loo / Voong / Bettiol, Expedia Ho, Agoda 2056156621, Ohmyhotel 28374, RezLive REZ6AD9A3A2, Jain meal 211Q1126Y (13–25/10).

- **Two drafts:** this reply and the forward to front office (`department-forwards.md`). Front office forwarded it in → one draft, the reply, `--to` the writer `--cc haya@haya-hotels.com`.
- **Shape:** greeting · `Thank you for your message.` · [a short booking block when the writer is a desk, an OTA or a group: ref, group code, guest, stay, room] · one sentence or one labelled paragraph per point, in their order · closing line · sign-off.

Guest, English:
```
Dear Ms [Surname],

Thank you for your message.

We have noted your request for [a non-smoking room away from the elevator, with two single beds] for your stay [in a Deluxe Sea View room] from [16] to [19 October 2026]. We will do our best to arrange this for you, subject to availability at check-in.

We look forward to welcoming you.

Best regards,
Reservations Team
HAYA Hotel Phu Quoc, Trademark Collection by Wyndham
sales@haya-hotels.com
```
Desk or OTA team (Agoda, RezLive, Ohmyhotel), English:
```
Dear [Agoda / RezLive Reconfirmation] team,

Thank you for your email regarding [ref]. We have noted the guest's request as follows:

[Agoda booking ID / Supplier confirmation number]: [ref]
Hotel group code: #[code]
Guest(s): [names]
Stay: [DD/MM/YYYY] – [DD/MM/YYYY] ([n] nights), 1 [room], breakfast included
Request: [what they asked]

[The answer, one or two sentences.]

Best regards,
Reservations Team
HAYA Hotel Phu Quoc, Trademark Collection by Wyndham
sales@haya-hotels.com
```
Lines by point (keep only what applies):
- **Arrival time told:** `We have noted your arrival at around [HH:MM] on [DD/MM/YYYY].` If that's after 14:00: `Check-in time is from 14:00, so your room will be ready for you on arrival.` Late at night: `Our hotel staff is available 24/7 to assist you with check-in.`
- **Arrives before 14:00 / asks for early check-in:** `Our standard check-in time is 14:00. We will do our best to have your room ready earlier, subject to availability on the day. If it is not yet ready when you arrive, you are welcome to leave your luggage with us and enjoy the hotel facilities in the meantime.` Never "free of charge" (rule 8): an early check-in charge question → the bands in `hotel-info.md`, or Karen.
- **Room request** (bed, floor, quiet, near each other): `We have noted your request for [ ], subject to availability at check-in.` Bed already in the booked type: say the bed size (`hotel-info.md`). A group in several types: `As the group stays in [n] different room types, we will do our best to place the rooms as close to each other as possible; final allocation is subject to availability at check-in.`
- **Food** (vegetarian, Jain): `Vegetarian options are available at our breakfast. We have noted your [ ] requirements and passed them to our kitchen team.`
- **Baby cot:** `A baby cot will be provided in the room, subject to availability.` ("free of charge" only once Karen confirms the cot is free; `hotel-info.md`.)
- **Transfer:** section 7.
- A fact not in `hotel-info.md` → the best answer I can give, a `[CHECK BEFORE SENDING: …]` first line, and `ask-karen`.

Vietnamese guest: same lines in Vietnamese, `Kính gửi anh/chị [Tên],` / `Cảm ơn anh/chị đã thông tin cho khách sạn.` / `Khách sạn ghi nhận yêu cầu [ ], tùy tình trạng phòng khi nhận phòng.` / `Hân hạnh được đón tiếp anh/chị tại HAYA Hotel Phu Quoc.`

## 6. Tour operators: confirmation, decline (on request)
Sources: Odeon 4609701 (22/10), Pegas 11091234 / 11095509 (23/10), Selfie 14559551 (23/10).

**Odeon confirmation** — a new email (not a reply), subject `Odeon Reservation confirmation [ref]`, to `vietnamreservations@odeontours.com`, cc `vietnamaccounts@odeontours.com`, with the PDF:
```
Dear Odeon Tours Vietnam Reservations Team,

Thank you for your reservation.

We are pleased to confirm the following booking at HAYA Hotel Phu Quoc – Trademark Collection by Wyndham:

Ref: [ref] ([Sunmar / Coral Travel …], voucher [no.])
Guests: [names]
Dates: [DD/MM/YYYY] – [DD/MM/YYYY] ([n] nights)
Room: 1 [room], [n] adults
Meal plan: BB
Hotel confirmation no.: [no.]
Group code: #[code]

Please find attached our confirmation.

Best regards,
Reservations Team
HAYA Hotel Phu Quoc, Trademark Collection by Wyndham
sales@haya-hotels.com
```
Both PDFs go with it: the build tool's confirmation and our proforma invoice (`tour-operators.md` Odeon). `draft-confirmation <voucher email id> <row> <body> --to vietnamreservations@odeontours.com --cc vietnamaccounts@odeontours.com --subject "Odeon Reservation confirmation [ref]" --attach Invoice_[ref].pdf` — it refuses an Odeon row without them.

**Other tour operators' confirmation** — a reply on the operator's email (Anex: to reservation@anexvietnam.com), the same lines as Odeon's with `Dear [Anex Reservation / Pegas / Selfie Travel / Crystal Bay] Team,`, the group code and the EZFOLIO PDF. No deposit or bank block: they pay under their contract. Crystal Bay: our invoice attached too (`--attach`).

**Decline on request** — when `on-request` says REJECT (no availability, or occupancy over 60% with check-in more than 30 days away; dev, 2026-10-29), or Karen has said no. `--kind decline`. Reply on the operator's email (Anex: to reservation@anexvietnam.com); subject `Booking [no.] – Declined (on request)`:
```
Dear [Pegas / Selfie Travel] team,

Thank you for your reservation request[s].

Unfortunately we are unable to accommodate the following on-request booking[s]:

Booking no.: [no.]
Guests: [names]
Room: 1 [room], [n] adults[, BB]
Stay: [DD/MM/YYYY] – [DD/MM/YYYY] ([n] nights)

This booking falls outside our allotment, and we are unable to accept on-request bookings at the moment. Kindly decline [this request / these requests] in your system. We apologise for the inconvenience and look forward to your next booking.

Best regards,
Reservations Team
HAYA Hotel Phu Quoc, Trademark Collection by Wyndham
sales@haya-hotels.com
```
**Odeon decline** — a new email, not a reply (the voucher came through front office), to both Odeon addresses: `draft-new <voucher email id> vietnamreservations@odeontours.com,vietnamaccounts@odeontours.com "Voucher [no.] – Declined (on request)" <body> --kind decline --ref [no.]`:
```
Dear Odeon Tours Vietnam Reservations Team,

Thank you for your reservation request.

Voucher no. [no.] is declined: it falls outside our allotment, and we are unable to accept on-request bookings at the moment.

Guests: [names]
Room: 1 [room], [n] adults, [meal plan]
Stay: [DD/MM/YYYY] – [DD/MM/YYYY] ([n] nights)

Kindly decline this request in your system. We apologise for the inconvenience and look forward to your next booking.

Best regards,
Reservations Team
HAYA Hotel Phu Quoc, Trademark Collection by Wyndham
sales@haya-hotels.com
```
Cancellation of an operator booking: section 3.

## 7. Airport transfer asked for (`--kind request`)
Sources: Agoda 2058164209 (19/10), Klook KOK (16/10), Tushar Malik (25/10).
- **Qualifies for the free one-way transfer** (booking total above USD 250, `hotel-info.md`; Karen when unclear):
  ```
  We are pleased to confirm that we can arrange your complimentary airport pick-up from Phu Quoc International Airport to the hotel:

  Booking reference: [ref]
  Guest name: [name]
  Stay: [DD/MM/YYYY] – [DD/MM/YYYY] ([n] nights), [n] room(s)
  Pick-up date: [DD/MM/YYYY]

  To arrange the driver, could you please reply with:
  – Your flight number and scheduled landing time
  – A WhatsApp number on which our driver can contact you
  – The number of guests travelling

  Our driver will meet you in the arrival hall after you have cleared immigration and collected your baggage.
  ```
- **Doesn't qualify:** `Complimentary one-way airport pick-up applies only when the booking total is above USD 250. Your booking is below that threshold, so pick-up is available as a paid transfer at [price] VND one way.` Price from `hotel-info.md` (200.000 VND, 4-seat car); a larger car's price → Karen until it's in `hotel-info.md`. Then `If you would like us to arrange it, please reply to confirm and send your flight number and landing time.`
- Asking for the flight here is fine: they asked for the transfer.

## 8. Reconfirmation / hotel confirmation number (HCN) request — bedbanks, OTAs, B2B desks (`--kind reply`)
Sources: RezLive (15/10), BiziTrip (19/10), TBO 22541062 (26/10), Within Earth (25/10), Arbitrip (27/10).
Only when the booking is in EZFOLIO (the row has its group code / confirmation number). Not there yet → no draft; report "chờ EZFOLIO". Never "we are checking and will revert".
```
Dear [Rezlive Confirmations / TBO / BiziTrip Booking] Team,

Greetings from HAYA Hotel Phu Quoc, Trademark Collection by Wyndham, and thank you for your email. [We confirm that the following reservation is held in our system as Definite: / Please find the hotel confirmation for the booking below:]

Hotel confirmation number: [no.] (hotel group code #[code])
[Your reference / TBO Booking ID]: [ref]
[Supplier reference]: [ref] ([MG Bedbank / …])
Guest(s): [names] ([nationality])
Stay: [DD/MM/YYYY] – [DD/MM/YYYY] ([n] nights)
Room: 01 [room] – [n] adults
Meal plan: Breakfast included
[Payment: prepaid by the booking agency / covered by the third-party supplier]

[The confirmation number is valid for all nights of the stay.]

We look forward to welcoming the guests.

Best regards,
Reservations Team
HAYA Hotel Phu Quoc, Trademark Collection by Wyndham
sales@haya-hotels.com
```
A guest asking the same (via a booking platform's relay address): `Dear Guest,` / `Thank you for your email. We confirm that your reservation at HAYA Hotel Phu Quoc, Trademark Collection by Wyndham is held in our system as Definite:` + the lines.

## 9. Short replies — decline, "thank you", fully booked (`--kind reply`)
- **They decline our offer:** `Thank you for letting us know.` + `We look forward to welcoming you on [DD/MM/YYYY].` (they still have a booking) or `We hope to welcome you on another occasion.` Don't try to win them back with a price (Karen's).
- **The hotel is full for their dates** (availability sheet: nothing free on some night): `Thank you for your email and your interest in HAYA Hotel Phu Quoc. Unfortunately, the hotel is fully booked for [dates], so we are unable to offer a room for these dates.` / `We hope to welcome your guests on another occasion.` Only when no type is free every night; otherwise offer the type that is (`inquiries-and-quotes.md`).
- **A plain "thank you", "received", "ok"** → no draft, one report line.

---

## What HAYA's sent mail does that Emi does not copy
- Promising something free that isn't written policy ("early check-in … free of charge") — AGENTS.md rule 8.
- Holding replies ("our reservations team is checking … we will send … as soon as possible", "Bộ phận Kinh doanh sẽ gửi … trong thời gian sớm nhất") — rule 9.
- Asking for flight details or arrival time when no transfer was asked for — dev, 2026-10-22.
- A cancel-by time in a reminder ("If payment is not received by 10:00 on …, the booking will be cancelled") — Karen's call.
- The old bank account name "CÔNG TY TNHH MTV DU LỊCH PHUONG NGUYỄN".
- A balance due "48 giờ trước ngày nhận phòng" — the rule is 7 days before check-in.
- Asking a group for details before giving any rate — `inquiries-and-quotes.md` gives rates first (dev, 2026-10-22).
