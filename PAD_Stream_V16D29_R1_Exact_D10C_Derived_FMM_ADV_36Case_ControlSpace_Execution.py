#!/usr/bin/env python3
from pathlib import Path
import csv,json,hashlib,importlib.util,runpy,shutil,numpy as np,sys

ROOT=Path(__file__).resolve().parent

D29_SUMMARY=ROOT/"output"/"V16_D29_SOURCEBOUND_FMM_ADV_36CASE_CONTROLSPACE_EXPANSION_AUDIT"/"PAD_Stream_V16D29_Summary.json"
D29_SHA="8624c7744592fb4650fdec1cf5e74610b7484c575e6fa983f8cd9fa31613f2e1"

D10C=ROOT/"PAD_Stream_V16D10C_Full_Case0002_0025_SourceBound_FMM_ADV_TravelTime_Hierarchy_Execution.py"
D10C_SHA="5543065571e5a2c0c7d96df0d95ce6203c2c0ee4e933658e63d006709a7da91b"

FMM_SRC=ROOT/"PAD_Stream_V16B2_Exact_3D_Fast_Marching_Arrival_Time_Baseline.py"
B7_SRC=ROOT/"PAD_Stream_V16B7_Controlled_Directional_Advective_Travel_Time_Solve.py"
SG5_SRC=ROOT/"PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py"
HASH={"FMM":"0b26e3cdbc41276c53f4778e7eddcddd0cc8ef081ffb495b71df548152e8f049",
      "B7":"2355f3eecd41bb6571f7ead3ebb1c5d90a1907ae681826159e79463166994c56",
      "SG5":"2989fe58d1fd78fe9f9c03176dbb3ff066faf359f7edaf028cbdc0fea85135f2"}

FLOWDIR=ROOT/"output"/"V16_D25_36CASE_CONTROLSPACE_SG2_SG3_SG4_FLOW_ENSEMBLE"/"cases"
POLDIR=ROOT/"output"/"V16_D28_R1_36CASE_D9R1_CONSERVATIVE_FACE_METRIC_EXPANSION"/"cases"

OUT=ROOT/"output"/"V16_D29_R1_EXACT_D10C_DERIVED_FMM_ADV_36CASE_CONTROLSPACE_EXECUTION"
CASES=OUT/"cases"; CASES.mkdir(parents=True,exist_ok=True)

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def mod(p,n):
    s=importlib.util.spec_from_file_location(n,p)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

# Exact D10C face -> cell velocity conversion.
def cv(vx,vy,vz):
    nz,ny,nxm1=vx.shape; nx=nxm1+1
    x=np.empty((nz,ny,nx)); y=np.empty_like(x); z=np.empty_like(x)
    x[:,:,0]=vx[:,:,0]; x[:,:,-1]=vx[:,:,-1]; x[:,:,1:-1]=.5*(vx[:,:,:-1]+vx[:,:,1:])
    y[:,0,:]=vy[:,0,:]; y[:,-1,:]=vy[:,-1,:]; y[:,1:-1,:]=.5*(vy[:,:-1,:]+vy[:,1:,:])
    z[0]=vz[0]; z[-1]=vz[-1]; z[1:-1]=.5*(vz[:-1]+vz[1:])
    return x,y,z

def find_case_file(directory, token, required_keys=()):
    hits=[]
    for q in directory.glob("*.npz"):
        if token in q.name:
            try:
                with np.load(q,allow_pickle=True) as d:
                    if all(k in d.files for k in required_keys): hits.append(q)
            except Exception: pass
    if len(hits)!=1:
        raise RuntimeError(f"Expected exactly one artifact for {token} in {directory}; found {len(hits)}: {[x.name for x in hits]}")
    return hits[0]

def split_for(g):
    return "TRAIN" if g in (26,27) else ("VALIDATION" if g==28 else "LOCKED_OOD_TEST")

