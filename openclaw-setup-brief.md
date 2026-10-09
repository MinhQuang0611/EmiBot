# Emi — OpenClaw setup brief

Written 2026-10-08. For whoever stands Emi up on OpenClaw: Karen, the AI intern, or a helper AI working with one of them.

## Goal

Run **Emi**, HAYA Hotel Phu Quoc's reservations email agent, on an always-on OpenClaw host so that:

1. She works the hotel sales mailbox on a schedule (4 cron jobs).
2. She can ask Karen questions on **Telegram** and act on the answers.
3. She saves every outgoing email as a **draft**. A person presses send. Emi must not be able to send.

Nothing in this brief has been set up yet. Emi exists today as files only.

---

## What Emi does, in one table

| Step | What happens | System touched |
|---|---|---|
| 1 | Reads new email in `sales@haya-hotels.com`, with attachments | Outlook (read) |
| 2 | Writes new / changed / cancelled bookings to the intake sheet | Google Sheets (read + write) |
| 3 | A separate tool builds the booking in EZFOLIO and pastes a PDF link on the row | Not Emi |
| 4 | Checks the PDF, drafts the confirmation on the agency's thread with the PDF attached | Drive (read), Outlook (create draft) |
| 5 | Drafts forwards to accounting and front office | Outlook (create draft) |
| 6 | Drafts payment reminders at 40 hours (deposit) and before the balance is due | Outlook (create draft) |
| 7 | Asks Karen on Telegram when she needs a decision; reports what's waiting | Telegram |

Emi never touches EZFOLIO, never handles Palma, and never uses Zalo or WhatsApp.

---

## Environment

| Item | Value |
|---|---|
| Agent | Emi — HAYA reservations email |
| Host | Hostinger OpenClaw. See "Decision 1" below. |
| OpenClaw version | 2026.9.3 or later (same floor as Wanda and Sunny) |
| Human channel | Telegram only, a new bot for Emi |
| Zalo / WhatsApp | **None.** Do not install `zalouser` for Emi. |
| Mailbox | `sales@haya-hotels.com` (Microsoft 365 / Outlook) |
| Intake sheet | "HAYA Ezfolio Booking Intake v2", ID `16pFhmPB6sQB7Bu8S61qq094cvq8Ie1OcRGCeC-CR440`, tab `Intake`, row 2 = column instructions |
| Confirmation PDFs | Drive folder `1UDpbCxxj2EiIy_YSWK5CI4JRECVu-A3P` |
| Availability and price PDF | Drive folder named "FUTURE AVAILABILITY" (always the newest file, never a fixed file ID) |
| Accounting address | `accountant@palmahotel.vn` |
| Front office address | `haya@haya-hotels.com` |
| Timezone | `Asia/Ho_Chi_Minh` (UTC+7) |
| Source copy of Emi's files | `/Users/karennguyen/Desktop/AI AGENTS/Emi/` on Karen's Mac |

---

## Decisions Karen needs to make first

### Decision 1 — which host
| Option | For | Against |
|---|---|---|
| **A. New Hostinger OpenClaw app for Emi** (recommended) | Same pattern as Wanda and Sunny, one agent per app. A restart or update on Sunny's host can't take Emi down. No Zalo plugin on this host at all. | Another monthly Hostinger charge. This is spend, so it needs Karen's OK. |
| B. Second agent on Sunny's existing host | No new cost. Sunny's host already has a mail tool for this mailbox. | Sunny's host runs `zalouser`; Hostinger page Restart is known to drop plugins from `plugins.allow`. Two agents sharing one mailbox tool is how drafts get crossed. |

### Decision 2 — the Telegram bot's name
A new bot, separate from `@hayacs_bot` (Sunny). Karen picks the name.

### Decision 3 — who administers Microsoft 365 for haya-hotels.com
Someone with admin rights has to approve the mailbox permissions in step 3. If that isn't Karen, name the person.

### Decision 4 — who besides Karen presses send
They work in Outlook, not Telegram. Emi only needs their names so her reports can say who a draft is waiting on.

---

## Setup steps, in order

### Step 1 — Load Emi's files
Copy from the source folder on Karen's Mac. Sunny's live host uses the file names `Agent.md`, `Memory.md`, `Soul.md`, `User.md`; check the host's own convention and rename to match.

| Source file | Purpose |
|---|---|
| `SOUL.md` | Character and what she never does |
| `IDENTITY.md` | Name, role, vibe |
| `USER.md` | About Karen |
| `AGENTS.md` | Hard rules (12 of them) |
| `MEMORY.md` | Key IDs, Karen's decisions, open items |
| `skills/inbox-triage.md` | Classifying email |
| `skills/booking-intake.md` | Email to intake rows |
| `skills/department-forwards.md` | Accounting and front office forwards |
| `skills/confirmation-replies.md` | When to draft a confirmation; payment reminder rules |
| `skills/email-templates.md` | The approved wording, Vietnamese and English |
| `skills/inquiries-and-quotes.md` | Inquiry and quote replies |
| `schedule.md` | The four cron jobs in detail |

