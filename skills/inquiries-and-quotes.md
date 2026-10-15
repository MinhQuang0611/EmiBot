# Inquiries and quotes — by email

Taken over from Sunny on 2026-10-08 for email only. Sunny still answers on Zalo and WhatsApp, and the rules below are the same ones Karen set for her (config review, 2026-10-03), so an agency gets the same answer on either channel.

## Availability and rates — where they come from
- The **"FUTURE AVAILABILITY"** folder on Google Drive: the daily future availability file and the price PDF. Always use the newest file. Never save a fixed file ID.
- If the newest file looks stale or won't open: wait 2 minutes, retry, up to 3 times, then take it to Karen. Don't answer from an old file as if it were current.
- Direct-guest and walk-in rates haven't been provided yet. A direct guest asking for a price goes to Karen.

## What to offer
- The **cheapest room type available** for the full period, unless the client names a room type.
- **One allocation**, matching the number of rooms asked for. If one type can't cover the whole request, offer a combination (e.g. 1 Standard + 5 Superior Double).
- Give only the number of rooms they asked about. Don't tell an agency how many rooms are left — except when it's the last one: "còn 1 phòng".
- **Stop-sale:** if a date is over 50% occupancy and check-in is more than 14 days away, don't offer it. Say the hotel is not accepting bookings for that date. Never say "sold out" when it isn't.
- Extra bed requested → offer a Triple. Triple unavailable → Quadruple.
- Capacity: Triple = 3 people + 1 child under 12. Quadruple = 4 + 1 child under 12. Every other type = 2 + 1 child under 12.
- Children: 0–2.99 free. 3.00–11.99 charged when sharing the parents' bed. 12 and over counts as an adult.
- TW-DLX and APT: never to agencies. TW-DLX may be offered to direct guests.
- Rates by sender type (`channel_type` rule in `booking-intake.md`), files in `docs/RATE TABLES/` (dev, 2026-10-09):

  | Sender | Rate file |
  |---|---|
  | TA (travel agency) | `BẢNG GIÁ CHO TA HAYA HOTEL.pdf`, same rules as in `booking-intake.md` |
  | Anex | `Haya - Anex 2026 - 2027.pdf` |
  | Crystal Bay | `Haya - Crystal Bay 2026-2027.pdf` |
  | Odeon | `Haya - Odeon 2026-2027.pdf` |
  | Pegas | `W26 S27  Season 26 - 27 - (Haya Hotel - Pegas).pdf` |
  | Selfie | `SELFIE - HAYA 2026 - 2027.pdf` |
  | Fun and Sun | **No contract this season.** No rate to quote: flag to Karen, don't quote from the TA table. |

  A tour operator is quoted from its own contract, never from the TA table. A tour operator with no file here goes to Karen.

- **Read the transcribed version, not the PDF:** `docs/rate-knowledge/<name>.md` (one per row above, index and offer comparison in `docs/rate-knowledge/README.md`). Three of the PDFs are scans with no text layer; these files are the readable copy. If a figure looks wrong, check the PDF page — the PDF wins.

## Working out the numbers — the `quote` command (TA senders)
Never price a stay by hand. Run, from `/data/emi`:
```
.venv/bin/python -m tools.emi quote --arrival DD/MM/YYYY --departure DD/MM/YYYY --adults N --children "13;5;2"
```
- `--children`: every child's age; 12 and over is counted as an adult by the command. Age not given → ask for it in the reply, don't guess.
- The sender said how to split the rooms ("3 rooms for 2 adults, 1 room 2 adults + extra bed") → price exactly that: `--alloc "STD:3,TPL:1"` (extra bed = Triple). They gave a room count only → `--rooms N`. They named a type → `--room-type DLX-SV`. Two separate beds → `--twin`. Indian guests → `--indian`.
- Nothing said about rooms → the command lists options (cheapest, fewest rooms, only doubles, sea-view upgrade). Offer **one** allocation — the cheapest unless the guests' make-up says otherwise (4 adult friends ≠ one Quadruple; a family of 4 = Quadruple) — and at most one alternative line.
- Every number in the reply (rates, surcharges, total, deposit) is copied from the command's output.
- `GAP:` lines are things the data can't answer. Availability is always one (not connected yet): the draft is still written, and the scan report lists it as "check availability before sending". A 2027-holiday gap → the night's rate goes to Karen, not into the reply.
- Not a TA sender → the command says where to look (tour operator contract file, or Karen for OTA/direct).

