from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import json
import os
import shutil
import traceback

import numpy as np

# =============================================================================
# PAD-Stream V16E-24
# Historical 100-Day Reference-Truth Freeze / Provenance Manifest
# =============================================================================
#
# FORMAL REFERENCE-TRUTH FREEZE ONLY.
# NO CHANGE TO THE V16E-18-R1 FROZEN V16 DEPLOYMENT CANDIDATE.
# NO CHANGE TO THE V16E-22-R4 UNFROZEN SOURCE REFERENCE CANDIDATE.
# NO CHANGE TO THE V16E-23 INDEPENDENT VALIDATION ARTIFACTS.
# NO DEPLOYMENT GATE EVALUATION IN E24.
# NO V16 PERFORMANCE USED TO DEFINE OR FREEZE HISTORICAL REFERENCE TRUTH.
# NO SG7E THRESHOLD CHANGE: authoritative historical threshold remains S >= 0.5.
# 0.21 REMAINS DIAGNOSTIC-ONLY AND IS NOT USED IN E24.
# NO TRAINING / CHECKPOINT LOAD / MODEL INFERENCE.
# NO PRESSURE / DARCY / POLLOCK / TOF / MAP-BACK / TRANSPORT RECOMPUTATION.
#
# PURPOSE
# -------
# V16E-23 independently reconstructed and validated the historical SG7E 100-day
# reference truth against the V16E-22-R4 candidate with bitwise equality,
# L1 = 0, Linf = 0, and exact S>=0.5 plume-mask identity. E23 explicitly
# required the E24 freeze mode to be a byte-for-byte copy of the independently
# validated E22-R4 candidate.
#
# E24 therefore:
#   1) binds the complete accepted E23 artifact set by exact SHA-256;
#   2) revalidates E23 PASS / freeze-readiness semantics;
#   3) binds and revalidates the exact E22-R4 candidate source;
#   4) revalidates E23 independent numerical equality to E22-R4;
#   5) copies the E22-R4 candidate BYTE-FOR-BYTE into a new immutable frozen
#      reference-truth path;
#   6) verifies source/frozen file-byte identity and array/mask identity;
#   7) emits the formal reference-truth freeze/provenance manifest;
#   8) declares deployment-gate evaluation ELIGIBLE for E25, but evaluates no
#      deployment gate in E24.
# =============================================================================

MILESTONE = "V16E-24"
SUCCESS = "V16E24_HISTORICAL_100DAY_REFERENCE_TRUTH_FREEZE_PASS"
BLOCKED = "V16E24_HISTORICAL_100DAY_REFERENCE_TRUTH_FREEZE_BLOCKED"
NEXT_PASS = "V16E-25 - Frozen Historical Reference / Frozen V16 Candidate Deployment-Gate Evaluation"
NEXT_FAIL = "V16E-24-R1 - Repair only the failed V16E-24 reference-freeze/provenance gate; preserve E22-R4, E23, and E18-R1 unchanged"

EXPECTED_GRID = (15, 50, 50)
EXPECTED_REFERENCE_KEY = "SG7A_corrected"
EXPECTED_TIME_DAYS = 100.0
EXPECTED_THRESHOLD = 0.5
EXPECTED_DTYPE = np.dtype("float64")
EXPECTED_REFERENCE_ARRAY_SHA = "6135585d5dadd02f6ba2bcd2dd860c9a681d006526823c4e391e40f9f7f9ddd6"
EXPECTED_REFERENCE_MASK_SHA = "08458e742f2866096346e56ff69fb3c9be183b68623d09cd518778326dfe180b"
EXPECTED_PLUME_CELLS = 6084
EXPECTED_FOOTPRINT_CELLS = 724
EXPECTED_VERTICAL_EXTENT = 15

# Existing frozen V16 deployment candidate. This is NOT the reference truth.
EXPECTED_V16_FROZEN_SHA = "d422dc1e56281c1baf0ae007c62ce4bd69677a232bd1448a5bd79d3177eafaea"
E18_FROZEN_REL = Path(
    "provenance/hybrid_dp/V16E18_R1_FROZEN_SGSIM_100D_FULL_GRID_CANDIDATE/"
    "frozen_full_grid/V16E18_R1_Frozen_SGSim_100Day_Full_Grid_Candidate.npz"
)

# Accepted E22-R4 unfrozen historical-reference candidate authority.
E22R4_RUNNER_NAME = "PAD_Stream_V16E22_R4_Tracked_JSON_Canonical_Identity_Repair_and_Historical_Numerical_Recovery.py"
E22R4_RUNNER_SHA = "ea445ba686a5a261302da92dd0d03f93f10cd4f61aca827ff22646952e9eb13c"
E22R4_DIR_REL = Path(
    "provenance/hybrid_dp/"
    "V16E22_R4_HISTORICAL_R14_NUMERICAL_RECOVERY_100DAY_REFERENCE_TRUTH_LINEAGE_RECONSTRUCTION_AUDIT"
)
E22R4_CANDIDATE_NAME = "V16E22_R4_Historical_SG7E_100Day_Reference_Truth_Candidate.npz"
E22R4_CANDIDATE_FILE_SHA = "e78b87bf860776906d9a1862f4de252a9c2ddad21dc6ff02a15ac703a196b08f"

