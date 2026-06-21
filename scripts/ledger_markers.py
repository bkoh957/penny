"""Deterministic post-gate recency markers (Phase 4; design §4.3, §4.5).

Stamps structured-field markers that are mechanically detectable — no LLM:
  - last_referenced  on canon-core section headers (id-scan of brief + text)
  - last_advanced_chapter  on thread frontmatter (driven by the updater's flag)

Structured-field editing is fiddly and is the Phase-8 demotion precision seed,
so it lives in tested Python, not in the ledger-updater agent's prose output.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.penny_meta import (
    parse_canon_sections,
    write_canon_section_field,
    write_frontmatter_field,
)


def referenced_section_ids(canon_text: str, brief_text: str, chapter_text: str) -> list[str]:
    """Section ids whose any ``refs`` token appears (substring) in the brief or
    chapter text. Sections with empty refs are never referenced."""
    hay = f"{brief_text}\n{chapter_text}"
    out: list[str] = []
    for sec in parse_canon_sections(canon_text):
        refs = sec.get("refs") or []
        if any(ref and ref in hay for ref in refs):
            out.append(sec["id"])
    return out


def stamp_last_referenced(canon_text: str, chapter: int, brief_text: str,
                          chapter_text: str) -> str:
    """Return canon_text with ``last_referenced=chapter`` set on every referenced
    section. Ref-less / unreferenced sections are left untouched."""
    text = canon_text
    for sec_id in referenced_section_ids(canon_text, brief_text, chapter_text):
        text = write_canon_section_field(text, sec_id, "last_referenced", int(chapter))
    return text


def stamp_thread_advanced(thread_text: str, chapter: int) -> str:
    """Return thread_text with ``last_advanced_chapter=chapter`` in its frontmatter."""
    return write_frontmatter_field(thread_text, "last_advanced_chapter", int(chapter))


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Penny post-gate recency markers.")
    ap.add_argument("book")
    ap.add_argument("chapter")
    ap.add_argument("--canon", required=True)
    ap.add_argument("--brief", required=True)
    ap.add_argument("--text", required=True)
    ap.add_argument("--thread-advanced", action="append", default=[],
                    help="thread file path the updater flagged advanced (repeatable)")
    args = ap.parse_args(argv)
    ch = int(args.chapter)

    canon_p = Path(args.canon)
    canon_p.write_text(
        stamp_last_referenced(
            canon_p.read_text(encoding="utf-8"), ch,
            Path(args.brief).read_text(encoding="utf-8"),
            Path(args.text).read_text(encoding="utf-8"),
        ),
        encoding="utf-8",
    )
    for tp in args.thread_advanced:
        p = Path(tp)
        p.write_text(stamp_thread_advanced(p.read_text(encoding="utf-8"), ch),
                     encoding="utf-8")
    print(f"markers: canon last_referenced<-{ch}; "
          f"{len(args.thread_advanced)} thread(s) advanced<-{ch}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
