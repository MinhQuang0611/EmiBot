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
2. **Check for an existing row.** Search the sheet by `booking_ref` and by guest name. If the booking is already there (from an earlier email, or written by Sunny from Zalo), update that row — don't add a second one.
3. **CHANGE / CANCEL:** find the original row and carry over its `ezfolio_group_code` and `confirmation_no`. If the booking was never in the sheet, say so in `missing_info` — Tracy has to find it in EZFOLIO.
4. **Fill one row per room type**, same `booking_ref` on every row of one booking:
   - `action`, `received_at` (DD/MM/YYYY HH:MM, when the email carrying the booking or the change arrived — see "Follow-ups" below), `source_email` (that email's subject only, no links or IDs), `property` (HAYA), `channel_type` (TA / OTA / Direct / Tour operator — see "Channel type" below).
   - `company` exactly as named in EZFOLIO (not in EZFOLIO yet: write the name and put "new company" in `missing_info`), `contact_person`, `company_email`, `booking_ref`. **Direct:** never the guest's own name in `company` (the column is for an agency/OTA as named in EZFOLIO), and never "new company". Leave `company` blank and write `REQUIRED blank: company – direct guest, EZFOLIO account for direct bookings not known` in `missing_info` (Karen hasn't said which EZFOLIO account direct guests go under). The guest's name goes in `contact_person`, their email in `company_email`, and `booking_ref` stays blank unless the guest gave one.
   - `ezfolio_group_code`, `confirmation_no`: carried over for CHANGE / CANCEL, blank for NEW. `what_changed`: CHANGE only, e.g. "Dates 12–15 Nov → 13–16 Nov"; for CANCEL, the reason.
   - `guest_names` separated by ";", lead guest first, TBA if not given. `nationality` as a country name ("India"), from the email, else inferred from the names; if there is no name and no nationality, Vietnam. Never blank.
   - `arrival`, `departure` (DD/MM/YYYY), `nights`, `room_code` (dropdown), `rooms`, `adults`, `children` (0 if none), `child_ages` ("9; 2"), `meal_plan` (BB / RO / other).
   - `rate_source` (TA card / Anex contract / OTA net / Special (Karen) / Other), `rate_per_night_vnd` (the rate before surcharge, number only), `discount_promo`, `Average rate per night after discount`, `surcharge` (text, e.g. "+20% Indian guests", "Child 350k x 3 nights") and `Surcharge amount`, `total_vnd`.
   - `status` (Definite / Tentative / Cancelled), `hold_until`, `prepaid`, `invoice_details`, `arrival_time`, `transfer`, `special_requests`.
   - `notes` in the 7-line EZFOLIO format: (1) agency and reference, (2) lead guest and nationality, (3) stay dates, (4) room types and total adults + children, (5) requests, (6) rate calculation, (7) invoice details. Never mention an upgrade.
   - `missing_info`: everything the email didn't say.
   - `priority`. Leave `tracy_status` as Pending and `pdf_link` blank — those are Tracy's.
   - `COD` (deposit deadline): 48 hours from when the client receives the confirmation, unless the email or contract states another deadline.
   - `Payment 1`, `Payment 1 date + time`, `Payment 2`, `Payment 2 date + time` from slips in the thread. `Remaining amount` = total − Payment 1 − Payment 2 (equal to the total until a payment arrives).
   - Column names above are the sheet's exact headers (`test/fixtures/intake-columns.csv`). Filled examples: `test/fixtures/intake-examples.csv`.
5. **Required, never blank:** `company` (Direct: blank + named in `missing_info`, see above), `arrival`, `departure`, rate, `room_code`, `rooms`. If I can't fill one, the row is not ready and the gap goes in `missing_info` and to Karen.

## Channel type
Decided by who the booking comes from, checked in this order (2026-10-09):
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
- Tour operators: each one's own contract in `docs/RATE TABLES/`, never the TA card (dev, 2026-10-09). Anex = `Haya - Anex 2026 - 2027.pdf` (81/26-27/PQ-HAYA/AL); Crystal Bay, Odeon, Pegas (`W26 S27 ...`), Selfie = their named files. `rate_source` = "<operator> contract", e.g. "Odeon contract".
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
- Put one line in the CANCEL row's `notes`: "Cancellation charge (TA policy): [amount] VND — [days] days before check-in, [rule]. Paid: [amount]." Copy the figures from the output.
- `CHARGE: UNCLEAR` (exactly 7 days) or any `GAP:` → the row's `missing_info` says "cancellation charge: Karen to decide", and the scan report shows both figures.
- Tour operator, OTA or Direct → the command refuses; take the charge from that operator's own cancellation table in `docs/rate-knowledge/<name>.md` and mark it "to check" for Karen, or give it to Karen.
- A refund is never promised. Paid − charge is shown to Karen; accounting gets the refund request only after she decides (`department-forwards.md`).

## Before a row is ready for Tracy
- `missing_info` is blank, or Karen has said to proceed anyway.
- For a CANCEL row: Karen has OK'd the cancellation. Tracy never cancels without it.

## After Tracy
Tracy sets `tracy_status` to Entered (or Problem) and adds `pdf_link`. That change is what opens `confirmation-replies.md`. A row at Problem goes to Karen with what Tracy reported.
