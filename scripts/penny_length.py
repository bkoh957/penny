"""Word-count arithmetic for a series' length profile (design §5a).

The ONE place chapter bands and per-scene word budgets are computed. Reads
`config/length-profile.md` — a series-authored file — through penny_meta, never
PyYAML (see CLAUDE.md's dependency-split rule).

The profile carries a flat yaml block (the schema is documented for series
authors in README.md, "The length profile"; the engine ships no default, so a
series that predates this schema must add these keys by hand):

    band_opening:      [1800, 2400]
    band_default:      [2000, 2500]
    weight_anchor:      8
    weight_support:     3
    weight_connective:  1
    min_connective_words: 100
    min_support_words:    250

A scene's budget is its share of the band's midpoint, weighted by its emphasis
class. An anchor is worth eight connective beats because that is what the series
says it is worth — the engine ships no numbers of its own.

The three emphasis classes are the ENGINE's vocabulary, not the series' — the
outline parser (`penny_wiring.WEIGHT_RE`) reads exactly anchor|support|connective
and `brief_render._FORM` carries the drafting prose for exactly those three. What
a series owns is the NUMBERS: each class's relative weight, and each class's
`min_<class>_words` floor (below which a scene is starved and the chapter is
doing more than its band can pay for). A profile may declare a floor for every
class, some, or none.
"""
from __future__ import annotations

import re
from pathlib import Path

from scripts.penny_meta import load, parse_yaml_blocks

_BAND_PREFIX = "band_"
_WEIGHT_PREFIX = "weight_"
_FLOOR_RE = re.compile(r"^min_(.+)_words$")

SCHEMA_HINT = (
    "a length-profile needs band_default: [min, max] (plus any band_<type> "
    "overrides selected by a chapter title's [type: ...] flag) and a "
    "min_scene_words floor for the prose map's scenes — see README.md, 'The "
    "length profile'. (Legacy weight_<class> / min_<class>_words keys are "
    "tolerated and ignored.)"
)


def _ints(value) -> list[int]:
    if isinstance(value, list):
        return [int(str(v).strip()) for v in value]
    raise ValueError(f"length-profile: expected a [min, max] pair, got {value!r}")


def parse_profile(text: str) -> dict:
    """Parse a length profile, or raise a NAMED, actionable ValueError.

    The error names every key the schema needs, because the caller that hits it
    is a series author whose hand-written profile predates the schema — "no
    band_default" told them nothing about what changed or what to write.
    """
    cfg = parse_yaml_blocks(text)
    bands: dict[str, tuple[int, int]] = {}
    weights: dict[str, int] = {}
    floors: dict[str, int] = {}
    for key, value in cfg.items():
        if key.startswith(_BAND_PREFIX):
            lo, hi = _ints(value)
            bands[key[len(_BAND_PREFIX):].replace("_", "-")] = (lo, hi)
        elif key.startswith(_WEIGHT_PREFIX):
            weights[key[len(_WEIGHT_PREFIX):].replace("_", "-")] = int(str(value).strip())
        else:
            m = _FLOOR_RE.match(key)
            if m:
                floors[m.group(1).replace("_", "-")] = int(str(value).strip())
    if "default" not in bands:
        raise ValueError(f"length-profile: no band_default — {SCHEMA_HINT}")
    return {"bands": bands, "weights": weights, "floors": floors,
            "min_connective_words": floors.get("connective", 0),
            "min_scene_words": floors.get("scene")}


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
    if not weights:
        return []
    target = (band[0] + band[1]) // 2
    shares = [table[w] for w in weights]
    total = sum(shares)
    if total == 0:
        raise ValueError(
            f"length-profile: scene weight classes {sorted(set(weights))!r} sum to "
            "zero for this chapter's scenes — the chapter's word target cannot be "
            "shared out. Give at least one of these classes a nonzero weight_* "
            "value in length-profile.md."
        )
    budgets = [target * s // total for s in shares]
    heaviest = max(range(len(shares)), key=lambda i: shares[i])
    budgets[heaviest] += target - sum(budgets)
    return budgets


def validate_targets(profile: dict, band: tuple[int, int],
                     scenes: list[dict]) -> dict:
    """Validate a prose map's AUTHORED per-scene targets against the band.

    The redesign flips this module from generator to validator: the map-maker
    proposes targets and the showrunner approves them; the engine's only
    opinion is whether the numbers add up (spec 2026-07-18 §6).
    """
    blocking: list[str] = []
    notes: list[str] = []
    parseable = [s for s in scenes if s.get("target")]
    for s in scenes:
        if not s.get("target"):
            blocking.append(
                f"unparseable-target: scene {s['num']} '{s['title']}' has no "
                f"parseable `Target: A–B words` line — every scene must be priced")
    if parseable:
        lo = sum(s["target"][0] for s in parseable)
        hi = sum(s["target"][1] for s in parseable)
        if lo > band[1] or hi < band[0]:
            blocking.append(
                f"band-mismatch: scene targets sum to {lo}–{hi} words against a "
                f"chapter band of {band[0]}–{band[1]} — the map and the length "
                f"profile disagree about the chapter's size")
    floor = profile.get("min_scene_words")
    if floor is None:
        notes.append(
            "starved-scene — the floor check could not run: the length profile "
            "declares no min_scene_words (schema v2); no scene can be called starved")
    else:
        for s in parseable:
            if s["target"][1] < floor:
                blocking.append(
                    f"starved-scene: scene {s['num']} '{s['title']}' tops out at "
                    f"{s['target'][1]} words against the profile's {floor}-word "
                    f"min_scene_words floor — a scene priced this low is a beat, "
                    f"not a scene; fold it into a neighbour or cut it")
    return {"blocking": blocking, "notes": notes}
