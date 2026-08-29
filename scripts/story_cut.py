"""Validate story.md + cut-plan.md, then emit outline.md (spec 2026-08-03).

Deterministic throughout: this module makes no LLM judgment. The one judgment
in the cut — where chapter boundaries fall — is made by the `chapter-cutter`
agent and approved by the showrunner before this module ever runs (spec §5).

No waivers exist at this level (spec §8). Fix the story or fix the cut plan.
"""
import hashlib
import re
import sys
from pathlib import Path

# Allow `import scripts.*` when this file is run directly as
# `python3 scripts/story_cut.py` (direct-run puts scripts/ on sys.path, not
# the repo root) — same fix as map_check.py. Harmless under pytest, where
# pytest.ini's pythonpath=. already puts the repo root on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml  # ledger only — nested human-edited data (dependency-split rule)

from scripts import penny_genre, penny_paths, penny_story, plot_stage
from scripts.outline_views import parse_jobs
from scripts.penny_meta import parse_frontmatter, strip_frontmatter
# `_CUT_CHAPTER_RE`, `_CUT_FIELD_RE` and `_CUT_CLOSING_RE` are private to
# penny_story and imported anyway, deliberately: the raw-text guard in
# check_story must agree with that module about where a chapter block begins
# and what a field/closing line looks like, and a local re-derivation of its
# patterns is exactly what produced the divergence this guard replaces (spec
# 2026-08-29-nested-cut-plan-field-hijack-fix.md §3). story_cut already
# drives entirely off penny_story's parse; sharing the patterns is the
# smaller coupling.
from scripts.penny_story import (SLUG_RE, _CUT_CHAPTER_RE, _CUT_CLOSING_RE,
                                 _CUT_FIELD_RE, parse_cut_plan,
                                 parse_directives, parse_questions, parse_story)
from scripts.penny_wiring import FIELD_RE, QID_RE, TRACK_RE

#: (sigil, directive key) for the three tags that schedule something. Beats
#: schedule; direction does not (spec 2026-08-04 §3), and the message has to
#: name the token it objected to — the tag capture is deliberately loose, and
#: guardrail prose is English sentences, so "-- never arch" harvests as a close
#: tag with slug "-" (final review, Minor 6).
_SCHEDULE_SIGILS = (("+", "opens"), ("-", "closes"), ("!", "clues"))

#: Beats that open with one of these read as instructions to the writer, not
#: as something the reader watches happen (spec 2026-08-06 §5.1). Advisory
#: only, and deliberately grammar rather than judgment: the other two tells
#: the craft document teaches — an abstraction as subject, a verb that is not
#: an action — occur in perfectly good beats, and a checker for them would
#: fire on innocent lines. Same reasoning that keeps reveal-detection an LLM
#: judgment on inspector-fairplay instead of a name-grep.
_DIRECTIVE_OPENERS = frozenset({
    "Plant", "Keep", "Save", "Show", "Do", "Don't", "Avoid", "Ensure",
    "Establish", "Introduce", "Reveal", "Treat", "Let", "Leave", "Use",
    "Make",
})

_OPENER_RE = re.compile(r"^\s*(?P<word>[A-Za-z']+)")

# The three kinds a chapter may end on (spec 2026-08-12 §3). Engine-level rather
# than genre-level: these name shapes of ending, not cozy conventions.
CLOSING_KINDS = ("cliffhanger", "irony", "promise of action")


def directive_advisories(beats: list) -> list:
    """Non-blocking notes for beats shaped like directions to the writer."""
    out = []
    for n, beat in enumerate(beats, 1):
        m = _OPENER_RE.match(beat["text"])
        if m and m.group("word") in _DIRECTIVE_OPENERS:
            out.append(
                f"directive-shaped-beat: beat {n} opens with "
                f"\"{m.group('word')}\", which addresses the writer rather "
                f"than describing what happens. If it is about how the prose "
                f"should read it belongs in `## Guardrails`; if it is about "
                f"where chapters fall, in `## Chapter Direction`. Advisory — "
                f"nothing blocks on it.")
    return out


