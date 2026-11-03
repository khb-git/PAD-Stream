#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, importlib.util, io, json, subprocess, sys
from pathlib import Path
from typing import Any
import numpy as np

M = "POSTV16-AV4-PIVOT-P2-R6-R29-R3-R2-R1-R1-R1-R2-R1-R1-R1-R1-R1-R4"
NAME = "Independent All-CV/XY1 Candidate Acceptance + Time-Commit Readiness Audit"

PASS = (
    "AV4PIVOTP2R6R29R3R2R1R1R1R2R1R1R1R1R1R4_"
    "INDEPENDENT_ALL_CV_XY1_CANDIDATE_ACCEPTANCE_AND_TIME_COMMIT_READINESS_PASS_NO_TIME_MUTATION"
)
BLOCK = "AV4PIVOTP2R6R29R3R2R1R1R1R2R1R1R1R1R1R4_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "4428f03e26f1c59f4b9ffd9540f5c5108a8ddc9a"

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

# R3 controlled execution authority.
R3_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R1_R1_R3"
R3_REL = BASE / (R3_TOKEN + "_Controlled_AllCV_TheoryFlux_XY1_Candidate_Execution_NoTimeCommit")
R3_SUMMARY = "PAD_Stream_" + R3_TOKEN + "_Summary.json"
R3_DECISION = R3_TOKEN + "_Decision_Contract.json"
R3_MANIFEST = R3_TOKEN + "_Artifact_Manifest.csv"
R3_STATE = R3_TOKEN + "_Controlled_Candidate_State.npz"
R3_STATUS = (
    "AV4PIVOTP2R6R29R3R2R1R1R1R2R1R1R1R1R1R3_"
    "CONTROLLED_ALL_CV_EQUALITY_DOMAIN_THEORY_FLUX_XY1_CANDIDATE_EXECUTION_PASS_NO_TIME_COMMIT"
)
R3_CLASS = (
    "CONTROLLED_FROZEN_ALL_CV_EQUALITY_DOMAIN_THEORY_FLUX_XY1_"
    "CANDIDATE_EXECUTED_FULL_PROPAGATION_CLOSED_NO_TIME_COMMIT"
)
R3_STATE_SHA = "fa29ff25b8aa9ace60c6866acde599b5b387af203b08f5d528def6c68458155a"

R3_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R1_R1_R3_"
    "Controlled_AllCV_TheoryFlux_XY1_Candidate_Execution_NoTimeCommit.py"
)
R3_RUNNER_BLOB = "3dac9b3e6e8c2c1dc9581da0ff71085260759336"

# R2 design-freeze authority.
DESIGN_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R1_R1_R2"
DESIGN_REL = BASE / (DESIGN_TOKEN + "_AllCV_EqualityDomain_TheoryFlux_XY1_Repair_Design_Freeze")
DESIGN_MANIFEST = DESIGN_TOKEN + "_Artifact_Manifest.csv"
DESIGN_FROZEN = DESIGN_TOKEN + "_Frozen_Prospective_AllCV_TheoryFlux_XY1_Candidate.npz"
DESIGN_FROZEN_SHA = "cc27b5e8fb10551816d80f56f2a9d51f31cb2e51c39389985c163a1082f91a04"

# Accepted Day-375 parent.
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
    R3_RUNNER: R3_RUNNER_BLOB,
    R2SRC: R2SRC_BLOB,
    A2E: A2E_BLOB,
}

OUT_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R1_R1_R4"
OUT_REL = BASE / (OUT_TOKEN + "_Independent_Candidate_Acceptance_and_TimeCommit_Readiness_Audit")
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


