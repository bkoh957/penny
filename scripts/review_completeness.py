"""Review-panel completeness gate — deterministic, no LLM judgment.

`/review-chapter` used prose to ask an agent to confirm each verdict file
existed. On the live series `voice_drift.py` and `lexicon_check.py` ran in 1 of
12 rounds and nothing noticed, while `inspector-voice` recorded "No
voice_drift.py evidence was supplied for this round" and made its blocking call
blind. A gate computed over an incomplete panel is the soft gate this engine
exists to reject, so the check moves to `scripts/`, where it fails loud with a
named line and a nonzero exit.

The lines below are REPORT findings, not engine findings: they join no roster
(`story_cut.py`'s twenty-three, `tension_check.py`'s ten, `map_check.py`'s
seven), take no `--waive`, and gate nothing but this command's own step.

Two absences are legitimate and are never reported as findings:

1. `lexicon-fluency.md` when the series has no `config/setting-pack/lexicon.yaml`.
   The engine ships no lexicon — it is series-authored — and `lexicon_check.py`
   exits rather than writing when it is absent. The inert check is NAMED in a
   note; silence would let a real skipped dispatch hide behind it.
2. An inspector outside the active genre's roster. The genre chooses which
   inspectors run, so a fixed list here would report a cozy-only inspector
   missing from a thriller panel.

`fairplay_check.py` writes `fairplay.md`; `inspector-fairplay` writes
`fairplay-planting.md`. Different files — only the inspector verdict is expected
here, and it is expected in EVERY chapter, so no reveal-chapter logic belongs in
this check.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import lexicon_check, penny_genre
from scripts.penny_paths import output_path

# The engine's fixed inspector -> verdict-file table (mirrors the runbook's
# table in commands/review-chapter.md). WHICH of these run is the genre's call;
# what each one is named is the engine's.
VERDICT_FILES = {
    "continuity": "continuity-drift.md",
    "fairplay": "fairplay-planting.md",
    "structure": "structure-tension.md",
    "voice": "character-voice.md",
    "ai-prose": "ai-prose-taste-flags.md",
}

DEVELOPMENTAL_VERDICT = "developmental-edit.md"
VOICE_DRIFT_VERDICT = "voice-drift.md"
LEXICON_VERDICT = "lexicon-fluency.md"


def reviews_dir(book, chapter, repo_root=None) -> Path:
    book2, ch2 = str(book).zfill(2), str(chapter).zfill(2)
    return output_path(f"book-{book2}/chapters/ch-{ch2}.reviews", repo_root)


def check_detail(book, chapter, *, repo_root=None) -> dict:
    """{"findings": [...], "notes": [...]} — findings are the nonzero-exit half.

    Kept separate from `check()`'s flat line list so a caller (and a test) can
    tell the two channels apart without matching on a string prefix: the note
    naming the inert lexicon check contains the word "lexicon" exactly as the
    finding it must NOT be does.
    """
    findings: list[str] = []
    notes: list[str] = []

    reviews = reviews_dir(book, chapter, repo_root)
    present = {p.name for p in reviews.glob("*.md")} if reviews.is_dir() else set()

    for name in penny_genre.inspectors(root=repo_root):
        verdict = VERDICT_FILES.get(name)
        if verdict is None:
            notes.append(
                f"unmapped-inspector: '{name}' is in the genre roster but this "
                f"engine's table names no verdict file for it — its dispatch is "
                f"NOT covered by this check")
            continue
        if verdict not in present:
            findings.append(
                f"missing-inspector-verdict: {verdict} — inspector '{name}' is "
                f"in the genre roster but wrote no verdict")

    if DEVELOPMENTAL_VERDICT not in present:
        findings.append(
            f"missing-developmental-read: {DEVELOPMENTAL_VERDICT} — the "
            f"developmental-editor dispatch wrote nothing")

    if VOICE_DRIFT_VERDICT not in present:
        findings.append(
            f"missing-voice-drift: {VOICE_DRIFT_VERDICT} — the evidence "
            f"inspector-voice weighs; it is free and it did not run")

    if not lexicon_check.default_lexicon(repo_root).is_file():
        notes.append(
            "lexicon-fluency is inert for this series — no authored "
            "config/setting-pack/lexicon.yaml, so lexicon_check.py exits "
            "rather than writing a verdict")
    elif LEXICON_VERDICT not in present:
        findings.append(
            f"missing-lexicon-fluency: {LEXICON_VERDICT} — the series has an "
            f"authored lexicon, so the checker had something to say and did "
            f"not run")

    return {"findings": findings, "notes": notes}


def check(book, chapter, *, repo_root=None) -> tuple[int, list[str]]:
    """(exit_code, lines). 0 = every expected verdict present."""
    detail = check_detail(book, chapter, repo_root=repo_root)
    lines = list(detail["findings"]) + [f"note: {n}" for n in detail["notes"]]
    return (1 if detail["findings"] else 0), lines


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("usage: review_completeness.py <book> <chapter>", file=sys.stderr)
        return 2
    rc, lines = check(argv[0], argv[1])
    for line in lines:
        print(f"review_completeness: {line}")
    if rc == 0:
        print("review_completeness: OK (every expected verdict present)")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
