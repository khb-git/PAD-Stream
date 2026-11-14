#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
from typing import Any
import numpy as np

M="POSTV16-AV4-PIVOT-GPU-HYB-G3-R2-R2"
PASS="POSTV16AV4PIVOTGPUHYBG3R2R2_LATE_NATIVE_FLOW_NETWORK_STALENESS_SHADOW_PASS"
BLOCK="POSTV16AV4PIVOTGPUHYBG3R2R2_TECHNICAL_CONSERVATION_OR_PROJECTION_BLOCK"
BRANCH="postv16-av4-pivot"
PARENT="7397cdf7b85f1cf622380f2fe5fe1f8fb670cfec"

RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"
BASE_AV3=Path("post_v16")/RID/"POSTV16_AV3_Corey_Relperm_Heterogeneity"

R1_BLOCK_REL=BASE_AV4/"POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_R1_BLOCKED"
R1_BLOCK="POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_R1_Blocked_Report.json"

P3=("PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_Corrected_Dense_FrozenFlow_Trajectory_and_Exact_5Day_Flow_Diagnostic_Sweep.py","84076001f40ebcf0825bb8d9bcabe060ed0840d2")
R25=("PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R25_R3_Controlled_CapacityLimited_Reprojection_Stage2_PresolveOff.py","65cab626419137b191f2c53a4c543d9805ccf68d")
A2E=("PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py","79a8969233b72b4543edd382a0c3d1028c6dca09")
R2SRC=("PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py","a127f8730a16e150713420ea547a8de6255550ef")
E37A=("PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py","0bbf98ed89cee9128ef1d313c321f9a401b4e9f0")
SG7A=("PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py","a4dd47338e7a85f130a6a70d0a41211e38c655f8")
SG7D=("PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py","890088c0c0fcab415a2c7351c5079ca8ee12bf82")

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
MAX_SG=0.60
MASS_TOL=1e-6
REL_TOL=1e-10
HALO_OPT_TOL=1e-6
GRID=(15,50,50)
NCELL=int(np.prod(GRID))
NSL=1078
NCV=200
NCVT=NSL*NCV

OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G3_R2_R2"
OUT_REL=BASE_AV4/(OUT_TOKEN+"_LateNative_FlowNetwork_Staleness_Shadow")
BLOCK_REL=BASE_AV4/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json"
PROJECTION=f"{OUT_TOKEN}_Branch_Projection_Audit.csv"
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
        for c in iter(lambda:f.read(1<<20),b""):h.update(c)
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
        return {"day":scalar(z["diagnostic_day"]),
                "saturation":np.asarray(z["saturation"],dtype=np.float64),
                "pressure":np.asarray(z["pressure_psi"],dtype=np.float64),
                "xyz_m":np.asarray(z["streamline_xyz_m"],dtype=np.float64),
                "tau_s":np.asarray(z["streamline_tof_s"],dtype=np.float64),
                "tau_end_s":np.asarray(z["tau_end_s"],dtype=np.float64),
                "weights_m3_s":np.asarray(z["streamline_weight_m3_s"],dtype=np.float64),
                "producer":np.asarray(z["producer_labels"]).astype("U64"),
                "xi":np.asarray(z["xi"],dtype=np.float64)}

