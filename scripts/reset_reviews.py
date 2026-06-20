"""Re-run cleanup for the Penny Review Bus.

/review-chapter is re-run routinely (single-pass + manual loop). This empties a
chapter's verdict files and removes the stale sibling gate.md so each run's gate
reflects ONLY that run's verdicts — a fixed blocker from run 1 must not linger.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def reset_reviews(reviews_dir) -> None:
    root = Path(reviews_dir)
    if root.is_dir():
        for path in root.glob("*.md"):
            path.unlink()
    # Remove the stale sibling gate.md (chapters/<chapter>.gate.md).
    chapter = root.name.replace(".reviews", "")
    gate = root.parent / f"{chapter}.gate.md"
    if gate.exists():
        gate.unlink()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Empty a chapter's reviews dir + stale gate.md")
    parser.add_argument("reviews_dir")
    args = parser.parse_args(argv)
    reset_reviews(args.reviews_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
