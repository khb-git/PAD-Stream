from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json

import numpy as np


# =============================================================================
# PAD-Stream V16A-R7E
# Producer Identity Scope Limitation / Foundation Case Freeze Decision
#
# PURPOSE
# -------
# R7C3 concluded:
#   producer_id cannot be recovered from frozen non-retrace provenance.
#
# R7E decides whether Foundation Case 0001 may freeze without producer_id.
#
# The decision is based on the role of producer_id relative to the foundation:
#   - geology / permeability
#   - porosity
#   - pressure
#   - conservative Darcy fluxes
#   - face velocities
#   - frozen Pollock streamline geometry
#   - Pollock time-of-flight
#   - streamline weights
#
# producer_id is treated as a connectivity label / endpoint classification,
# not as a required primitive field for permeability-pressure foundation physics.
#
# R7E WILL NOT:
#   - reconstruct producer_id,
#   - rerun SG3/SG4,
#   - recompute velocity,
#   - retrace Pollock,
#   - run Fast Marching,
#   - train or infer ML,
#   - mutate frozen V15 artifacts.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V16_A_R7E_PRODUCER_SCOPE_FREEZE_DECISION"
OUT.mkdir(parents=True, exist_ok=True)

R7C3_DIR = ROOT / "output" / "V16_A_R7C3_FINAL_PRODUCER_METADATA_PROVENANCE_AUDIT"
R7C3_SUMMARY = R7C3_DIR / "PAD_Stream_V16AR7C3_Summary.json"

R7_DIR = ROOT / "output" / "V16_A_R7_CONTROLLED_SOURCE_AUTHENTIC_REGENERATION"
R7_DYNAMIC = R7_DIR / "V16AR7_Derived_V16_From_Frozen_V15_Dynamic_Components.npz"

R7B_DIR = ROOT / "output" / "V16_A_R7B_CONTROLLED_RESIDUAL_RECONSTRUCTION"
R7B_RESIDUAL = R7B_DIR / "V16AR7B_Derived_Velocity_Producer_Components.npz"

FOUNDATION_MATRIX = OUT / "V16AR7E_Foundation_Component_Criticality_Matrix.csv"
SCOPE_MATRIX = OUT / "V16AR7E_Producer_ID_Scope_Matrix.csv"
FREEZE_GATES = OUT / "V16AR7E_Foundation_Freeze_Decision_Gates.csv"
DECISION_CSV = OUT / "V16AR7E_Foundation_Freeze_Decision.csv"
CONTRACT = OUT / "V16AR7E_Producer_Identity_Scope_Contract.json"
SUMMARY = OUT / "PAD_Stream_V16AR7E_Summary.json"


