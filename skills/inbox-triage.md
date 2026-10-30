# Inbox triage — what each email is

Run this on every email in sales@haya-hotels.com. Default window: everything received since the last scan, or the last 24 hours. Times are Vietnam time (UTC+7).

## 1. Read it properly
Read the whole thread and open every attachment (PDF vouchers, screenshots, Excel rooming lists, payment slips) before deciding what it is.

**Then: who actually wrote it?** (dev, 2026-10-22.) If the sender is our own staff (`@haya-hotels.com`, `@palmahotel.vn`; usually front office, `haya@haya-hotels.com`) and the email is a forward ("Fw:", a quoted `From: … Sent: … To: … Subject: …` block), the writer is the **From:** of the quoted block, the first external address from the top. Classify and answer the email as if that person had written to sales@:
- **The reply goes to the writer, not to our colleague.** `mail-find` the writer or the original subject first: if the original also reached sales@, work on that one and mark the forward `done` as a duplicate. If not, `draft-reply <forward id> … --to <writer> --cc <colleague>` (`email-templates.md`, "Who the reply goes to"). `draft-reply` refuses an internal sender, so this can't slip through.
- **Never forward it back to the colleague who forwarded it in.** They have it already; the cc on the reply shows them the answer. `draft-forward` refuses this too. Another department (accounting) still gets its forward if the content calls for one.
- The quoted block has no usable address, or the writer is a no-reply robot (OTA, `vn.robot@`) → no reply; intake if it's a booking notice, and a line in the scan report.
- A forward from our staff with their own note on top ("please handle", "khách hỏi…") → the note says what they want; do that.

