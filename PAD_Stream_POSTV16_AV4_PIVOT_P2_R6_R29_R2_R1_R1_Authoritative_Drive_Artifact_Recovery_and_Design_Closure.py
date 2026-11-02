#!/usr/bin/env python3
from __future__ import annotations

import argparse, ast, csv, hashlib, importlib.util, inspect, io, json, re, subprocess, sys
from pathlib import Path
from typing import Any
import numpy as np

M = "POSTV16-AV4-PIVOT-P2-R6-R29-R2-R1-R1"
NAME = "Authoritative Drive Artifact Recovery + Recovered Heterogeneous-PV Design Closure"

PASS = (
    "AV4PIVOTP2R6R29R2R1R1_AUTHORITATIVE_DRIVE_ARTIFACT_RECOVERY_AND_"
    "RECOVERED_HETEROGENEOUS_PV_DESIGN_CLOSURE_PASS_NO_EXECUTION"
)
BLOCK = "AV4PIVOTP2R6R29R2R1R1_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "1f3c9ff327022fae5edae0c7df229614a4d62c41"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"

GRID = (15, 50, 50)
DAY = 375.0
DT_DAYS = 0.03721673128859954
CANDIDATE_TARGET_DAY = 375.0372167312886
UNIFORM_PHI = 0.20
MAX_SG = 0.60

# --------------------------------------------------------------------------------------
# Immutable lineage / publication identities.
# --------------------------------------------------------------------------------------

R29_FAIL_SHA256 = "1522b39b9e2c89cacf8899c07bcedf61a841a57ca61cc47bd41fbcd818b02209"
R29R1_BLOCK_SHA256 = "cde61dec85e1d183ee07329ce30329e9f7e9c88d62ee798ac648cec129933ab5"

R29R1R1_COMMIT = "f47247241036becfc154546dd197201423514703"
R29R1R1_RUNNER_SHA256 = "9b4c82bda2924155458183f6757991795c14fc2080ccbbf2b8ee842f343df289"
R29R1R1_RUNNER_BLOB = "2530da823cb25febcf66eb9baa5b971da51b662d"
R29R1R1_STATUS = (
    "AV4PIVOTP2R6R29R1R1_COMPREHENSIVE_TECHNICAL_CLOSURE_PASS_"
    "R29R1_DIAGNOSTIC_RECOVERED_NO_SCIENCE_STATE_MUTATION"
)
R29R1R1_CLASSIFICATION = (
    "R6R29R1R1_TECHNICAL_CLOSURE_RECOVERS_R29R1_DIAGNOSTIC_"
    "EXACT_STRING_FLOAT_FORMAT_GATE_ONLY_AV4_HETEROGENEOUS_PARENT_VALID_"
    "R29R2_REPAIR_DESIGN_NEXT"
)

# Values observed in the formal R29-R1-R1 PASS output.
OBS_R29R1_EXCEPTION_TEXT = "GateError('capillary_cell_mass_capacity_exceeded:1750.6206916789206')"
OBS_R29R1_EXCEPTION_EXCESS_KG = 1750.6206916789206
OBS_R29_FAIL_EXCESS_KG = 1750.620691678921
OBS_UNIFORM_MAX_EXCESS_KG = 1750.620691678921
OBS_UNIFORM_VIOLATING_COUNT = 6352
OBS_HETERO_MAX_EXCESS_KG = -0.011893801401129167
OBS_HETERO_CAP_TOL_KG = 1e-8
OBS_HETERO_VIOLATING_COUNT = 0
OBS_SAT_MAX_ABS_ERROR = 0.0
OBS_MASS_MAX_ABS_ERROR_KG = 4.547473508864641e-12

# Original canonical R29-R1-R1 directory. This is intentionally expected to be absent.
ORIG_R29R1R1_REL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R29_R1_R1_"
    "Comprehensive_Technical_Closure_PoreVolume_Diagnostic"
)
ORIG_R29R1R1_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R1_R1_Summary.json"

