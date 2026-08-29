# Runbook positional arguments are off by one

Date: 2026-08-29
Status: defect, fix brief — not a feature proposal
Severity: high — silent, corrupts the instruction before the agent reads it, the source file
looks correct to anyone auditing it, and it affects every positional argument in seven
runbooks rather than the single `$0` first reported

Filed in `specs/` rather than `backlog/` deliberately: `docs/backlog/README.md` excludes
defects. Written up because the failure is invisible at the source and the fix needs a
convention decision, not just an edit.

> **Amended 2026-08-29, after the premise was tested.** This spec was first written as
> *"Runbook rendering corrupts `$0` and `$1` inside code blocks"*, on the assumption that
> `$1` is the first argument (the shell convention every runbook here is written in) and
> that `$0` was an anomaly. **Both halves of that were wrong.**
>
> Claude Code's substitution is **zero-indexed**: `$0` is the first argument, `$1` the
> second, `$N` shorthand for `$ARGUMENTS[N]`. Confirmed empirically — see §2b — not inferred
> from documentation.
>
> So `$0` is not the bug. It is the only place the bug could not be papered over. The real
> defect is that **every positional in every runbook is off by one**, and §3's inventory and
> §4's fix are rewritten accordingly. The original framing is preserved below where it still
> holds, because how it looked benign is part of the evidence.

## 1. Why

`commands/*.md` runbooks are rendered into an agent's context when a command is invoked,
and that rendering substitutes argument placeholders — **uniformly, including inside fenced
code blocks**, and **zero-indexed**:

| placeholder | expands to |
|---|---|
| `$0` | the **first** argument |
| `$1` | the **second** argument |
| `$N` | shorthand for `$ARGUMENTS[N]` |
| `$ARGUMENTS` | all arguments |
| `$name` | a named argument declared in frontmatter |

A placeholder with no corresponding argument is left **literal** — `$2` stays `$2` when only
two arguments were given.

Every runbook in this plugin is written in the **one-indexed shell convention** — `book=$1`,
`chapter=$2` — which is off by one against that table. `book=$1` binds the chapter;
`chapter=$2` binds a third argument that does not exist.

The runbook file on disk is correct as shell. The version the agent receives is not. Nothing
in the repository is wrong when you read it, which is what makes this expensive.

## 2. Evidence from a real run

`/finalize-chapter 01 01`, Pelican's Crook book 01, 2026-08-29.

**Source — `commands/finalize-chapter.md:149-152`, correct:**

```awk
awk -v h="## Chapter $chapter " '
  index($0, h) == 1 { grab = 1; print; next }
  grab && (/^## / || /^# /) { exit }
  grab { print }
' input/book-$book/outline.md > "$brief"
```

**As rendered into the executing agent's context:**

```awk
awk -v h="## Chapter $chapter " '
  index(01, h) == 1 { grab = 1; print; next }
  grab && (/^## / || /^# /) { exit }
  grab { print }
' input/book-$book/outline.md > "$brief"
```

`$0` became `01`. In awk, `$0` is the **entire current record** — the whole line. Replacing
it with the literal `01` changes `index($0, h)`, "does this line begin with the chapter
heading", into `index(01, h)`, "does the constant 01 contain the heading string". That is
always false.

**Consequence if executed as rendered:** `$brief` is written empty. Step 3b then dispatches
`ledger-updater` with an empty brief, so the agent receives no scope context — no indication
of which characters, locations or threads the chapter touches. It does not error. It
produces a ledger update scoped by guesswork, and the run continues to a successful-looking
finalize.

The same substitution is visible throughout the rendered runbook wherever `$1` appeared:
`book=$1` rendered as `book=01`, and `preflight.py draft $1 $2` rendered as
`preflight.py draft 01 $2`. Those happen to be harmless — `01` *is* the book number, so the
corruption is invisibly correct. That is why this survived until an `awk` script made it
visible.

