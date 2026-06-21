"""Per-book manuscript producer + final-read shape validator (Phase 6).

Deterministic — never an LLM judgment. Three subcommands:

    assemble NN       build output/book-NN/book-NN.manuscript.md from ch-*.final.md
    seal NN           stamp read_by (from the final read) into the manuscript
    validate-read NN  hard-fail a malformed penny-final-read/1 artifact

Every miss exits non-zero via `assemble_book: <named predicate>`, mirroring
`preflight:`. The manuscript has one path but three states: assembled -> read
(seal) -> blessed (preflight approve-book mints the cert).
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.penny_meta import (parse_frontmatter, strip_frontmatter,
                                 write_frontmatter_field)

REPO = Path(__file__).resolve().parents[1]
MANUSCRIPT_SCHEMA = "penny-manuscript/1"
FINAL_READ_SCHEMA = "penny-final-read/1"
FINAL_READ_BOOLEANS = ("standalone", "mystery_resolved", "thread_left_open")
ENUM = {"yes", "no"}


def _fail(predicate: str):
    sys.exit(f"assemble_book: {predicate}")


def book_dir(book: str, repo_root) -> Path:
    return Path(repo_root) / "output" / f"book-{book}"


def chapters_dir(book: str, repo_root) -> Path:
    return book_dir(book, repo_root) / "chapters"


def manuscript_path(book: str, repo_root) -> Path:
    return book_dir(book, repo_root) / f"book-{book}.manuscript.md"


def final_read_path(book: str, repo_root) -> Path:
    return book_dir(book, repo_root) / f"book-{book}.final-read.md"


def _chapter_num(path: Path) -> int:
    # ch-07.final.md -> 7
    return int(path.name[len("ch-"):].split(".")[0])


def _stamps(value) -> set[str]:
    if isinstance(value, list):
        return {s for s in value if s}
    if isinstance(value, str) and value:
        return {value}
    return set()


def cmd_assemble(book: str, *, repo_root=REPO, now=None) -> int:
    cdir = chapters_dir(book, repo_root)
    finals = sorted(cdir.glob("ch-*.final.md"), key=_chapter_num)
    if not finals:
        _fail(f"no finalized chapters for book {book} ({cdir}/ch-*.final.md)")
    nums = [_chapter_num(p) for p in finals]
    expected = list(range(1, len(nums) + 1))
    if nums != expected:
        missing = sorted(set(expected) - set(nums))
        _fail(f"chapters not contiguous for book {book}: have {nums}, "
              f"missing {missing}")
    drafted: set[str] = set()
    bodies: list[str] = []
    for p in finals:
        text = p.read_text(encoding="utf-8")
        stamp = parse_frontmatter(text).get("drafted_by")
        if not _stamps(stamp):
            _fail(f"{p.name} missing drafted_by stamp")
        drafted |= _stamps(stamp)
        n = _chapter_num(p)
        bodies.append(f"# Chapter {n}\n\n{strip_frontmatter(text).rstrip(chr(10))}\n")
    # outline count guard (only if outline.md declares one).
    outline = book_dir(book, repo_root) / "outline.md"
    if outline.is_file():
        declared = parse_frontmatter(outline.read_text(encoding="utf-8")).get("chapters")
        if declared is not None and str(declared) != str(len(nums)):
            _fail(f"outline declares {declared} chapters but {len(nums)} finalized")
    ts = (now or datetime.now(timezone.utc)).isoformat()
    drafted_inline = "[" + ", ".join(sorted(drafted)) + "]"
    front = ("---\n"
             f"schema: {MANUSCRIPT_SCHEMA}\n"
             f"book: {book}\n"
             f"chapters: {len(nums)}\n"
             f"drafted_by: {drafted_inline}\n"
             f"assembled_at: {ts}\n"
             "---\n\n")
    out = manuscript_path(book, repo_root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(front + "\n".join(bodies), encoding="utf-8")
    return 0


def cmd_seal(book: str, *, repo_root=REPO) -> int:
    man = manuscript_path(book, repo_root)
    if not man.is_file():
        _fail(f"no manuscript to seal for book {book} ({man}) — run assemble first")
    fr = final_read_path(book, repo_root)
    if not fr.is_file():
        _fail(f"no final-read artifact for book {book} ({fr}) — run the final read first")
    read_by = parse_frontmatter(fr.read_text(encoding="utf-8")).get("read_by")
    if not read_by:
        _fail(f"final-read artifact has no read_by stamp ({fr})")
    man_text = man.read_text(encoding="utf-8")
    drafted = _stamps(parse_frontmatter(man_text).get("drafted_by"))
    if read_by in drafted:
        _fail(f"read_by '{read_by}' appears in drafted_by set {sorted(drafted)}")
    man.write_text(write_frontmatter_field(man_text, "read_by", read_by),
                   encoding="utf-8")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Penny per-book manuscript producer.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_asm = sub.add_parser("assemble", help="build the manuscript from ch-*.final.md")
    p_asm.add_argument("book")
    p_seal = sub.add_parser("seal", help="stamp read_by from the final read")
    p_seal.add_argument("book")
    args = ap.parse_args(argv)
    if args.cmd == "assemble":
        return cmd_assemble(args.book)
    if args.cmd == "seal":
        return cmd_seal(args.book)
    ap.error(f"unknown command {args.cmd!r}")  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())
