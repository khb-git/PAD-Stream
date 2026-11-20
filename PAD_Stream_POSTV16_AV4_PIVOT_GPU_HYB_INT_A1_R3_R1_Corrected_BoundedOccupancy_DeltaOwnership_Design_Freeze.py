#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, json, subprocess
from pathlib import Path
from typing import Any

M="POSTV16-AV4-PIVOT-GPU-HYB-INT-A1-R3-R1"
PASS="POSTV16AV4PIVOTGPUHYBINTA1R3R1_CORRECTED_BOUNDED_OCCUPANCY_DELTA_OWNERSHIP_DESIGN_FREEZE_PASS_NO_PHYSICS_EXECUTION"
BLOCK="POSTV16AV4PIVOTGPUHYBINTA1R3R1_TECHNICAL_OR_AUTHORITY_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="9a3b21d4337e892c655ebb67f914225cd741077a"

R4R1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R4_R1_CertifiedParent_Replay_Ownership_Validation_and_Day30_Day45_Run.py"
R4R1_BLOB="570c21db62d0b6636c5de895fdb0425ecb701db6"
R3_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R3_ParentOwnership_Mapback_Reconciliation_Design_Freeze.py"
R3_BLOB="cb9aab3b5c9a6310f4337e22c3d4c207e814b66c"
R2R1R1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R2_R1_R1_Corrected_TransientWorstCellSwitching_Localization.py"
R2R1R1_BLOB="543c664ef6e781a22abddda867cbcfc8ae607ed5"
F2R3_RUNNER="PAD_Stream_POSTV16_AV4_F2_R3_Bounded_Physical_Occupancy_Projection_Execution.py"
F2R3_BLOB="359f3c0edf87e10bb4006cacdd271cd426fed22b"
F4EXEC_RUNNER="PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_Ownership_Reconciled_Event_MapBack_and_Flow_Refresh_Execution.py"
F4EXEC_BLOB="b2c129bd067ef75163c3f06de5c15adc53ae5633"
E37A_RUNNER="PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB="0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

R4R1_BLOCK_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R4_R1_BLOCKED"
R4R1_BLOCK_REPORT="POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R4_R1_Blocked_Report.json"
R4R1_BLOCK_STATUS="POSTV16AV4PIVOTGPUHYBINTA1R4R1_TECHNICAL_CONSERVATION_OWNERSHIP_CAPACITY_OR_AUTHORITY_BLOCK"
R4R1_EXCEPTION_PREFIX="GateError('parent_ownership_stageA_infeasible:2:"

R3_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R3_ParentOwnership_Mapback_Reconciliation_Design_Freeze"
R3_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R3_Summary.json"
R3_STATUS="POSTV16AV4PIVOTGPUHYBINTA1R3_PARENT_OWNERSHIP_MAPBACK_RECONCILIATION_DESIGN_FREEZE_PASS_NO_PHYSICS_EXECUTION"

R2R1R1_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R2_R1_R1_Corrected_TransientWorstCellSwitching_Localization"
R2R1R1_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R2_R1_R1_Summary.json"
R2R1R1_STATUS="POSTV16AV4PIVOTGPUHYBINTA1R2R1R1_CORRECTED_TRANSIENT_WORST_CELL_SWITCHING_LOCALIZATION_PASS"

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R3_R1"
OUT_REL=BASE/(OUT_TOKEN+"_Corrected_BoundedOccupancy_DeltaOwnership_Design_Freeze")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
PROTOCOL=f"{OUT_TOKEN}_Corrected_Reconciliation_Protocol.json"
HANDOFF=f"{OUT_TOKEN}_R4_R2_Execution_Handoff_Contract.json"
DECISION=f"{OUT_TOKEN}_Decision_Contract.json"
GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"

class GateError(RuntimeError): pass

def gt(root:Path,*a:str)->str:
    return subprocess.check_output(["git","-C",str(root),*a],text=True).strip()

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""): h.update(c)
    return h.hexdigest()

