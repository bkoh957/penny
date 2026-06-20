"""Shared writer for Penny review verdict files.

A verdict is a markdown file in a chapter's ``ch-NN.reviews/`` directory. The
envelope is shared by deterministic checkers (Phase 2a) and inspector sub-agents
(Phase 2b):

    ---
    producer: <script or agent name>
    kind: deterministic-checker | inspector
    target: book-NN/ch-MM
    schema: penny-verdict/1
    score: <1-5>            # OPTIONAL — inspectors only; omitted for checkers
    ---
    BLOCKING: <one line per blocking issue>     # counted by the status line + gate
    - <one line per non-blocking note / evidence summary>
    metrics: <json>
    evidence:
      - <json>

Blocking issues are ``^BLOCKING:`` lines (the Phase 1 convention the status line
and gate count). ``penny_meta.parse_frontmatter`` reads the frontmatter.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# The blocker-line convention lives HERE (the verdict-format module owns what a
# blocker line looks like). Mirrored verbatim by penny-statusline.sh's
# `grep '^BLOCKING:'`; agreement is pinned by a cross-consistency test.
BLOCKING_RE = re.compile(r"^BLOCKING:", re.MULTILINE)

SCHEMA = "penny-verdict/1"


def write_verdict(
    *,
    out_dir,
    producer: str,
    kind: str,
    target: str,
    name: str,
    blocking: list[str],
    notes: list[str],
    metrics: dict,
    evidence: list[dict],
    score: int | None = None,
) -> Path:
    """Write ``<out_dir>/<name>.md`` and return its Path. Creates out_dir if needed."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.md"

    lines: list[str] = ["---", f"producer: {producer}", f"kind: {kind}",
                        f"target: {target}", f"schema: {SCHEMA}"]
    if score is not None:
        lines.append(f"score: {score}")
    lines.append("---")
    lines.append("")

    for issue in blocking:
        lines.append(f"BLOCKING: {issue}")
    for note in notes:
        lines.append(f"- {note}")
    if metrics:
        lines.append(f"metrics: {json.dumps(metrics, sort_keys=True)}")
    if evidence:
        lines.append("evidence:")
        for item in evidence:
            lines.append(f"  - {json.dumps(item, sort_keys=True)}")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def count_blocking(reviews_dir) -> int:
    """Count ``^BLOCKING:`` lines across every file in ``reviews_dir`` (recursive).

    Mirrors ``grep -rh '^BLOCKING:'``: reads all files, anchored + case-sensitive.
    Returns 0 if the directory is absent.
    """
    root = Path(reviews_dir)
    if not root.is_dir():
        return 0
    total = 0
    for path in sorted(root.rglob("*")):
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="ignore")
            total += len(BLOCKING_RE.findall(text))
    return total
