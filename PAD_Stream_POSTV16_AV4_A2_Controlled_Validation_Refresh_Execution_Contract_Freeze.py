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
from pathlib import Path
from typing import Any

import numpy as np


MILESTONE = "POSTV16-AV4-A2"

PROTOCOL_ID = (
    "POSTV16_AV4_A2_AV3CR0003_DAY365_CONTROLLED_SAME_TIME_"
    "SPATIAL_MOBILITY_PRESSURE_REFRESH_EXECUTION_CONTRACT_V1"
)

STATUS_PASS = (
    "AV4A2_AV3CR0003_DAY365_CONTROLLED_SAME_TIME_DYNAMIC_FLOW_REFRESH_"
    "PARENT_STATE_AND_EXECUTION_CONTRACT_PROSPECTIVELY_FROZEN_NO_EXECUTION"
)

STATUS_BLOCKED = "AV4A2_CONTROLLED_REFRESH_EXECUTION_CONTRACT_FREEZE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

PARENT_A1_COMMIT = "c621e750f3f3fdb2281969d7d0ca969420e99c7e"

A1_STATUS = (
    "AV4A1_SPATIAL_TOTAL_MOBILITY_PRESSURE_REFRESH_OPERATOR_MASS_CONSERVATIVE_"
    "SAME_TIME_RECONCILIATION_AND_FLOW_EPOCH_CONTRACT_PROSPECTIVELY_FROZEN_NO_EXECUTION"
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
DAYS = np.asarray(
    [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0],
    dtype=np.float64,
)

DX_M = 6.096
DY_M = 6.096
DZ_M = 1.2192
CELL_BULK_VOLUME_M3 = DX_M * DY_M * DZ_M

BACKGROUND = 0.20
INJECTED = 0.80
MAX_SG = 0.60

FOUNDATION_NAME = "V16A_Foundation_Case_0001.npz"
FOUNDATION_SHA256 = "4239e412ca6e2780f108c8eb1b0252e80a56be305bce48cc58e50d6140b86acc"

# --------------------------------------------------------------------------------------------------
# Exact repository authorities.
# --------------------------------------------------------------------------------------------------

A1 = "PAD_Stream_POSTV16_AV4_A1_Spatial_Mobility_Pressure_Refresh_and_Flow_Epoch_Contract_Freeze.py"
A1_BLOB = "9c48fd564be748295576264a9f9c6ad67327fdd2"

A6E = "PAD_Stream_POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution.py"
A6E_BLOB = "e3dcb0aa9354c399904f7f0e830b6a1fddd78987"

R7E = "PAD_Stream_POSTV16_AV1_D_R7_R7E_Frozen_Horizontal_Face_Halo_Occupancy_Domain_Execution.py"
R7E_BLOB = "9f99d9dcab649ba7ac911ad09ad79b4e0eb2ecc8"

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

R3R4 = "PAD_Stream_V16E41R3R4_Controlled_Same_Parent_Mass_Conservative_Refreshed_Flow_Transition_Validation.py"
R3R4_BLOB = "c4fdaf1e5886e2ba2618636406d63aa190152856"

PERM = "SGSIM_50x50x15_PERM_MD.csv"
PERM_BLOB = "317dd47d458bc6f880c2e3dc4ec1f69eeb0dd314"

SOURCE_BLOBS = {
    A1: A1_BLOB,
    A6E: A6E_BLOB,
    R7E: R7E_BLOB,
    R2: R2_BLOB,
    SG2: SG2_BLOB,
    SG3: SG3_BLOB,
    SG4: SG4_BLOB,
    SG5: SG5_BLOB,
    SG6: SG6_BLOB,
    SG7D: SG7D_BLOB,
    E37A: E37A_BLOB,
    R3R4: R3R4_BLOB,
    PERM: PERM_BLOB,
}

# --------------------------------------------------------------------------------------------------
# Drive authorities.
# --------------------------------------------------------------------------------------------------

BASE_AV4 = (
    Path("post_v16")
    / RID
    / "POSTV16_AV4_Dynamic_Flow_Coupling"
)

A1_REL = (
    BASE_AV4
    / "POSTV16_AV4_A1_Spatial_Mobility_Pressure_Refresh_and_Flow_Epoch_Contract_Freeze"
)

A1_SUMMARY = "PAD_Stream_POSTV16_AV4_A1_Summary.json"
A1_OPERATOR = "POSTV16_AV4_A1_Spatial_Mobility_Pressure_Operator_Contract.json"
A1_RECON = "POSTV16_AV4_A1_Mass_Conservative_SameTime_Reconciliation_Contract.json"
A1_FLOW = "POSTV16_AV4_A1_Flow_Epoch_Validation_and_Rollback_Contract.json"
A1_STATE = "POSTV16_AV4_A1_Refresh_State_Machine_and_Cadence_Policy.json"
A1_FIREWALL = "POSTV16_AV4_A1_13Channel_Reconstruction_and_Checkpoint_Authority_Firewall.json"
A1_HANDOFF = "POSTV16_AV4_A1_A2_Handoff_Contract.json"
A1_DECISION = "POSTV16_AV4_A1_Decision_Contract.json"
A1_MANIFEST = "POSTV16_AV4_A1_Artifact_Manifest.csv"

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

CONTROL_STATE_FILE = (
    "POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
)

OUT_REL = (
    BASE_AV4
    / "POSTV16_AV4_A2_Controlled_Validation_Refresh_Execution_Contract_Freeze"
)

BLOCK_REL = BASE_AV4 / "POSTV16_AV4_A2_BLOCKED"


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sha256_array(a: np.ndarray) -> str:
    arr = np.ascontiguousarray(np.asarray(a))
    h = hashlib.sha256()
    h.update(str(arr.dtype).encode("utf-8"))
    h.update(repr(arr.shape).encode("utf-8"))
    h.update(arr.tobytes(order="C"))
    return h.hexdigest()


def git_text(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


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
        for key in row:
            if key not in fields:
                fields.append(key)

    s = io.StringIO(newline="")
    w = csv.DictWriter(
        s,
        fieldnames=fields,
        lineterminator="\n",
    )
    w.writeheader()
    w.writerows(rows)

    return s.getvalue().encode("utf-8")


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)

    for name, data in files.items():
        p = out / name

        if p.exists() and p.read_bytes() != data:
            raise GateError("existing_output_differs:" + name)

        if not p.exists():
            p.write_bytes(data)


def find_named_exact(roots: list[Path], name: str, sha256: str) -> Path:

    candidates: list[Path] = []

    for root in roots:

        if not root.exists():
            continue

        direct = root / name

        if direct.is_file():
            candidates.append(direct)

        for p in root.rglob(name):
            if p.is_file():
                candidates.append(p)

    seen = set()

    for p in candidates:

        rp = str(p.resolve())

        if rp in seen:
            continue

        seen.add(rp)

        if sha256_file(p) == sha256:
            return p

    raise GateError(
        f"exact_file_not_found:{name}:{sha256}"
    )


def self_test() -> None:

    assert CONTROL_REALIZATION == "AV3CR0003"
    assert CONTROL_POROSITY == "AV2PHI0003"
    assert CONTROL_PARTITION == "VALIDATION"
    assert CONTROL_DAY == 365.0
    assert CONTROL_TIME_INDEX == 5
    assert DAYS[CONTROL_TIME_INDEX] == CONTROL_DAY

    assert GRID == (15, 50, 50)
    assert BACKGROUND == 0.20
    assert INJECTED == 0.80

    assert len(SOURCE_BLOBS) == 13

    print(
        "POSTV16-AV4-A2 controlled-refresh execution-contract self-test: PASS"
    )


def main(project_root: Path, drive_root: Path) -> int:

    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()

    out = drive / OUT_REL
    blocked = drive / BLOCK_REL

    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"

    def gate(name: str, passed: Any, value: Any = None) -> None:

        ok = bool(passed)

        gates[name] = {
            "passed": ok,
            "value": value,
        }

        print(
            f"[{'PASS' if ok else 'FAIL'}] {name}"
            + (f" — {value}" if value is not None else "")
        )

        if not ok:
            raise GateError(name)

    print("=" * 214)
    print(
        "POSTV16-AV4-A2 — CONTROLLED VALIDATION-REALIZATION DAY-365 "
        "SAME-TIME DYNAMIC-FLOW REFRESH EXECUTION CONTRACT FREEZE"
    )
    print("=" * 214)
    print("DESIGN / FREEZE ONLY.")
    print("NO PRESSURE SOLVE / DARCY-FLUX RECOMPUTATION.")
    print("NO POLLOCK RETRACE / TOF REBUILD.")
    print("NO EOS FIXED-POINT EXECUTION.")
    print("NO PI-RNN INFERENCE / TRAINING.")
    print("NO PHYSICAL-TIME ADVANCE.")
    print("NO MAPBACK / LP.")
    print("NO CMG.")
    print()

    try:

        # ------------------------------------------------------------------------------------------
        # Repository authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"

        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate(
            "repository_parent_is_A1_commit",
            parent == PARENT_A1_COMMIT,
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
                git_text(root, "hash-object", str(p))
                if p.is_file()
                else "missing"
            )

            gate(
                f"{Path(fn).stem}_git_blob_exact",
                actual == expected,
                actual,
            )

        # ------------------------------------------------------------------------------------------
        # Bind A1 final PASS contract.
        # ------------------------------------------------------------------------------------------
        stage = "A1_authority_binding"

        a1dir = drive / A1_REL

        gate(
            "A1_output_present",
            a1dir.is_dir(),
            str(a1dir),
        )

        a1_manifest = verify_manifest(
            a1dir,
            A1_MANIFEST,
        )

        gate(
            "A1_manifest_exact_10",
            len(a1_manifest) == 10,
            len(a1_manifest),
        )

        a1_summary = load_json(a1dir / A1_SUMMARY)
        a1_operator = load_json(a1dir / A1_OPERATOR)
        a1_recon = load_json(a1dir / A1_RECON)
        a1_flow = load_json(a1dir / A1_FLOW)
        a1_state = load_json(a1dir / A1_STATE)
        a1_firewall = load_json(a1dir / A1_FIREWALL)
        a1_handoff = load_json(a1dir / A1_HANDOFF)
        a1_decision = load_json(a1dir / A1_DECISION)

        gate(
            "A1_status_exact",
            a1_summary["status"] == A1_STATUS,
            a1_summary["status"],
        )

        gate(
            "A1_A2_control_case_exact",
            a1_state[
                "A2_controlled_validation"
            ][
                "realization"
            ]
            == CONTROL_REALIZATION
            and a1_state[
                "A2_controlled_validation"
            ][
                "paired_porosity"
            ]
            == CONTROL_POROSITY
            and a1_state[
                "A2_controlled_validation"
            ][
                "partition"
            ]
            == CONTROL_PARTITION
            and float(
                a1_state[
                    "A2_controlled_validation"
                ][
                    "canonical_day"
                ]
            )
            == CONTROL_DAY,
        )

        gate(
            "A1_eight_item_A2_contract_exact",
            len(
                a1_handoff[
                    "A2_must_execute"
                ]
            )
            == 8,
            len(
                a1_handoff[
                    "A2_must_execute"
                ]
            ),
        )

        gate(
            "A1_A2_authorized_execution_false",
            a1_decision[
                "AV4_A2_authorized"
            ]
            is True
            and a1_decision[
                "AV4_A2_execution_authorized"
            ]
            is False,
        )

        gate(
            "A1_operator_core_exact",
            a1_operator[
                "face_mobility"
            ][
                "rule"
            ]
            == "HARMONIC_TOTAL_MOBILITY"
            and float(
                a1_operator[
                    "reference_mobility"
                ][
                    "lambda_ref"
                ]
            )
            == 2000.0
            and float(
                a1_operator[
                    "gravity"
                ][
                    "density_kg_m3"
                ]
            )
            == 1020.0,
        )

        gate(
            "A1_fixed_point_core_exact",
            a1_recon[
                "direct_Picard"
            ]
            is True
            and a1_recon[
                "under_relaxation"
            ]
            is False
            and int(
                a1_recon[
                    "maximum_iterations"
                ]
            )
            == 100
            and float(
                a1_recon[
                    "pressure_relative_L2_tolerance"
                ]
            )
            == 1.0e-10
            and float(
                a1_recon[
                    "saturation_Linf_tolerance"
                ]
            )
            == 1.0e-10,
        )

        gate(
            "A1_checkpoint_firewall_exact",
            a1_firewall[
                "AV3_checkpoint_status_in_AV4"
            ]
            == "NOT_AUTHORIZED_FOR_COMMITTED_DYNAMIC_FLOW_TRANSPORT"
            and a1_firewall[
                "A2_operator_validation_PI_RNN_inference"
            ]
            is False,
        )

        # ------------------------------------------------------------------------------------------
        # Bind exact AV3-A6-E control-state artifact.
        # ------------------------------------------------------------------------------------------
        stage = "parent_state_authority_binding"

        a6edir = drive / A6E_REL

        gate(
            "A6E_output_present",
            a6edir.is_dir(),
            str(a6edir),
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
            "A6E_36_state_authority_exact",
            int(
                a6e_summary[
                    "integrated_states"
                ]
            )
            == 36,
            a6e_summary[
                "integrated_states"
            ],
        )

        gate(
            "control_state_manifested",
            CONTROL_STATE_FILE
            in a6e_manifest,
            CONTROL_STATE_FILE,
        )

        control_path = (
            a6edir
            / CONTROL_STATE_FILE
        )

        gate(
            "control_state_SHA256_manifest_exact",
            control_path.is_file()
            and sha256_file(
                control_path
            )
            == a6e_manifest[
                CONTROL_STATE_FILE
            ],
            sha256_file(
                control_path
            )
            if control_path.is_file()
            else "missing",
        )

        with np.load(
            control_path,
            allow_pickle=False,
        ) as z:

            required_arrays = {
                "paired_porosity",
                "nw",
                "no",
                "krw_max",
                "kro_max",
                "grid_saturation",
                "grid_component_mass_kg",
                "S0_nodes",
                "H1_nodes",
                "D1_nodes",
                "checkpoint_sha256",
                "target_days",
            }

            gate(
                "control_state_required_arrays_exact",
                required_arrays.issubset(
                    set(
                        z.files
                    )
                ),
                sorted(
                    z.files
                ),
            )

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

            grid_sat = np.asarray(
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

            checkpoint_sha = str(
                np.asarray(
                    z[
                        "checkpoint_sha256"
                    ]
                ).reshape(
                    -1
                )[
                    0
                ]
            )

            s0_nodes = np.asarray(
                z[
                    "S0_nodes"
                ],
                dtype=np.int64,
            )

            h1_nodes = np.asarray(
                z[
                    "H1_nodes"
                ],
                dtype=np.int64,
            )

            d1_nodes = np.asarray(
                z[
                    "D1_nodes"
                ],
                dtype=np.int64,
            )

        gate(
            "control_state_shapes_exact",
            phi.shape == GRID
            and nw.shape == GRID
            and no.shape == GRID
            and krw_max.shape == GRID
            and kro_max.shape == GRID
            and grid_sat.shape
            == (
                9,
                15,
                50,
                50,
            )
            and grid_mass.shape
            == (
                9,
                15,
                50,
                50,
            ),
            {
                "phi":
                    phi.shape,
                "grid_saturation":
                    grid_sat.shape,
                "grid_component_mass":
                    grid_mass.shape,
            },
        )

        gate(
            "control_target_days_exact",
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

        parent_saturation = grid_sat[
            CONTROL_TIME_INDEX
        ].copy()

        parent_component_mass = grid_mass[
            CONTROL_TIME_INDEX
        ].copy()

        gate(
            "parent_saturation_finite_bounded",
            np.isfinite(
                parent_saturation
            ).all()
            and float(
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
            "parent_component_mass_finite_nonnegative",
            np.isfinite(
                parent_component_mass
            ).all()
            and float(
                np.min(
                    parent_component_mass
                )
            )
            >= -1.0e-12,
            [
                float(
                    np.min(
                        parent_component_mass
                    )
                ),
                float(
                    np.sum(
                        parent_component_mass
                    )
                ),
            ],
        )

        gate(
            "parent_checkpoint_sha_present",
            len(
                checkpoint_sha
            )
            == 64,
            checkpoint_sha,
        )

        # ------------------------------------------------------------------------------------------
        # Bind exact parent pressure authority.
        # ------------------------------------------------------------------------------------------
        stage = "parent_pressure_authority_binding"

        foundation = find_named_exact(
            [
                root,
                drive,
            ],
            FOUNDATION_NAME,
            FOUNDATION_SHA256,
        )

        gate(
            "foundation_pressure_authority_SHA_exact",
            sha256_file(
                foundation
            )
            == FOUNDATION_SHA256,
            str(
                foundation
            ),
        )

        with np.load(
            foundation,
            allow_pickle=False,
        ) as z:

            gate(
                "foundation_pressure_array_present",
                "pressure"
                in z.files,
                sorted(
                    z.files
                ),
            )

            parent_pressure = np.asarray(
                z[
                    "pressure"
                ],
                dtype=np.float64,
            )

        gate(
            "parent_pressure_shape_finite",
            parent_pressure.shape
            == GRID
            and np.isfinite(
                parent_pressure
            ).all(),
            parent_pressure.shape,
        )

        # ------------------------------------------------------------------------------------------
        # Freeze exact extracted parent-state identity.
        # ------------------------------------------------------------------------------------------
        stage = "parent_state_identity_freeze"

        parent_identity = {
            "milestone":
                MILESTONE,

            "control_realization":
                CONTROL_REALIZATION,

            "paired_porosity":
                CONTROL_POROSITY,

            "partition":
                CONTROL_PARTITION,

            "canonical_day":
                CONTROL_DAY,

            "time_index":
                CONTROL_TIME_INDEX,

            "source_integrated_state_file":
                CONTROL_STATE_FILE,

            "source_integrated_state_sha256":
                a6e_manifest[
                    CONTROL_STATE_FILE
                ],

            "source_foundation_pressure_file":
                FOUNDATION_NAME,

            "source_foundation_pressure_sha256":
                FOUNDATION_SHA256,

            "array_sha256": {
                "parent_saturation":
                    sha256_array(
                        parent_saturation
                    ),

                "parent_component_mass_kg":
                    sha256_array(
                        parent_component_mass
                    ),

                "parent_pressure_psi":
                    sha256_array(
                        parent_pressure
                    ),

                "paired_porosity":
                    sha256_array(
                        phi
                    ),

                "nw":
                    sha256_array(
                        nw
                    ),

                "no":
                    sha256_array(
                        no
                    ),

                "krw_max":
                    sha256_array(
                        krw_max
                    ),

                "kro_max":
                    sha256_array(
                        kro_max
                    ),

                "S0_nodes":
                    sha256_array(
                        s0_nodes
                    ),

                "H1_nodes":
                    sha256_array(
                        h1_nodes
                    ),

                "D1_nodes":
                    sha256_array(
                        d1_nodes
                    ),
            },

            "parent_component_mass_total_kg":
                float(
                    np.sum(
                        parent_component_mass
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

            "local_pore_volume_definition":
                "paired_porosity * 6.096m * 6.096m * 1.2192m",

            "local_pore_volume_total_m3":
                float(
                    np.sum(
                        phi
                        * CELL_BULK_VOLUME_M3
                    )
                ),
        }

        # ------------------------------------------------------------------------------------------
        # Freeze parent-state pre-execution certification.
        # ------------------------------------------------------------------------------------------

        preexecution = {
            "must_pass_before_first_pressure_matrix_assembly": [
                "source integrated-state SHA256 exact",
                "foundation pressure SHA256 exact",
                "control day index exactly 5 and target day exactly 365.0",
                "all parent/constitutive arrays exact shape (15,50,50)",
                "parent saturation finite and bounded [0.20,0.80]",
                "parent component mass finite and nonnegative",
                "paired porosity finite positive and local PV finite positive",
                "spatial nw/no strictly inside (2,4)",
                "spatial krw_max/kro_max strictly inside (0.60,1.00)",
                "reconstruct parent component mass from parent saturation + parent pressure + local PV + frozen R2 EOS",
                "reconstructed-vs-stored parent component mass relative closure <=1e-10",
                "no AV3CR0004/OOD artifacts opened",
                "no PI-RNN checkpoint or predictor input opened",
            ],

            "parent_mass_authority":
                "stored AV3-A6-E day-365 Cartesian component-mass array",

            "EOS_reconstruction_role":
                "pre-execution identity/certification only; stored mass remains primary conserved authority",

            "failure_before_pressure_assembly":
                "TECHNICAL_OR_AUTHORITY_BLOCK_NO_DYNAMIC_FLOW_EXECUTION",
        }

        # ------------------------------------------------------------------------------------------
        # Freeze exact A2-E scientific execution recipe.
        # ------------------------------------------------------------------------------------------

        execution_recipe = {
            "milestone":
                "POSTV16-AV4-A2-E",

            "control_case": {
                "corey_realization":
                    CONTROL_REALIZATION,

                "paired_porosity":
                    CONTROL_POROSITY,

                "partition":
                    CONTROL_PARTITION,

                "canonical_day":
                    CONTROL_DAY,

                "physical_time_advance":
                    False,

                "transport_step":
                    False,

                "PI_RNN_inference":
                    False,
            },

            "operator": {
                "cell_total_mobility":
                    (
                        "AV3 spatial nw/no/krw_max/kro_max + A1 Se/kr/mobility law"
                    ),

                "face_total_mobility":
                    "harmonic",

                "dynamic_transmissibility":
                    "T_SG3_reference*(lambda_face/2000)",

                "dynamic_producer_WI":
                    "WI_SG3_reference*(lambda_well_cell/2000)",

                "gravity_density_kg_m3":
                    1020.0,

                "injector":
                    "frozen SG3 fixed-rate control",

                "producers":
                    "frozen SG3 2000 psi BHP control",
            },

            "same_time_fixed_point": {
                "initial_saturation":
                    "exact frozen parent saturation",

                "initial_pressure":
                    "exact frozen parent pressure",

                "primary_conserved_quantity":
                    "exact frozen cellwise parent CO2 component mass",

                "method":
                    "direct undamped Picard",

                "maximum_iterations":
                    100,

                "pressure_relative_L2_tolerance":
                    1.0e-10,

                "saturation_Linf_tolerance":
                    1.0e-10,

                "pressure_linear_relative_residual_max":
                    1.0e-8,

                "final_consistency_solve":
                    True,

                "hidden_damping":
                    False,

                "mass_clipping":
                    False,

                "cell_mass_redistribution":
                    False,

                "R7D_halo_during_refresh":
                    False,
            },

            "post_fixed_point_rebuild": [
                "conservative Darcy Qx/Qy/Qz",
                "cellwise local/global flow-conservation audit",
                "exact SG5 Pollock retrace using the frozen SG5 seeding/tracing implementation",
                "producer-capture audit and injector streamline-weight closure",
                "SG6 physical TOF / normalized coordinate rebuild",
                "SG7D overlap rebuild",
                "E37A control-volume geometry rebuild",
                "streamline face-pressure rebuild",
            ],

            "explicitly_not_executed_in_A2E": [
                "PI-RNN inference",
                "transport time advance",
                "B1 transport projection",
                "R7D transport/mapback halo reconciliation",
                "AV3 checkpoint compatibility evaluation",
                "training",
                "CMG",
            ],
        }

        # ------------------------------------------------------------------------------------------
        # Freeze PASS/FAIL/BLOCK scientific gates.
        # ------------------------------------------------------------------------------------------

        gates_contract = {
            "preexecution": {
                "parent_mass_reconstruction_relative_closure_max":
                    1.0e-10,

                "parent_state_shapes_and_finite":
                    True,

                "OOD_access":
                    False,

                "PI_RNN_access":
                    False,
            },

            "fixed_point": {
                "converged_within_iterations":
                    100,

                "pressure_relative_L2_max":
                    1.0e-10,

                "saturation_Linf_max":
                    1.0e-10,

                "pressure_linear_relative_residual_max":
                    1.0e-8,

                "same_time_cellwise_mass_error":
                    (
                        "max_abs <= max(1e-8 kg, "
                        "1e-10*max(max(parent_cell_mass),1 kg))"
                    ),

                "same_time_global_mass_relative_error_max":
                    1.0e-10,

                "saturation_bounds":
                    [0.20, 0.80],
            },

            "flow": {
                "face_fluxes_finite":
                    True,

                "local_conservation_relative_L2_max":
                    1.0e-8,

                "global_conservation_relative_mismatch_max":
                    1.0e-8,

                "well_rates_finite":
                    True,
            },

            "streamline_TOF": {
                "all_streamlines_terminal_producer_captured":
                    True,

                "injector_seed_weight_relative_closure_max":
                    1.0e-10,

                "TOF_finite_positive_monotone":
                    True,

                "all_four_producers_represented":
                    True,

                "SG7D_E37A_geometry_finite":
                    True,
            },

            "classification": {
                "valid_execution_hard_gate_failure":
                    "SCIENTIFIC_FAIL_NO_ADAPTATION_OR_AUTOMATIC_RERUN",

                "schema_IO_missing_authority_or_unintended_exception":
                    "TECHNICAL_BLOCK_NO_AUTOMATIC_RERUN",

                "PASS":
                    "ATOMIC_REFRESHED_FLOW_EPOCH_COMMITTED",
            },
        }

        # ------------------------------------------------------------------------------------------
        # Freeze atomic A2-E output schema.
        # ------------------------------------------------------------------------------------------

        output_contract = {
            "PASS_artifacts_only_if_all_hard_gates_pass": True,

            "atomic_flow_epoch_npz_required_arrays": [
                "parent_saturation",
                "parent_component_mass_kg",
                "parent_pressure_psi",
                "reconciled_saturation",
                "refreshed_pressure_psi",
                "lambda_total",
                "Tx_dynamic",
                "Ty_dynamic",
                "Tz_dynamic",
                "Qx",
                "Qy",
                "Qz",
                "streamline_xyz_m",
                "streamline_tof_s",
                "streamline_weight_m3_s",
                "paired_porosity",
                "nw",
                "no",
                "krw_max",
                "kro_max",
            ],

            "required_audits": [
                "fixed-point iteration history",
                "cellwise/global mass reconciliation",
                "Darcy local/global conservation",
                "producer rates",
                "Pollock capture/weight closure",
                "TOF validation",
                "SG7D/E37A geometry validation",
                "parent-vs-refreshed state differences",
            ],

            "parent_state_immutable_on_FAIL_or_BLOCK": True,

            "partial_refreshed_epoch_publication": False,
        }

        # ------------------------------------------------------------------------------------------
        # Freeze post-A2-E handoff.
        # ------------------------------------------------------------------------------------------

        next_contract = {
            "if_A2E_PASS": {
                "next_milestone":
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

                "AV3_checkpoint_committed_reuse":
                    False,
            },

            "if_A2E_SCIENTIFIC_FAIL": {
                "adaptation_authorized":
                    False,

                "automatic_rerun":
                    False,

                "A3_authorized":
                    False,
            },

            "if_A2E_TECHNICAL_BLOCK": {
                "automatic_rerun":
                    False,

                "closure_required":
                    True,

                "A3_authorized":
                    False,
            },
        }

        boundaries = {
            "A2_freeze_execution": {
                "pressure_solve":
                    False,

                "Darcy_flux_recompute":
                    False,

                "Pollock_retrace":
                    False,

                "TOF_recompute":
                    False,

                "EOS_fixed_point":
                    False,

                "PI_RNN_inference":
                    False,

                "training":
                    False,

                "CMG":
                    False,
            },

            "claims_not_authorized": [
                "AV4 dynamic flow has passed",
                "the A1 operator is accurate on arbitrary AV3 states",
                "the AV3 checkpoint is compatible with refreshed flow",
                "production refresh cadence is calibrated",
                "dynamic-flow coupling improves plume fidelity",
                "external CMG validates AV4",
            ],
        }

        handoff = {
            "milestone":
                "POSTV16-AV4-A2-E",

            "name":
                (
                    "Controlled AV3CR0003 Day-365 Same-Time Spatial-Mobility "
                    "Pressure/Saturation Refresh Execution"
                ),

            "authorized":
                True,

            "execution":
                True,

            "control_realization":
                CONTROL_REALIZATION,

            "paired_porosity":
                CONTROL_POROSITY,

            "partition":
                CONTROL_PARTITION,

            "canonical_day":
                CONTROL_DAY,

            "parent_state_source":
                CONTROL_STATE_FILE,

            "parent_state_source_sha256":
                a6e_manifest[
                    CONTROL_STATE_FILE
                ],

            "foundation_pressure_sha256":
                FOUNDATION_SHA256,

            "PI_RNN_inference":
                False,

            "physical_time_advance":
                False,

            "AV4_dynamic_transport_execution_authorized":
                False,
        }

        decision = {
            "milestone":
                MILESTONE,

            "status":
                STATUS_PASS,

            "protocol_id":
                PROTOCOL_ID,

            "A1_authority_bound":
                True,

            "control_parent_state_frozen":
                True,

            "control_realization":
                CONTROL_REALIZATION,

            "control_day":
                CONTROL_DAY,

            "parent_integrated_state_sha256":
                a6e_manifest[
                    CONTROL_STATE_FILE
                ],

            "foundation_pressure_sha256":
                FOUNDATION_SHA256,

            "parent_array_identities_frozen":
                True,

            "preexecution_certification_frozen":
                True,

            "same_time_refresh_recipe_frozen":
                True,

            "PASS_FAIL_BLOCK_gates_frozen":
                True,

            "atomic_output_commit_frozen":
                True,

            "pressure_solve_performed":
                False,

            "PI_RNN_inference_performed":
                False,

            "physical_time_advanced":
                False,

            "CMG_validation_performed":
                False,

            "A2E_authorized":
                True,

            "A2E_execution_authorized":
                True,

            "AV4_dynamic_transport_execution_authorized":
                False,

            "next":
                handoff,
        }

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

            "time_index":
                CONTROL_TIME_INDEX,

            "parent_integrated_state_sha256":
                a6e_manifest[
                    CONTROL_STATE_FILE
                ],

            "foundation_pressure_sha256":
                FOUNDATION_SHA256,

            "parent_component_mass_total_kg":
                parent_identity[
                    "parent_component_mass_total_kg"
                ],

            "parent_saturation_min":
                parent_identity[
                    "parent_saturation_min"
                ],

            "parent_saturation_max":
                parent_identity[
                    "parent_saturation_max"
                ],

            "parent_pressure_min_psi":
                parent_identity[
                    "parent_pressure_min_psi"
                ],

            "parent_pressure_max_psi":
                parent_identity[
                    "parent_pressure_max_psi"
                ],

            "scientific_execution":
                False,

            "A2E_authorized":
                True,

            "A2E_execution_authorized":
                True,

            "PI_RNN_inference":
                False,

            "physical_time_advance":
                False,
        }

        artifacts = {
            "PAD_Stream_POSTV16_AV4_A2_Summary.json":
                json_bytes(
                    summary
                ),

            "POSTV16_AV4_A2_Frozen_Parent_State_Identity.json":
                json_bytes(
                    parent_identity
                ),

            "POSTV16_AV4_A2_PreExecution_Parent_State_Certification_Contract.json":
                json_bytes(
                    preexecution
                ),

            "POSTV16_AV4_A2_Controlled_Refresh_Execution_Recipe.json":
                json_bytes(
                    execution_recipe
                ),

            "POSTV16_AV4_A2_Execution_Gates_and_Outcome_Classification.json":
                json_bytes(
                    gates_contract
                ),

            "POSTV16_AV4_A2_Atomic_Refreshed_Flow_Epoch_Output_Contract.json":
                json_bytes(
                    output_contract
                ),

            "POSTV16_AV4_A2_PostExecution_Handoff_Contract.json":
                json_bytes(
                    next_contract
                ),

            "POSTV16_AV4_A2_Scientific_Boundaries.json":
                json_bytes(
                    boundaries
                ),

            "POSTV16_AV4_A2_A2E_Handoff_Contract.json":
                json_bytes(
                    handoff
                ),

            "POSTV16_AV4_A2_Decision_Contract.json":
                json_bytes(
                    decision
                ),

            "POSTV16_AV4_A2_Final_Gate_Matrix.csv":
                csv_bytes(
                    [
                        {
                            "gate":
                                k,
                            **v,
                        }
                        for k, v in gates.items()
                    ]
                ),
        }

        immutable_publish(
            out,
            artifacts,
        )

        manifest_rows = []

        for p in sorted(
            out.iterdir()
        ):

            if (
                p.is_file()
                and p.name
                != "POSTV16_AV4_A2_Artifact_Manifest.csv"
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
                "POSTV16_AV4_A2_Artifact_Manifest.csv":
                    csv_bytes(
                        manifest_rows
                    )
            },
        )

        print()
        print("=" * 214)
        print("POSTV16-AV4-A2: CONTROLLED REFRESH EXECUTION CONTRACT FREEZE PASS")
        print("=" * 214)
        print("Control realization                     :", CONTROL_REALIZATION)
        print("Paired porosity                         :", CONTROL_POROSITY)
        print("Partition                               :", CONTROL_PARTITION)
        print("Canonical day                           :", CONTROL_DAY)
        print("Parent integrated-state SHA256          :", a6e_manifest[CONTROL_STATE_FILE])
        print("Foundation pressure SHA256              :", FOUNDATION_SHA256)
        print("Parent component mass kg                :", parent_identity["parent_component_mass_total_kg"])
        print("Parent saturation min/max               :", parent_identity["parent_saturation_min"], parent_identity["parent_saturation_max"])
        print("Parent pressure min/max psi             :", parent_identity["parent_pressure_min_psi"], parent_identity["parent_pressure_max_psi"])
        print("Pressure/flow execution in A2           : False")
        print("PI-RNN inference                        : False")
        print("Physical-time advance                   : False")
        print("POSTV16-AV4-A2-E                        : AUTHORIZED")
        print("A2-E execution                          : AUTHORIZED")
        print("AV4 dynamic transport                   : NOT YET AUTHORIZED")
        print("=" * 214)

        return 0

    except Exception as exc:

        blocked.mkdir(
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

            "gates":
                gates,

            "pressure_solve_performed":
                False,

            "PI_RNN_inference_performed":
                False,

            "physical_time_advanced":
                False,

            "CMG_validation_performed":
                False,

            "A2E_authorized":
                False,
        }

        p = blocked / "POSTV16_AV4_A2_Blocked_Report.json"

        if not p.exists():
            p.write_bytes(
                json_bytes(
                    report
                )
            )

        print()
        print("POSTV16-AV4-A2: BLOCKED")
        print("Stage    :", stage)
        print("Exception:", repr(exc))

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
