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


def _longest_uniform_run(lengths: list[int], tolerance: int = 2) -> tuple[int, int]:
    """Return (start, end) indices of the longest run of consecutive sentence
    lengths that stay within `tolerance` words of their neighbor — the near-equal
    -length stretch that makes low-stdev prose monotonous to read (spec §3c).

    Falls back to the single closest-matched adjacent pair if no run reaches
    length 2 within tolerance, so a low-stdev chapter (which by definition has
    some pair of close-length sentences) always yields a non-empty run — the
    caller uses this to populate evidence_spans, and an empty run would violate
    the §4 invariant for a legitimately flagged tic."""
    n = len(lengths)
    if n == 0:
        return (0, 0)
    if n == 1:
        return (0, 1)
    best_start, best_end = 0, 1
    start = 0
    for i in range(1, n):
        if abs(lengths[i] - lengths[i - 1]) > tolerance:
            if i - start > best_end - best_start:
                best_start, best_end = start, i
            start = i
    if n - start > best_end - best_start:
        best_start, best_end = start, n
    if best_end - best_start < 2:
        i = min(range(1, n), key=lambda k: abs(lengths[k] - lengths[k - 1]))
        best_start, best_end = i - 1, i + 1
    return best_start, best_end


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
        # A threshold of 0 (or negative) must never flag on zero actual
        # matches: with no spans, density is 0.0, and 0.0 >= 0 is True even
        # though there is nothing to show as evidence. Requiring a positive
        # count closes that crash vector (spec Fix 1).
        flagged = flag_at is not None and len(spans) > 0 and density >= flag_at
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

    def _first_line_for_word(word: str) -> int:
        """First PROSE line containing `word` as a whole word — filtered with
        _is_prose_line so a markdown heading can never win this search. The
        counters this looks up (openers, cw_counts) are themselves built over
        prose that already excludes headings (segment_sentences filters via
        _is_prose_line, and content words track that same domain in practice —
        see spec 2026-08-27-voice-drift-discards-evidence-fix.md Fix 2), so a
        chapter title such as "# Chapter 01 — The Life She Bought" must not be
        allowed to answer "where does this word first occur". A content word is
        not positional, so a line-containing search is the right shape here —
        only the search domain needed to change. Returns 0 if not found in
        prose (should not happen for a word a counter built from this same
        prose)."""
        pat = re.compile(r"\b" + re.escape(word) + r"\b", re.I)
        for ln_no, line in enumerate(lines, 1):
            if _is_prose_line(line) and pat.search(line):
                return ln_no
        return 0

    def _first_line_for_sentence(sentence: str) -> int:
        """First PROSE line containing the sentence's opening words. Sentences
        come from segment_sentences, which re-joins lines with spaces before
        splitting — so there is no exact sentence->line map. Matching the
        opening words against the raw lines is the same approximation spans_for
        relies on for pattern matches; falling back to just the first word
        covers a sentence that opens at a line break. Filtered with
        _is_prose_line for the same reason as _first_line_for_word: a heading
        must never be mistaken for the line a real sentence opens on."""
        head = _words(sentence)[:4]
        if not head:
            return 0
        pat = re.compile(r"\b" + r"\W+".join(re.escape(w) for w in head) + r"\b", re.I)
        for ln_no, line in enumerate(lines, 1):
            if _is_prose_line(line) and pat.search(line):
                return ln_no
        return _first_line_for_word(head[0])

    def _first_line_for_opener(word: str) -> int:
        """First line of the first SENTENCE that opens with `word`. Sentence
        openers are positional — the counter only counts a word when it is the
        sentence's first word — so this mirrors _first_line_for_sentence rather
        than doing a line-containing search: a line-containing search would
        stop at any occurrence of the word on a line, including one that isn't
        the sentence-initial occurrence the counter actually counted (and,
        before this fix, would also match inside the chapter's own markdown
        title). Content words get the line-containing shape instead
        (_first_line_for_word) because a content word is not positional (spec
        2026-08-27-voice-drift-discards-evidence-fix.md Fix 2)."""
        for s in sentences:
            head = _words(s)
            if head and head[0].lower() == word.lower():
                return _first_line_for_sentence(s)
        return 0

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
        # Same positive-count guard as add() (spec Fix 1): zero matches must
        # never flag, even against a threshold of 0.
        "flagged": total_flag is not None and len(pool_spans) > 0 and len(pool_spans) >= total_flag,
        "evidence_spans": pool_spans[:5],
    })

    # Sentence-length variance.
    lengths = [len(_words(s)) for s in sentences] or [0]
    stdev = statistics.pstdev(lengths) if len(lengths) > 1 else 0.0
    min_stdev = cfg.get("sentence_variance", {}).get("min_stdev", 0.0)
    sv_flagged = len(lengths) > 1 and stdev < min_stdev
    sv_spans: list[dict] = []
    if sv_flagged:
        # Cite the longest run of near-equal-length sentences — the actual
        # monotony the low stdev is a proxy for (spec §3c).
        run_start, run_end = _longest_uniform_run(lengths)
        run_len = run_end - run_start
        avg_len = round(sum(lengths[run_start:run_end]) / max(run_len, 1), 1)
        sv_spans = [{
            "tic_id": "sentence_variance",
            "span_text": f"{run_len} consecutive sentences of ~{avg_len} words each",
            "line": _first_line_for_sentence(sentences[run_start]) if sentences else 0,
        }]
    tics.append({
        "tic_id": "sentence_variance", "count": len(sentences),
        "threshold": min_stdev, "density_per_1k": round(stdev, 2),
        "flagged": sv_flagged,
        "evidence_spans": sv_spans,
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
    frag_spans: list[dict] = []
    run: list[str] = []

    def _flush_frag_run(candidate: list[str]) -> None:
        nonlocal frag_clusters
        if len(candidate) >= 3 and sum(_verbless(x) for x in candidate) >= 2:
            frag_clusters += 1
            snippet = " / ".join(candidate)
            if len(snippet) > 100:
                snippet = snippet[:97] + "..."
            frag_spans.append({
                "tic_id": "cinematic_fragments",
                "span_text": f"fragment cluster: {snippet}",
                "line": _first_line_for_sentence(candidate[0]),
            })

    for s in sentences:
        if len(_words(s)) < 4:
            run.append(s)
        else:
            _flush_frag_run(run)
            run = []
    _flush_frag_run(run)
    max_clusters = cfg.get("cinematic_fragments", {}).get("max_clusters_per_chapter", 1)
    tics.append({"tic_id": "cinematic_fragments", "count": frag_clusters,
                 "threshold": max_clusters, "density_per_1k": 0.0,
                 "flagged": frag_clusters > max_clusters,
                 "evidence_spans": frag_spans[:5]})

    # Lexical repetition splits into two independently-thresholded tics
    # (spec 2026-08-27-voice-drift-discards-evidence-fix.md §3b): repeated
    # sentence openers, and over-repeated content words. They used to share one
    # row (`lexical_repetition`) with `count` from the opener measurement and
    # `density_per_1k` from the content-word measurement, so a reader could not
    # tell which threshold actually tripped the flag — and neither measurement
    # carried evidence_spans at all (§1/§3a).
    _STOP = {"the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "at",
             "she", "he", "they", "her", "his", "it", "was", "had", "with", "for"}
    openers = Counter((_words(s)[0].lower() if _words(s) else "") for s in sentences)
    top_opener = max(openers.values(), default=0)
    # Drop singletons: a word that opens exactly one sentence isn't "repeated"
    # (spec Fix 3). Capped at 5 below, same convention as every other tic.
    opener_items = [(w, c) for w, c in openers.most_common() if w and c > 1]

    content = [w.lower() for w in words if w.lower() not in _STOP and len(w) > 3]
    cw_counts = Counter(content)
    top_cw_count = max(cw_counts.values(), default=0)
    top_cw_density = top_cw_count * per_1k if top_cw_count > 1 else 0.0
    cw_items = [(w, c) for w, c in cw_counts.most_common() if c > 1]

    # COMPAT SHIM — remove once every series' ai-tics-config.yaml has migrated.
    # This used to be one config block:
    #   lexical_repetition: { opener_repeat_flag_at: 3, content_word_per_1k_flag_at: 8 }
    # New per-tic keys are preferred (`repeated_openers.flag_at`,
    # `repeated_content_words.flag_at`, matching the `flag_at` convention every
    # other tic in this file uses). A series config that still carries only the
    # old block falls back to it, so it keeps flagging BOTH measurements instead
    # of silently going dark on both — the exact failure class this fix exists to
    # close (spec §1).
    ro_flag = cfg.get("repeated_openers", {}).get("flag_at")
    if ro_flag is None:
        ro_flag = cfg.get("lexical_repetition", {}).get("opener_repeat_flag_at")

    rcw_flag = cfg.get("repeated_content_words", {}).get("flag_at")
    if rcw_flag is None:
        rcw_flag = cfg.get("lexical_repetition", {}).get("content_word_per_1k_flag_at")

    # A threshold of 0 (or negative) must never flag on zero actual repeats —
    # same crash vector as the generic add() guard (spec Fix 1).
    opener_flagged = ro_flag is not None and top_opener > 0 and top_opener >= ro_flag
    if opener_flagged and not opener_items:
        # Fix 3's singleton filter can strip the very occurrence that tripped
        # the flag (e.g. flag_at == 1, so a single occurrence is itself "at
        # threshold"). Never let a flagged tic end up with empty evidence —
        # the §4 invariant must hold even at this degenerate config.
        opener_items = [(w, c) for w, c in openers.most_common() if w][:1]
    opener_spans = [{
        "tic_id": "repeated_openers",
        "span_text": f'sentence opener "{w.capitalize()}" ×{c}',
        "line": _first_line_for_opener(w),
    } for w, c in opener_items[:5]]
    tics.append({"tic_id": "repeated_openers", "count": top_opener,
                 "threshold": ro_flag, "density_per_1k": round(top_opener * per_1k, 2),
                 "flagged": bool(opener_flagged), "evidence_spans": opener_spans[:5]})

    cw_flagged = rcw_flag is not None and top_cw_count > 0 and top_cw_density >= rcw_flag
    if cw_flagged and not cw_items:
        # Same interaction guard as opener_items, above.
        cw_items = [(w, c) for w, c in cw_counts.most_common()][:1]
    cw_spans = [{
        "tic_id": "repeated_content_words",
        "span_text": f'content word "{w}" ×{c}',
        "line": _first_line_for_word(w),
    } for w, c in cw_items[:5]]
    tics.append({"tic_id": "repeated_content_words", "count": top_cw_count,
                 "threshold": rcw_flag, "density_per_1k": round(top_cw_density, 2),
                 "flagged": bool(cw_flagged), "evidence_spans": cw_spans[:5]})

    metrics = {"n_words": n_words, "n_sentences": len(sentences),
               "sentence_stdev": round(stdev, 2)}
    return {"tics": tics, "metrics": metrics, "blocking": []}  # evidence-only: always []


class UnevidencedFlagError(AssertionError):
    """A tic was flagged with no evidence_spans (spec §4 invariant)."""


def _assert_evidenced(tics: list[dict]) -> None:
    """§4 invariant (spec 2026-08-27-voice-drift-discards-evidence-fix.md): a tic
    with flagged=True and empty evidence_spans is a bug, not a legitimate state.
    voice_drift is evidence-only — inspector-voice weighs magnitude and decides
    whether it harms the read — so a flag with nothing to weigh doesn't just fail
    to help, it actively misdirects the review (see the spec's §2 real-book
    reproduction, where the sole flagged tic contributed zero of the evidence).

    This is a HARD FAILURE (raise), not merely a test: voice_drift never gates a
    chapter (`blocking` stays [] unconditionally — see analyze()'s return and
    every call site below), so raising here cannot block a finalize. It fails the
    checker itself loudly during review, which is what this engine does
    everywhere else a deterministic layer finds its own contract broken.

    Unflagged tics may legitimately carry no spans; the invariant applies only to
    flags."""
    culprits = [t["tic_id"] for t in tics if t.get("flagged") and not t.get("evidence_spans")]
    if culprits:
        raise UnevidencedFlagError(
            f"voice_drift: flagged tic(s) with no evidence_spans: {culprits} "
            "— every flag must be weighable, never just a count (spec §4)"
        )


def _flatten_evidence(tics: list[dict]) -> list[dict]:
    # Choke point: every real path from analyze()'s tic list to a written verdict
    # (main() -> write_verdict) passes through here, so the §4 guard lives at the
    # top of it rather than inside analyze() itself — analyze() is also called
    # directly by callers (including most of this file's own tests) who may want
    # to inspect an intermediate/partial tic list without tripping the guard;
    # what must never happen is an unevidenced flag reaching disk.
    _assert_evidenced(tics)
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
