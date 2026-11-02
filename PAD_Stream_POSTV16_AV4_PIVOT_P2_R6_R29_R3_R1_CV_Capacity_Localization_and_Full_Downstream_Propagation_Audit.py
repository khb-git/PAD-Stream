#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, importlib.util, io, json, subprocess, sys, zipfile
from pathlib import Path
from typing import Any
import numpy as np

M="POSTV16-AV4-PIVOT-P2-R6-R29-R3-R1"
NAME="CV Capacity Localization + Full Downstream Propagation Audit"
PASS="AV4PIVOTP2R6R29R3R1_CV_CAPACITY_LOCALIZATION_AND_FULL_DOWNSTREAM_PROPAGATION_AUDIT_PASS_NO_STATE_MUTATION"
BLOCK="AV4PIVOTP2R6R29R3R1_TECHNICAL_OR_AUTHORITY_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="2812539d0398d3a80dc7d064711421c6a49afe02"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"
BASE_AV3=Path("post_v16")/RID/"POSTV16_AV3_Corey_Relperm_Heterogeneity"

GRID=(15,50,50); NSL=1078; NN=201; NCV=200
DAY=375.0; DAY_TO_S=86400.0
BACKGROUND=0.20; MAX_SATURATION=0.80; MAX_SG=0.60
DT_NOMINAL=0.03721673128859954
TARGET_NOMINAL=375.0372167312886
EXPECTED_R29R3_EXCESS_KG=0.2366214634703283
MASS_TOL=1e-6; SAT_TOL=1e-10; SOURCE_SINK_REL_TOL=1e-10
PROBE_SAFETY_FRACTION=1e-10

R29R3_FAIL_REL=BASE/"POSTV16_AV4_PIVOT_P2_R6_R29_R3_SCIENTIFIC_FAIL"
R29R3_FAIL="POSTV16_AV4_PIVOT_P2_R6_R29_R3_Scientific_Fail_Report.json"
R29R3_FAIL_STATUS="AV4PIVOTP2R6R29R3_CORRECTED_HETEROGENEOUS_PV_FROZEN_FLOW_TRANSPORT_CANDIDATE_SCIENTIFIC_FAIL_NO_AUTOMATIC_RERUN"
R29R3_FAIL_STAGE="CV_component_mass_transport"
R29R3_FAIL_GATE="E37A_CV_component_mass_transport"
R29R3_FAIL_DETAIL="TrialReject('control_volume_component_capacity_exceeded:0.2366214634703283')"

R26_REL=BASE/"POSTV16_AV4_PIVOT_P2_R6_R26_Day375_CapacityLimited_SplitState_Restart_Representation_Closure_and_Acceptance_Audit"
R26_ACCEPTANCE="POSTV16_AV4_PIVOT_P2_R6_R26_Day375_SplitState_Acceptance_Contract.json"
R26_MANIFEST="POSTV16_AV4_PIVOT_P2_R6_R26_Artifact_Manifest.csv"

R25R3_REL=BASE/"POSTV16_AV4_PIVOT_P2_R6_R25_R3_Controlled_Day375_CapacityLimited_ExactSupport_SplitState_Reprojection_Execution_Stage2_PresolveOff"
R25R3_STATE="POSTV16_AV4_PIVOT_P2_R6_R25_R3_CapacityLimited_SplitState_Day375.npz"
R25R3_MANIFEST="POSTV16_AV4_PIVOT_P2_R6_R25_R3_Artifact_Manifest.csv"
R25R3_STATE_SHA256="9893e2476bce1d46213cdd1304e60ad93b49ea285e084d06743a2ffab25f721f"
R22_EPOCH_SHA256="7f030fd3676eb3b61bc7f341dff8cb82659e87e210640a9488bf6fb15e7bd80e"
PRESSURE_EPOCH_SHA256="99d73cab1d33191a68578f29d3c03f9fac07ed77c39e124cc8eb5e5bf75aa84d"

A6E_REL=BASE_AV3/"POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
A6E_STATE="POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
A6E_STATE_SHA256="f9e3a7bd8c6dcc43d522e0cb99a0cede2bd212fd570085b4faf82dc71af8f803"

R29R3_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R3_Corrected_HeterogeneousPV_FrozenFlow_Transport_Candidate_Execution_NoTimeCommit.py"
R29R3_BLOB="cff953d1b5b7b6361d87107054cfb0259a0c4e6e"
E37A="PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB="0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
R2="PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB="a127f8730a16e150713420ea547a8de6255550ef"
A2E="PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB="79a8969233b72b4543edd382a0c3d1028c6dca09"
SG7D="PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB="890088c0c0fcab415a2c7351c5079ca8ee12bf82"
SG7A="PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py"
SG7A_BLOB="a4dd47338e7a85f130a6a70d0a41211e38c655f8"
E36="PAD_Stream_V16E36_Short_Adaptive_SGSim_Rollout_and_Early_Plume_Snapshot_Validation.py"
E36_BLOB="9ab4035c95a25bd61c649f86c82d88f059cef9e2"

