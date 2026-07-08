"""Deterministic gate evaluator for the Penny Review Bus (Phase 2b).

Reads the verdict files in a chapter's ``ch-NN.reviews/`` directory, computes the
gate decision (PASS iff zero blockers) and the two-signal conflict outcomes, and
writes a ``ch-NN.gate.md`` summary alongside the chapter (sibling of reviews/).

The blocker COUNT is owned by ``penny_verdict.count_blocking`` (the single home of
the ^BLOCKING: convention); this module owns the panel DECISION. Fails loud
(nonzero exit) on operational errors; exit 0 for PASS or HOLD alike.
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

# Direct-file invocation (as the command runbooks do via ${CLAUDE_PLUGIN_ROOT})
# puts scripts/ on sys.path, not the repo root — add the root so `from scripts import …` resolves.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import penny_paths
from scripts.penny_meta import parse_frontmatter, parse_yaml_blocks
from scripts.penny_verdict import count_blocking

VERDICT_KINDS = ("inspector", "deterministic-checker")
DEVELOPMENTAL_KIND = "developmental"


class GateError(Exception):
    """Operational error — refuse to emit a gate (caller exits nonzero)."""


def _load_thresholds(config_path) -> dict:
    try:
        text = Path(config_path).read_text(encoding="utf-8")
    except OSError as exc:
        raise GateError(f"cannot read config {config_path}: {exc}") from exc
    cfg = parse_yaml_blocks(text)
    try:
        spread = int(cfg["score_spread_log_threshold"])
        escalate = str(cfg["escalate_on_blocking_disagreement"]).strip().lower() == "true"
    except (KeyError, ValueError) as exc:
        raise GateError(
            "run-config missing/non-numeric escalate_on_blocking_disagreement "
            "or score_spread_log_threshold"
        ) from exc
    return {"escalate_on_blocking_disagreement": escalate, "score_spread_log_threshold": spread}


def _load_verdicts(reviews_dir) -> list[dict]:
    root = Path(reviews_dir)
    if not root.is_dir():
        raise GateError(f"reviews dir not found: {reviews_dir}")
    verdicts: list[dict] = []
    for path in sorted(root.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        meta = parse_frontmatter(text)
        kind = meta.get("kind")
        if kind not in VERDICT_KINDS:
            continue  # skip gate-summary and anything non-verdict
        producer = meta.get("producer")
        if not producer:
            raise GateError(f"{path.name}: malformed verdict — missing producer")
        score = None
        if kind == "inspector":
            raw = meta.get("score")
            if raw is None:
                raise GateError(f"{path.name}: malformed inspector verdict — missing score")
            try:
                score = int(raw)
            except (TypeError, ValueError) as exc:
                raise GateError(f"{path.name}: non-numeric score {raw!r}") from exc
        blocking = [ln[len("BLOCKING:"):].strip()
                    for ln in text.splitlines() if ln.startswith("BLOCKING:")]
        verdicts.append({"file": path.name, "producer": producer, "kind": kind,
                         "score": score, "blocking": blocking})
    if not verdicts:
        raise GateError(f"no verdicts in {reviews_dir} (dispatch failed?)")
    return verdicts


def _load_developmental(reviews_dir) -> dict | None:
    path = Path(reviews_dir) / "developmental-edit.md"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    meta = parse_frontmatter(text)
    if meta.get("kind") != DEVELOPMENTAL_KIND:
        return None
    raw = meta.get("score")
    score = int(raw) if raw is not None else None
    note_count = sum(1 for ln in text.splitlines() if ln.startswith("- "))
    return {"producer": meta.get("producer"), "score": score,
            "note_count": note_count}


def _detect_blocking_disagreement(verdicts, cfg) -> list[str]:
    if not cfg["escalate_on_blocking_disagreement"]:
        return []
    by_producer = defaultdict(list)
    for v in verdicts:
        by_producer[v["producer"]].append(v)
    out = []
    for producer, group in sorted(by_producer.items()):
        if len(group) < 2:
            continue  # one verdict per dimension at panel_size:1 -> sleeps
        if len({bool(v["blocking"]) for v in group}) > 1:
            out.append(producer)
    return out


def _detect_score_spread(verdicts, cfg) -> list[dict]:
    by_producer = defaultdict(list)
    for v in verdicts:
        if v["kind"] == "inspector" and v["score"] is not None:
            by_producer[v["producer"]].append(v["score"])
    out = []
    for producer, scores in sorted(by_producer.items()):
        if len(scores) < 2:
            continue
        spread = max(scores) - min(scores)
        if spread >= cfg["score_spread_log_threshold"]:
            out.append({"producer": producer, "spread": spread})
    return out


def evaluate_gate(reviews_dir, config_path) -> dict:
    cfg = _load_thresholds(config_path)
    verdicts = _load_verdicts(reviews_dir)
    blocking_count = count_blocking(reviews_dir)  # authoritative, matches status line
    gate = "PASS" if blocking_count == 0 else "HOLD"
    blocking_issues = [(v["producer"], issue) for v in verdicts for issue in v["blocking"]]
    return {
        "gate": gate,
        "blocking_count": blocking_count,
        "blocking_issues": blocking_issues,
        "escalations": _detect_blocking_disagreement(verdicts, cfg),
        "score_spread_log": _detect_score_spread(verdicts, cfg),
        "developmental": _load_developmental(reviews_dir),
    }


def write_gate_md(out_path, target, result) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", "producer: review_gate.py", "kind: gate-summary",
             f"target: {target}", f"gate: {result['gate']}",
             f"blocking_count: {result['blocking_count']}",
             "schema: penny-verdict/1", "---", "",
             f"- {result['gate']}: {result['blocking_count']} blocking issue(s)"]
    for producer, issue in result["blocking_issues"]:
        lines.append(f"- blocking [{producer}]: {issue}")  # never ^BLOCKING:
    lines.append(f"- escalations: {result['escalations']}")
    lines.append(f"- score_spread_log: {result['score_spread_log']}")
    dev = result.get("developmental")
    if dev:
        lines.append(
            f"- developmental [{dev['producer']}]: score {dev['score']} "
            f"({dev['note_count']} note(s)) — advisory, non-blocking; "
            f"see developmental-edit.md")
    else:
        lines.append("- developmental: no developmental read found")
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def _derive_target(reviews_dir) -> str:
    # output/book-01/chapters/ch-07.reviews -> "book-01/ch-07"
    p = Path(reviews_dir)
    chapter = p.name.replace(".reviews", "")
    book = p.parent.parent.name
    return f"{book}/{chapter}"


def _default_out(reviews_dir) -> Path:
    p = Path(reviews_dir)
    chapter = p.name.replace(".reviews", "")
    return p.parent / f"{chapter}.gate.md"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Penny Review Bus gate evaluator")
    parser.add_argument("reviews_dir")
    parser.add_argument("--config", default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    config = args.config or str(penny_paths.config_path("run-config.md"))
    try:
        result = evaluate_gate(args.reviews_dir, config)
    except GateError as exc:
        print(f"review_gate: {exc}", file=sys.stderr)
        return 2
    out = Path(args.out) if args.out else _default_out(args.reviews_dir)
    write_gate_md(out, _derive_target(args.reviews_dir), result)
    suffix = f" ({result['blocking_count']} blocking)" if result["gate"] == "HOLD" else ""
    print(f"GATE: {result['gate']}{suffix}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
