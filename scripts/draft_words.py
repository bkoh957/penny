"""Stamp a chapter draft with its own word count.

`drafted_words:` belongs to the `drafted_by` / `drafted_on` family: a fact about
the draft as written, measured here rather than reported by the drafting model —
a model's own count of its words is a guess, and a guess in frontmatter reads
exactly like a measurement. Counting is the deterministic layer's job.

The stamp is the DRAFT's count and keeps that name downstream: the line and copy
edits cut flab, so the number a `.final.md` carries is what the draft weighed,
not what the finished chapter does.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.penny_meta import strip_frontmatter, write_frontmatter_field
from scripts.penny_paths import output_path
from scripts.penny_text import word_count

FIELD = "drafted_words"


def draft_path(book: str, chapter: str, repo_root=None):
    return output_path(
        f"book-{str(book).zfill(2)}/chapters/ch-{str(chapter).zfill(2)}.draft.md",
        repo_root)


def stamp_words(text: str) -> tuple[str, int]:
    """Return (text with `drafted_words` set, the count). Counts the body only,
    so the frontmatter's own words never inflate it. Raises ValueError when there
    is no frontmatter block — a draft without one has no `drafted_by` either, and
    inventing a block here would hide that."""
    count = word_count(strip_frontmatter(text))
    return write_frontmatter_field(text, FIELD, count), count


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("usage: draft_words.py <book> <chapter>", file=sys.stderr)
        return 2
    book, chapter = argv
    path = draft_path(book, chapter)
    if not path.is_file():
        print(f"draft_words: draft not found: {path}", file=sys.stderr)
        return 2
    try:
        text, count = stamp_words(path.read_text(encoding="utf-8"))
    except ValueError as e:
        print(f"draft_words: {path.name}: {e}", file=sys.stderr)
        return 2
    path.write_text(text, encoding="utf-8")
    print(f"{FIELD}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
