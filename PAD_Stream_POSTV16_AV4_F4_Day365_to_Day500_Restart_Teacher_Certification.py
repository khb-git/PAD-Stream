#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any

import numpy as np


MILESTONE = "POSTV16-AV4-F4"
PROTOCOL_ID = (
    "POSTV16_AV4_F4_CONTROLLED_DAY365_TO_DAY500_200CV_17CHANNEL_"
    "RESTART_TEACHER_CONSERVATIVE_LOOP_CERTIFICATION_V1"
)

STATUS_PASS = (
    "AV4F4_DAY365_TO_DAY500_200CV_17CHANNEL_RESTART_TEACHER_"
    "COMPONENT_MASS_CONSERVATIVE_E37A_MAPBACK_DAY500_DYNAMIC_FLOW_REFRESH_"
    "BOUNDED_REPROJECTION_AND_UNTRAINED_MODEL_SIGNATURE_CERTIFICATION_PASS"
)
STATUS_FAIL = (
    "AV4F4_DAY365_TO_DAY500_RESTART_TEACHER_OR_CONSERVATIVE_RECURRENT_LOOP_"
    "SCIENTIFIC_FAIL_NO_ADAPTATION_OR_AUTOMATIC_RERUN_AUTHORIZED"
)
STATUS_BLOCKED = "AV4F4_TECHNICAL_EXECUTION_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_F3_COMMIT = "11bcce94db924b8bca81780610ac660de46feda7"

CONTROL_REALIZATION = "AV3CR0003"
CONTROL_POROSITY = "AV2PHI0003"
CONTROL_PARTITION = "VALIDATION"
PARENT_DAY = 365.0
TARGET_DAY = 500.0
DELTA_DAY = 135.0

GRID = (15, 50, 50)
NZ, NY, NX = GRID
NCELL = NZ * NY * NX
NSL = 1078
NN = 201
NCV = 200

BACKGROUND = 0.20
INJECTED = 0.80
MAX_SG = 0.60
SW_INJ_TEACHER = 0.799
PE_C = 22.0
CFL = 0.25
SPD = 86400.0
CO2_RHO_REF = 700.0

INPUT_CHANNELS = 17
MODEL_PARAMETERS = 54081
HIDDEN_UNITS = 64
LSTM_LAYERS = 2
TRAINING_SEED = 16021

LOOKUP_POINTS = 200001
MAX_TEACHER_SUBSTEPS = 200000
MASS_CAPACITY_CFL = 0.50
MIN_TEACHER_DT_DAYS = 1.0e-10

CHANNELS17 = [
    "xi_cv",
    "pollock_tau_hat_cv",
    "adv_tau_hat_cv",
    "log10_Kh_cv",
    "log10_Kz_over_Kh_cv",
    "porosity_cv",
    "pressure_z_cv",
    "parent_time_hat",
    "target_time_hat",
    "delta_time_hat",
    "delta_eta_streamline",
    "nw_hat_cv",
    "no_hat_cv",
    "krw_max_hat_cv",
    "kro_max_hat_cv",
    "parent_CV_saturation_hat",
    "parent_CV_mass_fraction",
]

# --------------------------------------------------------------------------------------------------
# Exact repository authorities.
# --------------------------------------------------------------------------------------------------

F3 = "PAD_Stream_POSTV16_AV4_F3_Split_State_Restart_Model_and_Teacher_Protocol_Freeze.py"
F3_BLOB = "87b6cbf76272dfe3589b9f0da6559645f028be08"

F2R3 = "PAD_Stream_POSTV16_AV4_F2_R3_Bounded_Physical_Occupancy_Projection_Execution.py"
F2R3_BLOB = "359f3c0edf87e10bb4006cacdd271cd426fed22b"

E1R2 = (
    "PAD_Stream_POSTV16_AV4_A3_E1_R2_Fully_Schema_Corrected_"
    "Refreshed_X13_Structural_InputDomain_Audit.py"
)
E1R2_BLOB = "058f00fd12bd491dc7d7d7e471af3d4ff865af70"

A4R2 = (
    "PAD_Stream_POSTV16_AV3_A4_R2_"
    "Corrected_Certification_Teacher_Dataset_and_LockedOOD_Predictor.py"
)
A4R2_BLOB = "289901331e835afb44ff2f665fe9a6bbea2eac19"

A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"

R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"

SG2 = "PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"
SG2_BLOB = "7242012d3e758472abc3ee7f543831b92d2cf419"

SG3 = "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG3_BLOB = "66a379cd97ee9120f69e7e7e949171541e4918c3"

SG4 = "PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"
SG4_BLOB = "8d49f88bdf55b0da087af2bed04e69967740e695"

SG5 = "PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py"
SG5_BLOB = "9a0b64ea7e669904d0d9855ade1c6b052f05ecea"

SG6 = "PAD_Stream_V15SG6_TOF_Transport_Coordinates.py"
SG6_BLOB = "70ceda68e02894167958d753d88b4dbd694731ab"

SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"

R3R2R1 = "PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py"
R3R2R1_BLOB = "740c6da03e73906646bf0153633187e749449f31"

PERM = "SGSIM_50x50x15_PERM_MD.csv"
PERM_BLOB = "317dd47d458bc6f880c2e3dc4ec1f69eeb0dd314"

SOURCE_BLOBS = {
    F3: F3_BLOB,
    F2R3: F2R3_BLOB,
    E1R2: E1R2_BLOB,
    A4R2: A4R2_BLOB,
    A2E: A2E_BLOB,
    R2: R2_BLOB,
    E37A: E37A_BLOB,
    SG2: SG2_BLOB,
    SG3: SG3_BLOB,
    SG4: SG4_BLOB,
    SG5: SG5_BLOB,
    SG6: SG6_BLOB,
    SG7D: SG7D_BLOB,
    R3R2R1: R3R2R1_BLOB,
    PERM: PERM_BLOB,
}

# --------------------------------------------------------------------------------------------------
# Formal Drive authorities.
# --------------------------------------------------------------------------------------------------

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

F3_REL = BASE_AV4 / "POSTV16_AV4_F3_Split_State_Restart_Model_and_Teacher_Protocol_Freeze"
F3_SUMMARY = "PAD_Stream_POSTV16_AV4_F3_Summary.json"
F3_MODEL = "POSTV16_AV4_F3_Restart_Model_Signature_Contract.json"
F3_TEMPORAL = "POSTV16_AV4_F3_Restart_Temporal_Semantics_Contract.json"
F3_TEACHER = "POSTV16_AV4_F3_Split_State_Physics_Teacher_Contract.json"
F3_TRAIN = "POSTV16_AV4_F3_Training_Validation_OOD_Firewall_Contract.json"
F3_HANDOFF = "POSTV16_AV4_F3_F4_Handoff_Contract.json"
F3_DECISION = "POSTV16_AV4_F3_Decision_Contract.json"
F3_MANIFEST = "POSTV16_AV4_F3_Artifact_Manifest.csv"
F3_STATUS = (
    "AV4F3_F2R3_ACCEPTED_SPLIT_STATE_BOUND_RESTARTABLE_200CV_17CHANNEL_"
    "MODEL_SIGNATURE_TEMPORAL_SEMANTICS_CONSERVATIVE_TEACHER_LOOP_AND_"
    "TRAIN_VALIDATION_OOD_FIREWALLS_PROSPECTIVELY_FROZEN_NO_TEACHER_EXECUTION"
)

F2R3_REL = BASE_AV4 / "POSTV16_AV4_F2_R3_Bounded_Physical_Occupancy_Projection_Execution"
F2R3_STATE = "POSTV16_AV4_F2_R3_Accepted_Parent_Restart_State.npz"
F2R3_SUMMARY = "PAD_Stream_POSTV16_AV4_F2_R3_Summary.json"
F2R3_MANIFEST = "POSTV16_AV4_F2_R3_Artifact_Manifest.csv"
F2R3_STATUS = (
    "AV4F2R3_BOUNDED_PHYSICAL_OCCUPANCY_SPLIT_STATE_PARENT_PROJECTION_"
    "EXECUTION_PASS_CAPACITY_FEASIBLE_E37A_INVERSION_PASS_NO_TIME_ADVANCE"
)

E1R2_REL = BASE_AV4 / "POSTV16_AV4_A3_E1_R2_Refreshed_X13_Structural_InputDomain_Audit"
E1R2_SUMMARY = "PAD_Stream_POSTV16_AV4_A3_E1_R2_Summary.json"
E1R2_X13 = "POSTV16_AV4_A3_E1_R2_Refreshed_Day365_13Channel_Representation.npz"
E1R2_MANIFEST = "POSTV16_AV4_A3_E1_R2_Artifact_Manifest.csv"
E1R2_STATUS = (
    "AV4A3E1R2_FULLY_SCHEMA_CORRECTED_REFRESHED_DAY365_X13_"
    "RECONSTRUCTION_INPUT_DOMAIN_AUDIT_PASS_REPRESENTATION_ONLY_"
    "STRUCTURAL_RESTART_INCOMPATIBILITY_NO_CHECKPOINT_INFERENCE"
)

A2E_REL = BASE_AV4 / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_SUMMARY = "PAD_Stream_POSTV16_AV4_A2_E_Summary.json"
A2E_EPOCH = "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_MANIFEST = "POSTV16_AV4_A2_E_Artifact_Manifest.csv"
A2E_STATUS = (
    "AV4A2E_AV3CR0003_DAY365_SAME_TIME_SPATIAL_MOBILITY_PRESSURE_SATURATION_"
    "REFRESH_DARCY_POLLOCK_TOF_GEOMETRY_EXECUTION_PASS"
)

OUT_REL = BASE_AV4 / "POSTV16_AV4_F4_Day365_to_Day500_Restart_Teacher_Certification"
FAIL_REL = BASE_AV4 / "POSTV16_AV4_F4_SCIENTIFIC_FAIL"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F4_BLOCKED"


class GateError(RuntimeError):
    pass


