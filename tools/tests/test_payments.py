"""Payment chasing and confirmations due (Karen, 2026-11-04), and the review of 04/11's four drafts:
a stale availability sheet, direct rates past their printed date, plain-text drafts."""
import os
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

from tools import availability as avail
from tools import emi, payments, quote as quoting
from tools import intake_schema as schema
from tools.state import State

VN = timezone(timedelta(hours=7))
MAILBOX = "sales@haya-hotels.com"
AGENCY = "booking@agency.example"


def row(n, **kw):
    base = {"_row": n, "action": "NEW", "received_at": "02/11/2026 10:00", "channel_type": "TA", "company": "Threeland",
            "booking_ref": "31-130127", "ezfolio_group_code": "30742", "arrival": "13/01/2027", "departure": "16/01/2027",
            "total_vnd": "18000000", "status": "Definite", "pdf_link": "https://drive/x", "Remaining amount": "18000000",
            "COD": "48h after confirmation is received (deposit 50%); balance by 06/01/2027", "source_email": "Booking"}
    return {**base, **kw}


class FakeMail:
    def __init__(self, sent_at="2026-11-02T03:00:00Z", code="30742", attach=True, extra=()):
        self.sent_at, self.code, self.attach, self.extra = sent_at, code, attach, list(extra)
        self.searches = 0

    def search(self, text, top=10):
        self.searches += 1
        if self.sent_at is None or text != self.code:
            return list(self.extra)
        return [{"id": "conf", "from": {"emailAddress": {"address": MAILBOX}}, "sentDateTime": self.sent_at,
                 "hasAttachments": self.attach}] + list(self.extra)

    def get_message_bodies(self, message_id):
        return {"body": {"content": f"Group code: #{self.code}"},
                "toRecipients": [{"emailAddress": {"address": AGENCY}}, {"emailAddress": {"address": "haya@haya-hotels.com"}}],
                "ccRecipients": [{"emailAddress": {"address": "ops@agency.example"}}]}

    def get_draft(self, draft_id):
        return {"id": draft_id}


def due(rows, mail, st=None, now=None):
    st = st or State(os.devnull + "-none")
    return payments.due(rows, emi.booking_state, emi._parts, mail, st, MAILBOX,
                        now or datetime(2026, 11, 3, 20, 0, tzinfo=VN))


