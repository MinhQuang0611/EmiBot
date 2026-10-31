"""Rows that each passed the checks but disagreed with each other (live rows 56–79, 2026-10-22):
booking_ref and company spelled differently for the same channel, nationality written two ways, notes not in
the 1–8 format, a one-cell row typed by hand. tools/intake_schema.py check_row."""
import unittest

from tools import intake_schema as schema

NOTES = ("1. Booking.com – Ref 92777EF002985\n2. AbdolAziz Yary – UZB\n3. 22/10/2026 – 24/10/2026\n"
         "4. 1 Standard Garden – 1 adult, 0 children\n5. Non-smoking room\n"
         "6. 1,408,000 × 1 room × 2 nights = 2,816,000\n7. Invoice: prepaid on Booking.com\n8. No VAT info")
ROW = {"action": "NEW", "received_at": "22/10/2026 13:40", "property": "HAYA", "channel_type": "OTA",
       "source_email": "SynXis Res Confirmed (92777EF002985 )", "company": "Booking.com",
       "booking_ref": "SynXis 92777EF002985 (Booking.com)", "guest_names": "AbdolAziz Yary", "nationality": "Uzbekistan",
       "arrival": "22/10/2026", "departure": "24/10/2026", "nights": "2", "room_code": "STD", "rooms": "1",
       "adults": "1", "children": "0", "meal_plan": "BB", "rate_source": "Booking.com guest total", "rate_per_night_vnd": "1408000",
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
    def test_ota_ref_names_the_channel_as_the_live_sheet_does(self):
        # dev 30/10: "theo sheet thật" — live rows 794, 800, 812 (replaces 27/10's numbers only)
        for ref in ("SynXis 92777EF002984 (Booking.com)", "SynXis 92777EF002721 (Expedia)",
                    "Agoda 1783017402 / SynXis 92777EF002717", "Mytour H6844730 / MT1406527499",
                    "Booking.com 5486733008 / SynXis 92777EF003114", "MG AGIN3415562610364927 / HB2610161458"):
            errors, _ = check(booking_ref=ref, notes="")
            self.assertFalse(has(errors, "booking_ref:"), ref)
        for ref in ("92777EF002985", "1783017402 / 92777EF002717", "AGIN0116572610466700"):
            errors, _ = check(booking_ref=ref, notes="")
            self.assertTrue(has(errors, "booking_ref:"), ref)

    def test_ta_and_operator_codes_as_printed(self):
        for ref in ("GADT 0410STE251026", "Thu1230 TVR149", "INBOM04540000001", "0511-026 (PKG-19206)"):
            errors, _ = check(booking_ref=ref, notes="", channel_type="TA", company="Phú Minh Quang Travel",
                              rate_source="TA card")
            self.assertFalse(has(errors, "booking_ref:"), ref)

    def test_built_row_only_warned(self):
        # the confirmation record is keyed by booking_ref + row: don't force a rename after the build
        errors, warnings = check(booking_ref="92777EF002984", notes="",
                                 tracy_status="Entered", pdf_link="x", ezfolio_group_code="G1")
        self.assertFalse(has(errors, "booking_ref:"))
        self.assertTrue(has(warnings, "booking_ref:"))

    def test_ref_numbers(self):
        self.assertEqual(schema.ref_numbers("SynXis 92777EF002779 (Booking.com 5550972513)"),
                         ["92777EF002779", "5550972513"])

    def test_ref_parts(self):
        self.assertEqual(schema.ref_parts("1783017402 / 92777EF002717"), ["1783017402", "92777EF002717"])
        self.assertEqual(schema.ref_parts("SI781659A"), ["SI781659A"])


class CompanyTest(unittest.TestCase):
    def test_known_variants_map_to_one_name(self):
        for raw, canon in (("BOOKING.COM BV", "Booking.com"), ("ANEX KHABAROVSK", "Anex"), ("Anex Tour", "Anex"),
                           ("Agoda Company Pte Ltd", "Agoda"), ("FUN & SUN", "Fun and Sun"), ("MG Bedbank", "MG"),
                           ("Pegas Touristik", "Pegas"), ("crystal bay", "Crystal Bay"),
                           ("Coral Travel", "Odeon"), ("Oh My Hotel", "Oh My Hotel"), ("Ohmyhotel", "Oh My Hotel")):
            self.assertEqual(schema.canonical_company(raw), canon, raw)
        for raw in ("Viet Ban Mai Travel", "Phú Minh Quang Travel", "Bookings Travel Co"):
            self.assertIsNone(schema.canonical_company(raw), raw)

    def test_variant_is_a_warning_with_the_office_for_notes(self):
        errors, warnings = check(company="ANEX KHABAROVSK", channel_type="Tour operator", rate_source="Anex contract",
                                 notes="")
        self.assertFalse(has(errors, "company:"))
        w = next(x for x in warnings if x.startswith("company:"))
        self.assertIn("write 'Anex'", w)
        self.assertIn("'1. Anex (Khabarovsk) – Ref SynXis 92777EF002985 (Booking.com)'", w)
        self.assertTrue(has(check(company="BOOKING.COM BV", notes="")[1], "company: 'BOOKING.COM BV' is 'Booking.com'"))
        self.assertFalse(has(check(company="Viet Ban Mai Travel", channel_type="TA", notes="")[1], "company:"))

    def test_synxis_as_company_warned(self):
        self.assertTrue(has(check(company="SynXis", notes="")[1], "company: SynXis is the channel manager"))

    def test_new_company_refused_on_a_known_channel(self):
        # row 63: Booking.com with "new company" in missing_info
        self.assertTrue(has(check(missing_info="new company")[0], "missing_info: no 'new company' — Booking.com"))
        self.assertTrue(has(check(company="Anex", channel_type="Tour operator", rate_source="Anex contract",
                                  notes="", missing_info="new company")[0], "missing_info: no 'new company'"))
        self.assertFalse(has(check(company="Viet Ban Mai Travel", channel_type="TA", notes="",
                                   missing_info="new company")[0], "missing_info"))


class RateFloorTest(unittest.TestCase):
    def test_low_ota_rate_is_accepted(self):
        # Tracy audit 29/10: OTA and B2B bookings are always accepted and logged, no rate-floor flag
        low = {"rate_per_night_vnd": "841500", "Average rate per night after discount": "981750",
               "total_vnd": "1963500"}
        self.assertFalse(has(check(**low)[0], "missing_info"))


class NationalityTest(unittest.TestCase):
    """dev 30/10: nationality as the full country name ("KAZ" → "Kazakhstan"), Vietnam when nothing gives a clue.
    Replaces the 3-letter code of Tracy's audit (29/10)."""
    def test_codes_refused_with_the_name(self):
        errors, _ = check(nationality="KAZ")
        self.assertTrue(any(e.startswith("nationality: 'KAZ'") and "'Kazakhstan'" in e for e in errors))
        self.assertTrue(any("'United Kingdom'" in e for e in check(nationality="UK")[0]))
        self.assertTrue(has(check(nationality="India; RU")[0], "nationality: 'RU'"))
        self.assertTrue(has(check(nationality="vnm")[0], "nationality: 'vnm'"))
        self.assertTrue(has(check(nationality="LAO")[0], "nationality: 'LAO'"))

    def test_names_pass(self):
        for n in ("Vietnam", "United Kingdom", "India; Vietnam", "Iran", "Laos", "South Korea"):
            self.assertFalse(has(check(nationality=n, guest_names="Nguyễn Văn An")[0], "nationality"), n)

    def test_never_blank(self):
        self.assertTrue(has(check(nationality="")[0], "nationality: never blank"))
        errors, _ = check(nationality="", missing_info="nationality – only source market Malaysia given")
        self.assertTrue(has(errors, "nationality: never blank"))

    def test_old_full_name_on_a_change_only_warned(self):
        change = dict(action="CHANGE", what_changed="Payment 1 received", ezfolio_group_code="G1")
        errors, warnings = check(nationality="VNM", **change)
        self.assertFalse(has(errors, "nationality"))
        self.assertTrue(has(warnings, "nationality: 'VNM'"))


class NotesTest(unittest.TestCase):
    def test_numbering_must_be_1_to_8(self):
        seven = "\n".join(NOTES.splitlines()[:7])
        self.assertTrue(has(check(notes=seven)[1], "notes: NOTES RULE wants exactly 8 lines"))
        extra = NOTES + "\nCancellation charge: to check"
        self.assertTrue(has(check(notes=extra)[1], "notes: NOTES RULE"))
        self.assertTrue(has(check(notes="Guest wants high floor")[1], "notes: NOTES RULE"))

    def test_item_8_is_the_vat_invoice(self):
        vat = NOTES.replace("8. No VAT info", "8. VAT invoice: CÔNG TY ABC, MST 0402145541, 12 Lê Lợi, ke@abc.vn")
        self.assertFalse(has(check(notes=vat)[1], "notes:"))
        self.assertTrue(has(check(notes=NOTES.replace("8. No VAT info", "8. Invoice: none"))[1], "notes: item 8"))

    def test_item_1_is_company_and_ref(self):
        # row 61 / 65: "1. Anex + 112930961", "1. BOOKING.COM BV + 92777EF002985"
        bad = NOTES.replace("1. Booking.com – Ref 92777EF002985", "1. BOOKING.COM BV + 92777EF002985")
        w = next(x for x in check(notes=bad)[1] if x.startswith("notes:"))
        self.assertIn("start with the company 'Booking.com'", w)
        self.assertIn("contain 'Ref SynXis 92777EF002985 (Booking.com)'", w)

    def test_cancel_notes_are_the_8_items_with_the_charge_in_6(self):
        # dev 30/10: the live sheet's CANCEL rows have the 8 items; Emi's had only the charge line
        cancel = dict(action="CANCEL", what_changed="Cancelled by agency", status="Cancelled",
                      missing_info="ezfolio_group_code: not known", **{"Remaining amount": "0"})
        line = "Cancellation charge (Anex contract): 0 VND — 67 days before check-in, free (>21 days). Paid: 0 VND."
        self.assertTrue(has(check(notes=line, **cancel)[1], "notes: NOTES RULE"))
        self.assertTrue(has(check(notes=NOTES, **cancel)[1], "notes: on a CANCEL row item 6"))
        items = NOTES.splitlines()
        items[5] = "6. " + line
        self.assertFalse(has(check(notes="\n".join(items), **cancel)[1], "notes:"))

    def test_cancel_remaining_amount_is_zero(self):
        cancel = dict(action="CANCEL", what_changed="Cancelled by agency", status="Cancelled")
        self.assertTrue(has(check(**cancel, **{"Remaining amount": "6120000"})[0], "Remaining amount"))
        self.assertFalse(has(check(**cancel, **{"Remaining amount": "0"})[0], "Remaining amount"))


class PartialRowTest(unittest.TestCase):
    def test_one_or_two_cells_refused_as_a_stray_write(self):
        # row 79: {"source_email": "s"}
        errors, warnings = schema.check_row({"source_email": "s", "_row": 79})
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("row: only 1 cell(s) filled (source_email)"))
        self.assertTrue(schema.check_row({"action": "NEW", "booking_ref": "X", "tracy_status": "Pending"})[0][0]
                        .startswith("row: only 2 cell(s)"))


