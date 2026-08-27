#!/usr/bin/env python3
"""Splice an approved texture allocation into a book's cut plan (spec
2026-08-27 §4.2).

The allocation itself is a taste call — which chapter spends which image, where
texture goes deliberately quiet, which images recur as motifs — made by the
showrunner over the whole book at once and saved to
`input/book-NN/plot/texture.md`. Landing thirty-five blocks in the right chapter
blocks is not a taste call; it is mechanics, and a hand edit that puts one
chapter's spend in its neighbour has no symptom until a drafted chapter reads
wrong.

Idempotent: re-running replaces the `- **Texture:**` block it wrote last time,
so re-allocating after a chapter boundary moves is one command rather than a
manual diff.

Never partially applies. A blocking finding leaves cut-plan.md byte-identical.

  python3 scripts/texture_apply.py 01
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import penny_paths

#: The allocation save point, relative to `input/book-NN/`. It lives beside the
#: plot workshop's other save points because it is the same kind of artifact:
#: the showrunner's own judgment, written once, arguable in one place, cheap to
#: redo.
PLAN_REL = "plot/texture.md"

_CHAPTER_RE = re.compile(r"^##\s+Chapter\s+(?P<num>\d+)\b")
_ITEM_RE = re.compile(r"^\s*-\s+(?P<val>\S.*?)\s*$")
_TEXTURE_FIELD_RE = re.compile(r"^\s*-\s+\*\*Texture:\*\*")
_ANCHOR_RE = re.compile(r"^\s*-\s+\*\*(?:Summary|Compress):\*\*")
_NESTED_ITEM_RE = re.compile(r"^\s+-\s")


def parse_texture_plan(text: str) -> dict:
    """chapter number -> its allocated items, in authoring order.

    A chapter heading with no items yields an empty list rather than vanishing:
    naming a chapter and allocating it nothing is a different statement from not
    naming it, and `apply_texture` reports the two differently.
    """
    out: dict = {}
    current = None
    for raw in text.splitlines():
        m = _CHAPTER_RE.match(raw)
        if m:
            current = int(m.group("num"))
            out.setdefault(current, [])
            continue
        if current is None:
            continue
        im = _ITEM_RE.match(raw)
        if im:
            out[current].append(im.group("val"))
    return out


def _strip_texture(block: list) -> list:
    """The chapter block with any previously spliced Texture block removed."""
    out, dropping = [], False
    for raw in block:
        if _TEXTURE_FIELD_RE.match(raw):
            dropping = True
            continue
        if dropping:
            if not raw.strip():
                dropping = False
                out.append(raw)
                continue
            if _NESTED_ITEM_RE.match(raw):
                continue
            dropping = False
        out.append(raw)
    return out


def _anchor_index(block: list) -> "int | None":
    """Index of the line the Texture block goes after: the LAST Summary or
    Compress line. Texture is the positive half of the compress line, so it
    belongs with it — above Setting, Opening, Closing and the track rows."""
    hits = [i for i, raw in enumerate(block) if _ANCHOR_RE.match(raw)]
    return hits[-1] if hits else None


def apply_texture(cut_plan_text: str, plan: dict) -> tuple:
    """(new_text, blocking, notes).

    `new_text` is the input unchanged whenever `blocking` is non-empty — a
    half-applied allocation is worse than none, because the half that landed
    looks approved.
    """
    lines = cut_plan_text.splitlines()
    blocking: list = []
    notes: list = []

    order = [(int(m.group("num")), i) for i, raw in enumerate(lines)
             if (m := _CHAPTER_RE.match(raw))]
    starts = {num: i for num, i in order}
    ends = {num: (order[k + 1][1] if k + 1 < len(order) else len(lines))
            for k, (num, i) in enumerate(order)}

    for num in sorted(plan):
        if num not in starts:
            blocking.append(
                f"unknown-chapter: the allocation names chapter {num:02d}, "
                f"which cut-plan.md does not have — a boundary moved since the "
                f"allocation was written; re-allocate against the current plan")
    if blocking:
        return cut_plan_text, blocking, notes

    out = lines[:order[0][1]] if order else list(lines)
    for num, start in order:
        block = _strip_texture(lines[start:ends[num]])
        items = plan.get(num)
        if items is None:
            notes.append(
                f"unallocated-chapter: chapter {num:02d} has no allocation — it "
                f"spends nothing this book, which is legal: texture is a "
                f"resource, not an obligation")
            out.extend(block)
            continue
        if not items:
            notes.append(
                f"empty-allocation: chapter {num:02d} is named by the "
                f"allocation with no items — no Texture block written")
            out.extend(block)
            continue
        anchor = _anchor_index(block)
        if anchor is None:
            blocking.append(
                f"no-anchor: chapter {num:02d} has neither a **Summary:** nor a "
                f"**Compress:** line to place the Texture block after — repair "
                f"the cut plan")
            out.extend(block)
            continue
        rendered = ["- **Texture:**"] + [f"  - {t}" for t in items]
        out.extend(block[:anchor + 1] + rendered + block[anchor + 1:])

    if blocking:
        return cut_plan_text, blocking, notes
    return "\n".join(out) + "\n", blocking, notes


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print("usage: texture_apply.py <book>", file=sys.stderr)
        return 2
    book = str(argv[0]).zfill(2)

    root = penny_paths.series_root()
    bookdir = root / "input" / f"book-{book}"
    plan_p, cut_p = bookdir / PLAN_REL, bookdir / "cut-plan.md"
    for p in (plan_p, cut_p):
        if not p.is_file():
            print(f"texture_apply: missing {p}", file=sys.stderr)
            return 2

    plan = parse_texture_plan(plan_p.read_text(encoding="utf-8"))
    if not plan:
        print(f"texture_apply: {plan_p} names no chapters", file=sys.stderr)
        return 2

    text, blocking, notes = apply_texture(cut_p.read_text(encoding="utf-8"), plan)
    if blocking:
        for f in blocking:
            print(f)
        print("\nNothing written — cut-plan.md is unchanged.", file=sys.stderr)
        return 1

    cut_p.write_text(text, encoding="utf-8")
    print(f"texture_apply: allocated {len(plan)} chapters into {cut_p}")
    if notes:
        print("\nAdvisory — nothing blocks on these:")
        for n in notes:
            print(f"  {n}")
    # No literal path here: this runs from a series folder, where the engine
    # lives at ${CLAUDE_PLUGIN_ROOT}. The runbook owns the invocation.
    print(f"\nNow re-run the cut (story_cut.py {book}) so outline.md carries "
          f"the allocation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