class DepositTest(unittest.TestCase):
    def test_waits_until_hour_40(self):
        # sent 02/11 10:00 Vietnam time; 40 hours = 04/11 02:00; hour 34 at 20:00 on 03/11 is not there yet
        r = due([row(5)], FakeMail(), now=datetime(2026, 11, 3, 20, 0, tzinfo=VN))
        self.assertEqual(r["remind"], [])

    def test_mark_overnight_is_drafted_at_the_last_run(self):
        r = due([row(5)], FakeMail(), now=datetime(2026, 11, 3, 21, 0, tzinfo=VN))
        self.assertEqual(len(r["remind"]), 1)
        i = r["remind"][0]
        self.assertEqual((i["which"], i["amount"]), ("deposit", 9000000))
        self.assertEqual(i["deadline"], "10:00 on 04/11/2026, Vietnam time (UTC+7)")
        self.assertEqual(i["sent"]["to"], [AGENCY])  # our own front office is not who pays

    def test_after_hour_40(self):
        r = due([row(5)], FakeMail(), now=datetime(2026, 11, 4, 9, 0, tzinfo=VN))
        text = payments.render(r, datetime(2026, 11, 4, 9, 0, tzinfo=VN))
        self.assertIn("REMIND deposit", text)
        self.assertIn("--kind deposit_reminder", text)
        self.assertIn(f"--to {AGENCY} --cc ops@agency.example", text)
        self.assertIn("- NHẮC THANH TOÁN #30742", text)

    def test_never_confirmed_is_reported_not_chased(self):
        r = due([row(5)], FakeMail(sent_at=None), now=datetime(2026, 11, 9, 9, 0, tzinfo=VN))
        self.assertEqual(r["remind"], [])
        self.assertEqual(len(r["no_confirmation"]), 1)

    def test_a_paid_deposit_on_an_older_row_counts(self):
        # live row 1103: the latest CHANGE has Payment 1 blank, Remaining is halved
        rows = [row(5), row(6, action="CHANGE", received_at="03/11/2026 09:00", **{"Payment 1": "", "Remaining amount": "9000000"})]
        self.assertEqual(due(rows, FakeMail(), now=datetime(2026, 11, 6, 9, 0, tzinfo=VN))["remind"], [])
        rows = [row(5, **{"Payment 1": "9000000"}), row(6, action="CHANGE", received_at="03/11/2026 09:00", **{"Remaining amount": ""})]
        self.assertEqual(due(rows, FakeMail(), now=datetime(2026, 11, 6, 9, 0, tzinfo=VN))["remind"], [])

    def test_one_reminder_then_overdue(self):
        st = State(os.devnull + "-none")
        st.record_draft("d1", "31-130127", 5, "deposit_reminder")
        r = due([row(5)], FakeMail(), st=st, now=datetime(2026, 11, 5, 9, 0, tzinfo=VN))
        self.assertEqual(r["remind"], [])
        self.assertEqual(len(r["overdue"]), 1)

    def test_a_late_first_reminder_still_goes(self):
        r = due([row(5)], FakeMail(), now=datetime(2026, 11, 8, 9, 0, tzinfo=VN))
        self.assertTrue(r["remind"][0]["passed"])
        self.assertIn("LATE", payments.render(r, datetime(2026, 11, 8, 9, 0, tzinfo=VN)))

    def test_possible_slip_is_read_first(self):
        slip = {"id": "s1", "from": {"emailAddress": {"address": AGENCY}}, "sentDateTime": "2026-11-03T02:00:00Z",
                "hasAttachments": True}
        r = due([row(5)], FakeMail(extra=[slip]), now=datetime(2026, 11, 4, 9, 0, tzinfo=VN))
        self.assertEqual(r["remind"], [])
        self.assertEqual(r["slip"][0]["sent"]["slips"], ["s1"])

    def test_who_is_never_chased(self):
        now = datetime(2026, 11, 8, 9, 0, tzinfo=VN)
        for kw in ({"channel_type": "OTA"}, {"channel_type": "Tour operator"}, {"channel_type": "Direct"},
                   {"status": "Tentative"}, {"pdf_link": ""}, {"action": "CANCEL"}, {"COD": "Paid in full 01/11/2026"},
                   {"arrival": "01/11/2026"}):
            r = due([row(5, **kw)], FakeMail(), now=now)
            self.assertEqual(r["remind"] + r["no_confirmation"], [], kw)

    def test_short_notice_goes_to_karen(self):
        r = due([row(5, arrival="08/11/2026", COD="Full payment before arrival 08/11/2026 (arrival < 7 days)")], FakeMail())
        self.assertEqual(len(r["short_notice"]), 1)
        self.assertEqual(r["remind"], [])


class BalanceTest(unittest.TestCase):
    PAID = {"Payment 1": "9000000", "Remaining amount": "9000000",
            "COD": "Balance 9,000,000 due 06/01/2027 (7 days before arrival)"}

    def test_the_day_before_from_0900(self):
        rows = [row(5, **self.PAID)]
        self.assertEqual(due(rows, FakeMail(), now=datetime(2027, 1, 5, 8, 59, tzinfo=VN))["remind"], [])
        i = due(rows, FakeMail(), now=datetime(2027, 1, 5, 9, 0, tzinfo=VN))["remind"][0]
        self.assertEqual((i["which"], i["amount"], i["deadline"]), ("balance", 9000000, "before 06/01/2027"))

    def test_nothing_paid_by_the_balance_date_chases_all_of_it(self):
        i = due([row(5)], FakeMail(), now=datetime(2027, 1, 5, 9, 0, tzinfo=VN))["remind"][0]
        self.assertEqual((i["which"], i["amount"]), ("balance", 18000000))

    def test_an_old_deposit_date_in_cod_is_not_the_balance_date(self):
        # live row 50: COD still says the deposit deadline, 10/10; the balance runs from the arrival
        rows = [row(5, arrival="02/12/2026", COD="10/10/2026 16:29", **{"Payment 1": "9000000", "Remaining amount": "9000000"})]
        self.assertEqual(due(rows, FakeMail(), now=datetime(2026, 11, 4, 15, 0, tzinfo=VN))["remind"], [])
        i = due(rows, FakeMail(), now=datetime(2026, 11, 24, 9, 0, tzinfo=VN))["remind"][0]
        self.assertEqual(i["deadline"], "before 25/11/2026")

    def test_no_search_when_nothing_is_near(self):
        mail = FakeMail()
        due([row(5, **self.PAID)], mail, now=datetime(2026, 11, 5, 9, 0, tzinfo=VN))
        self.assertEqual(mail.searches, 0)

    def test_paid_since_flags_the_unsent_reminder(self):
        st = State(os.devnull + "-none")
        st.record_draft("d1", "31-130127", 5, "deposit_reminder")
        st.data["reviews"]["44"] = {"draft_id": "d1"}
        r = due([row(5, **self.PAID)], FakeMail(), st=st, now=datetime(2026, 11, 5, 9, 0, tzinfo=VN))
        self.assertEqual(r["paid_unsent"][0]["review"], "44")
        self.assertIn("deny #44", payments.render(r, datetime(2026, 11, 5, 9, 0, tzinfo=VN)))


