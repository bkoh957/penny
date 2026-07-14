import hashlib
import shutil
from pathlib import Path

import pytest

from scripts import preflight

SRC = preflight.REPO
# The cozy series fixture: real copies of the config OVERRIDES (run-config,
# packs, lexicon) + canon-core. Test-fixture ledgers (FAIR/UNFAIR below) still
# come from the real repo's tests/fixtures/ledgers/ — those are engine test
# data, not series content, and are unaffected by the config-cutover.
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "cozy"


def _scaffold_lockable(tmp_path, *, ledger_fixture, valid_lexicon=True):
    """Build a tmp repo able to run lock-mystery: fixture run-config, fixture
    canon-core, a (valid or malformed) lexicon, a resolvable character corpus,
    and a ledger."""
    # run-config + canon-core copied from the cozy fixture (both valid).
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURE / "config/run-config.md", tmp_path / "config/run-config.md")
    (tmp_path / "series/continuity").mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURE / "series/continuity/canon-core.md",
                tmp_path / "series/continuity/canon-core.md")
    # lexicon: fixture (valid) or a malformed stub.
    (tmp_path / "config/setting-pack").mkdir(parents=True, exist_ok=True)
    if valid_lexicon:
        shutil.copy(FIXTURE / "config/setting-pack/lexicon.yaml",
                    tmp_path / "config/setting-pack/lexicon.yaml")
    else:
        (tmp_path / "config/setting-pack/lexicon.yaml").write_text(
            "terms:\n  - {term: jumper}\n", encoding="utf-8")  # missing required fields
    # resolvable character corpus.
    cc = tmp_path / "series/continuity/characters"
    cc.mkdir(parents=True, exist_ok=True)
    for cid in ("margaret", "thomas", "edwin-tilley"):
        (cc / f"{cid}.md").write_text("---\nid: x\n---\n", encoding="utf-8")
    # the proposed (unlocked) ledger.
    wd = tmp_path / "series/whodunit"
    wd.mkdir(parents=True, exist_ok=True)
    shutil.copy(ledger_fixture, wd / "book-01.yaml")
    return wd / "book-01.yaml"


FAIR = SRC / "tests/fixtures/ledgers/fair.yaml"
UNFAIR = SRC / "tests/fixtures/ledgers/unfair_clue_after_reveal.yaml"


def test_lock_mystery_writes_lock_when_valid(tmp_path):
    _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=True)
    assert preflight.cmd_lock_mystery("01", repo_root=tmp_path) == 0
    assert preflight.lock_path("01", tmp_path).is_file()


def test_lock_mystery_no_lock_when_fairplay_fails(tmp_path):
    _scaffold_lockable(tmp_path, ledger_fixture=UNFAIR, valid_lexicon=True)
    with pytest.raises(SystemExit) as e:
        preflight.cmd_lock_mystery("01", repo_root=tmp_path)
    assert "fairplay failed" in str(e.value)
    assert not preflight.lock_path("01", tmp_path).is_file()


def test_lock_mystery_no_lock_when_lexicon_invalid(tmp_path):
    _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=False)
    with pytest.raises(SystemExit) as e:
        preflight.cmd_lock_mystery("01", repo_root=tmp_path)
    assert "lexicon" in str(e.value)
    assert not preflight.lock_path("01", tmp_path).is_file()


def test_lock_mystery_no_lock_when_canon_core_missing(tmp_path):
    _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=True)
    (tmp_path / "series/continuity/canon-core.md").unlink()
    with pytest.raises(SystemExit) as e:
        preflight.cmd_lock_mystery("01", repo_root=tmp_path)
    assert "canon-core" in str(e.value)
    assert not preflight.lock_path("01", tmp_path).is_file()


