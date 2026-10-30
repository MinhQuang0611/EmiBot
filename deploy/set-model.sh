#!/usr/bin/env bash
# Point agent `emi` at OpenAI or Anthropic, chosen by EMI_LLM_PROVIDER in /data/emi/.env.
# Changes only emi's own model (agents.list[i].model) — never the gateway default that `main` uses.
# Runs on the HOST:
#   /docker/openclaw-lk3h/data/emi/deploy/set-model.sh            # apply
#   /docker/openclaw-lk3h/data/emi/deploy/set-model.sh --dry-run  # validate only, write nothing
#
# In /docker/openclaw-lk3h/data/emi/.env:
#   EMI_LLM_PROVIDER=anthropic        # or openai
#   EMI_LLM_MODEL=                    # optional; empty = default for the provider below
# The API key itself goes in the OpenClaw container env, /docker/openclaw-lk3h/.env:
#   ANTHROPIC_API_KEY=...   or   OPENAI_API_KEY=...
# then `cd /docker/openclaw-lk3h && docker compose up -d` so the gateway sees it.
set -euo pipefail

COMPOSE_DIR="${OPENCLAW_COMPOSE_DIR:-/docker/openclaw-lk3h}"
DATA="${OPENCLAW_DATA:-$COMPOSE_DIR/data}"
EMI_ENV="${EMI_ENV_FILE:-$DATA/emi/.env}"
C="${OPENCLAW_CONTAINER:-openclaw-lk3h-openclaw-1}"
AGENT_ID="${EMI_AGENT_ID:-emi}"
DRY=""; [ "${1:-}" = "--dry-run" ] && DRY="--dry-run"

# Value of KEY in an env file, or empty if absent (never fails, so `set -e` doesn't stop on a missing key).
envval() { { grep -E "^$1=" "$2" 2>/dev/null || true; } | tail -1 | cut -d= -f2- | tr -d '"'"'"' \r'; }

PROVIDER="$(envval EMI_LLM_PROVIDER "$EMI_ENV" | tr 'A-Z' 'a-z')"
MODEL="$(envval EMI_LLM_MODEL "$EMI_ENV")"
case "$PROVIDER" in
  anthropic) KEYVAR=ANTHROPIC_API_KEY; MODEL="${MODEL:-anthropic/claude-sonnet-5-5}" ;;
  openai)    KEYVAR=OPENAI_API_KEY;    MODEL="${MODEL:-openai/gpt-5.6-sol}" ;;
  *) echo "EMI_LLM_PROVIDER in $EMI_ENV must be 'anthropic' or 'openai' (got '${PROVIDER:-empty}')" >&2; exit 2 ;;
esac
case "$MODEL" in "$PROVIDER"/*) ;; *) echo "EMI_LLM_MODEL '$MODEL' does not start with '$PROVIDER/'" >&2; exit 2 ;; esac
echo "provider: $PROVIDER | model: $MODEL | key var: $KEYVAR"

# Key present? Checked by name only; the value is never printed.
if [ -n "$(envval "$KEYVAR" "$COMPOSE_DIR/.env")" ]; then echo "key: set in $COMPOSE_DIR/.env"
else echo "key: MISSING — add $KEYVAR=... to $COMPOSE_DIR/.env" >&2; fi
if docker exec "$C" sh -c "[ -n \"\${$KEYVAR:-}\" ]"; then echo "key: visible to the gateway"
else echo "key: not visible inside $C yet — run: cd $COMPOSE_DIR && docker compose up -d" >&2; fi

# Find emi in agents.list.
LIST="$(docker exec "$C" openclaw config get agents.list --json 2>/dev/null || true)"
IDX="$(printf '%s' "$LIST" | python3 -c '
import json, sys
try:
    agents = json.load(sys.stdin)
except ValueError:
    agents = []
print(next((i for i, a in enumerate(agents) if isinstance(a, dict) and a.get("id") == sys.argv[1]), ""))
' "$AGENT_ID")"

if [ -z "$IDX" ]; then
  echo "agent '$AGENT_ID' not registered yet. Create it with this model:"
  echo "  docker exec $C openclaw agents add $AGENT_ID --workspace /data/.openclaw/workspace-emi --model $MODEL --non-interactive"
  exit 3
fi

docker exec "$C" openclaw config set "agents.list[$IDX].model" "$MODEL" --dry-run >/dev/null
echo "validated agents.list[$IDX].model = $MODEL"
if [ -z "$DRY" ]; then
  docker exec "$C" openclaw config set "agents.list[$IDX].model" "$MODEL"
  echo "applied. Check: docker exec $C openclaw models status --agent $AGENT_ID"
fi
