"""Dependency-free metadata parsing for Penny config and ledger files.

Supports only the small subset of YAML that Penny uses: a ``key: value`` line
where the value is a bare scalar or an inline list ``[a, b, c]``. This avoids a
PyYAML dependency in the deterministic ``/scripts`` layer.
"""
from __future__ import annotations

from pathlib import Path


def _coerce(value: str):
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [item.strip() for item in inner.split(",") if item.strip()]
    return value


def _parse_kv_lines(lines: list[str]) -> dict:
    out: dict = {}
    for raw in lines:
        line = raw.rstrip("\n")
        # Strip trailing comments that are not inside a value.
        if "#" in line and not line.strip().startswith("#"):
            # Only strip a comment that follows whitespace (so "[a, b]  # x" works).
            hash_idx = line.find("#")
            line = line[:hash_idx]
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        out[key.strip()] = _coerce(value)
    return out


def parse_frontmatter(text: str) -> dict:
    """Parse a leading ``---`` delimited frontmatter block. Returns {} if absent."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    body: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        body.append(line)
    return _parse_kv_lines(body)


def parse_yaml_blocks(text: str) -> dict:
    """Merge all fenced ```yaml blocks in a markdown document into one dict."""
    out: dict = {}
    in_block = False
    block: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not in_block and stripped.startswith("```") and "yaml" in stripped:
            in_block = True
            block = []
            continue
        if in_block and stripped.startswith("```"):
            in_block = False
            out.update(_parse_kv_lines(block))
            continue
        if in_block:
            block.append(line)
    return out


def load(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")
