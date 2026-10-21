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


MILESTONE = "POSTV16-AV3-A5-R1"

STATUS_PASS = (
    "AV3A5R1_IMMUTABLE_A5_TECHNICAL_BLOCK_PRESERVED_"
    "PRE_OOD_TRILINEAR_AUDIT_SCHEMA_ROOT_CAUSE_CLOSED_"
    "FROZEN_CHECKPOINT_CONTINUATION_AUTHORITY_FROZEN"
)

STATUS_BLOCKED = "AV3A5R1_TECHNICAL_BLOCK_CLOSURE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

PARENT_A5_COMMIT = "a8fc00588eaf2ac67283d6b535f9af15bc3e31ad"

A5 = "PAD_Stream_POSTV16_AV3_A5_PIRNN_Training_Checkpoint_and_OneTouch_OOD.py"
A5_BLOB = "ab1b7fbfc2330c995762ada0379e424cc09599f0"

R2 = (
    "PAD_Stream_POSTV16_AV3_A4_R2_"
    "Corrected_Certification_Teacher_Dataset_and_LockedOOD_Predictor.py"
)
R2_BLOB = "289901331e835afb44ff2f665fe9a6bbea2eac19"

C2 = "PAD_Stream_V16C2_Multi_Coordinate_Streamline_Transport_Database_Assembly.py"
C2_BLOB = "21ff44de456102772c99f7ddc80898c9139a76db"

SOURCE_BLOBS = {
    A5: A5_BLOB,
    R2: R2_BLOB,
    C2: C2_BLOB,
}

BASE = (
    Path("post_v16")
    / RID
    / "POSTV16_AV3_Corey_Relperm_Heterogeneity"
)

A5_OUT_REL = (
    BASE
    / "POSTV16_AV3_A5_PIRNN_Training_Checkpoint_and_OneTouch_OOD"
)

A5_BLOCK_REL = BASE / "POSTV16_AV3_A5_BLOCKED"

BLOCK_NAME = "POSTV16_AV3_A5_Blocked_Report.json"

CHECKPOINT = "POSTV16_AV3_A5_Best_Validation_Model.keras"
FREEZE = "POSTV16_AV3_A5_Best_Validation_Checkpoint_Freeze.json"
HISTORY = "POSTV16_AV3_A5_Training_History.csv"
VAL_PRED = "POSTV16_AV3_A5_Validation_Predictions_Before_OOD.npz"
OOD_MARKER = "POSTV16_AV3_A5_LOCKED_OOD_OPENED.marker"

EXPECTED_CHECKPOINT_SHA = (
    "17b188494e0452570d43e868c20c4c814e6a1f0b493329d0e40849c4c5ec6d4e"
)

EXPECTED_BEST_EPOCH = 92
EXPECTED_EPOCHS = 122
EXPECTED_BEST_VAL = 0.002138707781058555

OUT_REL = (
    BASE
    / "POSTV16_AV3_A5_R1_PreOOD_Technical_Block_Closure"
)

BLOCK_REL = BASE / "POSTV16_AV3_A5_R1_BLOCKED"


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


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)

    if spec is None or spec.loader is None:
        raise GateError("cannot_load_module:" + str(path))

    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)

    return module


def self_test() -> None:
    audit = {
        "x_clip_count": 0,
        "y_clip_count": 0,
        "z_clip_count": 0,
        "total_points": 1,
    }

    assert "finite" not in audit

    assert set(audit) == {
        "x_clip_count",
        "y_clip_count",
        "z_clip_count",
        "total_points",
    }

    assert EXPECTED_BEST_EPOCH == 92
    assert EXPECTED_EPOCHS == 122

    print(
        "POSTV16-AV3-A5-R1 pre-OOD technical-block closure self-test: PASS"
    )