def test_lock_mystery_no_lock_when_culprit_unresolvable(tmp_path):
    led = _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=True)
    # remove margaret's entity so existence resolution blocks.
    (tmp_path / "series/continuity/characters/margaret.md").unlink()
    with pytest.raises(SystemExit) as e:
        preflight.cmd_lock_mystery("01", repo_root=tmp_path)
    assert "culprit id 'margaret'" in str(e.value)
    assert not preflight.lock_path("01", tmp_path).is_file()


def _make_book(root, book="01", *, populated=True, locked=True, run_config=True):
    wd = root / "series/whodunit"
    wd.mkdir(parents=True, exist_ok=True)
    led = wd / f"book-{book}.yaml"
    led.write_text("book: '01'\nculprit: margaret\n" if populated else "", encoding="utf-8")
    if locked:
        ld = root / ".penny/locks"
        ld.mkdir(parents=True, exist_ok=True)
        (ld / f"book-{book}.mystery.lock").write_text("ok\n", encoding="utf-8")
    if run_config:
        _make_run_config(root, drafting="claude-opus", final_read="codex")
    return led


def test_draft_passes_when_populated_and_locked(tmp_path):
    _make_book(tmp_path, populated=True, locked=True)
    assert preflight.cmd_draft("01", "01", repo_root=tmp_path) == 0


def test_draft_fails_without_lock(tmp_path):
    _make_book(tmp_path, populated=True, locked=False)
    with pytest.raises(SystemExit) as e:
        preflight.cmd_draft("01", "01", repo_root=tmp_path)
    assert "no lock" in str(e.value)


def test_draft_fails_without_ledger(tmp_path):
    (tmp_path / "series/whodunit").mkdir(parents=True, exist_ok=True)
    with pytest.raises(SystemExit) as e:
        preflight.cmd_draft("01", "01", repo_root=tmp_path)
    assert "no ledger" in str(e.value)


def test_draft_fails_when_ledger_unpopulated(tmp_path):
    _make_book(tmp_path, populated=False, locked=True)
    with pytest.raises(SystemExit) as e:
        preflight.cmd_draft("01", "01", repo_root=tmp_path)
    assert "unpopulated" in str(e.value)


# The review panel is only worth running on a model that did not write the prose.
# The inspector agents carry no `model:` frontmatter, so an unrouted panel silently
# inherits the drafting session and grades its own work — a PASS that means nothing.
# Caught here, before a word is drafted, rather than at the gate.

def test_draft_fails_when_inspector_model_equals_drafting_model(tmp_path):
    _make_book(tmp_path, populated=True, locked=True, run_config=False)
    _make_run_config(tmp_path, drafting="claude-opus", final_read="codex",
                     inspector="claude-opus")
    with pytest.raises(SystemExit) as e:
        preflight.cmd_draft("01", "01", repo_root=tmp_path)
    assert "inspector_model equals drafting_model" in str(e.value)


def test_draft_fails_when_inspector_model_absent(tmp_path):
    _make_book(tmp_path, populated=True, locked=True, run_config=False)
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config/run-config.md").write_text(
        "```yaml\ndrafting_model: claude-opus\nfinal_read_model: codex\n```\n",
        encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        preflight.cmd_draft("01", "01", repo_root=tmp_path)
    assert "inspector_model" in str(e.value)


def test_draft_fails_without_run_config(tmp_path):
    _make_book(tmp_path, populated=True, locked=True, run_config=False)
    with pytest.raises(SystemExit) as e:
        preflight.cmd_draft("01", "01", repo_root=tmp_path)
    assert "run-config" in str(e.value)


def _make_run_config(root, *, drafting, final_read, inspector="claude-sonnet"):
    cfg = root / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "run-config.md").write_text(
        "# fixture run-config\n\n```yaml\n"
        f"drafting_model:   {drafting}\n"
        f"inspector_model:  {inspector}\n"
        f"final_read_model: {final_read}\n"
        "```\n",
        encoding="utf-8",
    )


def _make_chapter(root, book, ch, drafted_by):
    d = root / "output" / f"book-{book}" / "chapters"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"ch-{ch}.draft.md").write_text(
        f"---\ndrafted_by: {drafted_by}\n---\nprose\n", encoding="utf-8")


