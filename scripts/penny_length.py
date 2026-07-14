"""Word-count arithmetic for a series' length profile (design §5a).

The ONE place chapter bands and per-scene word budgets are computed. Reads
`config/length-profile.md` — a series-authored file — through penny_meta, never
PyYAML (see CLAUDE.md's dependency-split rule).

The profile carries a flat yaml block:

    band_opening:      [1800, 2400]
    band_default:      [2000, 2500]
    weight_anchor:      8
    weight_support:     3
    weight_connective:  1
    min_connective_words: 100

A scene's budget is its share of the band's midpoint, weighted by its emphasis
class. An anchor is worth eight connective beats because that is what the series
says it is worth — the engine ships no numbers of its own.
"""
from __future__ import annotations

from pathlib import Path

from scripts.penny_meta import load, parse_yaml_blocks

_BAND_PREFIX = "band_"
_WEIGHT_PREFIX = "weight_"


def _ints(value) -> list[int]:
    if isinstance(value, list):
        return [int(str(v).strip()) for v in value]
    raise ValueError(f"length-profile: expected a [min, max] pair, got {value!r}")


def parse_profile(text: str) -> dict:
    cfg = parse_yaml_blocks(text)
    bands: dict[str, tuple[int, int]] = {}
    weights: dict[str, int] = {}
    for key, value in cfg.items():
        if key.startswith(_BAND_PREFIX):
            lo, hi = _ints(value)
            bands[key[len(_BAND_PREFIX):].replace("_", "-")] = (lo, hi)
        elif key.startswith(_WEIGHT_PREFIX):
            weights[key[len(_WEIGHT_PREFIX):].replace("_", "-")] = int(str(value).strip())
    if "default" not in bands:
        raise ValueError("length-profile: no band_default")
    floor = cfg.get("min_connective_words")
    return {"bands": bands, "weights": weights,
            "min_connective_words": int(str(floor).strip()) if floor else 0}


def load_profile(path) -> dict:
    return parse_profile(load(Path(path)))


def band_for(profile: dict, chapter_type: "str | None") -> tuple[int, int]:
    """The [min, max] band for a declared chapter type; the default band otherwise.

    The type is DECLARED in the chapter title, never inferred from the prose — the
    drafter used to guess it, which is how a chapter gets graded against a band it
    was never written for.
    """
    bands = profile["bands"]
    if chapter_type and chapter_type in bands:
        return bands[chapter_type]
    return bands["default"]


def scene_budgets(profile: dict, band: tuple[int, int], weights: list[str]) -> list[int]:
    """Split the band's midpoint across scenes in proportion to their emphasis class.

    The remainder from integer division lands on the heaviest scene, so the budgets
    always sum to the target exactly — a chapter's price is never quietly lost to
    rounding.
    """
    table = profile["weights"]
    for w in weights:
        if w not in table:
            raise ValueError(f"unknown scene weight {w!r} (known: {sorted(table)})")
    target = (band[0] + band[1]) // 2
    shares = [table[w] for w in weights]
    total = sum(shares)
    if total == 0:
        return [0] * len(weights)
    budgets = [target * s // total for s in shares]
    heaviest = max(range(len(shares)), key=lambda i: shares[i])
    budgets[heaviest] += target - sum(budgets)
    return budgets
