import subprocess
import sys
from pathlib import Path

import pytest

from scripts.voice_drift import (
    UnevidencedFlagError,
    _flatten_evidence,
    analyze,
    load_config,
    segment_sentences,
)

REPO = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "cozy"
DEFAULT_CONFIG = FIXTURE / "config/voice-pack/ai-tics-config.yaml"


def test_default_config_has_required_keys():
    cfg = load_config(DEFAULT_CONFIG)
    for key in ("bodily_reaction", "soft_qualifiers", "sentence_variance",
                "lexical_repetition", "banned_phrases", "metaphor_pool"):
        assert key in cfg, f"ai-tics-config.yaml missing {key}"
    assert cfg["bodily_reaction"]["flag_at"] >= 1
    assert isinstance(cfg["metaphor_pool"], list)


def test_missing_config_hard_fails(tmp_path):
    with pytest.raises(SystemExit):
        load_config(tmp_path / "nope.yaml")

FIX = REPO / "tests/fixtures/prose"


def test_segmentation_handles_dialogue_and_abbreviations():
    text = (REPO / "tests/fixtures/prose/dialogue.md").read_text(encoding="utf-8")
    sents = segment_sentences(text)
    # "I'm fine," she said.  -> one sentence (no split at the comma inside quotes)
    assert any("I'm fine" in s and "she said" in s for s in sents)
    # "Mrs. Pennington did not look fine." -> not split at "Mrs."
    assert any(s.strip().startswith("Mrs. Pennington") for s in sents)
    # Ellipsis is non-terminal: the "It's just... a lot" line stays one sentence.
    assert any("just" in s and "a lot" in s for s in sents)


def test_segmentation_handles_curly_smart_quotes():
    # Real prose from Scrivener/Word uses U+201C/U+201D smart quotes, not ASCII ".
    # The interior period must NOT split the dialogue sentence.
    text = "“I know who did it. I saw them.” she said. He nodded."
    sents = segment_sentences(text)
    # The two interior clauses must stay together in one segment.
    assert any("I know who did it" in s and "I saw them" in s for s in sents), (
        "smart-quoted dialogue was split at the interior period (ASCII-only quote bug)"
    )
    # The follow-on sentence must be separate.
    assert any("He nodded" in s for s in sents)


def test_clean_prose_flags_nothing(tmp_path):
    cfg = load_config(DEFAULT_CONFIG)
    result = analyze((FIX / "clean.md").read_text(encoding="utf-8"), cfg)
    flagged = [t for t in result["tics"] if t["flagged"]]
    assert flagged == []
    assert result["blocking"] == []   # evidence-only: never any blocking


def test_tic_saturated_prose_flags_bodily_and_qualifiers(tmp_path):
    cfg = load_config(DEFAULT_CONFIG)
    result = analyze((FIX / "tics.md").read_text(encoding="utf-8"), cfg)
    flagged_ids = {t["tic_id"] for t in result["tics"] if t["flagged"]}
    assert "bodily_reaction" in flagged_ids
    assert "soft_qualifiers" in flagged_ids
    assert result["blocking"] == []   # still no blocking, even when saturated


def test_monotone_prose_flags_low_variance():
    cfg = load_config(DEFAULT_CONFIG)
    result = analyze((FIX / "monotone.md").read_text(encoding="utf-8"), cfg)
    assert result["metrics"]["sentence_stdev"] < cfg["sentence_variance"]["min_stdev"]
    assert any(t["tic_id"] == "sentence_variance" and t["flagged"] for t in result["tics"])


def test_evidence_capped_at_five_per_tic():
    cfg = load_config(DEFAULT_CONFIG)
    result = analyze((FIX / "tics.md").read_text(encoding="utf-8"), cfg)
    bodily = next(t for t in result["tics"] if t["tic_id"] == "bodily_reaction")
    assert len(bodily["evidence_spans"]) <= 5
    assert bodily["count"] >= len(bodily["evidence_spans"])  # count is the full signal