class ConfirmationsDueTest(unittest.TestCase):
    def run_it(self, rows, mail, st=None):
        return payments.needs_confirmation(rows, emi.booking_state, emi._parts, mail,
                                           st or State(os.devnull + "-none"), MAILBOX, date(2026, 11, 4))

    def test_built_and_never_confirmed(self):
        anex = row(1110, channel_type="Tour operator", company="Anex", booking_ref="112970549", ezfolio_group_code="30800")
        self.assertEqual([i["row"] for i in self.run_it([anex], FakeMail(code="other"))], [1110])

    def test_the_line_gives_every_room_row_and_the_booking_total(self):
        # Threeland 04/11: row 1057 alone against the whole PDF read as "a room type too many, total differs"
        rows = [row(1057, room_code="STD", total_vnd="9560000"), row(1058, room_code="SUP-DBL", total_vnd="9120000")]
        items = self.run_it(rows, FakeMail(code="other"))
        self.assertEqual((items[0]["rows"], items[0]["total"]), ([1057, 1058], 18680000))
        self.assertIn("booking rows 1057, 1058, total 18,680,000", payments.render_confirmations(items))

    def test_confirmed_from_outlook_by_a_person(self):
        self.assertEqual(self.run_it([row(5)], FakeMail()), [])

    def test_already_drafted(self):
        st = State(os.devnull + "-none")
        st.record_draft("d1", "31-130127", 5, "confirmation")
        self.assertEqual(self.run_it([row(5)], FakeMail(code="other"), st), [])

    def test_skipped(self):
        for kw in ({"channel_type": "OTA"}, {"pdf_link": ""}, {"received_at": "20/10/2026 10:00"},
                   {"action": "CANCEL"}, {"arrival": "01/11/2026"}):
            self.assertEqual(self.run_it([row(5, **kw)], FakeMail(code="other")), [], kw)


class ConfirmationInThePdfTest(unittest.TestCase):
    """Anex 112970549: a person's reply of 12:59 had the group code only in the PDF, so the booking kept coming up."""

    class Mail(FakeMail):
        def get_message_bodies(self, message_id):
            return {"body": {"content": "Dear Anex Reservation Team, thank you."}, "toRecipients": [], "ccRecipients": []}

        def search(self, text, top=10):
            return [{"id": "c", "subject": "RE: NEW RESERVATION No: 112970549;", "hasAttachments": self.attach,
                     "from": {"emailAddress": {"address": MAILBOX}}, "sentDateTime": "2026-11-04T05:59:00Z"}]

    def test_code_in_the_attachment_and_ref_in_the_subject(self):
        hit = payments.find_confirmation(self.Mail(), "30800", MAILBOX, frozenset({"112970549"}))
        self.assertEqual(hit["id"], "c")

    def test_a_number_that_matched_something_else(self):
        self.assertIsNone(payments.find_confirmation(self.Mail(), "30800", MAILBOX, frozenset({"999"})))
        self.assertIsNone(payments.find_confirmation(self.Mail(attach=False), "30800", MAILBOX, frozenset({"112970549"})))


