from pathlib import Path

from scripts import lmstudio_draft_chapter as lm


def test_extract_chapter_section_accepts_zero_padded_number():
    outline = """---
book: 01
total_chapters: 2
---

## Chapter 01 — Arrival

### Overall Summary
One.

---

## Chapter 02 — Body

Two.
"""
    section = lm.extract_chapter_section(outline, "1")
    assert section.startswith("## Chapter 01 — Arrival")
    assert "## Chapter 02" not in section


def test_split_scene_units_allocates_targets():
    brief = """## Chapter 03 — Test

### Scene 1 — Kitchen
A.

### Scene 2 — Beach
B.
"""
    units = lm.split_scene_units(brief, 2200)
    assert [u.title for u in units] == ["Scene 1 — Kitchen", "Scene 2 — Beach"]
    assert sum(u.target_words for u in units) == 2200
    assert all(u.target_words >= 450 for u in units)


def test_split_scene_units_does_not_attach_chapter_notes_to_last_scene():
    brief = """## Chapter 03 — Test

### Scene 1 — Kitchen
A.

### Scene 2 — Beach
B.

### Chapter Structure Summary
Chapter-level notes.
"""
    units = lm.split_scene_units(brief, 2200)
    assert units[-1].title == "Scene 2 — Beach"
    assert "Chapter Structure Summary" not in units[-1].brief


def test_compact_chapter_context_keeps_scene_map_and_drops_scene_bodies():
    brief = """## Chapter 03 — Test

### Overall Summary
Overall.

### Scene 1 — Kitchen
Long private beat flow for kitchen.

### Scene 2 — Beach
Long private beat flow for beach.

### Drafting Notes / Guardrails
Keep the hook.
"""
    compact = lm.compact_chapter_context(brief)
    assert "Overall." in compact
    assert "- Scene 1 — Kitchen" in compact
    assert "- Scene 2 — Beach" in compact
    assert "Keep the hook." in compact
    assert "Long private beat flow" not in compact


def test_compact_whodunit_context_keeps_current_rows_not_full_answer_key():
    whodunit = Path("tests/fixtures/cozy/series/whodunit/book-01.yaml").read_text(encoding="utf-8")
    excerpt = lm.compact_whodunit_context(whodunit, "09", "## Chapter 09\nSaffron pressure.")
    assert "reveal_chapter" in excerpt
    assert "rh-saffron" in excerpt
    assert "central_deception" not in excerpt
    assert "culprit:" not in excerpt


def test_collect_context_prefers_lmstudio_digests(tmp_path):
    (tmp_path / ".penny").mkdir()
    (tmp_path / "input/book-01").mkdir(parents=True)
    (tmp_path / "config/voice-pack").mkdir(parents=True)
    (tmp_path / "config/setting-pack").mkdir(parents=True)
    (tmp_path / "config/genre-pack").mkdir(parents=True)
    (tmp_path / "series/continuity").mkdir(parents=True)
    (tmp_path / "series/whodunit").mkdir(parents=True)
    (tmp_path / "input/book-01/outline.md").write_text(
        """---
book: 01
total_chapters: 1
---

## Chapter 01 — Test

### Scene 1 — One
Do the scene.
""",
        encoding="utf-8",
    )
    (tmp_path / "config/voice-pack/voice-pack.md").write_text("FULL VOICE", encoding="utf-8")
    (tmp_path / "config/voice-pack/lmstudio-digest.md").write_text("VOICE DIGEST", encoding="utf-8")
    (tmp_path / "config/setting-pack/coast.md").write_text("FULL SETTING", encoding="utf-8")
    (tmp_path / "config/setting-pack/lmstudio-digest.md").write_text("SETTING DIGEST", encoding="utf-8")
    (tmp_path / "config/genre-pack/cozy.md").write_text("FULL GENRE", encoding="utf-8")
    (tmp_path / "config/genre-pack/lmstudio-digest.md").write_text("GENRE DIGEST", encoding="utf-8")
    (tmp_path / "config/length-profile.md").write_text("| Standard | 2,000–2,500 |", encoding="utf-8")
    (tmp_path / "series/whodunit/book-01.yaml").write_text("book: 01\nreveal_chapter: 25\nvictim: neil\n", encoding="utf-8")

    context = lm.collect_context("01", "01", tmp_path)
    assert context["voice_pack"] == "VOICE DIGEST"
    assert context["setting_pack"] == "SETTING DIGEST"
    assert context["genre_pack"] == "GENRE DIGEST"
    assert "FULL VOICE" not in context["voice_pack"]
    assert "FULL SETTING" not in context["setting_pack"]
    assert "FULL GENRE" not in context["genre_pack"]


