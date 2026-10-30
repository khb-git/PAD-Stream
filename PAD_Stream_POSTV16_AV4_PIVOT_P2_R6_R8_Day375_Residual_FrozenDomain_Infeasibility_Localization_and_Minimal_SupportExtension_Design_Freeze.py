#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, importlib.util, io, json, shutil, subprocess, sys
from pathlib import Path
from typing import Any
import numpy as np

MILESTONE="POSTV16-AV4-PIVOT-P2-R6-R8"
MILESTONE_NAME="Day375 Residual Frozen-Domain Infeasibility Localization and Minimal Support-Extension Design Freeze"
STATUS_PASS="AV4PIVOTP2R6R8_DAY375_RESIDUAL_FROZEN_DOMAIN_INFEASIBILITY_LOCALIZATION_AND_MINIMAL_SUPPORT_EXTENSION_DESIGN_FREEZE_PASS_NO_STATE_MUTATION"
STATUS_BLOCKED="AV4PIVOTP2R6R8_TECHNICAL_OR_AUTHORITY_BLOCK"
RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
EXPECTED_BRANCH="postv16-av4-pivot"
EXPECTED_PARENT="604e7a56627868a0cebd410e8da82f135d024f86"
GRID=(15,50,50); NZ,NY,NX=GRID; NCELL=NZ*NY*NX; NSL=1078; NCV=200; NCV_TOTAL=NSL*NCV
DAY=375.0; BACKGROUND=0.20; MAX_SG=0.60
CELL_TOL_KG=1e-7; CV_TOL_KG=1e-7; LEDGER_TOL_KG=1e-6; SIGN_TOL_KG=1e-10
SLACK_CV_TOL_KG=1e-7; SLACK_TOTAL_ABS_TOL_KG=1e-6; SLACK_TOTAL_REL_TOL=1e-12; POSITIVE_ROOM_TOL_KG=1e-8
EXPECTED_COMPONENTS=158; EXPECTED_GROUPS=87; EXPECTED_FAILED=21; EXPECTED_FEASIBLE=66
EXPECTED_TARGET_CVS=10225; EXPECTED_RECURRENT_EDGES=74237983; EXPECTED_UNIQUE_SINKS=8226
R5_PROVISIONAL_SHA256="1553445022f7267d7802f8833d5440d7521433a4cd8b7c06652cffeb6d693e57"
BASE_AV4=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"
R7_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R6_R7_Day375_Residual_External_Component_Exact_Projection_Semantics_Freeze"
R7_SUM="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R7_Summary.json"
R7_DEC="POSTV16_AV4_PIVOT_P2_R6_R7_Decision_Contract.json"
R7_BASE="POSTV16_AV4_PIVOT_P2_R6_R7_Baseline_Exact_Feasibility_Audit.csv"
R7_TGT="POSTV16_AV4_PIVOT_P2_R6_R7_Frozen_Target_CVs.csv"
R7_EDGE="POSTV16_AV4_PIVOT_P2_R6_R7_Frozen_Recurrent_Eligibility_Edges.csv"
R7_GRP="POSTV16_AV4_PIVOT_P2_R6_R7_Prospective_Execution_Groups.csv"
R7_GF="POSTV16_AV4_PIVOT_P2_R6_R7_Group_Exact_Feasibility_Audit.csv"
R7_MAN="POSTV16_AV4_PIVOT_P2_R6_R7_Artifact_Manifest.csv"
R7_STATUS="AV4PIVOTP2R6R7_DAY375_RESIDUAL_EXTERNAL_COMPONENT_EXACT_PROJECTION_SEMANTICS_FREEZE_PASS_NO_STATE_MUTATION"
R7_CLASS="R6R7_EXACT_FROZEN_DOMAIN_PROJECTION_SEMANTICS_FROZEN_RESIDUAL_GROUPS_REMAIN_INFEASIBLE_MINIMAL_SUPPORT_EXTENSION_DESIGN_REQUIRED"
R8_NAME=MILESTONE_NAME
R6_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R6_R6_Day375_Residual_External_Component_Projection_Authority_and_Global_State_Closure_Audit"
R6_CV="POSTV16_AV4_PIVOT_P2_R6_R6_Residual_CV_Component_Ownership.csv"
R5_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R6_R5_Controlled_Day375_TerminalSink_FixedExternal_Local_Projection"
R5_SUM="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R5_Summary.json"; R5_STATE="POSTV16_AV4_PIVOT_P2_R6_R5_Provisional_LocalRepaired_Day375_State.npz"
R5_STATUS="AV4PIVOTP2R6R5_CONTROLLED_DAY375_TERMINAL_SINK_FIXED_EXTERNAL_RECURRENT_ELIGIBILITY_EXACT_CV_CONSERVATIVE_LOCAL_PROJECTION_EXECUTION_PASS"
D370_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_CompletedComponent_CellMembership_Identity_Repair_and_Controlled_Projection"
D370_SUM="PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_Summary.json"; D370_STATE="POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_Repaired_Day370_State.npz"
D370_STATUS="AV4PIVOTP2R5G2AR4R1R1R1_COMPLETED_COMPONENT_CELL_MEMBERSHIP_IDENTITY_REPAIR_AND_COMPONENT_FRONTIER_PROJECTION_EXECUTION_PASS"
A2E_REL=BASE_AV4/"POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"; A2E_EPOCH="POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"; A2E_SUM="PAD_Stream_POSTV16_AV4_A2_E_Summary.json"
A2E_STATUS="AV4A2E_AV3CR0003_DAY365_SAME_TIME_SPATIAL_MOBILITY_PRESSURE_SATURATION_REFRESH_DARCY_POLLOCK_TOF_GEOMETRY_EXECUTION_PASS"
OUT_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R6_R8_Day375_Residual_FrozenDomain_Infeasibility_Localization_and_Minimal_SupportExtension_Design_Freeze"
BLOCK_REL=BASE_AV4/"POSTV16_AV4_PIVOT_P2_R6_R8_BLOCKED"
R7RUN="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R7_Day375_Residual_External_Component_Exact_Projection_Semantics_Freeze.py"; R7BLOB="d9699621847b275074b67efcfeb03c49d4eebacd"
R6RUN="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R6_Day375_Residual_External_Component_Projection_Authority_and_Global_State_Closure_Audit.py"; R6BLOB="c46c8c3cdb35087fcbd2879b8121b2154cae0b0d"
R4RUN="PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R4_Day375_TerminalSink_FixedExternal_RecurrentEligibility_Prospective_Repair_Semantics_Freeze.py"; R4BLOB="02c5cc227075c4e64b856909545cd1ecbc1daf23"
R2SRC="PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"; R2BLOB="a127f8730a16e150713420ea547a8de6255550ef"
SOURCE_BLOBS={R7RUN:R7BLOB,R6RUN:R6BLOB,R4RUN:R4BLOB,R2SRC:R2BLOB}

