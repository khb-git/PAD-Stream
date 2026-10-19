#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, io, json, subprocess
from pathlib import Path
from typing import Any

MILESTONE = "POSTV16-AV1-D-R7-R2"
STATUS_PASS = (
    "AV1DR7R2_CONSERVATIVE_BOUNDED_SUPPORT_GRAPH_OVERLAP_OCCUPANCY_"
    "RECONCILIATION_PROTOCOL_PROSPECTIVELY_FROZEN"
)
STATUS_BLOCKED = "AV1DR7R2_RECONCILIATION_PROTOCOL_FREEZE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R7R1_COMMIT = "971cd4c3ca391360fe8329ff5a092ea4de2c4482"

R7R1 = "PAD_Stream_POSTV16_AV1_D_R7_R1_E37A_Mapback_Capacity_Failure_Localization.py"
R7R1_BLOB = "734fe31b3ff3cc6d40c33ebb9b0162b02e99a368"
R7 = "PAD_Stream_POSTV16_AV1_D_R7_Full_End_to_End_PAD_Stream_Integration.py"
R7_BLOB = "a28722b0b8059bd50d94fb8a914defc0b35f2f7b"
R6 = "PAD_Stream_POSTV16_AV1_D_R6_Accepted_PIRNN_Deployment_Promotion_and_Canonical_Runtime_Binding.py"
R6_BLOB = "1ca67ca946683eeb31fbba7d31fba2613d5c0f6f"
B1 = "PAD_Stream_POSTV16_AV1_B1_R1_C26_to_E37A_Component_Mass_Representation_Equivalence_Audit.py"
B1_BLOB = "8d9561d7c85805b82dedc26073c4633f90eeeab6"
R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"

SOURCE_BLOBS = {
    R7R1:R7R1_BLOB, R7:R7_BLOB, R6:R6_BLOB, B1:B1_BLOB,
    R2:R2_BLOB, E37A:E37A_BLOB, SG7D:SG7D_BLOB,
}

BASE = Path("post_v16")/RID/"POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
R7R1_REL = BASE/"POSTV16_AV1_D_R7_R1_E37A_Mapback_Capacity_Failure_Localization"
R7R1_SUMMARY = "PAD_Stream_POSTV16_AV1_D_R7_R1_Summary.json"
R7R1_DIAG = "POSTV16_AV1_D_R7_R1_Failure_Localization_Diagnosis.json"
R7R1_AUDIT = "POSTV16_AV1_D_R7_R1_Overloaded_Cell_Audit.csv"
R7R1_MANIFEST = "POSTV16_AV1_D_R7_R1_Artifact_Manifest.csv"

OUT_REL = BASE/"POSTV16_AV1_D_R7_R2_Conservative_Bounded_Overlap_Occupancy_Reconciliation_Freeze"
BLOCKED_REL = BASE/"POSTV16_AV1_D_R7_R2_BLOCKED"

R7R1_STATUS = (
    "AV1DR7R1_E37A_DAY30_MAPBACK_CAPACITY_FAILURE_LOCALIZED_"
    "NO_REPAIR_SELECTED"
)

EXPECTED_OVERLOADED = 546
EXPECTED_WORST = [4,24,24]
EXPECTED_MAX_EXCESS = 9471.745379391963
EXPECTED_WORST_CAPACITY_RATIO = 3.499091567765
EXPECTED_WORST_COVERAGE_RATIO = 3.971093980018
EXPECTED_WORST_STREAMLINES = 49
EXPECTED_GLOBAL_CAPACITY_FRACTION = 0.12712205868832774

PROTOCOL_ID = "POSTV16_AV1_D_R7_R2_SUPPORT_GRAPH_MIN_COST_EXCESS_MASS_RECONCILIATION_V1"

class GateError(RuntimeError):
    pass

def sha256_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):
            h.update(b)
    return h.hexdigest()

def git_text(root:Path,*args:str)->str:
    p=subprocess.run(
        ["git","-C",str(root),*args],check=True,text=True,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE
    )
    return p.stdout.strip()

def git_blob_sha(p:Path,root:Path)->str:
    return git_text(root,"hash-object",str(p))

def load_json(p:Path)->dict[str,Any]:
    return json.loads(p.read_text(encoding="utf-8"))

def read_csv(p:Path)->list[dict[str,str]]:
    with p.open("r",newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))

def verify_manifest(d:Path,name:str)->dict[str,str]:
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

def json_bytes(x:Any)->bytes:
    return (json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+"\n").encode()

