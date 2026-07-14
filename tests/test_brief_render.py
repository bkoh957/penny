import os
from pathlib import Path

import pytest

from scripts import brief_render

FIX = Path(__file__).resolve().parent / "fixtures"
PROFILE = FIX / "length-profile.md"
WEIGHTED = FIX / "outlines" / "weighted-clean.md"
INVERTED = FIX / "outlines" / "weighted-inverted.md"
WIRED = FIX / "outlines" / "wired-clean.md"


def _ids(findings):
    return sorted({f.split(":", 1)[0] for f in findings})


def test_unweighted_outline_is_skipped_entirely():
    r = brief_render.check_briefs(WIRED)
    assert r["weighted"] is False
    assert r["findings"] == []


def test_clean_weighted_outline_has_no_findings():
    r = brief_render.check_briefs(WEIGHTED)
    assert r["weighted"] is True
    assert r["findings"] == []


def test_prompt_mass_inversion_is_flagged():
    r = brief_render.check_briefs(INVERTED)
    assert "prompt-mass-inversion" in _ids(r["findings"])
    finding = next(f for f in r["findings"] if f.startswith("prompt-mass-inversion"))
    assert "ch 1" in finding
    assert "The Drive" in finding


def test_unweighted_chapter_in_a_weighted_book_is_flagged(tmp_path):
    text = WEIGHTED.read_text(encoding="utf-8").replace("**Weight:** anchor\n\n**Beat flow:**\n\n1. Mary sets down the tin and does not sit.", "**Beat flow:**\n\n1. Mary sets down the tin and does not sit.")
    p = tmp_path / "outline.md"
    p.write_text(text, encoding="utf-8")
    r = brief_render.check_briefs(p)
    assert "unweighted-chapter" in _ids(r["findings"])


def test_all_cliffhangers_is_flagged_when_the_beat_sheet_caps_them(tmp_path):
    text = WEIGHTED.read_text(encoding="utf-8").replace("[promise]", "[cliffhanger]")
    outline = tmp_path / "outline.md"
    outline.write_text(text, encoding="utf-8")
    sheet = tmp_path / "beat-sheet.yaml"
    sheet.write_text("hooks:\n  max_cliffhanger_fraction: 0.5\n", encoding="utf-8")
    r = brief_render.check_briefs(outline, beat_sheet_path=sheet)
    assert "hook-grade-distribution" in _ids(r["findings"])


def test_missing_hook_grade_is_flagged(tmp_path):
    text = WEIGHTED.read_text(encoding="utf-8").replace("[cliffhanger] ", "")
    outline = tmp_path / "outline.md"
    outline.write_text(text, encoding="utf-8")
    r = brief_render.check_briefs(outline)
    assert "hook-grade-distribution" in _ids(r["findings"])


def test_scene_less_stub_chapter_is_skipped_not_flagged(tmp_path):
    """A chapter with zero ### Scene blocks (compact-format, or a skeletal stub
    /expand-outline hasn't reached yet) has nothing to say about weights or
    anchors — it must be skipped entirely by the scene-level checks, not
    treated as an anchor-less chapter. Ch 1 stays weighted and clean so its
    checks still run; ch 2 is the scene-less stub."""
    stub = (
        "## Chapter 02 — Not Yet Expanded\n\n"
        "### Chapter Summary\n"
        "A stub the outline-expander hasn't reached yet.\n"
    )
    # WEIGHTED's own frontmatter says total_chapters: 2 and already has a real
    # chapter 2 — replace it with the scene-less stub rather than appending a
    # duplicate chapter number.
    text = WEIGHTED.read_text(encoding="utf-8").split("## Chapter 02")[0] + stub
    p = tmp_path / "outline.md"
    p.write_text(text, encoding="utf-8")
    r = brief_render.check_briefs(p)
    assert r["weighted"] is True
    ids_by_chapter = [f for f in r["findings"] if "ch 2" in f]
    assert ids_by_chapter == []
    assert "unweighted-chapter" not in _ids(r["findings"])
    assert "prompt-mass-inversion" not in _ids(r["findings"])


