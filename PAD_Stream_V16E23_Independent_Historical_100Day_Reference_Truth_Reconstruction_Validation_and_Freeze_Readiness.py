from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import json
import tempfile
import traceback
import zipfile

import numpy as np

# =============================================================================
# PAD-Stream V16E-23
# Independent Historical 100-Day Reference-Truth Reconstruction Validation /
# Freeze Readiness
# =============================================================================
#
# NO CHANGE TO THE V16E-18-R1 FROZEN V16 CANDIDATE.
# NO CHANGE TO THE V16E-22-R4 REFERENCE-TRUTH CANDIDATE.
# NO REFERENCE FREEZE IN E23.
# NO DEPLOYMENT GATE EVALUATION.
# NO V16 PERFORMANCE USED TO DEFINE OR VALIDATE HISTORICAL REFERENCE TRUTH.
# NO SG7E THRESHOLD CHANGE: authoritative historical threshold remains S >= 0.5.
# 0.21 REMAINS DIAGNOSTIC-ONLY AND IS NOT USED IN E23.
# NO TRAINING / CHECKPOINT LOAD / MODEL INFERENCE.
# NO PRESSURE / DARCY / POLLOCK / TOF / MAP-BACK / TRANSPORT RECOMPUTATION.
#
# PURPOSE
# -------
# V16E-22-R4 recovered and authenticated the original Git-ignored V15-SG7E1R14
# multi-time historical reference artifact, then created an unfrozen 100-day
# reference-truth candidate by selecting the unique historical time == 100 days.
#
# E23 validates that candidate independently. It does NOT call the E22-R4
# reconstruction implementation. Instead it:
#   1) binds the accepted E22-R4 runner and output artifacts by exact SHA-256;
#   2) authenticates the exact accepted R4 recovery ZIP again;
#   3) independently reads the historical R14 NPZ and tracked R14 contract;
#   4) independently identifies the unique 100-day snapshot from the time axis;
#   5) independently reconstructs S>=0.5 plume membership;
#   6) compares the independent state bit-for-bit/hash-for-hash against the
#      E22-R4 candidate;
#   7) establishes freeze readiness only. E23 does NOT freeze the candidate.
# =============================================================================

MILESTONE = "V16E-23"
SUCCESS = "V16E23_INDEPENDENT_HISTORICAL_100DAY_REFERENCE_TRUTH_VALIDATION_PASS"
BLOCKED = "V16E23_INDEPENDENT_HISTORICAL_100DAY_REFERENCE_TRUTH_VALIDATION_BLOCKED"
NEXT_PASS = "V16E-24 - Historical 100-Day Reference-Truth Freeze / Provenance Manifest"
NEXT_FAIL = "V16E-23-R1 - Repair only the failed V16E-23 independent reference-validation gate; preserve the V16E-22-R4 candidate unchanged"

EXPECTED_GRID = (15, 50, 50)
EXPECTED_MULTI = (4, 15, 50, 50)
EXPECTED_TIMES = np.asarray([100.0, 250.0, 500.0, 1000.0], dtype=np.float64)
EXPECTED_THRESHOLD = 0.5
EXPECTED_REFERENCE_KEY = "SG7A_corrected"
EXPECTED_100D_INDEX = 0
EXPECTED_100D_DTYPE = np.dtype("float64")

# Frozen V16 candidate is bound only for immutability; E23 does not compare its
# performance to reference truth.
EXPECTED_V16_FROZEN_SHA = "d422dc1e56281c1baf0ae007c62ce4bd69677a232bd1448a5bd79d3177eafaea"
E18_FROZEN_REL = Path(
    "provenance/hybrid_dp/V16E18_R1_FROZEN_SGSIM_100D_FULL_GRID_CANDIDATE/"
    "frozen_full_grid/V16E18_R1_Frozen_SGSim_100Day_Full_Grid_Candidate.npz"
)

# Accepted V16E-22-R4 authority.
E22R4_RUNNER_NAME = "PAD_Stream_V16E22_R4_Tracked_JSON_Canonical_Identity_Repair_and_Historical_Numerical_Recovery.py"
E22R4_RUNNER_SHA = "ea445ba686a5a261302da92dd0d03f93f10cd4f61aca827ff22646952e9eb13c"
E22R4_DIR_REL = Path(
    "provenance/hybrid_dp/"
    "V16E22_R4_HISTORICAL_R14_NUMERICAL_RECOVERY_100DAY_REFERENCE_TRUTH_LINEAGE_RECONSTRUCTION_AUDIT"
)
E22R4_ARTIFACTS = {
    "V16E22_R4_Historical_SG7E_100Day_Reference_Truth_Candidate.npz":
        "e78b87bf860776906d9a1862f4de252a9c2ddad21dc6ff02a15ac703a196b08f",
    "V16E22_R4_Historical_100Day_Reference_Truth_Lineage_Contract.json":
        "faf7c273d412f3c23afe863815104f5e90dc4991988dc3c13615a787702eab6a",
    "V16E22_R4_Reference_Truth_Reconstruction_Audit.json":
        "8d6bd0105916e98b5f13ce1a2f9a237c471bfecfcc4585cd02d4bc8bdc59bbe3",
    "PAD_Stream_V16E22_R4_Summary.json":
        "b07a83db87da4eb0256f4f20c503d1c9c037d7d1ca768b68b6cb7f92dee1b683",
    "V16E22_R4_Handoff.md":
        "eb0992f189e72e7bf63e10374b76110a80aa0684563e9ae4d781f3a87d543abc",
    "V16E22_R4_Historical_Source_Authority.csv":
        "5e6ae9a23b8a67bbd8db935abcc0621163f365daf4f71dc16aa9f96069ae916a",
    "V16E22_R4_Historical_Output_Identity.csv":
        "7e1d6d4ecf02704855de53ca8b3235f9ae665e8516890f63d512aa59cec50d3c",
    "V16E22_R4_Recovery_Bundle_Identity.csv":
        "7092ba26cfd7bf5fde4cc7191774c7ef463b364a3d250ca2e50fab27ed6269bc",
    "V16E22_R4_Reference_Time_Snapshot_Identity.csv":
        "c6ef1e40a53986ac497793b9b538c4cf6cbb063ef84a5b284a79fc4ade0e5fad",
    "V16E22_R4_Final_Gate_Matrix.csv":
        "2bac10c46ced5d853e56e6e3fd1388fc836c6b5ea7667298b14aa96eac9c0ab7",
}

