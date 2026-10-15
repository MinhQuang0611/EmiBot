#!/usr/bin/env bash
# Run an OpenClaw CLI command against the hotpink-bee Gateway from the dev machine.
# Reads only OPENCLAW_GATEWAY_URL / _TOKEN / _PASSWORD from the project .env (never printed).
#   deploy/emi-remote.sh agents list
#   deploy/emi-remote.sh agent --agent emi -m "Chạy job 1 theo schedule.md"
set -euo pipefail

ENV_FILE="$(cd "$(dirname "$0")/.." && pwd)/.env"
[ -f "$ENV_FILE" ] || { echo "no .env at $ENV_FILE" >&2; exit 2; }

while IFS='=' read -r key value; do
  case "$key" in
    OPENCLAW_GATEWAY_URL|OPENCLAW_GATEWAY_TOKEN|OPENCLAW_GATEWAY_PASSWORD)
      value="${value%$'\r'}"; value="${value#\"}"; value="${value%\"}"
      [ -n "$value" ] && export "$key=$value" ;;
  esac
done < <(grep -E '^OPENCLAW_GATEWAY_(URL|TOKEN|PASSWORD)=' "$ENV_FILE" || true)

[ -n "${OPENCLAW_GATEWAY_URL:-}" ] || { echo "OPENCLAW_GATEWAY_URL is not set in .env" >&2; exit 2; }
[ -n "${OPENCLAW_GATEWAY_TOKEN:-}${OPENCLAW_GATEWAY_PASSWORD:-}" ] || {
  echo "set OPENCLAW_GATEWAY_TOKEN (or OPENCLAW_GATEWAY_PASSWORD) in .env" >&2; exit 2; }

exec openclaw "$@"