def check_story(story_text: str, cut_plan_text: str,
                job_ids: list, clue_ids: list) -> dict:
    """Named findings over the story and its cut plan.

    job_ids and clue_ids are injected rather than looked up so this function
    holds no genre or series knowledge — the engine's location-agnostic rule.
    """
    blocking: list[str] = []
    notes: list[str] = []

    beats = parse_story(story_text)
    questions = parse_questions(story_text)
    chapters = parse_cut_plan(cut_plan_text)

    known_jobs, known_clues = set(job_ids), set(clue_ids)
    planted: set = set()
    opened: set = set()
    closed: set = set()

    # Beat numbers are optional, but a WRONG one is worse than none: the cut plan's
    # `Beats: 22-25` ranges are positional, so an author reading a stale number off
    # the page and writing it into a range silently hands beats to the wrong chapter.
    # Numbering is all-or-nothing per file — a half-numbered story is the state in
    # which a stale number is most likely to be trusted.
    numbered = [n for n, b in enumerate(beats, 1) if b["num"] is not None]
    if numbered:
        for n, beat in enumerate(beats, 1):
            if beat["num"] is None:
                blocking.append(
                    f"unnumbered-beat: beat {n} (line {beat['line']}) carries no "
                    f"[number] while {len(numbered)} other beats do — renumber the "
                    f"file with `story_cut.py number NN`")
            elif beat["num"] != n:
                blocking.append(
                    f"misnumbered-beat: the beat on line {beat['line']} is written "
                    f"[{beat['num']}] but sits at position {n} — a cut plan range "
                    f"built from the written number would claim the wrong beats; "
                    f"renumber with `story_cut.py number NN`")

    # Setting and chapter frames are cut-level, all-or-nothing per plan (spec
    # 2026-08-12 §5.1). Checking each chapter independently would make a
    # half-adopted book the quiet default: the chapters that were filled in are
    # governed and the rest silently return the ending to the drafter.
    adopted = any(ch["settings"] or ch["opening"] or ch["closing"]
                  for ch in chapters)
    if adopted:
        for ch in chapters:
            held = set(ch["beats"])
            seen: set = set()
            for s in ch["settings"]:
                for n in s["beats"]:
                    if n not in held:
                        blocking.append(
                            f"setting-outside-chapter: ch {ch['num']:02d} has a "
                            f"setting covering beat {n}, which this chapter does "
                            f"not hold — a chapter boundary moved and the setting "
                            f"ranges did not move with it; repair cut-plan.md")
                    elif n in seen:
                        blocking.append(
                            f"overlapping-setting: ch {ch['num']:02d} has two "
                            f"settings covering beat {n}, so where it happens is "
                            f"ambiguous")
                    seen.add(n)
            for n in sorted(held - seen):
                blocking.append(
                    f"beat-without-setting: ch {ch['num']:02d} beat {n} is covered "
                    f"by no setting — every beat must say where it happens, or the "
                    f"drafter picks the room")
            if not ch["opening"]:
                blocking.append(
                    f"missing-chapter-frame: ch {ch['num']:02d} has no Opening — "
                    f"other chapters in this plan carry one, and adoption is "
                    f"all-or-nothing")
            if not ch["closing"]:
                blocking.append(
                    f"missing-chapter-frame: ch {ch['num']:02d} has no Closing — "
                    f"a missing ending hands the last line back to the drafter")
            elif ch["closing"]["kind"] not in CLOSING_KINDS:
                blocking.append(
                    f"unknown-closing-kind: ch {ch['num']:02d} ends on "
                    f"'{ch['closing']['kind']}', which is not one of "
                    f"{', '.join(CLOSING_KINDS)}")

    # The same forgery the directive check below guards against, one level
    # up: emit_outline writes Opening and Chapter Summary VERBATIM at column
    # 0 (`"### Opening\n" + ch["opening"]`), and Compress with a bare "- "
    # prefix it adds itself (`"Compress:\n- " + ch["compress"]`) — Closing is
    # excluded because it always opens on a fixed, capitalised CLOSING_KINDS
    # word, which can never parse as a wiring field. An authored
    # `- **Closes:** q-bogus` in any of these three fields becomes a wiring
    # line the cut never wrote, and tension_check fires phantom-answer on a
    # chapter whose footer says no such thing (final review, Minor). Reuses
    # the exact FIELD_RE/TRACK_RE check and message the directive guard below
    # uses — one mechanism, not a second one for cut-plan fields.
    for ch in chapters:
        for label, emitted in (
                ("Opening", ch["opening"]),
                ("Chapter Summary", ch["summary"]),
                ("Compress", f"- {ch['compress']}" if ch["compress"] else "")):
            if emitted and (FIELD_RE.match(emitted) or TRACK_RE.match(emitted)):
                blocking.append(
                    f"wiring-shaped-directive: ch {ch['num']:02d} {label} reads "
                    f"'{emitted}', which the outline parser would read as a "
                    f"wiring field or a Track Movement row rather than as prose "
                    f"— the cut writes those itself. Reword the note so it does "
                    f"not begin with **Because:**/**Opens:**/**Closes:**/"
                    f"**Carries:**/**Hook:** or **<letter>:**")

    # Texture items are emitted the same way, one bullet each — same forgery,
    # same finding. Reusing `wiring-shaped-directive` rather than minting a
    # texture-specific name is deliberate: the failure is identical, and the
    # roster stays at twenty-three.
    for ch in chapters:
        for item in ch["texture"]:
            emitted = f"- {item}"
            if FIELD_RE.match(emitted) or TRACK_RE.match(emitted):
                blocking.append(
                    f"wiring-shaped-directive: ch {ch['num']:02d} Texture reads "
                    f"'{emitted}', which the outline parser would read as a "
                    f"wiring field or a Track Movement row rather than as prose "
                    f"— the cut writes those itself. Reword the item so it does "
                    f"not begin with **Because:**/**Opens:**/**Closes:**/"
                    f"**Carries:**/**Hook:** or **<letter>:**")

    # The TRACK-shaped nested item never reaches the loop above, and this is the
    # only place it can be caught. `penny_story.parse_cut_plan` tests its
    # track-row pattern BEFORE its nested-block branches, so an item written
    # `  - **R:** a phantom romance` under `- **Texture:**` — or under
    # `- **Setting:**` — is not a nested item at all by the time the dict exists:
    # it has been reclassified into `ch["tracks"]`, where it is
    # indistinguishable from a genuine track row. Left alone it reaches
    # `### Track Movement`, and worse, `tension_check` counts every non-"none"
    # track toward `obligations.max_per_chapter` — so an allocated image
    # silently becomes an OBLIGATION, the one thing this layer forbids (spec
    # 2026-08-27 §4.2). The scan therefore runs over the raw text, where the
    # indentation is still visible.
    #
    # INDENTATION is the whole rule, and the guard deliberately does not model
    # where a nested block ends. `emit_outline` writes Track Movement rows at
    # column 0 and every genuine track row in the repo sits at column 0, so an
    # indented track-shaped line inside a chapter block can never be a row the
    # cut would have written — whichever field it is nested under, including
    # fields added later. The previous attempt re-derived `parse_cut_plan`'s
    # own bookkeeping with a state machine and diverged from it: a blank line, a
    # whitespace-only line, an HTML comment or a stray prose line between the
    # declaration and the forged row are all ignored by that parser and all
    # closed the block for the guard, reopening the bug — and Setting was never
    # covered at all. Indentation makes the question moot.
    #
    # TRACK_RE only, deliberately: a FIELD-shaped nested item (`**Closes:**`) is
    # matched by neither of that parser's field nor track patterns, so it still
    # lands in `ch["texture"]` and the loop above already refuses it. The two
    # guards partition the shapes; checking both here would report one line
    # twice. Same finding name as the two loops above — one failure, one name,
    # and the roster stays at twenty-three.
    #
    # `_CUT_FIELD_RE`/`_CUT_CLOSING_RE` widen the same rule to the OTHER half of
    # the field table (spec 2026-08-29). Both are anchored at `^\s*` in
    # `parse_cut_plan`, tested BEFORE that parser's nested-item branches, so a
    # line written as a nested item under `- **Texture:**` or `- **Setting:**`
    # — `  - **Summary:** The potter did it, obviously.` — is not read as an item
    # all: it is read as the CHAPTER's own field and silently overwrites the
    # value the author actually wrote. Four of the five keys (`Summary`,
    # `Compress`, `Opening`, `Closing`) raise no finding anywhere else; `Beats`
    # raises `beats-without-chapter` findings that name the symptom (a beat
    # uncovered or out of range) and never the cause. Same indentation
    # discriminator as the TRACK_RE guard above, for the same reason: a genuine
    # field or closing line is never indented — `chapter-cutter` writes them at
    # column 0 and `emit_outline`/`parse_cut_plan` both read them there — so the
    # guard does not have to model where a nested block begins or ends.
    num = None
    for raw in cut_plan_text.splitlines():
        m = _CUT_CHAPTER_RE.match(raw)
        if m:
            num = int(m.group("num"))
            continue
        if num is None or not raw[:1].isspace():
            continue
        if TRACK_RE.match(raw):
            blocking.append(
                f"wiring-shaped-directive: ch {num:02d} indents "
                f"'{raw.strip()}' inside its chapter block, and the plan's "
                f"own parser reads a **<letter>:** row as a Track Movement "
                f"row wherever it sits — it would become a track the cut "
                f"never wrote, and tension_check counts tracks toward this "
                f"chapter's obligation cap. Reword the item so it does not "
                f"begin with **<letter>:** — or, if it was meant as a Track "
                f"Movement row, unindent it to column 0, where the cut "
                f"writes the chapter's real Track Movement rows")
            continue
        fm = _CUT_FIELD_RE.match(raw)
        cm = _CUT_CLOSING_RE.match(raw)
        if fm or cm:
            key = fm.group("key") if fm else f"Closing ({cm.group('kind').strip()})"
            blocking.append(
                f"wiring-shaped-directive: ch {num:02d} indents "
                f"'{raw.strip()}' inside its chapter block, and the plan's "
                f"own parser reads a **{key}:** line as THIS CHAPTER's own "
                f"{key} field wherever it sits — it would silently overwrite "
                f"the chapter's authored {key}. Reword the line so it does "
                f"not begin with **{key}:** — or, if it was meant as the "
                f"chapter's real {key}, unindent it to column 0, where the "
                f"cut reads the chapter's real fields")

    for n, beat in enumerate(beats, 1):
        for slug in beat["strands"]:
            if not SLUG_RE.match(slug):
                blocking.append(
                    f"unknown-strand: beat {n} tags @{slug}, which breaks the "
                    f"slug contract ^[a-z0-9][a-z0-9-]*$ — strand ids become "
                    f"filenames on the strand pages")
        for slug in beat["jobs"]:
            if slug not in known_jobs:
                blocking.append(
                    f"unknown-job: beat {n} tags #{slug}, which the active "
                    f"genre's macro-structure does not declare")
        for cid in beat["clues"]:
            if cid not in known_clues:
                blocking.append(
                    f"unknown-clue: beat {n} tags !{cid}, which is not in the "
                    f"whodunit ledger")
            planted.add(cid)
        for qid in beat["opens"]:
            opened.add(qid)
        for qid in beat["opens"] + beat["closes"]:
            if not QID_RE.match(qid):
                blocking.append(
                    f"unknown-question: beat {n} names '{qid}', which is not a "
                    f"question id (expected q-…)")
            elif qid not in questions:
                blocking.append(
                    f"unknown-question: beat {n} names {qid}, absent from the "
                    f"## Questions block — the wiring line needs its prose")
        for qid in beat["closes"]:
            if qid not in opened:
                blocking.append(
                    f"orphan-question: beat {n} closes {qid}, which no earlier "
                    f"beat opens")
        for qid in beat["closes"]:
            closed.add(qid)

    used_strands = {s for b in beats for s in b["strands"]}
    used_jobs = {j for b in beats for j in b["jobs"]}

    for heading in ("Chapter Direction", "Guardrails"):
        for d in parse_directives(story_text, heading):
            where = f"{heading} line {d['line']}"
            for slug in d["strands"]:
                if not SLUG_RE.match(slug):
                    blocking.append(
                        f"unknown-strand: {where} tags @{slug}, which breaks "
                        f"the slug contract ^[a-z0-9][a-z0-9-]*$")
                elif slug not in used_strands:
                    blocking.append(
                        f"orphan-direction: {where} is scoped to @{slug}, "
                        f"which no beat tags — the note would be rendered "
                        f"nowhere and read by no one")
            for slug in d["jobs"]:
                if slug not in known_jobs:
                    blocking.append(
                        f"unknown-job: {where} tags #{slug}, which the active "
                        f"genre's macro-structure does not declare")
                elif slug not in used_jobs:
                    blocking.append(
                        f"orphan-direction: {where} is scoped to #{slug}, "
                        f"which no beat carries — the note would be rendered "
                        f"nowhere and read by no one")
            tokens = [f"'{sigil}{slug}'"
                      for sigil, key in _SCHEDULE_SIGILS for slug in d[key]]
            if tokens:
                blocking.append(
                    f"misplaced-schedule-tag: {where} carries "
                    f"{', '.join(tokens)}, which schedules nothing here — "
                    f"direction scopes with @strand and #job only")
            # The emitter writes an authored guardrail as `- {text}` straight
            # into the chapter block, and penny_wiring matches FIELD_RE/TRACK_RE
            # against EVERY line of that block, not only the wiring section. So
            # a note reading `- **Closes:** q-bogus` becomes a wiring field the
            # cut never wrote, and tension_check fires phantom-answer on a
            # chapter whose footer says no such thing — with nothing to tell the
            # author why. The deterministic layer's own output must not be
            # forgeable from authored prose (final review, Important 2).
            emitted = f"- {d['text']}"
            if FIELD_RE.match(emitted) or TRACK_RE.match(emitted):
                blocking.append(
                    f"wiring-shaped-directive: {where} reads '{emitted}', which "
                    f"the outline parser would read as a wiring field or a "
                    f"Track Movement row rather than as prose — the cut writes "
                    f"those itself. Reword the note so it does not begin with "
                    f"**Because:**/**Opens:**/**Closes:**/**Carries:**/"
                    f"**Hook:** or **<letter>:**")

    # The converse of orphan-question, and the ONLY place it can be caught.
    # `tension_check`'s dropped-question fires on a question that is neither
    # closed nor carried, but the emitter carries every live question into
    # every chapter through the last one — so downstream, an abandoned question
    # is indistinguishable from a deliberate series seed and is caught by
    # nothing at all (final review, Important 3).
    #
    # The rule is "at most one", not "none", because ONE unclosed question is
    # structural, not sloppy: the wiring format requires every chapter to hook
    # a question that is open at it (tension_check's broken-hook), and the final
    # chapter can only hook something the book has not closed. The engine's own
    # canonical clean outline (tests/fixtures/outlines/wired-clean.md) ends
    # exactly this way — one seed carried past the end. A SECOND unclosed
    # question is a dropped thread wearing the seed's clothes, and this is the
    # last place anything can say so. No waivers at this level (spec §8): close
    # it in a beat, or accept it as the seed and close the others.
    unclosed = sorted(opened - closed)
    if len(unclosed) > 1:
        blocking.append(
            f"unclosed-question: {', '.join(unclosed)} are all opened by a beat "
            f"and closed by none — a book carries at most one question past its "
            f"end (the seed its last chapter hooks); the rest read downstream as "
            f"deliberate carries, so nothing else will catch them")
    elif not unclosed and opened:
        notes.append(
            "every question the story opens is also closed, so the last "
            "chapter has no live question to hook — tension_check will report "
            "broken-hook on it. Leave one question open as the book's seed, or "
            "expect that finding.")

    for cid in clue_ids:
        if cid not in planted:
            blocking.append(
                f"unscheduled-clue: ledger clue [{cid}] is planted by no beat — "
                f"an unplanted clue is an unfair reveal")

    owners: dict = {}
    for ch in chapters:
        for idx in ch["beats"]:
            owners.setdefault(idx, []).append(ch["num"])
    for n in range(1, len(beats) + 1):
        who = owners.get(n, [])
        if not who:
            blocking.append(
                f"beats-without-chapter: beat {n} lands in no chapter — the cut "
                f"plan must cover every beat")
        elif len(who) > 1:
            blocking.append(
                f"duplicate-beat: beat {n} is claimed by chapters {who} — one "
                f"beat, one home")
    for idx in sorted(owners):
        if idx < 1 or idx > len(beats):
            blocking.append(
                f"beats-without-chapter: the cut plan claims beat {idx} but the "
                f"story has only {len(beats)}")

    notes.extend(directive_advisories(beats))

    return {"blocking": blocking, "notes": notes}


