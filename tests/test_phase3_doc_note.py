from pathlib import Path

DESIGN = Path("penny-design-v3.md")


def test_codex_plugin_recorded():
    text = DESIGN.read_text(encoding="utf-8")
    assert "Codex plugin" in text, "master doc must record the Codex-via-plugin decision"
    assert "supersedes" in text.lower(), "the note must mark it as superseding the adapter wording"
