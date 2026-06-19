# Penny

Modular, Claude-Code-native harness for producing a 13-book commercial fiction
series with independent quality review. Genre/location-agnostic: everything
project-specific lives in swappable config, never in the engine.

See `penny-design-v3.md` (design) and `penny-PRD-v3.md` (requirements).

## Status: Phase 1 (Skeleton)

In place: engine/config separation, sectioned continuity ledger + canon-core,
series-memory documents, one cozy-mystery / coastal-Victoria pack, the three-tier
AI-prose defense config, run-config, and the TUI status bar. Manual single-chapter
drafting via `/draft-chapter`.

Not yet built: review bus (Phase 2), `/plan-mystery` + cross-model routing
(Phase 3), prose passes (Phase 4), beta layer (Phase 5), book loop (Phase 6).

## Develop

```bash
python3 -m pytest          # run the structural + status-line tests
```

Requires `python3`, `jq` (status line), and `pytest`. One third-party dependency
(PyYAML, for nested human-edited config/ledgers):

```bash
pip install -r requirements.txt
```

## Status line

`scripts/penny-statusline.sh` is wired in `.claude/settings.json`. It reads harness
state from `.penny/current-stage` and `/output`, and the session JSON from stdin.
Honours `$PENNY_ROOT` (default `.`).
