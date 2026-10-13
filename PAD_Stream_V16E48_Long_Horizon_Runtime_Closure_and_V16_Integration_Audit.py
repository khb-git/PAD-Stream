
from __future__ import annotations

from pathlib import Path
import argparse, csv, hashlib, io, json, math, subprocess
from typing import Any
import numpy as np

MILESTONE = "V16E-48"
STATUS = "LONG_HORIZON_RUNTIME_CLOSURE_AND_V16_INTEGRATION_AUDIT_VALIDATED"
NEXT = "V16E-49 - Final V16 Freeze and Release-Candidate Assembly"

OBSERVATION_DAYS = [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0]
EXPECTED_STEPS = [611, 1222, 4640, 5747, 7931, 10400, 13259, 18490, 23668]
EXPECTED_CURSORS = list(range(1, 10))
EXPECTED_NEXT = [60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0, None]
INJECTOR_MASS_RATE_KG_DAY = 500_000.0
EXPECTED_BREAKTHROUGH_TIME_DAYS = 23.380258876143085
PRODUCTION_POLICY = "HALF_OBSERVED_STALE_INTERVAL"
MAX_FLOW_EPOCH_DAYS = 4.9417335239115445
EXPECTED_GRID = (15, 50, 50)

LEGACY_REL = Path(
    "provenance/hybrid_dp/V16E18_R1_FROZEN_SGSIM_100D_FULL_GRID_CANDIDATE/"
    "frozen_full_grid/V16E18_R1_Frozen_SGSim_100Day_Full_Grid_Candidate.npz"
)
LEGACY_SHA256 = "d422dc1e56281c1baf0ae007c62ce4bd69677a232bd1448a5bd79d3177eafaea"

POLICY_REL = Path("provenance/hybrid_dp/V16E41R3R6_PRODUCTION_RUNTIME_REFRESH_POLICY_FREEZE")
POLICY_CONTRACT = "PAD_Stream_V16E41R3R6_Production_Runtime_Refresh_Policy_Contract.json"
POLICY_CLOSURE = "V16E41R3R6_Final_Closure.json"

E41_REL = Path("provenance/hybrid_dp/V16E41R3R8_100D_LEGACY_NUMERICAL_REGRESSION_AND_E41_CLOSURE")
E41_SUMMARY = "PAD_Stream_V16E41R3R8_Summary.json"
E41_CLOSURE = "V16E41R3R8_Final_Closure.json"
EXPECTED_E41_STATUS = "E41_REPAIRED_100D_PRODUCTION_AND_LEGACY_NUMERICAL_REGRESSION_CLOSED"

SOURCE_BINDINGS = {
    "E39": ("PAD_Stream_V16E39_Post_Breakthrough_SGSim_Rollout_and_First_30d_Observation_Checkpoint.py", "5c507b72e68f762d9ff9b83f5ea175168bdb3569"),
    "E40": ("PAD_Stream_V16E40_Post_Breakthrough_SGSim_Rollout_and_Second_60d_Observation_Checkpoint.py", "d562444e03e6aac706291694d42b6a4795003ec7"),
    "R3R6": ("PAD_Stream_V16E41R3R6_Production_Runtime_Refresh_Policy_Freeze.py", "58f17776a1e72baece909a67ff6e1ca7135adf6a"),
    "R3R7": ("PAD_Stream_V16E41R3R7_Repaired_Production_Rollout_to_Exact_100Day_Observation.py", "1e7e54f17477788fe518e440c21a65a544b30a48"),
    "R3R8": ("PAD_Stream_V16E41R3R8_100Day_Legacy_Numerical_Regression_and_E41_Closure.py", "607536622c3b0ff0d4aef451652e724ad4689baa"),
    "E42": ("PAD_Stream_V16E42_Repaired_Production_Continuation_to_Exact_150Day_Observation.py", "7efe0cb943b40e976b7364241dc7f41dc819a2df"),
    "E43": ("PAD_Stream_V16E43_Repaired_Production_Continuation_to_Exact_250Day_Observation.py", "1aca85b46129ecc47d4089ea2d2e4b0e00500283"),
    "E44R1": ("PAD_Stream_V16E44R1_Predecessor_Binding_Repair_and_Exact_365Day_Observation.py", "44db79e0553e7a2853e54f057d66874595d51716"),
    "E45": ("PAD_Stream_V16E45_Repaired_Production_Continuation_to_Exact_500Day_Observation.py", "82d730049c18a2ce529f0a80a736bc395c5cf125"),
    "E46": ("PAD_Stream_V16E46_Repaired_Production_Continuation_to_Exact_750Day_Observation.py", "969fae98d3d8ad4b500f3f6d266d838e093ef173"),
    "E47": ("PAD_Stream_V16E47_Repaired_Production_Continuation_to_Exact_1000Day_Observation.py", "b3f6a4212e18e13239eb7bd5703c43484b376dcb"),
}

