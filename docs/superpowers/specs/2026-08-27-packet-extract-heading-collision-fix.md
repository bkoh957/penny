# Packet extract heading collision

Date: 2026-08-27
Status: defect, fix brief — not a feature proposal
Severity: high — silent, affects every chapter of every book, weakens Tier-1 continuity

Filed in `specs/` rather than `backlog/` deliberately: `docs/backlog/README.md` excludes
defects ("If the engine is wrong, fix it"). This is a defect, but the fix requires choosing
between options, so it is written up rather than simply patched.

## 1. Why

`packet_assemble.py` embeds continuity source files into the packet **verbatim, with their
own markdown headings intact**:

```python
# scripts/packet_assemble.py:103
parts.append(f"### canon-core.md\n\n{canon_core_path.read_text(encoding='utf-8').strip()}")
# scripts/packet_assemble.py:109
parts.append(f"### {rel.as_posix()}\n\n{e['text'].strip()}")
```

Those parts are then dropped under a `## Continuity Extracts` heading
(`packet_assemble.py:210`). Any embedded heading at level 1 or 2 therefore **terminates the
section that is supposed to contain it.**

`/review-chapter` step 4 and `/draft-chapter` step 3 both instruct agents to read the
ledger slice from "the `## Continuity Extracts` section of the packet". An agent that
honours that instruction by parsing markdown structure gets a fraction of the slice and is
given no signal that anything is missing.

## 2. Evidence from a real book

Pelican's Crook, book 01, chapter 01. `input/book-01/packets/ch-01.md` heading map:

```
  8  ## Chapter 01 — The Life She Bought [type: opening]
101  ## Ledger Clues
105  ## Continuity Extracts      <-- section opens
124  ## Practical canon decisions (book 1)   <-- canon-core.md's OWN heading; section ends
577  ## Established facts        <-- characters/elspeth.md's own heading
590  ## Knowledge state          <-- characters/elspeth.md's own heading
672  ## Standing Series Guardrails
676  ## Word Budget
```

The section is declared at 105 and structurally closed at 124. **A section-scoped read
yields 19 lines of a slice that actually runs to line 576** — roughly 4%.

The 30 `background/*.md` entries at lines 148–576 and the 6 `characters/*.md` entries are
all orphaned: structurally they appear to belong to "Practical canon decisions (book 1)".

**Which sources offend:**

- `series/continuity/canon-core.md` — 2 headings, `# Canon Core` (**level 1**, outranking
  the packet's own `# Packet — Chapter 01` title) and `## Practical canon decisions (book 1)`.
  This is the first break and the damaging one, 19 lines in.
- `series/continuity/characters/*.md` — 9 files, 1–3 headings each (`## Established facts`,
  `## Knowledge state`).
- `series/continuity/background/*.md` — 30 files, **zero** headings. Clean, and the reason
  the bug is not total.

**Observed cost.** On 2026-08-27, `inspector-continuity` was dispatched for ch 01 with the
standard instruction. It reported reading "lines 105–123" and stated that "no brief-derived
or one-hop entries were present in that section." It returned a clean 5/5 having never seen
`maggie.md`, `marion.md`, `faye.md`, `tara.md` or `wheelhouse.md` — the entries the chapter
most depends on. A re-run given an explicit line range (`sed -n '105,576p'`) confirmed all
30 background entries and also returned 5/5. **The verdict was right by luck, not by
process.** Every other chapter of every book has been running the same way.

`inspector-structure` reported the same 105–123 range in the same run.

The failure is silent by construction: a truncated read produces a confident verdict, and
nothing in the gate can distinguish it from a complete one.

## 3. Fix

### Recommended: demote embedded headings, and add a manifest line

**3a. Demote on embed.** Before interpolating source text, rewrite every `^#{1,6} ` in it to
sit strictly deeper than its `###` wrapper. `# Canon Core` becomes `##### Canon Core`,
`## Practical canon decisions` becomes `###### ...`, and so on, clamped at 6.

This keeps the packet readable as markdown, keeps embedded structure visible, and makes the
section boundary correct by construction. Both call sites (`:103` and `:109`) need it, so it
belongs in a small shared helper rather than inline twice.

**3b. Emit a manifest.** Change the section heading line to carry a count, e.g.

```
## Continuity Extracts (37 entries: canon-core.md, 30 background/, 6 characters/)
```

Cheap, and it converts a silent failure into a checkable one: any agent — or any future
inspector prompt — can verify it read what the packet says it contains. 3a alone fixes the
defect; 3b is what stops a future regression being invisible.

### Rejected

- **Fence embedded text in code blocks.** Robust against every heading level, but it strips
  emphasis and structure from canon the drafter is meant to read as prose, and turns 470
  lines of continuity into an undifferentiated block.
- **Require source files to be heading-free.** Pushes an engine serialisation constraint
  onto authored canon. `canon-core.md` is hand-maintained by the showrunner and its headings
  are meaningful; the engine should absorb this, not delegate it.
- **Emit explicit line ranges into the review prompts.** Works — it is what the re-run used —
  but it is a workaround at the call site, has to be recomputed per chapter, and leaves the
  packet itself malformed for every other consumer.

## 4. Test

The regression test writes a packet whose continuity source contains a level-1 and a level-2
heading, then asserts that between the `## Continuity Extracts` heading and the next
sibling `##` heading, all emitted extract entries are present. That assertion fails on
today's code and passes after 3a.

A second test asserts the manifest count matches the number of `### ` entries actually
emitted.

## 5. Blast radius

Every consumer that reads the slice by section: `inspector-continuity`,
`inspector-fairplay`, `inspector-structure`, `inspector-voice`, `inspector-ai-prose` (all via
`/review-chapter` step 4) and `drafter` (via `/draft-chapter` step 3, though the drafter is
usually told to read the whole packet and so is less exposed).

No packet needs regenerating for correctness of *content* — the text was always all there.
Packets regenerate on their own next `packet_assemble` run, which changes their sha and
therefore requires re-stamping any map built against them. That is routine.
