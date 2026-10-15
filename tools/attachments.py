"""Save email attachments to disk and pull out their text, so the agent can read vouchers,
rooming lists and payment slips without opening Outlook.

PDF needs pypdf, Excel needs openpyxl (requirements.txt). Images are saved and listed; the
agent opens the file itself to read a payment slip screenshot.
"""
import csv
import hashlib
import io
import os
import re
import zipfile

MAX_TEXT = 20000           # characters of extracted text printed per file
SMALL_INLINE_IMAGE = 15000  # bytes; inline images under this are logos and signatures
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".heic", ".tif", ".tiff"}


def message_dir(work_dir, message_id):
    """One folder per message, named by a short hash of the Graph id (ids are too long for paths)."""
    return os.path.join(work_dir, hashlib.sha1(message_id.encode()).hexdigest()[:12])


def safe_name(name):
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", name or "attachment").strip(" .")
    return name[:150] or "attachment"


def skip(att):
    """Inline logos and signature images are noise."""
    ext = os.path.splitext(att.get("name") or "")[1].lower()
    return att.get("isInline") and ext in IMAGE_EXT and len(att.get("data", b"")) < SMALL_INLINE_IMAGE


def save(folder, att):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, safe_name(att.get("name")))
    with open(path, "wb") as f:
        f.write(att["data"])
    return path


def extract_text(path, data):
    """Best-effort text for the agent. Never raises: a broken file returns a note instead."""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".pdf":
            text = _pdf(data)
            return text if text.strip() else "(PDF has no text layer — likely a scan; open the file to read it)"
        if ext in (".xlsx", ".xlsm"):
            return _xlsx(data)
        if ext == ".docx":
            return _docx(data)
        if ext in (".csv", ".txt"):
            return _decode(data)
        if ext in IMAGE_EXT:
            return "(image — open the file to read it)"
        if ext == ".xls":
            return "(old .xls format, not extracted — ask for .xlsx or read it another way)"
        return f"({ext or 'no extension'} not extracted)"
    except ImportError as e:
        return f"(not extracted: {e.name} is not installed — pip install -r requirements.txt)"
    except Exception as e:
        return f"(could not read file: {type(e).__name__}: {e})"


def _decode(data):
    for enc in ("utf-8-sig", "cp1258", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "replace")


def _pdf(data):
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    return "\n".join(f"--- page {i} ---\n{p.extract_text() or ''}" for i, p in enumerate(reader.pages, 1))


def _xlsx(data):
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    out = []
    for ws in wb.worksheets:
        out.append(f"--- sheet {ws.title} ---")
        buf = io.StringIO()
        w = csv.writer(buf, delimiter="\t", lineterminator="\n")
        for row in ws.iter_rows(values_only=True):
            if any(c not in (None, "") for c in row):
                w.writerow(["" if c is None else c for c in row])
        out.append(buf.getvalue())
    return "\n".join(out)


def _docx(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    xml = re.sub(r"</w:p>", "\n", xml)
    return re.sub(r"<[^>]+>", "", xml)


def clip(text):
    return text if len(text) <= MAX_TEXT else text[:MAX_TEXT] + f"\n... ({len(text) - MAX_TEXT} more characters in the file)"
