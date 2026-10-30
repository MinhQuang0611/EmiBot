"""Write the Google service-account key from an environment variable to EMI_GOOGLE_KEYFILE.

    python -m tools.google_key

For hosts where the only safe way in for a secret is the hosting panel's environment variables
(Hostinger's OpenClaw: chat goes through the model, the terminal blocks Python). Set
EMI_GOOGLE_KEY_B64 to the base64 of the JSON key file. The key is checked, written mode 600,
and never printed. Afterwards the panel variable can be removed.
"""
import base64
import json
import os
import sys

from . import config


def main():
    raw = os.environ.get("EMI_GOOGLE_KEY_B64", "").strip()
    if not raw:
        sys.exit("EMI_GOOGLE_KEY_B64 is not set in this environment")
    path = os.environ.get("EMI_GOOGLE_KEYFILE")
    if not path:
        sys.exit("EMI_GOOGLE_KEYFILE is not set (python -m tools.setenv EMI_GOOGLE_KEYFILE=...)")
    try:
        key = json.loads(base64.b64decode(raw))
    except ValueError:
        sys.exit("EMI_GOOGLE_KEY_B64 is not base64 of a JSON file")
    if key.get("type") != "service_account" or not key.get("private_key") or not key.get("client_email"):
        sys.exit("EMI_GOOGLE_KEY_B64 is not a Google service-account key")
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(key, f)
    os.chmod(path, 0o600)
    print(f"PASS: wrote key for {key['client_email']} to {path} (mode 600)")


if __name__ == "__main__":
    config.load_env()
    main()
