# The background-history source layer

Date: 2026-08-13
Status: design, approved in conversation, not yet planned
Supersedes: nothing. Extends the authored-source → derived-slices pattern established by
`2026-08-03-story-source-layer-design.md` (below, "the source-layer spec").

## 1. Why

The showrunner's working process starts with a single long brainstorming document: the
town's history, the main characters, the history of their relationships, their secrets,
and the canon decisions those imply. That document exists — 72KB of it, at
`input/series/town-and-character-history.md` in the cozy series — and **nothing in the
engine reads it.** No script, no command, no agent. It has no consumer at all.

Meanwhile the file every prose-facing agent *does* read for setting,
`config/setting-pack/<place>.md`, is 837 bytes, was last edited two renames ago, and in
the cozy series still describes a town called Wreckers Bluff and a protagonist called
Cora. The series is Pelican's Crook and Maggie.

So the background the showrunner maintains is unreachable, and the background the engine
reaches is stale. This spec closes that gap with the pattern the engine already uses for
plot: **one authored source, a deterministic cut, derived files that nothing hand-edits.**

The failure this prevents is not that an agent reads nothing — it is that an agent reads
something *wrong* and no check can see it. `readiness_check.py` reports the stale pack as
`ready`, correctly: it verifies a setting prose file exists, never what is in it, because
the engine is location-agnostic by rule. No deterministic check can ever catch this class
of drift. Making the setting pack derived is what makes it correct by construction.

### 1.1 Elspeth, as the measurement

`Elspeth` appears **11 times in `input/book-01/story.md`**, 9 times in the background
document, and 4 times in `input/series/series-bible.md`. She has **no continuity entry**
and no mention in `canon-core.md`. She is a character book 01 runs on who exists only in
files the slice cannot load. That is the shape of the problem, not an oversight in one
series.

## 2. What the file is, and what it is not

`input/series/background-history.md` — series-level, singular, and permanent. It evolves
as the books are written; there is **no per-book copy and no versioning**. When book 3
changes what is true about the town, the showrunner edits this file and re-cuts. Book 1's
earlier state is recoverable from git and from nowhere else, deliberately: a versioned
background was considered and rejected as machinery serving a need the showrunner does
not have.

The series already carries three series-level authored documents whose boundaries have
drifted. This spec does not merge them, but names the division so the drift stops:

| File | Mood | Holds | Read by |
|---|---|---|---|
| `background-history.md` (new) | **indicative** — what is true | town history, character histories, relationships, secrets | the cut (§5) |
| `series-bible.md` | **imperative** — how to render it | calibration and drafting guardrails | `outline-expander`, `/review-outline` |
| `series-arc.md` | per-book premises | the 13-book long game | nothing, by its own spec |

The bible constrains the writing; the background supplies the facts. They overlap on the
same people (Tara/Marion, Maggie, George/Elspeth) and do not contradict today. Where they
overlap, **the background is the fact and the bible is the ruling** — a bible sentence
that states a fact rather than a constraint belongs in the background.

Note for a future session: `series-bible.md` currently holds book-01 psychological core,
which `penny-design-v3.md:120` assigns to neither the bible nor the arc. Out of scope
here; recorded so it is not rediscovered as new.

## 3. Format — the heading contract

The cut is mechanical because the document's headings are its contract. Nothing is
summarized and no LLM is involved at any point (§6.1).

```markdown
# <series name> — Background History

## Stance
<the compact block, authored by the showrunner — becomes the setting pack>

## Town
### <slug-able title>
### <slug-able title>

## Characters
### <Name> — <epithet>

## Relationships
### <Name A> and <Name B>

## Secrets
### <slug-able title>
```

- `## Stance` is **required**. Its body is the setting pack, verbatim.
- The four Part headings are each optional; an absent one cuts nothing.
- Every `###` under a Part heading becomes one derived entry. Its body is copied
  **verbatim** — the cut never rewrites prose.
- Free prose directly under a `##` heading (before the first `###`) is **reference only**
  and is not cut. This is where the showrunner's connective writing lives without
  becoming an entry.

**Slugging.** A `###` title is truncated at its first em dash, then lowercased with
non-alphanumerics collapsed to `-`, so `### Maggie — the woman who rebuilt without erasing
herself` becomes `maggie`. A `###` title **under `## Relationships`** splits on ` and `
and joins the two slugs with `--`, sorted, so `### Maggie and Cal` and `### Cal and
Maggie` both produce `cal--maggie` and collide loudly rather than producing two entries
(§5.2, `duplicate-entry`).

