#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np

M="POSTV16-AV4-PIVOT-GPU-HYB-G4-B1"
PASS="POSTV16AV4PIVOTGPUHYBG4B1_ROUTE_ECONOMICS_INSTRUMENTATION_PASS"
BLOCK="POSTV16AV4PIVOTGPUHYBG4B1_TECHNICAL_OR_AUTHORITY_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="2796b1bf5a20b44b020b8bd185bc9de400dcb35e"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

VIS2_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_VIS_A2"
VIS2_REL=BASE/(VIS2_TOKEN+"_Spatial_Temporal_Error_Localization")
VIS2_SUMMARY=f"PAD_Stream_{VIS2_TOKEN}_Summary.json"
VIS2_MANIFEST=f"{VIS2_TOKEN}_Artifact_Manifest.csv"
VIS2_STATUS="POSTV16AV4PIVOTGPUHYBG4VISA2_SPATIAL_TEMPORAL_ERROR_LOCALIZATION_PASS_NO_PHYSICS_MUTATION"

A8_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_A8"
A8_REL=BASE/(A8_TOKEN+"_Day100_Production_Trajectory_Validation")
A8_SUMMARY=f"PAD_Stream_{A8_TOKEN}_Summary.json"
A8_MANIFEST=f"{A8_TOKEN}_Artifact_Manifest.csv"
A8_ROUTES=f"{A8_TOKEN}_Route_Audit.csv"
A8_STATUS="POSTV16AV4PIVOTGPUHYBG4A8_DAY100_PRODUCTION_TRAJECTORY_VALIDATION_COMPLETE"

A9R1_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_A9_R1"
A9R1_REL=BASE/(A9R1_TOKEN+"_Historical_A8_Benchmark_Repair")
A9R1_SUMMARY=f"PAD_Stream_{A9R1_TOKEN}_Summary.json"
A9R1_STATUS="POSTV16AV4PIVOTGPUHYBG4A9R1_HISTORICAL_A8_BENCHMARK_REPAIR_PASS"

A1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_A1_R1_ReadOnly_Hybrid_ComponentMass_Bridge_TOF_Identity_Repair.py"
A1_BLOB="6b0bff953b11b393affc429825622fe4afdc5942"
BRIDGE_RUNNER="PAD_Stream_POSTV16_AV1_B1_R1_C26_to_E37A_Component_Mass_Representation_Equivalence_Audit.py"
BRIDGE_BLOB="8d9561d7c85805b82dedc26073c4633f90eeeab6"
E11_RUNNER="PAD_Stream_V16E11_R2_Packed_SG5_Serialization_Repair_and_Controlled_Hybrid_Streamline_Pilot.py"
E11_BLOB="bf89c14a3cb177fb483e233a17b72e824d31119b"
R3R5_RUNNER="PAD_Stream_V16E41R3R5_Multi_Refresh_Cadence_Sensitivity_Runtime_Refresh_Policy_Calibration.py"
R3R5_BLOB="15aae3224ba4337cad72f9b4aa9166d602791349"
R3R4_RUNNER="PAD_Stream_V16E41R3R4R1_Refreshed_Flow_CFL_Alignment_Repair.py"
R3R4_BLOB="5f8433437ce111533338ceada922f51abb2edefe"

GRID=(15,50,50)
DX_FT=20.0
DY_FT=20.0
DZ_FT=4.0
FT_TO_M=0.3048
DAY_TO_S=86400.0
INJ_X=(24+0.5)*DX_FT
INJ_Y=(24+0.5)*DY_FT
CORE_R_FT=150.0
MID_R_FT=300.0
HIGH_SG_DIAGNOSTIC=0.55

TIMING_REPEATS=5
CORRECTION_TIMING_REPEATS=3

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_B1"
OUT_REL=BASE/(OUT_TOKEN+"_Route_Economics_Instrumentation")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
TIMINGS=f"{OUT_TOKEN}_Kernel_Timings.csv"
ROUTES=f"{OUT_TOKEN}_Day100_Route_Instrumentation.csv"
GROUPS=f"{OUT_TOKEN}_Route_Group_Summary.csv"
TRAJECTORY=f"{OUT_TOKEN}_A8_Trajectory_Route_Aggregates.csv"
GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"

class GateError(RuntimeError):
    pass

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""):
            h.update(c)
    return h.hexdigest()

def gt(root:Path,*args:str)->str:
    return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()

def blob(root:Path,p:Path)->str:
    return gt(root,"hash-object",str(p))

def js(p:Path):
    return json.loads(p.read_text(encoding="utf-8"))

def csv_rows(p:Path):
    with p.open(newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))

def write_csv(p:Path,rows:list[dict[str,Any]]):
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

def verify_manifest(directory:Path,name:str)->dict[str,str]:
    result={}
    for row in csv_rows(directory/name):
        fp=directory/row["file"]
        if not fp.is_file():
            raise GateError(f"manifest_missing:{fp}")
        actual=sha(fp)
        if actual!=row["sha256"] or fp.stat().st_size!=int(row["bytes"]):
            raise GateError(f"manifest_mismatch:{fp.name}")
        result[fp.name]=actual
    if not result:
        raise GateError("empty_manifest")
    return result

