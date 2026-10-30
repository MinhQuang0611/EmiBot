# EmiBot audit: branch `deploy-openclaw` vs Tracy's current workflow
Checked 29/10/2026 by Tracy (HAYA Reservations). Read-only: nothing in the repo was changed.
`deploy-openclaw` is 60 commits ahead of `master` (0 behind); `master` is the old 8–9 Oct version.

## 1. Which files cover what
| Area | Files |
|---|---|
| Reading emails | `skills/inbox-triage.md`, `skills/tour-operators.md` |
| Replying (drafts) | `skills/email-templates.md`, `skills/confirmation-replies.md`, `skills/inquiries-and-quotes.md`, `skills/department-forwards.md`, `skills/telegram-review.md` |
| Intake sheet | `skills/booking-intake.md` |
| All three (repeated rules) | `AGENTS.md`, `MEMORY.md` |

## 2. Already correct on `deploy-openclaw`
- Sign-off: "Trân trọng, / Best regards," then "Reservations Team, HAYA Hotel Phu Quoc, Trademark Collection by Wyndham".
- Tour-operator on-request rule: reject if no availability, or occupancy >60% and check-in >30 days away; otherwise ask Karen. Declines get a CANCEL row ("On request booking cannot be accommodated") plus a decline draft.
- Operator prices come from each operator's contract (`to-price`), never asked.
- Odeon drafts attach the Ezfolio PDF and the proforma invoice (vietnamreservations@ / vietnamaccounts@).
- Anex robot emails get reply drafts.
- Slip forwards to the accountant are in Vietnamese with group codes.
- All attachments are read, including scanned image pages.
- Agoda/SynXis duplicate pairs are deduped.
- Every confirmation draft attaches the Ezfolio PDF.
- Travel-agency room requests: reply "sold out" when occupancy >50% and the dates are >14 days out. Karen confirmed this is a correct revenue rule; keep it, but label it clearly as being for travel-agency requests only (see 3.3).

## 3. Mismatches to fix (repo now → correct)
1. **Notes format** (`booking-intake.md`, `tour-operators.md`): exactly 7 lines → 8 items numbered "1." to "8.". Item 8 = "8. VAT invoice: <company, MST, address, invoice email>" or "8. No VAT info".
2. **CHANGE rows**: only the changed fields plus `what_changed`, with `sheet-append` copying the rest → every CHANGE row's notes column must hold the full contract-ready Notice (items 1–8, incl. rate calc line, invoice line, guest requests), and all rate fields must be filled (rate/night, average rate, source, total, status, nights, meal plan). Karen's Ezfolio tool copies only the LATEST CHANGE row's notes verbatim into the Notice. Today only tour-operator CHANGE rows rewrite the notes.
3. **Stop sales (missing rule)**: the repo has only the travel-agency 50%/14-day rule. Add a separate rule: when a room type's inventory in the future availability file is 1 or less (incl. 0 or negative) for a date, stop sales on B2B and OTA sites by drafting a stop-sales email in sales@ that matches past stop-sales emails (format and recipients).
4. **OTA rate floor** (`inbox-triage.md`, `booking-intake.md`, `MEMORY.md`, `AGENTS.md`): OTA rates under 1,000,000 VND get flagged and `sheet-check` refuses the row → OTA and B2B bookings (Booking.com, Agoda, Expedia, Trip.com, MG Bedbank, HotelBeds, WebBeds, Ohmyhotel…) are always accepted and logged; no flag, no availability question.
5. **Palma** (`inbox-triage.md`, `AGENTS.md`): flag to Karen → auto-forward every Palma Resort email to booking@palmahotel.vn (check Sent Items, never twice). Don't log it on the HAYA sheet or draft replies. Emails from accountant@palmahotel.vn about HAYA payments are not Palma items.
6. **Holding replies** (`AGENTS.md` rule 9, `confirmation-replies.md`, `inbox-triage.md`): go to Karen after 3 failed attempts / draft only when every fact is known / chasers get no draft → never write "we'll check and get back to you". Always save a complete best-answer draft, with a bold red "[CHECK BEFORE SENDING: …]" line at the top (no highlight colour) naming what's uncertain, and raise it with Karen.
7. **Payment slips** (`department-forwards.md`, `AGENTS.md` rule 1): every forward is a draft; slips without a group code are held → forward every HAYA slip, UNC, remittance and OTA payout advice (e.g. Citi Paylink for Traveloka) to accountant@palmahotel.vn automatically in Vietnamese. Check Sent Items first and never forward twice.
8. **`tracy_status`** (`booking-intake.md`, `MEMORY.md`, `AGENTS.md`, `tools/intake_sheet.py`, `tools/README.md`): Pending/Entered as the gate → that column was deleted on 12/10. A row counts as built when Karen's Ezfolio tool fills `pdf_link`.
9. **Protected columns / group code**: CHANGE/CANCEL rows "carry over" the group code → never write cols 51–55 (Ezfolio status/error columns, incl. `ez_error` col 53), `pdf_link` or the group code, except on CANCEL rows or when Karen asks. Every CHANGE row carries the group code in both group-code columns (look it up in the NEW row, then RER004, then Ezfolio).
10. **Nationality** (`sheet-check` refuses codes): use the nationality the booking lists; if the agency sends a passport, use that; otherwise infer it from the guest's name; if the name gives no clue, use VNM. Store it as a code (e.g. VNM), and `sheet-check` must accept codes. (Karen 29/10)
11. **Cancellations**: CANCEL rows wait for Karen's OK → when a cancellation email clearly matches a booking, log the CANCEL row and draft the reply right away. Ask Karen first only if something is unclear (possible fee, which booking). Always a separate CANCEL row; never convert the NEW row. (Karen 29/10) Still open: should CANCEL notes keep the TA cancellation-charge line?

