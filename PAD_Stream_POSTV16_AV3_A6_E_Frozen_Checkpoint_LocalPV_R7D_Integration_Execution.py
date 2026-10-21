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


MILESTONE = "POSTV16-AV3-A6-E"

PROTOCOL_ID = (
    "POSTV16_AV3_A6_E_FROZEN_EPOCH92_13CHANNEL_CHECKPOINT_"
    "LOCAL_PORE_VOLUME_R7D_TERMINAL_HALO_INTEGRATION_EXECUTION_V1"
)

STATUS_PASS = (
    "AV3A6E_FROZEN_EPOCH92_CHECKPOINT_LOCAL_PORE_VOLUME_R7D_TERMINAL_HALO_"
    "INTEGRATION_ALL_4_REALIZATIONS_ALL_9_TIMES_PASS"
)

STATUS_FAIL = (
    "AV3A6E_SPATIAL_COREY_RELPERM_LOCAL_PV_R7D_INTEGRATION_SCIENTIFIC_FAIL_"
    "NO_ADAPTATION_RETUNING_OR_SECOND_OOD_AUTHORIZED"
)

STATUS_BLOCKED = "AV3A6E_TECHNICAL_EXECUTION_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

PARENT_A6_COMMIT = "85d613050787fb743eafeaaf9c66fa16ec8e2905"

EXPECTED_CHECKPOINT_SHA256 = (
    "17b188494e0452570d43e868c20c4c814e6a1f0b493329d0e40849c4c5ec6d4e"
)

EXPECTED_BEST_EPOCH = 92
EXPECTED_EPOCHS_COMPLETED = 122
EXPECTED_BEST_VALIDATION_TOTAL = 0.002138707781058555

# --------------------------------------------------------------------------------------------------
# Exact repository authorities.
# --------------------------------------------------------------------------------------------------

A6 = (
    "PAD_Stream_POSTV16_AV3_A6_"
    "Frozen_Checkpoint_Deployment_Integration_Contract_Freeze.py"
)
A6_BLOB = "3e3937cc084807e5a439c2cd14f54914ac134db2"

A5R2 = "PAD_Stream_POSTV16_AV3_A5_R2_Frozen_Checkpoint_OneTouch_OOD_Continuation.py"
A5R2_BLOB = "b2dd3fb27966a51e6a6057e444dfdb617976b36f"

A4R2 = (
    "PAD_Stream_POSTV16_AV3_A4_R2_"
    "Corrected_Certification_Teacher_Dataset_and_LockedOOD_Predictor.py"
)
A4R2_BLOB = "289901331e835afb44ff2f665fe9a6bbea2eac19"

A2 = (
    "PAD_Stream_POSTV16_AV3_A2_"
    "Corey_Relperm_Field_Realization_Certification_and_Streamline_Sampling.py"
)
A2_BLOB = "e7d4f1b1e69ea3e756c4f41d7edb57e2ffd87d7b"

AV2A5 = "PAD_Stream_POSTV16_AV2_A5_Frozen_Checkpoint_LocalPV_R7D_Integration.py"
AV2A5_BLOB = "f2cc67b80a17eccfca54f4330b2259ef9b7e377c"

R7E = "PAD_Stream_POSTV16_AV1_D_R7_R7E_Frozen_Horizontal_Face_Halo_Occupancy_Domain_Execution.py"
R7E_BLOB = "9f99d9dcab649ba7ac911ad09ad79b4e0eb2ecc8"

B1 = "PAD_Stream_POSTV16_AV1_B1_R1_C26_to_E37A_Component_Mass_Representation_Equivalence_Audit.py"
B1_BLOB = "8d9561d7c85805b82dedc26073c4633f90eeeab6"

E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"

SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"

EOS_R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
EOS_R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

SOURCE_BLOBS = {
    A6: A6_BLOB,
    A5R2: A5R2_BLOB,
    A4R2: A4R2_BLOB,
    A2: A2_BLOB,
    AV2A5: AV2A5_BLOB,
    R7E: R7E_BLOB,
    B1: B1_BLOB,
    E37A: E37A_BLOB,
    SG7D: SG7D_BLOB,
    EOS_R2: EOS_R2_BLOB,
}

# --------------------------------------------------------------------------------------------------
# Frozen Drive authorities.
# --------------------------------------------------------------------------------------------------

BASE = (
    Path("post_v16")
    / RID
    / "POSTV16_AV3_Corey_Relperm_Heterogeneity"
)

A6_REL = BASE / "POSTV16_AV3_A6_Deployment_Integration_Contract_Freeze"

A6_SUMMARY = "PAD_Stream_POSTV16_AV3_A6_Summary.json"
A6_REGISTRY = "POSTV16_AV3_A6_Realization_Registry.json"
A6_PREDICTION = "POSTV16_AV3_A6_Prediction_Authority_Contract.json"
A6_TRANSFER = "POSTV16_AV3_A6_B1_R7D_Transfer_Integration_Contract.json"
A6_EXECUTION_GATES = "POSTV16_AV3_A6_Execution_Gates.json"
A6_FORBIDDEN = "POSTV16_AV3_A6_Forbidden_Adaptations.json"
A6_HANDOFF = "POSTV16_AV3_A6_A6E_Handoff_Contract.json"
A6_DECISION = "POSTV16_AV3_A6_Decision_Contract.json"
A6_GATE_MATRIX = "POSTV16_AV3_A6_Final_Gate_Matrix.csv"
A6_MANIFEST = "POSTV16_AV3_A6_Artifact_Manifest.csv"

A6_STATUS = (
    "AV3A6_FROZEN_EPOCH92_CHECKPOINT_LOCAL_PV_R7D_TERMINAL_HALO_"
    "DEPLOYMENT_AND_INTEGRATION_CONTRACT_PROSPECTIVELY_FROZEN_NO_EXECUTION"
)

A4R2_REL = (
    BASE
    / "POSTV16_AV3_A4_R2_Corrected_Teacher_Dataset_and_LockedOOD_Predictor"
)

A4R2_TRAINVAL = "POSTV16_AV3_A4_R2_TrainValidation_13Channel_Transport_Dataset.npz"
A4R2_MANIFEST = "POSTV16_AV3_A4_R2_Artifact_Manifest.csv"

A5R2_REL = (
    BASE
    / "POSTV16_AV3_A5_R2_Frozen_Checkpoint_OneTouch_OOD_Continuation"
)

A5R2_OOD_RESULT = "POSTV16_AV3_A5_R2_LockedOOD_Truth_and_Predictions.npz"
A5R2_MANIFEST = "POSTV16_AV3_A5_R2_Artifact_Manifest.csv"

A2_REL = (
    BASE
    / "POSTV16_AV3_A2_Corey_Relperm_Field_Realization_Certification_and_Streamline_Sampling"
)

A2_MANIFEST = "POSTV16_AV3_A2_Artifact_Manifest.csv"

CHECKPOINT_REL = (
    BASE
    / "POSTV16_AV3_A5_PIRNN_Training_Checkpoint_and_OneTouch_OOD"
    / "POSTV16_AV3_A5_Best_Validation_Model.keras"
)

OUT_REL = (
    BASE
    / "POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
)

FAIL_REL = BASE / "POSTV16_AV3_A6_E_SCIENTIFIC_FAIL"
BLOCK_REL = BASE / "POSTV16_AV3_A6_E_BLOCKED"

# --------------------------------------------------------------------------------------------------
# Frozen dimensions / states.
# --------------------------------------------------------------------------------------------------

GRID = (15, 50, 50)
NSL = 1078
NN = 201
NCV = 200
NT = 9

DX = 6.096
DY = 6.096
DZ = 1.2192
BULK_VOLUME_M3 = DX * DY * DZ

