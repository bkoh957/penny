---
description: Build one chapter's packet, propose its prose map, and gate the map before drafting (spec 2026-07-18 §7 — replaces /build-briefs).
argument-hint: <book-number> <chapter-number>
---
# /map-chapter

Pass 1 of the per-chapter pipeline (design §2): **packet → map → draft → audit**.
The packet is a deterministic slice — no LLM, no judgment. The map is the one new
LLM product in this stage, and it takes the established posture: **an agent
proposes, the showrunner approves; only the approved artifact is stamped and
consumed.** Run from the series folder, after the book is locked.

## Steps

1. **Parse args and write the harness state marker:**

   ```bash
   book=$1
   chapter=$2
   mkdir -p .penny
   echo "book=$book chapter=$chapter stage=MAP" > .penny/current-stage
   ```

2. **Assemble the packet** (deterministic — slice + lookups, no LLM):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/packet_assemble.py" $book $chapter
   ```

   Writes `input/book-$book/packets/ch-$chapter.md`, stamped
   `built_from_outline:` / `built_from_whodunit:`. A non-zero exit names the cure —
   don't guess at it:
   - **No mystery lock** — the packet needs the sealed ledger's obligations; run
     `preflight lock-mystery $book` (or finish `/plot-book $book`) first.
   - **No `### Required Beats` section in the chapter's outline block** — this
     chapter is not yet in packet format (spec §3); migrate the block before
     assembling a packet. (Book 1 chapters not yet migrated stay on the legacy
     path — see `/draft-chapter`'s fallback — and are never routed through
     `/map-chapter` at all.)
   - **No outline / no chapter block** — the outline doesn't cover this chapter
     number; fix the outline first.

3. **Dispatch the `map-maker` sub-agent** with the packet text (pass `model:` =
   `plot_model` from `config/run-config.md`, defaulting to `drafting_model` when
   unset — planning work, same routing as the workshop; the agent def carries no
   `model:` frontmatter, so without this override it silently inherits the
   parent). It proposes the complete prose map — scene divisions, `Target:`
   ranges, free-text `Weight:` labels, `Beats covered:` lines for every packet
   Required Beat, and every ledger clue id placed in exactly one scene's `Clue:`
   field.

4. **Present the proposed map to the showrunner.** The showrunner edits/approves
   — this is a taste call (scene divisions and per-scene word targets are
   authored, not computed) and the map-maker never gets to decide it alone. Only
   the **approved** map is written, to `input/book-$book/maps/ch-$chapter.md`,
   stamped with the sha256 of the packet file it was built from:

   ```
   ---
   built_from_packet: <sha256 of input/book-$book/packets/ch-$chapter.md>
   ---
   ```

5. **Gate the approved map — no waivers at this level:**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/map_check.py" $book $chapter
   ```

   Findings are named, not vague: `band-mismatch` (scene targets can't sum into
   the chapter's band), `starved-scene` (a scene's max target is below the
   profile's `min_scene_words` floor), `unparseable-target` (a scene with no
   parseable `Target: A–B words` line), `dropped-beat` (a Required Beat lands in
   no scene), `duplicate-beat` (a Required Beat claimed by more than one scene),
   `unscheduled-clue` (a ledger clue id planted in no scene's `Clue:` line), and
   `stale-map` (the map's `built_from_packet` stamp no longer matches the packet
   on disk). **The map is not consumable until this exits clean.** Unlike the
   lock, there is no `--waive` here: a finding means fix the map (re-approve a
   revised proposal) or fix the outline (a genuinely overloaded chapter needs
   fewer Required Beats, not a forced fit) — never a recorded exception.

6. **Advance the marker:**

   ```bash
   echo "book=$book chapter=$chapter stage=MAPPED" > .penny/current-stage
   ```

   The chapter is now ready for `/draft-chapter $book $chapter`, which reads the
   map as its instruction and the packet as its context.
