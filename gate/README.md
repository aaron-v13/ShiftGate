# ShiftGate: Gate Subsystem (`gate/`)

The gate subsystem evaluates reference-bank candidate versions against the active baseline model to prevent defect escapes and ensure false-hold reductions.

## Public API (`gate.api`)

- `run_gate(scores_path, policy_path, current, candidate) -> dict`  
  Compares validation scores of candidate against current version using calibration-derived thresholds and policy rules, returning a gate report.

- `record_approval(report, reviewer, note, registry_path=None) -> dict`  
  Attaches quality reviewer sign-off to a gate report, logs the approval in the registry, and returns an updated report copy.

- `activate(report, registry_path=None) -> dict`  
  Promotes an approved ALLOW candidate to active in the registry, moving current to previous, and guarding against stale reports.

- `rollback(registry_path=None) -> dict`  
  Restores the previous model version as active in the registry and logs the rollback action.

- `export_bundle(report, out_dir, extra_files=None) -> str`  
  Exports a reproducible compliance bundle containing report, changed decisions, policy snapshot, and SHA-256 hashes.

- `get_registry(registry_path=None) -> dict`  
  Loads current registry state (active version, previous version, and audit history), initializing default state if absent.

- `reset_registry(registry_path=None) -> dict`  
  Resets registry to initial state (`v1_current` active, no previous version, empty history) for demonstration resets.

## Internal Submodules

- `gate.schema.validate_scores(df, versions_needed=None) -> None`  
  Validates input scores DataFrame against schema rules, data types, split integrity, and device values, raising `ScoresError` on failure.

- `gate.fake_data.generate_fake_data(out_dir="gate", seed=42) -> tuple[pd.DataFrame, dict]`  
  Generates deterministic synthetic scores and run metadata demonstrating false-hold reduction and defect escape scenarios.

- `gate.thresholds.compute_thresholds(df, percentile=99.0, versions=None) -> dict[str, float]`  
  Computes per-version decision thresholds using calibration normal scores at the configured percentile.

- `gate.thresholds.get_threshold_warnings(df, versions=None, min_count=20) -> list[str]`  
  Returns warning strings when calibration sets have fewer than the recommended sample size.

- `gate.decisions.decide(scores, threshold) -> Union[str, pd.Series, list[str]]`  
  Applies decision rule: marks `HOLD` if score is strictly above threshold, else `PASS` (ties pass).

- `gate.metrics.compute_metrics(df_val, decisions) -> dict[str, Any]`  
  Calculates false hold counts/rates, defect recall, and per-condition metrics on validation data.

- `gate.compare.find_changed_decisions(df_val_current, current_thresh, df_val_cand, cand_thresh) -> list[dict]`  
  Identifies images whose decision changes between versions, classified and sorted by contract priority order.

- `gate.compare.evaluate_policy(current_metrics, candidate_metrics, changed_decisions, policy) -> tuple[str, list[str]]`  
  Applies all policy rules (missed defects, defect recall, false-hold reduction, per-condition checks) to yield `ALLOW` or `BLOCK` and reasons.
