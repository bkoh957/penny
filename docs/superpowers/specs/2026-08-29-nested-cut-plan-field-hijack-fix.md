# A nested item hijacks its chapter's own cut-plan field

Date: 2026-08-29
Status: defect, fix brief — not a feature proposal
Severity: high — silent for four of the five affected keys, and a forged value reaches the
blind fan read

Filed in `specs/` rather than `backlog/` deliberately: `docs/backlog/README.md` excludes
defects ("If the engine is wrong, fix it"). This is a defect, but the fix has one naming
decision in it that changes a pinned count in four places, so it is written up rather than
simply patched.

Found while reviewing the texture-allocation branch (2026-08-27), by the reviewer that
closed the track-row half of the same hole. Recorded then, deliberately not fixed: it is
pre-existing — it arrived with `Setting:` on 2026-08-12, six weeks before `Texture:` — and
it was outside that spec's scope.

## 1. Why

`penny_story.parse_cut_plan` matches a chapter's field lines with patterns anchored to
`^\s*`, so they match **at any indentation**:

```python
# scripts/penny_story.py:184-186
_CUT_FIELD_RE = re.compile(
    r"^\s*-\s+\*\*(?P<key>Beats|Summary|Compress|Setting|Texture|Opening):\*\*"
    r"\s*(?P<val>.*)$")
# scripts/penny_story.py:187-188
_CUT_CLOSING_RE = re.compile(
    r"^\s*-\s+\*\*Closing\s*\((?P<kind>[^)]*)\):\*\*\s*(?P<val>.*)$")
```

Both are tested (`:247`, `:253`) **before** the nested-item branches that collect
`Setting:`'s ranges and `Texture:`'s images. So a line written as a nested item under one of
those blocks is not read as an item at all — it is read as the chapter's own field, and it
**overwrites the value the author actually wrote**:

```markdown
- **Beats:** 1-2
- **Summary:** She locks up as always.
- **Texture:**
  - bakery 6am: proving-room warmth
  - **Summary:** Marion did it, obviously.      <- becomes THE chapter's Summary
```

This is the same class of forgery as `wiring-shaped-directive`, through the other half of
the field table. The track-row half was closed on 2026-08-28 (`d56729c`) with an
indentation rule in `story_cut.check_story`:

```python
# scripts/story_cut.py:238
if num is not None and raw[:1].isspace() and TRACK_RE.match(raw):
```

That rule is correct and is the model for this fix — it simply only covers `TRACK_RE`.

## 2. Evidence

Measured against `check_story` on a two-chapter plan that is clean before the nested line is
added (`Setting`, `Opening` and `Closing` present throughout, so the all-or-nothing adoption
rule is satisfied and contributes no findings of its own). Identical results whether the host
block is `- **Texture:**` or `- **Setting:**`:

| nested item | effect on the chapter | findings |
|---|---|---|
| `- **Summary:** FORGED` | Summary replaced | **none** |
| `- **Compress:** FORGED` | Compress replaced | **none** |
| `- **Opening:** FORGED` | Opening replaced | **none** |
| `- **Closing (irony):** FORGED` | Closing replaced | **none** |
| `- **Beats:** 9` | beat range `[1,2]` → `[9]` | 3, all misdirected — see below |
| `- **M:** FORGED` | *(none — kept as an item)* | 1, `wiring-shaped-directive` ✓ |

**Four of the five are completely silent.** Zero findings, and the authored value is gone.

**`Beats:` is not silent, but every finding it raises names the symptom and not the cause:**

```
beats-without-chapter: beat 1 lands in no chapter — the cut plan must cover every beat
beats-without-chapter: beat 2 lands in no chapter — the cut plan must cover every beat
beats-without-chapter: the cut plan claims beat 9 but the story has only 3
```

Nothing points at the nested line. A showrunner reading that goes looking at chapter
boundaries — the one place the fault is not. (`Beats:` is caught at all only because the
plan must partition every beat exactly once, so any change to a range either drops coverage
or doubles it. A hijack that happened to preserve the partition would be silent too.)

**A forged Summary reaches the blind fan read.** `plot_stage._KEEP_SUBSECTIONS`
(`scripts/plot_stage.py:93-94`) admits `chapter summary`, `setting`, `opening` and
`closing` into the reader's copy — every one of them hijackable. Verified end to end
through `emit_outline` → `readers_copy_text`: the forged summary is present in the reader's
copy and the authored one is absent. The reader's copy is the instrument the fan-audit
measures put-down risk and whodunit guessing with; a line that reaches it can name the
culprit to a reader the process calls blind.

Severity is therefore *high*, not medium: the failure is silent, it destroys authored
content rather than merely adding to it, and it has a path to the one artifact in the engine
whose whole value is that its contents were constructed rather than trusted.

## 3. Fix

### Recommended: extend the existing indentation rule to the other two patterns

In `story_cut.check_story`, beside the `TRACK_RE` guard at `scripts/story_cut.py:238`,
refuse any **indented** line inside a chapter block that matches `_CUT_FIELD_RE` or
`_CUT_CLOSING_RE`.

The load-bearing observation is the same one that closed the track-row half: **a genuine
cut-plan field line is never indented.** `chapter-cutter`'s output format writes them at
column 0, and `story_cut` reads them there. So indentation is a sound discriminator, and
using it means the guard does not have to model where a nested block begins or ends — the
mistake that made the first attempt at the track-row fix close only the one input shape its
own test used.

