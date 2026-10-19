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


MILESTONE = "POSTV16-AV1-D-R7-R5"
STATUS_PASS = (
    "AV1DR7R5_DETERMINISTIC_NUMERICAL_CERTIFICATION_REDESIGN_"
    "PROSPECTIVELY_FROZEN_PHYSICAL_RECONCILIATION_UNCHANGED"
)
STATUS_BLOCKED = "AV1DR7R5_NUMERICAL_CERTIFICATION_FREEZE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R7R4_COMMIT = "ec5053770d62c360fcfe21159795038da2bc5fb2"

R7R4 = "PAD_Stream_POSTV16_AV1_D_R7_R4_R7R3_Tiebreak_Certification_Failure_Closure.py"
R7R4_BLOB = "687aa4580c85b8a188e4d2e2dc0493b2f25dc97f"
R7R3 = "PAD_Stream_POSTV16_AV1_D_R7_R3_Controlled_Frozen_Reconciliation_Execution.py"
R7R3_BLOB = "a431ac9d4faa3fdf0ecf415c36208ac31c797ad0"
R7R2 = "PAD_Stream_POSTV16_AV1_D_R7_R2_Conservative_Bounded_Overlap_Occupancy_Reconciliation_Freeze.py"
R7R2_BLOB = "c9c4ceed05e6e631ad071b9da901d35874609255"
R6 = "PAD_Stream_POSTV16_AV1_D_R6_Accepted_PIRNN_Deployment_Promotion_and_Canonical_Runtime_Binding.py"
R6_BLOB = "1ca67ca946683eeb31fbba7d31fba2613d5c0f6f"
B1 = "PAD_Stream_POSTV16_AV1_B1_R1_C26_to_E37A_Component_Mass_Representation_Equivalence_Audit.py"
B1_BLOB = "8d9561d7c85805b82dedc26073c4633f90eeeab6"
E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"

SOURCE_BLOBS = {
    R7R4:R7R4_BLOB,
    R7R3:R7R3_BLOB,
    R7R2:R7R2_BLOB,
    R6:R6_BLOB,
    B1:B1_BLOB,
    E37A:E37A_BLOB,
    SG7D:SG7D_BLOB,
}

BASE = Path("post_v16")/RID/"POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"

R7R4_REL = BASE/"POSTV16_AV1_D_R7_R4_R7R3_Tiebreak_Certification_Failure_Closure"
R7R4_SUMMARY = "PAD_Stream_POSTV16_AV1_D_R7_R4_Summary.json"
R7R4_CLOSURE = "POSTV16_AV1_D_R7_R4_R7R3_Failure_Closure.json"
R7R4_MANIFEST = "POSTV16_AV1_D_R7_R4_Artifact_Manifest.csv"

R7R2_REL = BASE/"POSTV16_AV1_D_R7_R2_Conservative_Bounded_Overlap_Occupancy_Reconciliation_Freeze"
R7R2_PROTOCOL = "POSTV16_AV1_D_R7_R2_Frozen_Reconciliation_Protocol.json"
R7R2_MANIFEST = "POSTV16_AV1_D_R7_R2_Artifact_Manifest.csv"

OUT_REL = BASE/"POSTV16_AV1_D_R7_R5_Deterministic_Numerical_Certification_Redesign_Freeze"
BLOCKED_REL = BASE/"POSTV16_AV1_D_R7_R5_BLOCKED"

R7R4_STATUS = (
    "AV1DR7R4_R7R3_SCIENTIFIC_FAIL_CLOSED_"
    "SECONDARY_TIEBREAK_PRIMARY_OPTIMUM_CERTIFICATION_OVERRUN_LOCALIZED"
)
R7R3_FAIL_STATUS = (
    "AV1DR7R3_FROZEN_SUPPORT_GRAPH_RECONCILIATION_EXECUTION_FAIL_"
    "NO_ADAPTATION_OR_ALTERNATE_REPAIR_AUTHORIZED"
)
R7R2_PROTOCOL_ID = "POSTV16_AV1_D_R7_R2_SUPPORT_GRAPH_MIN_COST_EXCESS_MASS_RECONCILIATION_V1"
NEW_PROTOCOL_ID = "POSTV16_AV1_D_R7_R5_STRICT_HIGHS_DS_NUMERICAL_CERTIFICATION_V1"

