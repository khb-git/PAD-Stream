#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

M="POSTV16-AV4-PIVOT-GPU-HYB-G3-R5"
PASS="POSTV16AV4PIVOTGPUHYBG3R5_RECONCILED_RUNTIME_CONTROLLER_SHADOW_IMPLEMENTATION_AND_DECISION_MATRIX_PASS_NO_PHYSICS_EXECUTION"
BLOCK="POSTV16AV4PIVOTGPUHYBG3R5_TECHNICAL_OR_AUTHORITY_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="f262b6f66124aafbd1a627cb6ab3ed213bd71f16"

R4_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R4_Integrated_Runtime_Controller_Policy_Reconciliation_Design_Freeze.py"
R4_BLOB="e63e62e8d0baa52ac28b3c4593310978f9d5eafc"
CTRL_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_Integrated_Runtime_Controller_R2.py"
CTRL_BLOB="2d1c4fd3b792c9c19bef268b74956574bcaaf540"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

R4_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G3_R4_Integrated_Runtime_Controller_Policy_Reconciliation_Design_Freeze"
R4_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R4_Summary.json"
R4_CONTRACT="POSTV16_AV4_PIVOT_GPU_HYB_G3_R4_Reconciliation_Contract.json"
R4_DECISION="POSTV16_AV4_PIVOT_GPU_HYB_G3_R4_Decision_Contract.json"
R4_STATUS="POSTV16AV4PIVOTGPUHYBG3R4_INTEGRATED_RUNTIME_CONTROLLER_POLICY_RECONCILIATION_DESIGN_FREEZE_PASS_NO_PHYSICS_EXECUTION"

DEVELOPMENT_REFERENCE_DAYS=5.0
LEGACY_E41_EPOCH_DAYS=4.9417335239115445
PRODUCTION_MAX_FLOW_EPOCH_DAYS=None
AUTHORITY_SCOPE="DEVELOPMENT_SHADOW_ONLY_NOT_PRODUCTION"

HARD_REFRESH_TRIGGERS=(
    "RESTART_OR_INITIALIZATION",
    "WELL_OR_CONTROL_CHANGE",
    "POST_OBSERVATION_CHECKPOINT",
    "CAPACITY_PREFLIGHT_REJECTION",
)

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

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G3_R5"
OUT_REL=BASE/(OUT_TOKEN+"_Reconciled_Runtime_Controller_Shadow_Implementation_and_Test")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
CONTRACT=f"{OUT_TOKEN}_Shadow_Controller_Contract.json"
DECISION=f"{OUT_TOKEN}_Decision_Contract.json"
MATRIX=f"{OUT_TOKEN}_Decision_Test_Matrix.csv"
GUARDS=f"{OUT_TOKEN}_Guard_Test_Matrix.csv"
GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"

class GateError(RuntimeError):
    pass

@dataclass(frozen=True)
class ShadowDecision:
    action: str
    reason: str
    flow_epoch_age_days: float
    development_reference_days: float
    authority_scope: str
    production_max_flow_epoch_days: None
    active_hard_triggers: tuple[str,...]
    required_sequence: tuple[str,...]

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

def decide_shadow_action(
    current_time_days:float,
    flow_epoch_origin_day:float,
    *,
    hard_triggers:Iterable[str]=(),
)->ShadowDecision:
    age=float(current_time_days)-float(flow_epoch_origin_day)
    if age < -1.0e-12:
        raise ValueError("flow_epoch_origin_after_current_time")

    active=tuple(str(x) for x in hard_triggers)
    unknown=[x for x in active if x not in HARD_REFRESH_TRIGGERS]
    if unknown:
        raise ValueError(f"unknown_hard_refresh_trigger:{unknown}")

    if active:
        return ShadowDecision(
            action="FULL_FLOW_REFRESH",
            reason="HARD_TRIGGER:"+",".join(active),
            flow_epoch_age_days=age,
            development_reference_days=DEVELOPMENT_REFERENCE_DAYS,
            authority_scope=AUTHORITY_SCOPE,
            production_max_flow_epoch_days=None,
            active_hard_triggers=active,
            required_sequence=REFRESH_SEQUENCE,
        )

    if age >= DEVELOPMENT_REFERENCE_DAYS - 1.0e-12:
        return ShadowDecision(
            action="FULL_FLOW_REFRESH",
            reason="DEVELOPMENT_FLOW_EPOCH_AGE_REFERENCE_REACHED",
            flow_epoch_age_days=age,
            development_reference_days=DEVELOPMENT_REFERENCE_DAYS,
            authority_scope=AUTHORITY_SCOPE,
            production_max_flow_epoch_days=None,
            active_hard_triggers=(),
            required_sequence=REFRESH_SEQUENCE,
        )

    return ShadowDecision(
        action="REUSE_FLOW_NETWORK_FOR_MIXED_TRANSPORT",
        reason="FLOW_EPOCH_FRESH",
        flow_epoch_age_days=age,
        development_reference_days=DEVELOPMENT_REFERENCE_DAYS,
        authority_scope=AUTHORITY_SCOPE,
        production_max_flow_epoch_days=None,
        active_hard_triggers=(),
        required_sequence=TRANSPORT_REUSE_SEQUENCE,
    )

