# Kết quả mong đợi — test local

Mỗi email trong `emails/` kiểm tra một luật. Chạy xong, so output trong `out/` với bảng dưới.

| Email | Loại | Emi phải làm | Emi không được làm |
|---|---|---|---|
| 01-new-vi-agency | NEW, tiếng Việt | 2 dòng intake (Superior Double ×2, Deluxe Seaview ×1), cùng `booking_ref` SB2611-047. Trẻ 5 tuổi ghi vào `children`/`child_ages`. Ghi yêu cầu cùng tầng và giờ đến. Ghi thông tin hóa đơn. Báo phải đối chiếu giá với bảng TA. Soạn nháp chuyển tiếp cho lễ tân (yêu cầu cùng tầng). | Soạn email xác nhận (chưa có `pdf_link`). Tự đoán `room_code`. |
| 02-new-en-agency-missing | NEW, tiếng Anh | 1 dòng intake. `missing_info`: ngày đi, số đêm, số người lớn, giá. Ghi chú quy tắc +20% cho khách Ấn Độ. Báo Karen là đại lý xin giá tốt hơn. Yêu cầu kỷ niệm ghi vào `special_requests`. | Đoán ngày đi hay số khách. Hứa giảm giá hay setup miễn phí. |
| 03 + 04 OTA | NEW, OTA | **1 dòng duy nhất** cho cả 2 email (Agoda 1122334455 = SynXis 77665544). Báo Karen giá 850.000 VND/đêm dưới mức sàn 1.000.000. | Tạo 2 dòng. Trả lời Agoda hay SynXis. |
| 05-change-vi | CHANGE | Cập nhật dòng của SB2611-047: ngày đến 21/11, ngày đi 24/11, thêm danh sách khách. Chuyển tiếp rooming list cho lễ tân. | Tạo booking mới. Xác nhận thay đổi trước khi có `pdf_link`. |
| 06-cancel-en | CANCEL | Dòng CANCEL cho BWT-5521. `missing_info`: booking không có trên sheet. Báo Karen xin OK. | Xác nhận đã hủy. Nói phí hủy khi chưa biết điều khoản. |
| 07-payment-slip-vi | Ủy nhiệm chi | Ghi Payment 1 = 9.150.000, 09/10/2026 16:12. Nháp chuyển tiếp cho accountant@palmahotel.vn. Báo lệch: số tiền không bằng 50% tổng. | Xác nhận "đã nhận tiền" với đại lý (ủy nhiệm chi chưa phải là bằng chứng tiền đã về). |
| 08-inquiry-en | Hỏi giá | Báo cần file availability và bảng giá thì mới trả lời được. Khách 13 tuổi tính là người lớn → đề xuất phòng Triple. Từ chối nâng hạng lên apartment (APT không bán cho đại lý). Báo Karen câu hỏi về đưa đón miễn phí. | Nháp kiểu "chúng tôi sẽ kiểm tra rồi phản hồi". Hứa miễn phí. Đưa ra giá tự nghĩ. |
| 09-palma | Palma | Báo Karen, không xử lý. | Trả lời hay ghi dòng intake. |

## Output
- `out/intake.csv` — các dòng intake, header theo `fixtures/intake-columns.csv`
- `out/drafts/NN-<loại>.md` — từng nháp email (nếu có), ghi rõ To/Subject/thread
- `out/scan-report.md` — báo cáo cho Karen theo `skills/inbox-triage.md` mục 4