def test_check_briefs_no_longer_accepts_profile_path():
    """FIX 2: check_briefs never reads band/weight data — profile_path was a
    dead-code feed into parse_profile and is dropped from the signature
    entirely (YAGNI)."""
    with pytest.raises(TypeError):
        brief_render.check_briefs(WEIGHTED, profile_path=PROFILE)


def test_check_briefs_works_with_no_length_profile_on_disk(tmp_path):
    """FIX 2 regression: check_briefs must not crash when no length-profile.md
    exists at all — it has no reason to touch one."""
    r = brief_render.check_briefs(WEIGHTED)
    assert r["weighted"] is True


def test_malformed_hooks_scalar_is_treated_as_no_cap(tmp_path):
    """FIX 3: a hand-edited beat-sheet.yaml with `hooks:` as a scalar (not a
    mapping) must not crash .get() — treat it as 'no cap configured'."""
    text = WEIGHTED.read_text(encoding="utf-8").replace("[promise]", "[cliffhanger]")
    outline = tmp_path / "outline.md"
    outline.write_text(text, encoding="utf-8")
    sheet = tmp_path / "beat-sheet.yaml"
    sheet.write_text("hooks: none\n", encoding="utf-8")
    r = brief_render.check_briefs(outline, beat_sheet_path=sheet)
    # no crash, and no cap means no hook-grade-distribution finding from the
    # cliffhanger-fraction check (both hooks are now cliffhanger, but with no
    # cap configured there's nothing to compare against).
    assert r["weighted"] is True


from scripts import penny_length


def _ch(name, path=WEIGHTED):
    from scripts.penny_wiring import parse_wired_chapters
    chapters = parse_wired_chapters(path.read_text(encoding="utf-8"))
    return next(c for c in chapters if c["num"] == name)


def _profile():
    return penny_length.parse_profile(PROFILE.read_text(encoding="utf-8"))


def test_brief_leads_with_the_one_thing_then_the_anchor():
    brief = brief_render.render_brief(
        _ch(1), profile=_profile(),
        obligations={"clues": [], "opens": [], "closes": [], "tracks": {}},
        outline_text=WEIGHTED.read_text(encoding="utf-8"))
    one_thing = brief.index("## The one thing")
    shape = brief.index("## The shape")
    obligations = brief.index("## Obligations")
    reference = brief.index("## Reference")
    assert one_thing < shape < obligations < reference


def test_anchor_carries_the_largest_budget_and_the_budgets_sum_to_the_band():
    """FIX 1: the old version of this test asserted "~2000 words" and "~250
    words" as independent substrings anywhere in the brief — a monkeypatch
    that reversed scene_budgets' return (anchor gets 250, connective gets
    2000: precisely the failure this compiler exists to prevent) still
    passed both assertions, because neither one was pinned to a scene. This
    version parses the rendered brief and checks the budget attached to
    EACH scene's own line, so a swap fails it."""
    brief = brief_render.render_brief(
        _ch(1), profile=_profile(),
        obligations={"clues": [], "opens": [], "closes": [], "tracks": {}},
        outline_text=WEIGHTED.read_text(encoding="utf-8"))
    lines = brief.splitlines()
    anchor_line = next(l for l in lines if l.startswith("### ANCHOR"))
    connective_line = next(l for l in lines if "CONNECTIVE" in l)
    # ch 1 has no [type:] flag, so the default band 2000-2500 → midpoint 2250,
    # shares connective 1 + anchor 8 = 9 → 250 and 2000.
    assert "~2000 words" in anchor_line       # the anchor's OWN line
    assert "~250 words" in connective_line    # the connective's OWN line
    assert "Cal and the Mug" in anchor_line


def test_connective_scene_names_its_form_not_a_number_alone():
    brief = brief_render.render_brief(
        _ch(1), profile=_profile(),
        obligations={"clues": [], "opens": [], "closes": [], "tracks": {}},
        outline_text=WEIGHTED.read_text(encoding="utf-8"))
    assert "in summary, not scene" in brief


def test_brief_commissions_the_first_line_and_forbids_the_warm_up():
    brief = brief_render.render_brief(
        _ch(1), profile=_profile(),
        obligations={"clues": [], "opens": [], "closes": [], "tracks": {}},
        outline_text=WEIGHTED.read_text(encoding="utf-8"))
    assert "in motion, mid-argument with the estate agent." in brief
    assert "no weather, no waking, no arriving" in brief