Also copy the `anti-ai-slop` skill (`/Users/karennguyen/Desktop/anti-ai-slop-SKILL.md`); three of Emi's skills call it.

Do not copy `CLAUDE.md` — it's a loader for Claude Code only.

**Two lines in the files point at tools that exist only in Karen's Claude Code workspace.** Fix them on the host copy:
- `MEMORY.md` → "Infrastructure": replace the Zapier connector note with the real mail and Google tools set up below.
- Any mention of "this workspace" means Karen's Mac, not the host.

### Step 2 — Telegram
1. Create the bot in BotFather. Add the token to the host.
2. Confirm `telegram` is in `plugins.allow`:
   ```bash
   openclaw config get plugins.allow
   ```
3. Restrict the bot to Karen's Telegram user ID only. Nobody else may talk to Emi.
4. Probe:
   ```bash
   openclaw channels status --probe
   ```
   Success: Telegram shows **works**.

Known issue from Sunny's host: a Telegram **polling conflict** happens when two processes poll the same bot token. One bot token, one agent.

### Step 3 — Mailbox access (Microsoft Graph)
Emi needs to read mail and create drafts. **She must not be granted permission to send.**

| Permission | Grant? | Why |
|---|---|---|
| `Mail.Read` | Yes | Read inbox, Sent folder, attachments |
| `Mail.ReadWrite` | Yes | Create and update drafts, set a category on her drafts |
| `Mail.Send` | **No** | Karen's rule: a person presses send on all email. Leaving this permission out makes that a property of the system instead of a promise in a prompt. |

Graph calls Emi's mail tool needs:

| Job | Call |
|---|---|
| List new inbox mail | `GET /me/mailFolders/inbox/messages` with `$filter=receivedDateTime ge …` |
| Read one message as text | `GET /me/messages/{id}` with header `Prefer: outlook.body-content-type="text"` |
| Read attachments | `GET /me/messages/{id}/attachments` |
| Draft a reply on the thread | `POST /me/messages/{id}/createReply`, then `PATCH` the draft body |
| Draft a forward | `POST /me/messages/{id}/createForward`, then `PATCH` |
| Attach the PDF to a draft | `POST /me/messages/{draftId}/attachments` |
| Tag her own drafts | `PATCH /me/messages/{draftId}` with `categories: ["Emi"]` |
| List drafts still unsent | `GET /me/mailFolders/drafts/messages` |
| See what was actually sent, and when | `GET /me/mailFolders/sentitems/messages` |

The tool must have **no** call to `/sendMail`, `/send`, or `reply` / `forward` (the non-`create` versions send immediately).

Sunny's host has `tools/sunny_graph_mail.py` for this same mailbox. It can be the starting point, but read it first: if it has a send function, Emi's copy must not.

Reading the Sent folder through Graph was tested on 2026-10-08 from Karen's Mac (through Zapier) and works. Creating a draft with an attachment has **not** been tested anywhere yet.

### Step 4 — Google access
Use a Google service account, the same way Wanda's host does. Share only these three things with the service account's email address:

| Resource | Access |
|---|---|
| Intake sheet `16pFhmPB6sQB7Bu8S61qq094cvq8Ie1OcRGCeC-CR440` | Editor |
| Confirmations folder `1UDpbCxxj2EiIy_YSWK5CI4JRECVu-A3P` | Viewer |
| "FUTURE AVAILABILITY" folder | Viewer |

Do not share the whole Drive. The hotel's Google accounts hold payroll, timesheets, and the OTA login mastersheet; Emi needs none of it.

### Step 5 — Where Emi keeps track between runs
Each run starts fresh, so she needs a small state store on the host (a JSON file is enough):

- Time of the last inbox scan
- Open questions to Karen, by ID
- Every draft she created: message ID, booking, type, time drafted
- Every confirmation sent: real sent time, deposit deadline, balance deadline
- Reminders already drafted, so each deadline gets one

Her drafts are also tagged with the Outlook category `Emi`, so she can tell her own drafts from anyone else's in the Drafts folder.

**Do not add columns to the intake sheet for this.** The sheet's columns are a contract with the EZFOLIO build tool.

### Step 6 — Cron jobs
Full detail for each job is in `schedule.md`. Use whatever scheduler the host already uses for Wanda's 07:30 forecast.

