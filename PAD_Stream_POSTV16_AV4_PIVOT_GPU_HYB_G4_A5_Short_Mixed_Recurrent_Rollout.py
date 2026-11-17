#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
from typing import Any
import numpy as np

M="POSTV16-AV4-PIVOT-GPU-HYB-G4-A5"
PASS="POSTV16AV4PIVOTGPUHYBG4A5_SHORT_MIXED_RECURRENT_ROLLOUT_PASS"
BLOCK="POSTV16AV4PIVOTGPUHYBG4A5_TECHNICAL_OR_RECURRENT_ROLLOUT_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="6e17d52b2ecee8def258b2826b2cab2ed284a24b"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

A4_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_A4_First_Controlled_Recurrent_Hybrid_Child.py"
A4_BLOB="7067cc6df1c4fe94a27043485b1fc0f5f041213a"
G2_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_R1_Rank1_Day75_80_ExactFlow_and_Hybrid_Endpoint_Diagnostic.py"
G2_BLOB="04c3940a7c736b1d210376113e48bab6111fc173"
R3R4_RUNNER="PAD_Stream_V16E41R3R4R1_Refreshed_Flow_CFL_Alignment_Repair.py"
R3R4_BLOB="5f8433437ce111533338ceada922f51abb2edefe"
A1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_A1_R1_ReadOnly_Hybrid_ComponentMass_Bridge_TOF_Identity_Repair.py"
A1_BLOB="6b0bff953b11b393affc429825622fe4afdc5942"
B1_RUNNER="PAD_Stream_POSTV16_AV1_B1_R1_C26_to_E37A_Component_Mass_Representation_Equivalence_Audit.py"
B1_BLOB="8d9561d7c85805b82dedc26073c4633f90eeeab6"
E11_RUNNER="PAD_Stream_V16E11_R2_Packed_SG5_Serialization_Repair_and_Controlled_Hybrid_Streamline_Pilot.py"
E11_BLOB="bf89c14a3cb177fb483e233a17b72e824d31119b"

DAY_TO_S=86400.0
FT_TO_M=0.3048
FLOW_EPOCH_DAY=75.0
MAX_FLOW_EPOCH_DAYS=5.0
ROLLOUT_STEPS=3
NSTREAM=1078
NFACES=201
NCV=200

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_A5"
OUT_REL=BASE/(OUT_TOKEN+"_Short_Mixed_Recurrent_Rollout")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
STEPS=f"{OUT_TOKEN}_Step_Audit.csv"
ROUTES=f"{OUT_TOKEN}_Route_Audit.csv"
PRODUCERS=f"{OUT_TOKEN}_Producer_Audit.csv"
SNAPSHOTS=f"{OUT_TOKEN}_Rollout_Snapshots.npz"
GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"

class GateError(RuntimeError): pass

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""):h.update(c)
    return h.hexdigest()

def gt(root:Path,*a:str)->str:
    return subprocess.check_output(["git","-C",str(root),*a],text=True).strip()

def blob(root:Path,p:Path)->str:
    return subprocess.check_output(["git","-C",str(root),"hash-object",str(p)],text=True).strip()

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

def write_csv(p:Path,rows:list[dict[str,Any]]):
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields:fields.append(k)
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows)

def read_manifest(p:Path)->dict[str,str]:
    with p.open(newline="",encoding="utf-8") as f:return {r["file"]:r["sha256"] for r in csv.DictReader(f)}

def rel_l2(a,b):
    a=np.asarray(a,float);b=np.asarray(b,float)
    return float(np.linalg.norm((a-b).ravel())/max(float(np.linalg.norm(b.ravel())),1e-30))

def selftest():
    t=75.0+4*0.045
    assert t<80.0 and ROLLOUT_STEPS==3
    print("POSTV16 GPU-HYB-G4-A5 structural self-test: PASS")

