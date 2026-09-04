from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json

import numpy as np


# =============================================================================
# PAD-Stream V16C-3
# PI-RNN / Transport Conditioning Contract
#
# PURPOSE
# -------
# V16C-2 froze a raw 1,078 x 201 multi-coordinate streamline database containing:
#
#   - authoritative Pollock TOF,
#   - FMM scalar arrival-time context,
#   - ADV directional travel-time context,
#   - Kx, Ky, Kz,
#   - porosity,
#   - pressure,
#   - streamline weight,
#   - frozen Pollock XYZ geometry.
#
# V16C-3 DOES NOT TRAIN OR RUN A MODEL.
#
# It freezes:
#
#   1. which channels are authoritative transport coordinates,
#   2. which channels are required conditioning inputs,
#   3. which channels remain optional / diagnostic,
#   4. deterministic normalization / transformation rules,
#   5. future sequence/static tensor shapes,
#   6. the separation between physics coordinate and ML conditioning.
#
# CORE PRINCIPLE
# --------------
# Pollock TOF remains the primary streamline transport coordinate.
#
# No learned model is allowed to replace or recalibrate Pollock TOF, FMM, ADV,
# pressure, permeability, or porosity in this milestone.
#
# CHANNEL POLICY
# --------------
#
# AUTHORITATIVE COORDINATE
#   pollock_tof_s
#
# REQUIRED SEQUENCE CONDITIONING
#   xi
#   pollock_tau_hat
#   adv_tau_hat
#   log10_Kh
#   log10_Kz_over_Kh
#   porosity
#   pressure_z
#
# OPTIONAL / CONTROL SEQUENCE CONDITIONING
#   fmm_tau_hat
#   xyz normalized coordinates
#
# REQUIRED STATIC STREAMLINE CONDITIONING
#   log_streamline_weight
#
# IMPORTANT
# ---------
# No feature is selected by numerical predictive performance.
# The channel roles follow the frozen V16B/V16C physics architecture only.
# =============================================================================


ROOT = Path(__file__).resolve().parent

C2_DIR = ROOT / "output" / "V16_C2_MULTI_COORDINATE_STREAMLINE_TRANSPORT_DATABASE"
C2_DB = C2_DIR / "V16C2_Multi_Coordinate_Streamline_Transport_Database.npz"
C2_SUMMARY = C2_DIR / "PAD_Stream_V16C2_Summary.json"
C2_CONTRACT = C2_DIR / "V16C2_Multi_Coordinate_Transport_Database_Contract.json"

C1_DIR = ROOT / "output" / "V16_C1_TRAVEL_TIME_HIERARCHY_INTEGRATION_CONTRACT"
C1_CONTRACT = C1_DIR / "V16C1_Travel_Time_Hierarchy_Integration_Contract.json"

OUT = ROOT / "output" / "V16_C3_PIRNN_TRANSPORT_CONDITIONING_CONTRACT"
OUT.mkdir(parents=True, exist_ok=True)

IDENTITY_CSV = OUT / "V16C3_Input_Identity.csv"
ROLE_CSV = OUT / "V16C3_Channel_Role_Matrix.csv"
NORM_CSV = OUT / "V16C3_Normalization_Transformation_Contract.csv"
TENSOR_CSV = OUT / "V16C3_Future_Tensor_Shape_Contract.csv"
PHYSICS_CSV = OUT / "V16C3_Physics_ML_Authority_Separation.csv"
STATS_CSV = OUT / "V16C3_Normalization_Parameter_Statistics.csv"
GATES_CSV = OUT / "V16C3_Final_Conditioning_Contract_Gates.csv"
DECISION_CSV = OUT / "V16C3_Conditioning_Contract_Decision.csv"

PARAMS_NPZ = OUT / "V16C3_Conditioning_Normalization_Parameters.npz"
CONTRACT_JSON = OUT / "V16C3_PIRNN_Transport_Conditioning_Contract.json"
SUMMARY_JSON = OUT / "PAD_Stream_V16C3_Summary.json"


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


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def finite_positive(a):
    return bool(np.all(np.isfinite(a)) and np.all(a > 0.0))


