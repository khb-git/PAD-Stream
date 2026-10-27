#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R4-R3-R4"
STATUS_PASS = (
    "AV4F4R3R3R3R3R3O3R6R4R3R4_GENERALIZED_ACTIVE_SET_BOX_CONSTRAINED_"
    "PROJECTED_COUPLED_SOLVER_SEMANTICS_DESIGN_FREEZE_PASS_NO_GENERALIZED_"
    "EXECUTION_NO_STATE_MUTATION_NO_SUPPORT_EXPANSION_NO_TIME_ADVANCE"
)
STATUS_BLOCK = "AV4F4R3R3R3R3R3O3R6R4R3R4_TECHNICAL_OR_AUTHORITY_BLOCK"

PARENT_R3R3_COMMIT = "c3d90dc0044e16364436c2968b43fd20e2c80087"

R3R3 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R3_"
    "Controlled_AlphaDependent_BoxConstrained_Tangent_Candidate_Feasibility_Test.py"
)
R3R3_BLOB = "9d10e50f49af402634db0f22e8f29899076eb6da"
R3R2 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R2_"
    "Alpha_Dependent_Box_Constrained_Tangent_Projection_Semantics_Design_Freeze.py"
)
R3R2_BLOB = "4e5b643ed212ef3432d43026993931325256d28a"
R3R1 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R1_"
    "Saturation_Box_Tangent_Correction_Compatibility_ReadOnly_Audit.py"
)
R3R1_BLOB = "aaf38a0a271e05b04c0d17f93ca07d2a69bdfea3"
R4 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4_"
    "Controlled_Adaptive_Feasibility_Preserving_Stabilized_Coupled_Execution.py"
)
R4_BLOB = "c41cd5c78e7cc2d91e1920e538f1793037961a31"
R1R1 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R1R1_"
    "CV60424_ActiveCut_Boundary_Semantics_Repair_and_Certification.py"
)
R1R1_BLOB = "e0da9d713db9cb40c0883ed17c54736f532b9f5c"
R3DESIGN = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R3_"
    "Adaptive_Feasibility_Preserving_Stabilization_Semantics_Design_Freeze.py"
)
R3DESIGN_BLOB = "c118972a991e4ae0ce7200a9f880a73407450b8b"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R3R3_REL = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R3_"
    "Controlled_AlphaDependent_BoxConstrained_Tangent_Candidate_Feasibility_Test"
)

OUT = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R4_"
    "Generalized_ActiveSet_BoxConstrained_Projected_CoupledSolver_Semantics_Design_Freeze"
)
BLOCK = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R4_BLOCKED"

SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R4_Summary.json"
OPERATOR = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R4_Generalized_ActiveSet_Operator_Contract.json"
CUTS = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R4_Cut_Separation_and_Sensitivity_Contract.json"
ALPHA = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R4_Alpha_Candidate_and_Selection_Contract.json"
QP = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R4_BoxConstrained_MultiCut_QP_Contract.json"
CONVERGENCE = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R4_Convergence_and_Final_Closure_Contract.json"
CHECKPOINT = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R4_Checkpoint_Restart_Policy.json"
FAILURE = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R4_Failure_Semantics.json"
DECISION = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R4_Decision_Contract.json"
GATES = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R4_Final_Gate_Matrix.csv"
MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R4_Artifact_Manifest.csv"

LINE_DEN = 1024
ALPHA_INDICES = [1024,512,256,128,64,32,16,8,4,2,1]
MAX_ACTIVE_CUT_ROUNDS_PER_ALPHA = 32
SAT_MIN = 0.20
SAT_MAX = 0.80
SENSITIVITY_STEP = 1.0e-5
RAW_SECANT_EPSILON = 1.0/1024.0
TANGENT_INEQUALITY_TOL_KG_PER_FULL_STEP = 1.0e-8
PRESSURE_RESIDUAL_TOL = 1.0e-8
FEAS_UNSERVED_TOL_KG = 1.0e-6
FEAS_CV_LINF_TOL_KG = 1.0e-6
FEAS_CAP_EXCESS_TOL_KG = 1.0e-6
MAX_NONLINEAR_ITERATIONS = 100


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
        ["git","-C",str(root),*args],
        check=True,text=True,capture_output=True
    ).stdout.strip()


