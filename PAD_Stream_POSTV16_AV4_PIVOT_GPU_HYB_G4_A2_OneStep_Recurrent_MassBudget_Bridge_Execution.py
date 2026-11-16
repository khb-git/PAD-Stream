#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
from typing import Any
import numpy as np

M="POSTV16-AV4-PIVOT-GPU-HYB-G4-A2"
PASS="POSTV16AV4PIVOTGPUHYBG4A2_ONESTEP_RECURRENT_MASS_BUDGET_BRIDGE_PASS"
BLOCK="POSTV16AV4PIVOTGPUHYBG4A2_TECHNICAL_OR_CONSERVATIVE_BRIDGE_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="bae121196088ca89394c6213b62664cf4419150b"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

A1_REL=BASE_AV4/"POSTV16_AV4_PIVOT_GPU_HYB_G4_A1_R1_ReadOnly_Hybrid_ComponentMass_Bridge_TOF_Identity_Repair"
A1_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_A1_R1_Summary.json"
A1_STATUS="POSTV16AV4PIVOTGPUHYBG4A1R1_READONLY_HYBRID_COMPONENT_MASS_BRIDGE_TOF_IDENTITY_REPAIR_PASS"

G2_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_R1_Rank1_Day75_80_ExactFlow_and_Hybrid_Endpoint_Diagnostic.py"
G2_BLOB="04c3940a7c736b1d210376113e48bab6111fc173"
A1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_A1_R1_ReadOnly_Hybrid_ComponentMass_Bridge_TOF_Identity_Repair.py"
A1_BLOB="6b0bff953b11b393affc429825622fe4afdc5942"
B1_RUNNER="PAD_Stream_POSTV16_AV1_B1_R1_C26_to_E37A_Component_Mass_Representation_Equivalence_Audit.py"
B1_BLOB="8d9561d7c85805b82dedc26073c4633f90eeeab6"
R3R4R1_RUNNER="PAD_Stream_V16E41R3R4R1_Refreshed_Flow_CFL_Alignment_Repair.py"
R3R4R1_BLOB="5f8433437ce111533338ceada922f51abb2edefe"
E11_RUNNER="PAD_Stream_V16E11_R2_Packed_SG5_Serialization_Repair_and_Controlled_Hybrid_Streamline_Pilot.py"
E11_BLOB="bf89c14a3cb177fb483e233a17b72e824d31119b"

DAY_TO_S=86400.0
EXPECTED_NSTREAM=1078
EXPECTED_NFACES=201
EXPECTED_NCV=200
TARGET_PARENT_DAY=75.0

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_A2"
OUT_REL=BASE_AV4/(OUT_TOKEN+"_OneStep_Recurrent_MassBudget_Bridge_Execution")
BLOCK_REL=BASE_AV4/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
METRICS=f"{OUT_TOKEN}_Hybrid10_Accepted_Streamline_Metrics.csv"
AGG=f"{OUT_TOKEN}_Aggregate_Metrics.json"
ARRAYS=f"{OUT_TOKEN}_Bridge_Arrays.npz"
GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"

class GateError(RuntimeError):pass

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""): h.update(c)
    return h.hexdigest()

def git_blob(root:Path,p:Path)->str:
    return subprocess.check_output(["git","-C",str(root),"hash-object",str(p)],text=True).strip()

def gt(root:Path,*a:str)->str:
    return subprocess.check_output(["git","-C",str(root),*a],text=True).strip()

def load_mod(root:Path,fn:str,blob:str,name:str):
    p=root/fn
    if not p.is_file():raise GateError(f"missing_source:{fn}")
    actual=git_blob(root,p)
    if actual!=blob:raise GateError(f"source_blob:{fn}:{actual}:{blob}")
    s=importlib.util.spec_from_file_location(name,p)
    if s is None or s.loader is None:raise GateError(f"import_spec:{fn}")
    m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m

def js(p:Path):return json.loads(p.read_text(encoding="utf-8"))

def load_npz(p:Path,allow_pickle=False):
    with np.load(p,allow_pickle=allow_pickle) as z:
        return {k:np.asarray(z[k]).copy() for k in z.files}

def scalar(x:Any)->float:return float(np.asarray(x).reshape(()))

def read_manifest(path:Path)->dict[str,str]:
    out={}
    with path.open(newline="",encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out[row["file"]]=row["sha256"]
    return out

def write_csv(path:Path,rows:list[dict[str,Any]]):
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields:fields.append(k)
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows)

