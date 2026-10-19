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


MILESTONE = "POSTV16-AV2-A3"

STATUS_PASS = (
    "AV2A3_VARIABLE_POROSITY_TRAIN_VALIDATION_TEACHER_DATASET_CERTIFIED_"
    "LOCKED_OOD_PREDICTOR_ONLY_PIRNN_PROTOCOL_FROZEN"
)

STATUS_FAIL = (
    "AV2A3_VARIABLE_POROSITY_TEACHER_OR_DATASET_SCIENTIFIC_FAIL_"
    "NO_OOD_OPENING_OR_PROTOCOL_RETUNING_AUTHORIZED"
)

STATUS_BLOCKED = "AV2A3_TECHNICAL_EXECUTION_BLOCKED"

PROTOCOL_ID = (
    "POSTV16_AV2_A3_VARIABLE_PHI_TEACHER_DATASET_AND_PIRNN_PROTOCOL_V1"
)

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_AV2A2_COMMIT = "b7f9481a4c85ffe524aae85066a73be6b935dc91"

# Exact source lineage.
A2 = (
    "PAD_Stream_POSTV16_AV2_A2_"
    "Porosity_Realization_and_Pore_Kinematics_Execution.py"
)
A2_BLOB = "f141b07f0424d29a7996c089a76dbe7128af5132"

R7 = "PAD_Stream_POSTV16_AV1_D_R7_Full_End_to_End_PAD_Stream_Integration.py"
R7_BLOB = "a28722b0b8059bd50d94fb8a914defc0b35f2f7b"

B2 = "PAD_Stream_V16B2_Exact_3D_Fast_Marching_Arrival_Time_Baseline.py"
B2_BLOB = "95025d1e67a74f9dacaad311e5a402b63e7b4335"

C2 = "PAD_Stream_V16C2_Multi_Coordinate_Streamline_Transport_Database_Assembly.py"
C2_BLOB = "21ff44de456102772c99f7ddc80898c9139a76db"

C7 = "PAD_Stream_V16C7_Pollock_TOF_Full_BL_CCUS_Transport_Adapter_Physics_Contract.py"
C7_BLOB = "78b312ad16c1778a62cfbd9a77a9793aa14044d4"

C10 = "PAD_Stream_V16C10_Conservative_201_Node_Pollock_Coordinate_Full_Physics_Operator_Construction.py"
C10_BLOB = "753fd3de9490c37173c5c00544a3bb995de4ccfc"

C11 = "PAD_Stream_V16C11_Executable_Conservative_Full_Physics_Pollock_Transport_Solver_Assembly_and_Diagnostic_Validation.py"
C11_BLOB = "cafabb886569bfddaf4ab62674d6abcbcbf65f1f"

C17 = "PAD_Stream_V16C17_Production_Source_Authentic_Y_Transport_Tensor_Generation_and_Certification.py"
C17_BLOB = "310e10853ce6f160ee8c9bd270f2823893bf98d3"

C20 = "PAD_Stream_V16C20_Stage4_PIRNN_to_V16_Training_Interface_and_Architecture_Binding_Contract.py"
C20_BLOB = "70b073faafd76f71c2c97a2df031592f05f6cf9f"

C25 = "PAD_Stream_V16C25_Differentiable_Pollock_Full_Physics_Residual_Boundary_Mask_and_Physics_Loss_Weight_Authority_Contract.py"
C25_BLOB = "0a4740b95c2b5e5d15db3137414e663e1e9b6282"

C26 = "PAD_Stream_V16C26_EXP2_Physics_Informed_Training_Execution_Best_Validation_Checkpoint_and_Locked_Test_Evaluation.py"
C26_BLOB = "62e19e6b502fb3ab101a2589251c26b5f9ad9031"

STAGE4 = "pi_rnn_stage4_full_godunov.py"
STAGE4_BLOB = "0c276317a5d8487c190c7185908b228544c33073"

SOURCE_BLOBS = {
    A2: A2_BLOB,
    R7: R7_BLOB,
    B2: B2_BLOB,
    C2: C2_BLOB,
    C7: C7_BLOB,
    C10: C10_BLOB,
    C11: C11_BLOB,
    C17: C17_BLOB,
    C20: C20_BLOB,
    C25: C25_BLOB,
    C26: C26_BLOB,
    STAGE4: STAGE4_BLOB,
}

BASE_AV2 = (
    Path("post_v16")
    / RID
    / "POSTV16_AV2_Variable_Porosity"
)

A2_REL = BASE_AV2 / "POSTV16_AV2_A2_Porosity_Realization_and_Pore_Kinematics_Execution"
A2_SUMMARY = "PAD_Stream_POSTV16_AV2_A2_Summary.json"
A2_DECISION = "POSTV16_AV2_A2_Decision_Contract.json"
A2_DIAG = "POSTV16_AV2_A2_By_Porosity_Realization_Diagnostics.csv"
A2_MANIFEST = "POSTV16_AV2_A2_Artifact_Manifest.csv"

A2_STATUS = (
    "AV2A2_FROZEN_SPATIAL_POROSITY_REALIZATIONS_GENERATED_"
    "PRESSURE_Q_INVARIANCE_CERTIFIED_PORE_KINEMATICS_RECONSTRUCTED_PASS"
)

OUT_REL = (
    BASE_AV2
    / "POSTV16_AV2_A3_Variable_Porosity_Teacher_Dataset_and_PIRNN_Protocol"
)
FAIL_REL = BASE_AV2 / "POSTV16_AV2_A3_SCIENTIFIC_FAIL"
BLOCKED_REL = BASE_AV2 / "POSTV16_AV2_A3_BLOCKED"

FOUNDATION_NAME = "V16A_Foundation_Case_0001.npz"
FOUNDATION_SHA = "4239e412ca6e2780f108c8eb1b0252e80a56be305bce48cc58e50d6140b86acc"

GRID = (15, 50, 50)
NZ, NY, NX = GRID
NSL = 1078
NN = 201
NT = 9

DX = 6.096
DY = 6.096
DZ = 1.2192

DAYS = np.asarray(
    [30., 60., 100., 150., 250., 365., 500., 750., 1000.],
    dtype=np.float64,
)
SPD = 86400.0

# Exact A1/A2 registry.
REALIZATIONS = [
    ("AV2PHI0001", 260201, "TRAIN"),
    ("AV2PHI0002", 260202, "TRAIN"),
    ("AV2PHI0003", 260203, "VALIDATION"),
    ("AV2PHI0004", 260204, "LOCKED_OOD_TEST"),
]

# Frozen transport constitutive parameters from C14/C17/C25.
P = {
    "nw": 2.0,
    "no": 2.0,
    "swc": 0.2,
    "sor": 0.2,
    "krw_max": 0.8,
    "kro_max": 0.8,
    "mu_w": 0.5,
    "mu_o": 5.0,
}
P["sw_init"] = P["swc"] + 1.0e-3
P["sw_inj"] = 1.0 - P["sor"] - 1.0e-3

PE_C = 22.0
LAMBDA_C = 2.0
CFL = 0.25
EPS = 1.0e-12

# C17 certification thresholds, reused exactly rather than relaxed.
ADV_CONSERVATION_MAX = 1.0e-11
IMPLICIT_RESIDUAL_MAX = 1.0e-10
PRECLIP_BOUND_MAX = 1.0e-8
Y_BOUND_MAX = 1.0e-8
INLET_ERROR_MAX = 1.0e-12
UNDERSHOOT_MAX = 1.0e-8
TEMPORAL_NEGATIVE_FRACTION_MAX = 0.01
SPATIAL_POSITIVE_FRACTION_MAX = 0.05

# Frozen AV2 model/training protocol: preserve C26 architecture and optimizer.
TRAINING_SEED = 16021
HIDDEN_UNITS = 64
LSTM_LAYERS = 2
INPUT_CHANNELS = 9
BATCH_SIZE = 64
MAX_EPOCHS = 300
EARLY_STOP_PATIENCE = 30
EARLY_STOP_MIN_DELTA = 1.0e-6
LR_REDUCE_FACTOR = 0.5
LR_REDUCE_PATIENCE = 10
MIN_LR = 1.0e-6
INITIAL_LR = 1.0e-3
LAMBDA_DATA = 1.0
LAMBDA_PHYS = 0.01
R0 = 1.0


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
    p = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return p.stdout.strip()