PRIMARY_FEAS_TOL = 1.0e-10
DUAL_FEAS_TOL = 1.0e-10
FINAL_CERT_GUARD = 1.0e-8


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
    primary=76140261.34928446
    tol_obj=max(1.0e-8,1.0e-12*max(abs(primary),1.0))
    if abs(tol_obj-7.614026134928446e-05)>1e-15:
        raise RuntimeError("primary_envelope_formula_changed")
    if PRIMARY_FEAS_TOL!=1e-10 or DUAL_FEAS_TOL!=1e-10:
        raise RuntimeError("solver_tolerance")
    if FINAL_CERT_GUARD!=1e-8:
        raise RuntimeError("cert_guard")
    print("POSTV16-AV1-D-R7-R5 self-test: PASS")


def main(root: Path,drive: Path) -> int:
    gates={};stage="preflight"
    out=drive/OUT_REL;blocked=drive/BLOCKED_REL

    def gate(name: str,passed: Any,value: Any=None) -> None:
        ok=bool(passed)
        gates[name]={"passed":ok,"value":value}
        suffix=f" — {value}" if value is not None else ""
        print(f"[{'PASS' if ok else 'FAIL'}] {name}{suffix}")
        if not ok:
            raise GateError(name)

    print("="*188)
    print("POSTV16-AV1-D-R7-R5 — DETERMINISTIC NUMERICAL-CERTIFICATION REDESIGN / FREEZE")
    print("="*188)
    print("FREEZE ONLY. NO MODEL INFERENCE. NO LP EXECUTION ON FOUNDATION CASE 0001. NO RECONCILIATION RETEST.")
    print("R7-R3 REMAINS FAIL. R7-R2 PHYSICAL RECONCILIATION OPERATOR IS UNCHANGED.")
    print("ONLY THE NUMERICAL SOLVER/CERTIFICATION IMPLEMENTATION FOR A NEW FUTURE EXECUTION IS REDEFINED.\n")

    try:
        root=root.resolve();drive=drive.resolve()

        parent=git_text(root,"rev-parse","HEAD^")
        status=git_text(root,"status","--porcelain")
        gate("repository_parent_is_R7R4_commit",parent==PARENT_R7R4_COMMIT,parent)
        gate("repository_clean",status=="",repr(status))

        for fn,blob in SOURCE_BLOBS.items():
            p=root/fn
            actual=git_blob_sha(p,root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",actual==blob,actual)

        stage="failure_closure_binding"

        r7r4=drive/R7R4_REL
        gate("R7R4_output_present",r7r4.is_dir(),str(r7r4))
        m4=verify_manifest(r7r4,R7R4_MANIFEST)
        gate("R7R4_manifest_SHA_closure",True,len(m4))

        s4=load_json(r7r4/R7R4_SUMMARY)
        c4=load_json(r7r4/R7R4_CLOSURE)

        gate("R7R4_status_exact",s4["status"]==R7R4_STATUS,s4["status"])
        gate("R7R3_result_remains_FAIL",s4["R7R3_result"]=="FAIL")
        gate("R7R3_failed_gate_bound",s4["failed_gate"]=="tiebreak_preserves_primary_optimum")
        gate("R7R3_primary_LP_infeasibility_not_observed",s4["primary_LP_infeasibility_observed"] is False)
        gate("R7R3_transport_or_B1_failure_not_observed",s4["transport_or_B1_failure_observed"] is False)
        gate("R7R3_retest_forbidden",s4["R7R3_retest_authorized"] is False)
        gate("new_protocol_freeze_authorized",s4["R7R5_new_protocol_freeze_authorized"] is True)

        cls=c4["classification"]
        gate("closure_failure_is_numerical_certification",cls["failure_mechanism"]=="NUMERICAL_CERTIFICATION_OVERRUN_OF_SECONDARY_TIEBREAK_PRIMARY_OPTIMUM_ENVELOPE")
        gate("closure_not_primary_LP_infeasible",cls["failure_is_primary_LP_infeasibility"] is False)
        gate("closure_not_capacity_infeasible",cls["failure_is_component_capacity_infeasibility"] is False)
        gate("closure_not_mass_conservation_failure",cls["failure_is_mass_conservation_failure"] is False)
        gate("closure_not_saturation_bound_failure",cls["failure_is_saturation_bound_failure"] is False)
        gate("closure_not_checkpoint_failure",cls["failure_is_transport_checkpoint_failure"] is False)

        rules=c4["lineage_rules"]
        gate("R7R3_changed_tolerance_rerun_forbidden",rules["R7R3_may_be_rerun_with_changed_tolerance"] is False)
        gate("R7R3_changed_solver_rerun_forbidden",rules["R7R3_may_be_rerun_with_changed_solver_settings"] is False)
        gate("future_new_protocol_required",rules["future_new_protocol_must_have_new_milestone_and_new_freeze"] is True)

        stage="physical_operator_identity_binding"

        r7r2=drive/R7R2_REL
        gate("R7R2_output_present",r7r2.is_dir(),str(r7r2))
        m2=verify_manifest(r7r2,R7R2_MANIFEST)
        gate("R7R2_manifest_SHA_closure",True,len(m2))
        p2=load_json(r7r2/R7R2_PROTOCOL)

        gate("R7R2_protocol_id_exact",p2["protocol_id"]==R7R2_PROTOCOL_ID,p2["protocol_id"])
        gate("R7R2_primary_edge_cost_identity",
             p2["minimum_cost_flow"]["primary_edge_cost_units"]==
             "5*abs(delta_i) + 5*abs(delta_j) + abs(delta_k); 20-ft x/y cells therefore cost 5 units and 4-ft z cells cost 1 unit")
        gate("R7R2_base_mass_identity",p2["mass_bookkeeping"]["base_mass"]=="b_c = min(m_c, C_c)")
        gate("R7R2_excess_supply_identity",p2["mass_bookkeeping"]["excess_supply"]=="e_c = max(m_c - C_c, 0)")
        gate("R7R2_spare_capacity_identity",p2["mass_bookkeeping"]["spare_capacity"]=="d_c = C_c - b_c")
        gate("R7R2_support_graph_domain_unchanged",p2["support_graph"]["unsupported_cells_eligible"] is False)
        gate("R7R2_cross_component_transfer_unchanged",p2["support_graph"]["cross_component_mass_transfer_allowed"] is False)
        gate("R7R2_Smax_unchanged",p2["prohibitions"]["relax_Smax_above_0p80"] is True)
        gate("R7R2_B1_unchanged",p2["prohibitions"]["change_B1_half_overlap"] is True)
        gate("R7R2_checkpoint_unchanged",p2["prohibitions"]["change_accepted_checkpoint"] is True)

        stage="freeze_new_numerical_certification"

        redesigned={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "protocol_id":NEW_PROTOCOL_ID,
            "lineage":{
                "R7R3_immutable_result":R7R3_FAIL_STATUS,
                "R7R3_relabelled_or_retested":False,
                "R7R4_closure_commit":PARENT_R7R4_COMMIT,
                "R7R4_runner_blob":R7R4_BLOB,
                "physical_reconciliation_authority":R7R2_PROTOCOL_ID,
                "physical_reconciliation_changed":False,
            },
            "unchanged_physical_operator":{
                "raw_mass_and_capacity_bookkeeping":"exact R7-R2",
                "support_graph":"exact R7-R2 SG7D-supported Cartesian-cell graph",
                "primary_edge_cost":"5*|Δi| + 5*|Δj| + |Δk|",
                "connected_component_isolation":True,
                "unsupported_cells_as_sinks":False,
                "B1_half_overlap_projection":"unchanged",
                "accepted_R6_checkpoint":"unchanged",
                "C3_normalization":"unchanged",
                "saturation_bounds":[0.20,0.80],
                "EOS_inversion":"unchanged frozen R2",
            },
            "redesigned_numerical_execution":{
                "LP_method":"highs-ds",
                "presolve":True,
                "primal_feasibility_tolerance":PRIMARY_FEAS_TOL,
                "dual_feasibility_tolerance":DUAL_FEAS_TOL,
                "solver_options_fixed":True,
                "node_edge_variable_ordering":"unchanged exact R7-R2/R7-R3 fixed ordering",
                "primary_LP":{
                    "objective":"unchanged R7-R2 graph-distance objective",
                    "reported_solver_fun_not_used_as_certification_authority":True,
                    "certified_primary_objective_recomputation":"math.fsum(float(c_i)*float(x_i) for all variables in fixed variable order)",
                },
                "primary_objective_envelope":{
                    "formula":"tol_obj = max(1e-8, 1e-12*max(abs(primary_optimum),1))",
                    "formula_changed_from_R7R2":False,
                },
                "secondary_tiebreak_LP":{
                    "objective":"unchanged normalized lexicographic edge-flow rank plus normalized recipient-absorption rank",
                    "primary_constraint":"c_primary @ x <= certified_primary_optimum + tol_obj",
                    "solver_method":"highs-ds",
                    "primal_feasibility_tolerance":PRIMARY_FEAS_TOL,
                    "dual_feasibility_tolerance":DUAL_FEAS_TOL,
                    "presolve":True,
                },
                "secondary_certification":{
                    "certified_primary_cost_recomputation":"math.fsum(float(c_i)*float(x_i) for all variables in fixed variable order)",
                    "frozen_gate":"certified_tie_primary_cost <= certified_primary_optimum + tol_obj + 1e-8",
                    "final_additive_numerical_guard":FINAL_CERT_GUARD,
                    "final_guard_changed_from_R7R3":False,
                    "explicit_inequality_slack_gate":"secondary.ineqlin.residual[0] >= -1e-8",
                    "primary_and_secondary_solver_success_required":True,
                },
            },
            "reason_for_redesign":{
                "observed_R7R3_overrun_kg_cost_units":float(s4["overrun"]),
                "observed_R7R3_overrun_relative_to_primary":float(s4["overrun_relative_to_primary"]),
                "diagnosis":(
                    "R7-R3 used the HiGHS default 1e-7 feasibility tolerances while "
                    "certifying the secondary primary-objective envelope with a tighter "
                    "1e-8 final guard. The new protocol makes the solver feasibility "
                    "tolerances explicitly stricter than the certification guard and "
                    "recomputes objective values in fixed order using math.fsum."
                ),
                "tolerance_widening_used":False,
                "physical_gate_relaxed":False,
            },
            "hard_gates_for_R7R6":{
                "all_R7R2_physical_gates_unchanged":True,
                "all_9_canonical_times":True,
                "primary_LP_success_all_times":True,
                "secondary_LP_success_all_times":True,
                "secondary_inequality_slack_gate_all_times":True,
                "secondary_primary_objective_certification_all_times":True,
                "node_balance_mass_capacity_bounds_EOS_gates_unchanged":True,
                "accepted_checkpoint_B1_C3_unchanged":True,
                "no_geology0031_or_acceptance_truth":True,
            },
            "prohibitions":{
                "R7R3_rerun":True,
                "primary_envelope_widening":True,
                "final_1e8_guard_widening":True,
                "primary_graph_cost_change":True,
                "secondary_rank_objective_change":True,
                "support_graph_change":True,
                "unsupported_sink_addition":True,
                "saturation_bound_change":True,
                "checkpoint_change":True,
                "B1_change":True,
                "normalization_refit":True,
                "geology0031_use":True,
                "acceptance_truth_use":True,
            },
            "next":{
                "milestone":"POSTV16-AV1-D-R7-R6",
                "name":"Controlled execution of frozen strict numerical-certification protocol",
                "authorized":True,
                "candidate_count":1,
                "alternate_candidate_authorized":False,
            },
        }

        freeze={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "new_protocol_id":NEW_PROTOCOL_ID,
            "physical_R7R2_protocol_id":R7R2_PROTOCOL_ID,
            "R7R3_result_preserved_as_FAIL":True,
            "R7R3_retest_performed":False,
            "model_inference_performed":False,
            "LP_execution_on_foundation_case_performed":False,
            "physical_reconciliation_changed":False,
            "primary_objective_envelope_changed":False,
            "final_certification_guard_changed":False,
            "solver_method_and_feasibility_tolerances_prospectively_fixed":True,
            "objective_recomputation_method_prospectively_fixed":True,
            "candidate_count":1,
            "R7R6_execution_authorized":True,
        }

        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "new_protocol_id":NEW_PROTOCOL_ID,
            "R7R3_immutable_result":"FAIL",
            "R7R3_retest_performed":False,
            "physical_operator_changed":False,
            "primary_envelope_changed":False,
            "final_guard_changed":False,
            "new_LP_method":"highs-ds",
            "new_primal_feasibility_tolerance":PRIMARY_FEAS_TOL,
            "new_dual_feasibility_tolerance":DUAL_FEAS_TOL,
            "objective_certification":"math.fsum in fixed variable order",
            "model_inference_performed":False,
            "R7R6_authorized":True,
            "next":"POSTV16-AV1-D-R7-R6 — controlled execution of the single frozen strict numerical-certification protocol",
        }

        immutable_publish(out,{
            "PAD_Stream_POSTV16_AV1_D_R7_R5_Summary.json":json_bytes(summary),
            "POSTV16_AV1_D_R7_R5_Frozen_Numerical_Certification_Protocol.json":json_bytes(redesigned),
            "POSTV16_AV1_D_R7_R5_Protocol_Freeze_Contract.json":json_bytes(freeze),
            "POSTV16_AV1_D_R7_R5_Final_Gate_Matrix.csv":csv_bytes([{"gate":k,**v} for k,v in gates.items()]),
        })

        rows=[]
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name!="POSTV16_AV1_D_R7_R5_Artifact_Manifest.csv":
                rows.append({"file":p.name,"sha256":sha256_file(p),"bytes":p.stat().st_size})
        immutable_publish(out,{
            "POSTV16_AV1_D_R7_R5_Artifact_Manifest.csv":csv_bytes(rows)
        })

        print("\n"+"="*188)
        print("POSTV16-AV1-D-R7-R5: PASS")
        print("="*188)
        print(f"{'Status':108}: {STATUS_PASS}")
        print(f"{'R7-R3 immutable result':108}: FAIL")
        print(f"{'New numerical protocol':108}: {NEW_PROTOCOL_ID}")
        print(f"{'Physical R7-R2 reconciliation changed':108}: False")
        print(f"{'Primary objective envelope changed':108}: False")
        print(f"{'Final +1e-8 certification guard changed':108}: False")
        print(f"{'Fixed LP method':108}: highs-ds")
        print(f"{'Primal / dual feasibility tolerance':108}: 1e-10 / 1e-10")
        print(f"{'Objective certification':108}: math.fsum, fixed variable order")
        print(f"{'Model inference / Foundation LP execution in R7-R5':108}: False / False")
        print(f"{'R7-R6 single-candidate execution authorized':108}: True")
        print(f"{'NEXT':108}: POSTV16-AV1-D-R7-R6 — execute strict numerical-certification protocol")
        print("="*188)
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
            "model_inference_performed":False,
            "LP_execution_on_foundation_case_performed":False,
            "R7R6_authorized":False,
            "next_action":(
                "Audit only the R7-R5 provenance/protocol freeze. "
                "Do not rerun R7-R3 or execute an unfrozen numerical redesign."
            ),
        }
        data=json_bytes(report)
        p=blocked/"POSTV16_AV1_D_R7_R5_Blocked_Report.json"
        if p.exists() and p.read_bytes()!=data:
            p=blocked/f"POSTV16_AV1_D_R7_R5_Blocked_Report_{hashlib.sha256(data).hexdigest()[:12]}.json"
        if not p.exists():
            p.write_bytes(data)

        print("\n"+"="*188)
        print("POSTV16-AV1-D-R7-R5: BLOCKED")
        print("="*188)
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