## Reply to an inquiry — template (draft wording, not yet approved by Karen)
Same rules as `email-templates.md` (anh/chị unless the thread shows it, `**Label:**`, `•` lists, "Best, / HAYA Team", sender's language). Drop any line that doesn't apply.
```
Kính gửi anh/chị [Tên],

HAYA Hotel Phu Quoc, Trademark Collection by Wyndham xin cảm ơn anh/chị đã quan tâm đến khách sạn.

Với yêu cầu [n người lớn, n trẻ em (tuổi)] từ [DD/MM/YYYY] đến [DD/MM/YYYY] ([n] đêm), HAYA xin gửi phương án như sau:

**Hạng phòng:** [n] [hạng phòng][ + n hạng phòng]
**Gợi ý:** [một câu vì sao chọn cách xếp này, từ giường và sức chứa trong output, ví dụ: Phòng Quadruple (2 giường 1m8) ở được 4 người lớn và 1 bé dưới 12 tuổi, phòng Standard Double (giường 1m6) cho 2 người lớn và bé còn lại, nên cả nhà chỉ cần 2 phòng.]
**Đơn giá:** [giá] VND/phòng/đêm ([hạng phòng])[; …]
**Phụ thu trẻ em:** [bé [tuổi] tuổi ngủ chung giường: [giá] VND/đêm × [n] đêm = [số tiền] VND][; bé dưới 3 tuổi miễn phí]
**Phụ thu ở 1 đêm:** [[giá] VND/khách × [n] khách = [số tiền] VND — chỉ khi ở 1 đêm]
**Tổng tiền:** [tổng] VND cho [n] đêm, bao gồm ăn sáng, VAT và phí dịch vụ.
[**Phương án khác:** [một dòng, ví dụ nâng lên Deluxe Double Seaview: tổng [tổng] VND]]

**Bao gồm:** ăn sáng (06:30–10:30), hồ bơi, phòng gym, wifi.
**Nhận phòng / trả phòng:** sau 14:00 / trước 12:00.

**Điều khoản thanh toán:**

• Đặt cọc 50% trong vòng 48 giờ sau khi nhận được xác nhận đặt phòng.
• 50% còn lại vui lòng thanh toán trước 07 ngày so với ngày nhận phòng.

[Trả lời từng câu hỏi khác trong email: đưa đón (giá từ ta.md, không miễn phí), nâng hạng / miễn phí (không có trên bảng giá — nói lý do thật), chính sách hủy, trẻ em…]

Để giữ phòng, anh/chị vui lòng gửi giúp HAYA: tên khách, ngày ở, hạng phòng, số người lớn và trẻ em, quốc tịch và yêu cầu đặc biệt (nếu có).

Best,
HAYA Team
```
English: same blocks — "Thank you for your interest in HAYA Hotel Phu Quoc, Trademark Collection by Wyndham.", **Room / Rate / Surcharge / Total / Alternative / Included / Check-in / check-out / Payment terms**, "To hold the rooms, please send the guest names, stay dates, room type, number of adults and children, nationality and any special requests."

## Questions about offers, children, cancellation, payment
Answer from the sender's own file in `docs/rate-knowledge/`. Example: "do we get anything for booking early or for a big group?"
- Give what the file has, with its conditions: the early-bird tiers and dates, the long-stay offer, whether they combine, what they don't apply to (meals, extra bed, child surcharge).
- Say plainly what it doesn't have. None of the tour operator contracts has a group-size discount; the TA table has none except ROH (>15 double/twin rooms at the Standard Double rate) and no early bird or long-stay offer.
- Never quote one party's contract terms to another, and never compare them ("another agency gets…"). Every contract is confidential.
- A figure marked ⚠ in the file is a misprint or open point: don't quote it until Karen confirms.
- Anything beyond the file (a bigger discount, a group rate, an exception) is a request to Karen, flagged as needing her parents' sign-off. No holding reply to the sender — answer what the file covers, and list the open ask in the scan report.

## To hold a booking
After giving availability and price, state that to hold the booking the client needs to send full details: guest names, stay dates, room type, number of adults and children, nationality, and any special requests. In Vietnamese: "tên khách, ngày ở, hạng phòng, số người lớn và trẻ em, quốc tịch và yêu cầu đặc biệt (nếu có)".

Payment terms to state: 50% deposit within 48 hours of receiving the confirmation, remaining 50% 7 days before check-in.

When those details arrive, the email becomes a NEW booking → `booking-intake.md`.

## Money asks
Discount, upgrade, waived fee, free extra: acknowledge, give the real reason it isn't offered on this rate, offer what is available at its price. Never yes, never "let me see what I can do." If it's something Karen might grant, it goes to her as a request.

## Replies
- Every reply, including a plain greeting, is saved to Drafts for a person to send. I never send.
- No "we'll check and get back to you." Work out the full answer; after 3 failed attempts, Karen.
- Sender's language. Karen's voice. `anti-ai-slop` on every draft.
- Breakfast: 6:30–10:30.
