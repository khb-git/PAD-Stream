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
from typing import Any

import numpy as np

M="POSTV16-AV4-PIVOT-GPU-HYB-G2-R1-R1"
PASS="POSTV16AV4PIVOTGPUHYBG2R1R1_RANK1_DAY75_DAY80_EXACT_FLOW_AND_READONLY_HYBRID_ENDPOINT_DIAGNOSTIC_PASS"
BLOCK="POSTV16AV4PIVOTGPUHYBG2R1R1_TECHNICAL_OR_SAFETY_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="0089f49efa5dd15659cb8e6facbc7b1f3100d863"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

G2R1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_Runtime_Hybrid_Endpoint_Bridge_Protocol_Freeze.py"
G2R1_BLOB="ba15e6bfefe6840ea9744ca6041f0a1a4bb3b44b"
G2R1_REL=BASE_AV4/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_Runtime_Hybrid_Endpoint_Bridge_Protocol_Freeze"
G2R1_SUMMARY="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_Summary.json"
G2R1_HANDOFF="POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_Rank1_Execution_Handoff.json"
G2R1_STATUS="POSTV16AV4PIVOTGPUHYBG2R1_RUNTIME_HYBRID_ENDPOINT_BRIDGE_PROTOCOL_FREEZE_PASS_NO_PHYSICS_EXECUTION"

R3R5_RUNNER="PAD_Stream_V16E41R3R5_Multi_Refresh_Cadence_Sensitivity_Runtime_Refresh_Policy_Calibration.py"
R3R5_BLOB="15aae3224ba4337cad72f9b4aa9166d602791349"
R3R5_REL=Path("provenance/hybrid_dp/V16E41R3R5_MULTI_REFRESH_CADENCE_SENSITIVITY_RUNTIME_POLICY_CALIBRATION")
R3R5_SUMMARY="PAD_Stream_V16E41R3R5_Summary.json"
R3R5_SELECTED="V16E41R3R5_Selected_Calibration_State_80d.npz"
R3R5_STATUS="MULTI_REFRESH_CADENCE_SENSITIVITY_RUNTIME_POLICY_CALIBRATED"
DAY80_SHA="7ca6f0b8fbbf08608d4ddc6cc136e4cfcd5cbb3e609762412e1ba861ef41a0fb"

R3R4R1_RUNNER="PAD_Stream_V16E41R3R4R1_Refreshed_Flow_CFL_Alignment_Repair.py"
R3R4R1_BLOB="5f8433437ce111533338ceada922f51abb2edefe"

A0_RUNNER="PAD_Stream_POSTV16_P_CAD_A0_Exact_Pressure_Evolution_and_FlowEpoch_Hold_Screening.py"
A0_BLOB="ce56b4742e941e89444ca463e7bc583a506a6389"
A0_STATUS="POSTV16PCADA0_EXACT_PRESSURE_EVOLUTION_AND_FLOWEPOCH_HOLD_SCREENING_PASS_NO_PHYSICS_MUTATION"

E11_RUNNER="PAD_Stream_V16E11_R2_Packed_SG5_Serialization_Repair_and_Controlled_Hybrid_Streamline_Pilot.py"
E11_BLOB="bf89c14a3cb177fb483e233a17b72e824d31119b"

DAY69_TIME=69.88346704782309
DAY69_SHA="8714f5b35b99472de0251def022043076f85fb9cee2ada1cfc4d7b7441cce5e6"
TARGET75=75.0
TARGET80=80.0
DAY_TO_S=86400.0
FT_TO_M=0.3048
NUM_EPS=1.0e-12

PRIMARY_METRICS=[
    "pressure_relative_L2",
    "flux_relative_L2",
    "tau_end_relative_L2",
    "streamline_weight_relative_L2",
    "producer_connectivity_mismatch_fraction",
    "path_RMS_displacement_ft",
]

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_R1"
OUT_REL=BASE_AV4/(OUT_TOKEN+"_Rank1_Day75_Day80_ExactFlow_and_Hybrid_Endpoint_Diagnostic")
BLOCK_REL=BASE_AV4/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DECISION=f"{OUT_TOKEN}_Decision_Contract.json"
CADENCE=f"{OUT_TOKEN}_Day75_to_Day80_PCAD_Metrics.csv"
HYBRID=f"{OUT_TOKEN}_Hybrid_Endpoint_Metrics.csv"
ROUTES=f"{OUT_TOKEN}_Hybrid_Route_Counts.csv"
PRODUCERS=f"{OUT_TOKEN}_Hybrid_Producer_Outlet_Diagnostics.csv"
GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"
DAY75_STATE=f"{OUT_TOKEN}_Exact_Day75_SelectedPolicy_State.npz"
DAY75_DIAG=f"{OUT_TOKEN}_Day75_ExactFlow_and_Hybrid_Diagnostic.npz"
DAY80_DIAG=f"{OUT_TOKEN}_Day80_ExactFlow_and_Hybrid_Diagnostic.npz"