OBS_SPECS = [
    ("E39",30.0,611,1,60.0,"V16E39_POST_BREAKTHROUGH_FIRST_FIXED_OBSERVATION_30D_CHECKPOINT","PAD_Stream_V16E39_Summary.json","V16E39_Final_Closure.json","POST_BREAKTHROUGH_FIRST_FIXED_OBSERVATION_30D_CHECKPOINT_VALIDATED","V16E39_Canonical_PostBreakthrough_SGSim_Runtime_State_Observation_0030d.npz",None,None,None),
    ("E40",60.0,1222,2,100.0,"V16E40_POST_BREAKTHROUGH_SECOND_FIXED_OBSERVATION_60D_CHECKPOINT","PAD_Stream_V16E40_Summary.json","V16E40_Final_Closure.json","POST_BREAKTHROUGH_SECOND_FIXED_OBSERVATION_60D_CHECKPOINT_VALIDATED","V16E40_Canonical_PostBreakthrough_SGSim_Runtime_State_Observation_0060d.npz",None,None,None),
    ("R3R7",100.0,4640,3,150.0,"V16E41R3R7_REPAIRED_PRODUCTION_EXACT_100D_OBSERVATION","PAD_Stream_V16E41R3R7_Summary.json","V16E41R3R7_Final_Closure.json","REPAIRED_PRODUCTION_EXACT_100D_OBSERVATION_VALIDATED","V16E41R3R7_Authoritative_100d_PostObservation_Refreshed_Restart.npz","0772e6c067d36c20037ff448e2b1ebc7e11c53ef8e05642264583c56bb18a770","exact_100d_observation","rollout"),
    ("E42",150.0,5747,4,250.0,"V16E42_REPAIRED_PRODUCTION_EXACT_150D_OBSERVATION","PAD_Stream_V16E42_Summary.json","V16E42_Final_Closure.json","REPAIRED_PRODUCTION_EXACT_150D_OBSERVATION_VALIDATED","V16E42_Authoritative_150d_PostObservation_Refreshed_Restart.npz","b1be00eee245a5490da2534950ef897b552f52c0194ce5701bdf851cd64b3f74","exact_150d_observation","rollout_100_to_150d"),
    ("E43",250.0,7931,5,365.0,"V16E43_REPAIRED_PRODUCTION_EXACT_250D_OBSERVATION","PAD_Stream_V16E43_Summary.json","V16E43_Final_Closure.json","REPAIRED_PRODUCTION_EXACT_250D_OBSERVATION_VALIDATED","V16E43_Authoritative_250d_PostObservation_Refreshed_Restart.npz","371adfb9b5dbb37a926f7624239a46187c00f3fc6e590734ddf4d2d23c878e57","exact_250d_observation","rollout_150_to_250d"),
    ("E44R1",365.0,10400,6,500.0,"V16E44R1_PREDECESSOR_BINDING_REPAIR_EXACT_365D_OBSERVATION","PAD_Stream_V16E44R1_Summary.json","V16E44R1_Final_Closure.json","PREDECESSOR_BINDING_REPAIRED_EXACT_365D_OBSERVATION_VALIDATED","V16E44R1_Authoritative_365d_PostObservation_Refreshed_Restart.npz","782d852947c29bedb3fa913428779ad14f5f719a861401c6e4fe15fc8944f869","exact_365d_observation","rollout_250_to_365d"),
    ("E45",500.0,13259,7,750.0,"V16E45_REPAIRED_PRODUCTION_EXACT_500D_OBSERVATION","PAD_Stream_V16E45_Summary.json","V16E45_Final_Closure.json","REPAIRED_PRODUCTION_EXACT_500D_OBSERVATION_VALIDATED","V16E45_Authoritative_500d_PostObservation_Refreshed_Restart.npz","21f61c24396305c2651712c34ed03bc6fb818993241820cb3ed0fbc9ac734e09","exact_500d_observation","rollout_365_to_500d"),
    ("E46",750.0,18490,8,1000.0,"V16E46_REPAIRED_PRODUCTION_EXACT_750D_OBSERVATION","PAD_Stream_V16E46_Summary.json","V16E46_Final_Closure.json","REPAIRED_PRODUCTION_EXACT_750D_OBSERVATION_VALIDATED","V16E46_Authoritative_750d_PostObservation_Refreshed_Restart.npz","a07c5e8348f1c7746cd761c1a206b4d770e6db469b8336e2cb1c76c9ffbb4513","exact_750d_observation","rollout_500_to_750d"),
    ("E47",1000.0,23668,9,None,"V16E47_REPAIRED_PRODUCTION_EXACT_1000D_OBSERVATION","PAD_Stream_V16E47_Summary.json","V16E47_Final_Closure.json","REPAIRED_PRODUCTION_EXACT_1000D_OBSERVATION_VALIDATED","V16E47_Authoritative_1000d_PostObservation_Refreshed_Restart.npz","af0097b5e7befc7417286fbb90cc2139a3dab583cb3cce972c9293c7b7fe0a7e","exact_1000d_observation","rollout_750_to_1000d"),
]

