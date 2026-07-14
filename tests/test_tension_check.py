from pathlib import Path

from scripts.tension_check import check_tension

FIX = Path("tests/fixtures/outlines")


def _predicates(result):
    return {b.split(":", 1)[0] for b in result["blocking"]}


def test_clean_wired_outline_has_no_findings():
    r = check_tension(FIX / "wired-clean.md")
    assert r["wired"] is True and r["blocking"] == []


def test_unwired_outline_is_skipped():
    r = check_tension(FIX / "well-formed.md")
    assert r["wired"] is False and r["blocking"] == []


def test_orphan_chapter():
    assert "orphan-chapter" in _predicates(check_tension(FIX / "wired-orphan.md"))


def test_dropped_question():
    assert "dropped-question" in _predicates(check_tension(FIX / "wired-dropped-question.md"))


def test_phantom_answer():
    assert "phantom-answer" in _predicates(check_tension(FIX / "wired-phantom-answer.md"))


def test_broken_hook_on_already_closed_question():
    assert "broken-hook" in _predicates(check_tension(FIX / "wired-broken-hook.md"))


def test_carried_question_stays_hookable():
    # wired-clean ch 06 carries q-elspeth-vale and hooks it: must NOT be broken-hook.
    r = check_tension(FIX / "wired-clean.md")
    assert not any(b.startswith("broken-hook") for b in r["blocking"])


BEATS = Path("tests/fixtures/plot/beat-sheet.yaml")
WHOD = Path("tests/fixtures/plot/whodunit-mini.yaml")


def test_dead_stretch_fires_before_reveal_proxy():
    r = check_tension(FIX / "wired-dead-stretch.md", beat_sheet_path=BEATS)
    assert "dead-stretch" in _predicates(r)


def test_starved_thread_fires_past_max_dark_gap():
    r = check_tension(FIX / "wired-starved-thread.md", beat_sheet_path=BEATS)
    assert "starved-thread" in _predicates(r)


def test_clean_outline_survives_curve_checks_with_real_reveal():
    r = check_tension(FIX / "wired-clean.md", beat_sheet_path=BEATS, whodunit_path=WHOD)
    assert r["blocking"] == []


def test_curve_checks_skipped_without_beat_sheet():
    r = check_tension(FIX / "wired-starved-thread.md")
    assert "starved-thread" not in _predicates(r)


def test_carried_question_stays_open_for_dead_stretch_count():
    # wired-carry-midbook: ch 02 carries q-a (opened ch 01) and opens nothing
    # new. If carries were wrongly subtracted from the open-question count
    # (like closes), ch 02's open count would drop to 0 — below
    # min_open_before_reveal (1) and before the reveal (ch 05) — and
    # dead-stretch would fire. A carried question must stay OPEN, so the
    # clean outline must survive with zero blocking findings.
    r = check_tension(FIX / "wired-carry-midbook.md", beat_sheet_path=BEATS, whodunit_path=WHOD)
    assert r["blocking"] == []
    assert r["metrics"]["open_counts"][2] == 1


from scripts.tension_check import main as tension_main

TP_GOOD = Path("tests/fixtures/plot/turning-points-good.md")
TP_BAD = Path("tests/fixtures/plot/turning-points-offmark.md")


def test_off_mark_beat_fires():
    r = check_tension(FIX / "wired-clean.md", beat_sheet_path=BEATS,
                      turning_points_path=TP_BAD, whodunit_path=WHOD)
    assert "off-mark-beat" in _predicates(r)


def test_on_mark_beats_pass():
    r = check_tension(FIX / "wired-clean.md", beat_sheet_path=BEATS,
                      turning_points_path=TP_GOOD, whodunit_path=WHOD)
    assert r["blocking"] == []


def test_reveal_beat_checked_against_whodunit(tmp_path):
    bad_whod = Path("tests/fixtures/plot/whodunit-mini.yaml")  # reveal 5
    # TP_GOOD places reveal at 5 → clean; re-point at ch 4 via off-mark fixture logic:
    text = TP_GOOD.read_text(encoding="utf-8").replace(
        "## TP-4 — The kitchen truth\n- **Beat:** reveal\n- **Chapter:** 5",
        "## TP-4 — The kitchen truth\n- **Beat:** reveal\n- **Chapter:** 4")
    tp_path = tmp_path / "turning-points-reveal-mismatch.md"
    tp_path.write_text(text, encoding="utf-8")
    r = check_tension(FIX / "wired-clean.md", beat_sheet_path=BEATS,
                      turning_points_path=tp_path, whodunit_path=bad_whod)
    assert "off-mark-beat" in _predicates(r)