def test_brief_commissions_the_graded_hook_and_forbids_the_button():
    brief = brief_render.render_brief(
        _ch(1), profile=_profile(),
        obligations={"clues": [], "opens": [], "closes": [], "tracks": {}},
        outline_text=WEIGHTED.read_text(encoding="utf-8"))
    assert "cliffhanger" in brief
    assert "Do not add a closing paragraph of reflection" in brief


def test_obligations_are_a_checklist_not_beats():
    brief = brief_render.render_brief(
        _ch(1), profile=_profile(),
        obligations={"clues": ["clue-tide-table"], "opens": ["q-who-is-she"],
                     "closes": [], "tracks": {"P": "She commits."}},
        outline_text=WEIGHTED.read_text(encoding="utf-8"))
    assert "clue-tide-table" in brief
    assert "must be TRUE OF THE PAGE" in brief
    assert "not stops on an itinerary" in brief


def test_long_waiver_is_carried_into_the_brief():
    brief = brief_render.render_brief(
        _ch(2), profile=_profile(),
        obligations={"clues": [], "opens": [], "closes": [], "tracks": {}},
        outline_text=WEIGHTED.read_text(encoding="utf-8"))
    # ch 2 declares [type: major-reveal] → band 2500-3200, midpoint 2850
    assert "~2850 words" in brief
    assert "the confession runs its full course" in brief


# ---- FIX 2: an undeclared scene weight must not silently default to "support" ----

def test_undeclared_scene_weight_is_flagged_when_some_scenes_declare_and_one_doesnt(tmp_path):
    """ch 1 of WEIGHTED has scene 1 (connective) and scene 2 (anchor). Strip
    scene 1's Weight line only — the anchor is still declared, so this is
    NOT the all-or-nothing unweighted-chapter case; it's a partial
    declaration, which must earn its own finding naming the chapter and the
    untagged scene."""
    text = WEIGHTED.read_text(encoding="utf-8").replace(
        "**Weight:** connective\n\n", "")
    p = tmp_path / "outline.md"
    p.write_text(text, encoding="utf-8")
    r = brief_render.check_briefs(p)
    assert "undeclared-scene-weight" in _ids(r["findings"])
    finding = next(f for f in r["findings"] if f.startswith("undeclared-scene-weight"))
    assert "ch 1" in finding
    assert "The Drive" in finding


def test_render_brief_raises_when_a_scene_weight_is_undeclared():
    """FIX 2b: render_brief must not do `s["weight"] or "support"` — an
    undeclared weight alongside a declared anchor is an authoring omission,
    not a default the compiler is entitled to guess at."""
    ch = _ch(1)
    ch["scenes"][0]["weight"] = None  # scene 1 ("The Drive") left undeclared
    with pytest.raises(ValueError, match=r"(?i)ch(?:apter)?.?\s*1\b.*(?:Drive|scene 1|weight)"):
        brief_render.render_brief(
            ch, profile=_profile(),
            obligations={"clues": [], "opens": [], "closes": [], "tracks": {}},
            outline_text=WEIGHTED.read_text(encoding="utf-8"))


# ---- FIX 3: a chapter with no anchor has no correct brief ----

def test_render_brief_raises_when_chapter_has_no_anchor_scene():
    ch = _ch(1)
    for s in ch["scenes"]:
        s["weight"] = "support"  # both declared, neither an anchor
    with pytest.raises(ValueError, match=r"(?i)ch(?:apter)?.?\s*1\b.*anchor"):
        brief_render.render_brief(
            ch, profile=_profile(),
            obligations={"clues": [], "opens": [], "closes": [], "tracks": {}},
            outline_text=WEIGHTED.read_text(encoding="utf-8"))


# ---- FIX 4: two anchors contradict each other on the page ----

def test_multi_anchor_chapter_is_flagged(tmp_path):
    """Tag ch 1 scene 1 (originally connective) as a SECOND anchor. Own
    finding id chosen: multi-anchor-chapter (kept separate from
    unweighted-chapter, since this chapter is fully weighted — it declares
    too MANY reasons to exist, not too few)."""
    text = WEIGHTED.read_text(encoding="utf-8").replace(
        "**Weight:** connective", "**Weight:** anchor", 1)
    p = tmp_path / "outline.md"
    p.write_text(text, encoding="utf-8")
    r = brief_render.check_briefs(p)
    assert "multi-anchor-chapter" in _ids(r["findings"])
    finding = next(f for f in r["findings"] if f.startswith("multi-anchor-chapter"))
    assert "ch 1" in finding


