#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors

M = "POSTV16-P-CAD-A0"
NAME = "Read-Only Exact Pressure Evolution + Flow-Epoch Hold-Duration Screening"
PASS = "POSTV16PCADA0_EXACT_PRESSURE_EVOLUTION_AND_FLOWEPOCH_HOLD_SCREENING_PASS_NO_PHYSICS_MUTATION"
BLOCK = "POSTV16PCADA0_TECHNICAL_OR_AUTHORITY_BLOCK_NO_PHYSICS_MUTATION"

BRANCH = "postv16-av4-pivot"
PARENT = "e7f4122ebde59676f07d1ad4bfac197a29bf9954"  # VIS-A3
RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
BASE_AV5 = Path("post_v16") / RID / "POSTV16_AV5_Learned_Acceleration"

VIS_A1_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_VIS_A1_Certified_Day365_to_Day405_ReadOnly_3D_Visualization.py"
VIS_A1_BLOB = "40d79b83b8d9d0d1e7d9dd42c3a17b32f49e5173"
VIS_A3_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_VIS_A3_Industry_Style_Reservoir_PostProcessing.py"
VIS_A3_BLOB = "270def5961bf5a434564b77fe365c6c1c50c2e46"
AV5_A4_RUNNER = "PAD_Stream_POSTV16_AV5_A4_Exact_Pressure_Teacher_Dataset_Generation_TRAIN_Only_Normalization_and_Locked_OOD_Predictor_Materialization.py"
AV5_A4_BLOB = "b4a12d9949953ec8aa3d99e1ea1d8bac90d4eaf7"

VIS_A3_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P3_R1_VIS_A3_Industry_Style_Reservoir_PostProcessing"
VIS_A3_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_VIS_A3_Summary.json"
VIS_A3_MANIFEST = "POSTV16_AV4_PIVOT_P3_R1_VIS_A3_Artifact_Manifest.csv"
VIS_A3_STATUS = "AV4PIVOTP3R1VISA3_INDUSTRY_STYLE_RESERVOIR_POSTPROCESSING_PASS_NO_PHYSICS_MUTATION"

A4_REL = BASE_AV5 / "POSTV16_AV5_A4_Exact_Pressure_Teacher_Dataset_TRAIN_Only_Normalization_and_Locked_OOD_Predictor_Materialization"
A4_SUMMARY = "PAD_Stream_POSTV16_AV5_A4_Summary.json"
A4_DATASET = "POSTV16_AV5_A4_TrainValidation_6Channel_PressureTeacher_Dataset.npz"
A4_MANIFEST = "POSTV16_AV5_A4_Artifact_Manifest.csv"
A4_STATUS = "POSTV16AV5A4_EXACT_PRESSURE_TEACHER_DATASET_TRAIN_ONLY_NORMALIZATION_AND_LEAKAGE_SAFE_LOCKED_OOD_PREDICTOR_MATERIALIZATION_PASS_NO_TRAINING"
A4_AV4_STATE_SHA = "07856a508db8ae6ba449e9e248bf8cdbc406eb0b4504471099b4b82f6048e0a6"
REALIZATION_IDS = {0: "AV3CR0001", 1: "AV3CR0002", 2: "AV3CR0003"}
EARLY_DAYS = [30, 60, 100, 150, 250, 365]
LATE_DAYS = [365, 370, 375, 380, 385, 390, 395, 400, 405]
HOLD_DAYS = [5, 10, 15, 20, 25, 30, 35, 40]
GRID = (15, 50, 50)
MID_K = 7
DX_FT = 20.0
DY_FT = 20.0
FT_TO_M = 0.3048
DAY_TO_S = 86400.0

# Strict equality-like criteria for claiming the AV5 early pressure sequence can be
# formally spliced onto the AV4/A2-E Day365 pressure trajectory. These are not cadence tolerances.
SPLICE_REL_L2_MAX = 1.0e-12
SPLICE_MAXABS_PSI_MAX = 1.0e-8

