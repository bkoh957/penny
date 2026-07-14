"""Compile a locked outline into one prompt-shaped brief per chapter (spec:
docs/superpowers/specs/2026-07-14-outline-prompt-design.md).

Two subcommands:

  check  — the prompt-level defects: a scene whose instruction mass contradicts its
           declared weight, a chapter with no weights in a weighted book, a book of
           undeclared or unrelieved cliffhangers.
  build  — write input/book-NN/briefs/ch-MM.md, stamped with the outline's sha256.

Why this exists: /draft-chapter used to hand the drafter the raw outline section —
ten numbered beats, each written with equal lavishness, reference material formatted
identically to directives. A numbered list is a promise of parity and a model's
default unit is the scene, so ten beats became 3,802 words against an 1,800-2,400
band. The model obeyed the prompt it received. This turns the outline into a prompt.

Deterministic throughout: given a weighted outline there is exactly one correct
brief. The weights themselves are the showrunner's, declared in the outline.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml  # beat-sheet only — nested, human-edited (CLAUDE.md dependency split)
# The whodunit ledger read in _obligations is legitimately PyYAML too (nested,
# human-edited data — CLAUDE.md dependency split), not config/frontmatter.

from scripts import penny_length, penny_paths
from scripts.penny_meta import parse_frontmatter, write_frontmatter_field
from scripts.penny_wiring import has_weights, parse_wired_chapters

_FORM = {
    "anchor": "Dramatise fully. This is the chapter's reason to exist.",
    "support": "Brief scene texture, kept subordinate to the anchor.",
    "connective": "Compress: one paragraph, a transition, a phone call, or a line of "
                  "dialogue — in summary, not scene.",
}

_NO_WARMUP = ("Open in motion — no weather, no waking, no arriving, no scene-setting "
              "run-up. The chapter starts where the trouble starts.")

_NO_BUTTON = ("End on that line. Do not add a closing paragraph of reflection, and do "
              "not tie the chapter off.")

_GRADE = {
    "cliffhanger": "a turn, threat, or revelation that makes the next page involuntary",
    "promise": "a promise of the next action — an intention, an appointment, a decision "
               "taken (the lesser hook, and the right one for a connective chapter)",
}


def _load_sheet(path) -> dict:
    if path is None or not Path(path).is_file():
        return {}
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def check_briefs(outline_path, *, beat_sheet_path=None) -> dict:
    text = Path(outline_path).read_text(encoding="utf-8")
    chapters = parse_wired_chapters(text)
    if not has_weights(chapters):
        return {"weighted": False, "findings": [], "metrics": {"chapters": len(chapters)}}

    findings: list[str] = []

    for ch in chapters:
        scenes = ch["scenes"]
        if not scenes:
            # A chapter with zero ### Scene blocks (compact-format, or a stub
            # /expand-outline hasn't reached yet — it expands one chapter at
            # a time, so a half-expanded outline is ordinary) has nothing to
            # say about weights or anchors. Flagging it as "no anchor scene"
            # is a false positive that fires on every healthy unexpanded
            # chapter, every run — a check that cries wolf gets ignored.
            continue
        weighted_scenes = [s for s in scenes if s["weight"]]
        if not weighted_scenes:
            findings.append(
                f"unweighted-chapter: ch {ch['num']} declares no scene weights in a "
                f"weighted book — the drafter will treat all {len(scenes)} scenes as equal")
            continue
        if len(weighted_scenes) < len(scenes):
            # Some scenes in this chapter declare a weight and at least one
            # doesn't — a partial declaration, distinct from the
            # all-or-nothing unweighted-chapter case above. Left alone,
            # render_brief used to default the untagged scene to "support"
            # silently; the showrunner never asked for that, so it earns its
            # own finding rather than passing the checks clean.
            undeclared = [s for s in scenes if not s["weight"]]
            names = ", ".join(f"scene {s['num']} '{s['title']}'" for s in undeclared)
            findings.append(
                f"undeclared-scene-weight: ch {ch['num']} declares a weight for some "
                f"scenes but not {names} — an undeclared scene weight would silently "
                f"default to 'support', which nobody asked for")
            continue
        anchors = [s for s in scenes if s["weight"] == "anchor"]
        if not anchors:
            findings.append(
                f"unweighted-chapter: ch {ch['num']} has no anchor scene — every chapter "
                f"needs one central dramatic experience")
            continue
        if len(anchors) > 1:
            names = ", ".join(f"scene {s['num']} '{s['title']}'" for s in anchors)
            findings.append(
                f"multi-anchor-chapter: ch {ch['num']} tags {len(anchors)} scenes as "
                f"anchor ({names}) — a chapter has one reason to exist, not two")
            continue
        heaviest_anchor = max(s["instruction_words"] for s in anchors)
        for s in scenes:
            if s["weight"] == "connective" and s["instruction_words"] > heaviest_anchor:
                findings.append(
                    f"prompt-mass-inversion: ch {ch['num']} scene {s['num']} "
                    f"'{s['title']}' is marked connective but carries "
                    f"{s['instruction_words']} words of instruction against the anchor's "
                    f"{heaviest_anchor} — the prompt says it matters more than the anchor, "
                    f"and the drafter will believe the prompt")

    graded = [c for c in chapters if c["hook_grade"]]
    ungraded = [c["num"] for c in chapters if not c["hook_grade"]]
    if ungraded:
        findings.append(
            f"hook-grade-distribution: chapters {ungraded} declare no hook grade "
            f"(cliffhanger | promise) — a chapter that ends on neither ends on nothing")
    sheet = _load_sheet(beat_sheet_path)
    hooks_cfg = sheet.get("hooks")
    cap = hooks_cfg.get("max_cliffhanger_fraction") if isinstance(hooks_cfg, dict) else None
    if cap is not None and graded:
        cliffs = [c["num"] for c in graded if c["hook_grade"] == "cliffhanger"]
        fraction = len(cliffs) / len(graded)
        if fraction > float(cap):
            findings.append(
                f"hook-grade-distribution: {len(cliffs)}/{len(graded)} chapters end on a "
                f"cliffhanger ({fraction:.0%} > {float(cap):.0%}) — unrelieved cliffhangers "
                f"read as machinery and the reader stops believing them")

    return {"weighted": True, "findings": findings,
            "metrics": {"chapters": len(chapters),
                        "scenes": sum(len(c["scenes"]) for c in chapters)}}


def render_brief(chapter: dict, *, profile: dict, obligations: dict,
                 outline_text: str) -> str:
    """One chapter's brief: a prompt, not an outline section.

    The order is the instruction. The one thing comes before any beat; the anchor is
    the root and everything else is nested beneath it; obligations are a checklist,
    never stops; reference material is demoted out of instruction voice.
    """
    scenes = chapter["scenes"]

    # A chapter with no anchor has no central dramatic experience, and one
    # with two contradicts itself on the page (both, still labelled ANCHOR,
    # both told "this is the chapter's reason to exist") — there is no
    # correct brief for either, so the compiler refuses rather than degrade
    # into the flat, equal-scene prompt it exists to eliminate.
    anchors = [s for s in scenes if s["weight"] == "anchor"]
    if len(anchors) > 1:
        names = ", ".join(f"scene {s['num']} ('{s['title']}')" for s in anchors)
        raise ValueError(
            f"chapter {chapter['num']}: {len(anchors)} scenes tagged anchor "
            f"({names}) — a chapter has at most one anchor; render_brief refuses "
            "to render two scenes each claiming to be the chapter's reason to exist")
    if not anchors:
        raise ValueError(
            f"chapter {chapter['num']}: no anchor scene — a chapter with no anchor "
            "has no central dramatic experience, and there is no correct brief for it")

    # A silent `s["weight"] or "support"` default would contradict this
    # module's own promise ("given a weighted outline there is exactly one
    # correct brief") — an undeclared scene weight is an authoring omission,
    # not a default the compiler is entitled to guess at.
    undeclared = [s for s in scenes if not s["weight"]]
    if undeclared:
        names = ", ".join(f"scene {s['num']} ('{s['title']}')" for s in undeclared)
        raise ValueError(
            f"chapter {chapter['num']}: {names} declare no weight — render_brief "
            "refuses to silently default an undeclared scene weight to 'support'")

    band = penny_length.band_for(profile, chapter["chapter_type"])
    budgets = penny_length.scene_budgets(
        profile, band, [s["weight"] for s in scenes])
    target = sum(budgets)

    anchor = anchors[0]
    out: list[str] = []
    out.append(f"# Chapter {chapter['num']:02d} — {chapter['title']}")
    out.append("")
    out.append("## The one thing")
    out.append("")
    out.append("The reader should finish this chapter remembering **one** central "
               "dramatic experience, not a list of technically correct stops:")
    out.append("")
    out.append(f"> {anchor['title'] if anchor else chapter['title']}")
    out.append("")
    out.append(f"Total budget: **~{target} words** (band {band[0]}–{band[1]}).")
    if chapter["long_waiver"]:
        out.append("")
        out.append(f"**Declared long:** {chapter['long_waiver']} — this override is "
                   f"recorded, and the length checks honour it.")
    out.append("")

    out.append("## The shape")
    out.append("")
    if anchor:
        i = scenes.index(anchor)
        out.append(f"### ANCHOR — Scene {anchor['num']}: {anchor['title']} "
                   f"(~{budgets[i]} words)")
        out.append("")
        out.append(_FORM["anchor"])
        out.append("")
        out.append("Everything below is **subordinate to this scene**. It is material in "
                   "service of it, not a peer of it.")
        out.append("")
    for i, s in enumerate(scenes):
        if s is anchor:
            continue
        weight = s["weight"]
        if weight not in _FORM:
            # penny_length.scene_budgets is generic over any weight_* class a
            # series declares in length-profile.md, so a 4th class is legal
            # and reachable — but _FORM only carries drafting prose for the
            # three the engine ships. A bare KeyError here would name
            # neither the class nor where to fix it.
            raise ValueError(
                f"chapter {chapter['num']} scene {s['num']}: unknown scene weight "
                f"class {weight!r} — length-profile.md declares weight_{weight}, "
                f"but _FORM in scripts/brief_render.py has no drafting instruction "
                "for it yet; add one there")
        out.append(f"  - **{weight.upper()} — Scene {s['num']}: {s['title']}** "
                   f"(~{budgets[i]} words). {_FORM[weight]}")
    out.append("")

    out.append("## Obligations")
    out.append("")
    out.append("These **must be TRUE OF THE PAGE** by the end of the chapter. They are "
               "**not stops on an itinerary** — most can be discharged inside the anchor "
               "scene in a sentence. Do not give any of them their own scene.")
    out.append("")
    for clue in obligations.get("clues", []):
        out.append(f"- Plant: `{clue}` — fairly, on the page, in view of the reader.")
    for q in obligations.get("opens", []):
        out.append(f"- Open the question: `{q}`")
    for q in obligations.get("closes", []):
        out.append(f"- Close the question: `{q}`")
    for track, movement in (obligations.get("tracks") or {}).items():
        if movement and movement.strip().lower() != "none":
            out.append(f"- Advance thread **{track}**: {movement}")
    if not any(obligations.get(k) for k in ("clues", "opens", "closes", "tracks")):
        out.append("- None.")
    out.append("")

    out.append("## The first line")
    out.append("")
    if chapter["first_line"]:
        out.append(f"{chapter['first_line']}")
        out.append("")
    out.append(_NO_WARMUP)
    out.append("")

    out.append("## The last line")
    out.append("")
    grade = chapter["hook_grade"]
    if grade:
        out.append(f"End on a **{grade}**: {_GRADE[grade]}.")
    if chapter["hook_raw"]:
        out.append("")
        out.append(f"The hook: {chapter['hook_raw']}")
    out.append("")
    out.append(_NO_BUTTON)
    out.append("")

    out.append("## Negative space")
    out.append("")
    out.append("Do not resolve any question this chapter is not commissioned to close. "
               "Do not dramatise anything not named above — if an event must be "
               "acknowledged, refer to it in a line. Left to itself a model resolves "
               "tension early and stages everything; both are fatal to a page-turner.")
    out.append("")

    out.append("## Reference — available material, NOT a checklist")
    out.append("")
    out.append("Everything below is the outline as written. It is context you may draw "
               "on. It is **not** a list of things to do, and no line of it obliges you "
               "to write a scene.")
    out.append("")
    out.append("<details>")
    out.append("")
    out.append(_chapter_block(outline_text, chapter["num"]))
    out.append("")
    out.append("</details>")
    out.append("")
    return "\n".join(out)


def _chapter_block(outline_text: str, num: int) -> str:
    """The raw `## Chapter NN` section — reference only."""
    from scripts.penny_wiring import CHAPTER_RE, HEADING_RE
    marks = list(HEADING_RE.finditer(outline_text))
    for i, m in enumerate(marks):
        cm = CHAPTER_RE.match(m.group(1))
        if cm and int(cm.group(1)) == num:
            start = m.start()
            end = marks[i + 1].start() if i + 1 < len(marks) else len(outline_text)
            return outline_text[start:end].strip()
    return ""


def brief_path(book: str, chapter: str, repo_root) -> Path:
    return penny_paths.input_path(f"book-{book}/briefs/ch-{chapter}.md", root=repo_root)


def _sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


NO_WHODUNIT = "none"  # sentinel for built_from_whodunit when no ledger existed at
# build time. A real sha256 digest is 64 lowercase hex characters, so this
# string can never collide with one. ALWAYS written (never omitted) — an
# absent ledger is a fact this build saw, not an exemption from staleness
# (CLAUDE.md: nothing drifts silently).


def load_ledger(path) -> dict:
    """Read + parse the whodunit ledger at `path` — the ONE guarded entry point
    every caller uses (build()'s _obligations, preflight.cmd_draft). A ledger
    that cannot be read, is not valid YAML, or whose top level is not a
    mapping produces a NAMED ValueError identifying the path and the problem
    — never a raw ParserError/AttributeError/OSError traceback. Callers turn
    this into their own convention (a per-chapter FAILED line here, a
    `preflight: <predicate>` exit there)."""
    path = Path(path)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        raise ValueError(f"unreadable-ledger: cannot read {path} — {e}") from e
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        raise ValueError(f"malformed-ledger: {path} is not valid YAML — {e}") from e
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(
            f"malformed-ledger: {path} top level is a {type(data).__name__}, "
            "not a mapping — cannot read clue_schedule/red_herrings from it")
    return data


def _ledger_identity(path) -> str:
    """The ledger's identity, used for BOTH stamping (build) and comparison
    (stale_briefs): its sha256 if the file exists and is readable, or
    NO_WHODUNIT if none exists yet. A ledger that EXISTS but cannot be read
    (permission denied) is a real failure, not silent absence — those two
    must not be conflated, so this raises the same named ValueError as
    load_ledger rather than letting a bare PermissionError escape."""
    path = Path(path)
    if not path.is_file():
        return NO_WHODUNIT
    try:
        raw = path.read_bytes()
    except OSError as e:
        raise ValueError(f"unreadable-ledger: cannot read {path} — {e}") from e
    return hashlib.sha256(raw).hexdigest()


def _plant_chapter(entry: dict, led: Path) -> int:
    """The clue's scheduled chapter, validated. `.get(key, default)` only
    substitutes when the key is ABSENT — a hand-edited `plant_chapter: null`
    leaves the key present with value None, so a bare `int(entry.get(...))`
    raises a bare TypeError that crashes the whole book build. Both a missing
    key and an explicit null are equally "we don't know which chapter this
    clue belongs to" — neither is safe to silently coerce to 0."""
    raw = entry.get("plant_chapter")
    cid = entry.get("id", "<no id>")
    if raw is None:
        raise ValueError(
            f"malformed-plant-chapter: clue {cid!r} in {led} has no "
            "plant_chapter (missing or null) — cannot schedule its obligation")
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise ValueError(
            f"malformed-plant-chapter: clue {cid!r} in {led} has a "
            f"non-integer plant_chapter {raw!r} — cannot schedule its obligation")


def _obligations(book: str, chapter: dict, repo_root) -> dict:
    """What must be TRUE OF THE PAGE — derived from the locked ledger and the wiring,
    never re-authored. This is why the stage runs after the lock."""
    led = penny_paths.series_path(f"whodunit/book-{book}.yaml", root=repo_root)
    clues: list[str] = []
    if led.is_file():
        data = load_ledger(led)
        for entry in (data.get("clue_schedule") or []):
            if _plant_chapter(entry, led) == chapter["num"]:
                clues.append(str(entry["id"]))
        for entry in (data.get("red_herrings") or []):
            if _plant_chapter(entry, led) == chapter["num"]:
                clues.append(str(entry["id"]))
    return {"clues": clues,
            "opens": [q for q, _ in chapter["opens"]],
            "closes": list(chapter["closes"]),
            "tracks": dict(chapter["tracks"])}


def build(book: str, *, chapter=None, repo_root=None) -> int:
    """Compile the locked outline into input/book-NN/briefs/ch-MM.md, one file per
    chapter, each stamped with the outline's sha256 (built_from_outline).

    A chapter render_brief refuses (no anchor, two anchors, an undeclared scene
    weight) does not abort the whole book: it is reported by name and reason,
    skipped, and the run's exit status reflects that not everything compiled —
    the caller (a human, or /build-briefs) must not mistake a partial write for
    a clean one.
    """
    root = Path(repo_root) if repo_root is not None else penny_paths.series_root()
    outline = penny_paths.input_path(f"book-{book}/outline.md", root=root)
    profile_path = penny_paths.config_path("length-profile.md", root=root)
    text = outline.read_text(encoding="utf-8")
    chapters = parse_wired_chapters(text)
    if not has_weights(chapters):
        print("no scene weights detected — no briefs written "
              "(the drafter will receive the raw outline section, as today)")
        return 0
    profile = penny_length.parse_profile(profile_path.read_text(encoding="utf-8"))
    sha = _sha(outline)
    # The whodunit ledger is a real upstream of every brief — obligations
    # (_obligations) come from it, not just the outline. ALWAYS stamp
    # built_from_whodunit, using the NO_WHODUNIT sentinel when no ledger
    # exists: an absent ledger is a fact this build saw, not an exemption
    # from staleness. stale_briefs() below then catches a mismatch in EITHER
    # direction — ledger edited, ledger deleted, or a ledger arriving where
    # none existed before — exactly as it catches an outline edit; nothing
    # drifts silently. A ledger that EXISTS but can't be read (permission
    # denied) is a real failure: every chapter's stamp would be unreliable,
    # so the whole book build is reported by name and aborted here, rather
    # than letting a raw exception escape.
    ledger_path = penny_paths.series_path(f"whodunit/book-{book}.yaml", root=root)
    try:
        whodunit_stamp = _ledger_identity(ledger_path)
    except ValueError as e:
        print(f"FAILED: {e}")
        return 1
    written = 0
    failed: list[str] = []
    for ch in chapters:
        num = f"{ch['num']:02d}"
        if chapter is not None and num != str(chapter).zfill(2):
            continue
        try:
            body = render_brief(ch, profile=profile,
                                obligations=_obligations(book, ch, root),
                                outline_text=text)
        except ValueError as e:
            print(f"FAILED: ch {num} did not compile — {e}")
            failed.append(num)
            continue
        stamped = write_frontmatter_field("---\n---\n\n" + body,
                                          "built_from_outline", sha)
        stamped = write_frontmatter_field(stamped, "built_from_whodunit", whodunit_stamp)
        p = brief_path(book, num, root)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(stamped, encoding="utf-8")
        written += 1
    print(f"briefs: wrote {written} chapter brief(s) to input/book-{book}/briefs/"
          + (f" ({len(failed)} failed: {', '.join(failed)})" if failed else ""))
    return 1 if failed else 0


def stale_briefs(book: str, repo_root) -> list[str]:
    """Chapter numbers whose brief was built from a different outline OR a different
    whodunit ledger than the ones now on disk. The ledger is a real upstream: a
    brief's OBLIGATIONS (_obligations) come from clue_schedule/red_herrings'
    plant_chapter, so moving a clue between chapters must invalidate the briefs
    exactly as an outline edit does — nothing drifts silently (the workshop's own
    contract).

    build() ALWAYS stamps `built_from_whodunit` — a sha256, or the NO_WHODUNIT
    sentinel when no ledger existed at build time — so a mismatch in EITHER
    direction is stale: a sha that no longer matches, a sha where the ledger
    has since been deleted, and a sentinel where a ledger has since ARRIVED
    (the hole this fix closes: a book built before any ledger existed must not
    stay "fresh" forever once one is created). A brief carrying no
    `built_from_whodunit` key at all (built before this field existed) is
    likewise stale — it recorded nothing about the ledger, and an absent
    record is not a clean bill of health; re-running /build-briefs is how it
    earns one.

    Raises ValueError (unreadable-ledger) if the ledger exists on disk but
    cannot be read — a real failure, not silent absence.
    """
    root = Path(repo_root)
    outline = penny_paths.input_path(f"book-{book}/outline.md", root=root)
    briefs_dir = penny_paths.input_path(f"book-{book}/briefs", root=root)
    if not briefs_dir.is_dir() or not outline.is_file():
        return []
    sha = _sha(outline)
    ledger = penny_paths.series_path(f"whodunit/book-{book}.yaml", root=root)
    ledger_stamp = _ledger_identity(ledger)
    stale = []
    for p in sorted(briefs_dir.glob("ch-*.md")):
        fm = parse_frontmatter(p.read_text(encoding="utf-8"))
        is_stale = fm.get("built_from_outline") != sha
        # ledger_stamp is never None (NO_WHODUNIT or a sha), so a brief with
        # no built_from_whodunit key at all (fm.get(...) -> None) always
        # compares unequal too — the "no stamp ever written" case falls out
        # of the same comparison, no special-casing needed.
        if fm.get("built_from_whodunit") != ledger_stamp:
            is_stale = True
        if is_stale:
            stale.append(p.stem.replace("ch-", ""))
    return stale


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Compile a locked outline into chapter briefs.")
    ap.add_argument("command", choices=["check", "build"])
    ap.add_argument("book")
    ap.add_argument("--chapter", default=None, help="only this chapter, e.g. 03")
    args = ap.parse_args(argv)

    root = penny_paths.series_root()
    outline = penny_paths.input_path(f"book-{args.book}/outline.md", root=root)
    if not outline.is_file():
        sys.exit(f"brief: no outline at {outline}")

    if args.command == "check":
        result = check_briefs(outline, beat_sheet_path=_beat_sheet_path(root))
        if not result["weighted"]:
            print("no scene weights detected — skipped "
                  "(the drafter will receive the raw outline section)")
            return 0
        for f in result["findings"]:
            print(f"FINDING: {f}")
        print(f"briefs: {result['metrics']['chapters']} chapter(s), "
              f"{result['metrics']['scenes']} scene(s), "
              f"{len(result['findings'])} finding(s)")
        return 1 if result["findings"] else 0

    # build (a later task): genuinely needs band/weight data, so its
    # length-profile requirement stays here rather than in check_briefs.
    profile = penny_paths.config_path("length-profile.md", root=root)
    if not profile.is_file():
        sys.exit(f"brief: no length profile at {profile}")

    return build(args.book, chapter=args.chapter, repo_root=root)


def _beat_sheet_path(root):
    """The active genre's beat sheet, resolved through penny_genre's `beat_sheet()`
    — never a hardcoded filename (CLAUDE.md). Returns None when the genre declares
    none, which the checks treat as 'no cap configured'."""
    from scripts import penny_genre
    return penny_genre.beat_sheet(root=root)


if __name__ == "__main__":
    raise SystemExit(main())
