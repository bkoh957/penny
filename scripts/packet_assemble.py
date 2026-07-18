"""Assemble a chapter's PACKET — spec 2026-07-18 §5. Deterministic: a slice
plus lookups, no LLM. The packet is the curation boundary: this chapter's
block, its ledger clues, its continuity slice, the standing guardrails, its
band — and nothing else."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import penny_length
from scripts.penny_meta import parse_canon_meta, parse_frontmatter
from scripts.penny_paths import (config_path, input_path, penny_path,
                                 series_path, series_root)
from scripts.penny_whodunit import (clues_by_chapter, file_sha256,
                                    ledger_identity, load_ledger)
from scripts.penny_wiring import (chapter_block, parse_packet_sections,
                                  parse_wired_chapters)


def _fail(predicate: str):
    print(f"PREDICATE FAILED: {predicate}", file=sys.stderr)
    raise SystemExit(1)


def packet_path(book: str, chapter: str, repo_root=None) -> Path:
    return input_path(
        f"book-{str(book).zfill(2)}/packets/ch-{str(chapter).zfill(2)}.md",
        repo_root)


_HEADING_LINE_RE = re.compile(r"^##\s+Chapter\s+0*(\d+)\b.*$", re.MULTILINE)


def _heading_line(outline_text: str, num: int) -> str:
    """The original `## Chapter NN ...` heading line, verbatim (including any
    `[type: ...]`/`[long: ...]` flags), sliced straight out of the outline —
    chapter_block() deliberately excludes it, and the packet must re-attach
    it exactly as authored rather than reconstruct it from parsed parts."""
    for m in _HEADING_LINE_RE.finditer(outline_text):
        if int(m.group(1)) == num:
            return m.group(0)
    return ""


_CONTINUITY_SUBDIRS = ("characters", "locations", "threads")


def _continuity_entries(root) -> dict[str, dict]:
    """Every series/continuity/{characters,locations,threads}/*.md entry,
    keyed by `"<subdir>/<stem>"` (lowercased) — a subdir-qualified key, so a
    same-named file in two subdirs (characters/mary.md and threads/mary.md)
    gets two distinct entries instead of one silently clobbering the other.
    Matching and one-hop linking still operate on the unqualified `names` set
    (stem + canon-meta id) carried inside each entry, unaffected by the key
    change — only storage was colliding, not lookup."""
    entries: dict[str, dict] = {}
    for sub in _CONTINUITY_SUBDIRS:
        d = series_path(f"continuity/{sub}", root)
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):
            text = f.read_text(encoding="utf-8")
            meta = parse_canon_meta(text)
            stem = f.stem.lower()
            mid = str(meta.get("id", "")).strip().lower()
            names = {stem} | ({mid} if mid else set())
            entries[f"{sub}/{stem}"] = {"path": f, "text": text, "meta": meta, "names": names}
    return entries


def _word_match(name: str, text: str) -> bool:
    return bool(re.search(rf"\b{re.escape(name)}\b", text, re.IGNORECASE))


def _continuity_slice(root, chapter_text: str) -> str:
    """canon-core.md (always, first) + entries named in `chapter_text` (word
    boundary, case-insensitive) + one hop through each matched entry's
    canon-meta `links`/`refs`. Nothing else — the packet is the curation
    boundary, so unmatched entries (future chapters, other characters'
    secrets) stay out."""
    canon_core_path = series_path("continuity/canon-core.md", root)
    entries = _continuity_entries(root)

    matched: set[str] = {
        key for key, e in entries.items()
        if any(_word_match(n, chapter_text) for n in e["names"] if n)
    }
    for key in list(matched):
        meta = entries[key]["meta"]
        linked = list(meta.get("links") or []) + list(meta.get("refs") or [])
        for link in linked:
            lname = str(link).strip().lower()
            for other_key, other in entries.items():
                if lname in other["names"]:
                    matched.add(other_key)

    parts: list[str] = []
    notes: list[str] = []
    if canon_core_path.is_file():
        parts.append(f"### canon-core.md\n\n{canon_core_path.read_text(encoding='utf-8').strip()}")
    else:
        notes.append("no series/continuity/canon-core.md")
    for key in sorted(matched):
        e = entries[key]
        rel = e["path"].relative_to(series_path("continuity", root))
        parts.append(f"### {rel.as_posix()}\n\n{e['text'].strip()}")

    if not parts:
        note = "; ".join(notes) if notes else "no continuity entries matched this chapter"
        return f"- None. — {note}"
    return "\n\n".join(parts)


def assemble(book: str, chapter: str, *, repo_root=None) -> Path:
    root = Path(repo_root) if repo_root is not None else series_root()
    book2 = str(book).zfill(2)
    ch2 = str(chapter).zfill(2)
    chnum = int(chapter)

    lock = penny_path(f"locks/book-{book2}.mystery.lock", root)
    if not lock.is_file():
        _fail(f"book {book} has no mystery lock — packet assembly needs the "
              f"sealed ledger's obligations; run preflight lock-mystery {book}")

    outline_path = input_path(f"book-{book2}/outline.md", root)
    if not outline_path.is_file():
        _fail(f"book {book} has no outline at {outline_path}")
    outline_text = outline_path.read_text(encoding="utf-8")

    block = chapter_block(outline_text, chnum)
    if not block:
        _fail(f"book {book} outline has no chapter {chapter} block")

    heading = _heading_line(outline_text, chnum) or f"## Chapter {ch2}"
    full_block = f"{heading}\n{block}"

    sections = parse_packet_sections(block)
    if not sections.get("Required Beats", "").strip():
        _fail(f"chapter {chapter} has no ### Required Beats section — this "
              f"chapter is not in packet format; migrate the block (spec "
              f"2026-07-18 §3) before assembling a packet")

    chapters = parse_wired_chapters(outline_text)
    ch_dict = next((c for c in chapters if c["num"] == chnum), {})
    chapter_type = ch_dict.get("chapter_type")

    # --- ledger clues ---
    ledger_path = series_path(f"whodunit/book-{book2}.yaml", root)
    whodunit_stamp = ledger_identity(ledger_path)
    clue_lines: list[str] = []
    if ledger_path.is_file():
        try:
            data = load_ledger(ledger_path)
        except ValueError as e:
            _fail(str(e))
        ids_here = clues_by_chapter(ledger_path).get(chnum, [])
        entry_by_id: dict[str, dict] = {}
        for key in ("clue_schedule", "red_herrings"):
            for entry in (data.get(key) or []):
                entry_by_id[str(entry.get("id", "<no id>"))] = entry
        for cid in ids_here:
            entry = entry_by_id.get(cid, {})
            desc = (entry.get("description") or entry.get("misleads_toward")
                    or "(no description in ledger)")
            clue_lines.append(f"- [{cid}] plant_chapter {chnum}: {desc}")
    if not clue_lines:
        clue_lines = ["- None."]

    # --- continuity slice ---
    continuity_section = _continuity_slice(root, full_block)

    # --- standing series guardrails ---
    guardrails_path = config_path("series-guardrails.md", root)
    if guardrails_path.is_file():
        guardrails_section = guardrails_path.read_text(encoding="utf-8").strip()
    else:
        guardrails_section = "- None — this series has no config/series-guardrails.md."

    # --- word budget ---
    profile_path = config_path("length-profile.md", root)
    if not profile_path.is_file():
        band_line = "Band: unknown — no config/length-profile.md"
    else:
        try:
            profile = penny_length.parse_profile(profile_path.read_text(encoding="utf-8"))
            lo, hi = penny_length.band_for(profile, chapter_type)
            band_line = f"Band: {lo}–{hi} words (type: {chapter_type or 'default'})"
        except ValueError as e:
            band_line = f"Band: unknown — {e}"

    outline_sha = file_sha256(outline_path)

    lines = [
        "---",
        f"built_from_outline: {outline_sha}",
        f"built_from_whodunit: {whodunit_stamp}",
        "---",
        "",
        f"# Packet — Chapter {ch2}",
        "",
        full_block,
        "",
        "## Ledger Clues",
        "",
        *clue_lines,
        "",
        "## Continuity Extracts",
        "",
        continuity_section,
        "",
        "## Standing Series Guardrails",
        "",
        guardrails_section,
        "",
        "## Word Budget",
        "",
        band_line,
        "",
    ]
    text = "\n".join(lines)

    p = packet_path(book, chapter, root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


_CHAPTER_PACKET_RE = re.compile(r"^ch-(\d+)\.md$")


def stale_packets(book: str, repo_root=None) -> set[str]:
    """Chapter numbers (zero-padded) whose packet was built from a different
    outline OR a different whodunit ledger than the ones now on disk — the
    staleness contract the deleted brief compiler pioneered, inherited here."""
    root = Path(repo_root) if repo_root is not None else series_root()
    book2 = str(book).zfill(2)
    packets_dir = input_path(f"book-{book2}/packets", root)
    if not packets_dir.is_dir():
        return set()

    outline_path = input_path(f"book-{book2}/outline.md", root)
    outline_sha = file_sha256(outline_path) if outline_path.is_file() else None
    ledger_path = series_path(f"whodunit/book-{book2}.yaml", root)
    ledger_stamp = ledger_identity(ledger_path)

    stale: set[str] = set()
    for p in sorted(packets_dir.glob("ch-*.md")):
        m = _CHAPTER_PACKET_RE.match(p.name)
        if not m:
            continue
        num = m.group(1).zfill(2)
        fm = parse_frontmatter(p.read_text(encoding="utf-8"))
        is_stale = outline_sha is None or fm.get("built_from_outline") != outline_sha
        if fm.get("built_from_whodunit") != ledger_stamp:
            is_stale = True
        if is_stale:
            stale.add(num)
    return stale


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("usage: packet_assemble.py <book> <chapter>", file=sys.stderr)
        return 2
    book, chapter = argv
    p = assemble(book, chapter)
    print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