BACKGROUND = 0.20
INJECTED = 0.80
MAXSG = 0.60

DAYS = np.asarray(
    [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0],
    dtype=np.float64,
)

REALIZATIONS = [
    ("AV3CR0001", 0, "AV2PHI0001", "TRAIN"),
    ("AV3CR0002", 1, "AV2PHI0002", "TRAIN"),
    ("AV3CR0003", 2, "AV2PHI0003", "VALIDATION"),
    ("AV3CR0004", 3, "AV2PHI0004", "LOCKED_OOD_TEST"),
]


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
            raise GateError("manifest_SHA_mismatch:" + fn)

    return m


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
    out.mkdir(parents=True, exist_ok=True)

    for name, data in files.items():
        p = out / name

        if p.exists() and p.read_bytes() != data:
            raise GateError("existing_output_differs:" + name)

        if not p.exists():
            p.write_bytes(data)


def local_mass(
    r2,
    saturation: np.ndarray,
    pressure: np.ndarray,
    reference_gas_pressure_pa: float,
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
        sat - BACKGROUND,
        0.0,
        MAXSG,
    )

    rho = np.asarray(
        r2.gas_density_from_state(
            sat,
            pressure,
            reference_gas_pressure_pa,
        ),
        dtype=np.float64,
    )

    return pv * rho * sg


