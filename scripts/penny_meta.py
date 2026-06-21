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


_SECTION_RE = re.compile(r"^##\s+(.*?)\s*$", re.MULTILINE)


def _split_top_level(inner: str) -> list[str]:
    """Split on commas that are not inside an inline ``[...]`` list."""
    parts, depth, buf = [], 0, []
    for ch in inner:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return parts


def parse_canon_sections(text: str) -> list[dict]:
    """Return one dict per ``##`` section that carries a ``canon-meta`` header.

    Each dict has ``heading`` (the ## title) plus the header's parsed fields
    (``id``, ``refs`` as a list, etc.). The file-level header that precedes the
    first ``##`` is excluded; sections without a canon-meta header are skipped.
    """
    out: list[dict] = []
    headings = list(_SECTION_RE.finditer(text))
    for i, h in enumerate(headings):
        start = h.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        m = _CANON_META_RE.search(text[start:end])
        if not m:
            continue
        meta = _parse_kv_lines(_split_top_level(m.group(1)))
        meta.setdefault("refs", [])
        meta["heading"] = h.group(1)
        out.append(meta)
    return out


def _fmt_meta_value(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _set_inline_field(inner: str, field: str, value: str) -> str:
    """Update or insert ``field: value`` inside a canon-meta inner string,
    normalizing to a single space. Other fields are preserved byte-for-byte."""
    pat = re.compile(rf"\b{re.escape(field)}\s*:\s*[^,}}]*")
    if pat.search(inner):
        return pat.sub(f"{field}: {value}", inner, count=1)
    sep = ", " if inner.strip() else ""
    return inner.rstrip() + f"{sep}{field}: {value}"


def write_canon_section_field(text: str, section_id: str, field: str, value) -> str:
    """Set the canon-meta ``field`` of the ``##`` section whose id is
    ``section_id``. Preserves body bytes. Idempotent on repeated same-value
    stamps. Raises KeyError if no section has that id."""
    val = _fmt_meta_value(value)
    headings = list(_SECTION_RE.finditer(text))
    for i, h in enumerate(headings):
        start = h.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        m = _CANON_META_RE.search(text[start:end])
        if not m:
            continue
        inner = m.group(1)
        if _parse_kv_lines(_split_top_level(inner)).get("id") != section_id:
            continue
        new_inner = _set_inline_field(inner, field, val)
        abs_start, abs_end = start + m.start(1), start + m.end(1)
        return text[:abs_start] + new_inner + text[abs_end:]
    raise KeyError(f"no canon-core section with id {section_id!r}")


def write_frontmatter_field(text: str, field: str, value) -> str:
    """Set ``field: value`` in the leading ``---`` frontmatter block, preserving
    the body. Inserts the field at the block end if absent. Raises ValueError if
    there is no frontmatter block."""
    val = _fmt_meta_value(value)
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError("no frontmatter block")
    close = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if close is None:
        raise ValueError("unterminated frontmatter block")
    pat = re.compile(rf"^\s*{re.escape(field)}\s*:.*$")
    for i in range(1, close):
        if pat.match(lines[i].rstrip("\n")):
            nl = "\n" if lines[i].endswith("\n") else ""
            lines[i] = f"{field}: {val}{nl}"
            return "".join(lines)
    lines.insert(close, f"{field}: {val}\n")
    return "".join(lines)


def strip_frontmatter(text: str) -> str:
    """Return the body after a leading ``---`` frontmatter block, with leading
    blank lines removed. If there is no frontmatter block, return ``text`` as-is."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "".join(lines[i + 1:]).lstrip("\n")
    return text