def selftest():
    assert NCVT == 215600
    assert abs((PARENT_DAY + DT) - TARGET_DAY) < 1.0e-12
    print("POSTV16 AV4 PIVOT P2-R6-R29-R3-R2-R1-R1-R1-R2-R1-R1-R1-R1-R1-R4 structural self-test: PASS")


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

        stage = "R3_controlled_execution_authority"
        r3d = drive / R3_REL
        r3m = manifest(r3d, R3_MANIFEST)
        r3s = js(r3d / R3_SUMMARY)
        r3c = js(r3d / R3_DECISION)

        gate("R3_status_exact", r3s.get("status") == R3_STATUS, r3s.get("status"))
        gate("R3_class_exact", r3s.get("classification") == R3_CLASS, r3s.get("classification"))
        gate("R3_candidate_execution_complete", r3c.get("candidate_execution_complete") is True)
        gate("R3_candidate_not_yet_accepted", r3c.get("candidate_accepted") is False)
        gate("R3_R4_authorized",
             r3c.get("P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R1_R1_R4_authorized") is True)
        gate("R3_R4_acceptance_only",
             r3c.get("P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R1_R1_R4_acceptance_only") is True)
        gate("R3_no_time_advance", r3s.get("physical_time_advance_executed") is False)
        gate("R3_no_R30", r3s.get("R30_authorized") is False)
        gate("R3_state_manifested", R3_STATE in r3m)
        candidate_path = r3d / R3_STATE
        gate("R3_candidate_manifest_SHA_exact", r3m.get(R3_STATE) == R3_STATE_SHA, r3m.get(R3_STATE))
        gate("R3_candidate_file_SHA_exact", candidate_path.is_file() and sha(candidate_path) == R3_STATE_SHA)
        gate("R3_candidate_summary_SHA_exact", r3s.get("controlled_candidate_state_sha256") == R3_STATE_SHA)
        gate(
            "R3_candidate_decision_SHA_exact",
            r3c.get("P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R1_R1_R4_must_bind_candidate_SHA") == R3_STATE_SHA,
        )

        stage = "R2_design_freeze_authority"
        dd = drive / DESIGN_REL
        dm = manifest(dd, DESIGN_MANIFEST)
        frozen_path = dd / DESIGN_FROZEN
        gate("R2_frozen_candidate_manifested", DESIGN_FROZEN in dm)
        gate("R2_frozen_candidate_manifest_SHA_exact", dm.get(DESIGN_FROZEN) == DESIGN_FROZEN_SHA)
        gate("R2_frozen_candidate_file_SHA_exact", frozen_path.is_file() and sha(frozen_path) == DESIGN_FROZEN_SHA)

        stage = "load_candidate_and_design"
        with np.load(candidate_path, allow_pickle=False) as z:
            candidate_parent_day = float(np.asarray(z["candidate_parent_day"]).reshape(()))
            candidate_target_day = float(np.asarray(z["candidate_target_day"]).reshape(()))
            physical_time_committed = bool(np.asarray(z["physical_time_committed"]).reshape(()))
            candidate = np.asarray(z["cartesian_component_mass_kg"], dtype=np.float64)
            cell_rep = np.asarray(z["represented_cartesian_cell_mass_kg"], dtype=np.float64)
            residual = np.asarray(z["grid_residual_component_mass_kg"], dtype=np.float64)
            cv_mass = np.asarray(z["transport_CV_component_mass_kg"], dtype=np.float64)
            cv_sat = np.asarray(z["transport_CV_saturation"], dtype=np.float64)
            pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
            tof_s = np.asarray(z["streamline_tof_s"], dtype=np.float64)
            weights = np.asarray(z["streamline_weight_m3_s"], dtype=np.float64)
            edge_cv = np.asarray(z["XY1_edge_cv"], dtype=np.int64)
            edge_cell = np.asarray(z["XY1_edge_cell"], dtype=np.int64)
            shell = np.asarray(z["XY1_edge_shell_cost"], dtype=np.int8)
            edge_mass = np.asarray(z["XY1_edge_assigned_mass_kg"], dtype=np.float64)
            theory_flux = np.asarray(z["theory_face_mass_flux_kg_day"], dtype=np.float64)
            direct_target = np.asarray(z["direct_delta_represented_target_kg"], dtype=np.float64)
            zero_idx = np.asarray(z["zero_target_CV_indices"], dtype=np.int64)
            zero_assigned = np.asarray(z["zero_target_CV_assigned_mass_kg"], dtype=np.float64)

        with np.load(frozen_path, allow_pickle=False) as z:
            d_edge_cv = np.asarray(z["XY1_edge_cv"], dtype=np.int64)
            d_edge_cell = np.asarray(z["XY1_edge_cell"], dtype=np.int64)
            d_shell = np.asarray(z["XY1_edge_shell_cost"], dtype=np.int8)
            d_edge_mass = np.asarray(z["all_CV_edge_allocation_kg"], dtype=np.float64)
            d_cell_rep = np.asarray(z["all_CV_represented_candidate_kg"], dtype=np.float64)
            d_candidate = np.asarray(z["all_CV_candidate_grid_mass_kg"], dtype=np.float64)
            d_candidate_sat = np.asarray(z["all_CV_candidate_saturation"], dtype=np.float64)
            d_cv_mass = np.asarray(z["theory_transport_new_CV_mass_kg"], dtype=np.float64)
            d_cv_sat = np.asarray(z["theory_transport_new_CV_saturation"], dtype=np.float64)
            d_flux = np.asarray(z["theory_face_mass_flux_kg_day"], dtype=np.float64)
            d_target = np.asarray(z["direct_delta_represented_target_kg"], dtype=np.float64)
            d_residual = np.asarray(z["residual_parent_frozen_kg"], dtype=np.float64)
            d_zero_idx = np.asarray(z["zero_target_CV_indices"], dtype=np.int64)
            d_zero_assigned = np.asarray(z["zero_target_CV_assigned_mass_kg"], dtype=np.float64)
            d_stage1_halo = float(np.asarray(z["stage1_minimum_terminal_mass_kg"]).reshape(()))

        gate("candidate_parent_day_exact", abs(candidate_parent_day - PARENT_DAY) <= 1.0e-12, candidate_parent_day)
        gate("candidate_target_day_exact", abs(candidate_target_day - TARGET_DAY) <= 1.0e-12, candidate_target_day)
        gate("candidate_physical_time_not_committed", physical_time_committed is False)

        stage = "candidate_exact_design_binding"
        gate("candidate_edge_cv_exact_design", np.array_equal(edge_cv, d_edge_cv))
        gate("candidate_edge_cell_exact_design", np.array_equal(edge_cell, d_edge_cell))
        gate("candidate_shell_exact_design", np.array_equal(shell, d_shell))
        gate("candidate_edge_mass_exact_design", np.array_equal(edge_mass, d_edge_mass))
        gate("candidate_represented_exact_design", np.array_equal(cell_rep, d_cell_rep))
        gate("candidate_grid_mass_exact_design", np.array_equal(candidate, d_candidate))
        gate("candidate_CV_mass_exact_design", np.array_equal(cv_mass, d_cv_mass))
        gate("candidate_CV_saturation_exact_design", np.array_equal(cv_sat, d_cv_sat))
        gate("candidate_flux_exact_design", np.array_equal(theory_flux, d_flux))
        gate("candidate_direct_target_exact_design", np.array_equal(direct_target, d_target))
        gate("candidate_residual_exact_design", np.array_equal(residual, d_residual))
        gate("candidate_zero_index_exact_design", np.array_equal(zero_idx, d_zero_idx))
        gate("candidate_zero_assigned_exact_design", np.array_equal(zero_assigned, d_zero_assigned))

        stage = "accepted_parent_independent_binding"
        r25 = drive / R25_REL
        m25 = manifest(r25, R25_MANIFEST)
        parent_path = r25 / R25_STATE
        gate("R25_state_manifest_SHA_exact", m25.get(R25_STATE) == R25_SHA)
        gate("R25_state_file_SHA_exact", parent_path.is_file() and sha(parent_path) == R25_SHA)
        with np.load(parent_path, allow_pickle=False) as z:
            grid_parent = np.asarray(z["cartesian_component_mass_kg"], dtype=np.float64)
            represented_parent = np.asarray(z["represented_cartesian_cell_mass_kg"], dtype=np.float64)
            residual_parent = np.asarray(z["grid_residual_component_mass_kg"], dtype=np.float64)
            pressure_parent = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            p_ref_parent = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            xyz_parent = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
            tof_parent = np.asarray(z["streamline_tof_s"], dtype=np.float64)
            weights_parent = np.asarray(z["streamline_weight_m3_s"], dtype=np.float64)

        gate("parent_split_identity",
             float(np.max(np.abs(grid_parent - represented_parent - residual_parent))) <= MASS_TOL)
        gate("candidate_residual_bitwise_parent", np.array_equal(residual, residual_parent))
        gate("candidate_pressure_bitwise_parent", np.array_equal(pressure, pressure_parent))
        gate("candidate_reference_pressure_exact_parent", p_ref == p_ref_parent)
        gate("candidate_xyz_bitwise_parent", np.array_equal(xyz, xyz_parent))
        gate("candidate_TOF_bitwise_parent", np.array_equal(tof_s, tof_parent))
        gate("candidate_weight_bitwise_parent", np.array_equal(weights, weights_parent))

        stage = "independent_ledger_reconstruction"
        gate("edge_shapes_exact", edge_cv.shape == edge_cell.shape == shell.shape == edge_mass.shape)
        gate("edge_indices_valid",
             np.all((edge_cv >= 0) & (edge_cv < NCVT))
             and np.all((edge_cell >= 0) & (edge_cell < NCELL)))
        gate("edge_mass_nonnegative", float(np.min(edge_mass)) >= -MASS_TOL, float(np.min(edge_mass)))
        gate("shell_values_exact", np.all((shell == 0) | (shell == 1)))

        cv_from_edges = np.bincount(edge_cv, weights=edge_mass, minlength=NCVT).reshape(NSL, NCV)
        cv_err = float(np.max(np.abs(cv_from_edges - cv_mass)))
        cv_l1 = float(np.sum(np.abs(cv_from_edges - cv_mass)))
        gate("all_CV_mass_equalities", cv_err <= MASS_TOL, cv_err)

        zero_mask = cv_mass.reshape(-1) <= MASS_TOL
        zero_idx_rebuilt = np.where(zero_mask)[0]
        zero_assigned_rebuilt = cv_from_edges.reshape(-1)[zero_mask]
        zero_max = float(np.max(zero_assigned_rebuilt)) if len(zero_assigned_rebuilt) else 0.0
        zero_total = float(np.sum(zero_assigned_rebuilt))
        gate("zero_target_index_set_rebuilt_exact", np.array_equal(zero_idx, zero_idx_rebuilt))
        gate("zero_target_assignment_rebuilt_exact",
             float(np.max(np.abs(zero_assigned - zero_assigned_rebuilt))) <= 1.0e-12,
             float(np.max(np.abs(zero_assigned - zero_assigned_rebuilt))))
        gate("zero_target_max_below_gate", zero_max <= MASS_TOL, zero_max)
        gate("zero_target_total_negligible", zero_total <= 1.0e-5, zero_total)

        cell_from_edges = np.bincount(edge_cell, weights=edge_mass, minlength=NCELL).reshape(GRID)
        cell_err = float(np.max(np.abs(cell_from_edges - cell_rep)))
        gate("edge_to_cell_ledger_exact", cell_err <= 1.0e-10, cell_err)

        split_err = float(np.max(np.abs(candidate - cell_rep - residual)))
        gate("candidate_split_identity", split_err <= MASS_TOL, split_err)

        halo_mass = float(np.sum(edge_mass[shell > 0]))
        gate("stage1_halo_design_exact",
             abs(d_stage1_halo - float(r3s["stage1_minimum_terminal_mass_kg"])) <= 1.0e-9,
             [d_stage1_halo, r3s["stage1_minimum_terminal_mass_kg"]])
        gate("stage2_halo_R3_exact",
             abs(halo_mass - float(r3s["stage2_terminal_mass_kg"])) <= 1.0e-9,
             [halo_mass, r3s["stage2_terminal_mass_kg"]])
        gate("halo_optimum_preserved", abs(halo_mass - d_stage1_halo) <= 2.0e-6,
             [halo_mass, d_stage1_halo])

        stage = "independent_global_mass_validation"
        injected = float(np.sum(theory_flux[:, 0]) * DT)
        produced = float(np.sum(theory_flux[:, -1]) * DT)
        expected_total = float(np.sum(grid_parent)) + injected - produced
        source_sink = float(np.sum(candidate)) - expected_total
        global_tol = max(MASS_TOL, REL_TOL * max(abs(expected_total), 1.0))
        gate("candidate_source_sink_closure", abs(source_sink) <= global_tol, [source_sink, global_tol])

        stage = "independent_storage_and_EOS_validation"
        a6e = drive / A6E_REL / A6E_STATE
        gate("A6E_state_SHA_exact", a6e.is_file() and sha(a6e) == A6E_SHA)
        with np.load(a6e, allow_pickle=False) as z:
            phi = np.asarray(z["paired_porosity"], dtype=np.float64)

        r2 = load_module(root / R2SRC, "r4_r2")
        a2e = load_module(root / A2E, "r4_a2e")
        hetero_pv = phi * float(a2e.BULK_VOLUME_M3)
        full_sat = np.full(GRID, float(a2e.INJECTED), dtype=np.float64)
        cart_capacity = np.asarray(
            a2e.local_mass(r2, full_sat, pressure, p_ref, hetero_pv),
            dtype=np.float64,
        )
        cap_excess = float(np.max(candidate - cart_capacity))
        gate("candidate_heterogeneous_cartesian_capacity", cap_excess <= 1.0e-8, cap_excess)

        candidate_sg = np.asarray(
            a2e.invert_local_mass(r2, candidate, pressure, p_ref, hetero_pv),
            dtype=np.float64,
        )
        candidate_sat = float(a2e.BACKGROUND) + candidate_sg
        gate("candidate_saturation_exact_design",
             float(np.max(np.abs(candidate_sat - d_candidate_sat))) <= 1.0e-12,
             float(np.max(np.abs(candidate_sat - d_candidate_sat))))
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

        stage = "time_commit_readiness"
        gate("target_day_equals_parent_plus_dt", abs((PARENT_DAY + DT) - TARGET_DAY) <= 1.0e-12)
        gate("candidate_is_not_currently_time_committed", physical_time_committed is False)
        gate("R3_did_not_mutate_parent", r3s.get("state_mutation_of_accepted_parent_executed") is False)
        gate("R3_did_not_recompute_optimization", r3s.get("optimization_reexecuted") is False)
        gate("R3_did_not_recompute_transport", r3s.get("transport_recomputed") is False)
        gate("R3_residual_unchanged", r3s.get("residual_sidecar_unchanged") is True)
        gate("R3_pressure_unchanged", r3s.get("pressure_state_unchanged") is True)
        gate("R3_TOF_unchanged", r3s.get("TOF_geometry_unchanged") is True)

        stage = "acceptance_publication"
        out.mkdir(parents=True, exist_ok=False)

        classification = (
            "CONTROLLED_ALL_CV_XY1_CANDIDATE_INDEPENDENTLY_ACCEPTED_"
            "TIME_COMMIT_READY_NO_TIME_MUTATION"
        )

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "accepted_candidate_state_sha256": R3_STATE_SHA,
            "source_design_freeze_candidate_sha256": DESIGN_FROZEN_SHA,
            "accepted_parent_state_sha256": R25_SHA,
            "parent_physical_day": PARENT_DAY,
            "accepted_candidate_target_day": TARGET_DAY,
            "nominal_dt_days": DT,
            "candidate_accepted": True,
            "time_commit_ready": True,
            "physical_time_committed": False,
            "all_CV_count": NCVT,
            "zero_target_CV_count": int(np.count_nonzero(zero_mask)),
            "CV_equality_max_abs_error_kg": cv_err,
            "CV_equality_L1_error_kg": cv_l1,
            "zero_target_CV_total_assigned_mass_kg": zero_total,
            "zero_target_CV_max_assigned_mass_kg": zero_max,
            "stage1_minimum_terminal_mass_kg": d_stage1_halo,
            "stage2_terminal_mass_kg": halo_mass,
            "cartesian_max_capacity_excess_kg": cap_excess,
            "cartesian_source_sink_residual_kg": source_sink,
            "cartesian_mass_reconstruction_max_abs_error_kg": recon_err,
            "candidate_saturation_min": float(np.min(candidate_sat)),
            "candidate_saturation_max": float(np.max(candidate_sat)),
            "residual_sidecar_unchanged": True,
            "pressure_state_unchanged": True,
            "TOF_geometry_unchanged": True,
            "state_mutation_executed": False,
            "physical_time_advance_executed": False,
            "R30_authorized": True,
            "P3_authorized": False,
        }

        acceptance_contract = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "accepted_candidate_state_sha256": R3_STATE_SHA,
            "acceptance_scope": {
                "candidate_state_exact_design_binding": True,
                "all_CV_conservation": True,
                "zero_target_CV_conservation": True,
                "XY1_representation": True,
                "residual_sidecar_unchanged": True,
                "pressure_state_unchanged": True,
                "TOF_geometry_unchanged": True,
                "heterogeneous_cartesian_capacity": True,
                "EOS_reconstruction": True,
                "global_source_sink_closure": True,
            },
            "time_commit_readiness": {
                "parent_physical_day": PARENT_DAY,
                "target_day": TARGET_DAY,
                "nominal_dt_days": DT,
                "candidate_currently_time_committed": False,
                "ready_for_atomic_time_commit": True,
            },
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "candidate_accepted": True,
            "accepted_candidate_state_sha256": R3_STATE_SHA,
            "R30_authorized": True,
            "R30_name": "Atomic Physical-Time Commit of Accepted All-CV/XY1 Candidate",
            "R30_must_bind_accepted_candidate_SHA": R3_STATE_SHA,
            "R30_must_bind_parent_state_SHA": R25_SHA,
            "R30_target_day": TARGET_DAY,
            "R30_nominal_dt_days": DT,
            "R30_execution_authorized": True,
            "R30_must_not_recompute_transport": True,
            "R30_must_not_recompute_optimization": True,
            "R30_must_not_refresh_pressure": True,
            "R30_must_not_retrace_TOF": True,
            "R30_must_not_change_support": True,
            "R30_must_not_mutate_residual_sidecar": True,
            "physical_time_advance_executed": False,
            "P3_authorized": False,
        }

        (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out / f"{OUT_TOKEN}_Independent_Acceptance_Contract.json").write_bytes(jb(acceptance_contract))
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
        print("Accepted candidate SHA256              :", R3_STATE_SHA)
        print("Parent physical day                    :", PARENT_DAY)
        print("Accepted candidate target day          :", TARGET_DAY)
        print("CV equality max error kg               :", cv_err)
        print("Zero-target total assigned mass kg     :", zero_total)
        print("Cartesian source/sink residual kg      :", source_sink)
        print("Cartesian max capacity excess kg       :", cap_excess)
        print("Candidate saturation min/max           :", np.min(candidate_sat), "/", np.max(candidate_sat))
        print("Candidate accepted                     : True")
        print("Time-commit ready                      : True")
        print("Physical time committed                : False")
        print("R30 authorized                         : True")
        print("P3 authorized                          : False")
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
                "R3_candidate_preserved": True,
                "candidate_accepted": False,
                "state_mutation_executed": False,
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
