#!/usr/bin/env python3
"""Resolve every `ch NN` / `chapter NN` reference in a book's instruction text.

The problem this exists for: chapter references are POSITIONAL, and a re-cut moves
every chapter. Book 01 went 29 -> 35 and left seventeen references pointing at the
wrong chapter — a guardrail citing "the sleuth's ch 18 theory" for a theory built in
ch 23, a habit ladder cited as "ch 4, ch 8 and ch 12" when the showings are in
ch 05, 09 and 16. Neither review panel member caught more than a third of them,
because catching them means resolving each claim against the beats by hand.

Two rules, in descending confidence:

  BLOCKING  out-of-range: a reference to a chapter the book does not have.

  ADVISORY  yaml-field-disagreement: a whodunit entry whose prose says "ch NN"
            while its own plant_chapter / resolves_chapter / pays_off_chapter
            field says a different number. The structured field and the prose
            describe the same event, so a mismatch is one of them being stale.
            This is the rule that would have caught book 01's stale character refs.

  BLOCKING  clue-plant-mismatch: a clue the whodunit declares `plant_chapter: N`
            whose `!clue-id` sigil in story.md actually falls in chapter M. Fully
            mechanical and exact — the sigil and the field are the same fact
            written twice.

A fuzzy "the words near this reference match a different chapter better" rule was
tried and removed: it flagged CORRECT references as wrong (a bare list like
"ch 5, ch 9 and ch 16" carries too few content words to score), and a checker that
cries wolf is worse than no checker.

Exit 1 only on BLOCKING findings, matching the other penny checkers.
"""
import argparse, re, sys, pathlib
try:
    import yaml
except ImportError:
    yaml = None

REF = re.compile(r'\b(?:ch|chapter)\s*(\d{1,2})\b', re.I)
STOP = set("""a an the and or but of to in on at by for with from as is are was were be been being
it its this that these those they them their he she her his him you your we our not no nor if then
than so such which who whom what when where why how all any both each few more most other some only
own same too very can will just don should now here there into out up down over under again once
does did doing have has had having would could may might must shall about after before during while
because until against between through above below off further chapter ch page beat beats""".split())


def load_ranges(cut_plan: str):
    titles, ranges, ch = {}, {}, None
    for line in cut_plan.splitlines():
        m = re.match(r'^## Chapter (\d+)(?: — (.+))?$', line)
        if m:
            ch = int(m.group(1)); titles[ch] = (m.group(2) or "").strip(); continue
        b = re.match(r'^\s*- \*\*Beats:\*\* (\d+)-(\d+)', line)
        if b and ch:
            ranges[ch] = (int(b.group(1)), int(b.group(2)))
    return titles, ranges


def load_beats(story: str):
    return {int(m.group(1)): m.group(2)
            for m in re.finditer(r'^\- \[(\d+)\] (.+)$', story, re.M)}


def chapter_text(ranges, beats):
    out = {}
    for c, (lo, hi) in ranges.items():
        out[c] = " ".join(beats.get(n, "") for n in range(lo, hi + 1)).lower()
    return out


def content_words(s):
    return [w for w in re.findall(r"[a-z']{4,}", s.lower()) if w not in STOP]


