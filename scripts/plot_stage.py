"""Save-point machinery for the plotting workshop (spec §7).

Deterministic: which stage is next, what is stale (built_from_* sha256
fingerprints — the clear-dev binding trick applied to planning files), and the
blind reader's-copy rendering (Task 9). The /plot-book runbook only ever ASKS
this script; it never improvises stage detection.

  python3 scripts/plot_stage.py status 01
  python3 scripts/plot_stage.py stamp 01 input/book-01/plot/ending.md \
      --from input/book-01/plot/premise.md
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import penny_paths
from scripts.penny_meta import parse_frontmatter, write_frontmatter_field

STAGE_ORDER = ["premise", "ending", "turning-points", "counterplot",
               "chapters", "weave", "readback"]

_UPSTREAM = {
    "premise": ["material"],           # material is optional (spec §4)
    "ending": ["premise"],
    "turning-points": ["premise", "ending"],
    "counterplot": ["ending", "turning-points"],
    "chapters": ["turning-points", "counterplot"],
    "weave": [],                       # done-ness is the skeleton's woven flag
    "readback": ["chapters"],
}


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _root(repo_root) -> Path:
    return Path(repo_root) if repo_root is not None else penny_paths.series_root()


def stage_paths(book: str, root: Path) -> dict:
    plot = root / "input" / f"book-{book}" / "plot"
    out = root / "output" / f"book-{book}"
    skel = root / "input" / f"book-{book}" / "outline-skeleton.md"
    return {"material": plot / "material.md", "premise": plot / "premise.md",
            "ending": plot / "ending.md", "turning-points": plot / "turning-points.md",
            "counterplot": out / "mystery-solution.md", "chapters": skel,
            "weave": skel, "readback": out / "reports" / "outline-fan.md"}


def stage_status(book: str, *, repo_root=None) -> list:
    root = _root(repo_root)
    paths = stage_paths(book, root)
    rows = []
    for name in STAGE_ORDER:
        p = paths[name]
        if not p.is_file():
            rows.append((name, "missing", str(p)))
            continue
        fm = parse_frontmatter(p.read_text(encoding="utf-8"))
        if name == "weave":
            done = str(fm.get("woven", "")).strip().lower() == "true"
            rows.append((name, "done" if done else "missing", "woven flag"))
            continue
        stale = []
        for up in _UPSTREAM[name]:
            upath = paths[up]
            field = f"built_from_{upath.stem}"
            recorded = fm.get(field)
            if recorded is None:
                if up == "material" and not upath.is_file():
                    continue  # absent material is a legitimate blank start
                stale.append(f"{field} unstamped")
            elif not upath.is_file() or _sha(upath) != recorded:
                stale.append(f"{field} mismatch")
        rows.append((name, "stale" if stale else "done", "; ".join(stale)))
    return rows


def next_stage(rows) -> "str | None":
    for name, state, _ in rows:
        if state != "done":
            return name
    return None


def stamp(book: str, target, upstreams, *, repo_root=None) -> None:
    p = Path(target)
    text = p.read_text(encoding="utf-8")
    if not text.startswith("---"):
        text = "---\n---\n\n" + text
    for up in upstreams:
        upp = Path(up)
        text = write_frontmatter_field(text, f"built_from_{upp.stem}", _sha(upp))
    p.write_text(text, encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Plotting-workshop stage machinery.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_st = sub.add_parser("status")
    p_st.add_argument("book")
    p_sp = sub.add_parser("stamp")
    p_sp.add_argument("book")
    p_sp.add_argument("target")
    p_sp.add_argument("--from", dest="upstreams", nargs="+", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "status":
        rows = stage_status(args.book)
        for name, state, detail in rows:
            print(f"stage {name}: {state}" + (f" ({detail})" if state == "stale" and detail else ""))
        nxt = next_stage(rows)
        print(f"next: {nxt if nxt else 'none — plan complete'}")
        return 0
    if args.cmd == "stamp":
        stamp(args.book, args.target, args.upstreams)
        return 0
    ap.error(f"unknown command {args.cmd!r}")  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())
