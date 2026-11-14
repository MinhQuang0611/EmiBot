"""OTA notices are answered by an intake note on the SynXis thread (Karen, 2026-11-14).

Karen: "việc reply cho booking OTA thì chỉ cần reply cho email Synxis no reply để chị biết được là Emi nhận thông tin
bổ sung vào intake sheet rồi. Chị thấy rất nhiều New booking hoặc cancel bị miss." Replaces the dev's 13/11 rule (the
OTA confirmation with the PDF, to the email printed in the booking). The note is written only after the rows, so a
notice with no note in its thread is one that isn't on the sheet; ota-audit lists the notices that have no rows."""
import os
import unittest
from types import SimpleNamespace
from unittest import mock

from tools import emi
from tools.state import State
from tools.tests.test_reply_every_email_1113 import NOTICE_3350, SUBJECT, SYNXIS

CANCEL_SUBJECT = "SynXis Res Cancelled (92777EF003350 )"
MOD_SUBJECT = "SynXis Res Confirmed (92777EF003350 ) (MODIFICATION)"


def row(n, action="NEW", ref="SynXis 92777EF003350 (Trip.com 1653718335673330)", **kw):
    return {"_row": n, "action": action, "booking_ref": ref, "guest_names": "JAMIL HUSSAIN", "arrival": "13/11/2026",
            "departure": "15/11/2026", "received_at": "10/11/2026 16:38", "rooms": "1", "room_code": "STD",
            "channel_type": "OTA", "company": "Trip.com", **kw}


class Sheet:
    def __init__(self, rows):
        self._rows = rows

    def rows(self):
        return list(self._rows)


class Mail:
    def __init__(self, messages):
        self.messages = messages  # id -> (sender, subject, body, received)
        self.drafts = {}

    def get_message_text(self, mid):
        sender, subject, body, _ = self.messages[mid]
        return {"from": {"emailAddress": {"address": sender}}, "subject": subject, "body": {"content": body}}

    def reply_draft_with_text(self, mid, text, reply_all=False, to=None, cc=None, **kw):
        d = {"id": f"d{len(self.drafts) + 1}", "text": text, "to": to, "cc": cc, "reply_all": reply_all, "source": mid}
        self.drafts[d["id"]] = d
        return d

    def get_draft(self, did):
        d = self.drafts.get(did)
        return d and {"id": did, "toRecipients": [{"emailAddress": {"address": a}} for a in d["to"] or []]}

    def list_inbox_since(self, since):
        return [{"id": mid, "subject": s, "receivedDateTime": rcv, "from": {"emailAddress": {"address": snd}}}
                for mid, (snd, s, _, rcv) in self.messages.items()]


class Base(unittest.TestCase):
    def setUp(self):
        p = mock.patch.dict(os.environ, {"EMI_DRAFT_MODE": "outlook"})
        p.start()
        self.addCleanup(p.stop)
        self.st = State(os.devnull + "-none")
        self.lines = []

    def note(self, mail, rows, mid="m1", ref="SynXis 92777EF003350 (Trip.com 1653718335673330)"):
        args = SimpleNamespace(message_id=mid, ref=ref, replaces="")
        return emi.ota_note(mail, Sheet(rows), self.st, args, out=self.lines.append)


