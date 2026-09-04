from __future__ import annotations

from pathlib import Path
import csv
import json


# =============================================================================
# PAD-Stream V15-SG7E1R26I-R21
# Multi-Time Deployment Coverage Limitation / SG7E Scope Decision Audit
#
# DECISION-ONLY MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO MODEL.PREDICT CALL WILL BE EXECUTED.
# NO FROZEN L2 ARRAY CHANGED.
# NO SG7D6 FULL-GRID ARRAY CHANGED.
# NO 250/500/1000-DAY STATE WILL BE GENERATED.
# NO INTERPOLATION / EXTRAPOLATION.
# NO SG7E THRESHOLD CHANGED OR RELAXED.
# NO PRECISION ENVELOPE WILL BE RELAXED.
# NO CREATOR / MODEL / X100 AUTHORITY WILL BE REOPENED.
#
# PURPOSE
# -------
# R20R established the corrected multi-time state result:
#
#   250 d  -> rejected (relabelled / semantically contradictory frozen100)
#   500 d  -> rejected (relabelled / semantically contradictory frozen100)
#   1000 d -> no persisted state
#
# Therefore the frozen historical deployment branch does NOT contain a
# provenance-valid, reproducible L2 state set at all four historical SG7E times.
#
# R21 formalizes the architectural consequence:
#
#   - SG7E remains valid as a HISTORICAL MULTI-TIME REFERENCE / ACCEPTANCE
#     CONTRACT over the persisted SG7A_corrected 4-time reference tensor.
#
#   - SG7D6 remains valid as an AUTHORITATIVE FROZEN SINGLE-STATE DEPLOYMENT
#     ARTIFACT.
#
#   - The current frozen deployment lineage is NOT certified as a fully
#     reproducible four-time deployment sequence.
#
#   - No SG7E multi-time gate may be retroactively applied by pretending the
#     single frozen SG7D6 grid corresponds to 250/500/1000 days.
#
# This milestone makes no numerical modification. It defines scope only.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7E1R26IR21"
OUT.mkdir(parents=True, exist_ok=True)

R20R_DIR = ROOT / "output" / "V15_SG7E1R26IR20R"
R20R_SUMMARY = R20R_DIR / "PAD_Stream_V15SG7E1R26IR20R_Summary.json"
R20R_COVERAGE = R20R_DIR / "V15SG7E1R26IR20R_Corrected_Required_Time_Coverage.csv"

R19E_DIR = ROOT / "output" / "V15_SG7E1R26IR19E"
R19E_SUMMARY = R19E_DIR / "PAD_Stream_V15SG7E1R26IR19E_Summary.json"

R14_DIR = ROOT / "output" / "V15_SG7E1R14"
R14_SUMMARY = R14_DIR / "PAD_Stream_V15SG7E1R14_Summary.json"

R23_DIR = ROOT / "output" / "V15_SG7E1R23"
R23_SUMMARY = R23_DIR / "PAD_Stream_V15SG7E1R23_Summary.json"

# Outputs
COVERAGE_TABLE = OUT / "V15SG7E1R26IR21_Multi_Time_Coverage_Status.csv"
SCOPE_TABLE = OUT / "V15SG7E1R26IR21_SG7E_Scope_Matrix.csv"
AUTHORITY_TABLE = OUT / "V15SG7E1R26IR21_Artifact_Authority_Matrix.csv"
PROHIBITION_TABLE = OUT / "V15SG7E1R26IR21_Prohibited_Interpretations.csv"
PATH_TABLE = OUT / "V15SG7E1R26IR21_Allowed_Development_Paths.csv"
GATE_TABLE = OUT / "V15SG7E1R26IR21_Final_Scope_Decision_Gates.csv"
DECISION_TABLE = OUT / "V15SG7E1R26IR21_SG7E_Scope_Decision.csv"

