"""Minimal JSON-over-HTTP helper on the standard library, so the host needs no extra packages for Graph."""
import json
import urllib.error
import urllib.parse
import urllib.request


class HttpError(Exception):
    def __init__(self, status, url, body):
        super().__init__(f"HTTP {status} for {url}: {body[:500]}")
        self.status = status
        self.url = url
        self.body = body


def request(method, url, headers=None, body=None, form=None, timeout=60):
    """Return the decoded JSON response, or {} for an empty body. Raises HttpError on 4xx/5xx."""
    headers = dict(headers or {})
    data = None
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        raise HttpError(e.code, url, e.read().decode(errors="replace")) from None
    return json.loads(raw) if raw else {}
