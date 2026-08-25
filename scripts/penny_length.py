"""Word-count arithmetic for a series' length profile (schema v2; design §5a).

The ONE place chapter bands are resolved and a prose map's authored scene
targets are validated. Reads `config/length-profile.md` — a series-authored
file — through penny_meta, never PyYAML (see CLAUDE.md's dependency-split rule).

The profile carries a flat yaml block (the schema is documented for series
authors in README.md, "The length profile"; the engine ships no default, so a
series that predates this schema must add these keys by hand):

    band_opening:    [1800, 2400]
    band_default:    [2000, 2500]
    min_scene_words: 250

This module is a VALIDATOR, not a generator (spec 2026-07-18 §6): the engine
no longer computes per-scene budgets from emphasis weights. The map-maker
proposes each scene's `Target: A–B words` and the showrunner approves it; the
engine's only opinion is whether the numbers add up — the targets must sum
into the chapter's band, and no scene may be priced below the series'
`min_scene_words` floor. Legacy v1 keys (`weight_<class>`,
`min_<class>_words`) are tolerated and ignored.
"""
from __future__ import annotations

import re
from pathlib import Path

from scripts.penny_meta import load, parse_yaml_blocks

_BAND_PREFIX = "band_"

# The v1 keys the engine stopped reading (spec 2026-07-18 §6): per-class
# emphasis weights and per-class word floors. `min_scene_words` — the v2 floor —
# matches the `min_<class>_words` shape exactly, so it is excluded by name; a
# schema note that listed the live floor among the dead keys would be worse
# than no note at all.
_LEGACY_V1_KEY_RE = re.compile(
    r"^(?:weight_[a-z0-9_]+|min_(?!scene_words$)[a-z0-9_]+_words)$")

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
    for key, value in cfg.items():
        if key.startswith(_BAND_PREFIX):
            lo, hi = _ints(value)
            bands[key[len(_BAND_PREFIX):].replace("_", "-")] = (lo, hi)
    if "default" not in bands:
        raise ValueError(f"length-profile: no band_default — {SCHEMA_HINT}")
    floor = cfg.get("min_scene_words")
    return {"bands": bands,
            "min_scene_words": int(str(floor).strip()) if floor is not None else None,
            "legacy_v1_keys": sorted(k for k in cfg if _LEGACY_V1_KEY_RE.match(k))}


def load_profile(path) -> dict:
    return parse_profile(load(Path(path)))


def schema_note(profile: dict) -> "str | None":
    """Name the series-level fact that `validate_targets` can only whisper.

    Without `min_scene_words` the starved-scene check is inert for every scene
    in every chapter of the whole series, and today the only trace of that is a
    note in one chapter's `map_check` output, read at map time and gone. A
    profile still carrying the v1 `weight_*` / `min_<class>_words` keys is the
    sharper case: it LOOKS like it declares floors, and a map-maker handed those
    numbers prices scenes against a ratio nothing checks.

    Returns None for a profile that declares a floor. One predicate name for
    both floorless cases — the consequence is identical — with the failed
    migration named only when the dead keys are actually there.
    """
    if profile.get("min_scene_words") is not None:
        return None
    legacy = profile.get("legacy_v1_keys") or []
    note = ("no-scene-floor: the length profile declares no min_scene_words, so "
            "map_check's starved-scene can never fire — no scene in this series "
            "can be called too short")
    if legacy:
        note += (f"; the profile is still on schema v1 ({', '.join(legacy)}), and "
                 f"those keys are tolerated and IGNORED — the engine stopped "
                 f"pricing scenes from emphasis weights (spec 2026-07-18 §6)")
    return note + ". Add `min_scene_words: <words>` — see README.md, 'The length profile'."


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
