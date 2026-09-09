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
from scripts.penny_wiring import (chapter_block, heading_line,
                                  parse_packet_sections, parse_wired_chapters)


def _fail(predicate: str):
    print(f"PREDICATE FAILED: {predicate}", file=sys.stderr)
    raise SystemExit(1)


def packet_path(book: str, chapter: str, repo_root=None) -> Path:
    return input_path(
        f"book-{str(book).zfill(2)}/packets/ch-{str(chapter).zfill(2)}.md",
        repo_root)


_ATX_HEADING_RE = re.compile(r"^( {0,3})(#{1,6})([ \t]+)(.*)$", re.MULTILINE)
_SETEXT_UNDERLINE_RE = re.compile(r"^ {0,3}(=+|-+)[ \t]*$")
_LIST_ITEM_LINE_RE = re.compile(r"^ {0,3}(?:[-*+]|\d{1,9}[.)])(?:[ \t]|$)")
_BLOCKQUOTE_LINE_RE = re.compile(r"^ {0,3}>")
_ATX_LINE_RE = re.compile(r"^ {0,3}#{1,6}(?:[ \t]|$)")
_HTML_BLOCK_LINE_RE = re.compile(r"^ {0,3}<")
_INDENTED_CODE_LINE_RE = re.compile(r"^(?: {4,}|\t)")
# A fence delimiter line (never real setext TEXT — it opens or closes a code
# block either way) and a line shaped like a GFM table row: it must START
# with a `|` cell separator, not merely contain one anywhere — ordinary
# setext-heading text can contain a `|` (a pairing/comparison heading such
# as "Sleuth | Victim") and must still demote. Neither exclusion is fence
# *state* tracking — this recognizes a line's own shape, not whether an
# earlier line opened a fence still in effect — so the "no fenced-code-block
# tracking" rule (a `#` demoted INSIDE a fence stays demoted, deliberately)
# is untouched.
_FENCE_LINE_RE = re.compile(r"^ {0,3}(?:`{3,}|~{3,})")
_TABLE_ROW_LINE_RE = re.compile(r"^ {0,3}\|")


def _frontmatter_end(lines: list[str]) -> int:
    """If `lines` opens with a bare `---` delimiter (0-3 space indent) on its
    very first line, return the index of the line that closes the block
    (also a bare `---`); else -1. Deliberately narrow — only trusted when
    the block opens at line 1 — since a continuity entry otherwise starts
    with a `<!-- canon-meta -->` comment and `canon-core.md` is plain
    prose/headings; this exists only to keep a hand-authored YAML
    frontmatter block from being misread as a setext heading pair (the
    `key: value` line immediately above the closing `---` looks exactly
    like setext-heading text otherwise)."""
    if not lines or lines[0].strip() != "---":
        return -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return i
    return -1


def _convert_setext_headings(text: str, offset: int, max_level: int) -> str:
    """Rewrite setext headings (a non-blank text line followed by a line of
    only `=` or only `-`) into demoted ATX form, at the same depth the ATX
    path would land an equivalent `#`/`##` heading — spec
    2026-08-27-packet-extract-heading-collision-fix.md follow-up. Deliberately
    conservative: a `---`/`===` that could be a thematic break, YAML
    frontmatter delimiter, or that follows a list item / blockquote / ATX
    heading / HTML block line / indented code line is never converted —
    those are real, common shapes in hand-authored canon (an
    `<!-- canon-meta -->` comment opens every continuity entry the engine
    ships) and getting one wrong corrupts authored text, which is worse than
    a narrow reopening of the original bug. The text line's own 1-3 space
    indent, if any, is preserved in the demoted output, matching the ATX
    path."""
    lines = text.split("\n")
    fm_end = _frontmatter_end(lines)
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        if i <= fm_end:
            out.append(lines[i])
            i += 1
            continue
        line = lines[i]
        if i + 1 < n and line.strip():
            m = _SETEXT_UNDERLINE_RE.match(lines[i + 1])
            if (m and not _LIST_ITEM_LINE_RE.match(line)
                    and not _BLOCKQUOTE_LINE_RE.match(line)
                    and not _ATX_LINE_RE.match(line)
                    and not _HTML_BLOCK_LINE_RE.match(line)
                    and not _INDENTED_CODE_LINE_RE.match(line)
                    and not _FENCE_LINE_RE.match(line)
                    and not _TABLE_ROW_LINE_RE.match(line)):
                level = 1 if m.group(1)[0] == "=" else 2
                new_level = min(level + offset, max_level)
                indent = line[:len(line) - len(line.lstrip(" "))]
                out.append(f"{indent}{'#' * new_level} {line.strip()}")
                i += 2
                continue
        out.append(line)
        i += 1
    return "\n".join(out)


