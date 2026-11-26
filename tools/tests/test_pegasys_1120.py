"""Dev, 2026-11-20: "giờ Emi cần tự confirm trên extranet Pegas". Emi presses Confirm on provider.pegasys.pegast.com
once HAYA's confirmation (with the EZFOLIO PDF) has gone to Pegas after the robot's latest notice; never on a decline,
a cancellation, a booking not built, or before the confirmation is sent (Palma's rule, tools/pegasys.py)."""
import io
import json
import os
import tempfile
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone

from tools import pegasys
from tools.state import State

VN = timezone(timedelta(hours=7))
NOW = datetime(2026, 11, 20, 10, 0, tzinfo=VN)
GUID = "3f2a9c1e-7b4d-4e8a-9c2f-1a2b3c4d5e6f"
MAILBOX = "sales@haya-hotels.com"


def booking_page(status, version="v1", conf=""):
    return (f'<html><form><input name="__RequestVerificationToken" type="hidden" value="tok-page" /></form>'
            f'<article class="booking" data-version="{version}">'
            f'<input id="Status" type="hidden" value="{status}" />'
            f'<input type="text" id="ConfirmationNumber" value="{conf}" /></article></html>')


LOGIN_PAGE = ('<html><form action="/Login"><input type="password" name="password" />'
              '<input name="__RequestVerificationToken" type="hidden" value="tok-login" /></form></html>')


class Resp(io.BytesIO):
    def __init__(self, url, text):
        super().__init__(text.encode())
        self.url = url

    def geturl(self):
        return self.url


class FakeSite:
    """The provider site: login, one booking, Confirm and UpdateConfirmationNumber, checking expectedVersion."""

    def __init__(self, status="New", conf="", fail_confirm=False):
        self.status, self.conf, self.version, self.logged_in = status, conf, 1, False
        self.fail_confirm = fail_confirm
        self.calls = []

    def open(self, req, timeout=None):
        path = req.full_url.replace(pegasys.BASE, "")
        body = json.loads(req.data) if req.data else None
        self.calls.append((req.get_method(), path, body, dict(req.header_items())))
        if path == "/Login" and req.get_method() == "GET":
            return Resp(req.full_url, LOGIN_PAGE)
        if path == "/Login":
            assert req.get_header("Requestverificationtoken") == "tok-login"
            self.logged_in = body["username"] == "haya" and body["password"] == "pw"
            return Resp(req.full_url, json.dumps({"isSucceeded": self.logged_in}))
        if not self.logged_in:
            return Resp(pegasys.BASE + "/Login?ReturnUrl=x", LOGIN_PAGE)
        if path.startswith("/HotelBookings/"):
            return Resp(req.full_url, booking_page(self.status, f"v{self.version}", self.conf))
        if body.get("expectedVersion") != f"v{self.version}":
            return Resp(req.full_url, json.dumps({"isSucceeded": False, "error": "version"}))
        if path == "/HotelServiceListView/Confirm":
            if self.fail_confirm:
                raise urllib.error.HTTPError(req.full_url, 500, "boom", {}, io.BytesIO(b"server error"))
            self.status = {"New": "Confirmed", "Changed": "Confirmed changes"}[self.status]
        elif path == "/HotelServiceEditView/UpdateConfirmationNumber":
            assert body["lastConfirmationNumber"] == self.conf
            self.conf = body["confirmationNumber"]
        self.version += 1
        return Resp(req.full_url, json.dumps({"isSucceeded": True}))

    def presses(self):
        return [c[1] for c in self.calls if c[0] == "POST" and c[1] != "/Login"]


def notice(mid, bid, at, subject="New reservation from Pegas Touristik"):
    link = f"https://provider.pegasys.pegast.com/HotelBookings/{bid}/{GUID}"
    return {"id": mid, "subject": f"{subject} (#{bid}, Haya)", "receivedDateTime": at,
            "from": {"emailAddress": {"address": pegasys.ROBOT}},
            "_html": f'<p>Please confirm.</p><a href="{link}">Open booking</a>'}


def sent(mid, bid, at, files=True, to="reservation.vtm@pegast.com", subject=None):
    return {"id": mid, "subject": subject or f"RE: New reservation from Pegas Touristik (#{bid}, Haya)",
            "sentDateTime": at, "hasAttachments": files, "from": {"emailAddress": {"address": MAILBOX}},
            "toRecipients": [{"emailAddress": {"address": to}}]}