SOURCE_BLOBS={
R29R3_RUNNER:R29R3_BLOB,E37A:E37A_BLOB,R2:R2_BLOB,A2E:A2E_BLOB,
SG7D:SG7D_BLOB,SG7A:SG7A_BLOB,E36:E36_BLOB,
}

OUT_TOKEN="POSTV16_AV4_PIVOT_P2_R6_R29_R3_R1"
OUT_REL=BASE/(OUT_TOKEN+"_CV_Capacity_Localization_and_Full_Downstream_Propagation_Audit")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")

class GateError(RuntimeError): pass

def gt(root,*args):
    return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for c in iter(lambda:f.read(1<<20),b""): h.update(c)
    return h.hexdigest()

def js(path): return json.loads(path.read_text(encoding="utf-8"))

def csvr(path):
    with open(path,newline="",encoding="utf-8") as f: return list(csv.DictReader(f))

def csvb(rows):
    if not rows:return b""
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    s=io.StringIO(newline="")
    w=csv.DictWriter(s,fieldnames=fields,lineterminator="\n")
    w.writeheader();w.writerows(rows)
    return s.getvalue().encode()

def jb(obj): return (json.dumps(obj,indent=2,sort_keys=True)+"\n").encode()

def manifest(directory,filename):
    out={}
    for row in csvr(directory/filename):
        p=directory/row["file"]
        if not p.is_file(): raise GateError(f"manifest_missing:{p.name}")
        if sha(p)!=row["sha256"]: raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size!=int(row["bytes"]): raise GateError(f"manifest_bytes:{p.name}")
        out[p.name]=row["sha256"]
    return out