def test_cli_exit_codes(capsys):
    assert tension_main([str(FIX / "wired-clean.md"), "--beat-sheet", str(BEATS),
                         "--whodunit", str(WHOD)]) == 0
    assert tension_main([str(FIX / "wired-orphan.md")]) == 1
    assert "orphan-chapter" in capsys.readouterr().out


def test_cli_unwired_skips_exit_zero(capsys):
    assert tension_main([str(FIX / "well-formed.md")]) == 0
    assert "no wiring" in capsys.readouterr().out


# --- FINAL REVIEW FINDING 2: chapter-coverage — the chapters-stage failure
# mode (N separate chapter-weaver dispatches, one per turning-point gap) is
# gaps/dupes at the seams; nothing compared the chapter set to total_chapters.

def test_chapter_coverage_fires_on_gap():
    r = check_tension(FIX / "wired-chapter-gap.md")
    assert _predicates(r) == {"chapter-coverage"}


def test_chapter_coverage_fires_on_total_chapters_mismatch(tmp_path):
    # The finding's own reproduction: total_chapters declares more than the
    # skeleton actually has (chapters 1-22 of a declared 24).
    text = (FIX / "wired-clean.md").read_text(encoding="utf-8").replace(
        "total_chapters: 6", "total_chapters: 8")
    p = tmp_path / "outline.md"
    p.write_text(text, encoding="utf-8")
    assert "chapter-coverage" in _predicates(check_tension(p))


def test_chapter_coverage_quiet_on_clean_outline():
    r = check_tension(FIX / "wired-clean.md")
    assert "chapter-coverage" not in _predicates(r)


def test_chapter_coverage_waivable_like_every_other_check(tmp_path):
    # Waivability is automatic via the check-id prefix convention
    # (preflight._parse_waivers / cmd_lock_mystery splits on the first ":").
    r = check_tension(FIX / "wired-chapter-gap.md")
    assert all(f.split(":", 1)[0] == "chapter-coverage" for f in r["blocking"])


# --- FINAL REVIEW FINDING 4: starved-thread must fail CLOSED on a MISSING
# Track Movement row, not silently count it as advancing. -------------------

def test_starved_thread_fires_on_missing_track_rows():
    r = check_tension(FIX / "wired-starved-thread-missing-rows.md", beat_sheet_path=BEATS)
    assert "starved-thread" in _predicates(r)


def test_starved_thread_fires_when_track_movement_section_entirely_absent(tmp_path):
    # A chapter with NO track rows at all (not even the ones that DO advance)
    # must still be caught — the original bug was `dark` only True when the
    # row exists AND starts with "none", so an absent row read as advancing.
    text = """---
book: 01
total_chapters: 3
---

## Chapter 01 — One

### Chapter Structure
- **Hook:** q-a — first?
- **Because:** opening
- **Opens:** q-a — first?

## Chapter 02 — Two

### Chapter Structure
- **Hook:** q-a — still?
- **Because:** ch 01 — follows.

## Chapter 03 — Three

### Chapter Structure
- **Hook:** q-a — still?
- **Because:** ch 02 — follows.
- **Closes:** q-a
"""
    p = tmp_path / "outline.md"
    p.write_text(text, encoding="utf-8")
    r = check_tension(p, beat_sheet_path=BEATS)
    assert "starved-thread" in _predicates(r)


def test_starved_thread_still_quiet_when_rows_present_and_advancing():
    # Regression guard: the fix must not make every track look starved —
    # wired-clean's chapters all carry real Track Movement rows.
    r = check_tension(FIX / "wired-clean.md", beat_sheet_path=BEATS)
    assert "starved-thread" not in _predicates(r)


# --- Task 6: overloaded-chapter — the plot-level check ---------------------

PROFILE = Path(__file__).resolve().parent / "fixtures" / "length-profile.md"


