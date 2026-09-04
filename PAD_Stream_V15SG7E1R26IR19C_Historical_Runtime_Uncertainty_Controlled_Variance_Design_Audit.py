from __future__ import annotations

from pathlib import Path
import csv
import json

# =============================================================================
# PAD-Stream V15-SG7E1R26I-R19C
# Historical Runtime Uncertainty / Controlled Variance Design Audit
#
# DESIGN-ONLY MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO MODEL.PREDICT CALL WILL BE EXECUTED.
# NO FROZEN L2 ARRAY CHANGED.
# NO GAMMA / GUARD RECALIBRATION.
# NO 250/500/1000-DAY STATE WILL BE GENERATED.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO PRECISION ENVELOPE WILL BE RELAXED.
# NO CREATOR / MODEL / X100 AUTHORITY WILL BE REOPENED.
#
# PURPOSE
# -------
# R19B established that the exact historical runtime cannot be reconstructed
# completely because at least:
#
#   TensorFlow version : unresolved
#   oneDNN state       : unresolved
#
# while:
#
#   Keras version      : 3.15.1
#   determinism        : explicit
#   TF thread contract : explicit
#
# R19C does NOT execute inference. It defines a bounded, provenance-safe
# variance experiment that may be executed in a later milestone.
#
# The experiment may vary ONLY historically unresolved runtime dimensions.
# It must not vary:
#
#   - model weights
#   - X100
#   - tD_scale
#   - batch semantics
#   - correction operators
#   - SG7E thresholds
#   - R16 precision envelope
#
# The objective is not to "find settings that pass." The objective is to
# characterize whether the creator100/frozen100 discrepancy is stable under a
# small admissible runtime envelope and whether any explicitly supported runtime
# configuration reproduces the historical frozen100 identity.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR19C"
OUT.mkdir(parents=True, exist_ok=True)

R19B_DIR = ROOT / "output" / "V15_SG7E1R26IR19B"
R19B_SUMMARY = R19B_DIR / "PAD_Stream_V15SG7E1R26IR19B_Summary.json"
R19B_COMPONENTS = R19B_DIR / "V15SG7E1R26IR19B_Runtime_Component_Resolution.csv"

R16_DIR = ROOT / "output" / "V15_SG7E1R26IR16"
R16_CONTRACT = R16_DIR / "V15SG7E1R26IR16_SG7B16_Frozen100_Runtime_Contract.json"

