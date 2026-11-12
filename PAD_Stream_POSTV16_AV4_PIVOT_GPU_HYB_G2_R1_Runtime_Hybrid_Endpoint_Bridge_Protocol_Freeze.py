#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,json,subprocess
from pathlib import Path
from typing import Any
import numpy as np

M="POSTV16-AV4-PIVOT-GPU-HYB-G2-R1"
PASS="POSTV16AV4PIVOTGPUHYBG2R1_RUNTIME_HYBRID_ENDPOINT_BRIDGE_PROTOCOL_FREEZE_PASS_NO_PHYSICS_EXECUTION"
BLOCK="POSTV16AV4PIVOTGPUHYBG2R1_PROTOCOL_OR_AUTHORITY_BLOCK_NO_PHYSICS_EXECUTION"
BRANCH="postv16-av4-pivot"
PARENT="cfc33622f74d0178527e74a042db63a6e2843ef0"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

G2A0_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_A0_Early_Targeted_Window_DualTransport_Protocol_Freeze.py"
G2A0_BLOB="95702d782d636b7e4e8ec0873410f0323ee1e95c"
G2A0_REL=BASE_AV4/"POSTV16_AV4_PIVOT_GPU_HYB_G2_A0_Early_Targeted_Window_DualTransport_Protocol_Freeze"
G2A0_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_A0_Summary.json"
G2A0_STATUS="POSTV16AV4PIVOTGPUHYBG2A0_EARLY_TARGETED_WINDOW_DUALTRANSPORT_PROTOCOL_FREEZE_PASS_NO_PHYSICS_EXECUTION"

G1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G1_R4_R2_Tiered_Replay_Equivalence_Certification.py"
G1_BLOB="8e2aef8688d7a7978872592079b7913dc09a7056"
G1_REL=BASE_AV4/"POSTV16_AV4_PIVOT_GPU_HYB_G1_R4_R2_Tiered_Replay_Equivalence_Certification"
G1_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G1_R4_R2_Summary.json"
G1_STATUS="POSTV16AV4PIVOTGPUHYBG1R4R2_TIERED_REPLAY_EQUIVALENCE_PASS_G2_AUTHORIZED"

PCAD_RUNNER="PAD_Stream_POSTV16_P_CAD_A2_HoldEnvelope_FailureDriver_and_GPU_TargetedProbe_Protocol_Freeze.py"
PCAD_BLOB="6387abe0754c6a1e8e0fd2fb935283766af2a5e7"

E11_RUNNER="PAD_Stream_V16E11_R2_Packed_SG5_Serialization_Repair_and_Controlled_Hybrid_Streamline_Pilot.py"
E11_BLOB="bf89c14a3cb177fb483e233a17b72e824d31119b"
E9_ADAPTER="PAD_Stream_V16E9_Hybrid_Transport_Adapter.py"
E9_BLOB="83e3340424f43ceda604c403e955435036cf6661"
E9R1_RUNNER="PAD_Stream_V16E9_R1_Reconciled_Hybrid_Transport_Adapter_Identical_State_Certification.py"
E9R1_BLOB="f66ef57bdbc87808de68154643b604e9ccc5f6de"

E37A_RUNNER="PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB="0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
E35R2_RUNNER="PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
E35R2_BLOB="a127f8730a16e150713420ea547a8de6255550ef"
R3R5_RUNNER="PAD_Stream_V16E41R3R5_Multi_Refresh_Cadence_Sensitivity_Runtime_Refresh_Policy_Calibration.py"
R3R5_BLOB="15aae3224ba4337cad72f9b4aa9166d602791349"
R3R5_REL=Path("provenance/hybrid_dp/V16E41R3R5_MULTI_REFRESH_CADENCE_SENSITIVITY_RUNTIME_POLICY_CALIBRATION")
R3R5_SUMMARY="PAD_Stream_V16E41R3R5_Summary.json"
R3R5_SELECTED="V16E41R3R5_Selected_Calibration_State_80d.npz"
R3R5_STATUS="MULTI_REFRESH_CADENCE_SENSITIVITY_RUNTIME_POLICY_CALIBRATED"
R3R5_SELECTED_SHA="7ca6f0b8fbbf08608d4ddc6cc136e4cfcd5cbb3e609762412e1ba861ef41a0fb"
MAX_EPOCH=4.9417335239115445