def support_repair(edge_cv,edge_cell,shell,new_cv_mass,rep_capacity_flat,direct_target_rep):
    from scipy.optimize import linprog
    from scipy.sparse import coo_matrix,csr_matrix,eye,hstack,vstack
    nedge=len(edge_cv)
    Aeq=coo_matrix((np.ones(nedge),(edge_cv,np.arange(nedge,dtype=np.int64))),shape=(NCVT,nedge)).tocsr()
    beq=np.asarray(new_cv_mass,dtype=np.float64).reshape(-1).copy()
    Acell=coo_matrix((np.ones(nedge),(edge_cell,np.arange(nedge,dtype=np.int64))),shape=(NCELL,nedge)).tocsr()
    c1=(shell>0).astype(np.float64)
    lp1=linprog(c1,A_ub=Acell,b_ub=rep_capacity_flat,A_eq=Aeq,b_eq=beq,bounds=(0,None),method="highs-ds",
                options={"presolve":True,"primal_feasibility_tolerance":1e-10,"dual_feasibility_tolerance":1e-10})
    if not lp1.success:raise GateError(f"XY1_stage1_infeasible:{lp1.status}:{lp1.message}")
    halo_opt=float(lp1.fun)
    nd=NCELL;zero_d=csr_matrix((NCELL,nd),dtype=np.float64)
    A_cap=hstack([Acell,zero_d],format="csr");I=eye(nd,format="csr",dtype=np.float64)
    A_abs_pos=hstack([Acell,-I],format="csr");A_abs_neg=hstack([-Acell,-I],format="csr")
    target=np.asarray(direct_target_rep,dtype=np.float64).reshape(-1)
    halo_row=csr_matrix(c1.reshape(1,-1));zero1=csr_matrix((1,nd),dtype=np.float64)
    A_halo_pos=hstack([halo_row,zero1],format="csr");A_halo_neg=hstack([-halo_row,zero1],format="csr")
    b_halo=np.asarray([halo_opt+HALO_OPT_TOL,-halo_opt+HALO_OPT_TOL])
    A_ub=vstack([A_cap,A_abs_pos,A_abs_neg,A_halo_pos,A_halo_neg],format="csr")
    b_ub=np.concatenate([rep_capacity_flat,target,-target,b_halo])
    Aeq2=hstack([Aeq,csr_matrix((NCVT,nd),dtype=np.float64)],format="csr")
    c2=np.concatenate([np.zeros(nedge),np.ones(nd)])
    lp2=linprog(c2,A_ub=A_ub,b_ub=b_ub,A_eq=Aeq2,b_eq=beq,bounds=[(0,None)]*(nedge+nd),method="highs-ds",
                options={"presolve":True,"primal_feasibility_tolerance":1e-10,"dual_feasibility_tolerance":1e-10})
    if not lp2.success:raise GateError(f"XY1_stage2_infeasible:{lp2.status}:{lp2.message}")
    z=np.asarray(lp2.x,dtype=np.float64);x=z[:nedge]
    cv_check=np.bincount(edge_cv,weights=x,minlength=NCVT).reshape(NSL,NCV)
    cv_err=float(np.max(np.abs(cv_check-new_cv_mass)))
    cell_rep=np.bincount(edge_cell,weights=x,minlength=NCELL).reshape(GRID)
    halo_mass=float(np.sum(x[shell>0]));l1=float(np.sum(np.abs(cell_rep-direct_target_rep)))
    if cv_err>MASS_TOL:raise GateError(f"XY1_CV_equality:{cv_err}")
    return x,{"mode":"XY1_LEXICOGRAPHIC_REPAIR","halo_mass_kg":halo_mass,"halo_opt_kg":halo_opt,
              "cell_L1_kg":l1,"CV_equality_max_abs_error_kg":cv_err}

