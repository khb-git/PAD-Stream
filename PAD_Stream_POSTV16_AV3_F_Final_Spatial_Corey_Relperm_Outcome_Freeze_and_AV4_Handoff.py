#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np


MILESTONE = "POSTV16-AV3-F"

PROTOCOL_ID = (
    "POSTV16_AV3_F_FINAL_SPATIAL_COREY_RELPERM_SCIENTIFIC_OUTCOME_"
    "FREEZE_AND_AV4_DYNAMIC_FLOW_HANDOFF_V1"
)

STATUS_PASS = (
    "AV3_FINAL_SPATIAL_COREY_RELPERM_SCIENTIFIC_OUTCOME_FROZEN_"
    "AV4_DYNAMIC_FLOW_COUPLING_A0_AUTHORIZED"
)

STATUS_BLOCKED = "AV3F_FINAL_OUTCOME_FREEZE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_A6E_COMMIT = "299fe531cc2576cb8eb2394889d2176829af0121"

CHECKPOINT_SHA = (
    "17b188494e0452570d43e868c20c4c814e6a1f0b493329d0e40849c4c5ec6d4e"
)
BEST_EPOCH = 92
EPOCHS_COMPLETED = 122
BEST_VALIDATION_TOTAL = 0.002138707781058555

# Frozen A5-R2 descriptive predictive evidence.
EXPECTED_VALIDATION_RMSE = 0.02190303635032904
EXPECTED_VALIDATION_MAE = 0.012419776862723155
EXPECTED_OOD_RMSE = 0.022039389447979965
EXPECTED_OOD_MAE = 0.01256132183343651
EXPECTED_OOD_VAL_RMSE_RATIO = 1.0062253057279373
EXPECTED_OOD_VAL_MAE_RATIO = 1.0113967402375954
EXPECTED_OOD_PHYSICS_RESIDUAL_MSE = 0.17698767654321812

# Frozen A6-E end-to-end integration maxima.
EXPECTED_A6E_MAX_B1 = 4.0464371797013485e-16
EXPECTED_A6E_MAX_MASS = 2.0056025184931104e-16
EXPECTED_A6E_MAX_EOS = 4.0622642439853137e-16
EXPECTED_A6E_MAX_CAPACITY_EXCESS_KG = 9.094947017729282e-13
EXPECTED_A6E_MAX_H1_CAPACITY_FRACTION = 0.5568028851725462
EXPECTED_A6E_MAX_H1_OCCUPIED = 7630

A4_FAIL_SHA256 = (
    "1fdc0aeb7c462b7161525d52b1aa381b80885ffba00a4afa80875a67861cd08d"
)

# --------------------------------------------------------------------------------------------------
# Exact source lineage.
# --------------------------------------------------------------------------------------------------

A0 = "PAD_Stream_POSTV16_AV3_A0_Corey_Relperm_Authority_Gap_and_Physics_Impact_Freeze.py"
A1 = "PAD_Stream_POSTV16_AV3_A1_Corey_Relperm_Parameter_Field_Model_and_Split_Registry_Freeze.py"
A2 = "PAD_Stream_POSTV16_AV3_A2_Corey_Relperm_Field_Realization_Certification_and_Streamline_Sampling.py"
A3 = "PAD_Stream_POSTV16_AV3_A3_Transport_Teacher_Residual_and_PIRNN_Protocol_Freeze.py"
A3R1 = "PAD_Stream_POSTV16_AV3_A3_R1_First9_CellCentered_Geometry_and_Normalization_Authority_Correction.py"
A4 = "PAD_Stream_POSTV16_AV3_A4_Corrected_CellCentered_Teacher_Dataset_and_LockedOOD_Predictor.py"
A4R1 = "PAD_Stream_POSTV16_AV3_A4_R1_Teacher_Certification_Failure_Semantics_Closure.py"
A4R2 = "PAD_Stream_POSTV16_AV3_A4_R2_Corrected_Certification_Teacher_Dataset_and_LockedOOD_Predictor.py"
A5 = "PAD_Stream_POSTV16_AV3_A5_PIRNN_Training_Checkpoint_and_OneTouch_OOD.py"
A5R1 = "PAD_Stream_POSTV16_AV3_A5_R1_PreOOD_Technical_Block_Closure.py"
A5R2 = "PAD_Stream_POSTV16_AV3_A5_R2_Frozen_Checkpoint_OneTouch_OOD_Continuation.py"
A6 = "PAD_Stream_POSTV16_AV3_A6_Frozen_Checkpoint_Deployment_Integration_Contract_Freeze.py"
A6E = "PAD_Stream_POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution.py"

SOURCE_BLOBS = {
    A0: "a755a5ac20e81e81a925b39765bd303403b581b9",
    A1: "fb3b77b89ab3d1b12a09f967a476c4ecfcda0e33",
    A2: "e7d4f1b1e69ea3e756c4f41d7edb57e2ffd87d7b",
    A3: "40fe89c142e62aad750a749f0a8ae452574f28bd",
    A3R1: "2a70ef6b67ddefee61b5a9ab2fb080755fdb4b49",
    A4: "24a6e4b815b83dfe89eca85a18ccc23021b4eefb",
    A4R1: "cdd6c52de598cfc1674828d4d7918828e828f2ab",
    A4R2: "289901331e835afb44ff2f665fe9a6bbea2eac19",
    A5: "ab1b7fbfc2330c995762ada0379e424cc09599f0",
    A5R1: "1710ddffc2cb74ce171010ea55011b6c31ccad83",
    A5R2: "b2dd3fb27966a51e6a6057e444dfdb617976b36f",
    A6: "3e3937cc084807e5a439c2cd14f54914ac134db2",
    A6E: "e3dcb0aa9354c399904f7f0e830b6a1fddd78987",
}

# --------------------------------------------------------------------------------------------------
# Frozen milestone status identities.
# --------------------------------------------------------------------------------------------------

A0_STATUS = (
    "AV3A0_SPATIAL_COREY_RELPERM_AUTHORITY_GAP_PHYSICS_IMPACT_AND_SCOPE_"
    "PROSPECTIVELY_FROZEN_NO_FIELD_GENERATION"
)

A1_STATUS = (
    "AV3A1_COREY_RELPERM_PARAMETER_SUBSET_FIELD_MODEL_CORRELATION_BOUNDS_"
    "CHANNEL_SCHEMA_AND_SPLIT_REGISTRY_PROSPECTIVELY_FROZEN_NO_FIELD_GENERATION"
)

A2_STATUS = (
    "AV3A2_FROZEN_COREY_RELPERM_REALIZATIONS_GENERATED_CERTIFIED_"
    "AND_SAMPLED_TO_FROZEN_AV2_STREAMLINES_PASS"
)

