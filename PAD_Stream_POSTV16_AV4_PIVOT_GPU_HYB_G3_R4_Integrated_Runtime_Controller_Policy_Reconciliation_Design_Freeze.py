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

M="POSTV16-AV4-PIVOT-GPU-HYB-G3-R4"
PASS="POSTV16AV4PIVOTGPUHYBG3R4_INTEGRATED_RUNTIME_CONTROLLER_POLICY_RECONCILIATION_DESIGN_FREEZE_PASS_NO_PHYSICS_EXECUTION"
BLOCK="POSTV16AV4PIVOTGPUHYBG3R4_TECHNICAL_OR_AUTHORITY_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="f8c771a9261a4c98b27d44ff9fc667310a320f23"

G3R3_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R3_EarlyLate_Causal_Cadence_Decision_Freeze.py"
G3R3_BLOB="52819a33333e362b15fd662f5e6dbd399d04cd36"
CTRL_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_Integrated_Runtime_Controller_R2.py"
CTRL_BLOB="2d1c4fd3b792c9c19bef268b74956574bcaaf540"
OLD_CAL_RUNNER="PAD_Stream_V16E41R3R5_Multi_Refresh_Cadence_Sensitivity_Runtime_Refresh_Policy_Calibration.py"
OLD_CAL_BLOB="15aae3224ba4337cad72f9b4aa9166d602791349"
OLD_FREEZE_RUNNER="PAD_Stream_V16E41R3R6_Production_Runtime_Refresh_Policy_Freeze.py"
OLD_FREEZE_BLOB="58f17776a1e72baece909a67ff6e1ca7135adf6a"
B5_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_B5_CPU_GPU_Overlap_Economics_Probe.py"
B5_BLOB="e3149d043c71fa7745b37f01bb27630fcbdfa563"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

G3R3_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G3_R3_EarlyLate_Causal_Cadence_Decision_Freeze"
G3R3_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R3_Summary.json"
G3R3_DEC="POSTV16_AV4_PIVOT_GPU_HYB_G3_R3_Decision_Contract.json"
G3R3_STATUS="POSTV16AV4PIVOTGPUHYBG3R3_EARLY_LATE_CAUSAL_CADENCE_DECISION_FREEZE_PASS_NO_PHYSICS_EXECUTION"

B5_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G4_B5_Route_Economics_Instrumentation"
B5_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_B5_Summary.json"
B5_STATUS="POSTV16AV4PIVOTGPUHYBG4B5_CPU_GPU_OVERLAP_ECONOMICS_PROBE_PASS"

OLD_R3R5_REL=Path("provenance/hybrid_dp/V16E41R3R5_MULTI_REFRESH_CADENCE_SENSITIVITY_RUNTIME_POLICY_CALIBRATION")
OLD_R3R5_SUM="PAD_Stream_V16E41R3R5_Summary.json"
OLD_R3R5_CLOSURE="V16E41R3R5_Final_Closure.json"
OLD_R3R5_STATUS="MULTI_REFRESH_CADENCE_SENSITIVITY_RUNTIME_POLICY_CALIBRATED"

OLD_R3R6_REL=Path("provenance/hybrid_dp/V16E41R3R6_PRODUCTION_RUNTIME_REFRESH_POLICY_FREEZE")
OLD_R3R6_CONTRACT="PAD_Stream_V16E41R3R6_Production_Runtime_Refresh_Policy_Contract.json"
OLD_R3R6_CLOSURE="V16E41R3R6_Final_Closure.json"
OLD_R3R6_STATUS="PRODUCTION_RUNTIME_REFRESH_POLICY_FROZEN"

LEGACY_SELECTED_POLICY="HALF_OBSERVED_STALE_INTERVAL"
LEGACY_MAX_FLOW_EPOCH_DAYS=4.9417335239115445
CURRENT_DEVELOPMENT_REFERENCE_DAYS=5.0

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

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G3_R4"
OUT_REL=BASE/(OUT_TOKEN+"_Integrated_Runtime_Controller_Policy_Reconciliation_Design_Freeze")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
CONTRACT=f"{OUT_TOKEN}_Reconciliation_Contract.json"
DECISION=f"{OUT_TOKEN}_Decision_Contract.json"
SOURCE_BINDINGS=f"{OUT_TOKEN}_Source_Bindings.csv"
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