### 3.1 Why `## Stance` is authored rather than derived

The setting pack is loaded on **every chapter of every book**, and on the LM Studio path
is hard-truncated at 2,500 characters (`scripts/lmstudio_draft_chapter.py:387`). No
verbatim slice of fourteen sections of town history reaches that size, so an earlier
draft of this design had an agent compress Part I into the pack, with a showrunner
approval gate on the result.

**Both were cut.** Approval in this engine exists in exactly one situation — where a
generated artifact would otherwise be mistaken for a decision (`chapter-cutter` writing
`cut-plan.md` directly is the named case, "the same forged-certificate error"). A
compressed setting pack is not a decision; it is a lossy view of a decision already made
in the source, and if it is wrong the source is still right and re-cutting is free. An
approval gate there would buy nothing and would add showrunner touch on every re-cut.

But removing the gate leaves what the gate was covering for: **compression is lossy and
the loss is silent.** An agent that quietly drops "the town is ordinary to locals, strange
to the protagonist" trips no check; the prose is marginally worse in every chapter for
months. That is the same failure class as the fan-read leak of 2026-08-04 — a degradation
with no detector.

So the compression is removed instead of gated. The showrunner authors the compact block;
the cut copies it. This is what `story.md` already does with `## Questions`: nothing
derives them, they are written once and the cut copies them where they are needed. The
author decides; the machine links.

## 4. The derived tree

```
series/continuity/background/<slug>.md      one flat directory
config/setting-pack/setting.md              from ## Stance
```

**Flat, not nested.** `packet_assemble.py:60` walks a fixed allowlist of continuity
subdirs with a flat `*.md` glob, so a nested `background/characters/…` tree would be
invisible to the slice. The category is carried in each entry's `canon-meta` header
instead of in its path:

```markdown
<!-- canon-meta: {id: maggie, kind: character, links: [cal--maggie, faye--maggie], source: characters-maggie, built_from_background: …, cut_output_sha256: …} -->
```

`kind` is one of `town`, `character`, `relationship`, `secret`.

**The header is the `canon-meta` comment form, not YAML frontmatter.**
`packet_assemble.py` reads entries with `parse_canon_meta`, which only sees the comment
form — so an entry written as frontmatter contributes no `id` and no `links`, and gets no
one-hop. (Noted, out of scope: the cozy series' existing `characters/*.md` are frontmatter,
so one-hop linking is inert for them today.)

**Prerequisite fix.** `penny_meta.parse_canon_meta` splits its header on bare commas
(`inner.split(",")`), so `links: [cal--maggie, faye--maggie]` parses as `[cal--maggie` and
the rest is lost. Only single-element lists have ever been exercised
(`tests/test_packet_assemble.py:58`). `_split_top_level` already exists for exactly this
and is used by `parse_canon_sections`; `parse_canon_meta` must use it too. This is a
prerequisite of §4.1, not an optional cleanup — multi-link entries are the normal case.

A background entry and a continuity entry may share a stem — `background/maggie.md` beside
`characters/maggie.md`. `_continuity_entries` keys by `<subdir>/<stem>`, so they are two
distinct entries, and both carry the name `maggie`, so **both load together** when a
chapter names her. That is the mechanism §6.2 depends on.

**`setting.md` is a fixed filename**, not a place name. The engine must stay
location-agnostic (CLAUDE.md, "Readiness is genre/location-agnostic"), and
`readiness_check.py:131` accepts any `*.md` under `config/setting-pack/` other than
`lexicon.md` and `ai-tics-detection.md`, so a fixed name satisfies it without
reintroducing a hardcoded place.

### 4.1 Linking, and the one place it needs care

Relationship entries carry `links` to both their characters, and each character entry
carries `links` to the relationship entries it appears in. This is what makes them
reachable at all: `_word_match` tests an entry's stem and `canon-meta` id against the
chapter text, and the string `cal--maggie` never appears in prose. Without the character
→ relationship link, a relationship entry could never load.

