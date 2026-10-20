#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import subprocess
from pathlib import Path
from typing import Any

import numpy as np


MILESTONE = "POSTV16-AV3-A3"
PROTOCOL_ID = (
    "POSTV16_AV3_A3_SPATIAL_COREY_RELPERM_TRANSPORT_TEACHER_DATASET_"
    "PHYSICS_RESIDUAL_AND_13CHANNEL_PIRNN_PROTOCOL_FREEZE_V1"
)

STATUS_PASS = (
    "AV3A3_SPATIAL_COREY_RELPERM_TRANSPORT_TEACHER_RESIDUAL_AND_"
    "13CHANNEL_PIRNN_PROTOCOL_PROSPECTIVELY_FROZEN_NO_TEACHER_OR_TRAINING_EXECUTION"
)

STATUS_BLOCKED = "AV3A3_PROTOCOL_FREEZE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_A2_COMMIT = "5fcdc4041be8592be54a4fe548400921cc9afd30"

# Exact source lineage.
A2 = "PAD_Stream_POSTV16_AV3_A2_Corey_Relperm_Field_Realization_Certification_and_Streamline_Sampling.py"
A2_BLOB = "e7d4f1b1e69ea3e756c4f41d7edb57e2ffd87d7b"

AV2A3 = "PAD_Stream_POSTV16_AV2_A3_Variable_Porosity_Teacher_Dataset_and_PIRNN_Protocol.py"
AV2A3_BLOB = "9b209abc3a2abb905b9250a16344e52160e61c47"

C20 = "PAD_Stream_V16C20_Stage4_PIRNN_to_V16_Training_Interface_and_Architecture_Binding_Contract.py"
C20_BLOB = "70b073faafd76f71c2c97a2df031592f05f6cf9f"

C21 = "PAD_Stream_V16C21_PIRNN_Training_Objective_Hyperparameter_and_Model_Selection_Authority_Contract.py"
C21_BLOB = "7a24f1af9ce161d7ae1570f91556df8c8f19184c"

C25 = "PAD_Stream_V16C25_Differentiable_Pollock_Full_Physics_Residual_Boundary_Mask_and_Physics_Loss_Weight_Authority_Contract.py"
C25_BLOB = "0a4740b95c2b5e5d15db3137414e663e1e9b6282"

C26 = "PAD_Stream_V16C26_EXP2_Physics_Informed_Training_Execution_Best_Validation_Checkpoint_and_Locked_Test_Evaluation.py"
C26_BLOB = "62e19e6b502fb3ab101a2589251c26b5f9ad9031"

STAGE4 = "pi_rnn_stage4_full_godunov.py"
STAGE4_BLOB = "0c276317a5d8487c190c7185908b228544c33073"

SOURCE_BLOBS = {
    A2: A2_BLOB,
    AV2A3: AV2A3_BLOB,
    C20: C20_BLOB,
    C21: C21_BLOB,
    C25: C25_BLOB,
    C26: C26_BLOB,
    STAGE4: STAGE4_BLOB,
}

BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"

A2_REL = BASE_AV3 / "POSTV16_AV3_A2_Corey_Relperm_Field_Realization_Certification_and_Streamline_Sampling"
A2_SUMMARY = "PAD_Stream_POSTV16_AV3_A2_Summary.json"
A2_DECISION = "POSTV16_AV3_A2_Decision_Contract.json"
A2_DIAG = "POSTV16_AV3_A2_By_Realization_Diagnostics.csv"
A2_SAMPLING = "POSTV16_AV3_A2_Streamline_Sampling_Audit.csv"
A2_MANIFEST = "POSTV16_AV3_A2_Artifact_Manifest.csv"

A2_STATUS = (
    "AV3A2_FROZEN_COREY_RELPERM_REALIZATIONS_GENERATED_CERTIFIED_"
    "AND_SAMPLED_TO_FROZEN_AV2_STREAMLINES_PASS"
)

OUT_REL = BASE_AV3 / "POSTV16_AV3_A3_Transport_Teacher_Residual_and_PIRNN_Protocol_Freeze"
BLOCK_REL = BASE_AV3 / "POSTV16_AV3_A3_BLOCKED"

GRID = (15, 50, 50)
NSL = 1078
NN = 201
NT = 9
DAYS = [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0]

REALIZATIONS = [
    ("AV3CR0001", "AV2PHI0001", "TRAIN"),
    ("AV3CR0002", "AV2PHI0002", "TRAIN"),
    ("AV3CR0003", "AV2PHI0003", "VALIDATION"),
    ("AV3CR0004", "AV2PHI0004", "LOCKED_OOD_TEST"),
]

VARIABLE_PARAMETERS = ["nw", "no", "krw_max", "kro_max"]