# Historical R29-R2 / current R29-R2-R1 publication.
R29R2_COMMIT = "c1ed4fa0baafe25104ce971e61f23ccd921f7c90"
R29R2_RUNNER_SHA256 = "68d20b0353f574d92a944f68e9bdb948d285a7a4b190ca87a9a186928eb0a870"
R29R2_RUNNER_BLOB = "a0763f963b70522b3b5122b1286b0bf34c0e4234"
R29R2_BLOCK_STAGE = "R29R1R1_authority"
R29R2_BLOCK_EXCEPTION = "FileNotFoundError(2, 'No such file or directory')"

R29R2R1_COMMIT = PARENT
R29R2R1_RUNNER_SHA256 = "43fced5e3f5cb3b997246f915c44a70df7f3438f97cabd62c8d2c37a4e6a989e"
R29R2R1_RUNNER_BLOB = "3716a32b2879ad6c526092ecea01a0a08fb3895f"

# --------------------------------------------------------------------------------------
# Frozen input authorities required to reconstruct the diagnostic.
# --------------------------------------------------------------------------------------

R25R3_REL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R25_R3_"
    "Controlled_Day375_CapacityLimited_ExactSupport_SplitState_"
    "Reprojection_Execution_Stage2_PresolveOff"
)
R25R3_STATE = "POSTV16_AV4_PIVOT_P2_R6_R25_R3_CapacityLimited_SplitState_Day375.npz"
R25R3_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R25_R3_Artifact_Manifest.csv"
R25R3_STATE_SHA256 = "9893e2476bce1d46213cdd1304e60ad93b49ea285e084d06743a2ffab25f721f"

CLOSURE_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_R1_R1_R1"
CLOSURE_REL = BASE / (
    CLOSURE_TOKEN
    + "_Comprehensive_Technical_Closure_and_Pressure_Refresh_Acceptance"
)
CLOSURE_SUMMARY = f"PAD_Stream_{CLOSURE_TOKEN}_Summary.json"
CLOSURE_MANIFEST = f"{CLOSURE_TOKEN}_Artifact_Manifest.csv"
PRESSURE_EPOCH = f"{CLOSURE_TOKEN}_Accepted_Day375_Pressure_Epoch.npz"
PRESSURE_EPOCH_SHA256 = "99d73cab1d33191a68578f29d3c03f9fac07ed77c39e124cc8eb5e5bf75aa84d"

A6E_REL = BASE_AV3 / "POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
A6E_STATE = "POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
A6E_STATE_SHA256 = "f9e3a7bd8c6dcc43d522e0cb99a0cede2bd212fd570085b4faf82dc71af8f803"

R28_REL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R28_"
    "FrozenFlow_Transport_DeltaMapback_ResidualWell_Coupling_Protocol_Freeze"
)
R28_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R28_Summary.json"
R28_DECISION = "POSTV16_AV4_PIVOT_P2_R6_R28_Decision_Contract.json"
R28_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R28_Artifact_Manifest.csv"

# --------------------------------------------------------------------------------------
# Repository source authorities.
# --------------------------------------------------------------------------------------

R29R1R1_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R1_R1_Comprehensive_Technical_Closure.py"
R29R2_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R2_"
    "Heterogeneous_Cartesian_PV_DeltaMapback_Repair_Design_Freeze.py"
)
R29R2R1_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R2_R1_"
    "Comprehensive_Technical_Closure_and_Recovered_Design_Freeze.py"
)
E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"
R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

SOURCE_BLOBS = {
    R29R1R1_RUNNER: R29R1R1_RUNNER_BLOB,
    R29R2_RUNNER: R29R2_RUNNER_BLOB,
    R29R2R1_RUNNER: R29R2R1_RUNNER_BLOB,
    E37A: E37A_BLOB,
    A2E: A2E_BLOB,
    R2: R2_BLOB,
}

OUT_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R29_R2_R1_R1"
OUT_REL = BASE / (
    OUT_TOKEN
    + "_Authoritative_Drive_Artifact_Recovery_and_Recovered_Design_Closure"
)
BLOCK_REL = BASE / (OUT_TOKEN + "_BLOCKED")


class GateError(RuntimeError):
    pass


