# tools/ — Emi's host-side code

Python 3.10+. Graph uses only the standard library. Google needs `pip install -r requirements.txt`.

| File | What it does |
|---|---|
| `emi.py` | The fixed commands the scheduled jobs call (`python -m tools.emi --help`): list new inbox mail, show a thread with attachments, mark handled, move the scan clock, find / append / update sheet rows, save reply / forward drafts, attach a file. Job 1's order is in `schedule.md`. |
| `operator_rates.py` | Prices a tour operator booking from that operator's own contract (`docs/rate-knowledge/<operator>-rates.json`): seasons, holidays, early bird, free nights, child and meal surcharges, Odeon SPO codes; prints the row's rate fields and notes item 6 (`to-price`). |
| `operators.py` | The tour operator procedure (`skills/tour-operators.md`): addresses, steps, the on-request rule (`on-request`), check-out lists (`checkouts`), proforma figures (`invoice-data`). |
| `intake_schema.py` | What each sheet column takes (booking vs room level, required, allowed values, formats) and `check_row`, run by `sheet-check`, `sheet-append` and `sheet-update`. Column instructions, room codes and rules are read live from the sheet (row 2, tabs `Room codes` and `Rules`) by `sheet-schema`. |
| `drive.py` | Downloads a Drive file (the confirmation PDF behind `pdf_link`) with the service account. Needs the Drive API enabled in the GCP project and the file or folder shared with the service account. |
| `attachments.py` | Saves attachments under `EMI_WORK_DIR` (default `emi-work/`) and extracts text: PDF (pypdf), Excel .xlsx (openpyxl), .docx, .csv/.txt. Images are saved for the agent to open. |
| `graph_mail.py` | Outlook for sales@ via Microsoft Graph: read inbox, thread, attachments, Sent, Drafts; create reply / forward / new **drafts**, attach a PDF, tag drafts `Emi`. No send method; `_call` refuses `send`, `sendMail`, `reply`, `replyAll`, `forward`. |
| `intake_sheet.py` | Intake sheet: read rows by header name, find by `booking_ref`, append rows, update single cells. Refuses unknown columns and refuses to write `tracy_status` / `pdf_link` (except `Pending` on a new row). Deletes only `TEST-` rows. |
| `state.py` | JSON state between runs: last scan, Telegram questions `E-001`…, drafts, confirmations, reminders. |
| `precheck.py` | Cheap check before cron jobs 1 and 2. Exit 0 = work, 1 = quiet, 2 = check failed. |
| `acceptance.py` | Acceptance tests 2–7 from `openclaw-setup-brief.md` against the real systems. |
| `config.py` | Settings from environment variables, loaded from `.env` if present (copy `.env.example`). |

## Environment variables

| Variable | Value |
|---|---|
| `EMI_TENANT_ID`, `EMI_CLIENT_ID`, `EMI_CLIENT_SECRET` | App registration with **Mail.Read + Mail.ReadWrite application permissions only**, limited to sales@ by an Exchange application access policy |
| `EMI_GOOGLE_KEYFILE` | Service-account JSON. Share only the intake sheet (Editor) and the two Drive folders (Viewer) |
| `EMI_MAILBOX` | Default `sales@haya-hotels.com` |
| `EMI_AUTH=delegated` | Production without a secret, same as Sunny: `EMI_TENANT_ID` + `EMI_CLIENT_ID`, sign in once as sales@ with a device code (delegated `Mail.ReadWrite`, no `Mail.Send`); refresh token cached in `EMI_TOKEN_CACHE`, mode 600. `acceptance mail-read` fails if the token belongs to any account other than `EMI_MAILBOX`. Do the first sign-in in a terminal: a cron run would sit waiting for the code. |
| `EMI_AUTH=device` | Test mode on a personal Outlook.com mailbox: sign in once with a device code (delegated `Mail.ReadWrite`, no `Mail.Send`), refresh token cached in `EMI_TOKEN_CACHE` (default `.emi-token.json`). Needs only `EMI_CLIENT_ID` from an app registration that allows personal Microsoft accounts and public client flows. |
| `EMI_TEST_SENDER` | Address `acceptance draft-reply` will answer; default `haya@haya-hotels.com` |
| `EMI_SHEET_ID`, `EMI_SHEET_TAB` | Default the v2 intake sheet, tab `Intake` |
| `EMI_STATE_PATH` | Default `emi-state.json` |

## Tests

```bash
python -m unittest discover -s tools/tests -t .   # offline, fake HTTP
python -m tools.acceptance send-blocked           # offline
python -m tools.acceptance mail-read              # real, read-only — then the rest in the order in acceptance.py
```

## Not built yet
- The proforma invoice PDF from the Google Sheets template (`invoice-data` prints the figures; template ID and layout not given).
- Scheduled jobs for the tour operators' daily / Monday accounting emails (`checkouts` gives the list on request).
- Attachments over 3 MB (Graph upload session).
- Reading "FUTURE AVAILABILITY" from Drive. (The confirmation PDF behind `pdf_link` is read by `pdf-fetch`.)
- The signal for a cancellation done in EZFOLIO; `precheck confirmations` only sees `pdf_link`.
- Telegram bot.
