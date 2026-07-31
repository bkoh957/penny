"""Deterministic, read-only views over a book's outline (spec 2026-07-31 §3.2).

`outline.md` is a MACHINE INPUT: packet_assemble.py slices one chapter out of it
and each block must stand alone, so roughly a third of the file is repeated
furniture. The showrunner was never its audience. This module renders what they
should read instead, and NEVER writes to the source.

Three views, none of which makes an LLM judgement:
  glance   — every chapter's title + summary, in order
  strands  — one character's line through the whole book
  spine    — the active genre's structural-job worksheet
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterator

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.penny_meta import strip_frontmatter
from scripts.penny_wiring import CHAPTER_RE, HEADING_RE, parse_packet_sections


def iter_chapters(text: str) -> Iterator[tuple[int, str, str]]:
    """(number, title, block) for each `## Chapter NN — Title`, in file order."""
    body = strip_frontmatter(text)
    marks = list(HEADING_RE.finditer(body))
    for i, m in enumerate(marks):
        cm = CHAPTER_RE.match(m.group(1))
        if not cm:
            continue
        start = m.end()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
        yield int(cm.group(1)), (cm.group(2) or "").strip(), body[start:end].strip()


def glance(text: str) -> str:
    """The whole story in order: title + summary per chapter, nothing else."""
    out = ["# The story at a glance", ""]
    for num, title, block in iter_chapters(text):
        summary = parse_packet_sections(block).get("Chapter Summary", "").strip()
        out.append(f"## {num:02d} — {title}" if title else f"## {num:02d}")
        out.append("")
        out.append(summary or "*(no summary)*")
        out.append("")
    return "\n".join(out)


_STRAND_SECTIONS = ("Chapter Summary", "Required Beats")


def name_tokens(slug: str) -> list[str]:
    """'tara-marion' -> ['tara', 'marion']. A ledger slug is an id; the outline
    prose uses the plain names inside it, either of which identifies them."""
    return [t for t in slug.lower().split("-") if t]


def strand(text: str, slug: str) -> list[tuple[int, str]]:
    """(chapter_number, line) for every summary/beat line naming this character,
    in story order — their line through the whole book on one page.

    WHOLE-WORD matching is load-bearing: a substring match puts 'Simone' on
    Simon's page, which invents a hole rather than finding one.
    """
    tokens = name_tokens(slug)
    if not tokens:
        raise ValueError(f"strand: slug {slug!r} yields no name tokens")
    pat = re.compile(r"\b(?:" + "|".join(re.escape(t) for t in tokens) + r")\b",
                     re.IGNORECASE)
    hits: list[tuple[int, str]] = []
    seen: set[tuple[int, str]] = set()
    for num, _title, block in iter_chapters(text):
        sections = parse_packet_sections(block)
        for name in _STRAND_SECTIONS:
            for raw in sections.get(name, "").splitlines():
                line = raw.strip().lstrip("-").strip()
                if line and pat.search(line) and (num, line) not in seen:
                    seen.add((num, line))
                    hits.append((num, line))
    return hits


def render_strand(slug: str, hits: list[tuple[int, str]]) -> str:
    out = [f"# Strand — {slug}", ""]
    if not hits:
        out.append("*(this character is never named in a summary or beat)*")
        return "\n".join(out) + "\n"
    for num, line in hits:
        out.append(f"- **ch {num:02d}** — {line}")
    return "\n".join(out) + "\n"


def roster(book: str, root=None) -> list[str]:
    """Character slugs from the whodunit ledger: every alibi_grid suspect, plus
    the victim. PyYAML is correct here — the ledger is nested human-edited data.
    Returns [] when there is no readable ledger; the caller then needs --who.

    Raises ValueError (never a raw yaml.YAMLError) when the ledger file exists
    but is not parseable — a hand-edited yaml file can be truncated or broken,
    and the CLI's single ValueError catch is what turns this into a named
    stderr line instead of a traceback."""
    import yaml

    from scripts import penny_paths
    path = penny_paths.series_path(f"whodunit/book-{book}.yaml", root=root)
    if not Path(path).is_file():
        return []
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ValueError(
            f"roster: whodunit ledger for book {book} is not valid YAML "
            f"({path}): {exc}"
        ) from exc
    if not isinstance(data, dict):
        # Valid YAML, wrong shape: a scalar ("just a string\n") or a bare
        # top-level list both parse cleanly but have no .get() — a truncated
        # or mis-saved hand-edited ledger is a realistic way to get here, and
        # this is exactly the failure mode the earlier YAMLError guard was
        # meant to eliminate.
        raise ValueError(
            f"roster: whodunit ledger for book {book} must be a mapping at "
            f"the top level, got {type(data).__name__} ({path})"
        )
    names: list[str] = []
    for entry in data.get("alibi_grid") or []:
        if isinstance(entry, dict) and entry.get("suspect"):
            names.append(str(entry["suspect"]))
    victim = data.get("victim")
    if victim and str(victim) not in names:
        names.append(str(victim))
    return names


_JOB_RE = re.compile(r"^##\s+\d+\.\s+(?P<title>.+?)\s*$\n<!--\s*job:\s*(?P<id>[a-z0-9-]+)\s*-->",
                     re.MULTILINE)


def parse_jobs(text: str) -> list[tuple[str, str]]:
    """(job_id, title) for each marked structural job, in file order.

    A job is addressed by its STABLE ID, never its ordinal position: 'job 11'
    means nothing in a genre whose file has a different shape. An unmarked
    heading is not a job — silently skipped, so a genre pack can carry prose
    headings alongside its jobs. That silence is deliberate.

    A marker that IS present but malformed — inline with its heading, indented,
    or naming an id outside [a-z0-9-] — is a different case and must fail loud:
    a genre author's typo would otherwise leave the spine worksheet quietly
    missing a job. Detected by scanning for the literal '<!-- job:' substring
    and comparing it against what _JOB_RE actually captured — a well-formed
    file can never have more literal occurrences than captures.

    Two jobs sharing an id also fails loud: the whole premise of an id is that
    it addresses one job unambiguously.
    """
    jobs: list[tuple[str, str]] = []
    matched_line_nos: set[int] = set()
    for m in _JOB_RE.finditer(text):
        jobs.append((m.group("id"), m.group("title")))
        marker_offset = m.start() + m.group(0).index("<!--")
        matched_line_nos.add(text.count("\n", 0, marker_offset))

    lines = text.split("\n")
    stray = [i for i, line in enumerate(lines)
             if "<!-- job:" in line and i not in matched_line_nos]
    if stray:
        i = stray[0]
        raise ValueError(
            f"parse_jobs: malformed job marker at line {i + 1}: {lines[i]!r} — "
            "a '<!-- job: some-id -->' marker must sit alone on the line "
            "immediately after its '## N. Title' heading, with a lowercase "
            "id made only of [a-z0-9-]"
        )

    seen: dict[str, str] = {}
    for job_id, title in jobs:
        if job_id in seen:
            raise ValueError(
                f"parse_jobs: duplicate job id {job_id!r} (used by both "
                f"{seen[job_id]!r} and {title!r})"
            )
        seen[job_id] = title

    return jobs


def spine_worksheet(jobs: list[tuple[str, str]],
                    chapters: list[tuple[int, str]]) -> str:
    """The structural-job worksheet: every job, unfilled, beside the book's
    chapter list. WHICH chapter answers WHICH job is a judgement and belongs to
    the spine-mapper agent — this half stays deterministic so the frame the
    agent fills is never itself an opinion."""
    if not jobs:
        raise ValueError("spine_worksheet: no structural jobs — the active "
                         "genre declares no macro_structure, or its file "
                         "carries no <!-- job: --> markers")
    out = ["# Spine worksheet", "",
           "One line per structural job. Fill `chapters:` with the chapter "
           "numbers that answer it, or leave it empty — an empty job is a hole.",
           "", "## Jobs", ""]
    for job_id, title in jobs:
        out += [f"### {job_id}", f"*{title}*", "", "chapters:", ""]
    out += ["## The book's chapters", ""]
    for num, title in chapters:
        out.append(f"- {num:02d} — {title}" if title else f"- {num:02d}")
    out.append("")
    return "\n".join(out)


_SLUG_RE = re.compile(r"\A[a-z0-9][a-z0-9-]*\Z")


def _slug_error(kind: str, value: str) -> str | None:
    """None if `value` is safe to use as a single path component; otherwise a
    named refusal message. A book id or character slug is showrunner-authored
    — typed by hand after --who, or read out of a hand-edited yaml ledger's
    `suspect:`/`victim:` fields — and this is the only check standing between
    a stray '/' or '..' and a write outside output/book-NN/reports/. It MUST
    run before the value ever reaches Path(...), never after."""
    if not _SLUG_RE.match(value):
        return (f"outline_views: invalid {kind} {value!r} — must match "
                f"{_SLUG_RE.pattern!r} (lowercase letters, digits, hyphens "
                "only; no '/', no '.', no leading hyphen)")
    return None


def _reports_dir(book: str, root=None) -> Path:
    from scripts import penny_paths
    d = Path(penny_paths.output_path(f"book-{book}/reports", root=root))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _outline_text(book: str, root=None) -> str:
    from scripts import penny_paths
    path = Path(penny_paths.input_path(f"book-{book}/outline.md", root=root))
    if not path.is_file():
        # NOT sys.exit(f"...") — sys.exit(str) sets process exit code 1, but
        # this CLI's contract (and this module's tests) is 0/2 = clean/usage.
        print(f"outline_views: no outline for book {book} ({path})", file=sys.stderr)
        sys.exit(2)
    return path.read_text(encoding="utf-8")


def _main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: outline_views <glance|strands|spine> NN [--who a,b]",
              file=sys.stderr)
        return 2
    cmd, book = argv[0], argv[1]

    # Validate the book id BEFORE it ever reaches a path — _outline_text and
    # _reports_dir both interpolate it straight into a filesystem path, so a
    # book id of e.g. "../.." must be refused here, before either function
    # creates or opens anything.
    err = _slug_error("book id", book)
    if err:
        print(err, file=sys.stderr)
        return 2

    text = _outline_text(book)
    dest_dir = _reports_dir(book)

    # Every view below can raise ValueError from the view layer — a degenerate
    # character slug (strand()), an unparseable ledger (roster()), or a
    # malformed/duplicate job marker (parse_jobs(), spine_worksheet()). All of
    # those are showrunner-data problems, not engine bugs: turn each into one
    # named line on stderr and exit 2, never a raw traceback in the writer's
    # face.
    try:
        if cmd == "glance":
            dest = dest_dir / "outline-glance.md"
            dest.write_text(glance(text), encoding="utf-8")
            print(dest)
            return 0

        if cmd == "strands":
            who: list[str] = []
            if "--who" in argv:
                idx = argv.index("--who")
                if idx + 1 >= len(argv):
                    print("outline_views: --who requires a value "
                          "(comma-separated character slugs)", file=sys.stderr)
                    return 2
                who = [s.strip() for s in argv[idx + 1].split(",") if s.strip()]
            else:
                who = roster(book)
            if not who:
                print(f"outline_views: no roster for book {book} — no "
                      "whodunit ledger was found, or it was found but has no "
                      "alibi_grid entries — pass --who name,name",
                      file=sys.stderr)
                return 2
            # Validate every slug BEFORE any file is written — a batch of N
            # slugs where the last one is a path-traversal attempt must not
            # have already written the first N-1 files.
            for slug in who:
                err = _slug_error("character slug", slug)
                if err:
                    print(err, file=sys.stderr)
                    return 2
            out_dir = dest_dir / "strands"
            out_dir.mkdir(parents=True, exist_ok=True)
            for slug in who:
                dest = out_dir / f"{slug}.md"
                dest.write_text(render_strand(slug, strand(text, slug)), encoding="utf-8")
                print(dest)
            return 0

        if cmd == "spine":
            from scripts import penny_genre
            path = penny_genre.macro_structure()
            if path is None:
                print("outline_views: the active series declares no genre, or its "
                      "genre.yaml has no macro_structure: key — the spine view "
                      "cannot know what jobs to check", file=sys.stderr)
                return 2
            jobs = parse_jobs(Path(path).read_text(encoding="utf-8"))
            chapters = [(n, t) for n, t, _b in iter_chapters(text)]
            body = spine_worksheet(jobs, chapters)
            dest = dest_dir / "spine-worksheet.md"
            dest.write_text(body, encoding="utf-8")
            print(dest)
            return 0
    except ValueError as exc:
        print(f"outline_views: {exc}", file=sys.stderr)
        return 2

    print(f"outline_views: unknown view '{cmd}'", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
