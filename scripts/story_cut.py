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

from scripts import penny_genre, penny_paths
from scripts.outline_views import parse_jobs
from scripts.penny_meta import parse_frontmatter, strip_frontmatter
from scripts.penny_story import (SLUG_RE, parse_cut_plan, parse_questions,
                                 parse_story)
from scripts.penny_wiring import QID_RE


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

    return {"blocking": blocking, "notes": notes}


def _carried(upto_index, opened_by, closed_by):
    """Question ids opened at or before this chapter and not yet closed."""
    live = []
    for qid, opened_at in opened_by.items():
        if opened_at <= upto_index and closed_by.get(qid, 10 ** 9) >= upto_index:
            live.append(qid)
    return sorted(live)


def emit_outline(story_text: str, cut_plan_text: str, questions: dict,
                 ledger: dict, *, reveal_chapter: int, guardrails: str,
                 job_titles: dict) -> str:
    """Expand an approved cut plan into packet-format chapter blocks (spec §5.2)."""
    beats = parse_story(story_text)
    chapters = parse_cut_plan(cut_plan_text)

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

    out = []
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

        out.append("### Required Beats\n"
                   + "\n".join(f"- {b['text']}" for b in mine) + "\n")

        clues = [c for b in mine for c in b["clues"]]
        out.append("### Clues and Plants\n" + ("\n".join(
            f"- [{c}] {ledger.get(c, c)}" for c in clues)
            or "- No ledger clue is scheduled for this chapter.") + "\n")

        out.append("### Character Knowledge\nOn the page so far:\n"
                   + "\n".join(f"- {s}" for s in strands_so_far) + "\n"
                   + f"\nNot yet known:\n- The solution, until chapter "
                     f"{reveal_chapter:02d}.\n")

        out.append("### Guardrails\n- " + guardrails.strip()
                   + f"\n- Do not resolve the mystery before chapter {reveal_chapter:02d}.\n")

        wiring = []
        if opens:
            wiring.append(f"- **Hook:** {qline(opens[0])}")
        if pos:
            wiring.append(f"- **Because:** ch {chapters[pos - 1]['num']:02d}")
        wiring += [f"- **Opens:** {qline(q)}" for q in opens]
        wiring += [f"- **Closes:** {qline(q)}" for q in closes]
        # A question this chapter closes is never also "carried" by it — the
        # format never produces close-and-carry in the same chapter (0/28 in
        # book-01's outline); a question this chapter opens still carries
        # (28/28 do), so only `closes` is excluded here, not `opens`.
        wiring += [f"- **Carries:** {q}" for q in carried if q not in closes]
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


def stamp_outline(body: str, *, story_sha: str, cut_sha: str) -> str:
    out_sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return ("---\n"
            f"built_from_story: {story_sha}\n"
            f"built_from_cut: {cut_sha}\n"
            f"cut_output_sha256: {out_sha}\n"
            "---\n\n" + body)


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


def _job_ids_and_titles():
    """(ids, id->title) from the active genre's macro-structure, or ([], {})."""
    path = penny_genre.macro_structure()
    if path is None or not path.is_file():
        return [], {}
    jobs = parse_jobs(path.read_text(encoding="utf-8"))
    return [jid for jid, _ in jobs], {jid: title for jid, title in jobs}


def _ledger(root, book):
    p = root / "series" / "whodunit" / f"book-{book}.yaml"
    if not p.is_file():
        return {}, None, p
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    clues = {c["id"]: c.get("description", c["id"])
             for c in (data.get("clue_schedule") or []) if c.get("id")}
    return clues, data, p


_ID_LINE_RE = re.compile(r"^(?P<indent>[ \t]*)-\s*id:\s*(?P<id>[^\s#]+)")
_CHAPTER_LINE_RE = re.compile(
    r"^(?P<indent>[ \t]*)chapter:\s*(?P<value>[^\s#]+)(?P<trail>.*)$")
_LIST_ITEM_RE = re.compile(r"^[ \t]*-\s")