def _demote_headings(text: str, offset: int = 4, max_level: int = 6) -> str:
    """Rewrite every heading in embedded continuity source text — ATX
    (`^#{1,6} ...`, indented up to 3 spaces) and setext (a text line
    underlined with `===`/`---`) — to sit well below the `### <source>`
    wrapper the packet puts around it, clamped at level 6 — spec
    2026-08-27-packet-extract-heading-collision-fix.md §3a plus its
    follow-up. Without this, a source file's own top-level heading
    structurally closes the packet's `## Continuity Extracts` section, and
    every consumer that reads that section by markdown structure silently
    gets a truncated slice.

    Only a `#` immediately followed by whitespace, at the start of a line
    with 0-3 leading spaces, counts as an ATX heading — `#hashtag` (no
    space), a mid-line `#`, and a 4+-space-indented `#` (an indented code
    block, not a heading, per CommonMark) are left untouched. The original
    indent is preserved in the output — an indented heading is demoted in
    place, not left-stripped. Setext conversion is conservative by design:
    see `_convert_setext_headings`. Shared by both embed call sites
    (canon-core.md and each continuity entry) so the rule can't drift
    between them.
    """
    def _demote(m: re.Match) -> str:
        indent, hashes, spacing, rest = m.group(1), m.group(2), m.group(3), m.group(4)
        new_level = min(len(hashes) + offset, max_level)
        return f"{indent}{'#' * new_level}{spacing}{rest}"
    text = _ATX_HEADING_RE.sub(_demote, text)
    text = _convert_setext_headings(text, offset, max_level)
    return text


_CONTINUITY_SUBDIRS = ("characters", "locations", "threads", "background")


def _continuity_entries(root) -> dict[str, dict]:
    """Every series/continuity/{characters,locations,threads,background}/*.md entry,
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


_CONTINUITY_HEADING_RE = re.compile(r"^## Continuity Extracts\b.*$", re.MULTILINE)
_NEXT_TOP_HEADING_RE = re.compile(r"^#{1,2}(?!#)[ \t]", re.MULTILINE)


def without_continuity(packet_text: str) -> str:
    """The packet minus its `## Continuity Extracts` section — a read-only
    projection for agents that never read the slice (the map-maker prices
    scenes; the developmental-editor carries its own character-bible slice).
    Never writes: the stamped packet on disk is the artefact, this is a
    dispatch-time view of it (spec 2026-09-09-check-economics §6).

    The section ends at the next level-1/2 heading — a demoted `###`+ heading
    from an embedded source does NOT end it, which is why the whole section is
    removed rather than only its first entry."""
    m = _CONTINUITY_HEADING_RE.search(packet_text)
    if m is None:
        return packet_text
    rest = packet_text[m.end():]
    nxt = _NEXT_TOP_HEADING_RE.search(rest)
    tail = rest[nxt.start():] if nxt else ""
    return packet_text[:m.start()] + tail


def _manifest(counts: dict[str, int]) -> str:
    """The `(N entries: canon-core.md, 32 background/, 7 characters/)` suffix a
    continuity section's heading carries to declare its own contents (spec
    2026-08-29-curated-artifacts-declare-their-contents-design.md). One home,
    because `_continuity_slice` builds it and `inspector_slice` must rebuild it
    for a reduced entry set — two copies would let the projection's manifest
    drift from the assembler's without any test noticing."""
    total = sum(counts.values())
    if not counts:
        return "(0 entries)"
    breakdown = []
    if "canon-core.md" in counts:
        breakdown.append("canon-core.md")
    breakdown += [f"{counts[s]} {s}" for s in sorted(counts) if s != "canon-core.md"]
    noun = "entry" if total == 1 else "entries"
    return f"({total} {noun}: {', '.join(breakdown)})"


