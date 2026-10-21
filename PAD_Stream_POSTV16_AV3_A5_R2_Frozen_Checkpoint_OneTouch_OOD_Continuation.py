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


MILESTONE = "POSTV16-AV3-A5-R2"

STATUS_PASS = (
    "AV3A5R2_FROZEN_EPOCH92_CHECKPOINT_PRE_OOD_INTEGRITY_CORRECTED_"
    "LOCKED_OOD_TEACHER_GENERATED_ONCE_EVALUATED_ONCE_PASS"
)

STATUS_FAIL = (
    "AV3A5R2_ONE_TOUCH_OOD_CONTINUATION_SCIENTIFIC_FAIL_"
    "NO_RETRAINING_RESELECTION_REFIT_RETUNING_OR_SECOND_OOD_AUTHORIZED"
)

STATUS_BLOCKED = "AV3A5R2_ONE_TOUCH_OOD_CONTINUATION_TECHNICAL_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

PARENT_R1_COMMIT = "a30d437ce7fff8f3403271de9eaad74d35da4ac2"

# --------------------------------------------------------------------------------------------------
# Exact source lineage.
# --------------------------------------------------------------------------------------------------

R1 = "PAD_Stream_POSTV16_AV3_A5_R1_PreOOD_Technical_Block_Closure.py"
R1_BLOB = "1710ddffc2cb74ce171010ea55011b6c31ccad83"

A5 = "PAD_Stream_POSTV16_AV3_A5_PIRNN_Training_Checkpoint_and_OneTouch_OOD.py"
A5_BLOB = "ab1b7fbfc2330c995762ada0379e424cc09599f0"

R2 = (
    "PAD_Stream_POSTV16_AV3_A4_R2_"
    "Corrected_Certification_Teacher_Dataset_and_LockedOOD_Predictor.py"
)
R2_BLOB = "289901331e835afb44ff2f665fe9a6bbea2eac19"

A2 = (
    "PAD_Stream_POSTV16_AV3_A2_"
    "Corey_Relperm_Field_Realization_Certification_and_Streamline_Sampling.py"
)
A2_BLOB = "e7d4f1b1e69ea3e756c4f41d7edb57e2ffd87d7b"

C2 = "PAD_Stream_V16C2_Multi_Coordinate_Streamline_Transport_Database_Assembly.py"
C2_BLOB = "21ff44de456102772c99f7ddc80898c9139a76db"

SOURCE_BLOBS = {
    R1: R1_BLOB,
    A5: A5_BLOB,
    R2: R2_BLOB,
    A2: A2_BLOB,
    C2: C2_BLOB,
}

# --------------------------------------------------------------------------------------------------
# Frozen Drive authorities.
# --------------------------------------------------------------------------------------------------

BASE = (
    Path("post_v16")
    / RID
    / "POSTV16_AV3_Corey_Relperm_Heterogeneity"
)

R1_REL = BASE / "POSTV16_AV3_A5_R1_PreOOD_Technical_Block_Closure"
R1_SUMMARY = "PAD_Stream_POSTV16_AV3_A5_R1_Summary.json"
R1_DECISION = "POSTV16_AV3_A5_R1_Decision_Contract.json"
R1_CONTINUATION = "POSTV16_AV3_A5_R1_R2_Continuation_Contract.json"
R1_MANIFEST = "POSTV16_AV3_A5_R1_Artifact_Manifest.csv"

R1_STATUS = (
    "AV3A5R1_IMMUTABLE_A5_TECHNICAL_BLOCK_PRESERVED_"
    "PRE_OOD_TRILINEAR_AUDIT_SCHEMA_ROOT_CAUSE_CLOSED_"
    "FROZEN_CHECKPOINT_CONTINUATION_AUTHORITY_FROZEN"
)

A5_OUT_REL = (
    BASE
    / "POSTV16_AV3_A5_PIRNN_Training_Checkpoint_and_OneTouch_OOD"
)

A5_BLOCK_REL = BASE / "POSTV16_AV3_A5_BLOCKED"
A5_BLOCK_NAME = "POSTV16_AV3_A5_Blocked_Report.json"

CHECKPOINT = "POSTV16_AV3_A5_Best_Validation_Model.keras"
FREEZE = "POSTV16_AV3_A5_Best_Validation_Checkpoint_Freeze.json"
HISTORY = "POSTV16_AV3_A5_Training_History.csv"
VAL_PRED = "POSTV16_AV3_A5_Validation_Predictions_Before_OOD.npz"
ORIGINAL_A5_OOD_MARKER = "POSTV16_AV3_A5_LOCKED_OOD_OPENED.marker"

