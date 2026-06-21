from scripts import ledger_markers as lm

CANON = """# Canon Core
<!-- canon-meta: {id: canon-core, fluency_stage: OUTSIDER} -->

## Protagonist fixed facts
<!-- canon-meta: {id: protagonist-fixed, refs: [cora-mistate], active_window: "1-2", last_referenced: null, reconfirmed_at: null, keep_reason: null} -->
- Cora.

## Current timeline position
<!-- canon-meta: {id: current-timeline, refs: [], active_window: "1-13", last_referenced: null, reconfirmed_at: null, keep_reason: null} -->
- Book 01.
"""

BRIEF_REFS = "POV: cora-mistate. Beats: she arrives at the-bluff.\n"
BRIEF_NONE = "POV: thomas. Beats: a stranger appears.\n"


def test_referenced_when_ref_in_brief():
    ids = lm.referenced_section_ids(CANON, BRIEF_REFS, "prose with no ids")
    assert ids == ["protagonist-fixed"]            # current-timeline has empty refs


def test_not_referenced_when_absent():
    assert lm.referenced_section_ids(CANON, BRIEF_NONE, "prose") == []


def test_stamp_writes_chapter_on_referenced_only():
    out = lm.stamp_last_referenced(CANON, 7, BRIEF_REFS, "prose")
    from scripts.penny_meta import parse_canon_sections
    secs = {s["id"]: s for s in parse_canon_sections(out)}
    assert secs["protagonist-fixed"]["last_referenced"] == "7"
    assert secs["current-timeline"]["last_referenced"] == "null"   # untouched


def test_stamp_is_idempotent():
    once = lm.stamp_last_referenced(CANON, 7, BRIEF_REFS, "prose")
    twice = lm.stamp_last_referenced(once, 7, BRIEF_REFS, "prose")
    assert once == twice                            # byte-identical re-application


def test_stamp_leaves_body_bytes_intact():
    out = lm.stamp_last_referenced(CANON, 7, BRIEF_REFS, "prose")
    assert "- Cora." in out and "- Book 01." in out
