#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R4-R3-R2"
STATUS_PASS = (
    "AV4F4R3R3R3R3R3O3R6R4R3R2_ALPHA_DEPENDENT_BOX_CONSTRAINED_TANGENT_"
    "PROJECTION_SEMANTICS_DESIGN_FREEZE_PASS_NO_PROJECTED_EXECUTION_NO_PRESSURE_"
    "NO_LP_NO_STATE_MUTATION_NO_SUPPORT_EXPANSION_NO_TIME_ADVANCE"
)
STATUS_BLOCK = "AV4F4R3R3R3R3R3O3R6R4R3R2_TECHNICAL_OR_AUTHORITY_BLOCK"

PARENT_R3R1_COMMIT = "07dc77168814f386e9570a0026f4d67bdf03b3c8"

R3R1 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R1_"
    "Saturation_Box_Tangent_Correction_Compatibility_ReadOnly_Audit.py"
)
R3R1_BLOB = "aaf38a0a271e05b04c0d17f93ca07d2a69bdfea3"
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

R3R1_REL = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R1_"
    "Saturation_Box_Tangent_Correction_Compatibility_ReadOnly_Audit"
)
R3R1_SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R1_Summary.json"
R3R1_AUDIT = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R1_Box_Tangent_Audit.json"
R3R1_ALPHA = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R1_Box_Tangent_Alpha_Sweep.csv"
R3R1_CELL = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R1_Cut_Cell_Bound_Diagnostics.csv"
R3R1_DECISION = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R1_Decision_Contract.json"
R3R1_GATES = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R1_Final_Gate_Matrix.csv"
R3R1_MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R1_Artifact_Manifest.csv"
EXPECTED_R3R1_FILES = {
    R3R1_SUMMARY, R3R1_AUDIT, R3R1_ALPHA, R3R1_CELL, R3R1_DECISION, R3R1_GATES,
}

OUT = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R2_"
    "Alpha_Dependent_Box_Constrained_Tangent_Projection_Semantics_Design_Freeze"
)
BLOCK = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R2_BLOCKED"

SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R2_Summary.json"
OPERATOR = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R2_Alpha_Dependent_Box_Projection_Operator_Contract.json"
CANDIDATES = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R2_Candidate_Family_Contract.json"
CERTIFICATION = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R2_Exact_Candidate_Certification_Contract.json"
CONVERGENCE = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R2_Convergence_Preservation_Contract.json"
CHECKPOINT = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R2_Checkpoint_Restart_Policy.json"
DECISION = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R2_Decision_Contract.json"
GATES = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R2_Final_Gate_Matrix.csv"
MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R2_Artifact_Manifest.csv"

EXPECTED_CUT_CVS = 67
EXPECTED_CUT_CELLS = 24
MIN_ALPHA = 1.0/1024.0
LARGEST_ANALYTIC_DYADIC_ALPHA = 1.0/128.0
CANDIDATE_INDICES = [8,4,2,1]  # denominator 1024, largest first
LINE_DEN = 1024
S_MIN = 0.20
S_MAX = 0.80
A_RAW = 53.3337138146162


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