def test_cli_writes_verdict_with_no_blocking_lines(tmp_path):
    chapter = tmp_path / "ch-07.draft.md"
    chapter.write_text((FIX / "tics.md").read_text(encoding="utf-8"), encoding="utf-8")
    # --config is passed explicitly so this test never needs series_root() to
    # resolve a '.penny/' marker at cwd — independent of whether the engine repo
    # itself carries a series marker (it won't, post the engine/series split).
    rc = subprocess.run(
        [sys.executable, str(REPO / "scripts/voice_drift.py"), str(chapter),
         "--out", str(tmp_path), "--target", "book-01/ch-07",
         "--config", str(DEFAULT_CONFIG)],
        cwd=REPO, capture_output=True, text=True,
    )
    assert rc.returncode == 0, rc.stderr
    verdict = (tmp_path / "voice-drift.md").read_text(encoding="utf-8")
    # HARD RULE: voice_drift never emits BLOCKING: lines, even on saturated prose.
    assert not any(ln.startswith("BLOCKING:") for ln in verdict.splitlines())
    assert "producer: voice_drift.py" in verdict


def test_soft_qualifiers_two_in_one_sentence_flags():
    # The cluster rule path: a sentence with >= cluster_in_sentence qualifiers flags.
    cfg = load_config(DEFAULT_CONFIG)
    text = "He walked home. She was almost, somehow, certain of nothing in particular today."
    result = analyze(text, cfg)
    sq = next(t for t in result["tics"] if t["tic_id"] == "soft_qualifiers")
    assert sq["flagged"] is True


def test_cinematic_fragments_counted():
    cfg = load_config(DEFAULT_CONFIG)
    result = analyze((FIX / "fragments.md").read_text(encoding="utf-8"), cfg)
    cf = next(t for t in result["tics"] if t["tic_id"] == "cinematic_fragments")
    assert cf["count"] >= 2          # two runs of short verbless fragments
    assert result["blocking"] == []  # still evidence-only


def test_repeated_openers_flags_on_monotone_prose():
    # lexical_repetition (mixed opener+content-word row) split into two tics
    # (spec 2026-08-27-voice-drift-discards-evidence-fix.md §3b): this is the
    # opener half.
    cfg = load_config(DEFAULT_CONFIG)
    result = analyze((FIX / "monotone.md").read_text(encoding="utf-8"), cfg)
    ro = next(t for t in result["tics"] if t["tic_id"] == "repeated_openers")
    assert ro["flagged"] is True     # "She" opens many sentences
    assert ro["evidence_spans"], "flagged tic must carry evidence (spec §4)"
    assert any("She" in s["span_text"] for s in ro["evidence_spans"])


def test_clean_prose_still_flags_nothing_after_extra_detectors():
    cfg = load_config(DEFAULT_CONFIG)
    result = analyze((FIX / "clean.md").read_text(encoding="utf-8"), cfg)
    assert [t for t in result["tics"] if t["flagged"]] == []


# --- spec 2026-08-27-voice-drift-discards-evidence-fix.md §5 -----------------------

def test_repeated_openers_flags_with_named_evidence_and_line():
    # §5.1: a fixture with 10 sentences all opening "The" flags repeated_openers,
    # and its evidence names "The" with a line number.
    cfg = load_config(DEFAULT_CONFIG)
    text = "\n".join([
        "The cat sat on a mat.",
        "The dog ran down a road.",
        "The bird flew over a wall.",
        "The fish swam in a pond.",
        "The horse walked to a barn.",
        "The mouse crept behind a wall.",
        "The child played by a tree.",
        "The woman read by a window.",
        "The man stood near a door.",
        "The teacher wrote on a board.",
    ])
    result = analyze(text, cfg)
    ro = next(t for t in result["tics"] if t["tic_id"] == "repeated_openers")
    assert ro["flagged"] is True
    assert ro["evidence_spans"]
    named = [s for s in ro["evidence_spans"] if "The" in s["span_text"]]
    assert named, ro["evidence_spans"]
    assert named[0]["line"] == 1   # "The cat sat..." is the file's first line


