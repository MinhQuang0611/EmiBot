# Test Emi local — chưa deploy

Chạy Emi ngay trong Claude Code, trên email giả, không đụng Outlook, sheet hay Drive thật.

## Thư mục
| Thư mục | Nội dung |
|---|---|
| `emails/` | Email giả, mỗi file một email. Tên công ty và domain `.test` đều là giả. |
| `fixtures/` | Bản copy local của sheet và bảng giá. Xem `fixtures/README.md`, còn thiếu số liệu thật. |
| `out/` | Emi ghi kết quả vào đây: `intake.csv`, `drafts/`, `scan-report.md` |
| `expected.md` | Kết quả đúng cho từng email |

## Chạy
Mở Claude Code trong thư mục project (CLAUDE.md sẽ nạp Emi), rồi gõ:

```
Chạy chế độ test local: quét toàn bộ test/emails/ như inbox mới.
Ghi intake vào test/out/intake.csv, nháp vào test/out/drafts/, báo cáo vào test/out/scan-report.md.
Không gọi tool mail, sheet hay Drive thật.
```

Chạy một email: thay `toàn bộ test/emails/` bằng tên file.

Chạy lại từ đầu: xóa `test/out/` trước.

## Thêm test
Thêm file `.txt` vào `emails/` với header From/To/Date/Subject. Ghi kết quả mong đợi vào `expected.md`. Email thật export từ Outlook (`.eml`) cũng dùng được, nhưng có dữ liệu khách, cần Karen OK và không commit lên repo.

## Bước tiếp theo
1. Điền `fixtures/` bằng số liệu thật.
2. Mức 2: script local (mail tool chỉ tạo nháp, ghi sheet, langextract), dùng mailbox test và bản copy của sheet.
3. Mức 3: OpenClaw local với bot Telegram test.
4. Deploy lên Hostinger theo `openclaw-setup-brief.md`.
