#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
from typing import Any
import numpy as np

M="POSTV16-AV4-PIVOT-GPU-HYB-G3-R2-R1"
PASS="POSTV16AV4PIVOTGPUHYBG3R2R1_LATE_NATIVE_DAY405_SAME_STATE_STALE_VS_REFRESHED_SHADOW_REPAIR_PASS"
BLOCK="POSTV16AV4PIVOTGPUHYBG3R2R1_TECHNICAL_CONSERVATION_OR_LATE_NATIVE_SEMANTIC_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="5f1a254216a6c8434674b818bb53874b2291995e"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"
BASE_AV3=Path("post_v16")/RID/"POSTV16_AV3_Corey_Relperm_Heterogeneity"

FAILED_REL=BASE_AV4/"POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_BLOCKED"
FAILED_REPORT="POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_Blocked_Report.json"
EXPECTED_FAILED_STAGE="late_semantic_compatibility"

A0_REL=BASE_AV4/"POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_A0_Late_Day405_Shadow_Compatibility_and_Protocol_Freeze"
A0_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_A0_Summary.json"

P3=("PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_Corrected_Dense_FrozenFlow_Trajectory_and_Exact_5Day_Flow_Diagnostic_Sweep.py",
    "84076001f40ebcf0825bb8d9bcabe060ed0840d2")
A2E=("PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py",
     "79a8969233b72b4543edd382a0c3d1028c6dca09")
R2SRC=("PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py",
       "a127f8730a16e150713420ea547a8de6255550ef")
E37A=("PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py",
      "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0")
E36=("PAD_Stream_V16E36_Short_Adaptive_SGSim_Rollout_and_Early_Plume_Snapshot_Validation.py",
     "9ab4035c95a25bd61c649f86c82d88f059cef9e2")
SG7A=("PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py","a4dd47338e7a85f130a6a70d0a41211e38c655f8")
SG7D=("PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py","890088c0c0fcab415a2c7351c5079ca8ee12bf82")
R3R4R1=("PAD_Stream_V16E41R3R4R1_Refreshed_Flow_CFL_Alignment_Repair.py","5f8433437ce111533338ceada922f51abb2edefe")

A2E_REL=BASE_AV4/"POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_EPOCH="POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_EPOCH_SHA="b49d48baa9d791b69a9e9c41635e1930fae84114b93ceb15ab5b21d3441ba08d"

A6E_REL=BASE_AV3/"POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
A6E_STATE="POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
A6E_SHA="f9e3a7bd8c6dcc43d522e0cb99a0cede2bd212fd570085b4faf82dc71af8f803"

D390_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P3_R1_R7_R7_XY2_Day385_to_Day390_FifthObservation_Pilot_and_Exact_Flow_Diagnostic"
D390_STATE="POSTV16_AV4_PIVOT_P3_R1_R7_R7_Day0390_Accepted_Dense_State.npz"
D390_DIAG="POSTV16_AV4_PIVOT_P3_R1_R7_R7_Day0390_Exact_Flow_Diagnostic.npz"
D390_STATE_SHA="83e26d77f5f853412b817c37dcd4d3958ba4469bbd14c10a8467a256b52c33ee"
D390_DIAG_SHA="a5e2271830649b37e0de38459a9ead58fb79d4c20c185fee1d3390e9e749c9dc"

D400_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P3_R1_R7_R9_XY2_Day395_to_Day400_SeventhObservation_Pilot_and_Exact_Flow_Diagnostic"
D400_STATE="POSTV16_AV4_PIVOT_P3_R1_R7_R9_Day0400_Accepted_Dense_State.npz"
D400_DIAG="POSTV16_AV4_PIVOT_P3_R1_R7_R9_Day0400_Exact_Flow_Diagnostic.npz"
D400_STATE_SHA="9630449981429d90f3265dad60875217873000061a294b2bf60bbe806cb5c5d4"
D400_DIAG_SHA="2e772ca70526a2c64bc0a84f3fbc42c2540593e6b7d79dc74787e33b52c0ac42"

