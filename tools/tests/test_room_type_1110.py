"""dev 10/11, Ohmyhotel V26082610068H01: a pick-up request went on CHANGE row 1784 as DLX-SV, the booking being
TW-DLX (live row 1459, Ohmyhotel's 'Deluxe Twin Sea View'). The backfill had written Ohmyhotel as 'TA', the CHANGE
copied it, and the 'never TW-DLX to agencies' check refused the booking's own room type."""
import unittest

from tools import emi
from tools import intake_schema as schema

BACKFILL = {"action": "EXISTING BOOKING", "booking_ref": "V26082610068H01", "channel_type": "TA",
            "company": "CÔNG TY TNHH OHMYHOTEL&CO VN", "room_code": "TW-DLX", "rooms": "2", "_row": 1459,
            "_sheet": "live", "received_at": "05/11/2026 19:46"}
PICKUP = {"action": "CHANGE", "booking_ref": "V26082610068H01", "channel_type": "OTA",
          "company": "CÔNG TY TNHH OHMYHOTEL&CO VN", "room_code": "DLX-SV", "rooms": "2",
          "what_changed": "Airport pick-up details added: flight 9G750, arrival 17:35 on 01/12/2026"}


class KeepRoomTypesTest(unittest.TestCase):
    def test_a_change_without_a_room_change_keeps_the_room_code(self):
        with self.assertRaisesRegex(emi.Refused, "keeps the booking's room_code"):
            emi.keep_room_types([PICKUP], [BACKFILL])
        emi.keep_room_types([dict(PICKUP, room_code="TW-DLX")], [BACKFILL])

    def test_a_room_type_change_names_both_codes(self):
        emi.keep_room_types([dict(PICKUP, what_changed="Room type TW-DLX → DLX-SV, guest asked")], [BACKFILL])

    def test_nothing_to_compare(self):
        emi.keep_room_types([PICKUP], [dict(BACKFILL, room_code="")])
        emi.keep_room_types([PICKUP], [])
        emi.keep_room_types([dict(PICKUP, action="CANCEL")], [BACKFILL])


class OnlineSitesTest(unittest.TestCase):
    def errors(self, **cells):
        rec = dict(action="CHANGE", channel_type="OTA", company="CÔNG TY TNHH OHMYHOTEL&CO VN", room_code="TW-DLX")
        rec.update(cells)
        return schema.check_row(rec, {"TW-DLX": ("", ""), "DLX-SV": ("", "")})[0]

    def test_an_online_site_sells_tw_dlx(self):
        self.assertFalse([e for e in self.errors(channel_type="TA") if "never sold to agencies" in e])
        self.assertTrue([e for e in self.errors(channel_type="TA", company="TIQI") if "never sold to agencies" in e])

    def test_an_ota_is_not_ta(self):
        self.assertTrue([e for e in self.errors(channel_type="TA") if e.startswith("channel_type:")])
        self.assertFalse([e for e in self.errors() if e.startswith("channel_type:")])
        self.assertFalse([e for e in self.errors(channel_type="TA", company="WebBeds FZ LLC")
                          if e.startswith("channel_type:")])
        # the backfill rows already on the sheet aren't flagged
        self.assertFalse([e for e in self.errors(action="EXISTING BOOKING", channel_type="TA")
                          if e.startswith("channel_type:")])


if __name__ == "__main__":
    unittest.main()
