# Inquiries and quotes — by email

Taken over from Sunny on 2026-10-08 for email only. Sunny still answers on Zalo and WhatsApp, and the rules below are the same ones Karen set for her (config review, 2026-10-03), so an agency gets the same answer on either channel.

**Which emails this covers:** price, availability or hotel questions from someone with **no booking yet** — saved with `--kind inquiry`. A question or special request on a booking the sender **already has** (arrival time, same floor, late check-out, luggage) is not an inquiry: it's a guest request, `email-templates.md` section 5, `--kind request`, plus a forward to front office.

**Hotel facts** (check-in/out times, breakfast, pool, wifi, in-room amenities, payment at the hotel, parking, smoking, laundry, tours, visa, weather, early check-in / late check-out charges, contact, transfer) come from `docs/rate-knowledge/hotel-info.md`, which includes HAYA's guest FAQ. Its "Chưa biết" list is what I don't know: the email gets no draft yet. I ask Karen with `ask-karen <message_id> "<question>" --ref <ref>`, then `done <message_id> "waiting on Karen E-…"`, and write the reply once `karen-answer` has every answer (dev, 2026-10-22).

## Availability and rates — where they come from
- **Availability: the "Future Availability — HAYA" Google Sheet** (dev, 2026-10-27; ID in `tools/config.py`, `EMI_AVAILABILITY_SHEET_ID`). One row per room type, one column per night; each cell is the rooms of that type still free that night. **0 = none left**; below 0 = overbooked, also none left. Its title gives the window it covers (e.g. 27/10/2026–23/02/2027).
- I read it only through the commands: `quote` checks every option it prints against it, and `availability --arrival … --departure … [--alloc "STD:2,TPL:1"]` shows every room type for a stay. Never from memory, never from an older run: it changes every day.
- A stay outside the sheet's window, or the sheet not readable → the command prints it; availability is unknown, and the question goes to Karen (`ask-karen`), no draft until she answers.
- **Direct guests** (an individual, no company): `docs/RATE TABLES/HAYA HOTEL - DIRECT BOOKINGS.pdf`, transcribed in `docs/rate-knowledge/direct.md`, priced with `quote --channel Direct`. The table is printed valid **01/03/2026–31/05/2026**. For any stay after that, `quote` prints `GAP: RATES OUT OF DATE`. Until Karen confirms the table still applies, there is no draft: the price question goes to Karen with `ask-karen`, and the reply is written after her answer. Walk-in rates: none.

## What to offer
- The **cheapest room type available** for the full period, unless the client names a room type. "Available" = `quote` prints `OPTION …: AVAILABLE`, i.e. free on **every** night of the stay.
- The option or the named type is `NOT AVAILABLE` → don't offer it. Re-run `quote --room-type <code>` (or `--alloc`) with the next cheapest type that `availability` shows free every night, and offer that, saying plainly the asked type is full on those dates ("Phòng Standard đã hết vào đêm 11–12/11, HAYA xin gợi ý …"). Nothing free for the whole stay → say so and give the nearest dates or types that are free; never "we'll check and get back to you".
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
  | Direct guest | `HAYA HOTEL - DIRECT BOOKINGS.pdf` — never the TA table (TA rates are agency rates) |

  A tour operator is quoted from its own contract, never from the TA table. A tour operator with no file here goes to Karen.

- **Read the transcribed version, not the PDF:** `docs/rate-knowledge/<name>.md` (one per row above, index and offer comparison in `docs/rate-knowledge/README.md`). Three of the PDFs are scans with no text layer; these files are the readable copy. If a figure looks wrong, check the PDF page — the PDF wins.