def csv_bytes(rows:list[dict[str,Any]])->bytes:
    if not rows:return b""
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields:fields.append(k)
    s=io.StringIO(newline="")
    w=csv.DictWriter(s,fieldnames=fields,lineterminator="\n")
    w.writeheader();w.writerows(rows)
    return s.getvalue().encode()

def immutable_publish(out:Path,files:dict[str,bytes])->None:
    out.mkdir(parents=True,exist_ok=True)
    for n,d in files.items():
        p=out/n
        if p.exists() and p.read_bytes()!=d:
            raise GateError(f"existing_output_differs:{n}")
        if not p.exists():p.write_bytes(d)

def near(a,b,rtol=1e-11,atol=1e-8):
    return abs(float(a)-float(b)) <= max(atol,rtol*max(abs(float(b)),1.0))

def self_test():
    # Algebraic feasibility sanity check for the frozen protocol.
    raw=[12.0,2.0,1.0]
    cap=[10.0,5.0,5.0]
    base=[min(r,c) for r,c in zip(raw,cap)]
    supply=sum(max(r-c,0.0) for r,c in zip(raw,cap))
    spare=sum(c-b for c,b in zip(cap,base))
    if abs(supply-2.0)>1e-12 or spare<2.0:
        raise RuntimeError("synthetic_capacity_bookkeeping")
    print("POSTV16-AV1-D-R7-R2 self-test: PASS")