def _make_final_read(root, book, read_by):
    d = root / "output" / f"book-{book}"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"book-{book}.final-read.md").write_text(
        f"---\nread_by: {read_by}\n---\nholistic read\n", encoding="utf-8")


def test_assemble_green(tmp_path):
    _make_run_config(tmp_path, drafting="claude-opus", final_read="codex")
    _make_chapter(tmp_path, "01", "01", "claude-opus")
    _make_final_read(tmp_path, "01", "codex")
    assert preflight.cmd_assemble("01", repo_root=tmp_path) == 0


def test_assemble_config_invariant_fails_before_stamps(tmp_path):
    _make_run_config(tmp_path, drafting="claude-opus", final_read="claude-opus")
    # no chapters at all — must still fail on the config compare
    with pytest.raises(SystemExit) as e:
        preflight.cmd_assemble("01", repo_root=tmp_path)
    assert "equals drafting_model" in str(e.value)


def test_assemble_drift_configured_final_reader_drafted(tmp_path):
    _make_run_config(tmp_path, drafting="claude-opus", final_read="codex")
    _make_chapter(tmp_path, "01", "01", "claude-opus")
    _make_chapter(tmp_path, "01", "02", "codex")  # codex drafted ch-02 — config lies
    with pytest.raises(SystemExit) as e:
        preflight.cmd_assemble("01", repo_root=tmp_path)
    assert "configured final_read_model 'codex'" in str(e.value)


def test_assemble_read_by_collides_with_drafter(tmp_path):
    _make_run_config(tmp_path, drafting="claude-opus", final_read="codex")
    _make_chapter(tmp_path, "01", "01", "claude-opus")
    _make_final_read(tmp_path, "01", "claude-opus")  # final read done by a drafter
    with pytest.raises(SystemExit) as e:
        preflight.cmd_assemble("01", repo_root=tmp_path)
    assert "final-read model 'claude-opus'" in str(e.value)


def _make_gate(root, book, ch, verdict):
    d = root / "output" / f"book-{book}" / "chapters"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"ch-{ch}.gate.md").write_text(
        f"---\nproducer: review_gate.py\nkind: gate-summary\n"
        f"target: book-{book}/ch-{ch}\ngate: {verdict}\nblocking_count: 0\n"
        f"schema: penny-verdict/1\n---\n\n- {verdict}: 0 blocking issue(s)\n",
        encoding="utf-8",
    )


def test_finalize_passes_on_passing_gate(tmp_path):   # REPLACES the old same-named test
    _make_gate(tmp_path, "01", "07", "PASS")
    _clear_for(tmp_path, "01", "07")
    assert preflight.cmd_finalize("01", "07", repo_root=tmp_path) == 0


def test_finalize_blocks_on_held_gate(tmp_path):
    _make_gate(tmp_path, "01", "07", "HOLD")
    with pytest.raises(SystemExit) as e:
        preflight.cmd_finalize("01", "07", repo_root=tmp_path)
    assert "did not pass" in str(e.value)


def test_finalize_blocks_when_gate_missing(tmp_path):
    with pytest.raises(SystemExit) as e:
        preflight.cmd_finalize("01", "07", repo_root=tmp_path)
    assert "no gate" in str(e.value)


def test_finalize_blocks_without_dev_clearance(tmp_path):
    _make_gate(tmp_path, "01", "07", "PASS")
    _write_draft(tmp_path, "01", "07")          # gate PASS + draft, but never cleared
    with pytest.raises(SystemExit) as e:
        preflight.cmd_finalize("01", "07", repo_root=tmp_path)
    assert "developmental clearance" in str(e.value)


def test_finalize_blocks_on_stale_dev_clearance(tmp_path):
    _make_gate(tmp_path, "01", "07", "PASS")
    _clear_for(tmp_path, "01", "07", body="original\n")
    _write_draft(tmp_path, "01", "07", body="REVISED after clearance\n")  # hash now differs
    with pytest.raises(SystemExit) as e:
        preflight.cmd_finalize("01", "07", repo_root=tmp_path)
    assert "stale" in str(e.value)


