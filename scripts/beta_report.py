"""Beta-reader report serializer + per-persona cross-model collapser (Phase 5).

The blind beta-reader agent supplies *judgment* (engagement scores, put-down
chapters, would-buy verdict); this module enforces *shape* — exactly the
penny_verdict.py / ledger_markers.py split. It never decides anything a reader
should decide; it stamps the persona's lens, validates enums, and (Task 2)
collapses a persona's per-model readings into one converged report.

No cross-PERSONA rollup lives here — that is Phase 6 (the revision-priority
report). See docs/superpowers/specs/2026-06-21-penny-phase5-beta-layer-design.md.
"""
from __future__ import annotations

import json
from pathlib import Path

SCHEMA = "penny-beta/1"

# Single source of truth for the stamped driver enum (spec §5.1). One driver per
# persona lens. Mirrored by the persona files' `driver:` frontmatter; agreement
# is pinned by the scaffold test in Task 3.
DRIVER_BY_PERSONA = {
    "cozy-loyalist": "comfort-tone",
    "puzzle-hawk": "fairness",
    "arc-reader": "transformation",
    "romance-reader": "chemistry",
    "impatient-skimmer": "pace",
    "newcomer-outsider": "onboarding",
}
VERDICTS = {"yes", "no", "n/a"}
ARC_FACETS = {"self", "place"}


def _require(cond, msg):
    if not cond:
        raise ValueError(msg)


def build_raw_reading(*, persona, model, engagement_curve, put_down_points,
                      whodunit_guess, confusion_points, emotional_beats,
                      would_buy_verdict, would_buy_facet=None, notes=""):
    """Normalize + validate one (persona, model) reading into a raw-reading dict.

    `driver` and every emotional-beat `lens` are STAMPED from the persona — never
    taken from the agent payload (spec §5.1 rule 3). `would_buy_verdict` is the
    only yes|no|n/a the reader chooses; `would_buy_facet` (arc-reader only) is the
    only reader-chosen sub-tag.
    """
    _require(persona in DRIVER_BY_PERSONA, f"unknown persona {persona!r}")
    _require(would_buy_verdict in VERDICTS,
             f"would_buy_verdict {would_buy_verdict!r} not in {sorted(VERDICTS)}")
    driver = DRIVER_BY_PERSONA[persona]
    if would_buy_facet is not None:
        _require(persona == "arc-reader",
                 f"facet only valid for arc-reader, not {persona!r}")
        _require(would_buy_facet in ARC_FACETS,
                 f"facet {would_buy_facet!r} not in {sorted(ARC_FACETS)}")
    beats = [{"beat": b, "lens": driver} for b in emotional_beats]
    would_buy = {"verdict": would_buy_verdict, "driver": driver}
    if would_buy_facet is not None:
        would_buy["facet"] = would_buy_facet
    return {
        "schema": SCHEMA,
        "persona": persona,
        "model": model,
        "engagement_curve": list(engagement_curve),
        "put_down_points": list(put_down_points),
        "whodunit_guess": whodunit_guess,
        "confusion_points": list(confusion_points),
        "emotional_beats": beats,
        "would_buy_next": would_buy,
        "notes": notes,
    }


def serialize_raw_reading(reading) -> str:
    return ("---\n"
            f"schema: {reading['schema']}\n"
            f"persona: {reading['persona']}\n"
            f"model: {reading['model']}\n"
            "kind: beta-raw\n"
            "---\n"
            + json.dumps(reading, sort_keys=True, indent=2) + "\n")


def write_raw_reading(out_dir, reading) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{reading['persona']}.{reading['model']}.raw.md"
    path.write_text(serialize_raw_reading(reading), encoding="utf-8")
    return path