def test_previously_empty_tics_now_carry_evidence_when_flagged():
    # §5.2: a fixture exercising each of the three formerly-empty-evidence tics
    # (sentence_variance, cinematic_fragments, the two lexical-repetition tics)
    # asserts non-empty evidence when flagged.
    cfg = load_config(DEFAULT_CONFIG)

    monotone = analyze((FIX / "monotone.md").read_text(encoding="utf-8"), cfg)
    sv = next(t for t in monotone["tics"] if t["tic_id"] == "sentence_variance")
    assert sv["flagged"] is True
    assert sv["evidence_spans"]

    ro = next(t for t in monotone["tics"] if t["tic_id"] == "repeated_openers")
    assert ro["flagged"] is True
    assert ro["evidence_spans"]

    frag_result = analyze((FIX / "fragments.md").read_text(encoding="utf-8"), cfg)
    cf = next(t for t in frag_result["tics"] if t["tic_id"] == "cinematic_fragments")
    assert cf["flagged"] is True
    assert cf["evidence_spans"]


def test_no_flagged_tic_has_empty_evidence_across_all_fixtures():
    # §5.3 — the property test that matters, the §4 invariant itself: over every
    # fixture, no tic may be flagged with empty evidence_spans.
    cfg = load_config(DEFAULT_CONFIG)
    checked = 0
    for path in sorted((REPO / "tests/fixtures/prose").glob("*.md")):
        result = analyze(path.read_text(encoding="utf-8"), cfg)
        for t in result["tics"]:
            if t["flagged"]:
                assert t["evidence_spans"], (
                    f"{path.name}: {t['tic_id']} flagged with no evidence_spans"
                )
        checked += 1
    assert checked > 0   # the loop actually ran


def test_compat_shim_old_lexical_repetition_block_still_flags_both_measurements():
    # The fixture config (tests/fixtures/cozy/config/voice-pack/ai-tics-config.yaml)
    # deliberately still carries only the OLD combined `lexical_repetition:` block —
    # this proves an un-migrated series config keeps flagging both measurements via
    # the fallback, rather than silently going dark on both (spec §3b DECISION).
    cfg = load_config(DEFAULT_CONFIG)
    assert "repeated_openers" not in cfg
    assert "repeated_content_words" not in cfg
    result = analyze((FIX / "monotone.md").read_text(encoding="utf-8"), cfg)
    ro = next(t for t in result["tics"] if t["tic_id"] == "repeated_openers")
    rcw = next(t for t in result["tics"] if t["tic_id"] == "repeated_content_words")
    assert ro["threshold"] == cfg["lexical_repetition"]["opener_repeat_flag_at"]
    assert rcw["threshold"] == cfg["lexical_repetition"]["content_word_per_1k_flag_at"]
    assert ro["flagged"] is True


def test_new_config_keys_take_precedence_over_old_block():
    cfg = load_config(DEFAULT_CONFIG)
    cfg["repeated_openers"] = {"flag_at": 1000}          # unreachable threshold
    cfg["repeated_content_words"] = {"flag_at": 1000000}
    result = analyze((FIX / "monotone.md").read_text(encoding="utf-8"), cfg)
    ro = next(t for t in result["tics"] if t["tic_id"] == "repeated_openers")
    rcw = next(t for t in result["tics"] if t["tic_id"] == "repeated_content_words")
    assert ro["threshold"] == 1000
    assert rcw["threshold"] == 1000000
    assert ro["flagged"] is False    # new key wins even though old block would flag


def test_flagged_tic_with_no_evidence_raises():
    # §5's invariant test, aimed at the guard itself rather than a fixture that
    # happens to satisfy it: a hand-built violating tic list must raise.
    bad_tics = [{"tic_id": "x", "flagged": True, "evidence_spans": []}]
    with pytest.raises(UnevidencedFlagError):
        _flatten_evidence(bad_tics)


def test_unflagged_tic_with_no_evidence_does_not_raise():
    # The invariant applies only to flags (spec §4, last line).
    ok_tics = [{"tic_id": "x", "flagged": False, "evidence_spans": []}]
    assert _flatten_evidence(ok_tics) == []