class OtaNoteTest(Base):
    def test_the_note_goes_to_the_synxis_sender_only_and_names_the_rows(self):
        mail = Mail({"m1": (SYNXIS, SUBJECT, NOTICE_3350, "2026-11-10T09:38:00Z")})
        rows = [row(1937, transfer="THIẾU: Country"), row(1938), row(1939)]
        d = self.note(mail, rows)
        draft = mail.drafts[d["id"]]
        self.assertEqual(draft["to"], [SYNXIS])
        self.assertFalse(draft["reply_all"])
        for bit in ("Đã nhận và đã ghi vào intake sheet", "SynXis 92777EF003350", "JAMIL HUSSAIN",
                    "13/11/2026 – 15/11/2026", "1937 (NEW 1 STD)", "1939", "Còn thiếu (cột AJ): country"):
            self.assertIn(bit, draft["text"])
        self.assertNotIn("lodgingsupport@trip.com", str(draft))
        n, r = next(iter(self.st.data["reviews"].items()))
        self.assertEqual((r["kind"], r["source"], r["row"]), ("ota_note", "m1", 1937))

    def test_no_row_no_note(self):
        mail = Mail({"m1": (SYNXIS, SUBJECT, NOTICE_3350, "2026-11-10T09:38:00Z")})
        with self.assertRaises(emi.Refused) as e:
            self.note(mail, [row(5, ref="SynXis 92777EF009999")])
        self.assertIn("ROW NOT ON THE SHEET", str(e.exception))
        self.assertEqual(mail.drafts, {})

    def test_a_cancellation_needs_its_cancel_row(self):
        mail = Mail({"m1": (SYNXIS, CANCEL_SUBJECT, NOTICE_3350, "2026-11-12T09:38:00Z")})
        with self.assertRaises(emi.Refused) as e:
            self.note(mail, [row(1937)])
        self.assertIn("NO CANCEL ROW", str(e.exception))
        d = self.note(mail, [row(1937), row(2001, "CANCEL", received_at="12/11/2026 16:38")])
        text = mail.drafts[d["id"]]["text"]
        self.assertIn("Loại: huỷ", text)
        self.assertIn("2001 (CANCEL", text)
        self.assertNotIn("1937", text)

    def test_a_modification_lists_the_latest_rows(self):
        mail = Mail({"m1": (SYNXIS, MOD_SUBJECT, NOTICE_3350, "2026-11-12T09:38:00Z")})
        d = self.note(mail, [row(1937), row(2002, "CHANGE", received_at="12/11/2026 16:38", departure="16/11/2026")])
        text = mail.drafts[d["id"]]["text"]
        self.assertIn("Loại: thay đổi", text)
        self.assertIn("2002 (CHANGE", text)
        self.assertIn("16/11/2026", text)

    def test_one_note_per_notice(self):
        mail = Mail({"m1": (SYNXIS, SUBJECT, NOTICE_3350, "2026-11-10T09:38:00Z")})
        self.note(mail, [row(1937)])
        with self.assertRaises(emi.Refused):
            self.note(mail, [row(1937)])

    def test_not_for_an_agency_email(self):
        mail = Mail({"m1": ("res@agency.vn", "New booking 123456", "", "2026-11-10T09:38:00Z")})
        with self.assertRaises(emi.Refused) as e:
            self.note(mail, [row(1937, ref="123456")])
        self.assertIn("draft-reply", str(e.exception))

    def test_draft_reply_and_draft_confirmation_on_a_notice_point_to_ota_note(self):
        mail = Mail({"m1": (SYNXIS, SUBJECT, NOTICE_3350, "2026-11-10T09:38:00Z")})
        args = SimpleNamespace(message_id="m1", to="", cc="", internal=False, all=False)
        for kind in ("confirmation", "reply", "cancellation"):
            with self.assertRaises(emi.Refused, msg=kind) as e:
                emi.reply_recipients(mail, args, kind)
            self.assertIn("ota-note", str(e.exception))

    def test_other_no_reply_robots_keep_the_booking_email(self):
        mail = Mail({"m1": ("noreply@hotelnotice.example", "Your stay", "Email: guest@x.com", "")})
        args = SimpleNamespace(message_id="m1", to="", cc="", internal=False, all=False)
        self.assertEqual(emi.reply_recipients(mail, args, "reply"), (["guest@x.com"], []))


class DoneNeedsTheNoteTest(Base):
    def check(self, outcome, mid="m1", subject=SUBJECT):
        msg = {"from": {"emailAddress": {"address": SYNXIS}}, "subject": subject}
        emi.check_email_answered(self.st, mid, outcome, lambda: msg, out=self.lines.append)

    def test_rows_without_the_note_are_refused(self):
        with self.assertRaises(emi.Refused) as e:
            self.check("NEW rows 1937-1939 SynXis 92777EF003350")
        self.assertIn("NO OTA NOTE", str(e.exception))

    def test_an_old_confirmation_draft_is_not_the_note(self):
        self.st.data["reviews"]["760"] = {"draft_id": "d1", "status": "open", "source": "m1", "kind": "confirmation"}
        with self.assertRaises(emi.Refused):
            self.check("NEW row 1937; confirmation #760 before PDF")

    def test_the_note_passes_and_the_pair_names_it(self):
        self.st.data["reviews"]["761"] = {"draft_id": "d1", "status": "open", "source": "m1", "kind": "ota_note"}
        self.check("NEW rows 1937-1939; note #761")
        self.check("SynXis copy of Agoda 1783017402, row 1937; same booking as #761", mid="m2")
        with self.assertRaises(emi.Refused):
            self.check("same booking as #999", mid="m3")

    def test_still_never_without_a_row(self):
        with self.assertRaises(emi.Refused) as e:
            self.check("waits on Karen; no row written")
        self.assertIn("OTA BOOKING WITHOUT A ROW", str(e.exception))


