# Booking intake — email to sheet, for Tracy

Turns a booking email into rows Tracy can build in EZFOLIO without re-reading the email. Taken over from Tracy's own `booking-email-intake` skill on 2026-10-08; the sheet and its column rules are unchanged.

## The sheet
- "HAYA Ezfolio Booking Intake v2", tab **Intake**. Sheet ID `16pFhmPB6sQB7Bu8S61qq094cvq8Ie1OcRGCeC-CR440`.
- **Row 2 holds the instruction for each column. Read it before filling** — it wins over this file if they differ.
- Tab **Rules** holds the notes rule. Tab **Room codes** feeds the `room_code` dropdown.

## Read the attachments first
The voucher, rooming list or booking form is usually an attachment, and it is where room type, room count, pax, rate, total and meal plan come from. `show` saves every attachment and prints its text.
- **Scanned PDF.** `show` prints `PDF has no text layer (scan). Page images saved — open each one to read it:` and one PNG path per page. Open and read every page image before writing the row. Same for `PDF page(s) N have no text layer`: the text pages are printed, the listed pages are images.
- **Image** (payment slip, screenshot): open the saved file.
- `Page images not made` → open the PDF itself. If I still can't read it, the row's `missing_info` says "voucher not readable: <file name>" and it goes to Karen in the report.
- A field left blank because I didn't open an attachment I could have read is a mistake, not a missing field. "Voucher text unavailable" is never a reason when the page images are there.

