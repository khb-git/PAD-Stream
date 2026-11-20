#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,json,subprocess
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors
from PIL import Image

M="POSTV16-AV4-PIVOT-GPU-HYB-INT-VIS-A1"
PASS="POSTV16AV4PIVOTGPUHYBINTVISA1_INTEGRATED_DAY30_DAY45_3D_VISUALIZATION_PASS_NO_PHYSICS_MUTATION"
BLOCK="POSTV16AV4PIVOTGPUHYBINTVISA1_TECHNICAL_OR_AUTHORITY_BLOCK_NO_PHYSICS_MUTATION"
BRANCH="postv16-av4-pivot"
PARENT="82d21cc0c9ee33dc4a29645b4008bcb32e675b17"
R4R3_RUNNER="PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R4_R3_Cartesian_GlobalDelta_Projection_Validation_and_Day30_Day45_Run.py"
R4R3_BLOB="e49ca05b37f4b3ea6cca523c6a7b6e184f801016"
R4R3_STATUS="POSTV16AV4PIVOTGPUHYBINTA1R4R3_CARTESIAN_GLOBAL_DELTA_PROJECTION_VALIDATION_AND_DAY30_DAY45_RUN_PASS"
RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"
R4R3_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_INT_A1_R4_R3"
R4R3_REL=BASE/(R4R3_TOKEN+"_Cartesian_GlobalDelta_Projection_Validation_and_Day30_Day45_Run")
R4R3_SUM=f"PAD_Stream_{R4R3_TOKEN}_Summary.json"
R4R3_INDEX=f"{R4R3_TOKEN}_Visualization_Checkpoint_Index.csv"
R4R3_PROJ=f"{R4R3_TOKEN}_Cartesian_GlobalDelta_Projection_Audit.csv"
R4R3_MANIFEST=f"{R4R3_TOKEN}_Artifact_Manifest.csv"
GRID=(15,50,50);NZ,NY,NX=GRID
DX_FT=20.0;DY_FT=20.0;DZ_FT=4.0;LX_FT=1000.0;LY_FT=1000.0;LZ_FT=60.0
M_TO_FT=1.0/0.3048;DAY_TO_S=86400.0
SAT_FILTER=0.25;DELTA_S_FILTER=0.005;MID_K=7
VIS_DAYS=(30.0,35.0,40.0,45.0)
DELTA_PAIRS=((30.0,35.0),(35.0,40.0),(40.0,45.0),(30.0,45.0))
OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_INT_VIS_A1"
OUT_REL=BASE/(OUT_TOKEN+"_Integrated_Day30_Day45_3D_Visualization")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json";INDEX=f"{OUT_TOKEN}_Visualization_Index.csv";METRICS=f"{OUT_TOKEN}_Checkpoint_Metrics.csv";DELTA=f"{OUT_TOKEN}_Delta_Metrics.csv";PROJ=f"{OUT_TOKEN}_Projection_Event_Summary.csv";MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"

class GateError(RuntimeError): pass

def sha(p:Path):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''): h.update(c)
 return h.hexdigest()
def gt(root:Path,*a): return subprocess.check_output(['git','-C',str(root),*a],text=True).strip()
def rows(p:Path):
 with p.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def js(p:Path): return json.loads(p.read_text(encoding='utf-8'))
def write_csv(p,rs):
 rs=list(rs)
 if not rs: p.write_text('',encoding='utf-8');return
 fs=[]
 for r in rs:
  for k in r:
   if k not in fs:fs.append(k)
 with p.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fs,lineterminator='\n');w.writeheader();w.writerows(rs)
def exact_blob(root,fn,expected):
 p=root/fn
 if not p.is_file():raise GateError('missing_source:'+fn)
 a=gt(root,'hash-object',str(p))
 if a!=expected:raise GateError(f'source_blob:{fn}:{a}:{expected}')
 return a
def verify_manifest(d,name):
 rr=rows(d/name)
 if not rr:raise GateError('empty_manifest')
 for r in rr:
  p=d/r['file']
  if not p.is_file():raise GateError('manifest_missing:'+r['file'])
  if sha(p)!=r['sha256']:raise GateError('manifest_sha:'+r['file'])
  if p.stat().st_size!=int(r['bytes']):raise GateError('manifest_bytes:'+r['file'])
def load_npz(p):
 with np.load(p,allow_pickle=False) as z:return {k:np.asarray(z[k]) for k in z.files}
