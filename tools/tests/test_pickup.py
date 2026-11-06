import unittest

from tools import emi
from tools import pickup


def row(n, ref, total, action="NEW", received="01/11/2026 19:48", name="Erkinbek Uzakbaev", room="DLX-SV",
        rooms="1", company="Booking.com", channel="OTA", source="Booking.com guest total", **kw):
    return dict(_row=n, _sheet="live", action=action, received_at=received, booking_ref=ref, guest_names=name,
                arrival="06/11/2026", departure="09/11/2026", company=company, channel_type=channel,
                room_code=room, rooms=rooms, rate_source=source, total_vnd=str(total),
                rate_per_night_vnd=str(total // 3), **kw)


def check(rows, ref, **kw):
    return pickup.check(rows, ref, emi._parts, **kw)


# Erkinbek Uzakbaev, 06/11: one Booking.com booking, two SynXis numbers; the guest's messages only reach 003194.
ERKINBEK = [row(1023, "SynXis 92777EF003194 (Booking.com)", 5760000),
            row(1024, "SynXis 92777EF003193 (Booking.com)", 5760000, room="TW-DLX"),
            row(1591, "Booking.com 6907944253 / SynXis 92777EF003194", 5760000, action="CHANGE",
                received="06/11/2026 09:16")]


class PickupTest(unittest.TestCase):
    def test_both_synxis_numbers_count(self):
        # 06/11: Emi charged 250,000 on one room's 5,760,000; the booking is 11,520,000
        r = check(ERKINBEK, "6907944253")
        self.assertEqual((r["outcome"], r["total"], r["rooms"]), (pickup.FREE, 11520000, 2))

    def test_cancelled_room_drops_out(self):
        rows = ERKINBEK + [row(1700, "SynXis 92777EF003193 (Booking.com)", 5760000, room="TW-DLX",
                               action="CANCEL", received="06/11/2026 10:33")]
        r = check(rows, "6907944253", ota_rooms=1)
        self.assertEqual((r["outcome"], r["rooms"]), (pickup.PAID, 1))

    def test_other_guest_same_dates_not_added(self):
        rows = ERKINBEK[:1] + [row(1030, "SynXis 92777EF003199 (Booking.com)", 9000000, name="Anna Ivanova")]
        self.assertEqual(check(rows, "92777EF003194", ota_rooms=1)["outcome"], pickup.PAID)

    def test_two_emails_same_minute_counted_once(self):
        # Adrian Sequeira, live rows 1599 + 1600: two messages at 10:29, two identical CHANGE rows
        rows = [row(1048, "Booking.com 5337759531 / SynXis 92777EF003205", 5540400, name="Adrian Sequeira")] + [
            row(n, "Booking.com 5337759531 / SynXis 92777EF003205", 5540400, name="Adrian Sequeira",
                action="CHANGE", received="06/11/2026 10:29") for n in (1599, 1600)]
        r = check(rows, "5337759531", ota_rooms=1)
        self.assertEqual((r["outcome"], r["rooms"], r["total"]), (pickup.PAID, 1, 5540400))
        # Booking.com's message says 2 rooms: a room is missing from the sheet, never "paid"
        r = check(rows, "5337759531", ota_rooms=2)
        self.assertEqual(r["outcome"], pickup.CHECK)
        self.assertIn("missing from the sheet", " ".join(r["notes"]))
        # no room count given: an OTA booking is not called paid
        self.assertEqual(check(rows, "5337759531")["outcome"], pickup.CHECK)

    def test_net_and_guest_figures(self):
        agoda = [row(1579, "Agoda 1794048417 / SynXis 92777EF003253", 6426864, name="YUK YAN IP",
                     company="Agoda", source="Agoda net")]
        self.assertEqual(check(agoda, "1794048417")["outcome"], pickup.CHECK)       # net below the mark
        self.assertEqual(check(agoda, "1794048417", paid_vnd=7387200)["outcome"], pickup.FREE)
        self.assertEqual(check(agoda, "1794048417", paid_usd=250)["outcome"], pickup.PAID)
        self.assertEqual(check(agoda, "1794048417", paid_usd=275)["outcome"], pickup.FREE)
        self.assertEqual(check(agoda, "1794048417", paid_vnd=6300000)["outcome"], pickup.CHECK)  # between marks
        big_net = [dict(agoda[0], total_vnd="6900000")]
        self.assertEqual(check(big_net, "1794048417")["outcome"], pickup.FREE)       # guest paid at least the net

    def test_provisional_ta_card_is_not_what_the_guest_paid(self):
        rows = [row(1587, "Booking.com 1820191432482205445", 19000000, name="Jane-Marie Gardner", source="Other",
                    missing_info="Booking.com voucher not received: rate is the TA card, provisional")]
        self.assertEqual(check(rows, "1820191432482205445")["outcome"], pickup.CHECK)

    def test_ta_booking_is_never_free(self):
        rows = [row(900, "Thu1230 TVR149", 20000000, company="Vietravel", channel="TA", source="TA table")]
        self.assertEqual(check(rows, "Thu1230 TVR149")["outcome"], pickup.TA)

    def test_command(self):
        class Sheet:
            def rows(self):
                return [dict(r) for r in ERKINBEK]
        out = []
        args = emi.parser().parse_args(["pickup", "6907944253"])
        emi.run_pickup(Sheet(), args, out=out.append)
        self.assertIn("PICK-UP: FREE", out[0])
        self.assertIn("92777EF003193", out[0])
        with self.assertRaises(emi.Refused):
            emi.run_pickup(Sheet(), emi.parser().parse_args(["pickup", "999999"]), out=out.append)


if __name__ == "__main__":
    unittest.main()