def _carried(upto_index, opened_by, closed_by):
    """Question ids opened at or before this chapter and not yet closed."""
    live = []
    for qid, opened_at in opened_by.items():
        if opened_at <= upto_index and closed_by.get(qid, 10 ** 9) >= upto_index:
            live.append(qid)
    return sorted(live)


# (ledger key, bullet label) — in the order the reference hand-authored outline
# (book 01) lists them. `central_deception` and `true_motive` are two distinct
# ledger keys (not one merged "central deception / motive" line as book 01's
# outline reads by hand) — kept separate here since the emitter must not invent
# a combined value neither key actually holds.
_SOLUTION_FIELDS = (
    ("culprit", "culprit"),
    ("victim", "victim"),
    ("central_deception", "central deception"),
    ("true_motive", "true motive"),
    ("murder_method", "murder method"),
    ("murder_location", "murder location"),
)


def _solution_block(solution: dict) -> str:
    """The `## Solution` block, derived from the whodunit ledger (spec §5.2).

    Heading is deliberately UNLABELLED — `outline_check._SOLUTION_RE` accepts
    a bare `## Solution` (label is optional) but blocks an empty label after a
    colon, so a bare heading is the one shape that can never trip that half of
    the predicate. A bullet whose ledger key is absent is omitted outright,
    never emitted empty — an absent key is not the same claim as an empty one.
    No `## Threads` block: nothing downstream requires it (spec §5.2 table).
    """
    lines = ["## Solution"]
    for key, label in _SOLUTION_FIELDS:
        value = solution.get(key)
        if not value:
            continue
        # Ledger prose (central_deception) is often an authored multi-line
        # YAML block scalar; a bullet's value must stay on one line.
        text = " ".join(str(value).split())
        lines.append(f"- {label}: {text}")

    grid = solution.get("alibi_grid")
    suspects: list = []
    if isinstance(grid, list):
        for entry in grid:
            if isinstance(entry, dict) and entry.get("suspect"):
                name = str(entry["suspect"]).strip()
                if name and name not in suspects:
                    suspects.append(name)
    if suspects:
        lines.append(f"- suspects: {', '.join(suspects)}")

    return "\n".join(lines) + "\n"