_EXTRACT_ENTRY_RE = re.compile(r"^### (.+?)$", re.MULTILINE)
_INSPECTOR_EXCLUDED_SUBDIRS = ("background/",)


def inspector_slice(packet_text: str) -> str:
    """The packet's continuity section with `background/` entries removed — a
    read-only projection for the two inspectors that grade a chapter against
    the ledger. `background/` is authored narrative source the DRAFTER needs
    (backstory, texture, how a character sounds); `characters/`, `locations/`
    and `threads/` are the ledger — the facts a chapter can contradict. Both
    real continuity blockers in the live series traced to `characters/`
    (spec 2026-09-09-check-economics §2.4).

    The manifest is recomputed from what is kept: the heading declares its own
    contents, so a projection that drops entries and keeps the original count
    would claim coverage it does not have."""
    m = _CONTINUITY_HEADING_RE.search(packet_text)
    if m is None:
        return ""
    rest = packet_text[m.end():]
    nxt = _NEXT_TOP_HEADING_RE.search(rest)
    body = rest[:nxt.start()] if nxt else rest

    entries = list(_EXTRACT_ENTRY_RE.finditer(body))
    kept: list[str] = []
    counts: dict[str, int] = {}
    for i, em in enumerate(entries):
        name = em.group(1).strip()
        if any(name.startswith(x) for x in _INSPECTOR_EXCLUDED_SUBDIRS):
            continue
        end = entries[i + 1].start() if i + 1 < len(entries) else len(body)
        kept.append(body[em.start():end].strip())
        if "/" in name:
            sub = name.split("/", 1)[0] + "/"
            counts[sub] = counts.get(sub, 0) + 1
        else:
            counts[name] = counts.get(name, 0) + 1

    if not kept:
        # Nothing survived the filter. If the assembler wrote a reason instead
        # of entries (`- None. — no continuity entries matched this chapter`),
        # carry it: a bare `(0 entries)` is truthful about the count but leaves
        # an inspector unable to tell an empty slice from a filtered one.
        preamble = (body[:entries[0].start()] if entries else body).strip()
        if preamble:
            kept = [preamble]

    out = f"## Continuity Extracts {_manifest(counts)}\n"
    if kept:
        out += "\n" + "\n\n".join(kept) + "\n"
    return out


