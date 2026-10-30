#!/usr/bin/env bash
# Copy Emi's persona, skills and knowledge from the git checkout into the OpenClaw agent workspace.
# Run on the HOST after every `git pull` (the container has no git or rsync).
# Never copies secrets, test data or Claude Code files.
# Host /docker/openclaw-lk3h/data is /data inside the OpenClaw container.
set -euo pipefail

DATA="${OPENCLAW_DATA:-/docker/openclaw-lk3h/data}"
REPO="${EMI_REPO_HOST:-$DATA/emi}"
WS="${EMI_WORKSPACE_HOST:-$DATA/.openclaw/workspace-emi}"

[ -d "$REPO/.git" ] || { echo "no git checkout at $REPO" >&2; exit 2; }
mkdir -p "$WS/skills" "$WS/docs" "$WS/memory"

# Persona and rules. MEMORY.md and memory/ are Emi's own notes: seed them once, never overwrite,
# so what Emi learns on the host isn't wiped by a deploy.
for f in SOUL.md IDENTITY.md USER.md AGENTS.md schedule.md; do
  cp "$REPO/$f" "$WS/$f"
done
[ -f "$WS/MEMORY.md" ] || cp "$REPO/MEMORY.md" "$WS/MEMORY.md"

rsync -a --delete "$REPO/skills/" "$WS/skills/"
rsync -a --delete "$REPO/docs/rate-knowledge/" "$WS/docs/rate-knowledge/"

# Which commit is live, for `deploy/status.sh` and for Emi to quote if asked.
{
  echo "commit: $(git -C "$REPO" rev-parse --short HEAD)"
  echo "subject: $(git -C "$REPO" log -1 --format=%s)"
  echo "synced_at: $(TZ=Asia/Ho_Chi_Minh date '+%Y-%m-%d %H:%M %Z')"
  if [ -n "$(git -C "$REPO" status --porcelain --untracked-files=no)" ]; then echo "WARNING: uncommitted changes on host"; fi
} > "$WS/DEPLOYED_VERSION"

# Files under /data belong to uid 1000, like the rest of the OpenClaw data dir.
chown -R 1000:1000 "$WS"

echo "synced $(git -C "$REPO" rev-parse --short HEAD) -> $WS"