## Working out the numbers — the `quote` command (TA and direct senders)
Never price a stay by hand. Run, from `/data/emi`:
```
.venv/bin/python -m tools.emi quote --arrival DD/MM/YYYY --departure DD/MM/YYYY --adults N --children "13;5;2"
```
- `--children`: every child's age; 12 and over is counted as an adult by the command. Age not given → ask for it in the reply, don't guess.
- The sender said how to split the rooms ("3 rooms for 2 adults, 1 room 2 adults + extra bed") → price exactly that: `--alloc "STD:3,TPL:1"` (extra bed = Triple). They gave a room count only → `--rooms N`. They named a type → `--room-type DLX-SV`. Two separate beds → `--twin`. Indian guests → `--indian`.
- Nothing said about rooms → the command lists options (cheapest, fewest rooms, only doubles, sea-view upgrade). Offer **one** allocation — the cheapest unless the guests' make-up says otherwise (4 adult friends ≠ one Quadruple; a family of 4 = Quadruple) — and at most one alternative line.
- Every number in the reply (rates, surcharges, total, deposit) is copied from the command's output.
- `GAP:` lines are things the data can't answer. Availability is read from the sheet (above): `GAP: availability sheet not readable` → no draft, the scan report says so. A 2027-holiday gap → the night's rate goes to Karen with `ask-karen`; the reply waits for her answer.
- Direct guest → add `--channel Direct`. What differs from TA, all printed by the command: two rate columns only (ngày thường / Lễ, Tết), no ROH, no 1-night surcharge, no Indian +20%, child sharing a bed 350.000 (500.000 on holidays), **100% payment before check-in** (no 50% deposit line in the reply), and early check-in / late check-out charges. The `NOTE:` lines (holiday dates, breakfast) are open points for Karen: list them in the scan report. Don't write "bao gồm ăn sáng" in a direct-guest reply until Karen confirms it.
- Tour operator or OTA → the command refuses and says where to look: `to-price --operator <name>` prices from that operator's own contract (`tour-operators.md`); OTA → Karen.

## Group enquiries and vague dates: answer with rates now (dev, 2026-10-22)
"End of January", "mid-March", "around Tết", "70 pax, 3 nights": a vague date or a big group is **not** a reason to answer with questions only. That is a holding reply (AGENTS.md rule 9), and it is what the first live run did: the draft only asked for exact dates. An agency asking for "availability and best possible rates" gets rates in the first reply.

1. **Pick a stay inside the period they named** and say it is an example: "end of January 2027, 3 nights" → 27/01/2027 – 30/01/2027. Stay within one season and before any holiday (see 4).
2. **Rooms from the pax count:** 2 guests per room (double or twin). An odd number → one room for a single guest, at the same room rate. Write the assumption in the reply. Adults travelling as a group are not put four to a Quadruple even when `quote`'s "cheapest" option suggests it: run `quote --rooms N` with the room count you worked out.
3. **More than 15 double/twin rooms = ROH** (`quote` prints the NOTE): every room at the Standard Double rate of that season, the hotel assigns the room types. That is the TA table's only group offer, so say it plainly; there is no other group discount to promise. Don't add a "sea-view upgrade" line under ROH (`quote` lists Deluxe Seaview at the ROH price only because of ROH; it is not an upgrade on offer). Groups of 15 rooms or fewer: normal rates by room type.
4. **Season and holidays:** the reply says which period the rate covers. The TA table has no 2027 holiday dates. **Tết 2027 falls on 06/02/2027**, and the 2026 holiday block ran from 3 days before Tết to 5 days after it, so nights in early-to-mid February 2027 must not be quoted at the winter rate: their rate goes to Karen with `ask-karen`, and the reply is written after her answer. Other 2027 holidays: the `quote` GAP list.
5. **Give per room per night, and a total for the example stay:** per group and for everyone, if they gave two groups. Numbers copied from `quote`.
6. **Nationality not given:** quote the standard TA rate and ask for nationality in the "to hold" line. If anything in the email suggests Indian guests (Indian agency, Indian names, an Indian phone number), the scan report puts the Indian +20% figure next to it for the reviewer to decide before sending. The rule is Karen's and is never explained in the email: HAYA's own confirmation for Indian guests just shows the higher rate.
7. **GAP lines go in the scan report, not the email:** availability for that many rooms (always), holiday rates, nationality. The email is written as a full answer.
8. **Then ask for what's needed to hold:** exact dates per group, rooming (twin/double, singles), nationality, special requests.

