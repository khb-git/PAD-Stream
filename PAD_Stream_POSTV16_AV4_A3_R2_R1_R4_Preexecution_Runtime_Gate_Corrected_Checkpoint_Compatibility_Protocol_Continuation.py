#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import numpy as np


MILESTONE = "POSTV16-AV4-A3-R2-R1-R4"

PROTOCOL_ID = (
    "POSTV16_AV4_A3_R2_R1_R4_PREEXECUTION_RUNTIME_GATE_CORRECTED_"
    "REFRESHED_13CHANNEL_RECONSTRUCTION_CHECKPOINT_RESTART_COMPATIBILITY_"
    "AND_TEACHER_BACKED_AUTHORITY_FREEZE_V1"
)

STATUS_PASS = (
    "AV4A3R2R1R4_PREEXECUTION_RUNTIME_GATE_CORRECTED_"
    "REFRESHED_13CHANNEL_RECONSTRUCTION_INPUT_DOMAIN_RESTART_SEMANTICS_"
    "AND_TEACHER_BACKED_CHECKPOINT_COMPATIBILITY_PROTOCOL_FROZEN_"
    "NO_INFERENCE_NO_TRANSPORT"
)

STATUS_BLOCKED = "AV4A3R2R1R4_PROTOCOL_CONTINUATION_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

PARENT_A3R2R1R3_COMMIT = "f4c1635d85e52ddd39c3bf9adcb311f9a4a4fbb1"

CONTROL_REALIZATION = "AV3CR0003"
CONTROL_POROSITY = "AV2PHI0003"
CONTROL_PARTITION = "VALIDATION"
CONTROL_DAY = 365.0

GRID = (15, 50, 50)
NSL = 1078
NN = 201
NCV = 200

DX_M = 6.096
DY_M = 6.096
DZ_M = 1.2192
ORIGIN_CENTER_M = np.asarray(
    [DX_M / 2.0, DY_M / 2.0, DZ_M / 2.0],
    dtype=np.float64,
)

DAYS = np.asarray(
    [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0],
    dtype=np.float64,
)

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

FIRST9 = CHANNELS13[:9]
NEW4 = CHANNELS13[9:]

MODEL_PARAMETERS = 53057
EXPECTED_CHECKPOINT_SHA256 = (
    "17b188494e0452570d43e868c20c4c814e6a1f0b493329d0e40849c4c5ec6d4e"
)
EXPECTED_BEST_EPOCH = 92
EXPECTED_EPOCHS_COMPLETED = 122

# --------------------------------------------------------------------------------------------------
# Exact repository authorities.
# --------------------------------------------------------------------------------------------------

A3R2R1R3_PREEXECUTION = (
    "PAD_Stream_POSTV16_AV4_A3_R2_R1_R3_Preexecution_Display_Normalized_"
    "Checkpoint_Compatibility_Protocol_Continuation.py"
)
A3R2R1R3_PREEXECUTION_BLOB = "a374f2465aed7cc715098d844272fe89049c533c"

A3R2R1R2_PREEXECUTION = (
    "PAD_Stream_POSTV16_AV4_A3_R2_R1_R2_Preexecution_Provenance_Normalized_"
    "Checkpoint_Compatibility_Protocol_Continuation.py"
)
A3R2R1R2_PREEXECUTION_BLOB = "feb6b13c85429a5cbee4ee38574e5178742c8563"

A3R2R1R1_PREEXECUTION = (
    "PAD_Stream_POSTV16_AV4_A3_R2_R1_R1_Preexecution_Import_Corrected_"
    "Checkpoint_Compatibility_Protocol_Continuation.py"
)
A3R2R1R1_PREEXECUTION_BLOB = "2f98773eab2d6324d3649ffdcc5f3d4ee8184876"

A3R2R1_PREEXECUTION = (
    "PAD_Stream_POSTV16_AV4_A3_R2_R1_Preexecution_Namespace_Corrected_"
    "Checkpoint_Compatibility_Protocol_Continuation.py"
)
A3R2R1_PREEXECUTION_BLOB = "52cd572a1bdd2e543a8fd50b07a925ff37d4f553"

A3R2_PREEXECUTION = (
    "PAD_Stream_POSTV16_AV4_A3_R2_Corrected_Refreshed_13Channel_"
    "Checkpoint_Compatibility_Protocol_Continuation.py"
)
A3R2_PREEXECUTION_BLOB = "451392eb5b4424914d38a1843262fb92ff9599c4"

A3_ORIGINAL = (
    "PAD_Stream_POSTV16_AV4_A3_"
    "Refreshed_13Channel_Checkpoint_Compatibility_Protocol_Freeze.py"
)
A3_ORIGINAL_BLOB = "4ca86c76d29a628ce010661e85663e7e4fa3b34a"

AV4A3R1 = "PAD_Stream_POSTV16_AV4_A3_R1_Technical_Authority_Schema_Block_Closure.py"
AV4A3R1_BLOB = "a673d7dc0f10a2a93c48cd09878a67956a091f4e"

A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"

A6E = "PAD_Stream_POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution.py"
A6E_BLOB = "e3dcb0aa9354c399904f7f0e830b6a1fddd78987"

A5R2 = "PAD_Stream_POSTV16_AV3_A5_R2_Frozen_Checkpoint_OneTouch_OOD_Continuation.py"
A5R2_BLOB = "b2dd3fb27966a51e6a6057e444dfdb617976b36f"

A4R2 = (
    "PAD_Stream_POSTV16_AV3_A4_R2_"
    "Corrected_Certification_Teacher_Dataset_and_LockedOOD_Predictor.py"
)
A4R2_BLOB = "289901331e835afb44ff2f665fe9a6bbea2eac19"

AV3A3R1 = (
    "PAD_Stream_POSTV16_AV3_A3_R1_"
    "First9_CellCentered_Geometry_and_Normalization_Authority_Correction.py"
)
AV3A3R1_BLOB = "2a70ef6b67ddefee61b5a9ab2fb080755fdb4b49"

AV3A3 = "PAD_Stream_POSTV16_AV3_A3_Transport_Teacher_Residual_and_PIRNN_Protocol_Freeze.py"
AV3A3_BLOB = "40fe89c142e62aad750a749f0a8ae452574f28bd"

B3 = "PAD_Stream_V16B3_Independent_FMM_Pollock_TOF_Comparison.py"
B3_BLOB = "1f04056d039d698707991646f086f5dc320a04ca"

C2 = "PAD_Stream_V16C2_Multi_Coordinate_Streamline_Transport_Database_Assembly.py"
C2_BLOB = "21ff44de456102772c99f7ddc80898c9139a76db"

PERM = "SGSIM_50x50x15_PERM_MD.csv"
PERM_BLOB = "317dd47d458bc6f880c2e3dc4ec1f69eeb0dd314"

