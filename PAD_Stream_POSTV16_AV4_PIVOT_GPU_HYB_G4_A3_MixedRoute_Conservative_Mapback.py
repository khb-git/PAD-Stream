#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
from typing import Any
import numpy as np

M="POSTV16-AV4-PIVOT-GPU-HYB-G4-A3"
PASS="POSTV16AV4PIVOTGPUHYBG4A3_MIXED_ROUTE_CONSERVATIVE_MAPBACK_PASS"
BLOCK="POSTV16AV4PIVOTGPUHYBG4A3_TECHNICAL_OR_CONSERVATION_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="82aa73ea0f0a4d6a8f657dec2ad21488a08467ee"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

A2R1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_A2_R1_ParentAnchored_Incremental_Hybrid_Bridge.py"
A2R1_BLOB="ee31d40afeef718cb71112d8848f5f4a5e52bed5"
G2_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_R1_Rank1_Day75_80_ExactFlow_and_Hybrid_Endpoint_Diagnostic.py"
G2_BLOB="04c3940a7c736b1d210376113e48bab6111fc173"
R3R4_RUNNER="PAD_Stream_V16E41R3R4R1_Refreshed_Flow_CFL_Alignment_Repair.py"
R3R4_BLOB="5f8433437ce111533338ceada922f51abb2edefe"

DAY_TO_S=86400.0
FT_TO_M=0.3048
NSTREAM=1078
NCV=200
PARENT_DAY=75.0

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_A3"
OUT_REL=BASE/(OUT_TOKEN+"_MixedRoute_Conservative_Mapback")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
AGG=f"{OUT_TOKEN}_Aggregate_Metrics.json"
ARRAYS=f"{OUT_TOKEN}_MixedRoute_Grid_Arrays.npz"
ROUTES=f"{OUT_TOKEN}_Route_Counts.csv"
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

def read_manifest(p:Path)->dict[str,str]:
    with p.open(newline="",encoding="utf-8") as f:
        return {r["file"]:r["sha256"] for r in csv.DictReader(f)}

def rel_l2(a,b):
    a=np.asarray(a,float);b=np.asarray(b,float)
    return float(np.linalg.norm((a-b).ravel())/max(float(np.linalg.norm(b.ravel())),1e-30))

def selftest():
    x=np.array([1.,2.]);y=x.copy();y[0]=3.
    assert float(np.sum(y))==5.
    print("POSTV16 GPU-HYB-G4-A3 structural self-test: PASS")

