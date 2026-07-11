#!/usr/bin/env python3
"""Draft a Penny chapter through LM Studio using scene-shard orchestration.

This is an alternate drafting backend for local models that produce good short
scenes but unreliable whole chapters. The deterministic engine still owns path
resolution, preflight, word-count verification, and artifact placement; LM Studio
is used only for prose generation.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# Allow `import scripts.*` when run directly as
# `python3 /path/to/penny/scripts/lmstudio_draft_chapter.py` from a series folder.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import yaml
except ImportError:  # pragma: no cover - requirements.txt includes PyYAML
    yaml = None

from scripts import penny_paths
from scripts.penny_meta import load, parse_yaml_blocks

DEFAULT_BASE_URL = "http://localhost:1234/v1"
MAX_CONTEXT_CHARS = 80_000
POST_SCENE_HEADING = re.compile(
    r"^###\s+(?:Chapter\s+Structure\s+Summary|Track\s+Movement|Drafting\s+Notes|Possible\s+Line-Level\s+Prompts)\b.*$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class SceneUnit:
    title: str
    brief: str
    target_words: int


@dataclass(frozen=True)
class LengthRange:
    label: str
    minimum: int
    maximum: int


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w’'-]+\b", text))


def _read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _truncate(label: str, text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n[TRUNCATED {label}: {len(text) - limit} chars omitted]\n"


def _read_config_digest_or_file(digest_rel: str, fallback_rel: str, repo_root: Path) -> str:
    digest = penny_paths.config_path(digest_rel, root=repo_root)
    if digest.is_file():
        return digest.read_text(encoding="utf-8")
    return _read_optional(penny_paths.config_path(fallback_rel, root=repo_root))


def _read_config_pack_for_lmstudio(pack_rel: str, repo_root: Path) -> str:
    """Read a short LM Studio digest for a pack, falling back to the full pack files.

    Digest files are series-authored config overlays named
    ``config/<pack_rel>/lmstudio-digest.md``. They are intentionally curated,
    compact prompt surfaces for smaller local models. If absent, preserve the
    existing behavior: concatenate all markdown files in the resolved pack dir.
    """
    digest = penny_paths.config_path(f"{pack_rel}/lmstudio-digest.md", root=repo_root)
    if digest.is_file():
        return digest.read_text(encoding="utf-8")

    parts = []
    pack_dir = penny_paths.config_path(pack_rel, root=repo_root)
    if pack_dir.is_dir():
        for p in sorted(pack_dir.glob("*.md")):
            if p.name == "lmstudio-digest.md":
                continue
            parts.append(f"# {p.name}\n{p.read_text(encoding='utf-8')}")
    return "\n\n".join(parts)


def extract_chapter_section(outline_text: str, chapter: str) -> str:
    ch_int = int(chapter)
    pat = re.compile(rf"^##\s+Chapter\s+0*{ch_int}\b.*$", re.MULTILINE)
    match = pat.search(outline_text)
    if not match:
        raise ValueError(f"chapter {chapter} not found in outline")
    next_match = re.search(r"^##\s+Chapter\s+\d+\b.*$", outline_text[match.end():], re.MULTILINE)
    end = match.end() + next_match.start() if next_match else len(outline_text)
    # Trim trailing separator before next chapter if present.
    section = outline_text[match.start():end].rstrip()
    return re.sub(r"\n---\s*$", "", section).rstrip() + "\n"


def split_scene_units(chapter_brief: str, target_total: int) -> list[SceneUnit]:
    scene_matches = list(re.finditer(r"^###\s+Scene\s+\d+\s+[—-]\s+.*$", chapter_brief, re.MULTILINE))
    if not scene_matches:
        return [SceneUnit("Whole chapter", chapter_brief, target_total)]

    units: list[SceneUnit] = []
    for i, m in enumerate(scene_matches):
        if i + 1 < len(scene_matches):
            end = scene_matches[i + 1].start()
        else:
            post_scene = POST_SCENE_HEADING.search(chapter_brief, m.end())
            end = post_scene.start() if post_scene else len(chapter_brief)
        title = m.group(0).lstrip("# ").strip()
        units.append(SceneUnit(title=title, brief=chapter_brief[m.start():end].strip(), target_words=0))

    # Give every scene a floor, then distribute the remaining chapter budget roughly evenly.
    floor = 450 if target_total >= 1800 else 300
    base = max(floor, target_total // max(1, len(units)))
    weighted = [SceneUnit(u.title, u.brief, base) for u in units]
    delta = target_total - sum(u.target_words for u in weighted)
    if delta > 0 and weighted:
        extra_each = delta // len(weighted)
        rem = delta % len(weighted)
        weighted = [
            SceneUnit(u.title, u.brief, u.target_words + extra_each + (1 if idx < rem else 0))
            for idx, u in enumerate(weighted)
        ]
    return weighted


def compact_chapter_context(chapter_brief: str, limit: int = 8_000) -> str:
    """Keep chapter-level instructions while dropping other scene bodies."""
    scene_matches = list(re.finditer(r"^###\s+Scene\s+\d+\s+[—-]\s+.*$", chapter_brief, re.MULTILINE))
    if not scene_matches:
        return _truncate("chapter_context", chapter_brief, limit)

    pieces: list[str] = []
    first_scene = scene_matches[0]
    pieces.append(chapter_brief[: first_scene.start()].strip())
    pieces.append("Scene map:")
    pieces.extend("- " + m.group(0).lstrip("# ").strip() for m in scene_matches)
    post_scene = POST_SCENE_HEADING.search(chapter_brief, scene_matches[-1].end())
    if post_scene:
        pieces.append(chapter_brief[post_scene.start():].strip())
    return _truncate("chapter_context", "\n\n".join(p for p in pieces if p), limit)


def compact_whodunit_context(whodunit: str, chapter: str, chapter_brief: str, limit: int = 3_500) -> str:
    """Return a chapter-scoped whodunit excerpt instead of the full ledger."""
    if not whodunit or yaml is None:
        return _truncate("whodunit", whodunit, limit)

    try:
        data = yaml.safe_load(whodunit)
    except yaml.YAMLError:
        return _truncate("whodunit", whodunit, limit)
    if not isinstance(data, dict):
        return _truncate("whodunit", whodunit, limit)

    ch = int(chapter)
    brief_l = chapter_brief.lower()

    def mentioned(value: object) -> bool:
        text = str(value or "").lower().replace("-", " ")
        return bool(text and text in brief_l)

    out: dict[str, object] = {
        "book": data.get("book"),
        "reveal_chapter": data.get("reveal_chapter"),
        "victim": data.get("victim"),
        "note": "excerpt only: active/current clue, red-herring, and alibi constraints for this chapter",
    }
    reveal_ch = data.get("reveal_chapter")
    if reveal_ch and ch >= int(reveal_ch):
        out["culprit"] = data.get("culprit")
        out["central_deception"] = data.get("central_deception")

    clue_rows = []
    for row in data.get("clue_schedule") or []:
        if not isinstance(row, dict):
            continue
        plant = int(row.get("plant_chapter") or 0)
        payoff = int(row.get("pays_off_chapter") or 0)
        if plant == ch or payoff == ch or (plant and payoff and plant < ch < payoff) or mentioned(row.get("id")):
            clue_rows.append(row)
    if clue_rows:
        out["clue_schedule_excerpt"] = clue_rows

    red_herrings = []
    for row in data.get("red_herrings") or []:
        if not isinstance(row, dict):
            continue
        plant = int(row.get("plant_chapter") or 0)
        if plant == ch or mentioned(row.get("id")) or mentioned(row.get("misleads_toward")):
            red_herrings.append(row)
    if red_herrings:
        out["red_herrings_excerpt"] = red_herrings

    alibis = []
    for row in data.get("alibi_grid") or []:
        if not isinstance(row, dict):
            continue
        row_ch = int(row.get("chapter") or 0)
        if row_ch == ch or mentioned(row.get("suspect")):
            alibis.append(row)
    if alibis:
        out["alibi_grid_excerpt"] = alibis

    return _truncate("whodunit_excerpt", yaml.safe_dump(out, sort_keys=False, allow_unicode=True), limit)


def parse_length_profile(text: str, chapter_brief: str) -> LengthRange:
    rows = []
    for line in text.splitlines():
        if "|" not in line or "–" not in line and "-" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or not re.search(r"\d", cells[1]):
            continue
        nums = [int(n.replace(",", "")) for n in re.findall(r"\d[\d,]*", cells[1])]
        if len(nums) >= 2:
            rows.append((cells[0].lower(), nums[0], nums[1], cells[0]))

    brief_l = chapter_brief.lower()
    priorities = [
        ("final confrontation", ["final confrontation", "climax"]),
        ("major reveal", ["major reveal", "emotional shift", "reveal"]),
        ("quick discovery", ["quick discovery", "confrontation"]),
        ("standard", ["standard investigation", "character chapter", "investigation"]),
    ]
    for row_key, needles in priorities:
        if any(n in brief_l for n in needles):
            for label_l, mn, mx, label in rows:
                if row_key in label_l:
                    return LengthRange(label, mn, mx)
    if "opening chapter" in brief_l or re.search(r"^##\s+chapter\s+0*1\b", brief_l, re.MULTILINE):
        for label_l, mn, mx, label in rows:
            if "opening" in label_l:
                return LengthRange(label, mn, mx)
    for label_l, mn, mx, label in rows:
        if "standard" in label_l:
            return LengthRange(label, mn, mx)
    return LengthRange("Default", 2000, 2500)


def _frontmatter_model(model: str) -> str:
    model = model.strip() or "unknown-local-model"
    return f"lmstudio/{model}"


def _find_model(base_url: str) -> str | None:
    try:
        headers = {}
        api_key = os.environ.get("LMSTUDIO_API_KEY") or os.environ.get("LM_STUDIO_API_KEY")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        req = urllib.request.Request(base_url.rstrip("/") + "/models", headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None
    data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict) and first.get("id"):
            return str(first["id"])
    return None


def load_run_config_model(repo_root: Path) -> str | None:
    cfg_path = penny_paths.config_path("run-config.md", root=repo_root)
    if not cfg_path.is_file():
        return None
    cfg = parse_yaml_blocks(load(cfg_path))
    for key in ("lmstudio_drafter_model", "lmstudio_model", "local_drafter_model"):
        val = cfg.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def resolve_model(base_url: str, explicit: str | None, repo_root: Path) -> str:
    return (
        explicit
        or os.environ.get("LMSTUDIO_MODEL")
        or load_run_config_model(repo_root)
        or _find_model(base_url)
        or "local-model"
    )


class LMStudioClient:
    def __init__(self, base_url: str, model: str, temperature: float = 0.75, api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.api_key = api_key or os.environ.get("LMSTUDIO_API_KEY") or os.environ.get("LM_STUDIO_API_KEY")

    def chat(self, messages: list[dict], *, max_tokens: int = 4096) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": max_tokens,
            # LM Studio exposes some local reasoning models that otherwise put
            # prose into reasoning_content and leave message.content empty.
            # The OpenAI-compatible knob LM Studio currently honors is the
            # top-level reasoning_effort field.
            "reasoning_effort": "none",
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}),
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LM Studio HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"cannot reach LM Studio at {self.base_url}: {exc}") from exc
        payload = json.loads(raw)
        try:
            return payload["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"unexpected LM Studio response shape: {raw[:500]}") from exc


def collect_context(book: str, chapter: str, repo_root: Path) -> dict[str, str]:
    outline = _read_optional(penny_paths.input_path(f"book-{book}/outline.md", root=repo_root))
    chapter_brief = extract_chapter_section(outline, chapter)

    continuity_parts = []
    cont_root = penny_paths.series_path("continuity", root=repo_root)
    if cont_root.is_dir():
        for p in sorted(cont_root.rglob("*.md")):
            if p.name == "canon-core.md" or p.stem.lower() in chapter_brief.lower():
                continuity_parts.append(f"# {p.relative_to(cont_root)}\n{p.read_text(encoding='utf-8')}")

    whodunit = _read_optional(penny_paths.series_path(f"whodunit/book-{book}.yaml", root=repo_root))
    reveal = ""
    if whodunit and yaml is not None:
        try:
            data = yaml.safe_load(whodunit)
            if isinstance(data, dict) and data.get("reveal_chapter"):
                reveal = str(data["reveal_chapter"])
        except yaml.YAMLError:
            pass

    context = {
        "chapter_brief": chapter_brief,
        "chapter_context": compact_chapter_context(chapter_brief),
        "voice_pack": _read_config_digest_or_file("voice-pack/lmstudio-digest.md", "voice-pack/voice-pack.md", repo_root),
        "setting_pack": _read_config_pack_for_lmstudio("setting-pack", repo_root),
        "genre_pack": _read_config_pack_for_lmstudio("genre-pack", repo_root),
        "length_profile": _read_optional(penny_paths.config_path("length-profile.md", root=repo_root)),
        "continuity": "\n\n".join(continuity_parts),
        "mystery_solution": _read_optional(penny_paths.output_path(f"book-{book}/mystery-solution.md", root=repo_root)),
        "whodunit": whodunit,
        "whodunit_excerpt": compact_whodunit_context(whodunit, chapter, chapter_brief),
        "reveal_chapter": reveal,
    }
    limits = {
        "chapter_brief": 30_000,
        "chapter_context": 8_000,
        "voice_pack": 3_500,
        "setting_pack": 2_500,
        "genre_pack": 2_500,
        "length_profile": 4_000,
        "continuity": 4_000,
        "mystery_solution": 6_000,
        "whodunit": 4_000,
        "whodunit_excerpt": 3_500,
        "reveal_chapter": 200,
    }
    return {k: _truncate(k, v, limits.get(k, MAX_CONTEXT_CHARS // 10)) for k, v in context.items()}


def system_prompt() -> str:
    return (
        "You are Penny's local prose drafter. Write commercial cozy mystery prose in close third "
        "limited through the protagonist. You are given sealed mystery knowledge only to avoid "
        "contradictions and premature reveals. Do not reveal or confirm culprit guilt before the "
        "book's reveal chapter. Follow the brief exactly; do not invent a new plot. Australian "
        "spelling. Output prose only unless asked for a revision pass."
    )


def scene_prompt(context: dict[str, str], unit: SceneUnit, idx: int, total: int, previous_summary: str) -> str:
    return f"""
