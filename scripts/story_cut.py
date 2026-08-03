"""Validate story.md + cut-plan.md, then emit outline.md (spec 2026-08-03).

Deterministic throughout: this module makes no LLM judgment. The one judgment
in the cut — where chapter boundaries fall — is made by the `chapter-cutter`
agent and approved by the showrunner before this module ever runs (spec §5).

No waivers exist at this level (spec §8). Fix the story or fix the cut plan.
"""
import sys

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


def _carried(chapters_beats, upto_index, opened_by, closed_by):
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
        for qid in beat["opens"]:
            opened_by.setdefault(qid, beat_chapter.get(n, 0))
        for qid in beat["closes"]:
            closed_by[qid] = beat_chapter.get(n, 0)

    def qline(qid):
        return f"{qid} — {questions.get(qid, '')}".rstrip(" —")

    out = []
    for pos, ch in enumerate(chapters):
        mine = [beats[i - 1] for i in ch["beats"] if 1 <= i <= len(beats)]
        strands_so_far = sorted({s for i in range(1, max(ch["beats"], default=0) + 1)
                                 for s in (beats[i - 1]["strands"] if i <= len(beats) else [])})
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

        carried = _carried(chapters, ch["num"], opened_by, closed_by)
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
        wiring += [f"- **Carries:** {q}" for q in carried]
        out.append("### Chapter Structure\n" + "\n".join(wiring) + "\n")

        out.append("### Track Movement\n" + "\n".join(
            f"- **{k}:** {v}" for k, v in ch["tracks"].items()) + "\n")

    return "\n".join(out).rstrip() + "\n"
