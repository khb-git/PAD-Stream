#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,json,subprocess
from pathlib import Path
from typing import Any
import numpy as np

M="POSTV16-AV4-PIVOT-GPU-HYB-G4-A0"
PASS="POSTV16AV4PIVOTGPUHYBG4A0_HYBRID_RECURRENT_COMPONENT_MASS_BRIDGE_DESIGN_FREEZE_PASS_NO_STATE_MUTATION"
BLOCK="POSTV16AV4PIVOTGPUHYBG4A0_TECHNICAL_OR_AUTHORITY_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="8c33a9a5b703c317198c368fc1868b80df1a5f78"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

# Cadence authority: development reference only; not a claim of optimal production cadence.
CAD_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G2_CAD_D1_EarlyLate_Cadence_Evidence_Synthesis_and_G3_Shadow_Protocol_Freeze"
CAD_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_CAD_D1_Summary.json"

# Mature mixed Hybrid/exact pilot authority.
E11_REL=Path("pilots/hybrid_dp/V16E11_R2_SGSIM_100D_CONTROLLED_STREAMLINE_PILOT")
E11_PILOT="V16E11_R2_SGSim_100Day_Streamline_Pilot.npz"
E11_PILOT_SHA="710720e933d740787868a9894fa04f90e88429c120d9f86a52b750f4c41db844"
E11_SUM="PAD_Stream_V16E11_R2_Summary.json"
E11_SUM_SHA="76336276daf4a506ea7e0880a6ad2e2852724deaf4623ca3945eafbf029e4243"

# Source authorities.
SOURCE_BLOBS={
 "PAD_Stream_Dykstra_Parsons_Hybrid_PIRNN_10Param.py":"3b56beb7d10aa92c106ad8f75f814a6206bfb1f7",
 "PAD_Stream_V16E11_R2_Packed_SG5_Serialization_Repair_and_Controlled_Hybrid_Streamline_Pilot.py":"bf89c14a3cb177fb483e233a17b72e824d31119b",
 "PAD_Stream_V16E12_R1_Route_Semantics_Reconciliation_and_Conservative_MapBack_Protocol_Freeze.py":"ed419ecd2cd23421625b655461a74bb4d9d35fb3",
 "PAD_Stream_POSTV16_AV1_B1_R1_C26_to_E37A_Component_Mass_Representation_Equivalence_Audit.py":"8d9561d7c85805b82dedc26073c4633f90eeeab6",
 "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py":"0bbf98ed89cee9128ef1d313c321f9a401b4e9f0",
 "PAD_Stream_V16E41R3R4R1_Refreshed_Flow_CFL_Alignment_Repair.py":"5f8433437ce111533338ceada922f51abb2edefe",
 "PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_CAD_D1_EarlyLate_Cadence_Evidence_Synthesis_and_G3_Shadow_Protocol_Freeze.py":"cd4c4408035672699c11d6992cf70c32ed409ee4",
}

EXPECTED_NSTREAM=1078
EXPECTED_NODES=201
EXPECTED_CVS=200
EXPECTED_ROUTE_CODE_COUNTS={10:462,12:0,20:41,30:575,99:0}

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_A0"
OUT_REL=BASE/(OUT_TOKEN+"_Hybrid_Recurrent_ComponentMass_Bridge_Design_Freeze")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
PROTOCOL=f"{OUT_TOKEN}_Bridge_Protocol.json"
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
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n")
        w.writeheader();w.writerows(rows)

def selftest():
    assert EXPECTED_NODES-1==EXPECTED_CVS
    assert sum(EXPECTED_ROUTE_CODE_COUNTS.values())==EXPECTED_NSTREAM
    assert EXPECTED_ROUTE_CODE_COUNTS[10]>0
    print("POSTV16 GPU-HYB-G4-A0 structural self-test: PASS")

