"""Mail watcher: run every minute as an OpenClaw command job (no model, no cost when quiet).

    python -m tools.watch <job1-automation-id>

New mail in sales@ since the last scan -> starts job 1 at once (`openclaw automations run <id>`), so a draft is
on Telegram a minute or two after the email lands instead of at the next scheduled run.
While a triggered job 1 is still working (its scan clock hasn't moved yet) it isn't started again, for up to
RUN_WINDOW; after that a run that died is retried.
Prints NO_REPLY when there is nothing to do. Exit 2 = the check failed (token, network): the run history shows it.
"""
import json
import os
import shutil
import subprocess
import sys
import time

from . import config
from .precheck import inbox_has_work

RUN_WINDOW = 25 * 60  # job 1's own timeout is 25 minutes


def _lock_path():
    return os.path.join(config.SIM_DIR or os.environ.get("EMI_WORK_DIR", "emi-work"), "watch.json")


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def check(mail, st, job_id, run=subprocess.run, now=time.time, lock_path=None, out=print):
    lock_path = lock_path or _lock_path()
    lock = _read(lock_path)
    if lock and lock.get("last_scan") == st.data["last_scan"] and now() - lock.get("triggered_at", 0) < RUN_WINDOW:
        out("NO_REPLY")  # job 1 started by us is still running
        return "running"
    if not inbox_has_work(mail, st):
        out("NO_REPLY")
        return "quiet"
    exe = shutil.which("openclaw") or "openclaw"
    res = run([exe, "automations", "run", job_id], capture_output=True, text=True, timeout=90)
    if res.returncode != 0:
        raise RuntimeError(f"could not start job 1: {(res.stderr or res.stdout).strip()[-300:]}")
    os.makedirs(os.path.dirname(os.path.abspath(lock_path)), exist_ok=True)
    with open(lock_path, "w", encoding="utf-8") as f:
        json.dump({"triggered_at": now(), "last_scan": st.data["last_scan"]}, f)
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