def _rewrite_clue_chapters(ledger_text: str, updates: dict) -> str:
    """Rewrite only `clue_schedule[*].chapter` for ids in `updates` (id ->
    new chapter number) — byte-identical everywhere else.

    The whodunit ledger is a hand-authored showrunner artifact: comments,
    anchors, quoting, and bare yes/no scalars all carry meaning that
    `yaml.safe_load` → `yaml.safe_dump` silently destroys on write. So the
    ledger is never round-tripped through PyYAML on write — only read with
    `safe_load` (in `_ledger`). This is a line-walk instead: find each
    `- id: <cid>` line, then the `chapter:` line that belongs to that same
    entry — scanning forward until either a sibling list item at the id
    line's own indentation, or a dedent past it, at which point the entry
    has no `chapter:` key and one is inserted right after the `id:` line, at
    one indent level deeper (matching its sibling keys). A found
    `chapter:` line has only its value replaced — indentation and any
    trailing inline comment are preserved verbatim.
    """
    if not updates:
        return ledger_text
    lines = ledger_text.splitlines(keepends=True)
    out: list = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _ID_LINE_RE.match(line.rstrip("\n"))
        if not m or m.group("id") not in updates:
            out.append(line)
            i += 1
            continue

        cid = m.group("id")
        dash_indent = m.group("indent")
        out.append(line)
        i += 1

        chapter_idx = None
        j = i
        while j < len(lines):
            body = lines[j].rstrip("\n")
            stripped = body.strip()
            if stripped:
                cur_indent = body[:len(body) - len(body.lstrip(" \t"))]
                if len(cur_indent) <= len(dash_indent):
                    break
                cm = _CHAPTER_LINE_RE.match(body)
                if cm:
                    chapter_idx = j
                    break
            j += 1

        if chapter_idx is not None:
            for k in range(i, chapter_idx):
                out.append(lines[k])
            body = lines[chapter_idx].rstrip("\n")
            eol = lines[chapter_idx][len(body):]
            cm = _CHAPTER_LINE_RE.match(body)
            out.append(f"{cm.group('indent')}chapter: {updates[cid]}"
                       f"{cm.group('trail')}{eol}")
            i = chapter_idx + 1
        else:
            key_indent = dash_indent + "  "
            out.append(f"{key_indent}chapter: {updates[cid]}\n")

    return "".join(out)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: story_cut.py <book>", file=sys.stderr)
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
    if findings:
        for f in findings:
            print(f)
        return 1

    guard_p = root / "config" / "series-guardrails.md"
    guardrails = guard_p.read_text(encoding="utf-8") if guard_p.is_file() else ""
    reveal = int(ledger_data["reveal_chapter"])

    body = emit_outline(story_text, plan_text, parse_questions(story_text), clues,
                        reveal_chapter=reveal, guardrails=guardrails,
                        job_titles=job_titles)
    outline_p.write_text(
        stamp_outline(body,
                      story_sha=hashlib.sha256(story_text.encode()).hexdigest(),
                      cut_sha=hashlib.sha256(plan_text.encode()).hexdigest()),
        encoding="utf-8")

    # Chapter numbers are derived, so the ledger's are too (spec §6). Safe
    # because lock-mystery runs after the cut — the ledger is still unsealed.
    # The ledger is a hand-authored file (comments, anchors, quoting, bare
    # yes/no scalars), so this rewrites its TEXT surgically rather than
    # round-tripping it through yaml.safe_dump, which would silently destroy
    # all of that (see _rewrite_clue_chapters).
    if ledger_data and ledger_data.get("clue_schedule"):
        beats = parse_story(story_text)
        chapters = parse_cut_plan(plan_text)
        home = {i: c["num"] for c in chapters for i in c["beats"]}
        where = {cid: home.get(n) for n, b in enumerate(beats, 1) for cid in b["clues"]}
        updates = {cid: chapter for cid, chapter in where.items() if chapter}
        if updates:
            ledger_text = ledger_p.read_text(encoding="utf-8")
            new_text = _rewrite_clue_chapters(ledger_text, updates)
            if new_text != ledger_text:
                ledger_p.write_text(new_text, encoding="utf-8")

    print(f"story_cut: wrote {outline_p} ({len(parse_cut_plan(plan_text))} chapters)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