def js(p:Path): return json.loads(p.read_text(encoding="utf-8"))

def write_csv(p:Path,rows):
    rows=list(rows)
    if not rows:
        p.write_text("",encoding="utf-8");return
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows)

def exact_blob(root:Path,fn:str,expected:str)->str:
    p=root/fn
    if not p.is_file(): raise GateError(f"missing_source:{fn}")
    actual=gt(root,"hash-object",str(p))
    if actual!=expected: raise GateError(f"source_blob:{fn}:{actual}:{expected}")
    return actual

def selftest(root:Path):
    for fn,b in [
        (R4R1_RUNNER,R4R1_BLOB),(R3_RUNNER,R3_BLOB),(R2R1R1_RUNNER,R2R1R1_BLOB),
        (F2R3_RUNNER,F2R3_BLOB),(F4EXEC_RUNNER,F4EXEC_BLOB),(E37A_RUNNER,E37A_BLOB),
    ]:
        assert exact_blob(root,fn,b)==b
    print("POSTV16 GPU-HYB-INT-A1-R3-R1 corrected delta-ownership design-freeze self-test: PASS")

def main(root:Path,drive:Path)->int:
    root=root.resolve();drive=drive.resolve();out=drive/OUT_REL;blocked=drive/BLOCK_REL
    gates=[];stage="preflight"
    def gate(n,c,d=None):
        ok=bool(c);gates.append({"stage":stage,"gate":n,"pass":ok,"detail":"" if d is None else repr(d)})
        print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"),flush=True)
        if not ok: raise GateError(n)

    try:
        print("="*196)
        print("INT-A1-R3-R1 — CORRECTED BOUNDED-OCCUPANCY DELTA-OWNERSHIP DESIGN FREEZE")
        print("CPU-ONLY. NO PHYSICS. NO HYBRID INFERENCE. NO LP EXECUTION. NO STATE MUTATION.")
        print("="*196)

        stage="repository"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_R4_R1_BLOCK_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")

        stage="source_authority"
        for label,fn,b in [
            ("R4_R1",R4R1_RUNNER,R4R1_BLOB),("R3",R3_RUNNER,R3_BLOB),
            ("R2_R1_R1",R2R1R1_RUNNER,R2R1R1_BLOB),("F2_R3",F2R3_RUNNER,F2R3_BLOB),
            ("F4_OWNERSHIP_EXEC",F4EXEC_RUNNER,F4EXEC_BLOB),("E37A",E37A_RUNNER,E37A_BLOB),
        ]:
            gate(label+"_blob_exact",exact_blob(root,fn,b)==b)

        stage="R4_R1_BLOCK_authority"
        bp=drive/R4R1_BLOCK_REL/R4R1_BLOCK_REPORT
        gate("R4_R1_BLOCK_report_present",bp.is_file(),str(bp))
        b=js(bp)
        gate("R4_R1_BLOCK_status_exact",b.get("status")==R4R1_BLOCK_STATUS,b.get("status"))
        gate("R4_R1_BLOCK_stage_exact",b.get("failed_stage")=="controlled_integrated_rollout",b.get("failed_stage"))
        gate("R4_R1_STAGEA_infeasibility_exact",
             str(b.get("exception","")).startswith(R4R1_EXCEPTION_PREFIX),b.get("exception"))
        gate("R4_R1_no_clipping",b.get("cell_mass_clipping_performed") is False)
        gate("R4_R1_no_mass_discard",b.get("mass_discard_performed") is False)
        gate("R4_R1_no_tolerance_relaxation",b.get("scientific_tolerance_relaxed") is False)
        gate("R4_R1_visualization_closed",b.get("INT_VIS_A1_integrated_3D_visualization_authorized") is False)

        stage="prior_science_authority"
        r3p=drive/R3_REL/R3_SUM
        r2p=drive/R2R1R1_REL/R2R1R1_SUM
        gate("R3_summary_present",r3p.is_file(),str(r3p))
        gate("R2_R1_R1_summary_present",r2p.is_file(),str(r2p))
        r3=js(r3p);r2=js(r2p)
        gate("R3_status_exact",r3.get("status")==R3_STATUS,r3.get("status"))
        gate("R2_R1_R1_status_exact",r2.get("status")==R2R1R1_STATUS,r2.get("status"))
        gate("dt_only_repair_closed",r2.get("timestep_only_repair_rejected") is True)
        gate("ownership_mechanism_still_bound",
             float(r2.get("worst_cell_parent_raw_subsegment_ownership_excess_kg"))>0.0,
             r2.get("worst_cell_parent_raw_subsegment_ownership_excess_kg"))

        stage="corrected_design_freeze"
        protocol={
            "milestone":M,
            "status":PASS,
            "classification":"R3_ABSOLUTE_OVERLAPPING_CV_OWNERSHIP_CONSTRAINT_SUPERSEDED_BY_F2R3_BOUNDED_OCCUPANCY_PARENT_SPLIT_PLUS_EXACT_E37A_CV_TRANSPORT_DELTA_RECONCILIATION",
            "R4_R1_stageA_infeasibility_interpretation":{
                "scientific_meaning":"ordinary E37A parent CV masses are overlapping restart-sampling inventories, not exclusive Cartesian ownership variables",
                "invalid_constraint_closed":"sum_c P_jc = raw sampled M0_transport_j while simultaneously requiring sum_j P_jc <= Cartesian G0_c",
                "solver_failure_is_not_support_expansion_authority":True,
                "solver_failure_is_not_tolerance_relaxation_authority":True,
            },
            "state_semantics":{
                "G0_c":"authoritative Cartesian parent CO2 mass",
                "M0T_j":"ordinary E37A sampled parent transport CV mass; overlapping representation; retained for transport evolution only",
                "M1T_j":"accepted mixed Hybrid/exact child transport CV mass",
                "DeltaM_j":"M1T_j - M0T_j; exact per-CV transport increment and the quantity that mapback must preserve",
                "P0_q":"bounded parent Cartesian ownership on E37A subsegment q",
                "O0_j":"bounded ownership CV mass = sum_q_in_j P0_q; distinct from M0T_j",
                "R_c":"residual Cartesian sidecar = G0_c - bounded mapped ownership",
                "O1_j":"child ownership target = O0_j + DeltaM_j",
            },
            "stage_A_bounded_parent_occupancy_split":{
                "source_precedent":"POSTV16-AV4-F2-R3 bounded physical occupancy projection",
                "existing_E37A_subsegment_support_only":True,
                "W_c":"sum of E37A subsegment pore volumes crossing Cartesian cell c",
                "D_c":"max(physical Cartesian cell pore volume V_c, W_c)",
                "P0_q":"G0_c * PV_q / D_c for subsegment q in cell c",
                "mapped_parent_cell":"sum_q_in_c P0_q = G0_c * min(1, W_c/V_c)",
                "residual_sidecar":"R_c = G0_c - mapped_parent_cell >= 0",
                "ownership_CV_mass":"O0_j = sum_q_in_j P0_q",
                "hard_gates":[
                    "P0_q finite and nonnegative",
                    "mapped_parent_cell <= G0_c cellwise",
                    "R_c >= 0 cellwise",
                    "sum_c R_c + sum_j O0_j = sum_c G0_c",
                ],
                "no_LP_required":True,
            },
            "stage_B_exact_transport_delta_reconciliation":{
                "transport_increment":"DeltaM_j = M1T_j - M0T_j",
                "ownership_child_target":"O1_j = O0_j + DeltaM_j",
                "hard_precondition":"O1_j >= 0 for every CV; otherwise scientific FAIL because exact transport withdrawal exceeds bounded parent ownership",
                "variables":"X_jc >= 0 on existing E37A CV-cell support only",
                "hard_constraints":[
                    "sum_c X_jc = O1_j for every CV j",
                    "R_c + sum_j X_jc <= physical Cartesian capacity C_c",
                    "X_jc = 0 outside existing E37A support",
                    "no cross-CV delta exchange",
                ],
                "primary_target":"parent-continuity target derived from bounded P0 ownership scaled to O1_j",
                "secondary_target":"raw child EOS/subsegment distribution Q1_jc, diagnostic target only",
                "deterministic_tiebreak":"fixed lexicographic CV-cell pair ordering",
            },
            "mandatory_identities":{
                "zero_transport_delta_identity":"DeltaM_j=0 -> X_jc=P0_jc and G1_c=G0_c",
                "per_CV_delta_identity":"sum_c(X_jc-P0_jc)=DeltaM_j exactly",
                "global_delta_identity":"sum_c(G1_c-G0_c)=sum_j DeltaM_j",
                "grid_reconstruction":"G1_c=R_c+sum_j X_jc",
                "nonnegative_grid":"G1_c>=0",
                "capacity_bound":"G1_c<=C_c",
                "residual_sidecar_immutable":True,
            },
            "superseded_R3_terms":[
                "raw sampled transport M0T_j is NOT required to equal bounded ownership O0_j",
                "raw sampled transport M1T_j is NOT required to equal child ownership O1_j",
                "what is preserved exactly is DeltaM_j = M1T_j-M0T_j",
            ],
            "prohibitions":[
                "cellwise clipping","mass discard","global plume rescaling",
                "scientific tolerance relaxation","support expansion",
                "cross-CV transport-delta exchange","changing accepted DeltaM_j",
                "extra flow refresh caused solely by mapback reconciliation",
            ],
            "controller_contract":{
                "flow_refresh_schedule_days":[30.0,35.0,40.0,45.0],
                "unchanged":True,
            },
            "R4_R2_execution_protocol":{
                "phase_1":"replay R1 path to certified Day30.003412917596155 parent",
                "phase_2":"construct F2R3-style bounded parent occupancy split dynamically on current E37A geometry",
                "phase_3":"verify O1_j=O0_j+DeltaM_j nonnegative and execute exact delta-preserving ownership LP",
                "phase_4":"prove zero-delta, per-CV delta, global delta, nonnegative, capacity, support, and residual-sidecar gates",
                "phase_5":"if and only if local validation passes, continue controlled Day30->45 trajectory in same run",
                "ordinary_E37A_first_path":True,
            },
        }

        summary={
            "milestone":M,"status":PASS,"classification":protocol["classification"],
            "R4_R1_BLOCK_bound":True,
            "R4_R1_stageA_absolute_ownership_formulation_closed":True,
            "R3_repair_family_retained":True,
            "R3_absolute_CV_ownership_constraint_superseded":True,
            "bounded_parent_occupancy_split_source":"F2_R3",
            "transport_authority_preserved_as_exact_per_CV_delta":True,
            "raw_sampled_parent_transport_CV_mass_is_exclusive_ownership":False,
            "raw_sampled_child_transport_CV_mass_is_exclusive_ownership":False,
            "existing_E37A_support_only":True,
            "residual_sidecar_preserved":True,
            "zero_delta_identity_required":True,
            "cellwise_clipping_authorized":False,
            "mass_discard_authorized":False,
            "global_rescaling_authorized":False,
            "scientific_tolerance_relaxation_authorized":False,
            "support_expansion_authorized":False,
            "R3_R1_physics_executed":False,
            "R3_R1_LP_executed":False,
            "R3_R1_Hybrid_inference_executed":False,
            "CPU_only_design_freeze":True,
            "INT_A1_R4_R2_execution_authorized":True,
            "INT_A1_R4_R2_local_validation_required_before_trajectory":True,
            "INT_VIS_A1_integrated_3D_visualization_authorized":False,
            "longer_horizon_validation_authorized":False,
            "production_pressure_refresh_cadence_selected":False,
            "P4_authorized":False,
        }

        decision={
            "milestone":M,"status":PASS,
            "corrected_reconciliation_design_frozen":True,
            "supersedes":"INT-A1-R3 Stage-A absolute sampled-CV ownership equality only",
            "does_not_supersede":"R2-R1-R1 ownership/disaggregation diagnosis, R3 existing-support/no-clipping/no-tolerance/no-support-expansion principles, 5-day controller",
            "next_milestone":{
                "name":"POSTV16-AV4-PIVOT-GPU-HYB-INT-A1-R4-R2",
                "purpose":"Execute F2R3-style bounded parent occupancy + exact per-CV transport-delta reconciliation at the certified failed parent; on local PASS continue Day30->45 in the same run.",
                "authorized":True,
            },
            "runtime_recommendation":"L4/T4 for formal R4-R2; A100 not required",
            "P4_authorized":False,
        }

        handoff={
            "milestone":M,"status":PASS,
            "R4_R2_authorized":True,
            "local_validation_before_trajectory_required":True,
            "flow_refresh_schedule_days":[30.0,35.0,40.0,45.0],
            "visualization_on_R4_R2_PASS":"INT-VIS-A1 immediately authorized",
            "production_activation_authorized":False,
            "P4_authorized":False,
        }

        stage="scope_guards"
        gate("no_physics_execution",summary["R3_R1_physics_executed"] is False)
        gate("no_LP_execution",summary["R3_R1_LP_executed"] is False)
        gate("no_Hybrid_inference",summary["R3_R1_Hybrid_inference_executed"] is False)
        gate("delta_not_absolute_transport_mass_is_mapback_authority",
             summary["transport_authority_preserved_as_exact_per_CV_delta"] is True)
        gate("existing_support_only",summary["existing_E37A_support_only"] is True)
        gate("no_tolerance_relaxation",summary["scientific_tolerance_relaxation_authorized"] is False)
        gate("no_support_expansion",summary["support_expansion_authorized"] is False)
        gate("R4_R2_authorized",summary["INT_A1_R4_R2_execution_authorized"] is True)
        gate("visualization_still_closed",summary["INT_VIS_A1_integrated_3D_visualization_authorized"] is False)
        gate("P4_closed",summary["P4_authorized"] is False)

        stage="publication"
        gate("output_absent",not out.exists(),str(out))
        out.mkdir(parents=True)
        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        (out/PROTOCOL).write_text(json.dumps(protocol,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        (out/HANDOFF).write_text(json.dumps(handoff,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        (out/DECISION).write_text(json.dumps(decision,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        write_csv(out/GATES,gates)
        write_csv(out/MANIFEST,[{"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size}
                                for p in sorted(out.iterdir()) if p.is_file() and p.name!=MANIFEST])

        print("="*196)
        print(M,"PASS")
        print("R4-R1 Stage-A infeasibility     : CLASSIFIED")
        print("Raw E37A M0/M1 absolute ownership: SUPERSEDED")
        print("Bounded parent split             : F2-R3 OCCUPANCY FORMULA")
        print("Transport authority              : EXACT per-CV DeltaM")
        print("Support                          : EXISTING E37A ONLY")
        print("R4-R2                            : AUTHORIZED")
        print("Recommended runtime              : L4/T4; A100 NOT REQUIRED")
        print("="*196)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps({
            "milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),"gates":gates,
            "INT_A1_R4_R2_execution_authorized":False,
            "INT_VIS_A1_integrated_3D_visualization_authorized":False,
            "P4_authorized":False,
        },indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(M,"BLOCK");print("Stage:",stage);print("Exception:",repr(exc));return 2

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",type=Path,default=Path("."))
    ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test:selftest(a.project_root.resolve());raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))
