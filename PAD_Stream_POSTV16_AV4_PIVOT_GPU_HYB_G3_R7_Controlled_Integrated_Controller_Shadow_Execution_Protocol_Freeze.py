#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

M="POSTV16-AV4-PIVOT-GPU-HYB-G3-R7"
PASS="POSTV16AV4PIVOTGPUHYBG3R7_CONTROLLED_INTEGRATED_CONTROLLER_SHADOW_EXECUTION_PROTOCOL_FREEZE_PASS_NO_PHYSICS_EXECUTION"
BLOCK="POSTV16AV4PIVOTGPUHYBG3R7_TECHNICAL_OR_AUTHORITY_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="559fc472b218b3721e5306e92946dd346a6db025"

G3R6_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R6_AcceptedState_Timeline_Controller_Shadow_Replay_and_Refresh_Event_Audit.py"
G3R6_BLOB="570b63553dd277309be529655045a0fea2f8d431"
G3R5_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R5_Reconciled_Runtime_Controller_Shadow_Implementation_and_Test.py"
G3R5_BLOB="0675eaac7e1c47601dada82e295beaab0076c998"
CTRL_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_Integrated_Runtime_Controller_R2.py"
CTRL_BLOB="2d1c4fd3b792c9c19bef268b74956574bcaaf540"
G2R3_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_Rank3_Day40_45_ExactFlow_and_Hybrid_Endpoint_Diagnostic.py"
G2R3_BLOB="b06a18d93e68dca2c3d7326cc8b76e4116999117"
B5_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_B5_CPU_GPU_Overlap_Economics_Probe.py"
B5_BLOB="e3149d043c71fa7745b37f01bb27630fcbdfa563"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

G3R6_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G3_R6_AcceptedState_Timeline_Controller_Shadow_Replay_and_Refresh_Event_Audit"
G3R6_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R6_Summary.json"
G3R6_CONTRACT="POSTV16_AV4_PIVOT_GPU_HYB_G3_R6_Replay_Contract.json"
G3R6_DECISION="POSTV16_AV4_PIVOT_GPU_HYB_G3_R6_Decision_Contract.json"
G3R6_STATUS="POSTV16AV4PIVOTGPUHYBG3R6_ACCEPTED_STATE_TIMELINE_CONTROLLER_SHADOW_REPLAY_AND_REFRESH_EVENT_AUDIT_PASS_NO_PHYSICS_EXECUTION"

B5_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G4_B5_Route_Economics_Instrumentation"
B5_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_B5_Summary.json"
B5_STATUS="POSTV16AV4PIVOTGPUHYBG4B5_CPU_GPU_OVERLAP_ECONOMICS_PROBE_PASS"

DEVELOPMENT_REFERENCE_DAYS=5.0
CONTROLLED_START_DAY=30.0
CONTROLLED_END_DAY=45.0
CONTROLLED_REFRESH_BOUNDARIES=(35.0,40.0,45.0)
VISUALIZATION_DAYS=(30.0,35.0,40.0,45.0)
NEXT_MILESTONE="POSTV16-AV4-PIVOT-GPU-HYB-INT-A1"

REFRESH_SEQUENCE=(
    "PRESERVE_CELLWISE_CARTESIAN_CO2_COMPONENT_MASS",
    "TEMPORAL_PRESSURE_SEED",
    "EXACT_FINITE_VOLUME_PRESSURE_CORRECTION",
    "DIRECT_SPSOLVE_REFERENCE_OR_FALLBACK_IF_REQUIRED",
    "CONSERVATIVE_DARCY_FACE_FLUXES",
    "EXACT_POLLOCK_STREAMLINES",
    "TIME_OF_FLIGHT_WEIGHTS_CONNECTIVITY",
    "REFRESHED_FLOW_CFL",
)

