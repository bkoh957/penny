"""The one module that knows the layout (design: engine-plugin + series-folders).

Two roots:
  - plugin_root(): the engine repo where this file lives (code + config DEFAULTS).
  - series_root(): the nearest ancestor of the cwd that contains a `.penny/` dir
    (that series' DATA). Hard error if none — never guess which series.

Data paths (series/, input/, output/, .penny/) anchor on the series root.
Config paths overlay: series override if present, else plugin default.
"""
from __future__ import annotations

import sys
from pathlib import Path

_MARKER = ".penny"


def plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def series_root(start: Path | None = None) -> Path:
    cur = Path(start).resolve() if start is not None else Path.cwd().resolve()
    for d in (cur, *cur.parents):
        if (d / _MARKER).is_dir():
            return d
    sys.exit(f"penny-paths: no series root (no '{_MARKER}/' at or above {cur})")


def _root(root: Path | None) -> Path:
    return Path(root).resolve() if root is not None else series_root()


def config_path(rel: str, root: Path | None = None) -> Path:
    override = _root(root) / "config" / rel
    return override if override.exists() else plugin_root() / "config" / rel


def series_path(rel: str, root: Path | None = None) -> Path:
    return _root(root) / "series" / rel


def input_path(rel: str, root: Path | None = None) -> Path:
    return _root(root) / "input" / rel


def output_path(rel: str, root: Path | None = None) -> Path:
    return _root(root) / "output" / rel


def penny_path(rel: str, root: Path | None = None) -> Path:
    return _root(root) / _MARKER / rel


def active(root: Path | None = None) -> str:
    return _root(root).name


def _main(argv: list[str]) -> int:
    if not argv:
        print("usage: penny_paths resolve <config|series|input|output|penny> <rel> | active", file=sys.stderr)
        return 2
    if argv[0] == "active":
        print(active())
        return 0
    if argv[0] == "resolve" and len(argv) == 3:
        kind, rel = argv[1], argv[2]
        fn = {"config": config_path, "series": series_path, "input": input_path,
              "output": output_path, "penny": penny_path}.get(kind)
        if fn is None:
            print(f"penny-paths: unknown kind '{kind}'", file=sys.stderr)
            return 2
        print(fn(rel))
        return 0
    print("usage: penny_paths resolve <kind> <rel> | active", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
