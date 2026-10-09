# Báo cáo quét — 6 email thật, 08/10/2026
Nguồn: 6 file `.eml` trong `test/emails/`, được chuyển từ sales@ kèm nhãn loại email. Không gọi mail, sheet hay Drive thật. Giờ trong email gốc coi là giờ Việt Nam.

## Cần Karen xử lý ngay
| # | Booking | Việc | Vì sao gấp |
|---|---|---|---|
| 1 | **Phú Minh Quang An0109** (#29519, XN 25694), 11–15/01/2027 | Đại lý xin dời hạn đặt cọc sang **15/10/2026** vì khách chuyển khoản quốc tế. Karen đồng ý hay không? | Hạn trong xác nhận đã gửi là 13:49 ngày 08/10/2026, đã qua. Theo quy định "48 giờ sau khi đại lý nhận xác nhận" thì hạn đúng là 09:47 ngày 09/10/2026 (xác nhận gửi 07/10 09:47). Booking chưa bị hủy, vì không hủy gì khi chưa có Karen. |
| 2 | **Anex 112888584**, LIASHENKO, 11–21/10/2026 | Anex xin hủy. Karen OK hủy không? Ai bấm link xác nhận trên hệ thống Anex? | Khách đến trong 3 ngày. Lúc đặt (05/10) booking ở trạng thái "On request", chưa rõ HAYA đã xác nhận chưa. Booking không có trong sheet. |
| 3 | **Hindol Roy**, khách trực tiếp, 23–26/10/2026 | Hỏi giá trực tiếp, xin giảm giá/nâng hạng miễn phí, hỏi phí đưa đón, bữa sáng chay/Ấn Độ, phòng tiện cho cụ ông 88 tuổi | Chưa có giá trực tiếp, nên chuyển Karen. Email gửi 03/10. Theo `email-templates.md`, Karen đã trả lời ông Roy ngày 07/10, nên Emi không soạn thêm để tránh trả lời 2 lần. |
| 4 | **Tên tài khoản ngân hàng** | Tên in trên UNC của OBT là "CT TNHH MTV DU LICH PHUONG NGUYEN". MEMORY ghi "CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC". Cùng số tài khoản 1020729617 | Tên nào là tên đúng trên tài khoản? Tất cả xác nhận gửi đi đều in tên này. |

Ghi chú về mục 1: nhãn trong email yêu cầu Emi nhắn Karen qua Telegram. Emi chưa có kênh Telegram nên tạm báo ở đây.

## Booking mới / thay đổi / hủy
| Booking | Loại | Dòng intake | Còn thiếu |
|---|---|---|---|
| Agoda 1783423852, Irina Boltenkova | NEW, OTA, trả trước | 1 dòng. Suite Sea View, 19–26/11/2026, 7 đêm, net 22.494.024 | room_code. Giá net 3.213.432/đêm, trên sàn. Không hoàn hủy. |
| 365 Travel, 3 Standard Double | NEW, TA | 1 dòng. 02–05/12/2026, 1.700.000/phòng/đêm, tổng 15.300.000 | Giá chưa đối chiếu bảng TA; mã booking của đại lý; tên khách; số khách; room_code |
| Phú Minh Quang An0109 | CHANGE (dời hạn cọc) | 2 dòng (Triple, Deluxe Seaview), có mã đoàn #29519 | Chờ Karen OK. Tracy chưa đổi gì. |
| Anex 112888584 | CANCEL | 1 dòng | Chờ Karen OK; mã đoàn trong EZFOLIO |

## Thanh toán
| Booking | UNC | Trạng thái |
|---|---|---|
| OBT071026MB (#29521), Nguyễn Chí Công, 08–09/10/2026 | 1.150.000 VND, 08/10/2026 13:49, từ VPBank 5288678888 | Số tiền bằng toàn bộ tổng tiền chứ không phải 50%, dù nội dung ghi "COC". Đã soạn chuyển kế toán, kèm thông tin hóa đơn. Booking này không có dòng trong sheet local nên chưa ghi được cột payment. Trên sheet thật: tìm OBT071026MB, ghi payment_1. UNC chưa phải xác nhận tiền đã về. |

## Bản nháp trong `test/out/real/drafts/`
| File | Gửi cho | Nội dung |
|---|---|---|
| `01-forward-accounting-OBT071026MB.md` | accountant@palmahotel.vn | UNC #29521 + yêu cầu xuất hóa đơn VAT |
| `02-forward-frontoffice-Anex-112888584.md` | haya@haya-hotels.com | Báo lễ tân Anex xin hủy, khách đến 11/10, **chưa hủy**. Còn trống mã đoàn. |

## Chưa soạn, và lý do
| Việc | Lý do |
|---|---|
| Xác nhận 365 Travel | Chưa có `pdf_link`. |
| Trả lời Phú Minh Quang | Chờ Karen quyết. Không soạn thư hẹn "sẽ kiểm tra". |
| Xác nhận hủy Anex | Chưa có OK của Karen. Email từ robot, không trả lời được; Anex cần bấm link trên hệ thống của họ. |
| Trả lời Agoda | Email OTA không trả lời. Agoda đã gửi thẳng cho haya@ nên lễ tân đã có yêu cầu "yên tĩnh, view đẹp". |
| Trả lời Hindol Roy | Karen đã trả lời 07/10. Chưa có giá trực tiếp. |
| Báo "đã nhận tiền" cho OBT | Kế toán chưa xác nhận tiền đã về. |

## Lưu ý dữ liệu
- `test/emails/` và `test/out/real/` giờ có dữ liệu khách thật (tên, số tài khoản, MST). Không commit lên repo. Xóa khi test xong.
- Hai xác nhận cũ trong thread (OBT ngày 06/10, Phú Minh Quang ngày 07/10) không theo mẫu đã duyệt: thiếu giờ hạn cọc hoặc tính hạn từ lúc nhận yêu cầu. Chỉ ghi nhận, Emi không sửa email đã gửi.
