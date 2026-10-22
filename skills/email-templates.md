# Email templates — new, changed, cancelled, guest requests

Built 2026-10-08 from emails actually sent from sales@haya-hotels.com between 2 and 8 October 2026. Wording is taken from those emails; only the booking details are replaced with [fields]. Source email for each is named so the original can be checked.

## Rules that apply to all of them
- **Formatting, same as HAYA's own sent confirmations:** write `**Label:**` for a bold label and start list lines with `•`. A blank line starts a new paragraph; lines without a blank between them stay together. `draft-reply` and `draft-confirmation` turn this into Outlook HTML (bold, bullet list) — the `**` never reaches the reader. Copy the templates below with their `**` and `•` exactly.
- **Reply on the agency's own thread** (RE: their subject). No new subject line. The reply goes to whoever wrote the email, which is not always who put it in our inbox: see "Who the reply goes to" below.
- **Language (Karen, 2026-10-08):** the language of the email, not the nationality of the agency. Sender wrote in Vietnamese → reply in Vietnamese. Sender wrote in English → reply in English. A Vietnamese agency that writes in English gets English. If a thread mixes both, use the language of the sender's most recent email. Any other language (Chinese, Korean, Russian) → English.
- **Greeting:** Vietnamese "Kính gửi chị/anh [Name]"; if no name is known, "Kính gửi Quý Đối tác". English "Dear Ms./Mr. [Name]," or "Dear [Agency] team,".
- **Greeting a guest (not an agency):** the name as the guest signs the email, else the guest name on the intake row or voucher. Write it exactly as given — never transliterate, translate, shorten, or guess which part is the family name. A From display name alone doesn't count when it isn't in Latin script (e.g. "유정아"). No usable name → "Dear Guest," / "Kính gửi Quý khách,".
- **Never guess anh/chị or Mr./Ms.** Use "chị"/"anh" (Ms./Mr.) only when the thread shows it: a title in the signature ("Ms. Hương"), how the sender writes about themselves, or an earlier HAYA email to the same person. Otherwise "Kính gửi anh/chị [Name]," and "Anh/Chị vui lòng…" for every "Chị vui lòng…" in the template; English "Dear [Name]," with no title.
- **Nationality and words in the email's language:** the sheet stores "Vietnam", "India"; a Vietnamese email writes "Việt Nam", "Ấn Độ".
- **Surcharges in the total:** if any row has a surcharge (child, Indian +20%, 1-night), the Total line names it, as in HAYA's sent confirmation for An0109: "Tổng tiền: 22.040.000 VND, gồm phòng 20.640.000 VND và phụ thu trẻ 4 tuổi 1.400.000 VND; bao gồm ăn sáng, VAT và phí dịch vụ." English: "Total: VND 22,040,000 (rooms VND 20,640,000 + child surcharge VND 1,400,000), including breakfast, VAT and service charge."
- **Bracketed lines are optional:** keep one only when it is true for this booking. The "gửi giúp HAYA danh sách đầy đủ tên khách / tên khách, quốc tịch" ask goes in only when `guest_names` on the row contains TBA or is short of the guest count; with every name given, leave it out.
- **Deadline wording:** Vietnamese "[HH:MM] ngày [DD/MM/YYYY] (giờ Việt Nam, UTC+7)"; English "by [HH:MM] on [DD/MM/YYYY], Vietnam time (UTC+7)". Never mix the two.
- **No operational questions (dev, 2026-10-22, parked in `docs/archive/arrival-and-transfer-asks.md`):** don't ask for arrival time, flight details, or whether the group needs an airport or port pickup, in any draft. If the sender gives these themselves, record them (`arrival_time`, `transfer`) and forward them to front office (`department-forwards.md`) — that forward is still required; only the asking is parked.
- **Dates** DD/MM/YYYY. **Money in Vietnamese** 7.200.000 VND; **in English** VND 7,200,000.
- **Fields come from the intake row and the PDF; hotel facts from `docs/rate-knowledge/hotel-info.md`.** This covers every draft — confirmations, replies, inquiries, requests. **A draft is written only when I have every fact it needs (dev, 2026-10-22).** A field or fact I don't have is never guessed and never left as a `[…: hotel to confirm]` gap for the reviewer: I write no draft for that email, ask Karen with `ask-karen <message_id> "<question>" --ref <ref>`, then `done <message_id> "waiting on Karen E-…"`, and write the draft once `karen-answer` has every answer. The draft commands refuse a text that still has a gap. The intake row is still written; only the reply waits.
- **Never write about what I can or can't see.** The reader is a guest or an agency, not my reviewer. Never: "The luggage-storage policy is not shown in the reservation record currently available to us." Never: "the exact amount cannot be confirmed from the reservation information currently available to us." Nor "we will check and revert", "our records don't show", or any sentence explaining a gap. A missing fact means no draft yet: the question goes to Karen (above).
- **Attach the confirmation PDF** on new and changed bookings.
- **Sign-off (Karen, 2026-10-08):** "Best," then "HAYA Team" on the next line — in English and in Vietnamese emails alike.
- **Total (Karen, 2026-10-08):** always "including breakfast, VAT and service charge" / "bao gồm ăn sáng, VAT và phí dịch vụ". Service charge is already inside every room rate — it is not a separate line item. Never show it as its own line or amount, and never add it on top of a rate.
- **Deposit clock (Karen, 2026-10-08):** 48 hours after the guest or agency receives the booking confirmation from the hotel. Never counted from their booking request.
- **Bank details** (as sent in every confirmation):
  - Tên tài khoản: CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC
  - Số tài khoản: 1020729617
  - Ngân hàng: Vietcombank, CN Phú Quốc

