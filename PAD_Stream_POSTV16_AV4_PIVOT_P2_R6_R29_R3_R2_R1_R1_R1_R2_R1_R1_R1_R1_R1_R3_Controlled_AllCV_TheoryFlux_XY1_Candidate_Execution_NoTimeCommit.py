#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, importlib.util, io, json, subprocess, sys, zipfile
from pathlib import Path
from typing import Any
import numpy as np

M = "POSTV16-AV4-PIVOT-P2-R6-R29-R3-R2-R1-R1-R1-R2-R1-R1-R1-R1-R1-R3"
NAME = "Controlled All-CV Equality-Domain Theory-Flux + XY1 Candidate Execution — No Time Commit"

PASS = (
    "AV4PIVOTP2R6R29R3R2R1R1R1R2R1R1R1R1R1R3_"
    "CONTROLLED_ALL_CV_EQUALITY_DOMAIN_THEORY_FLUX_XY1_CANDIDATE_EXECUTION_PASS_NO_TIME_COMMIT"
)
BLOCK = "AV4PIVOTP2R6R29R3R2R1R1R1R2R1R1R1R1R1R3_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "f8a7636f5a4a819f65c43a433097f9ea2bc4122c"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"

GRID = (15, 50, 50)
NZ, NY, NX = GRID
NCELL = int(np.prod(GRID))
NSL = 1078
NCV = 200
NN = 201
NCVT = NSL * NCV

PARENT_DAY = 375.0
DT = 0.03721673128859954
TARGET_DAY = 375.0372167312886
BACKGROUND = 0.20
MAX_SAT = 0.80
MASS_TOL = 1.0e-6
SAT_TOL = 1.0e-10
REL_TOL = 1.0e-10

# Design-freeze authority.
DESIGN_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R1_R1_R2"
DESIGN_REL = BASE / (DESIGN_TOKEN + "_AllCV_EqualityDomain_TheoryFlux_XY1_Repair_Design_Freeze")
DESIGN_SUMMARY = "PAD_Stream_" + DESIGN_TOKEN + "_Summary.json"
DESIGN_PROTOCOL = DESIGN_TOKEN + "_Comprehensive_Repair_Protocol.json"
DESIGN_DECISION = DESIGN_TOKEN + "_Decision_Contract.json"
DESIGN_MANIFEST = DESIGN_TOKEN + "_Artifact_Manifest.csv"
DESIGN_FROZEN = DESIGN_TOKEN + "_Frozen_Prospective_AllCV_TheoryFlux_XY1_Candidate.npz"
DESIGN_STATUS = (
    "AV4PIVOTP2R6R29R3R2R1R1R1R2R1R1R1R1R1R2_"
    "ALL_CV_EQUALITY_DOMAIN_THEORY_FLUX_XY1_REPAIR_DESIGN_FREEZE_PASS_NO_STATE_MUTATION"
)
DESIGN_CLASS = (
    "ALL_CV_EQUALITY_DOMAIN_THEORY_FLUX_XY1_LEXICOGRAPHIC_MAPBACK_"
    "REPAIR_DESIGN_FROZEN_FULL_PROPAGATION_CLOSED"
)
FROZEN_SHA = "cc27b5e8fb10551816d80f56f2a9d51f31cb2e51c39389985c163a1082f91a04"

DESIGN_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R1_R1_R2_"
    "AllCV_EqualityDomain_TheoryFlux_XY1_Repair_Design_Freeze.py"
)
DESIGN_RUNNER_BLOB = "2491795d8a25c99713d291654e6d97f0be730833"

# Accepted Day-375 parent state.
R25_REL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R25_R3_"
    "Controlled_Day375_CapacityLimited_ExactSupport_SplitState_"
    "Reprojection_Execution_Stage2_PresolveOff"
)
R25_STATE = "POSTV16_AV4_PIVOT_P2_R6_R25_R3_CapacityLimited_SplitState_Day375.npz"
R25_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R25_R3_Artifact_Manifest.csv"
R25_SHA = "9893e2476bce1d46213cdd1304e60ad93b49ea285e084d06743a2ffab25f721f"