class ScientificFail(RuntimeError):
    def __init__(self, gate: str, detail: Any = None):
        super().__init__(gate)
        self.gate = gate
        self.detail = detail


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
    manifest = {r["file"]: r["sha256"] for r in rows}
    if not manifest:
        raise GateError("manifest_empty:" + name)
    for fn, expected in manifest.items():
        p = directory / fn
        if not p.is_file():
            raise GateError("manifest_missing:" + fn)
        if sha256_file(p) != expected:
            raise GateError("manifest_SHA_mismatch:" + fn)
    return manifest


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError("cannot_load_module:" + str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def json_bytes(obj: Any) -> bytes:
    return (
        json.dumps(obj, indent=2, sort_keys=True, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return s.getvalue().encode("utf-8")


def deterministic_npz_bytes(arrays: dict[str, Any]) -> bytes:
    outer = io.BytesIO()
    with zipfile.ZipFile(
        outer,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as zf:
        for key in sorted(arrays):
            b = io.BytesIO()
            np.save(b, np.asarray(arrays[key]), allow_pickle=False)
            info = zipfile.ZipInfo(
                f"{key}.npy",
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, b.getvalue())
    return outer.getvalue()


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        if p.exists() and p.read_bytes() != data:
            raise GateError("existing_output_differs:" + name)
        if not p.exists():
            p.write_bytes(data)


def fsum_array(a: np.ndarray) -> float:
    return float(math.fsum(float(x) for x in np.asarray(a, dtype=np.float64).ravel()))


def relative_l2(a: np.ndarray, b: np.ndarray) -> float:
    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)
    return float(
        np.linalg.norm((aa - bb).ravel())
        / max(float(np.linalg.norm(bb.ravel())), 1.0e-30)
    )


def model_parameter_count(input_channels: int, units: int) -> int:
    first = 4 * units * (units + input_channels + 1)
    second = 4 * units * (units + units + 1)
    dense = units + 1
    return first + second + dense


def harmonic(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return 2.0 * a * b / np.maximum(a + b, 1.0e-300)


def build_mass_fraction_lookup(r2: Any) -> tuple[np.ndarray, np.ndarray]:
    sg = np.linspace(0.0, MAX_SG, LOOKUP_POINTS, dtype=np.float64)
    pc = np.asarray(r2.capillary_pressure_from_incremental_sg(sg), dtype=np.float64)
    g = np.exp(
        np.clip(float(r2.CO2_COMPRESSIBILITY_1_PA) * pc, -50.0, 50.0)
    ) * sg
    y = g / float(g[-1])
    if not np.isfinite(y).all() or np.any(np.diff(y) <= 0.0):
        raise GateError("mass_fraction_lookup_not_strictly_monotone")
    if abs(float(y[0])) > 1.0e-15 or abs(float(y[-1]) - 1.0) > 1.0e-12:
        raise GateError("mass_fraction_lookup_endpoints")
    return y, BACKGROUND + sg


def saturation_from_mass_fraction(
    mass: np.ndarray,
    capacity: np.ndarray,
    y_lookup: np.ndarray,
    s_lookup: np.ndarray,
    tol: float,
) -> np.ndarray:
    m = np.asarray(mass, dtype=np.float64)
    c = np.asarray(capacity, dtype=np.float64)
    frac = m / c
    fmin = float(np.min(frac))
    fmax = float(np.max(frac))
    if fmin < -tol or fmax > 1.0 + tol:
        raise ScientificFail(
            "teacher_mass_fraction_outside_capacity",
            {"min": fmin, "max": fmax, "tolerance": tol},
        )
    eval_frac = np.minimum(np.maximum(frac, 0.0), 1.0)
    sat = np.interp(
        eval_frac.reshape(-1),
        y_lookup,
        s_lookup,
    ).reshape(frac.shape)
    return sat


def build_cv_geometry_from_faces(
    tof_s: np.ndarray,
    xi_1d: np.ndarray,
) -> dict[str, np.ndarray]:
    tof = np.asarray(tof_s, dtype=np.float64)
    xi = np.asarray(xi_1d, dtype=np.float64)
    tau_end = tof[:, -1]
    theta_face = tof / tau_end[:, None]
    dtheta = np.diff(theta_face, axis=1)
    dxi = np.diff(xi)
    if (
        theta_face.shape != (NSL, NN)
        or xi.shape != (NN,)
        or np.any(dtheta <= 0.0)
        or np.any(dxi <= 0.0)
    ):
        raise GateError("invalid_200CV_face_geometry")
    metric_cv = dtheta / dxi[None, :]
    theta_cv = 0.5 * (theta_face[:, :-1] + theta_face[:, 1:])
    xi_cv = 0.5 * (xi[:-1] + xi[1:])
    dtheta_center = np.diff(theta_cv, axis=1)
    metric_face = np.empty((NSL, NN), dtype=np.float64)
    metric_face[:, 0] = metric_cv[:, 0]
    metric_face[:, -1] = metric_cv[:, -1]
    metric_face[:, 1:-1] = harmonic(metric_cv[:, :-1], metric_cv[:, 1:])
    if (
        not np.isfinite(metric_cv).all()
        or not np.isfinite(metric_face).all()
        or np.any(metric_cv <= 0.0)
        or np.any(metric_face <= 0.0)
        or np.any(dtheta_center <= 0.0)
    ):
        raise GateError("nonpositive_200CV_metric_geometry")
    return {
        "theta_face": theta_face,
        "theta_cv": theta_cv,
        "dtheta_cv": dtheta,
        "dtheta_center": dtheta_center,
        "metric_cv": metric_cv,
        "metric_face": metric_face,
        "tau_end_s": tau_end,
        "xi_cv_1d": xi_cv,
    }


def teacher_face_fluxes(
    *,
    a4: Any,
    r2: Any,
    saturation: np.ndarray,
    q_m3_day: np.ndarray,
    face_pressure_psi: np.ndarray,
    p_ref_pa: float,
    nw: np.ndarray,
    no: np.ndarray,
    krw_max: np.ndarray,
    kro_max: np.ndarray,
    phi_cv: np.ndarray,
    cvgeom: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    S = np.asarray(saturation, dtype=np.float64)
    q = np.asarray(q_m3_day, dtype=np.float64)
    fp = np.asarray(face_pressure_psi, dtype=np.float64)

    adv = np.zeros((NSL, NCV + 1), dtype=np.float64)

    # The rate-controlled injector is the sole external CO2 source.
    adv[:, 0] = q * CO2_RHO_REF

    if NCV > 1:
        donor = S[:, :-1]
        ff = np.asarray(
            a4.local_fw(
                donor,
                nw[:, :-1],
                no[:, :-1],
                krw_max[:, :-1],
                kro_max[:, :-1],
            ),
            dtype=np.float64,
        )
        rho = np.asarray(
            r2.gas_density_from_state(
                donor,
                fp[:, 1:-1],
                p_ref_pa,
            ),
            dtype=np.float64,
        )
        adv[:, 1:-1] = q[:, None] * ff * rho

    ff_out = np.asarray(
        a4.local_fw(
            S[:, -1],
            nw[:, -1],
            no[:, -1],
            krw_max[:, -1],
            kro_max[:, -1],
        ),
        dtype=np.float64,
    )
    rho_out = np.asarray(
        r2.gas_density_from_state(
            S[:, -1],
            fp[:, -1],
            p_ref_pa,
        ),
        dtype=np.float64,
    )
    adv[:, -1] = q * ff_out * rho_out

    # --------------------------------------------------------------------------
    # Conservative capillary face flux.
    #
    # Starting from the frozen AV3 strong form, q*tau_end*dtheta is the
    # streamline pore volume of one TOF CV. Multiplication by that CV storage
    # cancels tau_end and dtheta, leaving q times the AV3 phi/Pe/metric
    # diffusion face coefficient. We symmetrize phi*M at the face so a single
    # pairwise phase-volume flux is shared by both neighboring CVs.
    #
    # Boundary capillary flux is zero at both ends. This is the rate-controlled
    # mass-compatible R2 convention: capillarity redistributes internally and
    # never creates a second injector source.
    # --------------------------------------------------------------------------
    D = np.asarray(
        a4.local_dshape(S, nw, no, krw_max, kro_max),
        dtype=np.float64,
    )
    Dface = 0.5 * (D[:, :-1] + D[:, 1:])

    metric_cv = cvgeom["metric_cv"]
    metric_face = cvgeom["metric_face"]
    dtheta_center = cvgeom["dtheta_center"]

    phi_metric = phi_cv * metric_cv
    phi_metric_face = 0.5 * (
        phi_metric[:, :-1] + phi_metric[:, 1:]
    )

    conductance = (
        q[:, None]
        * (phi_metric_face / PE_C)
        * Dface
        * metric_face[:, 1:-1]
        / dtheta_center
    )

    qcap = -conductance * (S[:, 1:] - S[:, :-1])

    cap = np.zeros((NSL, NCV + 1), dtype=np.float64)
    if NCV > 1:
        donor_left = S[:, :-1]
        donor_right = S[:, 1:]
        rho_left = np.asarray(
            r2.gas_density_from_state(
                donor_left,
                fp[:, 1:-1],
                p_ref_pa,
            ),
            dtype=np.float64,
        )
        rho_right = np.asarray(
            r2.gas_density_from_state(
                donor_right,
                fp[:, 1:-1],
                p_ref_pa,
            ),
            dtype=np.float64,
        )
        rho_up = np.where(qcap >= 0.0, rho_left, rho_right)
        cap[:, 1:-1] = qcap * rho_up

    rhs = (
        adv[:, :-1] - adv[:, 1:]
        + cap[:, :-1] - cap[:, 1:]
    )

    return {
        "advective_mass_flux_kg_day": adv,
        "capillary_mass_flux_kg_day": cap,
        "capillary_phase_conductance_m3_day_per_sat": conductance,
        "rhs_mass_kg_day": rhs,
        "outlet_fractional_flow": ff_out,
    }



def execute_teacher_with_coeff(
    *,
    a4: Any,
    r2: Any,
    e37: Any,
    old_mass: np.ndarray,
    old_sat: np.ndarray,
    capacity: np.ndarray,
    cv_pressure_mass_coeff: np.ndarray,
    cv_pv_m3: np.ndarray,
    face_pressure_psi: np.ndarray,
    p_ref_pa: float,
    q_m3_day: np.ndarray,
    nw: np.ndarray,
    no: np.ndarray,
    krw_max: np.ndarray,
    kro_max: np.ndarray,
    phi_cv: np.ndarray,
    cvgeom: dict[str, np.ndarray],
    delta_days: float,
) -> dict[str, Any]:
    mass = np.asarray(old_mass, dtype=np.float64).copy()
    cap = np.asarray(capacity, dtype=np.float64)
    coeff = np.asarray(cv_pressure_mass_coeff, dtype=np.float64)
    old_total = fsum_array(mass)

    y_lookup, s_lookup = build_mass_fraction_lookup(r2)

    lookup_parent = saturation_from_mass_fraction(
        mass, cap, y_lookup, s_lookup, 1.0e-10
    )
    lookup_parent_error = float(
        np.max(np.abs(lookup_parent - old_sat))
    )

    dfmax = float(
        a4.max_dfw_realization(
            nw, no, krw_max, kro_max
        )
    )
    dt_eta_adv = float(
        CFL
        * np.min(cvgeom["dtheta_cv"])
        / (dfmax + 1.0e-12)
    )
    adv_dt_days = float(
        dt_eta_adv
        * np.min(cvgeom["tau_end_s"])
        / SPD
    )
    if not np.isfinite(adv_dt_days) or adv_dt_days <= 0.0:
        raise ScientificFail("teacher_advective_CFL_nonpositive", adv_dt_days)

    remaining = float(delta_days)
    elapsed = 0.0
    steps = 0
    injected = 0.0
    produced = 0.0
    max_step_ledger = 0.0
    max_capillary_global_flux = 0.0
    min_dt_used = float("inf")
    max_dt_used = 0.0
    max_mass_fraction = float(np.max(mass / cap))

    while remaining > 1.0e-12 * max(float(delta_days), 1.0):
        sat = saturation_from_mass_fraction(
            mass, cap, y_lookup, s_lookup, 1.0e-9
        )

        flux = teacher_face_fluxes(
            a4=a4,
            r2=r2,
            saturation=sat,
            q_m3_day=q_m3_day,
            face_pressure_psi=face_pressure_psi,
            p_ref_pa=p_ref_pa,
            nw=nw,
            no=no,
            krw_max=krw_max,
            kro_max=kro_max,
            phi_cv=phi_cv,
            cvgeom=cvgeom,
        )

        rhs = flux["rhs_mass_kg_day"]
        conductance = flux[
            "capillary_phase_conductance_m3_day_per_sat"
        ]

        con_sum = np.zeros((NSL, NCV), dtype=np.float64)
        con_sum[:, :-1] += conductance
        con_sum[:, 1:] += conductance
        active = con_sum > 1.0e-30
        cap_dt_days = (
            float(CFL * np.min(cv_pv_m3[active] / con_sum[active]))
            if np.any(active)
            else float("inf")
        )

        positive = rhs > 1.0e-18
        negative = rhs < -1.0e-18
        dt_mass = float("inf")

        if np.any(positive):
            room = cap[positive] - mass[positive]
            if float(np.min(room)) < -1.0e-7:
                raise ScientificFail(
                    "teacher_mass_already_above_capacity",
                    float(np.min(room)),
                )
            candidates = room / rhs[positive]
            finite = candidates[np.isfinite(candidates) & (candidates > 0.0)]
            if finite.size:
                dt_mass = min(
                    dt_mass,
                    MASS_CAPACITY_CFL * float(np.min(finite)),
                )
            elif np.any(room <= 1.0e-12):
                raise ScientificFail(
                    "teacher_positive_flux_at_saturated_capacity"
                )

        if np.any(negative):
            candidates = mass[negative] / (-rhs[negative])
            finite = candidates[np.isfinite(candidates) & (candidates > 0.0)]
            if finite.size:
                dt_mass = min(
                    dt_mass,
                    MASS_CAPACITY_CFL * float(np.min(finite)),
                )
            elif np.any(mass[negative] <= 1.0e-12):
                raise ScientificFail(
                    "teacher_negative_flux_at_zero_mass"
                )

        h = min(
            remaining,
            adv_dt_days,
            cap_dt_days,
            dt_mass,
        )

        if not np.isfinite(h) or h <= MIN_TEACHER_DT_DAYS:
            raise ScientificFail(
                "teacher_substep_nonpositive_or_stiff",
                {
                    "dt_days": h,
                    "remaining_days": remaining,
                    "adv_dt_days": adv_dt_days,
                    "cap_dt_days": cap_dt_days,
                    "mass_dt_days": dt_mass,
                },
            )

        before = fsum_array(mass)
        trial = mass + h * rhs

        tol = max(1.0e-7, 1.0e-12 * max(before, 1.0))
        min_mass = float(np.min(trial))
        max_excess = float(np.max(trial - cap))
        if min_mass < -tol:
            raise ScientificFail(
                "teacher_negative_CV_mass_after_substep",
                {"minimum_kg": min_mass, "tolerance_kg": tol},
            )
        if max_excess > tol:
            raise ScientificFail(
                "teacher_CV_capacity_after_substep",
                {"maximum_excess_kg": max_excess, "tolerance_kg": tol},
            )

        mass = trial

        inj_step = h * fsum_array(
            flux["advective_mass_flux_kg_day"][:, 0]
        )
        prod_step = h * fsum_array(
            flux["advective_mass_flux_kg_day"][:, -1]
        )
        injected += inj_step
        produced += prod_step

        cap_global = (
            fsum_array(flux["capillary_mass_flux_kg_day"][:, 0])
            - fsum_array(flux["capillary_mass_flux_kg_day"][:, -1])
        )
        max_capillary_global_flux = max(
            max_capillary_global_flux,
            abs(cap_global),
        )

        after = fsum_array(mass)
        step_res = after - before - inj_step + prod_step
        max_step_ledger = max(max_step_ledger, abs(step_res))

        elapsed += h
        remaining = max(0.0, float(delta_days) - elapsed)
        steps += 1
        min_dt_used = min(min_dt_used, h)
        max_dt_used = max(max_dt_used, h)
        max_mass_fraction = max(
            max_mass_fraction,
            float(np.max(mass / cap)),
        )

        if steps > MAX_TEACHER_SUBSTEPS:
            raise ScientificFail(
                "teacher_subcycling_exceeded_limit",
                {
                    "steps": steps,
                    "limit": MAX_TEACHER_SUBSTEPS,
                    "elapsed_days": elapsed,
                },
            )

    final_sat_lookup = saturation_from_mass_fraction(
        mass, cap, y_lookup, s_lookup, 1.0e-9
    )
    final_sat_exact = np.asarray(
        e37.invert_cv_mass_to_saturation(
            r2,
            mass,
            coeff,
        ),
        dtype=np.float64,
    )
    lookup_final_error = float(
        np.max(np.abs(final_sat_lookup - final_sat_exact))
    )

    reconstructed = np.asarray(
        e37.cv_mass_from_saturation(
            r2,
            final_sat_exact,
            coeff,
        ),
        dtype=np.float64,
    )
    inversion_error = float(np.max(np.abs(reconstructed - mass)))

    final_total = fsum_array(mass)
    global_residual = final_total - old_total - injected + produced
    global_tol = max(
        1.0e-5,
        1.0e-10
        * max(abs(final_total), abs(injected), abs(produced), 1.0),
    )

    final_flux = teacher_face_fluxes(
        a4=a4,
        r2=r2,
        saturation=final_sat_exact,
        q_m3_day=q_m3_day,
        face_pressure_psi=face_pressure_psi,
        p_ref_pa=p_ref_pa,
        nw=nw,
        no=no,
        krw_max=krw_max,
        kro_max=kro_max,
        phi_cv=phi_cv,
        cvgeom=cvgeom,
    )

    return {
        "future_mass": mass,
        "future_saturation": final_sat_exact,
        "future_mass_fraction": mass / cap,
        "injected_mass_kg": injected,
        "produced_mass_kg": produced,
        "delta_mass_kg": final_total - old_total,
        "global_mass_residual_kg": global_residual,
        "global_mass_tolerance_kg": global_tol,
        "substeps": steps,
        "advective_CFL_dt_days": adv_dt_days,
        "minimum_dt_days": min_dt_used,
        "maximum_dt_days": max_dt_used,
        "lookup_parent_saturation_max_abs_error": lookup_parent_error,
        "lookup_final_vs_exact_max_abs_error": lookup_final_error,
        "exact_final_mass_inversion_max_abs_kg": inversion_error,
        "max_step_mass_ledger_residual_kg": max_step_ledger,
        "max_capillary_boundary_mass_flux_kg_day": max_capillary_global_flux,
        "maximum_mass_fraction_seen": max_mass_fraction,
        "final_advective_mass_flux_kg_day": final_flux[
            "advective_mass_flux_kg_day"
        ],
        "final_capillary_mass_flux_kg_day": final_flux[
            "capillary_mass_flux_kg_day"
        ],
        "final_rhs_mass_kg_day": final_flux[
            "rhs_mass_kg_day"
        ],
    }


def exact_parent_mass_mapback(
    *,
    r2: Any,
    parent_grid_mass: np.ndarray,
    old_cv_saturation: np.ndarray,
    new_cv_saturation: np.ndarray,
    old_cv_mass: np.ndarray,
    new_cv_mass: np.ndarray,
    geometry: dict[str, np.ndarray],
    p_ref_pa: float,
) -> dict[str, Any]:
    cv_id = np.asarray(geometry["cv_id"], dtype=np.int64)
    flat = np.asarray(geometry["flat_cell"], dtype=np.int64)
    pv = np.asarray(geometry["pv_m3"], dtype=np.float64)
    pseg = np.asarray(geometry["pseg_psi"], dtype=np.float64)

    old_flat = np.asarray(old_cv_saturation, dtype=np.float64).reshape(-1)
    new_flat = np.asarray(new_cv_saturation, dtype=np.float64).reshape(-1)

    old_sub_sat = old_flat[cv_id]
    new_sub_sat = new_flat[cv_id]
    old_sg = np.clip(old_sub_sat - BACKGROUND, 0.0, MAX_SG)
    new_sg = np.clip(new_sub_sat - BACKGROUND, 0.0, MAX_SG)

    rho_old = np.asarray(
        r2.gas_density_from_state(old_sub_sat, pseg, p_ref_pa),
        dtype=np.float64,
    )
    rho_new = np.asarray(
        r2.gas_density_from_state(new_sub_sat, pseg, p_ref_pa),
        dtype=np.float64,
    )

    sub_delta = pv * (rho_new * new_sg - rho_old * old_sg)

    cv_delta = (
        fsum_array(new_cv_mass) - fsum_array(old_cv_mass)
    )
    sub_total = fsum_array(sub_delta)
    transfer_residual = sub_total - cv_delta
    transfer_tol = max(1.0e-6, 1.0e-10 * max(abs(cv_delta), 1.0))

    if abs(transfer_residual) > transfer_tol:
        raise ScientificFail(
            "F4_E37A_CV_to_subsegment_transfer_closure",
            {
                "residual_kg": transfer_residual,
                "tolerance_kg": transfer_tol,
            },
        )

    deposited = np.bincount(
        flat,
        weights=sub_delta,
        minlength=NCELL,
    ).reshape(GRID)

    future_mass = np.asarray(parent_grid_mass, dtype=np.float64) + deposited
    min_mass = float(np.min(future_mass))
    total_target = fsum_array(parent_grid_mass) + cv_delta
    ledger_residual = fsum_array(future_mass) - total_target
    roundoff = max(
        1.0e-6,
        1.0e-10 * max(abs(total_target), 1.0),
    )

    if min_mass < -roundoff:
        raise ScientificFail(
            "F4_mapback_negative_grid_cell_mass",
            {"minimum_kg": min_mass, "tolerance_kg": roundoff},
        )
    if abs(ledger_residual) > roundoff:
        raise ScientificFail(
            "F4_exact_parent_grid_mapback_ledger",
            {
                "residual_kg": ledger_residual,
                "tolerance_kg": roundoff,
            },
        )

    return {
        "future_grid_mass_kg": future_mass,
        "deposited_delta_mass_kg": deposited,
        "cv_delta_mass_kg": cv_delta,
        "subsegment_delta_mass_kg": sub_total,
        "transfer_residual_kg": transfer_residual,
        "target_final_mass_kg": total_target,
        "ledger_residual_kg": ledger_residual,
        "roundoff_mass_kg": roundoff,
    }


def bounded_reproject(
    *,
    r2: Any,
    e37: Any,
    sg7d: Any,
    xyz_m: np.ndarray,
    tof_s: np.ndarray,
    weights_m3_s: np.ndarray,
    grid_mass: np.ndarray,
    grid_pore_volume_m3: np.ndarray,
    pressure_psi: np.ndarray,
    p_ref_pa: float,
) -> dict[str, Any]:
    operator = sg7d.build_subsegment_operator(
        xyz_m,
        tof_s / SPD,
        weights_m3_s * SPD,
    )
    stream = np.asarray(operator["streamline"], dtype=np.int64)
    node = np.asarray(operator["node"], dtype=np.int64)
    flat = np.asarray(operator["flat_cell"], dtype=np.int64)
    pv = np.asarray(operator["pv_m3"], dtype=np.float64)

    if (
        int(np.min(stream)) != 0
        or int(np.max(stream)) != NSL - 1
        or int(np.min(node)) != 0
        or int(np.max(node)) != NCV - 1
    ):
        raise ScientificFail(
            "F4_target_reprojection_operator_index_contract",
            {
                "stream": [int(np.min(stream)), int(np.max(stream))],
                "node": [int(np.min(node)), int(np.max(node))],
            },
        )

    mass_flat = np.asarray(grid_mass, dtype=np.float64).reshape(-1)
    cell_pv_flat = np.asarray(
        grid_pore_volume_m3, dtype=np.float64
    ).reshape(-1)

    W = np.bincount(flat, weights=pv, minlength=NCELL)
    denom = np.maximum(cell_pv_flat, W)
    sub_mass = mass_flat[flat] * pv / denom[flat]
    mapped_cell = np.bincount(
        flat,
        weights=sub_mass,
        minlength=NCELL,
    )
    residual_flat = mass_flat - mapped_cell

    tol = max(
        1.0e-8,
        1.0e-12 * max(float(np.max(np.abs(mass_flat))), 1.0),
    )
    if float(np.min(residual_flat)) < -tol:
        raise ScientificFail(
            "F4_target_reprojection_negative_residual",
            float(np.min(residual_flat)),
        )

    cv_id = stream * NCV + node
    cv_mass = np.bincount(
        cv_id,
        weights=sub_mass,
        minlength=NSL * NCV,
    ).reshape(NSL, NCV)

    geometry = e37.build_control_volume_geometry(
        r2,
        operator,
        pressure_psi,
        p_ref_pa,
        NSL,
        NCV,
    )
    coeff = np.asarray(
        geometry["cv_pressure_mass_coeff"], dtype=np.float64
    )
    cv_pv = np.asarray(geometry["cv_pv_m3"], dtype=np.float64)
    capacity = np.asarray(
        e37.cv_mass_from_saturation(
            r2,
            np.full((NSL, NCV), INJECTED, dtype=np.float64),
            coeff,
        ),
        dtype=np.float64,
    )
    excess = cv_mass - capacity
    cap_tol = max(
        1.0e-9,
        1.0e-12 * max(float(np.max(np.abs(cv_mass))), 1.0),
    )
    overloaded = int(np.sum(excess > cap_tol))
    if overloaded:
        worst = np.unravel_index(int(np.argmax(excess)), excess.shape)
        raise ScientificFail(
            "F4_target_reprojection_CV_capacity",
            {
                "overloaded_CV_count": overloaded,
                "max_excess_kg": float(np.max(excess)),
                "worst_streamline": int(worst[0]),
                "worst_CV": int(worst[1]),
            },
        )

    cv_sat = np.asarray(
        e37.invert_cv_mass_to_saturation(r2, cv_mass, coeff),
        dtype=np.float64,
    )

    total = fsum_array(grid_mass)
    mapped_total = fsum_array(cv_mass)
    residual_total = fsum_array(residual_flat)
    ledger = mapped_total + residual_total - total
    mass_tol = max(1.0e-6, 1.0e-10 * max(abs(total), 1.0))
    if abs(ledger) > mass_tol:
        raise ScientificFail(
            "F4_target_split_state_global_ledger",
            {"residual_kg": ledger, "tolerance_kg": mass_tol},
        )

    return {
        "operator": operator,
        "geometry": geometry,
        "cv_mass": cv_mass,
        "cv_saturation": cv_sat,
        "cv_capacity": capacity,
        "cv_pore_volume_m3": cv_pv,
        "cv_pressure_mass_coeff": coeff,
        "residual_grid_mass": residual_flat.reshape(GRID),
        "occupancy_fraction_alpha": np.minimum(
            1.0, W / cell_pv_flat
        ).reshape(GRID),
        "W_m3": W.reshape(GRID),
        "mapped_grid_mass": mapped_cell.reshape(GRID),
        "subsegment_mass": sub_mass,
        "mapped_mass_kg": mapped_total,
        "residual_mass_kg": residual_total,
        "ledger_residual_kg": ledger,
        "overloaded_CV_count": overloaded,
        "maximum_capacity_excess_kg": float(np.max(excess)),
    }


def self_test() -> None:
    assert len(CHANNELS17) == 17
    assert model_parameter_count(17, 64) == 54081
    assert PARENT_DAY + DELTA_DAY == TARGET_DAY

    # Synthetic conservative face-divergence identity.
    ns, n = 2, 3
    adv = np.array(
        [
            [10.0, 8.0, 5.0, 2.0],
            [9.0, 7.0, 4.0, 1.0],
        ]
    )
    cap = np.array(
        [
            [0.0, 1.5, -0.5, 0.0],
            [0.0, -2.0, 0.75, 0.0],
        ]
    )
    rhs = adv[:, :-1] - adv[:, 1:] + cap[:, :-1] - cap[:, 1:]
    assert abs(
        float(np.sum(rhs))
        - float(np.sum(adv[:, 0]) - np.sum(adv[:, -1]))
    ) < 1.0e-14

    # Bounded occupancy cell ledger.
    parent = np.array([12.0, 8.0])
    pvcell = np.array([10.0, 4.0])
    flat = np.array([0, 0, 1, 1])
    pv = np.array([1.0, 3.0, 2.0, 4.0])
    W = np.bincount(flat, weights=pv, minlength=2)
    sub = parent[flat] * pv / np.maximum(pvcell, W)[flat]
    mapped = np.bincount(flat, weights=sub, minlength=2)
    residual = parent - mapped
    assert np.allclose(mapped + residual, parent)

    print(
        "POSTV16-AV4-F4 Day365->Day500 restart teacher / "
        "conservative-loop self-test: PASS"
    )


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    failed = drive / FAIL_REL
    blocked = drive / BLOCK_REL

    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"
    teacher_started = False
    mapback_executed = False
    target_refresh_executed = False
    target_reprojection_executed = False
    model_built = False

    def gate(name: str, passed: Any, value: Any = None) -> None:
        ok = bool(passed)
        gates[name] = {"passed": ok, "value": value}
        print(
            f"[{'PASS' if ok else 'FAIL'}] {name}"
            + (f" — {value}" if value is not None else "")
        )
        if not ok:
            raise GateError(name)

    def sci_gate(name: str, passed: Any, value: Any = None) -> None:
        ok = bool(passed)
        gates[name] = {
            "passed": ok,
            "value": value,
            "scientific_execution_gate": True,
        }
        print(
            f"[{'PASS' if ok else 'FAIL'}] {name}"
            + (f" — {value}" if value is not None else "")
        )
        if not ok:
            raise ScientificFail(name, value)

    print("=" * 214)
    print(
        "POSTV16-AV4-F4 — CONTROLLED DAY365→DAY500 200-CV / 17-CHANNEL "
        "RESTART TEACHER + CONSERVATIVE RECURRENT-LOOP CERTIFICATION"
    )
    print("=" * 214)
    print("SINGLE VALIDATION CONTROL TRANSITION ONLY: AV3CR0003 / AV2PHI0003 / 365→500 DAYS.")
    print("NO MODEL TRAINING. NO CHECKPOINT CREATION/SELECTION/INFERENCE. NO LOCKED OOD OPENING.")
    print("NO HYPERPARAMETER SEARCH. NO SUPPORT EXPANSION. NO MASS CLIPPING/RESCALING. NO CMG.")
    print()

    try:
        # ------------------------------------------------------------------------------------------
        # Repository authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"

        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")
        gate("repository_parent_is_F3_commit", parent == PARENT_F3_COMMIT, parent)
        gate("repository_clean", status == "", repr(status))

        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        # ------------------------------------------------------------------------------------------
        # Formal F3 binding.
        # ------------------------------------------------------------------------------------------
        stage = "F3_protocol_binding"

        f3d = drive / F3_REL
        gate("F3_output_present", f3d.is_dir(), str(f3d))
        mf3 = verify_manifest(f3d, F3_MANIFEST)
        gate("F3_manifest_exact_8", len(mf3) == 8, len(mf3))

        sf3 = load_json(f3d / F3_SUMMARY)
        mod3 = load_json(f3d / F3_MODEL)
        tmp3 = load_json(f3d / F3_TEMPORAL)
        tea3 = load_json(f3d / F3_TEACHER)
        tr3 = load_json(f3d / F3_TRAIN)
        h3 = load_json(f3d / F3_HANDOFF)
        d3 = load_json(f3d / F3_DECISION)

        gate("F3_status_exact", sf3["status"] == F3_STATUS, sf3["status"])
        gate(
            "F3_model_signature_exact",
            int(sf3["sequence_length"]) == NCV
            and int(sf3["input_channels"]) == INPUT_CHANNELS
            and int(sf3["model_parameters"]) == MODEL_PARAMETERS
            and sf3["channel_order"] == CHANNELS17
            and mod3["explicit_parent_state_channels"]
            == ["parent_CV_saturation_hat", "parent_CV_mass_fraction"],
        )
        gate(
            "F3_temporal_semantics_exact",
            float(tmp3["first_controlled_transition"]["parent_day"]) == PARENT_DAY
            and float(tmp3["first_controlled_transition"]["target_day"]) == TARGET_DAY
            and float(tmp3["first_controlled_transition"]["delta_day"]) == DELTA_DAY,
        )
        gate(
            "F3_teacher_loop_exact",
            tea3["execution_in_F3"] is False
            and tea3["residual_grid_participation"]["neural_prediction"] is False
            and "Delta_M_CV" in tea3[
                "residual_grid_participation"
            ]["conservative_future_grid_update"],
        )
        gate(
            "F3_validation_and_OOD_firewall_exact",
            tr3["realization_split"]["VALIDATION"] == [CONTROL_REALIZATION]
            and tr3["first_controlled_teacher_pair_is_validation_only"] is True
            and tr3["checkpoint_and_OOD"]["OOD_teacher_target_access_before_checkpoint"] is False,
        )
        gate(
            "F3_F4_handoff_exact",
            h3["milestone"] == MILESTONE
            and h3["authorized"] is True
            and h3["execution"] is True
            and h3["control_realization"] == CONTROL_REALIZATION
            and h3["paired_porosity"] == CONTROL_POROSITY
            and h3["partition"] == CONTROL_PARTITION
            and float(h3["parent_day"]) == PARENT_DAY
            and float(h3["target_day"]) == TARGET_DAY
            and float(h3["delta_day"]) == DELTA_DAY,
            h3,
        )
        gate(
            "F3_downstream_firewalls",
            d3["F4_authorized"] is True
            and d3["F4_execution_authorized"] is True
            and d3["F5_dataset_generation_authorized"] is False
            and d3["training_performed"] is False
            and d3["checkpoint_created"] is False
            and d3["A3_E2_authorized"] is False
            and d3["AV4_dynamic_transport_execution_authorized"] is False,
        )

        # ------------------------------------------------------------------------------------------
        # Bind F2-R3 parent split state, E1-R2 refreshed X13, and A2-E flow epoch.
        # ------------------------------------------------------------------------------------------
        stage = "parent_authority_binding"

        f2d = drive / F2R3_REL
        gate("F2R3_output_present", f2d.is_dir(), str(f2d))
        mf2 = verify_manifest(f2d, F2R3_MANIFEST)
        gate("F2R3_manifest_exact_9", len(mf2) == 9, len(mf2))
        sf2 = load_json(f2d / F2R3_SUMMARY)
        gate("F2R3_status_exact", sf2["status"] == F2R3_STATUS, sf2["status"])
        gate("F2R3_state_manifested", F2R3_STATE in mf2, F2R3_STATE)

        with np.load(f2d / F2R3_STATE, allow_pickle=False) as z:
            parent_cv_mass = np.asarray(z["parent_CV_component_mass_kg"], dtype=np.float64)
            parent_cv_sat = np.asarray(z["parent_CV_saturation"], dtype=np.float64)
            parent_cv_capacity = np.asarray(z["parent_CV_capacity_kg"], dtype=np.float64)
            parent_cv_pv = np.asarray(z["parent_CV_pore_volume_m3"], dtype=np.float64)
            parent_cv_coeff = np.asarray(z["parent_CV_pressure_mass_coeff"], dtype=np.float64)
            parent_mapped_grid = np.asarray(z["mapped_grid_component_mass_kg"], dtype=np.float64)
            parent_residual_grid = np.asarray(z["residual_grid_component_mass_kg"], dtype=np.float64)
            parent_total_state = float(np.asarray(z["parent_total_mass_kg"]).reshape(()))

        gate(
            "F2R3_parent_state_shapes_exact",
            parent_cv_mass.shape == (NSL, NCV)
            and parent_cv_sat.shape == (NSL, NCV)
            and parent_cv_capacity.shape == (NSL, NCV)
            and parent_cv_pv.shape == (NSL, NCV)
            and parent_cv_coeff.shape == (NSL, NCV)
            and parent_mapped_grid.shape == GRID
            and parent_residual_grid.shape == GRID,
        )

        e1d = drive / E1R2_REL
        gate("E1R2_output_present", e1d.is_dir(), str(e1d))
        me1 = verify_manifest(e1d, E1R2_MANIFEST)
        gate("E1R2_manifest_exact_9", len(me1) == 9, len(me1))
        se1 = load_json(e1d / E1R2_SUMMARY)
        gate("E1R2_status_exact", se1["status"] == E1R2_STATUS, se1["status"])
        gate("E1R2_X13_manifested", E1R2_X13 in me1, E1R2_X13)

        with np.load(e1d / E1R2_X13, allow_pickle=False) as z:
            X13 = np.asarray(z["X_refreshed_13"], dtype=np.float64)
            x13_channels = [str(x) for x in np.asarray(z["channel_names"]).tolist()]
            x13_tau_end = np.asarray(z["terminal_pollock_tof_s"], dtype=np.float64)

        gate("E1R2_X13_shape_exact", X13.shape == (NSL, NN, 13), X13.shape)
        gate(
            "E1R2_X13_channel_order_exact",
            x13_channels
            == [
                "xi",
                "pollock_tau_hat",
                "adv_tau_hat",
                "log10_Kh",
                "log10_Kz_over_Kh",
                "porosity",
                "pressure_z",
                "target_time_hat",
                "target_eta_sequence",
                "nw_hat",
                "no_hat",
                "krw_max_hat",
                "kro_max_hat",
            ],
            x13_channels,
        )

        a2d = drive / A2E_REL
        gate("A2E_output_present", a2d.is_dir(), str(a2d))
        ma2 = verify_manifest(a2d, A2E_MANIFEST)
        gate("A2E_manifest_exact_12", len(ma2) == 12, len(ma2))
        sa2 = load_json(a2d / A2E_SUMMARY)
        gate("A2E_status_exact", sa2["status"] == A2E_STATUS, sa2["status"])

        with np.load(a2d / A2E_EPOCH, allow_pickle=False) as z:
            epoch = {k: np.asarray(z[k]).copy() for k in z.files}

        required_epoch = {
            "parent_component_mass_kg",
            "reconciled_saturation",
            "refreshed_pressure_psi",
            "pore_volume_m3",
            "reference_gas_pressure_pa",
            "streamline_xyz_m",
            "streamline_tof_s",
            "streamline_weight_m3_s",
            "streamline_face_pressure_psi",
            "xi",
            "nw",
            "no",
            "krw_max",
            "kro_max",
            "paired_porosity",
        }
        gate(
            "A2E_required_F4_arrays_present",
            required_epoch.issubset(set(epoch)),
            sorted(required_epoch),
        )

        parent_grid_mass = np.asarray(epoch["parent_component_mass_kg"], dtype=np.float64)
        parent_grid_sat = np.asarray(epoch["reconciled_saturation"], dtype=np.float64)
        parent_pressure = np.asarray(epoch["refreshed_pressure_psi"], dtype=np.float64)
        grid_pv = np.asarray(epoch["pore_volume_m3"], dtype=np.float64)
        p_ref = float(np.asarray(epoch["reference_gas_pressure_pa"]).reshape(()))
        parent_xyz = np.asarray(epoch["streamline_xyz_m"], dtype=np.float64)
        parent_tof = np.asarray(epoch["streamline_tof_s"], dtype=np.float64)
        parent_weights_s = np.asarray(epoch["streamline_weight_m3_s"], dtype=np.float64)
        parent_face_pressure = np.asarray(epoch["streamline_face_pressure_psi"], dtype=np.float64)
        xi_raw = np.asarray(epoch["xi"], dtype=np.float64)
        grid_nw = np.asarray(epoch["nw"], dtype=np.float64)
        grid_no = np.asarray(epoch["no"], dtype=np.float64)
        grid_krw = np.asarray(epoch["krw_max"], dtype=np.float64)
        grid_kro = np.asarray(epoch["kro_max"], dtype=np.float64)

        xi_1d = xi_raw.reshape(-1)
        gate(
            "A2E_F4_parent_shapes_exact",
            parent_grid_mass.shape == GRID
            and parent_grid_sat.shape == GRID
            and parent_pressure.shape == GRID
            and grid_pv.shape == GRID
            and parent_xyz.shape == (NSL, NN, 3)
            and parent_tof.shape == (NSL, NN)
            and parent_weights_s.shape == (NSL,)
            and parent_face_pressure.shape == (NSL, NN)
            and xi_1d.shape == (NN,)
            and grid_nw.shape == GRID
            and grid_no.shape == GRID
            and grid_krw.shape == GRID
            and grid_kro.shape == GRID,
        )
        f2r3_reconstructed_parent_grid = (
            parent_mapped_grid + parent_residual_grid
        )
        parent_grid_array_rel_l2 = relative_l2(
            parent_grid_mass,
            f2r3_reconstructed_parent_grid,
        )
        parent_grid_array_linf = float(
            np.max(
                np.abs(
                    parent_grid_mass
                    - f2r3_reconstructed_parent_grid
                )
            )
        )
        parent_grid_total_residual = (
            fsum_array(parent_grid_mass) - parent_total_state
        )
        parent_grid_authority_tol = max(
            1.0e-8,
            1.0e-12
            * max(
                float(np.max(np.abs(parent_grid_mass))),
                1.0,
            ),
        )

        gate(
            "parent_grid_mass_equals_F2R3_full_array_authority",
            parent_grid_array_rel_l2 <= 1.0e-12
            and parent_grid_array_linf <= parent_grid_authority_tol
            and abs(parent_grid_total_residual)
            <= max(1.0e-6, 1.0e-10 * parent_total_state),
            {
                "array_relative_L2": parent_grid_array_rel_l2,
                "array_Linf_kg": parent_grid_array_linf,
                "array_tolerance_kg": parent_grid_authority_tol,
                "A2E_grid_total_kg": fsum_array(parent_grid_mass),
                "F2R3_total_kg": parent_total_state,
                "total_residual_kg": parent_grid_total_residual,
            },
        )
        gate(
            "E1R2_and_A2E_tau_end_match",
            float(np.max(np.abs(x13_tau_end - parent_tof[:, -1]))) <= 1.0e-8,
            float(np.max(np.abs(x13_tau_end - parent_tof[:, -1]))),
        )

        # ------------------------------------------------------------------------------------------
        # Source module binding.
        # ------------------------------------------------------------------------------------------
        stage = "source_module_binding"

        a4 = load_module(root / A4R2, "postv16_av4_f4_a4")
        a2e = load_module(root / A2E, "postv16_av4_f4_a2e")
        r2 = load_module(root / R2, "postv16_av4_f4_r2")
        e37 = load_module(root / E37A, "postv16_av4_f4_e37a")
        sg2 = load_module(root / SG2, "postv16_av4_f4_sg2")
        sg3 = load_module(root / SG3, "postv16_av4_f4_sg3")
        sg4 = load_module(root / SG4, "postv16_av4_f4_sg4")
        sg5 = load_module(root / SG5, "postv16_av4_f4_sg5")
        sg6 = load_module(root / SG6, "postv16_av4_f4_sg6")
        sg7d = load_module(root / SG7D, "postv16_av4_f4_sg7d")
        r3r2r1 = load_module(root / R3R2R1, "postv16_av4_f4_r3r2r1")

        gate(
            "source_authentic_teacher_functions_present",
            hasattr(a4, "local_fw")
            and hasattr(a4, "local_dshape")
            and hasattr(a4, "max_dfw_realization"),
        )
        gate(
            "source_authentic_recurrent_loop_functions_present",
            hasattr(a2e, "fixed_point_refresh")
            and hasattr(a2e, "invert_local_mass")
            and hasattr(e37, "build_control_volume_geometry")
            and hasattr(e37, "invert_cv_mass_to_saturation")
            and hasattr(sg7d, "build_subsegment_operator"),
        )

        # ------------------------------------------------------------------------------------------
        # Build exact 17-channel parent predictor tensor.
        # ------------------------------------------------------------------------------------------
        stage = "X17_predictor_construction"

        cvavg = 0.5 * (X13[:, :-1, :] + X13[:, 1:, :])
        delta_eta = DELTA_DAY * SPD / parent_tof[:, -1]

        parent_sat_hat = (parent_cv_sat - BACKGROUND) / MAX_SG
        parent_mass_fraction = parent_cv_mass / parent_cv_capacity

        X17 = np.stack(
            [
                cvavg[:, :, 0],
                cvavg[:, :, 1],
                cvavg[:, :, 2],
                cvavg[:, :, 3],
                cvavg[:, :, 4],
                cvavg[:, :, 5],
                cvavg[:, :, 6],
                np.full((NSL, NCV), PARENT_DAY / 1000.0),
                np.full((NSL, NCV), TARGET_DAY / 1000.0),
                np.full((NSL, NCV), DELTA_DAY / 1000.0),
                np.broadcast_to(delta_eta[:, None], (NSL, NCV)),
                cvavg[:, :, 9],
                cvavg[:, :, 10],
                cvavg[:, :, 11],
                cvavg[:, :, 12],
                parent_sat_hat,
                parent_mass_fraction,
            ],
            axis=-1,
        )

        sci_gate("X17_shape_exact", X17.shape == (NSL, NCV, 17), X17.shape)
        sci_gate("X17_finite", np.isfinite(X17).all())
        sci_gate(
            "X17_parent_state_bounds",
            float(np.min(parent_sat_hat)) >= -1.0e-12
            and float(np.max(parent_sat_hat)) <= 1.0 + 1.0e-12
            and float(np.min(parent_mass_fraction)) >= -1.0e-12
            and float(np.max(parent_mass_fraction)) <= 1.0 + 1.0e-12,
            {
                "sat_hat": [float(np.min(parent_sat_hat)), float(np.max(parent_sat_hat))],
                "mass_fraction": [
                    float(np.min(parent_mass_fraction)),
                    float(np.max(parent_mass_fraction)),
                ],
            },
        )

        # Physical CV fields recovered from the certified X13 representation.
        phi_cv = cvavg[:, :, 5]
        nw_cv = 3.0 + cvavg[:, :, 9]
        no_cv = 3.0 + cvavg[:, :, 10]
        krw_cv = 0.80 + 0.20 * cvavg[:, :, 11]
        kro_cv = 0.80 + 0.20 * cvavg[:, :, 12]

        cvgeom = build_cv_geometry_from_faces(parent_tof, xi_1d)

        # ------------------------------------------------------------------------------------------
        # Build untrained F3 architecture. No compile, fit, checkpoint, or inference.
        # ------------------------------------------------------------------------------------------
        stage = "untrained_model_signature_certification"

        try:
            import tensorflow as tf

            tf.keras.backend.clear_session()
            tf.keras.utils.set_random_seed(TRAINING_SEED)

            model = tf.keras.Sequential(
                [
                    tf.keras.layers.Input(shape=(NCV, INPUT_CHANNELS)),
                    tf.keras.layers.LSTM(HIDDEN_UNITS, return_sequences=True),
                    tf.keras.layers.LSTM(HIDDEN_UNITS, return_sequences=True),
                    tf.keras.layers.TimeDistributed(
                        tf.keras.layers.Dense(1, activation="sigmoid")
                    ),
                ],
                name="POSTV16_AV4_F3_200CV_17Channel_Restart_Model",
            )
            parameter_count = int(model.count_params())
            model_json = model.to_json()
            model_built = True
        except Exception as exc:
            raise GateError("F4_untrained_model_build_failure:" + repr(exc)) from exc

        gate(
            "untrained_model_parameter_count_54081",
            parameter_count == MODEL_PARAMETERS
            and parameter_count == model_parameter_count(17, 64),
            parameter_count,
        )
        gate(
            "untrained_model_output_shape_exact",
            tuple(model.output_shape) == (None, NCV, 1),
            model.output_shape,
        )

        # ------------------------------------------------------------------------------------------
        # Rebuild parent E37A geometry and bind F2-R3 CV coefficients.
        # ------------------------------------------------------------------------------------------
        stage = "parent_E37A_geometry_binding"

        parent_operator = sg7d.build_subsegment_operator(
            parent_xyz,
            parent_tof / SPD,
            parent_weights_s * SPD,
        )
        parent_geometry = e37.build_control_volume_geometry(
            r2,
            parent_operator,
            parent_pressure,
            p_ref,
            NSL,
            NCV,
        )

        sci_gate(
            "parent_CV_pore_volume_matches_F2R3",
            float(
                np.max(
                    np.abs(
                        np.asarray(parent_geometry["cv_pv_m3"])
                        - parent_cv_pv
                    )
                )
            )
            <= 1.0e-8,
            float(
                np.max(
                    np.abs(
                        np.asarray(parent_geometry["cv_pv_m3"])
                        - parent_cv_pv
                    )
                )
            ),
        )
        sci_gate(
            "parent_CV_pressure_coeff_matches_F2R3",
            relative_l2(
                np.asarray(parent_geometry["cv_pressure_mass_coeff"]),
                parent_cv_coeff,
            )
            <= 1.0e-12,
            relative_l2(
                np.asarray(parent_geometry["cv_pressure_mass_coeff"]),
                parent_cv_coeff,
            ),
        )

        # ------------------------------------------------------------------------------------------
        # Controlled 365->500 teacher execution.
        # ------------------------------------------------------------------------------------------
        stage = "controlled_200CV_restart_teacher"
        teacher_started = True
        t0 = time.time()

        teacher = execute_teacher_with_coeff(
            a4=a4,
            r2=r2,
            e37=e37,
            old_mass=parent_cv_mass,
            old_sat=parent_cv_sat,
            capacity=parent_cv_capacity,
            cv_pressure_mass_coeff=parent_cv_coeff,
            cv_pv_m3=parent_cv_pv,
            face_pressure_psi=parent_face_pressure,
            p_ref_pa=p_ref,
            q_m3_day=parent_weights_s * SPD,
            nw=nw_cv,
            no=no_cv,
            krw_max=krw_cv,
            kro_max=kro_cv,
            phi_cv=phi_cv,
            cvgeom=cvgeom,
            delta_days=DELTA_DAY,
        )
        teacher_elapsed = float(time.time() - t0)

        sci_gate(
            "teacher_global_component_mass_closure",
            abs(float(teacher["global_mass_residual_kg"]))
            <= float(teacher["global_mass_tolerance_kg"]),
            {
                "residual_kg": teacher["global_mass_residual_kg"],
                "tolerance_kg": teacher["global_mass_tolerance_kg"],
            },
        )
        sci_gate(
            "teacher_capillary_boundary_mass_flux_zero",
            float(teacher["max_capillary_boundary_mass_flux_kg_day"])
            <= 1.0e-12,
            teacher["max_capillary_boundary_mass_flux_kg_day"],
        )
        sci_gate(
            "teacher_lookup_parent_matches_exact_state",
            float(teacher["lookup_parent_saturation_max_abs_error"])
            <= 5.0e-6,
            teacher["lookup_parent_saturation_max_abs_error"],
        )
        sci_gate(
            "teacher_lookup_final_matches_exact_inversion",
            float(teacher["lookup_final_vs_exact_max_abs_error"])
            <= 5.0e-6,
            teacher["lookup_final_vs_exact_max_abs_error"],
        )
        sci_gate(
            "teacher_final_mass_inversion_closure",
            float(teacher["exact_final_mass_inversion_max_abs_kg"])
            <= max(
                1.0e-6,
                1.0e-10
                * max(float(np.max(np.abs(teacher["future_mass"]))), 1.0),
            ),
            teacher["exact_final_mass_inversion_max_abs_kg"],
        )
        sci_gate(
            "teacher_future_mass_fraction_bounds",
            float(np.min(teacher["future_mass_fraction"])) >= -1.0e-10
            and float(np.max(teacher["future_mass_fraction"])) <= 1.0 + 1.0e-10,
            [
                float(np.min(teacher["future_mass_fraction"])),
                float(np.max(teacher["future_mass_fraction"])),
            ],
        )

        # Conservative residual algebra on the supervised parent->future pair.
        mid_sat = 0.5 * (
            parent_cv_sat + teacher["future_saturation"]
        )
        mid_flux = teacher_face_fluxes(
            a4=a4,
            r2=r2,
            saturation=mid_sat,
            q_m3_day=parent_weights_s * SPD,
            face_pressure_psi=parent_face_pressure,
            p_ref_pa=p_ref,
            nw=nw_cv,
            no=no_cv,
            krw_max=krw_cv,
            kro_max=kro_cv,
            phi_cv=phi_cv,
            cvgeom=cvgeom,
        )
        pair_residual = (
            (
                teacher["future_mass_fraction"]
                - parent_mass_fraction
            )
            / (DELTA_DAY / 1000.0)
            - (
                1000.0
                * mid_flux["rhs_mass_kg_day"]
                / parent_cv_capacity
            )
        )
        sci_gate(
            "200CV_physics_pair_residual_finite",
            np.isfinite(pair_residual).all(),
        )

        mid_global_rhs = fsum_array(mid_flux["rhs_mass_kg_day"])
        mid_boundary_rhs = (
            fsum_array(mid_flux["advective_mass_flux_kg_day"][:, 0])
            - fsum_array(mid_flux["advective_mass_flux_kg_day"][:, -1])
        )
        sci_gate(
            "200CV_conservative_face_algebra_global_identity",
            abs(mid_global_rhs - mid_boundary_rhs)
            <= max(1.0e-8, 1.0e-12 * max(abs(mid_boundary_rhs), 1.0)),
            mid_global_rhs - mid_boundary_rhs,
        )

        # ------------------------------------------------------------------------------------------
        # Conservative CV increment mapback onto exact full parent grid mass.
        # ------------------------------------------------------------------------------------------
        stage = "E37A_exact_parent_mass_increment_mapback"

        mapback = exact_parent_mass_mapback(
            r2=r2,
            parent_grid_mass=parent_grid_mass,
            old_cv_saturation=parent_cv_sat,
            new_cv_saturation=teacher["future_saturation"],
            old_cv_mass=parent_cv_mass,
            new_cv_mass=teacher["future_mass"],
            geometry=parent_geometry,
            p_ref_pa=p_ref,
        )
        mapback_executed = True

        expected_future_total = (
            fsum_array(parent_grid_mass)
            + float(teacher["injected_mass_kg"])
            - float(teacher["produced_mass_kg"])
        )
        sci_gate(
            "parent_to_future_full_grid_mass_ledger",
            abs(
                fsum_array(mapback["future_grid_mass_kg"])
                - expected_future_total
            )
            <= float(mapback["roundoff_mass_kg"]),
            {
                "future_grid_mass_kg": fsum_array(mapback["future_grid_mass_kg"]),
                "expected_kg": expected_future_total,
                "tolerance_kg": mapback["roundoff_mass_kg"],
            },
        )

        # Preliminary future saturation under parent pressure for fixed-point start.
        try:
            future_sg_parent_pressure = a2e.invert_local_mass(
                r2,
                mapback["future_grid_mass_kg"],
                parent_pressure,
                p_ref,
                grid_pv,
            )
        except Exception as exc:
            raise ScientificFail(
                "F4_future_grid_parent_pressure_mass_inversion",
                repr(exc),
            ) from exc

        future_sat_start = BACKGROUND + np.asarray(
            future_sg_parent_pressure, dtype=np.float64
        )

        # ------------------------------------------------------------------------------------------
        # Target-Day500 same-time pressure / flow / Pollock / TOF refresh.
        # ------------------------------------------------------------------------------------------
        stage = "Day500_same_time_dynamic_flow_refresh"

        permeability_md = np.loadtxt(
            root / PERM,
            skiprows=1,
            dtype=np.float64,
        ).reshape(GRID, order="C")

        try:
            refresh = a2e.fixed_point_refresh(
                r2=r2,
                r3r2r1=r3r2r1,
                sg2=sg2,
                sg3=sg3,
                permeability_md=permeability_md,
                parent_mass=mapback["future_grid_mass_kg"],
                parent_saturation=future_sat_start,
                parent_pressure_psi=parent_pressure,
                p_ref_gas_pa=p_ref,
                pore_volume_m3=grid_pv,
                nw=grid_nw,
                no=grid_no,
                krw_max=grid_krw,
                kro_max=grid_kro,
                sci_gate=sci_gate,
            )
        except ScientificFail:
            raise
        except Exception as exc:
            raise ScientificFail(
                "F4_Day500_fixed_point_refresh_failure",
                repr(exc),
            ) from exc

        target_refresh_sat = np.asarray(refresh["saturation"], dtype=np.float64)
        target_pressure = np.asarray(refresh["pressure_psi"], dtype=np.float64)

        try:
            producer_rates, producer_sink = r3r2r1.producer_rates_updated(
                sg3,
                target_pressure,
                refresh["producer_wi"],
            )
            qx, qy, qz = sg4.compute_face_fluxes(
                target_pressure,
                refresh["tx"],
                refresh["ty"],
                refresh["tz"],
            )
            conservation = r3r2r1.flow_conservation_metrics(
                sg3,
                sg4,
                qx,
                qy,
                qz,
                producer_sink,
            )
        except Exception as exc:
            raise ScientificFail(
                "F4_Day500_Darcy_flow_failure",
                repr(exc),
            ) from exc

        sci_gate(
            "Day500_all_BHP_wells_remain_producers",
            all(float(v["m3_s"]) > 0.0 for v in producer_rates.values()),
            {k: float(v["m3_day"]) for k, v in producer_rates.items()},
        )
        sci_gate(
            "Day500_Darcy_local_conservation",
            conservation["local_relative_l2_error"] < 1.0e-8,
            conservation["local_relative_l2_error"],
        )
        sci_gate(
            "Day500_Darcy_global_conservation",
            conservation["global_relative_mismatch"] < 1.0e-8,
            conservation["global_relative_mismatch"],
        )

        try:
            vx, vy, vz = sg5.construct_face_pore_velocities(qx, qy, qz)
            faces, seeds = sg5.build_seeds(qx, qy, qz)
            target_streamlines = sg5.trace_streamlines(seeds, vx, vy, vz)
            sg5_validation = sg5.validate_streamlines(
                faces,
                seeds,
                target_streamlines,
            )
        except Exception as exc:
            raise ScientificFail(
                "F4_Day500_Pollock_retrace_failure",
                repr(exc),
            ) from exc

        statuses = [str(s["status"]) for s in target_streamlines]
        sci_gate(
            "Day500_all_streamlines_producer_captured",
            len(target_streamlines) == NSL
            and all(s == "PRODUCER" for s in statuses),
            {
                "count": len(target_streamlines),
                "status_counts": {
                    s: statuses.count(s) for s in sorted(set(statuses))
                },
            },
        )

        try:
            target_sg6_streamlines = a2e.convert_sg5_to_sg6(
                target_streamlines
            )
            target_db = sg6.build_transport_database(target_sg6_streamlines)
            sg6.validate_transport(target_db)
        except Exception as exc:
            raise ScientificFail(
                "F4_Day500_SG6_TOF_failure",
                repr(exc),
            ) from exc

        target_xyz = np.asarray(target_db["xyz_m"], dtype=np.float64)
        target_tof = np.asarray(target_db["tau_s"], dtype=np.float64)
        target_weights_s = np.asarray(
            target_db["weights_m3_s"], dtype=np.float64
        )
        target_tau_end = np.asarray(
            target_db["tau_end_s"], dtype=np.float64
        )
        target_xi = np.asarray(target_db["xi"], dtype=np.float64)

        sci_gate(
            "Day500_streamline_signature_shape_preserved",
            target_xyz.shape == (NSL, NN, 3)
            and target_tof.shape == (NSL, NN)
            and target_weights_s.shape == (NSL,)
            and target_xi.reshape(-1).shape == (NN,),
            {
                "xyz": target_xyz.shape,
                "tof": target_tof.shape,
                "weights": target_weights_s.shape,
                "xi": target_xi.shape,
            },
        )
        sci_gate(
            "Day500_TOF_positive_monotone",
            np.all(target_tau_end > 0.0)
            and np.all(np.diff(target_tof, axis=1) >= -1.0e-12),
            {
                "tau_min_days": float(np.min(target_tau_end) / SPD),
                "tau_max_days": float(np.max(target_tau_end) / SPD),
            },
        )
        target_refresh_executed = True

        target_face_pressure = a2e.sample_pressure_at_streamline_nodes(
            sg7d,
            target_xyz,
            target_pressure,
        )

        # ------------------------------------------------------------------------------------------
        # Target-Day500 bounded split-state reprojection.
        # ------------------------------------------------------------------------------------------
        stage = "Day500_bounded_split_state_reprojection"

        target_split = bounded_reproject(
            r2=r2,
            e37=e37,
            sg7d=sg7d,
            xyz_m=target_xyz,
            tof_s=target_tof,
            weights_m3_s=target_weights_s,
            grid_mass=mapback["future_grid_mass_kg"],
            grid_pore_volume_m3=grid_pv,
            pressure_psi=target_pressure,
            p_ref_pa=p_ref,
        )
        target_reprojection_executed = True

        sci_gate(
            "Day500_reprojection_zero_overloaded_CVs",
            target_split["overloaded_CV_count"] == 0,
            {
                "overloaded": target_split["overloaded_CV_count"],
                "max_excess_kg": target_split["maximum_capacity_excess_kg"],
            },
        )
        sci_gate(
            "Day500_split_state_global_mass_closure",
            abs(float(target_split["ledger_residual_kg"]))
            <= max(
                1.0e-6,
                1.0e-10
                * max(
                    fsum_array(mapback["future_grid_mass_kg"]),
                    1.0,
                ),
            ),
            target_split["ledger_residual_kg"],
        )

        # Target refresh must preserve the exact future grid mass under EOS.
        target_mass_recon = a2e.local_mass(
            r2,
            target_refresh_sat,
            target_pressure,
            p_ref,
            grid_pv,
        )
        sci_gate(
            "Day500_refreshed_saturation_exact_future_mass",
            relative_l2(
                target_mass_recon,
                mapback["future_grid_mass_kg"],
            )
            <= 1.0e-10,
            relative_l2(
                target_mass_recon,
                mapback["future_grid_mass_kg"],
            ),
        )

        # ------------------------------------------------------------------------------------------
        # Final accepted F4 artifacts / F5 handoff.
        # ------------------------------------------------------------------------------------------
        stage = "final_certification_and_publish"

        parent_mass_total = fsum_array(parent_grid_mass)
        future_mass_total = fsum_array(mapback["future_grid_mass_kg"])
        target_residual_total = fsum_array(
            target_split["residual_grid_mass"]
        )

        teacher_audit = {
            "milestone": MILESTONE,
            "parent_day": PARENT_DAY,
            "target_day": TARGET_DAY,
            "delta_day": DELTA_DAY,
            "substeps": int(teacher["substeps"]),
            "elapsed_seconds": teacher_elapsed,
            "advective_CFL_dt_days": float(teacher["advective_CFL_dt_days"]),
            "minimum_dt_days": float(teacher["minimum_dt_days"]),
            "maximum_dt_days": float(teacher["maximum_dt_days"]),
            "parent_CV_mass_kg": fsum_array(parent_cv_mass),
            "future_CV_mass_kg": fsum_array(teacher["future_mass"]),
            "injected_mass_kg": float(teacher["injected_mass_kg"]),
            "produced_mass_kg": float(teacher["produced_mass_kg"]),
            "teacher_delta_mass_kg": float(teacher["delta_mass_kg"]),
            "global_mass_residual_kg": float(
                teacher["global_mass_residual_kg"]
            ),
            "max_step_mass_ledger_residual_kg": float(
                teacher["max_step_mass_ledger_residual_kg"]
            ),
            "max_capillary_boundary_mass_flux_kg_day": float(
                teacher["max_capillary_boundary_mass_flux_kg_day"]
            ),
            "maximum_mass_fraction_seen": float(
                teacher["maximum_mass_fraction_seen"]
            ),
            "future_mass_fraction_min": float(
                np.min(teacher["future_mass_fraction"])
            ),
            "future_mass_fraction_max": float(
                np.max(teacher["future_mass_fraction"])
            ),
            "future_saturation_min": float(
                np.min(teacher["future_saturation"])
            ),
            "future_saturation_max": float(
                np.max(teacher["future_saturation"])
            ),
            "lookup_parent_saturation_max_abs_error": float(
                teacher["lookup_parent_saturation_max_abs_error"]
            ),
            "lookup_final_vs_exact_max_abs_error": float(
                teacher["lookup_final_vs_exact_max_abs_error"]
            ),
            "exact_final_mass_inversion_max_abs_kg": float(
                teacher["exact_final_mass_inversion_max_abs_kg"]
            ),
            "capillary_boundary_condition": (
                "zero mass flux at inlet and outlet; rate-controlled injector "
                "is the sole external source"
            ),
            "capillary_rederivation": (
                "pairwise conservative physical phase-volume flux obtained by "
                "multiplying the frozen AV3 TOF strong-form face coefficient by "
                "the streamline q and symmetrizing phi*metric at the face"
            ),
        }

        physics_audit = {
            "milestone": MILESTONE,
            "residual_definition": (
                "R = (y500-y365)/(0.135) - "
                "1000*RHS_mass(midpoint_state)/parent_CV_capacity"
            ),
            "residual_shape": list(pair_residual.shape),
            "residual_finite": bool(np.isfinite(pair_residual).all()),
            "residual_rms": float(
                np.sqrt(np.mean(pair_residual * pair_residual))
            ),
            "residual_linf": float(np.max(np.abs(pair_residual))),
            "global_face_algebra_residual_kg_day": float(
                mid_global_rhs - mid_boundary_rhs
            ),
            "advection_rule": (
                "positive-flow local spatial-Corey upwind; fixed 500 t/day "
                "component-mass injector source"
            ),
            "capillary_rule": (
                "source-authentic AV3 Dtilde/phi/TOF metric, pairwise conservative "
                "internal no-flow-boundary component-mass redistribution"
            ),
        }

        recurrent_audit = {
            "milestone": MILESTONE,
            "parent_full_grid_mass_kg": parent_mass_total,
            "future_full_grid_mass_kg": future_mass_total,
            "expected_future_mass_kg": expected_future_total,
            "CV_increment_mapback_residual_kg": float(
                mapback["ledger_residual_kg"]
            ),
            "CV_to_subsegment_transfer_residual_kg": float(
                mapback["transfer_residual_kg"]
            ),
            "Day500_pressure_iterations": int(refresh["iterations"]),
            "Day500_pressure_min_psi": float(np.min(target_pressure)),
            "Day500_pressure_max_psi": float(np.max(target_pressure)),
            "Day500_saturation_min": float(np.min(target_refresh_sat)),
            "Day500_saturation_max": float(np.max(target_refresh_sat)),
            "Day500_streamlines": int(target_xyz.shape[0]),
            "Day500_tau_end_min_days": float(np.min(target_tau_end) / SPD),
            "Day500_tau_end_max_days": float(np.max(target_tau_end) / SPD),
            "Day500_reprojected_CV_mass_kg": float(
                target_split["mapped_mass_kg"]
            ),
            "Day500_residual_grid_mass_kg": target_residual_total,
            "Day500_reprojection_ledger_residual_kg": float(
                target_split["ledger_residual_kg"]
            ),
            "Day500_overloaded_CV_count": int(
                target_split["overloaded_CV_count"]
            ),
            "Day500_CV_saturation_min": float(
                np.min(target_split["cv_saturation"])
            ),
            "Day500_CV_saturation_max": float(
                np.max(target_split["cv_saturation"])
            ),
        }

        f5_handoff = {
            "milestone": "POSTV16-AV4-F5",
            "name": (
                "TRAIN/VALIDATION Restart Teacher Dataset + 17-Channel "
                "Normalization / Physics-Sidecar Assembly"
            ),
            "authorized": True,
            "execution": True,
            "required_F4_status": STATUS_PASS,
            "allowed": [
                "generate restart teachers for all 8 adjacent pairs for AV3CR0001 and AV3CR0002 TRAIN",
                "generate restart teachers for all 8 adjacent pairs for AV3CR0003 VALIDATION",
                "assemble 17-channel 200-CV TRAIN and VALIDATION tensors",
                "fit any newly fitted restart normalization statistics on TRAIN only",
                "assemble conservative mass-residual physics sidecars",
                "assemble AV3CR0004 locked-OOD predictor features only without teacher targets",
                "certify recursive split-state carryover between adjacent pairs",
            ],
            "forbidden": [
                "model training",
                "checkpoint creation or selection",
                "locked-OOD teacher generation",
                "locked-OOD metrics",
                "OOD normalization fit",
                "hyperparameter search",
                "historical AV3 checkpoint restart reuse",
                "A3-E2",
                "general dynamic deployment",
                "CMG",
            ],
            "F6_training_authorized": False,
            "checkpoint_creation_authorized": False,
            "locked_OOD_teacher_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "F3_protocol_bound": True,
            "X17_constructed": True,
            "untrained_model_built": True,
            "untrained_model_parameters": parameter_count,
            "teacher_executed": True,
            "teacher_component_mass_conservative": True,
            "teacher_capillary_internal_zero_sum": True,
            "teacher_final_E37A_inversion_PASS": True,
            "E37A_increment_mapback_executed": True,
            "Day500_dynamic_flow_refresh_executed": True,
            "Day500_bounded_reprojection_executed": True,
            "Day500_split_state_accepted": True,
            "training_performed": False,
            "checkpoint_created": False,
            "checkpoint_selected": False,
            "checkpoint_inference_performed": False,
            "locked_OOD_opened": False,
            "normalization_refit_performed": False,
            "hyperparameter_search_performed": False,
            "CMG_validation_performed": False,
            "F5_dataset_generation_authorized": True,
            "F5_execution_authorized": True,
            "F6_training_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "control_realization": CONTROL_REALIZATION,
            "paired_porosity": CONTROL_POROSITY,
            "partition": CONTROL_PARTITION,
            "parent_day": PARENT_DAY,
            "target_day": TARGET_DAY,
            "delta_day": DELTA_DAY,
            "X17_shape": list(X17.shape),
            "model_parameters": parameter_count,
            "teacher_substeps": int(teacher["substeps"]),
            "teacher_injected_mass_kg": float(teacher["injected_mass_kg"]),
            "teacher_produced_mass_kg": float(teacher["produced_mass_kg"]),
            "teacher_global_mass_residual_kg": float(
                teacher["global_mass_residual_kg"]
            ),
            "parent_grid_mass_kg": parent_mass_total,
            "future_grid_mass_kg": future_mass_total,
            "Day500_streamline_count": int(target_xyz.shape[0]),
            "Day500_reprojected_CV_mass_kg": float(
                target_split["mapped_mass_kg"]
            ),
            "Day500_residual_grid_mass_kg": target_residual_total,
            "Day500_split_state_accepted": True,
            "training": False,
            "checkpoint_creation": False,
            "checkpoint_inference": False,
            "locked_OOD_opened": False,
            "F5_authorized": True,
            "F6_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        predictor_npz = deterministic_npz_bytes(
            {
                "X_restart_17": X17.astype(np.float32),
                "channel_names": np.asarray(CHANNELS17, dtype="U40"),
                "streamline_index": np.arange(NSL, dtype=np.int64),
                "parent_day": np.full(NSL, PARENT_DAY, dtype=np.float64),
                "target_day": np.full(NSL, TARGET_DAY, dtype=np.float64),
                "delta_day": np.full(NSL, DELTA_DAY, dtype=np.float64),
                "terminal_parent_TOF_s": parent_tof[:, -1],
            }
        )

        teacher_npz = deterministic_npz_bytes(
            {
                "parent_CV_component_mass_kg": parent_cv_mass,
                "parent_CV_saturation": parent_cv_sat,
                "parent_CV_capacity_kg": parent_cv_capacity,
                "parent_CV_mass_fraction": parent_mass_fraction,
                "future_parent_geometry_CV_component_mass_kg": teacher["future_mass"],
                "future_parent_geometry_CV_saturation": teacher["future_saturation"],
                "future_parent_geometry_CV_mass_fraction": teacher["future_mass_fraction"],
                "parent_full_grid_component_mass_kg": parent_grid_mass,
                "future_full_grid_component_mass_kg": mapback["future_grid_mass_kg"],
                "future_full_grid_saturation": target_refresh_sat,
                "Day500_refreshed_pressure_psi": target_pressure,
                "Day500_streamline_xyz_m": target_xyz,
                "Day500_streamline_tof_s": target_tof,
                "Day500_streamline_weight_m3_s": target_weights_s,
                "Day500_streamline_face_pressure_psi": target_face_pressure,
                "Day500_reprojected_CV_component_mass_kg": target_split["cv_mass"],
                "Day500_reprojected_CV_saturation": target_split["cv_saturation"],
                "Day500_reprojected_CV_capacity_kg": target_split["cv_capacity"],
                "Day500_residual_grid_component_mass_kg": target_split["residual_grid_mass"],
                "Day500_occupancy_fraction_alpha": target_split["occupancy_fraction_alpha"],
                "physics_pair_residual": pair_residual,
                "teacher_final_advective_mass_flux_kg_day": teacher[
                    "final_advective_mass_flux_kg_day"
                ],
                "teacher_final_capillary_mass_flux_kg_day": teacher[
                    "final_capillary_mass_flux_kg_day"
                ],
                "parent_day": np.asarray(PARENT_DAY),
                "target_day": np.asarray(TARGET_DAY),
                "delta_day": np.asarray(DELTA_DAY),
            }
        )

        output_files = {
            "PAD_Stream_POSTV16_AV4_F4_Summary.json":
                json_bytes(summary),
            "POSTV16_AV4_F4_Day365_17Channel_Predictor.npz":
                predictor_npz,
            "POSTV16_AV4_F4_Day365_to_Day500_Teacher_and_Recurrent_State.npz":
                teacher_npz,
            "POSTV16_AV4_F4_Untrained_Model_Architecture.json":
                model_json.encode("utf-8"),
            "POSTV16_AV4_F4_Teacher_Mass_Conservation_Audit.json":
                json_bytes(teacher_audit),
            "POSTV16_AV4_F4_200CV_Physics_Residual_Certification.json":
                json_bytes(physics_audit),
            "POSTV16_AV4_F4_Recurrent_Mapback_Refresh_Reprojection_Audit.json":
                json_bytes(recurrent_audit),
            "POSTV16_AV4_F4_F5_Handoff_Contract.json":
                json_bytes(f5_handoff),
            "POSTV16_AV4_F4_Decision_Contract.json":
                json_bytes(decision),
            "POSTV16_AV4_F4_Final_Gate_Matrix.csv":
                csv_bytes(
                    [{"gate": name, **value} for name, value in gates.items()]
                ),
        }

        immutable_publish(out, output_files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV4_F4_Artifact_Manifest.csv":
                manifest_rows.append(
                    {
                        "file": p.name,
                        "sha256": sha256_file(p),
                        "bytes": p.stat().st_size,
                    }
                )

        immutable_publish(
            out,
            {
                "POSTV16_AV4_F4_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print()
        print("=" * 214)
        print(f"{MILESTONE}: DAY365→DAY500 RESTART TEACHER / CONSERVATIVE LOOP CERTIFICATION PASS")
        print("=" * 214)
        print("X17 shape                                 :", X17.shape)
        print("Untrained model parameters                :", parameter_count)
        print("Teacher substeps                          :", teacher["substeps"])
        print("Teacher injected mass kg                  :", teacher["injected_mass_kg"])
        print("Teacher produced mass kg                  :", teacher["produced_mass_kg"])
        print("Teacher global mass residual kg           :", teacher["global_mass_residual_kg"])
        print("Parent full-grid mass kg                  :", parent_mass_total)
        print("Future full-grid mass kg                  :", future_mass_total)
        print("Day500 pressure fixed-point iterations    :", refresh["iterations"])
        print("Day500 streamline count                   :", target_xyz.shape[0])
        print("Day500 reprojected CV mass kg             :", target_split["mapped_mass_kg"])
        print("Day500 residual-grid mass kg              :", target_residual_total)
        print("Day500 split-state ledger residual kg     :", target_split["ledger_residual_kg"])
        print("Day500 overloaded CV count                :", target_split["overloaded_CV_count"])
        print("Training / checkpoint / OOD               : False / False / False")
        print("POSTV16-AV4-F5                            : AUTHORIZED")
        print("F6 training / A3-E2 / dynamic AV4         : NOT AUTHORIZED")
        print("=" * 214)

        return 0

    except ScientificFail as exc:
        failed.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_FAIL,
            "failed_stage": stage,
            "failed_gate": exc.gate,
            "detail": exc.detail,
            "gates": gates,
            "teacher_started": teacher_started,
            "mapback_executed": mapback_executed,
            "target_refresh_executed": target_refresh_executed,
            "target_reprojection_executed": target_reprojection_executed,
            "model_built": model_built,
            "training_performed": False,
            "checkpoint_created": False,
            "checkpoint_inference_performed": False,
            "locked_OOD_opened": False,
            "support_expansion_performed": False,
            "mass_rescaling_performed": False,
            "F5_authorized": False,
            "F6_training_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
            "automatic_rerun_authorized": False,
        }
        data = json_bytes(report)
        p = failed / "POSTV16_AV4_F4_Scientific_Fail_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = failed / (
                "POSTV16_AV4_F4_Scientific_Fail_Report_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        if not p.exists():
            p.write_bytes(data)

        print()
        print("=" * 214)
        print(f"{MILESTONE}: SCIENTIFIC FAIL")
        print("=" * 214)
        print("Stage      :", stage)
        print("Failed gate:", exc.gate)
        print("Detail     :", exc.detail)
        print("NO ADAPTATION OR AUTOMATIC RERUN AUTHORIZED.")
        print("F5 / training / A3-E2 / dynamic AV4: NOT AUTHORIZED")
        print("=" * 214)
        return 3

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "teacher_started": teacher_started,
            "mapback_executed": mapback_executed,
            "target_refresh_executed": target_refresh_executed,
            "target_reprojection_executed": target_reprojection_executed,
            "model_built": model_built,
            "training_performed": False,
            "checkpoint_created": False,
            "checkpoint_inference_performed": False,
            "locked_OOD_opened": False,
            "F5_authorized": False,
            "F6_training_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
            "automatic_rerun_authorized": False,
        }
        data = json_bytes(report)
        p = blocked / "POSTV16_AV4_F4_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV4_F4_Blocked_Report_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        if not p.exists():
            p.write_bytes(data)

        print()
        print("=" * 214)
        print(f"{MILESTONE}: TECHNICAL / AUTHORITY BLOCK")
        print("=" * 214)
        print("Stage    :", stage)
        print("Exception:", repr(exc))
        print("NO TEACHER ADAPTATION OR AUTOMATIC RERUN AUTHORIZED.")
        print("=" * 214)
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
    raise SystemExit(main(args.project_root, args.drive_root))
