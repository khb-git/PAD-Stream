from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json

import numpy as np


# =============================================================================
# PAD-Stream V16B-9
# FMM / Directional Travel-Time Architecture Role Decision
#
# PURPOSE
# -------
# V16B-8 completed the raw three-way comparison:
#
#   isotropic FMM
#   directional advective travel time
#   Pollock TOF
#
# V16B-9 does NOT solve new physics.
#
# It freezes the architectural role of each travel-time representation inside
# post-V15 PAD-Stream based on the V16B-8 evidence.
#
# EVIDENCE FROM V16B-8
# ---------------------
# All-node:
#   FMM r  = 0.731192
#   ADV r  = 0.921879
#   FMM MAE = 107.587349 d
#   ADV MAE =  66.742762 d
#
# Terminal:
#   FMM r  = 0.203891
#   ADV r  = 0.392841
#   FMM MAE = 285.550305 d
#   ADV MAE = 257.306154 d
#
# Monotonicity:
#   FMM monotonic fraction = 0.238404
#   ADV monotonic fraction = 0.383117
#   FMM negative-step frac = 0.126090
#   ADV negative-step frac = 0.034763
#
# IMPORTANT INTERPRETATION
# ------------------------
# ADV substantially improves consistency with Pollock, but does NOT replace
# Pollock as the exact characteristic/streamline reference.
#
# Therefore the architecture separates three roles:
#
#   FMM     -> rapid scalar connectivity / lower-bound arrival-time control
#   ADV     -> Eulerian directional travel-time field
#   Pollock -> exact trajectory-level transport coordinate / reference
#
# V16B-9 freezes this role separation without recalibration.
# =============================================================================


ROOT = Path(__file__).resolve().parent

B8_DIR = ROOT / "output" / "V16_B8_INDEPENDENT_DIRECTIONAL_FMM_POLLOCK_COMPARISON"
B8_SUMMARY = B8_DIR / "PAD_Stream_V16B8_Summary.json"
B8_CONTRACT = B8_DIR / "V16B8_Three_Way_Comparison_Contract.json"
B8_NPZ = B8_DIR / "V16B8_Directional_FMM_Pollock_Comparison.npz"

B7_DIR = ROOT / "output" / "V16_B7_CONTROLLED_DIRECTIONAL_ADVECTIVE_TRAVEL_TIME_SOLVE"
B7_CONTRACT = B7_DIR / "V16B7_Directional_Advective_Travel_Time_Contract.json"

B2_DIR = ROOT / "output" / "V16_B2_EXACT_3D_FMM_ARRIVAL_TIME_BASELINE"
B2_CONTRACT = B2_DIR / "V16B2_Exact_3D_FMM_Arrival_Time_Contract.json"

FOUNDATION_DIR = (
    ROOT
    / "output"
    / "V16_A_R8R_FOUNDATION_CASE_0001_FREEZE"
    / "PAD_Stream_V16A_Foundation_Case_0001"
)
FOUNDATION_NPZ = FOUNDATION_DIR / "V16A_Foundation_Case_0001.npz"

OUT = ROOT / "output" / "V16_B9_TRAVEL_TIME_ARCHITECTURE_ROLE_DECISION"
OUT.mkdir(parents=True, exist_ok=True)

IDENTITY_CSV = OUT / "V16B9_Input_Identity.csv"
EVIDENCE_CSV = OUT / "V16B9_Three_Way_Evidence_Summary.csv"
ROLE_CSV = OUT / "V16B9_Travel_Time_Method_Role_Matrix.csv"
FLOW_CSV = OUT / "V16B9_PAD_Stream_Travel_Time_Architecture_Flow.csv"
LIMIT_CSV = OUT / "V16B9_Method_Limitations_and_Prohibited_Claims.csv"
NEXT_CSV = OUT / "V16B9_Post_V16B_Development_Handoff.csv"
GATES_CSV = OUT / "V16B9_Final_Architecture_Decision_Gates.csv"
DECISION_CSV = OUT / "V16B9_Architecture_Role_Decision.csv"

