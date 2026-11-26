"""Mail watcher: run every minute as an OpenClaw command job (no model, no cost when quiet).

    python -m tools.watch <job1-automation-id>

New mail in sales@ since the last scan -> starts job 1 (`openclaw automations run <id>`) once the oldest email waiting
has been in the inbox BATCH_WAIT (dev, 2026-11-26: "chờ 10 phút oke"). Before, every email started its own run at
once: 100 of 162 runs on 25-26/11 had a single email, each ~300k+ tokens before reading it. A draft now reaches
Telegram at most ~10 minutes after the email lands, and the emails of those minutes go in one run.
Auto-replies (out-of-office, autoresponders) are marked done here, by code (tools/auto_reply.py), and start nothing.
Tracy's hourly "HAYA intake audit" alone starts nothing either (dev 26/11): job 1 reads it on its next run.
While a triggered job 1 is still working (its scan clock hasn't moved yet) it isn't started again, for up to
RUN_WINDOW; after that a run that died is retried. A run that ended with mail left over but handled some (a run
takes a few emails, schedule.md) frees the lock at once, so the next one starts a minute later (dev, 30/10).
Prints NO_REPLY when there is nothing to do. Exit 2 = the check failed (token, network): the run history shows it.
"""
import json
import os
import shutil
import subprocess
import sys
import time

from . import auto_reply, config
from .graph_mail import is_search_noise

RUN_WINDOW = 25 * 60  # job 1's own timeout is 25 minutes
BATCH_WAIT = 10 * 60  # dev 26/11: the oldest waiting email is this old before job 1 starts


def _work_dir():
    return config.SIM_DIR or os.environ.get("EMI_WORK_DIR", "emi-work")


def _lock_path():
    return os.path.join(_work_dir(), "watch.json")


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _finished_since(exe, job_id, started_at, run):
    """True when job 1's latest finished run began at or after started_at (the run history lists finished runs)."""
    try:
        res = run([exe, "automations", "runs", "--id", job_id, "--limit", "1"], capture_output=True, text=True,
                  timeout=60)
        text = res.stdout or ""
        last = (json.loads(text[text.index("{"):]).get("entries") or [{}])[0]
    except (ValueError, OSError, subprocess.SubprocessError):
        return False
    return last.get("runAtMs", 0) >= (started_at - 60) * 1000


def waiting_mail(mail, st):
    """Emails since the scan clock that job 1 has to read: not done yet, not Tracy's audit. None = a full page
    (a flood): start at once, no waiting."""
    got = mail.new_inbox_mail(st.data["last_scan"])
    if len(got) >= getattr(mail, "NEW_MAIL_PAGE", 50):
        return None
    return [m for m in got if not is_search_noise(m) and m["id"] not in (st.data.get("processed") or {})]


def close_auto_replies(msgs):
    """The watcher's own state write: under the state lock, on the state as it is now."""
    from .emi import vn
    from .state import hold_lock
    hold_lock(config.state_path())
    st = config.state()
    msgs = [m for m in msgs if not st.is_processed(m["id"])]
    tg = None
    try:
        tg = config.telegram()
    except Exception:
        pass
    auto_reply.close(st, msgs, tg=tg, work_dir=_work_dir(), vn=vn, out=lambda s: print(s, file=sys.stderr))
    st.save()


def check(mail, st, job_id, run=subprocess.run, now=time.time, lock_path=None, out=print, closer=None,
          cache_path=None):
    lock_path = lock_path or _lock_path()
    lock = _read(lock_path)
    exe = shutil.which("openclaw") or "openclaw"
    if lock and lock.get("last_scan") == st.data["last_scan"] and now() - lock.get("triggered_at", 0) < RUN_WINDOW:
        # Mail handled since the start and the run is over: the next batch goes now. No progress: wait out the
        # window, so a run that keeps failing on the same email isn't restarted every minute.
        handled = len(st.data.get("processed") or {})
        if not (handled > lock.get("processed", handled) and _finished_since(exe, job_id, lock["triggered_at"], run)):
            out("NO_REPLY")  # job 1 started by us is still running
            return "running"
    if st.data["last_scan"] is None:
        msgs = None
    else:
        msgs = waiting_mail(mail, st)
    if msgs:
        autos = auto_reply.find(mail, msgs, cache_path=cache_path or os.path.join(_work_dir(), "auto-reply.json"),
                                now=now)
        if autos:
            (closer or close_auto_replies)(autos)
            for m in autos:  # the count below sees them as handled, so they aren't taken for a run's progress
                st.data.setdefault("processed", {})[m["id"]] = {"outcome": auto_reply.OUTCOME}
            msgs = [m for m in msgs if m not in autos]
        if not msgs:
            out("NO_REPLY")
            return "quiet"
        oldest = min(auto_reply.received_epoch(m) for m in msgs)
        if now() - oldest < BATCH_WAIT:
            out("NO_REPLY")  # the batch is still filling: the next minutes' emails go in the same run
            return "waiting"
    elif msgs is not None:
        out("NO_REPLY")
        return "quiet"
    handled = len(st.data.get("processed") or {})
    res = run([exe, "automations", "run", job_id], capture_output=True, text=True, timeout=90)
    if res.returncode != 0 and '"already-running"' in f"{res.stdout or ''}{res.stderr or ''}":
        # A job 1 run started elsewhere (its 3-hourly run, job 6, a person) is working: it or the next minute's
        # check takes the new mail. Not a failure (dev, 2026-11-21: five false "watch failed" on 20/11).
        out("NO_REPLY")
        return "running"
    if res.returncode != 0:
        raise RuntimeError(f"could not start job 1: {(res.stderr or res.stdout).strip()[-300:]}")
    os.makedirs(os.path.dirname(os.path.abspath(lock_path)), exist_ok=True)
    with open(lock_path, "w", encoding="utf-8") as f:
        json.dump({"triggered_at": now(), "last_scan": st.data["last_scan"], "processed": handled}, f)
    out("new mail: job 1 started")
    return "started"


def main(argv):
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        check(config.mail(), config.state(), argv[0])
    except Exception as e:
        print(f"watch failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
