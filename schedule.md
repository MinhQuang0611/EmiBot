# Emi — scheduled jobs

Drafted by Monica 2026-10-08, times for jobs 1–3 set by Karen the same day. **Switched on (dev, 2026-10-22): job 1 only, 24/7, on real mail.** A watcher (OpenClaw command automation "Emi mail watcher", every minute, no model) runs `tools.watch`, and new mail in sales@ starts job 1 (automation "Emi job 1 - inbox", isolated session, report to the dev's Telegram) within a minute or two. Job 1 also runs every 3 hours as a safety net. **Live from the evening of 2026-10-30 (dev):** rows go straight onto the live intake sheet, drafts straight into Outlook Drafts, each with a Telegram notice; Karen's Accept is her approval and a person presses Send (`skills/telegram-review.md`). Jobs 2–4 are not switched on. All times are Vietnam time: set the scheduler's timezone to `Asia/Ho_Chi_Minh` (on a server running UTC, subtract 7 hours).

Runs every day including weekends — agencies email on Saturdays and Sundays.

| # | Job | Cron (Vietnam time) | Runs |
|---|---|---|---|
| 1 | Inbox scan + 40-hour deposit reminders | `0 6-22 * * *` | Hourly, 06:00–22:00 (17 a day) |
| 2 | Confirmation drafts | `30 6-22 * * *` | Hourly at :30, 06:30–22:30 (17 a day) |
| 3 | Payment deadline check | `0 8,15 * * *` | 08:00 and 15:00 |
| 4 | Daily report to Karen | `30 21 * * *` | 21:30 |

## 1. Inbox scan + 40-hour deposit reminders — `0 6-22 * * *`
Hourly (Karen, 2026-10-08). The 06:00–22:00 window is Monica's, matched to job 2.
Skills: `inbox-triage.md`, `booking-intake.md`, `department-forwards.md`, `inquiries-and-quotes.md`, `email-templates.md`.
1. Read every email in sales@haya-hotels.com received since the last scan, whole thread and attachments.
2. Classify each one.
3. New / change / cancellation → write intake sheet rows. A clear cancellation → CANCEL row + cancellation reply draft at once; unclear (fee, which booking) → Karen first.
4. Payment slips, UNC, remittances, OTA payout advices → a CHANGE row with the payment columns filled; draft the forward to accountant@palmahotel.vn in Vietnamese, with the group code or "chưa có mã đoàn", and the thank-you to the sender confirming the slip (`email-templates.md` 4b). Once per email. A slip paid to someone else (not HAYA's account 1020729617, or another hotel's / booking's UNC) → no forward, no payment columns, only the reply asking for the correct UNC (`email-templates.md` 4d; dev, 2026-10-30).
5. Arrival details, special requests, rooming lists → on the booking's row (`special_requests`, `arrival_time`, notes item 5), a CHANGE row for a booking already on the sheet; the guest or agency gets the reply. No forward to front office: it reads the EZFOLIO notes (dev, 2026-10-30).
6. Inquiries and quote requests → draft the reply.
7. Read the Sent folder: for any draft of mine that was sent, record the real sent time and note any edits as corrections.
8. Palma emails → forward draft to booking@palmahotel.vn (once). Flag money asks and anything unclassified. Phishing senders are dropped by `inbox-new`.
8a. **Stop sales:** `stop-sales` → any room type at 1 room or fewer on a night → stop-sales draft in the form of HAYA's last one (`skills/inquiries-and-quotes.md`). `STOP SALES NOT CHECKED` (sheet not readable) → one report line, carry on.
9. **40-hour deposit reminder.** For every confirmed booking with no deposit seen, count hours since the confirmation was actually sent. 40 hours reached → re-check the inbox and the payment columns, then draft the deposit reminder. At the 22:00 run, also draft it for any booking that will reach 40 hours before 06:00. This lives here, not in job 3, because the 40-hour mark can land at any hour and job 3 only runs twice a day.

### Job 1 — the commands, in order
Run everything from `/data/emi` with `.venv/bin/python` (written `py` below). Use only these commands to reach the mailbox and the sheet; never write your own Python for it. Write your own files (row JSON, draft text) under `emi-work/out/`.

**One command per shell call (dev, 30/10).** `show`, `sheet-find`, `sheet-check`, `sheet-append`, `sheet-update`, `draft-*`, `done`: each in a shell call of its own, never several joined by newlines, `;` or `&&`, never a loop over ids. Every `tools.emi` command prints `END <command> rc=<n>` as its last line. No `END` line = the output was cut off (the shell call came back before the command finished): run that command again on its own and read the whole output. A cut-off output is not a failed run. (30/10 21:23–22:15: ten `show`s in one call came back half after 30 s and three runs stopped with 29 mails unread.)

1. `py -m tools.precheck inbox --agent` → prints `quiet` or `work`, exit 0 either way (audit 30/10: exit 1 made every quiet run show as "Bash failed" and hid the real failures). `quiet`: answer exactly `NO_REPLY` (the scheduler then posts nothing) and stop. Exit 2: report the error line and stop.
2. `py -m tools.emi sheet-schema` → every sheet column with its level, required rule, allowed values and the sheet's own instruction, plus the room codes and the Rules tab. Read it once per run; it is the only reference for column names and values. Never guess a column name or a value format.
3. `py -m tools.emi inbox-new` → note the `scan_started=` value; you need it in step 7.
4. For each email listed, oldest first:
   1. `py -m tools.emi show <id>` → the whole thread, with attachments saved and their text printed. Image attachments: open the saved file to read it. A scanned PDF (`PDF has no text layer (scan)`) prints the paths of its page images: open and read every one before writing the row. If it says `Page images not made`, open the PDF itself; if that fails too, the voucher goes to Karen in the report as unread.
   2. Classify it (`skills/inbox-triage.md`).
   3. Booking → `py -m tools.emi sheet-find <booking_ref>` and `sheet-find <guest surname>`.
      - Not there and this email is the booking itself → `py -m tools.emi sheet-template NEW emi-work/out/<ref>.json`. A direct guest's `booking_ref`: `py -m tools.emi direct-ref`. ("There" = my sheet or the live sheet: `sheet-find` reads both.) Not there but the email is a follow-up (modification, payment, request, guest in house) on a booking HAYA already has → CHANGE with `missing_info` "original booking not on the sheet", never a NEW dated back to the original email (`skills/booking-intake.md`, "One email, one set of rows"; audit 30/10). `sheet-check` warns on a NEW dated more than 2 days back. Fill the values: shared columns in `booking`, one `room_lines` entry per room type (copy the entry for each extra type). Don't add or rename keys. Unknown → leave blank; a blank REQUIRED column goes in `missing_info` as `REQUIRED blank: <column> – <reason>`.
      - Change, payment, follow-up that adds something, or cancellation of a booking already there → `sheet-template CHANGE` (or `CANCEL`): new rows with the same `booking_ref` and `what_changed` filled. A CHANGE row writes its own `notes` (all 8 items) and every rate field (`rate_per_night_vnd`, average, `rate_source`, `total_vnd`, `status`, `nights`, `meal_plan`); `sheet-append` copies the rest (company, guests, dates, payments, pax, group code into both columns) from the booking's rows and prints what it copied. A CANCEL with one empty room line becomes one row per room type. Cancel-and-rebuild: CANCEL and NEW rows in one file. Not built yet (no `pdf_link` on either sheet) → no CHANGE: `sheet-update` the NEW rows with the news, as the live sheet does; a payment is a CHANGE row anyway (`skills/booking-intake.md`, "One email, one set of rows", dev 30/10).
      - TA or direct NEW, or a CHANGE adding rooms/nights (not OTA / B2B: always accepted) → `py -m tools.emi availability --arrival <DD/MM/YYYY> --departure <DD/MM/YYYY> --alloc "<code>:<rooms>,…"`. `DOES NOT FIT` → `availability: …` in `missing_info`, top of the report for Karen (`skills/booking-intake.md` step 5). `AVAILABILITY NOT CHECKED` (sheet not readable, exit 0) → `availability: not checked – Future Availability sheet not readable` in `missing_info`, write the row and carry on: it is a gap, not a failed command (audit 30/10).
      - **Tour operator** (Anex, Odeon, Crystal Bay, Pegas, Selfie): `skills/tour-operators.md`. Rates from `py -m tools.emi to-price --operator <name> …` (Odeon: `--spo` from the voucher). On request → `py -m tools.emi on-request …`: REJECT = CANCEL rows + decline draft, ASK KAREN = `ask-karen`, no row. Anex robot emails: every one gets a reply draft (it goes to reservation@anexvietnam.com by itself).
      - `py -m tools.emi sheet-check emi-work/out/<ref>.json` → fix every line it lists, run it again until `OK`. Warnings: fix them or say why in the run report (not in `notes`: they become the EZFOLIO Notice).
      - `py -m tools.emi sheet-append emi-work/out/<ref>.json` → prints the rows as written: compare with the email.
      - A wrong cell I wrote on a row not yet built → `sheet-update <row> emi-work/out/<ref>-fix.json` (`{"column": "value"}`); it re-checks the whole row. It refuses payment columns, the group code and rows already built (`pdf_link` filled): those are CHANGE rows. It backs the row up and reads it back.
      - If a command refuses, read the reason and fix the JSON. Never write to the sheet any other way. Every `sheet-check` refusal says how to fix it: a blank nationality → from the booking, the passport or the guest's name, else `Vietnam`; a required value the email doesn't give (a CANCEL's group code for a booking on neither sheet) → name the column in `missing_info`. When an edit to the JSON doesn't apply, write the whole file again (`sheet-template` + your values) instead of giving up. Still refused after three tries → leave that email not `done`, go on with the next email, and put it in the report with the refusal line (30/10: three Agoda cancellations refused for a blank nationality and a missing group code stopped the run and left seven other mails untouched).
   4. Inquiry or quote request (no booking yet) → `py -m tools.emi quote …` as in `skills/inquiries-and-quotes.md`, offer only options it marks `AVAILABLE` (the Future Availability sheet; `availability` for the other room types), write the reply from its template with the command's numbers, `py -m tools.emi draft-reply <id> emi-work/out/<sender>-inquiry.txt --kind inquiry`. List every `GAP:` line in the report.
   5. Forward / reply needed → write the text to `emi-work/out/<ref>-<kind>.txt`, then `py -m tools.emi draft-forward <id> <to> <file> --kind forward --ref <ref> --row <N>` or `py -m tools.emi draft-reply <id> <file> --kind <kind> --ref <ref> --row <N>`, with `<N>` the first row `sheet-append` printed for this email (no row written → leave `--row` out). A `NOTE: #n still pending` line → the report says "deny #n, replaced by #m" (audit 30/10). Kind (`skills/inbox-triage.md` "Draft kind"): `request` for a question or special request on an existing booking (then also the front-office forward), `inquiry` only for a price or availability question with no booking yet, `reply` for anything else. An email forwarded in by a colleague (@haya-hotels.com, @palmahotel.vn): reply to the original writer with `--to <their address> --cc <colleague>` (`skills/email-templates.md` "Who the reply goes to"); `draft-reply` refuses to answer a colleague by mistake.
      **A fact I'm not sure of** (not in `hotel-info.md`, the rate files or the email): still the complete best-answer draft, with `[CHECK BEFORE SENDING: <what to check>]` as its first line (bold red in Outlook), and `py -m tools.emi ask-karen <id> "<the question, in Vietnamese>" --ref <ref>` (Tracy's audit, 29/10). Never "we'll check and get back to you". The draft commands refuse a `[…: hotel to confirm]` gap inside the text and Karen's name anywhere in a draft. Replies are reply-all by default.
   6. `py -m tools.emi done <id> <one-line outcome>` — also for noise, so a re-run skips it.
5. Steps 7–9 above (Sent folder, flags, 40-hour reminders): not wired to commands yet. Skip them, and leave them out of the scan report.
6. If any `show` or sheet command failed, **don't** run step 7 (an availability or stop-sales GAP is not a failure): the next run starts from the same point and skips what's already `done`. One email that can't be finished never stops the others: every email in the list gets its turn first.
7. `py -m tools.emi mark-scanned <scan_started>`.
8. Answer with the scan report in the exact shape of `skills/inbox-triage.md` §4: plain lines for Telegram, **no table**. Name every draft by its number (`#12`), as printed by the `draft-*` command for that email, never another email's. Each one already has its Telegram notice, so I don't send another.

## 2. Confirmation drafts — `30 6-22 * * *`
Skills: `confirmation-replies.md`, `email-templates.md`.
1. Read the intake sheet for rows where the build tool has pasted a `pdf_link` and no confirmation has been drafted yet. (Cancellations are answered in job 1.)
2. Open the PDF and check it against the row. Mismatch → flag to Karen, no draft.
3. Changed booking → check the payment columns for the deposit; pick the reminder or no-reminder block.
4. Draft the reply on the agency's thread in their language, PDF attached, deadline as exact time and date in Vietnam time. Leave it in Drafts.
5. Rows waiting on the build tool for more than 4 hours → list for Karen.

Hourly because this is the step the agency is waiting on. It does nothing on a run where no row has changed.

### Job 2 — the commands (confirmation for one row)
1. `py -m tools.emi pdf-fetch <row>` → the PDF behind `pdf_link`, saved, its text printed next to the row. Compare every date, room, rate and total. Mismatch → report to Karen, stop for this booking.
2. Write the confirmation text (`skills/email-templates.md`, sender's language, deposit deadline as exact date, time and "Vietnam time (UTC+7)") to `emi-work/out/<ref>-confirmation.txt`.
3. `py -m tools.emi draft-confirmation <message_id of the agency's email> <row> emi-work/out/<ref>-confirmation.txt` → reply draft on the agency's thread with the PDF attached. It refuses a row with no `pdf_link`, a file that isn't a PDF, and a booking that already has a confirmation draft.
4. Tour operators (`skills/tour-operators.md`): no deposit block. Odeon and Crystal Bay need our invoice first (`py -m tools.emi invoice-data <ref>`; the template isn't connected, so a person makes the PDF — until it is in `emi-work/out/`, report "chờ invoice <ref>"). Odeon: a new email, `--to vietnamreservations@odeontours.com --cc vietnamaccounts@odeontours.com --subject "Odeon Reservation confirmation <ref>" --attach emi-work/out/Invoice_<ref>.pdf`. Report line for Odeon: Confirm on the extranet still to be pressed.

## 3. Payment deadline check — `0 8,15 * * *`
08:00 and 15:00 (Karen, 2026-10-08): early enough that the client can still pay the same day. A 17:00 check is too late to get anything resolved.

Skill: `confirmation-replies.md` → Payment reminders. Templates: `email-templates.md` section 4.
- **08:00:**
  - List every deposit deadline falling today and every balance due today, plus anything already overdue. Check the inbox and the payment columns for each.
  - Balance due tomorrow (check-in is 8 days away) and not seen → draft the balance reminder.
- **15:00:** re-check everything due today. Report to Karen: paid, part-paid, or nothing received. Anything still unpaid is named with its exact deadline so someone can call the agency before the banks close.
- A slip has arrived for a booking with an unsent reminder in Drafts → flag that draft for deletion.
- Deadline passed with nothing received → report to Karen. Nothing is cancelled and no cancellation notice is drafted.

## 4. Daily report to Karen — `30 21 * * *`
One short table:
- New bookings, changes, cancellations logged today
- Drafts still unsent, and how long each has waited (any confirmation draft over 24 hours old gets its deadline updated first). `py -m tools.emi review-list` gives the ones nobody has answered on Telegram.
- Rows with `missing_info`
- Rows waiting on the build tool, and rows it failed
- Payment reminders drafted today, deadlines due tomorrow, and anything overdue
- Anything flagged and not yet answered
Then write the day's log to `memory/YYYY-MM-DD.md`.

## Open before any of this is switched on
- Where it runs (scheduled routine here, or OpenClaw).
- Where the reports land (Telegram, email, or a tab on the intake sheet).
- Sheet write access and draft-with-attachment are untested.
- Job 2 depends on the EZFOLIO build tool being live and on what it writes for cancellations and failures.
