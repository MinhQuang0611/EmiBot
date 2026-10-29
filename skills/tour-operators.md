# Tour operators — Anex, Odeon, Crystal Bay, Pegas, Selfie

Rules from the dev, 2026-10-29. They sit on top of `booking-intake.md`: everything there still applies. Contracts and rate tables are in `docs/RATE TABLES/`, transcribed in `docs/rate-knowledge/<operator>.md`, priced from `docs/rate-knowledge/<operator>-rates.json`. `python -m tools.emi to-info <operator>` prints this checklist for one operator.

## Common steps (every tour operator)
1. **Booking arrives in sales@.** A booking sent only to haya@ is forwarded to sales@ by front office first; I only see sales@. Front office's forward is an internal sender: what I reply goes to the operator (`email-templates.md` "Who the reply goes to"), never back to haya@.
2. **Read it.** Ref, guests and nationality, room type, dates, meal plan, guest count, and whether it is **allotment** or **on request**. The voucher is usually the attachment.
3. **Price it from that operator's own contract:**
   ```
   py -m tools.emi to-price --operator <Anex|Crystal Bay|Odeon|Pegas|Selfie> --arrival DD/MM/YYYY --departure DD/MM/YYYY \
       --room <code> [--rooms N] --adults <per room> [--children "<ages per room>"] [--meal BB|HB|FB] --booked DD/MM/YYYY [--spo …]
   ```
   - One call per room type (one row). `--adults` / `--children` are per room; `--rooms` multiplies.
   - `--booked` is the operator's booking date on the voucher (else the day the email arrived). It decides the early bird and the cut-off.
   - It applies the contract's early bird, stay/pay (free nights), child and meal surcharges, and prints `ROW FIELDS`: `rate_source`, `rate_per_night_vnd`, `discount_promo`, `Average rate per night after discount`, `surcharge`, `Surcharge amount`, `total_vnd`, `meal_plan` and the full calculation for **notes item 6**. Copy them; check them against the voucher.
   - The voucher's own total differs from `to-price` → I don't pick one: both figures in `missing_info`, Karen in the report (`booking-intake.md` Rates).
   - Every `GAP:` line goes in `missing_info` and the report.
   - `AFTER RELEASE` in the output = the cut-off has passed: treat the booking as on request even if the voucher says allotment, and say so in the report.