class FakeMail:
    def __init__(self, *msgs):
        self.msgs = {m["id"]: m for m in msgs}
        self.html_reads = 0

    def list_from_since(self, address, since):
        return [m for m in self.msgs.values() if m["from"]["emailAddress"]["address"] == address
                and m["receivedDateTime"] >= since]

    def get_message_html(self, mid):
        self.html_reads += 1
        return self.msgs[mid].get("_html", "")

    def search(self, text, top=10):
        return [m for m in self.msgs.values() if text in m["subject"]]

    def get_message_bodies(self, mid):
        return self.msgs[mid]


def row(n, **kw):
    r = {"_row": n, "action": "NEW", "received_at": "18/11/2026 09:00", "booking_ref": "Pegas 11138234",
         "channel_type": "Tour operator", "company": "Pegas", "ez_status": "done", "pdf_link": "https://drive/x.pdf",
         "ezfolio_group_code": "#31200", "confirmation_no": "26990"}
    r.update(kw)
    return r


def state_of(rows, ref):
    return [r for r in rows if r["booking_ref"] == ref]


class PegasysTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(self.path)
        self.st = State(self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def due(self, mail, rows):
        return pegasys.due(mail, rows, state_of, self.st, MAILBOX, NOW)

    def client(self, site):
        return pegasys.Pegasys("haya", "pw", opener=site)

    # --- which bookings ---

    def test_confirmation_sent_after_notice_is_due(self):
        mail = FakeMail(notice("n1", "11138234", "2026-11-18T02:00:00Z"), sent("s1", "11138234", "2026-11-18T09:00:00Z"))
        items, lines = self.due(mail, [row(1)])
        self.assertEqual([(i["booking_id"], i["guid"], i["group"]) for i in items], [("11138234", GUID, "31200")])
        self.assertEqual(lines, [])

    def test_not_sent_yet_or_sent_bare_is_not_due(self):
        for extra in ([], [sent("s1", "11138234", "2026-11-18T09:00:00Z", files=False)],
                      [sent("s1", "11138234", "2026-11-18T01:00:00Z")],  # before the notice
                      [sent("s1", "11138234", "2026-11-18T09:00:00Z", to="haya@haya-hotels.com")],
                      [sent("s1", "11138234", "2026-11-18T09:00:00Z", subject="Payment reminder 11138234")]):
            mail = FakeMail(notice("n1", "11138234", "2026-11-18T02:00:00Z"), *extra)
            self.assertEqual(self.due(mail, [row(1)])[0], [], extra)

    def test_cancelled_or_unbuilt_is_not_due(self):
        mail = FakeMail(notice("n1", "11138234", "2026-11-18T02:00:00Z"), sent("s1", "11138234", "2026-11-18T09:00:00Z"))
        self.assertEqual(self.due(mail, [row(1), row(2, action="CANCEL")])[0], [])
        bare = FakeMail(notice("n1", "11138234", "2026-11-18T02:00:00Z"))
        self.assertEqual(self.due(bare, [row(1, ez_status="needs_review")])[0], [])
        self.assertEqual(self.due(bare, [row(1, pdf_link="")])[0], [])

    def test_unbuilt_but_confirmation_sent_is_due(self):
        # dev 26/11, Pegas 11152394: the revised PDF went to Pegas while the build tool's change waited on Long;
        # the site stayed "Changed" a day. The confirmation a person sent is the signal.
        mail = FakeMail(notice("n1", "11138234", "2026-11-18T02:00:00Z"), sent("s1", "11138234", "2026-11-18T09:00:00Z"))
        [item] = self.due(mail, [row(1, action="CHANGE", ez_status="needs_review")])[0]
        self.assertEqual(item["sent"]["id"], "s1")
        self.assertEqual(item["group"], "31200")

    def test_not_on_the_sheet_is_a_line(self):
        mail = FakeMail(notice("n1", "11138234", "2026-11-18T02:00:00Z"), sent("s1", "11138234", "2026-11-18T09:00:00Z"))
        items, lines = self.due(mail, [])
        self.assertEqual(items, [])
        self.assertIn("not on the intake sheet", lines[0])

    def test_change_notice_waits_for_its_own_confirmation(self):
        mail = FakeMail(notice("n1", "11138234", "2026-11-18T02:00:00Z"), sent("s1", "11138234", "2026-11-18T09:00:00Z"),
                        notice("n2", "11138234", "2026-11-19T02:00:00Z", subject="Change of booking"))
        self.assertEqual(self.due(mail, [row(1)])[0], [])  # the first confirmation came before the change
        mail.msgs["s2"] = sent("s2", "11138234", "2026-11-19T05:00:00Z")
        self.assertEqual(self.due(mail, [row(1)])[0][0]["notice_at"], "2026-11-19T02:00:00Z")

    def test_links_read_once(self):
        mail = FakeMail(notice("n1", "11138234", "2026-11-18T02:00:00Z"))
        self.due(mail, [row(1)])
        self.due(mail, [row(1)])
        self.assertEqual(mail.html_reads, 1)

    # --- pressing ---

    def test_new_is_confirmed_and_recorded_once(self):
        site = FakeSite("New")
        mail = FakeMail(notice("n1", "11138234", "2026-11-18T02:00:00Z"), sent("s1", "11138234", "2026-11-18T09:00:00Z"))
        items, _ = self.due(mail, [row(1)])
        out = []
        pegasys.run(items, self.client(site), self.st, out=out.append)
        self.assertEqual(site.status, "Confirmed")
        self.assertEqual(site.presses(), ["/HotelServiceListView/Confirm"])
        self.assertIn("New -> Confirmed", out[0])
        self.assertIn("Confirmation # left as it is", out[0])
        confirm = next(c for c in site.calls if c[1] == "/HotelServiceListView/Confirm")
        self.assertEqual(confirm[2], {"bookingId": 11138234, "hotelServiceGuid": GUID, "expectedVersion": "v1",
                                      "displayOptions": "SSRs, SpecialFares", "showHotelName": "False"})
        headers = {k.lower(): v for k, v in confirm[3].items()}
        self.assertEqual((headers["x-requested-with"], headers["clienttimezone"]), ("XMLHttpRequest", "-420"))
        self.assertEqual(self.due(mail, [row(1)])[0], [])  # done for this notice

    def test_group_code_written_as_confirmation_number(self):
        site = FakeSite("New")
        mail = FakeMail(notice("n1", "11138234", "2026-11-18T02:00:00Z"), sent("s1", "11138234", "2026-11-18T09:00:00Z"))
        items, _ = self.due(mail, [row(1)])
        pegasys.run(items, self.client(site), self.st, field="group", out=lambda *_: None)
        self.assertEqual((site.status, site.conf), ("Confirmed", "31200"))
        self.assertEqual(site.presses(), ["/HotelServiceListView/Confirm",
                                          "/HotelServiceEditView/UpdateConfirmationNumber"])

    def test_changed_becomes_confirmed_changes(self):
        site = FakeSite("Changed", conf="31200")
        item = {"booking_id": "11138234", "guid": GUID, "group": "31200"}
        status, line = pegasys.press(self.client(site), item, field="group")
        self.assertEqual(status, "Confirmed changes")
        self.assertIn("Confirmation # already 31200", line)

    def test_already_confirmed_or_cancelled_is_not_pressed(self):
        for status in ("Confirmed", "Cancelled"):
            site = FakeSite(status)
            pegasys.press(self.client(site), {"booking_id": "11138234", "guid": GUID}, field="")
            self.assertEqual(site.presses(), [], status)

    def test_dry_run_presses_nothing(self):
        site = FakeSite("New")
        status, line = pegasys.press(self.client(site), {"booking_id": "11138234", "guid": GUID}, dry_run=True)
        self.assertEqual((site.status, site.presses()), ("New", []))
        self.assertIn("would press Confirm", line)

    def test_failure_is_reported_and_retried(self):
        site = FakeSite("New", fail_confirm=True)
        mail = FakeMail(notice("n1", "11138234", "2026-11-18T02:00:00Z"), sent("s1", "11138234", "2026-11-18T09:00:00Z"))
        items, _ = self.due(mail, [row(1)])
        sentmsgs, out = [], []

        class TG:
            def send(self, text, topic=None):
                sentmsgs.append((text, topic))
        pegasys.run(items, self.client(site), self.st, tg=TG(), out=out.append)
        pegasys.run(items, self.client(site), self.st, tg=TG(), out=out.append)
        self.assertIn("NOT CONFIRMED", out[0])
        self.assertEqual(len(sentmsgs), 1)  # one Telegram line per notice, not one per run
        self.assertEqual(sentmsgs[0][1], "report")
        self.assertEqual(len(self.due(mail, [row(1)])[0]), 1)  # still due next run

    def test_session_expired_logs_in_again(self):
        site = FakeSite("New")
        c = self.client(site)
        c.booking("11138234", GUID)
        site.logged_in = False  # the cookie ran out
        self.assertEqual(c.booking("11138234", GUID)["status"], "New")
        self.assertEqual(sum(1 for m, p, *_ in site.calls if (m, p) == ("POST", "/Login")), 2)

    def test_wrong_password_fails(self):
        with self.assertRaises(pegasys.PegasysError):
            pegasys.Pegasys("haya", "wrong", opener=FakeSite()).booking("11138234", GUID)


# The real page's structure (11120333, read 20/11), with made-up guests.
DETAIL_PAGE = """<html><body>
<input name="__RequestVerificationToken" type="hidden" value="tok" />
<article data-booking-id="11120333" data-service-guid="g" data-version="639;108" class="row">
<section class="row"><div class="booking-block col-xs-12">
<div class="k-block">
    <div class="k-header">
        Booking
    </div>
    <div class="container-fluid"><div class="row">
      <div class="form-group row"><label class="col-xs-5">
                        Booking #
                    </label>
                    <div class="col-xs-7">
                        <span>11120333</span>
                    </div></div>
      <div class="form-group row"><label class="col-xs-5">Check-in</label><div class="col-xs-7">15.11.2026</div></div>
      <div class="form-group row"><label class="col-xs-5">Check-out</label><div class="col-xs-7">27.11.2026</div></div>
      <div class="form-group row"><label class="col-xs-5">Nights</label><div class="col-xs-7">12</div></div>
      <div class="form-group row"><label class="col-xs-5">Package</label><div class="col-xs-7">Vietnam Phu Quoc (Ekaterinburg)</div></div>
      <div class="form-group row"><label class="col-xs-5">Market</label><div class="col-xs-7">Russia</div></div>
      <div class="form-group row"><label class="col-xs-5">Room</label><div class="col-xs-7">
                        Superior Double or Twin Room
                    </div></div>
      <div class="form-group row"><label class="col-xs-5">Meal</label><div class="col-xs-7">Bed &amp; Breakfast</div></div>
      <div class="form-group row"><label class="col-xs-5">Accommodation</label><div class="col-xs-7">DBL+CHD</div></div>
      <div class="form-group row"><label class="col-xs-5">Booking date</label><div class="col-xs-7">03.11.2026 16:34</div></div>
      <div class="form-group row"><label class="col-xs-5">Room</label><div class="col-xs-7">Superior Double or Twin Room</div></div>
    </div></div>
</div>
<div class="k-block"><div class="k-header">
        Confirmation
    </div>
<input class="k-textbox" id="Status" name="Status" value="New" />
<input class="k-textbox" id="ConfirmationNumber" value="" />
</div>
<div class="special-requests-block col-xs-12 col-md-6">
<div class="k-block">
    <div class="k-header">Special Requests</div>
    <div class="container-fluid">
        <ul class="ul-with-padding">
                <li>Upper Floor if possible</li>
                <li>Sea View if possible</li>
        </ul>
    </div>
</div></div>
<div class="k-block">
    <div class="k-header">
        Guests
    </div>
    <table class="table"><thead><tr><th>Title</th><th>Last Name</th><th>First Name</th><th>Date of birth</th>
      <th>Age</th><th>Document</th><th>Additional information</th><th>Arrival flight</th><th>Departure flight</th></tr></thead>
      <tr><td>MR</td><td>IVANOV</td><td>PETR</td><td>25.04.1996</td><td>30</td>
          <td><div>Russia</div><div>700000001</div></td><td>
          </td><td><div>09:30</div><div><div class='font-size-tertiary'>N4-3831 (SVX-PQC)</div></div></td>
          <td><div>12:15</div><div><div class='font-size-tertiary'>N4-3832 (PQC-SVX)</div></div></td></tr>
      <tr><td>CHD</td><td>IVANOVA</td><td>ANNA</td><td>20.11.2014</td><td>12</td>
          <td><div>Russia</div><div>700000002</div></td><td></td><td></td><td></td></tr>
    </table>
</div>
<div class="k-block">
    <div class="k-header">
        Messages
    </div>
<div component-id="m" class="container-fluid">
    <button class="k-button new-message-button">New message</button>
    <p><em>No messages.</em></p>
    <div id="new-message-window"><button>Send</button></div>
</div></div>
</section></article></body></html>"""


class DetailClient:
    def __init__(self):
        self.calls = []

    def details(self, bid, guid):
        self.calls.append((bid, guid))
        return pegasys.parse_details(DETAIL_PAGE)


class DetailsTests(unittest.TestCase):
    """Dev, 2026-11-20: "làm luôn phần đọc chi tiết booking để ghi intake". Pegas's robot mail is only a link."""

    def test_page_fields(self):
        d = pegasys.parse_details(DETAIL_PAGE)
        self.assertEqual(d["status"], "New")
        f = d["fields"]
        self.assertEqual((f["Booking #"], f["Check-in"], f["Check-out"], f["Nights"], f["Meal"], f["Accommodation"]),
                         ("11120333", "15.11.2026", "27.11.2026", "12", "Bed & Breakfast", "DBL+CHD"))
        self.assertEqual(f["Room"], "Superior Double or Twin Room")
        self.assertEqual(d["requests"], ["Upper Floor if possible", "Sea View if possible"])
        self.assertEqual(d["messages"], [])
        man, child = d["guests"]
        self.assertEqual((man["title"], man["last"], man["first"], man["document"]),
                         ("MR", "IVANOV", "PETR", ["Russia", "700000001"]))
        self.assertEqual((man["arrival"], man["departure"]), ("09:30 N4-3831 (SVX-PQC)", "12:15 N4-3832 (PQC-SVX)"))
        # 12 on the site today, 11 at check-in: the age that decides adult or child is the one at check-in
        self.assertEqual((child["age"], child["age_at_checkin"]), ("12", 11))

    def test_render(self):
        text = "\n".join(pegasys.render_details("11120333", pegasys.parse_details(DETAIL_PAGE)))
        self.assertIn("status on the site: New", text)
        self.assertIn("CHD IVANOVA ANNA, born 20.11.2014 (age 11 at check-in), document Russia 700000002", text)
        self.assertIn("NOT ON THE PAGE: the price", text)
        cancelled = DETAIL_PAGE.replace('value="New"', 'value="Cancellation request"')
        self.assertIn("CANCELLED BY PEGAS", pegasys.render_details("1", pegasys.parse_details(cancelled))[0])

    def test_show_prints_the_page_under_a_robot_mail(self):
        from tools import emi
        out, client, opened = [], DetailClient(), set()
        body = f"Please confirm the reservation: https://provider.pegasys.pegast.com/HotelBookings/11120333/{GUID}\n"
        emi._show_pegasys(body, out.append, opened, client=client)
        emi._show_pegasys(body, out.append, opened, client=client)  # quoted again lower in the thread
        self.assertEqual(client.calls, [("11120333", GUID)])
        self.assertIn("\n[Pegasys page, read now]", out)
        self.assertTrue(any("IVANOV PETR" in line for line in out))

    def test_show_says_when_the_page_is_not_read(self):
        from tools import emi
        out = []
        old = {k: os.environ.pop(k, None) for k in ("EMI_PEGAS_USER", "EMI_PEGAS_PASSWORD")}
        try:
            emi._show_pegasys(f"https://provider.pegasys.pegast.com/HotelBookings/11120333/{GUID}", out.append, set())
        finally:
            os.environ.update({k: v for k, v in old.items() if v})
        self.assertIn("Pegasys page not read", out[-1])

    def test_pegas_booking_finds_the_link_in_the_mailbox(self):
        from tools import emi
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(path)
        st, client, out = State(path), DetailClient(), []
        mail = FakeMail(notice("n1", "11120333", "2026-11-03T09:48:42Z"))
        emi.run_pegas_booking(mail, st, "#11120333", client=client, out=out.append)
        self.assertEqual(client.calls, [("11120333", GUID)])
        self.assertEqual(out[-1], "END pegas-booking")
        with self.assertRaises(emi.Refused):
            emi.run_pegas_booking(FakeMail(), st, "999", client=client, out=out.append)


if __name__ == "__main__":
    unittest.main()


class NoInternalStepInDraftTest(unittest.TestCase):
    """Dev 26/11, Pegas 11152394 (#1841): 'Confirmation on the Pegas extranet is awaiting the required manager
    approval' went to Pegas. HAYA's own approvals, the build tool and E-nnn never go in an email."""

    def check(self, text):
        from tools import emi
        emi.check_no_gaps(text)

    def test_internal_steps_refused(self):
        from tools import emi
        for bad in ("Confirmation on the Pegas extranet is awaiting the required manager approval.",
                    "The change is pending approval from our management.",
                    "Our build tool has not finished yet.",
                    "See E-696.",
                    "Booking đang chờ quản lý duyệt."):
            with self.assertRaises(emi.Refused, msg=bad) as e:
                self.check(f"Dear Ms. Dao,\n\n{bad}\n\nBest regards,\nReservations Team")
            self.assertIn("INTERNAL STEP", str(e.exception))

    def test_check_line_and_plain_reply_pass(self):
        self.check("[CHECK BEFORE SENDING: E-696 is open; manager approval in EZFOLIO.]\n\nDear Ms. Dao,\n\n"
                   "The revised booking #11152394 is confirmed under group code #31444 and confirmed on the Pegas "
                   "extranet.\n\nBest regards,\nReservations Team")
