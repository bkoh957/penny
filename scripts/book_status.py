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
from dataclasses import dataclass
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
    try:
        lock_text = p.read_text(encoding="utf-8")
    except Exception as exc:
        return Row(run=yes(), passed=unknown(),
                   reason=f"lock could not be read: {exc}", **common)
    fm = parse_frontmatter_or_lines(lock_text)
    recorded = fm.get("outline_sha256")
    source = fm.get("outline_source")
    if not recorded or not source:
        # Legacy lock (pre-7cb2f4e) — it records THAT it validated, not WHAT.
        # A certificate must not claim coverage it does not have, so the only
        # honest answer is that the question cannot be answered.
        return Row(run=yes(), passed=unknown(),
                   reason="staleness unknown — lock records no fingerprint; "
                          "re-mint to fix", **common)
    root_path = _root(root).resolve()
    src = (root_path / source).resolve()
    # Ensure the resolved source stays within the series root
    try:
        src.relative_to(root_path)
    except ValueError:
        return Row(run=yes(), passed=unknown(),
                   reason=f"staleness unknown — {source} is outside the series root",
                   **common)
    if not src.is_file():
        return Row(run=yes(), passed=unknown(),
                   reason=f"staleness unknown — {source} no longer exists", **common)
    try:
        if _sha(src) == recorded:
            return Row(run=yes(), passed=yes(), reason=f"matches {source}", **common)
    except Exception as exc:
        return Row(run=yes(), passed=unknown(),
                   reason=f"staleness unknown — {source} could not be read: {exc}",
                   **common)
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


_UNKNOWN_TOTAL = "total_chapters not declared in the outline frontmatter"


def total_chapters(book: str, repo_root=None) -> int | None:
    """The denominator for every count, taken from the outline's frontmatter.

    Deliberately NOT inferred from whichever directory happens to be fullest: a
    count with a guessed denominator reads as fact and is a guess.
    """
    root = _root(repo_root)
    p = _outline_path(str(book).zfill(2), root)
    if not p.is_file():
        return None
    raw = parse_frontmatter(p.read_text(encoding="utf-8")).get("total_chapters")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _glob_chapters(d: Path, pattern: str) -> set[str]:
    """Zero-padded chapter numbers matching e.g. 'ch-*.draft.md'."""
    if not d.is_dir():
        return set()
    out = set()
    for p in d.glob(pattern):
        if not p.is_file():          # Filter out directories
            continue
        stem = p.name.split(".")[0]           # 'ch-07'
        if stem.startswith("ch-") and stem[3:].isdigit():
            out.add(stem[3:].zfill(2))
    return out


def chapter_rows(book: str, repo_root=None) -> list[Row]:
    root = _root(repo_root)
    book = str(book).zfill(2)
    total = total_chapters(book, root)
    chapters = Path(penny_paths.output_path(f"book-{book}/chapters", root=root))
    packets_dir = Path(penny_paths.input_path(f"book-{book}/packets", root=root))
    maps_dir = Path(penny_paths.input_path(f"book-{book}/maps", root=root))
    locks = Path(penny_paths.penny_path("locks", root=root))

    def c(done: int) -> Cell:
        return unknown() if total is None else count(done, total)

    reason = _UNKNOWN_TOTAL if total is None else ""

    packets = _glob_chapters(packets_dir, "ch-*.md")
    try:
        from scripts.packet_assemble import stale_packets
        stale = stale_packets(book, root)
        fresh = len(packets - stale)
        packet_passed = c(fresh)
        packet_reason = reason or (f"{len(stale)} stale" if stale else "")
    except Exception as exc:
        packet_passed, packet_reason = unknown(), f"staleness could not be read: {exc}"

    maps = _glob_chapters(maps_dir, "ch-*.md")
    drafts = _glob_chapters(chapters, "ch-*.draft.md")
    finals = _glob_chapters(chapters, "ch-*.final.md")

    passing_gates = 0
    gates_reason = ""
    for num in _glob_chapters(chapters, "ch-*.gate.md"):
        try:
            body = (chapters / f"ch-{num}.gate.md").read_text(encoding="utf-8")
        except Exception as exc:
            gates_reason = f"ch-{num} gate unreadable"
            passing_gates = None
            break
        if any(l.strip() == "gate: PASS" for l in body.splitlines()):
            passing_gates += 1

    gates_passed = unknown() if passing_gates is None else c(passing_gates)

    cleared = 0
    cleared_reason = ""
    for num in drafts:
        cert = locks / f"book-{book}.ch-{num}.dev-clear"
        draft = chapters / f"ch-{num}.draft.md"
        if not cert.is_file():
            continue
        try:
            recorded = parse_frontmatter(
                cert.read_text(encoding="utf-8")).get("cleared_draft_sha256")
        except Exception as exc:
            cleared_reason = f"ch-{num} dev-clear unreadable"
            cleared = None
            break
        if recorded and recorded == _sha(draft):
            cleared += 1

    cleared_passed = unknown() if cleared is None else c(cleared)

    return [
        Row("packets", "packets", c(len(packets)), packet_passed,
            f"/map-chapter {book} MM", f"input/book-{book}/packets/", packet_reason),
        Row("maps", "maps", c(len(maps)), na(),
            f"/map-chapter {book} MM", f"input/book-{book}/maps/", reason),
        Row("drafts", "drafts", c(len(drafts)), na(),
            f"/draft-chapter {book} MM",
            f"output/book-{book}/chapters/ch-MM.draft.md", reason),
        Row("gates", "gates", na(), gates_passed,
            f"/review-chapter {book} MM",
            f"output/book-{book}/chapters/ch-MM.gate.md", gates_reason or reason),
        Row("dev-cleared", "dev cleared", na(), cleared_passed,
            f"preflight clear-dev {book} MM",
            f".penny/locks/book-{book}.ch-MM.dev-clear", cleared_reason or reason),
        Row("finals", "finals", c(len(finals)), na(),
            f"/finalize-chapter {book} MM",
            f"output/book-{book}/chapters/ch-MM.final.md", reason),
    ]