TRANSPORT_REUSE_SEQUENCE=(
    "SAMPLE_CURRENT_CARTESIAN_STATE_TO_E37A_COMPONENT_MASS_CVS",
    "HYBRID10_PARENT_ANCHORED_INCREMENT_ON_ELIGIBLE_ROUTES",
    "EXACT_E37A_FALLBACK_ON_ALL_OTHER_ROUTES",
    "EXACT_PARENT_PLUS_INLET_MINUS_OUTLET_COMPONENT_MASS_BUDGET",
    "BOX_CONSTRAINED_CONSERVATIVE_MASS_PROJECTION",
    "SINGLE_COMMON_E37A_CV_TO_CARTESIAN_MAPBACK",
    "CONSERVATIVE_CARTESIAN_CAPILLARY_REDISTRIBUTION",
    "CREATE_NEXT_RECURRENT_STATE",
)

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G3_R7"
OUT_REL=BASE/(OUT_TOKEN+"_Controlled_Integrated_Controller_Shadow_Execution_Protocol_Freeze")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
PROTOCOL=f"{OUT_TOKEN}_INT_A1_Protocol.json"
DECISION=f"{OUT_TOKEN}_Decision_Contract.json"
EVENTS=f"{OUT_TOKEN}_Controller_Event_Schedule.csv"
OUTPUTS=f"{OUT_TOKEN}_Required_INT_A1_Outputs.csv"
GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"

class GateError(RuntimeError):
    pass

def gt(root:Path,*args:str)->str:
    return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()

def sha256(p:Path)->str:
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda:f.read(1<<20),b""):
            h.update(c)
    return h.hexdigest()

def js(p:Path):
    return json.loads(Path(p).read_text(encoding="utf-8"))

def file_sha256(p:Path)->str:
    return sha256(p)

def exact_blob(root:Path,filename:str,expected:str)->str:
    p=root/filename
    if not p.is_file():
        raise GateError(f"missing_source:{filename}")
    actual=gt(root,"hash-object",str(p))
    if actual!=expected:
        raise GateError(f"source_blob:{filename}:{actual}:{expected}")
    return actual

def import_exact(root:Path,filename:str,expected:str,name:str):
    exact_blob(root,filename,expected)
    p=root/filename
    spec=importlib.util.spec_from_file_location(name,p)
    if spec is None or spec.loader is None:
        raise GateError(f"import_spec:{filename}")
    m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m
    spec.loader.exec_module(m)
    return m