CONTRACT_JSON = OUT / "V16B9_Travel_Time_Architecture_Role_Contract.json"
SUMMARY_JSON = OUT / "PAD_Stream_V16B9_Summary.json"


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


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16B-9")
    print("FMM / Directional Travel-Time Architecture Role Decision")
    print("=" * 78)

    print("""
NO NEW PHYSICS WILL BE SOLVED.
NO FMM FIELD WILL BE CHANGED.
NO DIRECTIONAL ADVECTIVE FIELD WILL BE CHANGED.
NO POLLOCK STREAMLINE WILL BE RETRACED.
NO FIELD WILL BE RECALIBRATED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO TRAINING WILL BE PERFORMED.
THIS MILESTONE FREEZES METHOD ROLES IN THE PAD-STREAM ARCHITECTURE ONLY.
""")

    for p in [
        B8_SUMMARY,
        B8_CONTRACT,
        B8_NPZ,
        B7_CONTRACT,
        B2_CONTRACT,
        FOUNDATION_NPZ,
    ]:
        if not p.exists():
            raise FileNotFoundError(p)

    b8 = load_json(B8_SUMMARY)

    if b8.get("status") != "V16B_INDEPENDENT_DIRECTIONAL_FMM_POLLOCK_COMPARISON_COMPLETE":
        raise RuntimeError("V16B-9 requires completed V16B-8.")

    save_csv(
        IDENTITY_CSV,
        [{
            "foundation_sha256": sha256_file(FOUNDATION_NPZ),
            "V16B2_contract_sha256": sha256_file(B2_CONTRACT),
            "V16B7_contract_sha256": sha256_file(B7_CONTRACT),
            "V16B8_contract_sha256": sha256_file(B8_CONTRACT),
            "V16B8_numerical_sha256": sha256_file(B8_NPZ),
        }],
    )

    evidence_rows = [
        {
            "metric": "all_node_pearson_r",
            "FMM": b8["FMM_all_node_r"],
            "ADV": b8["ADV_all_node_r"],
            "ADV_minus_FMM": b8["ADV_all_node_r"] - b8["FMM_all_node_r"],
        },
        {
            "metric": "all_node_MAE_days",
            "FMM": b8["FMM_all_node_MAE_days"],
            "ADV": b8["ADV_all_node_MAE_days"],
            "ADV_minus_FMM": b8["ADV_all_node_MAE_days"] - b8["FMM_all_node_MAE_days"],
        },
        {
            "metric": "terminal_pearson_r",
            "FMM": b8["FMM_terminal_r"],
            "ADV": b8["ADV_terminal_r"],
            "ADV_minus_FMM": b8["ADV_terminal_r"] - b8["FMM_terminal_r"],
        },
        {
            "metric": "terminal_MAE_days",
            "FMM": b8["FMM_terminal_MAE_days"],
            "ADV": b8["ADV_terminal_MAE_days"],
            "ADV_minus_FMM": b8["ADV_terminal_MAE_days"] - b8["FMM_terminal_MAE_days"],
        },
        {
            "metric": "median_terminal_ratio_to_Pollock",
            "FMM": b8["median_terminal_FMM_to_Pollock_ratio"],
            "ADV": b8["median_terminal_ADV_to_Pollock_ratio"],
            "ADV_minus_FMM": (
                b8["median_terminal_ADV_to_Pollock_ratio"]
                - b8["median_terminal_FMM_to_Pollock_ratio"]
            ),
        },
    ]
    save_csv(EVIDENCE_CSV, evidence_rows)

    role_rows = [
        {
            "method": "ISOTROPIC_FMM",
            "equation": "|grad(T_FMM)| = 1/|v|",
            "primary_role": "RAPID_SCALAR_CONNECTIVITY_AND_ARRIVAL_TIME_CONTROL",
            "secondary_role": "LOW_COST_GRID_LEVEL_SCREENING",
            "reference_status": "CONTROL_BASELINE",
            "transport_directionality": "NO",
            "retained": True,
        },
        {
            "method": "DIRECTIONAL_ADVECTIVE_TRAVEL_TIME",
            "equation": "v dot grad(tau_ADV) = 1",
            "primary_role": "EULERIAN_DIRECTIONAL_TRAVEL_TIME_FIELD",
            "secondary_role": "GRID_LEVEL_DIRECTIONAL_CONNECTIVITY_AND_TIME_COORDINATE",
            "reference_status": "DIRECTIONAL_GRID_BASELINE",
            "transport_directionality": "YES",
            "retained": True,
        },
        {
            "method": "POLLOCK",
            "equation": "dx/dt = v(x)",
            "primary_role": "EXACT_TRAJECTORY_LEVEL_TRANSPORT_COORDINATE",
            "secondary_role": "REFERENCE_FOR_STREAMLINE_TOF_AND_PATH_GEOMETRY",
            "reference_status": "AUTHORITATIVE_CHARACTERISTIC_REFERENCE",
            "transport_directionality": "YES",
            "retained": True,
        },
    ]
    save_csv(ROLE_CSV, role_rows)

    flow_rows = [
        {
            "stage": 1,
            "component": "Foundation Case 0001",
            "input": "K, phi, pressure, Q, V",
            "output": "frozen post-V15 flow foundation",
        },
        {
            "stage": 2,
            "component": "Isotropic FMM",
            "input": "|V|",
            "output": "rapid scalar arrival-time / connectivity field",
        },
        {
            "stage": 3,
            "component": "Directional Advective PDE",
            "input": "V vector field",
            "output": "Eulerian directional travel-time field",
        },
        {
            "stage": 4,
            "component": "Pollock",
            "input": "V vector field + exact cellwise tracing",
            "output": "trajectory-level streamline geometry and TOF",
        },
        {
            "stage": 5,
            "component": "Transport / PI-RNN downstream use",
            "input": "selected grid or streamline transport coordinate",
            "output": "future post-V16 transport coupling",
        },
    ]
    save_csv(FLOW_CSV, flow_rows)

    limitation_rows = [
        {
            "method": "ISOTROPIC_FMM",
            "limitation": "removes velocity orientation and permits shortcut propagation",
            "prohibited_claim": "equivalent to Pollock TOF",
        },
        {
            "method": "DIRECTIONAL_ADVECTIVE_TRAVEL_TIME",
            "limitation": "Eulerian first-order upwind field is not identical to exact Pollock characteristic integration",
            "prohibited_claim": "exact replacement for Pollock",
        },
        {
            "method": "POLLOCK",
            "limitation": "trajectory-level and more expensive / geometry-dependent than grid scalar fields",
            "prohibited_claim": "unnecessary once ADV is available",
        },
        {
            "method": "ALL",
            "limitation": "V16B comparisons are untuned baseline evidence",
            "prohibited_claim": "cross-calibrated equivalence",
        },
    ]
    save_csv(LIMIT_CSV, limitation_rows)

    handoff_rows = [
        {
            "priority": 1,
            "next_branch": "V16C",
            "development_goal": "formal integration of FMM/ADV/Pollock travel-time hierarchy into PAD-Stream transport architecture",
            "allowed": True,
        },
        {
            "priority": 2,
            "next_branch": "V16C",
            "development_goal": "define when downstream transport uses grid-level ADV versus streamline-level Pollock TOF",
            "allowed": True,
        },
        {
            "priority": 3,
            "next_branch": "POST_V16_OPTIONAL",
            "development_goal": "tensor/Riemannian anisotropic front propagation research branch",
            "allowed": True,
        },
        {
            "priority": 4,
            "next_branch": "PROHIBITED",
            "development_goal": "tune isotropic FMM until it numerically matches Pollock",
            "allowed": False,
        },
    ]
    save_csv(NEXT_CSV, handoff_rows)

    adv_better_all_node_r = b8["ADV_all_node_r"] > b8["FMM_all_node_r"]
    adv_better_all_node_mae = b8["ADV_all_node_MAE_days"] < b8["FMM_all_node_MAE_days"]
    adv_better_terminal_r = b8["ADV_terminal_r"] > b8["FMM_terminal_r"]
    adv_better_terminal_mae = b8["ADV_terminal_MAE_days"] < b8["FMM_terminal_MAE_days"]

    gates = [
        ("V16B8_status_reproduced", True),
        ("three_way_evidence_registered", True),
        ("ADV_improves_all_node_correlation", adv_better_all_node_r),
        ("ADV_reduces_all_node_MAE", adv_better_all_node_mae),
        ("ADV_improves_terminal_correlation", adv_better_terminal_r),
        ("ADV_reduces_terminal_MAE", adv_better_terminal_mae),
        ("FMM_retained_as_isotropic_control", True),
        ("ADV_retained_as_directional_grid_baseline", True),
        ("Pollock_retained_as_characteristic_reference", True),
        ("ADV_not_promoted_to_exact_Pollock_replacement", True),
        ("FMM_not_discarded", True),
        ("no_cross_calibration_authorized", True),
        ("no_new_physics_solved", True),
        ("no_FMM_change", True),
        ("no_ADV_change", True),
        ("no_Pollock_retrace", True),
        ("no_model_predict", True),
        ("no_training", True),
    ]
    save_csv(GATES_CSV, [{"gate": g, "passed": bool(p)} for g, p in gates])

    all_pass = all(bool(p) for _, p in gates)

    if all_pass:
        status = "V16B_TRAVEL_TIME_ARCHITECTURE_ROLES_FROZEN"
        diagnosis = (
            "FMM_ADV_AND_POLLOCK_PROVIDE_DISTINCT_COMPLEMENTARY_LEVELS_OF_CONNECTIVITY_AND_TRAVEL_TIME_INFORMATION"
        )
        recommendation = (
            "Close V16B with all three methods preserved. Use FMM for rapid scalar connectivity screening, "
            "ADV for directional Eulerian travel time, and Pollock for exact trajectory-level TOF. "
            "Proceed to V16C to integrate this hierarchy into the downstream PAD-Stream transport architecture."
        )
        next_ms = "V16C — Travel-Time Hierarchy Integration into PAD-Stream Transport"
    else:
        status = "V16B_ARCHITECTURE_ROLE_DECISION_REQUIRES_AUDIT"
        diagnosis = "ONE_OR_MORE_ROLE_DECISION_EVIDENCE_GATES_FAILED"
        recommendation = "Audit only failed V16B-9 role-decision gates."
        next_ms = "V16B-9R — Architecture Role Decision Residual Audit"

    save_csv(
        DECISION_CSV,
        [{
            "status": status,
            "diagnosis": diagnosis,
            "FMM_role": "RAPID_SCALAR_CONNECTIVITY_CONTROL",
            "ADV_role": "DIRECTIONAL_EULERIAN_TRAVEL_TIME",
            "Pollock_role": "AUTHORITATIVE_TRAJECTORY_TOF_REFERENCE",
            "next_milestone": next_ms,
        }],
    )

    contract = {
        "milestone": "V16B-9",
        "status": status,
        "diagnosis": diagnosis,
        "role_registry": {
            "FMM": "rapid scalar connectivity / arrival-time control",
            "ADV": "directional Eulerian travel-time field",
            "Pollock": "authoritative trajectory-level TOF reference",
        },
        "prohibited_interpretations": [
            "FMM equivalent to Pollock",
            "ADV exact replacement for Pollock",
            "Pollock unnecessary after ADV",
            "cross-calibrated equivalence",
        ],
        "architecture_principle": (
            "retain multiple travel-time representations because they encode different levels of directional information"
        ),
        "recommendation": recommendation,
        "next_milestone": next_ms,
    }
    save_json(CONTRACT_JSON, contract)

    save_json(
        SUMMARY_JSON,
        {
            "milestone": "V16B-9",
            "status": status,
            "diagnosis": diagnosis,
            "FMM_role": "RAPID_SCALAR_CONNECTIVITY_CONTROL",
            "ADV_role": "DIRECTIONAL_EULERIAN_TRAVEL_TIME",
            "Pollock_role": "AUTHORITATIVE_TRAJECTORY_TOF_REFERENCE",
            "recommendation": recommendation,
            "next_milestone": next_ms,
        },
    )

    print("V16B-8 EVIDENCE")
    print(f"  FMM all-node r          : {b8['FMM_all_node_r']:.6f}")
    print(f"  ADV all-node r          : {b8['ADV_all_node_r']:.6f}")
    print(f"  FMM all-node MAE        : {b8['FMM_all_node_MAE_days']:.6f} days")
    print(f"  ADV all-node MAE        : {b8['ADV_all_node_MAE_days']:.6f} days")
    print(f"  FMM terminal r          : {b8['FMM_terminal_r']:.6f}")
    print(f"  ADV terminal r          : {b8['ADV_terminal_r']:.6f}")

    print("\nFROZEN ARCHITECTURE ROLES")
    print("  FMM                     : RAPID_SCALAR_CONNECTIVITY_CONTROL")
    print("  ADV                     : DIRECTIONAL_EULERIAN_TRAVEL_TIME")
    print("  POLLOCK                 : AUTHORITATIVE_TRAJECTORY_TOF_REFERENCE")

    print("\n" + "=" * 78)
    print("V16B-9 FINAL ARCHITECTURE DECISION GATES")
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
    for p in [
        IDENTITY_CSV,
        EVIDENCE_CSV,
        ROLE_CSV,
        FLOW_CSV,
        LIMIT_CSV,
        NEXT_CSV,
        GATES_CSV,
        DECISION_CSV,
    ]:
        print(f"  {p.name}")
    print("\nContract:")
    print(f"  {CONTRACT_JSON.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_JSON.name}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16B-9 TRAVEL-TIME ARCHITECTURE ROLE DECISION: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()
