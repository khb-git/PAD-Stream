#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, io, json, subprocess
from pathlib import Path
from typing import Any

MILESTONE = "POSTV16-AV1-D-R7-R4"
STATUS_PASS = (
    "AV1DR7R4_R7R3_SCIENTIFIC_FAIL_CLOSED_"
    "SECONDARY_TIEBREAK_PRIMARY_OPTIMUM_CERTIFICATION_OVERRUN_LOCALIZED"
)
STATUS_BLOCKED = "AV1DR7R4_FAILURE_CLOSURE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R7R3_COMMIT = "1856d50d8d7d1232cbcaef20011b51570d219194"

R7R3 = "PAD_Stream_POSTV16_AV1_D_R7_R3_Controlled_Frozen_Reconciliation_Execution.py"
R7R3_BLOB = "a431ac9d4faa3fdf0ecf415c36208ac31c797ad0"
R7R2 = "PAD_Stream_POSTV16_AV1_D_R7_R2_Conservative_Bounded_Overlap_Occupancy_Reconciliation_Freeze.py"
R7R2_BLOB = "c9c4ceed05e6e631ad071b9da901d35874609255"

BASE = Path("post_v16")/RID/"POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
R7R3_REL = BASE/"POSTV16_AV1_D_R7_R3_Controlled_Frozen_Reconciliation_Execution"
R7R3_SUMMARY = "PAD_Stream_POSTV16_AV1_D_R7_R3_Summary.json"
R7R3_DECISION = "POSTV16_AV1_D_R7_R3_Final_Decision.json"
R7R3_GATES = "POSTV16_AV1_D_R7_R3_Final_Gate_Matrix.csv"
R7R3_MANIFEST = "POSTV16_AV1_D_R7_R3_Artifact_Manifest.csv"

OUT_REL = BASE/"POSTV16_AV1_D_R7_R4_R7R3_Tiebreak_Certification_Failure_Closure"
BLOCKED_REL = BASE/"POSTV16_AV1_D_R7_R4_BLOCKED"

R7R3_FAIL_STATUS = (
    "AV1DR7R3_FROZEN_SUPPORT_GRAPH_RECONCILIATION_EXECUTION_FAIL_"
    "NO_ADAPTATION_OR_ALTERNATE_REPAIR_AUTHORIZED"
)

EXPECTED_FAILED_GATE = "tiebreak_preserves_primary_optimum"
EXPECTED_PRIMARY = 76140261.34928446
EXPECTED_TIE_COST = 76140261.34936073
EXPECTED_TOL = 7.614026134928446e-05
EXPECTED_COMPLETED_TIMES = 2

class GateError(RuntimeError):
    pass

def sha256_file(p: Path) -> str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):
            h.update(b)
    return h.hexdigest()

def git_text(root: Path,*args: str) -> str:
    q=subprocess.run(
        ["git","-C",str(root),*args],
        check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE
    )
    return q.stdout.strip()

def git_blob_sha(p: Path,root: Path) -> str:
    return git_text(root,"hash-object",str(p))

def load_json(p: Path) -> dict[str,Any]:
    return json.loads(p.read_text(encoding="utf-8"))

def read_csv(p: Path) -> list[dict[str,str]]:
    with p.open("r",newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))

def verify_manifest(d: Path,name: str) -> dict[str,str]:
    rows=read_csv(d/name)
    m={r["file"]:r["sha256"] for r in rows}
    for fn,e in m.items():
        p=d/fn
        if not p.is_file():
            raise GateError(f"manifest_file_missing:{fn}")
        a=sha256_file(p)
        if a!=e:
            raise GateError(f"manifest_SHA_mismatch:{fn}:{a}:{e}")
    return m

def json_bytes(x: Any) -> bytes:
    return (json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+"\n").encode()

def csv_bytes(rows: list[dict[str,Any]]) -> bytes:
    if not rows:
        return b""
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    s=io.StringIO(newline="")
    w=csv.DictWriter(s,fieldnames=fields,lineterminator="\n")
    w.writeheader();w.writerows(rows)
    return s.getvalue().encode()

def immutable_publish(out: Path,files: dict[str,bytes]) -> None:
    out.mkdir(parents=True,exist_ok=True)
    for n,d in files.items():
        p=out/n
        if p.exists() and p.read_bytes()!=d:
            raise GateError(f"existing_output_differs:{n}")
        if not p.exists():
            p.write_bytes(d)