class HoldTest(unittest.TestCase):
    def setUp(self):
        self.st = State(os.devnull + "-none")
        self.rows = [row(5)]
        self.sheet = SimpleNamespace(rows=lambda: self.rows)

    def due(self):
        return payments.needs_confirmation(self.rows, emi.booking_state, emi._parts, FakeMail(code="other"), self.st,
                                           MAILBOX, date(2026, 11, 4))

    def hold(self, **kw):
        args = dict(ref="31-130127", row=5, reason=["PDF", "total", "differs"], clear=False)
        with mock.patch.object(emi, "_row", return_value=self.rows[0]):
            emi.run_confirmation_hold(self.sheet, self.st, SimpleNamespace(**{**args, **kw}), out=lambda *_: None)

    def test_held_until_a_new_pdf(self):
        self.assertEqual(len(self.due()), 1)
        self.hold()
        self.assertEqual(self.due(), [])
        self.rows[0] = dict(self.rows[0], pdf_link="https://drive/new")
        self.assertEqual(len(self.due()), 1)

    def test_clear_and_a_reason_is_needed(self):
        self.hold()
        self.hold(clear=True)
        self.assertEqual(len(self.due()), 1)
        with self.assertRaises(emi.Refused):
            self.hold(reason=[])


class SpeedTest(unittest.TestCase):
    def test_parts_is_cached_and_not_shared_mutable(self):
        emi._parts.cache_clear()
        a, b = emi._parts("Agoda 1783017402 / SynXis 92777EF002717"), emi._parts("Agoda 1783017402 / SynXis 92777EF002717")
        self.assertIs(a, b)
        self.assertIsInstance(a, frozenset)
        self.assertEqual(emi._parts(None), frozenset())

    def test_a_big_sheet_is_quick(self):
        import time
        rows = [row(i, booking_ref=f"REF{i}", ezfolio_group_code=str(30000 + i)) for i in range(2, 1200)]
        t = time.time()
        due(rows, FakeMail(), now=datetime(2026, 11, 3, 20, 0, tzinfo=VN))
        self.assertLess(time.time() - t, 10)


class ReminderDraftTest(unittest.TestCase):
    def args(self, path, **kw):
        base = dict(message_id="conf", body=path, kind="deposit_reminder", ref="31-130127", row="5", to=AGENCY, cc="",
                    all=False, sender_only=False, internal=False, replaces="", subject_suffix="- PAYMENT REMINDER #30742")
        return SimpleNamespace(**{**base, **kw})

    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("Dear team,\n\nA reminder.")
        self.addCleanup(os.remove, self.path)
        self.mail = mock.Mock()
        self.mail.reply_draft_with_text.return_value = {"id": "d9"}
        self.mail.get_draft.return_value = {"id": "d9", "subject": "RE: x", "toRecipients": [], "ccRecipients": []}
        self.st = State(os.devnull + "-none")

    def test_suffix_reaches_the_mailbox_and_the_record(self):
        emi.draft_reply(self.mail, self.st, self.args(self.path), out=lambda *_: None)
        self.assertEqual(self.mail.reply_draft_with_text.call_args.kwargs["subject_suffix"], "- PAYMENT REMINDER #30742")
        self.assertTrue(self.st.reminder_drafted("31-130127", "deposit"))

    def test_one_reminder_per_deadline(self):
        self.st.record_draft("d1", "31-130127", 5, "deposit_reminder")
        with self.assertRaises(emi.Refused):
            emi.draft_reply(self.mail, self.st, self.args(self.path), out=lambda *_: None)

    def test_needs_ref_and_row(self):
        with self.assertRaises(emi.Refused):
            emi.draft_reply(self.mail, self.st, self.args(self.path, row=""), out=lambda *_: None)


TITLE = "Future Availability — HAYA — 2026-10-30_2027-02-26"
ROWS = [["Room Type", "Number Of Rooms", "30/10 Friday", "31/10 Saturday"],
        ["STD - STANDARD GARDEN", "10", "2", "2"],
        ["Occupancy %", "-11", "76.00%", "76.00%"]]


