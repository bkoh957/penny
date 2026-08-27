"""Parser for input/book-NN/story.md — the source layer (spec 2026-08-03 §3).

Dependency-free by the split rule: story.md is flat authored text, not nested
data, so it belongs to penny_meta's family and never to PyYAML.

The file is beats in story order. Four sigils and nothing else carry meaning:

    @strand   #job   +q-id / -q-id   !clue-id

`##` headings are for the author's reading and are ignored, with one exception:
`## Questions` holds id-to-prose lines and no beats (spec §3.1.1). That
asymmetry is deliberate — the moment a heading means something, the file has a
form to arrange, and arranging a form is what turned the outline's retired
staging layer into a duplicate of outline.md (spec §1).
"""
import re

from scripts.penny_meta import strip_frontmatter  # noqa: F401  (re-exported for callers)

SLUG = r"[a-z0-9][a-z0-9-]*"
SLUG_RE = re.compile(rf"^{SLUG}$")

# A tag is a sigil + one whitespace-delimited token.
#
# The (?<!\S) guard is what keeps "-q-clear" (a close tag) distinct from
# "- text" (a bullet): a bullet's hyphen is followed by a space, and \S+
# cannot match a space.
#
# Capture is deliberately LOOSE (\S+) while validation is strict (SLUG_RE, in
# story_cut.check_story). A tight capture would make "@Dez" fail to
# tokenise at all — the strand would vanish from the beat silently, and the
# author would get a clean run with a missing character. Capturing it and
# refusing it by name is the loud failure the engine promises.
TAG_RE = re.compile(r"(?<!\S)(?P<sigil>[@#+!-])(?P<slug>\S+)")

QUESTIONS_HEADING_RE = re.compile(r"^##\s+Questions\s*$", re.IGNORECASE)
_HEADING_RE = re.compile(r"^##\s+")
_BULLET_RE = re.compile(r"^-\s+(?P<rest>.*)$")

# An OPTIONAL author-facing beat number: `- [12] Dez throws a cup…`. Bracketed
# rather than `12.` because a beat may legitimately open with a bare number ("1987
# was the year of the flood"), and a silent mis-parse here is the worst failure the
# story layer has: beat indices are what the cut plan's `Beats: 22-25` ranges refer
# to, so an off-by-one steals beats from a neighbouring chapter with no symptom.
#
# The number is STRIPPED from the beat's prose. Left in, it would travel through
# emit_outline into the chapter block's Required Beats and land in the drafter's
# packet as literal text — the same leak plain `$tags` cause.
#
# It is never the source of truth. POSITION is. The number is a written-down claim
# ABOUT position, which `story_cut.check_story` verifies (misnumbered-beat) — that
# is its whole value. Absent numbers are legal everywhere: a story.md that has
# never been numbered parses exactly as before.
_BEAT_NUM_RE = re.compile(r"^\[(?P<num>\d+)\]\s+")
_QUESTION_LINE_RE = re.compile(rf"^-\s+(?P<id>q-{SLUG})\s*[—-]\s*(?P<prose>.+?)\s*$")

# Headings whose bullets are NOT beats. A directive bullet read as a beat would
# shift every later beat index, so the cut plan's `Beats: 22-25` would silently
# claim the wrong beats (spec 2026-08-04 §3).
_INERT_HEADINGS = {"questions", "chapter direction", "guardrails"}


def _heading_name(raw):
    """Lowercased text of a `## ` heading, or None if the line is not one."""
    m = _HEADING_RE.match(raw)
    return raw[m.end():].strip().lower() if m else None

_SIGIL_KEY = {"@": "strands", "#": "jobs", "+": "opens", "-": "closes", "!": "clues"}


def _blank_beat(line_no):
    return {"text": "", "strands": [], "jobs": [], "opens": [], "closes": [],
            "clues": [], "line": line_no, "num": None}


def _harvest(beat, raw):
    """Pull tags out of one raw line, returning the prose that is left."""
    for m in TAG_RE.finditer(raw):
        beat[_SIGIL_KEY[m.group("sigil")]].append(m.group("slug"))
    return TAG_RE.sub("", raw)


