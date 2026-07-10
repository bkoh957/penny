# Outline feedback: split the recommendation out of the observation

**Date:** 2026-07-10
**Status:** approved (design), not yet implemented
**Extends:** `docs/superpowers/specs/2026-07-09-outline-developmental-review-design.md`
(the outline-review tier and its append-only `OF-<n>` ledger).

## Problem

Panel members already recommend fixes — they just bury them in the diagnosis. From book 01's
first live pass:

- `OF-1` (claude): *"…Consider planting one more low-stakes, purely pleasurable Cal/Maggie beat
  somewhere in the Chapter 13–17 trough…"*
- `OF-20` (codex): *"…Before drafting, mark the few that genuinely matter so the chapter does not
  scatter intriguing details the mystery never cashes."*

The fix and the observation are fused into one `text` blob. The showrunner cannot scan what is
being *proposed* without re-reading every diagnosis, and the rendered view cannot present them
distinctly.

The question this spec answers is not *whether* recommendations exist, but whether they get
their own identity — and, given that, **who authors them and when**.

## Decision: reviewer-authored, at generation time

A recommendation is a reviewer's suggested fix for its own observation. Only that reviewer can
author it, in the same breath as the observation. A "second pass" would be a different read
producing a different fix — a new item, not a recommendation attached to the original one.

This is reinforced by an invariant we are not going to break. `append_items` deep-copies the
ledger and only appends; nothing in `outline_feedback.py` mutates an existing item. That is the
same rule that protects the showrunner's hand-owned `state:`. Therefore:

**Existing items are never retro-filled by a tool.** `OF-1`…`OF-22` stay recommendation-less
unless the showrunner hand-edits them. Only items minted by a fresh pass carry the field. This
is the guarantee working, not a limitation to route around.

## Schema

Items gain one **optional** key:

```yaml
- id: OF-23
  source: claude
  pass: 2
  state: open
  text: >-
    The romance's warm pleasure is front-loaded and then starved from ch11 onward...
  recommendation: >-
    Plant one low-stakes Cal/Maggie beat in the ch13–17 trough.
```

Prose, not a score — the outline tier's no-scores rule is unchanged. `VALID_STATES` is
untouched; `state` remains the showrunner's.

**Absent, not empty.** When there is nothing to fix, the key is omitted — never `""`, never
`"No action required"`. `OF-10`'s whole point is *"two areas are genuinely strong and need no
intervention"*; a required field would force a reviewer to invent an action for it. Making "I
have no fix for you" a costless, first-class answer is the only thing that stops the field from
manufacturing advice.

**Per-source, never merged.** `OF-1` (claude) and `OF-21` (codex) both address the romance
strand and reach *different* fixes: claude wants a warm beat added in the ch13–17 trough, codex
wants Cal's ch26 absence kept emotionally active. `recommendation` must not become the place
those get reconciled. Reviewer disagreement is the signal this tier exists to preserve;
converging it here would reintroduce exactly the K-of-M averaging the outline tier deliberately
inverts.

## Where it is authored

### A gap this spec must close first

Only **one** member's output shape is written down. `agents/outline-reviewer.md:35` binds the
claude member to `{ "text": "<one focused prose point>" }`. The codex member has **no output
contract anywhere in the repo** — `commands/review-outline.md` step 6 says only "send the SAME
rubric + inputs to the Codex reviewer via the codex plugin runtime", and step 7 describes the
returned shape passively (*"Each member returns a JSON array of `{ "text": ... }`"*) without
ever instructing codex to produce it.

The orchestrator therefore improvises codex's prompt at run time. The book-01 pass happened to
compose a serviceable one, and codex happened to return well-formed points. That is luck, not a
contract. It also quietly weakens step 6's headline promise of *"identical inputs"*: the members
receive identical **files** but differently-worded **instructions**, every run, unreproducibly.

This blocks the feature: there is no file in which to tell codex about `recommendation`.

**Close the gap by giving the codex member a written contract**, so both members are bound by a
committed artifact:

