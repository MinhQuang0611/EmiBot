# Department forwards — who needs to see what

Forwards go to accounting (payment slips, invoices, refunds), the company's VAT address and Palma. Front office gets none: it reads the booking's EZFOLIO notes (dev, 2026-10-30).

Every forward is saved to the Drafts folder for a person to send. I never send it myself. Forward the original email with its attachments intact; add a short note on top, never edit the original below it.

**Once per email** (Tracy's audit, 29/10): before a forward, `mail-find` the subject or ref to see whether it is already in Sent Items; `draft-forward` itself refuses a second forward of the same email to the same address (unless the first draft was denied). Never Karen's name in the note.

**The note on top, in Karen's style (dev, 2026-10-22):** Vietnamese, labels and bullets, nothing else. The colleague reading it should know in five seconds which booking, when, and what to do, without opening the email below. Accounting gets the block in `email-templates.md` 4c (mã đoàn on the first line, then total, 50%, the amount on the slip and whether it is short, reference numbers, invoice details — as HAYA's own forward for An0109 on 15/10/2026, subject "Fw: … – UNC cọc #[mã đoàn]"). No reasons, no "Dear team", no sign-off paragraph.
- **Never forward an email back to the colleague who forwarded it to us** (sender `haya@haya-hotels.com` → nothing back to haya@). They have it; the reply to the guest or agency cc's them (`email-templates.md`, "Who the reply goes to"). `draft-forward` refuses it.

## Accounting — `accountant@palmahotel.vn` (no "s")
| Forward | Note on top must include |
|---|---|
| Every HAYA payment slip, UNC, remittance, and OTA payout advice (e.g. Citi Paylink for Traveloka) | EZFOLIO **group code** (or "chưa có mã đoàn"), agency/guest, amount on the slip, which payment it is (deposit / balance) |
| Red invoice (VAT) requests and company invoice details | Group code, company name, tax code, address as given |
| Refund requests after a cancellation | Group code, amount requested, what the booking's cancellation terms say |

- **First check who the slip paid (dev, 2026-10-30).** HAYA's account is 1020729617, CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC, Vietcombank (the old name "CT TNHH MTV DU LICH PHUONG NGUYEN" is the same account). A slip paid to anyone else, or naming another hotel or another booking — Footprint's UNC for 141C0127Y was Hoa Binh Hotel's, ref 141S1126J, 11,550,000 — is **not forwarded to accounting**, gets no payment columns and no thank-you. The only draft is a reply to the sender (`email-templates.md` 4d) asking for the correct UNC. Unreadable beneficiary → treat it as the right one and say "người nhận không đọc được" in the forward.
- Draft the forward as soon as the slip arrives, without asking first, in Vietnamese. No group code yet → forward anyway, the note says "chưa có mã đoàn" (Tracy's audit, 29/10; the old "hold until Tracy has entered it" is gone).
- The agency's thank-you (`email-templates.md` 4b) is drafted in the same run as this forward (dev, 2026-10-30). No answer from the accountant means the payment is fine; an answer that it didn't arrive goes to Karen.
- Never state an amount I can't read on the slip. Unreadable = say unreadable.
- Write the payment as a CHANGE row at the same time (`booking-intake.md`, "One email, one set of rows"); the NEW row is never edited.

## Front office — no forwards (dev, 2026-10-30)
Front office reads a booking's requests in its EZFOLIO notes, so nothing is forwarded to `haya@haya-hotels.com`; `draft-forward` refuses it. Forwards are for payment slips (accounting), VAT chasers and Palma.

Arrival time or flight, special requests (non-smoking, bed type, floor, quiet room, early check-in / late check-out, set-ups, food), rooming lists and name changes go on the booking's row instead (`booking-intake.md`):
- `special_requests`: the requests, `;`-separated, in plain words ("Non-smoking room; high floor; large bed; quiet room").
- `arrival_time` when given (a flight's landing time counts).
- `notes` item 5: the same requests and the arrival time; items 6–7 say what front office needs to know about the money (net amount, prepaid, non-refundable).
- A booking already on the sheet → a CHANGE row with all of it (`booking-intake.md`, "One email, one set of rows"). An OTA notice → the NEW row.

Why (dev, 30/10): draft #205 (Agoda 1791966280, four requests) was forwarded to haya@; the reviewer logged the requests in the booking's EZFOLIO notes instead, where front office sees them, and noted the forward left out the net amount (1,606,716 VND) and that the booking is non-refundable. Before this, 2026-10-22 to 30/10, every request was a forward to haya@ plus the reply.

A guest's or agency's email that front office forwarded in still gets its reply `--to` the original writer `--cc haya@haya-hotels.com` (`email-templates.md`, "Who the reply goes to"); that cc is a reply, not a forward.

## VAT invoice chasers — `ctyphuongnguyenpq.kt@gmail.com`
An agency chasing a VAT (red) invoice that was already requested: forward to ctyphuongnguyenpq.kt@gmail.com (Tracy's audit, 29/10), note on top with group code, company, MST and what they're chasing. This is the company's accounting address, not Karen's personal Gmail.

## Palma — `booking@palmahotel.vn`
Every Palma Resort email that lands in sales@: `draft-forward <id> booking@palmahotel.vn <note> --kind forward`, once. No HAYA row, no reply to the sender. accountant@palmahotel.vn writing about a HAYA payment is not a Palma item.

## Other departments
Housekeeping, F&B, engineering: no email route defined. If an email needs one of them, it goes to Karen in the scan report.

## Never
- Never forward a guest's or agency's email outside the hotel.
- Never forward one agency's rates or contract terms to another agency.
- Never use Karen's personal Gmail as a forwarding address.
