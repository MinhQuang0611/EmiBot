# Emi — scheduled jobs

Drafted by Monica 2026-10-08, times for jobs 1–3 set by Karen the same day. **Nothing here is switched on.** All times are Vietnam time: set the scheduler's timezone to `Asia/Ho_Chi_Minh` (on a server running UTC, subtract 7 hours).

Runs every day including weekends — agencies email on Saturdays and Sundays.

| # | Job | Cron (Vietnam time) | Runs |
|---|---|---|---|
| 1 | Inbox scan + 40-hour deposit reminders | `0 6-22 * * *` | Hourly, 06:00–22:00 (17 a day) |
| 2 | Confirmation drafts | `30 6-22 * * *` | Hourly at :30, 06:30–22:30 (17 a day) |
| 3 | Payment deadline check | `0 8,15 * * *` | 08:00 and 15:00 |
| 4 | Daily report to Karen | `30 21 * * *` | 21:30 |

## 1. Inbox scan + 40-hour deposit reminders — `0 6-22 * * *`
Hourly (Karen, 2026-10-08). The 06:00–22:00 window is Monica's, matched to job 2.
Skills: `inbox-triage.md`, `booking-intake.md`, `department-forwards.md`, `inquiries-and-quotes.md`.
1. Read every email in sales@haya-hotels.com received since the last scan, whole thread and attachments.
2. Classify each one.
3. New / change / cancellation → write or update intake sheet rows. Cancellations are flagged to Karen.
4. Payment slips → fill the payment columns; draft the forward to accountant@palmahotel.vn with the group code.
5. Arrival details, special requests, rooming lists, changes within 3 days of arrival → draft the forward to haya@haya-hotels.com.
6. Inquiries and quote requests → draft the reply.
7. Read the Sent folder: for any draft of mine that was sent, record the real sent time and note any edits as corrections.
8. Flag OTA rates under 1,000,000 VND/room-night, Palma emails, money asks, and anything unclassified.
9. **40-hour deposit reminder.** For every confirmed booking with no deposit seen, count hours since the confirmation was actually sent. 40 hours reached → re-check the inbox and the payment columns, then draft the deposit reminder. At the 22:00 run, also draft it for any booking that will reach 40 hours before 06:00. This lives here, not in job 3, because the 40-hour mark can land at any hour and job 3 only runs twice a day.

### Job 1 — the commands, in order
Run everything from `/data/emi` with `.venv/bin/python` (written `py` below). Use only these commands to reach the mailbox and the sheet; never write your own Python for it. Write your own files (row JSON, draft text) under `emi-work/out/`.

1. `py -m tools.precheck inbox` → prints `quiet` (exit 1): answer `QUIET` and stop. Exit 2: report the error line to Karen and stop.
2. `py -m tools.emi sheet-schema` → every sheet column with its level, required rule, allowed values and the sheet's own instruction, plus the room codes and the Rules tab. Read it once per run; it is the only reference for column names and values. Never guess a column name or a value format.
3. `py -m tools.emi inbox-new` → note the `scan_started=` value; you need it in step 7.
4. For each email listed, oldest first:
   1. `py -m tools.emi show <id>` → the whole thread, with attachments saved and their text printed. Image attachments: open the saved file to read it.
   2. Classify it (`skills/inbox-triage.md`).
   3. Booking → `py -m tools.emi sheet-find <booking_ref>` and `sheet-find <guest surname>`.
      - Not there (new booking) → `py -m tools.emi sheet-template NEW emi-work/out/<ref>.json`. Fill the values: shared columns in `booking`, one `room_lines` entry per room type (copy the entry for each extra type). Don't add or rename keys. Unknown → leave blank; a blank REQUIRED column goes in `missing_info` as `REQUIRED blank: <column> – <reason>`.
      - Change or cancellation of a booking already there → `sheet-template CHANGE` (or `CANCEL`) the same way; per the Rules tab it becomes new rows with the same `booking_ref` and `what_changed` filled.
      - `py -m tools.emi sheet-check emi-work/out/<ref>.json` → fix every line it lists, run it again until `OK`. Warnings: fix them or say why in `notes`.
      - `py -m tools.emi sheet-append emi-work/out/<ref>.json` → prints the rows as written: compare with the email.
      - A wrong cell on an existing row → `sheet-update <row> emi-work/out/<ref>-fix.json` (`{"column": "value"}`); it re-checks the whole row.
      - If a command refuses, read the reason and fix the JSON. Never write to the sheet any other way.
   4. Forward / reply needed → write the text to `emi-work/out/<ref>-<kind>.txt`, then `py -m tools.emi draft-forward <id> <to> <file> --kind forward --ref <ref>` or `py -m tools.emi draft-reply <id> <file> --kind inquiry`.
   5. `py -m tools.emi done <id> <one-line outcome>` — also for noise, so a re-run skips it.
5. Steps 7–9 above (Sent folder, flags, 40-hour reminders): not wired to commands yet; list them in the report as not done.
6. If any `show` or sheet command failed, **don't** run step 7: the next run starts from the same point and skips what's already `done`.
7. `py -m tools.emi mark-scanned <scan_started>`.
8. Answer with the scan report table from `skills/inbox-triage.md` §4.

## 2. Confirmation drafts — `30 6-22 * * *`
Skills: `confirmation-replies.md`, `email-templates.md`.
1. Read the intake sheet for rows where the build tool has pasted a `pdf_link` (or marked a cancellation done) and no confirmation has been drafted yet.
2. Open the PDF and check it against the row. Mismatch → flag to Karen, no draft.
3. Changed booking → check the payment columns for the deposit; pick the reminder or no-reminder block.
4. Draft the reply on the agency's thread in their language, PDF attached, deadline as exact time and date in Vietnam time. Leave it in Drafts.
5. Rows waiting on the build tool for more than 4 hours → list for Karen.

Hourly because this is the step the agency is waiting on. It does nothing on a run where no row has changed.

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
- Drafts still unsent, and how long each has waited (any confirmation draft over 24 hours old gets its deadline updated first)
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
