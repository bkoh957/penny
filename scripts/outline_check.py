"""Outline structural checker (deterministic, Tier-3, shape-only).

Validates that an author outline (output/book-NN/outline.md) is SHAPED like an
outline — nothing more. Four named predicates; zero genre/LLM judgment. Fairness,
suspect-existence and prose quality are judged elsewhere (the lock, the scaffolder,
the human review). Mirrors fairplay_check.py: named predicate + nonzero exit.

Dependency-free apart from scripts.penny_meta (frontmatter) — no PyYAML.

  python3 scripts/outline_check.py output/book-01/outline.md
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.penny_meta import parse_frontmatter

_HEADING_RE = re.compile(r"^##\s+(.*?)\s*$", re.MULTILINE)
_CHAPTER_RE = re.compile(r"^Chapter\s+(\d+)$")
_SOLUTION_RE = re.compile(r"^Solution\b(?::\s*(?P<label>.*?))?$")


def _chapter_numbers(text: str) -> list[int]:
    return [int(m.group(1)) for h in _HEADING_RE.findall(text)
            for m in [_CHAPTER_RE.match(h)] if m]


def _empty_chapter_beats(text: str) -> list[int]:
    empty: list[int] = []
    matches = list(_HEADING_RE.finditer(text))
    for i, m in enumerate(matches):
        cm = _CHAPTER_RE.match(m.group(1))
        if not cm:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        if not text[start:end].strip():
            empty.append(int(cm.group(1)))
    return empty


def check_outline(outline_path, *, repo_root=None) -> dict:
    path = Path(outline_path)
    if not path.is_file():
        return {"blocking": [f"outline-frontmatter: outline not found: {path}"],
                "metrics": {}}
    text = path.read_text(encoding="utf-8")
    blocking: list[str] = []

    fm = parse_frontmatter(text)
    book = fm.get("book")
    total_raw = fm.get("total_chapters")
    if not (isinstance(book, str) and book.strip().isdigit()):
        blocking.append(f"outline-frontmatter: 'book' missing or not an integer: {book!r}")
    total = None
    if isinstance(total_raw, str) and total_raw.strip().isdigit():
        total = int(total_raw)
    else:
        blocking.append(
            f"outline-frontmatter: 'total_chapters' missing or not an integer: {total_raw!r}")

    headings = _HEADING_RE.findall(text)
    if not any(_SOLUTION_RE.match(h) for h in headings):
        blocking.append("outline-solution: no '## Solution' block found")

    nums = _chapter_numbers(text)
    if total is not None:
        expected = list(range(1, total + 1))
        if sorted(nums) != expected:
            blocking.append(
                f"outline-chapters-contiguous: chapter headings {sorted(nums)} are not "
                f"a contiguous 1..{total} (gaps/dupes/extras)")

    empty = _empty_chapter_beats(text)
    if empty:
        blocking.append(
            f"outline-nonempty-beats: chapter(s) {empty} have an empty beat body")

    metrics = {"book": book, "total_chapters": total,
               "chapters_found": sorted(nums)}
    return {"blocking": blocking, "metrics": metrics}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Penny outline structural checker.")
    ap.add_argument("outline", help="path to output/book-NN/outline.md")
    args = ap.parse_args(argv)
    result = check_outline(args.outline)
    for line in result["blocking"]:
        print(f"outline_check: {line}")
    return 1 if result["blocking"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
