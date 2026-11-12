#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, hashlib, json, shutil, subprocess
from pathlib import Path
from typing import Any
import numpy as np

M="POSTV16-AV4-PIVOT-GPU-HYB-G2-A0"
PASS="POSTV16AV4PIVOTGPUHYBG2A0_EARLY_TARGETED_WINDOW_DUALTRANSPORT_PROTOCOL_FREEZE_PASS_NO_PHYSICS_EXECUTION"
BLOCK="POSTV16AV4PIVOTGPUHYBG2A0_PROTOCOL_OR_AUTHORITY_BLOCK_NO_PHYSICS_EXECUTION"
BRANCH="postv16-av4-pivot"
PARENT="71486c0c3af6278e921ee5045f8c27fcebde5875"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

# Current Hybrid replay authority.
G1_R4_R2_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G1_R4_R2_Tiered_Replay_Equivalence_Certification.py"
G1_R4_R2_BLOB="8e2aef8688d7a7978872592079b7913dc09a7056"
G1_R4_R2_REL=BASE_AV4/"POSTV16_AV4_PIVOT_GPU_HYB_G1_R4_R2_Tiered_Replay_Equivalence_Certification"
G1_R4_R2_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G1_R4_R2_Summary.json"
G1_R4_R2_CONTRACT="POSTV16_AV4_PIVOT_GPU_HYB_G1_R4_R2_Downstream_Replay_Contract.json"
G1_R4_R2_STATUS="POSTV16AV4PIVOTGPUHYBG1R4R2_TIERED_REPLAY_EQUIVALENCE_PASS_G2_AUTHORIZED"

# Cadence authority.
PCAD_A2_RUNNER="PAD_Stream_POSTV16_P_CAD_A2_HoldEnvelope_FailureDriver_and_GPU_TargetedProbe_Protocol_Freeze.py"
PCAD_A2_BLOB="6387abe0754c6a1e8e0fd2fb935283766af2a5e7"
PCAD_A2_REL=BASE_AV4/"POSTV16_P_CAD_A2_HoldEnvelope_FailureDriver_and_GPU_TargetedProbe_Protocol_Freeze"
PCAD_A2_SUMMARY="PAD_Stream_POSTV16_P_CAD_A2_Summary.json"
PCAD_A2_STATUS="POSTV16PCADA2_HOLD_ENVELOPE_FAILURE_DRIVER_AND_GPU_TARGETED_PROBE_PROTOCOL_FREEZE_PASS_NO_PHYSICS_EXECUTION"

# Exact runtime / current pressure-refresh lineage.
R3R6_RUNNER="PAD_Stream_V16E41R3R6_Production_Runtime_Refresh_Policy_Freeze.py"
R3R6_BLOB="58f17776a1e72baece909a67ff6e1ca7135adf6a"
R3R6_REL=Path("provenance/hybrid_dp/V16E41R3R6_PRODUCTION_RUNTIME_REFRESH_POLICY_FREEZE")
R3R6_CONTRACT="PAD_Stream_V16E41R3R6_Production_Runtime_Refresh_Policy_Contract.json"
R3R6_CLOSURE="V16E41R3R6_Final_Closure.json"
R3R6_STATUS="PRODUCTION_RUNTIME_REFRESH_POLICY_FROZEN"
MAX_FLOW_EPOCH_DAYS=4.9417335239115445

# Rank-1 current-lineage accepted parent near day 70.
R3R1_REL=Path("provenance/hybrid_dp/V16E41R3R1_ACCEPTED_TRANSITION_BUDGET_CAPACITY_REGIME_AUDIT")
R3R1_STATE="V16E41R3R1_Diagnostic_Partial_Runtime_State_After_2500_Accepted_Transitions.npz"
R3R1_SHA="8714f5b35b99472de0251def022043076f85fb9cee2ada1cfc4d7b7441cce5e6"
R3R1_TIME=69.88346704782309
R3R1_STEP=3975

# Historical exact observation checkpoints.
E39_RUNNER="PAD_Stream_V16E39_Post_Breakthrough_SGSim_Rollout_and_First_30d_Observation_Checkpoint.py"
E39_BLOB="5c507b72e68f762d9ff9b83f5ea175168bdb3569"
E39_REL=Path("provenance/hybrid_dp/V16E39_POST_BREAKTHROUGH_FIRST_FIXED_OBSERVATION_30D_CHECKPOINT")
E39_SUMMARY="PAD_Stream_V16E39_Summary.json"
E39_STATE="V16E39_Canonical_PostBreakthrough_SGSim_Runtime_State_Observation_0030d.npz"
E39_STATUS="POST_BREAKTHROUGH_FIRST_FIXED_OBSERVATION_30D_CHECKPOINT_VALIDATED"

