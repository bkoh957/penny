# Chapter status manifest

Date: 2026-09-08
Status: design, approved in conversation, not yet planned
Supersedes: nothing. Extends `scripts/book_status.py` (spec `2026-08-01-book-status-design.md`)
by relocating its per-chapter view rather than replacing it.

## 1. Why

Per chapter, check state lives in four places, and none of them is the chapter file
itself:

- the draft's own frontmatter (`drafted_by` / `drafted_on` / `drafted_words`);
- `output/book-NN/chapters/ch-MM.reviews/*.md` — one verdict file per check that ran:
  the deterministic checkers (`voice-drift.md`, `lexicon-fluency.md`), one per inspector
  in the active genre's roster, and the developmental read. Each carries `producer`,
  `kind`, `score`, `reviewed_by`, `reviewed_draft_sha256`, and any `^BLOCKING:` lines.
  The directory holds only what ran, which is why a missing check is invisible here —
  there is no empty row to notice, only a file that is not there;
- `ch-MM.gate.md` — the PASS/HOLD summary `review_gate.py` writes;
- `.penny/locks/book-NN.ch-MM.dev-clear` — the developmental clearance certificate,
  bound to a draft hash via `cleared_draft_sha256`.

`scripts/book_status.py NN MM` already prints a six-row RUN/PASS table for one chapter
(`one_chapter_rows`), so almost all of this information already exists somewhere
machine-readable. What is missing is not data, it is proximity: the showrunner opens the
chapter to read the prose, and the status is three commands away.

**The motivating case.** In the user's series, `book-01/ch-02` has all six agent verdicts
written and clean, and there is no `ch-02.gate.md` at all — the gate was never computed.
Its reviews directory also has no `voice-drift.md` and no `lexicon-fluency.md`, so the two
deterministic 2a checkers never ran either. Nothing in any view the showrunner has —
opening the draft, opening the reviews directory, or running `/book-status` — surfaces
either gap in one look. Two of eight steps silently never ran on a chapter that otherwise
looks finished.

## 2. What is built

A **chapter status manifest**: a rendered summary block stamped into the DRAFT file only,
immediately after its frontmatter, between two HTML-comment delimiters:

```
<!-- penny-manifest v1 · derived <date> · never read back · refresh: /chapter-manifest NN MM -->
... rendered content ...
<!-- /penny-manifest -->
```

The delimiter line names its own refresh command so a showrunner reading a stale draft in
an editor, with no terminal open, still knows what to run.

The rendered content is:

1. a heading line naming the book and chapter;
2. a draft identity line — word count, `drafted_by`, `drafted_on`, and a short sha of the
   draft;
3. a three-column markdown table, `step/check | status | details`, one row per stage in
   the chapter's whole chain — not only the review gate: packet, map, draft, the two
   deterministic checkers (voice-drift, lexicon), each of the active genre's inspectors,
   developmental, GATE, dev-clear, final;
4. a `blockers:` line;
5. a `next:` line.

**The details column always names a file, rendered relative to the series root** — the
same convention `book_status.py`'s `_rel` helper already uses for its WHY/ARTEFACT
column. A NOT-RUN row still names its file: an empty row and a missing file are the same
fact, and the column is where the showrunner learns where the thing would land if it ran.

**Staleness folds into the status cell**, not into a separate column. Each verdict
carries `reviewed_draft_sha256`; when it no longer matches the draft's own hash, the cell
reads, for example, `4 · clean · STALE (an older draft)`. This is the one genuinely new
fact the manifest adds — everything else is relocation. `book_status.py` today would still
report a gate as having run after the chapter was redrafted underneath it; nothing
currently compares a verdict's recorded hash against the *current* draft hash and folds
the answer into the same cell the score lives in.

**On a HOLD**, every `^BLOCKING:` line is listed under `blockers:` together with its
producing agent, so the summary answers "what is wrong", not merely "something is".

### 2.1 Worked example — book-01/ch-02, as it stands today

