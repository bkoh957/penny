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
# story_cut.check_story). A tight capture would make "@Maggie" fail to
# tokenise at all — the strand would vanish from the beat silently, and the
# author would get a clean run with a missing character. Capturing it and
# refusing it by name is the loud failure the engine promises.
TAG_RE = re.compile(r"(?<!\S)(?P<sigil>[@#+!-])(?P<slug>\S+)")

QUESTIONS_HEADING_RE = re.compile(r"^##\s+Questions\s*$", re.IGNORECASE)
_HEADING_RE = re.compile(r"^##\s+")
_BULLET_RE = re.compile(r"^-\s+(?P<rest>.*)$")
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
            "clues": [], "line": line_no}


def _harvest(beat, raw):
    """Pull tags out of one raw line, returning the prose that is left."""
    for m in TAG_RE.finditer(raw):
        beat[_SIGIL_KEY[m.group("sigil")]].append(m.group("slug"))
    return TAG_RE.sub("", raw)


def _finish(beat, prose_parts):
    beat["text"] = " ".join(" ".join(prose_parts).split())
    return beat


def parse_story(text: str) -> list[dict]:
    """Beats in story order. Tags are stripped from each beat's `text`."""
    lines = text.splitlines()
    offset = len(text.splitlines()) - len(strip_frontmatter(text).splitlines())
    beats, current, prose = [], None, []
    inert = False

    for i, raw in enumerate(lines):
        if i < offset:
            continue
        if _HEADING_RE.match(raw):
            if current is not None:
                beats.append(_finish(current, prose))
                current, prose = None, []
            inert = _heading_name(raw) in _INERT_HEADINGS
            continue
        if inert:
            continue
        m = _BULLET_RE.match(raw)
        if m:
            if current is not None:
                beats.append(_finish(current, prose))
            current = _blank_beat(i + 1)
            prose = [_harvest(current, m.group("rest"))]
        elif current is not None:
            if not raw.strip():
                beats.append(_finish(current, prose))
                current, prose = None, []
            else:
                prose.append(_harvest(current, raw.strip()))

    if current is not None:
        beats.append(_finish(current, prose))
    return [b for b in beats if b["text"] or any(
        b[k] for k in ("strands", "jobs", "opens", "closes", "clues"))]


def parse_questions(text: str) -> dict[str, str]:
    """id -> prose, from the single `## Questions` block (spec §3.1.1)."""
    out, in_block = {}, False
    for raw in text.splitlines():
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
    out, current, prose, in_block = [], None, [], False

    for i, raw in enumerate(text.splitlines()):
        if _HEADING_RE.match(raw):
            if current is not None:
                out.append(_finish(current, prose))
                current, prose = None, []
            in_block = _heading_name(raw) == want
            continue
        if not in_block:
            continue
        m = _BULLET_RE.match(raw)
        if m:
            if current is not None:
                out.append(_finish(current, prose))
            current = _blank_beat(i + 1)
            prose = [_harvest(current, m.group("rest"))]
        elif current is not None:
            if not raw.strip():
                out.append(_finish(current, prose))
                current, prose = None, []
            else:
                prose.append(_harvest(current, raw.strip()))

    if current is not None:
        out.append(_finish(current, prose))
    return out


_CUT_CHAPTER_RE = re.compile(r"^##\s+Chapter\s+(?P<num>\d+)\s*[—-]\s*(?P<title>.+?)\s*$")
_CUT_FIELD_RE = re.compile(r"^\s*-\s+\*\*(?P<key>Beats|Summary|Compress):\*\*\s*(?P<val>.*)$")
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
    """The showrunner-approved grouping (spec §5.1)."""
    chapters, current = [], None
    for raw in text.splitlines():
        m = _CUT_CHAPTER_RE.match(raw)
        if m:
            current = {"num": int(m.group("num")), "title": m.group("title"),
                       "beats": [], "summary": "", "compress": "", "tracks": {}}
            chapters.append(current)
            continue
        if current is None:
            continue
        fm = _CUT_FIELD_RE.match(raw)
        if fm:
            key, val = fm.group("key"), fm.group("val").strip()
            if key == "Beats":
                current["beats"] = _expand_beats(val)
            else:
                current[key.lower()] = val
            continue
        tm = _CUT_TRACK_RE.match(raw)
        if tm:
            current["tracks"][tm.group("letter")] = tm.group("val").strip()
    return chapters
