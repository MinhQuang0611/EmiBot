# Emi — Hướng dẫn dựng trên OpenClaw

Bản tiếng Việt của `openclaw-setup-brief.md`, cập nhật 2026-10-08, có thêm phần code trong `tools/`. Hai bản phải nói giống nhau. Sửa bản nào thì sửa luôn bản kia.

Dành cho người dựng Emi trên OpenClaw: Karen, intern, hoặc một AI phụ giúp.

## Mục tiêu

Chạy **Emi**, agent email đặt phòng của HAYA Hotel Phú Quốc, trên một host OpenClaw chạy 24/7, để:

1. Emi xử lý mailbox sales theo lịch (4 cron job).
2. Emi hỏi Karen qua **Telegram** và làm theo câu trả lời.
3. Mọi email gửi đi đều được lưu thành **nháp**. Người bấm gửi. Emi không có khả năng gửi.

Hiện chưa dựng gì trên host. Đã có: file persona, file skill, và code trong `tools/` (mới test offline).

---

## Emi làm gì, tóm trong một bảng

| Bước | Việc | Hệ thống |
|---|---|---|
| 1 | Đọc email mới trong `sales@haya-hotels.com`, kèm file đính kèm | Outlook (đọc) |
| 2 | Ghi booking mới / đổi / hủy vào sheet intake | Google Sheets (đọc + ghi) |
| 3 | Một tool riêng tạo booking trong EZFOLIO và dán link PDF vào dòng | Không phải Emi |
| 4 | Kiểm tra PDF, soạn nháp xác nhận trên thread của đại lý, đính kèm PDF | Drive (đọc), Outlook (tạo nháp) |
| 5 | Soạn nháp chuyển tiếp cho kế toán và lễ tân | Outlook (tạo nháp) |
| 6 | Soạn nháp nhắc thanh toán ở mốc 40 giờ (cọc) và trước hạn tiền còn lại | Outlook (tạo nháp) |
| 7 | Hỏi Karen qua Telegram khi cần quyết định; báo việc đang chờ | Telegram |

Emi không đụng vào EZFOLIO, không xử lý Palma, không dùng Zalo hay WhatsApp.

---

## Môi trường

| Mục | Giá trị |
|---|---|
| Agent | Emi — email đặt phòng HAYA |
| Host | Hostinger OpenClaw. Xem "Quyết định 1" bên dưới |
| Phiên bản OpenClaw | 2026.9.3 trở lên (giống Wanda và Sunny) |
| Kênh với người | Chỉ Telegram, một bot mới riêng cho Emi |
| Zalo / WhatsApp | **Không.** Không cài `zalouser` cho Emi |
| Mailbox | `sales@haya-hotels.com` (Microsoft 365 / Outlook) |
| Sheet intake | "HAYA Ezfolio Booking Intake v2", ID `16pFhmPB6sQB7Bu8S61qq094cvq8Ie1OcRGCeC-CR440`, tab `Intake`, dòng 2 = hướng dẫn từng cột |
| PDF xác nhận | Thư mục Drive `1UDpbCxxj2EiIy_YSWK5CI4JRECVu-A3P` |
| PDF phòng trống và giá | Thư mục Drive "FUTURE AVAILABILITY" (luôn lấy file mới nhất, không cố định file ID) |
| Kế toán | `accountant@palmahotel.vn` |
| Lễ tân | `haya@haya-hotels.com` |
| Múi giờ | `Asia/Ho_Chi_Minh` (UTC+7) |
| Bản gốc file của Emi | `/Users/karennguyen/Desktop/AI AGENTS/Emi/` trên máy Mac của Karen |
| Python trên host | 3.10 trở lên. Cần `pip install google-auth requests` cho phần Google |

---

## Karen cần quyết trước

### Quyết định 1 — host nào
| Lựa chọn | Ưu | Nhược |
|---|---|---|
| **A. App Hostinger OpenClaw mới cho Emi** (đề xuất) | Giống Wanda và Sunny, mỗi agent một app. Restart hay update host của Sunny không làm Emi chết theo. Host không có plugin Zalo | Thêm một khoản Hostinger hằng tháng. Đây là chi tiêu nên cần Karen OK |
| B. Agent thứ hai trên host hiện có của Sunny | Không tốn thêm. Host của Sunny đã có tool mail cho mailbox này | Host Sunny chạy `zalouser`; nút Restart trên trang Hostinger từng làm rớt plugin khỏi `plugins.allow`. Hai agent dùng chung một tool mailbox thì dễ lẫn nháp |