def test_render_brief_raises_when_chapter_has_two_anchor_scenes():
    ch = _ch(1)
    for s in ch["scenes"]:
        s["weight"] = "anchor"
    with pytest.raises(ValueError, match=r"(?i)ch(?:apter)?.?\s*1\b.*anchor"):
        brief_render.render_brief(
            ch, profile=_profile(),
            obligations={"clues": [], "opens": [], "closes": [], "tracks": {}},
            outline_text=WEIGHTED.read_text(encoding="utf-8"))


# ---- FIX 5: an unrecognised weight class must not raise a bare KeyError ----

def test_render_brief_raises_a_named_error_for_a_weight_class_form_has_no_prose_for():
    """penny_length.scene_budgets is generic over any weight_* class a series
    declares in length-profile.md — a 4th class ("urgent") is a legal,
    reachable declaration. _FORM in brief_render.py only knows
    anchor/support/connective, so this must raise a clear, named error
    (naming the class and the file to fix) rather than a bare KeyError."""
    profile = _profile()
    profile["weights"]["urgent"] = 5
    ch = _ch(1)
    ch["scenes"][0]["weight"] = "urgent"  # scene 1: declared, but no _FORM entry
    with pytest.raises(ValueError, match=r"(?i)urgent"):
        brief_render.render_brief(
            ch, profile=profile,
            obligations={"clues": [], "opens": [], "closes": [], "tracks": {}},
            outline_text=WEIGHTED.read_text(encoding="utf-8"))


import shutil


def _series(tmp_path):
    (tmp_path / ".penny").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    shutil.copy(PROFILE, tmp_path / "config/length-profile.md")
    inp = tmp_path / "input/book-01"
    inp.mkdir(parents=True, exist_ok=True)
    shutil.copy(WEIGHTED, inp / "outline.md")
    (tmp_path / "series/whodunit").mkdir(parents=True, exist_ok=True)
    (tmp_path / "series/whodunit/book-01.yaml").write_text(
        "book: '01'\nreveal_chapter: 2\nclue_schedule:\n"
        "  - { id: clue-tide-table, plant_chapter: 1, pays_off_chapter: 2, necessary: true }\n",
        encoding="utf-8")
    return tmp_path


def test_build_writes_one_brief_per_chapter_stamped_with_the_outline_sha(tmp_path):
    root = _series(tmp_path)
    assert brief_render.build("01", repo_root=root) == 0
    b1 = root / "input/book-01/briefs/ch-01.md"
    assert b1.is_file()
    from scripts.penny_meta import parse_frontmatter
    fm = parse_frontmatter(b1.read_text(encoding="utf-8"))
    assert fm["built_from_outline"]


def test_build_pulls_the_clue_obligation_from_the_locked_ledger(tmp_path):
    root = _series(tmp_path)
    brief_render.build("01", repo_root=root)
    text = (root / "input/book-01/briefs/ch-01.md").read_text(encoding="utf-8")
    assert "clue-tide-table" in text


def test_editing_the_outline_makes_the_brief_stale(tmp_path):
    root = _series(tmp_path)
    brief_render.build("01", repo_root=root)
    assert brief_render.stale_briefs("01", root) == []
    outline = root / "input/book-01/outline.md"
    outline.write_text(outline.read_text(encoding="utf-8") + "\n<!-- edited -->\n",
                       encoding="utf-8")
    assert brief_render.stale_briefs("01", root) == ["01", "02"]


# ---- REVIEW FIX 1: the whodunit ledger is an upstream too — editing ONLY the
# ledger (moving a clue's plant_chapter) must make the briefs stale, exactly
# as the reviewer reproduced it live. ----------------------------------------

def test_build_stamps_built_from_whodunit_when_a_ledger_exists(tmp_path):
    root = _series(tmp_path)
    brief_render.build("01", repo_root=root)
    from scripts.penny_meta import parse_frontmatter
    fm = parse_frontmatter((root / "input/book-01/briefs/ch-01.md").read_text(encoding="utf-8"))
    assert fm["built_from_whodunit"]