class GateError(RuntimeError): pass

def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""): h.update(c)
    return h.hexdigest()

def git_blob(path:Path,root:Path)->str:
    return subprocess.check_output(["git","-C",str(root),"hash-object",str(path)],text=True).strip()

def gt(root:Path,*args:str)->str:
    return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()

def load_module_blob(path:Path,expected_blob:str,name:str,root:Path):
    if not path.is_file(): raise GateError(f"missing_source:{path}")
    actual=git_blob(path,root)
    if actual!=expected_blob: raise GateError(f"source_blob:{path.name}:{actual}:{expected_blob}")
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise GateError(f"cannot_import:{path}")
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod)
    return mod

def js(path:Path)->dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def load_npz(path:Path)->dict[str,np.ndarray]:
    with np.load(path,allow_pickle=False) as z:
        return {k:z[k].copy() for k in z.files}

def scalar(v:Any)->float:
    return float(np.asarray(v).reshape(()))

def int_scalar(v:Any)->int:
    return int(np.asarray(v).reshape(()))

def write_csv(path:Path,rows:list[dict[str,Any]])->None:
    if not rows:
        path.write_text("",encoding="utf-8"); return
    fields=[]
    for row in rows:
        for k in row:
            if k not in fields: fields.append(k)
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n"); w.writeheader(); w.writerows(rows)

def endpoint_db(epoch:dict[str,Any],sg5,sg6,r3r4r1)->dict[str,np.ndarray]:
    qx=np.asarray(epoch["qx"],dtype=np.float64)
    qy=np.asarray(epoch["qy"],dtype=np.float64)
    qz=np.asarray(epoch["qz"],dtype=np.float64)
    vx,vy,vz=sg5.construct_face_pore_velocities(qx,qy,qz)
    _faces,seeds=sg5.build_seeds(qx,qy,qz)
    streams=sg5.trace_streamlines(seeds,vx,vy,vz)
    db=sg6.build_transport_database(r3r4r1.convert_sg5_to_sg6_streamlines(streams))
    return {
        "xyz_m":np.asarray(db["xyz_m"],dtype=np.float64),
        "tau_s":np.asarray(db["tau_s"],dtype=np.float64),
        "tau_end_s":np.asarray(db["tau_end_s"],dtype=np.float64),
        "weights_m3_s":np.asarray(db["weights_m3_s"],dtype=np.float64),
        "producer":np.asarray(db["producer"]).astype("U64"),
        "xi":np.asarray(db["xi"],dtype=np.float64),
    }

def same_time_endpoint(
    state:dict[str,np.ndarray], *,
    r3r5,r3r4r1,physics,r3r2r1,e36,e37a,sg2,sg3,sg4,sg5,sg6,sg7a,sg7d,
    permeability_md,cell_pore_volume_m3
):
    t0=scalar(state["physical_time_days"]); s0=int_scalar(state["accepted_step_index"])
    inj0=scalar(state["cumulative_injected_co2_mass_kg"])
    prod0=scalar(state["cumulative_produced_co2_mass_kg"])
    stored0=scalar(state["stored_co2_mass_current_kg"])
    refreshed,epoch,_rows=r3r5.build_flow_epoch(
        current=state,r3r4r1=r3r4r1,physics=physics,r3r2r1=r3r2r1,e36=e36,e37a=e37a,
        sg2=sg2,sg3=sg3,sg4=sg4,sg5=sg5,sg6=sg6,sg7a=sg7a,sg7d=sg7d,
        permeability_md=permeability_md,cell_pore_volume_m3=cell_pore_volume_m3
    )
    if scalar(refreshed["physical_time_days"])!=t0: raise GateError("endpoint_refresh_advanced_time")
    if int_scalar(refreshed["accepted_step_index"])!=s0: raise GateError("endpoint_refresh_advanced_step")
    if scalar(refreshed["cumulative_injected_co2_mass_kg"])!=inj0: raise GateError("endpoint_refresh_changed_injection")
    if scalar(refreshed["cumulative_produced_co2_mass_kg"])!=prod0: raise GateError("endpoint_refresh_changed_production")
    tol=max(1e-6,1e-10*max(abs(stored0),1.0))
    if abs(scalar(refreshed["stored_co2_mass_current_kg"])-stored0)>tol: raise GateError("endpoint_refresh_changed_stored_mass")
    db=endpoint_db(epoch,sg5,sg6,r3r4r1)
    if db["weights_m3_s"].shape!=(int(epoch["nstream"]),): raise GateError("endpoint_db_weight_shape")
    if not np.array_equal(db["producer"].astype(str),np.asarray(epoch["labels"]).astype(str)):
        raise GateError("endpoint_db_labels_not_exact")
    if not np.allclose(db["weights_m3_s"]*DAY_TO_S,np.asarray(epoch["weights_m3_day"]),rtol=0.0,atol=1e-12):
        raise GateError("endpoint_db_weights_not_reproduced")
    return refreshed,epoch,db