Draft scene unit {idx} of {total}: {unit.title}

Target length for this unit: about {unit.target_words} words. It is acceptable to run a little long if the scene work is doing real cozy texture, dialogue, interiority, clue clarity, or emotional turn. Do not write the whole chapter; write only this unit.

Previous scene continuity summary:
{previous_summary or '(none — this is the opening unit)'}

CHAPTER-LEVEL CONTEXT (compressed; scene bodies omitted except the current unit):
{context.get('chapter_context') or compact_chapter_context(context['chapter_brief'])}

THIS SCENE UNIT BRIEF:
{unit.brief}

VOICE PACK:
{context['voice_pack']}

GENRE PACK:
{context['genre_pack']}

SETTING PACK:
{context['setting_pack']}

CONTINUITY LEDGER SLICE:
{context['continuity']}

SEALED MYSTERY / WHODUNIT CONTEXT:
Reveal chapter: {context['reveal_chapter'] or '(unknown)'}
{context.get('whodunit_excerpt') or context.get('whodunit', '')}

Hard requirements:
- Produce finished prose for this scene unit, not notes.
- Ground the scene in physical action, dialogue, sensory/cozy texture, and the stated emotional turn.
- Preserve the protagonist's current knowledge-state.
- Plant only the clues the brief requires; never spotlight future answers.
- End this unit with enough continuity for the next unit to follow.
""".strip()


def summarize_prompt(scene_text: str) -> str:
    return (
        "Summarize this drafted scene in 5 bullet points for continuity into the next scene. "
        "Include only on-page facts, emotional state, location changes, and unresolved hooks.\n\n"
        + scene_text
    )


def stitch_prompt(context: dict[str, str], draft_body: str, target: LengthRange) -> str:
    return f"""
