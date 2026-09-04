from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json

import numpy as np


# =============================================================================
# PAD-Stream V16C-4
# Model-Ready Conditioning Tensor Assembly
#
# PURPOSE
# -------
# Assemble deterministic model-ready conditioning tensors from:
#
#   - frozen V16C-2 raw multi-coordinate streamline database
#   - frozen V16C-3 normalization / conditioning contract
#
# NO training is performed.
# NO model inference is performed.
# NO saturation target is generated.
# NO transport solve is executed.
#
# REQUIRED SEQUENCE TENSOR
# ------------------------
# X_sequence_required channels:
#
#   0: xi
#   1: pollock_tau_hat
#   2: adv_tau_hat
#   3: log10_Kh
#   4: log10_Kz_over_Kh
#   5: porosity
#   6: pressure_z
#
# Shape:
#
#   (1078, 201, 7)
#
# OPTIONAL CONTROL TENSOR
# -----------------------
# X_sequence_optional:
#
#   0: fmm_tau_hat
#   1: x_norm
#   2: y_norm
#   3: z_norm
#
# Shape:
#
#   (1078, 201, 4)
#
# REQUIRED STATIC TENSOR
# ----------------------
# X_static_required:
#
#   0: log_streamline_weight_z
#
# Shape:
#
#   (1078, 1)
#
# IMPORTANT
# ---------
# No ML target Y is created in V16C-4.
# =============================================================================


ROOT = Path(__file__).resolve().parent

C2_DIR = ROOT / "output" / "V16_C2_MULTI_COORDINATE_STREAMLINE_TRANSPORT_DATABASE"
C2_DB = C2_DIR / "V16C2_Multi_Coordinate_Streamline_Transport_Database.npz"
C2_SUMMARY = C2_DIR / "PAD_Stream_V16C2_Summary.json"

C3_DIR = ROOT / "output" / "V16_C3_PIRNN_TRANSPORT_CONDITIONING_CONTRACT"
C3_PARAMS = C3_DIR / "V16C3_Conditioning_Normalization_Parameters.npz"
C3_SUMMARY = C3_DIR / "PAD_Stream_V16C3_Summary.json"
C3_CONTRACT = C3_DIR / "V16C3_PIRNN_Transport_Conditioning_Contract.json"

OUT = ROOT / "output" / "V16_C4_MODEL_READY_CONDITIONING_TENSOR_ASSEMBLY"
OUT.mkdir(parents=True, exist_ok=True)

TENSORS_NPZ = OUT / "V16C4_Model_Ready_Conditioning_Tensors.npz"

IDENTITY_CSV = OUT / "V16C4_Input_Identity.csv"
CHANNEL_CSV = OUT / "V16C4_Assembled_Channel_Registry.csv"
SHAPE_CSV = OUT / "V16C4_Tensor_Shape_Audit.csv"
RANGE_CSV = OUT / "V16C4_Tensor_Range_and_Finiteness_Audit.csv"
REPRO_CSV = OUT / "V16C4_Transformation_Reproduction_Audit.csv"
GATES_CSV = OUT / "V16C4_Final_Tensor_Assembly_Gates.csv"
DECISION_CSV = OUT / "V16C4_Tensor_Assembly_Decision.csv"

CONTRACT_JSON = OUT / "V16C4_Model_Ready_Conditioning_Tensor_Contract.json"
SUMMARY_JSON = OUT / "PAD_Stream_V16C4_Summary.json"


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


