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


MILESTONE = "POSTV16-AV1-D-R7-R7"
STATUS_PASS = (
    "AV1DR7R7_R7R6_SCIENTIFIC_FAIL_CLOSED_"
    "SECONDARY_CONSTRAINT_VS_FSUM_CERTIFICATION_SEMANTICS_MISMATCH_LOCALIZED"
)
STATUS_BLOCKED = "AV1DR7R7_FAILURE_CLOSURE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R7R6_COMMIT = "efcd47ec9c188ed205dc22913275616924b8059c"

R7R6 = "PAD_Stream_POSTV16_AV1_D_R7_R6_Strict_Numerical_Certification_Execution.py"
R7R6_BLOB = "b7bddd20ed08c05f3b832d5006ae98586468fd26"
R7R5 = "PAD_Stream_POSTV16_AV1_D_R7_R5_Deterministic_Numerical_Certification_Redesign_Freeze.py"
R7R5_BLOB = "bc43079146772a16a3c3ecc6cea13fe88a963857"
R7R4 = "PAD_Stream_POSTV16_AV1_D_R7_R4_R7R3_Tiebreak_Certification_Failure_Closure.py"
R7R4_BLOB = "687aa4580c85b8a188e4d2e2dc0493b2f25dc97f"

BASE = Path("post_v16")/RID/"POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
R7R6_REL = BASE/"POSTV16_AV1_D_R7_R6_Strict_Numerical_Certification_Execution"
R7R6_SUMMARY = "PAD_Stream_POSTV16_AV1_D_R7_R6_Summary.json"
R7R6_DECISION = "POSTV16_AV1_D_R7_R6_Final_Decision.json"
R7R6_MANIFEST = "POSTV16_AV1_D_R7_R6_Artifact_Manifest.csv"
R7R6_TIME_AUDIT = "POSTV16_AV1_D_R7_R6_Timewise_Strict_Certification_Audit.csv"

OUT_REL = BASE/"POSTV16_AV1_D_R7_R7_R7R6_Certification_Semantics_Failure_Closure"
BLOCKED_REL = BASE/"POSTV16_AV1_D_R7_R7_BLOCKED"

R7R6_FAIL_STATUS = (
    "AV1DR7R6_STRICT_NUMERICAL_CERTIFICATION_EXECUTION_FAIL_"
    "NO_ADAPTATION_OR_ALTERNATE_CANDIDATE_AUTHORIZED"
)
EXPECTED_GATE = "secondary_primary_objective_certification_all_times"
EXPECTED_COMPLETED = 2

EXPECTED_PRIMARY = 76140261.34928478
EXPECTED_TIE = 76140261.34936105
EXPECTED_TOL = 7.614026134928478e-05
EXPECTED_GUARD = 1.0e-08
EXPECTED_LIMIT = 76140261.34936094
EXPECTED_OVERRUN = 1.043081283569336e-07
EXPECTED_SOLVER_SLACK = 0.0


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):
            h.update(b)
    return h.hexdigest()


def git_text(root: Path,*args: str) -> str:
    p=subprocess.run(
        ["git","-C",str(root),*args],
        check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE
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
            raise GateError(f"manifest_missing:{fn}")
        actual=sha256_file(p)
        if actual!=expected:
            raise GateError(f"manifest_SHA:{fn}:{actual}:{expected}")
    return m


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+"\n").encode()


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
    return s.getvalue().encode()


def immutable_publish(out: Path,files: dict[str,bytes]) -> None:
    out.mkdir(parents=True,exist_ok=True)
    for name,data in files.items():
        p=out/name
        if p.exists() and p.read_bytes()!=data:
            raise GateError(f"existing_output_differs:{name}")
        if not p.exists():
            p.write_bytes(data)


def near(a: float,b: float,rtol: float=1e-14,atol: float=1e-12) -> bool:
    return abs(float(a)-float(b)) <= max(atol,rtol*max(abs(float(b)),1.0))


