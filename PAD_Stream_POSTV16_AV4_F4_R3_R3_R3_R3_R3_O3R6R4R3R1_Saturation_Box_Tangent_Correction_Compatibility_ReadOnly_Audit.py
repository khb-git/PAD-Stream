#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R4-R3-R1"
STATUS_PASS = (
    "AV4F4R3R3R3R3R3O3R6R4R3R1_SATURATION_BOX_TANGENT_CORRECTION_"
    "COMPATIBILITY_READ_ONLY_AUDIT_PASS_NO_PRESSURE_NO_LP_NO_STATE_MUTATION_"
    "NO_SUPPORT_EXPANSION_NO_TIME_ADVANCE"
)
STATUS_BLOCK = "AV4F4R3R3R3R3R3O3R6R4R3R1_TECHNICAL_OR_AUTHORITY_BLOCK"

PARENT_R3_COMMIT = "3709329532409c50f870b1ffe5467e05558c05a6"

R3 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3_"
    "Controlled_SingleCut_Projected_Direction_OneStep_Feasibility_Test.py"
)
R3_BLOB = "059b3379115b3cabc215a16d1a1fca82ad0ca88a"
R2 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R2_"
    "Projected_Tangent_Constrained_Update_Semantics_Design_Freeze.py"
)
R2_BLOB = "687a35265bf0fe72a2110e2f91dab78cac5805b8"
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

R3_RECOVERY = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3_Recovery_Checkpoints"
R3_FAIL = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3_SCIENTIFIC_FAIL"
R3_FAIL_REPORT = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3_Scientific_Fail_Report.json"

R4_RECOVERY = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_Recovery_Checkpoints"

R2_REL = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R2_"
    "Projected_Tangent_Constrained_Update_Semantics_Design_Freeze"
)
R2_OPERATOR = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R2_Projected_Update_Operator_Contract.json"
R2_PROBES = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R2_Cut_Sensitivity_Probe_Contract.json"
R2_DECISION = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R2_Decision_Contract.json"
R2_MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R2_Artifact_Manifest.csv"

OUT = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R1_"
    "Saturation_Box_Tangent_Correction_Compatibility_ReadOnly_Audit"
)
BLOCK = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R1_BLOCKED"

SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R1_Summary.json"
AUDIT = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R1_Box_Tangent_Audit.json"
ALPHA_CSV = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R1_Box_Tangent_Alpha_Sweep.csv"
CELL_CSV = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R1_Cut_Cell_Bound_Diagnostics.csv"
DECISION = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R1_Decision_Contract.json"
GATES = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R1_Final_Gate_Matrix.csv"
MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R1_Artifact_Manifest.csv"

GRID = (15, 50, 50)
LINE_DEN = 1024
ALPHA_INDICES = [1,2,4,8,16,32,64,128,256,512,1024]
S_MIN = 0.20
S_MAX = 0.80
TARGET_TOL = 1.0e-10
BOUND_TOL = 1.0e-12


class GateError(RuntimeError):
    pass


def load_module(path: Path, name: str):
    import importlib.util
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


def flat_to_kji(cell: int) -> tuple[int,int,int]:
    k = int(cell) // 2500
    rem = int(cell) % 2500
    j = rem // 50
    i = rem % 50
    return k,j,i