def emit_outline(story_text: str, cut_plan_text: str, questions: dict,
                 ledger: dict, *, reveal_chapter: int, guardrails: str,
                 job_titles: dict, solution: dict) -> str:
    """Expand an approved cut plan into packet-format chapter blocks (spec §5.2).

    `solution` is the whodunit ledger dict (culprit, victim, central_deception,
    true_motive, murder_method, murder_location, alibi_grid, …), resolved by
    `main()` exactly as `reveal_chapter`/`guardrails`/`job_titles` already are —
    this function still does no I/O and holds no genre or series knowledge.
    """
    beats = parse_story(story_text)
    chapters = parse_cut_plan(cut_plan_text)
    notes = parse_directives(story_text, "Guardrails")

    opened_by, closed_by, beat_chapter = {}, {}, {}
    for ch in chapters:
        for idx in ch["beats"]:
            beat_chapter[idx] = ch["num"]
    for n, beat in enumerate(beats, 1):
        # A beat no chapter claims resolves to chapter 0. Chapter 0 is not a
        # real chapter, so a question tagged on that beat must not enter
        # opened_by/closed_by at all — left in, it would satisfy
        # `opened_at <= upto_index` from chapter 1 onward and read as
        # "carried" everywhere. check_story refuses this case upstream, but
        # emit_outline must not depend on a caller running it first.
        owner = beat_chapter.get(n, 0)
        if owner == 0:
            continue
        for qid in beat["opens"]:
            opened_by.setdefault(qid, owner)
        for qid in beat["closes"]:
            closed_by[qid] = owner

    def qline(qid):
        prose = questions.get(qid, "")
        return f"{qid} — {prose}" if prose else qid

    out = [_solution_block(solution)]
    high_water = 0
    seen_strands: set = set()
    for pos, ch in enumerate(chapters):
        mine = [beats[i - 1] for i in ch["beats"] if 1 <= i <= len(beats)]
        # Accumulate a running high-water mark across chapters as we iterate,
        # so a chapter with no beats of its own (or an out-of-order one)
        # inherits every strand seen so far rather than resetting to none.
        high_water = max(high_water, max(ch["beats"], default=0))
        seen_strands |= {s for i in range(1, high_water + 1)
                         for s in (beats[i - 1]["strands"] if i <= len(beats) else [])}
        strands_so_far = sorted(seen_strands)
        opens = [q for b in mine for q in b["opens"]]
        closes = [q for b in mine for q in b["closes"]]
        jobs = []
        for b in mine:
            for j in b["jobs"]:
                if j not in jobs:
                    jobs.append(j)

        out.append(f"## Chapter {ch['num']:02d} — {ch['title']}\n")
        out.append("### Chapter Summary\n" + ch["summary"] + "\n")
        if ch["settings"]:
            # Chapter-local beat numbers, matching ### Required Beats, which
            # already lists this chapter's beats rather than the book's. Book
            # positions here would send the drafter to the wrong line. Rank
            # within the chapter's own (possibly non-contiguous) Beats set,
            # not an arithmetic offset from its minimum — a chapter holding
            # book beats {3,5,6} has only three local beats, so an offset
            # would render a local number ("4") that doesn't exist.
            ordered = sorted(ch["beats"])
            def _local(ns):
                loc = sorted(ordered.index(n) + 1 for n in ns)
                return (f"{loc[0]}-{loc[-1]}"
                        if len(loc) > 1 and loc == list(range(loc[0], loc[-1] + 1))
                        else ",".join(str(n) for n in loc))
            out.append("### Setting\n" + "\n".join(
                f"- Beats {_local(s['beats'])} — {s['text']}"
                for s in ch["settings"]) + "\n")
        out.append("### Chapter Purpose\n"
                   + "\n".join(f"- {job_titles.get(j, j)}" for j in jobs) + "\n")

        carried = _carried(ch["num"], opened_by, closed_by)
        start = [f"- Chapter {ch['num']:02d} is forced by ch {chapters[pos - 1]['num']:02d}."] \
            if pos else ["- This chapter opens the book."]
        start += [f"- Carried in: {qline(q)}" for q in carried if q not in opens]
        out.append("### Starting State\n" + "\n".join(start) + "\n")

        end = [f"- {mine[-1]['text']}"] if mine else []
        end += [f"- Closes: {qline(q)}" for q in closes]
        end += [f"- Hook question remains: {qline(q)}" for q in opens if q not in closes]
        out.append("### Ending State\n" + "\n".join(end) + "\n")

        out.append("### Reader-Facing Shape\nPrimary anchor:\n"
                   + (f"- {mine[0]['text']}\n" if mine else "")
                   + "\nCompress:\n- " + ch["compress"] + "\n")

        # The positive half of the Compress line above it (spec 2026-08-27
        # §4.2): what this chapter MAY spend, allocated once across the whole
        # book so no image is spent twice. A resource, not an obligation —
        # nothing downstream checks that it was spent, and map_check has no
        # `unscheduled-texture` on purpose.
        if ch["texture"]:
            out.append("### Texture\n"
                       + "\n".join(f"- {t}" for t in ch["texture"]) + "\n")

        if ch["opening"]:
            out.append("### Opening\n" + ch["opening"] + "\n")
        if ch["closing"]:
            # The kind becomes a prose lead-in rather than a parenthetical key:
            # the emitted block is read by agents and by the reader's copy, never
            # parsed back into the cut plan.
            kind = ch["closing"]["kind"]
            out.append(f"### Closing\n{kind[0].upper() + kind[1:]} — "
                       f"{ch['closing']['text']}\n")

        out.append("### Required Beats\n"
                   + "\n".join(f"- {b['text']}" for b in mine) + "\n")

        clues = [c for b in mine for c in b["clues"]]
        out.append("### Clues and Plants\n" + ("\n".join(
            f"- [{c}] {ledger.get(c, c)}" for c in clues)
            or "- No ledger clue is scheduled for this chapter.") + "\n")

        # Both reveal-relative lines (here and in Guardrails) must know which
        # side of the reveal this chapter is on. Emitted unconditionally they
        # are false in every chapter past `reveal_chapter` — and this block is
        # the drafter's instruction, so an endgame chapter was being told the
        # solution is still unknown (OF-122). The two lines take different
        # boundaries deliberately: the solution IS known in the reveal chapter
        # (that is what the reveal is), while "do not resolve before ch NN" is
        # still true in ch NN — it says where the reveal belongs, and it
        # belongs here.
        if ch["num"] < reveal_chapter:
            knowledge = (f"\nNot yet known:\n- The solution, until chapter "
                         f"{reveal_chapter:02d}.\n")
        elif ch["num"] == reveal_chapter:
            knowledge = "\nRevealed here:\n- The solution is revealed in this chapter.\n"
        else:
            knowledge = (f"\nKnown from here on:\n- The solution, known since "
                         f"chapter {reveal_chapter:02d}.\n")
        out.append("### Character Knowledge\nOn the page so far:\n"
                   + "\n".join(f"- {s}" for s in strands_so_far) + "\n"
                   + knowledge)

        # Scoped to THIS chapter's own beats, never to `seen_strands` — that
        # is a running high-water mark for Character Knowledge, and reusing it
        # would follow a character's note into chapters she is absent from.
        mine_strands = {s for b in mine for s in b["strands"]}
        mine_jobs = {j for b in mine for j in b["jobs"]}
        authored = [d["text"] for d in notes
                    if (not d["strands"] and not d["jobs"])
                    or (set(d["strands"]) & mine_strands)
                    or (set(d["jobs"]) & mine_jobs)]

        # Past the reveal the prohibition inverts: the danger is no longer an
        # early resolution but hedged, pre-reveal prose in the endgame.
        reveal_line = (
            f"Do not resolve the mystery before chapter {reveal_chapter:02d}."
            if ch["num"] <= reveal_chapter else
            f"The mystery resolved in chapter {reveal_chapter:02d}; "
            "do not write it as still open.")
        out.append("### Guardrails\n"
                   + "".join(f"- {a}\n" for a in authored)
                   + "- " + guardrails.strip()
                   + f"\n- {reveal_line}\n")

        wiring = []
        # A question this chapter closes is never also "carried" by it — the
        # format never produces close-and-carry in the same chapter (0/28 in
        # book-01's outline); a question this chapter opens still carries
        # (28/28 do), so only `closes` is excluded here, not `opens`.
        still_live = [q for q in carried if q not in closes]
        # The Hook must name a question tension_check can see as OPEN at this
        # chapter: opened at or before it (`open_ch[hook] <= num`) and not
        # already closed (`closed_ch[hook] > num`). A chapter that opens
        # nothing still has one — whatever it carries — so falling back to the
        # first live carried question is what stops `broken-hook` firing on
        # every chapter after the first (final review, Critical 2).
        hook_q = opens[0] if opens else (still_live[0] if still_live else None)
        if hook_q:
            wiring.append(f"- **Hook:** {qline(hook_q)}")
        # `tension_check`'s orphan-chapter accepts exactly two forms: the
        # literal `opening` (chapter 1 only) or `ch NN` naming an earlier
        # chapter. Chapter one got NEITHER before this — it had no Because line
        # at all, so every cut book opened with an orphan-chapter finding.
        wiring.append(f"- **Because:** ch {chapters[pos - 1]['num']:02d}"
                      if pos else "- **Because:** opening")
        wiring += [f"- **Opens:** {qline(q)}" for q in opens]
        wiring += [f"- **Closes:** {qline(q)}" for q in closes]
        wiring += [f"- **Carries:** {q}" for q in still_live]
        out.append("### Chapter Structure\n" + "\n".join(wiring) + "\n")

        out.append("### Track Movement\n" + "\n".join(
            f"- **{k}:** {v}" for k, v in ch["tracks"].items()) + "\n")

    return "\n".join(out).rstrip() + "\n"


