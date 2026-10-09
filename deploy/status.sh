#!/usr/bin/env bash
# One screen to see what's deployed and whether the jobs are healthy.
#   deploy/status.sh
# Runs on the HOST. Host /docker/openclaw-lk3h/data = /data in the container.
DATA="${OPENCLAW_DATA:-/docker/openclaw-lk3h/data}"
REPO="${EMI_REPO_HOST:-$DATA/emi}"
WS="${EMI_WORKSPACE_HOST:-$DATA/.openclaw/workspace-emi}"
LOG_DIR="${EMI_LOG_DIR_HOST:-$DATA/emi-logs}"

echo "== Deployed version"
cat "$WS/DEPLOYED_VERSION" 2>/dev/null || echo "(not synced yet)"
echo "openclaw: $(docker exec openclaw-lk3h-openclaw-1 openclaw --version 2>&1 | head -1)"
docker exec openclaw-lk3h-openclaw-1 openclaw agents list 2>/dev/null | grep -E "^- " || true
echo "repo HEAD: $(git -C "$REPO" log -1 --format='%h %s (%cr)' 2>/dev/null)"
git -C "$REPO" fetch -q 2>/dev/null && echo "behind origin: $(git -C "$REPO" rev-list --count HEAD..@{u} 2>/dev/null) commit(s)"

echo; echo "== Secrets present (contents never printed)"
for f in "$REPO/.env" "${EMI_GOOGLE_KEYFILE_PATH:-$REPO/secrets/google-service-account.json}"; do
  if [ -f "$f" ]; then echo "ok   $f ($(stat -c %a "$f"))"; else echo "MISSING $f"; fi
done

echo; echo "== Cron lines"
crontab -l 2>/dev/null | grep -F "run-job.sh" || echo "(no Emi cron lines — jobs are OFF)"

echo; echo "== Last activity per job"
for j in inbox confirmations payments report; do
  printf '%-14s ' "$j"; tail -n 1 "$LOG_DIR/$j.log" 2>/dev/null || echo "(no log)"
done

echo; echo "== Failures in the last 200 log lines"
cat "$LOG_DIR"/*.log 2>/dev/null | tail -n 200 | grep -E "FAILED|rc=[1-9]|Traceback|HttpError" || echo "none"
