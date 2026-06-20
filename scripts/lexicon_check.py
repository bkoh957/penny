"""Lexicon fluency check — Tier-3, evidence-only.

Detects premature out-of-stage lexicon terms in NARRATION (dialogue removed). The
fluency dial is deterministic in one direction only — a term tagged for a later
stage appearing now is countable evidence. Insufficient idiom in later books is a
taste judgment and stays inspector-voice's job. Per the Phase-2a rule, this checker
NEVER emits BLOCKING: lines — the blocking call is inspector-voice's.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml

from scripts.penny_meta import parse_canon_meta
from scripts.penny_text import strip_dialogue
from scripts.penny_verdict import write_verdict

REPO = Path(__file__).resolve().parents[1]
DEFAULT_LEXICON = REPO / "config/setting-pack/lexicon.yaml"
DEFAULT_CANON_CORE = REPO / "series/continuity/canon-core.md"

STAGE_RANK = {"OUTSIDER": 0, "SETTLING": 1, "BELONGING": 2}
REQUIRED = ("term", "narration_ok_from_stage", "auto_detectable")


def load_lexicon(path) -> list[dict]:
    path = Path(path)
    if not path.is_file():
        sys.exit(f"lexicon_check: lexicon not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        sys.exit(f"lexicon_check: lexicon is not valid YAML ({path}): {exc}")
    if not isinstance(data, dict) or not isinstance(data.get("terms"), list):
        sys.exit(f"lexicon_check: lexicon must have a 'terms:' list: {path}")
    return data["terms"]


def current_stage(canon_core_path) -> str:
    text = Path(canon_core_path).read_text(encoding="utf-8")
    meta = parse_canon_meta(text)
    stage = meta.get("fluency_stage")
    if stage not in STAGE_RANK:
        sys.exit(
            f"lexicon_check: canon-core declares no valid fluency_stage "
            f"(got {stage!r}); expected one of {sorted(STAGE_RANK)}"
        )
    return stage


def scan(text: str, terms: list[dict], stage: str) -> dict:
    """Return {'flags': [...], 'inspector_notes': [...]}. A flag fires iff the term
    is auto_detectable, word-boundary-matches in narration, and its stage outranks
    the current stage. auto_detectable: false terms become inspector-only notes."""
    cur = STAGE_RANK[stage]
    narration = strip_dialogue(text)
    flags: list[dict] = []
    notes: list[dict] = []
    for entry in terms:
        term = entry["term"]
        term_stage = entry["narration_ok_from_stage"]
        if STAGE_RANK[term_stage] <= cur:
            continue  # in-stage (or earlier) — allowed in narration now
        if not entry.get("auto_detectable", False):
            notes.append({"term": term, "term_stage": term_stage,
                          "reason": "auto_detectable=false; inspector judgment"})
            continue
        pattern = re.compile(rf"\b{re.escape(term)}\b", re.I)
        for m in pattern.finditer(narration):
            line = narration[:m.start()].count("\n") + 1
            flags.append({"term": term, "line": line,
                          "term_stage": term_stage, "current_stage": stage})
    return {"flags": flags, "inspector_notes": notes}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Lexicon fluency check (evidence-only).")
    ap.add_argument("chapter", help="path to the chapter markdown file")
    ap.add_argument("--out", default=None, help="reviews dir to write lexicon-fluency.md")
    ap.add_argument("--lexicon", default=str(DEFAULT_LEXICON))
    ap.add_argument("--canon-core", default=str(DEFAULT_CANON_CORE))
    ap.add_argument("--target", default="unknown")
    args = ap.parse_args(argv)

    terms = load_lexicon(args.lexicon)
    stage = current_stage(args.canon_core)
    text = Path(args.chapter).read_text(encoding="utf-8")
    result = scan(text, terms, stage)

    flags, notes = result["flags"], result["inspector_notes"]
    summary = [f"current fluency_stage: {stage}",
               f"premature-term flags: {len(flags)} (evidence-only; inspector decides)"]
    for n in notes:
        summary.append(f"inspector-only term (auto_detectable=false): {n['term']} "
                       f"(ok from {n['term_stage']})")

    out_dir = args.out or str(Path(args.chapter).parent)
    write_verdict(
        out_dir=out_dir, producer="lexicon_check.py", kind="deterministic-checker",
        target=args.target, name="lexicon-fluency",
        blocking=[],  # evidence-only — never blocks
        notes=summary,
        metrics={"current_stage": stage, "flag_count": len(flags),
                 "inspector_note_count": len(notes)},
        evidence=flags[:5],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
