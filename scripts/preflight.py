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
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml

from scripts.fairplay_check import check_fairplay, load_fraction
from scripts.lexicon_check import load_lexicon, stage_drift, validate_lexicon
from scripts.penny_meta import load, parse_frontmatter, parse_yaml_blocks

REPO = Path(__file__).resolve().parents[1]


def _fail(predicate: str):
    sys.exit(f"preflight: {predicate}")


def ledger_path(book: str, repo_root) -> Path:
    return Path(repo_root) / "series/whodunit" / f"book-{book}.yaml"


def lock_path(book: str, repo_root) -> Path:
    return Path(repo_root) / ".penny/locks" / f"book-{book}.mystery.lock"


def gate_path(book: str, chapter: str, repo_root) -> Path:
    return (Path(repo_root) / "output" / f"book-{book}" / "chapters"
            / f"ch-{chapter}.gate.md")


def cmd_finalize(book: str, chapter: str, *, repo_root=REPO) -> int:
    gp = gate_path(book, chapter, repo_root)
    if not gp.is_file():
        _fail(f"no gate for book {book} ch {chapter} ({gp}) — run /review-chapter first")
    gate = parse_frontmatter(gp.read_text(encoding="utf-8")).get("gate")
    if gate != "PASS":
        _fail(f"chapter {book}/{chapter} did not pass the gate (gate: {gate}); "
              f"resolve the HOLD before finalizing")
    return 0


def cmd_draft(book: str, chapter: str, *, repo_root=REPO) -> int:
    led = ledger_path(book, repo_root)
    if not led.is_file():
        _fail(f"no ledger for book {book} ({led}) — run /plan-mystery {book}")
    data = yaml.safe_load(led.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data:
        _fail(f"ledger unpopulated for book {book} ({led})")
    if not lock_path(book, repo_root).is_file():
        _fail(f"no lock for book {book} — run /plan-mystery {book} to validate and lock")
    return 0


def _drafted_by_set(book: str, repo_root) -> set[str]:
    chapters = Path(repo_root) / "output" / f"book-{book}" / "chapters"
    stamps: set[str] = set()
    for ch in sorted(chapters.glob("ch-*.draft.md")):
        m = parse_frontmatter(ch.read_text(encoding="utf-8")).get("drafted_by")
        if isinstance(m, str) and m:
            stamps.add(m)
    return stamps


def _final_read_path(book: str, repo_root) -> Path:
    return Path(repo_root) / "output" / f"book-{book}" / f"book-{book}.final-read.md"


def cmd_assemble(book: str, *, repo_root=REPO, run_config=None) -> int:
    run_config = run_config or (Path(repo_root) / "config/run-config.md")
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


def cmd_lock_mystery(book: str, *, repo_root=REPO, run_config=None) -> int:
    repo_root = Path(repo_root)
    run_config = run_config or (repo_root / "config/run-config.md")
    led = ledger_path(book, repo_root)
    if not led.is_file():
        _fail(f"no ledger to lock for book {book} ({led})")
    # 1. fairplay: numeric fairness + character-id existence (BLOCKING gate).
    fraction = load_fraction(run_config)
    fp = check_fairplay(led, culprit_by_fraction=fraction, repo_root=repo_root)
    if fp["blocking"]:
        _fail("fairplay failed; lock NOT written:\n  - " + "\n  - ".join(fp["blocking"]))
    # 2. lexicon schema validation (+ stage drift).
    errors = validate_lexicon(load_lexicon(repo_root / "config/setting-pack/lexicon.yaml"))
    canon = repo_root / "series/continuity/canon-core.md"
    if not canon.is_file():
        _fail(f"no canon-core to validate stage drift ({canon})")
    drift = stage_drift(canon.read_text(encoding="utf-8"))
    if drift:
        errors.append(drift)
    if errors:
        _fail("lexicon --validate failed; lock NOT written:\n  - " + "\n  - ".join(errors))
    # 3. both passed — mint the certificate (the LAST write).
    lp = lock_path(book, repo_root)
    lp.parent.mkdir(parents=True, exist_ok=True)
    lp.write_text(
        f"book: {book}\nvalidated: fairplay+lexicon\n"
        f"locked_at: {datetime.now(timezone.utc).isoformat()}\n",
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
    p_lock = sub.add_parser("lock-mystery", help="validate + write the lock (last)")
    p_lock.add_argument("book")
    p_fin = sub.add_parser("finalize", help="post-gate guard: chapter must have PASSed")
    p_fin.add_argument("book")
    p_fin.add_argument("chapter")
    args = ap.parse_args(argv)
    if args.cmd == "draft":
        return cmd_draft(args.book, args.chapter)
    if args.cmd == "assemble":
        return cmd_assemble(args.book)
    if args.cmd == "lock-mystery":
        return cmd_lock_mystery(args.book)
    if args.cmd == "finalize":
        return cmd_finalize(args.book, args.chapter)
    ap.error(f"unknown command {args.cmd!r}")  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())