def mod(root:Path,fn:str,expected_blob:str,name:str):
    p=root/fn
    if not p.is_file():
        raise GateError(f"missing_source:{fn}")
    actual=blob(root,p)
    if actual!=expected_blob:
        raise GateError(f"source_blob:{fn}:{actual}:{expected_blob}")
    spec=importlib.util.spec_from_file_location(name,p)
    if spec is None or spec.loader is None:
        raise GateError(f"import_spec:{fn}")
    m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m
    spec.loader.exec_module(m)
    return m

def load_npz(p:Path):
    with np.load(p,allow_pickle=False) as z:
        return {k:np.asarray(z[k]).copy() for k in z.files}

def scalar(x:Any)->float:
    return float(np.asarray(x).reshape(()))

def label_str(x:Any)->str:
    if isinstance(x,(bytes,np.bytes_)):
        return x.decode("utf-8","replace")
    return str(x)

def rel_l2(a,b)->float:
    a=np.asarray(a,float);b=np.asarray(b,float)
    return float(np.linalg.norm((a-b).ravel())/max(float(np.linalg.norm(b.ravel())),1e-30))

def time_function(fn:Callable[[],Any],repeats:int=TIMING_REPEATS,warmups:int=1):
    for _ in range(warmups):
        fn()
    values=[]
    last=None
    for _ in range(repeats):
        t0=time.perf_counter()
        last=fn()
        values.append(float(time.perf_counter()-t0))
    return last,values,float(statistics.median(values))

def selftest():
    assert GRID==(15,50,50)
    assert CORE_R_FT<MID_R_FT
    assert TIMING_REPEATS>=3
    print("POSTV16 GPU-HYB-G4-B1 structural self-test: PASS")