```markdown
<!-- penny-manifest v1 · derived 2026-09-08 · never read back · refresh: /chapter-manifest 01 02 -->
## Chapter status — book 01, ch 02

Draft: 2,105 words · claude-opus · 2026-09-08 · c15bb88

| step / check          | status                        | details |
|------------------------|--------------------------------|---------|
| packet                 | built                          | input/book-01/packets/ch-02.md |
| map                    | built                          | input/book-01/maps/ch-02.md |
| draft                  | 2,105 words                    | output/book-01/chapters/ch-02.draft.md |
| voice-drift            | NOT RUN                       | output/book-01/chapters/ch-02.reviews/voice-drift.md |
| lexicon                | NOT RUN                       | output/book-01/chapters/ch-02.reviews/lexicon-fluency.md |
| inspector-continuity   | 5 · clean                     | output/book-01/chapters/ch-02.reviews/continuity-drift.md |
| inspector-voice        | 4 · clean                     | output/book-01/chapters/ch-02.reviews/character-voice.md |
| inspector-fairplay     | 4 · clean                     | output/book-01/chapters/ch-02.reviews/fairplay-planting.md |
| inspector-structure    | 4 · clean                     | output/book-01/chapters/ch-02.reviews/structure-tension.md |
| inspector-ai-prose     | 4 · clean                     | output/book-01/chapters/ch-02.reviews/ai-prose-taste-flags.md |
| developmental          | 4 · advisory                  | output/book-01/chapters/ch-02.reviews/developmental-edit.md |
| GATE                   | NOT RUN                       | output/book-01/chapters/ch-02.gate.md |
| dev-clear              | NOT RUN                       | .penny/locks/book-01.ch-02.dev-clear |
| final                  | not written                   | output/book-01/chapters/ch-02.final.md |

blockers: none recorded
next: /review-chapter 01 02 — six verdicts exist, but neither checker ran and the gate
was never computed
<!-- /penny-manifest -->
```

Every existing verdict is clean and no `^BLOCKING:` line has ever been written for this
chapter, which is exactly why nothing has surfaced the gap before: a showrunner scanning
five green inspector scores has no reason to suspect the gate summarizing them was never
computed. The manifest's `next:` line is the first place in the pipeline that says so in
one sentence.

## 3. The hard invariant

**The manifest is derived and never read. It is written by one script and consumed by
nothing.** No gate, no preflight, no command, and no agent may ever parse a value out of
it. If the manifest and the artefacts disagree, the artefacts are right and the manifest
is stale.

This is not a style preference; it is CLAUDE.md's rule under "Locks and certificates,"
applied directly: a validated state must never be represented as a field inside the data
it gates, because a field is a forgeable certificate. A `gate: PASS` line sitting inside
the chapter's own file is exactly that shape — a status claim living in the same document
whose status it claims to report. The manifest is safe to ship *only* because nothing
downstream trusts it. It has the same standing as `drafted_words`: measured and stamped
for a human to read, but never read back as authority for anything.

Every section below exists to protect this invariant against the two ways a manifest
could otherwise compromise the pipeline it reports on.

## 4. Finding 1 — stamping would block finalization

`scripts/preflight.py`'s `draft_sha256()` (line ~73) hashes the whole draft file's raw
bytes:

```python
return hashlib.sha256(p.read_bytes()).hexdigest()
```

Every inspector verdict records that hash as `reviewed_draft_sha256`; the dev-clear
certificate records it as `cleared_draft_sha256` (`cmd_clear_dev`, same file). Therefore:
refreshing the manifest after `/review-chapter`, or after `preflight clear-dev`, changes
the draft's bytes. The dev-clear cert stops matching the new hash, `preflight finalize`
refuses, and every existing verdict now reads STALE — because the file that carries the
manifest is the same file whose hash the manifest itself is trying to report on. The
manifest would break the very staleness it exists to surface.

**The fix:** `draft_sha256` must hash the draft with the manifest block stripped out
first, not the raw bytes.