SOURCE_BLOBS = {
    A3R2R1R3_PREEXECUTION: A3R2R1R3_PREEXECUTION_BLOB,
    A3R2R1R2_PREEXECUTION: A3R2R1R2_PREEXECUTION_BLOB,
    A3R2R1R1_PREEXECUTION: A3R2R1R1_PREEXECUTION_BLOB,
    A3R2R1_PREEXECUTION: A3R2R1_PREEXECUTION_BLOB,
    A3R2_PREEXECUTION: A3R2_PREEXECUTION_BLOB,
    A3_ORIGINAL: A3_ORIGINAL_BLOB,
    AV4A3R1: AV4A3R1_BLOB,
    A2E: A2E_BLOB,
    A6E: A6E_BLOB,
    A5R2: A5R2_BLOB,
    A4R2: A4R2_BLOB,
    AV3A3R1: AV3A3R1_BLOB,
    AV3A3: AV3A3_BLOB,
    B3: B3_BLOB,
    C2: C2_BLOB,
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

AV4A3R1_REL = (
    BASE_AV4
    / "POSTV16_AV4_A3_R1_Technical_Authority_Schema_Block_Closure"
)
AV4A3R1_SUMMARY = "PAD_Stream_POSTV16_AV4_A3_R1_Summary.json"
AV4A3R1_DECISION = "POSTV16_AV4_A3_R1_Decision_Contract.json"
AV4A3R1_CORRECTED = "POSTV16_AV4_A3_R1_Corrected_A2E_Authority_Read_Contract.json"
AV4A3R1_HANDOFF = "POSTV16_AV4_A3_R1_A3R2_Handoff_Contract.json"
AV4A3R1_MANIFEST = "POSTV16_AV4_A3_R1_Artifact_Manifest.csv"

AV4A3R1_STATUS = (
    "AV4A3R1_ORIGINAL_A3_TECHNICAL_BLOCK_PRESERVED_"
    "A2E_SUMMARY_VS_DECISION_AUTHORITY_SCHEMA_ROOT_CAUSE_CLOSED_"
    "CORRECTED_A3R2_CONTINUATION_PROSPECTIVELY_FROZEN_NO_A3_SCIENTIFIC_EXECUTION"
)

ORIGINAL_A3_BLOCK_REL = BASE_AV4 / "POSTV16_AV4_A3_BLOCKED"
ORIGINAL_A3_BLOCK = "POSTV16_AV4_A3_Blocked_Report.json"
ORIGINAL_A3_BLOCK_STATUS = "AV4A3_PROTOCOL_FREEZE_BLOCKED"

A3R2_PREEXECUTION_PASS_REL = (
    BASE_AV4
    / "POSTV16_AV4_A3_R2_Corrected_Refreshed_13Channel_Checkpoint_Compatibility_Protocol_Freeze"
)
A3R2_PREEXECUTION_PASS_SUMMARY = "PAD_Stream_POSTV16_AV4_A3_R2_Summary.json"
A3R2_PREEXECUTION_BLOCK_REL = BASE_AV4 / "POSTV16_AV4_A3_R2_BLOCKED"
A3R2_PREEXECUTION_BLOCK_REPORT = "POSTV16_AV4_A3_R2_Blocked_Report.json"

A3R2R1_PREEXECUTION_PASS_REL = (
    BASE_AV4
    / "POSTV16_AV4_A3_R2_R1_Preexecution_Namespace_Corrected_Protocol_Continuation"
)
A3R2R1_PREEXECUTION_PASS_SUMMARY = "PAD_Stream_POSTV16_AV4_A3_R2_R1_Summary.json"
A3R2R1_PREEXECUTION_BLOCK_REL = BASE_AV4 / "POSTV16_AV4_A3_R2_R1_BLOCKED"
A3R2R1_PREEXECUTION_BLOCK_REPORT = "POSTV16_AV4_A3_R2_R1_Blocked_Report.json"

A3R2R1R1_PREEXECUTION_PASS_REL = (
    BASE_AV4
    / "POSTV16_AV4_A3_R2_R1_R1_R1_Preexecution_Import_Corrected_Protocol_Continuation"
)
A3R2R1R1_PREEXECUTION_PASS_SUMMARY = "PAD_Stream_POSTV16_AV4_A3_R2_R1_R1_Summary.json"
A3R2R1R1_PREEXECUTION_BLOCK_REL = BASE_AV4 / "POSTV16_AV4_A3_R2_R1_R1_R1_BLOCKED"
A3R2R1R1_PREEXECUTION_BLOCK_REPORT = "POSTV16_AV4_A3_R2_R1_R1_Blocked_Report.json"

A3R2R1R2_PREEXECUTION_PASS_REL = (
    BASE_AV4
    / "POSTV16_AV4_A3_R2_R1_R2_Preexecution_Provenance_Normalized_Protocol_Continuation"
)
A3R2R1R2_PREEXECUTION_PASS_SUMMARY = "PAD_Stream_POSTV16_AV4_A3_R2_R1_R2_Summary.json"
A3R2R1R2_PREEXECUTION_BLOCK_REL = BASE_AV4 / "POSTV16_AV4_A3_R2_R1_R2_BLOCKED"
A3R2R1R2_PREEXECUTION_BLOCK_REPORT = "POSTV16_AV4_A3_R2_R1_R2_Blocked_Report.json"

A3R2R1R3_PREEXECUTION_PASS_REL = (
    BASE_AV4
    / "POSTV16_AV4_A3_R2_R1_R3_Preexecution_Display_Normalized_Protocol_Continuation"
)
A3R2R1R3_PREEXECUTION_PASS_SUMMARY = "PAD_Stream_POSTV16_AV4_A3_R2_R1_R3_Summary.json"
A3R2R1R3_PREEXECUTION_BLOCK_REL = BASE_AV4 / "POSTV16_AV4_A3_R2_R1_R3_BLOCKED"
A3R2R1R3_PREEXECUTION_BLOCK_REPORT = "POSTV16_AV4_A3_R2_R1_R3_Blocked_Report.json"

A2E_REL = (
    BASE_AV4
    / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
)

A2E_SUMMARY = "PAD_Stream_POSTV16_AV4_A2_E_Summary.json"
A2E_DECISION = "POSTV16_AV4_A2_E_Decision_Contract.json"
A2E_EPOCH = "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_STATE_DIFF = "POSTV16_AV4_A2_E_Parent_vs_Refreshed_State_Differences.json"
A2E_MANIFEST = "POSTV16_AV4_A2_E_Artifact_Manifest.csv"

A2E_STATUS = (
    "AV4A2E_AV3CR0003_DAY365_SAME_TIME_SPATIAL_MOBILITY_PRESSURE_SATURATION_"
    "REFRESH_DARCY_POLLOCK_TOF_GEOMETRY_EXECUTION_PASS"
)

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
A6E_STATUS = (
    "AV3A6E_FROZEN_EPOCH92_CHECKPOINT_LOCAL_PORE_VOLUME_R7D_TERMINAL_HALO_"
    "INTEGRATION_ALL_4_REALIZATIONS_ALL_9_TIMES_PASS"
)

A5R2_REL = (
    BASE_AV3
    / "POSTV16_AV3_A5_R2_Frozen_Checkpoint_OneTouch_OOD_Continuation"
)
A5R2_SUMMARY = "PAD_Stream_POSTV16_AV3_A5_R2_Summary.json"
A5R2_DECISION = "POSTV16_AV3_A5_R2_Decision_Contract.json"
A5R2_MANIFEST = "POSTV16_AV3_A5_R2_Artifact_Manifest.csv"
A5R2_STATUS = (
    "AV3A5R2_FROZEN_EPOCH92_CHECKPOINT_PRE_OOD_INTEGRITY_CORRECTED_"
    "LOCKED_OOD_TEACHER_GENERATED_ONCE_EVALUATED_ONCE_PASS"
)

A4R2_REL = (
    BASE_AV3
    / "POSTV16_AV3_A4_R2_Corrected_Teacher_Dataset_and_LockedOOD_Predictor"
)
A4R2_TRAINVAL = "POSTV16_AV3_A4_R2_TrainValidation_13Channel_Transport_Dataset.npz"
A4R2_NORM = "POSTV16_AV3_A4_R2_Corrected_TRAIN_Only_Normalization.npz"
A4R2_SIDECAR = "POSTV16_AV3_A4_R2_Spatial_Relperm_Physics_Sidecar.npz"
A4R2_MANIFEST = "POSTV16_AV3_A4_R2_Artifact_Manifest.csv"

AV3A3R1_REL = (
    BASE_AV3
    / "POSTV16_AV3_A3_R1_First9_CellCentered_Geometry_and_Normalization_Authority_Correction"
)
AV3A3R1_SUMMARY = "PAD_Stream_POSTV16_AV3_A3_R1_Summary.json"
AV3A3R1_FIRST9 = "POSTV16_AV3_A3_R1_First9_CellCentered_Channel_Contract.json"
AV3A3R1_NORM = "POSTV16_AV3_A3_R1_Corrected_Normalization_Contract.json"
AV3A3R1_MANIFEST = "POSTV16_AV3_A3_R1_Artifact_Manifest.csv"

AV3A3R1_STATUS = (
    "AV3A3R1_FIRST_NINE_CHANNEL_CELL_CENTERED_GEOMETRY_AND_"
    "TRAIN_NORMALIZATION_AUTHORITY_CORRECTION_FROZEN_NO_A4_EXECUTION"
)

AV3A3_REL = (
    BASE_AV3
    / "POSTV16_AV3_A3_Transport_Teacher_Residual_and_PIRNN_Protocol_Freeze"
)
AV3A3_SUMMARY = "PAD_Stream_POSTV16_AV3_A3_Summary.json"
AV3A3_MODEL = "POSTV16_AV3_A3_13Channel_PIRNN_Training_Protocol.json"
AV3A3_DATASET = "POSTV16_AV3_A3_Teacher_Dataset_and_Leakage_Firewall.json"
AV3A3_RESIDUAL = "POSTV16_AV3_A3_Differentiable_Physics_Residual_Contract.json"
AV3A3_MANIFEST = "POSTV16_AV3_A3_Artifact_Manifest.csv"

AV3A3_STATUS = (
    "AV3A3_SPATIAL_COREY_RELPERM_TRANSPORT_TEACHER_RESIDUAL_AND_"
    "13CHANNEL_PIRNN_PROTOCOL_PROSPECTIVELY_FROZEN_NO_TEACHER_OR_TRAINING_EXECUTION"
)

CHECKPOINT_REL = (
    BASE_AV3
    / "POSTV16_AV3_A5_PIRNN_Training_Checkpoint_and_OneTouch_OOD"
    / "POSTV16_AV3_A5_Best_Validation_Model.keras"
)

OUT_REL = (
    BASE_AV4
    / "POSTV16_AV4_A3_R2_R1_R4_Preexecution_Runtime_Gate_Corrected_Protocol_Continuation"
)

BLOCK_REL = BASE_AV4 / "POSTV16_AV4_A3_R2_R1_R4_BLOCKED"


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


def self_test() -> None:
    assert GRID == (15, 50, 50)
    assert NSL == 1078
    assert NN == 201
    assert NCV == 200
    assert len(CHANNELS13) == 13
    assert CHANNELS13[:9] == FIRST9
    assert CHANNELS13[9:] == NEW4
    assert MODEL_PARAMETERS == 53057
    assert CONTROL_DAY == DAYS[5]
    assert np.array_equal(
        ORIGIN_CENTER_M,
        np.asarray([3.048, 3.048, 0.6096], dtype=np.float64),
    )

    # Fundamental restartability fact: the historical AV3 predictor has no explicit
    # parent saturation / parent mass / previous-state channel.
    forbidden_parent_state_names = {
        "parent_saturation",
        "current_saturation",
        "previous_saturation",
        "parent_component_mass",
        "current_component_mass",
        "previous_state",
    }
    assert forbidden_parent_state_names.isdisjoint(CHANNELS13)

    assert AV4A3R1 != AV3A3R1
    assert AV4A3R1_BLOB != AV3A3R1_BLOB
    assert AV4A3R1_REL != AV3A3R1_REL
    assert AV4A3R1_STATUS != AV3A3R1_STATUS
    assert re.findall(r"^A3R1\s*=", "A3R1 = 1", flags=re.MULTILINE) == ["A3R1 ="]

    milestone_token = MILESTONE.replace("-", "_")
    assert PROTOCOL_ID.startswith(milestone_token + "_")
    assert OUT_REL.name.startswith(milestone_token + "_")
    assert BLOCK_REL.name == milestone_token + "_BLOCKED"
    assert MILESTONE == "POSTV16-AV4-A3-R2-R1-R4"

    print(
        "POSTV16-AV4-A3-R2-R1-R4 preexecution runtime-gate-corrected "
        "checkpoint compatibility protocol self-test: PASS"
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
        "POSTV16-AV4-A3-R2-R1-R4 — PREEXECUTION RUNTIME-GATE-CORRECTED REFRESHED 13-CHANNEL RECONSTRUCTION / "
        "CHECKPOINT RESTART-COMPATIBILITY / TEACHER-BACKED AUTHORITY PROTOCOL FREEZE"
    )
    print("=" * 214)
    print("PREEXECUTION RUNTIME-GATE CORRECTION + DESIGN / FREEZE ONLY.")
    print("NO PI-RNN MODEL LOAD. NO CHECKPOINT INFERENCE.")
    print("NO TEACHER TRANSPORT. NO PHYSICAL-TIME ADVANCE.")
    print("NO MAPBACK / LP. NO CHECKPOINT RETRAINING OR RESELECTION. NO CMG.")
    print("AV3 CHECKPOINT COMMITTED REUSE REMAINS FALSE.")
    print()

    try:
        # ------------------------------------------------------------------------------------------
        # Repository authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"

        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate(
            "repository_parent_is_A3R2R1R3_preexecution_commit",
            parent == PARENT_A3R2R1R3_COMMIT,
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
                git_blob(p, root)
                if p.is_file()
                else "missing"
            )

            gate(
                f"{Path(fn).stem}_git_blob_exact",
                actual == expected,
                actual,
            )

        # ------------------------------------------------------------------------------------------
        # Bind the pushed-but-not-executed R2-R1-R3 runtime-gate/display defects.
        # ------------------------------------------------------------------------------------------
        stage = "A3R2R1R3_preexecution_runtime_gate_defect_binding"

        r2r1r3_source = (root / A3R2R1R3_PREEXECUTION).read_text(
            encoding="utf-8",
            errors="replace",
        )

        gate(
            "R2R1R3_preexecution_source_blob_exact",
            git_blob(root / A3R2R1R3_PREEXECUTION, root) == A3R2R1R3_PREEXECUTION_BLOB,
            git_blob(root / A3R2R1R3_PREEXECUTION, root),
        )

        gate(
            "R2R1R3_preexecution_PASS_banner_stale",
            'print(f"{MILESTONE}: PREEXECUTION RUNTIME-GATE-CORRECTED PROTOCOL FREEZE PASS")'
            in r2r1r3_source,
        )

        gate(
            "R2R1R3_preexecution_BLOCK_banner_stale",
            'print(f"{MILESTONE}: TECHNICAL / AUTHORITY BLOCK")'
            in r2r1r3_source,
        )

        gate(
            "R2R1R3_preexecution_R2R1R2_PASS_detector_incorrect",
            '\'print(f"{MILESTONE}: PREEXECUTION DISPLAY-NORMALIZED PROTOCOL FREEZE PASS")\''
            in r2r1r3_source,
        )

        gate(
            "R2R1R3_preexecution_R2R1R2_BLOCK_detector_incorrect",
            '\'print(f"{MILESTONE}: TECHNICAL / AUTHORITY BLOCK")\''
            in r2r1r3_source,
        )

        gate(
            "R2R1R3_preexecution_no_PASS_output",
            not (
                drive
                / A3R2R1R3_PREEXECUTION_PASS_REL
                / A3R2R1R3_PREEXECUTION_PASS_SUMMARY
            ).exists(),
            str(
                drive
                / A3R2R1R3_PREEXECUTION_PASS_REL
                / A3R2R1R3_PREEXECUTION_PASS_SUMMARY
            ),
        )

        gate(
            "R2R1R3_preexecution_no_BLOCK_report",
            not (
                drive
                / A3R2R1R3_PREEXECUTION_BLOCK_REL
                / A3R2R1R3_PREEXECUTION_BLOCK_REPORT
            ).exists(),
            str(
                drive
                / A3R2R1R3_PREEXECUTION_BLOCK_REL
                / A3R2R1R3_PREEXECUTION_BLOCK_REPORT
            ),
        )

        # ------------------------------------------------------------------------------------------
        # Bind the pushed-but-not-executed R2-R1-R2 display-label defect.
        # ------------------------------------------------------------------------------------------
        stage = "A3R2R1R2_preexecution_display_label_defect_binding"

        r2r1r2_source = (root / A3R2R1R2_PREEXECUTION).read_text(
            encoding="utf-8",
            errors="replace",
        )

        gate(
            "R2R1R2_preexecution_source_blob_exact",
            git_blob(root / A3R2R1R2_PREEXECUTION, root) == A3R2R1R2_PREEXECUTION_BLOB,
            git_blob(root / A3R2R1R2_PREEXECUTION, root),
        )

        gate(
            "R2R1R2_preexecution_PASS_banner_stale",
            'print("POSTV16-AV4-A3-R2-R1-R1: PREEXECUTION IMPORT-CORRECTED PROTOCOL FREEZE PASS")'
            in r2r1r2_source,
        )

        gate(
            "R2R1R2_preexecution_BLOCK_banner_stale",
            'print("POSTV16-AV4-A3-R2-R1-R1: TECHNICAL / AUTHORITY BLOCK")'
            in r2r1r2_source,
        )

        gate(
            "R2R1R2_preexecution_no_PASS_output",
            not (
                drive
                / A3R2R1R2_PREEXECUTION_PASS_REL
                / A3R2R1R2_PREEXECUTION_PASS_SUMMARY
            ).exists(),
            str(
                drive
                / A3R2R1R2_PREEXECUTION_PASS_REL
                / A3R2R1R2_PREEXECUTION_PASS_SUMMARY
            ),
        )

        gate(
            "R2R1R2_preexecution_no_BLOCK_report",
            not (
                drive
                / A3R2R1R2_PREEXECUTION_BLOCK_REL
                / A3R2R1R2_PREEXECUTION_BLOCK_REPORT
            ).exists(),
            str(
                drive
                / A3R2R1R2_PREEXECUTION_BLOCK_REL
                / A3R2R1R2_PREEXECUTION_BLOCK_REPORT
            ),
        )

        # ------------------------------------------------------------------------------------------
        # Bind the pushed-but-not-executed R2-R1-R1 provenance defects.
        # ------------------------------------------------------------------------------------------
        stage = "A3R2R1R1_preexecution_provenance_defect_binding"

        r2r1r1_source = (root / A3R2R1R1_PREEXECUTION).read_text(
            encoding="utf-8",
            errors="replace",
        )

        gate(
            "R2R1R1_preexecution_source_blob_exact",
            git_blob(root / A3R2R1R1_PREEXECUTION, root) == A3R2R1R1_PREEXECUTION_BLOB,
            git_blob(root / A3R2R1R1_PREEXECUTION, root),
        )

        gate(
            "R2R1R1_preexecution_protocol_extra_R1_present",
            "POSTV16_AV4_A3_R2_R1_R1_R1_PREEXECUTION_" in r2r1r1_source,
        )

        gate(
            "R2R1R1_preexecution_output_folder_extra_R1_present",
            "POSTV16_AV4_A3_R2_R1_R1_R1_Preexecution_Import_Corrected_Protocol_Continuation"
            in r2r1r1_source,
        )

        gate(
            "R2R1R1_preexecution_overescaped_import_regex_present",
            r'r"^import\\s+re(?:\\s|$)"' in r2r1r1_source,
        )

        gate(
            "R2R1R1_preexecution_no_PASS_output",
            not (
                drive
                / A3R2R1R1_PREEXECUTION_PASS_REL
                / A3R2R1R1_PREEXECUTION_PASS_SUMMARY
            ).exists(),
            str(
                drive
                / A3R2R1R1_PREEXECUTION_PASS_REL
                / A3R2R1R1_PREEXECUTION_PASS_SUMMARY
            ),
        )

        gate(
            "R2R1R1_preexecution_no_BLOCK_report",
            not (
                drive
                / A3R2R1R1_PREEXECUTION_BLOCK_REL
                / A3R2R1R1_PREEXECUTION_BLOCK_REPORT
            ).exists(),
            str(
                drive
                / A3R2R1R1_PREEXECUTION_BLOCK_REL
                / A3R2R1R1_PREEXECUTION_BLOCK_REPORT
            ),
        )

        # ------------------------------------------------------------------------------------------
        # Bind the pushed-but-not-executed R2-R1 missing-import defect.
        # ------------------------------------------------------------------------------------------
        stage = "A3R2R1_preexecution_missing_import_binding"

        r2r1_source = (root / A3R2R1_PREEXECUTION).read_text(
            encoding="utf-8",
            errors="replace",
        )

        gate(
            "R2R1_preexecution_source_blob_exact",
            git_blob(root / A3R2R1_PREEXECUTION, root) == A3R2R1_PREEXECUTION_BLOB,
            git_blob(root / A3R2R1_PREEXECUTION, root),
        )

        gate(
            "R2R1_preexecution_regex_usage_present",
            "re.findall(" in r2r1_source,
        )

        gate(
            "R2R1_preexecution_re_import_absent",
            not bool(
                re.search(
                    r"^import\s+re(?:\s|$)",
                    r2r1_source,
                    flags=re.MULTILINE,
                )
            ),
        )

        gate(
            "R2R1_preexecution_no_PASS_output",
            not (
                drive
                / A3R2R1_PREEXECUTION_PASS_REL
                / A3R2R1_PREEXECUTION_PASS_SUMMARY
            ).exists(),
            str(
                drive
                / A3R2R1_PREEXECUTION_PASS_REL
                / A3R2R1_PREEXECUTION_PASS_SUMMARY
            ),
        )

        gate(
            "R2R1_preexecution_no_BLOCK_report",
            not (
                drive
                / A3R2R1_PREEXECUTION_BLOCK_REL
                / A3R2R1_PREEXECUTION_BLOCK_REPORT
            ).exists(),
            str(
                drive
                / A3R2R1_PREEXECUTION_BLOCK_REL
                / A3R2R1_PREEXECUTION_BLOCK_REPORT
            ),
        )

        # ------------------------------------------------------------------------------------------
        # Bind the pushed-but-not-executed R2 source defect.
        # ------------------------------------------------------------------------------------------
        stage = "A3R2_preexecution_namespace_defect_binding"

        r2_source = (root / A3R2_PREEXECUTION).read_text(
            encoding="utf-8",
            errors="replace",
        )

        gate(
            "R2_preexecution_source_blob_exact",
            git_blob(root / A3R2_PREEXECUTION, root) == A3R2_PREEXECUTION_BLOB,
            git_blob(root / A3R2_PREEXECUTION, root),
        )

        gate(
            "R2_preexecution_duplicate_A3R1_source_symbol_present",
            len(re.findall(r"^A3R1\s*=", r2_source, flags=re.MULTILINE)) >= 2,
            len(re.findall(r"^A3R1\s*=", r2_source, flags=re.MULTILINE)),
        )

        gate(
            "R2_preexecution_duplicate_A3R1_REL_symbol_present",
            len(re.findall(r"^A3R1_REL\s*=", r2_source, flags=re.MULTILINE)) >= 2,
            len(re.findall(r"^A3R1_REL\s*=", r2_source, flags=re.MULTILINE)),
        )

        gate(
            "R2_preexecution_no_PASS_output",
            not (
                drive
                / A3R2_PREEXECUTION_PASS_REL
                / A3R2_PREEXECUTION_PASS_SUMMARY
            ).exists(),
            str(
                drive
                / A3R2_PREEXECUTION_PASS_REL
                / A3R2_PREEXECUTION_PASS_SUMMARY
            ),
        )

        gate(
            "R2_preexecution_no_BLOCK_report",
            not (
                drive
                / A3R2_PREEXECUTION_BLOCK_REL
                / A3R2_PREEXECUTION_BLOCK_REPORT
            ).exists(),
            str(
                drive
                / A3R2_PREEXECUTION_BLOCK_REL
                / A3R2_PREEXECUTION_BLOCK_REPORT
            ),
        )

        # ------------------------------------------------------------------------------------------
        # Bind successful AV4 A3-R1 closure and preserve the original A3 technical block.
        # ------------------------------------------------------------------------------------------
        stage = "AV4A3R1_closure_binding"

        r1 = drive / AV4A3R1_REL

        gate(
            "AV4_A3R1_output_present",
            r1.is_dir(),
            str(r1),
        )

        mr1 = verify_manifest(
            r1,
            AV4A3R1_MANIFEST,
        )

        gate(
            "AV4_A3R1_manifest_exact_6",
            len(mr1) == 6,
            len(mr1),
        )

        sr1 = load_json(
            r1 / AV4A3R1_SUMMARY
        )

        dr1 = load_json(
            r1 / AV4A3R1_DECISION
        )

        cr1 = load_json(
            r1 / AV4A3R1_CORRECTED
        )

        hr1 = load_json(
            r1 / AV4A3R1_HANDOFF
        )

        gate(
            "AV4_A3R1_status_exact",
            sr1["status"] == AV4A3R1_STATUS,
            sr1["status"],
        )

        gate(
            "AV4_A3R1_root_cause_closed",
            dr1["root_cause_closed"] is True
            and dr1["root_cause_type"]
            == "TECHNICAL_AUTHORITY_SCHEMA_READ_MISMATCH",
        )

        gate(
            "AV4_A3R1_original_A3_block_preserved",
            dr1["original_A3_technical_BLOCK_preserved"] is True
            and dr1["original_A3_scientific_PASS_claimed"] is False,
        )

        gate(
            "AV4_A3R1_corrected_authority_source_exact",
            cr1["field"] == "AV4_dynamic_transport_execution_authorized"
            and cr1["authoritative_source_for_A3R2"] == A2E_SUMMARY
            and cr1["required_value"] is False
            and cr1["normalization_or_physics_change"] is False
            and cr1["checkpoint_change"] is False
            and cr1["transport_change"] is False,
        )

        gate(
            "AV4_A3R1_A3R2_handoff_exact",
            hr1["milestone"] == "POSTV16-AV4-A3-R2"
            and hr1["authorized"] is True
            and hr1["execution"] is True,
            hr1,
        )

        gate(
            "AV4_A3R1_A3E1_still_unauthorized",
            dr1["AV4_A3_E1_authorized"] is False,
        )

        gate(
            "AV4_A3R1_dynamic_transport_still_unauthorized",
            dr1["AV4_dynamic_transport_execution_authorized"] is False,
        )

        original_block_path = drive / ORIGINAL_A3_BLOCK_REL / ORIGINAL_A3_BLOCK

        gate(
            "original_A3_block_report_still_present",
            original_block_path.is_file(),
            str(original_block_path),
        )

        original_block_sha = sha256_file(
            original_block_path
        )

        gate(
            "original_A3_block_SHA_preserved_through_R1",
            original_block_sha == sr1["original_A3_block_SHA256"]
            and original_block_sha == dr1["original_A3_block_SHA256"],
            original_block_sha,
        )

        original_block = load_json(
            original_block_path
        )

        gate(
            "original_A3_block_status_still_exact",
            original_block["status"] == ORIGINAL_A3_BLOCK_STATUS,
            original_block["status"],
        )

        gate(
            "original_A3_block_had_no_scientific_execution",
            original_block["checkpoint_model_loaded"] is False
            and original_block["checkpoint_inference_performed"] is False
            and original_block["teacher_transport_performed"] is False
            and original_block["physical_time_advanced"] is False
            and original_block["training_performed"] is False
            and original_block["normalization_refit"] is False,
        )

        # ------------------------------------------------------------------------------------------
        # Bind exact AV4-A2-E scientific PASS and refreshed-flow epoch.
        # ------------------------------------------------------------------------------------------
        stage = "A2E_authority_binding"

        a2e = drive / A2E_REL

        gate(
            "A2E_output_present",
            a2e.is_dir(),
            str(a2e),
        )

        m2e = verify_manifest(
            a2e,
            A2E_MANIFEST,
        )

        gate(
            "A2E_manifest_exact_12",
            len(m2e) == 12,
            len(m2e),
        )

        gate(
            "A2E_refreshed_epoch_manifested",
            A2E_EPOCH in m2e,
            A2E_EPOCH,
        )

        s2e = load_json(
            a2e / A2E_SUMMARY
        )

        d2e = load_json(
            a2e / A2E_DECISION
        )

        diff2e = load_json(
            a2e / A2E_STATE_DIFF
        )

        gate(
            "A2E_status_exact",
            s2e["status"] == A2E_STATUS,
            s2e["status"],
        )

        gate(
            "A2E_scientific_execution_completed",
            d2e["scientific_execution_completed"] is True
            and d2e["same_time_pressure_saturation_refresh_PASS"] is True,
        )

        gate(
            "A2E_atomic_refreshed_flow_epoch_committed",
            d2e["atomic_refreshed_flow_epoch_committed"] is True,
        )

        gate(
            "A2E_parent_state_immutable",
            d2e["parent_state_modified"] is False,
        )

        gate(
            "A2E_no_PI_RNN_inference",
            d2e["PI_RNN_inference"] is False,
        )

        gate(
            "A2E_no_physical_time_advance",
            d2e["physical_time_advance"] is False,
        )

        gate(
            "A2E_A3_authorized_execution_false",
            d2e["next"]["milestone"] == "POSTV16-AV4-A3"
            and d2e["next"]["authorized"] is True
            and d2e["next"]["execution"] is False,
        )

        gate(
            "A2E_dynamic_transport_still_unauthorized",
            s2e["AV4_dynamic_transport_execution_authorized"] is False,
        )

        gate(
            "A2E_R1_schema_correction_exact",
            "AV4_dynamic_transport_execution_authorized" in s2e
            and "AV4_dynamic_transport_execution_authorized" not in d2e,
        )

        gate(
            "A2E_descriptive_state_shift_present",
            float(diff2e["pressure_relative_L2_change"]) > 0.0
            and float(diff2e["saturation_Linf_change"]) > 0.0,
            {
                "pressure_relative_L2_change":
                    float(diff2e["pressure_relative_L2_change"]),
                "saturation_Linf_change":
                    float(diff2e["saturation_Linf_change"]),
            },
        )

        epoch_path = a2e / A2E_EPOCH

        gate(
            "A2E_epoch_SHA_manifest_exact",
            epoch_path.is_file()
            and sha256_file(epoch_path) == m2e[A2E_EPOCH],
            sha256_file(epoch_path) if epoch_path.is_file() else "missing",
        )

        with np.load(
            epoch_path,
            allow_pickle=False,
        ) as z:
            required_epoch = {
                "parent_saturation",
                "parent_component_mass_kg",
                "parent_pressure_psi",
                "reconciled_saturation",
                "refreshed_pressure_psi",
                "lambda_total",
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
                "xi",
                "tau_end_s",
                "streamline_face_pressure_psi",
                "canonical_day",
                "physical_time_advance",
                "PI_RNN_inference",
            }

            gate(
                "A2E_epoch_required_arrays",
                required_epoch.issubset(set(z.files)),
                sorted(z.files),
            )

            gate(
                "A2E_grid_state_shapes",
                np.asarray(z["reconciled_saturation"]).shape == GRID
                and np.asarray(z["refreshed_pressure_psi"]).shape == GRID
                and np.asarray(z["paired_porosity"]).shape == GRID
                and np.asarray(z["nw"]).shape == GRID
                and np.asarray(z["no"]).shape == GRID
                and np.asarray(z["krw_max"]).shape == GRID
                and np.asarray(z["kro_max"]).shape == GRID,
            )

            gate(
                "A2E_refreshed_streamline_shapes",
                np.asarray(z["streamline_xyz_m"]).shape == (NSL, NN, 3)
                and np.asarray(z["streamline_tof_s"]).shape == (NSL, NN)
                and np.asarray(z["streamline_weight_m3_s"]).shape == (NSL,)
                and np.asarray(z["tau_end_s"]).shape == (NSL,)
                and np.asarray(z["streamline_face_pressure_psi"]).shape == (NSL, NN),
            )

            gate(
                "A2E_xi_shape",
                np.asarray(z["xi"]).shape == (NN,),
                np.asarray(z["xi"]).shape,
            )

            gate(
                "A2E_canonical_day_exact",
                float(np.asarray(z["canonical_day"]).reshape(())) == CONTROL_DAY,
                float(np.asarray(z["canonical_day"]).reshape(())),
            )

            gate(
                "A2E_epoch_firewalls_exact",
                bool(np.asarray(z["physical_time_advance"]).reshape(())) is False
                and bool(np.asarray(z["PI_RNN_inference"]).reshape(())) is False,
            )

        # ------------------------------------------------------------------------------------------
        # Bind immutable historical AV3 checkpoint deployment result.
        # ------------------------------------------------------------------------------------------
        stage = "AV3_checkpoint_authority_binding"

        a6e = drive / A6E_REL

        gate(
            "AV3_A6E_output_present",
            a6e.is_dir(),
            str(a6e),
        )

        m6e = verify_manifest(
            a6e,
            A6E_MANIFEST,
        )

        s6e = load_json(
            a6e / A6E_SUMMARY
        )

        gate(
            "AV3_A6E_status_exact",
            s6e["status"] == A6E_STATUS,
            s6e["status"],
        )

        gate(
            "AV3_A6E_integrated_states_36",
            int(s6e["integrated_states"]) == 36,
            int(s6e["integrated_states"]),
        )

        a5r2 = drive / A5R2_REL

        gate(
            "AV3_A5R2_output_present",
            a5r2.is_dir(),
            str(a5r2),
        )

        m5 = verify_manifest(
            a5r2,
            A5R2_MANIFEST,
        )

        gate(
            "AV3_A5R2_manifest_exact_8",
            len(m5) == 8,
            len(m5),
        )

        s5 = load_json(
            a5r2 / A5R2_SUMMARY
        )

        d5 = load_json(
            a5r2 / A5R2_DECISION
        )

        gate(
            "AV3_A5R2_status_exact",
            s5["status"] == A5R2_STATUS,
            s5["status"],
        )

        gate(
            "AV3_checkpoint_epoch_and_training_identity_exact",
            s5["frozen_checkpoint_sha256"] == EXPECTED_CHECKPOINT_SHA256
            and int(s5["best_epoch"]) == EXPECTED_BEST_EPOCH
            and int(s5["epochs_completed"]) == EXPECTED_EPOCHS_COMPLETED,
        )

        gate(
            "AV3_one_touch_OOD_closed",
            d5["second_OOD_generation_authorized"] is False
            and d5["second_OOD_evaluation_authorized"] is False,
        )

        checkpoint = drive / CHECKPOINT_REL

        gate(
            "AV3_checkpoint_file_present",
            checkpoint.is_file(),
            str(checkpoint),
        )

        gate(
            "AV3_checkpoint_SHA_exact_without_model_load",
            checkpoint.is_file()
            and sha256_file(checkpoint) == EXPECTED_CHECKPOINT_SHA256,
            sha256_file(checkpoint) if checkpoint.is_file() else "missing",
        )

        # ------------------------------------------------------------------------------------------
        # Bind original AV3 13-channel, sampling, normalization, and leakage authorities.
        # ------------------------------------------------------------------------------------------
        stage = "AV3_13channel_authority_binding"

        a4 = drive / A4R2_REL

        gate(
            "AV3_A4R2_output_present",
            a4.is_dir(),
            str(a4),
        )

        m4 = verify_manifest(
            a4,
            A4R2_MANIFEST,
        )

        gate(
            "AV3_A4R2_manifest_exact_11",
            len(m4) == 11,
            len(m4),
        )

        for required_name in [
            A4R2_TRAINVAL,
            A4R2_NORM,
            A4R2_SIDECAR,
        ]:
            gate(
                "AV3_A4R2_manifested_" + Path(required_name).stem,
                required_name in m4,
                required_name,
            )

        with np.load(
            a4 / A4R2_NORM,
            allow_pickle=False,
        ) as z:
            pmean = float(
                np.asarray(z["pressure_mean_psi"]).reshape(-1)[0]
            )
            pstd = float(
                np.asarray(z["pressure_std_psi"]).reshape(-1)[0]
            )
            fit_ids = [
                str(x)
                for x in np.asarray(
                    z["fit_corey_realizations"]
                ).reshape(-1)
            ]

            gate(
                "AV3_pressure_normalization_finite_positive",
                np.isfinite(pmean)
                and np.isfinite(pstd)
                and pstd > 0.0,
                {
                    "mean_psi": pmean,
                    "std_psi": pstd,
                },
            )

            gate(
                "AV3_pressure_normalization_TRAIN_only",
                fit_ids == ["AV3CR0001", "AV3CR0002"]
                and bool(
                    np.asarray(
                        z["validation_used_for_pressure_fit"]
                    ).reshape(-1)[0]
                ) is False
                and bool(
                    np.asarray(
                        z["locked_OOD_used_for_pressure_fit"]
                    ).reshape(-1)[0]
                ) is False,
                fit_ids,
            )

            gate(
                "AV3_sampling_origin_normalization_exact",
                np.array_equal(
                    np.asarray(
                        z["sampling_origin_center_m"],
                        dtype=np.float64,
                    ),
                    ORIGIN_CENTER_M,
                ),
                np.asarray(
                    z["sampling_origin_center_m"],
                    dtype=np.float64,
                ).tolist(),
            )

        a3r1 = drive / AV3A3R1_REL

        gate(
            "AV3_A3R1_output_present",
            a3r1.is_dir(),
            str(a3r1),
        )

        m3r1 = verify_manifest(
            a3r1,
            AV3A3R1_MANIFEST,
        )

        gate(
            "AV3_A3R1_manifest_exact_10",
            len(m3r1) == 10,
            len(m3r1),
        )

        s3r1 = load_json(
            a3r1 / AV3A3R1_SUMMARY
        )

        f9 = load_json(
            a3r1 / AV3A3R1_FIRST9
        )

        n3r1 = load_json(
            a3r1 / AV3A3R1_NORM
        )

        gate(
            "AV3_A3R1_status_exact",
            s3r1["status"] == AV3A3R1_STATUS,
            s3r1["status"],
        )

        gate(
            "AV3_cell_center_origin_exact",
            np.array_equal(
                np.asarray(
                    f9["cell_center_origin_m"],
                    dtype=np.float64,
                ),
                ORIGIN_CENTER_M,
            ),
            f9["cell_center_origin_m"],
        )

        gate(
            "AV3_pressure_refit_contract_exact",
            n3r1["pressure_z"]["fit_required"] is True
            and n3r1["pressure_z"]["validation_used_for_fit"] is False
            and n3r1["pressure_z"]["locked_OOD_used_for_fit"] is False,
        )

        av3a3 = drive / AV3A3_REL

        gate(
            "AV3_A3_output_present",
            av3a3.is_dir(),
            str(av3a3),
        )

        m3 = verify_manifest(
            av3a3,
            AV3A3_MANIFEST,
        )

        gate(
            "AV3_A3_manifest_exact_10",
            len(m3) == 10,
            len(m3),
        )

        s3 = load_json(
            av3a3 / AV3A3_SUMMARY
        )

        model3 = load_json(
            av3a3 / AV3A3_MODEL
        )

        dataset3 = load_json(
            av3a3 / AV3A3_DATASET
        )

        residual3 = load_json(
            av3a3 / AV3A3_RESIDUAL
        )

        gate(
            "AV3_A3_status_exact",
            s3["status"] == AV3A3_STATUS,
            s3["status"],
        )

        gate(
            "AV3_13channel_order_exact",
            model3["channel_order"] == CHANNELS13,
            model3["channel_order"],
        )

        gate(
            "AV3_model_parameter_count_exact",
            int(model3["parameter_count"]) == MODEL_PARAMETERS,
            int(model3["parameter_count"]),
        )

        gate(
            "AV3_historical_temporal_pairing_is_adjacent_absolute_targets",
            residual3["time_derivative"]["pairs"]
            == "adjacent physical target times from same streamline",
            residual3["time_derivative"]["pairs"],
        )

        gate(
            "AV3_historical_split_firewall_exact",
            dataset3["VALIDATION_teacher_realizations"] == [CONTROL_REALIZATION]
            and dataset3["LOCKED_OOD_realization"] == "AV3CR0004",
        )

        # ------------------------------------------------------------------------------------------
        # Freeze refreshed 13-channel reconstruction.
        # ------------------------------------------------------------------------------------------
        stage = "refreshed_13channel_contract_freeze"

        channel_rows = [
            {
                "index": 0,
                "channel": "xi",
                "refreshed_source": "A2E xi, broadcast to every refreshed streamline",
                "normalization": "none",
                "flow_refresh_sensitive": False,
            },
            {
                "index": 1,
                "channel": "pollock_tau_hat",
                "refreshed_source": "A2E streamline_tof_s / A2E tau_end_s[:,None]",
                "normalization": "terminal refreshed Pollock TOF",
                "flow_refresh_sensitive": True,
            },
            {
                "index": 2,
                "channel": "adv_tau_hat",
                "refreshed_source": (
                    "recompute deterministic ADV travel-time field from A2E Qx/Qy/Qz "
                    "+ paired porosity using frozen historical ADV algorithm; sample on "
                    "A2E refreshed XYZ with cell-center origin; divide by refreshed tau_end_s"
                ),
                "normalization": "terminal refreshed Pollock TOF",
                "flow_refresh_sensitive": True,
            },
            {
                "index": 3,
                "channel": "log10_Kh",
                "refreshed_source": (
                    "sample frozen SGSim Kx=Ky=K on refreshed XYZ using exact "
                    "cell-centered trilinear geometry; log10(sqrt(Kx*Ky))"
                ),
                "normalization": "none",
                "flow_refresh_sensitive": True,
            },
            {
                "index": 4,
                "channel": "log10_Kz_over_Kh",
                "refreshed_source": (
                    "sample frozen Kz=0.10*K plus Kx/Ky on refreshed XYZ; "
                    "log10(Kz/Kh)"
                ),
                "normalization": "none",
                "flow_refresh_sensitive": True,
            },
            {
                "index": 5,
                "channel": "porosity",
                "refreshed_source": (
                    "sample A2E paired_porosity grid on refreshed XYZ using "
                    "cell-centered trilinear geometry"
                ),
                "normalization": "none",
                "flow_refresh_sensitive": True,
            },
            {
                "index": 6,
                "channel": "pressure_z",
                "refreshed_source": (
                    "A2E refreshed streamline node pressure, cross-checked against "
                    "cell-centered sampling of refreshed_pressure_psi"
                ),
                "normalization": (
                    "historical frozen AV3 TRAIN-only pressure mean/std; no refit"
                ),
                "flow_refresh_sensitive": True,
            },
            {
                "index": 7,
                "channel": "target_time_hat",
                "refreshed_source": (
                    "absolute historical target-day encoding only for representation audit; "
                    "must not be silently reinterpreted as restart delta-time"
                ),
                "normalization": "target_days/1000",
                "flow_refresh_sensitive": False,
            },
            {
                "index": 8,
                "channel": "target_eta_sequence",
                "refreshed_source": (
                    "historical absolute target_days*86400/refreshed tau_end_s, "
                    "repeated over 201 nodes, for representation audit only"
                ),
                "normalization": "refreshed terminal Pollock TOF",
                "flow_refresh_sensitive": True,
            },
            {
                "index": 9,
                "channel": "nw_hat",
                "refreshed_source": (
                    "sample A2E nw grid on refreshed XYZ with cell-centered geometry"
                ),
                "normalization": "(nw-3.0)/1.0",
                "flow_refresh_sensitive": True,
            },
            {
                "index": 10,
                "channel": "no_hat",
                "refreshed_source": (
                    "sample A2E no grid on refreshed XYZ with cell-centered geometry"
                ),
                "normalization": "(no-3.0)/1.0",
                "flow_refresh_sensitive": True,
            },
            {
                "index": 11,
                "channel": "krw_max_hat",
                "refreshed_source": (
                    "sample A2E krw_max grid on refreshed XYZ with cell-centered geometry"
                ),
                "normalization": "(krw_max-0.80)/0.20",
                "flow_refresh_sensitive": True,
            },
            {
                "index": 12,
                "channel": "kro_max_hat",
                "refreshed_source": (
                    "sample A2E kro_max grid on refreshed XYZ with cell-centered geometry"
                ),
                "normalization": "(kro_max-0.80)/0.20",
                "flow_refresh_sensitive": True,
            },
        ]

        gate(
            "refreshed_channel_registry_exact_13",
            [r["channel"] for r in channel_rows] == CHANNELS13,
            [r["channel"] for r in channel_rows],
        )

        reconstruction = {
            "milestone": MILESTONE,
            "channel_order": CHANNELS13,
            "nodes_per_streamline": NN,
            "refreshed_streamlines": NSL,
            "control_case": {
                "corey_realization": CONTROL_REALIZATION,
                "paired_porosity": CONTROL_POROSITY,
                "partition": CONTROL_PARTITION,
                "canonical_day": CONTROL_DAY,
            },
            "primary_flow_authority": {
                "artifact": A2E_EPOCH,
                "sha256": m2e[A2E_EPOCH],
            },
            "sampling_geometry": {
                "origin_center_m": ORIGIN_CENTER_M.tolist(),
                "spacing_m": [DX_M, DY_M, DZ_M],
                "interpolation": (
                    "exact historical V16B3/V16C2 cell-centered trilinear convention"
                ),
            },
            "pressure_normalization": {
                "mean_psi": pmean,
                "std_psi": pstd,
                "fit_authority": "frozen AV3CR0001+AV3CR0002 TRAIN only",
                "refit_in_AV4": False,
            },
            "constitutive_scaling": {
                "nw_hat": "(nw-3.0)/1.0",
                "no_hat": "(no-3.0)/1.0",
                "krw_max_hat": "(krw_max-0.80)/0.20",
                "kro_max_hat": "(kro_max-0.80)/0.20",
            },
            "required_reconstruction_identity_gates": [
                "all 13 channels finite",
                "shape exactly (1078,201,13) for one target-time slice",
                "channel order byte-for-byte equal to historical AV3 order",
                "xi starts at 0 and ends at 1",
                "pollock_tau_hat starts at 0 and ends at 1 for every streamline",
                "pressure_z uses historical TRAIN-only mean/std with no AV4 refit",
                "porosity and four constitutive channels use refreshed-path sampling",
                "all grid-to-streamline sampling uses half-cell origin [3.048,3.048,0.6096] m",
                "no checkpoint/model file loaded during reconstruction",
            ],
            "historical_validation_comparator": (
                "AV3CR0003 day-365 slice from the frozen A4-R2 validation predictor tensor"
            ),
            "direct_reuse_claim_after_reconstruction": False,
        }

        # ------------------------------------------------------------------------------------------
        # Freeze the structural temporal-semantics / restartability firewall.
        # ------------------------------------------------------------------------------------------
        stage = "restart_semantics_firewall_freeze"

        explicit_parent_state_channels = [
            c
            for c in CHANNELS13
            if c in {
                "parent_saturation",
                "current_saturation",
                "previous_saturation",
                "parent_component_mass",
                "current_component_mass",
                "previous_state",
            }
        ]

        gate(
            "historical_checkpoint_has_no_explicit_parent_state_channel",
            explicit_parent_state_channels == [],
            explicit_parent_state_channels,
        )

        temporal_firewall = {
            "historical_AV3_training_semantics": {
                "prediction_type": (
                    "absolute saturation profile at canonical target time under one "
                    "frozen streamline/TOF realization"
                ),
                "time_features": [
                    "target_time_hat = target_day/1000",
                    "target_eta_sequence = target_day*86400/terminal_TOF",
                ],
                "physics_pairs": (
                    "adjacent absolute target times on the same historical flow geometry"
                ),
                "explicit_parent_state_input": False,
            },
            "AV4_restart_problem": {
                "parent_time_days": CONTROL_DAY,
                "parent_state_authority": (
                    "A2E reconciled_saturation + exact parent_component_mass_kg"
                ),
                "flow_geometry_changed_at_parent_time": True,
                "next_canonical_day": 500.0,
                "next_interval_days": 135.0,
            },
            "forbidden_semantic_shortcuts": [
                (
                    "do not feed target_day=500 on the refreshed geometry and call the "
                    "result a 365->500 restart prediction without proof"
                ),
                (
                    "do not replace target_day by delta_t=135 and claim compatibility; "
                    "delta-time was not the historical checkpoint training semantics"
                ),
                (
                    "do not infer restartability from input-range overlap alone"
                ),
                (
                    "do not infer restartability from one low teacher error alone if "
                    "the parent-state information path is absent"
                ),
            ],
            "direct_restart_authority": {
                "currently_proven": False,
                "AV3_checkpoint_committed_reuse": False,
                "reason": (
                    "the frozen 13-channel signature has no explicit parent/current "
                    "saturation or component-mass state channel; restart semantics were "
                    "not part of the historical training contract"
                ),
            },
            "checkpoint_roles_still_allowed": [
                "immutable historical benchmark",
                "diagnostic one-touch compatibility candidate after a separate authorization",
                "possible transfer-learning initialization in a future restartable architecture",
            ],
        }

        # ------------------------------------------------------------------------------------------
        # Freeze predictor-domain shift audit.
        # ------------------------------------------------------------------------------------------
        stage = "input_domain_shift_contract_freeze"

        domain_shift = {
            "reference_authorities": {
                "TRAIN_VALIDATION_X13": A4R2_TRAINVAL,
                "TRAIN_VALIDATION_X13_sha256": m4[A4R2_TRAINVAL],
                "normalization": A4R2_NORM,
                "normalization_sha256": m4[A4R2_NORM],
            },
            "required_comparisons": [
                "refreshed AV3CR0003 day365 vs historical AV3CR0003 day365 channel-by-channel",
                "refreshed AV3CR0003 day365 vs frozen TRAIN support channel-by-channel",
                "refreshed streamline terminal-TOF distribution vs historical AV3CR0003 day365 geometry",
                "refreshed pressure_z distribution vs historical validation pressure_z",
                "refreshed constitutive samples vs historical AV3CR0003 path samples",
            ],
            "per_channel_metrics": [
                "finite_fraction",
                "minimum",
                "maximum",
                "mean",
                "standard_deviation",
                "q001",
                "q01",
                "q05",
                "q50",
                "q95",
                "q99",
                "q999",
                "fraction_below_frozen_TRAIN_min",
                "fraction_above_frozen_TRAIN_max",
                "mean_shift_in_frozen_TRAIN_std_units_when_std_nonzero",
            ],
            "sequence_metrics": [
                "relative_L2_vs_historical_validation_day365 for aligned scalar channels where alignment is meaningful",
                "terminal_TOF min/median/max and quantile shift",
                "refreshed path-length distribution shift",
                "producer-wise streamline-count/weight redistribution",
            ],
            "hard_failures": [
                "nonfinite reconstructed channel",
                "wrong shape/order",
                "normalization refit or use of AV4 statistics",
                "wrong cell-centered sampling origin",
                "opening/loading the PI-RNN checkpoint",
                "teacher transport execution",
                "physical-time advance",
            ],
            "domain_shift_role": (
                "diagnostic evidence only in A3-E1; no arbitrary numeric extrapolation "
                "threshold is allowed to authorize checkpoint reuse"
            ),
        }

        # ------------------------------------------------------------------------------------------
        # Freeze future teacher-backed checkpoint compatibility protocol.
        # This protocol is frozen here but NOT authorized for execution by A3.
        # ------------------------------------------------------------------------------------------
        stage = "teacher_backed_compatibility_protocol_freeze"

        teacher_protocol = {
            "status": "FROZEN_NOT_YET_EXECUTION_AUTHORIZED",
            "purpose": (
                "If structural restart-state representation is later closed, evaluate "
                "the immutable AV3 checkpoint against a physics teacher from the same "
                "refreshed parent state and refreshed flow epoch."
            ),
            "mandatory_preconditions_before_any_teacher_or_checkpoint_execution": [
                "A3-E1 refreshed X13 reconstruction PASS",
                "A3-E1 input-domain audit complete",
                "a separately frozen mass-conservative grid->refreshed-streamline parent-state projection",
                "an explicit restart temporal encoding contract",
                "proof that the tested model receives sufficient parent-state information OR a newly defined restartable model signature",
                "no reuse of locked OOD as a tuning set",
            ],
            "teacher_parent_state": {
                "time_days": CONTROL_DAY,
                "cellwise_component_mass": "exact A2E parent_component_mass_kg authority",
                "saturation": "exact A2E reconciled_saturation",
                "pressure": "exact A2E refreshed_pressure_psi",
                "flow_epoch": "exact A2E refreshed Pollock/TOF geometry",
            },
            "first_candidate_interval_if_later_authorized": {
                "from_day": 365.0,
                "to_day": 500.0,
                "delta_days": 135.0,
            },
            "checkpoint_rules_if_later_authorized": [
                "immutable SHA256 checkpoint only",
                "one candidate evaluation per frozen temporal encoding",
                "no retraining",
                "no checkpoint reselection",
                "no normalization refit",
                "no hyperparameter retuning",
                "no second locked OOD evaluation",
            ],
            "compatibility_decision_must_separate": [
                "representation/domain compatibility",
                "restart-state semantic compatibility",
                "teacher predictive agreement",
                "mass-conservative integration compatibility",
            ],
            "single_teacher_match_cannot_override_structural_restart_failure": True,
        }

        # ------------------------------------------------------------------------------------------
        # Freeze outcome classification.
        # ------------------------------------------------------------------------------------------
        stage = "outcome_classification_freeze"

        outcome = {
            "A3_E1_PASS_REPRESENTATION_ONLY": {
                "meaning": (
                    "refreshed X13 can be reconstructed exactly and audited; checkpoint "
                    "reuse still not authorized"
                ),
                "checkpoint_inference_authorized": False,
                "dynamic_transport_authorized": False,
            },
            "STRUCTURAL_RESTART_INCOMPATIBILITY": {
                "trigger": (
                    "historical 13-channel signature/temporal semantics cannot represent "
                    "the required parent-state-conditioned restart mapping"
                ),
                "checkpoint_committed_reuse": False,
                "automatic_retraining": False,
                "next": (
                    "freeze a state-conditioned restartable AV4 transport architecture "
                    "and conservative parent-state projection"
                ),
            },
            "TEACHER_BACKED_TEST_LATER_AUTHORIZED": {
                "trigger": (
                    "only after a separate restart-state representation/projection "
                    "contract is frozen and passed"
                ),
                "one_touch_checkpoint_inference": True,
                "production_dynamic_transport": False,
            },
            "TECHNICAL_BLOCK": {
                "automatic_rerun": False,
                "scientific_claim": False,
            },
        }

        # ------------------------------------------------------------------------------------------
        # A3-E1 handoff: representation and structural audit only.
        # ------------------------------------------------------------------------------------------
        handoff = {
            "milestone": "POSTV16-AV4-A3-E1",
            "name": (
                "Refreshed 13-Channel Reconstruction and Structural/Input-Domain "
                "Restart-Compatibility Audit"
            ),
            "authorized": True,
            "execution": True,
            "control_realization": CONTROL_REALIZATION,
            "paired_porosity": CONTROL_POROSITY,
            "canonical_day": CONTROL_DAY,
            "allowed": [
                "reconstruct the exact refreshed 13-channel day365 predictor representation",
                "read frozen TRAIN/VALIDATION X13 reference artifacts for comparison",
                "compute channel-by-channel input-domain diagnostics",
                "compare refreshed geometry/TOF/pressure representation with historical AV3CR0003 day365",
                "classify structural restart-state semantic support",
            ],
            "forbidden": [
                "load the .keras model",
                "perform checkpoint inference",
                "generate a new transport teacher",
                "advance physical time",
                "map back a new transported state",
                "retrain or reselect the checkpoint",
                "refit any normalization",
                "use locked OOD for tuning",
                "run CMG",
            ],
            "A3_E2_teacher_backed_checkpoint_test_authorized": False,
            "AV3_checkpoint_committed_reuse": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "A2E_scientific_PASS_bound": True,
            "A2E_refreshed_epoch_bound": True,
            "historical_AV3_checkpoint_SHA_bound": True,
            "historical_AV3_13channel_order_bound": True,
            "historical_TRAIN_only_normalization_bound": True,
            "refreshed_13channel_reconstruction_contract_frozen": True,
            "input_domain_shift_audit_contract_frozen": True,
            "restart_temporal_semantics_firewall_frozen": True,
            "teacher_backed_checkpoint_protocol_frozen": True,
            "historical_checkpoint_has_explicit_parent_state_input": False,
            "direct_restart_semantics_proven": False,
            "AV3_checkpoint_committed_reuse": False,
            "checkpoint_model_loaded": False,
            "checkpoint_inference_performed": False,
            "teacher_transport_performed": False,
            "physical_time_advanced": False,
            "normalization_refit": False,
            "training_performed": False,
            "checkpoint_reselected": False,
            "mapback_performed": False,
            "CMG_validation_performed": False,
            "AV4_A3_E1_authorized": True,
            "AV4_A3_E1_execution_authorized": True,
            "AV4_A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
            "next": handoff,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "control_realization": CONTROL_REALIZATION,
            "paired_porosity": CONTROL_POROSITY,
            "canonical_day": CONTROL_DAY,
            "refreshed_flow_epoch_sha256": m2e[A2E_EPOCH],
            "checkpoint_sha256": EXPECTED_CHECKPOINT_SHA256,
            "checkpoint_best_epoch": EXPECTED_BEST_EPOCH,
            "checkpoint_epochs_completed": EXPECTED_EPOCHS_COMPLETED,
            "input_channels": len(CHANNELS13),
            "channel_order": CHANNELS13,
            "model_parameters": MODEL_PARAMETERS,
            "pressure_normalization_mean_psi": pmean,
            "pressure_normalization_std_psi": pstd,
            "cell_center_origin_m": ORIGIN_CENTER_M.tolist(),
            "historical_checkpoint_parent_state_channels": 0,
            "direct_restart_semantics_proven": False,
            "checkpoint_inference": False,
            "teacher_transport": False,
            "physical_time_advance": False,
            "AV3_checkpoint_committed_reuse": False,
            "AV4_A3_E1_authorized": True,
            "AV4_A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        authority = {
            "A2E": {
                "status": A2E_STATUS,
                "refreshed_epoch_file": A2E_EPOCH,
                "refreshed_epoch_sha256": m2e[A2E_EPOCH],
            },
            "AV3_checkpoint": {
                "sha256": EXPECTED_CHECKPOINT_SHA256,
                "best_epoch": EXPECTED_BEST_EPOCH,
                "epochs_completed": EXPECTED_EPOCHS_COMPLETED,
                "model_loaded_in_A3": False,
            },
            "AV3_predictor": {
                "channel_order": CHANNELS13,
                "parameter_count": MODEL_PARAMETERS,
                "TRAIN_validation_dataset_sha256": m4[A4R2_TRAINVAL],
                "normalization_sha256": m4[A4R2_NORM],
                "physics_sidecar_sha256": m4[A4R2_SIDECAR],
            },
            "sampling": {
                "origin_center_m": ORIGIN_CENTER_M.tolist(),
                "B3_blob": B3_BLOB,
                "C2_blob": C2_BLOB,
            },
        }

        # R2 continuation provenance; scientific protocol content above is unchanged from original A3.
        summary["A3R2R1R3_preexecution_runtime_gate_defects_preserved"] = True
        summary["A3R2R1R3_preexecution_source_blob"] = A3R2R1R3_PREEXECUTION_BLOB
        summary["A3R2R1R2_preexecution_display_label_defect_preserved"] = True
        summary["A3R2R1R2_preexecution_source_blob"] = A3R2R1R2_PREEXECUTION_BLOB
        summary["A3R2R1R1_preexecution_provenance_defects_preserved"] = True
        summary["A3R2R1R1_preexecution_source_blob"] = A3R2R1R1_PREEXECUTION_BLOB
        summary["A3R2R1_preexecution_missing_import_preserved"] = True
        summary["A3R2R1_preexecution_source_blob"] = A3R2R1_PREEXECUTION_BLOB
        summary["AV4_A3R1_closure_bound"] = True
        summary["A3R2_preexecution_namespace_collision_preserved"] = True
        summary["A3R2_preexecution_source_blob"] = A3R2_PREEXECUTION_BLOB
        summary["original_A3_technical_BLOCK_preserved"] = True
        summary["original_A3_block_SHA256"] = original_block_sha
        summary["R1_only_correction"] = (
            "dynamic-transport authority read uses A2-E Summary instead of Decision"
        )

        decision["A3R2R1R3_preexecution_runtime_gate_corrected"] = True
        decision["A3R2R1R3_preexecution_scientific_execution_claimed"] = False
        decision["A3R2R1R2_preexecution_display_labels_normalized"] = True
        decision["A3R2R1R2_preexecution_scientific_execution_claimed"] = False
        decision["A3R2R1R1_preexecution_provenance_normalized"] = True
        decision["A3R2R1R1_preexecution_scientific_execution_claimed"] = False
        decision["A3R2R1_preexecution_missing_import_corrected"] = True
        decision["A3R2R1_preexecution_scientific_execution_claimed"] = False
        decision["AV4_A3R1_closure_bound"] = True
        decision["A3R2_preexecution_namespace_collision_corrected"] = True
        decision["A3R2_preexecution_scientific_execution_claimed"] = False
        decision["original_A3_technical_BLOCK_preserved"] = True
        decision["original_A3_block_SHA256"] = original_block_sha
        decision["R1_only_correction_applied"] = True
        decision["original_A3_source_modified"] = False

        authority["A3R2R1R3_preexecution_source_blob"] = A3R2R1R3_PREEXECUTION_BLOB
        authority["A3R2R1R3_runtime_gate_corrections"] = [
            "R2R1R2_stale_PASS_banner_detector",
            "R2R1R2_stale_BLOCK_banner_detector",
            "current_PASS_BLOCK_banners_derive_from_MILESTONE",
        ]
        authority["A3R2R1R2_preexecution_source_blob"] = A3R2R1R2_PREEXECUTION_BLOB
        authority["A3R2R1R2_display_correction"] = "PASS/BLOCK banners derived from MILESTONE"
        authority["A3R2R1R1_preexecution_source_blob"] = A3R2R1R1_PREEXECUTION_BLOB
        authority["A3R2R1R1_provenance_corrections"] = ["protocol_id_extra_R1_removed", "output_folder_extra_R1_removed", "overescaped_import_detection_regex_corrected"]
        authority["A3R2R1_preexecution_source_blob"] = A3R2R1_PREEXECUTION_BLOB
        authority["A3R2R1_missing_import"] = "re"
        authority["AV4_A3R1_closure_status"] = AV4A3R1_STATUS
        authority["A3R2_preexecution_source_blob"] = A3R2_PREEXECUTION_BLOB
        authority["AV3_A3R1_historical_source_blob"] = AV3A3R1_BLOB
        authority["AV4_A3R1_manifest_file"] = AV4A3R1_MANIFEST
        authority["original_A3_block_SHA256"] = original_block_sha
        authority["original_A3_source_blob"] = A3_ORIGINAL_BLOB

        output_files = {
            "PAD_Stream_POSTV16_AV4_A3_R2_R1_R4_Summary.json":
                json_bytes(summary),

            "POSTV16_AV4_A3_R2_R1_R4_Authority_and_Compatibility_Scope.json":
                json_bytes(authority),

            "POSTV16_AV4_A3_R2_R1_R4_Refreshed_13Channel_Reconstruction_Contract.json":
                json_bytes(reconstruction),

            "POSTV16_AV4_A3_R2_R1_R4_13Channel_Registry.csv":
                csv_bytes(channel_rows),

            "POSTV16_AV4_A3_R2_R1_R4_Temporal_Semantics_and_Restartability_Firewall.json":
                json_bytes(temporal_firewall),

            "POSTV16_AV4_A3_R2_R1_R4_Input_Domain_Shift_Audit_Contract.json":
                json_bytes(domain_shift),

            "POSTV16_AV4_A3_R2_R1_R4_Teacher_Backed_Checkpoint_Compatibility_Protocol.json":
                json_bytes(teacher_protocol),

            "POSTV16_AV4_A3_R2_R1_R4_Outcome_Classification_and_Gates.json":
                json_bytes(outcome),

            "POSTV16_AV4_A3_R2_R1_R4_A3E1_Handoff_Contract.json":
                json_bytes(handoff),

            "POSTV16_AV4_A3_R2_R1_R4_Decision_Contract.json":
                json_bytes(decision),

            "POSTV16_AV4_A3_R2_R1_R4_Final_Gate_Matrix.csv":
                csv_bytes(
                    [
                        {
                            "gate": name,
                            **value,
                        }
                        for name, value in gates.items()
                    ]
                ),
        }

        immutable_publish(
            out,
            output_files,
        )

        manifest_rows = []

        for p in sorted(out.iterdir()):
            if (
                p.is_file()
                and p.name != "POSTV16_AV4_A3_R2_R1_R4_Artifact_Manifest.csv"
            ):
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
                "POSTV16_AV4_A3_R2_R1_R4_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print()
        print("=" * 214)
        print("POSTV16-AV4-A3-R2-R1-R1: PREEXECUTION IMPORT-CORRECTED PROTOCOL FREEZE PASS")
        print("=" * 214)
        print("R2-R1-R1 provenance defects             : PRESERVED / NORMALIZED")
        print("R2-R1 preexecution missing import        : PRESERVED / CORRECTED")
        print("R2 preexecution namespace defect         : PRESERVED / CORRECTED")
        print("AV4 A3-R1 technical closure              : BOUND")
        print("Original A3 technical block              : PRESERVED")
        print("A2-E refreshed-flow authority             : BOUND")
        print("Historical AV3 checkpoint                 :", EXPECTED_CHECKPOINT_SHA256)
        print("Historical AV3 input signature            : 201 x 13")
        print("Historical parent-state input channels    : 0")
        print("Refreshed X13 reconstruction contract     : FROZEN")
        print("Input-domain shift audit                  : FROZEN")
        print("Restart temporal-semantics firewall       : FROZEN")
        print("Teacher-backed compatibility protocol     : FROZEN / NOT YET EXECUTION AUTHORIZED")
        print("Checkpoint model load / inference         : False / False")
        print("Teacher transport / time advance          : False / False")
        print("AV3 checkpoint committed reuse            : False")
        print("POSTV16-AV4-A3-E1                         : AUTHORIZED")
        print("A3-E1 execution                           : AUTHORIZED")
        print("A3-E2 checkpoint test                     : NOT YET AUTHORIZED")
        print("AV4 dynamic transport                     : NOT YET AUTHORIZED")
        print("=" * 214)

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
            "exception": repr(exc),
            "gates": gates,
            "checkpoint_model_loaded": False,
            "checkpoint_inference_performed": False,
            "teacher_transport_performed": False,
            "physical_time_advanced": False,
            "training_performed": False,
            "normalization_refit": False,
            "AV4_A3_E1_authorized": False,
            "AV4_A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        p = (
            blocked
            / "POSTV16_AV4_A3_R2_R1_R4_Blocked_Report.json"
        )

        if not p.exists():
            p.write_bytes(
                json_bytes(report)
            )

        print()
        print("=" * 214)
        print("POSTV16-AV4-A3-R2-R1-R1: TECHNICAL / AUTHORITY BLOCK")
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
        raise SystemExit(0)

    raise SystemExit(
        main(
            args.project_root,
            args.drive_root,
        )
    )
