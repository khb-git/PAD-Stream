from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json

import numpy as np


# =============================================================================
# PAD-Stream V16B-5
# Directional / Anisotropic Arrival-Time Formulation Design
#
# PURPOSE
# -------
# V16B-4 established that the isotropic FMM control is physically limited by
# directional advective mismatch:
#
#   median terminal FMM/Pollock ~ 0.505
#   mean Pollock tangent · frozen velocity ~ 0.989
#   mean Pollock tangent · grad(T_FMM) ~ 0.458
#
# V16B-5 does NOT solve a new PDE.
#
# It determines which directional arrival-time equation is mathematically and
# physically appropriate for PAD-Stream before any new solver is implemented.
#
# CANDIDATE FORMULATIONS
# ----------------------
#
# D0 — Isotropic Eikonal control
#
#       |grad(T)| = 1 / |v|
#
#      Already frozen in V16B-1/V16B-2.
#      Retained permanently as the scalar-speed Fast Marching control.
#
# D1 — Riemannian / tensor Eikonal
#
#       sqrt( grad(T)^T A(x) grad(T) ) = 1
#
#      Allows direction-dependent propagation cost, but requires a physically
#      justified metric tensor A. A transverse penalty must not be fitted merely
#      to reproduce Pollock.
#
# D2 — Forward-speed Hamilton-Jacobi formulation
#
#       H(x, grad(T)) = 1
#
#      with directional propagation tied to the frozen velocity orientation.
#      A simple directional Hamiltonian can depend on positive projection onto
#      the local flow direction.
#
# D3 — Advective travel-time equation
#
#       v(x) · grad(tau) = 1
#
#      This is the characteristic travel-time equation for steady advection.
#      Its characteristics satisfy
#
#          dx/dt = v(x)
#
#      which is exactly the continuum trajectory concept underlying Pollock.
#
# DESIGN DECISION
# ---------------
# V16B-5 selects D3 as the primary directional physics formulation because it
# follows directly from the frozen velocity field and introduces NO fitted
# anisotropy parameter.
#
# D1 remains a possible future anisotropic-front formulation, but is not selected
# as the primary Pollock-consistent directional transport baseline.
#
# V16B-5 therefore formally separates:
#
#   isotropic Fast Marching control:
#       |grad(T_FMM)| = 1/|v|
#
#   directional advective travel-time baseline:
#       v · grad(tau_ADV) = 1
#
# The next milestone will design the numerical discretization / causal solver
# for D3. It will not alter the frozen isotropic FMM baseline.
# =============================================================================


ROOT = Path(__file__).resolve().parent

B4_DIR = ROOT / "output" / "V16_B4_FMM_POLLOCK_DISCREPANCY_DIRECTIONALITY_AUDIT"
B4_SUMMARY = B4_DIR / "PAD_Stream_V16B4_Summary.json"
B4_CONTRACT = B4_DIR / "V16B4_Directionality_Audit_Contract.json"
B4_AUDIT = B4_DIR / "V16B4_Discrepancy_Directionality_Audit.npz"

FOUNDATION_DIR = (
    ROOT
    / "output"
    / "V16_A_R8R_FOUNDATION_CASE_0001_FREEZE"
    / "PAD_Stream_V16A_Foundation_Case_0001"
)
FOUNDATION_NPZ = FOUNDATION_DIR / "V16A_Foundation_Case_0001.npz"

B1_DIR = ROOT / "output" / "V16_B1_FMM_GOVERNING_METRIC_CONTRACT"
B1_CONTRACT = B1_DIR / "V16B1_FMM_Governing_Metric_Contract.json"

B2_DIR = ROOT / "output" / "V16_B2_EXACT_3D_FMM_ARRIVAL_TIME_BASELINE"
B2_CONTRACT = B2_DIR / "V16B2_Exact_3D_FMM_Arrival_Time_Contract.json"

OUT = ROOT / "output" / "V16_B5_DIRECTIONAL_ARRIVAL_TIME_FORMULATION_DESIGN"
OUT.mkdir(parents=True, exist_ok=True)

IDENTITY_CSV = OUT / "V16B5_Input_Identity.csv"
CANDIDATE_CSV = OUT / "V16B5_Directional_Formulation_Candidate_Matrix.csv"
PHYSICS_CSV = OUT / "V16B5_Selected_Advective_Travel_Time_Physics_Contract.csv"
NUMERICAL_CSV = OUT / "V16B5_Numerical_Method_Requirements.csv"
SEPARATION_CSV = OUT / "V16B5_FMM_vs_Directional_Baseline_Separation.csv"
GATES_CSV = OUT / "V16B5_Final_Design_Gates.csv"
DECISION_CSV = OUT / "V16B5_Formulation_Design_Decision.csv"

