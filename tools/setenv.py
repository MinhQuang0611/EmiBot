"""Set keys in .env from one command line, for shells without heredocs (Hostinger's lshell).

    python -m tools.setenv KEY=VALUE [KEY=VALUE ...]          # add or replace
    python -m tools.setenv --if-missing KEY=VALUE [...]        # only add keys that aren't set yet
    python -m tools.setenv --show                              # key names, values hidden

Other lines and comments are kept. The file is written with mode 600. Never pass a secret here:
it would land in shell history. Secrets go in with `read -s` or a file.
"""
import os
import sys

from .config import ENV_FILE


def _read(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return f.read().splitlines()


def _key(line):
    s = line.strip()
    if not s or s.startswith("#") or "=" not in s:
        return None
    return s.split("=", 1)[0].strip()


def set_keys(pairs, path=ENV_FILE, if_missing=False):
    lines = _read(path)
    have = {_key(l): i for i, l in enumerate(lines) if _key(l)}
    for k, v in pairs:
        if k in have:
            if if_missing and lines[have[k]].split("=", 1)[1].strip():
                continue
            lines[have[k]] = f"{k}={v}"
        else:
            have[k] = len(lines)
            lines.append(f"{k}={v}")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    os.chmod(path, 0o600)


def show(path=ENV_FILE):
    for l in _read(path):
        k = _key(l)
        if k:
            print(k, "set" if l.split("=", 1)[1].strip() else "(empty)")


def main(argv):
    if argv == ["--show"]:
        return show()
    if_missing = bool(argv) and argv[0] == "--if-missing"
    args = argv[1:] if if_missing else argv
    pairs = []
    for a in args:
        k, sep, v = a.partition("=")
        if not sep or not k.isidentifier():
            sys.exit(f"not KEY=VALUE: {a}\n\n{__doc__}")
        pairs.append((k, v))
    if not pairs:
        sys.exit(__doc__)
    set_keys(pairs, if_missing=if_missing)
    show()


if __name__ == "__main__":
    main(sys.argv[1:])
