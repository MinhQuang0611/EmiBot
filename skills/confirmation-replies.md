# Confirmation replies — only after the PMS is updated

The reply that tells an agency or guest their booking is confirmed, changed, or cancelled.

## The gate
The booking is built in EZFOLIO by a separate tool Karen is building, which reads the intake form and pastes the link to the PDF confirmation into the row once it's complete (Karen, 2026-10-08). Until that tool is live, Tracy does the same job.

A confirmation is ready to send (its PDF on it) only when — drafting it earlier with the DO NOT SEND line is below, "Drafted before the PDF":
- for NEW and CHANGE: the row has a `pdf_link`. The link appearing is the signal that the PMS is updated (`tracy_status` was deleted from the live sheet on 12/10).
- for CANCEL: as soon as the CANCEL row is written, when the cancellation clearly matches one booking (Karen, 29/10, via Tracy's audit). Something unclear (a possible fee, which booking) → Karen first, then the reply.

A link is not proof the booking is right. I still open the PDF and check it against the row before drafting.

If the sender chases before that, I never write "we'll check and get back to you". The scan report says the row is waiting on EZFOLIO and how long the sender has waited.

**Drafted before the PDF (dev, 2026-11-07, Pegas 11124455: booked 12:06, built 15:33, confirmed only after; "cứ cho Emi build draft, khi nào tool xuất PDF thì attach sau"; Karen to be told).** The confirmation is written in job 1, the moment the row is on the sheet, and finished in job 2:
- `draft-confirmation <id> <row> <body> --before-pdf`: the full confirmation from `email-templates.md`, with only what the build gives as a placeholder: `#[GROUP CODE]` for the group code (every place it appears, transfer reference too), `[CONF NO]` for the confirmation number, `[DEPOSIT DEADLINE]` for the deposit's time and date (`trước [DEPOSIT DEADLINE] (giờ Việt Nam, UTC+7)` / `by [DEPOSIT DEADLINE], Vietnam time (UTC+7)`). Any other `[…]` is refused. The command writes `[DO NOT SEND UNTIL PDF IS ATTACHED]` as the first line, bold red; I never write it myself or remove it.
- The draft can't be Accepted while it waits (the reviewer gets "chưa có PDF"). A Rewrite keeps the line.
- Job 2: `confirmations-due` lists the booking with `ATTACH: draft #n` once it is built. I check the PDF as always (`pdf-fetch`), then `confirmation-attach <n>`: the PDF goes on the same draft, the placeholders take the row's group code and confirmation number and a deposit deadline 48 hours from that moment, the red line comes off, and the Telegram notice is updated. Edits a person made in Outlook stay. A mismatch → `confirmation-hold` and Karen, as for any confirmation; the draft keeps its line. Odeon: `confirmation-attach <n>` makes our proforma itself (`invoice-make`) and puts both PDFs on; if the invoice can't be made (`NO INVOICE` line), the PDF and the build's facts still go on and the red line becomes `[DO NOT SEND UNTIL INVOICE IS ATTACHED]` until it is (dev, 2026-11-09). Never a hold for the invoice.
- The early draft gone from Drafts before its PDF (`WARNING #n`): a person sent or deleted it. The booking comes back as a normal `CONFIRM`; the report says it may have gone out without the PDF. Booking cancelled meanwhile (`DENY #n`): `review-deny`.

**The build tool stopped (dev, 2026-11-07).** When the build tool can't build a row it writes `ez_status` `needs_review` or `error` and its reason in `ez_note` / `ez_error` (a room type full, a group it can't find, voucher fields blank). No PDF will come until a person acts, so the confirmation never comes on its own: on 06/11 Church Travels, Footprint 031P0127J, Amara #30124, Ohmyhotel and the Pegas and Odeon vouchers sat there while the agencies chased. The hourly confirmation check now sends each stop to Karen on Telegram once, as a question `E-nnn` on the booking's email, with the build tool's reason (`py -m tools.emi build-stuck` lists them, and whether Karen has answered). What to do there is Karen's or Long's call, never mine: overbook, another room type, decline, fix the group.
- Her answer → `karen-answer`, then the draft that answer calls for (a decline, an offer of another room type), on the agency's thread.
- Long fixes it and the build tool finishes → job 2's confirmation, as usual.
- The agency chases a stuck booking → no second question while one is open for it: `done <id> "chased, waiting on Karen E-nnn"` and the chase goes at the top of the scan report with how long they have waited. No question open yet → `ask-karen` with the build tool's reason.