E22R4_CANDIDATE_NAME = "V16E22_R4_Historical_SG7E_100Day_Reference_Truth_Candidate.npz"
E22R4_LINEAGE_NAME = "V16E22_R4_Historical_100Day_Reference_Truth_Lineage_Contract.json"
E22R4_AUDIT_NAME = "V16E22_R4_Reference_Truth_Reconstruction_Audit.json"
E22R4_SUMMARY_NAME = "PAD_Stream_V16E22_R4_Summary.json"
E22R4_GATE_NAME = "V16E22_R4_Final_Gate_Matrix.csv"

# Exact accepted historical-recovery identities established in E22-R4.
EXPECTED_RECOVERY_ZIP_NAME = "V16E22_R4_Historical_R14_Reference_Recovery.zip"
EXPECTED_RECOVERY_ZIP_SHA = "9931213895f5cead72cb3b0864748f088c700666fdfe4c15ac7003814351f4e5"
RECOVERY_MANIFEST_NAME = "V16E22_R4_Recovery_Manifest.json"
RECOVERY_NUMERICAL_NAME = "V15SG7E1R14_Multi_Time_Historical_Reference.npz"
EXPECTED_R14_NUMERICAL_FILE_SHA = "cda7645d4cb5505a2110caf2f75ef001a3c6b8233bce12011c9c481c958fe75e"
EXPECTED_MULTI_REFERENCE_ARRAY_SHA = "e3d4bef65753a2d0dd65414db04416cc3cb89408578411109384617847b31bce"
EXPECTED_TIMES_ARRAY_SHA = "8d7b7de1173f6ec1ec171c5f13c90f6b9d2d09755d168c025ca86472411fc6e6"
EXPECTED_MULTI_MASK_ARRAY_SHA = "9b720bb1d99af1734fd0aa0131f6562897df6e4e2bc41fe3e8c5cc6a7d62be77"
EXPECTED_100D_ARRAY_SHA = "6135585d5dadd02f6ba2bcd2dd860c9a681d006526823c4e391e40f9f7f9ddd6"
EXPECTED_100D_MASK_SHA = "08458e742f2866096346e56ff69fb3c9be183b68623d09cd518778326dfe180b"
EXPECTED_100D_PLUME_CELLS = 6084
EXPECTED_100D_FOOTPRINT_CELLS = 724
EXPECTED_100D_VERTICAL_EXTENT_LAYERS = 15

# Historical source/contract authority used independently in E23.
R14_SOURCE_NAME = "PAD_Stream_V15SG7E1R14_Multi_Time_Historical_Reference_Reconstruction_Contract_Audit.py"
R14_SOURCE_SHA = "514e6f5ebaf5346691d3194cb2eefe041528eb00b4bd452c657b5d23e5132a3a"
R14_CONTRACT_REL = Path("output/V15_SG7E1R14/V15SG7E1R14_Multi_Time_Historical_Reference_Contract.json")


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


def same_times(v) -> bool:
    try:
        a = np.asarray(v, dtype=np.float64).reshape(-1)
    except Exception:
        return False
    return a.shape == EXPECTED_TIMES.shape and np.array_equal(a, EXPECTED_TIMES)


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


def safe_zip_members(zf: zipfile.ZipFile):
    names = zf.namelist()
    for name in names:
        p = Path(name)
        if p.is_absolute() or ".." in p.parts or len(p.parts) != 1:
            raise GateError(f"unsafe_or_nested_recovery_zip_member:{name}")
    return names


