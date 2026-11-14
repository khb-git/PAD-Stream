#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,shutil,subprocess,sys
from pathlib import Path
from typing import Any
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors

M="POSTV16-AV4-PIVOT-GPU-HYB-G2-VIS-A1"
PASS="POSTV16AV4PIVOTGPUHYBG2VISA1_CERTIFIED_EARLYTIME_3D_VISUALIZATION_PASS_NO_PHYSICS_MUTATION"
BLOCK="POSTV16AV4PIVOTGPUHYBG2VISA1_TECHNICAL_OR_AUTHORITY_BLOCK_NO_PHYSICS_MUTATION"
BRANCH="postv16-av4-pivot"
PARENT="aa54533d1bb080786a1d87f81eb971fe0906b9d6"
RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"
VIS_A3=("PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_VIS_A3_Industry_Style_Reservoir_PostProcessing.py","270def5961bf5a434564b77fe365c6c1c50c2e46")
R3_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_Rank3_Day40_Day45_ExactFlow_and_Hybrid_Endpoint_Diagnostic"
R1_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_R1_Rank1_Day75_Day80_ExactFlow_and_Hybrid_Endpoint_Diagnostic"
R2_REL=BASE/"POSTV16_AV4_PIVOT_GPU_HYB_G2_R2_Rank2_Day120_Day125_ExactFlow_and_Hybrid_Endpoint_Diagnostic"
R3R5_REL=Path("provenance/hybrid_dp/V16E41R3R5_MULTI_REFRESH_CADENCE_SENSITIVITY_RUNTIME_POLICY_CALIBRATION")
R3_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_Summary.json"
R1_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_R1_Summary.json"
R2_SUM="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G2_R2_Summary.json"
DAYS=[40,45,75,80,120,125]; PAIRS=[(40,45),(75,80),(120,125)]
GRID=(15,50,50); NZ,NY,NX=GRID
DX_FT=20.0;DY_FT=20.0;DZ_FT=4.0;LX_FT=1000.;LY_FT=1000.;LZ_FT=60.
POROSITY=0.20; CELL_PV_FT3=POROSITY*DX_FT*DY_FT*DZ_FT
THRESHOLDS=(0.05,0.10,0.25,0.40,0.60); DELTA_FILTER=0.02
OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G2_VIS_A1"
OUT_REL=BASE/(OUT_TOKEN+"_Certified_EarlyTime_3D_Visualization")
STAGE_REL=BASE/(OUT_TOKEN+"_STAGING")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json";METRICS=f"{OUT_TOKEN}_Volumetric_Occupancy_Metrics.csv";PAIR=f"{OUT_TOKEN}_Pairwise_Change_Metrics.csv";INDEX=f"{OUT_TOKEN}_Visualization_Index.csv";MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"
class GateError(RuntimeError):pass

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for c in iter(lambda:f.read(1<<20),b''):h.update(c)
 return h.hexdigest()
