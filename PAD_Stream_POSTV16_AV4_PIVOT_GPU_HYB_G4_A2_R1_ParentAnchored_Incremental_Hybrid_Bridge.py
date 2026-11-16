#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
from typing import Any
import numpy as np

M="POSTV16-AV4-PIVOT-GPU-HYB-G4-A2-R1"
PASS="POSTV16AV4PIVOTGPUHYBG4A2R1_PARENT_ANCHORED_INCREMENTAL_HYBRID_BRIDGE_PASS"
BLOCK="POSTV16AV4PIVOTGPUHYBG4A2R1_TECHNICAL_OR_CONSERVATIVE_BRIDGE_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="de04173d2f591e6316debf562667e0acdbaafcfe"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

A2_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_A2_OneStep_Recurrent_MassBudget_Bridge_Execution.py"
A2_BLOB="c3283093179ef9dac7e5111784e1b3037db6dd83"
A1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_A1_R1_ReadOnly_Hybrid_ComponentMass_Bridge_TOF_Identity_Repair.py"
A1_BLOB="6b0bff953b11b393affc429825622fe4afdc5942"
G2_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_R1_Rank1_Day75_80_ExactFlow_and_Hybrid_Endpoint_Diagnostic.py"
G2_BLOB="04c3940a7c736b1d210376113e48bab6111fc173"
B1_RUNNER="PAD_Stream_POSTV16_AV1_B1_R1_C26_to_E37A_Component_Mass_Representation_Equivalence_Audit.py"
B1_BLOB="8d9561d7c85805b82dedc26073c4633f90eeeab6"
R3R4_RUNNER="PAD_Stream_V16E41R3R4R1_Refreshed_Flow_CFL_Alignment_Repair.py"
R3R4_BLOB="5f8433437ce111533338ceada922f51abb2edefe"
E11_RUNNER="PAD_Stream_V16E11_R2_Packed_SG5_Serialization_Repair_and_Controlled_Hybrid_Streamline_Pilot.py"
E11_BLOB="bf89c14a3cb177fb483e233a17b72e824d31119b"

DAY_TO_S=86400.0
NSTREAM=1078
NFACES=201
NCV=200
PARENT_DAY=75.0

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_A2_R1"
OUT_REL=BASE/(OUT_TOKEN+"_ParentAnchored_Incremental_Hybrid_Bridge")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
METRICS=f"{OUT_TOKEN}_Hybrid10_Incremental_Metrics.csv"
AGG=f"{OUT_TOKEN}_Aggregate_Metrics.json"
ARRAYS=f"{OUT_TOKEN}_Incremental_Bridge_Arrays.npz"
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
    return subprocess.check_output(["git","-C",str(root),"hash-object",str(p)],text=True).strip()

def mod(root:Path,fn:str,expected:str,name:str):
    p=root/fn
    if not p.is_file():raise GateError(f"missing_source:{fn}")
    actual=blob(root,p)
    if actual!=expected:raise GateError(f"source_blob:{fn}:{actual}:{expected}")
    s=importlib.util.spec_from_file_location(name,p)
    if s is None or s.loader is None:raise GateError(f"import_spec:{fn}")
    m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m

def js(p:Path):return json.loads(p.read_text(encoding="utf-8"))

def load_npz(p:Path):
    with np.load(p,allow_pickle=False) as z:return {k:np.asarray(z[k]).copy() for k in z.files}

def scalar(x:Any)->float:return float(np.asarray(x).reshape(()))

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

def pct(x):
    a=np.asarray(x,float)
    return {"min":float(np.min(a)),"median":float(np.median(a)),"p95":float(np.percentile(a,95)),
            "max":float(np.max(a)),"mean":float(np.mean(a))}

def selftest():
    parent=np.array([10.,20.]);m0=np.array([1.,3.]);m1=np.array([2.,4.])
    c=parent+(m1-m0)
    assert np.array_equal(c,np.array([11.,21.]))
    print("POSTV16 GPU-HYB-G4-A2-R1 structural self-test: PASS")

