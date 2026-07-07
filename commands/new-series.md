---
description: Scaffold a brand-new series' data folder (directory contract only — no story content) so /plan-mystery 01 can run there.
argument-hint: <name> [myBooks-root]
---
# /new-series

The multi-series front door (design: engine-plugin + series-folders — see
`docs/superpowers/specs/2026-07-03-multi-series-packs-design.md`). The engine is
genre/location-agnostic; every series lives in its own folder **outside** this repo,
anchored by a `.penny/` marker that `${CLAUDE_PLUGIN_ROOT}/scripts/penny_paths.py`'s `series_root()` walks
up from cwd to find. This command creates that folder's directory contract — the
exact shape `series_root()` and the config overlay (`config_path()`) expect — and
**invents no story content**: no bible, no cast, no whodunit. Those come later, from
inside the new folder, via `/scaffold-book` or `/plan-mystery`.

## Steps

1. **Parse args:** `name=$1` (kebab-case series slug, e.g. `cozy-pelicans`), optional
   `root=${2:-$HOME/myBooks}` — the `~/myBooks` root is configurable per-invocation;
   default is `~/myBooks`.

2. **Refuse to clobber:** this command creates a series, it never merges into an
   existing one.

   ```bash
   target="$root/$name"
   if [ -e "$target" ]; then
     echo "new-series: $target already exists — refusing to overwrite" >&2
     exit 1
   fi
   ```

3. **Create the directory contract** — empty stubs only, matching the shape read by
   `penny_paths.series_root()` (the `.penny/` marker) and `config_path()` (the
   series-override-else-plugin-default overlay):

   ```bash
   mkdir -p "$target"/.penny/locks
   mkdir -p "$target"/series/continuity/characters
   mkdir -p "$target"/series/continuity/locations
   mkdir -p "$target"/series/continuity/threads
   mkdir -p "$target"/series/whodunit
   mkdir -p "$target"/config/voice-pack
   mkdir -p "$target"/config/setting-pack
   mkdir -p "$target"/config/genre-pack
   mkdir -p "$target"/input
   mkdir -p "$target"/output
   touch "$target"/series/continuity/canon-core.md
   ```

   The `config/` directories are created empty: `config_path()` will fall back to the
   plugin's shipped defaults (its own `config/run-config.md`, `config/voice-pack/…`,
   etc.) for anything this series hasn't overridden. A new series inherits ALL engine
   config defaults; to override one, the showrunner adds that file under the series'
   `config/` later (e.g., edit `$target/config/run-config.md`).

4. **`git init` the new folder** — each series is its own repo, independent of the
   engine's:

   ```bash
   git -C "$target" init -q
   ```

5. **Print the path and the next step** — this command never drafts, plans, or
   locks anything itself:

   ```bash
   echo "Created series '$name' at $target"
   echo "cd $target && run /plan-mystery 01"
   ```

## Deferred (do not build here)
Populating `series/continuity/canon-core.md` or any bible content (that is
`/scaffold-book`'s or the showrunner's job, never this command's); multi-root
discovery beyond a single `--root`/`$HOME/myBooks` default; series-to-series
copy/fork (this is create-empty only).