**Accepted cost, stated plainly:** a chapter naming Maggie pulls every relationship entry
she is in. For a protagonist that is most of them. The mitigation is editorial, not
mechanical — relationship entries stay terse, because they are the entries most likely to
be loaded. If this proves too heavy in practice the fix is a `kind`-aware hop limit in
`_continuity_slice`, which is deliberately **not** built now.

## 5. The cut

`scripts/background_cut.py` — deterministic, stdlib only, no PyYAML (the dependency-split
rule; `canon-meta` headers are `penny_meta`'s job). Modelled on `story_cut.py`.

### 5.1 Stamps and re-cutting

Every derived file carries `cut_output_sha256` (of its own emitted body) and
`built_from_background` (of the source document) in its `canon-meta` header. Re-cutting is
free while a target's `cut_output_sha256` still matches its content, and refuses the
moment it does not.

**Absence is a refusal, not a licence** — a derived-path file with no `cut_output_sha256`
was never produced by a cut, so it is hand-authored work and the cut must not eat it. This
is the same branch that protects book 01's hand-authored `outline.md`, and it is also the
whole migration path (§8): a hand-authored file joins the layer by being deleted, which is
the showrunner's explicit act.

### 5.2 Findings — named, blocking, no waivers

Fix the source or fix the target; there is nothing to waive at this level (source-layer
spec §8).

| Finding | Fires when |
|---|---|
| `missing-stance` | no `## Stance` block, or its body is empty |
| `unknown-section` | a `##` heading that is not `Stance`/`Town`/`Characters`/`Relationships`/`Secrets` |
| `unknown-entry-depth` | a heading deeper than `###` anywhere inside a Part |
| `duplicate-entry` | two `###` titles slug to the same filename |
| `malformed-relationship` | a `###` title under `## Relationships` with no ` and ` separator |
| `unslugged-entry` | a `###` title slugs to `""` (e.g. pure punctuation) — no usable identifier |
| `unstamped-target` | a file exists at a derived path with no `cut_output_sha256` |
| `target-modified-since-cut` | a derived file's content no longer matches its stamp |

And two advisories on the non-blocking `notes` channel, never blocking — the roster stays
eight:

- **`orphan-derived`** — a derived file whose source `###` is gone. Reported by name,
  **never auto-deleted**: a removed heading is as likely to be a rename in progress as a
  deletion, and the cut destroying an entry on that guess is unrecoverable in a way the
  report is not.
- **`stale-setting-pack`** — a `config/setting-pack/*.md` file that is not `setting.md`
  (or one of the pack's other known contract files: `lexicon.md`, `ai-tics-detection.md`,
  `lmstudio-digest.md`). The cut cannot refuse it — `target_refusal` only guards paths it
  is about to write, and this file is not one of them — but
  `lmstudio_draft_chapter._read_config_pack_for_lmstudio` concatenates every `*.md` in the
  directory, so a stale hand-authored pack still reaches every drafting agent until the
  author deletes it. Reported, never deleted, for the same reason as `orphan-derived`:
  deleting a file the author wrote is the author's act.

Exit 0/1/2 (clean / findings / usage), matching `map_check.py`.

## 6. What the cut never writes, and why

### 6.1 No LLM, anywhere

There is no proposing agent and no approval gate in this design (§3.1). The cut is a text
transformation with named refusals.

### 6.2 Never `series/continuity/characters/`

Those files already have a writer: `ledger-updater` appends knowledge-state and
established facts to them after every finalized chapter. Two writers in one file is where
this class of design fails, and here both writers are legitimate and ongoing — a re-cut
would clobber the accumulated record every time.

Separate homes were chosen over sectional ownership inside one file. It is the only option
under which re-cutting stays genuinely free forever, and it keeps the two kinds of
knowledge honestly distinct: **background is what the showrunner decided; the ledger is
what the books put on the page.** When they disagree, that should be visible, not silently
resolved in favour of whichever ran last.

### 6.3 Never `canon-core.md`

Promotion to canon-core is a showrunner act — `ledger-updater` is explicitly forbidden
from touching its body, and this cut inherits that guard. canon-core is loaded on every
chapter forever; what goes in it is a decision, not a derivation.

### 6.4 Never any whodunit ledger

`## Secrets` cuts to `background/`, not to `series/whodunit/book-NN.yaml`.

The whodunit ledger is **per book and gets frozen**; the background is **series-level and
never freezes**. The ledger already has two writers (the showrunner, and `story_cut.py`
rewriting `plant_chapter:`) and is safe only because the cut runs before
`preflight lock-mystery`. A series-level document writing into a per-book sealed file
would either fail after the lock or forge past it.

So the boundary lands where it is actually sharp: **the background says what is true; the
ledger says what this book plants and when.** A secret is defined once in the background;
each book's ledger references it as a clue or red herring. The lock never sees the
background document.

**Accepted cost:** renaming a secret in the background does not check that book-01's
ledger still agrees. The connection is showrunner discipline, not a finding. Ids are not
cross-checked because doing so would give a never-freezing series file a say over a sealed
per-book one — the coupling this section exists to prevent.

## 7. Consumers

| Consumer | Change |
|---|---|
| `packet_assemble.py` | add `background` to `_CONTINUITY_SUBDIRS`; entries join the slice on the existing trigger |
| `drafter`, `chapter-cutter`, `outline-expander`, `developmental-editor` | `Inputs:` path change to the derived setting pack |
| `config/review-rubrics/developmental-craft.md:30` | same path change |
| `story-author` | **new** `Inputs:` — the stance block, plus background entries for the strands in its beat range |
| `plot-proposer` | **new** `Inputs:` — the stance block |

**The setting pack is not embedded in the packet.** The packet carries what varies per
chapter and stamps `built_from_*` on it; setting is global and constant, so embedding it
would make all 28 packets stale on every one-line edit. The existing design already draws
this line — the continuity slice is in the packet, the voice pack and genre pack are not.
Setting belongs on the second side and stays a direct read.

`story-author` receives a **slice, not the whole background**, triggered by the `@strand`
tags in the range it is working. Context discipline is the engine's own rule (design §4.2,
"keep it tiny; every line taxes every chapter"), and an agent writing five beats does not
need twelve character histories.

