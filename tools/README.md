# tools/ — Emi's host-side code

Python 3.10+. Graph uses only the standard library. Google needs `pip install -r requirements.txt`.

| File | What it does |
|---|---|
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
- Attachments over 3 MB (Graph upload session).
- Reading the Drive confirmations folder and "FUTURE AVAILABILITY" (Drive API; same service account).
- The signal for a cancellation done in EZFOLIO; `precheck confirmations` only sees `pdf_link`.
- Telegram bot.
