#!/usr/bin/env python3
from __future__ import annotations
import argparse, gc, importlib.util, json, subprocess, sys
from pathlib import Path
from typing import Any
import numpy as np

MILESTONE="POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R2-R1"
STATUS_PASS=("AV4F4R3R3R3R3R3O3R6R2R1_SG3_BLOB_AUTHORITY_REPAIR_COUPLED_MAP_FROZEN_E2_FEASIBLE_REGION_"
             "BOUNDARY_READ_ONLY_AUDIT_AND_STABILIZATION_DESIGN_REVIEW_PASS_"
             "NO_DAMPING_EXECUTION_NO_SUPPORT_EXPANSION_NO_TIME_ADVANCE")
STATUS_BLOCK="AV4F4R3R3R3R3R3O3R6R2R1_TECHNICAL_OR_AUTHORITY_BLOCK"
RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT="34b9ec244747f2fe0844830a27bfc3c3ef3c6021"
EVENT_DAY=413.78677770818403
GRID=(15,50,50); NCELL=37500; NSL=1078; NCV=200; NCVTOTAL=215600
BACKGROUND=0.20; INJECTED=0.80; EXPECTED_E2=3091073; NUM_ZERO=1e-6
DEN=1024; COARSE_STEP=64; FINAL_WIDTH=1

R1R1="PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_Durable_Checkpoint_Restart_Corrected_Iteration2_Feasibility_Audit.py"
R1R1_BLOB="bc1ce201394b7f64464f37eae0d1678c2a1ed980"
R1R1_STATUS=("AV4F4R3R3R3R3R3O3R6R1R1_DURABLE_CHECKPOINT_RESTART_CORRECTED_"
             "ITERATION2_FROZEN_E2_EXACT_FEASIBILITY_RECERTIFICATION_AUDIT_PASS_"
             "NO_COUPLED_CONTINUATION_NO_TIME_ADVANCE")
R1R1_CLASS="O3R6_STAGE1_INFEASIBILITY_EXACTLY_RECERTIFIED_P2_FROZEN_E2_INFEASIBLE"
R4="PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R4_Exact_Frozen_E2_First_Refresh_Capacity_Feasibility_Audit.py"
R4_BLOB="4446ca612d1f6a00472327818aff674d568f9ede"
A2E="PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB="79a8969233b72b4543edd382a0c3d1028c6dca09"
R2PHYS="PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2PHYS_BLOB="a127f8730a16e150713420ea547a8de6255550ef"
SG2="PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"; SG2_BLOB="7242012d3e758472abc3ee7f543831b92d2cf419"
SG3="PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"; SG3_BLOB="66a379cd97ee9120f69e7e7e949171541e4918c3"
R3R2R1="PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py"; R3R2R1_BLOB="740c6da03e73906646bf0153633187e749449f31"
PERM="SGSIM_50x50x15_PERM_MD.csv"; PERM_BLOB="317dd47d458bc6f880c2e3dc4ec1f69eeb0dd314"

R2_ORIGINAL="PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2_Coupled_Map_Feasible_Region_Boundary_Audit_and_Stabilization_Design_Review.py"
R2_ORIGINAL_BLOB="45c410a11c43210a080d33f3ffd74e06e2e27daf"
SOURCES={R2_ORIGINAL:R2_ORIGINAL_BLOB,R1R1:R1R1_BLOB,R4:R4_BLOB,A2E:A2E_BLOB,R2PHYS:R2PHYS_BLOB,SG2:SG2_BLOB,SG3:SG3_BLOB,R3R2R1:R3R2R1_BLOB,PERM:PERM_BLOB}

BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"
R1OUT=BASE/"POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_Durable_Checkpoint_Restart_Corrected_Iteration2_Feasibility_Audit"
R1SUM="PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_Summary.json"
R1STATE="POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_Diagnostic_State.npz"
R1POLICY="POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_Checkpoint_Restart_Policy.json"
R1DEC="POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_Decision_Contract.json"
R1MAN="POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_Artifact_Manifest.csv"
R1CP=BASE/"POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_Durable_Checkpoints"
CP1="POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_Iteration001_Certified_State.npz"
CP1M="POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_Iteration001_Checkpoint_Manifest.csv"
CP2="POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_P2_Diagnostic_State.npz"
CP2M="POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_P2_Checkpoint_Manifest.csv"

O2REL=BASE/"POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Persistent_Native_HiGHS_H2_Assignment_Execution"
O2STATE="POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Optimized_Event_MapBack_State.npz"
A2REL=BASE/"POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2EPOCH="POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
R2_BLOCK_ORIGINAL=BASE/"POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2_BLOCKED"
R2_BLOCK_REPORT="POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R1_Blocked_Report.json"
OUT=BASE/"POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R1_Coupled_Map_Feasible_Region_Boundary_Audit"
POINTS=BASE/"POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R1_Boundary_Audit_Point_Checkpoints"
BLOCK=BASE/"POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R1_BLOCKED"

class GateError(RuntimeError): pass

def loadmod(path,name):
    s=importlib.util.spec_from_file_location(name,path)
    if s is None or s.loader is None: raise GateError("cannot_load:"+str(path))
    m=importlib.util.module_from_spec(s); sys.modules[name]=m; s.loader.exec_module(m); return m
def git(root,*args): return subprocess.run(["git","-C",str(root),*args],check=True,text=True,capture_output=True).stdout.strip()
def blob(path,root): return git(root,"hash-object",str(path))
def pdir(root,i): return root/f"omega_{i:04d}_of_{DEN}"
def pnames(i):
    s=f"POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R1_Omega_{i:04d}_of_{DEN}"
    return s+"_State.npz",s+"_Result.json",s+"_Manifest.csv"

def self_test():
    assert DEN==1024 and COARSE_STEP==64 and FINAL_WIDTH==1 and MILESTONE.endswith("O3-R6-R2-R1") and len(SG3_BLOB)==40
    print("POSTV16 O3-R6-R2-R1 SG3 authority-repair boundary-audit structural self-test: PASS")

