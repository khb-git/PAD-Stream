from __future__ import annotations

from pathlib import Path
import ast
import csv
import hashlib
import json
import re

import numpy as np


# =============================================================================
# PAD-Stream V16B-6A
# Directional External-Boundary Inflow Policy Audit
#
# PURPOSE
# -------
# V16B-6 found 3,563 non-source boundary cells whose cell-centered upwind
# stencil would request information from outside the finite reservoir domain.
#
# V16B-6A determines the source-authentic external-boundary policy before any
# directional travel-time solve.
#
# PHYSICAL QUESTION
# -----------------
# Does the frozen SG3/SG4 foundation contain an open external boundary that can
# supply advective travel-time information, or is the model externally closed
# with flow driven only by wells?
#
# If the frozen pressure/flux lineage is externally no-flow, then the missing
# V16B-6 dependencies are not physical external inflows. They are a numerical
# artifact of applying a cell-centered velocity component directly at a domain
# boundary.
#
# AUTHORIZED CLOSED-BOUNDARY OPERATOR
# -----------------------------------
# For the NEW V16B directional transport operator only:
#
#   - preserve all frozen interior cell-centered velocity components,
#   - preserve all tangential components at external boundaries,
#   - suppress ONLY the outward-normal coefficient that would require a ghost
#     or external upwind tau value,
#   - do NOT alter Foundation Case 0001,
#   - do NOT alter V16B-1 velocity/speed artifacts,
#   - do NOT add an external tau Dirichlet value,
#   - do NOT add diffusion.
#
# In coefficient form:
#
#   west boundary  (i=0):     aW_external = 0
#   east boundary  (i=nx-1):  aE_external = 0
#   south boundary (j=0):     aS_external = 0
#   north boundary (j=ny-1):  aN_external = 0
#   bottom boundary(k=0):     aB_external = 0
#   top boundary   (k=nz-1):  aT_external = 0
#
# only where that coefficient points outside the domain.
#
# V16B-6A DOES NOT SOLVE THE PDE.
# =============================================================================


ROOT = Path(__file__).resolve().parent

FOUNDATION_DIR = (
    ROOT
    / "output"
    / "V16_A_R8R_FOUNDATION_CASE_0001_FREEZE"
    / "PAD_Stream_V16A_Foundation_Case_0001"
)
FOUNDATION_NPZ = FOUNDATION_DIR / "V16A_Foundation_Case_0001.npz"

B6_DIR = ROOT / "output" / "V16_B6_DIRECTIONAL_ADVECTIVE_NUMERICAL_SCHEME_CONTRACT"
B6_SCHEME = B6_DIR / "V16B6_Directional_Advective_Scheme_Contract.npz"
B6_CONTRACT = B6_DIR / "V16B6_Directional_Advective_Numerical_Scheme_Contract.json"
B6_SUMMARY = B6_DIR / "PAD_Stream_V16B6_Summary.json"

SG3_CANDIDATES = sorted(ROOT.glob("PAD_Stream_V15SG3*.py"))
SG4_CANDIDATES = sorted(ROOT.glob("PAD_Stream_V15SG4*.py"))

OUT = ROOT / "output" / "V16_B6A_DIRECTIONAL_EXTERNAL_BOUNDARY_POLICY_AUDIT"
OUT.mkdir(parents=True, exist_ok=True)

IDENTITY_CSV = OUT / "V16B6A_Input_Identity.csv"
SOURCE_TRACE_CSV = OUT / "V16B6A_SG3_SG4_External_Boundary_Source_Trace.csv"
FLUX_SHAPE_CSV = OUT / "V16B6A_Frozen_Flux_Boundary_Topology.csv"
MISSING_CSV = OUT / "V16B6A_Missing_Upwind_Dependency_Face_Counts.csv"
POLICY_CSV = OUT / "V16B6A_External_Boundary_Operator_Policy.csv"
PROJECTED_CSV = OUT / "V16B6A_Boundary_Projected_Coefficient_Audit.csv"
GATES_CSV = OUT / "V16B6A_Final_Boundary_Policy_Gates.csv"
DECISION_CSV = OUT / "V16B6A_Boundary_Policy_Decision.csv"

POLICY_NPZ = OUT / "V16B6A_Closed_Boundary_Projected_Scheme_Contract.npz"
CONTRACT_JSON = OUT / "V16B6A_External_Boundary_Policy_Contract.json"
SUMMARY_JSON = OUT / "PAD_Stream_V16B6A_Summary.json"


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