def git_blob(path: Path, root: Path) -> str:
    return git_text(root,"hash-object",str(path))


def self_test() -> None:
    assert ALPHA_INDICES[0] == 1024 and ALPHA_INDICES[-1] == 1
    assert [i/LINE_DEN for i in ALPHA_INDICES[:4]] == [1.0,0.5,0.25,0.125]
    assert RAW_SECANT_EPSILON == 1.0/1024.0
    assert SAT_MIN < SAT_MAX
    assert MAX_ACTIVE_CUT_ROUNDS_PER_ALPHA >= 1
    assert len(PARENT_R3R3_COMMIT) == 40
    print(
        "POSTV16 O3-R6-R4-R3-R4 generalized active-set projected solver "
        "design structural self-test: PASS"
    )


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT
    blocked = drive / BLOCK
    gates: dict[str,dict[str,Any]] = {}
    stage = "preflight"

    def gate(name: str, cond: bool, detail: Any=None):
        gates[name] = {"status":"PASS" if cond else "FAIL","detail":detail}
        if not cond:
            raise GateError(f"{name}: {detail!r}")
        print(f"[PASS] {name}" + (f" -- {detail}" if detail is not None else ""))

    print("="*214)
    print(MILESTONE+" -- GENERALIZED ACTIVE-SET BOX-CONSTRAINED PROJECTED COUPLED-SOLVER SEMANTICS DESIGN FREEZE")
    print("="*214)
    print("DESIGN / FREEZE ONLY.")
    print("NO GENERALIZED ACTIVE-SET EXECUTION. NO FIVE-STAGE ASSIGNMENT. NO PRESSURE/LP/QP EXECUTION.")
    print("NO STATE MUTATION. NO SUPPORT EXPANSION. NO TIME ADVANCE.")
    print()

    try:
        stage = "repository_authority"
        parent=git_text(root,"rev-parse","HEAD^")
        dirty=git_text(root,"status","--porcelain")
        gate("repository_parent_is_R3R3_commit",parent==PARENT_R3R3_COMMIT,parent)
        gate("repository_clean",dirty=="",repr(dirty))

        for fn,expected in {
            R3R3:R3R3_BLOB,R3R2:R3R2_BLOB,R3R1:R3R1_BLOB,R4:R4_BLOB,
            R1R1:R1R1_BLOB,R3DESIGN:R3DESIGN_BLOB,
        }.items():
            p=root/fn
            actual=git_blob(p,root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==expected,actual)

        r3r3=load_module(root/R3R3,"postv16_o3r6r4r3r4_r3r3")
        r3design=load_module(root/R3DESIGN,"postv16_o3r6r4r3r4_r3design")

        stage = "R3R3_PASS_binding"
        d=drive/R3R3_REL
        gate("R3R3_output_present",d.is_dir(),str(d))
        manifest=r3design.verify_manifest(d,r3r3.MANIFEST)
        expected_files={r3r3.SUMMARY,r3r3.STATE,r3r3.CANDIDATE_CSV,r3r3.DECISION,r3r3.GATES}
        gate("R3R3_manifest_payload_exact",set(manifest)==expected_files,sorted(manifest))

        s=r3design.load_json(d/r3r3.SUMMARY)
        dec=r3design.load_json(d/r3r3.DECISION)
        gate(
            "R3R3_PASS_exact",
            s.get("status")==r3r3.STATUS_PASS
            and s.get("candidate_indices_evaluated")==[8,4,2,1]
            and s.get("feasible_candidate_indices")==[4,2,1]
            and int(s.get("selected_alpha_index",-1))==4
            and abs(float(s.get("selected_alpha"))-1.0/256.0)<=1e-15
            and abs(float(s.get("selected_minimum_unserved_mass_kg"))-0.0)<=1e-15
            and abs(float(s.get("selected_cut_signed_deficit_kg"))-(-0.024434776074485853))<=1e-12
            and s.get("pressure_solve_executed") is True
            and s.get("feasibility_LP_executed") is True
            and s.get("five_stage_assignment_executed") is False
            and s.get("full_fixed_point_execution_performed") is False
            and s.get("prospective_candidate_physical_state_authority") is False
            and s.get("support_domain_changed") is False
            and s.get("physical_time_advanced") is False,
        )
        gate(
            "R3R3_authorizes_R3R4_design_only",
            dec.get("O3R6R4R3R4_generalized_solver_design_freeze_authorized") is True
            and dec.get("O3R6R4R3R4_execution_authorized") is False
            and dec.get("full_fixed_point_execution_authorized") is False
            and dec.get("five_stage_assignment_execution_authorized") is False
            and dec.get("selected_prospective_candidate_acceptance_authorized") is False
            and dec.get("automatic_R3R3_rerun_authorized") is False
            and dec.get("support_expansion_authorized") is False
            and dec.get("O3R7_authorized") is False,
        )

        # Freeze generalized solver semantics.
        operator={
            "milestone":MILESTONE,
            "operator_id":"PAD_STREAM_GENERALIZED_ACTIVE_SET_BOX_PROJECTED_FIXED_POINT_V1",
            "scope":"Same-time nonlinear fixed-point globalization only; physical-time advance remains forbidden.",
            "state_roles":{
                "S_iter_k":"computational pressure-driving iterate only",
                "P_map_k":"exact unchanged pressure solution from S_iter_k",
                "x_map_k":"exact unchanged five-stage frozen-E2 assignment at P_map_k",
                "S_map_k":"exact EOS physical-map candidate F(S_iter_k)",
                "d_raw_k":"S_map_k - S_iter_k",
                "S_trial":"prospective computational globalization candidate only",
            },
            "exact_physical_map":{
                "sequence":[
                    "spatial mobility from S_iter_k",
                    "exact unchanged pressure solve",
                    "unchanged residual/capacity construction",
                    "unchanged exact O2 five-stage frozen-E2 lexicographic assignment",
                    "exact residual + mapped Cartesian mass",
                    "exact EOS inversion to S_map_k",
                    "physical-map checkpoint before globalization",
                ],
                "support":"frozen E2/H2 only",
                "objectives":"unchanged O2 five-stage lexicographic objectives",
                "physical_state_authority":"S_map_k is a physical-map candidate; accepted projected iterates are not",
            },
            "globalization":{
                "method":"largest-first dyadic alpha-dependent active-set box-constrained projection",
                "alpha_contract_file":ALPHA,
                "cut_contract_file":CUTS,
                "QP_contract_file":QP,
            },
            "physical_time_advance":False,
        }

        cuts={
            "milestone":MILESTONE,
            "cut_separation_id":"PAD_STREAM_EXACT_FROZEN_E2_RESIDUAL_MINCUT_SEPARATION_V1",
            "cut_deficit":"D_C(S)=sum_{cv in C} demand_cv - sum_{cell in J_C} available_capacity_cell(P(S))",
            "feasible_sign":"D_C(S) <= 0",
            "cut_identity":"SHA256 of sorted cut CV IDs plus sorted cut cell IDs",
            "separation_source":"residual-network minimum cut reconstructed from the exact minimum-unserved LP solution",
            "active_cut_pool":{
                "initialization":"empty, optionally seeded by prior candidate/iteration cuts as computational warm starts only",
                "authority":"no cut is authoritative without current-state exact LP recertification",
                "novel_cut_action":"add cut identity to active pool and enlarge correction-DOF union by its cut cells",
                "duplicate_cut_action":"current alpha is declared linearization-stalled and is abandoned for the next smaller alpha",
                "maximum_novel_cut_rounds_per_alpha":MAX_ACTIVE_CUT_ROUNDS_PER_ALPHA,
                "round_limit_action":"current alpha fails; proceed to next smaller alpha; no support expansion",
            },
            "correction_DOF_domain":"union of Cartesian cells belonging to all currently active cuts; this is not E2/H2 support expansion",
            "raw_direction_secant":{
                "epsilon":RAW_SECANT_EPSILON,
                "definition":"a_C = [D_C(S_iter + epsilon*d_raw) - D_C(S_iter)] / epsilon",
                "reason":"preserves the validated R1-R1/R3 secant treatment of the raw direction",
                "shared_probe":"the same raw-direction pressure/capacity probe is reused for every cut in the current nonlinear iteration",
            },
            "local_sensitivity":{
                "definition":"g_C,j = partial D_C / partial S_j at S_iter",
                "probe_step_saturation":SENSITIVITY_STEP,
                "central":"S_j +/- 1e-5 when both remain in [0.20,0.80]",
                "bound_case":"single admissible inward one-sided 1e-5 probe",
                "DOF_columns":"all cells in the current active-cut union, including cross-cut pressure coupling",
                "probe_cache":"one pressure/capacity probe pair per correction DOF can update sensitivities for every active cut",
                "pressure_residual_required_lt":PRESSURE_RESIDUAL_TOL,
            },
            "forbidden":[
                "tolerance graph pruning",
                "support expansion",
                "capacity relaxation",
                "per-CV mass relaxation",
                "mass clipping or discard",
                "global mass rescaling",
                "physical-time advance",
            ],
        }

        qp={
            "milestone":MILESTONE,
            "QP_id":"PAD_STREAM_MULTICUT_MINIMUM_NORM_BOX_QP_V1",
            "solver":"native HiGHS 1.15.1 convex QP; successor execution must pass a deterministic tiny-QP API/solution self-test before expensive work",
            "variables":"q_j on the current active-cut correction-DOF union",
            "objective":"minimize 0.5 * q^T q",
            "cut_rows":"for every active cut C: a_C + g_C^T q <= 0",
            "variable_bounds":{
                "lower":"(S_min - S_iter,j)/alpha - d_raw,j",
                "upper":"(S_max - S_iter,j)/alpha - d_raw,j",
                "S_min":SAT_MIN,
                "S_max":SAT_MAX,
            },
            "row_residual_tolerance_kg_per_full_step":TANGENT_INEQUALITY_TOL_KG_PER_FULL_STEP,
            "bound_tolerance_saturation":1.0e-10,
            "empty_cut_pool":"q=0 exactly",
            "QP_infeasible_action":"current alpha fails; proceed to next smaller alpha",
            "QP_solution_authority":"computational globalization object only",
        }

        alpha={
            "milestone":MILESTONE,
            "candidate_id":"PAD_STREAM_GENERALIZED_DYADIC_ALPHA_FAMILY_V1",
            "denominator":LINE_DEN,
            "indices_largest_first":ALPHA_INDICES,
            "alphas_largest_first":[i/LINE_DEN for i in ALPHA_INDICES],
            "per_alpha_algorithm":[
                "start/reuse a non-authoritative cut warm-start pool",
                "solve the current box-constrained multi-cut minimum-norm QP",
                "form S_trial = S_iter + alpha*(d_raw + E_union*q)",
                "verify saturation box exactly",
                "execute exact unchanged pressure/capacity calculation",
                "execute exact frozen-E2 minimum-unserved LP",
                "if LP feasible: certify candidate and stop; this is the largest feasible alpha",
                "if LP infeasible: reconstruct residual minimum cut",
                "if cut is novel and active-cut round limit not reached: add cut, update/augment cached sensitivities, and repeat same alpha",
                "if cut is duplicate, QP is infeasible, or round limit reached: abandon this alpha and continue smaller",
            ],
            "exact_candidate_feasibility":{
                "minimum_unserved_mass_kg_max":FEAS_UNSERVED_TOL_KG,
                "CV_equality_Linf_kg_max":FEAS_CV_LINF_TOL_KG,
                "maximum_cell_capacity_excess_kg_max":FEAS_CAP_EXCESS_TOL_KG,
                "pressure_linear_relative_residual_max":PRESSURE_RESIDUAL_TOL,
            },
            "monotonicity_assumption":False,
            "reason_no_monotonicity":"each alpha can have a different active-cut pool and different QP correction direction",
            "selection":"first exactly feasible candidate in largest-first order",
            "minimum_alpha":1.0/LINE_DEN,
            "below_minimum_alpha":"forbidden",
            "no_feasible_alpha_action":"scientific FAIL; no automatic support expansion or smaller step",
        }

        convergence={
            "milestone":MILESTONE,
            "convergence_id":"PAD_STREAM_ORIGINAL_UNDAMPED_FIXED_POINT_PRESERVATION_V2",
            "maximum_nonlinear_iterations":MAX_NONLINEAR_ITERATIONS,
            "required_final_conditions":[
                "selected alpha exactly 1",
                "projection correction q is identically zero within Linf <= 1e-12",
                "raw fixed-point saturation residual max_abs(S_map-S_iter) <= 1e-10",
                "pressure relative L2 drift <= 1e-10",
                "grid/global mass criteria unchanged from R3/R4",
                "exact per-CV mass closure",
                "pressure-dependent cell-capacity closure",
                "pressure linear relative residual < 1e-8",
            ],
            "raw_residual_definition":"max_abs(S_map_k - S_iter_k); never the projected accepted increment",
            "false_convergence_prohibited":[
                "small alpha",
                "small projected increment",
                "small or active QP correction",
                "feasible projected candidate",
                "stable active-cut pool",
                "small cut deficit alone",
            ],
            "final_closure":[
                "freeze converged exact five-stage assignment",
                "one final unchanged pressure solve",
                "pressure relative drift <= 1e-10",
                "recompute final capacities under final pressure",
                "frozen mapped mass remains feasible",
                "EOS inversion of identical final mass",
                "saturation drift <= 1e-10",
                "exact CV/global mass closure",
            ],
            "fixed_point_preservation":"projection is a globalization device only and must vanish before PASS",
            "physical_time_advance":False,
        }

        checkpoint={
            "milestone":MILESTONE,
            "policy_id":"PAD_STREAM_GENERALIZED_ACTIVE_SET_CHECKPOINT_POLICY_V1",
            "inherits":"PAD_STREAM_DURABLE_CHECKPOINT_POLICY_V2_STABILIZED_SOLVER",
            "required_checkpoints":[
                "all five lexicographic assignment stages of every expensive physical-map evaluation",
                "every exact physical-map candidate",
                "raw-direction epsilon pressure/capacity probe per nonlinear iteration",
                "each saturation sensitivity probe state keyed by nonlinear iteration and flat cell",
                "each active cut identity and membership",
                "each candidate alpha / active-set round QP state and solution",
                "each candidate exact pressure/capacity state",
                "each exact min-unserved LP result and reconstructed cut",
                "accepted computational iterate",
            ],
            "restart_rules":[
                "rebuild exact model and current active-cut QP from immutable metadata",
                "validate every reused manifest and source identity",
                "reused prior-iteration cuts are warm starts only and receive current exact recertification",
                "never promote a projected candidate to physical-state authority",
                "never rerun automatically after immutable PASS/FAIL/BLOCK",
            ],
            "physical_time_advance":False,
        }

        failure={
            "milestone":MILESTONE,
            "scientific_fail_conditions":[
                "no alpha >= 1/1024 can be exactly frozen-E2 feasible",
                "active-set QP is infeasible for every authorized alpha",
                "a duplicate current-state minimum cut reappears after its constraint is active and no smaller alpha succeeds",
                "maximum active-cut rounds are exhausted and no smaller alpha succeeds",
                "pressure/capacity physics fail certification",
                "exact min-unserved LP certification fails scientifically",
                "maximum nonlinear iterations reached without original fixed-point convergence",
                "final undamped closure fails",
            ],
            "technical_block_conditions":[
                "source/provenance mismatch",
                "checkpoint/manifest corruption",
                "HiGHS QP/LP API integrity failure",
                "unexpected runtime/code exception",
            ],
            "automatic_rerun_after_final_outcome":False,
            "support_expansion_after_failure":False,
            "tolerance_relaxation_after_failure":False,
            "physical_time_advance_after_failure":False,
        }

        decision={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "next_milestone":(
                "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R4-R3-R5 — "
                "controlled generalized active-set one-step separation-loop validation"
            ),
            "O3R6R4R3R5_one_step_active_set_validation_authorized":True,
            "O3R6R4R3R5_full_fixed_point_execution_authorized":False,
            "O3R6R4R3R5_five_stage_assignment_authorized":False,
            "full_generalized_solver_execution_authorized":False,
            "automatic_R3R3_rerun_authorized":False,
            "sub_1_over_1024_step_authorized":False,
            "support_expansion_authorized":False,
            "capacity_relaxation_authorized":False,
            "per_CV_mass_relaxation_authorized":False,
            "O3R7_authorized":False,
            "R3R3R4_authorized":False,
            "F5_dataset_generation_authorized":False,
            "training_authorized":False,
        }

        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "design_only":True,
            "operator_id":operator["operator_id"],
            "generalized_active_set":True,
            "multi_cut_QP":True,
            "full_dyadic_alpha_family":[i/LINE_DEN for i in ALPHA_INDICES],
            "maximum_active_cut_rounds_per_alpha":MAX_ACTIVE_CUT_ROUNDS_PER_ALPHA,
            "raw_secant_epsilon":RAW_SECANT_EPSILON,
            "sensitivity_probe_step":SENSITIVITY_STEP,
            "projection_must_vanish_for_final_PASS":True,
            "generalized_execution_performed":False,
            "pressure_solve_executed":False,
            "feasibility_LP_executed":False,
            "QP_executed":False,
            "five_stage_assignment_executed":False,
            "state_mutated":False,
            "support_domain_changed":False,
            "physical_time_advanced":False,
            "R3R5_one_step_validation_authorized":True,
            "full_generalized_solver_execution_authorized":False,
        }

        files={
            SUMMARY:r3design.json_bytes(summary),
            OPERATOR:r3design.json_bytes(operator),
            CUTS:r3design.json_bytes(cuts),
            ALPHA:r3design.json_bytes(alpha),
            QP:r3design.json_bytes(qp),
            CONVERGENCE:r3design.json_bytes(convergence),
            CHECKPOINT:r3design.json_bytes(checkpoint),
            FAILURE:r3design.json_bytes(failure),
            DECISION:r3design.json_bytes(decision),
            GATES:r3design.csv_bytes([{"gate":k,**v} for k,v in gates.items()]),
        }
        r3design.immutable_publish(out,files)
        rows=[
            {"file":p.name,"sha256":r3design.sha256_file(p),"bytes":p.stat().st_size}
            for p in sorted(out.iterdir()) if p.is_file() and p.name!=MANIFEST
        ]
        r3design.immutable_publish(out,{MANIFEST:r3design.csv_bytes(rows)})

        print()
        print("="*214)
        print(MILESTONE+": DESIGN FREEZE PASS")
        print("="*214)
        print("Operator                         :",operator["operator_id"])
        print("Generalized active-set           : True")
        print("Multi-cut minimum-norm box QP    : True")
        print("Alpha family                     :",[i/LINE_DEN for i in ALPHA_INDICES])
        print("Max novel cuts / alpha           :",MAX_ACTIVE_CUT_ROUNDS_PER_ALPHA)
        print("Projection must vanish at PASS   : True")
        print("R3-R5 one-step validation        : AUTHORIZED")
        print("Full generalized execution       : NOT AUTHORIZED")
        print("Five-stage assignment in R3-R5   : NOT AUTHORIZED")
        print("O3-R7                            : NOT AUTHORIZED")
        print("="*214)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        report={
            "milestone":MILESTONE,
            "status":STATUS_BLOCK,
            "failed_stage":stage,
            "exception":repr(exc),
            "gates":gates,
            "design_only":True,
            "generalized_execution_performed":False,
            "state_mutated":False,
            "support_domain_changed":False,
            "physical_time_advanced":False,
            "O3R6R4R3R5_one_step_active_set_validation_authorized":False,
            "O3R7_authorized":False,
        }
        p=blocked/"POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R4_Blocked_Report.json"
        if not p.exists():
            p.write_bytes((json.dumps(report,indent=2,sort_keys=True)+"\n").encode())
        print()
        print(MILESTONE+": TECHNICAL / AUTHORITY BLOCK")
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
