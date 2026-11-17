#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
from typing import Any

M="POSTV16-AV4-PIVOT-GPU-HYB-G4-A6"
PASS="POSTV16AV4PIVOTGPUHYBG4A6_INTEGRATED_RUNTIME_ASSEMBLY_PASS_A7_CONTROLLED_INTEGRATED_TRAJECTORY_AUTHORIZED"
BLOCK="POSTV16AV4PIVOTGPUHYBG4A6_TECHNICAL_OR_AUTHORITY_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="d8816c8fc25514a198df87ad6d295b02f266f9c0"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID
BASE_AV4=BASE/"POSTV16_AV4_Dynamic_Flow_Coupling"
BASE_AV5=BASE/"POSTV16_AV5_Learned_Acceleration"

A5_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_A5_Short_Mixed_Recurrent_Rollout.py"
A5_BLOB="e366446f5c2e1e12b1ea74d9c63f079af36d8b15"
B3_RUNNER="PAD_Stream_POSTV16_AV5_B3_Validation_WallClock_Economics_Outcome_Interpretation_and_AV5_LearnedAcceleration_Closure_Decision_Freeze.py"
B3_BLOB="693f95c53db9c8e5705a62b0feb0baa3571d92d2"
R3R6_RUNNER="PAD_Stream_V16E41R3R6_Production_Runtime_Refresh_Policy_Freeze.py"
R3R6_BLOB="b7fe6bfd1c23cf77402b486c0036c0af3e3cbf15"
R3R4R1_RUNNER="PAD_Stream_V16E41R3R4R1_Refreshed_Flow_CFL_Alignment_Repair.py"
R3R4R1_BLOB="5f8433437ce111533338ceada922f51abb2edefe"
E37A_RUNNER="PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB="0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
G2R3A0_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_A0_Day30_CurrentAuthority_SameTime_Flow_Refresh_Bridge.py"
G2R3A0_BLOB="de8bedba356b661146997da55451e93fb4215c4d"
CONTROLLER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_Integrated_Runtime_Controller.py"

A5_REL=BASE_AV4/"POSTV16_AV4_PIVOT_GPU_HYB_G4_A5_Short_Mixed_Recurrent_Rollout"
A5_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_A5_Summary.json"
A5_STATUS="POSTV16AV4PIVOTGPUHYBG4A5_SHORT_MIXED_RECURRENT_ROLLOUT_PASS"

B3_REL=BASE_AV5/"POSTV16_AV5_B3_Validation_WallClock_Economics_Outcome_Interpretation_and_AV5_LearnedAcceleration_Closure_Decision_Freeze"
B3_SUM="PAD_Stream_POSTV16_AV5_B3_Summary.json"
B3_DISPOSITION="POSTV16_AV5_B3_Learned_Pressure_Seed_Disposition_Contract.json"
B3_STATUS=(
    "POSTV16AV5B3_VALIDATION_WALLCLOCK_ECONOMICS_OUTCOME_INTERPRETATION_"
    "AND_AV5_LEARNED_ACCELERATION_CLOSURE_DECISION_FREEZE_PASS_NO_MODEL_EXECUTION"
)

R3R6_REL=Path("provenance/hybrid_dp/V16E41R3R6_PRODUCTION_RUNTIME_REFRESH_POLICY_FREEZE")
R3R6_CONTRACT="PAD_Stream_V16E41R3R6_Production_Runtime_Refresh_Policy_Contract.json"
R3R6_CLOSURE="V16E41R3R6_Final_Closure.json"

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_A6"
OUT_REL=BASE_AV4/(OUT_TOKEN+"_Integrated_Runtime_Assembly")
BLOCK_REL=BASE_AV4/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
CONTRACT=f"{OUT_TOKEN}_Integrated_Runtime_Contract.json"
COMPONENTS=f"{OUT_TOKEN}_Component_Bindings.csv"
DECISION=f"{OUT_TOKEN}_Decision_Contract.json"
GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"