def invert_local_mass(
    r2,
    target_mass_kg: np.ndarray,
    pressure: np.ndarray,
    reference_gas_pressure_pa: float,
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

    if target.shape != GRID or pv.shape != GRID:
        raise GateError("local_inversion_shape")

    if (
        np.any(target < -1.0e-9)
        or np.any(pv <= 0.0)
        or not np.isfinite(pv).all()
    ):
        raise GateError("local_inversion_input")

    target = np.maximum(
        target,
        0.0,
    )

    cap = local_mass(
        r2,
        np.full(
            GRID,
            INJECTED,
            dtype=np.float64,
        ),
        pressure,
        reference_gas_pressure_pa,
        pv,
    )

    tol = max(
        1.0e-8,
        1.0e-12
        * max(
            float(
                np.max(
                    cap
                )
            ),
            1.0,
        ),
    )

    excess = float(
        np.max(
            target
            - cap
        )
    )

    if excess > tol:
        raise ScientificFail(
            "local_cell_mass_capacity_before_EOS_inversion",
            {
                "excess_kg": excess,
                "tolerance_kg": tol,
            },
        )

    lo = np.zeros(
        GRID,
        dtype=np.float64,
    )

    hi = np.full(
        GRID,
        MAXSG,
        dtype=np.float64,
    )

    for _ in range(80):

        mid = 0.5 * (
            lo
            + hi
        )

        mass = local_mass(
            r2,
            BACKGROUND
            + mid,
            pressure,
            reference_gas_pressure_pa,
            pv,
        )

        below = mass < target

        lo = np.where(
            below,
            mid,
            lo,
        )

        hi = np.where(
            below,
            hi,
            mid,
        )

    sg = 0.5 * (
        lo
        + hi
    )

    sg[
        target
        <= 1.0e-18
    ] = 0.0

    return sg


def assemble_prediction(
    prediction: np.ndarray,
    time_index: np.ndarray,
    streamline_index: np.ndarray,
) -> np.ndarray:

    pred = np.asarray(
        prediction,
        dtype=np.float64,
    )

    ti = np.asarray(
        time_index,
        dtype=np.int64,
    )

    sl = np.asarray(
        streamline_index,
        dtype=np.int64,
    )

    out = np.empty(
        (
            NT,
            NSL,
            NN,
        ),
        dtype=np.float64,
    )

    seen = np.zeros(
        (
            NT,
            NSL,
        ),
        dtype=np.int64,
    )

    for n in range(
        len(
            pred
        )
    ):

        out[
            ti[n],
            sl[n],
        ] = pred[n]

        seen[
            ti[n],
            sl[n],
        ] += 1

    if not np.all(
        seen == 1
    ):
        raise ScientificFail(
            "prediction_time_streamline_bijection",
            {
                "minimum_multiplicity":
                    int(
                        np.min(
                            seen
                        )
                    ),
                "maximum_multiplicity":
                    int(
                        np.max(
                            seen
                        )
                    ),
            },
        )

    return out


def reconcile_with_r7e(
    r7e,
    raw_mass_grid: np.ndarray,
    capacity_grid: np.ndarray,
    graph: dict[str, Any],
):

    try:
        return r7e.reconcile_mass_halo_strict(
            raw_mass_grid,
            capacity_grid,
            graph,
        )

    except Exception as exc:

        if exc.__class__.__name__ == "ScientificFail":

            gate = getattr(
                exc,
                "gate",
                "R7E_reconciliation_scientific_fail",
            )

            detail = getattr(
                exc,
                "detail",
                repr(
                    exc
                ),
            )

            raise ScientificFail(
                gate,
                detail,
            ) from exc

        raise


def self_test() -> None:

    class R:
        @staticmethod
        def gas_density_from_state(s, p, pref):
            return np.full(
                np.broadcast(
                    s,
                    p,
                ).shape,
                700.0,
                dtype=np.float64,
            )

    phi = np.linspace(
        0.11,
        0.29,
        np.prod(
            GRID
        ),
    ).reshape(
        GRID
    )

    pv = (
        phi
        * BULK_VOLUME_M3
    )

    sg = np.full(
        GRID,
        0.37,
        dtype=np.float64,
    )

    pressure = np.full(
        GRID,
        2500.0,
        dtype=np.float64,
    )

    target = (
        pv
        * 700.0
        * sg
    )

    got = invert_local_mass(
        R(),
        target,
        pressure,
        0.0,
        pv,
    )

    if float(
        np.max(
            np.abs(
                got
                - sg
            )
        )
    ) > 1.0e-12:
        raise RuntimeError(
            "variable_local_pv_inversion"
        )

    assert len(REALIZATIONS) == 4
    assert len(DAYS) == 9

    print(
        "POSTV16-AV3-A6-E frozen-checkpoint local-PV R7D integration self-test: PASS"
    )


def main(
    root: Path,
    drive: Path,
) -> int:

    import tensorflow as tf

    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"

    completed_states = 0
    time_rows: list[dict[str, Any]] = []
    realization_rows: list[dict[str, Any]] = []
    output_files: dict[str, bytes] = {}

    out = drive / OUT_REL
    fail_dir = drive / FAIL_REL
    block_dir = drive / BLOCK_REL

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

    print("=" * 214)
    print(
        "POSTV16-AV3-A6-E — FROZEN EPOCH-92 CHECKPOINT / "
        "LOCAL-PV / R7D TERMINAL-HALO 36-STATE INTEGRATION EXECUTION"
    )
    print("=" * 214)
    print("4 FROZEN AV3 COREY/RELPERM REALIZATIONS x 9 CANONICAL TIMES = 36 STATES.")
    print("CR0001/2/3: EXACT EPOCH-92 CHECKPOINT INFERENCE ON FROZEN A4-R2 X13.")
    print("CR0004: REUSE FROZEN A5-R2 Y_pred ONLY — NO Y_true ACCESS / REINFERENCE.")
    print("NO TRAINING / RESELECTION / NORMALIZATION REFIT / RETUNING.")
    print("NO PRESSURE RE-SOLVE / DARCY-Q RECOMPUTATION / POLLOCK RETRACE / TOF RECOMPUTE.")
    print("NO ADAPTIVE HALO / GLOBAL RESCALE / MASS CLIPPING OR DISCARD / CMG.")
    print()

    try:
        root = root.resolve()
        drive = drive.resolve()

        # ------------------------------------------------------------------------------------------
        # Immutable no-rerun firewall.
        # ------------------------------------------------------------------------------------------
        stage = "preexisting_state_firewall"

        pass_summary = out / "PAD_Stream_POSTV16_AV3_A6_E_Summary.json"
        fail_report = fail_dir / "POSTV16_AV3_A6_E_Scientific_Fail_Report.json"
        block_report = block_dir / "POSTV16_AV3_A6_E_Blocked_Report.json"

        gate(
            "no_preexisting_A6E_PASS",
            not pass_summary.exists(),
            str(
                pass_summary
            ),
        )

        gate(
            "no_preexisting_A6E_FAIL",
            not fail_report.exists(),
            str(
                fail_report
            ),
        )

        gate(
            "no_preexisting_A6E_BLOCK",
            not block_report.exists(),
            str(
                block_report
            ),
        )

        # ------------------------------------------------------------------------------------------
        # Exact Git authority.
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
            "repository_parent_is_A6_commit",
            parent == PARENT_A6_COMMIT,
            parent,
        )

        gate(
            "repository_clean",
            status == "",
            repr(
                status
            ),
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
                actual == expected,
                actual,
            )

        # ------------------------------------------------------------------------------------------
        # Bind exact formal A6 freeze.
        # ------------------------------------------------------------------------------------------
        stage = "A6_contract_binding"

        a6 = drive / A6_REL

        gate(
            "A6_output_present",
            a6.is_dir(),
            str(
                a6
            ),
        )

        m6 = verify_manifest(
            a6,
            A6_MANIFEST,
        )

        gate(
            "A6_manifest_exact_9",
            len(
                m6
            )
            == 9,
            len(
                m6
            ),
        )

        a6_summary = load_json(
            a6
            / A6_SUMMARY
        )

        a6_registry = load_json(
            a6
            / A6_REGISTRY
        )

        a6_prediction = load_json(
            a6
            / A6_PREDICTION
        )

        a6_transfer = load_json(
            a6
            / A6_TRANSFER
        )

        a6_execution_gates = load_json(
            a6
            / A6_EXECUTION_GATES
        )

        a6_forbidden = load_json(
            a6
            / A6_FORBIDDEN
        )

        a6_handoff = load_json(
            a6
            / A6_HANDOFF
        )

        a6_decision = load_json(
            a6
            / A6_DECISION
        )

        a6_gate_rows = read_csv(
            a6
            / A6_GATE_MATRIX
        )

        gate(
            "A6_status_exact",
            a6_summary[
                "status"
            ]
            == A6_STATUS,
            a6_summary[
                "status"
            ],
        )

        gate(
            "A6_checkpoint_exact",
            a6_summary[
                "checkpoint_sha256"
            ]
            == EXPECTED_CHECKPOINT_SHA256
            and int(
                a6_summary[
                    "best_epoch"
                ]
            )
            == EXPECTED_BEST_EPOCH,
        )

        gate(
            "A6_registry_4x9_exact",
            len(
                a6_registry[
                    "realizations"
                ]
            )
            == 4
            and a6_registry[
                "canonical_times_days"
            ]
            == DAYS.tolist()
            and int(
                a6_summary[
                    "prospective_integrated_states"
                ]
            )
            == 36,
        )

        gate(
            "A6_CR0004_frozen_prediction_only",
            a6_summary[
                "OOD_prediction_authority"
            ]
            == "FROZEN_A5R2_Y_PRED_ONLY"
            and a6_prediction[
                "AV3CR0004"
            ][
                "Y_true_access"
            ]
            is False
            and a6_prediction[
                "AV3CR0004"
            ][
                "metric_recompute"
            ]
            is False
            and a6_prediction[
                "AV3CR0004"
            ][
                "model_reinference"
            ]
            is False
            and a6_prediction[
                "AV3CR0004"
            ][
                "teacher_regeneration"
            ]
            is False,
        )

        gate(
            "A6_transfer_contract_exact_core",
            a6_transfer[
                "raw_deposition_support"
            ]
            == "S0 only"
            and a6_transfer[
                "H1_terminal_occupancy_only"
            ]
            is True
            and a6_transfer[
                "H1_transit"
            ]
            is False
            and float(
                a6_transfer[
                    "S0_to_H1_entry_cost"
                ]
            )
            == 5.0
            and a6_transfer[
                "adaptive_halo"
            ]
            is False
            and a6_transfer[
                "local_PV"
            ]
            == "paired_porosity * cell_bulk_volume"
            and a6_transfer[
                "global_rescale"
            ]
            is False
            and a6_transfer[
                "mass_clipping_or_discard"
            ]
            is False
            and a6_transfer[
                "saturation_bounds"
            ]
            == [
                0.20,
                0.80,
            ],
        )

        gate(
            "A6_execution_thresholds_exact",
            int(
                a6_execution_gates[
                    "realizations"
                ]
            )
            == 4
            and int(
                a6_execution_gates[
                    "times_each"
                ]
            )
            == 9
            and int(
                a6_execution_gates[
                    "integrated_states"
                ]
            )
            == 36
            and float(
                a6_execution_gates[
                    "B1_projection_relative_closure_max"
                ]
            )
            == 1.0e-12
            and float(
                a6_execution_gates[
                    "mass_relative_closure_max"
                ]
            )
            == 1.0e-10
            and float(
                a6_execution_gates[
                    "EOS_localPV_mass_relative_closure_max"
                ]
            )
            == 1.0e-10,
        )

        gate(
            "A6_all_freeze_gates_passed",
            len(
                a6_gate_rows
            )
            == 38
            and all(
                str(
                    row[
                        "passed"
                    ]
                ).lower()
                == "true"
                for row in a6_gate_rows
            ),
            len(
                a6_gate_rows
            ),
        )

        gate(
            "A6_A6E_handoff_exact",
            a6_handoff[
                "milestone"
            ]
            == MILESTONE
            and a6_handoff[
                "authorized"
            ]
            is True
            and a6_handoff[
                "execution"
            ]
            is True
            and a6_handoff[
                "AV3_final_outcome_freeze_authorized"
            ]
            is False
            and a6_decision[
                "A6_execution_authorized"
            ]
            is True,
        )

        # ------------------------------------------------------------------------------------------
        # Bind checkpoint and exact scientific modules.
        # ------------------------------------------------------------------------------------------
        stage = "runtime_authority_binding"

        checkpoint = drive / CHECKPOINT_REL

        gate(
            "checkpoint_file_present",
            checkpoint.is_file(),
            str(
                checkpoint
            ),
        )

        gate(
            "checkpoint_SHA256_exact",
            checkpoint.is_file()
            and sha256_file(
                checkpoint
            )
            == EXPECTED_CHECKPOINT_SHA256,
            sha256_file(
                checkpoint
            )
            if checkpoint.is_file()
            else "missing",
        )

        r7e = load_module(
            root
            / R7E,
            "av3a6e_r7e",
        )

        b1 = load_module(
            root
            / B1,
            "av3a6e_b1",
        )

        e37 = load_module(
            root
            / E37A,
            "av3a6e_e37",
        )

        sg7d = load_module(
            root
            / SG7D,
            "av3a6e_sg7d",
        )

        r2 = load_module(
            root
            / EOS_R2,
            "av3a6e_r2",
        )

        foundation = r7e.find_named_exact(
            [
                root,
                drive,
            ],
            r7e.FOUNDATION_NAME,
            r7e.FOUNDATION_SHA,
        )

        gate(
            "foundation_SHA_exact",
            sha256_file(
                foundation
            )
            == r7e.FOUNDATION_SHA,
            str(
                foundation
            ),
        )

        with np.load(
            foundation,
            allow_pickle=False,
        ) as z:

            pressure = np.asarray(
                z[
                    "pressure"
                ],
                dtype=np.float64,
            )

        sci_gate(
            "foundation_pressure_shape_finite",
            pressure.shape
            == GRID
            and np.isfinite(
                pressure
            ).all(),
            pressure.shape,
        )

        injector_capillary_pa = float(
            r2.capillary_pressure_from_incremental_sg(
                float(
                    r2.MAX_INCREMENTAL_CO2_SATURATION
                )
            )
        )

        injector_pressure_pa = np.asarray(
            [
                pressure[
                    k,
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

        reference_gas_pressure_pa = float(
            np.mean(
                injector_pressure_pa
            )
            + injector_capillary_pa
        )

        sci_gate(
            "reference_gas_pressure_finite",
            np.isfinite(
                reference_gas_pressure_pa
            ),
            reference_gas_pressure_pa,
        )

        # ------------------------------------------------------------------------------------------
        # Prediction authorities.
        #
        # CR0001/2/3 -> model inference.
        # CR0004     -> frozen Y_pred only. Y_true is NEVER indexed/read.
        # ------------------------------------------------------------------------------------------
        stage = "prediction_authority_execution"

        a4r2 = drive / A4R2_REL
        m4 = verify_manifest(
            a4r2,
            A4R2_MANIFEST,
        )

        trainval_path = a4r2 / A4R2_TRAINVAL

        gate(
            "A4R2_trainval_manifested",
            A4R2_TRAINVAL
            in m4
            and trainval_path.is_file()
            and sha256_file(
                trainval_path
            )
            == m4[
                A4R2_TRAINVAL
            ],
        )

        with np.load(
            trainval_path,
            allow_pickle=False,
        ) as z:

            X13 = np.asarray(
                z[
                    "X_required_13"
                ],
                dtype=np.float32,
            )

            trainval_realization_index = np.asarray(
                z[
                    "realization_index"
                ],
                dtype=np.int64,
            )

            trainval_time_index = np.asarray(
                z[
                    "time_index"
                ],
                dtype=np.int64,
            )

            trainval_streamline_index = np.asarray(
                z[
                    "streamline_index"
                ],
                dtype=np.int64,
            )

        sci_gate(
            "A4R2_X13_shape_exact",
            X13.shape
            == (
                29106,
                NN,
                13,
            ),
            X13.shape,
        )

        a5r2 = drive / A5R2_REL
        m5 = verify_manifest(
            a5r2,
            A5R2_MANIFEST,
        )

        ood_path = a5r2 / A5R2_OOD_RESULT

        gate(
            "A5R2_OOD_result_manifested",
            A5R2_OOD_RESULT
            in m5
            and ood_path.is_file()
            and sha256_file(
                ood_path
            )
            == m5[
                A5R2_OOD_RESULT
            ],
        )

        # IMPORTANT: Do not read Y_true.
        with np.load(
            ood_path,
            allow_pickle=False,
        ) as z:

            P_ood_frozen = np.asarray(
                z[
                    "Y_pred"
                ],
                dtype=np.float64,
            )

            ood_realization_index = np.asarray(
                z[
                    "realization_index"
                ],
                dtype=np.int64,
            )

            ood_time_index = np.asarray(
                z[
                    "time_index"
                ],
                dtype=np.int64,
            )

            ood_streamline_index = np.asarray(
                z[
                    "streamline_index"
                ],
                dtype=np.int64,
            )

            ood_target_days = np.asarray(
                z[
                    "target_time_days"
                ],
                dtype=np.float64,
            )

            ood_checkpoint_sha = str(
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

        gate(
            "CR0004_frozen_prediction_checkpoint_exact",
            ood_checkpoint_sha
            == EXPECTED_CHECKPOINT_SHA256,
            ood_checkpoint_sha,
        )

        sci_gate(
            "CR0004_frozen_prediction_shape_exact",
            P_ood_frozen.shape
            == (
                NT
                * NSL,
                NN,
            ),
            P_ood_frozen.shape,
        )

        sci_gate(
            "CR0004_registry_exact",
            set(
                np.unique(
                    ood_realization_index
                ).tolist()
            )
            == {
                3
            }
            and set(
                np.unique(
                    ood_time_index
                ).tolist()
            )
            == set(
                range(
                    NT
                )
            )
            and set(
                np.unique(
                    ood_streamline_index
                ).tolist()
            )
            == set(
                range(
                    NSL
                )
            )
            and np.allclose(
                np.unique(
                    ood_target_days
                ),
                DAYS,
            ),
        )

        model = tf.keras.models.load_model(
            checkpoint
        )

        sci_gate(
            "checkpoint_parameter_count_53057",
            model.count_params()
            == 53057,
            model.count_params(),
        )

        prediction_by_realization: dict[str, np.ndarray] = {}
        inference_seconds: dict[str, float] = {}

        for rid, idx, phi_rid, partition in REALIZATIONS:

            if idx < 3:

                q = np.flatnonzero(
                    trainval_realization_index
                    == idx
                )

                sci_gate(
                    f"{rid}_predictor_count_exact",
                    len(
                        q
                    )
                    == NT
                    * NSL,
                    len(
                        q
                    ),
                )

                t0 = time.time()

                pred = model.predict(
                    X13[
                        q
                    ],
                    batch_size=64,
                    verbose=0,
                ).astype(
                    np.float64
                )

                inference_seconds[
                    rid
                ] = float(
                    time.time()
                    - t0
                )

                prediction_by_realization[
                    rid
                ] = assemble_prediction(
                    pred,
                    trainval_time_index[
                        q
                    ],
                    trainval_streamline_index[
                        q
                    ],
                )

            else:

                prediction_by_realization[
                    rid
                ] = assemble_prediction(
                    P_ood_frozen,
                    ood_time_index,
                    ood_streamline_index,
                )

                inference_seconds[
                    rid
                ] = 0.0

        gate(
            "CR0004_Y_true_not_accessed",
            True,
        )

        gate(
            "CR0004_metric_recompute_not_performed",
            True,
        )

        gate(
            "CR0004_reinference_not_performed",
            inference_seconds[
                "AV3CR0004"
            ]
            == 0.0,
        )

        gate(
            "no_training_or_optimizer_updates",
            True,
        )

        # ------------------------------------------------------------------------------------------
        # 36-state conservative integration.
        # ------------------------------------------------------------------------------------------
        a2 = drive / A2_REL
        m2 = verify_manifest(
            a2,
            A2_MANIFEST,
        )

        for rid, idx, phi_rid, partition in REALIZATIONS:

            stage = (
                "integration_"
                + rid
            )

            artifact_name = (
                f"POSTV16_AV3_A2_{rid}_"
                "Corey_Relperm_Field_and_Streamline_Sampling.npz"
            )

            artifact_path = (
                a2
                / artifact_name
            )

            gate(
                f"{rid}_A2_artifact_manifested",
                artifact_name
                in m2
                and artifact_path.is_file()
                and sha256_file(
                    artifact_path
                )
                == m2[
                    artifact_name
                ],
                artifact_name,
            )

            with np.load(
                artifact_path,
                allow_pickle=False,
            ) as z:

                phi = np.asarray(
                    z[
                        "paired_porosity"
                    ],
                    dtype=np.float64,
                )

                xyz = np.asarray(
                    z[
                        "streamline_xyz_m"
                    ],
                    dtype=np.float64,
                )

                tof_s = np.asarray(
                    z[
                        "pollock_tof_s"
                    ],
                    dtype=np.float64,
                )

                weight_m3_s = np.asarray(
                    z[
                        "streamline_weight_m3_s"
                    ],
                    dtype=np.float64,
                )

                nw_grid = np.asarray(
                    z[
                        "nw"
                    ],
                    dtype=np.float64,
                )

                no_grid = np.asarray(
                    z[
                        "no"
                    ],
                    dtype=np.float64,
                )

                krw_grid = np.asarray(
                    z[
                        "krw_max"
                    ],
                    dtype=np.float64,
                )

                kro_grid = np.asarray(
                    z[
                        "kro_max"
                    ],
                    dtype=np.float64,
                )

                stored_rid = str(
                    np.asarray(
                        z[
                            "corey_realization_id"
                        ]
                    ).reshape(
                        -1
                    )[
                        0
                    ]
                )

                stored_phi_rid = str(
                    np.asarray(
                        z[
                            "paired_porosity_realization_id"
                        ]
                    ).reshape(
                        -1
                    )[
                        0
                    ]
                )

            sci_gate(
                f"{rid}_identity_exact",
                stored_rid
                == rid
                and stored_phi_rid
                == phi_rid,
                [
                    stored_rid,
                    stored_phi_rid,
                ],
            )

            sci_gate(
                f"{rid}_paired_porosity_shape_bounds_nonconstant",
                phi.shape
                == GRID
                and float(
                    np.min(
                        phi
                    )
                )
                > 0.10
                and float(
                    np.max(
                        phi
                    )
                )
                < 0.30
                and float(
                    np.std(
                        phi
                    )
                )
                > 0.0,
                [
                    phi.shape,
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
                    float(
                        np.std(
                            phi
                        )
                    ),
                ],
            )

            for field_name, field in [
                (
                    "nw",
                    nw_grid,
                ),
                (
                    "no",
                    no_grid,
                ),
                (
                    "krw_max",
                    krw_grid,
                ),
                (
                    "kro_max",
                    kro_grid,
                ),
            ]:

                sci_gate(
                    f"{rid}_{field_name}_grid_shape_finite",
                    field.shape
                    == GRID
                    and np.isfinite(
                        field
                    ).all(),
                    field.shape,
                )

            sci_gate(
                f"{rid}_kinematics_shapes_exact",
                xyz.shape
                == (
                    NSL,
                    NN,
                    3,
                )
                and tof_s.shape
                == (
                    NSL,
                    NN,
                )
                and weight_m3_s.shape
                == (
                    NSL,
                ),
                [
                    xyz.shape,
                    tof_s.shape,
                    weight_m3_s.shape,
                ],
            )

            pore_volume_grid_m3 = (
                phi
                * BULK_VOLUME_M3
            )

            sci_gate(
                f"{rid}_local_cell_PV_positive_finite",
                np.isfinite(
                    pore_volume_grid_m3
                ).all()
                and np.all(
                    pore_volume_grid_m3
                    > 0.0
                ),
            )

            sci_gate(
                f"{rid}_local_cell_PV_nonconstant",
                float(
                    np.std(
                        pore_volume_grid_m3
                    )
                )
                > 0.0,
                float(
                    np.std(
                        pore_volume_grid_m3
                    )
                ),
            )

            operator = sg7d.build_subsegment_operator(
                xyz,
                tof_s
                / float(
                    e37.DAY_TO_S
                ),
                weight_m3_s
                * float(
                    e37.DAY_TO_S
                ),
            )

            graph = r7e.build_extended_halo_graph(
                operator
            )

            sci_gate(
                f"{rid}_S0_nonempty",
                len(
                    graph[
                        "s0_nodes"
                    ]
                )
                > 0,
                len(
                    graph[
                        "s0_nodes"
                    ]
                ),
            )

            sci_gate(
                f"{rid}_H1_nonempty",
                len(
                    graph[
                        "h1_nodes"
                    ]
                )
                > 0,
                len(
                    graph[
                        "h1_nodes"
                    ]
                ),
            )

            sci_gate(
                f"{rid}_D1_partition_exact",
                len(
                    graph[
                        "nodes"
                    ]
                )
                == len(
                    graph[
                        "s0_nodes"
                    ]
                )
                + len(
                    graph[
                        "h1_nodes"
                    ]
                ),
                [
                    len(
                        graph[
                            "nodes"
                        ]
                    ),
                    len(
                        graph[
                            "s0_nodes"
                        ]
                    ),
                    len(
                        graph[
                            "h1_nodes"
                        ]
                    ),
                ],
            )

            arc_kind = np.asarray(
                graph[
                    "arc_kind"
                ],
                dtype=np.int8,
            )

            arc_u = np.asarray(
                graph[
                    "arc_u"
                ],
                dtype=np.int64,
            )

            sci_gate(
                f"{rid}_H1_never_originates_arc",
                not np.any(
                    graph[
                        "h1_mask"
                    ][
                        arc_u
                    ]
                ),
            )

            sci_gate(
                f"{rid}_halo_entry_cost_exact_5",
                np.all(
                    np.asarray(
                        graph[
                            "arc_cost"
                        ],
                        dtype=np.float64,
                    )[
                        arc_kind
                        == 1
                    ]
                    == 5.0
                ),
            )

            geometry = e37.build_control_volume_geometry(
                r2,
                operator,
                pressure,
                reference_gas_pressure_pa,
                NSL,
                NCV,
            )

            cv_pressure_mass_coeff = np.asarray(
                geometry[
                    "cv_pressure_mass_coeff"
                ],
                dtype=np.float64,
            )

            sci_gate(
                f"{rid}_E37_mass_coefficient_positive_finite",
                cv_pressure_mass_coeff.shape
                == (
                    NSL,
                    NCV,
                )
                and np.all(
                    cv_pressure_mass_coeff
                    > 0.0
                )
                and np.isfinite(
                    cv_pressure_mass_coeff
                ).all(),
                cv_pressure_mass_coeff.shape,
            )

            prediction_201 = prediction_by_realization[
                rid
            ]

            streamline_ids = np.tile(
                np.arange(
                    NSL,
                    dtype=np.int64,
                ),
                NT,
            )

            pred_200_flat, projected_mass_flat, projected_sample_mass_flat = (
                b1.project_201_to_200_component_mass(
                    r2,
                    e37,
                    prediction_201.reshape(
                        -1,
                        NN,
                    ),
                    cv_pressure_mass_coeff,
                    streamline_ids,
                )
            )

            pred_200 = np.asarray(
                pred_200_flat,
                dtype=np.float64,
            ).reshape(
                NT,
                NSL,
                NCV,
            )

            projected_mass = np.asarray(
                projected_mass_flat,
                dtype=np.float64,
            ).reshape(
                NT,
                NSL,
                NCV,
            )

            projected_sample_mass = np.asarray(
                projected_sample_mass_flat,
                dtype=np.float64,
            ).reshape(
                NT,
                NSL,
                NN,
            )

            b1_closure = (
                np.abs(
                    np.sum(
                        projected_mass,
                        axis=(
                            1,
                            2,
                        ),
                    )
                    - np.sum(
                        projected_sample_mass,
                        axis=(
                            1,
                            2,
                        ),
                    )
                )
                / np.maximum(
                    np.abs(
                        np.sum(
                            projected_mass,
                            axis=(
                                1,
                                2,
                            ),
                        )
                    ),
                    1.0,
                )
            )

            sci_gate(
                f"{rid}_B1_mass_projection_closure",
                float(
                    np.max(
                        b1_closure
                    )
                )
                <= 1.0e-12,
                float(
                    np.max(
                        b1_closure
                    )
                ),
            )

            flat_cell = np.asarray(
                geometry[
                    "flat_cell"
                ],
                dtype=np.int64,
            )

            control_volume_id = np.asarray(
                geometry[
                    "cv_id"
                ],
                dtype=np.int64,
            )

            subsegment_pore_volume_m3 = np.asarray(
                geometry[
                    "pv_m3"
                ],
                dtype=np.float64,
            )

            subsegment_pressure_psi = np.asarray(
                geometry[
                    "pseg_psi"
                ],
                dtype=np.float64,
            )

            rho_max = np.asarray(
                r2.gas_density_from_state(
                    np.full(
                        GRID,
                        INJECTED,
                        dtype=np.float64,
                    ),
                    pressure,
                    reference_gas_pressure_pa,
                ),
                dtype=np.float64,
            )

            capacity_grid_kg = (
                pore_volume_grid_m3
                * rho_max
                * MAXSG
            )

            sci_gate(
                f"{rid}_local_capacity_positive_finite",
                np.isfinite(
                    capacity_grid_kg
                ).all()
                and np.all(
                    capacity_grid_kg
                    > 0.0
                ),
            )

            saturation_out = np.empty(
                (
                    NT,
                )
                + GRID,
                dtype=np.float64,
            )

            mass_out = np.empty(
                (
                    NT,
                )
                + GRID,
                dtype=np.float64,
            )

            integration_start = time.time()

            for it, day in enumerate(
                DAYS
            ):

                subsegment_saturation = pred_200[
                    it
                ].reshape(
                    -1
                )[
                    control_volume_id
                ]

                subsegment_incremental_sg = np.clip(
                    subsegment_saturation
                    - BACKGROUND,
                    0.0,
                    MAXSG,
                )

                subsegment_rho = np.asarray(
                    r2.gas_density_from_state(
                        subsegment_saturation,
                        subsegment_pressure_psi,
                        reference_gas_pressure_pa,
                    ),
                    dtype=np.float64,
                )

                subsegment_mass = (
                    subsegment_pore_volume_m3
                    * subsegment_rho
                    * subsegment_incremental_sg
                )

                raw_mass = np.bincount(
                    flat_cell,
                    weights=subsegment_mass,
                    minlength=np.prod(
                        GRID
                    ),
                ).reshape(
                    GRID
                )

                target_mass = float(
                    np.sum(
                        projected_mass[
                            it
                        ]
                    )
                )

                deposit_residual = float(
                    np.sum(
                        raw_mass
                    )
                    - target_mass
                )

                deposit_tolerance = max(
                    1.0e-7,
                    1.0e-11
                    * max(
                        abs(
                            target_mass
                        ),
                        1.0,
                    ),
                )

                sci_gate(
                    f"{rid}_day{int(day)}_B1_to_subsegment_mass",
                    abs(
                        deposit_residual
                    )
                    <= deposit_tolerance,
                    [
                        deposit_residual,
                        deposit_tolerance,
                    ],
                )

                raw_flat = raw_mass.reshape(
                    -1
                )

                outside_s0 = np.ones(
                    np.prod(
                        GRID
                    ),
                    dtype=bool,
                )

                outside_s0[
                    graph[
                        "s0_nodes"
                    ]
                ] = False

                sci_gate(
                    f"{rid}_day{int(day)}_raw_outside_S0_exact_zero",
                    np.array_equal(
                        raw_flat[
                            outside_s0
                        ],
                        np.zeros(
                            np.sum(
                                outside_s0
                            ),
                            dtype=np.float64,
                        ),
                    ),
                )

                d1_nodes = np.asarray(
                    graph[
                        "nodes"
                    ],
                    dtype=np.int64,
                )

                d1_capacity_kg = float(
                    np.sum(
                        capacity_grid_kg.reshape(
                            -1
                        )[
                            d1_nodes
                        ]
                    )
                )

                raw_total_kg = float(
                    np.sum(
                        raw_mass
                    )
                )

                feasibility_tol = max(
                    1.0e-7,
                    1.0e-11
                    * max(
                        abs(
                            raw_total_kg
                        ),
                        1.0,
                    ),
                )

                sci_gate(
                    f"{rid}_day{int(day)}_R7D_D1_capacity_feasible",
                    raw_total_kg
                    <= d1_capacity_kg
                    + feasibility_tol,
                    [
                        raw_total_kg,
                        d1_capacity_kg,
                        feasibility_tol,
                    ],
                )

                reconciled_mass, diag, _ = reconcile_with_r7e(
                    r7e,
                    raw_mass,
                    capacity_grid_kg,
                    graph,
                )

                max_post_capacity_excess = float(
                    diag[
                        "max_capacity_excess_after_reconciliation_kg"
                    ]
                )

                capacity_tol = max(
                    1.0e-7,
                    1.0e-11
                    * max(
                        float(
                            diag[
                                "D1_capacity_kg"
                            ]
                        ),
                        1.0,
                    ),
                )

                sci_gate(
                    f"{rid}_day{int(day)}_post_reconciliation_capacity",
                    max_post_capacity_excess
                    <= capacity_tol,
                    [
                        max_post_capacity_excess,
                        capacity_tol,
                    ],
                )

                sci_gate(
                    f"{rid}_day{int(day)}_total_component_mass_closure",
                    float(
                        diag[
                            "total_component_mass_relative_closure"
                        ]
                    )
                    <= 1.0e-10,
                    float(
                        diag[
                            "total_component_mass_relative_closure"
                        ]
                    ),
                )

                incremental_sg = invert_local_mass(
                    r2,
                    reconciled_mass,
                    pressure,
                    reference_gas_pressure_pa,
                    pore_volume_grid_m3,
                )

                saturation = (
                    BACKGROUND
                    + incremental_sg
                )

                sci_gate(
                    f"{rid}_day{int(day)}_grid_saturation_finite_bounds",
                    np.isfinite(
                        saturation
                    ).all()
                    and float(
                        np.min(
                            saturation
                        )
                    )
                    >= BACKGROUND
                    - 1.0e-12
                    and float(
                        np.max(
                            saturation
                        )
                    )
                    <= INJECTED
                    + 1.0e-12,
                    [
                        float(
                            np.min(
                                saturation
                            )
                        ),
                        float(
                            np.max(
                                saturation
                            )
                        ),
                    ],
                )

                reconstructed_mass = float(
                    np.sum(
                        local_mass(
                            r2,
                            saturation,
                            pressure,
                            reference_gas_pressure_pa,
                            pore_volume_grid_m3,
                        )
                    )
                )

                reconciled_total_mass = float(
                    np.sum(
                        reconciled_mass
                    )
                )

                eos_relative_closure = (
                    abs(
                        reconstructed_mass
                        - reconciled_total_mass
                    )
                    / max(
                        abs(
                            reconciled_total_mass
                        ),
                        1.0,
                    )
                )

                sci_gate(
                    f"{rid}_day{int(day)}_EOS_localPV_mass_closure",
                    eos_relative_closure
                    <= 1.0e-10,
                    eos_relative_closure,
                )

                d1_mask = np.zeros(
                    np.prod(
                        GRID
                    ),
                    dtype=bool,
                )

                d1_mask[
                    d1_nodes
                ] = True

                d1_mask = d1_mask.reshape(
                    GRID
                )

                sci_gate(
                    f"{rid}_day{int(day)}_outside_D1_background_exact",
                    np.array_equal(
                        saturation[
                            ~d1_mask
                        ],
                        np.full(
                            np.sum(
                                ~d1_mask
                            ),
                            BACKGROUND,
                            dtype=np.float64,
                        ),
                    ),
                )

                sci_gate(
                    f"{rid}_day{int(day)}_outside_D1_mass_exact_zero",
                    np.array_equal(
                        reconciled_mass[
                            ~d1_mask
                        ],
                        np.zeros(
                            np.sum(
                                ~d1_mask
                            ),
                            dtype=np.float64,
                        ),
                    ),
                )

                saturation_out[
                    it
                ] = saturation

                mass_out[
                    it
                ] = reconciled_mass

                completed_states += 1

                time_rows.append(
                    {
                        "corey_realization_id":
                            rid,

                        "paired_porosity_realization_id":
                            phi_rid,

                        "partition":
                            partition,

                        "target_day":
                            float(
                                day
                            ),

                        "S0_cells":
                            len(
                                graph[
                                    "s0_nodes"
                                ]
                            ),

                        "H1_cells":
                            len(
                                graph[
                                    "h1_nodes"
                                ]
                            ),

                        "D1_cells":
                            len(
                                graph[
                                    "nodes"
                                ]
                            ),

                        "B1_projection_relative_closure":
                            float(
                                b1_closure[
                                    it
                                ]
                            ),

                        "raw_total_component_mass_kg":
                            float(
                                diag[
                                    "raw_total_component_mass_kg"
                                ]
                            ),

                        "raw_overloaded_cell_count":
                            int(
                                diag[
                                    "raw_overloaded_cell_count"
                                ]
                            ),

                        "raw_max_capacity_excess_kg":
                            float(
                                diag[
                                    "raw_max_capacity_excess_kg"
                                ]
                            ),

                        "D1_capacity_kg":
                            float(
                                diag[
                                    "D1_capacity_kg"
                                ]
                            ),

                        "S0_capacity_kg":
                            float(
                                diag[
                                    "S0_capacity_kg"
                                ]
                            ),

                        "H1_capacity_kg":
                            float(
                                diag[
                                    "H1_capacity_kg"
                                ]
                            ),

                        "H1_final_component_mass_kg":
                            float(
                                diag[
                                    "H1_final_component_mass_kg"
                                ]
                            ),

                        "H1_capacity_fraction_used":
                            float(
                                diag[
                                    "H1_capacity_fraction_used"
                                ]
                            ),

                        "H1_occupied_cell_count":
                            int(
                                diag[
                                    "H1_occupied_cell_count"
                                ]
                            ),

                        "max_capacity_excess_after_reconciliation_kg":
                            max_post_capacity_excess,

                        "mass_relative_closure":
                            float(
                                diag[
                                    "total_component_mass_relative_closure"
                                ]
                            ),

                        "EOS_localPV_mass_relative_closure":
                            eos_relative_closure,

                        "grid_saturation_min":
                            float(
                                np.min(
                                    saturation
                                )
                            ),

                        "grid_saturation_max":
                            float(
                                np.max(
                                    saturation
                                )
                            ),
                    }
                )

            integration_seconds = float(
                time.time()
                - integration_start
            )

            output_files[
                f"POSTV16_AV3_A6_E_{rid}_Integrated_State.npz"
            ] = deterministic_npz_bytes(
                {
                    "paired_porosity":
                        phi,

                    "nw":
                        nw_grid,

                    "no":
                        no_grid,

                    "krw_max":
                        krw_grid,

                    "kro_max":
                        kro_grid,

                    "grid_saturation":
                        saturation_out,

                    "grid_component_mass_kg":
                        mass_out,

                    "S0_nodes":
                        np.asarray(
                            graph[
                                "s0_nodes"
                            ],
                            dtype=np.int64,
                        ),

                    "H1_nodes":
                        np.asarray(
                            graph[
                                "h1_nodes"
                            ],
                            dtype=np.int64,
                        ),

                    "D1_nodes":
                        np.asarray(
                            graph[
                                "nodes"
                            ],
                            dtype=np.int64,
                        ),

                    "checkpoint_sha256":
                        np.asarray(
                            EXPECTED_CHECKPOINT_SHA256
                        ),

                    "target_days":
                        DAYS,
                }
            )

            realization_rows.append(
                {
                    "corey_realization_id":
                        rid,

                    "paired_porosity_realization_id":
                        phi_rid,

                    "partition":
                        partition,

                    "porosity_min":
                        float(
                            np.min(
                                phi
                            )
                        ),

                    "porosity_max":
                        float(
                            np.max(
                                phi
                            )
                        ),

                    "porosity_mean":
                        float(
                            np.mean(
                                phi
                            )
                        ),

                    "porosity_std":
                        float(
                            np.std(
                                phi
                            )
                        ),

                    "nw_min":
                        float(
                            np.min(
                                nw_grid
                            )
                        ),

                    "nw_max":
                        float(
                            np.max(
                                nw_grid
                            )
                        ),

                    "no_min":
                        float(
                            np.min(
                                no_grid
                            )
                        ),

                    "no_max":
                        float(
                            np.max(
                                no_grid
                            )
                        ),

                    "krw_max_field_min":
                        float(
                            np.min(
                                krw_grid
                            )
                        ),

                    "krw_max_field_max":
                        float(
                            np.max(
                                krw_grid
                            )
                        ),

                    "kro_max_field_min":
                        float(
                            np.min(
                                kro_grid
                            )
                        ),

                    "kro_max_field_max":
                        float(
                            np.max(
                                kro_grid
                            )
                        ),

                    "S0_cells":
                        len(
                            graph[
                                "s0_nodes"
                            ]
                        ),

                    "H1_cells":
                        len(
                            graph[
                                "h1_nodes"
                            ]
                        ),

                    "D1_cells":
                        len(
                            graph[
                                "nodes"
                            ]
                        ),

                    "checkpoint_inference_seconds":
                        inference_seconds[
                            rid
                        ],

                    "integration_seconds":
                        integration_seconds,

                    "all_9_times_passed":
                        True,
                }
            )

        # ------------------------------------------------------------------------------------------
        # Global 36-state outcome.
        # ------------------------------------------------------------------------------------------
        stage = "global_outcome"

        sci_gate(
            "all_4_realizations_all_9_times",
            completed_states
            == 36,
            completed_states,
        )

        max_b1_closure = max(
            float(
                row[
                    "B1_projection_relative_closure"
                ]
            )
            for row in time_rows
        )

        max_mass_closure = max(
            float(
                row[
                    "mass_relative_closure"
                ]
            )
            for row in time_rows
        )

        max_eos_closure = max(
            float(
                row[
                    "EOS_localPV_mass_relative_closure"
                ]
            )
            for row in time_rows
        )

        max_capacity_excess = max(
            float(
                row[
                    "max_capacity_excess_after_reconciliation_kg"
                ]
            )
            for row in time_rows
        )

        max_d1_capacity = max(
            float(
                row[
                    "D1_capacity_kg"
                ]
            )
            for row in time_rows
        )

        max_capacity_tol = max(
            1.0e-7,
            1.0e-11
            * max(
                max_d1_capacity,
                1.0,
            ),
        )

        sci_gate(
            "all_B1_projection_closures",
            max_b1_closure
            <= 1.0e-12,
            max_b1_closure,
        )

        sci_gate(
            "all_total_mass_closures",
            max_mass_closure
            <= 1.0e-10,
            max_mass_closure,
        )

        sci_gate(
            "all_EOS_localPV_mass_closures",
            max_eos_closure
            <= 1.0e-10,
            max_eos_closure,
        )

        sci_gate(
            "all_post_reconciliation_capacity_bounds",
            max_capacity_excess
            <= max_capacity_tol,
            [
                max_capacity_excess,
                max_capacity_tol,
            ],
        )

        # Immutable no-adaptation claims.
        for name in [
            "no_training",
            "no_checkpoint_reselection",
            "no_normalization_refit",
            "no_hyperparameter_retuning",
            "no_CR0004_Y_true_access",
            "no_CR0004_metric_recompute",
            "no_CR0004_reinference",
            "no_CR0004_teacher_regeneration",
            "no_second_OOD_exposure",
            "no_pressure_resolve",
            "no_Darcy_Q_recompute",
            "no_Pollock_retrace",
            "no_TOF_recompute",
            "no_constitutive_reseed",
            "no_halo_adaptation",
            "no_global_rescale",
            "no_mass_clipping_or_discard",
            "no_mapback_retuning",
            "no_CMG",
        ]:

            gate(
                name,
                True,
            )

        decision = {
            "milestone":
                MILESTONE,

            "status":
                STATUS_PASS,

            "protocol_id":
                PROTOCOL_ID,

            "checkpoint_sha256":
                EXPECTED_CHECKPOINT_SHA256,

            "checkpoint_best_epoch":
                EXPECTED_BEST_EPOCH,

            "all_four_AV3_realizations_integrated":
                True,

            "all_nine_canonical_times_integrated":
                True,

            "integrated_states":
                36,

            "local_pore_volume_capacity_used":
                True,

            "B1_component_mass_bridge_preserved":
                True,

            "SG7D_E37A_subsegment_deposition_preserved":
                True,

            "R7D_terminal_halo_semantics_preserved":
                True,

            "R7R7A_arithmetic_preserved_via_R7E_authority":
                True,

            "CR0004_frozen_A5R2_prediction_reused":
                True,

            "CR0004_Y_true_accessed":
                False,

            "CR0004_metric_recomputed":
                False,

            "CR0004_reinference":
                False,

            "CR0004_teacher_regenerated":
                False,

            "training":
                False,

            "checkpoint_reselection":
                False,

            "normalization_refit":
                False,

            "hyperparameter_retuning":
                False,

            "pressure_resolve":
                False,

            "Darcy_Q_recompute":
                False,

            "Pollock_retrace":
                False,

            "TOF_recompute":
                False,

            "halo_adaptation":
                False,

            "global_mass_rescale":
                False,

            "mass_clipping_or_discard":
                False,

            "CMG_validation":
                False,

            "AV3_final_outcome_freeze_authorized":
                True,

            "next":
                {
                    "milestone":
                        "POSTV16-AV3-F",

                    "authorized":
                        True,

                    "execution":
                        True,

                    "name":
                        "Final Spatial-Corey/Relative-Permeability Scientific Outcome Freeze and AV4 Handoff",
                },
        }

        summary = {
            "milestone":
                MILESTONE,

            "status":
                STATUS_PASS,

            "protocol_id":
                PROTOCOL_ID,

            "checkpoint_sha256":
                EXPECTED_CHECKPOINT_SHA256,

            "checkpoint_best_epoch":
                EXPECTED_BEST_EPOCH,

            "realizations_completed":
                4,

            "canonical_times_per_realization":
                9,

            "integrated_states":
                36,

            "max_B1_projection_relative_closure":
                max_b1_closure,

            "max_mass_relative_closure":
                max_mass_closure,

            "max_EOS_localPV_mass_relative_closure":
                max_eos_closure,

            "max_post_reconciliation_capacity_excess_kg":
                max_capacity_excess,

            "max_H1_capacity_fraction_used":
                max(
                    float(
                        row[
                            "H1_capacity_fraction_used"
                        ]
                    )
                    for row in time_rows
                ),

            "max_H1_occupied_cell_count":
                max(
                    int(
                        row[
                            "H1_occupied_cell_count"
                        ]
                    )
                    for row in time_rows
                ),

            "training":
                False,

            "CR0004_Y_true_accessed":
                False,

            "CR0004_metric_recomputed":
                False,

            "CR0004_reinference":
                False,

            "CMG_validation":
                False,

            "AV3_final_outcome_freeze_authorized":
                True,

            "next":
                decision[
                    "next"
                ],
        }

        output_files.update(
            {
                "PAD_Stream_POSTV16_AV3_A6_E_Summary.json":
                    json_bytes(
                        summary
                    ),

                "POSTV16_AV3_A6_E_Realization_Summary.csv":
                    csv_bytes(
                        realization_rows
                    ),

                "POSTV16_AV3_A6_E_Timewise_Integration_Audit.csv":
                    csv_bytes(
                        time_rows
                    ),

                "POSTV16_AV3_A6_E_Decision_Contract.json":
                    json_bytes(
                        decision
                    ),

                "POSTV16_AV3_A6_E_Final_Gate_Matrix.csv":
                    csv_bytes(
                        [
                            {
                                "gate": key,
                                **value,
                            }
                            for key, value in gates.items()
                        ]
                    ),
            }
        )

        immutable_publish(
            out,
            output_files,
        )

        manifest_rows = []

        for q in sorted(
            out.iterdir()
        ):

            if (
                q.is_file()
                and q.name
                != "POSTV16_AV3_A6_E_Artifact_Manifest.csv"
            ):

                manifest_rows.append(
                    {
                        "file":
                            q.name,

                        "sha256":
                            sha256_file(
                                q
                            ),

                        "bytes":
                            q.stat().st_size,
                    }
                )

        immutable_publish(
            out,
            {
                "POSTV16_AV3_A6_E_Artifact_Manifest.csv":
                    csv_bytes(
                        manifest_rows
                    )
            },
        )

        print()
        print("=" * 214)
        print("POSTV16-AV3-A6-E: 36-STATE INTEGRATION PASS")
        print("=" * 214)
        print("Frozen checkpoint SHA256                  :", EXPECTED_CHECKPOINT_SHA256)
        print("Checkpoint epoch                           :", EXPECTED_BEST_EPOCH)
        print("Integrated states                          : 36 / 36")
        print("Max B1 projection relative closure         :", max_b1_closure)
        print("Max total mass relative closure            :", max_mass_closure)
        print("Max EOS local-PV relative closure          :", max_eos_closure)
        print("Max post-reconciliation capacity excess kg :", max_capacity_excess)
        print("Max H1 capacity fraction used              :", summary["max_H1_capacity_fraction_used"])
        print("Max H1 occupied cells                      :", summary["max_H1_occupied_cell_count"])
        print("CR0004 Y_true access                       : False")
        print("CR0004 metric recompute                    : False")
        print("CR0004 reinference                         : False")
        print("Training / reselection / refit / retune    : False / False / False / False")
        print("CMG                                         : Deferred")
        print("POSTV16-AV3-F                               : AUTHORIZED")
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

            "gates":
                gates,

            "completed_states":
                completed_states,

            "training":
                False,

            "CR0004_Y_true_accessed":
                False,

            "CR0004_metric_recomputed":
                False,

            "CR0004_reinference":
                False,

            "adaptation_authorized":
                False,

            "A6E_rerun_authorized":
                False,

            "AV3_final_outcome_freeze_authorized":
                False,
        }

        p = (
            fail_dir
            / "POSTV16_AV3_A6_E_Scientific_Fail_Report.json"
        )

        if not p.exists():
            p.write_bytes(
                json_bytes(
                    report
                )
            )

        print()
        print("=" * 214)
        print("POSTV16-AV3-A6-E: SCIENTIFIC FAIL")
        print("=" * 214)
        print("Failed stage  :", stage)
        print("Failed gate   :", exc.gate)
        print("Completed     :", completed_states, "/ 36")
        print("Adaptation    : NOT AUTHORIZED")
        print("Rerun         : NOT AUTHORIZED")
        print("AV3-F         : NOT AUTHORIZED")
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

            "gates":
                gates,

            "completed_states":
                completed_states,

            "training":
                False,

            "CR0004_Y_true_accessed":
                False,

            "CR0004_metric_recomputed":
                False,

            "CR0004_reinference":
                False,

            "A6E_rerun_authorized":
                False,

            "AV3_final_outcome_freeze_authorized":
                False,
        }

        p = (
            block_dir
            / "POSTV16_AV3_A6_E_Blocked_Report.json"
        )

        if not p.exists():
            p.write_bytes(
                json_bytes(
                    report
                )
            )

        print()
        print("=" * 214)
        print("POSTV16-AV3-A6-E: TECHNICAL BLOCK")
        print("=" * 214)
        print("Failed stage :", stage)
        print("Exception    :", repr(exc))
        print("Completed    :", completed_states, "/ 36")
        print("Rerun        : NOT AUTHORIZED")
        print("AV3-F        : NOT AUTHORIZED")
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