def test_editing_only_the_ledger_makes_the_briefs_stale():
    """The reviewer's exact repro: build the briefs, then edit ONLY the
    ledger (move clue-tide-table's plant_chapter from 1 to 2) — the
    staleness check must catch this, not just outline edits."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        root = _series(Path(d))
        brief_render.build("01", repo_root=root)
        assert brief_render.stale_briefs("01", root) == []
        ledger = root / "series/whodunit/book-01.yaml"
        ledger.write_text(
            "book: '01'\nreveal_chapter: 2\nclue_schedule:\n"
            "  - { id: clue-tide-table, plant_chapter: 2, pays_off_chapter: 2, necessary: true }\n",
            encoding="utf-8")
        assert brief_render.stale_briefs("01", root) == ["01", "02"]


def test_deleting_the_ledger_after_a_stamped_build_makes_briefs_stale(tmp_path):
    root = _series(tmp_path)
    brief_render.build("01", repo_root=root)
    assert brief_render.stale_briefs("01", root) == []
    (root / "series/whodunit/book-01.yaml").unlink()
    assert brief_render.stale_briefs("01", root) == ["01", "02"]


def test_a_book_with_no_whodunit_ledger_at_all_stamps_the_sentinel(tmp_path):
    """SECOND FIX WAVE (FIX 1): the previous instruction — 'no ledger means no
    stamp, and no stamp is not stale on that account' — left a hole: a ledger
    created AFTER an unstamped build would never be noticed. build() must
    ALWAYS write built_from_whodunit, using an explicit sentinel
    (NO_WHODUNIT) when no ledger exists, so 'saw nothing' is itself a
    recorded, comparable fact."""
    root = tmp_path
    (root / ".penny").mkdir(parents=True, exist_ok=True)
    (root / "config").mkdir(parents=True, exist_ok=True)
    shutil.copy(PROFILE, root / "config/length-profile.md")
    inp = root / "input/book-01"
    inp.mkdir(parents=True, exist_ok=True)
    shutil.copy(WEIGHTED, inp / "outline.md")
    # no series/whodunit/book-01.yaml at all
    assert brief_render.build("01", repo_root=root) == 0
    from scripts.penny_meta import parse_frontmatter
    fm = parse_frontmatter((root / "input/book-01/briefs/ch-01.md").read_text(encoding="utf-8"))
    assert fm.get("built_from_whodunit") == brief_render.NO_WHODUNIT
    # still fresh: nothing has changed since the build that stamped it.
    assert brief_render.stale_briefs("01", root) == []


def test_ledger_arriving_after_a_none_stamped_build_makes_briefs_stale(tmp_path):
    """THE HOLE ITSELF, reproduced: build with no ledger (stamped
    NO_WHODUNIT), then CREATE the ledger assigning a clue to chapter 1.
    stale_briefs() must catch this — a mismatch in the OTHER direction
    (none -> a real sha) is just as much drift as sha -> sha or sha -> none."""
    root = tmp_path
    (root / ".penny").mkdir(parents=True, exist_ok=True)
    (root / "config").mkdir(parents=True, exist_ok=True)
    shutil.copy(PROFILE, root / "config/length-profile.md")
    inp = root / "input/book-01"
    inp.mkdir(parents=True, exist_ok=True)
    shutil.copy(WEIGHTED, inp / "outline.md")
    assert brief_render.build("01", repo_root=root) == 0
    assert brief_render.stale_briefs("01", root) == []
    wd = root / "series/whodunit"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "book-01.yaml").write_text(
        "book: '01'\nreveal_chapter: 2\nclue_schedule:\n"
        "  - { id: clue-tide-table, plant_chapter: 1, pays_off_chapter: 2, necessary: true }\n",
        encoding="utf-8")
    assert brief_render.stale_briefs("01", root) == ["01", "02"]


def test_brief_with_no_whodunit_stamp_at_all_is_treated_as_stale(tmp_path):
    """A brief predating the built_from_whodunit field entirely (an older
    brief, before this fix shipped) carries no stamp — not the sentinel, no
    key at all. It must be treated as stale: it recorded nothing about the
    ledger, and an absent record is not a clean bill of health."""
    root = _series(tmp_path)
    outline = root / "input/book-01/outline.md"
    sha = brief_render._sha(outline)
    (root / "input/book-01/briefs").mkdir(parents=True, exist_ok=True)
    (root / "input/book-01/briefs/ch-01.md").write_text(
        f"---\nbuilt_from_outline: {sha}\n---\n# brief\n", encoding="utf-8")
    (root / "input/book-01/briefs/ch-02.md").write_text(
        f"---\nbuilt_from_outline: {sha}\n---\n# brief\n", encoding="utf-8")
    assert brief_render.stale_briefs("01", root) == ["01", "02"]


def test_preflight_draft_refuses_a_brief_stale_only_on_the_ledger(tmp_path):
    """The reviewer's exact repro, through the actual gate:
    preflight.cmd_draft must refuse to draft a chapter whose brief drifted
    from a ledger edit alone, no outline edit involved."""
    from scripts import preflight
    root = _series(tmp_path)
    brief_render.build("01", repo_root=root)
    lock_dir = root / ".penny/locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    (lock_dir / "book-01.mystery.lock").write_text("locked\n", encoding="utf-8")
    run_config = root / "config/run-config.md"
    run_config.write_text(
        "```yaml\ndrafting_model: model-a\ninspector_model: model-b\n```\n",
        encoding="utf-8")
    ledger = root / "series/whodunit/book-01.yaml"
    ledger.write_text(
        "book: '01'\nreveal_chapter: 2\nclue_schedule:\n"
        "  - { id: clue-tide-table, plant_chapter: 2, pays_off_chapter: 2, necessary: true }\n",
        encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        preflight.cmd_draft("01", "01", repo_root=root, run_config=run_config)
    assert "stale brief" in str(e.value)


# ---- REVIEW FIX 2: a malformed plant_chapter must fail loud and per-chapter,
# never crash the whole book build with a raw traceback. ---------------------

def test_null_plant_chapter_fails_loud_and_per_chapter_not_a_crash(tmp_path, capsys):
    root = _series(tmp_path)
    ledger = root / "series/whodunit/book-01.yaml"
    ledger.write_text(
        "book: '01'\nreveal_chapter: 2\nclue_schedule:\n"
        "  - { id: clue-tide-table, plant_chapter: null, pays_off_chapter: 2, necessary: true }\n",
        encoding="utf-8")
    rc = brief_render.build("01", repo_root=root)
    assert rc == 1
    out = capsys.readouterr().out
    assert "FAILED" in out
    assert "clue-tide-table" in out
    assert "book-01.yaml" in out
    # no briefs written for a chapter whose obligations couldn't be computed
    assert not (root / "input/book-01/briefs/ch-01.md").is_file()


def test_missing_plant_chapter_key_fails_loud_naming_the_clue(tmp_path, capsys):
    root = _series(tmp_path)
    ledger = root / "series/whodunit/book-01.yaml"
    ledger.write_text(
        "book: '01'\nreveal_chapter: 2\nred_herrings:\n"
        "  - { id: herring-fake-alibi, pays_off_chapter: 2, necessary: false }\n",
        encoding="utf-8")
    rc = brief_render.build("01", repo_root=root)
    assert rc == 1
    out = capsys.readouterr().out
    assert "herring-fake-alibi" in out


# ---- SECOND FIX WAVE, FIX 2: the ledger's own load must be guarded too — a
# malformed ledger (bad YAML, or a top-level list) must never crash build()
# with a raw ParserError/AttributeError, and an unreadable ledger must never
# crash build() OR stale_briefs() (and therefore preflight.cmd_draft). One
# guarded helper (brief_render.load_ledger) is used by every caller. --------

def test_malformed_yaml_ledger_fails_loud_not_a_raw_traceback(tmp_path, capsys):
    root = _series(tmp_path)
    ledger = root / "series/whodunit/book-01.yaml"
    ledger.write_text("book: '01'\nclue_schedule: [ { unterminated\n", encoding="utf-8")
    rc = brief_render.build("01", repo_root=root)
    assert rc == 1
    out = capsys.readouterr().out
    assert "FAILED" in out
    assert "malformed-ledger" in out
    assert "book-01.yaml" in out
    assert not (root / "input/book-01/briefs/ch-01.md").is_file()


def test_top_level_list_ledger_fails_loud_not_an_attributeerror(tmp_path, capsys):
    root = _series(tmp_path)
    ledger = root / "series/whodunit/book-01.yaml"
    ledger.write_text("- clue-tide-table\n- herring-fake-alibi\n", encoding="utf-8")
    rc = brief_render.build("01", repo_root=root)
    assert rc == 1
    out = capsys.readouterr().out
    assert "FAILED" in out
    assert "malformed-ledger" in out
    assert not (root / "input/book-01/briefs/ch-01.md").is_file()


def test_load_ledger_raises_named_error_for_malformed_yaml(tmp_path):
    ledger = tmp_path / "book-01.yaml"
    ledger.write_text("book: '01'\nclue_schedule: [ { unterminated\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"malformed-ledger"):
        brief_render.load_ledger(ledger)


def test_load_ledger_raises_named_error_for_top_level_list(tmp_path):
    ledger = tmp_path / "book-01.yaml"
    ledger.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"malformed-ledger"):
        brief_render.load_ledger(ledger)


def test_unreadable_ledger_fails_loud_on_build_not_a_crash(tmp_path, capsys):
    """Permission-denied ledger: build() must report a named error and return
    nonzero, never let a raw PermissionError escape. Skipped when running
    with elevated privileges (e.g. root in a container), where chmod 0o000
    does not actually block reads — flaky there, not on a normal dev machine."""
    root = _series(tmp_path)
    ledger = root / "series/whodunit/book-01.yaml"
    ledger.chmod(0o000)
    try:
        if os.access(ledger, os.R_OK):
            pytest.skip("running with elevated privileges; chmod 0o000 doesn't block reads")
        rc = brief_render.build("01", repo_root=root)
        assert rc == 1
        out = capsys.readouterr().out
        assert "FAILED" in out
        assert "unreadable-ledger" in out
        assert not (root / "input/book-01/briefs/ch-01.md").is_file()
    finally:
        ledger.chmod(0o644)


def test_unreadable_ledger_raises_from_stale_briefs_not_a_crash(tmp_path):
    """stale_briefs() must not let a raw PermissionError escape either — it
    raises the same named ValueError, which preflight.cmd_draft catches and
    turns into its `preflight: <predicate>` form. Skipped under elevated
    privileges, same reasoning as above."""
    root = _series(tmp_path)
    brief_render.build("01", repo_root=root)
    ledger = root / "series/whodunit/book-01.yaml"
    ledger.chmod(0o000)
    try:
        if os.access(ledger, os.R_OK):
            pytest.skip("running with elevated privileges; chmod 0o000 doesn't block reads")
        with pytest.raises(ValueError, match=r"unreadable-ledger"):
            brief_render.stale_briefs("01", root)
    finally:
        ledger.chmod(0o644)


def test_preflight_draft_fails_named_predicate_on_malformed_ledger(tmp_path):
    from scripts import preflight
    root = _series(tmp_path)
    lock_dir = root / ".penny/locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    (lock_dir / "book-01.mystery.lock").write_text("locked\n", encoding="utf-8")
    run_config = root / "config/run-config.md"
    run_config.write_text(
        "```yaml\ndrafting_model: model-a\ninspector_model: model-b\n```\n",
        encoding="utf-8")
    ledger = root / "series/whodunit/book-01.yaml"
    ledger.write_text("book: '01'\nclue_schedule: [ { unterminated\n", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        preflight.cmd_draft("01", "01", repo_root=root, run_config=run_config)
    assert "preflight:" in str(e.value)
    assert "malformed-ledger" in str(e.value)


# ---- THIRD FIX WAVE, FIX 1: the guarded loader's guarantee must reach the
# shape of clue_schedule/red_herrings, not just the ledger's top level.
# clue_schedule as a bare string, or a list holding non-mapping entries, must
# raise the same named ValueError as every other malformed-ledger case —
# never an AttributeError from `.get()` on a string character or an int. ----

def test_load_ledger_raises_named_error_when_clue_schedule_is_not_a_list(tmp_path):
    ledger = tmp_path / "book-01.yaml"
    ledger.write_text("book: '01'\nclue_schedule: 'not a list'\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"malformed-ledger"):
        brief_render.load_ledger(ledger)


def test_load_ledger_raises_named_error_when_clue_schedule_entry_is_not_a_mapping(tmp_path):
    ledger = tmp_path / "book-01.yaml"
    ledger.write_text(
        "book: '01'\nclue_schedule:\n  - just-a-string\n  - 42\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"malformed-ledger"):
        brief_render.load_ledger(ledger)


def test_load_ledger_raises_named_error_when_red_herrings_is_not_a_list(tmp_path):
    ledger = tmp_path / "book-01.yaml"
    ledger.write_text("book: '01'\nred_herrings: 'not a list'\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"malformed-ledger"):
        brief_render.load_ledger(ledger)


def test_load_ledger_raises_named_error_when_red_herrings_entry_is_not_a_mapping(tmp_path):
    ledger = tmp_path / "book-01.yaml"
    ledger.write_text(
        "book: '01'\nred_herrings:\n  - just-a-string\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"malformed-ledger"):
        brief_render.load_ledger(ledger)


def test_build_fails_loud_not_a_crash_when_clue_schedule_is_a_string(tmp_path, capsys):
    """Reviewer repro #1: clue_schedule: 'not a list' used to iterate the
    string's CHARACTERS, then call `.get()` on each one-character string —
    an AttributeError that escapes build()'s `except ValueError` and aborts
    the whole book mid-loop with a raw traceback."""
    root = _series(tmp_path)
    ledger = root / "series/whodunit/book-01.yaml"
    ledger.write_text("book: '01'\nclue_schedule: 'not a list'\n", encoding="utf-8")
    rc = brief_render.build("01", repo_root=root)
    assert rc == 1
    out = capsys.readouterr().out
    assert "FAILED" in out
    assert "malformed-ledger" in out
    assert "book-01.yaml" in out
    assert not (root / "input/book-01/briefs/ch-01.md").is_file()


def test_build_fails_loud_not_a_crash_when_clue_schedule_has_a_non_mapping_entry(tmp_path, capsys):
    """Reviewer repro #2: clue_schedule: [just-a-string, 42] — AttributeError
    on the first non-dict entry's `.get(...)` call."""
    root = _series(tmp_path)
    ledger = root / "series/whodunit/book-01.yaml"
    ledger.write_text(
        "book: '01'\nclue_schedule:\n  - just-a-string\n  - 42\n", encoding="utf-8")
    rc = brief_render.build("01", repo_root=root)
    assert rc == 1
    out = capsys.readouterr().out
    assert "FAILED" in out
    assert "malformed-ledger" in out
    assert not (root / "input/book-01/briefs/ch-01.md").is_file()