OUT_TOKEN = "POSTV16_P_CAD_A0"
OUT_REL = BASE_AV4 / (OUT_TOKEN + "_Exact_Pressure_Evolution_and_FlowEpoch_Hold_Screening")
STAGE_REL = BASE_AV4 / (OUT_TOKEN + "_STAGING")
BLOCK_REL = BASE_AV4 / (OUT_TOKEN + "_BLOCKED")
SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
LINEAGE = f"{OUT_TOKEN}_Day365_Lineage_Audit.csv"
EARLY_METRICS = f"{OUT_TOKEN}_Early_Pressure_Evolution.csv"
EARLY_PRIORITY = f"{OUT_TOKEN}_Early_Probe_Priority.csv"
FIVE_DAY = f"{OUT_TOKEN}_Late_FiveDay_Increment_Metrics.csv"
HOLD_PAIRWISE = f"{OUT_TOKEN}_Hold_Duration_Pairwise.csv"
HOLD_SUMMARY = f"{OUT_TOKEN}_Hold_Duration_Summary.csv"
GATES = f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"

class GateError(RuntimeError):
    pass

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()

def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def js(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))

def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text('', encoding='utf-8'); return
    fields: list[str] = []
    for row in rows:
        for k in row:
            if k not in fields: fields.append(k)
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader(); w.writerows(rows)

def verify_manifest(directory: Path, filename: str) -> dict[str, str]:
    p = directory / filename
    if not p.is_file(): raise GateError(f"manifest_missing:{p}")
    out: dict[str, str] = {}
    for row in csv_rows(p):
        q = directory / row['file']
        if not q.is_file(): raise GateError(f"manifest_artifact_missing:{q.name}")
        actual = sha256(q)
        if actual != row['sha256']: raise GateError(f"manifest_sha:{q.name}")
        if q.stat().st_size != int(row['bytes']): raise GateError(f"manifest_bytes:{q.name}")
        out[q.name] = actual
    if not out: raise GateError(f"manifest_empty:{p}")
    return out

def load_module_exact(root: Path, filename: str, blob: str, module_name: str):
    p = root / filename
    if not p.is_file(): raise GateError(f"source_missing:{filename}")
    actual = gt(root, 'hash-object', str(p))
    if actual != blob: raise GateError(f"source_blob:{filename}:{actual}:{blob}")
    spec = importlib.util.spec_from_file_location(module_name, p)
    if spec is None or spec.loader is None: raise GateError(f"cannot_import:{filename}")
    m = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = m
    spec.loader.exec_module(m)
    return m

def rel_l2(a: np.ndarray, b: np.ndarray) -> float:
    aa=np.asarray(a,dtype=np.float64); bb=np.asarray(b,dtype=np.float64)
    return float(np.linalg.norm((aa-bb).ravel()) / max(float(np.linalg.norm(bb.ravel())),1e-30))

def diff_metrics(current: np.ndarray, anchor: np.ndarray) -> dict[str, float]:
    d=np.asarray(current,dtype=np.float64)-np.asarray(anchor,dtype=np.float64)
    ad=np.abs(d)
    return {
        'relative_L2': rel_l2(current, anchor),
        'rmse': float(np.sqrt(np.mean(d*d))),
        'mae': float(np.mean(ad)),
        'p95_abs': float(np.percentile(ad,95.0)),
        'max_abs': float(np.max(ad)),
        'mean_delta': float(np.mean(d)),
        'min_delta': float(np.min(d)),
        'max_delta': float(np.max(d)),
    }

def concat_flux(rec: dict[str, Any]) -> np.ndarray:
    return np.concatenate([rec['Qx'].ravel(),rec['Qy'].ravel(),rec['Qz'].ravel()])