A3_STATUS = (
    "AV3A3_SPATIAL_COREY_RELPERM_TRANSPORT_TEACHER_RESIDUAL_AND_"
    "13CHANNEL_PIRNN_PROTOCOL_PROSPECTIVELY_FROZEN_NO_TEACHER_OR_TRAINING_EXECUTION"
)

A3R1_STATUS = (
    "AV3A3R1_FIRST_NINE_CHANNEL_CELL_CENTERED_GEOMETRY_AND_"
    "TRAIN_NORMALIZATION_AUTHORITY_CORRECTION_FROZEN_NO_A4_EXECUTION"
)

A4_FAIL_STATUS = (
    "AV3A4_SPATIAL_COREY_RELPERM_TEACHER_OR_DATASET_SCIENTIFIC_FAIL_"
    "NO_OOD_OPENING_RESEED_RETUNE_OR_TRAINING_AUTHORIZED"
)

A4R1_STATUS = (
    "AV3A4R1_IMMUTABLE_A4_SCIENTIFIC_FAIL_PRESERVED_"
    "TEACHER_CERTIFICATION_GATE_SEMANTICS_ROOT_CAUSE_CLOSED_NO_TEACHER_REEXECUTION"
)

A4R2_STATUS = (
    "AV3A4R2_CORRECTED_CERTIFICATION_TRAIN_VALIDATION_TEACHERS_"
    "13CHANNEL_DATASET_PHYSICS_SIDECAR_AND_LOCKED_OOD_PREDICTOR_ONLY_PASS"
)

A5_BLOCK_STATUS = "AV3A5_TECHNICAL_EXECUTION_BLOCKED"

A5R1_STATUS = (
    "AV3A5R1_IMMUTABLE_A5_TECHNICAL_BLOCK_PRESERVED_"
    "PRE_OOD_TRILINEAR_AUDIT_SCHEMA_ROOT_CAUSE_CLOSED_"
    "FROZEN_CHECKPOINT_CONTINUATION_AUTHORITY_FROZEN"
)

A5R2_STATUS = (
    "AV3A5R2_FROZEN_EPOCH92_CHECKPOINT_PRE_OOD_INTEGRITY_CORRECTED_"
    "LOCKED_OOD_TEACHER_GENERATED_ONCE_EVALUATED_ONCE_PASS"
)

A6_STATUS = (
    "AV3A6_FROZEN_EPOCH92_CHECKPOINT_LOCAL_PV_R7D_TERMINAL_HALO_"
    "DEPLOYMENT_AND_INTEGRATION_CONTRACT_PROSPECTIVELY_FROZEN_NO_EXECUTION"
)

A6E_STATUS = (
    "AV3A6E_FROZEN_EPOCH92_CHECKPOINT_LOCAL_PORE_VOLUME_R7D_TERMINAL_HALO_"
    "INTEGRATION_ALL_4_REALIZATIONS_ALL_9_TIMES_PASS"
)

# --------------------------------------------------------------------------------------------------
# Drive authorities.
# --------------------------------------------------------------------------------------------------

BASE = (
    Path("post_v16")
    / RID
    / "POSTV16_AV3_Corey_Relperm_Heterogeneity"
)

MILESTONES = {
    "A0": (
        BASE / "POSTV16_AV3_A0_Corey_Relperm_Authority_Gap_and_Physics_Impact_Freeze",
        "PAD_Stream_POSTV16_AV3_A0_Summary.json",
        "POSTV16_AV3_A0_Artifact_Manifest.csv",
        A0_STATUS,
    ),
    "A1": (
        BASE / "POSTV16_AV3_A1_Corey_Relperm_Parameter_Field_Model_and_Split_Registry_Freeze",
        "PAD_Stream_POSTV16_AV3_A1_Summary.json",
        "POSTV16_AV3_A1_Artifact_Manifest.csv",
        A1_STATUS,
    ),
    "A2": (
        BASE / "POSTV16_AV3_A2_Corey_Relperm_Field_Realization_Certification_and_Streamline_Sampling",
        "PAD_Stream_POSTV16_AV3_A2_Summary.json",
        "POSTV16_AV3_A2_Artifact_Manifest.csv",
        A2_STATUS,
    ),
    "A3": (
        BASE / "POSTV16_AV3_A3_Transport_Teacher_Residual_and_PIRNN_Protocol_Freeze",
        "PAD_Stream_POSTV16_AV3_A3_Summary.json",
        "POSTV16_AV3_A3_Artifact_Manifest.csv",
        A3_STATUS,
    ),
    "A3R1": (
        BASE / "POSTV16_AV3_A3_R1_First9_CellCentered_Geometry_and_Normalization_Authority_Correction",
        "PAD_Stream_POSTV16_AV3_A3_R1_Summary.json",
        "POSTV16_AV3_A3_R1_Artifact_Manifest.csv",
        A3R1_STATUS,
    ),
    "A4R1": (
        BASE / "POSTV16_AV3_A4_R1_Teacher_Certification_Failure_Semantics_Closure",
        "PAD_Stream_POSTV16_AV3_A4_R1_Summary.json",
        "POSTV16_AV3_A4_R1_Artifact_Manifest.csv",
        A4R1_STATUS,
    ),
    "A4R2": (
        BASE / "POSTV16_AV3_A4_R2_Corrected_Teacher_Dataset_and_LockedOOD_Predictor",
        "PAD_Stream_POSTV16_AV3_A4_R2_Summary.json",
        "POSTV16_AV3_A4_R2_Artifact_Manifest.csv",
        A4R2_STATUS,
    ),
    "A5R1": (
        BASE / "POSTV16_AV3_A5_R1_PreOOD_Technical_Block_Closure",
        "PAD_Stream_POSTV16_AV3_A5_R1_Summary.json",
        "POSTV16_AV3_A5_R1_Artifact_Manifest.csv",
        A5R1_STATUS,
    ),
    "A5R2": (
        BASE / "POSTV16_AV3_A5_R2_Frozen_Checkpoint_OneTouch_OOD_Continuation",
        "PAD_Stream_POSTV16_AV3_A5_R2_Summary.json",
        "POSTV16_AV3_A5_R2_Artifact_Manifest.csv",
        A5R2_STATUS,
    ),
    "A6": (
        BASE / "POSTV16_AV3_A6_Deployment_Integration_Contract_Freeze",
        "PAD_Stream_POSTV16_AV3_A6_Summary.json",
        "POSTV16_AV3_A6_Artifact_Manifest.csv",
        A6_STATUS,
    ),
    "A6E": (
        BASE / "POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution",
        "PAD_Stream_POSTV16_AV3_A6_E_Summary.json",
        "POSTV16_AV3_A6_E_Artifact_Manifest.csv",
        A6E_STATUS,
    ),
}

