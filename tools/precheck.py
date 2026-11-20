"""Cheap check before a cron job wakes the agent (openclaw-setup-brief.md step 6).

    python -m tools.precheck inbox          # job 1
    python -m tools.precheck confirmations  # job 2; also sends Karen the bookings the build tool stopped on
                                            # and presses Confirm on Pegasys (EMI_PEGAS_CONFIRM=1)
    python -m tools.precheck payments       # job 3: a reminder is due
    python -m tools.precheck inbox --agent  # the agent's own first step in job 1 (schedule.md)

Exit 0 = there is work, start the agent. Exit 1 = nothing to do. Exit 2 = the check itself failed
(bad token, sheet not shared); the message goes to stderr and the cron log.
Cron line:  python -m tools.precheck inbox && <start Emi with job 1>
--agent: exit 0 for both `work` and `quiet` (read the printed word). The OpenClaw gateway records a Bash call
that exits 1 as a failed run (audit 30/10: every quiet safety-net run showed as "Bash failed").
"""
import sys
from datetime import datetime

from . import build_watch, config, payments


def inbox_has_work(mail, state, leftovers=False):
    """New mail since the last scan. leftovers=True (job 1's own first step, and so its 3-hourly safety run): also an
    email from the last days nobody marked done (Karen, 14/11, missed bookings), which inbox-new now lists again.
    The every-minute watcher keeps the one cheap call."""
    since = state.data["last_scan"]
    if since is None or mail.has_new_inbox_mail(since):
        return True
    if not leftovers:
        return False
    from .emi import unhandled_inbox
    return bool(unhandled_inbox(mail, state, since))


def confirmations_have_work(mail, sheet, state):
    # Cancellations done in EZFOLIO carry no PDF; the build tool's signal for them isn't defined yet.
    from .emi import _parts, booking_state, _today_vn
    return bool(payments.needs_confirmation(sheet.rows(), booking_state, _parts, mail, state, config.MAILBOX,
                                            _today_vn())) or holds_need_a_look(state)


def holds_need_a_look(state):
    """A held confirmation with no open question to Karen: never asked, or answered and not acted on (Karen 15/11,
    Greentours 0349-IN 1211 held three days unseen). One waiting on Karen's answer doesn't wake job 2."""
    questions = state.data["questions"].values()
    return any(not any(q.get("booking_ref") == ref and q.get("answer") is None and not q.get("closed")
                       for q in questions)
               for ref in state.data["confirmation_holds"])


def alert_build_stuck(mail, sheet):
    """Dev 07/11: rows the build tool stopped on (needs_review / error) or never picked up go to Karen on Telegram,
    once each (tools/build_watch.py). A side job of the hourly confirmation check, so it needs no model. Its own
    failure never changes the check's answer: the line goes to stderr."""
    from .emi import booking_state, VN
    from .state import hold_lock
    try:
        hold_lock(config.state_path())
        st = config.state()  # read after the lock: a command may have saved it meanwhile
        items = build_watch.stuck(sheet.rows(), booking_state, datetime.now(VN))
        sent = build_watch.alert(st, config.telegram(), mail, items, config.MAILBOX,
                                 out=lambda s: print(s, file=sys.stderr))
        if sent:
            st.save()
    except Exception as e:
        print(f"build-stuck alert failed: {e}", file=sys.stderr)


def pegas_confirm(mail, sheet):
    """Dev 20/11: Emi presses Confirm on the Pegas provider site once HAYA's confirmation has gone to Pegas
    (tools/pegasys.py). A side job of the 15-minute confirmation check, like the build-stuck alert: no model, and its
    own failure never changes the check's answer. Off unless EMI_PEGAS_CONFIRM=1."""
    from . import pegasys
    if not pegasys.enabled():
        return
    from .emi import booking_state, VN
    from .state import hold_lock
    try:
        hold_lock(config.state_path())
        st = config.state()
        items, _ = pegasys.due(mail, sheet.rows(), booking_state, st, config.MAILBOX, datetime.now(VN))
        if items:
            pegasys.run(items, pegasys.from_env(), st, field=pegasys.conf_field(), tg=config.telegram(),
                        out=lambda s: print(s, file=sys.stderr))
        st.save()  # the robot links read this run are kept even when nothing was pressed
    except Exception as e:
        print(f"pegas confirm failed: {e}", file=sys.stderr)


def payments_have_work(mail, sheet, state):
    from .emi import _parts, booking_state, VN
    from datetime import datetime
    r = payments.due(sheet.rows(), booking_state, _parts, mail, state, config.MAILBOX, datetime.now(VN))
    return bool(r["remind"] or r["slip"])


def main(argv):
    agent = "--agent" in argv
    argv = [a for a in argv if a != "--agent"]
    if len(argv) != 1 or argv[0] not in ("inbox", "confirmations", "payments"):
        print(__doc__, file=sys.stderr)
        return 2
    try:
        st = config.state()
        if argv[0] == "inbox":
            work = inbox_has_work(config.mail(), st, leftovers=agent)
        elif argv[0] == "confirmations":
            mail, sheet = config.mail(), config.sheet()
            work = confirmations_have_work(mail, sheet, st)
            alert_build_stuck(mail, sheet)
            pegas_confirm(mail, sheet)
        else:
            work = payments_have_work(config.mail(), config.sheet(), st)
    except Exception as e:
        print(f"precheck {argv[0]} failed: {e}", file=sys.stderr)
        return 2
    print("work" if work else "quiet")
    return 0 if work or agent else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
