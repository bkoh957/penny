# Curated artifacts declare their contents

Date: 2026-08-29
Status: §4a shipped 2026-08-31 (showrunner approved that site only). §6's open
decision — whether consumers echo back what they read — is untouched, and its
recommendation still stands: do not build receipts yet.
Severity: n/a — this is preventive, not a defect brief

Filed as a design rather than a defect because nothing here is currently broken. It is the
general shape behind four defects fixed on 2026-08-27/29, and the cheap half of a remedy
whose expensive half should not be built yet.

Related, and the evidence for all of it:
`2026-08-27-packet-extract-heading-collision-fix.md`,
`2026-08-27-voice-drift-discards-evidence-fix.md`,
`2026-08-29-engine-holds-story-details-fix.md`,
`2026-08-29-runbook-render-corrupts-positional-vars-fix.md`.

## 1. Why

Four defects in three days shared a description — *an agent received an input that differed
from what the repository intended, and nothing could see it* — and that description is
where the analysis usually stops. It should not, because those four are **three different
mechanisms** and only one of them is addressed by anything proposed here.

**A — Framing.** Every byte arrived; the structure a reader navigates by lied. Continuity
sources were embedded with their own `#`/`##` headings intact, so an embedded heading closed
the `## Continuity Extracts` section that was supposed to contain them. `inspector-continuity`
read 19 lines of a 470-line slice, reported reading "lines 105–123", and returned a clean 5/5.

**B — Transmission.** The text the agent received genuinely differed from the file on disk.
Runbook rendering substitutes argument placeholders, so `index($0, h)` arrived as
`index(01, h)` and the extracted brief was empty.

**C — Producer.** The input was transmitted perfectly and was itself wrong. `voice_drift`
computed which words repeated and discarded them; `line-edit.md` asserted a story fact that
contradicted the voice pack.

A manifest addresses **A**. It cannot address **B** — a channel that corrupts the payload
corrupts the manifest with it. It has nothing to say about **C**, which happens before
transmission. §7 records what those two need instead, so this design is not mistaken for a
general remedy.

## 2. What the engine already has, and the gap

Penny already refuses to take an artifact's word for itself. `built_from_outline`,
`built_from_packet`, `built_from_story`, `built_from_whodunit`, `cut_output_sha256` — plus
out-of-band certificates, which exist precisely because *"never represent 'locked/validated'
as a field inside the data it gates (a field would be a forgeable certificate)"*.

Every one of those describes **what an artifact was built from**. None describes **what it
contains**, and nothing anywhere describes **what a consumer got out of it**.

That is the whole gap. An agent handed a curated slice has no way to tell a complete read
from a truncated one, because the artifact never said how much there was.

## 3. The rule

> **A section that was curated by omission declares what it contains.**

"Curated by omission" is the test, and it is narrow on purpose. A section qualifies when the
engine chose a subset and the consumer cannot reconstruct the choice. The chapter block does
not qualify — it is the whole block. `## Word Budget` does not — it is one value. The
continuity slice does: thirty-seven entries were selected out of hundreds, and nothing on the
page said thirty-seven.

The declaration is a **count and a breakdown, derived from what was actually emitted** —
never from a second walk of the source, which would let the two disagree. `packet_assemble`
already does this:

```
## Continuity Extracts (37 entries: canon-core.md, 30 background/, 6 characters/)
```

## 4. The sites

**Shipped.** `## Continuity Extracts` — `packet_assemble.py`, 2026-08-29.

**4a. `## Ledger Clues` — SHIPPED 2026-08-31. It was the same bug, latent.**

`packet_assemble.py:293` interpolates a ledger description raw:

```python
clue_lines.append(f"- [{cid}] plant_chapter {chnum}: {desc}")
```

`desc` comes from an authored YAML ledger. In the live book **ten of forty-five clue entries
have multi-line descriptions** (block scalars). None currently contains a line beginning
`## `, so this is latent rather than live — but it is one authored heading away from
terminating `## Ledger Clues` exactly as canon-core's heading terminated Continuity Extracts.
And the consequence is worse: a truncated clue list means a chapter plants fewer clues than
the ledger scheduled, which `inspector-fairplay` grades against the sealed ledger and the
reader ultimately pays for.