EXPECTED_CHECKPOINT_SHA = (
    "17b188494e0452570d43e868c20c4c814e6a1f0b493329d0e40849c4c5ec6d4e"
)
EXPECTED_BEST_EPOCH = 92
EXPECTED_EPOCHS = 122
EXPECTED_BEST_VAL = 0.002138707781058555

R2_REL = (
    BASE
    / "POSTV16_AV3_A4_R2_Corrected_Teacher_Dataset_and_LockedOOD_Predictor"
)
R2_OOD = "POSTV16_AV3_A4_R2_LockedOOD_13Channel_Predictor_Only_Dataset.npz"
R2_SIDECAR = "POSTV16_AV3_A4_R2_Spatial_Relperm_Physics_Sidecar.npz"
R2_MANIFEST = "POSTV16_AV3_A4_R2_Artifact_Manifest.csv"

A2_REL = (
    BASE
    / "POSTV16_AV3_A2_Corey_Relperm_Field_Realization_Certification_and_Streamline_Sampling"
)

OUT_REL = (
    BASE
    / "POSTV16_AV3_A5_R2_Frozen_Checkpoint_OneTouch_OOD_Continuation"
)

FAIL_REL = BASE / "POSTV16_AV3_A5_R2_SCIENTIFIC_FAIL"
BLOCK_REL = BASE / "POSTV16_AV3_A5_R2_BLOCKED"

OOD_MARKER = "POSTV16_AV3_A5_R2_LOCKED_OOD_OPENED.marker"

# --------------------------------------------------------------------------------------------------
# Frozen dimensions / physics.
# --------------------------------------------------------------------------------------------------

NN = 201
NSL = 1078
NT = 9
CH = 13
OOD_PROFILES = 9702
OOD_PAIRS = 8624
BATCH = 64

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

    for stream in np.unique(sl):

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

    # The exact technical defect being closed.
    audit = {
        "x_clip_count": 0,
        "y_clip_count": 0,
        "z_clip_count": 0,
        "total_points": 1,
    }

    assert "finite" not in audit
    assert np.isfinite(
        np.asarray(
            [1.0],
            dtype=np.float64,
        )
    ).all()

    # OOD pair count.
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

    assert EXPECTED_BEST_EPOCH == 92
    assert EXPECTED_EPOCHS == 122

    print(
        "POSTV16-AV3-A5-R2 frozen-checkpoint one-touch-OOD continuation self-test: PASS"
    )