---

## How HAYA writes a reply — everything that isn't a fixed template (dev, 2026-10-22)
Sections 1–4 are fixed forms. Every other reply (a guest's request, an update, an inquiry, a decline, a thank-you) is written fresh, and it must read like HAYA's own sent mail, not like a system log. Rebuilt from the sent emails after the first live run, where the drafts were correct but stiff.

**What HAYA's sent emails do:**
- **Open with one short line of thanks, then go straight to the answer.** "Thank you for your reply." / "Cảm ơn email của team." No restating of their email back to them.
- **Concrete.** Room names, bed sizes, dates, rates, totals, the policy line that applies. A real number beats a sentence about numbers.
- **A request is one clause, not a paragraph:** "HAYA ghi nhận yêu cầu xếp phòng Deluxe ở tầng cao, view đẹp tùy tình trạng phòng." The "subject to availability" goes inside the sentence, never as its own sentence.
- **Answer only what was said or asked.** Someone who tells us their arrival time is not asking about check-in rules or charges.
- **Short.** A request or update reply is 2–5 lines between greeting and sign-off. A quote can be longer because it carries numbers.
- **Warm close in one line,** fitted to the reader: a guest coming → "Have a safe trip, and we look forward to welcoming you."; an agency or reconfirmation desk → "We look forward to welcoming your guests."; a thread that ends → "We hope to welcome you on another occasion." / "Nếu có booking khác, chị cứ liên hệ để HAYA hỗ trợ nhé."
- **English says "we"; Vietnamese says "HAYA"** ("HAYA xin phép gửi…", "HAYA ghi nhận…"). Never "quoted by HAYA" in an English sentence.

**Real examples to copy the tone from** (from sales@ Sent; guest data replaced by [ ]):

1. Vietnamese confirmation opener, to an agency (Re: NEW BOOKING OBT071026MB, 06/10/2026):
   ```
   Dear Team,

   Cảm ơn email của team.

   HAYA xin phép gửi xác nhận đặt phòng như sau:
   ```
2. A room request inside a confirmation, one clause (Re: HAYA Hotel/TBA/11-15.01.2027/An0109, 07/10/2026):
   ```
   HAYA ghi nhận yêu cầu xếp phòng Deluxe ở tầng cao, view đẹp tùy tình trạng phòng.
   ```
3. English quote to a direct guest (RE: [Booking confirmation] Your booking at Haya Hotel Phu Quoc…, 22/10/2026):
   ```
   Dear Mr [Name],

   Thank you for your reply.

   We have noted your request for a quotation for one additional room, over and above your two King Suites with Sea View already booked.
   We are pleased to quote as follows:
   Rate: 3,600,000 VND per night for 3 adults, breakfast and VAT included
   Total for 2 nights (18/11/2026 – 20/11/2026): 7,200,000 VND
   Full payment is required before check-in.
   ```
4. Closing a thread that ends (cancellation, Amara Tours, 03/10/2026): "Cảm ơn chị và [tên đại lý] đã nghĩ đến HAYA. Nếu có booking khác trong thời gian tới, chị cứ liên hệ để HAYA hỗ trợ nhé."

**Sounds like a robot — never write** (all from drafts of the 2026-10-22 live run):
- "Thank you for your email about your stay from [date] to [date]." → "Thank you for your email." / "Thank you for letting us know."
- "Check-in is from 14:00, so an evening arrival is a normal check-in with no extra charge." → say nothing about check-in rules; "our front office will be expecting you."
- "…and will pass it to our front office." after every point → once at most, or "our front office will be expecting you".
- "This is subject to availability." as its own sentence → ", subject to availability" inside the sentence.
- "We have noted that you are not proceeding with the additional room quoted by HAYA." → "Thank you for letting us know."
- "Please send the exact check-in and check-out dates… so HAYA can prepare the suitable room proposal and applicable rates." → give the rates for the period now, then ask for the dates to hold (`inquiries-and-quotes.md`, group and vague-date enquiries).
- "We look forward to welcoming you." to a reservation desk or reconfirmation team → "…welcoming your guests."
- "Please be informed that", "We would like to inform you", "Kindly note", "Greetings from HAYA" → not in HAYA's mail. Just say the thing.
- Every blind-spot sentence ("not shown in the information available to us", "cannot be confirmed from the reservation record", "we will check and revert") → no draft; the missing fact goes to Karen with `ask-karen`.

## Who the reply goes to (dev, 2026-10-22)
A reply goes to the person who wrote the email, not to whoever put it in our inbox.

- **Forwarded in by our own staff.** Sender `@haya-hotels.com` or `@palmahotel.vn` (usually front office, `haya@haya-hotels.com`) and the email is a forward ("Fw:", and a quoted block `From: … Sent: … To: … Subject: …`). The writer is the **From:** of that quoted block: the first external address, reading from the top. `draft-reply` refuses to answer an internal sender for this reason: on 2026-10-22 two replies meant for RezLive and a guest went to haya@.
  1. **Look for the original first:** `mail-find <the writer's address or the original subject>`. If the original is also in sales@ (they wrote to sales@ or cc'd it), reply on that one, normally, and mark the forward `done` as a duplicate.
  2. **Otherwise reply on the forward with the writer's address:**
     `draft-reply <forward id> <body> --kind <kind> --to <writer's address> --cc <the colleague who forwarded it>`
     The draft goes To the writer, Cc our colleague, subject `RE: <their original subject>` without the "Fw:". The cc is how the colleague sees our answer, and it replaces any forward back to them (`department-forwards.md`).
  3. **No usable address** (forwarded as an attachment, no quoted header, or the writer is a no-reply robot such as an OTA or `vn.robot@`): no reply. It goes in the scan report.
  - Never `--internal` to get past the refusal for a guest or agency. `--internal` is only for a real answer to a colleague, `--kind reply`.
- **Confirmation on a booking request that was forwarded in:** `draft-confirmation <id> <row> <body> --to <the agency's address> --cc <colleague>`, same reason. The agency's address is the quoted From:, which is also what the row's `company_email` should hold, never haya@.
- **Reply-all (`--all`)** only when the sender cc'd their own colleagues (agency managers, accounts). With `--to`, list everyone yourself; `--all` and `--to` don't mix.

---

## 1. New booking — Vietnamese
**Status: APPROVED by Karen, 2026-10-08.** Use as written. Don't reword, reorder, or drop sections. (She approved the English form; this is the same form in Vietnamese, word for word from a sent confirmation.)

Source: "RE: 0327-IN1205 || HAYA HOTEL", sent 07/10/2026.

```
Kính gửi chị [Tên],

HAYA Hotel Phu Quoc, Trademark Collection by Wyndham xin chân thành cảm ơn Quý Đối tác đã lựa chọn khách sạn.

Vui lòng xem thông tin xác nhận đặt phòng và PDF đính kèm như sau:

**Mã đoàn:** #[mã đoàn]
**Số xác nhận:** [số xác nhận]
**Mã đặt phòng:** [mã của đại lý]
**Tên đoàn:** [tên đoàn / khách chính]
**Đại lý du lịch:** [tên đại lý]

**Thời gian lưu trú:** [DD/MM/YYYY] – [DD/MM/YYYY] ([n] đêm)
**Hạng phòng:** [số phòng] [hạng phòng]
**Số lượng khách:** [n] người lớn[, n trẻ em (tuổi)], quốc tịch [quốc tịch].
**Đơn giá:** [giá] VND/phòng/đêm.
**Tổng tiền:** [tổng] VND, bao gồm ăn sáng, VAT và phí dịch vụ.

**Điều khoản thanh toán:**

• Đặt cọc 50% ([số tiền] VND); hạn giữ phòng [HH:MM] ngày [DD/MM/YYYY] (giờ Việt Nam, UTC+7), 48 giờ sau khi khách nhận được xác nhận.
• 50% còn lại ([số tiền] VND) vui lòng thanh toán trước 07 ngày so với ngày nhận phòng.
Đặt phòng sẽ được tự động hủy mà không cần thông báo trước nếu khách sạn không nhận được khoản đặt cọc đúng hạn.

**Thông tin xuất hóa đơn VAT:**

[HAYA đã ghi nhận thông tin xuất hóa đơn theo yêu cầu. / Chị vui lòng bổ sung tên pháp lý công ty, mã số thuế, địa chỉ và email nhận hóa đơn.]

**Thông tin tài khoản thanh toán:**

**Tên tài khoản:** CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC
**Số tài khoản:** 1020729617
**Ngân hàng:** Vietcombank, CN Phú Quốc

**Lưu ý:**

• Vui lòng ghi rõ Tên Công ty + Mã đoàn (#[mã đoàn]) trong nội dung chuyển khoản.
• Trường hợp nội dung chuyển khoản không đầy đủ hoặc không chính xác, khách sạn có thể chưa ghi nhận thanh toán cho đến khi hoàn tất đối chiếu.
• Sau khi chuyển khoản, vui lòng gửi ủy nhiệm chi hoặc biên lai qua email để khách sạn kiểm tra và xác nhận.
[Chị vui lòng xem PDF đính kèm và gửi giúp HAYA danh sách đầy đủ tên khách khi có.]

Xin chân thành cảm ơn sự hợp tác của Quý Đối tác và hân hạnh được đón tiếp Quý khách tại HAYA Hotel Phu Quoc, Trademark Collection by Wyndham.

Best,
HAYA Team
```

## 1. New booking — English
**Status: APPROVED by Karen, 2026-10-08.** Use as written. Don't reword, reorder, or drop sections.

Source: "RE: NEW RESERVATION(S): 2775717", sent 07/10/2026.

```
Dear Ms. [Name],

Thank you for choosing HAYA Hotel Phu Quoc, Trademark Collection by Wyndham.

Please find the booking confirmation below and the attached PDF:

**Group code:** #[group code]
**Confirmation number:** [confirmation no.]
**Agency reference:** [agency ref]
**Group name:** [group name / lead guest]
**Travel agency:** [agency]

**Stay:** [DD/MM/YYYY] – [DD/MM/YYYY] ([n] nights)
**Room:** [number] [room type]
**Guests:** [n] adults[ + n children aged x and y], [nationality]
**Rate:** VND [rate] per room per night
**Total:** VND [total], including breakfast, VAT and service charge.

**Payment terms:**

  * 50% deposit (VND [amount]) within 48 hours of receiving this confirmation: by [HH:MM] on [DD/MM/YYYY], Vietnam time (UTC+7).
  * The remaining 50% (VND [amount]) is payable 7 days before check-in.

The booking will be automatically released without further notice if the deposit is not received by the deadline.

**VAT invoice details:**

[We have noted the invoice details provided. / Please send your company's legal name, tax code, address and invoice email address if a VAT invoice is required.]

**Bank details:**

**Account name:** CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC
**Account number:** 1020729617
**Bank:** Vietcombank, Phu Quoc Branch

**Notes:**

  * Please include your company name + group code #[group code] in the transfer reference.
  * Incomplete or incorrect references may delay payment reconciliation.
  * Please email the payment slip after the transfer so we can verify receipt.

Thank you for your cooperation. We look forward to welcoming your guests.

Best,
HAYA Team
```

---

## 2. Changed booking — deposit check first (Karen, 2026-10-08)
Before drafting, look up the booking in the intake sheet (Payment 1 and its date) and check the thread for a payment slip.

- **No deposit received yet** → use payment block A: remind them to pay the deposit to the hotel's bank account within 48 hours of receiving this email, with the exact deadline (time, date, Vietnam time) and the bank details.
- **Deposit already received** → use payment block B: no reminder, existing terms continue.
- **Can't tell** (row missing, Payment 1 blank but a slip is in the thread, amounts don't match) → don't pick one. Flag it to Karen in the scan report.

## 2. Changed booking — Vietnamese
**Status: updated with Karen's deposit rule, 2026-10-08.**

Sources: "RE: VICTORIA DMC ĐẶT PHÒNG HAYA HOTEL - NPKM00210000088 - 28/10" (07/10/2026) for the layout; "RE: URGENT - AMEND - Booking code AAT261116.553" (02/10/2026) for the "what changed" paragraph.

```
Kính gửi chị [Tên],

HAYA xin gửi xác nhận điều chỉnh đặt phòng theo yêu cầu của chị:

**Mã đoàn:** #[mã đoàn]
**Số xác nhận:** [số xác nhận]
**Tên đoàn:** [tên đoàn]
**Đại lý du lịch:** [tên đại lý]

**Thời gian lưu trú:** [DD/MM/YYYY] – [DD/MM/YYYY] ([n] đêm)
**Hạng phòng:** [số phòng + hạng phòng]
**Số lượng khách:** [n] người lớn[, n trẻ em]
**Đơn giá:** [giá] VND/phòng/đêm
**Tổng tiền:** [tổng] VND, bao gồm ăn sáng, VAT và phí dịch vụ.

**Nội dung điều chỉnh:** [cũ → mới, một hoặc hai câu. Ví dụ: HAYA đã thay 1 Standard và 1 Superior bằng 2 Deluxe Seaview, giữ mức giá tương ứng.]

**Điều khoản thanh toán:**

[KHỐI A — chưa nhận được tiền cọc]
• HAYA chưa nhận được khoản đặt cọc cho booking này. Chị vui lòng chuyển khoản đặt cọc 50% ([số tiền] VND) vào tài khoản khách sạn trong vòng 48 giờ kể từ khi nhận được email này: trước [HH:MM] ngày [DD/MM/YYYY] (giờ Việt Nam, UTC+7).
• 50% còn lại ([số tiền] VND) vui lòng thanh toán trước 07 ngày so với ngày nhận phòng.
Đặt phòng sẽ được tự động hủy mà không cần thông báo trước nếu khách sạn không nhận được khoản đặt cọc đúng hạn.

[KHỐI B — đã nhận tiền cọc]
HAYA đã nhận khoản đặt cọc [số tiền] VND ngày [DD/MM/YYYY]. Số tiền còn lại sau điều chỉnh: [số tiền] VND, vui lòng thanh toán trước 07 ngày so với ngày nhận phòng.

**Thông tin xuất hóa đơn VAT:** [Đã được ghi nhận theo yêu cầu. / Chị vui lòng gửi thông tin xuất hóa đơn nếu cần.]

**Thông tin tài khoản thanh toán:**
CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC
1020729617 – Vietcombank, CN Phú Quốc

**Lưu ý:** Chị vui lòng xem PDF điều chỉnh đính kèm[ và gửi giúp HAYA tên khách, quốc tịch khi có]. Nội dung chuyển khoản vui lòng ghi Tên Công ty + Mã đoàn #[mã đoàn].

Best,
HAYA Team
```

## 2. Changed booking — English
**Status: updated with Karen's deposit rule, 2026-10-08.** No English change confirmation was found in the Sent folder for this period. This is a translation of the Vietnamese one above, not a copy of something already sent.

```
Dear Ms. [Name],

Please find the revised booking confirmation as requested:

**Group code:** #[group code]
**Confirmation number:** [confirmation no.]
**Group name:** [group name]
**Travel agency:** [agency]

**Stay:** [DD/MM/YYYY] – [DD/MM/YYYY] ([n] nights)
**Room:** [number + room type]
**Guests:** [n] adults[ + n children]
**Rate:** VND [rate] per room per night
**Total:** VND [total], including breakfast, VAT and service charge.

**What changed:** [old → new, one or two sentences.]

**Payment terms:**

[BLOCK A — no deposit received yet]
  * We have not yet received the deposit for this booking. Please transfer the 50% deposit (VND [amount]) to the hotel's bank account within 48 hours of receiving this email: by [HH:MM] on [DD/MM/YYYY], Vietnam time (UTC+7).
  * The remaining 50% (VND [amount]) is payable 7 days before check-in.
The booking will be automatically released without further notice if the deposit is not received by the deadline.

[BLOCK B — deposit already received]
We have received your deposit of VND [amount] on [DD/MM/YYYY]. The remaining balance after this change is VND [amount], payable 7 days before check-in.

**VAT invoice details:** [Noted as requested. / Please send invoice details if required.]

**Bank details:**
CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC
1020729617 – Vietcombank, Phu Quoc Branch

Please see the revised PDF attached. It replaces the earlier confirmation. Please include your company name + group code #[group code] in the transfer reference.

Best,
HAYA Team
```

---

## 3. Cancelled booking — Vietnamese
**Status: APPROVED by Karen, 2026-10-08.** Use as written. (She approved the English form; this is the same form in Vietnamese, from a sent email.)

Source: "RE: AMARA TOURS - HAYA HOTEL PHUQUOC - KL TRAVEL", sent 03/10/2026.

```
Kính gửi chị [Tên],

HAYA đã nhận yêu cầu hủy booking [mã đặt phòng] ngày [DD/MM/YYYY]–[DD/MM/YYYY] (mã đoàn #[mã đoàn]) và xác nhận đã hủy đặt phòng này trên hệ thống[, không tính phí / phí hủy: … VND].

Cảm ơn chị và [tên đại lý] đã nghĩ đến HAYA. Nếu có booking khác trong thời gian tới, chị cứ liên hệ để HAYA hỗ trợ nhé.

Best,
HAYA Team
```

## 3. Cancelled booking — English
**Status: APPROVED by Karen, 2026-10-08.** Use as written.

Source: "Re: Hold/MVN31006/RIKIN ASHOKBHAI KOTADIA/Haya Hotel Phu Quoc Island", sent 07/10/2026.

```
Dear [Agency] team,

Thank you for your email. We confirm that booking [agency ref] for [lead guest] at HAYA Hotel Phu Quoc (group code #[group code]) has been cancelled [without charge / with a cancellation charge of VND …].

We hope to welcome your guests on another occasion.

Best,
HAYA Team
```

---

## 4. Payment reminders (Karen, 2026-10-08)
**Status: written by Monica from Karen's instruction and two sent emails (Eagle Crest, 07/10/2026; Absolute Asia, 03/10/2026). Not yet approved by Karen.** Reply on the booking's thread.

### 4a. Deposit reminder — at 40 hours, no deposit seen

Vietnamese:
```
Kính gửi chị [Tên],

HAYA chưa nhận được khoản đặt cọc cho booking [mã đặt phòng] (mã đoàn #[mã đoàn]), lưu trú [DD/MM/YYYY] – [DD/MM/YYYY].

Hạn đặt cọc 50% ([số tiền] VND) là [HH:MM] ngày [DD/MM/YYYY] (giờ Việt Nam, UTC+7). Chị vui lòng gửi ủy nhiệm chi qua email sau khi chuyển khoản để kế toán khách sạn kiểm tra. Nếu chị đã chuyển khoản, chị gửi giúp HAYA ủy nhiệm chi nhé.

Đặt phòng sẽ được tự động hủy nếu khách sạn không nhận được khoản đặt cọc đúng hạn.

**Thông tin tài khoản thanh toán:**
CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC
1020729617 – Vietcombank, CN Phú Quốc
**Nội dung chuyển khoản:** Tên Công ty + Mã đoàn #[mã đoàn]

Best,
HAYA Team
```

English:
```
Dear Ms. [Name],

We have not yet received the deposit for booking [agency ref] (group code #[group code]), [DD/MM/YYYY] – [DD/MM/YYYY].

The 50% deposit of VND [amount] is due by [HH:MM] on [DD/MM/YYYY], Vietnam time (UTC+7). Can you please send us the payment slip after the transfer so that our accountant can check? If you have already made the transfer, please send us the slip.

The booking will be automatically released if the deposit is not received by the deadline.

**Bank details:**
CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC
1020729617 – Vietcombank, Phu Quoc Branch
**Transfer reference:** company name + group code #[group code]

Best,
HAYA Team
```

### 4b. Balance reminder — the day before it's due (8 days before check-in), no balance seen

Vietnamese:
```
Kính gửi chị [Tên],

HAYA chưa nhận được khoản thanh toán 50% còn lại cho booking [mã đặt phòng] (mã đoàn #[mã đoàn]), nhận phòng ngày [DD/MM/YYYY].

Số tiền còn lại [số tiền] VND cần được thanh toán trước ngày [DD/MM/YYYY], 07 ngày trước ngày nhận phòng. Chị vui lòng gửi ủy nhiệm chi qua email sau khi chuyển khoản để kế toán khách sạn kiểm tra. Nếu chị đã chuyển khoản, chị gửi giúp HAYA ủy nhiệm chi nhé.

**Thông tin tài khoản thanh toán:**
CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC
1020729617 – Vietcombank, CN Phú Quốc
**Nội dung chuyển khoản:** Tên Công ty + Mã đoàn #[mã đoàn]

Best,
HAYA Team
```

English:
```
Dear Ms. [Name],

We have not yet received the remaining 50% for booking [agency ref] (group code #[group code]), check-in [DD/MM/YYYY].

The balance of VND [amount] is due by [DD/MM/YYYY], 7 days before check-in. Can you please send us the payment slip after the transfer so that our accountant can check? If you have already made the transfer, please send us the slip.

**Bank details:**
CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC
1020729617 – Vietcombank, Phu Quoc Branch
**Transfer reference:** company name + group code #[group code]

Best,
HAYA Team
```

---

## 5. Guest request or update on an existing booking — `--kind request` (dev, 2026-10-22)
**Status: rewritten 2026-10-22 from HAYA's sent emails after the first live run. Not yet approved by Karen.** For a guest or agency who tells us or asks us something about a booking they already have: arrival time, bed type, same floor, connecting rooms, early check-in / late check-out, luggage, transfer. Not price or availability with no booking yet (that's `inquiries-and-quotes.md`, `--kind inquiry`). Write it the way "How HAYA writes a reply" above says.