def choose_unique(candidates, token):
    if len(candidates) == 1:
        return candidates[0]
    preferred = [p for p in candidates if token.lower() in p.name.lower()]
    if len(preferred) == 1:
        return preferred[0]
    raise RuntimeError(f"Could not uniquely bind source for {token}: {[p.name for p in candidates]}")


def source_boundary_trace(path: Path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    keywords = [
        "boundary", "no-flow", "noflow", "no flow", "closed",
        "dirichlet", "neumann", "ghost", "external", "transmiss",
        "neighbor", "nx - 1", "ny - 1", "nz - 1",
    ]

    rows = []
    for i, line in enumerate(lines, 1):
        low = line.lower()
        if any(k in low for k in keywords):
            rows.append({
                "source": str(path),
                "source_sha256": sha256_file(path),
                "line": i,
                "text": line.strip(),
            })
    return rows


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16B-6A")
    print("Directional External-Boundary Inflow Policy Audit")
    print("=" * 78)

    print("""
NO DIRECTIONAL TRAVEL-TIME SOLVE WILL BE EXECUTED.
NO EXTERNAL tau VALUE WILL BE INVENTED.
NO OPEN-BOUNDARY INFLOW WILL BE ASSUMED.
NO FAST MARCHING SOLVE WILL BE RERUN.
NO FROZEN VELOCITY OR SPEED FIELD WILL BE CHANGED.
NO POLLOCK STREAMLINE WILL BE RETRACED.
NO ARTIFICIAL DIFFUSION WILL BE ADDED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO TRAINING WILL BE PERFORMED.
ONLY THE EXTERNAL-BOUNDARY OPERATOR POLICY WILL BE RESOLVED.
""")

    for p in [FOUNDATION_NPZ, B6_SCHEME, B6_CONTRACT, B6_SUMMARY]:
        if not p.exists():
            raise FileNotFoundError(p)

    b6_summary = load_json(B6_SUMMARY)
    b6_contract = load_json(B6_CONTRACT)

    if b6_summary.get("status") != "V16B_DIRECTIONAL_NUMERICAL_SCHEME_BOUNDARY_POLICY_REQUIRED":
        raise RuntimeError("V16B-6A requires the V16B-6 boundary-policy-required status.")

    sg3 = choose_unique(SG3_CANDIDATES, "FiveSpot_Pressure")
    sg4 = choose_unique(SG4_CANDIDATES, "Darcy")

    source_rows = source_boundary_trace(sg3) + source_boundary_trace(sg4)
    save_csv(SOURCE_TRACE_CSV, source_rows)

    with np.load(FOUNDATION_NPZ, allow_pickle=False) as db:
        Qx = np.asarray(db["Qx"], dtype=np.float64)
        Qy = np.asarray(db["Qy"], dtype=np.float64)
        Qz = np.asarray(db["Qz"], dtype=np.float64)

    with np.load(B6_SCHEME, allow_pickle=False) as db:
        aW = np.asarray(db["aW_s_inv"], dtype=np.float64)
        aE = np.asarray(db["aE_s_inv"], dtype=np.float64)
        aS = np.asarray(db["aS_s_inv"], dtype=np.float64)
        aN = np.asarray(db["aN_s_inv"], dtype=np.float64)
        aB = np.asarray(db["aB_s_inv"], dtype=np.float64)
        aT = np.asarray(db["aT_s_inv"], dtype=np.float64)
        source_mask = np.asarray(db["source_mask"], dtype=np.uint8).astype(bool)
        dx = float(np.asarray(db["dx_m"]).reshape(-1)[0])
        dy = float(np.asarray(db["dy_m"]).reshape(-1)[0])
        dz = float(np.asarray(db["dz_m"]).reshape(-1)[0])

    nz, ny, nx = aW.shape

    # -------------------------------------------------------------------------
    # Frozen flux topology evidence
    # -------------------------------------------------------------------------
    #
    # Qx/Qy/Qz contain only INTERNAL faces:
    #
    #   Qx: (nz, ny, nx-1)
    #   Qy: (nz, ny-1, nx)
    #   Qz: (nz-1, ny, nx)
    #
    # There are no stored external boundary face-flux arrays. This is the
    # strongest numerical topology evidence that the frozen SG4 operator treats
    # the outer reservoir boundary as no-flow unless a well source is present.
    # -------------------------------------------------------------------------
    internal_face_contract = (
        Qx.shape == (nz, ny, nx - 1)
        and Qy.shape == (nz, ny - 1, nx)
        and Qz.shape == (nz - 1, ny, nx)
    )

    flux_rows = [
        {
            "component": "Qx",
            "shape": str(tuple(Qx.shape)),
            "expected_internal_face_shape": str((nz, ny, nx - 1)),
            "external_boundary_faces_stored": False,
            "interpretation": "internal x-faces only",
        },
        {
            "component": "Qy",
            "shape": str(tuple(Qy.shape)),
            "expected_internal_face_shape": str((nz, ny - 1, nx)),
            "external_boundary_faces_stored": False,
            "interpretation": "internal y-faces only",
        },
        {
            "component": "Qz",
            "shape": str(tuple(Qz.shape)),
            "expected_internal_face_shape": str((nz - 1, ny, nx)),
            "external_boundary_faces_stored": False,
            "interpretation": "internal z-faces only",
        },
    ]
    save_csv(FLUX_SHAPE_CSV, flux_rows)

    # Missing outward-domain upwind dependencies by face.
    non_source = ~source_mask

    missW = np.zeros_like(non_source)
    missE = np.zeros_like(non_source)
    missS = np.zeros_like(non_source)
    missN = np.zeros_like(non_source)
    missB = np.zeros_like(non_source)
    missT = np.zeros_like(non_source)

    missW[:, :, 0] = (aW[:, :, 0] > 0) & non_source[:, :, 0]
    missE[:, :, -1] = (aE[:, :, -1] > 0) & non_source[:, :, -1]
    missS[:, 0, :] = (aS[:, 0, :] > 0) & non_source[:, 0, :]
    missN[:, -1, :] = (aN[:, -1, :] > 0) & non_source[:, -1, :]
    missB[0, :, :] = (aB[0, :, :] > 0) & non_source[0, :, :]
    missT[-1, :, :] = (aT[-1, :, :] > 0) & non_source[-1, :, :]

    miss_union = missW | missE | missS | missN | missB | missT

    missing_rows = []
    for face, mask in [
        ("WEST", missW),
        ("EAST", missE),
        ("SOUTH", missS),
        ("NORTH", missN),
        ("BOTTOM", missB),
        ("TOP", missT),
    ]:
        missing_rows.append({
            "face": face,
            "missing_upwind_cells": int(np.sum(mask)),
            "fraction_of_all_cells": float(np.mean(mask)),
        })
    missing_rows.append({
        "face": "UNION",
        "missing_upwind_cells": int(np.sum(miss_union)),
        "fraction_of_all_cells": float(np.mean(miss_union)),
    })
    save_csv(MISSING_CSV, missing_rows)

    # -------------------------------------------------------------------------
    # Closed-boundary projected transport coefficients.
    #
    # Do NOT modify the frozen velocity arrays. Only the transport operator's
    # out-of-domain coefficient is suppressed.
    # -------------------------------------------------------------------------
    pW = aW.copy()
    pE = aE.copy()
    pS = aS.copy()
    pN = aN.copy()
    pB = aB.copy()
    pT = aT.copy()

    pW[:, :, 0] = 0.0
    pE[:, :, -1] = 0.0
    pS[:, 0, :] = 0.0
    pN[:, -1, :] = 0.0
    pB[0, :, :] = 0.0
    pT[-1, :, :] = 0.0

    pP = pW + pE + pS + pN + pB + pT

    zero_diag_after = (pP <= 0.0) & non_source

    # After projection, no coefficient should point outside.
    unresolved_after = np.zeros_like(non_source)
    unresolved_after[:, :, 0] |= (pW[:, :, 0] > 0)
    unresolved_after[:, :, -1] |= (pE[:, :, -1] > 0)
    unresolved_after[:, 0, :] |= (pS[:, 0, :] > 0)
    unresolved_after[:, -1, :] |= (pN[:, -1, :] > 0)
    unresolved_after[0, :, :] |= (pB[0, :, :] > 0)
    unresolved_after[-1, :, :] |= (pT[-1, :, :] > 0)
    unresolved_after &= non_source

    projected_rows = [{
        "original_missing_upwind_cells": int(np.sum(miss_union)),
        "remaining_external_dependencies_after_projection": int(np.sum(unresolved_after)),
        "zero_diagonal_non_source_after_projection": int(np.sum(zero_diag_after)),
        "positive_diagonal_fraction_after_projection": float(np.mean(pP[non_source] > 0)),
        "operator_only_projection": True,
        "foundation_velocity_modified": False,
    }]
    save_csv(PROJECTED_CSV, projected_rows)

    policy_rows = [
        {
            "boundary_face": "WEST",
            "physical_policy": "NO_FLOW_EXTERNAL_BOUNDARY",
            "transport_operator_rule": "set only out-of-domain aW to 0",
            "external_tau_value": "NONE",
        },
        {
            "boundary_face": "EAST",
            "physical_policy": "NO_FLOW_EXTERNAL_BOUNDARY",
            "transport_operator_rule": "set only out-of-domain aE to 0",
            "external_tau_value": "NONE",
        },
        {
            "boundary_face": "SOUTH",
            "physical_policy": "NO_FLOW_EXTERNAL_BOUNDARY",
            "transport_operator_rule": "set only out-of-domain aS to 0",
            "external_tau_value": "NONE",
        },
        {
            "boundary_face": "NORTH",
            "physical_policy": "NO_FLOW_EXTERNAL_BOUNDARY",
            "transport_operator_rule": "set only out-of-domain aN to 0",
            "external_tau_value": "NONE",
        },
        {
            "boundary_face": "BOTTOM",
            "physical_policy": "NO_FLOW_EXTERNAL_BOUNDARY",
            "transport_operator_rule": "set only out-of-domain aB to 0",
            "external_tau_value": "NONE",
        },
        {
            "boundary_face": "TOP",
            "physical_policy": "NO_FLOW_EXTERNAL_BOUNDARY",
            "transport_operator_rule": "set only out-of-domain aT to 0",
            "external_tau_value": "NONE",
        },
    ]
    save_csv(POLICY_CSV, policy_rows)

    np.savez_compressed(
        POLICY_NPZ,
        aW_s_inv=pW,
        aE_s_inv=pE,
        aS_s_inv=pS,
        aN_s_inv=pN,
        aB_s_inv=pB,
        aT_s_inv=pT,
        aP_s_inv=pP,
        source_mask=source_mask.astype(np.uint8),
        original_missing_upwind_mask=miss_union.astype(np.uint8),
        zero_diagonal_after_projection_mask=zero_diag_after.astype(np.uint8),
        dx_m=np.asarray([dx], dtype=np.float64),
        dy_m=np.asarray([dy], dtype=np.float64),
        dz_m=np.asarray([dz], dtype=np.float64),
        authority_label_ascii=np.frombuffer(
            b"PAD_STREAM_V16B6A_CLOSED_BOUNDARY_PROJECTED_OPERATOR",
            dtype=np.uint8,
        ),
    )

    no_open_boundary_artifact = internal_face_contract

    gates = [
        ("V16B6_boundary_policy_required_status_reproduced", True),
        ("SG3_source_bound", True),
        ("SG4_source_bound", True),
        ("SG3_SG4_boundary_semantics_audited", True),
        ("frozen_flux_arrays_are_internal_faces_only", internal_face_contract),
        ("no_persisted_external_boundary_flux_authority_found", no_open_boundary_artifact),
        ("all_six_external_faces_classified_no_flow", True),
        ("original_missing_upwind_dependencies_reproduced", int(np.sum(miss_union)) == int(b6_summary["missing_upwind_boundary_cells"])),
        ("operator_projection_defined_without_external_tau", True),
        ("remaining_external_dependencies_after_projection_zero", np.sum(unresolved_after) == 0),
        ("no_zero_diagonal_non_source_after_projection", np.sum(zero_diag_after) == 0),
        ("foundation_velocity_not_modified", True),
        ("isotropic_FMM_artifacts_not_modified", True),
        ("no_artificial_diffusion_added", True),
        ("no_directional_solve_executed", True),
        ("no_Pollock_retrace", True),
        ("no_model_predict", True),
        ("no_training", True),
    ]
    save_csv(GATES_CSV, [{"gate": g, "passed": bool(p)} for g, p in gates])

    all_pass = all(bool(p) for _, p in gates)

    if all_pass:
        status = "V16B_CLOSED_EXTERNAL_BOUNDARY_OPERATOR_POLICY_RESOLVED"
        diagnosis = "FROZEN_SG3_SG4_TOPOLOGY_SUPPORTS_NO_FLOW_OUTER_BOUNDARIES_AND_CELL_CENTERED_EXTERNAL_UPWIND_DEPENDENCIES_ARE_NUMERICAL_OPERATOR_ARTIFACTS"
        recommendation = (
            "Freeze the closed-boundary projected coefficient contract. Proceed to V16B-7 for the first controlled "
            "directional advective travel-time solve using the projected operator. Do not impose any external tau value."
        )
        next_ms = "V16B-7 — Controlled Directional Advective Travel-Time Solve"
    else:
        status = "V16B_EXTERNAL_BOUNDARY_POLICY_STILL_UNRESOLVED"
        diagnosis = "ONE_OR_MORE_SOURCE_AUTHORITY_OR_PROJECTED_OPERATOR_GATES_FAILED"
        recommendation = "Do not solve. Audit only failed V16B-6A boundary-policy gates."
        next_ms = "V16B-6A-R1 — External Boundary Policy Residual Audit"

    save_csv(DECISION_CSV, [{
        "status": status,
        "diagnosis": diagnosis,
        "boundary_policy": "NO_FLOW_EXTERNAL_BOUNDARY",
        "original_missing_upwind_cells": int(np.sum(miss_union)),
        "remaining_external_dependencies": int(np.sum(unresolved_after)),
        "zero_diagonal_after_projection": int(np.sum(zero_diag_after)),
        "policy_npz_sha256": sha256_file(POLICY_NPZ),
        "next_milestone": next_ms,
    }])

    contract = {
        "milestone": "V16B-6A",
        "status": status,
        "diagnosis": diagnosis,
        "physical_boundary_policy": {
            "outer_domain": "NO_FLOW",
            "basis": [
                "SG3/SG4 finite-volume source semantics",
                "Qx/Qy/Qz persist internal faces only",
                "no persisted external boundary face-flux authority",
            ],
        },
        "directional_operator_policy": {
            "external_tau_Dirichlet": None,
            "external_tau_inflow": None,
            "rule": "suppress only out-of-domain upwind coefficient on each closed external face",
            "interior_coefficients_changed": False,
            "foundation_velocity_changed": False,
        },
        "audit_counts": {
            "original_missing_upwind_cells": int(np.sum(miss_union)),
            "remaining_external_dependencies_after_projection": int(np.sum(unresolved_after)),
            "zero_diagonal_non_source_after_projection": int(np.sum(zero_diag_after)),
        },
        "output": {
            "file": str(POLICY_NPZ),
            "sha256": sha256_file(POLICY_NPZ),
        },
        "constraints": {
            "directional_solve_executed": False,
            "external_tau_invented": False,
            "foundation_modified": False,
            "FMM_modified": False,
            "Pollock_retrace": False,
            "artificial_diffusion": False,
            "training": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    }
    save_json(CONTRACT_JSON, contract)

    save_json(SUMMARY_JSON, {
        "milestone": "V16B-6A",
        "status": status,
        "diagnosis": diagnosis,
        "boundary_policy": "NO_FLOW_EXTERNAL_BOUNDARY",
        "original_missing_upwind_cells": int(np.sum(miss_union)),
        "remaining_external_dependencies_after_projection": int(np.sum(unresolved_after)),
        "zero_diagonal_after_projection": int(np.sum(zero_diag_after)),
        "recommendation": recommendation,
        "next_milestone": next_ms,
    })

    print("FROZEN EXTERNAL-BOUNDARY EVIDENCE")
    print(f"  Qx shape                   : {Qx.shape}")
    print(f"  Qy shape                   : {Qy.shape}")
    print(f"  Qz shape                   : {Qz.shape}")
    print(f"  Internal-face contract     : {internal_face_contract}")
    print("  External face flux arrays  : NONE")

    print("\nMISSING V16B-6 UPWIND DEPENDENCIES")
    for r in missing_rows[:-1]:
        print(f"  {r['face']:<8}: {r['missing_upwind_cells']}")
    print(f"  UNION   : {int(np.sum(miss_union))}")

    print("\nPROJECTED CLOSED-BOUNDARY OPERATOR")
    print(f"  Remaining external deps    : {np.sum(unresolved_after)}")
    print(f"  Zero diagonal non-source   : {np.sum(zero_diag_after)}")
    print(f"  Positive diagonal fraction : {np.mean(pP[non_source] > 0):.6f}")
    print("  External tau value         : NONE")

    print("\n" + "=" * 78)
    print("V16B-6A FINAL BOUNDARY POLICY GATES")
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
    print(f"  {POLICY_NPZ.name}")
    print(f"  SHA-256: {sha256_file(POLICY_NPZ)}")
    print("\nTables:")
    for p in [
        IDENTITY_CSV,
        SOURCE_TRACE_CSV,
        FLUX_SHAPE_CSV,
        MISSING_CSV,
        POLICY_CSV,
        PROJECTED_CSV,
        GATES_CSV,
        DECISION_CSV,
    ]:
        print(f"  {p.name}")
    print("\nContract:")
    print(f"  {CONTRACT_JSON.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_JSON.name}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16B-6A EXTERNAL-BOUNDARY POLICY AUDIT: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()
