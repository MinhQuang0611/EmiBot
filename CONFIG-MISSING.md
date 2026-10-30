## Karen cần quyết định hoặc cung cấp

- [ ] **Chọn nơi chạy Emi**: OpenClaw riêng cho Emi hay agent trên host hiện tại; ghi rõ host/phiên bản. Host mới phát sinh chi phí.
- [ ] **Chốt kênh hỏi/báo cáo**: tạo bot Telegram riêng, cung cấp token an toàn trên host. Chốt báo cáo job 4 gửi qua Telegram, email hay nơi khác.
- [x] **Xác nhận phạm vi chuyển lễ tân** — dev 30/10: không forward cho lễ tân, yêu cầu ghi vào notes EZFOLIO (`skills/department-forwards.md`).

## Quyền truy cập và secret cần cấu hình

- [ ] **Microsoft 365**: xác định admin thực hiện app registration và Exchange application access policy. Cấp application permissions `Mail.Read` + `Mail.ReadWrite`, giới hạn đúng `sales@haya-hotels.com`; tuyệt đối không cấp `Mail.Send`. Điền `EMI_TENANT_ID` và `EMI_CLIENT_SECRET` vào secret store trên host; xác nhận `EMI_CLIENT_ID` hiện có thuộc đúng app. Không ghi secret vào tài liệu/git.
- [ ] **Google live resources**: share intake sheet `16pFhmPB6sQB7Bu8S61qq094cvq8Ie1OcRGCeC-CR440` quyền Editor; share thư mục confirmations `1UDpbCxxj2EiIy_YSWK5CI4JRECVu-A3P` và `FUTURE AVAILABILITY` quyền Viewer với service account. Không share toàn Drive.
- [ ] **Service account trên host**: đặt JSON key ngoài workspace và cấu hình `EMI_GOOGLE_KEYFILE` trỏ đến file đó. Đường dẫn key hiện có trên máy local không tự dùng được trên host.Tình trạng cấu hình local ghi nhận được

- `.env` có một số giá trị đã điền, nhưng `EMI_TENANT_ID` và `EMI_CLIENT_SECRET` đang trống. Điều này chưa xác nhận quyền truy cập live hoạt động; không đưa nội dung `.env` vào báo cáo/chia sẻ.
- `EMI_SHEET_ID` mẫu trỏ live sheet, còn MEMORY ghi service account đã kiểm tra với sandbox. Xác nhận cặp sheet/keyfile trước mọi thao tác ghi.
- Emi chưa được triển khai lên host và schedule chưa bật. Một số acceptance test có ghi dữ liệu, nên cần xác định môi trường test trước khi chạy.
