#!/usr/bin/env bash
# Run an OpenClaw CLI command against the hotpink-bee Gateway from the dev machine.
#   deploy/emi-remote.sh gateway health
#   deploy/emi-remote.sh agent --agent emi -m "Chạy job 1 theo schedule.md"
#
# hotpink-bee sits behind Hostinger's access page: POST /login with the gateway token sets a
# 2-hour cookie, and the WebSocket upgrade is refused without it. So each run logs in first and
# hands the cookie to the CLI through gateway.remote.edgeAuth in a separate profile ("hotpink",
# state in ~/.openclaw-hotpink), leaving the machine's default OpenClaw config alone.
# One-time profile setup (already done on the dev machine, 2026-10-15):
#   openclaw --profile hotpink config set gateway.mode remote
#   openclaw --profile hotpink config set gateway.remote.url wss://hotpink-bee-609973.hostingersite.com
#   openclaw --profile hotpink config set gateway.remote.token --ref-provider default --ref-source env --ref-id OPENCLAW_GATEWAY_TOKEN
#   openclaw --profile hotpink config set gateway.remote.edgeAuth.Cookie --ref-provider default --ref-source env --ref-id HOSTINGER_OPENCLAW_COOKIE
# Reads only OPENCLAW_GATEWAY_URL / OPENCLAW_GATEWAY_TOKEN from the project .env; never prints them.
set -euo pipefail

ENV_FILE="$(cd "$(dirname "$0")/.." && pwd)/.env"
[ -f "$ENV_FILE" ] || { echo "no .env at $ENV_FILE" >&2; exit 2; }

URL="" TOKEN=""
while IFS='=' read -r key value; do
  value="${value%$'\r'}"; value="${value#\"}"; value="${value%\"}"
  case "$key" in
    OPENCLAW_GATEWAY_URL) URL="$value" ;;
    OPENCLAW_GATEWAY_TOKEN) TOKEN="$value" ;;
  esac
done < <(grep -E '^OPENCLAW_GATEWAY_(URL|TOKEN)=' "$ENV_FILE" || true)
[ -n "$URL" ] && [ -n "$TOKEN" ] || { echo "set OPENCLAW_GATEWAY_URL and OPENCLAW_GATEWAY_TOKEN in .env" >&2; exit 2; }

HTTPS="${URL/#wss:/https:}"
COOKIE="$(curl -s -m 30 -o /dev/null -D - -X POST --data-urlencode "token=$TOKEN" --data-urlencode "next=/" \
  "$HTTPS/login" | tr -d '\r' | sed -nE 's/^[Ss]et-[Cc]ookie: (u4s-openclaw-session=[^;]+).*/\1/p' | head -1)"
[ -n "$COOKIE" ] || { echo "Hostinger login gave no session cookie: wrong token, or the access page changed" >&2; exit 2; }

export OPENCLAW_GATEWAY_TOKEN="$TOKEN" HOSTINGER_OPENCLAW_COOKIE="$COOKIE"
unset OPENCLAW_GATEWAY_URL  # an explicit URL would skip the profile's edgeAuth cookie
exec openclaw --profile hotpink "$@"
