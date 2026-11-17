#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
from typing import Any
import numpy as np

M="POSTV16-AV4-PIVOT-GPU-HYB-G4-A7"
PASS="POSTV16AV4PIVOTGPUHYBG4A7_CONTROLLED_INTEGRATED_TRAJECTORY_REUSE_REFRESH_RESUME_PASS"
BLOCK="POSTV16AV4PIVOTGPUHYBG4A7_TECHNICAL_CONSERVATION_OR_CONTROLLER_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="5f92dfcca80e27912767cde303ee71b2f1c666c3"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

A6_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_A6_R2_Exact_Refresh_Contract_Repair.py"
A6_BLOB="c5daf18eda03491d01233eb7539d4335c5e1417c"
CTRL_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_Integrated_Runtime_Controller_R2.py"
CTRL_BLOB="2d1c4fd3b792c9c19bef268b74956574bcaaf540"
A5_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_A5_Short_Mixed_Recurrent_Rollout.py"
A5_BLOB="e366446f5c2e1e12b1ea74d9c63f079af36d8b15"
A1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_A1_R1_ReadOnly_Hybrid_ComponentMass_Bridge_TOF_Identity_Repair.py"
A1_BLOB="6b0bff953b11b393affc429825622fe4afdc5942"
B1_RUNNER="PAD_Stream_POSTV16_AV1_B1_R1_C26_to_E37A_Component_Mass_Representation_Equivalence_Audit.py"
B1_BLOB="8d9561d7c85805b82dedc26073c4633f90eeeab6"
E11_RUNNER="PAD_Stream_V16E11_R2_Packed_SG5_Serialization_Repair_and_Controlled_Hybrid_Streamline_Pilot.py"
E11_BLOB="bf89c14a3cb177fb483e233a17b72e824d31119b"
G2_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_R1_Rank1_Day75_80_ExactFlow_and_Hybrid_Endpoint_Diagnostic.py"
G2_BLOB="04c3940a7c736b1d210376113e48bab6111fc173"
R3R5_RUNNER="PAD_Stream_V16E41R3R5_Multi_Refresh_Cadence_Sensitivity_Runtime_Refresh_Policy_Calibration.py"
R3R5_BLOB="15aae3224ba4337cad72f9b4aa9166d602791349"
R3R4_RUNNER="PAD_Stream_V16E41R3R4R1_Refreshed_Flow_CFL_Alignment_Repair.py"
R3R4_BLOB="5f8433437ce111533338ceada922f51abb2edefe"

DAY_TO_S=86400.0
FT_TO_M=0.3048
FLOW_EPOCH_ORIGIN_DAY=75.0
MAX_EPOCH_DAYS=4.9417335239115445
REFRESH_DAY=FLOW_EPOCH_ORIGIN_DAY+MAX_EPOCH_DAYS
NSTREAM_EXPECTED=1078

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_A7"
OUT_REL=BASE/(OUT_TOKEN+"_Controlled_Integrated_Trajectory")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
STEPS=f"{OUT_TOKEN}_Accepted_Transitions.csv"
REFRESH=f"{OUT_TOKEN}_Flow_Refresh.csv"
ROUTES=f"{OUT_TOKEN}_Route_Audit.csv"
SNAPS=f"{OUT_TOKEN}_Key_Snapshots.npz"
GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"
FINAL_MIXED=f"{OUT_TOKEN}_Final_Mixed_State.npz"
FINAL_EXACT=f"{OUT_TOKEN}_Final_Exact_Benchmark_State.npz"

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

def js(p:Path):return json.loads(p.read_text(encoding="utf-8"))

def load_npz(p:Path):
    with np.load(p,allow_pickle=False) as z:return {k:np.asarray(z[k]).copy() for k in z.files}

def scalar(x:Any)->float:return float(np.asarray(x).reshape(()))
def int_scalar(x:Any)->int:return int(np.asarray(x).reshape(()))

def write_csv(p:Path,rows:list[dict[str,Any]]):
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields:fields.append(k)
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows)

def rel_l2(a,b):
    a=np.asarray(a,float);b=np.asarray(b,float)
    return float(np.linalg.norm((a-b).ravel())/max(float(np.linalg.norm(b.ravel())),1e-30))

def deterministic_npz_bytes(arrays:dict[str,Any])->bytes:
    import io
    bio=io.BytesIO()
    np.savez_compressed(bio,**{k:np.asarray(v) for k,v in arrays.items()})
    return bio.getvalue()

def selftest():
    assert abs(REFRESH_DAY-79.94173352391154)<=1e-12
    assert MAX_EPOCH_DAYS<5.0
    print("POSTV16 GPU-HYB-G4-A7 structural self-test: PASS")