class OtaAuditTest(Base):
    def test_missing_rows_and_cancels_are_named(self):
        mail = Mail({
            "a": (SYNXIS, "SynXis Res Confirmed (92777EF003350 )", NOTICE_3350, "2026-11-13T02:00:00Z"),
            "b": (SYNXIS, "SynXis Res Confirmed (92777EF003401 )", "Last Name : NGUYEN\nArrival : Friday, November 20, 2026",
                  "2026-11-13T03:00:00Z"),
            "c": (SYNXIS, "SynXis Res Cancelled (92777EF003350 )", "", "2026-11-13T04:00:00Z"),
            "d": ("noreply@agoda.com", "Agoda Booking ID 1783017402 - CONFIRMED", "", "2026-11-13T05:00:00Z"),
            "e": ("guest@gmail.com", "Hello", "", "2026-11-13T06:00:00Z"),
            "f": (SYNXIS, "SynXis Res Confirmed (92777EF003402 )", "Last Name : TRAN\nArrival : Friday, November 20, 2026",
                  "2026-11-13T07:00:00Z")})
        self.st.mark_processed("a", "NEW row 1937")
        self.st.mark_processed("c", "cancel")
        rows = [row(1937), row(1950, ref="Agoda 1783017402 / SynXis 92777EF003300"),
                row(1960, ref="Trip.com 999999999 / SynXis 92777EF003399", guest_names="TRAN VAN A",
                    arrival="20/11/2026")]
        counts = emi.ota_audit(mail, self.st, rows, days=7, out=self.lines.append)
        text = "\n".join(self.lines)
        self.assertEqual(counts, {"OK": 1, "CHECK": 2, "MISSING": 2})
        self.assertIn("OTA notices in the inbox", text)
        self.assertNotIn("Hello", text)
        self.assertIn("no row on the sheet", text)                 # b: nothing for 003401 or NGUYEN 20/11
        self.assertIn("cancelled, but no CANCEL row", text)       # c
        self.assertIn("surname TRAN + arrival 20/11/2026", text)  # f: found by name, never marked done → CHECK
        self.assertIn("never marked done by Emi", text)           # d: on the sheet, not done → CHECK


class OldDraftsTest(Base):
    """Dev 14/11: "các draft cũ nếu cần thì sửa đi" — the 13/11-rule drafts on OTA notices are denied and the notice
    gets its intake note; one Karen accepted is left to her."""

    def setUp(self):
        super().setUp()
        self.mail = Mail({"m1": (SYNXIS, SUBJECT, NOTICE_3350, "2026-11-13T09:00:00Z"),
                          "m2": (SYNXIS, "SynXis Res Confirmed (92777EF003999 )", "", "2026-11-13T10:00:00Z"),
                          "m3": (SYNXIS, "SynXis Res Confirmed (92777EF003351 )", "", "2026-11-13T11:00:00Z"),
                          "ta": ("res@agency.vn", "Booking 123456", "", "2026-11-13T11:00:00Z")})
        self.mail.deleted = []
        self.mail.delete_draft = self.mail.deleted.append
        self.mail.drafts.update({f"old{i}": {"id": f"old{i}", "to": ["x@y.z"], "text": "", "reply_all": True,
                                             "source": s, "cc": None} for i, s in enumerate(("m1", "m2", "m3", "ta"))})
        for i, (src, status, ref) in enumerate((("m1", "pending", "SynXis 92777EF003350 (Trip.com 1653718335673330)"),
                                                ("m2", "pending", "SynXis 92777EF003999"),
                                                ("m3", "approved", "SynXis 92777EF003351"),
                                                ("ta", "pending", "TVR123456"))):
            self.st.data["reviews"][str(870 + i)] = {
                "draft_id": f"old{i}", "status": status, "how": "reply", "kind": "confirmation", "source": src,
                "ref": ref, "row": 1937, "opened_at": "2026-11-13T09:10:00Z", "history": [], "text": "",
                **({"ota_row": {"channel_type": "OTA"}} if src != "ta" else {})}
        self.st.data["next_review"] = 900

    def test_list_only(self):
        found = emi.ota_old_drafts(self.mail, self.st, out=self.lines.append)
        self.assertEqual([n for n, _, _ in found], ["870", "871", "872"])
        emi.ota_drafts(self.mail, Sheet([row(1937)]), self.st, out=self.lines.append)
        self.assertEqual(self.mail.deleted, [])

    def test_fix(self):
        emi.ota_drafts(self.mail, Sheet([row(1937)]), self.st, fix=True, out=self.lines.append)
        text = "\n".join(self.lines)
        reviews = self.st.data["reviews"]
        self.assertEqual((reviews["870"]["status"], reviews["871"]["status"], reviews["872"]["status"],
                          reviews["873"]["status"]), ("denied", "denied", "approved", "pending"))
        self.assertEqual(self.mail.deleted, ["old0", "old1"])
        notes = [r for r in reviews.values() if r.get("kind") == "ota_note"]
        self.assertEqual([r["source"] for r in notes], ["m1"])            # m2 has no row: named, not forced
        self.assertIn("NO NOTE: ROW NOT ON THE SHEET", text)
        self.assertIn("accepted by Karen: left as it is", text)


if __name__ == "__main__":
    unittest.main()
