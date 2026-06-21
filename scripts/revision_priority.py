"""Deterministic revision-priority aggregator (Phase 6, design §10).

Pure reader over three already-structured signals — cross-persona put-down counts,
would-buy-next tallies, accumulated score spreads. Escalate-vs-log is RAW threshold
arithmetic; it NEVER computes a blended/derived severity score (that would smuggle
judgment back into the deterministic layer). Every emitted line names the rule that
fired plus its raw counts, so the showrunner sees *why* it escalated, not just that
it did. Non-blocking: always exits 0; the escalations inform the human gate.

Inputs (shapes verified against the producers):
  - output/book-NN/reports/<persona>.converged.md  (beta_report.serialize_converged:
    frontmatter + JSON body; put_down_points.{consensus,logged}, would_buy_next.tally.no)
  - output/book-NN/chapters/ch-*.gate.md            (review_gate.write_gate_md:
    body line `- score_spread_log: [<repr list of dicts>]`)
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.penny_meta import parse_yaml_blocks, strip_frontmatter

REPO = Path(__file__).resolve().parents[1]
SCHEMA = "penny-revision-priority/1"


def _fail(predicate: str):
    sys.exit(f"revision_priority: {predicate}")


def book_dir(book: str, repo_root) -> Path:
    return Path(repo_root) / "output" / f"book-{book}"


def report_path(book: str, repo_root) -> Path:
    return book_dir(book, repo_root) / "reports" / "revision-priority.md"


def _load_thresholds(config_path) -> dict:
    cfg = parse_yaml_blocks(Path(config_path).read_text(encoding="utf-8"))
    try:
        return {"personas": int(cfg["revision_escalate_personas"]),
                "would_buy": int(cfg["would_buy_escalate_count"])}
    except (KeyError, ValueError) as exc:
        _fail(f"run-config missing/non-numeric revision_escalate_personas or "
              f"would_buy_escalate_count ({exc})")


def _load_converged(reports_dir) -> list[dict]:
    out = []
    for path in sorted(Path(reports_dir).glob("*.converged.md")):
        try:
            out.append(json.loads(strip_frontmatter(path.read_text(encoding="utf-8"))))
        except (json.JSONDecodeError, ValueError) as exc:
            _fail(f"malformed converged report {path.name}: {exc}")
    return out


def _score_spreads(chapters_dir) -> list[tuple[int, dict]]:
    """Return (chapter, entry) for every score_spread_log entry across gate.md files."""
    out = []
    for path in sorted(Path(chapters_dir).glob("ch-*.gate.md")):
        chapter = int(path.name[len("ch-"):].split(".")[0])
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("- score_spread_log:"):
                raw = s[len("- score_spread_log:"):].strip()
                try:
                    entries = ast.literal_eval(raw) if raw else []
                except (ValueError, SyntaxError) as exc:
                    _fail(f"unparsable score_spread_log in {path.name}: {exc}")
                for e in entries:
                    out.append((chapter, e))
    return out


def aggregate(book: str, *, repo_root=REPO, config_path=None) -> dict:
    config_path = config_path or (Path(repo_root) / "config/run-config.md")
    th = _load_thresholds(config_path)
    converged = _load_converged(book_dir(book, repo_root) / "reports")

    # Rule 1 — cross_persona_putdown: per chapter, count DISTINCT personas with a
    # put-down (consensus or logged). >= threshold -> ESCALATE else LOG.
    by_chapter: dict[int, set[str]] = {}
    for rep in converged:
        persona = rep["persona"]
        pd = rep.get("put_down_points", {})
        for ch in set(pd.get("consensus", [])) | set(pd.get("logged", [])):
            by_chapter.setdefault(int(ch), set()).add(persona)

    escalate, log = [], []
    for ch in sorted(by_chapter):
        personas = sorted(by_chapter[ch])
        n = len(personas)
        names = ", ".join(personas)
        noun = "persona" if n == 1 else "personas"
        if n >= th["personas"]:
            escalate.append(f"- [put-down] ch.{ch} — rule cross_persona_putdown>="
                            f"{th['personas']} ({n} {noun}: {names})")
        else:
            log.append(f"- [put-down] ch.{ch} — rule cross_persona_putdown<"
                       f"{th['personas']} ({n} {noun}: {names})")

    # Rule 2 — would_buy_no: sum tally.no across personas. >= threshold -> ESCALATE.
    total_no = sum(int(r.get("would_buy_next", {}).get("tally", {}).get("no", 0))
                   for r in converged)
    if total_no >= th["would_buy"]:
        escalate.append(f"- [would-buy] book — rule would_buy_no>={th['would_buy']} "
                        f"({total_no} personas said would-not-buy-next)")
    elif total_no:
        log.append(f"- [would-buy] book — rule would_buy_no<{th['would_buy']} "
                   f"({total_no} personas said would-not-buy-next)")

    # Rule 3 — score_spread: every entry -> LOG only (SOFT per design §6).
    for ch, e in _score_spreads(book_dir(book, repo_root) / "chapters"):
        log.append(f"- [score-spread] ch.{ch} — rule score_spread "
                   f"(producer {e.get('producer')}, spread {e.get('spread')})")

    return {"escalate": escalate, "log": log}


def write_report(out_path, result) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"schema: {SCHEMA}", "kind: revision-priority",
             f"escalations: {len(result['escalate'])}", "---", "",
             "## ESCALATE", ""]
    lines += result["escalate"] or ["- (none)"]
    lines += ["", "## LOG", ""]
    lines += result["log"] or ["- (none)"]
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def cmd_report(book: str, *, repo_root=REPO, config_path=None) -> int:
    result = aggregate(book, repo_root=repo_root, config_path=config_path)
    write_report(report_path(book, repo_root), result)
    print(f"REVISION-PRIORITY: {len(result['escalate'])} escalation(s)")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Penny revision-priority aggregator.")
    ap.add_argument("book")
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    return cmd_report(args.book, config_path=args.config)


if __name__ == "__main__":
    raise SystemExit(main())
