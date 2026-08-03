import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_live_reference_to_the_retired_skeleton():
    """docs/ keeps its history; live engine surfaces must not name the file."""
    hits = subprocess.run(
        ["grep", "-rn", "outline-skeleton", "scripts", "commands", "agents",
         "genres", "README.md", "CLAUDE.md"],
        cwd=ROOT, capture_output=True, text=True).stdout.strip()
    assert hits == "", f"still naming the retired skeleton:\n{hits}"
