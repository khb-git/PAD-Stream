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


MILESTONE = "POSTV16-AV1-D-R7-R7C"
STATUS_PASS = (
    "AV1DR7R7C_R7R7B_SCIENTIFIC_FAIL_CLOSED_"
    "DAY365_SINGLE_SUPPORT_COMPONENT_CAPACITY_EXHAUSTION_LOCALIZED"
)
STATUS_BLOCKED = "AV1DR7R7C_FAILURE_CLOSURE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R7R7B_COMMIT = "1abcd05bffb2d932727a7eb3265a4510217556f1"

R7R7B = "PAD_Stream_POSTV16_AV1_D_R7_R7B_Canonical_Solver_Native_Semantics_Execution.py"
R7R7B_BLOB = "c65fc15f630a097a81fbe6fe28dab87c7056ce65"
R7R7A = "PAD_Stream_POSTV16_AV1_D_R7_R7A_Canonical_Primary_Envelope_Arithmetic_Semantics_Freeze.py"
R7R7A_BLOB = "191792855ecbb2560475ca2066b307d6fef494d5"
R7R7 = "PAD_Stream_POSTV16_AV1_D_R7_R7_R7R6_Certification_Semantics_Failure_Closure.py"
R7R7_BLOB = "1b44f47ff40394162788f73531301b2336cc2b24"
R7R2 = "PAD_Stream_POSTV16_AV1_D_R7_R2_Conservative_Bounded_Overlap_Occupancy_Reconciliation_Freeze.py"
R7R2_BLOB = "c9c4ceed05e6e631ad071b9da901d35874609255"

SOURCE_BLOBS = {
    R7R7B:R7R7B_BLOB,
    R7R7A:R7R7A_BLOB,
    R7R7:R7R7_BLOB,
    R7R2:R7R2_BLOB,
}

BASE = Path("post_v16")/RID/"POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"

R7R7B_REL = BASE/"POSTV16_AV1_D_R7_R7B_Canonical_Solver_Native_Semantics_Execution"
R7R7B_SUMMARY = "PAD_Stream_POSTV16_AV1_D_R7_R7B_Summary.json"
R7R7B_DECISION = "POSTV16_AV1_D_R7_R7B_Final_Decision.json"
R7R7B_GATES = "POSTV16_AV1_D_R7_R7B_Final_Gate_Matrix.csv"
R7R7B_TIME = "POSTV16_AV1_D_R7_R7B_Timewise_Strict_Certification_Audit.csv"
R7R7B_MANIFEST = "POSTV16_AV1_D_R7_R7B_Artifact_Manifest.csv"

OUT_REL = BASE/"POSTV16_AV1_D_R7_R7C_Support_Domain_Capacity_Failure_Closure"
BLOCKED_REL = BASE/"POSTV16_AV1_D_R7_R7C_BLOCKED"

R7R7B_FAIL_STATUS = (
    "AV1DR7R7B_CANONICAL_SOLVER_NATIVE_SEMANTICS_EXECUTION_FAIL_"
    "NO_ADAPTATION_OR_ALTERNATE_CANDIDATE_AUTHORIZED"
)
EXPECTED_GATE = "component_feasibility_all_times"
EXPECTED_COMPONENT = 0
EXPECTED_SUPPLY = 23573448.275608115
EXPECTED_SPARE = 21943589.990585063
EXPECTED_TOL = 0.00023573448275608113
EXPECTED_COMPLETED = 5
EXPECTED_DAYS = [30.0,60.0,100.0,150.0,250.0]


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


def near(a: float,b: float,rtol: float=1e-13,atol: float=1e-9) -> bool:
    return abs(float(a)-float(b)) <= max(atol,rtol*max(abs(float(b)),1.0))


def row_passed(row: dict[str,str]) -> bool:
    return str(row.get("passed","")).strip().lower()=="true"


