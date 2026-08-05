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
import re
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
    # The action that advances this row FROM ITS CURRENT (ran-but-failed)
    # state, when that differs from `command` (which creates the artefact).
    # Empty by convention for every row except the two where re-running
    # `command` is actively harmful (feedback: grows the backlog; manuscript:
    # re-runs the cross-model final read). `render` prefers this when set.
    fix_command: str = ""


def _root(repo_root):
    return Path(repo_root) if repo_root is not None else penny_paths.series_root()


def _sha(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"_sha: not a file: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rel(p: Path, root: Path) -> str:
    """Render an artefact path relative to the series root for display, so the
    drill-down reads like the book-level rows rather than wrapping a deep
    absolute path across the terminal. Falls back to the absolute path if `p`
    isn't under `root` — should not happen for the paths built here, but a
    display fallback is cheaper than a crash."""
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)


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
    n_strands = (len([p for p in strands.glob("*.md") if p.is_file()])
                 if strands.is_dir() else 0)
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
    rel = f"output/book-{book}/reports/outline-feedback.yaml"
    common = dict(id="feedback", label="outline feedback",
                  command=f"/review-outline {book}", artefact=rel)
    if not p.is_file():
        return Row(run=no(), passed=no(), reason="no feedback ledger", **common)

    # Detect a genuine parse failure OURSELVES, before handing the file to
    # outline_feedback.load_ledger(): that accessor returns an EMPTY ledger
    # (stamp "") for ANY unreadable file — bad indent, a YAML list instead of
    # a mapping, whatever — which downstream would misread as "reviewed, then
    # the outline changed" (false: the outline never changed) and would send
    # the showrunner to /review-outline, which is destructive here: append ->
    # load_ledger (blank on parse failure) -> write_ledger silently discards
    # every hand-set `state:` because of the one bad byte. Function-local
    # import: PyYAML is genuinely nested human-edited data (dependency-split
    # rule) — never module-level in this file.
    import yaml
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    except Exception as exc:
        return Row(run=yes(), passed=unknown(),
                   reason=f"ledger could not be parsed: {exc}", **common)
    if not isinstance(raw, dict):
        return Row(run=yes(), passed=unknown(),
                   reason="ledger does not parse to a mapping "
                          f"(got {type(raw).__name__})", **common)

    try:
        # Reuse the ledger's own accessors rather than reimplementing the read
        # (I2) for everything the parse-failure check above cannot express.
        from scripts import outline_feedback
        ledger = outline_feedback.load_ledger(book, repo_root=root)
        items = ledger.get("items") or []
        if not isinstance(items, list):
            raise ValueError("items: is not a list")
        reviewed_sha = ledger.get("reviewed_outline_sha256", "")
        if reviewed_sha is None:
            reviewed_sha = ""
        cur_sha = outline_feedback.sha256_of(
            outline_feedback.outline_src_path(book, repo_root=root))
        open_n = len(outline_feedback.open_items(ledger))
    except Exception as exc:
        return Row(run=yes(), passed=unknown(),
                   reason=f"ledger could not be read: {exc}", **common)

    # A NON-EMPTY stamp that no longer matches the outline on disk is stale,
    # regardless of open-item count (I2, still shipped below). An EMPTY stamp
    # is not a mismatch to be read as staleness — it means no review panel has
    # read outline.md at all, which is the normal /plot-book shape: fan-audit
    # items append with --source and deliberately leave the stamp blank
    # (commands/plot-book.md:212-218), because outline.md may not even exist
    # yet when they're written. Falsely calling that "STALE" makes the
    # feedback row's open-item backlog and fix_command vanish the moment
    # /expand-outline later writes outline.md.
    # NB: emptiness is tested against "" explicitly, not by truthiness — an
    # unquoted all-digit sha (e.g. a run of zeros) parses through YAML as the
    # int 0, which is falsy but is very much a present, non-empty stamp.
    never_reviewed = reviewed_sha == ""
    if not never_reviewed and cur_sha != reviewed_sha:
        return Row(run=yes(), passed=no(),
                   reason="STALE — outline changed since its last review",
                   **common)

    never_reviewed = (" (no panel review has run yet — fan-audit items only)"
                       if never_reviewed else "")
    if open_n:
        return Row(run=yes(), passed=no(),
                   reason=f"{open_n} open of {len(items)}{never_reviewed}",
                   fix_command=f"hand-edit state: in {rel}", **common)
    return Row(run=yes(), passed=yes(),
               reason=f"{len(items)} items, none open{never_reviewed}",
               **common)


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
    try:
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
    except Exception as exc:                      # never a traceback — e.g. a NUL
                                                    # byte in outline_source raises
                                                    # ValueError out of Path.resolve()
        return Row(run=yes(), passed=unknown(),
                   reason=f"staleness unknown — {source} could not be resolved: {exc}",
                   **common)
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