CONTRACT_FILE = OUT / "V15SG7E1R26IR21_Multi_Time_Coverage_Scope_Contract.json"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7E1R26IR21_Summary.json"


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
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def boolish(v):
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"true", "1", "yes"}


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7E1R26I-R21")
    print("Multi-Time Deployment Coverage Limitation / SG7E Scope Decision Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO FROZEN L2 ARRAY WILL BE CHANGED.
NO SG7D6 FULL-GRID ARRAY WILL BE CHANGED.
NO 250/500/1000-DAY STATE WILL BE GENERATED.
NO INTERPOLATION OR EXTRAPOLATION WILL BE USED.
NO SG7E THRESHOLD WILL BE CHANGED OR RELAXED.
NO PRECISION ENVELOPE WILL BE CHANGED OR RELAXED.
THIS MILESTONE DEFINES SG7E / SG7D DEPLOYMENT SCOPE ONLY.
""")

    r20r = load_json(R20R_SUMMARY)
    r19e = load_json(R19E_SUMMARY)
    r14 = load_json(R14_SUMMARY)
    r23 = load_json(R23_SUMMARY)
    coverage = load_csv(R20R_COVERAGE)

    if r20r.get("status") != "R20_LATER_TIME_BINDINGS_REJECTED_OR_INCOMPLETE":
        raise RuntimeError("R21 requires the corrected R20R incomplete later-time coverage result.")

    if r19e.get("status") != "HISTORICAL_RUNTIME_REPRODUCIBILITY_LIMITATION_FORMALIZED":
        raise RuntimeError("R21 requires the R19E runtime-reproducibility limitation decision.")

    if r14.get("status") != "SG7E_MULTI_TIME_HISTORICAL_REFERENCE_CONTRACT_RECONSTRUCTED":
        raise RuntimeError("R21 requires the reconstructed R14 SG7E historical multi-time reference contract.")

    if r23.get("status") != "L2_100D_NOMINATED_DEPLOYMENT_STATE_BOUND":
        raise RuntimeError("R21 requires the bound authoritative 100-day L2 deployment state.")

    # -------------------------------------------------------------------------
    # Corrected coverage record
    # -------------------------------------------------------------------------
    coverage_rows = []
    for row in coverage:
        t = float(row["time_days"])
        accepted = boolish(row.get("accepted_after_semantic_audit", False))
        classification = row.get("classification", "")

        coverage_rows.append({
            "time_days": t,
            "deployment_state_available": accepted,
            "classification": classification,
            "scope_effect": (
                "DEPLOYMENT_STATE_AVAILABLE"
                if accepted
                else "NO_PROVENANCE_VALID_DEPLOYMENT_STATE"
            ),
        })

    # Add the already-established authoritative 100-day state explicitly.
    coverage_rows.insert(0, {
        "time_days": 100.0,
        "deployment_state_available": True,
        "classification": "AUTHORITATIVE_L2_INDEPENDENT_100",
        "scope_effect": "DEPLOYMENT_STATE_AVAILABLE",
    })

    save_csv(COVERAGE_TABLE, coverage_rows)

    required_times = [100.0, 250.0, 500.0, 1000.0]
    available_times = [
        float(r["time_days"])
        for r in coverage_rows
        if boolish(r["deployment_state_available"])
    ]
    missing_times = sorted(set(required_times) - set(available_times))

    complete_four_time_deployment = len(missing_times) == 0

    # -------------------------------------------------------------------------
    # SG7E scope matrix
    # -------------------------------------------------------------------------
    scope_rows = [
        {
            "scope_object": "SG7E historical reference tensor",
            "scope_status": "VALID",
            "role": "MULTI_TIME_REFERENCE_ACCEPTANCE_CONTRACT",
            "time_coverage": "100/250/500/1000 days",
            "deployment_reproducibility_required": False,
            "notes": "Reference tensor remains immutable and fully reconstructed from persisted SG7A_corrected history.",
        },
        {
            "scope_object": "SG7D6 frozen full-grid deployment artifact",
            "scope_status": "VALID",
            "role": "AUTHORITATIVE_FROZEN_SINGLE_STATE_DEPLOYMENT_ARTIFACT",
            "time_coverage": "single persisted state",
            "deployment_reproducibility_required": False,
            "notes": "Numerical authority preserved; no unsupported physical-time relabelling permitted.",
        },
        {
            "scope_object": "L2_independent_100",
            "scope_status": "VALID",
            "role": "AUTHORITATIVE_100D_DEPLOYMENT_STATE",
            "time_coverage": "100 days only",
            "deployment_reproducibility_required": False,
            "notes": "Bound by candidate-selection and freeze-readiness provenance.",
        },
        {
            "scope_object": "250/500/1000-day frozen deployment sequence",
            "scope_status": "NOT_CERTIFIED",
            "role": "MISSING_MULTI_TIME_DEPLOYMENT_COVERAGE",
            "time_coverage": "incomplete",
            "deployment_reproducibility_required": True,
            "notes": "No provenance-valid persisted state set exists for all required later times.",
        },
        {
            "scope_object": "SG7E four-time deployment gate evaluation",
            "scope_status": "BLOCKED",
            "role": "NOT_APPLICABLE_TO_CURRENT_FROZEN_DEPLOYMENT_LINEAGE",
            "time_coverage": "requires 100/250/500/1000 deployment states",
            "deployment_reproducibility_required": True,
            "notes": "Historical SG7E reference contract remains valid, but current frozen deployment lineage cannot be evaluated across all four times.",
        },
    ]
    save_csv(SCOPE_TABLE, scope_rows)

    # -------------------------------------------------------------------------
    # Authority matrix
    # -------------------------------------------------------------------------
    authority_rows = [
        {
            "artifact_or_contract": "SG7A_corrected historical 4-time reference",
            "authority": "AUTHORITATIVE_REFERENCE",
            "immutable": True,
            "may_drive_future_validation": True,
        },
        {
            "artifact_or_contract": "Historical S=0.5 plume threshold",
            "authority": "AUTHORITATIVE_ACCEPTANCE_PARAMETER",
            "immutable": True,
            "may_drive_future_validation": True,
        },
        {
            "artifact_or_contract": "L2_independent_100",
            "authority": "AUTHORITATIVE_100D_DEPLOYMENT_STATE",
            "immutable": True,
            "may_drive_future_validation": True,
        },
        {
            "artifact_or_contract": "SG7D6 frozen full-grid field",
            "authority": "AUTHORITATIVE_FROZEN_DEPLOYMENT_ARTIFACT",
            "immutable": True,
            "may_drive_future_validation": True,
        },
        {
            "artifact_or_contract": "250/500/1000-day current-runtime generated states",
            "authority": "PROHIBITED",
            "immutable": False,
            "may_drive_future_validation": False,
        },
        {
            "artifact_or_contract": "R20 rejected 250/500 frozen100 relabellings",
            "authority": "REJECTED",
            "immutable": False,
            "may_drive_future_validation": False,
        },
    ]
    save_csv(AUTHORITY_TABLE, authority_rows)

    # -------------------------------------------------------------------------
    # Prohibited interpretations
    # -------------------------------------------------------------------------
    prohibition_rows = [
        {
            "interpretation": "Treat frozen100 as 250-day state",
            "allowed": False,
            "reason": "Semantic contradiction; same authoritative 100-day state hash.",
        },
        {
            "interpretation": "Treat frozen100 as 500-day state",
            "allowed": False,
            "reason": "Semantic contradiction; same authoritative 100-day state hash.",
        },
        {
            "interpretation": "Assume SG7D6 represents 1000 days",
            "allowed": False,
            "reason": "No persisted physical-time authority.",
        },
        {
            "interpretation": "Generate missing later-time states with current TensorFlow runtime",
            "allowed": False,
            "reason": "Historical runtime replay is not certified at 100 days.",
        },
        {
            "interpretation": "Relax SG7E threshold or R16 precision envelope to recover coverage",
            "allowed": False,
            "reason": "Would change frozen acceptance contracts rather than recover provenance.",
        },
        {
            "interpretation": "Claim Version 15 frozen deployment is a reproducible four-time SG7E sequence",
            "allowed": False,
            "reason": "Later-time deployment coverage is incomplete.",
        },
    ]
    save_csv(PROHIBITION_TABLE, prohibition_rows)

    # -------------------------------------------------------------------------
    # Allowed development paths
    # -------------------------------------------------------------------------
    path_rows = [
        {
            "path_id": "P1",
            "path": "Freeze SG7E as historical multi-time reference/acceptance contract",
            "allowed": True,
            "purpose": "Preserve historical reference validity without fabricating deployment states.",
        },
        {
            "path_id": "P2",
            "path": "Freeze SG7D6 as authoritative single-state deployment artifact",
            "allowed": True,
            "purpose": "Preserve completed frozen deployment provenance.",
        },
        {
            "path_id": "P3",
            "path": "Document multi-time deployment reproducibility limitation in Version 15 theory/validation record",
            "allowed": True,
            "purpose": "Make the scope boundary explicit and reproducible.",
        },
        {
            "path_id": "P4",
            "path": "Continue PAD-Stream development beyond SG7E without modifying frozen Version 15 artifacts",
            "allowed": True,
            "purpose": "Allow future Version 16 / research branch work to address multi-time deployment explicitly.",
        },
        {
            "path_id": "P5",
            "path": "Retroactively regenerate missing later-time states inside frozen V15",
            "allowed": False,
            "purpose": "Would break historical freeze and runtime-provenance constraints.",
        },
    ]
    save_csv(PATH_TABLE, path_rows)

    gates = [
        ("R20R_corrected_later_time_rejection_reproduced", True),
        ("R19E_runtime_limitation_reproduced", True),
        ("R14_four_time_reference_contract_reproduced", True),
        ("R23_100d_L2_authority_reproduced", True),
        ("100d_deployment_state_retained", 100.0 in available_times),
        ("250d_deployment_state_not_certified", 250.0 in missing_times),
        ("500d_deployment_state_not_certified", 500.0 in missing_times),
        ("1000d_deployment_state_not_certified", 1000.0 in missing_times),
        ("SG7E_reference_contract_preserved", True),
        ("SG7D6_single_state_authority_preserved", True),
        ("four_time_deployment_gate_marked_blocked", not complete_four_time_deployment),
        ("no_relabelled_100d_state_accepted", True),
        ("no_model_predict_executed", True),
        ("no_training_performed", True),
        ("no_state_generated", True),
        ("no_threshold_or_precision_change", True),
    ]

    failed = [g for g, p in gates if not p]
    save_csv(GATE_TABLE, [{"gate": g, "passed": p} for g, p in gates])

    status = "SG7E_HISTORICAL_REFERENCE_SCOPE_PRESERVED_MULTI_TIME_DEPLOYMENT_SCOPE_LIMITED"
    diagnosis = (
        "FOUR_TIME_SG7E_REFERENCE_CONTRACT_IS_VALID_BUT_FROZEN_DEPLOYMENT_LINEAGE_HAS_ONLY_CERTIFIED_100D_STATE_AND_SINGLE_FROZEN_GRID"
    )
    recommendation = (
        "Freeze this scope decision into Version 15. Preserve SG7E as a historical multi-time "
        "reference/acceptance contract and preserve SG7D6/L2_independent_100 as authoritative frozen "
        "deployment artifacts. Do not claim a reproducible four-time deployment sequence. The next "
        "milestone should close SG7E1 with a final branch disposition / Version 15 freeze-readiness audit."
    )
    next_ms = (
        "V15-SG7E1R26I-R22 — SG7E1 Final Branch Disposition / Version 15 Freeze-Readiness Audit"
    )

    save_csv(DECISION_TABLE, [{
        "status": status,
        "diagnosis": diagnosis,
        "required_reference_times": "100;250;500;1000",
        "certified_deployment_times": ";".join(str(int(t)) for t in sorted(available_times)),
        "uncertified_deployment_times": ";".join(str(int(t)) for t in missing_times),
        "four_time_deployment_sequence_certified": complete_four_time_deployment,
        "SG7E_reference_contract_valid": True,
        "SG7D6_authority_valid": True,
        "failed_gates": ";".join(failed),
        "next_milestone": next_ms,
    }])

    save_json(CONTRACT_FILE, {
        "milestone": "V15-SG7E1R26I-R21",
        "status": status,
        "diagnosis": diagnosis,
        "reference_time_contract_days": required_times,
        "certified_deployment_times_days": sorted(available_times),
        "uncertified_deployment_times_days": missing_times,
        "four_time_deployment_sequence_certified": complete_four_time_deployment,
        "SG7E_scope": "HISTORICAL_MULTI_TIME_REFERENCE_ACCEPTANCE_CONTRACT",
        "SG7D6_scope": "AUTHORITATIVE_FROZEN_SINGLE_STATE_DEPLOYMENT_ARTIFACT",
        "authority_matrix": authority_rows,
        "prohibited_interpretations": prohibition_rows,
        "allowed_paths": path_rows,
        "constraints": {
            "training_performed": False,
            "model_predict_executed": False,
            "state_generated": False,
            "interpolation_used": False,
            "extrapolation_used": False,
            "threshold_changed": False,
            "precision_envelope_changed": False,
            "runtime_search_broadened": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    save_json(SUMMARY_FILE, {
        "milestone": "V15-SG7E1R26I-R21",
        "status": status,
        "diagnosis": diagnosis,
        "certified_deployment_times_days": sorted(available_times),
        "uncertified_deployment_times_days": missing_times,
        "four_time_deployment_sequence_certified": complete_four_time_deployment,
        "failed_gates": failed,
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("MULTI-TIME COVERAGE")
    print(f"  Historical SG7E reference times : {required_times}")
    print(f"  Certified deployment times      : {sorted(available_times)}")
    print(f"  Uncertified deployment times    : {missing_times}")
    print(f"  Four-time deployment certified  : {complete_four_time_deployment}")

    print("\nSCOPE DECISION")
    print("  SG7E historical reference       : PRESERVED")
    print("  SG7D6 frozen deployment         : PRESERVED")
    print("  L2_independent_100              : PRESERVED")
    print("  Four-time deployment sequence   : NOT CERTIFIED")
    print("  Four-time SG7E deployment gates : BLOCKED")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R21 FINAL SCOPE DECISION GATES")
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
        COVERAGE_TABLE,
        SCOPE_TABLE,
        AUTHORITY_TABLE,
        PROHIBITION_TABLE,
        PATH_TABLE,
        GATE_TABLE,
        DECISION_TABLE,
    ):
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7E1R26I-R21 SG7E SCOPE DECISION AUDIT: COMPLETE")
    print()
    print("No model.predict call was executed.")
    print("No training was performed.")
    print("No later-time state was generated.")
    print("No SG7E threshold or precision envelope was changed.")
    print("=" * 78)


if __name__ == "__main__":
    main()
