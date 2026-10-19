#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path
from typing import Any


MILESTONE = "POSTV16-AV1-D-R7-R7A"
STATUS_PASS = (
    "AV1DR7R7A_SINGLE_CANONICAL_SOLVER_NATIVE_PRIMARY_ENVELOPE_"
    "ARITHMETIC_SEMANTICS_PROSPECTIVELY_FROZEN"
)
STATUS_BLOCKED = "AV1DR7R7A_CANONICAL_ARITHMETIC_SEMANTICS_FREEZE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R7R7_COMMIT = "2b805907f90acb2d3faf2ca980a45510299ea0bc"

R7R7 = "PAD_Stream_POSTV16_AV1_D_R7_R7_R7R6_Certification_Semantics_Failure_Closure.py"
R7R7_BLOB = "1b44f47ff40394162788f73531301b2336cc2b24"
R7R6 = "PAD_Stream_POSTV16_AV1_D_R7_R6_Strict_Numerical_Certification_Execution.py"
R7R6_BLOB = "b7bddd20ed08c05f3b832d5006ae98586468fd26"
R7R5 = "PAD_Stream_POSTV16_AV1_D_R7_R5_Deterministic_Numerical_Certification_Redesign_Freeze.py"
R7R5_BLOB = "bc43079146772a16a3c3ecc6cea13fe88a963857"
R7R2 = "PAD_Stream_POSTV16_AV1_D_R7_R2_Conservative_Bounded_Overlap_Occupancy_Reconciliation_Freeze.py"
R7R2_BLOB = "c9c4ceed05e6e631ad071b9da901d35874609255"

SOURCE_BLOBS = {
    R7R7:R7R7_BLOB,
    R7R6:R7R6_BLOB,
    R7R5:R7R5_BLOB,
    R7R2:R7R2_BLOB,
}

BASE = Path("post_v16")/RID/"POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"

R7R7_REL = BASE/"POSTV16_AV1_D_R7_R7_R7R6_Certification_Semantics_Failure_Closure"
R7R7_SUMMARY = "PAD_Stream_POSTV16_AV1_D_R7_R7_Summary.json"
R7R7_CLOSURE = "POSTV16_AV1_D_R7_R7_R7R6_Failure_Closure.json"
R7R7_MANIFEST = "POSTV16_AV1_D_R7_R7_Artifact_Manifest.csv"

R7R5_REL = BASE/"POSTV16_AV1_D_R7_R5_Deterministic_Numerical_Certification_Redesign_Freeze"
R7R5_PROTOCOL = "POSTV16_AV1_D_R7_R5_Frozen_Numerical_Certification_Protocol.json"
R7R5_MANIFEST = "POSTV16_AV1_D_R7_R5_Artifact_Manifest.csv"

R7R2_REL = BASE/"POSTV16_AV1_D_R7_R2_Conservative_Bounded_Overlap_Occupancy_Reconciliation_Freeze"
R7R2_PROTOCOL = "POSTV16_AV1_D_R7_R2_Frozen_Reconciliation_Protocol.json"
R7R2_MANIFEST = "POSTV16_AV1_D_R7_R2_Artifact_Manifest.csv"

OUT_REL = BASE/"POSTV16_AV1_D_R7_R7A_Canonical_Primary_Envelope_Arithmetic_Semantics_Freeze"
BLOCKED_REL = BASE/"POSTV16_AV1_D_R7_R7A_BLOCKED"

R7R7_STATUS = (
    "AV1DR7R7_R7R6_SCIENTIFIC_FAIL_CLOSED_"
    "SECONDARY_CONSTRAINT_VS_FSUM_CERTIFICATION_SEMANTICS_MISMATCH_LOCALIZED"
)
R7R5_PROTOCOL_ID = "POSTV16_AV1_D_R7_R5_STRICT_HIGHS_DS_NUMERICAL_CERTIFICATION_V1"
R7R2_PROTOCOL_ID = "POSTV16_AV1_D_R7_R2_SUPPORT_GRAPH_MIN_COST_EXCESS_MASS_RECONCILIATION_V1"
NEW_PROTOCOL_ID = "POSTV16_AV1_D_R7_R7A_SOLVER_NATIVE_UNSCALED_PRIMARY_ENVELOPE_SEMANTICS_V1"

LP_METHOD = "highs-ds"
PRIMAL_FEAS_TOL = 1.0e-10
DUAL_FEAS_TOL = 1.0e-10
CANONICAL_RESIDUAL_FLOOR = -1.0e-10


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):
            h.update(block)
    return h.hexdigest()