Revise the assembled scene shards into one continuous chapter draft.

Rules:
- Preserve the same plot, clues, scene order, and facts. Do not invent a new scene or solution.
- Smooth transitions, remove repeated setup, maintain consistent close-third POV and voice.
- Ensure the chapter delivers the Chapter Structure Summary and lands the hook.
- Keep cozy texture and embodied action; do not compress into synopsis.
- Target range: {target.minimum}-{target.maximum} words. Lower bound is hard.
- Output the chapter body only, no frontmatter and no commentary.

CHAPTER CONTEXT:
{context.get('chapter_context') or compact_chapter_context(context['chapter_brief'])}

ASSEMBLED SHARDS:
{draft_body}
""".strip()


def expand_prompt(context: dict[str, str], draft_body: str, needed: int) -> str:
    return f"""
The chapter draft is under its required minimum by about {needed} words. Expand it without padding.

Rules:
- Preserve all existing plot facts and order.
- Add real scene work: embodied action, dialogue, interiority, craft/setting/cozy texture, and clearer emotional turns.
- Do not add recap. Do not reveal future mystery knowledge.
- Output the complete revised chapter body only.

CHAPTER CONTEXT:
{context.get('chapter_context') or compact_chapter_context(context['chapter_brief'])}

CURRENT DRAFT:
{draft_body}
""".strip()


def draft_chapter_with_client(context: dict[str, str], client: LMStudioClient, target: LengthRange) -> str:
    target_total = (target.minimum + target.maximum) // 2
    units = split_scene_units(context["chapter_brief"], target_total)
    pieces: list[str] = []
    prev_summary = ""
    for idx, unit in enumerate(units, start=1):
        prompt = scene_prompt(context, unit, idx, len(units), prev_summary)
        print(
            f"lmstudio-draft: scene {idx}/{len(units)} — {unit.title} "
            f"(~{unit.target_words} words, prompt {len(prompt):,} chars)",
            flush=True,
        )
        scene = client.chat([
            {"role": "system", "content": system_prompt()},
            {"role": "user", "content": prompt},
        ], max_tokens=5000)
        pieces.append(scene.strip())
        # Avoid a second model call per scene: local models are slow, and a
        # short prose tail is enough continuity for the next shard.
        prev_summary = " ".join(scene.split()[-120:])

    assembled = "\n\n***\n\n".join(pieces)
    stitch = stitch_prompt(context, assembled, target)
    print(f"lmstudio-draft: stitching scene shards (prompt {len(stitch):,} chars)", flush=True)
    body = client.chat([
        {"role": "system", "content": system_prompt()},
        {"role": "user", "content": stitch},
    ], max_tokens=9000)

    attempts = 0
    while word_count(body) < target.minimum and attempts < 3:
        attempts += 1
        needed = target.minimum - word_count(body)
        expand = expand_prompt(context, body, needed)
        print(f"lmstudio-draft: expansion pass {attempts} (needs ~{needed} words, prompt {len(expand):,} chars)", flush=True)
        body = client.chat([
            {"role": "system", "content": system_prompt()},
            {"role": "user", "content": expand},
        ], max_tokens=9000)
    return body.strip() + "\n"


def write_draft(book: str, chapter: str, body: str, model: str, repo_root: Path, draft_date: str | None = None) -> Path:
    draft_date = draft_date or _dt.date.today().isoformat()
    out_dir = penny_paths.output_path(f"book-{book}/chapters", root=repo_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"ch-{chapter}.draft.md"
    content = f"---\ndrafted_by: {_frontmatter_model(model)}\ndrafted_on: {draft_date}\n---\n\n{body.strip()}\n"
    out.write_text(content, encoding="utf-8")
    return out


def set_stage(book: str, chapter: str, stage: str, repo_root: Path) -> None:
    p = penny_paths.penny_path("current-stage", root=repo_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"book={book} chapter={chapter} stage={stage}\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Draft a Penny chapter via LM Studio scene shards")
    ap.add_argument("book")
    ap.add_argument("chapter")
    ap.add_argument("--model", help="LM Studio model id; defaults to LMSTUDIO_MODEL, run-config, /models first id, then local-model")
    ap.add_argument("--base-url", default=os.environ.get("LMSTUDIO_BASE_URL", DEFAULT_BASE_URL), help="OpenAI-compatible base URL")
    ap.add_argument("--temperature", type=float, default=0.75)
    ap.add_argument("--skip-preflight", action="store_true", help="For tests/experiments only; command runbook should not use this")
    args = ap.parse_args(argv)

    repo_root = penny_paths.series_root()
    book = f"{int(args.book):02d}"
    chapter = f"{int(args.chapter):02d}"

    if not args.skip_preflight:
        from scripts import preflight
        preflight.cmd_draft(book, chapter, repo_root=repo_root)

    # Advisory only; never block drafting.
    try:
        from scripts import outline_feedback
        print(outline_feedback.status_line(book, repo_root=repo_root))
    except Exception as exc:  # pragma: no cover - advisory resilience
        print(f"lmstudio-draft: outline feedback status unavailable: {exc}", file=sys.stderr)

    model = resolve_model(args.base_url, args.model, repo_root)
    set_stage(book, chapter, "DRAFT-LMSTUDIO", repo_root)
    context = collect_context(book, chapter, repo_root)
    target = parse_length_profile(context["length_profile"], context["chapter_brief"])
    client = LMStudioClient(args.base_url, model, temperature=args.temperature)
    body = draft_chapter_with_client(context, client, target)
    out = write_draft(book, chapter, body, model, repo_root)
    set_stage(book, chapter, "DRAFTED", repo_root)

    wc = word_count(body)
    print(f"wrote {out}")
    print(f"drafted_by: {_frontmatter_model(model)}")
    print(f"word_count: {wc} (target {target.minimum}-{target.maximum}, {target.label})")
    if wc < target.minimum:
        print("WARNING: draft remains under minimum after repair attempts", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
