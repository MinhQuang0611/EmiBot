#!/usr/bin/env bash
# Run one scheduled Emi job: cheap precheck first, wake the OpenClaw agent only if there is work.
# One lock per job so a slow run is never overlapped by the next one. Everything goes to a log.
# Runs INSIDE the OpenClaw container; host cron calls it with:
#   docker exec openclaw-lk3h-openclaw-1 /data/emi/deploy/run-job.sh inbox|confirmations|payments|report
set -uo pipefail

JOB="${1:?usage: run-job.sh inbox|confirmations|payments|report}"
REPO="${EMI_REPO:-/data/emi}"
LOG_DIR="${EMI_LOG_DIR:-/data/emi-logs}"
AGENT_ID="${EMI_AGENT_ID:-emi}"
# OpenClaw 2026.9.4: `openclaw agent --agent <id> -m <text>` runs one turn via the gateway.
AGENT_CMD="${EMI_AGENT_CMD:-openclaw agent --agent $AGENT_ID -m}"
PY="$REPO/.venv/bin/python"

mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/$JOB.log"
ts() { TZ=Asia/Ho_Chi_Minh date '+%Y-%m-%d %H:%M:%S'; }

exec 9>"/tmp/emi-$JOB.lock"
if ! flock -n 9; then
  echo "$(ts) [$JOB] previous run still going, skipped" >> "$LOG"
  exit 0
fi

case "$JOB" in
  inbox)         PRE="inbox";         MSG="Run scheduled job 1 (inbox scan + 40-hour deposit reminders) as described in schedule.md." ;;
  confirmations) PRE="confirmations"; MSG="Run scheduled job 2 (confirmation drafts) as described in schedule.md." ;;
  payments)      PRE="";              MSG="Run scheduled job 3 (payment deadline check) as described in schedule.md." ;;
  report)        PRE="";              MSG="Run scheduled job 4 (daily report to Karen) as described in schedule.md." ;;
  *) echo "unknown job $JOB" >&2; exit 2 ;;
esac

if [ -n "$PRE" ]; then
  (cd "$REPO" && "$PY" -m tools.precheck "$PRE") >> "$LOG" 2>&1
  rc=$?
  if [ $rc -eq 1 ]; then echo "$(ts) [$JOB] quiet" >> "$LOG"; exit 0; fi
  if [ $rc -ne 0 ]; then echo "$(ts) [$JOB] PRECHECK FAILED rc=$rc" >> "$LOG"; exit $rc; fi
fi

echo "$(ts) [$JOB] waking agent $AGENT_ID" >> "$LOG"
$AGENT_CMD "$MSG" >> "$LOG" 2>&1
rc=$?
echo "$(ts) [$JOB] agent exit rc=$rc" >> "$LOG"
exit $rc