**How it was caught:** the executing session noticed `index(01, h)` did not look like valid
awk, substituted `$0` back by hand, and got the correct 94-line brief. Had it followed the
rendered instruction literally — which is the expected behaviour — the ledger updater would
have run unscoped and nothing would have reported a problem.

## 2b. The test that settled it

The original evidence was one observed run, and it admitted a second reading: that the
executing model had mis-transcribed the awk line. It needed settling, and the documentation
was ambiguous — it describes *skills*, and these are plugin slash commands.

Settled by rendering an **existing** runbook with distinctive arguments, creating no files
and executing nothing. `/book-status AAA BBB`. Source line 13:

```
1. **Parse args:** `book=$1` (e.g. `01`), optional `chapter=$2`.
```

As rendered into context:

```
1. **Parse args:** `book=BBB` (e.g. `01`), optional `chapter=$2`.
```

`$1` → `BBB`, the **second** argument. `$2` → left literal, there being no third. Zero-indexed,
uniformly applied, confirmed.

## 2c. Why nothing has visibly broken in months

Two things hid it, and they are different in kind.

**The dominant usage masks it arithmetically.** This project runs `/command 01 01` almost
exclusively — book 01, chapter 01. When the first and second arguments are identical, an
off-by-one is invisible. It is why §2's original analysis read `book=$1` rendering as
`book=01` and concluded "harmless — `01` *is* the book number". It was the *chapter* number
that happened to match.

**And the interpreter is a model, not a shell.** These runbooks are not executed by bash;
an agent reads them and acts. An agent handed `/draft-chapter 01 07` and a line reading
`book=07` will generally reason "they asked for book 01, chapter 07" and do the right thing.
Every step absorbs the corruption through ordinary comprehension.

That is the whole reason this surfaced in an `awk` one-liner and nowhere else. Inside
`index($0, h)` there was nothing to correct against — no intent for the model to recover, just
a token to pass through. **The awk is not the bug; it is the only site with no human sense to
paper over it.** Any fix that addresses only §4a leaves the actual defect in place.

## 3. Blast radius

The original count — "fifteen runbooks contain `$0` or `$1` inside code" — conflated two
things. Measured:

| | count | |
|---|---|---|
| contain `$0`/`$1` **anywhere** | 15 | the original list; correct on that basis |
| …inside **fenced code blocks** | **7** | the affected set |
| …containing **`$0`** | 1 | `finalize-chapter` only |

The other eight are inline-code spans in prose, every one a "Parse args" line such as
`` `book=$1` (e.g. `01`) ``. They are substituted too, but they instruct a reader rather than
run, and a wrong value there is corrected by the same comprehension described in §2c.

**The seven, and every positional in them.** All are off by one; none is safe:

| runbook | positionals in code |
|---|---|
| `finalize-chapter` | `$1 $2` (preflight), `book=$1`, `chapter=$2`, `flag=${3:-}`, **`$0`** (awk) |
| `draft-chapter` | `$1 $2` (preflight), `$1` (outline_feedback), `$1 $2` (draft_words) |
| `draft-chapter-lmstudio` | `$1 $2` (preflight), `$3` (model-id guard), `$1 $2 $3`, `$1 $2` |
| `review-outline` | `$1` ×5 (outline test, stage markers, outline_feedback) |
| `map-chapter` | `book=$1`, `chapter=$2` |
| `assemble-book` | `book=$1`, `flag=${2:-}` |
| `allocate-texture` | `book=$1` |
| `book-status` | `${2:+"$2"}` |

The dangerous class named in the original spec — a `$0` or `$1` meaning something *other*
than a positional argument — still stands, and `finalize-chapter:150`'s awk `$0` is still its
only instance. It is now a special case of the general defect rather than the defect itself.

## 4. Fix

The original 4a/4b/4c assumed the defect was `$0`. It is the indexing. Revised.

### 4a. Correct the indexing in all seven runbooks

Every positional shifts down one: `$1`→`$0`, `$2`→`$1`, `$3`→`$2`, and `${2:-}`→`${1:-}`.