# Outputs
UNCERTAINTY_TABLE = OUT / "V15SG7E1R26IR19C_Runtime_Uncertainty_Inventory.csv"
FIXED_TABLE = OUT / "V15SG7E1R26IR19C_Fixed_Runtime_and_Physics_Contract.csv"
VARIANCE_TABLE = OUT / "V15SG7E1R26IR19C_Admissible_Runtime_Variance_Matrix.csv"
METRIC_TABLE = OUT / "V15SG7E1R26IR19C_Required_Replay_Metrics.csv"
STOP_TABLE = OUT / "V15SG7E1R26IR19C_Stopping_and_Interpretation_Rules.csv"
GATE_TABLE = OUT / "V15SG7E1R26IR19C_Final_Design_Gates.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR19C_Controlled_Variance_Design_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R26IR19C_Controlled_Runtime_Variance_Design_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR19C_Summary.json"


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path):
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_csv(path: Path, rows):
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def boolish(v):
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes"}


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R19C")
    print("Historical Runtime Uncertainty / Controlled Variance Design Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO PRECISION ENVELOPE WILL BE CHANGED OR RELAXED.
NO CREATOR / MODEL / X100 AUTHORITY WILL BE REOPENED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
THIS MILESTONE DEFINES A BOUNDED RUNTIME-VARIANCE EXPERIMENT ONLY.
""")

    prev = load_json(R19B_SUMMARY)
    if prev.get("status") != "HISTORICAL_RUNTIME_ENVIRONMENT_COMPONENTS_STILL_INCOMPLETE":
        raise RuntimeError("R19C requires the incomplete R19B runtime-environment result.")

    components = load_csv(R19B_COMPONENTS)
    comp = {r["component"]: r for r in components}

    # -------------------------------------------------------------------------
    # Correct uncertainty inventory
    # -------------------------------------------------------------------------
    uncertainty_rows = []
    for name, row in comp.items():
        resolved = boolish(row.get("resolved", False))
        uncertainty_rows.append({
            "component": name,
            "resolved": resolved,
            "historical_value_or_evidence": row.get("value_or_evidence", ""),
            "role": "FIXED" if resolved else "UNCERTAIN",
            "may_vary_in_controlled_experiment": (
                not resolved and name in {"TensorFlow version", "TF_ENABLE_ONEDNN_OPTS"}
            ),
        })
    save_csv(UNCERTAINTY_TABLE, uncertainty_rows)

    # -------------------------------------------------------------------------
    # Fixed contract
    # -------------------------------------------------------------------------
    r16 = load_json(R16_CONTRACT)
    x100 = r16["X100"]
    model = r16["model"]
    closure = r16["closure"]

    fixed_rows = [
        {"quantity": "creator_source", "value": "PAD_Stream_V15SG7B16_Controlled_Front_Preserving_TOF_Refinement.py"},
        {"quantity": "model_path", "value": model["path"]},
        {"quantity": "model_sha256", "value": model["sha256"]},
        {"quantity": "X100_sha256", "value": x100["sha256"]},
        {"quantity": "X100_shape", "value": str(tuple(x100["shape"]))},
        {"quantity": "X100_dtype", "value": x100["dtype"]},
        {"quantity": "tD_scale", "value": x100["tD_scale"]},
        {"quantity": "batch_semantics", "value": "historical_source-defined; must remain unchanged"},
        {"quantity": "Keras_version", "value": "3.15.1"},
        {"quantity": "determinism_contract", "value": "historically explicit; must remain enabled as historically specified"},
        {"quantity": "thread_contract", "value": "historically explicit TF intra/inter-op contract; must remain fixed"},
        {"quantity": "precision_envelope", "value": closure["precision_envelope"]},
        {"quantity": "SG7E_threshold", "value": "unchanged"},
        {"quantity": "gamma_guard", "value": "unchanged"},
        {"quantity": "later_time_generation", "value": "prohibited"},
    ]
    save_csv(FIXED_TABLE, fixed_rows)

    # -------------------------------------------------------------------------
    # Bounded admissible variance matrix
    #
    # Only unresolved runtime dimensions can vary. We deliberately do not guess
    # a historical TensorFlow version. Instead we define admissible categories:
    #
    #   CURRENT_RUNTIME_BASELINE
    #   ONEDNN_DISABLED_SAME_RUNTIME
    #
    # A different TensorFlow version is NOT authorized here because R19B did
    # not recover a historical version. It remains a future option only if an
    # explicit historical version is later found.
    # -------------------------------------------------------------------------
    variance_rows = [
        {
            "case_id": "C0",
            "description": "Current runtime baseline reproduction",
            "tensorflow_version": "CURRENT_INSTALLED",
            "keras_version": "3.15.1_FIXED",
            "TF_ENABLE_ONEDNN_OPTS": "CURRENT_UNSET",
            "thread_contract": "FIXED_HISTORICAL",
            "determinism_contract": "FIXED_HISTORICAL",
            "authorized": True,
            "reason": "Baseline control already represented by R16 runtime.",
        },
        {
            "case_id": "C1",
            "description": "Same runtime with oneDNN explicitly disabled",
            "tensorflow_version": "CURRENT_INSTALLED",
            "keras_version": "3.15.1_FIXED",
            "TF_ENABLE_ONEDNN_OPTS": "0",
            "thread_contract": "FIXED_HISTORICAL",
            "determinism_contract": "FIXED_HISTORICAL",
            "authorized": True,
            "reason": (
                "oneDNN is historically unresolved and current TensorFlow explicitly warns "
                "that oneDNN may change floating-point results by operation ordering."
            ),
        },
        {
            "case_id": "C2",
            "description": "Alternative TensorFlow historical-version replay",
            "tensorflow_version": "UNRESOLVED_HISTORICAL_VERSION",
            "keras_version": "3.15.1_FIXED",
            "TF_ENABLE_ONEDNN_OPTS": "UNRESOLVED",
            "thread_contract": "FIXED_HISTORICAL",
            "determinism_contract": "FIXED_HISTORICAL",
            "authorized": False,
            "reason": (
                "Historical TensorFlow version is not recovered. Do not install or select "
                "a version by numerical closeness."
            ),
        },
        {
            "case_id": "C3",
            "description": "Thread-count perturbation",
            "tensorflow_version": "CURRENT_INSTALLED",
            "keras_version": "3.15.1_FIXED",
            "TF_ENABLE_ONEDNN_OPTS": "CURRENT_UNSET",
            "thread_contract": "ALTERED",
            "determinism_contract": "FIXED_HISTORICAL",
            "authorized": False,
            "reason": (
                "Thread contract is historically resolved and therefore is not an admissible "
                "uncertainty dimension."
            ),
        },
    ]
    save_csv(VARIANCE_TABLE, variance_rows)

    # -------------------------------------------------------------------------
    # Required metrics for any future execution
    # -------------------------------------------------------------------------
    metric_rows = [
        {"metric": "creator100_sha256", "required": True, "purpose": "Exact runtime identity"},
        {"metric": "frozen100_sha256", "required": True, "purpose": "Historical target identity"},
        {"metric": "L1", "required": True, "purpose": "Global mean absolute replay difference"},
        {"metric": "L2", "required": True, "purpose": "Global RMS replay difference"},
        {"metric": "Linf", "required": True, "purpose": "Frozen precision gate"},
        {"metric": "count_above_R16_envelope", "required": True, "purpose": "Sparse tail comparison"},
        {"metric": "max_float32_ULP", "required": True, "purpose": "Runtime numerical drift magnitude"},
        {"metric": "90_cell_frozen_fingerprint_exact", "required": True, "purpose": "Historical discrepancy fingerprint"},
        {"metric": "exact_frozen100_hash_match", "required": True, "purpose": "Strongest possible reproducibility evidence"},
    ]
    save_csv(METRIC_TABLE, metric_rows)

    # -------------------------------------------------------------------------
    # Interpretation / stopping rules
    # -------------------------------------------------------------------------
    stop_rows = [
        {
            "rule_id": "S1",
            "condition": "C1 exact hash == frozen100",
            "interpretation": "oneDNN runtime ordering explains historical identity difference",
            "action": "Freeze runtime provenance result; do not widen tolerance.",
        },
        {
            "rule_id": "S2",
            "condition": "C1 Linf <= unchanged R16 envelope but hash differs",
            "interpretation": "oneDNN setting restores precision-contract closure without exact bit identity",
            "action": "Audit precision-equivalence only; do not change physical gates.",
        },
        {
            "rule_id": "S3",
            "condition": "C1 remains outside R16 envelope",
            "interpretation": "oneDNN alone does not explain historical frozen100",
            "action": "Do not broaden experiment automatically; historical TensorFlow version remains unresolved.",
        },
        {
            "rule_id": "S4",
            "condition": "Any unauthorized case is needed to obtain closure",
            "interpretation": "reproducibility cannot be certified from preserved provenance",
            "action": "Record historical runtime as partially unrecoverable; do not tune runtime by performance.",
        },
        {
            "rule_id": "S5",
            "condition": "Any case changes model/X100/threshold/gamma/guard/thread contract",
            "interpretation": "contract violation",
            "action": "Reject case.",
        },
    ]
    save_csv(STOP_TABLE, stop_rows)

    unresolved = [r for r in uncertainty_rows if not r["resolved"]]
    authorized_cases = [r for r in variance_rows if r["authorized"]]

    gates = [
        ("R19B_incomplete_runtime_result_reproduced", True),
        ("runtime_uncertainty_inventory_constructed", len(uncertainty_rows) > 0),
        ("resolved_runtime_components_frozen", True),
        ("only_unresolved_components_allowed_to_vary", all(
            (
                (r["may_vary_in_controlled_experiment"] and not r["resolved"])
                or (not r["may_vary_in_controlled_experiment"])
            )
            for r in uncertainty_rows
        )),
        ("oneDNN_off_case_defined", any(r["case_id"] == "C1" and r["authorized"] for r in variance_rows)),
        ("unknown_tensorflow_version_not_authorized", any(r["case_id"] == "C2" and not r["authorized"] for r in variance_rows)),
        ("thread_perturbation_not_authorized", any(r["case_id"] == "C3" and not r["authorized"] for r in variance_rows)),
        ("R16_precision_envelope_fixed", True),
        ("required_replay_metrics_defined", len(metric_rows) >= 8),
        ("stopping_rules_defined", len(stop_rows) >= 5),
        ("no_model_predict_executed", True),
        ("no_training_performed", True),
        ("no_precision_relaxation", True),
        ("no_authority_reopened", True),
        ("no_later_time_state_generated", True),
    ]
    failed = [g for g, p in gates if not p]
    save_csv(GATE_TABLE, [{"gate": g, "passed": p} for g, p in gates])

    status = "CONTROLLED_RUNTIME_VARIANCE_EXPERIMENT_DESIGN_READY"
    diagnosis = (
        "HISTORICAL_RUNTIME_IS_PARTIALLY_UNRECOVERABLE_BUT_ONE_BOUNDED_UNRESOLVED_RUNTIME_DIMENSION_CAN_BE_TESTED_WITHOUT_CHANGING_MODEL_OR_GATES"
    )
    recommendation = (
        "Execute only the authorized controlled cases. C0 is the existing baseline. "
        "C1 is the only new execution authorized: current TensorFlow/Keras runtime with "
        "TF_ENABLE_ONEDNN_OPTS=0, while keeping the historical thread/determinism contract, "
        "model, X100, batch semantics, and precision envelope unchanged. Do not test alternate "
        "TensorFlow versions unless a historical version is explicitly recovered."
    )
    next_ms = (
        "V15-SG7E1R26I-R19D — Controlled oneDNN-Off 100-Day Replay"
    )

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "unresolved_runtime_component_count": len(unresolved),
        "authorized_case_count": len(authorized_cases),
        "authorized_cases": ";".join(r["case_id"] for r in authorized_cases),
        "failed_gates": ";".join(failed),
        "next_milestone": next_ms,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R19C",
        "status": status,
        "diagnosis": diagnosis,
        "uncertainty_inventory": uncertainty_rows,
        "fixed_contract": fixed_rows,
        "variance_matrix": variance_rows,
        "required_metrics": metric_rows,
        "stopping_rules": stop_rows,
        "constraints": {
            "training_performed": False,
            "model_predict_executed": False,
            "model_parameters_changed": False,
            "precision_envelope_relaxed": False,
            "creator_authority_reopened": False,
            "model_authority_reopened": False,
            "X100_authority_reopened": False,
            "thread_contract_change_authorized": False,
            "historical_tensorflow_version_guessed": False,
            "new_250d_state_generated": False,
            "new_500d_state_generated": False,
            "new_1000d_state_generated": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R26I-R19C",
        "status": status,
        "diagnosis": diagnosis,
        "authorized_cases": [r["case_id"] for r in authorized_cases],
        "failed_gates": failed,
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("RUNTIME UNCERTAINTY")
    for r in uncertainty_rows:
        print(
            f"  {r['component']:<24} | resolved={str(r['resolved']):<5} | "
            f"mayVary={r['may_vary_in_controlled_experiment']}"
        )

    print("\nCONTROLLED VARIANCE CASES")
    for r in variance_rows:
        print(
            f"  {r['case_id']} | authorized={str(r['authorized']):<5} | "
            f"{r['description']}"
        )

    print("\nFIXED ACCEPTANCE CONTRACT")
    print(f"  Precision envelope      : {closure['precision_envelope']}")
    print(f"  Model SHA-256           : {model['sha256']}")
    print(f"  X100 SHA-256            : {x100['sha256']}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R19C FINAL DESIGN GATES")
    print("=" * 78)
    for g, p in gates:
        print(f"[{'PASS' if p else 'FAIL'}] {g}")
    print("=" * 78)

    print("\nSTATUS")
    print(f"  {status}")
    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")
    print("\nRECOMMENDATION")
    print(f"  {recommendation}")
    print("\nNEXT MILESTONE")
    print(f"  {next_ms}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUT}")
    print("\nTables:")
    for p in (
        UNCERTAINTY_TABLE,
        FIXED_TABLE,
        VARIANCE_TABLE,
        METRIC_TABLE,
        STOP_TABLE,
        GATE_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")
    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R19C CONTROLLED RUNTIME VARIANCE DESIGN AUDIT: COMPLETE")
    print()
    print("No model.predict call was executed.")
    print("No training was performed.")
    print("The precision envelope was not relaxed.")
    print("No model/X100/thread authority was changed.")
    print("No later-time state was generated.")
    print("=" * 78)


if __name__ == "__main__":
    main()