## 4. Rules missing entirely (add)
- **Rounding**: if rate × nights × rooms ≠ the exact email/contract total, put the signed difference (e.g. +4 / −3 VND) in the extra service column (the one used for the one-night and child surcharges). Applies to tour operators, agencies and OTAs. In Ezfolio it posts as a folio transaction: 110 Room Charge, sub 1 System Charge, note "Rounding adjustment to contract total".
- **Phishing**: ignore "new booking" emails from care@mail.myjorney.com and vip@mail.voyageandco.com. Never log, draft, click or report them. Never click confirm or portal links in unsolicited emails.
- OTA payout advices count as payment slips.
- No reply from the accountant means the payment is fine; acknowledge receipt to the agency.
- Never put Karen's name in any draft.
- Always reply all, keeping To/CC, and save drafts as HTML.
- Stop-sales email drafted in sales@ (see 3.3).
- Sheet writes: re-read before writing (no duplicates), back up first, write RAW through the service account, verify after.
- VAT invoice chasers go to ctyphuongnguyenpq.kt@gmail.com.
- No intake row for transfer requests on bookings under 250 USD (airport transfer is free above 250 USD; guest gives a WhatsApp number and flight number).
- Bank sheet ("CTY HAYA 617"): "tp" in column H, group code(s) in column I. Card batches are matched via the card report's "Số bút toán báo có" = bank reference, using gross amounts.
- No child or extra-bed charge when the party fits the room's capacity.

## 5. In the repo but not what Tracy does (remove or confirm)
- OTA rate-floor flag (see 3.4).
- `availability` DOES NOT FIT → "still write the row, never decline" (conflicts with the on-request decline rules).
- `cancel-fee` command and the TA cancellation-charge line in CANCEL notes (open question).
- Direct guests: company left blank.
- "Parents' sign-off" on pricing decisions.
- Emi/Tracy/Sunny/Mira split (`AGENTS.md`, `SOUL.md`, `IDENTITY.md`, setup briefs): confirm it's still accurate.
- 40-hour deposit reminder and day-before balance reminder: confirm they still apply.
- Daily/Monday accounting emails for Anex, Crystal Bay and Pegas (listed as open, not scheduled).
- Telegram review flow and Vietnamese scan reports without tables.

## 6. Open questions for Karen / Minh Quang
1. Should CANCEL notes include the TA cancellation-charge line?
2. Is the Emi/Tracy/Sunny/Mira split still accurate?
3. Do the 40-hour deposit and day-before balance reminders still apply?
4. Should "parents' sign-off on pricing" stay?
5. Who writes the HAYA intake rows today: Emi, Tracy, or both?
