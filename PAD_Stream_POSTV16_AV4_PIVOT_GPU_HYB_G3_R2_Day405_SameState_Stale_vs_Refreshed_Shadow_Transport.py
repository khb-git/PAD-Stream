#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
from typing import Any
import numpy as np

M="POSTV16-AV4-PIVOT-GPU-HYB-G3-R2"
PASS="POSTV16AV4PIVOTGPUHYBG3R2_DAY405_SAME_STATE_STALE_VS_REFRESHED_SHADOW_TRANSPORT_PASS"
BLOCK="POSTV16AV4PIVOTGPUHYBG3R2_TECHNICAL_CONSERVATION_OR_SEMANTIC_COMPATIBILITY_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="824d7e88408c13878909414a54fdf2d49477c4be"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

A0_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_A0_Late_Day405_Shadow_Compatibility_and_Protocol_Freeze"
A0_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_A0_Summary.json"
A0_PROTOCOL="POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_A0_Late_Day405_Shadow_Protocol.json"
A0_STATUS="POSTV16AV4PIVOTGPUHYBG3R2A0_LATE_DAY405_SAME_STATE_SHADOW_COMPATIBILITY_PROTOCOL_FREEZE_PASS_NO_PHYSICS_EXECUTION"

D390_REL=BASE/"POSTV16_AV4_PIVOT_P3_R1_R7_R7_XY2_Day385_to_Day390_FifthObservation_Pilot_and_Exact_Flow_Diagnostic"
D390_STATE="POSTV16_AV4_PIVOT_P3_R1_R7_R7_Day0390_Accepted_Dense_State.npz"
D390_DIAG="POSTV16_AV4_PIVOT_P3_R1_R7_R7_Day0390_Exact_Flow_Diagnostic.npz"
D390_STATE_SHA="83e26d77f5f853412b817c37dcd4d3958ba4469bbd14c10a8467a256b52c33ee"
D390_DIAG_SHA="a5e2271830649b37e0de38459a9ead58fb79d4c20c185fee1d3390e9e749c9dc"

D400_REL=BASE/"POSTV16_AV4_PIVOT_P3_R1_R7_R9_XY2_Day395_to_Day400_SeventhObservation_Pilot_and_Exact_Flow_Diagnostic"
D400_STATE="POSTV16_AV4_PIVOT_P3_R1_R7_R9_Day0400_Accepted_Dense_State.npz"
D400_DIAG="POSTV16_AV4_PIVOT_P3_R1_R7_R9_Day0400_Exact_Flow_Diagnostic.npz"
D400_STATE_SHA="9630449981429d90f3265dad60875217873000061a294b2bf60bbe806cb5c5d4"
D400_DIAG_SHA="2e772ca70526a2c64bc0a84f3fbc42c2540593e6b7d79dc74787e33b52c0ac42"

D405_REL=BASE/"POSTV16_AV4_PIVOT_P3_R1_R7_R10_XY2_Day400_to_Day405_EighthObservation_Pilot_and_Exact_Flow_Diagnostic"
D405_STATE="POSTV16_AV4_PIVOT_P3_R1_R7_R10_Day0405_Accepted_Dense_State.npz"
D405_DIAG="POSTV16_AV4_PIVOT_P3_R1_R7_R10_Day0405_Exact_Flow_Diagnostic.npz"
D405_STATE_SHA="dbe07ff7e33587f65b7c3ff02a4755e739975715cf003d42541070dc084d2077"
D405_DIAG_SHA="a567f4f560fcc56f1a26edfa4a4e6747a2a6d42e93fd9c9ce0c7cd87781fdafa"

R3R4R1=("PAD_Stream_V16E41R3R4R1_Refreshed_Flow_CFL_Alignment_Repair.py","5f8433437ce111533338ceada922f51abb2edefe")
E37A=("PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py","0bbf98ed89cee9128ef1d313c321f9a401b4e9f0")