def body_sha(text: str) -> str:
    """sha256 of the outline body, frontmatter excluded.

    Excluding frontmatter is what lets the stamp describe the prose without
    describing itself — a hash that covered its own field could never match.
    """
    return hashlib.sha256(strip_frontmatter(text).encode("utf-8")).hexdigest()


def stamp_outline(body: str, *, story_sha: str, cut_sha: str, book: str,
                  total_chapters: int, whodunit_sha: "str | None" = None) -> str:
    """The cut-produced outline's frontmatter.

    `book:` and `total_chapters:` are not decoration: `book_status.py`'s
    `_total_chapters_with_reason` reads `total_chapters` and blanks every
    per-chapter row without it, and `tension_check`'s chapter-coverage check
    falls back to `len(chapters)` (so a gap can never be seen) without it. The
    cut knows the count — it just cut them (final review, Important 6).

    `built_from_book-NN` is the whodunit fingerprint `plot_stage`'s `cut` stage
    demands (`_UPSTREAM["cut"] = ["chapters", "whodunit"]`). Written here rather
    than by a `plot_stage stamp` call in the runbook because the cut is the one
    thing that knows the cut actually happened; a runbook step can be skipped,
    and the stamp would then claim a cut that never ran (final review,
    Important 5).
    """
    out_sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
    whodunit_line = (f"built_from_book-{book}: {whodunit_sha}\n"
                     if whodunit_sha else "")
    return ("---\n"
            f"book: {book}\n"
            f"total_chapters: {total_chapters}\n"
            f"built_from_story: {story_sha}\n"
            + whodunit_line
            + f"built_from_cut: {cut_sha}\n"
            f"cut_output_sha256: {out_sha}\n"
            "---\n\n" + body)


