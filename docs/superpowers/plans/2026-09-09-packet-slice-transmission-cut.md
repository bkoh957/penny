# Packet Slice Transmission Cut — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop transmitting the packet's 13,866-word `## Continuity Extracts` block to the five of eight per-chapter agent dispatches whose own definitions never reference it, and narrow it for the two that do — cutting a chapter cycle from ~224,813 to ~105,937 tokens without removing a single check.

**Architecture:** Two **projections** — pure functions of an already-assembled packet's text, printed to stdout, never written to disk. That is load-bearing: packets are stamped `built_from_outline`/`built_from_whodunit` and maps carry `built_from_packet`, so a projection that wrote a second artefact or altered the stamped one would make every map in the series stale at once. Task 3 narrows the slice inside `_continuity_slice` itself, which *does* change the packet's sha256 by design. Task 4 wires the runbooks and agent definitions to consume the projections.

**Tech Stack:** Python 3 stdlib only (the deterministic layer takes no PyYAML dependency; use `scripts/penny_meta.py` for frontmatter). pytest; `pytest.ini` sets `pythonpath=.`.

**Spec:** `docs/superpowers/specs/2026-09-09-check-economics-design.md` (§3b and §6 are this plan's scope; §3a and §3c are NOT)

## Global Constraints

- **No check is deleted and no inspector stops running.** Rosters stay fixed: twenty-three named findings in `story_cut.py`, ten in `tension_check.py`, seven in `map_check.py`. This plan adds no finding and no `--waive` handle.
- **Deterministic layer is stdlib-only.** No PyYAML in `packet_assemble.py`.
- **A projection never writes.** `assemble()`'s on-disk output and its `built_from_*` stamps must be byte-identical whether or not a projection is requested. Projections print to stdout and return; they do not call `assemble()` to regenerate.
- **A projection's manifest must not lie.** The `## Continuity Extracts (N entries: ...)` heading declares its own contents (spec `2026-08-29-curated-artifacts-declare-their-contents-design.md`). Any projection that drops entries recomputes that manifest; leaving the original count is a defect, not a cosmetic issue.
- **`CLAUDE.md:52`'s `full suite (N tests)` line must equal the real collected count** — `tests/test_texture_allocation_docs.py:118` enforces it. Move it in the same commit as any task that adds tests. Current baseline: **1324 passed**.
- **Runbook edits:** read CLAUDE.md's "Runbook arguments" section first. `commands/*.md` are rendered with argument substitution applied **including inside fenced code blocks**. **Never write a bare `$` before a digit** — `tests/test_runbook_arguments.py` fails the build on one. A runbook edit needs a session restart to take effect.
- **Commit per task, on `main`. Do not push.**
- **Do not modify anything under `~/myBooks/`** — that is the author's manuscript data.
- **Do not implement spec §3a or §3c** — turning on `tension_check`/`voice_drift`/`lexicon_check`, the thread roster, or any change to which inspectors run. Out of scope.

---

### Task 1: `without_continuity` — the packet minus its continuity block

For `map-maker` (proposing scene divisions and word targets) and `developmental-editor` (whose own agent definition asks for a character-bible slice and chapter brief, not the packet). Saves 13,866 words per dispatch, twice per cycle.

**Files:**
- Modify: `scripts/packet_assemble.py` (add the function; extend `main()` at line 411)
- Test: `tests/test_packet_assemble.py`

**Interfaces:**
- Produces: `without_continuity(packet_text: str) -> str` — returns `packet_text` with the `## Continuity Extracts ...` section removed, heading line included, everything else byte-identical. CLI: `python3 scripts/packet_assemble.py <book> <chapter> --without-continuity` reads the packet already on disk and prints the projection to stdout, writing nothing.
- Consumes: nothing from other tasks.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_packet_assemble.py`:

```python
def test_without_continuity_drops_the_section_and_keeps_the_rest():
    packet = (
        "---\nbuilt_from_outline: abc\n---\n\n"
        "# Packet — Chapter 05\n\n"
        "## Chapter 05 — A Title\n\nBlock body.\n\n"
        "## Ledger Clues (1 scheduled: c-one)\n\nClue body.\n\n"
        "## Continuity Extracts (2 entries: canon-core.md, 1 characters/)\n\n"
        "### canon-core.md\n\nCanon body.\n\n"
        "### characters/mary.md\n\nMary body.\n\n"
        "## Standing Series Guardrails\n\nGuardrail body.\n\n"
        "## Word Budget\n\nBand: 2000-3000\n")

    out = packet_assemble.without_continuity(packet)

    assert "## Continuity Extracts" not in out
    assert "Canon body." not in out
    assert "Mary body." not in out
    # Everything else survives, in order.
    assert "built_from_outline: abc" in out
    assert "## Chapter 05 — A Title" in out
    assert "Clue body." in out
    assert "## Standing Series Guardrails" in out
    assert "Guardrail body." in out
    assert "Band: 2000-3000" in out
    assert out.index("## Ledger Clues") < out.index("## Standing Series Guardrails")


def test_without_continuity_is_a_noop_when_there_is_no_such_section():
    packet = "# Packet — Chapter 05\n\n## Word Budget\n\nBand: 1-2\n"
    assert packet_assemble.without_continuity(packet) == packet


def test_without_continuity_stops_at_the_next_top_level_heading_only():
    """A demoted `###`+ heading inside the section must not end it early —
    the whole section goes, not just its first entry."""
    packet = (
        "## Continuity Extracts (1 entries: canon-core.md)\n\n"
        "### canon-core.md\n\n#### A demoted heading\n\nBody.\n\n"
        "## Word Budget\n\nBand: 1-2\n")

    out = packet_assemble.without_continuity(packet)

    assert "A demoted heading" not in out
    assert out.startswith("## Word Budget")


def test_projection_never_writes(series_tree):
    """The stamped packet on disk is byte-identical after a projection."""
    path = packet_assemble.assemble("01", "05", repo_root=series_tree)
    before = path.read_bytes()

    packet_assemble.without_continuity(path.read_text(encoding="utf-8"))

    assert path.read_bytes() == before
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_packet_assemble.py -k without_continuity -v`
Expected: FAIL with `AttributeError: module 'scripts.packet_assemble' has no attribute 'without_continuity'`.

- [ ] **Step 3: Write minimal implementation**

Add to `scripts/packet_assemble.py`, near `_continuity_slice`:

```python
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
```

Then extend `main()` (line 411) to accept the flag:

```python
def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    projection = None
    for flag in ("--without-continuity",):
        if flag in argv:
            argv.remove(flag)
            projection = flag
    if len(argv) != 2:
        print("usage: packet_assemble.py <book> <chapter> [--without-continuity]",
              file=sys.stderr)
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
    print(without_continuity(p.read_text(encoding="utf-8")))
    return 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_packet_assemble.py -v` — PASS, all pre-existing tests included.
Run: `python3 -m pytest` — expect **1328 passed** (1324 + 4). Update `CLAUDE.md:52` to 1328.

- [ ] **Step 5: Commit**

```bash
git add scripts/packet_assemble.py tests/test_packet_assemble.py CLAUDE.md
git commit -m "feat(packet): --without-continuity projection

The map-maker prices scenes and the developmental-editor carries its own
character-bible slice; neither reads the continuity block, and both were
being handed all 13,866 words of it. A read-only projection of the packet
already on disk — it never assembles, so it cannot move a built_from_ stamp
or stale a map.

Spec: docs/superpowers/specs/2026-09-09-check-economics-design.md §3b

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: `inspector_slice` — the ledger without the background prose

For `inspector-continuity` and `inspector-fairplay`. `background/` is drafter fuel — backstory, texture, how a character sounds. `characters/`, `locations/` and `threads/` are the ledger: the facts a chapter can contradict. Both real continuity blockers in the live series traced to `characters/`.

**Files:**
- Modify: `scripts/packet_assemble.py`
- Test: `tests/test_packet_assemble.py`

**Interfaces:**
- Consumes: `_NEXT_TOP_HEADING_RE` and `_CONTINUITY_HEADING_RE` from Task 1.
- Produces: `inspector_slice(packet_text: str) -> str` — the `## Continuity Extracts` section alone, keeping `### canon-core.md` and every `### <subdir>/<file>` entry whose subdir is NOT `background`, with the heading's manifest **recomputed** to match what is kept. CLI: `--inspector-slice`.

- [ ] **Step 1: Write the failing tests**

```python
INSPECTOR_PACKET = (
    "# Packet — Chapter 05\n\n"
    "## Continuity Extracts (4 entries: canon-core.md, 2 background/, 1 characters/)\n\n"
    "### canon-core.md\n\nCanon body.\n\n"
    "### background/mary.md\n\nMary backstory.\n\n"
    "### background/mary--cal.md\n\nTheir history.\n\n"
    "### characters/mary.md\n\nMary ledger facts.\n\n"
    "## Word Budget\n\nBand: 1-2\n")


def test_inspector_slice_drops_background_and_keeps_the_ledger():
    out = packet_assemble.inspector_slice(INSPECTOR_PACKET)

    assert "Canon body." in out
    assert "Mary ledger facts." in out
    assert "Mary backstory." not in out
    assert "Their history." not in out
    assert "### background/" not in out


def test_inspector_slice_recomputes_the_manifest():
    """The heading declares its own contents; a projection that drops entries
    and keeps the old count claims coverage it does not have
    (spec 2026-08-29-curated-artifacts-declare-their-contents-design.md)."""
    out = packet_assemble.inspector_slice(INSPECTOR_PACKET)

    assert "(2 entries: canon-core.md, 1 characters/)" in out
    assert "4 entries" not in out
    assert "background/" not in out


def test_inspector_slice_carries_only_the_section():
    out = packet_assemble.inspector_slice(INSPECTOR_PACKET)
    assert "## Word Budget" not in out
    assert "Band: 1-2" not in out


def test_inspector_slice_of_a_packet_without_the_section_is_empty():
    assert packet_assemble.inspector_slice("# Packet\n\n## Word Budget\n\nB\n") == ""
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/test_packet_assemble.py -k inspector_slice -v`
Expected: FAIL with `AttributeError: ... has no attribute 'inspector_slice'`.

- [ ] **Step 3: Write minimal implementation**

```python
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

    total = sum(counts.values())
    if counts:
        breakdown = []
        if "canon-core.md" in counts:
            breakdown.append("canon-core.md")
        breakdown += [f"{counts[s]} {s}" for s in sorted(counts) if s != "canon-core.md"]
        noun = "entry" if total == 1 else "entries"
        manifest = f"({total} {noun}: {', '.join(breakdown)})"
    else:
        manifest = "(0 entries)"

    return f"## Continuity Extracts {manifest}\n\n" + "\n\n".join(kept) + "\n"
```

Add `--inspector-slice` to `main()`'s flag tuple and dispatch to `inspector_slice` — extend the loop from Task 1 to `("--without-continuity", "--inspector-slice")`, and select the function by the captured flag. Update the usage string. **If both flags are passed, fail with exit 2 and a named message** — they are different projections and silently picking one would hide a runbook bug.

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_packet_assemble.py -v` — PASS.
Run: `python3 -m pytest` — expect **1332 passed** (1328 + 4). Update `CLAUDE.md:52` to 1332.

- [ ] **Step 5: Commit**

```bash
git add scripts/packet_assemble.py tests/test_packet_assemble.py CLAUDE.md
git commit -m "feat(packet): --inspector-slice projection, ledger without background

background/ is drafter fuel; characters/, locations/ and threads/ are the
ledger a chapter can contradict. Both real continuity blockers in the live
series traced to characters/. Cuts the two grading inspectors from 13,866
words of slice to roughly 4,363, and recomputes the manifest so the heading
cannot claim entries the projection dropped.

Spec: docs/superpowers/specs/2026-09-09-check-economics-design.md §3b

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: one-hop relationship entries need both ends named

19 of 39 entries in the live series' ch-01 slice arrive by one hop and are never named in the chapter — naming Maggie pulls `cal--maggie`, `george--maggie`, `maggie--saffron` and so on. A relationship entry earns its place only when both its ends are in the chapter.

**Files:**
- Modify: `scripts/packet_assemble.py` — `_continuity_slice`, lines 195-206 (the one-hop loop)
- Test: `tests/test_packet_assemble.py`

**Interfaces:**
- Consumes: nothing from Tasks 1-2.
- Produces: no signature change. `_continuity_slice` no longer returns a hopped entry whose stem contains `--` unless every `--`-separated segment names an entry already matched by name in the chapter text.

**This task changes the packet on disk and therefore its sha256** — by design (spec §6). Non-relationship one-hop entries are untouched.

- [ ] **Step 1: Write the failing tests**

Use the `series_tree` fixture; add continuity entries to the tmp tree inside the test. Read `test_assemble_slices_continuity_one_hop` (line 95) and `test_background_entry_loads_when_named` (line 159) first and follow their fixture style.

```python
def test_relationship_entry_needs_both_ends_named(series_tree):
    """A `a--b` entry linked from a named `a` does not ride along when `b` is
    absent from the chapter — 19 of 39 entries in the live series arrived this
    way (spec 2026-09-09-check-economics §2.3). The fixture's chapter 05 names
    Mary and Cal but NOT Saffron (verified against
    tests/fixtures/outlines/packet-format.md)."""
    bg = series_tree / "series/continuity/background"
    bg.mkdir(parents=True, exist_ok=True)
    (bg / "mary--saffron.md").write_text(
        "<!-- canon-meta: {id: mary--saffron, links: []} -->\n\n"
        "Mary and Saffron have history.\n", encoding="utf-8")
    (bg / "mary.md").write_text(
        "<!-- canon-meta: {id: mary, links: [mary--saffron]} -->\n\n"
        "Mary background.\n", encoding="utf-8")

    text = packet_assemble.assemble("01", "05", repo_root=series_tree).read_text(
        encoding="utf-8")

    assert "Mary and Saffron have history." not in text
    assert "### background/mary--saffron.md" not in text


def test_relationship_entry_rides_along_when_both_ends_are_named(series_tree):
    """Chapter 05 names both Mary and Cal, so `mary--cal` earns its place."""
    bg = series_tree / "series/continuity/background"
    bg.mkdir(parents=True, exist_ok=True)
    (bg / "mary--cal.md").write_text(
        "<!-- canon-meta: {id: mary--cal, links: []} -->\n\n"
        "Mary and Cal have history.\n", encoding="utf-8")
    (bg / "mary.md").write_text(
        "<!-- canon-meta: {id: mary, links: [mary--cal]} -->\n\n"
        "Mary background.\n", encoding="utf-8")

    text = packet_assemble.assemble("01", "05", repo_root=series_tree).read_text(
        encoding="utf-8")

    assert "Mary and Cal have history." in text


def test_non_relationship_one_hop_is_unaffected(series_tree):
    """The both-ends rule applies only to `--` entries; the fixture's existing
    one-hop link (characters/mary.md links to cal) must still resolve, which
    the pre-existing test_assemble_slices_continuity_one_hop also guards."""
    bg = series_tree / "series/continuity/background"
    bg.mkdir(parents=True, exist_ok=True)
    (bg / "the-archive.md").write_text(
        "<!-- canon-meta: {id: the-archive, links: []} -->\n\n"
        "Archive detail.\n", encoding="utf-8")
    (bg / "mary.md").write_text(
        "<!-- canon-meta: {id: mary, links: [the-archive]} -->\n\n"
        "Mary background.\n", encoding="utf-8")

    text = packet_assemble.assemble("01", "05", repo_root=series_tree).read_text(
        encoding="utf-8")

    assert "Archive detail." in text
```

Verified against the real fixture: `tests/fixtures/outlines/packet-format.md`'s chapter 05
block (279 words) word-matches **mary** and **cal** but not **saffron**, and the
`series_tree` fixture already writes `characters/{mary,cal,saffron}.md`. **The hop source must itself be
name-matched or the test is vacuous** — an entry that never matches by name is never in
`matched`, so its `links` are never traversed and the relationship entry never arrives
regardless of the rule. That is why each test writes `background/mary.md` (canon-meta
`id: mary`, which word-matches "Mary" in the chapter) as the source. It does not collide
with the fixture's `characters/mary.md`: `_continuity_entries` keys entries by
`"<subdir>/<stem>"`, so both exist independently and both match by name — which is exactly
the shape the live series has.

The fixture's chapter-05 block must name Mary and Cal but not "Absent" — confirm against `tests/fixtures/`'s packet outline - [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/test_packet_assemble.py -k relationship -v`
Expected: `test_relationship_entry_needs_both_ends_named` FAILS on `"Mary and Absent have history." not in text`. The other two should already pass — they guard against over-correction.

- [ ] **Step 3: Write minimal implementation**

In `_continuity_slice`, replace the one-hop loop (lines ~195-206):

```python
    named_stems = {entries[k]["path"].stem.lower() for k in matched}
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
                        part in named_stems for part in stem.split("--")):
                    continue
                matched.add(other_key)
```

`named_stems` is computed from the by-name matches **before** the hop loop adds anything, so a relationship entry can never qualify another relationship entry.

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_packet_assemble.py -v` — PASS. If `test_assemble_slices_continuity_one_hop` (line 95) fails, read it: if its fixture uses a `--` entry with an absent end, its expectation is now wrong and should be updated; if it uses an ordinary link, the implementation is over-broad — fix the implementation, not the test.
Run: `python3 -m pytest` — expect **1335 passed** (1332 + 3). Update `CLAUDE.md:52` to 1335.

- [ ] **Step 5: Commit**

```bash
git add scripts/packet_assemble.py tests/test_packet_assemble.py CLAUDE.md
git commit -m "fix(packet): a one-hop relationship entry needs both ends named

Relationship entries are reachable only by one hop, so naming a protagonist
pulled every relationship she is in — 19 of 39 entries in the live series'
ch-01 slice arrived that way and none was named in the chapter. CLAUDE.md
predicted this exactly ('keep them terse'); they run 3,069 words.

Changes the packet's sha256 by design — land at a chapter boundary and
re-run /map-chapter for anything mapped but not yet drafted.

Spec: docs/superpowers/specs/2026-09-09-check-economics-design.md §3b

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: wire the runbooks and agent definitions

The projections are inert until the dispatches use them. This is the task that actually spends the saving.

**Files:**
- Modify: `commands/map-chapter.md` (step 3), `commands/review-chapter.md` (steps 4 and 7b)
- Modify: `agents/inspector-structure.md`, `agents/inspector-voice.md`, `agents/inspector-ai-prose.md` (remove `ledger_slice` from declared inputs), `agents/inspector-continuity.md`, `agents/inspector-fairplay.md` (narrow it), `agents/map-maker.md`, `agents/developmental-editor.md`
- Test: `tests/` — a new contract-test module, modelled on `tests/test_drafter_loads_voice_pack.py`

**Interfaces:**
- Consumes: `--without-continuity` (Task 1) and `--inspector-slice` (Task 2) exactly as named.
- Produces: nothing consumed downstream.

**Read `tests/test_drafter_loads_voice_pack.py` first** — it is the established shape for asserting a runbook/agent-definition contract, and this task's tests should match it.

- [ ] **Step 1: Write the failing contract tests**

Create `tests/test_packet_projection_wiring.py`:

```python
"""The projections are inert unless the dispatches use them — these pin the
wiring (spec 2026-09-09-check-economics §3b)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_map_chapter_dispatches_the_map_maker_without_continuity():
    assert "--without-continuity" in _read("commands/map-chapter.md")


def test_review_chapter_uses_the_inspector_slice():
    assert "--inspector-slice" in _read("commands/review-chapter.md")


def test_review_chapter_gives_the_developmental_editor_no_continuity():
    assert "--without-continuity" in _read("commands/review-chapter.md")


def test_slice_free_inspectors_do_not_declare_a_ledger_slice():
    for name in ("inspector-structure", "inspector-voice", "inspector-ai-prose"):
        text = _read(f"agents/{name}.md")
        assert "ledger_slice" not in text, f"{name} still declares ledger_slice"


def test_grading_inspectors_still_receive_a_slice():
    for name in ("inspector-continuity", "inspector-fairplay"):
        assert "ledger_slice" in _read(f"agents/{name}.md")
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/test_packet_projection_wiring.py -v`
Expected: all five FAIL.

- [ ] **Step 3: Make the edits**

**`commands/map-chapter.md`, step 3** — the map-maker dispatch. Add, in the prose describing what it is passed: the packet is passed through the `--without-continuity` projection, with the reason (it prices scenes and places beats and clues; it never reads the continuity slice, and the slice is 13,866 words in a real series). Show the command:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/packet_assemble.py" $book $chapter --without-continuity
```

**`commands/review-chapter.md`, step 4** — replace "read it from there directly" with the split. `inspector-continuity` and `inspector-fairplay` get:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/packet_assemble.py" $book $chapter --inspector-slice
```

State plainly that `inspector-structure`, `inspector-voice` and `inspector-ai-prose` receive **no** continuity slice — structure works from the thread roster, voice from the lexicon plus the `voice_drift`/`lexicon_check` evidence, ai-prose from the rubric and the page. Keep the legacy no-packet fallback prose intact for the grading inspectors.

**`commands/review-chapter.md`, step 7b** — the developmental-editor is passed the packet through `--without-continuity`.

**Agent definitions** — update the `**Inputs:**` line and the Independence paragraph of each of the seven agents so the declared inputs match what they are actually handed. Do not change any agent's instructions or its scoring behaviour; only what it declares it receives.

**Do not write a bare `$` before a digit anywhere in a `commands/*.md` file.**

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_packet_projection_wiring.py -v` — PASS.
Run: `python3 -m pytest tests/test_runbook_arguments.py -v` — PASS (this is the guard against `$`-digit corruption).
Run: `python3 -m pytest` — expect **1340 passed** (1335 + 5). Update `CLAUDE.md:52` to 1340.

- [ ] **Step 5: Commit**

```bash
git add commands/ agents/ tests/test_packet_projection_wiring.py CLAUDE.md
git commit -m "feat(dispatch): spend the projections — cut the slice from five of eight

One 13,866-word continuity block was transmitted eight times per chapter
cycle, 66% of the token bill, to five recipients whose own agent definitions
never reference it. The map-maker and developmental-editor now get the
packet without it; structure, voice and ai-prose get no slice at all;
continuity and fairplay get the ledger without background prose.

A cycle drops from ~224,813 to ~105,937 tokens. No check is deleted, no
inspector stops running, no gate judgment changes.

Runbook edits need a session restart to take effect.

Spec: docs/superpowers/specs/2026-09-09-check-economics-design.md §3b

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Out of scope for this plan

- **Spec §3a** — turning on `tension_check`, running `voice_drift`/`lexicon_check` every round, the thread roster. Separate work.
- **Spec §3c** — any change to WHICH inspectors run, or making the developmental-editor opt-in. Deliberately deferred until voice and structure have run with their declared inputs.
- **The deferred Important from the guardrail branch** — demoting authored `Summary:`/`Opening:` values in `emit_outline`. Its own follow-up spec.
- **Do not re-cut or re-assemble the live series.** Task 3 changes packet hashes; the operator sequences that.
- **Do not push.**
