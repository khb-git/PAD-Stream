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
import time
from pathlib import Path
from typing import Any

import numpy as np

M = "POSTV16-AV4-PIVOT-P3-R1-R4-R2"
NAME = "Combined Zero-/Positive-Halo Ten-Step Recurrent Prefix Certification"
PASS = "AV4PIVOTP3R1R4R2_COMBINED_ZERO_POSITIVE_HALO_TEN_STEP_RECURRENT_PREFIX_CERTIFICATION_PASS_SHADOW_EXECUTION"
BLOCK = "AV4PIVOTP3R1R4R2_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "fd4cf4ed6292fa0a540677ca3a713c4a901ec727"

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

OUT_TOKEN = "POSTV16_AV4_PIVOT_P3_R1_R4_R2"
OUT_REL = BASE_AV4 / (OUT_TOKEN + "_Combined_ZeroPositiveHalo_TenStep_Recurrent_Prefix_Certification")
STAGE_REL = BASE_AV4 / (OUT_TOKEN + "_STAGING")
BLOCK_REL = BASE_AV4 / (OUT_TOKEN + "_BLOCKED")

SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
STEP_AUDIT = f"{OUT_TOKEN}_Step_Audit.csv"
FINAL_STATE = f"{OUT_TOKEN}_Shadow_Final_State.npz"
GATES = f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"

DAY_TO_S = 86400.0
MASS_TOL = 1.0e-6
SAT_TOL = 1.0e-10
REL_TOL = 1.0e-10
HIGHS_FEAS_TOL = 1.0e-10
HALO_OPT_TOL = 1.0e-6
DEFAULT_TIME_LIMIT = 90.0
PREFIX_STEPS = 10
MAX_CG_ITERATIONS = 6
COLUMN_BATCH_SIZE = 5000
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


def classify(all_steps: bool, fallback_count: int, max_step_wall: float) -> tuple[str, str, bool]:
    if all_steps and fallback_count == 0:
        return (
            "P3R1_COMBINED_ZERO_AND_POSITIVE_HALO_FAST_PATHS_RECURRENTLY_CERTIFIED_FOR_TEN_CONSECUTIVE_ATOMIC_STEPS_NO_GENERIC_STAGE2_FALLBACK_DAY370_REPAIRED_PILOT_AUTHORIZED",
            "Execute a repaired Day365-to-Day370 pilot with per-step progress and recurrent checkpoints using the certified zero-halo reduced path and positive-halo column-generation path; preserve the frozen generic XY1 fallback and keep the full Day365-to500 sweep and P4 locked.",
            True,
        )
    if all_steps:
        return (
            "P3R1_TEN_STEP_RECURRENT_PREFIX_CERTIFIED_BUT_GENERIC_STAGE2_FALLBACK_REQUIRED_DAY370_REPAIRED_PILOT_NOT_YET_AUTHORIZED",
            "Profile the generic-fallback prefix steps before extending the trajectory.",
            False,
        )
    return (
        "P3R1_COMBINED_FAST_PATH_TEN_STEP_RECURRENT_PREFIX_NOT_CERTIFIED_REPAIR_REQUIRES_ADDITIONAL_DIAGNOSIS",
        "Use the per-step audit to diagnose the first uncertified recurrent step; do not run the Day370 pilot or full P3-R1 sweep.",
        False,
    )