# Accepted E23 independent-validation authority.
E23_RUNNER_NAME = "PAD_Stream_V16E23_Independent_Historical_100Day_Reference_Truth_Reconstruction_Validation_and_Freeze_Readiness.py"
E23_RUNNER_SHA = "7b1ec6397c48f9d01441e29944900c2d1a61bed9a2203fa4e012f227d68e3184"
E23_DIR_REL = Path(
    "provenance/hybrid_dp/"
    "V16E23_INDEPENDENT_HISTORICAL_100DAY_REFERENCE_TRUTH_VALIDATION_FREEZE_READINESS"
)
E23_ARTIFACTS = {
    "V16E23_Independent_Historical_100Day_Reference_Reconstruction.npz":
        "edb6d4020549a9f0edfb746c64d4f9e8beb18da9712e8d59b8e12e25baabe499",
    "V16E23_Independent_Reference_Truth_Validation_Contract.json":
        "e0c1cfd3b6eb56a9f76de0aec1c7f354e97addc62d89780b316920742f499b78",
    "V16E23_Reference_Truth_Freeze_Readiness_Manifest.json":
        "6dcfb227a3fbaf0f5231ab3624120495d0f58f715cd6640a66bd7b6e50851bc3",
    "PAD_Stream_V16E23_Summary.json":
        "9c299476e8bdbe2d60be6b655684e4ab96adeff6a3d13ef7dc7f5edbad3c08d9",
    "V16E23_Handoff.md":
        "57817a03cc895e1edb42effde1c9548438619140737edf914c73982eb5f24eb9",
    "V16E23_E22R4_Authority.csv":
        "9b676dab3e34dc9a7161d4a8e0e1adfa14916a3aab7cdf02c1f2f01dfc93bb39",
    "V16E23_Recovery_Bundle_Independent_Validation.csv":
        "b0113ed71e68961fd26c773bafa66966eef07ef5c30fad329b43fa73fd95aa21",
    "V16E23_Independent_Reconstruction_Identity.csv":
        "95baeeeefd4c69cb50499d13094226fae82962531432033a523c55cee538abdc",
    "V16E23_Freeze_Readiness_Matrix.csv":
        "a3c93a3d3bab1051eac4a616c70c401e5b1283d439a4905fa16c11a024be3b6f",
    "V16E23_Final_Gate_Matrix.csv":
        "45224b63c5b7c8852c094434b4001cc35d268c54d086c7d21b5bc48e42e7195c",
}
E23_NUMERICAL_NAME = "V16E23_Independent_Historical_100Day_Reference_Reconstruction.npz"
E23_CONTRACT_NAME = "V16E23_Independent_Reference_Truth_Validation_Contract.json"
E23_READINESS_NAME = "V16E23_Reference_Truth_Freeze_Readiness_Manifest.json"
E23_SUMMARY_NAME = "PAD_Stream_V16E23_Summary.json"
E23_GATE_NAME = "V16E23_Final_Gate_Matrix.csv"

OUT_REL = Path("provenance/hybrid_dp/V16E24_FROZEN_HISTORICAL_100DAY_REFERENCE_TRUTH")
BLOCKED_REL = Path("provenance/hybrid_dp/V16E24_BLOCKED_HISTORICAL_100DAY_REFERENCE_TRUTH_FREEZE")
FROZEN_SUBDIR = "frozen_reference"
FROZEN_NAME = "V16E24_Frozen_Historical_SG7E_100Day_Reference_Truth.npz"


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_array(arr) -> str:
    a = np.ascontiguousarray(arr)
    return hashlib.sha256(a.tobytes()).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def load_csv(path: Path):
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_csv(path: Path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def boolish(v) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"true", "1", "yes", "pass"}


def scalar(db, key):
    return np.asarray(db[key]).reshape(()).item()


