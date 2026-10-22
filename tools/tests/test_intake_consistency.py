"""Rows that each passed the checks but disagreed with each other (live rows 56–79, 2026-10-22):
booking_ref and company spelled differently for the same channel, nationality as a code, notes not in
the 1–7 format, a one-cell row typed by hand. tools/intake_schema.py check_row."""
import unittest

from tools import intake_schema as schema

NOTES = ("1. Booking.com – Ref 92777EF002985\n2. AbdolAziz Yary – Uzbekistan\n3. 22/10/2026 – 24/10/2026\n"
         "4. 1 Standard Garden – 1 adult, 0 children\n5. Non-smoking room\n"
         "6. 1,408,000 × 1 room × 2 nights = 2,816,000\n7. Invoice: none stated")
ROW = {"action": "NEW", "received_at": "22/10/2026 13:40", "property": "HAYA", "channel_type": "OTA",
       "source_email": "SynXis Res Confirmed (92777EF002985 )", "company": "Booking.com",
       "booking_ref": "92777EF002985", "guest_names": "AbdolAziz Yary", "nationality": "Uzbekistan",
       "arrival": "22/10/2026", "departure": "24/10/2026", "nights": "2", "room_code": "STD", "rooms": "1",
       "adults": "1", "children": "0", "rate_source": "OTA net", "rate_per_night_vnd": "1408000",
       "Average rate per night after discount": "1408000", "total_vnd": "2816000", "status": "Definite",
       "notes": NOTES, "missing_info": "meal plan not stated", "priority": "Urgent", "tracy_status": "Pending"}


def check(**changes):
    return schema.check_row(dict(ROW, **changes))


def has(items, start):
    return any(x.startswith(start) for x in items)


class CleanRowTest(unittest.TestCase):
    def test_reference_row_passes_without_warnings(self):
        self.assertEqual(check(), ([], []))


class BookingRefTest(unittest.TestCase):
    def test_channel_words_or_brackets_refused(self):
        # rows 59 / 40 / 48 / 19
        for ref in ("SynXis 92777EF002984 (Booking.com)", "SynXis 92777EF002721 (Expedia)",
                    "Agoda 1783017402 / SynXis 92777EF002717", "Mytour H6844730 / MT1406527499",
                    "0511-026 (PKG-19206)"):
            errors, _ = check(booking_ref=ref, notes="")
            self.assertTrue(has(errors, "booking_ref:"), ref)

    def test_plain_numbers_pass(self):
        for ref in ("92777EF002985", "1783017402 / 92777EF002717", "AGIN0116572610466700", "GADT 0410STE251026"):
            errors, _ = check(booking_ref=ref, notes="")
            self.assertFalse(has(errors, "booking_ref:"), ref)

    def test_built_row_only_warned(self):
        # the confirmation record is keyed by booking_ref + row: don't force a rename after the build
        errors, warnings = check(booking_ref="SynXis 92777EF002984 (Booking.com)", notes="",
                                 tracy_status="Entered", pdf_link="x", ezfolio_group_code="G1")
        self.assertFalse(has(errors, "booking_ref:"))
        self.assertTrue(has(warnings, "booking_ref:"))

    def test_ref_parts(self):
        self.assertEqual(schema.ref_parts("1783017402 / 92777EF002717"), ["1783017402", "92777EF002717"])
        self.assertEqual(schema.ref_parts("SI781659A"), ["SI781659A"])


class CompanyTest(unittest.TestCase):
    def test_known_variants_map_to_one_name(self):
        for raw, canon in (("BOOKING.COM BV", "Booking.com"), ("ANEX KHABAROVSK", "Anex"), ("Anex Tour", "Anex"),
                           ("Agoda Company Pte Ltd", "Agoda"), ("FUN & SUN", "Fun and Sun"), ("MG Bedbank", "MG"),
                           ("Pegas Touristik", "Pegas"), ("crystal bay", "Crystal Bay")):
            self.assertEqual(schema.canonical_company(raw), canon, raw)
        for raw in ("Viet Ban Mai Travel", "Phú Minh Quang Travel", "Coral Travel", "Bookings Travel Co"):
            self.assertIsNone(schema.canonical_company(raw), raw)

    def test_variant_is_a_warning_with_the_office_for_notes(self):
        errors, warnings = check(company="ANEX KHABAROVSK", channel_type="Tour operator", rate_source="Anex contract",
                                 notes="")
        self.assertFalse(has(errors, "company:"))
        w = next(x for x in warnings if x.startswith("company:"))
        self.assertIn("write 'Anex'", w)
        self.assertIn("'1. Anex (Khabarovsk) – Ref 92777EF002985'", w)
        self.assertTrue(has(check(company="BOOKING.COM BV", notes="")[1], "company: 'BOOKING.COM BV' is 'Booking.com'"))
        self.assertFalse(has(check(company="Viet Ban Mai Travel", channel_type="TA", notes="")[1], "company:"))

    def test_synxis_as_company_warned(self):
        self.assertTrue(has(check(company="SynXis", notes="")[1], "company: SynXis is the channel manager"))


