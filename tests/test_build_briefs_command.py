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


# --- FINAL REVIEW I4: the runbook's stated order must be TRUE. Weights are
# authored only here, `overloaded-chapter` only runs inside `lock-mystery`, and
# the old runbook hard-refused an unlocked book — so the check could never see a
# weight, and the runbook was telling the showrunner to edit a SEALED outline
# (CLAUDE.md: a lock is "frozen against edits") while the certificate went on
# claiming tension validation the weighted outline never received.

def test_runbook_weighs_before_the_lock_and_compiles_after():
    text = CMD.read_text(encoding="utf-8")
    assert "before the lock" in text
    assert "after the lock" in text
    # weigh comes before compile, and the compile step is the one that needs the lock
    assert text.index("3. **Weigh the scenes") < text.index("5. **Compile**")


def test_runbook_tells_the_showrunner_to_re_mint_a_lock_that_predates_the_weights():
    text = CMD.read_text(encoding="utf-8")
    assert "lock-mystery" in text
    assert 'rm ".penny/locks/book-$book.mystery.lock"' in text, (
        "adding weights to an already-locked book must re-mint the certificate — "
        "delete + re-run, the documented re-planning flow")


def test_runbook_no_longer_hard_refuses_an_unlocked_book():
    text = CMD.read_text(encoding="utf-8")
    assert "is not locked — the obligations are not settled yet" not in text, (
        "weighing needs only the outline and the length profile; refusing an "
        "unlocked book is what made overloaded-chapter unreachable")


def test_runbook_says_a_compact_chapter_is_skipped_not_failed():
    text = CMD.read_text(encoding="utf-8").lower()
    assert "compact" in text
    assert "skips it by name" in text or "skipped" in text