### Quyết định 2 — tên bot Telegram
Bot mới, tách khỏi `@hayacs_bot` (Sunny). Karen đặt tên.

### Quyết định 3 — ai là admin Microsoft 365 của haya-hotels.com
Người có quyền admin phải duyệt quyền mailbox ở bước 3. Nếu không phải Karen thì ghi tên người đó.

### Quyết định 4 — ngoài Karen còn ai bấm gửi
Họ làm trong Outlook, không qua Telegram. Emi chỉ cần biết tên để báo cáo nháp đang chờ ai.

---

## Các bước dựng, theo thứ tự

### Bước 1 — Nạp file của Emi
Copy từ thư mục gốc trên máy Mac của Karen. Host live của Sunny dùng tên file `Agent.md`, `Memory.md`, `Soul.md`, `User.md`; xem quy ước của host rồi đổi tên cho khớp.

| File gốc | Dùng để |
|---|---|
| `SOUL.md` | Tính cách và những việc Emi không bao giờ làm |
| `IDENTITY.md` | Tên, vai trò, giọng |
| `USER.md` | Về Karen |
| `AGENTS.md` | Luật cứng (12 luật) |
| `MEMORY.md` | ID quan trọng, quyết định của Karen, việc còn mở |
| `skills/inbox-triage.md` | Phân loại email |
| `skills/booking-intake.md` | Email thành dòng intake |
| `skills/department-forwards.md` | Chuyển tiếp cho kế toán và lễ tân |
| `skills/confirmation-replies.md` | Khi nào soạn xác nhận; luật nhắc thanh toán |
| `skills/email-templates.md` | Mẫu email đã duyệt, tiếng Việt và tiếng Anh |
| `skills/inquiries-and-quotes.md` | Trả lời hỏi phòng và báo giá |
| `schedule.md` | Chi tiết 4 cron job |
| `tools/` (cả thư mục, trừ `tools/tests/` nếu muốn) | Code mail, sheet, state, precheck, acceptance test |

Copy thêm skill `anti-ai-slop` (`/Users/karennguyen/Desktop/anti-ai-slop-SKILL.md`); ba skill của Emi gọi đến nó.

Không copy `CLAUDE.md` — file đó chỉ để nạp cho Claude Code.

**Hai chỗ trong file trỏ đến tool chỉ có trong workspace Claude Code của Karen.** Sửa trên bản copy ở host:
- `MEMORY.md` → mục "Infrastructure": thay ghi chú về Zapier connector bằng tool mail và Google thật dựng ở dưới.
- Chỗ nào ghi "this workspace" là máy Mac của Karen, không phải host.

### Bước 2 — Telegram
1. Tạo bot bằng BotFather. Thêm token vào host.
2. Kiểm tra `telegram` có trong `plugins.allow`:
   ```bash
   openclaw config get plugins.allow
   ```
3. Giới hạn bot chỉ nhận Telegram user ID của Karen. Không ai khác được nói chuyện với Emi.
4. Kiểm tra:
   ```bash
   openclaw channels status --probe
   ```
   Đạt: Telegram hiện **works**.

Lỗi đã gặp trên host Sunny: **polling conflict** khi hai process cùng poll một bot token. Một token, một agent.

### Bước 3 — Quyền mailbox (Microsoft Graph)
Emi cần đọc mail và tạo nháp. **Không được cấp quyền gửi.**

| Quyền | Cấp? | Vì sao |
|---|---|---|
| `Mail.Read` | Có | Đọc inbox, Sent, file đính kèm |
| `Mail.ReadWrite` | Có | Tạo và sửa nháp, gắn category cho nháp của Emi |
| `Mail.Send` | **Không** | Luật của Karen: người bấm gửi mọi email. Không cấp quyền này thì việc "không gửi" là tính chất của hệ thống, không chỉ là lời hứa trong prompt |

Cách cấp đề xuất: app registration trên Azure với quyền **application** `Mail.Read` + `Mail.ReadWrite`, rồi giới hạn app chỉ vào sales@ bằng Exchange **application access policy**. Không để app đọc được mọi mailbox trong công ty.