def _story_path(book: str, root) -> Path:
    return Path(penny_paths.input_path(f"book-{book}/story.md", root=root))


def _cut_plan_path(book: str, root) -> Path:
    return Path(penny_paths.input_path(f"book-{book}/cut-plan.md", root=root))


def _story_row(book: str, root) -> Row:
    """Findings over story.md — the layer the author actually edits.

    Reuses `story_cut.check_story`, the same function the cut itself refuses
    on, so this row can never disagree with what the cut will do. Anything it
    cannot resolve (genre, ledger) is `unknown`, never a fail: without the job
    list every #job reads as unknown-job, and a table that guesses is worse
    than one that admits.

    Function-local import throughout: story_cut pulls in PyYAML at module
    level, and this file keeps PyYAML off its import surface (dependency-split
    rule).
    """
    rel = f"input/book-{book}/story.md"
    common = dict(id="story", label="story",
                  command=f"/plot-book {book}", artefact=rel)
    from scripts import story_cut

    try:
        job_ids, _ = story_cut._job_ids_and_titles(root=root)
    except Exception as exc:
        return Row(run=yes(), passed=unknown(),
                   reason=f"the genre's job list could not be read: {exc}", **common)
    if not job_ids:
        return Row(run=yes(), passed=unknown(),
                   reason="the active genre's macro-structure could not be "
                          "resolved — every #job would read as unknown-job",
                   **common)
    try:
        clues, _data, ledger_p = story_cut._ledger(root, book)
    except Exception as exc:
        return Row(run=yes(), passed=unknown(),
                   reason=f"the whodunit ledger could not be read: {exc}", **common)
    if not ledger_p.is_file():
        return Row(run=yes(), passed=unknown(),
                   reason="the whodunit ledger is missing — every !clue would "
                          "read as unknown-clue", **common)

    text = _story_path(book, root).read_text(encoding="utf-8")
    result = story_cut.check_story(text, "", job_ids, list(clues))
    # beats-without-chapter is the cut plan's question, not the story's. It
    # fires for EVERY beat when the plan is absent, which is the normal state
    # of a story being written — counting it here would make every live book
    # look broken.
    findings = [f for f in result["blocking"]
                if not f.startswith("beats-without-chapter")]
    if findings:
        n = len(findings)
        return Row(run=yes(), passed=no(),
                   reason=f"{n} finding{'s' if n != 1 else ''} — fix before cutting",
                   fix_command=f"fix the findings in {rel}", **common)
    return Row(run=yes(), passed=yes(),
               reason=f"{len(story_cut.parse_story(text))} beats, no findings",
               **common)


def _cut_plan_row(book: str, root) -> Row:
    """Whether the chapter-cutter's grouping exists and covers every beat."""
    p = _cut_plan_path(book, root)
    rel = f"input/book-{book}/cut-plan.md"
    common = dict(id="cut-plan", label="cut plan",
                  command=f"/plot-book {book}", artefact=rel)
    if not p.is_file():
        return Row(run=no(), passed=no(),
                   reason="no cut plan — the chapter-cutter has not proposed one",
                   **common)
    from scripts import story_cut
    plan_text = p.read_text(encoding="utf-8")
    story_text = _story_path(book, root).read_text(encoding="utf-8")
    # Empty job/clue lists on purpose: this row asks only whether every beat
    # landed in a chapter, and beats-without-chapter needs neither. Keeping it
    # independent of the genre means a book with an unresolvable genre still
    # gets a truthful cut-plan row.
    result = story_cut.check_story(story_text, plan_text, [], [])
    orphans = [f for f in result["blocking"]
               if f.startswith("beats-without-chapter")]
    if orphans:
        return Row(run=yes(), passed=no(), reason=orphans[0],
                   fix_command=f"every beat must land in a chapter — edit {rel}",
                   **common)
    return Row(run=yes(), passed=yes(),
               reason=f"{len(story_cut.parse_cut_plan(plan_text))} chapters",
               **common)