- **Two drafts:** this reply (`draft-reply <id> <file> --kind request --ref <ref>`) and the forward to front office (`department-forwards.md`), also when the ref isn't on the intake sheet yet. If the reply needs a fact I don't have, the forward is still drafted now and the reply waits for Karen's answer (rules for all, above). **Exception:** front office forwarded the email to us. Then it's one draft, the reply, to the original writer with front office in cc (see "Who the reply goes to"), and no forward back.
- **Shape:** greeting, one line of thanks, one short paragraph answering their points in their order, one closing line, "Best, / HAYA Team".
- **Arrival time, any hour:** "We have noted your arrival at around [HH:MM] on [DD/MM/YYYY], and our front office will be expecting you." That's all. No check-in rules, no "no extra charge", no "normal check-in". Check-in times come up only if they ask to check in before 14:00. (Whether the desk is staffed 24 hours is still unknown: `hotel-info.md`. Don't claim it, and don't raise it.)
- **Room requests** (bed type, same floor, connecting, high floor, quiet room): one clause, "noted, subject to availability" / "HAYA ghi nhận … tùy tình trạng phòng". When the booked room already has what they ask for, say so with the bed size from `hotel-info.md`, for example "the Deluxe Double Seaview has one 1.8 m bed" for a king-size bed request.
- **Early check-in / late check-out, when asked:** the bands from `hotel-info.md`. What the % is of is not known yet (`hotel-info.md`, "Chưa biết"): ask Karen before the reply. Never a free one.
- **Free late check-out, upgrade, waived charge** → money ask, Karen (AGENTS.md rule 8). The reply gives the charges as they are.
- **Pickup:** they said they'll take a taxi, or they don't need one → nothing to answer. They ask → the price from `hotel-info.md`; not there (direct and OTA guests) → ask Karen.
- A fact not in `hotel-info.md` → no reply yet: `ask-karen`, and the scan report names the question.

