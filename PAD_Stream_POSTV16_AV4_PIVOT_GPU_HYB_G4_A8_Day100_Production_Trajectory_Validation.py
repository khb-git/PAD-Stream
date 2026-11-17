#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

M="POSTV16-AV4-PIVOT-GPU-HYB-G4-A8"
PASS="POSTV16AV4PIVOTGPUHYBG4A8_DAY100_PRODUCTION_TRAJECTORY_VALIDATION_COMPLETE"
BLOCK="POSTV16AV4PIVOTGPUHYBG4A8_TECHNICAL_CONSERVATION_OR_VALIDATION_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="80299e03e4eaa1a0da1608d5cb8d7ef03ac70e79"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

A7_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_A7_Controlled_Integrated_Trajectory.py"
A7_BLOB="a11ebdd94378ad673c34efb335d66c47d6855af0"
A1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_A1_R1_ReadOnly_Hybrid_ComponentMass_Bridge_TOF_Identity_Repair.py"
A1_BLOB="6b0bff953b11b393affc429825622fe4afdc5942"
B1_RUNNER="PAD_Stream_POSTV16_AV1_B1_R1_C26_to_E37A_Component_Mass_Representation_Equivalence_Audit.py"
B1_BLOB="8d9561d7c85805b82dedc26073c4633f90eeeab6"
E11_RUNNER="PAD_Stream_V16E11_R2_Packed_SG5_Serialization_Repair_and_Controlled_Hybrid_Streamline_Pilot.py"
E11_BLOB="bf89c14a3cb177fb483e233a17b72e824d31119b"
R3R7_RUNNER="PAD_Stream_V16E41R3R7_Repaired_Production_Rollout_to_Exact_100Day_Observation.py"
R3R7_BLOB="1e7e54f17477788fe518e440c21a65a544b30a48"
R3R8_RUNNER="PAD_Stream_V16E41R3R8_100Day_Legacy_Numerical_Regression_and_E41_Closure.py"
R3R8_BLOB="607536622c3b0ff0d4aef451652e724ad4689baa"
R3R5_RUNNER="PAD_Stream_V16E41R3R5_Multi_Refresh_Cadence_Sensitivity_Runtime_Refresh_Policy_Calibration.py"
R3R5_BLOB="15aae3224ba4337cad72f9b4aa9166d602791349"
R3R4_RUNNER="PAD_Stream_V16E41R3R4R1_Refreshed_Flow_CFL_Alignment_Repair.py"
R3R4_BLOB="5f8433437ce111533338ceada922f51abb2edefe"
R2_REPAIR_RUNNER="PAD_Stream_V16E41R2_Capacity_Aware_Conservative_MapBack_Timestep_Repair.py"
R2_REPAIR_BLOB="f6961c48dc47c5fb55f2af658ef4ce429eb66533"

TARGET_DAY=100.0
MAX_FLOW_EPOCH_DAYS=4.9417335239115445
PRODUCTION_POLICY="HALF_OBSERVED_STALE_INTERVAL"
DAY_TO_S=86400.0
FT_TO_M=0.3048
INJECTOR_MASS_RATE_KG_DAY=500_000.0
EXPECTED_GRID=(15,50,50)

EXACT_OBS_SHA="0418c18e24c967747c7d9dd4024c68635a83bbcf4ee0fe276683e1fb5aa1321e"
EXACT_RESTART_SHA="0772e6c067d36c20037ff448e2b1ebc7e11c53ef8e05642264583c56bb18a770"

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_A8"
OUT_REL=BASE/(OUT_TOKEN+"_Day100_Production_Trajectory_Validation")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
STEPS=f"{OUT_TOKEN}_Accepted_Transitions.csv"
REFRESHES=f"{OUT_TOKEN}_Flow_Refreshes.csv"
CAPACITY=f"{OUT_TOKEN}_Capacity_Events.csv"
CONTROLLER=f"{OUT_TOKEN}_Capacity_Controller.csv"
ROUTES=f"{OUT_TOKEN}_Route_Audit.csv"
SNAPS=f"{OUT_TOKEN}_Refresh_Snapshots.npz"
MIXED_OBS=f"{OUT_TOKEN}_Mixed_100d_Observation_State.npz"
MIXED_RESTART=f"{OUT_TOKEN}_Mixed_100d_PostObservation_Refreshed_Restart.npz"
GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"

class GateError(RuntimeError): pass

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""): h.update(c)
    return h.hexdigest()

def gt(root:Path,*a:str)->str:
    return subprocess.check_output(["git","-C",str(root),*a],text=True).strip()

def blob(root:Path,p:Path)->str:
    return gt(root,"hash-object",str(p))

def mod(root:Path,fn:str,expected:str,name:str):
    p=root/fn
    if not p.is_file(): raise GateError(f"missing_source:{fn}")
    actual=blob(root,p)
    if actual!=expected: raise GateError(f"source_blob:{fn}:{actual}:{expected}")
    s=importlib.util.spec_from_file_location(name,p)
    if s is None or s.loader is None: raise GateError(f"import_spec:{fn}")
    m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m

def js(p:Path): return json.loads(p.read_text(encoding="utf-8"))

def load_npz(p:Path):
    with np.load(p,allow_pickle=False) as z:return {k:np.asarray(z[k]).copy() for k in z.files}

def scalar(x:Any)->float:return float(np.asarray(x).reshape(()))
def int_scalar(x:Any)->int:return int(np.asarray(x).reshape(()))
def bool_scalar(x:Any)->bool:return bool(np.asarray(x).reshape(()))

def rel_l2(a,b):
    a=np.asarray(a,float);b=np.asarray(b,float)
    return float(np.linalg.norm((a-b).ravel())/max(float(np.linalg.norm(b.ravel())),1e-30))

def write_csv(p:Path,rows:list[dict[str,Any]]):
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields:fields.append(k)
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n")
        w.writeheader();w.writerows(rows)

