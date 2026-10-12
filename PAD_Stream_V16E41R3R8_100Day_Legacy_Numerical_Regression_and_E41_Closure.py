from __future__ import annotations
from pathlib import Path
import argparse, csv, hashlib, importlib.util, io, json, subprocess, sys, zipfile
from typing import Any
import numpy as np

MILESTONE = "V16E-41-R3-R8"
STATUS = "E41_REPAIRED_100D_PRODUCTION_AND_LEGACY_NUMERICAL_REGRESSION_CLOSED"
NEXT = "V16E-42 - Repaired Production Continuation to Exact 150-Day Observation"
TARGET_DAY = 100.0
BACKGROUND_SATURATION = 0.20
ACTIVE_INCREMENT_THRESHOLD = 1e-8
VISIBLE_INCREMENT_THRESHOLD = 1e-4
EXPECTED_GRID = (15, 50, 50)
EXPECTED_CELLS = 37500
FT_TO_M = 0.3048
DAY_TO_S = 86400.0

R3R7_RUNNER = "PAD_Stream_V16E41R3R7_Repaired_Production_Rollout_to_Exact_100Day_Observation.py"
R3R7_GIT_BLOB = "1e7e54f17477788fe518e440c21a65a544b30a48"
LEGACY_E41_RUNNER = "PAD_Stream_V16E41_Production_100D_Checkpoint_and_Legacy_Frozen_Candidate_Regression.py"
LEGACY_E41_GIT_BLOB = "458b22ca4d8c38982cc9756c93b79351ccd92987"
R3R7_REL = Path("provenance/hybrid_dp/V16E41R3R7_REPAIRED_PRODUCTION_EXACT_100D_OBSERVATION")
R3R7_SUMMARY = "PAD_Stream_V16E41R3R7_Summary.json"
R3R7_CLOSURE = "V16E41R3R7_Final_Closure.json"
R3R7_OBS = "V16E41R3R7_Canonical_Exact_100d_Observation_State_PreRefresh.npz"
R3R7_RESTART = "V16E41R3R7_Authoritative_100d_PostObservation_Refreshed_Restart.npz"
EXPECTED_R3R7_STATUS = "REPAIRED_PRODUCTION_EXACT_100D_OBSERVATION_VALIDATED"
EXPECTED_R3R7_OBS_SHA = "0418c18e24c967747c7d9dd4024c68635a83bbcf4ee0fe276683e1fb5aa1321e"
EXPECTED_R3R7_RESTART_SHA = "0772e6c067d36c20037ff448e2b1ebc7e11c53ef8e05642264583c56bb18a770"

LEGACY_REL = Path("provenance/hybrid_dp/V16E18_R1_FROZEN_SGSIM_100D_FULL_GRID_CANDIDATE")
LEGACY_SUMMARY = "PAD_Stream_V16E18_R1_Summary.json"
LEGACY_MANIFEST = "V16E18_R1_Full_Grid_Freeze_Manifest.json"
LEGACY_SUBDIR = "frozen_full_grid"
LEGACY_FILE = "V16E18_R1_Frozen_SGSim_100Day_Full_Grid_Candidate.npz"
LEGACY_FROZEN_SHA256 = "d422dc1e56281c1baf0ae007c62ce4bd69677a232bd1448a5bd79d3177eafaea"
LEGACY_EXPECTED_SUPPORTED = 20462
LEGACY_EXPECTED_UNSUPPORTED = 17038
LEGACY_EXPECTED_MIN = 0.20
LEGACY_EXPECTED_MAX = 0.78499960534060065


SG7A_GIT_BLOB = "a4dd47338e7a85f130a6a70d0a41211e38c655f8"
SG7D_GIT_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"

E36_REL = Path("provenance/hybrid_dp/V16E36_SHORT_ADAPTIVE_SGSIM_ROLLOUT_EARLY_PLUME_VALIDATION")
E36_CACHE = "V16E36_Certified_Physics_Cache.npz"
OUT_REL = Path("provenance/hybrid_dp/V16E41R3R8_100D_LEGACY_NUMERICAL_REGRESSION_AND_E41_CLOSURE")
BLOCKED_REL = Path("provenance/hybrid_dp/V16E41R3R8_BLOCKED_100D_LEGACY_NUMERICAL_REGRESSION_AND_E41_CLOSURE")

class GateError(RuntimeError):
    pass

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