def selftest() -> None:
    c, _, ok = classify(True, 0, 12.0)
    assert "DAY370_REPAIRED_PILOT_AUTHORIZED" in c and ok
    c, _, ok = classify(False, 0, 0.0)
    assert "NOT_CERTIFIED" in c and not ok
    assert PREFIX_STEPS == 10
    assert PARENT == "fd4cf4ed6292fa0a540677ca3a713c4a901ec727"
    print("POSTV16 AV4 PIVOT P3-R1-R4-R2 structural self-test: PASS")


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
        print("POSTV16-AV4-PIVOT-P3-R1-R4-R2 — COMBINED ZERO-/POSITIVE-HALO TEN-STEP RECURRENT PREFIX CERTIFICATION", flush=True)
        print("SHADOW EXECUTION ONLY. TEN ATOMIC STEPS. NO AUTHORITATIVE P3-R1 STATE COMMIT. NO FLOW-DIAGNOSTIC REFRESH.", flush=True)
        print("FAST PATHS: DIRECT -> ZERO-HALO REDUCED STAGE2; POSITIVE-HALO -> FULL STAGE1 + COLUMN-GENERATED EXACT STAGE2.", flush=True)
        print("FROZEN GENERIC XY1 LEXICOGRAPHIC SOLVER IS RETAINED AS BOUNDED FALLBACK.", flush=True)
        print("=" * 220, flush=True)

        stage = "preexisting_state_firewall"
        gate("no_preexisting_PASS", not (out / SUMMARY).exists())
        gate("no_preexisting_BLOCK", not (blocked / f"{OUT_TOKEN}_Blocked_Report.json").exists())
        gate("no_preexisting_STAGING", not staging.exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH, gt(root, "branch", "--show-current"))
        gate("parent_is_R4R1_commit", gt(root, "rev-parse", "HEAD^") == PARENT, gt(root, "rev-parse", "HEAD^"))
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for fn, blob in [(P3R1, P3R1_BLOB), (R31, R31_BLOB), (R32, R32_BLOB), (R3, R3_BLOB), (R4R1, R4R1_BLOB)]:
            fp = root / fn
            gate(f"{Path(fn).stem}_present", fp.is_file(), str(fp))
            gate(f"{Path(fn).stem}_blob_exact", gt(root, "hash-object", str(fp)) == blob, gt(root, "hash-object", str(fp)))

        p3 = load_module(root / P3R1, "p3r1_r4r2_authority")

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

        stage = "partial_P3R1_evidence"
        state_path = drive / P3R1_STAGE_REL / P3R1_DAY365_STATE
        gate("P3R1_Day365_partial_state_exists", state_path.is_file(), str(state_path))
        gate("P3R1_Day365_partial_state_SHA_matches_R3",
             sha(state_path) == r3sum.get("P3R1_partial_Day365_state_sha256"),
             sha(state_path))

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
            (p3.SG7A, p3.SG7A_BLOB),
            (p3.SG7D, p3.SG7D_BLOB),
        ]:
            fp = root / fn
            gate(f"{Path(fn).stem}_present", fp.is_file(), str(fp))
            gate(f"{Path(fn).stem}_blob_exact", gt(root, "hash-object", str(fp)) == expected, gt(root, "hash-object", str(fp)))

        a2e = load_module(root / p3.A2E, "p3r1r4r2_a2e")
        r2src = load_module(root / p3.R2SRC, "p3r1r4r2_r2src")
        e37a = load_module(root / p3.E37A, "p3r1r4r2_e37a")
        sg7a = load_module(root / p3.SG7A, "p3r1r4r2_sg7a")
        sg7d = load_module(root / p3.SG7D, "p3r1r4r2_sg7d")

        with np.load(a2ep, allow_pickle=False) as z:
            frozen_pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
            tof_s = np.asarray(z["streamline_tof_s"], dtype=np.float64)
            weights_m3_s = np.asarray(z["streamline_weight_m3_s"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            tau_end_s = np.asarray(z["tau_end_s"], dtype=np.float64)
        with np.load(a6ep, allow_pickle=False) as z:
            phi = np.asarray(z["paired_porosity"], dtype=np.float64)
        with np.load(state_path, allow_pickle=False) as z:
            physical_day = float(np.asarray(z["physical_day"]).reshape(()))
            current_grid_mass = np.asarray(z["cartesian_component_mass_kg"], dtype=np.float64)
            current_rep = np.asarray(z["represented_cartesian_cell_mass_kg"], dtype=np.float64)
            current_residual = np.asarray(z["grid_residual_component_mass_kg"], dtype=np.float64)
            current_cv_mass = np.asarray(z["transport_CV_component_mass_kg"], dtype=np.float64)
            current_cv_sat = np.asarray(z["transport_CV_saturation"], dtype=np.float64)
            edge_cv = np.asarray(z["XY1_edge_cv"], dtype=np.int64)
            edge_cell = np.asarray(z["XY1_edge_cell"], dtype=np.int64)
            shell = np.asarray(z["XY1_edge_shell_cost"], dtype=np.int8)
            current_edge_mass = np.asarray(z["XY1_edge_assigned_mass_kg"], dtype=np.float64)

        gate("physical_day_365_exact", abs(physical_day - 365.0) <= 1.0e-12, physical_day)
        initial_total_mass = float(np.sum(current_grid_mass))

        hetero_pv = phi * float(a2e.BULK_VOLUME_M3)
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

        current_time = physical_day
        cumulative_injected = 0.0
        cumulative_produced = 0.0
        rows: list[dict[str, Any]] = []
        fallback_count = 0
        reduced_count = 0
        positive_halo_cg_count = 0
        direct_count = 0
        total_cg_iterations = 0
        maximum_selected_shell_edge_count = 0
        all_steps_certified = True

        for step in range(1, PREFIX_STEPS + 1):
            step_start = time.perf_counter()
            dt = nominal_dt
            mode = ""
            stage1_wall = 0.0
            stage2_wall = 0.0
            positive_halo_stage1_wall = 0.0
            column_generation_stage2_wall = 0.0
            column_generation_iterations = 0
            column_generation_selected_shell_edges = 0
            column_generation_min_omitted_reduced_cost = None
            fallback_wall = 0.0

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
                all_steps_certified = False
                rows.append({"step": step, "outcome": "CV_NEGATIVE"})
                break

            cv_capacity = np.asarray(
                e37a.cv_mass_from_saturation(
                    r2src,
                    np.full((p3.NSL, p3.NCV), p3.MAX_SAT, dtype=np.float64),
                    geometry["cv_pressure_mass_coeff"],
                ),
                dtype=np.float64,
            )
            if float(np.max(new_cv_mass - cv_capacity)) > cv_cap_tol:
                all_steps_certified = False
                rows.append({"step": step, "outcome": "CV_CAPACITY"})
                break

            new_cv_sat = np.asarray(
                e37a.invert_cv_mass_to_saturation(r2src, new_cv_mass, geometry["cv_pressure_mass_coeff"]),
                dtype=np.float64,
            )
            if float(np.min(new_cv_sat)) < p3.BACKGROUND - SAT_TOL or float(np.max(new_cv_sat)) > p3.MAX_SAT + SAT_TOL:
                all_steps_certified = False
                rows.append({"step": step, "outcome": "CV_SATURATION"})
                break

            injected = float(np.sum(theory_flux[:, 0]) * dt)
            produced = float(np.sum(theory_flux[:, -1]) * dt)
            cv_delta = float(np.sum(new_cv_mass) - np.sum(old_cv_mass))
            cv_source_sink = cv_delta - injected + produced
            if abs(cv_source_sink) > max(MASS_TOL, REL_TOL * max(abs(injected), 1.0)):
                all_steps_certified = False
                rows.append({"step": step, "outcome": "CV_SOURCE_SINK"})
                break

            old_sub_sat = old_cv_sat.reshape(-1)[geom_cv_id]
            new_sub_sat = new_cv_sat.reshape(-1)[geom_cv_id]
            old_sub_sg = np.clip(old_sub_sat - p3.BACKGROUND, 0.0, p3.MAX_SG)
            new_sub_sg = np.clip(new_sub_sat - p3.BACKGROUND, 0.0, p3.MAX_SG)
            rho_old = np.asarray(r2src.gas_density_from_state(old_sub_sat, pseg, p_ref), dtype=np.float64)
            rho_new = np.asarray(r2src.gas_density_from_state(new_sub_sat, pseg, p_ref), dtype=np.float64)
            sub_delta = sub_pv * (rho_new * new_sub_sg - rho_old * old_sub_sg)
            if abs(float(np.sum(sub_delta)) - cv_delta) > MASS_TOL:
                all_steps_certified = False
                rows.append({"step": step, "outcome": "SUBSEGMENT_CLOSURE"})
                break

            delta_grid = np.bincount(flat_cell, weights=sub_delta, minlength=p3.NCELL).reshape(p3.GRID)
            direct_target_rep = old_rep + delta_grid
            rep_capacity = cart_capacity - current_residual
            rep_capacity_flat = np.maximum(rep_capacity, 0.0).reshape(-1)
            if float(np.min(rep_capacity)) < -cart_cap_tol:
                all_steps_certified = False
                rows.append({"step": step, "outcome": "REP_CAPACITY_NEGATIVE"})
                break

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
                direct_count += 1
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
                        all_steps_certified = False
                        rows.append({
                            "step": step,
                            "outcome": "REDUCED_STAGE2_NOT_SUCCESS",
                            "solver_status": int(lp2.status),
                            "solver_message": str(lp2.message),
                            "stage1_zero_halo_certificate_wall_seconds": stage1_wall,
                            "reduced_stage2_wall_seconds": stage2_wall,
                        })
                        break

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
                    reduced_count += 1

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
                        all_steps_certified = False
                        rows.append({
                            "step": step,
                            "outcome": "POSITIVE_HALO_STAGE1_NOT_SUCCESS",
                            "solver_status": int(lp1.status),
                            "solver_message": str(lp1.message),
                            "zero_halo_certificate_wall_seconds": stage1_wall,
                            "positive_halo_stage1_wall_seconds": positive_halo_stage1_wall,
                        })
                        break

                    halo_opt = float(lp1.fun)
                    x1 = np.asarray(lp1.x, dtype=np.float64)
                    shell_mask_global = shell > 0
                    seed_shell_positions = np.where(
                        shell_mask_global & (x1 > POSITIVE_EDGE_TOL)
                    )[0]
                    selected_shell = set(int(x) for x in seed_shell_positions.tolist())

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

                    total_cg_iterations += column_generation_iterations
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
                        positive_halo_cg_count += 1
                        stage2_wall = column_generation_stage2_wall

                    else:
                        # Frozen full generic Stage2 is retained as bounded safety fallback.
                        fallback_count += 1
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
                            all_steps_certified = False
                            rows.append({
                                "step": step,
                                "outcome": "POSITIVE_HALO_CG_AND_GENERIC_STAGE2_NOT_SUCCESS",
                                "stage1_halo_optimum_kg": halo_opt,
                                "column_generation_iterations": column_generation_iterations,
                                "column_generation_selected_shell_edges": column_generation_selected_shell_edges,
                                "column_generation_min_omitted_reduced_cost": column_generation_min_omitted_reduced_cost,
                                "generic_solver_status": int(lp2f.status),
                                "generic_solver_message": str(lp2f.message),
                                "generic_fallback_wall_seconds": fallback_wall,
                            })
                            break

                        zf = np.asarray(lp2f.x, dtype=np.float64)
                        new_edge_mass = zf[:nedge]
                        new_rep = np.bincount(
                            edge_cell, weights=new_edge_mass, minlength=p3.NCELL
                        ).reshape(p3.GRID)
                        stage1_halo = halo_opt
                        stage2_l1 = float(np.sum(np.abs(
                            new_rep - direct_target_rep
                        )))
                        mode = "GENERIC_XY1_STAGE2_FALLBACK"

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

            # Shadow recurrent commit.
            current_grid_mass = candidate_grid
            current_rep = new_rep
            current_cv_mass = new_cv_mass
            current_cv_sat = new_cv_sat
            current_edge_mass = new_edge_mass
            current_time += dt
            cumulative_injected += injected
            cumulative_produced += produced

            step_wall = time.perf_counter() - step_start
            rows.append({
                "step": step,
                "outcome": "CERTIFIED",
                "parent_day": current_time - dt,
                "shadow_accepted_day": current_time,
                "dt_days": dt,
                "representation_mode": mode,
                "stage1_terminal_mass_kg": stage1_halo,
                "stage2_cell_L1_kg": stage2_l1,
                "exact_support_zero_halo_certificate_wall_seconds": stage1_wall,
                "positive_halo_full_stage1_wall_seconds": positive_halo_stage1_wall,
                "reduced_or_column_generated_stage2_wall_seconds": stage2_wall,
                "column_generation_stage2_wall_seconds": column_generation_stage2_wall,
                "column_generation_iterations": column_generation_iterations,
                "column_generation_selected_shell_edges": column_generation_selected_shell_edges,
                "column_generation_min_omitted_reduced_cost": column_generation_min_omitted_reduced_cost,
                "generic_fallback_wall_seconds": fallback_wall,
                "total_step_wall_seconds": step_wall,
                "cartesian_capacity_excess_kg": cap_excess,
                "cartesian_EOS_reconstruction_max_error_kg": recon_err,
                "global_source_sink_residual_kg": source_sink,
                "shadow_total_mass_kg": float(np.sum(candidate_grid)),
            })
            print(
                f"[PREFIX STEP {step:02d}/{PREFIX_STEPS}] t={current_time:.9f} d "
                f"mode={mode} zeroH={stage1_wall:.3f}s posH1={positive_halo_stage1_wall:.3f}s "
                f"stage2={stage2_wall:.3f}s cgIter={column_generation_iterations} "
                f"fallback={fallback_wall:.3f}s total={step_wall:.3f}s",
                flush=True,
            )

        certified_steps = sum(1 for r in rows if r.get("outcome") == "CERTIFIED")
        if certified_steps != PREFIX_STEPS:
            all_steps_certified = False

        final_total = float(np.sum(current_grid_mass))
        final_ledger_residual = final_total - (
            initial_total_mass + cumulative_injected - cumulative_produced
        )
        max_step_wall = max(
            [float(r.get("total_step_wall_seconds", 0.0)) for r in rows if r.get("outcome") == "CERTIFIED"] or [0.0]
        )

        classification, recommendation, day370_auth = classify(
            all_steps_certified, fallback_count, max_step_wall
        )

        stage = "publication"
        staging.mkdir(parents=True, exist_ok=False)
        (staging / STEP_AUDIT).write_bytes(csvb(rows))
        (staging / GATES).write_bytes(csvb(gates))
        (staging / FINAL_STATE).write_bytes(deterministic_npz_bytes({
            "shadow_only": np.asarray(True),
            "authoritative_state": np.asarray(False),
            "physical_day": np.asarray(current_time, dtype=np.float64),
            "cartesian_component_mass_kg": current_grid_mass,
            "represented_cartesian_cell_mass_kg": current_rep,
            "grid_residual_component_mass_kg": current_residual,
            "transport_CV_component_mass_kg": current_cv_mass,
            "transport_CV_saturation": current_cv_sat,
            "XY1_edge_cv": edge_cv,
            "XY1_edge_cell": edge_cell,
            "XY1_edge_shell_cost": shell,
            "XY1_edge_assigned_mass_kg": current_edge_mass,
        }))

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "repository_parent_R4R1_commit": PARENT,
            "R3_status_bound": R3_STATUS,
            "R4R1_status_bound": R4R1_STATUS,
            "P3R1_partial_Day365_state_sha256": sha(state_path),
            "authoritative_physics_state_mutated": False,
            "authoritative_physical_time_advanced": False,
            "shadow_prefix_executed": True,
            "shadow_prefix_start_day": physical_day,
            "shadow_prefix_final_day": current_time,
            "requested_prefix_steps": PREFIX_STEPS,
            "certified_prefix_steps": certified_steps,
            "nominal_CFL_dt_days": nominal_dt,
            "direct_step_count": direct_count,
            "zero_halo_reduced_fast_path_step_count": reduced_count,
            "positive_halo_column_generation_step_count": positive_halo_cg_count,
            "total_column_generation_iterations": total_cg_iterations,
            "maximum_selected_shell_edge_count": maximum_selected_shell_edge_count,
            "generic_XY1_fallback_step_count": fallback_count,
            "all_ten_steps_certified": all_steps_certified,
            "maximum_certified_step_wall_seconds": max_step_wall,
            "cumulative_injected_kg": cumulative_injected,
            "cumulative_produced_kg": cumulative_produced,
            "final_shadow_global_source_sink_residual_kg": final_ledger_residual,
            "recommended_next_action": recommendation,
            "CFL_change_authorized": False,
            "transport_law_change_authorized": False,
            "support_topology_change_authorized": False,
            "residual_sidecar_change_authorized": False,
            "lexicographic_objective_change_authorized": False,
            "Day365_to_Day370_repaired_pilot_authorized": bool(day370_auth),
            "P3_R1_full_rerun_authorized": False,
            "P4_authorized": False,
        }
        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "R32_recurrent_semantics_remain_authoritative": True,
            "P3_R0_remains_authoritative": True,
            "scientific_failure_declared": False,
            "authoritative_state_mutation_authorized": False,
            "physics_change_authorized": False,
            "CFL_change_authorized": False,
            "support_topology_change_authorized": False,
            "residual_sidecar_change_authorized": False,
            "lexicographic_objective_change_authorized": False,
            "zero_halo_certificate_may_replace_full_Stage1_optimization_when_feasible": True,
            "reduced_exact_support_Stage2_may_replace_generic_Stage2_when_zero_halo_certified": True,
            "positive_halo_column_generation_Stage2_may_replace_generic_Stage2_when_dual_pricing_closes": True,
            "positive_halo_column_generation_must_validate_selected_column_dual_pricing": True,
            "positive_halo_column_generation_must_price_all_omitted_shell_edges": True,
            "frozen_generic_XY1_lexicographic_fallback_must_be_preserved": True,
            "Day365_to_Day370_repaired_pilot_authorized": bool(day370_auth),
            "Day370_pilot_must_publish_per_step_progress": True,
            "Day370_pilot_must_publish_recurrent_checkpoints": True,
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
        print("Certified prefix steps                 :", certified_steps, "/", PREFIX_STEPS, flush=True)
        print("Shadow final day                       :", current_time, flush=True)
        print("Direct / zeroH / posH-CG / generic    :", direct_count, "/", reduced_count, "/", positive_halo_cg_count, "/", fallback_count, flush=True)
        print("Max certified step wall seconds        :", max_step_wall, flush=True)
        print("Final shadow ledger residual kg        :", final_ledger_residual, flush=True)
        print("Day365->Day370 repaired pilot authorized:", day370_auth, flush=True)
        print("Full P3-R1 rerun authorized            : False", flush=True)
        print("P4 authorized                          : False", flush=True)
        print("=" * 220, flush=True)
        return 0

    except Exception as exc:
        if staging.exists():
            shutil.rmtree(staging)
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