## Steps
1. **Classify** the email as NEW, CHANGE, or CANCEL (see `inbox-triage.md`).
2. **Check for an existing row.** `sheet-find` each reference number on its own (the OTA's number and the SynXis number, if the email has both) and the lead guest's surname. If the booking is already there (from an earlier email, the other half of an Agoda/SynXis pair, or written by Sunny from Zalo), it is not NEW: anything the new email adds or changes is a CHANGE row (see "One email, one set of rows" below). The one exception: a SynXis notice whose OTA number is already on a row, saying nothing new — add the SynXis number to that row's `booking_ref` with `sheet-update` (every row of the booking), don't append.
   - **Every email for the booking, not just this one.** Read the whole thread, then `mail-find <ref>` for each reference number and read those emails too (an MG voucher, the RezLive or VCC email for the same booking, an earlier version). Room type, pax, nationality or a rate missing from one email is often in another. A field is blank only when none of them has it.
3. **CHANGE / CANCEL:** the rows repeat the whole booking as it stands after this email (Rules tab), not only what changed. **Karen's EZFOLIO tool copies only the latest CHANGE row's notes, word for word, into the Notice** (Tracy's audit, 29/10). So every CHANGE row writes itself: `notes` as the full contract-ready Notice (items 1–8: rate calculation line, invoice line, VAT line, guest requests), and every rate field — `rate_per_night_vnd`, `Average rate per night after discount`, `rate_source`, `total_vnd`, `status`, `nights`, `meal_plan`. `sheet-append` refuses a CHANGE without them. It copies the rest I leave blank from the booking's latest rows (company, channel, confirmation number, guests, dates, payments, pax) and prints what it copied; check those lines. Plus `what_changed`.
   - **Group code** on every CHANGE / CANCEL row, in both group-code columns of the live sheet: from the booking's NEW row (`sheet-append` finds it on any earlier row of the booking), else EZFOLIO's RER004 report, else EZFOLIO. Also look in the thread (HAYA's own confirmation, the PDF name). Not found → named in `missing_info`. If the booking was never in the sheet, the email still decides the action — "amendment", "revised", "update", "Re:" on a booking → CHANGE, never NEW — and `missing_info` says "original booking not on the sheet" so Tracy finds it in EZFOLIO.
4. **Fill one row per room type**, same `booking_ref` on every row of one booking:
   - `action`, `received_at` (DD/MM/YYYY HH:MM, when the email carrying the booking or the change arrived — see "Follow-ups" below), `source_email` (that email's subject only, no links or IDs), `property` (HAYA), `channel_type` (TA / OTA / Direct / Tour operator — see "Channel type" below).
   - `company` exactly as named in EZFOLIO — see "Company" below (not in EZFOLIO yet: write the name and put "new company" in `missing_info`; never for a named OTA or tour operator — Booking.com, Agoda, MG, Anex… are already there, and `sheet-check` refuses it), `contact_person`, `company_email` (the address of whoever actually wrote the booking: for an email a colleague forwarded in, the original From in the quoted header, never haya@ or another @haya-hotels.com address; the confirmation is sent there), `booking_ref` (see "booking_ref" below). **Direct:** never the guest's own name in `company` (the column is for an agency/OTA as named in EZFOLIO), and never "new company". Leave `company` blank and write `REQUIRED blank: company – direct guest, EZFOLIO account for direct bookings not known` in `missing_info` (Karen hasn't said which EZFOLIO account direct guests go under). The guest's name goes in `contact_person`, their email in `company_email`, and `booking_ref` stays blank unless the guest gave one.
   - `ezfolio_group_code`, `confirmation_no`: carried for CHANGE / CANCEL (step 3), blank for NEW. I never write the group code on any other row (`sheet-update` refuses it), unless Karen asks. `what_changed`: CHANGE only, e.g. "Dates 12–15 Nov → 13–16 Nov"; for CANCEL, the reason.
   - `guest_names` separated by ";", lead guest first, TBA if not given. `nationality`: see "Nationality" below.
   - `arrival`, `departure` (DD/MM/YYYY), `nights`, `room_code` (see "Room code" below), `rooms`, `adults`, `children` (0 if none), `child_ages` ("9; 2"), `meal_plan` (BB / RO / other).
   - **A date with no year** ("12 Nov") is the next one after the email: an email of 24/10/2026 asking for 12 Nov means 12/11/2026. `sheet-check` refuses a NEW or CHANGE arriving before the email's date.
   - **`adults`**: the pax the voucher or rooming list gives for that room type, never 2 per room by habit. A single (1 adult, one name) stays 1. Not stated anywhere → `REQUIRED blank: adults – <reason>`.
   - **Children** go on the row of the room type they sleep in (the rooming list says which), and the child surcharge goes on that same row. Rooming list silent → the children and their surcharge on the first row, and `missing_info` "which room the children (ages) share – not in the rooming list", so the agency is asked.
   - **`meal_plan`**: HAYA's TA and contract rates include breakfast, so BB unless the email says room only. OTA notices (Booking.com, Expedia, Trip.com…) → BB unless the notice says "room only" / "no meal". Never blank.
   - `rate_source` (TA card / Anex contract / Odeon contract / Pegas contract / Crystal Bay contract / Selfie contract / Booking.com guest total / OTA net / Special (Karen) / Other — exactly one of these; how the rate was worked out goes in notes item 6, never in brackets here). Booking.com → `Booking.com guest total`; every other OTA → `OTA net`; `sheet-check` refuses the mix-up. `rate_per_night_vnd` (number only; Indian guests: the rate **with** the +20% in it, e.g. 1,700,000 → 2,040,000, and the surcharge column says "+20% Indian guests (incl. in rate)"), `discount_promo`, `Average rate per night after discount`, `surcharge` (text, e.g. "+20% Indian guests", "Child 350k x 3 nights") and `Surcharge amount`, `total_vnd`.
   - `status` (Definite / Tentative / Cancelled): **Definite** for a booking request, a voucher, a tour operator's booking, and every CHANGE of a Definite booking. **Tentative** only when the sender asks to hold or put rooms on option, with a time limit → `hold_until`. `hold_until` (DD/MM/YYYY, or DD/MM/YYYY HH:MM when the agency gives a time), `prepaid`, `invoice_details`, `arrival_time`, `transfer`, `special_requests`.
   - `notes` in the 8-item EZFOLIO format — see "Notes" below. Never mention an upgrade.
   - `missing_info`: everything the email didn't say.
   - **OTA and B2B rates are accepted as they come** (Tracy's audit, 29/10): no rate-floor flag.
   - **Rounding:** rate × nights × rooms (+ surcharges) must equal the email's or contract's exact total. If it doesn't, the signed difference goes in the extra-service columns, the same ones as the one-night and child surcharges: `Surcharge amount` gets it added (e.g. `4`, `-3`; with a child surcharge of 1,050,000 and −3: `1049997`), `surcharge` gets `Rounding +4` / `Rounding -3` (after any other surcharge text, `; ` between). Tour operators, agencies and OTAs alike. EZFOLIO posts it as a folio transaction: 110 Room Charge, sub 1 System Charge, note "Rounding adjustment to contract total". `sheet-check` prints the difference when the total doesn't add up.
   - **No child or extra-bed charge when the party fits the room's capacity.**
   - `priority`. Never write `pdf_link`, the group code (except step 3), or the EZFOLIO status/error columns (live sheet columns 51–55, `ez_error` is 53): `sheet-append` and `sheet-update` refuse them. The live sheet has no `tracy_status` any more (deleted 12/10); on the SANDBOX `sheet-append` still sets it to Pending.
   - `COD` (deposit deadline): 48 hours from when the client receives the confirmation, unless the email or contract states another deadline.
   - `Payment 1`, `Payment 1 date + time`, `Payment 2`, `Payment 2 date + time` from slips in the thread. `Remaining amount` = total − Payment 1 − Payment 2 (equal to the total until a payment arrives). A slip that arrives after the booking was written is a CHANGE row (`what_changed`: "Payment 1 received 4,000,000"), never an edit of the NEW row: `sheet-update` refuses payment columns.
   - Column names above are the sheet's exact headers (`test/fixtures/intake-columns.csv`). Filled examples: `test/fixtures/intake-examples.csv`.
5. **Rooms free?** OTA and B2B bookings (Booking.com, Agoda, Expedia, Trip.com, MG Bedbank, HotelBeds, WebBeds, Ohmyhotel…) are always accepted and logged: no availability check, no question (Tracy's audit, 29/10). For a TA or direct NEW booking, or a CHANGE that adds rooms or nights: `availability --arrival … --departure … --alloc "<code>:<rooms>,…"` with the row's room codes. `DOES NOT FIT` → the row is still written as the email asks, `missing_info` gets `availability: <the DOES NOT FIT line>`, and it goes to Karen at the top of the scan report. I don't decline, move the guest to another type, or tell the sender anything: whether to accept, overbook or offer another type is Karen's call. A tour operator's allotment booking still gets the line (Karen knows the allotments).
   - **Exception — a tour operator's on-request booking** (dev, 2026-10-29): `on-request` decides. No availability, or occupancy over 60% with check-in more than 30 days away → CANCEL rows and a decline draft; anything else → ask Karen before any row (`tour-operators.md` step 5).
6. **Required, never blank:** `company` (Direct: blank + named in `missing_info`, see above), `arrival`, `departure`, rate, `room_code`, `rooms`. If I can't fill one, the row is not ready and the gap goes in `missing_info` and to Karen.

## booking_ref
The reference number(s) only, exactly as the sender prints them. The channel goes in `company`, never in `booking_ref`. `sheet-append` refuses a NEW whose `booking_ref` is already on the sheet (exact match) and `sheet-find` matches part of it, so one spelling per booking is what makes both work.
- One number: `92777EF002985`, `AGIN0116572610466700`, `112930961`, `SI781659A`.
- Two numbers for one booking (the OTA's own number and the SynXis number; Mytour's two codes): the OTA's first, joined by ` / `: `1783017402 / 92777EF002717`. Only one known so far → write that one; add the other with `sheet-update` when its email arrives.
- No channel names (SynXis, Booking.com, Agoda, MG, Anex…), no brackets, no "Ref". `sheet-check` refuses them on a row not yet built.
- A TA's own code is copied as the agency writes it ("GADT 0410STE251026", "Thu1230 TVR149"), the same on every later email.
- Never rewrite `booking_ref` on a row that already has a `pdf_link`: the confirmation record is keyed by it. Report it to Karen instead.

## Company
`company` is the name EZFOLIO uses. For the channels in "Channel type" below, one fixed spelling, whatever the email signs with:

| Write | Not |
|---|---|
| Booking.com | BOOKING.COM BV, Booking.com B.V. |
| Agoda | Agoda Company Pte Ltd |
| Expedia, Trip.com, Traveloka, MG, MakeMyTrip, Dida Travel, Mytour, VNTrip | upper-case or legal-name versions |
| Anex | ANEX KHABAROVSK, Anex Tour |
| Odeon, Pegas, Crystal Bay, Selfie, Fun and Sun | Odeon Tours, Pegas Touristik, FUN&SUN |
| Odeon | Coral Travel (any country), Sunmar, Odeonbeds — Odeon's contract covers them; the brand goes in notes item 1: `1. Odeon (Coral Travel Ukraine) – Ref …` |
| Oh My Hotel | Ohmyhotel, OHMYHOTEL. RezLive only relays it: a RezLive email for an Oh My Hotel booking is `company` Oh My Hotel |
| Wyndham | Wyndham Rewards free nights: `rate_per_night_vnd` 0, `rate_source` Other, notes item 6 "Wyndham Rewards free night" |

- A TA's name is its full trading name as it signs and as on its earlier rows ("Vietnam Travel Concierge (KOMPAS Touroperator)", not "Travel Concierge"). Footprint Travel, Travel Source and the like are TA even when the guest or a colleague forwards their email: `channel_type` comes from the booking, not from who sent this email.
- A legal suffix (BV, Ltd, Pte, JSC) is dropped.
- An office or city in the name ("ANEX KHABAROVSK") goes in notes item 1: `1. Anex (Khabarovsk) – Ref 112921433`. Not in `contact_person`, which is a person's name.
- SynXis is the channel manager, not the seller: `company` is the OTA the SynXis notice names (Booking.com, Expedia…); SynXis only when it names none.
- `sheet-check` warns on a known variant. These spellings are a working list: Karen hasn't confirmed them against EZFOLIO's company list yet.

## Nationality
A 3-letter code: `VNM`, `IND`, `GBR`, `RUS`, `KOR` (Karen, 29/10, via Tracy's audit). Never blank. `sheet-check` refuses a country name or a 2-letter code on a NEW row and says which code to write; rows from before 29/10 with a full name only get a warning.
1. The nationality the booking lists (a nationality field in the email or voucher).
2. Else the passport, if the agency sends one.
3. Else inferred from the guest's name.
4. The name gives no clue (or TBA): `VNM`.
- A "market", "source market", "country of residence" or "POS" field is **not** nationality. Never copy the market across; go on to the passport and the name.
- Changing `nationality` on an existing row means a document said so. Say which one in the report ("voucher page 2: Nationality Malaysia").

## Room code
- `sheet-schema` lists each code with its EZFOLIO name and the name agencies use (the TA table's): STD = Standard Double, SUP-DBL = Superior Double, SUP-TWN = Superior Twin, DLX-SV = Deluxe Double Seaview, and SUITE-SV, TPL, QPL, TPL-SV.
- A voucher name that is a shortened form of exactly one of these is that code: "DELUXE DOUBLE" → DLX-SV (the only deluxe double; TW-DLX is a twin and never sold to agencies), "STANDARD GARDEN" → STD. Write the voucher's own name in notes item 4: `4. 1 Deluxe Double Seaview (voucher: DELUXE DOUBLE) – 2 adults, 0 children`.
- OTA listing names (`sheet-schema` prints them as "OTAs call it"): "Deluxe Twin Sea View" / "Deluxe Twin" → **TW-DLX**, "Triple City View" → **TPL**, "Deluxe Double Sea View" → DLX-SV. TW-DLX is never sold to agencies (TA, tour operator), but an OTA guest who booked it gets it: don't move them to DLX-SV.
- A TA writing just "Twin" → SUP-TWN (the twin on the TA table; Standard Twin is quoted at the same rate). A group asking for "3 twin + 8 double" is two room types: two rows (SUP-TWN or STD-TWN as the agency names it, and STD).
- A name that fits two codes ("Superior" with no bed type) or none: blank, with `REQUIRED blank: room_code – voucher says <name>` in `missing_info`. Only after reading every email for the booking (step 2).

## Notes
Exactly 8 items, one per line, numbered `1. ` to `8. `, parts joined with ` – `. Nothing after item 8. `sheet-check` warns on anything else (Tracy's audit, 29/10; the Rules tab on the sheet still says 1–7 until Karen updates it).
```
1. <company> – Ref <booking_ref>
2. <lead guest> – <nationality code>
3. <arrival> – <departure>
4. <rooms> <room type> – <adults> adults, <children> children (<ages>)
5. <requests, or None>
6. <rate calculation, incl. VAT/breakfast note>
7. Invoice: <who pays and how: agency transfer, prepaid on the OTA, pay at hotel; Anex: from the contract>
8. VAT invoice: <company, MST, address, invoice email>   — or —   8. No VAT info
```
Example:
```
1. Phú Minh Quang Travel – Ref Thu1230 TVR149
2. MR DEEPAK GUPTA – IND
3. 04/01/2027 – 06/01/2027
4. 1 Deluxe Seaview – 2 adults, 1 child (4)
5. None
6. 2,000,000 +20% Indian = 2,400,000 × 2 nights × 1 room = 4,800,000, incl. 8% VAT
7. Invoice: agency pays by bank transfer
8. VAT invoice: CÔNG TY TNHH THƯƠNG MẠI & DỊCH VỤ DU LỊCH PHÚ MINH QUANG, MST 0402145541
```
- Line 1 starts with `company` exactly as on the row and contains `Ref <booking_ref>` exactly. Direct: `1. Direct – <contact_person>`, plus ` – Ref <ref>` if the guest gave one.
- Vietnamese-language email: the items may be in Vietnamese; the numbering and the line 1 format stay.
- CANCEL row: not the 8 items — the single cancellation-charge line from "Cancellations — the charge" below (whether CANCEL notes keep that line is open with Karen).

## Channel type
Exactly one of `TA`, `OTA`, `Direct`, `Tour operator` — never "Tour operator (Anex)" (the sheet's row 2 shows that as an example); the operator's name goes in `company`. Decided by who the booking comes from, checked in this order (2026-10-09):
1. **Tour operator** — Odeon, Crystal Bay, Pegas, Anex, Selfie, Fun and Sun.
2. **OTA** — online travel sites: SynXis, Agoda, Expedia, Trip.com, Oh My Hotel, MG, MakeMyTrip, Traveloka, Dida Travel, Mytour, VNTrip, Booking.com, Wyndham (Rewards nights).
3. **TA** — any other travel company (công ty du lịch).
4. **Direct** — an individual booking for themselves, not through any company. No company name on the row (`sheet-check` refuses a Direct row with `company` filled or "new company" in `missing_info`); the blank is named in `missing_info`.

If the email doesn't make clear whether the sender is a travel company or a private person, leave `channel_type` blank and put it in `missing_info`.

## One email, one set of rows
Each row is the record of one email. A later email about a booking already on the sheet never edits the earlier rows (live sheet, 2026-10-27: 27 follow-ups were folded into old rows or skipped). It gets its own rows:

| The email | Rows |
|---|---|
| Anything that changes or adds to the booking: dates, rooms, pax, names (Omar's name update), flight or arrival time, pick-up asked or withdrawn, a meal (Jain meal), a request, a payment slip, a fee or surcharge waiver asked for or agreed | **CHANGE**, one row per room type, `what_changed` = what this email changed |
| The hotel declined an on-request booking ("cannot be accommodated", "no availability", "fully booked" from HAYA in the thread) | **CANCEL**, `status` Cancelled, `what_changed` "On request booking cannot be accommodated". Not NEW |
| The operator's own cancel notice for a booking already CANCEL on the sheet | no row; `sheet-append` refuses a second CANCEL. `done <id> "already cancelled"` |
| Cancel and rebuild (agency cancels the group and sends it again under the same code) | CANCEL rows for the old booking + NEW rows for the new one, both from this email, in **one file** (a JSON list of rows) |
| A chaser or reminder with nothing new ("please reconfirm", an MG reminder, "any update?") | no row; a report line |
| A transfer request on a booking under 250 USD (the guest gives a WhatsApp number and flight number) | no row; the transfer is paid, 200k one way. Above 250 USD the airport transfer is free one way: that is a CHANGE row |
| A forward of a booking that already reached sales@ (a colleague's Fw:) | no row; the original email is the record (`inbox-triage.md` §1) |

A follow-up on a booking that isn't on the sheet yet → write the NEW rows from the original voucher in the thread. `received_at` and `source_email` are the voucher email's, not the follow-up's; then the follow-up's own CHANGE rows if it adds something.

`received_at` is always the time `show` prints for that email (Vietnam time), never a time written inside a quoted or forwarded header or a PDF's "Reservation date" (2789404: received 15:39, PDF 13:06).

## Follow-ups asking for the confirmation number
An OTA writing "Could you please reconfirm and share the hotel confirmation number for this booking?" under its voucher adds nothing to the booking: no row (above).
- The ask itself is not drafted: there is no confirmation number until EZFOLIO has the booking. Report line: "OTA asks for the hotel confirmation number, waiting on EZFOLIO". The answer goes with the confirmation once the row has its `pdf_link` (`confirmation-replies.md`).

## Rates
- Travel agencies: HAYA TA rate table 2026 (rates include 8% VAT and breakfast). Per Karen (2026-10-03) the 2026 table also applies to 2027 dates until she provides a new one.
  - Seasons: Normal = Mar–May, Aug–Oct; Summer = Jun–Jul; Winter = Jan–Feb, Nov–Dec; holiday rates on holidays.
  - Minimum 2 nights. 1-night stay: +250,000 VND/person weekday, +300,000 holiday (ONT).
  - Child aged 3.00–11.99 sharing the parents' bed: 350,000/night weekday, 400,000 holiday (EXC). Under 3: free. 12 and over: adult.
  - Standard Twin is quoted at the Superior Twin rate. Never TW-DLX or APT for agencies.
  - Indian guests: +20% on the applicable TA rate (Karen's rule, confirmed 2026-10-03).
- TA rate file: `docs/RATE TABLES/BẢNG GIÁ CHO TA HAYA HOTEL.pdf`.
- Tour operators: each one's own contract in `docs/RATE TABLES/`, never the TA card (dev, 2026-10-09). Anex = `Haya - Anex 2026 - 2027.pdf` (81/26-27/PQ-HAYA/AL); Crystal Bay, Odeon, Pegas (`W26 S27 ...`), Selfie = their named files. `rate_source` = "<operator> contract": Anex / Odeon / Pegas / Crystal Bay / Selfie contract. **Priced with `to-price`** (early bird, free nights, child and meal surcharges, notes item 6), the whole procedure in `tour-operators.md` (dev, 2026-10-29).
- Fun and Sun: no contract this season. Leave `rate_source` and the rate blank unless the email states one, put "no Fun and Sun contract this season" in `missing_info`, and flag it to Karen.
- OTA: the amount that reaches the hotel's bank. Booking.com = full guest total (commission settled monthly). Expedia/SynXis = the net payment amount: the **"Remittance amount"** line, ÷ nights ÷ rooms for the rate — never "Total Cost with Tax" or the "Expedia Net Rate" per night shown above it (Choong, 2026-10: 5,561,400 = 1,853,800 × 3, not 6,045,000).
- TA booking whose rate field says "Promotion", "as contract", "TA rate" or has no number: the TA card rate for that room and season (`quote`), `rate_source` TA card, the voucher's word in notes item 6. Not blank (Viet Ban Mai SI781659A: Superior Double Pool View, November → 1,900,000).
- Average rate = total after promos ÷ nights.
- **If the rate in the email and the rate table disagree, I don't pick one. I flag it to Karen.**

## Cancellations — the charge
For every TA cancellation, before writing the CANCEL row:
```
.venv/bin/python -m tools.emi cancel-fee <booking_ref> --cancelled-at "<received_at of the cancellation email>"
```
- It reads the booking's current rows (latest CHANGE, else NEW) and the TA policy, counts days from the email's date to check-in, and prints the charge, what's been paid (Payment 1/2) and paid − charge.
- The CANCEL row's `notes` is this one line and nothing else: "Cancellation charge (TA policy): [amount] VND — [days] days before check-in, [rule]. Paid: [amount]." Copy the figures from the output. Tour operator: "Cancellation charge (Anex contract): … To check." in the same shape.
- `CHARGE: UNCLEAR` (exactly 7 days) or any `GAP:` → the row's `missing_info` says "cancellation charge: Karen to decide", and the scan report shows both figures.
- Tour operator, OTA or Direct → the command refuses; take the charge from that operator's own cancellation table in `docs/rate-knowledge/<name>.md` and mark it "to check" for Karen, or give it to Karen.
- A refund is never promised. Paid − charge is shown to Karen; accounting gets the refund request only after she decides (`department-forwards.md`).

## Before a row is ready for Tracy
- `missing_info` is blank, or Karen has said to proceed anyway.
- A CANCEL row that clearly matches one booking is ready at once (Karen, 29/10). Unclear (a possible fee, which booking) → Karen first.

## Writing to the sheet
Re-read before writing (`sheet-find`: no duplicates), write through the service account as RAW text, read back after. `sheet-append` reads the rows back and refuses to report success if they aren't there; `sheet-update` saves the row as it was to `emi-work/sheet-backup/` first and reads the cell back after. A failed read-back is never "try again": check with `sheet-find` first.

## After Tracy
Karen's EZFOLIO tool (Tracy until then) builds the booking and fills `pdf_link`. That is what opens `confirmation-replies.md`. An error in the EZFOLIO status columns (`ez_error`) goes to Karen with what it says.
