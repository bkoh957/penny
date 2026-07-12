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
from scripts.penny_wiring import CHAPTER_RE, FIELD_RE, HEADING_RE, QID_RE, split_id

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
# "- **Hook:**" (4-letter key) or plain bolded prose like "- **Maggie** …"
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
            "weave": skel, "readback": out / "reports" / "outline-fan.md",
            "whodunit": root / "series" / "whodunit" / f"book-{book}.yaml"}


def stage_status(book: str, *, repo_root=None) -> list:
    root = _root(repo_root)
    paths = stage_paths(book, root)
    rows = []
    for name in STAGE_ORDER:
        p = paths[name]
        if not p.is_file():
            rows.append((name, "missing", str(p)))
            continue
        fm = parse_frontmatter(p.read_text(encoding="utf-8"))
        if name == "weave":
            done = str(fm.get("woven", "")).strip().lower() == "true"
            rows.append((name, "done" if done else "missing", "woven flag"))
            continue
        stale = []
        for up in _UPSTREAM[name]:
            upath = paths[up]
            field = f"built_from_{upath.stem}"
            recorded = fm.get(field)
            if recorded is None:
                if up == "material" and not upath.is_file():
                    continue  # absent material is a legitimate blank start
                stale.append(f"{field} unstamped")
            elif not upath.is_file() or _sha(upath) != recorded:
                stale.append(f"{field} mismatch")
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
        text = write_frontmatter_field(text, f"built_from_{upp.stem}", _sha(upp))
    p.write_text(text, encoding="utf-8")


def readers_copy_text(text: str, *, reveal_chapter: "int | None" = None) -> str:
    """The blind reader's copy (spec §5): chapters only, in story order, with the
    Solution/Threads sections, wiring lines, question ids, and drafting machinery
    stripped BY CONSTRUCTION — blindness is not an instruction to an agent.

    When reveal_chapter is given, only chapters with num < reveal_chapter are
    emitted (FINDING 3): the reveal chapter's own summary names the culprit, so
    truncating before it mirrors the real reading experience — a reader guesses
    before the reveal — while keeping the whole sagging-middle span the
    put-down signal needs. When None, all chapters are emitted (current/legacy
    behaviour)."""
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

    emitted = [c for c in chapters
               if reveal_chapter is None or c[0] < reveal_chapter]
    truncated = reveal_chapter is not None and len(emitted) < len(chapters)

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


def _reveal_chapter(book: str, root: Path) -> "int | None":
    """Read reveal_chapter from series/whodunit/book-NN.yaml. That ledger is
    genuinely nested human-edited data, so PyYAML is permitted here —
    imported inside this function-scoped helper only, the same pattern
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
    also exits with a named error instead of a raw traceback; it already
    failed closed (nothing written), this only makes the failure legible."""
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
        print(readers_copy(args.book))
        return 0
    ap.error(f"unknown command {args.cmd!r}")  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())
