#!/usr/bin/env python3
"""Cut input/series/background-history.md into derived continuity entries and
the setting pack (spec 2026-08-13).

Pure functions take text and return findings; all IO lives in main(). The cut
never writes canon-core.md, continuity/characters/, or any whodunit ledger —
those have their own owners (spec §6).
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import penny_meta, penny_paths  # noqa: E402

PART_HEADINGS = ("Stance", "Town", "Characters", "Relationships", "Secrets")
KIND_BY_PART = {
    "Town": "town",
    "Characters": "character",
    "Relationships": "relationship",
    "Secrets": "secret",
}

_EM_DASH = "—"
_HEADING_RE = re.compile(r"^(?P<hashes>#{2,})\s+(?P<title>.+?)\s*$")
_AND_RE = re.compile(r"\s+and\s+", re.IGNORECASE)


def slug(title: str) -> str:
    """Truncate at the first em dash, then lowercase with non-alphanumerics
    collapsed to single hyphens."""
    head = title.split(_EM_DASH, 1)[0]
    out = re.sub(r"[^a-z0-9]+", "-", head.strip().lower())
    return out.strip("-")


def relationship_slug(title: str) -> "str | None":
    """`Maggie and Cal` -> `cal--maggie`. None when there is no ` and `."""
    parts = _AND_RE.split(title.split(_EM_DASH, 1)[0].strip(), maxsplit=1)
    if len(parts) != 2:
        return None
    left, right = slug(parts[0]), slug(parts[1])
    if not left or not right:
        return None
    return "--".join(sorted((left, right)))


def parse_background(text: str) -> dict:
    """Split the source on its heading contract (spec §3)."""
    stance_lines: list[str] = []
    entries: list[dict] = []
    unknown_parts: list[str] = []
    deep_headings: list[str] = []

    part: "str | None" = None
    current: "dict | None" = None
    buf: list[str] = []

    def flush():
        nonlocal current, buf
        if current is not None:
            current["body"] = "\n".join(buf).strip()
            entries.append(current)
        current, buf = None, []

    for line in text.splitlines():
        m = _HEADING_RE.match(line)
        if not m:
            if current is not None:
                buf.append(line)
            elif part == "Stance":
                stance_lines.append(line)
            continue

        level, title = len(m.group("hashes")), m.group("title")
        if level == 2:
            flush()
            part = title if title in PART_HEADINGS else None
            if title not in PART_HEADINGS:
                unknown_parts.append(title)
            continue
        if level >= 4:
            deep_headings.append(title)
            continue
        # level == 3
        flush()
        if part is None or part == "Stance":
            continue
        kind = KIND_BY_PART[part]
        s = relationship_slug(title) if kind == "relationship" else slug(title)
        current = {"part": part, "kind": kind, "title": title, "slug": s}

    flush()
    return {
        "stance": "\n".join(stance_lines).strip(),
        "entries": entries,
        "unknown_parts": unknown_parts,
        "deep_headings": deep_headings,
    }


def check_background(parsed: dict) -> dict:
    """Named findings over the parsed source (spec §5.2). No waivers."""
    blocking: list[str] = []
    notes: list[str] = []

    if not parsed["stance"].strip():
        blocking.append(
            "missing-stance: no `## Stance` block, or its body is empty — "
            "the setting pack is authored, not derived (spec §3.1)")

    for title in parsed["unknown_parts"]:
        blocking.append(
            f"unknown-section: `## {title}` is not one of "
            f"{', '.join(PART_HEADINGS)}")

    for title in parsed["deep_headings"]:
        blocking.append(
            f"unknown-entry-depth: `#### {title}` — entries are `###` only")

    seen: dict[str, str] = {}
    for e in parsed["entries"]:
        if e["slug"] is None:
            blocking.append(
                f"malformed-relationship: `### {e['title']}` has no ` and ` "
                f"separator")
            continue
        if e["slug"] == "":
            blocking.append(
                f"unslugged-entry: `### {e['title']}` produced no usable "
                f"identifier — give it a title with at least one letter or "
                f"digit")
            continue
        if e["slug"] in seen:
            blocking.append(
                f"duplicate-entry: `### {e['title']}` and "
                f"`### {seen[e['slug']]}` both slug to `{e['slug']}`")
            continue
        seen[e["slug"]] = e["title"]

    return {"blocking": blocking, "notes": notes}


BACKGROUND_DIR = "series/continuity/background"
SETTING_PACK_REL = "config/setting-pack/setting.md"


def body_sha(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def _fmt(value) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(str(v) for v in value) + "]"
    return str(value)


def stamp(body: str, meta: dict) -> str:
    """Prepend the canon-meta comment header. Comment form, not frontmatter —
    packet_assemble reads entries with parse_canon_meta, which only sees this
    form (spec §4)."""
    inner = ", ".join(f"{k}: {_fmt(v)}" for k, v in meta.items())
    return f"<!-- canon-meta: {{{inner}}} -->\n\n{body.strip()}\n"


def build_entries(parsed: dict, source_sha: str) -> list[dict]:
    """Emitted files for a parsed source. Assumes check_background is clean."""
    entries = [e for e in parsed["entries"] if e["slug"]]
    rel_slugs = {e["slug"] for e in entries if e["kind"] == "relationship"}

    def links_for(e: dict) -> list[str]:
        if e["kind"] == "relationship":
            return sorted(e["slug"].split("--"))
        if e["kind"] == "character":
            return sorted(r for r in rel_slugs
                          if e["slug"] in r.split("--"))
        return []

    out: list[dict] = []
    for e in entries:
        meta = {
            "id": e["slug"],
            "kind": e["kind"],
            "links": links_for(e),
            "source": f"{e['part'].lower()}-{e['slug']}",
            "built_from_background": source_sha,
            "cut_output_sha256": body_sha(e["body"]),
        }
        out.append({"rel": f"{BACKGROUND_DIR}/{e['slug']}.md",
                    "text": stamp(e["body"], meta)})

    stance = parsed["stance"]
    out.append({
        "rel": SETTING_PACK_REL,
        "text": stamp(stance, {
            "id": "setting-pack",
            "kind": "stance",
            "built_from_background": source_sha,
            "cut_output_sha256": body_sha(stance),
        }),
    })
    return out


def target_refusal(existing_text: str, rel: str) -> "str | None":
    """Guard an existing file at a derived path (spec §5.1).

    An absent stamp is a refusal, not a licence: a file with no
    cut_output_sha256 was never produced by a cut, so it is hand-authored work
    and deleting it is the showrunner's explicit act — the same branch that
    protects a hand-authored outline.md.
    """
    meta = penny_meta.parse_canon_meta(existing_text)
    stamped = str(meta.get("cut_output_sha256", "")).strip()
    if not stamped:
        return (f"unstamped-target: {rel} has no cut_output_sha256 — it was "
                f"not produced by a cut. Delete it to adopt the layer.")
    body = existing_text.split("-->", 1)[1] if "-->" in existing_text else existing_text
    if body_sha(body) != stamped:
        return (f"target-modified-since-cut: {rel} was edited by hand since "
                f"the last cut. Move the change into background-history.md.")
    return None


def orphan_notes(existing_rels: list, produced_rels: list) -> list:
    """Advisory only — never deleted. A vanished heading is as likely to be a
    rename in progress as a deletion (spec §5.2)."""
    produced = set(produced_rels)
    return [
        f"orphan-derived: {rel} has no section in background-history.md. "
        f"It still loads into packets until you delete it."
        for rel in sorted(existing_rels) if rel not in produced
    ]


SOURCE_REL = "input/series/background-history.md"


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv:
        print("usage: background_cut.py   (run from a series root)",
              file=sys.stderr)
        return 2

    root = penny_paths.series_root()
    src = root / SOURCE_REL
    if not src.is_file():
        print(f"background_cut: missing {src}", file=sys.stderr)
        return 2

    text = src.read_text(encoding="utf-8")
    parsed = parse_background(text)
    result = check_background(parsed)
    if result["blocking"]:
        for f in result["blocking"]:
            print(f)
        return 1

    built = build_entries(parsed, body_sha(text))

    refusals = []
    for b in built:
        p = root / b["rel"]
        if p.is_file():
            f = target_refusal(p.read_text(encoding="utf-8"), b["rel"])
            if f:
                refusals.append(f)
    if refusals:
        for f in refusals:
            print(f)
        return 1

    for b in built:
        p = root / b["rel"]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(b["text"], encoding="utf-8")

    bg = root / BACKGROUND_DIR
    existing = ([f"{BACKGROUND_DIR}/{p.name}" for p in sorted(bg.glob("*.md"))]
                if bg.is_dir() else [])
    notes = orphan_notes(existing, [b["rel"] for b in built])

    print(f"background_cut: wrote {len(built)} files from {src}")
    if notes:
        print("\nAdvisory — nothing blocks on these:")
        for n in notes:
            print(f"  {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
