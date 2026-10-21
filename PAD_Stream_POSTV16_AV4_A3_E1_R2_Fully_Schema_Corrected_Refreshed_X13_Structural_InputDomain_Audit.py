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
import zipfile
from pathlib import Path
from typing import Any

import numpy as np


MILESTONE = "POSTV16-AV4-A3-E1-R2"

PROTOCOL_ID = (
    "POSTV16_AV4_A3_E1_R2_FULLY_SCHEMA_CORRECTED_REFRESHED_DAY365_"
    "13CHANNEL_RECONSTRUCTION_INPUT_DOMAIN_AND_STRUCTURAL_"
    "RESTART_COMPATIBILITY_AUDIT_V1"
)

STATUS_PASS = (
    "AV4A3E1R2_FULLY_SCHEMA_CORRECTED_REFRESHED_DAY365_X13_"
    "RECONSTRUCTION_INPUT_DOMAIN_AUDIT_PASS_REPRESENTATION_ONLY_"
    "STRUCTURAL_RESTART_INCOMPATIBILITY_NO_CHECKPOINT_INFERENCE"
)

STATUS_FAIL = (
    "AV4A3E1R2_REPRESENTATION_RECONSTRUCTION_SCIENTIFIC_FAIL_"
    "NO_ADAPTATION_OR_AUTOMATIC_RERUN_AUTHORIZED"
)

STATUS_BLOCKED = "AV4A3E1R2_TECHNICAL_EXECUTION_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

PARENT_E1R1R1_COMMIT = "db36bdfd8099600cfcf09403d29cbeba9351cad7"

CONTROL_REALIZATION = "AV3CR0003"
CONTROL_POROSITY = "AV2PHI0003"
CONTROL_PARTITION = "VALIDATION"
CONTROL_DAY = 365.0
CONTROL_TIME_INDEX = 5

GRID = (15, 50, 50)
NZ, NY, NX = GRID
NSL = 1078
NN = 201
NT = 9

DX = 6.096
DY = 6.096
DZ = 1.2192
ORIGIN_CENTER_M = np.asarray([3.048, 3.048, 0.6096], dtype=np.float64)

DAYS = np.asarray(
    [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0],
    dtype=np.float64,
)
SPD = 86400.0

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

EXPECTED_CHECKPOINT_SHA256 = (
    "17b188494e0452570d43e868c20c4c814e6a1f0b493329d0e40849c4c5ec6d4e"
)

# --------------------------------------------------------------------------------------------------
# Exact repository source authorities.
# --------------------------------------------------------------------------------------------------

E1_ORIGINAL = "PAD_Stream_POSTV16_AV4_A3_E1_Refreshed_X13_Structural_InputDomain_Audit.py"
E1_ORIGINAL_BLOB = "2555ccdb5c3311ea49b0269746ba6ce17aa46258"

E1R1 = "PAD_Stream_POSTV16_AV4_A3_E1_R1_Technical_Authority_Schema_Block_Closure.py"
E1R1_BLOB = "26cd1dcde3850cd3c9bde4b73d67e096e16a1de3"

E1R1R1 = "PAD_Stream_POSTV16_AV4_A3_E1_R1_R1_Complete_R5_Schema_Audit_Extension.py"
E1R1R1_BLOB = "69fb006b700e35f1912655c7642a20d9eb5d365a"

R5 = (
    "PAD_Stream_POSTV16_AV4_A3_R2_R1_R5_Preexecution_Historical_Gate_Validated_"
    "Checkpoint_Compatibility_Protocol_Continuation.py"
)
R5_BLOB = "7192495d80d656fb950b7c5418f928f32246e93f"

A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"

A4R2 = (
    "PAD_Stream_POSTV16_AV3_A4_R2_"
    "Corrected_Certification_Teacher_Dataset_and_LockedOOD_Predictor.py"
)
A4R2_BLOB = "289901331e835afb44ff2f665fe9a6bbea2eac19"

AV2A2 = "PAD_Stream_POSTV16_AV2_A2_Porosity_Realization_and_Pore_Kinematics_Execution.py"
AV2A2_BLOB = "f141b07f0424d29a7996c089a76dbe7128af5132"

R7 = "PAD_Stream_POSTV16_AV1_D_R7_Full_End_to_End_PAD_Stream_Integration.py"
R7_BLOB = "a28722b0b8059bd50d94fb8a914defc0b35f2f7b"

B2 = "PAD_Stream_V16B2_Exact_3D_Fast_Marching_Arrival_Time_Baseline.py"
B2_BLOB = "95025d1e67a74f9dacaad311e5a402b63e7b4335"

C2 = "PAD_Stream_V16C2_Multi_Coordinate_Streamline_Transport_Database_Assembly.py"
C2_BLOB = "21ff44de456102772c99f7ddc80898c9139a76db"

PERM = "SGSIM_50x50x15_PERM_MD.csv"
PERM_BLOB = "317dd47d458bc6f880c2e3dc4ec1f69eeb0dd314"

SOURCE_BLOBS = {
    E1_ORIGINAL: E1_ORIGINAL_BLOB,
    E1R1: E1R1_BLOB,
    E1R1R1: E1R1R1_BLOB,
    R5: R5_BLOB,
    A2E: A2E_BLOB,
    A4R2: A4R2_BLOB,
    AV2A2: AV2A2_BLOB,
    R7: R7_BLOB,
    B2: B2_BLOB,
    C2: C2_BLOB,
    PERM: PERM_BLOB,
}

# --------------------------------------------------------------------------------------------------
# Frozen Drive authorities.
# --------------------------------------------------------------------------------------------------

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

E1R1_REL = BASE_AV4 / "POSTV16_AV4_A3_E1_R1_Technical_Authority_Schema_Block_Closure"
E1R1_SUMMARY = "PAD_Stream_POSTV16_AV4_A3_E1_R1_Summary.json"
E1R1_HANDOFF = "POSTV16_AV4_A3_E1_R1_E1R2_Handoff_Contract.json"
E1R1_DECISION = "POSTV16_AV4_A3_E1_R1_Decision_Contract.json"
E1R1_MANIFEST = "POSTV16_AV4_A3_E1_R1_Artifact_Manifest.csv"
E1R1_STATUS = (
    "AV4A3E1R1_ORIGINAL_E1_TECHNICAL_BLOCK_PRESERVED_"
    "R5_RECONSTRUCTION_CONTRACT_SHAPE_SCHEMA_ROOT_CAUSE_CLOSED_"
    "CORRECTED_E1R2_CONTINUATION_PROSPECTIVELY_FROZEN_"
    "NO_E1_SCIENTIFIC_EXECUTION"
)