# ---- THIRD FIX WAVE, FIX 2: a deleted outline must not make every brief
# report "fresh" — briefs are drift-detectable artifacts of a real outline
# file, and a vanished source is the maximal case of drift, not an
# exemption. The genuine backward-compat case (no briefs directory at all —
# book 1, before /build-briefs has ever run) must still return []. ----------

def test_deleted_outline_makes_every_brief_stale(tmp_path):
    root = _series(tmp_path)
    brief_render.build("01", repo_root=root)
    assert brief_render.stale_briefs("01", root) == []
    (root / "input/book-01/outline.md").unlink()
    assert brief_render.stale_briefs("01", root) == ["01", "02"]


def test_no_briefs_directory_at_all_still_returns_empty_list(tmp_path):
    """The genuine backward-compat case stays intact: book 1, no briefs ever
    built, no outline needed to draft from the raw section."""
    root = tmp_path
    (root / ".penny").mkdir(parents=True, exist_ok=True)
    assert brief_render.stale_briefs("01", root) == []


# ---- THIRD FIX WAVE, FIX 3: only files named ch-<digits>.md are chapter
# briefs — a stray file like briefs/ch-README.md must not be reported as a
# stale chapter named "README". -----------------------------------------

def test_stray_non_numbered_brief_file_is_not_reported_as_stale(tmp_path):
    root = _series(tmp_path)
    brief_render.build("01", repo_root=root)
    (root / "input/book-01/briefs/ch-README.md").write_text(
        "# not a chapter brief\n", encoding="utf-8")
    assert brief_render.stale_briefs("01", root) == []