def bounded_dot_range(g: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> tuple[float,float]:
    gl = g * lo
    gh = g * hi
    return float(np.sum(np.minimum(gl, gh))), float(np.sum(np.maximum(gl, gh)))


def min_norm_box_hyperplane(
    g: np.ndarray, lo: np.ndarray, hi: np.ndarray, target: float
) -> np.ndarray:
    """
    Solve min 0.5 ||q||^2 subject to g^T q = target and lo <= q <= hi.
    KKT form q(lambda)=clip(-lambda*g, lo, hi). Monotone in lambda.
    """
    dmin, dmax = bounded_dot_range(g, lo, hi)
    if target < dmin - TARGET_TOL or target > dmax + TARGET_TOL:
        raise GateError(
            f"bounded_hyperplane_infeasible: target={target}, range=({dmin},{dmax})"
        )

    # Find a bracket in lambda. phi(lambda)=g^T clip(-lambda*g,lo,hi)-target
    def phi(lam: float) -> float:
        q = np.clip(-lam * g, lo, hi)
        return float(np.dot(g, q) - target)

    left, right = -1.0, 1.0
    fl, fr = phi(left), phi(right)
    # phi is non-increasing in lambda.
    for _ in range(200):
        if fl >= 0.0 and fr <= 0.0:
            break
        if fl < 0.0:
            left *= 2.0
            fl = phi(left)
        if fr > 0.0:
            right *= 2.0
            fr = phi(right)
    else:
        raise GateError("lambda_bracket_failure")

    for _ in range(200):
        mid = 0.5 * (left + right)
        fm = phi(mid)
        if abs(fm) <= 1.0e-12:
            left = right = mid
            break
        if fm > 0.0:
            left = mid
        else:
            right = mid

    lam = 0.5 * (left + right)
    q = np.clip(-lam * g, lo, hi)
    return q


def self_test() -> None:
    g = np.asarray([1.0, -2.0], dtype=float)
    lo = np.asarray([-1.0, -1.0])
    hi = np.asarray([1.0, 1.0])
    target = -1.5
    q = min_norm_box_hyperplane(g, lo, hi, target)
    assert abs(float(np.dot(g, q)) - target) <= 1.0e-9
    assert np.all(q >= lo - 1e-12) and np.all(q <= hi + 1e-12)
    print("POSTV16 O3-R6-R4-R3-R1 box/tangent audit structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT
    blocked = drive / BLOCK
    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"

    def gate(name: str, cond: bool, detail: Any = None):
        gates[name] = {"status": "PASS" if cond else "FAIL", "detail": detail}
        if not cond:
            raise GateError(f"{name}: {detail!r}")
        print(f"[PASS] {name}" + (f" -- {detail}" if detail is not None else ""))

    print("="*210)
    print(MILESTONE + " -- SATURATION-BOX / TANGENT-CORRECTION COMPATIBILITY READ-ONLY AUDIT")
    print("="*210)
    print("READ-ONLY. REUSES IMMUTABLE R3 PROBES / LINE-SEARCH CHECKPOINTS AND R4 BASE/MAP.")
    print("NO PRESSURE SOLVES. NO HIGHS LP. NO PROJECTED EXECUTION. NO STATE MUTATION.")
    print("NO SUPPORT EXPANSION. NO CAPACITY/CV-MASS RELAXATION. NO TIME ADVANCE.")
    print()

    try:
        stage = "repository_authority"
        parent = git_text(root, "rev-parse", "HEAD^")
        dirty = git_text(root, "status", "--porcelain")
        gate("repository_parent_is_R3_commit", parent == PARENT_R3_COMMIT, parent)
        gate("repository_clean", dirty == "", repr(dirty))
        for fn, expected in {
            R3:R3_BLOB, R2:R2_BLOB, R4:R4_BLOB, R3DESIGN:R3DESIGN_BLOB
        }.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        r3test = load_module(root / R3, "postv16_o3r6r4r3r1_r3test")
        r2 = load_module(root / R2, "postv16_o3r6r4r3r1_r2")
        r4 = load_module(root / R4, "postv16_o3r6r4r3r1_r4")
        r3 = load_module(root / R3DESIGN, "postv16_o3r6r4r3r1_r3design")

        stage = "R3_fail_binding"
        failp = drive / R3_FAIL / R3_FAIL_REPORT
        gate("R3_fail_report_present", failp.is_file(), str(failp))
        fail = r3.load_json(failp)
        gate(
            "R3_scientific_fail_exact",
            fail.get("status") == r3test.STATUS_FAIL
            and fail.get("failed_gate") == "no_projected_feasible_alpha_at_or_above_1_over_1024"
            and fail.get("failed_stage") == "projected_exact_feasibility_line_search"
            and fail.get("feasibility_LP_execution_performed") is False
            and fail.get("five_stage_assignment_executed") is False
            and fail.get("full_fixed_point_execution_performed") is False
            and fail.get("support_domain_changed") is False
            and fail.get("physical_time_advanced") is False
            and fail.get("automatic_rerun_authorized") is False,
        )
        gate(
            "R3_unbounded_projection_metrics_bound",
            abs(float(fail["gates"]["all_24_sensitivities_finite"]["detail"]["g_L2"]) - 1.2493304995770507) <= 1e-12
            and abs(float(fail["gates"]["projected_direction_finite"]["detail"]["correction_L2"]) - 42.68983574216097) <= 1e-10
            and abs(float(fail["gates"]["projected_direction_finite"]["detail"]["correction_Linf"]) - 25.45324129038726) <= 1e-10
            and abs(float(fail["gates"]["raw_direction_finite"]["detail"]["raw_Linf"]) - 0.23222537758493456) <= 1e-12,
        )

        stage = "R2_contract_binding"
        r2d = drive / R2_REL
        gate("R2_output_present", r2d.is_dir(), str(r2d))
        r3.verify_manifest(r2d, R2_MANIFEST)
        op2 = r3.load_json(r2d / R2_OPERATOR)
        pr2 = r3.load_json(r2d / R2_PROBES)
        d2 = r3.load_json(r2d / R2_DECISION)
        gate(
            "R2_contract_exact",
            op2.get("operator_id") == "PAD_STREAM_SINGLE_CUT_LOCAL_SECANT_TANGENT_PROJECTION_V1"
            and d2.get("O3R6R4R3_one_step_projected_test_authorized") is True
            and d2.get("O3R6R4R3_full_fixed_point_execution_authorized") is False
            and d2.get("O3R6R4R3_five_stage_assignment_authorized") is False,
        )
        cut_cells = np.asarray(op2["cut_definition"]["cell_ids"], dtype=np.int64)
        a_raw = float(op2["raw_cut_secant_slope"]["value_kg_per_full_raw_step"])
        gate("cut_cell_count_exact_24", cut_cells.size == 24, int(cut_cells.size))

        stage = "R4_base_map_binding"
        r4rec = drive / R4_RECOVERY
        bdir = r4.recovery_dir(r4rec, "accepted_iterates", 0)
        bsn,bmn,bman = r4.accepted_names(0)
        gate("R4_base_checkpoint_valid", r4.manifest_valid(r3,bdir,bman,{bsn,bmn}), str(bdir))
        with np.load(bdir / bsn, allow_pickle=False) as z:
            S_base = np.asarray(z["S_iter_next"], dtype=np.float64)

        mdir = r4.recovery_dir(r4rec, "physical_maps", 1)
        msn,mmn,mman = r4.map_names(1)
        gate("R4_map_checkpoint_valid", r4.manifest_valid(r3,mdir,mman,{msn,mmn}), str(mdir))
        with np.load(mdir / msn, allow_pickle=False) as z:
            S_iter_map = np.asarray(z["S_iter"], dtype=np.float64)
            S_map = np.asarray(z["S_map"], dtype=np.float64)
        gate(
            "R4_base_map_pair_exact",
            r4.array_sha256(S_base) == r4.array_sha256(S_iter_map),
            r4.array_sha256(S_base),
        )
        d_raw = S_map - S_base

        stage = "R3_probe_binding"
        probe_root = drive / R3_RECOVERY / "sensitivity_probes"
        g = np.zeros(24, dtype=np.float64)
        probe_rows = []
        for local_index, cell in enumerate(cut_cells):
            pn,pm = r3test.probe_names(local_index,int(cell))
            pd = probe_root / f"probe_{local_index:02d}_cell_{int(cell):05d}"
            gate(
                f"probe_{local_index:02d}_checkpoint_valid",
                r3test.checkpoint_manifest_valid(r3,pd,pm,{pn}),
                str(pd),
            )
            rec = r3.load_json(pd / pn)
            gate(
                f"probe_{local_index:02d}_identity_exact",
                int(rec.get("probe_index",-1)) == local_index
                and int(rec.get("flat_cell",-1)) == int(cell)
                and math.isfinite(float(rec.get("sensitivity_kg_per_saturation"))),
            )
            g[local_index] = float(rec["sensitivity_kg_per_saturation"])
            probe_rows.append(rec)

        gate(
            "g_reconstructs_R3_norms",
            abs(float(np.linalg.norm(g)) - 1.2493304995770507) <= 1e-12
            and abs(float(np.max(np.abs(g))) - 0.7448965334333478) <= 1e-12,
            {"g_L2":float(np.linalg.norm(g)),"g_Linf":float(np.max(np.abs(g)))},
        )

        q_unbounded = -(a_raw / float(np.dot(g,g))) * g
        d_unbounded = d_raw.reshape(-1).copy()
        d_unbounded[cut_cells] += q_unbounded
        gate(
            "unbounded_projection_reconstructs_R3",
            abs(float(np.linalg.norm(q_unbounded)) - 42.68983574216097) <= 1e-9
            and abs(float(np.max(np.abs(q_unbounded))) - 25.45324129038726) <= 1e-9,
            {"q_L2":float(np.linalg.norm(q_unbounded)),"q_Linf":float(np.max(np.abs(q_unbounded)))},
        )

        stage = "R3_line_checkpoint_binding"
        line_root = drive / R3_RECOVERY / "projected_line_search"
        line_rows = []
        all_saturation_bounds = True
        for idx in ALPHA_INDICES:
            ld = line_root / f"alpha_{idx:04d}_of_{LINE_DEN}"
            sn,rn,mn = r3test.line_names(idx)
            gate(
                f"alpha_{idx:04d}_checkpoint_valid",
                r3test.checkpoint_manifest_valid(r3,ld,mn,{sn,rn}),
                str(ld),
            )
            rr = r3.load_json(ld / rn)
            with np.load(ld / sn, allow_pickle=False) as z:
                St = np.asarray(z["S_trial"],dtype=np.float64)
            expected = S_base + (idx/LINE_DEN) * d_unbounded.reshape(GRID)
            gate(
                f"alpha_{idx:04d}_trial_reconstruction",
                float(np.max(np.abs(St-expected))) <= 1e-12,
                float(np.max(np.abs(St-expected))),
            )
            all_saturation_bounds = all_saturation_bounds and (
                rr.get("classification_source") == "SATURATION_BOUNDS"
                and rr.get("exact_frozen_E2_feasible") is False
                and rr.get("minimum_unserved_mass_kg") is None
                and rr.get("pressure_linear_relative_residual") is None
            )
            sflat = St.reshape(-1)
            below = np.flatnonzero(sflat < S_MIN - 1e-10)
            above = np.flatnonzero(sflat > S_MAX + 1e-10)
            line_rows.append({
                "alpha_index":idx,
                "alpha":idx/LINE_DEN,
                "classification_source":rr.get("classification_source"),
                "trial_saturation_min":float(np.min(St)),
                "trial_saturation_max":float(np.max(St)),
                "below_lower_bound_count":int(below.size),
                "above_upper_bound_count":int(above.size),
                "worst_below_cell":None if below.size==0 else int(below[np.argmin(sflat[below])]),
                "worst_above_cell":None if above.size==0 else int(above[np.argmax(sflat[above])]),
            })
        gate("all_11_R3_trials_failed_saturation_bounds_before_LP", all_saturation_bounds, len(line_rows))

        # Exact box-limited alpha for the *unbounded* projected direction.
        s0 = S_base.reshape(-1)
        dp = d_unbounded
        alpha_limits = []
        limiting_cells = []
        for cell in range(dp.size):
            d = float(dp[cell])
            if d > 0.0:
                lim = (S_MAX - float(s0[cell])) / d
            elif d < 0.0:
                lim = (S_MIN - float(s0[cell])) / d
            else:
                continue
            if lim >= 0.0 and math.isfinite(lim):
                alpha_limits.append(float(lim))
                limiting_cells.append(cell)
        alpha_box_max = min(alpha_limits) if alpha_limits else math.inf
        min_positions = [
            i for i,v in enumerate(alpha_limits)
            if abs(v-alpha_box_max) <= max(1e-14,1e-10*max(abs(alpha_box_max),1.0))
        ]
        alpha_box_limiting_cells = [int(limiting_cells[i]) for i in min_positions]
        gate(
            "unbounded_projection_box_limit_below_1_over_1024",
            alpha_box_max < 1.0/LINE_DEN,
            {"alpha_box_max":alpha_box_max,"limiting_cells":alpha_box_limiting_cells},
        )

        # Box-constrained tangent compatibility at dyadic alpha values.
        stage = "box_constrained_tangent_compatibility"
        target = -a_raw
        alpha_rows = []
        feasible_indices = []
        q_min_at_smallest = None
        for idx in ALPHA_INDICES:
            alpha = idx/LINE_DEN
            sb = s0[cut_cells]
            dr = d_raw.reshape(-1)[cut_cells]
            lo = (S_MIN - sb)/alpha - dr
            hi = (S_MAX - sb)/alpha - dr
            dot_min,dot_max = bounded_dot_range(g,lo,hi)

            equality_feasible = (
                target >= dot_min - TARGET_TOL
                and target <= dot_max + TARGET_TOL
            )
            inward_inequality_feasible = dot_min <= target + TARGET_TOL

            q_bounded = None
            active_lower = active_upper = None
            q_l2 = q_linf = None
            tangent_residual = None
            candidate_min = candidate_max = None
            if equality_feasible:
                q_bounded = min_norm_box_hyperplane(g,lo,hi,target)
                tangent_residual = a_raw + float(np.dot(g,q_bounded))
                Scut = sb + alpha*(dr+q_bounded)
                candidate_min = float(np.min(Scut))
                candidate_max = float(np.max(Scut))
                active_lower = int(np.count_nonzero(np.isclose(q_bounded,lo,rtol=0,atol=1e-9)))
                active_upper = int(np.count_nonzero(np.isclose(q_bounded,hi,rtol=0,atol=1e-9)))
                q_l2 = float(np.linalg.norm(q_bounded))
                q_linf = float(np.max(np.abs(q_bounded)))
                if idx == 1:
                    q_min_at_smallest = q_bounded.copy()
                feasible_indices.append(idx)

            alpha_rows.append({
                "alpha_index":idx,
                "alpha":alpha,
                "target_g_dot_q":target,
                "achievable_g_dot_q_min":dot_min,
                "achievable_g_dot_q_max":dot_max,
                "tangent_equality_box_feasible":bool(equality_feasible),
                "tangent_inward_inequality_box_feasible":bool(inward_inequality_feasible),
                "bounded_min_norm_q_L2":q_l2,
                "bounded_min_norm_q_Linf":q_linf,
                "bounded_tangent_residual_kg_per_full_step":tangent_residual,
                "bounded_trial_cut_cell_saturation_min":candidate_min,
                "bounded_trial_cut_cell_saturation_max":candidate_max,
                "q_active_lower_bound_count":active_lower,
                "q_active_upper_bound_count":active_upper,
            })

        alpha_min_feasible = 1 in feasible_indices
        largest_feasible_index = max(feasible_indices) if feasible_indices else None
        largest_feasible_alpha = None if largest_feasible_index is None else largest_feasible_index/LINE_DEN

        if alpha_min_feasible:
            q1 = q_min_at_smallest
            sb = s0[cut_cells]
            dr = d_raw.reshape(-1)[cut_cells]
            S1cut = sb + (1/LINE_DEN)*(dr+q1)
            gate(
                "bounded_tangent_candidate_at_1_over_1024_respects_box",
                float(np.min(S1cut)) >= S_MIN-1e-10
                and float(np.max(S1cut)) <= S_MAX+1e-10
                and abs(a_raw+float(np.dot(g,q1))) <= 1e-8,
                {
                    "min":float(np.min(S1cut)),
                    "max":float(np.max(S1cut)),
                    "tangent_residual":a_raw+float(np.dot(g,q1)),
                },
            )

        # Cell-level diagnostics at alpha_min.
        alpha = 1.0/LINE_DEN
        sb = s0[cut_cells]
        dr = d_raw.reshape(-1)[cut_cells]
        lo = (S_MIN-sb)/alpha-dr
        hi = (S_MAX-sb)/alpha-dr
        cell_rows = []
        for j,cell in enumerate(cut_cells):
            k,row,col = flat_to_kji(int(cell))
            unbounded_step_dir = dr[j] + q_unbounded[j]
            S_unbounded_min_alpha = sb[j] + alpha*unbounded_step_dir
            cell_rows.append({
                "local_index":j,
                "flat_cell":int(cell),
                "layer_one_based":k+1,
                "row_one_based":row+1,
                "column_one_based":col+1,
                "S_base":float(sb[j]),
                "d_raw":float(dr[j]),
                "g":float(g[j]),
                "q_unbounded":float(q_unbounded[j]),
                "unbounded_projected_direction":float(unbounded_step_dir),
                "S_trial_unbounded_alpha_1_over_1024":float(S_unbounded_min_alpha),
                "violates_lower_at_alpha_1_over_1024":bool(S_unbounded_min_alpha < S_MIN-1e-10),
                "violates_upper_at_alpha_1_over_1024":bool(S_unbounded_min_alpha > S_MAX+1e-10),
                "box_q_lower_at_alpha_1_over_1024":float(lo[j]),
                "box_q_upper_at_alpha_1_over_1024":float(hi[j]),
                "q_box_min_norm_alpha_1_over_1024":
                    None if q_min_at_smallest is None else float(q_min_at_smallest[j]),
            })

        if alpha_min_feasible:
            classification = (
                "UNBOUNDED_MINIMUM_L2_TANGENT_CORRECTION_IS_SATURATION_BOX_"
                "INCOMPATIBLE_BUT_A_BOX_CONSTRAINED_TANGENT_EQUALITY_IS_"
                "ANALYTICALLY_FEASIBLE_AT_OR_ABOVE_1_OVER_1024"
            )
            implication = (
                "R3 failed because the unconstrained minimum-L2 correction ignored "
                "the saturation box. The certified local linear geometry still admits "
                "a box-respecting tangent correction at alpha>=1/1024. A successor "
                "design may therefore freeze a bound-constrained minimum-norm tangent "
                "projection and test it prospectively, without support expansion or "
                "sub-1/1024 stepping."
            )
            next_milestone = (
                "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R4-R3-R2 — "
                "bound-constrained tangent projection semantics design freeze"
            )
            design_authorized = True
        else:
            classification = (
                "NO_BOX_CONSTRAINED_TANGENT_EQUALITY_EXISTS_AT_ALPHA_1_OVER_1024_"
                "WITHIN_THE_CURRENT_24_CUT_CELL_CORRECTION_DOMAIN"
            )
            implication = (
                "The failure is not merely the choice of unconstrained minimum-L2 "
                "correction. The current 24 cut-cell correction domain cannot satisfy "
                "both the first-order cut condition and saturation bounds at the "
                "minimum authorized step. Further direction-space design review is "
                "required; no projected rerun is authorized."
            )
            next_milestone = (
                "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R4-R3-R2 — "
                "projected correction-domain design review"
            )
            design_authorized = False

        summary = {
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "classification":classification,
            "R3_scientific_fail_preserved":True,
            "R3_all_11_trials_failed_saturation_bounds_before_LP":True,
            "unbounded_q_L2":float(np.linalg.norm(q_unbounded)),
            "unbounded_q_Linf":float(np.max(np.abs(q_unbounded))),
            "raw_direction_Linf":float(np.max(np.abs(d_raw))),
            "unbounded_projected_direction_Linf":float(np.max(np.abs(d_unbounded))),
            "unbounded_projected_alpha_box_max":float(alpha_box_max),
            "unbounded_projected_alpha_box_limiting_cells":alpha_box_limiting_cells,
            "minimum_authorized_alpha":1.0/LINE_DEN,
            "box_constrained_tangent_equality_feasible_at_1_over_1024":bool(alpha_min_feasible),
            "largest_dyadic_alpha_with_box_constrained_tangent_equality":largest_feasible_alpha,
            "pressure_solve_executed":False,
            "feasibility_LP_executed":False,
            "five_stage_assignment_executed":False,
            "projected_trial_executed":False,
            "state_mutated":False,
            "support_domain_changed":False,
            "physical_time_advanced":False,
        }

        audit = {
            **summary,
            "a_raw_kg_per_full_step":a_raw,
            "g_L2":float(np.linalg.norm(g)),
            "g_Linf":float(np.max(np.abs(g))),
            "scientific_implication":implication,
            "gates":gates,
        }

        decision = {
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "classification":classification,
            "scientific_implication":implication,
            "next_milestone":next_milestone,
            "O3R6R4R3R2_bound_constrained_projection_design_freeze_authorized":bool(design_authorized),
            "O3R6R4R3R2_execution_authorized":False,
            "automatic_R3_rerun_authorized":False,
            "sub_1_over_1024_step_authorized":False,
            "support_expansion_authorized":False,
            "capacity_relaxation_authorized":False,
            "per_CV_mass_relaxation_authorized":False,
            "full_fixed_point_execution_authorized":False,
            "O3R7_authorized":False,
            "F5_dataset_generation_authorized":False,
            "training_authorized":False,
        }

        r3.immutable_publish(
            out,
            {
                SUMMARY:r3.json_bytes(summary),
                AUDIT:r3.json_bytes(audit),
                ALPHA_CSV:r3.csv_bytes(alpha_rows),
                CELL_CSV:r3.csv_bytes(cell_rows),
                DECISION:r3.json_bytes(decision),
                GATES:r3.csv_bytes([{"gate":k,**v} for k,v in gates.items()]),
            },
        )
        rows = [
            {"file":p.name,"sha256":r3.sha256_file(p),"bytes":p.stat().st_size}
            for p in sorted(out.iterdir()) if p.is_file() and p.name != MANIFEST
        ]
        r3.immutable_publish(out,{MANIFEST:r3.csv_bytes(rows)})

        print()
        print("="*210)
        print(MILESTONE + ": READ-ONLY AUDIT PASS")
        print("="*210)
        print("Classification                              :", classification)
        print("All 11 R3 trials saturation-bound rejected :", True)
        print("Unbounded projected alpha box max           :", alpha_box_max)
        print("Minimum authorized alpha                    :", 1.0/LINE_DEN)
        print("Box-constrained tangent feasible @ 1/1024   :", alpha_min_feasible)
        print("Largest dyadic alpha tangent-feasible        :", largest_feasible_alpha)
        print("Pressure / LP / projected execution         : False / False / False")
        print("R3-R2 design freeze authorized              :", design_authorized)
        print("R3-R2 execution authorized                  : False")
        print("O3-R7                                        : NOT AUTHORIZED")
        print("="*210)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        report = {
            "milestone":MILESTONE,
            "status":STATUS_BLOCK,
            "failed_stage":stage,
            "exception":repr(exc),
            "gates":gates,
            "read_only":True,
            "pressure_solve_executed":False,
            "feasibility_LP_executed":False,
            "projected_trial_executed":False,
            "state_mutated":False,
            "support_domain_changed":False,
            "physical_time_advanced":False,
            "automatic_R3_rerun_authorized":False,
            "O3R7_authorized":False,
        }
        p = blocked / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R1_Blocked_Report.json"
        if not p.exists():
            p.write_bytes((json.dumps(report,indent=2,sort_keys=True)+"\n").encode())
        print()
        print(MILESTONE + ": TECHNICAL / AUTHORITY BLOCK")
        print("Stage:",stage)
        print("Exception:",repr(exc))
        return 2


def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--project-root",type=Path,default=Path("."))
    p.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    p.add_argument("--self-test",action="store_true")
    return p.parse_args()


if __name__=="__main__":
    args=parse_args()
    if args.self_test:
        self_test(); raise SystemExit(0)
    raise SystemExit(main(args.project_root,args.drive_root))
