#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R4-R3"
STATUS_PASS = (
    "AV4F4R3R3R3R3R3O3R6R4R3_CONTROLLED_SINGLE_CUT_PROJECTED_DIRECTION_"
    "ONE_STEP_FEASIBILITY_TEST_PASS_PROSPECTIVE_COMPUTATIONAL_CANDIDATE_ONLY_"
    "NO_FIVE_STAGE_ASSIGNMENT_NO_SUPPORT_EXPANSION_NO_TIME_ADVANCE"
)
STATUS_FAIL = (
    "AV4F4R3R3R3R3R3O3R6R4R3_CONTROLLED_SINGLE_CUT_PROJECTED_DIRECTION_"
    "ONE_STEP_FEASIBILITY_TEST_SCIENTIFIC_FAIL_NO_AUTOMATIC_RERUN_"
    "NO_SUPPORT_EXPANSION_NO_TIME_ADVANCE"
)
STATUS_BLOCK = "AV4F4R3R3R3R3R3O3R6R4R3_TECHNICAL_OR_AUTHORITY_BLOCK"

PARENT_R2_COMMIT = "9ef64cf1b85618a4949aae4442964b105789b8c8"

R2 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R2_"
    "Projected_Tangent_Constrained_Update_Semantics_Design_Freeze.py"
)
R2_BLOB = "687a35265bf0fe72a2110e2f91dab78cac5805b8"
R1R1 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1R1_"
    "CV60424_ActiveCut_Boundary_Semantics_Repair_and_Certification.py"
)
R1R1_BLOB = "e0da9d713db9cb40c0883ed17c54736f532b9f5c"
R4 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_"
    "Controlled_Adaptive_Feasibility_Preserving_Stabilized_Coupled_Execution.py"
)
R4_BLOB = "c41cd5c78e7cc2d91e1920e538f1793037961a31"
R3DESIGN = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R3_"
    "Adaptive_Feasibility_Preserving_Stabilization_Semantics_Design_Freeze.py"
)
R3DESIGN_BLOB = "c118972a991e4ae0ce7200a9f880a73407450b8b"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

OUT = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3_"
    "Controlled_SingleCut_Projected_Direction_OneStep_Feasibility_Test"
)
RECOVERY = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3_Recovery_Checkpoints"
FAIL = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3_SCIENTIFIC_FAIL"
BLOCK = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3_BLOCKED"

SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3_Summary.json"
PROJECTION_STATE = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3_Projection_State.npz"
PROBE_CSV = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3_Cut_Sensitivity_Probes.csv"
LINE_CSV = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3_Projected_Line_Search.csv"
DECISION = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3_Decision_Contract.json"
GATES = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3_Final_Gate_Matrix.csv"
MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3_Artifact_Manifest.csv"

GRID = (15, 50, 50)
NCELL = 37500
NCVTOTAL = 215600
EXPECTED_E2 = 3091073
INJECTED = 0.80
BACKGROUND = 0.20

LINE_DEN = 1024
MIN_ALPHA_INDEX = 1
FEAS_UNSERVED_TOL = 1.0e-6
FEAS_CV_LINF_TOL = 1.0e-6
FEAS_CAP_EXCESS_TOL = 1.0e-6


class GateError(RuntimeError):
    pass