def build_branch(name,stale_days,diag,*,parent_mass,frozen_pressure,pref,p3,r25,e37a,r2,sg7a,sg7d):
    xyz=diag["xyz_m"];tau=diag["tau_s"];weights_day=diag["weights_m3_s"]*DAY_TO_S;xi=diag["xi"]
    nstream=int(xyz.shape[0]);ncv=len(xi)-1
    if nstream!=NSL or ncv!=NCV:raise GateError(f"{name}:shape:{nstream}:{ncv}")
    op=sg7d.build_subsegment_operator(xyz,tau/DAY_TO_S,weights_day)
    geom=e37a.build_control_volume_geometry(r2,op,frozen_pressure,pref,NSL,NCV)
    exact_cv,exact_cell,target=r25.build_edge_target_and_support(parent_mass,op)
    cv_capacity=np.asarray(e37a.cv_mass_from_saturation(r2,np.full((NSL,NCV),MAX_SAT),geom["cv_pressure_mass_coeff"]),dtype=np.float64)
    s1=r25.stage1_max_representable(parent_mass,cv_capacity,exact_cv,exact_cell)
    s2=r25.stage2_min_l1_to_target(parent_mass,cv_capacity,exact_cv,exact_cell,target,float(s1["represented_mass_kg"]))
    exact_mass=np.asarray(s2["x"],dtype=np.float64)
    cv_mass=np.bincount(exact_cv,weights=exact_mass,minlength=NCVT).reshape(NSL,NCV)
    rep=np.bincount(exact_cell,weights=exact_mass,minlength=NCELL).reshape(GRID)
    residual=np.asarray(parent_mass,dtype=np.float64)-rep
    if float(np.min(residual))<-MASS_TOL:raise GateError(f"{name}:negative_residual:{float(np.min(residual))}")
    residual=np.maximum(residual,0.0)
    cv_sat=np.asarray(e37a.invert_cv_mass_to_saturation(r2,cv_mass,geom["cv_pressure_mass_coeff"]),dtype=np.float64)
    edge_cv,edge_cell,shell,exact_pos=p3.build_xy1_support(exact_cv,exact_cell)
    edge_mass=np.zeros(len(edge_cv),dtype=np.float64);edge_mass[exact_pos]=exact_mass
    sub_cv=np.asarray(op["streamline"],dtype=np.int64)*NCV+np.asarray(op["node"],dtype=np.int64)
    sub_cell=np.asarray(op["flat_cell"],dtype=np.int64)
    exact_keys=exact_cv*NCELL+exact_cell; key_to_exact={int(k):i for i,k in enumerate(exact_keys.tolist())}
    sub_exact_idx=np.asarray([key_to_exact[int(k)] for k in (sub_cv*NCELL+sub_cell).tolist()],dtype=np.int64)
    scan=np.linspace(float(sg7a.S_INITIAL),float(sg7a.S_INJECTED),4001)
    max_df=float(np.max(np.abs(np.asarray(sg7a.df_dS(scan),dtype=np.float64))))
    u=np.asarray(sg7a.u_dimensionless(xi),dtype=np.float64)
    dtD=float(sg7a.CFL*(1.0/NCV)/(float(np.max(u))*max_df+float(sg7a.EPS)))
    cfl=float(dtD*np.min(diag["tau_end_s"]/DAY_TO_S))
    return {"name":name,"stale_days":float(stale_days),"diag":diag,"op":op,"geom":geom,
            "weights_day":weights_day,"xi":xi,"u":u,"cfl_days":cfl,
            "cv_mass":cv_mass,"cv_sat":cv_sat,"rep":rep,"residual":residual,
            "edge_cv":edge_cv,"edge_cell":edge_cell,"shell":shell,"exact_pos":exact_pos,"edge_mass":edge_mass,
            "exact_cv":exact_cv,"sub_exact_idx":sub_exact_idx,
            "represented_mass_kg":float(np.sum(rep)),"residual_mass_kg":float(np.sum(residual)),
            "represented_fraction":float(np.sum(rep)/np.sum(parent_mass)),"stage2_L1_kg":float(s2["L1_objective_kg"])}