def check(book_dir: pathlib.Path, series_root: pathlib.Path, book: str):
    blocking, advisory = [], []
    cut_plan_p = book_dir / "cut-plan.md"
    story_p = book_dir / "story.md"
    whodunit_p = series_root / "series" / "whodunit" / f"book-{book}.yaml"

    if not cut_plan_p.exists() or not story_p.exists():
        print(f"chapter_refs_check: no cut-plan.md/story.md for book {book}", file=sys.stderr)
        return 2

    titles, ranges = load_ranges(cut_plan_p.read_text())
    beats = load_beats(story_p.read_text())
    if not ranges:
        print("chapter_refs_check: cut-plan.md declares no **Beats:** ranges", file=sys.stderr)
        return 2
    chtext = chapter_text(ranges, beats)
    nchap = max(ranges)

    sources = {"cut-plan.md": cut_plan_p.read_text(), "story.md": story_p.read_text()}
    if whodunit_p.exists():
        sources[whodunit_p.name] = whodunit_p.read_text()

    # --- rule 1: out of range -------------------------------------------------
    for name, txt in sources.items():
        for ln, line in enumerate(txt.splitlines(), 1):
            if line.startswith("## Chapter"):
                continue
            for m in REF.finditer(line):
                n = int(m.group(1))
                if n < 1 or n > nchap:
                    blocking.append(
                        f"out-of-range: {name}:{ln} references ch {n:02d}, but the book has "
                        f"{nchap} chapters — {line.strip()[:90]}")

    # --- rule 2: whodunit prose vs its own structured fields ------------------
    if whodunit_p.exists() and yaml is not None:
        data = yaml.safe_load(whodunit_p.read_text()) or {}
        for key in ("clues", "red_herrings", "suspects"):
            for entry in (data.get(key) or []):
                if not isinstance(entry, dict):
                    continue
                declared = {f: entry[f] for f in
                            ("plant_chapter", "resolves_chapter", "pays_off_chapter")
                            if isinstance(entry.get(f), int)}
                if not declared:
                    continue
                prose = " ".join(str(v) for k, v in entry.items()
                                 if k in ("description", "note", "text") and v)
                lo_d, hi_d = min(declared.values()), max(declared.values())
                for m in REF.finditer(prose):
                    n = int(m.group(1))
                    # An entry legitimately names chapters INSIDE its own life —
                    # a herring planted at 6 and resolved at 21 may say "cleared of
                    # the murder at ch 16" without either field being stale. Only a
                    # reference outside that span is evidence of rot.
                    if lo_d <= n <= hi_d:
                        continue
                    advisory.append(
                        f"yaml-field-disagreement: {whodunit_p.name} `{entry.get('id','?')}` prose "
                        f"says ch {n:02d} but the entry declares "
                        + ", ".join(f"{f}={v}" for f, v in declared.items())
                        + f" — one of them is stale (…{prose[max(0,m.start()-55):m.start()+55].strip()}…)")

    # --- rule 3: clue plant chapter vs the sigil's actual chapter -----------
    if whodunit_p.exists() and yaml is not None:
        data = yaml.safe_load(whodunit_p.read_text()) or {}
        declared = {c["id"]: c["plant_chapter"]
                    for c in (data.get("clues") or [])
                    if isinstance(c, dict) and isinstance(c.get("plant_chapter"), int)}
        where = {}
        for n, text in beats.items():
            for cid in re.findall(r'!([a-z0-9][a-z0-9-]*)', text):
                where.setdefault(cid, n)
        for cid, want in declared.items():
            n = where.get(cid)
            if n is None:
                continue
            got = next((c for c, (lo, hi) in ranges.items() if lo <= n <= hi), None)
            if got is not None and got != want:
                blocking.append(
                    f"clue-plant-mismatch: `{cid}` declares plant_chapter={want}, but its "
                    f"!{cid} sigil is on beat {n}, which the cut places in ch {got:02d} "
                    f"(\"{titles.get(got,'')}\")")

    for f in blocking:
        print(f"chapter_refs_check: {f}")
    if advisory:
        print("\nAdvisory — nothing blocks on these:" if blocking else "Advisory — nothing blocks on these:")
        for f in advisory:
            print(f"  {f}")
    if not blocking and not advisory:
        print(f"chapter_refs_check: book {book} — every chapter reference resolves, no findings")
    return 1 if blocking else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("book")
    ap.add_argument("--series-root", default=".")
    a = ap.parse_args()
    root = pathlib.Path(a.series_root).resolve()
    return check(root / "input" / f"book-{a.book}", root, a.book)


if __name__ == "__main__":
    sys.exit(main())