def arr_sha(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()

def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")

def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader(); w.writerows(rows)
    return buf.getvalue().encode("utf-8")

def deterministic_npz_bytes(arrays: dict[str, Any]) -> bytes:
    outer = io.BytesIO()
    with zipfile.ZipFile(outer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for key in sorted(arrays):
            b = io.BytesIO(); np.save(b, np.asarray(arrays[key]), allow_pickle=False)
            info = zipfile.ZipInfo(f"{key}.npy", date_time=(1980,1,1,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, b.getvalue())
    return outer.getvalue()

def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        if p.exists() and p.read_bytes() != data:
            raise GateError(f"existing_output_differs:{name}")
        if not p.exists():
            p.write_bytes(data)

def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k].copy() for k in z.files}

def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load_module:{path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

def git_blob_sha(path: Path, repo_root: Path) -> str:
    return subprocess.check_output(
        ["git","-C",str(repo_root),"hash-object",str(path)], text=True
    ).strip()

def scalar(a: Any) -> float:
    return float(np.asarray(a).reshape(()))

def int_scalar(a: Any) -> int:
    return int(np.asarray(a).reshape(()))

def self_test() -> None:
    if TARGET_DAY != 100.0 or EXPECTED_CELLS != int(np.prod(EXPECTED_GRID)):
        raise RuntimeError("identity_failure")
    if LEGACY_EXPECTED_SUPPORTED + LEGACY_EXPECTED_UNSUPPORTED != EXPECTED_CELLS:
        raise RuntimeError("partition_identity_failure")
    if False:  # closeness threshold intentionally unfrozen
        raise RuntimeError("illegal_regression_threshold")
    print("PAD-Stream V16E-41-R3-R8 100-day legacy numerical regression / E41 closure self-test: PASS")

def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL
    gates: dict[str, dict[str, Any]] = {}
    failed_stage = None

    def gate(name: str, passed: bool, detail: Any = "") -> None:
        gates[name] = {"passed": bool(passed), "detail": str(detail)}
        if not passed:
            raise GateError(name)

    try:
        print("\n" + "="*158)
        print("PAD-Stream V16E-41-R3-R8 — 100-Day Legacy Numerical Regression and E41 Closure")
        print("="*158)
        print("New state : repaired exact R3-R7 100-day production observation")
        print("Legacy    : immutable V16E18-R1 numerical deployment candidate")
        print("Rule      : numerical differences are diagnostic; no invented closeness gate")

        failed_stage = "source_and_provenance_binding"
        for role, filename, blob in [
            ("R3R7", R3R7_RUNNER, R3R7_GIT_BLOB),
            ("LEGACY_E41", LEGACY_E41_RUNNER, LEGACY_E41_GIT_BLOB),
        ]:
            p = root / filename
            gate(f"{role}_runner_exists", p.is_file(), p)
            actual = git_blob_sha(p, root)
            gate(f"{role}_git_blob_exact", actual == blob, actual)

        helper = load_module(root / LEGACY_E41_RUNNER, "pad_stream_v16e41r3r8_legacy_helper")

        r3r7_dir = drive / R3R7_REL
        obs_path = r3r7_dir / R3R7_OBS
        restart_path = r3r7_dir / R3R7_RESTART
        summary_path = r3r7_dir / R3R7_SUMMARY
        closure_path = r3r7_dir / R3R7_CLOSURE

        legacy_dir = drive / LEGACY_REL
        legacy_path = legacy_dir / LEGACY_SUBDIR / LEGACY_FILE
        legacy_summary_path = legacy_dir / LEGACY_SUMMARY
        legacy_manifest_path = legacy_dir / LEGACY_MANIFEST
        e36_cache_path = drive / E36_REL / E36_CACHE

        for p in [obs_path,restart_path,summary_path,closure_path,legacy_path,legacy_summary_path,legacy_manifest_path,e36_cache_path]:
            gate(f"artifact_exists_{p.name}", p.is_file(), p)

        r3r7_summary = load_json(summary_path)
        r3r7_closure = load_json(closure_path)
        legacy_summary = load_json(legacy_summary_path)
        legacy_manifest = load_json(legacy_manifest_path)

        gate("R3R7_status_exact", r3r7_summary.get("status") == EXPECTED_R3R7_STATUS, r3r7_summary.get("status"))
        gate("R3R7_closure_passed", r3r7_closure.get("all_gates_passed") is True, r3r7_closure.get("all_gates_passed"))
        gate("R3R7_regression_authorized", r3r7_summary.get("100d_legacy_regression_authorized") is True)
        gate("R3R7_E41_open_on_entry", r3r7_summary.get("E41_closed") is False)

        obs_sha_before = sha256_file(obs_path)
        restart_sha_before = sha256_file(restart_path)
        legacy_sha_before = sha256_file(legacy_path)
        e36_cache_sha_before = sha256_file(e36_cache_path)
        gate("R3R7_observation_SHA_exact", obs_sha_before == EXPECTED_R3R7_OBS_SHA, obs_sha_before)
        gate("R3R7_restart_SHA_exact", restart_sha_before == EXPECTED_R3R7_RESTART_SHA, restart_sha_before)
        gate("legacy_frozen_SHA_exact", legacy_sha_before == LEGACY_FROZEN_SHA256, legacy_sha_before)
        gate("legacy_summary_PASS", legacy_summary.get("status") == "PASS", legacy_summary.get("status"))
        gate("legacy_candidate_frozen", legacy_summary.get("candidate_frozen") is True)
        gate("legacy_not_full_grid_truth", legacy_summary.get("full_grid_plume_authorized") is False)
        gate("legacy_SHA_matches_manifest", legacy_manifest.get("authoritative_frozen_sha256") == legacy_sha_before)

        observation = load_npz(obs_path)
        restart = load_npz(restart_path)
        cache = load_npz(e36_cache_path)
        gate("new_observation_time_exact", scalar(observation["physical_time_days"]) == TARGET_DAY)
        gate("new_observation_cursor_exact", int_scalar(observation["observation_cursor_index"]) == 3 and scalar(observation["last_fixed_observation_day"]) == 100.0 and scalar(observation["next_fixed_observation_day"]) == 150.0)
        gate("restart_same_step_time", int_scalar(restart["accepted_step_index"]) == int_scalar(observation["accepted_step_index"]) and scalar(restart["physical_time_days"]) == TARGET_DAY)

        failed_stage = "legacy_candidate_schema_binding"
        with np.load(legacy_path, allow_pickle=False) as z:
            required = [
                "saturation_grid_full_float64","saturation_grid_supported_only_float64",
                "supported_mask","support_denominator","support_numerator",
                "segment_piece_count","streamline_visit_count","background_saturation",
                "physical_time_days","grid_shape"
            ]
            gate("legacy_required_arrays_present", all(k in z.files for k in required), required)
            legacy_sat = np.asarray(z["saturation_grid_full_float64"], dtype=np.float64).copy()
            legacy_supported_only = np.asarray(z["saturation_grid_supported_only_float64"], dtype=np.float64).copy()
            legacy_supported_mask = np.asarray(z["supported_mask"], dtype=bool).copy()
            legacy_denominator = np.asarray(z["support_denominator"]).copy()
            legacy_numerator = np.asarray(z["support_numerator"]).copy()
            legacy_piece_count = np.asarray(z["segment_piece_count"]).copy()
            legacy_visit_count = np.asarray(z["streamline_visit_count"]).copy()
            legacy_background = float(np.asarray(z["background_saturation"]))
            legacy_time = float(np.asarray(z["physical_time_days"]))
            legacy_grid = tuple(int(x) for x in np.asarray(z["grid_shape"]).tolist())

        gate("legacy_grid_exact", legacy_sat.shape == EXPECTED_GRID and legacy_grid == EXPECTED_GRID and legacy_sat.size == EXPECTED_CELLS, f"{legacy_sat.shape}:{legacy_grid}")
        gate("legacy_time_exact_100d", legacy_time == TARGET_DAY, legacy_time)
        gate("legacy_background_exact", legacy_background == BACKGROUND_SATURATION, legacy_background)
        gate("legacy_bounds_exact", float(np.min(legacy_sat)) == LEGACY_EXPECTED_MIN and float(np.max(legacy_sat)) == LEGACY_EXPECTED_MAX, f"{np.min(legacy_sat)}:{np.max(legacy_sat)}")
        gate("legacy_support_counts_exact", int(np.sum(legacy_supported_mask)) == LEGACY_EXPECTED_SUPPORTED and int(np.sum(~legacy_supported_mask)) == LEGACY_EXPECTED_UNSUPPORTED)
        gate("legacy_background_has_zero_support_evidence", bool(np.all(legacy_denominator[~legacy_supported_mask] == 0.0)) and bool(np.all(legacy_numerator[~legacy_supported_mask] == 0.0)))

        failed_stage = "field_regression"
        new_sat = np.asarray(observation["transport_saturation"], dtype=np.float64)
        gate("new_grid_shape_exact", new_sat.shape == EXPECTED_GRID, new_sat.shape)
        gate("new_field_finite", bool(np.all(np.isfinite(new_sat))))
        gate("legacy_field_finite", bool(np.all(np.isfinite(legacy_sat))))

        whole = helper.field_error_metrics(new_sat, legacy_sat)
        supported = helper.field_error_metrics(new_sat, legacy_sat, legacy_supported_mask)
        background = helper.field_error_metrics(new_sat, legacy_sat, ~legacy_supported_mask)
        active_overlap = helper.overlap_metrics(new_sat, legacy_sat, ACTIVE_INCREMENT_THRESHOLD)
        visible_overlap = helper.overlap_metrics(new_sat, legacy_sat, VISIBLE_INCREMENT_THRESHOLD)
        new_centroid = helper.saturation_increment_centroid_m(new_sat)
        legacy_centroid = helper.saturation_increment_centroid_m(legacy_sat)
        centroid_delta = np.asarray(new_centroid) - np.asarray(legacy_centroid)
        centroid_distance = float(np.linalg.norm(centroid_delta))
        layer_rows = helper.layerwise_regression_rows(new_sat, legacy_sat, legacy_supported_mask)
        gate("core_field_metrics_finite", all(np.isfinite(float(whole[k])) for k in ["L1_mean_abs","L2_rms","Linf","signed_mean_bias_new_minus_legacy"]) and np.isfinite(centroid_distance))

        new_increment = np.clip(new_sat - BACKGROUND_SATURATION, 0.0, None)
        new_active_in_legacy_background = int(np.sum((~legacy_supported_mask) & (new_increment > ACTIVE_INCREMENT_THRESHOLD)))
        new_visible_in_legacy_background = int(np.sum((~legacy_supported_mask) & (new_increment > VISIBLE_INCREMENT_THRESHOLD)))

        failed_stage = "historical_common_evaluator"
        # Reuse the exact common evaluator intended by original E41:
        # frozen E36 reference pressure/streamline geometry. This is diagnostic only.
        for filename, expected_sha in [
            (helper.R2_RUNNER, helper.R2_RUNNER_SHA256),
            (helper.E36_RUNNER, helper.E36_RUNNER_SHA256),
            (helper.E37A_RUNNER, helper.E37A_RUNNER_SHA256),
            (helper.E37B_RUNNER, helper.E37B_RUNNER_SHA256),
        ]:
            p = root / filename
            gate(f"common_source_exists_{filename}", p.is_file(), p)
            gate(f"common_source_SHA_exact_{filename}", sha256_file(p) == expected_sha, sha256_file(p))

        for filename, expected_blob in [
            (helper.SG7A, SG7A_GIT_BLOB),
            (helper.SG7D, SG7D_GIT_BLOB),
        ]:
            p = root / filename
            gate(f"common_source_exists_{filename}", p.is_file(), p)
            gate(
                f"common_source_git_blob_exact_{filename}",
                git_blob_sha(p, root) == expected_blob,
                git_blob_sha(p, root),
            )

        r2 = load_module(root / helper.R2_RUNNER, "pad_stream_v16e41r3r8_r2")
        e36 = load_module(root / helper.E36_RUNNER, "pad_stream_v16e41r3r8_e36")
        e37a = load_module(root / helper.E37A_RUNNER, "pad_stream_v16e41r3r8_e37a")
        e37b = load_module(root / helper.E37B_RUNNER, "pad_stream_v16e41r3r8_e37b")
        sg7a = load_module(root / helper.SG7A, "pad_stream_v16e41r3r8_sg7a")
        sg7d = load_module(root / helper.SG7D, "pad_stream_v16e41r3r8_sg7d")

        pressure_psi = np.asarray(cache["accepted_pressure_psi"], dtype=np.float64)
        xyz_m = np.asarray(cache["streamline_xyz_m"], dtype=np.float64)
        tau_s = np.asarray(cache["streamline_tof_s"], dtype=np.float64)
        tau_end_s = np.asarray(cache["tau_end_s"], dtype=np.float64)
        weights_m3_s = np.asarray(cache["streamline_weights_m3_s"], dtype=np.float64)
        xi_faces = np.asarray(cache["xi"], dtype=np.float64)
        weights_m3_day = weights_m3_s * DAY_TO_S
        tof_days = tau_s / DAY_TO_S
        nstream = len(tau_end_s); nfaces = len(xi_faces); ncv = nfaces - 1
        operator = sg7d.build_subsegment_operator(xyz_m, tof_days, weights_m3_day)
        p_ref = scalar(observation["co2_density_reference_pressure_pa"])
        geometry = e37a.build_control_volume_geometry(r2, operator, pressure_psi, p_ref, nstream, ncv)
        cell_pore_volume_m3 = 0.20 * (20.0*FT_TO_M) * (20.0*FT_TO_M) * (4.0*FT_TO_M)

        new_common_mass = float(r2.stored_co2_mass_kg(new_sat, pressure_psi, p_ref, cell_pore_volume_m3))
        legacy_common_mass = float(r2.stored_co2_mass_kg(legacy_sat, pressure_psi, p_ref, cell_pore_volume_m3))
        new_cv_sat, _, new_close = e37a.sample_grid_inventory_to_control_volumes(r2, new_sat, pressure_psi, p_ref, geometry, nstream, ncv)
        legacy_cv_sat, _, legacy_close = e37a.sample_grid_inventory_to_control_volumes(r2, legacy_sat, pressure_psi, p_ref, geometry, nstream, ncv)
        common_tol = max(1e-6, 1e-10 * max(abs(new_common_mass), abs(legacy_common_mass), 1.0))
        gate("new_common_sampling_closure", abs(float(new_close)) <= common_tol, new_close)
        gate("legacy_common_sampling_closure", abs(float(legacy_close)) <= common_tol, legacy_close)
        new_common_cut = float(e37b.weighted_outlet_gas_cut(sg7a, new_cv_sat, weights_m3_day))
        legacy_common_cut = float(e37b.weighted_outlet_gas_cut(sg7a, legacy_cv_sat, weights_m3_day))
        gate("common_metrics_finite", all(np.isfinite(v) for v in [new_common_mass,legacy_common_mass,new_common_cut,legacy_common_cut]))

        failed_stage = "regression_closure"
        regression = {
            "milestone": MILESTONE,
            "status": "100D_LEGACY_NUMERICAL_REGRESSION_COMPUTED",
            "legacy_candidate_is_physical_truth": False,
            "legacy_full_grid_plume_claim_authorized": False,
            "regression_accuracy_threshold_frozen": False,
            "regression_difference_magnitude_is_blocking": False,
            "new_exact_100d_observation_state_sha256": obs_sha_before,
            "new_post_observation_restart_sha256": restart_sha_before,
            "legacy_frozen_file_sha256": legacy_sha_before,
            "new_observation_saturation_array_sha256": arr_sha(new_sat),
            "legacy_saturation_array_sha256": arr_sha(legacy_sat),
            "new_and_legacy_arrays_bitwise_equal": bool(np.array_equal(new_sat, legacy_sat)),
            "grid_shape": list(EXPECTED_GRID),
            "physical_time_days": TARGET_DAY,
            "legacy_supported_cells": int(np.sum(legacy_supported_mask)),
            "legacy_background_completed_cells": int(np.sum(~legacy_supported_mask)),
            "whole_grid": whole,
            "legacy_supported_partition": supported,
            "legacy_background_completed_partition": background,
            "active_plume_overlap": active_overlap,
            "visible_plume_overlap": visible_overlap,
            "new_incremental_saturation_centroid_m": {"x":new_centroid[0],"y":new_centroid[1],"z":new_centroid[2]},
            "legacy_incremental_saturation_centroid_m": {"x":legacy_centroid[0],"y":legacy_centroid[1],"z":legacy_centroid[2]},
            "centroid_shift_new_minus_legacy_m": {"dx":float(centroid_delta[0]),"dy":float(centroid_delta[1]),"dz":float(centroid_delta[2]),"distance":centroid_distance},
            "new_active_cells_inside_legacy_background_completed_partition": new_active_in_legacy_background,
            "new_visible_cells_inside_legacy_background_completed_partition": new_visible_in_legacy_background,
            "historical_E41_common_evaluator": {
                "basis": "Frozen E36 reference pressure and streamline geometry used by the original E41 regression design.",
                "new_repaired_implied_stored_CO2_mass_kg": new_common_mass,
                "legacy_implied_stored_CO2_mass_kg": legacy_common_mass,
                "stored_mass_difference_new_minus_legacy_kg": new_common_mass - legacy_common_mass,
                "new_repaired_recomputed_producer_CO2_gas_cut": new_common_cut,
                "legacy_recomputed_producer_CO2_gas_cut": legacy_common_cut,
                "producer_cut_difference_new_minus_legacy": new_common_cut - legacy_common_cut,
                "note": "These are common-evaluator diagnostics, not the authoritative dynamic-pressure mass ledger or producer metric of the repaired R3-R7 state."
            },
            "new_canonical_100d_state": {
                "accepted_step_index": int_scalar(observation["accepted_step_index"]),
                "stored_CO2_mass_kg": scalar(observation["stored_co2_mass_current_kg"]),
                "cumulative_injected_CO2_mass_kg": scalar(observation["cumulative_injected_co2_mass_kg"]),
                "cumulative_produced_CO2_mass_kg": scalar(observation["cumulative_produced_co2_mass_kg"]),
                "producer_CO2_gas_cut": scalar(observation["current_producer_co2_gas_cut"]),
                "breakthrough_time_days": scalar(observation["breakthrough_time_days"]),
            },
            "legacy_breakthrough_time_available_from_single_100d_candidate": False,
        }
        gate("no_invented_accuracy_gate", regression["regression_accuracy_threshold_frozen"] is False and regression["regression_difference_magnitude_is_blocking"] is False)
        gate("new_observation_immutable", sha256_file(obs_path) == obs_sha_before)
        gate("new_restart_immutable", sha256_file(restart_path) == restart_sha_before)
        gate("legacy_artifact_immutable", sha256_file(legacy_path) == legacy_sha_before)
        gate("E36_common_evaluator_cache_immutable", sha256_file(e36_cache_path) == e36_cache_sha_before)

        fields_bytes = deterministic_npz_bytes({
            "new_exact_100d_saturation_float64": new_sat,
            "legacy_frozen_saturation_float64": legacy_sat,
            "difference_new_minus_legacy_float64": new_sat - legacy_sat,
            "legacy_supported_mask": legacy_supported_mask,
            "legacy_supported_only_float64": legacy_supported_only,
            "legacy_support_denominator": legacy_denominator,
            "legacy_support_numerator": legacy_numerator,
            "legacy_segment_piece_count": legacy_piece_count,
            "legacy_streamline_visit_count": legacy_visit_count,
        })
        fields_sha = hashlib.sha256(fields_bytes).hexdigest()

        summary = {
            "milestone": MILESTONE,
            "status": STATUS,
            "E41_closed": True,
            "closure_basis": [
                "R3-R7 reached the exact repaired 100-day observation under the frozen production runtime.",
                "The canonical 100-day observation and same-time post-observation restart remain immutable.",
                "The V16E18-R1 candidate remained immutable and was treated only as historical numerical regression evidence.",
                "Whole-grid, partitioned, overlap, centroid, layerwise, stored-mass and producer-response diagnostics were computed.",
                "No unfrozen numerical-closeness criterion was invented or used as a blocker."
            ],
            "key_regression_metrics": {
                "whole_grid_L1_mean_abs": whole["L1_mean_abs"],
                "whole_grid_L2_rms": whole["L2_rms"],
                "whole_grid_Linf": whole["Linf"],
                "whole_grid_pearson_correlation": whole["pearson_correlation"],
                "supported_partition_L1_mean_abs": supported["L1_mean_abs"],
                "background_completed_partition_L1_mean_abs": background["L1_mean_abs"],
                "active_plume_IOU": active_overlap["intersection_over_union"],
                "visible_plume_IOU": visible_overlap["intersection_over_union"],
                "centroid_shift_distance_m": centroid_distance,
                "historical_common_evaluator_mass_difference_kg": new_common_mass - legacy_common_mass,
                "historical_common_evaluator_producer_cut_difference": new_common_cut - legacy_common_cut,
            },
            "authoritative_100d_production_restart": str(restart_path),
            "next_observation_day": 150.0,
            "next_milestone": NEXT,
        }

        closure = {
            "milestone": MILESTONE,
            "status": STATUS,
            "all_gates_passed": all(v["passed"] for v in gates.values()),
            "gate_count": len(gates),
            "repaired_exact_100d_state_validated": True,
            "legacy_numerical_regression_completed": True,
            "legacy_candidate_is_physical_truth": False,
            "regression_accuracy_threshold_frozen": False,
            "regression_difference_magnitude_is_blocking": False,
            "new_100d_observation_state_sha256": obs_sha_before,
            "new_100d_runtime_restart_sha256": restart_sha_before,
            "legacy_frozen_candidate_sha256": legacy_sha_before,
            "regression_fields_sha256": fields_sha,
            "E41_closed": True,
            "next_milestone": NEXT,
        }

        files = {
            "PAD_Stream_V16E41R3R8_Summary.json": json_bytes(summary),
            "V16E41R3R8_100D_Legacy_Regression_Metrics.json": json_bytes(regression),
            "V16E41R3R8_100D_Layerwise_Regression.csv": csv_bytes(layer_rows),
            "V16E41R3R8_100D_Regression_Fields.npz": fields_bytes,
            "V16E41R3R8_Final_Gate_Matrix.csv": csv_bytes([{"gate":k, **v} for k,v in gates.items()]),
            "V16E41R3R8_Final_Closure.json": json_bytes(closure),
        }
        immutable_publish(out, files)
        manifest = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "V16E41R3R8_Artifact_Manifest.csv":
                manifest.append({"file":p.name,"sha256":sha256_file(p),"bytes":p.stat().st_size})
        immutable_publish(out, {"V16E41R3R8_Artifact_Manifest.csv": csv_bytes(manifest)})

        print("\n" + "="*158)
        print("PAD-Stream V16E-41-R3-R8: PASS")
        print("="*158)
        print(f"{'Status':72}: {STATUS}")
        print(f"{'New exact 100d observation SHA':72}: {obs_sha_before}")
        print(f"{'New 100d production restart SHA':72}: {restart_sha_before}")
        print(f"{'Legacy frozen candidate SHA':72}: {legacy_sha_before}")
        print(f"{'Whole-grid L1 mean abs saturation difference':72}: {whole['L1_mean_abs']:.12e}")
        print(f"{'Whole-grid L2 RMS saturation difference':72}: {whole['L2_rms']:.12e}")
        print(f"{'Whole-grid Linf saturation difference':72}: {whole['Linf']:.12e}")
        print(f"{'Whole-grid Pearson correlation':72}: {whole['pearson_correlation']:.12g}")
        print(f"{'Legacy-supported L1 mean abs difference':72}: {supported['L1_mean_abs']:.12e}")
        print(f"{'Legacy-background-completed L1 mean abs difference':72}: {background['L1_mean_abs']:.12e}")
        print(f"{'Active-plume IOU':72}: {active_overlap['intersection_over_union']:.12g}")
        print(f"{'Visible-plume IOU':72}: {visible_overlap['intersection_over_union']:.12g}")
        print(f"{'Incremental-saturation centroid shift':72}: {centroid_distance:.12g} m")
        print(f"{'Historical common-evaluator mass difference':72}: {new_common_mass-legacy_common_mass:.12e} kg")
        print(f"{'Historical common-evaluator producer-cut difference':72}: {new_common_cut-legacy_common_cut:.12e}")
        print(f"{'Regression closeness threshold frozen':72}: False")
        print(f"{'Regression difference magnitude blocking':72}: False")
        print(f"{'E41 closed':72}: True")
        print(f"{'Next':72}: {NEXT}")
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": "E41_100D_LEGACY_NUMERICAL_REGRESSION_CLOSURE_BLOCKED",
            "failed_stage": failed_stage,
            "exception": repr(exc),
            "gates": gates,
        }
        data = json_bytes(report)
        p = blocked / "V16E41R3R8_Blocked_Regression_Closure.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / ("V16E41R3R8_Blocked_Regression_Closure_" + hashlib.sha256(data).hexdigest()[:12] + ".json")
        p.write_bytes(data)
        print("\n" + "="*158)
        print("PAD-Stream V16E-41-R3-R8: BLOCKED")
        print("="*158)
        print("Report      :", p)
        print("Failed stage:", failed_stage)
        print("Exception   :", repr(exc))
        return 2

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", type=Path, default=Path("."))
    p.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    p.add_argument("--self-test", action="store_true")
    return p.parse_args()

if __name__ == "__main__":
    args = parse_args()
    if args.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root))