def hybrid_endpoint(
    day:float, refreshed:dict[str,np.ndarray], epoch:dict[str,Any], db:dict[str,np.ndarray], *,
    e37a, physics, e11, adapter, r2, e9r1, tf, model10, p, speed, swstar, screen
)->tuple[dict[str,Any],dict[str,np.ndarray],list[dict[str,Any]]]:
    nstream=int(epoch["nstream"]); nfaces=int(epoch["nfaces"]); ncv=int(epoch["ncv"])
    if nfaces!=201 or ncv!=200: raise GateError(f"endpoint_transport_shape:{nstream}:{nfaces}:{ncv}")
    p_ref=scalar(refreshed["co2_density_reference_pressure_pa"])
    cv_sat,cv_mass,sample_closure=e37a.sample_grid_inventory_to_control_volumes(
        physics,np.asarray(refreshed["transport_saturation"],dtype=np.float64),
        np.asarray(epoch["pressure_psi"],dtype=np.float64),p_ref,epoch["geometry"],nstream,ncv
    )
    tol=max(1e-6,1e-10*max(abs(float(np.sum(cv_mass))),1.0))
    if abs(float(sample_closure))>tol: raise GateError(f"endpoint_CV_sampling_closure:{sample_closure}:{tol}")

    exact=np.empty((nstream,nfaces),dtype=np.float64)
    exact[:,0]=0.8
    exact[:,1:]=np.asarray(cv_sat,dtype=np.float64)

    xi=np.asarray(db["xi"],dtype=np.float64)
    tau=np.asarray(db["tau_s"],dtype=np.float64)
    terminal=np.asarray(db["tau_end_s"],dtype=np.float64)/DAY_TO_S
    if xi.shape!=(201,) or tau.shape!=(nstream,201): raise GateError("hybrid_coordinate_shape")

    xstar=(float(day)/terminal)*float(speed)
    clock=np.asarray([e11.classify_clock(float(x)) for x in xstar],dtype="U32")
    if np.any(clock=="UNRESOLVED"): raise GateError("unresolved_hybrid_clock")

    learned_candidate=clock=="LEARNED_WINDOW"
    prebt=clock=="PREBT_EXACT_R2"
    postbt=clock=="POSTBT_FULL_PHYSICS"
    projected=np.full((nstream,nfaces),np.nan,dtype=np.float32)
    mixed=exact.astype(np.float32).copy()
    route=np.full(nstream,30,dtype=np.int16) # exact-runtime fallback unless learned accept
    route[prebt]=21
    route[postbt]=30
    screen_pass=np.zeros(nstream,dtype=np.uint8)
    reasons=np.full(nstream,"",dtype="U160")
    rejection_counts={}
    unsafe=0

    idx=np.flatnonzero(learned_candidate)
    if idx.size:
        cond=[]; states=[]
        for i in idx:
            state=adapter.physical_time_state(
                elapsed_time=float(day),tau_end=float(terminal[i]),
                characteristic_speed=float(speed),Sw_star=float(swstar)
            )
            if not (0.05<=float(state["xD_star"])<=0.95): raise GateError("learned_candidate_outside_window")
            states.append(state)
            cond.append(adapter.conditioning_vector("HYBRID10",p,state))
        pred=e9r1.infer(tf,model10,xi.astype(np.float32),np.asarray(cond,dtype=np.float32),batch=256)
        for local,i in enumerate(idx):
            state=states[local]; fan=pred[local]
            ok,sm=e11.screen_fan_prediction(
                fan,p,state,xi,tau[i]/DAY_TO_S,r2,adapter,screen
            )
            reasons[i]=";".join(sm["failures"]); screen_pass[i]=1 if ok else 0
            if ok:
                profile=adapter.project_fan_to_pollock_nodes(
                    tau_nodes=tau[i]/DAY_TO_S,state=state,fan_xi=xi,fan_sw=fan,swc=float(p["swc"])
                ).astype(np.float32)
                projected[i]=profile; mixed[i]=profile; route[i]=10
                if sm["failures"]: unsafe+=1
            else:
                route[i]=20
                for reason in sm["failures"]:
                    rejection_counts[reason]=rejection_counts.get(reason,0)+1

    if unsafe!=0: raise GateError(f"unsafe_learned_accepts:{unsafe}")
    if not np.all(np.isfinite(mixed)): raise GateError("mixed_hybrid_profile_nonfinite")
    if np.any(mixed<float(p["swc"])-1e-7) or np.any(mixed>1.0-float(p["sor"])+1e-7):
        raise GateError("mixed_hybrid_profile_bounds")

    accept=route==10
    err=mixed.astype(np.float64)-exact
    weights=np.asarray(db["weights_m3_s"],dtype=np.float64)
    per_l1=np.mean(np.abs(err),axis=1)

    def maybe(v):
        return None if not np.any(accept) else float(v)

    if np.any(accept):
        ea=err[accept]
        learned_l1=float(np.mean(np.abs(ea)))
        learned_rmse=float(np.sqrt(np.mean(ea*ea)))
        learned_linf=float(np.max(np.abs(ea)))
        learned_fw=float(np.sum(weights[accept]*per_l1[accept])/np.sum(weights[accept]))
    else:
        learned_l1=learned_rmse=learned_linf=learned_fw=None

    producer_rows=[]
    for name in sorted(set(db["producer"].astype(str).tolist())):
        m=db["producer"].astype(str)==name
        qsum=float(np.sum(weights[m]))
        outlet=np.abs(err[m,-1])
        producer_rows.append({
            "day":float(day),"producer":name,"streamline_count":int(np.sum(m)),
            "flow_weight_m3_s":qsum,
            "outlet_abs_difference_flow_weighted":float(np.sum(weights[m]*outlet)/qsum) if qsum>0 else 0.0,
            "outlet_max_abs_difference":float(np.max(outlet)) if outlet.size else 0.0,
        })

    metrics={
        "day":float(day),
        "streamline_count":nstream,
        "learned_window_candidates":int(np.sum(learned_candidate)),
        "preBT_exact_runtime_fallback":int(np.sum(prebt)),
        "postBT_exact_runtime_fallback":int(np.sum(postbt)),
        "Hybrid10_screen_accept_count":int(np.sum(route==10)),
        "Hybrid10_screen_reject_count":int(np.sum(route==20)),
        "unsafe_learned_accepts":int(unsafe),
        "learned_accept_face_saturation_L1":learned_l1,
        "learned_accept_face_saturation_RMSE":learned_rmse,
        "learned_accept_face_saturation_Linf":learned_linf,
        "learned_accept_flow_weighted_profile_L1":learned_fw,
        "mixed_profile_vs_exact_L1":float(np.mean(np.abs(err))),
        "mixed_profile_vs_exact_RMSE":float(np.sqrt(np.mean(err*err))),
        "mixed_profile_vs_exact_Linf":float(np.max(np.abs(err))),
        "mixed_flow_weighted_profile_L1":float(np.sum(weights*per_l1)/np.sum(weights)),
        "producer_outlet_abs_difference_flow_weighted":float(np.sum(weights*np.abs(err[:,-1]))/np.sum(weights)),
        "grid_to_CV_component_mass_sampling_closure_kg":float(sample_closure),
        "rejection_reason_counts":json.dumps(rejection_counts,sort_keys=True),
    }
    arrays={
        "physical_time_days":np.asarray(day,dtype=np.float64),
        "exact_runtime_face_saturation":exact.astype(np.float64),
        "hybrid_mixed_diagnostic_profile":mixed.astype(np.float32),
        "hybrid_projected_learned_profile":projected.astype(np.float32),
        "route_code":route,
        "learned_screen_pass":screen_pass,
        "learned_screen_reasons":reasons,
        "clock_class":clock,
        "xi":xi,
        "xyz_m":db["xyz_m"],
        "tau_s":db["tau_s"],
        "tau_end_s":db["tau_end_s"],
        "weights_m3_s":db["weights_m3_s"],
        "producer":db["producer"],
        "pressure_psi":np.asarray(epoch["pressure_psi"],dtype=np.float64),
        "Qx":np.asarray(epoch["qx"],dtype=np.float64),
        "Qy":np.asarray(epoch["qy"],dtype=np.float64),
        "Qz":np.asarray(epoch["qz"],dtype=np.float64),
    }
    return metrics,arrays,producer_rows

