"""Voice-drift checker — statistical prose evidence (Tier-3, evidence-only).

Detection patterns/algorithms live in this file (stable). Tunable thresholds and
the compounding banned-phrase / metaphor lists live in
config/voice-pack/ai-tics-config.yaml (authoritative). Per spec, this checker NEVER
emits BLOCKING: lines — its flags are evidence the 2b voice inspector weighs.
"""
from __future__ import annotations

import argparse
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

# Allow `import scripts.*` when this file is run directly as `python3 scripts/voice_drift.py`
# (direct-run puts scripts/ on sys.path, not the repo root). Harmless under pytest.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml

from scripts import penny_paths
from scripts.penny_meta import parse_frontmatter
from scripts.penny_verdict import write_verdict
from scripts.penny_text import (
    _ABBREV,
    _is_prose_line,
    _words,
    segment_sentences,
    strip_frontmatter,
)


def default_config(repo_root=None) -> Path:
    return penny_paths.config_path("voice-pack/ai-tics-config.yaml", root=repo_root)


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


# Closed detection sets / patterns (the stable algorithm; values come from config).
_PATTERNS = {
    "bodily_reaction": re.compile(
        r"\b(heart (pounded|hammered|raced|thudded|skipped|clenched)"
        r"|breath (caught|hitched|stilled)"
        r"|stomach (twisted|dropped|knotted|churned|lurched)"
        r"|throat (tightened|closed|went dry)"
        r"|pulse (quickened|jumped)"
        r"|blood (ran cold|froze))", re.I),
    "wave_templates": re.compile(
        r"\ba (wave|surge|flood|rush|tide|swell) of \w+ (washed|swept|came|rolled|crashed) over"
        r"|\ba (deep |profound |strange )?sense of (unease|dread|loss|longing|foreboding)", re.I),
    "something_language": re.compile(
        r"\bsomething (shifted|changed|passed) between them"
        r"|\bsomething in (his|her|their) (voice|eyes|face|expression)", re.I),
    "filtering_verbs": re.compile(
        r"\b(noticed|realized|could feel|could see|could hear|watched as|saw that|seemed to)\b", re.I),
    "soft_qualifiers": re.compile(
        r"\b(almost|somehow|slightly|seemingly|as if|as though|a little|not quite)\b", re.I),
}