def expand_in_place_refusal(outline_text: str) -> "str | None":
    """None when `/expand-outline` may write into this outline in place; a
    named refusal when the outline was produced by the cut (spec 2026-08-03
    §12 ruling).

    A cut-produced outline is regenerated from story.md, never edited
    upstream of it — expanding a stub in place there would silently make
    story.md and outline.md disagree, the exact drift that retired the
    outline's earlier staging layer in the first place. A legacy outline with no
    `cut_output_sha256` stamp (hand-authored or scaffolded, e.g. book 01) was
    never cut from a story.md and keeps working exactly as before.
    """
    if parse_frontmatter(outline_text).get("cut_output_sha256"):
        return ("cut-owned-outline: this outline carries cut_output_sha256 — "
                "it was produced by the cut from story.md and must not be "
                "edited upstream of it. Edit story.md's beats and re-run the "
                "cut instead of expanding in place.")
    return None


def recut_refusal(existing_outline_text: str) -> "str | None":
    """None when re-cutting is safe; a named finding when it is not (spec §7)."""
    meta = parse_frontmatter(existing_outline_text)
    recorded = meta.get("cut_output_sha256")
    if not recorded:
        return ("outline-modified-since-cut: the outline carries no "
                "cut_output_sha256, so it was not produced by the cut — "
                "refusing to overwrite hand-authored chapter work")
    if body_sha(existing_outline_text) != recorded:
        return ("outline-modified-since-cut: the outline has been edited since "
                "the cut wrote it — re-cutting would discard that work. Edit "
                "story.md and cut a fresh book, or keep the hand edits")
    return None


def _job_ids_and_titles(root=None):
    """(ids, id->title) from the active genre's macro-structure, or ([], {}).

    `root` is threaded through because `book_status.py` calls this with an
    injected series root: it reports on a book without being run from inside
    it, and resolving the genre from cwd would read some other series' pack.
    """
    path = penny_genre.macro_structure(root=root)
    if path is None or not path.is_file():
        return [], {}
    jobs = parse_jobs(path.read_text(encoding="utf-8"))
    return [jid for jid, _ in jobs], {jid: title for jid, title in jobs}


#: The ledger collections that schedule a clue by chapter. BOTH are real
#: obligations: `penny_whodunit.clues_by_chapter` and `packet_assemble` merge
#: the two, so a `!rh-…` tag that only `clue_schedule` knew about was refused
#: `unknown-clue` even though the packet would have scheduled it (final review
#: C1, second half).
_CLUE_COLLECTIONS = ("clue_schedule", "red_herrings")


def _ledger(root, book):
    p = root / "series" / "whodunit" / f"book-{book}.yaml"
    if not p.is_file():
        return {}, None, p
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    clues = {}
    for key in _CLUE_COLLECTIONS:
        for c in (data.get(key) or []):
            if isinstance(c, dict) and c.get("id"):
                # Same fallback chain packet_assemble.py uses, so the outline's
                # "Clues and Plants" line and the packet's read alike: a red
                # herring carries `misleads_toward:` where a clue carries
                # `description:`.
                clues[c["id"]] = (c.get("description") or c.get("misleads_toward")
                                  or c["id"])
    return clues, data, p


_COLLECTION_RE = re.compile(
    rf"^(?P<indent>[ \t]*)(?:{'|'.join(_CLUE_COLLECTIONS)}):\s*(?:#.*)?$")
_ITEM_START_RE = re.compile(r"^(?P<indent>[ \t]*)-\s")
# `id:`/`plant_chapter:` may be the FIRST key on the dash's own line
# ("  - id: x") or a later continuation line ("    id: x") — YAML mappings are
# unordered, so either key can lead. Both alternatives are anchored at column 0
# with no other content before them, so a value that merely CONTAINS "id:" or
# "plant_chapter:" later in the line (e.g. inside a quoted description) never
# matches: the key must be the first thing on the line, dash or no dash.
_ID_ANY_RE = re.compile(r"^(?:[ \t]*-[ \t]*|[ \t]*)id:\s*(?P<id>[^\s#]+)")
_PLANT_ANY_RE = re.compile(
    r"^(?P<prefix>[ \t]*-[ \t]*|[ \t]*)plant_chapter:\s*(?P<value>[^\s#]+)(?P<trail>.*)$")

# The INLINE FLOW-MAPPING item form — `  - { id: clue-x, plant_chapter: 5, … }`,
# the shape this repo's own whodunit-ledger fixtures actually use. The
# block form's line walk cannot see keys that never start a line, so this form
# is matched whole and edited inside its braces (final review, Important 4).
_FLOW_ITEM_RE = re.compile(r"^(?P<pre>[ \t]*-[ \t]*\{)(?P<body>[^}]*)(?P<post>\}.*)$")
_FLOW_ID_RE = re.compile(r"(?:^|,)\s*id\s*:\s*(?P<id>[^,}\s]+)")
_FLOW_PLANT_RE = re.compile(r"(?P<lead>(?:^|,)\s*plant_chapter\s*:\s*)(?P<val>[^,\s]*)")


