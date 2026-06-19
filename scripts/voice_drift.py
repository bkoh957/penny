"""Voice-drift checker — statistical prose evidence (Tier-3, evidence-only).

Detection patterns/algorithms live in this file (stable). Tunable thresholds and
the compounding banned-phrase / metaphor lists live in
config/voice-pack/ai-tics-config.yaml (authoritative). Per spec, this checker NEVER
emits BLOCKING: lines — its flags are evidence the 2b voice inspector weighs.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow `import scripts.*` when this file is run directly as `python3 scripts/voice_drift.py`
# (direct-run puts scripts/ on sys.path, not the repo root). Harmless under pytest.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml

DEFAULT_CONFIG = Path("config/voice-pack/ai-tics-config.yaml")


def load_config(path) -> dict:
    """Load the tic config. Hard-fail (SystemExit) if missing/unreadable/malformed —
    no hardcoded threshold fallback (spec §3.3)."""
    path = Path(path)
    if not path.is_file():
        sys.exit(f"voice_drift: config not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        sys.exit(f"voice_drift: config is not valid YAML ({path}): {exc}")
    if not isinstance(data, dict):
        sys.exit(f"voice_drift: config must be a mapping: {path}")
    return data
