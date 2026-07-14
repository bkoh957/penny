"""Deterministic pre-flight gates (Tier-3, structural). One tool, four subcommands:

    lock-mystery N   heavy: fairplay + lexicon --validate; sole writer of the lock.
    draft N CH       light: lock present + ledger populated; pure file check.
    assemble N       routing: final_read_model != drafting_model + set membership.
    finalize N CH    post-gate guard: chapter must have gate == PASS.

Gates never make an LLM judgment, so they survive Option-A's soft-gate weakness.
Every miss exits non-zero via `preflight: <named predicate>`.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import assemble_book, penny_paths, revision_priority
from scripts.fairplay_check import check_fairplay, load_fraction
from scripts.lexicon_check import load_lexicon, stage_drift, validate_lexicon
from scripts.penny_meta import load, parse_frontmatter, parse_yaml_blocks

REPO = Path(__file__).resolve().parents[1]


def _fail(predicate: str):
    sys.exit(f"preflight: {predicate}")


def _parse_waivers(raw) -> dict:
    """['check-id:reason', ...] -> {check-id: reason}. Both halves required."""
    out: dict[str, str] = {}
    for item in raw or []:
        check, _, reason = str(item).partition(":")
        if not check.strip() or not reason.strip():
            _fail(f'bad --waive {item!r}; expected check-id:"reason"')
        out[check.strip()] = reason.strip()
    return out


def _first_file(*paths):
    for p in paths:
        if p is not None and Path(p).is_file():
            return p
    return None


def ledger_path(book: str, repo_root) -> Path:
    return penny_paths.series_path(f"whodunit/book-{book}.yaml", root=repo_root)


def lock_path(book: str, repo_root) -> Path:
    return penny_paths.penny_path(f"locks/book-{book}.mystery.lock", root=repo_root)


def approved_path(book: str, repo_root) -> Path:
    return penny_paths.penny_path(f"locks/book-{book}.approved", root=repo_root)


def gate_path(book: str, chapter: str, repo_root) -> Path:
    return (penny_paths.output_path(f"book-{book}/chapters", root=repo_root)
            / f"ch-{chapter}.gate.md")


def draft_path(book: str, chapter: str, repo_root) -> Path:
    return (penny_paths.output_path(f"book-{book}/chapters", root=repo_root)
            / f"ch-{chapter}.draft.md")


def draft_sha256(book: str, chapter: str, *, repo_root=None) -> str:
    repo_root = Path(repo_root) if repo_root is not None else penny_paths.series_root()
    p = draft_path(book, chapter, repo_root)
    if not p.is_file():
        _fail(f"no draft for book {book} ch {chapter} ({p})")
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dev_report_path(book: str, chapter: str, repo_root) -> Path:
    return (penny_paths.output_path(f"book-{book}/chapters", root=repo_root)
            / f"ch-{chapter}.reviews" / "developmental-edit.md")


def dev_clear_path(book: str, chapter: str, repo_root) -> Path:
    return penny_paths.penny_path(f"locks/book-{book}.ch-{chapter}.dev-clear", root=repo_root)


def cmd_finalize(book: str, chapter: str, *, repo_root=None) -> int:
    repo_root = Path(repo_root) if repo_root is not None else penny_paths.series_root()
    gp = gate_path(book, chapter, repo_root)
    if not gp.is_file():
        _fail(f"no gate for book {book} ch {chapter} ({gp}) — run /review-chapter first")
    gate = parse_frontmatter(gp.read_text(encoding="utf-8")).get("gate")
    if gate != "PASS":
        _fail(f"chapter {book}/{chapter} did not pass the gate (gate: {gate}); "
              f"resolve the HOLD before finalizing")
    # second predicate: a fresh developmental clearance bound to THIS draft.
    cert = dev_clear_path(book, chapter, repo_root)
    if not cert.is_file():
        _fail(f"no developmental clearance for book {book} ch {chapter} — "
              f"run /review-chapter then `preflight clear-dev {book} {chapter}`")
    cleared = parse_frontmatter(cert.read_text(encoding="utf-8")).get("cleared_draft_sha256")
    current = draft_sha256(book, chapter, repo_root=repo_root)
    if cleared != current:
        _fail(f"developmental clearance is stale for book {book} ch {chapter} "
              f"(draft changed since clearance: cleared {str(cleared)[:12]} != "
              f"current {current[:12]}); revise then re-clear")
    return 0


def cmd_clear_dev(book: str, chapter: str, *, repo_root=None) -> int:
    repo_root = Path(repo_root) if repo_root is not None else penny_paths.series_root()
    rep = dev_report_path(book, chapter, repo_root)
    if not rep.is_file():
        _fail(f"no developmental read for book {book} ch {chapter} ({rep}) — "
              f"run /review-chapter first")
    reviewed = parse_frontmatter(rep.read_text(encoding="utf-8")).get("reviewed_draft_sha256")
    if not reviewed:
        _fail(f"developmental report missing reviewed_draft_sha256 ({rep})")
    current = draft_sha256(book, chapter, repo_root=repo_root)
    if reviewed != current:
        _fail(f"developmental report is stale for book {book} ch {chapter}: "
              f"reviewed {reviewed[:12]} != current draft {current[:12]}; re-run /review-chapter")
    # validated — mint the certificate (the LAST write).
    cert = dev_clear_path(book, chapter, repo_root)
    cert.parent.mkdir(parents=True, exist_ok=True)
    cert.write_text(
        f"---\nbook: {book}\nchapter: {chapter}\n"
        f"cleared_draft_sha256: {current}\n"
        f"cleared_at: {datetime.now(timezone.utc).isoformat()}\n---\n",
        encoding="utf-8",
    )
    return 0


def cmd_draft(book: str, chapter: str, *, repo_root=None, run_config=None) -> int:
    repo_root = Path(repo_root) if repo_root is not None else penny_paths.series_root()
    # Ledger reads go through brief_render.load_ledger — the one guarded entry
    # point every caller uses, so a malformed or unreadable ledger fails with
    # this module's own `preflight: <predicate>` form, never a raw traceback.
    from scripts.brief_render import load_ledger, stale_briefs
    led = ledger_path(book, repo_root)
    if not led.is_file():
        _fail(f"no ledger for book {book} ({led}) — run /plan-mystery {book}")
    try:
        data = load_ledger(led)
    except ValueError as e:
        _fail(str(e))
    if not data:
        _fail(f"ledger unpopulated for book {book} ({led})")
    if not lock_path(book, repo_root).is_file():
        _fail(f"no lock for book {book} — run /plan-mystery {book} to validate and lock")
    # The review panel must not be the drafter. The inspector agents declare no
    # `model:`, so an unrouted panel inherits the drafting session and grades its
    # own prose — a PASS that means nothing. Refuse before a word is written.
    run_config = run_config or penny_paths.config_path("run-config.md", root=repo_root)
    if not Path(run_config).is_file():
        _fail(f"no run-config ({run_config}) — the review panel cannot be routed")
    cfg = parse_yaml_blocks(load(run_config))
    drafting = cfg.get("drafting_model")
    inspector = cfg.get("inspector_model")
    if not drafting or not inspector:
        _fail("run-config missing drafting_model or inspector_model — the review "
              "panel would inherit the drafting model and grade its own prose")
    if inspector == drafting:
        _fail(f"inspector_model equals drafting_model ({inspector}) — the review "
              "panel would grade its own prose")
    # A brief built from a different outline (or whodunit ledger) is a lie
    # about what this chapter owes. No briefs at all is fine — that is book 1,
    # and it drafts from the raw section. An unreadable ledger, though, is a
    # real failure — caught here and reported through the same named-predicate
    # convention as every other preflight miss, never a raw traceback.
    try:
        stale = stale_briefs(book, repo_root)
    except ValueError as e:
        _fail(str(e))
    if chapter.zfill(2) in stale:
        _fail(f"stale brief for ch {chapter} — the outline or whodunit ledger changed "
              f"since it was built; re-run /build-briefs {book}")
    return 0


def _drafted_by_set(book: str, repo_root) -> set[str]:
    chapters = penny_paths.output_path(f"book-{book}/chapters", root=repo_root)
    stamps: set[str] = set()
    for ch in sorted(chapters.glob("ch-*.draft.md")):
        m = parse_frontmatter(ch.read_text(encoding="utf-8")).get("drafted_by")
        if isinstance(m, str) and m:
            stamps.add(m)
    return stamps


def _final_read_path(book: str, repo_root) -> Path:
    return penny_paths.output_path(f"book-{book}/book-{book}.final-read.md", root=repo_root)


def cmd_assemble(book: str, *, repo_root=None, run_config=None) -> int:
    repo_root = Path(repo_root) if repo_root is not None else penny_paths.series_root()
    run_config = run_config or penny_paths.config_path("run-config.md", root=repo_root)
    cfg = parse_yaml_blocks(load(run_config))
    drafting = cfg.get("drafting_model")
    final_read = cfg.get("final_read_model")
    if not drafting or not final_read:
        _fail("run-config missing drafting_model or final_read_model")
    # 1. config-invariant — fails before stamps matter.
    if final_read == drafting:
        _fail(f"final_read_model equals drafting_model ({final_read})")
    # 2. reality-check: the configured final reader must not be among drafters.
    drafted = _drafted_by_set(book, repo_root)
    if final_read in drafted:
        _fail(f"configured final_read_model '{final_read}' appears in "
              f"drafted_by set {sorted(drafted)}")
    # 3. the actual final-read artifact (if present): read_by must not be a drafter.
    fr = _final_read_path(book, repo_root)
    if fr.is_file():
        read_by = parse_frontmatter(fr.read_text(encoding="utf-8")).get("read_by")
        if not read_by:
            _fail(f"final-read artifact has no read_by stamp ({fr})")
        if read_by in drafted:
            _fail(f"final-read model '{read_by}' appears in "
                  f"drafted_by set {sorted(drafted)}")
    return 0


def cmd_approve_book(book: str, *, repo_root=None) -> int:
    repo_root = Path(repo_root) if repo_root is not None else penny_paths.series_root()
    man = assemble_book.manuscript_path(book, repo_root)
    if not man.is_file():
        _fail(f"no manuscript for book {book} ({man}) — run /assemble-book first")
    # final-read shape (reuses the validator; raises assemble_book: on a bad shape).
    assemble_book.validate_final_read(book, repo_root=repo_root)
    read_by = parse_frontmatter(
        assemble_book.final_read_path(book, repo_root).read_text(encoding="utf-8")
    ).get("read_by")
    drafted = parse_frontmatter(man.read_text(encoding="utf-8")).get("drafted_by")
    drafted = set(drafted) if isinstance(drafted, list) else {drafted} if drafted else set()
    if read_by in drafted:
        _fail(f"final-read model '{read_by}' appears in drafted_by set {sorted(drafted)}")
    report = revision_priority.report_path(book, repo_root)
    if not report.is_file():
        _fail(f"no revision-priority report for book {book} ({report})")
    # all preconditions green — mint the cert (the LAST write).
    cert = approved_path(book, repo_root)
    cert.parent.mkdir(parents=True, exist_ok=True)
    cert.write_text(
        f"book: {book}\napproved: final-read+revision-priority\n"
        f"approved_at: {datetime.now(timezone.utc).isoformat()}\n",
        encoding="utf-8",
    )
    return 0


def cmd_lock_mystery(book: str, *, repo_root=None, run_config=None, waivers=None) -> int:
    repo_root = Path(repo_root) if repo_root is not None else penny_paths.series_root()
    run_config = run_config or penny_paths.config_path("run-config.md", root=repo_root)
    led = ledger_path(book, repo_root)
    if not led.is_file():
        _fail(f"no ledger to lock for book {book} ({led})")
    # 1. fairplay: numeric fairness + character-id existence (BLOCKING gate).
    fraction = load_fraction(run_config)
    fp = check_fairplay(led, culprit_by_fraction=fraction, repo_root=repo_root)
    if fp["blocking"]:
        _fail("fairplay failed; lock NOT written:\n  - " + "\n  - ".join(fp["blocking"]))
    # 2. lexicon schema validation (+ stage drift).
    errors = validate_lexicon(load_lexicon(penny_paths.config_path("setting-pack/lexicon.yaml", root=repo_root)))
    canon = penny_paths.series_path("continuity/canon-core.md", root=repo_root)
    if not canon.is_file():
        _fail(f"no canon-core to validate stage drift ({canon})")
    drift = stage_drift(canon.read_text(encoding="utf-8"))
    if drift:
        errors.append(drift)
    if errors:
        _fail("lexicon --validate failed; lock NOT written:\n  - " + "\n  - ".join(errors))
    # 3. tension gate (plot-book workshop spec §6): only when the outline has wiring.
    from scripts import penny_genre
    from scripts.tension_check import check_tension
    waiver_map = _parse_waivers(waivers)
    outline = _first_file(
        repo_root / "input" / f"book-{book}" / "outline-skeleton.md",
        repo_root / "input" / f"book-{book}" / "outline.md")
    # FINAL REVIEW FINDING 5: resolve THROUGH genre.yaml's `beat_sheet:` key
    # (penny_genre.beat_sheet(), which is itself overlay-resolved and tolerant
    # of an undeclared genre) rather than a hardcoded "beat-sheet.yaml" — a
    # future genre pack naming its file differently must not silently lose
    # the curve/beat checks while still minting a lock that claims full
    # tension coverage.
    beat_sheet_path = penny_genre.beat_sheet(root=repo_root)
    if beat_sheet_path is not None and not beat_sheet_path.is_file():
        # config_path() always returns SOME path (falling back to the plugin
        # default location even when nothing exists there) — normalize the
        # nonexistent case to None so the note below fires correctly instead
        # of silently passing a dead path through to check_tension.
        beat_sheet_path = None
    # The engine ships no length-profile.md (series-authored) — same guard as
    # beat_sheet_path: config_path() always returns SOME path (falling back
    # to the plugin default location), so normalize a nonexistent one to
    # None. check_tension() itself no-ops the overloaded-chapter check when
    # profile_path is None or the file is absent — a series without one must
    # still lock.
    profile_path = penny_paths.config_path("length-profile.md", root=repo_root)
    if not profile_path.is_file():
        profile_path = None
    validated = "fairplay+lexicon"
    waived_lines: list[str] = []
    fired: set[str] = set()
    if outline is not None:
        tres = check_tension(
            outline,
            beat_sheet_path=beat_sheet_path,
            turning_points_path=_first_file(
                repo_root / "input" / f"book-{book}" / "plot" / "turning-points.md"),
            whodunit_path=led,
            profile_path=profile_path)
        if tres["wired"]:
            validated = "fairplay+lexicon+tension"
            if beat_sheet_path is None:
                # The `validated:` stamp must not claim more than actually
                # ran (FINDING 5): say so visibly when curve/beat checks were
                # skipped for lack of a resolvable beat sheet.
                print("lock-mystery: note — no beat sheet resolved; curve/beat "
                      "checks (dead-stretch, starved-thread, off-mark-beat) skipped")
            for f in tres["blocking"]:
                print(f"tension_check: {f}")
            unwaived = [f for f in tres["blocking"]
                        if f.split(":", 1)[0] not in waiver_map]
            if unwaived:
                _fail("tension failed; lock NOT written:\n  - " + "\n  - ".join(unwaived))
            fired = {f.split(":", 1)[0] for f in tres["blocking"]}
    # FINAL REVIEW FINDING 9: hoisted out of `if tres["wired"]` (and out of
    # `if outline is not None`, which has the same hole) — a waiver dictated
    # for a book that never reached wiring, or has no outline at all, must
    # still be reported as unrecorded rather than silently swallowed. `fired`
    # is simply empty in those cases, so every waiver correctly reports
    # "not recorded" without any wired-outline-specific branching here.
    for check, reason in sorted(waiver_map.items()):
        if check in fired:
            waived_lines.append(f"waived: {check} — {reason}")
        else:
            print(f"lock-mystery: note — waiver for '{check}' matched no finding; not recorded")
    # 4. all passed — mint the certificate (the LAST write).
    lp = lock_path(book, repo_root)
    lp.parent.mkdir(parents=True, exist_ok=True)
    lp.write_text(
        f"book: {book}\nvalidated: {validated}\n"
        f"locked_at: {datetime.now(timezone.utc).isoformat()}\n"
        + "".join(line + "\n" for line in waived_lines),
        encoding="utf-8",
    )
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Penny deterministic pre-flight gates.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_draft = sub.add_parser("draft", help="draft-time gate")
    p_draft.add_argument("book")
    p_draft.add_argument("chapter")
    p_asm = sub.add_parser("assemble", help="cross-model routing guard")
    p_asm.add_argument("book")
    p_app = sub.add_parser("approve-book", help="precondition gate + mint .approved cert")
    p_app.add_argument("book")
    p_lock = sub.add_parser("lock-mystery", help="validate + write the lock (last)")
    p_lock.add_argument("book")
    p_lock.add_argument("--waive", action="append", default=[], metavar='CHECK:"REASON"')
    p_fin = sub.add_parser("finalize", help="post-gate guard: chapter must have PASSed")
    p_fin.add_argument("book")
    p_fin.add_argument("chapter")
    p_clear = sub.add_parser("clear-dev", help="mint dev-clearance cert (draft-hash bound)")
    p_clear.add_argument("book")
    p_clear.add_argument("chapter")
    args = ap.parse_args(argv)
    if args.cmd == "draft":
        return cmd_draft(args.book, args.chapter)
    if args.cmd == "assemble":
        return cmd_assemble(args.book)
    if args.cmd == "approve-book":
        return cmd_approve_book(args.book)
    if args.cmd == "lock-mystery":
        return cmd_lock_mystery(args.book, waivers=args.waive)
    if args.cmd == "finalize":
        return cmd_finalize(args.book, args.chapter)
    if args.cmd == "clear-dev":
        return cmd_clear_dev(args.book, args.chapter)
    ap.error(f"unknown command {args.cmd!r}")  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())
