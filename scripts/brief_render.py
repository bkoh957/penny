"""Compile a locked outline into one prompt-shaped brief per chapter (spec:
docs/superpowers/specs/2026-07-14-outline-prompt-design.md).

Two subcommands:

  check  — the prompt-level defects: a scene whose instruction mass contradicts its
           declared weight, a chapter with no weights in a weighted book, a book of
           undeclared or unrelieved cliffhangers.
  build  — write input/book-NN/briefs/ch-MM.md, stamped with the outline's sha256.

Why this exists: /draft-chapter used to hand the drafter the raw outline section —
ten numbered beats, each written with equal lavishness, reference material formatted
identically to directives. A numbered list is a promise of parity and a model's
default unit is the scene, so ten beats became 3,802 words against an 1,800-2,400
band. The model obeyed the prompt it received. This turns the outline into a prompt.

Deterministic throughout: given a weighted outline there is exactly one correct
brief. The weights themselves are the showrunner's, declared in the outline.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml  # beat-sheet only — nested, human-edited (CLAUDE.md dependency split)

from scripts import penny_paths
from scripts.penny_wiring import has_weights, parse_wired_chapters


def _load_sheet(path) -> dict:
    if path is None or not Path(path).is_file():
        return {}
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def check_briefs(outline_path, *, beat_sheet_path=None) -> dict:
    text = Path(outline_path).read_text(encoding="utf-8")
    chapters = parse_wired_chapters(text)
    if not has_weights(chapters):
        return {"weighted": False, "findings": [], "metrics": {"chapters": len(chapters)}}

    findings: list[str] = []

    for ch in chapters:
        scenes = ch["scenes"]
        if not scenes:
            # A chapter with zero ### Scene blocks (compact-format, or a stub
            # /expand-outline hasn't reached yet — it expands one chapter at
            # a time, so a half-expanded outline is ordinary) has nothing to
            # say about weights or anchors. Flagging it as "no anchor scene"
            # is a false positive that fires on every healthy unexpanded
            # chapter, every run — a check that cries wolf gets ignored.
            continue
        if not any(s["weight"] for s in scenes):
            findings.append(
                f"unweighted-chapter: ch {ch['num']} declares no scene weights in a "
                f"weighted book — the drafter will treat all {len(scenes)} scenes as equal")
            continue
        anchors = [s for s in scenes if s["weight"] == "anchor"]
        if not anchors:
            findings.append(
                f"unweighted-chapter: ch {ch['num']} has no anchor scene — every chapter "
                f"needs one central dramatic experience")
            continue
        heaviest_anchor = max(s["instruction_words"] for s in anchors)
        for s in scenes:
            if s["weight"] == "connective" and s["instruction_words"] > heaviest_anchor:
                findings.append(
                    f"prompt-mass-inversion: ch {ch['num']} scene {s['num']} "
                    f"'{s['title']}' is marked connective but carries "
                    f"{s['instruction_words']} words of instruction against the anchor's "
                    f"{heaviest_anchor} — the prompt says it matters more than the anchor, "
                    f"and the drafter will believe the prompt")

    graded = [c for c in chapters if c["hook_grade"]]
    ungraded = [c["num"] for c in chapters if not c["hook_grade"]]
    if ungraded:
        findings.append(
            f"hook-grade-distribution: chapters {ungraded} declare no hook grade "
            f"(cliffhanger | promise) — a chapter that ends on neither ends on nothing")
    sheet = _load_sheet(beat_sheet_path)
    hooks_cfg = sheet.get("hooks")
    cap = hooks_cfg.get("max_cliffhanger_fraction") if isinstance(hooks_cfg, dict) else None
    if cap is not None and graded:
        cliffs = [c["num"] for c in graded if c["hook_grade"] == "cliffhanger"]
        fraction = len(cliffs) / len(graded)
        if fraction > float(cap):
            findings.append(
                f"hook-grade-distribution: {len(cliffs)}/{len(graded)} chapters end on a "
                f"cliffhanger ({fraction:.0%} > {float(cap):.0%}) — unrelieved cliffhangers "
                f"read as machinery and the reader stops believing them")

    return {"weighted": True, "findings": findings,
            "metrics": {"chapters": len(chapters),
                        "scenes": sum(len(c["scenes"]) for c in chapters)}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Compile a locked outline into chapter briefs.")
    ap.add_argument("command", choices=["check", "build"])
    ap.add_argument("book")
    ap.add_argument("--chapter", default=None, help="only this chapter, e.g. 03")
    args = ap.parse_args(argv)

    root = penny_paths.series_root()
    outline = penny_paths.input_path(f"book-{args.book}/outline.md", root=root)
    if not outline.is_file():
        sys.exit(f"brief: no outline at {outline}")

    if args.command == "check":
        result = check_briefs(outline, beat_sheet_path=_beat_sheet_path(root))
        if not result["weighted"]:
            print("no scene weights detected — skipped "
                  "(the drafter will receive the raw outline section)")
            return 0
        for f in result["findings"]:
            print(f"FINDING: {f}")
        print(f"briefs: {result['metrics']['chapters']} chapter(s), "
              f"{result['metrics']['scenes']} scene(s), "
              f"{len(result['findings'])} finding(s)")
        return 1 if result["findings"] else 0

    # build (a later task): genuinely needs band/weight data, so its
    # length-profile requirement stays here rather than in check_briefs.
    profile = penny_paths.config_path("length-profile.md", root=root)
    if not profile.is_file():
        sys.exit(f"brief: no length profile at {profile}")

    return build(args.book, chapter=args.chapter, repo_root=root)


def _beat_sheet_path(root):
    """The active genre's beat sheet, resolved through penny_genre's `beat_sheet()`
    — never a hardcoded filename (CLAUDE.md). Returns None when the genre declares
    none, which the checks treat as 'no cap configured'."""
    from scripts import penny_genre
    return penny_genre.beat_sheet(root=root)


if __name__ == "__main__":
    raise SystemExit(main())