# ---------------------------------------------------------------------------
# approve-book tests
# ---------------------------------------------------------------------------
from scripts import assemble_book, revision_priority


def _approvable(tmp_path, *, read_by="codex", standalone="yes",
                with_report=True, with_manuscript=True):
    """Build a book-99 tree that approve-book should accept."""
    book = tmp_path / "output" / "book-99"
    (book / "chapters").mkdir(parents=True, exist_ok=True)
    if with_manuscript:
        assemble_book.manuscript_path("99", tmp_path).write_text(
            "---\nschema: penny-manuscript/1\nbook: 99\nchapters: 1\n"
            "drafted_by: [claude-opus]\nassembled_at: 2026-06-21T00:00:00+00:00\n---\n\n"
            "# Chapter 1\n\nprose\n", encoding="utf-8")
    assemble_book.final_read_path("99", tmp_path).write_text(
        f"---\nschema: penny-final-read/1\nread_by: {read_by}\n"
        f"standalone: {standalone}\nmystery_resolved: yes\nthread_left_open: yes\n---\n"
        "## Holistic verdict\nGood.\n", encoding="utf-8")
    if with_report:
        revision_priority.report_path("99", tmp_path).parent.mkdir(parents=True, exist_ok=True)
        revision_priority.report_path("99", tmp_path).write_text(
            "---\nschema: penny-revision-priority/1\nescalations: 0\n---\n", encoding="utf-8")


def test_approve_book_mints_cert_when_green(tmp_path):
    _approvable(tmp_path)
    assert preflight.cmd_approve_book("99", repo_root=tmp_path) == 0
    cert = tmp_path / ".penny/locks/book-99.approved"
    assert cert.is_file()


def test_approve_book_fails_without_manuscript(tmp_path):
    _approvable(tmp_path, with_manuscript=False)
    with pytest.raises(SystemExit) as e:
        preflight.cmd_approve_book("99", repo_root=tmp_path)
    assert "no manuscript" in str(e.value)
    assert not (tmp_path / ".penny/locks/book-99.approved").exists()


def test_approve_book_fails_on_hedged_final_read(tmp_path):
    _approvable(tmp_path, standalone="mostly")
    with pytest.raises(SystemExit) as e:
        preflight.cmd_approve_book("99", repo_root=tmp_path)
    assert "standalone" in str(e.value)
    assert not (tmp_path / ".penny/locks/book-99.approved").exists()


def test_approve_book_fails_when_read_by_drafted(tmp_path):
    _approvable(tmp_path, read_by="claude-opus")     # drafted_by is [claude-opus]
    with pytest.raises(SystemExit) as e:
        preflight.cmd_approve_book("99", repo_root=tmp_path)
    assert "appears in drafted_by" in str(e.value)
    assert not (tmp_path / ".penny/locks/book-99.approved").exists()


def test_approve_book_fails_without_report(tmp_path):
    _approvable(tmp_path, with_report=False)
    with pytest.raises(SystemExit) as e:
        preflight.cmd_approve_book("99", repo_root=tmp_path)
    assert "revision-priority" in str(e.value)
    assert not (tmp_path / ".penny/locks/book-99.approved").exists()


# ---------------------------------------------------------------------------
# draft sha256 + dev path helpers
# ---------------------------------------------------------------------------

def _write_draft(root, book, ch, body="prose\n"):
    d = root / "output" / f"book-{book}" / "chapters"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"ch-{ch}.draft.md"
    p.write_text(body, encoding="utf-8")
    return p


def test_draft_sha256_matches_file_bytes(tmp_path):
    p = _write_draft(tmp_path, "01", "07", body="hello draft\n")
    expected = hashlib.sha256(p.read_bytes()).hexdigest()
    assert preflight.draft_sha256("01", "07", repo_root=tmp_path) == expected


