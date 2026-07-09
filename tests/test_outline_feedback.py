import copy
import scripts.outline_feedback as of


def _seed():
    return {
        "book": "01",
        "reviewed_outline_sha256": "oldsha",
        "items": [
            {"id": "OF-1", "source": "claude", "pass": 1, "state": "solved", "text": "a"},
            {"id": "OF-2", "source": "codex", "pass": 1, "state": "rejected", "text": "b"},
        ],
    }


def test_append_preserves_existing_items_exactly():
    ledger = _seed()
    before = copy.deepcopy(ledger["items"])
    out = of.append_items(
        ledger,
        [{"source": "claude", "text": "c"}, {"source": "codex", "text": "d"}],
        reviewed_sha="newsha",
    )
    assert out["items"][:2] == before  # existing items byte-identical
    assert out["reviewed_outline_sha256"] == "newsha"


def test_append_allocates_monotonic_ids_and_next_pass():
    out = of.append_items(_seed(), [{"source": "claude", "text": "c"}], reviewed_sha="s")
    assert out["items"][2] == {
        "id": "OF-3", "source": "claude", "pass": 2, "state": "open", "text": "c",
    }


def test_append_shares_one_pass_across_all_new_points():
    out = of.append_items(
        _seed(),
        [{"source": "claude", "text": "c"}, {"source": "codex", "text": "d"}],
        reviewed_sha="s",
    )
    assert out["items"][2]["pass"] == out["items"][3]["pass"] == 2
    assert out["items"][2]["id"] == "OF-3" and out["items"][3]["id"] == "OF-4"


def test_append_onto_empty_ledger_starts_at_one_and_pass_one():
    out = of.append_items(of.empty_ledger("01"), [{"source": "claude", "text": "x"}], reviewed_sha="s")
    assert out["items"] == [{"id": "OF-1", "source": "claude", "pass": 1, "state": "open", "text": "x"}]


def test_append_does_not_mutate_input_ledger():
    ledger = _seed()
    of.append_items(ledger, [{"source": "claude", "text": "c"}], reviewed_sha="s")
    assert len(ledger["items"]) == 2 and ledger["reviewed_outline_sha256"] == "oldsha"
