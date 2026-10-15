# Confirmation replies — only after the PMS is updated

The reply that tells an agency or guest their booking is confirmed, changed, or cancelled.

## The gate
The booking is built in EZFOLIO by a separate tool Karen is building, which reads the intake form and pastes the link to the PDF confirmation into the row once it's complete (Karen, 2026-10-08). Until that tool is live, Tracy does the same job.

I draft a confirmation only when:
- for NEW and CHANGE: the row has a `pdf_link`. The link appearing is the signal that the PMS is updated.
- for CANCEL: Karen's OK on the cancellation is on record, and the row shows the cancellation was done in EZFOLIO. A cancellation has no PDF, so what marks it as done is not settled yet — until it is, I ask Karen before drafting.

A link is not proof the booking is right. I still open the PDF and check it against the row before drafting.

If the sender chases before that, I don't draft a holding reply. I tell Karen the row is still Pending and what it's waiting on.

## Wording
Use the templates in `email-templates.md`. They are built from confirmations already sent from this mailbox. This file says when to draft and what to check; that file says how the email reads.

## Before drafting — check the PDF against the row
Open the PDF from the Drive confirmations folder (`1UDpbCxxj2EiIy_YSWK5CI4JRECVu-A3P`) and check: group code, agency, confirmation number, room type, dates, number of rooms, rate, surcharges (each printed once), grand total. If anything differs from the row or the original email, stop and report it to Karen. I never fix, regenerate, or edit a PDF.

## New booking
Reply on the original thread, in the sender's language. Include:
- Confirmation number and group code.
- Guest name(s), stay dates, room type and number of rooms, pax.
- Total, including breakfast, VAT, and service charge. Service charge is inside the room rate, never a separate line.
- **Deposit:** 50% due within 48 hours of receiving the confirmation, written as an exact date and time, "Vietnam time (UTC+7)" (Vietnamese email: "giờ Việt Nam, UTC+7"). Remaining 50% due 7 days before check-in, also as an exact date. Use the contract's terms instead if the agency has its own.
- Bank details for payment, exactly as in `email-templates.md` (taken from confirmations already sent).
- The original confirmation PDF attached, unaltered.

## Change
Same thread. State what changed (old → new), the new total, and attach the new PDF. Say plainly that it replaces the earlier confirmation.

**Deposit check (Karen, 2026-10-08):** look up Payment 1 on the intake row. If no deposit has been received, the email reminds them to pay the deposit to the hotel's bank account within 48 hours of receiving this email, with the exact deadline in Vietnam time. If the deposit is in, no reminder — state what's been received and the balance. If I can't tell, I flag it to Karen and don't draft either version.

## Cancellation
Same thread. Confirm the booking is cancelled, with confirmation number and group code, the date it was cancelled, and any charge that applies under the booking's cancellation terms. If a refund is involved, say only what Karen has approved.

## Where the draft goes
I save the reply as a draft on the original thread in sales@haya-hotels.com and leave it in the Drafts folder. Karen or another staff member reads it and presses send. I never send it.

- The deposit deadline in the draft is 48 hours from the time I draft it. I say that time in my scan report.
- Each scan, I list every draft still unsent and how long it has been waiting. Once a confirmation draft is 24 hours old, I update the deadline in it so the person sending isn't sending a deadline that has partly run out.
- After a draft is sent, I read the Sent folder for the actual sent time and use that for the cutoff follow-ups below.
- If a sent email differs from my draft, the edit is a correction: I record what changed in MEMORY.md.

## OTA bookings
No reply. The OTA confirms to the guest itself.

## Payment reminders (Karen, 2026-10-08)
I follow up on unpaid bookings myself. Reminders are drafted from `email-templates.md` (section 4) and left in Drafts like everything else.

**"Received" means:** a payment slip in the inbox for that booking, or the payment columns filled on the intake row. I check both before every reminder.

**Deposit — 50%, due 48 hours after the client received the confirmation.**
- The clock starts at the real sent time of the confirmation, read from the Sent folder.
- At **40 hours** with no deposit seen → draft the deposit reminder, stating the exact deadline (time, date, Vietnam time).
- If the 40-hour mark falls overnight, between my last run of the day and my first run the next morning, I draft the reminder at the last run before it. Waiting for morning could put it past the deadline.
- One reminder per deadline. No second chaser unless Karen asks.
- **Reminders are drafts too (Karen confirmed, 2026-10-08).** A person presses send on all email, with no exception for reminders. Because a deposit reminder only has 8 hours to be useful, every scan report lists any unsent reminder first, with the hours left until its deadline.

**Balance — remaining 50%, due 7 days before check-in.**
- No balance seen by 09:00 the day before it's due (8 days before check-in) → draft the balance reminder.
- Booking made less than 8 days before check-in: flag to Karen instead — the standard terms don't fit and she sets the deadline.

**Both reminders ask for the payment slip** so the hotel's accountant can check it.

**Agency asks to move a deadline** (deposit or balance): I never decide it. It goes to Karen as a question, at the top of the scan report (by Telegram once that channel exists). The intake row keeps the current deadline and notes the requested one as awaiting Karen. No reply to the agency until she has decided — and no holding reply either.

**Deadline passed, still nothing:** I report it to Karen. The confirmation says the booking is released automatically, but nothing is cancelled in EZFOLIO without her OK, and I don't draft a cancellation notice on my own.

**A slip arrives:** forward to accounting (see `department-forwards.md`), fill the payment columns, and no reminder goes out. If a reminder for that booking is still sitting unsent in Drafts, I flag it for deletion so it isn't sent by mistake.

## Voice
Agency confirmations follow the templates and sign off "Best, HAYA Team" in both English and Vietnamese. Anything outside a template is in Karen's voice: greeting, the facts, a polite ask if there is one, no reasons given for asks. No emoji. Run `anti-ai-slop` on any free-written text before it goes to Drafts.