def near(a,b,rtol=1e-12,atol=1e-10):
    return abs(float(a)-float(b)) <= max(atol,rtol*max(abs(float(b)),1.0))

def self_test():
    diff=EXPECTED_TIE_COST-EXPECTED_PRIMARY
    over=diff-EXPECTED_TOL
    if not (diff>EXPECTED_TOL and over>0):
        raise RuntimeError("expected_overrun_not_positive")
    print("POSTV16-AV1-D-R7-R4 self-test: PASS")

def main(root: Path,drive: Path) -> int:
    gates={};stage="preflight"
    out=drive/OUT_REL;blocked=drive/BLOCKED_REL

    def gate(n,p,v=None):
        ok=bool(p)
        gates[n]={"passed":ok,"value":v}
        print(f"[{'PASS' if ok else 'FAIL'}] {n}"+(f" — {v}" if v is not None else ""))
        if not ok:
            raise GateError(n)

    print("="*188)
    print("POSTV16-AV1-D-R7-R4 — R7-R3 TIE-BREAK CERTIFICATION FAILURE CLOSURE")
    print("="*188)
    print("CLOSURE/AUDIT ONLY. NO MODEL INFERENCE. NO LP RE-SOLVE. NO RETUNING. NO ALTERNATE RECONCILIATION.")
    print("THE IMMUTABLE R7-R3 SCIENTIFIC FAIL IS PRESERVED.\n")

    try:
        root=root.resolve();drive=drive.resolve()

        parent=git_text(root,"rev-parse","HEAD^")
        status=git_text(root,"status","--porcelain")
        gate("repository_parent_is_R7R3_commit",parent==PARENT_R7R3_COMMIT,parent)
        gate("repository_clean",status=="",repr(status))

        for fn,b in ((R7R3,R7R3_BLOB),(R7R2,R7R2_BLOB)):
            p=root/fn
            a=git_blob_sha(p,root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",a==b,a)

        stage="R7R3_failure_binding"
        d=drive/R7R3_REL
        gate("R7R3_output_present",d.is_dir(),str(d))
        m=verify_manifest(d,R7R3_MANIFEST)
        gate("R7R3_manifest_SHA_closure",True,len(m))

        s=load_json(d/R7R3_SUMMARY)
        q=load_json(d/R7R3_DECISION)
        gm=read_csv(d/R7R3_GATES)

        gate("R7R3_status_exact",q["status"]==R7R3_FAIL_STATUS,q["status"])
        gate("R7R3_scientific_execution_pass_false",q["scientific_execution_pass"] is False)
        gate("R7R3_failed_gate_exact",q["failed_gate"]==EXPECTED_FAILED_GATE,q["failed_gate"])
        gate("R7R3_completed_times_exact",int(q["completed_canonical_times"])==EXPECTED_COMPLETED_TIMES,q["completed_canonical_times"])
        gate("R7R3_inference_performed_true",q["model_inference_performed"] is True)
        gate("R7R3_reconciliation_started_true",q["reconciliation_started"] is True)
        gate("R7R3_checkpoint_unmodified",q["accepted_checkpoint_modified"] is False)
        gate("R7R3_B1_unmodified",q["B1_modified"] is False)
        gate("R7R3_bounds_unmodified",q["saturation_bounds_modified"] is False)
        gate("R7R3_no_global_rescaling",q["global_saturation_rescaling_used"] is False)
        gate("R7R3_no_unsupported_sinks",q["unsupported_cells_used_as_sinks"] is False)
        gate("R7R3_no_geology0031",q["geology0031_used"] is False)
        gate("R7R3_no_acceptance_truth",q["acceptance_truth_used"] is False)
        gate("R7R3_alternate_candidate_forbidden",q["alternate_reconciliation_candidate_authorized"] is False)
        gate("R7R3_retuning_forbidden",q["retuning_authorized"] is False)

        fd=q["failure_detail"]
        primary=float(fd["primary_optimum"])
        tie=float(fd["tie_primary_cost"])
        tol=float(fd["tolerance"])

        gate("primary_optimum_exact",near(primary,EXPECTED_PRIMARY,rtol=1e-14),primary)
        gate("tie_primary_cost_exact",near(tie,EXPECTED_TIE_COST,rtol=1e-14),tie)
        gate("frozen_tolerance_exact",near(tol,EXPECTED_TOL,rtol=1e-14,atol=1e-12),tol)

        diff=tie-primary
        overrun=diff-tol
        rel_to_primary=diff/max(abs(primary),1.0)
        overrun_rel_primary=overrun/max(abs(primary),1.0)
        ratio_to_tol=diff/tol

        gate("frozen_gate_was_actually_violated",diff>tol,[diff,tol])
        gate("overrun_positive",overrun>0,overrun)

        names={r["gate"]:r for r in gm}
        gate("accepted_transport_bounds_passed","accepted_transport_saturation_bounds" in names and names["accepted_transport_saturation_bounds"]["passed"].lower()=="true")
        gate("B1_projection_passed","same_B1_201_to_200_projection" in names and names["same_B1_201_to_200_projection"]["passed"].lower()=="true")
        gate("support_graph_component_gate_passed","support_graph_components_positive" in names and names["support_graph_components_positive"]["passed"].lower()=="true")
        gate("day30_grid_bounds_passed","time_30_grid_saturation_bounds" in names and names["time_30_grid_saturation_bounds"]["passed"].lower()=="true")
        gate("day60_grid_bounds_passed","time_60_grid_saturation_bounds" in names and names["time_60_grid_saturation_bounds"]["passed"].lower()=="true")
        gate("day30_EOS_closure_passed","time_30_EOS_mass_inversion_closure" in names and names["time_30_EOS_mass_inversion_closure"]["passed"].lower()=="true")
        gate("day60_EOS_closure_passed","time_60_EOS_mass_inversion_closure" in names and names["time_60_EOS_mass_inversion_closure"]["passed"].lower()=="true")
        gate("day100_subsegment_mass_closure_passed","time_100_B1_to_subsegment_mass_closure" in names and names["time_100_B1_to_subsegment_mass_closure"]["passed"].lower()=="true")

        closure={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "R7R3_immutable_status":R7R3_FAIL_STATUS,
            "R7R3_result_remains_FAIL":True,
            "failed_gate":EXPECTED_FAILED_GATE,
            "failed_stage_class":"SECONDARY_DETERMINISTIC_TIEBREAK_CERTIFICATION",
            "completed_times_before_fail":EXPECTED_COMPLETED_TIMES,
            "numerical_localization":{
                "primary_optimum":primary,
                "tie_solution_primary_cost":tie,
                "allowed_primary_cost_increase":tol,
                "actual_primary_cost_increase":diff,
                "overrun_beyond_frozen_limit":overrun,
                "actual_increase_relative_to_primary":rel_to_primary,
                "overrun_relative_to_primary":overrun_rel_primary,
                "actual_increase_over_allowed_tolerance_ratio":ratio_to_tol,
            },
            "what_is_proven":{
                "frozen_tiebreak_certification_gate_failed":True,
                "primary_LP_had_succeeded_before_failure":True,
                "secondary_tiebreak_LP_had_returned_success_before_certification_failure":True,
                "day30_reconciliation_completed":True,
                "day60_reconciliation_completed":True,
                "day30_grid_saturation_bounded":True,
                "day60_grid_saturation_bounded":True,
                "day30_EOS_mass_closure_passed":True,
                "day60_EOS_mass_closure_passed":True,
                "day100_B1_to_subsegment_mass_closure_passed":True,
            },
            "what_is_not_proven":{
                "all_9_time_end_to_end_integration_pass":True,
                "day100_reconciled_grid_state_valid":True,
                "support_graph_protocol_physically_infeasible":True,
                "accepted_PI_RNN_failed":True,
                "B1_bridge_failed":True,
            },
            "classification":{
                "immutable_protocol_result":"SCIENTIFIC_FAIL",
                "failure_mechanism":"NUMERICAL_CERTIFICATION_OVERRUN_OF_SECONDARY_TIEBREAK_PRIMARY_OPTIMUM_ENVELOPE",
                "failure_is_primary_LP_infeasibility":False,
                "failure_is_component_capacity_infeasibility":False,
                "failure_is_mass_conservation_failure":False,
                "failure_is_saturation_bound_failure":False,
                "failure_is_transport_checkpoint_failure":False,
            },
            "lineage_rules":{
                "R7R3_may_be_rerun_with_changed_tolerance":False,
                "R7R3_may_be_rerun_with_changed_solver_settings":False,
                "alternate_R7R3_reconciliation_candidate_authorized":False,
                "R7R3_result_may_be_relabelled_PASS":False,
                "future_new_protocol_must_have_new_milestone_and_new_freeze":True,
            },
            "next":{
                "milestone":"POSTV16-AV1-D-R7-R5",
                "name":"Prospective deterministic numerical-certification protocol redesign and freeze",
                "authorized":True,
                "scope":(
                    "Numerical certification only. Preserve the R7-R2 physical reconciliation "
                    "operator, support graph, primary graph-distance costs, saturation bounds, "
                    "B1 bridge, accepted checkpoint, and supported-cell domain. "
                    "Do not claim R7-R3 passed."
                ),
            },
        }

        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "R7R3_result":"FAIL",
            "failed_gate":EXPECTED_FAILED_GATE,
            "primary_optimum":primary,
            "tie_solution_primary_cost":tie,
            "allowed_increase":tol,
            "actual_increase":diff,
            "overrun":overrun,
            "overrun_relative_to_primary":overrun_rel_primary,
            "completed_times":EXPECTED_COMPLETED_TIMES,
            "primary_LP_infeasibility_observed":False,
            "transport_or_B1_failure_observed":False,
            "R7R3_retest_authorized":False,
            "R7R5_new_protocol_freeze_authorized":True,
        }

        immutable_publish(out,{
            "PAD_Stream_POSTV16_AV1_D_R7_R4_Summary.json":json_bytes(summary),
            "POSTV16_AV1_D_R7_R4_R7R3_Failure_Closure.json":json_bytes(closure),
            "POSTV16_AV1_D_R7_R4_Final_Gate_Matrix.csv":csv_bytes(
                [{"gate":k,**v} for k,v in gates.items()]
            ),
        })

        rows=[]
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name!="POSTV16_AV1_D_R7_R4_Artifact_Manifest.csv":
                rows.append({"file":p.name,"sha256":sha256_file(p),"bytes":p.stat().st_size})
        immutable_publish(
            out,
            {"POSTV16_AV1_D_R7_R4_Artifact_Manifest.csv":csv_bytes(rows)}
        )

        print("\n"+"="*188)
        print("POSTV16-AV1-D-R7-R4: PASS")
        print("="*188)
        print(f"{'Status':106}: {STATUS_PASS}")
        print(f"{'Immutable R7-R3 result':106}: FAIL")
        print(f"{'Failed gate':106}: {EXPECTED_FAILED_GATE}")
        print(f"{'Primary optimum':106}: {primary:.15e}")
        print(f"{'Tie solution primary cost':106}: {tie:.15e}")
        print(f"{'Allowed primary-cost increase':106}: {tol:.15e}")
        print(f"{'Actual primary-cost increase':106}: {diff:.15e}")
        print(f"{'Overrun beyond frozen limit':106}: {overrun:.15e}")
        print(f"{'Overrun relative to primary optimum':106}: {overrun_rel_primary:.15e}")
        print(f"{'Primary LP infeasibility observed':106}: False")
        print(f"{'Transport checkpoint / B1 failure observed':106}: False / False")
        print(f"{'R7-R3 retest authorized':106}: False")
        print(f"{'New numerical-certification protocol freeze authorized':106}: True")
        print(f"{'NEXT':106}: POSTV16-AV1-D-R7-R5 — prospective deterministic numerical-certification redesign/freeze")
        print("="*188)
        return 0

    except Exception as e:
        blocked.mkdir(parents=True,exist_ok=True)
        rep={
            "milestone":MILESTONE,
            "status":STATUS_BLOCKED,
            "failed_stage":stage,
            "exception":repr(e),
            "gates":gates,
            "model_inference_performed":False,
            "LP_resolve_performed":False,
            "R7R3_result_changed":False,
            "R7R5_authorized":False,
            "next_action":"Audit only the R7-R4 closure. Do not rerun or modify R7-R3.",
        }
        data=json_bytes(rep)
        p=blocked/"POSTV16_AV1_D_R7_R4_Blocked_Report.json"
        if p.exists() and p.read_bytes()!=data:
            p=blocked/f"POSTV16_AV1_D_R7_R4_Blocked_Report_{hashlib.sha256(data).hexdigest()[:12]}.json"
        if not p.exists():
            p.write_bytes(data)

        print("\n"+"="*188)
        print("POSTV16-AV1-D-R7-R4: BLOCKED")
        print("="*188)
        print("Failed stage:",stage)
        print("Exception:",repr(e))
        print("Report:",p)
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