def _recut_cost(book: str, root) -> str:
    """What re-cutting costs, named rather than commanded.

    This row deliberately hands over no runnable command. Re-cutting rewrites
    `plant_chapter:` in the whodunit ledger, so it needs the ledger UNSEALED,
    and it restales every packet built from the current outline. A
    copy-pasteable command would hide both prerequisites behind one word, and
    "the status table told me to" is not a reason to delete a certificate.
    """
    costs = []
    lock = Path(penny_paths.penny_path(
        f"locks/book-{book}.mystery.lock", root=root))
    if lock.is_file():
        costs.append("the mystery lock must be deleted first "
                     "(the cut rewrites the ledger)")
    n = len(_glob_chapters(
        Path(penny_paths.input_path(f"book-{book}/packets", root=root)), "ch-*.md"))
    if n:
        costs.append(f"{n} packet{'s' if n != 1 else ''} will go stale")
    tail = ("; " + "; ".join(costs)) if costs else ""
    return f"re-cut needed — story.md has moved past outline.md{tail}"


def _cut_row(book: str, root) -> Row:
    """Whether outline.md is still the output of the story on disk.

    The outline already records this: `story_cut.stamp_outline` writes
    `built_from_story: <sha of story.md>` into its frontmatter. Nothing read it
    until now, which is why a book being edited upstream looked green.
    """
    outline_p = _outline_path(book, root)
    rel = f"input/book-{book}/outline.md"
    common = dict(id="cut", label="cut", command=f"/plot-book {book}",
                  artefact=rel)
    if not outline_p.is_file():
        return Row(run=no(), passed=no(), reason="not cut yet", **common)

    stamped = parse_frontmatter(
        outline_p.read_text(encoding="utf-8")).get("built_from_story")
    if not stamped:
        # A KNOWN fact, not an unknown: this outline is not the story's output.
        # It is the legacy/hand-authored shape (book 01 mid-migration), and
        # deleting it is what makes the first cut legal — the showrunner's
        # explicit act, never an engine override.
        return Row(run=yes(), passed=no(),
                   reason="outline.md carries no built_from_story — it was not "
                          "produced by the cut",
                   fix_command="this outline predates the cut; deleting it is "
                               "what makes the first cut legal",
                   **common)

    current = hashlib.sha256(
        _story_path(book, root).read_text(encoding="utf-8").encode("utf-8")
    ).hexdigest()
    if str(stamped) == current:
        return Row(run=yes(), passed=yes(),
                   reason=f"matches input/book-{book}/story.md", **common)
    return Row(run=yes(), passed=no(),
               reason="OUT OF DATE — story.md changed since the cut",
               fix_command=_recut_cost(book, root), **common)


def book_rows(book: str, repo_root=None) -> list[Row]:
    root = _root(repo_root)
    book = str(book).zfill(2)
    # The source layer sits ABOVE the outline, because since spec 2026-08-03
    # the outline is a build product: story.md is what the author edits. Row
    # order is the whole mechanism — next_action prefers the first
    # ran-but-failed row, so a book being edited upstream can no longer be
    # advised from its own output.
    #
    # Presence on disk is the switch, not a flag: a book with no story.md is
    # not on the source layer and rows about it would be noise. This mirrors
    # the cut's own rule (recut_refusal runs only `if outline_p.is_file()`).
    source_layer = []
    if _story_path(book, root).is_file():
        source_layer = [_story_row(book, root), _cut_plan_row(book, root),
                        _cut_row(book, root)]
    return source_layer + [_outline_row(book, root), _diagnostics_row(book, root),
                           _feedback_row(book, root), _lock_row(book, root)]