DAY_TO_S=86400.0
FT_TO_M=0.3048
BACKGROUND=0.20
MAX_SAT=0.80

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G3_R2"
OUT_REL=BASE/(OUT_TOKEN+"_Day405_SameState_Stale_vs_Refreshed_Shadow_Transport")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
RESULTS=f"{OUT_TOKEN}_Branch_Results.csv"
COMPARE=f"{OUT_TOKEN}_Causal_Comparison_vs_Refreshed.csv"
PRODUCERS=f"{OUT_TOKEN}_Producer_Results.csv"
SEMANTICS=f"{OUT_TOKEN}_Late_Mass_Semantic_Compatibility.csv"
GATES=f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"
REF_CHILD=f"{OUT_TOKEN}_REFRESHED_0D_Shadow_Child.npz"
S5_CHILD=f"{OUT_TOKEN}_STALE_5D_Shadow_Child.npz"
S15_CHILD=f"{OUT_TOKEN}_STALE_15D_Shadow_Child.npz"

class GateError(RuntimeError): pass

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""): h.update(c)
    return h.hexdigest()

def gt(root:Path,*a:str)->str:
    return subprocess.check_output(["git","-C",str(root),*a],text=True).strip()

def module(root:Path,spec:tuple[str,str],name:str):
    fn,expected=spec;p=root/fn
    if not p.is_file(): raise GateError(f"missing_source:{fn}")
    actual=gt(root,"hash-object",str(p))
    if actual!=expected: raise GateError(f"source_blob:{fn}:{actual}:{expected}")
    s=importlib.util.spec_from_file_location(name,p)
    if s is None or s.loader is None: raise GateError(f"cannot_import:{fn}")
    m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m

def js(p:Path): return json.loads(p.read_text(encoding="utf-8"))

def load_npz(p:Path)->dict[str,np.ndarray]:
    with np.load(p,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}

def scalar(v:Any)->float:return float(np.asarray(v).reshape(()))

def write_csv(p:Path,rows:list[dict[str,Any]]):
    if not rows:p.write_text("",encoding="utf-8");return
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields:fields.append(k)
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows)

def rel_l2(a,b):
    aa=np.asarray(a,dtype=np.float64);bb=np.asarray(b,dtype=np.float64)
    return float(np.linalg.norm((aa-bb).ravel())/max(float(np.linalg.norm(bb.ravel())),1e-30))

def late_diag(p:Path):
    with np.load(p,allow_pickle=False) as z:
        needed=["diagnostic_day","pressure_psi","streamline_xyz_m","streamline_tof_s",
                "streamline_weight_m3_s","tau_end_s","producer_labels","xi"]
        for k in needed:
            if k not in z.files: raise GateError(f"diag_missing:{p.name}:{k}")
        return {
            "day":float(np.asarray(z["diagnostic_day"]).reshape(())),
            "pressure":np.asarray(z["pressure_psi"],dtype=np.float64),
            "xyz_m":np.asarray(z["streamline_xyz_m"],dtype=np.float64),
            "tau_s":np.asarray(z["streamline_tof_s"],dtype=np.float64),
            "tau_end_s":np.asarray(z["tau_end_s"],dtype=np.float64),
            "weights_m3_s":np.asarray(z["streamline_weight_m3_s"],dtype=np.float64),
            "producer":np.asarray(z["producer_labels"]).astype("U64"),
            "xi":np.asarray(z["xi"],dtype=np.float64),
        }

def semantic_audit(day,state,diag,*,physics,r3r4r1,pv):
    mass=np.asarray(state["cartesian_component_mass_kg"],dtype=np.float64)
    sat=np.asarray(state["cartesian_saturation"],dtype=np.float64)
    pref=scalar(state["reference_gas_pressure_pa"])
    rec=r3r4r1.parent_cellwise_component_mass(physics,sat,diag["pressure"],pref,pv)
    diff=rec-mass
    rel=rel_l2(rec,mass)
    linf=float(np.max(np.abs(diff)))
    g=float(np.sum(diff))
    scale=max(float(np.max(np.abs(mass))),1.0)
    cell_tol=max(1e-6,1e-10*scale)
    total_tol=max(1e-6,1e-10*max(float(np.sum(np.abs(mass))),1.0))
    if linf>cell_tol or abs(g)>total_tol:
        raise GateError(f"Day{day}:late_mass_semantic_mismatch:linf={linf}:cell_tol={cell_tol}:global={g}:global_tol={total_tol}")
    return {"day":day,"component_mass_relative_L2":rel,"component_mass_Linf_kg":linf,
            "component_mass_global_difference_kg":g,"cell_tolerance_kg":cell_tol,
            "global_tolerance_kg":total_tol,"modern_mass_operator_compatible":True}

