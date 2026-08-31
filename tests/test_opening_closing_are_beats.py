"""Contract + regression test for
`docs/superpowers/specs/2026-08-29-opening-closing-are-beats-not-sentences-fix.md`.

The defect: `agents/drafter.md` told the drafter that `### Opening` and
`### Closing` were "instruction, not context" and that the chapter "opens and
lands exactly as they say". That instruction cannot be satisfied, because the
field it governs does not contain what it assumes. `**Opening:**` and
`**Closing (kind):**` are authored in `cut-plan.md` at plotting time, months
before any prose exists, and in practice they hold two different kinds of thing
with nothing marking which is which — sometimes a usable sentence ("Rourke fills
the kettle before he looks at the body"), sometimes a description of an effect
("The town has decided what her steadiness means before she has finished being
steady"). The second kind is not a sentence anyone would put in a novel and
cannot be reproduced verbatim, so the drafter had to decide unaided which it was
holding, and nothing in the packet, the map or the contract told it.

There is also a tense mismatch built into the mechanism: the fields are authored
in present tense and the series voice contract is third limited **past**, so the
one thing declared fixed was guaranteed to be altered by hand, differently each
time. Book 01 chapter 01 was drafted three times in one day against an unchanged
packet and produced three renderings of the same "verbatim" line (spec §2).

Two tests, matching spec §5, and they guard opposite directions:

1. `test_drafter_does_not_demand_verbatim_opening_or_closing` and
   `test_drafter_names_opening_and_closing_as_beats` pin the contract wording.
   This is a wording change rather than a behaviour change, so the assertion is
   on the agent definition text — that is the whole of the artefact being fixed.
   The second half matters as much as the first: deleting the offending sentence
   would satisfy a purely negative check while leaving the drafter with no
   guidance at all, which is not the fix the spec asked for.

2. `test_no_draft_reading_script_references_opening_or_closing` is the
   regression guard spec §5.2 asks for: nothing may compare a draft's first or
   last line to the packet's `Opening`/`Closing`, so a future checker cannot
   silently reintroduce the verbatim contract without this spec being revisited.
   The spec rejected that checker explicitly — it would enforce a rule that is
   unsatisfiable for the abstract fields, and it would have locked in book 01
   chapter 01's technically-wrong opening as correct.

   The guard is expressed as a **disjointness** rule over `scripts/` rather than
   as a list of forbidden files, so it keeps holding as scripts are added. Two
   sets are computed from the tree: scripts that read a chapter's prose artefact
   (`.draft.md` / `.final.md`), and scripts that name the `Opening`/`Closing`
   fields. Today those sets are disjoint by construction — the six draft readers
   (`assemble_book`, `book_status`, `draft_words`, `lmstudio_draft_chapter`,
   `preflight`, `readiness_check`) never name the fields, and the four scripts
   that do (`penny_story`, `story_cut`, `texture_apply`, `tension_check`) work on
   the cut plan and the outline, never on prose. A script that joined both sets
   would be one holding a draft's text and the field it was authored from, which
   is the shape the rejected checker would have to take.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DRAFTER = REPO / "agents" / "drafter.md"
SCRIPTS = REPO / "scripts"

# Language that makes the fields a script to copy rather than a beat to hit.
# `instruction, not context` is here because it is the clause that framed them
# as reproducible in the first place — the spec's diff removes it.
VERBATIM_MARKERS = [
    "instruction, not context",
    "exactly as they say",
    "reproduce them exactly",
    "exactly as written",
]

# `verbatim` and `word for word` are the words the demand is naturally made in,
# but they are also the words used to FORBID it — the spec's own replacement
# text reads "Do not reproduce them verbatim". So they are matched only when no
# negator governs them. A bare-word check here would reject the fix this file
# exists to enforce, which is a test that fails its own subject.
NEGATED_VERBATIM = re.compile(
    r"(?:do not|don't|never|not|rather than|instead of)\s+"
    r"(?:\w+\s+){0,4}?(?:verbatim|word[- ]for[- ]word)",
    re.IGNORECASE,
)
VERBATIM_WORDS = re.compile(r"verbatim|word[- ]for[- ]word", re.IGNORECASE)

# A chapter's prose artefacts. A script touching either is holding draft text.
DRAFT_ARTEFACTS = re.compile(r"\.(?:draft|final)\.md")
# The cut-plan/outline fields the drafter must not be told to reproduce.
FIELD_NAMES = re.compile(r"\bOpening\b|\bClosing\b")


def packet_bullet() -> str:
    """The `- **The packet**` bullet of `agents/drafter.md` — the passage that
    governs what `### Opening` and `### Closing` mean to the drafter.

    Bullets in the Inputs list start with `- **` at column 0 and continue
    through their indented continuation lines, so the bullet is everything from
    its own marker up to the next one.
    """
    lines = DRAFTER.read_text(encoding="utf-8").splitlines()
    starts = [i for i, ln in enumerate(lines) if ln.startswith("- **")]
    for n, i in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        block = "\n".join(lines[i:end])
        if "### Opening" in block and "### Closing" in block:
            return block
    raise AssertionError(
        "no bullet in agents/drafter.md governs both `### Opening` and "
        "`### Closing` — the contract this spec fixes has moved or been deleted"
    )


def contract_clause() -> str:
    """The clause inside that bullet that says what the two fields ARE.

    Runs from the pair's FIRST mention to `### Texture`, which begins the next
    field's contract. Deliberately not anchored on the verb: the fix changes it
    from "are" to "name", and a test that broke on its own fix would be
    worthless. Nor on the pair's LAST mention — the fixed wording names
    `### Opening` a second time ("must open on what `### Opening` describes"),
    so a trailing anchor slices the contract's own subject off the front.
    """
    bullet = packet_bullet()
    start = bullet.index("`### Opening`")
    end = bullet.index("`### Texture` is", start)
    return bullet[start:end]


def test_drafter_does_not_demand_verbatim_opening_or_closing():
    passage = packet_bullet()
    found = [m for m in VERBATIM_MARKERS if m in passage.lower()]
    # An unnegated "verbatim" is a demand; a negated one is the fix.
    if VERBATIM_WORDS.search(NEGATED_VERBATIM.sub("", passage)):
        found.append("verbatim (unnegated)")
    assert not found, (
        "agents/drafter.md still instructs the drafter to reproduce `### Opening`"
        f" / `### Closing` exactly: {found}. Those fields are authored at plotting"
        " time, in present tense, and may be phrased as a description of an effect"
        " rather than as a usable sentence — so a verbatim contract is"
        " unsatisfiable and is silently renegotiated by every drafter"
        " (spec §1, §2)."
    )


def test_drafter_names_opening_and_closing_as_beats():
    # Scoped to the governing clause, not the whole bullet: `Beats covered:`
    # and "each of its beats happens" both already sit in this bullet for
    # unrelated reasons, so a bullet-wide search for "beat" passes no matter
    # what the contract says.
    clause = contract_clause()
    assert "beat" in clause.lower(), (
        "agents/drafter.md no longer tells the drafter what `### Opening` and"
        " `### Closing` ARE. Removing the verbatim instruction is only half the"
        " fix: the fields name the chapter's first and last BEAT, not its first"
        " and last sentence, and the drafter writes the sentences (spec §3)."
    )


def test_no_draft_reading_script_references_opening_or_closing():
    both = []
    for path in sorted(SCRIPTS.glob("*.py")):
        src = path.read_text(encoding="utf-8")
        if DRAFT_ARTEFACTS.search(src) and FIELD_NAMES.search(src):
            both.append(path.name)
    assert not both, (
        f"{both} both read a chapter's prose artefact and name the"
        " `Opening`/`Closing` fields. That is the shape of a checker comparing a"
        " draft's first or last line to the packet — the fix the spec rejected"
        " (spec §3, 'Adding a checker that enforces the verbatim contract'). It"
        " would enforce a rule that is unsatisfiable for the abstract fields."
    )