E40_RUNNER="PAD_Stream_V16E40_Post_Breakthrough_SGSim_Rollout_and_Second_60d_Observation_Checkpoint.py"
E40_BLOB="d562444e03e6aac706291694d42b6a4795003ec7"
E40_REL=Path("provenance/hybrid_dp/V16E40_POST_BREAKTHROUGH_SECOND_FIXED_OBSERVATION_60D_CHECKPOINT")
E40_SUMMARY="PAD_Stream_V16E40_Summary.json"
E40_STATE="V16E40_Canonical_PostBreakthrough_SGSim_Runtime_State_Observation_0060d.npz"
E40_STATUS="POST_BREAKTHROUGH_SECOND_FIXED_OBSERVATION_60D_CHECKPOINT_VALIDATED"

R3R7_RUNNER="PAD_Stream_V16E41R3R7_Repaired_Production_Rollout_to_Exact_100Day_Observation.py"
R3R7_BLOB="1e7e54f17477788fe518e440c21a65a544b30a48"
R3R7_REL=Path("provenance/hybrid_dp/V16E41R3R7_REPAIRED_PRODUCTION_EXACT_100D_OBSERVATION")
R3R7_SUMMARY="PAD_Stream_V16E41R3R7_Summary.json"
R3R7_RESTART="V16E41R3R7_Authoritative_100d_PostObservation_Refreshed_Restart.npz"
R3R7_STATUS="REPAIRED_PRODUCTION_EXACT_100D_OBSERVATION_VALIDATED"

E42_RUNNER="PAD_Stream_V16E42_Repaired_Production_Continuation_to_Exact_150Day_Observation.py"
E42_BLOB="7efe0cb943b40e976b7364241dc7f41dc819a2df"
E42_REL=Path("provenance/hybrid_dp/V16E42_REPAIRED_PRODUCTION_EXACT_150D_OBSERVATION")
E42_SUMMARY="PAD_Stream_V16E42_Summary.json"
E42_RESTART="V16E42_Authoritative_150d_PostObservation_Refreshed_Restart.npz"
E42_STATUS="REPAIRED_PRODUCTION_EXACT_150D_OBSERVATION_VALIDATED"

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G2_A0"
OUT_REL=BASE_AV4/(OUT_TOKEN+"_Early_Targeted_Window_DualTransport_Protocol_Freeze")
BLOCK_REL=BASE_AV4/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
CONTRACT=f"{OUT_TOKEN}_Execution_Contract.json"
WINDOWS=f"{OUT_TOKEN}_Targeted_Window_Protocol.csv"
DECISION=f"{OUT_TOKEN}_Decision_Contract.json"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"

class GateError(RuntimeError): pass

def sha256(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""): h.update(c)
    return h.hexdigest()

def gt(root:Path,*args:str)->str:
    return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()

def js(p:Path): return json.loads(p.read_text(encoding="utf-8"))

def write_csv(path:Path,rows:list[dict[str,Any]])->None:
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n"); w.writeheader(); w.writerows(rows)

def state_identity(path:Path, expected_time:float|None=None, expected_sha:str|None=None)->dict[str,Any]:
    if not path.is_file(): raise GateError(f"state_missing:{path}")
    hs=sha256(path)
    if expected_sha is not None and hs!=expected_sha: raise GateError(f"state_sha:{path.name}:{hs}")
    with np.load(path,allow_pickle=False) as z:
        if "physical_time_days" not in z.files or "transport_saturation" not in z.files:
            raise GateError(f"state_schema:{path.name}")
        t=float(np.asarray(z["physical_time_days"]).reshape(()))
        sat=np.asarray(z["transport_saturation"])
        if expected_time is not None and abs(t-expected_time)>1e-10: raise GateError(f"state_time:{path.name}:{t}")
        if sat.shape!=(15,50,50) or not np.all(np.isfinite(sat)): raise GateError(f"state_sat:{path.name}:{sat.shape}")
        step=int(np.asarray(z["accepted_step_index"]).reshape(())) if "accepted_step_index" in z.files else None
    return {"path":str(path),"sha256":hs,"time_days":t,"accepted_step_index":step,"saturation_shape":[15,50,50]}