class NationalityTest(unittest.TestCase):
    def test_codes_refused_with_the_name(self):
        errors, _ = check(nationality="VNM")
        self.assertIn("nationality: 'VNM' is a code; write the full English country name ('Vietnam')", errors)
        self.assertTrue(has(check(nationality="India; RU")[0], "nationality: 'RU'"))
        self.assertTrue(has(check(nationality="XQ")[0], "nationality: 'XQ' is a code"))

    def test_full_names_pass(self):
        for n in ("Vietnam", "United Kingdom", "India; Vietnam", "Iran", "Laos"):
            self.assertFalse(has(check(nationality=n)[0], "nationality"), n)

    def test_blank_only_when_named_in_missing_info(self):
        # MG voucher showing only the source market: blank, said in missing_info
        self.assertTrue(has(check(nationality="")[0], "nationality: never blank"))
        errors, _ = check(nationality="", missing_info="nationality – only source market Malaysia given")
        self.assertFalse(has(errors, "nationality"))


class NotesTest(unittest.TestCase):
    def test_numbering_must_be_1_to_7(self):
        six = "\n".join(NOTES.splitlines()[:6])
        self.assertTrue(has(check(notes=six)[1], "notes: NOTES RULE wants exactly 7 lines"))
        extra = NOTES + "\nCancellation charge: to check"
        self.assertTrue(has(check(notes=extra)[1], "notes: NOTES RULE"))
        self.assertTrue(has(check(notes="Guest wants high floor")[1], "notes: NOTES RULE"))

    def test_item_1_is_company_and_ref(self):
        # row 61 / 65: "1. Anex + 112930961", "1. BOOKING.COM BV + 92777EF002985"
        bad = NOTES.replace("1. Booking.com – Ref 92777EF002985", "1. BOOKING.COM BV + 92777EF002985")
        w = next(x for x in check(notes=bad)[1] if x.startswith("notes:"))
        self.assertIn("start with the company 'Booking.com'", w)
        self.assertIn("contain 'Ref 92777EF002985'", w)

    def test_cancel_notes_are_the_charge_line(self):
        cancel = dict(action="CANCEL", what_changed="Cancelled by agency", status="Cancelled",
                      missing_info="ezfolio_group_code: not known")
        self.assertTrue(has(check(notes=NOTES, **cancel)[1], "notes: a CANCEL row's notes"))
        line = "Cancellation charge (Anex contract): 0 VND — 67 days before check-in, free (>21 days). Paid: 0 VND."
        self.assertFalse(has(check(notes=line, **cancel)[1], "notes:"))


class PartialRowTest(unittest.TestCase):
    def test_one_or_two_cells_refused_as_a_stray_write(self):
        # row 79: {"source_email": "s"}
        errors, warnings = schema.check_row({"source_email": "s", "_row": 79})
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("row: only 1 cell(s) filled (source_email)"))
        self.assertTrue(schema.check_row({"action": "NEW", "booking_ref": "X", "tracy_status": "Pending"})[0][0]
                        .startswith("row: only 2 cell(s)"))


class OldRowRulesTest(unittest.TestCase):
    def test_enum_errors_say_where_the_detail_goes(self):
        errors, _ = check(channel_type="Tour operator (Anex)")
        self.assertTrue(any("not allowed" in e and "goes in company" in e for e in errors))
        errors, _ = check(rate_source="OTA net (Expedia remittance)")
        self.assertTrue(any("not allowed" in e and "notes item 6" in e for e in errors))

    def test_each_tour_operator_contract_is_a_rate_source(self):
        for op in ("Anex", "Odeon", "Pegas", "Crystal Bay", "Selfie"):
            self.assertFalse(has(check(rate_source=f"{op} contract")[0], "rate_source"), op)
        self.assertTrue(has(check(rate_source="Fun and Sun contract")[0], "rate_source"))

    def test_hold_until_takes_a_time(self):
        self.assertFalse(has(check(hold_until="07/10/2026 17:00")[0], "hold_until"))
        self.assertFalse(has(check(hold_until="07/10/2026")[0], "hold_until"))
        self.assertTrue(has(check(hold_until="7 Oct 17:00")[0], "hold_until"))
        self.assertTrue(has(check(arrival="22/10/2026 14:00")[0], "arrival"))

    def test_built_new_row_can_still_be_updated(self):
        # a payment slip recorded with sheet-update after the build tool set Entered + pdf_link + group code
        built = dict(tracy_status="Entered", pdf_link="Booking.pdf", ezfolio_group_code="G123")
        self.assertEqual(check(**built)[0], [])
        self.assertTrue(has(check(pdf_link="Booking.pdf")[0], "pdf_link: filled by the build tool"))


if __name__ == "__main__":
    unittest.main()
