#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any

import numpy as np


MILESTONE = "POSTV16-AV3-A5"

PROTOCOL_ID = (
    "POSTV16_AV3_A5_SPATIAL_COREY_RELPERM_13CHANNEL_PIRNN_"
    "TRAIN_BEST_VALIDATION_CHECKPOINT_FREEZE_ONE_TOUCH_OOD_V1"
)

STATUS_PASS = (
    "AV3A5_13CHANNEL_PIRNN_TRAINING_COMPLETE_BEST_VALIDATION_CHECKPOINT_"
    "FROZEN_LOCKED_OOD_TEACHER_GENERATED_ONCE_EVALUATED_ONCE"
)

STATUS_FAIL = (
    "AV3A5_TRAINING_OR_ONE_TOUCH_OOD_SCIENTIFIC_FAIL_"
    "NO_RETUNING_RESELECTION_OR_SECOND_OOD_AUTHORIZED"
)

STATUS_BLOCKED = "AV3A5_TECHNICAL_EXECUTION_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

PARENT_R2_COMMIT = "c9366a5e8b13fd788560e6eb8db80467930d3c0a"

# --------------------------------------------------------------------------------------------------
# Exact source lineage.
# --------------------------------------------------------------------------------------------------

R2 = (
    "PAD_Stream_POSTV16_AV3_A4_R2_"
    "Corrected_Certification_Teacher_Dataset_and_LockedOOD_Predictor.py"
)
R2_BLOB = "289901331e835afb44ff2f665fe9a6bbea2eac19"

R1 = (
    "PAD_Stream_POSTV16_AV3_A4_R1_"
    "Teacher_Certification_Failure_Semantics_Closure.py"
)
R1_BLOB = "cdd6c52de598cfc1674828d4d7918828e828f2ab"

A3 = (
    "PAD_Stream_POSTV16_AV3_A3_"
    "Transport_Teacher_Residual_and_PIRNN_Protocol_Freeze.py"
)
A3_BLOB = "40fe89c142e62aad750a749f0a8ae452574f28bd"

A2 = (
    "PAD_Stream_POSTV16_AV3_A2_"
    "Corey_Relperm_Field_Realization_Certification_and_Streamline_Sampling.py"
)
A2_BLOB = "e7d4f1b1e69ea3e756c4f41d7edb57e2ffd87d7b"

C2 = "PAD_Stream_V16C2_Multi_Coordinate_Streamline_Transport_Database_Assembly.py"
C2_BLOB = "21ff44de456102772c99f7ddc80898c9139a76db"

SOURCE_BLOBS = {
    R2: R2_BLOB,
    R1: R1_BLOB,
    A3: A3_BLOB,
    A2: A2_BLOB,
    C2: C2_BLOB,
}

# --------------------------------------------------------------------------------------------------
# Drive authorities.
# --------------------------------------------------------------------------------------------------

BASE = (
    Path("post_v16")
    / RID
    / "POSTV16_AV3_Corey_Relperm_Heterogeneity"
)

R2_REL = (
    BASE
    / "POSTV16_AV3_A4_R2_Corrected_Teacher_Dataset_and_LockedOOD_Predictor"
)

R2_SUMMARY = "PAD_Stream_POSTV16_AV3_A4_R2_Summary.json"
R2_TRAINVAL = "POSTV16_AV3_A4_R2_TrainValidation_13Channel_Transport_Dataset.npz"
R2_OOD = "POSTV16_AV3_A4_R2_LockedOOD_13Channel_Predictor_Only_Dataset.npz"
R2_SIDECAR = "POSTV16_AV3_A4_R2_Spatial_Relperm_Physics_Sidecar.npz"
R2_NORM = "POSTV16_AV3_A4_R2_Corrected_TRAIN_Only_Normalization.npz"
R2_PAIRS = "POSTV16_AV3_A4_R2_Adjacent_Time_Physics_Pair_Registry.npz"
R2_TEACHER = "POSTV16_AV3_A4_R2_Teacher_Certification_By_Realization.csv"
R2_HANDOFF = "POSTV16_AV3_A4_R2_A5_Handoff_Contract.json"
R2_DECISION = "POSTV16_AV3_A4_R2_Decision_Contract.json"
R2_MANIFEST = "POSTV16_AV3_A4_R2_Artifact_Manifest.csv"

R2_STATUS = (
    "AV3A4R2_CORRECTED_CERTIFICATION_TRAIN_VALIDATION_TEACHERS_"
    "13CHANNEL_DATASET_PHYSICS_SIDECAR_AND_LOCKED_OOD_PREDICTOR_ONLY_PASS"
)

A3_REL = (
    BASE
    / "POSTV16_AV3_A3_Transport_Teacher_Residual_and_PIRNN_Protocol_Freeze"
)

A3_MODEL = "POSTV16_AV3_A3_13Channel_PIRNN_Training_Protocol.json"
A3_RESIDUAL = "POSTV16_AV3_A3_Differentiable_Physics_Residual_Contract.json"
A3_DATASET = "POSTV16_AV3_A3_Teacher_Dataset_and_Leakage_Firewall.json"
A3_MANIFEST = "POSTV16_AV3_A3_Artifact_Manifest.csv"

A2_REL = (
    BASE
    / "POSTV16_AV3_A2_Corey_Relperm_Field_Realization_Certification_and_Streamline_Sampling"
)

ORIGINAL_A4_FAIL = (
    BASE
    / "POSTV16_AV3_A4_SCIENTIFIC_FAIL"
    / "POSTV16_AV3_A4_Scientific_Fail_Report.json"
)

ORIGINAL_A4_FAIL_SHA256 = (
    "1fdc0aeb7c462b7161525d52b1aa381b80885ffba00a4afa80875a67861cd08d"
)

OUT_REL = (
    BASE
    / "POSTV16_AV3_A5_PIRNN_Training_Checkpoint_and_OneTouch_OOD"
)

FAIL_REL = BASE / "POSTV16_AV3_A5_SCIENTIFIC_FAIL"
BLOCK_REL = BASE / "POSTV16_AV3_A5_BLOCKED"

CHECKPOINT = "POSTV16_AV3_A5_Best_Validation_Model.keras"
CHECKPOINT_FREEZE = "POSTV16_AV3_A5_Best_Validation_Checkpoint_Freeze.json"
OOD_MARKER = "POSTV16_AV3_A5_LOCKED_OOD_OPENED.marker"

# --------------------------------------------------------------------------------------------------
# Frozen dimensions / protocol.
# --------------------------------------------------------------------------------------------------

NN = 201
NSL = 1078
NT = 9
CH = 13

DAYS = np.asarray(
    [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0],
    dtype=np.float64,
)

ORIGIN_CENTER_M = np.asarray(
    [3.048, 3.048, 0.6096],
    dtype=np.float64,
)

DX = 6.096
DY = 6.096
DZ = 1.2192

CHANNELS13 = [
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
]

TRAIN_PROFILES = 19404
VAL_PROFILES = 9702
OOD_PROFILES = 9702

TRAIN_PAIRS = 17248
VAL_PAIRS = 8624
OOD_PAIRS = 8624

MODEL_PARAMETERS = 53057

SEED = 16021
BATCH = 64
MAX_EPOCHS = 300
EARLY_STOP_PATIENCE = 30
EARLY_STOP_MIN_DELTA = 1.0e-6
LR_FACTOR = 0.5
LR_PATIENCE = 10
MIN_LR = 1.0e-6
INITIAL_LR = 1.0e-3

LAMBDA_PHYS = 0.01
R0 = 1.0

SWC = 0.20
SOR = 0.20
SPAN = 0.60
SW_INJ = 0.799

MU_W = 0.5
MU_O = 5.0
PE_C = 22.0
LAMBDA_C = 2.0
EPS = 1.0e-12


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
            raise GateError("manifest_SHA:" + fn)

    return manifest


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


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:
        raise GateError("cannot_load_module:" + str(path))

    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)

    return module


def predictive_metrics(
    prediction: np.ndarray,
    truth: np.ndarray,
) -> dict[str, float]:

    P = np.asarray(
        prediction,
        dtype=np.float64,
    )

    T = np.asarray(
        truth,
        dtype=np.float64,
    )

    E = P - T

    mse = float(
        np.mean(
            E * E
        )
    )

    return {
        "mse": mse,
        "rmse": float(
            np.sqrt(
                mse
            )
        ),
        "mae": float(
            np.mean(
                np.abs(
                    E
                )
            )
        ),
        "max_abs_error": float(
            np.max(
                np.abs(
                    E
                )
            )
        ),
        "prediction_min": float(
            np.min(
                P
            )
        ),
        "prediction_max": float(
            np.max(
                P
            )
        ),
    }