def build_branch(name,stale_days,diag,*,parent_mass,pref,pv,r3r4r1,e37a,physics,e36,sg7a,sg7d):
    pressure=diag["pressure"]
    parent_sg=np.asarray(physics._invert_incremental_sg_from_mass(parent_mass,pressure,pref,pv),dtype=np.float64)
    parent_sat=BACKGROUND+parent_sg
    reconstructed=r3r4r1.parent_cellwise_component_mass(physics,parent_sat,pressure,pref,pv)
    max_mass_err=float(np.max(np.abs(reconstructed-parent_mass)))
    global_mass_err=float(np.sum(reconstructed)-np.sum(parent_mass))
    tol=max(1e-6,1e-10*max(float(np.max(np.abs(parent_mass))),1.0))
    if max_mass_err>tol: raise GateError(f"{name}:parent_mass_inversion:{max_mass_err}:{tol}")
    if float(np.min(parent_sat))<BACKGROUND-1e-12 or float(np.max(parent_sat))>MAX_SAT+1e-12:
        raise GateError(f"{name}:parent_sat_bounds:{float(np.min(parent_sat))}:{float(np.max(parent_sat))}")

    xyz=diag["xyz_m"];tau_s=diag["tau_s"];tau_end=diag["tau_end_s"]
    weights_day=diag["weights_m3_s"]*DAY_TO_S;xi=diag["xi"]
    nstream=int(xyz.shape[0]);nfaces=int(xi.shape[0]);ncv=nfaces-1
    if xyz.shape!=(nstream,nfaces,3) or tau_s.shape!=(nstream,nfaces):
        raise GateError(f"{name}:stream_shape")
    operator=sg7d.build_subsegment_operator(xyz,tau_s/DAY_TO_S,weights_day)
    geometry=e37a.build_control_volume_geometry(physics,operator,pressure,pref,nstream,ncv)
    face_pressure=e37a.build_face_pressure(e36,sg7d,xyz,pressure)
    cfl=float(r3r4r1.transport_cfl_dt_days(sg7a,xi,tau_end))
    if not np.isfinite(cfl) or cfl<=0: raise GateError(f"{name}:cfl:{cfl}")
    return {"name":name,"stale_days":float(stale_days),"diag":diag,"pressure":pressure,
            "parent_sat":parent_sat,"parent_mass_reconstruction_max_abs_kg":max_mass_err,
            "parent_mass_reconstruction_global_kg":global_mass_err,"geometry":geometry,
            "face_pressure":face_pressure,"weights_day":weights_day,"xi":xi,
            "nstream":nstream,"nfaces":nfaces,"ncv":ncv,"cfl_days":cfl}