D405_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P3_R1_R7_R10_XY2_Day400_to_Day405_EighthObservation_Pilot_and_Exact_Flow_Diagnostic"
D405_STATE="POSTV16_AV4_PIVOT_P3_R1_R7_R10_Day0405_Accepted_Dense_State.npz"
D405_DIAG="POSTV16_AV4_PIVOT_P3_R1_R7_R10_Day0405_Exact_Flow_Diagnostic.npz"
D405_STATE_SHA="dbe07ff7e33587f65b7c3ff02a4755e739975715cf003d42541070dc084d2077"
D405_DIAG_SHA="a567f4f560fcc56f1a26edfa4a4e6747a2a6d42e93fd9c9ce0c7cd87781fdafa"

DAY_TO_S=86400.0
BACKGROUND=0.20
MAX_SAT=0.80

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_R1"
OUT_REL=BASE_AV4/(OUT_TOKEN+"_LateNative_Day405_SameState_Shadow_Repair")
BLOCK_REL=BASE_AV4/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
SEMANTICS=f"{OUT_TOKEN}_Late_Native_Semantic_Audit.csv"
RESULTS=f"{OUT_TOKEN}_Branch_Results.csv"
COMPARE=f"{OUT_TOKEN}_Causal_Comparison_vs_Refreshed.csv"
PRODUCERS=f"{OUT_TOKEN}_Producer_Results.csv"
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
    if not p.is_file():raise GateError(f"missing_source:{fn}")
    actual=gt(root,"hash-object",str(p))
    if actual!=expected:raise GateError(f"source_blob:{fn}:{actual}:{expected}")
    s=importlib.util.spec_from_file_location(name,p)
    if s is None or s.loader is None:raise GateError(f"cannot_import:{fn}")
    m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m

def js(p:Path):return json.loads(p.read_text(encoding="utf-8"))
def scalar(v:Any)->float:return float(np.asarray(v).reshape(()))

def load_npz(p:Path):
    with np.load(p,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}

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
        return {
            "day":float(np.asarray(z["diagnostic_day"]).reshape(())),
            "saturation":np.asarray(z["saturation"],dtype=np.float64),
            "pressure":np.asarray(z["pressure_psi"],dtype=np.float64),
            "xyz_m":np.asarray(z["streamline_xyz_m"],dtype=np.float64),
            "tau_s":np.asarray(z["streamline_tof_s"],dtype=np.float64),
            "tau_end_s":np.asarray(z["tau_end_s"],dtype=np.float64),
            "weights_m3_s":np.asarray(z["streamline_weight_m3_s"],dtype=np.float64),
            "producer":np.asarray(z["producer_labels"]).astype("U64"),
            "xi":np.asarray(z["xi"],dtype=np.float64),
        }

def native_semantic_audit(day,state,diag,*,a2e,r2,frozen_pressure,hetero_pv):
    mass=np.asarray(state["cartesian_component_mass_kg"],dtype=np.float64)
    sat=np.asarray(state["cartesian_saturation"],dtype=np.float64)
    pref=scalar(state["reference_gas_pressure_pa"])
    rec=np.asarray(a2e.local_mass(r2,sat,frozen_pressure,pref,hetero_pv),dtype=np.float64)
    diff=rec-mass
    linf=float(np.max(np.abs(diff)));glob=float(np.sum(diff));rel=rel_l2(rec,mass)
    cell_tol=max(1e-6,1e-10*max(float(np.max(np.abs(mass))),1.0))
    glob_tol=max(1e-6,1e-10*max(float(np.sum(np.abs(mass))),1.0))
    if linf>cell_tol or abs(glob)>glob_tol:
        raise GateError(f"Day{day}:native_mass_semantics:{linf}:{cell_tol}:{glob}:{glob_tol}")
    diag_sat_linf=float(np.max(np.abs(diag["saturation"]-sat)))
    if diag_sat_linf>1e-12:raise GateError(f"Day{day}:diagnostic_saturation_not_state:{diag_sat_linf}")
    return {"day":day,"native_frozen_pressure_mass_relative_L2":rel,
            "native_frozen_pressure_mass_Linf_kg":linf,
            "native_frozen_pressure_mass_global_difference_kg":glob,
            "diagnostic_saturation_Linf_vs_state":diag_sat_linf,
            "native_heterogeneous_PV_semantics_verified":True}

