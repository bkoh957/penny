"""Extract one chapter's brief from `input/book-NN/outline.md` — the heading
line plus its body, verbatim.

Replaces the inline `awk` one-liner `finalize-chapter.md` step 3a used to run
(spec `docs/superpowers/specs/2026-08-29-runbook-render-corrupts-positional-
vars-fix.md` §4b). `commands/*.md` runbooks are rendered into an agent's
context with argument placeholders substituted — zero-indexed, uniformly,
including inside fenced code blocks. The awk read `$0` as if it were the
drafting model's first positional argument once rendered; in awk `$0` is the
whole current record, so the substitution silently turned
`index($0, h) == 1` into `index(01, h) == 1` — always false — and `$brief`
came out empty every time, with no error. `ledger-updater` then ran with no
scope context and guessed.

A script under `scripts/` is never rendered into an agent's context, so no
substitution can reach it — and unlike the inline awk, it is testable.

Reuses the engine's existing outline parser rather than forking a third one:
`penny_wiring.chapter_block` (body) and `penny_wiring.heading_line` (the
heading line verbatim, including any `[type: ...]` flag) — the same split
`packet_assemble.assemble` already composes as `full_block`.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.penny_paths import input_path
from scripts.penny_wiring import chapter_block, heading_line


def outline_path(book: str, repo_root=None) -> Path:
    return input_path(f"book-{str(book).zfill(2)}/outline.md", repo_root)


def extract_brief(outline_text: str, chapter) -> str:
    """The chapter's `## Chapter NN ...` heading line, then its body, exactly
    as the outline carries them (heading excluded from the body, then
    re-attached — chapter_block() deliberately excludes it). Raises
    ValueError, named by chapter, when the outline has no such block —
    never returns empty: that silent-empty output is exactly the failure
    this module exists to make loud."""
    num = int(chapter)
    heading = heading_line(outline_text, num)
    block = chapter_block(outline_text, num)
    if not heading or not block:
        raise ValueError(f"outline has no chapter {num} block")
    return f"{heading}\n{block}"


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("usage: extract_brief.py <book> <chapter>", file=sys.stderr)
        return 2
    book, chapter = argv

    path = outline_path(book)
    if not path.is_file():
        print(f"extract_brief: no outline at {path}", file=sys.stderr)
        return 2

    try:
        brief = extract_brief(path.read_text(encoding="utf-8"), chapter)
    except ValueError as e:
        print(f"extract_brief: book {book}: {e}", file=sys.stderr)
        return 2

    print(brief)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