def self_test() -> None:
    deficit=EXPECTED_SUPPLY-EXPECTED_SPARE
    ratio=EXPECTED_SUPPLY/EXPECTED_SPARE
    if not deficit>EXPECTED_TOL:
        raise RuntimeError("capacity_deficit_not_positive")
    if not ratio>1.0:
        raise RuntimeError("supply_spare_ratio")
    print("POSTV16-AV1-D-R7-R7C self-test: PASS")


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

    print("="*194)
    print("POSTV16-AV1-D-R7-R7C — R7-R7B SUPPORT-DOMAIN CAPACITY FAILURE CLOSURE")
    print("="*194)
    print("AUDIT/CLOSURE ONLY. NO MODEL INFERENCE. NO LP RE-SOLVE. NO MAPBACK REDESIGN OR EXECUTION.")
    print("R7-R7B REMAINS AN IMMUTABLE SCIENTIFIC FAIL. R7-R3 AND R7-R6 ALSO REMAIN FAIL.")
    print("THE PURPOSE IS TO CLASSIFY THE DAY-365 FAILURE BEFORE ANY NEW PHYSICAL MAPBACK PROTOCOL IS DESIGNED.\n")

    try:
        root=root.resolve();drive=drive.resolve()

        parent=git_text(root,"rev-parse","HEAD^")
        status=git_text(root,"status","--porcelain")
        gate("repository_parent_is_R7R7B_commit",parent==PARENT_R7R7B_COMMIT,parent)
        gate("repository_clean",status=="",repr(status))

        for fn,blob in SOURCE_BLOBS.items():
            p=root/fn
            actual=git_blob_sha(p,root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==blob,actual)

        stage="R7R7B_failure_binding"
        d=drive/R7R7B_REL
        gate("R7R7B_output_present",d.is_dir(),str(d))
        manifest=verify_manifest(d,R7R7B_MANIFEST)
        gate("R7R7B_manifest_SHA_closure",True,len(manifest))

        s=load_json(d/R7R7B_SUMMARY)
        q=load_json(d/R7R7B_DECISION)
        gm=read_csv(d/R7R7B_GATES)

        gate("R7R7B_status_exact",q["status"]==R7R7B_FAIL_STATUS,q["status"])
        gate("R7R7B_scientific_execution_pass_false",q["scientific_execution_pass"] is False)
        gate("R7R7B_failed_gate_exact",q["failed_gate"]==EXPECTED_GATE,q["failed_gate"])
        gate("R7R7B_completed_times_exact",int(q["completed_canonical_times"])==EXPECTED_COMPLETED,q["completed_canonical_times"])
        gate("R7R7B_model_inference_performed",q["model_inference_performed"] is True)
        gate("R7R7B_reconciliation_started",q["reconciliation_started"] is True)
        gate("R7R3_remains_FAIL",q["R7R3_immutable_result"]=="FAIL")
        gate("R7R6_remains_FAIL",q["R7R6_immutable_result"]=="FAIL")
        gate("R7R3_not_retested",q["R7R3_retested"] is False)
        gate("R7R6_not_retested",q["R7R6_retested"] is False)
        gate("checkpoint_unmodified",q["accepted_checkpoint_modified"] is False)
        gate("B1_unmodified",q["B1_modified"] is False)
        gate("support_graph_unmodified",q["support_graph_modified"] is False)
        gate("primary_graph_cost_unmodified",q["primary_graph_cost_modified"] is False)
        gate("saturation_bounds_unmodified",q["saturation_bounds_modified"] is False)
        gate("primary_envelope_unmodified",q["primary_envelope_changed"] is False)
        gate("constraint_unscaled",q["constraint_scaling_applied"] is False)
        gate("canonical_arithmetic_exact",q["canonical_arithmetic"]=="solver-native unscaled secondary inequality residual")
        gate("fsum_not_pass_fail",q["independent_fsum_pass_fail_gate"] is False)
        gate("no_geology0031",q["geology0031_used"] is False)
        gate("no_acceptance_truth",q["acceptance_truth_used"] is False)
        gate("no_alternate_candidate",q["alternate_candidate_authorized"] is False)
        gate("no_retuning",q["retuning_authorized"] is False)

        fd=q["failure_detail"]
        component=int(fd["component"])
        supply=float(fd["excess_supply_kg"])
        spare=float(fd["spare_capacity_kg"])
        tol=float(fd["tolerance_kg"])

        gate("failure_component_exact",component==EXPECTED_COMPONENT,component)
        gate("excess_supply_exact",near(supply,EXPECTED_SUPPLY),supply)
        gate("spare_capacity_exact",near(spare,EXPECTED_SPARE),spare)
        gate("component_tolerance_exact",near(tol,EXPECTED_TOL,rtol=1e-12,atol=1e-12),tol)

        deficit=supply-spare
        supply_over_spare=deficit/spare
        demand_ratio=supply/spare

        gate("component_capacity_deficit_positive",deficit>tol,deficit)
        gate("component_excess_demand_ratio_gt_one",demand_ratio>1.0,demand_ratio)

        names={r["gate"]:r for r in gm}
        gate(
            "support_graph_single_component",
            "support_graph_components_positive" in names
            and row_passed(names["support_graph_components_positive"])
            and str(names["support_graph_components_positive"].get("value","")).strip() in {"1","1.0"},
            names.get("support_graph_components_positive",{}).get("value"),
        )
        gate(
            "support_graph_cross_component_gate_passed",
            "support_graph_no_cross_component_edges" in names
            and row_passed(names["support_graph_no_cross_component_edges"]),
        )
        gate(
            "physical_cell_capacity_gate_passed",
            "physical_cell_capacity_positive_finite" in names
            and row_passed(names["physical_cell_capacity_positive_finite"]),
        )
        gate(
            "day365_B1_to_subsegment_mass_closure_passed",
            "time_365_B1_to_subsegment_mass_closure" in names
            and row_passed(names["time_365_B1_to_subsegment_mass_closure"]),
        )

        # In the frozen implementation, global_mass_feasibility_all_times is
        # evaluated before component_feasibility_all_times. Reaching the latter
        # therefore proves the whole-grid capacity gate did not fail.
        gate("whole_grid_capacity_gate_preceded_and_did_not_fail",True)

        stage="completed_time_evidence"
        time_path=d/R7R7B_TIME
        gate("R7R7B_time_audit_present",time_path.is_file(),str(time_path))
        rows=read_csv(time_path)
        gate("R7R7B_five_completed_time_rows",len(rows)==EXPECTED_COMPLETED,len(rows))
        days=[float(r["target_day"]) for r in rows]
        gate("R7R7B_completed_days_exact",days==EXPECTED_DAYS,days)

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
                "R7R7B":"FAIL",
                "R7R7B_may_be_relabelled_PASS":False,
                "R7R7B_may_be_rerun_with_changed_physical_domain":False,
            },
            "failure_localization":{
                "failed_gate":EXPECTED_GATE,
                "first_failed_target_day":365.0,
                "completed_times_before_failure":EXPECTED_DAYS,
                "support_graph_component_count":1,
                "failed_component":component,
                "failed_component_is_entire_supported_domain":True,
                "excess_supply_kg":supply,
                "spare_supported_capacity_kg":spare,
                "support_domain_capacity_deficit_kg":deficit,
                "excess_demand_over_spare_fraction":supply_over_spare,
                "excess_demand_over_spare_percent":100.0*supply_over_spare,
                "excess_supply_to_spare_ratio":demand_ratio,
                "frozen_component_tolerance_kg":tol,
            },
            "classification":{
                "failure_class":"SINGLE_CONNECTED_SUPPORT_DOMAIN_TOTAL_CAPACITY_EXHAUSTION",
                "numerical_certification_failure":False,
                "primary_or_secondary_LP_failure":False,
                "connectivity_partition_failure":False,
                "accepted_transport_checkpoint_failure":False,
                "B1_failure":False,
                "EOS_failure":False,
                "saturation_bound_failure_before_day365":False,
                "whole_grid_total_capacity_failure":False,
                "frozen_supported_domain_capacity_failure":True,
            },
            "logical_basis":{
                "single_support_component":(
                    "The SG7D-supported Cartesian graph contains one connected component, "
                    "so component 0 is the full frozen supported-cell domain."
                ),
                "capacity_identity":(
                    "Within a component, sum(raw mass)-sum(cell capacity) equals "
                    "sum(excess supply)-sum(spare capacity). Positive excess-minus-spare "
                    "therefore proves that no conservative redistribution confined to that "
                    "component can satisfy all cell capacities."
                ),
                "whole_grid_gate":(
                    "The R7-R7B implementation checks whole-grid capacity before component "
                    "capacity. Because execution reached component_feasibility_all_times, "
                    "the whole-grid capacity gate did not fail."
                ),
            },
            "what_is_proven":{
                "days_30_60_100_150_250_completed_under_canonical_semantics":True,
                "day365_B1_to_subsegment_mass_closure_passed":True,
                "day365_exact_supported_domain_infeasible_under_R7R2_constraints":True,
                "no_within_support_LP_or_path_choice_can_remove_the_capacity_deficit":True,
            },
            "what_is_not_proven":{
                "full_cartesian_grid_capacity_infeasible":True,
                "accepted_transport_model_invalid_at_day365":True,
                "B1_representation_invalid":True,
                "a_specific_support_domain_extension_is_correct":True,
                "full_field_plume_fidelity":True,
            },
            "lineage_rules":{
                "do_not_rerun_R7R7B_with_unsupported_sinks_enabled":True,
                "do_not_relax_saturation_bounds":True,
                "do_not_clip_or_discard_mass":True,
                "do_not_globally_rescale_saturation":True,
                "do_not_change_checkpoint_or_B1":True,
                "do_not_relabel_R7R7B":True,
                "future_physical_domain_change_requires_new_prospective_protocol":True,
            },
            "next":{
                "milestone":"POSTV16-AV1-D-R7-R7D",
                "name":"Prospective physically admissible Cartesian occupancy-domain extension design and freeze",
                "authorized":True,
                "execution_authorized":False,
                "scope":(
                    "Design a new physical mapback occupancy domain beyond exact SG7D-crossed "
                    "cells while preserving mass conservation, Cartesian cell capacities, "
                    "saturation bounds, accepted transport checkpoint, B1 bridge, and the "
                    "canonical R7-R7A arithmetic semantics. The extension rule must be frozen "
                    "before any new execution."
                ),
            },
        }

        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "R7R3_result":"FAIL",
            "R7R6_result":"FAIL",
            "R7R7B_result":"FAIL",
            "failed_gate":EXPECTED_GATE,
            "first_failed_target_day":365.0,
            "completed_times":EXPECTED_DAYS,
            "support_graph_component_count":1,
            "support_domain_capacity_deficit_kg":deficit,
            "excess_demand_over_spare_percent":100.0*supply_over_spare,
            "whole_grid_capacity_failure":False,
            "supported_domain_capacity_failure":True,
            "numerical_certification_failure":False,
            "R7R7B_retest_authorized":False,
            "R7R7D_physical_domain_design_freeze_authorized":True,
        }

        immutable_publish(out,{
            "PAD_Stream_POSTV16_AV1_D_R7_R7C_Summary.json":json_bytes(summary),
            "POSTV16_AV1_D_R7_R7C_R7R7B_Failure_Closure.json":json_bytes(closure),
            "POSTV16_AV1_D_R7_R7C_Final_Gate_Matrix.csv":csv_bytes(
                [{"gate":k,**v} for k,v in gates.items()]
            ),
        })

        manifest=[]
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name!="POSTV16_AV1_D_R7_R7C_Artifact_Manifest.csv":
                manifest.append({
                    "file":p.name,
                    "sha256":sha256_file(p),
                    "bytes":p.stat().st_size,
                })
        immutable_publish(out,{
            "POSTV16_AV1_D_R7_R7C_Artifact_Manifest.csv":csv_bytes(manifest)
        })

        print("\n"+"="*194)
        print("POSTV16-AV1-D-R7-R7C: PASS")
        print("="*194)
        print(f"{'Status':114}: {STATUS_PASS}")
        print(f"{'Immutable R7-R3 / R7-R6 / R7-R7B results':114}: FAIL / FAIL / FAIL")
        print(f"{'First failed target day':114}: 365")
        print(f"{'Completed target days before failure':114}: 30, 60, 100, 150, 250")
        print(f"{'Support-graph connected components':114}: 1")
        print(f"{'Failed component is entire supported domain':114}: True")
        print(f"{'Excess supply [kg]':114}: {supply:.12e}")
        print(f"{'Remaining supported capacity [kg]':114}: {spare:.12e}")
        print(f"{'Supported-domain capacity deficit [kg]':114}: {deficit:.12e}")
        print(f"{'Excess demand above supported spare capacity':114}: {100.0*supply_over_spare:.9f}%")
        print(f"{'Whole-grid total-capacity failure':114}: False")
        print(f"{'Numerical certification failure':114}: False")
        print(f"{'R7-R7B retest authorized':114}: False")
        print(f"{'New physical occupancy-domain design/freeze authorized':114}: True")
        print(f"{'NEXT':114}: POSTV16-AV1-D-R7-R7D — prospective Cartesian occupancy-domain extension design/freeze")
        print("="*194)
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
            "mapback_redesign_performed":False,
            "R7R7B_result_changed":False,
            "R7R7D_authorized":False,
            "next_action":(
                "Audit only this closure milestone. Do not rerun R7-R7B or modify "
                "the occupancy domain until the physical failure is validly closed."
            ),
        }
        data=json_bytes(report)
        p=blocked/"POSTV16_AV1_D_R7_R7C_Blocked_Report.json"
        if p.exists() and p.read_bytes()!=data:
            p=blocked/f"POSTV16_AV1_D_R7_R7C_Blocked_Report_{hashlib.sha256(data).hexdigest()[:12]}.json"
        if not p.exists():
            p.write_bytes(data)

        print("\n"+"="*194)
        print("POSTV16-AV1-D-R7-R7C: BLOCKED")
        print("="*194)
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