def gt(root,*a):return subprocess.check_output(['git','-C',str(root),*a],text=True).strip()
def mod(root,spec,name):
 fn,blob=spec;p=root/fn
 if gt(root,'hash-object',str(p))!=blob:raise GateError('source_blob:'+fn)
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
def js(p):return json.loads(Path(p).read_text())
def write_csv(p,rows):
 fields=[]
 for r in rows:
  for k in r:
   if k not in fields:fields.append(k)
 with open(p,'w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows)
def load_state(p):
 with np.load(p,allow_pickle=False) as z:return np.asarray(z['transport_saturation'],float),float(np.asarray(z['physical_time_days']).reshape(()))
def load_diag(p):
 with np.load(p,allow_pickle=False) as z:
  return {'pressure':np.asarray(z['pressure_psi'],float),'xyz_m':np.asarray(z['xyz_m'],float),'tau_end_s':np.asarray(z['tau_end_s'],float),'weights_m3_s':np.asarray(z['weights_m3_s'],float),'producer_labels':np.asarray(z['producer']).astype('U64')}
def records(drive):
 r3=js(drive/R3_REL/R3_SUM);r1=js(drive/R1_REL/R1_SUM);r2=js(drive/R2_REL/R2_SUM)
 if not r3.get('early_3D_visualization_sequence_authorized'):raise GateError('R3_3D_not_authorized')
 specs={
 40:(drive/R3_REL/'POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_Exact_Day40_State.npz',drive/R3_REL/'POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_Day40_ExactFlow_and_Hybrid_Diagnostic.npz',r3['Day40_state_sha256']),
 45:(drive/R3_REL/'POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_Exact_Day45_State.npz',drive/R3_REL/'POSTV16_AV4_PIVOT_GPU_HYB_G2_R3_Day45_ExactFlow_and_Hybrid_Diagnostic.npz',r3['Day45_state_sha256']),
 75:(drive/R1_REL/'POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_R1_Exact_Day75_SelectedPolicy_State.npz',drive/R1_REL/'POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_R1_Day75_ExactFlow_and_Hybrid_Diagnostic.npz',r1['Day75_exact_state_sha256']),
 80:(drive/R3R5_REL/'V16E41R3R5_Selected_Calibration_State_80d.npz',drive/R1_REL/'POSTV16_AV4_PIVOT_GPU_HYB_G2_R1_R1_Day80_ExactFlow_and_Hybrid_Diagnostic.npz',r1['Day80_state_sha256']),
 120:(drive/R2_REL/'POSTV16_AV4_PIVOT_GPU_HYB_G2_R2_Exact_Day120_State.npz',drive/R2_REL/'POSTV16_AV4_PIVOT_GPU_HYB_G2_R2_Day120_ExactFlow_and_Hybrid_Diagnostic.npz',r2['Day120_state_sha256']),
 125:(drive/R2_REL/'POSTV16_AV4_PIVOT_GPU_HYB_G2_R2_Exact_Day125_State.npz',drive/R2_REL/'POSTV16_AV4_PIVOT_GPU_HYB_G2_R2_Day125_ExactFlow_and_Hybrid_Diagnostic.npz',r2['Day125_state_sha256'])}
 out=[]
 for d in DAYS:
  sp,dp,exp=specs[d]
  if not sp.is_file() or not dp.is_file():raise GateError(f'missing_Day{d}')
  if sha(sp)!=exp:raise GateError(f'Day{d}_state_sha')
  sat,t=load_state(sp);diag=load_diag(dp)
  if abs(t-d)>1e-10 or sat.shape!=GRID or diag['pressure'].shape!=GRID:raise GateError(f'Day{d}_shape_time')
  out.append({'day':d,'saturation':sat,'state_sha':exp,'diag_sha':sha(dp),'state_file':sp,'diag_file':dp,**diag})
 return out

def occ(r):
 sat=r['saturation'];n=sat.size;pv=n*CELL_PV_FT3;sgpv=float(np.sum(sat)*CELL_PV_FT3)
 row={'day':r['day'],'state_sha256':r['state_sha'],'diagnostic_sha256':r['diag_sha'],'saturation_min':float(sat.min()),'saturation_mean':float(sat.mean()),'saturation_max':float(sat.max()),'total_pore_volume_ft3':pv,'gas_saturation_weighted_pore_volume_ft3':sgpv}
 for th in THRESHOLDS:
  m=sat>=th;tag=str(th).replace('.','p');q=int(m.sum());sg=float(np.sum(sat[m])*CELL_PV_FT3)
  row[f'cell_volume_fraction_Sg_ge_{tag}']=q/n
  row[f'pore_volume_fraction_Sg_ge_{tag}']=q/n
  row[f'gas_saturation_PV_fraction_in_cells_Sg_ge_{tag}']=sg/sgpv if sgpv>0 else 0.0
 return row

def delta3d(a,b,out):
 ds=b['saturation']-a['saturation'];k,j,i=np.indices(GRID);x=(i+.5)*DX_FT;y=(j+.5)*DY_FT;z=(k+.5)*DZ_FT;m=np.abs(ds)>=DELTA_FILTER
 if not np.any(m):m=np.abs(ds)>0
 vmax=max(float(np.max(np.abs(ds[m]))) if np.any(m) else 1e-6,1e-6)
 fig=plt.figure(figsize=(10.5,8.2));ax=fig.add_subplot(111,projection='3d')
 sc=ax.scatter(x[m],y[m],z[m],c=ds[m],cmap='coolwarm',norm=colors.TwoSlopeNorm(vmin=-vmax,vcenter=0,vmax=vmax),s=8,alpha=.72,linewidths=0)
 ax.set_xlim(0,LX_FT);ax.set_ylim(0,LY_FT);ax.set_zlim(0,LZ_FT);ax.set_box_aspect((1,1,(LZ_FT/LX_FT)*5));ax.view_init(elev=24,azim=-58)
 ax.set_xlabel('X (ft)');ax.set_ylabel('Y (ft)');ax.set_zlabel('Z (ft)');ax.set_title(f"Day {a['day']} → {b['day']}: 3D saturation redistribution\nvisualization filter |ΔSg| ≥ {DELTA_FILTER:.2f}; 5× vertical exaggeration")
 fig.colorbar(sc,ax=ax,pad=.08,shrink=.72).set_label('ΔSg');fig.tight_layout();p=out/f"Day{a['day']:04d}_to_Day{b['day']:04d}_DeltaSg_3D.png";fig.savefig(p,dpi=200,bbox_inches='tight');plt.close(fig);return p

def pairmetric(a,b):
 ds=b['saturation']-a['saturation'];dp=b['pressure']-a['pressure']
 return {'day_start':a['day'],'day_end':b['day'],'saturation_relative_L2':float(np.linalg.norm(ds.ravel())/max(np.linalg.norm(a['saturation'].ravel()),1e-30)),'saturation_Linf':float(np.max(np.abs(ds))),'pressure_relative_L2':float(np.linalg.norm(dp.ravel())/max(np.linalg.norm(a['pressure'].ravel()),1e-30)),'pressure_max_abs_psi':float(np.max(np.abs(dp))),'cells_abs_DeltaSg_ge_0p02':int(np.count_nonzero(np.abs(ds)>=DELTA_FILTER))}

def selftest():
 assert DAYS==[40,45,75,80,120,125] and GRID==(15,50,50) and abs(CELL_PV_FT3-320.)<1e-12
 print('POSTV16 GPU-HYB-G2-VIS-A1 structural self-test: PASS')

def main(root,drive):
 root=root.resolve();drive=drive.resolve();out=drive/OUT_REL;staging=drive/STAGE_REL;blocked=drive/BLOCK_REL;stage='preflight';gates=[]
 def gate(n,c,d=None):
  ok=bool(c);gates.append({'stage':stage,'gate':n,'pass':ok,'detail':'' if d is None else repr(d)});print(f"[{'PASS' if ok else 'FAIL'}] {n}",flush=True)
  if not ok:raise GateError(n)
 try:
  print('='*170);print('G2-VIS-A1 — CERTIFIED EARLY-TIME 3D VISUALIZATION');print('READ ONLY — NO PHYSICS OR STATE MUTATION');print('='*170)
  stage='repo';gate('branch',gt(root,'branch','--show-current')==BRANCH);gate('parent',gt(root,'rev-parse','HEAD^')==PARENT);gate('clean',gt(root,'status','--porcelain')=='')
  vis=mod(root,VIS_A3,'g2_vis_a3');recs=records(drive);gate('six_records',len(recs)==6)
  stage='output';gate('output_absent',not out.exists());
  if staging.exists():shutil.rmtree(staging)
  staging.mkdir(parents=True)
  pmin=min(float(r['pressure'].min()) for r in recs);pmax=max(float(r['pressure'].max()) for r in recs)
  ta=np.concatenate([r['tau_end_s']/vis.DAY_TO_S for r in recs]);pos=ta[ta>0];tof=colors.LogNorm(vmin=max(float(pos.min()),1e-6),vmax=float(pos.max()))
  geos=[];overs=[];press=[]
  for r in recs:
   geos.append(vis.plot_geocellular_saturation(r,staging));overs.append(vis.plot_plume_streamline_overlay(r,staging,tof));press.append(vis.plot_pressure_layer(r,staging,pmin,pmax))
  labels=[f'Day {d}' for d in DAYS]
  vis.make_contact_sheet(geos,labels,staging/f'{OUT_TOKEN}_Saturation_3D_ContactSheet.png');vis.make_contact_sheet(overs,labels,staging/f'{OUT_TOKEN}_Streamline_Overlay_3D_ContactSheet.png');vis.make_contact_sheet(press,labels,staging/f'{OUT_TOKEN}_Pressure_ContactSheet.png')
  vis.make_gif(geos,labels,staging/f'{OUT_TOKEN}_Saturation_3D_Progression.gif');vis.make_gif(overs,labels,staging/f'{OUT_TOKEN}_Streamline_Overlay_3D_Progression.gif')
  by={r['day']:r for r in recs}
  for a,b in PAIRS:delta3d(by[a],by[b],staging)
  write_csv(staging/METRICS,[occ(r) for r in recs]);write_csv(staging/PAIR,[pairmetric(by[a],by[b]) for a,b in PAIRS])
  idx=[{'file':p.name,'type':'GIF' if p.suffix.lower()=='.gif' else 'PNG'} for p in sorted(staging.iterdir()) if p.suffix.lower() in {'.png','.gif'}];write_csv(staging/INDEX,idx)
  summary={'milestone':M,'status':PASS,'classification':'CERTIFIED_EARLY_DAY40_45_75_80_120_125_3D_VISUALIZATION_COMPLETE_NO_PHYSICS_MUTATION','days':DAYS,'pairwise_change_windows':[list(x) for x in PAIRS],'individual_3D_saturation_count':len(geos),'individual_3D_streamline_overlay_count':len(overs),'individual_pressure_map_count':len(press),'volumetric_thresholds':list(THRESHOLDS),'gas_saturation_PV_fraction_metric_added':True,'uniform_phi_equal_cell_note':'cell-volume and pore-volume fractions are equal because phi=0.20 and cell dimensions are uniform','physics_mutation':False,'production_pressure_refresh_cadence_selected':False,'P4_authorized':False}
  (staging/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n');write_csv(staging/'GATES.csv',gates)
  manifest=[{'file':p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(staging.iterdir()) if p.is_file() and p.name!=MANIFEST];write_csv(staging/MANIFEST,manifest)
  staging.rename(out);print(M,'PASS');print('Output:',out);return 0
 except Exception as e:
  if staging.exists():shutil.rmtree(staging)
  blocked.mkdir(parents=True,exist_ok=True);(blocked/f'{OUT_TOKEN}_Blocked_Report.json').write_text(json.dumps({'milestone':M,'status':BLOCK,'failed_stage':stage,'exception':repr(e),'gates':gates,'physics_mutation':False},indent=2,sort_keys=True)+'\n');print(M,'BLOCK',repr(e));return 2

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--project-root',type=Path,default=Path('.'));ap.add_argument('--drive-root',type=Path,default=Path('/content/drive/MyDrive/PAD_Stream_Compute'));ap.add_argument('--self-test',action='store_true');a=ap.parse_args()
 if a.self_test:selftest();raise SystemExit(0)
 raise SystemExit(main(a.project_root,a.drive_root))
