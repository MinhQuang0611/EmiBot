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
After each scan, one short table: new bookings, changes, cancellations, payment slips, drafts waiting in the Drafts folder with how long each has been there, money asks, anything in `missing_info`, and anything I couldn't classify. Leave pure OTA noise out of the pending list unless she asks for it.
