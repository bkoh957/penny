import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path("scripts/penny-statusline.sh").resolve()


@pytest.fixture
def penny_root(tmp_path):
    """Build a throwaway Penny tree; return a runner that invokes the status line."""
    (tmp_path / ".penny").mkdir()

    def write_stage(line: str):
        (tmp_path / ".penny" / "current-stage").write_text(line + "\n", encoding="utf-8")

    def write_outline(book: str, chapter_count: int):
        d = tmp_path / "input" / f"book-{book}"
        d.mkdir(parents=True, exist_ok=True)
        body = "# Outline\n\n" + "".join(f"## Chapter {i}\n\n" for i in range(1, chapter_count + 1))
        (d / "outline.md").write_text(body, encoding="utf-8")

    def write_blocking(book: str, chapter: str, count: int):
        d = tmp_path / "output" / f"book-{book}" / "chapters" / f"ch-{chapter}.reviews"
        d.mkdir(parents=True, exist_ok=True)
        body = "".join(f"BLOCKING: issue {i}\n" for i in range(count))
        (d / "inspector-continuity.md").write_text(body or "ok\n", encoding="utf-8")

    def run(session_json: str) -> str:
        # Disable the ccstatusline append so output stays deterministic and the
        # tests don't shell out to `npx ccstatusline` on every run.
        env = dict(os.environ, PENNY_ROOT=str(tmp_path), PENNY_NO_CCSTATUSLINE="1")
        proc = subprocess.run(
            ["bash", str(SCRIPT)],
            input=session_json, capture_output=True, text=True, env=env, check=True,
        )
        return proc.stdout.strip()

    return type("PennyRoot", (), {
        "path": tmp_path, "write_stage": staticmethod(write_stage),
        "write_outline": staticmethod(write_outline),
        "write_blocking": staticmethod(write_blocking), "run": staticmethod(run),
    })
