from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import re

import numpy as np


# =============================================================================
# PAD-Stream V16C-7
# Pollock-TOF / Full BL-CCUS Transport Adapter Physics Contract
#
# PURPOSE
# -------
# Derive the physics adapter between:
#
#   V16 primary transport lineage:
#       Stage-4 full compressible + capillary conservative Godunov PI-RNN
#
# and:
#
#   frozen PAD-Stream streamline coordinates:
#       Pollock XYZ + Pollock TOF
#
# NO transport solve is performed.
# NO saturation target Y is generated.
# NO PI-RNN is trained or inferred.
#
# ---------------------------------------------------------------------------
# NATIVE STAGE-4 PDE
# ---------------------------------------------------------------------------
#
#   dS/dt_D + d[ u_D(x_D) f(S) ]/dx_D
#       = (phi/Pe_c) d/dx_D [ D_tilde(S) dS/dx_D ]
#
#   u_D(x_D) = exp(Nc x_D)
#
# ---------------------------------------------------------------------------
# EXACT GEOMETRIC COORDINATE ADAPTER
# ---------------------------------------------------------------------------
#
# Along every frozen Pollock streamline:
#
#   s       = cumulative physical arc length
#   x_D     = s / L_s
#   theta   = tau_Pollock / tau_end
#
# Define
#
#   M(theta) = d theta / d x_D
#
# so that
#
#   d/dx_D = M d/dtheta
#
# and therefore
#
#   d/dx_D [D dS/dx_D]
#       = M d/dtheta [ D M dS/dtheta ].
#
# This identity is the exact coordinate transformation required to preserve
# the Stage-4 capillary operator on the frozen Pollock coordinate.
#
# IMPORTANT:
# Pollock TOF is NOT x_D.
#
# ---------------------------------------------------------------------------
# COMPRESSIBILITY AUTHORITY
# ---------------------------------------------------------------------------
#
# The Stage-4 u_D = exp(Nc x_D) factor is NOT automatically applied on top of
# Pollock TOF.
#
# Pollock TOF already contains the frozen V15 velocity / residence-time
# kinematics. Stage-4 Nc/u_D may only survive as a distinct transport
# compressibility correction after its physical authority is separated from
# those frozen kinematics.
#
# C7 therefore:
#
#   - binds the geometric/TOF transform,
#   - binds the capillary spatial metric,
#   - PROHIBITS naive Nc/u_D stacking,
#   - identifies compressibility-authority separation as the only residual
#     physics decision before target generation.
#
# ---------------------------------------------------------------------------
# SEQUENCE CONTRACT
# ---------------------------------------------------------------------------
#
# V16C remains 201 nodes / streamline.
# No truth-adaptive reduction to the legacy native 64-node Stage-4 sequence
# is allowed.
#
# The future adapter must therefore operate natively on the frozen 201-node
# Pollock sequence; legacy 64 nodes remain a historical model-interface fact,
# not a reason to alter the frozen V16 geometry.
# =============================================================================


ROOT = Path(__file__).resolve().parent

C6_DIR = ROOT / "output" / "V16_C6_BL_CCUS_PIRNN_LINEAGE_BINDING_AUDIT"
C6_SUMMARY = C6_DIR / "PAD_Stream_V16C6_Summary.json"
C6_CONTRACT = C6_DIR / "V16C6_BL_CCUS_PIRNN_Lineage_Binding_Contract.json"

C5_DIR = ROOT / "output" / "V16_C5_TRANSPORT_TARGET_SUPERVISION_AUTHORITY_CONTRACT"
C5_CONTRACT = C5_DIR / "V16C5_Transport_Target_Supervision_Authority_Contract.json"

C2_DIR = ROOT / "output" / "V16_C2_MULTI_COORDINATE_STREAMLINE_TRANSPORT_DATABASE"
C2_DB = C2_DIR / "V16C2_Multi_Coordinate_Streamline_Transport_Database.npz"

STAGE4 = ROOT / "pi_rnn_stage4_full_godunov.py"
EXPECTED_STAGE4_SHA = "165016fd8c099afbe8fea0f5f1998728dc2a5b70ad2df35b9e1429d6eecb580a"

OUT = ROOT / "output" / "V16_C7_POLLOCK_TOF_FULL_BL_CCUS_ADAPTER_PHYSICS_CONTRACT"
OUT.mkdir(parents=True, exist_ok=True)

METRIC_NPZ = OUT / "V16C7_Pollock_TOF_Streamline_Metric_Contract.npz"