English:
```
Dear [Name / Guest],

Thank you for [your email / letting us know].

[Their points, in their order, in one short paragraph — keep only what applies:
We have noted your arrival at around [HH:MM] on [DD/MM/YYYY], and our front office will be expecting you.
We have noted your request for [two rooms on the same floor], subject to availability.
The [room type] has one [1.8 m] bed[, so the king-size bed is already in place].
Check-out is at 12:00. Late check-out is subject to availability and charged at [25% / 50% / 100% of <the basis Karen gave>] — 25% until 15:00, 50% until 18:00, 100% after 18:00.
[Luggage storage, as Karen answered.]]

[Have a safe trip, and we look forward to welcoming you. / We look forward to welcoming your guests.]

Best,
HAYA Team
```

Vietnamese:
```
Kính gửi anh/chị [Tên] / Quý khách,

Cảm ơn anh/chị đã báo cho HAYA.

[Giữ dòng nào đúng, theo thứ tự khách hỏi:
HAYA đã ghi nhận anh/chị đến khoảng [HH:MM] ngày [DD/MM/YYYY], lễ tân sẽ chờ đón anh/chị.
HAYA ghi nhận yêu cầu [xếp 2 phòng cùng tầng] tùy tình trạng phòng.
Phòng [hạng phòng] có 1 giường [1m8].
Giờ trả phòng là 12:00. Trả phòng muộn tùy tình trạng phòng, phụ thu [25% / 50% / 100% của <mức Karen đã trả lời>]: 25% đến 15:00, 50% đến 18:00, 100% sau 18:00.
[Gửi hành lý, theo câu trả lời của Karen.]]

[Chúc anh/chị chuyến đi thuận lợi, hẹn gặp anh/chị tại HAYA. / Hân hạnh được đón tiếp khách của anh/chị.]

Best,
HAYA Team
```

