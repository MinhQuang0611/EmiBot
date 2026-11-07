"""Dev, 2026-11-07 (Pegas 11124455 sat 3.5 h between the booking and its build): "cứ cho Emi build draft, khi nào tool
xuất PDF thì attach sau. Ghi note là DO NOT SEND UNTIL PDF IS ATTACHED". draft-confirmation --before-pdf writes the
confirmation with the red line and placeholders; confirmation-attach puts the build tool's PDF on the same draft."""
import os
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

from tools import emi, payments, review
from tools.graph_mail import DO_NOT_SEND, email_html
from tools.state import State
from tools.tests.test_tools import mail_with

VN = timezone(timedelta(hours=7))
LINK = "https://drive.google.com/file/d/1HnZMlqfHYERA2Gf39QuP5yfWBUxRvsil/view?usp=drivesdk"
PEGAS = {"action": "NEW", "received_at": "07/11/2026 12:06", "source_email": "New reservation from Pegas Touristik",
         "channel_type": "Tour operator", "company": "Pegas", "booking_ref": "Pegas 11124455",
         "guest_names": "MR KULNIS ALIAKSANDR; MRS AKSENOVA OLGA", "arrival": "08/01/2027", "departure": "19/01/2027",
         "room_code": "STD", "rooms": "1", "total_vnd": "24150000", "status": "Definite", "_row": 1586}
BUILT = {"ezfolio_group_code": "30901", "confirmation_no": "26533", "pdf_link": LINK, "ez_status": "done",
         "ez_processed_at": "2026-11-07T15:33:33"}
BODY = ("Dear Pegas Team,\n\nThank you for your reservation.\n\nWe are pleased to confirm the following booking:\n\n"
        "Ref: Pegas 11124455\nGuests: MR KULNIS ALIAKSANDR; MRS AKSENOVA OLGA\n"
        "Dates: 08/01/2027 – 19/01/2027 (11 nights)\nRoom: 1 Standard Double, 2 adults\nMeal plan: HB\n"
        "Hotel confirmation no.: [CONF NO]\nGroup code: #[GROUP CODE]\n\nPlease find attached our confirmation.\n\n"
        "Best regards,\nReservations Team\nHAYA Hotel Phu Quoc, Trademark Collection by Wyndham\nsales@haya-hotels.com")


class FakeSheet:
    def __init__(self, *rows):
        self.data = [dict(r) for r in rows]

    def rows(self):
        return [dict(r) for r in self.data]


def outlook_mail(draft_html):
    return mail_with([
        ("POST", "/createReply", {"id": "d1", "subject": "RE: New reservation"}),
        ("GET", "/messages/d1?$select=id", {"id": "d1", "subject": "RE: New reservation", "isDraft": True,
                                            "categories": ["Emi"], "toRecipients": []}),
        ("GET", "/messages/d1?$select=body", lambda _: {"body": {"content": draft_html[0]}}),
        ("PATCH", "/messages/d1", lambda b: draft_html.__setitem__(0, b["body"]["content"]) if "body" in b else {}),
    ])


