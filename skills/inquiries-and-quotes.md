# Inquiries and quotes — by email

Taken over from Sunny on 2026-10-08 for email only. Sunny still answers on Zalo and WhatsApp, and the rules below are the same ones Karen set for her (config review, 2026-10-03), so an agency gets the same answer on either channel.

**Which emails this covers:** price, availability or hotel questions from someone with **no booking yet** — saved with `--kind inquiry`. A question or special request on a booking the sender **already has** (arrival time, same floor, late check-out, luggage) is not an inquiry: it's a guest request, `email-templates.md` section 5, `--kind request`, plus a forward to front office.

**Hotel facts** (check-in/out times, breakfast, pool, wifi, in-room water/tea/coffee, early check-in / late check-out charges, contact, transfer) come from `docs/rate-knowledge/hotel-info.md`. Its "Chưa biết" list is what I don't know: the email gets no draft yet. I ask Karen with `ask-karen <message_id> "<question>" --ref <ref>`, then `done <message_id> "waiting on Karen E-…"`, and write the reply once `karen-answer` has every answer (dev, 2026-10-22).

## Availability and rates — where they come from
- The **"FUTURE AVAILABILITY"** folder on Google Drive: the daily future availability file and the price PDF. Always use the newest file. Never save a fixed file ID.
- If the newest file looks stale or won't open: wait 2 minutes, retry, up to 3 times, then take it to Karen. Don't answer from an old file as if it were current.
- **Direct guests** (an individual, no company): `docs/RATE TABLES/HAYA HOTEL - DIRECT BOOKINGS.pdf`, transcribed in `docs/rate-knowledge/direct.md`, priced with `quote --channel Direct`. The table is printed valid **01/03/2026–31/05/2026**. For any stay after that, `quote` prints `GAP: RATES OUT OF DATE`. Until Karen confirms the table still applies, there is no draft: the price question goes to Karen with `ask-karen`, and the reply is written after her answer. Walk-in rates: none.

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
- `GAP:` lines are things the data can't answer. Availability is always one (not connected yet): the draft is still written, and the scan report lists it as "check availability before sending". A 2027-holiday gap → the night's rate goes to Karen with `ask-karen`; the reply waits for her answer.
- Direct guest → add `--channel Direct`. What differs from TA, all printed by the command: two rate columns only (ngày thường / Lễ, Tết), no ROH, no 1-night surcharge, no Indian +20%, child sharing a bed 350.000 (500.000 on holidays), **100% payment before check-in** (no 50% deposit line in the reply), and early check-in / late check-out charges. The `NOTE:` lines (holiday dates, breakfast) are open points for Karen: list them in the scan report. Don't write "bao gồm ăn sáng" in a direct-guest reply until Karen confirms it.
- Tour operator or OTA → the command refuses and says where to look (tour operator contract file, or Karen for OTA).

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
Dear Saurabh,

Thank you for your enquiry for the Rotary group.

For 70 guests (2 groups of 35), 3 nights at the end of January 2027, we are pleased to quote as follows:

**Rate:** VND 1,700,000 per room per night, 2 guests sharing a double or twin room. As each group is more than 15 rooms, all rooms are charged at this rate and the hotel assigns the room types.
**Example stay:** 27/01/2027 – 30/01/2027 (3 nights)
• One group of 35 guests, 18 rooms (17 shared and 1 single): VND 91,800,000
• Both groups together, 35 rooms: VND 178,500,000
**Included:** breakfast (06:30–10:30), pool, gym, wifi, VAT and service charge.

**Payment terms:**

• 50% deposit within 48 hours of receiving the booking confirmation.
• The remaining 50% 7 days before check-in.

This rate is for nights up to 31/01/2027. Stays in February 2027 around Tết are priced separately.

To hold the rooms, please send the exact dates for each group, the rooming list (double, twin and single rooms), the guests' nationality and any special requests.

Best,
HAYA Team
```
Scan report lines for it:
```
- Draft: #5
- Cần kiểm tra: còn 35 phòng cuối 01/2027 không (chưa nối file FUTURE AVAILABILITY)
- Quốc tịch chưa rõ: nếu khách Ấn Độ, giá 2.040.000/phòng/đêm, cả đoàn 214.200.000 — sửa draft trước khi gửi
```

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

[Trả lời từng câu hỏi khác trong email, từ hotel-info.md: đưa đón (giá từ ta.md, không miễn phí), nâng hạng / miễn phí (không có trên bảng giá — nói lý do thật), chính sách hủy, trẻ em… Điều không có trong hotel-info.md: chưa soạn thư, hỏi Karen bằng `ask-karen` trước]

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
- No "we'll check and get back to you." Work out the full answer; after 3 failed attempts, Karen. A vague date or a big group is not a reason to ask first: quote the period they named (above).
- Write it the way HAYA's own sent mail reads (`email-templates.md`, "How HAYA writes a reply"): one line of thanks, then the numbers.
- **Never write about what I can or can't see** (`email-templates.md`, rules for all). Not "the policy is not shown in the information available to us", not "cannot be confirmed from the reservation information". A fact I don't have means no draft yet: `ask-karen`, and the scan report names the question.
- Sender's language. Karen's voice. `anti-ai-slop` on every draft.
- Breakfast: 6:30–10:30. Other hotel facts: `docs/rate-knowledge/hotel-info.md`.