E1R1R1_REL = (
    BASE_AV4
    / "POSTV16_AV4_A3_E1_R1_R1_Preexecution_Complete_R5_Schema_Audit_Extension"
)
E1R1R1_SUMMARY = "PAD_Stream_POSTV16_AV4_A3_E1_R1_R1_Summary.json"
E1R1R1_AUTHORITY = "POSTV16_AV4_A3_E1_R1_R1_E1R2_Complete_Correction_Authority.json"
E1R1R1_HANDOFF = "POSTV16_AV4_A3_E1_R1_R1_E1R2_Handoff_Contract.json"
E1R1R1_DECISION = "POSTV16_AV4_A3_E1_R1_R1_Decision_Contract.json"
E1R1R1_MANIFEST = "POSTV16_AV4_A3_E1_R1_R1_Artifact_Manifest.csv"
E1R1R1_STATUS = (
    "AV4A3E1R1R1_E1R1_PASS_PRESERVED_COMPLETE_R5_SCHEMA_READ_AUDIT_"
    "EXTENSION_FROZEN_E1R2_FULL_SCHEMA_CORRECTIONS_AUTHORIZED_"
    "NO_SCIENTIFIC_EXECUTION"
)

R5_REL = (
    BASE_AV4
    / "POSTV16_AV4_A3_R2_R1_R5_Preexecution_Historical_Gate_Validated_Protocol_Continuation"
)
R5_SUMMARY = "PAD_Stream_POSTV16_AV4_A3_R2_R1_R5_Summary.json"
R5_RECON = "POSTV16_AV4_A3_R2_R1_R5_Refreshed_13Channel_Reconstruction_Contract.json"
R5_TEMPORAL = "POSTV16_AV4_A3_R2_R1_R5_Temporal_Semantics_and_Restartability_Firewall.json"
R5_DOMAIN = "POSTV16_AV4_A3_R2_R1_R5_Input_Domain_Shift_Audit_Contract.json"
R5_OUTCOME = "POSTV16_AV4_A3_R2_R1_R5_Outcome_Classification_and_Gates.json"
R5_HANDOFF = "POSTV16_AV4_A3_R2_R1_R5_A3E1_Handoff_Contract.json"
R5_DECISION = "POSTV16_AV4_A3_R2_R1_R5_Decision_Contract.json"
R5_MANIFEST = "POSTV16_AV4_A3_R2_R1_R5_Artifact_Manifest.csv"

R5_STATUS = (
    "AV4A3R2R1R5_PREEXECUTION_HISTORICAL_GATE_VALIDATED_"
    "REFRESHED_13CHANNEL_RECONSTRUCTION_INPUT_DOMAIN_RESTART_SEMANTICS_"
    "AND_TEACHER_BACKED_CHECKPOINT_COMPATIBILITY_PROTOCOL_FROZEN_"
    "NO_INFERENCE_NO_TRANSPORT"
)

A2E_REL = BASE_AV4 / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_EPOCH = "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_SUMMARY = "PAD_Stream_POSTV16_AV4_A2_E_Summary.json"
A2E_MANIFEST = "POSTV16_AV4_A2_E_Artifact_Manifest.csv"

A2E_STATUS = (
    "AV4A2E_AV3CR0003_DAY365_SAME_TIME_SPATIAL_MOBILITY_PRESSURE_SATURATION_"
    "REFRESH_DARCY_POLLOCK_TOF_GEOMETRY_EXECUTION_PASS"
)

BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"
A4R2_REL = BASE_AV3 / "POSTV16_AV3_A4_R2_Corrected_Teacher_Dataset_and_LockedOOD_Predictor"
A4R2_TRAINVAL = "POSTV16_AV3_A4_R2_TrainValidation_13Channel_Transport_Dataset.npz"
A4R2_NORM = "POSTV16_AV3_A4_R2_Corrected_TRAIN_Only_Normalization.npz"
A4R2_SIDECAR = "POSTV16_AV3_A4_R2_Spatial_Relperm_Physics_Sidecar.npz"
A4R2_MANIFEST = "POSTV16_AV3_A4_R2_Artifact_Manifest.csv"

BASE_AV2 = Path("post_v16") / RID / "POSTV16_AV2_Variable_Porosity"
AV2A2_REL = BASE_AV2 / "POSTV16_AV2_A2_Porosity_Realization_and_Pore_Kinematics_Execution"
AV2A2_MANIFEST = "POSTV16_AV2_A2_Artifact_Manifest.csv"
AV2PHI0003_ARTIFACT = "POSTV16_AV2_A2_AV2PHI0003_Variable_Porosity_Pore_Kinematics.npz"

OUT_REL = BASE_AV4 / "POSTV16_AV4_A3_E1_R2_Refreshed_X13_Structural_InputDomain_Audit"
FAIL_REL = BASE_AV4 / "POSTV16_AV4_A3_E1_R2_SCIENTIFIC_FAIL"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_A3_E1_R2_BLOCKED"


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
            raise GateError("manifest_SHA_mismatch:" + fn)

    return manifest


def json_bytes(obj: Any) -> bytes:
    return (
        json.dumps(obj, indent=2, sort_keys=True, allow_nan=False)
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
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
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
            np.save(b, np.asarray(arrays[key]), allow_pickle=False)
            info = zipfile.ZipInfo(
                f"{key}.npy",
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, b.getvalue())

    return outer.getvalue()


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)

    for name, data in files.items():
        p = out / name

        if p.exists() and p.read_bytes() != data:
            raise GateError("existing_output_differs:" + name)

        if not p.exists():
            p.write_bytes(data)


def copied_module(root: Path, filename: str, module_name: str, td: Path):
    src = root / filename
    dst = td / filename
    dst.write_bytes(src.read_bytes())

    spec = importlib.util.spec_from_file_location(module_name, dst)
    if spec is None or spec.loader is None:
        raise GateError("cannot_load_module:" + filename)

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def scalar_stats(a: np.ndarray) -> dict[str, float]:
    x = np.asarray(a, dtype=np.float64).reshape(-1)
    return {
        "min": float(np.min(x)),
        "q01": float(np.quantile(x, 0.01)),
        "mean": float(np.mean(x)),
        "q50": float(np.quantile(x, 0.50)),
        "q99": float(np.quantile(x, 0.99)),
        "max": float(np.max(x)),
        "std": float(np.std(x)),
    }


def comparison_stats(a: np.ndarray, b: np.ndarray) -> dict[str, float]:
    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)
    d = aa - bb
    return {
        "mean_abs": float(np.mean(np.abs(d))),
        "rms": float(np.sqrt(np.mean(d * d))),
        "linf": float(np.max(np.abs(d))),
        "mean_signed": float(np.mean(d)),
    }