def shadow_step(branch,dt,*,parent_mass,parent_total,pref,pv,perm,r3r4r1,e37a,physics,sg7a):
    old_sat,old_mass,sample_closure=e37a.sample_grid_inventory_to_control_volumes(
        physics,branch["parent_sat"],branch["pressure"],pref,branch["geometry"],branch["nstream"],branch["ncv"])
    sample_tol=max(1e-6,1e-10*max(abs(float(np.sum(old_mass))),1.0))
    if abs(sample_closure)>sample_tol:
        raise GateError(f"{branch['name']}:sampling_closure:{sample_closure}:{sample_tol}")

    tr=e37a.advance_component_mass_control_volumes(
        physics,sg7a,old_sat,old_mass,branch["geometry"]["cv_pressure_mass_coeff"],
        branch["face_pressure"],pref,branch["weights_day"],branch["xi"],dt)

    injected=float(tr["injected_mass_kg"]);produced=float(tr["produced_mass_kg"])
    target=parent_total+injected-produced

    pf=r3r4r1.preflight_mapback_capacity(
        physics=physics,parent_saturation=branch["parent_sat"],parent_mass=parent_mass,
        old_cv_saturation=old_sat,new_cv_saturation=tr["new_saturation"],
        geometry=branch["geometry"],pressure_psi=branch["pressure"],p_ref_gas_pa=pref,
        cell_pore_volume_m3=pv)
    if int(pf["overcapacity_cell_count"])!=0:
        raise GateError(f"{branch['name']}:common_dt_capacity_failure:{pf['overcapacity_cell_count']}:{pf['max_capacity_excess_kg']}")

    mp=e37a.map_control_volume_increment_to_grid(
        physics,branch["parent_sat"],old_sat,tr["new_saturation"],old_mass,tr["new_mass"],
        branch["geometry"],branch["pressure"],pref,pv,target)

    cap=physics.conservative_capillary_mass_redistribution(
        transport_saturation=np.asarray(mp["corrected_saturation"],dtype=np.float64),
        permeability_md=perm,pressure_psi=branch["pressure"],p_ref_pa=pref,
        cell_pore_volume_m3=pv,dt_seconds=dt*DAY_TO_S)
    child_sat=np.asarray(cap["corrected"],dtype=np.float64)
    child_mass=r3r4r1.parent_cellwise_component_mass(physics,child_sat,branch["pressure"],pref,pv)
    final_total=float(np.sum(child_mass))
    closure=final_total-parent_total-injected+produced
    closure_tol=max(1e-6,1e-10*max(abs(target),1.0))
    if abs(closure)>closure_tol:
        raise GateError(f"{branch['name']}:child_mass_closure:{closure}:{closure_tol}")
    if abs(float(cap["external_mass_change_kg"]))>closure_tol:
        raise GateError(f"{branch['name']}:capillary_external_mass:{cap['external_mass_change_kg']}")

    prod_rows,cut=e37a.producer_rows_from_flux(
        branch["diag"]["producer"],branch["weights_day"],tr["outlet_fractional_flow"],
        tr["face_mass_flux_kg_day"][:,-1],dt)

    return {"child_sat":child_sat,"child_mass":child_mass,"final_total":final_total,
            "injected":injected,"produced":produced,"cut":float(cut),
            "mapback_ledger":float(mp["ledger_residual_kg"]),
            "mapback_transfer":float(mp["transfer_residual_kg"]),
            "capacity_margin":float(pf["minimum_capacity_margin_kg"]),
            "sample_closure":float(sample_closure),
            "transport_closure":float(tr["mass_residual_kg"]),
            "capillary_external":float(cap["external_mass_change_kg"]),
            "producer_rows":prod_rows}

def selftest():
    assert [405-405,405-400,405-390]==[0,5,15]
    a=np.array([1.,2.,3.]);assert rel_l2(a,a)==0.0
    print("POSTV16 GPU-HYB-G3-R2 structural self-test: PASS")

