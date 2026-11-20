#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

M="POSTV16-AV4-PIVOT-GPU-HYB-INT-A1-R3"
PASS="POSTV16AV4PIVOTGPUHYBINTA1R3_PARENT_OWNERSHIP_MAPBACK_RECONCILIATION_DESIGN_FREEZE_PASS_NO_PHYSICS_EXECUTION"
BLOCK="POSTV16AV4PIVOTGPUHYBINTA1R3_TECHNICAL_OR_AUTHORITY_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="c25f2e575e1477f3246be768afa8b471501d9a1b"

R2R1R1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R2_R1_R1_Corrected_TransientWorstCellSwitching_Localization.py"
R2R1R1_BLOB="543c664ef6e781a22abddda867cbcfc8ae607ed5"
INTA1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_Controlled_Integrated_Day30_Day45_WholeSystem_Run.py"
INTA1_BLOB="4b78313ab08827f3dcc0f63ee5f603df6390b2c1"
G3R7_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R7_Controlled_Integrated_Controller_Shadow_Execution_Protocol_Freeze.py"
G3R7_BLOB="2204b827987a2027cc9e6bda8b27582d4b713d60"
E37A_RUNNER="PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB="0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
A3R1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_A3_R1_MixedRoute_CVDelta_Ledger_Repair.py"
A3R1_BLOB="dc0b10d72991786752a0522f2e58f640d90b420d"
F4FREEZE_RUNNER="PAD_Stream_POSTV16_AV4_F4_R3_R3_R2_Bounded_Parent_Ownership_Event_MapBack_Reconciliation_Freeze.py"
F4FREEZE_BLOB="247e1e5b6d3fc83bd81d3dd84f0bbeb88c5280c0"
F4EXEC_RUNNER="PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_Ownership_Reconciled_Event_MapBack_and_Flow_Refresh_Execution.py"
F4EXEC_BLOB="b2c129bd067ef75163c3f06de5c15adc53ae5633"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

R2R1R1_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R2_R1_R1_Corrected_TransientWorstCellSwitching_Localization"
R2R1R1_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R2_R1_R1_Summary.json"
R2R1R1_DEC="POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R2_R1_R1_Decision_Contract.json"
R2R1R1_STATUS="POSTV16AV4PIVOTGPUHYBINTA1R2R1R1_CORRECTED_TRANSIENT_WORST_CELL_SWITCHING_LOCALIZATION_PASS"

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R3"
OUT_REL=BASE/(OUT_TOKEN+"_ParentOwnership_Mapback_Reconciliation_Design_Freeze")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
PROTOCOL=f"{OUT_TOKEN}_Frozen_Reconciliation_Protocol.json"
HANDOFF=f"{OUT_TOKEN}_R4_Execution_Handoff_Contract.json"
DECISION=f"{OUT_TOKEN}_Decision_Contract.json"
GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"

class GateError(RuntimeError): pass

def gt(root:Path,*args:str)->str:
    return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""):
            h.update(c)
    return h.hexdigest()

def js(p:Path):
    return json.loads(p.read_text(encoding="utf-8"))

def write_csv(p:Path,rows:list[dict[str,Any]]):
    rows=list(rows)
    if not rows:
        p.write_text("",encoding="utf-8");return
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n")
        w.writeheader();w.writerows(rows)

def exact_blob(root:Path,fn:str,expected:str)->str:
    p=root/fn
    if not p.is_file(): raise GateError(f"missing_source:{fn}")
    actual=gt(root,"hash-object",str(p))
    if actual!=expected: raise GateError(f"source_blob:{fn}:{actual}:{expected}")
    return actual

def selftest(root:Path):
    pairs=[
        (R2R1R1_RUNNER,R2R1R1_BLOB),
        (INTA1_RUNNER,INTA1_BLOB),
        (G3R7_RUNNER,G3R7_BLOB),
        (E37A_RUNNER,E37A_BLOB),
        (A3R1_RUNNER,A3R1_BLOB),
        (F4FREEZE_RUNNER,F4FREEZE_BLOB),
        (F4EXEC_RUNNER,F4EXEC_BLOB),
    ]
    for fn,b in pairs:
        assert exact_blob(root,fn,b)==b
    print("POSTV16 GPU-HYB-INT-A1-R3 parent-ownership design-freeze self-test: PASS")