- `agents/outline-reviewer.md` — the claude member's contract (exists).
- `commands/review-outline.md` step 6 — add an explicit, quoted output contract for the codex
  dispatch, worded identically to the outline-reviewer's.

These two must then stay in lockstep, for the same reason `inspector-fairplay.md` and its rubric
must: an agent reads its agent file *and* its prompt, and a rule taught in only one of them is a
rule the panel half-follows. That failure has already bitten this repo once — the whole-branch
review of the solution-blindness removal caught two rubric files still teaching the deleted rule.

### The change itself

Both contracts gain an optional `"recommendation"` sibling key, described in identical words:
`text` carries the observation, `recommendation` carries the fix, and omitting it is a legitimate
answer.

Step 7's collect shape becomes `[{source, text, recommendation?}, …]`. The command continues to
own `source`; the reviewer never sets it.

## Transport (deterministic layer)

`append_items` copies the key through **only when present and non-blank**:

```python
item = {"id": f"OF-{next_id}", "source": pt["source"], "pass": next_pass,
        "state": "open", "text": pt["text"]}
if pt.get("recommendation"):
    item["recommendation"] = pt["recommendation"]
```

That is the entirety of the script's judgment: *is the key there*. No parsing, no
classification, no LLM decision — `outline_feedback.py` keeps its promise of zero LLM/genre
judgment.

`--points`' help string updates from `{source,text}` to `{source,text,recommendation?}`.

### Rejected: extract the fix from the prose

A `append`-time heuristic that lifts the trailing "Consider…" / "Make sure…" sentence out of
`text` would retro-fill the existing 22 items for free. Reject it. Deciding which sentence is a
recommendation is an LLM judgment. A heuristic would fire on `OF-22`'s *"The main caution is to
avoid making pottery do too much interpretive work"* while missing `OF-20`'s bare imperative
*"mark the few that genuinely matter"*. This is the same trap as the premature-reveal predicate
that is deliberately **not** a script.

### Rejected: a sidecar recommendations file keyed by OF id

Splits one record across two files and reintroduces mutation-by-join. Data lives in its own
file; the `.md` is the rendered doc.

## Presentation

`render_view` prints the observation first and the recommendation indented beneath it, inside
that item's own source-tagged bullet:

```markdown
- **OF-23** · _claude_ · pass 2
  The romance's warm pleasure is front-loaded and then starved from ch11 onward...
  **→** Plant one low-stakes Cal/Maggie beat in the ch13–17 trough.
```

**Never a standalone list of fixes.** Splitting the fix out of the diagnosis makes it easy to
read only the recommendations and skip the reasoning; ordering is the mitigation. The
`Open`/`Solved`/`Rejected` bucketing and per-source grouping are unchanged.

## What does not change

`status_line` needs no change. It prints item IDs and never item text — the property that keeps
solution content out of a drafting context — and a recommendation is item text. Its output must
be byte-identical whether or not recommendations are present.

`status` still exits 0 always. The tier stays advisory: a recommendation never gates, never
blocks drafting, and carries no score.

## Testing

Test-first against `tests/fixtures/`. Each assertion targets the *new sentence* or a
*structural absence*, and must be proven RED against the pre-change tree — a test asserting a
bare token can pass for an unrelated reason.

- `append` carries `recommendation` when present.
- `append` omits the key entirely when absent — assert `"recommendation" not in item`, not that
  it is falsy.
- `append` omits it when the reviewer sends `""` or whitespace (the truthiness guard).
- `render_view` renders an item with the field, and one without.
- A ledger of pre-change items (no key anywhere) renders unchanged — the back-compat proof.
- `status_line` output is byte-identical with and without recommendations present.
- **Contract lockstep:** `commands/review-outline.md` and `agents/outline-reviewer.md` both
  state the optional `recommendation` key. Assert on the sentence, not the bare token
  `recommendation` — the word will appear in prose elsewhere in both files and would make the
  test vacuous.

## Scope

Engine-only, genre-agnostic. No genre pack, no series data, no `config/` default changes. The
book-01 ledger is unaffected until its next pass.
