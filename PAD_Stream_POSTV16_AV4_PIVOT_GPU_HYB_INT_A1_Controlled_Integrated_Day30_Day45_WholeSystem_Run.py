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

M="POSTV16-AV4-PIVOT-GPU-HYB-INT-A1"
PASS="POSTV16AV4PIVOTGPUHYBINTA1_CONTROLLED_INTEGRATED_DAY30_DAY45_WHOLE_SYSTEM_RUN_PASS"
BLOCK="POSTV16AV4PIVOTGPUHYBINTA1_TECHNICAL_CONSERVATION_CAPACITY_OR_AUTHORITY_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="4f77fe5d751dab72bf12994f294ef20f65b2165a"

G3R7_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R7_Controlled_Integrated_Controller_Shadow_Execution_Protocol_Freeze.py"
G3R7_BLOB="2204b827987a2027cc9e6bda8b27582d4b713d60"
G3R5_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R5_Reconciled_Runtime_Controller_Shadow_Implementation_and_Test.py"
G3R5_BLOB="0675eaac7e1c47601dada82e295beaab0076c998"
G2R3_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_Rank3_Day40_45_ExactFlow_and_Hybrid_Endpoint_Diagnostic.py"
G2R3_BLOB="b06a18d93e68dca2c3d7326cc8b76e4116999117"
A8_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_A8_Day100_Production_Trajectory_Validation.py"
A8_BLOB="65006bfdc44630746d4c45c6d8696560b70efef6"
A1_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_A1_R1_ReadOnly_Hybrid_ComponentMass_Bridge_TOF_Identity_Repair.py"
A1_BLOB="6b0bff953b11b393affc429825622fe4afdc5942"
B1_RUNNER="PAD_Stream_POSTV16_AV1_B1_R1_C26_to_E37A_Component_Mass_Representation_Equivalence_Audit.py"
B1_BLOB="8d9561d7c85805b82dedc26073c4633f90eeeab6"
E11_RUNNER="PAD_Stream_V16E11_R2_Packed_SG5_Serialization_Repair_and_Controlled_Hybrid_Streamline_Pilot.py"
E11_BLOB="bf89c14a3cb177fb483e233a17b72e824d31119b"
R3R5_RUNNER="PAD_Stream_V16E41R3R5_Multi_Refresh_Cadence_Sensitivity_Runtime_Refresh_Policy_Calibration.py"
R3R5_BLOB="15aae3224ba4337cad72f9b4aa9166d602791349"
R3R4_RUNNER="PAD_Stream_V16E41R3R4R1_Refreshed_Flow_CFL_Alignment_Repair.py"
R3R4_BLOB="5f8433437ce111533338ceada922f51abb2edefe"
R2_REPAIR_RUNNER="PAD_Stream_V16E41R2_Capacity_Aware_Conservative_MapBack_Timestep_Repair.py"
R2_REPAIR_BLOB="f6961c48dc47c5fb55f2af658ef4ce429eb66533"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"

G3R7_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G3_R7_Controlled_Integrated_Controller_Shadow_Execution_Protocol_Freeze"
G3R7_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G3_R7_Summary.json"
G3R7_PROTOCOL="POSTV16_AV4_PIVOT_GPU_HYB_G3_R7_INT_A1_Protocol.json"
G3R7_DECISION="POSTV16_AV4_PIVOT_GPU_HYB_G3_R7_Decision_Contract.json"
G3R7_STATUS="POSTV16AV4PIVOTGPUHYBG3R7_CONTROLLED_INTEGRATED_CONTROLLER_SHADOW_EXECUTION_PROTOCOL_FREEZE_PASS_NO_PHYSICS_EXECUTION"

TARGET_DAY=45.0
START_DAY=30.0
MAX_FLOW_EPOCH_DAYS=5.0
SCHEDULED_REFRESH_DAYS=(30.0,35.0,40.0,45.0)
VIS_DAYS=(30.0,35.0,40.0,45.0)
DAY_TO_S=86400.0
FT_TO_M=0.3048
INJECTOR_MASS_RATE_KG_DAY=500_000.0
EXPECTED_GRID=(15,50,50)
POLICY_NAME="G3_RECONCILED_FIVE_DAY_DEVELOPMENT_SHADOW"

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_INT_A1"
OUT_REL=BASE/(OUT_TOKEN+"_Controlled_Integrated_Day30_Day45_WholeSystem_Run")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DECISION=f"{OUT_TOKEN}_Decision_Contract.json"
STEPS=f"{OUT_TOKEN}_Accepted_Transitions.csv"
REFRESHES=f"{OUT_TOKEN}_Flow_Refreshes.csv"
CAPACITY=f"{OUT_TOKEN}_Capacity_Events.csv"
CONTROLLER=f"{OUT_TOKEN}_Controller_Events.csv"
ROUTES=f"{OUT_TOKEN}_Route_Audit.csv"
REFERENCE=f"{OUT_TOKEN}_Reference_Comparison.csv"
CHECKPOINTS=f"{OUT_TOKEN}_Visualization_Checkpoint_Index.csv"
FINAL_STATE=f"{OUT_TOKEN}_Final_Day45_PostRefresh_State.npz"
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

def gt(root:Path,*a:str)->str:
    return subprocess.check_output(["git","-C",str(root),*a],text=True).strip()

def blob(root:Path,p:Path)->str:
    return gt(root,"hash-object",str(p))

def mod(root:Path,fn:str,expected:str,name:str):
    p=root/fn
    if not p.is_file():
        raise GateError(f"missing_source:{fn}")
    actual=blob(root,p)
    if actual!=expected:
        raise GateError(f"source_blob:{fn}:{actual}:{expected}")
    s=importlib.util.spec_from_file_location(name,p)
    if s is None or s.loader is None:
        raise GateError(f"import_spec:{fn}")
    m=importlib.util.module_from_spec(s)
    sys.modules[name]=m
    s.loader.exec_module(m)
    return m