**Why this is safe to ship into an existing repo:** on a draft carrying no manifest block,
stripping is a no-op that returns the input unchanged. Every hash already recorded on disk
today — every `reviewed_draft_sha256`, every `cleared_draft_sha256` — was computed over a
manifest-free draft, so it still matches the same draft hashed the new way. No existing
series needs re-locking, no chapter needs re-review, and no in-flight book needs any
migration step at all. The change is backward compatible by construction, not by
convention: it only ever *removes* bytes that could not have existed before this spec
shipped.

`scripts/book_status.py`'s `_sha()` (line ~82) hashes raw bytes the same way and compares
it against the dev-clear cert in `one_chapter_rows()` (`cleared = yes() if rec and rec ==
_sha(draft) else no()`) and in `chapter_rows()`'s aggregate loop. It needs the identical
strip, for the identical reason: otherwise `/book-status` starts reporting a chapter's
dev-clear as broken the moment its manifest is refreshed, which is the same bug in a
second reader.

## 5. Finding 2 — a manifest breaks inspector isolation

CLAUDE.md, "Independence, isolation, reader simulation": isolation means each inspector
gets one chapter, one rubric, one ledger slice, and **never** another inspector's verdict.
A table sitting above the prose that lists all five inspectors' scores is precisely
another inspector's verdict, embedded in the chapter text the next inspector reads. On any
re-review, every inspector would see the previous run's results before forming its own —
cross-talk, silently, on every second pass over a chapter.

Two mitigations, both required — neither is sufficient alone:

**(a) Strip before dispatch.** `/review-chapter`'s existing re-run cleanup step (step 2,
which today calls `scripts/reset_reviews.py` to empty the reviews directory and remove the
stale sibling `gate.md`) is extended to also remove the manifest block from the draft. The
draft therefore carries no manifest for the whole duration of a review run — inspectors,
the deterministic checkers, and the developmental editor all read a manifest-free draft.
The block is re-stamped once, at the end of the run, after the gate is computed.

**(b) Strip at every hand-off.** Any draft text ever handed to an agent — not only inside
`/review-chapter` — is passed through the strip helper first. No runbook may hand an agent
a draft carrying the block. This covers hand-offs the re-run cleanup does not reach: a
fresh `/draft-chapter` reading the previous chapter's tail, `/finalize-chapter`'s
line-editor and copy-editor reading the current chapter, and any future agent that reads
a draft outside the review path.

## 6. What ships

**New module `scripts/penny_manifest.py`** — the single owner of the block. Dependency-free
per CLAUDE.md's dependency-split rule: it uses `scripts/penny_meta.py`, never PyYAML, since
the manifest is boilerplate the engine derives, not nested human-edited data. It exposes
three functions:

- `strip(text) -> str` — remove the delimited block; a no-op when the block is absent.
- `render(book, chapter) -> str` — pure; builds the block from artefacts already on disk.
  Takes no draft text as input and mutates nothing.
- `stamp(book, chapter) -> None` — strip, then insert the freshly rendered block; calling
  it twice in a row produces the same file both times.

**Genre-agnostic**, per CLAUDE.md's non-negotiable engine rule: the inspector rows come
from `scripts/penny_genre.py`'s `inspectors()` resolution (the active genre's
`genre.yaml` roster), never a hardcoded list of inspector names. A series running a genre
pack with a different inspector roster gets a manifest with different rows, with no
change to `penny_manifest.py`. Do not reintroduce a hardcoded inspector or genre filename
inside this module.

**Five existing readers route through `strip()`**, so the block is invisible to every
script that measures or hashes the draft:

- `scripts/preflight.py` `draft_sha256` (finding 1, §4);
- `scripts/book_status.py` `_sha` (finding 1, §4);
- `scripts/draft_words.py` `stamp_words` — it currently counts
  `word_count(strip_frontmatter(text))`; without the added strip, the manifest's own
  words (headings, table, blockers/next lines) would inflate `drafted_words`, corrupting
  the one field in this whole system whose entire purpose is to be a trustworthy
  measurement rather than a guess;
- `scripts/voice_drift.py` — it already calls `strip_frontmatter` at `analyze()` (line
  ~107) before scanning prose; the manifest strip goes in the same place, for the same
  reason a frontmatter block must not be scanned as prose;
