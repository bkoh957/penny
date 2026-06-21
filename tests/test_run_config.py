from scripts.penny_meta import load, parse_yaml_blocks

REQUIRED_KEYS = {
    # model-per-role (design §7)
    "drafting_model", "inspector_model", "copyedit_model",
    "final_read_model", "beta_models",
    # run-mode flags (design §12)
    "cadence", "panel_size", "gate_mode", "escalation_scope", "ledger_approval",
    "beta_consensus_k",
    # escalation thresholds (design §6)
    "escalate_on_blocking_disagreement", "score_spread_log_threshold",
    # structure inspector (design §8)
    "thread_dormant_after_chapters",
}


def test_run_config_declares_all_required_keys():
    cfg = parse_yaml_blocks(load("config/run-config.md"))
    missing = REQUIRED_KEYS - set(cfg)
    assert not missing, f"run-config.md missing keys: {sorted(missing)}"


def test_final_read_differs_from_drafting_model():
    cfg = parse_yaml_blocks(load("config/run-config.md"))
    assert cfg["final_read_model"] != cfg["drafting_model"], (
        "final_read_model must differ from drafting_model (design §7 invariant)"
    )