## Wording
Use the templates in `email-templates.md`. They are built from confirmations already sent from this mailbox. This file says when to draft and what to check; that file says how the email reads.

## Before drafting — check the PDF against the row
Open the PDF from the Drive confirmations folder (`1UDpbCxxj2EiIy_YSWK5CI4JRECVu-A3P`) and check: group code, agency, confirmation number, room type, dates, number of rooms, rate, surcharges (each printed once), grand total. If anything differs from the row or the original email, stop and report it to Karen. I never fix, regenerate, or edit a PDF.

**Not a mismatch (Karen, 04/11):** the build tool's `ez_note` "hết STD, xếp phòng hạng DLX-SV; hợp đồng vẫn ghi STD" — the booked type was full and the guests sit in a higher room inside EZFOLIO. The PDF and the confirmation say the booked type; the placement is never mentioned to the agency or guest. An old `availability: DOES NOT FIT` in a TA row's `missing_info` (written before 04/11) doesn't hold the confirmation either.

## New booking
Reply on the original thread, in the sender's language. Include:
- Confirmation number and group code.
- Guest name(s), stay dates, room type and number of rooms, pax.
- Total, including breakfast, VAT, and service charge. Service charge is inside the room rate, never a separate line.
- **Deposit:** 50% due within 48 hours of receiving the confirmation, written as an exact date and time, "Vietnam time (UTC+7)" (Vietnamese email: "giờ Việt Nam, UTC+7"). Remaining 50% due 7 days before check-in, also as an exact date. Use the contract's terms instead if the agency has its own.
- Bank details for payment, exactly as in `email-templates.md` (taken from confirmations already sent).
- The original confirmation PDF attached, unaltered.
- **Cancellation terms exactly as the PDF prints them** (audit 03/11: the email said 7 days, the EZFOLIO PDF 3 days). `draft-confirmation` reads the PDF and refuses an email whose cancellation days aren't the PDF's. If the PDF itself looks wrong (not the agency's contract), no draft: `ask-karen`.
- **One confirmation per booking**, not one per room row: a booking of several room types has one PDF and one email. `draft-confirmation` refuses a second one while the first is still in Drafts; a new PDF after a change → `--replaces <n>`.

## Change
**No note before the build (dev, 05/11, Amara #30124):** a change of dates, rooms or room type gets its row in job 1 and nothing to the agency but its change confirmation, drafted then with `--before-pdf` (dev, 07/11, above). No "we have noted", no asking them to confirm the room list. `confirmations-due` lists it as `CONFIRM CHANGE` once the build tool has finished its rows (`ez_status` done): the PDF is remade under the same Drive link and every CHANGE row carries that link from the start, so the link says nothing here; `ez_processed_at` does. From 05/11 on; older changes were confirmed by hand.

Same thread. State what changed (old → new), the new total, and attach the new PDF. Say plainly that it replaces the earlier confirmation. A `CONFIRM CHANGE` line whose change touches no date, room or total → `confirmation-hold`, nothing to send.

**Name, pax and meal-plan changes too (dev, 2026-11-07).** A change of guest names, number of guests or meal plan, built in EZFOLIO, is owed its confirmation the same way: Ohmyhotel #27984, Ohmyhotel/ivedo #27981, Mekong MVN29835 and Travel Concierge 2801572 asked for a name change, it was built, and nobody answered, because `confirmations-due` only knew dates, rooms and totals. Not a change: names given for a "TBA" booking or added to a rooming list (job 1 answers those), the same name written another way, a payment. An OTA change is confirmed like the booking itself from 13/11 on (dev: every email gets its reply, robots too, section "OTA bookings"); before that, only when a person at the agency or bed bank asked for it. The line names the booking under its group code too, so a change written under the group code (`27984`) and the booking under its number (`S26082711291H01`) are one. **The new name must be on the PDF** before I confirm it: on 06/11 the build tool's note for both Ohmyhotel name changes said only "sửa Notice", not the guest name. Old name still on the PDF → `confirmation-hold` and `ask-karen`, no draft.

**`RATE MOVED` under a `CONFIRM CHANGE` line:** the total changed while the dates and rooms stayed the same. A price the agency or Karen agreed (what_changed says so) → confirm as usual. Anything else → no draft: `confirmation-hold`, and `ask-karen`, because the price in EZFOLIO may be wrong (Ohmyhotel #27984: 7,437,500 → 9,500,000 from a provisional figure on a name change).

**Deposit check (Karen, 2026-10-08):** look up Payment 1 on the intake row. If no deposit has been received, the email reminds them to pay the deposit to the hotel's bank account within 48 hours of receiving this email, with the exact deadline in Vietnam time. If the deposit is in, no reminder — state what's been received and the balance. If I can't tell, I flag it to Karen and don't draft either version.

## Cancellation
Same thread, `draft-reply … --kind cancellation --ref <ref> --row <CANCEL row>`. Confirm the booking is cancelled, with confirmation number and group code, the date it was cancelled, and any charge that applies under the booking's cancellation terms. If a refund is involved, say only what Karen has approved.
- The charge in the email is the one on the CANCEL row's `notes` from `cancel-fee` — or, if it said UNCLEAR, the figure Karen chose. Template `email-templates.md` §3: "không tính phí" / "without charge" when it is 0, otherwise "phí hủy: [amount] VND" / "with a cancellation charge of VND [amount]".

## Where the draft goes
I save the reply as a draft on the original thread in sales@haya-hotels.com and leave it in the Drafts folder. Karen or another staff member reads it and presses send. I never send it. Reply all, To and Cc kept (`draft-confirmation` does it unless `--to` is given). Every confirmation draft has the EZFOLIO PDF attached.

- The deposit deadline in the draft is 48 hours from the time I draft it. I say that time in my scan report.
- Each scan, I list every draft still unsent and how long it has been waiting. Once a confirmation draft is 24 hours old, I update the deadline in it so the person sending isn't sending a deadline that has partly run out.
- After a draft is sent, I read the Sent folder for the actual sent time and use that for the cutoff follow-ups below.
- If a sent email differs from my draft, the edit is a correction: I record what changed in MEMORY.md.

## OTA bookings
**Confirmed like every other booking (dev, 2026-11-13; replaces "No reply. The OTA confirms to the guest itself").** Every email gets its reply, an OTA's no-reply notice too. Job 1 writes the rows and drafts the confirmation `--before-pdf` (`email-templates.md` 1c) to the email printed in the booking; job 2 attaches the EZFOLIO PDF. `confirmations-due` lists OTA bookings (and OTA changes, whoever asked) received from 13/11 on; older ones are not chased back. No amount, no bank details, no deposit: the OTA holds the money and the row's figure is the net.

## Payment reminders (Karen, 2026-10-08)
I follow up on unpaid bookings myself, **travel companies (TA) only** (Karen via the dev, 07/11: online sites — OTAs and B2B like Ohmyhotel, MG, WebBeds, Hotelbeds, Tiket — pay by VCC and are never chased, even on a row written "TA"): `py -m tools.emi payments-due` (job 3, `schedule.md`) works out who is due and prints the draft command. Tour operators pay under their contract, OTAs are paid by the OTA, and direct guests pay 100% before check-in with no reminder rule (open with Karen). Reminders are drafted from `email-templates.md` (section 4) and left in Drafts like everything else.

**"Received" means:** a payment slip in the inbox for that booking, or the payment columns filled on the booking's latest row (a payment arrives as a CHANGE row). I check both before every reminder.

**Deposit — 50%, due 48 hours after the client received the confirmation.**
- The clock starts at the real sent time of the confirmation: the first mail from sales@ carrying the booking's group code, whoever sent it. None found → `NO CONFIRMATION FOUND`, the clock hasn't started, nothing is chased: report line. A COD that is only a date is the agreed deadline instead of the 48 hours. A booking known only from the EZFOLIO backfill (`EXISTING BOOKING` rows of 05/11, no COD, no payment record) is never chased: `NOT CHASED, BACKFILL ONLY`, one report line; an OTA or B2B written as "TA" there (Ohmyhotel, MG, Mytour, Dida) isn't even listed (dev, 07/11: Ohmyhotel V26062610072H01 got a reminder for a deadline of 29/06).
- At **40 hours** with no deposit seen → draft the deposit reminder, stating the exact deadline (time, date, Vietnam time).
- If the 40-hour mark falls overnight, between my last run of the day and my first run the next morning, I draft the reminder at the last run before it. Waiting for morning could put it past the deadline.
- One reminder per deadline. No second chaser unless Karen asks.
- **Reminders are drafts too (Karen confirmed, 2026-10-08).** A person presses send on all email, with no exception for reminders. Because a deposit reminder only has 8 hours to be useful, every scan report lists any unsent reminder first, with the hours left until its deadline.

**Balance — remaining 50%, due 7 days before check-in.**
- No balance seen by 09:00 the day before it's due (8 days before check-in) → draft the balance reminder.
- Booking made less than 8 days before check-in: flag to Karen instead — the standard terms don't fit and she sets the deadline.

**Both reminders ask for the payment slip** so the hotel's accountant can check it.

**Agency asks to move its deposit deadline (dev, 2026-11-07; replaces "Karen decides", 08/10):** granted at once, no question to Karen. The new deadline is **17:00 two days after the day the request came** (a request on Saturday 07/11 → Monday 09/11, 17:00), or the time they asked for when that is sooner. Never later than that, never earlier than the deadline they already have.
```
py -m tools.emi deposit-extension --asked "<request received, DD/MM/YYYY HH:MM>" [--wanted "<their time>"] \
    [--current "<current deadline>"] [--balance-by <balance date from COD>]
```
It prints the deadline with the weekday and the `COD` text (`Deposit extended to 09/11/2026 17:00 (asked 07/11); balance by …`). Write that COD on the booking (`sheet-update --ref` on a NEW row not built yet, otherwise a CHANGE row), then the reply, `email-templates.md` 4e. `payments-due` reads the new deadline from COD, so the reminder follows it. Always an exact date and time, never "Monday" or "next week" alone (rule 6).
**A balance deadline** (7 days before check-in) asked to move: still Karen's call, `ask-karen`, with a complete best-answer draft and a CHECK line.

**Deadline passed and no reminder ever went** (`LATE` in `payments-due`, Karen 2026-11-04: bookings went unchased from 08/10 until this was built): the one reminder still goes, with the deadline as it stood.

**Deadline passed after the reminder, still nothing:** I report it to Karen (`OVERDUE`). The confirmation says the booking is released automatically, but nothing is cancelled in EZFOLIO without her OK, and I don't draft a cancellation notice on my own.

**A slip arrives** (UNC, remittance, or an OTA payout advice such as Citi Paylink for Traveloka): write the CHANGE row with the payment, send the slip to accounting with `forward-slip` (`department-forwards.md`, `email-templates.md` 4c) and, for an agency or guest, draft the thank-you that confirms the slip (`email-templates.md` 4b) in the same run (dev, 2026-10-30). No reminder goes out. An OTA payout advice gets no thank-you (no-reply sender). If a reminder for that booking is still sitting unsent in Drafts, I flag it for deletion so it isn't sent by mistake.

**The accountant answers that the money didn't arrive or is short:** to Karen; nothing more to the agency until she decides. No answer means the payment is fine (Tracy's audit, 29/10).

## Voice
Agency confirmations follow the templates and sign off "Trân trọng," / "Best regards," + "Reservations Team / HAYA Hotel Phu Quoc, Trademark Collection by Wyndham / sales@haya-hotels.com" (dev, 2026-10-27, from the Sent folder). Anything outside a template is in Karen's voice: greeting, the facts, a polite ask if there is one, no reasons given for asks. No emoji. Run `anti-ai-slop` on any free-written text before it goes to Drafts.