SWC = 0.20
SOR = 0.20
SW_INIT = SWC + 1.0e-3
SW_INJ = 1.0 - SOR - 1.0e-3
MU_W = 0.5
MU_O = 5.0
PE_C = 22.0
LAMBDA_C = 2.0
CFL = 0.25
EPS = 1.0e-12

AV2_CHANNELS = [
    "xi",
    "pollock_tau_hat",
    "adv_tau_hat",
    "log10_Kh",
    "log10_Kz_over_Kh",
    "porosity",
    "pressure_z",
    "target_time_hat",
    "target_eta_sequence",
]

NEW_CHANNELS = [
    "nw_hat",
    "no_hat",
    "krw_max_hat",
    "kro_max_hat",
]

AV3_CHANNELS = AV2_CHANNELS + NEW_CHANNELS

HIDDEN_UNITS = 64
LSTM_LAYERS = 2
INPUT_CHANNELS = 13
MODEL_PARAMETERS = 53057

TRAINING_SEED = 16021
BATCH_SIZE = 64
MAX_EPOCHS = 300
INITIAL_LR = 1.0e-3
EARLY_STOP_PATIENCE = 30
EARLY_STOP_MIN_DELTA = 1.0e-6
LR_FACTOR = 0.5
LR_PATIENCE = 10
MIN_LR = 1.0e-6
LAMBDA_DATA = 1.0
LAMBDA_PHYS = 0.01
R0 = 1.0