def write_csv(p:Path,rows):
    rows=list(rows)
    if not rows:
        p.write_text("",encoding="utf-8")
        return
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with open(p,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

def selftest(root:Path):
    g3r5=import_exact(root,G3R5_RUNNER,G3R5_BLOB,"g3r7_g3r5_selftest")
    ctrl=import_exact(root,CTRL_RUNNER,CTRL_BLOB,"g3r7_ctrl_selftest")
    g2=import_exact(root,G2R3_RUNNER,G2R3_BLOB,"g3r7_g2r3_selftest")
    exact_blob(root,G3R6_RUNNER,G3R6_BLOB)
    exact_blob(root,B5_RUNNER,B5_BLOB)

    assert g3r5.DEVELOPMENT_REFERENCE_DAYS==DEVELOPMENT_REFERENCE_DAYS
    assert g3r5.PRODUCTION_MAX_FLOW_EPOCH_DAYS is None
    assert tuple(ctrl.production_refresh_sequence())==REFRESH_SEQUENCE
    assert tuple(ctrl.transport_reuse_sequence())==TRANSPORT_REUSE_SEQUENCE
    assert g2.TARGET_FINAL==45.0
    assert g2.DAY30_RESTART_SHA=="093fa9570b07d91d6865c8464104cd6f72c271b2d638b93dc167c74497827035"
    assert g3r5.decide_shadow_action(35.0,30.0).action=="FULL_FLOW_REFRESH"
    assert g3r5.decide_shadow_action(40.0,35.0).action=="FULL_FLOW_REFRESH"
    assert g3r5.decide_shadow_action(45.0,40.0).action=="FULL_FLOW_REFRESH"
    print("POSTV16 GPU-HYB-G3-R7 structural/integration-protocol self-test: PASS")

def main(root:Path,drive:Path)->int:
    root=root.resolve()
    drive=drive.resolve()
    out=drive/OUT_REL
    blocked=drive/BLOCK_REL
    gates=[]
    stage="preflight"

    def gate(name,cond,detail=None):
        ok=bool(cond)
        gates.append({
            "stage":stage,
            "gate":name,
            "pass":ok,
            "detail":"" if detail is None else repr(detail),
        })
        print(f"[{'PASS' if ok else 'FAIL'}] {name}"+("" if detail is None else f" -- {detail}"),flush=True)
        if not ok:
            raise GateError(name)

    try:
        print("="*190)
        print("G3-R7 — CONTROLLED INTEGRATED CONTROLLER-SHADOW EXECUTION PROTOCOL FREEZE")
        print("FINAL G3 CONTROLLER-PHASE FREEZE. NO PHYSICS EXECUTION. NO CANONICAL STATE MUTATION.")
        print("ON PASS, AUTHORIZES INT-A1: CONTROLLED WHOLE-SYSTEM DAY30->45 PAD-STREAM RUN.")
        print("="*190)

        stage="repository"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_G3_R6_PASS_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")

        stage="source_authority"
        bindings=[
            ("G3_R6",G3R6_RUNNER,G3R6_BLOB),
            ("G3_R5_SHADOW_CONTROLLER",G3R5_RUNNER,G3R5_BLOB),
            ("G4_CONTROLLER_R2",CTRL_RUNNER,CTRL_BLOB),
            ("G2_R3_DAY30_45_REFERENCE",G2R3_RUNNER,G2R3_BLOB),
            ("G4_B5_RUNTIME_CONTEXT",B5_RUNNER,B5_BLOB),
        ]
        for role,fn,blob in bindings:
            gate(role+"_blob_exact",exact_blob(root,fn,blob)==blob)

        g3r5=import_exact(root,G3R5_RUNNER,G3R5_BLOB,"g3r7_g3r5")
        ctrl=import_exact(root,CTRL_RUNNER,CTRL_BLOB,"g3r7_ctrl")
        g2=import_exact(root,G2R3_RUNNER,G2R3_BLOB,"g3r7_g2r3")

        stage="G3_R6_authority"
        s6p=drive/G3R6_REL/G3R6_SUM
        c6p=drive/G3R6_REL/G3R6_CONTRACT
        d6p=drive/G3R6_REL/G3R6_DECISION
        for label,p in [("G3R6_summary",s6p),("G3R6_contract",c6p),("G3R6_decision",d6p)]:
            gate(label+"_present",p.is_file(),str(p))
        s6=js(s6p);c6=js(c6p);d6=js(d6p)
        gate("G3R6_status_exact",s6.get("status")==G3R6_STATUS,s6.get("status"))
        gate("G3R6_reference_5d",float(s6.get("development_reference_days"))==5.0)
        gate("G3R6_production_epoch_unselected",s6.get("production_max_flow_epoch_days") is None)
        gate("G3R6_Day30_45_boundaries_exact",s6.get("Day30_to45_projected_boundaries")==[35.0,40.0,45.0],s6.get("Day30_to45_projected_boundaries"))
        gate("G3R6_real_transition_evidence_present",int(s6.get("continuous_accepted_transition_count",0))>0,s6.get("continuous_accepted_transition_count"))
        gate("G3R6_no_false_global_continuity",s6.get("false_Day75_to80_continuity_claim_made") is False)
        gate("G3R6_R7_authorized",s6.get("G3_R7_controlled_integrated_controller_shadow_execution_protocol_freeze_authorized") is True)
        gate("G3R6_R7_no_canonical_mutation",s6.get("G3_R7_canonical_state_mutation_authorized") is False)
        gate("G3R6_R7_no_production",s6.get("G3_R7_production_activation_authorized") is False)
        gate("G3R6_decision_next_is_R7",d6.get("next_milestone",{}).get("name")=="POSTV16-AV4-PIVOT-GPU-HYB-G3-R7")
        gate("G3R6_contract_no_global_continuity",c6.get("interpretation_guards",{}).get("no_global_Day30_to405_continuity_claim") is True)

        stage="Day30_reference_authority"
        bridge_sum=drive/g2.R3A0_REL/g2.R3A0_SUM
        restart=drive/g2.R3A0_REL/g2.R3A0_RESTART
        g2sum=drive/g2.OUT_REL/g2.SUMMARY
        g2steps=drive/g2.OUT_REL/g2.STEPS
        for label,p in [
            ("Day30_bridge_summary",bridge_sum),
            ("Day30_current_authority_restart",restart),
            ("G2R3_reference_summary",g2sum),
            ("G2R3_reference_steps",g2steps),
        ]:
            gate(label+"_present",p.is_file(),str(p))
        bs=js(bridge_sum)
        rs=js(g2sum)
        gate("Day30_bridge_status_exact",bs.get("status")==g2.R3A0_STATUS,bs.get("status"))
        gate("Day30_restart_SHA_summary_exact",bs.get("current_authority_Day30_restart_sha256")==g2.DAY30_RESTART_SHA,bs.get("current_authority_Day30_restart_sha256"))
        gate("Day30_restart_file_SHA_exact",file_sha256(restart)==g2.DAY30_RESTART_SHA,file_sha256(restart))
        gate("G2R3_reference_status_exact",rs.get("status")==g2.PASS,rs.get("status"))
        gate("G2R3_continuous_reference_30_45",rs.get("continuous_30_to45_rollout") is True)
        gate("G2R3_reference_Day40_not_restart",rs.get("Day40_was_restart") is False)
        gate("G2R3_reference_no_production_cadence",rs.get("production_pressure_refresh_cadence_selected") is False)

        stage="controller_semantics"
        gate("shadow_reference_5d",float(g3r5.DEVELOPMENT_REFERENCE_DAYS)==5.0)
        gate("shadow_production_epoch_unselected",g3r5.PRODUCTION_MAX_FLOW_EPOCH_DAYS is None)
        gate("refresh_sequence_exact",tuple(ctrl.production_refresh_sequence())==REFRESH_SEQUENCE,ctrl.production_refresh_sequence())
        gate("reuse_sequence_exact",tuple(ctrl.transport_reuse_sequence())==TRANSPORT_REUSE_SEQUENCE,ctrl.transport_reuse_sequence())
        gate("learned_pressure_checkpoint_not_production",ctrl.LEARNED_PRESSURE_CHECKPOINT_POLICY=="RESEARCH_REFERENCE_ONLY_NOT_PRODUCTION_AUTHORIZED",ctrl.LEARNED_PRESSURE_CHECKPOINT_POLICY)
        gate("pressure_seed_policy_temporal_exact_FV",ctrl.PRESSURE_SEED_PRODUCTION_POLICY=="TEMPORAL_SEED_EXACT_FV_CORRECTION",ctrl.PRESSURE_SEED_PRODUCTION_POLICY)

        stage="B5_transport_context"
        b5p=drive/B5_REL/B5_SUM
        gate("B5_summary_present",b5p.is_file(),str(b5p))
        b5=js(b5p)
        gate("B5_status_exact",b5.get("status")==B5_STATUS,b5.get("status"))
        gate("B5_exact_output_identity_certified",b5.get("exact_output_identity_certified") is True)
        gate("B5_R4_transport_authority_preserved",b5.get("G4_B4_fixed_shape_graph_transport_authority_preserved") is True)
        gate("B5_integrated_production_closed",b5.get("integrated_GPU_runtime_production_authorized") is False)
        gate("B5_P4_closed",b5.get("P4_authorized") is False)

        stage="INT_A1_protocol_freeze"
        event_rows=[]
        origin=CONTROLLED_START_DAY
        init=g3r5.decide_shadow_action(CONTROLLED_START_DAY,CONTROLLED_START_DAY,hard_triggers=("RESTART_OR_INITIALIZATION",))
        gate("Day30_initialization_refresh",init.action=="FULL_FLOW_REFRESH",init.action)
        event_rows.append({
            "event_index":0,
            "event_day":30.0,
            "event_type":"CONTROLLED_RUN_INITIALIZATION",
            "flow_epoch_origin_before_event":30.0,
            "flow_epoch_age_days":0.0,
            "controller_action":init.action,
            "controller_reason":init.reason,
            "same_time_refresh_required":True,
            "accepted_state_must_exist_at_event":True,
        })
        for i,day in enumerate(CONTROLLED_REFRESH_BOUNDARIES,1):
            d=g3r5.decide_shadow_action(day,origin)
            gate(f"Day{int(day)}_5d_boundary_refresh",d.action=="FULL_FLOW_REFRESH",d.action)
            event_rows.append({
                "event_index":i,
                "event_day":day,
                "event_type":"FIVE_DAY_DEVELOPMENT_CONTROLLER_BOUNDARY",
                "flow_epoch_origin_before_event":origin,
                "flow_epoch_age_days":day-origin,
                "controller_action":d.action,
                "controller_reason":d.reason,
                "same_time_refresh_required":True,
                "accepted_state_must_exist_at_event":True,
            })
            origin=day

        gate("INT_A1_boundaries_exact",[r["event_day"] for r in event_rows[1:]]==[35.0,40.0,45.0])
        gate("INT_A1_final_day_exact",origin==45.0)

        required_outputs=[
            {
                "output":"CONTROLLED_STATE_CHECKPOINT",
                "days":"30,35,40,45",
                "required_contents":"Cartesian saturation; cellwise CO2 component mass; stored/injected/produced mass ledgers; accepted-step/time metadata",
                "required":True,
                "visualization_ready":True,
            },
            {
                "output":"PRESSURE_FLOW_CHECKPOINT",
                "days":"30,35,40,45",
                "required_contents":"exact-corrected pressure; Darcy face fluxes; flow residuals; refresh metadata",
                "required":True,
                "visualization_ready":True,
            },
            {
                "output":"STREAMLINE_TOF_CHECKPOINT",
                "days":"30,35,40,45",
                "required_contents":"Pollock streamline geometry; producer labels/connectivity; TOF; streamline weights",
                "required":True,
                "visualization_ready":True,
            },
            {
                "output":"CONTROLLER_EVENT_LEDGER",
                "days":"30-45",
                "required_contents":"flow epoch origin; age; action; reason; hard trigger; boundary landing; refresh count",
                "required":True,
                "visualization_ready":False,
            },
            {
                "output":"TRANSPORT_ROUTE_LEDGER",
                "days":"30-45",
                "required_contents":"Hybrid10 eligible/accepted/rejected routes; exact E37A fallbacks; conservative projection/mapback diagnostics",
                "required":True,
                "visualization_ready":False,
            },
            {
                "output":"REFERENCE_COMPARISON",
                "days":"40,45",
                "required_contents":"controlled integrated state vs immutable G2-R3 exact-reference diagnostics; report finite differences without inventing a new scientific tolerance",
                "required":True,
                "visualization_ready":True,
            },
        ]

        protocol={
            "milestone":M,
            "status":PASS,
            "main_spine_transition":"EXIT_G3_CONTROLLER_DEVELOPMENT_ENTER_CONTROLLED_WHOLE_SYSTEM_INTEGRATION",
            "next_milestone":NEXT_MILESTONE,
            "next_milestone_name":"Controlled Integrated PAD-Stream Day30-to-Day45 Run",
            "execution_scope":"CONTROLLED_NONCANONICAL_WHOLE_SYSTEM_SHADOW_TRAJECTORY",
            "environment":"Google Colab A100 80GB High-RAM",
            "start_authority":{
                "day":30.0,
                "artifact":"current-authority mass-conservative refreshed Day30 restart",
                "sha256":g2.DAY30_RESTART_SHA,
                "canonical_source_remains_immutable":True,
            },
            "time_window":{
                "start_day":30.0,
                "end_day":45.0,
                "exact_controller_boundary_days":[35.0,40.0,45.0],
                "boundary_landing_policy":"CLIP_ACCEPTED_TIMESTEP_TO_CONTROLLER_BOUNDARY_BEFORE_REFRESH",
                "boundary_state_semantics":"each controller boundary must be an exact accepted state before same-time refresh",
            },
            "controller":{
                "authority":"G3-R5 reconciled GPU-Hybrid development shadow controller",
                "development_reference_days":5.0,
                "production_max_flow_epoch_days":None,
                "hard_refresh_triggers":list(g3r5.HARD_REFRESH_TRIGGERS),
                "production_cadence_selected":False,
            },
            "full_refresh":{
                "same_time":True,
                "preserve_cellwise_cartesian_CO2_component_mass":True,
                "preserve_injection_production_stored_mass_ledgers":True,
                "sequence":list(REFRESH_SEQUENCE),
                "learned_pressure_checkpoint_policy":"RESEARCH_REFERENCE_ONLY_NOT_PRODUCTION_AUTHORIZED",
                "pressure_seed_policy":"TEMPORAL_SEED_EXACT_FV_CORRECTION",
            },
            "transport_between_refreshes":{
                "sequence":list(TRANSPORT_REUSE_SEQUENCE),
                "Hybrid10_role":"PROPOSAL_ON_ELIGIBLE_ROUTES_ONLY",
                "exact_E37A_role":"FALLBACK_AND_EXACT_CONSERVATIVE_TRANSPORT_AUTHORITY",
                "conservative_projection_required":True,
                "single_common_mapback_required":True,
                "capillary_redistribution_required":True,
                "R4_fixed_shape_graph_exact_transport_authority_preserved":True,
                "B5_overlap_scheduling":"OPTIONAL_PERFORMANCE_LAYER_ONLY_IF_EXACT_OUTPUT_IDENTITY_IS_PRESERVED",
            },
            "capacity_safety":{
                "preflight_before_accept":True,
                "preflight_rejection_is_hard_refresh_trigger":True,
                "same_parent_refresh_before_any_post_rejection_accept":True,
                "no_overcapacity_state_may_be_accepted":True,
                "existing_exact_capacity_control_semantics_preserved":True,
            },
            "acceptance_gates":{
                "exact_final_day_45":True,
                "no_nan_or_nonfinite_authoritative_state":True,
                "saturation_and_capacity_bounds_required":True,
                "step_component_mass_conservation_required":True,
                "same_time_refresh_mass_invariance_required":True,
                "pressure_flow_refresh_sequence_required":True,
                "controller_boundaries_exact_35_40_45_required":True,
                "Hybrid_may_not_bypass_exact_conservative_correction":True,
                "no_new_scientific_tolerance_defined":True,
            },
            "reference_comparison":{
                "immutable_reference":"G2-R3 Day30->45 exact/current-authority historical run",
                "comparison_days":[40.0,45.0],
                "purpose":"diagnostic comparison only; controlled integrated trajectory is expected to differ because cadence and Hybrid transport authority differ",
                "new_acceptance_threshold_defined":False,
            },
            "visualization_contract":{
                "checkpoint_days":[30.0,35.0,40.0,45.0],
                "pressure_3D_ready":True,
                "saturation_and_CO2_mass_3D_ready":True,
                "streamlines_3D_ready":True,
                "TOF_3D_ready":True,
                "pressure_change_between_refreshes_ready":True,
            },
            "scope_guards":{
                "G3_R7_physics_execution":False,
                "G3_R7_canonical_state_mutation":False,
                "INT_A1_outputs_are_controlled_noncanonical":True,
                "production_pressure_refresh_cadence_selected":False,
                "integrated_GPU_runtime_production_authorized":False,
                "P4_authorized":False,
            },
        }

        decision={
            "milestone":M,
            "status":PASS,
            "G3_controller_development_phase_closed":True,
            "INT_A1_controlled_integrated_Day30_to45_run_authorized":True,
            "INT_A1_start_day":30.0,
            "INT_A1_end_day":45.0,
            "INT_A1_refresh_boundary_days":[35.0,40.0,45.0],
            "INT_A1_visualization_checkpoint_days":[30.0,35.0,40.0,45.0],
            "INT_A1_canonical_state_mutation_authorized":False,
            "INT_A1_production_activation_authorized":False,
            "production_pressure_refresh_cadence_selected":False,
            "P4_authorized":False,
            "next_after_INT_A1":"Integrated 3D validation / visualization from Day30, Day35, Day40, Day45 checkpoints, followed by longer-horizon validation.",
        }

        summary={
            "milestone":M,
            "status":PASS,
            "classification":"FINAL_G3_CONTROLLER_PHASE_PROTOCOL_FROZEN_INT_A1_CONTROLLED_WHOLE_SYSTEM_DAY30_DAY45_INTEGRATION_AUTHORIZED_WITH_EXACT_5DAY_BOUNDARIES_AND_VISUALIZATION_READY_CHECKPOINTS",
            "G3_R6_authority_bound":True,
            "G3_R5_controller_authority_bound":True,
            "G4_controller_semantics_bound":True,
            "G2_R3_Day30_45_reference_bound":True,
            "G4_B5_transport_context_bound":True,
            "G3_controller_development_phase_closed":True,
            "physics_executed":False,
            "canonical_state_mutated":False,
            "INT_A1_authorized":True,
            "INT_A1_window_days":[30.0,45.0],
            "INT_A1_refresh_boundary_days":[35.0,40.0,45.0],
            "INT_A1_visualization_checkpoint_days":[30.0,35.0,40.0,45.0],
            "INT_A1_trajectory_class":"CONTROLLED_NONCANONICAL_WHOLE_SYSTEM_SHADOW_TRAJECTORY",
            "INT_A1_requires_Hybrid10_plus_exact_E37A_conservative_transport":True,
            "INT_A1_requires_exact_FV_Darcy_Pollock_TOF_refresh":True,
            "INT_A1_requires_stepwise_component_mass_conservation":True,
            "INT_A1_production_activation_authorized":False,
            "production_max_flow_epoch_days":None,
            "production_pressure_refresh_cadence_selected":False,
            "integrated_GPU_runtime_production_authorized":False,
            "P4_authorized":False,
        }

        stage="scope_guards"
        gate("G3_R7_no_physics_execution",True)
        gate("G3_R7_no_state_mutation",True)
        gate("INT_A1_is_noncanonical",protocol["execution_scope"]=="CONTROLLED_NONCANONICAL_WHOLE_SYSTEM_SHADOW_TRAJECTORY")
        gate("production_epoch_unselected",summary["production_max_flow_epoch_days"] is None)
        gate("production_cadence_unselected",summary["production_pressure_refresh_cadence_selected"] is False)
        gate("production_activation_closed",summary["INT_A1_production_activation_authorized"] is False)
        gate("P4_closed",summary["P4_authorized"] is False)

        stage="publication"
        gate("output_absent",not out.exists(),str(out))
        out.mkdir(parents=True)
        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        (out/PROTOCOL).write_text(json.dumps(protocol,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        (out/DECISION).write_text(json.dumps(decision,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        write_csv(out/EVENTS,event_rows)
        write_csv(out/OUTPUTS,required_outputs)
        write_csv(out/GATES,gates)
        write_csv(out/MANIFEST,[
            {"file":q.name,"sha256":sha256(q),"bytes":q.stat().st_size}
            for q in sorted(out.iterdir()) if q.is_file() and q.name!=MANIFEST
        ])

        print("="*190)
        print(M,"PASS")
        print("Main-spine transition                         : G3 CONTROLLER PHASE -> INT-A1 WHOLE-SYSTEM INTEGRATION")
        print("Controlled window                             : Day30 -> Day45")
        print("Exact 5-day refresh boundaries               : Day35 / Day40 / Day45")
        print("Visualization-ready checkpoints              : Day30 / Day35 / Day40 / Day45")
        print("Hybrid10 + exact E37A conservative transport  : REQUIRED")
        print("Exact FV -> Darcy -> Pollock -> TOF refresh   : REQUIRED")
        print("Canonical trajectory mutation                 : False")
        print("INT-A1 authorized                             : True")
        print("Production activation authorized              : False")
        print("P4 authorized                                 : False")
        print("="*190)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps({
            "milestone":M,
            "status":BLOCK,
            "failed_stage":stage,
            "exception":repr(exc),
            "gates":gates,
            "G3_controller_development_phase_closed":False,
            "INT_A1_controlled_integrated_Day30_to45_run_authorized":False,
            "production_pressure_refresh_cadence_selected":False,
            "integrated_GPU_runtime_production_authorized":False,
            "P4_authorized":False,
        },indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(M,"BLOCK")
        print("Stage:",stage)
        print("Exception:",repr(exc))
        return 2

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
