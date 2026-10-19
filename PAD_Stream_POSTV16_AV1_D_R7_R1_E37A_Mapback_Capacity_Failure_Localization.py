#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, importlib.util, io, json, os, subprocess, sys, tempfile
from pathlib import Path
from typing import Any

import numpy as np

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

MILESTONE = "POSTV16-AV1-D-R7-R1"
STATUS_PASS = (
    "AV1DR7R1_E37A_DAY30_MAPBACK_CAPACITY_FAILURE_LOCALIZED_"
    "NO_REPAIR_SELECTED"
)
STATUS_BLOCKED = "AV1DR7R1_FAILURE_LOCALIZATION_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R7_COMMIT = "391f1919c3eb97546b5e3ca382aee5b3ce91799f"

R7 = "PAD_Stream_POSTV16_AV1_D_R7_Full_End_to_End_PAD_Stream_Integration.py"
R7_BLOB = "a28722b0b8059bd50d94fb8a914defc0b35f2f7b"
R6 = "PAD_Stream_POSTV16_AV1_D_R6_Accepted_PIRNN_Deployment_Promotion_and_Canonical_Runtime_Binding.py"
R6_BLOB = "1ca67ca946683eeb31fbba7d31fba2613d5c0f6f"
C26 = "PAD_Stream_V16C26_EXP2_Physics_Informed_Training_Execution_Best_Validation_Checkpoint_and_Locked_Test_Evaluation.py"
C26_BLOB = "62e19e6b502fb3ab101a2589251c26b5f9ad9031"
C2 = "PAD_Stream_V16C2_Multi_Coordinate_Streamline_Transport_Database_Assembly.py"
C2_BLOB = "21ff44de456102772c99f7ddc80898c9139a76db"
B2 = "PAD_Stream_V16B2_Exact_3D_Fast_Marching_Arrival_Time_Baseline.py"
B2_BLOB = "95025d1e67a74f9dacaad311e5a402b63e7b4335"
B1 = "PAD_Stream_POSTV16_AV1_B1_R1_C26_to_E37A_Component_Mass_Representation_Equivalence_Audit.py"
B1_BLOB = "8d9561d7c85805b82dedc26073c4633f90eeeab6"
R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"

SOURCE_BLOBS = {
    R7:R7_BLOB,R6:R6_BLOB,C26:C26_BLOB,C2:C2_BLOB,B2:B2_BLOB,
    B1:B1_BLOB,R2:R2_BLOB,E37A:E37A_BLOB,SG7D:SG7D_BLOB
}

BASE = Path("post_v16")/RID/"POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
R6_REL = BASE/"POSTV16_AV1_D_R6_Accepted_PIRNN_Deployment_Promotion_and_Canonical_Runtime_Binding"
R6_WEIGHTS = "POSTV16_AV1_D_R6_ACCEPTED_TRANSPORT_FROZEN.weights.h5"
R6_NORM = "POSTV16_AV1_D_R6_C3_Conditioning_Normalization_Parameters.npz"
R7_BLOCKED_REL = BASE/"POSTV16_AV1_D_R7_BLOCKED"
R7_BLOCKED_REPORT = "POSTV16_AV1_D_R7_Blocked_Report.json"
OUT_REL = BASE/"POSTV16_AV1_D_R7_R1_E37A_Mapback_Capacity_Failure_Localization"
BLOCKED_REL = BASE/"POSTV16_AV1_D_R7_R1_BLOCKED"

FOUNDATION_NAME = "V16A_Foundation_Case_0001.npz"
FOUNDATION_SHA = "4239e412ca6e2780f108c8eb1b0252e80a56be305bce48cc58e50d6140b86acc"
WEIGHTS_SHA = "46fa4e4dc9fa3dc9f00aaa0d0270010c7dd2a2048f43f247be691c027497c709"
NORM_SHA = "870c7360aff526c6ad0af31562270c139c61c69177a59290518f45b0d907efd3"

GRID=(15,50,50); NSL=1078; NN=201; NCV=200
DX=6.096; DY=6.096; DZ=1.2192
DAY=30.0
BACKGROUND=0.20
INJECTED=0.80
MAX_SG=0.60

class GateError(RuntimeError): pass