def tail_rows(book: str, repo_root=None) -> list[Row]:
    root = _root(repo_root)
    book = str(book).zfill(2)
    ms = Path(penny_paths.output_path(
        f"book-{book}/book-{book}.manuscript.md", root=root))
    approved = Path(penny_paths.penny_path(f"locks/book-{book}.approved", root=root))
    beta_dir = Path(penny_paths.output_path(f"book-{book}/beta-reports", root=root))
    n_beta = len([p for p in beta_dir.glob("*.converged.md") if p.is_file()]) if beta_dir.is_dir() else 0
    return [
        Row("manuscript", "manuscript",
            yes() if ms.is_file() else no(),
            yes() if approved.is_file() else no(),
            f"/assemble-book {book}",
            f"output/book-{book}/book-{book}.manuscript.md",
            "approved" if approved.is_file() else
            ("assembled, not approved" if ms.is_file() else "not assembled")),
        Row("beta", "beta read", yes() if n_beta else no(), na(),
            f"/beta-read output/book-{book}/book-{book}.manuscript.md",
            f"output/book-{book}/beta-reports/",
            f"{n_beta} personas" if n_beta else "not run"),
    ]


def all_rows(book: str, repo_root=None) -> list[Row]:
    return (book_rows(book, repo_root) + chapter_rows(book, repo_root)
            + tail_rows(book, repo_root))


def _is_run(row: Row) -> bool:
    c = row.run
    if c.kind == "na":
        # When RUN is na(), judge progress by the PASSED cell.
        # A 0/28 PASSED count is not evidence that anything ran.
        p = row.passed
        return p.done > 0 if p.kind == "count" else p.ok
    if c.kind == "count":
        return c.done > 0
    return c.ok


def _is_passed(row: Row) -> bool:
    c = row.passed
    if c.kind == "na":
        # When passed is na(), judge only on the run cell. If run is also na(),
        # there is nothing to pass and nothing to judge — the outcome IS running it.
        if row.run.kind == "na":
            return True
        # A count row with na() passed is only passed when all are done.
        return row.run.ok
    if c.kind == "count":
        return c.total > 0 and c.done == c.total
    return c.ok


def unknown_rows(rows: list[Row]) -> list[Row]:
    return [r for r in rows if r.run.kind == "unknown" or r.passed.kind == "unknown"]


def next_action(rows: list[Row]) -> "Row | None":
    """First row that RAN but did not PASS; else the first not yet run.

    Fixing a thing that ran badly outranks starting the next thing — which is
    the whole difference from `plot_stage.py status`, whose per-stage view sends
    book 01 back to rewrite its premise. Rows whose checks could not run are
    skipped: guessing from a fact the engine admits it lacks is the failure
    this replaces.
    """
    skip = {id(r) for r in unknown_rows(rows)}
    candidates = [r for r in rows if id(r) not in skip]
    for r in candidates:
        if _is_run(r) and not _is_passed(r):
            return r
    for r in candidates:
        if not _is_run(r):
            return r
    return None