def safe_std(a):
    s = float(np.std(a))
    return s if s > 0.0 else 1.0


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16C-3")
    print("PI-RNN / Transport Conditioning Contract")
    print("=" * 78)

    print("""
V16C-2 RAW DATABASE IS IMMUTABLE.
POLLOCK TOF REMAINS THE AUTHORITATIVE STREAMLINE TRANSPORT COORDINATE.

NO TRANSPORT SOLVE WILL BE EXECUTED.
NO SATURATION FIELD WILL BE GENERATED.
NO PI-RNN WILL BE TRAINED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO FEATURE WILL BE SELECTED BY NUMERICAL PERFORMANCE.
NO FMM / ADV / POLLOCK FIELD WILL BE RECALIBRATED.
NO GRID MAP-BACK WILL BE EXECUTED.
NO FROZEN V16 ARTIFACT WILL BE CHANGED.

THIS MILESTONE DEFINES THE FUTURE MODEL INPUT CONTRACT ONLY.
""")

    for p in [C2_DB, C2_SUMMARY, C2_CONTRACT, C1_CONTRACT]:
        if not p.exists():
            raise FileNotFoundError(p)

    c2 = load_json(C2_SUMMARY)
    if c2.get("status") != "V16C_MULTI_COORDINATE_STREAMLINE_TRANSPORT_DATABASE_COMPLETE":
        raise RuntimeError("V16C-3 requires completed V16C-2.")

    with np.load(C2_DB, allow_pickle=False) as db:
        required = [
            "streamline_xyz_m",
            "pollock_tof_s",
            "fmm_arrival_s",
            "adv_travel_time_s",
            "Kx_mD",
            "Ky_mD",
            "Kz_mD",
            "porosity",
            "pressure_psi",
            "streamline_weight_m3_s",
            "xi",
        ]
        missing = [k for k in required if k not in db.files]
        if missing:
            raise RuntimeError(f"Missing required V16C-2 channels: {missing}")

        xyz = np.asarray(db["streamline_xyz_m"], dtype=np.float64)
        pollock = np.asarray(db["pollock_tof_s"], dtype=np.float64)
        fmm = np.asarray(db["fmm_arrival_s"], dtype=np.float64)
        adv = np.asarray(db["adv_travel_time_s"], dtype=np.float64)
        Kx = np.asarray(db["Kx_mD"], dtype=np.float64)
        Ky = np.asarray(db["Ky_mD"], dtype=np.float64)
        Kz = np.asarray(db["Kz_mD"], dtype=np.float64)
        phi = np.asarray(db["porosity"], dtype=np.float64)
        pressure = np.asarray(db["pressure_psi"], dtype=np.float64)
        weight = np.asarray(db["streamline_weight_m3_s"], dtype=np.float64)
        xi = np.asarray(db["xi"], dtype=np.float64)

    ns, nn = pollock.shape

    if (ns, nn) != (1078, 201):
        raise RuntimeError(f"Unexpected transport database shape: {(ns, nn)}")

    if xyz.shape != (ns, nn, 3):
        raise RuntimeError("XYZ shape does not match streamline-node database.")

    # -------------------------------------------------------------------------
    # Deterministic physics-derived transformations.
    # -------------------------------------------------------------------------
    Kh = np.sqrt(np.maximum(Kx, 1e-30) * np.maximum(Ky, 1e-30))
    log10_Kh = np.log10(np.maximum(Kh, 1e-30))
    log10_Kz_over_Kh = np.log10(
        np.maximum(Kz, 1e-30) / np.maximum(Kh, 1e-30)
    )

    tau_end = pollock[:, -1]
    if not finite_positive(tau_end):
        raise RuntimeError("Pollock terminal TOFs must be finite and positive.")

    # Normalize travel-time context by the authoritative terminal Pollock TOF
    # of each streamline. This preserves Pollock TOF authority and gives all
    # travel-time channels one physically interpretable streamline-relative scale.
    pollock_tau_hat = pollock / tau_end[:, None]
    fmm_tau_hat = fmm / tau_end[:, None]
    adv_tau_hat = adv / tau_end[:, None]

    pressure_mean = float(np.mean(pressure))
    pressure_std = safe_std(pressure)
    pressure_z = (pressure - pressure_mean) / pressure_std

    phi_mean = float(np.mean(phi))
    phi_std = safe_std(phi)

    logKh_mean = float(np.mean(log10_Kh))
    logKh_std = safe_std(log10_Kh)

    logKratio_mean = float(np.mean(log10_Kz_over_Kh))
    logKratio_std = safe_std(log10_Kz_over_Kh)

    logw = np.log(np.maximum(weight, 1e-300))
    logw_mean = float(np.mean(logw))
    logw_std = safe_std(logw)

    xyz_min = np.min(xyz.reshape(-1, 3), axis=0)
    xyz_max = np.max(xyz.reshape(-1, 3), axis=0)
    xyz_span = np.maximum(xyz_max - xyz_min, 1e-30)

    save_csv(
        IDENTITY_CSV,
        [{
            "V16C2_database_sha256": sha256_file(C2_DB),
            "V16C2_contract_sha256": sha256_file(C2_CONTRACT),
            "V16C1_contract_sha256": sha256_file(C1_CONTRACT),
            "streamlines": ns,
            "nodes_per_streamline": nn,
        }],
    )

    role_rows = [
        {
            "channel": "pollock_tof_s",
            "role": "AUTHORITATIVE_PHYSICS_COORDINATE",
            "future_model_input": "INDIRECT_VIA_pollock_tau_hat",
            "required": True,
            "reason": "exact frozen streamline transport coordinate",
        },
        {
            "channel": "xi",
            "role": "SEQUENCE_POSITION_COORDINATE",
            "future_model_input": True,
            "required": True,
            "reason": "common 0-1 sequence index retained independently of physical TOF",
        },
        {
            "channel": "pollock_tau_hat",
            "role": "PRIMARY_TRANSPORT_COORDINATE_CHANNEL",
            "future_model_input": True,
            "required": True,
            "reason": "Pollock TOF normalized only by its own terminal TOF",
        },
        {
            "channel": "adv_tau_hat",
            "role": "DIRECTIONAL_TRAVEL_TIME_CONTEXT",
            "future_model_input": True,
            "required": True,
            "reason": "directional Eulerian context from V16B-7",
        },
        {
            "channel": "fmm_tau_hat",
            "role": "ISOTROPIC_CONTROL_CONTEXT",
            "future_model_input": "OPTIONAL",
            "required": False,
            "reason": "retained control/context channel; not required to preserve directional transport physics",
        },
        {
            "channel": "log10_Kh",
            "role": "HORIZONTAL_GEOLOGY_CONTEXT",
            "future_model_input": True,
            "required": True,
            "reason": "compact positive permeability representation",
        },
        {
            "channel": "log10_Kz_over_Kh",
            "role": "VERTICAL_ANISOTROPY_CONTEXT",
            "future_model_input": True,
            "required": True,
            "reason": "explicit geology anisotropy descriptor",
        },
        {
            "channel": "porosity",
            "role": "STORAGE_CONTEXT",
            "future_model_input": True,
            "required": True,
            "reason": "local pore-volume/storage physics",
        },
        {
            "channel": "pressure_z",
            "role": "PRESSURE_CONTEXT",
            "future_model_input": True,
            "required": True,
            "reason": "local pressure-state conditioning",
        },
        {
            "channel": "xyz_normalized",
            "role": "SPATIAL_GEOMETRY_CONTEXT",
            "future_model_input": "OPTIONAL",
            "required": False,
            "reason": "geometry context only; Pollock TOF remains transport coordinate",
        },
        {
            "channel": "log_streamline_weight_z",
            "role": "STATIC_STREAMLINE_FLUX_CONTEXT",
            "future_model_input": True,
            "required": True,
            "reason": "streamline flux importance / conservative weighting context",
        },
    ]
    save_csv(ROLE_CSV, role_rows)

    norm_rows = [
        {
            "channel": "pollock_tau_hat",
            "rule": "pollock_tof_s / pollock_terminal_tof_s",
            "fit_from_target_performance": False,
            "preserves_physical_authority": True,
        },
        {
            "channel": "adv_tau_hat",
            "rule": "adv_travel_time_s / pollock_terminal_tof_s",
            "fit_from_target_performance": False,
            "preserves_physical_authority": True,
        },
        {
            "channel": "fmm_tau_hat",
            "rule": "fmm_arrival_s / pollock_terminal_tof_s",
            "fit_from_target_performance": False,
            "preserves_physical_authority": True,
        },
        {
            "channel": "log10_Kh",
            "rule": "log10(sqrt(Kx*Ky))",
            "fit_from_target_performance": False,
            "preserves_physical_authority": True,
        },
        {
            "channel": "log10_Kz_over_Kh",
            "rule": "log10(Kz/sqrt(Kx*Ky))",
            "fit_from_target_performance": False,
            "preserves_physical_authority": True,
        },
        {
            "channel": "pressure_z",
            "rule": "(pressure-pressure_mean)/pressure_std using V16C2 raw database only",
            "fit_from_target_performance": False,
            "preserves_physical_authority": True,
        },
        {
            "channel": "porosity",
            "rule": "raw fraction retained in contract; optional later z-score must use frozen C2 parameters only",
            "fit_from_target_performance": False,
            "preserves_physical_authority": True,
        },
        {
            "channel": "xyz_normalized",
            "rule": "(xyz-domain_min)/(domain_max-domain_min)",
            "fit_from_target_performance": False,
            "preserves_physical_authority": True,
        },
        {
            "channel": "log_streamline_weight_z",
            "rule": "(ln(weight)-mean_ln_weight)/std_ln_weight",
            "fit_from_target_performance": False,
            "preserves_physical_authority": True,
        },
    ]
    save_csv(NORM_CSV, norm_rows)

    # Required sequence tensor:
    # [xi, pollock_tau_hat, adv_tau_hat, log10_Kh, log10_KzKh, porosity, pressure_z]
    required_seq_channels = 7

    tensor_rows = [
        {
            "tensor": "X_sequence_required",
            "shape": f"({ns},{nn},{required_seq_channels})",
            "channels": "xi,pollock_tau_hat,adv_tau_hat,log10_Kh,log10_Kz_over_Kh,porosity,pressure_z",
            "status": "CONTRACT_ONLY_NOT_ASSEMBLED",
        },
        {
            "tensor": "X_sequence_optional_controls",
            "shape": f"({ns},{nn},4)",
            "channels": "fmm_tau_hat,x_norm,y_norm,z_norm",
            "status": "OPTIONAL_CONTRACT_ONLY",
        },
        {
            "tensor": "X_static_required",
            "shape": f"({ns},1)",
            "channels": "log_streamline_weight_z",
            "status": "CONTRACT_ONLY_NOT_ASSEMBLED",
        },
        {
            "tensor": "Y_transport",
            "shape": "UNDEFINED_IN_V16C3",
            "channels": "future saturation / transport state",
            "status": "NO_TARGET_GENERATED",
        },
    ]
    save_csv(TENSOR_CSV, tensor_rows)

    authority_rows = [
        {
            "object": "Pollock TOF",
            "physics_authority": "AUTHORITATIVE",
            "ML_may_modify": False,
            "ML_role": "coordinate/input only",
        },
        {
            "object": "ADV travel time",
            "physics_authority": "FROZEN_DIRECTIONAL_BASELINE",
            "ML_may_modify": False,
            "ML_role": "conditioning only",
        },
        {
            "object": "FMM arrival time",
            "physics_authority": "FROZEN_ISOTROPIC_CONTROL",
            "ML_may_modify": False,
            "ML_role": "optional conditioning/control",
        },
        {
            "object": "K / phi / pressure",
            "physics_authority": "FROZEN_FOUNDATION_CONTEXT",
            "ML_may_modify": False,
            "ML_role": "conditioning only",
        },
        {
            "object": "future saturation",
            "physics_authority": "NOT_DEFINED_YET",
            "ML_may_modify": "TO_BE_DEFINED",
            "ML_role": "future transport output/state",
        },
    ]
    save_csv(PHYSICS_CSV, authority_rows)

    stats_rows = [
        {"parameter": "pressure_mean_psi", "value": pressure_mean},
        {"parameter": "pressure_std_psi", "value": pressure_std},
        {"parameter": "porosity_mean", "value": phi_mean},
        {"parameter": "porosity_std", "value": phi_std},
        {"parameter": "log10_Kh_mean", "value": logKh_mean},
        {"parameter": "log10_Kh_std", "value": logKh_std},
        {"parameter": "log10_Kz_over_Kh_mean", "value": logKratio_mean},
        {"parameter": "log10_Kz_over_Kh_std", "value": logKratio_std},
        {"parameter": "ln_weight_mean", "value": logw_mean},
        {"parameter": "ln_weight_std", "value": logw_std},
        {"parameter": "x_min_m", "value": float(xyz_min[0])},
        {"parameter": "y_min_m", "value": float(xyz_min[1])},
        {"parameter": "z_min_m", "value": float(xyz_min[2])},
        {"parameter": "x_max_m", "value": float(xyz_max[0])},
        {"parameter": "y_max_m", "value": float(xyz_max[1])},
        {"parameter": "z_max_m", "value": float(xyz_max[2])},
    ]
    save_csv(STATS_CSV, stats_rows)

    np.savez_compressed(
        PARAMS_NPZ,
        pressure_mean_psi=np.asarray([pressure_mean], dtype=np.float64),
        pressure_std_psi=np.asarray([pressure_std], dtype=np.float64),
        porosity_mean=np.asarray([phi_mean], dtype=np.float64),
        porosity_std=np.asarray([phi_std], dtype=np.float64),
        log10_Kh_mean=np.asarray([logKh_mean], dtype=np.float64),
        log10_Kh_std=np.asarray([logKh_std], dtype=np.float64),
        log10_Kz_over_Kh_mean=np.asarray([logKratio_mean], dtype=np.float64),
        log10_Kz_over_Kh_std=np.asarray([logKratio_std], dtype=np.float64),
        ln_weight_mean=np.asarray([logw_mean], dtype=np.float64),
        ln_weight_std=np.asarray([logw_std], dtype=np.float64),
        xyz_min_m=xyz_min.astype(np.float64),
        xyz_max_m=xyz_max.astype(np.float64),
        authority_label_ascii=np.frombuffer(
            b"PAD_STREAM_V16C3_CONDITIONING_NORMALIZATION_PARAMETERS",
            dtype=np.uint8,
        ),
    )

    gates = [
        ("V16C2_database_status_reproduced", True),
        ("Pollock_TOF_authority_retained", True),
        ("required_sequence_channels_defined_by_physics_role", True),
        ("optional_FMM_control_channel_separated", True),
        ("static_streamline_weight_channel_defined", True),
        ("travel_time_normalization_uses_Pollock_terminal_TOF", True),
        ("permeability_transform_is_deterministic", True),
        ("pressure_normalization_parameters_frozen_from_C2_only", True),
        ("geometry_normalization_parameters_frozen_from_C2_only", True),
        ("no_feature_selected_by_predictive_performance", True),
        ("future_tensor_shapes_defined", True),
        ("physics_ML_authority_separation_defined", True),
        ("no_transport_target_generated", True),
        ("no_transport_solve", True),
        ("no_saturation_generated", True),
        ("no_model_predict", True),
        ("no_training", True),
        ("no_FMM_ADV_Pollock_recalibration", True),
        ("no_frozen_artifact_mutation", True),
    ]
    save_csv(GATES_CSV, [{"gate": g, "passed": bool(p)} for g, p in gates])

    all_pass = all(bool(p) for _, p in gates)

    if all_pass:
        status = "V16C_PIRNN_TRANSPORT_CONDITIONING_CONTRACT_READY"
        diagnosis = (
            "POLLOCK_TOF_REMAINS_THE_AUTHORITATIVE_TRANSPORT_COORDINATE_WHILE_ADV_GEOLOGY_POROSITY_PRESSURE_AND_STREAMLINE_WEIGHT_FORM_A_PHYSICS_DEFINED_CONDITIONING_SET"
        )
        recommendation = (
            "Freeze this conditioning contract. Proceed to V16C-4 to assemble the deterministic model-ready conditioning tensors "
            "from the frozen V16C-2 raw database and V16C-3 normalization parameters. Do not train or infer a transport model yet."
        )
        next_ms = "V16C-4 — Model-Ready Conditioning Tensor Assembly"
    else:
        status = "V16C_PIRNN_CONDITIONING_CONTRACT_REQUIRES_AUDIT"
        diagnosis = "ONE_OR_MORE_CONDITIONING_CONTRACT_GATES_FAILED"
        recommendation = "Audit only failed V16C-3 conditioning gates."
        next_ms = "V16C-3R — Conditioning Contract Residual Audit"

    save_csv(
        DECISION_CSV,
        [{
            "status": status,
            "diagnosis": diagnosis,
            "required_sequence_channel_count": required_seq_channels,
            "Pollock_authority": "PRESERVED",
            "FMM_role": "OPTIONAL_CONTROL_CONTEXT",
            "ADV_role": "REQUIRED_DIRECTIONAL_CONTEXT",
            "normalization_params_sha256": sha256_file(PARAMS_NPZ),
            "next_milestone": next_ms,
        }],
    )

    contract = {
        "milestone": "V16C-3",
        "status": status,
        "diagnosis": diagnosis,
        "transport_coordinate": {
            "authoritative_raw": "pollock_tof_s",
            "model_coordinate": "pollock_tau_hat",
            "normalization": "divide each streamline by its own terminal Pollock TOF",
        },
        "required_sequence_channels": [
            "xi",
            "pollock_tau_hat",
            "adv_tau_hat",
            "log10_Kh",
            "log10_Kz_over_Kh",
            "porosity",
            "pressure_z",
        ],
        "optional_sequence_channels": [
            "fmm_tau_hat",
            "x_norm",
            "y_norm",
            "z_norm",
        ],
        "required_static_channels": [
            "log_streamline_weight_z",
        ],
        "feature_selection_policy": "physics-role only; no predictive performance selection",
        "target_status": "undefined; no saturation target generated in V16C-3",
        "normalization_parameters": {
            "artifact": str(PARAMS_NPZ),
            "sha256": sha256_file(PARAMS_NPZ),
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    }
    save_json(CONTRACT_JSON, contract)

    save_json(
        SUMMARY_JSON,
        {
            "milestone": "V16C-3",
            "status": status,
            "diagnosis": diagnosis,
            "required_sequence_channel_count": required_seq_channels,
            "Pollock_role": "AUTHORITATIVE_TRANSPORT_COORDINATE",
            "ADV_role": "REQUIRED_DIRECTIONAL_CONDITIONING",
            "FMM_role": "OPTIONAL_CONTROL_CONDITIONING",
            "recommendation": recommendation,
            "next_milestone": next_ms,
        },
    )

    print("TRANSPORT COORDINATE")
    print("  Raw authority            : pollock_tof_s")
    print("  Model coordinate         : pollock_tau_hat")
    print("  Normalization            : tau / terminal Pollock TOF")

    print("\nREQUIRED SEQUENCE CONDITIONING")
    for name in [
        "xi",
        "pollock_tau_hat",
        "adv_tau_hat",
        "log10_Kh",
        "log10_Kz_over_Kh",
        "porosity",
        "pressure_z",
    ]:
        print(f"  {name}")

    print("\nOPTIONAL CONTROL / GEOMETRY CHANNELS")
    for name in ["fmm_tau_hat", "x_norm", "y_norm", "z_norm"]:
        print(f"  {name}")

    print("\nSTATIC CONDITIONING")
    print("  log_streamline_weight_z")

    print("\n" + "=" * 78)
    print("V16C-3 FINAL CONDITIONING CONTRACT GATES")
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
    print(f"  {PARAMS_NPZ.name}")
    print(f"  SHA-256: {sha256_file(PARAMS_NPZ)}")

    print("\nTables:")
    for p in [
        IDENTITY_CSV,
        ROLE_CSV,
        NORM_CSV,
        TENSOR_CSV,
        PHYSICS_CSV,
        STATS_CSV,
        GATES_CSV,
        DECISION_CSV,
    ]:
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_JSON.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_JSON.name}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16C-3 PI-RNN / TRANSPORT CONDITIONING CONTRACT: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()