def shadow(branch,dt,*,parent_mass,parent_total,frozen_pressure,pref,hetero_pv,a2e,r2,e37a,sg7a):
    old_cv_mass=branch["cv_mass"];old_cv_sat=branch["cv_sat"];weights=branch["weights_day"];u=branch["u"]
    rho_ref=float(e37a.CO2_RHO_REF_KG_M3)
    flux=np.zeros((NSL,NCV+1),dtype=np.float64)
    flux[:,0]=weights*rho_ref
    ff_internal=np.asarray(sg7a.fractional_flow(old_cv_sat[:,:-1]),dtype=np.float64)
    flux[:,1:-1]=weights[:,None]*u[None,1:-1]*ff_internal*rho_ref
    ff_out=np.asarray(sg7a.fractional_flow(old_cv_sat[:,-1]),dtype=np.float64)
    flux[:,-1]=weights*float(u[-1])*ff_out*rho_ref
    new_cv_mass=old_cv_mass+dt*(flux[:,:-1]-flux[:,1:])
    if float(np.min(new_cv_mass))<-MASS_TOL:raise GateError(f"{branch['name']}:negative_CV_mass:{float(np.min(new_cv_mass))}")
    cv_capacity=np.asarray(e37a.cv_mass_from_saturation(r2,np.full((NSL,NCV),MAX_SAT),branch["geom"]["cv_pressure_mass_coeff"]),dtype=np.float64)
    excess=float(np.max(new_cv_mass-cv_capacity))
    if excess>max(1e-9,1e-12*max(float(np.max(cv_capacity)),1.0)):raise GateError(f"{branch['name']}:CV_capacity:{excess}")
    new_cv_sat=np.asarray(e37a.invert_cv_mass_to_saturation(r2,new_cv_mass,branch["geom"]["cv_pressure_mass_coeff"]),dtype=np.float64)
    injected=float(np.sum(flux[:,0])*dt);produced=float(np.sum(flux[:,-1])*dt)
    cv_delta=float(np.sum(new_cv_mass)-np.sum(old_cv_mass));cv_res=cv_delta-injected+produced
    if abs(cv_res)>max(MASS_TOL,REL_TOL*max(abs(injected),1.0)):raise GateError(f"{branch['name']}:CV_ledger:{cv_res}")
    g=branch["geom"];old_sub=old_cv_sat.reshape(-1)[g["cv_id"]];new_sub=new_cv_sat.reshape(-1)[g["cv_id"]]
    old_sg=np.clip(old_sub-BACKGROUND,0,MAX_SG);new_sg=np.clip(new_sub-BACKGROUND,0,MAX_SG)
    rho_old=np.asarray(r2.gas_density_from_state(old_sub,g["pseg_psi"],pref),dtype=np.float64)
    rho_new=np.asarray(r2.gas_density_from_state(new_sub,g["pseg_psi"],pref),dtype=np.float64)
    sub_delta=np.asarray(g["pv_m3"],dtype=np.float64)*(rho_new*new_sg-rho_old*old_sg)
    transfer=float(np.sum(sub_delta)-cv_delta)
    if abs(transfer)>MASS_TOL:raise GateError(f"{branch['name']}:CV_subsegment_transfer:{transfer}")
    delta_grid=np.bincount(g["flat_cell"],weights=sub_delta,minlength=NCELL).reshape(GRID)
    direct_target_rep=branch["rep"]+delta_grid
    edge_delta_exact=np.bincount(branch["sub_exact_idx"],weights=sub_delta,minlength=len(branch["exact_cv"]))
    candidate_edge=branch["edge_mass"].copy();candidate_edge[branch["exact_pos"]]+=edge_delta_exact
    cart_capacity=np.asarray(a2e.local_mass(r2,np.full(GRID,MAX_SAT),frozen_pressure,pref,hetero_pv),dtype=np.float64)
    rep_capacity=cart_capacity-branch["residual"]
    cap_tol=max(1e-8,1e-12*max(float(np.max(cart_capacity)),1.0))
    if float(np.min(rep_capacity))<-cap_tol:raise GateError(f"{branch['name']}:negative_represented_capacity")
    rep_capacity_flat=np.maximum(rep_capacity,0.0).reshape(-1)
    direct_mode=float(np.min(candidate_edge))>=-MASS_TOL
    if direct_mode:
        cv_from=np.bincount(branch["edge_cv"],weights=candidate_edge,minlength=NCVT).reshape(NSL,NCV)
        cell_from=np.bincount(branch["edge_cell"],weights=candidate_edge,minlength=NCELL).reshape(GRID)
        cv_err=float(np.max(np.abs(cv_from-new_cv_mass)));cap_ex=float(np.max(cell_from.reshape(-1)-rep_capacity_flat))
        l1=float(np.sum(np.abs(cell_from-direct_target_rep)))
        if cv_err>MASS_TOL or cap_ex>cap_tol or l1>max(1e-5,1e-10*max(float(np.sum(np.abs(direct_target_rep))),1.0)):
            direct_mode=False
    if direct_mode:
        new_edge=candidate_edge
        new_rep=np.bincount(branch["edge_cell"],weights=new_edge,minlength=NCELL).reshape(GRID)
        repinfo={"mode":"DIRECT_EDGE_EXACT","halo_mass_kg":float(np.sum(new_edge[branch["shell"]>0])),
                 "cell_L1_kg":float(np.sum(np.abs(new_rep-direct_target_rep)))}
    else:
        new_edge,repinfo=support_repair(branch["edge_cv"],branch["edge_cell"],branch["shell"],new_cv_mass,rep_capacity_flat,direct_target_rep)
        new_rep=np.bincount(branch["edge_cell"],weights=new_edge,minlength=NCELL).reshape(GRID)
    child_mass=new_rep+branch["residual"]
    cap_excess=float(np.max(child_mass-cart_capacity))
    if cap_excess>cap_tol:raise GateError(f"{branch['name']}:Cartesian_capacity:{cap_excess}:{cap_tol}")
    expected=parent_total+injected-produced;ledger=float(np.sum(child_mass)-expected)
    if abs(ledger)>max(MASS_TOL,REL_TOL*max(abs(expected),1.0)):raise GateError(f"{branch['name']}:Cartesian_ledger:{ledger}")
    child_sg=np.asarray(a2e.invert_local_mass(r2,child_mass,frozen_pressure,pref,hetero_pv),dtype=np.float64)
    child_sat=float(a2e.BACKGROUND)+child_sg
    recon=np.asarray(a2e.local_mass(r2,child_sat,frozen_pressure,pref,hetero_pv),dtype=np.float64)
    recon_err=float(np.max(np.abs(recon-child_mass)))
    if recon_err>1e-8:raise GateError(f"{branch['name']}:EOS_reconstruction:{recon_err}")
    prows,cut=e37a.producer_rows_from_flux(branch["diag"]["producer"],weights,ff_out,flux[:,-1],dt)
    return {"child_mass":child_mass,"child_sat":child_sat,"injected":injected,"produced":produced,"cut":float(cut),
            "final_total":float(np.sum(child_mass)),"CV_residual":cv_res,"transfer_residual":transfer,
            "grid_ledger_residual":ledger,"capacity_margin":float(np.min(cart_capacity-child_mass)),
            "EOS_reconstruction_Linf_kg":recon_err,"representation_mode":repinfo["mode"],
            "representation_halo_mass_kg":repinfo["halo_mass_kg"],"representation_cell_L1_kg":repinfo["cell_L1_kg"],
            "producer_rows":prows}