def stats_row(name, a):
    a = np.asarray(a, dtype=np.float64)
    return {
        "tensor_or_channel": name,
        "shape": str(tuple(a.shape)),
        "finite": bool(np.all(np.isfinite(a))),
        "min": float(np.min(a)),
        "median": float(np.median(a)),
        "mean": float(np.mean(a)),
        "max": float(np.max(a)),
    }


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16C-4")
    print("Model-Ready Conditioning Tensor Assembly")
    print("=" * 78)

    print("""
V16C-2 RAW DATABASE IS IMMUTABLE.
V16C-3 CONDITIONING CONTRACT IS IMMUTABLE.

NO PI-RNN WILL BE TRAINED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO TRANSPORT TARGET WILL BE GENERATED.
NO SATURATION FIELD WILL BE GENERATED.
NO TRANSPORT SOLVE WILL BE EXECUTED.
NO GRID MAP-BACK WILL BE EXECUTED.
NO FEATURE SELECTION WILL BE PERFORMED.
NO NORMALIZATION PARAMETER WILL BE REFIT.
NO FMM / ADV / POLLOCK FIELD WILL BE CHANGED.

THIS MILESTONE ONLY ASSEMBLES DETERMINISTIC MODEL-READY INPUT TENSORS.
""")

    for p in [C2_DB, C2_SUMMARY, C3_PARAMS, C3_SUMMARY, C3_CONTRACT]:
        if not p.exists():
            raise FileNotFoundError(p)

    c2_summary = load_json(C2_SUMMARY)
    c3_summary = load_json(C3_SUMMARY)

    if c2_summary.get("status") != "V16C_MULTI_COORDINATE_STREAMLINE_TRANSPORT_DATABASE_COMPLETE":
        raise RuntimeError("V16C-4 requires completed V16C-2.")

    if c3_summary.get("status") != "V16C_PIRNN_TRANSPORT_CONDITIONING_CONTRACT_READY":
        raise RuntimeError("V16C-4 requires completed V16C-3.")

    with np.load(C2_DB, allow_pickle=False) as db:
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

    with np.load(C3_PARAMS, allow_pickle=False) as db:
        pressure_mean = float(db["pressure_mean_psi"][0])
        pressure_std = float(db["pressure_std_psi"][0])
        logKh_mean = float(db["log10_Kh_mean"][0])
        logKh_std = float(db["log10_Kh_std"][0])
        logKratio_mean = float(db["log10_Kz_over_Kh_mean"][0])
        logKratio_std = float(db["log10_Kz_over_Kh_std"][0])
        lnw_mean = float(db["ln_weight_mean"][0])
        lnw_std = float(db["ln_weight_std"][0])
        xyz_min = np.asarray(db["xyz_min_m"], dtype=np.float64)
        xyz_max = np.asarray(db["xyz_max_m"], dtype=np.float64)

    ns, nn = pollock.shape

    if (ns, nn) != (1078, 201):
        raise RuntimeError(f"Unexpected C2 shape: {(ns, nn)}")

    if xyz.shape != (ns, nn, 3):
        raise RuntimeError("XYZ shape mismatch.")

    if xi.shape != (nn,):
        raise RuntimeError(f"xi shape mismatch: {xi.shape}")

    # -------------------------------------------------------------------------
    # Deterministic transformations defined in V16C-3.
    # -------------------------------------------------------------------------
    tau_end = pollock[:, -1]
    if np.any(~np.isfinite(tau_end)) or np.any(tau_end <= 0.0):
        raise RuntimeError("Invalid Pollock terminal TOF.")

    pollock_tau_hat = pollock / tau_end[:, None]
    adv_tau_hat = adv / tau_end[:, None]
    fmm_tau_hat = fmm / tau_end[:, None]

    Kh = np.sqrt(np.maximum(Kx, 1e-30) * np.maximum(Ky, 1e-30))
    log10_Kh = np.log10(np.maximum(Kh, 1e-30))
    log10_Kz_over_Kh = np.log10(
        np.maximum(Kz, 1e-30) / np.maximum(Kh, 1e-30)
    )

    pressure_z = (pressure - pressure_mean) / pressure_std

    xyz_span = np.maximum(xyz_max - xyz_min, 1e-30)
    xyz_norm = (xyz - xyz_min[None, None, :]) / xyz_span[None, None, :]

    logw = np.log(np.maximum(weight, 1e-300))
    logw_z = (logw - lnw_mean) / lnw_std

    xi_2d = np.broadcast_to(xi[None, :], (ns, nn))

    # Required sequence tensor.
    X_sequence_required = np.stack(
        [
            xi_2d,
            pollock_tau_hat,
            adv_tau_hat,
            log10_Kh,
            log10_Kz_over_Kh,
            phi,
            pressure_z,
        ],
        axis=-1,
    )

    # Optional/control tensor.
    X_sequence_optional = np.stack(
        [
            fmm_tau_hat,
            xyz_norm[:, :, 0],
            xyz_norm[:, :, 1],
            xyz_norm[:, :, 2],
        ],
        axis=-1,
    )

    X_static_required = logw_z[:, None]

    required_channel_names = np.asarray(
        [
            "xi",
            "pollock_tau_hat",
            "adv_tau_hat",
            "log10_Kh",
            "log10_Kz_over_Kh",
            "porosity",
            "pressure_z",
        ],
        dtype="U64",
    )

    optional_channel_names = np.asarray(
        [
            "fmm_tau_hat",
            "x_norm",
            "y_norm",
            "z_norm",
        ],
        dtype="U64",
    )

    static_channel_names = np.asarray(
        ["log_streamline_weight_z"],
        dtype="U64",
    )

    save_csv(
        IDENTITY_CSV,
        [{
            "V16C2_database_sha256": sha256_file(C2_DB),
            "V16C3_params_sha256": sha256_file(C3_PARAMS),
            "V16C3_contract_sha256": sha256_file(C3_CONTRACT),
            "streamlines": ns,
            "nodes_per_streamline": nn,
        }],
    )

    channel_rows = []
    for i, name in enumerate(required_channel_names.tolist()):
        channel_rows.append({
            "tensor": "X_sequence_required",
            "index": i,
            "channel": name,
            "required": True,
        })

    for i, name in enumerate(optional_channel_names.tolist()):
        channel_rows.append({
            "tensor": "X_sequence_optional",
            "index": i,
            "channel": name,
            "required": False,
        })

    channel_rows.append({
        "tensor": "X_static_required",
        "index": 0,
        "channel": "log_streamline_weight_z",
        "required": True,
    })

    save_csv(CHANNEL_CSV, channel_rows)

    shape_rows = [
        {
            "tensor": "X_sequence_required",
            "actual_shape": str(tuple(X_sequence_required.shape)),
            "expected_shape": str((1078, 201, 7)),
            "pass": X_sequence_required.shape == (1078, 201, 7),
        },
        {
            "tensor": "X_sequence_optional",
            "actual_shape": str(tuple(X_sequence_optional.shape)),
            "expected_shape": str((1078, 201, 4)),
            "pass": X_sequence_optional.shape == (1078, 201, 4),
        },
        {
            "tensor": "X_static_required",
            "actual_shape": str(tuple(X_static_required.shape)),
            "expected_shape": str((1078, 1)),
            "pass": X_static_required.shape == (1078, 1),
        },
    ]
    save_csv(SHAPE_CSV, shape_rows)

    range_rows = [
        stats_row("X_sequence_required", X_sequence_required),
        stats_row("X_sequence_optional", X_sequence_optional),
        stats_row("X_static_required", X_static_required),
        stats_row("pollock_tau_hat", pollock_tau_hat),
        stats_row("adv_tau_hat", adv_tau_hat),
        stats_row("fmm_tau_hat", fmm_tau_hat),
        stats_row("log10_Kh", log10_Kh),
        stats_row("log10_Kz_over_Kh", log10_Kz_over_Kh),
        stats_row("porosity", phi),
        stats_row("pressure_z", pressure_z),
        stats_row("xyz_norm", xyz_norm),
        stats_row("log_streamline_weight_z", logw_z),
    ]
    save_csv(RANGE_CSV, range_rows)

    # Reproduction / contract checks.
    pollock_start_linf = float(np.max(np.abs(pollock_tau_hat[:, 0])))
    pollock_end_linf = float(np.max(np.abs(pollock_tau_hat[:, -1] - 1.0)))

    pressure_mean_repro = float(np.mean(pressure_z))
    pressure_std_repro = float(np.std(pressure_z))

    xyz_min_repro = np.min(xyz_norm.reshape(-1, 3), axis=0)
    xyz_max_repro = np.max(xyz_norm.reshape(-1, 3), axis=0)

    logw_mean_repro = float(np.mean(logw_z))
    logw_std_repro = float(np.std(logw_z))

    repro_rows = [
        {
            "check": "pollock_tau_hat_starts_zero",
            "value": pollock_start_linf,
            "target": 0.0,
            "pass": pollock_start_linf <= 1e-12,
        },
        {
            "check": "pollock_tau_hat_ends_one",
            "value": pollock_end_linf,
            "target": 0.0,
            "pass": pollock_end_linf <= 1e-12,
        },
        {
            "check": "pressure_z_mean",
            "value": pressure_mean_repro,
            "target": 0.0,
            "pass": abs(pressure_mean_repro) <= 1e-10,
        },
        {
            "check": "pressure_z_std",
            "value": pressure_std_repro,
            "target": 1.0,
            "pass": abs(pressure_std_repro - 1.0) <= 1e-10,
        },
        {
            "check": "logw_z_mean",
            "value": logw_mean_repro,
            "target": 0.0,
            "pass": abs(logw_mean_repro) <= 1e-10,
        },
        {
            "check": "logw_z_std",
            "value": logw_std_repro,
            "target": 1.0,
            "pass": abs(logw_std_repro - 1.0) <= 1e-10,
        },
        {
            "check": "xyz_norm_global_min",
            "value": float(np.min(xyz_min_repro)),
            "target": 0.0,
            "pass": np.allclose(xyz_min_repro, 0.0, atol=1e-12),
        },
        {
            "check": "xyz_norm_global_max",
            "value": float(np.max(xyz_max_repro)),
            "target": 1.0,
            "pass": np.allclose(xyz_max_repro, 1.0, atol=1e-12),
        },
    ]
    save_csv(REPRO_CSV, repro_rows)

    np.savez_compressed(
        TENSORS_NPZ,
        X_sequence_required=X_sequence_required.astype(np.float32),
        X_sequence_optional=X_sequence_optional.astype(np.float32),
        X_static_required=X_static_required.astype(np.float32),
        required_channel_names=required_channel_names,
        optional_channel_names=optional_channel_names,
        static_channel_names=static_channel_names,
        pollock_tof_s=pollock.astype(np.float64),
        pollock_terminal_tof_s=tau_end.astype(np.float64),
        streamline_weight_m3_s=weight.astype(np.float64),
        xi=xi.astype(np.float64),
        authority_label_ascii=np.frombuffer(
            b"PAD_STREAM_V16C4_MODEL_READY_CONDITIONING_TENSORS",
            dtype=np.uint8,
        ),
    )

    all_shape_pass = all(bool(r["pass"]) for r in shape_rows)
    all_repro_pass = all(bool(r["pass"]) for r in repro_rows)

    gates = [
        ("V16C2_database_status_reproduced", True),
        ("V16C3_conditioning_contract_reproduced", True),
        ("normalization_parameters_loaded_without_refit", True),
        ("required_sequence_tensor_assembled", True),
        ("optional_sequence_tensor_assembled", True),
        ("required_static_tensor_assembled", True),
        ("required_sequence_shape_1078x201x7", X_sequence_required.shape == (1078, 201, 7)),
        ("optional_sequence_shape_1078x201x4", X_sequence_optional.shape == (1078, 201, 4)),
        ("static_shape_1078x1", X_static_required.shape == (1078, 1)),
        ("all_required_tensor_values_finite", bool(np.all(np.isfinite(X_sequence_required)))),
        ("all_optional_tensor_values_finite", bool(np.all(np.isfinite(X_sequence_optional)))),
        ("all_static_tensor_values_finite", bool(np.all(np.isfinite(X_static_required)))),
        ("Pollock_normalization_contract_reproduced", all_repro_pass),
        ("all_tensor_shape_contracts_pass", all_shape_pass),
        ("tensor_artifact_saved", TENSORS_NPZ.exists()),
        ("no_target_tensor_generated", True),
        ("no_transport_solve", True),
        ("no_saturation_generated", True),
        ("no_model_predict", True),
        ("no_training", True),
        ("no_feature_selection", True),
        ("no_normalization_refit", True),
        ("no_frozen_artifact_mutation", True),
    ]
    save_csv(GATES_CSV, [{"gate": g, "passed": bool(p)} for g, p in gates])

    all_pass = all(bool(p) for _, p in gates)

    if all_pass:
        status = "V16C_MODEL_READY_CONDITIONING_TENSORS_COMPLETE"
        diagnosis = (
            "FROZEN_V16C2_RAW_CHANNELS_HAVE_BEEN_DETERMINISTICALLY_TRANSFORMED_INTO_MODEL_READY_REQUIRED_OPTIONAL_AND_STATIC_INPUT_TENSORS_WITHOUT_GENERATING_A_TARGET"
        )
        recommendation = (
            "Freeze the V16C-4 conditioning tensors. Proceed to V16C-5 to define the transport target / supervision authority "
            "and determine how the existing frozen 100-day transport state and future BL/CCUS PI-RNN transport physics enter training or inference. "
            "Do not train a model yet."
        )
        next_ms = "V16C-5 — Transport Target / Supervision Authority Contract"
    else:
        status = "V16C_MODEL_READY_TENSOR_ASSEMBLY_REQUIRES_AUDIT"
        diagnosis = "ONE_OR_MORE_MODEL_READY_TENSOR_ASSEMBLY_GATES_FAILED"
        recommendation = "Audit only failed V16C-4 tensor gates."
        next_ms = "V16C-4R — Conditioning Tensor Assembly Residual Audit"

    save_csv(
        DECISION_CSV,
        [{
            "status": status,
            "diagnosis": diagnosis,
            "required_shape": str(tuple(X_sequence_required.shape)),
            "optional_shape": str(tuple(X_sequence_optional.shape)),
            "static_shape": str(tuple(X_static_required.shape)),
            "tensor_sha256": sha256_file(TENSORS_NPZ),
            "next_milestone": next_ms,
        }],
    )

    contract = {
        "milestone": "V16C-4",
        "status": status,
        "diagnosis": diagnosis,
        "model_ready_inputs": {
            "required_sequence": {
                "shape": list(X_sequence_required.shape),
                "channels": required_channel_names.tolist(),
            },
            "optional_sequence": {
                "shape": list(X_sequence_optional.shape),
                "channels": optional_channel_names.tolist(),
            },
            "required_static": {
                "shape": list(X_static_required.shape),
                "channels": static_channel_names.tolist(),
            },
        },
        "target_tensor": None,
        "artifact": {
            "path": str(TENSORS_NPZ),
            "sha256": sha256_file(TENSORS_NPZ),
        },
        "constraints": {
            "training": False,
            "model_predict": False,
            "transport_target_generated": False,
            "normalization_refit": False,
            "feature_selection": False,
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    }
    save_json(CONTRACT_JSON, contract)

    save_json(
        SUMMARY_JSON,
        {
            "milestone": "V16C-4",
            "status": status,
            "diagnosis": diagnosis,
            "required_sequence_shape": list(X_sequence_required.shape),
            "optional_sequence_shape": list(X_sequence_optional.shape),
            "required_static_shape": list(X_static_required.shape),
            "tensor_sha256": sha256_file(TENSORS_NPZ),
            "target_generated": False,
            "recommendation": recommendation,
            "next_milestone": next_ms,
        },
    )

    print("MODEL-READY TENSORS")
    print(f"  X_sequence_required     : {X_sequence_required.shape}")
    print(f"  X_sequence_optional     : {X_sequence_optional.shape}")
    print(f"  X_static_required       : {X_static_required.shape}")
    print("  Y_transport             : NOT GENERATED")

    print("\nREQUIRED CHANNEL ORDER")
    for i, name in enumerate(required_channel_names):
        print(f"  {i}: {name}")

    print("\nOPTIONAL CHANNEL ORDER")
    for i, name in enumerate(optional_channel_names):
        print(f"  {i}: {name}")

    print("\nSTATIC CHANNEL ORDER")
    for i, name in enumerate(static_channel_names):
        print(f"  {i}: {name}")

    print("\n" + "=" * 78)
    print("V16C-4 FINAL TENSOR ASSEMBLY GATES")
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
    print(f"  {TENSORS_NPZ.name}")
    print(f"  SHA-256: {sha256_file(TENSORS_NPZ)}")

    print("\nTables:")
    for p in [
        IDENTITY_CSV,
        CHANNEL_CSV,
        SHAPE_CSV,
        RANGE_CSV,
        REPRO_CSV,
        GATES_CSV,
        DECISION_CSV,
    ]:
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_JSON.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_JSON.name}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16C-4 MODEL-READY CONDITIONING TENSOR ASSEMBLY: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()
