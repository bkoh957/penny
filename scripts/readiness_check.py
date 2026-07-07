"""Pre-flight readiness checklist (deterministic, reporting-only).

Inspects the repo and emits a YAML report of what is ready to go and what is
missing — engine/config files and directories, and (when a book number is given)
the per-book inputs the MVP-1 pipeline needs plus a snapshot of pipeline progress.

This is a *reporter*, not a gate: it never exits non-zero on a not-ready repo and
never writes a lock or certificate. It answers "can I start / continue this book?"
by reusing the same predicates the real gates enforce (e.g. fairplay character-id
resolution), so a green checklist lines up with a clean `lock-mystery`.

  python3 scripts/readiness_check.py            # engine + config only
  python3 scripts/readiness_check.py 01         # + per-book inputs for book 01
  python3 scripts/readiness_check.py 01 --out readiness.yaml

Status values: ready | missing | blocked (present but failing a validation).
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml

from scripts import penny_paths
from scripts.fairplay_check import check_fairplay, load_fraction

REPO = Path(__file__).resolve().parents[1]

# (name, relative path, kind, expected_min_files) — the genre-agnostic engine +
# the shipped cozy/coastal packs every run reads. expected_min only for dirs.
ENGINE_CHECKS = [
    ("run-config",        "config/run-config.md",                    "file", None),
    ("voice-pack",        "config/voice-pack/voice-pack.md",         "file", None),
    ("ai-tics-config",    "config/voice-pack/ai-tics-config.yaml",   "file", None),
    ("ai-tics-detection", "config/voice-pack/ai-tics-detection.md",  "file", None),
    ("lexicon",           "config/setting-pack/lexicon.yaml",        "file", None),
    ("setting-pack",      "config/setting-pack/coastal-victoria-au.md", "file", None),
    ("genre-pack",        "config/genre-pack/cozy-mystery.md",       "file", None),
    ("length-profile",    "config/length-profile.md",                "file", None),
    ("line-edit",         "config/line-edit/line-edit.md",           "file", None),
    ("copy-edit",         "config/copy-edit/copy-edit.md",           "file", None),
    ("review-rubrics",    "config/review-rubrics",                   "dir",  5),
    ("beta-personas",     "config/beta-readers/personas",            "dir",  6),
    ("beta-protocol",     "config/beta-readers/beta-protocol.md",    "file", None),
    ("canon-core",        "series/continuity/canon-core.md",         "file", None),
]


def _check(name, kind, status, path=None, detail=None) -> dict:
    entry = {"name": name, "kind": kind, "status": status}
    if path is not None:
        entry["path"] = str(path)
    if detail is not None:
        entry["detail"] = detail
    return entry


def _resolve(rel: str, repo_root) -> Path:
    if rel.startswith("config/"):
        return penny_paths.config_path(rel[len("config/"):], root=repo_root)
    if rel.startswith("series/"):
        return penny_paths.series_path(rel[len("series/"):], root=repo_root)
    if rel.startswith("input/"):
        return penny_paths.input_path(rel[len("input/"):], root=repo_root)
    if rel.startswith("output/"):
        return penny_paths.output_path(rel[len("output/"):], root=repo_root)
    return Path(repo_root) / rel


def _file_check(name, rel, repo_root) -> dict:
    status = "ready" if _resolve(rel, repo_root).is_file() else "missing"
    return _check(name, "file", status, path=rel)


def _dir_check(name, rel, expected_min, repo_root) -> dict:
    d = _resolve(rel, repo_root)
    if not d.is_dir():
        return _check(name, "dir", "missing", path=rel)
    n = len(list(d.glob("*.md")))
    if expected_min is not None and n < expected_min:
        return _check(name, "dir", "blocked", path=rel,
                      detail=f"{n}/{expected_min} file(s)")
    return _check(name, "dir", "ready", path=rel, detail=f"{n} file(s)")


def engine_checks(repo_root=None) -> list[dict]:
    repo_root = repo_root or penny_paths.series_root()
    out = []
    for name, rel, kind, expected_min in ENGINE_CHECKS:
        if kind == "dir":
            out.append(_dir_check(name, rel, expected_min, repo_root))
        else:
            out.append(_file_check(name, rel, repo_root))
    return out


def _resolves(entity_id: str, repo_root) -> bool:
    static = Path(repo_root) / "series/characters" / f"{entity_id}.static.md"
    cont = Path(repo_root) / "series/continuity/characters" / f"{entity_id}.md"
    return static.is_file() or cont.is_file()


def _ledger_entity_ids(led: dict) -> list[str]:
    """culprit + victim + every alibi-grid suspect, de-duplicated, in order."""
    ids: list[str] = []
    for key in ("culprit", "victim"):
        v = led.get(key)
        if isinstance(v, str):
            ids.append(v)
    for row in led.get("alibi_grid", []) or []:
        s = row.get("suspect") if isinstance(row, dict) else None
        if isinstance(s, str):
            ids.append(s)
    seen, ordered = set(), []
    for i in ids:
        if i not in seen:
            seen.add(i)
            ordered.append(i)
    return ordered


def book_input_checks(book, repo_root) -> list[dict]:
    repo_root = Path(repo_root)
    led_rel = f"series/whodunit/book-{book}.yaml"
    led_path = repo_root / led_rel
    out = [_file_check("mystery-ledger", led_rel, repo_root)]

    # fairplay + character entities depend on a parseable ledger.
    if not led_path.is_file():
        out.append(_check("mystery-fairplay", "check", "missing",
                          detail="requires mystery ledger"))
        out.append(_check("character-entities", "check", "missing",
                          detail="requires mystery ledger"))
    else:
        try:
            led = yaml.safe_load(led_path.read_text(encoding="utf-8"))
            parseable = isinstance(led, dict)
        except yaml.YAMLError:
            led, parseable = None, False
        if not parseable:
            out.append(_check("mystery-fairplay", "check", "blocked",
                              path=led_rel, detail="ledger is not valid YAML"))
            out.append(_check("character-entities", "check", "blocked",
                              path=led_rel, detail="ledger is not valid YAML"))
        else:
            out.append(_fairplay_check(book, led_rel, repo_root))
            out.append(_entities_check(led, repo_root))

    # chapter briefs directory (per-chapter briefs the drafter consumes).
    briefs_rel = f"series/briefs/book-{book}"
    briefs = repo_root / briefs_rel
    if not briefs.is_dir():
        out.append(_check("chapter-briefs", "dir", "missing", path=briefs_rel))
    else:
        n = len(list(briefs.glob("ch-*-brief.md")))
        detail = f"{n} brief file(s)"
        out.append(_check("chapter-briefs", "dir",
                          "ready" if n else "blocked", path=briefs_rel,
                          detail=detail if n else "directory present but empty"))

    lock_rel = f".penny/locks/book-{book}.mystery.lock"
    out.append(_file_check("mystery-lock", lock_rel, repo_root))
    return out


def _fairplay_check(book, led_rel, repo_root) -> dict:
    """Structural fairplay validity (numeric fairness), excluding entity-existence
    — that is reported separately by character-entities."""
    cfg = Path(repo_root) / "config/run-config.md"
    if not cfg.is_file():
        return _check("mystery-fairplay", "check", "blocked", path=led_rel,
                      detail="requires config/run-config.md")
    fraction = load_fraction(cfg)
    result = check_fairplay(Path(repo_root) / led_rel,
                            culprit_by_fraction=fraction, repo_root=repo_root)
    structural = [b for b in result["blocking"] if "character entity" not in b]
    if structural:
        return _check("mystery-fairplay", "check", "blocked", path=led_rel,
                      detail="; ".join(structural))
    return _check("mystery-fairplay", "check", "ready", path=led_rel)


def _entities_check(led: dict, repo_root) -> dict:
    ids = _ledger_entity_ids(led)
    missing = [i for i in ids if not _resolves(i, repo_root)]
    if missing:
        return _check("character-entities", "check", "blocked",
                      detail="missing entity file(s): " + ", ".join(missing))
    return _check("character-entities", "check", "ready",
                  detail=f"{len(ids)} entity id(s) resolve")


def pipeline_progress(book, repo_root) -> dict:
    repo_root = Path(repo_root)
    chapters = repo_root / "output" / f"book-{book}" / "chapters"
    book_dir = repo_root / "output" / f"book-{book}"
    reports = book_dir / "reports"

    total = "?"
    led = repo_root / "series/whodunit" / f"book-{book}.yaml"
    if led.is_file():
        try:
            data = yaml.safe_load(led.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("total_chapters"), int):
                total = data["total_chapters"]
        except yaml.YAMLError:
            pass

    def _count(glob):
        return len(list(chapters.glob(glob))) if chapters.is_dir() else 0

    def _present(path):
        return "ready" if path.is_file() else "missing"

    n_beta = len(list(reports.glob("*.converged.md"))) if reports.is_dir() else 0
    return {
        "drafts": f"{_count('ch-*.draft.md')}/{total}",
        "finals": f"{_count('ch-*.final.md')}/{total}",
        "beta_converged_reports": n_beta,
        "manuscript": _present(book_dir / f"book-{book}.manuscript.md"),
        "final_read": _present(book_dir / f"book-{book}.final-read.md"),
        "revision_priority_report": _present(reports / "revision-priority.md"),
        "approved_cert": _present(repo_root / ".penny/locks" / f"book-{book}.approved"),
    }


def _summarize(*check_groups) -> dict:
    counts = {"ready": 0, "missing": 0, "blocked": 0}
    for group in check_groups:
        for c in group:
            counts[c["status"]] = counts.get(c["status"], 0) + 1
    verdict = "READY" if counts["missing"] == 0 and counts["blocked"] == 0 else "NOT-READY"
    return {**counts, "verdict": verdict}


def check_readiness(book=None, *, repo_root=REPO) -> dict:
    engine = engine_checks(repo_root)
    report: dict = {"book": book}
    if book is None:
        report["summary"] = _summarize(engine)
        report["engine_and_config"] = engine
        return report
    inputs = book_input_checks(book, repo_root)
    report["summary"] = _summarize(engine, inputs)
    report["engine_and_config"] = engine
    report["book_inputs"] = inputs
    report["pipeline_progress"] = pipeline_progress(book, repo_root)
    return report


def to_yaml(report: dict) -> str:
    return yaml.safe_dump(report, sort_keys=False, default_flow_style=False)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Penny pre-flight readiness checklist.")
    ap.add_argument("book", nargs="?", default=None, help="book number, e.g. 01")
    ap.add_argument("--out", default=None, help="also write the YAML report to this path")
    args = ap.parse_args(argv)

    report = check_readiness(args.book)
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), **report}
    text = to_yaml(report)
    sys.stdout.write(text)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