def main(root:Path,drive:Path)->int:
    root=root.resolve();drive=drive.resolve();out=drive/OUT_REL;blocked=drive/BLOCK_REL
    gates=[];stage="preflight";a4_child_sha_before=None;day75_sha_before=None
    def gate(n,c,d=None):
        ok=bool(c);gates.append({"stage":stage,"gate":n,"pass":ok,"detail":"" if d is None else repr(d)})
        print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"),flush=True)
        if not ok:raise GateError(n)
    try:
        print("="*190)
        print("G4-A5 — SHORT MIXED RECURRENT ROLLOUT")
        print("THREE ADDITIONAL MIXED TRANSPORT STEPS FROM THE CERTIFIED G4-A4 CHILD.")
        print("DAY75 FLOW EPOCH REMAINS FROZEN; FULL-EXACT THREE-STEP BRANCH RUNS BESIDE IT AS BENCHMARK.")
        print("NO PRESSURE REFRESH. NO CADENCE STUDY. NO PRODUCTION CANONICAL REPLACEMENT.")
        print("="*190)

        stage="repository"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_G4_A4",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")
        a4=mod(root,A4_RUNNER,A4_BLOB,"g4a5_a4")
        g2=mod(root,G2_RUNNER,G2_BLOB,"g4a5_g2")
        r3r4=mod(root,R3R4_RUNNER,R3R4_BLOB,"g4a5_r3r4")
        a1=mod(root,A1_RUNNER,A1_BLOB,"g4a5_a1")
        b1=mod(root,B1_RUNNER,B1_BLOB,"g4a5_b1")
        e11=mod(root,E11_RUNNER,E11_BLOB,"g4a5_e11")

        stage="A4_authority"
        a4s=js(drive/a4.OUT_REL/a4.SUMMARY)
        gate("A4_status_exact",a4s.get("status")==a4.PASS,a4s.get("status"))
        gate("A4_transition_executed",a4s.get("controlled_Hybrid_recurrent_state_transition_executed") is True)
        gate("A4_A5_authorized",a4s.get("G4_A5_short_mixed_recurrent_rollout_authorized") is True)
        gate("A4_parent_immutable",a4s.get("parent_state_immutable") is True)
        a4_manifest=read_manifest(drive/a4.OUT_REL/a4.MANIFEST)
        mixed_start_path=drive/a4.OUT_REL/a4.CHILD
        exact_start_path=drive/a4.OUT_REL/a4.EXACT_CHILD
        gate("A4_mixed_child_SHA_summary",sha(mixed_start_path)==a4s["controlled_child_state_sha256"],sha(mixed_start_path))
        gate("A4_mixed_child_SHA_manifest",sha(mixed_start_path)==a4_manifest[a4.CHILD],sha(mixed_start_path))
        gate("A4_exact_child_SHA_summary",sha(exact_start_path)==a4s["exact_benchmark_child_state_sha256"],sha(exact_start_path))
        a4_child_sha_before=sha(mixed_start_path)
        mixed_current=load_npz(mixed_start_path);exact_current=load_npz(exact_start_path)
        gate("A4_mixed_exact_same_start_time",
             abs(scalar(mixed_current["physical_time_days"])-scalar(exact_current["physical_time_days"]))<=1e-12,
             (scalar(mixed_current["physical_time_days"]),scalar(exact_current["physical_time_days"])))

        stage="Day75_flow_epoch_authority"
        g2s=js(drive/g2.OUT_REL/g2.SUMMARY)
        gate("G2_status_exact",g2s.get("status")==g2.PASS,g2s.get("status"))
        day75_path=drive/g2.OUT_REL/g2.DAY75_STATE
        day75_sha_before=sha(day75_path)
        gate("Day75_state_SHA_exact",day75_sha_before==g2s["Day75_exact_state_sha256"],day75_sha_before)
        day75=load_npz(day75_path)

        r3r5=g2.load_module_blob(root/g2.R3R5_RUNNER,g2.R3R5_BLOB,"g4a5_r3r5",root)
        roles={}
        for role in ["R3R2R1","E36","E37A","R2_PHYSICS","SG2","SG3","SG4","SG5","SG6","SG7A","SG7D"]:
            fn,bl=r3r4.SOURCE_BLOBS[role]
            roles[role]=g2.load_module_blob(root/fn,bl,f"g4a5_{role.lower()}",root)
        r3r2r1=roles["R3R2R1"];e36=roles["E36"];e37a=roles["E37A"];physics=roles["R2_PHYSICS"]
        sg2=roles["SG2"];sg3=roles["SG3"];sg4=roles["SG4"];sg5=roles["SG5"];sg6=roles["SG6"]
        sg7a=roles["SG7A"];sg7d=roles["SG7D"]

        pfn,pblob=r3r4.SOURCE_BLOBS["PERM"];perm_path=root/pfn
        gate("permeability_blob_exact",blob(root,perm_path)==pblob,blob(root,perm_path))
        permeability_md=np.loadtxt(perm_path,skiprows=1,dtype=np.float64).reshape((15,50,50),order="C")
        cell_pv=0.20*(20.0*FT_TO_M)*(20.0*FT_TO_M)*(4.0*FT_TO_M)

        ref75,epoch75,db75=g2.same_time_endpoint(
            day75,r3r5=r3r5,r3r4r1=r3r4,physics=physics,r3r2r1=r3r2r1,e36=e36,e37a=e37a,
            sg2=sg2,sg3=sg3,sg4=sg4,sg5=sg5,sg6=sg6,sg7a=sg7a,sg7d=sg7d,
            permeability_md=permeability_md,cell_pore_volume_m3=cell_pv)
        pressure=np.asarray(epoch75["pressure_psi"],dtype=np.float64)
        p_ref=scalar(ref75["co2_density_reference_pressure_pa"])
        face_pressure=e37a.build_face_pressure(e36,sg7d,db75["xyz_m"],pressure)
        q=np.asarray(db75["weights_m3_s"],dtype=np.float64)*DAY_TO_S
        xi=np.asarray(db75["xi"],dtype=np.float64)
        tau=np.asarray(db75["tau_s"],dtype=np.float64)
        tau_end=np.asarray(db75["tau_end_s"],dtype=np.float64)
        terminal_days=tau_end/DAY_TO_S
        dt=float(r3r4.transport_cfl_dt_days(sg7a,xi,tau_end))
        gate("fixed_dt_matches_A4",abs(dt-float(a4s["accepted_dt_days"]))<=1e-15,(dt,a4s["accepted_dt_days"]))
        gate("final_flow_epoch_age_within_5day_reference",
             scalar(mixed_current["physical_time_days"])+ROLLOUT_STEPS*dt-FLOW_EPOCH_DAY<MAX_FLOW_EPOCH_DAYS,
             scalar(mixed_current["physical_time_days"])+ROLLOUT_STEPS*dt-FLOW_EPOCH_DAY)

        stage="Hybrid_inference_authority"
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
        adapter=e11.import_exact(root/e11.E9_ADAPTER[0],e11.E9_ADAPTER[1],"g4a5_adapter")
        teacher=e11.import_exact(root/e11.R2_ADAPTER[0],e11.R2_ADAPTER[1],"g4a5_teacher")
        e9r1=e11.import_exact(root/e11.E9R1_RUNNER[0],e11.E9R1_RUNNER[1],"g4a5_e9r1")
        shock=teacher.welge_shock(adapter.teacher_params(params),scan_nodes=4097)
        speed=float(shock["characteristic_speed"]);swstar=float(shock["Sw_star"])
        tf=e9r1.prepare_tf(e5)
        gate("TensorFlow_2_20_exact",tf.__version__=="2.20.0",tf.__version__)
        gate("GPU_visible",len(tf.config.list_physical_devices("GPU"))>=1,[str(x) for x in tf.config.list_physical_devices("GPU")])
        model=e9r1.build_inference_model(tf,10,"G4A5_Hybrid10")
        gate("Hybrid10_parameter_count_exact",model.count_params()==52545,model.count_params())
        model.load_weights(str(drive/e11.E6A_REL/e11.E6A_CHECKPOINT[0]))

        def infer_profiles(day:float):
            xstar=(float(day)/terminal_days)*speed
            clocks=np.asarray([e11.classify_clock(float(x)) for x in xstar],dtype="U32")
            learned=clocks=="LEARNED_WINDOW"
            idx=np.flatnonzero(learned)
            if idx.size==0:
                return {},clocks,{}
            cond=[];states=[]
            for i in idx:
                st=adapter.physical_time_state(elapsed_time=day,tau_end=float(terminal_days[i]),
                                               characteristic_speed=speed,Sw_star=swstar)
                states.append(st);cond.append(adapter.conditioning_vector("HYBRID10",params,st))
            pred=e9r1.infer(tf,model,xi.astype(np.float32),np.asarray(cond,dtype=np.float32),batch=256)
            profiles={};reject={}
            for local,i in enumerate(idx):
                ok,sm=e11.screen_fan_prediction(
                    pred[local],params,states[local],xi,tau[i]/DAY_TO_S,teacher,adapter,screen)
                if ok:
                    profiles[int(i)]=adapter.project_fan_to_pollock_nodes(
                        tau_nodes=tau[i]/DAY_TO_S,state=states[local],fan_xi=xi,
                        fan_sw=pred[local],swc=float(params["swc"])).astype(np.float64)
                else:
                    for reason in sm["failures"]:reject[reason]=reject.get(reason,0)+1
            return profiles,clocks,reject

        step_rows=[];route_rows=[];producer_rows_all=[]
        mixed_sats=[np.asarray(mixed_current["transport_saturation"],dtype=np.float64).copy()]
        exact_sats=[np.asarray(exact_current["transport_saturation"],dtype=np.float64).copy()]
        times=[scalar(mixed_current["physical_time_days"])]
        cumulative_hybrid_routes=0
        cumulative_exact_routes=0

        stage="short_rollout"
        for local_step in range(1,ROLLOUT_STEPS+1):
            parent_time=scalar(mixed_current["physical_time_days"])
            exact_parent_time=scalar(exact_current["physical_time_days"])
            gate(f"step{local_step}_branch_times_match",abs(parent_time-exact_parent_time)<=1e-12,(parent_time,exact_parent_time))
            child_time=parent_time+dt
            gate(f"step{local_step}_flow_epoch_age_safe",child_time-FLOW_EPOCH_DAY<MAX_FLOW_EPOCH_DAYS,child_time-FLOW_EPOCH_DAY)

            parent_profiles,parent_clocks,parent_reject=infer_profiles(parent_time)
            child_profiles,child_clocks,child_reject=infer_profiles(child_time)
            eligible=sorted(set(parent_profiles).intersection(child_profiles))
            eligible=np.asarray(eligible,dtype=np.int64)

            # MIXED BRANCH parent state -> exact fallback + Hybrid incremental proposals.
            mixed_parent_sat=np.asarray(mixed_current["transport_saturation"],dtype=np.float64)
            mixed_old_sat,mixed_old_mass,mixed_sample=e37a.sample_grid_inventory_to_control_volumes(
                physics,mixed_parent_sat,pressure,p_ref,epoch75["geometry"],NSTREAM,NCV)
            sample_tol=max(1e-6,1e-10*max(abs(float(np.sum(mixed_old_mass))),1.0))
            gate(f"step{local_step}_mixed_parent_sampling_closure",abs(float(mixed_sample))<=sample_tol,mixed_sample)

            mixed_exact=e37a.advance_component_mass_control_volumes(
                physics,sg7a,mixed_old_sat,mixed_old_mass,epoch75["geometry"]["cv_pressure_mass_coeff"],
                face_pressure,p_ref,q,xi,dt)
            mixed_exact_mass=np.asarray(mixed_exact["new_mass"],dtype=np.float64)
            mixed_exact_sat=np.asarray(mixed_exact["new_saturation"],dtype=np.float64)

            # Production budget from parent + boundaries only.
            u=np.asarray(sg7a.u_dimensionless(xi),dtype=np.float64)
            inlet_rate=q*float(e37a.CO2_RHO_REF_KG_M3)
            outlet_sat=mixed_old_sat[:,-1]
            outlet_ff=np.asarray(sg7a.fractional_flow(outlet_sat),dtype=np.float64)
            outlet_rho=np.asarray(physics.gas_density_from_state(outlet_sat,face_pressure[:,-1],p_ref),dtype=np.float64)
            outlet_rate=q*float(u[-1])*outlet_ff*outlet_rho
            injected_i=inlet_rate*dt;produced_i=outlet_rate*dt
            target_i=np.sum(mixed_old_mass,axis=1)+injected_i-produced_i
            direct_budget_res=np.sum(mixed_exact_mass,axis=1)-target_i
            gate(f"step{local_step}_direct_budget_matches_exact_fallback",
                 float(np.max(np.abs(direct_budget_res)))<=1e-7,float(np.max(np.abs(direct_budget_res))))

            mixed_child_mass=mixed_exact_mass.copy()
            mixed_child_cv_sat=mixed_exact_sat.copy()

            if eligible.size:
                parent_prof=np.stack([parent_profiles[int(i)] for i in eligible],axis=0)
                child_prof=np.stack([child_profiles[int(i)] for i in eligible],axis=0)
                _,pmm,_=b1.project_201_to_200_component_mass(
                    physics,e37a,parent_prof,epoch75["geometry"]["cv_pressure_mass_coeff"],eligible)
                _,cmm,_=b1.project_201_to_200_component_mass(
                    physics,e37a,child_prof,epoch75["geometry"]["cv_pressure_mass_coeff"],eligible)
                delta=cmm-pmm
                raw=mixed_old_mass[eligible]+delta
                for j,sl in enumerate(eligible):
                    cap=np.asarray(e37a.cv_mass_from_saturation(
                        physics,
                        np.full(NCV,float(physics.BACKGROUND_SATURATION+physics.MAX_INCREMENTAL_CO2_SATURATION)),
                        np.asarray(epoch75["geometry"]["cv_pressure_mass_coeff"])[sl]),dtype=np.float64)
                    m,lam,closure=a1.box_project(raw[j],float(target_i[sl]),cap)
                    if abs(float(closure))>1e-8:raise GateError(f"step{local_step}_Hybrid_budget_closure:{sl}:{closure}")
                    ss=np.asarray(e37a.invert_cv_mass_to_saturation(
                        physics,m,np.asarray(epoch75["geometry"]["cv_pressure_mass_coeff"])[sl]),dtype=np.float64)
                    mixed_child_mass[sl]=m;mixed_child_cv_sat[sl]=ss

            mixed_global_target=scalar(mixed_current["stored_co2_mass_current_kg"])+float(np.sum(injected_i))-float(np.sum(produced_i))
            mixed_map=e37a.map_control_volume_increment_to_grid(
                physics,mixed_parent_sat,mixed_old_sat,mixed_child_cv_sat,mixed_old_mass,mixed_child_mass,
                epoch75["geometry"],pressure,p_ref,cell_pv,mixed_global_target)
            mixed_cap=physics.conservative_capillary_mass_redistribution(
                transport_saturation=np.asarray(mixed_map["corrected_saturation"],dtype=np.float64),
                permeability_md=permeability_md,pressure_psi=pressure,p_ref_pa=p_ref,
                cell_pore_volume_m3=cell_pv,dt_seconds=dt*DAY_TO_S)
            mixed_child_sat=np.asarray(mixed_cap["corrected"],dtype=np.float64)
            mixed_final=float(mixed_cap["final_mass_state_kg"])
            mixed_produced=float(np.sum(produced_i));mixed_injected=float(np.sum(injected_i))
            mixed_res=mixed_final-scalar(mixed_current["stored_co2_mass_current_kg"])-mixed_injected+mixed_produced
            closure_tol=max(1e-6,1e-10*max(abs(mixed_global_target),1.0))
            gate(f"step{local_step}_mixed_mapback_ledger",
                 abs(float(mixed_map["ledger_residual_kg"]))<=float(mixed_map["roundoff_mass_kg"]),
                 mixed_map["ledger_residual_kg"])
            gate(f"step{local_step}_mixed_capillary_external_zero",
                 abs(float(mixed_cap["external_mass_change_kg"]))<=closure_tol,mixed_cap["external_mass_change_kg"])
            gate(f"step{local_step}_mixed_step_mass_closure",abs(mixed_res)<=closure_tol,(mixed_res,closure_tol))

            mixed_prod_rows,mixed_cut=e37a.producer_rows_from_flux(
                epoch75["labels"],epoch75["weights_m3_day"],
                np.asarray(sg7a.fractional_flow(mixed_old_sat[:,-1]),dtype=np.float64),
                outlet_rate,dt)
            # producer_rows_from_flux expects outlet mass flux kg/day; outlet_rate already kg/day.
            gate(f"step{local_step}_mixed_gas_cut_valid",np.isfinite(mixed_cut) and 0.0<=mixed_cut<=1.0,mixed_cut)

            mixed_child=e36.make_child_state(
                mixed_current,mixed_child_sat,pressure,p_ref,dt,mixed_produced,mixed_cut,mixed_final,mixed_res,False)
            mixed_child["transport_face_count"]=np.asarray(NFACES,dtype=np.int64)
            mixed_child["transport_control_volume_count"]=np.asarray(NCV,dtype=np.int64)
            mixed_child["mass_conservative_flow_refresh_active"]=np.asarray(True,dtype=bool)
            mixed_child["runtime_refresh_policy_name_ascii"]=np.frombuffer(b"FIVE_DAY_CONSERVATIVE_INTEGRATION_REFERENCE",dtype=np.uint8)
            mixed_child["runtime_max_flow_epoch_days"]=np.asarray(MAX_FLOW_EPOCH_DAYS,dtype=np.float64)
            mixed_child["hybrid_recurrent_bridge_active"]=np.asarray(True,dtype=bool)
            mixed_child["hybrid_recurrent_mode_ascii"]=np.frombuffer(b"HYBRID_INCREMENTAL_MIXED",dtype=np.uint8)
            mixed_child["hybrid_parent_anchored_incremental"]=np.asarray(True,dtype=bool)
            mixed_child["flow_epoch_origin_day"]=np.asarray(FLOW_EPOCH_DAY,dtype=np.float64)
            mixed_child["flow_epoch_age_days"]=np.asarray(child_time-FLOW_EPOCH_DAY,dtype=np.float64)
            mixed_child["last_grid_mapback_ledger_residual_kg"]=np.asarray(mixed_map["ledger_residual_kg"],dtype=np.float64)
            mixed_child["last_capillary_external_mass_change_kg"]=np.asarray(mixed_cap["external_mass_change_kg"],dtype=np.float64)
            mixed_child["hybrid_incremental_route_count"]=np.asarray(int(eligible.size),dtype=np.int64)
            mixed_child["exact_fallback_route_count"]=np.asarray(int(NSTREAM-eligible.size),dtype=np.int64)
            mixed_child["controlled_hybrid_transition_index"]=np.asarray(1+local_step,dtype=np.int64)

            # FULL-EXACT BENCHMARK branch from its own parent.
            exact_parent_sat=np.asarray(exact_current["transport_saturation"],dtype=np.float64)
            exact_old_sat,exact_old_mass,exact_sample=e37a.sample_grid_inventory_to_control_volumes(
                physics,exact_parent_sat,pressure,p_ref,epoch75["geometry"],NSTREAM,NCV)
            exact_sample_tol=max(1e-6,1e-10*max(abs(float(np.sum(exact_old_mass))),1.0))
            gate(f"step{local_step}_exact_parent_sampling_closure",abs(float(exact_sample))<=exact_sample_tol,exact_sample)
            exact_tr=e37a.advance_component_mass_control_volumes(
                physics,sg7a,exact_old_sat,exact_old_mass,epoch75["geometry"]["cv_pressure_mass_coeff"],
                face_pressure,p_ref,q,xi,dt)
            exact_target=scalar(exact_current["stored_co2_mass_current_kg"])+float(exact_tr["injected_mass_kg"])-float(exact_tr["produced_mass_kg"])
            exact_map=e37a.map_control_volume_increment_to_grid(
                physics,exact_parent_sat,exact_old_sat,np.asarray(exact_tr["new_saturation"],dtype=np.float64),
                exact_old_mass,np.asarray(exact_tr["new_mass"],dtype=np.float64),epoch75["geometry"],
                pressure,p_ref,cell_pv,exact_target)
            exact_cap=physics.conservative_capillary_mass_redistribution(
                transport_saturation=np.asarray(exact_map["corrected_saturation"],dtype=np.float64),
                permeability_md=permeability_md,pressure_psi=pressure,p_ref_pa=p_ref,
                cell_pore_volume_m3=cell_pv,dt_seconds=dt*DAY_TO_S)
            exact_child_sat=np.asarray(exact_cap["corrected"],dtype=np.float64)
            exact_final=float(exact_cap["final_mass_state_kg"])
            exact_res=exact_final-scalar(exact_current["stored_co2_mass_current_kg"])-float(exact_tr["injected_mass_kg"])+float(exact_tr["produced_mass_kg"])
            exact_tol=max(1e-6,1e-10*max(abs(exact_target),1.0))
            gate(f"step{local_step}_exact_step_mass_closure",abs(exact_res)<=exact_tol,(exact_res,exact_tol))
            exact_prod_rows,exact_cut=e37a.producer_rows_from_flux(
                epoch75["labels"],epoch75["weights_m3_day"],
                exact_tr["outlet_fractional_flow"],exact_tr["face_mass_flux_kg_day"][:,-1],dt)
            gate(f"step{local_step}_exact_gas_cut_valid",np.isfinite(exact_cut) and 0.0<=exact_cut<=1.0,exact_cut)
            exact_child=e36.make_child_state(
                exact_current,exact_child_sat,pressure,p_ref,dt,float(exact_tr["produced_mass_kg"]),
                exact_cut,exact_final,exact_res,False)
            exact_child["flow_epoch_origin_day"]=np.asarray(FLOW_EPOCH_DAY,dtype=np.float64)
            exact_child["flow_epoch_age_days"]=np.asarray(child_time-FLOW_EPOCH_DAY,dtype=np.float64)

            sat_rel=rel_l2(mixed_child_sat,exact_child_sat)
            sat_linf=float(np.max(np.abs(mixed_child_sat-exact_child_sat)))
            stored_diff=mixed_final-exact_final
            gas_cut_diff=float(mixed_cut-exact_cut)

            step_rows.append({
                "rollout_transition":local_step,
                "parent_time_days":parent_time,
                "child_time_days":child_time,
                "dt_days":dt,
                "flow_epoch_age_days":child_time-FLOW_EPOCH_DAY,
                "Hybrid_incremental_route_count":int(eligible.size),
                "exact_fallback_route_count":int(NSTREAM-eligible.size),
                "Hybrid_route_fraction":float(eligible.size/NSTREAM),
                "mixed_injected_mass_kg":mixed_injected,
                "mixed_produced_mass_kg":mixed_produced,
                "mixed_stored_mass_kg":mixed_final,
                "mixed_step_mass_residual_kg":mixed_res,
                "mixed_cumulative_mass_residual_kg":scalar(mixed_child["cumulative_mass_residual_kg"]),
                "mixed_producer_gas_cut":float(mixed_cut),
                "exact_stored_mass_kg":exact_final,
                "exact_cumulative_mass_residual_kg":scalar(exact_child["cumulative_mass_residual_kg"]),
                "exact_producer_gas_cut":float(exact_cut),
                "mixed_vs_exact_saturation_relative_L2":sat_rel,
                "mixed_vs_exact_saturation_Linf":sat_linf,
                "mixed_minus_exact_stored_mass_kg":stored_diff,
                "mixed_minus_exact_gas_cut":gas_cut_diff,
                "parent_screen_rejection_count":int(sum(parent_reject.values())),
                "child_screen_rejection_count":int(sum(child_reject.values())),
            })
            route_rows += [
                {"rollout_transition":local_step,"route":"HYBRID10_PARENT_ANCHORED_INCREMENT","count":int(eligible.size)},
                {"rollout_transition":local_step,"route":"EXACT_E37A_FALLBACK","count":int(NSTREAM-eligible.size)},
            ]
            for row in mixed_prod_rows:
                rr=dict(row);rr["rollout_transition"]=local_step;rr["branch"]="MIXED";producer_rows_all.append(rr)
            for row in exact_prod_rows:
                rr=dict(row);rr["rollout_transition"]=local_step;rr["branch"]="EXACT";producer_rows_all.append(rr)

            cumulative_hybrid_routes+=int(eligible.size)
            cumulative_exact_routes+=int(NSTREAM-eligible.size)
            mixed_current=mixed_child;exact_current=exact_child
            mixed_sats.append(mixed_child_sat.copy());exact_sats.append(exact_child_sat.copy());times.append(child_time)

        stage="rollout_closure"
        final_time=scalar(mixed_current["physical_time_days"])
        final_exact_time=scalar(exact_current["physical_time_days"])
        gate("final_branch_times_match",abs(final_time-final_exact_time)<=1e-12,(final_time,final_exact_time))
        gate("final_flow_epoch_age_within_reference",final_time-FLOW_EPOCH_DAY<MAX_FLOW_EPOCH_DAYS,final_time-FLOW_EPOCH_DAY)
        mixed_final_res=scalar(mixed_current["cumulative_mass_residual_kg"])
        exact_final_res=scalar(exact_current["cumulative_mass_residual_kg"])
        mixed_tol=max(1e-6,1e-10*max(abs(scalar(mixed_current["stored_co2_mass_current_kg"])),1.0))
        exact_tol=max(1e-6,1e-10*max(abs(scalar(exact_current["stored_co2_mass_current_kg"])),1.0))
        gate("mixed_final_cumulative_mass_closure",abs(mixed_final_res)<=mixed_tol,(mixed_final_res,mixed_tol))
        gate("exact_final_cumulative_mass_closure",abs(exact_final_res)<=exact_tol,(exact_final_res,exact_tol))
        gate("A4_start_child_immutable",sha(mixed_start_path)==a4_child_sha_before,sha(mixed_start_path))
        gate("Day75_source_state_immutable",sha(day75_path)==day75_sha_before,sha(day75_path))

        final_sat_rel=rel_l2(np.asarray(mixed_current["transport_saturation"]),np.asarray(exact_current["transport_saturation"]))
        final_sat_linf=float(np.max(np.abs(np.asarray(mixed_current["transport_saturation"])-np.asarray(exact_current["transport_saturation"]))))
        final_stored_diff=scalar(mixed_current["stored_co2_mass_current_kg"])-scalar(exact_current["stored_co2_mass_current_kg"])
        final_cut_diff=scalar(mixed_current["current_producer_co2_gas_cut"])-scalar(exact_current["current_producer_co2_gas_cut"])

        stage="publication"
        gate("output_absent",not out.exists(),str(out));out.mkdir(parents=True)
        mixed_final_name=f"{OUT_TOKEN}_Final_Mixed_State.npz"
        exact_final_name=f"{OUT_TOKEN}_Final_Exact_Benchmark_State.npz"
        mixed_bytes=r3r5.deterministic_npz_bytes(mixed_current)
        exact_bytes=r3r5.deterministic_npz_bytes(exact_current)
        (out/mixed_final_name).write_bytes(mixed_bytes);(out/exact_final_name).write_bytes(exact_bytes)
        np.savez_compressed(out/SNAPSHOTS,
            physical_time_days=np.asarray(times,dtype=np.float64),
            mixed_transport_saturation=np.stack(mixed_sats,axis=0),
            exact_transport_saturation=np.stack(exact_sats,axis=0))
        summary={
            "milestone":M,"status":PASS,
            "classification":"THREE_STEP_MIXED_PARENT_ANCHORED_HYBRID_RECURRENT_ROLLOUT_CONSERVATIVE_AND_STABLE_G4_A6_INTEGRATED_GPU_RUNTIME_ASSEMBLY_AUTHORIZED",
            "starting_controlled_child_sha256":a4_child_sha_before,
            "additional_transitions_executed":ROLLOUT_STEPS,
            "starting_day":float(times[0]),
            "final_day":final_time,
            "final_flow_epoch_age_days":final_time-FLOW_EPOCH_DAY,
            "flow_refresh_executed_during_rollout":False,
            "five_day_reference_exceeded":False,
            "cumulative_Hybrid_route_uses":cumulative_hybrid_routes,
            "cumulative_exact_fallback_route_uses":cumulative_exact_routes,
            "mixed_final_cumulative_mass_residual_kg":mixed_final_res,
            "exact_final_cumulative_mass_residual_kg":exact_final_res,
            "final_mixed_vs_exact_saturation_relative_L2":final_sat_rel,
            "final_mixed_vs_exact_saturation_Linf":final_sat_linf,
            "final_mixed_minus_exact_stored_mass_kg":final_stored_diff,
            "final_mixed_minus_exact_producer_gas_cut":final_cut_diff,
            "A4_start_child_immutable":True,
            "Day75_source_state_immutable":True,
            "production_canonical_chain_replaced":False,
            "new_scientific_threshold_defined":False,
            "G4_A6_integrated_GPU_runtime_assembly_authorized":True,
            "integrated_GPU_runtime_authorized":False,
            "P4_authorized":False,
            "final_mixed_state_file":mixed_final_name,
            "final_mixed_state_sha256":hashlib.sha256(mixed_bytes).hexdigest(),
            "final_exact_benchmark_state_file":exact_final_name,
            "final_exact_benchmark_state_sha256":hashlib.sha256(exact_bytes).hexdigest(),
            "step_metrics":step_rows,
        }
        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        write_csv(out/STEPS,step_rows);write_csv(out/ROUTES,route_rows);write_csv(out/PRODUCERS,producer_rows_all)
        write_csv(out/GATES,gates)
        write_csv(out/MANIFEST,[{"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size}
                                for p in sorted(out.iterdir()) if p.is_file() and p.name!=MANIFEST])

        print("="*190);print(M,"PASS")
        print("Additional recurrent transitions             :",ROLLOUT_STEPS)
        print("Start / final day                            :",times[0],"/",final_time)
        print("Final flow-epoch age days                    :",final_time-FLOW_EPOCH_DAY)
        print("Cumulative Hybrid / exact route uses         :",cumulative_hybrid_routes,"/",cumulative_exact_routes)
        print("Mixed final cumulative mass residual kg      :",mixed_final_res)
        print("Final mixed vs exact saturation relL2        :",final_sat_rel)
        print("Final mixed vs exact saturation Linf         :",final_sat_linf)
        print("Final mixed-exact stored mass difference kg  :",final_stored_diff)
        print("Final mixed-exact producer gas-cut diff      :",final_cut_diff)
        print("G4-A6 integrated GPU runtime assembly        : AUTHORIZED")
        print("="*190)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps({
            "milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),"gates":gates,
            "A4_start_child_sha256_before":a4_child_sha_before,
            "Day75_source_state_sha256_before":day75_sha_before,
            "production_canonical_chain_replaced":False,
            "G4_A6_integrated_GPU_runtime_assembly_authorized":False,
            "integrated_GPU_runtime_authorized":False,"P4_authorized":False,
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