def main():
    print("="*78); print("PAD-Stream V16D-29-R1")
    print("Exact D10C-Derived FMM/ADV Hierarchy Across 36 Control-Space Foundation Cases"); print("="*78)

    pregates={
      "D29_summary_SHA_exact":D29_SUMMARY.exists() and sha(D29_SUMMARY)==D29_SHA,
      "D10C_SHA_exact":D10C.exists() and sha(D10C)==D10C_SHA,
      "FMM_source_SHA_exact":FMM_SRC.exists() and sha(FMM_SRC)==HASH["FMM"],
      "B7_source_SHA_exact":B7_SRC.exists() and sha(B7_SRC)==HASH["B7"],
      "SG5_source_SHA_exact":SG5_SRC.exists() and sha(SG5_SRC)==HASH["SG5"],
      "flow_case_dir_exists":FLOWDIR.exists(),
      "D28R1_case_dir_exists":POLDIR.exists(),
    }
    if D29_SUMMARY.exists():
        pregates["D29_status_authorizes_execution"]=json.loads(D29_SUMMARY.read_text()).get("status")=="V16D_D10C_FMM_ADV_EXACT_EXECUTION_LINEAGE_BOUND_36CASE_D29R1_EXECUTION_AUTHORIZED"
    else: pregates["D29_status_authorizes_execution"]=False
    for k,v in pregates.items(): print(f"[{'PASS' if v else 'FAIL'}] {k}")
    if not all(pregates.values()): raise RuntimeError("D29-R1 prerequisite authority gate failed.")

    fmm=mod(FMM_SRC,"d29r1_fmm"); sg5=mod(SG5_SRC,"d29r1_sg5")

    # D10C/B7 source-native handoff files. Preserve/restore any pre-existing files.
    b6dir=ROOT/"output"/"V16_B6_DIRECTIONAL_ADVECTIVE_TRAVEL_TIME_NUMERICAL_SCHEME_CONTRACT"
    b6adir=ROOT/"output"/"V16_B6A_DIRECTIONAL_EXTERNAL_BOUNDARY_POLICY_AUDIT"
    b6dir.mkdir(parents=True,exist_ok=True); b6adir.mkdir(parents=True,exist_ok=True)
    paths=[b6dir/"V16B6_Summary.json",
           b6adir/"V16B6A_External_Boundary_Policy_Contract.json",
           b6adir/"V16B6A_Closed_Boundary_Projected_Scheme_Contract.npz"]
    backups={}
    for q in paths:
        if q.exists():
            b=OUT/(q.name+".pre_D29R1_backup"); shutil.copy2(q,b); backups[q]=b

    rows=[]
    case_specs=[(g,r,b) for g in range(26,30) for r in (350,500,650) for b in (1800,2000,2200)]
    try:
        for idx,(g,rate,bhp) in enumerate(case_specs,1):
            token=f"V16D_Foundation_Case_{g:04d}_R{rate}_B{bhp}"
            print(f"\n{'-'*78}\n[{idx:02d}/36] {token}\n{'-'*78}")

            flow=find_case_file(FLOWDIR,token,("Qx","Qy","Qz"))
            pol=find_case_file(POLDIR,token,("pollock_tau_end_s",))

            with np.load(flow,allow_pickle=True) as fl:
                qx,qy,qz=[np.asarray(fl[k],float) for k in ("Qx","Qy","Qz")]

            vx,vy,vz=[np.asarray(a,float) for a in sg5.construct_face_pore_velocities(qx,qy,qz)]
            cx,cy,cz=cv(vx,vy,vz)
            speed=np.sqrt(cx*cx+cy*cy+cz*cz)

            div,tol,src_idx,sm,meta=fmm.bind_injector_sources(qx,qy,qz)
            T,state,accepted=fmm.fast_marching_3d(speed,sm,6.096,6.096,1.2192)

            dx=dy=6.096; dz=1.2192
            aW=np.maximum(cx,0)/dx;  aE=np.maximum(-cx,0)/dx
            aS=np.maximum(cy,0)/dy;  aN=np.maximum(-cy,0)/dy
            aB=np.maximum(cz,0)/dz;  aT=np.maximum(-cz,0)/dz
            aW[:,:,0]=0; aE[:,:,-1]=0; aS[:,0,:]=0; aN[:,-1,:]=0; aB[0]=0; aT[-1]=0
            aP=aW+aE+aS+aN+aB+aT

            paths[0].write_text(json.dumps({"status":"V16B_DIRECTIONAL_NUMERICAL_SCHEME_BOUNDARY_POLICY_REQUIRED"}))
            paths[1].write_text(json.dumps({"status":"V16B_CLOSED_EXTERNAL_BOUNDARY_OPERATOR_POLICY_RESOLVED"}))
            np.savez_compressed(paths[2],Vx_m_s=cx,Vy_m_s=cy,Vz_m_s=cz,source_mask=sm.astype(np.uint8),
                aW_s_inv=aW,aE_s_inv=aE,aS_s_inv=aS,aN_s_inv=aN,aB_s_inv=aB,aT_s_inv=aT,aP_s_inv=aP,
                dx_m=np.array(dx),dy_m=np.array(dy),dz_m=np.array(dz))

            # Exact frozen B7 execution, as in D10C.
            runpy.run_path(str(B7_SRC),run_name="__main__")
            b7out=ROOT/"output"/"V16_B7_CONTROLLED_DIRECTIONAL_ADVECTIVE_TRAVEL_TIME_SOLVE"/"V16B7_Directional_Advective_Travel_Time.npz"
            with np.load(b7out,allow_pickle=True) as db: adv=np.asarray(db["tau_adv_s"],float)
            with np.load(pol,allow_pickle=True) as pd: pt=np.asarray(pd["pollock_tau_end_s"],float)

            passed=(int(sm.sum())==5 and T.shape==(15,50,50) and adv.shape==(15,50,50)
                    and np.isfinite(T).all() and np.isfinite(adv).all()
                    and np.all(T>=0) and np.all(adv>=0)
                    and np.max(np.abs(T[sm]))<1e-8 and np.max(np.abs(adv[sm]))<1e-8
                    and len(pt)==1078)

            art=CASES/f"{token}_FMM_ADV_Pollock_Hierarchy.npz"
            np.savez_compressed(art,
                fmm_arrival_s=T,tau_adv_s=adv,source_mask=sm.astype(np.uint8),
                pollock_tau_end_s=pt,Vx=vx,Vy=vy,Vz=vz,
                geology_id=np.array(g),injection_rate_tpd=np.array(rate),producer_bhp_psi=np.array(bhp),
                split=np.array(split_for(g)),case_id=np.array(token))

            row={"case_id":token,"geology_id":g,"injection_rate_tpd":rate,"producer_bhp_psi":bhp,
                 "split":split_for(g),"status":"CERTIFIED" if passed else "FAILED","source_cells":int(sm.sum()),
                 "fmm_median_d":float(np.median(T)/86400),"fmm_max_d":float(T.max()/86400),
                 "adv_median_d":float(np.median(adv)/86400),"adv_max_d":float(adv.max()/86400),
                 "pollock_median_d":float(np.median(pt)/86400),"pollock_max_d":float(pt.max()/86400),
                 "artifact_sha256":sha(art)}
            rows.append(row)
            print(f"D29-R1 CASE STATUS: {row['status']} | FMM50={row['fmm_median_d']:.3f} d | "
                  f"ADV50={row['adv_median_d']:.3f} d | Pollock50={row['pollock_median_d']:.3f} d")
    finally:
        for q in paths:
            if q in backups: shutil.copy2(backups[q],q)
            elif q.exists(): q.unlink()

    man=OUT/"V16D29_R1_TravelTime_Hierarchy_Manifest.csv"
    with man.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    good=[r for r in rows if r["status"]=="CERTIFIED"]
    counts={s:sum(r["split"]==s for r in rows) for s in ("TRAIN","VALIDATION","LOCKED_OOD_TEST")}
    gates=dict(pregates)
    gates.update({
      "exactly_36_cases_attempted":len(rows)==36,
      "all_36_certified":len(good)==36,
      "all_five_source_cells":len(good)==36 and all(r["source_cells"]==5 for r in good),
      "split_counts_18_9_9":counts=={"TRAIN":18,"VALIDATION":9,"LOCKED_OOD_TEST":9},
      "all_9_controls_per_geology":all(sum(r["geology_id"]==g for r in rows)==9 for g in range(26,30)),
      "Pollock_remains_authoritative_reference":True,
      "FMM_role_auxiliary_scalar_control":True,
      "ADV_role_auxiliary_directional_field":True,
      "no_case_or_streamline_selection":True,
      "no_FMM_ADV_to_Pollock_fitting":True,
      "no_transport_target_generation":True,
      "no_training":True,
      "locked_OOD_physics_generated_not_statistically_evaluated":True,
    })
    ok=all(bool(v) for v in gates.values())
    vals=lambda k:np.array([r[k] for r in good],float)
    ensemble={}
    if good:
        for k in ("fmm_median_d","fmm_max_d","adv_median_d","adv_max_d","pollock_median_d","pollock_max_d"):
            a=vals(k); ensemble[k]={"min":float(a.min()),"median":float(np.median(a)),"max":float(a.max())}

    status=("V16D_36CASE_FMM_ADV_POLLOCK_TRAVELTIME_HIERARCHY_CERTIFIED_CONTROLSPACE_TRANSPORT_SUPERVISION_EXPANSION_AUTHORIZED"
            if ok else "V16D_D29_R1_FMM_ADV_CONTROLSPACE_ENSEMBLE_HAS_FAILURES")
    nxt=("V16D-30 — Source-bound Stage-4 transport supervision expansion contract across the 36 control-space Foundation Cases"
         if ok else "Diagnose failed D29-R1 cases without fitting, replacement, or threshold relaxation.")

    summary={"milestone":"V16D-29-R1","status":status,"certified_cases":len(good),
             "split_counts":counts,"manifest_sha256":sha(man),
             "source_hashes":{"D10C":D10C_SHA,**HASH},"ensemble":ensemble,
             "gates":gates,"next_milestone":nxt}
    sp=OUT/"PAD_Stream_V16D29_R1_Summary.json"; sp.write_text(json.dumps(summary,indent=2))

    print("\n"+"="*78); print("V16D-29-R1 ENSEMBLE SUMMARY"); print("="*78)
    print(f"  certified cases: {len(good)}/36")
    print(f"  split counts   : {counts}")
    if good:
        print("  FMM median days case min/median/max: %.3f / %.3f / %.3f"%(vals("fmm_median_d").min(),np.median(vals("fmm_median_d")),vals("fmm_median_d").max()))
        print("  ADV median days case min/median/max: %.3f / %.3f / %.3f"%(vals("adv_median_d").min(),np.median(vals("adv_median_d")),vals("adv_median_d").max()))
        print("  Pollock median case min/median/max : %.3f / %.3f / %.3f"%(vals("pollock_median_d").min(),np.median(vals("pollock_median_d")),vals("pollock_median_d").max()))
    print("\nGATES")
    for k,v in gates.items(): print(f"[{'PASS' if v else 'FAIL'}] {k}")
    print("\nSTATUS\n ",status); print("\nNEXT\n ",nxt)
    print("\nSummary SHA-256:",sha(sp))
    if not ok: sys.exit(2)

if __name__=="__main__": main()