def main(root:Path,drive:Path)->int:
    root=root.resolve();drive=drive.resolve();out=drive/OUT_REL;blocked=drive/BLOCK_REL
    gates=[];stage="preflight";a5_mixed_sha_before=None;day75_sha_before=None
    def gate(n,c,d=None):
        ok=bool(c);gates.append({"stage":stage,"gate":n,"pass":ok,"detail":"" if d is None else repr(d)})
        print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"),flush=True)
        if not ok: raise GateError(n)
    try:
        print("="*198)
        print("G4-A7 — FIRST CONTROLLED INTEGRATED PAD-STREAM TRAJECTORY")
        print("FLOW REUSE -> EXACT 4.9417335239115445-DAY BOUNDARY LANDING -> SAME-TIME FULL FLOW REFRESH -> RESUMED MIXED TRANSPORT.")
        print("MIXED HYBRID/EXACT-FALLBACK BRANCH AND FULL-EXACT TRANSPORT BENCHMARK RUN SIDE BY SIDE.")
        print("="*198)

        stage="repository"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_G4_A6_R2",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")
        a6=mod(root,A6_RUNNER,A6_BLOB,"g4a7_a6")
        ctrl=mod(root,CTRL_RUNNER,CTRL_BLOB,"g4a7_ctrl")
        a5=mod(root,A5_RUNNER,A5_BLOB,"g4a7_a5")
        a1=mod(root,A1_RUNNER,A1_BLOB,"g4a7_a1")
        b1=mod(root,B1_RUNNER,B1_BLOB,"g4a7_b1")
        e11=mod(root,E11_RUNNER,E11_BLOB,"g4a7_e11")
        g2=mod(root,G2_RUNNER,G2_BLOB,"g4a7_g2")
        r3r5=mod(root,R3R5_RUNNER,R3R5_BLOB,"g4a7_r3r5")
        r3r4=mod(root,R3R4_RUNNER,R3R4_BLOB,"g4a7_r3r4")

        stage="A6_controller_authority"
        a6s=js(drive/a6.OUT_REL/a6.SUMMARY)
        gate("A6_status_exact",a6s.get("status")==a6.PASS,a6s.get("status"))
        gate("A6_A7_authorized",a6s.get("G4_A7_controlled_integrated_trajectory_authorized") is True)
        gate("A6_exact_threshold",abs(float(a6s["production_max_flow_epoch_age_days"])-MAX_EPOCH_DAYS)<=1e-15,
             a6s["production_max_flow_epoch_age_days"])
        gate("controller_threshold_exact",abs(float(ctrl.PRODUCTION_MAX_FLOW_EPOCH_DAYS)-MAX_EPOCH_DAYS)<=1e-15,
             ctrl.PRODUCTION_MAX_FLOW_EPOCH_DAYS)
        gate("learned_pressure_checkpoint_firewalled",
             ctrl.LEARNED_PRESSURE_CHECKPOINT_POLICY=="RESEARCH_REFERENCE_ONLY_NOT_PRODUCTION_AUTHORIZED")
        gate("temporal_pressure_seed_exact_correction_policy",
             ctrl.PRESSURE_SEED_PRODUCTION_POLICY=="TEMPORAL_SEED_EXACT_FV_CORRECTION")

        stage="A5_start_authority"
        a5s=js(drive/a5.OUT_REL/a5.SUMMARY)
        gate("A5_status_exact",a5s.get("status")==a5.PASS,a5s.get("status"))
        mixed_start_path=drive/a5.OUT_REL/a5s["final_mixed_state_file"]
        exact_start_path=drive/a5.OUT_REL/a5s["final_exact_benchmark_state_file"]
        gate("A5_mixed_final_SHA",sha(mixed_start_path)==a5s["final_mixed_state_sha256"],sha(mixed_start_path))
        gate("A5_exact_final_SHA",sha(exact_start_path)==a5s["final_exact_benchmark_state_sha256"],sha(exact_start_path))
        a5_mixed_sha_before=sha(mixed_start_path)
        mixed_current=load_npz(mixed_start_path);exact_current=load_npz(exact_start_path)
        start_day=scalar(mixed_current["physical_time_days"])
        gate("start_day_matches_A5",abs(start_day-float(a5s["final_day"]))<=1e-12,(start_day,a5s["final_day"]))
        gate("start_before_refresh_boundary",start_day<REFRESH_DAY,(start_day,REFRESH_DAY))
        gate("start_dispatch_reuse",
             ctrl.decide_runtime_action(start_day,FLOW_EPOCH_ORIGIN_DAY).action=="REUSE_FLOW_NETWORK_FOR_MIXED_TRANSPORT")

        stage="physics_authority"
        roles={}
        for role in ["R3R2R1","E36","E37A","R2_PHYSICS","SG2","SG3","SG4","SG5","SG6","SG7A","SG7D"]:
            fn,bl=r3r4.SOURCE_BLOBS[role]
            roles[role]=g2.load_module_blob(root/fn,bl,f"g4a7_{role.lower()}",root)
        r3r2r1=roles["R3R2R1"];e36=roles["E36"];e37a=roles["E37A"];physics=roles["R2_PHYSICS"]
        sg2=roles["SG2"];sg3=roles["SG3"];sg4=roles["SG4"];sg5=roles["SG5"];sg6=roles["SG6"]
        sg7a=roles["SG7A"];sg7d=roles["SG7D"]

        pfn,pblob=r3r4.SOURCE_BLOBS["PERM"];perm_path=root/pfn
        gate("permeability_blob_exact",blob(root,perm_path)==pblob,blob(root,perm_path))
        permeability_md=np.loadtxt(perm_path,skiprows=1,dtype=np.float64).reshape((15,50,50),order="C")
        cell_pv=0.20*(20.0*FT_TO_M)*(20.0*FT_TO_M)*(4.0*FT_TO_M)

        # Recreate the authoritative Day75 flow epoch used by A5.
        g2s=js(drive/g2.OUT_REL/g2.SUMMARY)
        day75_path=drive/g2.OUT_REL/g2.DAY75_STATE
        day75_sha_before=sha(day75_path)
        gate("Day75_state_SHA_exact",day75_sha_before==g2s["Day75_exact_state_sha256"],day75_sha_before)
        day75=load_npz(day75_path)
        r3r5_g2=g2.load_module_blob(root/g2.R3R5_RUNNER,g2.R3R5_BLOB,"g4a7_g2_r3r5",root)
        ref75,epoch75,db75=g2.same_time_endpoint(
            day75,r3r5=r3r5_g2,r3r4r1=r3r4,physics=physics,r3r2r1=r3r2r1,e36=e36,e37a=e37a,
            sg2=sg2,sg3=sg3,sg4=sg4,sg5=sg5,sg6=sg6,sg7a=sg7a,sg7d=sg7d,
            permeability_md=permeability_md,cell_pore_volume_m3=cell_pv)
        gate("Day75_epoch_stream_count",int(epoch75["nstream"])==NSTREAM_EXPECTED,epoch75["nstream"])

        def rebuild_db(epoch:dict[str,Any]):
            vx,vy,vz=sg5.construct_face_pore_velocities(epoch["qx"],epoch["qy"],epoch["qz"])
            _faces,seeds=sg5.build_seeds(epoch["qx"],epoch["qy"],epoch["qz"])
            streamlines=sg5.trace_streamlines(seeds,vx,vy,vz)
            converted=r3r4.convert_sg5_to_sg6_streamlines(streamlines)
            db=sg6.build_transport_database(converted)
            if int(np.asarray(db["xyz_m"]).shape[0])!=int(epoch["nstream"]):
                raise GateError("refreshed_db_stream_count_mismatch")
            if np.asarray(db["xi"]).shape[0]!=int(epoch["nfaces"]):
                raise GateError("refreshed_db_face_count_mismatch")
            w=np.asarray(db["weights_m3_s"],float)*DAY_TO_S
            if np.max(np.abs(w-np.asarray(epoch["weights_m3_day"],float)))>1e-8:
                raise GateError("refreshed_db_weight_mismatch")
            if np.max(np.abs(np.asarray(db["xi"],float)-np.asarray(epoch["xi_faces"],float)))>1e-14:
                raise GateError("refreshed_db_xi_mismatch")
            return db

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
        adapter=e11.import_exact(root/e11.E9_ADAPTER[0],e11.E9_ADAPTER[1],"g4a7_adapter")
        teacher=e11.import_exact(root/e11.R2_ADAPTER[0],e11.R2_ADAPTER[1],"g4a7_teacher")
        e9r1=e11.import_exact(root/e11.E9R1_RUNNER[0],e11.E9R1_RUNNER[1],"g4a7_e9r1")
        shock=teacher.welge_shock(adapter.teacher_params(params),scan_nodes=4097)
        speed=float(shock["characteristic_speed"]);swstar=float(shock["Sw_star"])
        tf=e9r1.prepare_tf(e5)
        gate("TensorFlow_2_20_exact",tf.__version__=="2.20.0",tf.__version__)
        gate("GPU_visible",len(tf.config.list_physical_devices("GPU"))>=1,[str(x) for x in tf.config.list_physical_devices("GPU")])
        model=e9r1.build_inference_model(tf,10,"G4A7_Hybrid10")
        gate("Hybrid10_parameter_count_exact",model.count_params()==52545,model.count_params())
        model.load_weights(str(drive/e11.E6A_REL/e11.E6A_CHECKPOINT[0]))

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
            result=(profiles,clocks,reject)
            profile_cache[key]=result
            return result

        def mixed_step(current,epoch,db,dt,epoch_tag,transition_index):
            parent_time=scalar(current["physical_time_days"]);child_time=parent_time+dt
            parent_sat=np.asarray(current["transport_saturation"],float)
            pressure=np.asarray(epoch["pressure_psi"],float)
            p_ref=scalar(current["co2_density_reference_pressure_pa"])
            old_sat,old_mass,sample=e37a.sample_grid_inventory_to_control_volumes(
                physics,parent_sat,pressure,p_ref,epoch["geometry"],epoch["nstream"],epoch["ncv"])
            sample_tol=max(1e-6,1e-10*max(abs(float(np.sum(old_mass))),1.0))
            if abs(float(sample))>sample_tol:raise GateError(f"mixed_sample_closure:{transition_index}:{sample}")

            exact_fallback=e37a.advance_component_mass_control_volumes(
                physics,sg7a,old_sat,old_mass,epoch["geometry"]["cv_pressure_mass_coeff"],
                epoch["face_pressure_psi"],p_ref,epoch["weights_m3_day"],epoch["xi_faces"],dt)
            child_mass=np.asarray(exact_fallback["new_mass"],float).copy()
            child_cv_sat=np.asarray(exact_fallback["new_saturation"],float).copy()

            u=np.asarray(sg7a.u_dimensionless(epoch["xi_faces"]),float)
            q=np.asarray(epoch["weights_m3_day"],float)
            inlet_rate=q*float(e37a.CO2_RHO_REF_KG_M3)
            outlet_sat=old_sat[:,-1]
            outlet_ff=np.asarray(sg7a.fractional_flow(outlet_sat),float)
            outlet_rho=np.asarray(physics.gas_density_from_state(outlet_sat,epoch["face_pressure_psi"][:,-1],p_ref),float)
            outlet_rate=q*float(u[-1])*outlet_ff*outlet_rho
            target_i=np.sum(old_mass,axis=1)+inlet_rate*dt-outlet_rate*dt
            if np.max(np.abs(np.sum(child_mass,axis=1)-target_i))>1e-7:
                raise GateError(f"mixed_boundary_budget_vs_exact:{transition_index}")

            pp,_,pr=infer_profiles(parent_time,db,epoch_tag)
            cp,_,cr=infer_profiles(child_time,db,epoch_tag)
            eligible=np.asarray(sorted(set(pp).intersection(cp)),dtype=np.int64)
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
                        physics,np.full(int(epoch["ncv"]),float(physics.BACKGROUND_SATURATION+physics.MAX_INCREMENTAL_CO2_SATURATION)),coeff),float)
                    mm,lam,closure=a1.box_project(raw[j],float(target_i[sl]),cap)
                    if abs(float(closure))>1e-8:raise GateError(f"mixed_box_closure:{transition_index}:{sl}:{closure}")
                    ss=np.asarray(e37a.invert_cv_mass_to_saturation(physics,mm,coeff),float)
                    child_mass[sl]=mm;child_cv_sat[sl]=ss

            parent_cell_mass=r3r4.parent_cellwise_component_mass(physics,parent_sat,pressure,p_ref,cell_pv)
            preflight=r3r4.preflight_mapback_capacity(
                physics=physics,parent_saturation=parent_sat,parent_mass=parent_cell_mass,
                old_cv_saturation=old_sat,new_cv_saturation=child_cv_sat,geometry=epoch["geometry"],
                pressure_psi=pressure,p_ref_gas_pa=p_ref,cell_pore_volume_m3=cell_pv)
            if int(preflight["overcapacity_cell_count"])>0:
                raise GateError(f"mixed_capacity_preflight_rejection:{transition_index}:{preflight['overcapacity_cell_count']}")

            target_global=scalar(current["stored_co2_mass_current_kg"])+float(np.sum(inlet_rate)*dt)-float(np.sum(outlet_rate)*dt)
            mapping=e37a.map_control_volume_increment_to_grid(
                physics,parent_sat,old_sat,child_cv_sat,old_mass,child_mass,epoch["geometry"],
                pressure,p_ref,cell_pv,target_global)
            capillary=physics.conservative_capillary_mass_redistribution(
                transport_saturation=np.asarray(mapping["corrected_saturation"],float),
                permeability_md=permeability_md,pressure_psi=pressure,p_ref_pa=p_ref,
                cell_pore_volume_m3=cell_pv,dt_seconds=dt*DAY_TO_S)
            child_sat=np.asarray(capillary["corrected"],float)
            final_mass=float(capillary["final_mass_state_kg"])
            injected=float(np.sum(inlet_rate)*dt);produced=float(np.sum(outlet_rate)*dt)
            residual=final_mass-scalar(current["stored_co2_mass_current_kg"])-injected+produced
            tol=max(1e-6,1e-10*max(abs(target_global),1.0))
            if abs(residual)>tol:raise GateError(f"mixed_step_mass_closure:{transition_index}:{residual}")
            if abs(float(capillary["external_mass_change_kg"]))>tol:
                raise GateError(f"mixed_capillary_external:{transition_index}")

            prod_rows,cut=e37a.producer_rows_from_flux(
                epoch["labels"],epoch["weights_m3_day"],
                np.asarray(sg7a.fractional_flow(old_sat[:,-1]),float),outlet_rate,dt)
            if not np.isfinite(cut) or not 0<=cut<=1:raise GateError(f"mixed_gas_cut:{transition_index}:{cut}")
            child=e36.make_child_state(current,child_sat,pressure,p_ref,dt,produced,cut,final_mass,residual,False)
            child["flow_epoch_origin_day"]=np.asarray(float(parent_time-(0.0)),dtype=np.float64) # overwritten by caller
            child["hybrid_recurrent_bridge_active"]=np.asarray(True,dtype=bool)
            child["hybrid_recurrent_mode_ascii"]=np.frombuffer(b"HYBRID_INCREMENTAL_MIXED",dtype=np.uint8)
            child["hybrid_parent_anchored_incremental"]=np.asarray(True,dtype=bool)
            child["hybrid_incremental_route_count"]=np.asarray(int(eligible.size),dtype=np.int64)
            child["exact_fallback_route_count"]=np.asarray(int(epoch["nstream"]-eligible.size),dtype=np.int64)
            return child,{
                "Hybrid_incremental_route_count":int(eligible.size),
                "exact_fallback_route_count":int(epoch["nstream"]-eligible.size),
                "parent_screen_rejections":int(sum(pr.values())),
                "child_screen_rejections":int(sum(cr.values())),
                "step_mass_residual_kg":float(residual),
                "producer_gas_cut":float(cut),
                "stored_mass_kg":float(final_mass),
                "mapback_ledger_residual_kg":float(mapping["ledger_residual_kg"]),
                "minimum_capacity_margin_kg":float(preflight["minimum_capacity_margin_kg"]),
            }

        def exact_step(current,epoch,dt,transition_index):
            parent_sat=np.asarray(current["transport_saturation"],float)
            pressure=np.asarray(epoch["pressure_psi"],float);p_ref=scalar(current["co2_density_reference_pressure_pa"])
            old_sat,old_mass,sample=e37a.sample_grid_inventory_to_control_volumes(
                physics,parent_sat,pressure,p_ref,epoch["geometry"],epoch["nstream"],epoch["ncv"])
            if abs(float(sample))>max(1e-6,1e-10*max(abs(float(np.sum(old_mass))),1.0)):
                raise GateError(f"exact_sample_closure:{transition_index}:{sample}")
            tr=e37a.advance_component_mass_control_volumes(
                physics,sg7a,old_sat,old_mass,epoch["geometry"]["cv_pressure_mass_coeff"],
                epoch["face_pressure_psi"],p_ref,epoch["weights_m3_day"],epoch["xi_faces"],dt)
            parent_cell_mass=r3r4.parent_cellwise_component_mass(physics,parent_sat,pressure,p_ref,cell_pv)
            preflight=r3r4.preflight_mapback_capacity(
                physics=physics,parent_saturation=parent_sat,parent_mass=parent_cell_mass,
                old_cv_saturation=old_sat,new_cv_saturation=tr["new_saturation"],geometry=epoch["geometry"],
                pressure_psi=pressure,p_ref_gas_pa=p_ref,cell_pore_volume_m3=cell_pv)
            if int(preflight["overcapacity_cell_count"])>0:
                raise GateError(f"exact_capacity_preflight_rejection:{transition_index}:{preflight['overcapacity_cell_count']}")
            target=scalar(current["stored_co2_mass_current_kg"])+float(tr["injected_mass_kg"])-float(tr["produced_mass_kg"])
            mapping=e37a.map_control_volume_increment_to_grid(
                physics,parent_sat,old_sat,tr["new_saturation"],old_mass,tr["new_mass"],epoch["geometry"],
                pressure,p_ref,cell_pv,target)
            capillary=physics.conservative_capillary_mass_redistribution(
                transport_saturation=np.asarray(mapping["corrected_saturation"],float),
                permeability_md=permeability_md,pressure_psi=pressure,p_ref_pa=p_ref,
                cell_pore_volume_m3=cell_pv,dt_seconds=dt*DAY_TO_S)
            child_sat=np.asarray(capillary["corrected"],float);final_mass=float(capillary["final_mass_state_kg"])
            residual=final_mass-scalar(current["stored_co2_mass_current_kg"])-float(tr["injected_mass_kg"])+float(tr["produced_mass_kg"])
            tol=max(1e-6,1e-10*max(abs(target),1.0))
            if abs(residual)>tol:raise GateError(f"exact_step_mass_closure:{transition_index}:{residual}")
            prod_rows,cut=e37a.producer_rows_from_flux(
                epoch["labels"],epoch["weights_m3_day"],tr["outlet_fractional_flow"],tr["face_mass_flux_kg_day"][:,-1],dt)
            child=e36.make_child_state(current,child_sat,pressure,p_ref,dt,float(tr["produced_mass_kg"]),cut,final_mass,residual,False)
            return child,{
                "step_mass_residual_kg":float(residual),"producer_gas_cut":float(cut),
                "stored_mass_kg":float(final_mass),"minimum_capacity_margin_kg":float(preflight["minimum_capacity_margin_kg"])
            }

        step_rows=[];route_rows=[];refresh_rows=[]
        mixed_epoch=epoch75;exact_epoch=epoch75;mixed_db=db75;exact_db=db75
        mixed_epoch_origin=FLOW_EPOCH_ORIGIN_DAY;exact_epoch_origin=FLOW_EPOCH_ORIGIN_DAY
        transition=0
        snapshots={"start_mixed":np.asarray(mixed_current["transport_saturation"],float).copy(),
                   "start_exact":np.asarray(exact_current["transport_saturation"],float).copy()}
        boundary_pre_mixed=None;boundary_pre_exact=None;boundary_post_mixed=None;boundary_post_exact=None

        stage="pre_refresh_integrated_reuse"
        while scalar(mixed_current["physical_time_days"]) < REFRESH_DAY-1e-12:
            now=scalar(mixed_current["physical_time_days"])
            gate(f"reuse_dispatch_{transition}",
                 ctrl.decide_runtime_action(now,mixed_epoch_origin).action=="REUSE_FLOW_NETWORK_FOR_MIXED_TRANSPORT",
                 (now,mixed_epoch_origin))
            dt=min(float(mixed_epoch["cfl_dt_days"]),float(exact_epoch["cfl_dt_days"]),REFRESH_DAY-now)
            if not np.isfinite(dt) or dt<=0:raise GateError(f"nonpositive_pre_refresh_dt:{dt}")
            transition+=1
            mixed_child,mm=mixed_step(mixed_current,mixed_epoch,mixed_db,dt,"DAY75",transition)
            exact_child,em=exact_step(exact_current,exact_epoch,dt,transition)
            mixed_child["flow_epoch_origin_day"]=np.asarray(mixed_epoch_origin,dtype=np.float64)
            mixed_child["flow_epoch_age_days"]=np.asarray(scalar(mixed_child["physical_time_days"])-mixed_epoch_origin,dtype=np.float64)
            exact_child["flow_epoch_origin_day"]=np.asarray(exact_epoch_origin,dtype=np.float64)
            exact_child["flow_epoch_age_days"]=np.asarray(scalar(exact_child["physical_time_days"])-exact_epoch_origin,dtype=np.float64)
            mixed_current=mixed_child;exact_current=exact_child
            satrel=rel_l2(mixed_current["transport_saturation"],exact_current["transport_saturation"])
            step_rows.append({
                "transition":transition,"phase":"PRE_REFRESH_REUSE","parent_time_days":now,
                "child_time_days":scalar(mixed_current["physical_time_days"]),"dt_days":dt,
                "mixed_epoch_age_days":scalar(mixed_current["physical_time_days"])-mixed_epoch_origin,
                "Hybrid_incremental_route_count":mm["Hybrid_incremental_route_count"],
                "exact_fallback_route_count":mm["exact_fallback_route_count"],
                "mixed_step_mass_residual_kg":mm["step_mass_residual_kg"],
                "exact_step_mass_residual_kg":em["step_mass_residual_kg"],
                "mixed_vs_exact_saturation_relative_L2":satrel,
                "mixed_minus_exact_stored_mass_kg":mm["stored_mass_kg"]-em["stored_mass_kg"],
                "mixed_minus_exact_gas_cut":mm["producer_gas_cut"]-em["producer_gas_cut"],
            })
            route_rows.append({"transition":transition,"phase":"PRE_REFRESH_REUSE",
                               "Hybrid_count":mm["Hybrid_incremental_route_count"],
                               "exact_fallback_count":mm["exact_fallback_route_count"]})

        gate("exact_boundary_landing_mixed",abs(scalar(mixed_current["physical_time_days"])-REFRESH_DAY)<=1e-11,
             scalar(mixed_current["physical_time_days"]))
        gate("exact_boundary_landing_exact",abs(scalar(exact_current["physical_time_days"])-REFRESH_DAY)<=1e-11,
             scalar(exact_current["physical_time_days"]))
        gate("boundary_dispatch_refresh",
             ctrl.decide_runtime_action(REFRESH_DAY,mixed_epoch_origin).action=="FULL_FLOW_REFRESH")
        boundary_pre_mixed=np.asarray(mixed_current["transport_saturation"],float).copy()
        boundary_pre_exact=np.asarray(exact_current["transport_saturation"],float).copy()

        stage="same_time_full_flow_refresh"
        def do_refresh(current,branch):
            before_time=scalar(current["physical_time_days"]);before_step=int_scalar(current["accepted_step_index"])
            before_inj=scalar(current["cumulative_injected_co2_mass_kg"]);before_prod=scalar(current["cumulative_produced_co2_mass_kg"])
            before_stored=scalar(current["stored_co2_mass_current_kg"])
            refreshed,epoch,fp_rows=r3r5.build_flow_epoch(
                current=current,r3r4r1=r3r4,physics=physics,r3r2r1=r3r2r1,e36=e36,e37a=e37a,
                sg2=sg2,sg3=sg3,sg4=sg4,sg5=sg5,sg6=sg6,sg7a=sg7a,sg7d=sg7d,
                permeability_md=permeability_md,cell_pore_volume_m3=cell_pv)
            if scalar(refreshed["physical_time_days"])!=before_time:raise GateError(f"{branch}_refresh_advanced_time")
            if int_scalar(refreshed["accepted_step_index"])!=before_step:raise GateError(f"{branch}_refresh_advanced_step")
            if scalar(refreshed["cumulative_injected_co2_mass_kg"])!=before_inj:raise GateError(f"{branch}_refresh_injection")
            if scalar(refreshed["cumulative_produced_co2_mass_kg"])!=before_prod:raise GateError(f"{branch}_refresh_production")
            tol=max(1e-6,1e-10*max(abs(before_stored),1.0))
            if abs(scalar(refreshed["stored_co2_mass_current_kg"])-before_stored)>tol:raise GateError(f"{branch}_refresh_stored")
            refreshed["flow_epoch_origin_day"]=np.asarray(before_time,dtype=np.float64)
            refreshed["flow_epoch_age_days"]=np.asarray(0.0,dtype=np.float64)
            db=rebuild_db(epoch)
            return refreshed,epoch,db,{
                "branch":branch,"physical_time_days":before_time,"accepted_step_index":before_step,
                "fixed_point_iterations":int(epoch["fixed_point_iterations"]),
                "CFL_dt_days":float(epoch["cfl_dt_days"]),
                "streamline_count":int(epoch["nstream"]),
                "capture_fraction":float(epoch["capture_fraction"]),
                "flow_local_relative_residual":float(epoch["flow_local_residual"]),
                "flow_global_relative_residual":float(epoch["flow_global_residual"]),
                "pressure_rel_L2_vs_pre_refresh":float(epoch["refresh_pressure_rel_L2_vs_parent"]),
                "saturation_Linf_vs_pre_refresh":float(epoch["refresh_saturation_Linf_vs_parent"]),
                "refresh_global_mass_error_kg":float(epoch["refresh_global_mass_error_kg"]),
            }

        mixed_current,mixed_epoch,mixed_db,mr=do_refresh(mixed_current,"MIXED")
        exact_current,exact_epoch,exact_db,er=do_refresh(exact_current,"EXACT")
        mixed_epoch_origin=REFRESH_DAY;exact_epoch_origin=REFRESH_DAY
        refresh_rows.extend([mr,er])
        boundary_post_mixed=np.asarray(mixed_current["transport_saturation"],float).copy()
        boundary_post_exact=np.asarray(exact_current["transport_saturation"],float).copy()

        gate("mixed_refresh_same_time",abs(scalar(mixed_current["physical_time_days"])-REFRESH_DAY)<=1e-12)
        gate("exact_refresh_same_time",abs(scalar(exact_current["physical_time_days"])-REFRESH_DAY)<=1e-12)
        gate("mixed_refresh_flow_conservation",
             float(mixed_epoch["flow_local_residual"])<1e-8 and float(mixed_epoch["flow_global_residual"])<1e-8,
             (mixed_epoch["flow_local_residual"],mixed_epoch["flow_global_residual"]))
        gate("exact_refresh_flow_conservation",
             float(exact_epoch["flow_local_residual"])<1e-8 and float(exact_epoch["flow_global_residual"])<1e-8,
             (exact_epoch["flow_local_residual"],exact_epoch["flow_global_residual"]))

        p_rel=rel_l2(mixed_epoch["pressure_psi"],exact_epoch["pressure_psi"])
        qmix=np.concatenate([np.asarray(mixed_epoch["qx"]).ravel(),np.asarray(mixed_epoch["qy"]).ravel(),np.asarray(mixed_epoch["qz"]).ravel()])
        qex=np.concatenate([np.asarray(exact_epoch["qx"]).ravel(),np.asarray(exact_epoch["qy"]).ravel(),np.asarray(exact_epoch["qz"]).ravel()])
        q_rel=rel_l2(qmix,qex)
        refresh_sat_rel=rel_l2(mixed_current["transport_saturation"],exact_current["transport_saturation"])

        stage="post_refresh_resume"
        gate("post_refresh_dispatch_reuse",
             ctrl.decide_runtime_action(REFRESH_DAY,mixed_epoch_origin).action=="REUSE_FLOW_NETWORK_FOR_MIXED_TRANSPORT")
        dt_post=min(float(mixed_epoch["cfl_dt_days"]),float(exact_epoch["cfl_dt_days"]))
        transition+=1
        mixed_child,mm=mixed_step(mixed_current,mixed_epoch,mixed_db,dt_post,"POST_REFRESH_MIXED",transition)
        exact_child,em=exact_step(exact_current,exact_epoch,dt_post,transition)
        mixed_child["flow_epoch_origin_day"]=np.asarray(mixed_epoch_origin,dtype=np.float64)
        mixed_child["flow_epoch_age_days"]=np.asarray(scalar(mixed_child["physical_time_days"])-mixed_epoch_origin,dtype=np.float64)
        exact_child["flow_epoch_origin_day"]=np.asarray(exact_epoch_origin,dtype=np.float64)
        exact_child["flow_epoch_age_days"]=np.asarray(scalar(exact_child["physical_time_days"])-exact_epoch_origin,dtype=np.float64)
        mixed_current=mixed_child;exact_current=exact_child
        final_rel=rel_l2(mixed_current["transport_saturation"],exact_current["transport_saturation"])
        final_linf=float(np.max(np.abs(np.asarray(mixed_current["transport_saturation"])-np.asarray(exact_current["transport_saturation"]))))
        step_rows.append({
            "transition":transition,"phase":"POST_REFRESH_RESUME","parent_time_days":REFRESH_DAY,
            "child_time_days":scalar(mixed_current["physical_time_days"]),"dt_days":dt_post,
            "mixed_epoch_age_days":scalar(mixed_current["physical_time_days"])-mixed_epoch_origin,
            "Hybrid_incremental_route_count":mm["Hybrid_incremental_route_count"],
            "exact_fallback_route_count":mm["exact_fallback_route_count"],
            "mixed_step_mass_residual_kg":mm["step_mass_residual_kg"],
            "exact_step_mass_residual_kg":em["step_mass_residual_kg"],
            "mixed_vs_exact_saturation_relative_L2":final_rel,
            "mixed_minus_exact_stored_mass_kg":mm["stored_mass_kg"]-em["stored_mass_kg"],
            "mixed_minus_exact_gas_cut":mm["producer_gas_cut"]-em["producer_gas_cut"],
        })
        route_rows.append({"transition":transition,"phase":"POST_REFRESH_RESUME",
                           "Hybrid_count":mm["Hybrid_incremental_route_count"],
                           "exact_fallback_count":mm["exact_fallback_route_count"]})

        stage="trajectory_closure"
        mixed_cum=scalar(mixed_current["cumulative_mass_residual_kg"])
        exact_cum=scalar(exact_current["cumulative_mass_residual_kg"])
        mixed_tol=max(1e-6,1e-10*max(abs(scalar(mixed_current["stored_co2_mass_current_kg"])),1.0))
        exact_tol=max(1e-6,1e-10*max(abs(scalar(exact_current["stored_co2_mass_current_kg"])),1.0))
        gate("mixed_cumulative_mass_closure",abs(mixed_cum)<=mixed_tol,(mixed_cum,mixed_tol))
        gate("exact_cumulative_mass_closure",abs(exact_cum)<=exact_tol,(exact_cum,exact_tol))
        gate("A5_start_state_immutable",sha(mixed_start_path)==a5_mixed_sha_before,sha(mixed_start_path))
        gate("Day75_state_immutable",sha(day75_path)==day75_sha_before,sha(day75_path))

        final_stored_diff=scalar(mixed_current["stored_co2_mass_current_kg"])-scalar(exact_current["stored_co2_mass_current_kg"])
        final_cut_diff=scalar(mixed_current["current_producer_co2_gas_cut"])-scalar(exact_current["current_producer_co2_gas_cut"])
        pre_rows=[r for r in step_rows if r["phase"]=="PRE_REFRESH_REUSE"]
        hybrid_total=sum(int(r["Hybrid_incremental_route_count"]) for r in step_rows)
        fallback_total=sum(int(r["exact_fallback_route_count"]) for r in step_rows)

        stage="publication"
        gate("output_absent",not out.exists(),str(out));out.mkdir(parents=True)
        mb=deterministic_npz_bytes(mixed_current);eb=deterministic_npz_bytes(exact_current)
        (out/FINAL_MIXED).write_bytes(mb);(out/FINAL_EXACT).write_bytes(eb)
        np.savez_compressed(out/SNAPS,
            start_day=np.asarray(start_day),
            refresh_day=np.asarray(REFRESH_DAY),
            final_day=np.asarray(scalar(mixed_current["physical_time_days"])),
            start_mixed=snapshots["start_mixed"],start_exact=snapshots["start_exact"],
            boundary_pre_refresh_mixed=boundary_pre_mixed,boundary_pre_refresh_exact=boundary_pre_exact,
            boundary_post_refresh_mixed=boundary_post_mixed,boundary_post_refresh_exact=boundary_post_exact,
            final_mixed=np.asarray(mixed_current["transport_saturation"],float),
            final_exact=np.asarray(exact_current["transport_saturation"],float))
        summary={
            "milestone":M,"status":PASS,
            "classification":"CONTROLLED_INTEGRATED_PAD_STREAM_TRAJECTORY_FLOW_REUSE_EXACT_BOUNDARY_REFRESH_AND_POST_REFRESH_HYBRID_RESUME_CERTIFIED_A8_TRAJECTORY_VALIDATION_AUTHORIZED",
            "starting_day":start_day,
            "exact_refresh_boundary_day":REFRESH_DAY,
            "production_max_flow_epoch_age_days":MAX_EPOCH_DAYS,
            "pre_refresh_reuse_transition_count":len(pre_rows),
            "same_time_full_flow_refresh_count":1,
            "post_refresh_resume_transition_count":1,
            "total_transport_transition_count":len(step_rows),
            "cumulative_Hybrid_route_uses":hybrid_total,
            "cumulative_exact_fallback_route_uses":fallback_total,
            "mixed_refresh_fixed_point_iterations":int(mixed_epoch["fixed_point_iterations"]),
            "exact_refresh_fixed_point_iterations":int(exact_epoch["fixed_point_iterations"]),
            "mixed_refresh_pressure_rel_L2_vs_pre_refresh":float(mixed_epoch["refresh_pressure_rel_L2_vs_parent"]),
            "mixed_refresh_saturation_Linf_vs_pre_refresh":float(mixed_epoch["refresh_saturation_Linf_vs_parent"]),
            "mixed_vs_exact_refreshed_pressure_relative_L2":p_rel,
            "mixed_vs_exact_refreshed_flux_relative_L2":q_rel,
            "mixed_vs_exact_same_time_post_refresh_saturation_relative_L2":refresh_sat_rel,
            "final_day":scalar(mixed_current["physical_time_days"]),
            "final_mixed_vs_exact_saturation_relative_L2":final_rel,
            "final_mixed_vs_exact_saturation_Linf":final_linf,
            "final_mixed_minus_exact_stored_mass_kg":final_stored_diff,
            "final_mixed_minus_exact_producer_gas_cut":final_cut_diff,
            "mixed_final_cumulative_mass_residual_kg":mixed_cum,
            "exact_final_cumulative_mass_residual_kg":exact_cum,
            "flow_reuse_branch_executed":True,
            "exact_boundary_landing_executed":True,
            "full_flow_refresh_branch_executed":True,
            "post_refresh_mixed_transport_resumed":True,
            "temporal_pressure_seed_exact_FV_refresh_path_used":True,
            "AV5_learned_pressure_checkpoint_used":False,
            "new_scientific_accuracy_threshold_defined":False,
            "production_canonical_chain_replaced":False,
            "G4_A8_integrated_trajectory_validation_authorized":True,
            "integrated_GPU_runtime_production_authorized":False,
            "P4_authorized":False,
            "final_mixed_state_file":FINAL_MIXED,
            "final_mixed_state_sha256":hashlib.sha256(mb).hexdigest(),
            "final_exact_benchmark_state_file":FINAL_EXACT,
            "final_exact_benchmark_state_sha256":hashlib.sha256(eb).hexdigest(),
        }
        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        write_csv(out/STEPS,step_rows);write_csv(out/REFRESH,refresh_rows);write_csv(out/ROUTES,route_rows);write_csv(out/GATES,gates)
        write_csv(out/MANIFEST,[{"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size}
                                for p in sorted(out.iterdir()) if p.is_file() and p.name!=MANIFEST])

        print("="*198);print(M,"PASS")
        print("Start / refresh / final day                   :",start_day,"/",REFRESH_DAY,"/",scalar(mixed_current["physical_time_days"]))
        print("Pre-refresh reuse transitions                 :",len(pre_rows))
        print("Full same-time refreshes                      : 1")
        print("Post-refresh resume transitions               : 1")
        print("Cumulative Hybrid / exact fallback uses       :",hybrid_total,"/",fallback_total)
        print("Mixed vs exact refreshed pressure relL2       :",p_rel)
        print("Mixed vs exact refreshed flux relL2           :",q_rel)
        print("Final mixed vs exact saturation relL2         :",final_rel)
        print("Mixed final cumulative mass residual kg       :",mixed_cum)
        print("G4-A8 integrated trajectory validation        : AUTHORIZED")
        print("="*198)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps({
            "milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),"gates":gates,
            "A5_start_state_sha256_before":a5_mixed_sha_before,"Day75_state_sha256_before":day75_sha_before,
            "production_canonical_chain_replaced":False,
            "G4_A8_integrated_trajectory_validation_authorized":False,
            "integrated_GPU_runtime_production_authorized":False,"P4_authorized":False,
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