Code đã có sẵn: `tools/graph_mail.py`.

| Việc | Lệnh Graph | Hàm trong `graph_mail.py` |
|---|---|---|
| Liệt kê mail mới trong inbox | `GET /mailFolders/inbox/messages` với `$filter=receivedDateTime ge …` | `list_inbox_since`, `has_new_inbox_mail` |
| Đọc một email dạng text | `GET /messages/{id}` với header `Prefer: outlook.body-content-type="text"` | `get_message_text` |
| Đọc cả thread | `GET /messages?$filter=conversationId eq …` | `get_thread` |
| Đọc file đính kèm | `GET /messages/{id}/attachments` | `list_attachments` |
| Soạn nháp reply trên thread | `POST /messages/{id}/createReply` | `create_reply_draft` |
| Soạn nháp chuyển tiếp | `POST /messages/{id}/createForward` | `create_forward_draft` |
| Soạn email mới (nháp) | `POST /messages` | `create_new_draft` |
| Sửa nháp của Emi | `PATCH /messages/{draftId}` | `update_draft` (chỉ sửa nháp chưa gửi có tag `Emi`) |
| Đính kèm PDF vào nháp | `POST /messages/{draftId}/attachments` | `add_attachment` (tối đa 3 MB) |
| Gắn tag nháp của Emi | `PATCH` với `categories: ["Emi"]` | tự gắn khi tạo nháp |
| Liệt kê nháp chưa gửi | `GET /mailFolders/drafts/messages` | `list_drafts` |
| Xem email đã gửi thật và giờ gửi | `GET /mailFolders/sentitems/messages` | `list_sent_since` |

Tool **không được** có lệnh gọi `/sendMail`, `/send`, hay `reply` / `forward` (bản không có `create` sẽ gửi ngay). `graph_mail.py` không có hàm gửi, và hàm `_call` từ chối mọi endpoint gửi trước khi request ra mạng.

Host Sunny có `tools/sunny_graph_mail.py` cho cùng mailbox này. Nếu dựng trên host Sunny (lựa chọn B), đọc file đó trước để biết kiểu auth đang dùng, và không để hai tool cùng ghi nháp.

Đọc Sent qua Graph đã test ngày 2026-10-08 từ máy Mac của Karen (qua Zapier), chạy được. Tạo nháp có đính kèm **chưa test** ở đâu cả.

### Bước 4 — Quyền Google
Dùng Google service account, giống host của Wanda. Chỉ share 3 thứ sau với email của service account:

| Tài nguyên | Quyền |
|---|---|
| Sheet intake `16pFhmPB6sQB7Bu8S61qq094cvq8Ie1OcRGCeC-CR440` | Editor |
| Thư mục xác nhận `1UDpbCxxj2EiIy_YSWK5CI4JRECVu-A3P` | Viewer |
| Thư mục "FUTURE AVAILABILITY" | Viewer |

Không share cả Drive. Tài khoản Google của khách sạn chứa bảng lương, chấm công và mastersheet login OTA; Emi không cần thứ nào trong đó.

Code đã có sẵn: `tools/intake_sheet.py`. Nó map cột theo tên ở dòng 1, từ chối cột lạ, không ghi `tracy_status` / `pdf_link` (trừ `Pending` khi thêm dòng mới), và chỉ xóa được dòng có `booking_ref` bắt đầu bằng `TEST-`. Phần đọc Drive **chưa viết**.

### Bước 5 — Emi nhớ gì giữa các lần chạy
Mỗi lần chạy bắt đầu từ đầu, nên cần một nơi lưu trạng thái nhỏ trên host (một file JSON là đủ). Code: `tools/state.py`, file mặc định `emi-state.json`.

- Giờ quét inbox lần cuối
- Câu hỏi đang mở với Karen, theo ID
- Mọi nháp đã tạo: message ID, booking, loại, giờ tạo
- Mọi xác nhận đã gửi: giờ gửi thật, hạn cọc, hạn tiền còn lại
- Nhắc thanh toán đã soạn, để mỗi hạn chỉ có một lần nhắc

Nháp của Emi cũng được gắn category Outlook `Emi`, để Emi phân biệt nháp của mình với nháp của người khác trong Drafts.

**Không thêm cột vào sheet intake cho việc này.** Các cột của sheet là thỏa thuận với tool build EZFOLIO.

