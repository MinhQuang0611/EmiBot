"""dev, 2026-11-21: a booking email is put against what Sunny already told the agency on Zalo
(/data/shared/haya-notes.jsonl: sold out, quotes), and the reviewer sees it on the draft's Telegram notice."""
import json
import os
import tempfile
import unittest
from datetime import date
from types import SimpleNamespace
from unittest import mock

from tools import emi, review, zalo_notes

NOTES = [
    {"id": "N1", "at": "2026-11-05 20:38", "by": "sunny", "type": "sold_out", "agency": "TEST PAM & SUNNY",
     "guest": "THIEU DUNG", "stay": "2026-11-17/2026-11-21", "said": "Đã báo HAYA hết phòng 17/11/2026–21/11/2026",
     "expect": "Mail đặt HAYA cho 17/11/2026–21/11/2026 → cảnh báo người duyệt: Zalo đã báo hết"},
    {"id": "N2", "at": "2026-11-05 21:35", "by": "sunny", "type": "sold_out", "agency": "VICTORIA TOUR",
     "stay": "2026-11-08/2026-11-16", "said": "Đã báo HAYA hết phòng 08/11/2026–16/11/2026",
     "expect": "Mail đặt HAYA cho 08/11–16/11/2026 → cảnh báo người duyệt: Zalo đã báo hết"},
    {"id": "N3", "at": "2026-11-05 21:50", "by": "sunny", "type": "quote", "agency": "TEST PAM & SUNNY",
     "stay": "2027-02-17/2027-02-19", "rooms": "1 Twin", "said": "17/02/2027–19/02/2027: 01 Twin 1.900.000 VND/phòng/đêm",
     "expect": "Mail đặt nên khớp 01 Twin 1.900.000 VND/đêm"},
]


def write_notes(notes, extra=""):
    f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
    f.write("\n".join(json.dumps(n, ensure_ascii=False) for n in notes) + "\n" + extra)
    f.close()
    return f.name


class LoadTest(unittest.TestCase):
    def test_a_half_written_last_line_is_skipped(self):
        path = write_notes(NOTES, extra='{"id": "N4", "at": "2026-11')
        notes, gap = zalo_notes.load(path)
        self.assertEqual(gap, "")
        self.assertEqual([n["id"] for n in notes], ["N1", "N2", "N3"])

    def test_no_file_is_a_gap(self):
        notes, gap = zalo_notes.load(os.path.join(tempfile.gettempdir(), "no-such-notes.jsonl"))
        self.assertEqual(notes, [])
        self.assertIn("not checked", gap)


class MatchTest(unittest.TestCase):
    def test_agency_and_overlapping_stay(self):
        hits = zalo_notes.match(NOTES, "Victoria Tour & Travel JSC", [], date(2026, 11, 10), date(2026, 11, 12))
        self.assertEqual([n["id"] for n in hits], ["N2"])

    def test_other_dates_are_not_this_booking(self):
        self.assertEqual(zalo_notes.match(NOTES, "Victoria Tour", [], date(2026, 11, 16), date(2026, 11, 18)), [])

    def test_generic_words_alone_match_nothing(self):
        self.assertEqual(zalo_notes.match(NOTES, "Saigon Tour", [], date(2026, 11, 10), date(2026, 11, 12)), [])

    def test_guest_with_accents_and_middle_name(self):
        hits = zalo_notes.match(NOTES, "Other agency", ["Thiều Văn Dũng"], date(2026, 11, 18), date(2026, 11, 20))
        self.assertEqual([n["id"] for n in hits], ["N1"])

    def test_surname_alone_is_not_the_guest(self):
        self.assertEqual(zalo_notes.match(NOTES, "", ["Dung"], date(2026, 11, 18), date(2026, 11, 20)), [])

    def test_no_dates_needs_the_guest(self):
        self.assertEqual(zalo_notes.match(NOTES, "Victoria Tour", []), [])
        self.assertEqual([n["id"] for n in zalo_notes.match(NOTES, "", "THIEU VAN DUNG")], ["N1"])


class RowsTest(unittest.TestCase):
    ROW = {"action": "NEW", "company": "TEST PAM & SUNNY", "guest_names": "Nguyen An", "arrival": "17/02/2027",
           "departure": "19/02/2027", "rate_per_night_vnd": "1,900,000"}

    def test_quote_at_zalo_price(self):
        lines = zalo_notes.for_rows(NOTES, [self.ROW])
        self.assertEqual(len(lines), 1)
        self.assertIn("Zalo N3", lines[0])
        self.assertNotIn("GIÁ KHÁC", lines[0])

    def test_quote_at_another_price_is_named(self):
        lines = zalo_notes.for_rows(NOTES, [dict(self.ROW, rate_per_night_vnd="2,100,000")])
        self.assertIn("GIÁ KHÁC: sheet 2,100,000 / Zalo 1,900,000", lines[0])

    def test_sold_out_booking(self):
        row = dict(self.ROW, company="Victoria Tour", arrival="09/11/2026", departure="11/11/2026")
        lines = zalo_notes.for_rows(NOTES, [row])
        self.assertIn("đã báo hết phòng", lines[0])
        self.assertIn("cảnh báo người duyệt", lines[0])


class FakeTg:
    def __init__(self):
        self.sent = []

    def send(self, text, buttons=None, topic=None):
        self.sent.append(text)
        return 1


class NoticeTest(unittest.TestCase):
    def test_the_reviewer_sees_the_zalo_note(self):
        tg = FakeTg()
        r = {"text": "Dear team", "to": ["a@b.c"], "subject": "RE: booking", "kind": "confirmation", "how": "reply",
             "version": 1, "ref": "X", "source": "", "draft_id": "pending-7",
             "zalo": ["Zalo N2 (2026-11-05 21:35, sunny) đã báo hết phòng — VICTORIA TOUR"]}
        review.notify(tg, 7, r)
        self.assertIn("⚠️ <b>Zalo:</b> Zalo N2", tg.sent[0])


class CommandTest(unittest.TestCase):
    def test_zalo_lines_and_the_command(self):
        path = write_notes(NOTES)
        out = []
        with mock.patch.object(emi.config, "ZALO_NOTES", path):
            lines = emi.zalo_lines([{"action": "NEW", "company": "VICTORIA TOUR", "arrival": "09/11/2026",
                                     "departure": "11/11/2026"}], out=out.append)
            self.assertEqual(len(lines), 1)
            self.assertTrue(out[0].startswith("ZALO: Zalo N2"))
            out = []
            args = SimpleNamespace(agency="", guest="", arrival="", departure="", text="victoria")
            hits = emi.run_zalo_notes(args, out=out.append)
        self.assertEqual([n["id"] for n in hits], ["N2"])
        self.assertIn("3 Zalo note(s)", out[0])

    def test_no_shared_folder_says_nothing(self):
        out = []
        with mock.patch.object(emi.config, "ZALO_NOTES", "/no/such/dir/haya-notes.jsonl"):
            self.assertEqual(emi.zalo_lines([{"company": "X"}], out=out.append), [])
        self.assertEqual(out, [])


if __name__ == "__main__":
    unittest.main()