def _finish(beat, prose_parts):
    beat["text"] = " ".join(" ".join(prose_parts).split())
    return beat


def _body_lines(text: str) -> list:
    """`[(index, line), …]` for the body, frontmatter skipped.

    Every parser in this module walks THIS view, never `text.splitlines()`
    directly. A `## …` line at column 0 inside frontmatter is a legal YAML
    comment, and a parser that reads it as a markdown heading opens a block
    nothing can close — `---` is not a heading (final review, Important 1).

    Indices still count from the top of the FULL text, so a reported `line`
    number matches what the author sees in their editor.
    """
    lines = text.splitlines()
    offset = len(lines) - len(strip_frontmatter(text).splitlines())
    return list(enumerate(lines))[offset:]


def _fold(text: str, active) -> list[dict]:
    """The one bullet/continuation fold — beats and directives share it.

    `active(heading)` decides, from a `##` heading's lowercased name (or None,
    for the region before any heading), whether the bullets that follow are
    collected. Both callers had their own copy of this loop once, and the two
    copies drifted: only one skipped frontmatter, and only one dropped empty
    entries (final review, Important 1 and Minor 4). One loop, one behaviour.

    An entry with neither prose nor tags is dropped — a lone `- ` is not a beat
    and is not a directive.
    """
    entries, current, prose = [], None, []
    collecting = active(None)

    for i, raw in _body_lines(text):
        if _HEADING_RE.match(raw):
            if current is not None:
                entries.append(_finish(current, prose))
                current, prose = None, []
            collecting = active(_heading_name(raw))
            continue
        if not collecting:
            continue
        m = _BULLET_RE.match(raw)
        if m:
            if current is not None:
                entries.append(_finish(current, prose))
            current = _blank_beat(i + 1)
            rest = m.group("rest")
            num = _BEAT_NUM_RE.match(rest)
            if num:
                current["num"] = int(num.group("num"))
                rest = rest[num.end():]
            prose = [_harvest(current, rest)]
        elif current is not None:
            if not raw.strip():
                entries.append(_finish(current, prose))
                current, prose = None, []
            else:
                prose.append(_harvest(current, raw.strip()))

    if current is not None:
        entries.append(_finish(current, prose))
    return [e for e in entries if e["text"] or any(
        e[k] for k in ("strands", "jobs", "opens", "closes", "clues"))]


def parse_story(text: str) -> list[dict]:
    """Beats in story order. Tags are stripped from each beat's `text`."""
    return _fold(text, lambda h: h not in _INERT_HEADINGS)


def parse_questions(text: str) -> dict[str, str]:
    """id -> prose, from the single `## Questions` block (spec §3.1.1)."""
    out, in_block = {}, False
    for _, raw in _body_lines(text):
        if _HEADING_RE.match(raw):
            in_block = bool(QUESTIONS_HEADING_RE.match(raw))
            continue
        if not in_block:
            continue
        m = _QUESTION_LINE_RE.match(raw)
        if m:
            out[m.group("id")] = m.group("prose")
    return out


def parse_directives(text: str, heading: str) -> list[dict]:
    """Scoped direction lines from one `##` block (spec 2026-08-04 §3).

    Same shape as a beat, harvested by the same TAG_RE, so a directive scopes
    with @strand and #job and needs no second syntax. Chapter numbers cannot
    scope a directive — they do not exist until after the cut.
    """
    want = heading.strip().lower()
    return _fold(text, lambda h: h == want)


_CUT_CHAPTER_RE = re.compile(r"^##\s+Chapter\s+(?P<num>\d+)\s*[—-]\s*(?P<title>.+?)\s*$")
_CUT_FIELD_RE = re.compile(
    r"^\s*-\s+\*\*(?P<key>Beats|Summary|Compress|Setting|Texture|Opening):\*\*"
    r"\s*(?P<val>.*)$")