4. **Allotment → NEW rows**, one row per room type. `rate_source` "<Operator> contract", `channel_type` Tour operator, `company` the fixed spelling (`booking-intake.md` Company). `COD` = the contract's payment date (below), never the TA 48 hours.
5. **On request** (release passed or allotment used up): `py -m tools.emi on-request --arrival … --departure … --alloc "<code>:<rooms>,…"`
   - `REJECT` — no availability; or occupancy over 60% on a night of the stay **and** check-in more than 30 days away. Then:
     - **CANCEL rows** (not NEW): `status` Cancelled, `what_changed` "On request booking cannot be accommodated" (the same as Anex's declined bookings, `booking-intake.md` "One email, one set of rows").
     - **Decline draft** (`email-templates.md` section 6, `--kind decline`): the booking falls outside our allotment and we can't accept on-request bookings at the moment. A person still presses Send.
   - `ASK KAREN` — anything else can be accepted, but I ask before logging it: `ask-karen <id> "<booking, dates, rooms: can we accept it?>" --ref <ref>`, `done <id> "waiting on Karen E-…"`, **no row yet**. Her yes → NEW rows; her no → the REJECT path.
   - The availability sheet can't be read → no decision: ask Karen.
6. **The build tool builds it** and pastes the PDF link in `pdf_link` (column AQ). A booking it leaves **held** is approved by Long first. Then I check the PDF against the booking (`pdf-fetch <row>`), every date, room and total.
7. **Confirmation**: a reply draft on the original thread with the group code and the EZFOLIO PDF (`draft-confirmation`; `email-templates.md` section 6). Tour operator text: the operator's ref, `Group code: #<code>`, the sign-off. No deposit or bank block — operators pay under their contract. Odeon is a new email (below).
8. **Changes and cancellations**: CHANGE or CANCEL rows. **Every CHANGE row has its notes fully rewritten (all 7 lines) and its rate fields filled from a fresh `to-price`** — `sheet-append` refuses a tour operator CHANGE row without `notes`, `rate_source`, `rate_per_night_vnd`, `Average rate per night after discount`, `total_vnd`. A cancellation's charge comes from the operator's own table in `<operator>.md`, "to check" for Karen (`booking-intake.md` Cancellations).

## Payment dates (COD on the row)
| Operator | Due |
|---|---|
| Anex | Credit: invoiced after check-out, paid two weeks at a time. `COD` blank |
| Odeon | 100% 10 days before check-in |
| Crystal Bay | 100% at least 3 days before check-in |
| Pegas | 100% at least 7 days before check-in |
| Selfie | 100% 7 days before arrival |

The 40-hour deposit reminder and the 7-day balance reminder (`confirmation-replies.md`) are TA rules: never for a tour operator.

## Anex (contract 81/26-27)
- Emails come from a no-reply robot (`vn.robot@ms.anextour.com`). **Replies go to reservation@anexvietnam.com** — `draft-reply` on a robot email addresses it there by itself.
- **Every Anex email gets a reply draft**, including the NEW, CHANGED and CANCELLED robot emails.
- The robot email also asks us to confirm through a link. Someone still has to click it; an email reply doesn't count. Report line: "Anex <ref>: bấm link xác nhận trong email robot".
- "On request" and "Partly Allotment" go through step 5.
- **Every day:** an e-invoice for that day's check-outs to hotelaccount.vn@anextour.com. **Every Monday:** the previous week's check-outs (Monday to Sunday) to the same address; once Anex confirms, hard copies of the VAT invoice, folio and reservation go by post.
  - `py -m tools.emi checkouts --company Anex --from <today>` / `--last-week` lists them from the sheet. The e-invoice itself comes from accounting's invoicing system, not from me. Not switched on as a job yet.
- **Payment:** Anex pays two weeks at a time, on Friday of the third week. A check-out invoiced in a later month isn't paid, so every invoice goes out by month-end.

## Odeon (contract 1033494, W26/S27)
Its own seven steps:
1. **Odeon emails** about a new booking.
2. **Front office gets the voucher**: logs in to the Odeon extranet, downloads it and sends it to sales@.
3. **I read the voucher**: Odeon ref, guests, room type, dates, meal plan, guest count and **SPO code**. I price it with exactly the offer the SPO code applies: `to-price --operator Odeon … --spo "<code[,code]>"` (`EB` = early booking at the contract tier, `EB10` = the voucher's own %, `FS001` = 10=9 free night, `SCO` / `SSO` = 5%, `none` = contract rate only). SCO or SSO 5% only when the voucher shows that code. A code `to-price` doesn't know → Karen.
   - Allotment → NEW row. On request → step 5 above.
   - **Rejected** → CANCEL row "On request booking cannot be accommodated", then a **new email** (not a reply: the voucher came from front office) to vietnamreservations@odeontours.com and vietnamaccounts@odeontours.com:
     ```
     py -m tools.emi draft-new <voucher email id> vietnamreservations@odeontours.com,vietnamaccounts@odeontours.com \
         "Voucher <no.> – Declined (on request)" emi-work/out/<ref>-decline.txt --kind decline --ref <ref>
     ```
4. **The build tool builds it** and pastes the PDF link in column AQ. Held → Long approves it. I check the PDF against the voucher.
5. **Proforma invoice**: from the Google Sheets template, numbered "HAYA - <group>", due 10 days before check-in, downloaded as `Invoice_<ref>.pdf`. `py -m tools.emi invoice-data <ref>` prints the number, due date and lines. **The template is not connected to Emi yet**: a person fills and exports it until its sheet ID and layout are given; the report says "chờ invoice <ref>".
6. **Confirmation**: a new email to both Odeon addresses with **both PDFs**, the build tool's confirmation and the invoice:
   ```
   py -m tools.emi draft-confirmation <voucher email id> <row> emi-work/out/<ref>-confirmation.txt \
       --to vietnamreservations@odeontours.com --cc vietnamaccounts@odeontours.com \
       --subject "Odeon Reservation confirmation <ref>" --attach emi-work/out/Invoice_<ref>.pdf
   ```
   `draft-confirmation` refuses an Odeon row without the new-email options and the invoice. Karen or front office press Send.
7. **Confirm on the extranet**: someone presses Confirm on hotelextranet.odeontours.com. **Who: not decided yet** — every Odeon confirmation's report line says it is still to be pressed.

Changes and cancellations follow the same path, as CHANGE or CANCEL rows.

## Crystal Bay (contract 00145/26-27)
- Bookings come through Crystal Bay's online system and confirm automatically within the allotment.
- Anything outside the allotment must be answered **within 24 hours**, with the step 5 rule. Top of the scan report with the time it arrived.
- **Cut-off:** 10 days before arrival; 21 days from 1 Nov to 28 Feb and on public holidays (`to-price` prints it).
- **Before arrival:** the invoice goes with the confirmation to payment.acc@crystalbaytours.com (`invoice-data`, then `draft-confirmation … --attach`); they pay by bank transfer at least 3 days before check-in.
- **VAT invoice:** issued on the check-out date and sent within 2 working days. Late → HAYA pays any tax penalty.
- **Every Monday:** last week's check-outs invoiced (Monday to Sunday), with a signed and stamped debt reconciliation and the booking report (`checkouts --company "Crystal Bay" --last-week`).

## Pegas (W26/S27 contract)
- **Proforma invoice:** sent at least 14 days before check-in (`invoice-data` prints the send-by date).
- **Payment:** 100% by bank transfer at least 7 days before check-in, and they email the slip (a payment slip as usual: CHANGE row + accounting forward). If they pay late without telling us, the booking can be released — that is Karen's call; I report it, I don't release or warn.
- **VAT invoice:** issued on the check-out date.
- **Every week:** a signed and stamped debt reconciliation (`checkouts --company Pegas --last-week`).

## Selfie (contract 2026–2027)
- Priced from their contract (`to-price --operator Selfie`).
- So far every Selfie booking has shown "On request", so each one goes through step 5. **Open with Karen:** is that real, or just how their system labels every booking? Until she answers, each one goes through step 5.
- Their robot (`mailrobot@selfietravel.asia`) is answered with cc vietnam@selfietravel.asia (`email-templates.md`).

## Fun and Sun
No contract this season: nothing to price. Rate blank, "no Fun and Sun contract this season" in `missing_info`, flag to Karen.

## Still open (not built, or waiting on Karen)
- The proforma invoice template (Google Sheets ID and layout) — until then a person makes the PDF.
- Who presses Confirm on the Odeon extranet; who clicks the Anex robot's confirm link.
- Selfie's "On request" label.
- The daily / Monday accounting emails (Anex, Crystal Bay, Pegas) are not a scheduled job: `checkouts` gives the list on request.
- Contract details marked "Karen to confirm" in the rate files print as `GAP:` (Anex child breakfast 3–5.99 and the April holiday date, Pegas Quadruple Normal rate and the 31/12 gala dinner, Selfie early bird with the bonus night, Odeon SCO/SSO scope).
