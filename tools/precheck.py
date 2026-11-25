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
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

from . import build_watch, config, payments

# Dev 26/11: job 2 ran 310 times in 7 days (~100M tokens), 303 of them woken by the 15-minute check, and only 35 made
# or changed a draft. The rest re-read the same list ("build dừng, chờ Karen E-676", "giữ xác nhận, đã hỏi E-716")
# because the check said "work" every time anything at all was owed. Now the check wakes job 2 only for work it has
# not been woken for (a new booking, a remade PDF, Karen's answer), when the last run made progress (fewer items:
# it works through 5 at a time), or WAKE_AGAIN after the last wake. Job 2's own first step (--agent) is unchanged.
WAKE_AGAIN = 4 * 3600


def inbox_has_work(mail, state, leftovers=False):
    """New mail since the last scan. leftovers=True (job 1's own first step, and so its 3-hourly safety run): also an
    email from the last days nobody marked done (Karen, 14/11, missed bookings), which inbox-new now lists again.
    The every-minute watcher keeps the one cheap call."""
    since = state.data["last_scan"]
    if since is None:
        return True
    if not leftovers:  # the watcher: Tracy's hourly audit alone waits for the next real run (dev 26/11)
        return mail.has_new_inbox_mail(since, skip_noise=True)
    if mail.has_new_inbox_mail(since):
        return True
    from .emi import unhandled_inbox
    return bool(unhandled_inbox(mail, state, since))


def confirmations_have_work(mail, sheet, state):
    return bool(confirmation_work(mail, sheet, state))


def confirmation_work(mail, sheet, state):
    """What job 2 is owed, one key per item: a confirmation (the booking, the build tool's stamps on its rows, the
    draft a PDF goes on) and a held booking to look at again (with Karen's answers on it). A remade PDF or a new
    answer gives a new key. Cancellations done in EZFOLIO carry no PDF; the build tool's signal for them isn't
    defined yet."""
    from .emi import _parts, booking_state, _today_vn
    rows = sheet.rows()
    stamp = {r["_row"]: f"{r.get('ez_processed_at') or ''}|{r.get('pdf_link') or ''}" for r in rows}
    keys = [json.dumps(["confirm", i["ref"], sorted({stamp.get(n, "") for n in i.get("rows") or [i["row"]]}),
                        i.get("attach") or ""], ensure_ascii=False)
            for i in payments.needs_confirmation(rows, booking_state, _parts, mail, state, config.MAILBOX,
                                                 _today_vn())]
    return keys + [json.dumps(["hold", ref, answered], ensure_ascii=False) for ref, answered in holds_to_look(state)]


def holds_to_look(state):
    """Held confirmations with no open question to Karen: never asked, or answered and not acted on (Karen 15/11,
    Greentours 0349-IN 1211 held three days unseen), with the ids of her answered questions on it. One waiting on
    Karen's answer doesn't wake job 2."""
    questions = state.data["questions"]
    out = []
    for ref in state.data["confirmation_holds"]:
        mine = {qid: q for qid, q in questions.items() if q.get("booking_ref") == ref}
        if not any(q.get("answer") is None and not q.get("closed") for q in mine.values()):
            out.append((ref, sorted(qid for qid, q in mine.items() if q.get("answer") is not None)))
    return out


def holds_need_a_look(state):
    return bool(holds_to_look(state))


def wake_path():
    return os.path.join(os.path.dirname(os.path.abspath(config.state_path())), "confirm-wake.json")


def should_wake(keys, path, now=time.time, out=None):
    """True when job 2 is to be started for these keys (see WAKE_AGAIN above), and then they are recorded as woken.
    Nothing owed clears the record, so the next item is new."""
    out = out or (lambda s: print(s, file=sys.stderr))
    try:
        with open(path, encoding="utf-8") as f:
            last = json.load(f)
    except (OSError, ValueError):
        last = {}
    seen, at = set(last.get("keys") or []), last.get("at", 0)
    keys = set(keys)
    if keys and not (keys - seen) and not (keys < seen) and now() - at < WAKE_AGAIN:
        out(f"job 2 not woken: the same {len(keys)} item(s) as the run at "
            f"{datetime.fromtimestamp(at, timezone(timedelta(hours=7))).strftime('%d/%m %H:%M')}, nothing new since")
        return False
    record = {"keys": sorted(keys), "at": now() if keys else at}
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False)
    return bool(keys)


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
        # dev 21/11: a booking with no room in EZFOLIO is declined by job 2 (CANCEL rows + decline draft); it stays
        # on the list, and wakes job 2, until its CANCEL rows are on the sheet
        return [json.dumps(["decline", i["ref"]], ensure_ascii=False) for i in items if i["kind"] == "full"]
    except Exception as e:
        print(f"build-stuck alert failed: {e}", file=sys.stderr)
        return []


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
            keys = confirmation_work(mail, sheet, st) + alert_build_stuck(mail, sheet)
            pegas_confirm(mail, sheet)
            # the 15-minute check (no --agent) starts job 2 on "work": only for work it wasn't woken for (dev 26/11)
            work = bool(keys) if agent else should_wake(keys, wake_path())
        else:
            work = payments_have_work(config.mail(), config.sheet(), st)
    except Exception as e:
        print(f"precheck {argv[0]} failed: {e}", file=sys.stderr)
        return 2
    print("work" if work else "quiet")
    return 0 if work or agent else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
