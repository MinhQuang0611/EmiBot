"""Dev 21/11, SynXis 92777EE002243 (Agoda), live row 1082: "not picked up by EZFOLIO for 444 hours".

Agoda 698918623 is two rooms; SynXis gives one number per room (2243, 2244). Agoda's cancellation went in as row 1081
(Agoda 698918623 / SynXis 92777EE002244), the build tool cancelled group 28281 from it. SynXis's notice for 2243 went
in as a second CANCEL row 1082; the build tool ran on it (ez_processed_at 03/11 10:10) and wrote no status, and
build-stuck called it "not picked up" every day until the stay.
"""
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from tools import build_watch, emi
from tools.state import State

VN = timezone(timedelta(hours=7))
NOW = datetime(2026, 11, 21, 11, 45, tzinfo=VN)

BASE = {"action": "CANCEL", "channel_type": "OTA", "company": "Agoda", "guest_names": "SERGII POPAS",
        "arrival": "10/12/2026", "departure": "13/12/2026", "room_code": "STD", "status": "Cancelled"}
ROW_1081 = {**BASE, "_row": 1081, "_sheet": "live", "received_at": "02/11/2026 23:44", "rooms": "2",
            "booking_ref": "Agoda 698918623 / SynXis 92777EE002244", "ez_status": "done",
            "ez_note": "đã huỷ group 28281 (agent sửa booking, duyệt bởi longdev123)",
            "ez_processed_at": "2026-11-03T10:11:57+07:00"}
ROW_1082 = {**BASE, "_row": 1082, "_sheet": "live", "received_at": "02/11/2026 23:45", "rooms": "1",
            "booking_ref": "SynXis 92777EE002243 (Agoda)", "ez_processed_at": "2026-11-03T10:10:48"}


class BuildWatchTest(unittest.TestCase):
    def stuck(self, rows):
        return build_watch.stuck(rows, emi.booking_state, NOW)

    def test_the_second_rooms_cancel_is_covered_by_the_done_one(self):
        self.assertEqual(self.stuck([ROW_1081, ROW_1082]), [])

    def test_not_covered_when_the_sister_row_is_not_done_or_another_stay(self):
        open_sister = {**ROW_1081, "ez_status": "", "ez_note": "", "ez_processed_at": ""}
        other_stay = {**ROW_1081, "arrival": "11/12/2026"}
        other_guest = {**ROW_1081, "guest_names": "IVAN PETROV"}
        for sister in (open_sister, other_stay, other_guest):
            refs = {i["ref"] for i in self.stuck([sister, ROW_1082])}
            self.assertIn("SynXis 92777EE002243 (Agoda)", refs, sister)

    def test_run_with_no_result_is_its_own_kind_told_once(self):
        [i] = self.stuck([ROW_1082])
        self.assertEqual(i["kind"], "silent")
        self.assertIn("NO RESULT | OTA | Agoda | ref SynXis 92777EE002243 (Agoda)", build_watch.render([i]))
        self.assertIn("2026-11-03T10:10:48", i["key"])

        class Tg:
            sent = []

            def send(self, text, buttons=None, topic=None):
                self.sent.append(text)

        st, tg = State(tempfile.mktemp(suffix="-state.json")), Tg()
        build_watch.alert(st, tg, None, [i], "sales@haya-hotels.com", out=lambda *_: None)
        self.assertIn("wrote no ez_status", tg.sent[0])
        self.assertNotIn("not picked up", tg.sent[0])
        self.assertEqual(st.open_questions(), {})
        self.assertEqual(build_watch.alert(st, tg, None, self.stuck([ROW_1082]), "sales@haya-hotels.com",
                                           out=lambda *_: None), [])

    def test_never_touched_is_still_waiting(self):
        [i] = self.stuck([{**ROW_1082, "ez_processed_at": ""}])
        self.assertEqual(i["kind"], "waiting")


class IntakeTest(unittest.TestCase):
    NEW_1082 = {k: v for k, v in ROW_1082.items() if not k.startswith(("_", "ez_"))}

    def test_synxis_room_of_a_booking_the_ota_cancelled_whole(self):
        self.assertEqual(emi.ota_whole_cancel(self.NEW_1082, [ROW_1081])["_row"], 1081)

    def test_left_alone(self):
        synxis_only_sister = {**ROW_1081, "booking_ref": "SynXis 92777EE002244 (Agoda)"}  # one room cancelled
        for rec, rows in ((self.NEW_1082, [synxis_only_sister]),
                          (self.NEW_1082, [{**ROW_1081, "action": "NEW"}]),
                          (self.NEW_1082, [{**ROW_1081, "departure": "14/12/2026"}]),
                          ({**self.NEW_1082, "booking_ref": "Agoda 698918623"}, [ROW_1081]),  # the OTA's own notice
                          ({**self.NEW_1082, "action": "CHANGE"}, [ROW_1081])):
            self.assertIsNone(emi.ota_whole_cancel(rec, rows), (rec.get("booking_ref"), rows[0]["booking_ref"]))

    def test_sheet_append_refuses_it(self):
        class Sheet:
            def rows(self):
                return []

            def group_code_columns(self):
                return ["ezfolio_group_code", "Group code"]

        class Live:
            def rows(self):
                return [ROW_1081]

        with self.assertRaises(emi.Refused) as e:
            emi.sheet_append(Sheet(), [dict(self.NEW_1082)], out=lambda *_: None, live=Live())
        self.assertIn("SAME BOOKING", str(e.exception))
        self.assertIn('ota-note <id> --ref "Agoda 698918623 / SynXis 92777EE002244"', str(e.exception))


if __name__ == "__main__":
    unittest.main()
