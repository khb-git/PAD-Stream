#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R4-R2"
STATUS_PASS = (
    "AV4F4R3R3R3R3R3O3R6R4R2_PROJECTED_TANGENT_CONSTRAINED_UPDATE_"
    "SEMANTICS_DESIGN_FREEZE_PASS_NO_PROJECTED_EXECUTION_NO_STATE_MUTATION_"
    "NO_SUPPORT_EXPANSION_NO_TIME_ADVANCE"
)
STATUS_BLOCK = "AV4F4R3R3R3R3R3O3R6R4R2_TECHNICAL_OR_AUTHORITY_BLOCK"

PARENT_R1R1_COMMIT = "e27629475fccf15a5e822a13a50928ce2fd1831e"

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
R3 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R3_"
    "Adaptive_Feasibility_Preserving_Stabilization_Semantics_Design_Freeze.py"
)
R3_BLOB = "c118972a991e4ae0ce7200a9f880a73407450b8b"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R1R1_REL = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1R1_"
    "CV60424_ActiveCut_Boundary_Semantics_Repair_and_Certification"
)
R1R1_SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1R1_Summary.json"
R1R1_AUDIT = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1R1_Active_Cut_Audit.json"
R1R1_DECISION = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1R1_Decision_Contract.json"
R1R1_GATES = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1R1_Final_Gate_Matrix.csv"
R1R1_OMEGA = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1R1_Active_Cut_Omega_Sweep.csv"
R1R1_CVS = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1R1_Active_Cut_CVs.csv"
R1R1_CELLS = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1R1_Active_Cut_Cells.csv"
R1R1_MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1R1_Artifact_Manifest.csv"
EXPECTED_R1R1_FILES = {
    R1R1_SUMMARY, R1R1_AUDIT, R1R1_DECISION, R1R1_GATES,
    R1R1_OMEGA, R1R1_CVS, R1R1_CELLS,
}

R4_RECOVERY = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_Recovery_Checkpoints"
R4_FAIL = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_SCIENTIFIC_FAIL"
R4_FAIL_REPORT = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_Scientific_Fail_Report.json"

OUT = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R2_"
    "Projected_Tangent_Constrained_Update_Semantics_Design_Freeze"
)
BLOCK = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R2_BLOCKED"

SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R2_Summary.json"
OPERATOR = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R2_Projected_Update_Operator_Contract.json"
PROBES = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R2_Cut_Sensitivity_Probe_Contract.json"
LINE = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R2_Projected_Line_Search_and_Failure_Semantics.json"
CONVERGENCE = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R2_Convergence_and_Final_Closure_Contract.json"
CHECKPOINT = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R2_Checkpoint_Restart_Policy.json"
DECISION = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R2_Decision_Contract.json"
GATES = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R2_Final_Gate_Matrix.csv"
MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R2_Artifact_Manifest.csv"

CONTROLLING_CV = 60424
EXPECTED_CUT_CV_COUNT = 67
EXPECTED_CUT_CELL_COUNT = 24
EXPECTED_DIRECT_CELLS = 13
EXPECTED_OMEGA0_SLACK_KG = 0.00032674171234248206
EXPECTED_OMEGA1_DEFICIT_KG = 0.051756963184743654
EXPECTED_SECANT_SLOPE = 53.3337138146162
EXPECTED_SECANT_ROOT = 6.126363400797675e-06

SATURATION_MIN = 0.20
SATURATION_MAX = 0.80
LOCAL_SATURATION_PROBE = 1.0e-5
PROBE_PRESSURE_RESIDUAL_MAX = 1.0e-8
PROJECTED_DERIVATIVE_TOL_KG_PER_FULL_STEP = 1.0e-8
LINE_SEARCH_DEN = 1024
MIN_POSITIVE_ALPHA_INDEX = 1


class GateError(RuntimeError):
    pass


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