_UNKNOWN_TOTAL = "total_chapters not declared in the outline frontmatter"


def _total_chapters_with_reason(book: str, root) -> tuple[int | None, str]:
    """The denominator for every count, plus WHY it's missing when it is.

    A read failure and a missing key are different problems with different
    fixes, so they must not share a reason: telling a writer to add a key that
    is already there (because a bad byte elsewhere made the file unreadable)
    sends them chasing the wrong thing. `reason` is '' exactly when `total` is
    known.
    """
    p = _outline_path(book, root)
    if not p.is_file():
        return None, "no outline yet"
    try:
        text = p.read_text(encoding="utf-8")
    except Exception as exc:                      # never a traceback
        return None, f"outline could not be read: {exc}"
    raw = parse_frontmatter(text).get("total_chapters")
    try:
        return int(raw), ""
    except (TypeError, ValueError):
        return None, _UNKNOWN_TOTAL


def total_chapters(book: str, repo_root=None) -> int | None:
    """The denominator for every count, taken from the outline's frontmatter.

    Deliberately NOT inferred from whichever directory happens to be fullest: a
    count with a guessed denominator reads as fact and is a guess. Thin wrapper
    over `_total_chapters_with_reason`, kept for existing callers/tests that
    only want the int.
    """
    root = _root(repo_root)
    total, _ = _total_chapters_with_reason(str(book).zfill(2), root)
    return total


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
    total, total_reason = _total_chapters_with_reason(book, root)
    chapters = Path(penny_paths.output_path(f"book-{book}/chapters", root=root))
    packets_dir = Path(penny_paths.input_path(f"book-{book}/packets", root=root))
    maps_dir = Path(penny_paths.input_path(f"book-{book}/maps", root=root))
    locks = Path(penny_paths.penny_path("locks", root=root))

    def c(done: int) -> Cell:
        return unknown() if total is None else count(done, total)

    reason = total_reason if total is None else ""

    packets = _glob_chapters(packets_dir, "ch-*.md")
    try:
        from scripts.packet_assemble import stale_packets
        stale = stale_packets(book, root)
        fresh = len(packets - stale)
        packet_passed = c(fresh)
        packet_reason = reason or (f"{len(stale)} stale" if stale else "")
    except Exception as exc:
        # If total_chapters is already unknown, that is the more useful thing
        # to tell the showrunner — don't let this exception's message bury it.
        packet_passed = unknown()
        packet_reason = reason or f"staleness could not be read: {exc}"

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
            if recorded and recorded == _sha(draft):
                cleared += 1
        except Exception as exc:
            cleared_reason = f"ch-{num} dev-clear unreadable"
            cleared = None
            break

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
            ("assembled, not approved" if ms.is_file() else "not assembled"),
            # Assembled-but-not-approved must fix forward with --approve, not
            # re-run the bare command — that would redo the cross-model final
            # read for no reason (I1).
            fix_command=(f"/assemble-book {book} --approve"
                         if ms.is_file() and not approved.is_file() else "")),
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


_BOOK_RE = re.compile(r"\A[0-9]{1,3}\Z")


def render_cell(c: Cell) -> str:
    if c.kind == "na":
        return "—"
    if c.kind == "unknown":
        return "?"
    if c.kind == "count":
        return f"{c.done}/{c.total}"
    return "✓" if c.ok else "✗"


def render(book: str, rows: list[Row], next_row, unknowns: list[Row]) -> str:
    out = [f"BOOK {book}", ""]
    out.append(f"{'STEP':<16}{'RUN':>6}{'PASS':>7}   WHY / ARTEFACT")
    out.append("─" * 72)
    for r in rows:
        out.append(f"{r.label:<16}{render_cell(r.run):>6}{render_cell(r.passed):>7}   "
                   f"{r.reason or r.artefact}")
        out.append(f"{'':<16}{'':>6}{'':>7}   {r.command}")
    out.append("─" * 72)
    next_cmd = (next_row.fix_command or next_row.command) if next_row \
        else "nothing — every step has passed"
    out.append(f"next: {next_cmd}"
               + (f"   ({next_row.label})" if next_row else ""))
    for u in unknowns:
        out.append(f"  ? {u.label}: {u.reason}")
    return "\n".join(out) + "\n"