def self_test() -> None:
    assert GRID == (15, 50, 50)
    assert NSL == 1078
    assert NN == 201
    assert len(CHANNELS13) == 13
    assert CONTROL_DAY == DAYS[CONTROL_TIME_INDEX]
    assert np.array_equal(
        ORIGIN_CENTER_M,
        np.asarray([DX / 2.0, DY / 2.0, DZ / 2.0]),
    )

    # The E1 scientific classification is intentionally not a runtime failure:
    # representation can be reconstructed while restart semantics remain unsupported.
    historical_parent_state_channels = []
    assert historical_parent_state_channels == []
    assert "parent_saturation" not in CHANNELS13
    assert "parent_component_mass" not in CHANNELS13

    # Scaling identities.
    assert (CONTROL_DAY / 1000.0) == 0.365
    assert abs(((3.2 - 3.0) / 1.0) - 0.2) < 1.0e-15
    assert abs(((0.9 - 0.8) / 0.2) - 0.5) < 1.0e-15

    print(
        "POSTV16-AV4-A3-E1-R2 fully schema-corrected refreshed X13 / "
        "structural restart-compatibility audit self-test: PASS"
    )


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()

    out = drive / OUT_REL
    failed = drive / FAIL_REL
    blocked = drive / BLOCK_REL

    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"
    reconstruction_started = False
    checkpoint_model_loaded = False
    checkpoint_inference_performed = False
    teacher_transport_performed = False
    physical_time_advanced = False

    def gate(name: str, passed: Any, value: Any = None) -> None:
        ok = bool(passed)
        gates[name] = {"passed": ok, "value": value}
        print(
            f"[{'PASS' if ok else 'FAIL'}] {name}"
            + (f" — {value}" if value is not None else "")
        )
        if not ok:
            raise GateError(name)

    def sci_gate(name: str, passed: Any, value: Any = None) -> None:
        ok = bool(passed)
        gates[name] = {
            "passed": ok,
            "value": value,
            "scientific_execution_gate": True,
        }
        print(
            f"[{'PASS' if ok else 'FAIL'}] {name}"
            + (f" — {value}" if value is not None else "")
        )
        if not ok:
            raise ScientificFail(name, value)

    print("=" * 214)
    print(
        "POSTV16-AV4-A3-E1-R2 — FULLY SCHEMA-CORRECTED REFRESHED DAY365 13-CHANNEL RECONSTRUCTION / "
        "INPUT-DOMAIN / STRUCTURAL RESTART-COMPATIBILITY AUDIT"
    )
    print("=" * 214)
    print("REPRESENTATION + AUDIT ONLY.")
    print("NO .KERAS LOAD. NO CHECKPOINT INFERENCE. NO TEACHER TRANSPORT.")
    print("NO PHYSICAL-TIME ADVANCE. NO MAPBACK / LP. NO TRAINING / NORMALIZATION REFIT / CMG.")
    print("INPUT-DOMAIN SHIFT METRICS ARE DESCRIPTIVE — NO POST-HOC EXTRAPOLATION THRESHOLD.")
    print()

    try:
        # ------------------------------------------------------------------------------------------
        # Repository and source authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"

        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate(
            "repository_parent_is_E1R1R1_commit",
            parent == PARENT_E1R1R1_COMMIT,
            parent,
        )
        gate("repository_clean", status == "", repr(status))

        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(
                f"{Path(fn).stem}_git_blob_exact",
                actual == expected,
                actual,
            )

        # ------------------------------------------------------------------------------------------
        # Bind E1-R1 formal technical closure and E1-R1-R1 complete schema authority.
        # ------------------------------------------------------------------------------------------
        stage = "E1R1_R1R1_authority_binding"

        r1 = drive / E1R1_REL
        gate("E1R1_output_present", r1.is_dir(), str(r1))
        m1 = verify_manifest(r1, E1R1_MANIFEST)
        gate("E1R1_manifest_exact_6", len(m1) == 6, len(m1))

        s1 = load_json(r1 / E1R1_SUMMARY)
        h1 = load_json(r1 / E1R1_HANDOFF)
        d1 = load_json(r1 / E1R1_DECISION)

        gate("E1R1_status_exact", s1["status"] == E1R1_STATUS, s1["status"])
        gate(
            "E1R1_E1R2_handoff_authorized",
            h1["milestone"] == MILESTONE
            and h1["authorized"] is True
            and h1["execution"] is True,
            h1,
        )
        gate(
            "E1R1_original_scientific_execution_false",
            d1["original_E1_scientific_PASS_claimed"] is False
            and d1["scientific_execution_performed"] is False,
        )

        r11 = drive / E1R1R1_REL
        gate("E1R1R1_output_present", r11.is_dir(), str(r11))
        m11 = verify_manifest(r11, E1R1R1_MANIFEST)
        gate("E1R1R1_manifest_exact_6", len(m11) == 6, len(m11))

        s11 = load_json(r11 / E1R1R1_SUMMARY)
        a11 = load_json(r11 / E1R1R1_AUTHORITY)
        h11 = load_json(r11 / E1R1R1_HANDOFF)
        d11 = load_json(r11 / E1R1R1_DECISION)

        gate("E1R1R1_status_exact", s11["status"] == E1R1R1_STATUS, s11["status"])
        gate(
            "E1R1R1_complete_schema_authority_exact",
            len(a11["authorized_E1R2_schema_corrections"]) == 5
            and a11["scientific_change"] is False
            and a11["physics_change"] is False
            and a11["normalization_change"] is False
            and a11["ADV_algorithm_change"] is False
            and a11["checkpoint_change"] is False,
        )
        gate(
            "E1R1R1_E1R2_handoff_authorized",
            h11["milestone"] == MILESTONE
            and h11["authorized"] is True
            and h11["execution"] is True,
            h11,
        )
        gate(
            "E1R1R1_downstream_firewalls_preserved",
            h11["A3_E2_authorized"] is False
            and h11["AV4_dynamic_transport_execution_authorized"] is False
            and d11["A3_E2_authorized"] is False
            and d11["AV4_dynamic_transport_execution_authorized"] is False,
        )

        # ------------------------------------------------------------------------------------------
        # Bind R5 PASS and original E1 authorization exactly.
        # ------------------------------------------------------------------------------------------
        stage = "R5_authority_binding"

        r5 = drive / R5_REL
        gate("R5_output_present", r5.is_dir(), str(r5))

        m5 = verify_manifest(r5, R5_MANIFEST)
        gate("R5_manifest_exact_11", len(m5) == 11, len(m5))

        s5 = load_json(r5 / R5_SUMMARY)
        recon5 = load_json(r5 / R5_RECON)
        temporal5 = load_json(r5 / R5_TEMPORAL)
        domain5 = load_json(r5 / R5_DOMAIN)
        outcome5 = load_json(r5 / R5_OUTCOME)
        handoff5 = load_json(r5 / R5_HANDOFF)
        decision5 = load_json(r5 / R5_DECISION)

        gate("R5_status_exact", s5["status"] == R5_STATUS, s5["status"])
        gate(
            "R5_E1_handoff_exact",
            handoff5["milestone"] == "POSTV16-AV4-A3-E1"
            and handoff5["authorized"] is True
            and handoff5["execution"] is True,
            handoff5,
        )
        gate(
            "R5_E2_still_unauthorized",
            handoff5["A3_E2_teacher_backed_checkpoint_test_authorized"] is False
            and decision5["AV4_A3_E2_authorized"] is False,
        )
        gate(
            "R5_dynamic_transport_still_unauthorized",
            handoff5["AV4_dynamic_transport_execution_authorized"] is False
            and decision5["AV4_dynamic_transport_execution_authorized"] is False,
        )
        gate(
            "R5_checkpoint_reuse_still_false",
            handoff5["AV3_checkpoint_committed_reuse"] is False
            and decision5["AV3_checkpoint_committed_reuse"] is False,
        )
        gate(
            "R5_structural_outcome_contract_present",
            "A3_E1_PASS_REPRESENTATION_ONLY" in outcome5
            and "STRUCTURAL_RESTART_INCOMPATIBILITY" in outcome5,
        )
        gate(
            "R5_reconstruction_channel_order_exact",
            recon5["refreshed_streamlines"] == NSL
            and recon5["nodes_per_streamline"] == NN
            and len(recon5["channel_order"]) == 13
            and recon5["channel_order"] == CHANNELS13,
            recon5.get("channel_order"),
        )
        gate(
            "R5_absolute_target_time_semantics_frozen",
            temporal5["historical_AV3_training_semantics"]["time_features"]
            == [
                "target_time_hat = target_day/1000",
                "target_eta_sequence = target_day*86400/terminal_TOF",
            ],
        )
        gate(
            "R5_no_arbitrary_domain_threshold",
            domain5["domain_shift_role"]
            == (
                "diagnostic evidence only in A3-E1; no arbitrary numeric extrapolation "
                "threshold is allowed to authorize checkpoint reuse"
            ),
        )

        # ------------------------------------------------------------------------------------------
        # Bind A2-E refreshed Day365 epoch.
        # ------------------------------------------------------------------------------------------
        stage = "A2E_refreshed_epoch_binding"

        a2e = drive / A2E_REL
        gate("A2E_output_present", a2e.is_dir(), str(a2e))

        m2e = verify_manifest(a2e, A2E_MANIFEST)
        gate("A2E_manifest_exact_12", len(m2e) == 12, len(m2e))
        gate("A2E_epoch_manifested", A2E_EPOCH in m2e, A2E_EPOCH)

        s2e = load_json(a2e / A2E_SUMMARY)
        gate("A2E_status_exact", s2e["status"] == A2E_STATUS, s2e["status"])
        gate("A2E_no_PI_RNN_inference", s2e["PI_RNN_inference"] is False)
        gate("A2E_no_physical_time_advance", s2e["physical_time_advance"] is False)

        with np.load(a2e / A2E_EPOCH, allow_pickle=False) as z:
            epoch = {k: np.asarray(z[k]).copy() for k in z.files}

        required_epoch = {
            "Qx", "Qy", "Qz",
            "streamline_xyz_m", "streamline_tof_s", "streamline_weight_m3_s",
            "paired_porosity", "refreshed_pressure_psi",
            "nw", "no", "krw_max", "kro_max",
            "xi", "tau_end_s", "canonical_day",
            "physical_time_advance", "PI_RNN_inference",
        }
        gate(
            "A2E_required_epoch_arrays_present",
            required_epoch.issubset(epoch),
            sorted(epoch),
        )
        gate(
            "A2E_canonical_day_365",
            float(np.asarray(epoch["canonical_day"]).reshape(-1)[0]) == CONTROL_DAY,
        )
        gate(
            "A2E_epoch_firewalls_exact",
            bool(np.asarray(epoch["physical_time_advance"]).reshape(-1)[0]) is False
            and bool(np.asarray(epoch["PI_RNN_inference"]).reshape(-1)[0]) is False,
        )

        qx = np.asarray(epoch["Qx"], dtype=np.float64)
        qy = np.asarray(epoch["Qy"], dtype=np.float64)
        qz = np.asarray(epoch["Qz"], dtype=np.float64)
        xyz = np.asarray(epoch["streamline_xyz_m"], dtype=np.float64)
        tof = np.asarray(epoch["streamline_tof_s"], dtype=np.float64)
        tau_end = np.asarray(epoch["tau_end_s"], dtype=np.float64)
        weights = np.asarray(epoch["streamline_weight_m3_s"], dtype=np.float64)
        phi = np.asarray(epoch["paired_porosity"], dtype=np.float64)
        pressure = np.asarray(epoch["refreshed_pressure_psi"], dtype=np.float64)
        nw = np.asarray(epoch["nw"], dtype=np.float64)
        no = np.asarray(epoch["no"], dtype=np.float64)
        krw = np.asarray(epoch["krw_max"], dtype=np.float64)
        kro = np.asarray(epoch["kro_max"], dtype=np.float64)
        xi1d = np.asarray(epoch["xi"], dtype=np.float64)

        shape_gates = {
            "Qx": qx.shape == (15, 50, 49),
            "Qy": qy.shape == (15, 49, 50),
            "Qz": qz.shape == (14, 50, 50),
            "xyz": xyz.shape == (NSL, NN, 3),
            "tof": tof.shape == (NSL, NN),
            "tau_end": tau_end.shape == (NSL,),
            "weights": weights.shape == (NSL,),
            "phi": phi.shape == GRID,
            "pressure": pressure.shape == GRID,
            "nw": nw.shape == GRID,
            "no": no.shape == GRID,
            "krw": krw.shape == GRID,
            "kro": kro.shape == GRID,
            "xi": xi1d.shape == (NN,),
        }
        gate("A2E_refreshed_epoch_shapes_exact", all(shape_gates.values()), shape_gates)
        gate(
            "A2E_refreshed_epoch_finite",
            all(
                np.isfinite(a).all()
                for a in [qx, qy, qz, xyz, tof, tau_end, weights, phi, pressure, nw, no, krw, kro, xi1d]
            ),
        )
        gate(
            "A2E_tau_end_matches_TOF_terminal",
            float(np.max(np.abs(tau_end - tof[:, -1]))) <= 1.0e-10,
            float(np.max(np.abs(tau_end - tof[:, -1]))),
        )
        gate(
            "A2E_xi_exact_common_201",
            float(np.max(np.abs(xi1d - np.linspace(0.0, 1.0, NN)))) <= 1.0e-12,
            float(np.max(np.abs(xi1d - np.linspace(0.0, 1.0, NN)))),
        )

        # ------------------------------------------------------------------------------------------
        # Bind historical AV3 dataset, normalization, and baseline kinematics.
        # ------------------------------------------------------------------------------------------
        stage = "historical_AV3_reference_binding"

        a4 = drive / A4R2_REL
        gate("AV3_A4R2_output_present", a4.is_dir(), str(a4))

        m4 = verify_manifest(a4, A4R2_MANIFEST)
        gate("AV3_A4R2_manifest_exact_11", len(m4) == 11, len(m4))
        for fn in [A4R2_TRAINVAL, A4R2_NORM, A4R2_SIDECAR]:
            gate(f"AV3_A4R2_manifested_{Path(fn).stem}", fn in m4, fn)

        with np.load(a4 / A4R2_TRAINVAL, allow_pickle=False) as z:
            hist = {k: np.asarray(z[k]).copy() for k in z.files}

        with np.load(a4 / A4R2_NORM, allow_pickle=False) as z:
            norm = {k: np.asarray(z[k]).copy() for k in z.files}

        with np.load(a4 / A4R2_SIDECAR, allow_pickle=False) as z:
            side = {k: np.asarray(z[k]).copy() for k in z.files}

        Xhist = np.asarray(hist["X_required_13"], dtype=np.float32)
        ridx = np.asarray(hist["realization_index"], dtype=np.int64)
        tidx = np.asarray(hist["time_index"], dtype=np.int64)
        sidx = np.asarray(hist["streamline_index"], dtype=np.int64)
        hist_channels = [str(x) for x in np.asarray(hist["channel_names"]).tolist()]

        gate(
            "historical_X13_shape_exact",
            Xhist.shape == (3 * NT * NSL, NN, 13),
            Xhist.shape,
        )
        gate("historical_channel_order_exact", hist_channels == CHANNELS13, hist_channels)

        train_mask = ridx < 2
        val365_mask = (ridx == 2) & (tidx == CONTROL_TIME_INDEX)

        gate("historical_TRAIN_profile_count_19404", int(np.sum(train_mask)) == 19404, int(np.sum(train_mask)))
        gate("historical_AV3CR0003_day365_profile_count_1078", int(np.sum(val365_mask)) == NSL, int(np.sum(val365_mask)))

        val_order = np.argsort(sidx[val365_mask])
        val_sidx = sidx[val365_mask][val_order]
        gate(
            "historical_AV3CR0003_day365_streamline_index_exact",
            np.array_equal(val_sidx, np.arange(NSL, dtype=np.int64)),
        )
        Xval365 = Xhist[val365_mask][val_order]

        pmean = float(np.asarray(norm["pressure_mean_psi"]).reshape(-1)[0])
        pstd = float(np.asarray(norm["pressure_std_psi"]).reshape(-1)[0])
        fit_corey = [str(x) for x in np.asarray(norm["fit_corey_realizations"]).tolist()]
        norm_origin = np.asarray(norm["sampling_origin_center_m"], dtype=np.float64)

        gate(
            "historical_pressure_normalization_finite_positive",
            np.isfinite(pmean) and np.isfinite(pstd) and pstd > 0.0,
            {"mean_psi": pmean, "std_psi": pstd},
        )
        gate(
            "historical_pressure_normalization_TRAIN_only",
            fit_corey == ["AV3CR0001", "AV3CR0002"],
            fit_corey,
        )
        gate(
            "historical_cell_center_origin_exact",
            np.array_equal(norm_origin, ORIGIN_CENTER_M),
            norm_origin.tolist(),
        )

        hist_tau_all = np.asarray(side["terminal_pollock_tof_s"], dtype=np.float64)
        gate(
            "historical_sidecar_terminal_TOF_shape",
            hist_tau_all.shape == (4, NSL),
            hist_tau_all.shape,
        )
        hist_tau_val = hist_tau_all[2]

        av2a2 = drive / AV2A2_REL
        gate("AV2_A2_output_present", av2a2.is_dir(), str(av2a2))
        mva = verify_manifest(av2a2, AV2A2_MANIFEST)
        gate("AV2PHI0003_kinematics_manifested", AV2PHI0003_ARTIFACT in mva, AV2PHI0003_ARTIFACT)

        with np.load(av2a2 / AV2PHI0003_ARTIFACT, allow_pickle=False) as z:
            hist_xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
            hist_tof = np.asarray(z["pollock_tof_s"], dtype=np.float64)

        gate("historical_AV2PHI0003_XYZ_shape", hist_xyz.shape == (NSL, NN, 3), hist_xyz.shape)
        gate("historical_AV2PHI0003_TOF_shape", hist_tof.shape == (NSL, NN), hist_tof.shape)

        # ------------------------------------------------------------------------------------------
        # Scientific E1 reconstruction begins here.
        # ------------------------------------------------------------------------------------------
        reconstruction_started = True
        stage = "refreshed_ADV_and_X13_reconstruction"

        permeability = np.loadtxt(
            root / PERM,
            skiprows=1,
            dtype=np.float64,
        ).reshape(GRID, order="C")

        sci_gate(
            "SGSim_permeability_shape_finite_positive",
            permeability.shape == GRID
            and np.isfinite(permeability).all()
            and np.all(permeability > 0.0),
            [float(np.min(permeability)), float(np.max(permeability))],
        )

        Kx = permeability
        Ky = permeability
        Kz = 0.10 * permeability

        # Load exact historical helper implementations from temporary copies so
        # module-level output directories cannot dirty the repository.
        with tempfile.TemporaryDirectory(prefix="POSTV16_AV4_A3E1_MODULES_") as td_raw:
            td = Path(td_raw)

            av2mod = copied_module(root, AV2A2, "av4a3e1_av2a2", td)
            r7mod = copied_module(root, R7, "av4a3e1_r7", td)
            b2mod = copied_module(root, B2, "av4a3e1_b2", td)
            c2mod = copied_module(root, C2, "av4a3e1_c2", td)

            # Exact historical variable-phi face arithmetic and pore-velocity rule.
            px, py, pz, vx, vy, vz = av2mod.pore_velocity(
                qx, qy, qz, phi
            )

            sci_gate(
                "variable_phi_face_fields_finite_positive",
                all(np.isfinite(a).all() and np.all(a > 0.0) for a in [px, py, pz]),
            )
            sci_gate(
                "variable_phi_pore_velocity_finite",
                all(np.isfinite(a).all() for a in [vx, vy, vz]),
            )

            # Exact R7/B7 cell-centering + directional ADV solve.
            cx, cy, cz = r7mod.face_to_cell(vx, vy, vz)
            _, _, _, source_mask, _ = b2mod.bind_injector_sources(qx, qy, qz)
            source_mask = np.asarray(source_mask, dtype=bool)

            sci_gate("ADV_five_source_cells", int(np.sum(source_mask)) == 5, int(np.sum(source_mask)))

            adv_grid, adv_audit = r7mod.solve_adv(
                cx, cy, cz, source_mask, DX, DY, DZ
            )

            sci_gate("ADV_finite", adv_audit["finite"])
            sci_gate("ADV_nonnegative", adv_audit["nonnegative"])
            sci_gate("ADV_non_source_positive", adv_audit["non_source_positive"])
            sci_gate(
                "ADV_source_zero",
                adv_audit["source_max_abs_s"] < 1.0e-8,
                adv_audit["source_max_abs_s"],
            )
            sci_gate(
                "ADV_relative_L2_residual_lt_1e8",
                adv_audit["relative_L2_residual"] < 1.0e-8,
                adv_audit["relative_L2_residual"],
            )

            # Exact historical C2 trilinear cell-centered sampling.
            adv_s, audit_adv = c2mod.trilinear(
                adv_grid, xyz, DX, DY, DZ, ORIGIN_CENTER_M
            )
            kx_s, audit_kx = c2mod.trilinear(
                Kx, xyz, DX, DY, DZ, ORIGIN_CENTER_M
            )
            ky_s, audit_ky = c2mod.trilinear(
                Ky, xyz, DX, DY, DZ, ORIGIN_CENTER_M
            )
            kz_s, audit_kz = c2mod.trilinear(
                Kz, xyz, DX, DY, DZ, ORIGIN_CENTER_M
            )
            phi_s, audit_phi = c2mod.trilinear(
                phi, xyz, DX, DY, DZ, ORIGIN_CENTER_M
            )
            pressure_s, audit_pressure = c2mod.trilinear(
                pressure, xyz, DX, DY, DZ, ORIGIN_CENTER_M
            )
            nw_s, audit_nw = c2mod.trilinear(
                nw, xyz, DX, DY, DZ, ORIGIN_CENTER_M
            )
            no_s, audit_no = c2mod.trilinear(
                no, xyz, DX, DY, DZ, ORIGIN_CENTER_M
            )
            krw_s, audit_krw = c2mod.trilinear(
                krw, xyz, DX, DY, DZ, ORIGIN_CENTER_M
            )
            kro_s, audit_kro = c2mod.trilinear(
                kro, xyz, DX, DY, DZ, ORIGIN_CENTER_M
            )

        for name, arr in [
            ("adv_s", adv_s),
            ("kx_s", kx_s),
            ("ky_s", ky_s),
            ("kz_s", kz_s),
            ("phi_s", phi_s),
            ("pressure_s", pressure_s),
            ("nw_s", nw_s),
            ("no_s", no_s),
            ("krw_s", krw_s),
            ("kro_s", kro_s),
        ]:
            sci_gate(
                f"{name}_shape_finite",
                arr.shape == (NSL, NN) and np.isfinite(arr).all(),
                arr.shape,
            )

        pollock_hat = tof / tau_end[:, None]
        xi2 = np.broadcast_to(xi1d[None, :], (NSL, NN))

        sci_gate(
            "refreshed_xi_pollock_hat_identity",
            float(np.max(np.abs(xi2 - pollock_hat))) <= 1.0e-10,
            float(np.max(np.abs(xi2 - pollock_hat))),
        )

        Kh = np.sqrt(
            np.maximum(kx_s, 1.0e-30)
            * np.maximum(ky_s, 1.0e-30)
        )
        logKh = np.log10(np.maximum(Kh, 1.0e-30))
        logKratio = np.log10(
            np.maximum(kz_s, 1.0e-30)
            / np.maximum(Kh, 1.0e-30)
        )

        pressure_z = (pressure_s - pmean) / pstd
        target_time_hat = np.full((NSL, NN), CONTROL_DAY / 1000.0, dtype=np.float64)
        eta_streamline = CONTROL_DAY * SPD / tau_end
        target_eta = np.broadcast_to(eta_streamline[:, None], (NSL, NN))

        Xref = np.stack(
            [
                xi2,
                pollock_hat,
                adv_s / tau_end[:, None],
                logKh,
                logKratio,
                phi_s,
                pressure_z,
                target_time_hat,
                target_eta,
                nw_s - 3.0,
                no_s - 3.0,
                (krw_s - 0.80) / 0.20,
                (kro_s - 0.80) / 0.20,
            ],
            axis=-1,
        ).astype(np.float32)

        sci_gate("refreshed_X13_shape_exact", Xref.shape == (NSL, NN, 13), Xref.shape)
        sci_gate("refreshed_X13_finite", np.isfinite(Xref).all())
        sci_gate(
            "refreshed_target_time_hat_absolute_day365",
            float(np.max(np.abs(Xref[:, :, 7].astype(np.float64) - 0.365))) <= 2.0e-8,
            float(np.max(np.abs(Xref[:, :, 7].astype(np.float64) - 0.365))),
        )
        sci_gate(
            "refreshed_target_eta_positive",
            np.all(Xref[:, :, 8] > 0.0),
            [float(np.min(Xref[:, :, 8])), float(np.max(Xref[:, :, 8]))],
        )
        sci_gate(
            "refreshed_Corey_scaled_channels_strict_minus1_plus1",
            float(np.min(Xref[:, :, 9:13])) > -1.0
            and float(np.max(Xref[:, :, 9:13])) < 1.0,
            [
                float(np.min(Xref[:, :, 9:13])),
                float(np.max(Xref[:, :, 9:13])),
            ],
        )

        # ------------------------------------------------------------------------------------------
        # Input-domain and historical control-state audit. Descriptive only.
        # ------------------------------------------------------------------------------------------
        stage = "input_domain_and_historical_control_audit"

        channel_rows: list[dict[str, Any]] = []
        baseline_rows: list[dict[str, Any]] = []

        for j, name in enumerate(CHANNELS13):
            train_values = Xhist[train_mask, :, j].astype(np.float64)
            ref_values = Xref[:, :, j].astype(np.float64)
            baseline_values = Xval365[:, :, j].astype(np.float64)

            ts = scalar_stats(train_values)
            rs = scalar_stats(ref_values)

            outside_minmax = (ref_values < ts["min"]) | (ref_values > ts["max"])
            outside_p0199 = (ref_values < ts["q01"]) | (ref_values > ts["q99"])

            channel_rows.append(
                {
                    "channel_index": j,
                    "channel": name,
                    "TRAIN_min": ts["min"],
                    "TRAIN_q01": ts["q01"],
                    "TRAIN_mean": ts["mean"],
                    "TRAIN_q50": ts["q50"],
                    "TRAIN_q99": ts["q99"],
                    "TRAIN_max": ts["max"],
                    "TRAIN_std": ts["std"],
                    "refreshed_min": rs["min"],
                    "refreshed_q01": rs["q01"],
                    "refreshed_mean": rs["mean"],
                    "refreshed_q50": rs["q50"],
                    "refreshed_q99": rs["q99"],
                    "refreshed_max": rs["max"],
                    "refreshed_std": rs["std"],
                    "outside_TRAIN_minmax_count": int(np.sum(outside_minmax)),
                    "outside_TRAIN_minmax_fraction": float(np.mean(outside_minmax)),
                    "outside_TRAIN_p01_p99_count": int(np.sum(outside_p0199)),
                    "outside_TRAIN_p01_p99_fraction": float(np.mean(outside_p0199)),
                    "domain_metric_role": "DESCRIPTIVE_NO_REUSE_THRESHOLD",
                }
            )

            cmp = comparison_stats(ref_values, baseline_values)
            baseline_rows.append(
                {
                    "channel_index": j,
                    "channel": name,
                    **cmp,
                    "comparison": "refreshed_day365_minus_historical_AV3CR0003_day365",
                }
            )

        xyz_delta = xyz - hist_xyz
        xyz_node_shift = np.linalg.norm(xyz_delta, axis=2)
        terminal_tof_rel = (
            np.abs(tau_end - hist_tau_val)
            / np.maximum(np.abs(hist_tau_val), 1.0e-30)
        )

        geometry_audit = {
            "historical_geometry_source": AV2PHI0003_ARTIFACT,
            "refreshed_geometry_source": A2E_EPOCH,
            "XYZ_node_shift_m": scalar_stats(xyz_node_shift),
            "XYZ_RMS_vector_shift_m": float(
                np.sqrt(np.mean(np.sum(xyz_delta * xyz_delta, axis=2)))
            ),
            "XYZ_max_vector_shift_m": float(np.max(xyz_node_shift)),
            "terminal_TOF_historical_days": scalar_stats(hist_tau_val / SPD),
            "terminal_TOF_refreshed_days": scalar_stats(tau_end / SPD),
            "terminal_TOF_absolute_shift_days": scalar_stats(
                np.abs(tau_end - hist_tau_val) / SPD
            ),
            "terminal_TOF_relative_shift": scalar_stats(terminal_tof_rel),
            "full_201node_TOF_comparison": comparison_stats(tof, hist_tof),
            "role": "DESCRIPTIVE_INPUT_DOMAIN_AND_GEOMETRY_SHIFT_NO_REUSE_THRESHOLD",
        }

        adv_output_audit = {
            "source_cells": int(np.sum(source_mask)),
            "relative_L2_residual": float(adv_audit["relative_L2_residual"]),
            "max_abs_residual": float(adv_audit["max_abs_residual"]),
            "source_max_abs_s": float(adv_audit["source_max_abs_s"]),
            "finite": bool(adv_audit["finite"]),
            "nonnegative": bool(adv_audit["nonnegative"]),
            "non_source_positive": bool(adv_audit["non_source_positive"]),
            "variable_phi_face_rule": "arithmetic_mean_of_adjacent_cell_porosity",
            "pore_velocity_rule": "Q/(face_area*face_porosity)",
            "cell_center_rule": "frozen_R7_face_to_cell",
            "directional_solve_rule": "frozen_R7_solve_adv_B6_B6A_B7_semantics",
            "sampling_rule": "frozen_V16C2_trilinear_cell_centered",
            "sampling_origin_m": ORIGIN_CENTER_M.tolist(),
            "sampling_audits": {
                "ADV": audit_adv,
                "Kx": audit_kx,
                "Ky": audit_ky,
                "Kz": audit_kz,
                "porosity": audit_phi,
                "pressure": audit_pressure,
                "nw": audit_nw,
                "no": audit_no,
                "krw_max": audit_krw,
                "kro_max": audit_kro,
            },
        }

        # ------------------------------------------------------------------------------------------
        # Structural restart compatibility classification.
        # ------------------------------------------------------------------------------------------
        stage = "structural_restart_compatibility_classification"

        parent_state_channels = [
            c for c in CHANNELS13
            if c in {
                "parent_saturation",
                "current_saturation",
                "previous_saturation",
                "parent_component_mass",
                "current_component_mass",
                "previous_state",
            }
        ]

        structural_restart_incompatibility = (
            len(parent_state_channels) == 0
            and temporal5["direct_restart_authority"]["currently_proven"] is False
        )

        sci_gate(
            "historical_checkpoint_parent_state_channel_count_zero",
            len(parent_state_channels) == 0,
            parent_state_channels,
        )
        sci_gate(
            "structural_restart_incompatibility_classified",
            structural_restart_incompatibility,
        )

        restart_classification = {
            "classification": "STRUCTURAL_RESTART_INCOMPATIBILITY",
            "E1_execution_result": "A3_E1_PASS_REPRESENTATION_ONLY",
            "refreshed_X13_reconstructed": True,
            "input_domain_audit_completed": True,
            "historical_checkpoint_input_shape": [201, 13],
            "historical_parent_state_input_channels": parent_state_channels,
            "historical_parent_state_input_channel_count": len(parent_state_channels),
            "historical_temporal_semantics": {
                "target_time_hat": "absolute target day / 1000",
                "target_eta_sequence": "absolute target seconds / terminal Pollock TOF",
            },
            "day365_refreshed_state_is_a_restart_parent_state": True,
            "direct_day365_to_day500_checkpoint_restart_authority": False,
            "delta_time_135d_substitution_authorized": False,
            "absolute_day500_substitution_as_restart_authorized": False,
            "checkpoint_committed_reuse": False,
            "A3_E2_checkpoint_test_authorized": False,
            "teacher_backed_test_authorized_now": False,
            "AV4_dynamic_transport_execution_authorized": False,
            "automatic_retraining": False,
            "required_before_any_checkpoint_test": [
                "freeze and pass a mass-conservative grid-to-streamline parent-state projection",
                "freeze an explicit restart temporal contract",
                "provide sufficient parent-state information in a restartable model signature or state-conditioned AV4 transport architecture",
                "preserve frozen TRAIN-only normalization and no-OOD-tuning firewalls",
            ],
            "scientific_interpretation": (
                "The refreshed Day365 state can be represented in the historical 13-channel coordinates, "
                "but the historical checkpoint signature does not encode the parent/current saturation or "
                "component-mass state required to define a Day365->future restart mapping. Representation "
                "compatibility therefore does not establish restart-state semantic compatibility."
            ),
        }

        # ------------------------------------------------------------------------------------------
        # Firewalls and PASS publication.
        # ------------------------------------------------------------------------------------------
        gate("checkpoint_model_loaded_false", checkpoint_model_loaded is False)
        gate("checkpoint_inference_performed_false", checkpoint_inference_performed is False)
        gate("teacher_transport_performed_false", teacher_transport_performed is False)
        gate("physical_time_advanced_false", physical_time_advanced is False)
        gate("normalization_refit_false", True)
        gate("training_performed_false", True)
        gate("checkpoint_reselected_false", True)
        gate("mapback_performed_false", True)
        gate("locked_OOD_used_for_tuning_false", True)
        gate("CMG_validation_performed_false", True)
        gate("AV3_checkpoint_committed_reuse_false", True)
        gate("A3_E2_authorized_false", True)
        gate("AV4_dynamic_transport_authorized_false", True)

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "control_realization": CONTROL_REALIZATION,
            "paired_porosity": CONTROL_POROSITY,
            "partition": CONTROL_PARTITION,
            "canonical_day": CONTROL_DAY,
            "refreshed_flow_epoch_sha256": m2e[A2E_EPOCH],
            "historical_checkpoint_sha256": EXPECTED_CHECKPOINT_SHA256,
            "refreshed_X13_shape": list(Xref.shape),
            "channel_order": CHANNELS13,
            "historical_TRAIN_profiles": int(np.sum(train_mask)),
            "historical_validation_day365_profiles": int(np.sum(val365_mask)),
            "pressure_normalization_mean_psi": pmean,
            "pressure_normalization_std_psi": pstd,
            "ADV_relative_L2_residual": float(adv_audit["relative_L2_residual"]),
            "classification": "STRUCTURAL_RESTART_INCOMPATIBILITY",
            "representation_only_PASS": True,
            "checkpoint_model_loaded": False,
            "checkpoint_inference": False,
            "teacher_transport": False,
            "physical_time_advance": False,
            "AV3_checkpoint_committed_reuse": False,
            "AV4_A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "representation_reconstruction_PASS": True,
            "input_domain_audit_completed": True,
            "geometry_TOF_shift_audit_completed": True,
            "structural_restart_incompatibility": True,
            "checkpoint_reuse_authorized": False,
            "A3_E2_checkpoint_test_authorized": False,
            "teacher_backed_test_authorized_now": False,
            "AV4_dynamic_transport_execution_authorized": False,
            "automatic_retraining_authorized": False,
            "next_required_work": (
                "Freeze a state-conditioned restartable AV4 transport architecture together with "
                "a mass-conservative parent-state projection and explicit restart temporal contract "
                "before any checkpoint inference or teacher-backed restart test."
            ),
        }

        refreshed_npz = deterministic_npz_bytes(
            {
                "X_refreshed_13": Xref,
                "channel_names": np.asarray(CHANNELS13, dtype="U32"),
                "streamline_index": np.arange(NSL, dtype=np.int64),
                "target_time_days": np.full(NSL, CONTROL_DAY, dtype=np.float64),
                "target_time_hat": np.full(NSL, CONTROL_DAY / 1000.0, dtype=np.float32),
                "target_eta_sequence": target_eta.astype(np.float32),
                "terminal_pollock_tof_s": tau_end.astype(np.float64),
                "adv_travel_time_grid_s": np.asarray(adv_grid, dtype=np.float64),
                "historical_validation_day365_X13": Xval365.astype(np.float32),
            }
        )

        output_files = {
            "PAD_Stream_POSTV16_AV4_A3_E1_R2_Summary.json":
                json_bytes(summary),
            "POSTV16_AV4_A3_E1_R2_Refreshed_Day365_13Channel_Representation.npz":
                refreshed_npz,
            "POSTV16_AV4_A3_E1_R2_Channel_Input_Domain_Audit.csv":
                csv_bytes(channel_rows),
            "POSTV16_AV4_A3_E1_R2_Historical_AV3CR0003_Day365_Comparison.csv":
                csv_bytes(baseline_rows),
            "POSTV16_AV4_A3_E1_R2_Geometry_TOF_Shift_Audit.json":
                json_bytes(geometry_audit),
            "POSTV16_AV4_A3_E1_R2_ADV_Reconstruction_Audit.json":
                json_bytes(adv_output_audit),
            "POSTV16_AV4_A3_E1_R2_Structural_Restart_Compatibility_Classification.json":
                json_bytes(restart_classification),
            "POSTV16_AV4_A3_E1_R2_Decision_Contract.json":
                json_bytes(decision),
            "POSTV16_AV4_A3_E1_R2_Final_Gate_Matrix.csv":
                csv_bytes(
                    [{"gate": name, **value} for name, value in gates.items()]
                ),
        }

        immutable_publish(out, output_files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV4_A3_E1_R2_Artifact_Manifest.csv":
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
                "POSTV16_AV4_A3_E1_R2_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print()
        print("=" * 214)
        print(f"{MILESTONE}: REPRESENTATION-ONLY PASS / STRUCTURAL RESTART INCOMPATIBILITY")
        print("=" * 214)
        print("Refreshed Day365 X13 shape               :", Xref.shape)
        print("Historical TRAIN profiles                :", int(np.sum(train_mask)))
        print("Historical AV3CR0003 Day365 profiles     :", int(np.sum(val365_mask)))
        print("ADV relative L2 residual                 :", adv_audit["relative_L2_residual"])
        print("Checkpoint model loaded / inference      : False / False")
        print("Teacher transport / physical time advance: False / False")
        print("Structural restart compatibility         : False")
        print("AV3 checkpoint committed reuse           : False")
        print("A3-E2 checkpoint test                    : NOT AUTHORIZED")
        print("AV4 dynamic transport                    : NOT AUTHORIZED")
        print("NEXT REQUIRED WORK                       : state-conditioned restart architecture + conservative parent-state projection + explicit restart temporal contract")
        print("=" * 214)

        return 0

    except ScientificFail as exc:
        failed.mkdir(parents=True, exist_ok=True)

        report = {
            "milestone": MILESTONE,
            "status": STATUS_FAIL,
            "failed_stage": stage,
            "failed_gate": exc.gate,
            "detail": exc.detail,
            "gates": gates,
            "reconstruction_started": reconstruction_started,
            "checkpoint_model_loaded": checkpoint_model_loaded,
            "checkpoint_inference_performed": checkpoint_inference_performed,
            "teacher_transport_performed": teacher_transport_performed,
            "physical_time_advanced": physical_time_advanced,
            "AV3_checkpoint_committed_reuse": False,
            "AV4_A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
            "automatic_rerun_authorized": False,
        }

        data = json_bytes(report)
        p = failed / "POSTV16_AV4_A3_E1_R2_Scientific_Fail_Report.json"

        if p.exists() and p.read_bytes() != data:
            suffix = hashlib.sha256(data).hexdigest()[:12]
            p = failed / f"POSTV16_AV4_A3_E1_R2_Scientific_Fail_Report_{suffix}.json"

        if not p.exists():
            p.write_bytes(data)

        print()
        print("=" * 214)
        print(f"{MILESTONE}: SCIENTIFIC RECONSTRUCTION FAIL")
        print("=" * 214)
        print("Stage      :", stage)
        print("Failed gate:", exc.gate)
        print("Detail     :", exc.detail)
        print("NO AUTOMATIC RERUN AUTHORIZED.")
        print("=" * 214)

        return 3

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)

        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "reconstruction_started": reconstruction_started,
            "checkpoint_model_loaded": checkpoint_model_loaded,
            "checkpoint_inference_performed": checkpoint_inference_performed,
            "teacher_transport_performed": teacher_transport_performed,
            "physical_time_advanced": physical_time_advanced,
            "AV3_checkpoint_committed_reuse": False,
            "AV4_A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
            "automatic_rerun_authorized": False,
        }

        data = json_bytes(report)
        p = blocked / "POSTV16_AV4_A3_E1_R2_Blocked_Report.json"

        if p.exists() and p.read_bytes() != data:
            suffix = hashlib.sha256(data).hexdigest()[:12]
            p = blocked / f"POSTV16_AV4_A3_E1_R2_Blocked_Report_{suffix}.json"

        if not p.exists():
            p.write_bytes(data)

        print()
        print("=" * 214)
        print(f"{MILESTONE}: TECHNICAL / AUTHORITY BLOCK")
        print("=" * 214)
        print("Stage    :", stage)
        print("Exception:", repr(exc))
        print("NO AUTOMATIC RERUN AUTHORIZED.")
        print("=" * 214)

        return 2


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", type=Path, default=Path("."))
    p.add_argument(
        "--drive-root",
        type=Path,
        default=Path("/content/drive/MyDrive/PAD_Stream_Compute"),
    )
    p.add_argument("--self-test", action="store_true")
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