def augment_flow_arrays(rec: dict[str, Any]) -> None:
    with np.load(Path(rec['diag_file']), allow_pickle=False) as z:
        for key in ['Qx','Qy','Qz','streamline_weight_m3_s','producer_labels']:
            if key not in z.files: raise GateError(f"Day{rec['day']}_diagnostic_missing:{key}")
        rec['Qx']=np.asarray(z['Qx'],dtype=np.float64)
        rec['Qy']=np.asarray(z['Qy'],dtype=np.float64)
        rec['Qz']=np.asarray(z['Qz'],dtype=np.float64)
        rec['streamline_weight_m3_s']=np.asarray(z['streamline_weight_m3_s'],dtype=np.float64)
        rec['producer_labels']=np.asarray(z['producer_labels']).astype('U32')

def pair_metrics(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    pm=diff_metrics(b['pressure'],a['pressure'])
    fa=concat_flux(a); fb=concat_flux(b)
    tau_a=np.asarray(a['tau_end_s'],dtype=np.float64); tau_b=np.asarray(b['tau_end_s'],dtype=np.float64)
    wa=np.asarray(a['streamline_weight_m3_s'],dtype=np.float64); wb=np.asarray(b['streamline_weight_m3_s'],dtype=np.float64)
    xa=np.asarray(a['xyz_m'],dtype=np.float64); xb=np.asarray(b['xyz_m'],dtype=np.float64)
    if xa.shape != xb.shape or tau_a.shape != tau_b.shape or wa.shape != wb.shape:
        raise GateError(f"streamline_shape_change:{a['day']}:{b['day']}")
    disp_ft=np.linalg.norm(xb-xa,axis=2)/FT_TO_M
    labels_a=np.asarray(a['producer_labels']).astype('U32'); labels_b=np.asarray(b['producer_labels']).astype('U32')
    if labels_a.shape != labels_b.shape: raise GateError(f"producer_label_shape_change:{a['day']}:{b['day']}")
    return {
        'start_day':int(a['day']), 'end_day':int(b['day']), 'hold_days':int(b['day']-a['day']),
        'pressure_relative_L2':pm['relative_L2'], 'pressure_rmse_psi':pm['rmse'],
        'pressure_mae_psi':pm['mae'], 'pressure_p95_abs_psi':pm['p95_abs'],
        'pressure_max_abs_psi':pm['max_abs'], 'pressure_mean_delta_psi':pm['mean_delta'],
        'pressure_min_delta_psi':pm['min_delta'], 'pressure_max_delta_psi':pm['max_delta'],
        'flux_relative_L2':rel_l2(fb,fa),
        'Qx_relative_L2':rel_l2(b['Qx'],a['Qx']), 'Qy_relative_L2':rel_l2(b['Qy'],a['Qy']), 'Qz_relative_L2':rel_l2(b['Qz'],a['Qz']),
        'tau_end_relative_L2':rel_l2(tau_b,tau_a),
        'tau_end_rmse_days':float(np.sqrt(np.mean(((tau_b-tau_a)/DAY_TO_S)**2))),
        'streamline_weight_relative_L2':rel_l2(wb,wa),
        'producer_connectivity_mismatch_fraction':float(np.mean(labels_a != labels_b)),
        'path_RMS_displacement_ft':float(np.sqrt(np.mean(disp_ft*disp_ft))),
        'path_p95_displacement_ft':float(np.percentile(disp_ft,95.0)),
        'path_max_displacement_ft':float(np.max(disp_ft)),
    }

def add_wells(ax) -> None:
    ax.scatter([(24+.5)*DX_FT],[(24+.5)*DY_FT],marker='*',s=90,c='black',label='Injector',zorder=5)
    first=True
    for i,j in [(4,4),(45,4),(4,45),(45,45)]:
        ax.scatter([(i+.5)*DX_FT],[(j+.5)*DY_FT],marker='s',s=35,facecolors='white',edgecolors='black',label='Producers' if first else None,zorder=5)
        first=False

def make_early_maps(pressures: dict[int,np.ndarray], realization_label: str, splice: bool, out: Path) -> Path:
    p30=pressures[30]
    dps={d:pressures[d]-p30 for d in EARLY_DAYS}
    lim=max(max(float(np.max(np.abs(v))) for v in dps.values()),1e-9)
    fig,axes=plt.subplots(2,3,figsize=(16,10),constrained_layout=True)
    for ax,d in zip(axes.ravel(),EARLY_DAYS):
        arr=dps[d][MID_K]
        im=ax.imshow(arr,origin='lower',extent=[0,1000,0,1000],cmap='coolwarm',vmin=-lim,vmax=lim,interpolation='nearest',aspect='equal')
        add_wells(ax); ax.set_title(f'Day {d}: P(Day{d}) - P(Day30)')
        ax.set_xlabel('X (ft)'); ax.set_ylabel('Y (ft)')
    cb=fig.colorbar(im,ax=axes.ravel().tolist(),shrink=.85); cb.set_label('ΔP vs Day30 (psi)')
    mode='formal splice candidate' if splice else 'screening only — no formal Day365 splice'
    fig.suptitle(f'P-CAD-A0 early exact-pressure evolution — {realization_label}\nphysical layer 8 (z = 30 ft); {mode}',fontsize=14)
    p=out/f'{OUT_TOKEN}_Early_Day30_Relative_Pressure_Maps.png'; fig.savefig(p,dpi=180,bbox_inches='tight'); plt.close(fig); return p

def plot_early_metric(rows:list[dict[str,Any]], rid:str, out:Path)->Path:
    rr=[r for r in rows if r['realization_id']==rid and r['baseline']=='Day30']
    rr=sorted(rr,key=lambda r:r['end_day'])
    fig,ax=plt.subplots(figsize=(9,5.5)); ax.plot([r['end_day'] for r in rr],[r['relative_L2'] for r in rr],marker='o')
    ax.set_xlabel('Day'); ax.set_ylabel('Pressure relative L2 vs Day30'); ax.set_title(f'Early exact-pressure differentiation — {rid}')
    ax.grid(True,alpha=.25); fig.tight_layout(); p=out/f'{OUT_TOKEN}_Early_Pressure_RelL2_vs_Day30.png'; fig.savefig(p,dpi=180,bbox_inches='tight'); plt.close(fig); return p

def plot_hold(rows:list[dict[str,Any]], metric:str, ylabel:str, title:str, filename:str, out:Path)->Path:
    hs=sorted(rows,key=lambda r:int(r['hold_days']))
    x=[int(r['hold_days']) for r in hs]; mean=[float(r[f'{metric}_mean']) for r in hs]; mx=[float(r[f'{metric}_max']) for r in hs]
    fig,ax=plt.subplots(figsize=(9,5.5)); ax.plot(x,mean,marker='o',label='Mean across available windows'); ax.plot(x,mx,marker='o',label='Maximum across available windows')
    ax.set_xlabel('Flow-epoch hold duration (days)'); ax.set_ylabel(ylabel); ax.set_title(title); ax.grid(True,alpha=.25); ax.legend(); fig.tight_layout()
    p=out/filename; fig.savefig(p,dpi=180,bbox_inches='tight'); plt.close(fig); return p

def selftest() -> None:
    assert EARLY_DAYS == [30,60,100,150,250,365]
    assert HOLD_DAYS == [5,10,15,20,25,30,35,40]
    a=np.asarray([1.,2.,3.]); b=np.asarray([1.,2.,4.]); m=diff_metrics(b,a)
    assert m['max_abs']==1.0 and m['relative_L2']>0
    assert SPLICE_REL_L2_MAX < 1e-9
    print('POSTV16 P-CAD-A0 structural self-test: PASS')

def main(project_root:Path, drive_root:Path)->int:
    root=project_root.resolve(); drive=drive_root.resolve(); out=drive/OUT_REL; staging=drive/STAGE_REL; blocked=drive/BLOCK_REL
    stage='preflight'; gates=[]
    def gate(name:str,cond:Any,detail:Any=None):
        nonlocal gates
        ok=bool(cond); gates.append({'stage':stage,'gate':name,'pass':ok,'detail':'' if detail is None else repr(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ('' if detail is None else f' -- {detail}'),flush=True)
        if not ok: raise GateError(name)
    try:
        print('='*180); print('POSTV16-P-CAD-A0 — EXACT PRESSURE EVOLUTION + FLOW-EPOCH HOLD-DURATION SCREENING')
        print('READ-ONLY ANALYSIS. NO PRESSURE SOLVE. NO DARCY RECOMPUTATION. NO POLLOCK RETRACING. NO TRANSPORT ADVANCE.')
        print('NO PRODUCTION PRESSURE-REFRESH CADENCE IS SELECTED IN A0.'); print('='*180)
        stage='repository_authority'
        gate('branch_exact',gt(root,'branch','--show-current')==BRANCH,gt(root,'branch','--show-current'))
        gate('parent_is_VIS_A3_commit',gt(root,'rev-parse','HEAD^')==PARENT,gt(root,'rev-parse','HEAD^'))
        gate('repository_clean',gt(root,'status','--porcelain')=='')
        a1=load_module_exact(root,VIS_A1_RUNNER,VIS_A1_BLOB,'pcad_vis_a1')
        _v3=load_module_exact(root,VIS_A3_RUNNER,VIS_A3_BLOB,'pcad_vis_a3')
        _a4runner=load_module_exact(root,AV5_A4_RUNNER,AV5_A4_BLOB,'pcad_av5_a4')

        stage='VIS_A3_closure_authority'
        v3dir=drive/VIS_A3_REL; gate('VIS_A3_output_exists',v3dir.is_dir(),str(v3dir)); verify_manifest(v3dir,VIS_A3_MANIFEST); v3s=js(v3dir/VIS_A3_SUMMARY)
        gate('VIS_A3_status_exact',v3s.get('status')==VIS_A3_STATUS,v3s.get('status'))
        gate('VIS_A3_no_physics_mutation',v3s.get('authoritative_physics_state_mutated') is False)
        gate('VIS_A3_no_transport_advance',v3s.get('Day405_to_Day410_transport_executed') is False)
        gate('VIS_A3_Day410_authority_preserved',v3s.get('Day405_to_Day410_transport_remains_authorized') is True)
        gate('VIS_A3_P4_locked',v3s.get('P4_authorized') is False)

        stage='AV5_A4_exact_teacher_authority'
        a4dir=drive/A4_REL; gate('AV5_A4_output_exists',a4dir.is_dir(),str(a4dir)); a4m=verify_manifest(a4dir,A4_MANIFEST); a4s=js(a4dir/A4_SUMMARY)
        gate('AV5_A4_status_exact',a4s.get('status')==A4_STATUS,a4s.get('status'))
        gate('AV5_A4_AV4_state_binding_exact',a4s.get('AV4_authoritative_state_sha256')==A4_AV4_STATE_SHA,a4s.get('AV4_authoritative_state_sha256'))
        ds=a4dir/A4_DATASET; gate('AV5_A4_dataset_manifested',A4_DATASET in a4m and ds.is_file(),str(ds))
        with np.load(ds,allow_pickle=False) as z:
            required={'p_star_psi','target_day','realization_index','partition_code','AV4_authoritative_state_sha256'}
            gate('AV5_A4_dataset_arrays_present',required.issubset(set(z.files)),sorted(z.files))
            Pstar=np.asarray(z['p_star_psi'],dtype=np.float64); target=np.asarray(z['target_day'],dtype=np.float64); ridx=np.asarray(z['realization_index'],dtype=np.int64)
            av4sha=str(np.asarray(z['AV4_authoritative_state_sha256']).reshape(()))
        gate('AV5_A4_dataset_shape_exact',Pstar.shape==(27,)+GRID,Pstar.shape); gate('AV5_A4_dataset_AV4_binding_exact',av4sha==A4_AV4_STATE_SHA,av4sha)

        stage='AV4_Day365_to_Day405_authority'
        state405_sha,diag405_sha,r10sum=a1.bind_day405(drive); a1.OBS[405]['state_sha']=state405_sha; a1.OBS[405]['diag_sha']=diag405_sha
        late=[]; rec365=a1.load_day365(drive); a1.validate_arrays(rec365); augment_flow_arrays(rec365); late.append(rec365)
        for d in sorted(a1.OBS):
            r=a1.load_observation(drive,d,a1.OBS[d]); a1.validate_arrays(r); augment_flow_arrays(r); late.append(r)
        gate('late_days_exact',[int(r['day']) for r in late]==LATE_DAYS,[r['day'] for r in late])
        p365=np.asarray(late[0]['pressure'],dtype=np.float64)

        stage='Day365_lineage_audit'
        lineage=[]; candidates=[]
        for ri,rid in REALIZATION_IDS.items():
            idx=np.where((ridx==ri)&np.isclose(target,365.0,rtol=0,atol=1e-12))[0]
            gate(f'{rid}_single_Day365_teacher',idx.size==1,idx.tolist())
            p=np.asarray(Pstar[int(idx[0])],dtype=np.float64); m=diff_metrics(p,p365)
            exact=bool(m['relative_L2']<=SPLICE_REL_L2_MAX and m['max_abs']<=SPLICE_MAXABS_PSI_MAX)
            row={'realization_index':ri,'realization_id':rid,'partition':'TRAIN' if ri<2 else 'VALIDATION','Day365_relative_L2_vs_A2E':m['relative_L2'],'Day365_RMSE_psi_vs_A2E':m['rmse'],'Day365_max_abs_psi_vs_A2E':m['max_abs'],'strict_splice_match':exact}
            lineage.append(row); candidates.append((m['relative_L2'],m['max_abs'],ri,rid,exact))
        candidates.sort(); best=candidates[0]; best_ri=best[2]; best_rid=best[3]; exact_matches=[x for x in candidates if x[4]]
        splice=bool(len(exact_matches)==1 and exact_matches[0][2]==best_ri)
        print('Best Day365 early-teacher realization:',best_rid,'relL2=',best[0],'maxabs psi=',best[1],'strict splice=',splice,flush=True)

        stage='early_pressure_screening'
        early_rows=[]; early_pressures_by_rid={}
        for ri,rid in REALIZATION_IDS.items():
            dct={}
            for d in EARLY_DAYS:
                idx=np.where((ridx==ri)&np.isclose(target,float(d),rtol=0,atol=1e-12))[0]; gate(f'{rid}_Day{d}_single_teacher',idx.size==1,idx.tolist()); dct[d]=np.asarray(Pstar[int(idx[0])],dtype=np.float64)
            early_pressures_by_rid[rid]=dct
            p30=dct[30]
            prev_day=30; prev=p30
            for d in EARLY_DAYS:
                m30=diff_metrics(dct[d],p30)
                early_rows.append({'realization_index':ri,'realization_id':rid,'end_day':d,'baseline':'Day30','interval_days':d-30,**m30})
                if d!=30:
                    mp=diff_metrics(dct[d],prev)
                    early_rows.append({'realization_index':ri,'realization_id':rid,'start_day':prev_day,'end_day':d,'baseline':'PreviousCanonical','interval_days':d-prev_day,**mp})
                    prev_day=d; prev=dct[d]
        best_pressures=early_pressures_by_rid[best_rid]
        priority=[]
        for a,b in zip(EARLY_DAYS[:-1],EARLY_DAYS[1:]):
            m=diff_metrics(best_pressures[b],best_pressures[a]); dt=b-a
            priority.append({'realization_id':best_rid,'start_day':a,'end_day':b,'coarse_interval_days':dt,'pressure_relative_L2':m['relative_L2'],'relative_L2_rate_per_day':m['relative_L2']/dt,'RMSE_psi':m['rmse'],'RMSE_psi_per_day':m['rmse']/dt,'max_abs_psi':m['max_abs'],'max_abs_psi_per_day':m['max_abs']/dt})
        priority.sort(key=lambda r:r['relative_L2_rate_per_day'],reverse=True)
        for n,r in enumerate(priority,1): r['priority_rank_by_relative_L2_rate']=n

        stage='late_hold_duration_screening'
        pair_rows=[]
        byday={int(r['day']):r for r in late}
        for h in HOLD_DAYS:
            for a in LATE_DAYS:
                b=a+h
                if b in byday: pair_rows.append(pair_metrics(byday[a],byday[b]))
        gate('all_hold_durations_have_pairs',all(any(int(r['hold_days'])==h for r in pair_rows) for h in HOLD_DAYS),[(h,sum(int(r['hold_days'])==h for r in pair_rows)) for h in HOLD_DAYS])
        five=[r for r in pair_rows if int(r['hold_days'])==5]
        hold_summary=[]
        metric_names=['pressure_relative_L2','pressure_rmse_psi','pressure_max_abs_psi','flux_relative_L2','tau_end_relative_L2','streamline_weight_relative_L2','producer_connectivity_mismatch_fraction','path_RMS_displacement_ft','path_p95_displacement_ft']
        for h in HOLD_DAYS:
            rr=[r for r in pair_rows if int(r['hold_days'])==h]; row={'hold_days':h,'pair_count':len(rr)}
            for name in metric_names:
                vals=np.asarray([float(r[name]) for r in rr],dtype=np.float64); row[f'{name}_mean']=float(np.mean(vals)); row[f'{name}_max']=float(np.max(vals))
            hold_summary.append(row)

        stage='publication'
        gate('output_does_not_preexist',not out.exists(),str(out));
        if staging.exists(): shutil.rmtree(staging)
        staging.mkdir(parents=True,exist_ok=False)
        write_csv(staging/LINEAGE,lineage); write_csv(staging/EARLY_METRICS,early_rows); write_csv(staging/EARLY_PRIORITY,priority); write_csv(staging/FIVE_DAY,five); write_csv(staging/HOLD_PAIRWISE,pair_rows); write_csv(staging/HOLD_SUMMARY,hold_summary)
        make_early_maps(best_pressures,best_rid,splice,staging); plot_early_metric(early_rows,best_rid,staging)
        plot_hold(hold_summary,'pressure_relative_L2','Pressure relative L2','Pressure staleness vs held flow-epoch duration',f'{OUT_TOKEN}_Pressure_Hold_Error_vs_Duration.png',staging)
        plot_hold(hold_summary,'flux_relative_L2','Darcy-flux relative L2','Darcy-flow staleness vs held flow-epoch duration',f'{OUT_TOKEN}_Flux_Hold_Error_vs_Duration.png',staging)
        plot_hold(hold_summary,'tau_end_relative_L2','Terminal TOF relative L2','TOF staleness vs held flow-epoch duration',f'{OUT_TOKEN}_TOF_Hold_Error_vs_Duration.png',staging)

        top3=[{'start_day':r['start_day'],'end_day':r['end_day'],'rank':r['priority_rank_by_relative_L2_rate']} for r in priority[:3]]
        classification=(
          'P_CAD_A0_EXACT_DAY365_PRESSURE_SPLICE_CERTIFIED_LONG_HORIZON_AND_5DAY_HOLD_SCREENING_COMPLETE_TARGETED_EARLY_PROBE_DESIGN_AUTHORIZED'
          if splice else
          'P_CAD_A0_AV5_EARLY_PRESSURE_SCREENING_NOT_FORMALLY_CONTIGUOUS_WITH_AV4_DAY365_TRAJECTORY_LATE_HOLD_SCREENING_COMPLETE_TARGETED_EARLY_PROBE_DESIGN_REQUIRED'
        )
        summary={'milestone':M,'name':NAME,'status':PASS,'classification':classification,'repository_parent_VIS_A3_commit':PARENT,'VIS_A3_status_bound':VIS_A3_STATUS,'AV5_A4_status_bound':A4_STATUS,'AV5_A4_authoritative_state_sha256':A4_AV4_STATE_SHA,'Day365_A2E_pressure_authority_sha256':a1.DAY365_FLOW_SHA,'best_Day365_teacher_realization':best_rid,'best_Day365_teacher_relative_L2_vs_A2E':best[0],'best_Day365_teacher_max_abs_psi_vs_A2E':best[1],'formal_Day30_to_Day405_pressure_splice_authorized':splice,'early_screening_days':EARLY_DAYS,'late_exact_diagnostic_days':LATE_DAYS,'hold_durations_screened_days':HOLD_DAYS,'targeted_early_probe_priority_top3_coarse_windows':top3,'production_pressure_refresh_cadence_selected':False,'cadence_error_tolerance_defined':False,'new_pressure_solves_executed':False,'Darcy_recomputation_executed':False,'Pollock_retracing_executed':False,'TOF_recomputation_executed':False,'transport_execution_executed':False,'authoritative_physics_state_mutated':False,'authoritative_physical_time_advanced':False,'Day405_to_Day410_transport_executed':False,'Day405_to_Day410_transport_remains_authorized':True,'P3_R1_full_rerun_authorized':False,'P4_authorized':False,'recommended_next_action':'Review A0 long-horizon pressure differentiation and error-vs-hold-duration curves. Then freeze admissible pressure/flow/TOF error criteria and design only the highest-information early five-day probes; do not brute-force Day30-to-Day365 at five-day cadence.'}
        decision={'milestone':M,'status':PASS,'classification':classification,'formal_Day30_to_Day405_pressure_splice_authorized':splice,'production_pressure_refresh_cadence_selected':False,'cadence_error_tolerance_defined':False,'P_CAD_A1_targeted_early_probe_design_authorized':True,'P_CAD_A1_expensive_probe_execution_authorized':False,'brute_force_Day30_to_Day365_five_day_sweep_authorized':False,'Day405_to_Day410_transport_remains_authorized_from_R7R10':True,'Day405_to_Day410_transport_executed':False,'P4_authorized':False,'recommended_next_action':summary['recommended_next_action']}
        (staging/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8'); (staging/DECISION).write_text(json.dumps(decision,indent=2,sort_keys=True)+'\n',encoding='utf-8'); write_csv(staging/GATES,gates)
        manifest=[]
        for p in sorted(staging.iterdir()):
            if p.is_file() and p.name!=MANIFEST: manifest.append({'file':p.name,'sha256':sha256(p),'bytes':p.stat().st_size})
        write_csv(staging/MANIFEST,manifest); staging.rename(out)
        print('='*180); print(M,'PASS'); print('Classification                         :',classification); print('Best Day365 teacher realization         :',best_rid); print('Formal Day30->Day405 splice authorized  :',splice); print('Hold durations screened (days)          :',HOLD_DAYS); print('Top-3 early coarse windows              :',top3); print('Production cadence selected             : False'); print('New transport executed                  : False'); print('Day405->Day410 remains authorized       : True'); print('P4 authorized                           : False'); print('Output directory                        :',out); print('='*180); return 0
    except Exception as exc:
        if staging.exists(): shutil.rmtree(staging,ignore_errors=True)
        blocked.mkdir(parents=True,exist_ok=True); report=blocked/f'{OUT_TOKEN}_Blocked_Report.json'; report.write_text(json.dumps({'milestone':M,'status':BLOCK,'failed_stage':stage,'exception':repr(exc),'authoritative_physics_state_mutated':False,'authoritative_physical_time_advanced':False,'transport_execution_executed':False,'P4_authorized':False,'gates_completed':gates},indent=2,sort_keys=True)+'\n',encoding='utf-8')
        print(M,'TECHNICAL / AUTHORITY BLOCK'); print('Stage:',stage); print('Exception:',repr(exc)); return 2

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--project-root',type=Path,default=Path('.')); ap.add_argument('--drive-root',type=Path,default=Path('/content/drive/MyDrive/PAD_Stream_Compute')); ap.add_argument('--self-test',action='store_true'); args=ap.parse_args()
    if args.self_test: selftest(); raise SystemExit(0)
    raise SystemExit(main(args.project_root,args.drive_root))
