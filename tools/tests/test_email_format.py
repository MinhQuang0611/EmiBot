import re
import unittest

from tools.graph_mail import FONT, email_html, paragraphs

# Draft of 06/11 (Absolute Asia AAT261113.502, slip thank-you): written with single line breaks, it showed in
# Outlook as one block, in the thread's own serif font.
SLIP = """Kính gửi chị Mai,
HAYA Hotel Phu Quoc, Trademark Collection by Wyndham xin cảm ơn quý công ty đã gửi UNC. Chúng tôi xác nhận đã nhận chứng từ chuyển khoản 7.695.000 VND – thanh toán phần còn lại cho booking sau:
BK AAT261113.502 – Mã đoàn #28192 – JATHAR NEHA ONKAR (13/11 – 16/11/2026): đã thanh toán đủ 7.695.000 VND.
Thông tin xuất hóa đơn đã được ghi nhận: CÔNG TY CỔ PHẦN DU LỊCH ABSOLUTE ASIA – MST 0108042118.
Trân trọng,
Bộ phận Đặt phòng
HAYA Hotel Phu Quoc, Trademark Collection by Wyndham
sales@haya-hotels.com"""


class ParagraphsTest(unittest.TestCase):
    def test_wall_of_text_is_cut_into_paragraphs(self):
        blocks = paragraphs(SLIP).split("\n\n")
        self.assertEqual(blocks[0], "Kính gửi chị Mai,")
        self.assertTrue(blocks[1].startswith("HAYA Hotel") and blocks[1].endswith("booking sau:"))
        self.assertTrue(blocks[2].startswith("BK AAT261113.502"))
        self.assertTrue(blocks[3].startswith("Thông tin xuất hóa đơn"))
        self.assertEqual(blocks[4], "Trân trọng,\nBộ phận Đặt phòng\nHAYA Hotel Phu Quoc, Trademark Collection by "
                                    "Wyndham\nsales@haya-hotels.com")
        self.assertEqual(len(blocks), 5)

    def test_label_lines_and_bullets_stay_together(self):
        text = ("Dear Ms. Ip,\nThank you for your message.\nBooking reference: 1794048417\nGuest name: Yuk Yan Ip\n"
                "Stay: 21/11/2026 – 24/11/2026 (3 nights), 1 room(s)\nTo arrange the driver, could you please reply "
                "with:\n– Your flight number and scheduled landing time\n– A WhatsApp number\nBest regards,\n"
                "Reservations Team")
        self.assertEqual(paragraphs(text).split("\n\n"), [
            "Dear Ms. Ip,", "Thank you for your message.",
            "Booking reference: 1794048417\nGuest name: Yuk Yan Ip\nStay: 21/11/2026 – 24/11/2026 (3 nights), 1 room(s)",
            "To arrange the driver, could you please reply with:",
            "– Your flight number and scheduled landing time\n– A WhatsApp number",
            "Best regards,\nReservations Team"])

    def test_bank_block_with_a_sentence_after_its_label_stays_one_block(self):
        text = ("Thông tin tài khoản thanh toán:\nTên tài khoản: CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC\n"
                "Số tài khoản: 1020729617\nNgân hàng: Vietcombank, CN Phú Quốc\nNội dung chuyển khoản: Tên Công ty + "
                "Mã đoàn #30287. Sau khi chuyển khoản, chị vui lòng gửi ủy nhiệm chi qua email để khách sạn đối chiếu.")
        self.assertEqual(paragraphs(text), text)

    def test_text_already_in_paragraphs_is_unchanged(self):
        text = "Dear Zion,\n\nLate check-out until 18:00 is 50% of one night.\n\nBest regards,\nReservations Team"
        self.assertEqual(paragraphs(text), text)


class FontTest(unittest.TestCase):
    def test_every_paragraph_and_list_item_carries_the_font(self):
        h = email_html(SLIP + "\n\n– one\n– two")
        tags = re.findall(r"<(p|li)\b([^>]*)>", h)
        self.assertTrue(tags)
        for tag, attrs in tags:
            self.assertIn(FONT, attrs, tag)
        self.assertEqual(h.count("<p "), 5 + 0)  # 5 paragraphs; the list is a <ul>
        self.assertIn("<ul style=", h)
        self.assertTrue(h.startswith(f'<div style="{FONT}">'))


if __name__ == "__main__":
    unittest.main()