def test_draft_sha256_fails_when_draft_missing(tmp_path):
    with pytest.raises(SystemExit) as e:
        preflight.draft_sha256("01", "07", repo_root=tmp_path)
    assert "no draft" in str(e.value)


def test_dev_path_helpers_shape(tmp_path):
    rep = preflight.dev_report_path("01", "07", tmp_path)
    cert = preflight.dev_clear_path("01", "07", tmp_path)
    assert rep.name == "developmental-edit.md"
    assert rep.parent.name == "ch-07.reviews"
    assert cert.name == "book-01.ch-07.dev-clear"


# ---------------------------------------------------------------------------
# clear-dev tests
# ---------------------------------------------------------------------------

def _write_dev_report(root, book, ch, reviewed_sha, *, score=3):
    rep = preflight.dev_report_path(book, ch, root)
    rep.parent.mkdir(parents=True, exist_ok=True)
    rep.write_text(
        f"---\nproducer: developmental-editor\nkind: developmental\n"
        f"target: book-{book}/ch-{ch}\nschema: penny-verdict/1\nscore: {score}\n"
        f"reviewed_draft_sha256: {reviewed_sha}\n---\n\n- setting grounding thin\n",
        encoding="utf-8",
    )
    return rep


def _clear_for(root, book, ch, body="prose\n"):
    """Draft + dev report + minted clearance, all hash-consistent."""
    _write_draft(root, book, ch, body=body)
    sha = preflight.draft_sha256(book, ch, repo_root=root)
    _write_dev_report(root, book, ch, sha)
    assert preflight.cmd_clear_dev(book, ch, repo_root=root) == 0


def test_clear_dev_mints_cert_when_hash_matches(tmp_path):
    _write_draft(tmp_path, "01", "07", body="reviewed body\n")
    sha = preflight.draft_sha256("01", "07", repo_root=tmp_path)
    _write_dev_report(tmp_path, "01", "07", sha)
    assert preflight.cmd_clear_dev("01", "07", repo_root=tmp_path) == 0
    cert = preflight.dev_clear_path("01", "07", tmp_path)
    assert cert.is_file()
    from scripts.penny_meta import parse_frontmatter
    assert parse_frontmatter(cert.read_text(encoding="utf-8"))["cleared_draft_sha256"] == sha


def test_clear_dev_fails_without_report(tmp_path):
    _write_draft(tmp_path, "01", "07")
    with pytest.raises(SystemExit) as e:
        preflight.cmd_clear_dev("01", "07", repo_root=tmp_path)
    assert "no developmental read" in str(e.value)
    assert not preflight.dev_clear_path("01", "07", tmp_path).exists()


def test_clear_dev_fails_on_stale_report(tmp_path):
    _write_dev_report(tmp_path, "01", "07", "deadbeef")          # report for an old draft
    _write_draft(tmp_path, "01", "07", body="a DIFFERENT body\n")  # draft has since changed
    with pytest.raises(SystemExit) as e:
        preflight.cmd_clear_dev("01", "07", repo_root=tmp_path)
    assert "stale" in str(e.value)
    assert not preflight.dev_clear_path("01", "07", tmp_path).exists()


def test_clear_dev_fails_when_report_missing_sha256_key(tmp_path):
    """Report exists but lacks reviewed_draft_sha256 frontmatter — must fail."""
    _write_draft(tmp_path, "01", "07", body="some prose\n")
    rep = preflight.dev_report_path("01", "07", tmp_path)
    rep.parent.mkdir(parents=True, exist_ok=True)
    # write a dev report WITHOUT reviewed_draft_sha256
    rep.write_text(
        "---\nproducer: developmental-editor\nkind: developmental\n"
        "target: book-01/ch-07\nschema: penny-verdict/1\nscore: 3\n---\n"
        "\n- setting grounding thin\n",
        encoding="utf-8",
    )
    with pytest.raises(SystemExit) as e:
        preflight.cmd_clear_dev("01", "07", repo_root=tmp_path)
    assert "missing reviewed_draft_sha256" in str(e.value)
    assert not preflight.dev_clear_path("01", "07", tmp_path).exists()