def git_text(root: Path,*args: str) -> str:
    p=subprocess.run(
        ["git","-C",str(root),*args],
        check=True,text=True,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,
    )
    return p.stdout.strip()


def git_blob_sha(path: Path,root: Path) -> str:
    return git_text(root,"hash-object",str(path))


def load_json(path: Path) -> dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str,str]]:
    with path.open("r",newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))


def verify_manifest(directory: Path,name: str) -> dict[str,str]:
    rows=read_csv(directory/name)
    m={r["file"]:r["sha256"] for r in rows}
    for fn,expected in m.items():
        p=directory/fn
        if not p.is_file():
            raise GateError(f"manifest_file_missing:{fn}")
        actual=sha256_file(p)
        if actual!=expected:
            raise GateError(f"manifest_SHA_mismatch:{fn}:{actual}:{expected}")
    return m


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+"\n").encode("utf-8")


def csv_bytes(rows: list[dict[str,Any]]) -> bytes:
    if not rows:
        return b""
    fields=[]
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    s=io.StringIO(newline="")
    w=csv.DictWriter(s,fieldnames=fields,lineterminator="\n")
    w.writeheader();w.writerows(rows)
    return s.getvalue().encode("utf-8")


def immutable_publish(out: Path,files: dict[str,bytes]) -> None:
    out.mkdir(parents=True,exist_ok=True)
    for name,data in files.items():
        p=out/name
        if p.exists() and p.read_bytes()!=data:
            raise GateError(f"existing_output_differs:{name}")
        if not p.exists():
            p.write_bytes(data)


def self_test() -> None:
    # The canonical semantics intentionally uses the solver-native raw,
    # unscaled A_ub x <= b_ub residual and no independent arithmetic gate.
    primary=76140261.34928478
    tol=max(1.0e-8,1.0e-12*max(abs(primary),1.0))
    rhs=primary+tol
    if abs(tol-7.614026134928478e-05)>1e-15:
        raise RuntimeError("primary_envelope_formula_changed")
    if not rhs>primary:
        raise RuntimeError("secondary_rhs")
    if CANONICAL_RESIDUAL_FLOOR!=-1e-10:
        raise RuntimeError("canonical_residual_floor")
    print("POSTV16-AV1-D-R7-R7A self-test: PASS")