**Example: the live-run enquiry (2026-10-22).** Asian Classic Travels (TA), Rotary group: 70 pax (35 × 2 groups), 3 nights, end of January 2027, "advise availability and best possible rates". Numbers from:
`quote --arrival 27/01/2027 --departure 30/01/2027 --adults 35 --rooms 18` (one group: 18 rooms × 1.700.000 × 3 = 91.800.000) and `--adults 70 --rooms 35` (both groups: 178.500.000, deposit 89.250.000). All three nights are winter, ROH applies (18 rooms > 15).
```
Dear Mr. Saurabh,

Greetings from HAYA Hotel Phu Quoc, Trademark Collection by Wyndham, and thank you for considering us for the Rotary group (SAGRP0331).

We are pleased to offer the following:

– Guests: 70 (2 groups of 35), 2 guests sharing a double or twin room
– Example stay: 27/01/2027 – 30/01/2027 (3 nights)
– Rate: VND 1,700,000 per room per night, breakfast included. As each group is more than 15 rooms, all rooms are charged at this rate and the hotel assigns the room types.
– One group of 35 guests, 18 rooms (17 shared and 1 single): VND 1,700,000 × 18 rooms × 3 nights = VND 91,800,000
– Both groups together, 35 rooms: VND 178,500,000

Notes:
– Rates are in VND per room per night, including daily breakfast, swimming pool and gym access, VAT and service charge.
– This rate is for nights up to 31/01/2027. Stays in February 2027 around Tết are priced separately.
– Payment: 50% deposit within 48 hours of our booking confirmation, balance 7 days before check-in, by bank transfer.
– Cancellation: free of charge more than 7 days before check-in; 3–6 days: 1 night charge; within 3 days: 50%; no-show: 100%.
– Check-in from 14:00, check-out before 12:00.

To hold the rooms, please send the exact dates for each group, the rooming list (double, twin and single rooms), the guests' nationality and any special requests.

Best regards,
Reservations Team
HAYA Hotel Phu Quoc, Trademark Collection by Wyndham
sales@haya-hotels.com
```
Scan report lines for it:
```
- Draft: #5
- Phòng: 27–30/01/2027 còn đủ 35 phòng (availability, STD/SUP-DBL/DLX-SV)
- Quốc tịch chưa rõ: nếu khách Ấn Độ, giá 2.040.000/phòng/đêm, cả đoàn 214.200.000 — sửa draft trước khi gửi
```