OUT_REL = Path("provenance/hybrid_dp/V16E48_LONG_HORIZON_RUNTIME_CLOSURE_AND_V16_INTEGRATION_AUDIT")
BLOCKED_REL = Path("provenance/hybrid_dp/V16E48_BLOCKED_LONG_HORIZON_RUNTIME_CLOSURE_AND_V16_INTEGRATION_AUDIT")

class GateError(RuntimeError): pass

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20), b""): h.update(b)
    return h.hexdigest()

def json_bytes(o: Any) -> bytes:
    return (json.dumps(o,indent=2,sort_keys=True,allow_nan=False)+"\n").encode()

def csv_bytes(rows):
    if not rows: return b""
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    s=io.StringIO(newline="")
    w=csv.DictWriter(s,fieldnames=fields,lineterminator="\n"); w.writeheader(); w.writerows(rows)
    return s.getvalue().encode()

def load_json(p:Path): return json.loads(p.read_text())
def load_npz(p:Path):
    with np.load(p,allow_pickle=False) as z: return {k:z[k].copy() for k in z.files}
def scalar(v): return float(np.asarray(v).reshape(()))
def int_scalar(v): return int(np.asarray(v).reshape(()))
def bool_scalar(v): return bool(np.asarray(v).reshape(()))

def git_blob_sha(path:Path, root:Path)->str:
    r=subprocess.run(["git","-C",str(root),"hash-object",str(path)],check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return r.stdout.strip()

def closure_passed(c):
    return c.get("all_gates_passed") is True or c.get("all_runtime_gates_passed") is True

def immutable_publish(out:Path, files):
    out.mkdir(parents=True,exist_ok=True)
    for n,d in files.items():
        p=out/n
        if p.exists() and p.read_bytes()!=d: raise GateError(f"existing_output_differs:{n}")
        if not p.exists(): p.write_bytes(d)

def self_test():
    if OBSERVATION_DAYS != [30.,60.,100.,150.,250.,365.,500.,750.,1000.]: raise RuntimeError("schedule")
    if EXPECTED_STEPS != [611,1222,4640,5747,7931,10400,13259,18490,23668]: raise RuntimeError("steps")
    if EXPECTED_CURSORS != list(range(1,10)): raise RuntimeError("cursors")
    if EXPECTED_NEXT[-1] is not None: raise RuntimeError("terminal_next")
    if INJECTOR_MASS_RATE_KG_DAY*1000 != 500_000_000.: raise RuntimeError("injection")
    if len(OBS_SPECS)!=9: raise RuntimeError("spec_count")
    print("PAD-Stream V16E-48 long-horizon closure / V16 integration audit self-test: PASS")

def main(project_root:Path, drive_root:Path)->int:
    root=Path(project_root).resolve(); drive=Path(drive_root).resolve()
    out=drive/OUT_REL; blocked=drive/BLOCKED_REL
    gates={}; failed_stage=None
    def gate(name, passed, detail=""):
        gates[name]={"passed":bool(passed),"detail":str(detail)}
        if not passed: raise GateError(name)
    try:
        print("\n"+"="*156)
        print("PAD-Stream V16E-48 — Long-Horizon Runtime Closure and V16 Integration Audit")
        print("="*156)
        print("SIMULATION: none | AUDIT WINDOW: 30 -> 1000 d | NEXT:",NEXT)

        failed_stage="source_provenance_binding"
        source_rows=[]
        for role,(fn,expected) in SOURCE_BINDINGS.items():
            p=root/fn; gate(f"{role}_source_exists",p.is_file(),p)
            actual=git_blob_sha(p,root); gate(f"{role}_git_blob_exact",actual==expected,actual)
            source_rows.append({"role":role,"filename":fn,"expected_git_blob":expected,"actual_git_blob":actual})

        failed_stage="policy_legacy_E41_closure"
        legacy=drive/LEGACY_REL; gate("legacy_exists",legacy.is_file(),legacy)
        legacy_sha=sha256_file(legacy); gate("legacy_SHA_exact",legacy_sha==LEGACY_SHA256,legacy_sha)

        pc=drive/POLICY_REL/POLICY_CONTRACT; pcl=drive/POLICY_REL/POLICY_CLOSURE
        gate("policy_contract_exists",pc.is_file(),pc); gate("policy_closure_exists",pcl.is_file(),pcl)
        policy=load_json(pc); policy_closure=load_json(pcl)
        gate("policy_status_exact",policy.get("status")=="PRODUCTION_RUNTIME_REFRESH_POLICY_FROZEN",policy.get("status"))
        gate("policy_closure_passed",closure_passed(policy_closure))
        gate("policy_name_exact",policy["calibrated_policy"]["name"]==PRODUCTION_POLICY,policy["calibrated_policy"]["name"])
        gate("policy_epoch_exact",abs(float(policy["calibrated_policy"]["maximum_flow_epoch_age_days"])-MAX_FLOW_EPOCH_DAYS)<=1e-15)
        gate("policy_schedule_exact",[float(x) for x in policy["production_observation_policy"]["observation_days"]]==OBSERVATION_DAYS)
        gate("policy_capacity_controller_fallback_only",policy["capacity_safety_policy"]["capacity_controller_is_normal_timestep_driver"] is False)
        gate("policy_mass_clipping_forbidden",policy["capacity_safety_policy"]["mass_clipping_authorized"] is False)
        gate("policy_global_rescale_forbidden",policy["capacity_safety_policy"]["global_plume_rescaling_authorized"] is False)
        gate("policy_IBDP_deferred",policy["scope_guards"]["IBDP_work_authorized_before_V16_closeout"] is False)

        es=drive/E41_REL/E41_SUMMARY; ec=drive/E41_REL/E41_CLOSURE
        gate("E41_summary_exists",es.is_file(),es); gate("E41_closure_exists",ec.is_file(),ec)
        e41s=load_json(es); e41c=load_json(ec)
        gate("E41_status_exact",e41s.get("status")==EXPECTED_E41_STATUS,e41s.get("status"))
        gate("E41_closed",e41s.get("E41_closed") is True and e41c.get("E41_closed") is True)
        gate("E41_all_gates",e41c.get("all_gates_passed") is True)

        failed_stage="checkpoint_lineage_mass_capacity"
        observation_rows=[]; capacity_rows=[]; prior_inj=-1.; prior_prod=-1.
        spec_by_label={}
        for spec in OBS_SPECS:
            (label,day,step,cursor,next_day,rel,summary_name,closure_name,status,state_name,restart_sha,obs_key,rollout_key)=spec
            spec_by_label[label]=spec
            base=drive/"provenance/hybrid_dp"/rel
            sp=base/summary_name; cp=base/closure_name; stp=base/state_name
            gate(f"{label}_summary_exists",sp.is_file(),sp); gate(f"{label}_closure_exists",cp.is_file(),cp); gate(f"{label}_state_exists",stp.is_file(),stp)
            s=load_json(sp); c=load_json(cp); state=load_npz(stp); state_sha=sha256_file(stp)
            gate(f"{label}_status_exact",s.get("status")==status,s.get("status")); gate(f"{label}_closure_passed",closure_passed(c))
            if restart_sha: gate(f"{label}_restart_SHA_exact",state_sha==restart_sha,state_sha)

            t=scalar(state["physical_time_days"]); st=int_scalar(state["accepted_step_index"]); cur=int_scalar(state["observation_cursor_index"])
            last=scalar(state["last_fixed_observation_day"]); nxt=scalar(state["next_fixed_observation_day"])
            gate(f"{label}_time",t==day,t); gate(f"{label}_step",st==step,st); gate(f"{label}_cursor",cur==cursor,cur); gate(f"{label}_last_obs",last==day,last)
            if next_day is None:
                gate(f"{label}_terminal_next_nan",math.isnan(nxt),nxt)
                if "fixed_observation_schedule_complete" in state:
                    gate(f"{label}_terminal_complete_flag",bool_scalar(state["fixed_observation_schedule_complete"]))
                nxt_row=None
            else:
                gate(f"{label}_next_obs",nxt==next_day,nxt); nxt_row=nxt

            gate(f"{label}_BT_history",bool_scalar(state["breakthrough_reached"]) and abs(scalar(state["breakthrough_time_days"])-EXPECTED_BREAKTHROUGH_TIME_DAYS)<=1e-12,scalar(state["breakthrough_time_days"]))
            sat=np.asarray(state["transport_saturation"],dtype=float)
            gate(f"{label}_grid_shape",sat.shape==EXPECTED_GRID,sat.shape); gate(f"{label}_sat_finite",bool(np.all(np.isfinite(sat))))

            inj=scalar(state["cumulative_injected_co2_mass_kg"]); prod=scalar(state["cumulative_produced_co2_mass_kg"])
            stored=scalar(state["stored_co2_mass_current_kg"]); init=scalar(state["stored_co2_mass_initial_kg"])
            resid=stored-init-inj+prod; expected_inj=INJECTOR_MASS_RATE_KG_DAY*day
            inj_tol=max(1e-6,1e-12*expected_inj); mass_tol=max(1e-6,1e-10*max(abs(stored),1.))
            gate(f"{label}_fixed_rate_injection",abs(inj-expected_inj)<=inj_tol,f"{inj}:{expected_inj}:{inj_tol}")
            gate(f"{label}_mass_closure",abs(resid)<=mass_tol,f"{resid}:{mass_tol}")
            gate(f"{label}_injection_monotone",inj>=prior_inj-1e-9); gate(f"{label}_production_monotone",prod>=prior_prod-1e-9)
            prior_inj,prior_prod=inj,prod

            if obs_key:
                obs=s[obs_key]; gate(f"{label}_summary_time",float(obs["time_days"])==day); gate(f"{label}_summary_step",int(obs["step"])==step)
                post=s["post_observation_restart"]; gate(f"{label}_summary_restart_SHA",post["state_sha256"]==restart_sha,post["state_sha256"])
                gate(f"{label}_policy_name",s.get("production_policy")==PRODUCTION_POLICY,s.get("production_policy"))
                gate(f"{label}_policy_epoch",abs(float(s.get("maximum_flow_epoch_age_days"))-MAX_FLOW_EPOCH_DAYS)<=1e-15)
                r=s[rollout_key]; cr=int(r["capacity_refresh_count"]); ca=int(r["capacity_controller_adjustments_total"]); mm=float(r["minimum_raw_capacity_margin_kg"])
                gate(f"{label}_capacity_refresh_zero",cr==0,cr); gate(f"{label}_capacity_controller_zero",ca==0,ca); gate(f"{label}_capacity_margin_positive",mm>0,mm)
                capacity_rows.append({"label":label,"day":day,"accepted_transition_count":int(r["accepted_transition_count"]),"capacity_refresh_count":cr,"capacity_controller_adjustments_total":ca,"minimum_raw_capacity_margin_kg":mm})

            observation_rows.append({"label":label,"day":day,"step":st,"cursor":cur,"last_fixed_observation_day":last,"next_fixed_observation_day":nxt_row,"state_file":state_name,"state_sha256":state_sha,"expected_restart_sha256":restart_sha,"cumulative_injected_co2_mass_kg":inj,"cumulative_produced_co2_mass_kg":prod,"stored_co2_mass_kg":stored,"recomputed_cumulative_mass_residual_kg":resid,"mass_tolerance_kg":mass_tol,"producer_co2_gas_cut":scalar(state["current_producer_co2_gas_cut"]),"breakthrough_time_days":scalar(state["breakthrough_time_days"])})

        failed_stage="post_100d_parent_restart_lineage"
        lineage=[
            ("E42","parent_100d_restart",100.0,"0772e6c067d36c20037ff448e2b1ebc7e11c53ef8e05642264583c56bb18a770"),
            ("E43","parent_150d_restart",150.0,"b1be00eee245a5490da2534950ef897b552f52c0194ce5701bdf851cd64b3f74"),
            ("E44R1","parent_250d_restart",250.0,"371adfb9b5dbb37a926f7624239a46187c00f3fc6e590734ddf4d2d23c878e57"),
            ("E45","parent_365d_restart",365.0,"782d852947c29bedb3fa913428779ad14f5f719a861401c6e4fe15fc8944f869"),
            ("E46","parent_500d_restart",500.0,"21f61c24396305c2651712c34ed03bc6fb818993241820cb3ed0fbc9ac734e09"),
            ("E47","parent_750d_restart",750.0,"a07c5e8348f1c7746cd761c1a206b4d770e6db469b8336e2cb1c76c9ffbb4513"),
        ]
        for label,key,pday,psha in lineage:
            spec=spec_by_label[label]; rel=spec[5]; sn=spec[6]; s=load_json(drive/"provenance/hybrid_dp"/rel/sn); p=s[key]
            gate(f"{label}_parent_time_lineage",float(p["time_days"])==pday,p["time_days"]); gate(f"{label}_parent_SHA_lineage",p["state_sha256"]==psha,p["state_sha256"])

        failed_stage="terminal_closeout_authorization"
        e47=spec_by_label["E47"]; e47s=load_json(drive/"provenance/hybrid_dp"/e47[5]/e47[6]); e47o=e47s["exact_1000d_observation"]
        gate("terminal_schedule_complete_summary",e47o.get("fixed_observation_schedule_complete") is True)
        gate("terminal_next_none_summary",e47o.get("next_fixed_observation_day") is None)

        min_margin=min(r["minimum_raw_capacity_margin_kg"] for r in capacity_rows)
        total_refresh=sum(r["capacity_refresh_count"] for r in capacity_rows); total_adjust=sum(r["capacity_controller_adjustments_total"] for r in capacity_rows)
        final=observation_rows[-1]
        gate("repaired_runtime_min_capacity_margin_positive",min_margin>0,min_margin)
        gate("repaired_runtime_capacity_refreshes_zero",total_refresh==0,total_refresh)
        gate("repaired_runtime_capacity_adjustments_zero",total_adjust==0,total_adjust)
        gate("terminal_injected_500Mkg",abs(final["cumulative_injected_co2_mass_kg"]-500_000_000.)<=5e-4,final["cumulative_injected_co2_mass_kg"])

        runtime_policy_audit={
            "policy_name":PRODUCTION_POLICY,"maximum_flow_epoch_age_days":MAX_FLOW_EPOCH_DAYS,"observation_days":OBSERVATION_DAYS,
            "hard_refresh_triggers":policy["refresh_trigger_policy"]["hard_refresh_triggers"],
            "same_time_refresh_primary_conserved_quantity":policy["same_time_flow_refresh_contract"]["primary_conserved_quantity"],
            "capacity_controller_role":"fallback only","mass_clipping_authorized":False,"global_plume_rescaling_authorized":False,
            "legacy_numerical_candidate_is_truth":False,"legacy_candidate_sha256":legacy_sha,"E41_formally_closed":True,"terminal_schedule_complete":True
        }
        freeze={
            "runtime_observation_schedule_complete":True,"source_provenance_chain_closed":True,"frozen_runtime_policy_consistent":True,
            "all_checkpoint_mass_gates_passed":True,"all_repaired_runtime_capacity_margins_positive":True,
            "capacity_fallback_used_from_100_to_1000d":False,"terminal_1000d_post_observation_restart_available":True,
            "new_physics_required_before_final_V16_freeze":False,"new_calibration_required_before_final_V16_freeze":False,
            "IBDP_work_authorized_now":False,"V16_final_freeze_authorized":True,"required_next_action":NEXT,
            "post_freeze_visual_package_required":policy["V16_closeout_visuals_required"]
        }
        summary={
            "milestone":MILESTONE,"status":STATUS,"simulation_executed":False,"audited_observation_days":OBSERVATION_DAYS,
            "audited_final_step":final["step"],"audited_final_time_days":final["day"],
            "audited_final_restart_sha256":"af0097b5e7befc7417286fbb90cc2139a3dab583cb3cce972c9293c7b7fe0a7e",
            "terminal_cumulative_injected_co2_mass_kg":final["cumulative_injected_co2_mass_kg"],
            "terminal_cumulative_produced_co2_mass_kg":final["cumulative_produced_co2_mass_kg"],
            "terminal_stored_co2_mass_kg":final["stored_co2_mass_kg"],"terminal_recomputed_mass_residual_kg":final["recomputed_cumulative_mass_residual_kg"],
            "terminal_producer_co2_gas_cut":final["producer_co2_gas_cut"],"minimum_raw_capacity_margin_across_repaired_runtime_kg":min_margin,
            "capacity_triggered_refreshes_across_repaired_runtime":total_refresh,"capacity_controller_adjustments_across_repaired_runtime":total_adjust,
            "legacy_numerical_candidate_sha256":legacy_sha,"E41_closed":True,"runtime_policy":runtime_policy_audit,"freeze_readiness":freeze,"next_milestone":NEXT
        }
        closure={
            "milestone":MILESTONE,"status":STATUS,"all_gates_passed":all(v["passed"] for v in gates.values()),"gate_count":len(gates),
            "long_horizon_runtime_closed":True,"observation_schedule_complete":True,"terminal_observation_day":1000.0,"terminal_observation_step":23668,
            "terminal_restart_sha256":"af0097b5e7befc7417286fbb90cc2139a3dab583cb3cce972c9293c7b7fe0a7e",
            "production_policy_frozen":True,"E41_formally_closed":True,"legacy_regression_closed":True,
            "capacity_fallback_used_100_to_1000d":False,"V16_final_freeze_authorized":True,"next_milestone":NEXT
        }
        files={
            "PAD_Stream_V16E48_Summary.json":json_bytes(summary),"V16E48_Source_Bindings.csv":csv_bytes(source_rows),
            "V16E48_Observation_Lineage_and_Mass_Audit.csv":csv_bytes(observation_rows),"V16E48_Capacity_Safety_Audit.csv":csv_bytes(capacity_rows),
            "V16E48_Runtime_Policy_Audit.json":json_bytes(runtime_policy_audit),"V16E48_Freeze_Readiness.json":json_bytes(freeze),
            "V16E48_Final_Gate_Matrix.csv":csv_bytes([{"gate":k,**v} for k,v in gates.items()]),"V16E48_Final_Closure.json":json_bytes(closure)
        }
        immutable_publish(out,files)
        manifest=[]
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name!="V16E48_Artifact_Manifest.csv": manifest.append({"file":p.name,"sha256":sha256_file(p),"bytes":p.stat().st_size})
        immutable_publish(out,{"V16E48_Artifact_Manifest.csv":csv_bytes(manifest)})

        print("\n"+"="*156); print("PAD-Stream V16E-48: PASS"); print("="*156)
        print("Status                              :",STATUS)
        print("Observation schedule complete       : True")
        print("Audited checkpoints                 :",len(observation_rows))
        print("Terminal step / time                :",final["step"],"/",final["day"],"d")
        print("Terminal restart SHA                :",closure["terminal_restart_sha256"])
        print("Terminal injected CO2 kg            :",final["cumulative_injected_co2_mass_kg"])
        print("Terminal produced CO2 kg            :",final["cumulative_produced_co2_mass_kg"])
        print("Terminal stored CO2 kg              :",final["stored_co2_mass_kg"])
        print("Terminal mass residual kg           :",final["recomputed_cumulative_mass_residual_kg"])
        print("Minimum raw capacity margin kg      :",min_margin)
        print("Capacity-triggered refreshes        :",total_refresh)
        print("Capacity controller adjustments     :",total_adjust)
        print("E41 formally closed                 : True")
        print("Legacy frozen candidate unchanged   : True")
        print("V16 final freeze authorized         : True")
        print("Next                                :",NEXT)
        return 0
    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        report={"milestone":MILESTONE,"status":"LONG_HORIZON_RUNTIME_CLOSURE_AND_V16_INTEGRATION_AUDIT_BLOCKED","failed_stage":failed_stage,"exception":repr(exc),"gates":gates}
        data=json_bytes(report); p=blocked/"V16E48_Blocked_Runtime_Closure_Audit.json"
        if p.exists() and p.read_bytes()!=data: p=blocked/("V16E48_Blocked_Runtime_Closure_Audit_"+hashlib.sha256(data).hexdigest()[:12]+".json")
        p.write_bytes(data)
        print("\n"+"="*156); print("PAD-Stream V16E-48: BLOCKED"); print("="*156); print("Report:",p); print("Failed stage:",failed_stage); print("Exception:",repr(exc))
        return 2

def parse_args():
    p=argparse.ArgumentParser(); p.add_argument("--project-root",type=Path,default=Path(".")); p.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute")); p.add_argument("--self-test",action="store_true"); return p.parse_args()
if __name__=="__main__":
    a=parse_args()
    if a.self_test: self_test(); raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))
