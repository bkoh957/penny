"""Whodunit-ledger loading and identity — the ONE guarded entry point (PyYAML is
allowed here: the ledger is genuinely nested human-edited data).
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml  # the whodunit ledger is legitimately PyYAML (nested, human-edited
# data — CLAUDE.md dependency split), not config/frontmatter.

NO_WHODUNIT = "none"  # sentinel for built_from_whodunit when no ledger existed at
# build time. A real sha256 digest is 64 lowercase hex characters, so this
# string can never collide with one. ALWAYS written (never omitted) — an
# absent ledger is a fact this build saw, not an exemption from staleness
# (CLAUDE.md: nothing drifts silently).


def load_ledger(path) -> dict:
    """Read + parse the whodunit ledger at `path` — the ONE guarded entry point
    every caller uses (build()'s _obligations, preflight.cmd_draft). A ledger
    that cannot be read, is not valid YAML, whose top level is not a mapping,
    or whose `clue_schedule`/`red_herrings` are not lists of mappings produces
    a NAMED ValueError identifying the path and the problem — never a raw
    ParserError/AttributeError/OSError traceback. Callers turn this into their
    own convention (a per-chapter FAILED line here, a `preflight: <predicate>`
    exit there).

    The guard must reach the data its callers actually use, not just the
    ledger's top level: `_obligations` iterates `clue_schedule`/`red_herrings`
    and calls `.get(...)` on each entry, so a top-level-mapping check alone
    left a `clue_schedule: 'not a list'` (iterates the string's characters,
    then `.get()` on a one-character string) or a
    `clue_schedule: [just-a-string, 42]` (`.get()` on a non-dict entry) free
    to raise a bare AttributeError that escapes build()'s `except ValueError`
    and aborts the whole book mid-loop with a raw traceback."""
    path = Path(path)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        raise ValueError(f"unreadable-ledger: cannot read {path} — {e}") from e
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        raise ValueError(f"malformed-ledger: {path} is not valid YAML — {e}") from e
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(
            f"malformed-ledger: {path} top level is a {type(data).__name__}, "
            "not a mapping — cannot read clue_schedule/red_herrings from it")
    for key in ("clue_schedule", "red_herrings"):
        _validate_entry_list(data, key, path)
    return data


def _validate_entry_list(data: dict, key: str, path: Path) -> None:
    """`data[key]`, if present, must be a list of mappings — the shape every
    caller (`_obligations`, `_plant_chapter`) relies on when it calls `.get()`
    or subscripts an entry. Absent is fine (nothing to validate); present but
    wrong-shaped is a named malformed-ledger error naming the offending key
    and, for a bad entry, its index."""
    entries = data.get(key)
    if entries is None:
        return
    if not isinstance(entries, list):
        raise ValueError(
            f"malformed-ledger: {path} key {key!r} is a "
            f"{type(entries).__name__}, not a list — cannot read scheduled "
            "clues from it")
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(
                f"malformed-ledger: {path} key {key!r}[{i}] is a "
                f"{type(entry).__name__} ({entry!r}), not a mapping — cannot "
                "read its id/plant_chapter")


def ledger_identity(path) -> str:
    """The ledger's identity, used for BOTH stamping (build) and comparison
    (stale_briefs): its sha256 if the file exists and is readable, or
    NO_WHODUNIT if none exists yet. A ledger that EXISTS but cannot be read
    (permission denied) is a real failure, not silent absence — those two
    must not be conflated, so this raises the same named ValueError as
    load_ledger rather than letting a bare PermissionError escape."""
    path = Path(path)
    if not path.is_file():
        return NO_WHODUNIT
    try:
        raw = path.read_bytes()
    except OSError as e:
        raise ValueError(f"unreadable-ledger: cannot read {path} — {e}") from e
    return hashlib.sha256(raw).hexdigest()


def _plant_chapter(entry: dict, led: Path) -> int:
    """The clue's scheduled chapter, validated. `.get(key, default)` only
    substitutes when the key is ABSENT — a hand-edited `plant_chapter: null`
    leaves the key present with value None, so a bare `int(entry.get(...))`
    raises a bare TypeError that crashes the whole book build. Both a missing
    key and an explicit null are equally "we don't know which chapter this
    clue belongs to" — neither is safe to silently coerce to 0."""
    raw = entry.get("plant_chapter")
    cid = entry.get("id", "<no id>")
    if raw is None:
        raise ValueError(
            f"malformed-plant-chapter: clue {cid!r} in {led} has no "
            "plant_chapter (missing or null) — cannot schedule its obligation")
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise ValueError(
            f"malformed-plant-chapter: clue {cid!r} in {led} has a "
            f"non-integer plant_chapter {raw!r} — cannot schedule its obligation")


def clues_by_chapter(path) -> dict:
    """{chapter number: [clue ids]} from the locked ledger — the clue half of a
    chapter's obligation load. Shared with tension_check's overloaded-chapter, which
    needs the same schedule to know what the chapter's word band must pay for.
    Raises the same named ValueErrors load_ledger/_plant_chapter do."""
    led = Path(path)
    data = load_ledger(led)
    out: dict[int, list[str]] = {}
    for key in ("clue_schedule", "red_herrings"):
        for entry in (data.get(key) or []):
            out.setdefault(_plant_chapter(entry, led), []).append(
                str(entry.get("id", "<no id>")))
    return out


def file_sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