def self_test() -> None:
    # Synthetic one-cut tangent projection: a_raw + g^T q == 0.
    g = np.asarray([2.0, -1.0, 3.0], dtype=np.float64)
    a_raw = 5.0
    q = -(a_raw / float(np.dot(g, g))) * g
    projected = a_raw + float(np.dot(g, q))
    assert abs(projected) <= 1.0e-12
    assert LINE_SEARCH_DEN == 1024
    assert SATURATION_MIN < SATURATION_MAX
    assert len(PARENT_R1R1_COMMIT) == 40
    print(
        "POSTV16 O3-R6-R4-R2 projected/tangent-constrained design structural self-test: PASS"
    )


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

    print("=" * 214)
    print(MILESTONE + " -- PROJECTED / TANGENT-CONSTRAINED UPDATE SEMANTICS DESIGN FREEZE")
    print("=" * 214)
    print("DESIGN / FREEZE ONLY.")
    print("NO PROJECTED DIRECTION EXECUTION. NO PRESSURE PROBES. NO FEASIBILITY LP.")
    print("NO FIVE-STAGE ASSIGNMENT. NO STATE MUTATION. NO SUPPORT EXPANSION. NO TIME ADVANCE.")
    print()

    try:
        stage = "repository_authority"
        parent = git_text(root, "rev-parse", "HEAD^")
        dirty = git_text(root, "status", "--porcelain")
        gate("repository_parent_is_R1R1_commit", parent == PARENT_R1R1_COMMIT, parent)
        gate("repository_clean", dirty == "", repr(dirty))

        for fn, expected in {
            R1R1: R1R1_BLOB,
            R4: R4_BLOB,
            R3: R3_BLOB,
        }.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        r1r1 = load_module(root / R1R1, "postv16_o3r6r4r2_r1r1")
        r3 = load_module(root / R3, "postv16_o3r6r4r2_r3")

        stage = "R1R1_certification_binding"
        r1d = drive / R1R1_REL
        gate("R1R1_output_present", r1d.is_dir(), str(r1d))
        manifest = r3.verify_manifest(r1d, R1R1_MANIFEST)
        gate(
            "R1R1_manifest_payload_exact",
            set(manifest) == EXPECTED_R1R1_FILES,
            sorted(manifest),
        )

        s = r3.load_json(r1d / R1R1_SUMMARY)
        a = r3.load_json(r1d / R1R1_AUDIT)
        d = r3.load_json(r1d / R1R1_DECISION)

        gate(
            "R1R1_PASS_exact",
            s.get("status") == r1r1.STATUS_PASS
            and s.get("controlling_CV_id") == CONTROLLING_CV
            and int(s.get("cut_CV_count", -1)) == EXPECTED_CUT_CV_COUNT
            and int(s.get("cut_cell_count", -1)) == EXPECTED_CUT_CELL_COUNT
            and int(s.get("CV60424_direct_reachable_cell_count", -1)) == EXPECTED_DIRECT_CELLS
            and s.get("same_cut_controls_all_11_failed_omega_points") is True
            and abs(float(s.get("omega_zero_cut_spare_capacity_kg")) - EXPECTED_OMEGA0_SLACK_KG) <= 1.0e-12
            and abs(float(s.get("omega_1_over_1024_cut_signed_deficit_kg")) - EXPECTED_OMEGA1_DEFICIT_KG) <= 1.0e-12
            and abs(float(s.get("diagnostic_secant_slope_kg_per_unit_omega")) - EXPECTED_SECANT_SLOPE) <= 1.0e-10
            and abs(float(s.get("diagnostic_secant_root_omega")) - EXPECTED_SECANT_ROOT) <= 1.0e-15
            and s.get("secant_root_is_certified_boundary") is False
            and s.get("five_stage_assignment_executed") is False
            and s.get("physical_time_advanced") is False,
        )
        gate(
            "R1R1_authorizes_R2_design_only",
            d.get("O3R6R4R2_design_freeze_authorized") is True
            and d.get("O3R6R4R2_execution_authorized") is False
            and d.get("scalar_damping_rerun_authorized") is False
            and d.get("sub_1_over_1024_scalar_damping_search_authorized") is False
            and d.get("support_expansion_authorized") is False
            and d.get("O3R7_authorized") is False
            and d.get("F5_dataset_generation_authorized") is False,
        )

        cut_cv_ids = [int(v) for v in a["cut_CV_ids"]]
        cut_cell_ids = [int(v) for v in a["cut_cell_ids"]]
        gate(
            "certified_cut_membership_exact_size",
            len(cut_cv_ids) == EXPECTED_CUT_CV_COUNT
            and len(cut_cell_ids) == EXPECTED_CUT_CELL_COUNT
            and CONTROLLING_CV in cut_cv_ids,
            {"CVs": len(cut_cv_ids), "cells": len(cut_cell_ids)},
        )

        stage = "R4_checkpoint_presence_binding"
        recovery = drive / R4_RECOVERY
        gate("R4_recovery_present", recovery.is_dir(), str(recovery))
        accepted0 = recovery / "accepted_iterates" / "iteration_000"
        map1 = recovery / "physical_maps" / "iteration_001"
        gate("R4_base_iterate_checkpoint_present", accepted0.is_dir(), str(accepted0))
        gate("R4_physical_map_iteration1_checkpoint_present", map1.is_dir(), str(map1))
        failp = drive / R4_FAIL / R4_FAIL_REPORT
        gate("R4_scientific_fail_preserved", failp.is_file(), str(failp))

        # ----------------------------------------------------------------------------------
        # Freeze the prospective one-step projected operator.
        # ----------------------------------------------------------------------------------
        operator = {
            "milestone": MILESTONE,
            "operator_id": "PAD_STREAM_SINGLE_CUT_LOCAL_SECANT_TANGENT_PROJECTION_V1",
            "scope": (
                "Prospective one-step computational update from the immutable R4 "
                "iteration-1 base/map pair only. Not a general nonlinear solver."
            ),
            "state_roles": {
                "S_base":
                    "R4 accepted computational iterate iteration_000; no physical-state authority.",
                "S_map":
                    "R4 iteration_001 certified PHYSICAL_MAP_CANDIDATE.",
                "d_raw":
                    "S_map - S_base. This remains the original fixed-point map direction.",
                "cut":
                    "Immutable R1-R1 certified 67-CV / 24-cell frozen-E2 minimum cut.",
                "d_projected":
                    "d_raw plus a minimum-L2 local correction on the 24 cut-cell saturation DOFs.",
            },
            "cut_definition": {
                "CV_ids": cut_cv_ids,
                "cell_ids": cut_cell_ids,
                "demand_kg": float(a["cut_demand_kg"]),
                "deficit_function":
                    "D_C(S) = demand_C - sum_{j in cut_cells} max(capacity_j(P(S)) - residual_j, 0).",
                "feasible_sign": "D_C(S) <= 0",
                "omega0_spare_capacity_kg": EXPECTED_OMEGA0_SLACK_KG,
                "omega1_over_1024_deficit_kg": EXPECTED_OMEGA1_DEFICIT_KG,
            },
            "raw_cut_secant_slope": {
                "definition":
                    "(D_C(S_base + (1/1024)d_raw) - D_C(S_base)) / (1/1024)",
                "value_kg_per_full_raw_step": EXPECTED_SECANT_SLOPE,
                "source":
                    "R1-R1 exact invariant-cut sweep; no new sub-1/1024 raw-direction search.",
            },
            "local_sensitivity_vector": {
                "dimension": EXPECTED_CUT_CELL_COUNT,
                "DOFs":
                    "one saturation DOF for each certified cut Cartesian cell",
                "definition":
                    "g_j = partial D_C / partial S_j from exact pressure/capacity probes at S_base",
                "probe_contract_file": PROBES,
            },
            "projection_rule": {
                "if_raw_secant_slope_nonpositive":
                    "q = 0 and d_projected = d_raw; no correction is needed for this cut.",
                "if_raw_secant_slope_positive":
                    "Require ||g||_2^2 > 0. Then q = -(a_raw / (g^T g)) g.",
                "projected_direction":
                    "d_projected = d_raw + E_cut q, where E_cut injects q only into the 24 cut-cell saturation DOFs.",
                "first_order_certificate":
                    "a_raw + g^T q = 0 within 1e-8 kg per full projected step.",
                "optimality":
                    "q is the unique minimum-Euclidean-norm local correction satisfying the one-cut tangent equality.",
                "no_state_authority":
                    "The projected direction and any projected trial are computational globalization objects only.",
            },
            "saturation_interval": [SATURATION_MIN, SATURATION_MAX],
            "support_domain": "unchanged frozen E2/H2",
            "CV_mass_constraints": "unchanged exact O2/R3/R4 semantics",
            "capacity_definition": "unchanged pressure-dependent local mass capacity",
            "physical_time_advance": False,
        }

        probes = {
            "milestone": MILESTONE,
            "probe_id": "PAD_STREAM_LOCAL_CUT_CAPACITY_SENSITIVITY_PROBES_V1",
            "execution_status": "NOT_EXECUTED_IN_R2_DESIGN_FREEZE",
            "base_state":
                "immutable R4 accepted computational iterate iteration_000",
            "cut_cell_count": EXPECTED_CUT_CELL_COUNT,
            "probe_size_saturation": LOCAL_SATURATION_PROBE,
            "probe_method": {
                "central_difference":
                    "Use S_j +/- 1e-5 when both perturbed values remain inside [0.20,0.80].",
                "lower_or_upper_bound":
                    "Use the single admissible inward one-sided 1e-5 probe if central probing would leave [0.20,0.80].",
                "pressure":
                    "Each probe performs the exact unchanged R4 pressure solve.",
                "pressure_residual_max": PROBE_PRESSURE_RESIDUAL_MAX,
                "capacity":
                    "Recompute unchanged pressure-dependent cell capacities and the certified cut deficit only.",
                "assignment":
                    "No five-stage assignment and no min-unserved LP is executed for sensitivity probes.",
                "state_mutation":
                    "Probe states are diagnostic only and are never accepted as computational or physical states.",
            },
            "required_before_projection": [
                "all 24 cut-cell sensitivities finite",
                "all pressure residuals < 1e-8",
                "g^T g finite and > 0 when raw cut slope is positive",
                "no saturation probe outside [0.20,0.80]",
            ],
            "forbidden": [
                "support modification",
                "capacity relaxation",
                "CV-mass relaxation",
                "using probe states as physical authority",
                "physical-time advance",
            ],
        }

        line = {
            "milestone": MILESTONE,
            "line_search_id": "PAD_STREAM_PROJECTED_DIRECTION_EXACT_FEASIBILITY_TEST_V1",
            "scope":
                "One-step prospective test only; it does not advance the nonlinear fixed-point solver.",
            "trial_definition":
                "S_trial(alpha) = S_base + alpha * d_projected",
            "trial_order": [
                "alpha=1",
                "then 1/2, 1/4, ..., 1/1024 if needed",
                "after first feasible/infeasible bracket, binary-refine on denominator-1024 grid to largest certified feasible lower endpoint",
            ],
            "exact_trial_certification": [
                "all trial saturation values inside [0.20,0.80]",
                "exact unchanged pressure solve",
                "pressure linear relative residual < 1e-8",
                "unchanged residual-sidecar capacity check",
                "exact frozen-E2 minimum-unserved LP",
                "minimum unserved <= 1e-6 kg",
                "CV equality Linf <= 1e-6 kg",
                "maximum cell capacity excess <= 1e-6 kg",
            ],
            "monotonicity_guard":
                "Any sampled infeasible->feasible reversal after the first feasible->infeasible transition is a scientific/design failure.",
            "minimum_positive_alpha":
                "1/1024. No smaller automatic projected step is authorized.",
            "PASS_condition":
                "At least one alpha >= 1/1024 is exactly frozen-E2 feasible and all projection/probe gates pass.",
            "PASS_output_classification":
                "PROSPECTIVE_PROJECTED_COMPUTATIONAL_ITERATE_CANDIDATE_ONLY",
            "PASS_does_not_mean": [
                "nonlinear fixed-point convergence",
                "physical-state authority",
                "five-stage assignment at the projected trial",
                "authorization of O3-R7",
            ],
            "FAIL_conditions": [
                "local sensitivity vector cannot be certified",
                "projected tangent condition cannot be satisfied",
                "no projected alpha >= 1/1024 is exactly feasible",
                "new sampled nonmonotonic feasibility",
                "pressure/capacity/LP certification failure",
            ],
            "no_automatic_repairs": [
                "alpha below 1/1024",
                "support expansion",
                "capacity relaxation",
                "per-CV mass relaxation",
                "mass clipping/discarding",
                "global rescaling",
                "changing the five-stage objectives",
                "physical-time advance",
            ],
        }

        convergence = {
            "milestone": MILESTONE,
            "preserved_convergence_id": "PAD_STREAM_ORIGINAL_UNDAMPED_FIXED_POINT_CLOSURE_V1",
            "R2_scope":
                "No convergence is evaluated in R2 design freeze or the authorized R3 one-step test.",
            "future_full_solver_requirement": {
                "raw_map_residual":
                    "Convergence must still use max_abs(S_map - S_iter), never the projected accepted increment.",
                "projection_inactivity":
                    "A final fixed point cannot depend on a nonzero projection correction.",
                "full_step":
                    "Final convergence must recover the original undamped/full-map closure semantics.",
                "pressure_relative_L2_max": 1.0e-10,
                "saturation_raw_fixed_point_Linf_max": 1.0e-10,
                "global_mass_relative_error_max": 1.0e-10,
                "pressure_linear_relative_residual_max": 1.0e-8,
                "per_CV_mass": "exact within the frozen execution tolerance",
                "cell_capacity": "satisfied under final pressure",
                "final_frozen_assignment_closure": "required exactly as in R3/R4",
            },
            "false_convergence_prohibited": [
                "small projected correction",
                "small alpha",
                "small projected accepted increment",
                "tangent condition alone",
                "feasible projected one-step test",
            ],
        }

        checkpoint = {
            "milestone": MILESTONE,
            "policy_id": "PAD_STREAM_PROJECTED_ONE_STEP_CHECKPOINT_POLICY_V1",
            "prospective_R3_required_checkpoints": [
                "24 immutable cut-sensitivity probe results",
                "certified local sensitivity vector g",
                "raw cut secant slope source identity",
                "projection correction q and projected direction digest",
                "every exact projected line-search feasibility point",
                "selected prospective projected candidate if PASS",
            ],
            "prospective_candidate_classification":
                "COMPUTATIONAL_TEST_CANDIDATE_ONLY",
            "restart_rule":
                "A disconnected R3 one-step test may reuse individually manifest-verified probe and line-search checkpoints; it may not reinterpret them as physical state.",
            "five_stage_assignment_checkpointing":
                "Not applicable because the authorized R3 test performs no five-stage assignment.",
            "physical_time_advance": False,
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "next_milestone": (
                "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R4-R3 — "
                "controlled single-cut projected-direction one-step feasibility test"
            ),
            "O3R6R4R3_one_step_projected_test_authorized": True,
            "O3R6R4R3_full_fixed_point_execution_authorized": False,
            "O3R6R4R3_five_stage_assignment_authorized": False,
            "automatic_R4_rerun_authorized": False,
            "sub_1_over_1024_scalar_damping_search_authorized": False,
            "sub_1_over_1024_projected_step_authorized": False,
            "support_expansion_authorized": False,
            "capacity_relaxation_authorized": False,
            "per_CV_mass_relaxation_authorized": False,
            "O3R7_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "design_only": True,
            "operator_id": operator["operator_id"],
            "certified_cut_CV_count": EXPECTED_CUT_CV_COUNT,
            "certified_cut_cell_count": EXPECTED_CUT_CELL_COUNT,
            "raw_cut_secant_slope_kg_per_full_raw_step": EXPECTED_SECANT_SLOPE,
            "projection_correction_domain": "24 certified cut-cell saturation DOFs only",
            "local_sensitivity_probe_count": EXPECTED_CUT_CELL_COUNT,
            "prospective_test_uses_existing_R4_physical_map": True,
            "prospective_test_five_stage_assignment_required": False,
            "projected_execution_performed": False,
            "pressure_probe_execution_performed": False,
            "state_mutated": False,
            "support_domain_changed": False,
            "physical_time_advanced": False,
            "R3_one_step_test_authorized": True,
            "R3_full_fixed_point_execution_authorized": False,
        }

        files = {
            SUMMARY: r3.json_bytes(summary),
            OPERATOR: r3.json_bytes(operator),
            PROBES: r3.json_bytes(probes),
            LINE: r3.json_bytes(line),
            CONVERGENCE: r3.json_bytes(convergence),
            CHECKPOINT: r3.json_bytes(checkpoint),
            DECISION: r3.json_bytes(decision),
            GATES: r3.csv_bytes([{"gate": k, **v} for k, v in gates.items()]),
        }
        r3.immutable_publish(out, files)
        rows = [
            {"file": p.name, "sha256": r3.sha256_file(p), "bytes": p.stat().st_size}
            for p in sorted(out.iterdir())
            if p.is_file() and p.name != MANIFEST
        ]
        r3.immutable_publish(out, {MANIFEST: r3.csv_bytes(rows)})

        print()
        print("=" * 214)
        print(MILESTONE + ": DESIGN FREEZE PASS")
        print("=" * 214)
        print("Operator                         :", operator["operator_id"])
        print("Certified cut CV / cell count    :", EXPECTED_CUT_CV_COUNT, "/", EXPECTED_CUT_CELL_COUNT)
        print("Local sensitivity probes         :", EXPECTED_CUT_CELL_COUNT)
        print("Existing R4 physical map reused  : True")
        print("Five-stage assignment in R3 test : False")
        print("R4-R3 one-step test authorized   : True")
        print("Full fixed-point execution       : NOT AUTHORIZED")
        print("O3-R7                           : NOT AUTHORIZED")
        print("=" * 214)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCK,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "design_only": True,
            "projected_execution_performed": False,
            "state_mutated": False,
            "support_domain_changed": False,
            "physical_time_advanced": False,
            "O3R6R4R3_one_step_projected_test_authorized": False,
            "O3R7_authorized": False,
            "F5_dataset_generation_authorized": False,
        }
        p = blocked / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R2_Blocked_Report.json"
        if not p.exists():
            p.write_bytes((json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        print()
        print(MILESTONE + ": TECHNICAL / AUTHORITY BLOCK")
        print("Stage:", stage)
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