class StaleSheetTest(unittest.TestCase):
    """Karen 04/11, Aya Batyrova: the draft said Standard and Deluxe were free, read from a dead copy of the sheet."""

    def sheet(self, updated):
        return dict(avail.parse(TITLE, ROWS), as_of=updated.date())

    def test_age_comes_from_the_date_in_the_file_name(self):
        now = datetime(2026, 11, 4, 12, 0, tzinfo=VN)
        self.assertEqual(avail.stale(self.sheet(now), now), "")
        self.assertEqual(avail.stale(self.sheet(now - timedelta(days=1)), now), "")  # yesterday's export still counts
        self.assertIn("dated 30/10/2026, 5 day(s) ago", avail.stale(self.sheet(datetime(2026, 10, 30, tzinfo=VN)), now))
        self.assertEqual(avail.stale(avail.parse(TITLE, ROWS), now), "")  # parse() alone: age unknown

    def folder(self, files, seen=None):
        def call(method, url, **kw):
            if seen is not None:
                seen.append(url)
            if "files?q=" in url:
                return {"files": files}
            if "/values/" in url:
                return {"values": ROWS}
            return {"sheets": [{"properties": {"title": "t"}}]}
        return call

    def test_the_folder_gives_haya_never_palma(self):
        seen = []
        files = [{"id": "PDF", "name": "BẢNG GIÁ CHO TA HAYA HOTEL.pdf", "modifiedTime": "2026-11-04T07:00:00Z"},
                 {"id": "PALMA", "name": "Future Availability — Palma — 2026-10-30_2027-03-03", "modifiedTime": "2026-11-04T07:00:00Z"},
                 {"id": "HAYA", "name": TITLE, "modifiedTime": "2026-11-04T06:50:08.831Z"},
                 {"id": "OLD", "name": "Future Availability — HAYA — 2026-10-29_2027-02-26", "modifiedTime": "2026-10-29T06:50:08Z"}]
        data = avail.load(self.folder(files, seen), "FOLDER")
        read = " ".join(u for u in seen if "spreadsheets/" in u)
        self.assertIn("spreadsheets/HAYA", read)
        for other in ("PALMA", "PDF", "OLD"):
            self.assertNotIn(f"spreadsheets/{other}", read)
        self.assertEqual(data["as_of"], date(2026, 10, 30))  # the first date in the file's name
        self.assertIn("%27FOLDER%27%20in%20parents", seen[0])
        self.assertIn("trashed%3Dfalse", seen[0])

    def test_the_dates_in_the_name_pick_the_file_not_the_listing_order(self):
        seen = []
        files = [{"id": "OLDER", "name": "Future Availability — HAYA — 2026-10-29_2027-02-26"},
                 {"id": "NO-DATES", "name": "Future Availability — HAYA — copy"},
                 {"id": "LATEST", "name": TITLE}]
        self.assertEqual(avail.load(self.folder(files, seen), "FOLDER")["start"], date(2026, 10, 30))
        self.assertTrue(any("spreadsheets/LATEST" in u for u in seen))
        self.assertFalse(any("spreadsheets/OLDER" in u or "spreadsheets/NO-DATES" in u for u in seen))

    def test_same_name_twice_takes_the_newer_file(self):
        # Exports come hourly under the same name for the day; Drive lists them newest first (orderBy createdTime desc)
        seen = []
        files = [{"id": "NEWER", "name": TITLE}, {"id": "EARLIER", "name": TITLE}]
        avail.load(self.folder(files, seen), "FOLDER")
        self.assertIn("orderBy=createdTime%20desc", seen[0])
        self.assertTrue(any("spreadsheets/NEWER" in u for u in seen))
        self.assertFalse(any("spreadsheets/EARLIER" in u for u in seen))

    def test_no_haya_file_is_refused_not_guessed(self):
        palma = [{"id": "PALMA", "name": "Future Availability — Palma — 2026-11-04_2027-03-03", "modifiedTime": "2026-11-04T07:00:00Z"}]
        with self.assertRaises(avail.AvailabilityError):
            avail.load(self.folder(palma), "FOLDER")

    def test_availability_never_says_it_fits(self):
        args = SimpleNamespace(arrival="30/10/2026", departure="31/10/2026", alloc="STD:1")
        lines = []
        with mock.patch.object(emi, "_today_vn", return_value=date(2026, 10, 25)):
            emi.run_availability(args, self.sheet(datetime(2026, 10, 1, tzinfo=VN)), out=lines.append)
        text = "\n".join(lines)
        self.assertIn("AVAILABILITY STALE", text)
        self.assertIn("NOT VERIFIED (stale sheet): STD:1", text)
        self.assertNotIn("FITS:", text)

    def test_stop_sales_not_checked_on_a_stale_sheet(self):
        lines = []
        self.assertEqual(emi.run_stop_sales(self.sheet(datetime(2026, 10, 1, tzinfo=VN)), out=lines.append), {})
        self.assertIn("STOP SALES NOT CHECKED", lines[0])

    def quote_args(self, channel):
        return SimpleNamespace(arrival="30/10/2026", departure="31/10/2026", adults=2, children="", rooms=None,
                               room_type="STD", alloc=None, twin=False, indian=False, channel=channel)

    def test_quote_marks_the_option_not_verified(self):
        lines = []
        with mock.patch.object(emi, "_today_vn", return_value=date(2026, 10, 1)):
            emi.run_quote(self.quote_args("Direct"), out=lines.append,
                          availability=self.sheet(datetime(2026, 9, 1, tzinfo=VN)))
        text = "\n".join(lines)
        self.assertIn("NOT VERIFIED (stale sheet)", text)
        self.assertNotIn("NOT AVAILABLE", text)

    def test_stop_sale_is_for_travel_agencies_only(self):
        fresh = datetime(2026, 10, 1, tzinfo=VN)
        with mock.patch.object(emi, "_today_vn", return_value=date(2026, 10, 1)), \
                mock.patch.object(emi, "_stale", return_value=""):
            direct, ta = [], []
            emi.run_quote(self.quote_args("Direct"), out=direct.append, availability=self.sheet(fresh))
            emi.run_quote(self.quote_args("TA"), out=ta.append, availability=self.sheet(fresh))
        self.assertNotIn("stop-sale", "\n".join(direct).lower())
        self.assertIn("NOT AVAILABLE — stop-sale", "\n".join(ta))