def _continuity_slice(root, chapter_text: str) -> tuple[str, str]:
    """canon-core.md (always, first) + entries named in `chapter_text` (word
    boundary, case-insensitive) + one hop through each matched entry's
    canon-meta `links`/`refs`. Nothing else — the packet is the curation
    boundary, so unmatched entries (future chapters, other characters'
    secrets) stay out.

    Returns `(section_text, manifest)`. Each embedded source's own headings
    are demoted (`_demote_headings`) before interpolation, so an authored
    `#`/`##` heading inside canon-core.md or a continuity entry can never
    structurally close the packet's `## Continuity Extracts` section — see
    spec 2026-08-27-packet-extract-heading-collision-fix.md. `manifest` is a
    parenthesised `(N entries: ...)` breakdown derived from what was
    actually emitted (never a separate directory walk), meant to be appended
    to the section heading so any reader can check its read was complete."""
    canon_core_path = series_path("continuity/canon-core.md", root)
    entries = _continuity_entries(root)

    matched: set[str] = {
        key for key, e in entries.items()
        if any(_word_match(n, chapter_text) for n in e["names"] if n)
    }
    # Every NAME a matched entry answers to — stem plus its canon-meta `id`,
    # the same set `_word_match` above ran over. Stems alone would drop a
    # relationship whose end is spelled by an id no filename carries
    # (`calvin-pruitt.md` with `id: cal`, named after by `cal--maggie`).
    named: set[str] = {n for k in matched for n in entries[k]["names"] if n}
    for key in list(matched):
        meta = entries[key]["meta"]
        linked = list(meta.get("links") or []) + list(meta.get("refs") or [])
        for link in linked:
            lname = str(link).strip().lower()
            for other_key, other in entries.items():
                if lname not in other["names"]:
                    continue
                stem = other["path"].stem.lower()
                # A relationship entry (`a--b`) is reachable only by one hop —
                # it never appears in prose — so naming one protagonist used to
                # pull every relationship she is in. It earns its place only
                # when BOTH ends are in this chapter (spec 2026-09-09 §3b.4).
                if "--" in stem and not all(
                        part in named for part in stem.split("--")):
                    continue
                matched.add(other_key)

    parts: list[str] = []
    notes: list[str] = []
    counts: dict[str, int] = {}
    if canon_core_path.is_file():
        body = _demote_headings(canon_core_path.read_text(encoding="utf-8").strip())
        parts.append(f"### canon-core.md\n\n{body}")
        counts["canon-core.md"] = 1
    else:
        notes.append("no series/continuity/canon-core.md")
    for key in sorted(matched):
        e = entries[key]
        rel = e["path"].relative_to(series_path("continuity", root))
        body = _demote_headings(e["text"].strip())
        parts.append(f"### {rel.as_posix()}\n\n{body}")
        sub = f"{rel.parts[0]}/"
        counts[sub] = counts.get(sub, 0) + 1

    manifest = _manifest(counts)

    if not parts:
        note = "; ".join(notes) if notes else "no continuity entries matched this chapter"
        return f"- None. — {note}", manifest
    return "\n\n".join(parts), manifest


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

    heading = heading_line(outline_text, chnum) or f"## Chapter {ch2}"
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
    clue_ids: list[str] = []
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
            # Same demotion the continuity embeds get, for the same reason and
            # a worse consequence: a ledger description is authored YAML, ten
            # of the live book's forty-five are multi-line block scalars, and
            # one line beginning `## ` inside one of them structurally closes
            # `## Ledger Clues` — dropping every later clue out of the section
            # that `inspector-fairplay` grades the chapter against (spec
            # 2026-08-29-curated-artifacts-declare-their-contents-design.md
            # §4a).
            desc = _demote_headings(str(desc).strip())
            clue_lines.append(f"- [{cid}] plant_chapter {chnum}: {desc}")
            clue_ids.append(cid)
    # Declare what was scheduled, so a reader whose slice was truncated can
    # see that it was. Derived from what is actually emitted below, never from
    # a second walk of the ledger — a manifest counting a different pass than
    # the one it labels is worse than none.
    clues_manifest = (f"({len(clue_ids)} scheduled: {', '.join(clue_ids)})"
                      if clue_ids else "(0 scheduled)")
    if not clue_lines:
        clue_lines = ["- None."]

    # --- continuity slice ---
    continuity_section, continuity_manifest = _continuity_slice(root, full_block)

    # --- standing series guardrails ---
    guardrails_path = config_path("series-guardrails.md", root)
    if guardrails_path.is_file():
        # The carried file's own headings must not close the packet's
        # `## Standing Series Guardrails` section — the rule the continuity
        # extracts already follow (spec 2026-08-27, extended to this site by
        # spec 2026-09-09).
        guardrails_section = _demote_headings(
            guardrails_path.read_text(encoding="utf-8").strip())
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
        f"## Ledger Clues {clues_manifest}",
        "",
        *clue_lines,
        "",
        f"## Continuity Extracts {continuity_manifest}",
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
    argv = list(sys.argv[1:] if argv is None else argv)
    projections = {"--without-continuity": without_continuity,
                   "--inspector-slice": inspector_slice}
    projection = None
    for flag in ("--without-continuity", "--inspector-slice"):
        if flag in argv:
            argv.remove(flag)
            if projection is not None:
                # Two different projections of the same packet. Silently
                # picking one would hide the runbook bug that passed both.
                print(f"usage: {projection} and {flag} are different "
                      f"projections — pass exactly one", file=sys.stderr)
                return 2
            projection = flag
    if len(argv) != 2:
        print("usage: packet_assemble.py <book> <chapter> "
              "[--without-continuity | --inspector-slice]", file=sys.stderr)
        return 2
    book, chapter = argv
    if projection is None:
        print(assemble(book, chapter))
        return 0
    # Projections read the packet already on disk and print it — they never
    # assemble, so they cannot move a `built_from_*` stamp.
    p = packet_path(book, chapter)
    if not p.is_file():
        print(f"PREDICATE FAILED: no packet at {p} — run packet_assemble first",
              file=sys.stderr)
        return 1
    print(projections[projection](p.read_text(encoding="utf-8")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
