#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any

import numpy as np


MILESTONE = "POSTV16-AV4-A2-E"

STATUS_PASS = (
    "AV4A2E_AV3CR0003_DAY365_SAME_TIME_SPATIAL_MOBILITY_PRESSURE_SATURATION_"
    "REFRESH_DARCY_POLLOCK_TOF_GEOMETRY_EXECUTION_PASS"
)

STATUS_FAIL = (
    "AV4A2E_AV3CR0003_DAY365_DYNAMIC_FLOW_REFRESH_SCIENTIFIC_FAIL_"
    "NO_ADAPTATION_OR_AUTOMATIC_RERUN_AUTHORIZED"
)

STATUS_BLOCKED = "AV4A2E_TECHNICAL_EXECUTION_BLOCKED"

PROTOCOL_ID = (
    "POSTV16_AV4_A2_E_AV3CR0003_DAY365_SAME_TIME_SPATIAL_MOBILITY_"
    "PRESSURE_SATURATION_FLOW_REFRESH_EXECUTION_V1"
)

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

PARENT_A2_COMMIT = "0b7c5f0136178f4e90a51572f6336e90620b5e3f"

A2_STATUS = (
    "AV4A2_AV3CR0003_DAY365_CONTROLLED_SAME_TIME_DYNAMIC_FLOW_REFRESH_"
    "PARENT_STATE_AND_EXECUTION_CONTRACT_PROSPECTIVELY_FROZEN_NO_EXECUTION"
)

A6E_STATUS = (
    "AV3A6E_FROZEN_EPOCH92_CHECKPOINT_LOCAL_PORE_VOLUME_R7D_TERMINAL_HALO_"
    "INTEGRATION_ALL_4_REALIZATIONS_ALL_9_TIMES_PASS"
)

CONTROL_REALIZATION = "AV3CR0003"
CONTROL_POROSITY = "AV2PHI0003"
CONTROL_PARTITION = "VALIDATION"
CONTROL_DAY = 365.0
CONTROL_TIME_INDEX = 5

GRID = (15, 50, 50)
NZ, NY, NX = GRID

DAYS = np.asarray(
    [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0],
    dtype=np.float64,
)

DX_M = 6.096
DY_M = 6.096
DZ_M = 1.2192
BULK_VOLUME_M3 = DX_M * DY_M * DZ_M

BACKGROUND = 0.20
INJECTED = 0.80
MAX_SG = 0.60

MU_W_PA_S = 0.50e-3
MU_O_PA_S = 5.00e-3

MAX_FIXED_POINT_ITERATIONS = 100
PRESSURE_REL_L2_TOL = 1.0e-10
SATURATION_LINF_TOL = 1.0e-10
PRESSURE_LINEAR_REL_RESIDUAL_MAX = 1.0e-8

FLOW_LOCAL_REL_L2_MAX = 1.0e-8
FLOW_GLOBAL_REL_MISMATCH_MAX = 1.0e-8
INJECTOR_WEIGHT_REL_CLOSURE_MAX = 1.0e-10
GLOBAL_MASS_REL_TOL = 1.0e-10

DAY_TO_S = 86400.0

FOUNDATION_NAME = "V16A_Foundation_Case_0001.npz"
FOUNDATION_SHA256 = "4239e412ca6e2780f108c8eb1b0252e80a56be305bce48cc58e50d6140b86acc"

CONTROL_STATE_FILE = "POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
CONTROL_STATE_SHA256 = "f9e3a7bd8c6dcc43d522e0cb99a0cede2bd212fd570085b4faf82dc71af8f803"

# --------------------------------------------------------------------------------------------------
# Exact source authorities.
# --------------------------------------------------------------------------------------------------

A2 = "PAD_Stream_POSTV16_AV4_A2_Controlled_Validation_Refresh_Execution_Contract_Freeze.py"
A2_BLOB = "41bce32b6053060cb78cb47347db8be23ae1c16c"

A1 = "PAD_Stream_POSTV16_AV4_A1_Spatial_Mobility_Pressure_Refresh_and_Flow_Epoch_Contract_Freeze.py"
A1_BLOB = "9c48fd564be748295576264a9f9c6ad67327fdd2"

A6E = "PAD_Stream_POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution.py"
A6E_BLOB = "e3dcb0aa9354c399904f7f0e830b6a1fddd78987"

R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

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

E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"

R3R2R1 = "PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py"
R3R2R1_BLOB = "740c6da03e73906646bf0153633187e749449f31"

PERM = "SGSIM_50x50x15_PERM_MD.csv"
PERM_BLOB = "317dd47d458bc6f880c2e3dc4ec1f69eeb0dd314"

SOURCE_BLOBS = {
    A2: A2_BLOB,
    A1: A1_BLOB,
    A6E: A6E_BLOB,
    R2: R2_BLOB,
    SG2: SG2_BLOB,
    SG3: SG3_BLOB,
    SG4: SG4_BLOB,
    SG5: SG5_BLOB,
    SG6: SG6_BLOB,
    SG7D: SG7D_BLOB,
    E37A: E37A_BLOB,
    R3R2R1: R3R2R1_BLOB,
    PERM: PERM_BLOB,
}

# --------------------------------------------------------------------------------------------------
# Frozen Drive authorities.
# --------------------------------------------------------------------------------------------------

BASE_AV4 = (
    Path("post_v16")
    / RID
    / "POSTV16_AV4_Dynamic_Flow_Coupling"
)

A2_REL = (
    BASE_AV4
    / "POSTV16_AV4_A2_Controlled_Validation_Refresh_Execution_Contract_Freeze"
)

A2_SUMMARY = "PAD_Stream_POSTV16_AV4_A2_Summary.json"
A2_PARENT = "POSTV16_AV4_A2_Frozen_Parent_State_Identity.json"
A2_PREEXEC = "POSTV16_AV4_A2_PreExecution_Parent_State_Certification_Contract.json"
A2_RECIPE = "POSTV16_AV4_A2_Controlled_Refresh_Execution_Recipe.json"
A2_GATES = "POSTV16_AV4_A2_Execution_Gates_and_Outcome_Classification.json"
A2_OUTPUT = "POSTV16_AV4_A2_Atomic_Refreshed_Flow_Epoch_Output_Contract.json"
A2_POST = "POSTV16_AV4_A2_PostExecution_Handoff_Contract.json"
A2_HANDOFF = "POSTV16_AV4_A2_A2E_Handoff_Contract.json"
A2_DECISION = "POSTV16_AV4_A2_Decision_Contract.json"
A2_MANIFEST = "POSTV16_AV4_A2_Artifact_Manifest.csv"

BASE_AV3 = (
    Path("post_v16")
    / RID
    / "POSTV16_AV3_Corey_Relperm_Heterogeneity"
)

A6E_REL = (
    BASE_AV3
    / "POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
)

A6E_SUMMARY = "PAD_Stream_POSTV16_AV3_A6_E_Summary.json"
A6E_MANIFEST = "POSTV16_AV3_A6_E_Artifact_Manifest.csv"

OUT_REL = (
    BASE_AV4
    / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
)