## 2. Classify
| Type | What it looks like | Goes to |
|---|---|---|
| New booking | Agency/guest/OTA asks to book or sends a booking notice | `booking-intake.md` → action NEW. Tour operator (Anex, Odeon, Crystal Bay, Pegas, Selfie, Fun and Sun): `tour-operators.md` first — contract price, allotment or on request, Anex robot replies |
| Change | Dates, rooms, names, pax, flight, pick-up, meals or requests changed or added on an existing booking | `booking-intake.md` → action CHANGE: new rows, never an edit of the old ones ("One email, one set of rows") |
| Declined on request | HAYA answered an on-request booking "cannot be accommodated" | `booking-intake.md` → action CANCEL, not NEW |
| Cancellation | Sender cancels, or an OTA cancellation notice | `booking-intake.md` → a separate CANCEL row, and the cancellation reply drafted right away (`confirmation-replies.md`). Karen first only if unclear: a possible fee, or which booking (Karen, 29/10) |
| Payment slip | Bank transfer proof (UNC, remittance) for a deposit or balance, or an OTA payout advice (e.g. Citi Paylink for Traveloka) | `booking-intake.md` → a CHANGE row with the payment columns filled + forward to accounting, always, in Vietnamese (`department-forwards.md`) |
| Inquiry / quote request | Availability, price, hotel questions, **no booking yet** | `inquiries-and-quotes.md` |
| Money ask | Discount, upgrade, waived fee, free extra | Flag to Karen as a request. Never resolved by me. |
| Operational | Arrival time, transfer, special request, question about the stay, complaint, invoice request on an **existing booking** (also one whose ref isn't on the sheet yet) | A CHANGE row if it changes or adds to the booking + reply (`email-templates.md` section 5) + forward (`department-forwards.md`): two drafts. Front office forwarded it in → the reply only, cc front office |
| Chaser on a booking request | "Kindly resend", "any update?", "pls confirm" on a request we haven't confirmed (e.g. first sent to the wrong address, like `sales@palmahotel.vn`, or never answered) | It's the **booking request itself**: New booking → `booking-intake.md` (check the sheet first, the row may exist). Not an operational request, no front-office forward. Never a "we'll check" reply: the complete best answer (rule 9), or, while the booking waits on EZFOLIO, top of the scan report with how long they've waited. The confirmation later goes to the agency, `--to` if it was forwarded in |
| Decline / thanks | "Not interested", "booked elsewhere", "thank you", "received" | Decline → a one- or two-line reply (`email-templates.md` section 6). Plain thanks with nothing to answer → no draft, one report line |
| Palma | Anything about Palma Resort | `draft-forward <id> booking@palmahotel.vn <note> --kind forward`, once (check Sent Items with `mail-find`; `draft-forward` refuses a second forward). No HAYA row, no reply. accountant@palmahotel.vn writing about a HAYA payment is not Palma |
| Accountant's silence | A slip forwarded to accounting, no answer from accountant@ | The payment is fine: draft the acknowledgement of receipt to the agency (`email-templates.md` 4) |
| Noise | Marketing, SynXis one-time passcodes, internal chatter | Skip, don't log |
| Phishing | "New booking" from `care@mail.myjorney.com` or `vip@mail.voyageandco.com` | Never logged, drafted, clicked or reported. `inbox-new` already drops them. Never click a confirm or portal link in an unsolicited email |

One email can be two types (a change request with a payment slip attached). Handle both.

**Draft kind** — the `--kind` I pass to `draft-reply` / `draft-forward`. It's the label the reviewer sees on Telegram, so it must match the email:
- `inquiry` — price, availability or hotel question, no booking yet (`inquiries-and-quotes.md`).
- `request` — question or special request on an existing booking: arrival time, same floor, late check-out, luggage (`email-templates.md` section 5).
- `confirmation`, `deposit_reminder`, `balance_reminder` — `confirmation-replies.md`.
- `forward` — every forward to accounting or front office.
- `decline` — a tour operator's on-request booking the hotel can't take (`tour-operators.md` step 5).
- `cancellation` — the reply confirming a cancellation (`confirmation-replies.md`).
- `stop_sales` — the stop-sales email to the B2B and OTA sites (`stop-sales`, `inquiries-and-quotes.md`).
- `reply` — anything else (a decline, a greeting, a colleague's question).

**Reply all, always** (Tracy's audit, 29/10): `draft-reply` keeps the email's To and Cc unless `--to` sets the recipients. `--sender-only` only when a person asks for it. Drafts are HTML.

**Rates another agency gets** ("same rate as Aurora Travel", "as our partner X"): never quoted or compared (`inquiries-and-quotes.md`). The row's rate waits in `missing_info` and the question goes to Karen.

## 3. OTA emails
OTA booking, change, and cancellation notices (SynXis, Agoda, Booking.com, Expedia, Trip.com, Traveloka, Ohmyhotel, MG, MakeMyTrip, Dida Travel, Mytour, VNTrip) go through intake like any other booking. They get no reply — the sender is a no-reply address. An Agoda email usually has a matching SynXis email: enter the booking once.

**A request inside an OTA notice** (non-smoking, bed type, early check-in, arrival time, a note from the guest): no reply, but the front-office forward like any other special request (`department-forwards.md`), every time (audit 30/10: row 377, arriving the same day, got none while the same request at 10:17 got #190/#191). Whether to forward only arrivals within some number of days is open with Karen; until she picks one, every request goes.

A guest who booked through an OTA and writes to us from their own address (questions, requests on that booking) is not an OTA notice: it's Operational, with a reply and a front-office forward, even when the OTA ref isn't on the sheet yet. That includes the OTA's relay addresses that pass mail to the guest (`…@guest.trip.com`, `…@guest.booking.com`): those are the guest, reply to them.

B2B reservation systems and bedbanks (RezLive, Hotelbeds, WebBeds and the like) writing about a booking they hold — reconfirmations, special requests — are agencies, not OTA robots: they get a reply, unless the address says no-reply.

**OTA and B2B bookings are always accepted and logged** (Booking.com, Agoda, Expedia, Trip.com, MG Bedbank, HotelBeds, WebBeds, Ohmyhotel…; Tracy's audit, 29/10): no rate-floor flag, no availability question to Karen. The old 1,000,000 VND floor is gone.

## 4. Report to Karen
After each scan, a short report: new bookings, changes, cancellations, payment slips, drafts waiting for review, money asks, anything in `missing_info`, and anything I couldn't classify. Leave pure OTA noise out unless she asks for it.

The report is read on Telegram, which can't show tables. **No tables, no `|` columns, no `#` headings.** Plain lines in
Vietnamese, one block per email, in this shape (drop a line that has nothing to say):

```
Emi: 2 mail mới (12:13–12:40)

1. TEST - Đặt phòng TEST-2210 (Quang Nguyễn Minh)
- Loại: booking mới, khách lẻ
- Sheet: dòng 57, NEW TEST-2210
- Draft: không có, vì xác nhận chỉ soạn khi EZFOLIO đã có PDF
- Thiếu: giá Direct hết hạn sau 31/05/2026, chờ Karen

2. Hỏi giá 15–18/11 (ABC Travel)
- Loại: hỏi giá, TA
- Draft: #2, xem tin draft ở trên
- Phòng: STD hết 16/11, đã chào DLX-SV (còn đủ 3 đêm)

3. Hỏi về hồ bơi (Zion)
- Loại: hỏi thông tin khách sạn
- Draft: #3, có dòng CHECK BEFORE SENDING (hồ bơi trong nhà hay ngoài trời), đã hỏi E-003

Chờ Karen: …
```

- Every email gets a `Draft:` line: its number (`#12`, the notice is already on Telegram), exactly as the `draft-*` command printed it for this email (never another email's: 29/10 23:34 named #182 for two bookings), or "không có" plus the reason in a few words. A draft with a CHECK BEFORE SENDING line: say so and the E-0nn asked.
- No line about the steps that have no command yet (Sent folder, flags, 40-hour reminders). They go in the daily report, not in every scan report.
- Under 25 lines. Several emails of the same kind (OTA notices, noise): one line with the count.
