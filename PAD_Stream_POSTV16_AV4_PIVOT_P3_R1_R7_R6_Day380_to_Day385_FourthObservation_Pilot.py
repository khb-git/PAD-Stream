#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import os
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

M = "POSTV16-AV4-PIVOT-P3-R1-R7-R6"
NAME = "Restart-Safe XY2 Day380-to-Day385 Fourth-Observation Pilot + Exact Flow Diagnostic"
PASS = "AV4PIVOTP3R1R7R6_XY2_DAY380_TO_DAY385_FOURTH_OBSERVATION_PILOT_EXACT_FLOW_DIAGNOSTIC_PASS"
BLOCK = "AV4PIVOTP3R1R7R6_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "646e8ae3c9f1cf771328b8911d5d688de219842f"

P3R1 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_Corrected_Dense_FrozenFlow_Trajectory_and_Exact_5Day_Flow_Diagnostic_Sweep.py"
P3R1_BLOB = "84076001f40ebcf0825bb8d9bcabe060ed0840d2"
R31 = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R31_PostR30_Recurrent_FrozenFlow_Transport_Mapback_Certification.py"
R31_BLOB = "c6307aa53109c4ae6c4a2f962e1fef86fbc8ea4a"
R32 = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R32_Independent_Recurrent_Operation_Closure_Audit.py"
R32_BLOB = "435f5d6dcba38de7166e41ba9e081b6ef573edcf"
R3 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R3_Reduced_ExactSupport_Stage2_Equivalence_Runtime_Diagnostic.py"
R3_BLOB = "5dd59c82baf44977cd11cdbd28215c8762863914"

R4R1 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R4_R1_PositiveHalo_Stage2_ColumnGeneration_Diagnostic.py"
R4R1_BLOB = "8c7f96922ff2528e7a6cd472e73b9b15dd7e03ad"
R4R2 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R4_R2_Combined_ZeroPositiveHalo_TenStep_Recurrent_Prefix_Certification.py"
R4R2_BLOB = "08032db8679c58667a9df253ad072e7cc307f48e"

R5 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R5_RestartSafe_Day365_to_Day370_Repaired_Pilot_and_Exact_Flow_Diagnostic.py"
R5_BLOB = "effbefeebe1444010b07e0384061f0d4e4f26fe4"
R5R1R1 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R5_R1_R1_Corrected_Step42_CarryForward_ShellSupport_Runtime_Diagnostic.py"
R5R1R1_BLOB = "ae3c89efed89e1be8342ec12ad41a5ff56e363d4"

R5R2 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R5_R2_Checkpoint_Resume_CarryForward_Day370_Pilot.py"
R5R2_BLOB = "d2073155f6cdc9e84d87e9ed02b8d3d99488091f"

R6SRC = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R6_Day370_to_Day375_SecondObservation_Pilot.py"
R6SRC_BLOB = "e89eb57b753ba546b0ca8ec948042c7cab3537f6"
R6R1 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R6_R1_Day375_Publication_Technical_Closure_Audit.py"
R6R1_BLOB = "0cae6210d70af94e75189929a25057dae658ab43"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
P3R1_STAGE_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_STAGING"
P3R1_DAY365_STATE = "POSTV16_AV4_PIVOT_P3_R1_Day0365_Accepted_Dense_State.npz"

R3_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_R3_Reduced_ExactSupport_Stage2_Equivalence_Runtime_Diagnostic"
R3_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R3_Summary.json"
R3_DECISION = "POSTV16_AV4_PIVOT_P3_R1_R3_Decision_Contract.json"
R3_STAGE2 = "POSTV16_AV4_PIVOT_P3_R1_R3_Reduced_Stage2_Result.json"
R3_MANIFEST = "POSTV16_AV4_PIVOT_P3_R1_R3_Artifact_Manifest.csv"
R3_STATUS = "AV4PIVOTP3R1R3_REDUCED_EXACT_SUPPORT_STAGE2_EQUIVALENCE_RUNTIME_DIAGNOSTIC_PASS_NO_STATE_MUTATION"
R3_CLASS = "P3R1_FIRST_STEP_REDUCED_EXACT_SUPPORT_STAGE2_SOLVED_WITH_FROZEN_LEXICOGRAPHIC_OBJECTIVE_RUNTIME_PATH_CERTIFIED_SHORT_PREFIX_IMPLEMENTATION_AUTHORIZED"

R4R1_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_R4_R1_PositiveHalo_Stage2_ColumnGeneration_Diagnostic"
R4R1_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R4_R1_Summary.json"
R4R1_DECISION = "POSTV16_AV4_PIVOT_P3_R1_R4_R1_Decision_Contract.json"
R4R1_RESULT = "POSTV16_AV4_PIVOT_P3_R1_R4_R1_Restricted_Stage2_Result.json"
R4R1_MANIFEST = "POSTV16_AV4_PIVOT_P3_R1_R4_R1_Artifact_Manifest.csv"
R4R1_STATUS = "AV4PIVOTP3R1R4R1_POSITIVE_HALO_STAGE2_COLUMN_GENERATION_DIAGNOSTIC_PASS_NO_AUTHORITATIVE_STATE_MUTATION"
R4R1_CLASS = "P3R1_STEP3_POSITIVE_HALO_STAGE2_GLOBAL_OPTIMUM_CERTIFIED_BY_RESTRICTED_MASTER_AND_DUAL_PRICING_COLUMN_GENERATION_TEN_STEP_REPAIR_IMPLEMENTATION_AUTHORIZED"

R4R2_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_R4_R2_Combined_ZeroPositiveHalo_TenStep_Recurrent_Prefix_Certification"
R4R2_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R4_R2_Summary.json"
R4R2_DECISION = "POSTV16_AV4_PIVOT_P3_R1_R4_R2_Decision_Contract.json"
R4R2_AUDIT = "POSTV16_AV4_PIVOT_P3_R1_R4_R2_Step_Audit.csv"
R4R2_MANIFEST = "POSTV16_AV4_PIVOT_P3_R1_R4_R2_Artifact_Manifest.csv"
R4R2_STATUS = "AV4PIVOTP3R1R4R2_COMBINED_ZERO_POSITIVE_HALO_TEN_STEP_RECURRENT_PREFIX_CERTIFICATION_PASS_SHADOW_EXECUTION"
R4R2_CLASS = "P3R1_COMBINED_ZERO_AND_POSITIVE_HALO_FAST_PATHS_RECURRENTLY_CERTIFIED_FOR_TEN_CONSECUTIVE_ATOMIC_STEPS_NO_GENERIC_STAGE2_FALLBACK_DAY370_REPAIRED_PILOT_AUTHORIZED"

R5_STAGE_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_R5_STAGING"
R5_BLOCK_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_R5_BLOCKED"
R5_SOURCE_CHECKPOINT = "POSTV16_AV4_PIVOT_P3_R1_R5_Latest_Recurrent_Checkpoint.npz"
R5_SOURCE_CHECKPOINT_META = "POSTV16_AV4_PIVOT_P3_R1_R5_Latest_Recurrent_Checkpoint.json"
R5_SOURCE_STEP_AUDIT = "POSTV16_AV4_PIVOT_P3_R1_R5_Atomic_Step_Audit.csv"
R5_BLOCK_FILE = "POSTV16_AV4_PIVOT_P3_R1_R5_Blocked_Report.json"
R5_BLOCK_STATUS = "AV4PIVOTP3R1R5_TECHNICAL_OR_AUTHORITY_BLOCK"
R5_SOURCE_CHECKPOINT_SHA = "70fd7b6c233d9fe62828ffb5e979cc5a09bb73955b92a64c90d1cecfa7dd9a86"
R5_SOURCE_DAY = 366.4084157817048
R5_SOURCE_ACCEPTED_STEPS = 41

R5R1R1_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_R5_R1_R1_Corrected_Step42_CarryForward_ShellSupport_Runtime_Diagnostic"
R5R1R1_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R5_R1_R1_Summary.json"
R5R1R1_DECISION = "POSTV16_AV4_PIVOT_P3_R1_R5_R1_R1_Decision_Contract.json"
R5R1R1_RESULT = "POSTV16_AV4_PIVOT_P3_R1_R5_R1_R1_CarryForward_Result.json"
R5R1R1_MANIFEST = "POSTV16_AV4_PIVOT_P3_R1_R5_R1_R1_Artifact_Manifest.csv"
R5R1R1_STATUS = "AV4PIVOTP3R1R5R1R1_CORRECTED_STEP42_CARRY_FORWARD_SHELL_SUPPORT_RUNTIME_DIAGNOSTIC_PASS_NO_STATE_MUTATION"
R5R1R1_CLASS = "P3R1_STEP42_CARRY_FORWARD_SHELL_SUPPORT_COLUMN_GENERATION_GLOBAL_OPTIMUM_CERTIFIED_R5_CHECKPOINT_RESUME_REPAIR_AUTHORIZED"

R5R2_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_R5_R2_Checkpoint_Resume_CarryForward_Day370_Pilot_and_Exact_Flow_Diagnostic"
R5R2_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R5_R2_Summary.json"
R5R2_DECISION = "POSTV16_AV4_PIVOT_P3_R1_R5_R2_Decision_Contract.json"
R5R2_STATE = "POSTV16_AV4_PIVOT_P3_R1_R5_R2_Day0370_Accepted_Dense_State.npz"
R5R2_DIAGNOSTIC = "POSTV16_AV4_PIVOT_P3_R1_R5_R2_Day0370_Exact_Flow_Diagnostic.npz"
R5R2_AUDIT = "POSTV16_AV4_PIVOT_P3_R1_R5_R2_Atomic_Step_Audit.csv"
R5R2_MANIFEST = "POSTV16_AV4_PIVOT_P3_R1_R5_R2_Artifact_Manifest.csv"
R5R2_STATUS = "AV4PIVOTP3R1R5R2_CHECKPOINT_RESUME_CARRY_FORWARD_DAY370_PILOT_EXACT_FLOW_DIAGNOSTIC_PASS"
R5R2_CLASS = "P3R1_REPAIRED_DAY365_TO_DAY370_TRANSPORT_AND_EXACT_FLOW_DIAGNOSTIC_PILOT_CERTIFIED_RESTART_SAFE_COMBINED_FAST_PATHS_NO_GENERIC_STAGE2_FALLBACK_DAY375_PILOT_AUTHORIZED"
R5R2_STATE_SHA = "04fe6318623b1a7e4bf003cf49504648a2f32729a96c5a557294f664f4c35122"
R5R2_DIAGNOSTIC_SHA = "705409ee1b04241d294d9404d2945f4aa307ea0b2b68612a1cf8f86d7558e48a"
R5R2_SOURCE_DAY = 370.0
R5R2_ACCEPTED_STEPS = 138

R6SRC_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_R6_Day370_to_Day375_SecondObservation_Pilot_and_Exact_Flow_Diagnostic"
R6SRC_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R6_Summary.json"
R6SRC_DECISION = "POSTV16_AV4_PIVOT_P3_R1_R6_Decision_Contract.json"
R6SRC_STATE = "POSTV16_AV4_PIVOT_P3_R1_R6_Day0375_Accepted_Dense_State.npz"
R6SRC_DIAGNOSTIC = "POSTV16_AV4_PIVOT_P3_R1_R6_Day0375_Exact_Flow_Diagnostic.npz"
R6SRC_AUDIT = "POSTV16_AV4_PIVOT_P3_R1_R6_Atomic_Step_Audit.csv"
R6SRC_MANIFEST = "POSTV16_AV4_PIVOT_P3_R1_R6_Artifact_Manifest.csv"
R6SRC_STATUS = "AV4PIVOTP3R1R6_DAY370_TO_DAY375_SECOND_OBSERVATION_PILOT_EXACT_FLOW_DIAGNOSTIC_PASS"
R6SRC_CLASS = "P3R1_REPAIRED_DAY370_TO_DAY375_SECOND_OBSERVATION_TRANSPORT_AND_EXACT_FLOW_DIAGNOSTIC_CERTIFIED_RESTART_SAFE_CARRY_FORWARD_NO_GENERIC_STAGE2_FALLBACK_DAY380_PILOT_AUTHORIZED"
R6SRC_STATE_SHA = "89b69ed69ef2c67babcf1e52ead0add950f366379c849f23645be5b18dc5d7ac"
R6SRC_DIAGNOSTIC_SHA = "43957d890246452bcfc78467f19aba4f48feaaf9a0ffa58aababe7e7189e9c31"
R6SRC_SOURCE_DAY = 375.0
R6SRC_ACCEPTED_STEPS = 273

R6R1_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_R6_R1_Day375_Publication_Only_Technical_Closure_Audit"
R6R1_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R6_R1_Summary.json"
R6R1_DECISION = "POSTV16_AV4_PIVOT_P3_R1_R6_R1_Decision_Contract.json"
R6R1_AUDIT = "POSTV16_AV4_PIVOT_P3_R1_R6_R1_Closure_Audit.csv"
R6R1_MANIFEST = "POSTV16_AV4_PIVOT_P3_R1_R6_R1_Artifact_Manifest.csv"
R6R1_STATUS = "AV4PIVOTP3R1R6R1_DAY375_PUBLICATION_ONLY_TECHNICAL_CLOSURE_PASS_NO_STATE_MUTATION"
R6R1_CLASS = "P3R1_R6_DAY375_SCIENCE_ARTIFACTS_AND_DECISION_CERTIFIED_PUBLICATION_PRINT_NAMEERROR_CLOSED_DAY380_PILOT_AUTHORITY_PRESERVED"

R7SRC = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_Day375_to_Day380_ThirdObservation_Pilot.py"
R7SRC_BLOB = "0b42bb4cdd395740742e3784f455a2837f3b7ce2"
R7_SOURCE_STAGE_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_R7_STAGING"
R7_SOURCE_BLOCK_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_R7_BLOCKED"
R7_SOURCE_CHECKPOINT = "POSTV16_AV4_PIVOT_P3_R1_R7_Latest_Recurrent_Checkpoint.npz"
R7_SOURCE_CHECKPOINT_META = "POSTV16_AV4_PIVOT_P3_R1_R7_Latest_Recurrent_Checkpoint.json"
R7_SOURCE_BLOCK_FILE = "POSTV16_AV4_PIVOT_P3_R1_R7_Blocked_Report.json"
R7_SOURCE_CHECKPOINT_SHA = "d02fef7ef29d273002c1be613539fc39afac1ff231ad369b5f6571b0adcda83b"
R7_SOURCE_BLOCK_STATUS = "AV4PIVOTP3R1R7_TECHNICAL_OR_AUTHORITY_BLOCK"
R7_SOURCE_DAY = 376.9106720614003
R7_SOURCE_ACCEPTED_STEPS = 328

R7R4R1 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_R4_R1_Corrected_Certified_Master_Replay_Implementation_Freeze.py"
R7R4R1_BLOB = "d5089a62ef7d894f6efec3be4331ffa6a8ecb9fc"
R7R4R1_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_R7_R4_R1_Corrected_Certified_Master_Replay_XY2_Checkpoint_Resume_Implementation_Freeze"
R7R4R1_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_R4_R1_Summary.json"
R7R4R1_DECISION = "POSTV16_AV4_PIVOT_P3_R1_R7_R4_R1_Decision_Contract.json"
R7R4R1_IMPLEMENTATION = "POSTV16_AV4_PIVOT_P3_R1_R7_R4_R1_Implementation_Contract.json"
R7R4R1_REPLAY = "POSTV16_AV4_PIVOT_P3_R1_R7_R4_R1_Certified_Master_Replay.json"
R7R4R1_MANIFEST = "POSTV16_AV4_PIVOT_P3_R1_R7_R4_R1_Artifact_Manifest.csv"
R7R4R1_STATUS = "AV4PIVOTP3R1R7R4R1_CORRECTED_CERTIFIED_MASTER_REPLAY_IMPLEMENTATION_FREEZE_PASS_NO_STATE_MUTATION"
R7R4R1_CLASS = "P3R1_R7_XY2_CHECKPOINT_RESUME_IMPLEMENTATION_FREEZE_CERTIFIED_R7_CHECKPOINT_RESUME_EXECUTION_AUTHORIZED"

