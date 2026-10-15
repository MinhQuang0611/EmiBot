"""Download a file from Google Drive with the service account (read-only scope).

The account sees only what is shared with it: the confirmations folder for real PDFs.
The Drive API must be enabled in the service account's Google Cloud project.
"""
import re
import urllib.parse

DRIVE = "https://www.googleapis.com/drive/v3/files"


def file_id(url):
    """Drive file id from a /file/d/<id>/, open?id=<id> or uc?id=<id> link; None if it isn't one."""
    m = re.search(r"/(?:file/)?d/([A-Za-z0-9_-]{20,})", url or "")
    if m:
        return m.group(1)
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url or "").query)
    ids = q.get("id")
    return ids[0] if ids else None


def download(call, fid):
    """(name, mimeType, bytes). `call` is the sheet's service-account transport."""
    meta = call("GET", f"{DRIVE}/{fid}?fields=name,mimeType,size&supportsAllDrives=true")
    if meta.get("mimeType", "").startswith("application/vnd.google-apps"):
        raise ValueError(f"{meta.get('name')} is a Google {meta['mimeType'].rsplit('.', 1)[-1]}, not a file; "
                         f"the confirmation must be the exported PDF")
    data = call("GET", f"{DRIVE}/{fid}?alt=media&supportsAllDrives=true", raw=True)
    return meta.get("name") or f"{fid}.pdf", meta.get("mimeType", "application/octet-stream"), data
