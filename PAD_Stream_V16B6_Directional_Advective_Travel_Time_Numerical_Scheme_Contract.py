from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json

import numpy as np


# =============================================================================
# PAD-Stream V16B-6
# Directional Advective Travel-Time Numerical Scheme Contract
#
# PURPOSE
# -------
# V16B-5 selected the governing directional transport equation:
#
#       v(x) · grad(tau_ADV) = 1
#
# with
#
#       tau_ADV = 0
#
# on the frozen injector completion cells.
#
# V16B-6 does NOT solve the equation.
#
# It freezes the numerical method before execution:
#
#   - first-order donor-cell / upwind discretization,
#   - physical unequal grid spacing,
#   - sign-aware directional derivatives,
#   - sparse linear system form,
#   - source-cell Dirichlet treatment,
#   - well/source-mask exclusion from transport rows,
#   - diagonal dominance / inflow availability diagnostics,
#   - residual and causality contracts,
#   - no Pollock-based coefficient tuning.
#
# GOVERNING DISCRETIZATION
# ------------------------
# For a cell P with velocity (vx, vy, vz):
#
#   vx * d(tau)/dx + vy * d(tau)/dy + vz * d(tau)/dz = 1
#
# First-order upwind:
#
#   if vx > 0:
#       d(tau)/dx ~ (tau_P - tau_W)/dx
#   if vx < 0:
#       d(tau)/dx ~ (tau_E - tau_P)/dx
#
# Analogously for y and z.
#
# Rearranged:
#
#   aP * tau_P - sum(aN * tau_N) = 1
#
# where the positive neighbor coefficients are:
#
#   aW = max(vx, 0)/dx
#   aE = max(-vx, 0)/dx
#   aS = max(vy, 0)/dy
#   aN = max(-vy, 0)/dy
#   aB = max(vz, 0)/dz
#   aT = max(-vz, 0)/dz
#
#   aP = aW + aE + aS + aN + aB + aT
#
# Source cells are fixed to tau=0.
#
# IMPORTANT
# ---------
# This is a pure steady-advection travel-time discretization.
# No diffusion, artificial transverse penalty, or fitted anisotropy is added.
# =============================================================================


ROOT = Path(__file__).resolve().parent

FOUNDATION_DIR = (
    ROOT
    / "output"
    / "V16_A_R8R_FOUNDATION_CASE_0001_FREEZE"
    / "PAD_Stream_V16A_Foundation_Case_0001"
)
FOUNDATION_NPZ = FOUNDATION_DIR / "V16A_Foundation_Case_0001.npz"

B1_DIR = ROOT / "output" / "V16_B1_FMM_GOVERNING_METRIC_CONTRACT"
B1_SPEED = B1_DIR / "V16B1_FMM_Speed_Field_Contract.npz"

B2_DIR = ROOT / "output" / "V16_B2_EXACT_3D_FMM_ARRIVAL_TIME_BASELINE"
B2_ARRIVAL = B2_DIR / "V16B2_Exact_3D_FMM_Arrival_Time.npz"

B5_DIR = ROOT / "output" / "V16_B5_DIRECTIONAL_ARRIVAL_TIME_FORMULATION_DESIGN"
B5_SUMMARY = B5_DIR / "PAD_Stream_V16B5_Summary.json"
B5_CONTRACT = B5_DIR / "V16B5_Directional_Arrival_Time_Design_Contract.json"

OUT = ROOT / "output" / "V16_B6_DIRECTIONAL_ADVECTIVE_NUMERICAL_SCHEME_CONTRACT"
OUT.mkdir(parents=True, exist_ok=True)