def structural_metrics(
    prediction: np.ndarray,
    time_index: np.ndarray,
    streamline_index: np.ndarray,
) -> dict[str, float]:

    P = np.asarray(
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

    spatial_positive_fraction = float(
        np.mean(
            np.diff(
                P,
                axis=1,
            )
            > 1.0e-7
        )
    )

    neg = 0
    total = 0

    for stream in np.unique(
        sl
    ):

        q = np.where(
            sl == stream
        )[0]

        q = q[
            np.argsort(
                ti[q]
            )
        ]

        dd = np.diff(
            P[q],
            axis=0,
        )

        neg += int(
            np.sum(
                dd < -1.0e-6
            )
        )

        total += int(
            dd.size
        )

    return {
        "spatial_positive_fraction": spatial_positive_fraction,
        "temporal_negative_fraction": float(
            neg / total
            if total
            else 0.0
        ),
    }


def build_pairs(
    realization_index: np.ndarray,
    time_index: np.ndarray,
    streamline_index: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:

    ri = np.asarray(
        realization_index,
        dtype=np.int64,
    )

    ti = np.asarray(
        time_index,
        dtype=np.int64,
    )

    sl = np.asarray(
        streamline_index,
        dtype=np.int64,
    )

    lookup = {}

    for i in range(
        len(
            ri
        )
    ):

        key = (
            int(
                ri[i]
            ),
            int(
                ti[i]
            ),
            int(
                sl[i]
            ),
        )

        if key in lookup:
            raise GateError(
                "duplicate_pair_key:"
                + repr(
                    key
                )
            )

        lookup[
            key
        ] = i

    A = []
    B = []

    for r in sorted(
        set(
            int(x)
            for x in ri
        )
    ):

        for s in range(
            NSL
        ):

            for t in range(
                NT - 1
            ):

                A.append(
                    lookup[
                        (
                            r,
                            t,
                            s,
                        )
                    ]
                )

                B.append(
                    lookup[
                        (
                            r,
                            t + 1,
                            s,
                        )
                    ]
                )

    return (
        np.asarray(
            A,
            dtype=np.int64,
        ),
        np.asarray(
            B,
            dtype=np.int64,
        ),
    )


def self_test() -> None:
    assert len(CHANNELS13) == 13
    assert MODEL_PARAMETERS == 53057
    assert TRAIN_PAIRS == 17248
    assert VAL_PAIRS == 8624
    assert OOD_PAIRS == 8624

    ri = np.repeat(
        3,
        OOD_PROFILES,
    )

    ti = np.repeat(
        np.arange(
            NT,
            dtype=np.int64,
        ),
        NSL,
    )

    sl = np.tile(
        np.arange(
            NSL,
            dtype=np.int64,
        ),
        NT,
    )

    a, b = build_pairs(
        ri,
        ti,
        sl,
    )

    assert len(a) == OOD_PAIRS
    assert np.all(
        ti[b]
        - ti[a]
        == 1
    )

    print(
        "POSTV16-AV3-A5 training/checkpoint/one-touch-OOD self-test: PASS"
    )


def main(
    root: Path,
    drive: Path,
) -> int:

    import tensorflow as tf

    gates: dict[str, dict[str, Any]] = {}

    stage = "preflight"

    training_started = False
    checkpoint_frozen = False
    locked_ood_opened = False
    locked_ood_teacher_generated = False
    locked_ood_evaluated = False

    out = drive / OUT_REL
    fail_dir = drive / FAIL_REL
    block_dir = drive / BLOCK_REL

    checkpoint = out / CHECKPOINT
    checkpoint_freeze = out / CHECKPOINT_FREEZE
    ood_marker = out / OOD_MARKER

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

    print("=" * 210)
    print(
        "POSTV16-AV3-A5 — 13-CHANNEL PI-RNN TRAINING / BEST-VALIDATION "
        "CHECKPOINT FREEZE / ONE-TOUCH LOCKED-OOD"
    )
    print("=" * 210)
    print("TRAIN ONLY ON AV3CR0001 + AV3CR0002.")
    print("CHECKPOINT SELECTION ONLY BY MINIMUM VALIDATION TOTAL OBJECTIVE.")
    print("NO AV3CR0004 Y UNTIL CHECKPOINT FREEZE IS COMPLETE.")
    print("AFTER CHECKPOINT FREEZE: ONE AV3CR0004 TEACHER GENERATION + ONE EVALUATION ONLY.")
    print("NO POST-OOD TRAINING, RETUNING, RESELECTION, NORMALIZATION REFIT, OR SECOND OOD.")
    print("NO MAPBACK. NO LP. NO CMG.")
    print()

    try:
        root = root.resolve()
        drive = drive.resolve()

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
            "repository_parent_is_AV3A4R2_commit",
            parent == PARENT_R2_COMMIT,
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

        gate(
            "original_A4_fail_present",
            (drive / ORIGINAL_A4_FAIL).is_file(),
            str(
                drive
                / ORIGINAL_A4_FAIL
            ),
        )

        gate(
            "original_A4_fail_SHA_exact",
            sha256_file(
                drive
                / ORIGINAL_A4_FAIL
            )
            == ORIGINAL_A4_FAIL_SHA256,
            sha256_file(
                drive
                / ORIGINAL_A4_FAIL
            ),
        )

        # ------------------------------------------------------------------------------------------
        # Pre-existing outcome / one-touch firewall.
        # ------------------------------------------------------------------------------------------
        stage = "preexisting_state_firewall"

        gate(
            "no_preexisting_A5_checkpoint",
            not checkpoint.exists(),
            str(
                checkpoint
            ),
        )

        gate(
            "no_preexisting_A5_checkpoint_freeze",
            not checkpoint_freeze.exists(),
            str(
                checkpoint_freeze
            ),
        )

        gate(
            "no_preexisting_A5_OOD_marker",
            not ood_marker.exists(),
            str(
                ood_marker
            ),
        )

        # ------------------------------------------------------------------------------------------
        # Bind R2 PASS artifacts.
        # ------------------------------------------------------------------------------------------
        stage = "R2_binding"

        r2 = drive / R2_REL

        gate(
            "R2_output_present",
            r2.is_dir(),
            str(
                r2
            ),
        )

        m2 = verify_manifest(
            r2,
            R2_MANIFEST,
        )

        gate(
            "R2_manifest_SHA_closure",
            len(
                m2
            )
            == 11,
            len(
                m2
            ),
        )

        summary2 = load_json(
            r2
            / R2_SUMMARY
        )

        decision2 = load_json(
            r2
            / R2_DECISION
        )

        handoff2 = load_json(
            r2
            / R2_HANDOFF
        )

        gate(
            "R2_status_exact",
            summary2[
                "status"
            ]
            == R2_STATUS,
            summary2[
                "status"
            ],
        )

        gate(
            "R2_original_A4_fail_preserved",
            summary2[
                "original_AV3A4_scientific_FAIL_preserved"
            ]
            is True,
        )

        gate(
            "R2_original_A4_fail_SHA_exact",
            summary2[
                "original_AV3A4_fail_SHA256"
            ]
            == ORIGINAL_A4_FAIL_SHA256,
            summary2[
                "original_AV3A4_fail_SHA256"
            ],
        )

        gate(
            "R2_three_teachers_certified",
            int(
                summary2[
                    "teacher_realizations_certified"
                ]
            )
            == 3,
        )

        gate(
            "R2_OOD_target_still_closed",
            summary2[
                "LOCKED_OOD_target_generated"
            ]
            is False,
        )

        gate(
            "R2_A5_authorized",
            decision2[
                "AV3_A5_authorized"
            ]
            is True,
        )

        gate(
            "R2_A5_execution_authorized",
            handoff2[
                "authorized"
            ]
            is True
            and handoff2[
                "execution"
            ]
            is True
            and handoff2[
                "milestone"
            ]
            == "POSTV16-AV3-A5",
        )

        gate(
            "R2_model_contract_exact",
            handoff2[
                "frozen_model"
            ][
                "nodes"
            ]
            == 201
            and handoff2[
                "frozen_model"
            ][
                "input_channels"
            ]
            == 13
            and handoff2[
                "frozen_model"
            ][
                "parameters"
            ]
            == MODEL_PARAMETERS
            and handoff2[
                "frozen_model"
            ][
                "objective"
            ]
            == "L_data + 0.01 L_phys",
        )

        # ------------------------------------------------------------------------------------------
        # Bind A3 exact model / residual protocol.
        # ------------------------------------------------------------------------------------------
        stage = "A3_protocol_binding"

        a3 = drive / A3_REL

        m3 = verify_manifest(
            a3,
            A3_MANIFEST,
        )

        gate(
            "A3_manifest_SHA_closure",
            len(
                m3
            )
            == 10,
            len(
                m3
            ),
        )

        model_contract = load_json(
            a3
            / A3_MODEL
        )

        residual_contract = load_json(
            a3
            / A3_RESIDUAL
        )

        dataset_contract = load_json(
            a3
            / A3_DATASET
        )

        gate(
            "A3_channel_order_exact",
            model_contract[
                "channel_order"
            ]
            == CHANNELS13,
            model_contract[
                "channel_order"
            ],
        )

        gate(
            "A3_architecture_exact",
            model_contract[
                "nodes"
            ]
            == 201
            and model_contract[
                "input_channels"
            ]
            == 13
            and model_contract[
                "LSTM_layers"
            ]
            == 2
            and model_contract[
                "hidden_units"
            ]
            == 64
            and model_contract[
                "parameter_count"
            ]
            == MODEL_PARAMETERS,
        )

        gate(
            "A3_optimizer_exact",
            model_contract[
                "optimizer"
            ][
                "name"
            ]
            == "Adam"
            and float(
                model_contract[
                    "optimizer"
                ][
                    "learning_rate"
                ]
            )
            == INITIAL_LR,
        )

        gate(
            "A3_training_hyperparameters_exact",
            model_contract[
                "batch_size"
            ]
            == BATCH
            and model_contract[
                "max_epochs"
            ]
            == MAX_EPOCHS
            and model_contract[
                "random_seed"
            ]
            == SEED
            and model_contract[
                "early_stopping"
            ][
                "patience"
            ]
            == EARLY_STOP_PATIENCE
            and float(
                model_contract[
                    "early_stopping"
                ][
                    "min_delta"
                ]
            )
            == EARLY_STOP_MIN_DELTA
            and float(
                model_contract[
                    "lr_schedule"
                ][
                    "factor"
                ]
            )
            == LR_FACTOR
            and model_contract[
                "lr_schedule"
            ][
                "patience"
            ]
            == LR_PATIENCE
            and float(
                model_contract[
                    "lr_schedule"
                ][
                    "min_learning_rate"
                ]
            )
            == MIN_LR,
        )

        gate(
            "A3_objective_exact",
            float(
                model_contract[
                    "objective"
                ][
                    "lambda_phys"
                ]
            )
            == LAMBDA_PHYS
            and float(
                model_contract[
                    "objective"
                ][
                    "R0"
                ]
            )
            == R0,
        )

        gate(
            "A3_residual_interior_1_199",
            residual_contract[
                "loss_domain"
            ]
            == "interior nodes j=1..199 only",
        )

        gate(
            "A3_residual_same_face_algebra",
            residual_contract[
                "advection_term"
            ][
                "face_rule"
            ]
            == "same positive-upwind saturation+local-p rule as teacher"
            and residual_contract[
                "capillary_term"
            ][
                "Dtilde_rule"
            ]
            == "same local constitutive normalization as teacher",
        )

        gate(
            "A3_OOD_one_touch_contract",
            "one teacher generation + one evaluation only"
            in dataset_contract[
                "locked_OOD_after_checkpoint"
            ],
        )

        # ------------------------------------------------------------------------------------------
        # Load R2 TRAIN/VALIDATION dataset and exact physics sidecars/pair registry.
        # ------------------------------------------------------------------------------------------
        stage = "dataset_binding"

        with np.load(
            r2
            / R2_TRAINVAL,
            allow_pickle=False,
        ) as z:

            X = np.asarray(
                z[
                    "X_required_13"
                ],
                dtype=np.float32,
            )

            Y = np.asarray(
                z[
                    "Y_transport"
                ],
                dtype=np.float32,
            )

            realization_index = np.asarray(
                z[
                    "realization_index"
                ],
                dtype=np.int64,
            )

            time_index = np.asarray(
                z[
                    "time_index"
                ],
                dtype=np.int64,
            )

            streamline_index = np.asarray(
                z[
                    "streamline_index"
                ],
                dtype=np.int64,
            )

            partition_code = np.asarray(
                z[
                    "partition_code"
                ],
                dtype=np.int8,
            )

            eta_sequence = np.asarray(
                z[
                    "target_eta_sequence"
                ],
                dtype=np.float32,
            )

            target_days = np.asarray(
                z[
                    "target_time_days"
                ],
                dtype=np.float32,
            )

            channel_names = [
                str(x)
                for x in z[
                    "channel_names"
                ].tolist()
            ]

        gate(
            "trainval_X_shape_exact",
            X.shape
            == (
                TRAIN_PROFILES
                + VAL_PROFILES,
                NN,
                CH,
            ),
            X.shape,
        )

        gate(
            "trainval_Y_shape_exact",
            Y.shape
            == (
                TRAIN_PROFILES
                + VAL_PROFILES,
                NN,
            ),
            Y.shape,
        )

        gate(
            "channel_names_exact",
            channel_names
            == CHANNELS13,
            channel_names,
        )

        gate(
            "eta_sequence_constant_across_nodes",
            float(
                np.max(
                    np.ptp(
                        eta_sequence,
                        axis=1,
                    )
                )
            )
            <= 1.0e-7,
            float(
                np.max(
                    np.ptp(
                        eta_sequence,
                        axis=1,
                    )
                )
            ),
        )

        eta_scalar = eta_sequence[
            :,
            0,
        ].astype(
            np.float32
        )

        train_samples = np.flatnonzero(
            partition_code
            == 0
        )

        val_samples = np.flatnonzero(
            partition_code
            == 1
        )

        gate(
            "TRAIN_sample_count_exact",
            len(
                train_samples
            )
            == TRAIN_PROFILES,
            len(
                train_samples
            ),
        )

        gate(
            "VALIDATION_sample_count_exact",
            len(
                val_samples
            )
            == VAL_PROFILES,
            len(
                val_samples
            ),
        )

        with np.load(
            r2
            / R2_PAIRS,
            allow_pickle=False,
        ) as z:

            train_a = np.asarray(
                z[
                    "TRAIN_sample_index_a"
                ],
                dtype=np.int64,
            )

            train_b = np.asarray(
                z[
                    "TRAIN_sample_index_b"
                ],
                dtype=np.int64,
            )

            val_a = np.asarray(
                z[
                    "VALIDATION_sample_index_a"
                ],
                dtype=np.int64,
            )

            val_b = np.asarray(
                z[
                    "VALIDATION_sample_index_b"
                ],
                dtype=np.int64,
            )

            gate(
                "pair_registry_counts_exact",
                int(
                    z[
                        "TRAIN_pair_count"
                    ][0]
                )
                == TRAIN_PAIRS
                and int(
                    z[
                        "VALIDATION_pair_count"
                    ][0]
                )
                == VAL_PAIRS
                and int(
                    z[
                        "LOCKED_OOD_pair_count"
                    ][0]
                )
                == 0,
            )

        sci_gate(
            "TRAIN_pair_count_exact",
            len(
                train_a
            )
            == TRAIN_PAIRS,
            len(
                train_a
            ),
        )

        sci_gate(
            "VALIDATION_pair_count_exact",
            len(
                val_a
            )
            == VAL_PAIRS,
            len(
                val_a
            ),
        )

        for name, a, b, part in [
            (
                "TRAIN",
                train_a,
                train_b,
                0,
            ),
            (
                "VALIDATION",
                val_a,
                val_b,
                1,
            ),
        ]:

            sci_gate(
                f"{name}_pair_identity",
                np.array_equal(
                    realization_index[
                        a
                    ],
                    realization_index[
                        b
                    ],
                )
                and np.array_equal(
                    streamline_index[
                        a
                    ],
                    streamline_index[
                        b
                    ],
                )
                and np.array_equal(
                    time_index[
                        b
                    ],
                    time_index[
                        a
                    ]
                    + 1,
                )
                and np.all(
                    partition_code[
                        a
                    ]
                    == part
                )
                and np.all(
                    partition_code[
                        b
                    ]
                    == part
                ),
            )

        with np.load(
            r2
            / R2_SIDECAR,
            allow_pickle=False,
        ) as z:

            # Preserve native float64 geometry for authority/integrity checks.
            # Create separate float32 copies only for the differentiable
            # TensorFlow residual used during training.
            metric_M_native = np.asarray(
                z[
                    "metric_M"
                ],
                dtype=np.float64,
            )

            metric_M_face_native = np.asarray(
                z[
                    "metric_M_face"
                ],
                dtype=np.float64,
            )

            control_volume_native = np.asarray(
                z[
                    "control_volume_dtheta"
                ],
                dtype=np.float64,
            )

            dtheta_center_native = np.asarray(
                z[
                    "dtheta_center"
                ],
                dtype=np.float64,
            )

            metric_M = metric_M_native.astype(
                np.float32
            )

            metric_M_face = metric_M_face_native.astype(
                np.float32
            )

            control_volume = control_volume_native.astype(
                np.float32
            )

            dtheta_center = dtheta_center_native.astype(
                np.float32
            )

            phi_sequence = np.asarray(
                z[
                    "phi_sequence"
                ],
                dtype=np.float32,
            )

            nw_sequence = np.asarray(
                z[
                    "nw_sequence"
                ],
                dtype=np.float32,
            )

            no_sequence = np.asarray(
                z[
                    "no_sequence"
                ],
                dtype=np.float32,
            )

            krw_sequence = np.asarray(
                z[
                    "krw_max_sequence"
                ],
                dtype=np.float32,
            )

            kro_sequence = np.asarray(
                z[
                    "kro_max_sequence"
                ],
                dtype=np.float32,
            )

        gate(
            "physics_sidecar_shapes_exact",
            metric_M.shape
            == (
                4,
                NSL,
                NN,
            )
            and metric_M_face.shape
            == (
                4,
                NSL,
                NN
                + 1,
            )
            and control_volume.shape
            == (
                4,
                NSL,
                NN,
            )
            and dtheta_center.shape
            == (
                4,
                NSL,
                NN
                - 1,
            )
            and phi_sequence.shape
            == (
                4,
                NSL,
                NN,
            )
            and nw_sequence.shape
            == (
                4,
                NSL,
                NN,
            )
            and no_sequence.shape
            == (
                4,
                NSL,
                NN,
            )
            and krw_sequence.shape
            == (
                4,
                NSL,
                NN,
            )
            and kro_sequence.shape
            == (
                4,
                NSL,
                NN,
            ),
        )

        # Re-check the precision-order authority that closed the external R2 audit wrapper defect.
        for ridx, rid in enumerate(
            [
                "AV3CR0001",
                "AV3CR0002",
                "AV3CR0003",
                "AV3CR0004",
            ]
        ):

            a2_file = (
                drive
                / A2_REL
                / f"POSTV16_AV3_A2_{rid}_Corey_Relperm_Field_and_Streamline_Sampling.npz"
            )

            gate(
                f"{rid}_A2_authority_present",
                a2_file.is_file(),
                a2_file.name,
            )

            with np.load(
                a2_file,
                allow_pickle=False,
            ) as z:

                nw64 = np.asarray(
                    z[
                        "nw_streamline"
                    ],
                    dtype=np.float64,
                )

                no64 = np.asarray(
                    z[
                        "no_streamline"
                    ],
                    dtype=np.float64,
                )

                kw64 = np.asarray(
                    z[
                        "krw_max_streamline"
                    ],
                    dtype=np.float64,
                )

                ko64 = np.asarray(
                    z[
                        "kro_max_streamline"
                    ],
                    dtype=np.float64,
                )

            gate(
                f"{rid}_sidecar_raw_A2_float32_exact",
                np.array_equal(
                    nw_sequence[
                        ridx
                    ],
                    nw64.astype(
                        np.float32
                    ),
                )
                and np.array_equal(
                    no_sequence[
                        ridx
                    ],
                    no64.astype(
                        np.float32
                    ),
                )
                and np.array_equal(
                    krw_sequence[
                        ridx
                    ],
                    kw64.astype(
                        np.float32
                    ),
                )
                and np.array_equal(
                    kro_sequence[
                        ridx
                    ],
                    ko64.astype(
                        np.float32
                    ),
                ),
            )

            expected_p4 = np.stack(
                [
                    nw64
                    - 3.0,
                    no64
                    - 3.0,
                    (
                        kw64
                        - 0.80
                    )
                    / 0.20,
                    (
                        ko64
                        - 0.80
                    )
                    / 0.20,
                ],
                axis=-1,
            ).astype(
                np.float32
            )

            if ridx < 3:

                base = (
                    ridx
                    * NT
                    * NSL
                )

                actual_p4 = X[
                    base:base + NSL,
                    :,
                    9:13,
                ]

            else:

                with np.load(
                    r2
                    / R2_OOD,
                    allow_pickle=False,
                ) as z:

                    actual_p4 = np.asarray(
                        z[
                            "X_required_13"
                        ][
                            :NSL,
                            :,
                            9:13,
                        ],
                        dtype=np.float32,
                    )

            gate(
                f"{rid}_normalized_A2_to_X13_exact",
                np.array_equal(
                    actual_p4,
                    expected_p4,
                ),
            )

        # ------------------------------------------------------------------------------------------
        # Load OOD predictors now, still without Y.
        # ------------------------------------------------------------------------------------------
        stage = "OOD_predictor_binding"

        with np.load(
            r2
            / R2_OOD,
            allow_pickle=False,
        ) as z:

            ood_files = set(
                z.files
            )

            gate(
                "OOD_Y_absent_before_checkpoint",
                "Y_transport"
                not in ood_files
                and "Y"
                not in ood_files
                and "teacher_Y"
                not in ood_files,
                sorted(
                    ood_files
                ),
            )

            X_ood = np.asarray(
                z[
                    "X_required_13"
                ],
                dtype=np.float32,
            )

            ri_ood = np.asarray(
                z[
                    "realization_index"
                ],
                dtype=np.int64,
            )

            ti_ood = np.asarray(
                z[
                    "time_index"
                ],
                dtype=np.int64,
            )

            sl_ood = np.asarray(
                z[
                    "streamline_index"
                ],
                dtype=np.int64,
            )

            eta_ood = np.asarray(
                z[
                    "target_eta_sequence"
                ],
                dtype=np.float32,
            )[
                :,
                0,
            ]

            days_ood = np.asarray(
                z[
                    "target_time_days"
                ],
                dtype=np.float64,
            )

        gate(
            "OOD_X13_shape_exact",
            X_ood.shape
            == (
                OOD_PROFILES,
                NN,
                CH,
            ),
            X_ood.shape,
        )

        # ------------------------------------------------------------------------------------------
        # Build exact frozen model + differentiable residual.
        # ------------------------------------------------------------------------------------------
        stage = "model_build"

        try:
            tf.config.experimental.enable_op_determinism()
        except Exception:
            pass

        tf.keras.utils.set_random_seed(
            SEED
        )

        def build_model():

            inp = tf.keras.Input(
                shape=(
                    NN,
                    CH,
                ),
                name="AV3_required_13channel_sequence",
            )

            x = tf.keras.layers.LSTM(
                64,
                return_sequences=True,
                name="lstm_1",
            )(
                inp
            )

            x = tf.keras.layers.LSTM(
                64,
                return_sequences=True,
                name="lstm_2",
            )(
                x
            )

            x = tf.keras.layers.TimeDistributed(
                tf.keras.layers.Dense(
                    1
                ),
                name="td_dense",
            )(
                x
            )

            x = tf.keras.layers.Activation(
                "sigmoid",
                name="bounded_sigmoid",
            )(
                x
            )

            x = tf.keras.layers.Rescaling(
                SPAN,
                offset=SWC,
                name="bounded_saturation",
            )(
                x
            )

            outp = tf.keras.layers.Reshape(
                (
                    NN,
                ),
                name="Sw_sequence",
            )(
                x
            )

            return tf.keras.Model(
                inp,
                outp,
                name="PAD_Stream_AV3_A5",
            )

        model = build_model()

        sci_gate(
            "model_parameter_count_53057",
            model.count_params()
            == MODEL_PARAMETERS,
            model.count_params(),
        )

        optimizer = tf.keras.optimizers.Adam(
            INITIAL_LR
        )

        def tf_fw(
            S,
            nw,
            no,
            krw_max,
            kro_max,
        ):

            Se = tf.clip_by_value(
                (
                    S
                    - SWC
                )
                / SPAN,
                0.0,
                1.0,
            )

            krw = (
                krw_max
                * tf.pow(
                    Se,
                    nw,
                )
            )

            kro = (
                kro_max
                * tf.pow(
                    1.0
                    - Se,
                    no,
                )
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

        def tf_dshape(
            S,
            nw,
            no,
            krw_max,
            kro_max,
        ):

            Se = tf.clip_by_value(
                (
                    S
                    - SWC
                )
                / SPAN,
                1.0e-6,
                1.0
                - 1.0e-6,
            )

            kro = (
                kro_max
                * tf.pow(
                    1.0
                    - Se,
                    no,
                )
            )

            fw = tf_fw(
                S,
                nw,
                no,
                krw_max,
                kro_max,
            )

            raw = (
                kro
                * fw
                * tf.pow(
                    Se,
                    -1.0
                    / LAMBDA_C
                    - 1.0,
                )
            )

            Se_mid = tf.fill(
                tf.shape(
                    Se
                ),
                tf.constant(
                    0.5,
                    dtype=tf.float32,
                ),
            )

            S_mid = (
                SWC
                + SPAN
                * Se_mid
            )

            kro_mid = (
                kro_max
                * tf.pow(
                    1.0
                    - Se_mid,
                    no,
                )
            )

            fw_mid = tf_fw(
                S_mid,
                nw,
                no,
                krw_max,
                kro_max,
            )

            norm = (
                kro_mid
                * fw_mid
                * tf.pow(
                    Se_mid,
                    -1.0
                    / LAMBDA_C
                    - 1.0,
                )
            )

            return (
                raw
                / tf.maximum(
                    norm,
                    EPS,
                )
            )

        def physics_loss(
            Sa,
            Sb,
            eta_a,
            eta_b,
            M,
            M_face,
            cv,
            dtheta,
            phi,
            nw,
            no,
            krw_max,
            kro_max,
        ):

            Sm = (
                0.5
                * (
                    Sa
                    + Sb
                )
            )

            deta = tf.maximum(
                eta_b
                - eta_a,
                1.0e-8,
            )

            dS_deta = (
                (
                    Sb
                    - Sa
                )
                / deta[
                    :,
                    None,
                ]
            )

            # Positive-upwind local-p conservative face algebra for j=1..199.
            fw_nodes = tf_fw(
                Sm[
                    :,
                    1:-1,
                ],
                nw[
                    :,
                    1:-1,
                ],
                no[
                    :,
                    1:-1,
                ],
                krw_max[
                    :,
                    1:-1,
                ],
                kro_max[
                    :,
                    1:-1,
                ],
            )

            fw_inlet = tf_fw(
                tf.fill(
                    [
                        tf.shape(
                            Sm
                        )[
                            0
                        ]
                    ],
                    tf.constant(
                        SW_INJ,
                        dtype=tf.float32,
                    ),
                ),
                nw[
                    :,
                    0,
                ],
                no[
                    :,
                    0,
                ],
                krw_max[
                    :,
                    0,
                ],
                kro_max[
                    :,
                    0,
                ],
            )

            F_left = tf.concat(
                [
                    fw_inlet[
                        :,
                        None,
                    ],
                    fw_nodes[
                        :,
                        :-1,
                    ],
                ],
                axis=1,
            )

            F_right = fw_nodes

            advection = (
                F_right
                - F_left
            ) / cv[
                :,
                1:-1,
            ]

            # Exact A3 capillary face algebra.
            D_node = tf_dshape(
                Sm,
                nw,
                no,
                krw_max,
                kro_max,
            )

            D_face = (
                0.5
                * (
                    D_node[
                        :,
                        :-1,
                    ]
                    + D_node[
                        :,
                        1:,
                    ]
                )
            )

            grad = (
                Sm[
                    :,
                    1:
                ]
                - Sm[
                    :,
                    :-1
                ]
            ) / dtheta

            G_face = (
                D_face
                * M_face[
                    :,
                    1:-1,
                ]
                * grad
            )

            capillary_core = (
                M[
                    :,
                    1:-1,
                ]
                * (
                    G_face[
                        :,
                        1:
                    ]
                    - G_face[
                        :,
                        :-1
                    ]
                )
                / cv[
                    :,
                    1:-1,
                ]
            )

            R = (
                dS_deta[
                    :,
                    1:-1,
                ]
                + advection
                - (
                    phi[
                        :,
                        1:-1,
                    ]
                    / PE_C
                )
                * capillary_core
            )

            return (
                tf.reduce_mean(
                    tf.square(
                        R / R0
                    )
                )
            )

        # Physics sidecars as tf constants.
        M_tf = tf.constant(
            metric_M,
            dtype=tf.float32,
        )

        Mf_tf = tf.constant(
            metric_M_face,
            dtype=tf.float32,
        )

        cv_tf = tf.constant(
            control_volume,
            dtype=tf.float32,
        )

        dtheta_tf = tf.constant(
            dtheta_center,
            dtype=tf.float32,
        )

        phi_tf = tf.constant(
            phi_sequence,
            dtype=tf.float32,
        )

        nw_tf = tf.constant(
            nw_sequence,
            dtype=tf.float32,
        )

        no_tf = tf.constant(
            no_sequence,
            dtype=tf.float32,
        )

        krw_tf = tf.constant(
            krw_sequence,
            dtype=tf.float32,
        )

        kro_tf = tf.constant(
            kro_sequence,
            dtype=tf.float32,
        )

        @tf.function(
            reduce_retracing=True
        )
        def train_step(
            Xa,
            Xb,
            Ya,
            Yb,
            ea,
            eb,
            side_idx,
        ):

            M = tf.gather_nd(
                M_tf,
                side_idx,
            )

            Mf = tf.gather_nd(
                Mf_tf,
                side_idx,
            )

            cv = tf.gather_nd(
                cv_tf,
                side_idx,
            )

            dth = tf.gather_nd(
                dtheta_tf,
                side_idx,
            )

            phi = tf.gather_nd(
                phi_tf,
                side_idx,
            )

            nw = tf.gather_nd(
                nw_tf,
                side_idx,
            )

            no = tf.gather_nd(
                no_tf,
                side_idx,
            )

            kw = tf.gather_nd(
                krw_tf,
                side_idx,
            )

            ko = tf.gather_nd(
                kro_tf,
                side_idx,
            )

            with tf.GradientTape() as tape:

                Sa = model(
                    Xa,
                    training=True,
                )

                Sb = model(
                    Xb,
                    training=True,
                )

                data_loss = (
                    0.5
                    * (
                        tf.reduce_mean(
                            tf.square(
                                Sa
                                - Ya
                            )
                        )
                        + tf.reduce_mean(
                            tf.square(
                                Sb
                                - Yb
                            )
                        )
                    )
                )

                phys_loss = physics_loss(
                    Sa,
                    Sb,
                    ea,
                    eb,
                    M,
                    Mf,
                    cv,
                    dth,
                    phi,
                    nw,
                    no,
                    kw,
                    ko,
                )

                total = (
                    data_loss
                    + LAMBDA_PHYS
                    * phys_loss
                )

            gradients = tape.gradient(
                total,
                model.trainable_variables,
            )

            optimizer.apply_gradients(
                zip(
                    gradients,
                    model.trainable_variables,
                )
            )

            return (
                data_loss,
                phys_loss,
                total,
            )

        @tf.function(
            reduce_retracing=True
        )
        def eval_step(
            Xa,
            Xb,
            Ya,
            Yb,
            ea,
            eb,
            side_idx,
        ):

            M = tf.gather_nd(
                M_tf,
                side_idx,
            )

            Mf = tf.gather_nd(
                Mf_tf,
                side_idx,
            )

            cv = tf.gather_nd(
                cv_tf,
                side_idx,
            )

            dth = tf.gather_nd(
                dtheta_tf,
                side_idx,
            )

            phi = tf.gather_nd(
                phi_tf,
                side_idx,
            )

            nw = tf.gather_nd(
                nw_tf,
                side_idx,
            )

            no = tf.gather_nd(
                no_tf,
                side_idx,
            )

            kw = tf.gather_nd(
                krw_tf,
                side_idx,
            )

            ko = tf.gather_nd(
                kro_tf,
                side_idx,
            )

            Sa = model(
                Xa,
                training=False,
            )

            Sb = model(
                Xb,
                training=False,
            )

            data_loss = (
                0.5
                * (
                    tf.reduce_mean(
                        tf.square(
                            Sa
                            - Ya
                        )
                    )
                    + tf.reduce_mean(
                        tf.square(
                            Sb
                            - Yb
                        )
                    )
                )
            )

            phys_loss = physics_loss(
                Sa,
                Sb,
                ea,
                eb,
                M,
                Mf,
                cv,
                dth,
                phi,
                nw,
                no,
                kw,
                ko,
            )

            total = (
                data_loss
                + LAMBDA_PHYS
                * phys_loss
            )

            return (
                data_loss,
                phys_loss,
                total,
            )

        def pair_batch_arrays(
            a: np.ndarray,
            b: np.ndarray,
        ):

            side_idx = np.stack(
                [
                    realization_index[
                        a
                    ],
                    streamline_index[
                        a
                    ],
                ],
                axis=1,
            ).astype(
                np.int32
            )

            return (
                tf.convert_to_tensor(
                    X[
                        a
                    ],
                    dtype=tf.float32,
                ),
                tf.convert_to_tensor(
                    X[
                        b
                    ],
                    dtype=tf.float32,
                ),
                tf.convert_to_tensor(
                    Y[
                        a
                    ],
                    dtype=tf.float32,
                ),
                tf.convert_to_tensor(
                    Y[
                        b
                    ],
                    dtype=tf.float32,
                ),
                tf.convert_to_tensor(
                    eta_scalar[
                        a
                    ],
                    dtype=tf.float32,
                ),
                tf.convert_to_tensor(
                    eta_scalar[
                        b
                    ],
                    dtype=tf.float32,
                ),
                tf.convert_to_tensor(
                    side_idx,
                    dtype=tf.int32,
                ),
            )

        # ------------------------------------------------------------------------------------------
        # TRAIN / VALIDATION.
        # ------------------------------------------------------------------------------------------
        stage = "training"

        training_started = True

        tmp_dir = Path(
            tempfile.mkdtemp(
                prefix="AV3A5_"
            )
        )

        tmp_checkpoint = (
            tmp_dir
            / CHECKPOINT
        )

        best_validation_total = np.inf
        best_epoch = None

        early_stop_best = np.inf
        early_stop_wait = 0

        lr_wait = 0

        history_rows = []

        rng = np.random.default_rng(
            SEED
        )

        for epoch in range(
            1,
            MAX_EPOCHS
            + 1,
        ):

            order = rng.permutation(
                len(
                    train_a
                )
            )

            train_data_values = []
            train_phys_values = []
            train_total_values = []

            for start in range(
                0,
                len(
                    order
                ),
                BATCH,
            ):

                z = order[
                    start:start
                    + BATCH
                ]

                a = train_a[
                    z
                ]

                b = train_b[
                    z
                ]

                batch = pair_batch_arrays(
                    a,
                    b,
                )

                ld, lp, lt = train_step(
                    *batch
                )

                train_data_values.append(
                    float(
                        ld.numpy()
                    )
                )

                train_phys_values.append(
                    float(
                        lp.numpy()
                    )
                )

                train_total_values.append(
                    float(
                        lt.numpy()
                    )
                )

            val_data_values = []
            val_phys_values = []
            val_total_values = []

            for start in range(
                0,
                len(
                    val_a
                ),
                BATCH,
            ):

                a = val_a[
                    start:start
                    + BATCH
                ]

                b = val_b[
                    start:start
                    + BATCH
                ]

                batch = pair_batch_arrays(
                    a,
                    b,
                )

                ld, lp, lt = eval_step(
                    *batch
                )

                val_data_values.append(
                    float(
                        ld.numpy()
                    )
                )

                val_phys_values.append(
                    float(
                        lp.numpy()
                    )
                )

                val_total_values.append(
                    float(
                        lt.numpy()
                    )
                )

            tr_data = float(
                np.mean(
                    train_data_values
                )
            )

            tr_phys = float(
                np.mean(
                    train_phys_values
                )
            )

            tr_total = float(
                np.mean(
                    train_total_values
                )
            )

            val_data = float(
                np.mean(
                    val_data_values
                )
            )

            val_phys = float(
                np.mean(
                    val_phys_values
                )
            )

            val_total = float(
                np.mean(
                    val_total_values
                )
            )

            sci_gate(
                f"epoch_{epoch:03d}_finite",
                np.all(
                    np.isfinite(
                        [
                            tr_data,
                            tr_phys,
                            tr_total,
                            val_data,
                            val_phys,
                            val_total,
                        ]
                    )
                ),
                {
                    "train_total": tr_total,
                    "validation_total": val_total,
                },
            )

            current_lr = float(
                optimizer.learning_rate.numpy()
            )

            history_rows.append(
                {
                    "epoch": epoch,
                    "train_data": tr_data,
                    "train_phys": tr_phys,
                    "train_total": tr_total,
                    "validation_data": val_data,
                    "validation_phys": val_phys,
                    "validation_total": val_total,
                    "learning_rate": current_lr,
                }
            )

            # Strict minimum validation-total checkpoint authority.
            if val_total < best_validation_total:

                best_validation_total = val_total
                best_epoch = epoch

                model.save(
                    tmp_checkpoint,
                    overwrite=True,
                )

                lr_wait = 0

            else:
                lr_wait += 1

            # Frozen early-stop min_delta semantics.
            if (
                val_total
                < early_stop_best
                - EARLY_STOP_MIN_DELTA
            ):

                early_stop_best = val_total
                early_stop_wait = 0

            else:

                early_stop_wait += 1

            # Frozen ReduceLROnPlateau factor/patience/floor semantics.
            if lr_wait >= LR_PATIENCE:

                optimizer.learning_rate.assign(
                    max(
                        float(
                            optimizer.learning_rate.numpy()
                        )
                        * LR_FACTOR,
                        MIN_LR,
                    )
                )

                lr_wait = 0

            print(
                f"Epoch {epoch:03d}: "
                f"loss={tr_total:.9e} "
                f"data={tr_data:.9e} "
                f"phys={tr_phys:.9e} "
                f"val={val_total:.9e} "
                f"val_data={val_data:.9e} "
                f"val_phys={val_phys:.9e} "
                f"lr={float(optimizer.learning_rate.numpy()):.3e}"
            )

            if (
                early_stop_wait
                >= EARLY_STOP_PATIENCE
            ):

                print(
                    "Early stopping at epoch "
                    f"{epoch}; best validation total="
                    f"{best_validation_total:.12e} "
                    f"at epoch {best_epoch}"
                )

                break

        sci_gate(
            "best_checkpoint_created",
            tmp_checkpoint.is_file(),
            str(
                tmp_checkpoint
            ),
        )

        sci_gate(
            "best_validation_total_finite",
            np.isfinite(
                best_validation_total
            ),
            best_validation_total,
        )

        sci_gate(
            "best_epoch_defined",
            best_epoch is not None,
            best_epoch,
        )

        # ------------------------------------------------------------------------------------------
        # Freeze checkpoint BEFORE any OOD Y generation/opening.
        # ------------------------------------------------------------------------------------------
        stage = "checkpoint_freeze"

        out.mkdir(
            parents=True,
            exist_ok=True,
        )

        if checkpoint.exists():
            raise GateError(
                "checkpoint_preexists_at_freeze"
            )

        shutil.copy2(
            tmp_checkpoint,
            checkpoint,
        )

        checkpoint_sha = sha256_file(
            checkpoint
        )

        best_model = tf.keras.models.load_model(
            checkpoint
        )

        val_prediction = best_model.predict(
            X[
                val_samples
            ],
            batch_size=BATCH,
            verbose=0,
        ).astype(
            np.float64
        )

        val_truth = Y[
            val_samples
        ].astype(
            np.float64
        )

        validation_predictive = predictive_metrics(
            val_prediction,
            val_truth,
        )

        validation_structural = structural_metrics(
            val_prediction,
            time_index[
                val_samples
            ],
            streamline_index[
                val_samples
            ],
        )

        # Evaluate the FROZEN BEST checkpoint validation objective exactly
        # on the same validation pair registry. Do not use eval_step here:
        # eval_step closes over the end-of-training model object, whereas the
        # authority after checkpoint freeze is best_model loaded from CHECKPOINT.
        validation_data_values = []
        validation_phys_values = []
        validation_total_values = []

        for start in range(
            0,
            len(
                val_a
            ),
            BATCH,
        ):

            a = val_a[
                start:start
                + BATCH
            ]

            b = val_b[
                start:start
                + BATCH
            ]

            (
                Xa,
                Xb,
                Ya,
                Yb,
                ea,
                eb,
                side_idx,
            ) = pair_batch_arrays(
                a,
                b,
            )

            M = tf.gather_nd(
                M_tf,
                side_idx,
            )

            Mf = tf.gather_nd(
                Mf_tf,
                side_idx,
            )

            cv = tf.gather_nd(
                cv_tf,
                side_idx,
            )

            dth = tf.gather_nd(
                dtheta_tf,
                side_idx,
            )

            phi = tf.gather_nd(
                phi_tf,
                side_idx,
            )

            nw = tf.gather_nd(
                nw_tf,
                side_idx,
            )

            no = tf.gather_nd(
                no_tf,
                side_idx,
            )

            kw = tf.gather_nd(
                krw_tf,
                side_idx,
            )

            ko = tf.gather_nd(
                kro_tf,
                side_idx,
            )

            Sa = best_model(
                Xa,
                training=False,
            )

            Sb = best_model(
                Xb,
                training=False,
            )

            ld = (
                0.5
                * (
                    tf.reduce_mean(
                        tf.square(
                            Sa
                            - Ya
                        )
                    )
                    + tf.reduce_mean(
                        tf.square(
                            Sb
                            - Yb
                        )
                    )
                )
            )

            lp = physics_loss(
                Sa,
                Sb,
                ea,
                eb,
                M,
                Mf,
                cv,
                dth,
                phi,
                nw,
                no,
                kw,
                ko,
            )

            lt = (
                ld
                + LAMBDA_PHYS
                * lp
            )

            validation_data_values.append(
                float(
                    ld.numpy()
                )
            )

            validation_phys_values.append(
                float(
                    lp.numpy()
                )
            )

            validation_total_values.append(
                float(
                    lt.numpy()
                )
            )

        validation_objective = {
            "data": float(
                np.mean(
                    validation_data_values
                )
            ),
            "physics": float(
                np.mean(
                    validation_phys_values
                )
            ),
            "total": float(
                np.mean(
                    validation_total_values
                )
            ),
        }

        checkpoint_freeze_payload = {
            "milestone": MILESTONE,
            "protocol_id": PROTOCOL_ID,
            "checkpoint_file": CHECKPOINT,
            "checkpoint_sha256": checkpoint_sha,
            "best_epoch": int(
                best_epoch
            ),
            "epochs_completed": len(
                history_rows
            ),
            "best_validation_total_objective_during_training": float(
                best_validation_total
            ),
            "frozen_checkpoint_validation_objective": validation_objective,
            "frozen_checkpoint_validation_predictive_metrics": validation_predictive,
            "frozen_checkpoint_validation_structural_metrics_report_only": validation_structural,
            "LOCKED_OOD_target_generated_at_freeze_time": False,
            "LOCKED_OOD_target_opened_at_freeze_time": False,
            "optimizer_updates_after_this_freeze_authorized": False,
            "checkpoint_reselection_after_this_freeze_authorized": False,
            "normalization_refit_after_this_freeze_authorized": False,
            "architecture_or_loss_change_after_this_freeze_authorized": False,
        }

        checkpoint_freeze.write_bytes(
            json_bytes(
                checkpoint_freeze_payload
            )
        )

        checkpoint_frozen = True

        sci_gate(
            "checkpoint_frozen_before_OOD",
            checkpoint_freeze.is_file()
            and sha256_file(
                checkpoint
            )
            == checkpoint_sha,
            checkpoint_sha,
        )

        immutable_publish(
            out,
            {
                "POSTV16_AV3_A5_Training_History.csv":
                    csv_bytes(
                        history_rows
                    ),

                "POSTV16_AV3_A5_Validation_Predictions_Before_OOD.npz":
                    deterministic_npz_bytes(
                        {
                            "sample_indices":
                                val_samples,

                            "Y_true":
                                val_truth,

                            "Y_pred":
                                val_prediction,

                            "time_index":
                                time_index[
                                    val_samples
                                ],

                            "streamline_index":
                                streamline_index[
                                    val_samples
                                ],

                            "target_time_days":
                                target_days[
                                    val_samples
                                ],

                            "checkpoint_sha256":
                                np.asarray(
                                    checkpoint_sha
                                ),
                        }
                    ),
            },
        )

        # ------------------------------------------------------------------------------------------
        # Pre-OOD integrity reconstruction. Still no Y.
        # ------------------------------------------------------------------------------------------
        stage = "pre_OOD_integrity"

        a2_ood = (
            drive
            / A2_REL
            / "POSTV16_AV3_A2_AV3CR0004_Corey_Relperm_Field_and_Streamline_Sampling.npz"
        )

        gate(
            "OOD_A2_authority_present",
            a2_ood.is_file(),
            str(
                a2_ood
            ),
        )

        with np.load(
            a2_ood,
            allow_pickle=False,
        ) as z:

            xyz_ood = np.asarray(
                z[
                    "streamline_xyz_m"
                ],
                dtype=np.float64,
            )

            tof_ood = np.asarray(
                z[
                    "pollock_tof_s"
                ],
                dtype=np.float64,
            )

            phi_grid_ood = np.asarray(
                z[
                    "paired_porosity"
                ],
                dtype=np.float64,
            )

            nw_ood_64 = np.asarray(
                z[
                    "nw_streamline"
                ],
                dtype=np.float64,
            )

            no_ood_64 = np.asarray(
                z[
                    "no_streamline"
                ],
                dtype=np.float64,
            )

            krw_ood_64 = np.asarray(
                z[
                    "krw_max_streamline"
                ],
                dtype=np.float64,
            )

            kro_ood_64 = np.asarray(
                z[
                    "kro_max_streamline"
                ],
                dtype=np.float64,
            )

        r2_module = load_module(
            root
            / R2,
            "av3a5_r2",
        )

        c2_module = load_module(
            root
            / C2,
            "av3a5_c2",
        )

        operator_ood = r2_module.build_operator_geometry(
            xyz_ood,
            tof_ood,
        )

        phi_ood_64, phi_audit = c2_module.trilinear(
            phi_grid_ood,
            xyz_ood,
            DX,
            DY,
            DZ,
            ORIGIN_CENTER_M,
        )

        gate(
            "OOD_phi_sampling_cell_centered",
            phi_audit[
                "finite"
            ]
            and np.array_equal(
                phi_ood_64.astype(
                    np.float32
                ),
                phi_sequence[
                    3
                ],
            ),
            phi_audit,
        )

        gate(
            "OOD_metric_M_native_float64_matches_R2_sidecar",
            np.allclose(
                operator_ood[
                    "metric_M"
                ],
                metric_M_native[
                    3
                ],
                rtol=1.0e-12,
                atol=1.0e-12,
            ),
            float(
                np.max(
                    np.abs(
                        operator_ood[
                            "metric_M"
                        ]
                        - metric_M_native[
                            3
                        ]
                    )
                )
            ),
        )

        gate(
            "OOD_metric_M_face_native_float64_matches_R2_sidecar",
            np.allclose(
                operator_ood[
                    "metric_M_face"
                ],
                metric_M_face_native[
                    3
                ],
                rtol=1.0e-12,
                atol=1.0e-12,
            ),
            float(
                np.max(
                    np.abs(
                        operator_ood[
                            "metric_M_face"
                        ]
                        - metric_M_face_native[
                            3
                        ]
                    )
                )
            ),
        )

        gate(
            "OOD_control_volume_native_float64_matches_R2_sidecar",
            np.allclose(
                operator_ood[
                    "control_volume_dtheta"
                ],
                control_volume_native[
                    3
                ],
                rtol=1.0e-12,
                atol=1.0e-12,
            ),
            float(
                np.max(
                    np.abs(
                        operator_ood[
                            "control_volume_dtheta"
                        ]
                        - control_volume_native[
                            3
                        ]
                    )
                )
            ),
        )

        gate(
            "OOD_dtheta_native_float64_matches_R2_sidecar",
            np.allclose(
                operator_ood[
                    "dtheta_center"
                ],
                dtheta_center_native[
                    3
                ],
                rtol=1.0e-12,
                atol=1.0e-12,
            ),
            float(
                np.max(
                    np.abs(
                        operator_ood[
                            "dtheta_center"
                        ]
                        - dtheta_center_native[
                            3
                        ]
                    )
                )
            ),
        )

        gate(
            "OOD_constitutive_sidecars_match_A2",
            np.array_equal(
                nw_sequence[
                    3
                ],
                nw_ood_64.astype(
                    np.float32
                ),
            )
            and np.array_equal(
                no_sequence[
                    3
                ],
                no_ood_64.astype(
                    np.float32
                ),
            )
            and np.array_equal(
                krw_sequence[
                    3
                ],
                krw_ood_64.astype(
                    np.float32
                ),
            )
            and np.array_equal(
                kro_sequence[
                    3
                ],
                kro_ood_64.astype(
                    np.float32
                ),
            ),
        )

        # ------------------------------------------------------------------------------------------
        # ONE-TOUCH LOCKED OOD OPENING.
        # ------------------------------------------------------------------------------------------
        stage = "OOD_open"

        ood_marker.write_text(
            (
                "POSTV16-AV3-A5 LOCKED OOD OPENED\n"
                f"checkpoint_sha256={checkpoint_sha}\n"
                "training_after_marker=false\n"
                "checkpoint_reselection_after_marker=false\n"
                "normalization_refit_after_marker=false\n"
                "second_OOD_generation_authorized=false\n"
            ),
            encoding="utf-8",
        )

        locked_ood_opened = True

        sci_gate(
            "OOD_open_only_after_checkpoint_freeze",
            checkpoint_frozen
            and ood_marker.is_file(),
        )

        # ------------------------------------------------------------------------------------------
        # Exactly one OOD teacher generation under unchanged R2/A3 physics.
        # ------------------------------------------------------------------------------------------
        stage = "OOD_teacher_generation"

        teacher_start = time.time()

        Y_ood_3d, ood_teacher_diag = r2_module.generate_teacher(
            phi_ood_64,
            operator_ood,
            nw_ood_64,
            no_ood_64,
            krw_ood_64,
            kro_ood_64,
            DAYS,
        )

        locked_ood_teacher_generated = True

        sci_gate(
            "OOD_teacher_hard_numerical_certification",
            r2_module.teacher_diag_pass(
                ood_teacher_diag
            ),
            ood_teacher_diag,
        )

        sci_gate(
            "OOD_Y_shape_exact",
            Y_ood_3d.shape
            == (
                NT,
                NSL,
                NN,
            ),
            Y_ood_3d.shape,
        )

        Y_ood = Y_ood_3d.reshape(
            OOD_PROFILES,
            NN,
        ).astype(
            np.float64
        )

        # ------------------------------------------------------------------------------------------
        # Exactly one OOD evaluation of the frozen checkpoint.
        # ------------------------------------------------------------------------------------------
        stage = "OOD_evaluation"

        P_ood = best_model.predict(
            X_ood,
            batch_size=BATCH,
            verbose=0,
        ).astype(
            np.float64
        )

        locked_ood_evaluated = True

        sci_gate(
            "OOD_predictions_finite",
            np.all(
                np.isfinite(
                    P_ood
                )
            ),
        )

        sci_gate(
            "OOD_predictions_bounded",
            float(
                np.min(
                    P_ood
                )
            )
            >= SWC
            - 1.0e-6
            and float(
                np.max(
                    P_ood
                )
            )
            <= 1.0
            - SOR
            + 1.0e-6,
            [
                float(
                    np.min(
                        P_ood
                    )
                ),
                float(
                    np.max(
                        P_ood
                    )
                ),
            ],
        )

        ood_predictive = predictive_metrics(
            P_ood,
            Y_ood,
        )

        ood_structural = structural_metrics(
            P_ood,
            ti_ood,
            sl_ood,
        )

        ood_a, ood_b = build_pairs(
            ri_ood,
            ti_ood,
            sl_ood,
        )

        sci_gate(
            "OOD_adjacent_pair_count_8624",
            len(
                ood_a
            )
            == OOD_PAIRS,
            len(
                ood_a
            ),
        )

        # OOD physics residual: descriptive only, no selection threshold.
        P_ood_tf = tf.constant(
            P_ood.astype(
                np.float32
            ),
            dtype=tf.float32,
        )

        ood_phys_values = []

        for start in range(
            0,
            len(
                ood_a
            ),
            BATCH,
        ):

            a = ood_a[
                start:start
                + BATCH
            ]

            b = ood_b[
                start:start
                + BATCH
            ]

            slb = sl_ood[
                a
            ].astype(
                np.int32
            )

            side_idx = tf.convert_to_tensor(
                np.stack(
                    [
                        np.full_like(
                            slb,
                            3,
                        ),
                        slb,
                    ],
                    axis=1,
                ),
                dtype=tf.int32,
            )

            M = tf.gather_nd(
                M_tf,
                side_idx,
            )

            Mf = tf.gather_nd(
                Mf_tf,
                side_idx,
            )

            cv = tf.gather_nd(
                cv_tf,
                side_idx,
            )

            dth = tf.gather_nd(
                dtheta_tf,
                side_idx,
            )

            phi = tf.gather_nd(
                phi_tf,
                side_idx,
            )

            nw = tf.gather_nd(
                nw_tf,
                side_idx,
            )

            no = tf.gather_nd(
                no_tf,
                side_idx,
            )

            kw = tf.gather_nd(
                krw_tf,
                side_idx,
            )

            ko = tf.gather_nd(
                kro_tf,
                side_idx,
            )

            lp = physics_loss(
                tf.gather(
                    P_ood_tf,
                    a,
                ),
                tf.gather(
                    P_ood_tf,
                    b,
                ),
                tf.convert_to_tensor(
                    eta_ood[
                        a
                    ],
                    dtype=tf.float32,
                ),
                tf.convert_to_tensor(
                    eta_ood[
                        b
                    ],
                    dtype=tf.float32,
                ),
                M,
                Mf,
                cv,
                dth,
                phi,
                nw,
                no,
                kw,
                ko,
            )

            ood_phys_values.append(
                float(
                    lp.numpy()
                )
            )

        ood_physics_residual_mse = float(
            np.mean(
                ood_phys_values
            )
        )

        by_time_rows = []

        for day in DAYS:

            q = np.isclose(
                days_ood,
                day,
            )

            by_time_rows.append(
                {
                    "target_day": float(
                        day
                    ),
                    **predictive_metrics(
                        P_ood[
                            q
                        ],
                        Y_ood[
                            q
                        ],
                    ),
                }
            )

        generalization = {
            "validation_predictive_metrics": validation_predictive,
            "validation_objective": validation_objective,
            "locked_OOD_predictive_metrics": ood_predictive,
            "OOD_to_validation_RMSE_ratio": (
                ood_predictive[
                    "rmse"
                ]
                / max(
                    validation_predictive[
                        "rmse"
                    ],
                    1.0e-300,
                )
            ),
            "OOD_to_validation_MAE_ratio": (
                ood_predictive[
                    "mae"
                ]
                / max(
                    validation_predictive[
                        "mae"
                    ],
                    1.0e-300,
                )
            ),
            "validation_structural_metrics_report_only": validation_structural,
            "locked_OOD_structural_metrics_report_only": ood_structural,
            "locked_OOD_physics_residual_MSE": ood_physics_residual_mse,
            "locked_OOD_teacher_diagnostics": ood_teacher_diag,
            "locked_OOD_teacher_elapsed_seconds": float(
                time.time()
                - teacher_start
            ),
            "scientific_rule": (
                "Single prospectively locked AV3CR0004 one-touch evaluation. "
                "Metrics are descriptive evidence only. No post-hoc accuracy threshold, "
                "retraining, checkpoint reselection, normalization refit, or retuning is authorized."
            ),
            "arbitrary_generalization_claim_authorized": False,
        }

        # ------------------------------------------------------------------------------------------
        # Freeze final A5 state.
        # ------------------------------------------------------------------------------------------
        stage = "final_freeze"

        for name in [
            "no_post_OOD_training",
            "no_post_OOD_checkpoint_reselection",
            "no_post_OOD_normalization_refit",
            "no_post_OOD_hyperparameter_retuning",
            "no_second_OOD_generation",
            "no_second_OOD_evaluation",
            "no_mapback",
            "no_LP",
            "no_CMG",
        ]:
            gate(
                name,
                True,
            )

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "original_AV3A4_scientific_FAIL_preserved": True,
            "original_AV3A4_fail_SHA256": ORIGINAL_A4_FAIL_SHA256,
            "R2_dataset_authority_used": True,
            "training_protocol_executed_exactly": True,
            "training_realizations": [
                "AV3CR0001",
                "AV3CR0002",
            ],
            "validation_realization": "AV3CR0003",
            "best_validation_checkpoint_frozen_before_OOD": True,
            "checkpoint_sha256": checkpoint_sha,
            "best_epoch": int(
                best_epoch
            ),
            "epochs_completed": len(
                history_rows
            ),
            "best_validation_total_objective": float(
                best_validation_total
            ),
            "locked_OOD_realization": "AV3CR0004",
            "locked_OOD_teacher_generated_once": True,
            "locked_OOD_evaluated_once": True,
            "OOD_accuracy_threshold_gate": False,
            "post_OOD_training": False,
            "post_OOD_checkpoint_reselection": False,
            "post_OOD_normalization_refit": False,
            "post_OOD_hyperparameter_retuning": False,
            "second_OOD_generation_authorized": False,
            "second_OOD_evaluation_authorized": False,
            "arbitrary_generalization_claim_authorized": False,
            "mapback_performed": False,
            "LP_execution_performed": False,
            "CMG_validation_performed": False,
            "AV3_A6_authorized": True,
            "next": {
                "milestone": "POSTV16-AV3-A6",
                "authorized": True,
                "execution": False,
                "name": (
                    "Frozen AV3 Checkpoint Deployment / "
                    "Variable-Porosity Local-Pore-Volume R7D Terminal-Halo Integration"
                ),
                "note": (
                    "A6 design/freeze is authorized after A5 PASS; "
                    "execution must be prospectively frozen before deployment."
                ),
            },
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "checkpoint_sha256": checkpoint_sha,
            "best_epoch": int(
                best_epoch
            ),
            "epochs_completed": len(
                history_rows
            ),
            "best_validation_total_objective": float(
                best_validation_total
            ),
            "validation_metrics": validation_predictive,
            "validation_objective": validation_objective,
            "locked_OOD_teacher_certified": True,
            "locked_OOD_teacher_diagnostics": ood_teacher_diag,
            "locked_OOD_metrics": ood_predictive,
            "locked_OOD_physics_residual_MSE": ood_physics_residual_mse,
            "OOD_to_validation_RMSE_ratio": generalization[
                "OOD_to_validation_RMSE_ratio"
            ],
            "OOD_to_validation_MAE_ratio": generalization[
                "OOD_to_validation_MAE_ratio"
            ],
            "OOD_accuracy_gate_applied": False,
            "training_after_OOD": False,
            "retuning_after_OOD": False,
            "mapback": False,
            "LP": False,
            "CMG_validation": False,
            "AV3_A6_authorized": True,
            "next": decision[
                "next"
            ],
        }

        immutable_publish(
            out,
            {
                "POSTV16_AV3_A5_LockedOOD_Truth_and_Predictions.npz":
                    deterministic_npz_bytes(
                        {
                            "Y_true":
                                Y_ood,

                            "Y_pred":
                                P_ood,

                            "target_time_days":
                                days_ood,

                            "time_index":
                                ti_ood,

                            "streamline_index":
                                sl_ood,

                            "realization_index":
                                ri_ood,

                            "checkpoint_sha256":
                                np.asarray(
                                    checkpoint_sha
                                ),
                        }
                    ),

                "POSTV16_AV3_A5_LockedOOD_Predictive_Metrics_By_Time.csv":
                    csv_bytes(
                        by_time_rows
                    ),

                "POSTV16_AV3_A5_LockedOOD_Generalization_Evidence.json":
                    json_bytes(
                        generalization
                    ),

                "POSTV16_AV3_A5_Decision_Contract.json":
                    json_bytes(
                        decision
                    ),

                "PAD_Stream_POSTV16_AV3_A5_Summary.json":
                    json_bytes(
                        summary
                    ),

                "POSTV16_AV3_A5_Final_Gate_Matrix.csv":
                    csv_bytes(
                        [
                            {
                                "gate": key,
                                **value,
                            }
                            for key, value in gates.items()
                        ]
                    ),
            },
        )

        manifest_rows = []

        for q in sorted(
            out.iterdir()
        ):

            if (
                q.is_file()
                and q.name
                != "POSTV16_AV3_A5_Artifact_Manifest.csv"
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
                "POSTV16_AV3_A5_Artifact_Manifest.csv":
                    csv_bytes(
                        manifest_rows
                    )
            },
        )

        print()
        print("=" * 210)
        print("POSTV16-AV3-A5: FULL TRAINING / CHECKPOINT / ONE-TOUCH LOCKED-OOD PASS")
        print("=" * 210)
        print("Original AV3-A4 scientific FAIL              : PRESERVED")
        print("R2 dataset / physics authority                : USED")
        print("Model                                         : 201 x 13 -> 2xLSTM64 -> TD Dense")
        print("Trainable parameters                          :", MODEL_PARAMETERS)
        print("Objective                                     : L_data + 0.01 L_phys")
        print("Best epoch                                    :", best_epoch)
        print("Epochs completed                              :", len(history_rows))
        print("Best validation total objective               :", best_validation_total)
        print("Checkpoint SHA256                             :", checkpoint_sha)
        print("Checkpoint frozen before OOD                  : True")
        print("Validation RMSE / MAE                         :", validation_predictive["rmse"], "/", validation_predictive["mae"])
        print("Locked OOD teacher generated                  : ONCE")
        print("Locked OOD evaluation                         : ONCE")
        print("Locked OOD RMSE / MAE                         :", ood_predictive["rmse"], "/", ood_predictive["mae"])
        print("OOD / validation RMSE ratio                   :", generalization["OOD_to_validation_RMSE_ratio"])
        print("OOD / validation MAE ratio                    :", generalization["OOD_to_validation_MAE_ratio"])
        print("Locked OOD physics residual MSE               :", ood_physics_residual_mse)
        print("OOD accuracy threshold gate                   : False")
        print("Post-OOD training / reselection / refit       : False / False / False")
        print("Second OOD generation / evaluation            : NOT AUTHORIZED")
        print("Mapback / LP / CMG                            : False / False / Deferred")
        print("POSTV16-AV3-A6 design/freeze                  : AUTHORIZED")
        print("A6 execution                                  : NOT YET AUTHORIZED")
        print("=" * 210)

        return 0

    except ScientificFail as exc:

        fail_dir.mkdir(
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
            "training_started": training_started,
            "checkpoint_frozen": checkpoint_frozen,
            "locked_OOD_opened": locked_ood_opened,
            "locked_OOD_teacher_generated": locked_ood_teacher_generated,
            "locked_OOD_evaluated": locked_ood_evaluated,
            "retraining_authorized": False,
            "checkpoint_reselection_authorized": False,
            "normalization_refit_authorized": False,
            "second_OOD_generation_authorized": False,
            "second_OOD_evaluation_authorized": False,
            "AV3_A6_authorized": False,
        }

        p = (
            fail_dir
            / "POSTV16_AV3_A5_Scientific_Fail_Report.json"
        )

        if not p.exists():
            p.write_bytes(
                json_bytes(
                    report
                )
            )

        print()
        print("=" * 210)
        print("POSTV16-AV3-A5: SCIENTIFIC FAIL")
        print("=" * 210)
        print("Failed stage              :", stage)
        print("Failed gate               :", exc.gate)
        print("Checkpoint frozen         :", checkpoint_frozen)
        print("Locked OOD opened         :", locked_ood_opened)
        print("OOD teacher generated     :", locked_ood_teacher_generated)
        print("OOD evaluated             :", locked_ood_evaluated)
        print("Retraining authorized     : False")
        print("Second OOD authorized     : False")
        print("POSTV16-AV3-A6            : NOT AUTHORIZED")
        print("=" * 210)

        return 3

    except Exception as exc:

        block_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(
                exc
            ),
            "gates": gates,
            "training_started": training_started,
            "checkpoint_frozen": checkpoint_frozen,
            "locked_OOD_opened": locked_ood_opened,
            "locked_OOD_teacher_generated": locked_ood_teacher_generated,
            "locked_OOD_evaluated": locked_ood_evaluated,
            "retraining_authorized": False,
            "checkpoint_reselection_authorized": False,
            "normalization_refit_authorized": False,
            "second_OOD_generation_authorized": False,
            "second_OOD_evaluation_authorized": False,
            "AV3_A6_authorized": False,
        }

        p = (
            block_dir
            / "POSTV16_AV3_A5_Blocked_Report.json"
        )

        if not p.exists():
            p.write_bytes(
                json_bytes(
                    report
                )
            )

        print()
        print("=" * 210)
        print("POSTV16-AV3-A5: TECHNICAL BLOCK")
        print("=" * 210)
        print("Failed stage              :", stage)
        print("Exception                 :", repr(exc))
        print("Checkpoint frozen         :", checkpoint_frozen)
        print("Locked OOD opened         :", locked_ood_opened)
        print("OOD teacher generated     :", locked_ood_teacher_generated)
        print("OOD evaluated             :", locked_ood_evaluated)
        print("Retraining authorized     : False")
        print("Second OOD authorized     : False")
        print("POSTV16-AV3-A6            : NOT AUTHORIZED")
        print("=" * 210)

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
