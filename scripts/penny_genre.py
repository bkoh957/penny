"""Load and validate a genre manifest (genres/<genre>/genre.yaml).

The manifest is genuinely nested human-edited data, so this module (unlike the
stdlib-only penny_paths) uses PyYAML — consistent with the dependency-split rule.
It is the ONLY reader of the nested manifest; penny_paths reads only the flat
series.yaml.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow `import scripts.*` when this file is run directly as `python3 scripts/penny_genre.py`
# (direct-run puts scripts/ on sys.path, not the repo root). Harmless under pytest.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml

MANIFEST_KEYS = ("genre", "conventions", "planning", "inspectors", "gates", "rubrics", "tracks")
_PLANNING_KEYS = ("command", "artifact", "validator", "lock")
_OPTIONAL_FILE_KEYS = ("beat_sheet", "fan_persona")


def validate_manifest(manifest: dict, genre_dir: Path, *, plugin_root: Path) -> list[str]:
    """Return a list of error strings (empty means valid)."""
    errs: list[str] = []
    for k in MANIFEST_KEYS:
        if k not in manifest:
            errs.append(f"manifest missing required key: {k}")
    if errs:
        return errs

    if manifest["genre"] != genre_dir.name:
        errs.append(f"genre '{manifest['genre']}' does not match directory '{genre_dir.name}'")

    planning = manifest["planning"]
    if not isinstance(planning, dict):
        errs.append("planning must be a mapping")
    else:
        for k in _PLANNING_KEYS:
            if k not in planning:
                errs.append(f"planning missing key: {k}")
        if "artifact" in planning and "{NN}" not in str(planning["artifact"]):
            errs.append("planning.artifact must contain the {NN} book placeholder")
        cmd = planning.get("command")
        if cmd and not (plugin_root / "commands" / f"{cmd}.md").is_file():
            errs.append(f"planning.command '{cmd}' -> commands/{cmd}.md not found")
        val = planning.get("validator")
        if val is not None and not (plugin_root / "scripts" / f"{val}_check.py").is_file():
            errs.append(f"planning.validator '{val}' -> scripts/{val}_check.py not found")

    for name in manifest.get("inspectors", []):
        if not (plugin_root / "agents" / f"inspector-{name}.md").is_file():
            errs.append(f"inspector '{name}' -> agents/inspector-{name}.md not found")

    # conventions + rubric files: resolve through the overlay (genre dir OR engine default)
    conv = manifest["conventions"]
    if not (genre_dir / conv).is_file():
        errs.append(f"conventions '{conv}' not found in {genre_dir}")
    for rel in manifest.get("rubrics", []):
        if not ((genre_dir / rel).is_file() or (plugin_root / "config" / rel).is_file()):
            errs.append(f"rubric '{rel}' not found in genre pack or engine defaults")

    for key in _OPTIONAL_FILE_KEYS:
        val = manifest.get(key)
        if val is not None and not (genre_dir / str(val)).is_file():
            errs.append(f"{key} '{val}' not found in {genre_dir}")

    for key in ("inspectors", "gates", "rubrics", "tracks"):
        if not isinstance(manifest.get(key), list):
            errs.append(f"{key} must be a list")
    return errs


def load_manifest(genre: str | None = None, *, root: Path | None = None) -> dict:
    from scripts import penny_paths
    if genre is None:
        genre = penny_paths.genre(root=root)
    genre_dir = penny_paths.plugin_root() / "genres" / genre
    mpath = genre_dir / "genre.yaml"
    if not mpath.is_file():
        sys.exit(f"penny-genre: no manifest at {mpath}")
    manifest = yaml.safe_load(mpath.read_text(encoding="utf-8"))
    errs = validate_manifest(manifest, genre_dir, plugin_root=penny_paths.plugin_root())
    if errs:
        sys.exit("penny-genre: invalid manifest:\n  - " + "\n  - ".join(errs))
    return manifest


def inspectors(root: Path | None = None) -> list[str]:
    return load_manifest(root=root)["inspectors"]


def gates(root: Path | None = None) -> list[str]:
    return load_manifest(root=root)["gates"]


def planning(root: Path | None = None) -> dict:
    return load_manifest(root=root)["planning"]


def _main(argv: list[str]) -> int:
    if not argv:
        print("usage: penny_genre <inspectors|gates|planning-command|planning-artifact|planning-lock|planning-validator>",
              file=sys.stderr)
        return 2
    cmd = argv[0]
    if cmd == "inspectors":
        print("\n".join(inspectors()))
        return 0
    if cmd == "gates":
        print("\n".join(gates()))
        return 0
    if cmd.startswith("planning-"):
        key = cmd[len("planning-"):]
        val = planning().get(key)
        print("" if val is None else val)
        return 0
    print(f"penny_genre: unknown command '{cmd}'", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