class GateError(RuntimeError): pass

def git_text(root,*args):
    p=subprocess.run(["git","-C",str(root),*args],check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return (p.stdout or "").strip()
def sha256_file(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()
def load_json(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def read_csv(p):
    with Path(p).open("r",encoding="utf-8",newline="") as f: return list(csv.DictReader(f))
def csv_bytes(rows):
    if not rows: return b""
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    s=io.StringIO(newline=""); w=csv.DictWriter(s,fieldnames=fields,lineterminator="\n"); w.writeheader(); w.writerows(rows); return s.getvalue().encode()
def json_bytes(o): return (json.dumps(o,indent=2,sort_keys=True)+"\n").encode()
def load_module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise GateError(f"cannot_load_module:{path}")
    m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m
def scalar(x): return float(np.asarray(x).reshape(()))
def ijk(flat):
    k=flat//(NY*NX); rem=flat%(NY*NX); j=rem//NX; i=rem%NX; return k,j,i
def flat_of(k,j,i): return k*(NY*NX)+j*NX+i
def bool_csv(x): return str(x).strip().lower() in {"true","1","yes"}
def face_neighbors(cells):
    out=set()
    for c in cells:
        k,j,i=ijk(int(c))
        for dj,di in ((-1,0),(1,0),(0,-1),(0,1)):
            jj=j+dj; ii=i+di
            if 0<=jj<NY and 0<=ii<NX: out.add(flat_of(k,jj,ii))
    return out
def h2xy_radius2(cells,s0):
    out=set()
    for c in np.asarray(cells,dtype=np.int64).reshape(-1).tolist():
        k,j,i=ijk(int(c))
        for dj in range(-2,3):
            for di in range(-2,3):
                d=abs(di)+abs(dj)
                if not (1<=d<=2): continue
                jj=j+dj; ii=i+di
                if 0<=jj<NY and 0<=ii<NX:
                    h=flat_of(k,jj,ii)
                    if h not in s0: out.add(int(h))
    return out

def self_test():
    assert EXPECTED_GROUPS==87 and EXPECTED_FAILED==21 and EXPECTED_FEASIBLE==66
    assert EXPECTED_TARGET_CVS==10225 and EXPECTED_RECURRENT_EDGES==74237983
    c=flat_of(5,10,10); n=face_neighbors({c}); assert len(n)==4 and c not in n and all(ijk(x)[0]==5 for x in n)
    print("POSTV16 AV4 PIVOT P2-R6-R8 structural self-test: PASS")

def main(project_root,drive_root):
    root=Path(project_root).resolve(); drive=Path(drive_root).resolve(); out=drive/OUT_REL; block=drive/BLOCK_REL; stage="preflight"; gates=[]
    def gate(name,passed,value=None):
        ok=bool(passed); gates.append({"stage":stage,"gate":name,"pass":ok,"detail":"" if value is None else repr(value)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}"+(f" -- {value}" if value is not None else ""))
        if not ok: raise GateError(name)
    print("="*212)
    print("POSTV16-AV4-PIVOT-P2-R6-R8 -- FROZEN-DOMAIN INFEASIBILITY LOCALIZATION + MINIMAL SUPPORT-EXTENSION DESIGN FREEZE")
    print("="*212)
    print("READ-ONLY DESIGN/FREEZE. NO DAY375 MUTATION. 66 R6-R7 FEASIBLE GROUPS REMAIN FROZEN.")
    print("T0 CURRENT SUPPORT -> T1A UNUSED FROZEN-DOMAIN FACE SINKS -> T1B ONE NON-RECURSIVE SAME-LAYER FACE SHELL.")
    try:
        stage="formal_outcome_firewall"
        ps=out/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R8_Summary.json"; br=block/"POSTV16_AV4_PIVOT_P2_R6_R8_Blocked_Report.json"
        if ps.is_file(): print("[PASS] formal R6-R8 PASS already exists; immutable outcome preserved."); return 0
        gate("no_preexisting_R6R8_BLOCK",not br.exists(),str(br))

        stage="repository_authority"
        gate("branch_exact",git_text(root,"branch","--show-current")==EXPECTED_BRANCH)
        parent=git_text(root,"rev-parse","HEAD^"); gate("parent_is_R6R7_PASS",parent==EXPECTED_PARENT,parent)
        gate("repository_clean",git_text(root,"status","--porcelain")=="",repr(git_text(root,"status","--porcelain")))
        for fn,blob in SOURCE_BLOBS.items():
            p=root/fn; actual=git_text(root,"hash-object",str(p)) if p.is_file() else "missing"; gate(f"{Path(fn).stem}_blob_exact",actual==blob,actual)

        stage="R6R7_binding"
        r7=drive/R7_REL
        p={"sum":r7/R7_SUM,"dec":r7/R7_DEC,"base":r7/R7_BASE,"tgt":r7/R7_TGT,"edge":r7/R7_EDGE,"grp":r7/R7_GRP,"gf":r7/R7_GF,"man":r7/R7_MAN}
        for k,v in p.items(): gate(f"R6R7_{k}_present",v.is_file(),str(v))
        s=load_json(p["sum"]); d=load_json(p["dec"]); base_rows=read_csv(p["base"]); target_rows=read_csv(p["tgt"]); group_rows=read_csv(p["grp"]); gf_rows=read_csv(p["gf"]); man={r["file"]:r for r in read_csv(p["man"])}
        gate("R6R7_status_exact",s.get("status")==R7_STATUS,s.get("status")); gate("R6R7_class_exact",s.get("classification")==R7_CLASS,s.get("classification"))
        gate("R6R7_groups_exact",int(s["prospective_execution_group_count"])==EXPECTED_GROUPS)
        gate("R6R7_failed_exact",int(s["exact_frozen_domain_infeasible_group_count"])==EXPECTED_FAILED)
        gate("R6R7_feasible_exact",int(s["exact_frozen_domain_feasible_group_count"])==EXPECTED_FEASIBLE)
        gate("R6R7_targets_exact",int(s["target_CV_count"])==EXPECTED_TARGET_CVS)
        gate("R6R7_edges_exact",int(s["new_recurrent_eligibility_edge_count"])==EXPECTED_RECURRENT_EDGES)
        gate("R6R7_sinks_exact",int(s["new_recurrent_unique_sink_count"])==EXPECTED_UNIQUE_SINKS)
        gate("R6R7_R8_authorized",d.get("P2_R6_R8_authorized") is True); gate("R6R7_R8_name_exact",d.get("P2_R6_R8_name")==R8_NAME,d.get("P2_R6_R8_name")); gate("R6R7_execution_false",d.get("P2_R6_R8_projection_execution_authorized") is False); gate("R6R7_design_true",d.get("P2_R6_R8_minimal_support_extension_design_authorized") is True)
        for fn,sha_key in [(R7_BASE,"baseline_exact_feasibility_sha256"),(R7_TGT,"target_CVs_sha256"),(R7_EDGE,"recurrent_eligibility_edges_sha256"),(R7_GRP,"prospective_execution_groups_sha256"),(R7_GF,"group_exact_feasibility_sha256")]:
            gate(f"manifest_has_{fn}",fn in man); gate(f"manifest_sha_{fn}",man[fn]["sha256"]==s[sha_key],man[fn]["sha256"]); gate(f"manifest_size_{fn}",(r7/fn).stat().st_size==int(man[fn]["bytes"]),(r7/fn).stat().st_size)
        gate("R7_base_hash",sha256_file(p["base"])==s["baseline_exact_feasibility_sha256"]); gate("R7_tgt_hash",sha256_file(p["tgt"])==s["target_CVs_sha256"]); gate("R7_grp_hash",sha256_file(p["grp"])==s["prospective_execution_groups_sha256"]); gate("R7_gf_hash",sha256_file(p["gf"])==s["group_exact_feasibility_sha256"])
        gate("R7_base_rows",len(base_rows)==EXPECTED_COMPONENTS,len(base_rows)); gate("R7_target_rows",len(target_rows)==EXPECTED_TARGET_CVS,len(target_rows)); gate("R7_group_rows",len(group_rows)==EXPECTED_GROUPS,len(group_rows)); gate("R7_gf_rows",len(gf_rows)==EXPECTED_GROUPS,len(gf_rows))
        failed=sorted(int(r["execution_group_id"]) for r in gf_rows if not bool_csv(r["exact_frozen_domain_feasible"])); feasible=sorted(int(r["execution_group_id"]) for r in gf_rows if bool_csv(r["exact_frozen_domain_feasible"])); gate("failed_count",len(failed)==EXPECTED_FAILED,failed); gate("feasible_count",len(feasible)==EXPECTED_FEASIBLE)
        gmeta={int(r["execution_group_id"]):r for r in group_rows}; component_to_group={}
        for gid,row in gmeta.items():
            for cid in [int(x) for x in row["R6R6_component_ids"].split(";") if x]:
                if cid in component_to_group: raise GateError(f"duplicate_component_owner:{cid}")
                component_to_group[cid]=gid
        gate("component_partition",sorted(component_to_group)==list(range(EXPECTED_COMPONENTS)))
        target_by_component={cid:np.asarray(sorted(int(r["cv_id"]) for r in target_rows if int(r["component_id"])==cid),dtype=np.int64) for cid in range(EXPECTED_COMPONENTS)}

        stage="R6R6_ownership"
        cvrows=read_csv(drive/R6_REL/R6_CV); cv_to_component={int(r["cv_id"]):int(r["component_id"]) for r in cvrows}; gate("CV_owner_unique",len(cvrows)==len(cv_to_component))
        component_cvs={cid:np.asarray(sorted(cv for cv,owner in cv_to_component.items() if owner==cid),dtype=np.int64) for cid in range(EXPECTED_COMPONENTS)}
        gate("all_components_nonempty",all(len(v)>0 for v in component_cvs.values()))

        stage="state_binding"
        r5d=drive/R5_REL; r5sum=load_json(r5d/R5_SUM); r5state=r5d/R5_STATE; gate("R5_status",r5sum.get("status")==R5_STATUS,r5sum.get("status")); r5sha=sha256_file(r5state); gate("R5_SHA",r5sha==R5_PROVISIONAL_SHA256,r5sha)
        with np.load(r5state,allow_pickle=False) as z: st={k:np.asarray(z[k]).copy() for k in z.files}
        pair_cv=np.asarray(st["existing_pair_cv"],dtype=np.int64).reshape(-1); pair_cell=np.asarray(st["existing_pair_cell"],dtype=np.int64).reshape(-1); pair_val=np.asarray(st["locally_repaired_existing_pair_contribution_kg"],dtype=np.float64).reshape(-1); provisional=np.asarray(st["provisional_grid_component_mass_kg"],dtype=np.float64).reshape(-1); r5cv=np.asarray(st["local_component_cv"],dtype=np.int64).reshape(-1); r5hcv=np.asarray(st["local_halo_cv"],dtype=np.int64).reshape(-1); r5hcell=np.asarray(st["local_halo_cell"],dtype=np.int64).reshape(-1); r5hmass=np.asarray(st["local_halo_contribution_kg"],dtype=np.float64).reshape(-1); pstate=np.asarray(st["parent_pressure_psi"],dtype=np.float64)
        d370d=drive/D370_REL; d370sum=load_json(d370d/D370_SUM); gate("D370_status",d370sum.get("status")==D370_STATUS,d370sum.get("status")); gate("D370_SHA",sha256_file(d370d/D370_STATE)==d370sum.get("accepted_state_sha256"))
        with np.load(d370d/D370_STATE,allow_pickle=False) as z: old={k:np.asarray(z[k]).copy() for k in z.files}
        old_grid=np.asarray(old["grid_component_mass_kg"],dtype=np.float64).reshape(-1); fhcv=np.asarray(old["halo_cv"],dtype=np.int64).reshape(-1); fhcell=np.asarray(old["halo_cell"],dtype=np.int64).reshape(-1); keys=np.unique(fhcv*NCELL+fhcell); fhcv=(keys//NCELL).astype(np.int64); fhcell=(keys%NCELL).astype(np.int64); frozen_domain=set(int(x) for x in np.unique(fhcell).tolist())
        a2=drive/A2E_REL; a2sum=load_json(a2/A2E_SUM); gate("A2E_status",a2sum.get("status")==A2E_STATUS,a2sum.get("status"))
        with np.load(a2/A2E_EPOCH,allow_pickle=False) as z: ep={k:np.asarray(z[k]).copy() for k in z.files}
        pressure=np.asarray(ep["refreshed_pressure_psi"],dtype=np.float64); gate("pressure_identity",float(np.max(np.abs(pressure-pstate)))<=1e-12)
        r2=load_module(root/R2SRC,"r8_r2"); pv=np.asarray(ep["pore_volume_m3"],dtype=np.float64); pref=scalar(ep["reference_gas_pressure_pa"]); rho=np.asarray(r2.gas_density_from_state(np.full(GRID,BACKGROUND+MAX_SG),pressure,pref),dtype=np.float64); capacity=(pv*rho*MAX_SG).reshape(-1)
        cur_cv=np.bincount(pair_cv,weights=pair_val,minlength=NCV_TOTAL)+np.bincount(r5hcv,weights=r5hmass,minlength=NCV_TOTAL); recon=old_grid+np.bincount(pair_cell,weights=pair_val,minlength=NCELL)+np.bincount(r5hcell,weights=r5hmass,minlength=NCELL); gate("provisional_reconstruct",float(np.max(np.abs(recon-provisional)))<=CELL_TOL_KG,float(np.max(np.abs(recon-provisional)))); gate("ledger",abs(float(np.sum(provisional)-(np.sum(old_grid)+np.sum(cur_cv))))<=LEDGER_TOL_KG)
        residual=np.asarray(sorted(cv_to_component),dtype=np.int64); gate("residual_disjoint_R5",set(residual.tolist()).isdisjoint(set(r5cv.tolist())) and not bool(np.any(np.isin(r5hcv,residual))))
        global_s0=set(int(x) for x in np.unique(pair_cell).tolist()); r5_fixed=set(int(x) for x in np.unique(np.r_[pair_cell[np.isin(pair_cv,r5cv)],r5hcell]).tolist())

        stage="compact_R7_support"
        component_frontier={}; component_baseline={}; component_cells={}; component_targets={}; total_rec=0; unique_sinks=set()
        for cid in range(EXPECTED_COMPONENTS):
            cvs=component_cvs[cid]; tset=set(int(x) for x in target_by_component[cid].tolist()); component_targets[cid]=tset; s0cells=np.unique(pair_cell[np.isin(pair_cv,cvs)]).astype(np.int64); frontier=set(int(h) for h in h2xy_radius2(s0cells,global_s0) if int(h) in frozen_domain); component_frontier[cid]=frontier
            mask=np.isin(fhcv,cvs); bedges=sorted(set((int(a),int(b)) for a,b in zip(fhcv[mask].tolist(),fhcell[mask].tolist()))); component_baseline[cid]=bedges; bset=set(bedges); rec=sum(len(frontier)-sum(1 for h in frontier if (cv,h) in bset) for cv in tset); total_rec+=rec; unique_sinks.update(frontier if tset else set()); row=base_rows[cid]; gate(f"component_{cid}_rec_count",rec==int(row["prospective_recurrent_edge_count"]),rec)
            cc=set(int(x) for x in s0cells.tolist()); cc.update(h for _,h in bedges); cc.update(frontier if tset else set()); component_cells[cid]=cc
        gate("total_rec_exact",total_rec==EXPECTED_RECURRENT_EDGES,total_rec); gate("unique_sinks_exact",len(unique_sinks)==EXPECTED_UNIQUE_SINKS,len(unique_sinks))
        cell_to_group={}
        for cid,cells in component_cells.items():
            gid=component_to_group[cid]
            for c in cells: cell_to_group.setdefault(c,set()).add(gid)

        from scipy.optimize import linprog
        from scipy import sparse

        def build_pooled(group_cids,extra=None,add_slack=False):
            extra=extra or {}; cvs=np.asarray(sorted(int(cv) for cid in group_cids for cv in component_cvs[cid].tolist()),dtype=np.int64); pmask=np.isin(pair_cv,cvs); pidx=np.flatnonzero(pmask&(np.abs(pair_val)>SIGN_TOL_KG)); xcv=pair_cv[pidx]; xcell=pair_cell[pidx]; x0=pair_val[pidx]
            bindiv=[]; pools={}; targets={}
            for cid in group_cids:
                t=sorted(component_targets[cid]); pool=set(component_frontier[cid]); pool.update(int(x) for x in extra.get(cid,set())); pools[cid]=sorted(pool); targets[cid]=t
                for cv,h in component_baseline[cid]:
                    if cv in component_targets[cid] and h in pool: continue
                    bindiv.append((int(cv),int(h)))
            bindiv=sorted(set(bindiv)); ykeys=[(cid,cv) for cid in group_cids for cv in targets[cid]]; qkeys=[(cid,c) for cid in group_cids for c in pools[cid]]; nx=len(pidx); nb=len(bindiv); ny=len(ykeys); nq=len(qkeys); ncv=len(cvs)
            ox=0; ob=nx; oy=ob+nb; oq=oy+ny; osp=oq+nq; osm=osp+(ncv if add_slack else 0); nvar=osm+(ncv if add_slack else 0)
            cvrow={int(cv):r for r,cv in enumerate(cvs.tolist())}; pcids=[cid for cid in group_cids if targets[cid]]; prow={cid:ncv+i for i,cid in enumerate(pcids)}; er=[]; ec=[]; ev=[]
            for q,cv in enumerate(xcv.tolist()): er.append(cvrow[int(cv)]); ec.append(ox+q); ev.append(1.0)
            for q,(cv,c) in enumerate(bindiv): er.append(cvrow[cv]); ec.append(ob+q); ev.append(1.0)
            for q,(cid,cv) in enumerate(ykeys): er += [cvrow[cv],prow[cid]]; ec += [oy+q,oy+q]; ev += [1.0,1.0]
            for q,(cid,c) in enumerate(qkeys): er.append(prow[cid]); ec.append(oq+q); ev.append(-1.0)
            if add_slack:
                for r in range(ncv): er += [r,r]; ec += [osp+r,osm+r]; ev += [1.0,-1.0]
            Aeq=sparse.coo_matrix((np.asarray(ev),(np.asarray(er),np.asarray(ec))),shape=(ncv+len(pcids),nvar)).tocsr(); beq=np.r_[cur_cv[cvs],np.zeros(len(pcids))]
            lc=set(int(x) for x in xcell.tolist()); lc.update(c for _,c in bindiv); lc.update(c for _,c in qkeys); local=np.asarray(sorted(lc),dtype=np.int64); crow={int(c):r for r,c in enumerate(local.tolist())}; rr=[]; cc=[]; vv=[]
            for q,c in enumerate(xcell.tolist()): rr.append(crow[int(c)]); cc.append(ox+q); vv.append(1.0)
            for q,(cv,c) in enumerate(bindiv): rr.append(crow[c]); cc.append(ob+q); vv.append(1.0)
            for q,(cid,c) in enumerate(qkeys): rr.append(crow[c]); cc.append(oq+q); vv.append(1.0)
            Ac=sparse.coo_matrix((np.asarray(vv),(np.asarray(rr),np.asarray(cc))),shape=(len(local),nvar)).tocsr(); fixed_delta=np.bincount(pair_cell[~np.isin(pair_cv,cvs)],weights=pair_val[~np.isin(pair_cv,cvs)],minlength=NCELL); fixed=old_grid+fixed_delta+np.bincount(r5hcell,weights=r5hmass,minlength=NCELL); Aub=sparse.vstack([Ac,-Ac],format="csr"); bub=np.r_[capacity[local]-fixed[local],fixed[local]]
            bounds=[]
            for v in x0.tolist(): bounds.append((0.0,None) if v>SIGN_TOL_KG else ((None,0.0) if v<-SIGN_TOL_KG else (0.0,0.0)))
            bounds += [(0.0,None)]*(nb+ny+nq+(2*ncv if add_slack else 0))
            return {"cvs":cvs,"ncv":ncv,"nx":nx,"nb":nb,"ny":ny,"nq":nq,"osp":osp,"osm":osm,"nvar":nvar,"Aeq":Aeq,"beq":beq,"Ac":Ac,"Aub":Aub,"bub":bub,"bounds":bounds,"local":local,"fixed":fixed}
        def solve(data,slack=False):
            c=np.zeros(data["nvar"])
            if slack: c[data["osp"]:]=1.0
            return linprog(c,A_ub=data["Aub"],b_ub=data["bub"],A_eq=data["Aeq"],b_eq=data["beq"],bounds=data["bounds"],method="highs",options={"presolve":True})
        def metrics(data,lp):
            if not lp.success: return False,None,None,None,None
            z=np.asarray(lp.x); cvres=np.asarray(data["Aeq"][:data["ncv"],:]@z-data["beq"][:data["ncv"]]).ravel(); cm=data["fixed"][data["local"]]+np.asarray(data["Ac"]@z).ravel(); h=z[data["nx"]:data["nx"]+data["nb"]+data["ny"]+data["nq"]]; mcv=float(np.max(np.abs(cvres))) if len(cvres) else 0.0; mlo=max(0.0,-float(np.min(cm))); mhi=max(0.0,float(np.max(cm-capacity[data["local"]]))); minh=float(np.min(h)) if len(h) else 0.0; ok=mcv<=CV_TOL_KG and mlo<=CELL_TOL_KG and mhi<=CELL_TOL_KG and minh>=-SIGN_TOL_KG; return ok,mcv,mlo,mhi,minh

        stage="failed_group_localization"
        loc=[]; defrows=[]; cand=[]; tiers=[]; chosen={}; chosen_class={}; nT1A=nT1B=nfail=0; new_ep_groups=0
        for gid in failed:
            cids=[int(x) for x in gmeta[gid]["R6R6_component_ids"].split(";") if x]
            t0=build_pooled(cids,{},False); lp0=solve(t0,False); ok0,*_=metrics(t0,lp0); gate(f"group_{gid}_T0_failed",not ok0,lp0.message)
            sd=build_pooled(cids,{},True); lps=solve(sd,True); gate(f"group_{gid}_slack_LP",lps.success,lps.message); z=np.asarray(lps.x); n=sd["ncv"]; sp=z[sd["osp"]:sd["osp"]+n]; sm=z[sd["osm"]:sd["osm"]+n]; ab=sp+sm; sg=sp-sm; tot=float(np.sum(ab)); mx=float(np.max(ab)); tol=max(SLACK_TOTAL_ABS_TOL_KG,abs(float(np.sum(cur_cv[sd["cvs"]])))*SLACK_TOTAL_REL_TOL); gate(f"group_{gid}_nonzero_slack",tot>tol,tot); mask=ab>SLACK_CV_TOL_KG; dcvs=sd["cvs"][mask]; gate(f"group_{gid}_deficient_CVs",len(dcvs)>0,len(dcvs)); dcomps=sorted(set(cv_to_component[int(cv)] for cv in dcvs.tolist()))
            for cv,a,ss in zip(dcvs.tolist(),ab[mask].tolist(),sg[mask].tolist()): defrows.append({"execution_group_id":gid,"component_id":cv_to_component[int(cv)],"cv_id":int(cv),"streamline":int(cv//NCV),"cv_node":int(cv%NCV),"minimum_L1_absolute_conservation_slack_kg":float(a),"signed_conservation_slack_kg":float(ss),"R6R7_original_target_CV":int(cv) in component_targets[cv_to_component[int(cv)]]})
            extraA={}; extraB={}; fixed=sd["fixed"]
            for cid in cids:
                if cid not in dcomps: extraA[cid]=set(); extraB[cid]=set(); continue
                current=set(component_cells[cid]); shell=face_neighbors(current)-current; shell={int(c) for c in shell if int(c) not in global_s0 and int(c) not in r5_fixed}; shell={int(c) for c in shell if all(owner==gid for owner in cell_to_group.get(int(c),{gid}))}; shell={int(c) for c in shell if capacity[int(c)]-fixed[int(c)]>POSITIVE_ROOM_TOL_KG}; A={c for c in shell if c in frozen_domain}; Bnew={c for c in shell if c not in frozen_domain}; extraA[cid]=A; extraB[cid]=A|Bnew
                for c in sorted(A):
                    k,j,i=ijk(c); cand.append({"execution_group_id":gid,"component_id":cid,"tier":"T1A_UNUSED_FROZEN_H2_DOMAIN_FACE_SINK","flat_cell":c,"k":k,"j":j,"i":i,"already_in_Day370_frozen_H2_domain":True,"new_H2_endpoint_cell_if_executed":False,"same_layer_face_neighbor":True,"terminal_sink_only":True,"fixed_external_room_kg":float(capacity[c]-fixed[c])})
                for c in sorted(Bnew):
                    k,j,i=ijk(c); cand.append({"execution_group_id":gid,"component_id":cid,"tier":"T1B_NEW_H2_ENDPOINT_SINGLE_FACE_SHELL","flat_cell":c,"k":k,"j":j,"i":i,"already_in_Day370_frozen_H2_domain":False,"new_H2_endpoint_cell_if_executed":True,"same_layer_face_neighbor":True,"terminal_sink_only":True,"fixed_external_room_kg":float(capacity[c]-fixed[c])})
            da=build_pooled(cids,extraA,False); lpa=solve(da,False); oka,*_=metrics(da,lpa)
            if oka: nT1A+=1; cls="T1A_CONNECTIVITY_ONLY_WITHIN_FROZEN_H2_DOMAIN"; ex=extraA; okb=True; lpb=None
            else:
                db=build_pooled(cids,extraB,False); lpb=solve(db,False); okb,*_=metrics(db,lpb)
                if okb: nT1B+=1; new_ep_groups+=1; cls="T1B_SINGLE_NONRECURSIVE_FACE_SHELL_NEW_H2_ENDPOINTS"; ex=extraB
                else: nfail+=1; cls="T1B_SINGLE_SHELL_INSUFFICIENT"; ex=extraB
            chosen_class[gid]=cls
            for cid,cells in ex.items(): chosen[(gid,cid)]=set(cells)
            loc.append({"execution_group_id":gid,"R6R6_component_ids":";".join(map(str,cids)),"component_count":len(cids),"CV_count":len(sd["cvs"]),"R6R7_target_CV_count":sum(len(target_by_component[c]) for c in cids),"minimum_L1_total_absolute_conservation_slack_kg":tot,"minimum_L1_max_absolute_conservation_slack_kg":mx,"localized_deficient_CV_count":len(dcvs),"localized_deficient_component_count":len(dcomps),"localized_deficient_component_ids":";".join(map(str,dcomps)),"T1A_candidate_cell_count":sum(len(v) for v in extraA.values()),"T1A_exact_feasible":oka,"T1B_candidate_cell_count":sum(len(v) for v in extraB.values()),"T1B_new_endpoint_cell_count":sum(len(set(extraB[c])-set(extraA[c])) for c in cids),"T1B_exact_feasible":bool(okb),"chosen_support_class":cls})
            tiers.append({"execution_group_id":gid,"tier":"T0_R6R7_FROZEN_DOMAIN","exact_feasible":False,"HiGHS_status":int(lp0.status),"HiGHS_message":str(lp0.message),"additional_component_cell_memberships":0,"new_H2_endpoint_cells":0})
            tiers.append({"execution_group_id":gid,"tier":"T1A_UNUSED_FROZEN_H2_DOMAIN_FACE_SINKS","exact_feasible":bool(oka),"HiGHS_status":int(lpa.status),"HiGHS_message":str(lpa.message),"additional_component_cell_memberships":sum(len(v) for v in extraA.values()),"new_H2_endpoint_cells":0})
            if not oka: tiers.append({"execution_group_id":gid,"tier":"T1B_SINGLE_NONRECURSIVE_FACE_SHELL","exact_feasible":bool(okb),"HiGHS_status":int(lpb.status),"HiGHS_message":str(lpb.message),"additional_component_cell_memberships":sum(len(v) for v in extraB.values()),"new_H2_endpoint_cells":len(set(c for cid in cids for c in (set(extraB[cid])-set(extraA[cid]))))})
        gate("failed_partition",nT1A+nT1B+nfail==EXPECTED_FAILED,(nT1A,nT1B,nfail))

        compact=[]
        for gid in failed:
            for cid in [int(x) for x in gmeta[gid]["R6R6_component_ids"].split(";") if x]:
                for c in sorted(chosen.get((gid,cid),set())):
                    k,j,i=ijk(c); compact.append({"execution_group_id":gid,"component_id":cid,"chosen_support_class":chosen_class[gid],"flat_cell":c,"k":k,"j":j,"i":i,"cell_in_Day370_frozen_H2_domain":c in frozen_domain,"new_H2_endpoint_if_executed":c not in frozen_domain,"complete_bipartite_rule":"all_R6R7_target_CVs_in_this_component_may_deposit_nonnegative_mass_to_this_terminal_sink"})

        stage="artifact_publication"
        local=Path("/content")/"PAD_Stream_AV4_PIVOT_P2_R6_R8_Final_Artifacts"
        if local.exists(): shutil.rmtree(local)
        local.mkdir(parents=True)
        files={
            "localization":local/"POSTV16_AV4_PIVOT_P2_R6_R8_Failed_Group_Infeasibility_Localization.csv",
            "deficient":local/"POSTV16_AV4_PIVOT_P2_R6_R8_Localized_Deficient_CVs.csv",
            "candidate":local/"POSTV16_AV4_PIVOT_P2_R6_R8_SingleShell_Candidate_Terminal_Sinks.csv",
            "tiers":local/"POSTV16_AV4_PIVOT_P2_R6_R8_Tier_Exact_Feasibility_Audit.csv",
            "compact":local/"POSTV16_AV4_PIVOT_P2_R6_R8_Frozen_Compact_Support_Extension.csv",
        }
        for key,rows in [("localization",loc),("deficient",defrows),("candidate",cand),("tiers",tiers),("compact",compact)]: files[key].write_bytes(csv_bytes(rows))
        sh={k:sha256_file(v) for k,v in files.items()}; allresolved=nfail==0
        if allresolved: classification="R6R8_MINIMAL_SINGLE_SHELL_SUPPORT_EXTENSION_FROZEN_ALL_21_FAILED_GROUPS_EXACT_FEASIBLE_EXECUTION_NEXT"; next_name="Controlled Day375 Residual Minimal-Support Exact CV-Conservative Projection Execution"; exec_auth=True; design_auth=False
        else: classification="R6R8_SINGLE_SHELL_SUPPORT_EXTENSION_INSUFFICIENT_RESIDUAL_GROUPS_REQUIRE_SECOND_STAGE_TOPOLOGY_DESIGN"; next_name="Day375 Residual Second-Stage Support-Extension Topology Design Freeze"; exec_auth=False; design_auth=True
        contract={"milestone":MILESTONE,"status":STATUS_PASS,"classification":classification,"design_freeze_only":True,"state_mutation_executed":False,"compact_support_semantics":{"explicit_74M_edge_manifest_reemitted":False,"exact_equivalence_rule":"Within each R6R6 component, R6R7 target CVs are completely bipartite to the component terminal-sink pool. R6R8 stores target sets plus sink sets and enforces per-target H2 totals, per-cell H2 allocations and exact component pool balance; this is feasibility-equivalent to the explicit nonnegative transportation matrix.","baseline_individual_H2_edges_outside_complete_pool_remain_explicit":True},"extension_order":["T0 exact R6R7 frozen support","T1A unused frozen-H2-domain same-layer face sinks","T1B one non-recursive same-layer face shell outside frozen H2 endpoint domain"],"candidate_firewalls":{"global_S0_excluded":True,"R5_local_footprint_excluded":True,"other_R6R7_group_variable_domains_excluded":True,"positive_fixed_external_room_required":True,"vertical":False,"diagonal":False,"recursive_halo":False,"halo_transit":False},"manifests":{k:{"file":v.name,"sha256":sh[k]} for k,v in files.items()}}
        summary={"milestone":MILESTONE,"name":MILESTONE_NAME,"status":STATUS_PASS,"classification":classification,"design_freeze_only":True,"state_mutation_executed":False,"accepted_Day375_state_created":False,"R5_provisional_state_sha256":r5sha,"R5_local_repair_held_fixed":True,"R6R7_total_execution_group_count":EXPECTED_GROUPS,"R6R7_exact_feasible_group_count_frozen":EXPECTED_FEASIBLE,"R6R7_failed_group_count_localized":EXPECTED_FAILED,"T0_failed_groups_reproduced":EXPECTED_FAILED,"T1A_connectivity_only_feasible_group_count":nT1A,"T1B_single_shell_new_endpoint_feasible_group_count":nT1B,"single_shell_still_infeasible_group_count":nfail,"groups_requiring_new_H2_endpoint_cells":new_ep_groups,"localized_deficient_CV_count":len(defrows),"candidate_terminal_sink_membership_count":len(cand),"frozen_compact_support_membership_count":len(compact),"all_21_failed_groups_resolved_by_single_shell":allresolved,"explicit_74M_edge_manifest_reemitted":False,"compact_complete_bipartite_support_contract_used":True,"new_H2_endpoint_execution_performed":False,"vertical_support_used":False,"diagonal_support_used":False,"halo_transit_used":False,"pressure_refresh_executed":False,"time_advance_executed":False,"P3_authorized":False,"P4_authorized":False,"P5_training_authorized":False}
        decision={"milestone":MILESTONE,"status":STATUS_PASS,"classification":classification,"P2_R6_R9_authorized":True,"P2_R6_R9_name":next_name,"P2_R6_R9_projection_execution_authorized":exec_auth,"P2_R6_R9_second_stage_topology_design_authorized":design_auth,"P2_R6_R9_must_bind_R6R8_compact_support_contract":True,"P2_continuation_restart_authorized_now":False,"accepted_Day375_state_authorized_now":False,"support_growth_execution_authorized_now":False,"new_H2_endpoint_execution_authorized_now":False,"pressure_refresh_authorized":False,"Darcy_Pollock_TOF_regeneration_authorized":False,"time_advance_authorized":False,"P3_authorized":False,"P4_authorized":False,"P5_training_authorized":False}
        (local/"POSTV16_AV4_PIVOT_P2_R6_R8_Compact_Support_Design_Contract.json").write_bytes(json_bytes(contract)); (local/"PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R8_Summary.json").write_bytes(json_bytes(summary)); (local/"POSTV16_AV4_PIVOT_P2_R6_R8_Decision_Contract.json").write_bytes(json_bytes(decision))
        gate("R5_SHA_unchanged",sha256_file(r5state)==r5sha,sha256_file(r5state)); (local/"POSTV16_AV4_PIVOT_P2_R6_R8_Final_Gate_Matrix.csv").write_bytes(csv_bytes(gates)); manifest=[]
        for fp in sorted(local.rglob("*")):
            if fp.is_file(): manifest.append({"file":str(fp.relative_to(local)).replace("\\","/"),"sha256":sha256_file(fp),"bytes":fp.stat().st_size})
        (local/"POSTV16_AV4_PIVOT_P2_R6_R8_Artifact_Manifest.csv").write_bytes(csv_bytes(manifest))
        if out.exists(): raise GateError(f"final_output_already_exists_without_summary:{out}")
        out.parent.mkdir(parents=True,exist_ok=True); shutil.copytree(local,out)
        print("\n"+"="*212); print("POSTV16-AV4-PIVOT-P2-R6-R8: PASS"); print("Classification                                  :",classification); print("T1A connectivity-only feasible groups           :",nT1A); print("T1B new-endpoint single-shell feasible groups   :",nT1B); print("Still infeasible after single shell             :",nfail); print("Localized deficient CVs                         :",len(defrows)); print("Compact support memberships                     :",len(compact)); print("74M explicit edges re-emitted                   : False"); print("Day375 state mutation                           : False"); print("P2-R6-R9 projection execution authorized        :",exec_auth); print("P2-R6-R9 second-stage design authorized         :",design_auth); print("P3 authorized                                   : False"); print("="*212); return 0
    except Exception as exc:
        block.mkdir(parents=True,exist_ok=True); rp=block/"POSTV16_AV4_PIVOT_P2_R6_R8_Blocked_Report.json"
        if not rp.exists(): rp.write_text(json.dumps({"milestone":MILESTONE,"status":STATUS_BLOCKED,"failed_stage":stage,"exception":repr(exc),"state_mutation_executed":False,"automatic_rerun_authorized":False,"support_growth_execution_authorized":False,"new_H2_endpoint_execution_authorized":False,"pressure_refresh_authorized":False,"time_advance_authorized":False,"P3_authorized":False,"P4_authorized":False,"P5_training_authorized":False,"gates_completed":gates},indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(MILESTONE+": BLOCKED"); print("Stage:",stage); print("Exception:",repr(exc)); return 2

def parse_args():
    p=argparse.ArgumentParser(); p.add_argument("--project-root",type=Path,default=Path(".")); p.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute")); p.add_argument("--self-test",action="store_true"); return p.parse_args()
if __name__=="__main__":
    a=parse_args()
    if a.self_test: self_test(); raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))