WIRED_BAD = SRC / "tests/fixtures/outlines/wired-orphan.md"


def _add_wired_skeleton(tmp_path, fixture):
    d = tmp_path / "input/book-01"
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy(fixture, d / "outline-skeleton.md")


def test_lock_refused_on_unwaived_tension_finding(tmp_path):
    _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=True)
    _add_wired_skeleton(tmp_path, WIRED_BAD)
    with pytest.raises(SystemExit):
        preflight.cmd_lock_mystery("01", repo_root=tmp_path)
    assert not preflight.lock_path("01", tmp_path).is_file()


def test_waived_finding_locks_and_records_reason(tmp_path):
    _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=True)
    _add_wired_skeleton(tmp_path, WIRED_BAD)
    assert preflight.cmd_lock_mystery(
        "01", repo_root=tmp_path,
        waivers=['orphan-chapter:ch2 gap is the designed time-skip']) == 0
    body = preflight.lock_path("01", tmp_path).read_text(encoding="utf-8")
    assert "validated: fairplay+lexicon+tension" in body
    assert "waived: orphan-chapter — ch2 gap is the designed time-skip" in body


# --- FINAL REVIEW FINDING 5: with a declared genre, lock-mystery now
# resolves the beat sheet THROUGH genre.yaml and actually runs the
# curve/beat checks (dead-stretch, starved-thread, off-mark-beat), not just
# the graph checks. -----------------------------------------------------

def test_lock_refused_on_unwaived_curve_finding_when_genre_declared(tmp_path):
    _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=True)
    shutil.copy(FIXTURE / "series.yaml", tmp_path / "series.yaml")
    _add_wired_skeleton(tmp_path, SRC / "tests/fixtures/outlines/wired-starved-thread.md")
    with pytest.raises(SystemExit) as e:
        preflight.cmd_lock_mystery("01", repo_root=tmp_path)
    assert "starved-thread" in str(e.value)
    assert not preflight.lock_path("01", tmp_path).is_file()


def test_unwired_book_locks_exactly_as_before(tmp_path):
    _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=True)
    assert preflight.cmd_lock_mystery("01", repo_root=tmp_path) == 0
    body = preflight.lock_path("01", tmp_path).read_text(encoding="utf-8")
    assert "validated: fairplay+lexicon\n" in body


def test_malformed_waiver_fails_loud(tmp_path):
    _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=True)
    with pytest.raises(SystemExit):
        preflight.cmd_lock_mystery("01", repo_root=tmp_path, waivers=["no-reason"])


# --- FINAL REVIEW FINDING 9: the phantom-waiver note must print regardless
# of whether the outline is wired or even present — the cert never lies, but
# this is the one place an override currently passes silently. ------------

def test_phantom_waiver_note_prints_with_no_outline_at_all(tmp_path, capsys):
    _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=True)
    # no outline-skeleton.md / outline.md at all -> outline is None
    assert preflight.cmd_lock_mystery(
        "01", repo_root=tmp_path,
        waivers=["dead-stretch:never fires, no outline exists"]) == 0
    out = capsys.readouterr().out
    assert "waiver for 'dead-stretch' matched no finding; not recorded" in out


def test_phantom_waiver_note_prints_when_outline_present_but_unwired(tmp_path, capsys):
    _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=True)
    d = tmp_path / "input/book-01"
    d.mkdir(parents=True, exist_ok=True)
    (d / "outline-skeleton.md").write_text(
        "---\nbook: 01\ntotal_chapters: 1\n---\n\n## Chapter 01\nNo wiring here.\n",
        encoding="utf-8")
    assert preflight.cmd_lock_mystery(
        "01", repo_root=tmp_path,
        waivers=["dead-stretch:never fires, book is unwired"]) == 0
    out = capsys.readouterr().out
    assert "waiver for 'dead-stretch' matched no finding; not recorded" in out