def analyze(text: str, cfg: dict) -> dict:
    prose = strip_frontmatter(text)
    sentences = segment_sentences(text)
    words = _words(prose)
    n_words = max(len(words), 1)
    per_1k = 1000.0 / n_words

    tics: list[dict] = []

    def add(tic_id, spans):
        density = len(spans) * per_1k
        thr = cfg.get(tic_id, {})
        flag_at = thr.get("flag_at")          # per-1000-word density threshold
        flagged = flag_at is not None and density >= flag_at
        tics.append({
            "tic_id": tic_id, "count": len(spans),
            "threshold": flag_at, "density_per_1k": round(density, 2),
            "flagged": bool(flagged), "evidence_spans": spans[:5],
        })

    # Line numbers for evidence: search line by line.
    lines = prose.splitlines()

    def spans_for(pattern):
        out = []
        for ln_no, line in enumerate(lines, 1):
            for m in pattern.finditer(line):
                out.append({"tic_id": None, "span_text": m.group(0).strip(), "line": ln_no})
        return out

    for tic_id, pat in _PATTERNS.items():
        sp = spans_for(pat)
        for s in sp:
            s["tic_id"] = tic_id
        add(tic_id, sp)

    # Metaphor pool: count words drawn from the configured pool.
    pool = set(cfg.get("metaphor_pool", []))
    pool_spans = [{"tic_id": "metaphor_pool", "span_text": w, "line": 0}
                  for w in words if w.lower() in pool]
    density = len(pool_spans) * per_1k
    total_flag = cfg.get("metaphor_pool_rule", {}).get("total_flag_at")
    tics.append({
        "tic_id": "metaphor_pool", "count": len(pool_spans),
        "threshold": total_flag, "density_per_1k": round(density, 2),
        "flagged": total_flag is not None and len(pool_spans) >= total_flag,
        "evidence_spans": pool_spans[:5],
    })

    # Sentence-length variance.
    lengths = [len(_words(s)) for s in sentences] or [0]
    stdev = statistics.pstdev(lengths) if len(lengths) > 1 else 0.0
    min_stdev = cfg.get("sentence_variance", {}).get("min_stdev", 0.0)
    tics.append({
        "tic_id": "sentence_variance", "count": len(sentences),
        "threshold": min_stdev, "density_per_1k": round(stdev, 2),
        "flagged": len(lengths) > 1 and stdev < min_stdev,
        "evidence_spans": [],
    })

    # Soft-qualifier cluster rule: flag if any sentence has >= cluster_in_sentence qualifiers.
    cluster_n = cfg.get("soft_qualifiers", {}).get("cluster_in_sentence")
    if cluster_n:
        qpat = _PATTERNS["soft_qualifiers"]
        if any(len(qpat.findall(s)) >= cluster_n for s in sentences):
            for t in tics:
                if t["tic_id"] == "soft_qualifiers":
                    t["flagged"] = True

    # Cinematic fragments: clusters of >=3 consecutive sub-4-word sentences, >=2 verbless.
    def _verbless(s: str) -> bool:
        return not re.search(
            r"\b(\w+ed|is|was|were|are|am|be|been|had|has|have|did|do|does|"
            r"went|ran|came|saw|said|holds?|held|waited?)\b", s, re.I)

    frag_clusters = 0
    run: list[str] = []
    for s in sentences:
        if len(_words(s)) < 4:
            run.append(s)
        else:
            if len(run) >= 3 and sum(_verbless(x) for x in run) >= 2:
                frag_clusters += 1
            run = []
    if len(run) >= 3 and sum(_verbless(x) for x in run) >= 2:
        frag_clusters += 1
    max_clusters = cfg.get("cinematic_fragments", {}).get("max_clusters_per_chapter", 1)
    tics.append({"tic_id": "cinematic_fragments", "count": frag_clusters,
                 "threshold": max_clusters, "density_per_1k": 0.0,
                 "flagged": frag_clusters > max_clusters, "evidence_spans": []})

    # Lexical repetition: repeated sentence openers + over-repeated content words.
    _STOP = {"the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "at",
             "she", "he", "they", "her", "his", "it", "was", "had", "with", "for"}
    openers = Counter((_words(s)[0].lower() if _words(s) else "") for s in sentences)
    top_opener = max(openers.values(), default=0)
    content = [w.lower() for w in words if w.lower() not in _STOP and len(w) > 3]
    cw_counts = Counter(content)
    top_cw_count = max(cw_counts.values(), default=0)
    top_cw_density = top_cw_count * per_1k if top_cw_count > 1 else 0.0
    lr = cfg.get("lexical_repetition", {})
    opener_flag = lr.get("opener_repeat_flag_at")
    cw_flag = lr.get("content_word_per_1k_flag_at")
    lex_flagged = ((opener_flag is not None and top_opener >= opener_flag) or
                   (cw_flag is not None and top_cw_density >= cw_flag))
    tics.append({"tic_id": "lexical_repetition", "count": top_opener,
                 "threshold": opener_flag, "density_per_1k": round(top_cw_density, 2),
                 "flagged": bool(lex_flagged), "evidence_spans": []})

    metrics = {"n_words": n_words, "n_sentences": len(sentences),
               "sentence_stdev": round(stdev, 2)}
    return {"tics": tics, "metrics": metrics, "blocking": []}  # evidence-only: always []


def _flatten_evidence(tics: list[dict]) -> list[dict]:
    out = []
    for t in tics:
        out.extend(t["evidence_spans"])
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Voice-drift checker (evidence-only).")
    ap.add_argument("chapter", help="path to the chapter markdown file")
    ap.add_argument("--out", default=None, help="reviews dir to write voice-drift.md")
    ap.add_argument("--config", default=None,
                     help="tic config path (default: overlay resolution from series root)")
    ap.add_argument("--target", default="unknown")
    args = ap.parse_args(argv)

    cfg = load_config(args.config or default_config())
    text = Path(args.chapter).read_text(encoding="utf-8")
    result = analyze(text, cfg)

    notes = [f"{t['tic_id']}: {t['count']} (density {t['density_per_1k']}/1k, "
             f"threshold {t['threshold']}) {'FLAGGED' if t['flagged'] else 'ok'}"
             for t in result["tics"]]

    out_dir = args.out or str(Path(args.chapter).parent)
    write_verdict(
        out_dir=out_dir, producer="voice_drift.py", kind="deterministic-checker",
        target=args.target, name="voice-drift",
        blocking=result["blocking"],          # always [] — evidence-only
        notes=notes, metrics=result["metrics"],
        evidence=_flatten_evidence(result["tics"]),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
