"""Read and write the "HAYA Ezfolio Booking Intake v2" sheet.

Row 1 = header, row 2 = column instructions, data from row 3. Columns are mapped by header name,
never by position, because the columns are a contract with the EZFOLIO build tool and Emi must
not add, rename, or reorder them (openclaw-setup-brief.md step 5).
"""
import urllib.parse

from . import httpjson

SHEETS = "https://sheets.googleapis.com/v4/spreadsheets"
FIRST_DATA_ROW = 3

# Written by the build tool, not by Emi. Emi only sets tracy_status = Pending on a new row.
BUILD_TOOL_COLUMNS = {"tracy_status", "pdf_link"}
REQUIRED = ("company", "arrival", "departure", "rate_per_night_vnd", "room_code", "rooms")


class SheetContractError(Exception):
    pass


def col_letter(index):
    """0 -> A, 25 -> Z, 26 -> AA."""
    s = ""
    index += 1
    while index:
        index, r = divmod(index - 1, 26)
        s = chr(65 + r) + s
    return s


def google_service_account_transport(keyfile):
    """Transport signed by a Google service account. Needs `pip install google-auth` on the host."""
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request

    creds = service_account.Credentials.from_service_account_file(
        keyfile, scopes=["https://www.googleapis.com/auth/spreadsheets",
                         "https://www.googleapis.com/auth/drive.readonly"])

    def call(method, url, body=None):
        if not creds.valid:
            creds.refresh(Request())
        return httpjson.request(method, url, headers={"Authorization": f"Bearer {creds.token}"}, body=body)

    return call


class IntakeSheet:
    def __init__(self, sheet_id, transport, tab="Intake", value_input="RAW"):
        self.base = f"{SHEETS}/{sheet_id}"
        self.call = transport
        self.tab = tab
        # RAW keeps "21/11/2026" as typed text. Switch to USER_ENTERED only if Karen's sheet
        # needs real date cells; that parses by the sheet's locale, so test it first.
        self.value_input = value_input
        self._header = None

    def _range(self, a1):
        return urllib.parse.quote(f"'{self.tab}'!{a1}", safe="")

    @property
    def header(self):
        if self._header is None:
            resp = self.call("GET", f"{self.base}/values/{self._range('1:1')}")
            self._header = [h.strip() for h in resp.get("values", [[]])[0]]
            if not self._header:
                raise SheetContractError(f"tab {self.tab!r} has no header row")
        return self._header

    def check_header(self, expected):
        """Return (missing, extra) column names versus an expected list."""
        have = set(self.header)
        want = set(expected)
        return sorted(want - have), sorted(have - want)

    def rows(self):
        """All data rows as dicts, each with its sheet row number under '_row'."""
        last = col_letter(len(self.header) - 1)
        resp = self.call("GET", f"{self.base}/values/{self._range(f'A{FIRST_DATA_ROW}:{last}')}")
        out = []
        for i, values in enumerate(resp.get("values", [])):
            if not any(v.strip() for v in values):
                continue
            row = {h: (values[j] if j < len(values) else "") for j, h in enumerate(self.header)}
            row["_row"] = FIRST_DATA_ROW + i
            out.append(row)
        return out

    def find_by_ref(self, booking_ref):
        ref = booking_ref.strip().lower()
        return [r for r in self.rows() if r.get("booking_ref", "").strip().lower() == ref]

    def rows_awaiting_confirmation(self, already_drafted):
        """Rows with a pdf_link whose (booking_ref, row) has no confirmation draft yet."""
        return [r for r in self.rows()
                if r.get("pdf_link", "").strip() and (r.get("booking_ref"), r["_row"]) not in already_drafted]

    def _to_values(self, record):
        unknown = set(record) - set(self.header) - {"_row"}
        if unknown:
            raise SheetContractError(f"columns not on the sheet: {sorted(unknown)}")
        return [record.get(h, "") for h in self.header]

    def append_rows(self, records):
        """Append new booking rows. Duplicates are the caller's check (booking-intake.md step 2)."""
        values = []
        for rec in records:
            touched = BUILD_TOOL_COLUMNS & {k for k, v in rec.items() if v and not (k == "tracy_status" and v == "Pending")}
            if touched:
                raise SheetContractError(f"Emi doesn't write {sorted(touched)}")
            rec = dict(rec, tracy_status="Pending")
            values.append(self._to_values(rec))
        return self.call("POST",
                         f"{self.base}/values/{self._range('A1')}:append"
                         f"?valueInputOption={self.value_input}&insertDataOption=INSERT_ROWS",
                         body={"values": values})

    def update_cells(self, row_number, fields):
        """Update named cells on one row, leaving every other cell as it is."""
        if row_number < FIRST_DATA_ROW:
            raise SheetContractError("rows 1-2 are header and instructions")
        touched = BUILD_TOOL_COLUMNS & set(fields)
        if touched:
            raise SheetContractError(f"Emi doesn't write {sorted(touched)}")
        self._to_values(fields)  # rejects unknown columns
        data = [{"range": f"'{self.tab}'!{col_letter(self.header.index(k))}{row_number}", "values": [[v]]}
                for k, v in fields.items()]
        return self.call("POST", f"{self.base}/values:batchUpdate",
                         body={"valueInputOption": self.value_input, "data": data})

    def delete_test_row(self, row_number):
        """Delete a row only if its booking_ref starts with TEST- (acceptance test 7)."""
        row = next((r for r in self.rows() if r["_row"] == row_number), None)
        if not row or not row.get("booking_ref", "").upper().startswith("TEST-"):
            raise SheetContractError(f"row {row_number} is not a TEST- row; refusing to delete")
        meta = self.call("GET", f"{self.base}?fields=sheets.properties")
        gid = next(s["properties"]["sheetId"] for s in meta["sheets"] if s["properties"]["title"] == self.tab)
        return self.call("POST", f"{self.base}:batchUpdate", body={"requests": [{"deleteDimension": {
            "range": {"sheetId": gid, "dimension": "ROWS", "startIndex": row_number - 1, "endIndex": row_number}}}]})


def missing_required(record):
    return [c for c in REQUIRED if not str(record.get(c, "")).strip()]