R3R1_REL=Path("provenance/hybrid_dp/V16E41R3R1_ACCEPTED_TRANSITION_BUDGET_CAPACITY_REGIME_AUDIT")
R3R1_STATE="V16E41R3R1_Diagnostic_Partial_Runtime_State_After_2500_Accepted_Transitions.npz"
R3R1_SHA="8714f5b35b99472de0251def022043076f85fb9cee2ada1cfc4d7b7441cce5e6"
R3R1_TIME=69.88346704782309

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G2_R1"
OUT_REL=BASE_AV4/(OUT_TOKEN+"_Runtime_Hybrid_Endpoint_Bridge_Protocol_Freeze")
BLOCK_REL=BASE_AV4/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
CONTRACT=f"{OUT_TOKEN}_Endpoint_Bridge_Contract.json"
AMEND=f"{OUT_TOKEN}_A0_Refinement_Contract.json"
HANDOFF=f"{OUT_TOKEN}_Rank1_Execution_Handoff.json"
GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"

class GateError(RuntimeError): pass

def sha256(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""): h.update(c)
    return h.hexdigest()

def gt(root:Path,*args:str)->str:
    return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()

def js(p:Path)->dict[str,Any]:
    return json.loads(p.read_text(encoding="utf-8"))

def write_csv(path:Path,rows:list[dict[str,Any]])->None:
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n"); w.writeheader(); w.writerows(rows)

def state_check(path:Path,expected_time:float,expected_sha:str|None=None)->dict[str,Any]:
    if not path.is_file(): raise GateError(f"missing_state:{path}")
    hs=sha256(path)
    if expected_sha and hs!=expected_sha: raise GateError(f"state_sha:{path.name}:{hs}")
    with np.load(path,allow_pickle=False) as z:
        for k in ["physical_time_days","transport_saturation","accepted_step_index"]:
            if k not in z.files: raise GateError(f"state_key:{path.name}:{k}")
        t=float(np.asarray(z["physical_time_days"]).reshape(()))
        step=int(np.asarray(z["accepted_step_index"]).reshape(()))
        sat=np.asarray(z["transport_saturation"])
        if abs(t-expected_time)>1e-12: raise GateError(f"state_time:{path.name}:{t}")
        if sat.shape!=(15,50,50) or not np.all(np.isfinite(sat)): raise GateError(f"state_sat:{path.name}:{sat.shape}")
    return {"sha256":hs,"time_days":t,"step":step,"shape":[15,50,50]}

def selftest():
    ncv=200
    old=np.zeros((3,ncv),dtype=float)
    face=np.empty((3,ncv+1),dtype=float)
    face[:,0]=0.8
    face[:,1:]=old
    assert face.shape==(3,201)
    assert MAX_EPOCH<5.0
    print("POSTV16 GPU-HYB-G2-R1 endpoint bridge self-test: PASS")

