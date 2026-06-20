"""Deterministic pre-flight gates (Tier-3, structural). One tool, three subcommands:

    lock-mystery N   heavy: fairplay + lexicon --validate; sole writer of the lock.
    draft N CH       light: lock present + ledger populated; pure file check.
    assemble N       routing: final_read_model != drafting_model + set membership.

Gates never make an LLM judgment, so they survive Option-A's soft-gate weakness.
Every miss exits non-zero via `preflight: <named predicate>`.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml

REPO = Path(__file__).resolve().parents[1]


def _fail(predicate: str):
    sys.exit(f"preflight: {predicate}")


def ledger_path(book: str, repo_root) -> Path:
    return Path(repo_root) / "series/whodunit" / f"book-{book}.yaml"


def lock_path(book: str, repo_root) -> Path:
    return Path(repo_root) / ".penny/locks" / f"book-{book}.mystery.lock"


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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Penny deterministic pre-flight gates.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_draft = sub.add_parser("draft", help="draft-time gate")
    p_draft.add_argument("book")
    p_draft.add_argument("chapter")
    args = ap.parse_args(argv)
    if args.cmd == "draft":
        return cmd_draft(args.book, args.chapter)
    ap.error(f"unknown command {args.cmd!r}")  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())
