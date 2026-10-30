"""Cheap check before a cron job wakes the agent (openclaw-setup-brief.md step 6).

    python -m tools.precheck inbox          # job 1
    python -m tools.precheck confirmations  # job 2
    python -m tools.precheck inbox --agent  # the agent's own first step in job 1 (schedule.md)

Exit 0 = there is work, start the agent. Exit 1 = nothing to do. Exit 2 = the check itself failed
(bad token, sheet not shared); the message goes to stderr and the cron log.
Cron line:  python -m tools.precheck inbox && <start Emi with job 1>
--agent: exit 0 for both `work` and `quiet` (read the printed word). The OpenClaw gateway records a Bash call
that exits 1 as a failed run (audit 30/10: every quiet safety-net run showed as "Bash failed").
"""
import sys

from . import config


def inbox_has_work(mail, state):
    since = state.data["last_scan"]
    return since is None or mail.has_new_inbox_mail(since)


def confirmations_have_work(sheet, state):
    # Cancellations done in EZFOLIO carry no PDF; the build tool's signal for them isn't defined yet.
    return bool(sheet.rows_awaiting_confirmation(state.confirmation_drafted()))


def main(argv):
    agent = "--agent" in argv
    argv = [a for a in argv if a != "--agent"]
    if len(argv) != 1 or argv[0] not in ("inbox", "confirmations"):
        print(__doc__, file=sys.stderr)
        return 2
    try:
        st = config.state()
        if argv[0] == "inbox":
            work = inbox_has_work(config.mail(), st)
        else:
            work = confirmations_have_work(config.sheet(), st)
    except Exception as e:
        print(f"precheck {argv[0]} failed: {e}", file=sys.stderr)
        return 2
    print("work" if work else "quiet")
    return 0 if work or agent else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