def main(root:Path,drive:Path)->int:
    gates={};stage="preflight"
    out=drive/OUT_REL;blocked=drive/BLOCKED_REL

    def gate(n,p,v=None):
        ok=bool(p);gates[n]={"passed":ok,"value":v}
        print(f"[{'PASS' if ok else 'FAIL'}] {n}"+(f" — {v}" if v is not None else ""))
        if not ok:raise GateError(n)

    print("="*186)
    print("POSTV16-AV1-D-R7-R2 — CONSERVATIVE BOUNDED OVERLAP/OCCUPANCY RECONCILIATION PROTOCOL FREEZE")
    print("="*186)
    print("DESIGN/FREEZE ONLY. NO MODEL INFERENCE. NO MAPBACK REPAIR EXECUTION. NO TRAINING. NO GEOLOGY0031.")
    print("NO SATURATION CLIPPING, NO GLOBAL RESCALING, NO S_MAX RELAXATION, NO B1 OR CHECKPOINT CHANGE.\n")

    try:
        root=root.resolve();drive=drive.resolve()
        parent=git_text(root,"rev-parse","HEAD^")
        status=git_text(root,"status","--porcelain")
        gate("repository_parent_is_R7R1_commit",parent==PARENT_R7R1_COMMIT,parent)
        gate("repository_clean",status=="",repr(status))

        for fn,b in SOURCE_BLOBS.items():
            p=root/fn;a=git_blob_sha(p,root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",a==b,a)

        stage="R7R1_evidence_binding"
        d=drive/R7R1_REL
        gate("R7R1_output_present",d.is_dir(),str(d))
        m=verify_manifest(d,R7R1_MANIFEST)
        gate("R7R1_manifest_SHA_closure",True,len(m))
        s=load_json(d/R7R1_SUMMARY)
        q=load_json(d/R7R1_DIAG)
        audit=read_csv(d/R7R1_AUDIT)

        gate("R7R1_status_exact",s["status"]==R7R1_STATUS,s["status"])
        gate("R7R1_failure_reproduced",s["R7_failure_reproduced"] is True)
        gate("R7R1_repair_not_selected",s["repair_selected"] is False)
        gate("R7R1_overloaded_count_exact",int(s["overloaded_cell_count"])==EXPECTED_OVERLOADED,s["overloaded_cell_count"])
        gate("R7R1_worst_cell_exact",list(s["worst_cell_kji"])==EXPECTED_WORST,s["worst_cell_kji"])
        gate("R7R1_worst_excess_exact",near(s["worst_excess_kg"],EXPECTED_MAX_EXCESS),s["worst_excess_kg"])

        loc=q["local_capacity"]
        gate("R7R1_global_capacity_fraction_exact",near(loc["global_mass_capacity_fraction"],EXPECTED_GLOBAL_CAPACITY_FRACTION),loc["global_mass_capacity_fraction"])
        gate("R7R1_global_mass_not_capacity_failure",q["scientific_interpretation"]["global_mass_capacity_failure"] is False)
        gate("R7R1_local_capacity_failure",q["scientific_interpretation"]["local_grid_occupancy_capacity_failure"] is True)
        gate("R7R1_checkpoint_not_failure",q["scientific_interpretation"]["transport_checkpoint_failure"] is False)
        gate("R7R1_B1_not_failure",q["scientific_interpretation"]["B1_representation_failure"] is False)
        gate("R7R1_old_state_sampling_alone_insufficient",q["old_state_contract"]["sampled_old_CV_state_equals_R7_background_old_state"] is True)
        gate("R7R1_worst_capacity_ratio_exact",near(loc["worst_capacity_ratio"],EXPECTED_WORST_CAPACITY_RATIO,rtol=1e-10),loc["worst_capacity_ratio"])
        gate("R7R1_worst_coverage_ratio_exact",near(loc["worst_coverage_to_cell_PV_ratio"],EXPECTED_WORST_COVERAGE_RATIO,rtol=1e-10),loc["worst_coverage_to_cell_PV_ratio"])
        gate("R7R1_worst_streamline_support_exact",int(loc["worst_unique_streamline_count"])==EXPECTED_WORST_STREAMLINES,loc["worst_unique_streamline_count"])
        gate("R7R1_audit_nonempty",len(audit)>0,len(audit))

        stage="freeze_protocol"

        protocol={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "protocol_id":PROTOCOL_ID,
            "problem_statement":{
                "failure_class":"LOCAL_STREAMLINE_OVERLAP_TO_CARTESIAN_PHYSICAL_CAPACITY_INCOMPATIBILITY",
                "overloaded_cartesian_cells_day30":EXPECTED_OVERLOADED,
                "worst_cell_kji":EXPECTED_WORST,
                "worst_cell_mass_excess_kg":EXPECTED_MAX_EXCESS,
                "worst_cell_capacity_ratio":EXPECTED_WORST_CAPACITY_RATIO,
                "worst_coverage_to_physical_cell_PV_ratio":EXPECTED_WORST_COVERAGE_RATIO,
                "worst_unique_streamline_support_count":EXPECTED_WORST_STREAMLINES,
                "global_grid_capacity_fraction_used":EXPECTED_GLOBAL_CAPACITY_FRACTION,
                "accepted_transport_checkpoint_implicated":False,
                "B1_half_overlap_implicated":False,
                "global_grid_storage_capacity_implicated":False,
            },
            "operator_role":{
                "name":"support-graph minimum-cost excess-mass reconciliation",
                "classification":"representation reconciliation only",
                "is_physical_advection_operator":False,
                "is_capillary_diffusion_operator":False,
                "changes_transport_prediction":False,
                "changes_total_component_mass":False,
                "purpose":(
                    "Resolve non-unique overlapping streamline-tube pore-volume inventory "
                    "onto unique bounded Cartesian cell pore volume before EOS inversion."
                ),
            },
            "inputs":{
                "raw_cartesian_component_mass":"parent_grid_component_mass + exact E37A subsegment deposited component-mass increment",
                "physical_cell_capacity":"cell_pore_volume_m3 * rho_g(S=0.80, pressure, p_ref) * 0.60",
                "support_geometry":"frozen SG7D subsegment operator",
                "support_cells":"cells with SG7D coverage_weight_m3 > 0",
                "grid_pressure":"frozen pressure authority for the current integration fixture",
                "accepted_B1_component_mass":"unchanged upstream authority",
            },
            "support_graph":{
                "nodes":"unique Cartesian cells with nonzero SG7D subsegment support",
                "edge_rule":(
                    "undirected edge between two distinct cells when successive subsegments "
                    "of at least one same streamline occupy those cells"
                ),
                "self_edges":"discarded",
                "duplicate_edges":"collapsed",
                "component_rule":"connected components of this fixed support graph are reconciled independently",
                "unsupported_cells_eligible":False,
                "cross_component_mass_transfer_allowed":False,
            },
            "mass_bookkeeping":{
                "raw_mass_symbol":"m_c",
                "capacity_symbol":"C_c",
                "base_mass":"b_c = min(m_c, C_c)",
                "excess_supply":"e_c = max(m_c - C_c, 0)",
                "spare_capacity":"d_c = C_c - b_c",
                "source_nodes":"e_c > 0",
                "recipient_nodes":"d_c > 0",
                "component_feasibility_gate":"sum(e_c) <= sum(d_c) + tolerance within every support connected component",
                "global_mass_feasibility_gate":"sum(m_c) <= sum(C_c) + tolerance",
            },
            "minimum_cost_flow":{
                "variables":{
                    "directed_edge_flow_kg":"f_uv >= 0 for each direction of every support edge",
                    "absorbed_excess_kg":"a_c with 0 <= a_c <= d_c",
                },
                "node_balance":"sum_out(f_cu) - sum_in(f_uc) + a_c = e_c",
                "primary_edge_cost_units":(
                    "5*abs(delta_i) + 5*abs(delta_j) + abs(delta_k); "
                    "20-ft x/y cells therefore cost 5 units and 4-ft z cells cost 1 unit"
                ),
                "primary_objective":"minimize sum(edge_cost_units * directed_edge_flow_kg)",
                "solver":"scipy.optimize.linprog(method='highs')",
                "fixed_ordering":{
                    "node_order":"ascending flattened Cartesian cell index",
                    "edge_order":"lexicographic (min_flat_cell, max_flat_cell), then direction",
                    "recipient_order":"ascending flattened Cartesian cell index",
                },
                "deterministic_tie_break":(
                    "After solving the primary minimum-distance LP, freeze its optimum within "
                    "tol_obj=max(1e-8,1e-12*max(abs(primary_optimum),1)). "
                    "Solve a second LP over the same feasible set minimizing normalized "
                    "lexicographic edge-flow rank plus normalized recipient-absorption rank. "
                    "Primary cost may not exceed optimum+tol_obj."
                ),
                "final_cell_mass":"m*_c = b_c + a_c",
                "transit_flow_changes_cell_inventory":False,
            },
            "post_reconciliation":{
                "EOS_inversion":"use frozen R2 _invert_incremental_sg_from_mass on m*_c",
                "final_saturation":"S_c = 0.20 + Sg_c",
                "bounds":"0.20 <= S_c <= 0.80",
                "unsupported_cells":"remain exactly at parent/background incremental mass unless changed by the pre-existing parent state; reconciliation adds zero mass there",
                "no_additional_capillary_step_in_R7_repair":True,
            },
            "hard_execution_gates_for_R7R3":{
                "same_accepted_R6_weights_SHA":True,
                "same_R6_normalization_SHA":True,
                "same_B1_201_to_200_projection":True,
                "same_S_min_0p20_S_max_0p80":True,
                "all_9_canonical_times":True,
                "component_feasibility_all_times":True,
                "LP_primary_success_all_times":True,
                "LP_tiebreak_success_all_times":True,
                "max_node_balance_residual_kg":"<= max(1e-7,1e-11*max(total_excess_kg,1))",
                "max_capacity_excess_after_reconciliation_kg":"<= max(1e-7,1e-11*max(max_cell_capacity_kg,1))",
                "total_component_mass_relative_closure":"<= 1e-10",
                "unsupported_cell_added_mass_exact_zero":True,
                "cross_support_component_transfer_exact_zero":True,
                "grid_saturation_finite":True,
                "grid_saturation_bounds":True,
                "accepted_checkpoint_or_B1_modification":False,
            },
            "prohibitions":{
                "cellwise_clipping_and_mass_discard":True,
                "global_saturation_rescaling":True,
                "relax_Smax_above_0p80":True,
                "use_uncovered_cells_as_mass_sink":True,
                "change_B1_half_overlap":True,
                "change_accepted_checkpoint":True,
                "retrain_or_finetune":True,
                "use_geology0031":True,
                "use_acceptance_truth":True,
                "time_specific_tuning":True,
                "day30_specific_parameter":True,
            },
            "scope":{
                "design_based_on_R7R1_day30_failure_evidence":True,
                "operator_itself_time_generic":True,
                "operator_applies_identically_to_all_9_canonical_times":True,
                "new_accuracy_claim":False,
                "new_generalization_claim":False,
                "next_claim_if_R7R3_passes":(
                    "Only end-to-end conservative interface executability with bounded "
                    "support-constrained occupancy reconciliation on Foundation Case 0001."
                ),
            },
            "next":{
                "milestone":"POSTV16-AV1-D-R7-R3",
                "name":"Controlled execution of frozen support-graph overlap/occupancy reconciliation",
                "authorized":True,
                "repair_search_authorized":False,
                "alternate_reconciliation_candidate_authorized":False,
            },
        }

        freeze={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "protocol_id":PROTOCOL_ID,
            "parent_R7R1_commit":PARENT_R7R1_COMMIT,
            "R7R1_runner_blob":R7R1_BLOB,
            "R7_failure_evidence_consumed":True,
            "repair_execution_performed":False,
            "model_inference_performed":False,
            "accepted_checkpoint_modified":False,
            "B1_modified":False,
            "E37A_saturation_bounds_modified":False,
            "geology0031_used":False,
            "acceptance_truth_used":False,
            "candidate_count":1,
            "R7R3_execution_authorized":True,
        }

        summary={
            "milestone":MILESTONE,
            "status":STATUS_PASS,
            "protocol_id":PROTOCOL_ID,
            "diagnostic_overloaded_cells":EXPECTED_OVERLOADED,
            "diagnostic_worst_cell_kji":EXPECTED_WORST,
            "diagnostic_worst_excess_kg":EXPECTED_MAX_EXCESS,
            "global_capacity_fraction":EXPECTED_GLOBAL_CAPACITY_FRACTION,
            "repair_execution_performed":False,
            "model_inference_performed":False,
            "accepted_checkpoint_modified":False,
            "R7R3_authorized":True,
            "next":"POSTV16-AV1-D-R7-R3 — controlled execution of the single frozen support-graph reconciliation operator",
        }

        immutable_publish(out,{
            "PAD_Stream_POSTV16_AV1_D_R7_R2_Summary.json":json_bytes(summary),
            "POSTV16_AV1_D_R7_R2_Frozen_Reconciliation_Protocol.json":json_bytes(protocol),
            "POSTV16_AV1_D_R7_R2_Protocol_Freeze_Contract.json":json_bytes(freeze),
            "POSTV16_AV1_D_R7_R2_Final_Gate_Matrix.csv":csv_bytes([{"gate":k,**v} for k,v in gates.items()]),
        })

        rows=[]
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name!="POSTV16_AV1_D_R7_R2_Artifact_Manifest.csv":
                rows.append({"file":p.name,"sha256":sha256_file(p),"bytes":p.stat().st_size})
        immutable_publish(out,{"POSTV16_AV1_D_R7_R2_Artifact_Manifest.csv":csv_bytes(rows)})

        print("\n"+"="*186)
        print("POSTV16-AV1-D-R7-R2: PASS")
        print("="*186)
        print(f"{'Status':104}: {STATUS_PASS}")
        print(f"{'Frozen protocol':104}: {PROTOCOL_ID}")
        print(f"{'R7-R1 overloaded cells bound':104}: {EXPECTED_OVERLOADED}")
        print(f"{'Worst cell k/j/i bound':104}: {EXPECTED_WORST}")
        print(f"{'Worst excess mass [kg] bound':104}: {EXPECTED_MAX_EXCESS:.12e}")
        print(f"{'Reconciliation domain':104}: SG7D-supported Cartesian-cell graph only")
        print(f"{'Primary objective':104}: minimum graph-distance movement of excess component mass")
        print(f"{'Mass conservation':104}: exact up to frozen numerical tolerance")
        print(f"{'Unsupported cells eligible as sinks':104}: False")
        print(f"{'Saturation bounds changed':104}: False")
        print(f"{'Accepted checkpoint / B1 changed':104}: False / False")
        print(f"{'Repair execution in R7-R2':104}: False")
        print(f"{'R7-R3 controlled single-candidate execution authorized':104}: True")
        print(f"{'NEXT':104}: POSTV16-AV1-D-R7-R3 — execute frozen reconciliation across all 9 canonical times")
        print("="*186)
        return 0

    except Exception as e:
        blocked.mkdir(parents=True,exist_ok=True)
        rep={
            "milestone":MILESTONE,"status":STATUS_BLOCKED,
            "failed_stage":stage,"exception":repr(e),"gates":gates,
            "repair_execution_performed":False,
            "model_inference_performed":False,
            "accepted_checkpoint_modified":False,
            "R7R3_execution_authorized":False,
            "next_action":"Audit only the R7-R2 evidence/protocol freeze. Do not execute an unfreezed reconciliation repair.",
        }
        data=json_bytes(rep)
        p=blocked/"POSTV16_AV1_D_R7_R2_Blocked_Report.json"
        if p.exists() and p.read_bytes()!=data:
            p=blocked/f"POSTV16_AV1_D_R7_R2_Blocked_Report_{hashlib.sha256(data).hexdigest()[:12]}.json"
        if not p.exists():p.write_bytes(data)
        print("\n"+"="*186);print("POSTV16-AV1-D-R7-R2: BLOCKED");print("="*186)
        print("Failed stage:",stage);print("Exception:",repr(e));print("Report:",p)
        return 2

def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--project-root",type=Path,default=Path("."))
    p.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    p.add_argument("--self-test",action="store_true")
    return p.parse_args()

if __name__=="__main__":
    a=parse_args()
    if a.self_test:
        self_test();raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))