A6E_REL = BASE_AV3 / "POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
A6E_STATE = "POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
A6E_SHA = "f9e3a7bd8c6dcc43d522e0cb99a0cede2bd212fd570085b4faf82dc71af8f803"

R2SRC = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2SRC_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"

SOURCE_BLOBS = {
    DESIGN_RUNNER: DESIGN_RUNNER_BLOB,
    R2SRC: R2SRC_BLOB,
    A2E: A2E_BLOB,
}

OUT_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R1_R1_R3"
OUT_REL = BASE / (OUT_TOKEN + "_Controlled_AllCV_TheoryFlux_XY1_Candidate_Execution_NoTimeCommit")
BLOCK_REL = BASE / (OUT_TOKEN + "_BLOCKED")


class GateError(RuntimeError):
    pass


def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def js(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def csvr(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def csvb(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return s.getvalue().encode("utf-8")


def jb(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")


def manifest(directory: Path, filename: str) -> dict[str, str]:
    result = {}
    for row in csvr(directory / filename):
        p = directory / row["file"]
        if not p.is_file():
            raise GateError(f"manifest_missing:{p.name}")
        if sha(p) != row["sha256"]:
            raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes:{p.name}")
        result[p.name] = row["sha256"]
    return result


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load:{path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def deterministic_npz_bytes(arrays: dict[str, Any]) -> bytes:
    outer = io.BytesIO()
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


def allowed_xy1_keys(exact_cv: np.ndarray, exact_cell: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    exact_cv = np.asarray(exact_cv, dtype=np.int64)
    exact_cell = np.asarray(exact_cell, dtype=np.int64)
    exact_keys = np.unique(exact_cv * NCELL + exact_cell)

    k = exact_cell // (NY * NX)
    rem = exact_cell % (NY * NX)
    j = rem // NX
    i = rem % NX

    keys = [exact_cv * NCELL + exact_cell]
    for dj, di in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        jj = j + dj
        ii = i + di
        valid = (jj >= 0) & (jj < NY) & (ii >= 0) & (ii < NX)
        cell2 = (k[valid] * NY + jj[valid]) * NX + ii[valid]
        keys.append(exact_cv[valid] * NCELL + cell2)

    return exact_keys, np.unique(np.concatenate(keys))


def selftest():
    exact_cv = np.asarray([0], dtype=np.int64)
    exact_cell = np.asarray([(2 * NY + 10) * NX + 10], dtype=np.int64)
    exact_keys, allowed = allowed_xy1_keys(exact_cv, exact_cell)
    assert len(exact_keys) == 1
    assert len(allowed) == 5
    print("POSTV16 AV4 PIVOT P2-R6-R29-R3-R2-R1-R1-R1-R2-R1-R1-R1-R1-R1-R3 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    block_dir = drive / BLOCK_REL
    stage = "preflight"
    gates = []

    def gate(name: str, cond: Any, detail: Any = None):
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
        stage = "preexisting_state_firewall"
        gate("no_preexisting_PASS", not (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").exists())
        gate("no_preexisting_BLOCK", not (block_dir / f"{OUT_TOKEN}_Blocked_Report.json").exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_exact", gt(root, "rev-parse", "HEAD^") == PARENT, gt(root, "rev-parse", "HEAD^"))
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            gate(f"{Path(fn).stem}_present", p.is_file(), str(p))
            actual = gt(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_blob_exact", actual == expected, actual)

        stage = "design_freeze_authority"
        dd = drive / DESIGN_REL
        dm = manifest(dd, DESIGN_MANIFEST)
        ds = js(dd / DESIGN_SUMMARY)
        dp = js(dd / DESIGN_PROTOCOL)
        dc = js(dd / DESIGN_DECISION)

        gate("design_status_exact", ds.get("status") == DESIGN_STATUS, ds.get("status"))
        gate("design_class_exact", ds.get("classification") == DESIGN_CLASS, ds.get("classification"))
        gate("design_equality_domain_exact", ds.get("equality_domain") == "all_215600_transport_CVs")
        gate("design_all_CV_count_exact", int(ds.get("all_CV_count", -1)) == NCVT)
        gate("design_zero_target_count_exact", int(ds.get("zero_target_CV_count", -1)) == 14710)
        gate("design_flux_law_exact", ds.get("flux_law") == "q * u_D(xi) * f(S) * rho_ref")
        gate("design_support_topology_exact", ds.get("terminal_support_topology") == "XY1")
        gate("design_no_state_mutation", ds.get("state_mutation_executed") is False)
        gate("design_no_time_advance", ds.get("physical_time_advance_executed") is False)
        gate("design_R3_authorized",
             dc.get("P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R1_R1_R3_authorized") is True)
        gate("design_R3_execution_authorized",
             dc.get("P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R1_R1_R3_execution_authorized") is True)
        gate("design_R3_candidate_only",
             dc.get("P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R1_R1_R3_candidate_only") is True)
        gate("design_all_CV_required", dc.get("all_CV_equality_domain_required") is True)
        gate("design_zero_target_constraint_required",
             dc.get("zero_target_CV_edges_must_be_constrained_to_zero_total_mass") is True)
        gate("design_no_support_beyond_XY1", dc.get("support_beyond_XY1_authorized") is False)
        gate("design_no_residual_mutation", dc.get("residual_sidecar_mutation_authorized") is False)
        gate("design_no_dt_change", dc.get("nominal_dt_change_authorized") is False)
        gate("design_no_pressure_refresh", dc.get("pressure_refresh_authorized") is False)
        gate("design_no_TOF_retrace", dc.get("TOF_retrace_authorized") is False)
        gate("design_no_physical_time", dc.get("physical_time_advance_authorized") is False)
        gate("design_R30_false", dc.get("R30_authorized") is False)

        gate("frozen_candidate_manifested", DESIGN_FROZEN in dm)
        frozen_path = dd / DESIGN_FROZEN
        gate("frozen_candidate_SHA_manifest_exact", dm.get(DESIGN_FROZEN) == FROZEN_SHA, dm.get(DESIGN_FROZEN))
        gate("frozen_candidate_SHA_file_exact", frozen_path.is_file() and sha(frozen_path) == FROZEN_SHA)
        gate("frozen_candidate_SHA_summary_exact", ds.get("frozen_prospective_candidate_sha256") == FROZEN_SHA)
        gate("frozen_candidate_SHA_protocol_exact", dp.get("frozen_prospective_candidate_sha256") == FROZEN_SHA)
        gate(
            "frozen_candidate_SHA_decision_exact",
            dc.get("P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R1_R1_R3_must_bind_frozen_candidate_SHA") == FROZEN_SHA,
        )

        stage = "load_frozen_candidate"
        with np.load(frozen_path, allow_pickle=False) as z:
            edge_cv = np.asarray(z["XY1_edge_cv"], dtype=np.int64)
            edge_cell = np.asarray(z["XY1_edge_cell"], dtype=np.int64)
            shell = np.asarray(z["XY1_edge_shell_cost"], dtype=np.int8)
            x = np.asarray(z["all_CV_edge_allocation_kg"], dtype=np.float64)
            cell_rep = np.asarray(z["all_CV_represented_candidate_kg"], dtype=np.float64)
            candidate = np.asarray(z["all_CV_candidate_grid_mass_kg"], dtype=np.float64)
            candidate_sat_frozen = np.asarray(z["all_CV_candidate_saturation"], dtype=np.float64)
            cv_residual_frozen = np.asarray(z["all_CV_CV_equality_residual_kg"], dtype=np.float64)
            new_cv_mass = np.asarray(z["theory_transport_new_CV_mass_kg"], dtype=np.float64)
            new_cv_sat = np.asarray(z["theory_transport_new_CV_saturation"], dtype=np.float64)
            theory_flux = np.asarray(z["theory_face_mass_flux_kg_day"], dtype=np.float64)
            direct_target = np.asarray(z["direct_delta_represented_target_kg"], dtype=np.float64)
            residual_frozen = np.asarray(z["residual_parent_frozen_kg"], dtype=np.float64)
            zero_target_indices = np.asarray(z["zero_target_CV_indices"], dtype=np.int64)
            zero_target_assigned_frozen = np.asarray(z["zero_target_CV_assigned_mass_kg"], dtype=np.float64)
            stage1_halo_opt = float(np.asarray(z["stage1_minimum_terminal_mass_kg"]).reshape(()))

        gate("frozen_shapes_exact",
             cell_rep.shape == GRID
             and candidate.shape == GRID
             and candidate_sat_frozen.shape == GRID
             and residual_frozen.shape == GRID
             and direct_target.shape == GRID
             and new_cv_mass.shape == (NSL, NCV)
             and new_cv_sat.shape == (NSL, NCV)
             and theory_flux.shape == (NSL, NCV + 1)
             and edge_cv.shape == edge_cell.shape == shell.shape == x.shape)
        gate("frozen_arrays_finite",
             np.isfinite(x).all()
             and np.isfinite(cell_rep).all()
             and np.isfinite(candidate).all()
             and np.isfinite(new_cv_mass).all()
             and np.isfinite(theory_flux).all())

        stage = "accepted_parent_authority"
        r25 = drive / R25_REL
        m25 = manifest(r25, R25_MANIFEST)
        state_path = r25 / R25_STATE
        gate("R25_state_manifest_SHA_exact", m25.get(R25_STATE) == R25_SHA)
        gate("R25_state_file_SHA_exact", state_path.is_file() and sha(state_path) == R25_SHA)

        with np.load(state_path, allow_pickle=False) as z:
            grid_parent = np.asarray(z["cartesian_component_mass_kg"], dtype=np.float64)
            represented_parent = np.asarray(z["represented_cartesian_cell_mass_kg"], dtype=np.float64)
            residual_parent = np.asarray(z["grid_residual_component_mass_kg"], dtype=np.float64)
            old_cv_mass = np.asarray(z["transport_CV_component_mass_kg"], dtype=np.float64)
            xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
            tof_s = np.asarray(z["streamline_tof_s"], dtype=np.float64)
            weights_m3_s = np.asarray(z["streamline_weight_m3_s"], dtype=np.float64)
            pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            exact_cv = np.asarray(z["exact_support_edge_cv"], dtype=np.int64)
            exact_cell = np.asarray(z["exact_support_edge_cell"], dtype=np.int64)

        gate("parent_split_identity",
             float(np.max(np.abs(grid_parent - represented_parent - residual_parent))) <= MASS_TOL)
        gate("frozen_residual_bitwise_parent", np.array_equal(residual_frozen, residual_parent))
        gate("parent_transport_shape", old_cv_mass.shape == (NSL, NCV))
        gate("geometry_shapes",
             xyz.shape == (NSL, NN, 3)
             and tof_s.shape == (NSL, NN)
             and weights_m3_s.shape == (NSL,)
             and pressure.shape == GRID)

        stage = "edge_support_and_ledger_reconstruction"
        gate("edge_indices_in_range",
             np.all((edge_cv >= 0) & (edge_cv < NCVT))
             and np.all((edge_cell >= 0) & (edge_cell < NCELL)))
        gate("edge_shell_values_exact", np.all((shell == 0) | (shell == 1)))
        gate("edge_mass_nonnegative", float(np.min(x)) >= -MASS_TOL, float(np.min(x)))

        edge_keys = edge_cv * NCELL + edge_cell
        gate("edge_pairs_unique", len(np.unique(edge_keys)) == len(edge_keys), [len(np.unique(edge_keys)), len(edge_keys)])

        exact_keys, allowed_keys = allowed_xy1_keys(exact_cv, exact_cell)
        shell0_keys = edge_keys[shell == 0]
        shell1_keys = edge_keys[shell == 1]
        gate("shell0_edges_are_exact_support", np.all(np.isin(shell0_keys, exact_keys, assume_unique=False)))
        gate("all_edges_within_XY1", np.all(np.isin(edge_keys, allowed_keys, assume_unique=False)))
        gate("shell1_not_exact_support", not np.any(np.isin(shell1_keys, exact_keys, assume_unique=False)))

        cv_from_edges = np.bincount(edge_cv, weights=x, minlength=NCVT).reshape(NSL, NCV)
        cv_err = float(np.max(np.abs(cv_from_edges - new_cv_mass)))
        cv_l1 = float(np.sum(np.abs(cv_from_edges - new_cv_mass)))
        gate("all_CV_mass_equalities", cv_err <= MASS_TOL, cv_err)

        zero_mask = new_cv_mass.reshape(-1) <= MASS_TOL
        zero_indices_rebuilt = np.where(zero_mask)[0]
        gate("zero_target_index_set_exact", np.array_equal(zero_target_indices, zero_indices_rebuilt))
        zero_assigned = cv_from_edges.reshape(-1)[zero_mask]
        zero_max = float(np.max(zero_assigned)) if len(zero_assigned) else 0.0
        zero_total = float(np.sum(zero_assigned))
        gate("zero_target_max_below_gate", zero_max <= MASS_TOL, zero_max)
        gate("zero_target_total_matches_frozen",
             float(np.max(np.abs(zero_assigned - zero_target_assigned_frozen))) <= 1.0e-12,
             float(np.max(np.abs(zero_assigned - zero_target_assigned_frozen))))
        gate("zero_target_total_negligible", zero_total <= 1.0e-5, zero_total)

        cell_from_edges = np.bincount(edge_cell, weights=x, minlength=NCELL).reshape(GRID)
        cell_ledger_err = float(np.max(np.abs(cell_from_edges - cell_rep)))
        gate("cell_edge_ledger_exact", cell_ledger_err <= 1.0e-10, cell_ledger_err)

        split_err = float(np.max(np.abs(candidate - cell_rep - residual_parent)))
        gate("candidate_split_identity", split_err <= MASS_TOL, split_err)

        halo_mass = float(np.sum(x[shell > 0]))
        gate("stage1_halo_opt_matches_summary",
             abs(stage1_halo_opt - float(ds["stage1_minimum_terminal_mass_kg"])) <= 1.0e-9,
             [stage1_halo_opt, ds["stage1_minimum_terminal_mass_kg"]])
        gate("stage2_halo_mass_matches_summary",
             abs(halo_mass - float(ds["stage2_terminal_mass_kg"])) <= 1.0e-9,
             [halo_mass, ds["stage2_terminal_mass_kg"]])
        gate("halo_optimum_preserved",
             abs(halo_mass - stage1_halo_opt) <= 2.0e-6,
             [halo_mass, stage1_halo_opt])

        stage = "global_mass_and_storage_validation"
        injected = float(np.sum(theory_flux[:, 0]) * DT)
        produced = float(np.sum(theory_flux[:, -1]) * DT)
        expected_total = float(np.sum(grid_parent)) + injected - produced
        source_sink_residual = float(np.sum(candidate)) - expected_total
        global_tol = max(MASS_TOL, REL_TOL * max(abs(expected_total), 1.0))
        gate("candidate_source_sink_closure",
             abs(source_sink_residual) <= global_tol,
             [source_sink_residual, global_tol])

        a6e = drive / A6E_REL / A6E_STATE
        gate("A6E_state_SHA_exact", a6e.is_file() and sha(a6e) == A6E_SHA)
        with np.load(a6e, allow_pickle=False) as z:
            phi = np.asarray(z["paired_porosity"], dtype=np.float64)

        r2 = load_module(root / R2SRC, "r3_r2")
        a2e = load_module(root / A2E, "r3_a2e")
        hetero_pv = phi * float(a2e.BULK_VOLUME_M3)
        full_sat = np.full(GRID, float(a2e.INJECTED), dtype=np.float64)
        cart_capacity = np.asarray(
            a2e.local_mass(r2, full_sat, pressure, p_ref, hetero_pv),
            dtype=np.float64,
        )
        capacity_excess = float(np.max(candidate - cart_capacity))
        gate("candidate_heterogeneous_cartesian_capacity", capacity_excess <= 1.0e-8, capacity_excess)

        candidate_sg = np.asarray(
            a2e.invert_local_mass(r2, candidate, pressure, p_ref, hetero_pv),
            dtype=np.float64,
        )
        candidate_sat = float(a2e.BACKGROUND) + candidate_sg
        sat_match_err = float(np.max(np.abs(candidate_sat - candidate_sat_frozen)))
        gate("candidate_saturation_matches_frozen", sat_match_err <= 1.0e-12, sat_match_err)
        gate("candidate_saturation_bounds",
             float(np.min(candidate_sat)) >= BACKGROUND - SAT_TOL
             and float(np.max(candidate_sat)) <= MAX_SAT + SAT_TOL,
             [float(np.min(candidate_sat)), float(np.max(candidate_sat))])

        reconstructed = np.asarray(
            a2e.local_mass(r2, candidate_sat, pressure, p_ref, hetero_pv),
            dtype=np.float64,
        )
        recon_err = float(np.max(np.abs(reconstructed - candidate)))
        gate("candidate_EOS_reconstruction", recon_err <= 1.0e-8, recon_err)

        cv_residual_rebuilt = cv_from_edges - new_cv_mass
        gate("frozen_CV_residual_matches_rebuilt",
             float(np.max(np.abs(cv_residual_rebuilt - cv_residual_frozen))) <= 1.0e-12,
             float(np.max(np.abs(cv_residual_rebuilt - cv_residual_frozen))))

        stage = "controlled_candidate_publication"
        out.mkdir(parents=True, exist_ok=False)

        state_arrays = {
            "candidate_parent_day": np.asarray(PARENT_DAY, dtype=np.float64),
            "candidate_target_day": np.asarray(TARGET_DAY, dtype=np.float64),
            "physical_time_committed": np.asarray(False),
            "cartesian_component_mass_kg": candidate,
            "represented_cartesian_cell_mass_kg": cell_rep,
            "grid_residual_component_mass_kg": residual_parent,
            "transport_CV_component_mass_kg": new_cv_mass,
            "transport_CV_saturation": new_cv_sat,
            "refreshed_pressure_psi": pressure,
            "reference_gas_pressure_pa": np.asarray(p_ref, dtype=np.float64),
            "streamline_xyz_m": xyz,
            "streamline_tof_s": tof_s,
            "streamline_weight_m3_s": weights_m3_s,
            "XY1_edge_cv": edge_cv,
            "XY1_edge_cell": edge_cell,
            "XY1_edge_shell_cost": shell,
            "XY1_edge_assigned_mass_kg": x,
            "theory_face_mass_flux_kg_day": theory_flux,
            "direct_delta_represented_target_kg": direct_target,
            "zero_target_CV_indices": zero_target_indices,
            "zero_target_CV_assigned_mass_kg": zero_assigned,
        }
        candidate_name = f"{OUT_TOKEN}_Controlled_Candidate_State.npz"
        (out / candidate_name).write_bytes(deterministic_npz_bytes(state_arrays))
        candidate_sha = sha(out / candidate_name)

        classification = (
            "CONTROLLED_FROZEN_ALL_CV_EQUALITY_DOMAIN_THEORY_FLUX_XY1_"
            "CANDIDATE_EXECUTED_FULL_PROPAGATION_CLOSED_NO_TIME_COMMIT"
        )

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "source_design_freeze_candidate_sha256": FROZEN_SHA,
            "controlled_candidate_state_sha256": candidate_sha,
            "parent_accepted_state_sha256": R25_SHA,
            "parent_physical_day": PARENT_DAY,
            "candidate_target_day": TARGET_DAY,
            "nominal_dt_days": DT,
            "physical_time_committed": False,
            "flux_law": "q * u_D(xi) * f(S) * rho_ref",
            "equality_domain": "all_215600_transport_CVs",
            "terminal_support_topology": "XY1",
            "all_CV_count": NCVT,
            "zero_target_CV_count": int(np.count_nonzero(zero_mask)),
            "CV_equality_max_abs_error_kg": cv_err,
            "CV_equality_L1_error_kg": cv_l1,
            "zero_target_CV_total_assigned_mass_kg": zero_total,
            "zero_target_CV_max_assigned_mass_kg": zero_max,
            "stage1_minimum_terminal_mass_kg": stage1_halo_opt,
            "stage2_terminal_mass_kg": halo_mass,
            "cartesian_max_capacity_excess_kg": capacity_excess,
            "cartesian_source_sink_residual_kg": source_sink_residual,
            "cartesian_mass_reconstruction_max_abs_error_kg": recon_err,
            "candidate_saturation_min": float(np.min(candidate_sat)),
            "candidate_saturation_max": float(np.max(candidate_sat)),
            "residual_sidecar_unchanged": True,
            "pressure_state_unchanged": True,
            "TOF_geometry_unchanged": True,
            "optimization_reexecuted": False,
            "transport_recomputed": False,
            "state_mutation_of_accepted_parent_executed": False,
            "support_growth_accepted_state_executed": False,
            "physical_time_advance_executed": False,
            "R30_authorized": False,
            "P3_authorized": False,
        }

        execution_contract = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "execution_semantics": {
                "source": "exact frozen R2 prospective candidate",
                "source_frozen_candidate_sha256": FROZEN_SHA,
                "optimization_reexecuted": False,
                "transport_recomputed": False,
                "candidate_state_published": True,
                "accepted_parent_immutable": True,
                "physical_time_committed": False,
            },
            "frozen_science": {
                "transport_flux_law": "q * u_D(xi) * f(S) * rho_ref",
                "CV_equality_domain": "all 215600 CVs",
                "zero_target_CV_zero_RHS_required": True,
                "terminal_support": "XY1",
                "support_beyond_XY1": False,
                "residual_sidecar_mutation": False,
                "pressure_refresh": False,
                "TOF_retrace": False,
                "nominal_dt_change": False,
            },
            "controlled_candidate_state_sha256": candidate_sha,
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R1_R1_R4_authorized": True,
            "P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R1_R1_R4_name": (
                "Independent All-CV/XY1 Candidate Acceptance + Time-Commit Readiness Audit"
            ),
            "P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R1_R1_R4_acceptance_only": True,
            "P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R1_R1_R4_must_bind_candidate_SHA": candidate_sha,
            "candidate_execution_complete": True,
            "candidate_accepted": False,
            "physical_time_advance_authorized": False,
            "accepted_parent_mutation_authorized": False,
            "pressure_refresh_authorized": False,
            "TOF_retrace_authorized": False,
            "support_beyond_XY1_authorized": False,
            "residual_sidecar_mutation_authorized": False,
            "nominal_dt_change_authorized": False,
            "R30_authorized": False,
            "P3_authorized": False,
        }

        (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out / f"{OUT_TOKEN}_Controlled_Execution_Contract.json").write_bytes(jb(execution_contract))
        (out / f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))
        (out / f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(rows))

        print("=" * 200)
        print(M, "PASS")
        print("Classification                         :", classification)
        print("Source frozen candidate SHA256         :", FROZEN_SHA)
        print("Controlled candidate state SHA256      :", candidate_sha)
        print("Parent physical day                    :", PARENT_DAY)
        print("Candidate target day                   :", TARGET_DAY)
        print("Physical time committed                : False")
        print("CV equality max error kg               :", cv_err)
        print("Zero-target total assigned mass kg     :", zero_total)
        print("Stage2 terminal mass kg                :", halo_mass)
        print("Cartesian source/sink residual kg      :", source_sink_residual)
        print("Cartesian max capacity excess kg       :", capacity_excess)
        print("Candidate saturation min/max           :", np.min(candidate_sat), "/", np.max(candidate_sat))
        print("Independent R4 acceptance authorized   : True")
        print("R30 / P3                               : False / False")
        print("=" * 200)
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
                "design_freeze_preserved": True,
                "accepted_parent_preserved": True,
                "state_mutation_of_accepted_parent_executed": False,
                "physical_time_advance_executed": False,
                "R30_authorized": False,
                "P3_authorized": False,
                "gates_completed": gates,
            }))
        print(M, "TECHNICAL / AUTHORITY BLOCK")
        print("Stage:", stage)
        print("Exception:", repr(exc))
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
