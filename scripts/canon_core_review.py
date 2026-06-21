"""Reserved per-book demotion hook (Phase-6 no-op; Phase-8 fills the body).

Per the canon-core demotion design §7.1, coldness is a cross-book property that
cannot fire on Book 1 — so the per-book review cadence is a *hook* only. This
script exists, takes the exact Phase-8 args (`--book`, `--canon-core`), and returns
an empty candidate list. The interface is pinned so Phase 8 fills in the detector
body with no engine edit. The Phase-8 candidate shape is:

    {id, fact, last_referenced, active_window, verdict, proposed_target}
"""
from __future__ import annotations

import argparse
import json


def review(book: str, canon_core: str) -> list:
    """Return demotion candidates for `book`. Phase 6: always empty (no behavior)."""
    return []


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Per-book canon-core demotion review (reserved).")
    ap.add_argument("--book", required=True)
    ap.add_argument("--canon-core", required=True)
    args = ap.parse_args(argv)
    print(json.dumps(review(args.book, args.canon_core)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