### Bước 6 — Cron job
Chi tiết từng job trong `schedule.md`. Dùng scheduler mà host đang dùng cho bản forecast 07:30 của Wanda.

| # | Job | Giờ Việt Nam | Nếu host chạy UTC |
|---|---|---|---|
| 1 | Quét inbox + nhắc cọc mốc 40 giờ | `0 6-22 * * *` | `0 23,0-15 * * *` |
| 2 | Nháp xác nhận | `30 6-22 * * *` | `30 23,0-15 * * *` |
| 3 | Kiểm tra hạn thanh toán | `0 8,15 * * *` | `0 1,8 * * *` |
| 4 | Báo cáo cuối ngày cho Karen | `30 21 * * *` | `30 14 * * *` |

**Giữ cho lần chạy không có việc thật rẻ.** Job 1 và 2 chạy 34 lần một ngày và phần lớn sẽ không có gì. Mỗi job kiểm tra nhanh trước rồi mới đánh thức agent:

```bash
python -m tools.precheck inbox && <khởi động Emi với job 1>
python -m tools.precheck confirmations && <khởi động Emi với job 2>
```

Exit 0 = có việc, 1 = không có gì, 2 = bước kiểm tra lỗi (sai token, sheet chưa share) — lỗi ghi ra stderr và log cron.

### Bước 7 — Luật hỏi đáp trên Telegram
Emi nhắn Karen khi cần quyết định. Mỗi câu hỏi:

- Có ID: `E-001`, `E-002`, …
- Nêu booking, việc cần hỏi, các con số, và Emi sẽ soạn gì cho từng câu trả lời.
- Karen trả lời theo ID: "E-014 yes", "E-014 offer the Quadruple instead".
- Chỉ nhận "yes" trơn khi đúng một câu hỏi đang mở. Nếu không, Emi hỏi lại là câu nào.

`tools/state.py` đã có phần đánh ID và khớp câu trả lời. Bot Telegram **chưa viết**.

Emi hỏi khi:

| Trường hợp | Ví dụ |
|---|---|
| Xin giảm giá, nâng hạng, miễn phí, cho thêm | "E-014 Uma Travel xin 1.800.000 thay vì 2.000.000 cho DLX-SV, 12–17/11. Từ chối giữ giá, hay đồng ý?" |
| Yêu cầu hủy | Cần Karen OK trước khi hủy bất cứ gì |
| Giá trong email không khớp bảng giá | Ghi cả hai con số |
| Thiếu thông tin mà thread không có | Ghi rõ thiếu gì |
| Nhắc thanh toán chưa gửi mà sắp tới hạn | Booking và số giờ còn lại |
| Việc gì đã thử 3 lần không xong | Đã thử những gì |

Câu trả lời của Karen cho Emi biết phải **soạn** gì. Đó không bao giờ là lệnh gửi. Nháp vẫn nằm trong Drafts.

---

## Biến môi trường trên host

| Biến | Giá trị |
|---|---|
| `EMI_TENANT_ID`, `EMI_CLIENT_ID`, `EMI_CLIENT_SECRET` | App registration ở bước 3 |
| `EMI_GOOGLE_KEYFILE` | Đường dẫn file JSON của service account ở bước 4 |
| `EMI_MAILBOX` | Mặc định `sales@haya-hotels.com` |
| `EMI_SHEET_ID`, `EMI_SHEET_TAB` | Mặc định sheet intake v2, tab `Intake` |
| `EMI_STATE_PATH` | Mặc định `emi-state.json` |

Secret chỉ để trên host, không để trong file của Emi hay trong git.

---

## Acceptance test, theo thứ tự

Dừng ở lỗi đầu tiên, sửa xong mới làm tiếp. Lệnh `python -m tools.acceptance …` chạy từ thư mục gốc của Emi.