**How the live-run drafts should have read** (2026-10-22; guest names replaced, refs shortened):

A Trip.com guest (from a `@guest.trip.com` relay address, which is fine to reply to) says they land at 23:35 on 01/11 and will take a taxi:
```
Dear Minjun Park,

Thank you for letting us know. We have noted your arrival at around 23:35 on 01/11/2026, and our front office will be expecting you.

Have a safe trip, and we look forward to welcoming you to Phu Quoc.

Best,
HAYA Team
```
(A From name written in capitals, "MINJUN PARK", may be written in normal capitals. Never reorder or shorten it, and never guess Mr./Ms.)

RezLive's reconfirmation team asks for a king-size bed in a Deluxe Double, 08–11/11/2026. Front office forwarded it in, so this goes `--to ssr@rezlive.com --cc haya@haya-hotels.com`, with no separate forward:
```
Dear Reconfirmation Team,

Thank you for your email. The Deluxe Double Seaview booked for Mr. [Guest] and Ms. [Guest] (08/11/2026 – 11/11/2026, confirmation [AGIN…]) has one 1.8 m bed, so the king-size bed request is noted and our front office has it.

We look forward to welcoming your guests.

Best,
HAYA Team
```

---

## 6. Short replies: a decline, a "thank you", a "noted" (dev, 2026-10-22)
**Status: default written 2026-10-22 from the sent emails, not yet approved by Karen.** `--kind reply`.