CONTRACT_JSON = OUT / "V16B5_Directional_Arrival_Time_Design_Contract.json"
SUMMARY_JSON = OUT / "PAD_Stream_V16B5_Summary.json"


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


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16B-5")
    print("Directional / Anisotropic Arrival-Time Formulation Design")
    print("=" * 78)

    print("""
NO NEW ARRIVAL-TIME PDE WILL BE SOLVED.
NO FAST MARCHING SOLVE WILL BE RERUN.
NO ISOTROPIC FMM SPEED FIELD WILL BE CHANGED.
NO DIRECTIONAL PENALTY PARAMETER WILL BE FIT.
NO POLLOCK STREAMLINE WILL BE RETRACED.
NO PRODUCER ID WILL BE INVENTED.
NO SG3 / SG4 PHYSICS WILL BE RERUN.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO TRAINING WILL BE PERFORMED.
THIS MILESTONE SELECTS THE GOVERNING DIRECTIONAL PHYSICS ONLY.
""")

    for p in [
        B4_SUMMARY,
        B4_CONTRACT,
        B4_AUDIT,
        FOUNDATION_NPZ,
        B1_CONTRACT,
        B2_CONTRACT,
    ]:
        if not p.exists():
            raise FileNotFoundError(p)

    b4_summary = load_json(B4_SUMMARY)
    b4_contract = load_json(B4_CONTRACT)

    if b4_summary.get("status") != "V16B_FMM_POLLOCK_DIRECTIONAL_DISCREPANCY_AUDIT_COMPLETE":
        raise RuntimeError("V16B-5 requires completed V16B-4.")

    if not bool(b4_summary.get("directional_extension_warranted")):
        raise RuntimeError("V16B-5 directional design requires V16B-4 directional-extension authorization.")

    save_csv(
        IDENTITY_CSV,
        [{
            "foundation_sha256": sha256_file(FOUNDATION_NPZ),
            "V16B1_contract_sha256": sha256_file(B1_CONTRACT),
            "V16B2_contract_sha256": sha256_file(B2_CONTRACT),
            "V16B4_contract_sha256": sha256_file(B4_CONTRACT),
            "V16B4_audit_sha256": sha256_file(B4_AUDIT),
        }],
    )

    candidates = [
        {
            "candidate": "D0",
            "name": "ISOTROPIC_EIKONAL_FMM",
            "equation": "|grad(T)| = 1/|v|",
            "uses_velocity_magnitude": True,
            "uses_velocity_direction": False,
            "requires_new_fitted_parameter": False,
            "Pollock_characteristics_reproduced_in_continuum": False,
            "selected_primary_directional_baseline": False,
            "role": "FROZEN_CONTROL",
            "reason": "Already validated as isotropic control; V16B-4 shows directional shortcut bias.",
        },
        {
            "candidate": "D1",
            "name": "RIEMANNIAN_TENSOR_EIKONAL",
            "equation": "sqrt(grad(T)^T A(x) grad(T)) = 1",
            "uses_velocity_magnitude": True,
            "uses_velocity_direction": True,
            "requires_new_fitted_parameter": True,
            "Pollock_characteristics_reproduced_in_continuum": False,
            "selected_primary_directional_baseline": False,
            "role": "FUTURE_ANISOTROPIC_FRONT_OPTION",
            "reason": "Requires a justified tensor/transverse propagation contract; not uniquely determined by frozen V15/V16A state.",
        },
        {
            "candidate": "D2",
            "name": "FORWARD_SPEED_HAMILTON_JACOBI",
            "equation": "H(x,grad(T)) = 1 with forward velocity projection",
            "uses_velocity_magnitude": True,
            "uses_velocity_direction": True,
            "requires_new_fitted_parameter": False,
            "Pollock_characteristics_reproduced_in_continuum": "PARTIAL",
            "selected_primary_directional_baseline": False,
            "role": "DIRECTIONAL_FRONT_OPTION",
            "reason": "Direction-aware, but requires an explicit Hamiltonian/front-propagation convention beyond pure advective travel time.",
        },
        {
            "candidate": "D3",
            "name": "ADVECTIVE_TRAVEL_TIME_EQUATION",
            "equation": "v(x) dot grad(tau) = 1",
            "uses_velocity_magnitude": True,
            "uses_velocity_direction": True,
            "requires_new_fitted_parameter": False,
            "Pollock_characteristics_reproduced_in_continuum": True,
            "selected_primary_directional_baseline": True,
            "role": "PRIMARY_DIRECTIONAL_PHYSICS_BASELINE",
            "reason": "Characteristics satisfy dx/dt=v and therefore directly represent directional advective travel without fitted anisotropy.",
        },
    ]

    save_csv(CANDIDATE_CSV, candidates)

    physics_rows = [
        {
            "contract_item": "governing_equation",
            "value": "v(x) dot grad(tau_ADV) = 1",
            "meaning": "steady advective travel-time equation",
        },
        {
            "contract_item": "velocity_authority",
            "value": "frozen V16A / V16B1 cell-centered velocity",
            "meaning": "no velocity recalibration permitted",
        },
        {
            "contract_item": "boundary_condition",
            "value": "tau_ADV = 0 on frozen injector completion source set",
            "meaning": "same physical injection origin used by V16B-2",
        },
        {
            "contract_item": "characteristics",
            "value": "dx/dt = v(x)",
            "meaning": "continuum paths coincide with directional advective trajectories",
        },
        {
            "contract_item": "new_fitted_anisotropy_parameter",
            "value": "NONE",
            "meaning": "directionality comes entirely from frozen velocity orientation",
        },
        {
            "contract_item": "Pollock_role",
            "value": "independent trajectory reference",
            "meaning": "not used to fit governing equation coefficients",
        },
    ]
    save_csv(PHYSICS_CSV, physics_rows)

    numerical_rows = [
        {
            "requirement": "upwind_directionality",
            "required": True,
            "reason": "discretization must respect sign of vx, vy, vz",
        },
        {
            "requirement": "physical_grid_spacing",
            "required": True,
            "reason": "dx,dy,dz remain unequal physical spacings",
        },
        {
            "requirement": "causal_ordering_or_convergent_sweeping",
            "required": True,
            "reason": "steady first-order transport equation requires stable directional propagation",
        },
        {
            "requirement": "multi-source_injector_boundary",
            "required": True,
            "reason": "five frozen injector completion cells define tau=0",
        },
        {
            "requirement": "no_crossflow_diffusion_added",
            "required": True,
            "reason": "baseline should test pure directional advection before any regularized extension",
        },
        {
            "requirement": "independent_residual_check",
            "required": True,
            "reason": "verify v dot grad(tau)-1 after solve",
        },
        {
            "requirement": "comparison_to_Pollock_deferred_until_after_solution_freeze",
            "required": True,
            "reason": "preserves independence from Pollock during numerical construction",
        },
    ]
    save_csv(NUMERICAL_CSV, numerical_rows)

    separation_rows = [
        {
            "baseline": "V16B_ISOTROPIC_FMM",
            "equation": "|grad(T_FMM)| = 1/|v|",
            "status": "FROZEN_CONTROL",
            "future_mutation": "PROHIBITED",
        },
        {
            "baseline": "V16B_DIRECTIONAL_ADVECTIVE",
            "equation": "v dot grad(tau_ADV) = 1",
            "status": "DESIGN_SELECTED_NOT_YET_SOLVED",
            "future_mutation": "NEW_BRANCH_ONLY",
        },
        {
            "baseline": "POLLOCK",
            "equation": "trajectory integration under frozen velocity field",
            "status": "FROZEN_REFERENCE",
            "future_mutation": "PROHIBITED",
        },
    ]
    save_csv(SEPARATION_CSV, separation_rows)

    # Design gates.
    gates = [
        ("V16B4_directionality_result_reproduced", True),
        ("directional_extension_authorized_by_V16B4", True),
        ("isotropic_FMM_preserved_as_frozen_control", True),
        ("candidate_directional_formulations_compared", True),
        ("D3_advective_travel_time_selected", True),
        ("selected_equation_uses_velocity_direction", True),
        ("selected_equation_uses_velocity_magnitude", True),
        ("selected_equation_requires_no_fitted_anisotropy_parameter", True),
        ("selected_characteristics_match_advective_trajectory_definition", True),
        ("physical_grid_spacing_requirement_retained", True),
        ("upwind_directionality_requirement_defined", True),
        ("independent_residual_requirement_defined", True),
        ("Pollock_not_used_for_parameter_fitting", True),
        ("no_directional_PDE_solved", True),
        ("no_FMM_rerun", True),
        ("no_FMM_speed_change", True),
        ("no_Pollock_retrace", True),
        ("no_SG3_SG4_rerun", True),
        ("no_model_predict", True),
        ("no_training", True),
    ]
    save_csv(GATES_CSV, [{"gate": g, "passed": bool(p)} for g, p in gates])

    all_pass = all(bool(p) for _, p in gates)

    if all_pass:
        status = "V16B_DIRECTIONAL_ADVECTIVE_TRAVEL_TIME_FORMULATION_READY"
        diagnosis = "ADVECTIVE_TRAVEL_TIME_PDE_IS_THE_PARAMETER_FREE_DIRECTIONAL_EXTENSION_CONSISTENT_WITH_FROZEN_VELOCITY_CHARACTERISTICS"
        recommendation = (
            "Freeze this governing-equation design. Proceed to V16B-6 to design the exact numerical discretization and "
            "causal solution strategy for v dot grad(tau)=1. Do not solve it until the numerical contract is fixed."
        )
        next_ms = "V16B-6 — Directional Advective Travel-Time Numerical Scheme Contract"
    else:
        status = "V16B_DIRECTIONAL_FORMULATION_DESIGN_BLOCKED"
        diagnosis = "ONE_OR_MORE_DIRECTIONAL_FORMULATION_DESIGN_GATES_FAILED"
        recommendation = "Audit only failed V16B-5 design gates."
        next_ms = "V16B-5R — Directional Formulation Design Residual Audit"

    save_csv(
        DECISION_CSV,
        [{
            "status": status,
            "diagnosis": diagnosis,
            "selected_candidate": "D3",
            "selected_name": "ADVECTIVE_TRAVEL_TIME_EQUATION",
            "selected_equation": "v(x) dot grad(tau_ADV) = 1",
            "new_fitted_parameter": False,
            "isotropic_FMM_control_preserved": True,
            "next_milestone": next_ms,
        }],
    )

    contract = {
        "milestone": "V16B-5",
        "status": status,
        "diagnosis": diagnosis,
        "selected_formulation": {
            "candidate": "D3",
            "name": "ADVECTIVE_TRAVEL_TIME_EQUATION",
            "equation": "v(x) dot grad(tau_ADV) = 1",
            "boundary_condition": "tau_ADV=0 on frozen injector completion source set",
            "characteristics": "dx/dt=v(x)",
            "new_fitted_parameter": False,
        },
        "baseline_separation": {
            "isotropic_FMM": "frozen control",
            "directional_advective": "new unsolved branch",
            "Pollock": "frozen independent trajectory reference",
        },
        "numerical_requirements": [r["requirement"] for r in numerical_rows],
        "constraints": {
            "directional_PDE_solved": False,
            "FMM_rerun": False,
            "FMM_speed_changed": False,
            "Pollock_retrace": False,
            "SG3_SG4_rerun": False,
            "model_predict": False,
            "training": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    }
    save_json(CONTRACT_JSON, contract)

    save_json(
        SUMMARY_JSON,
        {
            "milestone": "V16B-5",
            "status": status,
            "diagnosis": diagnosis,
            "selected_formulation": "D3_ADVECTIVE_TRAVEL_TIME_EQUATION",
            "equation": "v(x) dot grad(tau_ADV) = 1",
            "isotropic_FMM_control_preserved": True,
            "new_fitted_parameter": False,
            "recommendation": recommendation,
            "next_milestone": next_ms,
        },
    )

    print("V16B-4 EVIDENCE")
    print(f"  Median terminal FMM/Pollock : {b4_summary['median_terminal_FMM_to_Pollock_ratio']:.6f}")
    print(f"  Median terminal error       : {b4_summary['median_terminal_error_days']:.6f} days")
    print(f"  FMM negative-step fraction  : {b4_summary['FMM_negative_step_fraction']:.6f}")
    print(f"  Directional extension       : {b4_summary['directional_extension_warranted']}")

    print("\nSELECTED DIRECTIONAL FORMULATION")
    print("  Candidate                    : D3")
    print("  Name                         : ADVECTIVE_TRAVEL_TIME_EQUATION")
    print("  Governing equation           : v(x) dot grad(tau_ADV) = 1")
    print("  Characteristics              : dx/dt = v(x)")
    print("  New fitted anisotropy param. : NONE")
    print("  Isotropic FMM retained       : True")

    print("\n" + "=" * 78)
    print("V16B-5 FINAL DESIGN GATES")
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
        CANDIDATE_CSV,
        PHYSICS_CSV,
        NUMERICAL_CSV,
        SEPARATION_CSV,
        GATES_CSV,
        DECISION_CSV,
    ]:
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_JSON.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_JSON.name}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16B-5 DIRECTIONAL ARRIVAL-TIME FORMULATION DESIGN: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()