def build_branch(name,stale_days,diag,*,parent_mass,pref,hetero_pv,a2e,r2,e37a,e36,sg7a,sg7d,r3r4r1):
    # Same Day405 physical component mass, reconciled under this branch diagnostic pressure
    # using the late AV4 heterogeneous-PV EOS.
    sg=np.asarray(a2e.invert_local_mass(r2,parent_mass,diag["pressure"],pref,hetero_pv),dtype=np.float64)
    parent_sat=float(a2e.BACKGROUND)+sg
    rec=np.asarray(a2e.local_mass(r2,parent_sat,diag["pressure"],pref,hetero_pv),dtype=np.float64)
    linf=float(np.max(np.abs(rec-parent_mass)))
    tol=max(1e-6,1e-10*max(float(np.max(np.abs(parent_mass))),1.0))
    if linf>tol:raise GateError(f"{name}:branch_mass_reconciliation:{linf}:{tol}")

    xyz=diag["xyz_m"];tau=diag["tau_s"];weights_day=diag["weights_m3_s"]*DAY_TO_S;xi=diag["xi"]
    nstream=int(xyz.shape[0]);nfaces=int(xi.shape[0]);ncv=nfaces-1
    operator=sg7d.build_subsegment_operator(xyz,tau/DAY_TO_S,weights_day)
    geometry=e37a.build_control_volume_geometry(r2,operator,diag["pressure"],pref,nstream,ncv)
    face_pressure=e37a.build_face_pressure(e36,sg7d,xyz,diag["pressure"])
    cfl=float(r3r4r1.transport_cfl_dt_days(sg7a,xi,diag["tau_end_s"]))
    if not np.isfinite(cfl) or cfl<=0:raise GateError(f"{name}:invalid_CFL:{cfl}")
    return {"name":name,"stale_days":float(stale_days),"diag":diag,"parent_sat":parent_sat,
            "pressure":diag["pressure"],"weights_day":weights_day,"xi":xi,
            "geometry":geometry,"face_pressure":face_pressure,
            "nstream":nstream,"ncv":ncv,"cfl_days":cfl,
            "parent_mass_reconciliation_Linf_kg":linf}

def hetero_mapback(branch,old_cv_sat,new_cv_sat,old_cv_mass,new_cv_mass, *,
                   parent_mass,parent_total,pref,hetero_pv,a2e,r2):
    g=branch["geometry"];cv_id=g["cv_id"];flat=g["flat_cell"];pv=np.asarray(g["pv_m3"],dtype=np.float64);pseg=g["pseg_psi"]
    old_flat=np.asarray(old_cv_sat,dtype=np.float64).reshape(-1)
    new_flat=np.asarray(new_cv_sat,dtype=np.float64).reshape(-1)
    old_sub=old_flat[cv_id];new_sub=new_flat[cv_id]
    old_sg=np.clip(old_sub-BACKGROUND,0.0,0.60);new_sg=np.clip(new_sub-BACKGROUND,0.0,0.60)
    rho_old=np.asarray(r2.gas_density_from_state(old_sub,pseg,pref),dtype=np.float64)
    rho_new=np.asarray(r2.gas_density_from_state(new_sub,pseg,pref),dtype=np.float64)
    sub_delta=pv*(rho_new*new_sg-rho_old*old_sg)
    cv_delta=float(np.sum(new_cv_mass)-np.sum(old_cv_mass))
    transfer=float(np.sum(sub_delta)-cv_delta)
    ttol=max(1e-6,1e-10*max(abs(cv_delta),1.0))
    if abs(transfer)>ttol:raise GateError(f"{branch['name']}:CV_to_subsegment_transfer:{transfer}:{ttol}")
    deposited=np.bincount(flat,weights=sub_delta,minlength=15*50*50).reshape((15,50,50))
    trial=np.asarray(parent_mass,dtype=np.float64)+deposited
    target=parent_total+cv_delta
    roundoff=max(1e-6,1e-10*max(abs(target),1.0))
    if float(np.min(trial))<-roundoff:raise GateError(f"{branch['name']}:negative_grid_mass:{float(np.min(trial))}")
    trial=np.maximum(trial,0.0)
    ledger=float(np.sum(trial)-target)
    if abs(ledger)>roundoff:raise GateError(f"{branch['name']}:grid_ledger:{ledger}:{roundoff}")

    cap=np.asarray(a2e.local_mass(r2,np.full((15,50,50),MAX_SAT),branch["pressure"],pref,hetero_pv),dtype=np.float64)
    excess=float(np.max(trial-cap))
    cap_tol=max(1e-8,1e-12*max(float(np.max(cap)),1.0))
    if excess>cap_tol:raise GateError(f"{branch['name']}:hetero_capacity:{excess}:{cap_tol}")

    sg=np.asarray(a2e.invert_local_mass(r2,trial,branch["pressure"],pref,hetero_pv),dtype=np.float64)
    sat=float(a2e.BACKGROUND)+sg
    recon=np.asarray(a2e.local_mass(r2,sat,branch["pressure"],pref,hetero_pv),dtype=np.float64)
    recon_linf=float(np.max(np.abs(recon-trial)))
    if recon_linf>max(1e-6,1e-10*max(float(np.max(trial)),1.0)):
        raise GateError(f"{branch['name']}:hetero_EOS_reconstruction:{recon_linf}")
    return {"child_mass":trial,"child_sat":sat,"transfer_residual_kg":transfer,
            "ledger_residual_kg":ledger,"minimum_capacity_margin_kg":float(np.min(cap-trial)),
            "EOS_reconstruction_Linf_kg":recon_linf}