class ScientificFail(RuntimeError):
    def __init__(self, gate: str, detail: Any):
        super().__init__(gate)
        self.gate = gate
        self.detail = detail


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError("cannot_load_module:" + str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def git_text(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True, text=True, capture_output=True
    ).stdout.strip()


def git_blob(path: Path, root: Path) -> str:
    return git_text(root, "hash-object", str(path))


def sha_array(a: np.ndarray) -> str:
    aa = np.ascontiguousarray(np.asarray(a))
    h = hashlib.sha256()
    h.update(str(aa.dtype).encode("ascii"))
    h.update(b"|")
    h.update(repr(tuple(aa.shape)).encode("ascii"))
    h.update(b"|")
    h.update(memoryview(aa).cast("B"))
    return h.hexdigest()


def checkpoint_manifest_valid(r3, d: Path, manifest: str, expected: set[str]) -> bool:
    if not d.is_dir() or not (d / manifest).is_file():
        return False
    try:
        return set(r3.verify_manifest(d, manifest)) == expected
    except Exception:
        return False


def probe_names(local_index: int, flat_cell: int) -> tuple[str, str]:
    stem = (
        "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3_"
        f"Probe_{local_index:02d}_Cell_{flat_cell:05d}"
    )
    return stem + ".json", stem + "_Manifest.csv"


def line_names(alpha_index: int) -> tuple[str, str, str]:
    stem = (
        "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3_"
        f"Alpha_{alpha_index:04d}_of_{LINE_DEN}"
    )
    return stem + "_State.npz", stem + "_Result.json", stem + "_Manifest.csv"


def self_test() -> None:
    g = np.asarray([2.0, -1.0, 3.0], dtype=np.float64)
    a_raw = 5.0
    q = -(a_raw / float(np.dot(g, g))) * g
    assert abs(a_raw + float(np.dot(g, q))) <= 1.0e-12
    assert LINE_DEN == 1024
    assert len(PARENT_R2_COMMIT) == 40
    print(
        "POSTV16 O3-R6-R4-R3 projected one-step feasibility test structural self-test: PASS"
    )


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT
    recovery = drive / RECOVERY
    failed = drive / FAIL
    blocked = drive / BLOCK

    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"
    pressure_probe_execution_performed = False
    feasibility_lp_execution_performed = False

    def gate(name: str, cond: bool, detail: Any = None):
        gates[name] = {"status": "PASS" if cond else "FAIL", "detail": detail}
        if not cond:
            raise GateError(f"{name}: {detail!r}")
        print(f"[PASS] {name}" + (f" -- {detail}" if detail is not None else ""))

    def sci_gate(name: str, cond: bool, detail: Any = None):
        gates[name] = {"status": "PASS" if cond else "FAIL", "detail": detail}
        if not cond:
            raise ScientificFail(name, detail)
        print(f"[PASS] {name}" + (f" -- {detail}" if detail is not None else ""))

    if (out / MANIFEST).is_file():
        print("[PASS] existing immutable O3-R6-R4-R3 PASS detected; no rerun")
        return 0
    fail_report = failed / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3_Scientific_Fail_Report.json"
    if fail_report.is_file():
        print("[FAIL] existing immutable O3-R6-R4-R3 scientific FAIL detected; automatic rerun prohibited")
        return 3
    block_report = blocked / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3_Blocked_Report.json"
    if block_report.is_file():
        print("[BLOCK] existing immutable O3-R6-R4-R3 technical/authority block detected")
        return 2

    print("=" * 214)
    print(MILESTONE + " -- CONTROLLED SINGLE-CUT PROJECTED-DIRECTION ONE-STEP FEASIBILITY TEST")
    print("=" * 214)
    print("ONE PROSPECTIVE COMPUTATIONAL TEST FROM THE IMMUTABLE R4 ITERATION-1 BASE/MAP PAIR.")
    print("24 LOCAL PRESSURE/CAPACITY SENSITIVITY PROBES + EXACT PROJECTED FROZEN-E2 FEASIBILITY TESTS.")
    print("NO FIVE-STAGE ASSIGNMENT. NO NONLINEAR STATE ADVANCE. NO SUPPORT EXPANSION. NO TIME ADVANCE.")
    print()

    try:
        # ----------------------------------------------------------------------------------
        # Repository and source authority.
        # ----------------------------------------------------------------------------------
        stage = "repository_authority"
        parent = git_text(root, "rev-parse", "HEAD^")
        dirty = git_text(root, "status", "--porcelain")
        gate("repository_parent_is_R2_commit", parent == PARENT_R2_COMMIT, parent)
        gate("repository_clean", dirty == "", repr(dirty))

        for fn, expected in {
            R2: R2_BLOB,
            R1R1: R1R1_BLOB,
            R4: R4_BLOB,
            R3DESIGN: R3DESIGN_BLOB,
        }.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        r2 = load_module(root / R2, "postv16_o3r6r4r3_r2")
        r4 = load_module(root / R4, "postv16_o3r6r4r3_r4")
        r3 = load_module(root / R3DESIGN, "postv16_o3r6r4r3_r3")
        o3r4 = load_module(root / r4.O3R4, "postv16_o3r6r4r3_o3r4")
        o3r6 = load_module(root / r4.O3R6, "postv16_o3r6r4r3_o3r6")
        a2e = load_module(root / r4.A2E, "postv16_o3r6r4r3_a2e")
        r2phys = load_module(root / r4.R2PHYS, "postv16_o3r6r4r3_r2phys")
        sg2 = load_module(root / r4.SG2, "postv16_o3r6r4r3_sg2")
        sg3 = load_module(root / r4.SG3, "postv16_o3r6r4r3_sg3")
        r3r2r1 = load_module(root / r4.R3R2R1, "postv16_o3r6r4r3_r3r2r1")

        for fn in [
            r4.O3R4, r4.O3R6, r4.A2E, r4.R2PHYS, r4.SG2,
            r4.SG3, r4.R3R2R1, r4.O2, r4.PERM
        ]:
            expected = r4.SOURCE_BLOBS[fn]
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        import highspy
        from scipy.sparse import coo_matrix
        gate(
            "highspy_version_exact_1_15_1",
            highspy.Highs().version() == "1.15.1",
            highspy.Highs().version(),
        )

        # ----------------------------------------------------------------------------------
        # Bind R2 frozen design contract.
        # ----------------------------------------------------------------------------------
        stage = "R2_design_binding"
        r2d = drive / r2.OUT
        gate("R2_output_present", r2d.is_dir(), str(r2d))
        r2_manifest = r3.verify_manifest(r2d, r2.MANIFEST)
        expected_r2_files = {
            r2.SUMMARY, r2.OPERATOR, r2.PROBES, r2.LINE,
            r2.CONVERGENCE, r2.CHECKPOINT, r2.DECISION, r2.GATES,
        }
        gate("R2_manifest_payload_exact", set(r2_manifest) == expected_r2_files, sorted(r2_manifest))

        s2 = r3.load_json(r2d / r2.SUMMARY)
        op2 = r3.load_json(r2d / r2.OPERATOR)
        pr2 = r3.load_json(r2d / r2.PROBES)
        ls2 = r3.load_json(r2d / r2.LINE)
        d2 = r3.load_json(r2d / r2.DECISION)

        gate(
            "R2_design_PASS_exact",
            s2.get("status") == r2.STATUS_PASS
            and s2.get("design_only") is True
            and s2.get("operator_id") == "PAD_STREAM_SINGLE_CUT_LOCAL_SECANT_TANGENT_PROJECTION_V1"
            and int(s2.get("certified_cut_CV_count", -1)) == 67
            and int(s2.get("certified_cut_cell_count", -1)) == 24
            and int(s2.get("local_sensitivity_probe_count", -1)) == 24
            and s2.get("prospective_test_uses_existing_R4_physical_map") is True
            and s2.get("prospective_test_five_stage_assignment_required") is False
            and s2.get("projected_execution_performed") is False
            and s2.get("support_domain_changed") is False
            and s2.get("physical_time_advanced") is False,
        )
        gate(
            "R2_authorizes_R3_one_step_only",
            d2.get("O3R6R4R3_one_step_projected_test_authorized") is True
            and d2.get("O3R6R4R3_full_fixed_point_execution_authorized") is False
            and d2.get("O3R6R4R3_five_stage_assignment_authorized") is False
            and d2.get("sub_1_over_1024_projected_step_authorized") is False
            and d2.get("support_expansion_authorized") is False
            and d2.get("O3R7_authorized") is False
            and d2.get("F5_dataset_generation_authorized") is False,
        )

        cut_cv_ids = np.asarray(op2["cut_definition"]["CV_ids"], dtype=np.int64)
        cut_cell_ids = np.asarray(op2["cut_definition"]["cell_ids"], dtype=np.int64)
        cut_demand = float(op2["cut_definition"]["demand_kg"])
        a_raw = float(op2["raw_cut_secant_slope"]["value_kg_per_full_raw_step"])
        hprobe = float(pr2["probe_size_saturation"])

        gate(
            "R2_cut_contract_exact",
            cut_cv_ids.size == 67
            and cut_cell_ids.size == 24
            and int(60424) in cut_cv_ids.tolist()
            and abs(a_raw - 53.3337138146162) <= 1.0e-10
            and abs(hprobe - 1.0e-5) <= 1.0e-15,
            {"cut_CVs": int(cut_cv_ids.size), "cut_cells": int(cut_cell_ids.size), "a_raw": a_raw},
        )

        # ----------------------------------------------------------------------------------
        # Bind immutable O2/A2E state and R4 base/map checkpoints.
        # ----------------------------------------------------------------------------------
        stage = "immutable_state_binding"
        o2d = drive / r4.O2_REL
        r3.verify_manifest(o2d, r4.O2_MANIFEST)
        with np.load(o2d / r4.O2_STATE, allow_pickle=False) as z:
            demand = np.asarray(z["event_CV_component_mass_kg"], dtype=np.float64).reshape(-1)
            e2_cv = np.asarray(z["E2_pair_cv_id"], dtype=np.int64)
            e2_cell = np.asarray(z["E2_pair_flat_cell"], dtype=np.int64)
            residual_grid = np.asarray(
                z["frozen_residual_grid_component_mass_kg"], dtype=np.float64
            )
            grid_pv = np.asarray(z["grid_pore_volume_m3"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))

        gate(
            "O2_state_shapes_exact",
            demand.shape == (NCVTOTAL,)
            and e2_cv.shape == (EXPECTED_E2,)
            and e2_cell.shape == (EXPECTED_E2,)
            and residual_grid.shape == GRID
            and grid_pv.shape == GRID,
        )
        residual = residual_grid.reshape(-1)

        a2d = drive / r4.A2E_REL
        r3.verify_manifest(a2d, r4.A2E_MANIFEST)
        with np.load(a2d / r4.A2E_EPOCH, allow_pickle=False) as z:
            epoch = {k: np.asarray(z[k]).copy() for k in z.files}
        grid_nw = np.asarray(epoch["nw"], dtype=np.float64)
        grid_no = np.asarray(epoch["no"], dtype=np.float64)
        grid_krw = np.asarray(epoch["krw_max"], dtype=np.float64)
        grid_kro = np.asarray(epoch["kro_max"], dtype=np.float64)

        r4rec = drive / r4.RECOVERY_REL
        base_dir = r4.recovery_dir(r4rec, "accepted_iterates", 0)
        bsn, bmn, bman = r4.accepted_names(0)
        gate(
            "R4_base_checkpoint_valid",
            r4.manifest_valid(r3, base_dir, bman, {bsn, bmn}),
            str(base_dir),
        )
        with np.load(base_dir / bsn, allow_pickle=False) as z:
            S_base = np.asarray(z["S_iter_next"], dtype=np.float64)

        map_dir = r4.recovery_dir(r4rec, "physical_maps", 1)
        msn, mmn, mman = r4.map_names(1)
        gate(
            "R4_map_checkpoint_valid",
            r4.manifest_valid(r3, map_dir, mman, {msn, mmn}),
            str(map_dir),
        )
        map_meta = r3.load_json(map_dir / mmn)
        with np.load(map_dir / msn, allow_pickle=False) as z:
            S_map_base = np.asarray(z["S_iter"], dtype=np.float64)
            S_map = np.asarray(z["S_map"], dtype=np.float64)
            P_map_checkpoint = np.asarray(z["P_map_psi"], dtype=np.float64)

        gate(
            "R4_base_map_pair_exact",
            S_base.shape == GRID
            and S_map.shape == GRID
            and r4.array_sha256(S_base) == r4.array_sha256(S_map_base),
            {
                "S_base_digest": r4.array_sha256(S_base),
                "S_map_digest": r4.array_sha256(S_map),
            },
        )
        gate(
            "R4_map_is_certified_physical_candidate",
            map_meta.get("checkpoint_classification") == "PHYSICAL_MAP_CANDIDATE"
            and int(map_meta.get("nonlinear_iteration", -1)) == 1
            and map_meta.get("physical_state_authority") is True
            and map_meta.get("physical_time_advanced") is False,
        )

        d_raw = S_map - S_base
        sci_gate(
            "raw_direction_finite",
            np.isfinite(d_raw).all(),
            {"raw_Linf": float(np.max(np.abs(d_raw)))},
        )

        # ----------------------------------------------------------------------------------
        # Pressure/capacity physics.
        # ----------------------------------------------------------------------------------
        stage = "pressure_physics_setup"
        permeability_md = np.loadtxt(
            root / r4.PERM, skiprows=1, dtype=np.float64
        ).reshape(GRID, order="C")
        kx, ky, kz = sg2.build_directional_permeability(permeability_md)
        kfx, kfy, kfz = sg2.build_face_permeabilities(kx, ky, kz)
        tx_ref, ty_ref, tz_ref = sg3.construct_si_transmissibilities(kfx, kfy, kfz)

        def pressure_step(saturation: np.ndarray) -> tuple[np.ndarray, float]:
            mobility = a2e.spatial_mobility(
                saturation, grid_nw, grid_no, grid_krw, grid_kro
            )
            tx, ty, tz, _ = r3r2r1.build_updated_transmissibilities(
                sg3, tx_ref, ty_ref, tz_ref, mobility["lambda_total"]
            )
            A, b, _ = r3r2r1.assemble_updated_pressure_system(
                sg3, permeability_md, tx, ty, tz, mobility["lambda_total"]
            )
            _ppa, ppsi, linear_residual = r3r2r1.solve_updated_pressure(sg3, A, b)
            return np.asarray(ppsi, dtype=np.float64), float(linear_residual)

        def capacity_and_cut_deficit(
            saturation: np.ndarray,
        ) -> tuple[np.ndarray, np.ndarray, float, float, np.ndarray]:
            p, pres = pressure_step(saturation)
            cap = np.asarray(
                a2e.local_mass(
                    r2phys, np.full(GRID, INJECTED), p, p_ref, grid_pv
                ),
                dtype=np.float64,
            )
            avail_raw = cap.reshape(-1) - residual
            cap_tol = max(
                1.0e-8,
                1.0e-12 * max(float(np.max(np.abs(cap))), 1.0),
            )
            if float(np.min(avail_raw)) < -cap_tol:
                raise ScientificFail(
                    "probe_or_trial_residual_sidecar_capacity",
                    {
                        "minimum_available_mapped_capacity_kg": float(np.min(avail_raw)),
                        "tolerance_kg": cap_tol,
                    },
                )
            available = np.maximum(avail_raw, 0.0)
            deficit = cut_demand - float(np.sum(available[cut_cell_ids]))
            return p, cap, float(pres), float(deficit), available

        p0, cap0, pres0, deficit0, available0 = capacity_and_cut_deficit(S_base)
        sci_gate(
            "base_pressure_linear_residual",
            pres0 < float(pr2["probe_method"]["pressure_residual_max"]),
            pres0,
        )
        sci_gate(
            "base_pressure_matches_R4_map_pressure",
            o3r6.max_abs(p0 - P_map_checkpoint) <= 1.0e-8,
            o3r6.max_abs(p0 - P_map_checkpoint),
        )
        sci_gate(
            "base_cut_deficit_matches_R1R1",
            abs(
                deficit0
                + float(op2["cut_definition"]["omega0_spare_capacity_kg"])
            ) <= 2.0e-5,
            deficit0,
        )

        # ----------------------------------------------------------------------------------
        # 24 immutable local sensitivity probes.
        # ----------------------------------------------------------------------------------
        stage = "cut_sensitivity_probes"
        probe_root = recovery / "sensitivity_probes"
        g = np.zeros(cut_cell_ids.size, dtype=np.float64)
        probe_rows: list[dict[str, Any]] = []

        for local_index, cell in enumerate(cut_cell_ids):
            pn, pm = probe_names(local_index, int(cell))
            pd = probe_root / f"probe_{local_index:02d}_cell_{int(cell):05d}"

            if checkpoint_manifest_valid(r3, pd, pm, {pn}):
                rec = r3.load_json(pd / pn)
                g[local_index] = float(rec["sensitivity_kg_per_saturation"])
                probe_rows.append(dict(rec))
                print(
                    f"[REUSE] sensitivity probe {local_index+1:02d}/24 "
                    f"cell={int(cell)} g={g[local_index]:.12e}"
                )
                continue

            s0_flat = S_base.reshape(-1)
            s0 = float(s0_flat[int(cell)])
            plus_ok = s0 + hprobe <= float(r2.SATURATION_MAX) + 1.0e-15
            minus_ok = s0 - hprobe >= float(r2.SATURATION_MIN) - 1.0e-15

            dplus = None
            dminus = None
            rplus = None
            rminus = None
            method = None

            if plus_ok and minus_ok:
                sp = S_base.copy().reshape(-1)
                sm = S_base.copy().reshape(-1)
                sp[int(cell)] += hprobe
                sm[int(cell)] -= hprobe
                _pp, _cp, rplus, dplus, _ap = capacity_and_cut_deficit(
                    sp.reshape(GRID)
                )
                _pm, _cm, rminus, dminus, _am = capacity_and_cut_deficit(
                    sm.reshape(GRID)
                )
                deriv = (float(dplus) - float(dminus)) / (2.0 * hprobe)
                method = "CENTRAL"
            elif plus_ok:
                sp = S_base.copy().reshape(-1)
                sp[int(cell)] += hprobe
                _pp, _cp, rplus, dplus, _ap = capacity_and_cut_deficit(
                    sp.reshape(GRID)
                )
                deriv = (float(dplus) - deficit0) / hprobe
                method = "FORWARD_INWARD"
            elif minus_ok:
                sm = S_base.copy().reshape(-1)
                sm[int(cell)] -= hprobe
                _pm, _cm, rminus, dminus, _am = capacity_and_cut_deficit(
                    sm.reshape(GRID)
                )
                deriv = (deficit0 - float(dminus)) / hprobe
                method = "BACKWARD_INWARD"
            else:
                raise ScientificFail(
                    "no_admissible_local_saturation_probe",
                    {"cell": int(cell), "base_saturation": s0},
                )

            pressure_probe_execution_performed = True
            max_probe_resid = max(
                [x for x in [rplus, rminus] if x is not None],
                default=0.0,
            )
            sci_gate(
                f"probe_{local_index:02d}_pressure_residual",
                max_probe_resid < float(pr2["probe_method"]["pressure_residual_max"]),
                max_probe_resid,
            )
            sci_gate(
                f"probe_{local_index:02d}_finite_sensitivity",
                math.isfinite(float(deriv)),
                float(deriv),
            )

            rec = {
                "milestone": MILESTONE,
                "probe_index": int(local_index),
                "flat_cell": int(cell),
                "base_saturation": s0,
                "probe_size_saturation": hprobe,
                "method": method,
                "base_cut_deficit_kg": deficit0,
                "plus_cut_deficit_kg": None if dplus is None else float(dplus),
                "minus_cut_deficit_kg": None if dminus is None else float(dminus),
                "plus_pressure_linear_relative_residual":
                    None if rplus is None else float(rplus),
                "minus_pressure_linear_relative_residual":
                    None if rminus is None else float(rminus),
                "sensitivity_kg_per_saturation": float(deriv),
                "state_mutated": False,
                "physical_time_advanced": False,
            }
            r3.immutable_publish(pd, {pn: r3.json_bytes(rec)})
            r3.immutable_publish(
                pd,
                {
                    pm: r3.csv_bytes([{
                        "file": pn,
                        "sha256": r3.sha256_file(pd / pn),
                        "bytes": (pd / pn).stat().st_size,
                    }])
                },
            )
            g[local_index] = float(deriv)
            probe_rows.append(rec)
            print(
                f"[CHECKPOINT] sensitivity probe {local_index+1:02d}/24 "
                f"cell={int(cell)} method={method} g={g[local_index]:.12e}"
            )
            sys.stdout.flush()

        sci_gate(
            "all_24_sensitivities_finite",
            g.shape == (24,) and np.isfinite(g).all(),
            {"g_L2": float(np.linalg.norm(g)), "g_Linf": float(np.max(np.abs(g)))},
        )

        g2 = float(np.dot(g, g))
        sci_gate(
            "positive_cut_sensitivity_norm",
            math.isfinite(g2) and g2 > 0.0,
            g2,
        )

        q = -(a_raw / g2) * g
        tangent_residual = a_raw + float(np.dot(g, q))
        sci_gate(
            "projected_first_order_tangent_condition",
            abs(tangent_residual)
                <= float(r2.PROJECTED_DERIVATIVE_TOL_KG_PER_FULL_STEP),
            tangent_residual,
        )

        d_projected = np.asarray(d_raw, dtype=np.float64).copy().reshape(-1)
        d_projected[cut_cell_ids] += q
        d_projected = d_projected.reshape(GRID)

        sci_gate(
            "projected_direction_finite",
            np.isfinite(d_projected).all(),
            {
                "projected_Linf": float(np.max(np.abs(d_projected))),
                "correction_L2": float(np.linalg.norm(q)),
                "correction_Linf": float(np.max(np.abs(q))),
            },
        )

        # ----------------------------------------------------------------------------------
        # Exact projected feasibility line search.
        # ----------------------------------------------------------------------------------
        stage = "projected_exact_feasibility_line_search"
        line_root = recovery / "projected_line_search"

        def evaluate_alpha(alpha_index: int) -> dict[str, Any]:
            nonlocal feasibility_lp_execution_performed
            alpha = float(alpha_index) / float(LINE_DEN)
            ld = line_root / f"alpha_{alpha_index:04d}_of_{LINE_DEN}"
            sn, rn, mn = line_names(alpha_index)

            if checkpoint_manifest_valid(r3, ld, mn, {sn, rn}):
                rec = r3.load_json(ld / rn)
                print(
                    f"[REUSE] alpha={alpha:.9f} "
                    f"feasible={rec['exact_frozen_E2_feasible']}"
                )
                return rec

            S_trial = S_base + alpha * d_projected
            smin = float(np.min(S_trial))
            smax = float(np.max(S_trial))

            if (
                smin < float(r2.SATURATION_MIN) - 1.0e-10
                or smax > float(r2.SATURATION_MAX) + 1.0e-10
            ):
                rec = {
                    "milestone": MILESTONE,
                    "alpha_index": int(alpha_index),
                    "alpha_denominator": LINE_DEN,
                    "alpha": alpha,
                    "exact_frozen_E2_feasible": False,
                    "classification_source": "SATURATION_BOUNDS",
                    "minimum_unserved_mass_kg": None,
                    "unserved_CV_count_above_1e6_kg": None,
                    "unserved_CV_ids": [],
                    "unserved_CV_values_kg": [],
                    "pressure_linear_relative_residual": None,
                    "CV_equality_Linf_kg": None,
                    "maximum_cell_capacity_excess_kg": None,
                    "trial_saturation_minmax": [smin, smax],
                    "physical_state_authority": False,
                    "physical_time_advanced": False,
                }
                arrays = {
                    "S_trial": S_trial,
                    "unserved_CV_ids": np.asarray([], dtype=np.int64),
                    "unserved_CV_values_kg": np.asarray([], dtype=np.float64),
                }
            else:
                p, cap, pres, cut_deficit, available = capacity_and_cut_deficit(
                    S_trial
                )
                sci_gate(
                    f"alpha_{alpha_index:04d}_pressure_residual",
                    pres < float(pr2["probe_method"]["pressure_residual_max"]),
                    pres,
                )
                lp, active, cv_e, cell_e, nedge, nnz = o3r4.build_feasibility_lp(
                    highspy, coo_matrix, e2_cv, e2_cell, demand, available
                )
                x, u, tel = o3r4.run_highs_feasibility(highspy, lp, nedge)
                del lp
                gc.collect()
                feasibility_lp_execution_performed = True

                assigned = np.bincount(
                    cv_e, weights=x, minlength=NCVTOTAL
                ).astype(np.float64)
                mapped = np.bincount(
                    cell_e, weights=x, minlength=NCELL
                ).astype(np.float64)
                cv_linf = float(np.max(np.abs(assigned + u - demand)))
                cap_excess = float(np.max(mapped - available))
                sci_gate(
                    f"alpha_{alpha_index:04d}_LP_certification",
                    cv_linf <= FEAS_CV_LINF_TOL
                    and cap_excess <= FEAS_CAP_EXCESS_TOL,
                    {
                        "CV_Linf_kg": cv_linf,
                        "capacity_excess_kg": cap_excess,
                    },
                )
                unserved = float(np.sum(u))
                ids = np.flatnonzero(u > FEAS_UNSERVED_TOL).astype(np.int64)
                vals = u[ids].astype(np.float64)
                feasible = unserved <= FEAS_UNSERVED_TOL

                rec = {
                    "milestone": MILESTONE,
                    "alpha_index": int(alpha_index),
                    "alpha_denominator": LINE_DEN,
                    "alpha": alpha,
                    "exact_frozen_E2_feasible": bool(feasible),
                    "classification_source": "EXACT_MINIMUM_UNSERVED_LP",
                    "minimum_unserved_mass_kg": unserved,
                    "unserved_CV_count_above_1e6_kg": int(ids.size),
                    "unserved_CV_ids": [int(v) for v in ids],
                    "unserved_CV_values_kg": [float(v) for v in vals],
                    "pressure_linear_relative_residual": float(pres),
                    "cut_signed_deficit_kg": float(cut_deficit),
                    "CV_equality_Linf_kg": cv_linf,
                    "maximum_cell_capacity_excess_kg": cap_excess,
                    "active_exact_zero_pruned_E2_edges": int(nedge),
                    "matrix_nnz": int(nnz),
                    "solver_telemetry": tel,
                    "trial_saturation_minmax": [smin, smax],
                    "physical_state_authority": False,
                    "physical_time_advanced": False,
                }
                arrays = {
                    "S_trial": S_trial,
                    "pressure_psi": p,
                    "cell_capacity_kg": cap,
                    "available_mapped_capacity_kg": available.reshape(GRID),
                    "unserved_CV_ids": ids,
                    "unserved_CV_values_kg": vals,
                }

            r3.immutable_publish(
                ld,
                {
                    sn: o3r6.deterministic_npz_bytes(arrays),
                    rn: r3.json_bytes(rec),
                },
            )
            r3.immutable_publish(
                ld,
                {
                    mn: r3.csv_bytes([
                        {
                            "file": n,
                            "sha256": r3.sha256_file(ld / n),
                            "bytes": (ld / n).stat().st_size,
                        }
                        for n in (sn, rn)
                    ])
                },
            )
            print(
                f"[CHECKPOINT] alpha={alpha:.9f} "
                f"feasible={rec['exact_frozen_E2_feasible']} "
                f"unserved={rec['minimum_unserved_mass_kg']}"
            )
            sys.stdout.flush()
            return rec

        def monotonicity_guard(results: dict[int, dict[str, Any]]):
            seen_infeasible = False
            for idx in sorted(results):
                feas = bool(results[idx]["exact_frozen_E2_feasible"])
                if not feas:
                    seen_infeasible = True
                elif seen_infeasible:
                    raise ScientificFail(
                        "projected_sampled_nonmonotonic_feasibility",
                        {
                            "ordered_points": [
                                [int(i), bool(results[i]["exact_frozen_E2_feasible"])]
                                for i in sorted(results)
                            ]
                        },
                    )

        results: dict[int, dict[str, Any]] = {}
        idx = LINE_DEN
        results[idx] = evaluate_alpha(idx)

        if results[idx]["exact_frozen_E2_feasible"]:
            selected_idx = idx
        else:
            upper = idx
            lower = None
            idx //= 2
            while idx >= MIN_ALPHA_INDEX:
                results[idx] = evaluate_alpha(idx)
                monotonicity_guard(results)
                if results[idx]["exact_frozen_E2_feasible"]:
                    lower = idx
                    break
                upper = idx
                if idx == MIN_ALPHA_INDEX:
                    break
                idx //= 2

            if lower is None:
                raise ScientificFail(
                    "no_projected_feasible_alpha_at_or_above_1_over_1024",
                    {"minimum_alpha": 1.0 / LINE_DEN},
                )

            while upper - lower > 1:
                mid = (upper + lower) // 2
                if mid not in results:
                    results[mid] = evaluate_alpha(mid)
                monotonicity_guard(results)
                if results[mid]["exact_frozen_E2_feasible"]:
                    lower = mid
                else:
                    upper = mid
            selected_idx = lower

        selected = results[selected_idx]
        selected_alpha = float(selected_idx) / float(LINE_DEN)
        sci_gate(
            "projected_positive_feasible_step_exists",
            bool(selected["exact_frozen_E2_feasible"])
            and selected_idx >= MIN_ALPHA_INDEX,
            {"selected_alpha_index": selected_idx, "selected_alpha": selected_alpha},
        )

        # ----------------------------------------------------------------------------------
        # Final prospective candidate + decision. No nonlinear state is accepted.
        # ----------------------------------------------------------------------------------
        stage = "final_certification"
        S_candidate = S_base + selected_alpha * d_projected
        projection_state = {
            "S_base": S_base,
            "S_map": S_map,
            "d_raw": d_raw,
            "cut_CV_ids": cut_cv_ids,
            "cut_cell_ids": cut_cell_ids,
            "cut_sensitivity_g": g,
            "projection_correction_q": q,
            "d_projected": d_projected,
            "selected_alpha_index": np.asarray(selected_idx, dtype=np.int64),
            "selected_alpha": np.asarray(selected_alpha, dtype=np.float64),
            "prospective_S_candidate": S_candidate,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "operator_id": op2["operator_id"],
            "cut_CV_count": int(cut_cv_ids.size),
            "cut_cell_count": int(cut_cell_ids.size),
            "raw_cut_secant_slope_kg_per_full_raw_step": a_raw,
            "base_cut_signed_deficit_kg": deficit0,
            "sensitivity_g_L2": float(np.linalg.norm(g)),
            "sensitivity_g_Linf": float(np.max(np.abs(g))),
            "projection_correction_q_L2": float(np.linalg.norm(q)),
            "projection_correction_q_Linf": float(np.max(np.abs(q))),
            "projected_tangent_residual_kg_per_full_step": tangent_residual,
            "raw_direction_Linf": float(np.max(np.abs(d_raw))),
            "projected_direction_Linf": float(np.max(np.abs(d_projected))),
            "selected_alpha_index": int(selected_idx),
            "selected_alpha": selected_alpha,
            "selected_exact_frozen_E2_feasible": True,
            "selected_minimum_unserved_mass_kg":
                selected.get("minimum_unserved_mass_kg"),
            "selected_cut_signed_deficit_kg":
                selected.get("cut_signed_deficit_kg"),
            "line_search_points_evaluated": len(results),
            "pressure_sensitivity_probe_count": 24,
            "pressure_probe_execution_performed":
                bool(pressure_probe_execution_performed),
            "feasibility_LP_execution_performed":
                bool(feasibility_lp_execution_performed),
            "five_stage_assignment_executed": False,
            "full_fixed_point_execution_performed": False,
            "prospective_candidate_physical_state_authority": False,
            "support_domain_changed": False,
            "capacity_relaxed": False,
            "per_CV_mass_relaxed": False,
            "physical_time_advanced": False,
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "scientific_interpretation": (
                "The R1-R1 controlling frozen-E2 cut can be neutralized to first order "
                "by the frozen minimum-L2 local tangent correction, and at least one "
                "projected step alpha>=1/1024 is exactly frozen-E2 feasible. This "
                "validates the projected-direction concept for the immutable R4 "
                "iteration-1 base/map pair only; it does not establish a full nonlinear "
                "solver or physical fixed point."
            ),
            "next_milestone": (
                "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R4-R4 — "
                "generalized active-set projected feasibility-preserving coupled-solver "
                "semantics design freeze"
            ),
            "O3R6R4R4_generalized_solver_design_freeze_authorized": True,
            "O3R6R4R4_execution_authorized": False,
            "full_fixed_point_execution_authorized": False,
            "five_stage_assignment_execution_authorized": False,
            "prospective_candidate_acceptance_authorized": False,
            "automatic_R4_rerun_authorized": False,
            "support_expansion_authorized": False,
            "capacity_relaxation_authorized": False,
            "per_CV_mass_relaxation_authorized": False,
            "sub_1_over_1024_projected_step_authorized": False,
            "O3R7_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }

        line_rows = []
        for i in sorted(results):
            rr = results[i]
            line_rows.append({
                "alpha_index": int(i),
                "alpha": float(rr["alpha"]),
                "feasible": bool(rr["exact_frozen_E2_feasible"]),
                "classification_source": rr["classification_source"],
                "minimum_unserved_mass_kg": rr["minimum_unserved_mass_kg"],
                "unserved_CV_count": rr["unserved_CV_count_above_1e6_kg"],
                "cut_signed_deficit_kg": rr.get("cut_signed_deficit_kg"),
                "pressure_linear_relative_residual":
                    rr["pressure_linear_relative_residual"],
                "CV_equality_Linf_kg": rr["CV_equality_Linf_kg"],
                "maximum_cell_capacity_excess_kg":
                    rr["maximum_cell_capacity_excess_kg"],
            })

        r3.immutable_publish(
            out,
            {
                SUMMARY: r3.json_bytes(summary),
                PROJECTION_STATE: o3r6.deterministic_npz_bytes(projection_state),
                PROBE_CSV: r3.csv_bytes(probe_rows),
                LINE_CSV: r3.csv_bytes(line_rows),
                DECISION: r3.json_bytes(decision),
                GATES: r3.csv_bytes([{"gate": k, **v} for k, v in gates.items()]),
            },
        )
        rows = [
            {
                "file": p.name,
                "sha256": r3.sha256_file(p),
                "bytes": p.stat().st_size,
            }
            for p in sorted(out.iterdir())
            if p.is_file() and p.name != MANIFEST
        ]
        r3.immutable_publish(out, {MANIFEST: r3.csv_bytes(rows)})

        print()
        print("=" * 214)
        print(MILESTONE + ": ONE-STEP PROJECTED FEASIBILITY TEST PASS")
        print("=" * 214)
        print("Cut CV / cell count               :", int(cut_cv_ids.size), "/", int(cut_cell_ids.size))
        print("g L2 / Linf                       :", float(np.linalg.norm(g)), "/", float(np.max(np.abs(g))))
        print("q L2 / Linf                       :", float(np.linalg.norm(q)), "/", float(np.max(np.abs(q))))
        print("Tangent residual kg/full step     :", tangent_residual)
        print("Selected alpha                    :", selected_idx, "/", LINE_DEN, "=", selected_alpha)
        print("Selected minimum unserved kg      :", selected.get("minimum_unserved_mass_kg"))
        print("Five-stage assignment executed    : False")
        print("Full fixed-point execution        : False")
        print("Prospective candidate authority   : False")
        print("R4-R4 design freeze authorized    : True")
        print("R4-R4 execution authorized        : False")
        print("O3-R7                             : NOT AUTHORIZED")
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
            "pressure_probe_execution_performed":
                bool(pressure_probe_execution_performed),
            "feasibility_LP_execution_performed":
                bool(feasibility_lp_execution_performed),
            "five_stage_assignment_executed": False,
            "full_fixed_point_execution_performed": False,
            "prospective_candidate_acceptance_authorized": False,
            "support_domain_changed": False,
            "physical_time_advanced": False,
            "automatic_rerun_authorized": False,
            "O3R7_authorized": False,
            "F5_dataset_generation_authorized": False,
        }
        p = failed / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3_Scientific_Fail_Report.json"
        if not p.exists():
            p.write_bytes((json.dumps(report, indent=2, sort_keys=True) + "\n").encode())
        print()
        print(MILESTONE + ": SCIENTIFIC FAIL")
        print("Stage :", stage)
        print("Gate  :", exc.gate)
        print("Detail:", exc.detail)
        print("NO AUTOMATIC RERUN OR REPAIR AUTHORIZED.")
        return 3

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCK,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "pressure_probe_execution_performed":
                bool(pressure_probe_execution_performed),
            "feasibility_LP_execution_performed":
                bool(feasibility_lp_execution_performed),
            "five_stage_assignment_executed": False,
            "full_fixed_point_execution_performed": False,
            "support_domain_changed": False,
            "physical_time_advanced": False,
            "automatic_rerun_authorized": False,
            "O3R7_authorized": False,
            "F5_dataset_generation_authorized": False,
        }
        p = blocked / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3_Blocked_Report.json"
        if not p.exists():
            p.write_bytes((json.dumps(report, indent=2, sort_keys=True) + "\n").encode())
        print()
        print(MILESTONE + ": TECHNICAL / AUTHORITY BLOCK")
        print("Stage    :", stage)
        print("Exception:", repr(exc))
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
    raise SystemExit(main(args.project_root, args.drive_root))
