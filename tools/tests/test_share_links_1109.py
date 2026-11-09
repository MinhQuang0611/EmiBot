"""A voucher sent as a OneDrive/SharePoint link is opened and read like an attachment (dev, 2026-11-09: front office
sent Odeon 8649178 as a link only, row 1609 went to the sheet with every field blank)."""
import base64
import os
import tempfile
import unittest

from tools import attachments, emi, httpjson
from tools.graph_mail import share_links
from tools.tests.test_tools import mail_with

LINK = "https://hayahotels-my.sharepoint.com/:b:/g/personal/haya_haya-hotels_com/EaBc123?e=xYz"


def b64url(url):
    return base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")


def thread_with(body):
    target = {"id": "m2", "conversationId": "c1"}
    thread = {"value": [
        {"id": "m2", "receivedDateTime": "2026-11-06T04:09:00Z", "subject": "", "hasAttachments": False,
         "from": {"emailAddress": {"address": "haya@haya-hotels.com"}}, "body": {"content": body}}]}
    return [("GET", "/messages/m2/attachments", {"value": []}), ("GET", "/messages?", thread),
            ("GET", "/messages/m2", target)]


class ShareLinksTest(unittest.TestCase):
    def test_finds_onedrive_and_sharepoint_links_once(self):
        text = (f"Voucher<{LINK}>\nagain {LINK}.\nshort https://1drv.ms/b/s!AbC\n"
                "not this https://www.odeontours.com/voucher")
        self.assertEqual(share_links(text), [LINK, "https://1drv.ms/b/s!AbC"])

    def test_safelinks_wrapper_taken_off(self):
        wrapped = ("https://apac01.safelinks.protection.outlook.com/?url=" + urllib_quote(LINK)
                   + "&data=05%7C02&reserved=0")
        self.assertEqual(share_links(f"see <{wrapped}>"), [LINK])

    def test_no_links(self):
        self.assertEqual(share_links("Dear team, voucher attached."), [])


def urllib_quote(s):
    import urllib.parse
    return urllib.parse.quote(s, safe="")


class ShowOpensLinkTest(unittest.TestCase):
    def test_file_behind_the_link_is_saved_and_read(self):
        item = {"name": "8649178.csv", "size": 30, "file": {}, "@microsoft.graph.downloadUrl": "https://dl.example/f"}
        rules = [("GET", "/shares/u!" + b64url(LINK) + "/driveItem", item),
                 ("GET", "dl.example/f", b"guest,arrival\nIVANOV,20.11.2026")] + thread_with(f"Voucher <{LINK}>")
        mail, http = mail_with(rules)
        lines = []
        with tempfile.TemporaryDirectory() as d:
            emi.show(mail, "m2", work_dir=d, out=lines.append)
            saved = os.listdir(attachments.message_dir(d, "m2"))
        text = "\n".join(lines)
        self.assertEqual(saved, ["8649178.csv"])
        self.assertIn("[link file saved:", text)
        self.assertIn("IVANOV,20.11.2026", text)
        share_call = next(c for c in http.calls if "/shares/" in c[1])
        self.assertTrue(share_call[1].startswith("https://graph.microsoft.com/v1.0/shares/u!"))

    def test_link_that_cannot_be_opened_says_so(self):
        def refuse(_):
            raise httpjson.HttpError(403, "x", '{"error":{"code":"accessDenied"}}')
        mail, _ = mail_with([("GET", "/shares/", refuse)] + thread_with(f"Voucher <{LINK}>"))
        lines = []
        with tempfile.TemporaryDirectory() as d:
            emi.show(mail, "m2", work_dir=d, out=lines.append)
        text = "\n".join(lines)
        self.assertIn("[link not opened: " + LINK, text)
        self.assertIn("HTTP 403", text)
        self.assertIn("accessDenied", text)

    def test_folder_link_gives_its_files(self):
        folder = {"name": "Vouchers", "folder": {"childCount": 2}}
        kids = {"value": [{"name": "a.csv", "size": 5, "file": {}, "@microsoft.graph.downloadUrl": "https://dl.example/a"},
                          {"name": "sub", "folder": {}}]}
        rules = [("GET", "/driveItem/children", kids), ("GET", "/driveItem", folder),
                 ("GET", "dl.example/a", b"x,y\n1,2")] + thread_with(LINK)
        mail, _ = mail_with(rules)
        with tempfile.TemporaryDirectory() as d:
            emi.show(mail, "m2", work_dir=d, out=lambda _: None)
            self.assertEqual(os.listdir(attachments.message_dir(d, "m2")), ["a.csv"])


if __name__ == "__main__":
    unittest.main()