def sha256_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def git_text(root:Path,*args)->str:
    q=subprocess.run(["git","-C",str(root),*args],check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return q.stdout.strip()

def git_blob_sha(p:Path,root:Path)->str:
    return git_text(root,"hash-object",str(p))

def load_json(p:Path): return json.loads(p.read_text(encoding="utf-8"))

def json_bytes(x): return (json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+"\n").encode()

def csv_bytes(rows):
    if not rows:return b""
    f=[]
    for r in rows:
        for k in r:
            if k not in f:f.append(k)
    s=io.StringIO(newline="");w=csv.DictWriter(s,fieldnames=f,lineterminator="\n");w.writeheader();w.writerows(rows);return s.getvalue().encode()

def immutable_publish(out:Path,files:dict[str,bytes]):
    out.mkdir(parents=True,exist_ok=True)
    for n,d in files.items():
        p=out/n
        if p.exists() and p.read_bytes()!=d: raise GateError(f"existing_output_differs:{n}")
        if not p.exists():p.write_bytes(d)

def find_named_exact(roots,name,sha):
    hits=[]
    for root in roots:
        if not root.exists():continue
        for p in root.rglob(name):
            try:
                if p.is_file() and sha256_file(p)==sha:hits.append(p.resolve())
            except OSError:pass
    if not hits:raise GateError(f"exact_authority_not_found:{name}:{sha}")
    return sorted(set(hits),key=lambda p:(len(str(p)),str(p)))[0]

def load_module(p:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,p)
    if spec is None or spec.loader is None:raise GateError(f"cannot_load_module:{p}")
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def self_test():
    cpv=DX*DY*DZ*.2
    if not (9.0<cpv<9.2):raise RuntimeError(cpv)
    print("POSTV16-AV1-D-R7-R1 self-test: PASS")

def main(root:Path,drive:Path)->int:
    import tensorflow as tf
    gates={};stage="preflight"
    out=drive/OUT_REL;blocked=drive/BLOCKED_REL
    def gate(n,p,v=None):
        ok=bool(p);gates[n]={"passed":ok,"value":v}
        print(f"[{'PASS' if ok else 'FAIL'}] {n}"+(f" — {v}" if v is not None else ""))
        if not ok:raise GateError(n)

    print("="*184)
    print("POSTV16-AV1-D-R7-R1 — E37A DAY-30 MAPBACK CAPACITY FAILURE LOCALIZATION")
    print("="*184)
    print("DIAGNOSTIC ONLY. NO REPAIR. NO THRESHOLD/GATE CHANGE. NO TRAINING. NO GEOLOGY0031. NO ACCEPTANCE TRUTH.")
    print("REPRODUCE ONLY THE FIRST R7 SNAPSHOT AND STOP BEFORE THE E37A CELL-MASS INVERSION.\n")

    try:
        root=root.resolve();drive=drive.resolve()
        parent=git_text(root,"rev-parse","HEAD^");status=git_text(root,"status","--porcelain")
        gate("repository_parent_is_R7_commit",parent==PARENT_R7_COMMIT,parent)
        gate("repository_clean",status=="",repr(status))
        for fn,b in SOURCE_BLOBS.items():
            p=root/fn;a=git_blob_sha(p,root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact",a==b,a)

        stage="R7_blocked_evidence"
        br=drive/R7_BLOCKED_REL/R7_BLOCKED_REPORT
        gate("R7_blocked_report_present",br.is_file(),str(br))
        rep=load_json(br)
        gate("R7_failed_stage_exact",rep.get("failed_stage")=="E37A_grid_mapback",rep.get("failed_stage"))
        exc=str(rep.get("exception",""))
        gate("R7_failure_is_capillary_cell_mass_capacity", "capillary_cell_mass_capacity_exceeded" in exc, exc)

        stage="authority_binding"
        r6=drive/R6_REL
        weights=r6/R6_WEIGHTS;norm=r6/R6_NORM
        gate("R6_weights_exact",weights.is_file() and sha256_file(weights)==WEIGHTS_SHA)
        gate("R6_norm_exact",norm.is_file() and sha256_file(norm)==NORM_SHA)
        foundation=find_named_exact([root,drive],FOUNDATION_NAME,FOUNDATION_SHA)
        gate("foundation_exact",sha256_file(foundation)==FOUNDATION_SHA,str(foundation))
        with np.load(foundation,allow_pickle=False) as z:
            d={k:np.asarray(z[k]).copy() for k in ["Kx","Ky","Kz","porosity","pressure","Qx","Qy","Qz","Vx","Vy","Vz","streamline_xyz","pollock_tof","streamline_weight"]}

        stage="reproduce_day30_R7_transport"
        r7=load_module(root/R7,"r7r1_r7")
        b2=load_module(root/B2,"r7r1_b2")
        c2=load_module(root/C2,"r7r1_c2")
        c26=load_module(root/C26,"r7r1_c26")
        b1=load_module(root/B1,"r7r1_b1")
        r2=load_module(root/R2,"r7r1_r2")
        e37a=load_module(root/E37A,"r7r1_e37a")

        pressure=np.asarray(d["pressure"],float)
        cx,cy,cz=r7.face_to_cell(d["Vx"],d["Vy"],d["Vz"])
        _,_,_,source_mask,_=b2.bind_injector_sources(d["Qx"],d["Qy"],d["Qz"])
        adv,_=r7.solve_adv(cx,cy,cz,np.asarray(source_mask,bool),DX,DY,DZ)
        xyz=np.asarray(d["streamline_xyz"],float)
        ptau=np.asarray(d["pollock_tof"],float)
        te=ptau[:,-1]
        xi=np.linspace(0.,1.,NN)
        origin=np.array([0.,0.,0.],float)
        adv_s,_=c2.trilinear(adv,xyz,DX,DY,DZ,origin)
        kx_s,_=c2.trilinear(d["Kx"],xyz,DX,DY,DZ,origin)
        ky_s,_=c2.trilinear(d["Ky"],xyz,DX,DY,DZ,origin)
        kz_s,_=c2.trilinear(d["Kz"],xyz,DX,DY,DZ,origin)
        phi_s,_=c2.trilinear(d["porosity"],xyz,DX,DY,DZ,origin)
        p_s,_=c2.trilinear(pressure,xyz,DX,DY,DZ,origin)
        with np.load(norm,allow_pickle=False) as z:
            pmean=float(np.asarray(z["pressure_mean_psi"]).reshape(-1)[0]);pstd=float(np.asarray(z["pressure_std_psi"]).reshape(-1)[0])
        Kh=np.sqrt(np.maximum(kx_s,1e-30)*np.maximum(ky_s,1e-30))
        X7=np.stack([
            np.broadcast_to(xi[None,:],(NSL,NN)),ptau/te[:,None],adv_s/te[:,None],
            np.log10(np.maximum(Kh,1e-30)),np.log10(np.maximum(kz_s,1e-30)/np.maximum(Kh,1e-30)),
            phi_s,(p_s-pmean)/pstd
        ],axis=-1).astype(np.float32)
        th=np.full((NSL,NN,1),DAY/1000.,dtype=np.float32)
        eta=(DAY*86400./te).astype(np.float32)
        et=np.repeat(eta[:,None],NN,axis=1)[:,:,None]
        X9=np.concatenate([X7,th,et],axis=2).astype(np.float32)
        gate("day30_X9_shape_exact",X9.shape==(NSL,NN,9),X9.shape)
        try:tf.config.experimental.enable_op_determinism()
        except Exception:pass
        tf.keras.utils.set_random_seed(16021)
        model=c26.model();model.load_weights(weights)
        pred201=model.predict(X9,batch_size=64,verbose=0).astype(np.float64)
        gate("day30_prediction_shape_exact",pred201.shape==(NSL,NN),pred201.shape)
        gate("day30_prediction_bounds",float(np.min(pred201))>=.2-1e-12 and float(np.max(pred201))<=.8+1e-12,[float(np.min(pred201)),float(np.max(pred201))])

        with tempfile.TemporaryDirectory(prefix="R7R1_SG7D_") as tdtmp:
            tdtmp=Path(tdtmp);cp=tdtmp/SG7D;cp.write_bytes((root/SG7D).read_bytes())
            sg7d=load_module(cp,"r7r1_sg7d")
            op=sg7d.build_subsegment_operator(xyz,ptau/86400.,np.asarray(d["streamline_weight"],float)*86400.)
            injection_pc=float(r2.capillary_pressure_from_incremental_sg(float(r2.MAX_INCREMENTAL_CO2_SATURATION)))
            injector_pw_pa=np.array([pressure[k,int(r2.INJECTOR_J),int(r2.INJECTOR_I)]*float(r2.PSI_TO_PA) for k in r2.COMPLETION_K])
            p_ref=float(np.mean(injector_pw_pa)+injection_pc)
            geom=e37a.build_control_volume_geometry(r2,op,pressure,p_ref,NSL,NCV)
            coeff=np.asarray(geom["cv_pressure_mass_coeff"],float)
            ids=np.arange(NSL,dtype=np.int64)
            pred200,pred_mass,src_mass=b1.project_201_to_200_component_mass(r2,e37a,pred201,coeff,ids)
            den=max(abs(float(np.sum(pred_mass))),1.0)
            b1closure=abs(float(np.sum(pred_mass))-float(np.sum(src_mass)))/den
            gate("day30_B1_mass_closure",b1closure<=1e-12,b1closure)

            stage="E37A_contract_localization"
            parent=np.full(GRID,BACKGROUND,float)
            old_sat,old_mass,sample_closure=e37a.sample_grid_inventory_to_control_volumes(
                r2,parent,pressure,p_ref,geom,NSL,NCV
            )
            gate("background_grid_sample_closure",abs(sample_closure)<=1e-8,sample_closure)
            gate("background_grid_sample_sat_exact",float(np.max(np.abs(old_sat-BACKGROUND)))<=1e-12,float(np.max(np.abs(old_sat-BACKGROUND))))
            gate("background_grid_sample_mass_zero",float(np.max(np.abs(old_mass)))<=1e-10,float(np.max(np.abs(old_mass))))

            cv_id=np.asarray(geom["cv_id"],np.int64);flat=np.asarray(geom["flat_cell"],np.int64);pv=np.asarray(geom["pv_m3"],float);pseg=np.asarray(geom["pseg_psi"],float)
            oldf=old_sat.reshape(-1);newf=np.asarray(pred200,float).reshape(-1)
            oldsub=oldf[cv_id];newsub=newf[cv_id]
            oldsg=np.clip(oldsub-BACKGROUND,0.,MAX_SG);newsg=np.clip(newsub-BACKGROUND,0.,MAX_SG)
            rho_old=np.asarray(r2.gas_density_from_state(oldsub,pseg,p_ref),float)
            rho_new=np.asarray(r2.gas_density_from_state(newsub,pseg,p_ref),float)
            sub_delta=pv*(rho_new*newsg-rho_old*oldsg)
            deposited=np.bincount(flat,weights=sub_delta,minlength=np.prod(GRID)).reshape(GRID)
            parent_mass=np.zeros(GRID,float)
            trial=parent_mass+deposited
            cell_pv=DX*DY*DZ*.2
            smax=np.full(GRID,INJECTED,float)
            rho_max=np.asarray(r2.gas_density_from_state(smax,pressure,p_ref),float)
            capacity=cell_pv*rho_max*MAX_SG
            excess=trial-capacity
            tol=max(1e-8,1e-12*max(float(np.max(capacity)),1.0))
            mask=excess>tol
            count=int(mask.sum())
            max_idx=np.unravel_index(int(np.argmax(excess)),GRID)
            k,j,i=(int(x) for x in max_idx)
            max_ex=float(excess[max_idx])
            gate("capacity_failure_reproduced",count>0,{"overloaded_cells":count,"max_excess_kg":max_ex})
            gate("max_excess_matches_R7_report",abs(max_ex-9471.745379391961)<=max(1e-6,1e-10*9471.745379391961),max_ex)

            coverage=np.bincount(flat,weights=pv,minlength=np.prod(GRID)).reshape(GRID)
            subcount=np.bincount(flat,minlength=np.prod(GRID)).reshape(GRID)
            pair=flat.astype(np.int64)*NSL+np.asarray(op["streamline"],np.int64)
            unique=np.unique(pair)
            ucell=unique//NSL
            streamcount=np.bincount(ucell,minlength=np.prod(GRID)).reshape(GRID)
            covratio=coverage/cell_pv
            global_mass=float(np.sum(trial));global_cap=float(np.sum(capacity))
            gate("global_mass_within_total_grid_capacity",global_mass<=global_cap+1e-8,[global_mass,global_cap,global_mass/global_cap])

            local_rows=[]
            inds=np.argwhere(mask)
            order=sorted(inds.tolist(),key=lambda q:float(excess[tuple(q)]),reverse=True)
            for q in order[:50]:
                kk,jj,ii=map(int,q);idx=(kk,jj,ii)
                local_rows.append({
                    "k":kk,"j":jj,"i":ii,
                    "trial_mass_kg":float(trial[idx]),
                    "cell_capacity_kg":float(capacity[idx]),
                    "excess_kg":float(excess[idx]),
                    "capacity_ratio":float(trial[idx]/capacity[idx]),
                    "coverage_weight_m3":float(coverage[idx]),
                    "physical_cell_pore_volume_m3":float(cell_pv),
                    "coverage_to_cell_PV_ratio":float(covratio[idx]),
                    "subsegment_count":int(subcount[idx]),
                    "unique_streamline_count":int(streamcount[idx]),
                })

            worst_support=(flat==((k*50+j)*50+i))
            worst_streams=np.unique(np.asarray(op["streamline"],np.int64)[worst_support])
            worst_cv_ids=np.unique(cv_id[worst_support])
            diagnosis={
                "milestone":MILESTONE,
                "status":STATUS_PASS,
                "R7_failure":{
                    "stage":"E37A_grid_mapback",
                    "exception":exc,
                    "reproduced_max_excess_kg":max_ex,
                    "overloaded_cell_count":count,
                    "worst_cell_kji":[k,j,i],
                },
                "old_state_contract":{
                    "E37A_requires_parent_grid_sampling":True,
                    "R7_original_omitted_parent_grid_sampling":True,
                    "day30_parent_is_uniform_background":True,
                    "sampled_old_CV_state_equals_R7_background_old_state":True,
                    "conclusion":"Adding parent-grid sampling alone cannot remove the first day-30 overload because the exact sampled t=0 CV state is the same background state used by R7.",
                },
                "local_capacity":{
                    "physical_cell_pore_volume_m3":cell_pv,
                    "global_trial_mass_kg":global_mass,
                    "global_grid_capacity_kg":global_cap,
                    "global_mass_capacity_fraction":global_mass/global_cap,
                    "worst_trial_mass_kg":float(trial[max_idx]),
                    "worst_cell_capacity_kg":float(capacity[max_idx]),
                    "worst_excess_kg":max_ex,
                    "worst_capacity_ratio":float(trial[max_idx]/capacity[max_idx]),
                    "worst_coverage_weight_m3":float(coverage[max_idx]),
                    "worst_coverage_to_cell_PV_ratio":float(covratio[max_idx]),
                    "worst_subsegment_count":int(subcount[max_idx]),
                    "worst_unique_streamline_count":int(streamcount[max_idx]),
                    "worst_supported_streamline_count_direct":int(len(worst_streams)),
                    "worst_supported_cv_count":int(len(worst_cv_ids)),
                },
                "scientific_interpretation":{
                    "transport_checkpoint_failure":False,
                    "B1_representation_failure":False,
                    "global_mass_capacity_failure":False,
                    "local_grid_occupancy_capacity_failure":True,
                    "cause_class":"ABSOLUTE_STREAMLINE_INVENTORY_TO_CARTESIAN_OVERLAP_CAPACITY_INCOMPATIBILITY",
                    "causal_mechanism_proven":(
                        "The exact E37A deposition implied by the day-30 accepted PI-RNN/B1 CV inventory places more component mass into at least one Cartesian cell than its bounded S=0.80 capillary-EOS capacity. "
                        "The SG7D operator assigns streamline-tube pore-volume support q*Δtau and multiple streamlines/subsegments can support the same Cartesian cell. "
                        "R7 attempted an absolute background-to-day30 deposit, so overlapping streamline inventory accumulated locally beyond cell capacity even though total grid capacity was sufficient."
                    ),
                },
                "repair_constraints":{
                    "do_not_clip_overloaded_cells":True,
                    "do_not_relax_S_max":True,
                    "do_not_global_rescale_saturation":True,
                    "do_not_change_accepted_checkpoint":True,
                    "do_not_change_B1_half_overlap":True,
                    "do_not_reuse_geology0031":True,
                    "next_required_step":"Prospectively design and freeze a conservative bounded overlap/occupancy reconciliation operator before any R7 repair execution.",
                },
            }

        files={
            "PAD_Stream_POSTV16_AV1_D_R7_R1_Summary.json":json_bytes({
                "milestone":MILESTONE,"status":STATUS_PASS,
                "R7_failure_reproduced":True,
                "overloaded_cell_count":count,
                "worst_cell_kji":[k,j,i],
                "worst_excess_kg":max_ex,
                "global_mass_within_total_grid_capacity":True,
                "accepted_checkpoint_changed":False,
                "repair_selected":False,
                "next":"POSTV16-AV1-D-R7-R2 — prospective conservative bounded overlap/occupancy reconciliation design and freeze"
            }),
            "POSTV16_AV1_D_R7_R1_Failure_Localization_Diagnosis.json":json_bytes(diagnosis),
            "POSTV16_AV1_D_R7_R1_Overloaded_Cell_Audit.csv":csv_bytes(local_rows),
            "POSTV16_AV1_D_R7_R1_Final_Gate_Matrix.csv":csv_bytes([{"gate":k,**v} for k,v in gates.items()]),
        }
        immutable_publish(out,files)
        manifest=[]
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name!="POSTV16_AV1_D_R7_R1_Artifact_Manifest.csv":
                manifest.append({"file":p.name,"sha256":sha256_file(p),"bytes":p.stat().st_size})
        immutable_publish(out,{"POSTV16_AV1_D_R7_R1_Artifact_Manifest.csv":csv_bytes(manifest)})

        print("\n"+"="*184)
        print("POSTV16-AV1-D-R7-R1: PASS")
        print("="*184)
        print(f"{'Status':102}: {STATUS_PASS}")
        print(f"{'R7 failure reproduced':102}: True")
        print(f"{'Overloaded Cartesian cells':102}: {count}")
        print(f"{'Worst cell k/j/i':102}: {k} / {j} / {i}")
        print(f"{'Worst cell excess mass [kg]':102}: {max_ex:.12e}")
        print(f"{'Worst cell capacity ratio':102}: {float(trial[max_idx]/capacity[max_idx]):.12e}")
        print(f"{'Worst coverage / physical cell PV ratio':102}: {float(covratio[max_idx]):.12e}")
        print(f"{'Worst unique streamline support count':102}: {int(streamcount[max_idx])}")
        print(f"{'Global mass / total grid capacity':102}: {global_mass/global_cap:.12e}")
        print(f"{'Accepted checkpoint / B1 changed':102}: False / False")
        print(f"{'Repair selected in R7-R1':102}: False")
        print(f"{'NEXT':102}: POSTV16-AV1-D-R7-R2 — freeze conservative bounded overlap/occupancy reconciliation")
        print("="*184)
        return 0

    except Exception as e:
        blocked.mkdir(parents=True,exist_ok=True)
        rep={"milestone":MILESTONE,"status":STATUS_BLOCKED,"failed_stage":stage,"exception":repr(e),"gates":gates,
             "training_performed":False,"accepted_checkpoint_changed":False,"repair_selected":False,
             "next_action":"Audit only R7-R1 localization. Do not alter saturation bounds, B1, E37A gates, or the accepted checkpoint."}
        data=json_bytes(rep);p=blocked/"POSTV16_AV1_D_R7_R1_Blocked_Report.json"
        if p.exists() and p.read_bytes()!=data:
            p=blocked/f"POSTV16_AV1_D_R7_R1_Blocked_Report_{hashlib.sha256(data).hexdigest()[:12]}.json"
        if not p.exists():p.write_bytes(data)
        print("\n"+"="*184);print("POSTV16-AV1-D-R7-R1: BLOCKED");print("="*184)
        print("Failed stage:",stage);print("Exception:",repr(e));print("Report:",p)
        return 2

def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--project-root",type=Path,default=Path("."))
    p.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    p.add_argument("--self-test",action="store_true")
    return p.parse_args()

if __name__=="__main__":
    a=parse_args()
    if a.self_test:
        self_test();raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))