A4_FAIL_REL = (
    BASE
    / "POSTV16_AV3_A4_SCIENTIFIC_FAIL"
    / "POSTV16_AV3_A4_Scientific_Fail_Report.json"
)

A5_BLOCK_REL = (
    BASE
    / "POSTV16_AV3_A5_BLOCKED"
    / "POSTV16_AV3_A5_Blocked_Report.json"
)

A5R2_GENERALIZATION = (
    BASE
    / "POSTV16_AV3_A5_R2_Frozen_Checkpoint_OneTouch_OOD_Continuation"
    / "POSTV16_AV3_A5_R2_LockedOOD_Generalization_Evidence.json"
)

A5R2_DECISION = (
    BASE
    / "POSTV16_AV3_A5_R2_Frozen_Checkpoint_OneTouch_OOD_Continuation"
    / "POSTV16_AV3_A5_R2_Decision_Contract.json"
)

A6E_DIR = (
    BASE
    / "POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
)

A6E_DECISION = A6E_DIR / "POSTV16_AV3_A6_E_Decision_Contract.json"
A6E_REALIZATION = A6E_DIR / "POSTV16_AV3_A6_E_Realization_Summary.csv"
A6E_TIMEWISE = A6E_DIR / "POSTV16_AV3_A6_E_Timewise_Integration_Audit.csv"
A6E_GATES = A6E_DIR / "POSTV16_AV3_A6_E_Final_Gate_Matrix.csv"

OUT_REL = BASE / "POSTV16_AV3_F_Final_Outcome_Freeze_and_AV4_Handoff"
BLOCK_REL = BASE / "POSTV16_AV3_F_BLOCKED"

DAYS = np.asarray(
    [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0],
    dtype=np.float64,
)

EXPECTED_DOMAINS = {
    "AV3CR0001": (20269, 11159, 31428),
    "AV3CR0002": (20592, 10799, 31391),
    "AV3CR0003": (20504, 10935, 31439),
    "AV3CR0004": (20190, 10918, 31108),
}


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
        actual = sha256_file(p)
        if actual != expected:
            raise GateError("manifest_SHA_mismatch:" + fn)

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


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)

    for name, data in files.items():
        p = out / name

        if p.exists() and p.read_bytes() != data:
            raise GateError("existing_output_differs:" + name)

        if not p.exists():
            p.write_bytes(data)


def true_value(v: Any) -> bool:
    return str(v).strip().lower() == "true"


def close(a: float, b: float, atol: float = 1.0e-15) -> bool:
    return abs(float(a) - float(b)) <= atol


