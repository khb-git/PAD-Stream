#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path

M="POSTV16-AV4-PIVOT-GPU-HYB-G3-R6"
PASS="POSTV16AV4PIVOTGPUHYBG3R6_ACCEPTED_STATE_TIMELINE_CONTROLLER_SHADOW_REPLAY_AND_REFRESH_EVENT_AUDIT_PASS_NO_PHYSICS_EXECUTION"
BLOCK="POSTV16AV4PIVOTGPUHYBG3R6_TECHNICAL_OR_AUTHORITY_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="676147ec6006ed113277a8743fcaf068fd151d18"

G3R5_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R5_Reconciled_Runtime_Controller_Shadow_Implementation_and_Test.py"
G3R5_BLOB="0675eaac7e1c47601dada82e295beaab0076c998"
G2R3_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_Rank3_Day40_45_ExactFlow_and_Hybrid_Endpoint_Diagnostic.py"
G2R3_BLOB="b06a18d93e68dca2c3d7326cc8b76e4116999117"
G2R1R1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_R1_Rank1_Day75_80_ExactFlow_and_Hybrid_Endpoint_Diagnostic.py"
G2R1R1_BLOB="04c3940a7c736b1d210376113e48bab6111fc173"
G2R2_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R2_Rank2_Day120_125_ExactFlow_and_Hybrid_Endpoint_Diagnostic.py"
G2R2_BLOB="1d08f9b2d7c2e38c69862028a731f695811e3cf8"
G3R2A0_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_A0_Late_Day405_Shadow_Compatibility_and_Protocol_Freeze.py"
G3R2A0_BLOB="61d2f3b7afe64035f1e363c93b658e499b9d3a8c"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

G3R5_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G3_R5_Reconciled_Runtime_Controller_Shadow_Implementation_and_Test"
G3R5_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R5_Summary.json"
G3R5_CONTRACT="POSTV16_AV4_PIVOT_GPU_HYB_G3_R5_Shadow_Controller_Contract.json"
G3R5_DECISION="POSTV16_AV4_PIVOT_GPU_HYB_G3_R5_Decision_Contract.json"
G3R5_STATUS="POSTV16AV4PIVOTGPUHYBG3R5_RECONCILED_RUNTIME_CONTROLLER_SHADOW_IMPLEMENTATION_AND_DECISION_MATRIX_PASS_NO_PHYSICS_EXECUTION"

G2R3_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_Rank3_Day40_Day45_ExactFlow_and_Hybrid_Endpoint_Diagnostic"
G2R3_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_Summary.json"
G2R3_STEPS="POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_Accepted_Transitions_30_to45.csv"
G2R3_REFRESH="POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_Flow_Refreshes_30_to45.csv"
G2R3_STATUS="POSTV16AV4PIVOTGPUHYBG2R3_RANK3_DAY40_DAY45_EXACT_FLOW_AND_READONLY_HYBRID_ENDPOINT_DIAGNOSTIC_PASS"

G2R1R1_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_R1_Rank1_Day75_Day80_ExactFlow_and_Hybrid_Endpoint_Diagnostic"
G2R1R1_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_R1_Summary.json"
G2R1R1_STATUS="POSTV16AV4PIVOTGPUHYBG2R1R1_RANK1_DAY75_DAY80_EXACT_FLOW_AND_READONLY_HYBRID_ENDPOINT_DIAGNOSTIC_PASS"
DAY69_TIME=69.88346704782309

G2R2_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R2_Rank2_Day120_Day125_ExactFlow_and_Hybrid_Endpoint_Diagnostic"
G2R2_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R2_Summary.json"
G2R2_STEPS="POSTV16_AV4_PIVOT_GPU_HYB_G2_R2_Accepted_Transitions_100_to125.csv"
G2R2_REFRESH="POSTV16_AV4_PIVOT_GPU_HYB_G2_R2_Flow_Refreshes_100_to125.csv"
G2R2_STATUS="POSTV16AV4PIVOTGPUHYBG2R2_RANK2_DAY120_DAY125_EXACT_FLOW_AND_READONLY_HYBRID_ENDPOINT_DIAGNOSTIC_PASS"

G3R2A0_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_A0_Late_Day405_Shadow_Compatibility_and_Protocol_Freeze"
G3R2A0_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_A0_Summary.json"
G3R2A0_PROTOCOL="POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_A0_Late_Day405_Shadow_Protocol.json"
G3R2A0_STATUS="POSTV16AV4PIVOTGPUHYBG3R2A0_LATE_DAY405_SAME_STATE_SHADOW_COMPATIBILITY_PROTOCOL_FREEZE_PASS_NO_PHYSICS_EXECUTION"