def selftest(root:Path):
    exact_blob(root,R4_RUNNER,R4_BLOB)
    ctrl=import_exact(root,CTRL_RUNNER,CTRL_BLOB,"g3r5_ctrl_selftest")
    assert float(ctrl.DEVELOPMENT_FLOW_REFRESH_REFERENCE_DAYS)==DEVELOPMENT_REFERENCE_DAYS
    assert abs(float(ctrl.PRODUCTION_MAX_FLOW_EPOCH_DAYS)-LEGACY_E41_EPOCH_DAYS)<=1e-15
    assert tuple(ctrl.HARD_REFRESH_TRIGGERS)==HARD_REFRESH_TRIGGERS
    assert tuple(ctrl.production_refresh_sequence())==REFRESH_SEQUENCE
    assert tuple(ctrl.transport_reuse_sequence())==TRANSPORT_REUSE_SEQUENCE

    assert decide_shadow_action(104.0,100.0).action=="REUSE_FLOW_NETWORK_FOR_MIXED_TRANSPORT"
    assert decide_shadow_action(105.0,100.0).action=="FULL_FLOW_REFRESH"
    assert decide_shadow_action(101.0,100.0,hard_triggers=("WELL_OR_CONTROL_CHANGE",)).action=="FULL_FLOW_REFRESH"
    assert decide_shadow_action(100.0+LEGACY_E41_EPOCH_DAYS,100.0).action=="REUSE_FLOW_NETWORK_FOR_MIXED_TRANSPORT"
    print("POSTV16 GPU-HYB-G3-R5 structural/shadow-controller self-test: PASS")

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
        print("G3-R5 — RECONCILED RUNTIME CONTROLLER SHADOW IMPLEMENTATION / TEST")
        print("NO RESERVOIR PHYSICS EXECUTION. NO CANONICAL STATE MUTATION. NO PRODUCTION ACTIVATION.")
        print("DEVELOPMENT/SHADOW REFERENCE = 5.0 DAYS. PRODUCTION MAX FLOW-EPOCH AGE = UNSELECTED.")
        print("="*190)

        stage="repository"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_G3_R4_PASS_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")

        stage="source_authority"
        gate("G3_R4_runner_blob_exact",exact_blob(root,R4_RUNNER,R4_BLOB)==R4_BLOB)
        ctrl=import_exact(root,CTRL_RUNNER,CTRL_BLOB,"g3r5_ctrl")
        gate("existing_controller_runner_blob_exact",exact_blob(root,CTRL_RUNNER,CTRL_BLOB)==CTRL_BLOB)
        gate("existing_controller_development_reference_5d",float(ctrl.DEVELOPMENT_FLOW_REFRESH_REFERENCE_DAYS)==DEVELOPMENT_REFERENCE_DAYS,ctrl.DEVELOPMENT_FLOW_REFRESH_REFERENCE_DAYS)
        gate("existing_controller_legacy_default_exact",abs(float(ctrl.PRODUCTION_MAX_FLOW_EPOCH_DAYS)-LEGACY_E41_EPOCH_DAYS)<=1e-15,ctrl.PRODUCTION_MAX_FLOW_EPOCH_DAYS)
        gate("existing_controller_hard_triggers_exact",tuple(ctrl.HARD_REFRESH_TRIGGERS)==HARD_REFRESH_TRIGGERS,ctrl.HARD_REFRESH_TRIGGERS)
        gate("existing_controller_refresh_sequence_exact",tuple(ctrl.production_refresh_sequence())==REFRESH_SEQUENCE,ctrl.production_refresh_sequence())
        gate("existing_controller_reuse_sequence_exact",tuple(ctrl.transport_reuse_sequence())==TRANSPORT_REUSE_SEQUENCE,ctrl.transport_reuse_sequence())

        stage="G3_R4_authority"
        r4s_path=drive/R4_REL/R4_SUM
        r4c_path=drive/R4_REL/R4_CONTRACT
        r4d_path=drive/R4_REL/R4_DECISION
        for label,p in [("R4_summary",r4s_path),("R4_contract",r4c_path),("R4_decision",r4d_path)]:
            gate(label+"_present",p.is_file(),str(p))
        r4s=js(r4s_path)
        r4c=js(r4c_path)
        r4d=js(r4d_path)

        gate("R4_status_exact",r4s.get("status")==R4_STATUS,r4s.get("status"))
        gate("R4_development_reference_5d",float(r4s.get("development_flow_refresh_reference_days"))==DEVELOPMENT_REFERENCE_DAYS)
        gate("R4_legacy_epoch_exact",abs(float(r4s.get("legacy_E41_max_flow_epoch_days"))-LEGACY_E41_EPOCH_DAYS)<=1e-15)
        gate("R4_legacy_epoch_not_current_authority",r4s.get("legacy_E41_max_flow_epoch_current_GPU_Hybrid_production_authority") is False)
        gate("R4_current_production_epoch_unselected",r4s.get("current_GPU_Hybrid_production_max_flow_epoch_days") is None)
        gate("R4_15day_fixed_hold_closed",r4s.get("fixed_15day_production_hold_authorized") is False)
        gate("R4_shadow_implementation_authorized",r4s.get("G3_R5_reconciled_controller_shadow_implementation_authorized") is True)
        gate("R4_decision_shadow_implementation_authorized",r4d.get("G3_R5_reconciled_controller_shadow_implementation_authorized") is True)
        gate("R4_decision_no_state_mutation",r4d.get("G3_R5_canonical_state_mutation_authorized") is False)
        gate("R4_decision_no_production_activation",r4d.get("G3_R5_production_activation_authorized") is False)

        rc_policy=r4c["reconciled_controller_policy"]
        gate("R4_contract_reference_5d",float(rc_policy["development_reference_days"])==DEVELOPMENT_REFERENCE_DAYS)
        gate("R4_contract_production_epoch_null",rc_policy["current_GPU_Hybrid_production_max_flow_epoch_days"] is None)
        gate("R4_contract_hard_triggers_exact",tuple(rc_policy["hard_refresh_triggers"])==HARD_REFRESH_TRIGGERS)
        gate("R4_contract_refresh_sequence_exact",tuple(rc_policy["refresh_sequence"])==REFRESH_SEQUENCE)
        gate("R4_contract_15day_closed",rc_policy["fixed_15day_production_hold_authorized"] is False)

        stage="decision_matrix"
        origin=100.0
        cases=[
            ("AGE_0_REUSE",0.0,(),"REUSE_FLOW_NETWORK_FOR_MIXED_TRANSPORT","FLOW_EPOCH_FRESH"),
            ("AGE_1_REUSE",1.0,(),"REUSE_FLOW_NETWORK_FOR_MIXED_TRANSPORT","FLOW_EPOCH_FRESH"),
            ("LEGACY_4P9417_BOUNDARY_REUSE",LEGACY_E41_EPOCH_DAYS,(),"REUSE_FLOW_NETWORK_FOR_MIXED_TRANSPORT","FLOW_EPOCH_FRESH"),
            ("JUST_BELOW_5D_REUSE",4.999999,(),"REUSE_FLOW_NETWORK_FOR_MIXED_TRANSPORT","FLOW_EPOCH_FRESH"),
            ("EXACT_5D_REFRESH",5.0,(),"FULL_FLOW_REFRESH","DEVELOPMENT_FLOW_EPOCH_AGE_REFERENCE_REACHED"),
            ("ABOVE_5D_REFRESH",5.000001,(),"FULL_FLOW_REFRESH","DEVELOPMENT_FLOW_EPOCH_AGE_REFERENCE_REACHED"),
        ]
        for trig in HARD_REFRESH_TRIGGERS:
            cases.append((f"HARD_{trig}",1.0,(trig,),"FULL_FLOW_REFRESH","HARD_TRIGGER:"+trig))
        cases.append(("ALL_HARD_TRIGGERS",1.0,HARD_REFRESH_TRIGGERS,"FULL_FLOW_REFRESH","HARD_TRIGGER:"+",".join(HARD_REFRESH_TRIGGERS)))

        rows=[]
        for name,age,triggers,expected_action,expected_reason in cases:
            shadow=decide_shadow_action(origin+age,origin,hard_triggers=triggers)
            legacy_explicit=ctrl.decide_runtime_action(
                origin+age,
                origin,
                hard_triggers=triggers,
                refresh_reference_days=DEVELOPMENT_REFERENCE_DAYS,
            )
            gate(name+"_shadow_action",shadow.action==expected_action,shadow.action)
            gate(name+"_shadow_reason",shadow.reason==expected_reason,shadow.reason)
            gate(name+"_explicit_controller_crosscheck_action",legacy_explicit.action==shadow.action,legacy_explicit.action)
            gate(name+"_explicit_controller_crosscheck_reason",legacy_explicit.reason==shadow.reason,legacy_explicit.reason)
            gate(name+"_production_epoch_null",shadow.production_max_flow_epoch_days is None)
            gate(name+"_authority_scope_shadow_only",shadow.authority_scope==AUTHORITY_SCOPE)
            if shadow.action=="FULL_FLOW_REFRESH":
                gate(name+"_refresh_sequence_exact",tuple(shadow.required_sequence)==REFRESH_SEQUENCE)
            else:
                gate(name+"_reuse_sequence_exact",tuple(shadow.required_sequence)==TRANSPORT_REUSE_SEQUENCE)
            rows.append({
                "case":name,
                "origin_day":origin,
                "current_day":origin+age,
                "flow_epoch_age_days":age,
                "hard_triggers":"|".join(triggers),
                "expected_action":expected_action,
                "shadow_action":shadow.action,
                "shadow_reason":shadow.reason,
                "explicit_existing_controller_5d_action":legacy_explicit.action,
                "explicit_existing_controller_5d_reason":legacy_explicit.reason,
                "production_max_flow_epoch_days":"",
                "authority_scope":shadow.authority_scope,
                "pass":True,
            })

        legacy_default=ctrl.decide_runtime_action(
            origin+LEGACY_E41_EPOCH_DAYS,
            origin,
        )
        reconciled_at_legacy=decide_shadow_action(
            origin+LEGACY_E41_EPOCH_DAYS,
            origin,
        )
        gate("legacy_default_refreshes_at_legacy_boundary",legacy_default.action=="FULL_FLOW_REFRESH",legacy_default.action)
        gate("reconciled_shadow_reuses_at_legacy_boundary",reconciled_at_legacy.action=="REUSE_FLOW_NETWORK_FOR_MIXED_TRANSPORT",reconciled_at_legacy.action)
        gate("legacy_default_explicitly_decoupled",legacy_default.action!=reconciled_at_legacy.action,{
            "legacy_default":legacy_default.action,
            "reconciled_shadow":reconciled_at_legacy.action,
        })

        stage="guard_tests"
        guard_rows=[]
        try:
            decide_shadow_action(99.0,100.0)
            neg_ok=False
            neg_msg="no_error"
        except ValueError as exc:
            neg_ok=str(exc)=="flow_epoch_origin_after_current_time"
            neg_msg=str(exc)
        gate("negative_age_rejected",neg_ok,neg_msg)
        guard_rows.append({"guard":"negative_age","pass":neg_ok,"detail":neg_msg})

        try:
            decide_shadow_action(101.0,100.0,hard_triggers=("UNKNOWN_TRIGGER",))
            unk_ok=False
            unk_msg="no_error"
        except ValueError as exc:
            unk_ok=str(exc).startswith("unknown_hard_refresh_trigger:")
            unk_msg=str(exc)
        gate("unknown_hard_trigger_rejected",unk_ok,unk_msg)
        guard_rows.append({"guard":"unknown_hard_trigger","pass":unk_ok,"detail":unk_msg})

        stage="scope_guards"
        gate("no_reservoir_physics_executed",True)
        gate("canonical_state_not_mutated",True)
        gate("existing_controller_source_not_mutated",True)
        gate("production_max_flow_epoch_unselected",PRODUCTION_MAX_FLOW_EPOCH_DAYS is None)
        gate("fixed_15day_production_hold_not_authorized",True)
        gate("production_pressure_refresh_cadence_not_selected",True)
        gate("integrated_GPU_runtime_production_not_authorized",True)
        gate("P4_not_authorized",True)

        contract={
            "milestone":M,
            "status":PASS,
            "controller_type":"RECONCILED_GPU_HYBRID_DEVELOPMENT_SHADOW_CONTROLLER",
            "authority_scope":AUTHORITY_SCOPE,
            "development_reference_days":DEVELOPMENT_REFERENCE_DAYS,
            "production_max_flow_epoch_days":None,
            "legacy_E41_epoch_days":LEGACY_E41_EPOCH_DAYS,
            "legacy_E41_epoch_used_as_current_trigger":False,
            "hard_refresh_triggers":list(HARD_REFRESH_TRIGGERS),
            "hard_triggers_override_age_reference":True,
            "age_policy":{
                "age_less_than_5d":"REUSE_FLOW_NETWORK_FOR_MIXED_TRANSPORT",
                "age_at_or_above_5d":"FULL_FLOW_REFRESH",
                "legacy_4p9417335239115445d_boundary":"REUSE_FLOW_NETWORK_FOR_MIXED_TRANSPORT",
            },
            "refresh_sequence":list(REFRESH_SEQUENCE),
            "transport_reuse_sequence":list(TRANSPORT_REUSE_SEQUENCE),
            "implementation":{
                "existing_G4_controller_source_mutated":False,
                "shadow_layer_is_separate":True,
                "existing_controller_crosscheck_uses_explicit_5d_reference":True,
                "existing_controller_default_is_not_current_GPU_Hybrid_authority":True,
            },
            "scope_guards":{
                "reservoir_physics_execution":False,
                "canonical_simulation_state_mutation":False,
                "production_pressure_refresh_cadence_selected":False,
                "integrated_GPU_runtime_production_authorized":False,
                "P4_authorized":False,
            },
        }

        summary={
            "milestone":M,
            "status":PASS,
            "classification":"FIVE_DAY_GPU_HYBRID_DEVELOPMENT_SHADOW_CONTROLLER_IMPLEMENTED_AND_CROSSCHECKED_LEGACY_E41_DEFAULT_EXPLICITLY_DECOUPLED_NO_PRODUCTION_ACTIVATION",
            "G3_R4_authority_bound":True,
            "existing_G4_controller_R2_authority_bound":True,
            "development_reference_days":DEVELOPMENT_REFERENCE_DAYS,
            "legacy_E41_epoch_days":LEGACY_E41_EPOCH_DAYS,
            "legacy_E41_default_decoupled_from_current_shadow_authority":True,
            "legacy_E41_epoch_current_GPU_Hybrid_production_authority":False,
            "production_max_flow_epoch_days":None,
            "decision_case_count":len(cases),
            "all_decision_cases_passed":True,
            "guard_test_count":len(guard_rows),
            "all_guard_tests_passed":all(bool(x["pass"]) for x in guard_rows),
            "hard_refresh_triggers":list(HARD_REFRESH_TRIGGERS),
            "refresh_sequence_exact":True,
            "transport_reuse_sequence_exact":True,
            "existing_controller_explicit_5d_crosscheck_passed":True,
            "physics_executed":False,
            "canonical_state_mutated":False,
            "existing_controller_source_mutated":False,
            "fixed_15day_production_hold_authorized":False,
            "production_pressure_refresh_cadence_selected":False,
            "G3_R6_accepted_state_timeline_controller_shadow_replay_authorized":True,
            "G3_R6_canonical_state_mutation_authorized":False,
            "G3_R6_production_activation_authorized":False,
            "integrated_GPU_runtime_production_authorized":False,
            "P4_authorized":False,
        }

        decision={
            "milestone":M,
            "status":PASS,
            "reconciled_shadow_controller_implementation_certified":True,
            "five_day_development_reference_implementation_certified":True,
            "legacy_default_decoupling_certified":True,
            "all_hard_trigger_decisions_certified":True,
            "production_max_flow_epoch_days":None,
            "production_pressure_refresh_cadence_selected":False,
            "next_milestone":{
                "name":"POSTV16-AV4-PIVOT-GPU-HYB-G3-R6",
                "purpose":"Replay the reconciled shadow controller against real accepted-state timing/event evidence and audit the refresh/reuse event schedule without mutating the canonical trajectory.",
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
        write_csv(out/MATRIX,rows)
        write_csv(out/GUARDS,guard_rows)
        write_csv(out/GATES,gates)
        write_csv(out/MANIFEST,[
            {"file":q.name,"sha256":sha256(q),"bytes":q.stat().st_size}
            for q in sorted(out.iterdir()) if q.is_file() and q.name!=MANIFEST
        ])

        print("="*190)
        print(M,"PASS")
        print("Development/shadow reference                    : 5.0 d")
        print("Legacy E41 boundary                             :",LEGACY_E41_EPOCH_DAYS,"d")
        print("At legacy boundary — reconciled shadow action   :",reconciled_at_legacy.action)
        print("At legacy boundary — legacy default action      :",legacy_default.action)
        print("Legacy default decoupled                        : True")
        print("Decision cases passed                           :",len(cases))
        print("Guard tests passed                              :",len(guard_rows))
        print("Production max flow-epoch age selected          : False")
        print("G3-R6 accepted-state timeline replay authorized : True")
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
            "G3_R6_accepted_state_timeline_controller_shadow_replay_authorized":False,
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