def load_module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise GateError(f"cannot_load:{path}")
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def deterministic_npz_bytes(arrays):
    outer=io.BytesIO()
    with zipfile.ZipFile(outer,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for key in sorted(arrays):
            arr=np.asarray(arrays[key])
            if arr.dtype==object: raise GateError(f"object_dtype_forbidden:{key}")
            payload=io.BytesIO();np.lib.format.write_array(payload,arr,allow_pickle=False)
            info=zipfile.ZipInfo(f"{key}.npy");info.date_time=(1980,1,1,0,0,0)
            info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o600<<16
            zf.writestr(info,payload.getvalue())
    return outer.getvalue()

def selftest():
    old=np.asarray([10.0,20.0]);cap=np.asarray([11.0,21.0]);net=np.asarray([5.0,-3.0])
    assert (cap[0]-old[0])/net[0]==0.2
    assert abs((TARGET_NOMINAL-DAY)-DT_NOMINAL)<1e-12
    print("POSTV16 AV4 PIVOT P2-R6-R29-R3-R1 structural self-test: PASS")

def main(project_root,drive_root):
    root=project_root.resolve();drive=drive_root.resolve()
    out=drive/OUT_REL;block_dir=drive/BLOCK_REL
    stage="preflight";gates=[]
    def gate(name,cond,detail=None):
        ok=bool(cond);gates.append({"stage":stage,"gate":name,"pass":ok,"detail":"" if detail is None else repr(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}"+("" if detail is None else f" -- {detail}"))
        if not ok: raise GateError(name)

    try:
        stage="preexisting_state_firewall"
        gate("no_preexisting_R29R3R1_PASS",not (out/f"PAD_Stream_{OUT_TOKEN}_Summary.json").exists())
        gate("no_preexisting_R29R3R1_BLOCK",not (block_dir/f"{OUT_TOKEN}_Blocked_Report.json").exists())

        stage="repository_authority"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH)
        gate("parent_is_R29R3_commit",gt(root,"rev-parse","HEAD^")==PARENT)
        gate("repository_clean",gt(root,"status","--porcelain")=="")
        for fn,expected in SOURCE_BLOBS.items():
            p=root/fn
            gate(f"{Path(fn).stem}_present",p.is_file(),str(p))
            actual=gt(root,"hash-object",str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_blob_exact",actual==expected,actual)

        stage="immutable_R29R3_scientific_fail_authority"
        fail_path=drive/R29R3_FAIL_REL/R29R3_FAIL
        gate("R29R3_FAIL_exists",fail_path.is_file(),str(fail_path))
        fail=js(fail_path);fail_sha=sha(fail_path)
        gate("R29R3_FAIL_status_exact",fail.get("status")==R29R3_FAIL_STATUS,fail.get("status"))
        gate("R29R3_FAIL_stage_exact",fail.get("failed_stage")==R29R3_FAIL_STAGE,fail.get("failed_stage"))
        gate("R29R3_FAIL_gate_exact",fail.get("failed_gate")==R29R3_FAIL_GATE,fail.get("failed_gate"))
        gate("R29R3_FAIL_detail_exact",fail.get("detail")==R29R3_FAIL_DETAIL,fail.get("detail"))
        gate("R29R3_FAIL_no_time_commit",fail.get("physical_time_committed") is False)
        gate("R29R3_FAIL_no_auto_rerun",fail.get("automatic_rerun_authorized") is False)

        stage="accepted_parent_authority"
        r26=drive/R26_REL;manifest(r26,R26_MANIFEST);a26=js(r26/R26_ACCEPTANCE)
        gate("R26_accepts_parent_SHA",a26.get("accepted_state_sha256")==R25R3_STATE_SHA256)
        gate("R26_state_not_rewritten",a26.get("state_rewritten_by_R26") is False)

        r25=drive/R25R3_REL;m25=manifest(r25,R25R3_MANIFEST);state_path=r25/R25R3_STATE
        gate("R25R3_state_manifest_SHA_exact",m25.get(R25R3_STATE)==R25R3_STATE_SHA256)
        gate("R25R3_state_file_SHA_exact",sha(state_path)==R25R3_STATE_SHA256)

        with np.load(state_path,allow_pickle=False) as z:
            grid_parent=np.asarray(z["cartesian_component_mass_kg"],dtype=np.float64)
            represented_parent=np.asarray(z["represented_cartesian_cell_mass_kg"],dtype=np.float64)
            residual_parent=np.asarray(z["grid_residual_component_mass_kg"],dtype=np.float64)
            old_cv_mass=np.asarray(z["transport_CV_component_mass_kg"],dtype=np.float64)
            old_cv_sat=np.asarray(z["transport_CV_saturation"],dtype=np.float64)
            xyz=np.asarray(z["streamline_xyz_m"],dtype=np.float64)
            tof_s=np.asarray(z["streamline_tof_s"],dtype=np.float64)
            weights_m3_s=np.asarray(z["streamline_weight_m3_s"],dtype=np.float64)
            producer_labels=np.asarray(z["producer_labels"]).astype("U32")
            streamline_id=np.asarray(z["streamline_id"],dtype=np.int64)
            pressure_psi=np.asarray(z["refreshed_pressure_psi"],dtype=np.float64)
            p_ref=float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            r22_sha=str(np.asarray(z["source_R22_flow_epoch_sha256"]).reshape(()))
            pressure_sha=str(np.asarray(z["source_pressure_epoch_sha256"]).reshape(()))
        gate("parent_shapes_exact",grid_parent.shape==GRID and represented_parent.shape==GRID and residual_parent.shape==GRID and old_cv_mass.shape==(NSL,NCV) and old_cv_sat.shape==(NSL,NCV) and xyz.shape==(NSL,NN,3) and tof_s.shape==(NSL,NN) and weights_m3_s.shape==(NSL,) and producer_labels.shape==(NSL,))
        gate("parent_R22_SHA_exact",r22_sha==R22_EPOCH_SHA256)
        gate("parent_pressure_SHA_exact",pressure_sha==PRESSURE_EPOCH_SHA256)
        gate("parent_split_identity",float(np.max(np.abs(grid_parent-represented_parent-residual_parent)))<=MASS_TOL)

        stage="source_binding_and_geometry"
        e37a=load_module(root/E37A,"r29r3r1_e37a");r2=load_module(root/R2,"r29r3r1_r2")
        a2e=load_module(root/A2E,"r29r3r1_a2e");sg7d=load_module(root/SG7D,"r29r3r1_sg7d")
        sg7a=load_module(root/SG7A,"r29r3r1_sg7a");e36=load_module(root/E36,"r29r3r1_e36")

        a6e_path=drive/A6E_REL/A6E_STATE
        gate("A6E_state_SHA_exact",a6e_path.is_file() and sha(a6e_path)==A6E_STATE_SHA256)
        with np.load(a6e_path,allow_pickle=False) as z: phi=np.asarray(z["paired_porosity"],dtype=np.float64)
        gate("paired_porosity_shape_positive",phi.shape==GRID and np.all(phi>0.0) and np.isfinite(phi).all())
        hetero_pv=phi*float(a2e.BULK_VOLUME_M3)

        op=sg7d.build_subsegment_operator(xyz,tof_s/DAY_TO_S,weights_m3_s*DAY_TO_S)
        geometry=e37a.build_control_volume_geometry(r2,op,pressure_psi,p_ref,NSL,NCV)
        face_pressure=e37a.build_face_pressure(e36,sg7d,xyz,pressure_psi)
        gate("face_pressure_shape_exact",face_pressure.shape==(NSL,NCV+1))

        stage="parent_CV_representation_audit"
        cv_coeff=np.asarray(geometry["cv_pressure_mass_coeff"],dtype=np.float64)
        old_cv_mass_from_sat=np.asarray(e37a.cv_mass_from_saturation(r2,old_cv_sat,cv_coeff),dtype=np.float64)
        parent_cv_mass_error=old_cv_mass-old_cv_mass_from_sat
        parent_cv_max_abs_error=float(np.max(np.abs(parent_cv_mass_error)))
        parent_cv_recon_tol=max(1e-6,1e-10*max(float(np.max(np.abs(old_cv_mass))),1.0))
        cv_capacity=np.asarray(e37a.cv_mass_from_saturation(r2,np.full_like(old_cv_sat,float(e37a.INJECTED_BOUNDARY_SATURATION)),cv_coeff),dtype=np.float64)
        parent_capacity_excess_arr=old_cv_mass-cv_capacity
        parent_capacity_tol=max(1e-9,1e-12*max(float(np.max(np.abs(old_cv_mass))),1.0))
        parent_capacity_violations=parent_capacity_excess_arr>parent_capacity_tol
        parent_capacity_violation_count=int(np.count_nonzero(parent_capacity_violations))
        parent_max_capacity_excess=float(np.max(parent_capacity_excess_arr))

        stage="nominal_CV_trial_reconstruction"
        xi_faces=np.linspace(0.0,1.0,NCV+1,dtype=np.float64)
        weights_m3_day=weights_m3_s*DAY_TO_S
        scan=np.linspace(float(sg7a.S_INITIAL),float(sg7a.S_INJECTED),4001)
        min_df=float(np.min(np.asarray(sg7a.df_dS(scan),dtype=np.float64)))
        gate("SG7A_fractional_flow_monotone",min_df>=-1e-10,min_df)
        u_face=np.asarray(sg7a.u_dimensionless(xi_faces),dtype=np.float64)
        flux=np.zeros((NSL,NCV+1),dtype=np.float64)
        flux[:,0]=weights_m3_day*float(e37a.CO2_RHO_REF_KG_M3)
        donor=old_cv_sat[:,:-1]
        ff=np.asarray(sg7a.fractional_flow(donor),dtype=np.float64)
        rho=np.asarray(r2.gas_density_from_state(donor,face_pressure[:,1:-1],p_ref),dtype=np.float64)
        flux[:,1:-1]=weights_m3_day[:,None]*u_face[None,1:-1]*ff*rho
        outlet_sat=old_cv_sat[:,-1]
        outlet_ff=np.asarray(sg7a.fractional_flow(outlet_sat),dtype=np.float64)
        outlet_rho=np.asarray(r2.gas_density_from_state(outlet_sat,face_pressure[:,-1],p_ref),dtype=np.float64)
        flux[:,-1]=weights_m3_day*float(u_face[-1])*outlet_ff*outlet_rho

        net_rate=flux[:,:-1]-flux[:,1:]
        nominal_new_mass=old_cv_mass+DT_NOMINAL*net_rate
        nominal_min_mass=float(np.min(nominal_new_mass))
        nominal_negative_tol=max(1e-6,1e-10*max(float(np.sum(old_cv_mass)),1.0))
        nominal_inv_tol=max(1e-9,1e-12*max(float(np.max(np.abs(nominal_new_mass))),1.0))
        nominal_excess=nominal_new_mass-cv_capacity
        nominal_violating=nominal_excess>nominal_inv_tol
        nominal_violation_count=int(np.count_nonzero(nominal_violating))
        nominal_max_excess=float(np.max(nominal_excess))
        max_flat=int(np.argmax(nominal_excess));max_sl,max_cv=np.unravel_index(max_flat,nominal_excess.shape)
        gate("R29R3_failure_reproduced_max_excess",abs(nominal_max_excess-EXPECTED_R29R3_EXCESS_KG)<=1e-10,nominal_max_excess)
        gate("R29R3_failure_reproduced_violation_count_positive",nominal_violation_count>0,nominal_violation_count)

        injected_nominal=float(np.sum(flux[:,0])*DT_NOMINAL)
        produced_nominal=float(np.sum(flux[:,-1])*DT_NOMINAL)
        nominal_delta=float(np.sum(nominal_new_mass)-np.sum(old_cv_mass))
        nominal_global_residual=nominal_delta-injected_nominal+produced_nominal

        stage="capacity_limited_dt_localization"
        capacity_slack=cv_capacity-old_cv_mass
        positive_net=net_rate>0.0
        dt_capacity=np.full_like(old_cv_mass,np.inf,dtype=np.float64)
        dt_capacity[positive_net]=capacity_slack[positive_net]/net_rate[positive_net]
        finite_positive_limits=np.isfinite(dt_capacity)&(dt_capacity>=0.0)
        gate("at_least_one_nonnegative_capacity_dt",np.any(finite_positive_limits))
        dt_capacity_global=float(np.min(dt_capacity[finite_positive_limits]))
        dt_capacity_flat=int(np.argmin(np.where(finite_positive_limits,dt_capacity,np.inf)))
        limit_sl,limit_cv=np.unravel_index(dt_capacity_flat,dt_capacity.shape)
        dt_reduction=DT_NOMINAL-dt_capacity_global
        dt_reduction_fraction=dt_reduction/DT_NOMINAL

        violating_rows=[]
        for sl,cv in np.argwhere(nominal_violating):
            violating_rows.append({
                "streamline_index":int(sl),"streamline_id":int(streamline_id[sl]),"cv_index":int(cv),
                "old_saturation":float(old_cv_sat[sl,cv]),"old_mass_kg":float(old_cv_mass[sl,cv]),
                "mass_from_old_saturation_kg":float(old_cv_mass_from_sat[sl,cv]),
                "parent_mass_consistency_error_kg":float(parent_cv_mass_error[sl,cv]),
                "capacity_kg":float(cv_capacity[sl,cv]),"capacity_slack_kg":float(capacity_slack[sl,cv]),
                "inlet_mass_rate_kg_day":float(flux[sl,cv]),"outlet_mass_rate_kg_day":float(flux[sl,cv+1]),
                "net_mass_rate_kg_day":float(net_rate[sl,cv]),"nominal_dt_days":DT_NOMINAL,
                "capacity_limited_dt_days":float(dt_capacity[sl,cv]) if np.isfinite(dt_capacity[sl,cv]) else "",
                "nominal_new_mass_kg":float(nominal_new_mass[sl,cv]),
                "nominal_capacity_excess_kg":float(nominal_excess[sl,cv]),
            })
        violating_rows.sort(key=lambda r:float(r["nominal_capacity_excess_kg"]),reverse=True)

        stage="capacity_feasible_downstream_propagation_probe"
        probe_possible=(parent_capacity_violation_count==0 and parent_cv_max_abs_error<=parent_cv_recon_tol and dt_capacity_global>0.0 and dt_capacity_global<DT_NOMINAL)
        dt_probe=float(dt_capacity_global*(1.0-PROBE_SAFETY_FRACTION)) if probe_possible else float("nan")
        probe={"probe_possible":bool(probe_possible),"dt_probe_days":dt_probe if probe_possible else None,
               "CV_inversion_pass":False,"CV_to_subsegment_closure_pass":False,
               "subsegment_to_grid_closure_pass":False,"represented_nonnegative_pass":False,
               "split_identity_pass":False,"heterogeneous_cartesian_capacity_pass":False,
               "heterogeneous_cartesian_inversion_pass":False,"cartesian_source_sink_closure_pass":False,
               "all_downstream_checks_pass":False,"exception":None}
        probe_arrays={}
        if probe_possible:
            try:
                probe_new_mass=old_cv_mass+dt_probe*net_rate
                probe_sat=np.asarray(e37a.invert_cv_mass_to_saturation(r2,probe_new_mass,cv_coeff),dtype=np.float64)
                probe["CV_inversion_pass"]=True
                cv_id=np.asarray(geometry["cv_id"],dtype=np.int64);flat_cell=np.asarray(geometry["flat_cell"],dtype=np.int64)
                sub_pv=np.asarray(geometry["pv_m3"],dtype=np.float64);pseg=np.asarray(geometry["pseg_psi"],dtype=np.float64)
                old_sub_sat=old_cv_sat.reshape(-1)[cv_id];new_sub_sat=probe_sat.reshape(-1)[cv_id]
                old_sub_sg=np.clip(old_sub_sat-BACKGROUND,0.0,MAX_SG);new_sub_sg=np.clip(new_sub_sat-BACKGROUND,0.0,MAX_SG)
                rho_old=np.asarray(r2.gas_density_from_state(old_sub_sat,pseg,p_ref),dtype=np.float64)
                rho_new=np.asarray(r2.gas_density_from_state(new_sub_sat,pseg,p_ref),dtype=np.float64)
                sub_delta_mass=sub_pv*(rho_new*new_sub_sg-rho_old*old_sub_sg)
                probe_cv_delta=float(np.sum(probe_new_mass)-np.sum(old_cv_mass))
                probe_sub_delta=float(np.sum(sub_delta_mass));probe_transfer_residual=probe_sub_delta-probe_cv_delta
                probe_grid_tol=max(MASS_TOL,SOURCE_SINK_REL_TOL*max(abs(probe_cv_delta),float(np.sum(grid_parent)),1.0))
                probe["CV_to_subsegment_closure_pass"]=abs(probe_transfer_residual)<=probe_grid_tol
                delta_grid=np.bincount(flat_cell,weights=sub_delta_mass,minlength=int(np.prod(GRID))).reshape(GRID)
                deposit_residual=float(np.sum(delta_grid)-probe_sub_delta)
                probe["subsegment_to_grid_closure_pass"]=abs(deposit_residual)<=probe_grid_tol
                represented_candidate=represented_parent+delta_grid;residual_candidate=residual_parent.copy();candidate_grid=grid_parent+delta_grid
                min_rep=float(np.min(represented_candidate))
                split_err=float(np.max(np.abs(candidate_grid-represented_candidate-residual_candidate)))
                probe["represented_nonnegative_pass"]=min_rep>=-MASS_TOL
                probe["split_identity_pass"]=split_err<=MASS_TOL
                full_sat=np.full(GRID,float(a2e.INJECTED),dtype=np.float64)
                cart_capacity=np.asarray(a2e.local_mass(r2,full_sat,pressure_psi,p_ref,hetero_pv),dtype=np.float64)
                cart_cap_tol=max(1e-8,1e-12*max(float(np.max(cart_capacity)),1.0))
                cart_excess=float(np.max(candidate_grid-cart_capacity))
                probe["heterogeneous_cartesian_capacity_pass"]=cart_excess<=cart_cap_tol
                candidate_sat=None;candidate_mass_err=None
                if probe["heterogeneous_cartesian_capacity_pass"]:
                    candidate_sg=np.asarray(a2e.invert_local_mass(r2,candidate_grid,pressure_psi,p_ref,hetero_pv),dtype=np.float64)
                    candidate_sat=float(a2e.BACKGROUND)+candidate_sg
                    recon=np.asarray(a2e.local_mass(r2,candidate_sat,pressure_psi,p_ref,hetero_pv),dtype=np.float64)
                    candidate_mass_err=float(np.max(np.abs(recon-candidate_grid)))
                    probe["heterogeneous_cartesian_inversion_pass"]=(candidate_mass_err<=1e-8 and float(np.min(candidate_sat))>=BACKGROUND-SAT_TOL and float(np.max(candidate_sat))<=MAX_SATURATION+SAT_TOL)
                injected_probe=float(np.sum(flux[:,0])*dt_probe);produced_probe=float(np.sum(flux[:,-1])*dt_probe)
                target_probe=float(np.sum(grid_parent))+injected_probe-produced_probe;candidate_total=float(np.sum(candidate_grid))
                source_sink_residual=candidate_total-target_probe
                probe["cartesian_source_sink_closure_pass"]=abs(source_sink_residual)<=probe_grid_tol
                probe.update({"CV_delta_kg":probe_cv_delta,"CV_to_subsegment_residual_kg":probe_transfer_residual,
                              "subsegment_to_grid_residual_kg":deposit_residual,"minimum_represented_candidate_mass_kg":min_rep,
                              "split_identity_max_abs_error_kg":split_err,"cartesian_max_capacity_excess_kg":cart_excess,
                              "cartesian_capacity_tolerance_kg":cart_cap_tol,
                              "cartesian_cellwise_mass_reconstruction_error_kg":candidate_mass_err,
                              "cartesian_source_sink_residual_kg":source_sink_residual,
                              "candidate_saturation_min":float(np.min(candidate_sat)) if candidate_sat is not None else None,
                              "candidate_saturation_max":float(np.max(candidate_sat)) if candidate_sat is not None else None})
                required=("CV_inversion_pass","CV_to_subsegment_closure_pass","subsegment_to_grid_closure_pass",
                          "represented_nonnegative_pass","split_identity_pass","heterogeneous_cartesian_capacity_pass",
                          "heterogeneous_cartesian_inversion_pass","cartesian_source_sink_closure_pass")
                probe["all_downstream_checks_pass"]=all(bool(probe[k]) for k in required)
                probe_arrays={"probe_new_CV_mass_kg":probe_new_mass,"probe_new_CV_saturation":probe_sat,
                              "probe_delta_grid_mass_kg":delta_grid,"probe_represented_candidate_mass_kg":represented_candidate,
                              "probe_candidate_grid_mass_kg":candidate_grid}
            except Exception as exc:
                probe["exception"]=repr(exc)

        if parent_capacity_violation_count>0:
            root_classification="PARENT_CV_CAPACITY_INVALID_UNDER_CURRENT_R22_GEOMETRY"
        elif parent_cv_max_abs_error>parent_cv_recon_tol:
            root_classification="PARENT_CV_MASS_SATURATION_REPRESENTATION_INCONSISTENT"
        elif nominal_violation_count<=0:
            root_classification="R29R3_CAPACITY_FAILURE_NOT_REPRODUCED"
        elif probe["all_downstream_checks_pass"]:
            root_classification="NOMINAL_DT_LOCAL_CV_CAPACITY_LIMIT_WITH_FULL_DOWNSTREAM_COMPATIBILITY_AT_CAPACITY_FEASIBLE_DIAGNOSTIC_PROBE"
        else:
            root_classification="NOMINAL_DT_LOCAL_CV_CAPACITY_LIMIT_WITH_ADDITIONAL_DOWNSTREAM_INCOMPATIBILITY_DETECTED_BY_PROPAGATION_PROBE"

        stage="diagnostic_publication"
        full_arrays={"old_CV_mass_kg":old_cv_mass,"old_CV_saturation":old_cv_sat,
                     "old_CV_mass_from_saturation_kg":old_cv_mass_from_sat,
                     "old_CV_mass_consistency_error_kg":parent_cv_mass_error,
                     "CV_capacity_kg":cv_capacity,"CV_capacity_slack_kg":capacity_slack,
                     "CV_net_mass_rate_kg_day":net_rate,"nominal_new_CV_mass_kg":nominal_new_mass,
                     "nominal_CV_capacity_excess_kg":nominal_excess,"nominal_CV_violating_mask":nominal_violating,
                     "capacity_limited_dt_days":dt_capacity,"face_mass_flux_kg_day":flux,
                     "streamline_id":streamline_id,"producer_labels":producer_labels,
                     "nominal_dt_days":np.asarray(DT_NOMINAL),"global_capacity_limited_dt_days":np.asarray(dt_capacity_global),
                     "diagnostic_probe_dt_days":np.asarray(dt_probe)}
        full_arrays.update(probe_arrays)

        out.mkdir(parents=True,exist_ok=False)
        npz_name=f"{OUT_TOKEN}_Full_CV_Capacity_and_Propagation_Audit.npz"
        (out/npz_name).write_bytes(deterministic_npz_bytes(full_arrays))
        (out/f"{OUT_TOKEN}_Violating_CV_Localization.csv").write_bytes(csvb(violating_rows))

        summary={"milestone":M,"name":NAME,"status":PASS,"classification":root_classification,
                 "source_R29R3_scientific_fail_sha256":fail_sha,"source_R25R3_state_sha256":R25R3_STATE_SHA256,
                 "source_A6E_state_sha256":A6E_STATE_SHA256,
                 "parent_CV_mass_saturation_max_abs_error_kg":parent_cv_max_abs_error,
                 "parent_CV_mass_saturation_tolerance_kg":parent_cv_recon_tol,
                 "parent_CV_capacity_violation_count":parent_capacity_violation_count,
                 "parent_CV_max_capacity_excess_kg":parent_max_capacity_excess,
                 "nominal_dt_days":DT_NOMINAL,"nominal_target_day":TARGET_NOMINAL,
                 "nominal_CV_min_mass_kg":nominal_min_mass,"nominal_CV_negative_mass_tolerance_kg":nominal_negative_tol,
                 "nominal_CV_capacity_violation_count":nominal_violation_count,
                 "nominal_CV_max_capacity_excess_kg":nominal_max_excess,
                 "nominal_CV_capacity_tolerance_kg":nominal_inv_tol,
                 "maximum_excess_streamline_index":int(max_sl),"maximum_excess_streamline_id":int(streamline_id[max_sl]),
                 "maximum_excess_CV_index":int(max_cv),"maximum_excess_old_saturation":float(old_cv_sat[max_sl,max_cv]),
                 "maximum_excess_old_mass_kg":float(old_cv_mass[max_sl,max_cv]),
                 "maximum_excess_capacity_kg":float(cv_capacity[max_sl,max_cv]),
                 "maximum_excess_old_capacity_slack_kg":float(capacity_slack[max_sl,max_cv]),
                 "maximum_excess_net_rate_kg_day":float(net_rate[max_sl,max_cv]),
                 "global_capacity_limiting_streamline_index":int(limit_sl),
                 "global_capacity_limiting_streamline_id":int(streamline_id[limit_sl]),
                 "global_capacity_limiting_CV_index":int(limit_cv),
                 "global_capacity_limited_dt_days":dt_capacity_global,
                 "nominal_minus_capacity_dt_days":dt_reduction,
                 "required_nominal_dt_reduction_fraction":dt_reduction_fraction,
                 "nominal_injected_mass_kg":injected_nominal,"nominal_produced_mass_kg":produced_nominal,
                 "nominal_CV_delta_kg":nominal_delta,"nominal_global_source_sink_residual_kg":nominal_global_residual,
                 "diagnostic_capacity_feasible_probe":probe,"full_CV_array_count":NSL*NCV,
                 "transport_state_mutation_executed":False,"accepted_candidate_created":False,
                 "physical_time_advance_executed":False,"automatic_dt_reduction_executed":False,
                 "automatic_rerun_executed":False,"P3_authorized":False}

        propagation={"milestone":M,"status":PASS,
                     "purpose":"trace R29-R3 CV-capacity failure through every downstream consumer before any scientific repair execution",
                     "failure_layer":"frozen-flow control-volume component-mass transport",
                     "audited_pipeline":["accepted parent CV mass/saturation consistency","parent CV capacity",
                         "exact frozen face-flux reconstruction","nominal CV mass trial",
                         "per-CV capacity slack and capacity-limited dt","capacity-feasible diagnostic CV inversion",
                         "CV-to-subsegment component-mass delta","subsegment-to-Cartesian flat-cell deposition",
                         "represented Cartesian nonnegativity","split-state recomposition",
                         "heterogeneous Cartesian pressure capacity","heterogeneous Cartesian mass inversion",
                         "global Cartesian source/sink closure"],
                     "diagnostic_probe_is_authoritative_execution":False,
                     "diagnostic_probe_dt_change_authorized":False,
                     "diagnostic_probe_state_accepted":False,
                     "root_classification":root_classification,"probe_results":probe}

        decision={"milestone":M,"status":PASS,"classification":root_classification,
                  "P2_R6_R29_R3_R2_authorized":True,
                  "P2_R6_R29_R3_R2_name":"Comprehensive CV-Capacity + Downstream-Propagation Repair Design Freeze",
                  "P2_R6_R29_R3_R2_design_only":True,"P2_R6_R29_R3_R2_execution_authorized":False,
                  "P2_R6_R29_R3_R2_must_bind_R29R3_FAIL_SHA":fail_sha,
                  "P2_R6_R29_R3_R2_must_bind_this_audit":True,
                  "automatic_dt_reduction_authorized":False,"dt_change_authorized_now":False,
                  "CV_transport_operator_change_authorized_now":False,"subsegment_delta_change_authorized_now":False,
                  "Cartesian_mapback_change_authorized_now":False,"residual_sidecar_mutation_authorized":False,
                  "support_growth_authorized":False,"state_mutation_authorized":False,
                  "physical_time_advance_authorized":False,"R30_authorized":False,"P3_authorized":False}

        (out/f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out/f"{OUT_TOKEN}_Full_Downstream_Propagation_Audit.json").write_bytes(jb(propagation))
        (out/f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))
        (out/f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))
        rows=[]
        for p in sorted(out.iterdir()):
            if p.is_file(): rows.append({"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size})
        (out/f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(rows))

        print("="*190)
        print(M,"PASS")
        print("Root classification                   :",root_classification)
        print("R29-R3 FAIL SHA256                    :",fail_sha)
        print("Parent CV mass/sat max error kg       :",parent_cv_max_abs_error)
        print("Parent CV capacity violations         :",parent_capacity_violation_count)
        print("Nominal CV capacity violations        :",nominal_violation_count)
        print("Nominal maximum capacity excess kg    :",nominal_max_excess)
        print("Maximum excess streamline/CV          :",int(max_sl),"/",int(max_cv))
        print("Global capacity-limited dt days       :",dt_capacity_global)
        print("Nominal dt days                       :",DT_NOMINAL)
        print("Required nominal dt reduction fraction:",dt_reduction_fraction)
        print("Diagnostic downstream probe possible  :",probe_possible)
        print("Downstream propagation all checks PASS:",probe["all_downstream_checks_pass"])
        print("Probe is execution authority          : False")
        print("State mutation / time / auto-rerun    : False / False / False")
        print("R29-R3-R2 design freeze               : AUTHORIZED")
        print("R30 authorized                        : False")
        print("="*190)
        return 0

    except Exception as exc:
        block_dir.mkdir(parents=True,exist_ok=True)
        p=block_dir/f"{OUT_TOKEN}_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(jb({"milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),
                              "R29R3_SCIENTIFIC_FAIL_preserved":True,"R25R3_parent_state_preserved":True,
                              "state_mutation_executed":False,"physical_time_advance_executed":False,
                              "automatic_dt_reduction_executed":False,"automatic_rerun_authorized":False,
                              "R30_authorized":False,"P3_authorized":False,"gates_completed":gates}))
        print(M,"TECHNICAL / AUTHORITY BLOCK")
        print("Stage:",stage);print("Exception:",repr(exc))
        return 2

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",type=Path,default=Path("."))
    ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test:selftest();raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))