Import the two patterns from `penny_story` rather than re-deriving them locally, exactly as
the existing guard imports `_CUT_CHAPTER_RE`. A local copy of another module's parser state
is what produced that earlier failure.

The message should name the chapter, quote the line, say which field it would overwrite, and
give the cure — which is the same two-branch cure the track-row message already gives: reword
it so it does not begin with a field key, or, if it was meant as the chapter's real field,
unindent it to column 0.

### Rejected

- **Anchor `_CUT_FIELD_RE` / `_CUT_CLOSING_RE` at column 0 in the parser.** Prevention rather
  than detection, and it makes the nesting mean what it looks like — a `- **Summary:** …`
  under `- **Texture:**` would simply become a texture item. Rejected because it trades one
  silent behaviour for another: an accidentally-indented *genuine* field line would quietly
  become a texture image instead of failing loudly, and the author would get a clean run with
  their Summary missing. This engine's contract is to fail loud with a named predicate, not
  to reinterpret. It also changes a parser that `book_status.py` and `chapter_refs_check.py`
  read, for a benefit the guard delivers without touching them.
- **Do both** — anchor the parser *and* report the refusal. Belt and braces, but the guard
  can only see what the parser leaves visible; once the parser stops matching, the guard has
  nothing to fire on, and the finding disappears rather than becoming loud. Pick one layer.
- **Detect by host block** — only refuse a field-shaped line while inside a `Texture:` or
  `Setting:` block. Rejected for the reason the track-row guard was rewritten: it requires
  modelling where a nested block ends, and `parse_cut_plan`'s notion of that is not
  re-derivable without drifting from it. Indentation needs no model.
- **Leave it, and document the shape as forbidden.** The two prose consumers most likely to
  hit it (`agents/chapter-cutter.md`, `commands/plot-book.md`) already tell their reader what
  the format is; the failure is that nothing checks. A rule that only exists in prose is what
  this defect already relies on.

## 4. The decision, settled

**Does this reuse `wiring-shaped-directive`, or mint a 24th finding?**

**DECIDED 2026-08-29 by the showrunner: reuse `wiring-shaped-directive`.** The roster stays
at 23 and the four pinned places are unchanged. The reasoning below stands as the record of
why; the alternative is kept for the same reason the rejected fixes are.

Reusing keeps `story_cut.py`'s roster at exactly 23, which is pinned in four places:
`tests/test_readme_check_count.py:54` (`len(STORY_CUT_FINDING_IDS) == 23`, plus the tuple
itself), `tests/test_claude_md_check_count.py` ("twenty-three findings"), `CLAUDE.md`'s
source-layer paragraph, and `README.md:552`'s finding table.

**Recommendation: reuse `wiring-shaped-directive`.** The concept it already names is *an
authored line that the cut's own parser will read as structure rather than as content* —
which is exactly this. It has generalised once already: `README.md:552` currently describes
it as covering a `## Chapter Direction`/`## Guardrails` line, a cut plan's
`Opening`/`Summary`/`Compress` value, a `Texture` item, and any indented track-shaped row.
Adding indented field rows extends that sentence rather than contradicting it, and one
mechanism with one name is what has kept this check comprehensible through three
extensions.

The honest cost: "wiring" is a slight stretch for `Beats:` and `Summary:`, which are cut-plan
fields rather than outline wiring, and a roster of named predicates is a promise about *what
can go wrong* — collapsing distinct failures under one name makes it less informative. If
that matters more than the count, mint `nested-field-hijack` instead and update the four
pinned places in the same change; nothing else depends on the number.

Whichever is chosen, `README.md:552`'s table row and `CLAUDE.md`'s paragraph must be updated
to describe what the finding actually covers afterwards.

## 5. Test

1. Each of the five keys — `Beats`, `Summary`, `Compress`, `Opening`, `Closing (<kind>)` —
   nested under `- **Texture:**` is refused by name. Table-drive it; the track-row fix's
   first attempt passed its own tests while leaving the bug open precisely because its tests
   used one shape.
2. The same five nested under `- **Setting:**` are refused. The host must not matter.
3. A nested field line under **no** host block — indented directly after the chapter heading
   — is refused too, matching how the track-row guard already behaves.
4. Genuine unindented field lines are never refused, in a chapter with a nested block and in
   one without.
5. The separator shapes that defeated the first track-row attempt: a blank line, a
   whitespace-only line, an HTML comment, and a prose line between the block declaration and
   the nested field line. All must still be refused.
6. A `Beats:` hijack now reports the nested line, and the misdirecting `beats-without-chapter`
   findings it used to raise are no longer the only signal.
7. The roster invariant, whichever way §4 is decided: the count assertion and the two doc
   pins agree with the code.

## 6. Blast radius

`story_cut.check_story` only — one added guard beside an existing one. No parser changes, no
emitter changes, no packet or map changes, and no existing finding changes meaning.

`README.md:502-513`'s cut-plan template is worth a look while this is in hand: the fenced
block sits inside a numbered list, so every line of it renders 3-space indented. A showrunner
who copies that fence and unindents only the `## Chapter` heading would produce exactly the
shape this guard refuses — loudly, with a cure, which is the right outcome, but the template
would be better not nesting the fence in a list.

No cut plan in this repo, and none in the one real series checked, contains an indented field
line, so nothing existing starts failing.