def js(p:Path):
    return json.loads(p.read_text(encoding="utf-8"))

def load_npz(p:Path):
    with np.load(p,allow_pickle=False) as z:
        return {k:np.asarray(z[k]).copy() for k in z.files}

def scalar(x:Any)->float:
    return float(np.asarray(x).reshape(()))

def int_scalar(x:Any)->int:
    return int(np.asarray(x).reshape(()))

def rel_l2(a,b):
    a=np.asarray(a,float);b=np.asarray(b,float)
    return float(np.linalg.norm((a-b).ravel())/max(float(np.linalg.norm(b.ravel())),1e-30))

def write_csv(p:Path,rows:list[dict[str,Any]]):
    rows=list(rows)
    if not rows:
        p.write_text("",encoding="utf-8")
        return
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n")
        w.writeheader();w.writerows(rows)

def deterministic_npz_bytes(arrays:dict[str,Any])->bytes:
    outer=io.BytesIO()
    with zipfile.ZipFile(outer,mode="w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for key in sorted(arrays):
            b=io.BytesIO()
            np.save(b,np.asarray(arrays[key]),allow_pickle=False)
            info=zipfile.ZipInfo(f"{key}.npy",date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o600<<16
            zf.writestr(info,b.getvalue())
    return outer.getvalue()

def selftest(root:Path):
    g3r7=mod(root,G3R7_RUNNER,G3R7_BLOB,"inta1_g3r7_selftest")
    g3r5=mod(root,G3R5_RUNNER,G3R5_BLOB,"inta1_g3r5_selftest")
    g2=mod(root,G2R3_RUNNER,G2R3_BLOB,"inta1_g2_selftest")
    mod(root,A8_RUNNER,A8_BLOB,"inta1_a8_selftest")
    mod(root,A1_RUNNER,A1_BLOB,"inta1_a1_selftest")
    mod(root,B1_RUNNER,B1_BLOB,"inta1_b1_selftest")
    mod(root,E11_RUNNER,E11_BLOB,"inta1_e11_selftest")
    mod(root,R3R5_RUNNER,R3R5_BLOB,"inta1_r3r5_selftest")
    mod(root,R3R4_RUNNER,R3R4_BLOB,"inta1_r3r4_selftest")
    mod(root,R2_REPAIR_RUNNER,R2_REPAIR_BLOB,"inta1_repair_selftest")
    assert START_DAY==30.0 and TARGET_DAY==45.0
    assert MAX_FLOW_EPOCH_DAYS==5.0
    assert SCHEDULED_REFRESH_DAYS==(30.0,35.0,40.0,45.0)
    assert g3r5.PRODUCTION_MAX_FLOW_EPOCH_DAYS is None
    assert g3r5.decide_shadow_action(35.0,30.0).action=="FULL_FLOW_REFRESH"
    assert g3r5.decide_shadow_action(40.0,35.0).action=="FULL_FLOW_REFRESH"
    assert g3r5.decide_shadow_action(45.0,40.0).action=="FULL_FLOW_REFRESH"
    assert g2.DAY30_RESTART_SHA=="093fa9570b07d91d6865c8464104cd6f72c271b2d638b93dc167c74497827035"
    assert g3r7.NEXT_MILESTONE=="POSTV16-AV4-PIVOT-GPU-HYB-INT-A1"
    print("POSTV16 GPU-HYB-INT-A1 structural/whole-system self-test: PASS")

def main(root:Path,drive:Path)->int:
    root=root.resolve()
    drive=drive.resolve()
    out=drive/OUT_REL
    blocked=drive/BLOCK_REL
    gates=[]
    stage="preflight"
    parent_sha_before=None

    def gate(name,cond,detail=None):
        ok=bool(cond)
        gates.append({"stage":stage,"gate":name,"pass":ok,"detail":"" if detail is None else repr(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}"+("" if detail is None else f" -- {detail}"),flush=True)
        if not ok:
            raise GateError(name)

    try:
        print("="*202)
        print("INT-A1 — CONTROLLED INTEGRATED PAD-STREAM DAY30 -> DAY45 WHOLE-SYSTEM RUN")
        print("REAL PHYSICS + GPU HYBRID TRANSPORT. EXACT 5-DAY CONTROLLER BOUNDARIES: DAY35 / DAY40 / DAY45.")
        print("NONCANONICAL CONTROLLED TRAJECTORY. IMMUTABLE HISTORICAL REFERENCES REMAIN UNCHANGED.")
        print("="*202)

        stage="repository"
        gate("branch_exact",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_G3_R7_PASS_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("repository_clean",gt(root,"status","--porcelain")=="")

        stage="source_authority"
        g3r7=mod(root,G3R7_RUNNER,G3R7_BLOB,"inta1_g3r7")
        g3r5=mod(root,G3R5_RUNNER,G3R5_BLOB,"inta1_g3r5")
        g2=mod(root,G2R3_RUNNER,G2R3_BLOB,"inta1_g2")
        a8=mod(root,A8_RUNNER,A8_BLOB,"inta1_a8")
        a1=mod(root,A1_RUNNER,A1_BLOB,"inta1_a1")
        b1=mod(root,B1_RUNNER,B1_BLOB,"inta1_b1")
        e11=mod(root,E11_RUNNER,E11_BLOB,"inta1_e11")
        r3r5=mod(root,R3R5_RUNNER,R3R5_BLOB,"inta1_r3r5")
        r3r4=mod(root,R3R4_RUNNER,R3R4_BLOB,"inta1_r3r4")
        repair=mod(root,R2_REPAIR_RUNNER,R2_REPAIR_BLOB,"inta1_repair")

        stage="G3_R7_authority"
        s7p=drive/G3R7_REL/G3R7_SUM
        p7p=drive/G3R7_REL/G3R7_PROTOCOL
        d7p=drive/G3R7_REL/G3R7_DECISION
        for label,p in [("G3R7_summary",s7p),("G3R7_protocol",p7p),("G3R7_decision",d7p)]:
            gate(label+"_present",p.is_file(),str(p))
        s7=js(s7p);p7=js(p7p);d7=js(d7p)
        gate("G3R7_status_exact",s7.get("status")==G3R7_STATUS,s7.get("status"))
        gate("G3_controller_phase_closed",s7.get("G3_controller_development_phase_closed") is True)
        gate("INT_A1_authorized",s7.get("INT_A1_authorized") is True)
        gate("INT_A1_window_exact",s7.get("INT_A1_window_days")==[30.0,45.0],s7.get("INT_A1_window_days"))
        gate("INT_A1_boundaries_exact",s7.get("INT_A1_refresh_boundary_days")==[35.0,40.0,45.0],s7.get("INT_A1_refresh_boundary_days"))
        gate("INT_A1_visual_days_exact",s7.get("INT_A1_visualization_checkpoint_days")==[30.0,35.0,40.0,45.0])
        gate("INT_A1_whole_system_transport_required",s7.get("INT_A1_requires_Hybrid10_plus_exact_E37A_conservative_transport") is True)
        gate("INT_A1_exact_flow_refresh_required",s7.get("INT_A1_requires_exact_FV_Darcy_Pollock_TOF_refresh") is True)
        gate("INT_A1_stepwise_mass_conservation_required",s7.get("INT_A1_requires_stepwise_component_mass_conservation") is True)
        gate("INT_A1_noncanonical",s7.get("INT_A1_trajectory_class")=="CONTROLLED_NONCANONICAL_WHOLE_SYSTEM_SHADOW_TRAJECTORY")
        gate("INT_A1_no_production_activation",s7.get("INT_A1_production_activation_authorized") is False)
        gate("G3R7_protocol_boundary_policy_exact",
             p7.get("time_window",{}).get("boundary_landing_policy")=="CLIP_ACCEPTED_TIMESTEP_TO_CONTROLLER_BOUNDARY_BEFORE_REFRESH")
        gate("G3R7_decision_INT_A1_authorized",d7.get("INT_A1_controlled_integrated_Day30_to45_run_authorized") is True)

        stage="Day30_start_authority"
        bridge_summary=drive/g2.R3A0_REL/g2.R3A0_SUM
        parent_path=drive/g2.R3A0_REL/g2.R3A0_RESTART
        gate("Day30_bridge_summary_present",bridge_summary.is_file(),str(bridge_summary))
        gate("Day30_restart_present",parent_path.is_file(),str(parent_path))
        bs=js(bridge_summary)
        gate("Day30_bridge_status_exact",bs.get("status")==g2.R3A0_STATUS,bs.get("status"))
        parent_sha_before=sha(parent_path)
        gate("Day30_restart_SHA_exact",parent_sha_before==g2.DAY30_RESTART_SHA,parent_sha_before)
        current=load_npz(parent_path)
        gate("Day30_start_time_exact",scalar(current["physical_time_days"])==30.0,scalar(current["physical_time_days"]))

        initial_injected=scalar(current["cumulative_injected_co2_mass_kg"])
        initial_produced=scalar(current["cumulative_produced_co2_mass_kg"])
        initial_stored=scalar(current["stored_co2_mass_current_kg"])

        stage="physics_authority"
        roles={}
        for role in ["R3R2R1","E36","E37A","R2_PHYSICS","SG2","SG3","SG4","SG5","SG6","SG7A","SG7D"]:
            fn,bl=r3r4.SOURCE_BLOBS[role]
            roles[role]=mod(root,fn,bl,f"inta1_{role.lower()}")
        r3r2r1=roles["R3R2R1"];e36=roles["E36"];e37a=roles["E37A"];physics=roles["R2_PHYSICS"]
        sg2=roles["SG2"];sg3=roles["SG3"];sg4=roles["SG4"];sg5=roles["SG5"];sg6=roles["SG6"]
        sg7a=roles["SG7A"];sg7d=roles["SG7D"]

        pfn,pblob=r3r4.SOURCE_BLOBS["PERM"]
        perm_path=root/pfn
        gate("permeability_blob_exact",blob(root,perm_path)==pblob,blob(root,perm_path))
        permeability_md=np.loadtxt(perm_path,skiprows=1,dtype=np.float64).reshape(EXPECTED_GRID,order="C")
        cell_pv=0.20*(20.0*FT_TO_M)*(20.0*FT_TO_M)*(4.0*FT_TO_M)

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
        adapter=e11.import_exact(root/e11.E9_ADAPTER[0],e11.E9_ADAPTER[1],"inta1_adapter")
        teacher=e11.import_exact(root/e11.R2_ADAPTER[0],e11.R2_ADAPTER[1],"inta1_teacher")
        e9r1=e11.import_exact(root/e11.E9R1_RUNNER[0],e11.E9R1_RUNNER[1],"inta1_e9r1")
        shock=teacher.welge_shock(adapter.teacher_params(params),scan_nodes=4097)
        speed=float(shock["characteristic_speed"])
        swstar=float(shock["Sw_star"])
        tf=e9r1.prepare_tf(e5)
        gate("TensorFlow_2_20_exact",tf.__version__=="2.20.0",tf.__version__)
        gate("GPU_visible",len(tf.config.list_physical_devices("GPU"))>=1,[str(x) for x in tf.config.list_physical_devices("GPU")])
        model=e9r1.build_inference_model(tf,10,"INTA1_Hybrid10")
        gate("Hybrid10_parameter_count_exact",model.count_params()==52545,model.count_params())
        model.load_weights(str(drive/e11.E6A_REL/e11.E6A_CHECKPOINT[0]))

        def rebuild_db(epoch:dict[str,Any]):
            vx,vy,vz=sg5.construct_face_pore_velocities(epoch["qx"],epoch["qy"],epoch["qz"])
            _faces,seeds=sg5.build_seeds(epoch["qx"],epoch["qy"],epoch["qz"])
            streamlines=sg5.trace_streamlines(seeds,vx,vy,vz)
            converted=r3r4.convert_sg5_to_sg6_streamlines(streamlines)
            db=sg6.build_transport_database(converted)
            if int(np.asarray(db["xyz_m"]).shape[0])!=int(epoch["nstream"]):
                raise GateError("db_stream_count")
            if int(np.asarray(db["xi"]).shape[0])!=int(epoch["nfaces"]):
                raise GateError("db_face_count")
            w=np.asarray(db["weights_m3_s"],float)*DAY_TO_S
            if np.max(np.abs(w-np.asarray(epoch["weights_m3_day"],float)))>1e-8:
                raise GateError("db_weights")
            if np.max(np.abs(np.asarray(db["xi"],float)-np.asarray(epoch["xi_faces"],float)))>1e-14:
                raise GateError("db_xi")
            return db

        profile_cache={}
        def infer_profiles(day:float,db:dict[str,np.ndarray],epoch_tag:str):
            key=(epoch_tag,round(float(day),12))
            if key in profile_cache:
                return profile_cache[key]
            tau=np.asarray(db["tau_s"],float)
            tau_end=np.asarray(db["tau_end_s"],float)
            xi=np.asarray(db["xi"],float)
            terminal_days=tau_end/DAY_TO_S
            xstar=(float(day)/terminal_days)*speed
            clocks=np.asarray([e11.classify_clock(float(x)) for x in xstar],dtype="U32")
            idx=np.flatnonzero(clocks=="LEARNED_WINDOW")
            profiles={};reject={}
            if idx.size:
                cond=[];states=[]
                for i in idx:
                    st=adapter.physical_time_state(
                        elapsed_time=day,tau_end=float(terminal_days[i]),
                        characteristic_speed=speed,Sw_star=swstar)
                    states.append(st)
                    cond.append(adapter.conditioning_vector("HYBRID10",params,st))
                pred=e9r1.infer(tf,model,xi.astype(np.float32),np.asarray(cond,dtype=np.float32),batch=256)
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
            result=(profiles,clocks,reject)
            profile_cache[key]=result
            return result

        refresh_rows=[]
        step_rows=[]
        capacity_rows=[]
        controller_rows=[]
        route_rows=[]
        reference_rows=[]
        checkpoint_rows=[]
        checkpoint_payloads={}
        pre_boundary_states={}
        capacity_margins=[]

        epoch=None;db=None;epoch_start_time=None;epoch_serial=0
        refresh_count=0;cadence_refresh_count=0;capacity_refresh_count=0
        total_hybrid_routes=0;total_exact_fallback_routes=0
        unscheduled_refresh=False

        def make_visual_payload(day:float,trigger:str):
            p_ref=scalar(current["co2_density_reference_pressure_pa"])
            sat=np.asarray(current["transport_saturation"],float)
            pressure=np.asarray(epoch["pressure_psi"],float)
            cell_mass=r3r4.parent_cellwise_component_mass(physics,sat,pressure,p_ref,cell_pv)
            return {
                "physical_time_days":np.asarray(day,dtype=np.float64),
                "accepted_step_index":np.asarray(int_scalar(current["accepted_step_index"]),dtype=np.int64),
                "controller_trigger_ascii":np.frombuffer(trigger.encode("ascii"),dtype=np.uint8),
                "flow_epoch_origin_day":np.asarray(epoch_start_time,dtype=np.float64),
                "flow_epoch_age_days":np.asarray(0.0,dtype=np.float64),
                "transport_saturation":sat,
                "cartesian_component_mass_kg":np.asarray(cell_mass,float),
                "pressure_psi":pressure,
                "qx":np.asarray(epoch["qx"],float),
                "qy":np.asarray(epoch["qy"],float),
                "qz":np.asarray(epoch["qz"],float),
                "streamline_xyz_m":np.asarray(db["xyz_m"],float),
                "streamline_tof_s":np.asarray(db["tau_s"],float),
                "streamline_tau_end_s":np.asarray(db["tau_end_s"],float),
                "streamline_weights_m3_s":np.asarray(db["weights_m3_s"],float),
                "streamline_xi":np.asarray(db["xi"],float),
                "producer_labels":np.asarray(epoch["labels"]),
                "stored_co2_mass_current_kg":np.asarray(scalar(current["stored_co2_mass_current_kg"]),dtype=np.float64),
                "cumulative_injected_co2_mass_kg":np.asarray(scalar(current["cumulative_injected_co2_mass_kg"]),dtype=np.float64),
                "cumulative_produced_co2_mass_kg":np.asarray(scalar(current["cumulative_produced_co2_mass_kg"]),dtype=np.float64),
                "producer_co2_gas_cut":np.asarray(scalar(current["current_producer_co2_gas_cut"]),dtype=np.float64),
                "flow_local_relative_residual":np.asarray(float(epoch["flow_local_residual"]),dtype=np.float64),
                "flow_global_relative_residual":np.asarray(float(epoch["flow_global_residual"]),dtype=np.float64),
                "capture_fraction":np.asarray(float(epoch["capture_fraction"]),dtype=np.float64),
            }

        def do_refresh(trigger:str,scheduled:bool):
            nonlocal current,epoch,db,epoch_start_time,epoch_serial
            nonlocal refresh_count,cadence_refresh_count,capacity_refresh_count,unscheduled_refresh
            before_time=scalar(current["physical_time_days"])
            before_step=int_scalar(current["accepted_step_index"])
            before_inj=scalar(current["cumulative_injected_co2_mass_kg"])
            before_prod=scalar(current["cumulative_produced_co2_mass_kg"])
            before_stored=scalar(current["stored_co2_mass_current_kg"])

            if trigger=="RESTART_OR_INITIALIZATION":
                decision=g3r5.decide_shadow_action(before_time,before_time,hard_triggers=("RESTART_OR_INITIALIZATION",))
            elif trigger=="CAPACITY_PREFLIGHT_REJECTION":
                decision=g3r5.decide_shadow_action(before_time,epoch_start_time,hard_triggers=("CAPACITY_PREFLIGHT_REJECTION",))
            else:
                decision=g3r5.decide_shadow_action(before_time,epoch_start_time)

            if decision.action!="FULL_FLOW_REFRESH":
                raise GateError(f"controller_did_not_authorize_refresh:{trigger}:{before_time}:{decision.action}")

            refreshed,new_epoch,_rows=r3r5.build_flow_epoch(
                current=current,r3r4r1=r3r4,physics=physics,r3r2r1=r3r2r1,e36=e36,e37a=e37a,
                sg2=sg2,sg3=sg3,sg4=sg4,sg5=sg5,sg6=sg6,sg7a=sg7a,sg7d=sg7d,
                permeability_md=permeability_md,cell_pore_volume_m3=cell_pv)

            if scalar(refreshed["physical_time_days"])!=before_time:
                raise GateError("refresh_advanced_time")
            if int_scalar(refreshed["accepted_step_index"])!=before_step:
                raise GateError("refresh_advanced_step")
            if scalar(refreshed["cumulative_injected_co2_mass_kg"])!=before_inj:
                raise GateError("refresh_changed_injection")
            if scalar(refreshed["cumulative_produced_co2_mass_kg"])!=before_prod:
                raise GateError("refresh_changed_production")
            mtol=max(1e-6,1e-10*max(abs(before_stored),1.0))
            if abs(scalar(refreshed["stored_co2_mass_current_kg"])-before_stored)>mtol:
                raise GateError("refresh_changed_stored")

            current=refreshed
            epoch=new_epoch
            db=rebuild_db(new_epoch)
            epoch_start_time=before_time
            epoch_serial+=1
            refresh_count+=1
            if trigger=="CADENCE":
                cadence_refresh_count+=1
            if trigger=="CAPACITY_PREFLIGHT_REJECTION":
                capacity_refresh_count+=1
                unscheduled_refresh=True

            refresh_rows.append({
                "refresh_index":refresh_count,
                "trigger":trigger,
                "scheduled":scheduled,
                "physical_time_days":before_time,
                "accepted_step_index":before_step,
                "controller_action":decision.action,
                "controller_reason":decision.reason,
                "fixed_point_iterations":int(new_epoch["fixed_point_iterations"]),
                "CFL_dt_days":float(new_epoch["cfl_dt_days"]),
                "streamline_count":int(new_epoch["nstream"]),
                "capture_fraction":float(new_epoch["capture_fraction"]),
                "flow_local_relative_residual":float(new_epoch["flow_local_residual"]),
                "flow_global_relative_residual":float(new_epoch["flow_global_residual"]),
                "pressure_rel_L2_vs_pre_refresh":float(new_epoch["refresh_pressure_rel_L2_vs_parent"]),
                "saturation_Linf_vs_pre_refresh":float(new_epoch["refresh_saturation_Linf_vs_parent"]),
                "refresh_global_mass_error_kg":float(new_epoch["refresh_global_mass_error_kg"]),
            })
            controller_rows.append({
                "physical_time_days":before_time,
                "flow_epoch_origin_before_event":before_time if trigger=="RESTART_OR_INITIALIZATION" else float(decision.flow_epoch_age_days and (before_time-decision.flow_epoch_age_days)),
                "flow_epoch_age_days":float(decision.flow_epoch_age_days),
                "trigger":trigger,
                "action":decision.action,
                "reason":decision.reason,
                "scheduled":scheduled,
            })

            if before_time in VIS_DAYS:
                checkpoint_payloads[before_time]=make_visual_payload(before_time,trigger)

        stage="controlled_integrated_rollout"
        do_refresh("RESTART_OR_INITIALIZATION",scheduled=True)

        while scalar(current["physical_time_days"])<TARGET_DAY-1e-13:
            now=scalar(current["physical_time_days"])
            if epoch is None or db is None or epoch_start_time is None:
                raise GateError("missing_epoch")

            due=epoch_start_time+MAX_FLOW_EPOCH_DAYS
            if now>=due-1e-13:
                gate(f"scheduled_boundary_exact_{now:.12f}",any(abs(now-d)<=1e-10 for d in (35.0,40.0)))
                do_refresh("CADENCE",scheduled=True)
                now=scalar(current["physical_time_days"])
                due=epoch_start_time+MAX_FLOW_EPOCH_DAYS

            decision=g3r5.decide_shadow_action(now,epoch_start_time)
            if decision.action!="REUSE_FLOW_NETWORK_FOR_MIXED_TRANSPORT":
                raise GateError(f"unexpected_nonreuse_between_boundaries:{now}:{epoch_start_time}:{decision.action}")

            intended_target=min(TARGET_DAY,due,now+float(epoch["cfl_dt_days"]))
            candidate_dt=float(intended_target-now)
            if not np.isfinite(candidate_dt) or candidate_dt<=0:
                raise GateError(f"nonpositive_candidate_dt:{candidate_dt}")

            parent_time=scalar(current["physical_time_days"])
            parent_step=int_scalar(current["accepted_step_index"])
            parent_sat=np.asarray(current["transport_saturation"],float)
            pressure=np.asarray(epoch["pressure_psi"],float)
            p_ref=scalar(current["co2_density_reference_pressure_pa"])
            parent_stored=scalar(current["stored_co2_mass_current_kg"])

            recomputed=float(physics.stored_co2_mass_kg(parent_sat,pressure,p_ref,cell_pv))
            ptol=max(1e-6,1e-10*max(abs(parent_stored),1.0))
            if abs(recomputed-parent_stored)>ptol:
                raise GateError(f"parent_mass_pressure_mismatch:{recomputed-parent_stored}")

            old_sat,old_mass,sample=e37a.sample_grid_inventory_to_control_volumes(
                physics,parent_sat,pressure,p_ref,epoch["geometry"],epoch["nstream"],epoch["ncv"])
            stol=max(1e-6,1e-10*max(abs(float(np.sum(old_mass))),1.0))
            if abs(float(sample))>stol:
                raise GateError(f"sampling_closure:{sample}")

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
            outlet_rho=np.asarray(physics.gas_density_from_state(
                outlet_sat,epoch["face_pressure_psi"][:,-1],p_ref),float)
            outlet_rate=q*float(u[-1])*outlet_ff*outlet_rho
            target_i=np.sum(old_mass,axis=1)+inlet_rate*candidate_dt-outlet_rate*candidate_dt

            direct_res=float(np.max(np.abs(np.sum(child_mass,axis=1)-target_i)))
            if direct_res>1e-7:
                raise GateError(f"boundary_budget_vs_exact_fallback:{direct_res}")

            epoch_tag=f"INTA1_E{epoch_serial}"
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
                        physics,
                        np.full(int(epoch["ncv"]),float(physics.BACKGROUND_SATURATION+physics.MAX_INCREMENTAL_CO2_SATURATION)),
                        coeff),float)
                    mm,lam,closure=a1.box_project(raw[j],float(target_i[sl]),cap)
                    if abs(float(closure))>1e-8:
                        raise GateError(f"Hybrid_budget_closure:{sl}:{closure}")
                    denom=max(float(np.sum(np.abs(raw[j]))),1e-30)
                    correction_l1.append(float(np.sum(np.abs(mm-raw[j])))/denom)
                    ss=np.asarray(e37a.invert_cv_mass_to_saturation(physics,mm,coeff),float)
                    child_mass[sl]=mm
                    child_cv_sat[sl]=ss

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
                    "physical_time_days":parent_time,
                    "accepted_step_index":parent_step,
                    "trial_dt_days":candidate_dt,
                    "overcapacity_cell_count":int(preflight["overcapacity_cell_count"]),
                    "max_capacity_excess_kg":float(preflight["max_capacity_excess_kg"]),
                    "minimum_capacity_margin_kg":float(preflight["minimum_capacity_margin_kg"]),
                    "planned_schedule_status":"BLOCK_REQUIRES_PROTOCOL_REPAIR",
                })
                # The exact capacity safety path is still executed as a same-parent refresh,
                # but INT-A1 cannot remain the planned exact Day30/35/40/45 schedule afterward.
                do_refresh("CAPACITY_PREFLIGHT_REJECTION",scheduled=False)
                raise GateError("unscheduled_capacity_refresh_requires_INT_A1_R1_protocol_repair")

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
            if abs(step_residual)>ctol:
                raise GateError(f"step_component_mass_closure:{step_residual}")

            prod_rows,aggregate_cut=e37a.producer_rows_from_flux(
                epoch["labels"],epoch["weights_m3_day"],
                np.asarray(sg7a.fractional_flow(old_sat[:,-1]),float),
                outlet_rate,candidate_dt)
            if not np.isfinite(aggregate_cut) or not 0<=aggregate_cut<=1:
                raise GateError(f"producer_gas_cut_invalid:{aggregate_cut}")

            child=e36.make_child_state(
                current,child_sat,pressure,p_ref,candidate_dt,produced_step,
                aggregate_cut,final_stored,step_residual,False)
            child["transport_face_count"]=np.asarray(epoch["nfaces"],dtype=np.int64)
            child["transport_control_volume_count"]=np.asarray(epoch["ncv"],dtype=np.int64)
            child["mass_conservative_flow_refresh_active"]=np.asarray(True,dtype=bool)
            child["runtime_refresh_policy_name_ascii"]=np.frombuffer(POLICY_NAME.encode("ascii"),dtype=np.uint8)
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
            for boundary in (35.0,40.0,45.0):
                if abs(accepted_time-boundary)<=1e-13:
                    child["physical_time_days"]=np.asarray(boundary,dtype=np.float64)
                    accepted_time=boundary

            total_hybrid_routes+=int(eligible.size)
            total_exact_fallback_routes+=int(epoch["nstream"]-eligible.size)
            route_rows.append({
                "accepted_step_index":int_scalar(child["accepted_step_index"]),
                "parent_time_days":parent_time,
                "accepted_time_days":accepted_time,
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
                "parent_time_days":parent_time,
                "accepted_time_days":accepted_time,
                "accepted_dt_days":candidate_dt,
                "active_epoch_CFL_dt_days":float(epoch["cfl_dt_days"]),
                "epoch_origin_day":epoch_start_time,
                "epoch_age_before_step_days":parent_time-epoch_start_time,
                "controller_boundary_landing":accepted_time in (35.0,40.0,45.0),
                "raw_minimum_capacity_margin_kg":float(preflight["minimum_capacity_margin_kg"]),
                "injected_CO2_mass_kg":injected_step,
                "produced_CO2_mass_kg":produced_step,
                "stored_CO2_mass_kg":final_stored,
                "step_component_mass_residual_kg":step_residual,
                "producer_CO2_gas_cut":float(aggregate_cut),
                "Hybrid_incremental_route_count":int(eligible.size),
                "exact_fallback_route_count":int(epoch["nstream"]-eligible.size),
            })

            current={k:np.asarray(v).copy() for k,v in child.items()}
            if accepted_time in (35.0,40.0,45.0):
                pre_boundary_states[accepted_time]={k:np.asarray(v).copy() for k,v in current.items()}

        stage="Day45_final_refresh"
        gate("Day45_pre_refresh_landing",scalar(current["physical_time_days"])==45.0,scalar(current["physical_time_days"]))
        gate("Day45_epoch_origin_40",abs(epoch_start_time-40.0)<=1e-12,epoch_start_time)
        gate("Day45_controller_action_refresh",
             g3r5.decide_shadow_action(45.0,epoch_start_time).action=="FULL_FLOW_REFRESH")
        do_refresh("CADENCE",scheduled=True)

        stage="trajectory_closure"
        gate("final_day_45",scalar(current["physical_time_days"])==45.0,scalar(current["physical_time_days"]))
        gate("scheduled_refresh_times_exact",
             [float(r["physical_time_days"]) for r in refresh_rows if r["scheduled"]]==[30.0,35.0,40.0,45.0],
             [r["physical_time_days"] for r in refresh_rows])
        gate("no_unscheduled_refresh",unscheduled_refresh is False)
        gate("capacity_triggered_refresh_count_zero",capacity_refresh_count==0,capacity_refresh_count)
        gate("cadence_refresh_count_three",cadence_refresh_count==3,cadence_refresh_count)
        gate("total_refresh_count_four",refresh_count==4,refresh_count)
        gate("visual_checkpoint_days_complete",sorted(checkpoint_payloads)==[30.0,35.0,40.0,45.0],sorted(checkpoint_payloads))
        gate("Day30_parent_immutable",sha(parent_path)==parent_sha_before,sha(parent_path))

        final_stored=scalar(current["stored_co2_mass_current_kg"])
        final_injected=scalar(current["cumulative_injected_co2_mass_kg"])
        final_produced=scalar(current["cumulative_produced_co2_mass_kg"])
        cumulative_residual=final_stored-scalar(current["stored_co2_mass_initial_kg"])-final_injected+final_produced
        mtol=max(1e-6,1e-10*max(abs(final_stored),1.0))
        gate("final_component_mass_closure",abs(cumulative_residual)<=mtol,(cumulative_residual,mtol))
        expected_added_injection=INJECTOR_MASS_RATE_KG_DAY*(TARGET_DAY-START_DAY)
        actual_added_injection=final_injected-initial_injected
        gate("Day30_to45_injection_rate_exact",
             abs(actual_added_injection-expected_added_injection)<=max(1e-6,1e-12*expected_added_injection),
             (actual_added_injection,expected_added_injection))

        stage="immutable_reference_comparison"
        ref_summary_path=drive/g2.OUT_REL/g2.SUMMARY
        ref40_path=drive/g2.OUT_REL/g2.DAY40_STATE
        ref45_path=drive/g2.OUT_REL/g2.DAY45_STATE
        for label,p in [("G2R3_summary",ref_summary_path),("G2R3_Day40",ref40_path),("G2R3_Day45",ref45_path)]:
            gate(label+"_present",p.is_file(),str(p))
        ref_summary=js(ref_summary_path)
        gate("G2R3_status_exact",ref_summary.get("status")==g2.PASS,ref_summary.get("status"))
        gate("G2R3_reference_continuous",ref_summary.get("continuous_30_to45_rollout") is True)
        refs={40.0:load_npz(ref40_path),45.0:load_npz(ref45_path)}
        for day in (40.0,45.0):
            controlled=pre_boundary_states[day]
            ref=refs[day]
            cs=np.asarray(controlled["transport_saturation"],float)
            rs=np.asarray(ref["transport_saturation"],float)
            metrics={
                "day":day,
                "controlled_vs_reference_saturation_relative_L2":rel_l2(cs,rs),
                "controlled_vs_reference_saturation_Linf":float(np.max(np.abs(cs-rs))),
                "controlled_minus_reference_stored_mass_kg":
                    scalar(controlled["stored_co2_mass_current_kg"])-scalar(ref["stored_co2_mass_current_kg"]),
                "controlled_minus_reference_cumulative_produced_mass_kg":
                    scalar(controlled["cumulative_produced_co2_mass_kg"])-scalar(ref["cumulative_produced_co2_mass_kg"]),
                "controlled_minus_reference_producer_gas_cut":
                    scalar(controlled["current_producer_co2_gas_cut"])-scalar(ref["current_producer_co2_gas_cut"]),
                "new_scientific_acceptance_threshold_applied":False,
                "comparison_role":"DIAGNOSTIC_ONLY_IMMUTABLE_REFERENCE",
            }
            gate(f"Day{int(day)}_reference_metrics_finite",
                 all(np.isfinite(float(metrics[k])) for k in [
                     "controlled_vs_reference_saturation_relative_L2",
                     "controlled_vs_reference_saturation_Linf",
                     "controlled_minus_reference_stored_mass_kg",
                     "controlled_minus_reference_cumulative_produced_mass_kg",
                     "controlled_minus_reference_producer_gas_cut"]))
            reference_rows.append(metrics)

        stage="publication"
        gate("output_absent",not out.exists(),str(out))
        out.mkdir(parents=True)

        for day in VIS_DAYS:
            payload=checkpoint_payloads[day]
            fn=f"{OUT_TOKEN}_Day{int(day):03d}_Visualization_Checkpoint.npz"
            b=deterministic_npz_bytes(payload)
            (out/fn).write_bytes(b)
            checkpoint_rows.append({
                "day":day,
                "file":fn,
                "sha256":hashlib.sha256(b).hexdigest(),
                "pressure_ready":True,
                "saturation_ready":True,
                "component_mass_ready":True,
                "streamlines_ready":True,
                "TOF_ready":True,
                "controller_overlay_ready":True,
            })

        final_bytes=deterministic_npz_bytes(current)
        (out/FINAL_STATE).write_bytes(final_bytes)

        summary={
            "milestone":M,
            "status":PASS,
            "classification":"CONTROLLED_WHOLE_SYSTEM_DAY30_DAY45_GPU_HYBRID_TRAJECTORY_EXECUTED_EXACT_5DAY_REFRESH_BOUNDARIES_CERTIFIED_VISUALIZATION_CHECKPOINTS_READY",
            "starting_day":START_DAY,
            "target_day":TARGET_DAY,
            "development_flow_refresh_reference_days":MAX_FLOW_EPOCH_DAYS,
            "scheduled_refresh_days":[30.0,35.0,40.0,45.0],
            "accepted_transport_transition_count":len(step_rows),
            "total_flow_refresh_count":refresh_count,
            "cadence_refresh_count":cadence_refresh_count,
            "capacity_triggered_refresh_count":capacity_refresh_count,
            "minimum_raw_capacity_margin_kg":float(np.min(capacity_margins)) if capacity_margins else None,
            "cumulative_Hybrid_route_uses":total_hybrid_routes,
            "cumulative_exact_fallback_route_uses":total_exact_fallback_routes,
            "final_cumulative_component_mass_residual_kg":cumulative_residual,
            "Day30_to45_added_injected_CO2_mass_kg":actual_added_injection,
            "Hybrid_parent_anchored_incremental_transport_used":True,
            "exact_E37A_fallback_used":True,
            "exact_FV_Darcy_Pollock_TOF_refresh_used":True,
            "single_common_E37A_mapback_used":True,
            "conservative_capillary_redistribution_used":True,
            "visualization_checkpoint_days":[30.0,35.0,40.0,45.0],
            "visualization_checkpoint_count":4,
            "visualization_ready":True,
            "Day40_reference_comparison":reference_rows[0],
            "Day45_reference_comparison":reference_rows[1],
            "new_scientific_accuracy_threshold_defined":False,
            "historical_reference_replaced":False,
            "canonical_state_mutated":False,
            "trajectory_class":"CONTROLLED_NONCANONICAL_WHOLE_SYSTEM_SHADOW_TRAJECTORY",
            "INT_VIS_A1_integrated_3D_visualization_authorized":True,
            "longer_horizon_validation_authorized":False,
            "production_pressure_refresh_cadence_selected":False,
            "integrated_GPU_runtime_production_authorized":False,
            "P4_authorized":False,
            "final_state_file":FINAL_STATE,
            "final_state_sha256":hashlib.sha256(final_bytes).hexdigest(),
        }

        decision={
            "milestone":M,
            "status":PASS,
            "controlled_whole_system_integration_executed":True,
            "five_day_controller_boundaries_executed":[35.0,40.0,45.0],
            "whole_system_chain":{
                "pressure_flow":"EXACT_FV_DARCY",
                "streamline_geometry":"EXACT_POLLOCK",
                "time_of_flight":"EXACT_TOF",
                "transport":"HYBRID10_PROPOSAL_PLUS_EXACT_E37A_FALLBACK",
                "conservation":"EXACT_COMPONENT_MASS_BUDGET_PLUS_BOX_PROJECTION",
                "mapback":"SINGLE_COMMON_E37A_MAPBACK",
                "capillary":"CONSERVATIVE_CARTESIAN_REDISTRIBUTION",
            },
            "next_milestone":{
                "name":"POSTV16-AV4-PIVOT-GPU-HYB-INT-VIS-A1",
                "purpose":"Generate integrated 3D pressure, pressure-change, saturation/CO2-mass, streamline, TOF, and controller-event figures from Day30/35/40/45 checkpoints.",
                "authorized":True,
            },
            "longer_horizon_validation_authorized":False,
            "production_pressure_refresh_cadence_selected":False,
            "P4_authorized":False,
        }

        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        (out/DECISION).write_text(json.dumps(decision,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        write_csv(out/STEPS,step_rows)
        write_csv(out/REFRESHES,refresh_rows)
        write_csv(out/CAPACITY,capacity_rows)
        write_csv(out/CONTROLLER,controller_rows)
        write_csv(out/ROUTES,route_rows)
        write_csv(out/REFERENCE,reference_rows)
        write_csv(out/CHECKPOINTS,checkpoint_rows)
        write_csv(out/GATES,gates)
        write_csv(out/MANIFEST,[
            {"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size}
            for p in sorted(out.iterdir()) if p.is_file() and p.name!=MANIFEST
        ])

        print("="*202)
        print(M,"PASS")
        print("Main spine phase                            : CONTROLLED WHOLE-SYSTEM INTEGRATION")
        print("Window                                      : Day30 -> Day45")
        print("Scheduled refreshes                         : Day30 / Day35 / Day40 / Day45")
        print("Accepted transport transitions              :",len(step_rows))
        print("Cumulative Hybrid / exact fallback uses     :",total_hybrid_routes,"/",total_exact_fallback_routes)
        print("Final cumulative mass residual kg           :",cumulative_residual)
        print("Visualization checkpoints ready             : Day30 / Day35 / Day40 / Day45")
        print("INT-VIS-A1 integrated 3D visualization      : AUTHORIZED")
        print("Longer-horizon validation                   : NOT YET AUTHORIZED")
        print("Production activation                       : False")
        print("P4 authorized                               : False")
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
            "Day30_parent_sha256_before":parent_sha_before,
            "controlled_whole_system_integration_executed":False,
            "INT_VIS_A1_integrated_3D_visualization_authorized":False,
            "longer_horizon_validation_authorized":False,
            "production_pressure_refresh_cadence_selected":False,
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
    a=ap.parse_args()
    if a.self_test:
        selftest(a.project_root.resolve())
        raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))
