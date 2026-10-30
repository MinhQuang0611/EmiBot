"""Offline tests for scanned PDF vouchers (tools/attachments.py) and the Direct-row company rule
(tools/intake_schema.py), both from the first live run on 2026-10-22."""
import importlib.util
import os
import sys
import tempfile
import unittest
from unittest import mock

from tools import attachments
from tools import intake_schema as schema

CAN_RENDER = all(importlib.util.find_spec(m) for m in ("pypdfium2", "PIL"))


def pdf(*streams):
    """A minimal PDF, one page per content stream. b"" = a page with no text on it, which is what
    pypdf sees on a scanned voucher."""
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    kids = []
    for s in streams:
        n = len(objs) + 1
        objs.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] "
                    b"/Resources << /Font << /F1 3 0 R >> >> /Contents %d 0 R >>" % (n + 1))
        objs.append(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(s), s))
        kids.append(b"%d 0 R" % n)
    objs[1] = b"<< /Type /Pages /Kids [%s] /Count %d >>" % (b" ".join(kids), len(kids))
    out, offsets = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (i, o)
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    return out + b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)


TEXT = b"BT /F1 12 Tf 20 100 Td (Voucher AGSA8534 Deluxe Double) Tj ET"


class ScannedPdfTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = os.path.join(self.dir.name, "HotelVoucher_AGSA8534.pdf")

    def extract(self, data):
        with open(self.path, "wb") as f:
            f.write(data)
        return attachments.extract_text(self.path, data)

    def pngs(self):
        return sorted(f for f in os.listdir(self.dir.name) if f.endswith(".png"))

    def test_text_pdf_still_returns_its_text(self):
        text = self.extract(pdf(TEXT))
        self.assertIn("--- page 1 ---", text)
        self.assertIn("Voucher AGSA8534 Deluxe Double", text)
        self.assertNotIn("no text layer", text)
        self.assertEqual(self.pngs(), [])

    @unittest.skipUnless(CAN_RENDER, "pypdfium2 and pillow not installed")
    def test_scan_gives_page_images_not_empty_page_markers(self):
        # 2026-10-22: the MG voucher printed "--- page 1 ---" / "--- page 2 ---" and nothing else
        text = self.extract(pdf(b"", b""))
        self.assertNotIn("--- page", text)
        self.assertIn("PDF has no text layer (scan). Page images saved — open each one to read it:", text)
        self.assertEqual(self.pngs(), ["HotelVoucher_AGSA8534-page1.png", "HotelVoucher_AGSA8534-page2.png"])
        for name in self.pngs():
            full = os.path.join(self.dir.name, name)
            self.assertIn(os.path.abspath(full), text)
            with open(full, "rb") as f:
                self.assertEqual(f.read(4), b"\x89PNG")

    @unittest.skipUnless(CAN_RENDER, "pypdfium2 and pillow not installed")
    def test_mixed_pdf_renders_only_the_scanned_pages(self):
        text = self.extract(pdf(TEXT, b""))
        self.assertIn("Voucher AGSA8534", text)
        self.assertIn("PDF page(s) 2 have no text layer (scan).", text)
        self.assertEqual(self.pngs(), ["HotelVoucher_AGSA8534-page2.png"])

    @unittest.skipUnless(CAN_RENDER, "pypdfium2 and pillow not installed")
    def test_page_images_are_capped(self):
        text = self.extract(pdf(*[b""] * 7))
        self.assertEqual(len(self.pngs()), attachments.MAX_PAGE_IMAGES)
        self.assertIn(f"Only the first {attachments.MAX_PAGE_IMAGES} of 7 scanned pages were saved.", text)

    def test_without_pypdfium2_says_what_to_install(self):
        with mock.patch.dict(sys.modules, {"pypdfium2": None}):
            text = self.extract(pdf(b""))
        self.assertIn("PDF has no text layer (scan).", text)
        self.assertIn("pip install pypdfium2", text)
        self.assertEqual(self.pngs(), [])

    def test_render_failure_is_a_note_not_an_exception(self):
        broken = mock.Mock(PdfDocument=mock.Mock(side_effect=RuntimeError("bad xref")))
        with mock.patch.dict(sys.modules, {"pypdfium2": broken}):
            text = self.extract(pdf(b""))
        self.assertIn("Page images not made (RuntimeError: bad xref)", text)


DIRECT = {"action": "NEW", "received_at": "21/10/2026 09:30", "source_email": "Đặt phòng 2 đêm",
          "property": "HAYA", "channel_type": "Direct", "contact_person": "Quang Nguyễn Minh", "booking_ref": "HAYA-D001",
          "guest_names": "Quang Nguyễn Minh", "nationality": "Vietnam", "arrival": "20/11/2026",
          "departure": "22/11/2026", "nights": "2", "room_code": "DLX-SV", "rooms": "1", "adults": "2", "meal_plan": "BB",
          "rate_per_night_vnd": "2000000", "Average rate per night after discount": "2000000",
          "status": "Tentative", "priority": "Normal", "missing_info": ""}


class DirectCompanyTest(unittest.TestCase):
    def test_direct_row_leaves_company_blank_but_names_it(self):
        errors, _ = schema.check_row(DIRECT)
        self.assertTrue(any(e.startswith("company: required") for e in errors))  # silent blank refused
        named = dict(DIRECT, missing_info="REQUIRED blank: company – direct guest, EZFOLIO account for "
                                          "direct bookings not known")
        self.assertEqual(schema.check_row(named)[0], [])

    def test_direct_row_with_the_guest_as_company_is_refused(self):
        # 2026-10-22, row 57: company = the sender's own name, missing_info "new company; ..."
        errors, _ = schema.check_row(dict(DIRECT, company="Quang Nguyễn Minh", missing_info="new company; rate"))
        self.assertTrue(any(e.startswith("company: blank for a Direct booking") for e in errors))
        self.assertTrue(any(e.startswith("missing_info: no 'new company'") for e in errors))

    def test_agency_row_still_needs_company(self):
        errors, _ = schema.check_row(dict(DIRECT, channel_type="TA", booking_ref="TA-1"))
        self.assertTrue(any(e.startswith("company: required") for e in errors))


if __name__ == "__main__":
    unittest.main()