def savefig(fig,out,name,index,kind,day=''):
 p=out/name;fig.savefig(p,dpi=220,bbox_inches='tight');plt.close(fig)
 index.append({'file':p.name,'sha256':sha(p),'bytes':p.stat().st_size,'kind':kind,'day':day,'authority':'R4_R3_READ_ONLY'})
 return p
def cfg3d(ax,title):
 ax.set_title(title,pad=12);ax.set_xlabel('X (ft)');ax.set_ylabel('Y (ft)');ax.set_zlabel('Z (ft)')
 ax.set_xlim(0,LX_FT);ax.set_ylim(0,LY_FT);ax.set_zlim(0,LZ_FT);ax.view_init(elev=24,azim=-58);ax.set_box_aspect((1,1,(LZ_FT/LX_FT)*5.0))
def saturation3d(r,out,index,norm):
 s=r['sat'];k,j,i=np.indices(s.shape);m=s>=SAT_FILTER
 fig=plt.figure(figsize=(10.5,8.2));ax=fig.add_subplot(111,projection='3d')
 sc=ax.scatter((i[m]+.5)*DX_FT,(j[m]+.5)*DY_FT,(k[m]+.5)*DZ_FT,c=s[m],norm=norm,s=8,alpha=.7,linewidths=0)
 cfg3d(ax,f"Day {r['day']:.0f} — integrated CO2 saturation plume");fig.colorbar(sc,ax=ax,pad=.08,shrink=.72,label='Gas saturation')
 return savefig(fig,out,f"Day{int(r['day']):03d}_Saturation_3D.png",index,'SATURATION_3D',str(r['day']))
def pressure3d(r,out,index,norm):
 p=r['p'];k,j,i=np.indices(p.shape);m=np.isin(k,(2,5,7,9,12))
 fig=plt.figure(figsize=(10.5,8.2));ax=fig.add_subplot(111,projection='3d')
 sc=ax.scatter((i[m]+.5)*DX_FT,(j[m]+.5)*DY_FT,(k[m]+.5)*DZ_FT,c=p[m],norm=norm,s=5,alpha=.58,linewidths=0)
 cfg3d(ax,f"Day {r['day']:.0f} — exact FV pressure, stacked layers");fig.colorbar(sc,ax=ax,pad=.08,shrink=.72,label='Pressure (psi)')
 return savefig(fig,out,f"Day{int(r['day']):03d}_Pressure_3D.png",index,'PRESSURE_3D',str(r['day']))
def pressure2d(r,out,index,norm):
 fig,ax=plt.subplots(figsize=(8.4,7.2));im=ax.imshow(r['p'][MID_K],origin='lower',extent=(0,LX_FT,0,LY_FT),norm=norm,aspect='equal')
 ax.set_xlabel('X (ft)');ax.set_ylabel('Y (ft)');ax.set_title(f"Day {r['day']:.0f} — exact pressure, layer {MID_K+1}");fig.colorbar(im,ax=ax,pad=.02,label='Pressure (psi)')
 return savefig(fig,out,f"Day{int(r['day']):03d}_Pressure_Layer{MID_K+1}.png",index,'PRESSURE_LAYER',str(r['day']))