def one_chapter_rows(book: str, chapter: str, repo_root=None) -> list[Row]:
    """The same six steps as the count rows, for one chapter."""
    # Resolved so artefact paths (built by penny_paths, which resolves
    # internally) can be reliably rendered relative to it via _rel().
    root = _root(repo_root).resolve()
    book, ch = str(book).zfill(2), str(chapter).zfill(2)
    chapters = Path(penny_paths.output_path(f"book-{book}/chapters", root=root))
    packet = Path(penny_paths.input_path(f"book-{book}/packets/ch-{ch}.md", root=root))
    mp = Path(penny_paths.input_path(f"book-{book}/maps/ch-{ch}.md", root=root))
    draft = chapters / f"ch-{ch}.draft.md"
    gate = chapters / f"ch-{ch}.gate.md"
    final = chapters / f"ch-{ch}.final.md"
    cert = Path(penny_paths.penny_path(
        f"locks/book-{book}.ch-{ch}.dev-clear", root=root))

    def b(p: Path) -> Cell:
        return yes() if p.is_file() else no()

    gate_pass, gate_reason = no(), ""
    if gate.is_file():
        try:
            body = gate.read_text(encoding="utf-8")
        except Exception as exc:                  # never a traceback
            gate_pass, gate_reason = unknown(), f"gate could not be read: {exc}"
        else:
            gate_pass = yes() if any(l.strip() == "gate: PASS"
                                     for l in body.splitlines()) else no()

    cleared, cleared_reason = no(), ""
    if cert.is_file() and draft.is_file():
        try:
            rec = parse_frontmatter(cert.read_text(encoding="utf-8")).get(
                "cleared_draft_sha256")
            cleared = yes() if rec and rec == _sha(draft) else no()
        except Exception as exc:                  # never a traceback
            cleared, cleared_reason = unknown(), f"dev-clear cert could not be read: {exc}"

    return [
        Row("packet", "packet", b(packet), na(),
            f"/map-chapter {book} {ch}", _rel(packet, root)),
        Row("map", "map", b(mp), na(), f"/map-chapter {book} {ch}", _rel(mp, root)),
        Row("draft", "draft", b(draft), na(),
            f"/draft-chapter {book} {ch}", _rel(draft, root)),
        Row("gate", "gate", b(gate), gate_pass,
            f"/review-chapter {book} {ch}", _rel(gate, root), gate_reason),
        Row("dev-clear", "dev clear", b(cert), cleared,
            f"preflight clear-dev {book} {ch}", _rel(cert, root), cleared_reason),
        Row("final", "final", b(final), na(),
            f"/finalize-chapter {book} {ch}", _rel(final, root)),
    ]


def _main(argv: list[str]) -> int:
    if not argv or len(argv) > 2:
        print("usage: book_status NN [MM]", file=sys.stderr)
        return 2
    book = argv[0]
    if not _BOOK_RE.match(book):
        print(f"book_status: invalid book id {book!r} — digits only",
              file=sys.stderr)
        return 2
    book = book.zfill(2)
    root = penny_paths.series_root()
    # A story.md with no outline is not an error — it is book 02 between
    # /plot-book writing the story and the first cut, and it is book 01 the
    # moment its legacy outline is deleted to migrate. Refusing on the outline
    # alone would turn the table off exactly at the documented migration step.
    if not (_outline_path(book, root).is_file()
            or _story_path(book, root).is_file()):
        print(f"book_status: nothing to report for book {book} — neither "
              f"{_story_path(book, root)} nor {_outline_path(book, root)}",
              file=sys.stderr)
        return 2
    if len(argv) == 2:
        ch = argv[1]
        if not _BOOK_RE.match(ch):
            print(f"book_status: invalid chapter id {ch!r} — digits only",
                  file=sys.stderr)
            return 2
        rows = one_chapter_rows(book, ch, root)
        print(render(f"{book} ch {ch.zfill(2)}", rows,
                     next_action(rows), unknown_rows(rows)))
        return 0
    rows = all_rows(book, root)
    print(render(book, rows, next_action(rows), unknown_rows(rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