def _rewrite_plant_chapters(ledger_text: str, updates: dict) -> "tuple[str, list]":
    """Rewrite only `plant_chapter:` for ids in `updates` (id -> new chapter
    number), across BOTH `clue_schedule` and `red_herrings` — byte-identical
    everywhere else. Returns `(new_text, missing_ids)`; `missing_ids` lists any
    update id that could not be located in either collection's text at all, so
    a caller can refuse rather than silently drop it.

    **`plant_chapter` is the key, not `chapter`.** Every consumer reads
    `plant_chapter`: `penny_whodunit._plant_chapter` (and through it
    `clues_by_chapter`, which feeds `packet_assemble` and `tension_check`'s
    overloaded-chapter), `fairplay_check`, and `lmstudio_draft_chapter`. Writing
    a `chapter:` key beside a stale `plant_chapter:` left the outline naming a
    clue the packet reported as "None" and `fairplay_check` blocking the lock.

    The whodunit ledger is a hand-authored showrunner artifact: comments,
    anchors, quoting, and bare yes/no scalars all carry meaning that
    `yaml.safe_load` → `yaml.safe_dump` silently destroys on write. So the
    ledger is never round-tripped through PyYAML on write — only read with
    `safe_load` (in `_ledger`). This is a line-walk instead, and it operates
    on each list ITEM'S SPAN, not on the shape of any one line: `id:` and
    `plant_chapter:` can appear in either order (or with other keys between
    them), because YAML mappings are unordered. Only lines inside a
    `clue_schedule:`/`red_herrings:` block are ever considered, so a
    `plant_chapter:` key belonging to some other structure in the file is
    never touched — and `alibi_grid`'s own `chapter:` keys are out of reach by
    construction.

    Two item shapes are supported. In the BLOCK form a found `plant_chapter:`
    line has only its value replaced — indentation, any dash prefix, and any
    trailing inline comment are preserved verbatim; an item with no
    `plant_chapter:` key gets one inserted right after its first line, at one
    indent level deeper than the dash. In the INLINE FLOW-MAPPING form
    (`- { id: x, plant_chapter: 5, … }`) only the value inside the braces is
    replaced, the rest of the line surviving byte-for-byte; an entry with no
    `plant_chapter` key gets one appended just inside the closing brace.
    """
    if not updates:
        return ledger_text, []

    lines = ledger_text.splitlines(keepends=True)
    out = list(lines)
    found: set = set()

    # Collect every collection block's item spans first, then edit bottom-up
    # across all of them: an inserted line shifts every index below it, so only
    # already-handled spans may sit below any insertion point.
    spans: list = []
    for heading_idx in range(len(lines)):
        m = _COLLECTION_RE.match(lines[heading_idx].rstrip("\n"))
        if not m:
            continue
        spans += _item_spans(lines, heading_idx, m.group("indent"))

    for s, e, item_indent in sorted(spans, reverse=True):
        item_id = None
        plant_idx = None
        flow_idx = None
        for idx in range(s, e):
            body = out[idx].rstrip("\n")
            fm = _FLOW_ITEM_RE.match(body)
            if fm:
                fid = _FLOW_ID_RE.search(fm.group("body"))
                if fid:
                    item_id, flow_idx = fid.group("id"), idx
                continue
            idm = _ID_ANY_RE.match(body)
            if idm:
                item_id = idm.group("id")
            if plant_idx is None and _PLANT_ANY_RE.match(body):
                plant_idx = idx
        if item_id is None or item_id not in updates:
            continue
        found.add(item_id)
        new_val = updates[item_id]
        if flow_idx is not None:
            body = out[flow_idx].rstrip("\n")
            eol = out[flow_idx][len(body):]
            fm = _FLOW_ITEM_RE.match(body)
            inner = fm.group("body")
            if _FLOW_PLANT_RE.search(inner):
                inner = _FLOW_PLANT_RE.sub(
                    lambda mm: f"{mm.group('lead')}{new_val}", inner, count=1)
            else:
                trimmed = inner.rstrip()
                pad = inner[len(trimmed):] or " "
                inner = (f"{trimmed}, plant_chapter: {new_val}{pad}"
                         if trimmed else f" plant_chapter: {new_val} ")
            out[flow_idx] = f"{fm.group('pre')}{inner}{fm.group('post')}{eol}"
        elif plant_idx is not None:
            body = out[plant_idx].rstrip("\n")
            eol = out[plant_idx][len(body):]
            pm = _PLANT_ANY_RE.match(body)
            out[plant_idx] = (f"{pm.group('prefix')}plant_chapter: {new_val}"
                              f"{pm.group('trail')}{eol}")
        else:
            out.insert(s + 1, f"{item_indent}  plant_chapter: {new_val}\n")

    missing = sorted(set(updates) - found)
    return "".join(out), missing


def _item_spans(lines: list, heading_idx: int, heading_indent: str) -> list:
    """`[(start, end, item_indent), …]` for the list items under one collection
    heading. Extracted so both `clue_schedule` and `red_herrings` walk the same
    code — a fork here is how the two collections drifted apart in the first
    place."""
    n = len(lines)
    start = heading_idx + 1
    item_indent = None
    end = n
    for idx in range(start, n):
        body = lines[idx].rstrip("\n")
        if not body.strip():
            continue
        cur_indent = body[:len(body) - len(body.lstrip(" \t"))]
        im = _ITEM_START_RE.match(body)
        # A line SHALLOWER than the heading always ends the block. A line at the
        # heading's OWN indent ends it only when it is not a sequence item —
        # YAML lets a sequence sit at its key's indent, and that is exactly what
        # `yaml.safe_dump` emits:
        #
        #     clue_schedule:
        #     - id: c01-…
        #
        # Treating `- ` at heading indent as the block's end found zero items in
        # every such ledger, so `_rewrite_plant_chapters` reported every clue as
        # not-found and the cut refused a partial update. safe_load reads this
        # shape happily, so the ledger validated and locked while the cut could
        # never run on it.
        if len(cur_indent) < len(heading_indent) or (
                len(cur_indent) == len(heading_indent) and not im):
            end = idx
            break
        if item_indent is None:
            if not im:
                end = idx
                break
            item_indent = im.group("indent")
        elif len(cur_indent) < len(item_indent):
            end = idx
            break
    if item_indent is None:
        return []

    spans, span_start = [], None
    for idx in range(start, end):
        body = lines[idx].rstrip("\n")
        if not body.strip():
            continue
        cur_indent = body[:len(body) - len(body.lstrip(" \t"))]
        if len(cur_indent) == len(item_indent) and _ITEM_START_RE.match(body):
            if span_start is not None:
                spans.append((span_start, idx, item_indent))
            span_start = idx
    if span_start is not None:
        spans.append((span_start, end, item_indent))
    return spans


def _check(book: str) -> int:
    """Validate story.md alone — no cut plan, no writes (spec 2026-08-06 §5).

    `beats-without-chapter` is filtered out because with no cut plan it fires
    once per beat, which is what a story mid-writing looks like, not a defect.
    Same call /book-status already made when it gave that finding to the `cut
    plan` row rather than the `story` row.

    Same rule as `book_status.py`'s `_story_row`: a table that guesses is
    worse than one that admits. Without a resolvable job list every #job
    would read as unknown-job; without the whodunit ledger every !clue-id
    would read as unknown-clue and every ledger clue would read as
    unscheduled — both are the NORMAL mid-workshop state, since the
    counterplot stage writes the ledger only after the chapters stage drafts
    the beats. So those findings are suppressed here (not in `check_story`,
    whose injected-ids design stays deliberate) and replaced with a named
    note saying the check could not run and why.
    """
    root = penny_paths.series_root()
    story_p = root / "input" / f"book-{book}" / "story.md"
    if not story_p.is_file():
        print(f"story_cut: missing {story_p}", file=sys.stderr)
        return 2

    job_ids, _ = _job_ids_and_titles()
    clues, _, ledger_p = _ledger(root, book)
    result = check_story(story_p.read_text(encoding="utf-8"), "",
                         job_ids, list(clues))

    findings = [f for f in result["blocking"]
                if not f.startswith("beats-without-chapter")]
    notes = list(result["notes"])

    if not job_ids:
        findings = [f for f in findings if not f.startswith("unknown-job:")]
        notes.append(
            "unknown-job could not run — the active genre's macro-structure "
            "could not be resolved")
    if not clues:
        findings = [f for f in findings
                    if not (f.startswith("unknown-clue:")
                            or f.startswith("unscheduled-clue:"))]
        notes.append(
            f"unknown-clue/unscheduled-clue could not run — the whodunit "
            f"ledger is missing or empty ({ledger_p})")

    for f in findings:
        print(f)
    if notes:
        print("\nAdvisory — nothing blocks on these:")
        for note in notes:
            print(f"  {note}")
    if not findings:
        print(f"story_cut: {story_p} has no blocking findings")
    return 1 if findings else 0