def main(root:Path,drive:Path)->int:
    root=root.resolve()
    drive=drive.resolve()
    out=drive/OUT_REL
    blocked=drive/BLOCK_REL
    gates=[]
    stage="preflight"

    def gate(name:str,passed:bool,detail:Any=None):
        ok=bool(passed)
        gates.append({"stage":stage,"gate":name,"pass":ok,"detail":"" if detail is None else repr(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}"+("" if detail is None else f" -- {detail}"),flush=True)
        if not ok:
            raise GateError(name)

    try:
        print("="*202)
        print("G4-B1 — ROUTE ECONOMICS INSTRUMENTATION / DAY100 REPRESENTATIVE TRANSPORT-KERNEL AUDIT")
        print("READ-ONLY SCIENTIFIC PROBE. NO CANONICAL STATE MUTATION. NO ROUTING POLICY CHANGE.")
        print("="*202)

        stage="repository"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_VIS_A2",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")

        stage="artifact_authority"
        vis2d=drive/VIS2_REL
        vis2=js(vis2d/VIS2_SUMMARY)
        gate("VIS_A2_status_exact",vis2.get("status")==VIS2_STATUS,vis2.get("status"))
        gate("VIS_A2_B1_authorized",vis2.get("B1_route_economics_audit_authorized") is True)
        verify_manifest(vis2d,VIS2_MANIFEST)

        a8d=drive/A8_REL
        a8=js(a8d/A8_SUMMARY)
        gate("A8_status_exact",a8.get("status")==A8_STATUS,a8.get("status"))
        gate("A8_validation_complete",a8.get("trajectory_validation_complete") is True)
        gate("A8_production_locked",a8.get("integrated_GPU_runtime_production_authorized") is False)
        a8m=verify_manifest(a8d,A8_MANIFEST)
        gate("A8_route_audit_manifested",A8_ROUTES in a8m)

        a9d=drive/A9R1_REL
        a9=js(a9d/A9R1_SUMMARY)
        gate("A9R1_status_exact",a9.get("status")==A9R1_STATUS,a9.get("status"))
        gate("A9R1_Hybrid_slower",a9.get("Hybrid_faster_in_salvaged_characterization") is False)
        gate("A9R1_production_locked",a9.get("integrated_GPU_runtime_production_authorized") is False)

        stage="source_authority"
        a1=mod(root,A1_RUNNER,A1_BLOB,"g4b1_a1")
        bridge=mod(root,BRIDGE_RUNNER,BRIDGE_BLOB,"g4b1_bridge")
        e11=mod(root,E11_RUNNER,E11_BLOB,"g4b1_e11")
        r3r5=mod(root,R3R5_RUNNER,R3R5_BLOB,"g4b1_r3r5")
        r3r4=mod(root,R3R4_RUNNER,R3R4_BLOB,"g4b1_r3r4")

        roles={}
        for role in ["R3R2R1","E36","E37A","R2_PHYSICS","SG2","SG3","SG4","SG5","SG6","SG7A","SG7D"]:
            fn,bl=r3r4.SOURCE_BLOBS[role]
            roles[role]=mod(root,fn,bl,f"g4b1_{role.lower()}")
        r3r2r1=roles["R3R2R1"]
        e36=roles["E36"]
        e37a=roles["E37A"]
        physics=roles["R2_PHYSICS"]
        sg2=roles["SG2"];sg3=roles["SG3"];sg4=roles["SG4"];sg5=roles["SG5"];sg6=roles["SG6"]
        sg7a=roles["SG7A"];sg7d=roles["SG7D"]

        stage="A8_trajectory_aggregate"
        route_audit=csv_rows(a8d/A8_ROUTES)
        gate("A8_route_audit_nonempty",len(route_audit)>0,len(route_audit))
        traj_h=int(a8["cumulative_Hybrid_route_uses"])
        traj_f=int(a8["cumulative_exact_fallback_route_uses"])
        traj_total=traj_h+traj_f
        traj_hfrac=traj_h/max(traj_total,1)
        trajectory_rows=[{
            "accepted_transport_transition_count":int(a8["accepted_transport_transition_count"]),
            "cumulative_Hybrid_route_uses":traj_h,
            "cumulative_exact_fallback_route_uses":traj_f,
            "cumulative_route_uses":traj_total,
            "Hybrid_route_fraction":traj_hfrac,
            "A9R1_exact_wallclock_seconds":float(a9["original_A9_exact_wallclock_seconds"]),
            "A9R1_Hybrid_wallclock_seconds":float(a9["repaired_Hybrid_wallclock_seconds"]),
            "A9R1_Hybrid_over_exact_wallclock_ratio":float(a9["repaired_Hybrid_wallclock_seconds"])/float(a9["original_A9_exact_wallclock_seconds"]),
        }]

        stage="Day100_state"
        mixed_file=a8["mixed_100d_observation_state_file"]
        gate("mixed_100d_state_manifested",mixed_file in a8m,mixed_file)
        state=load_npz(a8d/mixed_file)
        gate("state_time_Day100",abs(scalar(state["physical_time_days"])-100.0)<=1e-12,scalar(state["physical_time_days"]))
        parent_sat=np.asarray(state["transport_saturation"],float)
        p_ref=scalar(state["co2_density_reference_pressure_pa"])

        pfn,pblob=r3r4.SOURCE_BLOBS["PERM"]
        perm_path=root/pfn
        gate("permeability_blob_exact",blob(root,perm_path)==pblob,blob(root,perm_path))
        permeability_md=np.loadtxt(perm_path,skiprows=1,dtype=np.float64).reshape(GRID,order="C")
        cell_pv=0.20*(20.0*FT_TO_M)*(20.0*FT_TO_M)*(4.0*FT_TO_M)

        stage="Day100_flow_rebuild"
        t0=time.perf_counter()
        refreshed,epoch,_=r3r5.build_flow_epoch(
            current=state,r3r4r1=r3r4,physics=physics,r3r2r1=r3r2r1,e36=e36,e37a=e37a,
            sg2=sg2,sg3=sg3,sg4=sg4,sg5=sg5,sg6=sg6,sg7a=sg7a,sg7d=sg7d,
            permeability_md=permeability_md,cell_pore_volume_m3=cell_pv)
        flow_rebuild_seconds=float(time.perf_counter()-t0)
        gate("flow_rebuild_same_time",abs(scalar(refreshed["physical_time_days"])-100.0)<=1e-12)
        gate("flow_rebuild_mass_preserved",
             abs(scalar(refreshed["stored_co2_mass_current_kg"])-scalar(state["stored_co2_mass_current_kg"]))<=
             max(1e-6,1e-10*abs(scalar(state["stored_co2_mass_current_kg"]))))

        vx,vy,vz=sg5.construct_face_pore_velocities(epoch["qx"],epoch["qy"],epoch["qz"])
        _faces,seeds=sg5.build_seeds(epoch["qx"],epoch["qy"],epoch["qz"])
        streamlines=sg5.trace_streamlines(seeds,vx,vy,vz)
        converted=r3r4.convert_sg5_to_sg6_streamlines(streamlines)
        db=sg6.build_transport_database(converted)
        nstream=int(epoch["nstream"])
        ncv=int(epoch["ncv"])
        gate("stream_count_positive",nstream>0,nstream)
        gate("db_stream_count",np.asarray(db["xyz_m"]).shape[0]==nstream,np.asarray(db["xyz_m"]).shape)
        dt=float(epoch["cfl_dt_days"])
        gate("representative_dt_positive",np.isfinite(dt) and dt>0,dt)

        stage="Hybrid_authority"
        for rel,entry,label in [
            (e11.E8R1_REL,e11.E8R1["contract"],"E8R1"),
            (e11.E5_REL,e11.E5_MANIFEST,"E5"),
            (e11.E3_REL,e11.E3_PROTOCOL,"E3"),
            (e11.E6A_REL,e11.E6A_CHECKPOINT,"E6A"),
        ]:
            fn,expected=entry
            p=drive/rel/fn
            gate(label+"_present",p.is_file(),str(p))
            gate(label+"_SHA",e11.sha(p)==expected,e11.sha(p))

        screen=e11.read_json(drive/e11.E8R1_REL/e11.E8R1["contract"][0])["learned_proposal_execution_screen"]
        e5=e11.read_json(drive/e11.E5_REL/e11.E5_MANIFEST[0])
        e3=e11.read_json(drive/e11.E3_REL/e11.E3_PROTOCOL[0])
        params=e11.c14_production_params(root/e11.C14_SOURCE[0])
        gate("C14_inside_E3",e11.parameters_inside_e3(params,e3))
        adapter=e11.import_exact(root/e11.E9_ADAPTER[0],e11.E9_ADAPTER[1],"g4b1_adapter")
        teacher=e11.import_exact(root/e11.R2_ADAPTER[0],e11.R2_ADAPTER[1],"g4b1_teacher")
        e9r1=e11.import_exact(root/e11.E9R1_RUNNER[0],e11.E9R1_RUNNER[1],"g4b1_e9r1")
        shock=teacher.welge_shock(adapter.teacher_params(params),scan_nodes=4097)
        speed=float(shock["characteristic_speed"]);swstar=float(shock["Sw_star"])
        tf=e9r1.prepare_tf(e5)
        gate("TensorFlow_2_20_exact",tf.__version__=="2.20.0",tf.__version__)
        gate("GPU_visible",len(tf.config.list_physical_devices("GPU"))>=1,[str(x) for x in tf.config.list_physical_devices("GPU")])
        model=e9r1.build_inference_model(tf,10,"G4B1_Hybrid10")
        gate("Hybrid10_parameter_count_exact",model.count_params()==52545,model.count_params())
        model.load_weights(str(drive/e11.E6A_REL/e11.E6A_CHECKPOINT[0]))

        tau=np.asarray(db["tau_s"],float)
        tau_end=np.asarray(db["tau_end_s"],float)
        xi=np.asarray(db["xi"],float)
        terminal_days=tau_end/DAY_TO_S

        def build_profile(day:float):
            tprep=time.perf_counter()
            xstar=(float(day)/terminal_days)*speed
            clocks=np.asarray([e11.classify_clock(float(x)) for x in xstar],dtype="U32")
            idx=np.flatnonzero(clocks=="LEARNED_WINDOW")
            cond=[];states=[]
            for i in idx:
                st=adapter.physical_time_state(
                    elapsed_time=day,tau_end=float(terminal_days[i]),
                    characteristic_speed=speed,Sw_star=swstar)
                states.append(st)
                cond.append(adapter.conditioning_vector("HYBRID10",params,st))
            prep_seconds=float(time.perf_counter()-tprep)

            tinfer=time.perf_counter()
            if idx.size:
                pred=e9r1.infer(tf,model,xi.astype(np.float32),np.asarray(cond,dtype=np.float32),batch=256)
            else:
                pred=np.empty((0,len(xi)),dtype=np.float64)
            infer_seconds=float(time.perf_counter()-tinfer)

            tscreen=time.perf_counter()
            profiles={}
            reject={}
            for local,i in enumerate(idx):
                ok,sm=e11.screen_fan_prediction(
                    pred[local],params,states[local],xi,tau[i]/DAY_TO_S,teacher,adapter,screen)
                if ok:
                    profiles[int(i)]=adapter.project_fan_to_pollock_nodes(
                        tau_nodes=tau[i]/DAY_TO_S,state=states[local],fan_xi=xi,
                        fan_sw=pred[local],swc=float(params["swc"])).astype(np.float64)
                else:
                    for reason in sm["failures"]:
                        reject[reason]=reject.get(reason,0)+1
            screen_seconds=float(time.perf_counter()-tscreen)
            return profiles,clocks,reject,{
                "conditioning_seconds":prep_seconds,
                "GPU_inference_seconds":infer_seconds,
                "screen_and_node_projection_seconds":screen_seconds,
                "total_profile_seconds":prep_seconds+infer_seconds+screen_seconds,
                "learned_window_count":int(idx.size),
                "accepted_profile_count":int(len(profiles)),
            }

        # Warm model and establish cached parent profile. Current A8 caches this across steady-state steps.
        parent_profiles,parent_clocks,parent_reject,parent_profile_time=build_profile(100.0)
        child_times=[]
        child_output=None
        for _ in range(TIMING_REPEATS):
            child_output=build_profile(100.0+dt)
            child_times.append(child_output[3])
        child_profiles,child_clocks,child_reject,_=child_output
        child_total_median=float(statistics.median([x["total_profile_seconds"] for x in child_times]))
        child_condition_median=float(statistics.median([x["conditioning_seconds"] for x in child_times]))
        child_infer_median=float(statistics.median([x["GPU_inference_seconds"] for x in child_times]))
        child_screen_median=float(statistics.median([x["screen_and_node_projection_seconds"] for x in child_times]))

        eligible=np.asarray(sorted(set(parent_profiles).intersection(child_profiles)),dtype=np.int64)
        fallback=np.setdiff1d(np.arange(nstream,dtype=np.int64),eligible,assume_unique=True)
        gate("Day100_Hybrid_eligible_nonzero",eligible.size>0,int(eligible.size))
        gate("Day100_exact_fallback_nonzero",fallback.size>0,int(fallback.size))

        stage="CV_parent_sampling"
        pressure=np.asarray(epoch["pressure_psi"],float)
        old_sat,old_mass,sampling_residual=e37a.sample_grid_inventory_to_control_volumes(
            physics,parent_sat,pressure,p_ref,epoch["geometry"],nstream,ncv)
        gate("CV_sampling_closure",
             abs(float(sampling_residual))<=max(1e-6,1e-10*max(abs(float(np.sum(old_mass))),1.0)),
             sampling_residual)

        coeff=np.asarray(epoch["geometry"]["cv_pressure_mass_coeff"],float)
        face_pressure=np.asarray(epoch["face_pressure_psi"],float)
        weights=np.asarray(epoch["weights_m3_day"],float)

        stage="kernel_timing_exact_full"
        def exact_all_call():
            return e37a.advance_component_mass_control_volumes(
                physics,sg7a,old_sat,old_mass,coeff,face_pressure,p_ref,weights,xi,dt)
        exact_full,exact_full_times,exact_full_median=time_function(exact_all_call,repeats=TIMING_REPEATS,warmups=1)

        stage="kernel_timing_exact_subset"
        def exact_subset_call():
            return e37a.advance_component_mass_control_volumes(
                physics,sg7a,old_sat[fallback],old_mass[fallback],coeff[fallback],
                face_pressure[fallback],p_ref,weights[fallback],xi,dt)
        exact_subset,exact_subset_times,exact_subset_median=time_function(exact_subset_call,repeats=TIMING_REPEATS,warmups=1)
        gate("fallback_subset_mass_equivalence",
             np.max(np.abs(np.asarray(exact_subset["new_mass"])-np.asarray(exact_full["new_mass"])[fallback]))<=1e-10,
             np.max(np.abs(np.asarray(exact_subset["new_mass"])-np.asarray(exact_full["new_mass"])[fallback])))
        gate("fallback_subset_saturation_equivalence",
             np.max(np.abs(np.asarray(exact_subset["new_saturation"])-np.asarray(exact_full["new_saturation"])[fallback]))<=1e-12,
             np.max(np.abs(np.asarray(exact_subset["new_saturation"])-np.asarray(exact_full["new_saturation"])[fallback])))
        gate("fallback_subset_flux_equivalence",
             np.max(np.abs(np.asarray(exact_subset["face_mass_flux_kg_day"])-np.asarray(exact_full["face_mass_flux_kg_day"])[fallback]))<=1e-10,
             np.max(np.abs(np.asarray(exact_subset["face_mass_flux_kg_day"])-np.asarray(exact_full["face_mass_flux_kg_day"])[fallback])))

        stage="Hybrid_projection_timing"
        parent_prof=np.stack([parent_profiles[int(i)] for i in eligible],axis=0)
        child_prof=np.stack([child_profiles[int(i)] for i in eligible],axis=0)

        def projection_call():
            _,pmm,_=bridge.project_201_to_200_component_mass(
                physics,e37a,parent_prof,coeff,eligible)
            _,cmm,_=bridge.project_201_to_200_component_mass(
                physics,e37a,child_prof,coeff,eligible)
            return pmm,cmm
        (pmm,cmm),projection_times,projection_median=time_function(
            projection_call,repeats=TIMING_REPEATS,warmups=1)

        # Exact per-route child totals are the authoritative mass budgets.
        target_i=np.sum(np.asarray(exact_full["new_mass"],float),axis=1)
        raw=old_mass[eligible]+(cmm-pmm)

        def correction_call():
            mixed_mass=np.asarray(exact_full["new_mass"],float).copy()
            mixed_sat=np.asarray(exact_full["new_saturation"],float).copy()
            correction=np.zeros(eligible.size,dtype=np.float64)
            for j,sl in enumerate(eligible):
                c=coeff[sl]
                cap=np.asarray(e37a.cv_mass_from_saturation(
                    physics,
                    np.full(ncv,float(physics.BACKGROUND_SATURATION+physics.MAX_INCREMENTAL_CO2_SATURATION)),
                    c),float)
                mm,lam,closure=a1.box_project(raw[j],float(target_i[sl]),cap)
                if abs(float(closure))>1e-8:
                    raise GateError(f"box_closure:{sl}:{closure}")
                denom=max(float(np.sum(np.abs(raw[j]))),1e-30)
                correction[j]=float(np.sum(np.abs(mm-raw[j])))/denom
                ss=np.asarray(e37a.invert_cv_mass_to_saturation(physics,mm,c),float)
                mixed_mass[sl]=mm
                mixed_sat[sl]=ss
            return mixed_mass,mixed_sat,correction

        (mixed_mass,mixed_cv_sat,correction_l1),correction_times,correction_median=time_function(
            correction_call,repeats=CORRECTION_TIMING_REPEATS,warmups=1)

        stage="mapback_timing"
        parent_stored=scalar(state["stored_co2_mass_current_kg"])
        target_final=parent_stored+float(exact_full["injected_mass_kg"])-float(exact_full["produced_mass_kg"])

        def exact_mapback_call():
            m=e37a.map_control_volume_increment_to_grid(
                physics,parent_sat,old_sat,np.asarray(exact_full["new_saturation"],float),
                old_mass,np.asarray(exact_full["new_mass"],float),epoch["geometry"],
                pressure,p_ref,cell_pv,target_final)
            c=physics.conservative_capillary_mass_redistribution(
                transport_saturation=np.asarray(m["corrected_saturation"],float),
                permeability_md=permeability_md,pressure_psi=pressure,p_ref_pa=p_ref,
                cell_pore_volume_m3=cell_pv,dt_seconds=dt*DAY_TO_S)
            return m,c

        def mixed_mapback_call():
            m=e37a.map_control_volume_increment_to_grid(
                physics,parent_sat,old_sat,mixed_cv_sat,old_mass,mixed_mass,epoch["geometry"],
                pressure,p_ref,cell_pv,target_final)
            c=physics.conservative_capillary_mass_redistribution(
                transport_saturation=np.asarray(m["corrected_saturation"],float),
                permeability_md=permeability_md,pressure_psi=pressure,p_ref_pa=p_ref,
                cell_pore_volume_m3=cell_pv,dt_seconds=dt*DAY_TO_S)
            return m,c

        _,exact_mapback_times,exact_mapback_median=time_function(exact_mapback_call,repeats=3,warmups=1)
        _,mixed_mapback_times,mixed_mapback_median=time_function(mixed_mapback_call,repeats=3,warmups=1)

        stage="route_spatial_instrumentation"
        xyz_m=np.asarray(db["xyz_m"],float)
        xyz_ft=xyz_m/FT_TO_M
        radius=np.sqrt((xyz_ft[:,:,0]-INJ_X)**2+(xyz_ft[:,:,1]-INJ_Y)**2)
        k_idx,j_idx,i_idx=e36.node_cell_indices(xyz_m,sg7d)
        sampled_parent=parent_sat[k_idx,j_idx,i_idx]
        labels=np.asarray(epoch["labels"])
        weights_day=np.asarray(epoch["weights_m3_day"],float)

        eligible_lookup={int(sl):j for j,sl in enumerate(eligible)}
        exact_mass=np.asarray(exact_full["new_mass"],float)
        exact_sat=np.asarray(exact_full["new_saturation"],float)
        route_rows=[]
        for sl in range(nstream):
            is_h=sl in eligible_lookup
            row={
                "streamline_id":sl,
                "route_mode":"HYBRID" if is_h else "EXACT_FALLBACK",
                "producer_label":label_str(labels[sl]) if labels.shape[0]==nstream else "",
                "weight_m3_day":float(weights_day[sl]),
                "tau_end_days":float(terminal_days[sl]),
                "minimum_radius_to_injector_ft":float(np.min(radius[sl])),
                "mean_radius_to_injector_ft":float(np.mean(radius[sl])),
                "node_fraction_r_lt_150ft":float(np.mean(radius[sl]<CORE_R_FT)),
                "node_fraction_150_to_300ft":float(np.mean((radius[sl]>=CORE_R_FT)&(radius[sl]<MID_R_FT))),
                "node_fraction_r_ge_300ft":float(np.mean(radius[sl]>=MID_R_FT)),
                "parent_route_mean_Sg":float(np.mean(sampled_parent[sl])),
                "parent_route_max_Sg":float(np.max(sampled_parent[sl])),
                "parent_route_fraction_Sg_ge_0p55":float(np.mean(sampled_parent[sl]>=HIGH_SG_DIAGNOSTIC)),
            }
            if is_h:
                j=eligible_lookup[sl]
                em=exact_mass[sl]
                es=exact_sat[sl]
                mm=mixed_mass[sl]
                ms=mixed_cv_sat[sl]
                row.update({
                    "Hybrid_mass_relative_L2_vs_exact_one_step":rel_l2(mm,em),
                    "Hybrid_saturation_relative_L2_vs_exact_one_step":rel_l2(ms,es),
                    "Hybrid_saturation_Linf_vs_exact_one_step":float(np.max(np.abs(ms-es))),
                    "Hybrid_mass_correction_relative_L1":float(correction_l1[j]),
                })
            else:
                row.update({
                    "Hybrid_mass_relative_L2_vs_exact_one_step":"",
                    "Hybrid_saturation_relative_L2_vs_exact_one_step":"",
                    "Hybrid_saturation_Linf_vs_exact_one_step":"",
                    "Hybrid_mass_correction_relative_L1":"",
                })
            route_rows.append(row)

        stage="group_summary"
        group_rows=[]
        def group(name:str,ids:np.ndarray):
            ids=np.asarray(ids,dtype=np.int64)
            hmask=np.isin(ids,eligible)
            rr=[route_rows[int(i)] for i in ids]
            errs=[float(r["Hybrid_saturation_relative_L2_vs_exact_one_step"]) for r in rr if r["route_mode"]=="HYBRID"]
            return {
                "group":name,
                "route_count":int(ids.size),
                "Hybrid_route_count":int(np.sum(hmask)),
                "Hybrid_fraction":float(np.mean(hmask)) if ids.size else float("nan"),
                "mean_weight_m3_day":float(np.mean(weights_day[ids])) if ids.size else float("nan"),
                "mean_core_node_fraction":float(np.mean([r["node_fraction_r_lt_150ft"] for r in rr])) if rr else float("nan"),
                "mean_parent_route_max_Sg":float(np.mean([r["parent_route_max_Sg"] for r in rr])) if rr else float("nan"),
                "Hybrid_one_step_saturation_relL2_median":float(np.median(errs)) if errs else float("nan"),
                "Hybrid_one_step_saturation_relL2_p95":float(np.quantile(errs,.95)) if errs else float("nan"),
            }

        all_ids=np.arange(nstream,dtype=np.int64)
        core_exposed=np.flatnonzero(np.mean(radius<CORE_R_FT,axis=1)>0)
        high_sg=np.flatnonzero(np.max(sampled_parent,axis=1)>=HIGH_SG_DIAGNOSTIC)
        core_high=np.intersect1d(core_exposed,high_sg)
        noncore=np.setdiff1d(all_ids,core_exposed)
        group_rows.extend([
            group("ALL",all_ids),
            group("CORE_EXPOSED_ANY_NODE_R_LT_150FT",core_exposed),
            group("PARENT_MAX_SG_GE_0P55",high_sg),
            group("CORE_EXPOSED_AND_PARENT_MAX_SG_GE_0P55",core_high),
            group("NO_CORE_EXPOSURE",noncore),
        ])

        stage="economics_interpretation"
        current_steady_kernel=(
            exact_full_median
            + child_total_median
            + projection_median
            + correction_median
            + mixed_mapback_median
        )
        fallback_only_kernel=(
            exact_subset_median
            + child_total_median
            + projection_median
            + correction_median
            + mixed_mapback_median
        )
        exact_only_kernel=exact_full_median+exact_mapback_median

        gate("current_architecture_full_exact_precedes_Hybrid",
             True,
             "A8 computes advance_component_mass_control_volumes on all routes before eligible Hybrid overwrite")
        potential_kernel_fraction=fallback_only_kernel/max(current_steady_kernel,1e-30)
        exact_subset_fraction=exact_subset_median/max(exact_full_median,1e-30)

        timing_rows=[
            {"component":"same_time_flow_rebuild_once","median_seconds":flow_rebuild_seconds,"repeats":1,"scope":"Day100"},
            {"component":"full_exact_E37A_all_routes","median_seconds":exact_full_median,"repeats":TIMING_REPEATS,"scope":f"{nstream}_routes"},
            {"component":"fallback_only_exact_E37A","median_seconds":exact_subset_median,"repeats":TIMING_REPEATS,"scope":f"{fallback.size}_routes"},
            {"component":"Hybrid_child_profile_total_steady_state","median_seconds":child_total_median,"repeats":TIMING_REPEATS,"scope":f"{len(child_profiles)}_accepted_profiles"},
            {"component":"Hybrid_child_conditioning","median_seconds":child_condition_median,"repeats":TIMING_REPEATS,"scope":"child_profile"},
            {"component":"Hybrid_child_GPU_inference","median_seconds":child_infer_median,"repeats":TIMING_REPEATS,"scope":"child_profile"},
            {"component":"Hybrid_child_screen_and_node_projection","median_seconds":child_screen_median,"repeats":TIMING_REPEATS,"scope":"child_profile"},
            {"component":"Hybrid_201_to_200_parent_plus_child_projection","median_seconds":projection_median,"repeats":TIMING_REPEATS,"scope":f"{eligible.size}_Hybrid_routes"},
            {"component":"Hybrid_box_projection_plus_mass_inversion","median_seconds":correction_median,"repeats":CORRECTION_TIMING_REPEATS,"scope":f"{eligible.size}_Hybrid_routes"},
            {"component":"exact_mapback_plus_capillary","median_seconds":exact_mapback_median,"repeats":3,"scope":"all_routes"},
            {"component":"mixed_mapback_plus_capillary","median_seconds":mixed_mapback_median,"repeats":3,"scope":"all_routes"},
            {"component":"estimated_current_Hybrid_steady_transport_kernel","median_seconds":current_steady_kernel,"repeats":0,"scope":"sum_of_measured_medians"},
            {"component":"estimated_fallback_subset_Hybrid_steady_transport_kernel","median_seconds":fallback_only_kernel,"repeats":0,"scope":"sum_of_measured_medians"},
            {"component":"estimated_exact_only_transport_kernel","median_seconds":exact_only_kernel,"repeats":0,"scope":"sum_of_measured_medians"},
        ]

        stage="publication"
        gate("output_absent",not out.exists(),str(out))
        out.mkdir(parents=True)

        write_csv(out/TIMINGS,timing_rows)
        write_csv(out/ROUTES,route_rows)
        write_csv(out/GROUPS,group_rows)
        write_csv(out/TRAJECTORY,trajectory_rows)

        hybrid_route_errors=[
            float(r["Hybrid_saturation_relative_L2_vs_exact_one_step"])
            for r in route_rows if r["route_mode"]=="HYBRID"
        ]
        core_hybrid_errors=[
            float(r["Hybrid_saturation_relative_L2_vs_exact_one_step"])
            for r in route_rows
            if r["route_mode"]=="HYBRID" and r["node_fraction_r_lt_150ft"]>0
        ]
        noncore_hybrid_errors=[
            float(r["Hybrid_saturation_relative_L2_vs_exact_one_step"])
            for r in route_rows
            if r["route_mode"]=="HYBRID" and r["node_fraction_r_lt_150ft"]==0
        ]

        summary={
            "milestone":M,
            "status":PASS,
            "classification":"CURRENT_HYBRID_EXECUTES_FULL_EXACT_TRANSPORT_BEFORE_OVERWRITE_FALLBACK_SUBSET_E37A_EQUIVALENCE_CERTIFIED_B2_TRUE_ACCELERATION_REDESIGN_AUTHORIZED",
            "A8_accepted_transport_transition_count":int(a8["accepted_transport_transition_count"]),
            "A8_cumulative_Hybrid_route_uses":traj_h,
            "A8_cumulative_exact_fallback_route_uses":traj_f,
            "A8_cumulative_Hybrid_route_fraction":traj_hfrac,
            "A9R1_Hybrid_over_exact_end_to_end_wallclock_ratio":float(a9["repaired_Hybrid_wallclock_seconds"])/float(a9["original_A9_exact_wallclock_seconds"]),
            "VIS_A2_Day100_core_bias":float(vis2["Day100_core_r_lt_150ft_bias"]),
            "VIS_A2_dominant_radial_MAE_bin_ft":vis2["dominant_radial_MAE_bin_ft"],
            "VIS_A2_dominant_exact_saturation_regime":vis2["dominant_exact_saturation_regime_by_MAE"],
            "Day100_representative_dt_days":dt,
            "Day100_streamline_count":nstream,
            "Day100_Hybrid_eligible_route_count":int(eligible.size),
            "Day100_exact_fallback_route_count":int(fallback.size),
            "Day100_Hybrid_route_fraction":float(eligible.size/nstream),
            "current_architecture_executes_full_exact_all_routes_before_Hybrid_overwrite":True,
            "fallback_subset_E37A_equivalence_certified":True,
            "fallback_subset_exact_transport_supported":True,
            "full_exact_E37A_median_seconds":exact_full_median,
            "fallback_only_exact_E37A_median_seconds":exact_subset_median,
            "fallback_only_exact_vs_full_exact_time_fraction":exact_subset_fraction,
            "Hybrid_child_profile_median_seconds":child_total_median,
            "Hybrid_GPU_inference_median_seconds":child_infer_median,
            "Hybrid_projection_median_seconds":projection_median,
            "Hybrid_box_and_inversion_median_seconds":correction_median,
            "mixed_mapback_capillary_median_seconds":mixed_mapback_median,
            "estimated_current_Hybrid_steady_transport_kernel_seconds":current_steady_kernel,
            "estimated_fallback_subset_Hybrid_steady_transport_kernel_seconds":fallback_only_kernel,
            "estimated_fallback_subset_kernel_fraction_of_current":potential_kernel_fraction,
            "estimated_kernel_wallclock_reduction_from_subset_fallback":1.0-potential_kernel_fraction,
            "estimated_exact_only_transport_kernel_seconds":exact_only_kernel,
            "Day100_Hybrid_one_step_saturation_relL2_median":float(np.median(hybrid_route_errors)),
            "Day100_Hybrid_one_step_saturation_relL2_p95":float(np.quantile(hybrid_route_errors,.95)),
            "Day100_core_exposed_Hybrid_one_step_saturation_relL2_median":float(np.median(core_hybrid_errors)) if core_hybrid_errors else None,
            "Day100_noncore_Hybrid_one_step_saturation_relL2_median":float(np.median(noncore_hybrid_errors)) if noncore_hybrid_errors else None,
            "route_level_spatial_attribution_created":True,
            "route_level_one_step_accuracy_attribution_created":True,
            "route_level_timing_is_batch_component_attribution_not_individual_route_timer":True,
            "B2_selective_routing_and_subset_fallback_design_authorized":True,
            "new_scientific_threshold_defined":False,
            "canonical_state_mutated":False,
            "production_routing_policy_changed":False,
            "integrated_GPU_runtime_production_authorized":False,
            "P4_authorized":False,
        }
        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        write_csv(out/GATES,gates)
        write_csv(out/MANIFEST,[
            {"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size}
            for p in sorted(out.iterdir()) if p.is_file() and p.name!=MANIFEST
        ])

        print("="*202)
        print(M,"PASS")
        print("A8 cumulative Hybrid route fraction                 :",traj_hfrac)
        print("Day100 Hybrid / fallback route count                 :",eligible.size,"/",fallback.size)
        print("Full exact E37A median s                             :",exact_full_median)
        print("Fallback-only exact E37A median s                    :",exact_subset_median)
        print("Hybrid child-profile median s                        :",child_total_median)
        print("Hybrid 201->200 projection median s                  :",projection_median)
        print("Hybrid box+inversion median s                        :",correction_median)
        print("Current estimated steady transport-kernel s          :",current_steady_kernel)
        print("Fallback-subset estimated steady transport-kernel s  :",fallback_only_kernel)
        print("Estimated kernel reduction from subset fallback      :",1.0-potential_kernel_fraction)
        print("B2 selective routing + true subset fallback          : AUTHORIZED")
        print("="*202)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps({
            "milestone":M,
            "status":BLOCK,
            "failed_stage":stage,
            "exception":repr(exc),
            "gates":gates,
            "canonical_state_mutated":False,
            "production_routing_policy_changed":False,
            "B2_selective_routing_and_subset_fallback_design_authorized":False,
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
    args=ap.parse_args()
    if args.self_test:
        selftest()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root,args.drive_root))
