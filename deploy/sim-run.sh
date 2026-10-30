#!/usr/bin/env bash
# One command, whole SIM test from the dev machine:
#   deploy/sim-run.sh new-change-cancel
# 1. host: git pull, copy persona/skills/rate files to the workspace, run the offline tests
# 2. host: sim-reset <scenario> and switch EMI_SIM_DIR on in /data/emi/.env
# 3. Emi, fresh session: "Chạy job 1 theo schedule.md" — reads the scenario's .eml files, writes the sandbox sheet
# 4. host: sim-check <scenario>, then EMI_SIM_DIR switched off again (also if a step fails)
# Logs to emi-work/sim-logs/<scenario>-<time>.log on the dev machine.
set -uo pipefail

SCENARIO="${1:?usage: deploy/sim-run.sh <scenario in test/sim/>}"
HERE="$(cd "$(dirname "$0")" && pwd)"
REMOTE="$HERE/emi-remote.sh"
LOGDIR="$HERE/../emi-work/sim-logs"; mkdir -p "$LOGDIR"
LOG="$LOGDIR/$SCENARIO-$(date +%Y%m%d-%H%M%S).log"
SIM_DIR="/data/emi/emi-work/sim/$SCENARIO"

ask() {  # $1 session key, $2 timeout seconds, $3 message
  bash "$REMOTE" agent --agent emi --session-key "$1" --timeout "$2" -m "$3" 2>&1 | tee -a "$LOG"
  return "${PIPESTATUS[0]}"
}

sim_off() {
  echo "== switching SIM off" | tee -a "$LOG"
  ask agent:emi:dev 300 "Chạy và dán NGUYÊN VĂN output: cd /data/emi && .venv/bin/python -m tools.setenv EMI_SIM_DIR= && grep -c '^EMI_SIM_DIR=.' .env" >/dev/null
}
trap sim_off EXIT

echo "== 1-2. deploy + reset $SCENARIO" | tee -a "$LOG"
ask agent:emi:dev 540 "Chạy và dán NGUYÊN VĂN output: cd /data/emi && git pull --ff-only 2>&1 | tail -1 && cp schedule.md AGENTS.md /data/.openclaw/workspace-emi/ && cp skills/*.md /data/.openclaw/workspace-emi/skills/ && cp docs/rate-knowledge/* /data/.openclaw/workspace-emi/docs/rate-knowledge/ && .venv/bin/python -m unittest discover -s tools/tests -t . 2>&1 | grep -E '^(FAIL|ERROR)|Ran|^OK' && git log --oneline -1 && .venv/bin/python -m tools.emi sim-reset $SCENARIO && .venv/bin/python -m tools.setenv EMI_SIM_DIR=$SIM_DIR && .venv/bin/python -m tools.emi inbox-new | grep -E 'SIM MODE|new emails'" \
  || { echo "setup failed" | tee -a "$LOG"; exit 2; }
grep -q "SIM MODE" "$LOG" || { echo "SIM mode not confirmed on the host — not running the job" | tee -a "$LOG"; exit 2; }

echo "== 3. Emi runs job 1 (fresh session)" | tee -a "$LOG"
ask "agent:emi:sim-$(date +%s)" 1700 "Chạy job 1 theo schedule.md. (Lượt test SIM MODE: mail đọc từ file, draft ghi ra file — cứ làm đúng như chạy thật.) Cuối cùng trả về bảng báo cáo và liệt kê từng lệnh tools.emi em đã chạy."

echo "== 4. grade" | tee -a "$LOG"
ask agent:emi:dev 540 "Chạy và dán NGUYÊN VĂN toàn bộ output, không tóm tắt: cd /data/emi && .venv/bin/python -m tools.emi sim-check $SCENARIO"
grep -E "^(PASS|FAIL) |^RESULT" "$LOG" | tail -40
echo "log: $LOG"
