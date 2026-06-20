from scripts.penny_text import quote_spans, strip_dialogue


def test_strip_dialogue_preserves_length_and_newlines():
    text = 'She walked home.\n"Get stuffed," he said.\nThe rain fell.'
    out = strip_dialogue(text)
    assert len(out) == len(text)                      # offsets stay aligned
    assert out.count("\n") == text.count("\n")        # line numbers stay aligned
    assert "Get stuffed" not in out                    # dialogue blanked
    assert "She walked home." in out                   # narration kept
    assert "he said." in out                           # said-bookend narration kept


def test_term_inside_quote_is_blanked_but_in_narration_is_kept():
    # 'arvo' inside dialogue must survive in the dialogue but be gone from narration;
    # 'arvo' in the narrative clause must remain.
    text = 'It was a quiet arvo.\n"See you this arvo," she called.'
    narration = strip_dialogue(text)
    assert "It was a quiet arvo." in narration          # narrative-clause term kept
    assert "See you this arvo" not in narration         # in-dialogue term removed


def test_apostrophe_is_not_treated_as_dialogue():
    text = "I'm fine and I don't care, the cat's tail twitched."
    out = strip_dialogue(text)
    assert out == text                                  # single quotes are apostrophes, untouched
    assert quote_spans(text) == []


def test_smart_quotes_are_stripped():
    text = "The wind rose. “It’s late,” Cora said."  # smart-quoted dialogue
    out = strip_dialogue(text)
    assert "late" not in out                            # dialogue content gone
    assert "The wind rose." in out                      # leading narration kept
    assert "Cora said." in out                          # said-bookend narration kept
    assert quote_spans(text)                             # span detected


def test_dialogue_spanning_a_blank_line_is_handled_conservatively():
    # Balanced double quotes across paragraphs: each quoted run is its own span.
    text = '"First line of speech."\n\n"Second line of speech."\nNarration after.'
    out = strip_dialogue(text)
    assert "First line of speech" not in out
    assert "Second line of speech" not in out
    assert "Narration after." in out
    assert out.count("\n") == text.count("\n")


def test_em_dash_text_without_quotes_is_narration():
    # House style is quoted dialogue; an em-dash line with no quotes is narration.
    text = "She paused — the arvo light slanting low — and frowned."
    assert strip_dialogue(text) == text
    assert quote_spans(text) == []