def deterministic_npz_bytes(arrays:dict[str,Any])->bytes:
    outer=io.BytesIO()
    with zipfile.ZipFile(outer,mode="w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for key in sorted(arrays):
            b=io.BytesIO();np.save(b,np.asarray(arrays[key]),allow_pickle=False)
            info=zipfile.ZipInfo(f"{key}.npy",date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o600<<16
            zf.writestr(info,b.getvalue())
    return outer.getvalue()

def selftest():
    assert TARGET_DAY==100.0
    assert abs(MAX_FLOW_EPOCH_DAYS-4.9417335239115445)<=1e-15
    assert INJECTOR_MASS_RATE_KG_DAY*TARGET_DAY==50_000_000.0
    print("POSTV16 GPU-HYB-G4-A8 structural self-test: PASS")

def main(root:Path,drive:Path)->int:
    root=root.resolve();drive=drive.resolve();out=drive/OUT_REL;blocked=drive/BLOCK_REL
    gates=[];stage="preflight";parent_sha_before=None
    def gate(n,c,d=None):
        ok=bool(c);gates.append({"stage":stage,"gate":n,"pass":ok,"detail":"" if d is None else repr(d)})
        print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"),flush=True)
        if not ok: raise GateError(n)

    try:
        print("="*202)
        print("G4-A8 — DAY100 PRODUCTION-LINEAGE INTEGRATED HYBRID TRAJECTORY VALIDATION")
        print("STARTS FROM THE SAME AUTHORITATIVE DAY69.883467 PARENT AS R3-R7 AND USES THE FROZEN PRODUCTION REFRESH POLICY TO DAY100.")
        print("FINAL MIXED STATE IS COMPARED DIRECTLY AGAINST THE FROZEN EXACT R3-R7 DAY100 OBSERVATION.")
        print("="*202)

        stage="repository"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_G4_A7",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")
        a7=mod(root,A7_RUNNER,A7_BLOB,"g4a8_a7")
        a1=mod(root,A1_RUNNER,A1_BLOB,"g4a8_a1")
        b1=mod(root,B1_RUNNER,B1_BLOB,"g4a8_b1")
        e11=mod(root,E11_RUNNER,E11_BLOB,"g4a8_e11")
        r3r7=mod(root,R3R7_RUNNER,R3R7_BLOB,"g4a8_r3r7")
        r3r8=mod(root,R3R8_RUNNER,R3R8_BLOB,"g4a8_r3r8")
        r3r5=mod(root,R3R5_RUNNER,R3R5_BLOB,"g4a8_r3r5")
        r3r4=mod(root,R3R4_RUNNER,R3R4_BLOB,"g4a8_r3r4")
        repair=mod(root,R2_REPAIR_RUNNER,R2_REPAIR_BLOB,"g4a8_repair")

        stage="A7_authority"
        a7s=js(drive/a7.OUT_REL/a7.SUMMARY)
        gate("A7_status_exact",a7s.get("status")==a7.PASS,a7s.get("status"))
        gate("A7_A8_authorized",a7s.get("G4_A8_integrated_trajectory_validation_authorized") is True)
        gate("A7_reuse_refresh_resume_complete",
             a7s.get("flow_reuse_branch_executed") is True and
             a7s.get("full_flow_refresh_branch_executed") is True and
             a7s.get("post_refresh_mixed_transport_resumed") is True)
        gate("A7_no_production_authorization",a7s.get("integrated_GPU_runtime_production_authorized") is False)

        stage="exact_truth_authority"
        exact_obs_path=drive/r3r7.OUT_REL/r3r7.OBSERVATION_STATE_NAME
        exact_restart_path=drive/r3r7.OUT_REL/r3r7.RESTART_STATE_NAME
        gate("exact_100d_observation_present",exact_obs_path.is_file(),str(exact_obs_path))
        gate("exact_100d_restart_present",exact_restart_path.is_file(),str(exact_restart_path))
        gate("exact_100d_observation_SHA",sha(exact_obs_path)==EXACT_OBS_SHA,sha(exact_obs_path))
        gate("exact_100d_restart_SHA",sha(exact_restart_path)==EXACT_RESTART_SHA,sha(exact_restart_path))
        exact_truth=load_npz(exact_obs_path)
        exact_restart=load_npz(exact_restart_path)
        gate("exact_truth_time_100d",scalar(exact_truth["physical_time_days"])==100.0)
        gate("exact_restart_time_100d",scalar(exact_restart["physical_time_days"])==100.0)

        stage="physics_authority"
        roles={}
        for role in ["R3R2R1","E36","E37A","R2_PHYSICS","SG2","SG3","SG4","SG5","SG6","SG7A","SG7D"]:
            fn,bl=r3r4.SOURCE_BLOBS[role]
            roles[role]=mod(root,fn,bl,f"g4a8_{role.lower()}")
        r3r2r1=roles["R3R2R1"];e36=roles["E36"];e37a=roles["E37A"];physics=roles["R2_PHYSICS"]
        sg2=roles["SG2"];sg3=roles["SG3"];sg4=roles["SG4"];sg5=roles["SG5"];sg6=roles["SG6"]
        sg7a=roles["SG7A"];sg7d=roles["SG7D"]

        pfn,pblob=r3r4.SOURCE_BLOBS["PERM"];perm_path=root/pfn
        gate("permeability_blob_exact",blob(root,perm_path)==pblob,blob(root,perm_path))
        permeability_md=np.loadtxt(perm_path,skiprows=1,dtype=np.float64).reshape(EXPECTED_GRID,order="C")
        cell_pv=0.20*(20.0*FT_TO_M)*(20.0*FT_TO_M)*(4.0*FT_TO_M)

        parent_path=drive/r3r4.R3R1_REL/r3r4.R3R1_STATE
        gate("production_parent_present",parent_path.is_file(),str(parent_path))
        parent_sha_before=sha(parent_path)
        gate("production_parent_SHA_exact",parent_sha_before==r3r7.EXPECTED_PARENT_STATE_SHA256,parent_sha_before)
        current=load_npz(parent_path)
        gate("production_parent_time_exact",abs(scalar(current["physical_time_days"])-r3r7.EXPECTED_PARENT_TIME_DAYS)<=1e-12,
             scalar(current["physical_time_days"]))
        gate("production_parent_step_exact",int_scalar(current["accepted_step_index"])==r3r7.EXPECTED_PARENT_STEP,
             int_scalar(current["accepted_step_index"]))

        initial_injected=scalar(current["cumulative_injected_co2_mass_kg"])
        initial_produced=scalar(current["cumulative_produced_co2_mass_kg"])
        initial_stored=scalar(current["stored_co2_mass_current_kg"])

        stage="Hybrid_authority"
        for rel,entry,label in [
            (e11.E8R1_REL,e11.E8R1["contract"],"E8R1"),
            (e11.E5_REL,e11.E5_MANIFEST,"E5"),
            (e11.E3_REL,e11.E3_PROTOCOL,"E3"),
            (e11.E6A_REL,e11.E6A_CHECKPOINT,"E6A"),
        ]:
            fn,expected=entry;p=drive/rel/fn
            gate(label+"_present",p.is_file(),str(p));gate(label+"_SHA",e11.sha(p)==expected,e11.sha(p))
        screen=e11.read_json(drive/e11.E8R1_REL/e11.E8R1["contract"][0])["learned_proposal_execution_screen"]
        e5=e11.read_json(drive/e11.E5_REL/e11.E5_MANIFEST[0])
        e3=e11.read_json(drive/e11.E3_REL/e11.E3_PROTOCOL[0])
        params=e11.c14_production_params(root/e11.C14_SOURCE[0])
        gate("C14_inside_E3",e11.parameters_inside_e3(params,e3))
        adapter=e11.import_exact(root/e11.E9_ADAPTER[0],e11.E9_ADAPTER[1],"g4a8_adapter")
        teacher=e11.import_exact(root/e11.R2_ADAPTER[0],e11.R2_ADAPTER[1],"g4a8_teacher")
        e9r1=e11.import_exact(root/e11.E9R1_RUNNER[0],e11.E9R1_RUNNER[1],"g4a8_e9r1")
        shock=teacher.welge_shock(adapter.teacher_params(params),scan_nodes=4097)
        speed=float(shock["characteristic_speed"]);swstar=float(shock["Sw_star"])
        tf=e9r1.prepare_tf(e5)
        gate("TensorFlow_2_20_exact",tf.__version__=="2.20.0",tf.__version__)
        gate("GPU_visible",len(tf.config.list_physical_devices("GPU"))>=1,[str(x) for x in tf.config.list_physical_devices("GPU")])
        model=e9r1.build_inference_model(tf,10,"G4A8_Hybrid10")
        gate("Hybrid10_parameter_count_exact",model.count_params()==52545,model.count_params())
        model.load_weights(str(drive/e11.E6A_REL/e11.E6A_CHECKPOINT[0]))

        def rebuild_db(epoch:dict[str,Any]):
            vx,vy,vz=sg5.construct_face_pore_velocities(epoch["qx"],epoch["qy"],epoch["qz"])
            _faces,seeds=sg5.build_seeds(epoch["qx"],epoch["qy"],epoch["qz"])
            streamlines=sg5.trace_streamlines(seeds,vx,vy,vz)
            converted=r3r4.convert_sg5_to_sg6_streamlines(streamlines)
            db=sg6.build_transport_database(converted)
            if int(np.asarray(db["xyz_m"]).shape[0])!=int(epoch["nstream"]):raise GateError("db_stream_count")
            if int(np.asarray(db["xi"]).shape[0])!=int(epoch["nfaces"]):raise GateError("db_face_count")
            w=np.asarray(db["weights_m3_s"],float)*DAY_TO_S
            if np.max(np.abs(w-np.asarray(epoch["weights_m3_day"],float)))>1e-8:raise GateError("db_weights")
            return db

        profile_cache={}
        def infer_profiles(day:float,db:dict[str,np.ndarray],epoch_tag:str):
            key=(epoch_tag,round(float(day),12))
            if key in profile_cache:return profile_cache[key]
            tau=np.asarray(db["tau_s"],float);tau_end=np.asarray(db["tau_end_s"],float)
            xi=np.asarray(db["xi"],float);terminal_days=tau_end/DAY_TO_S
            xstar=(float(day)/terminal_days)*speed
            clocks=np.asarray([e11.classify_clock(float(x)) for x in xstar],dtype="U32")
            idx=np.flatnonzero(clocks=="LEARNED_WINDOW")
            profiles={};reject={}
            if idx.size:
                cond=[];states=[]
                for i in idx:
                    st=adapter.physical_time_state(elapsed_time=day,tau_end=float(terminal_days[i]),
                                                   characteristic_speed=speed,Sw_star=swstar)
                    states.append(st);cond.append(adapter.conditioning_vector("HYBRID10",params,st))
                pred=e9r1.infer(tf,model,xi.astype(np.float32),np.asarray(cond,dtype=np.float32),batch=256)
                for local,i in enumerate(idx):
                    ok,sm=e11.screen_fan_prediction(
                        pred[local],params,states[local],xi,tau[i]/DAY_TO_S,teacher,adapter,screen)
                    if ok:
                        profiles[int(i)]=adapter.project_fan_to_pollock_nodes(
                            tau_nodes=tau[i]/DAY_TO_S,state=states[local],fan_xi=xi,
                            fan_sw=pred[local],swc=float(params["swc"])).astype(np.float64)
                    else:
                        for reason in sm["failures"]:reject[reason]=reject.get(reason,0)+1
            result=(profiles,clocks,reject);profile_cache[key]=result;return result

        refresh_rows=[];step_rows=[];capacity_rows=[];controller_rows=[];route_rows=[]
        refresh_times=[];refresh_sats=[];refresh_pressures=[]
        capacity_margins=[]
        epoch=None;db=None;epoch_start_time=None;epoch_serial=0
        refresh_count=0;cadence_refresh_count=0;capacity_refresh_count=0
        capacity_adjustments_total=0;capacity_limited_steps=0;force_refresh_next=False
        total_hybrid_routes=0;total_exact_fallback_routes=0

        def do_refresh(trigger:str):
            nonlocal current,epoch,db,epoch_start_time,epoch_serial
            nonlocal refresh_count,cadence_refresh_count,capacity_refresh_count
            before_time=scalar(current["physical_time_days"]);before_step=int_scalar(current["accepted_step_index"])
            before_inj=scalar(current["cumulative_injected_co2_mass_kg"])
            before_prod=scalar(current["cumulative_produced_co2_mass_kg"])
            before_stored=scalar(current["stored_co2_mass_current_kg"])
            refreshed,new_epoch,_rows=r3r5.build_flow_epoch(
                current=current,r3r4r1=r3r4,physics=physics,r3r2r1=r3r2r1,e36=e36,e37a=e37a,
                sg2=sg2,sg3=sg3,sg4=sg4,sg5=sg5,sg6=sg6,sg7a=sg7a,sg7d=sg7d,
                permeability_md=permeability_md,cell_pore_volume_m3=cell_pv)
            if scalar(refreshed["physical_time_days"])!=before_time:raise GateError("refresh_advanced_time")
            if int_scalar(refreshed["accepted_step_index"])!=before_step:raise GateError("refresh_advanced_step")
            if scalar(refreshed["cumulative_injected_co2_mass_kg"])!=before_inj:raise GateError("refresh_changed_injection")
            if scalar(refreshed["cumulative_produced_co2_mass_kg"])!=before_prod:raise GateError("refresh_changed_production")
            mtol=max(1e-6,1e-10*max(abs(before_stored),1.0))
            if abs(scalar(refreshed["stored_co2_mass_current_kg"])-before_stored)>mtol:raise GateError("refresh_changed_stored")
            current=refreshed;epoch=new_epoch;db=rebuild_db(new_epoch)
            epoch_start_time=before_time;epoch_serial+=1;refresh_count+=1
            if trigger=="CADENCE":cadence_refresh_count+=1
            if trigger=="CAPACITY_PREFLIGHT_REJECTION":capacity_refresh_count+=1
            refresh_rows.append({
                "refresh_index":refresh_count,"trigger":trigger,"physical_time_days":before_time,
                "accepted_step_index":before_step,"fixed_point_iterations":int(new_epoch["fixed_point_iterations"]),
                "CFL_dt_days":float(new_epoch["cfl_dt_days"]),"streamline_count":int(new_epoch["nstream"]),
                "capture_fraction":float(new_epoch["capture_fraction"]),
                "flow_local_relative_residual":float(new_epoch["flow_local_residual"]),
                "flow_global_relative_residual":float(new_epoch["flow_global_residual"]),
                "pressure_rel_L2_vs_pre_refresh":float(new_epoch["refresh_pressure_rel_L2_vs_parent"]),
                "saturation_Linf_vs_pre_refresh":float(new_epoch["refresh_saturation_Linf_vs_parent"]),
                "refresh_global_mass_error_kg":float(new_epoch["refresh_global_mass_error_kg"]),
            })
            refresh_times.append(before_time)
            refresh_sats.append(np.asarray(current["transport_saturation"],float).copy())
            refresh_pressures.append(np.asarray(new_epoch["pressure_psi"],float).copy())

        stage="production_integrated_rollout"
        do_refresh("RESTART_OR_INITIALIZATION")

        while scalar(current["physical_time_days"])<TARGET_DAY-1e-13:
            now=scalar(current["physical_time_days"])
            if epoch is None or db is None or epoch_start_time is None:raise GateError("missing_epoch")

            if force_refresh_next:
                do_refresh("POST_CAPACITY_LIMITED_ACCEPT")
                force_refresh_next=False
                now=scalar(current["physical_time_days"])

            due=epoch_start_time+MAX_FLOW_EPOCH_DAYS
            if now>=due-1e-13:
                do_refresh("CADENCE");now=scalar(current["physical_time_days"]);due=epoch_start_time+MAX_FLOW_EPOCH_DAYS

            intended_target=min(TARGET_DAY,due,now+float(epoch["cfl_dt_days"]))
            base_dt=intended_target-now
            if not np.isfinite(base_dt) or base_dt<=0:raise GateError(f"nonpositive_base_dt:{base_dt}")

            same_parent_capacity_refresh_done=False
            capacity_adjustments_step=0
            candidate_dt=float(base_dt)

            while True:
                parent_time=scalar(current["physical_time_days"])
                parent_step=int_scalar(current["accepted_step_index"])
                parent_sat=np.asarray(current["transport_saturation"],float)
                pressure=np.asarray(epoch["pressure_psi"],float)
                p_ref=scalar(current["co2_density_reference_pressure_pa"])
                parent_stored=scalar(current["stored_co2_mass_current_kg"])

                candidate_dt=min(candidate_dt,float(epoch["cfl_dt_days"]),intended_target-parent_time,TARGET_DAY-parent_time)
                if candidate_dt<=0:raise GateError(f"nonpositive_candidate_dt:{candidate_dt}")

                recomputed=float(physics.stored_co2_mass_kg(parent_sat,pressure,p_ref,cell_pv))
                ptol=max(1e-6,1e-10*max(abs(parent_stored),1.0))
                if abs(recomputed-parent_stored)>ptol:raise GateError(f"parent_mass_pressure_mismatch:{recomputed-parent_stored}")

                old_sat,old_mass,sample=e37a.sample_grid_inventory_to_control_volumes(
                    physics,parent_sat,pressure,p_ref,epoch["geometry"],epoch["nstream"],epoch["ncv"])
                stol=max(1e-6,1e-10*max(abs(float(np.sum(old_mass))),1.0))
                if abs(float(sample))>stol:raise GateError(f"sampling_closure:{sample}")

                exact_fallback=e37a.advance_component_mass_control_volumes(
                    physics,sg7a,old_sat,old_mass,epoch["geometry"]["cv_pressure_mass_coeff"],
                    epoch["face_pressure_psi"],p_ref,epoch["weights_m3_day"],epoch["xi_faces"],candidate_dt)
                child_mass=np.asarray(exact_fallback["new_mass"],float).copy()
                child_cv_sat=np.asarray(exact_fallback["new_saturation"],float).copy()

                u=np.asarray(sg7a.u_dimensionless(epoch["xi_faces"]),float)
                q=np.asarray(epoch["weights_m3_day"],float)
                inlet_rate=q*float(e37a.CO2_RHO_REF_KG_M3)
                outlet_sat=old_sat[:,-1]
                outlet_ff=np.asarray(sg7a.fractional_flow(outlet_sat),float)
                outlet_rho=np.asarray(physics.gas_density_from_state(outlet_sat,epoch["face_pressure_psi"][:,-1],p_ref),float)
                outlet_rate=q*float(u[-1])*outlet_ff*outlet_rho
                target_i=np.sum(old_mass,axis=1)+inlet_rate*candidate_dt-outlet_rate*candidate_dt

                direct_res=np.max(np.abs(np.sum(child_mass,axis=1)-target_i))
                if direct_res>1e-7:raise GateError(f"boundary_budget_vs_exact_fallback:{direct_res}")

                epoch_tag=f"E{epoch_serial}"
                pp,_,pr=infer_profiles(parent_time,db,epoch_tag)
                cp,_,cr=infer_profiles(parent_time+candidate_dt,db,epoch_tag)
                eligible=np.asarray(sorted(set(pp).intersection(cp)),dtype=np.int64)

                correction_l1=[]
                if eligible.size:
                    parent_prof=np.stack([pp[int(i)] for i in eligible],axis=0)
                    child_prof=np.stack([cp[int(i)] for i in eligible],axis=0)
                    _,pmm,_=b1.project_201_to_200_component_mass(
                        physics,e37a,parent_prof,epoch["geometry"]["cv_pressure_mass_coeff"],eligible)
                    _,cmm,_=b1.project_201_to_200_component_mass(
                        physics,e37a,child_prof,epoch["geometry"]["cv_pressure_mass_coeff"],eligible)
                    raw=old_mass[eligible]+(cmm-pmm)
                    for j,sl in enumerate(eligible):
                        coeff=np.asarray(epoch["geometry"]["cv_pressure_mass_coeff"])[sl]
                        cap=np.asarray(e37a.cv_mass_from_saturation(
                            physics,np.full(int(epoch["ncv"]),float(physics.BACKGROUND_SATURATION+physics.MAX_INCREMENTAL_CO2_SATURATION)),
                            coeff),float)
                        mm,lam,closure=a1.box_project(raw[j],float(target_i[sl]),cap)
                        if abs(float(closure))>1e-8:raise GateError(f"Hybrid_budget_closure:{sl}:{closure}")
                        denom=max(float(np.sum(np.abs(raw[j]))),1e-30)
                        correction_l1.append(float(np.sum(np.abs(mm-raw[j])))/denom)
                        ss=np.asarray(e37a.invert_cv_mass_to_saturation(physics,mm,coeff),float)
                        child_mass[sl]=mm;child_cv_sat[sl]=ss

                injected_step=float(np.sum(inlet_rate)*candidate_dt)
                produced_step=float(np.sum(outlet_rate)*candidate_dt)
                physical_injected=INJECTOR_MASS_RATE_KG_DAY*candidate_dt
                itol=max(1e-6,1e-12*max(abs(physical_injected),1.0))
                if abs(injected_step-physical_injected)>itol:
                    raise GateError(f"fixed_rate_injection_mismatch:{injected_step-physical_injected}")

                parent_cell_mass=r3r4.parent_cellwise_component_mass(physics,parent_sat,pressure,p_ref,cell_pv)
                target_final=parent_stored+injected_step-produced_step
                preflight=r3r4.preflight_mapback_capacity(
                    physics=physics,parent_saturation=parent_sat,parent_mass=parent_cell_mass,
                    old_cv_saturation=old_sat,new_cv_saturation=child_cv_sat,geometry=epoch["geometry"],
                    pressure_psi=pressure,p_ref_gas_pa=p_ref,cell_pore_volume_m3=cell_pv)
                capacity_margins.append(float(preflight["minimum_capacity_margin_kg"]))

                if int(preflight["overcapacity_cell_count"])>0:
                    capacity_rows.append({
                        "physical_time_days":parent_time,"accepted_step_index":parent_step,
                        "trial_dt_days":candidate_dt,"same_parent_refresh_done":same_parent_capacity_refresh_done,
                        "overcapacity_cell_count":int(preflight["overcapacity_cell_count"]),
                        "max_capacity_excess_kg":float(preflight["max_capacity_excess_kg"]),
                        "minimum_capacity_margin_kg":float(preflight["minimum_capacity_margin_kg"]),
                    })
                    if not same_parent_capacity_refresh_done:
                        do_refresh("CAPACITY_PREFLIGHT_REJECTION")
                        same_parent_capacity_refresh_done=True
                        continue

                    ctl=repair.preflight_mapback_capacity(
                        r2=physics,e37a=e37a,parent_grid_saturation=parent_sat,
                        old_cv_saturation=old_sat,new_cv_saturation=child_cv_sat,
                        old_cv_mass=old_mass,new_cv_mass=child_mass,geometry=epoch["geometry"],
                        pressure_psi=pressure,p_ref_gas_pa=p_ref,cell_pore_volume_m3=cell_pv,
                        target_final_mass_kg=target_final,active_dt_days=candidate_dt)
                    if ctl.get("native_failure_required"):raise GateError(f"capacity_native_failure:{ctl.get('reason')}")
                    if not ctl.get("controller_applicable"):raise GateError("capacity_controller_not_applicable")
                    recommended=float(ctl["recommended_dt_days"])
                    if not np.isfinite(recommended) or recommended<=0 or recommended>=candidate_dt:
                        raise GateError(f"invalid_capacity_recommended_dt:{recommended}:{candidate_dt}")
                    capacity_adjustments_step+=1;capacity_adjustments_total+=1
                    controller_rows.append({
                        "physical_time_days":parent_time,"accepted_step_index":parent_step,
                        "adjustment_index_this_step":capacity_adjustments_step,
                        "candidate_dt_days":candidate_dt,"recommended_dt_days":recommended,
                        "raw_admissible_fraction":float(ctl["raw_admissible_fraction"]),
                        "max_capacity_excess_kg":float(ctl["max_capacity_excess_kg"]),
                        "limiting_cell_zero_based":str(ctl["upper_limiting_cell_zero_based"]),
                    })
                    if capacity_adjustments_step>int(repair.MAX_CAPACITY_ADJUSTMENTS):
                        raise GateError(f"capacity_adjustment_budget_exhausted:{parent_step+1}")
                    candidate_dt=recommended
                    continue

                mapping=e37a.map_control_volume_increment_to_grid(
                    physics,parent_sat,old_sat,child_cv_sat,old_mass,child_mass,epoch["geometry"],
                    pressure,p_ref,cell_pv,target_final)
                capillary=physics.conservative_capillary_mass_redistribution(
                    transport_saturation=np.asarray(mapping["corrected_saturation"],float),
                    permeability_md=permeability_md,pressure_psi=pressure,p_ref_pa=p_ref,
                    cell_pore_volume_m3=cell_pv,dt_seconds=candidate_dt*DAY_TO_S)
                child_sat=np.asarray(capillary["corrected"],float)
                final_stored=float(capillary["final_mass_state_kg"])
                step_residual=final_stored-parent_stored-injected_step+produced_step
                ctol=max(1e-6,1e-10*max(abs(target_final),1.0))
                if abs(float(capillary["external_mass_change_kg"]))>ctol:
                    raise GateError(f"capillary_external_mass_change:{capillary['external_mass_change_kg']}")
                if abs(step_residual)>ctol:raise GateError(f"step_component_mass_closure:{step_residual}")

                prod_rows,aggregate_cut=e37a.producer_rows_from_flux(
                    epoch["labels"],epoch["weights_m3_day"],
                    np.asarray(sg7a.fractional_flow(old_sat[:,-1]),float),outlet_rate,candidate_dt)
                if not np.isfinite(aggregate_cut) or not 0<=aggregate_cut<=1:
                    raise GateError(f"producer_gas_cut_invalid:{aggregate_cut}")

                child=e36.make_child_state(
                    current,child_sat,pressure,p_ref,candidate_dt,produced_step,
                    aggregate_cut,final_stored,step_residual,False)
                child["transport_face_count"]=np.asarray(epoch["nfaces"],dtype=np.int64)
                child["transport_control_volume_count"]=np.asarray(epoch["ncv"],dtype=np.int64)
                child["mass_conservative_flow_refresh_active"]=np.asarray(True,dtype=bool)
                child["runtime_refresh_policy_name_ascii"]=np.frombuffer(PRODUCTION_POLICY.encode("ascii"),dtype=np.uint8)
                child["runtime_max_flow_epoch_days"]=np.asarray(MAX_FLOW_EPOCH_DAYS,dtype=np.float64)
                child["hybrid_recurrent_bridge_active"]=np.asarray(True,dtype=bool)
                child["hybrid_recurrent_mode_ascii"]=np.frombuffer(b"HYBRID_INCREMENTAL_MIXED",dtype=np.uint8)
                child["hybrid_parent_anchored_incremental"]=np.asarray(True,dtype=bool)
                child["hybrid_incremental_route_count"]=np.asarray(int(eligible.size),dtype=np.int64)
                child["exact_fallback_route_count"]=np.asarray(int(epoch["nstream"]-eligible.size),dtype=np.int64)
                child["last_grid_mapback_ledger_residual_kg"]=np.asarray(mapping["ledger_residual_kg"],dtype=np.float64)
                child["last_capillary_external_mass_change_kg"]=np.asarray(capillary["external_mass_change_kg"],dtype=np.float64)
                child["flow_epoch_origin_day"]=np.asarray(epoch_start_time,dtype=np.float64)
                child["flow_epoch_age_days"]=np.asarray(parent_time+candidate_dt-epoch_start_time,dtype=np.float64)

                accepted_time=scalar(child["physical_time_days"])
                if TARGET_DAY-accepted_time<=1e-13:
                    child["physical_time_days"]=np.asarray(TARGET_DAY,dtype=np.float64);accepted_time=TARGET_DAY

                total_hybrid_routes+=int(eligible.size)
                total_exact_fallback_routes+=int(epoch["nstream"]-eligible.size)
                route_rows.append({
                    "accepted_step_index":int_scalar(child["accepted_step_index"]),
                    "parent_time_days":parent_time,"accepted_time_days":accepted_time,
                    "Hybrid_incremental_route_count":int(eligible.size),
                    "exact_fallback_route_count":int(epoch["nstream"]-eligible.size),
                    "Hybrid_route_fraction":float(eligible.size/max(int(epoch["nstream"]),1)),
                    "parent_screen_rejection_count":int(sum(pr.values())),
                    "child_screen_rejection_count":int(sum(cr.values())),
                    "mass_correction_relative_L1_median":float(np.median(correction_l1)) if correction_l1 else 0.0,
                    "mass_correction_relative_L1_p95":float(np.quantile(correction_l1,0.95)) if correction_l1 else 0.0,
                })
                step_rows.append({
                    "accepted_step_index":int_scalar(child["accepted_step_index"]),
                    "parent_time_days":parent_time,"accepted_time_days":accepted_time,
                    "accepted_dt_days":candidate_dt,"active_epoch_CFL_dt_days":float(epoch["cfl_dt_days"]),
                    "epoch_age_before_step_days":parent_time-epoch_start_time,
                    "observation_landing_step":accepted_time==TARGET_DAY,
                    "capacity_same_parent_refresh_used":same_parent_capacity_refresh_done,
                    "capacity_controller_adjustments":capacity_adjustments_step,
                    "raw_minimum_capacity_margin_kg":float(preflight["minimum_capacity_margin_kg"]),
                    "injected_CO2_mass_kg":injected_step,"produced_CO2_mass_kg":produced_step,
                    "stored_CO2_mass_kg":final_stored,"step_component_mass_residual_kg":step_residual,
                    "producer_CO2_gas_cut":float(aggregate_cut),
                    "Hybrid_incremental_route_count":int(eligible.size),
                    "exact_fallback_route_count":int(epoch["nstream"]-eligible.size),
                })
                current={k:np.asarray(v).copy() for k,v in child.items()}
                if capacity_adjustments_step>0:
                    capacity_limited_steps+=1;force_refresh_next=True
                break

        stage="Day100_observation_validation"
        gate("mixed_100d_landing",scalar(current["physical_time_days"])==TARGET_DAY,scalar(current["physical_time_days"]))
        mixed_obs=r3r7.observation_semantics(current)
        mixed_stored=scalar(mixed_obs["stored_co2_mass_current_kg"])
        mixed_injected=scalar(mixed_obs["cumulative_injected_co2_mass_kg"])
        mixed_produced=scalar(mixed_obs["cumulative_produced_co2_mass_kg"])
        mixed_cut=scalar(mixed_obs["current_producer_co2_gas_cut"])
        mixed_cum=mixed_stored-scalar(mixed_obs["stored_co2_mass_initial_kg"])-mixed_injected+mixed_produced
        mtol=max(1e-6,1e-10*max(abs(mixed_stored),1.0))
        gate("mixed_100d_component_mass_closure",abs(mixed_cum)<=mtol,mixed_cum)
        expected_injected=INJECTOR_MASS_RATE_KG_DAY*TARGET_DAY
        gate("mixed_100d_cumulative_injection_rate",
             abs(mixed_injected-expected_injected)<=max(1e-6,1e-12*expected_injected),
             mixed_injected-expected_injected)
        gate("parent_state_immutable",sha(parent_path)==parent_sha_before,sha(parent_path))

        truth_sat=np.asarray(exact_truth["transport_saturation"],float)
        mixed_sat=np.asarray(mixed_obs["transport_saturation"],float)
        sat_rel=rel_l2(mixed_sat,truth_sat)
        sat_linf=float(np.max(np.abs(mixed_sat-truth_sat)))
        sat_mae=float(np.mean(np.abs(mixed_sat-truth_sat)))
        stored_diff=mixed_stored-scalar(exact_truth["stored_co2_mass_current_kg"])
        stored_rel=abs(stored_diff)/max(abs(scalar(exact_truth["stored_co2_mass_current_kg"])),1e-30)
        produced_diff=mixed_produced-scalar(exact_truth["cumulative_produced_co2_mass_kg"])
        produced_rel=abs(produced_diff)/max(abs(scalar(exact_truth["cumulative_produced_co2_mass_kg"])),1e-30)
        cut_diff=mixed_cut-scalar(exact_truth["current_producer_co2_gas_cut"])
        active_threshold=1e-8;visible_threshold=1e-4
        bg=float(physics.BACKGROUND_SATURATION)
        mixed_inc=np.clip(mixed_sat-bg,0,None);truth_inc=np.clip(truth_sat-bg,0,None)
        active_count_diff=int(np.sum(mixed_inc>active_threshold)-np.sum(truth_inc>active_threshold))
        visible_count_diff=int(np.sum(mixed_inc>visible_threshold)-np.sum(truth_inc>visible_threshold))

        stage="Day100_same_time_refresh_validation"
        pre_time=scalar(mixed_obs["physical_time_days"]);pre_step=int_scalar(mixed_obs["accepted_step_index"])
        pre_inj=scalar(mixed_obs["cumulative_injected_co2_mass_kg"]);pre_prod=scalar(mixed_obs["cumulative_produced_co2_mass_kg"])
        pre_stored=scalar(mixed_obs["stored_co2_mass_current_kg"])
        mixed_restart,mixed_epoch100,_=r3r5.build_flow_epoch(
            current=mixed_obs,r3r4r1=r3r4,physics=physics,r3r2r1=r3r2r1,e36=e36,e37a=e37a,
            sg2=sg2,sg3=sg3,sg4=sg4,sg5=sg5,sg6=sg6,sg7a=sg7a,sg7d=sg7d,
            permeability_md=permeability_md,cell_pore_volume_m3=cell_pv)
        exact_rebuilt,exact_epoch100,_=r3r5.build_flow_epoch(
            current=exact_truth,r3r4r1=r3r4,physics=physics,r3r2r1=r3r2r1,e36=e36,e37a=e37a,
            sg2=sg2,sg3=sg3,sg4=sg4,sg5=sg5,sg6=sg6,sg7a=sg7a,sg7d=sg7d,
            permeability_md=permeability_md,cell_pore_volume_m3=cell_pv)

        gate("mixed_100d_refresh_same_time",scalar(mixed_restart["physical_time_days"])==pre_time)
        gate("mixed_100d_refresh_same_step",int_scalar(mixed_restart["accepted_step_index"])==pre_step)
        gate("mixed_100d_refresh_injection_unchanged",scalar(mixed_restart["cumulative_injected_co2_mass_kg"])==pre_inj)
        gate("mixed_100d_refresh_production_unchanged",scalar(mixed_restart["cumulative_produced_co2_mass_kg"])==pre_prod)
        gate("mixed_100d_refresh_stored_unchanged",
             abs(scalar(mixed_restart["stored_co2_mass_current_kg"])-pre_stored)<=mtol,
             scalar(mixed_restart["stored_co2_mass_current_kg"])-pre_stored)

        exact_restart_pressure_rel=rel_l2(exact_rebuilt["accepted_pressure_psi"],exact_restart["accepted_pressure_psi"])
        exact_restart_sat_rel=rel_l2(exact_rebuilt["transport_saturation"],exact_restart["transport_saturation"])
        gate("exact_100d_refresh_rebuild_pressure_matches_frozen",exact_restart_pressure_rel<=1e-12,exact_restart_pressure_rel)
        gate("exact_100d_refresh_rebuild_saturation_matches_frozen",exact_restart_sat_rel<=1e-12,exact_restart_sat_rel)

        pressure_rel=rel_l2(mixed_epoch100["pressure_psi"],exact_epoch100["pressure_psi"])
        qmix=np.concatenate([np.asarray(mixed_epoch100["qx"]).ravel(),np.asarray(mixed_epoch100["qy"]).ravel(),np.asarray(mixed_epoch100["qz"]).ravel()])
        qtruth=np.concatenate([np.asarray(exact_epoch100["qx"]).ravel(),np.asarray(exact_epoch100["qy"]).ravel(),np.asarray(exact_epoch100["qz"]).ravel()])
        flux_rel=rel_l2(qmix,qtruth)
        post_refresh_sat_rel=rel_l2(mixed_restart["transport_saturation"],exact_rebuilt["transport_saturation"])

        refresh_times.append(100.0)
        refresh_sats.append(np.asarray(mixed_restart["transport_saturation"],float).copy())
        refresh_pressures.append(np.asarray(mixed_epoch100["pressure_psi"],float).copy())

        stage="publication"
        gate("output_absent",not out.exists(),str(out));out.mkdir(parents=True)
        mixed_obs_bytes=deterministic_npz_bytes(mixed_obs)
        mixed_restart_bytes=deterministic_npz_bytes(mixed_restart)
        (out/MIXED_OBS).write_bytes(mixed_obs_bytes)
        (out/MIXED_RESTART).write_bytes(mixed_restart_bytes)

        np.savez_compressed(
            out/SNAPS,
            refresh_time_days=np.asarray(refresh_times,dtype=np.float64),
            mixed_refresh_saturation=np.stack(refresh_sats,axis=0),
            mixed_refresh_pressure_psi=np.stack(refresh_pressures,axis=0),
            exact_100d_saturation=truth_sat,
            exact_100d_refreshed_saturation=np.asarray(exact_rebuilt["transport_saturation"],float),
            exact_100d_refreshed_pressure_psi=np.asarray(exact_epoch100["pressure_psi"],float),
        )

        summary={
            "milestone":M,"status":PASS,
            "classification":"DAY100_PRODUCTION_LINEAGE_INTEGRATED_HYBRID_TRAJECTORY_VALIDATION_COMPLETE_SCIENTIFIC_INTERPRETATION_REQUIRED_BEFORE_PERFORMANCE_QUALIFICATION",
            "starting_parent_time_days":r3r7.EXPECTED_PARENT_TIME_DAYS,
            "target_day":TARGET_DAY,
            "production_max_flow_epoch_age_days":MAX_FLOW_EPOCH_DAYS,
            "accepted_transport_transition_count":len(step_rows),
            "total_flow_refresh_count":refresh_count,
            "cadence_refresh_count":cadence_refresh_count,
            "capacity_triggered_refresh_count":capacity_refresh_count,
            "capacity_controller_adjustment_count":capacity_adjustments_total,
            "capacity_limited_accepted_transition_count":capacity_limited_steps,
            "minimum_raw_capacity_margin_kg":float(np.min(capacity_margins)) if capacity_margins else None,
            "cumulative_Hybrid_route_uses":total_hybrid_routes,
            "cumulative_exact_fallback_route_uses":total_exact_fallback_routes,
            "mixed_100d_cumulative_mass_residual_kg":mixed_cum,
            "mixed_100d_vs_exact_saturation_relative_L2":sat_rel,
            "mixed_100d_vs_exact_saturation_Linf":sat_linf,
            "mixed_100d_vs_exact_saturation_MAE":sat_mae,
            "mixed_100d_minus_exact_stored_mass_kg":stored_diff,
            "mixed_100d_stored_mass_relative_error":stored_rel,
            "mixed_100d_minus_exact_cumulative_produced_mass_kg":produced_diff,
            "mixed_100d_cumulative_produced_mass_relative_error":produced_rel,
            "mixed_100d_minus_exact_producer_gas_cut":cut_diff,
            "mixed_100d_minus_exact_active_cell_count":active_count_diff,
            "mixed_100d_minus_exact_visible_cell_count":visible_count_diff,
            "mixed_vs_exact_100d_refreshed_pressure_relative_L2":pressure_rel,
            "mixed_vs_exact_100d_refreshed_flux_relative_L2":flux_rel,
            "mixed_vs_exact_100d_same_time_refreshed_saturation_relative_L2":post_refresh_sat_rel,
            "exact_refresh_rebuild_pressure_relative_L2_vs_frozen_restart":exact_restart_pressure_rel,
            "exact_refresh_rebuild_saturation_relative_L2_vs_frozen_restart":exact_restart_sat_rel,
            "AV5_learned_pressure_checkpoint_used":False,
            "temporal_pressure_seed_exact_FV_refresh_path_used":True,
            "Hybrid_parent_anchored_incremental_transport_used":True,
            "exact_E37A_fallback_used":True,
            "single_common_E37A_mapback_used":True,
            "conservative_capillary_used":True,
            "new_scientific_accuracy_threshold_defined":False,
            "production_canonical_chain_replaced":False,
            "trajectory_validation_complete":True,
            "scientific_interpretation_required":True,
            "G4_A9_performance_benchmark_review_ready":True,
            "integrated_GPU_runtime_production_authorized":False,
            "P4_authorized":False,
            "mixed_100d_observation_state_file":MIXED_OBS,
            "mixed_100d_observation_state_sha256":hashlib.sha256(mixed_obs_bytes).hexdigest(),
            "mixed_100d_refreshed_restart_file":MIXED_RESTART,
            "mixed_100d_refreshed_restart_sha256":hashlib.sha256(mixed_restart_bytes).hexdigest(),
            "exact_100d_observation_reference_sha256":EXACT_OBS_SHA,
            "exact_100d_restart_reference_sha256":EXACT_RESTART_SHA,
        }
        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        write_csv(out/STEPS,step_rows)
        write_csv(out/REFRESHES,refresh_rows)
        write_csv(out/CAPACITY,capacity_rows)
        write_csv(out/CONTROLLER,controller_rows)
        write_csv(out/ROUTES,route_rows)
        write_csv(out/GATES,gates)
        write_csv(out/MANIFEST,[{"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size}
                                for p in sorted(out.iterdir()) if p.is_file() and p.name!=MANIFEST])

        print("="*202);print(M,"PASS")
        print("Accepted transport transitions                :",len(step_rows))
        print("Flow refreshes / cadence / capacity            :",refresh_count,"/",cadence_refresh_count,"/",capacity_refresh_count)
        print("Capacity-controller adjustments                :",capacity_adjustments_total)
        print("Cumulative Hybrid / exact fallback route uses  :",total_hybrid_routes,"/",total_exact_fallback_routes)
        print("Day100 mixed vs exact saturation relL2         :",sat_rel)
        print("Day100 mixed vs exact saturation Linf          :",sat_linf)
        print("Day100 stored-mass relative error               :",stored_rel)
        print("Day100 produced-mass relative error             :",produced_rel)
        print("Day100 refreshed pressure relL2                 :",pressure_rel)
        print("Day100 refreshed flux relL2                     :",flux_rel)
        print("Mixed cumulative mass residual kg               :",mixed_cum)
        print("Scientific interpretation                      : REQUIRED BEFORE PERFORMANCE QUALIFICATION")
        print("="*202)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps({
            "milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),"gates":gates,
            "parent_state_sha256_before":parent_sha_before,
            "production_canonical_chain_replaced":False,
            "trajectory_validation_complete":False,
            "G4_A9_performance_benchmark_review_ready":False,
            "integrated_GPU_runtime_production_authorized":False,
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
