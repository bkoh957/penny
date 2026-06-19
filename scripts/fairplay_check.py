"""Fair-play checker — whodunit-ledger consistency (Tier-3, may block).

Reads a per-book ledger (series/whodunit/book-NN.yaml, PyYAML) and the scalar
culprit_by_fraction from run-config.md (penny_meta — the flat side of the
two-reader boundary). Audits the PLAN's fairness, not the prose (prose-planting is
the 2b inspector's job). Fairness failures emit BLOCKING: lines.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow `import scripts.*` when run directly as `python3 scripts/fairplay_check.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml

from scripts.penny_meta import load, parse_yaml_blocks
from scripts.penny_verdict import write_verdict

DEFAULT_RUN_CONFIG = Path("config/run-config.md")
_REQUIRED = ("book", "total_chapters", "reveal_chapter", "culprit",
             "culprit_first_appearance_chapter")


def load_fraction(run_config_path) -> float:
    """Read culprit_by_fraction from run-config.md. Hard-fail if absent/non-numeric."""
    cfg = parse_yaml_blocks(load(run_config_path))
    raw = cfg.get("culprit_by_fraction")
    if raw is None:
        sys.exit("fairplay: culprit_by_fraction missing from run-config.md")
    try:
        return float(raw)
    except (TypeError, ValueError):
        sys.exit(f"fairplay: culprit_by_fraction not numeric: {raw!r}")


def _load_ledger(path) -> dict:
    path = Path(path)
    if not path.is_file():
        sys.exit(f"fairplay: ledger not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        sys.exit(f"fairplay: ledger is not valid YAML ({path}): {exc}")
    if not isinstance(data, dict):
        sys.exit(f"fairplay: ledger must be a mapping: {path}")
    return data


def _is_int_in_range(v, lo, hi) -> bool:
    return isinstance(v, int) and lo <= v <= hi


def check_fairplay(ledger_path, *, culprit_by_fraction: float) -> dict:
    led = _load_ledger(ledger_path)
    blocking: list[str] = []
    notes: list[str] = []

    # 1. Well-formed first; on failure, stop (don't pile on derived failures).
    missing = [k for k in _REQUIRED if k not in led]
    total = led.get("total_chapters")
    reveal = led.get("reveal_chapter")
    if missing:
        blocking.append(f"malformed ledger: missing fields {sorted(missing)}")
        return {"blocking": blocking, "notes": notes, "metrics": {}}
    if not _is_int_in_range(total, 1, 10_000):
        blocking.append(f"malformed ledger: total_chapters not in range: {total!r}")
        return {"blocking": blocking, "notes": notes, "metrics": {}}
    if not _is_int_in_range(reveal, 1, total):
        blocking.append(f"malformed ledger: reveal_chapter not in 1..total_chapters: {reveal!r}")
        return {"blocking": blocking, "notes": notes, "metrics": {}}

    appearance = led["culprit_first_appearance_chapter"]
    if not _is_int_in_range(appearance, 1, total):
        blocking.append(f"malformed ledger: culprit_first_appearance_chapter invalid: {appearance!r}")
        return {"blocking": blocking, "notes": notes, "metrics": {}}

    # 2. Necessary clues scheduled before the reveal.
    for clue in led.get("clue_schedule", []):
        if clue.get("necessary"):
            plant = clue.get("plant_chapter")
            cid = clue.get("id", "?")
            if not isinstance(plant, int):
                blocking.append(f"necessary clue {cid} has no valid plant_chapter")
            elif plant >= reveal:
                blocking.append(f"necessary clue {cid} scheduled at/after reveal (ch {plant} >= {reveal})")

    # 3. Culprit floor (non-negotiable). Seed only if floor passes (one fault, one line).
    if appearance >= reveal:
        blocking.append(f"culprit first appears at/after reveal (ch {appearance} >= {reveal})")
    else:
        bound = round(culprit_by_fraction * total)
        if appearance > bound:
            blocking.append(
                f"culprit introduced too late: first appears ch {appearance}, "
                f"must be by chapter {bound} ({culprit_by_fraction:g} of the book)")

    # 4. Auditable culprit gap.
    culprit = led["culprit"]
    culprit_alibis = [a for a in led.get("alibi_grid", []) if a.get("suspect") == culprit]
    if culprit_alibis and all(a.get("holds") for a in culprit_alibis):
        blocking.append(f"culprit {culprit} has no auditable alibi gap (all alibis hold)")

    # Evidence (non-blocking).
    mention = led.get("culprit_first_mention_chapter")
    if isinstance(mention, int) and mention < appearance:
        notes.append(f"culprit mentioned (ch {mention}) before on-page appearance (ch {appearance})")
    for clue in led.get("clue_schedule", []):
        p = clue.get("plant_chapter")
        if isinstance(p, int) and p >= reveal:
            notes.append(f"clue {clue.get('id','?')} planted at/after reveal (non-necessary)")
    for rh in led.get("red_herrings", []):
        if rh.get("must_not_cheat") is False:
            notes.append(f"red herring {rh.get('id','?')} flagged must_not_cheat: false")
    # culprit-id resolution: evidence-only in 2a (promoted to BLOCKING in 2b/3).
    chars = Path(__file__).resolve().parents[1] / "series/continuity/characters"
    if chars.is_dir() and any(chars.iterdir()):
        if not (chars / f"{culprit}.md").is_file():
            notes.append(f"culprit id '{culprit}' does not resolve in series/continuity/characters/ (evidence; blocking in 2b/3)")

    metrics = {"reveal_chapter": reveal, "total_chapters": total,
               "culprit_first_appearance_chapter": appearance}
    return {"blocking": blocking, "notes": notes, "metrics": metrics}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Fair-play ledger-consistency checker.")
    ap.add_argument("ledger", help="path to series/whodunit/book-NN.yaml")
    ap.add_argument("--out", default=None, help="reviews dir to write fairplay.md")
    ap.add_argument("--run-config", default=str(DEFAULT_RUN_CONFIG))
    ap.add_argument("--target", default="unknown")
    args = ap.parse_args(argv)

    fraction = load_fraction(args.run_config)
    result = check_fairplay(args.ledger, culprit_by_fraction=fraction)

    out_dir = args.out or "."
    write_verdict(
        out_dir=out_dir, producer="fairplay_check.py", kind="deterministic-checker",
        target=args.target, name="fairplay",
        blocking=result["blocking"], notes=result["notes"],
        metrics=result["metrics"], evidence=[],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