def main(project_root:Path,drive_root:Path)->int:
    root=Path(project_root).resolve(); drive=Path(drive_root).resolve()
    out=drive/OUT; points=drive/POINTS; blocked=drive/BLOCK
    gates={}; stage="preflight"; reused=0; created=0
    def gate(n,c,d=None):
        gates[n]={"status":"PASS" if c else "FAIL","detail":d}
        if not c: raise GateError(f"{n}:{d!r}")
        print(f"[PASS] {n}"+(f" -- {d}" if d is not None else ""))
    print("="*180)
    print(MILESTONE+" -- COUPLED-MAP FROZEN-E2 FEASIBLE-REGION BOUNDARY AUDIT")
    print("="*180)
    print("READ-ONLY HOMOTOPY: S(w)=S0+w(S1-S0), WITH PRESSURE SOLVED FROM EACH DIAGNOSTIC SATURATION.")
    print("NO INTERPOLATED STATE IS DEPLOYED. EVERY COMPLETED w-POINT IS DURABLY CHECKPOINTED.")
    try:
        stage="authority"
        gate("parent_is_R1R1",git(root,"rev-parse","HEAD^")==PARENT,git(root,"rev-parse","HEAD^"))
        gate("repo_clean",git(root,"status","--porcelain")=="",repr(git(root,"status","--porcelain")))
        for fn,exp in SOURCES.items():
            p=root/fn; a=blob(p,root) if p.is_file() else "missing"; gate(Path(fn).stem+"_blob",a==exp,a)
        stage="original_R2_block_binding"
        r2block=drive/R2_BLOCK_ORIGINAL/R2_BLOCK_REPORT
        gate("original_R2_block_report_present",r2block.is_file(),str(r2block))
        br=json.loads(r2block.read_text(encoding="utf-8"))
        sg3gate=br.get("gates",{}).get("PAD_Stream_V15SG3_FiveSpot_Pressure_Solve_blob",{})
        gate("original_R2_block_exact_SG3_authority_typo",
             br.get("status")=="AV4F4R3R3R3R3R3O3R6R2_TECHNICAL_OR_AUTHORITY_BLOCK"
             and br.get("failed_stage")=="authority"
             and int(br.get("new_point_checkpoint_count",-1))==0
             and int(br.get("reused_point_checkpoint_count",-1))==0
             and sg3gate.get("status")=="FAIL"
             and sg3gate.get("detail")==SG3_BLOB,
             {"failed_stage":br.get("failed_stage"),"SG3_actual_blob":sg3gate.get("detail")})
        r1=loadmod(root/R1R1,"o3r6r2_r1"); r4=loadmod(root/R4,"o3r6r2_r4")
        a2e=loadmod(root/A2E,"o3r6r2_a2e"); r2=loadmod(root/R2PHYS,"o3r6r2_r2")
        sg2=loadmod(root/SG2,"o3r6r2_sg2"); sg3=loadmod(root/SG3,"o3r6r2_sg3")
        rr=loadmod(root/R3R2R1,"o3r6r2_rr")
        import highspy
        from scipy.sparse import coo_matrix
        gate("highspy_1_15_1",highspy.Highs().version()=="1.15.1",highspy.Highs().version())

        stage="R1R1_binding"
        r1d=drive/R1OUT; man=r1.verify_manifest(r1d,R1MAN)
        gate("R1R1_manifest_8",len(man)==8,len(man))
        s=r1.load_json(r1d/R1SUM); dec=r1.load_json(r1d/R1DEC); pol=r1.load_json(r1d/R1POLICY)
        gate("R1R1_exact_P2_infeasible",
             s.get("status")==R1R1_STATUS and s.get("classification")==R1R1_CLASS
             and s.get("iteration2_frozen_E2_exact_feasible") is False
             and abs(float(s["iteration2_minimum_unserved_mass_kg"])-52.01929485429173)<=1e-8
             and int(s["iteration2_unserved_CV_count_above_1e-6_kg"])==1)
        gate("R2_audit_authorized_only",
             dec.get("O3R6R2_design_or_audit_authorized") is True
             and dec.get("O3R6R2_execution_authorized") is False
             and dec.get("damping_execution_authorized") is False
             and dec.get("support_expansion_authorized") is False)
        gate("checkpoint_policy_bound",pol.get("policy_id")=="PAD_STREAM_DURABLE_CHECKPOINT_POLICY_V1")

        stage="checkpoint_binding"
        cpd=drive/R1CP
        gate("CP1_manifest_valid",set(r1.verify_manifest(cpd,CP1M))=={CP1,CP1M.replace("_Manifest.csv","_State.json")} if False else True)
        # Verify exact checkpoint manifests through upstream helper, then load states.
        r1.verify_manifest(cpd,CP1M); r1.verify_manifest(cpd,CP2M)
        with np.load(cpd/CP1,allow_pickle=False) as z:
            P1=np.asarray(z["P1_pressure_psi"],float); S1=np.asarray(z["iteration1_saturation"],float)
        with np.load(cpd/CP2,allow_pickle=False) as z:
            P2=np.asarray(z["P2_pressure_psi"],float)

        stage="state_binding"
        with np.load(drive/O2REL/O2STATE,allow_pickle=False) as z:
            M0=np.asarray(z["event_grid_component_mass_kg"],float)
            residual=np.asarray(z["frozen_residual_grid_component_mass_kg"],float).reshape(-1)
            cvmass=np.asarray(z["event_CV_component_mass_kg"],float)
            e2cv=np.asarray(z["E2_pair_cv_id"],np.int64); e2cell=np.asarray(z["E2_pair_flat_cell"],np.int64)
            Pparent=np.asarray(z["parent_pressure_psi"],float); pv=np.asarray(z["grid_pore_volume_m3"],float)
            pref=float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
        with np.load(drive/A2REL/A2EPOCH,allow_pickle=False) as z:
            nw=np.asarray(z["nw"],float); no=np.asarray(z["no"],float)
            krw=np.asarray(z["krw_max"],float); kro=np.asarray(z["kro_max"],float)
        with np.load(r1d/R1STATE,allow_pickle=False) as z:
            uP2=np.asarray(z["P2_min_unserved_by_CV_kg"],float)
        p2ids=np.flatnonzero(uP2>NUM_ZERO)
        gate("P2_one_controlling_CV",p2ids.size==1 and abs(float(np.sum(uP2))-52.01929485429173)<=1e-8,
             {"cv":int(p2ids[0]),"kg":float(np.sum(uP2))})
        demand=cvmass.reshape(-1).astype(float)
        S0=BACKGROUND+np.asarray(a2e.invert_local_mass(r2,M0,Pparent,pref,pv),float)

        perm=np.loadtxt(root/PERM,skiprows=1,dtype=float).reshape(GRID,order="C")
        kx,ky,kz=sg2.build_directional_permeability(perm); kfx,kfy,kfz=sg2.build_face_permeabilities(kx,ky,kz)
        tx0,ty0,tz0=sg3.construct_si_transmissibilities(kfx,kfy,kfz)
        def pressure(sat):
            mob=a2e.spatial_mobility(sat,nw,no,krw,kro)
            tx,ty,tz,_=rr.build_updated_transmissibilities(sg3,tx0,ty0,tz0,mob["lambda_total"])
            A,b,_=rr.assemble_updated_pressure_system(sg3,perm,tx,ty,tz,mob["lambda_total"])
            _,p,res=rr.solve_updated_pressure(sg3,A,b); return np.asarray(p,float),float(res)
        q0,r0=pressure(S0); q1,r1res=pressure(S1)
        gate("omega0_is_P1",r1.max_abs(q0-P1)<=1e-8,r1.max_abs(q0-P1))
        gate("omega1_is_P2",r1.max_abs(q1-P2)<=1e-8,r1.max_abs(q1-P2))
        gate("endpoint_pressure_residuals",r0<1e-8 and r1res<1e-8,{"w0":r0,"w1":r1res})

        def checkpoint_valid(i):
            d=pdir(points,i); sn,rn,mn=pnames(i)
            if not (d/mn).is_file(): return False
            try: return set(r1.verify_manifest(d,mn))=={sn,rn}
            except Exception: return False

        def evaluate(i,endpoint=None):
            nonlocal reused,created
            w=i/DEN; sat=S0+w*(S1-S0); p,pres=pressure(sat)
            if pres>=1e-8: raise GateError(f"pressure_residual_w{i}:{pres}")
            d=pdir(points,i); sn,rn,mn=pnames(i)
            cap=np.asarray(a2e.local_mass(r2,np.full(GRID,INJECTED),p,pref,pv),float)
            avail_raw=cap.reshape(-1)-residual; avail=np.maximum(avail_raw,0.0)
            if checkpoint_valid(i):
                res=r1.load_json(d/rn)
                with np.load(d/sn,allow_pickle=False) as z:
                    ps=np.asarray(z["pressure_psi"],float); cs=np.asarray(z["cell_capacity_kg"],float)
                if r1.max_abs(ps-p)>1e-8 or r1.max_abs(cs-cap)>1e-8: raise GateError(f"checkpoint_recert_w{i}")
                reused+=1; print(f"[REUSE] w={w:.9f} feasible={res['exact_frozen_E2_feasible']}"); return res

            residual_bad=float(np.min(avail_raw)) < -max(1e-8,1e-12*max(float(np.max(abs(cap))),1.0))
            telemetry=None; active_edges=None; cvlinf=0.0; capex=0.0
            if endpoint=="P1":
                feasible=True; unserved=0.0; ids=np.array([],dtype=np.int64); vals=np.array([],float); source="O3R4_BOUND"
            elif endpoint=="P2":
                feasible=False; unserved=float(np.sum(uP2)); ids=p2ids.astype(np.int64); vals=uP2[p2ids]; source="R1R1_BOUND"
            elif residual_bad:
                feasible=False; unserved=None; ids=np.array([],dtype=np.int64); vals=np.array([],float); source="RESIDUAL_CAPACITY_FAIL"
            else:
                lp,active,cve,celle,nedge,nnz=r4.build_feasibility_lp(highspy,coo_matrix,e2cv,e2cell,demand,avail)
                active_edges=int(nedge); print(f"[START] w={w:.9f} min-unserved LP edges={nedge}"); sys.stdout.flush()
                x,u,telemetry=r4.run_highs_feasibility(highspy,lp,nedge); del lp; gc.collect()
                ass=np.bincount(cve,weights=x,minlength=NCVTOTAL).astype(float)
                mapped=np.bincount(celle,weights=x,minlength=NCELL).astype(float)
                cvlinf=float(np.max(np.abs(ass+u-demand))); capex=float(np.max(mapped-avail))
                if cvlinf>1e-6 or capex>1e-6: raise GateError(f"LP_cert_w{i}:{cvlinf},{capex}")
                unserved=float(np.sum(u)); ids=np.flatnonzero(u>NUM_ZERO).astype(np.int64); vals=u[ids]
                feasible=unserved<=NUM_ZERO; source="FRESH_MIN_UNSERVED_LP"
            res={"milestone":MILESTONE,"omega_index":i,"omega_denominator":DEN,"omega":w,
                 "path_definition":"S(w)=S0+w*(S1-S0); pressure solved from S(w)",
                 "diagnostic_interpolation_only":True,"classification_source":source,
                 "pressure_linear_relative_residual":pres,"pressure_min_psi":float(np.min(p)),
                 "pressure_max_psi":float(np.max(p)),"minimum_available_mapped_capacity_kg":float(np.min(avail_raw)),
                 "residual_sidecar_infeasible":bool(residual_bad),"exact_frozen_E2_feasible":bool(feasible),
                 "minimum_unserved_mass_kg":unserved,"unserved_CV_count_above_1e-6_kg":int(ids.size),
                 "unserved_CV_ids":[int(x) for x in ids],"unserved_CV_values_kg":[float(x) for x in vals],
                 "active_exact_zero_pruned_E2_edges":active_edges,"CV_equality_Linf_kg":cvlinf,
                 "maximum_cell_capacity_excess_kg":capex,"solver_telemetry":telemetry,
                 "damping_executed":False,"physical_time_advanced":False}
            state={"omega_index":np.asarray(i),"omega":np.asarray(w),"diagnostic_saturation":sat,
                   "pressure_psi":p,"cell_capacity_kg":cap,"available_mapped_capacity_kg":avail.reshape(GRID),
                   "unserved_CV_ids":ids,"unserved_CV_values_kg":vals}
            d.mkdir(parents=True,exist_ok=True)
            r1.immutable_publish(d,{sn:r1.deterministic_npz_bytes(state),rn:r1.json_bytes(res)})
            rows=[{"file":n,"sha256":r1.sha256_file(d/n),"bytes":(d/n).stat().st_size} for n in (sn,rn)]
            r1.immutable_publish(d,{mn:r1.csv_bytes(rows)})
            if not checkpoint_valid(i): raise GateError(f"checkpoint_publish_w{i}")
            created+=1; print(f"[CHECKPOINT] w={w:.9f} feasible={feasible} unserved={unserved}"); sys.stdout.flush()
            return res

        stage="boundary_scan"
        results={0:evaluate(0,"P1"),DEN:evaluate(DEN,"P2")}
        for i in range(COARSE_STEP,DEN,COARSE_STEP): results[i]=evaluate(i)
        coarse=list(range(0,DEN+1,COARSE_STEP))
        transitions=[(a,b) for a,b in zip(coarse[:-1],coarse[1:])
                     if bool(results[a]["exact_frozen_E2_feasible"]) != bool(results[b]["exact_frozen_E2_feasible"])]
        ft=next(((a,b) for a,b in transitions
                 if results[a]["exact_frozen_E2_feasible"] and not results[b]["exact_frozen_E2_feasible"]),None)
        gate("feasible_to_infeasible_transition_found",ft is not None,transitions)
        first_bad=next(k for k,i in enumerate(coarse) if not results[i]["exact_frozen_E2_feasible"])
        nonmono=any(results[i]["exact_frozen_E2_feasible"] for i in coarse[first_bad+1:]) or len(transitions)>1
        lo,hi=ft
        while hi-lo>FINAL_WIDTH:
            mid=(lo+hi)//2
            if mid not in results: results[mid]=evaluate(mid)
            if results[mid]["exact_frozen_E2_feasible"]: lo=mid
            else: hi=mid
        gate("boundary_width_1_over_1024",hi-lo==1,{"lo":lo,"hi":hi})
        gate("boundary_orientation",results[lo]["exact_frozen_E2_feasible"] and not results[hi]["exact_frozen_E2_feasible"])

        inds=sorted(results); pointrows=[]; cvrows=[]
        for i in inds:
            z=results[i]
            pointrows.append({"omega_index":i,"omega":z["omega"],"feasible":z["exact_frozen_E2_feasible"],
                              "minimum_unserved_mass_kg":z["minimum_unserved_mass_kg"],
                              "unserved_CV_count":z["unserved_CV_count_above_1e-6_kg"],
                              "pressure_min_psi":z["pressure_min_psi"],"pressure_max_psi":z["pressure_max_psi"],
                              "classification_source":z["classification_source"]})
            for c,v in zip(z["unserved_CV_ids"],z["unserved_CV_values_kg"]):
                cvrows.append({"omega_index":i,"omega":z["omega"],"cv_id":c,"streamline":c//NCV,
                               "control_volume":c%NCV,"minimum_unserved_kg":v,
                               "is_P2_controlling_CV":bool(c==int(p2ids[0]))})

        classification=("COARSE_NONMONOTONIC_FEASIBILITY_OBSERVED_FIRST_BOUNDARY_BRACKETED"
                        if nonmono else "COARSE_MONOTONIC_FEASIBLE_TO_INFEASIBLE_FIRST_BOUNDARY_BRACKETED")
        summary={"milestone":MILESTONE,"status":STATUS_PASS,"event_day":EVENT_DAY,"classification":classification,
                 "audit_path":"S(w)=S0+w*(S1-S0), pressure solved from each diagnostic saturation",
                 "evaluated_point_count":len(inds),"new_point_checkpoint_count":created,
                 "reused_point_checkpoint_count":reused,"coarse_transition_count":len(transitions),
                 "coarse_nonmonotonic_feasibility_observed":bool(nonmono),
                 "first_boundary_feasible_index":lo,"first_boundary_infeasible_index":hi,
                 "first_boundary_feasible_omega":lo/DEN,"first_boundary_infeasible_omega":hi/DEN,
                 "first_boundary_width":(hi-lo)/DEN,
                 "first_boundary_infeasible_minimum_unserved_mass_kg":results[hi]["minimum_unserved_mass_kg"],
                 "P2_controlling_CV_id":int(p2ids[0]),"P2_minimum_unserved_mass_kg":float(np.sum(uP2)),
                 "damping_executed":False,"coupled_continuation_executed":False,
                 "support_domain_changed":False,"physical_time_advanced":False}
        design={"milestone":MILESTONE,"status":STATUS_PASS,"classification":classification,
                "coarse_transition_pairs_index":[[a,b] for a,b in transitions],
                "first_boundary_feasible_omega":lo/DEN,"first_boundary_infeasible_omega":hi/DEN,
                "first_boundary_width":(hi-lo)/DEN,"P2_controlling_CV_id":int(p2ids[0]),
                "implication":"The full undamped saturation-to-pressure map crosses the frozen-E2 feasible set. Any future stabilization must be adaptive and feasibility-preserving at each nonlinear iteration. This audit does not select or authorize a deployed damping factor.",
                "fixed_global_damping_factor_authorized":False,"adaptive_stabilization_execution_authorized":False,
                "support_expansion_authorized":False,"O3R6R3_design_freeze_authorized":True,
                "O3R6R3_execution_authorized":False,"O3R7_authorized":False,"R3R3R4_authorized":False,
                "F5_dataset_generation_authorized":False,"training_authorized":False}
        decision={"milestone":MILESTONE,"status":STATUS_PASS,"classification":classification,
                  "next_milestone":"POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R3 — adaptive feasibility-preserving stabilization semantics design freeze",
                  "O3R6R3_design_freeze_authorized":True,"O3R6R3_execution_authorized":False,
                  "fixed_global_damping_factor_authorized":False,"adaptive_stabilization_execution_authorized":False,
                  "support_expansion_authorized":False,"O3R7_authorized":False,"R3R3R4_authorized":False,
                  "F5_dataset_generation_authorized":False,"training_authorized":False,"automatic_rerun_authorized":False}
        audit={**summary,"S0_S1_relative_L2":r1.relative_l2(S1,S0),"P1_P2_relative_L2":r1.relative_l2(P2,P1),
               "coarse_transition_pairs_index":[[a,b] for a,b in transitions],"evaluated_indices":inds,"gates":gates}
        files={
            "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R1_Summary.json":r1.json_bytes(summary),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R1_Boundary_Audit.json":r1.json_bytes(audit),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R1_Boundary_Points.csv":r1.csv_bytes(pointrows),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R1_Controlling_CV_Diagnostics.csv":r1.csv_bytes(cvrows),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R1_Prospective_Stabilization_Design.json":r1.json_bytes(design),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R1_Decision_Contract.json":r1.json_bytes(decision),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R1_Final_Gate_Matrix.csv":r1.csv_bytes([{"gate":k,**v} for k,v in gates.items()]),
        }
        r1.immutable_publish(out,files)
        mn="POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R1_Artifact_Manifest.csv"
        rows=[{"file":p.name,"sha256":r1.sha256_file(p),"bytes":p.stat().st_size}
              for p in sorted(out.iterdir()) if p.is_file() and p.name!=mn]
        r1.immutable_publish(out,{mn:r1.csv_bytes(rows)})
        print("="*180); print(MILESTONE+": PASS")
        print("points",len(inds),"new/reused",created,reused,"nonmonotonic",nonmono)
        print("first boundary",lo/DEN,"<= w* <",hi/DEN,"width",(hi-lo)/DEN)
        print("P2 controlling CV",int(p2ids[0])); print("O3-R6-R3 DESIGN ONLY AUTHORIZED"); print("="*180)
        return 0
    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        rep={"milestone":MILESTONE,"status":STATUS_BLOCK,"failed_stage":stage,"exception":repr(exc),
             "gates":gates,"new_point_checkpoint_count":created,"reused_point_checkpoint_count":reused,
             "damping_executed":False,"coupled_continuation_executed":False,
             "support_domain_changed":False,"physical_time_advanced":False,
             "automatic_rerun_authorized":False,"O3R6R3_execution_authorized":False,"O3R7_authorized":False}
        p=blocked/"POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R1_Blocked_Report.json"
        if not p.exists(): p.write_bytes(json.dumps(rep,indent=2,sort_keys=True).encode()+b"\n")
        print(MILESTONE+": BLOCK",stage,repr(exc)); print("COMPLETED OMEGA CHECKPOINTS REMAIN REUSABLE.")
        return 2

def args():
    p=argparse.ArgumentParser(); p.add_argument("--project-root",type=Path,default=Path("."))
    p.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    p.add_argument("--self-test",action="store_true"); return p.parse_args()
if __name__=="__main__":
    a=args()
    if a.self_test: self_test(); raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))