def main(root:Path,drive:Path)->int:
    root=root.resolve();drive=drive.resolve()
    out=drive/OUT_REL;blocked=drive/BLOCK_REL
    gates=[];stage="preflight"

    def gate(name,cond,detail=None):
        ok=bool(cond)
        gates.append({"stage":stage,"gate":name,"pass":ok,"detail":"" if detail is None else repr(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}"+("" if detail is None else f" -- {detail}"),flush=True)
        if not ok: raise GateError(name)

    try:
        print("="*196)
        print("INT-A1-R3 — PARENT-OWNERSHIP MAPBACK RECONCILIATION DESIGN FREEZE")
        print("CPU-ONLY DESIGN/FREEZE. NO PHYSICS. NO HYBRID INFERENCE. NO LP EXECUTION. NO ACCEPTED-STATE MUTATION.")
        print("="*196)

        stage="repository"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_R2_R1_R1_PASS_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")

        stage="source_authority"
        for label,fn,b in [
            ("R2_R1_R1",R2R1R1_RUNNER,R2R1R1_BLOB),
            ("INT_A1",INTA1_RUNNER,INTA1_BLOB),
            ("G3_R7",G3R7_RUNNER,G3R7_BLOB),
            ("E37A",E37A_RUNNER,E37A_BLOB),
            ("G4_A3_R1",A3R1_RUNNER,A3R1_BLOB),
            ("F4_OWNERSHIP_FREEZE_PRECEDENT",F4FREEZE_RUNNER,F4FREEZE_BLOB),
            ("F4_OWNERSHIP_EXEC_PRECEDENT",F4EXEC_RUNNER,F4EXEC_BLOB),
        ]:
            gate(label+"_blob_exact",exact_blob(root,fn,b)==b)

        stage="R2_R1_R1_authority"
        sp=drive/R2R1R1_REL/R2R1R1_SUM
        dp=drive/R2R1R1_REL/R2R1R1_DEC
        gate("R2_R1_R1_summary_present",sp.is_file(),str(sp))
        gate("R2_R1_R1_decision_present",dp.is_file(),str(dp))
        s=js(sp);d=js(dp)
        gate("R2_R1_R1_status_exact",s.get("status")==R2R1R1_STATUS,s.get("status"))
        gate("R3_design_freeze_authorized",
             s.get("INT_A1_R3_parent_ownership_mapback_reconciliation_design_freeze_authorized") is True)
        gate("R3_execution_not_authorized",
             s.get("INT_A1_R3_execution_authorized") is False)
        gate("exact_fallback_admissible_all_failed_retries",
             s.get("exact_fallback_mapback_admissible_for_all_failed_parent_retries") is True)
        gate("mixed_rejected_all_failed_retries",
             s.get("mixed_mapback_rejected_for_all_failed_parent_retries") is True)
        gate("dt_refinement_4096_exact",float(s.get("dt_refinement_factor"))==4096.0,s.get("dt_refinement_factor"))
        gate("timestep_only_repair_rejected",s.get("timestep_only_repair_rejected") is True)
        gate("terminal_refinement_factor_256",
             float(s.get("terminal_worst_cell_refinement_factor"))==256.0,
             s.get("terminal_worst_cell_refinement_factor"))
        gate("terminal_worst_cell_run_9",
             int(s.get("terminal_worst_cell_run_length"))==9,
             s.get("terminal_worst_cell_run_length"))
        gate("terminal_ownership_excess_positive",
             float(s.get("worst_cell_parent_raw_subsegment_ownership_excess_kg"))>0.0,
             s.get("worst_cell_parent_raw_subsegment_ownership_excess_kg"))
        gate("Hybrid_minus_exact_delta_negative",
             float(s.get("worst_cell_Hybrid_minus_exact_delta_kg"))<0.0,
             s.get("worst_cell_Hybrid_minus_exact_delta_kg"))
        gate("no_clipping_authority",s.get("cell_mass_clipping_authorized") is False)
        gate("no_mass_discard_authority",s.get("mass_discard_authorized") is False)
        gate("no_tolerance_relaxation_authority",s.get("tolerance_relaxation_authorized") is False)
        gate("no_support_expansion_authority",s.get("support_expansion_authorized") is False)
        gate("decision_repair_family_exact",
             d.get("repair_family_selected")=="BOUNDED_PARENT_OWNERSHIP_PRESERVING_MIXED_CV_TO_CARTESIAN_RECONCILIATION",
             d.get("repair_family_selected"))

        stage="repair_design_freeze"

        protocol={
            "milestone":M,
            "status":PASS,
            "classification":"MIXED_ROUTE_PARENT_OWNERSHIP_PRESERVING_CV_TO_CARTESIAN_RECONCILIATION_FROZEN_EXISTING_E37A_SUPPORT_ONLY_R4_LOCAL_VALIDATION_THEN_CONTROLLED_TRAJECTORY_AUTHORIZED",
            "problem_statement":{
                "accepted_transport_CV_state_is_conservative":True,
                "raw_E37A_signed_subsegment_delta_mapback_can_be_locally_inadmissible_for_mixed_Hybrid_state":True,
                "root_mechanism":"raw old subsegment EOS inventory may exceed actual Cartesian parent ownership in a supported cell; subtracting that raw inventory can create negative Cartesian mass even as dt -> 0",
                "timestep_only_repair_closed":True,
            },
            "authoritative_inputs":{
                "G0_c":"authoritative parent Cartesian CO2 component mass per cell",
                "M0_j":"authoritative parent E37A CV component mass per CV",
                "M1_j":"accepted mixed Hybrid/exact child CV component mass per CV; immutable through mapback reconciliation",
                "E_jc":"existing E37A CV-to-Cartesian incidence support only; pair exists iff a frozen E37A subsegment of CV j intersects cell c",
                "Q0_jc":"raw old EOS/subsegment aggregate mass on pair (j,c); diagnostic/secondary target only",
                "Q1_jc":"raw child EOS/subsegment aggregate mass on pair (j,c); diagnostic/secondary target only",
                "C_c":"physical Cartesian CO2 component-mass capacity under current pressure and frozen saturation ceiling",
            },
            "stage_A_parent_ownership_reconstruction":{
                "variables":"P_jc >= 0 on existing E_jc only",
                "hard_constraints":[
                    "sum_c P_jc = M0_j for every CV j",
                    "sum_j P_jc <= G0_c for every Cartesian cell c",
                    "P_jc = 0 outside existing E_jc support",
                ],
                "residual_sidecar":"R_c = G0_c - sum_j P_jc; require R_c >= 0",
                "objective_primary":"minimize L1(P_jc - Q0_jc), establishing the closest bounded parent ownership to the raw old-EOS/subsegment representation",
                "objective_tiebreak":"deterministic lexicographic pair-order tie break after the primary optimum is frozen",
                "required_identity":"sum_c R_c + sum_j M0_j = sum_c G0_c",
            },
            "stage_B_child_ownership_reconciliation":{
                "variables":"X_jc >= 0 on the SAME existing E_jc support",
                "hard_constraints":[
                    "sum_c X_jc = M1_j for every CV j; transported CV mass identity is exact",
                    "R_c + sum_j X_jc <= C_c for every Cartesian cell c",
                    "X_jc = 0 outside existing E_jc support",
                    "no cross-CV mass exchange",
                ],
                "continuity_target":{
                    "M0_j_positive":"T_jc = P_jc * M1_j / M0_j",
                    "M0_j_zero_M1_j_positive":"normalize Q1_jc over that CV's existing support only; if no supported positive target exists, scientific FAIL",
                },
                "objective_stage1":"minimize L1(X_jc - T_jc)",
                "objective_stage2":"freeze stage1 optimum and minimize L1(X_jc - Q1_jc)",
                "objective_stage3":"freeze stages1/2 and minimize deterministic normalized lexicographic pair-rank * X_jc",
                "grid_reconstruction":"G1_c = R_c + sum_j X_jc",
            },
            "mandatory_identity_and_physics_gates":{
                "zero_transport_delta_identity":"when M1_j = M0_j for all j, require X_jc = P_jc and G1_c = G0_c to numerical roundoff",
                "per_CV_mass_identity":"sum_c X_jc = M1_j for every CV",
                "global_mass_identity":"sum_c G1_c = sum_c R_c + sum_j M1_j",
                "nonnegative_cells":"G1_c >= 0 for every cell",
                "capacity_bound":"G1_c <= C_c for every cell",
                "outside_support_added_mass":"exact zero",
                "residual_sidecar":"R_c unchanged during mapback",
            },
            "solver_freeze":{
                "method":"scipy.optimize.linprog(method='highs')",
                "scientific_tolerance_change":False,
                "solver_feasibility_residuals":"must be audited against existing frozen numerical closure/roundoff semantics; solver tolerances do not create new scientific acceptance authority",
                "determinism":"fixed lexicographic CV-cell pair ordering",
            },
            "prohibitions":[
                "cellwise clipping",
                "mass discard",
                "global plume rescaling",
                "scientific tolerance relaxation",
                "support expansion",
                "cross-CV mass exchange",
                "transport-state modification to make mapback feasible",
                "extra pressure/flow refresh caused solely by this mapback repair",
            ],
            "controller_contract":{
                "flow_refresh_schedule_days":[30.0,35.0,40.0,45.0],
                "unchanged":True,
                "production_cadence_selected":False,
            },
            "R4_execution_protocol":{
                "phase_1_local_validation":{
                    "parent":"the certified failed parent reproduced at Day 30.003412917596155",
                    "actions":[
                        "reproduce mixed rejected trial and exact-fallback admissible control",
                        "construct Stage-A bounded parent ownership",
                        "execute Stage-B child ownership reconciliation on accepted mixed CV mass",
                        "prove zero-delta identity on the same parent",
                        "prove all per-CV, global, nonnegative, capacity, residual-sidecar, and support gates",
                    ],
                    "on_any_failure":"SCIENTIFIC FAIL; do not continue trajectory",
                },
                "phase_2_controlled_trajectory":{
                    "authorized_only_after_phase_1_pass":True,
                    "window_days":[30.0,45.0],
                    "flow_refresh_boundaries":[35.0,40.0,45.0],
                    "mapback_policy":"use frozen ownership reconciliation only when the ordinary frozen E37A mixed mapback rejects for aligned_mapback_negative_cell_mass; ordinary E37A mapback remains first path",
                    "capacity_rejection":"remains separate; this repair does not override upper-capacity safety",
                    "visualization_checkpoints":[30.0,35.0,40.0,45.0],
                },
            },
        }

        handoff={
            "milestone":M,
            "status":PASS,
            "next_milestone":{
                "name":"POSTV16-AV4-PIVOT-GPU-HYB-INT-A1-R4",
                "purpose":"Execute the frozen parent-ownership reconciliation first at the localized failed parent; only after all local gates pass, continue the controlled Day30->45 whole-system trajectory in the same run.",
                "authorized":True,
            },
            "runtime_recommendation":{
                "development_and_local_validation":"CPU runtime; no A100 required",
                "whole_system_phase_after_local_pass":"L4/T4 acceptable for short verification; A100 not required for this Day30->45 repair validation",
            },
            "canonical_state_mutation_authorized":False,
            "production_activation_authorized":False,
            "P4_authorized":False,
        }

        decision={
            "milestone":M,
            "status":PASS,
            "parent_ownership_reconciliation_design_frozen":True,
            "R3_physics_executed":False,
            "R3_LP_executed":False,
            "R3_Hybrid_inference_executed":False,
            "R3_canonical_state_mutated":False,
            "existing_E37A_support_only":True,
            "accepted_mixed_CV_mass_may_be_changed_by_reconciliation":False,
            "residual_sidecar_may_be_changed_by_reconciliation":False,
            "scientific_tolerance_relaxed":False,
            "support_expansion_authorized":False,
            "flow_refresh_schedule_changed":False,
            "INT_A1_R4_execution_authorized":True,
            "INT_A1_R4_must_local_validate_before_trajectory":True,
            "INT_VIS_A1_integrated_3D_visualization_authorized":False,
            "longer_horizon_validation_authorized":False,
            "production_pressure_refresh_cadence_selected":False,
            "integrated_GPU_runtime_production_authorized":False,
            "P4_authorized":False,
        }

        summary={
            "milestone":M,
            "status":PASS,
            "classification":protocol["classification"],
            "R2_R1_R1_PASS_bound":True,
            "terminal_worst_cell_kji":s.get("worst_cell_kji"),
            "terminal_worst_cell_run_length":s.get("terminal_worst_cell_run_length"),
            "terminal_worst_cell_refinement_factor":s.get("terminal_worst_cell_refinement_factor"),
            "terminal_parent_raw_subsegment_ownership_excess_kg":s.get("worst_cell_parent_raw_subsegment_ownership_excess_kg"),
            "terminal_Hybrid_minus_exact_delta_kg":s.get("worst_cell_Hybrid_minus_exact_delta_kg"),
            "timestep_only_repair_closed":True,
            "repair_family":"BOUNDED_PARENT_OWNERSHIP_PRESERVING_MIXED_CV_TO_CARTESIAN_RECONCILIATION",
            "existing_E37A_support_only":True,
            "per_CV_child_mass_preserved_exactly":True,
            "parent_residual_sidecar_preserved":True,
            "zero_delta_identity_required":True,
            "cellwise_clipping_authorized":False,
            "mass_discard_authorized":False,
            "global_rescaling_authorized":False,
            "scientific_tolerance_relaxation_authorized":False,
            "support_expansion_authorized":False,
            "flow_refresh_schedule_days":[30.0,35.0,40.0,45.0],
            "R3_physics_executed":False,
            "R3_LP_executed":False,
            "R3_Hybrid_inference_executed":False,
            "CPU_only_design_freeze":True,
            "INT_A1_R4_execution_authorized":True,
            "INT_A1_R4_local_validation_required_before_trajectory":True,
            "INT_VIS_A1_integrated_3D_visualization_authorized":False,
            "longer_horizon_validation_authorized":False,
            "production_pressure_refresh_cadence_selected":False,
            "P4_authorized":False,
        }

        stage="scope_guards"
        gate("no_physics_execution",summary["R3_physics_executed"] is False)
        gate("no_LP_execution",summary["R3_LP_executed"] is False)
        gate("no_Hybrid_inference",summary["R3_Hybrid_inference_executed"] is False)
        gate("existing_support_only",summary["existing_E37A_support_only"] is True)
        gate("CV_mass_identity_frozen",summary["per_CV_child_mass_preserved_exactly"] is True)
        gate("residual_sidecar_frozen",summary["parent_residual_sidecar_preserved"] is True)
        gate("no_tolerance_relaxation",summary["scientific_tolerance_relaxation_authorized"] is False)
        gate("no_support_expansion",summary["support_expansion_authorized"] is False)
        gate("R4_authorized",summary["INT_A1_R4_execution_authorized"] is True)
        gate("R4_local_validation_required",summary["INT_A1_R4_local_validation_required_before_trajectory"] is True)
        gate("visualization_still_closed",summary["INT_VIS_A1_integrated_3D_visualization_authorized"] is False)
        gate("P4_closed",summary["P4_authorized"] is False)

        stage="publication"
        gate("output_absent",not out.exists(),str(out))
        out.mkdir(parents=True)
        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        (out/PROTOCOL).write_text(json.dumps(protocol,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        (out/HANDOFF).write_text(json.dumps(handoff,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        (out/DECISION).write_text(json.dumps(decision,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        write_csv(out/GATES,gates)
        write_csv(out/MANIFEST,[{"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size}
                                for p in sorted(out.iterdir()) if p.is_file() and p.name!=MANIFEST])

        print("="*196)
        print(M,"PASS")
        print("Repair family                              : BOUNDED PARENT-OWNERSHIP RECONCILIATION")
        print("Support                                    : EXISTING E37A ONLY")
        print("Accepted mixed CV masses                   : PRESERVED EXACTLY")
        print("Parent residual Cartesian sidecar          : PRESERVED")
        print("Zero-delta parent identity                 : REQUIRED")
        print("Flow-refresh schedule                      : Day30 / Day35 / Day40 / Day45 UNCHANGED")
        print("R3 physics / Hybrid / LP execution         : NONE")
        print("Recommended runtime                        : CPU")
        print("INT-A1-R4                                  : AUTHORIZED")
        print("R4 local validation before trajectory      : REQUIRED")
        print("INT-VIS-A1                                 : NOT YET AUTHORIZED")
        print("P4                                         : CLOSED")
        print("="*196)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps({
            "milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),"gates":gates,
            "INT_A1_R4_execution_authorized":False,
            "INT_VIS_A1_integrated_3D_visualization_authorized":False,
            "production_pressure_refresh_cadence_selected":False,
            "P4_authorized":False,
        },indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(M,"BLOCK");print("Stage:",stage);print("Exception:",repr(exc));return 2

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",type=Path,default=Path("."))
    ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test:
        selftest(a.project_root.resolve())
        raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))