def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def js(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def csvr(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
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
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")


def manifest(directory: Path, filename: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in csvr(directory / filename):
        p = directory / row["file"]
        if not p.is_file():
            raise GateError(f"manifest_missing:{p.name}")
        if sha(p) != row["sha256"]:
            raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes:{p.name}")
        out[p.name] = row["sha256"]
    return out


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load:{path}")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def selftest() -> None:
    assert abs((CANDIDATE_TARGET_DAY - DAY) - DT_DAYS) < 1e-12
    assert OBS_UNIFORM_VIOLATING_COUNT == 6352
    assert OBS_HETERO_VIOLATING_COUNT == 0
    print("POSTV16 AV4 PIVOT P2-R6-R29-R2-R1-R1 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    block_dir = drive / BLOCK_REL
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
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"))
        if not ok:
            raise GateError(name)

    try:
        # ------------------------------------------------------------------
        # Prove authoritative Drive using frozen inputs that predate the loss.
        # ------------------------------------------------------------------
        stage = "real_drive_authority"

        gate("drive_root_exists", drive.is_dir(), str(drive))
        r25_state = drive / R25R3_REL / R25R3_STATE
        pressure_path = drive / CLOSURE_REL / PRESSURE_EPOCH
        a6e_path = drive / A6E_REL / A6E_STATE
        r28_summary_path = drive / R28_REL / R28_SUMMARY

        gate("R25R3_authority_probe_exists", r25_state.is_file(), str(r25_state))
        gate("pressure_epoch_authority_probe_exists", pressure_path.is_file(), str(pressure_path))
        gate("A6E_porosity_authority_probe_exists", a6e_path.is_file(), str(a6e_path))
        gate("R28_authority_probe_exists", r28_summary_path.is_file(), str(r28_summary_path))

        # The canonical R29-R1-R1 artifact is expected to be missing.
        orig_summary = drive / ORIG_R29R1R1_REL / ORIG_R29R1R1_SUMMARY
        gate("original_R29R1R1_summary_absent_on_authoritative_drive", not orig_summary.is_file(), str(orig_summary))

        stage = "preexisting_state_firewall"
        gate("no_preexisting_recovery_PASS", not (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").exists())
        gate("no_preexisting_recovery_BLOCK", not (block_dir / f"{OUT_TOKEN}_Blocked_Report.json").exists())

        # ------------------------------------------------------------------
        # Repository / immutable lineage.
        # ------------------------------------------------------------------
        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R29R2R1_publication", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")

        for filename, expected in SOURCE_BLOBS.items():
            p = root / filename
            gate(f"{Path(filename).stem}_present", p.is_file(), str(p))
            actual = gt(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(filename).stem}_blob_exact", actual == expected, actual)

        # ------------------------------------------------------------------
        # Frozen input manifests / exact SHAs.
        # ------------------------------------------------------------------
        stage = "frozen_input_authority"

        r25 = drive / R25R3_REL
        m25 = manifest(r25, R25R3_MANIFEST)
        gate("R25R3_state_SHA_exact", m25.get(R25R3_STATE) == R25R3_STATE_SHA256 and sha(r25_state) == R25R3_STATE_SHA256)

        closure = drive / CLOSURE_REL
        mc = manifest(closure, CLOSURE_MANIFEST)
        gate("pressure_epoch_SHA_exact", mc.get(PRESSURE_EPOCH) == PRESSURE_EPOCH_SHA256 and sha(pressure_path) == PRESSURE_EPOCH_SHA256)

        gate("A6E_state_SHA_exact", sha(a6e_path) == A6E_STATE_SHA256)

        r28 = drive / R28_REL
        manifest(r28, R28_MANIFEST)
        s28 = js(r28 / R28_SUMMARY)
        d28 = js(r28 / R28_DECISION)
        gate("R28_dt_exact", float(s28["nominal_dt_days"]) == DT_DAYS)
        gate("R28_target_day_exact", float(s28["candidate_target_day"]) == CANDIDATE_TARGET_DAY)
        gate("R28_delta_mapback_required", s28.get("delta_mapback_required") is True)
        gate("R28_absolute_mapback_forbidden", s28.get("absolute_mapback_forbidden") is True)
        gate("R28_residual_mutation_forbidden", d28.get("residual_sidecar_mutation_authorized") is False)

        # ------------------------------------------------------------------
        # Reconstruct the lost R29-R1-R1 diagnostic from frozen inputs.
        # This is a child recovery computation, NOT a rerun/overwrite of R29-R1-R1.
        # ------------------------------------------------------------------
        stage = "R29R1R1_diagnostic_reconstruction"

        with np.load(r25_state, allow_pickle=False) as z:
            parent_mass = np.asarray(z["cartesian_component_mass_kg"], dtype=np.float64)

        with np.load(pressure_path, allow_pickle=False) as z:
            pressure_mass = np.asarray(z["pressure_compatible_grid_mass_kg"], dtype=np.float64)
            pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            accepted_sat = np.asarray(z["reconciled_saturation"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))

        with np.load(a6e_path, allow_pickle=False) as z:
            phi = np.asarray(z["paired_porosity"], dtype=np.float64)

        gate("accepted_parent_mass_identity", np.array_equal(parent_mass, pressure_mass))
        gate("paired_porosity_shape_exact", phi.shape == GRID)
        gate("paired_porosity_positive_finite", np.all(phi > 0.0) and np.isfinite(phi).all())

        a2e = load_module(root / A2E, "r29r2r1r1_a2e")
        r2 = load_module(root / R2, "r29r2r1r1_r2")
        e37a = load_module(root / E37A, "r29r2r1r1_e37a")

        hetero_pv = phi * float(a2e.BULK_VOLUME_M3)
        uniform_pv_scalar = float(UNIFORM_PHI * float(a2e.BULK_VOLUME_M3))
        uniform_pv = np.full(GRID, uniform_pv_scalar, dtype=np.float64)

        full_sat = np.full(GRID, float(a2e.INJECTED), dtype=np.float64)
        rho_at_max = np.asarray(r2.gas_density_from_state(full_sat, pressure, p_ref), dtype=np.float64)

        uniform_capacity = uniform_pv * rho_at_max * MAX_SG
        hetero_capacity = hetero_pv * rho_at_max * MAX_SG

        uniform_excess_arr = parent_mass - uniform_capacity
        hetero_excess_arr = parent_mass - hetero_capacity
        uniform_max_excess = float(np.max(uniform_excess_arr))
        hetero_max_excess = float(np.max(hetero_excess_arr))
        uniform_violating = int(np.count_nonzero(uniform_excess_arr > 1e-8))
        hetero_cap_tol = max(1e-8, 1e-12 * max(float(np.max(hetero_capacity)), 1.0))
        hetero_violating = int(np.count_nonzero(hetero_excess_arr > hetero_cap_tol))

        gate("reconstruct_uniform_max_excess", abs(uniform_max_excess - OBS_UNIFORM_MAX_EXCESS_KG) <= 1e-9, uniform_max_excess)
        gate("reconstruct_uniform_violating_count", uniform_violating == OBS_UNIFORM_VIOLATING_COUNT, uniform_violating)
        gate("reconstruct_heterogeneous_max_excess", abs(hetero_max_excess - OBS_HETERO_MAX_EXCESS_KG) <= 1e-12, hetero_max_excess)
        gate("reconstruct_heterogeneous_zero_violations", hetero_violating == OBS_HETERO_VIOLATING_COUNT, hetero_violating)

        sg_hetero = np.asarray(
            a2e.invert_local_mass(r2, parent_mass, pressure, p_ref, hetero_pv),
            dtype=np.float64,
        )
        sat_hetero = float(a2e.BACKGROUND) + sg_hetero
        sat_err = float(np.max(np.abs(sat_hetero - accepted_sat)))
        gate("reconstruct_saturation_exact", sat_err == OBS_SAT_MAX_ABS_ERROR, sat_err)

        mass_reconstructed = np.asarray(
            a2e.local_mass(r2, sat_hetero, pressure, p_ref, hetero_pv),
            dtype=np.float64,
        )
        mass_err = float(np.max(np.abs(mass_reconstructed - parent_mass)))
        gate("reconstruct_mass_error", abs(mass_err - OBS_MASS_MAX_ABS_ERROR_KG) <= 1e-15, mass_err)

        # Reproduce the legacy exception semantically.
        legacy_exc = None
        try:
            r2._invert_incremental_sg_from_mass(parent_mass, pressure, p_ref, uniform_pv_scalar)
        except Exception as exc:
            legacy_exc = repr(exc)

        gate("legacy_uniform_exception_present", legacy_exc is not None, legacy_exc)
        m = re.search(r"capillary_cell_mass_capacity_exceeded:([0-9eE+\-.]+)", legacy_exc or "")
        gate("legacy_uniform_exception_parseable", m is not None, legacy_exc)
        legacy_excess = float(m.group(1))
        gate("legacy_uniform_exception_numeric_match", abs(legacy_excess - OBS_R29R1_EXCEPTION_EXCESS_KG) <= 1e-9, legacy_excess)

        # ------------------------------------------------------------------
        # Re-audit the intended R29-R2 repair boundary.
        # ------------------------------------------------------------------
        stage = "recovered_design_semantic_audit"

        adv_src = inspect.getsource(e37a.advance_component_mass_control_volumes)
        map_src = inspect.getsource(e37a.map_control_volume_increment_to_grid)
        inv_src = inspect.getsource(a2e.invert_local_mass)
        local_src = inspect.getsource(a2e.local_mass)

        gate("CV_transport_operator_unchanged", "cell_pore_volume_m3" not in inspect.signature(e37a.advance_component_mass_control_volumes).parameters)
        gate("CV_transport_global_closure_present", "component_mass_FV_global_closure" in adv_src)
        gate("subsegment_delta_formula_reusable", "sub_delta_mass" in map_src)
        gate("SG7D_flat_cell_deposition_reusable", "np.bincount" in map_src and "deposited_delta_mass" in map_src)
        gate("legacy_scalar_parent_dependency_identified", "float(cell_pore_volume_m3) * parent_rho * parent_sg" in map_src)
        gate("legacy_scalar_candidate_inversion_identified", "_invert_incremental_sg_from_mass" in map_src and "cell_pore_volume_m3" in map_src)
        gate("A2E_array_PV_inversion_present", "pore_volume_m3" in inspect.signature(a2e.invert_local_mass).parameters)
        gate("A2E_capacity_gate_present", "same_time_local_cell_mass_capacity" in inv_src)
        gate("A2E_array_local_mass_present", "pv * rho * sg" in local_src)

        # ------------------------------------------------------------------
        # Publish durable recovery artifacts under THIS child, never the lost original path.
        # ------------------------------------------------------------------
        stage = "authoritative_recovery_publication"

        classification = (
            "R6R29R2R1R1_AUTHORITATIVE_DRIVE_RECOVERS_LOST_R29R1R1_PASS_ARTIFACTS_"
            "BY_FROZEN_INPUT_RECONSTRUCTION_HETEROGENEOUS_PV_DESIGN_CLOSED_R29R3_NEXT"
        )

        recovered_r29r1r1 = {
            "recovery_milestone": M,
            "original_milestone_commit": R29R1R1_COMMIT,
            "original_runner_sha256": R29R1R1_RUNNER_SHA256,
            "original_runner_git_blob": R29R1R1_RUNNER_BLOB,
            "original_status": R29R1R1_STATUS,
            "original_classification": R29R1R1_CLASSIFICATION,
            "original_artifacts_present_on_authoritative_drive": False,
            "byte_identical_original_artifact_claim": False,
            "recovery_method": "reconstructed from frozen authoritative inputs and original source semantics",
            "observed_formal_PASS_values": {
                "source_R29R1_BLOCK_sha256": R29R1_BLOCK_SHA256,
                "source_R29_SCIENTIFIC_FAIL_sha256": R29_FAIL_SHA256,
                "R29R1_actual_exception_text": OBS_R29R1_EXCEPTION_TEXT,
                "R29R1_actual_exception_excess_kg": OBS_R29R1_EXCEPTION_EXCESS_KG,
                "R29_FAIL_excess_kg": OBS_R29_FAIL_EXCESS_KG,
                "uniform_PV_max_capacity_excess_kg": OBS_UNIFORM_MAX_EXCESS_KG,
                "uniform_PV_violating_cell_count": OBS_UNIFORM_VIOLATING_COUNT,
                "heterogeneous_PV_max_capacity_excess_kg": OBS_HETERO_MAX_EXCESS_KG,
                "heterogeneous_PV_capacity_tolerance_kg": OBS_HETERO_CAP_TOL_KG,
                "heterogeneous_PV_violating_cell_count": OBS_HETERO_VIOLATING_COUNT,
                "heterogeneous_inversion_saturation_max_abs_error": OBS_SAT_MAX_ABS_ERROR,
                "heterogeneous_inversion_cellwise_mass_max_abs_error_kg": OBS_MASS_MAX_ABS_ERROR_KG,
            },
            "reconstructed_values": {
                "legacy_exception_text": legacy_exc,
                "legacy_exception_excess_kg": legacy_excess,
                "uniform_PV_max_capacity_excess_kg": uniform_max_excess,
                "uniform_PV_violating_cell_count": uniform_violating,
                "heterogeneous_PV_max_capacity_excess_kg": hetero_max_excess,
                "heterogeneous_PV_capacity_tolerance_kg": hetero_cap_tol,
                "heterogeneous_PV_violating_cell_count": hetero_violating,
                "heterogeneous_inversion_saturation_max_abs_error": sat_err,
                "heterogeneous_inversion_cellwise_mass_max_abs_error_kg": mass_err,
            },
            "scientific_conclusion": {
                "accepted_parent_capacity_valid_under_AV4_authority": True,
                "uniform_E35_cartesian_PV_is_invalid_for_AV4": True,
                "heterogeneous_cartesian_PV_required": True,
            },
        }

        recovered_design = {
            "milestone": M,
            "status": PASS,
            "accepted_parent_state_sha256": R25R3_STATE_SHA256,
            "dt_days": DT_DAYS,
            "candidate_target_day": CANDIDATE_TARGET_DAY,
            "CV_transport_operator": "E37A.advance_component_mass_control_volumes",
            "CV_transport_operator_changed": False,
            "subsegment_delta_formula_changed": False,
            "SG7D_flat_cell_deposition_changed": False,
            "uniform_cartesian_PV_authorized": False,
            "heterogeneous_cartesian_PV": "paired_porosity * A2E.BULK_VOLUME_M3",
            "heterogeneous_porosity_state_sha256": A6E_STATE_SHA256,
            "accepted_parent_cartesian_mass_used_directly": True,
            "candidate_mass_identity": "M_grid_candidate = accepted_M_grid_parent + Delta_M_grid",
            "represented_candidate_identity": "M_represented_candidate = M_represented_parent + Delta_M_grid",
            "residual_candidate_identity": "M_residual_candidate = M_residual_parent exactly",
            "absolute_mapback_authorized": False,
            "candidate_capacity": "A2E.local_mass at S=0.80 with heterogeneous PV",
            "candidate_inversion": "A2E.invert_local_mass with heterogeneous PV",
            "automatic_dt_reduction_authorized": False,
            "support_growth_authorized": False,
            "residual_promotion_authorized": False,
            "physical_time_commit_authorized": False,
        }

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "original_R29R1R1_artifacts_found_on_authoritative_drive": False,
            "R29R1R1_recovery_completed": True,
            "R29R1R1_byte_identical_recovery_claim": False,
            "R29R1R1_original_commit": R29R1R1_COMMIT,
            "R29R1R1_original_runner_sha256": R29R1R1_RUNNER_SHA256,
            "R29R1R1_original_runner_git_blob": R29R1R1_RUNNER_BLOB,
            "reconstructed_uniform_PV_max_capacity_excess_kg": uniform_max_excess,
            "reconstructed_uniform_PV_violating_cell_count": uniform_violating,
            "reconstructed_heterogeneous_PV_max_capacity_excess_kg": hetero_max_excess,
            "reconstructed_heterogeneous_PV_violating_cell_count": hetero_violating,
            "reconstructed_saturation_max_abs_error": sat_err,
            "reconstructed_mass_max_abs_error_kg": mass_err,
            "accepted_parent_capacity_valid_under_AV4_authority": True,
            "heterogeneous_AV4_design_recovered": True,
            "R29R2_immutable_technical_block_preserved": True,
            "R29R2R1_publication_preserved": True,
            "transport_execution_performed": False,
            "state_mutation_executed": False,
            "physical_time_advance_executed": False,
            "P3_authorized": False,
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "P2_R6_R29_R3_authorized": True,
            "P2_R6_R29_R3_name": (
                "Controlled Post-Day375 Frozen-Flow Transport Candidate Execution — "
                "Heterogeneous Cartesian PV Repair — No Time Commit"
            ),
            "P2_R6_R29_R3_execution_authorized": True,
            "P2_R6_R29_R3_candidate_only": True,
            "P2_R6_R29_R3_must_bind_R29R2R1R1_recovery": True,
            "P2_R6_R29_R3_dt_days": DT_DAYS,
            "P2_R6_R29_R3_candidate_target_day": CANDIDATE_TARGET_DAY,
            "uniform_cartesian_PV_authorized": False,
            "heterogeneous_AV4_cartesian_PV_required": True,
            "CV_transport_operator_change_authorized": False,
            "subsegment_delta_formula_change_authorized": False,
            "absolute_mapback_authorized": False,
            "residual_sidecar_mutation_authorized": False,
            "automatic_dt_reduction_authorized": False,
            "support_growth_authorized": False,
            "physical_time_advance_authorized": False,
            "pressure_refresh_authorized": False,
            "P3_authorized": False,
        }

        out.mkdir(parents=True, exist_ok=False)
        (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out / f"{OUT_TOKEN}_Recovered_R29R1R1_Artifact_Record.json").write_bytes(jb(recovered_r29r1r1))
        (out / f"{OUT_TOKEN}_Recovered_HeterogeneousPV_Design_Contract.json").write_bytes(jb(recovered_design))
        (out / f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))
        (out / f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(rows))

        print("=" * 190)
        print(M, "PASS")
        print("Original R29-R1-R1 artifacts on real Drive : False")
        print("Authoritative recovery artifact published   : True")
        print("Byte-identical original artifact claim      : False")
        print("Uniform-PV max excess kg                    :", uniform_max_excess)
        print("Uniform-PV violating cells                  :", uniform_violating)
        print("Heterogeneous-PV max excess kg              :", hetero_max_excess)
        print("Heterogeneous violating cells               :", hetero_violating)
        print("Saturation / mass reconstruction error      :", sat_err, "/", mass_err)
        print("Heterogeneous-PV design recovered           : True")
        print("R29-R3 corrected execution authorized       : True")
        print("Transport / state / time / P3               : False / False / False / False")
        print("=" * 190)
        return 0

    except Exception as exc:
        block_dir.mkdir(parents=True, exist_ok=True)
        p = block_dir / f"{OUT_TOKEN}_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": BLOCK,
                "failed_stage": stage,
                "exception": repr(exc),
                "original_R29R1R1_artifacts_presumed_lost": True,
                "R29_FAIL_preserved": True,
                "R29R1_BLOCK_preserved": True,
                "R29R2_BLOCK_preserved": True,
                "transport_execution_executed": False,
                "state_mutation_executed": False,
                "physical_time_advance_executed": False,
                "P3_authorized": False,
                "automatic_rerun_authorized": False,
                "gates_completed": gates,
            }))
        print("=" * 190)
        print(M, "TECHNICAL / AUTHORITY BLOCK")
        print("Stage    :", stage)
        print("Exception:", repr(exc))
        print("NO TRANSPORT / STATE MUTATION / TIME ADVANCE.")
        print("=" * 190)
        return 2


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, default=Path("."))
    ap.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        selftest()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root))