- **They decline an offer or quote** ("Not interested, booked elsewhere"): **reply, in one or two lines.** HAYA closes threads warmly (both approved cancellation templates end on a goodwill line). Thank them, then:
  - they still have a booking with us → look forward to welcoming them on the arrival date;
  - they don't → "We hope to welcome you on another occasion."
  Don't repeat what they declined and don't try to win them back with a better price (that's a money decision, Karen's).
  If they say they booked "the same days through Booking.com" (or another OTA), it may be a booking at HAYA: the scan report says to watch for a matching OTA booking.
- **A plain "thank you", "received", "ok"** with nothing to answer or record → no draft. One line in the scan report: "không cần trả lời".

The decline from the live run (a direct guest who still has two suites booked for 18–20/11/2026; haya@ forwarded it in, but the guest had also written to sales@, so the reply goes on that original):
```
Dear Mr [Name],

Thank you for letting us know. We look forward to welcoming you on 18/11/2026.

Best,
HAYA Team
```
Vietnamese: "Cảm ơn anh/chị đã báo cho HAYA. Hẹn gặp anh/chị ngày [DD/MM/YYYY]." / "Hy vọng sẽ được đón tiếp anh/chị vào dịp khác."

---

## Also found in the Sent folder — same formats Emi follows

**Payment slip forward to accounting** (e.g. "Fw: AVD - 4246445", 08/10/2026): forward the agency's email to accountant@palmahotel.vn with one line on top:
```
**Mã đoàn:** #[mã đoàn]
```
When the slip needs explaining (e.g. "FW: RHK130126", 07/10/2026): one sentence with amount, date received, group code, and anything unusual such as the transfer coming from a different company's account.

**Payment received, to the agency** (e.g. "Re: Booking Code 111W1126P", 07/10/2026):
```
Dear chị [Tên],

HAYA Hotel Phu Quoc xác nhận đã nhận được [khoản tiền cọc / thanh toán] [số tiền] VND [ngày DD/MM/YYYY] cho booking [mã đặt phòng] (mã đoàn #[mã đoàn]). [Booking đã được thanh toán đủ. / Bộ phận kế toán sẽ ghi nhận vào hệ thống.]

Cảm ơn chị và [tên đại lý] đã hợp tác.
```
I draft this only once accounting has confirmed the money arrived. A slip is not proof of receipt.

## Not covered
- **Direct guests.** The one example (Mr. Hindol Roy, 07/10/2026) is written personally, signed "Karen Nguyen", and uses different terms: full payment before the free-cancellation date, 7 days before check-in. One example is not a template. Direct-guest confirmations go to Karen as a one-off draft.
- **Anex Tour.** Their confirmations follow the same layout but the rate lines carry contract discounts (early bird, SPO, stay 10 pay 9). The calculation comes from the intake row's notes, never worked out by me in the email.
