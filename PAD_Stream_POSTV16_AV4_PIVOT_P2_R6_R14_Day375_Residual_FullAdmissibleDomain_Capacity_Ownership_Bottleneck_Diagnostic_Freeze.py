#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,io,json,subprocess,sys
from pathlib import Path
from typing import Any
import numpy as np

M="POSTV16-AV4-PIVOT-P2-R6-R14"
NAME="Day375 Residual Full-Admissible-Domain Capacity and Ownership Bottleneck Diagnostic Freeze"
NEXT="Day375 Residual Bottleneck-Specific Projection/Support Reconciliation Design Freeze"
PASS="AV4PIVOTP2R6R14_DAY375_RESIDUAL_FULL_ADMISSIBLE_DOMAIN_CAPACITY_AND_OWNERSHIP_BOTTLENECK_DIAGNOSTIC_FREEZE_PASS_NO_STATE_MUTATION"
BLOCK="AV4PIVOTP2R6R14_TECHNICAL_OR_AUTHORITY_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="f83e963bf79bcb4007cbd875b2221342bf0501cf"
R13_RUN="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R13_Day375_Residual_ComponentSpecific_Local3D_FaceConnected_Support_Envelope_Design_Freeze.py"
R13_BLOB="360cef05c5c3f54e077d83c0fe6cf310139d2ec8"
R12_RUN="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R12_Day375_Residual_AdjacentLayer_FaceConnected_Lateral_Topology_Design_Freeze.py"
R12_BLOB="7c774e15337518031ea815b805e184b52d23bede"
R11_RUN="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R11_Day375_Residual_BeyondSameLayer_Topology_Design_Freeze.py"
R11_BLOB="a94ce35c8862b7922fca38923bd047ef782fa7c8"
R10_RUN="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R10_Day375_Residual_ThirdStage_SupportExtension_Topology_Design_Freeze.py"
R10_BLOB="dd9124c4cf7ac64ffd9c9e7bb98edf24eb8fba75"
R9_RUN="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R9_Day375_Residual_SecondStage_SupportExtension_Topology_Design_Freeze.py"
R9_BLOB="f45c5c4782dc20b8f860fd04860b7b7369bd1c2a"
R2="PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB="a127f8730a16e150713420ea547a8de6255550ef"
BLOBS={R13_RUN:R13_BLOB,R12_RUN:R12_BLOB,R11_RUN:R11_BLOB,R10_RUN:R10_BLOB,R9_RUN:R9_BLOB,R2:R2_BLOB}

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"
R13=BASE/"POSTV16_AV4_PIVOT_P2_R6_R13_Day375_Residual_ComponentSpecific_Local3D_FaceConnected_Support_Envelope_Design_Freeze"
R12=BASE/"POSTV16_AV4_PIVOT_P2_R6_R12_Day375_Residual_AdjacentLayer_FaceConnected_Lateral_Topology_Design_Freeze"
R11=BASE/"POSTV16_AV4_PIVOT_P2_R6_R11_Day375_Residual_BeyondSameLayer_Topology_Design_Freeze"
R10=BASE/"POSTV16_AV4_PIVOT_P2_R6_R10_Day375_Residual_ThirdStage_SupportExtension_Topology_Design_Freeze"
R9=BASE/"POSTV16_AV4_PIVOT_P2_R6_R9_Day375_Residual_SecondStage_SupportExtension_Topology_Design_Freeze"
R8=BASE/"POSTV16_AV4_PIVOT_P2_R6_R8_R1_Day375_Residual_FrozenDomain_Infeasibility_Localization_and_Minimal_SupportExtension_Design_Freeze"
R7=BASE/"POSTV16_AV4_PIVOT_P2_R6_R7_Day375_Residual_External_Component_Exact_Projection_Semantics_Freeze"
R6=BASE/"POSTV16_AV4_PIVOT_P2_R6_R6_Day375_Residual_External_Component_Projection_Authority_and_Global_State_Closure_Audit"
R5=BASE/"POSTV16_AV4_PIVOT_P2_R6_R5_Controlled_Day375_TerminalSink_FixedExternal_Local_Projection"
D370=BASE/"POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_CompletedComponent_CellMembership_Identity_Repair_and_Controlled_Projection"
A2=BASE/"POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
OUT=BASE/"POSTV16_AV4_PIVOT_P2_R6_R14_Day375_Residual_FullAdmissibleDomain_Capacity_Ownership_Bottleneck_Diagnostic_Freeze"
BLK=BASE/"POSTV16_AV4_PIVOT_P2_R6_R14_BLOCKED"