class NoBlankRateTest(unittest.TestCase):
    """Dev 04/11: rows 1059, 1152 and 1153 were left without a price because the email had none."""

    def errors(self, **kw):
        rec = {"action": "NEW", "company": "MG", "channel_type": "OTA", "arrival": "14/11/2026", "departure": "22/11/2026",
               "room_code": "DLX-SV", "rooms": "3", "total_vnd": "", "Average rate per night after discount": "",
               "rate_per_night_vnd": "", "missing_info": ""}
        return [e for e in schema.check_row({**rec, **kw})[0] if e.startswith("rate_per_night_vnd: the email")]

    def test_refused_even_with_a_reason_about_the_voucher(self):
        self.assertTrue(self.errors(missing_info="REQUIRED blank: rate_per_night_vnd – MG BedBank voucher not received"))

    def test_a_filled_rate_passes(self):
        self.assertEqual(self.errors(rate_per_night_vnd="2000000"), [])

    def test_no_table_for_the_room_and_fun_and_sun_stay_blank(self):
        self.assertEqual(self.errors(missing_info="REQUIRED blank: rate_per_night_vnd – no rate table for TW-DLX"), [])
        self.assertEqual(self.errors(company="Fun and Sun"), [])

    def test_a_row_with_no_room_or_dates_cannot_be_priced_yet(self):
        self.assertEqual(self.errors(room_code=""), [])
        self.assertEqual(self.errors(arrival=""), [])

    def test_a_row_already_built_is_not_blocked(self):
        self.assertEqual(self.errors(pdf_link="https://drive/x"), [])


class PlainTextDraftTest(unittest.TestCase):
    def test_html_in_the_text_is_refused(self):
        with self.assertRaises(emi.Refused):
            emi.check_no_gaps("<p>Dear Michał Midzio,</p>\n<p>Best,<br>Reservations Team</p>")


if __name__ == "__main__":
    unittest.main()