def validate_r14_contract(contract, ref, times, masks):
    hist = contract.get("historical_reference", {})
    if hist.get("key") != EXPECTED_REFERENCE_KEY:
        raise GateError("R14_contract_reference_key")
    if hist.get("shape") != list(EXPECTED_MULTI):
        raise GateError("R14_contract_shape")
    if not same_times(hist.get("times_days")):
        raise GateError("R14_contract_times")
    if abs(float(hist.get("plume_threshold")) - EXPECTED_THRESHOLD) > 1e-15:
        raise GateError("R14_contract_threshold")
    if hist.get("sha256") != sha256_array(ref):
        raise GateError("R14_contract_multi_reference_hash")
    if hist.get("times_sha256") != sha256_array(times):
        raise GateError("R14_contract_times_hash")
    if hist.get("plume_mask_sha256") != sha256_array(masks):
        raise GateError("R14_contract_multi_mask_hash")

    rows = contract.get("per_time_snapshots", [])
    rows100 = []
    for row in rows:
        try:
            if float(row.get("time_days")) == 100.0:
                rows100.append(row)
        except Exception:
            pass
    if len(rows100) != 1:
        raise GateError(f"R14_contract_100d_row_count:{len(rows100)}")
    row = rows100[0]
    if "snapshot_sha256" in row:
        raise GateError("R14_contract_unexpected_snapshot_sha256_schema")
    if row.get("saturation_sha256") != EXPECTED_100D_ARRAY_SHA:
        raise GateError("R14_contract_100d_saturation_hash")
    if row.get("plume_mask_sha256") != EXPECTED_100D_MASK_SHA:
        raise GateError("R14_contract_100d_mask_hash")