class BeforePdfTest(unittest.TestCase):
    def setUp(self):
        self._mode = os.environ.pop("EMI_DRAFT_MODE", None)
        self.addCleanup(lambda: os.environ.__setitem__("EMI_DRAFT_MODE", self._mode) if self._mode else None)
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.body = os.path.join(self.dir.name, "b.txt")
        self.write(BODY)
        self.st = State(os.path.join(self.dir.name, "s.json"))
        self.html = ["<html><body><div>quoted thread</div></body></html>"]
        self.mail, self.http = outlook_mail(self.html)

    def write(self, text):
        with open(self.body, "w", encoding="utf-8") as f:
            f.write(text)

    def args(self, **kw):
        a = dict(message_id="m1", row=1586, body=self.body, all=False, to="", cc="", subject="", attach=[],
                 before_pdf=True, replaces="")
        a.update(kw)
        return SimpleNamespace(**a)

    def draft(self, sheet=None):
        emi.draft_confirmation(self.mail, sheet or FakeSheet(PEGAS), self.st, self.args(), out=lambda *_: None)
        return "1"

    def fake_pdf(self, sheet, row, out=print):
        path = os.path.join(self.dir.name, "conf.pdf")
        with open(path, "wb") as f:
            f.write(b"%PDF-1.4 conf")
        return path, "Pegas 11124455 confirmation.pdf", "application/pdf", b"%PDF-1.4 conf"

    def attach(self, n, sheet, now=datetime(2026, 11, 7, 15, 40, tzinfo=VN)):
        with mock.patch.object(emi, "pdf_fetch", self.fake_pdf):
            emi.confirmation_attach(self.mail, sheet, self.st, SimpleNamespace(n=n, attach=[]), out=lambda *_: None,
                                    now=now)

    def test_drafted_without_pdf_red_line_first_and_waiting(self):
        n = self.draft()
        self.assertIn(DO_NOT_SEND, self.html[0])
        self.assertIn('color:#FF0000">' + DO_NOT_SEND, self.html[0])
        self.assertFalse([c for c in self.http.calls if c[1].endswith("/attachments")])
        r = self.st.data["reviews"][n]
        self.assertTrue(r["awaiting_pdf"])
        self.assertTrue(r["text"].startswith(DO_NOT_SEND))
        self.assertEqual(self.st.confirmation_drafted(), set())
        self.assertEqual(self.st.awaiting_pdf(), {("Pegas 11124455", 1586): "d1"})
        with self.assertRaises(emi.Refused):  # one draft per booking
            emi.draft_confirmation(self.mail, FakeSheet(PEGAS), self.st, self.args(), out=lambda *_: None)

    def test_accept_refused_until_the_pdf_is_on(self):
        n = self.draft()
        with self.assertRaises(review.ReviewError) as e:
            review.accept(self.mail, self.st, None, n, out=lambda *_: None)
        self.assertIn("PDF", str(e.exception))

    def test_template_blank_or_missing_group_token_refused(self):
        self.write(BODY.replace("#[GROUP CODE]", "#[group code]"))
        with self.assertRaises(emi.Refused) as e:
            self.draft()
        self.assertIn("#[group code]", str(e.exception))
        self.write(BODY.replace("Group code: #[GROUP CODE]\n", ""))
        with self.assertRaises(emi.Refused):
            self.draft()
        self.assertFalse([c for c in self.http.calls if "createReply" in c[1]])

    def test_built_row_refuses_before_pdf(self):
        with self.assertRaises(emi.Refused):
            self.draft(FakeSheet({**PEGAS, **BUILT}))

    def test_job2_names_the_draft_to_attach_to(self):
        n = self.draft()
        built = {**PEGAS, **BUILT}

        class NoConfirmation:
            def search(self, *a, **k):
                return []

            def list_sent_since(self, *a, **k):
                return []

        with mock.patch.object(payments, "find_confirmation", lambda *a, **k: None):
            items = payments.needs_confirmation([built], emi.booking_state, emi._parts, NoConfirmation(), self.st,
                                                "sales@haya-hotels.com", date(2026, 11, 7))
        self.assertEqual(items[0]["attach"], n)
        self.assertIn(f"confirmation-attach {n}", payments.render_confirmations(items))

    def test_attach_fills_placeholders_removes_line_adds_pdf(self):
        n = self.draft()
        self.html[0] = self.html[0].replace("quoted thread", "quoted thread, and a person's own edit")
        self.attach(n, FakeSheet({**PEGAS, **BUILT}))
        self.assertNotIn(DO_NOT_SEND, self.html[0])
        self.assertIn("#30901", self.html[0])
        self.assertIn("26533", self.html[0])
        self.assertIn("a person's own edit", self.html[0])
        att = [c[2] for c in self.http.calls if c[1].endswith("/messages/d1/attachments")]
        self.assertEqual([a["name"] for a in att], ["Pegas 11124455 confirmation.pdf"])
        r = self.st.data["reviews"][n]
        self.assertFalse(r["awaiting_pdf"])
        self.assertNotIn(DO_NOT_SEND, r["text"])
        self.assertIn("Group code: #30901", r["text"])
        self.assertEqual(self.st.confirmation_drafted(), {("Pegas 11124455", 1586)})
        self.assertEqual(self.st.awaiting_pdf(), {})
        review.accept(self.mail, self.st, None, n, out=lambda *_: None)  # now it can be approved

    def test_attach_follows_the_row_when_the_build_tool_inserted_rows_above(self):
        n = self.draft()
        self.attach(n, FakeSheet({**PEGAS, **BUILT, "_row": 1592}))
        self.assertIn("#30901", self.html[0])

    def test_not_built_yet_nothing_changes(self):
        n = self.draft()
        before = list(self.http.calls)
        with self.assertRaises(emi.Refused) as e:
            self.attach(n, FakeSheet({**PEGAS, "ez_status": "needs_review"}))
        self.assertIn("needs_review", str(e.exception))
        self.assertFalse([c for c in self.http.calls[len(before):] if c[0] in ("PATCH", "POST")])
        self.assertTrue(self.st.data["reviews"][n]["awaiting_pdf"])

    def test_deadline_counts_48_hours_from_the_attach(self):
        ta = {**PEGAS, "channel_type": "TA", "company": "Footprint", "booking_ref": "031P0127J"}
        self.write("Kính gửi chị Lan,\n\nKhách sạn xin xác nhận đặt phòng như sau:\n\nMã đoàn: #[GROUP CODE]\n"
                   "Số xác nhận: [CONF NO]\nTổng tiền: 3.400.000 VND (đã bao gồm ăn sáng và 8% VAT)\n\n"
                   "– Đặt cọc 50% = 1.700.000 VND trước [DEPOSIT DEADLINE] (giờ Việt Nam, UTC+7), 48 giờ kể từ khi "
                   "nhận xác nhận này.\n\nTên tài khoản: CÔNG TY TNHH DU LỊCH PHƯƠNG NGUYỄN PHÚ QUỐC\n"
                   "Số tài khoản: 1020729617\n\nTrân trọng,\nReservations Team")
        self.draft(FakeSheet(ta))
        self.attach("1", FakeSheet({**ta, **BUILT}), now=datetime(2026, 11, 7, 16, 31, 20, tzinfo=VN))
        self.assertIn("trước 16:31 ngày 09/11/2026 (giờ Việt Nam, UTC+7)", self.st.data["reviews"]["1"]["text"])
        self.assertIn("16:31 ngày 09/11/2026", self.html[0])

    def test_draft_gone_before_its_pdf_is_reported_and_dropped(self):
        n = self.draft()
        mail, _ = mail_with([("GET", "/messages/d1?$select=id", {"id": "d1", "isDraft": False})])
        lines = []
        emi.tidy_awaiting(mail, FakeSheet(PEGAS), self.st, out=lines.append)
        self.assertIn(f"WARNING #{n}", lines[0])
        self.assertEqual(self.st.awaiting_pdf(), {})
        self.assertEqual(self.st.data["reviews"][n]["status"], "gone")

    def test_cancelled_meanwhile_named_for_deny(self):
        n = self.draft()
        lines = []
        cancel = {**PEGAS, "action": "CANCEL", "status": "Cancelled", "_row": 1600}
        emi.tidy_awaiting(self.mail, FakeSheet(PEGAS, cancel), self.st, out=lines.append)
        self.assertTrue(any(line.startswith(f"DENY #{n}") for line in lines), lines)

    def test_pegas_robot_confirmation_goes_to_the_reservation_desk(self):
        self.mail, self.http = mail_with([
            ("GET", "/messages/m1", {"from": {"emailAddress": {"address": "pegasys-notifications@pegast.su"}}}),
            ("POST", "/createReply", {"id": "d1", "subject": "RE: Reminder: New booking #11124455"}),
            ("GET", "/messages/d1?$select=body", {"body": {"content": "<html><body></body></html>"}})])
        self.draft()
        patch = next(b for m, u, b in self.http.calls if m == "PATCH" and b and "toRecipients" in b)
        self.assertEqual(patch["toRecipients"], [{"emailAddress": {"address": "reservation.vtm@pegast.com"}}])

    def test_red_line_rendered_bold_red(self):
        self.assertIn('<span style="color:#FF0000">' + DO_NOT_SEND, email_html(DO_NOT_SEND + "\n\nDear X,"))


if __name__ == "__main__":
    unittest.main()