R7R5 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_R5_XY2_Checkpoint_Resume_Day380_Pilot.py"
R7R5_BLOB = "50214cbcc325335135b82cfa7e0f3d79f9955865"
R7R5_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_R7_R5_XY2_Checkpoint_Resume_Day380_Pilot_and_Exact_Flow_Diagnostic"
R7R5_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_R5_Summary.json"
R7R5_DECISION = "POSTV16_AV4_PIVOT_P3_R1_R7_R5_Decision_Contract.json"
R7R5_STATE = "POSTV16_AV4_PIVOT_P3_R1_R7_R5_Day0380_Accepted_Dense_State.npz"
R7R5_DIAGNOSTIC = "POSTV16_AV4_PIVOT_P3_R1_R7_R5_Day0380_Exact_Flow_Diagnostic.npz"
R7R5_AUDIT = "POSTV16_AV4_PIVOT_P3_R1_R7_R5_Atomic_Step_Audit.csv"
R7R5_MANIFEST = "POSTV16_AV4_PIVOT_P3_R1_R7_R5_Artifact_Manifest.csv"
R7R5_STATUS = "AV4PIVOTP3R1R7R5_XY2_CHECKPOINT_RESUME_DAY380_PILOT_EXACT_FLOW_DIAGNOSTIC_PASS"
R7R5_CLASS = "P3R1_R7_XY2_CHECKPOINT_RESUME_DAY380_TRANSPORT_AND_EXACT_FLOW_DIAGNOSTIC_CERTIFIED_NO_GENERIC_STAGE2_FALLBACK_DAY385_PILOT_AUTHORIZED"
R7R5_STATE_SHA = "691bde994f9b0c80f2fc53f575ed642fd0aaef5259d8bb6d20b8508957f63eca"
R7R5_DIAGNOSTIC_SHA = "1f17c00888774c20c1f9a9a9a45965536f8412107721d676ab7b12d287249189"
R7R5_SOURCE_DAY = 380.0
R7R5_ACCEPTED_STEPS = 411
EXPECTED_EXISTING_EDGE_COUNT = 1245666
EXPECTED_EXISTING_SHELL_EDGE_COUNT = 975945
EXPECTED_XY2_NEW_EDGE_COUNT = 1845407
EXPECTED_TOTAL_EDGE_COUNT = 3091073

OUT_TOKEN = "POSTV16_AV4_PIVOT_P3_R1_R7_R6"
OUT_REL = BASE_AV4 / (OUT_TOKEN + "_XY2_Day380_to_Day385_FourthObservation_Pilot_and_Exact_Flow_Diagnostic")
STAGE_REL = BASE_AV4 / (OUT_TOKEN + "_STAGING")
BLOCK_REL = BASE_AV4 / (OUT_TOKEN + "_BLOCKED")

SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
STEP_AUDIT = f"{OUT_TOKEN}_Atomic_Step_Audit.csv"
FINAL_STATE = f"{OUT_TOKEN}_Day0385_Accepted_Dense_State.npz"
FLOW_DIAGNOSTIC = f"{OUT_TOKEN}_Day0385_Exact_Flow_Diagnostic.npz"
DIAGNOSTIC_METRICS = f"{OUT_TOKEN}_Day0385_Exact_Flow_Diagnostic_Metrics.json"
CHECKPOINT_LATEST = f"{OUT_TOKEN}_Latest_Recurrent_Checkpoint.npz"
CHECKPOINT_META = f"{OUT_TOKEN}_Latest_Recurrent_Checkpoint.json"
CHECKPOINT_ARCHIVE_PREFIX = f"{OUT_TOKEN}_Checkpoint_Step"
GATES = f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"

DAY_TO_S = 86400.0
MASS_TOL = 1.0e-6
SAT_TOL = 1.0e-10
REL_TOL = 1.0e-10
HIGHS_FEAS_TOL = 1.0e-10
HALO_OPT_TOL = 1.0e-6
DEFAULT_TIME_LIMIT = 300.0
TARGET_DAY = 385.0
MAX_RETRIES = 8
RETRY_FACTOR = 0.5
CHECKPOINT_ARCHIVE_EVERY = 10
MAX_CG_ITERATIONS = 12
COLUMN_BATCH_SIZE = 10000
PRICING_TOL = 1.0e-8
POSITIVE_EDGE_TOL = 1.0e-10


class GateError(RuntimeError):
    pass


class TrialReject(RuntimeError):
    pass