Two changes, both mirroring the fix already shipped one section up:

- Run each description through `packet_assemble._demote_headings` before interpolating.
- Declare the count: `## Ledger Clues (3 scheduled: c02-…, c05-…, rh-01-…)`.

Both landed as written. Zero scheduled reads `(0 scheduled)`; the adjective needs no
pluralisation, so the `entry`/`entries` grammar §5.3 asks about does not arise here. A
third change was made beyond the two bullets: the manifest is documented in all three
contracts that read a packet — `drafter`, `map-maker`, `review-chapter` — as the
Continuity Extracts manifest already was. A declaration nobody is asked to compare
against is decoration, and §3's argument is about the consumer's ability to notice.

**4b. The brief.** `scripts/extract_brief.py` output, consumed by `ledger-updater` and
`ledger_markers.py --brief`. It is a whole chapter block, so it is not curated by omission
and does **not** need a manifest by §3's test. Listed here only to record that it was
considered and excluded — the failure it had was emptiness, and that is now a loud refusal.

**4c. The reader's copy — already compliant, and the model to copy.**
`plot_stage.readers_copy_text` declares its own truncation:

> Chapters 1–N. The book continues past this point…

That is a manifest in prose. It is why the blind fan cannot mistake a staged copy for a whole
book, and it is the precedent for everything above.

**4d. The direct pack reads.** `drafter`, `chapter-cutter`, `outline-expander` and
`developmental-editor` read the whole of `config/setting-pack/` through the three-tier
overlay. A file added by one tier and shadowed by another is invisible, and the agent has no
way to know the resolved set. Lower priority than 4a — no defect has come from it — but it is
the same shape and worth a `resolve-dir` style listing if one is ever cheap to add.

## 5. Test

1. For each manifested section: the declared count equals the number of entries actually
   emitted in that section. Derive both from the artifact, so the test cannot pass by reading
   the same variable twice.
2. For `## Ledger Clues`: a description containing a `## ` line does not terminate its
   section — the direct analogue of the Continuity Extracts regression test, and the one that
   would catch 4a going live.
3. Zero-entry and one-entry manifests read correctly (`(0 entries)`, `1 entry` — grammar the
   existing manifest already handles).

## 6. The open decision

**Do receipts get built at all?**

The full remedy has two halves. This design is the first: artifacts declare their contents.
The second is that consumers **echo back what they read** — a `read:` block in the verdict
envelope (`penny-verdict/1` → `/2`), naming the sections and ids consumed, with a
deterministic checker diffing receipt against manifest and emitting a blocking `short-read`.

Receipts would be sound here. These failures are not adversarial: `inspector-continuity`
honestly reported an honest read of misleading input, and the mismatch against a manifest is
exactly the signal. Self-reporting is reliable precisely because the agent is not the liar.

**Recommendation: do not build them yet.** A manifest alone does most of the work, because an
agent told "37 entries" that can see two will say so unprompted — and it costs no schema
change, no new checker, and nothing for every agent to remember. Build the receipt loop only
if a manifested section is observed to be under-read anyway.

This is the engine's own instinct, stated in
`2026-08-27-texture-allocation-design.md` §4.3 about a different problem:

> **Do not build the manifest until the simple version is observed to fail.**

## 7. What this does not fix

Recorded so the design is not over-claimed.

**B, transmission.** A manifest travels down the corrupted channel with the payload. The
remedy is routing, not verification: *logic complex enough to contain a `$` that is not a
command argument belongs in `scripts/`*, which is never rendered. Shipped as
`extract_brief.py`; the general rule belongs in `CLAUDE.md` alongside the architectural rule.

**C, producer.** Two different remedies, both already shipped, neither involving transmission:
an invariant at the producer (`voice_drift`'s `UnevidencedFlagError` — a flagged tic with no
evidence raises) and a precedence rule for contradictory inputs (`line-edit.md`/`copy-edit.md`:
where this checklist conflicts with the pack, *that file wins*).

The lesson worth keeping: **"the agent got the wrong input" is a symptom with at least three
causes, and they need three different fixes.** A single general remedy would have fixed one
of the four defects and left three.
