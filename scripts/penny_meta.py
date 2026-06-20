"""Dependency-free metadata parsing for Penny config and ledger files.

Supports only the small subset of YAML that Penny uses: a ``key: value`` line
where the value is a bare scalar or an inline list ``[a, b, c]``. This avoids a
PyYAML dependency in the deterministic ``/scripts`` layer.
"""
from __future__ import annotations

import re
from pathlib import Path


def _coerce(value: str) -> "str | list[str]":
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [item.strip() for item in inner.split(",") if item.strip()]
    return value


def _strip_inline_comment(line: str) -> str:
    """Strip a trailing ``# comment`` only when the ``#`` is outside any inline
    list and is preceded by whitespace. This protects values that legitimately
    contain ``#`` (e.g. ``https://x#anchor``) and ``#`` inside ``[...]`` lists."""
    in_brackets = False
    for i, ch in enumerate(line):
        if ch == "[":
            in_brackets = True
        elif ch == "]":
            in_brackets = False
        elif ch == "#" and not in_brackets and i > 0 and line[i - 1].isspace():
            return line[:i]
    return line


def _parse_kv_lines(lines: list[str]) -> dict:
    out: dict = {}
    for raw in lines:
        line = raw.rstrip("\n")
        full = line.strip()
        if not full or full.startswith("#"):
            continue
        line = _strip_inline_comment(line).strip()
        if not line or ":" not in line:
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


_CANON_META_RE = re.compile(r"<!--\s*canon-meta:\s*\{(.*?)\}\s*-->", re.DOTALL)


def parse_canon_meta(text: str) -> dict:
    """Read the first ``<!-- canon-meta: {k: v, ...} -->`` header. Returns {} if
    absent. Supports flat scalar pairs (sufficient for fluency_stage); nested maps
    are deferred to the demotion machinery (Phase 8)."""
    m = _CANON_META_RE.search(text)
    if not m:
        return {}
    inner = m.group(1)
    # Split top-level commas (no nesting expected at this stage) into k: v lines.
    return _parse_kv_lines([part for part in inner.split(",")])
