"""Prose-map checker (spec 2026-07-18 §6/7) — the map's coverage, pricing, and
staleness against its packet.

Three families of finding, one dict:
  - pricing (band-mismatch, starved-scene, unparseable-target) — delegated
    straight through from `penny_length.validate_targets`, priced against
    `band_for(profile, chapter_type)` where chapter_type comes off the
    packet's own `## Chapter NN ... [type: ...]` heading.
  - coverage (dropped-beat, duplicate-beat) — every packet `### Required
    Beats` line must land in exactly one scene's `Beats covered:` line. The
    1-based index into that list IS the id a map's `Beats covered:` line
    uses (penny_wiring.parse_required_beats: "ORDER IS CONTRACT").
  - clue scheduling (unscheduled-clue) — every ledger clue id named under the
    packet's `## Ledger Clues` heading must appear in some scene's `Clue:`
    text; an id that appears nowhere is a clue the map forgot to plant.

`check_map` never touches the filesystem or hashes anything — that split is
deliberate (per CLAUDE.md's dependency-split spirit: keep pure logic pure).
The CLI computes the packet FILE's sha256 and compares it to the map's
`built_from_packet` stamp, emitting `stale-map` itself.

Dependency-free (penny_meta only, via the modules this imports — no PyYAML).
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.packet_assemble import packet_path
from scripts.penny_length import band_for, parse_profile, validate_targets
from scripts.penny_map import map_path, parse_map
from scripts.penny_paths import config_path
from scripts.penny_wiring import parse_wired_chapters

# Only harvests ids from a packet's `## Ledger Clues` section — see
# _ledger_clue_ids, which bounds the search to that section before this ever
# runs, so an authored "- [x]"-style bullet anywhere else in the packet
# (Continuity Extracts, Standing Series Guardrails, ...) can't inject an id.
PACKET_CLUE_RE = re.compile(r"^\s*-\s*\[([^\]]+)\]", re.MULTILINE)

_LEDGER_CLUES_HEADING_RE = re.compile(r"^##\s+Ledger Clues\s*$", re.MULTILINE)
_H2_RE = re.compile(r"^##\s+", re.MULTILINE)

_NO_PROFILE_NOTE = ("targets — the pricing checks could not run: no "
                     "parseable length profile")


def _ledger_clue_ids(packet_text: str) -> list[str]:
    """Clue ids bulleted under the packet's `## Ledger Clues` heading, and
    nothing past the next `## ` heading."""
    m = _LEDGER_CLUES_HEADING_RE.search(packet_text)
    if not m:
        return []
    start = m.end()
    nm = _H2_RE.search(packet_text, start)
    end = nm.start() if nm else len(packet_text)
    return PACKET_CLUE_RE.findall(packet_text[start:end])


def check_map(packet_text: str, map_text: str, profile: "dict | None") -> dict:
    blocking: list[str] = []
    notes: list[str] = []

    chapters = parse_wired_chapters(packet_text)
    ch = chapters[0] if chapters else {"required_beats": [], "chapter_type": None}
    beats = ch["required_beats"]

    parsed_map = parse_map(map_text)
    scenes = parsed_map["scenes"]

    # --- pricing: band/targets, straight through from penny_length ---
    if profile is None:
        notes.append(_NO_PROFILE_NOTE)
    else:
        band = band_for(profile, ch["chapter_type"])
        priced = validate_targets(profile, band, scenes)
        blocking.extend(priced["blocking"])
        notes.extend(priced["notes"])

    # --- coverage: every Required Beat lands in exactly one scene ---
    claimed: dict[int, list[int]] = {}
    for s in scenes:
        for idx in s["beats_covered"]:
            claimed.setdefault(idx, []).append(s["num"])
            if not 1 <= idx <= len(beats):
                blocking.append(
                    f"dropped-beat: scene {s['num']} claims beat {idx} but "
                    f"the packet lists only {len(beats)} Required Beats")
    for i, beat in enumerate(beats, 1):
        owners = claimed.get(i, [])
        if not owners:
            blocking.append(
                f"dropped-beat: Required Beat {i} '{beat}' lands in no "
                f"scene's `Beats covered:` line — the map loses a moment "
                f"the book breaks without")
        elif len(owners) > 1:
            blocking.append(
                f"duplicate-beat: Required Beat {i} '{beat}' is claimed by "
                f"scenes {owners} — one beat, one home")

    # --- clue scheduling: every ledger clue id must be planted somewhere ---
    clue_ids = _ledger_clue_ids(packet_text)
    all_clue_text = " ".join(s["clue_text"] or "" for s in scenes)
    for cid in clue_ids:
        # A plain substring test lets "clue-jam" match inside "clue-jam-2" —
        # a real clue id that happens to be a hyphenated prefix of another
        # one. A bare \b...\b word-boundary regex does not fix this: regex
        # \b treats the hyphen itself as a boundary, so "clue-jam" still
        # matches at the start of "clue-jam-2". The token IS the id
        # including its internal hyphens, so the character immediately
        # before/after the match must not be a further identifier character
        # (word char OR hyphen) — a lookaround pins that, a plain \b cannot.
        if not re.search(rf"(?<![\w-]){re.escape(cid)}(?![\w-])", all_clue_text):
            blocking.append(
                f"unscheduled-clue: ledger clue [{cid}] appears in no "
                f"scene's Clue: line — an unplanted clue is an unfair reveal")

    return {"blocking": blocking, "notes": notes}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("usage: map_check.py <book> <chapter>", file=sys.stderr)
        return 2
    book, chapter = argv

    p_path = packet_path(book, chapter)
    if not p_path.is_file():
        print(f"map_check: packet not found: {p_path}", file=sys.stderr)
        return 2
    m_path = map_path(book, chapter)
    if not m_path.is_file():
        print(f"map_check: map not found: {m_path}", file=sys.stderr)
        return 2

    packet_bytes = p_path.read_bytes()
    packet_text = packet_bytes.decode("utf-8")
    map_text = m_path.read_text(encoding="utf-8")

    profile = None
    profile_path = config_path("length-profile.md")
    if profile_path.is_file():
        try:
            profile = parse_profile(profile_path.read_text(encoding="utf-8"))
        except ValueError as e:
            print(f"map_check: {e}", file=sys.stderr)
            profile = None

    result = check_map(packet_text, map_text, profile)

    # --- staleness: the map's stamp against the packet FILE's current sha256 ---
    parsed_map = parse_map(map_text)
    actual_sha = hashlib.sha256(packet_bytes).hexdigest()
    if parsed_map["stamp"] != actual_sha:
        result["blocking"].append(
            f"stale-map: map's built_from_packet stamp "
            f"{parsed_map['stamp']!r} does not match the packet's current "
            f"sha256 {actual_sha} — rebuild the map from the current packet")

    for line in result["blocking"]:
        print(f"BLOCKING: {line}")
    for line in result["notes"]:
        print(f"note: {line}")

    return 1 if result["blocking"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
