"""Outline-review feedback ledger + banner (deterministic, advisory, reporting-only).

Owns the append-only feedback ledger for the pre-draft outline review tier:
- `append` : append a review pass's prose points as new OF-<n> items (never mutates
  existing items or the showrunner's per-item state).
- `status` : the draft-time banner — open-item backlog + outline staleness. NEVER exits
  nonzero (it must never block drafting).
- `render` : regenerate the side-by-side markdown reading view from the yaml.

Nested human-edited data → PyYAML (the whodunit-ledger side of the dependency-split rule).
Zero LLM/genre judgment. See spec 2026-07-09-outline-developmental-review-design.md.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml

from scripts import penny_paths

VALID_STATES = ("open", "solved", "rejected")


def ledger_path(book, repo_root=None) -> Path:
    return penny_paths.output_path(f"book-{book}/reports/outline-feedback.yaml", root=repo_root)


def view_path(book, repo_root=None) -> Path:
    return penny_paths.output_path(f"book-{book}/reports/outline-review.md", root=repo_root)


def outline_src_path(book, repo_root=None) -> Path:
    return penny_paths.input_path(f"book-{book}/outline.md", root=repo_root)


def sha256_of(path) -> str:
    p = Path(path)
    if not p.is_file():
        return ""
    return hashlib.sha256(p.read_bytes()).hexdigest()


def empty_ledger(book) -> dict:
    return {"book": book, "reviewed_outline_sha256": "", "items": []}


def load_ledger(book, repo_root=None) -> dict:
    p = ledger_path(book, repo_root)
    if not p.is_file():
        return empty_ledger(book)
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return empty_ledger(book)
    if not isinstance(data, dict):
        return empty_ledger(book)
    data.setdefault("items", [])
    data.setdefault("reviewed_outline_sha256", "")
    return data


def max_id_num(items) -> int:
    nums = []
    for it in items:
        raw = str(it.get("id", ""))
        if raw.startswith("OF-") and raw[3:].isdigit():
            nums.append(int(raw[3:]))
    return max(nums) if nums else 0


def max_pass(items) -> int:
    passes = [it.get("pass", 0) for it in items if isinstance(it.get("pass"), int)]
    return max(passes) if passes else 0


def append_items(ledger, new_points, *, reviewed_sha) -> dict:
    out = copy.deepcopy(ledger)
    items = out.setdefault("items", [])
    next_id = max_id_num(items) + 1
    next_pass = max_pass(items) + 1
    for pt in new_points:
        item = {
            "id": f"OF-{next_id}",
            "source": pt["source"],
            "pass": next_pass,
            "state": "open",
            "text": pt["text"],
        }
        rec = pt.get("recommendation")
        if isinstance(rec, str) and rec.strip():
            item["recommendation"] = rec
        # Optional measurements (spec 2026-07-30 §6.1). Stored OPAQUELY — the
        # ledger records and renders them, it never interprets them, so a new
        # finding type needs no change here. `append` is operator-driven and
        # fails loudly (module docstring), so a malformed value is named rather
        # than dropped: a silently-discarded metric would leave an item reading
        # as a vague observation, which is the exact failure §6.1 exists to fix.
        chapters = pt.get("chapters")
        if chapters is not None:
            if (not isinstance(chapters, list)
                    or not all(isinstance(c, int) and not isinstance(c, bool)
                               for c in chapters)):
                raise SystemExit(
                    f"append: item {item['id']}: 'chapters' must be a list of "
                    f"integers, got {chapters!r}")
            item["chapters"] = list(chapters)
        metrics = pt.get("metrics")
        if metrics is not None:
            if not isinstance(metrics, dict):
                raise SystemExit(
                    f"append: item {item['id']}: 'metrics' must be a mapping, "
                    f"got {type(metrics).__name__}")
            item["metrics"] = dict(metrics)
        items.append(item)
        next_id += 1
    out["reviewed_outline_sha256"] = reviewed_sha
    return out


def open_items(ledger) -> list:
    return [it for it in ledger.get("items", []) if it.get("state") == "open"]


def status_line(book, repo_root=None) -> str:
    if not ledger_path(book, repo_root).is_file():
        return f"no outline review yet — consider /review-outline {book}"
    ledger = load_ledger(book, repo_root)
    cur = sha256_of(outline_src_path(book, repo_root))
    if cur != ledger.get("reviewed_outline_sha256", ""):
        return f"⚠ OUTLINE changed since its last review — re-run /review-outline {book}"
    opens = open_items(ledger)
    if opens:
        ids = ", ".join(it["id"] for it in opens)
        rel = f"output/book-{book}/reports/{ledger_path(book, repo_root).name}"
        return (f"⚠ OUTLINE: {len(opens)} open feedback item(s) ({ids}) — "
                f"see {rel}. Drafting anyway.")
    return f"✓ outline reviewed — no open items (book {book})"


def render_view(ledger) -> str:
    book = ledger.get("book", "?")
    lines = [f"# Outline review — book {book}", "",
             "_Side-by-side feedback; edit `state` in outline-feedback.yaml to disposition._", ""]
    buckets = [("Open", "open"), ("Solved", "solved"), ("Rejected", "rejected")]
    for title, state in buckets:
        rows = [it for it in ledger.get("items", []) if it.get("state") == state]
        lines.append(f"## {title} ({len(rows)})")
        if not rows:
            lines.append("_none_")
        for it in rows:
            head = f"- **{it.get('id')}** · _{it.get('source')}_ · pass {it.get('pass')}"
            chs = it.get("chapters")
            if isinstance(chs, list) and chs:
                head += " · ch " + ", ".join(str(c) for c in chs)
            lines.append(head)
            lines.append(f"  {it.get('text', '').strip()}")
            mets = it.get("metrics")
            if isinstance(mets, dict) and mets:
                # Rendered generically so an unrecognised metric key still shows.
                # M13: a `never` finding's first_suspected is legitimately None
                # (spec §6.1) — render it as "—" rather than the literal string
                # "None" in a document the showrunner reads.
                lines.append("  _" + " · ".join(
                    f"{k}={'—' if v is None else v}" for k, v in mets.items()) + "_")
            rec = it.get("recommendation")
            if isinstance(rec, str) and rec.strip():
                lines.append(f"  **→** {rec.strip()}")
        lines.append("")
    return "\n".join(lines)


def _cli_render(book, root):
    ledger = load_ledger(book, repo_root=root)
    p = view_path(book, repo_root=root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_view(ledger), encoding="utf-8")
    print(f"rendered {p}")


def write_ledger(ledger, book, repo_root=None) -> None:
    p = ledger_path(book, repo_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(ledger, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _cli_append(book, points_path, root, source=None):
    if not points_path:
        raise SystemExit("append: --points <json-file> is required")
    new_points = json.loads(Path(points_path).read_text(encoding="utf-8"))
    ledger_before = load_ledger(book, repo_root=root)
    if source:
        # FINAL REVIEW I6: --source marks a non-panel append (e.g. /plot-book's
        # fan-audit, which reviews outline-skeleton.md, not outline.md — the
        # file this sha normally stamps). Leave reviewed_outline_sha256
        # exactly as it was: a source that never reviewed outline.md must not
        # claim to have, either by re-stamping it to the current sha (which
        # would silently clear a staleness warning no panel review earned) or
        # by stamping it "" (which would falsely flag outline.md as changed
        # the moment it is first written).
        reviewed_sha = ledger_before.get("reviewed_outline_sha256", "")
    else:
        reviewed_sha = sha256_of(outline_src_path(book, repo_root=root))
    ledger = append_items(ledger_before, new_points, reviewed_sha=reviewed_sha)
    write_ledger(ledger, book, repo_root=root)
    _cli_render(book, root)
    print(f"appended {len(new_points)} item(s) to book-{book} outline ledger")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Outline-review feedback ledger tool.")
    ap.add_argument("cmd", choices=["status", "render", "append"])
    ap.add_argument("book")
    ap.add_argument("--root", default=None, help="repo/series root override (tests)")
    ap.add_argument("--points", help="append: path to a JSON array of "
                                     "{source,text,recommendation?,chapters?,metrics?}")
    ap.add_argument("--source", default=None,
                     help="append: path of the artifact this pass actually reviewed "
                          "(e.g. outline-skeleton.md, not outline.md); when given, "
                          "reviewed_outline_sha256 is left untouched rather than "
                          "re-stamped from outline.md")
    # NOTE: argparse usage errors (missing `book`, `cmd` outside choices) still exit 2
    # here via parse_args — that's a mis-written invocation, not a showrunner runtime
    # state, so it is deliberately NOT suppressed. The exit-0 guarantee below covers
    # only the status *operation* (path resolution, ledger load, etc.) once argv parses.
    args = ap.parse_args(argv)
    root = Path(args.root) if args.root else None
    if args.cmd == "status":
        # status is advisory and must never block /draft-chapter — see module
        # docstring. This exit-0 guarantee is scoped to status ONLY: render and
        # append are operator-driven and must fail loudly (see below).
        try:
            print(status_line(args.book, repo_root=root))
        except (Exception, SystemExit) as exc:
            print(f"(outline-review status unavailable: {exc})")
        return 0
    elif args.cmd == "render":
        _cli_render(args.book, root)
    elif args.cmd == "append":
        _cli_append(args.book, args.points, root, source=args.source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
