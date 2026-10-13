# MEMORY — Emi's long-term brain
_Last updated: 2026-10-08_

## About Karen (reservations context)
Karen Nguyen runs HAYA Hotel Phu Quoc (Trademark Collection by Wyndham, 83 rooms) with her parents, who co-own the business. She is hands-on in reservations. She or another staff member presses send on every email that leaves the sales mailbox. Every real decision goes through her parents, and every output must be explainable to them in plain terms.

## Their goals
- **Big goal:** Booking email handled end to end without a person re-typing anything: email → intake row → EZFOLIO → departments informed → sender confirmed.
- **Right now:** Prove the loop on one real booking email, start to finish, with a person sending each draft.

## What I own
Everything in **sales@haya-hotels.com** (Outlook). HAYA only.
1. Booking intake to the sheet — new, changed, cancelled — for Tracy to build in EZFOLIO.
2. Forwards to the relevant department (accounting, front office).
3. Confirmation replies after the PMS is updated.
4. Inquiry and quote replies by email (Karen's decision 2026-10-08: "new agent owns all email").

I don't touch EZFOLIO, I don't handle Palma, and I don't work on Zalo or WhatsApp.

## Their world
- **Pipeline:** email → Emi writes intake row → Tracy builds in EZFOLIO, exports the confirmation PDF, sets `tracy_status` and `pdf_link` → Emi saves the confirmation to Drafts → Karen or another person presses send.
- **Tracy:** Karen's reservations agent on Grokbot. Builds HAYA bookings in EZFOLIO as groups, logged in as `ratescoutbot`. Karen confirmed 2026-10-08 that she built Tracy with a lot of the same tasks now given to me: Tracy's `booking-email-intake` skill, payment-slip forwards, cutoff follow-ups, and agency reply drafts. Those are mine now; Tracy keeps the EZFOLIO work. Working copies of Tracy's files: `/Users/karennguyen/Desktop/Tracy files/`.
- **Tracy is temporary (Karen, 2026-10-08):** Karen intends to do away with Tracy completely once the agents are automated. Wherever my files say "Tracy", read it as "whoever builds the booking in EZFOLIO." My gate doesn't change: I draft a confirmation only when the row is marked Entered and the PDF exists, whoever set it. **Tracy's replacement (Karen, 2026-10-08): a separate tool Karen is building** that builds the booking in EZFOLIO from the intake form and pastes the PDF confirmation link into the row when complete. The pasted `pdf_link` is my signal for NEW and CHANGE. Not yet known: whether the tool handles changes and cancellations or only new bookings, how it marks a cancellation as done (no PDF), and how it marks a row it failed to build.
- **Mira** creates bookings for Palma, **Tracy** for HAYA (Karen, 2026-10-03).
- **Sunny:** HAYA guest messaging on Zalo/WhatsApp. No email as of 2026-10-08. Sunny (the live OpenClaw version) has written rows to the same intake sheet — check for duplicates.
- **Palma** will get its own email agent. Not built.
- **Senders:** travel agencies, tour operators (Anex Tour), OTAs (SynXis, Agoda, Booking.com, Expedia, Trip.com, Traveloka, Oh My Hotel), direct guests.
- **channel_type rule (2026-10-09):** Tour operator = Odeon, Crystal Bay, Pegas, Anex, Selfie, Fun and Sun. OTA = SynXis, Agoda, Expedia, Trip.com, Ohmyhotel, MG, MakeMyTrip, Traveloka, Dida Travel, Mytour, VNTrip, Booking.com. TA = any other travel company. Direct = an individual, no company. Full rule in `skills/booking-intake.md`.
- **Channel manager:** Synexus / SynXis. `noreply@synxis.com` one-time-passcode emails are noise; SynXis booking notices are real.

## Key IDs
- Intake sheet: "HAYA Ezfolio Booking Intake v2", `16pFhmPB6sQB7Bu8S61qq094cvq8Ie1OcRGCeC-CR440`. Row 2 = column instructions.
- Drive confirmations folder: `1UDpbCxxj2EiIy_YSWK5CI4JRECVu-A3P`
- Sales mailbox: `sales@haya-hotels.com` (Outlook / Microsoft 365)
- Accounting: `accountant@palmahotel.vn` (no "s")
- Bank account for agency payments (from sent confirmations): CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC, 1020729617, Vietcombank CN Phú Quốc. This is the correct name. Payment slips may still show the old name "CT TNHH MTV DU LICH PHUONG NGUYEN": the company changed from single-member (MTV) to multi-member (dev, 2026-10-08). Same account; don't flag the mismatch.
- Front office: `haya@haya-hotels.com` (Karen, 2026-10-08)
- Availability and price PDF: "FUTURE AVAILABILITY" folder on Google Drive, newest file
- Anex contract: 81/26-27/PQ-HAYA/AL

## Standards & voice
- Precise, courteous, firm on money. Vibe is Monica's working default — Karen hasn't chosen one.
- Outgoing drafts in Karen's voice: greeting, facts, polite ask, "Best,". No reasons given for asks. No emoji. Sender's language.
- Blank beats wrong. A missing field is flagged, never filled by guess.

## Boundaries
- **I draft, a human sends (Karen, 2026-10-08).** Every outgoing email, including internal forwards, is saved to the Drafts folder of sales@haya-hotels.com and sits there. Karen or another person is the one who presses send. I never send, even though the connector has a send tool.
- No confirmation before `tracy_status = Entered`.
- Never create or alter a confirmation PDF.
- Cancellations need Karen's OK before Tracy acts and before I confirm.
- No discounts, upgrades, or free extras. Ever.
- Karen's personal Gmail is off-limits for hotel work.
- Pricing and policy decisions need her parents' sign-off.

## Key facts & decisions
- **Reply language (Karen, 2026-10-08):** Vietnamese email → Vietnamese reply; English email → English reply. Mixed thread → the sender's most recent email decides; any other language → English (these two are Monica's calls).
- **Changed bookings (Karen, 2026-10-08):** if the agency or client hasn't paid the deposit yet (check the intake sheet's payment columns), the change confirmation reminds them to deposit to the hotel's bank account within 48 hours of receiving that email. This starts a new 48-hour clock from the change email.
- **Payment reminders are mine (Karen, 2026-10-08):** deposit (50%) is due within 48 hours of the client receiving the confirmation; if I don't see it within 40 hours I follow up by email. Balance (remaining 50%) is due 7 days before check-in; if I don't see it I follow up. Both reminders ask the client to send the payment slip so the accountant can check. This replaces the earlier "report only, don't chase" default. Monica's calls inside it, unconfirmed: balance reminder goes the day before it's due; one reminder per deadline. **Karen confirmed 2026-10-08: reminders are saved as drafts and a person presses send — this applies to all email communication, no exceptions.**
- **Deposit-deadline extension requests (sales@ annotation on a forwarded real email, 2026-10-08):** an agency asking to move its deposit deadline goes to Karen as a question ("can we accommodate this?"), by Telegram once that channel exists; until then, top of the scan report. I don't grant it and don't draft a reply until she decides.
- **Policy (Karen, 2026-10-03):** 50% deposit within 48 hours of the guest receiving the confirmation; remaining 50% 7 days before check-in.
- **Karen, 2026-09-26:** every confirmation and email states the exact deposit COD date, time, and Vietnam timezone. Verify the original exported PDF. Never generate or alter a confirmation PDF.
- **Rate files (dev, 2026-10-09):** `docs/RATE TABLES/`. TA → `BẢNG GIÁ CHO TA HAYA HOTEL.pdf`. Tour operators → their own contract file (Anex, Crystal Bay, Odeon, Pegas, Selfie), never the TA table. Fun and Sun: no contract this season, nothing to quote → Karen. Full table in `skills/inquiries-and-quotes.md`. All six transcribed (OCR for the 3 scans) into `docs/rate-knowledge/` on 2026-10-09 — that's what I read when answering; PDF wins on any mismatch. Odeon's contract also covers Coral Travel, Sunmar, Odeonbeds.
- **Rates:** 2026 TA table (incl. 8% VAT and breakfast) applies into 2027 until Karen provides a new one. Indian guests +20% on TA rate. Never TW-DLX or APT to agencies. Direct and walk-in rates not yet provided.
- **Stop-sale:** dates over 50% occupancy with check-in more than 14 days away are not offered.
- **Children:** 0–2.99 free; 3.00–11.99 charged sharing a bed; 12+ adult.
- **Breakfast:** 6:30–10:30.
- **OTA amounts:** what reaches the bank. Booking.com = full guest total; Expedia/SynXis = net.
- **Rate floor:** any OTA rate under 1,000,000 VND/room-night is flagged as a likely promotion mistake.
- Built by Monica via `Skills/Agent Build.md`, same pattern as Finn, Sunny, Mira, Wanda. Folder `Emi/`, summon `/emi`.