This is mechanical and it is the whole fix for six of the seven. It is also the step most
likely to be got wrong by a careless sweep, because the *result* looks like a typo to anyone
who knows shell — a reviewer's instinct will be to "correct" `book=$0` back. Every changed
site needs the comment that explains why, or it will be reverted within the month.

**A named-argument alternative is worth considering instead.** Frontmatter-declared arguments
substitute by name (`$book`, `$chapter`), which removes indexing from the question entirely
and reads correctly to both audiences. Every affected runbook already carries an
`argument-hint:` line, so the intent is declared; only the binding is positional. Confirm the
exact frontmatter key against current Claude Code documentation before adopting it — that
detail is not verified here. If it works, prefer it: 4a's renumbering leaves a permanent trap
for the next reader, and named arguments do not.

### 4b. Move the awk out of the runbook

Unchanged from the original, and still right on its own merits. Rewrite `finalize-chapter`'s
brief extraction as `scripts/extract_brief.py` and call it:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/extract_brief.py" "$book" "$chapter" > "$brief"
```

A script in `scripts/` is never rendered, so no substitution can reach it, and it is testable
— which the inline awk never was. The general rule holds: **logic complex enough to contain a
`$` that is not a command argument belongs in `scripts/`.**

Note this is now belt-and-braces rather than the primary fix. With 4a done, the awk `$0`
would still be corrupted, because `$0` is a real placeholder whatever the indexing. If the
awk stays in the runbook for any reason, it must be escaped as `\$0` — the documented escape
for a literal.

### 4c. A lint over the runbooks

Fail when a fenced code block in `commands/*.md` contains a bare `$` followed by a digit that
is not the intended zero-indexed argument — or, if 4a lands as named arguments, fail on any
bare positional at all, which is a far simpler rule to state and to keep.

The message must explain the substitution, because the failure is counter-intuitive in both
directions: the file is correct as shell and wrong as a runbook, and after the fix it is
correct as a runbook and looks wrong as shell.

### 4d. Document the convention

In `CLAUDE.md`, beside the architectural rule: *runbook code blocks are interpolated before
an agent sees them. Argument placeholders are zero-indexed — `$0` is the first argument. Never
write a bare `$` before a digit meaning anything else; escape it `\$` or move the logic into
`scripts/`.*

## 5. Test

1. **The end-to-end pin, and the one that matters.** A test asserting no fenced block under
   `commands/` contains a bare `$` before a digit — or, under named arguments, none at all.
   This is the only test that would catch the next occurrence.
2. If 4b lands as `extract_brief.py`: a unit test that the brief for a known outline is
   **non-empty** and begins with the expected `## Chapter NN` heading. The non-empty
   assertion is the important half — the failure this defect produces is an empty file,
   silently.
3. A rendering round-trip is **not** testable from inside this repo: substitution happens in
   the harness, not in anything here. §2b's method — render an existing runbook with
   distinctive arguments and read the result — is the procedure, and it belongs in the
   convention doc as the way to re-confirm after any Claude Code upgrade. It costs one
   invocation and creates nothing.

**Before implementing, re-run §2b.** This spec's first version was confidently wrong about
the indexing for a day. The behaviour lives in the harness and can change under us; a
thirty-second check is cheaper than renumbering seven runbooks the wrong way.

## 6. Related

Same family as `2026-08-29-engine-holds-story-details-fix.md` and
`2026-08-27-packet-extract-heading-collision-fix.md`: all three are cases where an agent
receives an input that is wrong in a way no check can see, and the wrongness only surfaces
because a human-in-the-loop happened to look closely at the right moment. The packet one
truncated a slice; the Cora one contradicted a pack; this one rewrites an instruction. None
of them fail loudly.

That pattern is worth naming: **the engine has no verification that what an agent received
is what the repository intended to send.** Each fix so far has been local. A general answer
— agents echoing back a checksum or a manifest of what they read, as
`packet_assemble`'s new Continuity Extracts manifest now allows — may be the real
remedy, and is worth a design of its own.