## 8. Migration (cozy series; not engine work)

1. `git mv input/series/town-and-character-history.md input/series/background-history.md`
2. Author `## Stance`; conform the Part/entry headings to §3.
3. **Delete `config/setting-pack/coastal-victoria-au.md`.** The cut does not refuse this
   file — `target_refusal` only guards paths it is about to write, and this stale sibling
   is not one of them. Left in place, it keeps reaching every drafting agent alongside the
   derived `setting.md`, since `lmstudio_draft_chapter._read_config_pack_for_lmstudio`
   concatenates every `*.md` in the directory. The cut *names* it as an advisory
   (`stale-setting-pack`, §5.2) on every run until it is gone. Deleting is the
   showrunner's explicit act.
4. Run the cut. `series/continuity/characters/` is untouched throughout.
5. Give **Elspeth** an entry (§1.1).

## 9. Out of scope

- Per-book background copies, deltas, or any book tier in the overlay.
- Writing `canon-core.md`, `series/continuity/characters/`, or any whodunit ledger.
- Any LLM step, proposing agent, or approval gate.
- Reconciling `series-bible.md`'s book-01 core (§2), or filling `series-arc.md`.
- A `kind`-aware hop limit in `_continuity_slice` (§4.1).
- Cross-checking secret ids against a book's whodunit ledger (§6.4).

## 10. Testing

Test-first against `tests/fixtures/`, per the engine convention.

- **Contract parsing:** each Part heading cuts its entries; free prose under a `##` is not
  cut; an absent Part cuts nothing; `## Stance` becomes the setting pack byte-for-byte.
- **Slugging:** em-dash truncation; relationship titles sort and join; `Maggie and Cal` and
  `Cal and Maggie` collide as `duplicate-entry`.
- **Each of the eight findings** fires on its own fixture and does not fire on the clean
  one — enumerated by reading the source, never by grepping for finding strings (the
  Step-5 lesson from `2026-08-12`).
- **`orphan-derived` is advisory**: it rides `notes`, exits 0, and leaves the file on disk.
- **Idempotence:** cutting twice with no source change writes no new bytes and reports
  clean.
- **Stamp guards:** an unstamped target refuses; a hand-edited derived file refuses; a
  re-cut after a source edit succeeds and rewrites.
- **Never-writes:** a cut over a fixture with populated `characters/`, `canon-core.md`,
  and `whodunit/book-01.yaml` leaves all three byte-identical.
- **Slice integration:** a background entry named in a chapter lands in that chapter's
  packet; one-hop pulls its relationship entries; an unnamed entry stays out.