def main(root:Path,drive:Path)->int:
    root=root.resolve();drive=drive.resolve();out=drive/OUT_REL;blocked=drive/BLOCK_REL
    gates=[];stage="preflight"
    def gate(n,c,d=None):
        ok=bool(c);gates.append({"stage":stage,"gate":n,"pass":ok,"detail":"" if d is None else repr(d)})
        print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"),flush=True)
        if not ok:raise GateError(n)
    try:
        print("="*190)
        print("G3-R2 — DAY405 SAME-STATE STALE-vs-REFRESHED SHADOW TRANSPORT")
        print("CANONICAL LATE TRAJECTORY IMMUTABLE. EXACT CONSERVATIVE TRANSPORT ONLY.")
        print("="*190)

        stage="repository"
        gate("branch",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_G3_R2_A0",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("clean",gt(root,"status","--porcelain")=="")

        stage="protocol_authority"
        a0=js(drive/A0_REL/A0_SUM);proto=js(drive/A0_REL/A0_PROTOCOL)
        gate("A0_status",a0.get("status")==A0_STATUS,a0.get("status"))
        gate("A0_direct_compatibility",a0.get("direct_modern_E37A_shadow_compatibility") is True)
        gate("A0_no_bridge",a0.get("bridge_execution_required_before_shadow") is False)
        gate("A0_G3_R2_authorized",a0.get("G3_R2_late_Day405_shadow_execution_authorized") is True)
        gate("A0_no_cadence_selection",a0.get("production_pressure_refresh_cadence_selected") is False)
        gate("protocol_no_science_tolerance",proto.get("scientific_tolerance_defined") is False)

        r3r4r1=module(root,R3R4R1,"g3r2_r3r4r1")
        e37a=module(root,E37A,"g3r2_e37a")
        role={}
        for key in ["E36","R2_PHYSICS","SG7A","SG7D"]:
            fn,b=r3r4r1.SOURCE_BLOBS[key]
            role[key]=module(root,(fn,b),"g3r2_"+key.lower())
        e36=role["E36"];physics=role["R2_PHYSICS"];sg7a=role["SG7A"];sg7d=role["SG7D"]
        pfn,pblob=r3r4r1.SOURCE_BLOBS["PERM"];pp=root/pfn
        gate("perm_blob_exact",gt(root,"hash-object",str(pp))==pblob,gt(root,"hash-object",str(pp)))

        dx,dy,dz=20*FT_TO_M,20*FT_TO_M,4*FT_TO_M
        pv=0.20*dx*dy*dz
        perm=np.loadtxt(pp,skiprows=1,dtype=np.float64).reshape((15,50,50),order="C")

        stage="late_semantic_compatibility"
        specs=[
            (390,drive/D390_REL/D390_STATE,drive/D390_REL/D390_DIAG,D390_STATE_SHA,D390_DIAG_SHA),
            (400,drive/D400_REL/D400_STATE,drive/D400_REL/D400_DIAG,D400_STATE_SHA,D400_DIAG_SHA),
            (405,drive/D405_REL/D405_STATE,drive/D405_REL/D405_DIAG,D405_STATE_SHA,D405_DIAG_SHA)]
        states={};diags={};semantic_rows=[]
        for day,sp,dp,ssha,dsha in specs:
            gate(f"Day{day}_state_SHA",sha(sp)==ssha,sha(sp))
            gate(f"Day{day}_diag_SHA",sha(dp)==dsha,sha(dp))
            st=load_npz(sp);dg=late_diag(dp)
            gate(f"Day{day}_state_day",scalar(st["physical_day"])==float(day),scalar(st["physical_day"]))
            gate(f"Day{day}_diag_day",dg["day"]==float(day),dg["day"])
            row=semantic_audit(day,st,dg,physics=physics,r3r4r1=r3r4r1,pv=pv)
            semantic_rows.append(row);states[day]=st;diags[day]=dg
            gate(f"Day{day}_modern_mass_semantics",row["modern_mass_operator_compatible"] is True,row)

        stage="parent_state"
        parent_state=states[405]
        parent_mass=np.asarray(parent_state["cartesian_component_mass_kg"],dtype=np.float64)
        parent_total=float(np.sum(parent_mass))
        pref=scalar(parent_state["reference_gas_pressure_pa"])
        gate("parent_mass_positive",parent_total>0,parent_total)
        gate("parent_mass_finite",np.all(np.isfinite(parent_mass)))
        gate("parent_pref_positive",np.isfinite(pref) and pref>0,pref)

        stage="frozen_flow_branches"
        b0=build_branch("REFRESHED_0D",0,diags[405],parent_mass=parent_mass,pref=pref,pv=pv,
                        r3r4r1=r3r4r1,e37a=e37a,physics=physics,e36=e36,sg7a=sg7a,sg7d=sg7d)
        b5=build_branch("STALE_5D",5,diags[400],parent_mass=parent_mass,pref=pref,pv=pv,
                        r3r4r1=r3r4r1,e37a=e37a,physics=physics,e36=e36,sg7a=sg7a,sg7d=sg7d)
        b15=build_branch("STALE_15D",15,diags[390],parent_mass=parent_mass,pref=pref,pv=pv,
                         r3r4r1=r3r4r1,e37a=e37a,physics=physics,e36=e36,sg7a=sg7a,sg7d=sg7d)
        branches=[b0,b5,b15]
        gate("all_streamline_counts_equal",len({b["nstream"] for b in branches})==1,
             {b["name"]:b["nstream"] for b in branches})
        gate("all_faces_201",all(b["nfaces"]==201 for b in branches),[b["nfaces"] for b in branches])
        common_dt=min(b["cfl_days"] for b in branches)
        gate("common_dt_positive",np.isfinite(common_dt) and common_dt>0,common_dt)
        gate("common_dt_within_all_CFL",all(common_dt<=b["cfl_days"]+1e-15 for b in branches),
             {b["name"]:b["cfl_days"] for b in branches})

        # Refreshed branch mass inversion should reproduce the archived Day405 saturation.
        archived_sat=np.asarray(parent_state["cartesian_saturation"],dtype=np.float64)
        sat_diff=np.asarray(b0["parent_sat"])-archived_sat
        gate("refreshed_Day405_mass_inversion_reproduces_archived_saturation",
             float(np.max(np.abs(sat_diff)))<=1e-9,
             float(np.max(np.abs(sat_diff))))

        stage="shadow_transport"
        results={}
        for b in branches:
            results[b["name"]]=shadow_step(
                b,common_dt,parent_mass=parent_mass,parent_total=parent_total,pref=pref,pv=pv,perm=perm,
                r3r4r1=r3r4r1,e37a=e37a,physics=physics,sg7a=sg7a)

        injected=[results[b["name"]]["injected"] for b in branches]
        inj_ref=max(abs(injected[0]),1.0)
        inj_tol=max(1e-8,1e-10*inj_ref)
        gate("same_injected_component_mass_all_branches",
             max(injected)-min(injected)<=inj_tol,
             {"values":injected,"tolerance_kg":inj_tol})

        ref=results["REFRESHED_0D"]
        comparisons=[]
        for name in ["STALE_5D","STALE_15D"]:
            x=results[name]
            comparisons.append({
                "branch":name,
                "staleness_days":5 if name=="STALE_5D" else 15,
                "child_cellwise_CO2_mass_relative_L2_vs_refreshed":rel_l2(x["child_mass"],ref["child_mass"]),
                "child_cellwise_CO2_mass_Linf_kg_vs_refreshed":float(np.max(np.abs(x["child_mass"]-ref["child_mass"]))),
                "child_saturation_relative_L2_vs_refreshed":rel_l2(x["child_sat"],ref["child_sat"]),
                "child_saturation_Linf_vs_refreshed":float(np.max(np.abs(x["child_sat"]-ref["child_sat"]))),
                "produced_CO2_mass_difference_kg_vs_refreshed":float(x["produced"]-ref["produced"]),
                "produced_CO2_mass_abs_difference_kg_vs_refreshed":float(abs(x["produced"]-ref["produced"])),
                "producer_CO2_gas_cut_difference_vs_refreshed":float(x["cut"]-ref["cut"]),
                "producer_CO2_gas_cut_abs_difference_vs_refreshed":float(abs(x["cut"]-ref["cut"])),
                "final_total_stored_mass_difference_kg_vs_refreshed":float(x["final_total"]-ref["final_total"]),
            })

        stage="publication"
        gate("output_absent",not out.exists(),str(out));out.mkdir(parents=True)
        branch_rows=[];producer_rows=[]
        for b in branches:
            x=results[b["name"]]
            branch_rows.append({
                "branch":b["name"],"staleness_days":b["stale_days"],
                "branch_CFL_dt_days":b["cfl_days"],"common_shadow_dt_days":common_dt,
                "parent_mass_reconstruction_max_abs_kg":b["parent_mass_reconstruction_max_abs_kg"],
                "parent_mass_reconstruction_global_kg":b["parent_mass_reconstruction_global_kg"],
                "injected_CO2_mass_kg":x["injected"],"produced_CO2_mass_kg":x["produced"],
                "producer_CO2_gas_cut":x["cut"],"final_stored_CO2_mass_kg":x["final_total"],
                "sample_closure_kg":x["sample_closure"],"transport_closure_kg":x["transport_closure"],
                "mapback_transfer_residual_kg":x["mapback_transfer"],
                "mapback_ledger_residual_kg":x["mapback_ledger"],
                "capillary_external_mass_change_kg":x["capillary_external"],
                "minimum_capacity_margin_kg":x["capacity_margin"]})
            for pr in x["producer_rows"]:
                producer_rows.append({"branch":b["name"],"staleness_days":b["stale_days"],**pr})

        write_csv(out/SEMANTICS,semantic_rows)
        write_csv(out/RESULTS,branch_rows);write_csv(out/COMPARE,comparisons);write_csv(out/PRODUCERS,producer_rows)

        child_map={"REFRESHED_0D":REF_CHILD,"STALE_5D":S5_CHILD,"STALE_15D":S15_CHILD}
        for b in branches:
            x=results[b["name"]]
            np.savez_compressed(out/child_map[b["name"]],
                branch=np.asarray(b["name"]),staleness_days=np.asarray(b["stale_days"]),
                common_shadow_dt_days=np.asarray(common_dt),pressure_psi=b["pressure"],
                parent_saturation_mass_consistent=b["parent_sat"],
                child_saturation=x["child_sat"],child_cellwise_CO2_mass_kg=x["child_mass"])

        c5=next(x for x in comparisons if x["branch"]=="STALE_5D")
        c15=next(x for x in comparisons if x["branch"]=="STALE_15D")
        summary={
            "milestone":M,"status":PASS,
            "classification":"DAY405_SAME_STATE_0D_5D_15D_STALE_FLOW_CAUSAL_SHADOW_EFFECT_MEASURED_NO_CADENCE_SELECTION",
            "parent_day":405.0,"parent_state_sha256":D405_STATE_SHA,
            "parent_stored_CO2_mass_kg":parent_total,
            "common_shadow_dt_days":common_dt,
            "branch_CFL_dt_days":{b["name"]:b["cfl_days"] for b in branches},
            "late_mass_semantic_compatibility_verified":True,
            "same_injected_component_mass_all_branches":True,
            "STALE_5D_effect_vs_refreshed":c5,
            "STALE_15D_effect_vs_refreshed":c15,
            "all_branches_component_mass_conservative":True,
            "all_branches_capacity_safe_at_common_dt":True,
            "canonical_trajectory_mutated":False,
            "Hybrid_recurrent_state_mutation_performed":False,
            "scientific_tolerance_defined":False,
            "production_pressure_refresh_cadence_selected":False,
            "G3_R3_early_late_causal_cadence_decision_freeze_authorized":True,
            "P4_authorized":False}
        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        write_csv(out/GATES,gates)
        manifest=[{"file":q.name,"sha256":sha(q),"bytes":q.stat().st_size}
                  for q in sorted(out.iterdir()) if q.is_file() and q.name!=MANIFEST]
        write_csv(out/MANIFEST,manifest)

        print("="*190);print(M,"PASS")
        print("Parent day                                    : 405")
        print("Common shadow dt days                         :",common_dt)
        print("Branch CFL days                               :",{b["name"]:b["cfl_days"] for b in branches})
        print("Late mass semantics compatible                : True")
        print("Same injected component mass all branches     : True")
        print("5d stale child mass relL2 vs refreshed        :",c5["child_cellwise_CO2_mass_relative_L2_vs_refreshed"])
        print("15d stale child mass relL2 vs refreshed       :",c15["child_cellwise_CO2_mass_relative_L2_vs_refreshed"])
        print("5d stale child saturation Linf vs refreshed   :",c5["child_saturation_Linf_vs_refreshed"])
        print("15d stale child saturation Linf vs refreshed  :",c15["child_saturation_Linf_vs_refreshed"])
        print("5d produced mass abs diff kg                  :",c5["produced_CO2_mass_abs_difference_kg_vs_refreshed"])
        print("15d produced mass abs diff kg                 :",c15["produced_CO2_mass_abs_difference_kg_vs_refreshed"])
        print("Canonical trajectory mutated                  : False")
        print("Production cadence selected                   : False")
        print("G3-R3 early+late decision freeze authorized   : True")
        print("P4 authorized                                 : False")
        print("="*190)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps({
            "milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),"gates":gates,
            "canonical_trajectory_mutated":False,
            "production_pressure_refresh_cadence_selected":False,
            "G3_R3_early_late_causal_cadence_decision_freeze_authorized":False,
            "P4_authorized":False},indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(M,"BLOCK");print("Stage:",stage);print("Exception:",repr(exc));return 2

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",type=Path,default=Path("."))
    ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test:selftest();raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))