def test_overloaded_chapter_flagged_when_a_connective_scene_cannot_be_paid_for(tmp_path):
    # 1 anchor + 8 connective in the default band (midpoint 2250): shares 8 + 8 = 16,
    # so each connective gets 2250/16 = 140 words... still above the 100 floor.
    # Push it to 20 connective scenes: 2250 * 1 / 28 = 80 < 100 → overloaded.
    scenes = "\n".join(
        f"### Scene {i} — Stop {i}\n\n**Weight:** connective\n\n**Beat flow:**\n\n1. A stop.\n"
        for i in range(2, 22))
    outline = tmp_path / "outline.md"
    outline.write_text(
        "---\nbook: 01\ntotal_chapters: 1\n---\n\n"
        "## Chapter 01 — Too Much\n\n"
        "- **Because:** opening\n"
        "- **Opens:** q-a — a question.\n"
        "- **Hook:** q-a — a hook.\n\n"
        "### Scene 1 — The Anchor\n\n**Weight:** anchor\n\n**Beat flow:**\n\n1. The turn.\n\n"
        + scenes, encoding="utf-8")
    result = check_tension(outline, profile_path=PROFILE)
    assert any(b.startswith("overloaded-chapter") for b in result["blocking"])
    finding = next(b for b in result["blocking"] if b.startswith("overloaded-chapter"))
    assert "ch 1" in finding


def test_no_overload_when_the_scene_count_fits_the_band(tmp_path):
    outline = tmp_path / "outline.md"
    outline.write_text(
        "---\nbook: 01\ntotal_chapters: 1\n---\n\n"
        "## Chapter 01 — Just Right\n\n"
        "- **Because:** opening\n"
        "- **Opens:** q-a — a question.\n"
        "- **Hook:** q-a — a hook.\n\n"
        "### Scene 1 — The Anchor\n\n**Weight:** anchor\n\n**Beat flow:**\n\n1. The turn.\n\n"
        "### Scene 2 — A Stop\n\n**Weight:** connective\n\n**Beat flow:**\n\n1. A stop.\n",
        encoding="utf-8")
    result = check_tension(outline, profile_path=PROFILE)
    assert not any(b.startswith("overloaded-chapter") for b in result["blocking"])


def test_unweighted_outline_is_never_overload_checked():
    # An un-weighted outline (book 1's shape) must never trip the check.
    result = check_tension(FIX / "wired-clean.md", profile_path=PROFILE)
    assert not any(b.startswith("overloaded-chapter") for b in result["blocking"])


# --- Fix wave: never silently lose the overload signal ---------------------
#
# _overload_check used to wrap penny_length.scene_budgets in a bare
# `try/except ValueError: continue` and separately default an undeclared
# scene weight to "support" (`s["weight"] or "support"`). Both are the exact
# anti-pattern brief_render.check_briefs already rejects by name
# (`undeclared-scene-weight`) for the identical problem: silently guessing
# at data the showrunner never declared. A chapter that cannot be budgeted —
# because the series' length-profile.md lacks a weight_* key it needs — must
# not lock with ZERO overload signal; it must produce a NAMED, waivable
# finding instead.

def test_overload_check_never_silently_skips_when_weight_class_unresolvable(tmp_path):
    # Reproduces the SAME 20-connective-scene overload as
    # test_overloaded_chapter_flagged_when_a_connective_scene_cannot_be_paid_for
    # above, but against a profile with no weight_connective — the exact
    # missing-config-key case the fix closes. Before the fix, scene_budgets
    # raised ValueError("unknown scene weight 'connective' ...") and the bare
    # `except ValueError: continue` swallowed it whole: no finding, nothing
    # to waive, a genuinely overloaded chapter locking clean.
    scenes = "\n".join(
        f"### Scene {i} — Stop {i}\n\n**Weight:** connective\n\n**Beat flow:**\n\n1. A stop.\n"
        for i in range(2, 22))
    outline = tmp_path / "outline.md"
    outline.write_text(
        "---\nbook: 01\ntotal_chapters: 1\n---\n\n"
        "## Chapter 01 — Too Much\n\n"
        "- **Because:** opening\n"
        "- **Opens:** q-a — a question.\n"
        "- **Hook:** q-a — a hook.\n\n"
        "### Scene 1 — The Anchor\n\n**Weight:** anchor\n\n**Beat flow:**\n\n1. The turn.\n\n"
        + scenes, encoding="utf-8")
    profile = tmp_path / "length-profile.md"
    profile.write_text(
        "```yaml\nband_default: [2000, 2500]\nweight_anchor: 8\n"
        "min_connective_words: 100\n```\n", encoding="utf-8")  # no weight_connective
    result = check_tension(outline, profile_path=profile)
    finding = next((b for b in result["blocking"] if b.startswith("overloaded-chapter")), None)
    assert finding is not None, (
        "a chapter that could not be budgeted at all must still produce a "
        "named, waivable finding — never silently vanish")
    assert "ch 1" in finding