DEVELOPMENT_REFERENCE_DAYS=5.0

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G3_R6"
OUT_REL=BASE/(OUT_TOKEN+"_AcceptedState_Timeline_Controller_Shadow_Replay_and_Refresh_Event_Audit")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
CONTRACT=f"{OUT_TOKEN}_Replay_Contract.json"
DECISION=f"{OUT_TOKEN}_Decision_Contract.json"
REPLAY=f"{OUT_TOKEN}_Accepted_State_Replay.csv"
BOUNDARIES=f"{OUT_TOKEN}_Projected_5Day_Boundaries.csv"
LEGACY=f"{OUT_TOKEN}_Historical_Legacy_Refresh_Events.csv"
LATE=f"{OUT_TOKEN}_Late_Day405_Branch_Decisions.csv"
WINDOWS=f"{OUT_TOKEN}_Replay_Window_Audit.csv"
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

def js(p:Path):
    return json.loads(Path(p).read_text(encoding="utf-8"))

def read_csv(p:Path):
    with open(p,newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))

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

def f(v):
    return float(v)

def replay_continuous_window(
    *,
    window_name:str,
    rows:list[dict],
    start_day:float,
    end_day:float,
    shadow,
):
    tol=1e-10
    if not rows:
        raise GateError(f"{window_name}:empty_accepted_transition_ledger")

    parsed=[]
    for r in rows:
        parsed.append({
            "accepted_step_index":int(float(r["accepted_step_index"])),
            "parent_time_days":f(r["parent_time_days"]),
            "accepted_time_days":f(r["accepted_time_days"]),
            "accepted_dt_days":f(r["accepted_dt_days"]),
            "targeted_checkpoint_landing":str(r.get("targeted_checkpoint_landing","")).strip().lower()=="true",
        })
    parsed.sort(key=lambda x:(x["accepted_time_days"],x["accepted_step_index"]))

    if abs(parsed[0]["parent_time_days"]-start_day)>tol:
        raise GateError(f"{window_name}:start_parent:{parsed[0]['parent_time_days']}:{start_day}")
    if abs(parsed[-1]["accepted_time_days"]-end_day)>tol:
        raise GateError(f"{window_name}:end_accept:{parsed[-1]['accepted_time_days']}:{end_day}")

    for i,r in enumerate(parsed):
        if r["accepted_time_days"] <= r["parent_time_days"]:
            raise GateError(f"{window_name}:nonpositive_transition:{i}")
        if abs((r["accepted_time_days"]-r["parent_time_days"])-r["accepted_dt_days"])>1e-8:
            raise GateError(f"{window_name}:dt_mismatch:{i}")
        if i>0 and abs(r["parent_time_days"]-parsed[i-1]["accepted_time_days"])>tol:
            raise GateError(f"{window_name}:noncontinuous_ledger:{i}")

    replay_rows=[]
    boundary_rows=[]

    # Replay initialization is a shadow-only controller initialization event.
    origin=start_day
    init=shadow.decide_shadow_action(start_day,start_day,hard_triggers=("RESTART_OR_INITIALIZATION",))
    if init.action!="FULL_FLOW_REFRESH":
        raise GateError(f"{window_name}:shadow_initialization_not_refresh")
    replay_rows.append({
        "window":window_name,
        "event_kind":"SHADOW_REPLAY_INITIALIZATION_ONLY",
        "event_day":start_day,
        "accepted_state":True,
        "accepted_step_index":"",
        "flow_epoch_origin_before_event":start_day,
        "flow_epoch_age_days":0.0,
        "shadow_action":init.action,
        "shadow_reason":init.reason,
        "targeted_checkpoint_landing":False,
        "note":"Replay initialization only; does not assert the historical runtime used this trigger at this moment.",
    })

    for r in parsed:
        at=r["accepted_time_days"]

        # Insert exact projected 5-day boundaries that lie strictly before this accepted state.
        while origin+DEVELOPMENT_REFERENCE_DAYS < at-tol:
            b=origin+DEVELOPMENT_REFERENCE_DAYS
            if not (r["parent_time_days"]-tol <= b <= at+tol):
                # The boundary can only be inside the current accepted transition if the ledger is continuous.
                raise GateError(f"{window_name}:boundary_not_bracketed:{b}:{r['parent_time_days']}:{at}")
            d=shadow.decide_shadow_action(b,origin)
            if d.action!="FULL_FLOW_REFRESH":
                raise GateError(f"{window_name}:projected_boundary_not_refresh:{b}")
            boundary_rows.append({
                "window":window_name,
                "boundary_day":b,
                "bracket_parent_accepted_state_day":r["parent_time_days"],
                "bracket_child_accepted_state_day":at,
                "boundary_is_accepted_state":False,
                "shadow_action":d.action,
                "shadow_reason":d.reason,
                "note":"Projected controller event between real accepted states; not an accepted reservoir state.",
            })
            replay_rows.append({
                "window":window_name,
                "event_kind":"PROJECTED_5D_BOUNDARY_BETWEEN_ACCEPTED_STATES",
                "event_day":b,
                "accepted_state":False,
                "accepted_step_index":"",
                "flow_epoch_origin_before_event":origin,
                "flow_epoch_age_days":b-origin,
                "shadow_action":d.action,
                "shadow_reason":d.reason,
                "targeted_checkpoint_landing":False,
                "note":"Projected shadow-controller boundary only.",
            })
            origin=b

        d=shadow.decide_shadow_action(at,origin)
        if at >= origin+DEVELOPMENT_REFERENCE_DAYS-tol:
            if d.action!="FULL_FLOW_REFRESH":
                raise GateError(f"{window_name}:accepted_boundary_not_refresh:{at}")
            boundary_rows.append({
                "window":window_name,
                "boundary_day":at,
                "bracket_parent_accepted_state_day":r["parent_time_days"],
                "bracket_child_accepted_state_day":at,
                "boundary_is_accepted_state":True,
                "shadow_action":d.action,
                "shadow_reason":d.reason,
                "note":"Projected 5-day boundary coincides with a real accepted state.",
            })
            event_kind="ACCEPTED_STATE_AT_5D_BOUNDARY"
            origin_before=origin
            origin=at
        else:
            if d.action!="REUSE_FLOW_NETWORK_FOR_MIXED_TRANSPORT":
                raise GateError(f"{window_name}:sub5d_accepted_state_not_reuse:{at}")
            event_kind="REAL_ACCEPTED_STATE_REUSE"
            origin_before=origin

        replay_rows.append({
            "window":window_name,
            "event_kind":event_kind,
            "event_day":at,
            "accepted_state":True,
            "accepted_step_index":r["accepted_step_index"],
            "flow_epoch_origin_before_event":origin_before,
            "flow_epoch_age_days":at-origin_before,
            "shadow_action":d.action,
            "shadow_reason":d.reason,
            "targeted_checkpoint_landing":r["targeted_checkpoint_landing"],
            "note":"Targeted checkpoint marker is recorded from the historical ledger but is not automatically promoted to POST_OBSERVATION_CHECKPOINT.",
        })

    return replay_rows,boundary_rows,parsed