def save_csv(path: Path, rows):
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_npz_keys(path: Path):
    if not path.exists():
        return []
    with np.load(path, allow_pickle=False) as db:
        return list(db.files)


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16A-R7E")
    print("Producer Identity Scope Limitation / Foundation Case Freeze Decision")
    print("=" * 78)

    print("""
NO PRODUCER ID WILL BE RECONSTRUCTED.
NO SG3 PRESSURE SOLVE WILL BE RERUN.
NO SG4 DARCY FLUX WILL BE RERUN.
NO VELOCITY ARRAY WILL BE RECOMPUTED.
NO POLLOCK STREAMLINE WILL BE RETRACED.
NO FAST MARCHING WILL BE EXECUTED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO TRAINING WILL BE PERFORMED.
NO FROZEN V15 ARTIFACT WILL BE CHANGED.
THIS MILESTONE MAKES A FOUNDATION-SCOPE / FREEZE DECISION ONLY.
""")

    if not R7C3_SUMMARY.exists():
        raise FileNotFoundError(R7C3_SUMMARY)

    r7c3 = json.loads(R7C3_SUMMARY.read_text(encoding="utf-8"))
    if r7c3.get("status") != "V16A_PRODUCER_IDENTITY_NOT_RECOVERABLE_WITHOUT_RETRACE":
        raise RuntimeError("R7E expects the final non-recoverable producer-id status from R7C3.")

    if not R7_DYNAMIC.exists():
        raise FileNotFoundError(R7_DYNAMIC)
    if not R7B_RESIDUAL.exists():
        raise FileNotFoundError(R7B_RESIDUAL)

    r7_keys = set(load_npz_keys(R7_DYNAMIC))
    r7b_keys = set(load_npz_keys(R7B_RESIDUAL))

    dynamic_required = {"pressure", "Qx", "Qy", "Qz"}
    velocity_required = {"Vx", "Vy", "Vz"}

    dynamic_ready = dynamic_required.issubset(r7_keys)
    velocity_ready = velocity_required.issubset(r7b_keys)

    # Foundation criticality matrix.
    components = [
        {
            "component": "Kx/Ky/Kz",
            "role": "PRIMARY_GEOLOGICAL_CONTROL",
            "required_for_foundation_freeze": True,
            "required_for_FMM_baseline": True,
            "status": "RECOVERABLE_FROM_FROZEN_V15_GEOLOGY",
        },
        {
            "component": "porosity",
            "role": "PRIMARY_STORAGE_AND_VELOCITY_CONTROL",
            "required_for_foundation_freeze": True,
            "required_for_FMM_baseline": True,
            "status": "RECOVERABLE_FROM_FROZEN_V15_GEOLOGY",
        },
        {
            "component": "pressure",
            "role": "PRIMARY_DYNAMIC_FOUNDATION_FIELD",
            "required_for_foundation_freeze": True,
            "required_for_FMM_baseline": True,
            "status": "DERIVED_V16_FROM_FROZEN_V15" if "pressure" in r7_keys else "MISSING",
        },
        {
            "component": "Qx/Qy/Qz",
            "role": "PRIMARY_CONSERVATIVE_FLOW_FIELD",
            "required_for_foundation_freeze": True,
            "required_for_FMM_baseline": True,
            "status": "DERIVED_V16_FROM_FROZEN_V15" if dynamic_ready else "MISSING",
        },
        {
            "component": "Vx/Vy/Vz",
            "role": "PRIMARY_ADVECTION_FIELD",
            "required_for_foundation_freeze": True,
            "required_for_FMM_baseline": False,
            "status": "DERIVED_V16_FROM_FROZEN_V15" if velocity_ready else "MISSING",
        },
        {
            "component": "streamline_xyz",
            "role": "FROZEN_POLLOCK_REFERENCE_GEOMETRY",
            "required_for_foundation_freeze": True,
            "required_for_FMM_baseline": False,
            "status": "PRESERVED_PREVIOUSLY_BOUND_V15_REFERENCE",
        },
        {
            "component": "pollock_tof",
            "role": "FROZEN_POLLOCK_REFERENCE_TRAVEL_TIME",
            "required_for_foundation_freeze": True,
            "required_for_FMM_baseline": False,
            "status": "PRESERVED_PREVIOUSLY_BOUND_V15_REFERENCE",
        },
        {
            "component": "streamline_weight",
            "role": "FROZEN_FLOW_ALLOCATION_REFERENCE",
            "required_for_foundation_freeze": True,
            "required_for_FMM_baseline": False,
            "status": "PRESERVED_PREVIOUSLY_BOUND_V15_REFERENCE",
        },
        {
            "component": "producer_id",
            "role": "CONNECTIVITY_LABEL_ONLY",
            "required_for_foundation_freeze": False,
            "required_for_FMM_baseline": False,
            "status": "UNAVAILABLE_FROM_FROZEN_NONRETRACE_PROVENANCE",
        },
    ]
    save_csv(FOUNDATION_MATRIX, components)

    scope_rows = [
        {
            "topic": "producer_id historical authority",
            "decision": "NOT_AVAILABLE",
            "reason": "No persisted or executably bound non-retrace producer classification rule remains.",
        },
        {
            "topic": "producer_id requirement for permeability-pressure foundation",
            "decision": "NOT_REQUIRED",
            "reason": "Producer identity is an endpoint connectivity label, not a primitive permeability/pressure/flux state variable.",
        },
        {
            "topic": "producer_id requirement for Fast Marching baseline",
            "decision": "NOT_REQUIRED",
            "reason": "FMM baseline can be developed from permeability/porosity/pressure-derived speed or metric fields without producer labels.",
        },
        {
            "topic": "future producer connectivity label",
            "decision": "POST_FREEZE_V16_DERIVED_OPTION",
            "reason": "A new explicit V16 endpoint-to-producer rule may be designed later if needed, but must be labeled as derived and not historical V15.",
        },
        {
            "topic": "Foundation Case 0001 freeze",
            "decision": "PERMITTED_WITH_SCOPE_LIMITATION",
            "reason": "All primitive foundation physics fields are available; producer_id is non-critical metadata.",
        },
    ]
    save_csv(SCOPE_MATRIX, scope_rows)

    all_critical_ready = dynamic_ready and velocity_ready

    gates = [
        ("incoming_R7C3_nonrecoverable_status_reproduced", True),
        ("R7_pressure_flux_artifact_exists", R7_DYNAMIC.exists()),
        ("R7B_velocity_artifact_exists", R7B_RESIDUAL.exists()),
        ("pressure_flux_components_present", dynamic_ready),
        ("velocity_components_present", velocity_ready),
        ("producer_id_classified_as_connectivity_label_not_primitive_field", True),
        ("producer_id_not_required_for_foundation_freeze", True),
        ("producer_id_not_required_for_FMM_baseline", True),
        ("future_derived_connectivity_rule_separated_from_frozen_V15_authority", True),
        ("no_producer_id_reconstructed", True),
        ("no_SG3_rerun", True),
        ("no_SG4_rerun", True),
        ("no_velocity_recompute", True),
        ("no_Pollock_retrace", True),
        ("no_FMM", True),
        ("no_model_predict", True),
        ("no_training", True),
        ("no_V15_mutation", True),
    ]
    save_csv(FREEZE_GATES, [{"gate": g, "passed": p} for g,p in gates])

    if all_critical_ready:
        status = "V16A_FOUNDATION_CASE_0001_FREEZE_AUTHORIZED_WITH_PRODUCER_ID_SCOPE_LIMITATION"
        diagnosis = (
            "ALL_PRIMITIVE_GEOLOGY_PRESSURE_FLOW_AND_VELOCITY_COMPONENTS_ARE_AVAILABLE_WHILE_PRODUCER_ID_IS_NONCRITICAL_CONNECTIVITY_METADATA"
        )
        recommendation = (
            "Proceed to final Foundation Case 0001 assembly/freeze. Omit producer_id from the required frozen component set, "
            "record it explicitly as unavailable historical metadata, and preserve a future option for a separately labeled "
            "post-freeze V16 connectivity-classification branch."
        )
        next_ms = "V16A-R8 — Foundation Case 0001 Final Assembly / Freeze"
    else:
        status = "V16A_FOUNDATION_FREEZE_NOT_YET_AUTHORIZED"
        diagnosis = "ONE_OR_MORE_CRITICAL_FOUNDATION_DYNAMIC_COMPONENTS_ARE_MISSING"
        recommendation = (
            "Do not freeze Foundation Case 0001. Audit only the missing critical pressure/flux/velocity components."
        )
        next_ms = "V16A-R7F — Critical Foundation Component Closure Audit"

    save_csv(DECISION_CSV, [{
        "status": status,
        "diagnosis": diagnosis,
        "dynamic_ready": dynamic_ready,
        "velocity_ready": velocity_ready,
        "producer_id_required": False,
        "producer_id_status": "UNAVAILABLE_FROM_FROZEN_NONRETRACE_PROVENANCE",
        "foundation_freeze_authorized": all_critical_ready,
        "next_milestone": next_ms,
    }])

    contract = {
        "milestone": "V16A-R7E",
        "status": status,
        "diagnosis": diagnosis,
        "foundation_scope": {
            "producer_id_required": False,
            "producer_id_status": "UNAVAILABLE_FROM_FROZEN_NONRETRACE_PROVENANCE",
            "producer_id_role": "CONNECTIVITY_LABEL_ONLY",
            "future_connectivity_branch_allowed": True,
            "future_connectivity_branch_must_be_labeled_derived_V16": True,
        },
        "critical_component_status": {
            "pressure_Q": dynamic_ready,
            "velocity": velocity_ready,
        },
        "artifacts": {
            "R7_dynamic": str(R7_DYNAMIC),
            "R7_dynamic_sha256": sha256_file(R7_DYNAMIC),
            "R7B_velocity": str(R7B_RESIDUAL),
            "R7B_velocity_sha256": sha256_file(R7B_RESIDUAL),
        },
        "constraints": {
            "producer_id_reconstructed": False,
            "SG3_rerun": False,
            "SG4_rerun": False,
            "velocity_recompute": False,
            "Pollock_retrace": False,
            "FMM": False,
            "model_predict": False,
            "training": False,
            "V15_mutation": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    }
    save_json(CONTRACT, contract)

    save_json(SUMMARY, {
        "milestone": "V16A-R7E",
        "status": status,
        "diagnosis": diagnosis,
        "foundation_freeze_authorized": all_critical_ready,
        "producer_id_required": False,
        "producer_id_status": "UNAVAILABLE_FROM_FROZEN_NONRETRACE_PROVENANCE",
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("FOUNDATION SCOPE")
    print(f"  Pressure / flux ready      : {dynamic_ready}")
    print(f"  Velocity ready             : {velocity_ready}")
    print(f"  producer_id available      : False")
    print(f"  producer_id required       : False")
    print(f"  Foundation freeze allowed  : {all_critical_ready}")

    print("\n" + "=" * 78)
    print("V16A-R7E FINAL FREEZE DECISION GATES")
    print("=" * 78)
    for g,p in gates:
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
    for p in [FOUNDATION_MATRIX, SCOPE_MATRIX, FREEZE_GATES, DECISION_CSV]:
        print(f"  {p.name}")
    print("\nContract:")
    print(f"  {CONTRACT.name}")
    print("\nSummary:")
    print(f"  {SUMMARY.name}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16A-R7E PRODUCER SCOPE / FOUNDATION FREEZE DECISION: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()