- `scripts/lexicon_check.py` — it reads the chapter text directly before scanning (line
  ~160); the manifest block is not the whodunit ledger and must not be scanned as
  chapter prose either.

**Refresh points** — where `stamp()` is called automatically:

- end of `/draft-chapter` and `/draft-chapter-lmstudio`, after `draft_words.py` runs;
- start of `/review-chapter` (removed, per §5a) and again at its end, after the gate is
  computed;
- after `preflight clear-dev` mints the dev-clear certificate;
- a new standalone command, `/chapter-manifest NN MM`, for refreshing on demand — the
  case in §2.1, where the showrunner wants to know the current state without re-running
  anything.

Automatic refresh at every point that changes chapter state matters for the reason
`book_status.py`'s own module docstring gives for replacing `.penny/current-stage`: two
statuses per row exist "because 'done' is two questions," and collapsing them into one
label "reproduces the `.penny/current-stage` failure this replaces: a label someone typed,
which has read OUTLINE-REVIEWED for days while the book moved on." A manifest the
showrunner must remember to refresh by hand is that same disease wearing a table instead
of a one-line marker — a stale manifest is worse than no manifest, because it looks
authoritative.

**New command `commands/chapter-manifest.md`.** Follows CLAUDE.md's "Runbook arguments"
rules exactly: arguments declared by name in frontmatter —

```yaml
argument-hint: <book-number> <chapter-number>
arguments: [book, chapter]
```

— referred to in the body as `$book` / `$chapter`, never a bare `$0`/`$1`, and with no
`$`-bearing logic inline; the one line of substance the runbook needs is a call into
`scripts/penny_manifest.py`, which is where any such logic belongs per the same section's
third rule.

## 7. Scope boundaries

- **Draft file only.** The manifest is never stamped into `.lineedit.md`, `.copyedit.md`,
  `.final.md`, or the assembled manuscript. `scripts/assemble_book.py` reads only
  `ch-*.final.md` and calls `strip_frontmatter` on it — it never sees a draft — so
  assembly needs **no change at all**. This is a direct consequence of the draft-only
  decision, not a coincidence: because the manifest never crosses the draft →
  `.final.md` boundary, nothing downstream of that boundary needs to know the block
  exists.
- **No new certificate, no new lock, no new gate.** The manifest reports on certificates;
  it does not become one.
- **No new blocking finding anywhere.** The manifest cannot fail a build. A showrunner who
  never runs `/chapter-manifest` and never gets an automatic refresh loses nothing but the
  summary — every existing gate keeps working exactly as it does today.
- **`book_status.py` is not replaced or changed in its reporting.** It keeps printing the
  same six-row table across a whole book. The manifest relocates that same information
  into the single chapter the showrunner has open, and adds the one column
  `book_status.py` does not have: staleness folded into the status cell (§2).

## 8. Testing

Test-first against `tests/fixtures/`, per the repo convention (CLAUDE.md, "Conventions").
Three properties matter most and must be pinned directly, not only exercised incidentally:

1. **The invariant (§3).** No script and no runbook ever reads a value out of the
   manifest block — it is written and stripped, never parsed for a value that feeds a
   decision.
2. **Hash stability (§4).** Stamping, re-stamping, and stripping a draft leaves
   `draft_sha256` unchanged across all three operations; and a manifest-free draft hashes
   identically before and after the `draft_sha256` change — the backward-compatibility
   proof that no existing certificate on disk is invalidated by this spec.
3. **Isolation (§5).** No agent-facing draft hand-off, in any runbook, ever includes the
   manifest block.

Also note: `tests/test_texture_allocation_docs.py::test_claude_md_test_count_matches_the_suite`
pins the "full suite (N tests)" figure in CLAUDE.md's Commands section against a live
`pytest --collect-only` count. Any tests this spec adds must be reflected in that line
(currently 1314) or the suite fails on the count mismatch alone, independent of whether
the new tests themselves pass.
