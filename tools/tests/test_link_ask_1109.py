"""Front office sent a voucher as a OneDrive link: Emi answers front office itself, asking gently for the PDF
(dev, 2026-11-09; email-templates.md 10). The draft goes to haya@ with --internal, nothing to Karen."""
from tools import emi
from tools.tests.test_replies import Base, FRONT, args

ASK = """Chào anh/chị,

Em cảm ơn anh/chị đã chuyển voucher Odeon 8649178 sang bộ phận Đặt phòng.

Email này chỉ có link OneDrive, em không mở được voucher. Anh/Chị gửi lại giúp em file PDF đính kèm trực tiếp trong email nhé.

Những lần sau, anh/chị gửi voucher dạng file PDF đính kèm giúp em, không gửi link ạ.

Em cảm ơn anh/chị!

Trân trọng,
Bộ phận Đặt phòng
HAYA Hotel Phu Quoc, Trademark Collection by Wyndham
sales@haya-hotels.com
"""


class LinkAskTest(Base):
    def test_ask_for_the_pdf_goes_to_front_office(self):
        d = emi.draft_reply(self.mail, self.st, args(self.body(ASK), internal=True, kind="reply", ref=""),
                            tg=self.tg, out=self.lines.append)
        self.assertEqual(self.mail._meta(d["id"])["to"], [FRONT])