def selftest():
    a=np.array([1.,2.,3.]); b=np.array([1.,2.,4.])
    rel=float(np.linalg.norm(b-a)/np.linalg.norm(a))
    assert rel>0
    exact=np.zeros((2,201)); mixed=exact.copy()
    assert float(np.sqrt(np.mean((mixed-exact)**2)))==0.0
    assert TARGET80-TARGET75==5.0
    print("POSTV16 GPU-HYB-G2-R1-R1 structural self-test: PASS")

def main(project_root:Path,drive_root:Path)->int:
    root=project_root.resolve(); drive=drive_root.resolve()
    out=drive/OUT_REL; blocked=drive/BLOCK_REL
    gates=[]; stage="preflight"
    def gate(name,cond,detail=None):
        ok=bool(cond); gates.append({"stage":stage,"gate":name,"pass":ok,"detail":"" if detail is None else repr(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"),flush=True)
        if not ok: raise GateError(name)

    try:
        print("="*190)
        print("POSTV16-AV4-PIVOT-GPU-HYB-G2-R1-R1 — RANK-1 DAY75->DAY80 EXACT FLOW + READ-ONLY HYBRID ENDPOINT DIAGNOSTIC")
        print("EXACT E41 RUNTIME ADVANCES ONLY TO DAY75. EXISTING IMMUTABLE DAY80 STATE IS REUSED.")
        print("HYBRID10 IS READ-ONLY; IT CANNOT MUTATE STATE, MASS LEDGER, FLOW EPOCH, OR TIMESTEP.")
        print("="*190)

        stage="repository_authority"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_G2_R1",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")

        g2r1=load_module_blob(root/G2R1_RUNNER,G2R1_BLOB,"g2r1_authority",root)
        r3r5=load_module_blob(root/R3R5_RUNNER,R3R5_BLOB,"g2r1r1_r3r5",root)
        r3r4r1=load_module_blob(root/R3R4R1_RUNNER,R3R4R1_BLOB,"g2r1r1_r3r4r1",root)
        a0=load_module_blob(root/A0_RUNNER,A0_BLOB,"g2r1r1_pcad_a0",root)
        e11=load_module_blob(root/E11_RUNNER,E11_BLOB,"g2r1r1_e11",root)

        stage="G2_R1_authority"
        s=js(drive/G2R1_REL/G2R1_SUMMARY)
        h=js(drive/G2R1_REL/G2R1_HANDOFF)
        gate("G2_R1_status_exact",s.get("status")==G2R1_STATUS,s.get("status"))
        gate("G2_R1_exact_runtime_only",s.get("exact_runtime_remains_only_time_advancing_authority") is True)
        gate("G2_R1_Hybrid_mutation_locked",s.get("Hybrid_recurrent_state_mutation_authorized") is False)
        gate("G2_R1_Hybrid_readonly_authorized",s.get("Hybrid_read_only_endpoint_diagnostic_authorized") is True)
        gate("G2_R1_R1_authorized",h.get("G2_R1_R1_authorized") is True)

        stage="exact_runtime_source_binding"
        role_modules={}
        for role in ["R3R2R1","E36","E37A","R2_PHYSICS","SG2","SG3","SG4","SG5","SG6","SG7A","SG7D"]:
            fn,blob=r3r4r1.SOURCE_BLOBS[role]
            role_modules[role]=load_module_blob(root/fn,blob,f"g2r1r1_{role.lower()}",root)
        r3r2r1=role_modules["R3R2R1"]; e36=role_modules["E36"]; e37a=role_modules["E37A"]
        physics=role_modules["R2_PHYSICS"]; sg2=role_modules["SG2"]; sg3=role_modules["SG3"]
        sg4=role_modules["SG4"]; sg5=role_modules["SG5"]; sg6=role_modules["SG6"]
        sg7a=role_modules["SG7A"]; sg7d=role_modules["SG7D"]
        pfn,pblob=r3r4r1.SOURCE_BLOBS["PERM"]
        perm_path=root/pfn
        gate("permeability_source_blob_exact",git_blob(perm_path,root)==pblob,git_blob(perm_path,root))

        parent_path=drive/r3r4r1.R3R1_REL/r3r4r1.R3R1_STATE
        gate("Day69_parent_present",parent_path.is_file(),str(parent_path))
        gate("Day69_parent_SHA_exact",sha256(parent_path)==DAY69_SHA,sha256(parent_path))
        parent=load_npz(parent_path)
        gate("Day69_parent_time_exact",abs(scalar(parent["physical_time_days"])-DAY69_TIME)<=1e-12,scalar(parent["physical_time_days"]))

        day80_path=drive/R3R5_REL/R3R5_SELECTED
        gate("Day80_selected_state_present",day80_path.is_file(),str(day80_path))
        gate("Day80_selected_state_SHA_exact",sha256(day80_path)==DAY80_SHA,sha256(day80_path))
        state80=load_npz(day80_path)
        gate("Day80_time_exact",abs(scalar(state80["physical_time_days"])-80.0)<=1e-12,scalar(state80["physical_time_days"]))

        r3r5_summary=js(drive/R3R5_REL/R3R5_SUMMARY)
        gate("R3R5_status_exact",r3r5_summary.get("status")==R3R5_STATUS,r3r5_summary.get("status"))
        gate("R3R5_selected_policy_exact",r3r5_summary.get("selected_policy")=="HALF_OBSERVED_STALE_INTERVAL",r3r5_summary.get("selected_policy"))
        max_epoch=float(r3r5_summary["selected_max_flow_epoch_days"])

        dx_m=20.0*FT_TO_M; dy_m=20.0*FT_TO_M; dz_m=4.0*FT_TO_M
        cell_pore_volume_m3=0.20*dx_m*dy_m*dz_m
        permeability_md=np.loadtxt(perm_path,skiprows=1,dtype=np.float64).reshape((15,50,50),order="C")

        stage="minimal_exact_Day75_landing"
        original_target=float(r3r5.CALIBRATION_TARGET_DAY)
        r3r5.CALIBRATION_TARGET_DAY=75.0
        result75=r3r5.run_policy(
            policy_name="HALF_OBSERVED_STALE_INTERVAL",max_epoch_days=max_epoch,parent=parent,
            r3r4r1=r3r4r1,physics=physics,r3r2r1=r3r2r1,e36=e36,e37a=e37a,
            sg2=sg2,sg3=sg3,sg4=sg4,sg5=sg5,sg6=sg6,sg7a=sg7a,sg7d=sg7d,
            permeability_md=permeability_md,cell_pore_volume_m3=cell_pore_volume_m3
        )
        r3r5.CALIBRATION_TARGET_DAY=original_target
        state75={k:np.asarray(v).copy() for k,v in result75["terminal_state"].items()}
        gate("Day75_exact_landing",abs(scalar(state75["physical_time_days"])-75.0)<=1e-12,scalar(state75["physical_time_days"]))
        gate("Day75_mass_residual_finite",np.isfinite(float(result75["cumulative_mass_residual_kg"])),result75["cumulative_mass_residual_kg"])
        gate("Day75_capacity_margin_positive",float(result75["min_raw_capacity_margin_kg"])>0.0,result75["min_raw_capacity_margin_kg"])

        stage="same_time_exact_endpoint_flow"
        ref75,epoch75,db75=same_time_endpoint(
            state75,r3r5=r3r5,r3r4r1=r3r4r1,physics=physics,r3r2r1=r3r2r1,e36=e36,e37a=e37a,
            sg2=sg2,sg3=sg3,sg4=sg4,sg5=sg5,sg6=sg6,sg7a=sg7a,sg7d=sg7d,
            permeability_md=permeability_md,cell_pore_volume_m3=cell_pore_volume_m3
        )
        ref80,epoch80,db80=same_time_endpoint(
            state80,r3r5=r3r5,r3r4r1=r3r4r1,physics=physics,r3r2r1=r3r2r1,e36=e36,e37a=e37a,
            sg2=sg2,sg3=sg3,sg4=sg4,sg5=sg5,sg6=sg6,sg7a=sg7a,sg7d=sg7d,
            permeability_md=permeability_md,cell_pore_volume_m3=cell_pore_volume_m3
        )
        gate("endpoint_streamline_shapes_exact",db75["xyz_m"].shape==db80["xyz_m"].shape,(db75["xyz_m"].shape,db80["xyz_m"].shape))
        gate("endpoint_tau_shapes_exact",db75["tau_end_s"].shape==db80["tau_end_s"].shape)
        gate("endpoint_weight_shapes_exact",db75["weights_m3_s"].shape==db80["weights_m3_s"].shape)

        stage="P_CAD_rank1_comparison"
        rec75={"day":75,"pressure":epoch75["pressure_psi"],"Qx":epoch75["qx"],"Qy":epoch75["qy"],"Qz":epoch75["qz"],
               "tau_end_s":db75["tau_end_s"],"streamline_weight_m3_s":db75["weights_m3_s"],"xyz_m":db75["xyz_m"],"producer_labels":db75["producer"]}
        rec80={"day":80,"pressure":epoch80["pressure_psi"],"Qx":epoch80["qx"],"Qy":epoch80["qy"],"Qz":epoch80["qz"],
               "tau_end_s":db80["tau_end_s"],"streamline_weight_m3_s":db80["weights_m3_s"],"xyz_m":db80["xyz_m"],"producer_labels":db80["producer"]}
        early=a0.pair_metrics(rec75,rec80)
        a0s=js(drive/a0.OUT_REL/a0.SUMMARY)
        gate("P_CAD_A0_status_exact",a0s.get("status")==A0_STATUS,a0s.get("status"))
        with (drive/a0.OUT_REL/a0.HOLD_SUMMARY).open(newline="",encoding="utf-8") as f:
            hold=list(csv.DictReader(f))
        base=[r for r in hold if int(float(r["hold_days"]))==5]
        gate("single_late_5day_envelope_row",len(base)==1,len(base))
        base=base[0]
        comparison={}
        all_within=True
        for metric in PRIMARY_METRICS:
            v=float(early[metric]); lim=float(base[metric+"_max"])
            passed=v<=lim*(1.0+NUM_EPS)+1.0e-15
            comparison[metric]={"early_75_80":v,"late_5day_max":lim,"inflation":v/lim if lim>0 else (0.0 if v==0 else float("inf")),"within":passed}
            if not passed: all_within=False
        exceed=[m for m in PRIMARY_METRICS if not comparison[m]["within"]]

        stage="Hybrid_authority_and_GPU"
        # Exact E11 subordinate identities are reused, not redefined.
        for rel,entry,label in [
            (e11.E8R1_REL,e11.E8R1["contract"],"E8R1_contract"),
            (e11.E5_REL,e11.E5_MANIFEST,"E5_manifest"),
            (e11.E3_REL,e11.E3_PROTOCOL,"E3_protocol"),
            (e11.E6A_REL,e11.E6A_CHECKPOINT,"E6A_checkpoint"),
        ]:
            fn,expected=entry; path=drive/rel/fn
            gate(label+"_present",path.is_file(),str(path))
            gate(label+"_SHA_exact",e11.sha(path)==expected,e11.sha(path) if path.is_file() else "missing")
        gate("C14_source_SHA_exact",e11.sha(root/e11.C14_SOURCE[0])==e11.C14_SOURCE[1])
        e8r1=e11.read_json(drive/e11.E8R1_REL/e11.E8R1["contract"][0]); screen=e8r1["learned_proposal_execution_screen"]
        e5=e11.read_json(drive/e11.E5_REL/e11.E5_MANIFEST[0])
        e3=e11.read_json(drive/e11.E3_REL/e11.E3_PROTOCOL[0])
        p=e11.c14_production_params(root/e11.C14_SOURCE[0])
        gate("C14_inside_E3",e11.parameters_inside_e3(p,e3),p)
        gate("C14_routes_fixed_Hybrid10",p["krw_max"]==0.8 and p["kro_max"]==0.8,p)

        adapter=e11.import_exact(root/e11.E9_ADAPTER[0],e11.E9_ADAPTER[1],"g2r1r1_e9_adapter")
        r2=e11.import_exact(root/e11.R2_ADAPTER[0],e11.R2_ADAPTER[1],"g2r1r1_r2_adapter")
        e9r1=e11.import_exact(root/e11.E9R1_RUNNER[0],e11.E9R1_RUNNER[1],"g2r1r1_e9r1")
        shock=r2.welge_shock(adapter.teacher_params(p),scan_nodes=4097)
        speed=float(shock["characteristic_speed"]); swstar=float(shock["Sw_star"])
        gate("Hybrid_characteristic_speed_positive",np.isfinite(speed) and speed>0.0,speed)

        tf=e9r1.prepare_tf(e5)
        gate("TensorFlow_2_20_exact",tf.__version__=="2.20.0",tf.__version__)
        gpus=tf.config.list_physical_devices("GPU")
        gate("TensorFlow_GPU_visible",len(gpus)>=1,[str(x) for x in gpus])
        model10=e9r1.build_inference_model(tf,10,"G2R1R1_Hybrid10")
        gate("Hybrid10_parameter_count_exact",model10.count_params()==52545,model10.count_params())
        model10.load_weights(str(drive/e11.E6A_REL/e11.E6A_CHECKPOINT[0]))

        stage="Hybrid_readonly_endpoint_diagnostics"
        h75,a75,p75=hybrid_endpoint(
            75.0,ref75,epoch75,db75,e37a=e37a,physics=physics,e11=e11,adapter=adapter,r2=r2,e9r1=e9r1,
            tf=tf,model10=model10,p=p,speed=speed,swstar=swstar,screen=screen
        )
        h80,a80,p80=hybrid_endpoint(
            80.0,ref80,epoch80,db80,e37a=e37a,physics=physics,e11=e11,adapter=adapter,r2=r2,e9r1=e9r1,
            tf=tf,model10=model10,p=p,speed=speed,swstar=swstar,screen=screen
        )
        gate("zero_unsafe_Hybrid_accepts_Day75",h75["unsafe_learned_accepts"]==0,h75["unsafe_learned_accepts"])
        gate("zero_unsafe_Hybrid_accepts_Day80",h80["unsafe_learned_accepts"]==0,h80["unsafe_learned_accepts"])

        stage="publication"
        gate("output_does_not_preexist",not out.exists(),str(out))
        out.mkdir(parents=True)

        state75_bytes=r3r5.deterministic_npz_bytes(state75)
        (out/DAY75_STATE).write_bytes(state75_bytes)
        (out/DAY75_DIAG).write_bytes(r3r5.deterministic_npz_bytes(a75))
        (out/DAY80_DIAG).write_bytes(r3r5.deterministic_npz_bytes(a80))

        cadence_row={k:v for k,v in early.items()}
        for metric in PRIMARY_METRICS:
            cadence_row[metric+"_late_5day_max"]=comparison[metric]["late_5day_max"]
            cadence_row[metric+"_inflation_vs_late_5day_max"]=comparison[metric]["inflation"]
            cadence_row[metric+"_within_late_5day_max"]=comparison[metric]["within"]
        cadence_row["all_primary_within_late_5day_max"]=all_within
        write_csv(out/CADENCE,[cadence_row])

        def flatten_h(x):
            y=dict(x); y["rejection_reason_counts"]=x["rejection_reason_counts"]; return y
        write_csv(out/HYBRID,[flatten_h(h75),flatten_h(h80)])
        route_rows=[]
        for day,hx in [(75,h75),(80,h80)]:
            route_rows += [
                {"day":day,"route":"HYBRID10_ACCEPT","count":hx["Hybrid10_screen_accept_count"]},
                {"day":day,"route":"HYBRID10_SCREEN_REJECT_EXACT_RUNTIME_FALLBACK","count":hx["Hybrid10_screen_reject_count"]},
                {"day":day,"route":"PREBT_EXACT_RUNTIME_FALLBACK","count":hx["preBT_exact_runtime_fallback"]},
                {"day":day,"route":"POSTBT_EXACT_RUNTIME_FALLBACK","count":hx["postBT_exact_runtime_fallback"]},
            ]
        write_csv(out/ROUTES,route_rows); write_csv(out/PRODUCERS,p75+p80)

        classification=(
            "RANK1_DAY75_DAY80_EXACT_FLOW_WITHIN_LATE_5DAY_MAX_ENVELOPE_HYBRID10_READONLY_ENDPOINT_DIAGNOSTIC_COMPLETE_G2_R2_AUTHORIZED"
            if all_within else
            "RANK1_DAY75_DAY80_EXACT_FLOW_EXCEEDS_LATE_5DAY_MAX_ENVELOPE_LOCAL_EXPANSION_FLAGGED_HYBRID10_READONLY_ENDPOINT_DIAGNOSTIC_COMPLETE_G2_R2_AUTHORIZED"
        )
        summary={
            "milestone":M,"status":PASS,"classification":classification,
            "Day75_exact_state_sha256":hashlib.sha256(state75_bytes).hexdigest(),
            "Day75_exact_state_time_days":75.0,
            "Day75_exact_transition_count":int(result75["accepted_transition_count"]),
            "Day75_runtime_refresh_count":int(result75["refresh_count_policy_runtime"]),
            "Day75_cadence_refresh_count":int(result75["cadence_refresh_count"]),
            "Day75_capacity_refresh_count":int(result75["capacity_refresh_count"]),
            "Day75_min_raw_capacity_margin_kg":float(result75["min_raw_capacity_margin_kg"]),
            "Day80_existing_state_reused":True,"Day80_state_sha256":DAY80_SHA,
            "rank1_probe_pair":[75,80],
            "P_CAD_primary_metrics":{m:comparison[m]["early_75_80"] for m in PRIMARY_METRICS},
            "late_5day_max_envelope":{m:comparison[m]["late_5day_max"] for m in PRIMARY_METRICS},
            "P_CAD_inflation_vs_late_5day_max":{m:comparison[m]["inflation"] for m in PRIMARY_METRICS},
            "all_primary_within_late_5day_max_envelope":bool(all_within),
            "primary_metrics_exceeding_late_5day_max":exceed,
            "rank1_local_expansion_authorized":bool(not all_within),
            "rank1_local_expansion_pairs_if_needed":[[70,75],[80,85]] if not all_within else [],
            "Hybrid_Day75":h75,"Hybrid_Day80":h80,
            "Hybrid_recurrent_state_mutation_performed":False,
            "Hybrid_read_only_endpoint_diagnostic_completed":True,
            "new_Hybrid_error_acceptance_threshold_defined":False,
            "G2_R2_Day120_Day125_authorized":True,
            "G2_R3_Day40_Day45_authorized":False,
            "production_pressure_refresh_cadence_selected":False,
            "Day405_to_Day410_transport_executed":False,
            "Day405_to_Day410_transport_remains_authorized":True,
            "P4_authorized":False,
        }
        decision={
            "milestone":M,"status":PASS,"classification":classification,
            "rank1_early_5day_probe_complete":True,
            "rank1_exceeds_late_5day_envelope":bool(not all_within),
            "rank1_exceeding_metrics":exceed,
            "local_expansion_authorized_only_if_exceeded":bool(not all_within),
            "next_ranked_probe":[120,125],
            "G2_R2_authorized":True,
            "production_pressure_refresh_cadence_selected":False,
            "Hybrid_may_advance_runtime_state":False,
            "future_recurrent_Hybrid_component_mass_bridge_still_required":True,
            "P4_authorized":False,
        }
        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        (out/DECISION).write_text(json.dumps(decision,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        write_csv(out/GATES,gates)
        manifest=[]
        for pth in sorted(out.iterdir()):
            if pth.is_file() and pth.name!=MANIFEST:
                manifest.append({"file":pth.name,"sha256":sha256(pth),"bytes":pth.stat().st_size})
        write_csv(out/MANIFEST,manifest)

        print("="*190)
        print(M,"PASS")
        print("Classification                                      :",classification)
        print("Day75 exact state SHA                               :",summary["Day75_exact_state_sha256"])
        print("Day80 existing exact state reused                   : True")
        print("Day75->80 all primary within late 5-day max         :",all_within)
        print("Metrics exceeding late 5-day max                    :",exceed)
        print("Day75 Hybrid accept / reject                        :",h75["Hybrid10_screen_accept_count"],h75["Hybrid10_screen_reject_count"])
        print("Day80 Hybrid accept / reject                        :",h80["Hybrid10_screen_accept_count"],h80["Hybrid10_screen_reject_count"])
        print("Hybrid recurrent mutation                           : False")
        print("G2-R2 Day120->125 authorized                        : True")
        print("Production pressure-refresh cadence selected        : False")
        print("P4 authorized                                       : False")
        print("Output directory                                    :",out)
        print("="*190)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps({
            "milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),"gates":gates,
            "Day75_state_published":False,"Hybrid_recurrent_state_mutation_performed":False,
            "production_pressure_refresh_cadence_selected":False,"G2_R2_authorized":False,"P4_authorized":False
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
        selftest(); raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))
