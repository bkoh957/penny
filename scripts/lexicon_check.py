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


def validate_lexicon(terms: list[dict]) -> list[str]:
    """Whole-lexicon required-field check. Returns one error string per offending
    entry/field — ALL of them, never just the first. Empty list == valid."""
    errors: list[str] = []
    for i, entry in enumerate(terms):
        label = entry.get("term", f"<entry #{i + 1} missing 'term'>")
        for field in REQUIRED:
            if field not in entry:
                errors.append(f"{label}: missing required field '{field}'")
        if "auto_detectable" in entry and not isinstance(entry["auto_detectable"], bool):
            errors.append(f"{label}: auto_detectable must be true/false")
        stage = entry.get("narration_ok_from_stage")
        if stage is not None and stage not in STAGE_RANK:
            errors.append(f"{label}: invalid narration_ok_from_stage {stage!r}")
    return errors


_PROSE_STAGE_RE = re.compile(r"\*\*(OUTSIDER|SETTLING|BELONGING)\*\*")


def prose_stage(canon_core_text: str) -> "str | None":
    """The first bolded stage name in the prose body, or None."""
    m = _PROSE_STAGE_RE.search(canon_core_text)
    return m.group(1) if m else None


def stage_drift(canon_core_text: str) -> "str | None":
    """A message if the canon-meta stage and the prose stage disagree, else None.
    A missing prose stage is not drift (the machine value is authoritative)."""
    meta = parse_canon_meta(canon_core_text).get("fluency_stage")
    prose = prose_stage(canon_core_text)
    if prose is not None and meta is not None and prose != meta:
        return (f"fluency_stage drift: canon-meta says {meta!r} but prose says "
                f"{prose!r} — reconcile (canon-meta is authoritative)")
    return None


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
    ap.add_argument("chapter", nargs="?", default=None,
                    help="path to the chapter markdown file")
    ap.add_argument("--validate", action="store_true",
                    help="validate the whole lexicon (lock-time gate) and exit")
    ap.add_argument("--out", default=None, help="reviews dir to write lexicon-fluency.md")
    ap.add_argument("--lexicon", default=str(DEFAULT_LEXICON))
    ap.add_argument("--canon-core", default=str(DEFAULT_CANON_CORE))
    ap.add_argument("--target", default="unknown")
    args = ap.parse_args(argv)

    if args.validate:
        errors = validate_lexicon(load_lexicon(args.lexicon))
        drift = stage_drift(Path(args.canon_core).read_text(encoding="utf-8"))
        if drift:
            errors.append(drift)
        if errors:
            sys.exit("lexicon_check --validate FAILED:\n  - " + "\n  - ".join(errors))
        print("lexicon_check: OK (lexicon valid, no stage drift)")
        return 0
    if args.chapter is None:
        ap.error("chapter is required unless --validate is given")

    terms = load_lexicon(args.lexicon)
    errors = validate_lexicon(terms)
    if errors:
        sys.exit("lexicon_check: invalid lexicon:\n  - " + "\n  - ".join(errors))
    stage = current_stage(args.canon_core)
    text = Path(args.chapter).read_text(encoding="utf-8")
    result = scan(text, terms, stage)

    flags, notes = result["flags"], result["inspector_notes"]
    summary = [f"current fluency_stage: {stage}",
               f"premature-term flags: {len(flags)} (evidence-only; inspector decides)"]
    for n in notes:
        summary.append(f"inspector-only term (auto_detectable=false): {n['term']} "
                       f"(ok from {n['term_stage']})")
    drift = stage_drift(Path(args.canon_core).read_text(encoding="utf-8"))
    if drift:
        summary.append(drift)

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
