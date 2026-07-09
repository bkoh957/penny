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

import copy
import hashlib
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
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
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
        items.append({
            "id": f"OF-{next_id}",
            "source": pt["source"],
            "pass": next_pass,
            "state": "open",
            "text": pt["text"],
        })
        next_id += 1
    out["reviewed_outline_sha256"] = reviewed_sha
    return out