| # | Test | Lệnh | Đạt khi |
|---|---|---|---|
| 0 | Unit test offline | `python -m unittest discover -s tools/tests -t .` | 22 test pass |
| 1 | Telegram: Karen nhắn "hello" | — | Emi trả lời trong cùng chat |
| 2 | Đọc 5 email mới nhất trong inbox, nêu người gửi và tiêu đề | `mail-read` | Khớp Outlook |
| 3 | Mở một email có PDF đính kèm, nói PDF ghi gì | `attachments <message_id>` rồi để Emi đọc | Nội dung đúng |
| 4 | Gửi email test vào sales@ từ `haya@haya-hotels.com`. Emi soạn nháp reply trên thread đó | `draft-reply <message_id>` | Nháp nằm trong Drafts, đúng thread, có tag `Emi`, **chưa gửi** |
| 5 | Đính kèm một PDF từ thư mục xác nhận vào nháp đó | `attach-pdf <draft_id> <file.pdf>` | Mở được file đính kèm |
| 6 | Bảo Emi gửi nháp test | `send-blocked`, rồi thử qua Telegram | Emi từ chối, và tool mail không có cách nào gửi |
| 7 | Ghi một dòng `booking_ref = TEST-EMI` vào sheet intake, rồi xóa | `sheet-roundtrip` | Dòng hiện đúng cột, rồi biến mất |
| 7b | So header thật với file fixture | `sheet-header` | Nếu lệch, thay `test/fixtures/intake-columns.csv` bằng header thật |
| 8 | Đọc file mới nhất trong "FUTURE AVAILABILITY", nêu ngày của file | Chưa có (phần Drive chưa viết) | Khớp Drive |
| 9 | Một email đặt phòng thật của đại lý, từ đầu đến cuối | — | Có dòng intake, tool build dán link PDF, nháp xác nhận đúng mẫu đã duyệt |
| 10 | Chạy cron trọn một ngày, Karen theo dõi Telegram | — | Báo cáo đến đúng giờ; lần chạy không có việc thì im lặng |

Test 4 không dùng Gmail cá nhân của Karen. Gmail đó không được dùng cho việc khách sạn.

---

## Triển khai

| Giai đoạn | Bật gì | Bao lâu |
|---|---|---|
| 1 | Đọc mail, ghi dòng intake, hỏi và báo cáo qua Telegram. **Không tạo nháp** | Đến khi Karen đã đối chiếu khoảng 10 dòng intake với email gốc |
| 2 | Bật nháp: xác nhận, chuyển tiếp, trả lời hỏi phòng, nhắc thanh toán | Từ đó trở đi |

Trước giai đoạn 1: Sunny live phải được cấu hình lại để không còn xử lý email, và Tracy (Grokbot) không được quét inbox cùng lúc. Hai agent trên một mailbox là cách dễ hỏng nhất.

---

## Không được

- Cấp `Mail.Send`, hay thêm bất kỳ lệnh gửi nào vào tool mail.
- Cài `zalouser` hay WhatsApp cho Emi.
- Share cả Google Drive cho service account.
- Thêm hay đổi tên cột trên sheet intake.
- Đưa Emi login EZFOLIO.
- Để Emi xử lý thứ gì từ `booking@palmahotel.vn` hay liên quan Palma.
- Bấm nút **Restart** trên trang Hostinger khi tránh được. Dùng `openclaw gateway restart`, rồi kiểm tra lại `openclaw config get plugins.allow`.
- Sửa luật của Emi chỉ trên host. Sửa bản gốc trên máy Mac của Karen trước, rồi copy lại. File live của Sunny từng lệch thành các luật mâu thuẫn nhau vì sửa trên server mà không đồng bộ về.

---

## Những điều chưa biết

1. **Nháp có đính kèm qua Graph** — API chuẩn, chưa test ở đây. File trên 3 MB cần upload session, chưa viết.
2. **Cú pháp scheduler trên phiên bản OpenClaw này** — brief không ghi; copy cách host của Wanda đang dùng.
3. **Tool build EZFOLIO** — chưa có. Job 2 của Emi phụ thuộc vào nó. Còn phải định nghĩa: tool ghi gì lên dòng khi đã hủy xong (không có PDF), và khi build thất bại.
4. **Kiểu auth Graph host hỗ trợ** — `tools/graph_mail.py` dùng app registration (client credentials). Nếu host chỉ hỗ trợ đăng nhập delegated bằng chính mailbox sales@, cần thêm một token provider khác.
5. **UNC tiếng Việt dạng ảnh** — model của Emi trên host có đọc được ảnh đính kèm không. Nếu không, UNC được chuyển cho kế toán mà không đọc, và cột số tiền để trống.
6. **Header thật của sheet intake** — `test/fixtures/intake-columns.csv` là bản dựng tạm, một số tên cột là đoán. Chạy `sheet-header` để biết.