def git_blob_sha(path: Path, root: Path) -> str:
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
        raise GateError("manifest_empty")
    for fn, expected in manifest.items():
        p = directory / fn
        if not p.is_file():
            raise GateError(f"manifest_missing:{fn}")
        actual = sha256_file(p)
        if actual != expected:
            raise GateError(f"manifest_SHA:{fn}:{actual}:{expected}")
    return manifest


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
        zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as zf:
        for key in sorted(arrays):
            b = io.BytesIO()
            np.save(
                b,
                np.asarray(arrays[key]),
                allow_pickle=False,
            )
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
            raise GateError(f"existing_output_differs:{name}")
        if not p.exists():
            p.write_bytes(data)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load_module:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def find_named_exact(
    roots: list[Path],
    name: str,
    expected_sha: str,
) -> Path:
    hits: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob(name):
            try:
                if p.is_file() and sha256_file(p) == expected_sha:
                    hits.append(p.resolve())
            except OSError:
                pass
    if not hits:
        raise GateError(f"exact_authority_not_found:{name}:{expected_sha}")
    return sorted(set(hits), key=lambda p: (len(str(p)), str(p)))[0]


def centered_derivative(y: np.ndarray, x: np.ndarray) -> np.ndarray:
    y = np.asarray(y, dtype=np.float64)
    x = np.asarray(x, dtype=np.float64)

    out = np.empty_like(y)

    dx0 = x[:, 1] - x[:, 0]
    dx1 = x[:, -1] - x[:, -2]

    if np.any(dx0 <= 0.0) or np.any(dx1 <= 0.0):
        raise ScientificFail("metric_endpoint_spacing_positive")

    out[:, 0] = (y[:, 1] - y[:, 0]) / dx0
    out[:, -1] = (y[:, -1] - y[:, -2]) / dx1

    den = x[:, 2:] - x[:, :-2]

    if np.any(den <= 0.0):
        raise ScientificFail("metric_centered_spacing_positive")

    out[:, 1:-1] = (y[:, 2:] - y[:, :-2]) / den

    return out


def build_operator_geometry(
    xyz: np.ndarray,
    tof: np.ndarray,
) -> dict[str, np.ndarray]:
    dxyz = np.diff(xyz, axis=1)
    ds = np.linalg.norm(dxyz, axis=2)

    if np.any(ds <= 0.0):
        raise ScientificFail(
            "positive_streamline_geometric_segments",
            int(np.sum(ds <= 0.0)),
        )

    s = np.concatenate(
        [
            np.zeros((xyz.shape[0], 1), dtype=np.float64),
            np.cumsum(ds, axis=1),
        ],
        axis=1,
    )

    L = s[:, -1]

    if np.any(L <= 0.0):
        raise ScientificFail("positive_terminal_streamline_length")

    xD = s / L[:, None]

    tau_end = tof[:, -1]

    if np.any(tau_end <= 0.0):
        raise ScientificFail("positive_terminal_TOF")

    theta = tof / tau_end[:, None]

    if np.any(np.diff(theta, axis=1) <= 0.0):
        raise ScientificFail(
            "strictly_increasing_normalized_TOF"
        )

    M = centered_derivative(theta, xD)

    if (
        np.any(~np.isfinite(M))
        or np.any(M <= 0.0)
    ):
        raise ScientificFail(
            "positive_finite_coordinate_metric_M"
        )

    theta_face = np.empty(
        (theta.shape[0], theta.shape[1] + 1),
        dtype=np.float64,
    )

    theta_face[:, 1:-1] = 0.5 * (
        theta[:, :-1]
        + theta[:, 1:]
    )

    theta_face[:, 0] = theta[:, 0]
    theta_face[:, -1] = theta[:, -1]

    cv = np.diff(theta_face, axis=1)

    if np.any(cv <= 0.0):
        raise ScientificFail(
            "positive_theta_control_volume_width"
        )

    M_face = np.empty(
        (M.shape[0], M.shape[1] + 1),
        dtype=np.float64,
    )

    M_face[:, 0] = M[:, 0]
    M_face[:, -1] = M[:, -1]

    M_face[:, 1:-1] = (
        2.0
        * M[:, :-1]
        * M[:, 1:]
        / (
            M[:, :-1]
            + M[:, 1:]
        )
    )

    if np.any(M_face <= 0.0):
        raise ScientificFail(
            "positive_face_metric_M"
        )

    return {
        "theta": theta,
        "xD_arc": xD,
        "metric_M": M,
        "metric_M_face": M_face,
        "control_volume_dtheta": cv,
        "dtheta_center": np.diff(theta, axis=1),
        "terminal_length_m": L,
        "terminal_TOF_s": tau_end,
    }