_CUT_CLOSING_RE = re.compile(
    r"^\s*-\s+\*\*Closing\s*\((?P<kind>[^)]*)\):\*\*\s*(?P<val>.*)$")
# A setting sub-item: `  - 22-23 — the pottery studio, late afternoon`. The dash
# separating range from prose is an em dash; a hyphen would be ambiguous against
# the range's own `22-23`.
_CUT_SETTING_ITEM_RE = re.compile(r"^\s+-\s+(?P<spec>[\d,\s-]+?)\s+—\s+(?P<val>.*)$")
# A texture sub-item: `  - bakery 6am: proving-room warmth`. Deliberately BROAD
# where the setting item pattern is narrow — an allocated image is free prose
# with no range to anchor on. That breadth is why the texture branch is matched
# LAST in the loop below, after the closing/field/track patterns: an indented
# `- **M:** …` must stay a track row, not become an image.
_CUT_TEXTURE_ITEM_RE = re.compile(r"^\s+-\s+(?P<val>\S.*?)\s*$")
#: Which cut-plan fields open a nested block, and the chapter key it fills.
_NESTED_BY_KEY = {"Setting": "settings", "Texture": "texture"}
_CUT_TRACK_RE = re.compile(r"^\s*-\s+\*\*(?P<letter>[A-Z]):\*\*\s*(?P<val>.*)$")
_RANGE_RE = re.compile(r"^(\d+)\s*-\s*(\d+)$")


def _expand_beats(spec: str) -> list[int]:
    out = []
    for part in (p.strip() for p in spec.split(",") if p.strip()):
        m = _RANGE_RE.match(part)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            out.extend(range(lo, hi + 1))
        elif part.isdigit():
            out.append(int(part))
    return out


def parse_cut_plan(text: str) -> list[dict]:
    """The showrunner-approved grouping (spec §5.1).

    `settings`, `opening` and `closing` are the cut-level record of where a
    chapter happens and how it lands (spec 2026-08-12). `texture` is the
    cut-level record of what it may SPEND (spec 2026-08-27 §4.2) — the positive
    half of the `compress` line, allocated once across the whole book. All four
    default empty, so a plan written before any of those designs parses exactly
    as it always did — adoption rules live in `story_cut.check_story`, not here.
    """
    chapters, current, nested = [], None, None
    for raw in text.splitlines():
        m = _CUT_CHAPTER_RE.match(raw)
        if m:
            current = {"num": int(m.group("num")), "title": m.group("title"),
                       "beats": [], "summary": "", "compress": "", "tracks": {},
                       "settings": [], "opening": "", "closing": None,
                       "texture": []}
            chapters.append(current)
            nested = None
            continue
        if current is None:
            continue
        if nested == "settings":
            sm = _CUT_SETTING_ITEM_RE.match(raw)
            if sm:
                current["settings"].append(
                    {"beats": _expand_beats(sm.group("spec")),
                     "text": sm.group("val").strip()})
                continue
        cm = _CUT_CLOSING_RE.match(raw)
        if cm:
            nested = None
            current["closing"] = {"kind": cm.group("kind").strip().lower(),
                                  "text": cm.group("val").strip()}
            continue
        fm = _CUT_FIELD_RE.match(raw)
        if fm:
            key, val = fm.group("key"), fm.group("val").strip()
            nested = _NESTED_BY_KEY.get(key)
            if key == "Beats":
                current["beats"] = _expand_beats(val)
            elif key == "Texture":
                # An inline value is a legal one-item allocation. Dropping it
                # silently would lose an author's line to a formatting choice.
                if val:
                    current["texture"].append(val)
            elif key != "Setting":
                current[key.lower()] = val
            continue
        tm = _CUT_TRACK_RE.match(raw)
        if tm:
            nested = None
            current["tracks"][tm.group("letter")] = tm.group("val").strip()
            continue
        if nested == "texture":
            im = _CUT_TEXTURE_ITEM_RE.match(raw)
            if im:
                current["texture"].append(im.group("val").strip())
    return chapters
