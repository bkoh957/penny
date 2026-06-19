#!/usr/bin/env bash
# penny-statusline.sh — render Penny harness state for the Claude Code status line.
# Harness state is read from files under $PENNY_ROOT (default "."); the Claude Code
# session JSON arrives on stdin. Only the first line of stdout becomes the status line.
set -uo pipefail

ROOT="${PENNY_ROOT:-.}"
STAGE_FILE="$ROOT/.penny/current-stage"

# Consume stdin once (the session JSON).
session_json="$(cat)"

# Context-window percentage (design §11). NOTE: confirm this jq path matches the
# live Claude Code status-line JSON schema during execution; adjust if needed.
ctx="$(printf '%s' "$session_json" | jq -r '.context_window.used_percentage // empty' 2>/dev/null)"
if [ -z "${ctx:-}" ]; then
  ctx="?"
else
  ctx="$(printf '%.0f' "$ctx" 2>/dev/null || printf '%s' "$ctx")"
fi

# No harness state yet → idle.
if [ ! -f "$STAGE_FILE" ]; then
  printf 'Penny · idle · ctx %s%%\n' "$ctx"
  exit 0
fi

stage_line="$(head -n1 "$STAGE_FILE")"
book="$(printf '%s' "$stage_line" | sed -n 's/.*book=\([^ ]*\).*/\1/p')"
chapter="$(printf '%s' "$stage_line" | sed -n 's/.*chapter=\([^ ]*\).*/\1/p')"
stage="$(printf '%s' "$stage_line" | sed -n 's/.*stage=\([^ ]*\).*/\1/p')"

# Guard against a malformed / partially-written marker so the line never errors
# or renders garbage. Inputs come from Penny's own commands, but the format is
# still evolving in early phases.
[ -z "$book" ] && book="??"
[ -z "$chapter" ] && chapter=0
[ -z "$stage" ] && stage="?"

# Total chapters from the book outline (## headings); fall back to current chapter.
outline="$ROOT/output/book-$book/outline.md"
if [ -f "$outline" ]; then
  total="$( { grep -c '^## ' "$outline" || true; } | head -n1)"
else
  total="$chapter"
fi
# Strip leading zeros for display (07 -> 7) without arithmetic on bare 0.
chapter_disp="$((10#$chapter))"
[ -z "$total" ] && total=0
total="$((10#$total))"

# Blocking verdicts = lines beginning "BLOCKING:" in the chapter's reviews dir.
reviews="$ROOT/output/book-$book/chapters/ch-$chapter.reviews"
if [ -d "$reviews" ]; then
  blocking="$( { grep -rh '^BLOCKING:' "$reviews" 2>/dev/null || true; } | grep -c '^BLOCKING:' || true)"
  [ -z "${blocking:-}" ] && blocking=0
else
  blocking=0
fi

printf 'Penny · Book %s · Ch %s/%s · %s · gate: %s blocking · ctx %s%%\n' \
  "$book" "$chapter_disp" "$total" "$stage" "$blocking" "$ctx"