def main(
    root: Path,
    drive: Path,
) -> int:

    import tensorflow as tf

    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"

    ood_opened = False
    ood_teacher_generated = False
    ood_evaluated = False

    out = drive / OUT_REL
    fail_dir = drive / FAIL_REL
    block_dir = drive / BLOCK_REL

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

    print("=" * 212)
    print(
        "POSTV16-AV3-A5-R2 — FROZEN CHECKPOINT / CORRECTED PRE-OOD INTEGRITY / "
        "ONE-TOUCH LOCKED-OOD CONTINUATION"
    )
    print("=" * 212)
    print("NO TRAINING. NO CHECKPOINT RESELECTION. NO NORMALIZATION REFIT. NO RETUNING.")
    print("REUSE EXACT FROZEN EPOCH-92 CHECKPOINT.")
    print("CORRECTED PRE-OOD INTEGRITY MUST PASS BEFORE OOD MARKER.")
    print("THEN ONE AV3CR0004 TEACHER GENERATION + ONE EVALUATION ONLY.")
    print("NO SECOND OOD. NO MAPBACK. NO LP. NO CMG.")
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
            "repository_parent_is_A5R1_commit",
            parent == PARENT_R1_COMMIT,
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
        # Bind R1 formal PASS and continuation contract.
        # ------------------------------------------------------------------------------------------
        stage = "R1_binding"

        r1 = drive / R1_REL

        gate(
            "R1_output_present",
            r1.is_dir(),
            str(
                r1
            ),
        )

        m1 = verify_manifest(
            r1,
            R1_MANIFEST,
        )

        gate(
            "R1_manifest_SHA_closure",
            len(
                m1
            )
            == 6,
            len(
                m1
            ),
        )

        r1_summary = load_json(
            r1
            / R1_SUMMARY
        )

        r1_decision = load_json(
            r1
            / R1_DECISION
        )

        continuation = load_json(
            r1
            / R1_CONTINUATION
        )

        gate(
            "R1_status_exact",
            r1_summary[
                "status"
            ]
            == R1_STATUS,
            r1_summary[
                "status"
            ],
        )

        gate(
            "R1_original_A5_BLOCK_preserved",
            r1_summary[
                "original_AV3A5_technical_BLOCK_preserved"
            ]
            is True,
        )

        gate(
            "R1_no_OOD_access",
            r1_summary[
                "OOD_access_in_R1"
            ]
            is False,
        )

        gate(
            "R1_A5R2_authorized",
            r1_decision[
                "AV3_A5_R2_authorized"
            ]
            is True
            and continuation[
                "authorized"
            ]
            is True
            and continuation[
                "execution"
            ]
            is True
            and continuation[
                "milestone"
            ]
            == MILESTONE,
        )

        gate(
            "R1_A6_still_unauthorized",
            r1_decision[
                "AV3_A6_authorized"
            ]
            is False,
        )

        gate(
            "R1_frozen_checkpoint_authority_exact",
            continuation[
                "frozen_checkpoint_sha256"
            ]
            == EXPECTED_CHECKPOINT_SHA
            and int(
                continuation[
                    "best_epoch"
                ]
            )
            == EXPECTED_BEST_EPOCH
            and int(
                continuation[
                    "epochs_completed"
                ]
            )
            == EXPECTED_EPOCHS
            and abs(
                float(
                    continuation[
                        "best_validation_total_objective"
                    ]
                )
                - EXPECTED_BEST_VAL
            )
            <= 1.0e-15,
        )

        gate(
            "R1_continuation_no_training_reselection_refit_retune",
            continuation[
                "training_in_R2"
            ]
            is False
            and continuation[
                "checkpoint_reselection_in_R2"
            ]
            is False
            and continuation[
                "normalization_refit_in_R2"
            ]
            is False
            and continuation[
                "hyperparameter_retuning_in_R2"
            ]
            is False,
        )

        gate(
            "R1_corrected_finiteness_test_exact",
            continuation[
                "corrected_pre_OOD_finiteness_test"
            ]
            == "np.isfinite(phi_ood_64).all()",
        )

        # ------------------------------------------------------------------------------------------
        # Bind original blocked A5 + frozen checkpoint. No retraining.
        # ------------------------------------------------------------------------------------------
        stage = "A5_frozen_checkpoint_binding"

        a5_out = drive / A5_OUT_REL

        a5_block = (
            drive
            / A5_BLOCK_REL
            / A5_BLOCK_NAME
        )

        checkpoint = (
            a5_out
            / CHECKPOINT
        )

        freeze_path = (
            a5_out
            / FREEZE
        )

        history_path = (
            a5_out
            / HISTORY
        )

        val_pred_path = (
            a5_out
            / VAL_PRED
        )

        original_a5_marker = (
            a5_out
            / ORIGINAL_A5_OOD_MARKER
        )

        gate(
            "original_A5_BLOCK_present",
            a5_block.is_file(),
            str(
                a5_block
            ),
        )

        block = load_json(
            a5_block
        )

        gate(
            "original_A5_BLOCK_identity_exact",
            block[
                "status"
            ]
            == "AV3A5_TECHNICAL_EXECUTION_BLOCKED"
            and block[
                "failed_stage"
            ]
            == "pre_OOD_integrity"
            and block[
                "exception"
            ]
            == "KeyError('finite')",
        )

        gate(
            "original_A5_OOD_never_opened",
            block[
                "locked_OOD_opened"
            ]
            is False
            and block[
                "locked_OOD_teacher_generated"
            ]
            is False
            and block[
                "locked_OOD_evaluated"
            ]
            is False
            and not original_a5_marker.exists(),
        )

        gate(
            "frozen_checkpoint_present",
            checkpoint.is_file(),
            str(
                checkpoint
            ),
        )

        checkpoint_sha = sha256_file(
            checkpoint
        )

        gate(
            "frozen_checkpoint_SHA_exact",
            checkpoint_sha
            == EXPECTED_CHECKPOINT_SHA,
            checkpoint_sha,
        )

        freeze = load_json(
            freeze_path
        )

        gate(
            "checkpoint_freeze_identity_exact",
            freeze[
                "checkpoint_sha256"
            ]
            == EXPECTED_CHECKPOINT_SHA
            and int(
                freeze[
                    "best_epoch"
                ]
            )
            == EXPECTED_BEST_EPOCH
            and int(
                freeze[
                    "epochs_completed"
                ]
            )
            == EXPECTED_EPOCHS
            and abs(
                float(
                    freeze[
                        "best_validation_total_objective_during_training"
                    ]
                )
                - EXPECTED_BEST_VAL
            )
            <= 1.0e-15,
        )

        gate(
            "checkpoint_was_frozen_before_OOD",
            freeze[
                "LOCKED_OOD_target_generated_at_freeze_time"
            ]
            is False
            and freeze[
                "LOCKED_OOD_target_opened_at_freeze_time"
            ]
            is False,
        )

        gate(
            "no_post_freeze_training_reselection_refit",
            freeze[
                "optimizer_updates_after_this_freeze_authorized"
            ]
            is False
            and freeze[
                "checkpoint_reselection_after_this_freeze_authorized"
            ]
            is False
            and freeze[
                "normalization_refit_after_this_freeze_authorized"
            ]
            is False,
        )

        history = read_csv(
            history_path
        )

        gate(
            "training_history_still_122_epochs",
            len(
                history
            )
            == EXPECTED_EPOCHS,
            len(
                history
            ),
        )

        val_total = np.asarray(
            [
                float(
                    row[
                        "validation_total"
                    ]
                )
                for row in history
            ],
            dtype=np.float64,
        )

        gate(
            "history_best_epoch_92_still_exact",
            int(
                np.argmin(
                    val_total
                )
                + 1
            )
            == EXPECTED_BEST_EPOCH,
            int(
                np.argmin(
                    val_total
                )
                + 1
            ),
        )

        gate(
            "history_best_validation_total_still_exact",
            abs(
                float(
                    np.min(
                        val_total
                    )
                )
                - EXPECTED_BEST_VAL
            )
            <= 1.0e-15,
            float(
                np.min(
                    val_total
                )
            ),
        )

        with np.load(
            val_pred_path,
            allow_pickle=False,
        ) as z:

            validation_truth = np.asarray(
                z[
                    "Y_true"
                ],
                dtype=np.float64,
            )

            validation_prediction = np.asarray(
                z[
                    "Y_pred"
                ],
                dtype=np.float64,
            )

            validation_checkpoint_sha = str(
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
            "validation_artifact_bound_to_frozen_checkpoint",
            validation_checkpoint_sha
            == EXPECTED_CHECKPOINT_SHA,
            validation_checkpoint_sha,
        )

        gate(
            "validation_artifact_shapes_exact",
            validation_truth.shape
            == (
                9702,
                NN,
            )
            and validation_prediction.shape
            == (
                9702,
                NN,
            ),
        )

        validation_metrics = predictive_metrics(
            validation_prediction,
            validation_truth,
        )

        # ------------------------------------------------------------------------------------------
        # One-touch pre-run firewall.
        # ------------------------------------------------------------------------------------------
        stage = "one_touch_pre_run_firewall"

        gate(
            "A5R2_marker_absent_before_integrity",
            not ood_marker.exists(),
            str(
                ood_marker
            ),
        )

        # ------------------------------------------------------------------------------------------
        # Bind R2 OOD predictor-only authority.
        # ------------------------------------------------------------------------------------------
        stage = "R2_OOD_binding"

        r2 = drive / R2_REL

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

        with np.load(
            r2
            / R2_OOD,
            allow_pickle=False,
        ) as z:

            files = set(
                z.files
            )

            gate(
                "R2_OOD_predictor_still_contains_no_Y",
                "Y_transport"
                not in files
                and "Y"
                not in files
                and "teacher_Y"
                not in files
                and bool(
                    np.asarray(
                        z[
                            "contains_Y_transport"
                        ]
                    ).reshape(
                        -1
                    )[
                        0
                    ]
                )
                is False,
                sorted(
                    files
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

        gate(
            "OOD_realization_index_exact",
            set(
                np.unique(
                    ri_ood
                ).tolist()
            )
            == {
                3
            },
        )

        gate(
            "OOD_time_streamline_registry_exact",
            set(
                np.unique(
                    ti_ood
                ).tolist()
            )
            == set(
                range(
                    NT
                )
            )
            and set(
                np.unique(
                    sl_ood
                ).tolist()
            )
            == set(
                range(
                    NSL
                )
            ),
        )

        with np.load(
            r2
            / R2_SIDECAR,
            allow_pickle=False,
        ) as z:

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

            dtheta_native = np.asarray(
                z[
                    "dtheta_center"
                ],
                dtype=np.float64,
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

        # ------------------------------------------------------------------------------------------
        # Corrected pre-OOD integrity closure.
        # NO marker before every gate below passes.
        # ------------------------------------------------------------------------------------------
        stage = "corrected_pre_OOD_integrity"

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
            "av3a5r2_teacher",
        )

        c2_module = load_module(
            root
            / C2,
            "av3a5r2_c2",
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

        # Exact correction frozen by R1: direct array finiteness, not phi_audit["finite"].
        gate(
            "corrected_phi_sample_finite_direct_array_test",
            np.isfinite(
                phi_ood_64
            ).all(),
        )

        gate(
            "V16C2_audit_schema_exact_no_finite_key",
            set(
                phi_audit
            )
            == {
                "x_clip_count",
                "y_clip_count",
                "z_clip_count",
                "total_points",
            }
            and "finite"
            not in phi_audit,
            sorted(
                phi_audit
            ),
        )

        gate(
            "phi_sampling_total_points_exact",
            int(
                phi_audit[
                    "total_points"
                ]
            )
            == NSL
            * NN,
            phi_audit,
        )

        gate(
            "phi_sample_matches_frozen_R2_sidecar",
            np.array_equal(
                phi_ood_64.astype(
                    np.float32
                ),
                phi_sequence[
                    3
                ],
            ),
        )

        for key, native in [
            (
                "metric_M",
                metric_M_native[
                    3
                ],
            ),
            (
                "metric_M_face",
                metric_M_face_native[
                    3
                ],
            ),
            (
                "control_volume_dtheta",
                control_volume_native[
                    3
                ],
            ),
            (
                "dtheta_center",
                dtheta_native[
                    3
                ],
            ),
        ]:

            gate(
                f"OOD_{key}_native_float64_matches_R2_sidecar",
                np.allclose(
                    operator_ood[
                        key
                    ],
                    native,
                    rtol=1.0e-12,
                    atol=1.0e-12,
                ),
                float(
                    np.max(
                        np.abs(
                            operator_ood[
                                key
                            ]
                            - native
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

        expected_p4 = np.stack(
            [
                nw_ood_64
                - 3.0,
                no_ood_64
                - 3.0,
                (
                    krw_ood_64
                    - 0.80
                )
                / 0.20,
                (
                    kro_ood_64
                    - 0.80
                )
                / 0.20,
            ],
            axis=-1,
        ).astype(
            np.float32
        )

        gate(
            "OOD_X13_constitutive_channels_exact_A2_authority",
            np.array_equal(
                X_ood[
                    :NSL,
                    :,
                    9:13,
                ],
                expected_p4,
            ),
        )

        # ------------------------------------------------------------------------------------------
        # Load exact frozen checkpoint only after integrity gates pass.
        # ------------------------------------------------------------------------------------------
        stage = "frozen_checkpoint_load"

        best_model = tf.keras.models.load_model(
            checkpoint
        )

        gate(
            "loaded_checkpoint_parameter_count_53057",
            best_model.count_params()
            == 53057,
            best_model.count_params(),
        )

        # ------------------------------------------------------------------------------------------
        # ONE-TOUCH OOD OPENING.
        # ------------------------------------------------------------------------------------------
        stage = "OOD_open"

        out.mkdir(
            parents=True,
            exist_ok=True,
        )

        gate(
            "both_A5_and_A5R2_markers_absent_immediately_before_open",
            not original_a5_marker.exists()
            and not ood_marker.exists(),
        )

        ood_marker.write_text(
            (
                "POSTV16-AV3-A5-R2 LOCKED OOD OPENED\n"
                f"checkpoint_sha256={EXPECTED_CHECKPOINT_SHA}\n"
                "training_in_A5R2=false\n"
                "checkpoint_reselection_in_A5R2=false\n"
                "normalization_refit_in_A5R2=false\n"
                "hyperparameter_retuning_in_A5R2=false\n"
                "second_OOD_generation_authorized=false\n"
                "second_OOD_evaluation_authorized=false\n"
            ),
            encoding="utf-8",
        )

        ood_opened = True

        sci_gate(
            "OOD_marker_written_only_after_corrected_integrity",
            ood_marker.is_file()
            and checkpoint_sha
            == EXPECTED_CHECKPOINT_SHA,
        )

        # ------------------------------------------------------------------------------------------
        # Exactly one CR0004 teacher generation under unchanged R2/A3 physics.
        # ------------------------------------------------------------------------------------------
        stage = "OOD_teacher_generation"

        teacher_start = time.time()

        Y_ood_3d, teacher_diag = r2_module.generate_teacher(
            phi_ood_64,
            operator_ood,
            nw_ood_64,
            no_ood_64,
            krw_ood_64,
            kro_ood_64,
            DAYS,
        )

        ood_teacher_generated = True

        sci_gate(
            "OOD_teacher_hard_numerical_certification",
            r2_module.teacher_diag_pass(
                teacher_diag
            ),
            teacher_diag,
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
        # Exactly one frozen-checkpoint OOD evaluation.
        # ------------------------------------------------------------------------------------------
        stage = "OOD_evaluation"

        P_ood = best_model.predict(
            X_ood,
            batch_size=BATCH,
            verbose=0,
        ).astype(
            np.float64
        )

        ood_evaluated = True

        sci_gate(
            "OOD_predictions_finite",
            np.isfinite(
                P_ood
            ).all(),
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

        ood_metrics = predictive_metrics(
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

        # ------------------------------------------------------------------------------------------
        # Descriptive A3 physics residual on frozen OOD predictions.
        # ------------------------------------------------------------------------------------------
        stage = "OOD_physics_residual"

        M_tf = tf.constant(
            metric_M_native.astype(
                np.float32
            ),
            dtype=tf.float32,
        )

        Mf_tf = tf.constant(
            metric_M_face_native.astype(
                np.float32
            ),
            dtype=tf.float32,
        )

        cv_tf = tf.constant(
            control_volume_native.astype(
                np.float32
            ),
            dtype=tf.float32,
        )

        dtheta_tf = tf.constant(
            dtheta_native.astype(
                np.float32
            ),
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

            return tf.reduce_mean(
                tf.square(
                    R
                )
            )

        P_tf = tf.constant(
            P_ood.astype(
                np.float32
            ),
            dtype=tf.float32,
        )

        phys_values = []

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

            lp = physics_loss(
                tf.gather(
                    P_tf,
                    a,
                ),
                tf.gather(
                    P_tf,
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
                tf.gather_nd(
                    M_tf,
                    side_idx,
                ),
                tf.gather_nd(
                    Mf_tf,
                    side_idx,
                ),
                tf.gather_nd(
                    cv_tf,
                    side_idx,
                ),
                tf.gather_nd(
                    dtheta_tf,
                    side_idx,
                ),
                tf.gather_nd(
                    phi_tf,
                    side_idx,
                ),
                tf.gather_nd(
                    nw_tf,
                    side_idx,
                ),
                tf.gather_nd(
                    no_tf,
                    side_idx,
                ),
                tf.gather_nd(
                    krw_tf,
                    side_idx,
                ),
                tf.gather_nd(
                    kro_tf,
                    side_idx,
                ),
            )

            phys_values.append(
                float(
                    lp.numpy()
                )
            )

        ood_physics_residual_mse = float(
            np.mean(
                phys_values
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

        teacher_elapsed = float(
            time.time()
            - teacher_start
        )

        # ------------------------------------------------------------------------------------------
        # Final one-touch freeze.
        # ------------------------------------------------------------------------------------------
        stage = "final_freeze"

        generalization = {
            "milestone": MILESTONE,
            "checkpoint_sha256": EXPECTED_CHECKPOINT_SHA,
            "validation_metrics_from_frozen_pre_OOD_A5_artifact":
                validation_metrics,
            "locked_OOD_metrics":
                ood_metrics,
            "OOD_to_validation_RMSE_ratio":
                ood_metrics[
                    "rmse"
                ]
                / max(
                    validation_metrics[
                        "rmse"
                    ],
                    1.0e-300,
                ),
            "OOD_to_validation_MAE_ratio":
                ood_metrics[
                    "mae"
                ]
                / max(
                    validation_metrics[
                        "mae"
                    ],
                    1.0e-300,
                ),
            "locked_OOD_structural_metrics_report_only":
                ood_structural,
            "locked_OOD_physics_residual_MSE":
                ood_physics_residual_mse,
            "locked_OOD_teacher_diagnostics":
                teacher_diag,
            "locked_OOD_teacher_elapsed_seconds":
                teacher_elapsed,
            "OOD_accuracy_threshold_gate":
                False,
            "arbitrary_generalization_claim_authorized":
                False,
            "post_OOD_training":
                False,
            "post_OOD_checkpoint_reselection":
                False,
            "post_OOD_normalization_refit":
                False,
            "post_OOD_hyperparameter_retuning":
                False,
            "second_OOD_generation_authorized":
                False,
            "second_OOD_evaluation_authorized":
                False,
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "original_AV3A5_technical_BLOCK_preserved":
                True,
            "AV3A5R1_closure_authority_used":
                True,
            "frozen_A5_checkpoint_reused_exactly":
                True,
            "checkpoint_sha256":
                EXPECTED_CHECKPOINT_SHA,
            "best_epoch":
                EXPECTED_BEST_EPOCH,
            "epochs_completed":
                EXPECTED_EPOCHS,
            "best_validation_total_objective":
                EXPECTED_BEST_VAL,
            "training_in_A5R2":
                False,
            "checkpoint_reselection_in_A5R2":
                False,
            "normalization_refit_in_A5R2":
                False,
            "hyperparameter_retuning_in_A5R2":
                False,
            "corrected_pre_OOD_integrity_passed":
                True,
            "locked_OOD_realization":
                "AV3CR0004",
            "locked_OOD_teacher_generated_once":
                True,
            "locked_OOD_evaluated_once":
                True,
            "OOD_accuracy_threshold_gate":
                False,
            "post_OOD_training":
                False,
            "post_OOD_checkpoint_reselection":
                False,
            "post_OOD_normalization_refit":
                False,
            "post_OOD_hyperparameter_retuning":
                False,
            "second_OOD_generation_authorized":
                False,
            "second_OOD_evaluation_authorized":
                False,
            "arbitrary_generalization_claim_authorized":
                False,
            "mapback_performed":
                False,
            "LP_execution_performed":
                False,
            "CMG_validation_performed":
                False,
            "AV3_A6_authorized":
                True,
            "next": {
                "milestone":
                    "POSTV16-AV3-A6",
                "authorized":
                    True,
                "execution":
                    False,
                "name": (
                    "Frozen AV3 Checkpoint Deployment / "
                    "Variable-Porosity Local-Pore-Volume R7D Terminal-Halo Integration"
                ),
                "note": (
                    "A6 design/freeze is authorized after A5-R2 PASS. "
                    "A6 execution must be prospectively frozen before deployment."
                ),
            },
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "original_AV3A5_technical_BLOCK_preserved":
                True,
            "frozen_checkpoint_sha256":
                EXPECTED_CHECKPOINT_SHA,
            "best_epoch":
                EXPECTED_BEST_EPOCH,
            "epochs_completed":
                EXPECTED_EPOCHS,
            "best_validation_total_objective":
                EXPECTED_BEST_VAL,
            "training_repeated":
                False,
            "checkpoint_reselected":
                False,
            "normalization_refit":
                False,
            "corrected_pre_OOD_integrity_passed":
                True,
            "locked_OOD_teacher_certified":
                True,
            "locked_OOD_teacher_diagnostics":
                teacher_diag,
            "validation_metrics":
                validation_metrics,
            "locked_OOD_metrics":
                ood_metrics,
            "locked_OOD_physics_residual_MSE":
                ood_physics_residual_mse,
            "OOD_to_validation_RMSE_ratio":
                generalization[
                    "OOD_to_validation_RMSE_ratio"
                ],
            "OOD_to_validation_MAE_ratio":
                generalization[
                    "OOD_to_validation_MAE_ratio"
                ],
            "OOD_accuracy_gate_applied":
                False,
            "post_OOD_training":
                False,
            "retuning_after_OOD":
                False,
            "second_OOD_authorized":
                False,
            "mapback":
                False,
            "LP":
                False,
            "CMG_validation":
                False,
            "AV3_A6_authorized":
                True,
            "next":
                decision[
                    "next"
                ],
        }

        authority = {
            "milestone": MILESTONE,
            "R1_status": R1_STATUS,
            "original_A5_BLOCK_preserved": True,
            "checkpoint_sha256": EXPECTED_CHECKPOINT_SHA,
            "best_epoch": EXPECTED_BEST_EPOCH,
            "epochs_completed": EXPECTED_EPOCHS,
            "best_validation_total_objective": EXPECTED_BEST_VAL,
            "training_repeated": False,
            "checkpoint_reselected": False,
            "normalization_refit": False,
            "pre_OOD_integrity_fix":
                "np.isfinite(phi_ood_64).all()",
            "OOD_marker_file":
                OOD_MARKER,
            "OOD_teacher_generation_count":
                1,
            "OOD_evaluation_count":
                1,
        }

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

        immutable_publish(
            out,
            {
                "POSTV16_AV3_A5_R2_Frozen_Checkpoint_Continuation_Authority.json":
                    json_bytes(
                        authority
                    ),

                "POSTV16_AV3_A5_R2_LockedOOD_Truth_and_Predictions.npz":
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
                                    EXPECTED_CHECKPOINT_SHA
                                ),
                        }
                    ),

                "POSTV16_AV3_A5_R2_LockedOOD_Predictive_Metrics_By_Time.csv":
                    csv_bytes(
                        by_time_rows
                    ),

                "POSTV16_AV3_A5_R2_LockedOOD_Generalization_Evidence.json":
                    json_bytes(
                        generalization
                    ),

                "POSTV16_AV3_A5_R2_Decision_Contract.json":
                    json_bytes(
                        decision
                    ),

                "PAD_Stream_POSTV16_AV3_A5_R2_Summary.json":
                    json_bytes(
                        summary
                    ),

                "POSTV16_AV3_A5_R2_Final_Gate_Matrix.csv":
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
                != "POSTV16_AV3_A5_R2_Artifact_Manifest.csv"
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
                "POSTV16_AV3_A5_R2_Artifact_Manifest.csv":
                    csv_bytes(
                        manifest_rows
                    )
            },
        )

        print()
        print("=" * 212)
        print("POSTV16-AV3-A5-R2: FROZEN CHECKPOINT / ONE-TOUCH LOCKED-OOD PASS")
        print("=" * 212)
        print("Original AV3-A5 technical BLOCK             : PRESERVED")
        print("A5-R1 closure authority                     : USED")
        print("Training repeated                            : False")
        print("Checkpoint reselected                        : False")
        print("Frozen checkpoint SHA256                     :", EXPECTED_CHECKPOINT_SHA)
        print("Best epoch / epochs completed                :", EXPECTED_BEST_EPOCH, "/", EXPECTED_EPOCHS)
        print("Best validation total objective              :", EXPECTED_BEST_VAL)
        print("Corrected pre-OOD integrity                  : PASS")
        print("Locked OOD teacher generation                : ONCE")
        print("Locked OOD evaluation                        : ONCE")
        print("Validation RMSE / MAE                        :", validation_metrics["rmse"], "/", validation_metrics["mae"])
        print("Locked OOD RMSE / MAE                        :", ood_metrics["rmse"], "/", ood_metrics["mae"])
        print("OOD / validation RMSE ratio                  :", generalization["OOD_to_validation_RMSE_ratio"])
        print("OOD / validation MAE ratio                   :", generalization["OOD_to_validation_MAE_ratio"])
        print("Locked OOD physics residual MSE              :", ood_physics_residual_mse)
        print("OOD accuracy threshold gate                  : False")
        print("Post-OOD training / reselection / refit      : False / False / False")
        print("Second OOD generation / evaluation           : NOT AUTHORIZED")
        print("Mapback / LP / CMG                           : False / False / Deferred")
        print("POSTV16-AV3-A6 design/freeze                 : AUTHORIZED")
        print("A6 execution                                 : NOT YET AUTHORIZED")
        print("=" * 212)

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
            "original_AV3A5_technical_BLOCK_reclassified":
                False,
            "training_repeated":
                False,
            "checkpoint_reselected":
                False,
            "normalization_refit":
                False,
            "OOD_opened_in_A5R2":
                ood_opened,
            "OOD_teacher_generated_in_A5R2":
                ood_teacher_generated,
            "OOD_evaluated_in_A5R2":
                ood_evaluated,
            "retraining_authorized":
                False,
            "checkpoint_reselection_authorized":
                False,
            "second_OOD_generation_authorized":
                False,
            "second_OOD_evaluation_authorized":
                False,
            "AV3_A6_authorized":
                False,
            "gates":
                gates,
        }

        p = (
            fail_dir
            / "POSTV16_AV3_A5_R2_Scientific_Fail_Report.json"
        )

        if not p.exists():
            p.write_bytes(
                json_bytes(
                    report
                )
            )

        print()
        print("=" * 212)
        print("POSTV16-AV3-A5-R2: SCIENTIFIC FAIL")
        print("=" * 212)
        print("Failed stage              :", stage)
        print("Failed gate               :", exc.gate)
        print("OOD opened                :", ood_opened)
        print("OOD teacher generated     :", ood_teacher_generated)
        print("OOD evaluated             :", ood_evaluated)
        print("Retraining authorized     : False")
        print("Second OOD authorized     : False")
        print("POSTV16-AV3-A6            : NOT AUTHORIZED")
        print("=" * 212)

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
            "original_AV3A5_technical_BLOCK_reclassified":
                False,
            "training_repeated":
                False,
            "checkpoint_reselected":
                False,
            "normalization_refit":
                False,
            "OOD_opened_in_A5R2":
                ood_opened,
            "OOD_teacher_generated_in_A5R2":
                ood_teacher_generated,
            "OOD_evaluated_in_A5R2":
                ood_evaluated,
            "retraining_authorized":
                False,
            "checkpoint_reselection_authorized":
                False,
            "second_OOD_generation_authorized":
                False,
            "second_OOD_evaluation_authorized":
                False,
            "AV3_A6_authorized":
                False,
            "gates":
                gates,
        }

        p = (
            block_dir
            / "POSTV16_AV3_A5_R2_Blocked_Report.json"
        )

        if not p.exists():
            p.write_bytes(
                json_bytes(
                    report
                )
            )

        print()
        print("=" * 212)
        print("POSTV16-AV3-A5-R2: TECHNICAL BLOCK")
        print("=" * 212)
        print("Failed stage              :", stage)
        print("Exception                 :", repr(exc))
        print("OOD opened                :", ood_opened)
        print("OOD teacher generated     :", ood_teacher_generated)
        print("OOD evaluated             :", ood_evaluated)
        print("Retraining authorized     : False")
        print("Second OOD authorized     : False")
        print("POSTV16-AV3-A6            : NOT AUTHORIZED")
        print("=" * 212)

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