def self_test() -> None:
    assert len(SOURCE_BLOBS) == 13
    assert len(MILESTONES) == 11
    assert len(EXPECTED_DOMAINS) == 4
    assert len(DAYS) == 9
    assert BEST_EPOCH == 92
    assert EPOCHS_COMPLETED == 122
    assert STATUS_PASS.endswith("AV4_DYNAMIC_FLOW_COUPLING_A0_AUTHORIZED")

    print(
        "POSTV16-AV3-F final spatial-Corey/relperm outcome-freeze self-test: PASS"
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
            + (f" — {value}" if value is not None else "")
        )

        if not ok:
            raise GateError(name)

    print("=" * 214)
    print(
        "POSTV16-AV3-F — FINAL SPATIAL COREY / RELATIVE-PERMEABILITY "
        "SCIENTIFIC OUTCOME FREEZE + AV4 HANDOFF"
    )
    print("=" * 214)
    print("AUDIT / FREEZE ONLY.")
    print("NO TRAINING. NO MODEL INFERENCE. NO OOD REOPENING.")
    print("NO LP. NO MAPBACK. NO EOS EXECUTION.")
    print("NO PRESSURE/Q RECOMPUTATION. NO POLLOCK/TOF RECOMPUTATION.")
    print("NO CMG.")
    print("AV3-A4 SCIENTIFIC FAIL AND AV3-A5 TECHNICAL BLOCK REMAIN IMMUTABLE.")
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
            "repository_parent_is_A6E_commit",
            parent == PARENT_A6E_COMMIT,
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
                git_text(
                    root,
                    "hash-object",
                    str(p),
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
        # Bind every formal PASS milestone in the AV3 lineage.
        # ------------------------------------------------------------------------------------------
        stage = "milestone_authority_binding"

        bound_manifests: dict[str, Any] = {}
        summaries: dict[str, dict[str, Any]] = {}

        for label, (
            rel,
            summary_name,
            manifest_name,
            expected_status,
        ) in MILESTONES.items():

            d = drive / rel

            gate(
                f"{label}_output_present",
                d.is_dir(),
                str(d),
            )

            m = verify_manifest(
                d,
                manifest_name,
            )

            s = load_json(
                d
                / summary_name
            )

            gate(
                f"{label}_status_exact",
                s[
                    "status"
                ]
                == expected_status,
                s[
                    "status"
                ],
            )

            bound_manifests[
                label
            ] = {
                "manifest_file":
                    manifest_name,
                "manifest_sha256":
                    sha256_file(
                        d
                        / manifest_name
                    ),
                "entries":
                    len(m),
            }

            summaries[
                label
            ] = s

        # ------------------------------------------------------------------------------------------
        # Immutable AV3-A4 scientific FAIL and its semantic closure.
        # ------------------------------------------------------------------------------------------
        stage = "A4_failure_history_binding"

        a4_fail_path = drive / A4_FAIL_REL

        gate(
            "A4_original_FAIL_report_present",
            a4_fail_path.is_file(),
            str(a4_fail_path),
        )

        gate(
            "A4_original_FAIL_SHA256_exact",
            sha256_file(
                a4_fail_path
            )
            == A4_FAIL_SHA256,
            sha256_file(
                a4_fail_path
            ),
        )

        a4_fail = load_json(
            a4_fail_path
        )

        gate(
            "A4_original_status_FAIL_exact",
            a4_fail[
                "status"
            ]
            == A4_FAIL_STATUS,
            a4_fail[
                "status"
            ],
        )

        gate(
            "A4_original_failed_stage_teacher_generation",
            a4_fail[
                "failed_stage"
            ]
            == "teacher_generation",
            a4_fail[
                "failed_stage"
            ],
        )

        gate(
            "A4_original_failed_gate_CR0001",
            a4_fail[
                "failed_gate"
            ]
            == "AV3CR0001_teacher_certification",
            a4_fail[
                "failed_gate"
            ],
        )

        gate(
            "A4_original_completed_zero",
            int(
                a4_fail[
                    "teacher_realizations_completed"
                ]
            )
            == 0,
            a4_fail[
                "teacher_realizations_completed"
            ],
        )

        gate(
            "A4_original_OOD_closed_training_false",
            a4_fail[
                "LOCKED_OOD_target_opened"
            ]
            is False
            and a4_fail[
                "training"
            ]
            is False,
        )

        a4r1 = summaries[
            "A4R1"
        ]

        gate(
            "A4R1_original_FAIL_preserved",
            a4r1[
                "original_A4_status"
            ]
            == A4_FAIL_STATUS,
            a4r1[
                "original_A4_status"
            ],
        )

        gate(
            "A4R1_no_teacher_reexecution_or_OOD_access",
            a4r1[
                "teacher_reexecution"
            ]
            is False
            and a4r1[
                "locked_OOD_target_access"
            ]
            is False,
        )

        # ------------------------------------------------------------------------------------------
        # Immutable AV3-A5 technical BLOCK and explicit R1/R2 closure.
        # ------------------------------------------------------------------------------------------
        stage = "A5_block_history_binding"

        a5_block_path = drive / A5_BLOCK_REL

        gate(
            "A5_original_BLOCK_report_present",
            a5_block_path.is_file(),
            str(a5_block_path),
        )

        a5_block = load_json(
            a5_block_path
        )

        gate(
            "A5_original_BLOCK_status_exact",
            a5_block[
                "status"
            ]
            == A5_BLOCK_STATUS,
            a5_block[
                "status"
            ],
        )

        gate(
            "A5_original_BLOCK_stage_exact",
            a5_block[
                "failed_stage"
            ]
            == "pre_OOD_integrity",
            a5_block[
                "failed_stage"
            ],
        )

        gate(
            "A5_original_BLOCK_exception_exact",
            a5_block[
                "exception"
            ]
            == "KeyError('finite')",
            a5_block[
                "exception"
            ],
        )

        gate(
            "A5_original_checkpoint_frozen",
            a5_block[
                "checkpoint_frozen"
            ]
            is True,
        )

        gate(
            "A5_original_OOD_unopened",
            a5_block[
                "locked_OOD_opened"
            ]
            is False
            and a5_block[
                "locked_OOD_teacher_generated"
            ]
            is False
            and a5_block[
                "locked_OOD_evaluated"
            ]
            is False,
        )

        a5r1 = summaries[
            "A5R1"
        ]

        gate(
            "A5R1_original_BLOCK_preserved",
            a5r1[
                "original_AV3A5_technical_BLOCK_preserved"
            ]
            is True,
        )

        gate(
            "A5R1_root_cause_exact",
            a5r1[
                "technical_root_cause"
            ]
            == "A5 referenced nonexistent V16C2 trilinear audit key 'finite'",
            a5r1[
                "technical_root_cause"
            ],
        )

        gate(
            "A5R1_checkpoint_authority_exact",
            a5r1[
                "frozen_checkpoint_sha256"
            ]
            == CHECKPOINT_SHA
            and int(
                a5r1[
                    "best_epoch"
                ]
            )
            == BEST_EPOCH
            and int(
                a5r1[
                    "epochs_completed"
                ]
            )
            == EPOCHS_COMPLETED
            and close(
                a5r1[
                    "best_validation_total_objective"
                ],
                BEST_VALIDATION_TOTAL,
                1.0e-15,
            ),
        )

        gate(
            "A5R1_no_retraining_or_OOD_access",
            a5r1[
                "training_repeated"
            ]
            is False
            and a5r1[
                "checkpoint_reselected"
            ]
            is False
            and a5r1[
                "OOD_access_in_R1"
            ]
            is False,
        )

        # ------------------------------------------------------------------------------------------
        # A5-R2 exact frozen checkpoint + one-touch locked-OOD evidence.
        # ------------------------------------------------------------------------------------------
        stage = "A5R2_predictive_evidence_binding"

        a5r2 = summaries[
            "A5R2"
        ]

        a5r2_decision = load_json(
            drive
            / A5R2_DECISION
        )

        a5r2_generalization = load_json(
            drive
            / A5R2_GENERALIZATION
        )

        gate(
            "A5R2_checkpoint_exact",
            a5r2[
                "frozen_checkpoint_sha256"
            ]
            == CHECKPOINT_SHA
            and int(
                a5r2[
                    "best_epoch"
                ]
            )
            == BEST_EPOCH
            and int(
                a5r2[
                    "epochs_completed"
                ]
            )
            == EPOCHS_COMPLETED
            and close(
                a5r2[
                    "best_validation_total_objective"
                ],
                BEST_VALIDATION_TOTAL,
                1.0e-15,
            ),
        )

        validation_metrics = a5r2[
            "validation_metrics"
        ]

        ood_metrics = a5r2[
            "locked_OOD_metrics"
        ]

        gate(
            "A5R2_validation_metrics_exact",
            close(
                validation_metrics[
                    "rmse"
                ],
                EXPECTED_VALIDATION_RMSE,
                1.0e-15,
            )
            and close(
                validation_metrics[
                    "mae"
                ],
                EXPECTED_VALIDATION_MAE,
                1.0e-15,
            ),
            validation_metrics,
        )

        gate(
            "A5R2_OOD_metrics_exact",
            close(
                ood_metrics[
                    "rmse"
                ],
                EXPECTED_OOD_RMSE,
                1.0e-15,
            )
            and close(
                ood_metrics[
                    "mae"
                ],
                EXPECTED_OOD_MAE,
                1.0e-15,
            ),
            ood_metrics,
        )

        gate(
            "A5R2_ratio_evidence_exact",
            close(
                a5r2[
                    "OOD_to_validation_RMSE_ratio"
                ],
                EXPECTED_OOD_VAL_RMSE_RATIO,
                1.0e-15,
            )
            and close(
                a5r2[
                    "OOD_to_validation_MAE_ratio"
                ],
                EXPECTED_OOD_VAL_MAE_RATIO,
                1.0e-15,
            ),
        )

        gate(
            "A5R2_physics_residual_exact",
            close(
                a5r2[
                    "locked_OOD_physics_residual_MSE"
                ],
                EXPECTED_OOD_PHYSICS_RESIDUAL_MSE,
                1.0e-15,
            ),
            a5r2[
                "locked_OOD_physics_residual_MSE"
            ],
        )

        gate(
            "A5R2_one_touch_and_no_adaptation",
            a5r2_decision[
                "locked_OOD_teacher_generated_once"
            ]
            is True
            and a5r2_decision[
                "locked_OOD_evaluated_once"
            ]
            is True
            and a5r2_decision[
                "post_OOD_training"
            ]
            is False
            and a5r2_decision[
                "post_OOD_checkpoint_reselection"
            ]
            is False
            and a5r2_decision[
                "post_OOD_normalization_refit"
            ]
            is False
            and a5r2_decision[
                "post_OOD_hyperparameter_retuning"
            ]
            is False
            and a5r2_decision[
                "second_OOD_generation_authorized"
            ]
            is False
            and a5r2_decision[
                "second_OOD_evaluation_authorized"
            ]
            is False,
        )

        gate(
            "A5R2_no_arbitrary_generalization_claim",
            a5r2_generalization[
                "arbitrary_generalization_claim_authorized"
            ]
            is False,
        )

        # ------------------------------------------------------------------------------------------
        # A6-E end-to-end 36-state integration authority.
        # ------------------------------------------------------------------------------------------
        stage = "A6E_integration_binding"

        a6e = summaries[
            "A6E"
        ]

        a6e_decision = load_json(
            drive
            / A6E_DECISION
        )

        realization_rows = read_csv(
            drive
            / A6E_REALIZATION
        )

        time_rows = read_csv(
            drive
            / A6E_TIMEWISE
        )

        a6e_gate_rows = read_csv(
            drive
            / A6E_GATES
        )

        gate(
            "A6E_checkpoint_exact",
            a6e[
                "checkpoint_sha256"
            ]
            == CHECKPOINT_SHA
            and int(
                a6e[
                    "checkpoint_best_epoch"
                ]
            )
            == BEST_EPOCH,
        )

        gate(
            "A6E_36_of_36_exact",
            int(
                a6e[
                    "realizations_completed"
                ]
            )
            == 4
            and int(
                a6e[
                    "canonical_times_per_realization"
                ]
            )
            == 9
            and int(
                a6e[
                    "integrated_states"
                ]
            )
            == 36,
        )

        gate(
            "A6E_global_metrics_exact",
            close(
                a6e[
                    "max_B1_projection_relative_closure"
                ],
                EXPECTED_A6E_MAX_B1,
                1.0e-30,
            )
            and close(
                a6e[
                    "max_mass_relative_closure"
                ],
                EXPECTED_A6E_MAX_MASS,
                1.0e-30,
            )
            and close(
                a6e[
                    "max_EOS_localPV_mass_relative_closure"
                ],
                EXPECTED_A6E_MAX_EOS,
                1.0e-30,
            )
            and close(
                a6e[
                    "max_post_reconciliation_capacity_excess_kg"
                ],
                EXPECTED_A6E_MAX_CAPACITY_EXCESS_KG,
                1.0e-24,
            )
            and close(
                a6e[
                    "max_H1_capacity_fraction_used"
                ],
                EXPECTED_A6E_MAX_H1_CAPACITY_FRACTION,
                1.0e-15,
            )
            and int(
                a6e[
                    "max_H1_occupied_cell_count"
                ]
            )
            == EXPECTED_A6E_MAX_H1_OCCUPIED,
        )

        gate(
            "A6E_all_464_gates_PASS",
            len(
                a6e_gate_rows
            )
            == 464
            and all(
                true_value(
                    row[
                        "passed"
                    ]
                )
                for row in a6e_gate_rows
            ),
            len(
                a6e_gate_rows
            ),
        )

        gate(
            "A6E_timewise_36_exact",
            len(
                time_rows
            )
            == 36,
            len(
                time_rows
            ),
        )

        gate(
            "A6E_no_OOD_reopen_or_flow_recompute",
            a6e_decision[
                "CR0004_Y_true_accessed"
            ]
            is False
            and a6e_decision[
                "CR0004_metric_recomputed"
            ]
            is False
            and a6e_decision[
                "CR0004_reinference"
            ]
            is False
            and a6e_decision[
                "CR0004_teacher_regenerated"
            ]
            is False
            and a6e_decision[
                "pressure_resolve"
            ]
            is False
            and a6e_decision[
                "Darcy_Q_recompute"
            ]
            is False
            and a6e_decision[
                "Pollock_retrace"
            ]
            is False
            and a6e_decision[
                "TOF_recompute"
            ]
            is False,
        )

        gate(
            "A6E_conservative_architecture_preserved",
            a6e_decision[
                "local_pore_volume_capacity_used"
            ]
            is True
            and a6e_decision[
                "B1_component_mass_bridge_preserved"
            ]
            is True
            and a6e_decision[
                "SG7D_E37A_subsegment_deposition_preserved"
            ]
            is True
            and a6e_decision[
                "R7D_terminal_halo_semantics_preserved"
            ]
            is True
            and a6e_decision[
                "R7R7A_arithmetic_preserved_via_R7E_authority"
            ]
            is True,
        )

        gate(
            "A6E_final_freeze_authorized",
            a6e_decision[
                "AV3_final_outcome_freeze_authorized"
            ]
            is True
            and a6e_decision[
                "next"
            ][
                "milestone"
            ]
            == MILESTONE,
        )

        # ------------------------------------------------------------------------------------------
        # Freeze exact realization/domain registry.
        # ------------------------------------------------------------------------------------------
        stage = "realization_domain_freeze"

        a6e_manifest = verify_manifest(
            drive
            / MILESTONES[
                "A6E"
            ][
                0
            ],
            MILESTONES[
                "A6E"
            ][
                2
            ],
        )

        frozen_registry = []

        gate(
            "A6E_realization_summary_4",
            len(
                realization_rows
            )
            == 4,
            len(
                realization_rows
            ),
        )

        for row in realization_rows:

            rid = str(
                row[
                    "corey_realization_id"
                ]
            )

            gate(
                f"{rid}_known_domain",
                rid
                in EXPECTED_DOMAINS,
                rid,
            )

            s0 = int(
                float(
                    row[
                        "S0_cells"
                    ]
                )
            )
            h1 = int(
                float(
                    row[
                        "H1_cells"
                    ]
                )
            )
            d1 = int(
                float(
                    row[
                        "D1_cells"
                    ]
                )
            )

            gate(
                f"{rid}_domain_exact",
                (
                    s0,
                    h1,
                    d1,
                )
                == EXPECTED_DOMAINS[
                    rid
                ],
                [
                    s0,
                    h1,
                    d1,
                ],
            )

            gate(
                f"{rid}_all9_pass",
                true_value(
                    row[
                        "all_9_times_passed"
                    ]
                ),
            )

            state_file = (
                f"POSTV16_AV3_A6_E_{rid}_Integrated_State.npz"
            )

            gate(
                f"{rid}_integrated_state_manifested",
                state_file
                in a6e_manifest,
                state_file,
            )

            frozen_registry.append(
                {
                    "corey_realization_id":
                        rid,

                    "paired_porosity_realization_id":
                        row[
                            "paired_porosity_realization_id"
                        ],

                    "partition":
                        row[
                            "partition"
                        ],

                    "porosity_min":
                        float(
                            row[
                                "porosity_min"
                            ]
                        ),

                    "porosity_max":
                        float(
                            row[
                                "porosity_max"
                            ]
                        ),

                    "porosity_mean":
                        float(
                            row[
                                "porosity_mean"
                            ]
                        ),

                    "porosity_std":
                        float(
                            row[
                                "porosity_std"
                            ]
                        ),

                    "nw_min":
                        float(
                            row[
                                "nw_min"
                            ]
                        ),

                    "nw_max":
                        float(
                            row[
                                "nw_max"
                            ]
                        ),

                    "no_min":
                        float(
                            row[
                                "no_min"
                            ]
                        ),

                    "no_max":
                        float(
                            row[
                                "no_max"
                            ]
                        ),

                    "krw_max_field_min":
                        float(
                            row[
                                "krw_max_field_min"
                            ]
                        ),

                    "krw_max_field_max":
                        float(
                            row[
                                "krw_max_field_max"
                            ]
                        ),

                    "kro_max_field_min":
                        float(
                            row[
                                "kro_max_field_min"
                            ]
                        ),

                    "kro_max_field_max":
                        float(
                            row[
                                "kro_max_field_max"
                            ]
                        ),

                    "S0_cells":
                        s0,

                    "H1_cells":
                        h1,

                    "D1_cells":
                        d1,

                    "integrated_state_file":
                        state_file,

                    "integrated_state_sha256":
                        a6e_manifest[
                            state_file
                        ],

                    "all_9_times_passed":
                        True,
                }
            )

        # ------------------------------------------------------------------------------------------
        # Final AV3 scientific claims and bounded scope.
        # ------------------------------------------------------------------------------------------
        stage = "final_freeze_publish"

        scientific_claims = {
            "milestone":
                MILESTONE,

            "protocol_id":
                PROTOCOL_ID,

            "frozen_claims": [
                {
                    "id":
                        "AV3_CLAIM_1_SPATIAL_CONSTITUTIVE_FIELDS",

                    "claim":
                        (
                            "AV3 extends the completed AV2 variable-porosity base with "
                            "prospectively frozen spatial heterogeneity in Corey exponents "
                            "nw/no and relative-permeability endpoints krw_max/kro_max, paired "
                            "one-to-one with the four frozen AV2 porosity realizations."
                        ),

                    "realizations":
                        frozen_registry,
                },
                {
                    "id":
                        "AV3_CLAIM_2_FLOW_KINEMATICS_HELD_FROZEN",

                    "claim":
                        (
                            "Within AV3, pressure, Darcy volumetric fluxes, Pollock paths, "
                            "and TOF are inherited from the paired AV2 realization and are "
                            "not recomputed from saturation-dependent total-mobility feedback. "
                            "That missing coupling is the explicit subject of AV4."
                        ),
                },
                {
                    "id":
                        "AV3_CLAIM_3_13CHANNEL_PIRNN",

                    "claim":
                        (
                            "The final AV3 transport surrogate is the frozen epoch-92 "
                            "53,057-parameter 13-channel PI-RNN checkpoint."
                        ),

                    "checkpoint_sha256":
                        CHECKPOINT_SHA,

                    "best_epoch":
                        BEST_EPOCH,

                    "epochs_completed":
                        EPOCHS_COMPLETED,

                    "best_validation_total_objective":
                        BEST_VALIDATION_TOTAL,
                },
                {
                    "id":
                        "AV3_CLAIM_4_SINGLE_LOCKED_OOD_EVIDENCE",

                    "claim":
                        (
                            "The frozen checkpoint was evaluated once on prospectively locked "
                            "AV3CR0004 after checkpoint freeze. Validation and locked-OOD errors "
                            "were similar in this single test, with no retraining, checkpoint "
                            "reselection, normalization refit, retuning, or second OOD exposure."
                        ),

                    "validation_RMSE":
                        EXPECTED_VALIDATION_RMSE,

                    "validation_MAE":
                        EXPECTED_VALIDATION_MAE,

                    "locked_OOD_RMSE":
                        EXPECTED_OOD_RMSE,

                    "locked_OOD_MAE":
                        EXPECTED_OOD_MAE,

                    "OOD_to_validation_RMSE_ratio":
                        EXPECTED_OOD_VAL_RMSE_RATIO,

                    "OOD_to_validation_MAE_ratio":
                        EXPECTED_OOD_VAL_MAE_RATIO,

                    "locked_OOD_physics_residual_MSE":
                        EXPECTED_OOD_PHYSICS_RESIDUAL_MSE,

                    "arbitrary_generalization_claim":
                        False,
                },
                {
                    "id":
                        "AV3_CLAIM_5_END_TO_END_INTEGRATION",

                    "claim":
                        (
                            "All four frozen AV3 spatial-Corey/relative-permeability realizations "
                            "were integrated at all nine canonical times through the exact B1 "
                            "component-mass bridge, SG7D/E37A S0 deposition, frozen R7D one-ring "
                            "horizontal terminal-occupancy halo, paired-porosity local pore-volume "
                            "capacity, and frozen R2 EOS inversion."
                        ),

                    "integrated_states":
                        36,

                    "max_B1_projection_relative_closure":
                        EXPECTED_A6E_MAX_B1,

                    "max_total_mass_relative_closure":
                        EXPECTED_A6E_MAX_MASS,

                    "max_localPV_EOS_relative_closure":
                        EXPECTED_A6E_MAX_EOS,

                    "max_post_reconciliation_capacity_excess_kg":
                        EXPECTED_A6E_MAX_CAPACITY_EXCESS_KG,

                    "max_H1_capacity_fraction_used":
                        EXPECTED_A6E_MAX_H1_CAPACITY_FRACTION,

                    "max_H1_occupied_cell_count":
                        EXPECTED_A6E_MAX_H1_OCCUPIED,
                },
                {
                    "id":
                        "AV3_CLAIM_6_IMMUTABLE_FAILURE_HISTORY",

                    "claim":
                        (
                            "The original AV3-A4 teacher-certification result remains an "
                            "immutable scientific FAIL and the original AV3-A5 pre-OOD result "
                            "remains an immutable technical BLOCK. Their later closure milestones "
                            "do not relabel those historical outcomes."
                        ),
                },
            ],

            "explicitly_not_claimed": [
                "generalization to arbitrary spatial Corey/relative-permeability fields",
                "saturation-dependent total-mobility feedback on pressure or Darcy flux",
                "dynamic pressure refresh accuracy",
                "dynamic Pollock-path or TOF feedback accuracy",
                "external full-physics or CMG agreement",
                "AV4 pressure-refresh/dynamic-flow performance",
                "AV5 final integrated GPU performance",
                "IBDP transferability",
                "plume-fidelity superiority over full-physics simulation",
            ],
        }

        immutable_history = {
            "AV3_A2_initial_preexecution_revision":
                {
                    "result":
                        "SUPERSEDED_UNEXECUTED_REVISION",

                    "commit":
                        "d2f12c96508d6d69f94a6b658a83a623f392f3c5",

                    "classification":
                        "NOT_FAIL_NOT_BLOCK",

                    "reason":
                        "cell-centered sampling-origin defect found before formal execution",
                },

            "AV3_A4":
                {
                    "result":
                        "SCIENTIFIC_FAIL",

                    "status":
                        A4_FAIL_STATUS,

                    "failure_report_sha256":
                        A4_FAIL_SHA256,

                    "failed_stage":
                        a4_fail[
                            "failed_stage"
                        ],

                    "failed_gate":
                        a4_fail[
                            "failed_gate"
                        ],

                    "teacher_realizations_completed":
                        int(
                            a4_fail[
                                "teacher_realizations_completed"
                            ]
                        ),

                    "reclassified":
                        False,
                },

            "AV3_A4_R1":
                {
                    "result":
                        "PASS",

                    "closure":
                        (
                            "Three morphology quantities were reclassified as report-only "
                            "because they are not universal invariants of the frozen spatially "
                            "heterogeneous constitutive PDE. Teacher physics was unchanged."
                        ),

                    "original_A4_FAIL_preserved":
                        True,
                },

            "AV3_A4_R2":
                {
                    "result":
                        "PASS",

                    "note":
                        (
                            "Corrected hard-gate teacher certification and 13-channel dataset "
                            "assembly completed. The subsequent external audit-wrapper float32/"
                            "float64 precision-order assertion was an audit-wrapper defect only "
                            "and did not alter the R2 scientific PASS."
                        ),
                },

            "AV3_A5":
                {
                    "result":
                        "TECHNICAL_BLOCK",

                    "status":
                        A5_BLOCK_STATUS,

                    "block_report_sha256":
                        sha256_file(
                            a5_block_path
                        ),

                    "failed_stage":
                        a5_block[
                            "failed_stage"
                        ],

                    "exception":
                        a5_block[
                            "exception"
                        ],

                    "checkpoint_frozen":
                        True,

                    "OOD_opened":
                        False,

                    "reclassified":
                        False,
                },

            "AV3_A5_R1":
                {
                    "result":
                        "PASS",

                    "root_cause":
                        a5r1[
                            "technical_root_cause"
                        ],

                    "original_A5_BLOCK_preserved":
                        True,

                    "OOD_access":
                        False,
                },

            "AV3_A5_R2":
                {
                    "result":
                        "PASS",

                    "locked_OOD_teacher_generated_once":
                        True,

                    "locked_OOD_evaluated_once":
                        True,

                    "second_OOD_authorized":
                        False,
                },

            "AV3_A6":
                {
                    "result":
                        "PASS",

                    "role":
                        "prospective deployment/integration contract freeze only",
                },

            "AV3_A6_E":
                {
                    "result":
                        "PASS",

                    "integrated_states":
                        36,

                    "runner_gates_PASS":
                        464,

                    "manifest_entries_SHA_exact":
                        9,
                },

            "history_rule":
                (
                    "Original FAIL/BLOCK outcomes remain immutable historical results; "
                    "closure milestones do not relabel them."
                ),
        }

        checkpoint_ood = {
            "checkpoint_sha256":
                CHECKPOINT_SHA,

            "best_epoch":
                BEST_EPOCH,

            "epochs_completed":
                EPOCHS_COMPLETED,

            "best_validation_total_objective":
                BEST_VALIDATION_TOTAL,

            "validation_metrics":
                validation_metrics,

            "locked_OOD_metrics":
                ood_metrics,

            "OOD_to_validation_RMSE_ratio":
                a5r2[
                    "OOD_to_validation_RMSE_ratio"
                ],

            "OOD_to_validation_MAE_ratio":
                a5r2[
                    "OOD_to_validation_MAE_ratio"
                ],

            "locked_OOD_physics_residual_MSE":
                a5r2[
                    "locked_OOD_physics_residual_MSE"
                ],

            "locked_OOD_teacher_generated_once":
                True,

            "locked_OOD_evaluated_once":
                True,

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
        }

        av4_handoff = {
            "from":
                MILESTONE,

            "AV3_complete":
                True,

            "AV3_scientific_outcome_frozen":
                True,

            "AV3_external_CMG_validation_complete":
                False,

            "CMG_remains_deferred":
                True,

            "AV3_checkpoint_sha256":
                CHECKPOINT_SHA,

            "AV3_checkpoint_best_epoch":
                BEST_EPOCH,

            "AV3_spatial_Corey_relperm_architecture_frozen":
                True,

            "AV4_authorized":
                True,

            "next": {
                "milestone":
                    "POSTV16-AV4-A0",

                "name":
                    (
                        "Dynamic Pressure-Refresh / Saturation-Dependent Mobility-Feedback "
                        "Authority-Gap and Physics-Impact Freeze"
                    ),

                "authorized":
                    True,

                "execution":
                    False,
            },

            "AV4_initial_scope": {
                "new_physics_axis":
                    (
                        "Introduce and prospectively define pressure/Darcy-flow refresh driven "
                        "by evolving saturation-dependent total mobility, and determine how that "
                        "feedback propagates into Pollock paths, TOF coordinates, transport "
                        "conditioning, and recurrent PAD-Stream state updates."
                    ),

                "AV3_checkpoint_may_be_assumed_authoritative_for_AV4":
                    False,

                "reason":
                    (
                        "AV4 changes the coupling between transport state and flow/kinematics. "
                        "AV3 deliberately held pressure/Q/Pollock/TOF frozen, so a new authority-gap "
                        "and physics-impact freeze is required before reusing or extending the AV3 "
                        "transport checkpoint under dynamic-flow feedback."
                    ),

                "external_CMG_may_guide_AV4_design":
                    False,
            },
        }

        ledger = {
            "repository_parent_A6E_commit":
                PARENT_A6E_COMMIT,

            "checkpoint_sha256":
                CHECKPOINT_SHA,

            "source_git_blobs":
                SOURCE_BLOBS,

            "bound_manifests":
                bound_manifests,

            "AV3_A4_failure_report_sha256":
                A4_FAIL_SHA256,

            "AV3_A5_block_report_sha256":
                sha256_file(
                    a5_block_path
                ),

            "A6E_integrated_state_SHA256": {
                row[
                    "corey_realization_id"
                ]:
                    row[
                        "integrated_state_sha256"
                    ]
                for row in frozen_registry
            },
        }

        decision = {
            "milestone":
                MILESTONE,

            "status":
                STATUS_PASS,

            "protocol_id":
                PROTOCOL_ID,

            "AV3_scientific_outcome_frozen":
                True,

            "AV3_internal_system_development_complete":
                True,

            "AV3_external_validation_complete":
                False,

            "checkpoint_sha256":
                CHECKPOINT_SHA,

            "checkpoint_best_epoch":
                BEST_EPOCH,

            "spatial_Corey_relperm_realizations_frozen":
                4,

            "canonical_times_frozen":
                9,

            "integrated_states_frozen":
                36,

            "single_locked_OOD_evidence_frozen":
                True,

            "A6E_conservative_integration_frozen":
                True,

            "original_A4_scientific_FAIL_preserved":
                True,

            "original_A5_technical_BLOCK_preserved":
                True,

            "training_performed":
                False,

            "inference_performed":
                False,

            "OOD_truth_accessed":
                False,

            "OOD_metrics_recomputed":
                False,

            "LP_execution_performed":
                False,

            "mapback_execution_performed":
                False,

            "pressure_Q_recomputed":
                False,

            "Pollock_TOF_recomputed":
                False,

            "CMG_validation_performed":
                False,

            "AV4_A0_authorized":
                True,

            "next":
                av4_handoff[
                    "next"
                ],
        }

        summary = {
            "milestone":
                MILESTONE,

            "status":
                STATUS_PASS,

            "protocol_id":
                PROTOCOL_ID,

            "checkpoint_sha256":
                CHECKPOINT_SHA,

            "checkpoint_best_epoch":
                BEST_EPOCH,

            "AV3_realizations":
                4,

            "canonical_times":
                9,

            "frozen_integrated_states":
                36,

            "A6E_runner_gate_count":
                464,

            "A6E_manifest_entry_count":
                9,

            "validation_RMSE":
                EXPECTED_VALIDATION_RMSE,

            "locked_OOD_RMSE":
                EXPECTED_OOD_RMSE,

            "OOD_to_validation_RMSE_ratio":
                EXPECTED_OOD_VAL_RMSE_RATIO,

            "max_B1_projection_relative_closure":
                EXPECTED_A6E_MAX_B1,

            "max_mass_relative_closure":
                EXPECTED_A6E_MAX_MASS,

            "max_localPV_EOS_relative_closure":
                EXPECTED_A6E_MAX_EOS,

            "max_post_reconciliation_capacity_excess_kg":
                EXPECTED_A6E_MAX_CAPACITY_EXCESS_KG,

            "max_H1_capacity_fraction_used":
                EXPECTED_A6E_MAX_H1_CAPACITY_FRACTION,

            "max_H1_occupied_cell_count":
                EXPECTED_A6E_MAX_H1_OCCUPIED,

            "original_A4_result":
                "SCIENTIFIC_FAIL",

            "original_A5_result":
                "TECHNICAL_BLOCK",

            "AV3_external_CMG_validation":
                False,

            "AV4_A0_authorized":
                True,

            "next":
                av4_handoff[
                    "next"
                ],
        }

        artifacts = {
            "PAD_Stream_POSTV16_AV3_F_Summary.json":
                json_bytes(
                    summary
                ),

            "POSTV16_AV3_F_Frozen_Scientific_Claims.json":
                json_bytes(
                    scientific_claims
                ),

            "POSTV16_AV3_F_Frozen_Realization_Domain_and_Integration_Registry.csv":
                csv_bytes(
                    frozen_registry
                ),

            "POSTV16_AV3_F_Immutable_Failure_Block_and_Closure_History.json":
                json_bytes(
                    immutable_history
                ),

            "POSTV16_AV3_F_Frozen_Checkpoint_and_Locked_OOD_Evidence.json":
                json_bytes(
                    checkpoint_ood
                ),

            "POSTV16_AV3_F_AV4_Handoff_Contract.json":
                json_bytes(
                    av4_handoff
                ),

            "POSTV16_AV3_F_Source_and_Artifact_Authority_Ledger.json":
                json_bytes(
                    ledger
                ),

            "POSTV16_AV3_F_Decision_Contract.json":
                json_bytes(
                    decision
                ),

            "POSTV16_AV3_F_Final_Gate_Matrix.csv":
                csv_bytes(
                    [
                        {
                            "gate":
                                key,
                            **value,
                        }
                        for key, value in gates.items()
                    ]
                ),
        }

        immutable_publish(
            out,
            artifacts,
        )

        manifest_rows = []

        for q in sorted(
            out.iterdir()
        ):

            if (
                q.is_file()
                and q.name
                != "POSTV16_AV3_F_Artifact_Manifest.csv"
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
                "POSTV16_AV3_F_Artifact_Manifest.csv":
                    csv_bytes(
                        manifest_rows
                    )
            },
        )

        print()
        print("=" * 214)
        print("POSTV16-AV3-F: FINAL SCIENTIFIC OUTCOME FREEZE PASS")
        print("=" * 214)
        print("Original AV3-A4 result                  : SCIENTIFIC FAIL (preserved)")
        print("AV3-A4-R1 / A4-R2                       : PASS / PASS")
        print("Original AV3-A5 result                  : TECHNICAL BLOCK (preserved)")
        print("AV3-A5-R1 / A5-R2                       : PASS / PASS")
        print("Frozen checkpoint                       : epoch 92")
        print("Checkpoint SHA256                       :", CHECKPOINT_SHA)
        print("Validation RMSE                         :", EXPECTED_VALIDATION_RMSE)
        print("Locked-OOD RMSE                         :", EXPECTED_OOD_RMSE)
        print("OOD / validation RMSE ratio             :", EXPECTED_OOD_VAL_RMSE_RATIO)
        print("A6-E integrated states                  : 36 / 36")
        print("A6-E gates / manifested artifacts       : 464 PASS / 9 SHA-exact")
        print("AV3 scientific outcome                  : FROZEN")
        print("CMG validation                          : Deferred")
        print("POSTV16-AV4-A0                          : AUTHORIZED")
        print("AV4 execution                           : NOT YET AUTHORIZED")
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

            "original_A4_scientific_FAIL_reclassified":
                False,

            "original_A5_technical_BLOCK_reclassified":
                False,

            "training_performed":
                False,

            "inference_performed":
                False,

            "OOD_truth_accessed":
                False,

            "OOD_metrics_recomputed":
                False,

            "LP_execution_performed":
                False,

            "mapback_execution_performed":
                False,

            "CMG_validation_performed":
                False,

            "AV3_outcome_frozen":
                False,

            "AV4_A0_authorized":
                False,
        }

        p = (
            blocked
            / "POSTV16_AV3_F_Blocked_Report.json"
        )

        if not p.exists():
            p.write_bytes(
                json_bytes(
                    report
                )
            )

        print()
        print("POSTV16-AV3-F: BLOCKED")
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