def test_draft_fails_on_a_stale_brief(tmp_path):
    _make_book(tmp_path, populated=True, locked=True)
    briefs = tmp_path / "input/book-01/briefs"
    briefs.mkdir(parents=True, exist_ok=True)
    (tmp_path / "input/book-01/outline.md").write_text("## Chapter 01 — X\n", encoding="utf-8")
    (briefs / "ch-01.md").write_text(
        "---\nbuilt_from_outline: deadbeef\n---\n# brief\n", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        preflight.cmd_draft("01", "01", repo_root=tmp_path)
    assert "stale brief" in str(e.value)


def test_draft_passes_when_no_briefs_exist_at_all(tmp_path):
    # Book 1 has no briefs and must keep drafting exactly as before.
    _make_book(tmp_path, populated=True, locked=True)
    assert preflight.cmd_draft("01", "01", repo_root=tmp_path) == 0


# --- Fix wave: cmd_lock_mystery now resolves + threads profile_path, but
# nothing exercised that path directly — a regression in the
# `not profile_path.is_file()` normalization would pass the whole suite
# silently. Mirrors test_waived_finding_locks_and_records_reason /
# test_lock_refused_on_unwaived_curve_finding_when_genre_declared. ----------

OVERLOAD_PROFILE = SRC / "tests/fixtures/length-profile.md"


def _overloaded_wired_outline() -> str:
    # Chapter 01 carries the identical overload shape as
    # tests/test_tension_check.py's own overload fixture (1 anchor + 20
    # connective scenes in the default band). Chapter 02 exists purely to
    # close/carry the questions chapter 01 opens, cleanly, so the ONLY
    # tension finding this outline produces is overloaded-chapter — nothing
    # else must fire, or waiving overloaded-chapter alone wouldn't be enough
    # to lock.
    scenes = "\n".join(
        f"### Scene {i} — Stop {i}\n\n**Weight:** connective\n\n**Beat flow:**\n\n1. A stop.\n"
        for i in range(2, 22))
    return (
        "---\nbook: 01\ntotal_chapters: 2\n---\n\n"
        "## Chapter 01 — Too Much\n\n"
        "- **Because:** opening\n"
        "- **Opens:** q-a — a question.\n"
        "- **Hook:** q-a — a hook.\n\n"
        "### Scene 1 — The Anchor\n\n**Weight:** anchor\n\n**Beat flow:**\n\n1. The turn.\n\n"
        + scenes +
        "\n## Chapter 02 — Cooldown\n\n"
        "- **Because:** ch 01 — settles the pace.\n"
        "- **Opens:** q-b — a second question.\n"
        "- **Closes:** q-a\n"
        "- **Carries:** q-b\n"
        "- **Hook:** q-b — a hook.\n"
    )


def _scaffold_overloadable(tmp_path):
    _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=True)
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    shutil.copy(OVERLOAD_PROFILE, tmp_path / "config/length-profile.md")
    d = tmp_path / "input/book-01"
    d.mkdir(parents=True, exist_ok=True)
    (d / "outline-skeleton.md").write_text(_overloaded_wired_outline(), encoding="utf-8")


def test_lock_refused_on_unwaived_overloaded_chapter(tmp_path):
    _scaffold_overloadable(tmp_path)
    with pytest.raises(SystemExit) as e:
        preflight.cmd_lock_mystery("01", repo_root=tmp_path)
    assert "overloaded-chapter" in str(e.value)
    assert not preflight.lock_path("01", tmp_path).is_file()