| # | Job | Vietnam time | If the host runs UTC |
|---|---|---|---|
| 1 | Inbox scan + 40-hour deposit reminders | `0 6-22 * * *` | `0 23,0-15 * * *` |
| 2 | Confirmation drafts | `30 6-22 * * *` | `30 23,0-15 * * *` |
| 3 | Payment deadline check | `0 8,15 * * *` | `0 1,8 * * *` |
| 4 | Daily report to Karen | `30 21 * * *` | `30 14 * * *` |

**Keep quiet runs cheap.** Jobs 1 and 2 fire 34 times a day and most runs will find nothing. Each job should first make one cheap check (any new mail since the last scan? any row with a new PDF link?) and stop there if the answer is no, before the agent loads its skills.

### Step 7 — Telegram conversation rules
Emi messages Karen when she needs a decision. Each question:

- Carries an ID: `E-001`, `E-002`, …
- States the booking, the ask, the numbers, and what Emi would draft for each answer.
- Is answered by ID: "E-014 yes", "E-014 offer the Quadruple instead".
- A bare "yes" is accepted only when exactly one question is open. Otherwise Emi asks which one.

What she asks about:

| Situation | Example |
|---|---|
| Reduced rate, upgrade, waived fee, free extra | "E-014 Uma Travel asks 1,800,000 instead of 2,000,000 for DLX-SV, 12–17 Nov. Decline and hold rate, or approve?" |
| Cancellation request | Needs Karen's OK before anything is cancelled |
| Rate in the email doesn't match the rate table | Both numbers shown |
| Missing info she can't find in the thread | The exact gap |
| Unsent payment reminder close to its deadline | Booking and hours left |
| Anything she failed at three times | What she tried |

Karen's answer tells Emi what to **draft**. It is never permission to send. The draft still goes to the Drafts folder.

---

## Acceptance tests, in order

Stop at the first failure and fix it before moving on.

| # | Test | Pass means |
|---|---|---|
| 1 | Telegram: Karen sends "hello" | Emi replies in the same chat |
| 2 | Read the 5 newest inbox emails and name sender and subject | Matches Outlook |
| 3 | Open one email with a PDF attachment and state what the PDF says | Content is right |
| 4 | Send a test email to the sales mailbox from `haya@haya-hotels.com`. Emi drafts a reply on that thread. | Draft appears in Drafts, on the thread, tagged `Emi`, **not sent** |
| 5 | Attach a PDF from the confirmations folder to that draft | Attachment opens |
| 6 | Tell Emi to send the test draft | She refuses, and the mail tool has no way to do it |
| 7 | Write one row to the intake sheet with `booking_ref = TEST-EMI`, then delete it | Row appears with the right columns, then is gone |
| 8 | Read the newest file in "FUTURE AVAILABILITY" and state its date | Matches Drive |
| 9 | One real agency booking email, end to end | Row written, PDF link appears from the build tool, confirmation drafted from the approved template |
| 10 | Run the cron jobs for one full day with Karen watching Telegram | Reports arrive on time; quiet runs stay quiet |

For test 4, do not use Karen's personal Gmail. It is off-limits for hotel work.

---

## Rollout

| Phase | What's on | How long |
|---|---|---|
| 1 | Reading, intake rows, Telegram questions and reports. **No drafts.** | Until Karen has checked about 10 intake rows against their emails |
| 2 | Drafts on: confirmations, forwards, inquiries, reminders | Ongoing |

Before phase 1: the live Sunny must be reconfigured so she no longer works email, and Tracy (Grokbot) must not be scanning the inbox at the same time. Two agents on one mailbox is the main way this goes wrong.

---

## Do not

- Grant `Mail.Send`, or add any send call to the mail tool.
- Install `zalouser` or WhatsApp for Emi.
- Share the whole Google Drive with the service account.
- Add or rename columns on the intake sheet.
- Give Emi the EZFOLIO login.
- Let Emi handle anything from `booking@palmahotel.vn` or about Palma.
- Use the Hostinger page **Restart** button when avoidable. Prefer `openclaw gateway restart`, then re-check `openclaw config get plugins.allow`.
- Edit Emi's rules only on the host. Change the source copy on Karen's Mac first, then re-copy. Sunny's live files drifted into contradicting rules because changes were made on the server and never reconciled.

---

## Known unknowns

1. **Draft with attachment through Graph** — standard API, untested here.
2. **Scheduler syntax on this OpenClaw version** — not written in this brief; copy the mechanism Wanda's host uses.
3. **The EZFOLIO build tool** — not built yet. Emi's job 2 waits on it. Still to define: what the tool writes on the row for a cancellation (no PDF), and for a row it failed to build.
4. **Which Graph auth flow** the host supports for a single mailbox (delegated sign-in as the sales mailbox, or an app registration scoped to that one mailbox). Either works; app-wide access to every mailbox in the company is more than Emi needs.
5. **Vietnamese payment slips as photos** — whether Emi's model on the host can read an image attachment. If it can't, slips are forwarded to accounting unread and the amount is left blank.