TRAIN_PROFILES = 2 * NT * NSL
VAL_PROFILES = NT * NSL
OOD_PREDICTOR_PROFILES = NT * NSL
TRAIN_PHYSICS_PAIRS = 2 * (NT - 1) * NSL
VAL_PHYSICS_PAIRS = (NT - 1) * NSL


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git_text(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


def git_blob(path: Path, root: Path) -> str:
    return git_text(root, "hash-object", str(path))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def verify_manifest(directory: Path, name: str) -> dict[str, str]:
    rows = read_csv(directory / name)
    m = {r["file"]: r["sha256"] for r in rows}
    if not m:
        raise GateError("manifest_empty:" + name)
    for fn, expected in m.items():
        p = directory / fn
        if not p.is_file():
            raise GateError("manifest_missing:" + fn)
        if sha256_file(p) != expected:
            raise GateError("manifest_SHA:" + fn)
    return m


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields: list[str] = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return s.getvalue().encode()


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        if p.exists() and p.read_bytes() != data:
            raise GateError("existing_output_differs:" + name)
        if not p.exists():
            p.write_bytes(data)


def local_relperm(
    S: np.ndarray,
    nw: np.ndarray,
    no: np.ndarray,
    krw_max: np.ndarray,
    kro_max: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    span = 1.0 - SWC - SOR
    Se = np.clip((np.asarray(S, dtype=np.float64) - SWC) / span, 0.0, 1.0)
    krw = np.asarray(krw_max, dtype=np.float64) * Se ** np.asarray(nw, dtype=np.float64)
    kro = np.asarray(kro_max, dtype=np.float64) * (1.0 - Se) ** np.asarray(no, dtype=np.float64)
    return krw, kro


def local_fw(
    S: np.ndarray,
    nw: np.ndarray,
    no: np.ndarray,
    krw_max: np.ndarray,
    kro_max: np.ndarray,
) -> np.ndarray:
    krw, kro = local_relperm(S, nw, no, krw_max, kro_max)
    lw = krw / MU_W
    lo = kro / MU_O
    return lw / (lw + lo + EPS)


def local_dshape(
    S: np.ndarray,
    nw: np.ndarray,
    no: np.ndarray,
    krw_max: np.ndarray,
    kro_max: np.ndarray,
) -> np.ndarray:
    span = 1.0 - SWC - SOR
    S = np.asarray(S, dtype=np.float64)
    Se = np.clip((S - SWC) / span, 1.0e-6, 1.0 - 1.0e-6)

    kro = np.asarray(kro_max, dtype=np.float64) * (
        1.0 - Se
    ) ** np.asarray(no, dtype=np.float64)

    fw = local_fw(S, nw, no, krw_max, kro_max)

    raw = kro * fw * Se ** (-1.0 / LAMBDA_C - 1.0)

    Se_mid = np.full_like(Se, 0.5)
    S_mid = SWC + span * Se_mid

    kro_mid = np.asarray(kro_max, dtype=np.float64) * (
        1.0 - Se_mid
    ) ** np.asarray(no, dtype=np.float64)

    fw_mid = local_fw(
        S_mid,
        nw,
        no,
        krw_max,
        kro_max,
    )

    norm = kro_mid * fw_mid * Se_mid ** (-1.0 / LAMBDA_C - 1.0)

    return raw / np.maximum(norm, EPS)


def self_test() -> None:
    # Constant-field collapse to the exact AV2 constitutive vector.
    s = np.linspace(SWC + 1.0e-3, 1.0 - SOR - 1.0e-3, 201)

    nw = np.full_like(s, 2.0)
    no = np.full_like(s, 2.0)
    krw_m = np.full_like(s, 0.8)
    kro_m = np.full_like(s, 0.8)

    krw, kro = local_relperm(s, nw, no, krw_m, kro_m)

    Se = np.clip((s - SWC) / (1.0 - SWC - SOR), 0.0, 1.0)
    krw_ref = 0.8 * Se**2.0
    kro_ref = 0.8 * (1.0 - Se)**2.0

    assert np.allclose(krw, krw_ref, rtol=0.0, atol=1.0e-15)
    assert np.allclose(kro, kro_ref, rtol=0.0, atol=1.0e-15)

    fw_ref = 1.0 / (1.0 + (MU_W / MU_O) * (kro_ref / (krw_ref + EPS)))
    assert np.max(np.abs(local_fw(s, nw, no, krw_m, kro_m) - fw_ref)) < 2.0e-10

    # Local normalized D must be one at Se=0.5 for every local constitutive vector.
    rng = np.random.default_rng(260303)
    shape = (128,)
    nwv = 2.0 + 2.0 * rng.random(shape)
    nov = 2.0 + 2.0 * rng.random(shape)
    kw = 0.60 + 0.40 * rng.random(shape)
    ko = 0.60 + 0.40 * rng.random(shape)
    smid = np.full(shape, SWC + 0.5 * (1.0 - SWC - SOR))

    assert np.max(np.abs(local_dshape(smid, nwv, nov, kw, ko) - 1.0)) < 1.0e-12

    # Model parameter count: first LSTM + second LSTM + TD Dense.
    p1 = 4 * (INPUT_CHANNELS + HIDDEN_UNITS + 1) * HIDDEN_UNITS
    p2 = 4 * (HIDDEN_UNITS + HIDDEN_UNITS + 1) * HIDDEN_UNITS
    ph = HIDDEN_UNITS + 1
    assert p1 + p2 + ph == MODEL_PARAMETERS

    assert len(AV3_CHANNELS) == 13
    assert TRAIN_PROFILES == 19404
    assert VAL_PROFILES == 9702
    assert OOD_PREDICTOR_PROFILES == 9702
    assert TRAIN_PHYSICS_PAIRS == 17248
    assert VAL_PHYSICS_PAIRS == 8624

    print("POSTV16-AV3-A3 transport/teacher/residual/PI-RNN protocol self-test: PASS")


def main(root: Path, drive: Path) -> int:
    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"

    out = drive / OUT_REL
    blocked = drive / BLOCK_REL

    def gate(name: str, passed: Any, value: Any = None) -> None:
        ok = bool(passed)
        gates[name] = {"passed": ok, "value": value}
        print(
            f"[{'PASS' if ok else 'FAIL'}] {name}"
            + (f" — {value}" if value is not None else "")
        )
        if not ok:
            raise GateError(name)

    print("=" * 204)
    print("POSTV16-AV3-A3 — SPATIAL COREY/RELPERM TRANSPORT + TEACHER/DATASET + RESIDUAL + 13-CHANNEL PI-RNN PROTOCOL FREEZE")
    print("=" * 204)
    print("DESIGN / FREEZE ONLY.")
    print("NO TRANSPORT TEACHER GENERATION. NO Y TARGET GENERATION. NO TRAINING. NO INFERENCE.")
    print("NO CHECKPOINT CREATION. NO OOD TARGET ACCESS. NO MAPBACK. NO LP. NO CMG.")
    print("PRESSURE/Q, POLLOCK/TOF, R7D GRAPH GEOMETRY, Swc/Sor, AND LOCAL-PV CAPACITY REMAIN FROZEN.")
    print()

    try:
        root = root.resolve()
        drive = drive.resolve()

        # ------------------------------------------------------------------------------------------
        # Repository/source authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"

        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate("repository_parent_is_AV3A2_commit", parent == PARENT_A2_COMMIT, parent)
        gate("repository_clean", status == "", repr(status))

        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        # ------------------------------------------------------------------------------------------
        # Bind exact A2 PASS and four immutable feature artifacts.
        # ------------------------------------------------------------------------------------------
        stage = "AV3A2_binding"

        a2 = drive / A2_REL
        gate("AV3A2_output_present", a2.is_dir(), str(a2))

        m2 = verify_manifest(a2, A2_MANIFEST)
        gate("AV3A2_manifest_SHA_closure", len(m2) == 11, len(m2))

        s2 = load_json(a2 / A2_SUMMARY)
        d2 = load_json(a2 / A2_DECISION)
        diag2 = read_csv(a2 / A2_DIAG)
        sample2 = read_csv(a2 / A2_SAMPLING)

        gate("AV3A2_status_exact", s2["status"] == A2_STATUS, s2["status"])
        gate("AV3A2_four_realizations", int(s2["realizations_completed"]) == 4)
        gate("AV3A2_corrected_origin_applied", s2["preexecution_sampling_origin_correction_applied"] is True)
        gate("AV3A2_A3_authorized", d2["AV3_A3_authorized"] is True)
        gate("AV3A2_A3_execution_not_yet_authorized", d2["next"]["execution"] is False)
        gate("AV3A2_pressure_Q_reused", d2["pressure_Q_reused"] is True)
        gate("AV3A2_Pollock_TOF_reused", d2["Pollock_TOF_reused"] is True)
        gate("AV3A2_R7D_geometry_preserved", d2["R7D_graph_geometry_preserved"] is True)
        gate("AV3A2_no_teacher_generation", d2["teacher_generation_performed"] is False)
        gate("AV3A2_no_training", d2["training_performed"] is False)
        gate("AV3A2_no_inference", d2["inference_performed"] is False)
        gate("AV3A2_diagnostics_count_4", len(diag2) == 4, len(diag2))
        gate("AV3A2_sampling_rows_16", len(sample2) == 16, len(sample2))

        for rid, phi_rid, partition in REALIZATIONS:
            npz = a2 / f"POSTV16_AV3_A2_{rid}_Corey_Relperm_Field_and_Streamline_Sampling.npz"
            gate(f"{rid}_A2_artifact_present", npz.is_file(), npz.name)

            with np.load(npz, allow_pickle=False) as z:
                required = {
                    "nw_streamline",
                    "no_streamline",
                    "krw_max_streamline",
                    "kro_max_streamline",
                    "streamline_xyz_m",
                    "pollock_tof_s",
                    "streamline_weight_m3_s",
                    "paired_porosity",
                    "corey_realization_id",
                    "paired_porosity_realization_id",
                    "partition",
                    "Swc",
                    "Sor",
                }

                gate(
                    f"{rid}_required_A2_arrays",
                    required.issubset(set(z.files)),
                    sorted(z.files),
                )

                for name in VARIABLE_PARAMETERS:
                    arr = np.asarray(z[f"{name}_streamline"], dtype=np.float64)
                    gate(f"{rid}_{name}_streamline_shape", arr.shape == (NSL, NN), arr.shape)
                    gate(f"{rid}_{name}_streamline_finite", np.isfinite(arr).all())

                gate(
                    f"{rid}_paired_phi_shape",
                    np.asarray(z["paired_porosity"]).shape == GRID,
                    np.asarray(z["paired_porosity"]).shape,
                )
                gate(
                    f"{rid}_XYZ_shape",
                    np.asarray(z["streamline_xyz_m"]).shape == (NSL, NN, 3),
                    np.asarray(z["streamline_xyz_m"]).shape,
                )
                gate(
                    f"{rid}_TOF_shape",
                    np.asarray(z["pollock_tof_s"]).shape == (NSL, NN),
                    np.asarray(z["pollock_tof_s"]).shape,
                )

                # A2 contains predictor physics only, never transport truth.
                forbidden = {
                    "Y",
                    "Y_transport",
                    "Sw_target",
                    "saturation_target",
                    "teacher_Y",
                }
                gate(
                    f"{rid}_no_transport_truth_arrays",
                    len(forbidden.intersection(set(z.files))) == 0,
                    sorted(forbidden.intersection(set(z.files))),
                )

        # ------------------------------------------------------------------------------------------
        # Freeze spatially varying constitutive PDE.
        # ------------------------------------------------------------------------------------------
        stage = "transport_operator_freeze"

        pde = {
            "coordinate": {
                "theta": "Pollock TOF / terminal Pollock TOF",
                "eta": "physical time / terminal Pollock TOF",
                "metric_M": "dtheta/dxD from frozen AV2 realization-specific Pollock geometry",
            },
            "strong_form": (
                "dS/deta + d/dtheta fw(S;p(theta)) = "
                "(phi(theta)/Pe_c) M(theta) d/dtheta["
                "Dtilde(S;p(theta)) M(theta) dS/dtheta]"
            ),
            "local_constitutive_vector": "p(theta)=(nw,no,krw_max,kro_max)",
            "fixed_parameters": {
                "Swc": SWC,
                "Sor": SOR,
                "mu_w_cP": MU_W,
                "mu_o_cP": MU_O,
                "Pe_c": PE_C,
                "lambda_c": LAMBDA_C,
                "Sw_init": SW_INIT,
                "Sw_inj": SW_INJ,
            },
            "relperm": {
                "Se": "(S-Swc)/(1-Swc-Sor), clipped to [0,1]",
                "krw": "krw_max(theta) * Se**nw(theta)",
                "kro": "kro_max(theta) * (1-Se)**no(theta)",
                "fw": "(krw/mu_w)/[(krw/mu_w)+(kro/mu_o)]",
            },
            "capillary_shape": {
                "raw": (
                    "kro(S;p) * fw(S;p) * "
                    "Se**(-1/lambda_c-1)"
                ),
                "normalization": (
                    "LOCAL nodewise raw value at Se=0.5 using the same local p(theta)"
                ),
                "Dtilde": "raw/local_midpoint_normalization",
                "property": "Dtilde(Se=0.5;p(theta))=1 at every node",
            },
            "AV2_constant_constitutive_collapse": True,
        }

        gate("PDE_Swc_fixed", SWC == 0.20)
        gate("PDE_Sor_fixed", SOR == 0.20)
        gate("PDE_Pe_c_frozen_22", PE_C == 22.0)
        gate("PDE_lambda_c_frozen_2", LAMBDA_C == 2.0)

        # ------------------------------------------------------------------------------------------
        # Freeze the teacher's conservative face algebra.
        # ------------------------------------------------------------------------------------------
        discretization = {
            "nodes": 201,
            "orientation": "injector_to_producer_positive_theta",
            "advection": {
                "form": "conservative finite-volume face divergence",
                "interior_update": (
                    "S_j <- S_j - deta*(F_{j+1/2}-F_{j-1/2})/DeltaTheta_j"
                ),
                "face_flux_rule": (
                    "positive-flow upwind: use upstream nodal saturation AND upstream "
                    "nodal constitutive vector p"
                ),
                "inlet_face": "fw(Sw_inj; p_node0)",
                "interior_face_between_j_and_jplus1": "fw(S_j; p_j)",
                "terminal_outflow_face": "fw(S_last; p_last)",
                "Godunov_direction": "fixed positive streamline direction; no Riemann sign switch",
            },
            "capillary": {
                "split": "explicit advection then semi-implicit capillary, as AV2",
                "D_node": "local Dtilde(Sadv_j;p_j)",
                "D_face": "arithmetic mean of neighboring D_node values",
                "M_face": "frozen harmonic face metric from AV2 operator geometry",
                "A_face": "D_face * M_face / DeltaTheta_center",
                "interior_coefficient": "phi_j/Pe_c * M_j/DeltaTheta_CV_j",
                "inlet": "Dirichlet Sw_inj",
                "terminal": "zero capillary update / terminal value inherited from advection",
            },
            "bounds": {
                "clip_after_advection": [SWC, 1.0 - SOR],
                "clip_after_capillary": [SWC, 1.0 - SOR],
                "inlet_reset_after_each_substep": SW_INJ,
            },
            "CFL": {
                "CFL_number": CFL,
                "wave_speed": (
                    "realization-local maximum |dfw/dS| evaluated from the physical "
                    "sampled p(theta) on a fixed 4001-point saturation grid; predictor "
                    "fields only, never Y or model performance"
                ),
                "dt_eta": "CFL*min(interior DeltaTheta_CV)/max_wave_speed",
                "same_algorithm_for_train_validation_and_future_locked_OOD_teacher": True,
            },
        }

        # ------------------------------------------------------------------------------------------
        # Freeze dataset/leakage protocol.
        # ------------------------------------------------------------------------------------------
        stage = "teacher_dataset_freeze"

        dataset = {
            "canonical_days": DAYS,
            "TRAIN_teacher_realizations": ["AV3CR0001", "AV3CR0002"],
            "VALIDATION_teacher_realizations": ["AV3CR0003"],
            "LOCKED_OOD_realization": "AV3CR0004",
            "TRAIN_profiles": TRAIN_PROFILES,
            "VALIDATION_profiles": VAL_PROFILES,
            "LOCKED_OOD_predictor_profiles": OOD_PREDICTOR_PROFILES,
            "TRAIN_physics_pairs": TRAIN_PHYSICS_PAIRS,
            "VALIDATION_physics_pairs": VAL_PHYSICS_PAIRS,
            "A4_authorized_teacher_generation": [
                "AV3CR0001",
                "AV3CR0002",
                "AV3CR0003",
            ],
            "A4_forbidden_teacher_generation": ["AV3CR0004"],
            "locked_OOD_predictor_feature_access": True,
            "locked_OOD_transport_target_access_before_checkpoint_freeze": False,
            "locked_OOD_metric_access_before_checkpoint_freeze": False,
            "locked_OOD_after_checkpoint": (
                "one teacher generation + one evaluation only; no retraining, "
                "checkpoint reselection, normalization refit, hyperparameter retuning, "
                "or second OOD evaluation"
            ),
            "teacher_certification_thresholds": {
                "advection_conservation_max_abs": 1.0e-11,
                "implicit_residual_max_abs": 1.0e-10,
                "preclip_bound_violation_max": 1.0e-8,
                "Y_bound_violation": 1.0e-8,
                "Y_inlet_Dirichlet_error": 1.0e-12,
                "Y_reservoir_undershoot": 1.0e-8,
                "temporal_negative_increment_fraction": 0.01,
                "spatial_positive_increment_fraction": 0.05,
            },
        }

        gate("TRAIN_profiles_19404", TRAIN_PROFILES == 19404)
        gate("VALIDATION_profiles_9702", VAL_PROFILES == 9702)
        gate("OOD_predictor_profiles_9702", OOD_PREDICTOR_PROFILES == 9702)
        gate("TRAIN_physics_pairs_17248", TRAIN_PHYSICS_PAIRS == 17248)
        gate("VALIDATION_physics_pairs_8624", VAL_PHYSICS_PAIRS == 8624)

        # ------------------------------------------------------------------------------------------
        # Freeze differentiable residual: exact same conservative spatial operator.
        # ------------------------------------------------------------------------------------------
        stage = "physics_residual_freeze"

        residual = {
            "loss_domain": "interior nodes j=1..199 only",
            "time_derivative": {
                "pairs": "adjacent physical target times from same streamline",
                "formula": "(S_b-S_a)/(eta_b-eta_a)",
                "spatial_state": "S_mid=0.5*(S_a+S_b)",
                "pairs_per_streamline": 8,
            },
            "advection_term": {
                "formula": "(F_right-F_left)/DeltaTheta_CV",
                "face_rule": "same positive-upwind saturation+local-p rule as teacher",
            },
            "capillary_term": {
                "formula": (
                    "(phi/Pe_c)*(M/DeltaTheta_CV)*"
                    "[A_right*(S_right-S)-A_left*(S-S_left)]"
                ),
                "A_face": "arithmetic_Dtilde_face * harmonic_M_face / DeltaTheta_center",
                "Dtilde_rule": "same local constitutive normalization as teacher",
            },
            "residual": "R=time_derivative + advection_divergence - capillary_divergence",
            "physics_sidecars": [
                "phi_sequence",
                "metric_M",
                "metric_M_face",
                "control_volume_dtheta",
                "dtheta_center",
                "nw_sequence",
                "no_sequence",
                "krw_max_sequence",
                "kro_max_sequence",
            ],
            "sidecar_alignment": (
                "same realization, streamline, 201-node order, and physical-time pair "
                "as the supervised prediction pair"
            ),
            "R0": R0,
            "lambda_phys": LAMBDA_PHYS,
            "no_OOD_physics_pairs_for_selection": True,
        }

        # ------------------------------------------------------------------------------------------
        # Freeze 13-channel model and training protocol.
        # ------------------------------------------------------------------------------------------
        stage = "PIRNN_protocol_freeze"

        model = {
            "architecture_family": "stacked_LSTM_TimeDistributed_Dense_bounded_Sw",
            "nodes": NN,
            "input_channels": INPUT_CHANNELS,
            "channel_order": AV3_CHANNELS,
            "AV2_channel_prefix_preserved": True,
            "new_constitutive_channel_scaling": {
                "nw_hat": "(nw-3.0)/1.0",
                "no_hat": "(no-3.0)/1.0",
                "krw_max_hat": "(krw_max-0.80)/0.20",
                "kro_max_hat": "(kro_max-0.80)/0.20",
            },
            "normalization": {
                "first_9_channels": (
                    "reuse frozen AV2 train-authority representations/scales because "
                    "K,phi,pressure,geometry,time definitions and split pairing are unchanged"
                ),
                "new_4_channels": "fixed analytical scaling; no fitted statistics",
                "validation_statistics_used_for_fit": False,
                "locked_OOD_statistics_used_for_fit": False,
            },
            "LSTM_layers": LSTM_LAYERS,
            "hidden_units": HIDDEN_UNITS,
            "TimeDistributed_output_units": 1,
            "bounded_output": "Swc + (1-Swc-Sor)*sigmoid(raw)",
            "output_bounds": [SWC, 1.0 - SOR],
            "parameter_count": MODEL_PARAMETERS,
            "AV2_epoch198_checkpoint_direct_weight_compatibility": False,
            "AV2_checkpoint_role": "historical baseline only",
            "objective": {
                "formula": "L_data + 0.01*L_phys",
                "L_data": "mean squared saturation error over all 201 nodes",
                "L_phys": "mean squared interior conservative spatial-relperm PDE residual",
                "lambda_data": LAMBDA_DATA,
                "lambda_phys": LAMBDA_PHYS,
                "R0": R0,
            },
            "optimizer": {
                "name": "Adam",
                "learning_rate": INITIAL_LR,
            },
            "batch_size": BATCH_SIZE,
            "max_epochs": MAX_EPOCHS,
            "shuffle_training_samples_each_epoch": True,
            "random_seed": TRAINING_SEED,
            "early_stopping": {
                "monitor": "validation total objective",
                "patience": EARLY_STOP_PATIENCE,
                "min_delta": EARLY_STOP_MIN_DELTA,
                "restore_best_weights": True,
            },
            "lr_schedule": {
                "type": "ReduceLROnPlateau",
                "monitor": "validation total objective",
                "factor": LR_FACTOR,
                "patience": LR_PATIENCE,
                "min_learning_rate": MIN_LR,
            },
            "checkpoint_selection": "minimum validation total objective",
            "checkpoint_freeze_before_OOD_target_generation": True,
        }

        gate("AV3_model_input_width_13", INPUT_CHANNELS == 13)
        gate("AV3_model_parameter_count_53057", MODEL_PARAMETERS == 53057)
        gate("AV3_lambda_phys_0p01", LAMBDA_PHYS == 0.01)
        gate("AV3_training_seed_16021", TRAINING_SEED == 16021)
        gate("AV3_batch_64", BATCH_SIZE == 64)
        gate("AV3_max_epochs_300", MAX_EPOCHS == 300)

        # ------------------------------------------------------------------------------------------
        # Final handoff.
        # ------------------------------------------------------------------------------------------
        handoff = {
            "milestone": "POSTV16-AV3-A4",
            "name": (
                "TRAIN/VALIDATION Spatial-Corey/Relperm Teacher Generation, "
                "13-Channel Dataset Assembly, and Locked-OOD Predictor-Only Freeze"
            ),
            "authorized": True,
            "execution": True,
            "allowed": [
                "generate certified teachers for AV3CR0001 and AV3CR0002 TRAIN only",
                "generate certified teacher for AV3CR0003 VALIDATION only",
                "assemble 13-channel TRAIN and VALIDATION tensors",
                "assemble AV3CR0004 13-channel predictor tensor without Y",
                "assemble TRAIN/VALIDATION physics sidecars and adjacent-time pair registries",
                "reuse frozen AV2 kinematics and first-nine-channel normalization authority",
            ],
            "forbidden": [
                "generate or open AV3CR0004 transport Y",
                "train the AV3 PI-RNN",
                "create or select an AV3 checkpoint",
                "compute an AV3CR0004 predictive metric",
                "retune A1 fields or seeds",
                "re-solve pressure or retrace Pollock",
                "map back, execute LP, or use CMG",
            ],
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "spatial_constitutive_PDE_frozen": True,
            "teacher_face_discretization_frozen": True,
            "local_capillary_normalization_frozen": True,
            "teacher_dataset_split_firewall_frozen": True,
            "differentiable_residual_matches_teacher_face_algebra": True,
            "AV3_13channel_model_protocol_frozen": True,
            "AV3_model_parameter_count": MODEL_PARAMETERS,
            "AV2_checkpoint_directly_compatible": False,
            "teacher_generation_performed": False,
            "Y_target_generation_performed": False,
            "training_performed": False,
            "inference_performed": False,
            "checkpoint_created": False,
            "locked_OOD_target_accessed": False,
            "locked_OOD_metric_computed": False,
            "pressure_resolve_performed": False,
            "Pollock_retrace_performed": False,
            "mapback_performed": False,
            "LP_execution_performed": False,
            "CMG_validation_performed": False,
            "AV3_A4_authorized": True,
            "next": handoff,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "transport_nodes": NN,
            "input_channels": INPUT_CHANNELS,
            "model_parameters": MODEL_PARAMETERS,
            "TRAIN_profiles": TRAIN_PROFILES,
            "VALIDATION_profiles": VAL_PROFILES,
            "LOCKED_OOD_predictor_profiles": OOD_PREDICTOR_PROFILES,
            "TRAIN_physics_pairs": TRAIN_PHYSICS_PAIRS,
            "VALIDATION_physics_pairs": VAL_PHYSICS_PAIRS,
            "teacher_generation": False,
            "Y_target_generation": False,
            "training": False,
            "inference": False,
            "checkpoint_creation": False,
            "locked_OOD_target_access": False,
            "CMG_validation": False,
            "AV3_A4_authorized": True,
            "next": handoff,
        }

        counts_rows = [
            {
                "partition": "TRAIN",
                "realizations": 2,
                "profiles": TRAIN_PROFILES,
                "physics_adjacent_time_pairs": TRAIN_PHYSICS_PAIRS,
                "teacher_Y_authorized_in_A4": True,
            },
            {
                "partition": "VALIDATION",
                "realizations": 1,
                "profiles": VAL_PROFILES,
                "physics_adjacent_time_pairs": VAL_PHYSICS_PAIRS,
                "teacher_Y_authorized_in_A4": True,
            },
            {
                "partition": "LOCKED_OOD_TEST",
                "realizations": 1,
                "profiles": OOD_PREDICTOR_PROFILES,
                "physics_adjacent_time_pairs": 0,
                "teacher_Y_authorized_in_A4": False,
            },
        ]

        files = {
            "PAD_Stream_POSTV16_AV3_A3_Summary.json": json_bytes(summary),
            "POSTV16_AV3_A3_Spatial_Constitutive_Transport_Operator.json": json_bytes(pde),
            "POSTV16_AV3_A3_Conservative_Face_Discretization_Contract.json": json_bytes(discretization),
            "POSTV16_AV3_A3_Teacher_Dataset_and_Leakage_Firewall.json": json_bytes(dataset),
            "POSTV16_AV3_A3_Differentiable_Physics_Residual_Contract.json": json_bytes(residual),
            "POSTV16_AV3_A3_13Channel_PIRNN_Training_Protocol.json": json_bytes(model),
            "POSTV16_AV3_A3_Frozen_Sample_and_Physics_Pair_Counts.csv": csv_bytes(counts_rows),
            "POSTV16_AV3_A3_A4_Handoff_Contract.json": json_bytes(handoff),
            "POSTV16_AV3_A3_Decision_Contract.json": json_bytes(decision),
            "POSTV16_AV3_A3_Final_Gate_Matrix.csv": csv_bytes(
                [{"gate": k, **v} for k, v in gates.items()]
            ),
        }

        immutable_publish(out, files)

        manifest_rows = []
        for q in sorted(out.iterdir()):
            if q.is_file() and q.name != "POSTV16_AV3_A3_Artifact_Manifest.csv":
                manifest_rows.append({
                    "file": q.name,
                    "sha256": sha256_file(q),
                    "bytes": q.stat().st_size,
                })

        immutable_publish(
            out,
            {"POSTV16_AV3_A3_Artifact_Manifest.csv": csv_bytes(manifest_rows)},
        )

        print()
        print("=" * 204)
        print("POSTV16-AV3-A3: FULL TRANSPORT / TEACHER / RESIDUAL / PI-RNN PROTOCOL FREEZE PASS")
        print("=" * 204)
        print("Spatial PDE                                  : FROZEN")
        print("Advection                                    : conservative positive-upwind local p")
        print("Capillary D                                  : local normalized Dtilde, arithmetic face mean")
        print("Teacher / residual face algebra              : MATCHED")
        print("Swc / Sor                                    : 0.20 / 0.20")
        print("Pe_c / lambda_c                              : 22 / 2")
        print("TRAIN / VAL / OOD predictor profiles         : 19404 / 9702 / 9702")
        print("TRAIN / VAL physics pairs                    : 17248 / 8624")
        print("Model                                        : 201 x 13 -> 2xLSTM64 -> TD Dense")
        print("Trainable parameters                         : 53057")
        print("Objective                                    : L_data + 0.01 L_phys")
        print("Teacher generation / training                : False / False")
        print("Locked OOD Y access                          : False")
        print("POSTV16-AV3-A4                               : AUTHORIZED")
        print("A4 execution                                 : AUTHORIZED")
        print("=" * 204)

        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)

        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "teacher_generation_performed": False,
            "Y_target_generation_performed": False,
            "training_performed": False,
            "inference_performed": False,
            "checkpoint_created": False,
            "locked_OOD_target_accessed": False,
            "AV3_A4_authorized": False,
        }

        q = blocked / "POSTV16_AV3_A3_Blocked_Report.json"

        if not q.exists():
            q.write_bytes(json_bytes(report))

        print()
        print("POSTV16-AV3-A3: BLOCKED", stage, repr(exc))
        return 2


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", type=Path, default=Path("."))
    p.add_argument(
        "--drive-root",
        type=Path,
        default=Path("/content/drive/MyDrive/PAD_Stream_Compute"),
    )
    p.add_argument("--self-test", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.self_test:
        self_test()
        raise SystemExit(0)

    raise SystemExit(
        main(
            args.project_root,
            args.drive_root,
        )
    )
