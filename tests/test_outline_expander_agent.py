"""Contract test: agents/outline-expander.md's canonical per-chapter template
must teach wiring-footer syntax scripts/penny_wiring.py actually parses.

A prior version of this template showed a bare `Because: …` / `Opens: x.
Closes: y. Carries: z.` / `Hook (cliffhanger|promise): …` footer — prose that
LOOKS like the wired-outline convention but that penny_wiring.FIELD_RE and
GRADE_RE silently ignore (FIELD_RE only matches the bulleted-bold
`- **Field:** value` form; GRADE_RE only matches a `[cliffhanger]`/`[promise]`
bracket). This mirrors test_outline_check.py's
test_shipped_template_teaches_syntax_the_wiring_parser_accepts: extract the
real example block and run it through the real parser, not a lookalike.
"""
import re
from pathlib import Path

from scripts.penny_wiring import parse_wired_chapters

REPO = Path(__file__).resolve().parent.parent
AGENT_DOC = REPO / "agents" / "outline-expander.md"


def _extract_template_block(text: str) -> str:
    """The fenced ``` block immediately following the 'Canonical template'
    label — the one worked example this doc teaches."""
    marker = "**Canonical template"
    idx = text.index(marker)
    fence_start = text.index("```", idx) + 3
    fence_end = text.index("```", fence_start)
    return text[fence_start:fence_end]


def test_agent_template_teaches_syntax_the_wiring_parser_accepts():
    text = AGENT_DOC.read_text(encoding="utf-8")
    block = _extract_template_block(text)

    # The template is reused for every chapter, so its heading carries the
    # literal placeholder "NN" for the chapter number (same convention as
    # "Because: <ch NN — …>" inside the footer). CHAPTER_RE needs a real
    # digit to recognise the block as a chapter at all — substitute one
    # concrete number, exactly as a showrunner would when actually using
    # the template, before handing it to the real parser.
    assert "## Chapter NN" in block, "template heading convention changed"
    block = block.replace("## Chapter NN", "## Chapter 01", 1)

    chapters = parse_wired_chapters(block)
    assert len(chapters) == 1
    ch = chapters[0]

    assert ch["because"], "Because: must resolve — bare prose form is invisible to FIELD_RE"
    assert ch["opens"], "Opens: must resolve to at least one (q-slug, phrasing) pair"
    assert ch["hook_grade"] in ("cliffhanger", "promise"), \
        "Hook's grade must be read from a real [cliffhanger]/[promise] bracket"
    assert ch["tracks"], "Track Movement rows (- **M:** / **P:** / **R:** / **B:**) must be present"
    assert ch["required_beats"], "Required Beats must resolve non-empty"

    # No stray "### Scene" section — packet format carries no scenes.
    assert ch["scenes"] == []


def test_agent_template_footer_is_bulleted_bold_not_bare_prose():
    """Regression pin for the exact defect this fixes: the old footer's bare
    'Because: …' / 'Opens: x. Closes: y.' lines must never come back."""
    text = AGENT_DOC.read_text(encoding="utf-8")
    block = _extract_template_block(text)
    assert not re.search(r"^Because:\s", block, re.MULTILINE)
    assert not re.search(r"^Opens:\s", block, re.MULTILINE)
    assert not re.search(r"^Hook \(cliffhanger\|promise\):", block, re.MULTILINE)
