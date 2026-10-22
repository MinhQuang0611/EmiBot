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
2. **Check for an existing row.** `sheet-find` each reference number on its own (the OTA's number and the SynXis number, if the email has both) and the lead guest's surname. If the booking is already there (from an earlier email, the other half of an Agoda/SynXis pair, or written by Sunny from Zalo), update that row — don't add a second one. A SynXis notice whose OTA number is already on a row: add the SynXis number to that row's `booking_ref` with `sheet-update` (every row of the booking), don't append.
   - **Every email for the booking, not just this one.** Read the whole thread, then `mail-find <ref>` for each reference number and read those emails too (an MG voucher, the RezLive or VCC email for the same booking, an earlier version). Room type, pax, nationality or a rate missing from one email is often in another. A field is blank only when none of them has it.
3. **CHANGE / CANCEL:** find the original row and carry over its `ezfolio_group_code` and `confirmation_no`. If the booking was never in the sheet, say so in `missing_info` — Tracy has to find it in EZFOLIO.
4. **Fill one row per room type**, same `booking_ref` on every row of one booking:
   - `action`, `received_at` (DD/MM/YYYY HH:MM, when the email carrying the booking or the change arrived — see "Follow-ups" below), `source_email` (that email's subject only, no links or IDs), `property` (HAYA), `channel_type` (TA / OTA / Direct / Tour operator — see "Channel type" below).
   - `company` exactly as named in EZFOLIO — see "Company" below (not in EZFOLIO yet: write the name and put "new company" in `missing_info`; never for a named OTA or tour operator — Booking.com, Agoda, MG, Anex… are already there, and `sheet-check` refuses it), `contact_person`, `company_email` (the address of whoever actually wrote the booking: for an email a colleague forwarded in, the original From in the quoted header, never haya@ or another @haya-hotels.com address; the confirmation is sent there), `booking_ref` (see "booking_ref" below). **Direct:** never the guest's own name in `company` (the column is for an agency/OTA as named in EZFOLIO), and never "new company". Leave `company` blank and write `REQUIRED blank: company – direct guest, EZFOLIO account for direct bookings not known` in `missing_info` (Karen hasn't said which EZFOLIO account direct guests go under). The guest's name goes in `contact_person`, their email in `company_email`, and `booking_ref` stays blank unless the guest gave one.
   - `ezfolio_group_code`, `confirmation_no`: carried over for CHANGE / CANCEL, blank for NEW. `what_changed`: CHANGE only, e.g. "Dates 12–15 Nov → 13–16 Nov"; for CANCEL, the reason.
   - `guest_names` separated by ";", lead guest first, TBA if not given. `nationality`: see "Nationality" below.
   - `arrival`, `departure` (DD/MM/YYYY), `nights`, `room_code` (see "Room code" below), `rooms`, `adults`, `children` (0 if none), `child_ages` ("9; 2"), `meal_plan` (BB / RO / other).
   - `rate_source` (TA card / Anex contract / Odeon contract / Pegas contract / Crystal Bay contract / Selfie contract / OTA net / Special (Karen) / Other — exactly one of these; how the rate was worked out goes in notes item 6, never in brackets here), `rate_per_night_vnd` (the rate before surcharge, number only), `discount_promo`, `Average rate per night after discount`, `surcharge` (text, e.g. "+20% Indian guests", "Child 350k x 3 nights") and `Surcharge amount`, `total_vnd`.
   - `status` (Definite / Tentative / Cancelled), `hold_until` (DD/MM/YYYY, or DD/MM/YYYY HH:MM when the agency gives a time), `prepaid`, `invoice_details`, `arrival_time`, `transfer`, `special_requests`.
   - `notes` in the 7-line EZFOLIO format — see "Notes" below. Never mention an upgrade.
   - `missing_info`: everything the email didn't say.
   - **OTA rate floor:** an OTA row with `rate_per_night_vnd` or the average under 1,000,000 VND gets `rate floor: <rate> VND/night under 1,000,000 – likely promotion mistake` in `missing_info` (inbox-triage.md §3); `sheet-check` refuses the row without it, and the report names it to Karen.
   - `priority`. Leave `tracy_status` as Pending and `pdf_link` blank — those are Tracy's.
   - `COD` (deposit deadline): 48 hours from when the client receives the confirmation, unless the email or contract states another deadline.
   - `Payment 1`, `Payment 1 date + time`, `Payment 2`, `Payment 2 date + time` from slips in the thread. `Remaining amount` = total − Payment 1 − Payment 2 (equal to the total until a payment arrives).
   - Column names above are the sheet's exact headers (`test/fixtures/intake-columns.csv`). Filled examples: `test/fixtures/intake-examples.csv`.
5. **Required, never blank:** `company` (Direct: blank + named in `missing_info`, see above), `arrival`, `departure`, rate, `room_code`, `rooms`. If I can't fill one, the row is not ready and the gap goes in `missing_info` and to Karen.

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
| Expedia, Trip.com, Traveloka, MG, Ohmyhotel, MakeMyTrip, Dida Travel, Mytour, VNTrip | upper-case or legal-name versions |
| Anex | ANEX KHABAROVSK, Anex Tour |
| Odeon, Pegas, Crystal Bay, Selfie, Fun and Sun | Odeon Tours, Pegas Touristik, FUN&SUN |

- A legal suffix (BV, Ltd, Pte, JSC) is dropped.
- An office or city in the name ("ANEX KHABAROVSK") goes in notes item 1: `1. Anex (Khabarovsk) – Ref 112921433`. Not in `contact_person`, which is a person's name.
- SynXis is the channel manager, not the seller: `company` is the OTA the SynXis notice names (Booking.com, Expedia…); SynXis only when it names none.
- `sheet-check` warns on a known variant. These spellings are a working list: Karen hasn't confirmed them against EZFOLIO's company list yet.

## Nationality
A full English country name: "Vietnam", "India", "United Kingdom". Never a code ("VNM", "VN", "UK") — `sheet-check` refuses 2–3 letter codes.
- From the guest's passport or a nationality field in the email or voucher.
- A "market", "source market", "country of residence" or "POS" field is **not** nationality. MG and other bedbank vouchers often show only the market. If that is all there is, nationality comes from the names only when they leave no real doubt (Vietnamese names → Vietnam); otherwise leave `nationality` blank and write `nationality – only source market <X> given` in `missing_info`. Never copy the market across.
- No names (TBA) and no nationality on a Vietnamese agency's booking written in Vietnamese: Vietnam, as before. Any other case with nothing to go on: blank and named in `missing_info`.
- Changing `nationality` on an existing row means a document said so. Say which one in the report ("voucher page 2: Nationality Malaysia").

## Room code
- `sheet-schema` lists each code with its EZFOLIO name and the name agencies use (the TA table's): STD = Standard Double, SUP-DBL = Superior Double, SUP-TWN = Superior Twin, DLX-SV = Deluxe Double Seaview, and SUITE-SV, TPL, QPL, TPL-SV.
- A voucher name that is a shortened form of exactly one of these is that code: "DELUXE DOUBLE" → DLX-SV (the only deluxe double; TW-DLX is a twin and never sold to agencies), "STANDARD GARDEN" → STD. Write the voucher's own name in notes item 4: `4. 1 Deluxe Double Seaview (voucher: DELUXE DOUBLE) – 2 adults, 0 children`.
- A name that fits two codes ("Superior" with no bed type, "Deluxe Twin") or none: blank, with `REQUIRED blank: room_code – voucher says <name>` in `missing_info`. Only after reading every email for the booking (step 2).

## Notes
Exactly 7 lines, one item each, numbered `1. ` to `7. `, parts joined with ` – `. Nothing after line 7. `sheet-check` warns on anything else.
```
1. <company> – Ref <booking_ref>
2. <lead guest> – <nationality>
3. <arrival> – <departure>
4. <rooms> <room type> – <adults> adults, <children> children (<ages>)
5. <requests, or None>
6. <rate calculation, incl. VAT/breakfast note>
7. Invoice: <invoice details, or none stated>
```
Example:
```
1. Phú Minh Quang Travel – Ref Thu1230 TVR149
2. MR DEEPAK GUPTA – India
3. 04/01/2027 – 06/01/2027
4. 1 Deluxe Seaview – 2 adults, 1 child (4)
5. None
6. 2,000,000 +20% Indian = 2,400,000 × 2 nights × 1 room = 4,800,000, incl. 8% VAT
7. Invoice: CÔNG TY TNHH THƯƠNG MẠI & DỊCH VỤ DU LỊCH PHÚ MINH QUANG, MST 0402145541
```
- Line 1 starts with `company` exactly as on the row and contains `Ref <booking_ref>` exactly. Direct: `1. Direct – <contact_person>`, plus ` – Ref <ref>` if the guest gave one.
- Vietnamese-language email: the items may be in Vietnamese; the numbering and the line 1 format stay.
- CANCEL row: not the 7 lines — the single cancellation-charge line from "Cancellations — the charge" below.

## Channel type
Exactly one of `TA`, `OTA`, `Direct`, `Tour operator` — never "Tour operator (Anex)" (the sheet's row 2 shows that as an example); the operator's name goes in `company`. Decided by who the booking comes from, checked in this order (2026-10-09):
1. **Tour operator** — Odeon, Crystal Bay, Pegas, Anex, Selfie, Fun and Sun.
2. **OTA** — online travel sites: SynXis, Agoda, Expedia, Trip.com, Ohmyhotel, MG, MakeMyTrip, Traveloka, Dida Travel, Mytour, VNTrip, Booking.com.
3. **TA** — any other travel company (công ty du lịch).
4. **Direct** — an individual booking for themselves, not through any company. No company name on the row (`sheet-check` refuses a Direct row with `company` filled or "new company" in `missing_info`); the blank is named in `missing_info`.

If the email doesn't make clear whether the sender is a travel company or a private person, leave `channel_type` blank and put it in `missing_info`.

## Follow-ups
The new email is sometimes a follow-up on a booking, not the booking itself — e.g. an OTA writing "Could you please reconfirm and share the hotel confirmation number for this booking?" under its voucher.
- Booking already on the sheet → nothing to write; the follow-up goes in the report.
- Booking not on the sheet yet → write the NEW row from the original voucher in the thread. `received_at` and `source_email` are the voucher email's, not the follow-up's.
- The ask itself is not drafted: there is no confirmation number until EZFOLIO has the booking. Report line: "OTA asks for the hotel confirmation number, waiting on EZFOLIO". The answer goes with the confirmation once the row has its `pdf_link` (`confirmation-replies.md`).

## Rates
- Travel agencies: HAYA TA rate table 2026 (rates include 8% VAT and breakfast). Per Karen (2026-10-03) the 2026 table also applies to 2027 dates until she provides a new one.
  - Seasons: Normal = Mar–May, Aug–Oct; Summer = Jun–Jul; Winter = Jan–Feb, Nov–Dec; holiday rates on holidays.
  - Minimum 2 nights. 1-night stay: +250,000 VND/person weekday, +300,000 holiday (ONT).
  - Child aged 3.00–11.99 sharing the parents' bed: 350,000/night weekday, 400,000 holiday (EXC). Under 3: free. 12 and over: adult.
  - Standard Twin is quoted at the Superior Twin rate. Never TW-DLX or APT for agencies.
  - Indian guests: +20% on the applicable TA rate (Karen's rule, confirmed 2026-10-03).
- TA rate file: `docs/RATE TABLES/BẢNG GIÁ CHO TA HAYA HOTEL.pdf`.
- Tour operators: each one's own contract in `docs/RATE TABLES/`, never the TA card (dev, 2026-10-09). Anex = `Haya - Anex 2026 - 2027.pdf` (81/26-27/PQ-HAYA/AL); Crystal Bay, Odeon, Pegas (`W26 S27 ...`), Selfie = their named files. `rate_source` = "<operator> contract": Anex / Odeon / Pegas / Crystal Bay / Selfie contract.
- Fun and Sun: no contract this season. Leave `rate_source` and the rate blank unless the email states one, put "no Fun and Sun contract this season" in `missing_info`, and flag it to Karen.
- OTA: the amount that reaches the hotel's bank. Booking.com = full guest total (commission settled monthly). Expedia/SynXis = the net payment amount.
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
- For a CANCEL row: Karen has OK'd the cancellation. Tracy never cancels without it.

## After Tracy
Tracy sets `tracy_status` to Entered (or Problem) and adds `pdf_link`. That change is what opens `confirmation-replies.md`. A row at Problem goes to Karen with what Tracy reported.
