---
description: Post-gate prose pipeline — line-edit → copy-edit → ledger update → promote → commit or pause for review.
argument-hint: <book-number> <chapter-number> [--commit]
---
# /finalize-chapter

Runs the post-gate tail for one chapter: line-editor → copy-editor → ledger-updater →
ledger markers → promote to `.final.md` → commit or pause (per `ledger_approval` in
`config/run-config.md`). Review via `/review-chapter` must pass before running this
command. Finalize via `/finalize-chapter`; if `ledger_approval: review`, inspect the
ledger diff then resume with `/finalize-chapter $1 $2 --commit`.

## Steps

### Step 0 — Gate guard

Hard-fail unless the chapter passed the developmental gate (`ch-NN.gate.md` shows
`gate: PASS`) — a HOLD or a missing gate file aborts finalize:

```bash
python3 scripts/preflight.py finalize $1 $2
```

A non-zero exit aborts immediately — do not proceed.

### Parse args

```bash
book=$1       # e.g. 01
chapter=$2    # e.g. 03
flag=${3:-}   # optional --commit
```

---

### `--commit` RESUME BRANCH (handle before everything else)

If `$flag` equals `--commit`, enter the resume path:

1. Read `.penny/current-stage` and assert it reads
   `book=$book chapter=$chapter stage=LEDGER-REVIEW`. If it does not, stop and tell
   the showrunner which chapter/stage is active.

2. **Git-commit the already-written working tree.** The prose agents have already run
   and their output is on disk — do NOT re-run any agents (re-running would re-edit
   prose non-idempotently and discard the reviewed text). Stage and commit exactly
   these paths:

   ```bash
   git add \
     output/book-$book/chapters/ch-$chapter.lineedit.md \
     output/book-$book/chapters/ch-$chapter.copyedit.md \
     output/book-$book/chapters/ch-$chapter.final.md \
     output/book-$book/chapters/ch-$chapter.ledger-diff.md \
     series/continuity/canon-core.md \
     series/continuity/threads/ \
     series/style-sheet.md

   git commit -m "finalize: book $book chapter $chapter"
   ```

3. Write the stage marker:

   ```bash
   echo "book=$book chapter=$chapter stage=FINALIZED" > .penny/current-stage
   ```

4. Report "Chapter $book/$chapter finalized." and **stop** — no agents run on this path.

---

### No-flag refusal guard

If `$flag` is empty AND `.penny/current-stage` reads
`book=$book chapter=$chapter stage=LEDGER-REVIEW`, **refuse to proceed**. Tell the
showrunner:

> "Chapter $book/$chapter is already at LEDGER-REVIEW. Re-running the pipeline would
> re-edit the prose non-idempotently and discard your reviewed text. To commit the
> current working tree, run:
>
> `/finalize-chapter $1 $2 --commit`"

Stop here.

---

### Step 1 — LINE-EDIT

Write the stage marker:

```bash
echo "book=$book chapter=$chapter stage=LINE-EDIT" > .penny/current-stage
```

Dispatch the **`line-editor`** sub-agent with:
- `output/book-$book/chapters/ch-$chapter.draft.md` — the chapter draft.
- `config/voice-pack/voice-pack.md` — voice rules.
- `config/length-profile.md` — word-count band.
- `config/line-edit/line-edit.md` — move checklist.

The agent writes its revised prose to
`output/book-$book/chapters/ch-$chapter.lineedit.md` (same content, overwrite or new
file).

### Step 2 — COPY-EDIT

Write the stage marker:

```bash
echo "book=$book chapter=$chapter stage=COPY-EDIT" > .penny/current-stage
```

Dispatch the **`copy-editor`** sub-agent with a **fresh context** (no drafting history,
no inspector verdicts):
- `output/book-$book/chapters/ch-$chapter.lineedit.md` — the line-edited text only.
- `series/style-sheet.md` — the house style sheet.
- `config/copy-edit/copy-edit.md` — copy-edit rubric.

The agent writes `output/book-$book/chapters/ch-$chapter.copyedit.md` and appends any
new decisions to `series/style-sheet.md`.

### Step 3 — FINALIZE (ledger update + markers)

Write the stage marker:

```bash
echo "book=$book chapter=$chapter stage=FINALIZE" > .penny/current-stage
```

**3a. Dispatch `ledger-updater`** with the loaded ledger slice (canon-core + this
chapter's thread files) and `output/book-$book/chapters/ch-$chapter.copyedit.md`. The
agent:
- Writes prose-body updates within the loaded slice only (bounded write-scope).
- Emits `output/book-$book/chapters/ch-$chapter.ledger-diff.md` with one
  `advanced: yes/no` flag per thread.

**3b. Run `ledger_markers.py`**, passing every thread file where `advanced: yes` was
emitted:

```bash
python3 scripts/ledger_markers.py $book $chapter \
  --canon series/continuity/canon-core.md \
  --brief series/briefs/book-$book/ch-$chapter-brief.md \
  --text output/book-$book/chapters/ch-$chapter.copyedit.md \
  --thread-advanced series/continuity/threads/<thread-file>.md \
  [--thread-advanced series/continuity/threads/<other-thread>.md ...]
```

Pass one `--thread-advanced` flag per thread file reported as `advanced: yes` in the
ledger diff. Omit `--thread-advanced` entirely if no threads were advanced.

### Step 4 — Promote

Copy `ch-$chapter.copyedit.md` to `ch-$chapter.final.md`, carrying all frontmatter:

```bash
cp output/book-$book/chapters/ch-$chapter.copyedit.md \
   output/book-$book/chapters/ch-$chapter.final.md
```

### Step 5 — `ledger_approval` branch

Read `ledger_approval` from `config/run-config.md`.

**`auto`:** git-commit end-to-end and set stage to FINALIZED:

```bash
git add \
  output/book-$book/chapters/ch-$chapter.lineedit.md \
  output/book-$book/chapters/ch-$chapter.copyedit.md \
  output/book-$book/chapters/ch-$chapter.final.md \
  output/book-$book/chapters/ch-$chapter.ledger-diff.md \
  series/continuity/canon-core.md \
  series/continuity/threads/ \
  series/style-sheet.md

git commit -m "finalize: book $book chapter $chapter"
echo "book=$book chapter=$chapter stage=FINALIZED" > .penny/current-stage
```

Report "Chapter $book/$chapter finalized and committed."

**`review`:** Pause — do NOT commit. Set stage to LEDGER-REVIEW:

```bash
echo "book=$book chapter=$chapter stage=LEDGER-REVIEW" > .penny/current-stage
```

Surface the ledger diff to the showrunner:

> "Ledger diff for book $book chapter $chapter is ready at
> `output/book-$book/chapters/ch-$chapter.ledger-diff.md`.
>
> Review the diff with `git diff` and the ledger-diff file, then commit by running:
>
> `/finalize-chapter $1 $2 --commit`"

**Do not commit. Stop here.** The showrunner must review and explicitly re-run with
`--commit`.