class LiveSheetDiffTest(unittest.TestCase):
    """Sandbox vs live sheet, 2026-10-27."""
    def test_booking_com_is_the_guest_total(self):
        self.assertTrue(has(check(rate_source="OTA net")[0], "rate_source: 'OTA net' on a Booking.com row"))
        self.assertFalse(has(check(company="Expedia", rate_source="OTA net", notes="")[0], "rate_source"))
        self.assertTrue(has(check(company="Expedia", rate_source="Booking.com guest total", notes="")[0],
                            "rate_source"))

    def test_meal_plan_and_adults_required(self):
        self.assertTrue(has(check(meal_plan="")[0], "meal_plan: required"))
        self.assertTrue(has(check(adults="")[0], "adults: required"))

    def test_arrival_before_the_email_is_a_wrong_year(self):
        errors, _ = check(arrival="12/11/2025", departure="14/11/2025", received_at="24/10/2026 18:28")
        self.assertTrue(has(errors, "arrival: 12/11/2025 is before the email"))
        self.assertFalse(has(check(action="CANCEL", what_changed="x", ezfolio_group_code="1",
                                   arrival="12/11/2025", departure="14/11/2025")[0], "arrival"))

    def test_wyndham_points_night_passes(self):
        zero = {"company": "Wyndham", "rate_per_night_vnd": "0", "Average rate per night after discount": "0",
                "total_vnd": "0", "rate_source": "Other", "notes": ""}
        self.assertEqual(check(**zero)[0], [])

    def test_tentative_without_hold_is_warned(self):
        self.assertTrue(has(check(status="Tentative")[1], "status: Tentative"))
        self.assertFalse(has(check(status="Tentative", hold_until="28/10/2026")[1], "status"))


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
        # live sheet: no tracy_status column, pdf_link alone marks the row built
        on_sheet = dict(ROW, pdf_link="Booking.pdf", ezfolio_group_code="G123", _row=40)
        on_sheet.pop("tracy_status")
        self.assertEqual(schema.check_row(on_sheet)[0], [])
        self.assertTrue(schema.is_built(on_sheet))


class RoundingTest(unittest.TestCase):
    def test_negative_rounding_in_surcharge_amount(self):
        # contract total 2,816,000 - 3: the difference goes in the extra-service columns (Tracy audit 29/10)
        errors, warnings = check(total_vnd="2815997", surcharge="Rounding -3", **{"Surcharge amount": "-3"})
        self.assertEqual(errors, [])
        self.assertFalse(has(warnings, "total_vnd"))

    def test_mismatch_suggests_the_rounding_line(self):
        w = next(x for x in check(total_vnd="2816004")[1] if x.startswith("total_vnd"))
        self.assertIn("'Rounding +4'", w)


if __name__ == "__main__":
    unittest.main()