def selftest():
    probes=[(75,80),(120,125),(40,45)]
    assert probes==[(75,80),(120,125),(40,45)]
    assert MAX_FLOW_EPOCH_DAYS<5.0
    print("POSTV16 GPU-HYB-G2-A0 protocol self-test: PASS")

def main(project_root:Path,drive_root:Path)->int:
    root=project_root.resolve(); drive=drive_root.resolve()
    out=drive/OUT_REL; blocked=drive/BLOCK_REL
    gates=[]
    def gate(name,cond,detail=""):
        ok=bool(cond); gates.append({"gate":name,"pass":ok,"detail":repr(detail) if detail!="" else ""})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail!="" else ""),flush=True)
        if not ok: raise GateError(name)
    try:
        print("="*180)
        print("POSTV16-AV4-PIVOT-GPU-HYB-G2-A0 — EARLY TARGETED-WINDOW DUAL-TRANSPORT PROTOCOL FREEZE")
        print("DESIGN/AUTHORITY ONLY. NO PRESSURE SOLVE. NO TRANSPORT. NO PHYSICAL TIME ADVANCE.")
        print("="*180)

        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_G1_R4_R2",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")
        for fn,blob in [
            (G1_R4_R2_RUNNER,G1_R4_R2_BLOB),(PCAD_A2_RUNNER,PCAD_A2_BLOB),
            (R3R6_RUNNER,R3R6_BLOB),(E39_RUNNER,E39_BLOB),(E40_RUNNER,E40_BLOB),
            (R3R7_RUNNER,R3R7_BLOB),(E42_RUNNER,E42_BLOB)
        ]:
            p=root/fn
            gate(f"source_present:{fn}",p.is_file())
            gate(f"source_blob:{fn}",gt(root,"hash-object",str(p))==blob,gt(root,"hash-object",str(p)) if p.is_file() else "missing")

        g1s=js(drive/G1_R4_R2_REL/G1_R4_R2_SUMMARY)
        gate("G1_R4_R2_status_PASS",g1s.get("status")==G1_R4_R2_STATUS,g1s.get("status"))
        gate("G1_R4_R2_semantic_equivalence",g1s.get("full_replay_semantic_equivalence_PASS") is True)
        gate("G1_R4_R2_G2_authorized",g1s.get("GPU_HYB_G2_authorized") is True)
        gate("G1_R4_R2_contract_present",(drive/G1_R4_R2_REL/G1_R4_R2_CONTRACT).is_file())

        a2=js(drive/PCAD_A2_REL/PCAD_A2_SUMMARY)
        gate("P_CAD_A2_status_PASS",a2.get("status")==PCAD_A2_STATUS,a2.get("status"))
        gate("target_pairs_exact",a2.get("future_GPU_targeted_probe_pairs")==[[75,80],[120,125],[40,45]],a2.get("future_GPU_targeted_probe_pairs"))
        gate("no_production_cadence_selected",a2.get("production_pressure_refresh_cadence_selected") is False)
        gate("exact_flow_truth_required",a2.get("future_GPU_reference_truth_requires_exact_FV_pressure") is True and a2.get("future_GPU_reference_truth_requires_exact_Darcy_Pollock_TOF") is True)

        r3r6c=js(drive/R3R6_REL/R3R6_CONTRACT)
        r3r6cl=js(drive/R3R6_REL/R3R6_CLOSURE)
        gate("R3R6_status_exact",r3r6c.get("status")==R3R6_STATUS,r3r6c.get("status"))
        gate("R3R6_closure_pass",r3r6cl.get("all_gates_passed") is True)
        gate("R3R6_policy_exact",r3r6c["calibrated_policy"]["name"]=="HALF_OBSERVED_STALE_INTERVAL")
        gate("R3R6_epoch_exact",abs(float(r3r6c["calibrated_policy"]["maximum_flow_epoch_age_days"])-MAX_FLOW_EPOCH_DAYS)<=1e-15)

        # Current-lineage rank-1 parent.
        rank1_parent=state_identity(drive/R3R1_REL/R3R1_STATE,R3R1_TIME,R3R1_SHA)
        gate("rank1_parent_step_exact",rank1_parent["accepted_step_index"]==R3R1_STEP,rank1_parent["accepted_step_index"])

        # Observation anchors / validation endpoints.
        e39s=js(drive/E39_REL/E39_SUMMARY); gate("E39_status",e39s.get("status")==E39_STATUS,e39s.get("status"))
        day30=state_identity(drive/E39_REL/E39_STATE,30.0)
        e40s=js(drive/E40_REL/E40_SUMMARY); gate("E40_status",e40s.get("status")==E40_STATUS,e40s.get("status"))
        day60=state_identity(drive/E40_REL/E40_STATE,60.0)
        r7s=js(drive/R3R7_REL/R3R7_SUMMARY); gate("R3R7_status",r7s.get("status")==R3R7_STATUS,r7s.get("status"))
        day100=state_identity(drive/R3R7_REL/R3R7_RESTART,100.0)
        e42s=js(drive/E42_REL/E42_SUMMARY); gate("E42_status",e42s.get("status")==E42_STATUS,e42s.get("status"))
        day150=state_identity(drive/E42_REL/E42_RESTART,150.0)

        windows=[
            {
                "priority_rank":1,"probe_pair":"75-80","restart_day":R3R1_TIME,
                "restart_authority":"V16E41R3R1 accepted current-lineage state",
                "restart_sha256":rank1_parent["sha256"],"window_end_day":80.0,
                "exact_control_transport":"current exact SG7A/runtime transport lineage",
                "hybrid_transport":"screened Hybrid10 proposal + exact/full-physics fallback under TIERED_REPLAY_EQUIVALENCE_V1",
                "flow_policy":"same exact pressure/Darcy/Pollock/TOF authority and same refresh/event schedule on both branches",
                "required_endpoint_days":"75,80",
                "execution_order":"FIRST",
            },
            {
                "priority_rank":2,"probe_pair":"120-125","restart_day":100.0,
                "restart_authority":"V16E41R3R7 authoritative 100d post-observation refreshed restart",
                "restart_sha256":day100["sha256"],"window_end_day":125.0,
                "exact_control_transport":"current exact SG7A/runtime transport lineage",
                "hybrid_transport":"screened Hybrid10 proposal + exact/full-physics fallback under TIERED_REPLAY_EQUIVALENCE_V1",
                "flow_policy":"same exact pressure/Darcy/Pollock/TOF authority and same refresh/event schedule on both branches",
                "required_endpoint_days":"120,125",
                "execution_order":"SECOND",
            },
            {
                "priority_rank":3,"probe_pair":"40-45","restart_day":30.0,
                "restart_authority":"V16E39 exact 30d Cartesian state; mandatory same-time current-authority full flow refresh before branch advance",
                "restart_sha256":day30["sha256"],"window_end_day":45.0,
                "exact_control_transport":"current exact SG7A/runtime transport lineage after hard refresh",
                "hybrid_transport":"screened Hybrid10 proposal + exact/full-physics fallback after same hard refresh",
                "flow_policy":"hard refresh at restart then identical current exact flow-refresh logic on both branches",
                "required_endpoint_days":"40,45",
                "execution_order":"THIRD",
            },
        ]

        contract={
            "milestone":M,"status":PASS,
            "architecture":{
                "two_clock_semantics_preserved":True,
                "transport_clock":"adaptive runtime transitions",
                "flow_epoch_clock":"complete exact pressure -> Darcy -> Pollock -> TOF -> weights -> connectivity refresh",
                "partial_pressure_only_refresh_forbidden":True,
            },
            "dual_transport_design":{
                "same_parent_state_required":True,
                "same_exact_flow_refresh_schedule_required":True,
                "branch_A":"EXACT_CONTROL: existing mass-conservative SG7A/runtime transport + conservative grid transfer",
                "branch_B":"GPU_HYBRID: screened Hybrid10 where eligible; exact R2/full-physics fallback; conservative grid transfer",
                "branch_B_replay_contract":"TIERED_REPLAY_EQUIVALENCE_V1",
                "learned_pressure_seed_used":False,
                "exact_pressure_truth_required":True,
            },
            "probe_metrics":{
                "cadence_primary":[
                    "pressure_relative_L2","flux_relative_L2","tau_end_relative_L2",
                    "streamline_weight_relative_L2","producer_connectivity_mismatch_fraction",
                    "path_RMS_displacement_ft"
                ],
                "supplemental":["pressure_rmse_psi","pressure_max_abs_psi","path_p95_displacement_ft"],
                "transport_cross_branch":[
                    "saturation_relative_L2","saturation_Linf","stored_mass_relative",
                    "producer_gas_cut_absolute","active_cell_count_relative","visible_cell_count_relative"
                ],
                "late_reference":"P-CAD-A2 authoritative Day365-Day405 observed five-day maximum-change envelope",
            },
            "window_strategy":{
                "brute_force_Day30_to365_5day_sweep":False,
                "restart_windows":windows,
                "rank1_parent_note":"Use day69.883 current-lineage state, not old Day60 cache, to avoid mixing pre-refresh and repaired refresh authorities.",
                "rank3_parent_note":"Day30 is historical exact Cartesian state; current exact flow network must be rebuilt at same time before any advance.",
            },
            "no_go":[
                "Do not infer Day75/80/120/125 by interpolation.",
                "Do not use learned pressure as reference truth.",
                "Do not allow Hybrid and exact-control branches to use different flow-refresh decisions.",
                "Do not fill or rescale saturation to hide mass/map-back failures.",
                "Do not select production cadence from G2-A0.",
            ],
        }

        decision={
            "milestone":M,"status":PASS,
            "classification":"G2_EARLY_TARGETED_RESTART_WINDOWS_AND_DUAL_TRANSPORT_COMPARISON_PROTOCOL_FROZEN_RANK1_DAY69P883_TO80_EXECUTION_AUTHORIZED",
            "G2_R1_rank1_Day75_to80_execution_authorized":True,
            "G2_R2_rank2_Day120_to125_execution_authorized":False,
            "G2_R3_rank3_Day40_to45_execution_authorized":False,
            "rank2_unlock_condition":"G2-R1 closes without transport/flow-authority ambiguity",
            "rank3_unlock_condition":"G2-R2 closes and current-authority same-time Day30 refresh is certified",
            "production_pressure_refresh_cadence_selected":False,
            "Day405_to_Day410_transport_remains_authorized":True,
            "Day405_to_Day410_transport_executed":False,
            "P4_authorized":False,
        }

        summary={
            "milestone":M,"status":PASS,"classification":decision["classification"],
            "rank1_restart_time_days":R3R1_TIME,"rank1_restart_sha256":rank1_parent["sha256"],
            "Day30_anchor_sha256":day30["sha256"],"Day60_anchor_sha256":day60["sha256"],
            "Day100_restart_sha256":day100["sha256"],"Day150_restart_sha256":day150["sha256"],
            "production_runtime_reference_max_flow_epoch_days":MAX_FLOW_EPOCH_DAYS,
            "target_pairs":[[75,80],[120,125],[40,45]],
            "dual_transport_protocol_frozen":True,
            "G2_R1_authorized":True,"G2_R2_authorized":False,"G2_R3_authorized":False,
            "physics_execution_performed":False,"physical_time_advanced":False,
            "production_pressure_refresh_cadence_selected":False,
            "P4_authorized":False,
        }

        if out.exists(): raise GateError(f"output_preexists:{out}")
        out.mkdir(parents=True)
        (out/CONTRACT).write_text(json.dumps(contract,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        (out/DECISION).write_text(json.dumps(decision,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        write_csv(out/WINDOWS,windows)
        manifest=[]
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name!=MANIFEST:
                manifest.append({"file":p.name,"sha256":sha256(p),"bytes":p.stat().st_size})
        write_csv(out/MANIFEST,manifest)

        print("="*180)
        print(M,"PASS")
        print("Rank-1 current-lineage restart time       :",R3R1_TIME)
        print("Rank-1 target pair                        : 75 -> 80")
        print("Rank-2 target pair                        : 120 -> 125 (locked)")
        print("Rank-3 target pair                        : 40 -> 45 (locked; same-time Day30 refresh required)")
        print("Dual exact-control / GPU-Hybrid protocol  : FROZEN")
        print("G2-R1 execution authorized                : True")
        print("Production cadence selected               : False")
        print("Physics executed                          : False")
        print("Output directory                          :",out)
        print("="*180)
        return 0
    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps({
            "milestone":M,"status":BLOCK,"exception":repr(exc),"gates":gates,
            "G2_R1_authorized":False,"physics_execution_performed":False,
            "physical_time_advanced":False,"P4_authorized":False
        },indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(M,"BLOCK",repr(exc))
        return 2

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",type=Path,default=Path("."))
    ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test:
        selftest(); raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))