def morphology(mask):
    mask = np.asarray(mask, dtype=bool)
    plume_cells = int(mask.sum())
    footprint_cells = int(np.any(mask, axis=0).sum())
    active_layers = np.where(np.any(mask, axis=(1, 2)))[0]
    if len(active_layers):
        zmin = int(active_layers[0])
        zmax = int(active_layers[-1])
        extent = int(zmax - zmin + 1)
    else:
        zmin = zmax = -1
        extent = 0
    pts = np.argwhere(mask)
    centroid = [None, None, None] if not len(pts) else [float(x) for x in pts.mean(axis=0)]
    return {
        "plume_cells": plume_cells,
        "footprint_cells": footprint_cells,
        "vertical_extent_layers": extent,
        "zmin_layer_zero_based": zmin,
        "zmax_layer_zero_based": zmax,
        "centroid_kji": centroid,
    }


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL
    frozen_dir = out / FROZEN_SUBDIR
    frozen_path = frozen_dir / FROZEN_NAME

    manifest_out = out / "V16E24_Historical_100Day_Reference_Truth_Freeze_Manifest.json"
    contract_out = out / "V16E24_Reference_Truth_Provenance_Contract.json"
    summary_out = out / "PAD_Stream_V16E24_Summary.json"
    handoff_out = out / "V16E24_Handoff.md"
    authority_csv = out / "V16E24_E23_Authority.csv"
    identity_csv = out / "V16E24_Frozen_Reference_Identity.csv"
    lineage_csv = out / "V16E24_Freeze_Lineage.csv"
    readiness_csv = out / "V16E24_Deployment_Evaluation_Readiness.csv"
    gate_csv = out / "V16E24_Final_Gate_Matrix.csv"
    blocked_json = blocked / "V16E24_Blocked_Historical_100Day_Reference_Truth_Freeze.json"

    gates = {}

    def gate(name, ok, detail=""):
        ok = bool(ok)
        gates[name] = {"passed": ok, "detail": str(detail)}
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""), flush=True)
        if not ok:
            raise GateError(name)

    print("\n" + "=" * 132)
    print("PAD-Stream V16E-24 Historical 100-Day Reference-Truth Freeze / Provenance Manifest")
    print("=" * 132)
    print("FORMAL REFERENCE-TRUTH FREEZE ONLY. BYTE-FOR-BYTE COPY OF THE INDEPENDENTLY VALIDATED E22-R4 CANDIDATE.")
    print("NO DEPLOYMENT GATE EVALUATION. NO V16 PERFORMANCE USED. NO THRESHOLD CHANGE. 0.21 REMAINS DIAGNOSTIC-ONLY.")

    e22_candidate_path = drive / E22R4_DIR_REL / E22R4_CANDIDATE_NAME
    e23_dir = drive / E23_DIR_REL
    e18_frozen = drive / E18_FROZEN_REL
    source_sha_before = None
    v16_sha_before = None

    try:
        # ------------------------------------------------------------------
        # Accepted source-code authorities.
        # ------------------------------------------------------------------
        print("\nSOURCE AUTHORITY")
        e23_runner = root / E23_RUNNER_NAME
        gate("E23_runner_exists", e23_runner.is_file(), e23_runner)
        gate("E23_runner_SHA_exact", sha256_file(e23_runner) == E23_RUNNER_SHA, sha256_file(e23_runner))

        e22_runner = root / E22R4_RUNNER_NAME
        gate("E22R4_runner_exists", e22_runner.is_file(), e22_runner)
        gate("E22R4_runner_SHA_exact", sha256_file(e22_runner) == E22R4_RUNNER_SHA, sha256_file(e22_runner))

        # ------------------------------------------------------------------
        # Complete E23 persisted-artifact authority.
        # ------------------------------------------------------------------
        print("\nV16E-23 ACCEPTED INDEPENDENT-VALIDATION AUTHORITY")
        authority_rows = []
        for name, expected_sha in E23_ARTIFACTS.items():
            path = e23_dir / name
            gate(f"E23_{name}_exists", path.is_file(), path)
            actual = sha256_file(path)
            gate(f"E23_{name}_SHA_exact", actual == expected_sha, actual)
            authority_rows.append({
                "artifact": name,
                "path": str(path),
                "sha256": actual,
                "exact": True,
            })

        e23_summary = load_json(e23_dir / E23_SUMMARY_NAME)
        e23_contract = load_json(e23_dir / E23_CONTRACT_NAME)
        e23_ready = load_json(e23_dir / E23_READINESS_NAME)
        e23_gates = load_csv(e23_dir / E23_GATE_NAME)

        gate("E23_summary_status_PASS", e23_summary.get("status") == "PASS")
        gate("E23_contract_status_exact", e23_contract.get("status") == "V16E23_INDEPENDENT_HISTORICAL_100DAY_REFERENCE_TRUTH_VALIDATION_PASS")
        gate("E23_all_recorded_gates_pass", bool(e23_gates) and all(boolish(r.get("passed")) for r in e23_gates))
        gate("E23_next_is_E24", e23_summary.get("next_milestone") == "V16E-24 - Historical 100-Day Reference-Truth Freeze / Provenance Manifest")
        gate("E23_reference_key_exact", e23_summary.get("historical_reference_key") == EXPECTED_REFERENCE_KEY)
        gate("E23_time_100d_exact", float(e23_summary.get("physical_time_days")) == EXPECTED_TIME_DAYS)
        gate("E23_threshold_0p5_exact", float(e23_summary.get("historical_authoritative_plume_threshold")) == EXPECTED_THRESHOLD)
        gate("E23_independent_array_hash_exact", e23_summary.get("independent_reference_array_sha256") == EXPECTED_REFERENCE_ARRAY_SHA)
        gate("E23_independent_mask_hash_exact", e23_summary.get("independent_reference_mask_sha256") == EXPECTED_REFERENCE_MASK_SHA)
        gate("E23_bitwise_exact", e23_summary.get("independent_reconstruction_bitwise_exact") is True)
        gate("E23_L1_zero", float(e23_summary.get("independent_reconstruction_L1")) == 0.0)
        gate("E23_Linf_zero", float(e23_summary.get("independent_reconstruction_Linf")) == 0.0)
        gate("E23_morphology_exact", (
            int(e23_summary.get("independent_plume_cells")) == EXPECTED_PLUME_CELLS and
            int(e23_summary.get("independent_footprint_cells")) == EXPECTED_FOOTPRINT_CELLS and
            int(e23_summary.get("independent_vertical_extent_layers")) == EXPECTED_VERTICAL_EXTENT
        ))
        gate("E23_freeze_ready", e23_summary.get("freeze_ready") is True and e23_ready.get("ready_for_V16E24_freeze") is True)
        gate("E23_freeze_mode_byte_copy_exact", e23_ready.get("freeze_mode_required") == "byte-for-byte copy of the independently validated E22-R4 candidate")
        gate("E23_reference_still_unfrozen", e23_summary.get("reference_candidate_frozen") is False and e23_ready.get("reference_candidate_frozen") is False)
        gate("E23_no_candidate_performance_used", e23_summary.get("candidate_performance_used") is False)
        gate("E23_no_deployment_evaluation", e23_summary.get("deployment_pass_fail_evaluated") is False)
        gate("E23_historical_truth_not_regenerated", e23_summary.get("historical_truth_regenerated") is False)
        gate("E23_V16_frozen_candidate_unchanged", e23_summary.get("V16_frozen_candidate_modified") is False)
        gate("E23_full_grid_plume_not_authorized", e23_summary.get("full_grid_plume_authorized") is False)
        gate("E23_internal_test_OOD_closed", e23_summary.get("internal_test_reopened") is False and e23_summary.get("OOD_reopened") is False)

        # ------------------------------------------------------------------
        # Revalidate E22-R4 source candidate and E23 independent reconstruction.
        # ------------------------------------------------------------------
        print("\nSOURCE REFERENCE / INDEPENDENT NUMERICAL IDENTITY")
        gate("E22R4_candidate_exists", e22_candidate_path.is_file(), e22_candidate_path)
        source_sha_before = sha256_file(e22_candidate_path)
        gate("E22R4_candidate_file_SHA_exact", source_sha_before == E22R4_CANDIDATE_FILE_SHA, source_sha_before)
        gate("E23_summary_E22R4_candidate_file_SHA_exact", e23_summary.get("E22R4_candidate_file_sha256") == source_sha_before)
        gate("E23_readiness_E22R4_candidate_file_SHA_exact", e23_ready.get("reference_candidate_file_sha256") == source_sha_before)

        with np.load(e22_candidate_path, allow_pickle=False) as db:
            expected_e22_keys = {
                "reference_truth_100d_native",
                "reference_plume_mask_100d_0p5",
                "physical_time_days",
                "plume_threshold",
                "source_reference_key",
                "source_multi_time_reference_array_sha256",
                "source_100d_snapshot_array_sha256",
                "source_R14_recovered_numerical_file_sha256",
                "source_recovery_bundle_sha256",
            }
            gate("E22R4_candidate_keys_exact", set(db.files) == expected_e22_keys, sorted(db.files))
            candidate = np.array(db["reference_truth_100d_native"], copy=True)
            candidate_mask = np.asarray(db["reference_plume_mask_100d_0p5"], dtype=np.uint8)
            candidate_time = float(scalar(db, "physical_time_days"))
            candidate_threshold = float(scalar(db, "plume_threshold"))
            candidate_key = str(scalar(db, "source_reference_key"))

        gate("E22R4_candidate_shape_exact", candidate.shape == EXPECTED_GRID, candidate.shape)
        gate("E22R4_candidate_dtype_exact", candidate.dtype == EXPECTED_DTYPE, candidate.dtype)
        gate("E22R4_candidate_time_exact", candidate_time == EXPECTED_TIME_DAYS, candidate_time)
        gate("E22R4_candidate_threshold_exact", candidate_threshold == EXPECTED_THRESHOLD, candidate_threshold)
        gate("E22R4_candidate_reference_key_exact", candidate_key == EXPECTED_REFERENCE_KEY, candidate_key)
        gate("E22R4_candidate_array_SHA_exact", sha256_array(candidate) == EXPECTED_REFERENCE_ARRAY_SHA, sha256_array(candidate))
        gate("E22R4_candidate_mask_SHA_exact", sha256_array(candidate_mask) == EXPECTED_REFERENCE_MASK_SHA, sha256_array(candidate_mask))
        gate("E22R4_candidate_mask_threshold_exact", np.array_equal(candidate_mask, (candidate >= EXPECTED_THRESHOLD).astype(np.uint8)))

        e23_numerical = e23_dir / E23_NUMERICAL_NAME
        with np.load(e23_numerical, allow_pickle=False) as db:
            required_e23_keys = {
                "independently_reconstructed_reference_truth_100d_native",
                "independently_reconstructed_plume_mask_100d_0p5",
                "physical_time_days",
                "plume_threshold",
                "reference_snapshot_array_sha256",
                "reference_plume_mask_array_sha256",
                "source_E22R4_candidate_file_sha256",
                "source_recovery_bundle_sha256",
                "source_R14_numerical_file_sha256",
            }
            gate("E23_independent_numerical_keys_exact", set(db.files) == required_e23_keys, sorted(db.files))
            independent = np.array(db["independently_reconstructed_reference_truth_100d_native"], copy=True)
            independent_mask = np.asarray(db["independently_reconstructed_plume_mask_100d_0p5"], dtype=np.uint8)
            independent_time = float(scalar(db, "physical_time_days"))
            independent_threshold = float(scalar(db, "plume_threshold"))
            recorded_array_hash = str(scalar(db, "reference_snapshot_array_sha256"))
            recorded_mask_hash = str(scalar(db, "reference_plume_mask_array_sha256"))
            recorded_source_file_hash = str(scalar(db, "source_E22R4_candidate_file_sha256"))

        gate("E23_independent_shape_exact", independent.shape == EXPECTED_GRID, independent.shape)
        gate("E23_independent_dtype_exact", independent.dtype == EXPECTED_DTYPE, independent.dtype)
        gate("E23_independent_time_exact", independent_time == EXPECTED_TIME_DAYS, independent_time)
        gate("E23_independent_threshold_exact", independent_threshold == EXPECTED_THRESHOLD, independent_threshold)
        gate("E23_independent_array_SHA_exact_recomputed", sha256_array(independent) == recorded_array_hash == EXPECTED_REFERENCE_ARRAY_SHA)
        gate("E23_independent_mask_SHA_exact_recomputed", sha256_array(independent_mask) == recorded_mask_hash == EXPECTED_REFERENCE_MASK_SHA)
        gate("E23_independent_source_file_SHA_exact", recorded_source_file_hash == source_sha_before)
        gate("E23_independent_bitwise_exact_to_E22R4", np.array_equal(independent, candidate))
        gate("E23_independent_mask_exact_to_E22R4", np.array_equal(independent_mask, candidate_mask))

        diff = independent.astype(np.float64) - candidate.astype(np.float64)
        gate("E23_revalidated_L1_zero", float(np.mean(np.abs(diff))) == 0.0)
        gate("E23_revalidated_Linf_zero", float(np.max(np.abs(diff))) == 0.0)

        morph = morphology(candidate_mask)
        gate("reference_plume_cells_exact", morph["plume_cells"] == EXPECTED_PLUME_CELLS, morph["plume_cells"])
        gate("reference_footprint_cells_exact", morph["footprint_cells"] == EXPECTED_FOOTPRINT_CELLS, morph["footprint_cells"])
        gate("reference_vertical_extent_exact", morph["vertical_extent_layers"] == EXPECTED_VERTICAL_EXTENT, morph["vertical_extent_layers"])

        # ------------------------------------------------------------------
        # Preserve V16 deployment candidate immutability before freeze.
        # ------------------------------------------------------------------
        print("\nV16 FROZEN DEPLOYMENT-CANDIDATE IMMUTABILITY")
        gate("E18R1_frozen_V16_candidate_exists", e18_frozen.is_file(), e18_frozen)
        v16_sha_before = sha256_file(e18_frozen)
        gate("E18R1_frozen_V16_candidate_SHA_exact_before", v16_sha_before == EXPECTED_V16_FROZEN_SHA, v16_sha_before)

        # ------------------------------------------------------------------
        # FORMAL REFERENCE FREEZE: byte-for-byte copy only.
        # ------------------------------------------------------------------
        print("\nFORMAL HISTORICAL 100-DAY REFERENCE-TRUTH FREEZE")
        out.mkdir(parents=True, exist_ok=True)
        frozen_dir.mkdir(parents=True, exist_ok=True)

        if frozen_path.exists():
            gate("existing_frozen_reference_SHA_exact", sha256_file(frozen_path) == source_sha_before, sha256_file(frozen_path))
            gate("existing_frozen_reference_bytes_exact", frozen_path.read_bytes() == e22_candidate_path.read_bytes())
        else:
            tmp = frozen_path.with_suffix(frozen_path.suffix + ".tmp")
            if tmp.exists():
                tmp.unlink()
            shutil.copyfile(e22_candidate_path, tmp)
            gate("temporary_frozen_reference_SHA_exact", sha256_file(tmp) == source_sha_before, sha256_file(tmp))
            gate("temporary_frozen_reference_bytes_exact", tmp.read_bytes() == e22_candidate_path.read_bytes())
            os.replace(tmp, frozen_path)
            gate("frozen_reference_created", frozen_path.is_file(), frozen_path)

        frozen_sha = sha256_file(frozen_path)
        gate("frozen_reference_file_SHA_equals_source", frozen_sha == source_sha_before == E22R4_CANDIDATE_FILE_SHA, frozen_sha)
        gate("frozen_reference_byte_identity_exact", frozen_path.read_bytes() == e22_candidate_path.read_bytes())

        with np.load(frozen_path, allow_pickle=False) as db:
            frozen = np.array(db["reference_truth_100d_native"], copy=True)
            frozen_mask = np.asarray(db["reference_plume_mask_100d_0p5"], dtype=np.uint8)
            frozen_time = float(scalar(db, "physical_time_days"))
            frozen_threshold = float(scalar(db, "plume_threshold"))
            frozen_key = str(scalar(db, "source_reference_key"))

        gate("frozen_reference_shape_exact", frozen.shape == EXPECTED_GRID, frozen.shape)
        gate("frozen_reference_dtype_exact", frozen.dtype == EXPECTED_DTYPE, frozen.dtype)
        gate("frozen_reference_time_exact", frozen_time == EXPECTED_TIME_DAYS, frozen_time)
        gate("frozen_reference_threshold_exact", frozen_threshold == EXPECTED_THRESHOLD, frozen_threshold)
        gate("frozen_reference_key_exact", frozen_key == EXPECTED_REFERENCE_KEY, frozen_key)
        gate("frozen_reference_array_SHA_exact", sha256_array(frozen) == EXPECTED_REFERENCE_ARRAY_SHA, sha256_array(frozen))
        gate("frozen_reference_mask_SHA_exact", sha256_array(frozen_mask) == EXPECTED_REFERENCE_MASK_SHA, sha256_array(frozen_mask))
        gate("frozen_reference_array_bitwise_exact_to_E22R4", np.array_equal(frozen, candidate))
        gate("frozen_reference_array_bitwise_exact_to_E23_independent", np.array_equal(frozen, independent))
        gate("frozen_reference_mask_exact_to_E22R4", np.array_equal(frozen_mask, candidate_mask))
        gate("frozen_reference_mask_exact_to_E23_independent", np.array_equal(frozen_mask, independent_mask))

        # ------------------------------------------------------------------
        # Post-freeze immutable-source checks and scientific firewalls.
        # ------------------------------------------------------------------
        gate("E22R4_source_candidate_unchanged_after_freeze", sha256_file(e22_candidate_path) == source_sha_before)
        gate("E23_independent_artifact_unchanged_after_freeze", sha256_file(e23_numerical) == E23_ARTIFACTS[E23_NUMERICAL_NAME])
        gate("E18R1_frozen_V16_candidate_SHA_exact_after", sha256_file(e18_frozen) == v16_sha_before == EXPECTED_V16_FROZEN_SHA)
        gate("historical_threshold_remains_0p5", True)
        gate("diagnostic_0p21_not_used_in_E24", True)
        gate("no_V16_candidate_performance_used_in_E24", True)
        gate("no_deployment_gate_evaluated_in_E24", True)
        gate("historical_truth_not_regenerated_in_E24", True)
        gate("reference_truth_frozen_in_E24", True)
        gate("full_grid_plume_not_authorized_in_E24", True)
        gate("internal_test_not_reopened", True)
        gate("OOD_not_reopened", True)
        gate("E25_deployment_gate_evaluation_eligible", True)

        # ------------------------------------------------------------------
        # Persist formal freeze/provenance records.
        # ------------------------------------------------------------------
        save_csv(authority_csv, authority_rows)

        save_csv(identity_csv, [{
            "role": "authoritative_frozen_historical_100day_reference_truth",
            "reference_key": EXPECTED_REFERENCE_KEY,
            "physical_time_days": EXPECTED_TIME_DAYS,
            "plume_threshold": EXPECTED_THRESHOLD,
            "path": str(frozen_path),
            "file_sha256": frozen_sha,
            "array_sha256": sha256_array(frozen),
            "plume_mask_sha256": sha256_array(frozen_mask),
            "dtype": str(frozen.dtype),
            "shape": "x".join(str(x) for x in frozen.shape),
            "plume_cells": morph["plume_cells"],
            "footprint_cells": morph["footprint_cells"],
            "vertical_extent_layers": morph["vertical_extent_layers"],
            "byte_identical_to_E22R4_source": True,
            "bitwise_identical_to_E23_independent": True,
        }])

        save_csv(lineage_csv, [
            {"order": 1, "milestone": "V15-SG7E1R14", "role": "Historical multi-time reference reconstruction", "decision": "SG7A_corrected at [100,250,500,1000] days; S>=0.5 authority preserved"},
            {"order": 2, "milestone": "V16E-21", "role": "Threshold/reference provenance reconciliation", "decision": "Historical S>=0.5 retained; 0.21 diagnostic-only; reference lineage required"},
            {"order": 3, "milestone": "V16E-22-R4", "role": "100-day reference candidate reconstruction", "decision": "Original historical R14 numerical truth authenticated; unique 100-day candidate created unfrozen"},
            {"order": 4, "milestone": "V16E-23", "role": "Independent reference validation", "decision": "Independent 100-day reconstruction bitwise exact; L1=0; Linf=0; freeze ready"},
            {"order": 5, "milestone": "V16E-24", "role": "Formal reference freeze", "decision": "Independently validated E22-R4 candidate copied byte-for-byte and frozen as authoritative historical 100-day reference truth"},
        ])

        save_csv(readiness_csv, [
            {"criterion": "Historical 100-day reference truth frozen", "ready": True, "evidence": frozen_sha},
            {"criterion": "Historical S>=0.5 threshold frozen", "ready": True, "evidence": "0.5"},
            {"criterion": "Reference array identity exact", "ready": True, "evidence": EXPECTED_REFERENCE_ARRAY_SHA},
            {"criterion": "Reference plume-mask identity exact", "ready": True, "evidence": EXPECTED_REFERENCE_MASK_SHA},
            {"criterion": "Independent E23 reconstruction exact", "ready": True, "evidence": E23_ARTIFACTS[E23_NUMERICAL_NAME]},
            {"criterion": "Frozen V16 deployment candidate unchanged", "ready": True, "evidence": EXPECTED_V16_FROZEN_SHA},
            {"criterion": "No deployment gate evaluated in freeze milestone", "ready": True, "evidence": "evaluation deferred to E25"},
            {"criterion": "Internal test/OOD remain closed", "ready": True, "evidence": "NO/NO"},
        ])

        save_csv(gate_csv, [{"gate": k, **v} for k, v in gates.items()])

        freeze_manifest = {
            "milestone": MILESTONE,
            "status": SUCCESS,
            "freeze_role": "authoritative_historical_SG7E_100day_reference_truth",
            "freeze_mode": "byte-for-byte copy of the independently validated E22-R4 candidate",
            "source_candidate": {
                "milestone": "V16E-22-R4",
                "path": str(e22_candidate_path),
                "file_sha256": source_sha_before,
                "reference_array_sha256": EXPECTED_REFERENCE_ARRAY_SHA,
                "reference_mask_sha256": EXPECTED_REFERENCE_MASK_SHA,
                "frozen_before_E24": False,
            },
            "independent_validation": {
                "milestone": "V16E-23",
                "runner_sha256": E23_RUNNER_SHA,
                "numerical_file_sha256": E23_ARTIFACTS[E23_NUMERICAL_NAME],
                "validation_contract_sha256": E23_ARTIFACTS[E23_CONTRACT_NAME],
                "freeze_readiness_manifest_sha256": E23_ARTIFACTS[E23_READINESS_NAME],
                "summary_sha256": E23_ARTIFACTS[E23_SUMMARY_NAME],
                "bitwise_exact": True,
                "L1": 0.0,
                "Linf": 0.0,
                "freeze_ready": True,
            },
            "frozen_reference": {
                "path": str(frozen_path),
                "file_sha256": frozen_sha,
                "reference_key": EXPECTED_REFERENCE_KEY,
                "physical_time_days": EXPECTED_TIME_DAYS,
                "shape": list(frozen.shape),
                "dtype": str(frozen.dtype),
                "plume_threshold": EXPECTED_THRESHOLD,
                "reference_array_sha256": sha256_array(frozen),
                "reference_mask_sha256": sha256_array(frozen_mask),
                "morphology": morph,
                "byte_identical_to_source": True,
                "bitwise_identical_to_independent_validation": True,
            },
            "separate_frozen_V16_deployment_candidate": {
                "path": str(e18_frozen),
                "file_sha256": EXPECTED_V16_FROZEN_SHA,
                "modified_in_E24": False,
            },
            "constraints": {
                "candidate_performance_used": False,
                "deployment_gate_evaluated": False,
                "threshold_changed": False,
                "diagnostic_0p21_used": False,
                "historical_truth_regenerated": False,
                "internal_test_reopened": False,
                "OOD_reopened": False,
            },
            "deployment_gate_evaluation_eligible": True,
            "next_milestone": NEXT_PASS,
        }
        save_json(manifest_out, freeze_manifest)

        provenance_contract = {
            "milestone": MILESTONE,
            "status": SUCCESS,
            "reference_truth_authority": {
                "reference_key": EXPECTED_REFERENCE_KEY,
                "physical_time_days": EXPECTED_TIME_DAYS,
                "authoritative_plume_threshold": EXPECTED_THRESHOLD,
                "frozen_reference_file_sha256": frozen_sha,
                "reference_array_sha256": EXPECTED_REFERENCE_ARRAY_SHA,
                "reference_mask_sha256": EXPECTED_REFERENCE_MASK_SHA,
                "plume_cells": EXPECTED_PLUME_CELLS,
                "footprint_cells": EXPECTED_FOOTPRINT_CELLS,
                "vertical_extent_layers": EXPECTED_VERTICAL_EXTENT,
            },
            "source_chain": {
                "E22R4_runner_sha256": E22R4_RUNNER_SHA,
                "E22R4_candidate_file_sha256": E22R4_CANDIDATE_FILE_SHA,
                "E23_runner_sha256": E23_RUNNER_SHA,
                "E23_artifacts": {k: {"sha256": v} for k, v in E23_ARTIFACTS.items()},
            },
            "frozen_V16_candidate_sha256": EXPECTED_V16_FROZEN_SHA,
            "reference_frozen": True,
            "deployment_gate_evaluated": False,
            "deployment_gate_evaluation_eligible": True,
            "next_milestone": NEXT_PASS,
        }
        save_json(contract_out, provenance_contract)

        summary = {
            "milestone": MILESTONE,
            "status": "PASS",
            "grid_shape": list(EXPECTED_GRID),
            "physical_time_days": EXPECTED_TIME_DAYS,
            "historical_reference_key": EXPECTED_REFERENCE_KEY,
            "historical_authoritative_plume_threshold": EXPECTED_THRESHOLD,
            "source_E22R4_candidate_file_sha256": source_sha_before,
            "E23_independent_numerical_file_sha256": E23_ARTIFACTS[E23_NUMERICAL_NAME],
            "frozen_reference_file_sha256": frozen_sha,
            "frozen_reference_array_sha256": EXPECTED_REFERENCE_ARRAY_SHA,
            "frozen_reference_mask_sha256": EXPECTED_REFERENCE_MASK_SHA,
            "frozen_reference_plume_cells": morph["plume_cells"],
            "frozen_reference_footprint_cells": morph["footprint_cells"],
            "frozen_reference_vertical_extent_layers": morph["vertical_extent_layers"],
            "reference_truth_frozen": True,
            "source_frozen_byte_identity": True,
            "E23_independent_bitwise_identity": True,
            "historical_truth_regenerated": False,
            "candidate_performance_used": False,
            "deployment_pass_fail_evaluated": False,
            "deployment_gate_evaluation_eligible": True,
            "V16_frozen_candidate_sha256": EXPECTED_V16_FROZEN_SHA,
            "V16_frozen_candidate_modified": False,
            "full_grid_plume_authorized": False,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "next_milestone": NEXT_PASS,
        }
        save_json(summary_out, summary)

        handoff_out.write_text(
            "# PAD-Stream V16E-24 Handoff\n\n"
            "V16E-24 formally freezes the independently validated historical SG7E 100-day reference truth. "
            "The frozen reference is a byte-for-byte copy of the V16E-22-R4 source candidate that V16E-23 "
            "independently reconstructed bitwise exactly.\n\n"
            f"- Historical reference: `{EXPECTED_REFERENCE_KEY}` at `100 days`\n"
            "- Historical authoritative plume threshold: `S >= 0.5`\n"
            f"- Frozen reference file SHA-256: `{frozen_sha}`\n"
            f"- Reference array SHA-256: `{EXPECTED_REFERENCE_ARRAY_SHA}`\n"
            f"- Reference plume-mask SHA-256: `{EXPECTED_REFERENCE_MASK_SHA}`\n"
            f"- Frozen V16 deployment candidate SHA-256: `{EXPECTED_V16_FROZEN_SHA}`\n"
            "- Reference truth is now FROZEN.\n"
            "- Frozen V16 deployment candidate remains unchanged.\n"
            "- No deployment gate was evaluated in E24.\n"
            "- Deployment-gate evaluation is now eligible for E25.\n"
            "- Internal test and OOD remain closed.\n\n"
            f"Next: **{NEXT_PASS}**.\n",
            encoding="utf-8",
        )

        # Save the final gate matrix after all freeze/post-freeze checks.
        save_csv(gate_csv, [{"gate": k, **v} for k, v in gates.items()])

        print("\n" + "=" * 132)
        print("V16E-24 RESULT: PASS")
        print("=" * 132)
        print(f"{'Historical reference':72}: {EXPECTED_REFERENCE_KEY} @ 100 days")
        print(f"{'Historical authoritative plume threshold':72}: S >= 0.5")
        print(f"{'Source E22-R4 candidate file SHA-256':72}: {source_sha_before}")
        print(f"{'E23 independent validation numerical SHA-256':72}: {E23_ARTIFACTS[E23_NUMERICAL_NAME]}")
        print(f"{'Frozen reference file SHA-256':72}: {frozen_sha}")
        print(f"{'Frozen reference array SHA-256':72}: {sha256_array(frozen)}")
        print(f"{'Frozen reference plume-mask SHA-256':72}: {sha256_array(frozen_mask)}")
        print(f"{'Source/frozen byte identity':72}: YES")
        print(f"{'E23 independent/frozen bitwise identity':72}: YES")
        print(f"{'Reference truth frozen':72}: YES")
        print(f"{'Deployment pass/fail evaluated':72}: NO")
        print(f"{'Deployment-gate evaluation eligible':72}: YES")
        print(f"{'V16 frozen deployment candidate modified':72}: NO")
        print(f"{'Full-grid plume authorized':72}: NO")
        print(f"{'Internal test / OOD reopened':72}: NO / NO")
        for p in [
            frozen_path, manifest_out, contract_out, summary_out, handoff_out,
            authority_csv, identity_csv, lineage_csv, readiness_csv, gate_csv,
        ]:
            print(f"{p.relative_to(out)} SHA: {sha256_file(p)}")
        print(f"Output: {out}")
        print(f"NEXT: {NEXT_PASS}")
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        payload = {
            "milestone": MILESTONE,
            "status": BLOCKED,
            "exception": repr(exc),
            "gates": gates,
            "E22R4_source_candidate_modified": False,
            "E23_artifacts_modified": False,
            "reference_truth_frozen": False,
            "historical_truth_regenerated": False,
            "candidate_performance_used": False,
            "deployment_pass_fail_evaluated": False,
            "V16_frozen_candidate_modified": False,
            "full_grid_plume_authorized": False,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "next_milestone": NEXT_FAIL,
            "traceback": traceback.format_exc(),
        }
        save_json(blocked_json, payload)
        print(f"\n[FAIL] V16E-24 did not close: {exc}")
        print(f"Blocked report SHA: {sha256_file(blocked_json)}")
        print(f"Blocked output: {blocked}")
        return 2


def parse_args():
    p = argparse.ArgumentParser(description="PAD-Stream V16E-24 historical 100-day reference-truth freeze")
    p.add_argument("--project-root", required=True)
    p.add_argument("--drive-root", required=True)
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(main(Path(args.project_root), Path(args.drive_root)))