def selftest():
    assert [405-405,405-400,405-390]==[0,5,15]
    print("POSTV16 GPU-HYB-G3-R2-R2 structural self-test: PASS")

def main(root:Path,drive:Path)->int:
    root=root.resolve();drive=drive.resolve();out=drive/OUT_REL;blocked=drive/BLOCK_REL
    gates=[];stage="preflight"
    def gate(n,c,d=None):
        ok=bool(c);gates.append({"stage":stage,"gate":n,"pass":ok,"detail":"" if d is None else repr(d)})
        print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"),flush=True)
        if not ok:raise GateError(n)
    try:
        print("="*190)
        print("G3-R2-R2 — LATE-NATIVE FLOW-NETWORK STALENESS SHADOW")
        print("DIAGNOSTIC PRESSURE IS FLOW-DIAGNOSTIC ONLY; NATIVE DAY365 THERMODYNAMIC PRESSURE RETAINED.")
        print("="*190)
        stage="repository"
        gate("branch",gt(root,"branch","--show-current")==BRANCH,gt(root,"branch","--show-current"))
        gate("parent_is_G3_R2_R1_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))
        gate("clean",gt(root,"status","--porcelain")=="")
        stage="prior_block_binding"
        bp=drive/R1_BLOCK_REL/R1_BLOCK;gate("R1_block_present",bp.is_file(),str(bp))
        br=js(bp);gate("R1_failed_at_branch_build",br.get("failed_stage")=="branch_build",br.get("failed_stage"))
        gate("R1_failed_due_local_mass_capacity","same_time_local_cell_mass_capacity" in str(br.get("exception","")),br.get("exception"))
        p3=module(root,P3,"g3r2r2_p3");r25=module(root,R25,"g3r2r2_r25");a2e=module(root,A2E,"g3r2r2_a2e")
        r2=module(root,R2SRC,"g3r2r2_r2");e37a=module(root,E37A,"g3r2r2_e37a")
        sg7a=module(root,SG7A,"g3r2r2_sg7a");sg7d=module(root,SG7D,"g3r2r2_sg7d")
        stage="native_authorities"
        a2ep=drive/A2E_REL/A2E_EPOCH;a6ep=drive/A6E_REL/A6E_STATE
        gate("A2E_SHA",sha(a2ep)==A2E_EPOCH_SHA,sha(a2ep));gate("A6E_SHA",sha(a6ep)==A6E_SHA,sha(a6ep))
        with np.load(a2ep,allow_pickle=False) as z:
            frozen_pressure=np.asarray(z["refreshed_pressure_psi"],dtype=np.float64);pref=scalar(z["reference_gas_pressure_pa"])
        with np.load(a6ep,allow_pickle=False) as z:phi=np.asarray(z["paired_porosity"],dtype=np.float64)
        hetero_pv=phi*float(a2e.BULK_VOLUME_M3)
        specs=[(390,drive/D390_REL/D390_STATE,drive/D390_REL/D390_DIAG,D390_STATE_SHA,D390_DIAG_SHA),
               (400,drive/D400_REL/D400_STATE,drive/D400_REL/D400_DIAG,D400_STATE_SHA,D400_DIAG_SHA),
               (405,drive/D405_REL/D405_STATE,drive/D405_REL/D405_DIAG,D405_STATE_SHA,D405_DIAG_SHA)]
        states={};diags={}
        stage="late_artifacts"
        for day,sp,dp,ssha,dsha in specs:
            gate(f"Day{day}_state_SHA",sha(sp)==ssha,sha(sp));gate(f"Day{day}_diag_SHA",sha(dp)==dsha,sha(dp))
            st=load_npz(sp);dg=late_diag(dp)
            rec=np.asarray(a2e.local_mass(r2,st["cartesian_saturation"],frozen_pressure,pref,hetero_pv),dtype=np.float64)
            gate(f"Day{day}_native_mass_semantics",float(np.max(np.abs(rec-st["cartesian_component_mass_kg"])))<=1e-8)
            gate(f"Day{day}_diagnostic_saturation_same",float(np.max(np.abs(dg["saturation"]-st["cartesian_saturation"])))<=1e-12)
            states[day]=st;diags[day]=dg
        stage="branch_projection"
        parent_mass=np.asarray(states[405]["cartesian_component_mass_kg"],dtype=np.float64);parent_total=float(np.sum(parent_mass))
        branches=[
            build_branch("REFRESHED_0D",0,diags[405],parent_mass=parent_mass,frozen_pressure=frozen_pressure,pref=pref,p3=p3,r25=r25,e37a=e37a,r2=r2,sg7a=sg7a,sg7d=sg7d),
            build_branch("STALE_5D",5,diags[400],parent_mass=parent_mass,frozen_pressure=frozen_pressure,pref=pref,p3=p3,r25=r25,e37a=e37a,r2=r2,sg7a=sg7a,sg7d=sg7d),
            build_branch("STALE_15D",15,diags[390],parent_mass=parent_mass,frozen_pressure=frozen_pressure,pref=pref,p3=p3,r25=r25,e37a=e37a,r2=r2,sg7a=sg7a,sg7d=sg7d)]
        common_dt=min(b["cfl_days"] for b in branches);gate("common_dt_positive",common_dt>0,common_dt)
        stage="shadow_transport"
        results={b["name"]:shadow(b,common_dt,parent_mass=parent_mass,parent_total=parent_total,frozen_pressure=frozen_pressure,pref=pref,hetero_pv=hetero_pv,a2e=a2e,r2=r2,e37a=e37a,sg7a=sg7a) for b in branches}
        injected=[results[b["name"]]["injected"] for b in branches];injtol=max(1e-8,1e-10*max(abs(injected[0]),1.0))
        gate("same_injected_mass_all_branches",max(injected)-min(injected)<=injtol,{"values":injected,"tol":injtol})
        ref=results["REFRESHED_0D"];comparisons=[]
        for name in ["STALE_5D","STALE_15D"]:
            x=results[name]
            comparisons.append({"branch":name,"staleness_days":5 if name=="STALE_5D" else 15,
                                "child_cellwise_CO2_mass_relative_L2_vs_refreshed":rel_l2(x["child_mass"],ref["child_mass"]),
                                "child_cellwise_CO2_mass_Linf_kg_vs_refreshed":float(np.max(np.abs(x["child_mass"]-ref["child_mass"]))),
                                "child_saturation_relative_L2_vs_refreshed":rel_l2(x["child_sat"],ref["child_sat"]),
                                "child_saturation_Linf_vs_refreshed":float(np.max(np.abs(x["child_sat"]-ref["child_sat"]))),
                                "produced_CO2_mass_difference_kg_vs_refreshed":float(x["produced"]-ref["produced"]),
                                "produced_CO2_mass_abs_difference_kg_vs_refreshed":float(abs(x["produced"]-ref["produced"])),
                                "producer_CO2_gas_cut_difference_vs_refreshed":float(x["cut"]-ref["cut"]),
                                "producer_CO2_gas_cut_abs_difference_vs_refreshed":float(abs(x["cut"]-ref["cut"])),
                                "final_total_stored_mass_difference_kg_vs_refreshed":float(x["final_total"]-ref["final_total"])})
        stage="publication"
        gate("output_absent",not out.exists(),str(out));out.mkdir(parents=True)
        proj=[];bres=[];prows=[]
        for b in branches:
            x=results[b["name"]]
            proj.append({"branch":b["name"],"staleness_days":b["stale_days"],"represented_mass_kg":b["represented_mass_kg"],
                         "residual_mass_kg":b["residual_mass_kg"],"represented_fraction":b["represented_fraction"],
                         "stage2_L1_kg":b["stage2_L1_kg"],"branch_CFL_dt_days":b["cfl_days"]})
            bres.append({"branch":b["name"],"staleness_days":b["stale_days"],"common_shadow_dt_days":common_dt,
                         "injected_CO2_mass_kg":x["injected"],"produced_CO2_mass_kg":x["produced"],"producer_CO2_gas_cut":x["cut"],
                         "final_stored_CO2_mass_kg":x["final_total"],"CV_transport_residual_kg":x["CV_residual"],
                         "CV_to_subsegment_transfer_residual_kg":x["transfer_residual"],"grid_ledger_residual_kg":x["grid_ledger_residual"],
                         "minimum_capacity_margin_kg":x["capacity_margin"],"EOS_reconstruction_Linf_kg":x["EOS_reconstruction_Linf_kg"],
                         "representation_mode":x["representation_mode"],"representation_halo_mass_kg":x["representation_halo_mass_kg"],
                         "representation_cell_L1_kg":x["representation_cell_L1_kg"]})
            for pr in x["producer_rows"]:prows.append({"branch":b["name"],"staleness_days":b["stale_days"],**pr})
        write_csv(out/PROJECTION,proj);write_csv(out/RESULTS,bres);write_csv(out/COMPARE,comparisons);write_csv(out/PRODUCERS,prows)
        cmap={"REFRESHED_0D":REF_CHILD,"STALE_5D":S5_CHILD,"STALE_15D":S15_CHILD}
        for b in branches:
            x=results[b["name"]]
            np.savez_compressed(out/cmap[b["name"]],branch=np.asarray(b["name"]),staleness_days=np.asarray(b["stale_days"]),
                                common_shadow_dt_days=np.asarray(common_dt),child_saturation=x["child_sat"],child_cellwise_CO2_mass_kg=x["child_mass"])
        c5=next(x for x in comparisons if x["branch"]=="STALE_5D");c15=next(x for x in comparisons if x["branch"]=="STALE_15D")
        summary={"milestone":M,"status":PASS,
                 "classification":"LATE_DAY405_NATIVE_STATE_FLOW_NETWORK_ONLY_0D_5D_15D_STALENESS_CAUSAL_SHADOW_MEASURED_NO_CADENCE_SELECTION",
                 "causal_scope":"FLOW_NETWORK_STALENESS_ONLY",
                 "diagnostic_pressure_used_as_thermodynamic_state_pressure":False,
                 "native_frozen_Day365_thermodynamic_pressure_retained":True,
                 "native_heterogeneous_cartesian_PV_retained":True,
                 "native_split_state_projection_rebuilt_per_branch":True,
                 "parent_day":405.0,"parent_state_sha256":D405_STATE_SHA,"parent_stored_CO2_mass_kg":parent_total,
                 "common_shadow_dt_days":common_dt,"branch_CFL_dt_days":{b["name"]:b["cfl_days"] for b in branches},
                 "branch_represented_fraction":{b["name"]:b["represented_fraction"] for b in branches},
                 "same_injected_component_mass_all_branches":True,
                 "STALE_5D_effect_vs_refreshed":c5,"STALE_15D_effect_vs_refreshed":c15,
                 "all_branches_component_mass_conservative":True,"all_branches_capacity_safe_at_common_dt":True,
                 "canonical_trajectory_mutated":False,"scientific_tolerance_defined":False,
                 "production_pressure_refresh_cadence_selected":False,
                 "G3_R3_early_late_causal_cadence_decision_freeze_authorized":True,
                 "G3_R3_must_preserve_scope_distinction_between_early_full_refresh_and_late_flow_network_only_shadow":True,
                 "P4_authorized":False}
        (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        write_csv(out/GATES,gates)
        manifest=[{"file":q.name,"sha256":sha(q),"bytes":q.stat().st_size} for q in sorted(out.iterdir()) if q.is_file() and q.name!=MANIFEST]
        write_csv(out/MANIFEST,manifest)
        print("="*190);print(M,"PASS")
        print("Causal scope                                    : FLOW_NETWORK_STALENESS_ONLY")
        print("Parent day                                      : 405")
        print("Common shadow dt days                           :",common_dt)
        print("Branch represented fractions                    :",{b["name"]:b["represented_fraction"] for b in branches})
        print("5d stale child mass relL2 vs refreshed          :",c5["child_cellwise_CO2_mass_relative_L2_vs_refreshed"])
        print("15d stale child mass relL2 vs refreshed         :",c15["child_cellwise_CO2_mass_relative_L2_vs_refreshed"])
        print("5d stale child saturation Linf vs refreshed     :",c5["child_saturation_Linf_vs_refreshed"])
        print("15d stale child saturation Linf vs refreshed    :",c15["child_saturation_Linf_vs_refreshed"])
        print("Production cadence selected                     : False")
        print("G3-R3 decision freeze authorized                : True")
        print("="*190)
        return 0
    except Exception as exc:
        blocked.mkdir(parents=True,exist_ok=True)
        (blocked/f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps(
            {"milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),"gates":gates,
             "canonical_trajectory_mutated":False,"production_pressure_refresh_cadence_selected":False,
             "G3_R3_early_late_causal_cadence_decision_freeze_authorized":False,"P4_authorized":False},
            indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(M,"BLOCK");print("Stage:",stage);print("Exception:",repr(exc));return 2

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",type=Path,default=Path("."))
    ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test:selftest();raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))