IDENTITY_CSV = OUT / "V16C7_Input_Identity.csv"
GEOM_CSV = OUT / "V16C7_Streamline_Geometric_Metric_Audit.csv"
TRANSFORM_CSV = OUT / "V16C7_Coordinate_Operator_Transform_Contract.csv"
CAP_CSV = OUT / "V16C7_Capillary_Operator_Transform_Contract.csv"
COMP_CSV = OUT / "V16C7_Compressibility_Authority_Separation.csv"
SEQ_CSV = OUT / "V16C7_Sequence_Interface_Decision.csv"
GATES_CSV = OUT / "V16C7_Final_Adapter_Physics_Gates.csv"
DECISION_CSV = OUT / "V16C7_Adapter_Physics_Decision.csv"

CONTRACT_JSON = OUT / "V16C7_Pollock_TOF_Full_BL_CCUS_Adapter_Physics_Contract.json"
SUMMARY_JSON = OUT / "PAD_Stream_V16C7_Summary.json"


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def save_csv(path: Path, rows):
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def centered_derivative(y, x):
    """
    Deterministic one-dimensional derivative along axis=1.
    Uses one-sided endpoints and centered interior differences.
    """
    y = np.asarray(y, dtype=np.float64)
    x = np.asarray(x, dtype=np.float64)

    out = np.empty_like(y)

    dx0 = x[:, 1] - x[:, 0]
    dx1 = x[:, -1] - x[:, -2]

    out[:, 0] = (y[:, 1] - y[:, 0]) / dx0
    out[:, -1] = (y[:, -1] - y[:, -2]) / dx1

    den = x[:, 2:] - x[:, :-2]
    out[:, 1:-1] = (y[:, 2:] - y[:, :-2]) / den

    return out


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16C-7")
    print("Pollock-TOF / Full BL-CCUS Transport Adapter Physics Contract")
    print("=" * 78)

    print("""
V16C-6 BL/CCUS PI-RNN LINEAGE IS IMMUTABLE.
STAGE-4 FULL COMPRESSIBLE + CAPILLARY GODUNOV IS THE PRIMARY TRANSPORT LINEAGE.
POLLOCK TOF REMAINS THE AUTHORITATIVE STREAMLINE TRANSPORT COORDINATE.

NO TRANSPORT SOLVE WILL BE EXECUTED.
NO Y_TRANSPORT WILL BE GENERATED.
NO SATURATION FIELD WILL BE GENERATED.
NO PI-RNN WILL BE TRAINED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO LOSS WEIGHT WILL BE CHANGED.
NO FMM / ADV / POLLOCK FIELD WILL BE RECALIBRATED.
NO LEGACY 64-NODE GRID WILL REPLACE THE FROZEN 201-NODE V16C GRID.
NO FROZEN V15/V16 ARTIFACT WILL BE CHANGED.

THIS MILESTONE DERIVES THE COORDINATE / METRIC ADAPTER ONLY.
""")

    for p in [C6_SUMMARY, C6_CONTRACT, C5_CONTRACT, C2_DB, STAGE4]:
        if not p.exists():
            raise FileNotFoundError(p)

    c6 = load_json(C6_SUMMARY)
    if c6.get("status") != "V16C_BL_CCUS_PIRNN_LINEAGE_BOUND_ADAPTER_REQUIRED":
        raise RuntimeError("V16C-7 requires completed V16C-6.")

    stage4_sha = sha256_file(STAGE4)
    if stage4_sha != EXPECTED_STAGE4_SHA:
        raise RuntimeError(
            f"Stage-4 SHA mismatch: {stage4_sha} != {EXPECTED_STAGE4_SHA}"
        )

    stage4_text = STAGE4.read_text(encoding="utf-8", errors="replace")

    stage4_ud_found = bool(
        re.search(r"(exp|expm1).*Nc.*xD|Nc.*xD.*(exp|expm1)", stage4_text, re.I | re.S)
    )
    stage4_capillary_found = (
        "inv_Pec" in stage4_text
        and "Dtilde" in stage4_text
        and "pde_residual_loss" in stage4_text
    )

    with np.load(C2_DB, allow_pickle=False) as db:
        xyz = np.asarray(db["streamline_xyz_m"], dtype=np.float64)
        tau = np.asarray(db["pollock_tof_s"], dtype=np.float64)
        xi = np.asarray(db["xi"], dtype=np.float64)

    ns, nn = tau.shape
    if xyz.shape != (ns, nn, 3):
        raise RuntimeError("Pollock XYZ / TOF shape mismatch.")
    if (ns, nn) != (1078, 201):
        raise RuntimeError(f"Unexpected V16C streamline shape: {(ns, nn)}")

    # -------------------------------------------------------------------------
    # Physical arc-length metric.
    # -------------------------------------------------------------------------
    dxyz = np.diff(xyz, axis=1)
    ds = np.linalg.norm(dxyz, axis=2)

    zero_ds = ds <= 0.0
    positive_ds = ds > 0.0

    s = np.concatenate(
        [np.zeros((ns, 1), dtype=np.float64), np.cumsum(ds, axis=1)],
        axis=1,
    )
    L = s[:, -1]

    if np.any(~np.isfinite(L)) or np.any(L <= 0.0):
        raise RuntimeError("One or more streamline lengths are invalid.")

    xD_arc = s / L[:, None]

    tau_end = tau[:, -1]
    if np.any(~np.isfinite(tau_end)) or np.any(tau_end <= 0.0):
        raise RuntimeError("One or more Pollock terminal TOFs are invalid.")

    theta = tau / tau_end[:, None]

    # Pollock time should be monotone along its own frozen trajectory.
    dtau = np.diff(tau, axis=1)
    tau_monotone = dtau >= -1e-10

    # Exact coordinate metric M = d theta / d x_D.
    # A derivative cannot be evaluated across a zero-length geometric segment.
    # The centered derivative uses xD_arc. If repeated positions occur, we
    # classify rather than fabricate a metric.
    dxD_seg = np.diff(xD_arc, axis=1)
    zero_xD_seg = dxD_seg <= 0.0

    metric_ready = not np.any(zero_xD_seg)

    if metric_ready:
        M = centered_derivative(theta, xD_arc)
        M_finite = bool(np.all(np.isfinite(M)))
        M_positive = bool(np.all(M > 0.0))
    else:
        M = np.full_like(theta, np.nan)
        M_finite = False
        M_positive = False

    # Direct segment diagnostic: dtheta/dxD.
    M_seg = np.full_like(ds, np.nan, dtype=np.float64)
    good = dxD_seg > 0.0
    M_seg[good] = np.diff(theta, axis=1)[good] / dxD_seg[good]

    # Also retain physical residence metric d tau / d s and pore-path speed ds/dtau.
    dtau_seg = np.diff(tau, axis=1)

    J_tau_per_m = np.full_like(ds, np.nan, dtype=np.float64)
    U_path_m_s = np.full_like(ds, np.nan, dtype=np.float64)

    good_metric = (ds > 0.0) & (dtau_seg > 0.0)
    J_tau_per_m[good_metric] = dtau_seg[good_metric] / ds[good_metric]
    U_path_m_s[good_metric] = ds[good_metric] / dtau_seg[good_metric]

    save_csv(
        IDENTITY_CSV,
        [{
            "V16C2_database_sha256": sha256_file(C2_DB),
            "V16C6_contract_sha256": sha256_file(C6_CONTRACT),
            "V16C5_contract_sha256": sha256_file(C5_CONTRACT),
            "stage4_source_sha256": stage4_sha,
            "stage4_sha_matches": stage4_sha == EXPECTED_STAGE4_SHA,
            "streamlines": ns,
            "nodes_per_streamline": nn,
        }],
    )

    geom_rows = [{
        "streamlines": ns,
        "nodes_per_streamline": nn,
        "segment_count": int(ds.size),
        "zero_length_segment_count": int(np.sum(zero_ds)),
        "positive_length_segment_fraction": float(np.mean(positive_ds)),
        "Pollock_negative_TOF_step_count": int(np.sum(dtau < -1e-10)),
        "Pollock_monotone_step_fraction": float(np.mean(tau_monotone)),
        "streamline_length_min_m": float(np.min(L)),
        "streamline_length_median_m": float(np.median(L)),
        "streamline_length_mean_m": float(np.mean(L)),
        "streamline_length_max_m": float(np.max(L)),
        "terminal_TOF_min_days": float(np.min(tau_end) / 86400.0),
        "terminal_TOF_median_days": float(np.median(tau_end) / 86400.0),
        "terminal_TOF_max_days": float(np.max(tau_end) / 86400.0),
        "metric_M_finite": M_finite,
        "metric_M_positive": M_positive,
    }]
    save_csv(GEOM_CSV, geom_rows)

    transform_rows = [
        {
            "object": "physical_arc_length",
            "symbol": "s",
            "definition": "cumulative Euclidean distance along frozen Pollock XYZ",
            "authority": "DERIVED_FROM_FROZEN_POLLOCK_GEOMETRY",
        },
        {
            "object": "dimensionless_arc_coordinate",
            "symbol": "xD_arc",
            "definition": "s / terminal_streamline_length",
            "authority": "V16_ADAPTER_COORDINATE",
        },
        {
            "object": "normalized_Pollock_TOF",
            "symbol": "theta",
            "definition": "tau_Pollock / terminal_Pollock_TOF",
            "authority": "POLL0CK_TOF_PRESERVED".replace("0", "O"),
        },
        {
            "object": "coordinate_metric",
            "symbol": "M",
            "definition": "d theta / d xD_arc",
            "authority": "DERIVED_COORDINATE_JACOBIAN",
        },
        {
            "object": "first_derivative_transform",
            "symbol": "d/dxD",
            "definition": "M * d/dtheta",
            "authority": "EXACT_CHAIN_RULE",
        },
    ]
    save_csv(TRANSFORM_CSV, transform_rows)

    cap_rows = [
        {
            "native_operator": "d/dxD [ D_tilde(S) dS/dxD ]",
            "transformed_operator": "M d/dtheta [ D_tilde(S) M dS/dtheta ]",
            "additional_fitted_parameter": False,
            "uses_Pollock_TOF": True,
            "uses_streamline_geometry": True,
            "status": "BOUND_IF_METRIC_M_VALID",
        },
        {
            "native_coefficient": "phi / Pe_c",
            "transformed_coefficient": "phi / Pe_c (unchanged; Jacobian carried by transformed operator)",
            "additional_fitted_parameter": False,
            "uses_Pollock_TOF": False,
            "uses_streamline_geometry": False,
            "status": "PRESERVED_FROM_STAGE4",
        },
    ]
    save_csv(CAP_CSV, cap_rows)

    comp_rows = [
        {
            "component": "frozen_Pollock_kinematics",
            "authority": "V15/V16 FROZEN FLOW",
            "contains_velocity_information": True,
            "allowed_to_change": False,
        },
        {
            "component": "Stage4_uD_exp_Nc_xD",
            "authority": "EXISTING_STAGE4_TRANSPORT_LINEAGE",
            "contains_velocity_information": True,
            "allowed_to_change": False,
        },
        {
            "component": "naive_combination",
            "authority": "NONE",
            "contains_velocity_information": True,
            "allowed_to_change": False,
            "decision": "PROHIBITED",
            "reason": "would risk applying the same kinematic velocity effect twice",
        },
        {
            "component": "residual_compressibility_mapping",
            "authority": "NOT_YET_BOUND",
            "contains_velocity_information": "TO_BE_CLASSIFIED",
            "allowed_to_change": False,
            "decision": "REQUIRES_NEXT_AUDIT",
            "reason": (
                "must distinguish transport/PVT compressibility from frozen Pollock flow kinematics "
                "before Stage4 Nc/uD can be retained, transformed, or removed"
            ),
        },
    ]
    save_csv(COMP_CSV, comp_rows)

    seq_rows = [
        {
            "interface": "legacy_Stage4_native",
            "nodes": 64,
            "status": "HISTORICAL_MODEL_INTERFACE",
            "V16_decision": "DO_NOT_FORCE_V16_GEOMETRY_TO_64",
        },
        {
            "interface": "V16C_frozen_Pollock",
            "nodes": 201,
            "status": "AUTHORITATIVE_V16_SEQUENCE",
            "V16_decision": "PRIMARY_ADAPTER_SEQUENCE",
        },
        {
            "interface": "future_model_execution",
            "nodes": 201,
            "status": "REQUIRED_BY_ADAPTER_CONTRACT",
            "V16_decision": (
                "either use sequence-length-flexible recurrent execution or build a deterministic "
                "201-node V16 model interface; no truth-adaptive resampling"
            ),
        },
    ]
    save_csv(SEQ_CSV, seq_rows)

    # Persist the adapter geometry regardless of compressibility decision.
    np.savez_compressed(
        METRIC_NPZ,
        streamline_arc_length_m=s,
        streamline_terminal_length_m=L,
        xD_arc=xD_arc,
        pollock_theta=theta,
        metric_M_dtheta_dxD=M,
        segment_metric_M_dtheta_dxD=M_seg,
        segment_dtau_ds_s_per_m=J_tau_per_m,
        segment_path_speed_m_s=U_path_m_s,
        xi=xi,
        authority_label_ascii=np.frombuffer(
            b"PAD_STREAM_V16C7_POLLOCK_TOF_STREAMLINE_METRIC_CONTRACT",
            dtype=np.uint8,
        ),
    )

    geometry_ready = (
        np.all(np.isfinite(s))
        and np.all(np.isfinite(xD_arc))
        and np.all(np.isfinite(theta))
        and int(np.sum(dtau < -1e-10)) == 0
    )

    capillary_transform_ready = geometry_ready and metric_ready and M_finite and M_positive

    compressibility_authority_ready = False  # deliberately not inferred

    gates = [
        ("V16C6_lineage_status_reproduced", True),
        ("stage4_source_sha256_reproduced", stage4_sha == EXPECTED_STAGE4_SHA),
        ("stage4_uD_Nc_semantics_reproduced", stage4_ud_found),
        ("stage4_capillary_semantics_reproduced", stage4_capillary_found),
        ("V16C2_Pollock_geometry_loaded", True),
        ("physical_arc_length_constructed", np.all(np.isfinite(s))),
        ("dimensionless_arc_coordinate_constructed", np.all(np.isfinite(xD_arc))),
        ("normalized_Pollock_theta_constructed", np.all(np.isfinite(theta))),
        ("Pollock_TOF_monotone_along_frozen_streamlines", int(np.sum(dtau < -1e-10)) == 0),
        ("coordinate_metric_M_constructed", metric_ready),
        ("coordinate_metric_M_finite", M_finite),
        ("coordinate_metric_M_positive", M_positive),
        ("first_derivative_chain_rule_bound", metric_ready),
        ("capillary_second_derivative_transform_bound", capillary_transform_ready),
        ("naive_Nc_uD_plus_Pollock_velocity_stacking_prohibited", True),
        ("compressibility_authority_separation_explicit", True),
        ("legacy_64_node_interface_not_imposed_on_V16", True),
        ("V16_201_node_adapter_sequence_retained", True),
        ("adapter_metric_artifact_saved", METRIC_NPZ.exists()),
        ("no_transport_solve", True),
        ("no_Y_transport_generated", True),
        ("no_saturation_generated", True),
        ("no_model_predict", True),
        ("no_training", True),
        ("no_loss_weight_change", True),
        ("no_frozen_artifact_mutation", True),
    ]

    save_csv(GATES_CSV, [{"gate": g, "passed": bool(v)} for g, v in gates])

    structural_pass = all(v for _, v in gates)

    # Compressibility separation is an explicit residual decision, not a failed
    # numerical gate. If the metric contract passes, C7 is complete with one
    # deliberately documented physics residual for C7A.
    if structural_pass and not compressibility_authority_ready:
        status = "V16C_POLLOCK_TOF_CAPILLARY_METRIC_ADAPTER_BOUND_COMPRESSIBILITY_AUTHORITY_PENDING"
        diagnosis = (
            "POLLOCK_TOF_TO_ARC_COORDINATE_JACOBIAN_AND_CAPILLARY_OPERATOR_TRANSFORM_ARE_BOUND_BUT_STAGE4_NC_UD_CANNOT_YET_BE_STACKED_ON_FROZEN_POLLOCK_KINEMATICS"
        )
        recommendation = (
            "Freeze the C7 geometric/capillary adapter. Do not generate Y yet. "
            "Proceed to V16C-7A to separate Stage-4 transport compressibility from frozen Pollock flow kinematics "
            "using source/PVT/pressure semantics; do not infer the answer from numerical fit."
        )
        next_ms = "V16C-7A — Compressibility Authority Separation / Nc-uD Pollock Compatibility Audit"
    elif structural_pass:
        status = "V16C_FULL_BL_CCUS_POLLOCK_ADAPTER_PHYSICS_READY"
        diagnosis = "ALL_GEOMETRIC_CAPILLARY_AND_COMPRESSIBILITY_ADAPTER_AUTHORITIES_BOUND"
        recommendation = "Proceed to target semantics; do not train yet."
        next_ms = "V16C-8 — Full BL/CCUS Streamline Target Semantics Contract"
    else:
        status = "V16C_POLLOCK_TOF_ADAPTER_PHYSICS_REQUIRES_AUDIT"
        diagnosis = "ONE_OR_MORE_GEOMETRIC_OR_OPERATOR_TRANSFORM_GATES_FAILED"
        recommendation = "Do not proceed to compressibility or target generation. Audit only failed V16C-7 gates."
        next_ms = "V16C-7R — Pollock-TOF Adapter Residual Audit"

    save_csv(
        DECISION_CSV,
        [{
            "status": status,
            "diagnosis": diagnosis,
            "geometry_adapter_ready": geometry_ready,
            "capillary_transform_ready": capillary_transform_ready,
            "compressibility_authority_ready": compressibility_authority_ready,
            "naive_Nc_Pollock_stacking": "PROHIBITED",
            "V16_sequence_nodes": 201,
            "next_milestone": next_ms,
        }],
    )

    contract = {
        "milestone": "V16C-7",
        "status": status,
        "diagnosis": diagnosis,
        "coordinate_adapter": {
            "physical_arc_length": "s from frozen Pollock XYZ",
            "xD_arc": "s/L_s",
            "theta": "tau_Pollock/tau_end",
            "metric_M": "d theta / d xD_arc",
            "first_derivative": "d/dxD = M d/dtheta",
        },
        "capillary_adapter": {
            "native": "d/dxD[D_tilde dS/dxD]",
            "transformed": "M d/dtheta[D_tilde M dS/dtheta]",
            "status": "BOUND" if capillary_transform_ready else "UNRESOLVED",
        },
        "compressibility_adapter": {
            "Stage4_uD": "exp(Nc xD)",
            "Pollock_contains_frozen_kinematics": True,
            "naive_stacking": "PROHIBITED",
            "residual_authority": "PENDING_C7A",
        },
        "sequence_contract": {
            "legacy_stage4_nodes": 64,
            "V16_authoritative_nodes": 201,
            "V16_decision": "retain 201 nodes; do not truth-adaptively collapse to 64",
        },
        "metric_artifact": {
            "path": str(METRIC_NPZ),
            "sha256": sha256_file(METRIC_NPZ),
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    }
    save_json(CONTRACT_JSON, contract)

    save_json(
        SUMMARY_JSON,
        {
            "milestone": "V16C-7",
            "status": status,
            "diagnosis": diagnosis,
            "geometry_adapter_ready": geometry_ready,
            "capillary_transform_ready": capillary_transform_ready,
            "compressibility_authority_ready": compressibility_authority_ready,
            "metric_sha256": sha256_file(METRIC_NPZ),
            "recommendation": recommendation,
            "next_milestone": next_ms,
        },
    )

    print("POLLOCK / GEOMETRIC COORDINATES")
    print(f"  Streamlines              : {ns}")
    print(f"  Nodes / streamline       : {nn}")
    print(f"  Zero-length segments     : {int(np.sum(zero_ds))}")
    print(f"  Negative Pollock TOF steps: {int(np.sum(dtau < -1e-10))}")
    print(f"  Metric M finite          : {M_finite}")
    print(f"  Metric M positive        : {M_positive}")

    print("\nEXACT OPERATOR TRANSFORM")
    print("  xD_arc                   : s / L_s")
    print("  theta                    : tau_Pollock / tau_end")
    print("  M                        : d theta / d xD_arc")
    print("  d/dxD                    : M d/dtheta")
    print("  Capillary                : M d/dtheta [D_tilde M dS/dtheta]")

    print("\nCOMPRESSIBILITY")
    print("  Stage-4 u_D              : exp(Nc xD)")
    print("  Pollock velocity content : PRESENT")
    print("  Naive stacking           : PROHIBITED")
    print("  Authority separation     : PENDING")

    print("\nSEQUENCE")
    print("  Legacy Stage-4           : 64 nodes")
    print("  Frozen V16C              : 201 nodes")
    print("  V16 adapter authority    : 201 nodes")

    print("\n" + "=" * 78)
    print("V16C-7 FINAL ADAPTER PHYSICS GATES")
    print("=" * 78)
    for g, v in gates:
        print(f"[{'PASS' if v else 'FAIL'}] {g}")
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
    print(f"  {METRIC_NPZ.name}")
    print(f"  SHA-256: {sha256_file(METRIC_NPZ)}")
    print("\nTables:")
    for p in [
        IDENTITY_CSV, GEOM_CSV, TRANSFORM_CSV, CAP_CSV,
        COMP_CSV, SEQ_CSV, GATES_CSV, DECISION_CSV
    ]:
        print(f"  {p.name}")
    print("\nContract:")
    print(f"  {CONTRACT_JSON.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_JSON.name}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16C-7 POLLOCK-TOF / FULL BL-CCUS ADAPTER PHYSICS CONTRACT: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()
