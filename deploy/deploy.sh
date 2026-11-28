#!/usr/bin/env bash
# deploy.sh — one command to put the latest push of deploy-openclaw live on hotpink-bee (2026-11-28, same idea as
# Sunny's tools/deploy.sh). Run in the hPanel terminal:
#     bash /data/emi/deploy/deploy.sh            # pull + copy what Emi reads + send-blocked check
#     bash /data/emi/deploy/deploy.sh --tests    # same + the full unit suite (needed when Python changed)
# Steps, as the dev does them by hand (memory/2026-11-2x "deployed on hotpink-bee"):
#   1. tracked files in /data/emi must be clean (else stop: DIRTY);
#   2. git pull --ff-only, the new commits listed;
#   3. the files Emi reads are copied into the workspace only when they differ — SOUL / IDENTITY / USER / AGENTS /
#      schedule.md, skills/, docs/rate-knowledge/ — the old copy kept in /data/emi-ws-backup-<stamp>/, each file
#      printed CHANGED / NEW / REMOVED with its md5; MEMORY.md and memory/ are Emi's own notes: seeded once, never
#      overwritten (as deploy/sync-workspace.sh); no rsync / chown / rm on this host (removed files are moved);
#   4. DEPLOYED_VERSION written;
#   5. `tools.acceptance send-blocked` (every send endpoint refused) — and with --tests the unit suite, its log in
#      /data/emi-logs/test-<commit>.txt. If Python can't run from this terminal, the step says SKIPPED: run it from
#      Emi's chat; the files are already copied.
# Exit: 0 ok, 2 pull failed, 3 repo / workspace missing, 5 dirty checkout, 6 send-blocked or tests FAILED.
# Env (tests on a dev machine): EMI_REPO, EMI_WS, EMI_BACKUP_ROOT, EMI_LOGS, EMI_NO_PULL=1.
# The body is one function, so bash has read all of it before `git pull` replaces this file.
main() {
  set -uo pipefail
  local REPO WS BKROOT LOGS STAMP BK OLD NEW out f rel src dst a b n_changed=0 n_new=0 n_removed=0 n_same=0 rc=0 tests=0 py
  [ "${1:-}" = "--tests" ] && tests=1
  REPO="${EMI_REPO:-$(cd "$(dirname "$0")/.." && pwd)}"
  WS="${EMI_WS:-/data/.openclaw/workspace-emi}"
  BKROOT="${EMI_BACKUP_ROOT:-/data}"
  LOGS="${EMI_LOGS:-/data/emi-logs}"
  [ -d "$REPO/.git" ] || { echo "REPO_MISSING: $REPO is not the EmiBot checkout"; return 3; }
  [ -d "$WS" ] || { echo "WORKSPACE_MISSING: $WS"; return 3; }

  out="$(git -C "$REPO" status --porcelain --untracked-files=no)"
  if [ -n "$out" ]; then
    echo "DIRTY: file đang sửa dở trong $REPO — dừng, hỏi dev trước khi pull:"; printf '%s\n' "$out" | sed 's/^/  /'
    return 5
  fi

  OLD="$(git -C "$REPO" rev-parse HEAD)"
  if [ "${EMI_NO_PULL:-}" != "1" ]; then
    if ! out="$(git -C "$REPO" pull --ff-only 2>&1)"; then
      echo "PULL_FAILED: $(printf '%s\n' "$out" | tail -n 3 | tr '\n' ' ')"; return 2
    fi
  fi
  NEW="$(git -C "$REPO" rev-parse HEAD)"
  if [ "$OLD" = "$NEW" ]; then
    echo "GIT: không có commit mới (đang ở $(git -C "$REPO" log --oneline -1 | cut -c1-100)); vẫn kiểm tra lại các file"
  else
    echo "GIT: các commit mới:"
    git -C "$REPO" log --oneline "$OLD..$NEW" | cut -c1-140 | sed 's/^/  /'
  fi

  STAMP="$(TZ=Asia/Ho_Chi_Minh date '+%Y%m%d-%H%M%S')"
  BK="$BKROOT/emi-ws-backup-$STAMP"
  keep() {  # move / copy the workspace's current copy of $1 into the backup folder
    mkdir -p "$BK/$(dirname "$1")" && cp -p "$WS/$1" "$BK/$1"
  }
  copy_one() {  # $1 = path relative to the repo and the workspace
    src="$REPO/$1"; dst="$WS/$1"
    a="$(md5sum < "$src" | cut -d' ' -f1)"
    if [ -f "$dst" ]; then
      b="$(md5sum < "$dst" | cut -d' ' -f1)"
      if [ "$a" = "$b" ]; then n_same=$((n_same + 1)); return; fi
      keep "$1" && cp "$src" "$dst" && { echo "CHANGED  $1  $a"; n_changed=$((n_changed + 1)); } || { echo "COPY_FAILED  $1"; rc=3; }
    else
      mkdir -p "$(dirname "$dst")" && cp "$src" "$dst" && { echo "NEW      $1  $a"; n_new=$((n_new + 1)); } || { echo "COPY_FAILED  $1"; rc=3; }
    fi
  }
  for f in SOUL.md IDENTITY.md USER.md AGENTS.md schedule.md; do
    [ -f "$REPO/$f" ] && copy_one "$f"
  done
  for d in skills docs/rate-knowledge; do
    [ -d "$REPO/$d" ] || continue
    while IFS= read -r rel; do copy_one "$rel"; done < <(cd "$REPO" && find "$d" -type f ! -name '*.pyc' | sort)
    # files gone from the repo (what rsync --delete did): moved to the backup, never deleted
    [ -d "$WS/$d" ] || continue
    while IFS= read -r rel; do
      if [ ! -f "$REPO/$rel" ]; then
        mkdir -p "$BK/$(dirname "$rel")" && mv "$WS/$rel" "$BK/$rel" && { echo "REMOVED  $rel  (cất vào $BK)"; n_removed=$((n_removed + 1)); }
      fi
    done < <(cd "$WS" && find "$d" -type f | sort)
  done
  [ -f "$WS/MEMORY.md" ] || { cp "$REPO/MEMORY.md" "$WS/MEMORY.md" && echo "NEW      MEMORY.md (lần đầu; sau đó không bao giờ ghi đè)"; }
  mkdir -p "$WS/memory"

  {
    echo "commit: $(git -C "$REPO" rev-parse --short HEAD)"
    echo "subject: $(git -C "$REPO" log -1 --format=%s | cut -c1-200)"
    echo "synced_at: $(TZ=Asia/Ho_Chi_Minh date '+%Y-%m-%d %H:%M %Z')"
    echo "synced_by: deploy/deploy.sh"
  } > "$WS/DEPLOYED_VERSION"
  echo "SUMMARY: $n_changed changed, $n_new new, $n_removed removed, $n_same same$( [ -d "$BK" ] && echo "; old copies in $BK")"
  echo "DEPLOYED_VERSION: $(git -C "$REPO" rev-parse --short HEAD)"

  py="$REPO/.venv/bin/python"
  # the hPanel terminal (lshell) may refuse Python even from a script: a failed `print(1)` = SKIPPED, not FAILED
  if [ -x "$py" ] && ! "$py" -c 'print(1)' >/dev/null 2>&1; then py="$py (không chạy được từ terminal này)"; fi
  if [ ! -x "$py" ]; then
    echo "SEND_BLOCKED: SKIPPED (không có $py) — chạy \`.venv/bin/python -m tools.acceptance send-blocked\` qua chat của Emi"
  elif out="$(cd "$REPO" && "$py" -m tools.acceptance send-blocked 2>&1)"; then
    echo "SEND_BLOCKED: $(printf '%s\n' "$out" | tail -n 1)"
  else
    echo "SEND_BLOCKED: FAILED — $(printf '%s\n' "$out" | tail -n 3 | tr '\n' ' ')"; rc=6
  fi
  if [ "$tests" = 1 ]; then
    mkdir -p "$LOGS"
    local log="$LOGS/test-$(git -C "$REPO" rev-parse --short HEAD).txt"
    if [ ! -x "$py" ]; then
      echo "TESTS: SKIPPED (không có $py) — chạy bộ test qua chat của Emi"
    elif (cd "$REPO" && "$py" -m unittest discover -s tools/tests -t .) > "$log" 2>&1; then
      echo "TESTS: $(grep -E '^Ran [0-9]+ tests' "$log" | tail -n 1) — $(tail -n 1 "$log") (log $log)"
    else
      echo "TESTS: FAILED — $(grep -E '^Ran [0-9]+ tests' "$log" | tail -n 1); $(tail -n 1 "$log") (log $log)"; rc=6
    fi
  fi
  [ "$rc" = 0 ] && echo "✅ Xong. Lượt chạy tới của Emi đọc file mới (không cần khởi động lại)."
  return "$rc"
}
main "$@"; exit $?
