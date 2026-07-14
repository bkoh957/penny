import re
from pathlib import Path

from scripts.penny_wiring import parse_wired_chapters

REPO = Path(__file__).resolve().parents[1]
CMD = REPO / "commands" / "build-briefs.md"
AGENT = REPO / "agents" / "brief-weigher.md"


def test_command_exists_and_runs_after_the_lock():
    text = CMD.read_text(encoding="utf-8")
    assert "lock" in text.lower()
    assert "brief_render.py" in text


def test_command_shells_out_through_the_plugin_root():
    # runbooks must resolve scripts regardless of which series folder is cwd
    assert "${CLAUDE_PLUGIN_ROOT}/scripts/brief_render.py" in CMD.read_text(encoding="utf-8")


def test_weigher_proposes_and_never_decides():
    text = AGENT.read_text(encoding="utf-8").lower()
    assert "propose" in text
    assert "never writes" in text or "does not write" in text


def test_documented_weight_syntax_actually_parses():
    # A substring check ("Weight" in text) sailed a wrong syntax through once
    # already: the runbook can name the field correctly while teaching a form
    # the parser rejects. This is a real contract test: extract the exact
    # Weight-field syntax the runbook documents (Notes section) and feed it,
    # verbatim, through the real parser inside a minimal chapter block. If the
    # runbook ever drifts from what penny_wiring accepts, this must fail —
    # not just say "Weight" appeared somewhere in the file.
    text = CMD.read_text(encoding="utf-8")
    m = re.search(r"`(-\s*\*\*Weight:\*\*\s*)anchor\|support\|connective`", text)
    assert m, "runbook must document the '- **Weight:** anchor|support|connective' syntax"
    documented_prefix = m.group(1)  # e.g. "- **Weight:** "

    block = f"""---
book: 01
total_chapters: 1
---

## Chapter 01 — One

### Scene 1 — Test

{documented_prefix}anchor

**Beat flow:**

1. Beat.
"""
    chapters = parse_wired_chapters(block)
    assert chapters[0]["scenes"][0]["weight"] == "anchor", (
        "the syntax build-briefs.md teaches must be syntax penny_wiring.parse_wired_chapters "
        "accepts — it silently produced weight=None instead"
    )