def self_test() -> None:
    fsum_delta=EXPECTED_TIE-EXPECTED_PRIMARY
    allowed=EXPECTED_TOL+EXPECTED_GUARD
    if not (fsum_delta>allowed):
        raise RuntimeError("expected_certification_failure_not_positive")
    if EXPECTED_SOLVER_SLACK != 0.0:
        raise RuntimeError("expected_solver_slack")
    print("POSTV16-AV1-D-R7-R7 self-test: PASS")


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

    print("="*190)
    print("POSTV16-AV1-D-R7-R7 — R7-R6 CERTIFICATION-SEMANTICS FAILURE CLOSURE")
    print("="*190)
    print("AUDIT/CLOSURE ONLY. NO MODEL INFERENCE. NO LP RE-SOLVE. NO NEW CERTIFICATION RULE.")
    print("R7-R6 REMAINS AN IMMUTABLE SCIENTIFIC FAIL. R7-R3 ALSO REMAINS FAIL.\n")

    try:
        root=root.resolve();drive=drive.resolve()

        parent=git_text(root,"rev-parse","HEAD^")
        status=git_text(root,"status","--porcelain")
        gate("repository_parent_is_R7R6_commit",parent==PARENT_R7R6_COMMIT,parent)
        gate("repository_clean",status=="",repr(status))

        for fn,blob in ((R7R6,R7R6_BLOB),(R7R5,R7R5_BLOB),(R7R4,R7R4_BLOB)):
            p=root/fn
            actual=git_blob_sha(p,root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==blob,actual)

        stage="R7R6_failure_binding"
        d=drive/R7R6_REL
        gate("R7R6_output_present",d.is_dir(),str(d))
        manifest=verify_manifest(d,R7R6_MANIFEST)
        gate("R7R6_manifest_SHA_closure",True,len(manifest))

        s=load_json(d/R7R6_SUMMARY)
        q=load_json(d/R7R6_DECISION)

        gate("R7R6_status_exact",q["status"]==R7R6_FAIL_STATUS,q["status"])
        gate("R7R6_scientific_execution_pass_false",q["scientific_execution_pass"] is False)
        gate("R7R6_failed_gate_exact",q["failed_gate"]==EXPECTED_GATE,q["failed_gate"])
        gate("R7R6_completed_times_exact",int(q["completed_canonical_times"])==EXPECTED_COMPLETED,q["completed_canonical_times"])
        gate("R7R6_model_inference_performed",q["model_inference_performed"] is True)
        gate("R7R6_reconciliation_started",q["reconciliation_started"] is True)
        gate("R7R6_R7R3_remains_FAIL",q["R7R3_immutable_result"]=="FAIL")
        gate("R7R6_R7R3_not_retested",q["R7R3_retested"] is False)
        gate("R7R6_checkpoint_unmodified",q["accepted_checkpoint_modified"] is False)
        gate("R7R6_B1_unmodified",q["B1_modified"] is False)
        gate("R7R6_graph_unmodified",q["support_graph_modified"] is False)
        gate("R7R6_primary_cost_unmodified",q["primary_graph_cost_modified"] is False)
        gate("R7R6_bounds_unmodified",q["saturation_bounds_modified"] is False)
        gate("R7R6_primary_envelope_unmodified",q["primary_envelope_changed"] is False)
        gate("R7R6_final_guard_unmodified",q["final_guard_changed"] is False)
        gate("R7R6_no_geology0031",q["geology0031_used"] is False)
        gate("R7R6_no_acceptance_truth",q["acceptance_truth_used"] is False)
        gate("R7R6_no_alternate_candidate",q["alternate_candidate_authorized"] is False)
        gate("R7R6_no_retuning",q["retuning_authorized"] is False)

        fd=q["failure_detail"]
        primary=float(fd["certified_primary_optimum"])
        tie=float(fd["certified_tie_primary_cost"])
        tol=float(fd["primary_envelope_tolerance"])
        guard=float(fd["final_additive_guard"])
        limit=float(fd["certification_limit"])
        overrun=float(fd["overrun"])
        slack=float(fd["secondary_inequality_slack"])

        gate("primary_exact",near(primary,EXPECTED_PRIMARY),primary)
        gate("tie_exact",near(tie,EXPECTED_TIE),tie)
        gate("tolerance_exact",near(tol,EXPECTED_TOL),tol)
        gate("guard_exact",near(guard,EXPECTED_GUARD,rtol=0,atol=1e-16),guard)
        gate("limit_exact",near(limit,EXPECTED_LIMIT),limit)
        gate("overrun_exact",near(overrun,EXPECTED_OVERRUN,rtol=1e-10,atol=1e-15),overrun)
        gate("secondary_solver_slack_exact_zero",slack==EXPECTED_SOLVER_SLACK,slack)

        delta=tie-primary
        permitted=tol+guard
        rel_overrun=overrun/max(abs(primary),1.0)
        relative_delta=delta/max(abs(primary),1.0)

        gate("fsum_certification_rejects_solution",delta>permitted,[delta,permitted])
        gate("reported_solver_constraint_residual_nonnegative",slack>=-1e-8,slack)
        gate("dual_certification_semantics_disagree",slack>=-1e-8 and delta>permitted)

        stage="completed_time_evidence"
        time_path=d/R7R6_TIME_AUDIT
        gate("R7R6_time_audit_present",time_path.is_file(),str(time_path))
        rows=read_csv(time_path)
        gate("R7R6_two_completed_time_rows",len(rows)==2,len(rows))
        days=[float(r["target_day"]) for r in rows]
        gate("R7R6_completed_days_30_60",days==[30.0,60.0],days)

        for r in rows:
            day=int(float(r["target_day"]))
            gate(
                f"time_{day}_mass_relative_closure_passed",
                float(r["total_component_mass_relative_closure"])<=1e-10,
                float(r["total_component_mass_relative_closure"]),
            )
            gate(
                f"time_{day}_EOS_relative_closure_passed",
                float(r["EOS_mass_relative_closure"])<=1e-10,
                float(r["EOS_mass_relative_closure"]),
            )
            gate(
                f"time_{day}_grid_bounds_passed",
                float(r["grid_saturation_min"])>=0.2-1e-12
                and float(r["grid_saturation_max"])<=0.8+1e-12,
                [float(r["grid_saturation_min"]),float(r["grid_saturation_max"])],
            )

        closure={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "immutable_results":{
                "R7R3":"FAIL",
                "R7R6":"FAIL",
                "R7R6_may_be_relabelled_PASS":False,
                "R7R6_may_be_retested_with_changed_rule":False,
            },
            "R7R6_failure":{
                "gate":EXPECTED_GATE,
                "day_reached_before_failure":100.0,
                "completed_times":[30.0,60.0],
                "certified_primary_optimum":primary,
                "certified_tie_primary_cost_math_fsum":tie,
                "primary_envelope_tolerance":tol,
                "final_additive_guard":guard,
                "certification_limit":limit,
                "math_fsum_overrun":overrun,
                "secondary_solver_inequality_residual":slack,
                "math_fsum_delta_from_primary":delta,
                "math_fsum_permitted_delta":permitted,
                "overrun_relative_to_primary":rel_overrun,
                "delta_relative_to_primary":relative_delta,
            },
            "localized_semantics":{
                "LP_method":"highs-ds",
                "primal_feasibility_tolerance":1e-10,
                "dual_feasibility_tolerance":1e-10,
                "solver_constraint_semantics_result":"PASS_ACTIVE_BOUNDARY",
                "solver_constraint_evidence":"secondary.ineqlin.residual[0] == 0.0",
                "independent_math_fsum_semantics_result":"FAIL",
                "independent_math_fsum_evidence":"certified_tie_primary_cost > certified_primary_optimum + tol_obj + 1e-8",
                "classification":"DUAL_FLOATING_POINT_ARITHMETIC_CERTIFICATION_SEMANTICS_MISMATCH",
            },
            "what_is_proven":{
                "strict_primary_LP_returned_success_before_failure":True,
                "strict_secondary_LP_returned_success_before_failure":True,
                "secondary_solver_constraint_residual_satisfied":True,
                "independent_math_fsum_gate_failed":True,
                "day30_end_to_end_reconciliation_passed":True,
                "day60_end_to_end_reconciliation_passed":True,
            },
            "what_is_not_proven":{
                "all_9_time_integration_pass":True,
                "day100_final_grid_state_valid":True,
                "physical_reconciliation_infeasible":True,
                "component_capacity_infeasible":True,
                "accepted_PI_RNN_failed":True,
                "B1_failed":True,
                "mass_conservation_failed":True,
                "saturation_bounds_failed":True,
            },
            "lineage_rules":{
                "do_not_widen_R7R6_tolerance":True,
                "do_not_change_R7R6_solver_settings":True,
                "do_not_drop_R7R6_fsum_gate_and_relabel":True,
                "do_not_rerun_R7R6":True,
                "new_future_protocol_must_define_one_canonical_primary_envelope_arithmetic_before_execution":True,
            },
            "next":{
                "milestone":"POSTV16-AV1-D-R7-R7A",
                "name":"Prospective canonical primary-envelope arithmetic semantics freeze",
                "authorized":True,
                "execution_authorized":False,
                "required_design_question":(
                    "Choose and prospectively freeze one canonical arithmetic semantics "
                    "for evaluating the secondary primary-objective envelope. "
                    "Do not execute another Foundation-case reconciliation until that "
                    "single semantics is fixed."
                ),
            },
        }

        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "R7R3_result":"FAIL",
            "R7R6_result":"FAIL",
            "failed_gate":EXPECTED_GATE,
            "solver_inequality_slack":slack,
            "math_fsum_overrun":overrun,
            "overrun_relative_to_primary":rel_overrun,
            "completed_times":2,
            "physical_infeasibility_established":False,
            "transport_or_B1_failure_established":False,
            "R7R6_retest_authorized":False,
            "R7R7A_semantics_freeze_authorized":True,
        }

        immutable_publish(out,{
            "PAD_Stream_POSTV16_AV1_D_R7_R7_Summary.json":json_bytes(summary),
            "POSTV16_AV1_D_R7_R7_R7R6_Failure_Closure.json":json_bytes(closure),
            "POSTV16_AV1_D_R7_R7_Final_Gate_Matrix.csv":csv_bytes(
                [{"gate":k,**v} for k,v in gates.items()]
            ),
        })

        manifest=[]
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name!="POSTV16_AV1_D_R7_R7_Artifact_Manifest.csv":
                manifest.append({
                    "file":p.name,
                    "sha256":sha256_file(p),
                    "bytes":p.stat().st_size,
                })
        immutable_publish(out,{
            "POSTV16_AV1_D_R7_R7_Artifact_Manifest.csv":csv_bytes(manifest)
        })

        print("\n"+"="*190)
        print("POSTV16-AV1-D-R7-R7: PASS")
        print("="*190)
        print(f"{'Status':110}: {STATUS_PASS}")
        print(f"{'Immutable R7-R3 / R7-R6 results':110}: FAIL / FAIL")
        print(f"{'R7-R6 failed gate':110}: {EXPECTED_GATE}")
        print(f"{'Strict solver inequality slack':110}: {slack:.12e}")
        print(f"{'math.fsum certification overrun':110}: {overrun:.12e}")
        print(f"{'Overrun relative to primary objective':110}: {rel_overrun:.12e}")
        print(f"{'Completed reconciled times before failure':110}: 30, 60 days")
        print(f"{'Physical/transport/B1 infeasibility established':110}: False")
        print(f"{'R7-R6 retest authorized':110}: False")
        print(f"{'Canonical arithmetic semantics freeze authorized':110}: True")
        print(f"{'NEXT':110}: POSTV16-AV1-D-R7-R7A — freeze one canonical primary-envelope arithmetic semantics")
        print("="*190)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        report={
            "milestone":MILESTONE,
            "status":STATUS_BLOCKED,
            "failed_stage":stage,
            "exception":repr(exc),
            "gates":gates,
            "model_inference_performed":False,
            "LP_resolve_performed":False,
            "R7R6_result_changed":False,
            "R7R7A_authorized":False,
            "next_action":(
                "Audit only this failure-closure milestone. Do not rerun R7-R6 "
                "or select a new certification arithmetic without a prospective freeze."
            ),
        }
        data=json_bytes(report)
        p=blocked/"POSTV16_AV1_D_R7_R7_Blocked_Report.json"
        if p.exists() and p.read_bytes()!=data:
            p=blocked/f"POSTV16_AV1_D_R7_R7_Blocked_Report_{hashlib.sha256(data).hexdigest()[:12]}.json"
        if not p.exists():
            p.write_bytes(data)

        print("\n"+"="*190)
        print("POSTV16-AV1-D-R7-R7: BLOCKED")
        print("="*190)
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