## Reply to an inquiry — template (from the Sent folder, 13–27/10/2026)
Same rules as `email-templates.md` (greeting, opening line, plain `Label: value` lines, sums written out, sign-off "Trân trọng, / Best regards, + Reservations Team…", sender's language). Sources: Explore Vietnam (25/10, EN), Selina Tran (21/10, VI), J Chang (25/10, EN). Drop any line that doesn't apply.

Vietnamese:
```
Kính gửi anh/chị [Tên],

HAYA Hotel Phu Quoc, Trademark Collection by Wyndham xin chân thành cảm ơn anh/chị đã quan tâm và liên hệ với khách sạn.

Khách sạn xin gửi báo giá cho [n người lớn[, n trẻ em (tuổi)]], thời gian lưu trú [DD/MM/YYYY] – [DD/MM/YYYY] ([n] đêm) như sau:

– [Hạng phòng] ([giường]): [giá] VND/phòng/đêm × [n] phòng × [n] đêm = [tiền] VND
[– [Hạng thứ hai] ([giường]): [giá] VND/phòng/đêm – tổng [n] đêm [tiền] VND]
[– Phụ thu trẻ em [tuổi] tuổi (ngủ chung giường với bố mẹ): 350.000 VND/bé/đêm × [n] đêm = [tiền] VND; bé dưới 3 tuổi miễn phí]
[– Phụ thu ở 1 đêm: [giá] VND/khách × [n] khách = [tiền] VND]
Tổng tiền: [tổng] VND (đã bao gồm ăn sáng và 8% VAT)
[Gợi ý: một câu vì sao chọn cách xếp phòng này, từ giường và sức chứa trong output của quote.]
[Nếu anh/chị muốn [hạng khác], khách sạn có hạng [ ]: [giá] VND/phòng/đêm – tổng [n] đêm [tiền] VND.]

Lưu ý:
– Giá đã bao gồm ăn sáng (06:30–10:30), hồ bơi, phòng gym, wifi và 8% VAT.
– Thanh toán: đặt cọc 50% trong vòng 48 giờ sau khi nhận xác nhận đặt phòng; 50% còn lại trước 07 ngày so với ngày nhận phòng. [Khách lẻ: thanh toán 100% trước khi nhận phòng.]
– Chính sách hủy: [theo bảng giá của người gửi]
– Nhận phòng từ 14:00, trả phòng trước 12:00.

[Trả lời từng câu hỏi khác trong email, từ hotel-info.md: đưa đón, chỗ đậu xe, thanh toán bằng tiền mặt… Điều không có trong hotel-info.md: chưa soạn thư, hỏi Karen bằng `ask-karen` trước.]

Để khách sạn giữ phòng, anh/chị vui lòng xác nhận giúp:
1. Hạng phòng anh/chị chọn
2. Họ tên đầy đủ của khách
3. Số lượng người lớn và trẻ em (độ tuổi trẻ em nếu có), quốc tịch và yêu cầu đặc biệt (nếu có)

Trân trọng,
Reservations Team
HAYA Hotel Phu Quoc, Trademark Collection by Wyndham
sales@haya-hotels.com
```
English:
```
Dear [Mr. / Ms. Name / Name] [and [Agency] team],

Greetings from HAYA Hotel Phu Quoc, Trademark Collection by Wyndham, and thank you for your enquiry.

We are pleased to offer the following for your request:

– Stay: [DD/MM/YYYY] – [DD/MM/YYYY] ([n] nights)
– Rooms: [n] [room type], breakfast included
– Guests: [n] adults[, n children aged …][ ([nationality])]

Our offer:
– [Room type] ([bed]): VND [rate] per room per night × [n] nights = VND [total]
[– [Room type] ([bed]): VND [rate] per room per night × [n] nights = VND [total]]

Notes:
– Rates are in VND per room per night, including daily breakfast, swimming pool and gym access, and 8% VAT.
– [Bed sizes, from hotel-info.md, when they asked about beds.]
– Payment: 50% deposit within 48 hours of our booking confirmation, balance 7 days before check-in, by bank transfer. [Direct guests: full payment before check-in.]
– Cancellation: [from the sender's rate file].
– Check-in from 14:00, check-out before 12:00.

[Answers to their other questions, one short paragraph each.]

To proceed, please confirm your preferred room type together with the guests' full names, the number of adults and children, nationality and any special requests.

Best regards,
Reservations Team
HAYA Hotel Phu Quoc, Trademark Collection by Wyndham
sales@haya-hotels.com
```
- **The type they asked for is full** (`quote` NOT AVAILABLE): say it plainly first, then the offer: `We regret to inform you that our [room type] is fully booked for your requested dates, from [d] to [d]. However, we are pleased to offer you our [other type], which [why it fits].` / `Rất tiếc hạng [ ] đã hết phòng vào [ngày]; khách sạn xin gợi ý hạng [ ] như sau:`
- **Nothing is free for the whole stay:** the short "fully booked" reply in `email-templates.md` section 9.
- A late answer opens with an apology: `…xin cảm ơn chị đã phản hồi và xin lỗi chị vì phản hồi chậm.`

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
- No "we'll check and get back to you." Work out the full answer; after 3 failed attempts, Karen. A vague date or a big group is not a reason to ask first: quote the period they named (above).
- Write it the way HAYA's own sent mail reads (`email-templates.md`, "Rules that apply to every email"): one line of thanks, then the numbers.
- **Never write about what I can or can't see** (`email-templates.md`, rules for all). Not "the policy is not shown in the information available to us", not "cannot be confirmed from the reservation information". A fact I don't have means no draft yet: `ask-karen`, and the scan report names the question.
- Sender's language. Karen's voice. `anti-ai-slop` on every draft.
- Breakfast: 6:30–10:30. Other hotel facts: `docs/rate-knowledge/hotel-info.md`.
