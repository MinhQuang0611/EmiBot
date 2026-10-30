# Department forwards — who needs to see what

Every forward is saved to the Drafts folder for a person to send. I never send it myself. Forward the original email with its attachments intact; add a short note on top, never edit the original below it.

**Once per email** (Tracy's audit, 29/10): before a forward, `mail-find` the subject or ref to see whether it is already in Sent Items; `draft-forward` itself refuses a second forward of the same email to the same address (unless the first draft was denied). Never Karen's name in the note.

**The note on top, in Karen's style (dev, 2026-10-22):** Vietnamese, labels and bullets, nothing else. The colleague reading it should know in five seconds which booking, when, and what to do, without opening the email below. Accounting gets the block in `email-templates.md` 4c (mã đoàn on the first line, then total, 50%, the amount on the slip and whether it is short, reference numbers, invoice details — as HAYA's own forward for An0109 on 15/10/2026, subject "Fw: … – UNC cọc #[mã đoàn]"); front office gets the short block below.
- **When first.** If the guest arrives today or tomorrow, say so in the stay line: "22/10/2026 – 24/10/2026 (đến hôm nay)".
- **One line per request,** in plain words: "Phòng không hút thuốc", not a copy of the email.
- **One polite ask at the end, only if they must do something now:** "Nhờ lễ tân giữ phòng không hút thuốc cho khách." No reasons, no "Dear team", no sign-off paragraph.
- **Never forward an email back to the colleague who forwarded it to us** (sender `haya@haya-hotels.com` → nothing back to haya@). They have it; the reply to the guest or agency cc's them (`email-templates.md`, "Who the reply goes to"). `draft-forward` refuses it.

## Accounting — `accountant@palmahotel.vn` (no "s")
| Forward | Note on top must include |
|---|---|
| Every HAYA payment slip, UNC, remittance, and OTA payout advice (e.g. Citi Paylink for Traveloka) | EZFOLIO **group code** (or "chưa có mã đoàn"), agency/guest, amount on the slip, which payment it is (deposit / balance) |
| Red invoice (VAT) requests and company invoice details | Group code, company name, tax code, address as given |
| Refund requests after a cancellation | Group code, amount requested, what the booking's cancellation terms say |

- Draft the forward as soon as the slip arrives, without asking first, in Vietnamese. No group code yet → forward anyway, the note says "chưa có mã đoàn" (Tracy's audit, 29/10; the old "hold until Tracy has entered it" is gone).
- No answer from the accountant means the payment is fine: the agency gets an acknowledgement of receipt (`confirmation-replies.md`).
- Never state an amount I can't read on the slip. Unreadable = say unreadable.
- Write the payment as a CHANGE row at the same time (`booking-intake.md`, "One email, one set of rows"); the NEW row is never edited.

## Front office — `haya@haya-hotels.com`
| Forward | Note on top must include |
|---|---|
| Arrival time, flight details, airport transfer requests | Group code, guest name, arrival date and time |
| Special requests: same floor, connecting rooms, bed type, early check-in / late check-out, honeymoon or birthday set-up, dietary needs | Group code, guest name, stay dates, the request in one line |
| Rooming lists and name changes | Group code, which rooms are affected |
| Any change or cancellation for an arrival within the next 3 days | Group code, what changed, effective date |

Address given by Karen, 2026-10-08. The list above is still Monica's working draft of what front office needs — Karen hasn't confirmed it. I draft these forwards to Drafts like any other, and whoever sends them is the check on whether front office needed it.

**A guest's request on a booking = two drafts (dev, 2026-10-22).** When an email asks for anything in the table above (arrival time, same floor, late check-in, early check-in / late check-out…), I draft both:
1. the reply to the sender — `email-templates.md` section 5, `draft-reply <id> <file> --kind request --ref <ref>`;
2. the forward to front office — `draft-forward <id> haya@haya-hotels.com <file> --kind forward --ref <ref>`.

The reply alone is not enough: front office hears it from me, not from the guest at check-in. This holds when the sender volunteered the detail without being asked (I don't ask for arrival time or pickup — `email-templates.md` — but what they give me still goes to front office).

**Exception:** front office forwarded the email to us. Then the reply goes to the original writer with `--cc haya@haya-hotels.com`, and that cc is front office's copy. No forward.

**Booking not on the sheet yet** (no group code — OTA bookings often arrive this way): forward anyway, unlike accounting. The note says so, and the scan report lists the refs to check. Note on top, in Vietnamese:
```
**Booking:** [mã đặt phòng của khách / OTA] — chưa có trên sheet intake, chưa có mã đoàn
**Khách:** [tên như khách ký]
**Lưu trú:** [DD/MM/YYYY] – [DD/MM/YYYY]
**Yêu cầu:**
• [mỗi yêu cầu một dòng, ví dụ: Đến sân bay Phú Quốc 21:00, xin nhận phòng muộn]
• [2 phòng cùng tầng]
• [Hỏi trả phòng muộn và gửi hành lý sau khi trả phòng]
```
With a group code: `**Mã đoàn:** #[mã đoàn]` in place of the first line.

Example, a SynXis notice for a Booking.com guest arriving the same day who asked for a non-smoking room (live run 2026-10-22, guest name replaced):
```
**Booking:** 92777EF002985 (Booking.com qua SynXis) — chưa có trên sheet intake, chưa có mã đoàn
**Khách:** [tên khách], 1 người lớn
**Lưu trú:** 22/10/2026 – 24/10/2026 (đến hôm nay)
**Phòng:** 1 Standard Garden View (1 Queen Bed)
**Yêu cầu:**
• Phòng không hút thuốc

Nhờ lễ tân giữ phòng không hút thuốc cho khách.
```

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
