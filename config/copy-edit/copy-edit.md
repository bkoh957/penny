# Copy-Edit Rubric [STABLE]

> Scope: grammar, punctuation, spelling, and consistency. No style rewrites.
> Design §7. Consumed by `.claude/agents/copy-editor.md`.
> The copy-editor agent runs in fresh context: text + style sheet only.

## Governing document

`series/style-sheet.md` is the single source of truth for every spelling, hyphenation, and punctuation decision across the 13-book series. Read it in full before touching the text. When the style sheet has no ruling, make a judgement call and **append** it.

## Spelling

- **Australian English** throughout: colour, favour, honour, realise, organise, recognise, -ise not -ize, travelling (double l), programme (unless "computer program").
- Proper nouns: match the ledger entry exactly. Character names, place names, business names, and Cora's deceased husband's name are never variant-spelled.

## Grammar and punctuation

- Serial (Oxford) comma: use it.
- Em-dash with no spaces for interruption or parenthetical aside — like this — not an en-dash and not spaced.
- Ellipsis: three-dot (`…` or `...`) with no space before and one space after, unless end of sentence.
- Dialogue: close quote after punctuation (Australian convention follows British: `"Come in," she said.`).
- Hyphenation: compound modifiers before a noun are hyphenated ("well-worn path"), but not predicatively ("the path was well worn").

## Consistency scope

- Character name spellings (cross-check every appearance).
- Place names and business names (cross-check every appearance).
- Running chapter-internal consistency: if a character's hair colour is stated twice, it must match.
- Tense consistency: past tense throughout; present tense only inside present-tense-framed flashbacks.

## Style-sheet append rule

For each new decision not already in `series/style-sheet.md`, append a single bullet under `## Decisions` using this form:

```
- <Category>: <ruling>. (e.g., Hyphenation: "post-mortem" hyphenated as noun and adjective.)
```

**Never** remove or reorder existing decisions. **Never** overwrite the style sheet — append only.

## Scope limits (do not cross)

- Do NOT rewrite sentences for style or rhythm — that is the line-editor's job and it is done.
- Do NOT add, cut, or reorder content.
- Do NOT resolve narrative ambiguity.
- Do NOT change frontmatter.

## Checklist (pass in order)

1. [ ] Read `series/style-sheet.md` fully.
2. [ ] Read `config/copy-edit/copy-edit.md` (this file).
3. [ ] Correct spelling (Australian English + proper nouns).
4. [ ] Correct grammar and punctuation against the rules above.
5. [ ] Check consistency (names, places, tense).
6. [ ] Append new decisions to the style sheet.
7. [ ] Confirm no rewriting occurred.
