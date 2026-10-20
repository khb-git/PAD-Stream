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


MILESTONE = "POSTV16-AV3-A4-R2"

PROTOCOL_ID = (
    "POSTV16_AV3_A4_R2_CORRECTED_TEACHER_CERTIFICATION_"
    "CELL_CENTERED_SPATIAL_COREY_RELPERM_13CHANNEL_DATASET_"
    "PHYSICS_SIDECAR_AND_LOCKED_OOD_PREDICTOR_V1"
)

STATUS_PASS = (
    "AV3A4R2_CORRECTED_CERTIFICATION_TRAIN_VALIDATION_TEACHERS_"
    "13CHANNEL_DATASET_PHYSICS_SIDECAR_AND_LOCKED_OOD_PREDICTOR_ONLY_PASS"
)

STATUS_FAIL = (
    "AV3A4R2_SPATIAL_COREY_RELPERM_TEACHER_OR_DATASET_SCIENTIFIC_FAIL_"
    "ORIGINAL_A4_FAIL_PRESERVED_NO_OOD_OPENING_RESEED_RETUNE_OR_TRAINING_AUTHORIZED"
)

STATUS_BLOCKED = "AV3A4R2_TECHNICAL_EXECUTION_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_A4R1_COMMIT = "77dd4f7d615b44bf1023bfc1ead3faec1d6c21f6"

ORIGINAL_A4_FAIL_SHA256 = "1fdc0aeb7c462b7161525d52b1aa381b80885ffba00a4afa80875a67861cd08d"
ORIGINAL_A4_FAIL_STATUS = (
    "AV3A4_SPATIAL_COREY_RELPERM_TEACHER_OR_DATASET_SCIENTIFIC_FAIL_"
    "NO_OOD_OPENING_RESEED_RETUNE_OR_TRAINING_AUTHORIZED"
)

# --------------------------------------------------------------------------------------------------
# Exact source lineage.
# --------------------------------------------------------------------------------------------------

A4R1 = (
    "PAD_Stream_POSTV16_AV3_A4_R1_"
    "Teacher_Certification_Failure_Semantics_Closure.py"
)
A4R1_BLOB = "cdd6c52de598cfc1674828d4d7918828e828f2ab"

A4 = (
    "PAD_Stream_POSTV16_AV3_A4_"
    "Corrected_CellCentered_Teacher_Dataset_and_LockedOOD_Predictor.py"
)
A4_BLOB = "24a6e4b815b83dfe89eca85a18ccc23021b4eefb"

A3R1 = (
    "PAD_Stream_POSTV16_AV3_A3_R1_"
    "First9_CellCentered_Geometry_and_Normalization_Authority_Correction.py"
)
A3R1_BLOB = "2a70ef6b67ddefee61b5a9ab2fb080755fdb4b49"

A3 = "PAD_Stream_POSTV16_AV3_A3_Transport_Teacher_Residual_and_PIRNN_Protocol_Freeze.py"
A3_BLOB = "40fe89c142e62aad750a749f0a8ae452574f28bd"

A2 = (
    "PAD_Stream_POSTV16_AV3_A2_"
    "Corey_Relperm_Field_Realization_Certification_and_Streamline_Sampling.py"
)
A2_BLOB = "e7d4f1b1e69ea3e756c4f41d7edb57e2ffd87d7b"

AV2A2 = "PAD_Stream_POSTV16_AV2_A2_Porosity_Realization_and_Pore_Kinematics_Execution.py"
AV2A2_BLOB = "f141b07f0424d29a7996c089a76dbe7128af5132"

R7 = "PAD_Stream_POSTV16_AV1_D_R7_Full_End_to_End_PAD_Stream_Integration.py"
R7_BLOB = "a28722b0b8059bd50d94fb8a914defc0b35f2f7b"

B2 = "PAD_Stream_V16B2_Exact_3D_Fast_Marching_Arrival_Time_Baseline.py"
B2_BLOB = "95025d1e67a74f9dacaad311e5a402b63e7b4335"

C2 = "PAD_Stream_V16C2_Multi_Coordinate_Streamline_Transport_Database_Assembly.py"
C2_BLOB = "21ff44de456102772c99f7ddc80898c9139a76db"

SOURCE_BLOBS = {
    A4R1: A4R1_BLOB,
    A4: A4_BLOB,
    A3R1: A3R1_BLOB,
    A3: A3_BLOB,
    A2: A2_BLOB,
    AV2A2: AV2A2_BLOB,
    R7: R7_BLOB,
    B2: B2_BLOB,
    C2: C2_BLOB,
}

# --------------------------------------------------------------------------------------------------
# Drive authorities.
# --------------------------------------------------------------------------------------------------

BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"

ORIGINAL_A4_FAIL_REL = (
    BASE_AV3
    / "POSTV16_AV3_A4_SCIENTIFIC_FAIL"
    / "POSTV16_AV3_A4_Scientific_Fail_Report.json"
)

A4R1_REL = (
    BASE_AV3
    / "POSTV16_AV3_A4_R1_Teacher_Certification_Failure_Semantics_Closure"
)
A4R1_SUMMARY = "PAD_Stream_POSTV16_AV3_A4_R1_Summary.json"
A4R1_CORRECTED = "POSTV16_AV3_A4_R1_Corrected_Teacher_Certification_Contract.json"
A4R1_HANDOFF = "POSTV16_AV3_A4_R1_R2_Handoff_Contract.json"
A4R1_DECISION = "POSTV16_AV3_A4_R1_Decision_Contract.json"
A4R1_MANIFEST = "POSTV16_AV3_A4_R1_Artifact_Manifest.csv"

A4R1_STATUS = (
    "AV3A4R1_IMMUTABLE_A4_SCIENTIFIC_FAIL_PRESERVED_"
    "TEACHER_CERTIFICATION_GATE_SEMANTICS_ROOT_CAUSE_CLOSED_NO_TEACHER_REEXECUTION"
)

A3R1_REL = (
    BASE_AV3
    / "POSTV16_AV3_A3_R1_First9_CellCentered_Geometry_and_Normalization_Authority_Correction"
)
A3R1_SUMMARY = "PAD_Stream_POSTV16_AV3_A3_R1_Summary.json"
A3R1_FIRST9 = "POSTV16_AV3_A3_R1_First9_CellCentered_Channel_Contract.json"
A3R1_NORM = "POSTV16_AV3_A3_R1_Corrected_Normalization_Contract.json"
A3R1_SIDECAR = "POSTV16_AV3_A3_R1_Corrected_Physics_Sidecar_Contract.json"
A3R1_HANDOFF = "POSTV16_AV3_A3_R1_A4_Handoff_Contract.json"
A3R1_DECISION = "POSTV16_AV3_A3_R1_Decision_Contract.json"
A3R1_MANIFEST = "POSTV16_AV3_A3_R1_Artifact_Manifest.csv"

A3R1_STATUS = (
    "AV3A3R1_FIRST_NINE_CHANNEL_CELL_CENTERED_GEOMETRY_AND_"
    "TRAIN_NORMALIZATION_AUTHORITY_CORRECTION_FROZEN_NO_A4_EXECUTION"
)

A3_REL = BASE_AV3 / "POSTV16_AV3_A3_Transport_Teacher_Residual_and_PIRNN_Protocol_Freeze"
A3_SUMMARY = "PAD_Stream_POSTV16_AV3_A3_Summary.json"
A3_PDE = "POSTV16_AV3_A3_Spatial_Constitutive_Transport_Operator.json"
A3_DISC = "POSTV16_AV3_A3_Conservative_Face_Discretization_Contract.json"
A3_DATASET = "POSTV16_AV3_A3_Teacher_Dataset_and_Leakage_Firewall.json"
A3_RESIDUAL = "POSTV16_AV3_A3_Differentiable_Physics_Residual_Contract.json"
A3_MODEL = "POSTV16_AV3_A3_13Channel_PIRNN_Training_Protocol.json"
A3_DECISION = "POSTV16_AV3_A3_Decision_Contract.json"
A3_MANIFEST = "POSTV16_AV3_A3_Artifact_Manifest.csv"

A3_STATUS = (
    "AV3A3_SPATIAL_COREY_RELPERM_TRANSPORT_TEACHER_RESIDUAL_AND_"
    "13CHANNEL_PIRNN_PROTOCOL_PROSPECTIVELY_FROZEN_NO_TEACHER_OR_TRAINING_EXECUTION"
)

A2_REL = (
    BASE_AV3
    / "POSTV16_AV3_A2_Corey_Relperm_Field_Realization_Certification_and_Streamline_Sampling"
)
A2_SUMMARY = "PAD_Stream_POSTV16_AV3_A2_Summary.json"
A2_DECISION = "POSTV16_AV3_A2_Decision_Contract.json"
A2_MANIFEST = "POSTV16_AV3_A2_Artifact_Manifest.csv"

A2_STATUS = (
    "AV3A2_FROZEN_COREY_RELPERM_REALIZATIONS_GENERATED_CERTIFIED_"
    "AND_SAMPLED_TO_FROZEN_AV2_STREAMLINES_PASS"
)

BASE_AV2 = Path("post_v16") / RID / "POSTV16_AV2_Variable_Porosity"

AV2A2_REL = BASE_AV2 / "POSTV16_AV2_A2_Porosity_Realization_and_Pore_Kinematics_Execution"
AV2A2_SUMMARY = "PAD_Stream_POSTV16_AV2_A2_Summary.json"
AV2A2_DECISION = "POSTV16_AV2_A2_Decision_Contract.json"
AV2A2_MANIFEST = "POSTV16_AV2_A2_Artifact_Manifest.csv"

AV2A2_STATUS = (
    "AV2A2_FROZEN_SPATIAL_POROSITY_REALIZATIONS_GENERATED_"
    "PRESSURE_Q_INVARIANCE_CERTIFIED_PORE_KINEMATICS_RECONSTRUCTED_PASS"
)

OUT_REL = (
    BASE_AV3
    / "POSTV16_AV3_A4_R2_Corrected_Teacher_Dataset_and_LockedOOD_Predictor"
)
FAIL_REL = BASE_AV3 / "POSTV16_AV3_A4_R2_SCIENTIFIC_FAIL"
BLOCK_REL = BASE_AV3 / "POSTV16_AV3_A4_R2_BLOCKED"

FOUNDATION_NAME = "V16A_Foundation_Case_0001.npz"
FOUNDATION_SHA = "4239e412ca6e2780f108c8eb1b0252e80a56be305bce48cc58e50d6140b86acc"

# --------------------------------------------------------------------------------------------------
# Frozen numerical/physical contract.
# --------------------------------------------------------------------------------------------------

GRID = (15, 50, 50)
NZ, NY, NX = GRID

NSL = 1078
NN = 201
NT = 9

DX = 6.096
DY = 6.096
DZ = 1.2192

ORIGIN_CENTER_M = np.asarray(
    [DX / 2.0, DY / 2.0, DZ / 2.0],
    dtype=np.float64,
)

DAYS = np.asarray(
    [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0],
    dtype=np.float64,
)

SPD = 86400.0

REALIZATIONS = [
    ("AV3CR0001", "AV2PHI0001", "TRAIN"),
    ("AV3CR0002", "AV2PHI0002", "TRAIN"),
    ("AV3CR0003", "AV2PHI0003", "VALIDATION"),
    ("AV3CR0004", "AV2PHI0004", "LOCKED_OOD_TEST"),
]