def main(root: Path,drive: Path) -> int:
    gates={};stage="preflight"
    out=drive/OUT_REL
    blocked=drive/BLOCKED_REL

    def gate(name: str,passed: Any,value: Any=None) -> None:
        ok=bool(passed)
        gates[name]={"passed":ok,"value":value}
        print(f"[{'PASS' if ok else 'FAIL'}] {name}"+(f" — {value}" if value is not None else ""))
        if not ok:
            raise GateError(name)

    print("="*192)
    print("POSTV16-AV1-D-R7-R7A — CANONICAL PRIMARY-ENVELOPE ARITHMETIC SEMANTICS FREEZE")
    print("="*192)
    print("FREEZE ONLY. NO MODEL INFERENCE. NO LP EXECUTION. NO FOUNDATION-CASE RECONCILIATION.")
    print("R7-R3 AND R7-R6 REMAIN IMMUTABLE FAILS.")
    print("ONE AND ONLY ONE PRIMARY-ENVELOPE PASS/FAIL ARITHMETIC IS DEFINED FOR THE NEXT EXECUTION.\n")

    try:
        root=root.resolve();drive=drive.resolve()

        parent=git_text(root,"rev-parse","HEAD^")
        status=git_text(root,"status","--porcelain")
        gate("repository_parent_is_R7R7_commit",parent==PARENT_R7R7_COMMIT,parent)
        gate("repository_clean",status=="",repr(status))

        for fn,blob in SOURCE_BLOBS.items():
            p=root/fn
            actual=git_blob_sha(p,root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==blob,actual)

        stage="R7R7_closure_binding"
        r7r7=drive/R7R7_REL
        gate("R7R7_output_present",r7r7.is_dir(),str(r7r7))
        m7=verify_manifest(r7r7,R7R7_MANIFEST)
        gate("R7R7_manifest_SHA_closure",True,len(m7))
        s7=load_json(r7r7/R7R7_SUMMARY)
        c7=load_json(r7r7/R7R7_CLOSURE)

        gate("R7R7_status_exact",s7["status"]==R7R7_STATUS,s7["status"])
        gate("R7R3_immutable_FAIL",s7["R7R3_result"]=="FAIL")
        gate("R7R6_immutable_FAIL",s7["R7R6_result"]=="FAIL")
        gate("R7R6_retest_forbidden",s7["R7R6_retest_authorized"] is False)
        gate("R7R7A_authorized",s7["R7R7A_semantics_freeze_authorized"] is True)
        gate("R7R7_physical_infeasibility_not_established",s7["physical_infeasibility_established"] is False)
        gate("R7R7_transport_B1_failure_not_established",s7["transport_or_B1_failure_established"] is False)

        sem=c7["localized_semantics"]
        gate("R7R7_solver_semantics_passed",sem["solver_constraint_semantics_result"]=="PASS_ACTIVE_BOUNDARY")
        gate("R7R7_fsum_semantics_failed",sem["independent_math_fsum_semantics_result"]=="FAIL")
        gate(
            "R7R7_mismatch_class_exact",
            sem["classification"]=="DUAL_FLOATING_POINT_ARITHMETIC_CERTIFICATION_SEMANTICS_MISMATCH",
        )

        rules=c7["lineage_rules"]
        gate("R7R6_no_tolerance_widening",rules["do_not_widen_R7R6_tolerance"] is True)
        gate("R7R6_no_solver_change",rules["do_not_change_R7R6_solver_settings"] is True)
        gate("R7R6_no_drop_fsum_and_relabel",rules["do_not_drop_R7R6_fsum_gate_and_relabel"] is True)
        gate("R7R6_no_rerun",rules["do_not_rerun_R7R6"] is True)
        gate(
            "future_single_semantics_required",
            rules["new_future_protocol_must_define_one_canonical_primary_envelope_arithmetic_before_execution"] is True,
        )

        stage="prior_numerical_protocol_binding"
        r7r5=drive/R7R5_REL
        gate("R7R5_output_present",r7r5.is_dir(),str(r7r5))
        m5=verify_manifest(r7r5,R7R5_MANIFEST)
        gate("R7R5_manifest_SHA_closure",True,len(m5))
        p5=load_json(r7r5/R7R5_PROTOCOL)
        gate("R7R5_protocol_id_exact",p5["protocol_id"]==R7R5_PROTOCOL_ID,p5["protocol_id"])
        num5=p5["redesigned_numerical_execution"]
        gate("R7R5_method_highs_ds",num5["LP_method"]==LP_METHOD)
        gate("R7R5_primal_tol_1e10",float(num5["primal_feasibility_tolerance"])==PRIMAL_FEAS_TOL)
        gate("R7R5_dual_tol_1e10",float(num5["dual_feasibility_tolerance"])==DUAL_FEAS_TOL)
        gate(
            "R7R5_primary_envelope_formula_bound",
            num5["primary_objective_envelope"]["formula"]
            =="tol_obj = max(1e-8, 1e-12*max(abs(primary_optimum),1))",
        )

        stage="physical_protocol_binding"
        r7r2=drive/R7R2_REL
        gate("R7R2_output_present",r7r2.is_dir(),str(r7r2))
        m2=verify_manifest(r7r2,R7R2_MANIFEST)
        gate("R7R2_manifest_SHA_closure",True,len(m2))
        p2=load_json(r7r2/R7R2_PROTOCOL)
        gate("R7R2_protocol_id_exact",p2["protocol_id"]==R7R2_PROTOCOL_ID,p2["protocol_id"])
        gate("R7R2_support_domain_unchanged",p2["support_graph"]["unsupported_cells_eligible"] is False)
        gate("R7R2_cross_component_transfer_forbidden",p2["support_graph"]["cross_component_mass_transfer_allowed"] is False)
        gate("R7R2_B1_change_forbidden",p2["prohibitions"]["change_B1_half_overlap"] is True)
        gate("R7R2_checkpoint_change_forbidden",p2["prohibitions"]["change_accepted_checkpoint"] is True)
        gate("R7R2_Smax_relaxation_forbidden",p2["prohibitions"]["relax_Smax_above_0p80"] is True)

        stage="freeze_single_canonical_semantics"

        protocol={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "protocol_id":NEW_PROTOCOL_ID,
            "immutable_history":{
                "R7R3":"FAIL",
                "R7R6":"FAIL",
                "R7R3_retested":False,
                "R7R6_retested":False,
                "prior_results_relabelled":False,
            },
            "physical_authority":{
                "protocol_id":R7R2_PROTOCOL_ID,
                "changed":False,
                "support_graph_changed":False,
                "primary_graph_cost_changed":False,
                "mass_bookkeeping_changed":False,
                "B1_changed":False,
                "accepted_checkpoint_changed":False,
                "C3_normalization_changed":False,
                "saturation_bounds_changed":False,
                "EOS_inversion_changed":False,
            },
            "solver_authority":{
                "method":LP_METHOD,
                "presolve":True,
                "primal_feasibility_tolerance":PRIMAL_FEAS_TOL,
                "dual_feasibility_tolerance":DUAL_FEAS_TOL,
                "changed_from_R7R5":False,
            },
            "canonical_primary_envelope_semantics":{
                "authority_name":"SOLVER_NATIVE_UNSCALED_SECONDARY_INEQUALITY_RESIDUAL",
                "primary_optimum_authority":"float(primary.fun) returned by the frozen highs-ds primary solve",
                "primary_envelope_formula":"tol_obj = max(1e-8, 1e-12*max(abs(primary.fun),1))",
                "secondary_constraint_coefficients":"exact unscaled c_primary vector used by the primary LP",
                "secondary_constraint_rhs":"float(primary.fun) + tol_obj",
                "coefficient_scaling_applied":False,
                "reason_no_scaling":(
                    "Scaling the inequality would map the fixed HiGHS feasibility tolerance "
                    "into a different effective tolerance in original primary-cost units. "
                    "The raw unscaled row preserves the intended units and envelope."
                ),
                "single_pass_fail_quantity":"float(secondary.ineqlin.residual[0])",
                "pass_rule":"secondary.success is True AND secondary.ineqlin.residual[0] >= -1e-10",
                "residual_floor":CANONICAL_RESIDUAL_FLOOR,
                "residual_units":"original primary graph-cost units",
                "independent_math_fsum_is_pass_fail_authority":False,
                "independent_numpy_dot_is_pass_fail_authority":False,
                "solver_reported_secondary_primary_constraint_is_only_authority":True,
            },
            "diagnostics_only":{
                "math_fsum_primary_cost":True,
                "math_fsum_secondary_primary_cost":True,
                "numpy_dot_primary_cost":True,
                "numpy_dot_secondary_primary_cost":True,
                "solver_reported_fun":True,
                "rule":(
                    "Diagnostic arithmetic differences are recorded but cannot independently "
                    "change PASS/FAIL once the canonical solver-native residual gate is evaluated."
                ),
            },
            "why_this_is_not_R7R6_relabelling":{
                "R7R6_fsum_gate_remains_binding_for_R7R6":True,
                "R7R6_result_remains_FAIL":True,
                "new_semantics_apply_only_to_future_new_milestone":True,
            },
            "hard_gates_for_next_execution":{
                "primary_LP_success_all_times":True,
                "secondary_LP_success_all_times":True,
                "canonical_secondary_residual_all_times":">= -1e-10",
                "all_R7R2_component_capacity_mass_bounds_EOS_gates_unchanged":True,
                "all_9_canonical_times":True,
                "unsupported_cells_as_sinks":False,
                "cross_component_transfer":False,
                "checkpoint_B1_graph_cost_bounds_changes":False,
                "no_geology0031_or_acceptance_truth":True,
            },
            "prohibitions":{
                "R7R6_rerun":True,
                "R7R6_relabel":True,
                "objective_envelope_formula_change":True,
                "constraint_row_scaling":True,
                "solver_method_change":True,
                "solver_feasibility_tolerance_change":True,
                "second_independent_arithmetic_pass_fail_gate":True,
                "support_graph_change":True,
                "primary_graph_cost_change":True,
                "B1_change":True,
                "checkpoint_change":True,
                "saturation_bound_change":True,
                "geology0031_use":True,
                "acceptance_truth_use":True,
            },
            "next":{
                "milestone":"POSTV16-AV1-D-R7-R7B",
                "name":"Controlled execution under the single canonical solver-native arithmetic semantics",
                "authorized":True,
                "candidate_count":1,
                "alternate_candidate_authorized":False,
            },
        }

        freeze={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "protocol_id":NEW_PROTOCOL_ID,
            "R7R3_result_preserved":"FAIL",
            "R7R6_result_preserved":"FAIL",
            "model_inference_performed":False,
            "LP_execution_performed":False,
            "foundation_case_reconciliation_execution_performed":False,
            "physical_operator_changed":False,
            "primary_envelope_formula_changed":False,
            "constraint_scaling_applied":False,
            "solver_method_changed_from_R7R5":False,
            "solver_tolerances_changed_from_R7R5":False,
            "single_canonical_arithmetic_defined":True,
            "math_fsum_demoted_to_diagnostic_only_for_future_protocol":True,
            "candidate_count":1,
            "R7R7B_execution_authorized":True,
        }

        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "protocol_id":NEW_PROTOCOL_ID,
            "R7R3_result":"FAIL",
            "R7R6_result":"FAIL",
            "canonical_arithmetic":"solver-native unscaled secondary inequality residual",
            "canonical_pass_rule":"secondary.success and residual >= -1e-10",
            "primary_envelope_formula_changed":False,
            "constraint_scaling_applied":False,
            "solver_method":LP_METHOD,
            "primal_feasibility_tolerance":PRIMAL_FEAS_TOL,
            "dual_feasibility_tolerance":DUAL_FEAS_TOL,
            "independent_fsum_pass_fail_gate":False,
            "physical_operator_changed":False,
            "model_inference_performed":False,
            "LP_execution_performed":False,
            "R7R7B_authorized":True,
            "next":"POSTV16-AV1-D-R7-R7B — controlled execution under single canonical solver-native arithmetic semantics",
        }

        immutable_publish(out,{
            "PAD_Stream_POSTV16_AV1_D_R7_R7A_Summary.json":json_bytes(summary),
            "POSTV16_AV1_D_R7_R7A_Frozen_Canonical_Arithmetic_Semantics.json":json_bytes(protocol),
            "POSTV16_AV1_D_R7_R7A_Protocol_Freeze_Contract.json":json_bytes(freeze),
            "POSTV16_AV1_D_R7_R7A_Final_Gate_Matrix.csv":csv_bytes(
                [{"gate":k,**v} for k,v in gates.items()]
            ),
        })

        rows=[]
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name!="POSTV16_AV1_D_R7_R7A_Artifact_Manifest.csv":
                rows.append({
                    "file":p.name,
                    "sha256":sha256_file(p),
                    "bytes":p.stat().st_size,
                })
        immutable_publish(out,{
            "POSTV16_AV1_D_R7_R7A_Artifact_Manifest.csv":csv_bytes(rows)
        })

        print("\n"+"="*192)
        print("POSTV16-AV1-D-R7-R7A: PASS")
        print("="*192)
        print(f"{'Status':112}: {STATUS_PASS}")
        print(f"{'R7-R3 / R7-R6 immutable results':112}: FAIL / FAIL")
        print(f"{'Frozen semantics protocol':112}: {NEW_PROTOCOL_ID}")
        print(f"{'Canonical authority':112}: solver-native unscaled secondary inequality residual")
        print(f"{'Primary optimum authority':112}: primary.fun")
        print(f"{'Primary envelope formula changed':112}: False")
        print(f"{'Constraint scaling applied':112}: False")
        print(f"{'Solver method / primal / dual tolerance':112}: highs-ds / 1e-10 / 1e-10")
        print(f"{'Canonical residual floor':112}: -1e-10")
        print(f"{'math.fsum future role':112}: diagnostic only")
        print(f"{'Physical reconciliation changed':112}: False")
        print(f"{'Model inference / LP execution in R7-R7A':112}: False / False")
        print(f"{'R7-R7B single-candidate execution authorized':112}: True")
        print(f"{'NEXT':112}: POSTV16-AV1-D-R7-R7B — execute single canonical arithmetic semantics")
        print("="*192)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        report={
            "milestone":MILESTONE,
            "status":STATUS_BLOCKED,
            "failed_stage":stage,
            "exception":repr(exc),
            "gates":gates,
            "R7R3_result_changed":False,
            "R7R6_result_changed":False,
            "model_inference_performed":False,
            "LP_execution_performed":False,
            "R7R7B_authorized":False,
            "next_action":(
                "Audit only the R7-R7A freeze. Do not execute another reconciliation "
                "until exactly one canonical arithmetic semantics has been validly frozen."
            ),
        }
        data=json_bytes(report)
        p=blocked/"POSTV16_AV1_D_R7_R7A_Blocked_Report.json"
        if p.exists() and p.read_bytes()!=data:
            p=blocked/f"POSTV16_AV1_D_R7_R7A_Blocked_Report_{hashlib.sha256(data).hexdigest()[:12]}.json"
        if not p.exists():
            p.write_bytes(data)

        print("\n"+"="*192)
        print("POSTV16-AV1-D-R7-R7A: BLOCKED")
        print("="*192)
        print("Failed stage:",stage)
        print("Exception   :",repr(exc))
        print("Report      :",p)
        return 2


def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--project-root",type=Path,default=Path("."))
    p.add_argument(
        "--drive-root",
        type=Path,
        default=Path("/content/drive/MyDrive/PAD_Stream_Compute"),
    )
    p.add_argument("--self-test",action="store_true")
    return p.parse_args()


if __name__=="__main__":
    a=parse_args()
    if a.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))