def test_waived_overloaded_chapter_locks_and_records_reason(tmp_path):
    _scaffold_overloadable(tmp_path)
    assert preflight.cmd_lock_mystery(
        "01", repo_root=tmp_path,
        waivers=['overloaded-chapter:ch 1 is deliberately dense; showrunner '
                 'accepts the length risk']) == 0
    body = preflight.lock_path("01", tmp_path).read_text(encoding="utf-8")
    assert "validated: fairplay+lexicon+tension" in body
    assert ("waived: overloaded-chapter — ch 1 is deliberately dense; showrunner "
            "accepts the length risk") in body


# --- FINAL REVIEW C1 + I4: the lock and the length profile ------------------
#
# C1: the live series' length-profile.md is the LEGACY format (a prose table +
# book_target_words — no band_*/weight_* keys). check_tension parsed it
# unconditionally, so /plot-book 02 -> lock-mystery raised a raw ValueError:
# a regression that made the live series unable to lock its next book.
#
# I4: weights are authored into the EXPANDED outline (input/book-NN/outline.md),
# which is where overloaded-chapter must therefore look — lock-mystery reads
# outline-skeleton.md for the wiring, and the skeleton has no scenes at all, so
# the ninth check was unreachable on the only path that produces weights.

LEGACY_PROFILE = SRC / "tests/fixtures/length-profile-legacy.md"
NEW_PROFILE = SRC / "tests/fixtures/length-profile.md"
WEIGHTED_OVERLOADED = SRC / "tests/fixtures/outlines/weighted-overloaded.md"
WIRED_CLEAN = SRC / "tests/fixtures/outlines/wired-clean.md"


def _add_profile(tmp_path, fixture):
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    shutil.copy(fixture, tmp_path / "config/length-profile.md")


def _add_expanded_outline(tmp_path, fixture):
    d = tmp_path / "input/book-01"
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy(fixture, d / "outline.md")


def test_legacy_length_profile_still_locks_a_wired_book(tmp_path):
    _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=True)
    _add_wired_skeleton(tmp_path, WIRED_CLEAN)
    _add_profile(tmp_path, LEGACY_PROFILE)
    assert preflight.cmd_lock_mystery("01", repo_root=tmp_path) == 0
    assert preflight.lock_path("01", tmp_path).is_file()


def test_legacy_length_profile_records_the_skipped_overload_check(tmp_path, capsys):
    _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=True)
    _add_wired_skeleton(tmp_path, WIRED_CLEAN)
    _add_expanded_outline(tmp_path, WEIGHTED_OVERLOADED)
    _add_profile(tmp_path, LEGACY_PROFILE)
    assert preflight.cmd_lock_mystery("01", repo_root=tmp_path) == 0
    body = preflight.lock_path("01", tmp_path).read_text(encoding="utf-8")
    assert "skipped: overloaded-chapter" in body, (
        "a certificate that stamps validated:...+tension while the overload check "
        "never ran is a certificate that lies")
    assert "band_default" in body


def test_overloaded_chapter_fires_at_the_lock_on_the_weighted_expanded_outline(tmp_path):
    _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=True)
    _add_wired_skeleton(tmp_path, WIRED_CLEAN)
    _add_expanded_outline(tmp_path, WEIGHTED_OVERLOADED)
    _add_profile(tmp_path, NEW_PROFILE)
    with pytest.raises(SystemExit) as e:
        preflight.cmd_lock_mystery("01", repo_root=tmp_path)
    assert "overloaded-chapter" in str(e.value)
    assert not preflight.lock_path("01", tmp_path).is_file()


def test_overloaded_chapter_is_waivable_at_the_lock(tmp_path):
    _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=True)
    _add_wired_skeleton(tmp_path, WIRED_CLEAN)
    _add_expanded_outline(tmp_path, WEIGHTED_OVERLOADED)
    _add_profile(tmp_path, NEW_PROFILE)
    assert preflight.cmd_lock_mystery(
        "01", repo_root=tmp_path,
        waivers=['overloaded-chapter:the day is meant to be relentless']) == 0
    body = preflight.lock_path("01", tmp_path).read_text(encoding="utf-8")
    assert "waived: overloaded-chapter — the day is meant to be relentless" in body