def self_test() -> None:
    assert CANDIDATE_INDICES == [8,4,2,1]
    assert CANDIDATE_INDICES[0]/LINE_DEN == LARGEST_ANALYTIC_DYADIC_ALPHA
    assert CANDIDATE_INDICES[-1]/LINE_DEN == MIN_ALPHA
    assert S_MIN < S_MAX
    assert len(PARENT_R3R1_COMMIT) == 40
    print(
        "POSTV16 O3-R6-R4-R3-R2 alpha-dependent box-constrained tangent "
        "projection design structural self-test: PASS"
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

    print("="*214)
    print(MILESTONE + " -- ALPHA-DEPENDENT BOX-CONSTRAINED TANGENT PROJECTION SEMANTICS DESIGN FREEZE")
    print("="*214)
    print("DESIGN / FREEZE ONLY.")
    print("NO PROJECTED EXECUTION. NO PRESSURE SOLVE. NO HIGHS LP. NO STATE MUTATION.")
    print("NO FIVE-STAGE ASSIGNMENT. NO SUPPORT EXPANSION. NO TIME ADVANCE.")
    print()

    try:
        stage = "repository_authority"
        parent = git_text(root, "rev-parse", "HEAD^")
        dirty = git_text(root, "status", "--porcelain")
        gate("repository_parent_is_R3R1_commit", parent == PARENT_R3R1_COMMIT, parent)
        gate("repository_clean", dirty == "", repr(dirty))

        for fn, expected in {
            R3R1:R3R1_BLOB, R3:R3_BLOB, R2:R2_BLOB, R4:R4_BLOB, R3DESIGN:R3DESIGN_BLOB
        }.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        r3r1 = load_module(root / R3R1, "postv16_o3r6r4r3r2_r3r1")
        r3design = load_module(root / R3DESIGN, "postv16_o3r6r4r3r2_r3design")

        stage = "R3R1_PASS_binding"
        d = drive / R3R1_REL
        gate("R3R1_output_present", d.is_dir(), str(d))
        manifest = r3design.verify_manifest(d, R3R1_MANIFEST)
        gate("R3R1_manifest_payload_exact", set(manifest) == EXPECTED_R3R1_FILES, sorted(manifest))

        s = r3design.load_json(d / R3R1_SUMMARY)
        a = r3design.load_json(d / R3R1_AUDIT)
        dec = r3design.load_json(d / R3R1_DECISION)

        gate(
            "R3R1_PASS_exact",
            s.get("status") == r3r1.STATUS_PASS
            and s.get("R3_scientific_fail_preserved") is True
            and s.get("R3_all_11_trials_failed_saturation_bounds_before_LP") is True
            and s.get("box_constrained_tangent_equality_feasible_at_1_over_1024") is True
            and abs(float(s.get("largest_dyadic_alpha_with_box_constrained_tangent_equality")) - LARGEST_ANALYTIC_DYADIC_ALPHA) <= 1e-15
            and abs(float(s.get("minimum_authorized_alpha")) - MIN_ALPHA) <= 1e-15
            and s.get("pressure_solve_executed") is False
            and s.get("feasibility_LP_executed") is False
            and s.get("projected_trial_executed") is False
            and s.get("state_mutated") is False
            and s.get("support_domain_changed") is False
            and s.get("physical_time_advanced") is False,
        )
        gate(
            "R3R1_authorizes_R3R2_design_only",
            dec.get("O3R6R4R3R2_bound_constrained_projection_design_freeze_authorized") is True
            and dec.get("O3R6R4R3R2_execution_authorized") is False
            and dec.get("automatic_R3_rerun_authorized") is False
            and dec.get("sub_1_over_1024_step_authorized") is False
            and dec.get("support_expansion_authorized") is False
            and dec.get("full_fixed_point_execution_authorized") is False
            and dec.get("O3R7_authorized") is False,
        )
        gate(
            "R3R1_cut_and_sensitivity_summary_exact",
            abs(float(a.get("a_raw_kg_per_full_step")) - A_RAW) <= 1e-10
            and abs(float(a.get("g_L2")) - 1.2493304995770507) <= 1e-12
            and abs(float(a.get("g_Linf")) - 0.7448965334333478) <= 1e-12,
        )

        # Freeze semantics. The correction is alpha-dependent; there is no single projected direction.
        operator = {
            "milestone":MILESTONE,
            "operator_id":"PAD_STREAM_ALPHA_DEPENDENT_BOX_CONSTRAINED_TANGENT_PROJECTION_V1",
            "scope":"Prospective one-step test from the immutable R4 iteration-1 base/map pair only.",
            "base_objects":{
                "S_base":"immutable R4 accepted computational iterate iteration_000",
                "S_map":"immutable R4 iteration_001 PHYSICAL_MAP_CANDIDATE",
                "d_raw":"S_map - S_base",
                "cut":"immutable R1-R1 67-CV / 24-cell cut",
                "g":"immutable 24-component sensitivity vector recovered from R3 probes",
                "a_raw_kg_per_full_step":A_RAW,
            },
            "critical_semantic_change":{
                "single_projected_direction":False,
                "reason":"The admissible correction box depends on alpha, so q_alpha is recomputed independently for each alpha.",
                "candidate_family":"S_trial(alpha)=S_base + alpha*(d_raw + E_cut q_alpha)",
            },
            "per_alpha_correction_problem":{
                "objective":"minimize 0.5 * ||q_alpha||_2^2",
                "tangent_constraint":"g^T q_alpha = -a_raw",
                "lower_bound":"q_alpha,j >= (S_min - S_base,j)/alpha - d_raw,j",
                "upper_bound":"q_alpha,j <= (S_max - S_base,j)/alpha - d_raw,j",
                "saturation_interval":[S_MIN,S_MAX],
                "solution_method":"deterministic scalar KKT/bisection clip form q(lambda)=clip(-lambda*g, lower, upper)",
                "required_residual":"|a_raw + g^T q_alpha| <= 1e-8 kg per full step",
                "physical_state_authority":False,
            },
            "support_domain":"unchanged frozen E2/H2",
            "capacity_definition":"unchanged pressure-dependent local mass capacity",
            "CV_mass_constraints":"unchanged exact O2/R3/R4 semantics",
            "physical_time_advance":False,
        }

        candidates = {
            "milestone":MILESTONE,
            "candidate_family_id":"PAD_STREAM_BOX_TANGENT_FOUR_CANDIDATE_FAMILY_V1",
            "denominator":LINE_DEN,
            "candidate_indices_largest_first":CANDIDATE_INDICES,
            "candidate_alphas_largest_first":[i/LINE_DEN for i in CANDIDATE_INDICES],
            "source":"R3-R1 analytical box/tangent compatibility audit",
            "largest_analytically_admissible_dyadic_alpha":LARGEST_ANALYTIC_DYADIC_ALPHA,
            "minimum_authorized_alpha":MIN_ALPHA,
            "excluded_larger_dyadic_indices":[16,32,64,128,256,512,1024],
            "excluded_larger_reason":"R3-R1 proved the tangent equality and inward inequality analytically impossible within the 24-cell correction domain.",
            "evaluation_rule":"Evaluate all four candidates independently. Do not infer monotonic feasibility because q_alpha changes with alpha.",
            "selection_rule":"Select the largest alpha among candidates that passes exact certification.",
            "no_binary_refinement":True,
            "no_sub_1_over_1024_candidate":True,
        }

        certification = {
            "milestone":MILESTONE,
            "certification_id":"PAD_STREAM_ALPHA_DEPENDENT_BOX_TANGENT_EXACT_CANDIDATE_CERTIFICATION_V1",
            "for_each_candidate":[
                "recompute q_alpha from the frozen analytical box-constrained minimum-norm problem",
                "verify tangent equality residual <= 1e-8 kg per full step",
                "verify all saturation values inside [0.20,0.80] before pressure",
                "execute exact unchanged pressure solve",
                "require pressure linear relative residual < 1e-8",
                "recompute unchanged pressure-dependent cell capacities",
                "require residual-sidecar capacity feasibility",
                "execute exact frozen-E2 minimum-unserved LP",
                "require minimum unserved <= 1e-6 kg",
                "require CV equality Linf <= 1e-6 kg",
                "require maximum cell capacity excess <= 1e-6 kg",
            ],
            "five_stage_assignment":"NOT EXECUTED",
            "candidate_authority":"PROSPECTIVE_COMPUTATIONAL_TEST_CANDIDATE_ONLY",
            "candidate_independence":"No monotonicity guard across alpha because the four q_alpha define different directions.",
            "PASS_condition":"At least one of the four alpha-dependent candidates is exactly frozen-E2 feasible.",
            "FAIL_condition":"None of the four candidates is exactly feasible, or any projection/pressure/LP certification gate fails.",
            "forbidden_repairs":[
                "alpha below 1/1024",
                "support expansion",
                "capacity relaxation",
                "per-CV mass relaxation",
                "mass clipping/discarding",
                "global rescaling",
                "changing five-stage objectives",
                "physical-time advance",
            ],
        }

        convergence = {
            "milestone":MILESTONE,
            "preserved_convergence_id":"PAD_STREAM_ORIGINAL_UNDAMPED_FIXED_POINT_CLOSURE_V1",
            "R3R3_scope":"One-step prospective test only; no nonlinear convergence claim.",
            "future_full_solver_requirements":[
                "raw residual max_abs(S_map-S_iter), never projected increment",
                "projection corrections must vanish/become inactive at the certified fixed point",
                "final convergence recovers original undamped/full-map semantics",
                "pressure relative L2 <= 1e-10",
                "raw saturation fixed-point Linf <= 1e-10",
                "global mass relative error <= 1e-10",
                "pressure linear relative residual < 1e-8",
                "exact per-CV mass and final pressure-dependent capacity closure",
                "final frozen-assignment recertification",
            ],
            "false_convergence_prohibited":[
                "small alpha",
                "small q_alpha",
                "box activity",
                "tangent equality",
                "one-step exact feasibility",
            ],
        }

        checkpoint = {
            "milestone":MILESTONE,
            "policy_id":"PAD_STREAM_ALPHA_DEPENDENT_BOX_TANGENT_ONE_STEP_CHECKPOINT_POLICY_V1",
            "prospective_R3R3_checkpoints":[
                "reused R3 24-component sensitivity vector identity",
                "per-alpha q_alpha and bound-active-set metadata for all evaluated candidates",
                "per-alpha exact pressure/capacity state",
                "per-alpha frozen-E2 minimum-unserved LP result",
                "selected largest exactly feasible candidate if PASS",
            ],
            "restart_rule":"Only individually manifest-verified candidate checkpoints may be reused.",
            "candidate_state_authority":False,
            "five_stage_assignment_checkpointing":"not applicable",
            "physical_time_advance":False,
        }

        decision = {
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "next_milestone":(
                "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R4-R3-R3 — "
                "controlled alpha-dependent box-constrained tangent candidate feasibility test"
            ),
            "O3R6R4R3R3_controlled_candidate_test_authorized":True,
            "O3R6R4R3R3_full_fixed_point_execution_authorized":False,
            "O3R6R4R3R3_five_stage_assignment_authorized":False,
            "automatic_R3_rerun_authorized":False,
            "sub_1_over_1024_step_authorized":False,
            "support_expansion_authorized":False,
            "capacity_relaxation_authorized":False,
            "per_CV_mass_relaxation_authorized":False,
            "O3R7_authorized":False,
            "F5_dataset_generation_authorized":False,
            "training_authorized":False,
        }

        summary = {
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "design_only":True,
            "operator_id":operator["operator_id"],
            "candidate_family_id":candidates["candidate_family_id"],
            "candidate_count":4,
            "candidate_indices_largest_first":CANDIDATE_INDICES,
            "candidate_alphas_largest_first":[i/LINE_DEN for i in CANDIDATE_INDICES],
            "single_projected_direction":False,
            "alpha_dependent_correction":True,
            "monotonic_line_search_assumption":False,
            "pressure_solve_executed":False,
            "feasibility_LP_executed":False,
            "projected_execution_performed":False,
            "five_stage_assignment_executed":False,
            "state_mutated":False,
            "support_domain_changed":False,
            "physical_time_advanced":False,
            "R3R3_candidate_test_authorized":True,
            "R3R3_full_fixed_point_execution_authorized":False,
        }

        files = {
            SUMMARY:r3design.json_bytes(summary),
            OPERATOR:r3design.json_bytes(operator),
            CANDIDATES:r3design.json_bytes(candidates),
            CERTIFICATION:r3design.json_bytes(certification),
            CONVERGENCE:r3design.json_bytes(convergence),
            CHECKPOINT:r3design.json_bytes(checkpoint),
            DECISION:r3design.json_bytes(decision),
            GATES:r3design.csv_bytes([{"gate":k,**v} for k,v in gates.items()]),
        }
        r3design.immutable_publish(out,files)
        rows = [
            {"file":p.name,"sha256":r3design.sha256_file(p),"bytes":p.stat().st_size}
            for p in sorted(out.iterdir()) if p.is_file() and p.name != MANIFEST
        ]
        r3design.immutable_publish(out,{MANIFEST:r3design.csv_bytes(rows)})

        print()
        print("="*214)
        print(MILESTONE + ": DESIGN FREEZE PASS")
        print("="*214)
        print("Operator                      :", operator["operator_id"])
        print("Single projected direction    : False")
        print("Alpha-dependent q             : True")
        print("Candidates                    :", [i/LINE_DEN for i in CANDIDATE_INDICES])
        print("Monotonic line-search assumed : False")
        print("R3-R3 candidate test          : AUTHORIZED")
        print("Full fixed-point execution    : NOT AUTHORIZED")
        print("Five-stage assignment         : NOT AUTHORIZED")
        print("O3-R7                         : NOT AUTHORIZED")
        print("="*214)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        report = {
            "milestone":MILESTONE,
            "status":STATUS_BLOCK,
            "failed_stage":stage,
            "exception":repr(exc),
            "gates":gates,
            "design_only":True,
            "projected_execution_performed":False,
            "pressure_solve_executed":False,
            "feasibility_LP_executed":False,
            "five_stage_assignment_executed":False,
            "state_mutated":False,
            "support_domain_changed":False,
            "physical_time_advanced":False,
            "O3R6R4R3R3_controlled_candidate_test_authorized":False,
            "O3R7_authorized":False,
        }
        p = blocked / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R4R3R2_Blocked_Report.json"
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