def renumber(story_text: str) -> str:
    """Rewrite every beat bullet's `[n]` to match its actual position.

    Text-level and idempotent: only the bracketed prefix on a beat bullet is
    touched, so tags, continuation lines, spacing and the inert Questions /
    Chapter Direction / Guardrails blocks come through byte-identical. Walks the
    same heading/bullet state machine `_fold` does, because a directive bullet
    numbered as a beat would reintroduce the exact off-by-one the numbers exist
    to catch.
    """
    lines = story_text.splitlines(keepends=True)
    offset = len(lines) - len(penny_story.strip_frontmatter(story_text).splitlines(keepends=True))
    collecting, n = True, 0
    for i in range(offset, len(lines)):
        raw = lines[i].rstrip("\n")
        if penny_story._HEADING_RE.match(raw):
            collecting = penny_story._heading_name(raw) not in penny_story._INERT_HEADINGS
            continue
        if not collecting:
            continue
        m = penny_story._BULLET_RE.match(raw)
        if not m:
            continue
        rest = m.group("rest")
        stripped = penny_story._BEAT_NUM_RE.sub("", rest)
        # A lone `- ` is not a beat (matching _fold's final filter), so it must not
        # consume a number — that would shift every beat after it.
        if not stripped.strip():
            continue
        n += 1
        eol = "\n" if lines[i].endswith("\n") else ""
        lines[i] = f"- [{n}] {stripped}{eol}"
    return "".join(lines)


def _renumber_cmd(book: str) -> int:
    root = penny_paths.series_root()
    p = root / "input" / f"book-{book}" / "story.md"
    if not p.is_file():
        print(f"story_cut: missing {p}", file=sys.stderr)
        return 2
    before = p.read_text(encoding="utf-8")
    after = renumber(before)
    beats_before = parse_story(before)
    beats_after = parse_story(after)
    # Renumbering must never change what the beats ARE. If prose or tags moved, the
    # rewrite is wrong and writing it would corrupt the story — refuse instead.
    if [(b["text"], b["strands"], b["jobs"], b["opens"], b["closes"], b["clues"])
            for b in beats_before] != [
            (b["text"], b["strands"], b["jobs"], b["opens"], b["closes"], b["clues"])
            for b in beats_after]:
        print("story_cut: renumber would alter beat content — refusing to write",
              file=sys.stderr)
        return 1
    if after == before:
        print(f"story_cut: {p} already numbered 1..{len(beats_after)}")
        return 0
    p.write_text(after, encoding="utf-8")
    print(f"story_cut: numbered {len(beats_after)} beats in {p}")
    return 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) == 2 and argv[0] == "check":
        return _check(argv[1])
    if len(argv) == 2 and argv[0] == "number":
        return _renumber_cmd(argv[1])
    if len(argv) != 1:
        print("usage: story_cut.py <book> | story_cut.py check <book> "
              "| story_cut.py number <book>", file=sys.stderr)
        return 2
    book = argv[0]
    root = penny_paths.series_root()
    bookdir = root / "input" / f"book-{book}"
    story_p, plan_p = bookdir / "story.md", bookdir / "cut-plan.md"
    for p in (story_p, plan_p):
        if not p.is_file():
            print(f"story_cut: missing {p}", file=sys.stderr)
            return 2

    story_text = story_p.read_text(encoding="utf-8")
    plan_text = plan_p.read_text(encoding="utf-8")
    job_ids, job_titles = _job_ids_and_titles()
    clues, ledger_data, ledger_p = _ledger(root, book)

    outline_p = bookdir / "outline.md"
    findings = []
    if outline_p.is_file():
        refusal = recut_refusal(outline_p.read_text(encoding="utf-8"))
        if refusal:
            findings.append(refusal)

    # A missing reveal_chapter must block, not silently emit vacuous guardrail
    # prose ("do not resolve before chapter 00") into every chapter block.
    if not ledger_data or ledger_data.get("reveal_chapter") is None:
        findings.append(
            "missing-reveal-chapter: the whodunit ledger has no "
            "reveal_chapter set, so the chapter guardrails ('do not resolve "
            f"the mystery before chapter NN') cannot be derived — set "
            f"reveal_chapter in {ledger_p} before cutting")

    result = check_story(story_text, plan_text, job_ids, list(clues))
    findings.extend(result["blocking"])
    for note in result["notes"]:
        print(f"note: {note}")

    # Chapter numbers are derived, so the ledger's are too (spec §6). Safe
    # because lock-mystery runs after the cut — the ledger is still unsealed.
    # The ledger is a hand-authored file (comments, anchors, quoting, bare
    # yes/no scalars), so this rewrites its TEXT surgically rather than
    # round-tripping it through yaml.safe_dump, which would silently destroy
    # all of that (see _rewrite_clue_chapters). Computed and validated here,
    # before anything is written: an id the text-level walk can't find (even
    # though the loaded yaml knows about it) must be a finding, not a
    # partial write discovered only after the outline already landed.
    ledger_text = new_ledger_text = None
    if ledger_data and any(ledger_data.get(k) for k in _CLUE_COLLECTIONS):
        beats = parse_story(story_text)
        chapters = parse_cut_plan(plan_text)
        home = {i: c["num"] for c in chapters for i in c["beats"]}
        where = {cid: home.get(n) for n, b in enumerate(beats, 1) for cid in b["clues"]}
        updates = {cid: chapter for cid, chapter in where.items() if chapter}
        if updates:
            ledger_text = ledger_p.read_text(encoding="utf-8")
            new_ledger_text, missing = _rewrite_plant_chapters(ledger_text, updates)
            for cid in missing:
                findings.append(
                    f"clue-not-found-in-ledger-text: ledger clue [{cid}] "
                    f"resolves a chapter but could not be located in "
                    f"{ledger_p}'s clue_schedule/red_herrings text — refusing "
                    f"a partial update")

    if findings:
        for f in findings:
            print(f)
        return 1

    guard_p = root / "config" / "series-guardrails.md"
    guardrails = guard_p.read_text(encoding="utf-8") if guard_p.is_file() else ""
    reveal = int(ledger_data["reveal_chapter"])

    body = emit_outline(story_text, plan_text, parse_questions(story_text), clues,
                        reveal_chapter=reveal, guardrails=guardrails,
                        job_titles=job_titles, solution=ledger_data)

    # The ledger is written FIRST, so the whodunit fingerprint stamped into the
    # outline describes the ledger the cut leaves behind — stamping the
    # pre-write bytes would make `plot_stage status` report the cut stale the
    # instant it finished, which is the bug in a different disguise.
    if new_ledger_text is not None and new_ledger_text != ledger_text:
        ledger_p.write_text(new_ledger_text, encoding="utf-8")

    whodunit_sha = plot_stage._upstream_sha(ledger_p) if ledger_p.is_file() else None
    outline_p.write_text(
        stamp_outline(body,
                      story_sha=hashlib.sha256(story_text.encode()).hexdigest(),
                      cut_sha=hashlib.sha256(plan_text.encode()).hexdigest(),
                      book=book,
                      total_chapters=len(parse_cut_plan(plan_text)),
                      whodunit_sha=whodunit_sha),
        encoding="utf-8")

    print(f"story_cut: wrote {outline_p} ({len(parse_cut_plan(plan_text))} chapters)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
