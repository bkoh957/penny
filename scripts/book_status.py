"""Where a book actually is (spec 2026-08-01).

READ-ONLY, absolutely: this module creates, edits and deletes nothing — not
even a reports directory. It reports on state other commands already wrote.

Two statuses per row, because "done" is two questions. RUN is "the artefact
exists". PASSED is "the proof exists AND is still current". Collapsing them
into one tick reproduces the .penny/current-stage failure this replaces: a
label someone typed, which has read OUTLINE-REVIEWED for days while the book
moved on.
"""
from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import penny_paths
from scripts.penny_meta import parse_frontmatter


@dataclass
class Cell:
    """One status column. kind is 'bool' | 'count' | 'na' | 'unknown'.

    'na' means the step has nothing to pass — running it IS the outcome. It is
    never a failure and never a pending state.
    'unknown' means the check could not run. It is never rendered as pass or
    fail, because a report that guesses is worse than one that admits.
    """
    kind: str
    ok: bool = False
    done: int = 0
    total: int = 0


def yes() -> Cell:
    return Cell("bool", ok=True)


def no() -> Cell:
    return Cell("bool", ok=False)


def count(done: int, total: int) -> Cell:
    return Cell("count", done=done, total=total, ok=(total > 0 and done == total))


def na() -> Cell:
    return Cell("na")


def unknown() -> Cell:
    return Cell("unknown")


@dataclass
class Row:
    id: str
    label: str
    run: Cell
    passed: Cell
    command: str
    artefact: str
    reason: str = ""


def _root(repo_root):
    return Path(repo_root) if repo_root is not None else penny_paths.series_root()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _outline_path(book: str, root) -> Path:
    return Path(penny_paths.input_path(f"book-{book}/outline.md", root=root))


def _outline_row(book: str, root) -> Row:
    p = _outline_path(book, root)
    rel = f"input/book-{book}/outline.md"
    common = dict(id="outline", label="outline",
                  command=f"/plot-book {book}", artefact=rel)
    if not p.is_file():
        return Row(run=no(), passed=no(), reason="no outline yet", **common)
    try:
        from scripts.outline_check import check_outline
        blocking = check_outline(p, repo_root=root)["blocking"]
        if blocking:
            return Row(run=yes(), passed=no(), reason=blocking[0], **common)
        return Row(run=yes(), passed=yes(), **common)
    except Exception as exc:                      # never a traceback
        return Row(run=yes(), passed=unknown(),
                   reason=f"outline_check could not run: {exc}", **common)


_DIAGNOSTIC_VIEWS = ("outline-glance.md", "spine-worksheet.md", "spine-map.md")


def _diagnostics_row(book: str, root) -> Row:
    d = Path(penny_paths.output_path(f"book-{book}/reports", root=root))
    present = [n for n in _DIAGNOSTIC_VIEWS if (d / n).is_file()]
    strands = d / "strands"
    n_strands = len(list(strands.glob("*.md"))) if strands.is_dir() else 0
    if n_strands:
        present.append(f"{n_strands} strands")
    return Row(id="diagnostics", label="diagnostics",
               run=yes() if present else no(), passed=na(),
               command=f"/diagnose-outline {book}",
               artefact=f"output/book-{book}/reports/",
               reason=", ".join(present) if present else "not run")


def _feedback_row(book: str, root) -> Row:
    p = Path(penny_paths.output_path(
        f"book-{book}/reports/outline-feedback.yaml", root=root))
    common = dict(id="feedback", label="outline feedback",
                  command=f"/review-outline {book}",
                  artefact=f"output/book-{book}/reports/outline-feedback.yaml")
    if not p.is_file():
        return Row(run=no(), passed=no(), reason="no feedback ledger", **common)
    try:
        import yaml
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"ledger is {type(data).__name__}, not a mapping")
        items = data.get("items") or []
        if not isinstance(items, list):
            raise ValueError("items: is not a list")
        open_n = sum(1 for i in items
                     if isinstance(i, dict) and i.get("state") == "open")
    except Exception as exc:
        return Row(run=yes(), passed=unknown(),
                   reason=f"ledger could not be read: {exc}", **common)
    if open_n:
        return Row(run=yes(), passed=no(),
                   reason=f"{open_n} open of {len(items)}", **common)
    return Row(run=yes(), passed=yes(),
               reason=f"{len(items)} items, none open", **common)


def _lock_row(book: str, root) -> Row:
    p = Path(penny_paths.penny_path(f"locks/book-{book}.mystery.lock", root=root))
    common = dict(id="lock", label="mystery lock",
                  command=f"preflight lock-mystery {book}",
                  artefact=f".penny/locks/book-{book}.mystery.lock")
    if not p.is_file():
        return Row(run=no(), passed=no(), reason="not locked", **common)
    fm = parse_frontmatter_or_lines(p.read_text(encoding="utf-8"))
    recorded = fm.get("outline_sha256")
    source = fm.get("outline_source")
    if not recorded or not source:
        # Legacy lock (pre-7cb2f4e) — it records THAT it validated, not WHAT.
        # A certificate must not claim coverage it does not have, so the only
        # honest answer is that the question cannot be answered.
        return Row(run=yes(), passed=unknown(),
                   reason="staleness unknown — lock records no fingerprint; "
                          "re-mint to fix", **common)
    src = Path(_root(root)) / source
    if not src.is_file():
        return Row(run=yes(), passed=unknown(),
                   reason=f"staleness unknown — {source} no longer exists", **common)
    if _sha(src) == recorded:
        return Row(run=yes(), passed=yes(), reason=f"matches {source}", **common)
    return Row(run=yes(), passed=no(),
               reason=f"STALE — {source} has changed since the lock", **common)


def parse_frontmatter_or_lines(text: str) -> dict:
    """The lock is `key: value` lines with NO `---` fences, so parse_frontmatter
    does not apply. Kept tiny and local rather than loosening penny_meta, whose
    strictness other callers depend on."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line and not line.startswith(" "):
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip()
    return out


def book_rows(book: str, repo_root=None) -> list[Row]:
    root = _root(repo_root)
    book = str(book).zfill(2)
    return [_outline_row(book, root), _diagnostics_row(book, root),
            _feedback_row(book, root), _lock_row(book, root)]