def test_undeclared_scene_weight_gets_named_finding_not_silent_support_default(tmp_path):
    # A chapter that declares a weight for some scenes but not others must
    # get brief_render's own "undeclared-scene-weight" finding, not a
    # `weight or "support"` guess the showrunner never made.
    outline = tmp_path / "outline.md"
    outline.write_text(
        "---\nbook: 01\ntotal_chapters: 1\n---\n\n"
        "## Chapter 01 — Partial\n\n"
        "- **Because:** opening\n"
        "- **Opens:** q-a — a question.\n"
        "- **Hook:** q-a — a hook.\n\n"
        "### Scene 1 — The Anchor\n\n**Weight:** anchor\n\n**Beat flow:**\n\n1. The turn.\n\n"
        "### Scene 2 — No Weight\n\n**Beat flow:**\n\n1. Untagged.\n",
        encoding="utf-8")
    result = check_tension(outline, profile_path=PROFILE)
    finding = next(
        (b for b in result["blocking"] if b.startswith("undeclared-scene-weight")), None)
    assert finding is not None, (
        "an undeclared scene weight in a partially-weighted chapter must get "
        "a named finding, not a silent 'support' default")
    assert "scene 2" in finding
    assert not any(b.startswith("overloaded-chapter") for b in result["blocking"]), (
        "an undeclared weight must never be silently defaulted to 'support' "
        "and then budgeted as if the showrunner chose that")


# --- FINAL REVIEW C1: a length-profile the engine cannot parse must NEVER
# crash the lock. The live series' length-profile.md predates the scene-budget
# schema (a prose table + book_target_words, no band_*/weight_* keys), and
# check_tension parsed it unconditionally: /plot-book 02 -> lock-mystery ->
# raw ValueError traceback, no lock, no named predicate. The other eight
# checks must still run and the book must still be lockable; the overload
# check says, by name, that it could not run. --------------------------------

LEGACY = Path(__file__).resolve().parent / "fixtures" / "length-profile-legacy.md"
WEIGHTED_OVERLOADED = FIX / "weighted-overloaded.md"


def test_legacy_profile_never_crashes_a_wired_lock():
    result = check_tension(FIX / "wired-clean.md", profile_path=LEGACY)
    assert result["wired"] is True
    assert result["blocking"] == []          # the book is still lockable


def test_legacy_profile_names_the_skipped_overload_check_on_a_weighted_book():
    result = check_tension(WEIGHTED_OVERLOADED, profile_path=LEGACY)
    notes = " ".join(result["notes"])
    assert "overloaded-chapter" in notes
    assert "band_default" in notes, "the note must name what the profile is missing"
    assert not any(b.startswith("overloaded-chapter") for b in result["blocking"]), (
        "a profile the engine cannot use is a SKIP, recorded on the certificate — "
        "not a finding the showrunner has to waive on every lock")


# --- FINAL REVIEW I3: `floor = profile.get("min_connective_words", 0); if not
# floor: return` silently disabled the whole check for the whole book. -------

def test_missing_min_connective_words_is_a_named_note_never_a_silent_skip(tmp_path):
    profile = tmp_path / "length-profile.md"
    profile.write_text(
        "```yaml\nband_default: [2000, 2500]\nweight_anchor: 8\n"
        "weight_support: 3\nweight_connective: 1\n```\n", encoding="utf-8")  # no floors
    result = check_tension(WEIGHTED_OVERLOADED, profile_path=profile)
    notes = " ".join(result["notes"])
    assert "overloaded-chapter" in notes
    assert "min_" in notes, f"the note must name the missing floor key: {notes}"


# --- FINAL REVIEW I4: the check must be able to fire on the path that
# actually produces weights — the EXPANDED outline, which on the /plot-book
# path carries scenes but (because outline-expander predates the wiring) not
# necessarily any wiring at all. An unwired-but-weighted outline used to
# return before the overload check ever ran. --------------------------------