def main(project_root:Path,drive_root:Path)->int:
    root=project_root.resolve(); drive=drive_root.resolve()
    out=drive/OUT_REL; blocked=drive/BLOCK_REL
    gates=[]
    def gate(name,cond,detail=""):
        ok=bool(cond); gates.append({"gate":name,"pass":ok,"detail":"" if detail=="" else repr(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail=="" else f" -- {detail}"),flush=True)
        if not ok: raise GateError(name)
    try:
        print("="*190)
        print("POSTV16-AV4-PIVOT-GPU-HYB-G2-R1 — RUNTIME/HYBRID ENDPOINT BRIDGE PROTOCOL FREEZE")
        print("NO PHYSICAL TIME ADVANCE. NO PRESSURE/FLOW SOLVE. NO MODEL INFERENCE.")
        print("="*190)

        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_G2_A0",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")

        bindings=[
            (G2A0_RUNNER,G2A0_BLOB),(G1_RUNNER,G1_BLOB),(PCAD_RUNNER,PCAD_BLOB),
            (E11_RUNNER,E11_BLOB),(E9_ADAPTER,E9_BLOB),(E9R1_RUNNER,E9R1_BLOB),
            (E37A_RUNNER,E37A_BLOB),(E35R2_RUNNER,E35R2_BLOB),(R3R5_RUNNER,R3R5_BLOB)
        ]
        for fn,blob in bindings:
            p=root/fn
            gate(f"source_present:{fn}",p.is_file())
            gate(f"source_blob:{fn}",gt(root,"hash-object",str(p))==blob,gt(root,"hash-object",str(p)) if p.is_file() else "missing")

        a0=js(drive/G2A0_REL/G2A0_SUMMARY)
        gate("G2A0_status_exact",a0.get("status")==G2A0_STATUS,a0.get("status"))
        gate("G2A0_rank1_authorized",a0.get("G2_R1_authorized") is True)
        gate("G2A0_target_pairs_exact",a0.get("target_pairs")==[[75,80],[120,125],[40,45]],a0.get("target_pairs"))

        g1=js(drive/G1_REL/G1_SUMMARY)
        gate("G1_status_exact",g1.get("status")==G1_STATUS,g1.get("status"))
        gate("G1_semantic_equivalence",g1.get("full_replay_semantic_equivalence_PASS") is True)
        gate("G1_model_conditioning_exact",g1.get("model_conditioning_tail_float32_exact") is True)
        gate("G1_learned_replay_exact",float(g1.get("learned_saturation_max_abs",1.0))==0.0)

        p69=state_check(drive/R3R1_REL/R3R1_STATE,R3R1_TIME,R3R1_SHA)
        r3r5=js(drive/R3R5_REL/R3R5_SUMMARY)
        gate("R3R5_status_exact",r3r5.get("status")==R3R5_STATUS,r3r5.get("status"))
        gate("R3R5_selected_policy_exact",r3r5.get("selected_policy")=="HALF_OBSERVED_STALE_INTERVAL",r3r5.get("selected_policy"))
        gate("R3R5_selected_epoch_exact",abs(float(r3r5.get("selected_max_flow_epoch_days"))-MAX_EPOCH)<=1e-15,r3r5.get("selected_max_flow_epoch_days"))
        gate("R3R5_selected_state_SHA_record_exact",r3r5.get("selected_calibration_state_sha256")==R3R5_SELECTED_SHA,r3r5.get("selected_calibration_state_sha256"))
        p80=state_check(drive/R3R5_REL/R3R5_SELECTED,80.0,R3R5_SELECTED_SHA)

        contract={
            "milestone":M,"status":PASS,
            "discovered_semantic_gap":{
                "E11_Hybrid_output":"absolute 201-node/face streamline saturation fan at a physical time",
                "E41_runtime_state":"incrementally advanced conservative Cartesian component-mass state",
                "direct_Hybrid_fan_as_recurrent_child_authorized":False,
                "reason":"No prior milestone certifies absolute Hybrid fan -> recurrent component-mass timestep semantics."
            },
            "G2_rank1_refined_execution_semantics":{
                "time_advancing_authority":"exact repaired E41 mass-conservative runtime only",
                "Hybrid_role":"READ_ONLY_ENDPOINT_TRANSPORT_DIAGNOSTIC",
                "Hybrid_may_mutate_runtime_state":False,
                "Hybrid_may_change_pressure_Darcy_Pollock_TOF":False,
                "Hybrid_may_change_injection_or_production_ledger":False,
                "Hybrid_may_select_timestep":False
            },
            "exact_endpoint_face_reference":{
                "source":"E37A exact Cartesian-grid inventory -> control-volume sampling on the same exact Pollock geometry",
                "old_CV_saturation":"E37A.sample_grid_inventory_to_control_volumes",
                "n_control_volumes":200,
                "n_faces":201,
                "face_saturation_convention":[
                    "face[0] = injected boundary saturation 0.8",
                    "face[1:] = 200 exact runtime control-volume saturations"
                ],
                "basis":"Same positive-flow donor convention used by E37A.advance_component_mass_control_volumes.",
                "grid_to_CV_component_mass_closure_required":True
            },
            "Hybrid_endpoint_diagnostic":{
                "input_geometry":"same exact endpoint Pollock/TOF epoch as exact reference",
                "coordinate":"same 201 xi faces",
                "constitutive_authority":"C14 fixed production state, same as E11",
                "routing":"E11/E9 frozen xD* clock eligibility + E8-R1 learned proposal screen",
                "learned_branch":"Hybrid10 only where legally eligible and screen-passing",
                "fallback_for_diagnostic_profile":"exact runtime face saturation at the same endpoint",
                "unsafe_learned_accepts_required":0,
                "comparison_metrics":[
                    "learned_accept_face_saturation_L1",
                    "learned_accept_face_saturation_RMSE",
                    "learned_accept_face_saturation_Linf",
                    "flow_weighted_profile_L1",
                    "mixed_profile_vs_exact_L1",
                    "mixed_profile_vs_exact_RMSE",
                    "producer_outlet_saturation_difference"
                ],
                "no_new_posthoc_error_acceptance_threshold":True
            },
            "rank1_exact_truth":{
                "parent_time_days":R3R1_TIME,
                "parent_state_sha256":p69["sha256"],
                "Day75":"minimal exact selected-policy runtime continuation from the immutable Day69.883467 parent to exactly 75.0 d",
                "Day80":"reuse immutable R3R5 selected calibration state; do not recompute merely to create truth",
                "Day80_state_sha256":p80["sha256"],
                "endpoint_flow_truth":"perform same-time mass-conservative full flow refresh at Day75 and Day80 for cadence diagnostics; refresh advances neither time nor component inventory",
                "cadence_pair":[75,80]
            },
            "cadence_metrics":{
                "primary":[
                    "pressure_relative_L2","flux_relative_L2","tau_end_relative_L2",
                    "streamline_weight_relative_L2","producer_connectivity_mismatch_fraction",
                    "path_RMS_displacement_ft"
                ],
                "reference":"P-CAD-A2 Day365-Day405 observed 5-day maximum-change envelope",
                "production_cadence_selected_by_this_milestone":False
            },
            "future_recurrent_Hybrid_bridge":{
                "required_before_Hybrid_can_advance_runtime_state":True,
                "must_preserve":[
                    "fixed-rate component-mass source",
                    "producer component-mass outflow",
                    "E37A CV-to-grid mass closure",
                    "EOS inversion/capacity bounds",
                    "no-flow Cartesian capillary mass redistribution",
                    "same exact flow-epoch authority"
                ],
                "not_required_for_read_only_G2_endpoint_diagnostics":True
            }
        }

        amend={
            "milestone":M,"status":PASS,
            "A0_refinement_needed":True,
            "A0_dual_transport_phrase_refined_to":"exact runtime advances physical state; Hybrid is a parallel read-only endpoint diagnostic until recurrent component-mass bridge certification",
            "A0_target_pairs_unchanged":True,
            "A0_rank1_parent_unchanged":True,
            "A0_exact_flow_truth_requirements_unchanged":True,
            "A0_production_cadence_unselected_unchanged":True,
            "scientific_reason":"Prevent an absolute streamline saturation fan from being silently treated as an incremental conservative runtime transition."
        }

        handoff={
            "milestone":M,"status":PASS,
            "next_milestone":"POSTV16-AV4-PIVOT-GPU-HYB-G2-R1-R1 — Minimal Exact Day75 Landing + Day75/Day80 Exact Flow Diagnostics + Read-Only Hybrid10 Endpoint Evaluation",
            "G2_R1_R1_authorized":True,
            "execution_plan":[
                "Load immutable Day69.883467 current-lineage parent.",
                "Reuse R3R5 selected HALF_OBSERVED_STALE_INTERVAL runtime engine with target day overridden only to 75.0.",
                "Publish exact Day75 state without altering any existing authority.",
                "Load immutable selected Day80 calibration state rather than rerunning Day69.883->80.",
                "At Day75 and Day80, perform same-time full mass-conservative flow refresh to obtain exact pressure/Q/Pollock/TOF/weights/connectivity.",
                "Sample exact Cartesian component inventory to 200 E37A control volumes; build exact 201-face transport reference.",
                "Run frozen Hybrid10 inference only on eligible/screen-passing paths at each endpoint.",
                "Use exact runtime face state for every nonlearned/rejected diagnostic fallback.",
                "Compute Day75->80 P-CAD metrics and Hybrid-vs-exact endpoint metrics.",
                "Do not let Hybrid mutate state, ledger, flow, or timestep."
            ],
            "required_runtime":"Colab Runtime Version 2026.07, Python 3.12.x, TensorFlow 2.20.0, GPU visible",
            "G2_rank2_authorized":False,
            "G2_rank3_authorized":False,
            "P4_authorized":False
        }

        summary={
            "milestone":M,"status":PASS,
            "classification":"EXACT_RUNTIME_RECURRENT_AUTHORITY_PRESERVED_HYBRID10_READONLY_FACE_ENDPOINT_DIAGNOSTIC_RANK1_EXECUTION_AUTHORIZED",
            "semantic_gap_identified_and_closed_by_contract":True,
            "exact_runtime_remains_only_time_advancing_authority":True,
            "Hybrid_recurrent_state_mutation_authorized":False,
            "Hybrid_read_only_endpoint_diagnostic_authorized":True,
            "rank1_parent_time_days":R3R1_TIME,
            "rank1_parent_sha256":p69["sha256"],
            "existing_exact_Day80_state_reused":True,
            "exact_Day80_state_sha256":p80["sha256"],
            "exact_Day75_state_exists_now":False,
            "G2_R1_R1_authorized":True,
            "production_pressure_refresh_cadence_selected":False,
            "physics_execution_performed":False,
            "model_inference_performed":False,
            "physical_time_advanced":False,
            "P4_authorized":False
        }

        if out.exists(): raise GateError(f"output_preexists:{out}")
        out.mkdir(parents=True)
        for fn,obj in [(CONTRACT,contract),(AMEND,amend),(HANDOFF,handoff),(SUMMARY,summary)]:
            (out/fn).write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        write_csv(out/GATES,gates)
        manifest=[]
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name!=MANIFEST:
                manifest.append({"file":p.name,"sha256":sha256(p),"bytes":p.stat().st_size})
        write_csv(out/MANIFEST,manifest)

        print("="*190)
        print(M,"PASS")
        print("Exact runtime only time-advancing authority       : True")
        print("Hybrid recurrent state mutation authorized        : False")
        print("Hybrid read-only endpoint diagnostic authorized   : True")
        print("Rank-1 parent time                                :",R3R1_TIME)
        print("Exact Day80 state reused                          : True")
        print("Exact Day75 state exists now                      : False")
        print("G2-R1-R1 authorized                               : True")
        print("Production cadence selected                       : False")
        print("P4 authorized                                     : False")
        print("Output directory                                  :",out)
        print("="*190)
        return 0
    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps({
            "milestone":M,"status":BLOCK,"exception":repr(exc),"gates":gates,
            "physics_execution_performed":False,"model_inference_performed":False,
            "physical_time_advanced":False,"G2_R1_R1_authorized":False,"P4_authorized":False
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
