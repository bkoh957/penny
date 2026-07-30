"""Save-point machinery for the plotting workshop (spec §7).

Deterministic: which stage is next, what is stale (built_from_* sha256
fingerprints — the clear-dev binding trick applied to planning files), and the
blind reader's-copy rendering (Task 9). The /plot-book runbook only ever ASKS
this script; it never improvises stage detection.

  python3 scripts/plot_stage.py status 01
  python3 scripts/plot_stage.py stamp 01 input/book-01/plot/ending.md \
      --from input/book-01/plot/premise.md
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import penny_paths
from scripts.penny_meta import parse_frontmatter, strip_frontmatter, write_frontmatter_field
from scripts.penny_wiring import (CHAPTER_RE, FIELD_RE, HEADING_RE, LONG_FLAG_RE,
                                   QID_RE, TYPE_FLAG_RE, split_id)

STAGE_ORDER = ["premise", "ending", "turning-points", "counterplot",
               "chapters", "weave", "readback"]

_DROP_FIELDS = {"Because", "Opens", "Closes", "Carries"}
# Case-insensitive WORD-BOUNDARY match; heading text is lower()'d before
# testing. Word-boundary (not substring) so "solution" doesn't also eat a
# legitimate "### Resolution" subsection — "re" + "solution" shares no word
# boundary at the point where "solution" would start.
_DROP_SUBSECTIONS = ("track movement", "tracks", "drafting notes",
                     "possible line-level prompts", "solution")
_DROP_SUBSECTION_RES = [re.compile(r"\b" + re.escape(s) + r"\b") for s in _DROP_SUBSECTIONS]
# Any heading of level 3 OR DEEPER (###, ####, ...) — a casing/level drift in a
# hand-edited heading must not silently defeat the subsection strip.
_H3_RE = re.compile(r"^#{3,}\s+(.*)$")
_QID_TOKEN_RE = re.compile(r"\bq-[a-z0-9][a-z0-9-]*\b")
# Defence in depth for FINDING 2: a permissive, DROP-ONLY pattern for the
# reader's-copy strip alone (never used to loosen the shared, precise
# FIELD_RE that tension_check.py depends on). Matches a Because/Opens/
# Closes/Carries field bullet in any of: "-"/"*"/"+" bullet or none, no
# space after the bullet, and the colon either inside or outside the bold
# markers. The reader's copy may be over-aggressive about dropping wiring
# lines; it must never be under-aggressive.
_WIRING_DROP_RE = re.compile(
    r"^\s*(?:[-*+]\s*)?\*\*\s*(?:Because|Opens|Closes|Carries)\s*:?\s*\*\*\s*:?",
    re.IGNORECASE,
)
# FINDING 1: the shared, strict penny_wiring.TRACK_RE (dash-space bullet,
# colon inside the bold, single uppercase letter) is exactly right for
# tension_check.py's starved-thread check but WRONG as a reader's-copy
# backstop — it is under-aggressive, the one failure mode this strip can
# never afford, on the single most sensitive row in the file (states what
# the culprit does). Mirror _WIRING_DROP_RE's permissiveness: any of
# "-"/"*"/"+"/em-dash/en-dash bullet or none, no space after the bullet, the
# colon inside or outside the bold, and a 1-2 letter (any case) track key.
# Em/en dash join the bullet class because this codebase already treats them
# as interchangeable with "-" elsewhere (see CHAPTER_RE's [—-] separator) and
# unlike a wiring field's question-id (caught by the unconditional
# _QID_TOKEN_RE scrub below regardless of bullet shape), a track row's prose
# has no content-level backstop — only this line-level pattern protects it,
# so its bullet class must be at least as permissive. The {1,2} letter bound
# plus requiring "**" immediately after the key is what keeps this DROP-ONLY
# pattern from also eating "- **Turn / Change:**" (multi-word key) or
# "- **Hook:**" (4-letter key) or plain bolded prose like "- **Character** …"
# (no colon, key too long to leave "**" immediately adjacent).
_TRACK_DROP_RE = re.compile(
    r"^\s*(?:[-*+—–]\s*)?\*\*\s*([A-Za-z]{1,2})\s*:?\s*\*\*\s*:?"
)

_UPSTREAM = {
    "premise": ["material"],           # material is optional (spec §4)
    "ending": ["premise"],
    "turning-points": ["premise", "ending"],
    "counterplot": ["ending", "turning-points"],
    # FINAL REVIEW FINDING 3: chapter-weaver also consumes the whodunit
    # ledger (clue schedule), and readers_copy/tension_check both read
    # reveal_chapter from it — a real upstream that must go stale on edit,
    # same as counterplot's mystery-solution.md.
    "chapters": ["turning-points", "counterplot", "whodunit"],
    "weave": [],                       # done-ness is the skeleton's woven flag
    "readback": ["chapters"],
}


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


_TOP_LEVEL_ENTRY_RE = re.compile(r"^[^\s#-]")


def _strip_reveals_block(text: str) -> str:
    """Remove the top-level `reveals:` block from raw ledger text, byte-for-byte
    over everything else (final review C1).

    The whodunit ledger is flat at the top level, so the block runs from the
    line matching `^reveals:` (column 0) through every following line up to,
    but not including, the next line that starts a new top-level entry — or
    EOF. A one-line `reveals: []` is the degenerate case: the very next line
    is already top-level, so the block is that single line.

    "Starts a new top-level entry" is NOT simply "any non-whitespace at
    column 0": this repo's own reveals: block (spec 2026-07-30 §3) writes its
    sequence items unindented — `- id: impersonation` at column 0, same style
    `clue_schedule:` already uses — so a bare non-whitespace test would treat
    every list item as ending the block after just one line. A line continues the
    current block if it is indented (nested content) OR starts with `-` (a
    block-sequence item); it starts a NEW top-level entry only when neither
    is true (`_TOP_LEVEL_ENTRY_RE`).

    Lines are removed whole (via str.splitlines(keepends=True) + rejoin),
    never re-flowed, so blank lines and the trailing newline outside the
    block are untouched."""
    lines = text.splitlines(keepends=True)
    out = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if re.match(r"^reveals:", line):
            i += 1
            while i < n and not _TOP_LEVEL_ENTRY_RE.match(lines[i]):
                i += 1
            continue
        out.append(line)
        i += 1
    return "".join(out)


def _upstream_sha(path: Path) -> str:
    """The fingerprint for one upstream file.

    The whodunit ledger is the one upstream whose file carries content for TWO
    different stages: the clue schedule feeds `chapters` (change it and the
    chapters carrying those clues must be rewoven), while `reveals:` feeds only
    readback. Hashing the whole file would make declaring a protected turn look
    like a clue-schedule edit and send /plot-book back to chapter regeneration —
    the feature's own activation path undoing the book (final review C1).

    So for that file the fingerprint is taken over the ledger with `reveals:`
    removed. Every other upstream keeps the plain file hash.

    **Detect structurally, strip textually.** `yaml.safe_load` answers only
    "does this ledger have a top-level `reveals:` key?" — parsing (rather than
    a raw substring search) is what keeps a `description:` that happens to
    mention the word "reveals" from being mistaken for the block. But the
    REMOVAL itself is done on the raw text (`_strip_reveals_block`), never by
    re-serialising the parsed dict through `yaml.safe_dump`: a round-trip
    reformats the WHOLE file (PyYAML reorders keys under `sort_keys=True`,
    reflows quoting/wrapping) and changes the hash of content that never
    changed. That would just relocate the false-staleness bug from "reveals:
    exists at all" to "reveals: is declared for the first time on an
    already-stamped book" — book 01's actual next step (spec §10) — instead of
    eliminating it. Text-level removal keeps every other byte identical, so:
    - absent `reveals:` → returns `_sha(path)`, byte-identical to today (every
      already-stamped book that never uses this feature is untouched).
    - `reveals:` added for the first time to an already-stamped ledger →
      stripping it back out reproduces the ORIGINAL bytes exactly (assuming
      nothing else changed), so the fingerprint does not move and `chapters`
      does not go stale. This is the whole point: there is no one-time
      migration cost, because nothing is ever re-serialised.
    - editing content outside `reveals:` (e.g. `clue_schedule`) still changes
      the stripped text, so `chapters` still correctly goes stale.

    Used on BOTH sides of the fingerprint (stamp() writes it, _stage_stale()
    compares against it) — both must agree or the comparison never matches.
    """
    if path.parent.name == "whodunit":
        text = path.read_text(encoding="utf-8")
        try:
            import yaml  # PyYAML: only to detect whether reveals: exists
            data = yaml.safe_load(text)
        except Exception:
            return _sha(path)   # malformed: fall back; _reveals fails loud elsewhere
        if isinstance(data, dict) and "reveals" in data:
            stripped = _strip_reveals_block(text)
            return hashlib.sha256(stripped.encode("utf-8")).hexdigest()
    return _sha(path)


def _root(repo_root) -> Path:
    return Path(repo_root) if repo_root is not None else penny_paths.series_root()


def stage_paths(book: str, root: Path) -> dict:
    plot = root / "input" / f"book-{book}" / "plot"
    out = root / "output" / f"book-{book}"
    skel = root / "input" / f"book-{book}" / "outline-skeleton.md"
    # "whodunit" is a fingerprint upstream (FINDING 3), not a STAGE_ORDER
    # stage — stage_status() only ever indexes this dict with STAGE_ORDER
    # names for the row loop; "whodunit" is reached solely via _UPSTREAM
    # lookups, the same pattern "material" already uses for "premise".
    return {"material": plot / "material.md", "premise": plot / "premise.md",
            "ending": plot / "ending.md", "turning-points": plot / "turning-points.md",
            "counterplot": out / "mystery-solution.md", "chapters": skel,
            # readback writes one report PER STAGE (outline-fan-stage-K.md), so
            # there is no single canonical filename any more — this entry's
            # ".parent" is the only part callers use (stage_status globs
            # "outline-fan*.md" under it); the "outline-fan.md" filename itself
            # is kept only as the human-readable hint in the "missing" detail
            # line printed when no report exists yet.
            "weave": skel, "readback": out / "reports" / "outline-fan.md",
            "whodunit": root / "series" / "whodunit" / f"book-{book}.yaml"}


def _stage_stale(name: str, path: Path, paths: dict) -> list[str]:
    """The `built_from_*` staleness findings for one stage file, or [] if it is
    current. Extracted from stage_status so the readback stage can run it over
    several files — the fan writes one report per protected reveal."""
    fm = parse_frontmatter(path.read_text(encoding="utf-8"))
    stale = []
    for up in _UPSTREAM[name]:
        upath = paths[up]
        field = f"built_from_{upath.stem}"
        recorded = fm.get(field)
        if recorded is None:
            if up == "material" and not upath.is_file():
                continue  # absent material is a legitimate blank start
            stale.append(f"{field} unstamped")
        elif not upath.is_file() or _upstream_sha(upath) != recorded:
            stale.append(f"{field} mismatch")
    return stale


def stage_status(book: str, *, repo_root=None) -> list:
    root = _root(repo_root)
    paths = stage_paths(book, root)
    rows = []
    for name in STAGE_ORDER:
        p = paths[name]
        if name == "readback":
            # The fan writes ONE REPORT PER STAGE (spec 2026-07-30 §5), so
            # there is no single canonical filename to stat. Readback is done
            # when at least one report exists AND every one of them is stamped
            # against the current skeleton: a readback is only complete if
            # every stage was read against the plan actually on disk. The glob
            # also keeps recognising a pre-staging `outline-fan.md`, so a
            # series read back before this change is not told to redo it.
            reports = sorted(p.parent.glob("outline-fan*.md"))
            if not reports:
                rows.append((name, "missing", str(p.parent / "outline-fan*.md")))
                continue
            stale = []
            for rp in reports:
                stale += [f"{rp.stem}: {s}" for s in _stage_stale(name, rp, paths)]
            rows.append((name, "stale" if stale else "done", "; ".join(stale)))
            continue
        if not p.is_file():
            rows.append((name, "missing", str(p)))
            continue
        if name == "weave":
            fm = parse_frontmatter(p.read_text(encoding="utf-8"))
            done = str(fm.get("woven", "")).strip().lower() == "true"
            rows.append((name, "done" if done else "missing", "woven flag"))
            continue
        stale = _stage_stale(name, p, paths)
        rows.append((name, "stale" if stale else "done", "; ".join(stale)))
    return rows


def next_stage(rows) -> "str | None":
    for name, state, _ in rows:
        if state != "done":
            return name
    return None


def stamp(book: str, target, upstreams, *, repo_root=None) -> None:
    p = Path(target)
    text = p.read_text(encoding="utf-8")
    if not text.startswith("---"):
        text = "---\n---\n\n" + text
    for up in upstreams:
        upp = Path(up)
        text = write_frontmatter_field(text, f"built_from_{upp.stem}", _upstream_sha(upp))
    p.write_text(text, encoding="utf-8")


def readers_copy_text(text: str, *, reveal_chapter: "int | None" = None,
                      last_chapter: "int | None" = None) -> str:
    """The blind reader's copy (spec §5): chapters only, in story order, with the
    Solution/Threads sections, wiring lines, question ids, and drafting machinery
    stripped BY CONSTRUCTION — blindness is not an instruction to an agent.

    When reveal_chapter is given, only chapters with num < reveal_chapter are
    emitted (FINDING 3): the reveal chapter's own summary names the culprit, so
    truncating before it mirrors the real reading experience — a reader guesses
    before the reveal — while keeping the whole sagging-middle span the
    put-down signal needs. When None, all chapters are emitted (current/legacy
    behaviour).

    `last_chapter` is the STAGED form (spec 2026-07-30 §4): emit chapters
    num <= last_chapter, so a caller can cut one chapter short of a protected
    reveal without pretending that reveal is the book's culprit reveal. The two
    parameters are mutually exclusive — they express the same cut with different
    off-by-one conventions, and accepting both would silently apply one."""
    body = strip_frontmatter(text)
    sections = list(HEADING_RE.finditer(body))
    chapters = []
    for i, m in enumerate(sections):
        cm = CHAPTER_RE.match(m.group(1))
        if not cm:
            continue
        start = m.start()
        end = sections[i + 1].start() if i + 1 < len(sections) else len(body)
        chapters.append((int(cm.group(1)), start, end))

    if reveal_chapter is not None and last_chapter is not None:
        raise ValueError(
            "readers_copy_text: pass reveal_chapter or last_chapter, not both")
    if last_chapter is not None:
        emitted = [c for c in chapters if c[0] <= last_chapter]
    else:
        emitted = [c for c in chapters
                   if reveal_chapter is None or c[0] < reveal_chapter]
    truncated = len(emitted) < len(chapters)

    out_lines = ["# Outline — reader's copy"]
    if truncated:
        last_num = max(n for n, _, _ in emitted) if emitted else 0
        out_lines.append(
            f"> Chapters 1–{last_num}. The book continues past this point; "
            "the ending is deliberately withheld.")
    out_lines.append("")
    for _num, start, end in emitted:
        skipping = False
        for line in body[start:end].splitlines():
            h3 = _H3_RE.match(line)
            if h3:
                skipping = any(pat.search(h3.group(1).lower()) for pat in _DROP_SUBSECTION_RES)
                if skipping:
                    continue
            elif skipping:
                continue
            if HEADING_RE.match(line):
                # A chapter-title flag ("## Chapter 14 — The Reveal
                # [type: major-reveal] [long: reason]") is a spoiler — it
                # names the reveal chapter to the blind reader as surely as
                # the raw heading text would. Strip it here, by construction,
                # reusing penny_wiring's own TYPE_FLAG_RE/LONG_FLAG_RE (one
                # parser, one set of patterns) rather than a second regex.
                line = TYPE_FLAG_RE.sub("", line)
                line = LONG_FLAG_RE.sub("", line)
            # FINDING 1: drop any track row wherever it falls, independent of
            # heading spelling/level, bullet style, spacing, or case, or
            # whether there is a heading at all — see _TRACK_DROP_RE above.
            if _TRACK_DROP_RE.match(line):
                continue
            fm = FIELD_RE.match(line)
            if fm:
                field, value = fm.group(1), fm.group(2)
                if field in _DROP_FIELDS:
                    continue
                if field == "Hook":
                    qid, rest = split_id(value)
                    if not QID_RE.match(qid):
                        # Malformed wiring (no clean "id — prose" separator):
                        # don't trust the split, don't leave the raw line in
                        # place — defensively scrub any bare question-id token
                        # wherever it falls. Blindness is enforced here, at
                        # the strip, not by trusting upstream validation ran.
                        rest = _QID_TOKEN_RE.sub("", value).strip()
                    line = line[:line.index("**Hook:**") + len("**Hook:**")] + (
                        f" {rest}" if rest else "")
            elif _WIRING_DROP_RE.match(line):
                # FINDING 2: non-canonical wiring bullets (asterisk bullet, no
                # space after the dash, colon outside the bold, no bullet at
                # all) that FIELD_RE's exact shape misses.
                continue
            # FINDING 2, belt-and-braces: scrub any surviving question-id
            # token from EVERY line that reaches the reader, not just the
            # malformed-Hook branch above. This closes case-drift gaps (e.g.
            # a lowercase "**hook:**" field, which misses FIELD_RE's exact
            # case and is deliberately absent from _WIRING_DROP_RE so Hook
            # prose can survive) by construction rather than by enumerating
            # every field shape that might carry an id.
            line = _QID_TOKEN_RE.sub("", line)
            line = re.sub(r"(?<=\S)[ \t]{2,}", " ", line).rstrip()
            out_lines.append(line)
        out_lines.append("")
    return "\n".join(out_lines).rstrip() + "\n"


def _load_whodunit(book: str, root: Path) -> "dict | None":
    """Load the whodunit ledger from series/whodunit/book-NN.yaml. Returns None
    if the ledger file doesn't exist (the legitimate pre-planning-stage case);
    exits loud if the file exists but is malformed YAML or not a mapping."""
    path = penny_paths.series_path(f"whodunit/book-{book}.yaml", root=root)
    if not path.is_file():
        return None
    import yaml  # PyYAML: the whodunit ledger is genuinely nested human data
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        sys.exit(f"plot_stage: malformed whodunit ledger {path}: {exc}")
    if not isinstance(data, dict):
        sys.exit(
            f"plot_stage: whodunit ledger {path} must be a YAML mapping, "
            f"got {type(data).__name__}")
    return data


def _reveal_chapter(book: str, root: Path) -> "int | None":
    """Read reveal_chapter from series/whodunit/book-NN.yaml. That ledger is
    genuinely nested human-edited data, so PyYAML is permitted here —
    imported inside the function-scoped helper _load_whodunit, the same pattern
    tension_check.py's _load_yaml uses. The outline itself stays penny_meta/
    penny_wiring only.

    FINDING 3 — fail LOUD, not open: "no ledger at all" (the file doesn't
    exist) is the legitimate pre-planning-stage case and returns None, which
    means "emit every chapter, untruncated" — correct, because a book that
    hasn't reached the mystery-planner stage yet has nothing to truncate
    before. But once a ledger EXISTS, a missing/blank/non-integer/boolean
    reveal_chapter is a mistake, not a legitimate state — a book plotted far
    enough to have a whodunit ledger always has a reveal_chapter by the time
    readers-copy runs. Silently returning None there would fail open and
    leak the reveal chapter, so it exits loud instead.

    FINDING 4 — malformed YAML or a non-mapping ledger (e.g. a bare list)
    is handled by _load_whodunit, which exits with a named error instead of
    a raw traceback; it already failed closed (nothing written), this only
    makes the failure legible."""
    data = _load_whodunit(book, root)
    if data is None:
        return None
    path = penny_paths.series_path(f"whodunit/book-{book}.yaml", root=root)
    rc = data.get("reveal_chapter")
    rc_int = None
    if isinstance(rc, int) and not isinstance(rc, bool):
        rc_int = rc
    elif isinstance(rc, str) and rc.strip().isdigit():
        rc_int = int(rc.strip())
    if rc_int is None or rc_int <= 0:
        sys.exit(
            f"plot_stage: whodunit ledger {path} has no valid reveal_chapter "
            f"(got {rc!r}); the reader's copy cannot be rendered blind "
            "without a valid reveal_chapter")
    return rc_int


def _reveals(book: str, root: Path) -> list[dict]:
    """Read the OPTIONAL `reveals:` block from series/whodunit/book-NN.yaml
    (spec 2026-07-30 §3) — the protected turns the staged reader's copy is cut
    at, and the answer key the audit measures the reader against.

    Absent ledger, or a ledger with no `reveals:` key, returns [] — that is the
    normal legacy case and the caller falls back to the single-cut copy. But a
    block that EXISTS and is malformed exits loud, never open: the same
    fail-loud-not-open rule _reveal_chapter documents. Silently falling back to
    one stage would hand the fan a copy that runs past a protected turn while
    the showrunner believed it was staged."""
    data = _load_whodunit(book, root)
    if data is None:
        return []
    path = penny_paths.series_path(f"whodunit/book-{book}.yaml", root=root)
    raw = data.get("reveals")
    if raw is None:
        return []
    if not isinstance(raw, list):
        sys.exit(f"plot_stage: {path}: 'reveals' must be a list, "
                 f"got {type(raw).__name__}")
    total = data.get("total_chapters")
    total_int = total if isinstance(total, int) and not isinstance(total, bool) else None
    out: list[dict] = []
    seen_ids: set[str] = set()
    prev_ch = 0
    for i, entry in enumerate(raw, start=1):
        where = f"{path}: reveals[{i}]"
        if not isinstance(entry, dict):
            sys.exit(f"plot_stage: {where} must be a mapping, "
                     f"got {type(entry).__name__}")
        rid = entry.get("id")
        if not isinstance(rid, str) or not rid.strip():
            sys.exit(f"plot_stage: {where} missing 'id'")
        rid = rid.strip()
        if rid in seen_ids:
            sys.exit(f"plot_stage: {where} duplicate reveal id {rid!r}")
        seen_ids.add(rid)
        if "reveal_chapter" not in entry:
            sys.exit(f"plot_stage: {where} ({rid}) missing 'reveal_chapter'")
        rc = entry["reveal_chapter"]
        if not isinstance(rc, int) or isinstance(rc, bool):
            sys.exit(f"plot_stage: {where} ({rid}) reveal_chapter is not an "
                     f"integer: {rc!r}")
        truth = entry.get("author_truth")
        if not isinstance(truth, str) or not truth.strip():
            sys.exit(f"plot_stage: {where} ({rid}) missing 'author_truth'")
        if rc < 2:
            sys.exit(f"plot_stage: {where} ({rid}) cannot be chapter {rc} — a "
                     "reveal at chapter 1 leaves its stage with no chapters to "
                     "read")
        if total_int is not None and rc > total_int:
            sys.exit(f"plot_stage: {where} ({rid}) reveal_chapter {rc} is "
                     f"beyond total_chapters ({total_int})")
        if rc < prev_ch:
            sys.exit(f"plot_stage: {where} ({rid}) reveal_chapter {rc} is not "
                     f"in ascending order (previous was {prev_ch})")
        prev_ch = rc
        item = {"id": rid, "reveal_chapter": rc, "author_truth": truth.strip()}
        if "reader_should_think_before" in entry:
            hints = entry["reader_should_think_before"]
            if not isinstance(hints, list) or not hints:
                sys.exit(f"plot_stage: {where} ({rid}) 'reader_should_think_before' "
                         f"must be a non-empty list")
            item["reader_should_think_before"] = [str(h).strip() for h in hints]
        out.append(item)
    return out


def reveal_stages(reveals: list[dict]) -> list[int | None]:
    """Stage boundaries for the staged reader's copy (spec 2026-07-30 §4).

    Returns one entry per stage: the LAST chapter that stage's copy may
    contain, with None (the always-final entry) meaning the whole book. Stage n
    stops one chapter short of the nth protected reveal, so the reader files
    what it believes BEFORE reading the turn.

    Equal reveal_chapter values collapse to one boundary — two protected turns
    landing in the same chapter is legitimate (a suspect reveal and an identity
    reveal can share it) and must not produce two identical stages. Empty input
    returns [], which the caller reads as "no staging, use the legacy
    single-cut copy"."""
    if not reveals:
        return []
    bounds: list[int | None] = []
    for r in reveals:
        b = r["reveal_chapter"] - 1
        if b not in bounds:
            bounds.append(b)
    bounds.append(None)
    return bounds


