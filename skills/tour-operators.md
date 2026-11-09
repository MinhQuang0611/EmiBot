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
   **An allotment booking is ours to honour, so it gets no "received" note** (Karen, 2026-11-04, Anex 112970549: "ghi allotment mà sao Emi báo là chúng tôi tiếp nhận thông tin"). No "received" note, no `[CHECK BEFORE SENDING]` about the PDF. Its reply is the confirmation of step 7, drafted now with `--before-pdf` (dev, 2026-11-07: `[DO NOT SEND UNTIL PDF IS ATTACHED]` on top, `#[GROUP CODE]` / `[CONF NO]` placeholders, `confirmation-replies.md` "Drafted before the PDF"); job 2 attaches the PDF when `pdf_link` lands. `done <id> "allotment, confirmation #n drafted, PDF on build"`. The Anex contract asks for an answer within 24 hours: a booking still unbuilt near that goes in the report.
5. **On request** (release passed or allotment used up): `py -m tools.emi on-request --arrival … --departure … --alloc "<code>:<rooms>,…"`
   - `REJECT` — no availability; or occupancy over 60% on a night of the stay **and** check-in more than 30 days away. Then:
     - **CANCEL rows** (not NEW): `status` Cancelled, `what_changed` "On request booking cannot be accommodated" (the same as Anex's declined bookings, `booking-intake.md` "One email, one set of rows").
     - **Decline draft** (`email-templates.md` section 6, `--kind decline`): the booking falls outside our allotment and we can't accept on-request bookings at the moment. A person still presses Send.
   - `ACCEPT` — anything not rejected is accepted (dev, 2026-11-07, Anex 112976780: it sat on E-252 with STD free and occupancy at 44%, no reply, until Karen turned it down by hand). **NEW rows exactly as an allotment booking (step 4)**: `to-price`, `rate_source` "<Operator> contract", `internal_notes` "On request, accepted by the on-request rule". No question to Karen: the reply is the confirmation of step 7, drafted now with `--before-pdf` like step 4, PDF attached by job 2. `done <id> "on request accepted, confirmation #n drafted, PDF on build"`.
   - `ASK KAREN` — only when the rule can't be checked: the availability sheet is stale or unreadable, or check-in is more than 30 days away and a night's occupancy is missing. Then `ask-karen <id> "<booking, dates, rooms: can we accept it?>" --ref <ref>`, `done <id> "waiting on Karen E-…"`, no row yet. Her yes → NEW rows; her no → the REJECT path.
6. **The build tool builds it** and pastes the PDF link in `pdf_link` (column AQ). A booking it leaves **held** is approved by Long first. Then I check the PDF against the booking (`pdf-fetch <row>`), every date, room and total.
7. **Confirmation**: a reply draft on the original thread with the group code and the EZFOLIO PDF (`draft-confirmation`; `email-templates.md` section 6). Tour operator text: the operator's ref, `Group code: #<code>`, the sign-off. No deposit or bank block — operators pay under their contract. Odeon is a new email (below).
8. **Changes and cancellations**: CHANGE or CANCEL rows. **Every CHANGE row has its notes fully rewritten (all 8 items) and its rate fields filled from a fresh `to-price`** — `sheet-append` refuses any CHANGE row (every channel since Tracy's audit, 29/10) without `notes`, `rate_source`, `rate_per_night_vnd`, `Average rate per night after discount`, `total_vnd`, `status`, `nights`, `meal_plan`. A contract total that differs by a few VND from rate × nights → the rounding line (`booking-intake.md`). A cancellation's charge comes from the operator's own table in `<operator>.md`, "to check" for Karen (`booking-intake.md` Cancellations).

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
- **CANCELLED for an on-request booking we already declined** (dev, 2026-11-07; 112967068: declined from sales@ on 02/11, the robot's CANCELLED on 04/11 went to Karen as "booking not on the sheet, fee?" and was never answered): `mail-find <ref>` first. A reply from sales@ declining it, or a decline draft of mine → the booking is closed: CANCEL row `what_changed` "On request booking cannot be accommodated", charge 0, and the short cancellation reply. No question to Karen: there is no fee on a booking we never accepted.
- **Every Anex email gets its reply, at the step its kind says:** NEW inside the allotment → the confirmation once `pdf_link` is there (step 4, step 7); CANCELLED → at once; CHANGED → the confirmation once the change is built; on request → step 5. Never a "we have recorded the reservation" note.
- The robot email also asks us to confirm through a link. Someone still has to click it; an email reply doesn't count. Report line: "Anex <ref>: bấm link xác nhận trong email robot".
- "On request" and "Partly Allotment" go through step 5.
- **Every day:** an e-invoice for that day's check-outs to hotelaccount.vn@anextour.com. **Every Monday:** the previous week's check-outs (Monday to Sunday) to the same address; once Anex confirms, hard copies of the VAT invoice, folio and reservation go by post.
  - `py -m tools.emi checkouts --company Anex --from <today>` / `--last-week` lists them from the sheet. The e-invoice itself comes from accounting's invoicing system, not from me. Not switched on as a job yet.
- **Payment:** Anex pays two weeks at a time, on Friday of the third week. A check-out invoiced in a later month isn't paid, so every invoice goes out by month-end.

## Odeon (contract 1033494, W26/S27)
Its own seven steps:
1. **Odeon emails** about a new booking.
2. **Front office gets the voucher**: logs in to the Odeon extranet, downloads it and sends it to sales@.
   - **Only a link, no file** (05–06/11: Odeon 8649178 came twice as a link and once as a PDF; a Pegas "Edit hotel booking").
     - **Front office sent a OneDrive / SharePoint link (dev, 2026-11-09; replaces 07/11's ask-karen):** front office has to send the voucher as a PDF attached to the email, never a link. I answer front office myself: `draft-reply <id> <body> --kind reply --internal`, `email-templates.md` 10, a gentle ask to send the PDF again as an attachment. No question to Karen. **No row** (dev, 2026-11-07): a NEW row with no dates, rooms or price only makes the build tool stop on blanks (rows 1586 and 1609, "lỗi dữ liệu"). `show` tries the link itself (`[link file saved: …]` once the sign-in has Files.Read.All, which needs an admin's consent the tenant hasn't given); when it opens, the row comes from that file as usual and the ask still goes, so the next voucher comes as a PDF. The email is then `done`, "voucher as link; front office asked for the PDF, draft #n".
     - **Before the ask, look for the PDF that may already be here:** the same voucher often comes twice (Odeon 8649178: link 05/11 10:04, **PDF 05/11 17:47**, link 06/11 11:09; the PDF became row 1710 under Odeon 4799222). `sheet-find` the guest's surname and the arrival date, and `mail-find` the ref; front office's emails have no subject, so also read its other emails of the last 2 days that carry a file. The voucher is already on the sheet or in another email → `done <id> "duplicate of row <n> / the <date> email"`, no row; the ask to send PDFs, not links, still goes once.
     - **The PDF arrives** (a new email from front office) → the NEW row from the voucher, as usual. A blank NEW row already written for a link (1586 Pegas 11124455) → `sheet-update <row> … --ref <ref>` with the voucher's cells, not a second NEW. Row 1609 (Odeon 8649178) is a duplicate of row 1710: Tracy marks it, not me.
     - **A link from the operator itself** (the Pegas portal): not front office's, so no ask to front office. `sheet-find <ref>`: the row already has dates, rooms and price from the operator's own email (a Pegas robot mail lists them all) → `done`, no row, no question (Pegas 11124455, 07/11). Otherwise `ask-karen <id> "<operator> gửi voucher <ref> dạng link, Emi không mở được" --ref <ref>`.
3. **I read the voucher**: Odeon ref, guests, room type, dates, meal plan, guest count and **SPO code**. I price it with exactly the offer the SPO code applies: `to-price --operator Odeon … --spo "<code[,code]>"` (`EB` = early booking at the contract tier, `EB10` = the voucher's own %, `FS001` = 10=9 free night, `SCO` / `SSO` = 5%, `none` = contract rate only). The voucher prints them in its SPOCode line: pass the whole line as `--spo`, e.g. `10 * (Contract Revise Rates(C[D45REB10%]) (C[S10P09]) ) + 3 * (…)`. `D45REB10%` = early booking, 45+ days, 10%; `S10P09` = stay 10 pay 9, the contract's FS001; `10 *` + `3 *` = nights per offer set, and `to-price` works out which nights itself (dev, 2026-11-05). A line with no `C[…]` inside, `7 * (Contract Revise Rates)`, is the contract rate with no offer: pass it as it is, it prices as `none` (dev, 2026-11-09, SGODOAMY4_11_1 went on the sheet with no rate). SCO or SSO 5% only when the voucher shows that code. A code `to-price` doesn't know → Karen.
   - Allotment → NEW row. On request → step 5 above.
   - **Rejected** → CANCEL row "On request booking cannot be accommodated", then a **new email** (not a reply: the voucher came from front office) to vietnamreservations@odeontours.com and vietnamaccounts@odeontours.com:
     ```
     py -m tools.emi draft-new <voucher email id> vietnamreservations@odeontours.com,vietnamaccounts@odeontours.com \
         "Voucher <no.> – Declined (on request)" emi-work/out/<ref>-decline.txt --kind decline --ref <ref>
     ```
4. **The build tool builds it** and pastes the PDF link in column AQ. Held → Long approves it. I check the PDF against the voucher.
5. **Proforma invoice**: from the Google Sheets template, numbered "HAYA - <group>", due 10 days before check-in, downloaded as `Invoice_<ref>.pdf`. `py -m tools.emi invoice-data <ref>` prints the number, due date and lines. **I make it myself (dev, 2026-11-09):** the workbook "HAYA Odeon Invoices 2026 - 2027" (`EMI_ODEON_INVOICE_BOOK`) has one tab per invoice, named by the Odeon ref; `py -m tools.emi invoice-make <ref>` copies the template tab Sheet1 (dev, 2026-11-09: layout, Odeon's address, the company's VND account Vietcombank 1020729617; Sheet1 prints USD, so the copy gets "Rate (VND)", "Net amount VND:" and VND amounts), writes the booking in (L8 number, M8 date, N8 due, line rows 13–17, amount in words, settle-by date) and saves `emi-work/out/Invoice_<ref>.pdf`. `--check` prints the cells and writes nothing. A tab already there with this number and total is exported as it is; with another number or total it is refused for a person to look at. `confirmation-attach` and `draft-confirmation` run it by themselves for Odeon, so normally there is nothing to do. **The invoice never holds back the EZFOLIO PDF (dev, 2026-11-09, Odeon 4801957 waited 13 h with no PDF on its draft):** when the invoice can't be made (a `NO INVOICE <ref>: …` line: the workbook not shared with Emi as Editor, a room code with no Odeon name, lines that don't add up), the PDF, group code and confirmation number still go on and the first line is `[DO NOT SEND UNTIL INVOICE IS ATTACHED]` in bold red; Accept is refused until the invoice is on: `confirmation-attach <n>` again once the cause is fixed, `--attach` a PDF a person made, or a person attaches it in Outlook (Accept then takes the line off). The report says "chờ invoice <ref>" with the reason. Never `confirmation-hold` for a missing invoice.
6. **Confirmation**: a new email to both Odeon addresses with **both PDFs**, the build tool's confirmation and the invoice:
   ```
   py -m tools.emi draft-confirmation <voucher email id> <row> emi-work/out/<ref>-confirmation.txt \
       --to vietnamreservations@odeontours.com --cc vietnamaccounts@odeontours.com \
       --subject "Odeon Reservation confirmation <ref>"
   ```
   `draft-confirmation` refuses an Odeon row without the new-email options, and makes the invoice itself (step 5); `--attach` only for an invoice a person made. If it can't be made, the draft gets the PDF and the line `[DO NOT SEND UNTIL INVOICE IS ATTACHED]`. Karen or front office press Send.
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
- **Robot mail gets its reply** (dev, 2026-11-07, Pegas 11124455 left unconfirmed by job 2 as "robot, no reply"): `pegasys-notifications@pegast.su` asks to confirm by answering the email. The confirmation goes as a reply, **to `reservation.vtm@pegast.com`**: `draft-confirmation` / `draft-reply` set it by themselves. Changing the status on the Pegas provider site is still a person's job: report line "Pegas <ref>: đổi trạng thái trên provider.pegasys".
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