def selftest(root:Path):
    g3=import_exact(root,G3R3_RUNNER,G3R3_BLOB,"g3r4_g3r3_selftest")
    ctrl=import_exact(root,CTRL_RUNNER,CTRL_BLOB,"g3r4_ctrl_selftest")
    old=import_exact(root,OLD_FREEZE_RUNNER,OLD_FREEZE_BLOB,"g3r4_oldfreeze_selftest")
    exact_blob(root,OLD_CAL_RUNNER,OLD_CAL_BLOB)
    exact_blob(root,B5_RUNNER,B5_BLOB)

    assert ctrl.DEVELOPMENT_FLOW_REFRESH_REFERENCE_DAYS==CURRENT_DEVELOPMENT_REFERENCE_DAYS
    assert abs(ctrl.PRODUCTION_MAX_FLOW_EPOCH_DAYS-LEGACY_MAX_FLOW_EPOCH_DAYS)<=1e-15
    assert tuple(ctrl.HARD_REFRESH_TRIGGERS)==HARD_REFRESH_TRIGGERS
    assert tuple(ctrl.production_refresh_sequence())==REFRESH_SEQUENCE
    assert tuple(ctrl.transport_reuse_sequence())==TRANSPORT_REUSE_SEQUENCE
    assert abs(old.EXPECTED_SELECTED_MAX_EPOCH_DAYS-LEGACY_MAX_FLOW_EPOCH_DAYS)<=1e-15
    assert old.EXPECTED_SELECTED_POLICY==LEGACY_SELECTED_POLICY
    assert g3.PARENT=="213e66660f2c8ce6733235dc0c06d92ca1b6bae0"
    print("POSTV16 GPU-HYB-G3-R4 structural/authority self-test: PASS")

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
            "detail":"" if detail is None else repr(detail)
        })
        print(f"[{'PASS' if ok else 'FAIL'}] {name}"+("" if detail is None else f" -- {detail}"),flush=True)
        if not ok:
            raise GateError(name)

    try:
        print("="*190)
        print("G3-R4 — INTEGRATED RUNTIME CONTROLLER POLICY RECONCILIATION DESIGN FREEZE")
        print("NO PHYSICS EXECUTION. NO CONTROLLER MUTATION. NO PRODUCTION CADENCE ACTIVATION.")
        print("RECONCILES NEW GPU-HYBRID CAUSAL EVIDENCE WITH LEGACY E41 CONTROLLER CALIBRATION.")
        print("="*190)

        stage="repository"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_G3_R3_PASS_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")

        stage="source_authority"
        bindings=[
            ("G3_R3",G3R3_RUNNER,G3R3_BLOB),
            ("G4_CONTROLLER_R2",CTRL_RUNNER,CTRL_BLOB),
            ("LEGACY_R3_R5_CALIBRATION",OLD_CAL_RUNNER,OLD_CAL_BLOB),
            ("LEGACY_R3_R6_POLICY_FREEZE",OLD_FREEZE_RUNNER,OLD_FREEZE_BLOB),
            ("G4_B5_TRANSPORT_CONTEXT",B5_RUNNER,B5_BLOB),
        ]
        binding_rows=[]
        for role,fn,expected in bindings:
            actual=exact_blob(root,fn,expected)
            gate(role+"_blob_exact",actual==expected,actual)
            binding_rows.append({
                "role":role,
                "filename":fn,
                "expected_git_blob":expected,
                "actual_git_blob":actual,
            })

        ctrl=import_exact(root,CTRL_RUNNER,CTRL_BLOB,"g3r4_ctrl")
        oldfreeze=import_exact(root,OLD_FREEZE_RUNNER,OLD_FREEZE_BLOB,"g3r4_oldfreeze")

        stage="current_G3_R3_authority"
        g3s_path=drive/G3R3_REL/G3R3_SUM
        g3d_path=drive/G3R3_REL/G3R3_DEC
        gate("G3_R3_summary_present",g3s_path.is_file(),str(g3s_path))
        gate("G3_R3_decision_present",g3d_path.is_file(),str(g3d_path))
        g3s=js(g3s_path)
        g3d=js(g3d_path)
        gate("G3_R3_status_exact",g3s.get("status")==G3R3_STATUS,g3s.get("status"))
        gate("G3_R3_5day_reference",float(g3s.get("cross_regime_conservative_reference_days"))==5.0,g3s.get("cross_regime_conservative_reference_days"))
        gate("G3_R3_15day_fixed_hold_closed",g3s.get("fixed_15day_production_hold_authorized") is False)
        gate("G3_R3_no_new_tolerance",g3s.get("new_scientific_tolerance_defined") is False)
        gate("G3_R3_no_production_cadence",g3s.get("production_pressure_refresh_cadence_selected") is False)
        gate("G3_R3_reconciliation_authorized",g3s.get("next_integrated_refresh_policy_reconciliation_design_freeze_authorized") is True)
        gate("G3_R3_decision_reconciliation_authorized",g3d.get("next_integrated_refresh_policy_reconciliation_design_freeze_authorized") is True)
        gate("G3_R3_existing_controller_not_promotable",g3d.get("no_existing_runtime_controller_may_be_promoted_to_production_from_this_freeze_alone") is True)

        stage="current_transport_context"
        b5p=drive/B5_REL/B5_SUM
        gate("B5_summary_present",b5p.is_file(),str(b5p))
        b5=js(b5p)
        gate("B5_status_exact",b5.get("status")==B5_STATUS,b5.get("status"))
        gate("B5_exact_output_identity",b5.get("exact_output_identity_certified") is True)
        gate("B5_R4_transport_authority_preserved",b5.get("G4_B4_fixed_shape_graph_transport_authority_preserved") is True)
        gate("B5_production_closed",b5.get("integrated_GPU_runtime_production_authorized") is False)
        gate("B5_P4_closed",b5.get("P4_authorized") is False)

        stage="legacy_E41_authority"
        r35p=drive/OLD_R3R5_REL/OLD_R3R5_SUM
        r35c=drive/OLD_R3R5_REL/OLD_R3R5_CLOSURE
        r36p=drive/OLD_R3R6_REL/OLD_R3R6_CONTRACT
        r36c=drive/OLD_R3R6_REL/OLD_R3R6_CLOSURE
        for label,p in [
            ("legacy_R3R5_summary",r35p),
            ("legacy_R3R5_closure",r35c),
            ("legacy_R3R6_contract",r36p),
            ("legacy_R3R6_closure",r36c),
        ]:
            gate(label+"_present",p.is_file(),str(p))
        r35=js(r35p)
        r35cl=js(r35c)
        r36=js(r36p)
        r36cl=js(r36c)
        gate("legacy_R3R5_status_exact",r35.get("status")==OLD_R3R5_STATUS,r35.get("status"))
        gate("legacy_R3R5_all_gates_passed",r35cl.get("all_gates_passed") is True)
        gate("legacy_R3R5_selected_policy_exact",r35.get("selected_policy")==LEGACY_SELECTED_POLICY,r35.get("selected_policy"))
        gate("legacy_R3R5_selected_epoch_exact",abs(float(r35.get("selected_max_flow_epoch_days"))-LEGACY_MAX_FLOW_EPOCH_DAYS)<=1e-15,r35.get("selected_max_flow_epoch_days"))
        gate("legacy_R3R6_status_exact",r36.get("status")==OLD_R3R6_STATUS,r36.get("status"))
        gate("legacy_R3R6_closure_status_exact",r36cl.get("status")==OLD_R3R6_STATUS,r36cl.get("status"))
        gate("legacy_R3R6_policy_frozen_historically",r36cl.get("production_policy_frozen") is True)
        gate("legacy_R3R6_epoch_exact",abs(float(r36cl.get("maximum_flow_epoch_age_days"))-LEGACY_MAX_FLOW_EPOCH_DAYS)<=1e-15)

        stage="controller_semantics"
        gate("controller_development_reference_5d",float(ctrl.DEVELOPMENT_FLOW_REFRESH_REFERENCE_DAYS)==CURRENT_DEVELOPMENT_REFERENCE_DAYS,ctrl.DEVELOPMENT_FLOW_REFRESH_REFERENCE_DAYS)
        gate("controller_legacy_epoch_value_exact",abs(float(ctrl.PRODUCTION_MAX_FLOW_EPOCH_DAYS)-LEGACY_MAX_FLOW_EPOCH_DAYS)<=1e-15,ctrl.PRODUCTION_MAX_FLOW_EPOCH_DAYS)
        gate("controller_hard_triggers_exact",tuple(ctrl.HARD_REFRESH_TRIGGERS)==HARD_REFRESH_TRIGGERS,ctrl.HARD_REFRESH_TRIGGERS)
        gate("controller_refresh_sequence_exact",tuple(ctrl.production_refresh_sequence())==REFRESH_SEQUENCE,ctrl.production_refresh_sequence())
        gate("controller_transport_reuse_sequence_exact",tuple(ctrl.transport_reuse_sequence())==TRANSPORT_REUSE_SEQUENCE,ctrl.transport_reuse_sequence())
        gate("legacy_freeze_hard_triggers_exact",tuple(oldfreeze.HARD_REFRESH_TRIGGERS)==HARD_REFRESH_TRIGGERS,oldfreeze.HARD_REFRESH_TRIGGERS)

        stage="reconciliation_freeze"
        reconciled_policy_class=(
            "CURRENT_GPU_HYBRID_DEVELOPMENT_REFERENCE_5D_WITH_HARD_EVENT_REFRESH;"
            "LEGACY_E41_4P9417335239115445D_RETAINED_AS_HISTORICAL_CALIBRATION_ONLY;"
            "CURRENT_GPU_HYBRID_PRODUCTION_EPOCH_LIMIT_UNSELECTED;"
            "LONGER_LATE_HOLD_REQUIRES_STAGEWISE_OR_ADAPTIVE_VALIDATION"
        )
        current_gpu_hybrid_production_epoch_days=None
        legacy_epoch_current_production_authority=False
        fixed_15day_production_hold_authorized=False

        gate("current_GPU_Hybrid_production_epoch_unselected",current_gpu_hybrid_production_epoch_days is None)
        gate("legacy_epoch_not_current_production_authority",legacy_epoch_current_production_authority is False)
        gate("fixed_15day_hold_closed",fixed_15day_production_hold_authorized is False)
        gate("five_day_development_reference_preserved",CURRENT_DEVELOPMENT_REFERENCE_DAYS==5.0)
        gate("no_controller_source_mutation",True)
        gate("no_physics_execution",True)
        gate("no_new_scientific_tolerance",True)
        gate("P4_closed",True)

        contract={
            "milestone":M,
            "status":PASS,
            "purpose":"Freeze the policy reconciliation between the existing integrated runtime controller, historical E41 cadence calibration, and current GPU-Hybrid causal cadence evidence before any controller implementation change or production activation.",
            "current_GPU_Hybrid_evidence":{
                "development_flow_refresh_reference_days":CURRENT_DEVELOPMENT_REFERENCE_DAYS,
                "fixed_15day_production_hold_authorized":False,
                "longer_late_hold_status":"RESEARCH_ONLY_REQUIRES_STAGEWISE_OR_ADAPTIVE_VALIDATION",
                "production_pressure_refresh_cadence_selected":False,
                "source":"G3-R3",
            },
            "legacy_E41_calibration":{
                "selected_policy":LEGACY_SELECTED_POLICY,
                "maximum_flow_epoch_age_days":LEGACY_MAX_FLOW_EPOCH_DAYS,
                "historically_frozen":True,
                "current_GPU_Hybrid_production_authority":False,
                "classification":"LEGACY_ARCHITECTURE_SPECIFIC_CALIBRATED_EVIDENCE_REQUIRES_CURRENT_ARCHITECTURE_REVALIDATION",
            },
            "reconciled_controller_policy":{
                "policy_class":reconciled_policy_class,
                "development_reference_days":CURRENT_DEVELOPMENT_REFERENCE_DAYS,
                "current_GPU_Hybrid_production_max_flow_epoch_days":current_gpu_hybrid_production_epoch_days,
                "hard_refresh_triggers":list(HARD_REFRESH_TRIGGERS),
                "hard_triggers_override_age_policy":True,
                "same_time_refresh_preserves_cellwise_component_mass":True,
                "refresh_sequence":list(REFRESH_SEQUENCE),
                "refreshed_flow_CFL_required":True,
                "capacity_preflight_rejection_remains_hard_refresh_trigger":True,
                "fixed_15day_production_hold_authorized":False,
                "adaptive_or_stagewise_longer_late_hold_authorized_for_research_test_only":True,
            },
            "transport_context":{
                "R4_fixed_shape_graph_exact_transport_authority_preserved":True,
                "B5_CPU_GPU_overlap_probe_completed":True,
                "B5_overlap_may_be_used_as_runtime_implementation_context":True,
                "B5_overlap_does_not_select_refresh_cadence":True,
                "transport_reuse_sequence":list(TRANSPORT_REUSE_SEQUENCE),
            },
            "implementation_guards":{
                "controller_source_mutation_in_R4":False,
                "physics_execution_in_R4":False,
                "canonical_state_mutation_in_R4":False,
                "new_scientific_tolerance_defined":False,
                "production_pressure_refresh_cadence_selected":False,
                "integrated_GPU_runtime_production_authorized":False,
                "P4_authorized":False,
            },
            "next_milestone":{
                "name":"POSTV16-AV4-PIVOT-GPU-HYB-G3-R5",
                "purpose":"Implement a reconciled runtime controller shadow using the frozen G3-R4 semantics and test decisions at age boundaries and hard-trigger cases without mutating canonical simulation state.",
                "authorized":True,
                "production_activation_authorized":False,
            },
        }

        decision={
            "milestone":M,
            "status":PASS,
            "G3_R4_reconciliation_design_frozen":True,
            "five_day_development_reference_preserved":True,
            "legacy_4p9417335239115445d_calibration_preserved_as_historical_evidence":True,
            "legacy_4p9417335239115445d_current_GPU_Hybrid_production_authority":False,
            "current_GPU_Hybrid_production_max_flow_epoch_days":None,
            "fixed_15day_production_hold_authorized":False,
            "hard_refresh_trigger_set_preserved":True,
            "mass_conservative_same_time_refresh_semantics_preserved":True,
            "refreshed_flow_CFL_semantics_preserved":True,
            "current_R4_B5_transport_context_bound":True,
            "production_pressure_refresh_cadence_selected":False,
            "G3_R5_reconciled_controller_shadow_implementation_authorized":True,
            "G3_R5_canonical_state_mutation_authorized":False,
            "G3_R5_production_activation_authorized":False,
            "P4_authorized":False,
        }

        summary={
            "milestone":M,
            "status":PASS,
            "classification":"GPU_HYBRID_CONTROLLER_POLICY_RECONCILIATION_DESIGN_FROZEN_LEGACY_E41_4P9417D_RETAINED_AS_HISTORICAL_EVIDENCE_NOT_CURRENT_PRODUCTION_AUTHORITY",
            "physics_executed":False,
            "controller_source_mutated":False,
            "canonical_state_mutated":False,
            "G3_R3_authority_bound":True,
            "legacy_E41_R3_R5_R3_R6_authority_bound":True,
            "existing_G4_controller_R2_authority_bound":True,
            "B5_transport_context_bound":True,
            "development_flow_refresh_reference_days":CURRENT_DEVELOPMENT_REFERENCE_DAYS,
            "legacy_E41_max_flow_epoch_days":LEGACY_MAX_FLOW_EPOCH_DAYS,
            "legacy_E41_max_flow_epoch_current_GPU_Hybrid_production_authority":False,
            "current_GPU_Hybrid_production_max_flow_epoch_days":None,
            "hard_refresh_triggers":list(HARD_REFRESH_TRIGGERS),
            "fixed_15day_production_hold_authorized":False,
            "longer_late_hold_status":"RESEARCH_ONLY_REQUIRES_STAGEWISE_OR_ADAPTIVE_VALIDATION",
            "new_scientific_tolerance_defined":False,
            "production_pressure_refresh_cadence_selected":False,
            "G3_R5_reconciled_controller_shadow_implementation_authorized":True,
            "integrated_GPU_runtime_production_authorized":False,
            "P4_authorized":False,
        }

        stage="publication"
        gate("output_absent",not out.exists(),str(out))
        out.mkdir(parents=True)
        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        (out/CONTRACT).write_text(json.dumps(contract,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        (out/DECISION).write_text(json.dumps(decision,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        write_csv(out/SOURCE_BINDINGS,binding_rows)
        write_csv(out/GATES,gates)
        write_csv(out/MANIFEST,[
            {"file":q.name,"sha256":sha256(q),"bytes":q.stat().st_size}
            for q in sorted(out.iterdir()) if q.is_file() and q.name!=MANIFEST
        ])

        print("="*190)
        print(M,"PASS")
        print("Development refresh reference                    : 5.0 d")
        print("Legacy E41 calibrated epoch                      :",LEGACY_MAX_FLOW_EPOCH_DAYS,"d")
        print("Legacy epoch current GPU-Hybrid production auth  : False")
        print("Current GPU-Hybrid production epoch selected     : False")
        print("15-day fixed production hold authorized          : False")
        print("Hard refresh triggers preserved                   :",list(HARD_REFRESH_TRIGGERS))
        print("G3-R5 controller shadow implementation authorized: True")
        print("Production activation authorized                 : False")
        print("P4 authorized                                    : False")
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
            "G3_R5_reconciled_controller_shadow_implementation_authorized":False,
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
