"""mail-find searches inside attached files (dev, 2026-11-09/10, Odeon OV613LLPX_11_1): front office sent the voucher
05/11 17:47 in an email with no subject, the ref only in the PDF. Emi didn't find it, wrote the booking from Odeon's
PENDING reminder on 09/11 (guests TBA, nationality Vietnam, no offers: 36,850,000 instead of 31,815,000) and the
build tool built it."""
import base64
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from tools import attachments, emi
from tools.tests.test_attachments_pdf import pdf
from tools.tests.test_tools import mail_with

VOUCHER = pdf(b"BT /F1 12 Tf 20 100 Td (Operator Voucher No OV613LLPX_11_1 KORNILOVA/ANASTASIIA) Tj ET")
OTHER = pdf(b"BT /F1 12 Tf 20 100 Td (Operator Voucher No 4799222 SMIRNOV/IVAN) Tj ET")


def recent(hours):
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


def fo(mid, hours, has_files=True):
    return {"id": mid, "subject": "", "receivedDateTime": recent(hours), "hasAttachments": has_files,
            "from": {"emailAddress": {"address": "haya@haya-hotels.com"}}}


def att(name, data):
    return {"@odata.type": "#microsoft.graph.fileAttachment", "name": name,
            "contentBytes": base64.b64encode(data).decode()}


class MailFindFilesTest(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.mkdtemp()
        self.inbox = [fo("fo-voucher", 100), fo("fo-other", 50), fo("fo-plain", 10, has_files=False)]
        self.mail, self.http = mail_with([
            ("GET", "$search=", {"value": [{"id": "odeon-reminder", "subject": "RE: PENDING - res OV613LLPX_11_1",
                                            "receivedDateTime": recent(1)}]}),
            ("GET", "/messages/fo-voucher/attachments", {"value": [
                att("hotelextranet.odeontours.com_PrintReservation_IDs=8646781.pdf", VOUCHER)]}),
            ("GET", "/messages/fo-other/attachments", {"value": [
                att("hotelextranet.odeontours.com_PrintReservation_IDs=8649178.pdf", OTHER)]}),
            ("GET", "/mailFolders/inbox/messages", {"value": self.inbox}),
        ])

    def find(self, text, **kw):
        lines = []
        hits = emi.mail_find(self.mail, text, out=lines.append, work_dir=self.work, **kw)
        return [m["id"] for m in hits], "\n".join(lines)

    def downloads(self):
        return [u for _, u, _ in self.http.calls if u.endswith("/attachments") or "/attachments?" in u]

    def test_ref_only_inside_the_pdf_is_found(self):
        ids, text = self.find("OV613LLPX_11_1")
        self.assertEqual(ids, ["odeon-reminder", "fo-voucher"])
        self.assertIn("(no subject)", text)
        self.assertIn("found in attached file: hotelextranet.odeontours.com_PrintReservation_IDs=8646781.pdf", text)
        self.assertNotIn("fo-other\n", text.replace("id: fo-other", ""))  # the other voucher isn't a hit

    def test_short_ref_and_case(self):
        ids, _ = self.find("ov613llpx")
        self.assertIn("fo-voucher", ids)

    def test_files_read_once_then_from_disk(self):
        self.find("OV613LLPX_11_1")
        first = len(self.downloads())
        self.assertEqual(first, 2)  # the email without files is never opened
        ids, _ = self.find("4799222")
        self.assertIn("fo-other", ids)
        self.assertEqual(len(self.downloads()), first)

    def test_days_zero_is_the_old_search(self):
        ids, _ = self.find("OV613LLPX_11_1", days=0)
        self.assertEqual(ids, ["odeon-reminder"])
        self.assertEqual(self.downloads(), [])

    def test_cap_says_not_all_read(self):
        old = emi.ATTACHMENT_SCAN_MAX
        emi.ATTACHMENT_SCAN_MAX = 1
        try:
            ids, text = self.find("OV613LLPX_11_1")
        finally:
            emi.ATTACHMENT_SCAN_MAX = old
        self.assertIn("NOT ALL READ: 1 email(s)", text)
        self.assertNotIn("fo-voucher", ids)  # newest first: the older voucher waits for the next run
        ids, _ = self.find("OV613LLPX_11_1")
        self.assertIn("fo-voucher", ids)

    def test_show_writes_the_index_mail_find_reads(self):
        m = fo("fo-voucher", 100)
        mail, http = mail_with([
            ("GET", "/messages/fo-voucher/attachments", {"value": [att("v.pdf", VOUCHER)]}),
        ])
        emi._show_attachments(mail, m, self.work, out=lambda *_: None)
        with open(emi._index_path(self.work, "fo-voucher"), encoding="utf-8") as f:
            idx = json.load(f)
        self.assertEqual(os.listdir(attachments.message_dir(self.work, "fo-voucher")), ["v.pdf"])  # files only
        self.assertIn("OV613LLPX_11_1", idx["files"][0]["text"])
        ids, _ = self.find("OV613LLPX_11_1")
        self.assertIn("fo-voucher", ids)
        self.assertNotIn("/messages/fo-voucher/attachments", " ".join(self.downloads()))

    def test_inbox_unreadable_is_a_gap_not_a_failure(self):
        class Broken:
            def search(self, text, top=10):
                return []

            def list_inbox_since(self, since):
                raise RuntimeError("403 Forbidden")
        lines = []
        self.assertEqual(emi.mail_find(Broken(), "OV613LLPX", out=lines.append, work_dir=self.work), [])
        self.assertIn("GAP: attached files not searched", "\n".join(lines))


if __name__ == "__main__":
    unittest.main()
