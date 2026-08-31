"""Lint for
`docs/superpowers/specs/2026-08-29-runbook-render-corrupts-positional-vars-fix.md`
§4c/§4d, and the only test that would catch the next occurrence (§5.1).

The defect: `commands/*.md` runbooks are rendered into an agent's context when
a command is invoked, and that rendering substitutes argument placeholders
**uniformly, including inside fenced code blocks**, and **zero-indexed** — `$0`
is the first argument, `$1` the second. Every runbook here was written in the
one-indexed shell convention, so `book=$1` bound the chapter and `chapter=$2`
bound a third argument that did not exist.

Nothing in the repository looked wrong. Two things hid it: this project runs
`/command 01 01` almost exclusively, and when the first and second arguments
are the same number an off-by-one is arithmetically invisible; and the thing
reading a runbook is a model, not a shell, so an agent handed `book=07` for
`/draft-chapter 01 07` reasons out what was meant and proceeds. It surfaced
only inside an `awk` one-liner, where `$0` means "the whole current record" and
there was no intent for the model to recover — `index($0, h)` rendered as
`index(01, h)`, always false, and the chapter brief was written empty. The
`ledger-updater` then ran unscoped and the finalize looked successful.

**The fix is named arguments, not renumbering.** Confirmed empirically on
2026-08-31 by rendering `commands/argprobe.md` with three distinguishable
arguments (the §2b procedure, re-run as §5's preamble demands):

    - named:      book=AAA | chapter=BBB | flag=CCC | extra=
    - positional: p0=AAA | p1=BBB | p2=CCC | p3=$3
    - escaped:    esc-pos=$0 | esc-named=$book

Three things follow, and the third was anticipated by nobody:

1. Named arguments bind correctly in plugin commands, not just skills — the
   open question the spec could not answer.
2. Positionals are zero-indexed, confirming §2b.
3. **An absent named argument renders EMPTY; an absent positional stays
   LITERAL** (`extra=` vs `p3=$3`). So under renumbering, `/assemble-book 01`
   with no `--approve` renders `flag=$1` — the literal characters — which is
   broken shell. Named arguments render `flag=`, which is correct. Renumbering
   would not merely have left the trap the spec warned about; it would have
   left the optional-flag case actively wrong in three runbooks.

Hence the rule this file enforces is the simple one §4c offers for the named
case: **no bare positional in a runbook, anywhere** — not merely inside fenced
blocks. Prose is substituted too, and the eight inline `` `book=$1` `` sites
were as wrong as the seven in code; they were survivable only because a reader
corrects them by comprehension. A rule with no "inside a code block" clause is
also far simpler to state, and it is what keeps the convention honest.
"""
import re
from pathlib import Path

import pytest

COMMANDS = Path(__file__).resolve().parents[1] / "commands"

# `$0`, `$12`, `${2:-}` — a `$` before a digit, optionally braced. A preceding
# backslash is the documented escape for a literal and is allowed.
BARE_POSITIONAL = re.compile(r"(?<!\\)\$\{?\d")

# The one file exempt, and the reason it must stay exempt: its entire purpose
# is to carry unescaped placeholders so a render can be read off. It is how
# §5.3's re-confirmation procedure is run after a Claude Code upgrade, when the
# substitution rules may have changed under us — the spec's own history (a day
# spent confidently wrong about the indexing) is why that check has to be cheap
# enough to actually repeat.
PROBE = "argprobe.md"


def runbooks():
    return sorted(p for p in COMMANDS.glob("*.md") if p.name != PROBE)


@pytest.mark.parametrize("path", runbooks(), ids=lambda p: p.name)
def test_runbook_has_no_bare_positional_argument(path):
    hits = [
        f"{path.name}:{n}: {line.strip()}"
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if BARE_POSITIONAL.search(line)
    ]
    assert not hits, (
        "bare positional argument(s) in a runbook — these are substituted "
        "before the agent reads the file, and they are ZERO-indexed, so `$1` "
        "is the SECOND argument:\n  " + "\n  ".join(hits) +
        "\nUse the named form (`$book`, `$chapter`) declared in the file's "
        "`arguments:` frontmatter. To write a literal, escape it: `\\$0`."
    )


def test_the_probe_is_the_only_exemption():
    # A one-file exemption is defensible; a growing list is how a lint dies.
    assert (COMMANDS / PROBE).is_file(), (
        f"commands/{PROBE} is exempt from the positional lint but does not "
        "exist. Either restore it or drop the exemption — an exemption for a "
        "missing file silently widens if that name is ever reused."
    )


# A hazard named arguments introduce that positionals did not, and the one this
# migration actually hit: once `root` is declared in `arguments:`, EVERY `$root`
# in the file is replaced by the argument before the shell ever runs. So a shell
# variable sharing a declared argument's name can never be read back — the
# assignment happens, and every read of it renders as the raw argument instead.
# `new-series` computed `root="${root_arg:-$HOME/myBooks}"` and then used
# `target="$root/$name"`, which would have rendered as the empty argument and
# built `target="/cozy-pelicans"` whenever the optional root was omitted. The
# variable is now `books_root`. The rule: a declared name may only ever be
# assigned its own placeholder.
ARGUMENTS_LINE = re.compile(r"(?m)^arguments:\s*\[([^\]]*)\]")
COMMENT = re.compile(r"\s+#.*$")


def declared_arguments(text):
    m = ARGUMENTS_LINE.search(text)
    return [n.strip() for n in m.group(1).split(",") if n.strip()] if m else []


@pytest.mark.parametrize("path", runbooks(), ids=lambda p: p.name)
def test_declared_argument_names_are_never_reused_as_shell_variables(path):
    text = path.read_text(encoding="utf-8")
    bad = []
    for name in declared_arguments(text):
        assign = re.compile(rf"^\s*{re.escape(name)}=(.*)$")
        for n, line in enumerate(text.splitlines(), 1):
            m = assign.match(line)
            if not m:
                continue
            value = COMMENT.sub("", m.group(1)).strip().strip('"')
            if value != f"${name}":
                bad.append(f"{path.name}:{n}: {line.strip()}")
    assert not bad, (
        "a declared argument's name is reused as a shell variable holding "
        "something else:\n  " + "\n  ".join(bad) +
        f"\nEvery `${{name}}` in this file is substituted before the shell runs, "
        "so this value can never be read back — the reads render as the raw "
        "argument. Give the shell variable a different name (e.g. `books_root`)."
    )
