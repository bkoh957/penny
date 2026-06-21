# run-config.md — Penny run configuration

The fixed engine reads this file for model routing, run-mode flags, and escalation
thresholds. All values are MVP 1 defaults; thresholds marked "tunable" are Book-1
seeds, not load-bearing constants. See design §7 (routing), §12 (flags), §6
(thresholds), §8 (structure inspector).

## Model-per-role (design §7)

The final-read invariant is **difference, not identity**: `final_read_model` must
not appear among the chapters' `drafted_by` stamps (enforced by `preflight.py` in
Phase 3). Substitute any reachable alternate model.

```yaml
drafting_model:   claude-opus
inspector_model:  claude-opus
copyedit_model:   claude-opus
final_read_model: codex            # MUST differ from drafting_model
beta_models:      [codex, hermes, openclaw]
```

## Run-mode flags (design §12)

```yaml
cadence:          chapter          # chapter | book-milestone
panel_size:       1                # 1 (fast) | 3 (consensus)
beta_consensus_k: 2                # ≥K-of-M beta models must flag a put-down for
                                   # per-persona consensus; default = majority of
                                   # panel_size (book-level panel_size: 3 → 2); tunable
gate_mode:        strict           # strict | fast
escalation_scope: minor-auto       # minor-auto | log-all
ledger_approval:  review           # review (early/tuning) | auto (once clean)
book_approval:    review           # review (pause for showrunner) | auto
```

## Escalation thresholds (design §6)

```yaml
escalate_on_blocking_disagreement: true   # HARD — holds gate, escalates now
score_spread_log_threshold: 2             # SOFT — logged only; tunable Book 1
revision_escalate_personas: 2             # >=N distinct personas flag a put-down at a chapter -> escalate; tunable
would_buy_escalate_count:   3             # >=N personas say "would not buy next" -> escalate; tunable
```

## Structure inspector (design §8)

```yaml
thread_dormant_after_chapters: 3          # flag a thread idle beyond N chapters; tunable
culprit_by_fraction: 0.5                  # fairplay: culprit on-page by this fraction of the book; tunable
```