def _chapter_numbers(text: str) -> list[int]:
    body = strip_frontmatter(text)
    return [int(cm.group(1)) for m in HEADING_RE.finditer(body)
            for cm in [CHAPTER_RE.match(m.group(1))] if cm]


def readers_copy(book: str, *, repo_root=None) -> Path:
    root = _root(repo_root)
    skel = stage_paths(book, root)["chapters"]
    if not skel.is_file():
        sys.exit(f"plot_stage: no outline-skeleton for book {book} ({skel})")
    skel_text = skel.read_text(encoding="utf-8")
    reveal_ch = _reveal_chapter(book, root)
    # FINAL REVIEW FINDING 1: a reveal_chapter LARGER than the last chapter in
    # the skeleton has nothing to truncate before — readers_copy_text would
    # silently emit every chapter, including the reveal chapter's own
    # culprit-naming summary, straight to the blind fan. The module docstring
    # promises "fail LOUD, not open"; a value in range but simply absent
    # coverage is caught elsewhere (readback/tension_check), but an
    # out-of-range value here specifically defeats the blind guarantee, so it
    # fails loud at the one place both the skeleton and the ledger are in hand.
    if reveal_ch is not None:
        nums = _chapter_numbers(skel_text)
        if nums and reveal_ch > max(nums):
            sys.exit(
                f"plot_stage: whodunit ledger reveal_chapter ({reveal_ch}) is "
                f"beyond the last chapter in the skeleton ({max(nums)}) for "
                f"book {book} — the reader's copy would have nothing to "
                "truncate and would leak the reveal chapter's own summary")
    dest = root / "output" / f"book-{book}" / "reports" / "outline-readers-copy.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        readers_copy_text(skel_text, reveal_chapter=reveal_ch),
        encoding="utf-8")
    return dest