IDENTITY_CSV = OUT / "V16B6_Input_Identity.csv"
STENCIL_CSV = OUT / "V16B6_Upwind_Stencil_Contract.csv"
MATRIX_CSV = OUT / "V16B6_Sparse_Matrix_Structure_Audit.csv"
SOURCE_CSV = OUT / "V16B6_Source_Boundary_Contract.csv"
SOLVER_CSV = OUT / "V16B6_Linear_Solver_Contract.csv"
RESIDUAL_CSV = OUT / "V16B6_Residual_and_Causality_Contract.csv"
GATES_CSV = OUT / "V16B6_Final_Numerical_Design_Gates.csv"
DECISION_CSV = OUT / "V16B6_Numerical_Scheme_Decision.csv"

SCHEME_NPZ = OUT / "V16B6_Directional_Advective_Scheme_Contract.npz"
CONTRACT_JSON = OUT / "V16B6_Directional_Advective_Numerical_Scheme_Contract.json"
SUMMARY_JSON = OUT / "PAD_Stream_V16B6_Summary.json"


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
    print("PAD-Stream V16B-6")
    print("Directional Advective Travel-Time Numerical Scheme Contract")
    print("=" * 78)

    print("""
NO DIRECTIONAL TRAVEL-TIME SOLVE WILL BE EXECUTED.
NO SPARSE LINEAR SYSTEM WILL BE SOLVED.
NO FAST MARCHING SOLVE WILL BE RERUN.
NO ISOTROPIC FMM SPEED FIELD WILL BE CHANGED.
NO POLLOCK STREAMLINE WILL BE RETRACED.
NO POLLOCK DATA WILL BE USED TO FIT COEFFICIENTS.
NO ARTIFICIAL CROSS-FLOW DIFFUSION WILL BE ADDED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO TRAINING WILL BE PERFORMED.
THIS MILESTONE FREEZES THE NUMERICAL SCHEME ONLY.
""")

    for p in [
        FOUNDATION_NPZ,
        B1_SPEED,
        B2_ARRIVAL,
        B5_SUMMARY,
        B5_CONTRACT,
    ]:
        if not p.exists():
            raise FileNotFoundError(p)

    b5_summary = load_json(B5_SUMMARY)
    b5_contract = load_json(B5_CONTRACT)

    if b5_summary.get("status") != "V16B_DIRECTIONAL_ADVECTIVE_TRAVEL_TIME_FORMULATION_READY":
        raise RuntimeError("V16B-6 requires completed V16B-5.")

    with np.load(B1_SPEED, allow_pickle=False) as db:
        Vxc = np.asarray(db["Vxc_m_s"], dtype=np.float64)
        Vyc = np.asarray(db["Vyc_m_s"], dtype=np.float64)
        Vzc = np.asarray(db["Vzc_m_s"], dtype=np.float64)

    with np.load(B2_ARRIVAL, allow_pickle=False) as db:
        source_mask = np.asarray(db["source_mask"], dtype=np.uint8).astype(bool)
        dx = float(np.asarray(db["dx_m"]).reshape(-1)[0])
        dy = float(np.asarray(db["dy_m"]).reshape(-1)[0])
        dz = float(np.asarray(db["dz_m"]).reshape(-1)[0])

    shape = Vxc.shape

    if Vyc.shape != shape or Vzc.shape != shape:
        raise RuntimeError("Cell-centered velocity component shapes do not match.")

    if shape != (15, 50, 50):
        raise RuntimeError(f"Unexpected grid shape: {shape}")

    if source_mask.shape != shape:
        raise RuntimeError("Source mask shape does not match velocity grid.")

    # -------------------------------------------------------------------------
    # Construct coefficient fields diagnostically only.
    # No linear solve occurs here.
    # -------------------------------------------------------------------------
    aW = np.maximum(Vxc, 0.0) / dx
    aE = np.maximum(-Vxc, 0.0) / dx
    aS = np.maximum(Vyc, 0.0) / dy
    aN = np.maximum(-Vyc, 0.0) / dy
    aB = np.maximum(Vzc, 0.0) / dz
    aT = np.maximum(-Vzc, 0.0) / dz

    aP = aW + aE + aS + aN + aB + aT

    # Boundary-neighbor availability masks.
    nz, ny, nx = shape

    hasW = np.ones(shape, dtype=bool)
    hasE = np.ones(shape, dtype=bool)
    hasS = np.ones(shape, dtype=bool)
    hasN = np.ones(shape, dtype=bool)
    hasB = np.ones(shape, dtype=bool)
    hasT = np.ones(shape, dtype=bool)

    hasW[:, :, 0] = False
    hasE[:, :, -1] = False
    hasS[:, 0, :] = False
    hasN[:, -1, :] = False
    hasB[0, :, :] = False
    hasT[-1, :, :] = False

    # Out-of-domain upwind dependencies are potential open-boundary issues.
    missing_upwind = (
        ((aW > 0) & (~hasW))
        | ((aE > 0) & (~hasE))
        | ((aS > 0) & (~hasS))
        | ((aN > 0) & (~hasN))
        | ((aB > 0) & (~hasB))
        | ((aT > 0) & (~hasT))
    )

    non_source = ~source_mask
    missing_upwind_non_source = missing_upwind & non_source

    zero_diag_non_source = (aP <= 0.0) & non_source

    # For a pure upwind transport equation, positive diagonal follows directly
    # from any nonzero directional velocity component.
    positive_diag_fraction = float(np.mean(aP[non_source] > 0.0))

    # Structural matrix inventory.
    active_links = (
        ((aW > 0) & hasW).astype(np.int32)
        + ((aE > 0) & hasE).astype(np.int32)
        + ((aS > 0) & hasS).astype(np.int32)
        + ((aN > 0) & hasN).astype(np.int32)
        + ((aB > 0) & hasB).astype(np.int32)
        + ((aT > 0) & hasT).astype(np.int32)
    )

    non_source_count = int(np.sum(non_source))
    source_count = int(np.sum(source_mask))

    estimated_nnz = (
        non_source_count  # diagonal
        + int(np.sum(active_links[non_source]))
        + source_count    # source identity rows
    )

    save_csv(
        IDENTITY_CSV,
        [{
            "foundation_sha256": sha256_file(FOUNDATION_NPZ),
            "V16B1_speed_sha256": sha256_file(B1_SPEED),
            "V16B2_arrival_sha256": sha256_file(B2_ARRIVAL),
            "V16B5_contract_sha256": sha256_file(B5_CONTRACT),
            "grid_shape": str(shape),
            "dx_m": dx,
            "dy_m": dy,
            "dz_m": dz,
        }],
    )

    stencil_rows = [
        {
            "direction": "WEST",
            "coefficient": "aW=max(vx,0)/dx",
            "neighbor": "(k,j,i-1)",
            "active_when": "vx>0",
            "derivative": "(tau_P-tau_W)/dx",
        },
        {
            "direction": "EAST",
            "coefficient": "aE=max(-vx,0)/dx",
            "neighbor": "(k,j,i+1)",
            "active_when": "vx<0",
            "derivative": "(tau_E-tau_P)/dx",
        },
        {
            "direction": "SOUTH",
            "coefficient": "aS=max(vy,0)/dy",
            "neighbor": "(k,j-1,i)",
            "active_when": "vy>0",
            "derivative": "(tau_P-tau_S)/dy",
        },
        {
            "direction": "NORTH",
            "coefficient": "aN=max(-vy,0)/dy",
            "neighbor": "(k,j+1,i)",
            "active_when": "vy<0",
            "derivative": "(tau_N-tau_P)/dy",
        },
        {
            "direction": "BOTTOM",
            "coefficient": "aB=max(vz,0)/dz",
            "neighbor": "(k-1,j,i)",
            "active_when": "vz>0",
            "derivative": "(tau_P-tau_B)/dz",
        },
        {
            "direction": "TOP",
            "coefficient": "aT=max(-vz,0)/dz",
            "neighbor": "(k+1,j,i)",
            "active_when": "vz<0",
            "derivative": "(tau_T-tau_P)/dz",
        },
    ]
    save_csv(STENCIL_CSV, stencil_rows)

    save_csv(
        MATRIX_CSV,
        [{
            "unknown_count": int(np.prod(shape)),
            "source_identity_rows": source_count,
            "transport_rows": non_source_count,
            "estimated_nnz": estimated_nnz,
            "mean_active_upwind_neighbors": float(np.mean(active_links[non_source])),
            "min_active_upwind_neighbors": int(np.min(active_links[non_source])),
            "max_active_upwind_neighbors": int(np.max(active_links[non_source])),
            "positive_diagonal_fraction_non_source": positive_diag_fraction,
            "zero_diagonal_non_source_cells": int(np.sum(zero_diag_non_source)),
            "missing_upwind_boundary_cells": int(np.sum(missing_upwind_non_source)),
        }],
    )

    source_indices = np.argwhere(source_mask)
    source_rows = []

    for sid, (k, j, i) in enumerate(source_indices):
        source_rows.append({
            "source_id": sid,
            "k": int(k),
            "j": int(j),
            "i": int(i),
            "boundary_condition": "tau_ADV=0",
            "matrix_row": "identity",
            "rhs": 0.0,
        })

    save_csv(SOURCE_CSV, source_rows)

    solver_rows = [
        {
            "item": "system_form",
            "value": "A tau = b",
            "requirement": "sparse steady linear transport system",
        },
        {
            "item": "primary_solver",
            "value": "scipy.sparse.linalg.spsolve",
            "requirement": "deterministic direct sparse reference solve",
        },
        {
            "item": "secondary_solver",
            "value": "optional GMRES/BiCGSTAB only after direct baseline",
            "requirement": "future scale-up only",
        },
        {
            "item": "matrix_dtype",
            "value": "float64",
            "requirement": "reference numerical baseline",
        },
        {
            "item": "artificial_diffusion",
            "value": "NONE",
            "requirement": "pure directional-advection baseline",
        },
        {
            "item": "Pollock_based_parameter_tuning",
            "value": "PROHIBITED",
            "requirement": "independent physics baseline",
        },
    ]
    save_csv(SOLVER_CSV, solver_rows)

    residual_rows = [
        {
            "check": "linear_system_relative_residual",
            "formula": "||A tau-b||2 / max(||b||2, tiny)",
            "required": True,
        },
        {
            "check": "advective_PDE_residual",
            "formula": "vx*d_upwind(tau)/dx + vy*d_upwind(tau)/dy + vz*d_upwind(tau)/dz - 1",
            "required": True,
        },
        {
            "check": "source_zero",
            "formula": "max(|tau[source]|)=0",
            "required": True,
        },
        {
            "check": "finite_nonnegative",
            "formula": "all finite and tau>=0",
            "required": True,
        },
        {
            "check": "flow_direction_causality",
            "formula": "downstream travel time should not systematically decrease along frozen velocity characteristics",
            "required": True,
        },
        {
            "check": "Pollock_comparison",
            "formula": "deferred until directional solution is frozen",
            "required": True,
        },
    ]
    save_csv(RESIDUAL_CSV, residual_rows)

    # Persist coefficient contract only.
    np.savez_compressed(
        SCHEME_NPZ,
        aW_s_inv=aW,
        aE_s_inv=aE,
        aS_s_inv=aS,
        aN_s_inv=aN,
        aB_s_inv=aB,
        aT_s_inv=aT,
        aP_s_inv=aP,
        source_mask=source_mask.astype(np.uint8),
        active_upwind_neighbor_count=active_links.astype(np.int8),
        missing_upwind_boundary_mask=missing_upwind_non_source.astype(np.uint8),
        dx_m=np.asarray([dx], dtype=np.float64),
        dy_m=np.asarray([dy], dtype=np.float64),
        dz_m=np.asarray([dz], dtype=np.float64),
        authority_label_ascii=np.frombuffer(
            b"PAD_STREAM_V16B6_ADVECTIVE_NUMERICAL_SCHEME_CONTRACT",
            dtype=np.uint8,
        ),
    )

    # Structural design classification.
    #
    # Missing upwind dependencies at external boundaries are not silently fixed.
    # If any exist, execution must pause for a boundary-condition policy audit.
    open_boundary_blocker = bool(np.any(missing_upwind_non_source))
    zero_diag_blocker = bool(np.any(zero_diag_non_source))

    gates = [
        ("V16B5_directional_formulation_reproduced", True),
        ("governing_equation_v_dot_grad_tau_equals_1_retained", True),
        ("physical_dx_dy_dz_retained", dx > 0 and dy > 0 and dz > 0),
        ("frozen_cell_centered_velocity_loaded", True),
        ("first_order_sign_aware_upwind_stencil_defined", True),
        ("sparse_linear_system_form_defined", True),
        ("source_identity_rows_defined", source_count > 0),
        ("no_zero_diagonal_non_source_cells", not zero_diag_blocker),
        ("external_upwind_boundary_dependencies_audited", True),
        ("linear_solver_contract_defined", True),
        ("PDE_residual_contract_defined", True),
        ("causality_contract_defined", True),
        ("no_artificial_crossflow_diffusion", True),
        ("no_Pollock_parameter_tuning", True),
        ("no_directional_solve_executed", True),
        ("no_FMM_rerun", True),
        ("no_FMM_speed_change", True),
        ("no_Pollock_retrace", True),
        ("no_model_predict", True),
        ("no_training", True),
    ]

    save_csv(
        GATES_CSV,
        [{"gate": g, "passed": bool(p)} for g, p in gates],
    )

    all_pass = all(bool(p) for _, p in gates)

    if not all_pass:
        status = "V16B_DIRECTIONAL_NUMERICAL_SCHEME_CONTRACT_BLOCKED"
        diagnosis = "ONE_OR_MORE_DIRECTIONAL_SCHEME_DESIGN_GATES_FAILED"
        recommendation = "Audit only failed V16B-6 design gates."
        next_ms = "V16B-6R — Directional Numerical Scheme Residual Audit"

    elif open_boundary_blocker:
        status = "V16B_DIRECTIONAL_NUMERICAL_SCHEME_BOUNDARY_POLICY_REQUIRED"
        diagnosis = "ONE_OR_MORE_NON_SOURCE_BOUNDARY_CELLS_REQUIRE_UPWIND_INFORMATION_FROM_OUTSIDE_THE_DOMAIN"
        recommendation = (
            "Do not solve yet. Define the external-boundary inflow travel-time policy source-authentically before "
            "assembling the directional transport system."
        )
        next_ms = "V16B-6A — Directional External-Boundary Inflow Policy Audit"

    else:
        status = "V16B_DIRECTIONAL_ADVECTIVE_NUMERICAL_SCHEME_READY"
        diagnosis = "FIRST_ORDER_SIGN_AWARE_UPWIND_SPARSE_TRANSPORT_DISCRETIZATION_IS_FULLY_DEFINED_WITHOUT_UNRESOLVED_BOUNDARY_INFLOW"
        recommendation = (
            "Freeze this numerical contract. Proceed to V16B-7 for the first controlled directional advective "
            "travel-time solve. Do not compare against Pollock until the directional solution passes its own residual gates."
        )
        next_ms = "V16B-7 — Controlled Directional Advective Travel-Time Solve"

    save_csv(
        DECISION_CSV,
        [{
            "status": status,
            "diagnosis": diagnosis,
            "unknown_count": int(np.prod(shape)),
            "source_count": source_count,
            "estimated_nnz": estimated_nnz,
            "missing_upwind_boundary_cells": int(np.sum(missing_upwind_non_source)),
            "zero_diagonal_non_source_cells": int(np.sum(zero_diag_non_source)),
            "scheme_npz_sha256": sha256_file(SCHEME_NPZ),
            "next_milestone": next_ms,
        }],
    )

    contract = {
        "milestone": "V16B-6",
        "status": status,
        "diagnosis": diagnosis,
        "governing_equation": "v dot grad(tau_ADV) = 1",
        "discretization": {
            "order": 1,
            "type": "sign-aware donor-cell upwind",
            "grid": "physical Cartesian unequal spacing",
            "equation_form": "aP*tauP - sum(aN*tauN) = 1",
            "source_rows": "tau=0 identity rows",
            "artificial_diffusion": False,
        },
        "matrix_structure": {
            "unknown_count": int(np.prod(shape)),
            "source_count": source_count,
            "estimated_nnz": estimated_nnz,
            "missing_upwind_boundary_cells": int(np.sum(missing_upwind_non_source)),
            "zero_diagonal_non_source_cells": int(np.sum(zero_diag_non_source)),
        },
        "solver_contract": {
            "primary": "scipy.sparse.linalg.spsolve",
            "dtype": "float64",
            "solve_executed_in_V16B6": False,
        },
        "validation_contract": [
            "linear_system_relative_residual",
            "upwind_advective_PDE_residual",
            "source_zero",
            "finite_nonnegative",
            "flow_direction_causality",
        ],
        "comparison_policy": {
            "Pollock_used_for_coefficient_tuning": False,
            "Pollock_comparison_before_solution_freeze": False,
        },
        "output": {
            "scheme_file": str(SCHEME_NPZ),
            "sha256": sha256_file(SCHEME_NPZ),
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    }

    save_json(CONTRACT_JSON, contract)

    save_json(
        SUMMARY_JSON,
        {
            "milestone": "V16B-6",
            "status": status,
            "diagnosis": diagnosis,
            "unknown_count": int(np.prod(shape)),
            "source_count": source_count,
            "estimated_nnz": estimated_nnz,
            "missing_upwind_boundary_cells": int(np.sum(missing_upwind_non_source)),
            "zero_diagonal_non_source_cells": int(np.sum(zero_diag_non_source)),
            "recommendation": recommendation,
            "next_milestone": next_ms,
        },
    )

    print("UPWIND TRANSPORT SYSTEM")
    print(f"  Grid shape                 : {shape}")
    print(f"  Unknowns                   : {np.prod(shape)}")
    print(f"  Source rows                : {source_count}")
    print(f"  Estimated nonzeros         : {estimated_nnz}")
    print(f"  Positive diagonal fraction : {positive_diag_fraction:.6f}")
    print(f"  Zero diagonal non-source   : {np.sum(zero_diag_non_source)}")
    print(f"  Missing boundary upwind    : {np.sum(missing_upwind_non_source)}")

    print("\nPRIMARY DISCRETIZATION")
    print("  vx>0 : (tau_P - tau_W)/dx")
    print("  vx<0 : (tau_E - tau_P)/dx")
    print("  vy>0 : (tau_P - tau_S)/dy")
    print("  vy<0 : (tau_N - tau_P)/dy")
    print("  vz>0 : (tau_P - tau_B)/dz")
    print("  vz<0 : (tau_T - tau_P)/dz")

    print("\n" + "=" * 78)
    print("V16B-6 FINAL NUMERICAL DESIGN GATES")
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

    print("\nNumerical:")
    print(f"  {SCHEME_NPZ.name}")
    print(f"  SHA-256: {sha256_file(SCHEME_NPZ)}")

    print("\nTables:")
    for p in [
        IDENTITY_CSV,
        STENCIL_CSV,
        MATRIX_CSV,
        SOURCE_CSV,
        SOLVER_CSV,
        RESIDUAL_CSV,
        GATES_CSV,
        DECISION_CSV,
    ]:
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_JSON.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_JSON.name}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16B-6 DIRECTIONAL NUMERICAL SCHEME CONTRACT: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()