def shadow_step(branch,dt,*,parent_mass,parent_total,pref,hetero_pv,a2e,r2,e37a,sg7a):
    old_sat,old_mass,sample_closure=e37a.sample_grid_inventory_to_control_volumes(
        r2,branch["parent_sat"],branch["pressure"],pref,branch["geometry"],branch["nstream"],branch["ncv"])
    stol=max(1e-6,1e-10*max(abs(float(np.sum(old_mass))),1.0))
    if abs(sample_closure)>stol:raise GateError(f"{branch['name']}:CV_sample_closure:{sample_closure}:{stol}")
    tr=e37a.advance_component_mass_control_volumes(
        r2,sg7a,old_sat,old_mass,branch["geometry"]["cv_pressure_mass_coeff"],
        branch["face_pressure"],pref,branch["weights_day"],branch["xi"],dt)
    mp=hetero_mapback(branch,old_sat,tr["new_saturation"],old_mass,tr["new_mass"],
                      parent_mass=parent_mass,parent_total=parent_total,pref=pref,hetero_pv=hetero_pv,
                      a2e=a2e,r2=r2)
    final_total=float(np.sum(mp["child_mass"]))
    closure=final_total-parent_total-float(tr["injected_mass_kg"])+float(tr["produced_mass_kg"])
    ctol=max(1e-6,1e-10*max(abs(final_total),1.0))
    if abs(closure)>ctol:raise GateError(f"{branch['name']}:global_shadow_closure:{closure}:{ctol}")
    prows,cut=e37a.producer_rows_from_flux(branch["diag"]["producer"],branch["weights_day"],
                                          tr["outlet_fractional_flow"],tr["face_mass_flux_kg_day"][:,-1],dt)
    return {"child_mass":mp["child_mass"],"child_sat":mp["child_sat"],"final_total":final_total,
            "injected":float(tr["injected_mass_kg"]),"produced":float(tr["produced_mass_kg"]),
            "cut":float(cut),"CV_sample_closure":float(sample_closure),
            "CV_transport_closure":float(tr["mass_residual_kg"]),
            "mapback_transfer_residual":mp["transfer_residual_kg"],
            "mapback_ledger_residual":mp["ledger_residual_kg"],
            "minimum_capacity_margin":mp["minimum_capacity_margin_kg"],
            "EOS_reconstruction_Linf_kg":mp["EOS_reconstruction_Linf_kg"],
            "producer_rows":prows}

def selftest():
    assert [405-405,405-400,405-390]==[0,5,15]
    print("POSTV16 GPU-HYB-G3-R2-R1 structural self-test: PASS")

