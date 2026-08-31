---
description: Throwaway probe — verifies how argument placeholders substitute into a plugin command. Delete after use.
argument-hint: <a> <b> <c>
arguments: [book, chapter, flag, extra]
---
# Argument substitution probe

**Do nothing.** Create no files, run no commands, change no state. Your only job is to
report the two blocks below **exactly as you received them**, character for character,
so the substitution can be read off.

## Prose (outside a fenced block)

- named:      book=$book | chapter=$chapter | flag=$flag | extra=$extra
- positional: p0=$0 | p1=$1 | p2=$2 | p3=$3
- all:        $ARGUMENTS
- escaped:    esc-pos=\$0 | esc-named=\$book

## Inside a fenced code block

```bash
book=$book
chapter=$chapter
flag=$flag
extra=$extra
p0=$0
p1=$1
p2=$2
awk '{ print $0 }' file.md
```

## Braced and default forms

```bash
braced_present=${book}
braced_absent=${extra}
default_present=${book:-FALLBACK}
default_absent=${extra:-FALLBACK}
escaped_braced=\${extra:-FALLBACK}
plus_absent=${extra:+"$extra"}
env_untouched=${CLAUDE_PLUGIN_ROOT}
```

Report all blocks verbatim, then stop.
