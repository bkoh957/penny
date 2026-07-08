# Lexicon (schema doc)

The authoritative lexicon data lives in **`lexicon.yaml`** (scripts read it; this
file is documentation only — do not duplicate rows here).

Schema (one mapping per entry under `terms:`):
`term | gloss | register | speaker_type | freq_cap | narration_ok_from_stage | auto_detectable | notes`

- `narration_ok_from_stage` couples each term to the fluency dial (`OUTSIDER` <
  `SETTLING` < `BELONGING`): a term whose stage is *later* than the book's current
  `fluency_stage`, appearing in **narration**, is a premature-term flag.
- `auto_detectable` (bool, required): `true` = safe to match mechanically
  (word-boundary). `false` = homograph of standard English; `lexicon_check.py` does
  not flag it — it is surfaced to `inspector-voice` as an inspector-only note.

`lexicon_check.py --validate` checks every entry has `term`,
`narration_ok_from_stage`, and `auto_detectable` before the lexicon is locked.

> **Accuracy note:** seeds are from general knowledge of Australian usage. Before a
> 13-book lock, a `research-notes.md` pass should verify coastal-Victorian idiom and
> AFL club loyalties.