def main(
    root: Path,
    drive: Path,
) -> int:

    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"

    out = drive / OUT_REL
    blocked = drive / BLOCK_REL

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

        print(
            f"[{'PASS' if ok else 'FAIL'}] {name}"
            + (
                f" — {value}"
                if value is not None
                else ""
            )
        )

        if not ok:
            raise GateError(name)

    print("=" * 206)
    print(
        "POSTV16-AV3-A5-R1 — IMMUTABLE A5 TECHNICAL-BLOCK PRESERVATION / "
        "PRE-OOD AUDIT-SCHEMA ROOT-CAUSE CLOSURE"
    )
    print("=" * 206)
    print("DESIGN / FAILURE-CLOSURE ONLY.")
    print("NO TRAINING. NO CHECKPOINT RESELECTION. NO NORMALIZATION REFIT.")
    print("NO AV3CR0004 Y GENERATION. NO OOD MARKER. NO OOD EVALUATION.")
    print("ORIGINAL AV3-A5 TECHNICAL BLOCK REMAINS IMMUTABLE.")
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
            "repository_parent_is_blocked_A5_commit",
            parent == PARENT_A5_COMMIT,
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
                actual == expected,
                actual,
            )

        # ------------------------------------------------------------------------------------------
        # Bind immutable A5 technical block.
        # ------------------------------------------------------------------------------------------
        stage = "A5_block_binding"

        a5_out = drive / A5_OUT_REL

        a5_block = (
            drive
            / A5_BLOCK_REL
            / BLOCK_NAME
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

        ood_marker = (
            a5_out
            / OOD_MARKER
        )

        gate(
            "A5_block_report_present",
            a5_block.is_file(),
            str(a5_block),
        )

        block = load_json(
            a5_block
        )

        gate(
            "A5_block_status_exact",
            block[
                "status"
            ]
            == "AV3A5_TECHNICAL_EXECUTION_BLOCKED",
            block[
                "status"
            ],
        )

        gate(
            "A5_block_failed_stage_exact",
            block[
                "failed_stage"
            ]
            == "pre_OOD_integrity",
            block[
                "failed_stage"
            ],
        )

        gate(
            "A5_block_exception_exact",
            block[
                "exception"
            ]
            == "KeyError('finite')",
            block[
                "exception"
            ],
        )

        gate(
            "A5_training_started",
            block[
                "training_started"
            ]
            is True,
        )

        gate(
            "A5_checkpoint_frozen_true",
            block[
                "checkpoint_frozen"
            ]
            is True,
        )

        gate(
            "A5_OOD_never_opened",
            block[
                "locked_OOD_opened"
            ]
            is False,
        )

        gate(
            "A5_OOD_teacher_not_generated",
            block[
                "locked_OOD_teacher_generated"
            ]
            is False,
        )

        gate(
            "A5_OOD_not_evaluated",
            block[
                "locked_OOD_evaluated"
            ]
            is False,
        )

        gate(
            "A5_retraining_not_authorized",
            block[
                "retraining_authorized"
            ]
            is False,
        )

        gate(
            "A5_second_OOD_not_authorized",
            block[
                "second_OOD_generation_authorized"
            ]
            is False
            and block[
                "second_OOD_evaluation_authorized"
            ]
            is False,
        )

        # ------------------------------------------------------------------------------------------
        # Bind frozen checkpoint and completed training.
        # ------------------------------------------------------------------------------------------
        stage = "checkpoint_training_binding"

        for p in [
            checkpoint,
            freeze_path,
            history_path,
            val_pred_path,
        ]:
            gate(
                f"partial_A5_artifact_present_{p.name}",
                p.is_file(),
                str(p),
            )

        gate(
            "A5_OOD_marker_absent",
            not ood_marker.exists(),
            str(ood_marker),
        )

        checkpoint_sha = sha256_file(
            checkpoint
        )

        gate(
            "checkpoint_SHA_exact",
            checkpoint_sha
            == EXPECTED_CHECKPOINT_SHA,
            checkpoint_sha,
        )

        freeze = load_json(
            freeze_path
        )

        gate(
            "freeze_checkpoint_SHA_exact",
            freeze[
                "checkpoint_sha256"
            ]
            == EXPECTED_CHECKPOINT_SHA,
            freeze[
                "checkpoint_sha256"
            ],
        )

        gate(
            "freeze_best_epoch_exact",
            int(
                freeze[
                    "best_epoch"
                ]
            )
            == EXPECTED_BEST_EPOCH,
            freeze[
                "best_epoch"
            ],
        )

        gate(
            "freeze_epochs_completed_exact",
            int(
                freeze[
                    "epochs_completed"
                ]
            )
            == EXPECTED_EPOCHS,
            freeze[
                "epochs_completed"
            ],
        )

        gate(
            "freeze_best_validation_total_exact",
            abs(
                float(
                    freeze[
                        "best_validation_total_objective_during_training"
                    ]
                )
                - EXPECTED_BEST_VAL
            )
            <= 1.0e-15,
            freeze[
                "best_validation_total_objective_during_training"
            ],
        )

        gate(
            "checkpoint_frozen_before_OOD",
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
            "no_post_freeze_optimizer_or_reselection",
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
            "training_history_epoch_count_122",
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
                    r[
                        "validation_total"
                    ]
                )
                for r in history
            ],
            dtype=np.float64,
        )

        gate(
            "training_history_best_epoch_92",
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
            "training_history_best_validation_total_exact",
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

            gate(
                "validation_prediction_checkpoint_SHA_exact",
                str(
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
                == EXPECTED_CHECKPOINT_SHA,
            )

            gate(
                "validation_prediction_shape_exact",
                np.asarray(
                    z[
                        "Y_true"
                    ]
                ).shape
                == (
                    9702,
                    201,
                )
                and np.asarray(
                    z[
                        "Y_pred"
                    ]
                ).shape
                == (
                    9702,
                    201,
                ),
            )

        # ------------------------------------------------------------------------------------------
        # Exact root-cause closure.
        # ------------------------------------------------------------------------------------------
        stage = "root_cause_closure"

        a5_text = (
            root
            / A5
        ).read_text(
            encoding="utf-8"
        )

        gate(
            "blocked_A5_source_contains_invalid_finite_lookup",
            'phi_audit[\n                "finite"\n            ]'
            in a5_text,
        )

        c2 = load_module(
            root
            / C2,
            "av3a5r1_c2",
        )

        field = np.ones(
            (
                2,
                2,
                2,
            ),
            dtype=np.float64,
        )

        xyz = np.asarray(
            [
                [
                    [
                        0.5,
                        0.5,
                        0.5,
                    ]
                ]
            ],
            dtype=np.float64,
        )

        sampled, audit = c2.trilinear(
            field,
            xyz,
            1.0,
            1.0,
            1.0,
            np.asarray(
                [
                    0.5,
                    0.5,
                    0.5,
                ],
                dtype=np.float64,
            ),
        )

        gate(
            "V16C2_trilinear_audit_keys_exact",
            set(
                audit
            )
            == {
                "x_clip_count",
                "y_clip_count",
                "z_clip_count",
                "total_points",
            },
            sorted(
                audit
            ),
        )

        gate(
            "V16C2_trilinear_has_no_finite_key",
            "finite"
            not in audit,
        )

        gate(
            "correct_finiteness_semantics_direct_array_test",
            np.isfinite(
                sampled
            ).all(),
        )

        # ------------------------------------------------------------------------------------------
        # Freeze continuation contract. NO OOD access here.
        # ------------------------------------------------------------------------------------------
        stage = "continuation_contract_freeze"

        continuation = {
            "milestone": "POSTV16-AV3-A5-R2",
            "name": (
                "Frozen-Checkpoint Pre-OOD Integrity Correction / "
                "One-Touch Locked-OOD Continuation"
            ),
            "authorized": True,
            "execution": True,
            "frozen_checkpoint_sha256":
                EXPECTED_CHECKPOINT_SHA,
            "best_epoch":
                EXPECTED_BEST_EPOCH,
            "epochs_completed":
                EXPECTED_EPOCHS,
            "best_validation_total_objective":
                EXPECTED_BEST_VAL,
            "training_in_R2":
                False,
            "checkpoint_reselection_in_R2":
                False,
            "normalization_refit_in_R2":
                False,
            "hyperparameter_retuning_in_R2":
                False,
            "corrected_pre_OOD_finiteness_test":
                "np.isfinite(phi_ood_64).all()",
            "required_sequence": [
                "bind the immutable A5 technical BLOCK",
                "bind the exact frozen epoch-92 checkpoint",
                "verify the original A5 OOD marker remains absent",
                "reconstruct AV3CR0004 pre-OOD integrity without using phi_audit['finite']",
                "verify sampled porosity is finite directly and matches the frozen R2 sidecar",
                "verify native float64 operator geometry and constitutive sidecars",
                "write a new A5-R2 one-touch OOD marker only after every corrected pre-OOD integrity gate passes",
                "generate AV3CR0004 teacher exactly once",
                "evaluate the frozen checkpoint exactly once",
                "record OOD metrics descriptively with no accuracy threshold",
                "perform no post-OOD training, reselection, refit, retuning, second generation, or second evaluation",
            ],
            "forbidden": [
                "rerun training",
                "select another checkpoint",
                "refit normalization",
                "change model architecture or objective",
                "open AV3CR0004 before corrected integrity closure",
                "perform a second OOD generation or evaluation",
                "reclassify the original A5 technical BLOCK as PASS",
            ],
        }

        root_cause = {
            "milestone": MILESTONE,
            "original_A5_status":
                block[
                    "status"
                ],
            "original_A5_failed_stage":
                block[
                    "failed_stage"
                ],
            "original_A5_exception":
                block[
                    "exception"
                ],
            "classification":
                "TECHNICAL_SCHEMA_MISMATCH_PRE_OOD",
            "invalid_lookup":
                'phi_audit["finite"]',
            "actual_V16C2_trilinear_audit_keys":
                sorted(
                    audit
                ),
            "correct_test":
                "np.isfinite(sampled_array).all()",
            "checkpoint_or_training_defect":
                False,
            "teacher_physics_defect":
                False,
            "OOD_exposure_occurred":
                False,
            "original_BLOCK_reclassified":
                False,
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "original_AV3A5_technical_BLOCK_preserved":
                True,
            "root_cause_classification":
                "TECHNICAL_SCHEMA_MISMATCH_PRE_OOD",
            "frozen_checkpoint_authority_preserved":
                True,
            "checkpoint_sha256":
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
            "locked_OOD_target_opened":
                False,
            "locked_OOD_teacher_generated":
                False,
            "locked_OOD_evaluated":
                False,
            "AV3_A5_R2_authorized":
                True,
            "AV3_A6_authorized":
                False,
            "next":
                continuation,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "original_AV3A5_technical_BLOCK_preserved":
                True,
            "technical_root_cause":
                "A5 referenced nonexistent V16C2 trilinear audit key 'finite'",
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
            "OOD_access_in_R1":
                False,
            "AV3_A5_R2_authorized":
                True,
            "AV3_A6_authorized":
                False,
        }

        files = {
            "PAD_Stream_POSTV16_AV3_A5_R1_Summary.json":
                json_bytes(
                    summary
                ),

            "POSTV16_AV3_A5_R1_Technical_Block_Root_Cause.json":
                json_bytes(
                    root_cause
                ),

            "POSTV16_AV3_A5_R1_Frozen_Checkpoint_Authority.json":
                json_bytes(
                    {
                        "checkpoint_sha256":
                            EXPECTED_CHECKPOINT_SHA,
                        "best_epoch":
                            EXPECTED_BEST_EPOCH,
                        "epochs_completed":
                            EXPECTED_EPOCHS,
                        "best_validation_total_objective":
                            EXPECTED_BEST_VAL,
                        "checkpoint_frozen_before_OOD":
                            True,
                        "training_repetition_authorized":
                            False,
                        "checkpoint_reselection_authorized":
                            False,
                    }
                ),

            "POSTV16_AV3_A5_R1_R2_Continuation_Contract.json":
                json_bytes(
                    continuation
                ),

            "POSTV16_AV3_A5_R1_Decision_Contract.json":
                json_bytes(
                    decision
                ),

            "POSTV16_AV3_A5_R1_Final_Gate_Matrix.csv":
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
                != "POSTV16_AV3_A5_R1_Artifact_Manifest.csv"
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
                "POSTV16_AV3_A5_R1_Artifact_Manifest.csv":
                    csv_bytes(
                        manifest_rows
                    )
            },
        )

        print()
        print("=" * 206)
        print("POSTV16-AV3-A5-R1: PRE-OOD TECHNICAL-BLOCK CLOSURE PASS")
        print("=" * 206)
        print("Original A5 technical BLOCK       : PRESERVED")
        print("Root cause                        : nonexistent phi_audit['finite'] key")
        print("Checkpoint SHA256                 :", EXPECTED_CHECKPOINT_SHA)
        print("Best epoch                        :", EXPECTED_BEST_EPOCH)
        print("Epochs completed                  :", EXPECTED_EPOCHS)
        print("Best validation total            :", EXPECTED_BEST_VAL)
        print("Training repeated                 : False")
        print("Checkpoint reselected             : False")
        print("OOD opened in R1                  : False")
        print("OOD teacher generated in R1       : False")
        print("OOD evaluated in R1               : False")
        print("POSTV16-AV3-A5-R2                 : AUTHORIZED")
        print("A5-R2 execution                   : AUTHORIZED")
        print("POSTV16-AV3-A6                    : NOT AUTHORIZED")
        print("=" * 206)

        return 0

    except Exception as exc:

        blocked.mkdir(
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
            "original_AV3A5_technical_BLOCK_reclassified":
                False,
            "training_repeated":
                False,
            "checkpoint_reselected":
                False,
            "locked_OOD_target_opened":
                False,
            "AV3_A5_R2_authorized":
                False,
            "AV3_A6_authorized":
                False,
        }

        p = (
            blocked
            / "POSTV16_AV3_A5_R1_Blocked_Report.json"
        )

        if not p.exists():
            p.write_bytes(
                json_bytes(
                    report
                )
            )

        print()
        print("POSTV16-AV3-A5-R1: BLOCKED")
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
        raise SystemExit(0)

    raise SystemExit(
        main(
            args.project_root,
            args.drive_root,
        )
    )
