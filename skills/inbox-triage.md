# Inbox triage — what each email is

Run this on every email in sales@haya-hotels.com. Default window: everything received since the last scan, or the last 24 hours. Times are Vietnam time (UTC+7).

## 1. Read it properly
Read the whole thread and open every attachment (PDF vouchers, screenshots, Excel rooming lists, payment slips) before deciding what it is.

## 2. Classify
| Type | What it looks like | Goes to |
|---|---|---|
| New booking | Agency/guest/OTA asks to book or sends a booking notice | `booking-intake.md` → action NEW |
| Change | Dates, rooms, names, pax, or requests changed on an existing booking | `booking-intake.md` → action CHANGE |
| Cancellation | Sender cancels, or an OTA cancellation notice | `booking-intake.md` → action CANCEL, and flag to Karen |
| Payment slip | Bank transfer proof for a deposit or balance | `booking-intake.md` payment columns + `department-forwards.md` (accounting) |
| Inquiry / quote request | Availability, price, hotel questions, no commitment yet | `inquiries-and-quotes.md` |
| Money ask | Discount, upgrade, waived fee, free extra | Flag to Karen as a request. Never resolved by me. |
| Operational | Arrival time, transfer, special request, complaint, invoice request on an existing booking | Update the row if it changes the booking + `department-forwards.md` |
| Palma | Anything about Palma Resort | Flag to Karen. Not mine. |
| Noise | Marketing, SynXis one-time passcodes, internal chatter | Skip, don't log |

One email can be two types (a change request with a payment slip attached). Handle both.

## 3. OTA emails
OTA booking, change, and cancellation notices (SynXis, Agoda, Booking.com, Expedia, Trip.com, Traveloka, Ohmyhotel, MG, MakeMyTrip, Dida Travel, Mytour, VNTrip) go through intake like any other booking. They get no reply — the sender is a no-reply address. An Agoda email usually has a matching SynXis email: enter the booking once.

Any OTA rate under **1,000,000 VND per room-night** is flagged to Karen the same day as a likely promotion mistake.

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
- Cần kiểm tra: tình trạng phòng (chưa nối file FUTURE AVAILABILITY)

Chờ Karen: …
```

- Every email gets a `Draft:` line: its number (`#12`, the notice is already on Telegram) or "không có" plus the reason in a few words.
- No line about the steps that have no command yet (Sent folder, flags, 40-hour reminders). They go in the daily report, not in every scan report.
- Under 25 lines. Several emails of the same kind (OTA notices, noise): one line with the count.