def rel_l2(a,b):
    a=np.asarray(a,dtype=np.float64);b=np.asarray(b,dtype=np.float64)
    return float(np.linalg.norm((a-b).ravel())/max(float(np.linalg.norm(b.ravel())),1e-30))

def pct(x):
    q=np.asarray(x,dtype=np.float64)
    return {"min":float(np.min(q)),"median":float(np.median(q)),
            "p95":float(np.percentile(q,95)),"max":float(np.max(q)),
            "mean":float(np.mean(q))}

def selftest():
    x=np.array([1.,2.,3.])
    assert abs(float(np.sum(x))-6.0)<1e-15
    print("POSTV16 GPU-HYB-G4-A2 structural self-test: PASS")

def main(root:Path,drive:Path)->int:
    root=root.resolve();drive=drive.resolve();out=drive/OUT_REL;blocked=drive/BLOCK_REL
    gates=[];stage="preflight"
    def gate(n,c,d=None):
        ok=bool(c);gates.append({"stage":stage,"gate":n,"pass":ok,"detail":"" if d is None else repr(d)})
        print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"),flush=True)
        if not ok:raise GateError(n)
    try:
        print("="*190)
        print("G4-A2 — ONE-STEP RECURRENT HYBRID COMPONENT-MASS BUDGET BRIDGE")
        print("DAY75 EXACT PARENT + DAY75 EXACT FLOW NETWORK; HYBRID INFERENCE AT 75+DT; REAL PARENT+INLET-OUTLET MASS BUDGET.")
        print("EXACT E37A CHILD IS BENCHMARK ONLY. NO GRID MAPBACK. NO CANONICAL STATE MUTATION.")
        print("="*190)

        stage="repository"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_G4_A1_R1",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")
        g2=load_mod(root,G2_RUNNER,G2_BLOB,"g4a2_g2")
        a1=load_mod(root,A1_RUNNER,A1_BLOB,"g4a2_a1")
        b1=load_mod(root,B1_RUNNER,B1_BLOB,"g4a2_b1")
        r3r4r1=load_mod(root,R3R4R1_RUNNER,R3R4R1_BLOB,"g4a2_r3r4r1")
        e11=load_mod(root,E11_RUNNER,E11_BLOB,"g4a2_e11")

        stage="A1_authority"
        a1s=js(drive/A1_REL/A1_SUM)
        gate("A1_status_exact",a1s.get("status")==A1_STATUS,a1s.get("status"))
        gate("A1_201_to_200_certified",a1s.get("201_to_200_component_mass_projection_certified") is True)
        gate("A1_box_projection_certified",a1s.get("box_constrained_target_mass_projection_certified") is True)
        gate("A1_A2_authorized",a1s.get("G4_A2_one_step_recurrent_bridge_execution_authorized") is True)
        gate("A1_no_canonical_mutation",a1s.get("canonical_state_mutated") is False)

        stage="Day75_authority"
        g2s=js(drive/g2.OUT_REL/g2.SUMMARY)
        gate("G2_status_exact",g2s.get("status")==g2.PASS,g2s.get("status"))
        state_path=drive/g2.OUT_REL/g2.DAY75_STATE
        diag_path=drive/g2.OUT_REL/g2.DAY75_DIAG
        manifest=read_manifest(drive/g2.OUT_REL/g2.MANIFEST)
        gate("Day75_state_SHA_summary",sha(state_path)==g2s["Day75_exact_state_sha256"],sha(state_path))
        gate("Day75_state_SHA_manifest",sha(state_path)==manifest[g2.DAY75_STATE],sha(state_path))
        gate("Day75_diag_SHA_manifest",sha(diag_path)==manifest[g2.DAY75_DIAG],sha(diag_path))
        parent=load_npz(state_path);diag=load_npz(diag_path)
        gate("Day75_parent_time_exact",abs(scalar(parent["physical_time_days"])-TARGET_PARENT_DAY)<=1e-12,scalar(parent["physical_time_days"]))
        gate("Day75_diag_time_exact",abs(scalar(diag["physical_time_days"])-TARGET_PARENT_DAY)<=1e-12,scalar(diag["physical_time_days"]))

        stage="exact_runtime_modules"
        role={}
        for key in ["E36","E37A","R2_PHYSICS","SG7A","SG7D"]:
            fn,blob=r3r4r1.SOURCE_BLOBS[key]
            role[key]=g2.load_module_blob(root/fn,blob,f"g4a2_{key.lower()}",root)
        e36=role["E36"];e37a=role["E37A"];physics=role["R2_PHYSICS"];sg7a=role["SG7A"];sg7d=role["SG7D"]

        stage="Day75_CV_parent"
        pressure=np.asarray(diag["pressure_psi"],dtype=np.float64)
        xyz=np.asarray(diag["xyz_m"],dtype=np.float64)
        tau=np.asarray(diag["tau_s"],dtype=np.float64)
        tau_end=np.asarray(diag["tau_end_s"],dtype=np.float64)
        weights_s=np.asarray(diag["weights_m3_s"],dtype=np.float64)
        xi=np.asarray(diag["xi"],dtype=np.float64)
        labels=np.asarray(diag["producer"]).astype("U64")
        exact_parent_face=np.asarray(diag["exact_runtime_face_saturation"],dtype=np.float64)
        gate("Day75_transport_shapes",
             xyz.shape==(EXPECTED_NSTREAM,EXPECTED_NFACES,3)
             and tau.shape==(EXPECTED_NSTREAM,EXPECTED_NFACES)
             and xi.shape==(EXPECTED_NFACES,)
             and exact_parent_face.shape==(EXPECTED_NSTREAM,EXPECTED_NFACES),
             (xyz.shape,tau.shape,xi.shape,exact_parent_face.shape))
        old_cv_sat=exact_parent_face[:,1:]
        p_ref=scalar(parent["co2_density_reference_pressure_pa"])
        op=sg7d.build_subsegment_operator(xyz,tau/DAY_TO_S,weights_s*DAY_TO_S)
        geometry=e37a.build_control_volume_geometry(physics,op,pressure,p_ref,EXPECTED_NSTREAM,EXPECTED_NCV)
        coeff=np.asarray(geometry["cv_pressure_mass_coeff"],dtype=np.float64)
        old_cv_mass=np.asarray(e37a.cv_mass_from_saturation(physics,old_cv_sat,coeff),dtype=np.float64)
        capacity=np.asarray(e37a.cv_mass_from_saturation(
            physics,np.full((EXPECTED_NSTREAM,EXPECTED_NCV),
                            float(physics.BACKGROUND_SATURATION+physics.MAX_INCREMENTAL_CO2_SATURATION)),coeff),dtype=np.float64)
        face_pressure=e37a.build_face_pressure(e36,sg7d,xyz,pressure)
        dt=float(r3r4r1.transport_cfl_dt_days(sg7a,xi,tau_end))
        gate("one_step_dt_positive",np.isfinite(dt) and dt>0.0,dt)
        child_day=TARGET_PARENT_DAY+dt

        stage="production_budget"
        q=weights_s*DAY_TO_S
        u=np.asarray(sg7a.u_dimensionless(xi),dtype=np.float64)
        inlet_rate=q*float(e37a.CO2_RHO_REF_KG_M3)
        outlet_sat=old_cv_sat[:,-1]
        outlet_ff=np.asarray(sg7a.fractional_flow(outlet_sat),dtype=np.float64)
        outlet_rho=np.asarray(physics.gas_density_from_state(
            outlet_sat,face_pressure[:,-1],p_ref),dtype=np.float64)
        outlet_rate=q*float(u[-1])*outlet_ff*outlet_rho
        injected_i=inlet_rate*dt
        produced_i=outlet_rate*dt
        target_total=np.sum(old_cv_mass,axis=1)+injected_i-produced_i
        gate("target_totals_finite",np.all(np.isfinite(target_total)))
        gate("target_totals_nonnegative",float(np.min(target_total))>=-1e-8,float(np.min(target_total)))
        gate("target_totals_capacity_feasible",
             np.all(target_total<=np.sum(capacity,axis=1)+1e-8),
             float(np.max(target_total-np.sum(capacity,axis=1))))

        stage="exact_benchmark"
        exact=e37a.advance_component_mass_control_volumes(
            physics,sg7a,old_cv_sat,old_cv_mass,coeff,face_pressure,p_ref,q,xi,dt)
        exact_mass=np.asarray(exact["new_mass"],dtype=np.float64)
        exact_sat=np.asarray(exact["new_saturation"],dtype=np.float64)
        telescoping=np.sum(exact_mass,axis=1)-target_total
        gate("boundary_budget_matches_exact_per_streamline",
             float(np.max(np.abs(telescoping)))<=1e-7,float(np.max(np.abs(telescoping))))
        gate("global_injected_matches_exact",
             abs(float(np.sum(injected_i))-float(exact["injected_mass_kg"]))<=1e-7,
             float(np.sum(injected_i))-float(exact["injected_mass_kg"]))
        gate("global_produced_matches_exact",
             abs(float(np.sum(produced_i))-float(exact["produced_mass_kg"]))<=1e-7,
             float(np.sum(produced_i))-float(exact["produced_mass_kg"]))

        stage="Hybrid_inference_authority"
        for rel,entry,label in [
            (e11.E8R1_REL,e11.E8R1["contract"],"E8R1_contract"),
            (e11.E5_REL,e11.E5_MANIFEST,"E5_manifest"),
            (e11.E3_REL,e11.E3_PROTOCOL,"E3_protocol"),
            (e11.E6A_REL,e11.E6A_CHECKPOINT,"E6A_checkpoint"),
        ]:
            fn,expected=entry;path=drive/rel/fn
            gate(label+"_present",path.is_file(),str(path))
            gate(label+"_SHA_exact",e11.sha(path)==expected,e11.sha(path))
        e8=e11.read_json(drive/e11.E8R1_REL/e11.E8R1["contract"][0])
        screen=e8["learned_proposal_execution_screen"]
        e5=e11.read_json(drive/e11.E5_REL/e11.E5_MANIFEST[0])
        e3=e11.read_json(drive/e11.E3_REL/e11.E3_PROTOCOL[0])
        p=e11.c14_production_params(root/e11.C14_SOURCE[0])
        gate("C14_inside_E3",e11.parameters_inside_e3(p,e3),p)
        adapter=e11.import_exact(root/e11.E9_ADAPTER[0],e11.E9_ADAPTER[1],"g4a2_adapter")
        r2teacher=e11.import_exact(root/e11.R2_ADAPTER[0],e11.R2_ADAPTER[1],"g4a2_r2teacher")
        e9r1=e11.import_exact(root/e11.E9R1_RUNNER[0],e11.E9R1_RUNNER[1],"g4a2_e9r1")
        shock=r2teacher.welge_shock(adapter.teacher_params(p),scan_nodes=4097)
        speed=float(shock["characteristic_speed"]);swstar=float(shock["Sw_star"])
        terminal_days=tau_end/DAY_TO_S
        xstar=(child_day/terminal_days)*speed
        clock=np.asarray([e11.classify_clock(float(x)) for x in xstar],dtype="U32")
        gate("all_child_clocks_resolved",not np.any(clock=="UNRESOLVED"))
        learned_candidate=clock=="LEARNED_WINDOW"
        gate("at_least_one_child_learned_candidate",int(np.sum(learned_candidate))>0,int(np.sum(learned_candidate)))

        tf=e9r1.prepare_tf(e5)
        gate("TensorFlow_2_20_exact",tf.__version__=="2.20.0",tf.__version__)
        gate("TensorFlow_GPU_visible",len(tf.config.list_physical_devices("GPU"))>=1,
             [str(x) for x in tf.config.list_physical_devices("GPU")])
        model10=e9r1.build_inference_model(tf,10,"G4A2_Hybrid10")
        gate("Hybrid10_parameter_count_exact",model10.count_params()==52545,model10.count_params())
        model10.load_weights(str(drive/e11.E6A_REL/e11.E6A_CHECKPOINT[0]))

        idx=np.flatnonzero(learned_candidate)
        cond=[];states=[]
        for i in idx:
            st=adapter.physical_time_state(
                elapsed_time=child_day,tau_end=float(terminal_days[i]),
                characteristic_speed=speed,Sw_star=swstar)
            if not (0.05<=float(st["xD_star"])<=0.95):raise GateError("child_learned_candidate_outside_window")
            states.append(st);cond.append(adapter.conditioning_vector("HYBRID10",p,st))
        pred=e9r1.infer(tf,model10,xi.astype(np.float32),np.asarray(cond,dtype=np.float32),batch=256)

        accepted=[];profiles=[];rejection_counts={}
        for local,i in enumerate(idx):
            fan=pred[local];st=states[local]
            ok,sm=e11.screen_fan_prediction(
                fan,p,st,xi,tau[i]/DAY_TO_S,r2teacher,adapter,screen)
            if ok:
                profile=adapter.project_fan_to_pollock_nodes(
                    tau_nodes=tau[i]/DAY_TO_S,state=st,fan_xi=xi,fan_sw=fan,swc=float(p["swc"])
                ).astype(np.float64)
                accepted.append(int(i));profiles.append(profile)
            else:
                for reason in sm["failures"]:
                    rejection_counts[reason]=rejection_counts.get(reason,0)+1
        accepted=np.asarray(accepted,dtype=np.int64)
        profiles=np.asarray(profiles,dtype=np.float64)
        gate("at_least_one_Hybrid10_screen_accept",accepted.size>0,int(accepted.size))
        gate("accepted_profile_shape",profiles.shape==(accepted.size,EXPECTED_NFACES),profiles.shape)
        gate("accepted_profiles_finite",np.all(np.isfinite(profiles)))

        stage="Hybrid_mass_bridge"
        cand_sat,cand_mass,cand_source=b1.project_201_to_200_component_mass(
            physics,e37a,profiles,coeff,accepted)
        cand_proj_res=np.sum(cand_mass,axis=1)-np.sum(cand_source,axis=1)
        gate("candidate_201_to_200_mass_conservative",
             float(np.max(np.abs(cand_proj_res)))<=1e-7,float(np.max(np.abs(cand_proj_res))))
        corrected=np.empty_like(cand_mass)
        corrected_sat=np.empty_like(cand_sat)
        rows=[];closures=[];rel_corr=[];sat_corr=[];exact_mass_rel=[];exact_sat_rel=[]
        for local,sl in enumerate(accepted):
            target=float(target_total[sl])
            c=np.asarray(cand_mass[local],dtype=np.float64)
            cap=np.asarray(capacity[sl],dtype=np.float64)
            m,lam,closure=a1.box_project(c,target,cap)
            ss=np.asarray(e37a.invert_cv_mass_to_saturation(physics,m,coeff[sl]),dtype=np.float64)
            corrected[local]=m;corrected_sat[local]=ss
            recon=np.asarray(e37a.cv_mass_from_saturation(physics,ss,coeff[sl]),dtype=np.float64)
            recon_err=float(np.max(np.abs(recon-m)))
            if recon_err>1e-7:raise GateError(f"corrected_mass_inversion:{int(sl)}:{recon_err}")
            dm=m-c
            rc=float(np.sum(np.abs(dm))/max(abs(target),1e-30))
            sc=float(np.max(np.abs(ss-cand_sat[local])))
            emr=rel_l2(m,exact_mass[sl]);esr=rel_l2(ss,exact_sat[sl])
            closures.append(abs(closure));rel_corr.append(rc);sat_corr.append(sc)
            exact_mass_rel.append(emr);exact_sat_rel.append(esr)
            rows.append({
                "streamline_index":int(sl),
                "parent_total_component_mass_kg":float(np.sum(old_cv_mass[sl])),
                "injected_component_mass_kg":float(injected_i[sl]),
                "produced_component_mass_kg":float(produced_i[sl]),
                "recurrent_target_total_component_mass_kg":target,
                "candidate_total_component_mass_kg":float(np.sum(c)),
                "candidate_total_mass_signed_error_kg":float(np.sum(c)-target),
                "corrected_total_component_mass_kg":float(np.sum(m)),
                "budget_closure_residual_kg":float(closure),
                "mass_correction_relative_L1":rc,
                "saturation_correction_Linf":sc,
                "corrected_vs_exact_mass_relative_L2":emr,
                "corrected_vs_exact_saturation_relative_L2":esr,
                "minimum_capacity_margin_kg":float(np.min(cap-m)),
                "mass_inversion_Linf_kg":recon_err,
                "lambda_shift_kg":float(lam),
            })

        gate("all_Hybrid10_budget_projections_feasible",len(rows)==accepted.size,len(rows))
        gate("all_Hybrid10_budget_closures_numerical",float(np.max(closures))<=1e-8,float(np.max(closures)))
        gate("all_corrected_Hybrid10_capacity_safe",
             np.all(corrected>=-1e-10) and np.all(corrected<=capacity[accepted]+1e-8))

        stage="publication"
        gate("output_absent",not out.exists(),str(out));out.mkdir(parents=True)
        aggregate={
            "parent_day":TARGET_PARENT_DAY,
            "one_step_dt_days":dt,
            "child_day":child_day,
            "learned_window_candidates":int(np.sum(learned_candidate)),
            "Hybrid10_screen_accept_count":int(accepted.size),
            "Hybrid10_screen_reject_count":int(np.sum(learned_candidate))-int(accepted.size),
            "preBT_exact_fallback_count":int(np.sum(clock=="PREBT_EXACT_R2")),
            "postBT_exact_fallback_count":int(np.sum(clock=="POSTBT_FULL_PHYSICS")),
            "screen_rejection_reason_counts":rejection_counts,
            "boundary_budget_vs_exact_per_streamline_Linf_kg":float(np.max(np.abs(telescoping))),
            "budget_closure_abs_kg":pct(closures),
            "mass_correction_relative_L1":pct(rel_corr),
            "saturation_correction_Linf":pct(sat_corr),
            "corrected_vs_exact_mass_relative_L2":pct(exact_mass_rel),
            "corrected_vs_exact_saturation_relative_L2":pct(exact_sat_rel),
            "scientific_acceptance_threshold_defined":False,
        }
        summary={
            "milestone":M,"status":PASS,
            "classification":"REAL_PARENT_PLUS_INLET_MINUS_OUTLET_RECURRENT_MASS_BUDGET_CERTIFIED_FOR_HYBRID10_ONESTEP_G4_A3_MIXED_ROUTE_MAPBACK_AUTHORIZED",
            "parent_day":TARGET_PARENT_DAY,
            "one_step_dt_days":dt,
            "child_day":child_day,
            "production_recurrent_budget_calculation_certified":True,
            "budget_uses_exact_interior_transport":False,
            "exact_E37A_child_used_as_benchmark_only":True,
            "new_Hybrid_inference_performed":True,
            "Hybrid10_screen_accept_count":int(accepted.size),
            "201_to_200_component_mass_projection_certified":True,
            "box_constrained_recurrent_target_projection_certified":True,
            "all_Hybrid10_budget_projections_feasible":True,
            "all_Hybrid10_budget_closures_numerical":True,
            "grid_mapback_performed":False,
            "physical_canonical_state_advanced":False,
            "canonical_state_mutated":False,
            "new_scientific_threshold_defined":False,
            "Hybrid_canonical_state_mutation_authorized":False,
            "G4_A3_mixed_route_one_step_conservative_mapback_authorized":True,
            "integrated_GPU_runtime_authorized":False,
            "P4_authorized":False,
            "aggregate_metrics":aggregate,
        }
        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        (out/AGG).write_text(json.dumps(aggregate,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        write_csv(out/METRICS,rows)
        np.savez_compressed(out/ARRAYS,
            accepted_streamline_index=accepted,
            parent_cv_component_mass_kg=old_cv_mass[accepted],
            candidate_cv_saturation=cand_sat,
            candidate_cv_component_mass_kg=cand_mass,
            corrected_cv_saturation=corrected_sat,
            corrected_cv_component_mass_kg=corrected,
            exact_benchmark_cv_saturation=exact_sat[accepted],
            exact_benchmark_cv_component_mass_kg=exact_mass[accepted],
            target_total_component_mass_kg=target_total[accepted],
            injected_component_mass_kg=injected_i[accepted],
            produced_component_mass_kg=produced_i[accepted])
        write_csv(out/GATES,gates)
        manifest=[{"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size}
                  for p in sorted(out.iterdir()) if p.is_file() and p.name!=MANIFEST]
        write_csv(out/MANIFEST,manifest)

        print("="*190);print(M,"PASS")
        print("Parent / child day                             :",TARGET_PARENT_DAY,"/",child_day)
        print("One-step dt days                              :",dt)
        print("Learned-window / Hybrid10 accepts             :",int(np.sum(learned_candidate)),"/",int(accepted.size))
        print("Real parent+inlet-outlet budget certified     : True")
        print("Exact interior transport used for budget      : False")
        print("Boundary budget vs exact max abs kg           :",float(np.max(np.abs(telescoping))))
        print("Max Hybrid budget closure abs kg              :",float(np.max(closures)))
        print("Median Hybrid mass correction relative L1     :",float(np.median(rel_corr)))
        print("P95 Hybrid mass correction relative L1        :",float(np.percentile(rel_corr,95)))
        print("Median corrected-vs-exact mass relL2          :",float(np.median(exact_mass_rel)))
        print("Grid mapback / canonical mutation             : False / False")
        print("G4-A3 mixed-route mapback authorized          : True")
        print("="*190)
        return 0
    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps({
            "milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),"gates":gates,
            "grid_mapback_performed":False,"canonical_state_mutated":False,
            "G4_A3_mixed_route_one_step_conservative_mapback_authorized":False,
            "Hybrid_canonical_state_mutation_authorized":False,
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