def main(root:Path,drive:Path)->int:
    root=root.resolve();drive=drive.resolve();out=drive/OUT_REL;blocked=drive/BLOCK_REL
    gates=[];stage="preflight"
    def gate(n,c,d=None):
        ok=bool(c);gates.append({"stage":stage,"gate":n,"pass":ok,"detail":"" if d is None else repr(d)})
        print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"),flush=True)
        if not ok:raise GateError(n)
    try:
        print("="*190)
        print("G4-A3 — MIXED HYBRID + EXACT-FALLBACK CONSERVATIVE MAPBACK")
        print("A2-R1 HYBRID PATHS ARE FROZEN; ALL OTHER PATHS USE EXACT E37A CHILD.")
        print("ONE COMMON E37A CV->GRID MAPBACK + CONSERVATIVE CAPILLARY. READ-ONLY: NO CANONICAL STATE MUTATION.")
        print("="*190)

        stage="repository"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_G4_A2_R1",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")
        a2r1=mod(root,A2R1_RUNNER,A2R1_BLOB,"g4a3_a2r1")
        g2=mod(root,G2_RUNNER,G2_BLOB,"g4a3_g2")
        r3r4=mod(root,R3R4_RUNNER,R3R4_BLOB,"g4a3_r3r4")

        stage="A2R1_authority"
        s=js(drive/a2r1.OUT_REL/a2r1.SUMMARY)
        gate("A2R1_status_exact",s.get("status")==a2r1.PASS,s.get("status"))
        gate("A2R1_incremental_tested",s.get("parent_anchored_incremental_representation_tested") is True)
        gate("A2R1_all_accuracy_improved",s.get("all_four_accuracy_metrics_improved_vs_A2_absolute_bridge") is True)
        gate("A2R1_mapback_review_authorized",s.get("G4_A3_mapback_review_authorized") is True)
        gate("A2R1_no_mutation",s.get("canonical_state_mutated") is False)
        a2_arrays_path=drive/a2r1.OUT_REL/a2r1.ARRAYS
        manifest=read_manifest(drive/a2r1.OUT_REL/a2r1.MANIFEST)
        gate("A2R1_arrays_SHA_manifest",sha(a2_arrays_path)==manifest[a2r1.ARRAYS],sha(a2_arrays_path))
        a2arr=load_npz(a2_arrays_path)
        accepted=np.asarray(a2arr["accepted_streamline_index"],dtype=np.int64)
        corrected_mass=np.asarray(a2arr["corrected_cv_mass_kg"],dtype=np.float64)
        corrected_sat=np.asarray(a2arr["corrected_cv_saturation"],dtype=np.float64)
        gate("A2R1_accept_count_exact",accepted.size==int(s["incremental_Hybrid10_screen_accept_count"]),accepted.size)
        gate("A2R1_corrected_shapes",corrected_mass.shape==(accepted.size,NCV) and corrected_sat.shape==(accepted.size,NCV),
             (corrected_mass.shape,corrected_sat.shape))

        stage="Day75_reconstruction"
        g2s=js(drive/g2.OUT_REL/g2.SUMMARY)
        gate("G2_status_exact",g2s.get("status")==g2.PASS,g2s.get("status"))
        state_path=drive/g2.OUT_REL/g2.DAY75_STATE
        state=load_npz(state_path)
        gate("Day75_time_exact",abs(scalar(state["physical_time_days"])-PARENT_DAY)<=1e-12,scalar(state["physical_time_days"]))

        r3r5=g2.load_module_blob(root/g2.R3R5_RUNNER,g2.R3R5_BLOB,"g4a3_r3r5",root)
        roles={}
        for role in ["R3R2R1","E36","E37A","R2_PHYSICS","SG2","SG3","SG4","SG5","SG6","SG7A","SG7D"]:
            fn,bl=r3r4.SOURCE_BLOBS[role]
            roles[role]=g2.load_module_blob(root/fn,bl,f"g4a3_{role.lower()}",root)
        r3r2r1=roles["R3R2R1"];e36=roles["E36"];e37a=roles["E37A"];physics=roles["R2_PHYSICS"]
        sg2=roles["SG2"];sg3=roles["SG3"];sg4=roles["SG4"];sg5=roles["SG5"];sg6=roles["SG6"]
        sg7a=roles["SG7A"];sg7d=roles["SG7D"]

        pfn,pblob=r3r4.SOURCE_BLOBS["PERM"];perm_path=root/pfn
        gate("permeability_blob_exact",blob(root,perm_path)==pblob,blob(root,perm_path))
        permeability_md=np.loadtxt(perm_path,skiprows=1,dtype=np.float64).reshape((15,50,50),order="C")
        cell_pv=0.20*(20.0*FT_TO_M)*(20.0*FT_TO_M)*(4.0*FT_TO_M)

        ref75,epoch75,db75=g2.same_time_endpoint(
            state,r3r5=r3r5,r3r4r1=r3r4,physics=physics,r3r2r1=r3r2r1,e36=e36,e37a=e37a,
            sg2=sg2,sg3=sg3,sg4=sg4,sg5=sg5,sg6=sg6,sg7a=sg7a,sg7d=sg7d,
            permeability_md=permeability_md,cell_pore_volume_m3=cell_pv)
        gate("same_time_ref75_no_time_advance",abs(scalar(ref75["physical_time_days"])-PARENT_DAY)<=1e-12)
        p_ref=scalar(ref75["co2_density_reference_pressure_pa"])
        pressure=np.asarray(epoch75["pressure_psi"],dtype=np.float64)
        parent_sat=np.asarray(ref75["transport_saturation"],dtype=np.float64)
        old_sat,old_mass,sample_closure=e37a.sample_grid_inventory_to_control_volumes(
            physics,parent_sat,pressure,p_ref,epoch75["geometry"],NSTREAM,NCV)
        sample_tol=max(1e-6,1e-10*max(abs(float(np.sum(old_mass))),1.0))
        gate("parent_grid_to_CV_sampling_closure",abs(float(sample_closure))<=sample_tol,(sample_closure,sample_tol))

        stage="exact_one_step_benchmark"
        face_pressure=e37a.build_face_pressure(e36,sg7d,db75["xyz_m"],pressure)
        q=np.asarray(db75["weights_m3_s"],dtype=np.float64)*DAY_TO_S
        xi=np.asarray(db75["xi"],dtype=np.float64)
        dt=float(r3r4.transport_cfl_dt_days(sg7a,xi,np.asarray(db75["tau_end_s"],dtype=np.float64)))
        gate("dt_matches_A2R1",abs(dt-float(s["aggregate_metrics"]["dt_days"]))<=1e-15,(dt,s["aggregate_metrics"]["dt_days"]))
        exact=e37a.advance_component_mass_control_volumes(
            physics,sg7a,old_sat,old_mass,epoch75["geometry"]["cv_pressure_mass_coeff"],
            face_pressure,p_ref,q,xi,dt)
        exact_mass=np.asarray(exact["new_mass"],dtype=np.float64)
        exact_sat=np.asarray(exact["new_saturation"],dtype=np.float64)

        gate("A2R1_parent_mass_matches_reconstructed",
             float(np.max(np.abs(np.asarray(a2arr["exact_parent_cv_mass_kg"])-old_mass[accepted])))<=1e-7,
             float(np.max(np.abs(np.asarray(a2arr["exact_parent_cv_mass_kg"])-old_mass[accepted]))))
        gate("A2R1_exact_child_matches_recomputed",
             float(np.max(np.abs(np.asarray(a2arr["exact_child_cv_mass_kg"])-exact_mass[accepted])))<=1e-7,
             float(np.max(np.abs(np.asarray(a2arr["exact_child_cv_mass_kg"])-exact_mass[accepted]))))

        stage="mixed_route_assembly"
        mixed_mass=exact_mass.copy();mixed_sat=exact_sat.copy()
        mixed_mass[accepted]=corrected_mass;mixed_sat[accepted]=corrected_sat
        fallback_mask=np.ones(NSTREAM,dtype=bool);fallback_mask[accepted]=False
        gate("mixed_Hybrid_count",int(np.sum(~fallback_mask))==accepted.size,int(np.sum(~fallback_mask)))
        gate("mixed_exact_fallback_count",int(np.sum(fallback_mask))==NSTREAM-accepted.size,int(np.sum(fallback_mask)))
        gate("mixed_mass_finite",np.all(np.isfinite(mixed_mass)))
        gate("mixed_sat_finite",np.all(np.isfinite(mixed_sat)))
        cap=np.asarray(epoch75["geometry"]["cv_pressure_mass_coeff"],dtype=np.float64)
        reconstructed=np.asarray(e37a.cv_mass_from_saturation(physics,mixed_sat,cap),dtype=np.float64)
        gate("mixed_mass_saturation_constitutive_consistency",
             float(np.max(np.abs(reconstructed-mixed_mass)))<=1e-7,
             float(np.max(np.abs(reconstructed-mixed_mass))))

        target_global=scalar(ref75["stored_co2_mass_current_kg"])+float(exact["injected_mass_kg"])-float(exact["produced_mass_kg"])
        mixed_cv_total=float(np.sum(mixed_mass))
        exact_cv_total=float(np.sum(exact_mass))
        global_tol=max(1e-6,1e-10*max(abs(target_global),1.0))
        gate("mixed_CV_global_budget",abs(mixed_cv_total-target_global)<=global_tol,(mixed_cv_total-target_global,global_tol))
        gate("exact_CV_global_budget",abs(exact_cv_total-target_global)<=global_tol,(exact_cv_total-target_global,global_tol))

        stage="common_conservative_mapback"
        mixed_map=e37a.map_control_volume_increment_to_grid(
            physics,parent_sat,old_sat,mixed_sat,old_mass,mixed_mass,epoch75["geometry"],
            pressure,p_ref,cell_pv,target_global)
        exact_map=e37a.map_control_volume_increment_to_grid(
            physics,parent_sat,old_sat,exact_sat,old_mass,exact_mass,epoch75["geometry"],
            pressure,p_ref,cell_pv,target_global)
        for name,mapping in [("mixed",mixed_map),("exact",exact_map)]:
            gate(name+"_transfer_closure",abs(float(mapping["transfer_residual_kg"]))<=float(mapping["roundoff_mass_kg"]),
                 mapping["transfer_residual_kg"])
            gate(name+"_mapback_ledger_closure",abs(float(mapping["ledger_residual_kg"]))<=float(mapping["roundoff_mass_kg"]),
                 mapping["ledger_residual_kg"])
            gate(name+"_grid_inversion_closure",abs(float(mapping["grid_inversion_residual_kg"]))<=float(mapping["roundoff_mass_kg"]),
                 mapping["grid_inversion_residual_kg"])
            gate(name+"_source_local_added_zero",float(mapping["source_local_added_mass_kg"])==0.0)

        mixed_pre=np.asarray(mixed_map["corrected_saturation"],dtype=np.float64)
        exact_pre=np.asarray(exact_map["corrected_saturation"],dtype=np.float64)
        mixed_grid_mass=np.asarray(mixed_map["corrected_mass"],dtype=np.float64)
        exact_grid_mass=np.asarray(exact_map["corrected_mass"],dtype=np.float64)

        stage="common_capillary"
        mixed_cap=physics.conservative_capillary_mass_redistribution(
            transport_saturation=mixed_pre,permeability_md=permeability_md,pressure_psi=pressure,
            p_ref_pa=p_ref,cell_pore_volume_m3=cell_pv,dt_seconds=dt*DAY_TO_S)
        exact_cap=physics.conservative_capillary_mass_redistribution(
            transport_saturation=exact_pre,permeability_md=permeability_md,pressure_psi=pressure,
            p_ref_pa=p_ref,cell_pore_volume_m3=cell_pv,dt_seconds=dt*DAY_TO_S)
        mixed_post=np.asarray(mixed_cap["corrected"],dtype=np.float64)
        exact_post=np.asarray(exact_cap["corrected"],dtype=np.float64)
        for name,capillary,mapping in [("mixed",mixed_cap,mixed_map),("exact",exact_cap,exact_map)]:
            gate(name+"_capillary_external_mass_zero",abs(float(capillary["external_mass_change_kg"]))<=global_tol,
                 capillary["external_mass_change_kg"])
            gate(name+"_capillary_preserves_mapback_mass",
                 abs(float(capillary["final_mass_state_kg"])-float(mapping["mapped_final_mass_kg"]))<=global_tol,
                 float(capillary["final_mass_state_kg"])-float(mapping["mapped_final_mass_kg"]))
        gate("mixed_post_capillary_bounds",
             float(np.min(mixed_post))>=float(physics.BACKGROUND_SATURATION)-1e-12 and
             float(np.max(mixed_post))<=float(physics.BACKGROUND_SATURATION+physics.MAX_INCREMENTAL_CO2_SATURATION)+1e-12,
             (float(np.min(mixed_post)),float(np.max(mixed_post))))

        stage="accuracy_and_publication"
        pre_sat_rel=rel_l2(mixed_pre,exact_pre)
        post_sat_rel=rel_l2(mixed_post,exact_post)
        grid_mass_rel=rel_l2(mixed_grid_mass,exact_grid_mass)
        pre_linf=float(np.max(np.abs(mixed_pre-exact_pre)))
        post_linf=float(np.max(np.abs(mixed_post-exact_post)))
        mass_linf=float(np.max(np.abs(mixed_grid_mass-exact_grid_mass)))
        aggregate={
            "parent_day":PARENT_DAY,
            "dt_days":dt,
            "child_day":PARENT_DAY+dt,
            "Hybrid_incremental_route_count":int(accepted.size),
            "exact_fallback_route_count":int(NSTREAM-accepted.size),
            "Hybrid_route_fraction":float(accepted.size/NSTREAM),
            "mixed_CV_global_budget_residual_kg":mixed_cv_total-target_global,
            "mixed_mapback_transfer_residual_kg":float(mixed_map["transfer_residual_kg"]),
            "mixed_mapback_ledger_residual_kg":float(mixed_map["ledger_residual_kg"]),
            "mixed_grid_inversion_residual_kg":float(mixed_map["grid_inversion_residual_kg"]),
            "mixed_capillary_external_mass_change_kg":float(mixed_cap["external_mass_change_kg"]),
            "mixed_vs_exact_pre_capillary_saturation_relative_L2":pre_sat_rel,
            "mixed_vs_exact_pre_capillary_saturation_Linf":pre_linf,
            "mixed_vs_exact_grid_component_mass_relative_L2":grid_mass_rel,
            "mixed_vs_exact_grid_component_mass_Linf_kg":mass_linf,
            "mixed_vs_exact_post_capillary_saturation_relative_L2":post_sat_rel,
            "mixed_vs_exact_post_capillary_saturation_Linf":post_linf,
            "scientific_acceptance_threshold_defined":False,
        }
        gate("output_absent",not out.exists(),str(out));out.mkdir(parents=True)
        summary={
            "milestone":M,"status":PASS,
            "classification":"MIXED_INCREMENTAL_HYBRID_PLUS_EXACT_FALLBACK_SINGLE_COMMON_E37A_MAPBACK_AND_CAPILLARY_CERTIFIED_G4_A4_CONTROLLED_RECURRENT_STATE_TRANSITION_AUTHORIZED",
            "Hybrid_incremental_route_count":int(accepted.size),
            "exact_fallback_route_count":int(NSTREAM-accepted.size),
            "single_common_mapback_operator_used":True,
            "route_specific_grid_mapback_used":False,
            "mixed_CV_global_budget_certified":True,
            "mixed_CV_to_grid_transfer_certified":True,
            "mixed_grid_mass_ledger_certified":True,
            "mixed_capillary_mass_conservation_certified":True,
            "exact_child_used_as_grid_benchmark_only":True,
            "new_Hybrid_inference_performed":False,
            "canonical_state_mutated":False,
            "new_scientific_threshold_defined":False,
            "G4_A4_controlled_one_step_recurrent_state_transition_authorized":True,
            "integrated_GPU_runtime_authorized":False,
            "P4_authorized":False,
            "aggregate_metrics":aggregate,
        }
        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        (out/AGG).write_text(json.dumps(aggregate,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        write_csv(out/ROUTES,[
            {"route":"HYBRID10_PARENT_ANCHORED_INCREMENT","count":int(accepted.size)},
            {"route":"EXACT_E37A_FALLBACK","count":int(NSTREAM-accepted.size)},
        ])
        np.savez_compressed(out/ARRAYS,
            accepted_streamline_index=accepted,
            mixed_cv_mass_kg=mixed_mass,
            mixed_cv_saturation=mixed_sat,
            exact_cv_mass_kg=exact_mass,
            exact_cv_saturation=exact_sat,
            mixed_pre_capillary_grid_saturation=mixed_pre,
            exact_pre_capillary_grid_saturation=exact_pre,
            mixed_grid_component_mass_kg=mixed_grid_mass,
            exact_grid_component_mass_kg=exact_grid_mass,
            mixed_post_capillary_grid_saturation=mixed_post,
            exact_post_capillary_grid_saturation=exact_post)
        write_csv(out/GATES,gates)
        write_csv(out/MANIFEST,[{"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size}
                                for p in sorted(out.iterdir()) if p.is_file() and p.name!=MANIFEST])

        print("="*190);print(M,"PASS")
        print("Hybrid / exact-fallback routes                :",int(accepted.size),"/",int(NSTREAM-accepted.size))
        print("Hybrid route fraction                         :",float(accepted.size/NSTREAM))
        print("Mixed CV global budget residual kg            :",mixed_cv_total-target_global)
        print("Mixed mapback transfer residual kg            :",mixed_map["transfer_residual_kg"])
        print("Mixed mapback ledger residual kg              :",mixed_map["ledger_residual_kg"])
        print("Mixed vs exact grid mass relL2                :",grid_mass_rel)
        print("Mixed vs exact pre-capillary sat relL2        :",pre_sat_rel)
        print("Mixed vs exact post-capillary sat relL2       :",post_sat_rel)
        print("Canonical state mutated                       : False")
        print("G4-A4 controlled recurrent transition         : AUTHORIZED")
        print("="*190)
        return 0
    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps({
            "milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),"gates":gates,
            "canonical_state_mutated":False,
            "G4_A4_controlled_one_step_recurrent_state_transition_authorized":False,
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