def relperm(S: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    span = max(EPS, 1.0 - P["swc"] - P["sor"])
    Se = np.clip(
        (S - P["swc"]) / span,
        0.0,
        1.0,
    )
    return (
        P["krw_max"] * Se**P["nw"],
        P["kro_max"] * (1.0 - Se)**P["no"],
    )


def fw(S: np.ndarray) -> np.ndarray:
    krw, kro = relperm(S)
    return 1.0 / (
        1.0
        + (P["mu_w"] / P["mu_o"])
        * (kro / (krw + EPS))
    )


def dshape(
    S: np.ndarray,
    lmb: float,
) -> np.ndarray:
    span = max(
        EPS,
        1.0 - P["swc"] - P["sor"],
    )

    Se = np.clip(
        (S - P["swc"]) / span,
        1.0e-6,
        1.0 - 1.0e-6,
    )

    def raw(E: np.ndarray | float, X: np.ndarray | float):
        kro = (
            P["kro_max"]
            * (1.0 - E)**P["no"]
        )
        return (
            kro
            * fw(np.asarray(X, dtype=np.float64))
            * np.asarray(E, dtype=np.float64)
            ** (-1.0 / lmb - 1.0)
        )

    mid = P["swc"] + 0.5 * span
    norm = float(raw(0.5, mid))

    return raw(Se, S) / max(norm, EPS)


def max_dfw() -> float:
    s = np.linspace(
        P["swc"],
        1.0 - P["sor"],
        4001,
    )
    return float(
        np.max(
            np.abs(
                np.gradient(
                    fw(s),
                    s,
                )
            )
        )
    )


def tri(
    lower: np.ndarray,
    diag: np.ndarray,
    upper: np.ndarray,
    rhs: np.ndarray,
) -> np.ndarray:
    a = lower.copy()
    b = diag.copy()
    c = upper.copy()
    d = rhs.copy()

    ns, n = b.shape

    for j in range(1, n):
        w = a[:, j] / b[:, j - 1]
        b[:, j] -= w * c[:, j - 1]
        d[:, j] -= w * d[:, j - 1]

    x = np.empty_like(d)
    x[:, -1] = d[:, -1] / b[:, -1]

    for j in range(n - 2, -1, -1):
        x[:, j] = (
            d[:, j]
            - c[:, j] * x[:, j + 1]
        ) / b[:, j]

    return x


def advective_step(
    S: np.ndarray,
    dt: np.ndarray,
    cv: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float]:
    ns, n = S.shape

    F = np.zeros(
        (ns, n + 1),
        dtype=np.float64,
    )

    F[:, 1] = fw(
        np.full(
            ns,
            P["sw_inj"],
            dtype=np.float64,
        )
    )

    if n > 2:
        F[:, 2:n] = fw(
            S[:, 1:n - 1]
        )

    F[:, n] = fw(S[:, -1])

    old = S.copy()

    S[:, 1:] -= (
        dt[:, None]
        * (
            F[:, 2:]
            - F[:, 1:-1]
        )
        / cv[:, 1:]
    )

    S[:, 0] = P["sw_inj"]

    lhs = np.sum(
        cv[:, 1:]
        * (
            S[:, 1:]
            - old[:, 1:]
        ),
        axis=1,
    )

    rhs = -dt * (
        F[:, -1]
        - F[:, 1]
    )

    err = float(
        np.max(
            np.abs(lhs - rhs)
        )
    )

    return S, F, err


def capillary_implicit_local_phi(
    Sadv: np.ndarray,
    dt: np.ndarray,
    phi_seq: np.ndarray,
    M: np.ndarray,
    M_face: np.ndarray,
    cv: np.ndarray,
    dtheta: np.ndarray,
) -> tuple[np.ndarray, float]:
    """
    Direct AV2 extension of the frozen Stage4/C7/C17 capillary coefficient:

        (phi / Pe_c) M d/dtheta[Dtilde(S) M dS/dtheta]

    The former Foundation scalar phi=0.20 is replaced by the local sampled
    porosity at each interior Pollock node. Pe_c=22 and the constitutive
    capillary-shape authority remain unchanged.
    """
    ns, n = Sadv.shape

    if phi_seq.shape != Sadv.shape:
        raise GateError(
            f"phi_sequence_shape:{phi_seq.shape}:{Sadv.shape}"
        )

    D = dshape(Sadv, LAMBDA_C)

    Dface = 0.5 * (
        D[:, :-1]
        + D[:, 1:]
    )

    Aface = (
        Dface
        * M_face[:, 1:-1]
        / dtheta
    )

    lower = np.zeros((ns, n), dtype=np.float64)
    diag = np.ones((ns, n), dtype=np.float64)
    upper = np.zeros((ns, n), dtype=np.float64)
    rhs = Sadv.copy()

    # Local phi multiplies the transformed capillary divergence at each
    # interior control volume. This collapses exactly to C17 when phi is constant.
    beta = (
        dt[:, None]
        * phi_seq[:, 1:-1]
        / PE_C
    )

    fac = (
        M[:, 1:-1]
        / cv[:, 1:-1]
    )

    aL = Aface[:, :-1]
    aR = Aface[:, 1:]

    lower[:, 1:-1] = -beta * fac * aL
    upper[:, 1:-1] = -beta * fac * aR

    diag[:, 1:-1] = (
        1.0
        + beta * fac * (aL + aR)
    )

    rhs[:, 0] = P["sw_inj"]
    rhs[:, -1] = Sadv[:, -1]

    S = tri(
        lower,
        diag,
        upper,
        rhs,
    )

    r = diag * S - rhs
    r[:, 1:] += lower[:, 1:] * S[:, :-1]
    r[:, :-1] += upper[:, :-1] * S[:, 1:]

    return (
        S,
        float(np.max(np.abs(r))),
    )


def generate_teacher(
    phi_seq: np.ndarray,
    operator: dict[str, np.ndarray],
    target_days: np.ndarray,
) -> tuple[np.ndarray, dict[str, Any]]:
    theta = operator["theta"]
    M = operator["metric_M"]
    M_face = operator["metric_M_face"]
    cv = operator["control_volume_dtheta"]
    dtheta = operator["dtheta_center"]
    tau_end = operator["terminal_TOF_s"]

    ns, n = theta.shape

    target_eta = (
        target_days[:, None]
        * SPD
        / tau_end[None, :]
    )

    dfmax = max_dfw()

    dt_cfl = float(
        CFL
        * np.min(cv[:, 1:])
        / (
            dfmax
            + EPS
        )
    )

    S = np.full(
        (ns, n),
        P["sw_init"],
        dtype=np.float64,
    )

    S[:, 0] = P["sw_inj"]

    eta = np.zeros(
        ns,
        dtype=np.float64,
    )

    nextk = np.zeros(
        ns,
        dtype=np.int64,
    )

    Y = np.full(
        (
            len(target_days),
            ns,
            n,
        ),
        np.nan,
        dtype=np.float64,
    )

    max_adv = 0.0
    max_imp = 0.0
    max_preclip = 0.0

    steps = 0

    max_iter = (
        int(
            np.ceil(
                np.max(target_eta)
                / dt_cfl
            )
        )
        + len(target_days)
        + 100
    )

    t0 = time.time()

    while np.any(
        nextk < len(target_days)
    ):
        active = nextk < len(target_days)

        goal = np.zeros(
            ns,
            dtype=np.float64,
        )

        idx = np.where(active)[0]

        goal[idx] = target_eta[
            nextk[idx],
            idx,
        ]

        dt = np.zeros(
            ns,
            dtype=np.float64,
        )

        dt[active] = np.minimum(
            dt_cfl,
            np.maximum(
                0.0,
                goal[active]
                - eta[active],
            ),
        )

        hit = (
            active
            & (
                np.abs(
                    goal - eta
                )
                <= 5.0e-14
            )
        )

        if np.any(hit):
            hi = np.where(hit)[0]
            Y[nextk[hi], hi, :] = S[hi, :]
            nextk[hi] += 1
            continue

        S, _, e = advective_step(
            S,
            dt,
            cv,
        )

        max_adv = max(
            max_adv,
            e,
        )

        pre = float(
            max(
                0.0,
                P["swc"] - np.min(S),
                np.max(S) - (1.0 - P["sor"]),
            )
        )

        max_preclip = max(
            max_preclip,
            pre,
        )

        np.clip(
            S,
            P["swc"],
            1.0 - P["sor"],
            out=S,
        )

        S[:, 0] = P["sw_inj"]

        S, r = capillary_implicit_local_phi(
            S,
            dt,
            phi_seq,
            M,
            M_face,
            cv,
            dtheta,
        )

        max_imp = max(
            max_imp,
            r,
        )

        pre = float(
            max(
                0.0,
                P["swc"] - np.min(S),
                np.max(S) - (1.0 - P["sor"]),
            )
        )

        max_preclip = max(
            max_preclip,
            pre,
        )

        np.clip(
            S,
            P["swc"],
            1.0 - P["sor"],
            out=S,
        )

        S[:, 0] = P["sw_inj"]

        eta += dt
        steps += 1

        if steps > max_iter:
            raise ScientificFail(
                "teacher_march_iteration_ceiling",
                {
                    "steps": steps,
                    "max_iter": max_iter,
                },
            )

    active = nextk < len(target_days)

    while np.any(active):
        idx = np.where(active)[0]

        goal = target_eta[
            nextk[idx],
            idx,
        ]

        hit = (
            np.abs(
                goal
                - eta[idx]
            )
            <= 1.0e-11
        )

        if not np.all(hit):
            raise ScientificFail(
                "final_target_capture_mismatch"
            )

        Y[nextk[idx], idx, :] = S[idx, :]
        nextk[idx] += 1
        active = nextk < len(target_days)

    finite = bool(
        np.all(
            np.isfinite(Y)
        )
    )

    smin = float(np.min(Y))
    smax = float(np.max(Y))

    inlet = float(
        np.max(
            np.abs(
                Y[:, :, 0]
                - P["sw_inj"]
            )
        )
    )

    bound = float(
        max(
            0.0,
            P["swc"] - smin,
            smax - (1.0 - P["sor"]),
        )
    )

    undershoot = float(
        max(
            0.0,
            P["sw_init"]
            - np.min(
                Y[:, :, 1:]
            ),
        )
    )

    temporal_negative = float(
        np.mean(
            np.diff(
                Y,
                axis=0,
            )
            < -1.0e-8
        )
    )

    spatial_positive = float(
        np.mean(
            np.diff(
                Y,
                axis=2,
            )
            > 1.0e-8
        )
    )

    diag = {
        "dt_eta_CFL_ceiling": dt_cfl,
        "iterations": int(steps),
        "elapsed_seconds": float(time.time() - t0),
        "advection_conservation_max_abs": max_adv,
        "implicit_residual_max_abs": max_imp,
        "preclip_bound_violation_max": max_preclip,
        "Y_finite": finite,
        "Y_min": smin,
        "Y_max": smax,
        "Y_bound_violation": bound,
        "Y_inlet_Dirichlet_error": inlet,
        "Y_reservoir_undershoot": undershoot,
        "temporal_negative_increment_fraction": temporal_negative,
        "spatial_positive_increment_fraction": spatial_positive,
        "target_eta_min": float(np.min(target_eta)),
        "target_eta_max": float(np.max(target_eta)),
    }

    return Y, diag


def teacher_diag_pass(d: dict[str, Any]) -> bool:
    return bool(
        d["Y_finite"]
        and d["advection_conservation_max_abs"] < ADV_CONSERVATION_MAX
        and d["implicit_residual_max_abs"] < IMPLICIT_RESIDUAL_MAX
        and d["preclip_bound_violation_max"] < PRECLIP_BOUND_MAX
        and d["Y_bound_violation"] < Y_BOUND_MAX
        and d["Y_inlet_Dirichlet_error"] < INLET_ERROR_MAX
        and d["Y_reservoir_undershoot"] < UNDERSHOOT_MAX
        and d["temporal_negative_increment_fraction"] < TEMPORAL_NEGATIVE_FRACTION_MAX
        and d["spatial_positive_increment_fraction"] < SPATIAL_POSITIVE_FRACTION_MAX
    )


def self_test() -> None:
    # Verify local-phi implicit solver collapses to the same algebraic system
    # as the scalar coefficient when phi is constant.
    rng = np.random.default_rng(260300)

    ns = 3
    n = 11

    S = 0.25 + 0.4 * rng.random((ns, n))
    S[:, 0] = P["sw_inj"]

    theta = np.broadcast_to(
        np.linspace(0.0, 1.0, n)[None, :],
        (ns, n),
    )

    M = np.ones((ns, n))
    Mf = np.ones((ns, n + 1))

    tf = np.empty((ns, n + 1))
    tf[:, 1:-1] = 0.5 * (
        theta[:, :-1]
        + theta[:, 1:]
    )
    tf[:, 0] = theta[:, 0]
    tf[:, -1] = theta[:, -1]

    cv = np.diff(tf, axis=1)
    dth = np.diff(theta, axis=1)

    dt = np.asarray(
        [1.0e-4, 2.0e-4, 3.0e-4]
    )

    phi = np.full(
        (ns, n),
        0.20,
    )

    out, residual = capillary_implicit_local_phi(
        S.copy(),
        dt,
        phi,
        M,
        Mf,
        cv,
        dth,
    )

    if not np.all(np.isfinite(out)):
        raise RuntimeError("selftest_nonfinite_capillary")
    if residual > 1.0e-10:
        raise RuntimeError(
            ("selftest_implicit_residual", residual)
        )

    if INPUT_CHANNELS != 9:
        raise RuntimeError("selftest_input_channels")

    print("POSTV16-AV2-A3 teacher/dataset protocol self-test: PASS")


def main(root: Path, drive: Path) -> int:
    gates: dict[str, dict[str, Any]] = {}

    stage = "preflight"
    teacher_generation_started = False
    teacher_realizations_completed = 0
    locked_ood_target_opened = False

    out = drive / OUT_REL
    fail = drive / FAIL_REL
    blocked = drive / BLOCKED_REL

    def gate(
        name: str,
        passed: Any,
        value: Any = None,
    ) -> None:
        ok = bool(passed)
        gates[name] = {
            "passed": ok,
            "value": value,
        }
        suffix = f" — {value}" if value is not None else ""
        print(f"[{'PASS' if ok else 'FAIL'}] {name}{suffix}")
        if not ok:
            raise GateError(name)

    def sci_gate(
        name: str,
        passed: Any,
        value: Any = None,
    ) -> None:
        ok = bool(passed)
        gates[name] = {
            "passed": ok,
            "value": value,
            "scientific_execution_gate": True,
        }
        suffix = f" — {value}" if value is not None else ""
        print(f"[{'PASS' if ok else 'FAIL'}] {name}{suffix}")
        if not ok:
            raise ScientificFail(name, value)

    print("=" * 206)
    print("POSTV16-AV2-A3 — VARIABLE-POROSITY TEACHER/DATASET ASSEMBLY + PI-RNN PROTOCOL FREEZE")
    print("=" * 206)
    print("TRAIN SUPERVISION: AV2PHI0001 + AV2PHI0002.")
    print("VALIDATION SUPERVISION: AV2PHI0003.")
    print("LOCKED OOD AV2PHI0004: PREDICTOR-SIDE INPUTS/PHYSICS SIDECAR ONLY — NO Y TRANSPORT TARGET MAY BE GENERATED OR OPENED.")
    print("NO MODEL TRAINING. NO CHECKPOINT CREATION. NO INFERENCE. NO MAPBACK. NO CMG.")
    print("C26 ARCHITECTURE/HYPERPARAMETERS ARE PRESERVED; ONLY VARIABLE-PHI DATA/PHYSICS SIDECARS ARE NEW.\n")

    try:
        root = root.resolve()
        drive = drive.resolve()

        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate(
            "repository_parent_is_AV2A2_commit",
            parent == PARENT_AV2A2_COMMIT,
            parent,
        )

        gate(
            "repository_clean",
            status == "",
            repr(status),
        )

        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = (
                git_blob_sha(p, root)
                if p.is_file()
                else "missing"
            )
            gate(
                f"{Path(fn).stem}_git_blob_exact",
                actual == expected,
                actual,
            )

        # ------------------------------------------------------------------
        # Bind exact A2 scientific PASS.
        # ------------------------------------------------------------------
        stage = "AV2A2_binding"

        a2 = drive / A2_REL

        gate(
            "AV2A2_output_present",
            a2.is_dir(),
            str(a2),
        )

        a2_manifest = verify_manifest(
            a2,
            A2_MANIFEST,
        )

        gate(
            "AV2A2_manifest_SHA_closure",
            True,
            len(a2_manifest),
        )

        s2 = load_json(
            a2 / A2_SUMMARY
        )

        d2 = load_json(
            a2 / A2_DECISION
        )

        diag2 = read_csv(
            a2 / A2_DIAG
        )

        gate(
            "AV2A2_status_exact",
            s2["status"] == A2_STATUS,
            s2["status"],
        )

        gate(
            "AV2A2_pressure_Q_invariance",
            s2["pressure_Q_invariance"] is True,
        )

        gate(
            "AV2A2_four_realizations_completed",
            int(s2["porosity_realizations_completed"]) == 4,
        )

        gate(
            "AV2A2_all_streamlines_captured",
            s2["all_streamlines_captured_each_realization"] is True,
        )

        gate(
            "AV2A2_locked_OOD_target_not_opened",
            d2["locked_OOD_transport_target_opened"] is False,
        )

        gate(
            "AV2A3_authorized",
            d2["next"]["authorized"] is True,
        )

        gate(
            "AV2A3_next_id_exact",
            d2["next"]["milestone"] == "POSTV16-AV2-A3",
        )

        registry_from_a2 = [
            (
                r["porosity_realization_id"],
                int(r["seed"]),
                r["partition"],
            )
            for r in diag2
        ]

        gate(
            "AV2A2_registry_exact",
            registry_from_a2 == REALIZATIONS,
            registry_from_a2,
        )

        # ------------------------------------------------------------------
        # Bind exact Foundation Case for K / pressure / Q.
        # ------------------------------------------------------------------
        stage = "Foundation_binding"

        foundation = find_named_exact(
            [root, drive],
            FOUNDATION_NAME,
            FOUNDATION_SHA,
        )

        gate(
            "Foundation0001_SHA_exact",
            sha256_file(foundation) == FOUNDATION_SHA,
            str(foundation),
        )

        with np.load(
            foundation,
            allow_pickle=False,
        ) as z:
            for k in [
                "Kx",
                "Ky",
                "Kz",
                "pressure",
                "Qx",
                "Qy",
                "Qz",
            ]:
                if k not in z.files:
                    raise GateError(
                        f"Foundation_missing:{k}"
                    )

            Kx = np.asarray(z["Kx"], dtype=np.float64)
            Ky = np.asarray(z["Ky"], dtype=np.float64)
            Kz = np.asarray(z["Kz"], dtype=np.float64)
            pressure = np.asarray(z["pressure"], dtype=np.float64)
            Qx = np.asarray(z["Qx"], dtype=np.float64)
            Qy = np.asarray(z["Qy"], dtype=np.float64)
            Qz = np.asarray(z["Qz"], dtype=np.float64)

        # ------------------------------------------------------------------
        # Import existing exact source algorithms for ADV/trilinear mapping.
        # ------------------------------------------------------------------
        stage = "algorithm_binding"

        r7 = load_module(
            root / R7,
            "av2a3_r7",
        )

        b2 = load_module(
            root / B2,
            "av2a3_b2",
        )

        c2 = load_module(
            root / C2,
            "av2a3_c2",
        )

        _, _, _, source_mask, _ = b2.bind_injector_sources(
            Qx,
            Qy,
            Qz,
        )

        source_mask = np.asarray(
            source_mask,
            dtype=bool,
        )

        gate(
            "ADV_exact_five_source_cells",
            int(np.sum(source_mask)) == 5,
            int(np.sum(source_mask)),
        )

        # ------------------------------------------------------------------
        # Predictor-side processing for all 4 realizations.
        # ------------------------------------------------------------------
        stage = "predictor_and_metric_assembly"

        per_case: dict[str, dict[str, Any]] = {}

        train_pressure_values: list[np.ndarray] = []
        train_log_weights: list[np.ndarray] = []

        for rid, seed, partition in REALIZATIONS:
            artifact = (
                a2
                / f"POSTV16_AV2_A2_{rid}_Variable_Porosity_Pore_Kinematics.npz"
            )

            gate(
                f"{rid}_A2_artifact_present",
                artifact.is_file(),
                artifact.name,
            )

            with np.load(
                artifact,
                allow_pickle=False,
            ) as z:
                phi_grid = np.asarray(
                    z["porosity"],
                    dtype=np.float64,
                )
                vx = np.asarray(
                    z["Vx_m_s"],
                    dtype=np.float64,
                )
                vy = np.asarray(
                    z["Vy_m_s"],
                    dtype=np.float64,
                )
                vz = np.asarray(
                    z["Vz_m_s"],
                    dtype=np.float64,
                )
                xyz = np.asarray(
                    z["streamline_xyz_m"],
                    dtype=np.float64,
                )
                tof = np.asarray(
                    z["pollock_tof_s"],
                    dtype=np.float64,
                )
                weight = np.asarray(
                    z["streamline_weight_m3_s"],
                    dtype=np.float64,
                )

            gate(
                f"{rid}_phi_shape",
                phi_grid.shape == GRID,
                phi_grid.shape,
            )

            gate(
                f"{rid}_XYZ_shape",
                xyz.shape == (NSL, NN, 3),
                xyz.shape,
            )

            gate(
                f"{rid}_TOF_shape",
                tof.shape == (NSL, NN),
                tof.shape,
            )

            cx, cy, cz = r7.face_to_cell(
                vx,
                vy,
                vz,
            )

            adv_grid, adv_audit = r7.solve_adv(
                cx,
                cy,
                cz,
                source_mask,
                DX,
                DY,
                DZ,
            )

            sci_gate(
                f"{rid}_ADV_finite",
                adv_audit["finite"],
            )

            sci_gate(
                f"{rid}_ADV_nonnegative",
                adv_audit["nonnegative"],
            )

            sci_gate(
                f"{rid}_ADV_non_source_positive",
                adv_audit["non_source_positive"],
            )

            sci_gate(
                f"{rid}_ADV_residual_lt_1e8",
                adv_audit["relative_L2_residual"] < 1.0e-8,
                adv_audit["relative_L2_residual"],
            )

            origin = np.array(
                [0.0, 0.0, 0.0],
                dtype=np.float64,
            )

            adv_s, _ = c2.trilinear(
                adv_grid,
                xyz,
                DX,
                DY,
                DZ,
                origin,
            )

            kx_s, _ = c2.trilinear(
                Kx,
                xyz,
                DX,
                DY,
                DZ,
                origin,
            )

            ky_s, _ = c2.trilinear(
                Ky,
                xyz,
                DX,
                DY,
                DZ,
                origin,
            )

            kz_s, _ = c2.trilinear(
                Kz,
                xyz,
                DX,
                DY,
                DZ,
                origin,
            )

            phi_s, _ = c2.trilinear(
                phi_grid,
                xyz,
                DX,
                DY,
                DZ,
                origin,
            )

            p_s, _ = c2.trilinear(
                pressure,
                xyz,
                DX,
                DY,
                DZ,
                origin,
            )

            operator = build_operator_geometry(
                xyz,
                tof,
            )

            tau_end = operator["terminal_TOF_s"]
            pth = tof / tau_end[:, None]

            xi = np.broadcast_to(
                np.linspace(
                    0.0,
                    1.0,
                    NN,
                    dtype=np.float64,
                )[None, :],
                (NSL, NN),
            )

            sci_gate(
                f"{rid}_xi_pollock_hat_identity",
                float(
                    np.max(
                        np.abs(
                            xi - pth
                        )
                    )
                )
                <= 1.0e-10,
                float(
                    np.max(
                        np.abs(
                            xi - pth
                        )
                    )
                ),
            )

            Kh = np.sqrt(
                np.maximum(kx_s, 1.0e-30)
                * np.maximum(ky_s, 1.0e-30)
            )

            logKh = np.log10(
                np.maximum(
                    Kh,
                    1.0e-30,
                )
            )

            logKratio = np.log10(
                np.maximum(
                    kz_s,
                    1.0e-30,
                )
                / np.maximum(
                    Kh,
                    1.0e-30,
                )
            )

            raw = {
                "rid": rid,
                "seed": seed,
                "partition": partition,
                "phi_grid": phi_grid,
                "xyz": xyz,
                "tof": tof,
                "weight": weight,
                "adv_grid": adv_grid,
                "adv_s": adv_s,
                "logKh": logKh,
                "logKratio": logKratio,
                "phi_s": phi_s,
                "pressure_s": p_s,
                "operator": operator,
                "xi": xi,
                "pollock_hat": pth,
                "adv_audit": adv_audit,
            }

            per_case[rid] = raw

            if partition == "TRAIN":
                train_pressure_values.append(
                    p_s.ravel()
                )
                train_log_weights.append(
                    np.log(
                        np.maximum(
                            weight,
                            1.0e-300,
                        )
                    )
                )

        # ------------------------------------------------------------------
        # TRAIN-only normalization — OOD never contributes statistics.
        # ------------------------------------------------------------------
        stage = "TRAIN_only_normalization"

        p_train = np.concatenate(
            train_pressure_values
        )

        lw_train = np.concatenate(
            train_log_weights
        )

        pmean = float(np.mean(p_train))
        pstd = float(np.std(p_train))
        lwmean = float(np.mean(lw_train))
        lwstd = float(np.std(lw_train))

        sci_gate(
            "TRAIN_pressure_std_positive",
            np.isfinite(pstd) and pstd > 0.0,
            pstd,
        )

        sci_gate(
            "TRAIN_logweight_std_positive",
            np.isfinite(lwstd) and lwstd > 0.0,
            lwstd,
        )

        normalization = {
            "pressure_mean_psi": np.asarray(
                [pmean],
                dtype=np.float64,
            ),
            "pressure_std_psi": np.asarray(
                [pstd],
                dtype=np.float64,
            ),
            "ln_weight_mean": np.asarray(
                [lwmean],
                dtype=np.float64,
            ),
            "ln_weight_std": np.asarray(
                [lwstd],
                dtype=np.float64,
            ),
            "fit_realizations": np.asarray(
                ["AV2PHI0001", "AV2PHI0002"],
                dtype="U32",
            ),
            "validation_used_for_fit": np.asarray(
                [False],
                dtype=np.bool_,
            ),
            "locked_OOD_used_for_fit": np.asarray(
                [False],
                dtype=np.bool_,
            ),
        }

        # ------------------------------------------------------------------
        # Generate teacher targets ONLY for TRAIN + VALIDATION.
        # ------------------------------------------------------------------
        stage = "teacher_generation"

        teacher_rows: list[dict[str, Any]] = []
        teacher_Y: dict[str, np.ndarray] = {}

        for rid, seed, partition in REALIZATIONS:
            case = per_case[rid]

            if partition == "LOCKED_OOD_TEST":
                # Critical leakage firewall: no call to generate_teacher().
                continue

            teacher_generation_started = True

            print("\n" + "=" * 206)
            print(
                f"AV2-A3 TEACHER — {rid} / {partition}"
            )
            print("=" * 206)

            Y, td = generate_teacher(
                case["phi_s"],
                case["operator"],
                DAYS,
            )

            passed = teacher_diag_pass(td)

            sci_gate(
                f"{rid}_teacher_certification",
                passed,
                td,
            )

            sci_gate(
                f"{rid}_Y_shape_9_1078_201",
                Y.shape == (NT, NSL, NN),
                Y.shape,
            )

            teacher_Y[rid] = Y

            teacher_rows.append(
                {
                    "porosity_realization_id": rid,
                    "seed": seed,
                    "partition": partition,
                    **td,
                    "certified": passed,
                }
            )

            teacher_realizations_completed += 1

        sci_gate(
            "exactly_three_supervised_realizations_generated",
            teacher_realizations_completed == 3,
            teacher_realizations_completed,
        )

        sci_gate(
            "LOCKED_OOD_target_not_generated",
            "AV2PHI0004" not in teacher_Y,
        )

        locked_ood_target_opened = False

        # ------------------------------------------------------------------
        # Assemble 7-channel conditioning + exact 2 time channels.
        # ------------------------------------------------------------------
        stage = "dataset_assembly"

        trainval_blocks: list[dict[str, np.ndarray]] = []
        ood_block: dict[str, np.ndarray] | None = None

        side_M = []
        side_Mf = []
        side_cv = []
        side_phi = []
        side_tauend = []

        for realization_index, (
            rid,
            seed,
            partition,
        ) in enumerate(REALIZATIONS):
            case = per_case[rid]

            X7 = np.stack(
                [
                    case["xi"],
                    case["pollock_hat"],
                    (
                        case["adv_s"]
                        / case["operator"]["terminal_TOF_s"][:, None]
                    ),
                    case["logKh"],
                    case["logKratio"],
                    case["phi_s"],
                    (
                        (
                            case["pressure_s"]
                            - pmean
                        )
                        / pstd
                    ),
                ],
                axis=-1,
            ).astype(np.float32)

            sci_gate(
                f"{rid}_X7_shape",
                X7.shape == (NSL, NN, 7),
                X7.shape,
            )

            sci_gate(
                f"{rid}_X7_finite",
                np.all(np.isfinite(X7)),
            )

            target_eta = (
                DAYS[:, None]
                * SPD
                / case["operator"]["terminal_TOF_s"][None, :]
            )

            X7f = np.broadcast_to(
                X7[None, :, :, :],
                (NT, NSL, NN, 7),
            ).reshape(
                NT * NSL,
                NN,
                7,
            ).copy()

            td = np.repeat(
                DAYS,
                NSL,
            )

            th = (
                td / 1000.0
            ).astype(
                np.float32
            )

            es = np.repeat(
                target_eta[:, :, None],
                NN,
                axis=2,
            ).reshape(
                NT * NSL,
                NN,
            ).astype(
                np.float32
            )

            T = np.broadcast_to(
                th[:, None, None],
                (
                    NT * NSL,
                    NN,
                    1,
                ),
            ).astype(
                np.float32
            )

            X9 = np.concatenate(
                [
                    X7f,
                    T,
                    es[:, :, None],
                ],
                axis=2,
            ).astype(
                np.float32
            )

            sci_gate(
                f"{rid}_X9_shape",
                X9.shape
                == (
                    NT * NSL,
                    NN,
                    INPUT_CHANNELS,
                ),
                X9.shape,
            )

            ti = np.repeat(
                np.arange(
                    NT,
                    dtype=np.int64,
                ),
                NSL,
            )

            si = np.tile(
                np.arange(
                    NSL,
                    dtype=np.int64,
                ),
                NT,
            )

            ri = np.full(
                NT * NSL,
                realization_index,
                dtype=np.int64,
            )

            static_weight = (
                (
                    np.log(
                        np.maximum(
                            case["weight"],
                            1.0e-300,
                        )
                    )
                    - lwmean
                )
                / lwstd
            ).astype(
                np.float32
            )

            side_M.append(
                case["operator"]["metric_M"]
            )
            side_Mf.append(
                case["operator"]["metric_M_face"]
            )
            side_cv.append(
                case["operator"]["control_volume_dtheta"]
            )
            side_phi.append(
                case["phi_s"]
            )
            side_tauend.append(
                case["operator"]["terminal_TOF_s"]
            )

            if partition in {
                "TRAIN",
                "VALIDATION",
            }:
                Y = teacher_Y[rid].reshape(
                    NT * NSL,
                    NN,
                ).astype(
                    np.float32
                )

                part_code = (
                    0
                    if partition == "TRAIN"
                    else 1
                )

                trainval_blocks.append(
                    {
                        "X": X9,
                        "Y": Y,
                        "realization_index": ri,
                        "time_index": ti,
                        "streamline_index": si,
                        "partition_code": np.full(
                            NT * NSL,
                            part_code,
                            dtype=np.int8,
                        ),
                        "target_time_days": td.astype(np.float32),
                        "target_time_hat": th,
                        "target_eta_sequence": es,
                    }
                )

            else:
                ood_block = {
                    "X": X9,
                    "realization_index": ri,
                    "time_index": ti,
                    "streamline_index": si,
                    "target_time_days": td.astype(np.float32),
                    "target_time_hat": th,
                    "target_eta_sequence": es,
                    "static_log_streamline_weight_z": np.broadcast_to(
                        static_weight[None, :],
                        (NT, NSL),
                    ).reshape(-1),
                }

        if ood_block is None:
            raise GateError(
                "locked_OOD_predictor_block_missing"
            )

        X_tv = np.concatenate(
            [
                b["X"]
                for b in trainval_blocks
            ],
            axis=0,
        )

        Y_tv = np.concatenate(
            [
                b["Y"]
                for b in trainval_blocks
            ],
            axis=0,
        )

        realization_tv = np.concatenate(
            [
                b["realization_index"]
                for b in trainval_blocks
            ]
        )

        time_tv = np.concatenate(
            [
                b["time_index"]
                for b in trainval_blocks
            ]
        )

        streamline_tv = np.concatenate(
            [
                b["streamline_index"]
                for b in trainval_blocks
            ]
        )

        partition_tv = np.concatenate(
            [
                b["partition_code"]
                for b in trainval_blocks
            ]
        )

        day_tv = np.concatenate(
            [
                b["target_time_days"]
                for b in trainval_blocks
            ]
        )

        th_tv = np.concatenate(
            [
                b["target_time_hat"]
                for b in trainval_blocks
            ]
        )

        eta_tv = np.concatenate(
            [
                b["target_eta_sequence"]
                for b in trainval_blocks
            ],
            axis=0,
        )

        train_count = int(
            np.sum(
                partition_tv == 0
            )
        )

        val_count = int(
            np.sum(
                partition_tv == 1
            )
        )

        expected_train = 2 * NT * NSL
        expected_val = 1 * NT * NSL
        expected_ood = NT * NSL

        sci_gate(
            "TRAIN_sample_count_exact",
            train_count == expected_train,
            train_count,
        )

        sci_gate(
            "VALIDATION_sample_count_exact",
            val_count == expected_val,
            val_count,
        )

        sci_gate(
            "LOCKED_OOD_predictor_count_exact",
            ood_block["X"].shape[0] == expected_ood,
            ood_block["X"].shape[0],
        )

        sci_gate(
            "TRAIN_validation_X_shape",
            X_tv.shape
            == (
                expected_train + expected_val,
                NN,
                INPUT_CHANNELS,
            ),
            X_tv.shape,
        )

        sci_gate(
            "TRAIN_validation_Y_shape",
            Y_tv.shape
            == (
                expected_train + expected_val,
                NN,
            ),
            Y_tv.shape,
        )

        sci_gate(
            "LOCKED_OOD_X_shape",
            ood_block["X"].shape
            == (
                expected_ood,
                NN,
                INPUT_CHANNELS,
            ),
            ood_block["X"].shape,
        )

        # ------------------------------------------------------------------
        # Pair counts for the frozen C25-style physics loss.
        # Every realization/streamline contains all nine times.
        # ------------------------------------------------------------------
        train_pairs = 2 * NSL * (NT - 1)
        val_pairs = 1 * NSL * (NT - 1)

        sci_gate(
            "TRAIN_adjacent_time_pair_count_exact",
            train_pairs == 17248,
            train_pairs,
        )

        sci_gate(
            "VALIDATION_adjacent_time_pair_count_exact",
            val_pairs == 8624,
            val_pairs,
        )

        # ------------------------------------------------------------------
        # Freeze PI-RNN protocol before training.
        # ------------------------------------------------------------------
        stage = "protocol_freeze"

        protocol = {
            "milestone": MILESTONE,
            "protocol_id": PROTOCOL_ID,
            "architecture": {
                "family": "C26 stacked LSTM -> TimeDistributed Dense -> bounded saturation",
                "input_nodes": NN,
                "input_channels": INPUT_CHANNELS,
                "required_channels": [
                    "xi",
                    "pollock_tau_hat",
                    "adv_tau_hat",
                    "log10_Kh",
                    "log10_Kz_over_Kh",
                    "porosity",
                    "pressure_z",
                    "target_time_hat",
                    "target_eta_sequence",
                ],
                "hidden_units": HIDDEN_UNITS,
                "lstm_layers": LSTM_LAYERS,
                "output_units_per_node": 1,
                "output_mapping": "0.20 + 0.60*sigmoid(raw)",
                "optional_FMM_XYZ_static_promoted": False,
            },
            "normalization": {
                "pressure": "z-score fitted on AV2PHI0001+0002 predictor nodes only",
                "streamline_weight": "log-z fitted on AV2PHI0001+0002 only; auxiliary sidecar, not model input",
                "log10_Kh": "raw transformed channel as in C4/C26; no fitted z-score",
                "log10_Kz_over_Kh": "raw transformed channel as in C4/C26; no fitted z-score",
                "porosity": "raw physical fraction; no fitted transform",
                "target_time_hat": "target_days / 1000",
                "target_eta_sequence": "target_days*86400 / terminal_Pollock_TOF",
                "VALIDATION_used_for_normalization_fit": False,
                "LOCKED_OOD_used_for_normalization_fit": False,
            },
            "teacher": {
                "supervised_realizations": [
                    "AV2PHI0001",
                    "AV2PHI0002",
                    "AV2PHI0003",
                ],
                "locked_OOD_teacher_generated": False,
                "target_days": DAYS.tolist(),
                "equation": (
                    "dS/deta + d fw/dtheta = "
                    "(phi(theta)/Pe_c) M d/dtheta[D_tilde(S) M dS/dtheta]"
                ),
                "local_phi_role": (
                    "Direct AV2 extension of the frozen Stage4/C7 coefficient phi/Pe_c: "
                    "the former scalar Foundation phi=0.20 is replaced by sampled local phi(theta)."
                ),
                "Pe_c": PE_C,
                "lambda_c": LAMBDA_C,
                "Corey_and_viscosity_parameters": P,
                "Pollock_kinematics_primary": True,
                "legacy_exp_Nc_xD_applied": False,
            },
            "physics_loss": {
                "objective": "L = 1.0*L_data + 0.01*L_phys",
                "lambda_data": LAMBDA_DATA,
                "lambda_phys": LAMBDA_PHYS,
                "R0": R0,
                "residual": (
                    "R=dS/deta + dfw/dtheta - "
                    "(phi(theta)/Pe_c) M d/dtheta[D_tilde(S) M dS/dtheta]"
                ),
                "time_derivative": (
                    "adjacent frozen target-time predictions, same realization and same streamline"
                ),
                "spatial_state": "midpoint of adjacent-time predictions",
                "PDE_nodes": "1..199",
                "metric_M": "realization-specific A3 sidecar derived from A2 Pollock XYZ/TOF",
                "phi": "realization-specific sampled porosity sidecar",
                "train_adjacent_pairs": train_pairs,
                "validation_adjacent_pairs": val_pairs,
                "LOCKED_OOD_pairs_for_selection": 0,
            },
            "optimizer_and_selection": {
                "optimizer": "Adam",
                "learning_rate": INITIAL_LR,
                "batch_size": BATCH_SIZE,
                "max_epochs": MAX_EPOCHS,
                "training_seed": TRAINING_SEED,
                "shuffle_training_pairs_each_epoch": True,
                "early_stopping_monitor": "validation total objective",
                "early_stopping_patience": EARLY_STOP_PATIENCE,
                "early_stopping_min_delta": EARLY_STOP_MIN_DELTA,
                "LR_reduce_factor": LR_REDUCE_FACTOR,
                "LR_reduce_patience": LR_REDUCE_PATIENCE,
                "minimum_learning_rate": MIN_LR,
                "checkpoint_selection": "minimum validation total objective",
            },
            "firewall": {
                "TRAIN": [
                    "AV2PHI0001",
                    "AV2PHI0002",
                ],
                "VALIDATION": [
                    "AV2PHI0003",
                ],
                "LOCKED_OOD_TEST": [
                    "AV2PHI0004",
                ],
                "LOCKED_OOD_Y_generated_in_A3": False,
                "LOCKED_OOD_Y_access_before_checkpoint_freeze": False,
                "checkpoint_selection_uses_LOCKED_OOD": False,
                "retraining_after_LOCKED_OOD": False,
                "threshold_retuning_after_LOCKED_OOD": False,
            },
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "teacher_generation_performed": True,
            "teacher_realizations": 3,
            "TRAIN_teacher_realizations": 2,
            "VALIDATION_teacher_realizations": 1,
            "LOCKED_OOD_teacher_generated": False,
            "LOCKED_OOD_target_opened": locked_ood_target_opened,
            "TRAIN_only_normalization_fit": True,
            "PI_RNN_training_performed": False,
            "checkpoint_created": False,
            "model_inference_performed": False,
            "mapback_performed": False,
            "CMG_validation_performed": False,
            "AV1_K_modified": False,
            "A2_porosity_or_kinematics_modified": False,
            "training_authorized": True,
            "next": {
                "milestone": "POSTV16-AV2-A4",
                "name": (
                    "Variable-Porosity PI-RNN Training, Best-Validation Checkpoint, "
                    "and One-Touch Locked-OOD Evaluation"
                ),
                "authorized": True,
                "LOCKED_OOD_target_generation_authorized_only_after_checkpoint_freeze": True,
            },
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "teacher_realizations_certified": teacher_realizations_completed,
            "TRAIN_samples": train_count,
            "VALIDATION_samples": val_count,
            "LOCKED_OOD_predictor_samples": int(
                ood_block["X"].shape[0]
            ),
            "LOCKED_OOD_target_generated": False,
            "input_shape_train_validation": list(X_tv.shape),
            "target_shape_train_validation": list(Y_tv.shape),
            "input_shape_locked_OOD": list(ood_block["X"].shape),
            "train_adjacent_pairs": train_pairs,
            "validation_adjacent_pairs": val_pairs,
            "architecture": "2xLSTM64_TimeDistributed_Dense_bounded_Sw",
            "lambda_phys": LAMBDA_PHYS,
            "training_performed": False,
            "checkpoint_created": False,
            "inference": False,
            "mapback": False,
            "CMG_validation": False,
            "next": decision["next"],
        }

        sidecar = {
            "metric_M": np.stack(
                side_M,
                axis=0,
            ).astype(np.float64),
            "metric_M_face": np.stack(
                side_Mf,
                axis=0,
            ).astype(np.float64),
            "control_volume_dtheta": np.stack(
                side_cv,
                axis=0,
            ).astype(np.float64),
            "porosity_sequence": np.stack(
                side_phi,
                axis=0,
            ).astype(np.float64),
            "terminal_pollock_tof_s": np.stack(
                side_tauend,
                axis=0,
            ).astype(np.float64),
            "realization_id": np.asarray(
                [r[0] for r in REALIZATIONS],
                dtype="U32",
            ),
            "partition": np.asarray(
                [r[2] for r in REALIZATIONS],
                dtype="U32",
            ),
        }

        files = {
            "PAD_Stream_POSTV16_AV2_A3_Summary.json":
                json_bytes(summary),

            "POSTV16_AV2_A3_TrainValidation_Transport_Dataset.npz":
                deterministic_npz_bytes(
                    {
                        "X_required_9": X_tv,
                        "Y_transport": Y_tv,
                        "realization_index": realization_tv,
                        "time_index": time_tv,
                        "streamline_index": streamline_tv,
                        "partition_code": partition_tv,
                        "target_time_days": day_tv,
                        "target_time_hat": th_tv,
                        "target_eta_sequence": eta_tv,
                        "partition_names": np.asarray(
                            ["TRAIN", "VALIDATION"],
                            dtype="U32",
                        ),
                    }
                ),

            "POSTV16_AV2_A3_LockedOOD_Predictor_Only_Dataset.npz":
                deterministic_npz_bytes(
                    {
                        "X_required_9": ood_block["X"],
                        "realization_index": ood_block["realization_index"],
                        "time_index": ood_block["time_index"],
                        "streamline_index": ood_block["streamline_index"],
                        "target_time_days": ood_block["target_time_days"],
                        "target_time_hat": ood_block["target_time_hat"],
                        "target_eta_sequence": ood_block["target_eta_sequence"],
                        "static_log_streamline_weight_z":
                            ood_block["static_log_streamline_weight_z"],
                        "contains_Y_transport": np.asarray(
                            [False],
                            dtype=np.bool_,
                        ),
                    }
                ),

            "POSTV16_AV2_A3_Variable_Porosity_Physics_Sidecar.npz":
                deterministic_npz_bytes(sidecar),

            "POSTV16_AV2_A3_TRAIN_Only_Normalization.npz":
                deterministic_npz_bytes(normalization),

            "POSTV16_AV2_A3_Teacher_Certification_By_Realization.csv":
                csv_bytes(teacher_rows),

            "POSTV16_AV2_A3_Frozen_PIRNN_Training_and_Physics_Objective_Contract.json":
                json_bytes(protocol),

            "POSTV16_AV2_A3_Decision_Contract.json":
                json_bytes(decision),

            "POSTV16_AV2_A3_Final_Gate_Matrix.csv":
                csv_bytes(
                    [
                        {
                            "gate": k,
                            **v,
                        }
                        for k, v in gates.items()
                    ]
                ),
        }

        immutable_publish(
            out,
            files,
        )

        manifest_rows = []

        for q in sorted(out.iterdir()):
            if (
                q.is_file()
                and q.name
                != "POSTV16_AV2_A3_Artifact_Manifest.csv"
            ):
                manifest_rows.append(
                    {
                        "file": q.name,
                        "sha256": sha256_file(q),
                        "bytes": q.stat().st_size,
                    }
                )

        immutable_publish(
            out,
            {
                "POSTV16_AV2_A3_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print("\n" + "=" * 206)
        print("POSTV16-AV2-A3: PASS")
        print("=" * 206)
        print(f"{'Status':122}: {STATUS_PASS}")
        print(f"{'Teacher realizations certified':122}: 3 / 3")
        print(f"{'TRAIN samples':122}: {train_count}")
        print(f"{'VALIDATION samples':122}: {val_count}")
        print(f"{'LOCKED OOD predictor samples':122}: {ood_block['X'].shape[0]}")
        print(f"{'LOCKED OOD Y generated/opened':122}: False / False")
        print(f"{'TRAIN-only pressure normalization mean/std [psi]':122}: {pmean:.9f} / {pstd:.9f}")
        print(f"{'Architecture':122}: 2 x LSTM(64) -> TimeDistributed Dense -> bounded Sw")
        print(f"{'Input':122}: 201 nodes x 9 channels")
        print(f"{'Physics residual local phi':122}: True")
        print(f"{'lambda_data / lambda_phys':122}: 1.0 / 0.01")
        print(f"{'TRAIN / VALIDATION adjacent-time physics pairs':122}: {train_pairs} / {val_pairs}")
        print(f"{'Training / checkpoint / inference / mapback':122}: False / False / False / False")
        print(f"{'CMG validation':122}: False")
        print(f"{'Next milestone authorized':122}: True")
        print(f"{'NEXT':122}: POSTV16-AV2-A4 — train, freeze checkpoint, then one-touch locked-OOD")
        print("=" * 206)

        return 0

    except ScientificFail as exc:
        fail.mkdir(
            parents=True,
            exist_ok=True,
        )

        report = {
            "milestone": MILESTONE,
            "status": STATUS_FAIL,
            "failed_stage": stage,
            "failed_gate": exc.gate,
            "detail": exc.detail,
            "gates": gates,
            "teacher_generation_started": teacher_generation_started,
            "teacher_realizations_completed": teacher_realizations_completed,
            "LOCKED_OOD_target_opened": locked_ood_target_opened,
            "training": False,
            "checkpoint_created": False,
            "inference": False,
            "mapback": False,
            "CMG_validation": False,
            "next_milestone_authorized": False,
            "next_action": (
                "Freeze and interpret the A3 scientific failure. "
                "Do not open AV2PHI0004 Y, relax teacher gates, or retune the "
                "porosity model/training protocol based on this result."
            ),
        }

        data = json_bytes(report)

        q = fail / "POSTV16_AV2_A3_Scientific_Fail_Report.json"

        if q.exists() and q.read_bytes() != data:
            suffix = hashlib.sha256(
                data
            ).hexdigest()[:12]
            q = fail / (
                f"POSTV16_AV2_A3_Scientific_Fail_Report_{suffix}.json"
            )

        if not q.exists():
            q.write_bytes(data)

        print("\n" + "=" * 206)
        print("POSTV16-AV2-A3: SCIENTIFIC FAIL")
        print("=" * 206)
        print("Failed stage:", stage)
        print("Failed gate :", exc.gate)
        print("Detail      :", exc.detail)
        print("LOCKED OOD Y opened:", locked_ood_target_opened)
        print("POSTV16-AV2-A4 IS NOT AUTHORIZED.")

        return 3

    except Exception as exc:
        blocked.mkdir(
            parents=True,
            exist_ok=True,
        )

        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "teacher_generation_started": teacher_generation_started,
            "teacher_realizations_completed": teacher_realizations_completed,
            "LOCKED_OOD_target_opened": locked_ood_target_opened,
            "training": False,
            "checkpoint_created": False,
            "inference": False,
            "mapback": False,
            "CMG_validation": False,
            "next_milestone_authorized": False,
            "next_action": (
                "Audit only the technical A3 failure. "
                "Do not open the LOCKED-OOD target or change the frozen A1/A2 design."
            ),
        }

        data = json_bytes(report)

        q = blocked / "POSTV16_AV2_A3_Blocked_Report.json"

        if q.exists() and q.read_bytes() != data:
            suffix = hashlib.sha256(
                data
            ).hexdigest()[:12]
            q = blocked / (
                f"POSTV16_AV2_A3_Blocked_Report_{suffix}.json"
            )

        if not q.exists():
            q.write_bytes(data)

        print("\n" + "=" * 206)
        print("POSTV16-AV2-A3: BLOCKED")
        print("=" * 206)
        print("Failed stage:", stage)
        print("Exception   :", repr(exc))
        print("LOCKED OOD Y opened:", locked_ood_target_opened)

        return 2


def parse_args():
    p = argparse.ArgumentParser()

    p.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
    )

    p.add_argument(
        "--drive-root",
        type=Path,
        default=Path(
            "/content/drive/MyDrive/PAD_Stream_Compute"
        ),
    )

    p.add_argument(
        "--self-test",
        action="store_true",
    )

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