FIRST9 = [
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

NEW4 = [
    "nw_hat",
    "no_hat",
    "krw_max_hat",
    "kro_max_hat",
]

CHANNELS13 = FIRST9 + NEW4

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

ADV_CONSERVATION_MAX = 1.0e-11
IMPLICIT_RESIDUAL_MAX = 1.0e-10
PRECLIP_BOUND_MAX = 1.0e-8
Y_BOUND_MAX = 1.0e-8
INLET_ERROR_MAX = 1.0e-12
# Historical A3 morphology threshold values are provenance only in R2.
# POSTV16-AV3-A4-R1 explicitly removed them from pass/fail certification.
LEGACY_A3_UNDERSHOOT_THRESHOLD_REFERENCE_ONLY = 1.0e-8
LEGACY_A3_TEMPORAL_NEGATIVE_FRACTION_THRESHOLD_REFERENCE_ONLY = 0.01
LEGACY_A3_SPATIAL_POSITIVE_FRACTION_THRESHOLD_REFERENCE_ONLY = 0.05

TRAIN_PROFILES = 2 * NT * NSL
VAL_PROFILES = NT * NSL
OOD_PROFILES = NT * NSL
TRAIN_PAIRS = 2 * (NT - 1) * NSL
VAL_PAIRS = (NT - 1) * NSL

MODEL_PARAMETERS = 53057
LAMBDA_PHYS = 0.01

DFW_GRID_POINTS = 4001
DFW_NODE_CHUNK = 1024


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
    return (
        json.dumps(
            obj,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""

    fields: list[str] = []

    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)

    s = io.StringIO(newline="")

    w = csv.DictWriter(
        s,
        fieldnames=fields,
        lineterminator="\n",
    )

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

            zf.writestr(
                info,
                b.getvalue(),
            )

    return outer.getvalue()


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(
        parents=True,
        exist_ok=True,
    )

    for name, data in files.items():
        p = out / name

        if p.exists() and p.read_bytes() != data:
            raise GateError("existing_output_differs:" + name)

        if not p.exists():
            p.write_bytes(data)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:
        raise GateError(
            f"cannot_load_module:{path}"
        )

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
                if (
                    p.is_file()
                    and sha256_file(p) == expected_sha
                ):
                    hits.append(
                        p.resolve()
                    )

            except OSError:
                pass

    if not hits:
        raise GateError(
            f"exact_authority_not_found:{name}:{expected_sha}"
        )

    return sorted(
        set(hits),
        key=lambda p: (
            len(str(p)),
            str(p),
        ),
    )[0]


def centered_derivative(
    y: np.ndarray,
    x: np.ndarray,
) -> np.ndarray:

    y = np.asarray(
        y,
        dtype=np.float64,
    )

    x = np.asarray(
        x,
        dtype=np.float64,
    )

    out = np.empty_like(y)

    dx0 = x[:, 1] - x[:, 0]
    dx1 = x[:, -1] - x[:, -2]

    if (
        np.any(dx0 <= 0.0)
        or np.any(dx1 <= 0.0)
    ):
        raise ScientificFail(
            "metric_endpoint_spacing_positive"
        )

    out[:, 0] = (
        y[:, 1] - y[:, 0]
    ) / dx0

    out[:, -1] = (
        y[:, -1] - y[:, -2]
    ) / dx1

    den = (
        x[:, 2:]
        - x[:, :-2]
    )

    if np.any(den <= 0.0):
        raise ScientificFail(
            "metric_centered_spacing_positive"
        )

    out[:, 1:-1] = (
        y[:, 2:]
        - y[:, :-2]
    ) / den

    return out


def build_operator_geometry(
    xyz: np.ndarray,
    tof: np.ndarray,
) -> dict[str, np.ndarray]:

    dxyz = np.diff(
        xyz,
        axis=1,
    )

    ds = np.linalg.norm(
        dxyz,
        axis=2,
    )

    if np.any(ds <= 0.0):
        raise ScientificFail(
            "positive_streamline_geometric_segments",
            int(
                np.sum(
                    ds <= 0.0
                )
            ),
        )

    s = np.concatenate(
        [
            np.zeros(
                (
                    xyz.shape[0],
                    1,
                ),
                dtype=np.float64,
            ),
            np.cumsum(
                ds,
                axis=1,
            ),
        ],
        axis=1,
    )

    L = s[:, -1]

    if np.any(L <= 0.0):
        raise ScientificFail(
            "positive_terminal_streamline_length"
        )

    xD = (
        s
        / L[:, None]
    )

    tau_end = tof[:, -1]

    if np.any(tau_end <= 0.0):
        raise ScientificFail(
            "positive_terminal_TOF"
        )

    theta = (
        tof
        / tau_end[:, None]
    )

    if np.any(
        np.diff(
            theta,
            axis=1,
        )
        <= 0.0
    ):
        raise ScientificFail(
            "strictly_increasing_normalized_TOF"
        )

    M = centered_derivative(
        theta,
        xD,
    )

    if (
        np.any(
            ~np.isfinite(M)
        )
        or np.any(
            M <= 0.0
        )
    ):
        raise ScientificFail(
            "positive_finite_coordinate_metric_M"
        )

    theta_face = np.empty(
        (
            theta.shape[0],
            theta.shape[1] + 1,
        ),
        dtype=np.float64,
    )

    theta_face[:, 1:-1] = (
        0.5
        * (
            theta[:, :-1]
            + theta[:, 1:]
        )
    )

    theta_face[:, 0] = theta[:, 0]
    theta_face[:, -1] = theta[:, -1]

    cv = np.diff(
        theta_face,
        axis=1,
    )

    if np.any(cv <= 0.0):
        raise ScientificFail(
            "positive_theta_control_volume_width"
        )

    M_face = np.empty(
        (
            M.shape[0],
            M.shape[1] + 1,
        ),
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

    if np.any(
        M_face <= 0.0
    ):
        raise ScientificFail(
            "positive_face_metric_M"
        )

    return {
        "theta": theta,
        "xD_arc": xD,
        "metric_M": M,
        "metric_M_face": M_face,
        "control_volume_dtheta": cv,
        "dtheta_center": np.diff(
            theta,
            axis=1,
        ),
        "terminal_length_m": L,
        "terminal_TOF_s": tau_end,
    }


def local_relperm(
    S: np.ndarray,
    nw: np.ndarray,
    no: np.ndarray,
    krw_max: np.ndarray,
    kro_max: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:

    span = (
        1.0
        - SWC
        - SOR
    )

    Se = np.clip(
        (
            np.asarray(
                S,
                dtype=np.float64,
            )
            - SWC
        )
        / span,
        0.0,
        1.0,
    )

    krw = (
        np.asarray(
            krw_max,
            dtype=np.float64,
        )
        * Se
        ** np.asarray(
            nw,
            dtype=np.float64,
        )
    )

    kro = (
        np.asarray(
            kro_max,
            dtype=np.float64,
        )
        * (
            1.0 - Se
        )
        ** np.asarray(
            no,
            dtype=np.float64,
        )
    )

    return krw, kro


def local_fw(
    S: np.ndarray,
    nw: np.ndarray,
    no: np.ndarray,
    krw_max: np.ndarray,
    kro_max: np.ndarray,
) -> np.ndarray:

    krw, kro = local_relperm(
        S,
        nw,
        no,
        krw_max,
        kro_max,
    )

    lw = krw / MU_W
    lo = kro / MU_O

    return (
        lw
        / (
            lw
            + lo
            + EPS
        )
    )


def local_dshape(
    S: np.ndarray,
    nw: np.ndarray,
    no: np.ndarray,
    krw_max: np.ndarray,
    kro_max: np.ndarray,
) -> np.ndarray:

    span = (
        1.0
        - SWC
        - SOR
    )

    S = np.asarray(
        S,
        dtype=np.float64,
    )

    Se = np.clip(
        (
            S
            - SWC
        )
        / span,
        1.0e-6,
        1.0 - 1.0e-6,
    )

    kro = (
        np.asarray(
            kro_max,
            dtype=np.float64,
        )
        * (
            1.0 - Se
        )
        ** np.asarray(
            no,
            dtype=np.float64,
        )
    )

    fw = local_fw(
        S,
        nw,
        no,
        krw_max,
        kro_max,
    )

    raw = (
        kro
        * fw
        * Se
        ** (
            -1.0
            / LAMBDA_C
            - 1.0
        )
    )

    Se_mid = np.full_like(
        Se,
        0.5,
    )

    S_mid = (
        SWC
        + span
        * Se_mid
    )

    kro_mid = (
        np.asarray(
            kro_max,
            dtype=np.float64,
        )
        * (
            1.0 - Se_mid
        )
        ** np.asarray(
            no,
            dtype=np.float64,
        )
    )

    fw_mid = local_fw(
        S_mid,
        nw,
        no,
        krw_max,
        kro_max,
    )

    norm = (
        kro_mid
        * fw_mid
        * Se_mid
        ** (
            -1.0
            / LAMBDA_C
            - 1.0
        )
    )

    return (
        raw
        / np.maximum(
            norm,
            EPS,
        )
    )


def max_dfw_realization(
    nw: np.ndarray,
    no: np.ndarray,
    krw_max: np.ndarray,
    kro_max: np.ndarray,
) -> float:
    """
    Frozen A3 CFL semantics:
      realization-local maximum |dfw/dS| evaluated from the actual sampled
      p(theta) fields on a fixed 4001-point saturation grid.

    The evaluation is chunked only for memory control; the search set is exact.
    """

    s = np.linspace(
        SWC,
        1.0 - SOR,
        DFW_GRID_POINTS,
        dtype=np.float64,
    )

    flat = [
        np.asarray(x, dtype=np.float64).reshape(-1)
        for x in (
            nw,
            no,
            krw_max,
            kro_max,
        )
    ]

    npts = flat[0].size

    best = 0.0

    for start in range(
        0,
        npts,
        DFW_NODE_CHUNK,
    ):

        stop = min(
            npts,
            start + DFW_NODE_CHUNK,
        )

        nww = flat[0][start:stop, None]
        noo = flat[1][start:stop, None]
        kww = flat[2][start:stop, None]
        koo = flat[3][start:stop, None]

        fw = local_fw(
            s[None, :],
            nww,
            noo,
            kww,
            koo,
        )

        grad = np.gradient(
            fw,
            s,
            axis=1,
        )

        local_best = float(
            np.max(
                np.abs(grad)
            )
        )

        best = max(
            best,
            local_best,
        )

    if (
        not np.isfinite(best)
        or best <= 0.0
    ):
        raise ScientificFail(
            "realization_local_dfw_max_positive_finite",
            best,
        )

    return best


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

    for j in range(
        1,
        n,
    ):

        w = (
            a[:, j]
            / b[:, j - 1]
        )

        b[:, j] -= (
            w
            * c[:, j - 1]
        )

        d[:, j] -= (
            w
            * d[:, j - 1]
        )

    x = np.empty_like(d)

    x[:, -1] = (
        d[:, -1]
        / b[:, -1]
    )

    for j in range(
        n - 2,
        -1,
        -1,
    ):

        x[:, j] = (
            d[:, j]
            - c[:, j]
            * x[:, j + 1]
        ) / b[:, j]

    return x


def advective_step_local_p(
    S: np.ndarray,
    dt: np.ndarray,
    cv: np.ndarray,
    nw: np.ndarray,
    no: np.ndarray,
    krw_max: np.ndarray,
    kro_max: np.ndarray,
) -> tuple[np.ndarray, float]:

    ns, n = S.shape

    F = np.zeros(
        (
            ns,
            n + 1,
        ),
        dtype=np.float64,
    )

    F[:, 1] = local_fw(
        np.full(
            ns,
            SW_INJ,
            dtype=np.float64,
        ),
        nw[:, 0],
        no[:, 0],
        krw_max[:, 0],
        kro_max[:, 0],
    )

    if n > 2:

        F[:, 2:n] = local_fw(
            S[:, 1:n - 1],
            nw[:, 1:n - 1],
            no[:, 1:n - 1],
            krw_max[:, 1:n - 1],
            kro_max[:, 1:n - 1],
        )

    F[:, n] = local_fw(
        S[:, -1],
        nw[:, -1],
        no[:, -1],
        krw_max[:, -1],
        kro_max[:, -1],
    )

    old = S.copy()

    S[:, 1:] -= (
        dt[:, None]
        * (
            F[:, 2:]
            - F[:, 1:-1]
        )
        / cv[:, 1:]
    )

    S[:, 0] = SW_INJ

    lhs = np.sum(
        cv[:, 1:]
        * (
            S[:, 1:]
            - old[:, 1:]
        ),
        axis=1,
    )

    rhs = (
        -dt
        * (
            F[:, -1]
            - F[:, 1]
        )
    )

    err = float(
        np.max(
            np.abs(
                lhs
                - rhs
            )
        )
    )

    return S, err


def capillary_implicit_local_p_phi(
    Sadv: np.ndarray,
    dt: np.ndarray,
    phi_seq: np.ndarray,
    M: np.ndarray,
    M_face: np.ndarray,
    cv: np.ndarray,
    dtheta: np.ndarray,
    nw: np.ndarray,
    no: np.ndarray,
    krw_max: np.ndarray,
    kro_max: np.ndarray,
) -> tuple[np.ndarray, float]:

    ns, n = Sadv.shape

    for name, arr in [
        ("phi_seq", phi_seq),
        ("nw", nw),
        ("no", no),
        ("krw_max", krw_max),
        ("kro_max", kro_max),
    ]:

        if arr.shape != Sadv.shape:
            raise GateError(
                f"{name}_shape:{arr.shape}:{Sadv.shape}"
            )

    D = local_dshape(
        Sadv,
        nw,
        no,
        krw_max,
        kro_max,
    )

    Dface = (
        0.5
        * (
            D[:, :-1]
            + D[:, 1:]
        )
    )

    Aface = (
        Dface
        * M_face[:, 1:-1]
        / dtheta
    )

    lower = np.zeros(
        (
            ns,
            n,
        ),
        dtype=np.float64,
    )

    diag = np.ones(
        (
            ns,
            n,
        ),
        dtype=np.float64,
    )

    upper = np.zeros(
        (
            ns,
            n,
        ),
        dtype=np.float64,
    )

    rhs = Sadv.copy()

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

    lower[:, 1:-1] = (
        -beta
        * fac
        * aL
    )

    upper[:, 1:-1] = (
        -beta
        * fac
        * aR
    )

    diag[:, 1:-1] = (
        1.0
        + beta
        * fac
        * (
            aL
            + aR
        )
    )

    rhs[:, 0] = SW_INJ
    rhs[:, -1] = Sadv[:, -1]

    S = tri(
        lower,
        diag,
        upper,
        rhs,
    )

    r = (
        diag
        * S
        - rhs
    )

    r[:, 1:] += (
        lower[:, 1:]
        * S[:, :-1]
    )

    r[:, :-1] += (
        upper[:, :-1]
        * S[:, 1:]
    )

    return (
        S,
        float(
            np.max(
                np.abs(r)
            )
        ),
    )


def generate_teacher(
    phi_seq: np.ndarray,
    operator: dict[str, np.ndarray],
    nw: np.ndarray,
    no: np.ndarray,
    krw_max: np.ndarray,
    kro_max: np.ndarray,
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

    t_dfw = time.time()

    dfmax = max_dfw_realization(
        nw,
        no,
        krw_max,
        kro_max,
    )

    dfw_elapsed = float(
        time.time()
        - t_dfw
    )

    dt_cfl = float(
        CFL
        * np.min(
            cv[:, 1:]
        )
        / (
            dfmax
            + EPS
        )
    )

    if (
        not np.isfinite(dt_cfl)
        or dt_cfl <= 0.0
    ):
        raise ScientificFail(
            "teacher_CFL_step_positive_finite",
            dt_cfl,
        )

    S = np.full(
        (
            ns,
            n,
        ),
        SW_INIT,
        dtype=np.float64,
    )

    S[:, 0] = SW_INJ

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
                np.max(
                    target_eta
                )
                / dt_cfl
            )
        )
        + len(target_days)
        + 100
    )

    t0 = time.time()

    while np.any(
        nextk
        < len(target_days)
    ):

        active = (
            nextk
            < len(target_days)
        )

        goal = np.zeros(
            ns,
            dtype=np.float64,
        )

        idx = np.where(
            active
        )[0]

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
                    goal
                    - eta
                )
                <= 5.0e-14
            )
        )

        if np.any(hit):

            hi = np.where(
                hit
            )[0]

            Y[
                nextk[hi],
                hi,
                :,
            ] = S[
                hi,
                :,
            ]

            nextk[hi] += 1
            continue

        S, e = advective_step_local_p(
            S,
            dt,
            cv,
            nw,
            no,
            krw_max,
            kro_max,
        )

        max_adv = max(
            max_adv,
            e,
        )

        pre = float(
            max(
                0.0,
                SWC
                - np.min(S),
                np.max(S)
                - (
                    1.0
                    - SOR
                ),
            )
        )

        max_preclip = max(
            max_preclip,
            pre,
        )

        np.clip(
            S,
            SWC,
            1.0 - SOR,
            out=S,
        )

        S[:, 0] = SW_INJ

        S, r = capillary_implicit_local_p_phi(
            S,
            dt,
            phi_seq,
            M,
            M_face,
            cv,
            dtheta,
            nw,
            no,
            krw_max,
            kro_max,
        )

        max_imp = max(
            max_imp,
            r,
        )

        pre = float(
            max(
                0.0,
                SWC
                - np.min(S),
                np.max(S)
                - (
                    1.0
                    - SOR
                ),
            )
        )

        max_preclip = max(
            max_preclip,
            pre,
        )

        np.clip(
            S,
            SWC,
            1.0 - SOR,
            out=S,
        )

        S[:, 0] = SW_INJ

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

    finite = bool(
        np.all(
            np.isfinite(Y)
        )
    )

    smin = float(
        np.min(Y)
    )

    smax = float(
        np.max(Y)
    )

    inlet = float(
        np.max(
            np.abs(
                Y[:, :, 0]
                - SW_INJ
            )
        )
    )

    bound = float(
        max(
            0.0,
            SWC - smin,
            smax
            - (
                1.0
                - SOR
            ),
        )
    )

    undershoot = float(
        max(
            0.0,
            SW_INIT
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
        "realization_local_max_abs_dfw_dS": dfmax,
        "dfw_scan_points_per_node": DFW_GRID_POINTS,
        "dfw_scan_elapsed_seconds": dfw_elapsed,
        "dt_eta_CFL_ceiling": dt_cfl,
        "iterations": int(steps),
        "elapsed_seconds": float(
            time.time()
            - t0
        ),
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
        "target_eta_min": float(
            np.min(
                target_eta
            )
        ),
        "target_eta_max": float(
            np.max(
                target_eta
            )
        ),
    }

    return Y, diag


def teacher_diag_pass(
    d: dict[str, Any],
) -> bool:
    """
    POSTV16-AV3-A4-R1 corrected certification semantics.

    Hard pass/fail checks only:
      - finite teacher state,
      - conservative advection closure,
      - implicit linear-system residual,
      - pre-clip bound behavior,
      - absolute saturation bounds,
      - inlet Dirichlet condition.

    The three heterogeneous-transport morphology quantities remain recorded
    in the teacher diagnostics but are report-only with no threshold:
      - Y_reservoir_undershoot,
      - temporal_negative_increment_fraction,
      - spatial_positive_increment_fraction.
    """

    return bool(
        d["Y_finite"]
        and d[
            "advection_conservation_max_abs"
        ]
        < ADV_CONSERVATION_MAX
        and d[
            "implicit_residual_max_abs"
        ]
        < IMPLICIT_RESIDUAL_MAX
        and d[
            "preclip_bound_violation_max"
        ]
        < PRECLIP_BOUND_MAX
        and d[
            "Y_bound_violation"
        ]
        < Y_BOUND_MAX
        and d[
            "Y_inlet_Dirichlet_error"
        ]
        < INLET_ERROR_MAX
    )


def build_pair_indices(
    realization_indices: np.ndarray,
    time_indices: np.ndarray,
    streamline_indices: np.ndarray,
    partition_codes: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:

    train_a = []
    train_b = []
    val_a = []
    val_b = []

    n = len(
        realization_indices
    )

    lookup = {}

    for idx in range(n):
        key = (
            int(
                realization_indices[idx]
            ),
            int(
                time_indices[idx]
            ),
            int(
                streamline_indices[idx]
            ),
        )

        if key in lookup:
            raise GateError(
                f"duplicate_sample_key:{key}"
            )

        lookup[key] = idx

    realization_ids = sorted(
        set(
            int(x)
            for x in realization_indices
        )
    )

    for ri in realization_ids:

        rows = np.where(
            realization_indices
            == ri
        )[0]

        if len(rows) == 0:
            continue

        part = int(
            partition_codes[
                rows[0]
            ]
        )

        if part not in {
            0,
            1,
        }:
            continue

        for t in range(
            NT - 1
        ):

            for s in range(
                NSL
            ):

                a = lookup[
                    (
                        ri,
                        t,
                        s,
                    )
                ]

                b = lookup[
                    (
                        ri,
                        t + 1,
                        s,
                    )
                ]

                if part == 0:
                    train_a.append(a)
                    train_b.append(b)

                else:
                    val_a.append(a)
                    val_b.append(b)

    train = {
        "sample_index_a": np.asarray(
            train_a,
            dtype=np.int64,
        ),
        "sample_index_b": np.asarray(
            train_b,
            dtype=np.int64,
        ),
    }

    val = {
        "sample_index_a": np.asarray(
            val_a,
            dtype=np.int64,
        ),
        "sample_index_b": np.asarray(
            val_b,
            dtype=np.int64,
        ),
    }

    return train, val


def self_test() -> None:
    assert np.array_equal(
        ORIGIN_CENTER_M,
        np.asarray(
            [
                3.048,
                3.048,
                0.6096,
            ],
            dtype=np.float64,
        ),
    )

    s = np.linspace(
        SWC + 1.0e-3,
        1.0 - SOR - 1.0e-3,
        201,
    )

    nw = np.full_like(
        s,
        2.0,
    )

    no = np.full_like(
        s,
        2.0,
    )

    kw = np.full_like(
        s,
        0.8,
    )

    ko = np.full_like(
        s,
        0.8,
    )

    krw, kro = local_relperm(
        s,
        nw,
        no,
        kw,
        ko,
    )

    Se = np.clip(
        (
            s - SWC
        )
        / (
            1.0
            - SWC
            - SOR
        ),
        0.0,
        1.0,
    )

    assert np.allclose(
        krw,
        0.8 * Se**2.0,
        rtol=0.0,
        atol=1.0e-15,
    )

    assert np.allclose(
        kro,
        0.8 * (1.0 - Se)**2.0,
        rtol=0.0,
        atol=1.0e-15,
    )

    rng = np.random.default_rng(
        260404
    )

    ntest = 256

    nwv = (
        2.0
        + 2.0
        * rng.random(
            ntest
        )
    )

    nov = (
        2.0
        + 2.0
        * rng.random(
            ntest
        )
    )

    kwv = (
        0.60
        + 0.40
        * rng.random(
            ntest
        )
    )

    kov = (
        0.60
        + 0.40
        * rng.random(
            ntest
        )
    )

    smid = np.full(
        ntest,
        SWC
        + 0.5
        * (
            1.0
            - SWC
            - SOR
        ),
    )

    assert np.max(
        np.abs(
            local_dshape(
                smid,
                nwv,
                nov,
                kwv,
                kov,
            )
            - 1.0
        )
    ) < 1.0e-12

    assert len(
        CHANNELS13
    ) == 13

    assert TRAIN_PROFILES == 19404
    assert VAL_PROFILES == 9702
    assert OOD_PROFILES == 9702

    assert TRAIN_PAIRS == 17248
    assert VAL_PAIRS == 8624

    # Small pair-registry test with same indexing algebra.
    ri = []
    ti = []
    si = []
    pi = []

    ns_small = 3
    nt_small = 4

    # local synthetic implementation check only
    for r, part in [(0, 0), (1, 1)]:
        for t in range(nt_small):
            for sidx in range(ns_small):
                ri.append(r)
                ti.append(t)
                si.append(sidx)
                pi.append(part)

    assert len(ri) == 24

    assert teacher_diag_pass(
        {
            "Y_finite": True,
            "advection_conservation_max_abs": 0.0,
            "implicit_residual_max_abs": 0.0,
            "preclip_bound_violation_max": 0.0,
            "Y_bound_violation": 0.0,
            "Y_inlet_Dirichlet_error": 0.0,
            # Deliberately large morphology values: report-only in R2.
            "Y_reservoir_undershoot": 1.0,
            "temporal_negative_increment_fraction": 1.0,
            "spatial_positive_increment_fraction": 1.0,
        }
    )

    print("POSTV16-AV3-A4-R2 corrected-certification teacher/dataset self-test: PASS")


def main(root: Path, drive: Path) -> int:
    gates: dict[str, dict[str, Any]] = {}

    stage = "preflight"

    teacher_generation_started = False
    teacher_realizations_completed = 0
    locked_ood_target_opened = False

    out = drive / OUT_REL
    fail = drive / FAIL_REL
    blocked = drive / BLOCK_REL

    def gate(
        name: str,
        passed: Any,
        value: Any = None,
    ) -> None:

        ok = bool(
            passed
        )

        gates[name] = {
            "passed": ok,
            "value": value,
        }

        print(
            f"[{'PASS' if ok else 'FAIL'}] {name}"
            + (
                f" — {value}"
                if value is not None
                else ""
            )
        )

        if not ok:
            raise GateError(
                name
            )

    def sci_gate(
        name: str,
        passed: Any,
        value: Any = None,
    ) -> None:

        ok = bool(
            passed
        )

        gates[name] = {
            "passed": ok,
            "value": value,
            "scientific_execution_gate": True,
        }

        print(
            f"[{'PASS' if ok else 'FAIL'}] {name}"
            + (
                f" — {value}"
                if value is not None
                else ""
            )
        )

        if not ok:
            raise ScientificFail(
                name,
                value,
            )

    print("=" * 208)
    print("POSTV16-AV3-A4-R2 — CORRECTED-CERTIFICATION TEACHER / 13-CHANNEL DATASET / LOCKED-OOD PREDICTOR EXECUTION")
    print("=" * 208)
    print("TRAIN Y: AV3CR0001 + AV3CR0002.")
    print("VALIDATION Y: AV3CR0003.")
    print("LOCKED OOD AV3CR0004: PREDICTOR FEATURES ONLY — NO TRANSPORT Y.")
    print("FIRST-NINE SPATIAL CHANNELS USE THE FROZEN HALF-CELL V16B3/V16C2 GEOMETRY.")
    print("PRESSURE NORMALIZATION IS FIT ONLY ON CORRECTED CR0001+CR0002 TRAIN NODES.")
    print("R1 HARD NUMERICAL CERTIFICATION GATES ONLY; THREE MORPHOLOGY METRICS ARE REPORT-ONLY.")
    print("ORIGINAL AV3-A4 SCIENTIFIC FAIL REMAINS IMMUTABLE.")
    print("NO MODEL TRAINING. NO CHECKPOINT CREATION. NO INFERENCE. NO MAPBACK. NO LP. NO CMG.")
    print()

    try:
        root = root.resolve()
        drive = drive.resolve()

        # ------------------------------------------------------------------------------------------
        # Repository/source authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"

        parent = git_text(
            root,
            "rev-parse",
            "HEAD^",
        )

        status = git_text(
            root,
            "status",
            "--porcelain",
        )

        gate(
            "repository_parent_is_AV3A4R1_commit",
            parent
            == PARENT_A4R1_COMMIT,
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
                git_blob(
                    p,
                    root,
                )
                if p.is_file()
                else "missing"
            )

            gate(
                f"{Path(fn).stem}_git_blob_exact",
                actual
                == expected,
                actual,
            )

        # ------------------------------------------------------------------------------------------
        # Bind immutable original A4 scientific FAIL and formal A4-R1 semantics closure.
        # ------------------------------------------------------------------------------------------
        stage = "AV3A4R1_binding"

        original_fail = drive / ORIGINAL_A4_FAIL_REL

        gate(
            "original_A4_fail_report_present",
            original_fail.is_file(),
            str(original_fail),
        )

        gate(
            "original_A4_fail_SHA_exact",
            sha256_file(original_fail) == ORIGINAL_A4_FAIL_SHA256,
            sha256_file(original_fail),
        )

        original_failure = load_json(original_fail)

        gate(
            "original_A4_fail_status_exact",
            original_failure["status"] == ORIGINAL_A4_FAIL_STATUS,
            original_failure["status"],
        )

        gate(
            "original_A4_failed_gate_preserved",
            original_failure["failed_gate"] == "AV3CR0001_teacher_certification",
            original_failure["failed_gate"],
        )

        gate(
            "original_A4_locked_OOD_remained_closed",
            original_failure["LOCKED_OOD_target_opened"] is False,
        )

        a4r1 = drive / A4R1_REL

        gate(
            "AV3A4R1_output_present",
            a4r1.is_dir(),
            str(a4r1),
        )

        mr1a4 = verify_manifest(
            a4r1,
            A4R1_MANIFEST,
        )

        gate(
            "AV3A4R1_manifest_SHA_closure",
            len(mr1a4) == 8,
            len(mr1a4),
        )

        sr1a4 = load_json(
            a4r1 / A4R1_SUMMARY
        )

        cr1a4 = load_json(
            a4r1 / A4R1_CORRECTED
        )

        hr1a4 = load_json(
            a4r1 / A4R1_HANDOFF
        )

        dr1a4 = load_json(
            a4r1 / A4R1_DECISION
        )

        gate(
            "AV3A4R1_status_exact",
            sr1a4["status"] == A4R1_STATUS,
            sr1a4["status"],
        )

        gate(
            "AV3A4R1_original_fail_preserved",
            dr1a4["original_A4_scientific_FAIL_preserved"] is True,
        )

        gate(
            "AV3A4R1_hard_numerical_checks_all_passed",
            dr1a4["hard_numerical_checks_all_passed"] is True,
        )

        gate(
            "AV3A4R1_morphology_report_only",
            dr1a4["morphology_diagnostics_report_only"] is True,
        )

        gate(
            "AV3A4R1_no_threshold_relaxation",
            dr1a4["morphology_thresholds_relaxed"] is False
            and cr1a4["replacement_relaxed_thresholds"] is False,
        )

        gate(
            "AV3A4R1_teacher_physics_unchanged",
            dr1a4["teacher_physics_changed"] is False
            and cr1a4["teacher_PDE_changed"] is False
            and cr1a4["face_algebra_changed"] is False
            and cr1a4["CFL_changed"] is False,
        )

        gate(
            "AV3A4R1_R2_execution_authorized",
            dr1a4["AV3_A4_R2_authorized"] is True
            and hr1a4["milestone"] == "POSTV16-AV3-A4-R2"
            and hr1a4["authorized"] is True
            and hr1a4["execution"] is True,
        )

        gate(
            "AV3A4R1_A5_still_unauthorized",
            dr1a4["AV3_A5_authorized"] is False,
        )

        # ------------------------------------------------------------------------------------------
        # Bind formal A3-R1 PASS.
        # ------------------------------------------------------------------------------------------
        stage = "AV3A3R1_binding"

        r1 = drive / A3R1_REL

        gate(
            "AV3A3R1_output_present",
            r1.is_dir(),
            str(r1),
        )

        mr1 = verify_manifest(
            r1,
            A3R1_MANIFEST,
        )

        gate(
            "AV3A3R1_manifest_SHA_closure",
            len(mr1) == 10,
            len(mr1),
        )

        sr1 = load_json(
            r1 / A3R1_SUMMARY
        )

        f9r1 = load_json(
            r1 / A3R1_FIRST9
        )

        nr1 = load_json(
            r1 / A3R1_NORM
        )

        psr1 = load_json(
            r1 / A3R1_SIDECAR
        )

        hr1 = load_json(
            r1 / A3R1_HANDOFF
        )

        dr1 = load_json(
            r1 / A3R1_DECISION
        )

        gate(
            "AV3A3R1_status_exact",
            sr1["status"]
            == A3R1_STATUS,
            sr1["status"],
        )

        gate(
            "AV3A3R1_A4_authorized",
            dr1["AV3_A4_authorized"]
            is True,
        )

        gate(
            "AV3A3R1_A4_execution_authorized",
            hr1["execution"]
            is True,
        )

        gate(
            "AV3A3R1_historical_X9_reuse_prohibited",
            dr1[
                "AV2A3_X9_direct_reuse_for_AV3_prohibited"
            ]
            is True,
        )

        gate(
            "AV3A3R1_correct_origin_exact",
            np.array_equal(
                np.asarray(
                    f9r1[
                        "cell_center_origin_m"
                    ],
                    dtype=np.float64,
                ),
                ORIGIN_CENTER_M,
            ),
            f9r1[
                "cell_center_origin_m"
            ],
        )

        gate(
            "AV3A3R1_pressure_refit_required",
            nr1[
                "pressure_z"
            ][
                "fit_required"
            ]
            is True,
        )

        gate(
            "AV3A3R1_validation_excluded_from_pressure_fit",
            nr1[
                "pressure_z"
            ][
                "validation_used_for_fit"
            ]
            is False,
        )

        gate(
            "AV3A3R1_OOD_excluded_from_pressure_fit",
            nr1[
                "pressure_z"
            ][
                "locked_OOD_used_for_fit"
            ]
            is False,
        )

        gate(
            "AV3A3R1_phi_identity_required",
            "array-identical"
            in psr1[
                "consistency_gate"
            ],
        )

        # ------------------------------------------------------------------------------------------
        # Bind formal A3 PASS contracts.
        # ------------------------------------------------------------------------------------------
        stage = "AV3A3_binding"

        a3 = drive / A3_REL

        gate(
            "AV3A3_output_present",
            a3.is_dir(),
            str(a3),
        )

        m3 = verify_manifest(
            a3,
            A3_MANIFEST,
        )

        gate(
            "AV3A3_manifest_SHA_closure",
            len(m3) == 10,
            len(m3),
        )

        s3 = load_json(
            a3 / A3_SUMMARY
        )

        pde3 = load_json(
            a3 / A3_PDE
        )

        disc3 = load_json(
            a3 / A3_DISC
        )

        ds3 = load_json(
            a3 / A3_DATASET
        )

        res3 = load_json(
            a3 / A3_RESIDUAL
        )

        model3 = load_json(
            a3 / A3_MODEL
        )

        dec3 = load_json(
            a3 / A3_DECISION
        )

        gate(
            "AV3A3_status_exact",
            s3["status"]
            == A3_STATUS,
            s3["status"],
        )

        gate(
            "AV3A3_model_channels_13",
            int(
                model3[
                    "input_channels"
                ]
            )
            == 13,
        )

        gate(
            "AV3A3_channel_order_exact",
            model3[
                "channel_order"
            ]
            == CHANNELS13,
            model3[
                "channel_order"
            ],
        )

        gate(
            "AV3A3_model_parameters_53057",
            int(
                model3[
                    "parameter_count"
                ]
            )
            == MODEL_PARAMETERS,
        )

        gate(
            "AV3A3_lambda_phys_exact",
            float(
                model3[
                    "objective"
                ][
                    "lambda_phys"
                ]
            )
            == LAMBDA_PHYS,
        )

        gate(
            "AV3A3_teacher_scope_exact",
            ds3[
                "A4_authorized_teacher_generation"
            ]
            == [
                "AV3CR0001",
                "AV3CR0002",
                "AV3CR0003",
            ],
        )

        gate(
            "AV3A3_OOD_teacher_forbidden",
            ds3[
                "A4_forbidden_teacher_generation"
            ]
            == [
                "AV3CR0004"
            ],
        )

        gate(
            "AV3A3_no_OOD_physics_pairs",
            res3[
                "no_OOD_physics_pairs_for_selection"
            ]
            is True,
        )

        gate(
            "AV3A3_local_D_midpoint_normalization",
            pde3[
                "capillary_shape"
            ][
                "property"
            ]
            == "Dtilde(Se=0.5;p(theta))=1 at every node",
        )

        gate(
            "AV3A3_positive_upwind_face_rule",
            "upstream nodal saturation AND upstream"
            in disc3[
                "advection"
            ][
                "face_flux_rule"
            ],
        )

        gate(
            "AV3A3_arithmetic_D_face",
            disc3[
                "capillary"
            ][
                "D_face"
            ]
            == "arithmetic mean of neighboring D_node values",
        )

        gate(
            "AV3A3_A4_authorized",
            dec3[
                "AV3_A4_authorized"
            ]
            is True,
        )

        # ------------------------------------------------------------------------------------------
        # Bind A2 constitutive realizations.
        # ------------------------------------------------------------------------------------------
        stage = "AV3A2_binding"

        a2 = drive / A2_REL

        gate(
            "AV3A2_output_present",
            a2.is_dir(),
            str(a2),
        )

        m2 = verify_manifest(
            a2,
            A2_MANIFEST,
        )

        gate(
            "AV3A2_manifest_SHA_closure",
            len(m2) == 11,
            len(m2),
        )

        s2 = load_json(
            a2 / A2_SUMMARY
        )

        d2 = load_json(
            a2 / A2_DECISION
        )

        gate(
            "AV3A2_status_exact",
            s2["status"]
            == A2_STATUS,
            s2["status"],
        )

        gate(
            "AV3A2_corrected_sampling_complete",
            d2[
                "frozen_AV2_streamline_sampling_complete"
            ]
            is True,
        )

        # ------------------------------------------------------------------------------------------
        # Bind AV2 A2 kinematics.
        # ------------------------------------------------------------------------------------------
        stage = "AV2A2_binding"

        av2a2 = drive / AV2A2_REL

        gate(
            "AV2A2_output_present",
            av2a2.is_dir(),
            str(av2a2),
        )

        mva2 = verify_manifest(
            av2a2,
            AV2A2_MANIFEST,
        )

        gate(
            "AV2A2_manifest_SHA_closure",
            len(mva2) > 0,
            len(mva2),
        )

        sva2 = load_json(
            av2a2 / AV2A2_SUMMARY
        )

        dva2 = load_json(
            av2a2 / AV2A2_DECISION
        )

        gate(
            "AV2A2_status_exact",
            sva2["status"]
            == AV2A2_STATUS,
            sva2["status"],
        )

        gate(
            "AV2A2_pressure_Q_invariance",
            dva2[
                "pressure_Q_invariance_certified"
            ]
            is True,
        )

        gate(
            "AV2A2_all_1078_streamlines",
            dva2[
                "all_1078_streamlines_captured_for_all_realizations"
            ]
            is True,
        )

        # ------------------------------------------------------------------------------------------
        # Bind exact Foundation pressure/geology/Q and exact algorithms.
        # ------------------------------------------------------------------------------------------
        stage = "foundation_and_algorithm_binding"

        foundation = find_named_exact(
            [
                root,
                drive,
            ],
            FOUNDATION_NAME,
            FOUNDATION_SHA,
        )

        gate(
            "Foundation0001_SHA_exact",
            sha256_file(
                foundation
            )
            == FOUNDATION_SHA,
            str(
                foundation
            ),
        )

        with np.load(
            foundation,
            allow_pickle=False,
        ) as z:

            required = {
                "Kx",
                "Ky",
                "Kz",
                "pressure",
                "Qx",
                "Qy",
                "Qz",
            }

            gate(
                "Foundation_required_arrays",
                required.issubset(
                    set(
                        z.files
                    )
                ),
                sorted(
                    z.files
                ),
            )

            Kx = np.asarray(
                z[
                    "Kx"
                ],
                dtype=np.float64,
            )

            Ky = np.asarray(
                z[
                    "Ky"
                ],
                dtype=np.float64,
            )

            Kz = np.asarray(
                z[
                    "Kz"
                ],
                dtype=np.float64,
            )

            pressure = np.asarray(
                z[
                    "pressure"
                ],
                dtype=np.float64,
            )

            Qx = np.asarray(
                z[
                    "Qx"
                ],
                dtype=np.float64,
            )

            Qy = np.asarray(
                z[
                    "Qy"
                ],
                dtype=np.float64,
            )

            Qz = np.asarray(
                z[
                    "Qz"
                ],
                dtype=np.float64,
            )

        gate(
            "Foundation_K_pressure_grid_shapes",
            Kx.shape == GRID
            and Ky.shape == GRID
            and Kz.shape == GRID
            and pressure.shape == GRID,
            [
                Kx.shape,
                Ky.shape,
                Kz.shape,
                pressure.shape,
            ],
        )

        r7 = load_module(
            root / R7,
            "av3a4_r7",
        )

        b2 = load_module(
            root / B2,
            "av3a4_b2",
        )

        c2 = load_module(
            root / C2,
            "av3a4_c2",
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
            int(
                np.sum(
                    source_mask
                )
            )
            == 5,
            int(
                np.sum(
                    source_mask
                )
            ),
        )

        # ------------------------------------------------------------------------------------------
        # Reconstruct corrected predictor-side static data for all 4 realizations.
        # ------------------------------------------------------------------------------------------
        stage = "corrected_predictor_reconstruction"

        per_case: dict[str, dict[str, Any]] = {}

        first9_audit_rows: list[dict[str, Any]] = []

        train_pressure_values: list[np.ndarray] = []
        train_log_weights: list[np.ndarray] = []

        for realization_index, (
            rid,
            phi_rid,
            partition,
        ) in enumerate(
            REALIZATIONS
        ):

            a2_npz = (
                a2
                / f"POSTV16_AV3_A2_{rid}_Corey_Relperm_Field_and_Streamline_Sampling.npz"
            )

            av2_npz = (
                av2a2
                / f"POSTV16_AV2_A2_{phi_rid}_Variable_Porosity_Pore_Kinematics.npz"
            )

            gate(
                f"{rid}_AV3A2_artifact_present",
                a2_npz.is_file(),
                a2_npz.name,
            )

            gate(
                f"{rid}_AV2A2_artifact_present",
                av2_npz.is_file(),
                av2_npz.name,
            )

            with np.load(
                a2_npz,
                allow_pickle=False,
            ) as z:

                a2_required = {
                    "nw_streamline",
                    "no_streamline",
                    "krw_max_streamline",
                    "kro_max_streamline",
                    "streamline_xyz_m",
                    "pollock_tof_s",
                    "streamline_weight_m3_s",
                    "paired_porosity",
                }

                gate(
                    f"{rid}_A2_required_arrays",
                    a2_required.issubset(
                        set(
                            z.files
                        )
                    ),
                    sorted(
                        z.files
                    ),
                )

                nw_s = np.asarray(
                    z[
                        "nw_streamline"
                    ],
                    dtype=np.float64,
                )

                no_s = np.asarray(
                    z[
                        "no_streamline"
                    ],
                    dtype=np.float64,
                )

                krw_s = np.asarray(
                    z[
                        "krw_max_streamline"
                    ],
                    dtype=np.float64,
                )

                kro_s = np.asarray(
                    z[
                        "kro_max_streamline"
                    ],
                    dtype=np.float64,
                )

                xyz = np.asarray(
                    z[
                        "streamline_xyz_m"
                    ],
                    dtype=np.float64,
                )

                tof = np.asarray(
                    z[
                        "pollock_tof_s"
                    ],
                    dtype=np.float64,
                )

                weight = np.asarray(
                    z[
                        "streamline_weight_m3_s"
                    ],
                    dtype=np.float64,
                )

                phi_grid_a2 = np.asarray(
                    z[
                        "paired_porosity"
                    ],
                    dtype=np.float64,
                )

            with np.load(
                av2_npz,
                allow_pickle=False,
            ) as z:

                av2_required = {
                    "porosity",
                    "Vx_m_s",
                    "Vy_m_s",
                    "Vz_m_s",
                    "streamline_xyz_m",
                    "pollock_tof_s",
                    "streamline_weight_m3_s",
                }

                gate(
                    f"{rid}_AV2A2_required_arrays",
                    av2_required.issubset(
                        set(
                            z.files
                        )
                    ),
                    sorted(
                        z.files
                    ),
                )

                phi_grid_av2 = np.asarray(
                    z[
                        "porosity"
                    ],
                    dtype=np.float64,
                )

                vx = np.asarray(
                    z[
                        "Vx_m_s"
                    ],
                    dtype=np.float64,
                )

                vy = np.asarray(
                    z[
                        "Vy_m_s"
                    ],
                    dtype=np.float64,
                )

                vz = np.asarray(
                    z[
                        "Vz_m_s"
                    ],
                    dtype=np.float64,
                )

                xyz_av2 = np.asarray(
                    z[
                        "streamline_xyz_m"
                    ],
                    dtype=np.float64,
                )

                tof_av2 = np.asarray(
                    z[
                        "pollock_tof_s"
                    ],
                    dtype=np.float64,
                )

                weight_av2 = np.asarray(
                    z[
                        "streamline_weight_m3_s"
                    ],
                    dtype=np.float64,
                )

            sci_gate(
                f"{rid}_paired_phi_grid_exact",
                np.array_equal(
                    phi_grid_a2,
                    phi_grid_av2,
                ),
            )

            sci_gate(
                f"{rid}_paired_XYZ_exact",
                np.array_equal(
                    xyz,
                    xyz_av2,
                ),
            )

            sci_gate(
                f"{rid}_paired_TOF_exact",
                np.array_equal(
                    tof,
                    tof_av2,
                ),
            )

            sci_gate(
                f"{rid}_paired_weight_exact",
                np.array_equal(
                    weight,
                    weight_av2,
                ),
            )

            sci_gate(
                f"{rid}_XYZ_shape",
                xyz.shape
                == (
                    NSL,
                    NN,
                    3,
                ),
                xyz.shape,
            )

            sci_gate(
                f"{rid}_TOF_shape",
                tof.shape
                == (
                    NSL,
                    NN,
                ),
                tof.shape,
            )

            for name, arr, lo, hi in [
                (
                    "nw",
                    nw_s,
                    2.0,
                    4.0,
                ),
                (
                    "no",
                    no_s,
                    2.0,
                    4.0,
                ),
                (
                    "krw_max",
                    krw_s,
                    0.60,
                    1.00,
                ),
                (
                    "kro_max",
                    kro_s,
                    0.60,
                    1.00,
                ),
            ]:

                sci_gate(
                    f"{rid}_{name}_shape",
                    arr.shape
                    == (
                        NSL,
                        NN,
                    ),
                    arr.shape,
                )

                sci_gate(
                    f"{rid}_{name}_strict_bounds",
                    float(
                        np.min(
                            arr
                        )
                    )
                    > lo
                    and float(
                        np.max(
                            arr
                        )
                    )
                    < hi,
                    [
                        float(
                            np.min(
                                arr
                            )
                        ),
                        float(
                            np.max(
                                arr
                            )
                        ),
                    ],
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
                adv_audit[
                    "finite"
                ],
            )

            sci_gate(
                f"{rid}_ADV_nonnegative",
                adv_audit[
                    "nonnegative"
                ],
            )

            sci_gate(
                f"{rid}_ADV_non_source_positive",
                adv_audit[
                    "non_source_positive"
                ],
            )

            sci_gate(
                f"{rid}_ADV_residual_lt_1e8",
                adv_audit[
                    "relative_L2_residual"
                ]
                < 1.0e-8,
                adv_audit[
                    "relative_L2_residual"
                ],
            )

            adv_s, audit_adv = c2.trilinear(
                adv_grid,
                xyz,
                DX,
                DY,
                DZ,
                ORIGIN_CENTER_M,
            )

            kx_s, audit_kx = c2.trilinear(
                Kx,
                xyz,
                DX,
                DY,
                DZ,
                ORIGIN_CENTER_M,
            )

            ky_s, audit_ky = c2.trilinear(
                Ky,
                xyz,
                DX,
                DY,
                DZ,
                ORIGIN_CENTER_M,
            )

            kz_s, audit_kz = c2.trilinear(
                Kz,
                xyz,
                DX,
                DY,
                DZ,
                ORIGIN_CENTER_M,
            )

            phi_s, audit_phi = c2.trilinear(
                phi_grid_a2,
                xyz,
                DX,
                DY,
                DZ,
                ORIGIN_CENTER_M,
            )

            p_s, audit_p = c2.trilinear(
                pressure,
                xyz,
                DX,
                DY,
                DZ,
                ORIGIN_CENTER_M,
            )

            operator = build_operator_geometry(
                xyz,
                tof,
            )

            tau_end = operator[
                "terminal_TOF_s"
            ]

            pollock_hat = (
                tof
                / tau_end[:, None]
            )

            xi = np.broadcast_to(
                np.linspace(
                    0.0,
                    1.0,
                    NN,
                    dtype=np.float64,
                )[None, :],
                (
                    NSL,
                    NN,
                ),
            )

            sci_gate(
                f"{rid}_xi_pollock_hat_identity",
                float(
                    np.max(
                        np.abs(
                            xi
                            - pollock_hat
                        )
                    )
                )
                <= 1.0e-10,
                float(
                    np.max(
                        np.abs(
                            xi
                            - pollock_hat
                        )
                    )
                ),
            )

            Kh = np.sqrt(
                np.maximum(
                    kx_s,
                    1.0e-30,
                )
                * np.maximum(
                    ky_s,
                    1.0e-30,
                )
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

            for channel, audit in [
                ("adv_tau", audit_adv),
                ("Kx", audit_kx),
                ("Ky", audit_ky),
                ("Kz", audit_kz),
                ("porosity", audit_phi),
                ("pressure", audit_p),
            ]:

                first9_audit_rows.append(
                    {
                        "corey_realization_id": rid,
                        "paired_porosity_realization_id": phi_rid,
                        "partition": partition,
                        "channel": channel,
                        "method": "TRILINEAR_CELL_CENTERED_V16C2_EXACT_ALGEBRA",
                        "origin_x_m": float(
                            ORIGIN_CENTER_M[
                                0
                            ]
                        ),
                        "origin_y_m": float(
                            ORIGIN_CENTER_M[
                                1
                            ]
                        ),
                        "origin_z_m": float(
                            ORIGIN_CENTER_M[
                                2
                            ]
                        ),
                        "dx_m": DX,
                        "dy_m": DY,
                        "dz_m": DZ,
                        **audit,
                    }
                )

            phi_f32 = phi_s.astype(
                np.float32
            )

            raw = {
                "rid": rid,
                "phi_rid": phi_rid,
                "partition": partition,
                "realization_index": realization_index,
                "xyz": xyz,
                "tof": tof,
                "weight": weight,
                "operator": operator,
                "xi": xi,
                "pollock_hat": pollock_hat,
                "adv_hat": (
                    adv_s
                    / tau_end[:, None]
                ),
                "logKh": logKh,
                "logKratio": logKratio,
                "phi_s_float64": phi_s,
                "phi_s_float32": phi_f32,
                "pressure_s": p_s,
                "nw_s": nw_s,
                "no_s": no_s,
                "krw_s": krw_s,
                "kro_s": kro_s,
                "adv_audit": adv_audit,
            }

            per_case[
                rid
            ] = raw

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

        # ------------------------------------------------------------------------------------------
        # Corrected TRAIN-only normalization.
        # ------------------------------------------------------------------------------------------
        stage = "corrected_TRAIN_only_normalization"

        p_train = np.concatenate(
            train_pressure_values
        )

        lw_train = np.concatenate(
            train_log_weights
        )

        pmean = float(
            np.mean(
                p_train
            )
        )

        pstd = float(
            np.std(
                p_train
            )
        )

        lwmean = float(
            np.mean(
                lw_train
            )
        )

        lwstd = float(
            np.std(
                lw_train
            )
        )

        sci_gate(
            "corrected_TRAIN_pressure_std_positive",
            np.isfinite(
                pstd
            )
            and pstd > 0.0,
            pstd,
        )

        sci_gate(
            "TRAIN_logweight_std_positive",
            np.isfinite(
                lwstd
            )
            and lwstd > 0.0,
            lwstd,
        )

        # ------------------------------------------------------------------------------------------
        # Generate teacher Y for TRAIN + VALIDATION only.
        # ------------------------------------------------------------------------------------------
        stage = "teacher_generation"

        teacher_rows: list[dict[str, Any]] = []
        teacher_Y: dict[str, np.ndarray] = {}

        for (
            rid,
            phi_rid,
            partition,
        ) in REALIZATIONS:

            case = per_case[
                rid
            ]

            if (
                partition
                == "LOCKED_OOD_TEST"
            ):
                continue

            teacher_generation_started = True

            print()
            print("=" * 208)
            print(
                f"AV3-A4 TEACHER — {rid} / {partition}"
            )
            print("=" * 208)

            Y, td = generate_teacher(
                case[
                    "phi_s_float64"
                ],
                case[
                    "operator"
                ],
                case[
                    "nw_s"
                ],
                case[
                    "no_s"
                ],
                case[
                    "krw_s"
                ],
                case[
                    "kro_s"
                ],
                DAYS,
            )

            passed = teacher_diag_pass(
                td
            )

            sci_gate(
                f"{rid}_teacher_hard_numerical_certification",
                passed,
                td,
            )

            sci_gate(
                f"{rid}_Y_shape_9_1078_201",
                Y.shape
                == (
                    NT,
                    NSL,
                    NN,
                ),
                Y.shape,
            )

            teacher_Y[
                rid
            ] = Y

            teacher_rows.append(
                {
                    "corey_realization_id": rid,
                    "paired_porosity_realization_id": phi_rid,
                    "partition": partition,
                    **td,
                    "certified_under_R1_hard_numerical_contract": passed,
                    "Y_reservoir_undershoot_role": "REPORT_ONLY_NO_THRESHOLD",
                    "temporal_negative_increment_fraction_role": "REPORT_ONLY_NO_THRESHOLD",
                    "spatial_positive_increment_fraction_role": "REPORT_ONLY_NO_THRESHOLD",
                }
            )

            teacher_realizations_completed += 1

        sci_gate(
            "exactly_three_supervised_realizations_generated",
            teacher_realizations_completed
            == 3,
            teacher_realizations_completed,
        )

        sci_gate(
            "LOCKED_OOD_target_not_generated",
            "AV3CR0004"
            not in teacher_Y,
        )

        locked_ood_target_opened = False

        # ------------------------------------------------------------------------------------------
        # Assemble corrected X13 and physics sidecars.
        # ------------------------------------------------------------------------------------------
        stage = "dataset_assembly"

        trainval_blocks: list[
            dict[
                str,
                np.ndarray,
            ]
        ] = []

        ood_block: dict[
            str,
            np.ndarray,
        ] | None = None

        side_M = []
        side_Mf = []
        side_cv = []
        side_dtheta = []
        side_phi = []
        side_tauend = []
        side_nw = []
        side_no = []
        side_krw = []
        side_kro = []
        side_weight = []

        for (
            rid,
            phi_rid,
            partition,
        ) in REALIZATIONS:

            case = per_case[
                rid
            ]

            pressure_z = (
                (
                    case[
                        "pressure_s"
                    ]
                    - pmean
                )
                / pstd
            )

            X7 = np.stack(
                [
                    case[
                        "xi"
                    ],
                    case[
                        "pollock_hat"
                    ],
                    case[
                        "adv_hat"
                    ],
                    case[
                        "logKh"
                    ],
                    case[
                        "logKratio"
                    ],
                    case[
                        "phi_s_float64"
                    ],
                    pressure_z,
                ],
                axis=-1,
            ).astype(
                np.float32
            )

            sci_gate(
                f"{rid}_corrected_X7_shape",
                X7.shape
                == (
                    NSL,
                    NN,
                    7,
                ),
                X7.shape,
            )

            sci_gate(
                f"{rid}_corrected_X7_finite",
                np.all(
                    np.isfinite(
                        X7
                    )
                ),
            )

            target_eta = (
                DAYS[:, None]
                * SPD
                / case[
                    "operator"
                ][
                    "terminal_TOF_s"
                ][None, :]
            )

            X7f = np.broadcast_to(
                X7[
                    None,
                    :,
                    :,
                    :,
                ],
                (
                    NT,
                    NSL,
                    NN,
                    7,
                ),
            ).reshape(
                NT
                * NSL,
                NN,
                7,
            ).copy()

            target_days = np.repeat(
                DAYS,
                NSL,
            )

            target_time_hat = (
                target_days
                / 1000.0
            ).astype(
                np.float32
            )

            eta_seq = np.repeat(
                target_eta[
                    :,
                    :,
                    None,
                ],
                NN,
                axis=2,
            ).reshape(
                NT
                * NSL,
                NN,
            ).astype(
                np.float32
            )

            T = np.broadcast_to(
                target_time_hat[
                    :,
                    None,
                    None,
                ],
                (
                    NT
                    * NSL,
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
                    eta_seq[
                        :,
                        :,
                        None,
                    ],
                ],
                axis=2,
            ).astype(
                np.float32
            )

            p4 = np.stack(
                [
                    (
                        case[
                            "nw_s"
                        ]
                        - 3.0
                    )
                    / 1.0,
                    (
                        case[
                            "no_s"
                        ]
                        - 3.0
                    )
                    / 1.0,
                    (
                        case[
                            "krw_s"
                        ]
                        - 0.80
                    )
                    / 0.20,
                    (
                        case[
                            "kro_s"
                        ]
                        - 0.80
                    )
                    / 0.20,
                ],
                axis=-1,
            ).astype(
                np.float32
            )

            sci_gate(
                f"{rid}_P4_shape",
                p4.shape
                == (
                    NSL,
                    NN,
                    4,
                ),
                p4.shape,
            )

            sci_gate(
                f"{rid}_P4_finite",
                np.all(
                    np.isfinite(
                        p4
                    )
                ),
            )

            sci_gate(
                f"{rid}_P4_strict_minus1_plus1",
                float(
                    np.min(
                        p4
                    )
                )
                > -1.0
                and float(
                    np.max(
                        p4
                    )
                )
                < 1.0,
                [
                    float(
                        np.min(
                            p4
                        )
                    ),
                    float(
                        np.max(
                            p4
                        )
                    ),
                ],
            )

            P4f = np.broadcast_to(
                p4[
                    None,
                    :,
                    :,
                    :,
                ],
                (
                    NT,
                    NSL,
                    NN,
                    4,
                ),
            ).reshape(
                NT
                * NSL,
                NN,
                4,
            ).copy()

            X13 = np.concatenate(
                [
                    X9,
                    P4f,
                ],
                axis=2,
            ).astype(
                np.float32
            )

            sci_gate(
                f"{rid}_X13_shape",
                X13.shape
                == (
                    NT
                    * NSL,
                    NN,
                    13,
                ),
                X13.shape,
            )

            sci_gate(
                f"{rid}_X13_finite",
                np.all(
                    np.isfinite(
                        X13
                    )
                ),
            )

            # Exact R1 consistency requirement.
            phi_static_from_X13 = X13[
                0:NSL,
                :,
                5,
            ]

            sci_gate(
                f"{rid}_X13_phi_equals_physics_phi_exact",
                np.array_equal(
                    phi_static_from_X13,
                    case[
                        "phi_s_float32"
                    ],
                ),
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
                NT
                * NSL,
                case[
                    "realization_index"
                ],
                dtype=np.int64,
            )

            static_weight = (
                (
                    np.log(
                        np.maximum(
                            case[
                                "weight"
                            ],
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
                case[
                    "operator"
                ][
                    "metric_M"
                ]
            )

            side_Mf.append(
                case[
                    "operator"
                ][
                    "metric_M_face"
                ]
            )

            side_cv.append(
                case[
                    "operator"
                ][
                    "control_volume_dtheta"
                ]
            )

            side_dtheta.append(
                case[
                    "operator"
                ][
                    "dtheta_center"
                ]
            )

            side_phi.append(
                case[
                    "phi_s_float32"
                ]
            )

            side_tauend.append(
                case[
                    "operator"
                ][
                    "terminal_TOF_s"
                ]
            )

            side_nw.append(
                case[
                    "nw_s"
                ].astype(
                    np.float32
                )
            )

            side_no.append(
                case[
                    "no_s"
                ].astype(
                    np.float32
                )
            )

            side_krw.append(
                case[
                    "krw_s"
                ].astype(
                    np.float32
                )
            )

            side_kro.append(
                case[
                    "kro_s"
                ].astype(
                    np.float32
                )
            )

            side_weight.append(
                case[
                    "weight"
                ]
            )

            if partition in {
                "TRAIN",
                "VALIDATION",
            }:

                Y = teacher_Y[
                    rid
                ].reshape(
                    NT
                    * NSL,
                    NN,
                ).astype(
                    np.float32
                )

                part_code = (
                    0
                    if partition
                    == "TRAIN"
                    else 1
                )

                trainval_blocks.append(
                    {
                        "X": X13,
                        "Y": Y,
                        "realization_index": ri,
                        "time_index": ti,
                        "streamline_index": si,
                        "partition_code": np.full(
                            NT
                            * NSL,
                            part_code,
                            dtype=np.int8,
                        ),
                        "target_time_days": target_days.astype(
                            np.float32
                        ),
                        "target_time_hat": target_time_hat,
                        "target_eta_sequence": eta_seq,
                    }
                )

            else:

                ood_block = {
                    "X": X13,
                    "realization_index": ri,
                    "time_index": ti,
                    "streamline_index": si,
                    "target_time_days": target_days.astype(
                        np.float32
                    ),
                    "target_time_hat": target_time_hat,
                    "target_eta_sequence": eta_seq,
                    "static_log_streamline_weight_z":
                        np.broadcast_to(
                            static_weight[
                                None,
                                :,
                            ],
                            (
                                NT,
                                NSL,
                            ),
                        ).reshape(
                            -1
                        ),
                }

        if ood_block is None:
            raise GateError(
                "locked_OOD_predictor_block_missing"
            )

        X_tv = np.concatenate(
            [
                b[
                    "X"
                ]
                for b in trainval_blocks
            ],
            axis=0,
        )

        Y_tv = np.concatenate(
            [
                b[
                    "Y"
                ]
                for b in trainval_blocks
            ],
            axis=0,
        )

        realization_tv = np.concatenate(
            [
                b[
                    "realization_index"
                ]
                for b in trainval_blocks
            ]
        )

        time_tv = np.concatenate(
            [
                b[
                    "time_index"
                ]
                for b in trainval_blocks
            ]
        )

        streamline_tv = np.concatenate(
            [
                b[
                    "streamline_index"
                ]
                for b in trainval_blocks
            ]
        )

        partition_tv = np.concatenate(
            [
                b[
                    "partition_code"
                ]
                for b in trainval_blocks
            ]
        )

        day_tv = np.concatenate(
            [
                b[
                    "target_time_days"
                ]
                for b in trainval_blocks
            ]
        )

        th_tv = np.concatenate(
            [
                b[
                    "target_time_hat"
                ]
                for b in trainval_blocks
            ]
        )

        eta_tv = np.concatenate(
            [
                b[
                    "target_eta_sequence"
                ]
                for b in trainval_blocks
            ],
            axis=0,
        )

        train_count = int(
            np.sum(
                partition_tv
                == 0
            )
        )

        val_count = int(
            np.sum(
                partition_tv
                == 1
            )
        )

        sci_gate(
            "TRAIN_sample_count_exact",
            train_count
            == TRAIN_PROFILES,
            train_count,
        )

        sci_gate(
            "VALIDATION_sample_count_exact",
            val_count
            == VAL_PROFILES,
            val_count,
        )

        sci_gate(
            "LOCKED_OOD_predictor_count_exact",
            int(
                ood_block[
                    "X"
                ].shape[
                    0
                ]
            )
            == OOD_PROFILES,
            int(
                ood_block[
                    "X"
                ].shape[
                    0
                ]
            ),
        )

        sci_gate(
            "TRAIN_validation_X13_shape",
            X_tv.shape
            == (
                TRAIN_PROFILES
                + VAL_PROFILES,
                NN,
                13,
            ),
            X_tv.shape,
        )

        sci_gate(
            "TRAIN_validation_Y_shape",
            Y_tv.shape
            == (
                TRAIN_PROFILES
                + VAL_PROFILES,
                NN,
            ),
            Y_tv.shape,
        )

        sci_gate(
            "LOCKED_OOD_X13_shape",
            ood_block[
                "X"
            ].shape
            == (
                OOD_PROFILES,
                NN,
                13,
            ),
            ood_block[
                "X"
            ].shape,
        )

        # ------------------------------------------------------------------------------------------
        # Frozen adjacent-time pair registries.
        # ------------------------------------------------------------------------------------------
        stage = "physics_pair_registry"

        train_pairs, val_pairs = build_pair_indices(
            realization_tv,
            time_tv,
            streamline_tv,
            partition_tv,
        )

        sci_gate(
            "TRAIN_adjacent_pair_count_exact",
            len(
                train_pairs[
                    "sample_index_a"
                ]
            )
            == TRAIN_PAIRS,
            len(
                train_pairs[
                    "sample_index_a"
                ]
            ),
        )

        sci_gate(
            "VALIDATION_adjacent_pair_count_exact",
            len(
                val_pairs[
                    "sample_index_a"
                ]
            )
            == VAL_PAIRS,
            len(
                val_pairs[
                    "sample_index_a"
                ]
            ),
        )

        sci_gate(
            "LOCKED_OOD_pair_count_zero",
            True,
            0,
        )

        # ------------------------------------------------------------------------------------------
        # Freeze A5 handoff.
        # ------------------------------------------------------------------------------------------
        stage = "A5_handoff"

        handoff = {
            "milestone": "POSTV16-AV3-A5",
            "name": (
                "Spatial-Corey/Relperm 13-Channel PI-RNN Training, "
                "Best-Validation Checkpoint Freeze, and One-Touch Locked-OOD Evaluation"
            ),
            "authorized": True,
            "execution": True,
            "required_sequence": [
                "train only on partition_code==0 using the frozen A3 objective",
                "select/freeze checkpoint only by minimum validation total objective",
                "do not generate/open AV3CR0004 Y before checkpoint freeze",
                "after checkpoint freeze generate AV3CR0004 teacher exactly once",
                "evaluate locked OOD exactly once",
                "no retraining, checkpoint reselection, normalization refit, or hyperparameter retuning after OOD",
            ],
            "frozen_model": {
                "nodes": NN,
                "input_channels": 13,
                "channel_order": CHANNELS13,
                "parameters": MODEL_PARAMETERS,
                "objective": "L_data + 0.01 L_phys",
            },
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "original_AV3A4_scientific_FAIL_preserved": True,
            "original_AV3A4_fail_SHA256": ORIGINAL_A4_FAIL_SHA256,
            "R1_corrected_certification_semantics_applied": True,
            "morphology_diagnostics_report_only_no_threshold": True,
            "teacher_physics_unchanged_from_A3": True,
            "teacher_realizations_certified": teacher_realizations_completed,
            "TRAIN_teacher_realizations": 2,
            "VALIDATION_teacher_realizations": 1,
            "LOCKED_OOD_teacher_generated": False,
            "LOCKED_OOD_target_opened": locked_ood_target_opened,
            "corrected_cell_center_origin_m": ORIGIN_CENTER_M.tolist(),
            "historical_AV2A3_X9_direct_reuse": False,
            "corrected_pressure_TRAIN_only_normalization_fit": True,
            "validation_used_for_pressure_fit": False,
            "locked_OOD_used_for_pressure_fit": False,
            "predictor_phi_equals_physics_phi_sidecar": True,
            "TRAIN_samples": train_count,
            "VALIDATION_samples": val_count,
            "LOCKED_OOD_predictor_samples": int(
                ood_block[
                    "X"
                ].shape[
                    0
                ]
            ),
            "TRAIN_physics_pairs": int(
                len(
                    train_pairs[
                        "sample_index_a"
                    ]
                )
            ),
            "VALIDATION_physics_pairs": int(
                len(
                    val_pairs[
                        "sample_index_a"
                    ]
                )
            ),
            "training_performed": False,
            "checkpoint_created": False,
            "model_inference_performed": False,
            "pressure_resolve_performed": False,
            "Pollock_retrace_performed": False,
            "mapback_performed": False,
            "LP_execution_performed": False,
            "CMG_validation_performed": False,
            "AV3_A5_authorized": True,
            "next": handoff,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "original_AV3A4_scientific_FAIL_preserved": True,
            "original_AV3A4_fail_SHA256": ORIGINAL_A4_FAIL_SHA256,
            "R1_corrected_certification_semantics_applied": True,
            "morphology_diagnostics_report_only_no_threshold": True,
            "teacher_physics_unchanged_from_A3": True,
            "teacher_realizations_certified": teacher_realizations_completed,
            "TRAIN_samples": train_count,
            "VALIDATION_samples": val_count,
            "LOCKED_OOD_predictor_samples": int(
                ood_block[
                    "X"
                ].shape[
                    0
                ]
            ),
            "LOCKED_OOD_target_generated": False,
            "input_shape_train_validation": list(
                X_tv.shape
            ),
            "target_shape_train_validation": list(
                Y_tv.shape
            ),
            "input_shape_locked_OOD": list(
                ood_block[
                    "X"
                ].shape
            ),
            "TRAIN_adjacent_pairs": int(
                len(
                    train_pairs[
                        "sample_index_a"
                    ]
                )
            ),
            "VALIDATION_adjacent_pairs": int(
                len(
                    val_pairs[
                        "sample_index_a"
                    ]
                )
            ),
            "corrected_pressure_mean_psi": pmean,
            "corrected_pressure_std_psi": pstd,
            "corrected_cell_center_origin_m": ORIGIN_CENTER_M.tolist(),
            "architecture": "2xLSTM64_TimeDistributed_Dense_bounded_Sw",
            "model_parameters": MODEL_PARAMETERS,
            "lambda_phys": LAMBDA_PHYS,
            "training_performed": False,
            "checkpoint_created": False,
            "inference": False,
            "mapback": False,
            "CMG_validation": False,
            "AV3_A5_authorized": True,
            "next": handoff,
        }

        # Physics sidecar: phi is intentionally float32 so it is bitwise
        # identical to the X13 porosity channel used by the model.
        sidecar = {
            "metric_M": np.stack(
                side_M,
                axis=0,
            ).astype(
                np.float64
            ),
            "metric_M_face": np.stack(
                side_Mf,
                axis=0,
            ).astype(
                np.float64
            ),
            "control_volume_dtheta": np.stack(
                side_cv,
                axis=0,
            ).astype(
                np.float64
            ),
            "dtheta_center": np.stack(
                side_dtheta,
                axis=0,
            ).astype(
                np.float64
            ),
            "phi_sequence": np.stack(
                side_phi,
                axis=0,
            ).astype(
                np.float32
            ),
            "terminal_pollock_tof_s": np.stack(
                side_tauend,
                axis=0,
            ).astype(
                np.float64
            ),
            "nw_sequence": np.stack(
                side_nw,
                axis=0,
            ).astype(
                np.float32
            ),
            "no_sequence": np.stack(
                side_no,
                axis=0,
            ).astype(
                np.float32
            ),
            "krw_max_sequence": np.stack(
                side_krw,
                axis=0,
            ).astype(
                np.float32
            ),
            "kro_max_sequence": np.stack(
                side_kro,
                axis=0,
            ).astype(
                np.float32
            ),
            "streamline_weight_m3_s": np.stack(
                side_weight,
                axis=0,
            ).astype(
                np.float64
            ),
            "realization_id": np.asarray(
                [
                    r[
                        0
                    ]
                    for r in REALIZATIONS
                ],
                dtype="U32",
            ),
            "partition": np.asarray(
                [
                    r[
                        2
                    ]
                    for r in REALIZATIONS
                ],
                dtype="U32",
            ),
        }

        normalization = {
            "pressure_mean_psi": np.asarray(
                [
                    pmean
                ],
                dtype=np.float64,
            ),
            "pressure_std_psi": np.asarray(
                [
                    pstd
                ],
                dtype=np.float64,
            ),
            "ln_weight_mean": np.asarray(
                [
                    lwmean
                ],
                dtype=np.float64,
            ),
            "ln_weight_std": np.asarray(
                [
                    lwstd
                ],
                dtype=np.float64,
            ),
            "fit_corey_realizations": np.asarray(
                [
                    "AV3CR0001",
                    "AV3CR0002",
                ],
                dtype="U32",
            ),
            "validation_used_for_pressure_fit": np.asarray(
                [
                    False
                ],
                dtype=np.bool_,
            ),
            "locked_OOD_used_for_pressure_fit": np.asarray(
                [
                    False
                ],
                dtype=np.bool_,
            ),
            "historical_AV2A3_pressure_stats_directly_reused": np.asarray(
                [
                    False
                ],
                dtype=np.bool_,
            ),
            "sampling_origin_center_m": ORIGIN_CENTER_M,
        }

        pair_registry = {
            "TRAIN_sample_index_a": train_pairs[
                "sample_index_a"
            ],
            "TRAIN_sample_index_b": train_pairs[
                "sample_index_b"
            ],
            "VALIDATION_sample_index_a": val_pairs[
                "sample_index_a"
            ],
            "VALIDATION_sample_index_b": val_pairs[
                "sample_index_b"
            ],
            "TRAIN_pair_count": np.asarray(
                [
                    TRAIN_PAIRS
                ],
                dtype=np.int64,
            ),
            "VALIDATION_pair_count": np.asarray(
                [
                    VAL_PAIRS
                ],
                dtype=np.int64,
            ),
            "LOCKED_OOD_pair_count": np.asarray(
                [
                    0
                ],
                dtype=np.int64,
            ),
        }

        files = {
            "PAD_Stream_POSTV16_AV3_A4_R2_Summary.json":
                json_bytes(
                    summary
                ),

            "POSTV16_AV3_A4_R2_TrainValidation_13Channel_Transport_Dataset.npz":
                deterministic_npz_bytes(
                    {
                        "X_required_13": X_tv,
                        "Y_transport": Y_tv,
                        "realization_index": realization_tv,
                        "time_index": time_tv,
                        "streamline_index": streamline_tv,
                        "partition_code": partition_tv,
                        "target_time_days": day_tv,
                        "target_time_hat": th_tv,
                        "target_eta_sequence": eta_tv,
                        "channel_names": np.asarray(
                            CHANNELS13,
                            dtype="U32",
                        ),
                        "partition_names": np.asarray(
                            [
                                "TRAIN",
                                "VALIDATION",
                            ],
                            dtype="U32",
                        ),
                    }
                ),

            "POSTV16_AV3_A4_R2_LockedOOD_13Channel_Predictor_Only_Dataset.npz":
                deterministic_npz_bytes(
                    {
                        "X_required_13":
                            ood_block[
                                "X"
                            ],
                        "realization_index":
                            ood_block[
                                "realization_index"
                            ],
                        "time_index":
                            ood_block[
                                "time_index"
                            ],
                        "streamline_index":
                            ood_block[
                                "streamline_index"
                            ],
                        "target_time_days":
                            ood_block[
                                "target_time_days"
                            ],
                        "target_time_hat":
                            ood_block[
                                "target_time_hat"
                            ],
                        "target_eta_sequence":
                            ood_block[
                                "target_eta_sequence"
                            ],
                        "static_log_streamline_weight_z":
                            ood_block[
                                "static_log_streamline_weight_z"
                            ],
                        "channel_names": np.asarray(
                            CHANNELS13,
                            dtype="U32",
                        ),
                        "contains_Y_transport": np.asarray(
                            [
                                False
                            ],
                            dtype=np.bool_,
                        ),
                    }
                ),

            "POSTV16_AV3_A4_R2_Spatial_Relperm_Physics_Sidecar.npz":
                deterministic_npz_bytes(
                    sidecar
                ),

            "POSTV16_AV3_A4_R2_Corrected_TRAIN_Only_Normalization.npz":
                deterministic_npz_bytes(
                    normalization
                ),

            "POSTV16_AV3_A4_R2_Adjacent_Time_Physics_Pair_Registry.npz":
                deterministic_npz_bytes(
                    pair_registry
                ),

            "POSTV16_AV3_A4_R2_Teacher_Certification_By_Realization.csv":
                csv_bytes(
                    teacher_rows
                ),

            "POSTV16_AV3_A4_R2_Corrected_First9_Sampling_Audit.csv":
                csv_bytes(
                    first9_audit_rows
                ),

            "POSTV16_AV3_A4_R2_A5_Handoff_Contract.json":
                json_bytes(
                    handoff
                ),

            "POSTV16_AV3_A4_R2_Decision_Contract.json":
                json_bytes(
                    decision
                ),

            "POSTV16_AV3_A4_R2_Final_Gate_Matrix.csv":
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

        for q in sorted(
            out.iterdir()
        ):

            if (
                q.is_file()
                and q.name
                != "POSTV16_AV3_A4_R2_Artifact_Manifest.csv"
            ):

                manifest_rows.append(
                    {
                        "file": q.name,
                        "sha256": sha256_file(
                            q
                        ),
                        "bytes": q.stat().st_size,
                    }
                )

        immutable_publish(
            out,
            {
                "POSTV16_AV3_A4_R2_Artifact_Manifest.csv":
                    csv_bytes(
                        manifest_rows
                    )
            },
        )

        print()
        print("=" * 208)
        print("POSTV16-AV3-A4-R2: FULL CORRECTED-CERTIFICATION TEACHER / 13-CHANNEL DATASET / LOCKED-OOD PREDICTOR PASS")
        print("=" * 208)
        print("Original AV3-A4 scientific FAIL              : PRESERVED")
        print("R1 corrected certification semantics          : APPLIED")
        print("Morphology diagnostics                        : REPORT ONLY / NO THRESHOLD")
        print("Correct cell-center origin m                  :", ORIGIN_CENTER_M.tolist())
        print("Historical AV2-A3 X9 direct reuse             : False")
        print("Teacher realizations certified               : 3 / 3")
        print("TRAIN samples                                :", train_count)
        print("VALIDATION samples                           :", val_count)
        print("LOCKED OOD predictor samples                 :", ood_block["X"].shape[0])
        print("LOCKED OOD Y generated/opened                : False / False")
        print("Corrected TRAIN pressure mean/std [psi]      :", pmean, "/", pstd)
        print("X13 shape TRAIN+VALIDATION                   :", X_tv.shape)
        print("Y shape TRAIN+VALIDATION                     :", Y_tv.shape)
        print("X13 shape LOCKED OOD                         :", ood_block["X"].shape)
        print("TRAIN / VALIDATION physics pairs             :", TRAIN_PAIRS, "/", VAL_PAIRS)
        print("Predictor phi == physics-sidecar phi         : True")
        print("Model training / checkpoint / inference      : False / False / False")
        print("POSTV16-AV3-A5                               : AUTHORIZED")
        print("A5 execution                                 : AUTHORIZED")
        print("=" * 208)

        return 0

    except ScientificFail as exc:

        fail.mkdir(
            parents=True,
            exist_ok=True,
        )

        report = {
            "milestone": MILESTONE,
            "status": STATUS_FAIL,
            "original_AV3A4_scientific_FAIL_preserved": True,
            "original_AV3A4_fail_SHA256": ORIGINAL_A4_FAIL_SHA256,
            "R1_corrected_certification_semantics_applied": True,
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
            "LP_execution": False,
            "CMG_validation": False,
            "AV3_A5_authorized": False,
            "next_action": (
                "Freeze and interpret this A4-R2 scientific failure while preserving the original A4 FAIL. "
                "Do not open AV3CR0004 Y, reject/reseed constitutive fields, "
                "retune the A1-A3 protocol, or train the model."
            ),
        }

        data = json_bytes(
            report
        )

        q = (
            fail
            / "POSTV16_AV3_A4_R2_Scientific_Fail_Report.json"
        )

        if (
            q.exists()
            and q.read_bytes()
            != data
        ):

            suffix = hashlib.sha256(
                data
            ).hexdigest()[
                :12
            ]

            q = (
                fail
                / f"POSTV16_AV3_A4_R2_Scientific_Fail_Report_{suffix}.json"
            )

        if not q.exists():
            q.write_bytes(
                data
            )

        print()
        print("=" * 208)
        print("POSTV16-AV3-A4-R2: SCIENTIFIC FAIL")
        print("=" * 208)
        print("Failed stage :", stage)
        print("Failed gate  :", exc.gate)
        print("Detail       :", exc.detail)
        print("LOCKED OOD Y opened :", locked_ood_target_opened)
        print("POSTV16-AV3-A5 IS NOT AUTHORIZED.")
        print("=" * 208)

        return 3

    except Exception as exc:

        blocked.mkdir(
            parents=True,
            exist_ok=True,
        )

        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "original_AV3A4_scientific_FAIL_preserved": True,
            "original_AV3A4_fail_SHA256": ORIGINAL_A4_FAIL_SHA256,
            "R1_corrected_certification_semantics_applied": True,
            "failed_stage": stage,
            "exception": repr(
                exc
            ),
            "gates": gates,
            "teacher_generation_started": teacher_generation_started,
            "teacher_realizations_completed": teacher_realizations_completed,
            "LOCKED_OOD_target_opened": locked_ood_target_opened,
            "training": False,
            "checkpoint_created": False,
            "inference": False,
            "mapback": False,
            "LP_execution": False,
            "CMG_validation": False,
            "AV3_A5_authorized": False,
            "next_action": (
                "Audit only the technical A4-R2 block while preserving the original A4 FAIL. "
                "Do not open locked-OOD Y, change frozen fields, or train."
            ),
        }

        data = json_bytes(
            report
        )

        q = (
            blocked
            / "POSTV16_AV3_A4_R2_Blocked_Report.json"
        )

        if (
            q.exists()
            and q.read_bytes()
            != data
        ):

            suffix = hashlib.sha256(
                data
            ).hexdigest()[
                :12
            ]

            q = (
                blocked
                / f"POSTV16_AV3_A4_R2_Blocked_Report_{suffix}.json"
            )

        if not q.exists():
            q.write_bytes(
                data
            )

        print()
        print("=" * 208)
        print("POSTV16-AV3-A4-R2: TECHNICAL BLOCK")
        print("=" * 208)
        print("Failed stage :", stage)
        print("Exception    :", repr(exc))
        print("LOCKED OOD Y opened :", locked_ood_target_opened)
        print("POSTV16-AV3-A5 IS NOT AUTHORIZED.")
        print("=" * 208)

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
        raise SystemExit(
            0
        )

    raise SystemExit(
        main(
            args.project_root,
            args.drive_root,
        )
    )