# --- spec 2026-08-27-voice-drift-discards-evidence-fix.md — review fixes -----------
# Fix 1 (Critical): flag_at == 0 (or negative) must never flag on zero actual
# matches. The generic add() guard, the metaphor_pool guard, and both split
# lexical-repetition guards all need `count > 0` alongside the density/threshold
# comparison, or an empty-evidence flag reaches the §4 invariant and crashes.

def test_threshold_zero_does_not_flag_generic_tic_with_zero_matches():
    # The exact reproduction from review: a threshold of 0 on a tic with no
    # matches must not flag, and must not raise once flattened for the verdict.
    result = analyze("Hello there world today. Another line goes here now.\n",
                      {"bodily_reaction": {"flag_at": 0}})
    br = next(t for t in result["tics"] if t["tic_id"] == "bodily_reaction")
    assert br["count"] == 0
    assert br["flagged"] is False
    assert br["evidence_spans"] == []
    _flatten_evidence(result["tics"])  # must not raise


def test_negative_threshold_does_not_flag_generic_tic_with_zero_matches():
    result = analyze("Hello there world today. Another line goes here now.\n",
                      {"bodily_reaction": {"flag_at": -1}})
    br = next(t for t in result["tics"] if t["tic_id"] == "bodily_reaction")
    assert br["flagged"] is False
    assert br["evidence_spans"] == []
    _flatten_evidence(result["tics"])


def test_threshold_zero_does_not_flag_metaphor_pool_with_zero_matches():
    result = analyze("Hello there world today.",
                      {"metaphor_pool_rule": {"total_flag_at": 0}, "metaphor_pool": ["wave"]})
    pool = next(t for t in result["tics"] if t["tic_id"] == "metaphor_pool")
    assert pool["flagged"] is False
    assert pool["evidence_spans"] == []
    _flatten_evidence(result["tics"])


def test_threshold_zero_does_not_flag_repeated_openers_with_zero_sentences():
    result = analyze("", {"repeated_openers": {"flag_at": 0}})
    ro = next(t for t in result["tics"] if t["tic_id"] == "repeated_openers")
    assert ro["flagged"] is False
    assert ro["evidence_spans"] == []
    _flatten_evidence(result["tics"])


def test_negative_threshold_does_not_flag_repeated_openers_with_zero_sentences():
    result = analyze("", {"repeated_openers": {"flag_at": -1}})
    ro = next(t for t in result["tics"] if t["tic_id"] == "repeated_openers")
    assert ro["flagged"] is False
    _flatten_evidence(result["tics"])


def test_threshold_zero_does_not_flag_repeated_content_words_with_zero_matches():
    result = analyze("", {"repeated_content_words": {"flag_at": 0}})
    rcw = next(t for t in result["tics"] if t["tic_id"] == "repeated_content_words")
    assert rcw["flagged"] is False
    assert rcw["evidence_spans"] == []
    _flatten_evidence(result["tics"])


def test_negative_threshold_does_not_flag_repeated_content_words_with_zero_matches():
    result = analyze("", {"repeated_content_words": {"flag_at": -1}})
    rcw = next(t for t in result["tics"] if t["tic_id"] == "repeated_content_words")
    assert rcw["flagged"] is False
    _flatten_evidence(result["tics"])


# --- Fix 2 (Important): evidence line numbers must skip markdown headings ---------
# The spec's own flagship case: a chapter title containing the top-repeated word
# must never win the "first occurrence" search over the word's real first
# sentence-opening/prose line.

TITLE_FIXTURE = "\n".join([
    "# Chapter 01 — The Life She Bought",
    "",
    "Cora walked to the shop early that morning without a coat.",
    "It was raining hard outside now and everyone hurried past.",
    "The dog barked twice at noon near the fence line loudly.",
    "The cat meowed loudly again from the windowsill above the door.",
    "The bird sang softly at dawn before the sun rose over hills.",
    "She counted the coins slowly in her palm by the counter.",
    "She frowned at the total and counted them again twice more.",
    "She sighed and pocketed the coins before turning to leave now.",
    "Her life had never felt so complicated as it did this morning.",
    "The strange life she led was full of secrets and small lies.",
]) + "\n"