def streamline3d(r,out,index,tofnorm):
 xyz=r['xyz']*M_TO_FT;tau=r['tau']/DAY_TO_S
 fig=plt.figure(figsize=(10.5,8.2));ax=fig.add_subplot(111,projection='3d')
 stride=max(1,len(xyz)//450)
 for pts in xyz[::stride]: ax.plot(pts[:,0],pts[:,1],pts[:,2],linewidth=.38,alpha=.25)
 e=xyz[:,-1,:];sc=ax.scatter(e[:,0],e[:,1],e[:,2],c=tau,norm=tofnorm,s=8,alpha=.8)
 cfg3d(ax,f"Day {r['day']:.0f} — exact Pollock geometry + terminal TOF");fig.colorbar(sc,ax=ax,pad=.08,shrink=.72,label='Terminal TOF (days)')
 return savefig(fig,out,f"Day{int(r['day']):03d}_Pollock_TOF_3D.png",index,'POLLOCK_TOF_3D',str(r['day']))
def overlay3d(r,out,index,snorm):
 s=r['sat'];xyz=r['xyz']*M_TO_FT;k,j,i=np.indices(s.shape);m=s>=SAT_FILTER
 fig=plt.figure(figsize=(10.5,8.2));ax=fig.add_subplot(111,projection='3d')
 sc=ax.scatter((i[m]+.5)*DX_FT,(j[m]+.5)*DY_FT,(k[m]+.5)*DZ_FT,c=s[m],norm=snorm,s=7,alpha=.38,linewidths=0)
 stride=max(1,len(xyz)//220)
 for pts in xyz[::stride]:ax.plot(pts[:,0],pts[:,1],pts[:,2],linewidth=.4,alpha=.32)
 cfg3d(ax,f"Day {r['day']:.0f} — plume + exact Pollock streamlines");fig.colorbar(sc,ax=ax,pad=.08,shrink=.72,label='Gas saturation')
 return savefig(fig,out,f"Day{int(r['day']):03d}_Plume_Streamline_Overlay_3D.png",index,'PLUME_STREAMLINE_OVERLAY',str(r['day']))
def tof_hist(r,out,index):
 fig,ax=plt.subplots(figsize=(8.4,6.2));ax.hist(r['tau']/DAY_TO_S,bins=40,weights=r['w']);ax.set_xlabel('Terminal TOF (days)');ax.set_ylabel('Streamline flow weight (m3/s)');ax.set_title(f"Day {r['day']:.0f} — flux-weighted TOF distribution")
 return savefig(fig,out,f"Day{int(r['day']):03d}_TOF_Weighted_Histogram.png",index,'TOF_HISTOGRAM',str(r['day']))
def delta_p(a,b,out,index,v):
 d=b['p'][MID_K]-a['p'][MID_K];norm=colors.TwoSlopeNorm(vmin=-v,vcenter=0,vmax=v)
 fig,ax=plt.subplots(figsize=(8.4,7.2));im=ax.imshow(d,origin='lower',extent=(0,LX_FT,0,LY_FT),norm=norm,aspect='equal');ax.set_xlabel('X (ft)');ax.set_ylabel('Y (ft)');ax.set_title(f"Day {a['day']:.0f} → {b['day']:.0f} — ΔP, layer {MID_K+1}");fig.colorbar(im,ax=ax,pad=.02,label='Pressure change (psi)')
 return savefig(fig,out,f"Day{int(a['day']):03d}_to_Day{int(b['day']):03d}_DeltaP.png",index,'DELTA_PRESSURE',f"{a['day']}->{b['day']}")
def delta_s(a,b,out,index,v):
 d=b['sat']-a['sat'];k,j,i=np.indices(d.shape);m=np.abs(d)>=DELTA_S_FILTER;norm=colors.TwoSlopeNorm(vmin=-v,vcenter=0,vmax=v)
 fig=plt.figure(figsize=(10.5,8.2));ax=fig.add_subplot(111,projection='3d');sc=ax.scatter((i[m]+.5)*DX_FT,(j[m]+.5)*DY_FT,(k[m]+.5)*DZ_FT,c=d[m],norm=norm,s=8,alpha=.7,linewidths=0);cfg3d(ax,f"Day {a['day']:.0f} → {b['day']:.0f} — 3D ΔSg");fig.colorbar(sc,ax=ax,pad=.08,shrink=.72,label='Gas saturation change')
 return savefig(fig,out,f"Day{int(a['day']):03d}_to_Day{int(b['day']):03d}_DeltaSg_3D.png",index,'DELTA_SATURATION_3D',f"{a['day']}->{b['day']}")
def mass_timeline(recs,out,index):
 d=np.array([r['day'] for r in recs]);inj=np.array([r['inj'] for r in recs]);prod=np.array([r['prod'] for r in recs]);stored=np.array([r['stored'] for r in recs])
 fig,ax=plt.subplots(figsize=(9.5,6.2));ax.plot(d,inj,marker='o',label='Cumulative injected');ax.plot(d,prod,marker='o',label='Cumulative produced');ax.plot(d,stored,marker='o',label='Stored CO2')
 for x in (35,40,45):ax.axvline(x,alpha=.25)
 ax.set_xlabel('Physical time (days)');ax.set_ylabel('CO2 component mass (kg)');ax.set_title('Integrated mass evolution and 5-day refresh boundaries');ax.legend()
 return savefig(fig,out,'Integrated_Mass_Controller_Timeline.png',index,'MASS_CONTROLLER_TIMELINE')
def projection_diag(rr,out,index):
 if not rr:return None
 t=np.array([float(r['parent_time_days']) for r in rr]);linf=np.array([float(r['projection_correction_Linf_kg']) for r in rr]);order=np.argsort(t)
 fig,ax=plt.subplots(figsize=(9.5,6.2));ax.scatter(t,linf,s=14,alpha=.65);ax.set_xlabel('Parent time (days)');ax.set_ylabel('Linf projection correction (kg)');ax.set_title('Cartesian projection events — diagnostic only')
 ax2=ax.twinx();ax2.plot(t[order],np.arange(1,len(t)+1)[order],alpha=.45);ax2.set_ylabel('Cumulative projection events')
 return savefig(fig,out,'Cartesian_Projection_Event_Diagnostic.png',index,'PROJECTION_EVENT_DIAGNOSTIC')
def contact(paths,out,name,index,kind):
 ims=[Image.open(p).convert('RGB') for p in paths[:4]];w=max(x.width for x in ims);h=max(x.height for x in ims);canvas=Image.new('RGB',(2*w,2*h))
 for n,im in enumerate(ims):canvas.paste(im,((n%2)*w,(n//2)*h))
 p=out/name;canvas.save(p);index.append({'file':p.name,'sha256':sha(p),'bytes':p.stat().st_size,'kind':kind,'day':'','authority':'DERIVED_CONTACT_SHEET'});return p
def gif(paths,out,name,index,kind):
 ims=[Image.open(p).convert('RGB') for p in paths];p=out/name;ims[0].save(p,save_all=True,append_images=ims[1:],duration=900,loop=0);index.append({'file':p.name,'sha256':sha(p),'bytes':p.stat().st_size,'kind':kind,'day':'','authority':'DERIVED_ANIMATION'});return p

def selftest(root:Path):
 assert exact_blob(root,R4R3_RUNNER,R4R3_BLOB)==R4R3_BLOB
 assert GRID==(15,50,50) and MID_K==7 and VIS_DAYS==(30.0,35.0,40.0,45.0)
 print('POSTV16 GPU-HYB-INT-VIS-A1 integrated visualization self-test: PASS')

def main(root:Path,drive:Path)->int:
 root=root.resolve();drive=drive.resolve();out=drive/OUT_REL;blocked=drive/BLOCK_REL;gates=[];stage='preflight'
 def gate(n,c,d=None):
  ok=bool(c);gates.append({'stage':stage,'gate':n,'pass':ok,'detail':'' if d is None else repr(d)});print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"),flush=True)
  if not ok:raise GateError(n)
 try:
  print('='*184);print('INT-VIS-A1 — INTEGRATED DAY30/DAY35/DAY40/DAY45 3D VISUALIZATION');print('READ-ONLY. NO PHYSICS. NO STATE MUTATION.');print('='*184)
  stage='repository';gate('branch_exact',gt(root,'branch','--show-current')==BRANCH);gate('parent_is_R4_R3_PASS_commit',gt(root,'rev-parse','HEAD^')==PARENT,gt(root,'rev-parse','HEAD^'));gate('repository_clean',gt(root,'status','--porcelain')=='')
  stage='source_authority';gate('R4_R3_blob_exact',exact_blob(root,R4R3_RUNNER,R4R3_BLOB)==R4R3_BLOB)
  stage='R4_R3_authority';d=drive/R4R3_REL;s=js(d/R4R3_SUM);gate('R4_R3_status_exact',s.get('status')==R4R3_STATUS,s.get('status'));gate('visualization_authorized',s.get('INT_VIS_A1_integrated_3D_visualization_authorized') is True);gate('visualization_ready',s.get('visualization_ready') is True);gate('days_exact',s.get('visualization_checkpoint_days')==[30.0,35.0,40.0,45.0]);gate('R3_R2_local_validation_PASS',s.get('R3_R2_local_validation_passed') is True);gate('production_closed',s.get('integrated_GPU_runtime_production_authorized') is False);verify_manifest(d,R4R3_MANIFEST)
  idx=rows(d/R4R3_INDEX);gate('checkpoint_index_four',len(idx)==4,len(idx));by={}
  for r in idx:
   day=float(r['day']);p=d/r['file'];gate(f'Day{int(day)}_checkpoint_present',p.is_file(),str(p));gate(f'Day{int(day)}_checkpoint_sha',sha(p)==r['sha256']);z=load_npz(p);gate(f'Day{int(day)}_grid_shapes',z['transport_saturation'].shape==GRID and z['pressure_psi'].shape==GRID);gate(f'Day{int(day)}_streamline_shape',z['streamline_xyz_m'].ndim==3 and z['streamline_xyz_m'].shape[2]==3,z['streamline_xyz_m'].shape)
   by[day]={'day':day,'sat':z['transport_saturation'].astype(float),'p':z['pressure_psi'].astype(float),'xyz':z['streamline_xyz_m'].astype(float),'tau':z['streamline_tau_end_s'].astype(float),'w':z['streamline_weights_m3_s'].astype(float),'stored':float(z['stored_co2_mass_current_kg'].reshape(())),'inj':float(z['cumulative_injected_co2_mass_kg'].reshape(())),'prod':float(z['cumulative_produced_co2_mass_kg'].reshape(())),'cut':float(z['producer_co2_gas_cut'].reshape(()))}
  gate('all_days_loaded',sorted(by)==list(VIS_DAYS),sorted(by));pr=rows(d/R4R3_PROJ);gate('projection_event_count_exact',len(pr)==int(s['cartesian_global_delta_projection_count']),(len(pr),s['cartesian_global_delta_projection_count']))
  stage='render';gate('output_absent',not out.exists(),str(out));out.mkdir(parents=True);index=[];recs=[by[x] for x in VIS_DAYS]
  pmin=min(float(r['p'].min()) for r in recs);pmax=max(float(r['p'].max()) for r in recs);smin=min(float(r['sat'].min()) for r in recs);smax=max(float(r['sat'].max()) for r in recs);pn=colors.Normalize(pmin,pmax);sn=colors.Normalize(smin,smax);alltof=np.concatenate([r['tau']/DAY_TO_S for r in recs]);pos=alltof[alltof>0];gate('positive_TOF',pos.size>0,pos.size);tn=colors.LogNorm(max(float(pos.min()),1e-9),float(pos.max()))
  satp=[];pp=[];sp=[];ov=[];metrics=[]
  for r in recs:
   satp.append(saturation3d(r,out,index,sn));pp.append(pressure3d(r,out,index,pn));pressure2d(r,out,index,pn);sp.append(streamline3d(r,out,index,tn));ov.append(overlay3d(r,out,index,sn));tof_hist(r,out,index)
   metrics.append({'day':r['day'],'saturation_min':float(r['sat'].min()),'saturation_mean':float(r['sat'].mean()),'saturation_max':float(r['sat'].max()),'visible_plume_cells_Sg_ge_0p25':int(np.sum(r['sat']>=SAT_FILTER)),'pressure_min_psi':float(r['p'].min()),'pressure_mean_psi':float(r['p'].mean()),'pressure_max_psi':float(r['p'].max()),'stored_CO2_mass_kg':r['stored'],'cumulative_injected_kg':r['inj'],'cumulative_produced_kg':r['prod'],'producer_CO2_gas_cut':r['cut'],'streamline_count':int(r['xyz'].shape[0]),'TOF_min_days':float(np.min(r['tau'])/DAY_TO_S),'TOF_max_days':float(np.max(r['tau'])/DAY_TO_S)})
  dpmax=max(float(np.max(np.abs(by[b]['p'][MID_K]-by[a]['p'][MID_K]))) for a,b in DELTA_PAIRS);dsmax=max(float(np.max(np.abs(by[b]['sat']-by[a]['sat']))) for a,b in DELTA_PAIRS);dpp=[];dsp=[];dm=[]
  for a,b in DELTA_PAIRS:
   A=by[a];B=by[b];dpp.append(delta_p(A,B,out,index,max(dpmax,1e-12)));dsp.append(delta_s(A,B,out,index,max(dsmax,1e-12)));ds=B['sat']-A['sat'];dp=B['p']-A['p'];dm.append({'start_day':a,'end_day':b,'saturation_relative_L2':float(np.linalg.norm(ds.ravel())/max(np.linalg.norm(A['sat'].ravel()),1e-30)),'saturation_Linf':float(np.max(np.abs(ds))),'pressure_relative_L2':float(np.linalg.norm(dp.ravel())/max(np.linalg.norm(A['p'].ravel()),1e-30)),'pressure_Linf_psi':float(np.max(np.abs(dp))),'stored_mass_change_kg':B['stored']-A['stored']})
  mass_timeline(recs,out,index);projection_diag(pr,out,index);contact(satp,out,'Integrated_Saturation_3D_ContactSheet.png',index,'SATURATION_CONTACT_SHEET');contact(pp,out,'Integrated_Pressure_3D_ContactSheet.png',index,'PRESSURE_CONTACT_SHEET');contact(sp,out,'Integrated_Pollock_TOF_3D_ContactSheet.png',index,'POLLOCK_TOF_CONTACT_SHEET');contact(ov,out,'Integrated_Plume_Streamline_ContactSheet.png',index,'OVERLAY_CONTACT_SHEET');contact(dpp,out,'Integrated_DeltaP_ContactSheet.png',index,'DELTA_PRESSURE_CONTACT_SHEET');contact(dsp,out,'Integrated_DeltaSg_ContactSheet.png',index,'DELTA_SATURATION_CONTACT_SHEET');gif(satp,out,'Integrated_Saturation_3D_Evolution.gif',index,'SATURATION_GIF');gif(pp,out,'Integrated_Pressure_3D_Evolution.gif',index,'PRESSURE_GIF')
  ps=[]
  if pr:
   arr=lambda k:np.array([float(r[k]) for r in pr]);t=arr('parent_time_days');ps=[{'event_count':len(pr),'first_event_day':float(t.min()),'last_event_day':float(t.max()),'projection_correction_L1_sum_kg':float(arr('projection_correction_L1_kg').sum()),'projection_correction_Linf_max_kg':float(arr('projection_correction_Linf_kg').max()),'max_changed_supported_cell_count':int(arr('changed_supported_cell_count').max()),'max_raw_negative_cell_count':int(arr('raw_negative_cell_count').max()),'max_abs_global_delta_identity_residual_kg':float(np.abs(arr('global_component_delta_identity_residual_kg')).max())}]
  write_csv(out/INDEX,index);write_csv(out/METRICS,metrics);write_csv(out/DELTA,dm);write_csv(out/PROJ,ps)
  summary={'milestone':M,'status':PASS,'classification':'READ_ONLY_INTEGRATED_DAY30_DAY45_PRESSURE_PLUME_POLLOCK_TOF_CONTROLLER_AND_CARTESIAN_PROJECTION_VISUALIZATION_COMPLETE','source_R4_R3_commit':PARENT,'checkpoint_days':[30.0,35.0,40.0,45.0],'saturation_3D_frame_count':4,'pressure_3D_frame_count':4,'pressure_layer_map_count':4,'Pollock_TOF_3D_frame_count':4,'plume_streamline_overlay_count':4,'TOF_histogram_count':4,'delta_pressure_count':4,'delta_saturation_3D_count':4,'contact_sheet_count':6,'animation_count':2,'projection_event_count':len(pr),'accepted_transition_count':int(s['accepted_transport_transition_count']),'cadence_refresh_count':int(s['cadence_refresh_count']),'capacity_triggered_refresh_count':int(s['capacity_triggered_refresh_count']),'final_cumulative_component_mass_residual_kg':float(s['final_cumulative_component_mass_residual_kg']),'Day30_to45_added_injected_CO2_mass_kg':float(s['Day30_to45_added_injected_CO2_mass_kg']),'visualization_filter_Sg':SAT_FILTER,'visualization_filter_abs_delta_Sg':DELTA_S_FILTER,'visualization_filters_are_display_only':True,'shared_pressure_normalization':True,'shared_saturation_normalization':True,'shared_TOF_normalization':True,'physics_execution_performed':False,'state_mutation_performed':False,'canonical_state_mutated':False,'production_pressure_refresh_cadence_selected':False,'longer_horizon_validation_authorized':False,'P4_authorized':False}
  (out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8');write_csv(out/MANIFEST,[{'file':p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.iterdir()) if p.is_file() and p.name!=MANIFEST]);print(M,'PASS');print('Figures / animations:',len(index));print('Projection events:',len(pr));print('Physics/state mutation: NONE/NONE');return 0
 except Exception as exc:
  blocked.mkdir(parents=True,exist_ok=True);(blocked/f'{OUT_TOKEN}_Blocked_Report.json').write_text(json.dumps({'milestone':M,'status':BLOCK,'failed_stage':stage,'exception':repr(exc),'gates':gates,'physics_execution_performed':False,'state_mutation_performed':False,'P4_authorized':False},indent=2,sort_keys=True)+'\n',encoding='utf-8');print(M,'BLOCK');print('Stage:',stage);print('Exception:',repr(exc));return 2

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--project-root',type=Path,default=Path('.'));ap.add_argument('--drive-root',type=Path,default=Path('/content/drive/MyDrive/PAD_Stream_Compute'));ap.add_argument('--self-test',action='store_true');a=ap.parse_args()
 if a.self_test:selftest(a.project_root.resolve());raise SystemExit(0)
 raise SystemExit(main(a.project_root,a.drive_root))
