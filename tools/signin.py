"""sales@ sign-in refused: one Telegram line in 📊 Báo cáo, not a job that hangs or fails every minute.

26/11 17:15–00:00 (dev, 27/11): Microsoft stopped taking the cached refresh token. Every command then waited 15
minutes for a device-code sign-in nobody saw; the ones holding the state lock made the others time out, and the mail
watcher was switched off after 10 failed runs. Now the token raises SignInNeeded at once, and the minute checks
(tools.watch, tools.precheck) post this line, at most every EVERY, and stay quiet, so they pick up again by
themselves once Karen has signed in.
"""
import json
import os
import sys
import time

EVERY = 6 * 3600


def _path(work_dir):
    return os.path.join(work_dir, "signin-alert.json")


def alert(err, tg, work_dir, now=time.time, out=lambda s: print(s, file=sys.stderr)):
    """Post the refusal once per EVERY (again at once when Microsoft's words change). Returns True when posted."""
    text = str(err)
    out(f"SIGN-IN NEEDED: {text}")
    path = _path(work_dir)
    try:
        with open(path, encoding="utf-8") as f:
            last = json.load(f)
    except (OSError, ValueError):
        last = {}
    if last.get("error") == text and now() - last.get("at", 0) < EVERY:
        return False
    if tg is None:
        return False
    try:
        tg.send("📛 <b>Emi không đọc được hộp thư sales@</b>: Microsoft từ chối đăng nhập.\n"
                f"<code>{_esc(text[:400])}</code>\n"
                "Mọi job đọc mail đang dừng cho tới khi Karen đăng nhập lại: dev chạy "
                "<code>python -m tools.acceptance mail-login-start --send</code> trong chat của Emi, Karen mở link và "
                "nhập mã bằng tài khoản sales@, rồi chạy <code>python -m tools.acceptance mail-login-finish</code>.",
                topic="report")
    except Exception as e:  # Telegram down too: the stderr line above is all there is
        out(f"sign-in alert not posted: {type(e).__name__}: {e}")
        return False
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"error": text, "at": now()}, f)
    return True


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