def test_overload_fires_on_a_weighted_outline_with_no_wiring(tmp_path):
    text = WEIGHTED_OVERLOADED.read_text(encoding="utf-8")
    stripped = "\n".join(
        line for line in text.splitlines()
        if not line.startswith(("- **Because:**", "- **Opens:**", "- **Hook:**")))
    outline = tmp_path / "outline.md"
    outline.write_text(stripped, encoding="utf-8")
    result = check_tension(outline, profile_path=PROFILE)
    assert result["wired"] is False
    assert any(b.startswith("overloaded-chapter") for b in result["blocking"]), (
        "scene weights, not wiring, are what the overload check reads — an "
        "expanded outline carrying weights but no wiring must still be checked")


# --- FINAL REVIEW I5: the spec defines overloaded-chapter as "scenes plus
# OBLIGATIONS exceed what the chapter's word band can hold". The check read
# neither support scenes nor obligations. -----------------------------------

def test_starved_support_scenes_overload_the_chapter():
    # 1 anchor + 12 support at the default band: 2250 * 3 / 44 = 153 words each,
    # against the profile's 250-word support floor.
    result = check_tension(FIX / "weighted-support-heavy.md", profile_path=PROFILE)
    finding = next((b for b in result["blocking"] if b.startswith("overloaded-chapter")), None)
    assert finding is not None, (
        "a chapter of twelve starved SUPPORT scenes is overloaded exactly as one "
        "of twenty starved connective scenes is")
    assert "support" in finding


def test_obligation_load_overloads_the_chapter(tmp_path):
    # Two scenes that price fine, but the chapter must also plant clues, open
    # and close questions, and advance every track — the load the band pays for.
    outline = tmp_path / "outline.md"
    outline.write_text(
        "---\nbook: 01\ntotal_chapters: 2\n---\n\n"
        "## Chapter 01 — Setup\n\n"
        "- **Because:** opening\n"
        "- **Opens:** q-a — a.\n"
        "- **Opens:** q-b — b.\n"
        "- **Opens:** q-c — c.\n"
        "- **Hook:** q-a — a hook.\n\n"
        "### Scene 1 — The Anchor\n\n- **Weight:** anchor\n\n**Beat flow:**\n\n1. The turn.\n\n"
        "## Chapter 02 — Everything At Once\n\n"
        "- **Because:** ch 01 — it follows.\n"
        "- **Opens:** q-d — d.\n"
        "- **Closes:** q-a\n"
        "- **Closes:** q-b\n"
        "- **Closes:** q-c\n"
        "- **Closes:** q-d\n"
        "- **Hook:** q-a — a hook.\n\n"
        "### Scene 1 — The Anchor\n\n- **Weight:** anchor\n\n**Beat flow:**\n\n1. The turn.\n\n"
        "### Scene 2 — A Stop\n\n- **Weight:** connective\n\n**Beat flow:**\n\n1. A stop.\n\n"
        "### Track Movement\n- **M:** The tin.\n- **P:** She commits.\n"
        "- **R:** Cal calls.\n- **B:** The shop opens.\n",
        encoding="utf-8")
    whodunit = tmp_path / "book-01.yaml"
    whodunit.write_text(
        "reveal_chapter: 2\nclue_schedule:\n"
        "  - {id: c-1, plant_chapter: 2}\n  - {id: c-2, plant_chapter: 2}\n"
        "red_herrings:\n  - {id: rh-1, plant_chapter: 2}\n", encoding="utf-8")
    sheet = tmp_path / "beat-sheet.yaml"
    sheet.write_text("obligations:\n  max_per_chapter: 6\n", encoding="utf-8")
    result = check_tension(outline, profile_path=PROFILE, whodunit_path=whodunit,
                           beat_sheet_path=sheet)
    finding = next((b for b in result["blocking"]
                    if b.startswith("overloaded-chapter") and "ch 2" in b), None)
    assert finding is not None, (
        "ch 2 discharges 12 obligations (3 clues + 1 open + 4 closes + 4 tracks) "
        "against the genre's cap of 6 — a chapter that will run long no matter "
        "how well it is written")
    assert "obligation" in finding
    assert not any(b.startswith("overloaded-chapter") and "ch 1" in b
                   for b in result["blocking"]), "ch 1 carries 4 obligations — under the cap"