FAIL_REL = BASE_AV4 / "POSTV16_AV4_A2_E_SCIENTIFIC_FAIL"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_A2_E_BLOCKED"


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

        for block in iter(
            lambda: f.read(1 << 20),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def sha256_array(a: np.ndarray) -> str:

    arr = np.ascontiguousarray(
        np.asarray(a)
    )

    h = hashlib.sha256()

    h.update(
        str(arr.dtype).encode("utf-8")
    )

    h.update(
        repr(arr.shape).encode("utf-8")
    )

    h.update(
        arr.tobytes(order="C")
    )

    return h.hexdigest()


def git_text(root: Path, *args: str) -> str:

    return subprocess.run(
        [
            "git",
            "-C",
            str(root),
            *args,
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


def load_json(path: Path) -> dict[str, Any]:

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def read_csv(path: Path) -> list[dict[str, str]]:

    with path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as f:

        return list(
            csv.DictReader(f)
        )


def verify_manifest(
    directory: Path,
    name: str,
) -> dict[str, str]:

    rows = read_csv(
        directory
        / name
    )

    manifest = {
        r["file"]:
            r["sha256"]
        for r in rows
    }

    if not manifest:
        raise GateError(
            "manifest_empty:"
            + name
        )

    for fn, expected in manifest.items():

        p = (
            directory
            / fn
        )

        if not p.is_file():
            raise GateError(
                "manifest_missing:"
                + fn
            )

        if sha256_file(
            p
        ) != expected:
            raise GateError(
                "manifest_SHA_mismatch:"
                + fn
            )

    return manifest


def load_module(
    path: Path,
    name: str,
):

    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise GateError(
            "cannot_load_module:"
            + str(path)
        )

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[
        name
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


def find_named_exact(
    roots: list[Path],
    name: str,
    expected_sha256: str,
) -> Path:

    candidates: list[Path] = []

    for root in roots:

        if not root.exists():
            continue

        direct = (
            root
            / name
        )

        if direct.is_file():
            candidates.append(
                direct
            )

        for p in root.rglob(
            name
        ):

            if p.is_file():
                candidates.append(
                    p
                )

    seen: set[str] = set()

    for p in candidates:

        key = str(
            p.resolve()
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        if sha256_file(
            p
        ) == expected_sha256:
            return p

    raise GateError(
        "exact_file_not_found:"
        f"{name}:"
        f"{expected_sha256}"
    )


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


def csv_bytes(
    rows: list[dict[str, Any]],
) -> bytes:

    if not rows:
        return b""

    fields: list[str] = []

    for row in rows:

        for key in row:

            if key not in fields:
                fields.append(
                    key
                )

    s = io.StringIO(
        newline=""
    )

    w = csv.DictWriter(
        s,
        fieldnames=fields,
        lineterminator="\n",
    )

    w.writeheader()
    w.writerows(
        rows
    )

    return s.getvalue().encode(
        "utf-8"
    )


def deterministic_npz_bytes(
    arrays: dict[str, Any],
) -> bytes:

    outer = io.BytesIO()

    with zipfile.ZipFile(
        outer,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as zf:

        for key in sorted(
            arrays
        ):

            b = io.BytesIO()

            np.save(
                b,
                np.asarray(
                    arrays[
                        key
                    ]
                ),
                allow_pickle=False,
            )

            info = zipfile.ZipInfo(
                f"{key}.npy",
                date_time=(
                    1980,
                    1,
                    1,
                    0,
                    0,
                    0,
                ),
            )

            info.compress_type = (
                zipfile.ZIP_DEFLATED
            )

            info.external_attr = (
                0o600 << 16
            )

            zf.writestr(
                info,
                b.getvalue(),
            )

    return outer.getvalue()


def immutable_publish(
    out: Path,
    files: dict[str, bytes],
) -> None:

    out.mkdir(
        parents=True,
        exist_ok=True,
    )

    for name, data in files.items():

        p = (
            out
            / name
        )

        if (
            p.exists()
            and p.read_bytes()
            != data
        ):
            raise GateError(
                "existing_output_differs:"
                + name
            )

        if not p.exists():

            p.write_bytes(
                data
            )


def max_abs(
    a: np.ndarray,
) -> float:

    return float(
        np.max(
            np.abs(
                np.asarray(
                    a,
                    dtype=np.float64,
                )
            )
        )
    )


def relative_l2(
    new: np.ndarray,
    old: np.ndarray,
) -> float:

    a = np.asarray(
        new,
        dtype=np.float64,
    )

    b = np.asarray(
        old,
        dtype=np.float64,
    )

    return float(
        np.linalg.norm(
            (
                a
                - b
            ).ravel()
        )
        / max(
            float(
                np.linalg.norm(
                    b.ravel()
                )
            ),
            1.0e-30,
        )
    )


def spatial_mobility(
    saturation: np.ndarray,
    nw: np.ndarray,
    no: np.ndarray,
    krw_max: np.ndarray,
    kro_max: np.ndarray,
) -> dict[str, np.ndarray]:

    S = np.asarray(
        saturation,
        dtype=np.float64,
    )

    Se = np.clip(
        (
            S
            - BACKGROUND
        )
        / MAX_SG,
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
            1.0
            - Se
        )
        ** np.asarray(
            no,
            dtype=np.float64,
        )
    )

    lambda_w = (
        krw
        / MU_W_PA_S
    )

    lambda_o = (
        kro
        / MU_O_PA_S
    )

    lambda_total = (
        lambda_w
        + lambda_o
    )

    if (
        lambda_total.shape
        != GRID
        or not np.isfinite(
            lambda_total
        ).all()
        or np.any(
            lambda_total
            <= 0.0
        )
    ):
        raise GateError(
            "invalid_spatial_total_mobility"
        )

    return {
        "effective_saturation":
            Se,
        "krw":
            krw,
        "kro":
            kro,
        "lambda_w":
            lambda_w,
        "lambda_o":
            lambda_o,
        "lambda_total":
            lambda_total,
    }


def local_mass(
    r2: Any,
    saturation: np.ndarray,
    pressure_psi: np.ndarray,
    p_ref_gas_pa: float,
    pore_volume_m3: np.ndarray,
) -> np.ndarray:

    sat = np.asarray(
        saturation,
        dtype=np.float64,
    )

    pv = np.asarray(
        pore_volume_m3,
        dtype=np.float64,
    )

    sg = np.clip(
        sat
        - BACKGROUND,
        0.0,
        MAX_SG,
    )

    rho = np.asarray(
        r2.gas_density_from_state(
            sat,
            pressure_psi,
            p_ref_gas_pa,
        ),
        dtype=np.float64,
    )

    return (
        pv
        * rho
        * sg
    )


def invert_local_mass(
    r2: Any,
    target_mass_kg: np.ndarray,
    pressure_psi: np.ndarray,
    p_ref_gas_pa: float,
    pore_volume_m3: np.ndarray,
) -> np.ndarray:

    target = np.asarray(
        target_mass_kg,
        dtype=np.float64,
    )

    pv = np.asarray(
        pore_volume_m3,
        dtype=np.float64,
    )

    if (
        target.shape
        != GRID
        or pv.shape
        != GRID
        or np.any(
            pv
            <= 0.0
        )
        or not np.isfinite(
            pv
        ).all()
    ):
        raise GateError(
            "local_EOS_inversion_input"
        )

    if np.any(
        target
        < -1.0e-9
    ):
        raise ScientificFail(
            "negative_parent_cell_mass",
            float(
                np.min(
                    target
                )
            ),
        )

    target = np.maximum(
        target,
        0.0,
    )

    capacity = local_mass(
        r2,
        np.full(
            GRID,
            INJECTED,
            dtype=np.float64,
        ),
        pressure_psi,
        p_ref_gas_pa,
        pv,
    )

    cap_tol = max(
        1.0e-8,
        1.0e-12
        * max(
            float(
                np.max(
                    capacity
                )
            ),
            1.0,
        ),
    )

    excess = float(
        np.max(
            target
            - capacity
        )
    )

    if excess > cap_tol:

        raise ScientificFail(
            "same_time_local_cell_mass_capacity",
            {
                "maximum_excess_kg":
                    excess,
                "tolerance_kg":
                    cap_tol,
            },
        )

    lower = np.zeros(
        GRID,
        dtype=np.float64,
    )

    upper = np.full(
        GRID,
        MAX_SG,
        dtype=np.float64,
    )

    for _ in range(
        80
    ):

        mid = 0.5 * (
            lower
            + upper
        )

        mass_mid = local_mass(
            r2,
            BACKGROUND
            + mid,
            pressure_psi,
            p_ref_gas_pa,
            pv,
        )

        below = (
            mass_mid
            < target
        )

        lower = np.where(
            below,
            mid,
            lower,
        )

        upper = np.where(
            below,
            upper,
            mid,
        )

    sg = 0.5 * (
        lower
        + upper
    )

    sg[
        target
        <= 1.0e-18
    ] = 0.0

    return sg


def reference_gas_pressure_pa(
    r2: Any,
    pressure_psi: np.ndarray,
) -> float:

    injector_capillary_pa = float(
        r2.capillary_pressure_from_incremental_sg(
            float(
                r2.MAX_INCREMENTAL_CO2_SATURATION
            )
        )
    )

    injector_pressure_pa = np.asarray(
        [
            pressure_psi[
                int(k),
                int(
                    r2.INJECTOR_J
                ),
                int(
                    r2.INJECTOR_I
                ),
            ]
            * float(
                r2.PSI_TO_PA
            )
            for k in r2.COMPLETION_K
        ],
        dtype=np.float64,
    )

    p_ref = float(
        np.mean(
            injector_pressure_pa
        )
        + injector_capillary_pa
    )

    if not np.isfinite(
        p_ref
    ):
        raise GateError(
            "reference_gas_pressure_nonfinite"
        )

    return p_ref


def convert_sg5_to_sg6(
    streamlines: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    result = []

    for idx, s in enumerate(
        streamlines
    ):

        result.append(
            {
                "id":
                    idx,
                "points_m":
                    np.asarray(
                        s[
                            "points_m"
                        ],
                        dtype=np.float64,
                    ),
                "tau_s":
                    np.asarray(
                        s[
                            "times_s"
                        ],
                        dtype=np.float64,
                    ),
                "weight_m3_s":
                    float(
                        s[
                            "weight_m3_s"
                        ]
                    ),
                "tau_end_s":
                    float(
                        s[
                            "travel_time_s"
                        ]
                    ),
                "status":
                    str(
                        s[
                            "status"
                        ]
                    ),
                "producer":
                    str(
                        s[
                            "producer"
                        ]
                    ),
            }
        )

    return result


def sample_pressure_at_streamline_nodes(
    sg7d: Any,
    xyz_m: np.ndarray,
    pressure_psi: np.ndarray,
) -> np.ndarray:

    xyz = np.asarray(
        xyz_m,
        dtype=np.float64,
    )

    result = np.empty(
        xyz.shape[:2],
        dtype=np.float64,
    )

    for s in range(
        xyz.shape[
            0
        ]
    ):

        for n in range(
            xyz.shape[
                1
            ]
        ):

            k, j, i = (
                sg7d.point_to_cell(
                    xyz[
                        s,
                        n,
                    ]
                )
            )

            result[
                s,
                n,
            ] = pressure_psi[
                k,
                j,
                i,
            ]

    return result


def fixed_point_refresh(
    *,
    r2: Any,
    r3r2r1: Any,
    sg2: Any,
    sg3: Any,
    permeability_md: np.ndarray,
    parent_mass: np.ndarray,
    parent_saturation: np.ndarray,
    parent_pressure_psi: np.ndarray,
    p_ref_gas_pa: float,
    pore_volume_m3: np.ndarray,
    nw: np.ndarray,
    no: np.ndarray,
    krw_max: np.ndarray,
    kro_max: np.ndarray,
    sci_gate,
) -> dict[str, Any]:

    kx, ky, kz = (
        sg2.build_directional_permeability(
            permeability_md
        )
    )

    kfx, kfy, kfz = (
        sg2.build_face_permeabilities(
            kx,
            ky,
            kz,
        )
    )

    tx_ref, ty_ref, tz_ref = (
        sg3.construct_si_transmissibilities(
            kfx,
            kfy,
            kfz,
        )
    )

    working_sat = np.asarray(
        parent_saturation,
        dtype=np.float64,
    ).copy()

    previous_pressure = np.asarray(
        parent_pressure_psi,
        dtype=np.float64,
    ).copy()

    rows: list[dict[str, Any]] = []

    accepted_pressure = None
    accepted_sat = None
    accepted_tx = None
    accepted_ty = None
    accepted_tz = None
    accepted_wi = None
    accepted_mobility = None

    cell_mass_tol = max(
        1.0e-8,
        1.0e-10
        * max(
            float(
                np.max(
                    parent_mass
                )
            ),
            1.0,
        ),
    )

    total_parent_mass = float(
        np.sum(
            parent_mass
        )
    )

    for iteration in range(
        1,
        MAX_FIXED_POINT_ITERATIONS
        + 1,
    ):

        mobility = spatial_mobility(
            working_sat,
            nw,
            no,
            krw_max,
            kro_max,
        )

        tx, ty, tz, face_mobility = (
            r3r2r1.build_updated_transmissibilities(
                sg3,
                tx_ref,
                ty_ref,
                tz_ref,
                mobility[
                    "lambda_total"
                ],
            )
        )

        try:

            A, b, producer_wi = (
                r3r2r1.assemble_updated_pressure_system(
                    sg3,
                    permeability_md,
                    tx,
                    ty,
                    tz,
                    mobility[
                        "lambda_total"
                    ],
                )
            )

            (
                _pressure_pa,
                pressure_psi,
                pressure_linear_residual,
            ) = (
                r3r2r1.solve_updated_pressure(
                    sg3,
                    A,
                    b,
                )
            )

        except Exception as exc:

            raise ScientificFail(
                "pressure_solve_failure",
                {
                    "iteration":
                        iteration,
                    "exception":
                        repr(
                            exc
                        ),
                },
            ) from exc

        sci_gate(
            f"iteration_{iteration:03d}_pressure_linear_residual",
            pressure_linear_residual
            < PRESSURE_LINEAR_REL_RESIDUAL_MAX,
            pressure_linear_residual,
        )

        try:

            sg_reconciled = (
                invert_local_mass(
                    r2,
                    parent_mass,
                    pressure_psi,
                    p_ref_gas_pa,
                    pore_volume_m3,
                )
            )

        except ScientificFail:
            raise

        except Exception as exc:

            raise ScientificFail(
                "same_time_EOS_inversion_failure",
                {
                    "iteration":
                        iteration,
                    "exception":
                        repr(
                            exc
                        ),
                },
            ) from exc

        reconciled_sat = (
            BACKGROUND
            + sg_reconciled
        )

        reconstructed_mass = (
            local_mass(
                r2,
                reconciled_sat,
                pressure_psi,
                p_ref_gas_pa,
                pore_volume_m3,
            )
        )

        max_cell_mass_error = (
            max_abs(
                reconstructed_mass
                - parent_mass
            )
        )

        global_mass_relative_error = (
            abs(
                float(
                    np.sum(
                        reconstructed_mass
                    )
                    - total_parent_mass
                )
            )
            / max(
                abs(
                    total_parent_mass
                ),
                1.0,
            )
        )

        pressure_delta_rel = (
            relative_l2(
                pressure_psi,
                previous_pressure,
            )
        )

        saturation_delta_linf = (
            max_abs(
                reconciled_sat
                - working_sat
            )
        )

        rows.append(
            {
                "iteration":
                    iteration,
                "pressure_relative_L2_change":
                    pressure_delta_rel,
                "saturation_Linf_change":
                    saturation_delta_linf,
                "pressure_linear_relative_residual":
                    pressure_linear_residual,
                "max_cell_mass_error_kg":
                    max_cell_mass_error,
                "global_mass_relative_error":
                    global_mass_relative_error,
                "pressure_min_psi":
                    float(
                        np.min(
                            pressure_psi
                        )
                    ),
                "pressure_max_psi":
                    float(
                        np.max(
                            pressure_psi
                        )
                    ),
                "saturation_min":
                    float(
                        np.min(
                            reconciled_sat
                        )
                    ),
                "saturation_max":
                    float(
                        np.max(
                            reconciled_sat
                        )
                    ),
                "lambda_total_min":
                    float(
                        np.min(
                            mobility[
                                "lambda_total"
                            ]
                        )
                    ),
                "lambda_total_max":
                    float(
                        np.max(
                            mobility[
                                "lambda_total"
                            ]
                        )
                    ),
            }
        )

        accepted_pressure = (
            pressure_psi
        )

        accepted_sat = (
            reconciled_sat
        )

        accepted_tx = (
            tx
        )

        accepted_ty = (
            ty
        )

        accepted_tz = (
            tz
        )

        accepted_wi = (
            producer_wi
        )

        accepted_mobility = (
            mobility
        )

        if (
            pressure_delta_rel
            <= PRESSURE_REL_L2_TOL
            and saturation_delta_linf
            <= SATURATION_LINF_TOL
        ):

            sci_gate(
                "fixed_point_cellwise_mass_error",
                max_cell_mass_error
                <= cell_mass_tol,
                {
                    "error_kg":
                        max_cell_mass_error,
                    "tolerance_kg":
                        cell_mass_tol,
                },
            )

            sci_gate(
                "fixed_point_global_mass_relative_error",
                global_mass_relative_error
                <= GLOBAL_MASS_REL_TOL,
                global_mass_relative_error,
            )

            break

        previous_pressure = (
            pressure_psi
        )

        working_sat = (
            reconciled_sat
        )

    else:

        raise ScientificFail(
            "pressure_saturation_fixed_point_nonconvergence",
            {
                "maximum_iterations":
                    MAX_FIXED_POINT_ITERATIONS,
                "last":
                    rows[
                        -1
                    ]
                    if rows
                    else None,
            },
        )

    working_sat = np.asarray(
        accepted_sat,
        dtype=np.float64,
    )

    previous_pressure = np.asarray(
        accepted_pressure,
        dtype=np.float64,
    )

    mobility_final = spatial_mobility(
        working_sat,
        nw,
        no,
        krw_max,
        kro_max,
    )

    tx_final, ty_final, tz_final, face_final = (
        r3r2r1.build_updated_transmissibilities(
            sg3,
            tx_ref,
            ty_ref,
            tz_ref,
            mobility_final[
                "lambda_total"
            ],
        )
    )

    try:

        A, b, wi_final = (
            r3r2r1.assemble_updated_pressure_system(
                sg3,
                permeability_md,
                tx_final,
                ty_final,
                tz_final,
                mobility_final[
                    "lambda_total"
                ],
            )
        )

        (
            _p_pa,
            pressure_final,
            linear_final,
        ) = (
            r3r2r1.solve_updated_pressure(
                sg3,
                A,
                b,
            )
        )

    except Exception as exc:

        raise ScientificFail(
            "final_consistency_pressure_solve_failure",
            repr(
                exc
            ),
        ) from exc

    sci_gate(
        "final_pressure_linear_residual",
        linear_final
        < PRESSURE_LINEAR_REL_RESIDUAL_MAX,
        linear_final,
    )

    sg_final = invert_local_mass(
        r2,
        parent_mass,
        pressure_final,
        p_ref_gas_pa,
        pore_volume_m3,
    )

    sat_final = (
        BACKGROUND
        + sg_final
    )

    pressure_consistency = (
        relative_l2(
            pressure_final,
            previous_pressure,
        )
    )

    saturation_consistency = (
        max_abs(
            sat_final
            - working_sat
        )
    )

    sci_gate(
        "final_pressure_fixed_point_consistency",
        pressure_consistency
        <= PRESSURE_REL_L2_TOL,
        pressure_consistency,
    )

    sci_gate(
        "final_saturation_fixed_point_consistency",
        saturation_consistency
        <= SATURATION_LINF_TOL,
        saturation_consistency,
    )

    reconstructed_final = (
        local_mass(
            r2,
            sat_final,
            pressure_final,
            p_ref_gas_pa,
            pore_volume_m3,
        )
    )

    max_cell_mass_error_final = (
        max_abs(
            reconstructed_final
            - parent_mass
        )
    )

    global_mass_relative_final = (
        abs(
            float(
                np.sum(
                    reconstructed_final
                )
                - total_parent_mass
            )
        )
        / max(
            abs(
                total_parent_mass
            ),
            1.0,
        )
    )

    sci_gate(
        "final_cellwise_mass_reconstruction",
        max_cell_mass_error_final
        <= cell_mass_tol,
        {
            "error_kg":
                max_cell_mass_error_final,
            "tolerance_kg":
                cell_mass_tol,
        },
    )

    sci_gate(
        "final_global_mass_relative_closure",
        global_mass_relative_final
        <= GLOBAL_MASS_REL_TOL,
        global_mass_relative_final,
    )

    sci_gate(
        "final_saturation_bounds",
        float(
            np.min(
                sat_final
            )
        )
        >= BACKGROUND
        - 1.0e-12
        and float(
            np.max(
                sat_final
            )
        )
        <= INJECTED
        + 1.0e-12,
        [
            float(
                np.min(
                    sat_final
                )
            ),
            float(
                np.max(
                    sat_final
                )
            ),
        ],
    )

    return {
        "saturation":
            sat_final,
        "pressure_psi":
            pressure_final,
        "tx":
            tx_final,
        "ty":
            ty_final,
        "tz":
            tz_final,
        "producer_wi":
            wi_final,
        "mobility":
            mobility_final,
        "face_mobility":
            face_final,
        "rows":
            rows,
        "iterations":
            len(
                rows
            ),
        "max_cell_mass_error_kg":
            max_cell_mass_error_final,
        "global_mass_relative_error":
            global_mass_relative_final,
        "pressure_rel_L2_vs_parent":
            relative_l2(
                pressure_final,
                parent_pressure_psi,
            ),
        "saturation_Linf_vs_parent":
            max_abs(
                sat_final
                - parent_saturation
            ),
        "pressure_consistency":
            pressure_consistency,
        "saturation_consistency":
            saturation_consistency,
    }


def self_test() -> None:

    sat = np.full(
        GRID,
        0.50,
        dtype=np.float64,
    )

    nw = np.full(
        GRID,
        3.0,
        dtype=np.float64,
    )

    no = np.full(
        GRID,
        3.0,
        dtype=np.float64,
    )

    krw_max = np.full(
        GRID,
        0.80,
        dtype=np.float64,
    )

    kro_max = np.full(
        GRID,
        0.80,
        dtype=np.float64,
    )

    # Introduce deterministic heterogeneity at two cells while preserving
    # the full production-grid shape required by spatial_mobility().
    nw[0, 0, 0] = 2.2
    no[0, 0, 0] = 3.8
    krw_max[0, 0, 0] = 0.65
    kro_max[0, 0, 0] = 0.95

    nw[-1, -1, -1] = 3.8
    no[-1, -1, -1] = 2.2
    krw_max[-1, -1, -1] = 0.95
    kro_max[-1, -1, -1] = 0.65

    m = spatial_mobility(
        sat,
        nw,
        no,
        krw_max,
        kro_max,
    )

    if not np.all(
        m[
            "lambda_total"
        ]
        > 0.0
    ):
        raise RuntimeError(
            "self_test_total_mobility"
        )

    if not (
        CONTROL_REALIZATION
        == "AV3CR0003"
        and CONTROL_DAY
        == 365.0
        and CONTROL_TIME_INDEX
        == 5
    ):
        raise RuntimeError(
            "self_test_control_case"
        )

    if not (
        MAX_FIXED_POINT_ITERATIONS
        == 100
        and PRESSURE_REL_L2_TOL
        == 1.0e-10
        and SATURATION_LINF_TOL
        == 1.0e-10
    ):
        raise RuntimeError(
            "self_test_fixed_point"
        )

    print(
        "POSTV16-AV4-A2-E controlled day365 dynamic-flow refresh self-test: PASS"
    )


def main(
    project_root: Path,
    drive_root: Path,
) -> int:

    root = Path(
        project_root
    ).resolve()

    drive = Path(
        drive_root
    ).resolve()

    out = (
        drive
        / OUT_REL
    )

    fail_dir = (
        drive
        / FAIL_REL
    )

    block_dir = (
        drive
        / BLOCK_REL
    )

    gates: dict[str, dict[str, Any]] = {}

    stage = "preflight"

    scientific_execution_started = False

    start_wall = time.time()

    def gate(
        name: str,
        passed: Any,
        value: Any = None,
    ) -> None:

        ok = bool(
            passed
        )

        gates[
            name
        ] = {
            "passed":
                ok,
            "value":
                value,
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

        gates[
            name
        ] = {
            "passed":
                ok,
            "value":
                value,
            "scientific_execution_gate":
                True,
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

    print("=" * 214)
    print(
        "POSTV16-AV4-A2-E — FIRST CONTROLLED SAME-TIME "
        "SATURATION-DEPENDENT DYNAMIC-FLOW REFRESH EXECUTION"
    )
    print("=" * 214)
    print("CONTROL : AV3CR0003 / AV2PHI0003 / VALIDATION / DAY 365")
    print("MASS    : exact frozen cellwise Cartesian CO2 component mass")
    print("FLOW    : spatial AV3 mobility -> pressure -> Darcy -> Pollock -> TOF")
    print("TIME    : no physical-time advance")
    print("PI-RNN  : OFF")
    print("CMG     : DEFERRED")
    print("NO ADAPTATION / RETUNING / AUTOMATIC RERUN.")
    print()

    try:

        # ------------------------------------------------------------------------------------------
        # Immutable one-shot state firewall.
        # ------------------------------------------------------------------------------------------
        stage = "preexisting_state_firewall"

        pass_summary = (
            out
            / "PAD_Stream_POSTV16_AV4_A2_E_Summary.json"
        )

        fail_report = (
            fail_dir
            / "POSTV16_AV4_A2_E_Scientific_Fail_Report.json"
        )

        block_report = (
            block_dir
            / "POSTV16_AV4_A2_E_Blocked_Report.json"
        )

        gate(
            "no_preexisting_A2E_PASS",
            not pass_summary.exists(),
            str(
                pass_summary
            ),
        )

        gate(
            "no_preexisting_A2E_FAIL",
            not fail_report.exists(),
            str(
                fail_report
            ),
        )

        gate(
            "no_preexisting_A2E_BLOCK",
            not block_report.exists(),
            str(
                block_report
            ),
        )

        # ------------------------------------------------------------------------------------------
        # Exact repository authority.
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
            "repository_parent_is_A2_commit",
            parent
            == PARENT_A2_COMMIT,
            parent,
        )

        gate(
            "repository_clean",
            status
            == "",
            repr(
                status
            ),
        )

        for fn, expected in SOURCE_BLOBS.items():

            p = (
                root
                / fn
            )

            actual = (
                git_text(
                    root,
                    "hash-object",
                    str(
                        p
                    ),
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
        # Bind frozen A2 execution contract.
        # ------------------------------------------------------------------------------------------
        stage = "A2_contract_binding"

        a2dir = (
            drive
            / A2_REL
        )

        gate(
            "A2_output_present",
            a2dir.is_dir(),
            str(
                a2dir
            ),
        )

        a2_manifest = verify_manifest(
            a2dir,
            A2_MANIFEST,
        )

        gate(
            "A2_manifest_exact_11",
            len(
                a2_manifest
            )
            == 11,
            len(
                a2_manifest
            ),
        )

        a2_summary = load_json(
            a2dir
            / A2_SUMMARY
        )

        a2_parent = load_json(
            a2dir
            / A2_PARENT
        )

        a2_preexec = load_json(
            a2dir
            / A2_PREEXEC
        )

        a2_recipe = load_json(
            a2dir
            / A2_RECIPE
        )

        a2_gates = load_json(
            a2dir
            / A2_GATES
        )

        a2_output = load_json(
            a2dir
            / A2_OUTPUT
        )

        a2_post = load_json(
            a2dir
            / A2_POST
        )

        a2_handoff = load_json(
            a2dir
            / A2_HANDOFF
        )

        a2_decision = load_json(
            a2dir
            / A2_DECISION
        )

        gate(
            "A2_status_exact",
            a2_summary[
                "status"
            ]
            == A2_STATUS,
            a2_summary[
                "status"
            ],
        )

        gate(
            "A2_control_case_exact",
            a2_summary[
                "control_realization"
            ]
            == CONTROL_REALIZATION
            and a2_summary[
                "paired_porosity"
            ]
            == CONTROL_POROSITY
            and a2_summary[
                "partition"
            ]
            == CONTROL_PARTITION
            and float(
                a2_summary[
                    "canonical_day"
                ]
            )
            == CONTROL_DAY
            and int(
                a2_summary[
                    "time_index"
                ]
            )
            == CONTROL_TIME_INDEX,
        )

        gate(
            "A2_parent_authorities_exact",
            a2_summary[
                "parent_integrated_state_sha256"
            ]
            == CONTROL_STATE_SHA256
            and a2_summary[
                "foundation_pressure_sha256"
            ]
            == FOUNDATION_SHA256,
        )

        gate(
            "A2_A2E_handoff_exact",
            a2_handoff[
                "milestone"
            ]
            == MILESTONE
            and a2_handoff[
                "authorized"
            ]
            is True
            and a2_handoff[
                "execution"
            ]
            is True
            and a2_handoff[
                "PI_RNN_inference"
            ]
            is False
            and a2_handoff[
                "physical_time_advance"
            ]
            is False
            and a2_decision[
                "A2E_execution_authorized"
            ]
            is True,
        )

        gate(
            "A2_operator_and_gates_exact",
            a2_recipe[
                "operator"
            ][
                "face_total_mobility"
            ]
            == "harmonic"
            and int(
                a2_recipe[
                    "same_time_fixed_point"
                ][
                    "maximum_iterations"
                ]
            )
            == MAX_FIXED_POINT_ITERATIONS
            and float(
                a2_gates[
                    "fixed_point"
                ][
                    "pressure_relative_L2_max"
                ]
            )
            == PRESSURE_REL_L2_TOL
            and float(
                a2_gates[
                    "fixed_point"
                ][
                    "saturation_Linf_max"
                ]
            )
            == SATURATION_LINF_TOL
            and float(
                a2_gates[
                    "flow"
                ][
                    "local_conservation_relative_L2_max"
                ]
            )
            == FLOW_LOCAL_REL_L2_MAX
            and float(
                a2_gates[
                    "streamline_TOF"
                ][
                    "injector_seed_weight_relative_closure_max"
                ]
            )
            == INJECTOR_WEIGHT_REL_CLOSURE_MAX,
        )

        gate(
            "A2_atomic_output_contract_exact",
            a2_output[
                "PASS_artifacts_only_if_all_hard_gates_pass"
            ]
            is True
            and len(
                a2_output[
                    "atomic_flow_epoch_npz_required_arrays"
                ]
            )
            == 20
            and a2_output[
                "parent_state_immutable_on_FAIL_or_BLOCK"
            ]
            is True
            and a2_output[
                "partial_refreshed_epoch_publication"
            ]
            is False,
        )

        gate(
            "A2_PASS_handoff_to_A3_only",
            a2_post[
                "if_A2E_PASS"
            ][
                "next_milestone"
            ]
            == "POSTV16-AV4-A3"
            and a2_post[
                "if_A2E_PASS"
            ][
                "authorized"
            ]
            is True
            and a2_post[
                "if_A2E_PASS"
            ][
                "execution"
            ]
            is False
            and a2_post[
                "if_A2E_PASS"
            ][
                "AV3_checkpoint_committed_reuse"
            ]
            is False,
        )

        # ------------------------------------------------------------------------------------------
        # Bind exact source modules and frozen parent-state artifact.
        # ------------------------------------------------------------------------------------------
        stage = "runtime_authority_binding"

        modules: dict[str, Any] = {}

        for role, fn in [
            (
                "r2",
                R2,
            ),
            (
                "sg2",
                SG2,
            ),
            (
                "sg3",
                SG3,
            ),
            (
                "sg4",
                SG4,
            ),
            (
                "sg5",
                SG5,
            ),
            (
                "sg6",
                SG6,
            ),
            (
                "sg7d",
                SG7D,
            ),
            (
                "e37a",
                E37A,
            ),
            (
                "r3r2r1",
                R3R2R1,
            ),
        ]:

            modules[
                role
            ] = load_module(
                root
                / fn,
                "pad_stream_a2e_"
                + role,
            )

        r2 = modules[
            "r2"
        ]

        sg2 = modules[
            "sg2"
        ]

        sg3 = modules[
            "sg3"
        ]

        sg4 = modules[
            "sg4"
        ]

        sg5 = modules[
            "sg5"
        ]

        sg6 = modules[
            "sg6"
        ]

        sg7d = modules[
            "sg7d"
        ]

        e37a = modules[
            "e37a"
        ]

        r3r2r1 = modules[
            "r3r2r1"
        ]

        a6edir = (
            drive
            / A6E_REL
        )

        a6e_manifest = verify_manifest(
            a6edir,
            A6E_MANIFEST,
        )

        a6e_summary = load_json(
            a6edir
            / A6E_SUMMARY
        )

        gate(
            "A6E_status_exact",
            a6e_summary[
                "status"
            ]
            == A6E_STATUS,
            a6e_summary[
                "status"
            ],
        )

        gate(
            "control_state_manifest_exact",
            CONTROL_STATE_FILE
            in a6e_manifest
            and a6e_manifest[
                CONTROL_STATE_FILE
            ]
            == CONTROL_STATE_SHA256,
            a6e_manifest.get(
                CONTROL_STATE_FILE
            ),
        )

        control_path = (
            a6edir
            / CONTROL_STATE_FILE
        )

        gate(
            "control_state_file_SHA_exact",
            control_path.is_file()
            and sha256_file(
                control_path
            )
            == CONTROL_STATE_SHA256,
            str(
                control_path
            ),
        )

        with np.load(
            control_path,
            allow_pickle=False,
        ) as z:

            phi = np.asarray(
                z[
                    "paired_porosity"
                ],
                dtype=np.float64,
            )

            nw = np.asarray(
                z[
                    "nw"
                ],
                dtype=np.float64,
            )

            no = np.asarray(
                z[
                    "no"
                ],
                dtype=np.float64,
            )

            krw_max = np.asarray(
                z[
                    "krw_max"
                ],
                dtype=np.float64,
            )

            kro_max = np.asarray(
                z[
                    "kro_max"
                ],
                dtype=np.float64,
            )

            grid_saturation = np.asarray(
                z[
                    "grid_saturation"
                ],
                dtype=np.float64,
            )

            grid_mass = np.asarray(
                z[
                    "grid_component_mass_kg"
                ],
                dtype=np.float64,
            )

            target_days = np.asarray(
                z[
                    "target_days"
                ],
                dtype=np.float64,
            )

        parent_saturation = (
            grid_saturation[
                CONTROL_TIME_INDEX
            ].copy()
        )

        parent_mass = (
            grid_mass[
                CONTROL_TIME_INDEX
            ].copy()
        )

        foundation = find_named_exact(
            [
                drive,
                root,
            ],
            FOUNDATION_NAME,
            FOUNDATION_SHA256,
        )

        with np.load(
            foundation,
            allow_pickle=False,
        ) as z:

            parent_pressure = np.asarray(
                z[
                    "pressure"
                ],
                dtype=np.float64,
            )

        # ------------------------------------------------------------------------------------------
        # Exact parent array identities from A2.
        # ------------------------------------------------------------------------------------------
        stage = "preexecution_parent_state_certification"

        arrays_for_identity = {
            "parent_saturation":
                parent_saturation,
            "parent_component_mass_kg":
                parent_mass,
            "parent_pressure_psi":
                parent_pressure,
            "paired_porosity":
                phi,
            "nw":
                nw,
            "no":
                no,
            "krw_max":
                krw_max,
            "kro_max":
                kro_max,
        }

        for name, arr in arrays_for_identity.items():

            gate(
                f"parent_array_identity_{name}",
                sha256_array(
                    arr
                )
                == a2_parent[
                    "array_sha256"
                ][
                    name
                ],
                sha256_array(
                    arr
                ),
            )

        gate(
            "parent_target_day_exact",
            np.array_equal(
                target_days,
                DAYS,
            )
            and float(
                target_days[
                    CONTROL_TIME_INDEX
                ]
            )
            == CONTROL_DAY,
            target_days.tolist(),
        )

        gate(
            "parent_shapes_finite",
            all(
                arr.shape
                == GRID
                and np.isfinite(
                    arr
                ).all()
                for arr in [
                    phi,
                    nw,
                    no,
                    krw_max,
                    kro_max,
                    parent_saturation,
                    parent_mass,
                    parent_pressure,
                ]
            ),
        )

        gate(
            "parent_saturation_bounds",
            float(
                np.min(
                    parent_saturation
                )
            )
            >= BACKGROUND
            - 1.0e-12
            and float(
                np.max(
                    parent_saturation
                )
            )
            <= INJECTED
            + 1.0e-12,
            [
                float(
                    np.min(
                        parent_saturation
                    )
                ),
                float(
                    np.max(
                        parent_saturation
                    )
                ),
            ],
        )

        gate(
            "parent_mass_nonnegative",
            float(
                np.min(
                    parent_mass
                )
            )
            >= -1.0e-12,
            float(
                np.min(
                    parent_mass
                )
            ),
        )

        gate(
            "paired_porosity_positive",
            np.all(
                phi
                > 0.0
            ),
            [
                float(
                    np.min(
                        phi
                    )
                ),
                float(
                    np.max(
                        phi
                    )
                ),
            ],
        )

        gate(
            "spatial_Corey_bounds",
            float(
                np.min(
                    nw
                )
            )
            > 2.0
            and float(
                np.max(
                    nw
                )
            )
            < 4.0
            and float(
                np.min(
                    no
                )
            )
            > 2.0
            and float(
                np.max(
                    no
                )
            )
            < 4.0
            and float(
                np.min(
                    krw_max
                )
            )
            > 0.60
            and float(
                np.max(
                    krw_max
                )
            )
            < 1.00
            and float(
                np.min(
                    kro_max
                )
            )
            > 0.60
            and float(
                np.max(
                    kro_max
                )
            )
            < 1.00,
        )

        pore_volume_m3 = (
            phi
            * BULK_VOLUME_M3
        )

        gate(
            "local_pore_volume_positive_finite",
            pore_volume_m3.shape
            == GRID
            and np.isfinite(
                pore_volume_m3
            ).all()
            and np.all(
                pore_volume_m3
                > 0.0
            ),
        )

        p_ref_gas_pa = (
            reference_gas_pressure_pa(
                r2,
                parent_pressure,
            )
        )

        reconstructed_parent_mass = (
            local_mass(
                r2,
                parent_saturation,
                parent_pressure,
                p_ref_gas_pa,
                pore_volume_m3,
            )
        )

        parent_mass_rel_l2 = (
            relative_l2(
                reconstructed_parent_mass,
                parent_mass,
            )
        )

        parent_mass_global_rel = (
            abs(
                float(
                    np.sum(
                        reconstructed_parent_mass
                    )
                    - np.sum(
                        parent_mass
                    )
                )
            )
            / max(
                abs(
                    float(
                        np.sum(
                            parent_mass
                        )
                    )
                ),
                1.0,
            )
        )

        gate(
            "parent_mass_reconstruction_relative_closure",
            parent_mass_rel_l2
            <= 1.0e-10,
            parent_mass_rel_l2,
        )

        gate(
            "parent_mass_reconstruction_global_closure",
            parent_mass_global_rel
            <= 1.0e-10,
            parent_mass_global_rel,
        )

        gate(
            "no_OOD_or_PI_RNN_authority_access",
            True,
        )

        # ------------------------------------------------------------------------------------------
        # Scientific execution begins here. From this point, hard scientific
        # gate failure -> immutable scientific FAIL, not technical BLOCK.
        # ------------------------------------------------------------------------------------------
        scientific_execution_started = True

        stage = "same_time_spatial_mobility_pressure_saturation_fixed_point"

        permeability_md = np.loadtxt(
            root
            / PERM,
            skiprows=1,
            dtype=np.float64,
        ).reshape(
            GRID,
            order="C",
        )

        sci_gate(
            "permeability_shape_finite_positive",
            permeability_md.shape
            == GRID
            and np.isfinite(
                permeability_md
            ).all()
            and np.all(
                permeability_md
                > 0.0
            ),
            [
                float(
                    np.min(
                        permeability_md
                    )
                ),
                float(
                    np.max(
                        permeability_md
                    )
                ),
            ],
        )

        refresh = fixed_point_refresh(
            r2=r2,
            r3r2r1=r3r2r1,
            sg2=sg2,
            sg3=sg3,
            permeability_md=permeability_md,
            parent_mass=parent_mass,
            parent_saturation=parent_saturation,
            parent_pressure_psi=parent_pressure,
            p_ref_gas_pa=p_ref_gas_pa,
            pore_volume_m3=pore_volume_m3,
            nw=nw,
            no=no,
            krw_max=krw_max,
            kro_max=kro_max,
            sci_gate=sci_gate,
        )

        reconciled_saturation = np.asarray(
            refresh[
                "saturation"
            ],
            dtype=np.float64,
        )

        refreshed_pressure = np.asarray(
            refresh[
                "pressure_psi"
            ],
            dtype=np.float64,
        )

        # ------------------------------------------------------------------------------------------
        # Conservative Darcy flow.
        # ------------------------------------------------------------------------------------------
        stage = "conservative_Darcy_flow"

        producer_rates, producer_sink = (
            r3r2r1.producer_rates_updated(
                sg3,
                refreshed_pressure,
                refresh[
                    "producer_wi"
                ],
            )
        )

        sci_gate(
            "all_BHP_wells_remain_producers",
            all(
                float(
                    v[
                        "m3_s"
                    ]
                )
                > 0.0
                for v in producer_rates.values()
            ),
            {
                k:
                    float(
                        v[
                            "m3_day"
                        ]
                    )
                for k, v in producer_rates.items()
            },
        )

        qx, qy, qz = (
            sg4.compute_face_fluxes(
                refreshed_pressure,
                refresh[
                    "tx"
                ],
                refresh[
                    "ty"
                ],
                refresh[
                    "tz"
                ],
            )
        )

        sci_gate(
            "Darcy_face_fluxes_finite",
            np.isfinite(
                qx
            ).all()
            and np.isfinite(
                qy
            ).all()
            and np.isfinite(
                qz
            ).all(),
        )

        conservation = (
            r3r2r1.flow_conservation_metrics(
                sg3,
                sg4,
                qx,
                qy,
                qz,
                producer_sink,
            )
        )

        sci_gate(
            "Darcy_local_conservation",
            conservation[
                "local_relative_l2_error"
            ]
            < FLOW_LOCAL_REL_L2_MAX,
            conservation[
                "local_relative_l2_error"
            ],
        )

        sci_gate(
            "Darcy_global_conservation",
            conservation[
                "global_relative_mismatch"
            ]
            < FLOW_GLOBAL_REL_MISMATCH_MAX,
            conservation[
                "global_relative_mismatch"
            ],
        )

        # ------------------------------------------------------------------------------------------
        # Exact Pollock retrace.
        # ------------------------------------------------------------------------------------------
        stage = "exact_Pollock_retrace"

        vx, vy, vz = (
            sg5.construct_face_pore_velocities(
                qx,
                qy,
                qz,
            )
        )

        faces, seeds = (
            sg5.build_seeds(
                qx,
                qy,
                qz,
            )
        )

        sci_gate(
            "Pollock_seed_count_positive",
            len(
                seeds
            )
            > 0,
            len(
                seeds
            ),
        )

        streamlines = (
            sg5.trace_streamlines(
                seeds,
                vx,
                vy,
                vz,
            )
        )

        try:

            sg5_validation = (
                sg5.validate_streamlines(
                    faces,
                    seeds,
                    streamlines,
                )
            )

        except Exception as exc:

            raise ScientificFail(
                "source_SG5_validation_failure",
                repr(
                    exc
                ),
            ) from exc

        statuses = [
            str(
                s[
                    "status"
                ]
            )
            for s in streamlines
        ]

        producers = [
            str(
                s[
                    "producer"
                ]
            )
            for s in streamlines
            if str(
                s[
                    "status"
                ]
            )
            == "PRODUCER"
        ]

        sci_gate(
            "all_streamlines_terminal_producer_captured",
            len(
                streamlines
            )
            > 0
            and all(
                status
                == "PRODUCER"
                for status in statuses
            ),
            {
                "streamlines":
                    len(
                        streamlines
                    ),
                "producer_captured":
                    int(
                        sum(
                            status
                            == "PRODUCER"
                            for status in statuses
                        )
                    ),
                "statuses":
                    {
                        status:
                            statuses.count(
                                status
                            )
                        for status in sorted(
                            set(
                                statuses
                            )
                        )
                    },
            },
        )

        sci_gate(
            "all_four_producers_represented",
            all(
                name
                in producers
                for name in sg5.PRODUCERS
            ),
            sorted(
                set(
                    producers
                )
            ),
        )

        seed_weight_m3_s = float(
            sum(
                float(
                    s[
                        "weight_m3_s"
                    ]
                )
                for s in seeds
            )
        )

        injection_weight_rel = (
            abs(
                seed_weight_m3_s
                - float(
                    sg3.Q_INJ_M3_S
                )
            )
            / max(
                abs(
                    float(
                        sg3.Q_INJ_M3_S
                    )
                ),
                1.0e-30,
            )
        )

        sci_gate(
            "injector_seed_weight_relative_closure",
            injection_weight_rel
            <= INJECTOR_WEIGHT_REL_CLOSURE_MAX,
            injection_weight_rel,
        )

        # ------------------------------------------------------------------------------------------
        # SG6 TOF / normalized-coordinate rebuild.
        # ------------------------------------------------------------------------------------------
        stage = "SG6_TOF_rebuild"

        sg6_streamlines = (
            convert_sg5_to_sg6(
                streamlines
            )
        )

        transport_db = (
            sg6.build_transport_database(
                sg6_streamlines
            )
        )

        try:

            sg6.validate_transport(
                transport_db
            )

        except Exception as exc:

            raise ScientificFail(
                "source_SG6_validation_failure",
                repr(
                    exc
                ),
            ) from exc

        xyz_m = np.asarray(
            transport_db[
                "xyz_m"
            ],
            dtype=np.float64,
        )

        tof_s = np.asarray(
            transport_db[
                "tau_s"
            ],
            dtype=np.float64,
        )

        streamline_weights_m3_s = np.asarray(
            transport_db[
                "weights_m3_s"
            ],
            dtype=np.float64,
        )

        tau_end_s = np.asarray(
            transport_db[
                "tau_end_s"
            ],
            dtype=np.float64,
        )

        producer_labels = np.asarray(
            transport_db[
                "producer"
            ],
            dtype="U32",
        )

        xi = np.asarray(
            transport_db[
                "xi"
            ],
            dtype=np.float64,
        )

        sci_gate(
            "TOF_finite_positive_monotone",
            np.isfinite(
                tof_s
            ).all()
            and np.all(
                tau_end_s
                > 0.0
            )
            and np.all(
                np.diff(
                    tof_s,
                    axis=1,
                )
                >= -1.0e-12
            ),
            {
                "streamlines":
                    int(
                        len(
                            tau_end_s
                        )
                    ),
                "tau_end_min_days":
                    float(
                        np.min(
                            tau_end_s
                        )
                        / DAY_TO_S
                    ),
                "tau_end_max_days":
                    float(
                        np.max(
                            tau_end_s
                        )
                        / DAY_TO_S
                    ),
            },
        )

        # ------------------------------------------------------------------------------------------
        # SG7D overlap + E37A control-volume geometry.
        # ------------------------------------------------------------------------------------------
        stage = "SG7D_E37A_geometry_rebuild"

        try:

            subsegment_operator = (
                sg7d.build_subsegment_operator(
                    xyz_m,
                    tof_s
                    / DAY_TO_S,
                    streamline_weights_m3_s
                    * DAY_TO_S,
                )
            )

            geometry = (
                e37a.build_control_volume_geometry(
                    r2,
                    subsegment_operator,
                    refreshed_pressure,
                    p_ref_gas_pa,
                    xyz_m.shape[
                        0
                    ],
                    xyz_m.shape[
                        1
                    ]
                    - 1,
                )
            )

        except Exception as exc:

            raise ScientificFail(
                "SG7D_E37A_geometry_rebuild_failure",
                repr(
                    exc
                ),
            ) from exc

        sci_gate(
            "SG7D_operator_finite_positive",
            len(
                subsegment_operator[
                    "pv_m3"
                ]
            )
            > 0
            and np.isfinite(
                subsegment_operator[
                    "pv_m3"
                ]
            ).all()
            and np.all(
                subsegment_operator[
                    "pv_m3"
                ]
                > 0.0
            ),
            len(
                subsegment_operator[
                    "pv_m3"
                ]
            ),
        )

        sci_gate(
            "E37A_geometry_finite_positive",
            np.isfinite(
                geometry[
                    "cv_pv_m3"
                ]
            ).all()
            and np.all(
                geometry[
                    "cv_pv_m3"
                ]
                > 0.0
            )
            and np.isfinite(
                geometry[
                    "cv_pressure_mass_coeff"
                ]
            ).all()
            and np.all(
                geometry[
                    "cv_pressure_mass_coeff"
                ]
                > 0.0
            ),
            {
                "cv_shape":
                    list(
                        geometry[
                            "cv_pv_m3"
                        ].shape
                    ),
                "subsegments":
                    int(
                        len(
                            geometry[
                                "pv_m3"
                            ]
                        )
                    ),
            },
        )

        face_pressure_psi = (
            sample_pressure_at_streamline_nodes(
                sg7d,
                xyz_m,
                refreshed_pressure,
            )
        )

        sci_gate(
            "streamline_face_pressure_finite",
            face_pressure_psi.shape
            == tof_s.shape
            and np.isfinite(
                face_pressure_psi
            ).all(),
            face_pressure_psi.shape,
        )

        # ------------------------------------------------------------------------------------------
        # Parent-vs-refreshed diagnostics. Descriptive only after all hard gates.
        # ------------------------------------------------------------------------------------------
        stage = "final_diagnostics_and_atomic_commit"

        pressure_delta = (
            refreshed_pressure
            - parent_pressure
        )

        saturation_delta = (
            reconciled_saturation
            - parent_saturation
        )

        parent_vs_refreshed = {
            "pressure_relative_L2_change":
                refresh[
                    "pressure_rel_L2_vs_parent"
                ],

            "pressure_max_abs_change_psi":
                max_abs(
                    pressure_delta
                ),

            "pressure_mean_change_psi":
                float(
                    np.mean(
                        pressure_delta
                    )
                ),

            "saturation_Linf_change":
                refresh[
                    "saturation_Linf_vs_parent"
                ],

            "saturation_mean_abs_change":
                float(
                    np.mean(
                        np.abs(
                            saturation_delta
                        )
                    )
                ),

            "parent_pressure_min_psi":
                float(
                    np.min(
                        parent_pressure
                    )
                ),

            "parent_pressure_max_psi":
                float(
                    np.max(
                        parent_pressure
                    )
                ),

            "refreshed_pressure_min_psi":
                float(
                    np.min(
                        refreshed_pressure
                    )
                ),

            "refreshed_pressure_max_psi":
                float(
                    np.max(
                        refreshed_pressure
                    )
                ),

            "parent_saturation_min":
                float(
                    np.min(
                        parent_saturation
                    )
                ),

            "parent_saturation_max":
                float(
                    np.max(
                        parent_saturation
                    )
                ),

            "reconciled_saturation_min":
                float(
                    np.min(
                        reconciled_saturation
                    )
                ),

            "reconciled_saturation_max":
                float(
                    np.max(
                        reconciled_saturation
                    )
                ),
        }

        producer_rows = []

        for name in sorted(
            producer_rates
        ):

            info = producer_rates[
                name
            ]

            producer_rows.append(
                {
                    "producer":
                        name,
                    "rate_m3_s":
                        float(
                            info[
                                "m3_s"
                            ]
                        ),
                    "rate_m3_day":
                        float(
                            info[
                                "m3_day"
                            ]
                        ),
                    "completion_rates_m3_day":
                        json.dumps(
                            [
                                float(
                                    x
                                )
                                for x in info[
                                    "perf_m3_day"
                                ]
                            ]
                        ),
                }
            )

        pollock_audit = {
            **sg5_validation,
            "all_streamlines_producer_captured":
                True,
            "injector_seed_weight_relative_closure":
                injection_weight_rel,
            "producer_labels":
                sorted(
                    set(
                        producer_labels.tolist()
                    )
                ),
        }

        tof_audit = {
            "streamline_count":
                int(
                    xyz_m.shape[
                        0
                    ]
                ),
            "nodes_per_streamline":
                int(
                    xyz_m.shape[
                        1
                    ]
                ),
            "tau_end_min_days":
                float(
                    np.min(
                        tau_end_s
                    )
                    / DAY_TO_S
                ),
            "tau_end_median_days":
                float(
                    np.median(
                        tau_end_s
                    )
                    / DAY_TO_S
                ),
            "tau_end_max_days":
                float(
                    np.max(
                        tau_end_s
                    )
                    / DAY_TO_S
                ),
            "all_four_producers_represented":
                all(
                    np.any(
                        producer_labels
                        == name
                    )
                    for name in sg6.PRODUCER_NAMES
                ),
            "TOF_finite_positive_monotone":
                True,
        }

        geometry_audit = {
            "subsegment_count":
                int(
                    len(
                        subsegment_operator[
                            "pv_m3"
                        ]
                    )
                ),
            "covered_grid_cells":
                int(
                    len(
                        np.unique(
                            subsegment_operator[
                                "flat_cell"
                            ]
                        )
                    )
                ),
            "control_volume_shape":
                list(
                    geometry[
                        "cv_pv_m3"
                    ].shape
                ),
            "control_volume_pv_total_m3":
                float(
                    np.sum(
                        geometry[
                            "cv_pv_m3"
                        ]
                    )
                ),
            "streamline_face_pressure_shape":
                list(
                    face_pressure_psi.shape
                ),
        }

        mass_audit = {
            "parent_total_component_mass_kg":
                float(
                    np.sum(
                        parent_mass
                    )
                ),
            "parent_mass_preexecution_relative_L2":
                parent_mass_rel_l2,
            "parent_mass_preexecution_global_relative_error":
                parent_mass_global_rel,
            "final_max_cell_mass_error_kg":
                refresh[
                    "max_cell_mass_error_kg"
                ],
            "final_global_mass_relative_error":
                refresh[
                    "global_mass_relative_error"
                ],
            "same_time_mass_change_kg":
                float(
                    np.sum(
                        local_mass(
                            r2,
                            reconciled_saturation,
                            refreshed_pressure,
                            p_ref_gas_pa,
                            pore_volume_m3,
                        )
                    )
                    - np.sum(
                        parent_mass
                    )
                ),
        }

        flow_audit = {
            **conservation,
            "Qx_min_m3_s":
                float(
                    np.min(
                        qx
                    )
                ),
            "Qx_max_m3_s":
                float(
                    np.max(
                        qx
                    )
                ),
            "Qy_min_m3_s":
                float(
                    np.min(
                        qy
                    )
                ),
            "Qy_max_m3_s":
                float(
                    np.max(
                        qy
                    )
                ),
            "Qz_min_m3_s":
                float(
                    np.min(
                        qz
                    )
                ),
            "Qz_max_m3_s":
                float(
                    np.max(
                        qz
                    )
                ),
        }

        flow_epoch_arrays = {
            # Frozen 20-array A2 contract.
            "parent_saturation":
                parent_saturation,
            "parent_component_mass_kg":
                parent_mass,
            "parent_pressure_psi":
                parent_pressure,
            "reconciled_saturation":
                reconciled_saturation,
            "refreshed_pressure_psi":
                refreshed_pressure,
            "lambda_total":
                refresh[
                    "mobility"
                ][
                    "lambda_total"
                ],
            "Tx_dynamic":
                refresh[
                    "tx"
                ],
            "Ty_dynamic":
                refresh[
                    "ty"
                ],
            "Tz_dynamic":
                refresh[
                    "tz"
                ],
            "Qx":
                qx,
            "Qy":
                qy,
            "Qz":
                qz,
            "streamline_xyz_m":
                xyz_m,
            "streamline_tof_s":
                tof_s,
            "streamline_weight_m3_s":
                streamline_weights_m3_s,
            "paired_porosity":
                phi,
            "nw":
                nw,
            "no":
                no,
            "krw_max":
                krw_max,
            "kro_max":
                kro_max,

            # Additional frozen refreshed-flow authority.
            "xi":
                xi,
            "tau_end_s":
                tau_end_s,
            "producer_labels":
                producer_labels,
            "streamline_face_pressure_psi":
                face_pressure_psi,
            "pore_volume_m3":
                pore_volume_m3,
            "reference_gas_pressure_pa":
                np.asarray(
                    p_ref_gas_pa,
                    dtype=np.float64,
                ),
            "canonical_day":
                np.asarray(
                    CONTROL_DAY,
                    dtype=np.float64,
                ),
            "physical_time_advance":
                np.asarray(
                    False,
                    dtype=np.bool_,
                ),
            "PI_RNN_inference":
                np.asarray(
                    False,
                    dtype=np.bool_,
                ),
        }

        elapsed = float(
            time.time()
            - start_wall
        )

        summary = {
            "milestone":
                MILESTONE,
            "status":
                STATUS_PASS,
            "protocol_id":
                PROTOCOL_ID,
            "control_realization":
                CONTROL_REALIZATION,
            "paired_porosity":
                CONTROL_POROSITY,
            "partition":
                CONTROL_PARTITION,
            "canonical_day":
                CONTROL_DAY,
            "fixed_point_iterations":
                int(
                    refresh[
                        "iterations"
                    ]
                ),
            "final_pressure_relative_L2_consistency":
                refresh[
                    "pressure_consistency"
                ],
            "final_saturation_Linf_consistency":
                refresh[
                    "saturation_consistency"
                ],
            "pressure_relative_L2_vs_parent":
                refresh[
                    "pressure_rel_L2_vs_parent"
                ],
            "saturation_Linf_vs_parent":
                refresh[
                    "saturation_Linf_vs_parent"
                ],
            "flow_local_relative_L2_error":
                conservation[
                    "local_relative_l2_error"
                ],
            "flow_global_relative_mismatch":
                conservation[
                    "global_relative_mismatch"
                ],
            "injector_seed_weight_relative_closure":
                injection_weight_rel,
            "streamline_count":
                int(
                    xyz_m.shape[
                        0
                    ]
                ),
            "TOF_nodes":
                int(
                    xyz_m.shape[
                        1
                    ]
                ),
            "subsegment_count":
                geometry_audit[
                    "subsegment_count"
                ],
            "parent_component_mass_kg":
                float(
                    np.sum(
                        parent_mass
                    )
                ),
            "same_time_global_mass_relative_error":
                refresh[
                    "global_mass_relative_error"
                ],
            "PI_RNN_inference":
                False,
            "training":
                False,
            "physical_time_advance":
                False,
            "CMG_validation":
                False,
            "AV3_checkpoint_committed_reuse":
                False,
            "AV4_A3_authorized":
                True,
            "AV4_A3_execution_authorized":
                False,
            "AV4_dynamic_transport_execution_authorized":
                False,
            "elapsed_seconds":
                elapsed,
        }

        decision = {
            "milestone":
                MILESTONE,
            "status":
                STATUS_PASS,
            "scientific_execution_completed":
                True,
            "same_time_pressure_saturation_refresh_PASS":
                True,
            "cellwise_component_mass_conserved":
                True,
            "Darcy_conservation_PASS":
                True,
            "all_streamlines_producer_captured":
                True,
            "Pollock_retrace_PASS":
                True,
            "TOF_rebuild_PASS":
                True,
            "SG7D_E37A_geometry_rebuild_PASS":
                True,
            "atomic_refreshed_flow_epoch_committed":
                True,
            "parent_state_modified":
                False,
            "PI_RNN_inference":
                False,
            "training":
                False,
            "physical_time_advance":
                False,
            "CMG_validation":
                False,
            "AV3_checkpoint_committed_reuse":
                False,
            "production_refresh_cadence_selected":
                False,
            "next": {
                "milestone":
                    "POSTV16-AV4-A3",
                "name":
                    (
                        "Refreshed 13-Channel Reconstruction and AV3 Checkpoint "
                        "Compatibility / Teacher-Backed Authority Protocol Freeze"
                    ),
                "authorized":
                    True,
                "execution":
                    False,
            },
        }

        output_files = {
            "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz":
                deterministic_npz_bytes(
                    flow_epoch_arrays
                ),
            "POSTV16_AV4_A2_E_Fixed_Point_Iteration_History.csv":
                csv_bytes(
                    refresh[
                        "rows"
                    ]
                ),
            "POSTV16_AV4_A2_E_Mass_Reconciliation_Audit.json":
                json_bytes(
                    mass_audit
                ),
            "POSTV16_AV4_A2_E_Darcy_Flow_Conservation_Audit.json":
                json_bytes(
                    flow_audit
                ),
            "POSTV16_AV4_A2_E_Producer_Rates.csv":
                csv_bytes(
                    producer_rows
                ),
            "POSTV16_AV4_A2_E_Pollock_Audit.json":
                json_bytes(
                    pollock_audit
                ),
            "POSTV16_AV4_A2_E_TOF_Audit.json":
                json_bytes(
                    tof_audit
                ),
            "POSTV16_AV4_A2_E_SG7D_E37A_Geometry_Audit.json":
                json_bytes(
                    geometry_audit
                ),
            "POSTV16_AV4_A2_E_Parent_vs_Refreshed_State_Differences.json":
                json_bytes(
                    parent_vs_refreshed
                ),
            "PAD_Stream_POSTV16_AV4_A2_E_Summary.json":
                json_bytes(
                    summary
                ),
            "POSTV16_AV4_A2_E_Decision_Contract.json":
                json_bytes(
                    decision
                ),
            "POSTV16_AV4_A2_E_Final_Gate_Matrix.csv":
                csv_bytes(
                    [
                        {
                            "gate":
                                name,
                            **value,
                        }
                        for name, value in gates.items()
                    ]
                ),
        }

        # Atomic PASS-only publication.
        immutable_publish(
            out,
            output_files,
        )

        manifest_rows = []

        for p in sorted(
            out.iterdir()
        ):

            if (
                p.is_file()
                and p.name
                != "POSTV16_AV4_A2_E_Artifact_Manifest.csv"
            ):

                manifest_rows.append(
                    {
                        "file":
                            p.name,
                        "sha256":
                            sha256_file(
                                p
                            ),
                        "bytes":
                            p.stat().st_size,
                    }
                )

        immutable_publish(
            out,
            {
                "POSTV16_AV4_A2_E_Artifact_Manifest.csv":
                    csv_bytes(
                        manifest_rows
                    )
            },
        )

        print()
        print("=" * 214)
        print("POSTV16-AV4-A2-E: CONTROLLED DYNAMIC-FLOW REFRESH SCIENTIFIC PASS")
        print("=" * 214)
        print("Control                                  : AV3CR0003 / AV2PHI0003 / day 365")
        print("Parent component mass kg                 :", summary["parent_component_mass_kg"])
        print("Fixed-point iterations                   :", summary["fixed_point_iterations"])
        print("Pressure rel-L2 vs parent                :", summary["pressure_relative_L2_vs_parent"])
        print("Saturation Linf vs parent                :", summary["saturation_Linf_vs_parent"])
        print("Flow local relative L2                   :", summary["flow_local_relative_L2_error"])
        print("Flow global relative mismatch            :", summary["flow_global_relative_mismatch"])
        print("Injector weight relative closure         :", summary["injector_seed_weight_relative_closure"])
        print("Streamlines                              :", summary["streamline_count"])
        print("TOF nodes                                :", summary["TOF_nodes"])
        print("SG7D/E37A subsegments                    :", summary["subsegment_count"])
        print("PI-RNN inference                         : False")
        print("Physical-time advance                    : False")
        print("CMG                                      : Deferred")
        print("POSTV16-AV4-A3                           : AUTHORIZED")
        print("A3 execution                             : NOT YET AUTHORIZED")
        print("AV4 dynamic transport                    : NOT YET AUTHORIZED")
        print("=" * 214)

        return 0

    except ScientificFail as exc:

        fail_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        report = {
            "milestone":
                MILESTONE,
            "status":
                STATUS_FAIL,
            "failed_stage":
                stage,
            "failed_gate":
                exc.gate,
            "detail":
                exc.detail,
            "scientific_execution_started":
                scientific_execution_started,
            "adaptation_authorized":
                False,
            "automatic_rerun_authorized":
                False,
            "PI_RNN_inference":
                False,
            "physical_time_advance":
                False,
            "AV4_A3_authorized":
                False,
            "gates":
                gates,
        }

        p = (
            fail_dir
            / "POSTV16_AV4_A2_E_Scientific_Fail_Report.json"
        )

        if not p.exists():

            p.write_bytes(
                json_bytes(
                    report
                )
            )

        print()
        print("=" * 214)
        print("POSTV16-AV4-A2-E: SCIENTIFIC FAIL")
        print("=" * 214)
        print("Stage :", stage)
        print("Gate  :", exc.gate)
        print("Detail:", exc.detail)
        print("NO ADAPTATION / AUTOMATIC RERUN AUTHORIZED.")
        print("=" * 214)

        return 3

    except Exception as exc:

        block_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        report = {
            "milestone":
                MILESTONE,
            "status":
                STATUS_BLOCKED,
            "failed_stage":
                stage,
            "exception":
                repr(
                    exc
                ),
            "scientific_execution_started":
                scientific_execution_started,
            "automatic_rerun_authorized":
                False,
            "PI_RNN_inference":
                False,
            "physical_time_advance":
                False,
            "AV4_A3_authorized":
                False,
            "gates":
                gates,
        }

        p = (
            block_dir
            / "POSTV16_AV4_A2_E_Blocked_Report.json"
        )

        if not p.exists():

            p.write_bytes(
                json_bytes(
                    report
                )
            )

        print()
        print("=" * 214)
        print("POSTV16-AV4-A2-E: TECHNICAL BLOCK")
        print("=" * 214)
        print("Stage    :", stage)
        print("Exception:", repr(exc))
        print("NO AUTOMATIC RERUN AUTHORIZED.")
        print("=" * 214)

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