def readers_copy_staged(book: str, *, repo_root=None) -> list[Path]:
    """Write one reader's copy per protected reveal (spec 2026-07-30 §4).

    Each stage's copy is CUMULATIVE from chapter 1 and stops one chapter short
    of that stage's reveal; the final stage is the whole book. Returns the paths
    in stage order, or [] when the ledger declares no `reveals:` — the caller
    then falls back to readers_copy() and today's behaviour is untouched."""
    root = _root(repo_root)
    reveals = _reveals(book, root)
    stages = reveal_stages(reveals)
    if not stages:
        return []
    skel = stage_paths(book, root)["chapters"]
    if not skel.is_file():
        sys.exit(f"plot_stage: no outline-skeleton for book {book} ({skel})")
    skel_text = skel.read_text(encoding="utf-8")
    nums = _chapter_numbers(skel_text)
    last = max(nums) if nums else 0
    for r in reveals:
        if r["reveal_chapter"] > last:
            sys.exit(
                f"plot_stage: reveal {r['id']!r} is at chapter "
                f"{r['reveal_chapter']} but the skeleton's last chapter is "
                f"{last} for book {book} — that stage cannot be cut")
    out_dir = root / "output" / f"book-{book}" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for i, bound in enumerate(stages, start=1):
        dest = out_dir / f"outline-readers-copy-stage-{i}.md"
        dest.write_text(readers_copy_text(skel_text, last_chapter=bound),
                        encoding="utf-8")
        written.append(dest)
    return written


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Plotting-workshop stage machinery.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_st = sub.add_parser("status")
    p_st.add_argument("book")
    p_sp = sub.add_parser("stamp")
    p_sp.add_argument("book")
    p_sp.add_argument("target")
    p_sp.add_argument("--from", dest="upstreams", nargs="+", required=True)
    p_rc = sub.add_parser("readers-copy")
    p_rc.add_argument("book")
    p_rc.add_argument("--staged", action="store_true",
                      help="one copy per protected reveal (whodunit reveals: "
                           "block); falls back to the single-cut copy when the "
                           "ledger declares none")
    args = ap.parse_args(argv)
    if args.cmd == "status":
        rows = stage_status(args.book)
        for name, state, detail in rows:
            print(f"stage {name}: {state}" + (f" ({detail})" if state == "stale" and detail else ""))
        nxt = next_stage(rows)
        print(f"next: {nxt if nxt else 'none — plan complete'}")
        return 0
    if args.cmd == "stamp":
        stamp(args.book, args.target, args.upstreams)
        return 0
    if args.cmd == "readers-copy":
        if args.staged:
            paths = readers_copy_staged(args.book)
            if paths:
                for p in paths:
                    print(p)
                return 0
            print("plot_stage: no reveals: block — writing the single-cut copy")
        print(readers_copy(args.book))
        return 0
    ap.error(f"unknown command {args.cmd!r}")  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())