def main(root:Path,drive:Path)->int:
    root=root.resolve();drive=drive.resolve()
    out=drive/OUT_REL;blocked=drive/BLOCK_REL
    gates=[];stage="preflight"
    def gate(n,c,d=None):
        ok=bool(c)
        gates.append({"stage":stage,"gate":n,"pass":ok,"detail":"" if d is None else repr(d)})
        print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"),flush=True)
        if not ok:raise GateError(n)
    try:
        print("="*190)
        print("G4-A0 — HYBRID RECURRENT COMPONENT-MASS BRIDGE DESIGN FREEZE")
        print("NO TRAINING. NO MODEL INFERENCE. NO TRANSPORT ADVANCE. NO MAPBACK. NO CANONICAL STATE MUTATION.")
        print("="*190)

        stage="repository"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_course_correction_head",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")
        for fn,blob in SOURCE_BLOBS.items():
            p=root/fn
            gate("source_present:"+fn,p.is_file(),str(p))
            actual=gt(root,"hash-object",str(p)) if p.is_file() else "missing"
            gate("source_blob_exact:"+fn,actual==blob,actual)

        stage="cadence_reference"
        cad=js(drive/CAD_REL/CAD_SUM)
        gate("five_day_cross_regime_reference",int(cad["cross_regime_conservative_reference_days"])==5,
             cad["cross_regime_conservative_reference_days"])
        gate("fifteen_day_not_production_authority",
             cad["fifteen_day_hold_status"]=="LATE_TIME_TYPICAL_ONLY_NOT_EARLY_PRODUCTION_AUTHORITY",
             cad["fifteen_day_hold_status"])
        gate("production_cadence_not_scientifically_selected",
             cad["production_pressure_refresh_cadence_selected"] is False)
        gate("prior_Hybrid_recurrent_mutation_not_authorized",
             cad["Hybrid_recurrent_state_mutation_authorized"] is False)

        stage="mature_hybrid_pilot"
        pp=drive/E11_REL/E11_PILOT;sp=drive/E11_REL/E11_SUM
        gate("E11_pilot_present",pp.is_file(),str(pp));gate("E11_pilot_SHA",sha(pp)==E11_PILOT_SHA,sha(pp))
        gate("E11_summary_present",sp.is_file(),str(sp));gate("E11_summary_SHA",sha(sp)==E11_SUM_SHA,sha(sp))
        s=js(sp)
        gate("E11_status_PASS",s.get("status")=="PASS",s.get("status"))
        gate("E11_zero_unsafe",int(s.get("unsafe_learned_proposals_accepted",-1))==0,
             s.get("unsafe_learned_proposals_accepted"))
        gate("E11_no_grid_mapback",s.get("grid_mapback_performed") is False)
        with np.load(pp,allow_pickle=False) as z:
            req=["xi","xyz_m","tau_s","tau_end_s","weights_m3_s","route_code","route_label",
                 "learned_screen_pass","saturation_100d"]
            gate("E11_required_arrays",all(k in z.files for k in req),str(z.files))
            xi=np.asarray(z["xi"]);sat=np.asarray(z["saturation_100d"],dtype=np.float64)
            route=np.asarray(z["route_code"],dtype=np.int64)
            gate("E11_xi_201",xi.shape==(EXPECTED_NODES,))
            gate("E11_saturation_shape",sat.shape==(EXPECTED_NSTREAM,EXPECTED_NODES),sat.shape)
            gate("E11_saturation_finite",np.all(np.isfinite(sat)))
            gate("E11_route_shape",route.shape==(EXPECTED_NSTREAM,),route.shape)
            counts={int(k):int(np.sum(route==k)) for k in EXPECTED_ROUTE_CODE_COUNTS}
            gate("E11_route_counts_exact",counts==EXPECTED_ROUTE_CODE_COUNTS,counts)

        stage="bridge_design_freeze"
        protocol={
          "milestone":M,
          "purpose":"Turn accepted Hybrid 201-node absolute saturation proposals into the same 200-CV component-mass state used by the authoritative recurrent E37A runtime, without allowing unconserved neural state mutation.",
          "cadence_development_reference":{
            "full_flow_refresh_reference_days":5,
            "semantics":"CONSERVATIVE_INTEGRATION_BASELINE_NOT_OPTIMALITY_CLAIM",
            "adaptive_or_longer_cadence_revisit_after_integrated_runtime_validation":True,
          },
          "authoritative_state_space":{
            "recurrent_state":"E37A 200-control-volume CO2 component mass",
            "source_Hybrid_profile":"201-node absolute transport saturation on frozen Pollock/TOF path",
            "route_labels":"provenance_and_fallback_selection_only",
            "single_common_mapback_operator":"E37A / accepted conservative mapback; no route-specific grid operator",
          },
          "hybrid_bridge_algorithm":[
            "1. Freeze exact parent E37A CV component mass M_old and current flow geometry.",
            "2. Hybrid10 may propose a 201-node absolute child saturation only on routes already eligible under the frozen E7/E8/E11 screens.",
            "3. Convert the 201-node proposal to 200-CV absolute component mass using the already-certified exact half-overlap component-mass projection: g(S)=exp(c_g*Pc(Sg))*Sg and Mhat_j=C_j*0.5*(g(S_j)+g(S_{j+1})).",
            "4. Compute the exact per-streamline component-mass budget target T = sum(M_old) + M_injected - M_produced using the existing E37A boundary-flux semantics over the common transport dt. This budget calculation is cheap and does not execute the full exact interior transport update.",
            "5. Conservatively correct the Hybrid candidate in 200-CV mass space by the minimum-change box-constrained projection onto sum(M_child)=T with 0<=M_child<=M_capacity. Saturation is never the conservation variable.",
            "6. If the conservative projection is infeasible, non-finite, violates existing route screens, or exceeds a future separately-frozen bridge-correction acceptance criterion, route that streamline to the existing exact E37A fallback. G4-A0 defines no new scientific error threshold.",
            "7. Assemble learned and exact fallback routes only in 200-CV component-mass space.",
            "8. Perform one common E37A conservative CV-to-Cartesian mapback; route labels remain provenance only.",
            "9. Apply downstream EOS/capacity/capillary machinery exactly as in the certified recurrent runtime.",
          ],
          "candidate_projection_objective":{
            "type":"BOX_CONSTRAINED_MINIMUM_CHANGE_MASS_PROJECTION",
            "recommended_execution_form":"minimize 0.5*||M-Mhat||_2^2 subject to sum(M)=T and 0<=M<=capacity",
            "deterministic_solution":"M=clip(Mhat+lambda,0,capacity), lambda solved monotonically by bisection",
            "reason":"cheap per-streamline conservative correction; preserves Hybrid spatial proposal as closely as possible while exact component-mass budget remains authoritative",
          },
          "firewalls":{
            "training_or_retraining":False,
            "checkpoint_change":False,
            "pressure_or_flow_recomputation_in_bridge":False,
            "unconserved_Hybrid_state_mutation":False,
            "saturation_space_global_rescaling":False,
            "route_specific_grid_mapback":False,
            "unsupported_cell_fill":False,
            "new_cadence_experiment":False,
          },
          "G4_A1_execution_scope":{
            "mode":"READ_ONLY_CONTROLLED_BRIDGE_EXECUTION",
            "use_existing_frozen_Hybrid_pilot_first":True,
            "execute_model_inference":False,
            "verify_201_to_200_mass_projection":True,
            "verify_box_constrained_mass_projection":True,
            "verify_per_streamline_budget_closure":True,
            "verify_capacity_feasibility":True,
            "compare_required_Hybrid_mass_correction_descriptively":True,
            "canonical_state_mutation":False,
            "production_Hybrid_mutation_authorized":False,
          }
        }
        decision={
          "milestone":M,"status":PASS,
          "main_spine_restored":True,
          "cadence_diagnostic_development_closed":True,
          "five_day_refresh_reference_for_integration":True,
          "Hybrid_recurrent_component_mass_bridge_protocol_frozen":True,
          "G4_A1_read_only_bridge_execution_authorized":True,
          "G4_A1_model_training_authorized":False,
          "G4_A1_new_model_inference_required":False,
          "Hybrid_canonical_state_mutation_authorized":False,
          "integrated_GPU_runtime_authorized":False,
          "P4_authorized":False,
        }
        summary={
          "milestone":M,"status":PASS,
          "classification":"MAIN_SPINE_HYBRID_RECURRENT_COMPONENT_MASS_BRIDGE_PROTOCOL_FROZEN_G4_A1_READONLY_EXECUTION_AUTHORIZED",
          "five_day_flow_refresh_development_reference":True,
          "production_cadence_optimality_claim":False,
          "mature_Hybrid10_pilot_streamlines":EXPECTED_NSTREAM,
          "Hybrid10_accepted_paths":EXPECTED_ROUTE_CODE_COUNTS[10],
          "exact_R2_fallback_paths":EXPECTED_ROUTE_CODE_COUNTS[20],
          "full_physics_fallback_paths":EXPECTED_ROUTE_CODE_COUNTS[30],
          "source_profile_nodes":EXPECTED_NODES,
          "target_component_mass_CVs":EXPECTED_CVS,
          "conservation_variable":"CO2_COMPONENT_MASS",
          "201_to_200_component_mass_projection_reused":True,
          "new_Hybrid_model_training_required":False,
          "new_Hybrid_model_inference_required_for_G4_A1":False,
          "G4_A1_read_only_bridge_execution_authorized":True,
          "Hybrid_canonical_state_mutation_authorized":False,
          "integrated_GPU_runtime_authorized":False,
          "P4_authorized":False,
        }

        stage="publication"
        gate("output_absent",not out.exists(),str(out));out.mkdir(parents=True)
        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        (out/PROTOCOL).write_text(json.dumps(protocol,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        (out/DECISION).write_text(json.dumps(decision,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        write_csv(out/GATES,gates)
        manifest=[{"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size}
                  for p in sorted(out.iterdir()) if p.is_file() and p.name!=MANIFEST]
        write_csv(out/MANIFEST,manifest)

        print("="*190);print(M,"PASS")
        print("Main spine restored                         : True")
        print("5-day flow refresh integration reference    : True")
        print("Hybrid10 accepted pilot paths               :",EXPECTED_ROUTE_CODE_COUNTS[10])
        print("201-node -> 200-CV mass bridge reused       : True")
        print("Conservation variable                       : CO2 component mass")
        print("G4-A1 read-only bridge execution authorized : True")
        print("Hybrid canonical state mutation             : False")
        print("Integrated GPU runtime authorized           : False")
        print("="*190)
        return 0
    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps({
          "milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),"gates":gates,
          "G4_A1_read_only_bridge_execution_authorized":False,
          "Hybrid_canonical_state_mutation_authorized":False,
          "integrated_GPU_runtime_authorized":False,
          "P4_authorized":False,
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