UNRES=[0,3,31,65,79]; GRID=(15,50,50); NZ,NY,NX=GRID; NCELL=37500; NCV=200; NCVT=1078*200
BG=.20; MAXSG=.60; CTOL=1e-7; CVTOL=1e-7; LTOL=1e-6; STOL=1e-10; RTOL=1e-8
R5SHA="1553445022f7267d7802f8833d5440d7521433a4cd8b7c06652cffeb6d693e57"

class GateError(RuntimeError): pass
def gt(r,*a): return subprocess.check_output(["git","-C",str(r),*a],text=True).strip()
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()
def js(p): return json.loads(Path(p).read_text())
def csvr(p):
    with open(p,newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def csvb(rows):
    if not rows:return b""
    fs=[]; [fs.append(k) for r in rows for k in r if k not in fs]
    s=io.StringIO(newline=""); w=csv.DictWriter(s,fieldnames=fs,lineterminator="\n");w.writeheader();w.writerows(rows);return s.getvalue().encode()
def jb(x): return (json.dumps(x,indent=2,sort_keys=True)+"\n").encode()
def mod(p,n):
    sp=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(sp);sys.modules[n]=m;sp.loader.exec_module(m);return m
def man(d,n):
    rows=csvr(d/n)
    for r in rows:
        p=d/r["file"]
        if not p.is_file() or sha(p)!=r["sha256"] or p.stat().st_size!=int(r["bytes"]): raise GateError("manifest:"+r["file"])
def h2(cells,s0):
    o=set()
    for c in np.asarray(cells).reshape(-1):
        k=c//2500; rem=c%2500; j=rem//50; i=rem%50
        for dj in range(-2,3):
            for di in range(-2,3):
                if 1<=abs(di)+abs(dj)<=2 and 0<=j+dj<50 and 0<=i+di<50:
                    x=int(k*2500+(j+dj)*50+i+di)
                    if x not in s0:o.add(x)
    return o
def emap(rows):
    d={}
    for r in rows:
        if r.get("flat_cell","")!="": d.setdefault((int(r["execution_group_id"]),int(r["component_id"])),set()).add(int(r["flat_cell"]))
    return d
def selftest():
    assert UNRES==[0,3,31,65,79] and NCELL==37500
    print("POSTV16 AV4 PIVOT P2-R6-R14 structural self-test: PASS")

def main(root,drive):
    root=Path(root); drive=Path(drive); out=drive/OUT; blk=drive/BLK; stage="preflight"; gates=[]
    def gate(n,x,d=None):
        ok=bool(x);gates.append({"stage":stage,"gate":n,"pass":ok,"detail":"" if d is None else repr(d)})
        print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"))
        if not ok: raise GateError(n)
    try:
        if (out/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R14_Summary.json").is_file(): return 0
        gate("no_preexisting_BLOCK",not (blk/"POSTV16_AV4_PIVOT_P2_R6_R14_Blocked_Report.json").exists())
        stage="repo"
        gate("branch",gt(root,"branch","--show-current")==BRANCH);gate("parent",gt(root,"rev-parse","HEAD^")==PARENT)
        gate("clean",gt(root,"status","--porcelain")=="")
        for f,b in BLOBS.items(): gate(Path(f).stem+"_blob",gt(root,"hash-object",str(root/f))==b)

        stage="R13"
        s13=js(drive/R13/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R13_Summary.json")
        d13=js(drive/R13/"POSTV16_AV4_PIVOT_P2_R6_R13_Decision_Contract.json")
        man(drive/R13,"POSTV16_AV4_PIVOT_P2_R6_R13_Artifact_Manifest.csv")
        ca=csvr(drive/R13/"POSTV16_AV4_PIVOT_P2_R6_R13_Component_Envelope_Selection_Audit.csv")
        dc=csvr(drive/R13/"POSTV16_AV4_PIVOT_P2_R6_R13_PostT5AL_Localized_Deficient_CVs.csv")
        gate("R13_status",s13["status"]=="AV4PIVOTP2R6R13_DAY375_RESIDUAL_COMPONENT_SPECIFIC_LOCAL_3D_FACE_CONNECTED_SUPPORT_ENVELOPE_DESIGN_FREEZE_PASS_NO_STATE_MUTATION")
        gate("R13_unresolved",s13["unresolved_after_T6E_group_ids"]==UNRES)
        gate("R13_zero_T6E",s13["T6E_exact_feasible_group_count"]==0 and s13["T6E_candidate_terminal_sink_membership_count"]==0)
        gate("R13_counts",len(ca)==5 and len(dc)==22)
        gate("R14_authority",d13["P2_R6_R14_authorized"] and d13["P2_R6_R14_full_admissible_domain_bottleneck_diagnostic_authorized"])

        stage="inputs"
        # support rows
        xs=[
            emap(csvr(drive/R8/"POSTV16_AV4_PIVOT_P2_R6_R8_R1_Frozen_Compact_Support_Extension.csv")),
            emap(csvr(drive/R9/"POSTV16_AV4_PIVOT_P2_R6_R9_Frozen_SecondStage_Support_Extension.csv")),
            emap(csvr(drive/R10/"POSTV16_AV4_PIVOT_P2_R6_R10_Frozen_ThirdStage_Support_Extension.csv")),
            emap(csvr(drive/R11/"POSTV16_AV4_PIVOT_P2_R6_R11_Frozen_Vertical_Support_Extension.csv")),
            emap(csvr(drive/R12/"POSTV16_AV4_PIVOT_P2_R6_R12_Frozen_AdjacentLayerLateral_Support_Extension.csv")),
        ]
        gr=csvr(drive/R7/"POSTV16_AV4_PIVOT_P2_R6_R7_Prospective_Execution_Groups.csv")
        tr=csvr(drive/R7/"POSTV16_AV4_PIVOT_P2_R6_R7_Frozen_Target_CVs.csv")
        cvrows=csvr(drive/R6/"POSTV16_AV4_PIVOT_P2_R6_R6_Residual_CV_Component_Ownership.csv")
        gmeta={int(r["execution_group_id"]):r for r in gr}
        c2g={}
        for gid,r in gmeta.items():
            for c in [int(x) for x in r["R6R6_component_ids"].split(";") if x]: c2g[c]=gid
        cv2c={int(r["cv_id"]):int(r["component_id"]) for r in cvrows}
        cc={c:np.asarray(sorted(v for v,o in cv2c.items() if o==c),dtype=np.int64) for c in range(158)}
        tgt={c:set(int(r["cv_id"]) for r in tr if int(r["component_id"])==c) for c in range(158)}

        st=np.load(drive/R5/"POSTV16_AV4_PIVOT_P2_R6_R5_Provisional_LocalRepaired_Day375_State.npz")
        pair_cv=np.asarray(st["existing_pair_cv"],dtype=np.int64).reshape(-1);pair_cell=np.asarray(st["existing_pair_cell"],dtype=np.int64).reshape(-1)
        pair_val=np.asarray(st["locally_repaired_existing_pair_contribution_kg"],float).reshape(-1)
        provisional=np.asarray(st["provisional_grid_component_mass_kg"],float).reshape(-1)
        r5cv=np.asarray(st["local_component_cv"],dtype=np.int64).reshape(-1);r5hcv=np.asarray(st["local_halo_cv"],dtype=np.int64).reshape(-1)
        r5hcell=np.asarray(st["local_halo_cell"],dtype=np.int64).reshape(-1);r5hmass=np.asarray(st["local_halo_contribution_kg"],float).reshape(-1)
        pstate=np.asarray(st["parent_pressure_psi"],float); st.close()
        gate("R5_sha",sha(drive/R5/"POSTV16_AV4_PIVOT_P2_R6_R5_Provisional_LocalRepaired_Day375_State.npz")==R5SHA)

        old=np.load(drive/D370/"POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_Repaired_Day370_State.npz")
        oldgrid=np.asarray(old["grid_component_mass_kg"],float).reshape(-1);fhcv=np.asarray(old["halo_cv"],dtype=np.int64).reshape(-1);fhcell=np.asarray(old["halo_cell"],dtype=np.int64).reshape(-1);old.close()
        ky=np.unique(fhcv*NCELL+fhcell);fhcv=ky//NCELL;fhcell=ky%NCELL;fdom=set(np.unique(fhcell).tolist())
        ep=np.load(drive/A2/"POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz")
        pressure=np.asarray(ep["refreshed_pressure_psi"],float);pv=np.asarray(ep["pore_volume_m3"],float);pref=float(np.asarray(ep["reference_gas_pressure_pa"]).reshape(()));ep.close()
        gate("pressure",np.max(np.abs(pressure-pstate))<=1e-12)
        r2=mod(root/R2,"r14r2");rho=np.asarray(r2.gas_density_from_state(np.full(GRID,BG+MAXSG),pressure,pref),float);cap=(pv*rho*MAXSG).reshape(-1)
        cur=np.bincount(pair_cv,weights=pair_val,minlength=NCVT)+np.bincount(r5hcv,weights=r5hmass,minlength=NCVT)
        recon=oldgrid+np.bincount(pair_cell,weights=pair_val,minlength=NCELL)+np.bincount(r5hcell,weights=r5hmass,minlength=NCELL)
        gate("recon",np.max(np.abs(recon-provisional))<=CTOL);gate("ledger",abs(provisional.sum()-(oldgrid.sum()+cur.sum()))<=LTOL)
        s0=set(np.unique(pair_cell).tolist());r5fixed=set(np.unique(np.r_[pair_cell[np.isin(pair_cv,r5cv)],r5hcell]).tolist())

        frontier={};base={}
        for c in range(158):
            cvs=cc[c]; s0c=np.unique(pair_cell[np.isin(pair_cv,cvs)])
            frontier[c]=set(x for x in h2(s0c,s0) if x in fdom)
            m=np.isin(fhcv,cvs);base[c]=sorted(set((int(a),int(b)) for a,b in zip(fhcv[m],fhcell[m])))
        pool={}
        owners={}
        for c in range(158):
            gid=c2g[c];p=set(frontier[c]);p.update(h for _,h in base[c])
            for z in xs:p.update(z.get((gid,c),set()))
            pool[c]=p
            for x in p:owners.setdefault(int(x),set()).add(gid)

        pos={(int(r["execution_group_id"]),int(r["component_id"])):float(r["post_T5AL_positive_support_deficit_kg"]) for r in ca}
        neg={(int(r["execution_group_id"]),int(r["component_id"])):float(r["post_T5AL_negative_slack_kg"]) for r in ca}

        from scipy.optimize import linprog
        from scipy import sparse
        def build(cids,poolcells,elig,relax):
            cvs=np.asarray(sorted(v for c in cids for v in cc[c]),dtype=np.int64);pm=np.isin(pair_cv,cvs);pi=np.flatnonzero(pm&(np.abs(pair_val)>STOL))
            xcv=pair_cv[pi];xcell=pair_cell[pi];x0=pair_val[pi]
            E=sorted(set(v for c in cids for v in (tgt[c] if elig=="target" else cc[c].tolist())));Es=set(E);P=sorted(set(poolcells));Ps=set(P)
            bi=sorted(set((cv,h) for c in cids for cv,h in base[c] if cv not in Es or h not in Ps))
            nx,nb,ny,nq=len(pi),len(bi),len(E),len(P);ncv=len(cvs);ob=nx;oy=ob+nb;oq=oy+ny;nv=oq+nq;cr={int(v):i for i,v in enumerate(cvs)}
            er=[];ec=[];ev=[]
            for q,v in enumerate(xcv):er.append(cr[int(v)]);ec.append(q);ev.append(1.)
            for q,(v,h) in enumerate(bi):er.append(cr[v]);ec.append(ob+q);ev.append(1.)
            for q,v in enumerate(E):er.append(cr[v]);ec.append(oy+q);ev.append(1.)
            for q in range(ny):er.append(ncv);ec.append(oy+q);ev.append(1.)
            for q in range(nq):er.append(ncv);ec.append(oq+q);ev.append(-1.)
            Aeq=sparse.coo_matrix((ev,(er,ec)),shape=(ncv+1,nv)).tocsr();beq=np.r_[cur[cvs],0.]
            loc=sorted(set(xcell.tolist())|set(h for _,h in bi)|set(P));lr={c:i for i,c in enumerate(loc)};rr=[];co=[];vv=[]
            for q,c in enumerate(xcell):rr.append(lr[int(c)]);co.append(q);vv.append(1.)
            for q,(v,c) in enumerate(bi):rr.append(lr[c]);co.append(ob+q);vv.append(1.)
            for q,c in enumerate(P):rr.append(lr[c]);co.append(oq+q);vv.append(1.)
            Ac=sparse.coo_matrix((vv,(rr,co)),shape=(len(loc),nv)).tocsr()
            fixed=oldgrid+np.bincount(pair_cell[~pm],weights=pair_val[~pm],minlength=NCELL)+np.bincount(r5hcell,weights=r5hmass,minlength=NCELL)
            li=np.asarray(loc,dtype=np.int64);Aub=sparse.vstack([Ac,-Ac]);bub=np.r_[cap[li]-fixed[li],fixed[li]]
            bd=[]
            for v in x0:
                bd.append((None,None) if relax else ((0,None) if v>STOL else ((None,0) if v<-STOL else (0,0))))
            bd += [(0,None)]*(nb+ny+nq)
            return dict(Aeq=Aeq,beq=beq,Aub=Aub,bub=bub,bounds=bd,nv=nv,ncv=ncv,Ac=Ac,li=li,fixed=fixed)
        def solve(d):
            lp=linprog(np.zeros(d["nv"]),A_ub=d["Aub"],b_ub=d["bub"],A_eq=d["Aeq"],b_eq=d["beq"],bounds=d["bounds"],method="highs",options={"presolve":True})
            if not lp.success:return False,lp,None,None,None
            z=np.asarray(lp.x);cvres=np.asarray(d["Aeq"][:d["ncv"]]@z-d["beq"][:d["ncv"]]).ravel();cm=d["fixed"][d["li"]]+np.asarray(d["Ac"]@z).ravel()
            mcv=float(np.max(np.abs(cvres)));lo=max(0.,-float(np.min(cm)));hi=max(0.,float(np.max(cm-cap[d["li"]])))
            return mcv<=CVTOL and lo<=CTOL and hi<=CTOL,lp,mcv,lo,hi

        stage="diagnostic"
        diag=[];caps=[];clsrows=[];counts={}
        cells=np.arange(NCELL,dtype=np.int64)
        for gid in UNRES:
            cids=[int(x) for x in gmeta[gid]["R6R6_component_ids"].split(";") if x];gp=set(x for c in cids for x in pool[c]);gcvs=np.asarray(sorted(v for c in cids for v in cc[c]))
            pm=np.isin(pair_cv,gcvs);fixed=oldgrid+np.bincount(pair_cell[~pm],weights=pair_val[~pm],minlength=NCELL)+np.bincount(r5hcell,weights=r5hmass,minlength=NCELL);room=cap-fixed
            strict=set(int(c) for c in cells[room>RTOL] if int(c) not in s0 and int(c) not in r5fixed and int(c) not in owners)
            relaxed=set(int(c) for c in cells[room>RTOL] if int(c) not in s0 and int(c) not in r5fixed)
            sp=gp|strict;rp=gp|relaxed
            pd=sum(max(0.,pos.get((gid,c),0.)) for c in cids);ns=sum(max(0.,neg.get((gid,c),0.)) for c in cids)
            variants=[("V0_CURRENT_SUPPORT_SHARED_POOL",gp,"target",False),("V1_STRICT_FULL_UNOWNED_DOMAIN",sp,"target",False),("V2_OWNERSHIP_RELAXED_FULL_DOMAIN",rp,"target",False),("V3_ALL_GROUP_CVS_H2_ELIGIBLE",rp,"all",False),("V4_SIGN_RELAXED_EXISTING_PAIRS",rp,"all",True)]
            res={}
            for vn,pp,ee,rr in variants:
                d=build(cids,pp,ee,rr);ok,lp,mcv,lo,hi=solve(d);res[vn]=ok
                diag.append({"execution_group_id":gid,"variant":vn,"pool_cell_count":len(pp),"eligibility":ee,"sign_relaxed":rr,"exact_feasible":ok,"HiGHS_status":int(lp.status),"HiGHS_message":str(lp.message),"max_CV_residual_kg":mcv,"max_cell_lower_violation_kg":lo,"max_cell_upper_violation_kg":hi})
            cr=sum(max(0.,room[c]) for c in gp);sr=sum(max(0.,room[c]) for c in strict);rrm=sum(max(0.,room[c]) for c in relaxed)
            phys=pd>RTOL and cr+rrm+RTOL<pd
            if res["V0_CURRENT_SUPPORT_SHARED_POOL"]:cl="COMPONENT_POOL_OWNERSHIP_SEMANTICS_BOTTLENECK"
            elif res["V1_STRICT_FULL_UNOWNED_DOMAIN"]:cl="LOCAL_SUPPORT_REACH_TOPOLOGY_BOTTLENECK"
            elif res["V2_OWNERSHIP_RELAXED_FULL_DOMAIN"]:cl="INTERGROUP_OWNERSHIP_EXCLUSION_BOTTLENECK"
            elif res["V3_ALL_GROUP_CVS_H2_ELIGIBLE"]:cl="TARGET_CV_H2_ELIGIBILITY_BOTTLENECK"
            elif res["V4_SIGN_RELAXED_EXISTING_PAIRS"]:cl="EXISTING_PAIR_SIGN_PRESERVATION_BOTTLENECK"
            elif phys:cl="PHYSICAL_CAPACITY_BOTTLENECK"
            else:cl="DEEPER_PROJECTION_FORMULATION_BOTTLENECK"
            counts[cl]=counts.get(cl,0)+1
            caps.append({"execution_group_id":gid,"positive_support_deficit_kg":pd,"negative_slack_kg":ns,"current_pool_cells":len(gp),"current_pool_room_kg":cr,"strict_unowned_cells":len(strict),"strict_unowned_room_kg":sr,"ownership_relaxed_cells":len(relaxed),"ownership_relaxed_room_kg":rrm,"aggregate_physical_capacity_shortfall":phys})
            clsrows.append({"execution_group_id":gid,"bottleneck_classification":cl,**{k:v for k,v in res.items()},"aggregate_physical_capacity_shortfall":phys})
        gate("five_classified",len(clsrows)==5)

        stage="publish";out.mkdir(parents=True)
        (out/"POSTV16_AV4_PIVOT_P2_R6_R14_Projection_Formulation_Diagnostic_Matrix.csv").write_bytes(csvb(diag))
        (out/"POSTV16_AV4_PIVOT_P2_R6_R14_FullDomain_Capacity_Audit.csv").write_bytes(csvb(caps))
        (out/"POSTV16_AV4_PIVOT_P2_R6_R14_Bottleneck_Classification.csv").write_bytes(csvb(clsrows))
        C="R6R14_FULL_ADMISSIBLE_DOMAIN_BOTTLENECK_DIAGNOSTIC_COMPLETE_BOTTLENECK_SPECIFIC_RECONCILIATION_DESIGN_REQUIRED"
        summ={"milestone":M,"name":NAME,"status":PASS,"classification":C,"input_unresolved_group_ids":UNRES,"input_unresolved_group_count":5,"diagnostic_variant_count_per_group":5,"diagnostic_LP_count":len(diag),"bottleneck_classification_counts":counts,"group_bottleneck_classifications":{str(r["execution_group_id"]):r["bottleneck_classification"] for r in clsrows},"state_mutation_executed":False,"support_growth_executed":False,"pressure_refresh_executed":False,"time_advance_executed":False,"P3_authorized":False}
        dec={"milestone":M,"status":PASS,"classification":C,"P2_R6_R15_authorized":True,"P2_R6_R15_name":NEXT,"P2_R6_R15_projection_execution_authorized":False,"P2_R6_R15_bottleneck_specific_reconciliation_design_authorized":True,"P2_R6_R15_must_bind_R6R13_local_3d_envelope_contract":True,"P2_R6_R15_must_bind_R6R14_bottleneck_classification_contract":True,"support_growth_execution_authorized_now":False,"new_H2_endpoint_execution_authorized_now":False,"pressure_refresh_authorized":False,"time_advance_authorized":False,"P3_authorized":False,"P4_authorized":False,"P5_training_authorized":False}
        con={"milestone":M,"name":NAME,"status":PASS,"classification":C,"diagnostic_freeze_only":True,"diagnostic_order":["V0_CURRENT_SUPPORT_SHARED_POOL","V1_STRICT_FULL_UNOWNED_DOMAIN","V2_OWNERSHIP_RELAXED_FULL_DOMAIN","V3_ALL_GROUP_CVS_H2_ELIGIBLE","V4_SIGN_RELAXED_EXISTING_PAIRS"],"classification_counts":counts,"successor":dec}
        (out/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R14_Summary.json").write_bytes(jb(summ));(out/"POSTV16_AV4_PIVOT_P2_R6_R14_Decision_Contract.json").write_bytes(jb(dec));(out/"POSTV16_AV4_PIVOT_P2_R6_R14_Bottleneck_Diagnostic_Contract.json").write_bytes(jb(con))
        gate("R5_state_unchanged",sha(drive/R5/"POSTV16_AV4_PIVOT_P2_R6_R5_Provisional_LocalRepaired_Day375_State.npz")==R5SHA)
        (out/"POSTV16_AV4_PIVOT_P2_R6_R14_Final_Gate_Matrix.csv").write_bytes(csvb(gates))
        mr=[]
        for p in sorted(out.iterdir()):
            if p.is_file():mr.append({"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size})
        (out/"POSTV16_AV4_PIVOT_P2_R6_R14_Artifact_Manifest.csv").write_bytes(csvb(mr))
        print("POSTV16-AV4-PIVOT-P2-R6-R14: PASS");print("Bottleneck classification counts:",counts);print("Group classifications:",{int(r["execution_group_id"]):r["bottleneck_classification"] for r in clsrows})
        return 0
    except Exception as e:
        blk.mkdir(parents=True,exist_ok=True);rp=blk/"POSTV16_AV4_PIVOT_P2_R6_R14_Blocked_Report.json"
        if not rp.exists():rp.write_text(json.dumps({"milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(e),"state_mutation_executed":False,"automatic_rerun_authorized":False,"gates_completed":gates},indent=2,sort_keys=True)+"\n")
        print(M+": BLOCKED");print("Stage:",stage);print("Exception:",repr(e));return 2

if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--project-root",type=Path,default=Path("."));a.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"));a.add_argument("--self-test",action="store_true");x=a.parse_args()
    if x.self_test:selftest();raise SystemExit(0)
    raise SystemExit(main(x.project_root,x.drive_root))
