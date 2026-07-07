#!/usr/bin/env bash
# penny-statusline.sh — render Penny harness state for the Claude Code status line.
# Harness state is resolved from the current directory's series via penny_paths
# (design: engine-plugin + series-folders); $PENNY_ROOT (default ".") is only the
# idle fallback for when cwd isn't inside a series. The Claude Code session JSON
# arrives on stdin. Only the first line of stdout becomes the status line.
set -uo pipefail

ROOT="${PENNY_ROOT:-.}"
# Resolve the active series' state via the penny_paths CLI shim rather than
# assuming $ROOT is the series root (design: engine-plugin + series-folders).
# Both calls degrade to empty output (never error/hang) when cwd isn't inside
# a series, so the status line still renders an idle segment.
STAGE_FILE="$(python3 -m scripts.penny_paths resolve penny current-stage 2>/dev/null)"
SERIES="$(python3 -m scripts.penny_paths active 2>/dev/null)"
series_prefix=""
[ -n "${SERIES:-}" ] && series_prefix="[$SERIES] "
# When inside a series, anchor ROOT on that same series so outline/reviews below
# resolve coherently with STAGE_FILE (not to a divergent $PENNY_ROOT). STAGE_FILE
# is `<series>/.penny/current-stage`, so dirname-of-dirname is the series root.
# Idle/outside-a-series (empty STAGE_FILE) keeps the $PENNY_ROOT fallback.
if [ -n "$STAGE_FILE" ]; then ROOT="$(dirname "$(dirname "$STAGE_FILE")")"; fi

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

# Append ccstatusline's output (the global status line) on a second line, feeding
# it the same session JSON on stdin. Best-effort: if ccstatusline isn't available,
# we silently fall back to the Penny segment alone.
append_ccstatusline() {
  local penny="$1" cc
  # Non-interactive contexts (tests, CI) can skip the nondeterministic, network
  # ccstatusline call by setting PENNY_NO_CCSTATUSLINE; the Penny segment alone is
  # then emitted, keeping output deterministic.
  if [ -n "${PENNY_NO_CCSTATUSLINE:-}" ]; then
    printf '%s\n' "$penny"
    return 0
  fi
  cc="$(printf '%s' "$session_json" | npx -y ccstatusline@latest 2>/dev/null | head -n1)"
  if [ -n "${cc:-}" ]; then
    printf '%s\n%s\n' "$penny" "$cc"
  else
    printf '%s\n' "$penny"
  fi
}

# No harness state yet → idle.
if [ ! -f "$STAGE_FILE" ]; then
  append_ccstatusline "$(printf '%sPenny · idle · ctx %s%%' "$series_prefix" "$ctx")"
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

# Total chapters from the book outline (numbered "## Chapter NN" headings only,
# so non-chapter sections like "## Solution", "## Threads", "## Chapter Engine
# Used Throughout" and the Act/Track headers are not miscounted); fall back to
# current chapter.
outline="$ROOT/input/book-$book/outline.md"
if [ -f "$outline" ]; then
  total="$( { grep -c '^## Chapter [0-9]' "$outline" || true; } | head -n1)"
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

append_ccstatusline "$(printf '%sPenny · Book %s · Ch %s/%s · %s · gate: %s blocking · ctx %s%%' \
  "$series_prefix" "$book" "$chapter_disp" "$total" "$stage" "$blocking" "$ctx")"