def main(root:Path,drive:Path)->int:
    root=root.resolve();drive=drive.resolve();out=drive/OUT_REL;blocked=drive/BLOCK_REL
    gates=[];stage="preflight"
    def gate(n,c,d=None):
        ok=bool(c);gates.append({"stage":stage,"gate":n,"pass":ok,"detail":"" if d is None else repr(d)})
        print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"),flush=True)
        if not ok:raise GateError(n)
    try:
        print("="*190)
        print("G4-A2-R1 — PARENT-ANCHORED INCREMENTAL HYBRID RECURRENT BRIDGE")
        print("HYBRID PROPOSES DELTA BETWEEN t AND t+dt; EXACT RECURRENT PARENT REMAINS THE BASE.")
        print("REAL PARENT+INLET-OUTLET MASS BUDGET; EXACT E37A CHILD BENCHMARK ONLY; NO MAPBACK; NO CANONICAL MUTATION.")
        print("="*190)

        stage="repository"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_G4_A2",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")
        a2=mod(root,A2_RUNNER,A2_BLOB,"a2r1_a2")
        a1=mod(root,A1_RUNNER,A1_BLOB,"a2r1_a1")
        g2=mod(root,G2_RUNNER,G2_BLOB,"a2r1_g2")
        b1=mod(root,B1_RUNNER,B1_BLOB,"a2r1_b1")
        r3r4=mod(root,R3R4_RUNNER,R3R4_BLOB,"a2r1_r3r4")
        e11=mod(root,E11_RUNNER,E11_BLOB,"a2r1_e11")

        stage="A2_authority"
        a2s=js(drive/a2.OUT_REL/a2.SUMMARY)
        gate("A2_status_exact",a2s.get("status")==a2.PASS,a2s.get("status"))
        gate("A2_real_budget_certified",a2s.get("production_recurrent_budget_calculation_certified") is True)
        gate("A2_exact_not_used_for_budget",a2s.get("budget_uses_exact_interior_transport") is False)
        gate("A2_no_mapback",a2s.get("grid_mapback_performed") is False)
        baseline=a2s["aggregate_metrics"]

        stage="Day75_authority"
        g2s=js(drive/g2.OUT_REL/g2.SUMMARY)
        gate("G2_status_exact",g2s.get("status")==g2.PASS,g2s.get("status"))
        state=load_npz(drive/g2.OUT_REL/g2.DAY75_STATE)
        diag=load_npz(drive/g2.OUT_REL/g2.DAY75_DIAG)
        gate("parent_day_exact",abs(scalar(state["physical_time_days"])-PARENT_DAY)<=1e-12,scalar(state["physical_time_days"]))
        gate("diag_day_exact",abs(scalar(diag["physical_time_days"])-PARENT_DAY)<=1e-12,scalar(diag["physical_time_days"]))
        parent_route=np.asarray(diag["route_code"],dtype=np.int64)
        parent_profiles=np.asarray(diag["hybrid_projected_learned_profile"],dtype=np.float64)
        gate("parent_Hybrid10_present",int(np.sum(parent_route==10))>0,int(np.sum(parent_route==10)))

        stage="exact_runtime_geometry"
        roles={}
        for key in ["E36","E37A","R2_PHYSICS","SG7A","SG7D"]:
            fn,bl=r3r4.SOURCE_BLOBS[key]
            roles[key]=g2.load_module_blob(root/fn,bl,f"a2r1_{key.lower()}",root)
        e36=roles["E36"];e37a=roles["E37A"];physics=roles["R2_PHYSICS"];sg7a=roles["SG7A"];sg7d=roles["SG7D"]

        pressure=np.asarray(diag["pressure_psi"],float)
        xyz=np.asarray(diag["xyz_m"],float);tau=np.asarray(diag["tau_s"],float)
        tau_end=np.asarray(diag["tau_end_s"],float);weights_s=np.asarray(diag["weights_m3_s"],float)
        xi=np.asarray(diag["xi"],float)
        exact_parent_face=np.asarray(diag["exact_runtime_face_saturation"],float)
        p_ref=scalar(state["co2_density_reference_pressure_pa"])
        op=sg7d.build_subsegment_operator(xyz,tau/DAY_TO_S,weights_s*DAY_TO_S)
        geometry=e37a.build_control_volume_geometry(physics,op,pressure,p_ref,NSTREAM,NCV)
        coeff=np.asarray(geometry["cv_pressure_mass_coeff"],float)
        old_sat=exact_parent_face[:,1:]
        old_mass=np.asarray(e37a.cv_mass_from_saturation(physics,old_sat,coeff),float)
        capacity=np.asarray(e37a.cv_mass_from_saturation(
            physics,np.full((NSTREAM,NCV),float(physics.BACKGROUND_SATURATION+physics.MAX_INCREMENTAL_CO2_SATURATION)),coeff),float)
        face_pressure=e37a.build_face_pressure(e36,sg7d,xyz,pressure)
        dt=float(r3r4.transport_cfl_dt_days(sg7a,xi,tau_end))
        child_day=PARENT_DAY+dt
        gate("dt_matches_A2",abs(dt-float(a2s["one_step_dt_days"]))<=1e-15,(dt,a2s["one_step_dt_days"]))

        stage="real_recurrent_budget"
        q=weights_s*DAY_TO_S
        u=np.asarray(sg7a.u_dimensionless(xi),float)
        inlet_rate=q*float(e37a.CO2_RHO_REF_KG_M3)
        outlet_sat=old_sat[:,-1]
        outlet_ff=np.asarray(sg7a.fractional_flow(outlet_sat),float)
        outlet_rho=np.asarray(physics.gas_density_from_state(outlet_sat,face_pressure[:,-1],p_ref),float)
        outlet_rate=q*float(u[-1])*outlet_ff*outlet_rho
        injected_i=inlet_rate*dt;produced_i=outlet_rate*dt
        target=np.sum(old_mass,axis=1)+injected_i-produced_i
        gate("targets_capacity_feasible",np.all(target<=np.sum(capacity,axis=1)+1e-8),
             float(np.max(target-np.sum(capacity,axis=1))))

        exact=e37a.advance_component_mass_control_volumes(
            physics,sg7a,old_sat,old_mass,coeff,face_pressure,p_ref,q,xi,dt)
        exact_mass=np.asarray(exact["new_mass"],float);exact_sat=np.asarray(exact["new_saturation"],float)
        budget_exact=np.sum(exact_mass,axis=1)-target
        gate("budget_matches_exact_per_streamline",float(np.max(np.abs(budget_exact)))<=1e-7,float(np.max(np.abs(budget_exact))))

        stage="Hybrid_child_inference"
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
        p=e11.c14_production_params(root/e11.C14_SOURCE[0])
        gate("C14_inside_E3",e11.parameters_inside_e3(p,e3))
        adapter=e11.import_exact(root/e11.E9_ADAPTER[0],e11.E9_ADAPTER[1],"a2r1_adapter")
        r2teacher=e11.import_exact(root/e11.R2_ADAPTER[0],e11.R2_ADAPTER[1],"a2r1_teacher")
        e9r1=e11.import_exact(root/e11.E9R1_RUNNER[0],e11.E9R1_RUNNER[1],"a2r1_e9r1")
        shock=r2teacher.welge_shock(adapter.teacher_params(p),scan_nodes=4097)
        speed=float(shock["characteristic_speed"]);swstar=float(shock["Sw_star"])
        terminal_days=tau_end/DAY_TO_S
        xstar_child=(child_day/terminal_days)*speed
        child_clock=np.asarray([e11.classify_clock(float(x)) for x in xstar_child],dtype="U32")
        child_candidates=child_clock=="LEARNED_WINDOW"
        joint_candidate=(parent_route==10)&child_candidates
        gate("joint_parent_child_learned_candidates_present",int(np.sum(joint_candidate))>0,int(np.sum(joint_candidate)))

        tf=e9r1.prepare_tf(e5)
        gate("TensorFlow_2_20_exact",tf.__version__=="2.20.0",tf.__version__)
        gate("GPU_visible",len(tf.config.list_physical_devices("GPU"))>=1,[str(x) for x in tf.config.list_physical_devices("GPU")])
        model=e9r1.build_inference_model(tf,10,"G4A2R1_Hybrid10")
        gate("Hybrid10_parameter_count_exact",model.count_params()==52545,model.count_params())
        model.load_weights(str(drive/e11.E6A_REL/e11.E6A_CHECKPOINT[0]))

        idx=np.flatnonzero(joint_candidate);cond=[];states=[]
        for i in idx:
            st=adapter.physical_time_state(elapsed_time=child_day,tau_end=float(terminal_days[i]),
                                           characteristic_speed=speed,Sw_star=swstar)
            states.append(st);cond.append(adapter.conditioning_vector("HYBRID10",p,st))
        pred=e9r1.infer(tf,model,xi.astype(np.float32),np.asarray(cond,dtype=np.float32),batch=256)

        accepted=[];child_profiles=[];rejections={}
        for local,i in enumerate(idx):
            st=states[local];fan=pred[local]
            ok,sm=e11.screen_fan_prediction(fan,p,st,xi,tau[i]/DAY_TO_S,r2teacher,adapter,screen)
            if ok:
                prof=adapter.project_fan_to_pollock_nodes(
                    tau_nodes=tau[i]/DAY_TO_S,state=st,fan_xi=xi,fan_sw=fan,swc=float(p["swc"])).astype(float)
                if not np.all(np.isfinite(parent_profiles[i])):raise GateError(f"parent_profile_nonfinite:{i}")
                accepted.append(int(i));child_profiles.append(prof)
            else:
                for reason in sm["failures"]:rejections[reason]=rejections.get(reason,0)+1
        accepted=np.asarray(accepted,dtype=np.int64);child_profiles=np.asarray(child_profiles,float)
        gate("incremental_Hybrid_accepts_present",accepted.size>0,int(accepted.size))
        parent_profiles_acc=parent_profiles[accepted]

        stage="parent_anchored_incremental_bridge"
        parent_model_sat,parent_model_mass,parent_model_src=b1.project_201_to_200_component_mass(
            physics,e37a,parent_profiles_acc,coeff,accepted)
        child_model_sat,child_model_mass,child_model_src=b1.project_201_to_200_component_mass(
            physics,e37a,child_profiles,coeff,accepted)
        parent_proj=np.sum(parent_model_mass,axis=1)-np.sum(parent_model_src,axis=1)
        child_proj=np.sum(child_model_mass,axis=1)-np.sum(child_model_src,axis=1)
        gate("parent_model_projection_conservative",float(np.max(np.abs(parent_proj)))<=1e-7,float(np.max(np.abs(parent_proj))))
        gate("child_model_projection_conservative",float(np.max(np.abs(child_proj)))<=1e-7,float(np.max(np.abs(child_proj))))

        delta_model=child_model_mass-parent_model_mass
        raw_candidate=old_mass[accepted]+delta_model
        corrected=np.empty_like(raw_candidate);corrected_sat=np.empty_like(raw_candidate)
        rows=[];closures=[];corr_rel=[];mass_rel=[];sat_rel=[];raw_neg=[];raw_excess=[];delta_rel=[]
        for local,sl in enumerate(accepted):
            raw=raw_candidate[local];cap=capacity[sl];tar=float(target[sl])
            raw_neg.append(max(0.0,-float(np.min(raw))))
            raw_excess.append(max(0.0,float(np.max(raw-cap))))
            m,lam,closure=a1.box_project(raw,tar,cap)
            ss=np.asarray(e37a.invert_cv_mass_to_saturation(physics,m,coeff[sl]),float)
            corrected[local]=m;corrected_sat[local]=ss
            rc=float(np.sum(np.abs(m-raw))/max(abs(tar),1e-30))
            mr=rel_l2(m,exact_mass[sl]);sr=rel_l2(ss,exact_sat[sl])
            dr=rel_l2(delta_model[local],exact_mass[sl]-old_mass[sl])
            closures.append(abs(closure));corr_rel.append(rc);mass_rel.append(mr);sat_rel.append(sr);delta_rel.append(dr)
            rows.append({
                "streamline_index":int(sl),
                "parent_total_mass_kg":float(np.sum(old_mass[sl])),
                "target_total_mass_kg":tar,
                "model_parent_total_mass_kg":float(np.sum(parent_model_mass[local])),
                "model_child_total_mass_kg":float(np.sum(child_model_mass[local])),
                "model_delta_total_mass_kg":float(np.sum(delta_model[local])),
                "physical_budget_delta_mass_kg":float(tar-np.sum(old_mass[sl])),
                "raw_parent_anchored_total_mass_kg":float(np.sum(raw)),
                "corrected_total_mass_kg":float(np.sum(m)),
                "budget_closure_residual_kg":float(closure),
                "mass_correction_relative_L1":rc,
                "model_delta_vs_exact_delta_relative_L2":dr,
                "corrected_vs_exact_mass_relative_L2":mr,
                "corrected_vs_exact_saturation_relative_L2":sr,
                "raw_negative_mass_violation_kg":raw_neg[-1],
                "raw_capacity_excess_kg":raw_excess[-1],
                "minimum_corrected_capacity_margin_kg":float(np.min(cap-m)),
                "lambda_shift_kg":float(lam),
            })

        gate("all_incremental_budget_projections_feasible",len(rows)==accepted.size,len(rows))
        gate("all_incremental_budget_closures_numerical",float(np.max(closures))<=1e-8,float(np.max(closures)))
        gate("all_corrected_incremental_capacity_safe",
             np.all(corrected>=-1e-10)&np.all(corrected<=capacity[accepted]+1e-8))

        baseline_mass_med=float(baseline["corrected_vs_exact_mass_relative_L2"]["median"])
        baseline_mass_p95=float(baseline["corrected_vs_exact_mass_relative_L2"]["p95"])
        baseline_sat_med=float(baseline["corrected_vs_exact_saturation_relative_L2"]["median"])
        baseline_sat_p95=float(baseline["corrected_vs_exact_saturation_relative_L2"]["p95"])
        current_mass=pct(mass_rel);current_sat=pct(sat_rel)
        improved={
            "mass_median":current_mass["median"]<baseline_mass_med,
            "mass_p95":current_mass["p95"]<baseline_mass_p95,
            "saturation_median":current_sat["median"]<baseline_sat_med,
            "saturation_p95":current_sat["p95"]<baseline_sat_p95,
        }
        all_improved=all(improved.values())

        stage="publication"
        gate("output_absent",not out.exists(),str(out));out.mkdir(parents=True)
        aggregate={
            "parent_day":PARENT_DAY,"dt_days":dt,"child_day":child_day,
            "joint_parent_child_learned_candidates":int(np.sum(joint_candidate)),
            "incremental_Hybrid10_screen_accept_count":int(accepted.size),
            "child_screen_rejection_reason_counts":rejections,
            "budget_closure_abs_kg":pct(closures),
            "mass_correction_relative_L1":pct(corr_rel),
            "model_delta_vs_exact_delta_relative_L2":pct(delta_rel),
            "corrected_vs_exact_mass_relative_L2":current_mass,
            "corrected_vs_exact_saturation_relative_L2":current_sat,
            "raw_negative_mass_violation_kg":pct(raw_neg),
            "raw_capacity_excess_kg":pct(raw_excess),
            "A2_absolute_bridge_baseline":{
                "corrected_vs_exact_mass_relative_L2":baseline["corrected_vs_exact_mass_relative_L2"],
                "corrected_vs_exact_saturation_relative_L2":baseline["corrected_vs_exact_saturation_relative_L2"],
                "mass_correction_relative_L1":baseline["mass_correction_relative_L1"],
            },
            "strict_improvement_vs_A2_absolute_bridge":improved,
            "all_four_median_p95_accuracy_metrics_improved":all_improved,
            "scientific_acceptance_threshold_defined":False,
        }
        classification=(
            "PARENT_ANCHORED_INCREMENTAL_HYBRID_BRIDGE_CONSERVATIVE_AND_STRICTLY_IMPROVES_A2_ABSOLUTE_REPRESENTATION_READY_FOR_MAPBACK_REVIEW"
            if all_improved else
            "PARENT_ANCHORED_INCREMENTAL_HYBRID_BRIDGE_CONSERVATIVE_BUT_ACCURACY_IMPROVEMENT_INCOMPLETE_MAPBACK_NOT_AUTHORIZED"
        )
        summary={
            "milestone":M,"status":PASS,"classification":classification,
            "parent_anchored_incremental_representation_tested":True,
            "Hybrid_absolute_parent_replacement_used":False,
            "real_recurrent_boundary_budget_used":True,
            "budget_uses_exact_interior_transport":False,
            "exact_E37A_child_used_as_benchmark_only":True,
            "incremental_Hybrid10_screen_accept_count":int(accepted.size),
            "all_incremental_budget_projections_feasible":True,
            "all_incremental_budget_closures_numerical":True,
            "all_four_accuracy_metrics_improved_vs_A2_absolute_bridge":all_improved,
            "grid_mapback_performed":False,
            "canonical_state_mutated":False,
            "new_scientific_threshold_defined":False,
            "Hybrid_canonical_state_mutation_authorized":False,
            "G4_A3_mapback_review_authorized":bool(all_improved),
            "integrated_GPU_runtime_authorized":False,
            "P4_authorized":False,
            "aggregate_metrics":aggregate,
        }
        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        (out/AGG).write_text(json.dumps(aggregate,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        write_csv(out/METRICS,rows)
        np.savez_compressed(out/ARRAYS,
            accepted_streamline_index=accepted,
            exact_parent_cv_mass_kg=old_mass[accepted],
            hybrid_parent_model_cv_mass_kg=parent_model_mass,
            hybrid_child_model_cv_mass_kg=child_model_mass,
            hybrid_model_delta_cv_mass_kg=delta_model,
            raw_parent_anchored_candidate_cv_mass_kg=raw_candidate,
            corrected_cv_mass_kg=corrected,
            corrected_cv_saturation=corrected_sat,
            exact_child_cv_mass_kg=exact_mass[accepted],
            exact_child_cv_saturation=exact_sat[accepted],
            target_total_mass_kg=target[accepted])
        write_csv(out/GATES,gates)
        write_csv(out/MANIFEST,[{"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size}
                                for p in sorted(out.iterdir()) if p.is_file() and p.name!=MANIFEST])

        print("="*190);print(M,"PASS")
        print("Incremental Hybrid accepts                   :",int(accepted.size))
        print("Median mass correction relative L1           :",float(np.median(corr_rel)))
        print("A2 absolute median mass relL2                :",baseline_mass_med)
        print("A2-R1 incremental median mass relL2          :",current_mass["median"])
        print("A2 absolute P95 mass relL2                   :",baseline_mass_p95)
        print("A2-R1 incremental P95 mass relL2             :",current_mass["p95"])
        print("A2 absolute median saturation relL2          :",baseline_sat_med)
        print("A2-R1 incremental median saturation relL2    :",current_sat["median"])
        print("All median/P95 accuracy metrics improved     :",all_improved)
        print("Grid mapback / canonical mutation            : False / False")
        print("G4-A3 mapback review authorized              :",bool(all_improved))
        print("="*190)
        return 0
    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps({
            "milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),"gates":gates,
            "grid_mapback_performed":False,"canonical_state_mutated":False,
            "G4_A3_mapback_review_authorized":False,
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