class GateError(RuntimeError):pass

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""):h.update(c)
    return h.hexdigest()

def gt(root:Path,*a:str)->str:
    return subprocess.check_output(["git","-C",str(root),*a],text=True).strip()

def js(p:Path):return json.loads(p.read_text(encoding="utf-8"))

def write_csv(p:Path,rows:list[dict[str,Any]]):
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields:fields.append(k)
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows)

def load_module(path:Path,name:str):
    s=importlib.util.spec_from_file_location(name,path)
    if s is None or s.loader is None:raise GateError(f"import_spec:{path.name}")
    m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m

def selftest():
    assert PARENT and len(PARENT)==40
    print("POSTV16 GPU-HYB-G4-A6 structural self-test: PASS")

def main(root:Path,drive:Path)->int:
    root=root.resolve();drive=drive.resolve();out=drive/OUT_REL;blocked=drive/BLOCK_REL
    gates=[];stage="preflight"
    def gate(n,c,d=None):
        ok=bool(c);gates.append({"stage":stage,"gate":n,"pass":ok,"detail":"" if d is None else repr(d)})
        print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"),flush=True)
        if not ok:raise GateError(n)
    try:
        print("="*196)
        print("G4-A6 — INTEGRATED GPU PAD-STREAM RUNTIME ASSEMBLY")
        print("ASSEMBLY/FREEZE ONLY. NO PHYSICAL TIME ADVANCE. NO PRESSURE SOLVE. NO HYBRID INFERENCE.")
        print("PRODUCTION PRESSURE PATH = TEMPORAL SEED + EXACT FV CORRECTION; AV5 LEARNED CHECKPOINT REMAINS RESEARCH-ONLY.")
        print("="*196)

        stage="repository"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_G4_A5",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")
        bindings=[
            ("G4_A5_recurrent_transport",A5_RUNNER,A5_BLOB),
            ("AV5_B3_pressure_disposition",B3_RUNNER,B3_BLOB),
            ("E41_R3_R6_refresh_policy",R3R6_RUNNER,R3R6_BLOB),
            ("E41_R3_R4_R1_refresh_CFL",R3R4R1_RUNNER,R3R4R1_BLOB),
            ("E37A_conservative_transfer",E37A_RUNNER,E37A_BLOB),
            ("G2_R3_A0_same_time_refresh_bridge",G2R3A0_RUNNER,G2R3A0_BLOB),
        ]
        component_rows=[]
        for role,fn,expected in bindings:
            p=root/fn;gate(role+"_present",p.is_file(),str(p))
            actual=gt(root,"hash-object",str(p)) if p.is_file() else "missing"
            gate(role+"_blob_exact",actual==expected,actual)
            component_rows.append({"role":role,"file":fn,"git_blob":actual})
        controller_path=root/CONTROLLER
        gate("integrated_controller_present",controller_path.is_file(),str(controller_path))
        controller=load_module(controller_path,"g4a6_controller")
        controller.self_test()

        stage="G4_A5_transport_authority"
        a5=js(drive/A5_REL/A5_SUM)
        gate("A5_status_exact",a5.get("status")==A5_STATUS,a5.get("status"))
        gate("A5_three_additional_transitions",int(a5.get("additional_transitions_executed"))==3,a5.get("additional_transitions_executed"))
        gate("A5_no_flow_refresh",a5.get("flow_refresh_executed_during_rollout") is False)
        gate("A5_five_day_reference_not_exceeded",a5.get("five_day_reference_exceeded") is False)
        gate("A5_A6_authorized",a5.get("G4_A6_integrated_GPU_runtime_assembly_authorized") is True)
        gate("A5_mass_residual_finite",abs(float(a5.get("mixed_final_cumulative_mass_residual_kg")))<1.0e-3,
             a5.get("mixed_final_cumulative_mass_residual_kg"))
        gate("A5_transport_accuracy_stable",float(a5.get("final_mixed_vs_exact_saturation_relative_L2"))<0.01,
             a5.get("final_mixed_vs_exact_saturation_relative_L2"))

        stage="AV5_B3_pressure_disposition"
        b3=js(drive/B3_REL/B3_SUM)
        disp=js(drive/B3_REL/B3_DISPOSITION)
        gate("B3_status_exact",b3.get("status")==B3_STATUS,b3.get("status"))
        gate("B3_scientific_mechanism_validated",b3.get("scientific_mechanism_validated") is True)
        gate("B3_wallclock_qualification_failed",b3.get("validation_wallclock_economic_qualification_pass") is False)
        gate("B3_workstream_closed",b3.get("AV5_learned_acceleration_workstream_closed") is True)
        gate("B3_checkpoint_research_only",
             b3.get("checkpoint_disposition")=="RESEARCH_REFERENCE_ONLY_NOT_PRODUCTION_AUTHORIZED",
             b3.get("checkpoint_disposition"))
        gate("B3_production_not_authorized",b3.get("AV5_production_execution_authorized") is False)
        gate("B3_pressure_seed_policy_no_change",
             disp.get("production_pressure_seed_policy")=="NO_CHANGE_AUTHORIZED_BY_AV5",
             disp.get("production_pressure_seed_policy"))
        gate("B3_temporal_seed_baseline_authoritative",
             disp.get("temporal_seed_exact_correction_baseline_remains_authoritative_reference") is True)
        gate("B3_exact_FV_authoritative",disp.get("exact_FV_correction_remains_authoritative") is True)
        gate("B3_direct_fallback_required",disp.get("direct_spsolve_reference_and_fallback_remains_required") is True)

        stage="exact_refresh_authority"
        r6=js(drive/R3R6_REL/R3R6_CONTRACT);r6c=js(drive/R3R6_REL/R3R6_CLOSURE)
        gate("R3R6_status_exact",r6.get("status")=="PRODUCTION_RUNTIME_REFRESH_POLICY_FROZEN",r6.get("status"))
        gate("R3R6_closure_pass",r6c.get("all_gates_passed") is True)
        gate("R3R6_same_time_mass_conserved",
             r6["same_time_flow_refresh_contract"]["primary_conserved_quantity"]=="cellwise Cartesian CO2 component mass array")
        gate("R3R6_flow_sequence_pressure_to_TOF",
             r6["same_time_flow_refresh_contract"]["flow_epoch_build_sequence"][:5]==[
                 "total_mobility_from_reconciled_saturation",
                 "finite_volume_pressure",
                 "conservative_Darcy_face_fluxes",
                 "exact_Pollock_streamlines",
                 "exact_time_of_flight",
             ],
             r6["same_time_flow_refresh_contract"]["flow_epoch_build_sequence"])
        gate("R3R6_hard_triggers_preserved",
             tuple(r6["refresh_trigger_policy"]["hard_refresh_triggers"])==tuple(controller.HARD_REFRESH_TRIGGERS),
             r6["refresh_trigger_policy"]["hard_refresh_triggers"])

        stage="controller_contract"
        d0=controller.decide_runtime_action(float(a5["final_day"]),75.0)
        gate("A5_final_state_dispatches_to_flow_reuse",d0.action=="REUSE_FLOW_NETWORK_FOR_MIXED_TRANSPORT",d0)
        gate("A5_final_flow_age_matches",abs(d0.flow_epoch_age_days-float(a5["final_flow_epoch_age_days"]))<=1e-12,
             (d0.flow_epoch_age_days,a5["final_flow_epoch_age_days"]))
        d1=controller.decide_runtime_action(80.0,75.0)
        gate("five_day_boundary_dispatches_to_refresh",d1.action=="FULL_FLOW_REFRESH",d1)
        d2=controller.decide_runtime_action(75.2,75.0,hard_triggers=("WELL_OR_CONTROL_CHANGE",))
        gate("hard_trigger_dispatches_to_refresh",d2.action=="FULL_FLOW_REFRESH",d2)
        gate("controller_pressure_policy_temporal_exact",
             controller.PRESSURE_SEED_PRODUCTION_POLICY=="TEMPORAL_SEED_EXACT_FV_CORRECTION",
             controller.PRESSURE_SEED_PRODUCTION_POLICY)
        gate("controller_learned_pressure_firewalled",
             controller.LEARNED_PRESSURE_CHECKPOINT_POLICY=="RESEARCH_REFERENCE_ONLY_NOT_PRODUCTION_AUTHORIZED",
             controller.LEARNED_PRESSURE_CHECKPOINT_POLICY)

        runtime_contract={
            "milestone":M,
            "status":PASS,
            "architecture_name":"PAD_STREAM_INTEGRATED_GPU_HYBRID_RECURRENT_RUNTIME_V1",
            "development_flow_refresh_reference_days":5.0,
            "development_reference_semantics":"CONSERVATIVE_INTEGRATION_REFERENCE_NOT_SCIENTIFIC_OPTIMALITY_CLAIM",
            "production_pressure_seed_policy":"TEMPORAL_SEED_EXACT_FV_CORRECTION",
            "learned_pressure_checkpoint_disposition":"RESEARCH_REFERENCE_ONLY_NOT_PRODUCTION_AUTHORIZED",
            "refresh_dispatch":{
                "age_reference_days":5.0,
                "hard_triggers":list(controller.HARD_REFRESH_TRIGGERS),
                "same_time_refresh_preserves":"cellwise Cartesian CO2 component mass",
                "flow_refresh_sequence":list(controller.production_refresh_sequence()),
            },
            "transport_dispatch":{
                "flow_fresh_action":"REUSE_FLOW_NETWORK_FOR_MIXED_TRANSPORT",
                "sequence":list(controller.transport_reuse_sequence()),
                "Hybrid_role":"PARENT_ANCHORED_INCREMENTAL_COMPONENT_MASS_PROPOSAL",
                "exact_fallback_role":"ALL_NONELIGIBLE_OR_UNSAFE_ROUTES",
                "conservation_authority":"EXACT_PARENT_PLUS_INLET_MINUS_OUTLET_COMPONENT_MASS_BUDGET",
                "grid_transfer_authority":"SINGLE_COMMON_E37A_MAPBACK",
            },
            "runtime_state_machine":[
                "READ_CURRENT_RECURRENT_STATE",
                "CHECK_HARD_REFRESH_TRIGGERS_AND_FLOW_EPOCH_AGE",
                "IF_REFRESH: SAME_TIME_MASS_CONSERVATIVE_EXACT_FLOW_REFRESH",
                "ELSE: REUSE_ACTIVE_FLOW_NETWORK",
                "EXECUTE_MIXED_GPU_HYBRID_PLUS_EXACT_FALLBACK_TRANSPORT",
                "EXACT_COMPONENT_MASS_BUDGET_CORRECTION",
                "COMMON_E37A_MAPBACK",
                "CONSERVATIVE_CAPILLARY",
                "CREATE_NEXT_RECURRENT_STATE",
                "REPEAT",
            ],
            "firewalls":{
                "AV5_learned_pressure_checkpoint_in_production":False,
                "pressure_without_exact_FV_correction":False,
                "Hybrid_absolute_parent_replacement":False,
                "Hybrid_unconserved_state_mutation":False,
                "route_specific_grid_mapback":False,
                "cadence_optimization_in_A6":False,
            },
            "A7_controlled_integrated_trajectory_scope":{
                "include_flow_reuse_steps":True,
                "include_at_least_one_full_flow_refresh":True,
                "use_5day_development_reference":True,
                "pressure_seed":"TEMPORAL",
                "exact_FV_correction_required":True,
                "Hybrid_transport_enabled":True,
                "exact_fallback_enabled":True,
                "canonical_production_chain_replacement":False,
            },
        }
        decision={
            "milestone":M,"status":PASS,
            "G4_A6_integrated_runtime_architecture_frozen":True,
            "G4_A6_controller_module_certified":True,
            "Hybrid_recurrent_transport_integrated":True,
            "exact_flow_refresh_integrated":True,
            "AV5_learned_pressure_checkpoint_production_integrated":False,
            "temporal_pressure_seed_exact_correction_integrated":True,
            "G4_A7_controlled_integrated_trajectory_authorized":True,
            "integrated_GPU_runtime_production_authorized":False,
            "P4_authorized":False,
        }
        summary={
            "milestone":M,"status":PASS,
            "classification":"INTEGRATED_GPU_PAD_STREAM_RUNTIME_STATE_MACHINE_ASSEMBLED_HYBRID_TRANSPORT_PLUS_EXACT_FLOW_REFRESH_A7_CONTROLLED_INTEGRATED_TRAJECTORY_AUTHORIZED",
            "A5_final_day":float(a5["final_day"]),
            "A5_final_flow_epoch_age_days":float(a5["final_flow_epoch_age_days"]),
            "A5_final_mixed_vs_exact_saturation_relative_L2":float(a5["final_mixed_vs_exact_saturation_relative_L2"]),
            "development_flow_refresh_reference_days":5.0,
            "AV5_learned_pressure_checkpoint_disposition":"RESEARCH_REFERENCE_ONLY_NOT_PRODUCTION_AUTHORIZED",
            "production_pressure_seed_policy":"TEMPORAL_SEED_EXACT_FV_CORRECTION",
            "exact_FV_correction_authoritative":True,
            "direct_spsolve_reference_and_fallback_required":True,
            "Hybrid_parent_anchored_incremental_transport_active":True,
            "exact_E37A_fallback_active":True,
            "single_common_E37A_mapback":True,
            "conservative_capillary_active":True,
            "controller_A5_final_dispatch":d0.action,
            "controller_5day_boundary_dispatch":d1.action,
            "hard_refresh_triggers":list(controller.HARD_REFRESH_TRIGGERS),
            "physical_time_advanced":False,
            "model_inference_executed":False,
            "pressure_solve_executed":False,
            "canonical_state_mutated":False,
            "G4_A7_controlled_integrated_trajectory_authorized":True,
            "integrated_GPU_runtime_production_authorized":False,
            "P4_authorized":False,
        }

        stage="publication"
        gate("output_absent",not out.exists(),str(out));out.mkdir(parents=True)
        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        (out/CONTRACT).write_text(json.dumps(runtime_contract,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        (out/DECISION).write_text(json.dumps(decision,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        write_csv(out/COMPONENTS,component_rows);write_csv(out/GATES,gates)
        write_csv(out/MANIFEST,[{"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size}
                                for p in sorted(out.iterdir()) if p.is_file() and p.name!=MANIFEST])

        print("="*196);print(M,"PASS")
        print("Integrated runtime controller                 : CERTIFIED")
        print("A5 final dispatch                             :",d0.action)
        print("5-day boundary dispatch                       :",d1.action)
        print("Production pressure seed                      : TEMPORAL + EXACT FV CORRECTION")
        print("AV5 learned pressure checkpoint               : RESEARCH REFERENCE ONLY")
        print("Hybrid transport                              : PARENT-ANCHORED INCREMENTAL")
        print("Exact fallback / common mapback / capillary   : ACTIVE / ACTIVE / ACTIVE")
        print("G4-A7 controlled integrated trajectory        : AUTHORIZED")
        print("="*196)
        return 0
    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps({
            "milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),"gates":gates,
            "physical_time_advanced":False,"canonical_state_mutated":False,
            "G4_A7_controlled_integrated_trajectory_authorized":False,
            "integrated_GPU_runtime_production_authorized":False,"P4_authorized":False,
        },indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(M,"BLOCK");print("Stage:",stage);print("Exception:",repr(exc));return 2

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",type=Path,default=Path("."))
    ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test:selftest();raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))