def main(project_root: Path, drive_root: Path, recovery_zip: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    recovery_zip = recovery_zip.resolve()

    out = drive / "provenance/hybrid_dp/V16E23_INDEPENDENT_HISTORICAL_100DAY_REFERENCE_TRUTH_VALIDATION_FREEZE_READINESS"
    blocked = drive / "provenance/hybrid_dp/V16E23_BLOCKED_INDEPENDENT_HISTORICAL_100DAY_REFERENCE_TRUTH_VALIDATION"

    numerical_out = out / "V16E23_Independent_Historical_100Day_Reference_Reconstruction.npz"
    contract_out = out / "V16E23_Independent_Reference_Truth_Validation_Contract.json"
    readiness_out = out / "V16E23_Reference_Truth_Freeze_Readiness_Manifest.json"
    summary_out = out / "PAD_Stream_V16E23_Summary.json"
    handoff_out = out / "V16E23_Handoff.md"
    authority_csv = out / "V16E23_E22R4_Authority.csv"
    recovery_csv = out / "V16E23_Recovery_Bundle_Independent_Validation.csv"
    identity_csv = out / "V16E23_Independent_Reconstruction_Identity.csv"
    readiness_csv = out / "V16E23_Freeze_Readiness_Matrix.csv"
    gate_csv = out / "V16E23_Final_Gate_Matrix.csv"
    blocked_json = blocked / "V16E23_Blocked_Independent_Historical_100Day_Reference_Truth_Validation.json"

    gates = {}

    def gate(name, ok, detail=""):
        ok = bool(ok)
        gates[name] = {"passed": ok, "detail": str(detail)}
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""), flush=True)
        if not ok:
            raise GateError(name)

    print("\n" + "=" * 132)
    print("PAD-Stream V16E-23 Independent Historical 100-Day Reference-Truth Reconstruction Validation / Freeze Readiness")
    print("=" * 132)
    print("NO REFERENCE FREEZE IN E23. NO DEPLOYMENT GATE EVALUATION. NO V16 PERFORMANCE USED.")
    print("NO HISTORICAL TRUTH REGENERATION. S >= 0.5 REMAINS AUTHORITATIVE; 0.21 REMAINS DIAGNOSTIC-ONLY.")

    try:
        # ------------------------------------------------------------------
        # Accepted E22-R4 authority.
        # ------------------------------------------------------------------
        print("\nV16E-22-R4 ACCEPTED REFERENCE-CANDIDATE AUTHORITY")
        parent_runner = root / E22R4_RUNNER_NAME
        gate("E22R4_runner_exists", parent_runner.is_file(), parent_runner)
        gate("E22R4_runner_SHA_exact", sha256_file(parent_runner) == E22R4_RUNNER_SHA, sha256_file(parent_runner))

        e22_dir = drive / E22R4_DIR_REL
        authority_rows = []
        for name, expected_sha in E22R4_ARTIFACTS.items():
            path = e22_dir / name
            gate(f"E22R4_{name}_exists", path.is_file(), path)
            actual = sha256_file(path)
            gate(f"E22R4_{name}_SHA_exact", actual == expected_sha, actual)
            authority_rows.append({"artifact": name, "path": str(path), "sha256": actual, "exact": True})

        e22_summary = load_json(e22_dir / E22R4_SUMMARY_NAME)
        e22_lineage = load_json(e22_dir / E22R4_LINEAGE_NAME)
        e22_audit = load_json(e22_dir / E22R4_AUDIT_NAME)
        e22_gates = load_csv(e22_dir / E22R4_GATE_NAME)

        gate("E22R4_summary_status_PASS", e22_summary.get("status") == "PASS")
        gate("E22R4_lineage_status_exact", e22_lineage.get("status") == "V16E22_R4_HISTORICAL_100DAY_REFERENCE_TRUTH_LINEAGE_RECONSTRUCTED")
        gate("E22R4_audit_status_PASS", e22_audit.get("status") == "PASS")
        gate("E22R4_all_recorded_gates_pass", bool(e22_gates) and all(boolish(r.get("passed")) for r in e22_gates))
        gate("E22R4_next_is_E23", e22_summary.get("next_milestone") == "V16E-23 - Independent Historical 100-Day Reference-Truth Reconstruction Validation / Freeze Readiness")
        gate("E22R4_reference_candidate_created_not_frozen", e22_summary.get("reference_candidate_created") is True and e22_summary.get("reference_candidate_frozen") is False)
        gate("E22R4_no_candidate_performance_used", e22_summary.get("candidate_performance_used_for_reference_selection") is False)
        gate("E22R4_no_deployment_evaluation", e22_summary.get("deployment_pass_fail_evaluated") is False)
        gate("E22R4_historical_truth_not_regenerated", e22_summary.get("historical_numerical_truth_regenerated") is False)
        gate("E22R4_threshold_0p5", abs(float(e22_summary.get("historical_authoritative_plume_threshold")) - 0.5) < 1e-15)
        gate("E22R4_reference_key_exact", e22_summary.get("historical_reference_key") == EXPECTED_REFERENCE_KEY)
        gate("E22R4_100d_index_exact", int(e22_summary.get("historical_100d_snapshot_index")) == EXPECTED_100D_INDEX)
        gate("E22R4_100d_snapshot_hash_exact", e22_summary.get("historical_100d_snapshot_sha256") == EXPECTED_100D_ARRAY_SHA)
        gate("E22R4_candidate_file_hash_record_exact", e22_summary.get("reference_candidate_file_sha256") == E22R4_ARTIFACTS[E22R4_CANDIDATE_NAME])

        candidate_path = e22_dir / E22R4_CANDIDATE_NAME
        candidate_sha_before = sha256_file(candidate_path)

        # ------------------------------------------------------------------
        # Candidate content is the target of independent validation only.
        # ------------------------------------------------------------------
        print("\nE22-R4 UNFROZEN 100-DAY REFERENCE-CANDIDATE CONTENT")
        with np.load(candidate_path, allow_pickle=False) as db:
            expected_keys = {
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
            gate("E22R4_candidate_keys_exact", set(db.files) == expected_keys, sorted(db.files))
            cand = np.array(db["reference_truth_100d_native"], copy=True)
            cand_mask = np.array(db["reference_plume_mask_100d_0p5"], copy=True)
            c_time = float(scalar(db, "physical_time_days"))
            c_thr = float(scalar(db, "plume_threshold"))
            c_key = str(scalar(db, "source_reference_key"))
            c_multi_hash = str(scalar(db, "source_multi_time_reference_array_sha256"))
            c_100_hash = str(scalar(db, "source_100d_snapshot_array_sha256"))
            c_r14_file_hash = str(scalar(db, "source_R14_recovered_numerical_file_sha256"))
            c_bundle_hash = str(scalar(db, "source_recovery_bundle_sha256"))

        gate("E22R4_candidate_shape_exact", cand.shape == EXPECTED_GRID, cand.shape)
        gate("E22R4_candidate_dtype_exact", cand.dtype == EXPECTED_100D_DTYPE, cand.dtype)
        gate("E22R4_candidate_time_exact", c_time == 100.0, c_time)
        gate("E22R4_candidate_threshold_exact", c_thr == 0.5, c_thr)
        gate("E22R4_candidate_reference_key_exact", c_key == EXPECTED_REFERENCE_KEY, c_key)
        gate("E22R4_candidate_array_hash_exact", sha256_array(cand) == EXPECTED_100D_ARRAY_SHA, sha256_array(cand))
        gate("E22R4_candidate_mask_hash_exact", sha256_array(cand_mask.astype(np.uint8)) == EXPECTED_100D_MASK_SHA, sha256_array(cand_mask.astype(np.uint8)))
        gate("E22R4_candidate_mask_from_threshold_exact", np.array_equal(cand_mask.astype(np.uint8), (cand >= 0.5).astype(np.uint8)))
        gate("E22R4_candidate_source_multi_hash_exact", c_multi_hash == EXPECTED_MULTI_REFERENCE_ARRAY_SHA, c_multi_hash)
        gate("E22R4_candidate_source_100d_hash_exact", c_100_hash == EXPECTED_100D_ARRAY_SHA, c_100_hash)
        gate("E22R4_candidate_source_R14_file_hash_exact", c_r14_file_hash == EXPECTED_R14_NUMERICAL_FILE_SHA, c_r14_file_hash)
        gate("E22R4_candidate_source_recovery_bundle_hash_exact", c_bundle_hash == EXPECTED_RECOVERY_ZIP_SHA, c_bundle_hash)

        # ------------------------------------------------------------------
        # Independent historical reconstruction from exact accepted R4 bundle.
        # ------------------------------------------------------------------
        print("\nINDEPENDENT HISTORICAL R14 RECONSTRUCTION")
        r14_source = root / R14_SOURCE_NAME
        gate("R14_source_exists", r14_source.is_file(), r14_source)
        gate("R14_source_SHA_exact", sha256_file(r14_source) == R14_SOURCE_SHA, sha256_file(r14_source))
        r14_contract_path = root / R14_CONTRACT_REL
        gate("R14_tracked_contract_exists", r14_contract_path.is_file(), r14_contract_path)
        r14_contract = load_json(r14_contract_path)
        gate("R14_tracked_contract_status_reconstructed", r14_contract.get("status") == "SG7E_MULTI_TIME_HISTORICAL_REFERENCE_CONTRACT_RECONSTRUCTED")
        gate("R14_tracked_contract_no_candidate_performance", r14_contract.get("constraints", {}).get("candidate_performance_used") is False)
        gate("R14_tracked_contract_threshold_unchanged", r14_contract.get("constraints", {}).get("threshold_changed") is False)

        gate("recovery_zip_exists", recovery_zip.is_file(), recovery_zip)
        recovery_zip_sha = sha256_file(recovery_zip)
        gate("recovery_zip_SHA_exact", recovery_zip_sha == EXPECTED_RECOVERY_ZIP_SHA, recovery_zip_sha)

        with zipfile.ZipFile(recovery_zip, "r") as zf:
            names = safe_zip_members(zf)
            gate("recovery_zip_exact_members", len(names) == 2 and set(names) == {RECOVERY_MANIFEST_NAME, RECOVERY_NUMERICAL_NAME}, names)
            manifest = json.loads(zf.read(RECOVERY_MANIFEST_NAME).decode("utf-8"))
            with tempfile.TemporaryDirectory(prefix="V16E23_independent_") as td:
                recovered_npz = Path(td) / RECOVERY_NUMERICAL_NAME
                recovered_npz.write_bytes(zf.read(RECOVERY_NUMERICAL_NAME))

                gate("recovery_manifest_milestone_exact", manifest.get("milestone") == "V16E-22-R4")
                gate("recovery_manifest_role_exact", manifest.get("bundle_role") == "LOCAL_IGNORED_R14_NUMERICAL_ARTIFACT_RECOVERY")
                gate("recovery_manifest_reference_key_exact", manifest.get("reference_key") == EXPECTED_REFERENCE_KEY)
                gate("recovery_manifest_shape_exact", manifest.get("shape") == list(EXPECTED_MULTI))
                gate("recovery_manifest_times_exact", same_times(manifest.get("times_days")))
                gate("recovery_manifest_threshold_0p5", abs(float(manifest.get("plume_threshold")) - 0.5) < 1e-15)
                gate("recovery_manifest_R14_file_SHA_exact", manifest.get("source_file_sha256") == EXPECTED_R14_NUMERICAL_FILE_SHA)
                gate("recovery_manifest_multi_reference_SHA_exact", manifest.get("multi_time_reference_array_sha256") == EXPECTED_MULTI_REFERENCE_ARRAY_SHA)
                gate("recovery_manifest_times_SHA_exact", manifest.get("times_array_sha256") == EXPECTED_TIMES_ARRAY_SHA)
                gate("recovery_manifest_multi_mask_SHA_exact", manifest.get("plume_mask_array_sha256") == EXPECTED_MULTI_MASK_ARRAY_SHA)
                gate("recovery_manifest_100d_index_exact", int(manifest.get("reference_100d_snapshot_index")) == EXPECTED_100D_INDEX)
                gate("recovery_manifest_100d_array_SHA_exact", manifest.get("reference_100d_snapshot_array_sha256") == EXPECTED_100D_ARRAY_SHA)
                gate("recovery_manifest_100d_mask_SHA_exact", manifest.get("reference_100d_plume_mask_array_sha256") == EXPECTED_100D_MASK_SHA)
                constraints = manifest.get("constraints", {})
                gate("recovery_manifest_no_regeneration", constraints.get("numerical_truth_regenerated") is False)
                gate("recovery_manifest_no_candidate_performance", constraints.get("candidate_performance_used") is False)
                gate("recovery_manifest_no_threshold_change", constraints.get("threshold_changed") is False)
                gate("recovery_manifest_no_gate_evaluation", constraints.get("deployment_gate_evaluated") is False)
                gate("recovered_R14_file_SHA_exact", sha256_file(recovered_npz) == EXPECTED_R14_NUMERICAL_FILE_SHA, sha256_file(recovered_npz))

                with np.load(recovered_npz, allow_pickle=False) as histdb:
                    expected_hist_keys = {
                        "SG7A_corrected",
                        "times_days",
                        "plume_threshold",
                        "SG7A_reference_plume_mask",
                    }
                    gate("R14_historical_npz_keys_exact", set(histdb.files) == expected_hist_keys, sorted(histdb.files))
                    ref = np.array(histdb["SG7A_corrected"], copy=True)
                    times = np.asarray(histdb["times_days"], dtype=np.float64).reshape(-1)
                    threshold_arr = np.asarray(histdb["plume_threshold"], dtype=np.float64).reshape(-1)
                    masks = np.asarray(histdb["SG7A_reference_plume_mask"], dtype=np.uint8)

                gate("independent_multi_reference_shape_exact", ref.shape == EXPECTED_MULTI, ref.shape)
                gate("independent_times_exact", np.array_equal(times, EXPECTED_TIMES), times.tolist())
                gate("independent_threshold_scalar_exact", threshold_arr.size == 1 and float(threshold_arr[0]) == 0.5, threshold_arr.tolist())
                gate("independent_masks_shape_exact", masks.shape == EXPECTED_MULTI, masks.shape)
                gate("independent_masks_equal_thresholded_reference", np.array_equal(masks, (ref >= 0.5).astype(np.uint8)))
                gate("independent_multi_reference_hash_exact", sha256_array(ref) == EXPECTED_MULTI_REFERENCE_ARRAY_SHA, sha256_array(ref))
                gate("independent_times_hash_exact", sha256_array(times) == EXPECTED_TIMES_ARRAY_SHA, sha256_array(times))
                gate("independent_multi_mask_hash_exact", sha256_array(masks) == EXPECTED_MULTI_MASK_ARRAY_SHA, sha256_array(masks))

                # Tracked historical contract is evaluated independently against
                # the recovered numerical content; E22-R4 output is not used here.
                validate_r14_contract(r14_contract, ref, times, masks)
                gate("independent_R14_contract_revalidated", True)

                matches = np.flatnonzero(times == 100.0)
                gate("independent_100d_time_unique", matches.size == 1, matches.tolist())
                idx100 = int(matches[0])
                gate("independent_100d_index_exact", idx100 == EXPECTED_100D_INDEX, idx100)

                independent = np.array(ref[idx100], copy=True)
                independent_mask = (independent >= 0.5).astype(np.uint8)
                independent_hash = sha256_array(independent)
                independent_mask_hash = sha256_array(independent_mask)
                gate("independent_100d_shape_exact", independent.shape == EXPECTED_GRID, independent.shape)
                gate("independent_100d_dtype_exact", independent.dtype == EXPECTED_100D_DTYPE, independent.dtype)
                gate("independent_100d_array_hash_exact", independent_hash == EXPECTED_100D_ARRAY_SHA, independent_hash)
                gate("independent_100d_mask_hash_exact", independent_mask_hash == EXPECTED_100D_MASK_SHA, independent_mask_hash)

        # ------------------------------------------------------------------
        # Independent reconstruction vs E22-R4 candidate.
        # ------------------------------------------------------------------
        print("\nINDEPENDENT RECONSTRUCTION VS E22-R4 CANDIDATE")
        diff = independent.astype(np.float64) - cand.astype(np.float64)
        l1 = float(np.mean(np.abs(diff)))
        linf = float(np.max(np.abs(diff)))
        gate("independent_reconstruction_bitwise_exact_to_E22R4", np.array_equal(independent, cand), f"Linf={linf:.17g}")
        gate("independent_reconstruction_hash_exact_to_E22R4", independent_hash == sha256_array(cand) == EXPECTED_100D_ARRAY_SHA)
        gate("independent_reconstruction_L1_zero", l1 == 0.0, l1)
        gate("independent_reconstruction_Linf_zero", linf == 0.0, linf)
        gate("independent_plume_mask_bitwise_exact_to_E22R4", np.array_equal(independent_mask, cand_mask.astype(np.uint8)))
        gate("independent_plume_mask_hash_exact_to_E22R4", independent_mask_hash == sha256_array(cand_mask.astype(np.uint8)) == EXPECTED_100D_MASK_SHA)

        morph = morphology(independent_mask)
        gate("independent_plume_cells_exact", morph["plume_cells"] == EXPECTED_100D_PLUME_CELLS, morph["plume_cells"])
        gate("independent_footprint_cells_exact", morph["footprint_cells"] == EXPECTED_100D_FOOTPRINT_CELLS, morph["footprint_cells"])
        gate("independent_vertical_extent_exact", morph["vertical_extent_layers"] == EXPECTED_100D_VERTICAL_EXTENT_LAYERS, morph["vertical_extent_layers"])

        # ------------------------------------------------------------------
        # Persist independent evidence only. Candidate remains unfrozen.
        # ------------------------------------------------------------------
        out.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            numerical_out,
            independently_reconstructed_reference_truth_100d_native=independent,
            independently_reconstructed_plume_mask_100d_0p5=independent_mask,
            physical_time_days=np.asarray(100.0, dtype=np.float64),
            plume_threshold=np.asarray(0.5, dtype=np.float64),
            reference_snapshot_array_sha256=np.asarray(independent_hash),
            reference_plume_mask_array_sha256=np.asarray(independent_mask_hash),
            source_E22R4_candidate_file_sha256=np.asarray(candidate_sha_before),
            source_recovery_bundle_sha256=np.asarray(recovery_zip_sha),
            source_R14_numerical_file_sha256=np.asarray(EXPECTED_R14_NUMERICAL_FILE_SHA),
        )
        gate("E23_independent_numerical_written", numerical_out.is_file(), numerical_out)
        with np.load(numerical_out, allow_pickle=False) as db3:
            replay = np.asarray(db3["independently_reconstructed_reference_truth_100d_native"])
            replay_mask = np.asarray(db3["independently_reconstructed_plume_mask_100d_0p5"], dtype=np.uint8)
        gate("E23_persisted_independent_reconstruction_bitwise_exact", np.array_equal(replay, independent))
        gate("E23_persisted_independent_reconstruction_hash_exact", sha256_array(replay) == EXPECTED_100D_ARRAY_SHA)
        gate("E23_persisted_independent_mask_exact", np.array_equal(replay_mask, independent_mask))

        e18_frozen = drive / E18_FROZEN_REL
        gate("E18R1_frozen_candidate_exists", e18_frozen.is_file(), e18_frozen)
        gate("E18R1_frozen_candidate_SHA_unchanged", sha256_file(e18_frozen) == EXPECTED_V16_FROZEN_SHA, sha256_file(e18_frozen))
        gate("E22R4_candidate_file_unchanged_during_E23", sha256_file(candidate_path) == candidate_sha_before == E22R4_ARTIFACTS[E22R4_CANDIDATE_NAME])

        # Firewalls / readiness.
        gate("no_V16_candidate_performance_used_in_E23", True)
        gate("no_authoritative_deployment_gate_evaluated_in_E23", True)
        gate("no_threshold_change_in_E23", True)
        gate("diagnostic_0p21_not_used_in_E23", True)
        gate("historical_truth_not_regenerated_in_E23", True)
        gate("reference_candidate_not_frozen_in_E23", True)
        gate("V16_frozen_candidate_not_modified_in_E23", True)
        gate("internal_test_not_reopened", True)
        gate("OOD_not_reopened", True)
        gate("E24_freeze_ready", True)

        # Save tables before JSON manifests so their exact paths are stable.
        save_csv(authority_csv, authority_rows)
        save_csv(recovery_csv, [{
            "recovery_zip": str(recovery_zip),
            "recovery_zip_sha256": recovery_zip_sha,
            "historical_R14_numerical_file_sha256": EXPECTED_R14_NUMERICAL_FILE_SHA,
            "multi_time_reference_array_sha256": sha256_array(ref),
            "times_array_sha256": sha256_array(times),
            "multi_time_plume_mask_array_sha256": sha256_array(masks),
            "historical_truth_regenerated": False,
            "V16_performance_used": False,
        }])
        save_csv(identity_csv, [{
            "reference_key": EXPECTED_REFERENCE_KEY,
            "time_days": 100.0,
            "snapshot_index": idx100,
            "shape": str(independent.shape),
            "dtype": str(independent.dtype),
            "independent_array_sha256": independent_hash,
            "E22R4_candidate_array_sha256": sha256_array(cand),
            "independent_mask_sha256": independent_mask_hash,
            "E22R4_candidate_mask_sha256": sha256_array(cand_mask.astype(np.uint8)),
            "L1": l1,
            "Linf": linf,
            "bitwise_exact": True,
            "plume_cells": morph["plume_cells"],
            "footprint_cells": morph["footprint_cells"],
            "vertical_extent_layers": morph["vertical_extent_layers"],
        }])
        readiness_rows = [
            {"criterion": "E22-R4 candidate file identity exact", "ready": True, "evidence": candidate_sha_before},
            {"criterion": "Historical R14 recovery bundle identity exact", "ready": True, "evidence": recovery_zip_sha},
            {"criterion": "Independent 100-day reconstruction bitwise exact", "ready": True, "evidence": independent_hash},
            {"criterion": "Independent S>=0.5 plume mask exact", "ready": True, "evidence": independent_mask_hash},
            {"criterion": "Historical threshold unchanged", "ready": True, "evidence": "0.5"},
            {"criterion": "No V16 performance used", "ready": True, "evidence": "prohibited"},
            {"criterion": "No deployment gate evaluated", "ready": True, "evidence": "E23 validation only"},
            {"criterion": "Reference candidate still unfrozen", "ready": True, "evidence": "freeze deferred to E24"},
        ]
        save_csv(readiness_csv, readiness_rows)
        save_csv(gate_csv, [{"gate": k, **v} for k, v in gates.items()])

        numerical_sha = sha256_file(numerical_out)
        contract = {
            "milestone": MILESTONE,
            "status": SUCCESS,
            "validation_mode": "independent reconstruction from exact authenticated historical R14 recovery bundle",
            "E22R4_authority": {
                "runner_sha256": E22R4_RUNNER_SHA,
                "candidate_file_sha256": candidate_sha_before,
                "candidate_array_sha256": sha256_array(cand),
                "candidate_mask_sha256": sha256_array(cand_mask.astype(np.uint8)),
                "candidate_frozen": False,
            },
            "historical_authority": {
                "reference_key": EXPECTED_REFERENCE_KEY,
                "multi_time_shape": list(ref.shape),
                "times_days": [float(x) for x in times],
                "plume_threshold": 0.5,
                "recovery_bundle_sha256": recovery_zip_sha,
                "R14_numerical_file_sha256": EXPECTED_R14_NUMERICAL_FILE_SHA,
                "multi_time_reference_array_sha256": sha256_array(ref),
                "multi_time_plume_mask_array_sha256": sha256_array(masks),
                "historical_truth_regenerated": False,
            },
            "independent_100day_validation": {
                "snapshot_index": idx100,
                "time_days": 100.0,
                "shape": list(independent.shape),
                "dtype": str(independent.dtype),
                "array_sha256": independent_hash,
                "plume_mask_sha256": independent_mask_hash,
                "bitwise_exact_to_E22R4": True,
                "L1": l1,
                "Linf": linf,
                "morphology": morph,
            },
            "constraints": {
                "candidate_performance_used": False,
                "deployment_gate_evaluated": False,
                "threshold_changed": False,
                "diagnostic_0p21_used": False,
                "historical_truth_regenerated": False,
                "reference_candidate_frozen": False,
                "V16_frozen_candidate_modified": False,
            },
            "independent_numerical_file": {"path": str(numerical_out), "sha256": numerical_sha},
            "freeze_ready": True,
            "next_milestone": NEXT_PASS,
        }
        save_json(contract_out, contract)

        readiness = {
            "milestone": MILESTONE,
            "status": SUCCESS,
            "reference_candidate": "V16E22_R4_Historical_SG7E_100Day_Reference_Truth_Candidate.npz",
            "reference_candidate_file_sha256": candidate_sha_before,
            "reference_candidate_array_sha256": EXPECTED_100D_ARRAY_SHA,
            "independent_reconstruction_array_sha256": independent_hash,
            "reference_plume_mask_sha256": EXPECTED_100D_MASK_SHA,
            "independent_reconstruction_exact": True,
            "reconstruction_L1": l1,
            "reconstruction_Linf": linf,
            "ready_for_V16E24_freeze": True,
            "reference_candidate_frozen": False,
            "freeze_mode_required": "byte-for-byte copy of the independently validated E22-R4 candidate",
            "deployment_gate_evaluated": False,
            "next_milestone": NEXT_PASS,
        }
        save_json(readiness_out, readiness)

        summary = {
            "milestone": MILESTONE,
            "status": "PASS",
            "grid_shape": list(EXPECTED_GRID),
            "physical_time_days": 100.0,
            "historical_reference_key": EXPECTED_REFERENCE_KEY,
            "historical_authoritative_plume_threshold": 0.5,
            "E22R4_candidate_file_sha256": candidate_sha_before,
            "independent_reference_array_sha256": independent_hash,
            "independent_reference_mask_sha256": independent_mask_hash,
            "independent_reconstruction_bitwise_exact": True,
            "independent_reconstruction_L1": l1,
            "independent_reconstruction_Linf": linf,
            "independent_plume_cells": morph["plume_cells"],
            "independent_footprint_cells": morph["footprint_cells"],
            "independent_vertical_extent_layers": morph["vertical_extent_layers"],
            "historical_truth_regenerated": False,
            "reference_candidate_frozen": False,
            "freeze_ready": True,
            "candidate_performance_used": False,
            "deployment_pass_fail_evaluated": False,
            "V16_frozen_candidate_modified": False,
            "full_grid_plume_authorized": False,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "next_milestone": NEXT_PASS,
        }
        save_json(summary_out, summary)

        handoff_out.write_text(
            "# PAD-Stream V16E-23 Handoff\n\n"
            "V16E-23 independently reconstructed the historical SG7E 100-day truth from the exact "
            "accepted V16E-22-R4 historical R14 recovery bundle and independently revalidated the "
            "tracked R14 contract. The independent field is bitwise/hash exact to the unfrozen "
            "V16E-22-R4 reference candidate.\n\n"
            f"- Historical reference: `{EXPECTED_REFERENCE_KEY}` at `100 days`\n"
            "- Historical plume threshold: `S >= 0.5`\n"
            f"- Reference array SHA-256: `{independent_hash}`\n"
            f"- Reference mask SHA-256: `{independent_mask_hash}`\n"
            f"- E22-R4 candidate file SHA-256: `{candidate_sha_before}`\n"
            f"- Independent reconstruction L1 / Linf: `{l1}` / `{linf}`\n"
            "- Reference candidate remains UNFROZEN.\n"
            "- No deployment gate was evaluated.\n"
            "- No V16 candidate performance was used.\n\n"
            f"Next: **{NEXT_PASS}**.\n",
            encoding="utf-8",
        )

        # Gate matrix is saved again after all persistence/firewall checks.
        save_csv(gate_csv, [{"gate": k, **v} for k, v in gates.items()])

        print("\n" + "=" * 132)
        print("V16E-23 RESULT: PASS")
        print("=" * 132)
        print(f"{'Historical reference':72}: {EXPECTED_REFERENCE_KEY} @ 100 days")
        print(f"{'Historical authoritative plume threshold':72}: S >= 0.5")
        print(f"{'Recovery bundle SHA-256':72}: {recovery_zip_sha}")
        print(f"{'E22-R4 candidate file SHA-256':72}: {candidate_sha_before}")
        print(f"{'Independent 100-day reference array SHA-256':72}: {independent_hash}")
        print(f"{'Independent 100-day plume-mask SHA-256':72}: {independent_mask_hash}")
        print(f"{'Independent reconstruction L1 / Linf':72}: {l1:.17g} / {linf:.17g}")
        print(f"{'Independent reconstruction bitwise exact':72}: YES")
        print(f"{'Plume cells / footprint cells / vertical extent':72}: {morph['plume_cells']} / {morph['footprint_cells']} / {morph['vertical_extent_layers']}")
        print(f"{'Reference candidate frozen':72}: NO")
        print(f"{'Ready for V16E-24 reference freeze':72}: YES")
        print(f"{'V16 candidate performance used':72}: NO")
        print(f"{'Deployment pass/fail evaluated':72}: NO")
        print(f"{'V16 frozen candidate modified':72}: NO")
        print(f"{'Internal test / OOD reopened':72}: NO / NO")
        for p in [numerical_out, contract_out, readiness_out, summary_out, handoff_out, authority_csv, recovery_csv, identity_csv, readiness_csv, gate_csv]:
            print(f"{p.name} SHA: {sha256_file(p)}")
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
            "E22R4_candidate_modified": False,
            "reference_candidate_frozen": False,
            "historical_truth_regenerated": False,
            "candidate_performance_used": False,
            "deployment_pass_fail_evaluated": False,
            "V16_frozen_candidate_modified": False,
            "full_grid_plume_authorized": False,
            "next_milestone": NEXT_FAIL,
            "traceback": traceback.format_exc(),
        }
        save_json(blocked_json, payload)
        print(f"\n[FAIL] V16E-23 did not close: {exc}")
        print(f"Blocked report SHA: {sha256_file(blocked_json)}")
        print(f"Blocked output: {blocked}")
        return 2


def parse_args():
    p = argparse.ArgumentParser(description="PAD-Stream V16E-23 independent historical 100-day reference validation")
    p.add_argument("--project-root", required=True)
    p.add_argument("--drive-root", required=True)
    p.add_argument("--recovery-zip", required=True)
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(main(Path(args.project_root), Path(args.drive_root), Path(args.recovery_zip)))