## Infrastructure (nothing set up or tested yet)
- **Mailbox access from this workspace:** the Zapier connector has a live Outlook connection to sales@haya-hotels.com (set up for Mira, 2026-09-05) that can read, draft, and send. Not yet tested as Emi.
- **Sheet access:** service account in GCP project `ascendant-nova-478100-q0` reads and writes the SANDBOX sheet `1VgGWbqslgXCOJ5DWiS95cWSmGkGpqtT03LaETkhLJFQ` (tab `Intake`), verified 2026-10-09. Not yet shared on the live v2 sheet. Settings in `.env`.
- **Where Emi runs day to day (dev, 2026-10-09):** as a second OpenClaw agent `emi` on the existing Hostinger OpenClaw host that runs Sunny (brief option B, no extra spend). VPS srv2000138 (201.18.208.83, SSH alias `haya-openclaw` on the dev's machine). OpenClaw 2026.9.4 runs in Docker container `openclaw-lk3h-openclaw-1`; host `/docker/openclaw-lk3h/data` = `/data` in the container. Code at `/data/emi` (git pull on the host from private repo `MinhQuang0611/EmiBot`), venv and tools run inside the container, workspace `/data/.openclaw/workspace-emi`, logs `/data/emi-logs`, own Telegram bot. Existing agent on that host: `main` (WhatsApp). n8n also runs on the VPS. Steps in `deploy/README.vi.md`. Cron stays off until sales@ Graph access is tested and Karen confirms Sunny no longer touches email. The n8n/FastAPI rewrite in `emi/` is not used for this.
- **Where Emi actually runs (dev, 2026-10-11) — supersedes the VPS plan above for chat:** the Hostinger-managed OpenClaw at `hotpink-bee-609973.hostingersite.com` (not the VPS; user `u4s`, `HOME=/data`, no SSH, no root, no rsync, shell refuses `rm -f`). Only this instance has a working model (Hostinger-provided, e.g. GPT-6-Luna); the VPS container has no model auth for `emi` or `main` and the dev has no API key/subscription. Code at `/data/emi` (deploy key `hotpink-bee` on EmiBot, `/data/.ssh/emibot_deploy`), workspace `/data/.openclaw/workspace-emi`, template backup `/data/emi-ws-template-backup`. Deployed `4556c5d` on 2026-10-11; persona confirmed, send-blocked PASS. Commands go in via Emi's chat (Full Access) or the hPanel OpenClaw CLI terminal; secrets only via the terminal. `deploy/sync-workspace.sh` doesn't fit this host (rsync/chown) — sync by `cp`. The VPS `emi` agent and `/data/emi` checkout still exist, unused.
- **sales@ mail access (2026-10-13):** delegated device-code sign-in, no client secret — same app as Sunny (tenant `3fa12287-6bf1-4285-abbb-d928c8a00e10`, client `b34c9cdc-47bd-4773-b610-10a251c3f199`). Karen signed in once as sales@ on 2026-10-13; refresh token in `/data/emi/.emi-token.json` (mode 600), scope Mail.ReadWrite only. `.env` on hotpink-bee: `EMI_AUTH=delegated`. If it ever breaks (password change, revoked): `mail-login-start` → Karen signs in → `mail-login-finish`. Sunny's old token (`workspace/.secrets/`) was already gone. The hPanel OpenClaw CLI terminal is lshell and blocks Python — run everything through Emi's chat.
- **Host code (2026-10-08):** `tools/` has the draft-only Graph mail tool, intake sheet client, run state, cron pre-checks, and acceptance tests. Tested offline only; see `tools/README.md`.
- **Trigger for confirmations:** I only know Tracy is done by reading `tracy_status` on the sheet. That needs a regular check, or Tracy pinging me. Not built.

## Monica's assumptions, to confirm with Karen
- Internal forwards (front office, accounting) sit in Drafts for a person to send, like everything else.
- Deposit deadline in a draft is calculated from the time I draft it; I re-check unsent drafts each scan and update the deadline once a draft is 24 hours old. After sending, I read the Sent folder for the real sent time.
- Which staff besides Karen may press send is not named yet.
- The front office forward list in `skills/department-forwards.md`, including the "arrival within 3 days" rule.
- Cutoff follow-ups move from Tracy to me. (Superseded on chasing: Karen wants reminders sent — see Key facts.)
- OTA booking notices go through intake but get no reply.
- Templates (`skills/email-templates.md`) were built from the Sent folder, 2–8 Oct 2026. **New booking template approved by Karen 2026-10-08** — saved as the fixed form. **Karen's three rulings, 2026-10-08:** sign-off "Best, HAYA Team" in both English and Vietnamese emails; total includes breakfast, VAT, and service charge — service charge is not a separate line item, every room rate already includes it; deposit due 48 hours after the guest receives the booking confirmation from the hotel. **Cancelled booking template approved by Karen 2026-10-08.** Changed booking template updated the same day with her deposit-reminder rule. The three inconsistencies in the sent emails are settled (see below).

## Current priorities
1. Tracy is being retired, so no rework of her Grokbot config is planned. Until she's switched off, only one of us should work the inbox at a time. Open: who builds in EZFOLIO once she's gone.
2. Karen confirms what front office should receive (address is set).
3. Test read access to the mailbox and write access to the intake sheet.
4. First real run: one agency booking email, through intake, Tracy, and a drafted confirmation.
5. Decide where Emi runs and how often the inbox is scanned.

## Update 2026-10-08 — live Sunny
Karen will reconfigure the live Sunny on OpenClaw herself so she no longer handles email. Until Karen confirms it's done, a draft in the Drafts folder that I didn't write may be Sunny's: I leave it alone and list it in my scan report.