def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load:{path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def js(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def csvr(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def csvb(rows: list[dict[str, Any]]) -> bytes:
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


def jb(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def verify_manifest(directory: Path, filename: str) -> dict[str, str]:
    out = {}
    for row in csvr(directory / filename):
        p = directory / row["file"]
        if not p.is_file():
            raise GateError(f"manifest_missing:{p.name}")
        if sha(p) != row["sha256"]:
            raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes:{p.name}")
        out[p.name] = row["sha256"]
    if not out:
        raise GateError(f"manifest_empty:{filename}")
    return out


def deterministic_npz_bytes(arrays: dict[str, Any]) -> bytes:
    outer = io.BytesIO()
    import zipfile
    with zipfile.ZipFile(outer, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for key in sorted(arrays):
            arr = np.asarray(arrays[key])
            if arr.dtype == object:
                raise GateError(f"object_dtype_forbidden:{key}")
            payload = io.BytesIO()
            np.lib.format.write_array(payload, arr, allow_pickle=False)
            info = zipfile.ZipInfo(f"{key}.npy")
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, payload.getvalue())
    return outer.getvalue()


def classify(day385_reached: bool, diagnostic_passed: bool, generic_fallback_count: int) -> tuple[str, str, bool]:
    if day385_reached and diagnostic_passed and generic_fallback_count == 0:
        return (
            "P3R1_R7_XY2_DAY380_TO_DAY385_FOURTH_OBSERVATION_TRANSPORT_AND_EXACT_FLOW_DIAGNOSTIC_CERTIFIED_NO_GENERIC_STAGE2_FALLBACK_DAY390_PILOT_AUTHORIZED",
            "Execute a Day385-to-Day390 fifth-observation pilot from the certified Day385 schema-v2 state using the same frozen exact+XY1+XY2 recurrent semantics and one-shot exact diagnostic; keep the full Day365-to500 sweep and P4 locked.",
            True,
        )
    if day385_reached and diagnostic_passed:
        return (
            "P3R1_R7_XY2_DAY380_TO_DAY385_FOURTH_OBSERVATION_CERTIFIED_BUT_GENERIC_STAGE2_FALLBACK_USED_RUNTIME_PATH_REQUIRES_LOCALIZATION_BEFORE_EXTENSION",
            "Localize the generic exact+XY1+XY2 Stage2 fallback usage before extending beyond Day385; keep the full Day365-to500 sweep and P4 locked.",
            False,
        )
    return (
        "P3R1_R7_XY2_DAY380_TO_DAY385_FOURTH_OBSERVATION_PILOT_NOT_CERTIFIED_NO_EXTENSION_AUTHORIZED",
        "Use the restart-safe schema-v2 checkpoint, atomic-step, and diagnostic evidence to diagnose the first unresolved condition; do not extend beyond Day385.",
        False,
    )

def selftest() -> None:
    c, _, ok = classify(True, True, 0)
    assert "DAY390_PILOT_AUTHORIZED" in c and ok
    c, _, ok = classify(True, True, 1)
    assert "GENERIC_STAGE2_FALLBACK_USED" in c and not ok
    assert TARGET_DAY == 385.0
    assert MAX_RETRIES == 8 and RETRY_FACTOR == 0.5
    assert PARENT == "646e8ae3c9f1cf771328b8911d5d688de219842f"
    print("POSTV16 AV4 PIVOT P3-R1-R7-R6 structural self-test: PASS")


def main(project_root: Path, drive_root: Path, time_limit_seconds: float) -> int:
    from scipy.optimize import linprog
    from scipy.sparse import coo_matrix, csr_matrix, eye, hstack, vstack

    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    staging = drive / STAGE_REL
    blocked = drive / BLOCK_REL
    stage = "preflight"
    gates: list[dict[str, Any]] = []

    def gate(name: str, cond: Any, detail: Any = None) -> None:
        ok = bool(cond)
        gates.append({
            "stage": stage,
            "gate": name,
            "pass": ok,
            "detail": "" if detail is None else repr(detail),
        })
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"), flush=True)
        if not ok:
            raise GateError(name)

    try:
        print("=" * 220, flush=True)
        print("POSTV16-AV4-PIVOT-P3-R1-R7-R6 — XY2 DAY380-TO-DAY385 FOURTH-OBSERVATION PILOT + EXACT FLOW DIAGNOSTIC", flush=True)
        print("START FROM THE FORMAL R7-R5 DAY380 SCHEMA-V2 ACCEPTED STATE. CONTINUE TO DAY385 ONLY. DO NOT REPLAY THE DAY376.910672 REPAIR.", flush=True)
        print("FAST PATHS: DIRECT -> ZERO-HALO REDUCED STAGE2; POSITIVE-HALO -> FULL STAGE1 + CARRY-FORWARD COLUMN-GENERATED EXACT STAGE2.", flush=True)
        print("FROZEN GENERIC EXACT+XY1+XY2 LEXICOGRAPHIC SOLVER IS RETAINED AS BOUNDED FALLBACK. ADAPTIVE RETRY/CFL SEMANTICS ARE PRESERVED.", flush=True)
        print("=" * 220, flush=True)

        stage = "preexisting_state_firewall"
        gate("no_preexisting_PASS", not (out / SUMMARY).exists())
        gate("no_preexisting_BLOCK", not (blocked / f"{OUT_TOKEN}_Blocked_Report.json").exists())
        latest_checkpoint_path = staging / CHECKPOINT_LATEST
        latest_checkpoint_meta_path = staging / CHECKPOINT_META
        if staging.exists():
            gate("existing_STAGING_is_resumable_checkpoint", latest_checkpoint_path.is_file() and latest_checkpoint_meta_path.is_file(), str(staging))
        else:
            staging.mkdir(parents=True, exist_ok=False)

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH, gt(root, "branch", "--show-current"))
        gate("parent_is_R7R5_commit", gt(root, "rev-parse", "HEAD^") == PARENT, gt(root, "rev-parse", "HEAD^"))
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for fn, blob in [(P3R1, P3R1_BLOB), (R31, R31_BLOB), (R32, R32_BLOB), (R3, R3_BLOB), (R4R1, R4R1_BLOB), (R4R2, R4R2_BLOB), (R5, R5_BLOB), (R5R1R1, R5R1R1_BLOB), (R5R2, R5R2_BLOB), (R6SRC, R6SRC_BLOB), (R6R1, R6R1_BLOB), (R7SRC, R7SRC_BLOB), (R7R4R1, R7R4R1_BLOB), (R7R5, R7R5_BLOB)]:
            fp = root / fn
            gate(f"{Path(fn).stem}_present", fp.is_file(), str(fp))
            gate(f"{Path(fn).stem}_blob_exact", gt(root, "hash-object", str(fp)) == blob, gt(root, "hash-object", str(fp)))

        p3 = load_module(root / P3R1, "p3r1_r7_authority")

        stage = "R3_authority"
        r3dir = drive / R3_REL
        gate("R3_dir_exists", r3dir.is_dir(), str(r3dir))
        for fn in [R3_SUMMARY, R3_DECISION, R3_STAGE2, R3_MANIFEST]:
            gate(f"R3_artifact_present:{fn}", (r3dir / fn).is_file())
        verify_manifest(r3dir, R3_MANIFEST)
        r3sum = js(r3dir / R3_SUMMARY)
        r3dec = js(r3dir / R3_DECISION)
        r3stage2 = js(r3dir / R3_STAGE2)
        gate("R3_status_exact", r3sum.get("status") == R3_STATUS, r3sum.get("status"))
        gate("R3_classification_exact", r3sum.get("classification") == R3_CLASS, r3sum.get("classification"))
        gate("R3_reduced_stage2_success", r3stage2.get("success") is True, r3stage2.get("outcome"))
        gate("R3_short_prefix_authorized", r3dec.get("reduced_stage2_short_prefix_implementation_authorized") is True)
        gate("R3_full_rerun_locked", r3dec.get("P3_R1_full_rerun_authorized") is False)
        gate("R3_P4_locked", r3dec.get("P4_authorized") is False)

        stage = "R4R1_authority"
        r4r1dir = drive / R4R1_REL
        gate("R4R1_dir_exists", r4r1dir.is_dir(), str(r4r1dir))
        for fn in [R4R1_SUMMARY, R4R1_DECISION, R4R1_RESULT, R4R1_MANIFEST]:
            gate(f"R4R1_artifact_present:{fn}", (r4r1dir / fn).is_file())
        verify_manifest(r4r1dir, R4R1_MANIFEST)
        r4r1sum = js(r4r1dir / R4R1_SUMMARY)
        r4r1dec = js(r4r1dir / R4R1_DECISION)
        r4r1result = js(r4r1dir / R4R1_RESULT)
        gate("R4R1_status_exact", r4r1sum.get("status") == R4R1_STATUS, r4r1sum.get("status"))
        gate("R4R1_classification_exact", r4r1sum.get("classification") == R4R1_CLASS, r4r1sum.get("classification"))
        gate("R4R1_global_optimum_certified",
             r4r1result.get("global_optimality_certified_by_dual_pricing") is True,
             r4r1result.get("global_optimality_certified_by_dual_pricing"))
        gate("R4R1_ten_step_implementation_authorized",
             r4r1dec.get("positive_halo_column_generation_ten_step_implementation_authorized") is True)
        gate("R4R1_day370_locked", r4r1dec.get("Day365_to_Day370_repaired_pilot_authorized") is False)
        gate("R4R1_full_rerun_locked", r4r1dec.get("P3_R1_full_rerun_authorized") is False)
        gate("R4R1_P4_locked", r4r1dec.get("P4_authorized") is False)

        stage = "R4R2_authority"
        r4r2dir = drive / R4R2_REL
        gate("R4R2_dir_exists", r4r2dir.is_dir(), str(r4r2dir))
        for fn in [R4R2_SUMMARY, R4R2_DECISION, R4R2_AUDIT, R4R2_MANIFEST]:
            gate(f"R4R2_artifact_present:{fn}", (r4r2dir / fn).is_file())
        verify_manifest(r4r2dir, R4R2_MANIFEST)
        r4r2sum = js(r4r2dir / R4R2_SUMMARY)
        r4r2dec = js(r4r2dir / R4R2_DECISION)
        gate("R4R2_status_exact", r4r2sum.get("status") == R4R2_STATUS, r4r2sum.get("status"))
        gate("R4R2_classification_exact", r4r2sum.get("classification") == R4R2_CLASS, r4r2sum.get("classification"))
        gate("R4R2_all_ten_steps_certified", r4r2sum.get("all_ten_steps_certified") is True)
        gate("R4R2_no_generic_fallback", int(r4r2sum.get("generic_XY1_fallback_step_count")) == 0)
        gate("R4R2_Day370_pilot_authorized", r4r2dec.get("Day365_to_Day370_repaired_pilot_authorized") is True)
        gate("R4R2_full_rerun_locked", r4r2dec.get("P3_R1_full_rerun_authorized") is False)
        gate("R4R2_P4_locked", r4r2dec.get("P4_authorized") is False)

        stage = "R5_checkpoint_authority"
        r5_cp = drive / R5_STAGE_REL / R5_SOURCE_CHECKPOINT
        r5_cp_meta = drive / R5_STAGE_REL / R5_SOURCE_CHECKPOINT_META
        r5_step_audit = drive / R5_STAGE_REL / R5_SOURCE_STEP_AUDIT
        r5_block = drive / R5_BLOCK_REL / R5_BLOCK_FILE
        gate("R5_source_checkpoint_exists", r5_cp.is_file(), str(r5_cp))
        gate("R5_source_checkpoint_meta_exists", r5_cp_meta.is_file(), str(r5_cp_meta))
        gate("R5_source_step_audit_exists", r5_step_audit.is_file(), str(r5_step_audit))
        gate("R5_BLOCK_exists", r5_block.is_file(), str(r5_block))
        r5meta = js(r5_cp_meta)
        r5b = js(r5_block)
        gate("R5_source_checkpoint_SHA_exact", sha(r5_cp) == R5_SOURCE_CHECKPOINT_SHA, sha(r5_cp))
        gate("R5_source_checkpoint_meta_SHA_exact", r5meta.get("checkpoint_sha256") == R5_SOURCE_CHECKPOINT_SHA, r5meta.get("checkpoint_sha256"))
        gate("R5_source_checkpoint_day_exact", abs(float(r5meta.get("physical_day")) - R5_SOURCE_DAY) <= 1.0e-12, r5meta.get("physical_day"))
        gate("R5_source_checkpoint_steps_exact", int(r5meta.get("accepted_atomic_steps")) == R5_SOURCE_ACCEPTED_STEPS, r5meta.get("accepted_atomic_steps"))
        gate("R5_BLOCK_status_exact", r5b.get("status") == R5_BLOCK_STATUS, r5b.get("status"))
        gate("R5_BLOCK_no_authoritative_mutation",
             r5b.get("authoritative_physics_state_mutated") is False
             and r5b.get("authoritative_physical_time_advanced") is False)

        stage = "R5R1R1_authority"
        r5r1r1dir = drive / R5R1R1_REL
        gate("R5R1R1_dir_exists", r5r1r1dir.is_dir(), str(r5r1r1dir))
        for fn in [R5R1R1_SUMMARY, R5R1R1_DECISION, R5R1R1_RESULT, R5R1R1_MANIFEST]:
            gate(f"R5R1R1_artifact_present:{fn}", (r5r1r1dir / fn).is_file())
        verify_manifest(r5r1r1dir, R5R1R1_MANIFEST)
        r5r1r1sum = js(r5r1r1dir / R5R1R1_SUMMARY)
        r5r1r1dec = js(r5r1r1dir / R5R1R1_DECISION)
        r5r1r1res = js(r5r1r1dir / R5R1R1_RESULT)
        gate("R5R1R1_status_exact", r5r1r1sum.get("status") == R5R1R1_STATUS, r5r1r1sum.get("status"))
        gate("R5R1R1_classification_exact", r5r1r1sum.get("classification") == R5R1R1_CLASS, r5r1r1sum.get("classification"))
        gate("R5R1R1_global_optimum_certified", r5r1r1res.get("global_optimality_certified") is True)
        gate("R5R1R1_resume_repair_authorized", r5r1r1dec.get("R5_checkpoint_resume_repair_authorized") is True)
        gate("R5R1R1_restart_from_Day365_forbidden", r5r1r1dec.get("restart_from_Day365_authorized") is False)
        gate("R5R1R1_full_rerun_locked", r5r1r1dec.get("P3_R1_full_rerun_authorized") is False)
        gate("R5R1R1_P4_locked", r5r1r1dec.get("P4_authorized") is False)

        stage = "R5R2_Day370_authority"
        r5r2dir = drive / R5R2_REL
        gate("R5R2_dir_exists", r5r2dir.is_dir(), str(r5r2dir))
        for fn in [R5R2_SUMMARY, R5R2_DECISION, R5R2_STATE, R5R2_DIAGNOSTIC, R5R2_AUDIT, R5R2_MANIFEST]:
            gate(f"R5R2_artifact_present:{fn}", (r5r2dir / fn).is_file())
        verify_manifest(r5r2dir, R5R2_MANIFEST)
        r5r2sum = js(r5r2dir / R5R2_SUMMARY)
        r5r2dec = js(r5r2dir / R5R2_DECISION)
        source_state_path = r5r2dir / R5R2_STATE
        source_diagnostic_path = r5r2dir / R5R2_DIAGNOSTIC

        gate("R5R2_status_exact", r5r2sum.get("status") == R5R2_STATUS, r5r2sum.get("status"))
        gate("R5R2_classification_exact", r5r2sum.get("classification") == R5R2_CLASS, r5r2sum.get("classification"))
        gate("R5R2_Day370_state_SHA_exact", sha(source_state_path) == R5R2_STATE_SHA, sha(source_state_path))
        gate("R5R2_Day370_diagnostic_SHA_exact", sha(source_diagnostic_path) == R5R2_DIAGNOSTIC_SHA, sha(source_diagnostic_path))
        gate("R5R2_Day370_state_summary_SHA_exact", r5r2sum.get("Day370_state_sha256") == R5R2_STATE_SHA, r5r2sum.get("Day370_state_sha256"))
        gate("R5R2_Day370_diagnostic_summary_SHA_exact", r5r2sum.get("Day370_diagnostic_sha256") == R5R2_DIAGNOSTIC_SHA, r5r2sum.get("Day370_diagnostic_sha256"))
        gate("R5R2_Day375_pilot_authorized", r5r2dec.get("Day370_to_Day375_repaired_pilot_authorized") is True)
        gate("R5R2_diagnostic_one_shot_no_feedback", r5r2dec.get("Day370_exact_diagnostic_is_one_shot_no_feedback") is True)
        gate("R5R2_no_generic_fallback", int(r5r2sum.get("generic_XY1_fallback_step_count")) == 0)
        gate("R5R2_full_rerun_locked", r5r2dec.get("P3_R1_full_rerun_authorized") is False)
        gate("R5R2_P4_locked", r5r2dec.get("P4_authorized") is False)

        stage = "R6R1_closure_authority"
        r6r1dir = drive / R6R1_REL
        gate("R6R1_dir_exists", r6r1dir.is_dir(), str(r6r1dir))
        for fn in [R6R1_SUMMARY, R6R1_DECISION, R6R1_AUDIT, R6R1_MANIFEST]:
            gate(f"R6R1_artifact_present:{fn}", (r6r1dir / fn).is_file())
        verify_manifest(r6r1dir, R6R1_MANIFEST)
        r6r1sum = js(r6r1dir / R6R1_SUMMARY)
        r6r1dec = js(r6r1dir / R6R1_DECISION)
        gate("R6R1_status_exact", r6r1sum.get("status") == R6R1_STATUS, r6r1sum.get("status"))
        gate("R6R1_classification_exact", r6r1sum.get("classification") == R6R1_CLASS, r6r1sum.get("classification"))
        gate("R6R1_science_PASS_authoritative", r6r1dec.get("R6_science_PASS_remains_authoritative") is True)
        gate("R6R1_Day375_state_authoritative", r6r1dec.get("R6_Day375_state_remains_authoritative") is True)
        gate("R6R1_Day375_diagnostic_authoritative", r6r1dec.get("R6_Day375_diagnostic_remains_authoritative") is True)
        gate("R6R1_prior_BLOCK_not_scientific", r6r1dec.get("R6_prior_BLOCK_is_scientific_failure") is False)
        gate("R6R1_transport_rerun_not_required", r6r1dec.get("R6_transport_rerun_required") is False)
        gate("R6R1_Day380_pilot_authorized", r6r1dec.get("Day375_to_Day380_repaired_pilot_authorized") is True)
        gate("R6R1_full_rerun_locked", r6r1dec.get("P3_R1_full_rerun_authorized") is False)
        gate("R6R1_P4_locked", r6r1dec.get("P4_authorized") is False)

        stage = "R6_Day375_science_authority"
        r6srcdir = drive / R6SRC_REL
        gate("R6SRC_dir_exists", r6srcdir.is_dir(), str(r6srcdir))
        for fn in [R6SRC_SUMMARY, R6SRC_DECISION, R6SRC_STATE, R6SRC_DIAGNOSTIC, R6SRC_AUDIT, R6SRC_MANIFEST]:
            gate(f"R6SRC_artifact_present:{fn}", (r6srcdir / fn).is_file())
        verify_manifest(r6srcdir, R6SRC_MANIFEST)
        r6srcsum = js(r6srcdir / R6SRC_SUMMARY)
        r6srcdec = js(r6srcdir / R6SRC_DECISION)
        source_state_path = r6srcdir / R6SRC_STATE
        source_diagnostic_path = r6srcdir / R6SRC_DIAGNOSTIC
        gate("R6SRC_status_exact", r6srcsum.get("status") == R6SRC_STATUS, r6srcsum.get("status"))
        gate("R6SRC_classification_exact", r6srcsum.get("classification") == R6SRC_CLASS, r6srcsum.get("classification"))
        gate("R6SRC_Day375_state_SHA_exact", sha(source_state_path) == R6SRC_STATE_SHA, sha(source_state_path))
        gate("R6SRC_Day375_diagnostic_SHA_exact", sha(source_diagnostic_path) == R6SRC_DIAGNOSTIC_SHA, sha(source_diagnostic_path))
        gate("R6SRC_Day375_state_summary_SHA_exact", r6srcsum.get("Day375_state_sha256") == R6SRC_STATE_SHA, r6srcsum.get("Day375_state_sha256"))
        gate("R6SRC_Day375_diagnostic_summary_SHA_exact", r6srcsum.get("Day375_diagnostic_sha256") == R6SRC_DIAGNOSTIC_SHA, r6srcsum.get("Day375_diagnostic_sha256"))
        gate("R6SRC_Day380_pilot_authorized", r6srcdec.get("Day375_to_Day380_repaired_pilot_authorized") is True)
        gate("R6SRC_diagnostic_one_shot_no_feedback", r6srcdec.get("Day375_exact_diagnostic_is_one_shot_no_feedback") is True)
        gate("R6SRC_no_generic_fallback", int(r6srcsum.get("generic_XY1_fallback_step_count")) == 0)
        gate("R6SRC_full_rerun_locked", r6srcdec.get("P3_R1_full_rerun_authorized") is False)
        gate("R6SRC_P4_locked", r6srcdec.get("P4_authorized") is False)

        stage = "R7_checkpoint_and_BLOCK_authority"
        r7_source_checkpoint = drive / R7_SOURCE_STAGE_REL / R7_SOURCE_CHECKPOINT
        r7_source_checkpoint_meta = drive / R7_SOURCE_STAGE_REL / R7_SOURCE_CHECKPOINT_META
        r7_source_block = drive / R7_SOURCE_BLOCK_REL / R7_SOURCE_BLOCK_FILE
        gate("R7_source_checkpoint_exists", r7_source_checkpoint.is_file(), str(r7_source_checkpoint))
        gate("R7_source_checkpoint_meta_exists", r7_source_checkpoint_meta.is_file(), str(r7_source_checkpoint_meta))
        gate("R7_source_BLOCK_exists", r7_source_block.is_file(), str(r7_source_block))
        r7meta = js(r7_source_checkpoint_meta)
        r7block = js(r7_source_block)
        gate("R7_source_checkpoint_SHA_exact", sha(r7_source_checkpoint) == R7_SOURCE_CHECKPOINT_SHA, sha(r7_source_checkpoint))
        gate("R7_source_checkpoint_meta_SHA_exact", r7meta.get("checkpoint_sha256") == R7_SOURCE_CHECKPOINT_SHA, r7meta.get("checkpoint_sha256"))
        gate("R7_source_checkpoint_day_exact", abs(float(r7meta.get("physical_day")) - R7_SOURCE_DAY) <= 1.0e-12, r7meta.get("physical_day"))
        gate("R7_source_checkpoint_steps_exact", int(r7meta.get("accepted_atomic_steps")) == R7_SOURCE_ACCEPTED_STEPS, r7meta.get("accepted_atomic_steps"))
        gate("R7_source_BLOCK_status_exact", r7block.get("status") == R7_SOURCE_BLOCK_STATUS, r7block.get("status"))
        gate("R7_source_BLOCK_no_authoritative_mutation",
             r7block.get("authoritative_physics_state_mutated") is False
             and r7block.get("authoritative_physical_time_advanced") is False)
        source_state_path = r7_source_checkpoint

        stage = "R7R4R1_implementation_authority"
        r7r4r1dir = drive / R7R4R1_REL
        gate("R7R4R1_dir_exists", r7r4r1dir.is_dir(), str(r7r4r1dir))
        for fn in [R7R4R1_SUMMARY, R7R4R1_DECISION, R7R4R1_IMPLEMENTATION, R7R4R1_REPLAY, R7R4R1_MANIFEST]:
            gate(f"R7R4R1_artifact_present:{fn}", (r7r4r1dir / fn).is_file())
        verify_manifest(r7r4r1dir, R7R4R1_MANIFEST)
        r7r4r1sum = js(r7r4r1dir / R7R4R1_SUMMARY)
        r7r4r1dec = js(r7r4r1dir / R7R4R1_DECISION)
        r7r4r1impl = js(r7r4r1dir / R7R4R1_IMPLEMENTATION)
        r7r4r1replay = js(r7r4r1dir / R7R4R1_REPLAY)
        gate("R7R4R1_status_exact", r7r4r1sum.get("status") == R7R4R1_STATUS, r7r4r1sum.get("status"))
        gate("R7R4R1_classification_exact", r7r4r1sum.get("classification") == R7R4R1_CLASS, r7r4r1sum.get("classification"))
        gate("R7R4R1_global_Stage2_certified", r7r4r1dec.get("global_Stage2_optimality_certified") is True)
        gate("R7R4R1_resume_transport_authorized", r7r4r1dec.get("R7_checkpoint_resume_transport_authorized") is True)
        gate("R7R4R1_XY2_recurrent_authorized", r7r4r1dec.get("XY2_execution_in_recurrent_transport_authorized") is True)
        gate("R7R4R1_Day380_authorized", r7r4r1dec.get("Day380_repaired_pilot_authorized") is True)
        gate("R7R4R1_full_P3R1_locked", r7r4r1dec.get("P3_R1_full_rerun_authorized") is False)
        gate("R7R4R1_P4_locked", r7r4r1dec.get("P4_authorized") is False)
        migration_contract = r7r4r1impl.get("checkpoint_migration", {})
        recurrent_contract = r7r4r1impl.get("recurrent_execution_contract", {})
        gate("R7R4R1_migration_no_state_change", migration_contract.get("physical_state_changed_by_migration") is False)
        gate("R7R4R1_XY2_parent_mass_zero", migration_contract.get("XY2_parent_state_mass_initialized_to_zero") is True)
        gate("R7R4R1_existing_order_preserved", migration_contract.get("existing_exact_plus_XY1_edge_order_preserved") is True)
        gate("R7R4R1_restart_Day375_forbidden", migration_contract.get("restart_from_Day375_forbidden") is True)
        gate("R7R4R1_carry_forward_contract_exact",
             recurrent_contract.get("carry_forward_terminal_seed") == "Stage1-positive XY1/XY2 UNION prior accepted positive XY1/XY2")
        gate("R7R4R1_pricing_domain_exact",
             recurrent_contract.get("omitted_pricing_domain") == "all unselected XY1+XY2 terminal edges")
        gate("R7R4R1_replay_min_RC_zero",
             abs(float(r7r4r1replay.get("final_minimum_omitted_reduced_cost"))) <= 1.0e-12,
             r7r4r1replay.get("final_minimum_omitted_reduced_cost"))

        stage = "R7R5_Day380_authority"
        r7r5dir = drive / R7R5_REL
        gate("R7R5_dir_exists", r7r5dir.is_dir(), str(r7r5dir))
        for fn in [R7R5_SUMMARY, R7R5_DECISION, R7R5_STATE, R7R5_DIAGNOSTIC, R7R5_AUDIT, R7R5_MANIFEST]:
            gate(f"R7R5_artifact_present:{fn}", (r7r5dir / fn).is_file())
        verify_manifest(r7r5dir, R7R5_MANIFEST)
        r7r5sum = js(r7r5dir / R7R5_SUMMARY)
        r7r5dec = js(r7r5dir / R7R5_DECISION)
        source_state_path = r7r5dir / R7R5_STATE
        source_diagnostic_path = r7r5dir / R7R5_DIAGNOSTIC
        gate("R7R5_status_exact", r7r5sum.get("status") == R7R5_STATUS, r7r5sum.get("status"))
        gate("R7R5_classification_exact", r7r5sum.get("classification") == R7R5_CLASS, r7r5sum.get("classification"))
        gate("R7R5_Day380_state_SHA_exact", sha(source_state_path) == R7R5_STATE_SHA, sha(source_state_path))
        gate("R7R5_Day380_diagnostic_SHA_exact", sha(source_diagnostic_path) == R7R5_DIAGNOSTIC_SHA, sha(source_diagnostic_path))
        gate("R7R5_Day380_state_summary_SHA_exact", r7r5sum.get("Day380_state_sha256") == R7R5_STATE_SHA, r7r5sum.get("Day380_state_sha256"))
        gate("R7R5_Day380_diagnostic_summary_SHA_exact", r7r5sum.get("Day380_diagnostic_sha256") == R7R5_DIAGNOSTIC_SHA, r7r5sum.get("Day380_diagnostic_sha256"))
        gate("R7R5_Day385_authorized", r7r5dec.get("Day380_to_Day385_repaired_pilot_authorized") is True)
        gate("R7R5_diagnostic_one_shot_no_feedback", r7r5dec.get("Day380_exact_diagnostic_is_one_shot_no_feedback") is True)
        gate("R7R5_schema2_authoritative", r7r5dec.get("schema_v2_recurrent_support_authoritative") is True)
        gate("R7R5_XY2_execution_executed", r7r5dec.get("XY2_execution_in_recurrent_transport_executed") is True)
        gate("R7R5_no_segment_generic_fallback", int(r7r5sum.get("segment_generic_XY2_fallback_step_count")) == 0)
        gate("R7R5_full_P3R1_locked", r7r5dec.get("P3_R1_full_rerun_authorized") is False)
        gate("R7R5_P4_locked", r7r5dec.get("P4_authorized") is False)

        stage = "partial_P3R1_evidence"
        day365_state_path = drive / P3R1_STAGE_REL / P3R1_DAY365_STATE
        gate("P3R1_Day365_partial_state_exists", day365_state_path.is_file(), str(day365_state_path))
        gate("P3R1_Day365_partial_state_SHA_matches_R3",
             sha(day365_state_path) == r3sum.get("P3R1_partial_Day365_state_sha256"),
             sha(day365_state_path))

        stage = "authoritative_inputs"
        a2ep = drive / p3.A2E_REL / p3.A2E_EPOCH
        a6ep = drive / p3.A6E_REL / p3.A6E_STATE
        gate("A2E_epoch_exists", a2ep.is_file(), str(a2ep))
        gate("A2E_epoch_SHA_exact", sha(a2ep) == p3.A2E_EPOCH_SHA, sha(a2ep))
        gate("A6E_state_exists", a6ep.is_file(), str(a6ep))
        gate("A6E_state_SHA_exact", sha(a6ep) == p3.A6E_SHA, sha(a6ep))
        for fn, expected in [
            (p3.A2E, p3.A2E_BLOB),
            (p3.R2SRC, p3.R2SRC_BLOB),
            (p3.E37A, p3.E37A_BLOB),
            (p3.SG2, p3.SG2_BLOB),
            (p3.SG3, p3.SG3_BLOB),
            (p3.SG4, p3.SG4_BLOB),
            (p3.SG5, p3.SG5_BLOB),
            (p3.SG6, p3.SG6_BLOB),
            (p3.SG7A, p3.SG7A_BLOB),
            (p3.SG7D, p3.SG7D_BLOB),
            (p3.R3R2R1, p3.R3R2R1_BLOB),
            (p3.PERM, p3.PERM_BLOB),
        ]:
            fp = root / fn
            gate(f"{Path(fn).stem}_present", fp.is_file(), str(fp))
            gate(f"{Path(fn).stem}_blob_exact", gt(root, "hash-object", str(fp)) == expected, gt(root, "hash-object", str(fp)))

        a2e = load_module(root / p3.A2E, "p3r1r7_a2e")
        r2src = load_module(root / p3.R2SRC, "p3r1r7_r2src")
        e37a = load_module(root / p3.E37A, "p3r1r7_e37a")
        sg2 = load_module(root / p3.SG2, "p3r1r7_sg2")
        sg3 = load_module(root / p3.SG3, "p3r1r7_sg3")
        sg4 = load_module(root / p3.SG4, "p3r1r7_sg4")
        sg5 = load_module(root / p3.SG5, "p3r1r7_sg5")
        sg6 = load_module(root / p3.SG6, "p3r1r7_sg6")
        sg7a = load_module(root / p3.SG7A, "p3r1r7_sg7a")
        sg7d = load_module(root / p3.SG7D, "p3r1r7_sg7d")
        r3r2r1 = load_module(root / p3.R3R2R1, "p3r1r7_r3r2r1")

        with np.load(a2ep, allow_pickle=False) as z:
            frozen_pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
            tof_s = np.asarray(z["streamline_tof_s"], dtype=np.float64)
            weights_m3_s = np.asarray(z["streamline_weight_m3_s"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            tau_end_s = np.asarray(z["tau_end_s"], dtype=np.float64)
        with np.load(a6ep, allow_pickle=False) as z:
            phi = np.asarray(z["paired_porosity"], dtype=np.float64)
            nw = np.asarray(z["nw"], dtype=np.float64)
            no = np.asarray(z["no"], dtype=np.float64)
            krw_max = np.asarray(z["krw_max"], dtype=np.float64)
            kro_max = np.asarray(z["kro_max"], dtype=np.float64)
        with np.load(day365_state_path, allow_pickle=False) as z:
            day365_initial_total_mass = float(np.sum(np.asarray(z["cartesian_component_mass_kg"], dtype=np.float64)))

        with np.load(source_state_path, allow_pickle=False) as z:
            gate("R7R5_source_state_schema2", int(np.asarray(z["state_schema_version"]).reshape(())) == 2)
            gate("R7R5_source_root_checkpoint_exact",
                 str(np.asarray(z["source_R7_checkpoint_sha256"]).reshape(())) == R7_SOURCE_CHECKPOINT_SHA,
                 str(np.asarray(z["source_R7_checkpoint_sha256"]).reshape(())))
            physical_day = float(np.asarray(z["physical_day"]).reshape(()))
            current_grid_mass = np.asarray(z["cartesian_component_mass_kg"], dtype=np.float64)
            current_rep = np.asarray(z["represented_cartesian_cell_mass_kg"], dtype=np.float64)
            current_residual = np.asarray(z["grid_residual_component_mass_kg"], dtype=np.float64)
            current_cv_mass = np.asarray(z["transport_CV_component_mass_kg"], dtype=np.float64)
            current_cv_sat = np.asarray(z["transport_CV_saturation"], dtype=np.float64)
            current_cart_sat = np.asarray(z["cartesian_saturation"], dtype=np.float64)
            source_frozen_flow_epoch_day = float(np.asarray(z["frozen_flow_epoch_day"]).reshape(()))
            source_cumulative_injected = float(np.asarray(z["cumulative_injected_component_mass_kg"]).reshape(()))
            source_cumulative_produced = float(np.asarray(z["cumulative_produced_component_mass_kg"]).reshape(()))
            edge_cv = np.asarray(z["support_edge_cv"], dtype=np.int64)
            edge_cell = np.asarray(z["support_edge_cell"], dtype=np.int64)
            shell = np.asarray(z["support_edge_terminal_cost"], dtype=np.int8)
            ring = np.asarray(z["support_edge_ring"], dtype=np.int8)
            current_edge_mass = np.asarray(z["support_edge_assigned_mass_kg"], dtype=np.float64)

        source_accepted_atomic_steps = int(r7r5sum.get("accepted_atomic_steps"))
        source_direct_count = int(r7r5sum.get("direct_step_count"))
        source_reduced_count = int(r7r5sum.get("zero_halo_reduced_fast_path_step_count"))
        source_positive_halo_cg_count = int(r7r5sum.get("positive_halo_column_generation_step_count"))
        source_fallback_count = int(r7r5sum.get("generic_XY2_fallback_step_count"))
        source_total_cg_iterations = int(r7r5sum.get("total_column_generation_iterations"))
        source_maximum_selected_shell_edge_count = int(r7r5sum.get("maximum_selected_terminal_edge_count"))
        source_retry_count_total = int(r7r5sum.get("retry_count_total"))

        gate("physical_day_Day380_exact", abs(physical_day - R7R5_SOURCE_DAY) <= 1.0e-12, physical_day)
        gate("accepted_steps_Day380_exact", source_accepted_atomic_steps == R7R5_ACCEPTED_STEPS, source_accepted_atomic_steps)
        gate("source_frozen_transport_flow_epoch_day365", abs(source_frozen_flow_epoch_day - 365.0) <= 1.0e-12, source_frozen_flow_epoch_day)
        gate("source_schema2_total_edge_count_exact", int(edge_cv.size) == EXPECTED_TOTAL_EDGE_COUNT, int(edge_cv.size))
        gate("source_schema2_support_lengths_exact",
             edge_cell.size == edge_cv.size == shell.size == ring.size == current_edge_mass.size)
        gate("source_schema2_ring_values_exact", set(np.unique(ring).tolist()).issubset({0, 1, 2}), np.unique(ring).tolist())
        gate("source_schema2_exact_support_terminal_cost_zero", bool(np.all(shell[ring == 0] == 0)))
        gate("source_schema2_terminal_support_cost_one", bool(np.all(shell[ring > 0] == 1)))
        gate("source_Day380_positive_XY1_count_exact",
             int(np.count_nonzero((ring == 1) & (current_edge_mass > POSITIVE_EDGE_TOL))) ==
             int(r7r5sum.get("Day380_positive_XY1_terminal_edge_count")))
        gate("source_Day380_positive_XY2_count_exact",
             int(np.count_nonzero((ring == 2) & (current_edge_mass > POSITIVE_EDGE_TOL))) ==
             int(r7r5sum.get("Day380_positive_XY2_terminal_edge_count")))
        source_rep_from_edges = np.bincount(edge_cell, weights=current_edge_mass, minlength=p3.NCELL).reshape(p3.GRID)
        source_cv_from_edges = np.bincount(edge_cv, weights=current_edge_mass, minlength=p3.NCVT).reshape(p3.NSL, p3.NCV)
        gate("source_schema2_representation_identity",
             float(np.max(np.abs(source_rep_from_edges - current_rep))) <= MASS_TOL,
             float(np.max(np.abs(source_rep_from_edges - current_rep))))
        gate("source_schema2_CV_identity",
             float(np.max(np.abs(source_cv_from_edges - current_cv_mass))) <= MASS_TOL,
             float(np.max(np.abs(source_cv_from_edges - current_cv_mass))))

        initial_total_mass = day365_initial_total_mass
        source_ledger_residual = float(np.sum(current_grid_mass)) - (
            initial_total_mass + source_cumulative_injected - source_cumulative_produced
        )
        gate("Day380_source_mass_ledger_closes",
             abs(source_ledger_residual) <= max(MASS_TOL, REL_TOL * max(abs(float(np.sum(current_grid_mass))), 1.0)),
             source_ledger_residual)

        hetero_pv = phi * float(a2e.BULK_VOLUME_M3)
        if current_cart_sat is None:
            current_cart_sat = float(a2e.BACKGROUND) + np.asarray(
                a2e.invert_local_mass(r2src, current_grid_mass, frozen_pressure, p_ref, hetero_pv),
                dtype=np.float64,
            )
        permeability_md = np.loadtxt(root / p3.PERM, skiprows=1, dtype=np.float64).reshape(p3.GRID, order="C")
        kx, ky, kz = sg2.build_directional_permeability(permeability_md)
        kfx, kfy, kfz = sg2.build_face_permeabilities(kx, ky, kz)
        tx_ref, ty_ref, tz_ref = sg3.construct_si_transmissibilities(kfx, kfy, kfz)
        op = sg7d.build_subsegment_operator(xyz, tof_s / DAY_TO_S, weights_m3_s * DAY_TO_S)
        geometry = e37a.build_control_volume_geometry(r2src, op, frozen_pressure, p_ref, p3.NSL, p3.NCV)
        xi_faces = np.linspace(0.0, 1.0, p3.NCV + 1, dtype=np.float64)
        weights_m3_day = weights_m3_s * DAY_TO_S
        sat_scan = np.linspace(float(sg7a.S_INITIAL), float(sg7a.S_INJECTED), 4001)
        max_df = float(np.max(np.abs(np.asarray(sg7a.df_dS(sat_scan), dtype=np.float64))))
        u_face = np.asarray(sg7a.u_dimensionless(xi_faces), dtype=np.float64)
        dtD = float(sg7a.CFL * (1.0 / p3.NCV) / (float(np.max(u_face)) * max_df + float(sg7a.EPS)))
        nominal_dt = float(dtD * np.min(tau_end_s / DAY_TO_S))
        gate("nominal_dt_matches_certified_P3R1_first_step",
             abs(nominal_dt - 0.03730130768843055) <= 1.0e-14,
             nominal_dt)
        gate("nominal_dt_positive", np.isfinite(nominal_dt) and nominal_dt > 0.0, nominal_dt)

        sub_pv = np.asarray(geometry["pv_m3"], dtype=np.float64)
        pseg = np.asarray(geometry["pseg_psi"], dtype=np.float64)
        flat_cell = np.asarray(geometry["flat_cell"], dtype=np.int64)
        geom_cv_id = np.asarray(geometry["cv_id"], dtype=np.int64)
        rho_ref = float(e37a.CO2_RHO_REF_KG_M3)

        full_sat = np.full(p3.GRID, float(a2e.INJECTED), dtype=np.float64)
        cart_capacity = np.asarray(a2e.local_mass(r2src, full_sat, frozen_pressure, p_ref, hetero_pv), dtype=np.float64)
        cart_cap_tol = max(1.0e-8, 1.0e-12 * max(float(np.max(cart_capacity)), 1.0))

        # R7-R5 Day380 state is already authoritative schema-v2 support.
        gate("schema2_source_total_edge_count_exact", int(edge_cv.size) == EXPECTED_TOTAL_EDGE_COUNT, int(edge_cv.size))
        gate("schema2_source_XY2_edge_count_exact",
             int(np.count_nonzero(ring == 2)) == EXPECTED_XY2_NEW_EDGE_COUNT,
             int(np.count_nonzero(ring == 2)))
        gate("schema2_source_existing_exact_XY1_count_exact",
             int(np.count_nonzero(ring != 2)) == EXPECTED_EXISTING_EDGE_COUNT,
             int(np.count_nonzero(ring != 2)))

        exact_mask = shell == 0
        ex_cv = edge_cv[exact_mask]
        ex_cell = edge_cell[exact_mask]
        exact_positions = np.where(exact_mask)[0]
        nex = int(ex_cv.size)
        active_cells = np.unique(ex_cell)
        nactive = int(active_cells.size)
        active_lookup = np.full(p3.NCELL, -1, dtype=np.int64)
        active_lookup[active_cells] = np.arange(nactive, dtype=np.int64)
        ex_active_cell = active_lookup[ex_cell]
        inactive_mask = np.ones(p3.NCELL, dtype=bool)
        inactive_mask[active_cells] = False

        ex_idx = np.arange(nex, dtype=np.int64)
        Aeq_exact = coo_matrix(
            (np.ones(nex, dtype=np.float64), (ex_cv, ex_idx)),
            shape=(p3.NCVT, nex),
        ).tocsr()
        Acell_exact_active = coo_matrix(
            (np.ones(nex, dtype=np.float64), (ex_active_cell, ex_idx)),
            shape=(nactive, nex),
        ).tocsr()

        # Full support matrices only for fallback.
        nedge = len(edge_cv)
        all_idx = np.arange(nedge, dtype=np.int64)
        Aeq_full = coo_matrix(
            (np.ones(nedge, dtype=np.float64), (edge_cv, all_idx)),
            shape=(p3.NCVT, nedge),
        ).tocsr()
        Acell_full = coo_matrix(
            (np.ones(nedge, dtype=np.float64), (edge_cell, all_idx)),
            shape=(p3.NCELL, nedge),
        ).tocsr()
        c1_full = (shell > 0).astype(np.float64)

        # Exact subsegment -> saved support-edge mapping.
        edge_keys = edge_cv * p3.NCELL + edge_cell
        key_to_edge = {int(k): i for i, k in enumerate(edge_keys.tolist())}
        sub_cv = np.asarray(op["streamline"], dtype=np.int64) * p3.NCV + np.asarray(op["node"], dtype=np.int64)
        sub_cell = np.asarray(op["flat_cell"], dtype=np.int64)
        sub_keys = sub_cv * p3.NCELL + sub_cell
        sub_edge_pos = np.asarray([key_to_edge[int(k)] for k in sub_keys.tolist()], dtype=np.int64)
        gate("all_subsegments_on_exact_support", bool(np.all(shell[sub_edge_pos] == 0)))

        # ------------------------------------------------------------------------------
        # Restart-safe pilot state and exact Day380 diagnostic.
        # ------------------------------------------------------------------------------
        day365_state_sha = sha(day365_state_path)

        def atomic_write_bytes(path: Path, payload: bytes) -> None:
            tmp = path.with_name(path.name + ".tmp")
            tmp.write_bytes(payload)
            os.replace(tmp, path)

        def write_checkpoint() -> None:
            arrays = {
                "checkpoint_schema_version": np.asarray(2, dtype=np.int64),
                "base_Day365_state_sha256": np.asarray(day365_state_sha),
                "source_R7_checkpoint_sha256": np.asarray(R7_SOURCE_CHECKPOINT_SHA),
                "source_R7R5_Day380_state_sha256": np.asarray(R7R5_STATE_SHA),
                "physical_day": np.asarray(current_time, dtype=np.float64),
                "accepted_atomic_steps": np.asarray(accepted_atomic_steps, dtype=np.int64),
                "cartesian_component_mass_kg": current_grid_mass,
                "represented_cartesian_cell_mass_kg": current_rep,
                "grid_residual_component_mass_kg": current_residual,
                "cartesian_saturation": current_cart_sat,
                "transport_CV_component_mass_kg": current_cv_mass,
                "transport_CV_saturation": current_cv_sat,
                "support_edge_cv": edge_cv,
                "support_edge_cell": edge_cell,
                "support_edge_terminal_cost": shell,
                "support_edge_ring": ring,
                "support_edge_assigned_mass_kg": current_edge_mass,
                "cumulative_injected_component_mass_kg": np.asarray(cumulative_injected, dtype=np.float64),
                "cumulative_produced_component_mass_kg": np.asarray(cumulative_produced, dtype=np.float64),
                "direct_step_count": np.asarray(direct_count, dtype=np.int64),
                "zero_halo_reduced_step_count": np.asarray(reduced_count, dtype=np.int64),
                "positive_halo_column_generation_step_count": np.asarray(positive_halo_cg_count, dtype=np.int64),
                "generic_XY2_fallback_step_count": np.asarray(fallback_count, dtype=np.int64),
                "total_column_generation_iterations": np.asarray(total_cg_iterations, dtype=np.int64),
                "maximum_selected_terminal_edge_count": np.asarray(maximum_selected_shell_edge_count, dtype=np.int64),
                "retry_count_total": np.asarray(retry_count_total, dtype=np.int64),
            }
            payload = deterministic_npz_bytes(arrays)
            atomic_write_bytes(latest_checkpoint_path, payload)
            meta = {
                "milestone": M,
                "checkpoint_schema_version": 2,
                "base_Day365_state_sha256": day365_state_sha,
                "source_R7_checkpoint_sha256": R7_SOURCE_CHECKPOINT_SHA,
                "source_R7R5_Day380_state_sha256": R7R5_STATE_SHA,
                "physical_day": current_time,
                "accepted_atomic_steps": accepted_atomic_steps,
                "checkpoint_sha256": sha(latest_checkpoint_path),
                "step_audit_sha256": sha(staging / STEP_AUDIT) if (staging / STEP_AUDIT).is_file() else None,
                "target_day": TARGET_DAY,
                "frozen_transport_flow_epoch_day": 365.0,
            }
            atomic_write_bytes(latest_checkpoint_meta_path, jb(meta))
            if accepted_atomic_steps > 0 and accepted_atomic_steps % CHECKPOINT_ARCHIVE_EVERY == 0:
                archive = staging / f"{CHECKPOINT_ARCHIVE_PREFIX}{accepted_atomic_steps:05d}.npz"
                if not archive.exists():
                    archive.write_bytes(payload)

        def run_exact_diagnostic(day: float) -> tuple[dict[str, Any], dict[str, Any]]:
            t0 = time.perf_counter()
            tp = time.perf_counter()
            mobility = a2e.spatial_mobility(current_cart_sat, nw, no, krw_max, kro_max)
            tx, ty, tz, _ = r3r2r1.build_updated_transmissibilities(
                sg3, tx_ref, ty_ref, tz_ref, mobility["lambda_total"]
            )
            A, b, producer_wi = r3r2r1.assemble_updated_pressure_system(
                sg3, permeability_md, tx, ty, tz, mobility["lambda_total"]
            )
            _ppa, diag_pressure, linear_residual = r3r2r1.solve_updated_pressure(sg3, A, b)
            diag_pressure = np.asarray(diag_pressure, dtype=np.float64)
            pressure_refresh_s = time.perf_counter() - tp
            if float(linear_residual) >= float(a2e.PRESSURE_LINEAR_REL_RESIDUAL_MAX):
                raise GateError(f"Day380_pressure_linear_residual:{linear_residual}")

            td = time.perf_counter()
            _producer_rates, producer_sink = r3r2r1.producer_rates_updated(sg3, diag_pressure, producer_wi)
            qx, qy, qz = sg4.compute_face_fluxes(diag_pressure, tx, ty, tz)
            conservation = r3r2r1.flow_conservation_metrics(sg3, sg4, qx, qy, qz, producer_sink)
            if conservation["local_relative_l2_error"] >= float(a2e.FLOW_LOCAL_REL_L2_MAX):
                raise GateError(f"Day380_Darcy_local_conservation:{conservation['local_relative_l2_error']}")
            if conservation["global_relative_mismatch"] >= float(a2e.FLOW_GLOBAL_REL_MISMATCH_MAX):
                raise GateError(f"Day380_Darcy_global_conservation:{conservation['global_relative_mismatch']}")
            darcy_s = time.perf_counter() - td

            tpo = time.perf_counter()
            vx, vy, vz = sg5.construct_face_pore_velocities(qx, qy, qz)
            faces, seeds = sg5.build_seeds(qx, qy, qz)
            streamlines = sg5.trace_streamlines(seeds, vx, vy, vz)
            sg5.validate_streamlines(faces, seeds, streamlines)
            statuses = [str(s["status"]) for s in streamlines]
            if not streamlines or not all(x == "PRODUCER" for x in statuses):
                raise GateError(f"Day380_Pollock_terminal_status:{ {x: statuses.count(x) for x in sorted(set(statuses))} }")
            pollock_s = time.perf_counter() - tpo

            tt = time.perf_counter()
            sg6_streamlines = a2e.convert_sg5_to_sg6(streamlines)
            transport_db = sg6.build_transport_database(sg6_streamlines)
            sg6.validate_transport(transport_db)
            dxyz = np.asarray(transport_db["xyz_m"], dtype=np.float64)
            dtof = np.asarray(transport_db["tau_s"], dtype=np.float64)
            dweights = np.asarray(transport_db["weights_m3_s"], dtype=np.float64)
            dtau_end = np.asarray(transport_db["tau_end_s"], dtype=np.float64)
            dlabels = np.asarray(transport_db["producer"]).astype("U32")
            dxi_nodes = np.asarray(transport_db["xi"], dtype=np.float64)
            tof_s_elapsed = time.perf_counter() - tt
            total = time.perf_counter() - t0
            arrays = {
                "diagnostic_day": np.asarray(day, dtype=np.float64),
                "saturation": np.asarray(current_cart_sat, dtype=np.float64),
                "lambda_total": np.asarray(mobility["lambda_total"], dtype=np.float64),
                "pressure_psi": diag_pressure,
                "Qx": np.asarray(qx, dtype=np.float64),
                "Qy": np.asarray(qy, dtype=np.float64),
                "Qz": np.asarray(qz, dtype=np.float64),
                "streamline_xyz_m": dxyz,
                "streamline_tof_s": dtof,
                "streamline_weight_m3_s": dweights,
                "tau_end_s": dtau_end,
                "producer_labels": dlabels,
                "xi": dxi_nodes,
                "diagnostic_is_same_time_fixed_point": np.asarray(False),
                "diagnostic_transport_feedback": np.asarray(False),
            }
            pressure_vs_day365 = float(
                np.linalg.norm((diag_pressure - frozen_pressure).ravel())
                / max(float(np.linalg.norm(frozen_pressure.ravel())), 1.0e-30)
            )
            metrics = {
                "diagnostic_day": day,
                "pressure_linear_relative_residual": float(linear_residual),
                "pressure_refresh_s": pressure_refresh_s,
                "Darcy_s": darcy_s,
                "Pollock_s": pollock_s,
                "TOF_s": tof_s_elapsed,
                "total_refresh_s": total,
                "pressure_relative_L2_vs_Day365": pressure_vs_day365,
                "pressure_min_psi": float(np.min(diag_pressure)),
                "pressure_max_psi": float(np.max(diag_pressure)),
                "flow_local_relative_L2_error": float(conservation["local_relative_l2_error"]),
                "flow_global_relative_mismatch": float(conservation["global_relative_mismatch"]),
                "streamline_count": int(dxyz.shape[0]),
                "nodes_per_streamline": int(dxyz.shape[1]),
                "tau_end_min_days": float(np.min(dtau_end) / DAY_TO_S),
                "tau_end_median_days": float(np.median(dtau_end) / DAY_TO_S),
                "tau_end_max_days": float(np.max(dtau_end) / DAY_TO_S),
                "diagnostic_same_time_fixed_point_executed": False,
                "diagnostic_transport_feedback_executed": False,
            }
            return arrays, metrics

        # Resume an R7-R6 checkpoint, or seed directly from the formal R7-R5 Day380 schema-v2 accepted state.
        if latest_checkpoint_path.is_file():
            meta = js(latest_checkpoint_meta_path)
            gate("resume_checkpoint_SHA_exact",
                 sha(latest_checkpoint_path) == meta.get("checkpoint_sha256"),
                 sha(latest_checkpoint_path))
            gate("resume_checkpoint_Day365_source_exact",
                 meta.get("base_Day365_state_sha256") == day365_state_sha,
                 meta.get("base_Day365_state_sha256"))
            gate("resume_checkpoint_R7_root_exact",
                 meta.get("source_R7_checkpoint_sha256") == R7_SOURCE_CHECKPOINT_SHA,
                 meta.get("source_R7_checkpoint_sha256"))
            gate("resume_checkpoint_Day380_source_exact",
                 meta.get("source_R7R5_Day380_state_sha256") == R7R5_STATE_SHA,
                 meta.get("source_R7R5_Day380_state_sha256"))
            with np.load(latest_checkpoint_path, allow_pickle=False) as z:
                gate("resume_checkpoint_schema2", int(np.asarray(z["checkpoint_schema_version"]).reshape(())) == 2)
                current_time = float(np.asarray(z["physical_day"]).reshape(()))
                accepted_atomic_steps = int(np.asarray(z["accepted_atomic_steps"]).reshape(()))
                current_grid_mass = np.asarray(z["cartesian_component_mass_kg"], dtype=np.float64)
                current_rep = np.asarray(z["represented_cartesian_cell_mass_kg"], dtype=np.float64)
                current_residual = np.asarray(z["grid_residual_component_mass_kg"], dtype=np.float64)
                current_cart_sat = np.asarray(z["cartesian_saturation"], dtype=np.float64)
                current_cv_mass = np.asarray(z["transport_CV_component_mass_kg"], dtype=np.float64)
                current_cv_sat = np.asarray(z["transport_CV_saturation"], dtype=np.float64)
                gate("resume_support_cv_exact", np.array_equal(np.asarray(z["support_edge_cv"], dtype=np.int64), edge_cv))
                gate("resume_support_cell_exact", np.array_equal(np.asarray(z["support_edge_cell"], dtype=np.int64), edge_cell))
                gate("resume_support_terminal_cost_exact", np.array_equal(np.asarray(z["support_edge_terminal_cost"], dtype=np.int8), shell))
                gate("resume_support_ring_exact", np.array_equal(np.asarray(z["support_edge_ring"], dtype=np.int8), ring))
                current_edge_mass = np.asarray(z["support_edge_assigned_mass_kg"], dtype=np.float64)
                cumulative_injected = float(np.asarray(z["cumulative_injected_component_mass_kg"]).reshape(()))
                cumulative_produced = float(np.asarray(z["cumulative_produced_component_mass_kg"]).reshape(()))
                direct_count = int(np.asarray(z["direct_step_count"]).reshape(()))
                reduced_count = int(np.asarray(z["zero_halo_reduced_step_count"]).reshape(()))
                positive_halo_cg_count = int(np.asarray(z["positive_halo_column_generation_step_count"]).reshape(()))
                fallback_count = int(np.asarray(z["generic_XY2_fallback_step_count"]).reshape(()))
                total_cg_iterations = int(np.asarray(z["total_column_generation_iterations"]).reshape(()))
                maximum_selected_shell_edge_count = int(np.asarray(z["maximum_selected_terminal_edge_count"]).reshape(()))
                retry_count_total = int(np.asarray(z["retry_count_total"]).reshape(()))
            rows = csvr(staging / STEP_AUDIT) if (staging / STEP_AUDIT).is_file() else []
            print(
                f"[R7-R6 RESUME] accepted_steps={accepted_atomic_steps} "
                f"t={current_time:.9f} d checkpoint={sha(latest_checkpoint_path)}",
                flush=True,
            )
        else:
            current_time = physical_day
            accepted_atomic_steps = source_accepted_atomic_steps
            cumulative_injected = source_cumulative_injected
            cumulative_produced = source_cumulative_produced
            direct_count = source_direct_count
            reduced_count = source_reduced_count
            positive_halo_cg_count = source_positive_halo_cg_count
            fallback_count = source_fallback_count
            total_cg_iterations = source_total_cg_iterations
            maximum_selected_shell_edge_count = source_maximum_selected_shell_edge_count
            retry_count_total = source_retry_count_total
            rows: list[dict[str, Any]] = []
            atomic_write_bytes(staging / STEP_AUDIT, csvb(rows))
            write_checkpoint()
            gate("Day380_schema2_seed_time_exact", abs(current_time - R7R5_SOURCE_DAY) <= 1.0e-12, current_time)
            gate("Day380_schema2_seed_steps_exact", accepted_atomic_steps == R7R5_ACCEPTED_STEPS, accepted_atomic_steps)
            print(
                f"[DAY380 SCHEMA-V2 STATE SEED] accepted_steps={accepted_atomic_steps} "
                f"t={current_time:.9f} d state={R7R5_STATE_SHA}",
                flush=True,
            )

        gate("pilot_resume_time_in_range",
             R7R5_SOURCE_DAY - 1.0e-12 <= current_time <= TARGET_DAY + 1.0e-12,
             current_time)

        while current_time < TARGET_DAY - 1.0e-12:
            step = accepted_atomic_steps + 1
            nominal = min(nominal_dt, TARGET_DAY - current_time)
            if not np.isfinite(nominal) or nominal <= 0.0:
                raise GateError(f"nonpositive_nominal_dt:{current_time}:{nominal}")
            accepted = False
            rejection_reasons: list[str] = []
            parent_time = current_time

            for retry in range(MAX_RETRIES + 1):
                dt = nominal * (RETRY_FACTOR ** retry)
                step_start = time.perf_counter()
                mode = ""
                stage1_wall = 0.0
                stage2_wall = 0.0
                positive_halo_stage1_wall = 0.0
                column_generation_stage2_wall = 0.0
                column_generation_iterations = 0
                column_generation_selected_shell_edges = 0
                column_generation_min_omitted_reduced_cost = None
                stage1_positive_shell_edge_count = 0
                prior_accepted_positive_shell_edge_count = 0
                carry_forward_union_shell_edge_count = 0
                fallback_wall = 0.0
                try:
                    old_grid = current_grid_mass
                    old_rep = current_rep
                    old_cv_mass = current_cv_mass
                    old_cv_sat = current_cv_sat
                    old_edge_mass = current_edge_mass

                    theory_flux = np.zeros((p3.NSL, p3.NCV + 1), dtype=np.float64)
                    theory_flux[:, 0] = weights_m3_day * rho_ref
                    ff_internal = np.asarray(sg7a.fractional_flow(old_cv_sat[:, :-1]), dtype=np.float64)
                    theory_flux[:, 1:-1] = weights_m3_day[:, None] * u_face[None, 1:-1] * ff_internal * rho_ref
                    ff_out = np.asarray(sg7a.fractional_flow(old_cv_sat[:, -1]), dtype=np.float64)
                    theory_flux[:, -1] = weights_m3_day * float(u_face[-1]) * ff_out * rho_ref

                    new_cv_mass = old_cv_mass + dt * (theory_flux[:, :-1] - theory_flux[:, 1:])
                    cv_cap_tol = max(1.0e-9, 1.0e-12 * max(float(np.max(np.abs(new_cv_mass))), 1.0))
                    if float(np.min(new_cv_mass)) < -MASS_TOL:
                        raise TrialReject(f"CV_NEGATIVE:{float(np.min(new_cv_mass))}")

                    cv_capacity = np.asarray(
                        e37a.cv_mass_from_saturation(
                            r2src,
                            np.full((p3.NSL, p3.NCV), p3.MAX_SAT, dtype=np.float64),
                            geometry["cv_pressure_mass_coeff"],
                        ),
                        dtype=np.float64,
                    )
                    if float(np.max(new_cv_mass - cv_capacity)) > cv_cap_tol:
                        raise TrialReject(f"CV_CAPACITY:{float(np.max(new_cv_mass - cv_capacity))}:{cv_cap_tol}")

                    new_cv_sat = np.asarray(
                        e37a.invert_cv_mass_to_saturation(r2src, new_cv_mass, geometry["cv_pressure_mass_coeff"]),
                        dtype=np.float64,
                    )
                    if float(np.min(new_cv_sat)) < p3.BACKGROUND - SAT_TOL or float(np.max(new_cv_sat)) > p3.MAX_SAT + SAT_TOL:
                        raise TrialReject(f"CV_SATURATION:{float(np.min(new_cv_sat))}:{float(np.max(new_cv_sat))}")

                    injected = float(np.sum(theory_flux[:, 0]) * dt)
                    produced = float(np.sum(theory_flux[:, -1]) * dt)
                    cv_delta = float(np.sum(new_cv_mass) - np.sum(old_cv_mass))
                    cv_source_sink = cv_delta - injected + produced
                    if abs(cv_source_sink) > max(MASS_TOL, REL_TOL * max(abs(injected), 1.0)):
                        raise TrialReject(f"CV_SOURCE_SINK:{cv_source_sink}")

                    old_sub_sat = old_cv_sat.reshape(-1)[geom_cv_id]
                    new_sub_sat = new_cv_sat.reshape(-1)[geom_cv_id]
                    old_sub_sg = np.clip(old_sub_sat - p3.BACKGROUND, 0.0, p3.MAX_SG)
                    new_sub_sg = np.clip(new_sub_sat - p3.BACKGROUND, 0.0, p3.MAX_SG)
                    rho_old = np.asarray(r2src.gas_density_from_state(old_sub_sat, pseg, p_ref), dtype=np.float64)
                    rho_new = np.asarray(r2src.gas_density_from_state(new_sub_sat, pseg, p_ref), dtype=np.float64)
                    sub_delta = sub_pv * (rho_new * new_sub_sg - rho_old * old_sub_sg)
                    if abs(float(np.sum(sub_delta)) - cv_delta) > MASS_TOL:
                        raise TrialReject(f"SUBSEGMENT_CLOSURE:{float(np.sum(sub_delta)) - cv_delta}")

                    delta_grid = np.bincount(flat_cell, weights=sub_delta, minlength=p3.NCELL).reshape(p3.GRID)
                    direct_target_rep = old_rep + delta_grid
                    rep_capacity = cart_capacity - current_residual
                    rep_capacity_flat = np.maximum(rep_capacity, 0.0).reshape(-1)
                    if float(np.min(rep_capacity)) < -cart_cap_tol:
                        raise TrialReject(f"REP_CAPACITY_NEGATIVE:{float(np.min(rep_capacity))}:{cart_cap_tol}")

                    edge_delta = np.bincount(sub_edge_pos, weights=sub_delta, minlength=nedge)
                    candidate_edge = old_edge_mass + edge_delta
                    direct_mode = float(np.min(candidate_edge)) >= -MASS_TOL

                    if direct_mode:
                        cv_from_edge = np.bincount(edge_cv, weights=candidate_edge, minlength=p3.NCVT).reshape(p3.NSL, p3.NCV)
                        cell_from_edge = np.bincount(edge_cell, weights=candidate_edge, minlength=p3.NCELL).reshape(p3.GRID)
                        cv_err = float(np.max(np.abs(cv_from_edge - new_cv_mass)))
                        cap_excess = float(np.max(cell_from_edge.reshape(-1) - rep_capacity_flat))
                        direct_l1 = float(np.sum(np.abs(cell_from_edge - direct_target_rep)))
                        direct_l1_tol = max(1.0e-5, 1.0e-10 * max(float(np.sum(np.abs(direct_target_rep))), 1.0))
                        if cv_err > MASS_TOL or cap_excess > cart_cap_tol or direct_l1 > direct_l1_tol:
                            direct_mode = False

                    if direct_mode:
                        new_edge_mass = candidate_edge
                        new_rep = np.bincount(edge_cell, weights=new_edge_mass, minlength=p3.NCELL).reshape(p3.GRID)
                        mode = "DIRECT_EDGE_EXACT"
                        stage1_halo = float(np.sum(new_edge_mass[shell > 0]))
                        stage2_l1 = float(np.sum(np.abs(new_rep - direct_target_rep)))
                    else:
                        # Stage1 zero-halo certificate: exact-support feasibility with CV equality and cell capacity.
                        t1 = time.perf_counter()
                        lp0 = linprog(
                            np.zeros(nex, dtype=np.float64),
                            A_ub=Acell_exact_active,
                            b_ub=rep_capacity_flat[active_cells],
                            A_eq=Aeq_exact,
                            b_eq=new_cv_mass.reshape(-1),
                            bounds=(0.0, None),
                            method="highs-ds",
                            options={
                                "presolve": True,
                                "primal_feasibility_tolerance": HIGHS_FEAS_TOL,
                                "dual_feasibility_tolerance": HIGHS_FEAS_TOL,
                                "time_limit": float(time_limit_seconds),
                            },
                        )
                        stage1_wall = time.perf_counter() - t1

                        if lp0.success:
                            # Zero terminal-shell mass is feasible; Stage1 optimum is exactly zero.
                            stage1_halo = 0.0

                            target_flat = direct_target_rep.reshape(-1)
                            target_active = target_flat[active_cells]
                            target_inactive = target_flat[inactive_mask]
                            constant_inactive_l1 = float(np.sum(np.abs(target_inactive)))

                            zero_d = csr_matrix((nactive, nactive), dtype=np.float64)
                            I = eye(nactive, format="csr", dtype=np.float64)
                            A_cap = hstack([Acell_exact_active, zero_d], format="csr")
                            A_abs_pos = hstack([Acell_exact_active, -I], format="csr")
                            A_abs_neg = hstack([-Acell_exact_active, -I], format="csr")
                            A_ub = vstack([A_cap, A_abs_pos, A_abs_neg], format="csr")
                            b_ub = np.concatenate([
                                rep_capacity_flat[active_cells],
                                target_active,
                                -target_active,
                            ])
                            Aeq = hstack([Aeq_exact, csr_matrix((p3.NCVT, nactive), dtype=np.float64)], format="csr")
                            c = np.concatenate([np.zeros(nex), np.ones(nactive)])
                            bounds = [(0.0, None)] * (nex + nactive)

                            t2 = time.perf_counter()
                            lp2 = linprog(
                                c,
                                A_ub=A_ub,
                                b_ub=b_ub,
                                A_eq=Aeq,
                                b_eq=new_cv_mass.reshape(-1),
                                bounds=bounds,
                                method="highs-ds",
                                options={
                                    "presolve": True,
                                    "primal_feasibility_tolerance": HIGHS_FEAS_TOL,
                                    "dual_feasibility_tolerance": HIGHS_FEAS_TOL,
                                    "time_limit": float(time_limit_seconds),
                                },
                            )
                            stage2_wall = time.perf_counter() - t2

                            if not lp2.success:
                                raise TrialReject(f"REDUCED_STAGE2_NOT_SUCCESS:{int(lp2.status)}:{str(lp2.message)}")

                            z = np.asarray(lp2.x, dtype=np.float64)
                            x = z[:nex]
                            d = z[nex:]
                            new_edge_mass = np.zeros(nedge, dtype=np.float64)
                            new_edge_mass[exact_positions] = x
                            new_rep_flat = np.bincount(ex_cell, weights=x, minlength=p3.NCELL)
                            new_rep = new_rep_flat.reshape(p3.GRID)

                            cv_check = np.bincount(ex_cv, weights=x, minlength=p3.NCVT).reshape(p3.NSL, p3.NCV)
                            cv_err = float(np.max(np.abs(cv_check - new_cv_mass)))
                            active_rep = new_rep_flat[active_cells]
                            aux_err = float(np.max(np.abs(d - np.abs(active_rep - target_active)))) if nactive else 0.0
                            stage2_l1 = float(np.sum(np.abs(active_rep - target_active)) + constant_inactive_l1)
                            obj_total = float(lp2.fun) + constant_inactive_l1
                            if cv_err > MASS_TOL:
                                raise TrialReject(f"reduced_CV_equality:{cv_err}")
                            if aux_err > 1.0e-5:
                                raise TrialReject(f"reduced_auxiliary:{aux_err}")
                            if abs(obj_total - stage2_l1) > max(1.0e-5, 1.0e-10 * max(stage2_l1, 1.0)):
                                raise TrialReject("reduced_objective_mismatch")
                            mode = "ZERO_HALO_CERTIFICATE_PLUS_REDUCED_STAGE2"

                        else:
                            # Positive-halo regime: preserve frozen full Stage1, then solve exact frozen Stage2
                            # by restricted master + dual-pricing column generation. The full generic Stage2
                            # remains a bounded safety fallback if global pricing cannot be closed.
                            tpos1 = time.perf_counter()
                            lp1 = linprog(
                                c1_full,
                                A_ub=Acell_full,
                                b_ub=rep_capacity_flat,
                                A_eq=Aeq_full,
                                b_eq=new_cv_mass.reshape(-1),
                                bounds=(0.0, None),
                                method="highs-ds",
                                options={
                                    "presolve": True,
                                    "primal_feasibility_tolerance": HIGHS_FEAS_TOL,
                                    "dual_feasibility_tolerance": HIGHS_FEAS_TOL,
                                    "time_limit": float(time_limit_seconds),
                                },
                            )
                            positive_halo_stage1_wall = time.perf_counter() - tpos1
                            if not lp1.success:
                                raise TrialReject(f"POSITIVE_HALO_STAGE1_NOT_SUCCESS:{int(lp1.status)}:{str(lp1.message)}")

                            halo_opt = float(lp1.fun)
                            x1 = np.asarray(lp1.x, dtype=np.float64)
                            shell_mask_global = shell > 0
                            seed_shell_positions = np.where(
                                shell_mask_global & (x1 > POSITIVE_EDGE_TOL)
                            )[0]
                            prior_accepted_shell_positions = np.where(
                                shell_mask_global & (old_edge_mass > POSITIVE_EDGE_TOL)
                            )[0]
                            carry_forward_union_shell_positions = np.unique(np.concatenate([
                                seed_shell_positions,
                                prior_accepted_shell_positions,
                            ]))
                            selected_shell = set(
                                int(x) for x in carry_forward_union_shell_positions.tolist()
                            )
                            stage1_positive_shell_edge_count = int(seed_shell_positions.size)
                            prior_accepted_positive_shell_edge_count = int(prior_accepted_shell_positions.size)
                            carry_forward_union_shell_edge_count = int(carry_forward_union_shell_positions.size)

                            cg_global_certified = False
                            cg_final_lp = None
                            cg_final_positions = None
                            pricing_valid = True

                            for cg_iter in range(1, MAX_CG_ITERATIONS + 1):
                                column_generation_iterations = cg_iter
                                selected_positions = np.concatenate([
                                    exact_positions,
                                    np.asarray(sorted(selected_shell), dtype=np.int64),
                                ])
                                selected_positions = np.unique(selected_positions)
                                nsel = int(selected_positions.size)
                                sel_cv = edge_cv[selected_positions]
                                sel_cell = edge_cell[selected_positions]
                                sel_shell = shell[selected_positions]
                                sel_idx = np.arange(nsel, dtype=np.int64)

                                Aeq_sel = coo_matrix(
                                    (np.ones(nsel, dtype=np.float64), (sel_cv, sel_idx)),
                                    shape=(p3.NCVT, nsel),
                                ).tocsr()
                                Acell_sel = coo_matrix(
                                    (np.ones(nsel, dtype=np.float64), (sel_cell, sel_idx)),
                                    shape=(p3.NCELL, nsel),
                                ).tocsr()

                                nd = p3.NCELL
                                zero_d_cg = csr_matrix((p3.NCELL, nd), dtype=np.float64)
                                I_cg = eye(nd, format="csr", dtype=np.float64)
                                A_cap_cg = hstack([Acell_sel, zero_d_cg], format="csr")
                                A_abs_pos_cg = hstack([Acell_sel, -I_cg], format="csr")
                                A_abs_neg_cg = hstack([-Acell_sel, -I_cg], format="csr")
                                halo_c = (sel_shell > 0).astype(np.float64)
                                halo_row_cg = csr_matrix(halo_c.reshape(1, -1))
                                zero1_cg = csr_matrix((1, nd), dtype=np.float64)
                                A_halo_pos_cg = hstack([halo_row_cg, zero1_cg], format="csr")
                                A_halo_neg_cg = hstack([-halo_row_cg, zero1_cg], format="csr")
                                A_ub_cg = vstack(
                                    [A_cap_cg, A_abs_pos_cg, A_abs_neg_cg, A_halo_pos_cg, A_halo_neg_cg],
                                    format="csr",
                                )
                                target_cg = direct_target_rep.reshape(-1)
                                b_halo_cg = np.asarray(
                                    [halo_opt + HALO_OPT_TOL, -halo_opt + HALO_OPT_TOL],
                                    dtype=np.float64,
                                )
                                b_ub_cg = np.concatenate([
                                    rep_capacity_flat,
                                    target_cg,
                                    -target_cg,
                                    b_halo_cg,
                                ])
                                Aeq2_cg = hstack(
                                    [Aeq_sel, csr_matrix((p3.NCVT, nd), dtype=np.float64)],
                                    format="csr",
                                )
                                c2_cg = np.concatenate([np.zeros(nsel), np.ones(nd)])
                                bounds_cg = [(0.0, None)] * (nsel + nd)

                                tcg = time.perf_counter()
                                lp_cg = linprog(
                                    c2_cg,
                                    A_ub=A_ub_cg,
                                    b_ub=b_ub_cg,
                                    A_eq=Aeq2_cg,
                                    b_eq=new_cv_mass.reshape(-1),
                                    bounds=bounds_cg,
                                    method="highs-ds",
                                    options={
                                        "presolve": True,
                                        "primal_feasibility_tolerance": HIGHS_FEAS_TOL,
                                        "dual_feasibility_tolerance": HIGHS_FEAS_TOL,
                                        "time_limit": float(time_limit_seconds),
                                    },
                                )
                                column_generation_stage2_wall += time.perf_counter() - tcg
                                if not lp_cg.success:
                                    cg_final_lp = lp_cg
                                    cg_final_positions = selected_positions
                                    break

                                mu = np.asarray(lp_cg.ineqlin.marginals, dtype=np.float64)
                                lam = np.asarray(lp_cg.eqlin.marginals, dtype=np.float64)
                                lower = np.asarray(lp_cg.lower.marginals, dtype=np.float64)

                                mu_cap = mu[0:p3.NCELL]
                                mu_pos = mu[p3.NCELL:2*p3.NCELL]
                                mu_neg = mu[2*p3.NCELL:3*p3.NCELL]
                                mu_hpos = float(mu[3*p3.NCELL])
                                mu_hneg = float(mu[3*p3.NCELL + 1])

                                predicted_selected = -(
                                    mu_cap[sel_cell]
                                    + mu_pos[sel_cell]
                                    - mu_neg[sel_cell]
                                    + (sel_shell > 0).astype(np.float64) * (mu_hpos - mu_hneg)
                                ) - lam[sel_cv]
                                pricing_error = float(np.max(np.abs(
                                    predicted_selected - lower[:nsel]
                                )))
                                if pricing_error > 1.0e-7:
                                    pricing_valid = False
                                    cg_final_lp = lp_cg
                                    cg_final_positions = selected_positions
                                    break

                                selected_shell_mask = np.zeros(nedge, dtype=bool)
                                if selected_shell:
                                    selected_shell_mask[
                                        np.asarray(sorted(selected_shell), dtype=np.int64)
                                    ] = True
                                omitted_positions = np.where(
                                    shell_mask_global & (~selected_shell_mask)
                                )[0]

                                if omitted_positions.size:
                                    ocell = edge_cell[omitted_positions]
                                    ocv = edge_cv[omitted_positions]
                                    omitted_rc = -(
                                        mu_cap[ocell]
                                        + mu_pos[ocell]
                                        - mu_neg[ocell]
                                        + (mu_hpos - mu_hneg)
                                    ) - lam[ocv]
                                    min_rc = float(np.min(omitted_rc))
                                    negative_local = np.where(omitted_rc < -PRICING_TOL)[0]
                                else:
                                    omitted_rc = np.asarray([], dtype=np.float64)
                                    min_rc = float("inf")
                                    negative_local = np.asarray([], dtype=np.int64)

                                column_generation_min_omitted_reduced_cost = min_rc
                                cg_final_lp = lp_cg
                                cg_final_positions = selected_positions

                                if negative_local.size == 0:
                                    cg_global_certified = True
                                    break

                                order = negative_local[np.argsort(omitted_rc[negative_local])]
                                take = order[:COLUMN_BATCH_SIZE]
                                add_positions = omitted_positions[take]
                                for pos in add_positions.tolist():
                                    selected_shell.add(int(pos))

                            column_generation_selected_shell_edges = len(selected_shell)
                            maximum_selected_shell_edge_count = max(
                                maximum_selected_shell_edge_count,
                                column_generation_selected_shell_edges,
                            )

                            if (
                                cg_global_certified
                                and pricing_valid
                                and cg_final_lp is not None
                                and cg_final_lp.success
                                and cg_final_positions is not None
                            ):
                                nsel = int(cg_final_positions.size)
                                zcg = np.asarray(cg_final_lp.x, dtype=np.float64)
                                xcg = zcg[:nsel]
                                dcg = zcg[nsel:]
                                sel_cv = edge_cv[cg_final_positions]
                                sel_cell = edge_cell[cg_final_positions]
                                sel_shell = shell[cg_final_positions]

                                new_edge_mass = np.zeros(nedge, dtype=np.float64)
                                new_edge_mass[cg_final_positions] = xcg
                                new_rep_flat = np.bincount(
                                    sel_cell, weights=xcg, minlength=p3.NCELL
                                )
                                new_rep = new_rep_flat.reshape(p3.GRID)

                                cv_check = np.bincount(
                                    sel_cv, weights=xcg, minlength=p3.NCVT
                                ).reshape(p3.NSL, p3.NCV)
                                cv_err = float(np.max(np.abs(cv_check - new_cv_mass)))
                                aux_err = float(np.max(np.abs(
                                    dcg - np.abs(new_rep_flat - direct_target_rep.reshape(-1))
                                )))
                                stage1_halo = float(np.sum(xcg[sel_shell > 0]))
                                stage2_l1 = float(np.sum(np.abs(
                                    new_rep_flat - direct_target_rep.reshape(-1)
                                )))
                                if cv_err > MASS_TOL:
                                    raise TrialReject(f"cg_CV_equality:{cv_err}")
                                if abs(stage1_halo - halo_opt) > 2.0 * HALO_OPT_TOL:
                                    raise TrialReject(
                                        f"cg_halo_optimum:{stage1_halo}:{halo_opt}"
                                    )
                                if aux_err > 1.0e-5:
                                    raise TrialReject(f"cg_auxiliary:{aux_err}")
                                if abs(float(cg_final_lp.fun) - stage2_l1) > max(
                                    1.0e-5, 1.0e-10 * max(stage2_l1, 1.0)
                                ):
                                    raise TrialReject("cg_objective_mismatch")

                                mode = "POSITIVE_HALO_STAGE1_PLUS_COLUMN_GENERATED_STAGE2"
                                stage2_wall = column_generation_stage2_wall

                            else:
                                # Frozen full generic Stage2 is retained as bounded safety fallback.
                                nd = p3.NCELL
                                zero_d_full = csr_matrix((p3.NCELL, nd), dtype=np.float64)
                                I_full = eye(nd, format="csr", dtype=np.float64)
                                A_cap_full = hstack([Acell_full, zero_d_full], format="csr")
                                A_abs_pos_full = hstack([Acell_full, -I_full], format="csr")
                                A_abs_neg_full = hstack([-Acell_full, -I_full], format="csr")
                                target_full = direct_target_rep.reshape(-1)
                                halo_row = csr_matrix(c1_full.reshape(1, -1))
                                zero1 = csr_matrix((1, nd), dtype=np.float64)
                                A_halo_pos = hstack([halo_row, zero1], format="csr")
                                A_halo_neg = hstack([-halo_row, zero1], format="csr")
                                b_halo = np.asarray(
                                    [halo_opt + HALO_OPT_TOL, -halo_opt + HALO_OPT_TOL],
                                    dtype=np.float64,
                                )
                                A_ub_full = vstack(
                                    [
                                        A_cap_full,
                                        A_abs_pos_full,
                                        A_abs_neg_full,
                                        A_halo_pos,
                                        A_halo_neg,
                                    ],
                                    format="csr",
                                )
                                b_ub_full = np.concatenate([
                                    rep_capacity_flat,
                                    target_full,
                                    -target_full,
                                    b_halo,
                                ])
                                Aeq2_full = hstack(
                                    [Aeq_full, csr_matrix((p3.NCVT, nd), dtype=np.float64)],
                                    format="csr",
                                )
                                c2_full = np.concatenate([np.zeros(nedge), np.ones(nd)])
                                bounds_full = [(0.0, None)] * (nedge + nd)

                                tf = time.perf_counter()
                                lp2f = linprog(
                                    c2_full,
                                    A_ub=A_ub_full,
                                    b_ub=b_ub_full,
                                    A_eq=Aeq2_full,
                                    b_eq=new_cv_mass.reshape(-1),
                                    bounds=bounds_full,
                                    method="highs-ds",
                                    options={
                                        "presolve": True,
                                        "primal_feasibility_tolerance": HIGHS_FEAS_TOL,
                                        "dual_feasibility_tolerance": HIGHS_FEAS_TOL,
                                        "time_limit": float(time_limit_seconds),
                                    },
                                )
                                fallback_wall = time.perf_counter() - tf
                                if not lp2f.success:
                                    raise TrialReject("POSITIVE_HALO_CG_AND_GENERIC_STAGE2_NOT_SUCCESS:" + f"{int(lp2f.status)}:{str(lp2f.message)}")

                                zf = np.asarray(lp2f.x, dtype=np.float64)
                                new_edge_mass = zf[:nedge]
                                new_rep = np.bincount(
                                    edge_cell, weights=new_edge_mass, minlength=p3.NCELL
                                ).reshape(p3.GRID)
                                stage1_halo = halo_opt
                                stage2_l1 = float(np.sum(np.abs(
                                    new_rep - direct_target_rep
                                )))
                                mode = "GENERIC_XY2_STAGE2_FALLBACK"

                    candidate_grid = new_rep + current_residual
                    cap_excess = float(np.max(candidate_grid - cart_capacity))
                    rep_min = float(np.min(new_rep))
                    candidate_min = float(np.min(candidate_grid))
                    if rep_min < -MASS_TOL:
                        raise TrialReject(f"represented_negative:{rep_min}")
                    if candidate_min < -MASS_TOL:
                        raise TrialReject(f"cartesian_negative:{candidate_min}")
                    if cap_excess > cart_cap_tol:
                        raise TrialReject(f"cartesian_capacity:{cap_excess}:{cart_cap_tol}")

                    cand_sg = np.asarray(
                        a2e.invert_local_mass(r2src, candidate_grid, frozen_pressure, p_ref, hetero_pv),
                        dtype=np.float64,
                    )
                    cand_sat = float(a2e.BACKGROUND) + cand_sg
                    if float(np.min(cand_sat)) < p3.BACKGROUND - SAT_TOL or float(np.max(cand_sat)) > p3.MAX_SAT + SAT_TOL:
                        raise TrialReject("cartesian_saturation_bounds")
                    recon = np.asarray(
                        a2e.local_mass(r2src, cand_sat, frozen_pressure, p_ref, hetero_pv),
                        dtype=np.float64,
                    )
                    recon_err = float(np.max(np.abs(recon - candidate_grid)))
                    if recon_err > 1.0e-8:
                        raise TrialReject(f"EOS_reconstruction:{recon_err}")

                    expected_total = float(np.sum(old_grid)) + injected - produced
                    source_sink = float(np.sum(candidate_grid)) - expected_total
                    global_tol = max(MASS_TOL, REL_TOL * max(abs(expected_total), 1.0))
                    if abs(source_sink) > global_tol:
                        raise TrialReject(f"source_sink:{source_sink}:{global_tol}")


                    # Trial accepted; commit recurrent state atomically in memory first.
                    current_grid_mass = candidate_grid
                    current_rep = new_rep
                    current_cv_mass = new_cv_mass
                    current_cv_sat = new_cv_sat
                    current_cart_sat = cand_sat
                    current_edge_mass = new_edge_mass
                    current_time = parent_time + dt
                    cumulative_injected += injected
                    cumulative_produced += produced
                    accepted_atomic_steps += 1
                    retry_count_total += retry
                    if mode == "DIRECT_EDGE_EXACT":
                        direct_count += 1
                    elif mode == "ZERO_HALO_CERTIFICATE_PLUS_REDUCED_STAGE2":
                        reduced_count += 1
                    elif mode == "POSITIVE_HALO_STAGE1_PLUS_COLUMN_GENERATED_STAGE2":
                        positive_halo_cg_count += 1
                    elif mode == "GENERIC_XY2_STAGE2_FALLBACK":
                        fallback_count += 1
                    total_cg_iterations += column_generation_iterations
                    maximum_selected_shell_edge_count = max(
                        maximum_selected_shell_edge_count,
                        column_generation_selected_shell_edges,
                    )

                    step_wall = time.perf_counter() - step_start
                    rows.append({
                        "accepted_step": accepted_atomic_steps,
                        "outcome": "CERTIFIED",
                        "parent_day": parent_time,
                        "accepted_day": current_time,
                        "dt_days": dt,
                        "retry_index": retry,
                        "representation_mode": mode,
                        "stage1_terminal_mass_kg": stage1_halo,
                        "stage2_cell_L1_kg": stage2_l1,
                        "exact_support_zero_halo_certificate_wall_seconds": stage1_wall,
                        "positive_halo_full_stage1_wall_seconds": positive_halo_stage1_wall,
                        "reduced_or_column_generated_stage2_wall_seconds": stage2_wall,
                        "column_generation_stage2_wall_seconds": column_generation_stage2_wall,
                        "column_generation_iterations": column_generation_iterations,
                        "stage1_positive_shell_edge_count": stage1_positive_shell_edge_count,
                        "prior_accepted_positive_shell_edge_count": prior_accepted_positive_shell_edge_count,
                        "carry_forward_union_shell_edge_count": carry_forward_union_shell_edge_count,
                        "column_generation_selected_shell_edges": column_generation_selected_shell_edges,
                        "column_generation_min_omitted_reduced_cost": column_generation_min_omitted_reduced_cost,
                        "positive_XY1_terminal_edge_count": int(np.count_nonzero((ring == 1) & (new_edge_mass > POSITIVE_EDGE_TOL))),
                        "positive_XY2_terminal_edge_count": int(np.count_nonzero((ring == 2) & (new_edge_mass > POSITIVE_EDGE_TOL))),
                        "XY1_terminal_assigned_mass_kg": float(np.sum(new_edge_mass[ring == 1])),
                        "XY2_terminal_assigned_mass_kg": float(np.sum(new_edge_mass[ring == 2])),
                        "generic_fallback_wall_seconds": fallback_wall,
                        "total_step_wall_seconds": step_wall,
                        "cartesian_capacity_excess_kg": cap_excess,
                        "cartesian_EOS_reconstruction_max_error_kg": recon_err,
                        "global_source_sink_residual_kg": source_sink,
                        "total_mass_kg": float(np.sum(candidate_grid)),
                    })
                    atomic_write_bytes(staging / STEP_AUDIT, csvb(rows))
                    write_checkpoint()
                    print(
                        f"[PILOT STEP {accepted_atomic_steps:04d}] t={current_time:.9f}/{TARGET_DAY:.1f} d "
                        f"dt={dt:.9f} retry={retry} mode={mode} zeroH={stage1_wall:.3f}s "
                        f"posH1={positive_halo_stage1_wall:.3f}s stage2={stage2_wall:.3f}s "
                        f"cgIter={column_generation_iterations} seed={carry_forward_union_shell_edge_count} "
                        f"sel={column_generation_selected_shell_edges} fallback={fallback_wall:.3f}s total={step_wall:.3f}s",
                        flush=True,
                    )
                    accepted = True
                    break
                except TrialReject as exc:
                    rejection_reasons.append(repr(exc))
                    rows.append({
                        "accepted_step": accepted_atomic_steps,
                        "outcome": "REJECTED_TRIAL",
                        "parent_day": parent_time,
                        "accepted_day": "",
                        "dt_days": dt,
                        "retry_index": retry,
                        "representation_mode": "",
                        "rejection_reason": repr(exc),
                    })
                    atomic_write_bytes(staging / STEP_AUDIT, csvb(rows))
                    print(f"[REJECT] t={parent_time:.9f} target={TARGET_DAY:.1f} retry={retry} dt={dt:.9g}: {exc}", flush=True)
                    if retry >= MAX_RETRIES:
                        raise GateError(f"atomic_retry_budget_exhausted:{parent_time}:{rejection_reasons}")
            if not accepted:
                raise GateError(f"atomic_step_not_accepted:{parent_time}")

        stage = "Day385_pilot_closure"
        gate("Day385_hit_exactly", abs(current_time - TARGET_DAY) <= 1.0e-10, current_time)
        split_err = float(np.max(np.abs(current_grid_mass - current_rep - current_residual)))
        cv_edge = np.bincount(edge_cv, weights=current_edge_mass, minlength=p3.NCVT).reshape(p3.NSL, p3.NCV)
        cv_err = float(np.max(np.abs(cv_edge - current_cv_mass)))
        ledger_expected = initial_total_mass + cumulative_injected - cumulative_produced
        ledger_resid = float(np.sum(current_grid_mass)) - ledger_expected
        gate("Day385_split_identity", split_err <= MASS_TOL, split_err)
        gate("Day385_CV_edge_equality", cv_err <= MASS_TOL, cv_err)
        gate("Day385_global_source_sink", abs(ledger_resid) <= max(MASS_TOL, REL_TOL * max(abs(ledger_expected), 1.0)), ledger_resid)
        day385_positive_xy1_edges = int(np.count_nonzero((ring == 1) & (current_edge_mass > POSITIVE_EDGE_TOL)))
        day385_positive_xy2_edges = int(np.count_nonzero((ring == 2) & (current_edge_mass > POSITIVE_EDGE_TOL)))
        day385_xy1_mass = float(np.sum(current_edge_mass[ring == 1]))
        day385_xy2_mass = float(np.sum(current_edge_mass[ring == 2]))

        state_arrays = {
            "state_schema_version": np.asarray(2, dtype=np.int64),
            "source_R7_checkpoint_sha256": np.asarray(R7_SOURCE_CHECKPOINT_SHA),
            "source_R7R5_Day380_state_sha256": np.asarray(R7R5_STATE_SHA),
            "physical_day": np.asarray(TARGET_DAY, dtype=np.float64),
            "cartesian_component_mass_kg": current_grid_mass,
            "represented_cartesian_cell_mass_kg": current_rep,
            "grid_residual_component_mass_kg": current_residual,
            "cartesian_saturation": current_cart_sat,
            "transport_CV_component_mass_kg": current_cv_mass,
            "transport_CV_saturation": current_cv_sat,
            "frozen_flow_epoch_day": np.asarray(365.0, dtype=np.float64),
            "streamline_xyz_m": xyz,
            "streamline_tof_s": tof_s,
            "streamline_weight_m3_s": weights_m3_s,
            "reference_gas_pressure_pa": np.asarray(p_ref, dtype=np.float64),
            "cumulative_injected_component_mass_kg": np.asarray(cumulative_injected, dtype=np.float64),
            "cumulative_produced_component_mass_kg": np.asarray(cumulative_produced, dtype=np.float64),
            "support_edge_cv": edge_cv,
            "support_edge_cell": edge_cell,
            "support_edge_terminal_cost": shell,
            "support_edge_ring": ring,
            "support_edge_assigned_mass_kg": current_edge_mass,
        }
        atomic_write_bytes(staging / FINAL_STATE, deterministic_npz_bytes(state_arrays))
        day385_state_sha = sha(staging / FINAL_STATE)

        diagnostic_arrays, diagnostic_metrics = run_exact_diagnostic(TARGET_DAY)
        atomic_write_bytes(staging / FLOW_DIAGNOSTIC, deterministic_npz_bytes(diagnostic_arrays))
        diagnostic_sha = sha(staging / FLOW_DIAGNOSTIC)
        atomic_write_bytes(staging / DIAGNOSTIC_METRICS, jb(diagnostic_metrics))
        gate("Day385_diagnostic_no_fixed_point", diagnostic_metrics["diagnostic_same_time_fixed_point_executed"] is False)
        gate("Day385_diagnostic_no_transport_feedback", diagnostic_metrics["diagnostic_transport_feedback_executed"] is False)
        gate("Day385_diagnostic_streamline_count_positive", int(diagnostic_metrics["streamline_count"]) > 0, diagnostic_metrics["streamline_count"])

        certified_rows = [r for r in rows if r.get("outcome") == "CERTIFIED"]
        max_step_wall = max([float(r.get("total_step_wall_seconds", 0.0)) for r in certified_rows] or [0.0])
        segment_fallback_count = int(fallback_count - source_fallback_count)
        segment_positive_halo_count = int(positive_halo_cg_count - source_positive_halo_cg_count)
        segment_zero_halo_count = int(reduced_count - source_reduced_count)
        segment_direct_count = int(direct_count - source_direct_count)
        segment_retry_count = int(retry_count_total - source_retry_count_total)
        diagnostic_passed = True
        classification, recommendation, day390_auth = classify(True, diagnostic_passed, segment_fallback_count)
        stage = "publication"
        (staging / GATES).write_bytes(csvb(gates))
        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "repository_parent_R7R5_commit": PARENT,
            "R7R5_status_bound": R7R5_STATUS,
            "R7R5_classification_bound": R7R5_CLASS,
            "Day380_source_state_sha256": R7R5_STATE_SHA,
            "Day380_source_diagnostic_sha256": R7R5_DIAGNOSTIC_SHA,
            "Day380_source_accepted_steps": R7R5_ACCEPTED_STEPS,
            "R7R4R1_status_bound": R7R4R1_STATUS,
            "R7R4R1_classification_bound": R7R4R1_CLASS,
            "source_R7_checkpoint_sha256": R7_SOURCE_CHECKPOINT_SHA,
            "source_R7_checkpoint_day": R7_SOURCE_DAY,
            "source_R7_checkpoint_accepted_steps": R7_SOURCE_ACCEPTED_STEPS,
            "immediate_source_state_schema_version": 2,
            "recurrent_checkpoint_schema_version": 2,
            "schema_v2_XY2_execution": True,
            "schema_v2_existing_exact_XY1_order_preserved": True,
            "schema_v2_source_already_migrated": True,
            "XY2_new_edge_count": EXPECTED_XY2_NEW_EDGE_COUNT,
            "XY2_total_edge_count": EXPECTED_TOTAL_EDGE_COUNT,
            "carry_forward_prior_terminal_support_execution": True,
            "P3R1_partial_Day365_state_sha256": day365_state_sha,
            "frozen_transport_flow_epoch_day": 365.0,
            "pilot_start_day": physical_day,
            "resume_execution_start_day": R7R5_SOURCE_DAY,
            "pilot_final_day": current_time,
            "accepted_atomic_steps": accepted_atomic_steps,
            "segment_accepted_atomic_steps": int(accepted_atomic_steps - R7R5_ACCEPTED_STEPS),
            "nominal_CFL_dt_days": nominal_dt,
            "retry_count_total": retry_count_total,
            "segment_retry_count": segment_retry_count,
            "direct_step_count": direct_count,
            "segment_direct_step_count": segment_direct_count,
            "zero_halo_reduced_fast_path_step_count": reduced_count,
            "segment_zero_halo_reduced_step_count": segment_zero_halo_count,
            "positive_halo_column_generation_step_count": positive_halo_cg_count,
            "segment_positive_halo_column_generation_step_count": segment_positive_halo_count,
            "total_column_generation_iterations": total_cg_iterations,
            "maximum_selected_terminal_edge_count": maximum_selected_shell_edge_count,
            "generic_XY2_fallback_step_count": fallback_count,
            "segment_generic_XY2_fallback_step_count": segment_fallback_count,
            "maximum_accepted_step_wall_seconds": max_step_wall,
            "cumulative_injected_kg": cumulative_injected,
            "cumulative_produced_kg": cumulative_produced,
            "Day385_global_source_sink_residual_kg": ledger_resid,
            "Day385_split_identity_max_abs_error_kg": split_err,
            "Day385_CV_edge_equality_max_abs_error_kg": cv_err,
            "Day385_positive_XY1_terminal_edge_count": day385_positive_xy1_edges,
            "Day385_positive_XY2_terminal_edge_count": day385_positive_xy2_edges,
            "Day385_XY1_terminal_assigned_mass_kg": day385_xy1_mass,
            "Day385_XY2_terminal_assigned_mass_kg": day385_xy2_mass,
            "Day385_state_file": FINAL_STATE,
            "Day385_state_sha256": day385_state_sha,
            "Day385_diagnostic_file": FLOW_DIAGNOSTIC,
            "Day385_diagnostic_sha256": diagnostic_sha,
            "Day385_diagnostic_metrics": diagnostic_metrics,
            "restart_safe_checkpointing_executed": True,
            "per_step_progress_executed": True,
            "diagnostic_transport_feedback_executed": False,
            "recommended_next_action": recommendation,
            "Day385_to_Day390_repaired_pilot_authorized": bool(day390_auth),
            "P3_R1_full_rerun_authorized": False,
            "P4_authorized": False,
            "CFL_change_authorized": False,
            "transport_law_change_authorized": False,
            "new_support_topology_change_authorized": False,
            "residual_sidecar_change_authorized": False,
            "lexicographic_objective_change_authorized": False,
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "R32_recurrent_semantics_remain_authoritative": True,
            "P3_R0_remains_authoritative": True,
            "R7R4R1_implementation_freeze_bound": True,
            "source_R7_checkpoint_must_be_preserved": True,
            "source_R7_checkpoint_sha256": R7_SOURCE_CHECKPOINT_SHA,
            "R7R5_Day380_state_must_be_preserved": True,
            "R7R5_Day380_state_sha256": R7R5_STATE_SHA,
            "schema_v2_recurrent_support_authoritative": True,
            "XY2_execution_in_recurrent_transport_executed": True,
            "scientific_failure_declared": False,
            "physics_change_authorized": False,
            "CFL_change_authorized": False,
            "new_support_topology_change_authorized": False,
            "residual_sidecar_change_authorized": False,
            "lexicographic_objective_change_authorized": False,
            "zero_halo_reduced_Stage2_path_preserved": True,
            "positive_halo_column_generation_Stage2_path_preserved": True,
            "positive_halo_carry_forward_prior_accepted_XY1_XY2_terminal_seed_preserved": True,
            "R7R5_Day380_accepted_state_is_segment_start_authority": True,
            "Day380_diagnostic_does_not_feed_transport": True,
            "restart_from_Day376_910672_authorized": False,
            "restart_from_Day375_authorized": False,
            "restart_from_Day365_authorized": False,
            "dual_pricing_global_closure_required_for_positive_halo": True,
            "frozen_generic_XY2_lexicographic_fallback_must_be_preserved": True,
            "adaptive_retry_policy_preserved": {"maximum_retries": MAX_RETRIES, "retry_factor": RETRY_FACTOR},
            "frozen_transport_flow_epoch_day": 365.0,
            "Day385_exact_diagnostic_is_one_shot_no_feedback": True,
            "Day385_to_Day390_repaired_pilot_authorized": bool(day390_auth),
            "P3_R1_full_rerun_authorized": False,
            "P4_authorized": False,
            "recommended_next_action": recommendation,
        }

        (staging / SUMMARY).write_bytes(jb(summary))
        (staging / DECISION).write_bytes(jb(decision))
        manifest_rows = []
        for p in sorted(staging.iterdir()):
            if p.is_file() and p.name != MANIFEST:
                manifest_rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (staging / MANIFEST).write_bytes(csvb(manifest_rows))
        if out.exists():
            raise GateError("final_output_directory_preexists")
        staging.rename(out)

        print("=" * 220, flush=True)
        print(M, "PASS", flush=True)
        print("Classification                         :", classification, flush=True)
        print("Accepted atomic steps                  :", accepted_atomic_steps, flush=True)
        print("Day385 final time                      :", current_time, flush=True)
        print("Direct / zeroH / posH-CG / generic    :", direct_count, "/", reduced_count, "/", positive_halo_cg_count, "/", fallback_count, flush=True)
        print("Total retries                          :", retry_count_total, flush=True)
        print("Day385 diagnostic total seconds        :", diagnostic_metrics["total_refresh_s"], flush=True)
        print("Day385 state SHA256                    :", day385_state_sha, flush=True)
        print("Day385 diagnostic SHA256               :", diagnostic_sha, flush=True)
        print("Day385->Day390 pilot authorized        :", day390_auth, flush=True)
        print("Full P3-R1 rerun authorized            : False", flush=True)
        print("P4 authorized                          : False", flush=True)
        print("=" * 220, flush=True)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = blocked / f"{OUT_TOKEN}_Blocked_Report.json"
        if not report.exists():
            report.write_bytes(jb({
                "milestone": M,
                "status": BLOCK,
                "failed_stage": stage,
                "exception": repr(exc),
                "authoritative_physics_state_mutated": False,
                "authoritative_physical_time_advanced": False,
                "Day385_to_Day390_repaired_pilot_authorized": False,
                "P3_R1_full_rerun_authorized": False,
                "P4_authorized": False,
                "gates_completed": gates,
            }))
        print(M, "TECHNICAL / AUTHORITY BLOCK", flush=True)
        print("Stage:", stage, flush=True)
        print("Exception:", repr(exc), flush=True)
        return 2


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, default=Path("."))
    ap.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--time-limit-seconds", type=float, default=DEFAULT_TIME_LIMIT)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        selftest()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root, args.time_limit_seconds))