def test_parse_length_profile_defaults_to_standard():
    text = """| Chapter type | Word range |
|---|---|
| Opening chapter | 1,800–2,400 |
| Standard investigation / character chapter | 2,000–2,500 |
| Major reveal / emotional shift | 2,500–3,200 |
"""
    rng = lm.parse_length_profile(text, "## Chapter 12 — Ordinary Trouble")
    assert (rng.minimum, rng.maximum) == (2000, 2500)


def test_parse_length_profile_detects_major_reveal():
    text = """| Chapter type | Word range |
|---|---|
| Standard investigation / character chapter | 2,000–2,500 |
| Major reveal / emotional shift | 2,500–3,200 |
"""
    rng = lm.parse_length_profile(text, "### Chapter Structure Summary\n- Major reveal / emotional shift")
    assert (rng.minimum, rng.maximum) == (2500, 3200)


class FakeClient:
    def __init__(self):
        self.calls = []

    def chat(self, messages, *, max_tokens=4096):
        prompt = messages[-1]["content"]
        self.calls.append(prompt)
        if "Summarize this drafted scene" in prompt:
            return "- continuity summary"
        if "Revise the assembled scene shards" in prompt:
            return "stitched body " * 120
        return "scene body " * 80


def test_draft_chapter_with_client_uses_scene_shards_and_stitch_pass():
    context = {
        "chapter_brief": """## Chapter 04 — Test

### Scene 1 — One
Do first thing.

### Scene 2 — Two
Do second thing.
""",
        "chapter_context": "compressed chapter context",
        "voice_pack": "voice",
        "genre_pack": "genre",
        "setting_pack": "setting",
        "continuity": "canon",
        "mystery_solution": "solution",
        "whodunit": "reveal_chapter: 25",
        "whodunit_excerpt": "reveal_chapter: 25\nclue_schedule_excerpt: []",
        "reveal_chapter": "25",
    }
    client = FakeClient()
    body = lm.draft_chapter_with_client(context, client, lm.LengthRange("Standard", 100, 200))
    assert "stitched body" in body
    assert any("Draft scene unit 1 of 2" in c for c in client.calls)
    assert any("Draft scene unit 2 of 2" in c for c in client.calls)
    assert any("Revise the assembled scene shards" in c for c in client.calls)


def test_write_draft_stamps_lmstudio_model(tmp_path):
    (tmp_path / ".penny").mkdir()
    out = lm.write_draft("01", "03", "Chapter prose.", "gemma-4-local", tmp_path, draft_date="2026-07-11")
    text = out.read_text(encoding="utf-8")
    assert out == tmp_path / "output/book-01/chapters/ch-03.draft.md"
    assert "drafted_by: lmstudio/gemma-4-local" in text
    assert "drafted_on: 2026-07-11" in text


def test_lmstudio_command_runs_same_preflight_gate():
    text = Path("commands/draft-chapter-lmstudio.md").read_text(encoding="utf-8")
    assert "scripts/preflight.py" in text and "preflight.py\" draft" in text
    assert "lmstudio_draft_chapter.py" in text