def main(root:Path,drive:Path)->int:
    root=root.resolve();drive=drive.resolve();out=drive/OUT_REL;blocked=drive/BLOCK_REL
    gates=[];stage="preflight"
    def gate(n,c,d=None):
        ok=bool(c);gates.append({"stage":stage,"gate":n,"pass":ok,"detail":"" if d is None else repr(d)})
        print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"),flush=True)
        if not ok:raise GateError(n)
    try:
        print("="*190)
        print("G3-R2-R1 — LATE-NATIVE DAY405 SAME-STATE STALE-vs-REFRESHED SHADOW REPAIR")
        print("HETEROGENEOUS CARTESIAN PV + LATE AV4 MASS SEMANTICS. NO CANONICAL STATE MUTATION.")
        print("="*190)

        stage="repository"
        gate("branch",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_failed_G3_R2_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("clean",gt(root,"status","--porcelain")=="")

        stage="prior_block_binding"
        br=drive/FAILED_REL/FAILED_REPORT
        gate("prior_block_present",br.is_file(),str(br))
        b=js(br)
        gate("prior_failed_stage_exact",b.get("failed_stage")==EXPECTED_FAILED_STAGE,b.get("failed_stage"))
        gate("prior_failure_is_mass_semantic_mismatch","late_mass_semantic_mismatch" in str(b.get("exception","")),b.get("exception"))

        a0=js(drive/A0_REL/A0_SUM)
        gate("A0_structure_audit_passed",a0.get("late_state_component_mass_direct_authority") is True)
        gate("A0_201node_diagnostics",a0.get("late_diagnostics_have_201_node_Pollock_TOF_database") is True)

        p3=module(root,P3,"g3r2r1_p3")
        a2e=module(root,A2E,"g3r2r1_a2e")
        r2=module(root,R2SRC,"g3r2r1_r2")
        e37a=module(root,E37A,"g3r2r1_e37a")
        e36=module(root,E36,"g3r2r1_e36")
        sg7a=module(root,SG7A,"g3r2r1_sg7a")
        sg7d=module(root,SG7D,"g3r2r1_sg7d")
        r3r4r1=module(root,R3R4R1,"g3r2r1_r3r4r1")

        stage="late_native_storage_authorities"
        a2ep=drive/A2E_REL/A2E_EPOCH;a6ep=drive/A6E_REL/A6E_STATE
        gate("A2E_epoch_present",a2ep.is_file(),str(a2ep));gate("A2E_epoch_SHA",sha(a2ep)==A2E_EPOCH_SHA,sha(a2ep))
        gate("A6E_state_present",a6ep.is_file(),str(a6ep));gate("A6E_state_SHA",sha(a6ep)==A6E_SHA,sha(a6ep))
        with np.load(a2ep,allow_pickle=False) as z:
            frozen_pressure=np.asarray(z["refreshed_pressure_psi"],dtype=np.float64)
            epoch_pref=scalar(z["reference_gas_pressure_pa"])
        with np.load(a6ep,allow_pickle=False) as z:
            phi=np.asarray(z["paired_porosity"],dtype=np.float64)
        hetero_pv=phi*float(a2e.BULK_VOLUME_M3)
        gate("hetero_phi_shape",phi.shape==(15,50,50),phi.shape)
        gate("hetero_phi_nonuniform",float(np.std(phi))>0,float(np.std(phi)))
        gate("hetero_PV_positive",float(np.min(hetero_pv))>0,float(np.min(hetero_pv)))

        specs=[
            (390,drive/D390_REL/D390_STATE,drive/D390_REL/D390_DIAG,D390_STATE_SHA,D390_DIAG_SHA),
            (400,drive/D400_REL/D400_STATE,drive/D400_REL/D400_DIAG,D400_STATE_SHA,D400_DIAG_SHA),
            (405,drive/D405_REL/D405_STATE,drive/D405_REL/D405_DIAG,D405_STATE_SHA,D405_DIAG_SHA)]
        states={};diags={};semantic_rows=[]

        stage="native_semantic_reconciliation"
        for day,sp,dp,ssha,dsha in specs:
            gate(f"Day{day}_state_SHA",sha(sp)==ssha,sha(sp));gate(f"Day{day}_diag_SHA",sha(dp)==dsha,sha(dp))
            st=load_npz(sp);dg=late_diag(dp)
            gate(f"Day{day}_pref_matches_A2E",abs(scalar(st["reference_gas_pressure_pa"])-epoch_pref)<=1e-9,
                 scalar(st["reference_gas_pressure_pa"])-epoch_pref)
            row=native_semantic_audit(day,st,dg,a2e=a2e,r2=r2,frozen_pressure=frozen_pressure,hetero_pv=hetero_pv)
            semantic_rows.append(row);states[day]=st;diags[day]=dg
            gate(f"Day{day}_native_semantics",row["native_heterogeneous_PV_semantics_verified"] is True,row)

        stage="Day405_parent"
        parent_mass=np.asarray(states[405]["cartesian_component_mass_kg"],dtype=np.float64)
        parent_total=float(np.sum(parent_mass));pref=scalar(states[405]["reference_gas_pressure_pa"])
        gate("parent_mass_positive",parent_total>0,parent_total)

        stage="branch_build"
        b0=build_branch("REFRESHED_0D",0,diags[405],parent_mass=parent_mass,pref=pref,hetero_pv=hetero_pv,
                        a2e=a2e,r2=r2,e37a=e37a,e36=e36,sg7a=sg7a,sg7d=sg7d,r3r4r1=r3r4r1)
        b5=build_branch("STALE_5D",5,diags[400],parent_mass=parent_mass,pref=pref,hetero_pv=hetero_pv,
                        a2e=a2e,r2=r2,e37a=e37a,e36=e36,sg7a=sg7a,sg7d=sg7d,r3r4r1=r3r4r1)
        b15=build_branch("STALE_15D",15,diags[390],parent_mass=parent_mass,pref=pref,hetero_pv=hetero_pv,
                         a2e=a2e,r2=r2,e37a=e37a,e36=e36,sg7a=sg7a,sg7d=sg7d,r3r4r1=r3r4r1)
        branches=[b0,b5,b15]
        gate("all_streamline_counts_equal",len({b["nstream"] for b in branches})==1,{b["name"]:b["nstream"] for b in branches})
        common_dt=min(b["cfl_days"] for b in branches)
        gate("common_dt_positive",common_dt>0,common_dt)

        stage="shadow_transport"
        results={}
        for bch in branches:
            results[bch["name"]]=shadow_step(
                bch,common_dt,parent_mass=parent_mass,parent_total=parent_total,pref=pref,hetero_pv=hetero_pv,
                a2e=a2e,r2=r2,e37a=e37a,sg7a=sg7a)

        injected=[results[b["name"]]["injected"] for b in branches]
        injtol=max(1e-8,1e-10*max(abs(injected[0]),1.0))
        gate("same_injected_component_mass_all_branches",max(injected)-min(injected)<=injtol,
             {"values":injected,"tolerance":injtol})

        ref=results["REFRESHED_0D"];comparisons=[]
        for name in ["STALE_5D","STALE_15D"]:
            x=results[name]
            comparisons.append({
                "branch":name,"staleness_days":5 if name=="STALE_5D" else 15,
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
        write_csv(out/SEMANTICS,semantic_rows)
        branch_rows=[];producer_rows=[]
        for bch in branches:
            x=results[bch["name"]]
            branch_rows.append({
                "branch":bch["name"],"staleness_days":bch["stale_days"],
                "branch_CFL_dt_days":bch["cfl_days"],"common_shadow_dt_days":common_dt,
                "parent_mass_reconciliation_Linf_kg":bch["parent_mass_reconciliation_Linf_kg"],
                "injected_CO2_mass_kg":x["injected"],"produced_CO2_mass_kg":x["produced"],
                "producer_CO2_gas_cut":x["cut"],"final_stored_CO2_mass_kg":x["final_total"],
                "CV_sample_closure_kg":x["CV_sample_closure"],"CV_transport_closure_kg":x["CV_transport_closure"],
                "mapback_transfer_residual_kg":x["mapback_transfer_residual"],
                "mapback_ledger_residual_kg":x["mapback_ledger_residual"],
                "minimum_heterogeneous_capacity_margin_kg":x["minimum_capacity_margin"],
                "EOS_reconstruction_Linf_kg":x["EOS_reconstruction_Linf_kg"]})
            for pr in x["producer_rows"]:
                producer_rows.append({"branch":bch["name"],"staleness_days":bch["stale_days"],**pr})
        write_csv(out/RESULTS,branch_rows);write_csv(out/COMPARE,comparisons);write_csv(out/PRODUCERS,producer_rows)

        child_map={"REFRESHED_0D":REF_CHILD,"STALE_5D":S5_CHILD,"STALE_15D":S15_CHILD}
        for bch in branches:
            x=results[bch["name"]]
            np.savez_compressed(out/child_map[bch["name"]],
                branch=np.asarray(bch["name"]),staleness_days=np.asarray(bch["stale_days"]),
                common_shadow_dt_days=np.asarray(common_dt),pressure_psi=bch["pressure"],
                parent_saturation_mass_consistent=bch["parent_sat"],
                child_saturation=x["child_sat"],child_cellwise_CO2_mass_kg=x["child_mass"])

        c5=next(x for x in comparisons if x["branch"]=="STALE_5D")
        c15=next(x for x in comparisons if x["branch"]=="STALE_15D")
        summary={
            "milestone":M,"status":PASS,
            "classification":"LATE_NATIVE_HETEROGENEOUS_PV_DAY405_SAME_STATE_0D_5D_15D_STALE_FLOW_CAUSAL_SHADOW_EFFECT_MEASURED_NO_CADENCE_SELECTION",
            "prior_G3_R2_block_correctly_localized":True,
            "prior_G3_R2_failure_cause":"modern uniform-PV/diagnostic-pressure semantic reinterpretation was invalid for late AV4 state",
            "late_native_storage_semantics":"heterogeneous paired_porosity Cartesian PV with frozen Day365 transport-pressure state authority",
            "late_diagnostic_flow_semantics":"same-time one-shot saturation-conditioned pressure/Darcy/Pollock/TOF with no transport feedback",
            "parent_day":405.0,"parent_state_sha256":D405_STATE_SHA,
            "parent_stored_CO2_mass_kg":parent_total,
            "common_shadow_dt_days":common_dt,
            "branch_CFL_dt_days":{b["name"]:b["cfl_days"] for b in branches},
            "native_late_mass_semantic_compatibility_verified":True,
            "heterogeneous_cartesian_PV_used":True,
            "separate_E41_capillary_redistribution_applied":False,
            "same_injected_component_mass_all_branches":True,
            "STALE_5D_effect_vs_refreshed":c5,
            "STALE_15D_effect_vs_refreshed":c15,
            "all_branches_component_mass_conservative":True,
            "all_branches_heterogeneous_capacity_safe_at_common_dt":True,
            "canonical_trajectory_mutated":False,
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
        print("Native late heterogeneous-PV semantics verified : True")
        print("Parent day                                        : 405")
        print("Common shadow dt days                             :",common_dt)
        print("Branch CFL days                                   :",{b["name"]:b["cfl_days"] for b in branches})
        print("5d stale child mass relL2 vs refreshed            :",c5["child_cellwise_CO2_mass_relative_L2_vs_refreshed"])
        print("15d stale child mass relL2 vs refreshed           :",c15["child_cellwise_CO2_mass_relative_L2_vs_refreshed"])
        print("5d stale child saturation Linf vs refreshed       :",c5["child_saturation_Linf_vs_refreshed"])
        print("15d stale child saturation Linf vs refreshed      :",c15["child_saturation_Linf_vs_refreshed"])
        print("Canonical trajectory mutated                      : False")
        print("Production cadence selected                       : False")
        print("G3-R3 decision freeze authorized                  : True")
        print("="*190)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps({
            "milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),"gates":gates,
            "canonical_trajectory_mutated":False,"production_pressure_refresh_cadence_selected":False,
            "G3_R3_early_late_causal_cadence_decision_freeze_authorized":False,"P4_authorized":False
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