def test_opener_evidence_line_skips_markdown_title():
    cfg = load_config(DEFAULT_CONFIG)
    result = analyze(TITLE_FIXTURE, cfg)
    ro = next(t for t in result["tics"] if t["tic_id"] == "repeated_openers")
    assert ro["flagged"] is True
    the_evidence = next(s for s in ro["evidence_spans"] if '"The"' in s["span_text"])
    assert the_evidence["line"] == 5, the_evidence   # first sentence opening "The"
    assert the_evidence["line"] != 1                 # never the title line


def test_content_word_evidence_line_skips_markdown_title():
    cfg = load_config(DEFAULT_CONFIG)
    result = analyze(TITLE_FIXTURE, cfg)
    rcw = next(t for t in result["tics"] if t["tic_id"] == "repeated_content_words")
    life_evidence = next((s for s in rcw["evidence_spans"] if '"life"' in s["span_text"]), None)
    assert life_evidence is not None, rcw["evidence_spans"]
    assert life_evidence["line"] == 11   # first prose occurrence, not the title
    assert life_evidence["line"] != 1


# --- Fix 3 (Minor): drop singletons, but never at the cost of the §4 invariant ----

def test_singleton_opener_not_in_evidence():
    cfg = load_config(DEFAULT_CONFIG)
    result = analyze(TITLE_FIXTURE, cfg)
    ro = next(t for t in result["tics"] if t["tic_id"] == "repeated_openers")
    for w in ('"Cora"', '"It"', '"Her"'):   # each opens exactly one sentence
        assert not any(w in s["span_text"] for s in ro["evidence_spans"])


def test_singleton_content_word_not_in_evidence():
    # No repeated word: every distinct content word occurs exactly once, so a
    # naive most_common()[:5] (pre-fix) fills evidence entirely with count-1
    # entries — the spec's own "cora" ×1 example.
    cfg = load_config(DEFAULT_CONFIG)
    text = ("Cora opened the window slowly. Sunlight touched the curtains again. "
            "Dust drifted through empty air quietly.")
    result = analyze(text, cfg)
    rcw = next(t for t in result["tics"] if t["tic_id"] == "repeated_content_words")
    assert not any(s["span_text"].endswith("×1") for s in rcw["evidence_spans"])
    ro = next(t for t in result["tics"] if t["tic_id"] == "repeated_openers")
    assert not any(s["span_text"].endswith("×1") for s in ro["evidence_spans"])


def test_flag_at_one_with_singleton_top_opener_still_has_evidence():
    # The interaction the review flagged explicitly: Fix 1's positive-count
    # guard and Fix 3's singleton filter must not combine to leave a flagged
    # tic with empty evidence_spans. flag_at == 1 makes a single occurrence
    # itself "at threshold".
    cfg = {"repeated_openers": {"flag_at": 1}}
    text = "Cora walked to the shop today near the wall."   # one sentence, opener count 1
    result = analyze(text, cfg)
    ro = next(t for t in result["tics"] if t["tic_id"] == "repeated_openers")
    assert ro["flagged"] is True
    assert ro["evidence_spans"], "flagged tic must never have empty evidence (§4)"
    _flatten_evidence(result["tics"])   # must not raise


def test_content_word_negative_threshold_singleton_top_word_still_has_evidence():
    # Same interaction, on the content-word side: top_cw_count == 1 forces
    # density to 0.0 (existing suppression), which a negative threshold still
    # clears — flagged True on a singleton, so the fallback must supply
    # evidence rather than let Fix 3's filter leave it empty.
    cfg = {"repeated_content_words": {"flag_at": -1}}
    text = "Cora walked toward the distant harbor slowly today morning."
    result = analyze(text, cfg)
    rcw = next(t for t in result["tics"] if t["tic_id"] == "repeated_content_words")
    assert rcw["flagged"] is True
    assert rcw["evidence_spans"], "flagged tic must never have empty evidence (§4)"
    _flatten_evidence(result["tics"])   # must not raise