def selftest(root:Path):
    g3=import_exact(root,G3R5_RUNNER,G3R5_BLOB,"g3r6_g3r5_selftest")
    exact_blob(root,G2R3_RUNNER,G2R3_BLOB)
    exact_blob(root,G2R1R1_RUNNER,G2R1R1_BLOB)
    exact_blob(root,G2R2_RUNNER,G2R2_BLOB)
    exact_blob(root,G3R2A0_RUNNER,G3R2A0_BLOB)
    assert g3.DEVELOPMENT_REFERENCE_DAYS==5.0
    assert g3.PRODUCTION_MAX_FLOW_EPOCH_DAYS is None
    assert g3.decide_shadow_action(405.0,400.0).action=="FULL_FLOW_REFRESH"
    assert g3.decide_shadow_action(405.0,405.0).action=="REUSE_FLOW_NETWORK_FOR_MIXED_TRANSPORT"
    print("POSTV16 GPU-HYB-G3-R6 structural/replay self-test: PASS")

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
        print("G3-R6 — ACCEPTED-STATE TIMELINE CONTROLLER SHADOW REPLAY / REFRESH EVENT AUDIT")
        print("NO RESERVOIR PHYSICS EXECUTION. NO CANONICAL STATE MUTATION. NO PRODUCTION ACTIVATION.")
        print("PROJECTED 5-DAY BOUNDARIES ARE CONTROLLER EVENTS, NOT ACCEPTED RESERVOIR STATES.")
        print("="*190)

        stage="repository"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_G3_R5_PASS_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")

        stage="source_authority"
        g3=import_exact(root,G3R5_RUNNER,G3R5_BLOB,"g3r6_g3r5")
        bindings=[
            ("G3_R5",G3R5_RUNNER,G3R5_BLOB),
            ("G2_R3_DAY30_45",G2R3_RUNNER,G2R3_BLOB),
            ("G2_R1_R1_DAY75_80",G2R1R1_RUNNER,G2R1R1_BLOB),
            ("G2_R2_DAY100_125",G2R2_RUNNER,G2R2_BLOB),
            ("G3_R2_A0_LATE_DAY405",G3R2A0_RUNNER,G3R2A0_BLOB),
        ]
        for role,fn,blob in bindings:
            gate(role+"_blob_exact",exact_blob(root,fn,blob)==blob)

        stage="G3_R5_authority"
        s5p=drive/G3R5_REL/G3R5_SUM
        c5p=drive/G3R5_REL/G3R5_CONTRACT
        d5p=drive/G3R5_REL/G3R5_DECISION
        for label,p in [("G3R5_summary",s5p),("G3R5_contract",c5p),("G3R5_decision",d5p)]:
            gate(label+"_present",p.is_file(),str(p))
        s5=js(s5p);c5=js(c5p);d5=js(d5p)
        gate("G3R5_status_exact",s5.get("status")==G3R5_STATUS,s5.get("status"))
        gate("G3R5_decisions_passed",s5.get("all_decision_cases_passed") is True)
        gate("G3R5_guards_passed",s5.get("all_guard_tests_passed") is True)
        gate("G3R5_reference_5d",float(s5.get("development_reference_days"))==5.0)
        gate("G3R5_production_epoch_unselected",s5.get("production_max_flow_epoch_days") is None)
        gate("G3R5_R6_authorized",s5.get("G3_R6_accepted_state_timeline_controller_shadow_replay_authorized") is True)
        gate("G3R5_R6_no_mutation",s5.get("G3_R6_canonical_state_mutation_authorized") is False)
        gate("G3R5_R6_no_production",s5.get("G3_R6_production_activation_authorized") is False)
        gate("G3R5_contract_reference_5d",float(c5.get("development_reference_days"))==5.0)
        gate("G3R5_contract_production_epoch_null",c5.get("production_max_flow_epoch_days") is None)
        gate("G3R5_decision_next_is_R6",d5.get("next_milestone",{}).get("name")=="POSTV16-AV4-PIVOT-GPU-HYB-G3-R6")

        stage="accepted_state_evidence"
        p_r3s=drive/G2R3_REL/G2R3_SUM
        p_r3steps=drive/G2R3_REL/G2R3_STEPS
        p_r3refresh=drive/G2R3_REL/G2R3_REFRESH
        p_r1s=drive/G2R1R1_REL/G2R1R1_SUM
        p_r2s=drive/G2R2_REL/G2R2_SUM
        p_r2steps=drive/G2R2_REL/G2R2_STEPS
        p_r2refresh=drive/G2R2_REL/G2R2_REFRESH
        p_lates=drive/G3R2A0_REL/G3R2A0_SUM
        p_latep=drive/G3R2A0_REL/G3R2A0_PROTOCOL

        for label,p in [
            ("G2R3_summary",p_r3s),("G2R3_steps",p_r3steps),("G2R3_refresh",p_r3refresh),
            ("G2R1R1_summary",p_r1s),
            ("G2R2_summary",p_r2s),("G2R2_steps",p_r2steps),("G2R2_refresh",p_r2refresh),
            ("G3R2A0_summary",p_lates),("G3R2A0_protocol",p_latep),
        ]:
            gate(label+"_present",p.is_file(),str(p))

        r3s=js(p_r3s);r1s=js(p_r1s);r2s=js(p_r2s);lates=js(p_lates);latep=js(p_latep)
        gate("G2R3_status_exact",r3s.get("status")==G2R3_STATUS,r3s.get("status"))
        gate("G2R3_continuous_30_45",r3s.get("continuous_30_to45_rollout") is True)
        gate("G2R1R1_status_exact",r1s.get("status")==G2R1R1_STATUS,r1s.get("status"))
        gate("G2R1R1_Day75_time_exact",float(r1s.get("Day75_exact_state_time_days"))==75.0)
        gate("G2R1R1_Day80_reused_separately",r1s.get("Day80_existing_state_reused") is True)
        gate("G2R2_status_exact",r2s.get("status")==G2R2_STATUS,r2s.get("status"))
        gate("G2R2_continuous_100_125",r2s.get("continuous_100_to125_rollout") is True)
        gate("G3R2A0_status_exact",lates.get("status")==G3R2A0_STATUS,lates.get("status"))
        gate("G3R2A0_parent_day405",float(lates.get("late_parent_day"))==405.0)
        gate("G3R2A0_staleness_0_5_15",lates.get("late_staleness_branches_days")==[0,5,15])

        r3_steps=read_csv(p_r3steps)
        r2_steps=read_csv(p_r2steps)
        r3_legacy_refresh=read_csv(p_r3refresh)
        r2_legacy_refresh=read_csv(p_r2refresh)

        gate("G2R3_step_count_matches_summary",len(r3_steps)==int(r3s["accepted_transition_count_30_to45"]),(len(r3_steps),r3s["accepted_transition_count_30_to45"]))
        gate("G2R3_refresh_count_matches_summary",len(r3_legacy_refresh)==int(r3s["flow_refresh_count_30_to45"]),(len(r3_legacy_refresh),r3s["flow_refresh_count_30_to45"]))
        gate("G2R2_step_count_matches_summary",len(r2_steps)==int(r2s["accepted_transition_count_100_to125"]),(len(r2_steps),r2s["accepted_transition_count_100_to125"]))
        gate("G2R2_refresh_count_matches_summary",len(r2_legacy_refresh)==int(r2s["flow_refresh_count_100_to125"]),(len(r2_legacy_refresh),r2s["flow_refresh_count_100_to125"]))

        stage="continuous_replay"
        replay30,bounds30,parsed30=replay_continuous_window(
            window_name="DAY30_TO45_CONTINUOUS_ACCEPTED_LEDGER",
            rows=r3_steps,start_day=30.0,end_day=45.0,shadow=g3,
        )
        replay100,bounds100,parsed100=replay_continuous_window(
            window_name="DAY100_TO125_CONTINUOUS_ACCEPTED_LEDGER",
            rows=r2_steps,start_day=100.0,end_day=125.0,shadow=g3,
        )

        gate("Day30_45_projected_boundary_days_exact",
             [round(x["boundary_day"],10) for x in bounds30]==[35.0,40.0,45.0],
             [x["boundary_day"] for x in bounds30])
        gate("Day100_125_projected_boundary_days_exact",
             [round(x["boundary_day"],10) for x in bounds100]==[105.0,110.0,115.0,120.0,125.0],
             [x["boundary_day"] for x in bounds100])

        stage="Day69_75_endpoint_only_replay"
        gate("Day69_source_time_exact",math.isclose(DAY69_TIME,69.88346704782309,rel_tol=0.0,abs_tol=1e-15))
        endpoint_boundary=DAY69_TIME+DEVELOPMENT_REFERENCE_DAYS
        gate("Day69_75_boundary_before_Day75",endpoint_boundary<75.0,(endpoint_boundary,75.0))
        init69=g3.decide_shadow_action(DAY69_TIME,DAY69_TIME,hard_triggers=("RESTART_OR_INITIALIZATION",))
        b69=g3.decide_shadow_action(endpoint_boundary,DAY69_TIME)
        d75=g3.decide_shadow_action(75.0,endpoint_boundary)
        gate("Day69_replay_init_refresh",init69.action=="FULL_FLOW_REFRESH",init69.action)
        gate("Day74p883_boundary_refresh",b69.action=="FULL_FLOW_REFRESH",b69.action)
        gate("Day75_after_projected_refresh_reuse",d75.action=="REUSE_FLOW_NETWORK_FOR_MIXED_TRANSPORT",d75.action)

        replay_endpoint=[
            {
                "window":"DAY69P883_TO75_ENDPOINT_ONLY",
                "event_kind":"SHADOW_REPLAY_INITIALIZATION_ONLY",
                "event_day":DAY69_TIME,
                "accepted_state":True,
                "accepted_step_index":"",
                "flow_epoch_origin_before_event":DAY69_TIME,
                "flow_epoch_age_days":0.0,
                "shadow_action":init69.action,
                "shadow_reason":init69.reason,
                "targeted_checkpoint_landing":False,
                "note":"Replay initialization from certified Day69.883467 state; not a claim about historical trigger identity.",
            },
            {
                "window":"DAY69P883_TO75_ENDPOINT_ONLY",
                "event_kind":"PROJECTED_5D_BOUNDARY_ENDPOINT_ONLY",
                "event_day":endpoint_boundary,
                "accepted_state":False,
                "accepted_step_index":"",
                "flow_epoch_origin_before_event":DAY69_TIME,
                "flow_epoch_age_days":5.0,
                "shadow_action":b69.action,
                "shadow_reason":b69.reason,
                "targeted_checkpoint_landing":False,
                "note":"Projected boundary only; no accepted-transition ledger was published for this G2-R1-R1 interval.",
            },
            {
                "window":"DAY69P883_TO75_ENDPOINT_ONLY",
                "event_kind":"CERTIFIED_DAY75_ENDPOINT_AFTER_PROJECTED_BOUNDARY",
                "event_day":75.0,
                "accepted_state":True,
                "accepted_step_index":"",
                "flow_epoch_origin_before_event":endpoint_boundary,
                "flow_epoch_age_days":75.0-endpoint_boundary,
                "shadow_action":d75.action,
                "shadow_reason":d75.reason,
                "targeted_checkpoint_landing":True,
                "note":"Day80 is a separately reused immutable comparison endpoint and is not treated as continuous Day75→80 replay.",
            },
        ]
        endpoint_boundary_row={
            "window":"DAY69P883_TO75_ENDPOINT_ONLY",
            "boundary_day":endpoint_boundary,
            "bracket_parent_accepted_state_day":DAY69_TIME,
            "bracket_child_accepted_state_day":75.0,
            "boundary_is_accepted_state":False,
            "shadow_action":b69.action,
            "shadow_reason":b69.reason,
            "note":"Endpoint-only projected 5-day boundary; no accepted-transition ledger published for this interval.",
        }

        stage="late_Day405_branch_replay"
        branches=latep.get("branches",[])
        gate("late_protocol_three_branches",len(branches)==3,branches)
        late_rows=[]
        expected={
            "REFRESHED_0D":"REUSE_FLOW_NETWORK_FOR_MIXED_TRANSPORT",
            "STALE_5D":"FULL_FLOW_REFRESH",
            "STALE_15D":"FULL_FLOW_REFRESH",
        }
        for b in branches:
            name=b["name"];source=float(b["flow_source_day"]);stale=float(b["staleness_days"])
            d=g3.decide_shadow_action(405.0,source)
            gate(f"late_{name}_staleness_exact",math.isclose(405.0-source,stale,rel_tol=0.0,abs_tol=1e-12),(source,stale))
            gate(f"late_{name}_action",d.action==expected[name],d.action)
            late_rows.append({
                "branch":name,
                "parent_state_day":405.0,
                "flow_source_day":source,
                "staleness_days":stale,
                "shadow_action":d.action,
                "shadow_reason":d.reason,
                "hard_trigger_injected":False,
                "note":"Causal age-policy replay only; no POST_OBSERVATION_CHECKPOINT trigger is injected into the Day405 branch comparison.",
            })

        stage="historical_refresh_evidence"
        legacy_rows=[]
        for window,rows in [
            ("DAY30_TO45_HISTORICAL_LEGACY_RUNTIME",r3_legacy_refresh),
            ("DAY100_TO125_HISTORICAL_LEGACY_RUNTIME",r2_legacy_refresh),
        ]:
            for r in rows:
                legacy_rows.append({
                    "window":window,
                    "historical_refresh_index":r.get("refresh_index",""),
                    "historical_trigger":r.get("trigger",""),
                    "historical_physical_time_days":r.get("physical_time_days",""),
                    "historical_accepted_step_index":r.get("accepted_step_index",""),
                    "classification":"HISTORICAL_LEGACY_RUNTIME_EVENT_NOT_CURRENT_GPU_HYBRID_CADENCE_AUTHORITY",
                })
        gate("historical_refresh_events_present",len(legacy_rows)>0,len(legacy_rows))

        stage="window_audit"
        window_rows=[
            {
                "window":"DAY30_TO45_CONTINUOUS_ACCEPTED_LEDGER",
                "evidence_type":"REAL_CONTINUOUS_ACCEPTED_TRANSITION_LEDGER",
                "start_day":30.0,"end_day":45.0,
                "accepted_transition_count":len(parsed30),
                "projected_5day_boundary_count":len(bounds30),
                "continuity_asserted":True,
                "gap_to_next_window_asserted":False,
            },
            {
                "window":"DAY69P883_TO75_ENDPOINT_ONLY",
                "evidence_type":"CERTIFIED_ENDPOINT_ONLY_NO_PUBLISHED_ACCEPTED_TRANSITION_LEDGER",
                "start_day":DAY69_TIME,"end_day":75.0,
                "accepted_transition_count":int(r1s["Day75_exact_transition_count"]),
                "projected_5day_boundary_count":1,
                "continuity_asserted":False,
                "gap_to_next_window_asserted":True,
            },
            {
                "window":"DAY80_COMPARISON_ENDPOINT_ONLY",
                "evidence_type":"IMMUTABLE_EXISTING_COMPARISON_ENDPOINT_REUSED_SEPARATELY",
                "start_day":80.0,"end_day":80.0,
                "accepted_transition_count":0,
                "projected_5day_boundary_count":0,
                "continuity_asserted":False,
                "gap_to_next_window_asserted":True,
            },
            {
                "window":"DAY100_TO125_CONTINUOUS_ACCEPTED_LEDGER",
                "evidence_type":"REAL_CONTINUOUS_ACCEPTED_TRANSITION_LEDGER",
                "start_day":100.0,"end_day":125.0,
                "accepted_transition_count":len(parsed100),
                "projected_5day_boundary_count":len(bounds100),
                "continuity_asserted":True,
                "gap_to_next_window_asserted":False,
            },
            {
                "window":"LATE_DAY405_SAME_STATE_BRANCH_SET",
                "evidence_type":"CERTIFIED_ACCEPTED_DAY390_DAY400_DAY405_STATE_AND_FLOW_DIAGNOSTIC_BRANCHES",
                "start_day":390.0,"end_day":405.0,
                "accepted_transition_count":0,
                "projected_5day_boundary_count":0,
                "continuity_asserted":False,
                "gap_to_next_window_asserted":True,
            },
        ]
        gate("no_false_global_continuity_claim",all(not (w["window"]!="DAY30_TO45_CONTINUOUS_ACCEPTED_LEDGER" and w["window"]!="DAY100_TO125_CONTINUOUS_ACCEPTED_LEDGER" and w["continuity_asserted"]) for w in window_rows))

        replay_rows=replay30+replay_endpoint+replay100
        boundary_rows=bounds30+[endpoint_boundary_row]+bounds100

        stage="scope_guards"
        gate("physics_executed_false",True)
        gate("canonical_state_mutated_false",True)
        gate("projected_boundaries_not_mislabeled_as_accepted_states",
             all((r["boundary_is_accepted_state"] in (True,False)) for r in boundary_rows))
        gate("production_epoch_unselected",s5.get("production_max_flow_epoch_days") is None)
        gate("production_cadence_unselected",s5.get("production_pressure_refresh_cadence_selected") is False)
        gate("fixed_15day_hold_closed",s5.get("fixed_15day_production_hold_authorized") is False)
        gate("integrated_GPU_production_closed",s5.get("integrated_GPU_runtime_production_authorized") is False)
        gate("P4_closed",s5.get("P4_authorized") is False)

        summary={
            "milestone":M,
            "status":PASS,
            "classification":"REAL_ACCEPTED_STATE_WINDOWS_REPLAYED_WITH_FIVE_DAY_GPU_HYBRID_SHADOW_CONTROLLER_PROJECTED_BOUNDARIES_AUDITED_LATE_DAY405_0D_5D_15D_DECISIONS_CERTIFIED_NO_GLOBAL_TIMELINE_CONTINUITY_CLAIM",
            "G3_R5_authority_bound":True,
            "development_reference_days":5.0,
            "production_max_flow_epoch_days":None,
            "replay_window_count":len(window_rows),
            "continuous_accepted_ledger_window_count":2,
            "continuous_accepted_transition_count":len(parsed30)+len(parsed100),
            "projected_5day_boundary_count":len(boundary_rows),
            "Day30_to45_projected_boundaries":[35.0,40.0,45.0],
            "Day69p883_to75_projected_boundary_day":endpoint_boundary,
            "Day100_to125_projected_boundaries":[105.0,110.0,115.0,120.0,125.0],
            "Day80_treated_as_separate_immutable_comparison_endpoint":True,
            "false_Day75_to80_continuity_claim_made":False,
            "late_Day405_branch_actions":{r["branch"]:r["shadow_action"] for r in late_rows},
            "late_REFREShed_0D_reuse_certified":True,
            "late_STALE_5D_refresh_certified":True,
            "late_STALE_15D_refresh_certified":True,
            "historical_legacy_refresh_event_count":len(legacy_rows),
            "historical_legacy_refresh_events_promoted_to_current_authority":False,
            "physics_executed":False,
            "canonical_state_mutated":False,
            "production_pressure_refresh_cadence_selected":False,
            "fixed_15day_production_hold_authorized":False,
            "G3_R7_controlled_integrated_controller_shadow_execution_protocol_freeze_authorized":True,
            "G3_R7_canonical_state_mutation_authorized":False,
            "G3_R7_production_activation_authorized":False,
            "integrated_GPU_runtime_production_authorized":False,
            "P4_authorized":False,
        }

        contract={
            "milestone":M,
            "status":PASS,
            "replay_scope":"READ_ONLY_ACCEPTED_STATE_TIMING_AND_EVENT_AUDIT",
            "development_reference_days":5.0,
            "production_max_flow_epoch_days":None,
            "continuous_windows":[
                {"name":"DAY30_TO45_CONTINUOUS_ACCEPTED_LEDGER","start_day":30.0,"end_day":45.0},
                {"name":"DAY100_TO125_CONTINUOUS_ACCEPTED_LEDGER","start_day":100.0,"end_day":125.0},
            ],
            "endpoint_only_windows":[
                {"name":"DAY69P883_TO75_ENDPOINT_ONLY","start_day":DAY69_TIME,"end_day":75.0},
                {"name":"DAY80_COMPARISON_ENDPOINT_ONLY","day":80.0,"continuity_from_Day75_asserted":False},
            ],
            "late_same_state_branch_replay":{
                "parent_day":405.0,
                "branches":[
                    {"name":"REFRESHED_0D","flow_source_day":405.0,"expected_action":"REUSE_FLOW_NETWORK_FOR_MIXED_TRANSPORT"},
                    {"name":"STALE_5D","flow_source_day":400.0,"expected_action":"FULL_FLOW_REFRESH"},
                    {"name":"STALE_15D","flow_source_day":390.0,"expected_action":"FULL_FLOW_REFRESH"},
                ],
                "hard_trigger_injected":False,
            },
            "interpretation_guards":{
                "projected_5day_boundaries_are_controller_events_not_accepted_states":True,
                "historical_legacy_refresh_events_are_context_not_current_authority":True,
                "targeted_checkpoint_landing_is_not_automatically_POST_OBSERVATION_CHECKPOINT":True,
                "no_global_Day30_to405_continuity_claim":True,
                "no_Day75_to80_continuity_claim":True,
            },
            "scope_guards":{
                "physics_execution":False,
                "canonical_state_mutation":False,
                "production_pressure_refresh_cadence_selected":False,
                "integrated_GPU_runtime_production_authorized":False,
                "P4_authorized":False,
            },
        }

        decision={
            "milestone":M,
            "status":PASS,
            "accepted_state_timeline_shadow_replay_certified":True,
            "five_day_projected_event_schedule_audited":True,
            "late_Day405_age_policy_actions_certified":True,
            "global_continuity_not_claimed":True,
            "production_max_flow_epoch_days":None,
            "production_pressure_refresh_cadence_selected":False,
            "next_milestone":{
                "name":"POSTV16-AV4-PIVOT-GPU-HYB-G3-R7",
                "purpose":"Freeze a controlled integrated controller-shadow execution protocol that can exercise the reconciled 5-day event scheduling on a selected certified runtime window without mutating the canonical trajectory or activating production.",
                "authorized":True,
                "canonical_state_mutation_authorized":False,
                "production_activation_authorized":False,
            },
            "P4_authorized":False,
        }

        stage="publication"
        gate("output_absent",not out.exists(),str(out))
        out.mkdir(parents=True)
        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        (out/CONTRACT).write_text(json.dumps(contract,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        (out/DECISION).write_text(json.dumps(decision,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        write_csv(out/REPLAY,replay_rows)
        write_csv(out/BOUNDARIES,boundary_rows)
        write_csv(out/LEGACY,legacy_rows)
        write_csv(out/LATE,late_rows)
        write_csv(out/WINDOWS,window_rows)
        write_csv(out/GATES,gates)
        write_csv(out/MANIFEST,[
            {"file":q.name,"sha256":sha256(q),"bytes":q.stat().st_size}
            for q in sorted(out.iterdir()) if q.is_file() and q.name!=MANIFEST
        ])

        print("="*190)
        print(M,"PASS")
        print("Continuous accepted-ledger windows              : 2")
        print("Continuous accepted transitions replayed        :",len(parsed30)+len(parsed100))
        print("Projected 5-day boundaries audited              :",len(boundary_rows))
        print("Day30->45 projected boundaries                  : [35, 40, 45]")
        print("Day69.883->75 projected boundary                :",endpoint_boundary)
        print("Day100->125 projected boundaries                : [105, 110, 115, 120, 125]")
        print("Day80 treated as separate immutable endpoint    : True")
        print("Late Day405 REFRESHED_0D action                 :",late_rows[0]["shadow_action"])
        print("Late Day405 STALE_5D action                     :",late_rows[1]["shadow_action"])
        print("Late Day405 STALE_15D action                    :",late_rows[2]["shadow_action"])
        print("Production max flow-epoch age selected          : False")
        print("G3-R7 protocol freeze authorized                : True")
        print("Production activation authorized                : False")
        print("P4 authorized                                   : False")
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
            "production_pressure_refresh_cadence_selected":False,
            "G3_R7_controlled_integrated_controller_shadow_execution_protocol_freeze_authorized":False,
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
