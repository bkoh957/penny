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
        if idx > len(beats):
            blocking.append(
                f"beats-without-chapter: the cut plan claims beat {idx} but the "
                f"story has only {len(beats)}")

    return {"blocking": blocking, "notes": notes}
