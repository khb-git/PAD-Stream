from __future__ import annotations
from pathlib import Path
import argparse,csv,hashlib,importlib.util,io,json,subprocess
from typing import Any
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize,LogNorm

MILESTONE='POSTV16-D1'
STATUS='POSTV16_HETEROGENEITY_TO_PLUME_RESPONSE_DIAGNOSTIC_AUDIT_COMPLETED'
NEXT='POSTV16-D2 - Audit interpretation and IBDP handoff decision'
RELEASE_ID='PAD-STREAM-V16-RC1-B92D52088D01078A'
RID='PAD_STREAM_V16_RC1_B92D52088D01078A'
EXPECTED_A1_CACHE_SHA='2acbbbc8608eb771d1a6ea6909c7d37caec2ee77666a7828226e3a9e531d316e'
S_INITIAL=0.20; POROSITY=0.20
DX_FT=20.0; DY_FT=20.0; DZ_FT=4.0; FT_TO_M=0.3048; DAY=86400.0
LAYER8_K=7
SELECTED_DAYS=np.asarray([30.,100.,250.,500.,750.,1000.])
THRESHOLDS=np.asarray([0.02,0.05,0.10])

SOURCES={
'C1':('PAD_Stream_V16VIS_C1_Final_V16_Visual_Package_Integration_and_Closeout_Audit.py','d2b18f1a75fdefc1778e6350b7a16551b1a76a1b'),
'A1':('PAD_Stream_V16VIS_A1_Visual_Authority_Manifest_and_Data_Extraction.py','7ed31f0e69b63489f25a1833cdc3693f735b1233'),
'B4':('PAD_Stream_V16VIS_B4_Frozen_V16_CO2_Plume_Evolution_Visuals.py','9f80237ce626c96ff9ec2f8e74f854f1ec7c779b'),
'B3R1':('PAD_Stream_V16VIS_B3R1_SG5_to_SG6_Interface_Repair.py','4bd5675efd0fba4e67634a5f5aab881a4118a52b'),
'SG2':('PAD_Stream_V15SG2_Anisotropic_Transmissibility.py','7242012d3e758472abc3ee7f543831b92d2cf419'),
'SG3':('PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py','66a379cd97ee9120f69e7e7e949171541e4918c3'),
'SG4':('PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py','8d49f88bdf55b0da087af2bed04e69967740e695'),
'SG5':('PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py','9a0b64ea7e669904d0d9855ade1c6b052f05ecea'),
'SG6':('PAD_Stream_V15SG6_TOF_Transport_Coordinates.py','70ceda68e02894167958d753d88b4dbd694731ab'),
'SG7A':('PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py','a4dd47338e7a85f130a6a70d0a41211e38c655f8'),
'SG7D':('PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py','890088c0c0fcab415a2c7351c5079ca8ee12bf82'),
'R3R2R1':('PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py','740c6da03e73906646bf0153633187e749449f31'),
'R3R4R1':('PAD_Stream_V16E41R3R4R1_Refreshed_Flow_CFL_Alignment_Repair.py','5f8433437ce111533338ceada922f51abb2edefe')}
A1_REL=Path('visuals')/RID/'Phase_A_Authority_and_Data_Extraction'
C1_REL=Path('visuals')/RID/'Phase_C1_Final_Visual_Package_Closeout'
OUT_REL=Path('post_v16')/RID/'POSTV16_D1_Heterogeneity_to_Plume_Response_Diagnostic_Audit'
BLOCKED_REL=Path('post_v16')/RID/'POSTV16_D1_BLOCKED'
FIGS=['D01','D02','D03','D04','D05','D06','D07','D08']

class GateError(RuntimeError):pass

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def blob(p,root):return subprocess.run(['git','-C',str(root),'hash-object',str(p)],check=True,text=True,stdout=subprocess.PIPE).stdout.strip()
def jl(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def cl(p):
 with Path(p).open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def jb(x):return (json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
def cb(rows):
 if not rows:return b''
 fields=[]
 for r in rows:
  for k in r:
   if k not in fields:fields.append(k)
 s=io.StringIO(newline='');w=csv.DictWriter(s,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows);return s.getvalue().encode()
def write(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists() and path.read_bytes()!=data:raise GateError('existing_output_differs:'+str(path))
 if not path.exists():path.write_bytes(data)
def load_module(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);assert spec and spec.loader;spec.loader.exec_module(m);return m
def save(fig,out,stem):
 rows=[]
 for ext in ('png','pdf'):
  p=out/f'{stem}.{ext}'
  if p.exists():raise GateError('existing_figure:'+p.name)
  fig.savefig(p,dpi=300,bbox_inches='tight');rows.append({'file':p.name,'sha256':sha(p),'bytes':p.stat().st_size})
 plt.close(fig);return rows
def corr(a,b):
 a=np.asarray(a,float).ravel();b=np.asarray(b,float).ravel();m=np.isfinite(a)&np.isfinite(b)
 if np.count_nonzero(m)<3:return float('nan')
 a=a[m];b=b[m]
 if np.std(a)<=1e-15 or np.std(b)<=1e-15:return 0.0
 return float(np.corrcoef(a,b)[0,1])
def b4_threshold(s):
 smin=float(np.min(s));smax=float(np.max(s));span=max(smax-smin,1e-12);return min(smin+max(0.01,0.03*span),smax)
def add_wells(ax):
 ax.scatter([490],[490],marker='^',s=45,label='Injector')
 ax.scatter([90,910,90,910],[90,90,910,910],marker='v',s=38,label='Producers')
def front_metrics(mask,x,y):
 jj,ii=np.where(mask)
 if len(ii)<4:return float('nan'),float('nan'),float('nan')
 xx=x[ii]-490.;yy=y[jj]-490.;pts=np.column_stack([xx,yy]);cov=np.cov(pts,rowvar=False)
 ev=np.linalg.eigvalsh(cov);axis=float(np.sqrt(max(ev[-1],1e-12)/max(ev[0],1e-12)))
 ang=np.arctan2(yy,xx);rad=np.hypot(xx,yy);edges=np.linspace(-np.pi,np.pi,37);front=[]
 for a,b in zip(edges[:-1],edges[1:]):
  m=(ang>=a)&(ang<b)
  if np.any(m):front.append(float(np.max(rad[m])))
 radial_cv=float(np.std(front)/np.mean(front)) if len(front)>=8 and np.mean(front)>0 else float('nan')
 # grid-edge perimeter circularity
 n=mask.astype(int);per_edges=np.sum(n[:,1:]!=n[:,:-1])+np.sum(n[1:,:]!=n[:-1,:])+np.sum(n[:,0])+np.sum(n[:,-1])+np.sum(n[0,:])+np.sum(n[-1,:])
 area=float(np.count_nonzero(mask)*(DX_FT*DY_FT));per=float(per_edges*DX_FT);circ=float(4*np.pi*area/(per*per)) if per>0 else float('nan')
 return axis,radial_cv,circ

def grid_tof_from_db(db,shape):
 sumw=np.zeros(shape,float);sumwt=np.zeros(shape,float);xyz=np.asarray(db['xyz_m'],float);tau=np.asarray(db['tau_s'],float)/DAY;weights=np.asarray(db['weights_m3_s'],float)
 dx=DX_FT*FT_TO_M;dy=DY_FT*FT_TO_M;dz=DZ_FT*FT_TO_M
 for s in range(xyz.shape[0]):
  pts=xyz[s];ii=np.clip(np.floor(pts[:,0]/dx).astype(int),0,shape[2]-1);jj=np.clip(np.floor(pts[:,1]/dy).astype(int),0,shape[1]-1);kk=np.clip(np.floor(pts[:,2]/dz).astype(int),0,shape[0]-1)
  lin=(kk*shape[1]+jj)*shape[2]+ii
  for cell in np.unique(lin):
   m=lin==cell;k=int(cell//(shape[1]*shape[2]));rem=int(cell%(shape[1]*shape[2]));j=int(rem//shape[2]);i=int(rem%shape[2]);tv=float(np.min(tau[s,m]));w=float(weights[s]);sumw[k,j,i]+=w;sumwt[k,j,i]+=w*tv
 out=np.full(shape,np.nan);m=sumw>0;out[m]=sumwt[m]/sumw[m];return out,sumw

def self_test():
 if S_INITIAL!=0.20 or POROSITY!=0.20:raise RuntimeError('baseline')
 if list(SELECTED_DAYS)!=[30.,100.,250.,500.,750.,1000.]:raise RuntimeError('days')
 if len(FIGS)!=8:raise RuntimeError('figure_count')
 a=np.array([.2,.3,.8]);t=b4_threshold(a)
 if not(.2<t<.8):raise RuntimeError('threshold')
 print('PAD-Stream POSTV16-D1 heterogeneity-to-plume audit self-test: PASS')

def main(project_root:Path,drive_root:Path)->int:
 root=Path(project_root).resolve();drive=Path(drive_root).resolve();out=drive/OUT_REL;blocked=drive/BLOCKED_REL;g={};stage=None
 def gate(n,ok,d=''):
  g[n]={'passed':bool(ok),'detail':str(d)}
  if not ok:raise GateError(n)
 try:
  print('\n'+'='*164);print('PAD-Stream POSTV16-D1 — Frozen Heterogeneity-to-Plume Response Diagnostic Audit');print('='*164)
  print('Release                    :',RELEASE_ID);print('V16 mutation               : none');print('Transport rerun             : none');print('Diagnostic reconstruction   : terminal Pollock/TOF only, read-only')
  stage='source_binding'
  for role,(fn,exp) in SOURCES.items():p=root/fn;gate(role+'_exists',p.is_file(),p);act=blob(p,root);gate(role+'_blob',act==exp,act)
  stage='frozen_closeout_authority';c1=drive/C1_REL;a1=drive/A1_REL
  for p in [c1/'PAD_Stream_V16VIS_C1_Summary.json',c1/'V16VIS_C1_Final_Closure.json',a1/'PAD_Stream_V16VIS_A1_Summary.json',a1/'V16VIS_A1_Final_Closure.json',a1/'V16VIS_A1_Authoritative_Visual_Data.npz'] :gate('exists_'+p.name,p.is_file(),p)
  cs=jl(c1/'PAD_Stream_V16VIS_C1_Summary.json');cc=jl(c1/'V16VIS_C1_Final_Closure.json');asum=jl(a1/'PAD_Stream_V16VIS_A1_Summary.json');ac=jl(a1/'V16VIS_A1_Final_Closure.json')
  gate('C1_closed',cs.get('status')=='FINAL_V16_VISUAL_PACKAGE_INTEGRATED_AND_CLOSED',cs.get('status'));gate('C1_closure',cc.get('V16_visual_package_formally_closed') is True);gate('A1_closed',ac.get('all_gates_passed') is True)
  cache=a1/'V16VIS_A1_Authoritative_Visual_Data.npz';gate('cache_sha',sha(cache)==EXPECTED_A1_CACHE_SHA,sha(cache));gate('cache_summary_sha',asum.get('visual_cache_sha256')==EXPECTED_A1_CACHE_SHA)
  stage='frozen_arrays'
  with np.load(cache,allow_pickle=False) as z:
   perm=np.asarray(z['permeability_md'],float);days=np.asarray(z['plume_days'],float);sat=np.asarray(z['plume_saturation'],float);x=np.asarray(z['x_center_ft'],float);y=np.asarray(z['y_center_ft'],float);depth=np.asarray(z['depth_center_ft'],float);flow_sat=np.asarray(z['flow_saturation'],float);flow_p=np.asarray(z['flow_pressure_psi'],float);flow_days=np.asarray(z['flow_days'],float)
  gate('shape_perm',perm.shape==(15,50,50),perm.shape);gate('shape_sat',sat.shape==(9,15,50,50),sat.shape);gate('days',np.array_equal(days,np.asarray([30.,60.,100.,150.,250.,365.,500.,750.,1000.])),days);gate('baseline_supported',float(np.min(sat))>=S_INITIAL-1e-3,float(np.min(sat)))
  ds=sat-S_INITIAL;gate('delta_finite',np.all(np.isfinite(ds)));gate('delta_positive_present',float(np.max(ds))>0,float(np.max(ds)))
  old_thr=b4_threshold(sat);old_delta=old_thr-S_INITIAL;old_active=float(np.mean(sat[-1]>old_thr))
  if out.exists() and any(out.iterdir()):raise GateError('D1_output_directory_not_empty')
  out.mkdir(parents=True,exist_ok=True);rendered=[];metrics=[]
  stage='D01'
  idx=[int(np.where(np.isclose(days,d))[0][0]) for d in SELECTED_DAYS]
  fig,axes=plt.subplots(2,6,figsize=(19,7),constrained_layout=True);im1=im2=None
  for c,(d,q) in enumerate(zip(SELECTED_DAYS,idx)):
   im1=axes[0,c].imshow(sat[q,LAYER8_K],origin='lower',extent=[0,1000,0,1000],vmin=float(np.min(sat)),vmax=float(np.max(sat)));add_wells(axes[0,c]);axes[0,c].set_title(f'{d:.0f} d');
   im2=axes[1,c].imshow(ds[q,LAYER8_K],origin='lower',extent=[0,1000,0,1000],vmin=0,vmax=float(np.max(ds)));add_wells(axes[1,c]);axes[1,c].set_title(f'{d:.0f} d')
  axes[0,0].set_ylabel('Absolute S\nY, ft');axes[1,0].set_ylabel('ΔS = S - 0.20\nY, ft');fig.colorbar(im1,ax=axes[0,:].tolist(),shrink=.75,label='Frozen saturation');fig.colorbar(im2,ax=axes[1,:].tolist(),shrink=.75,label='ΔS');fig.suptitle('D01 — Absolute saturation versus plume signal above frozen baseline')
  rendered+=save(fig,out,'D01_Absolute_Saturation_vs_DeltaS_Layer08')
  stage='D02';logk=np.log10(perm[LAYER8_K]);fig,axes=plt.subplots(2,3,figsize=(14,9),constrained_layout=True)
  for ax,d,q in zip(axes.ravel(),SELECTED_DAYS,idx):
   im=ax.imshow(logk,origin='lower',extent=[0,1000,0,1000]);levels=[.02,.05,.10];csx=ax.contour(ds[q,LAYER8_K],levels=levels,origin='lower',extent=[0,1000,0,1000],linewidths=1.2);ax.clabel(csx,fmt=lambda v:f'ΔS={v:.2f}',fontsize=7);add_wells(ax);ax.set_title(f'{d:.0f} d');ax.set_xlabel('X, ft');ax.set_ylabel('Y, ft')
  fig.colorbar(im,ax=axes.ravel().tolist(),shrink=.82,label='log10 permeability (mD)');fig.suptitle('D02 — Layer-8 SGSim permeability with ΔS plume contours');rendered+=save(fig,out,'D02_Layer08_Permeability_DeltaS_Overlay')
  stage='D03';fig=plt.figure(figsize=(15,5));vmax=float(np.max(ds[-1]))
  for n,thr in enumerate(THRESHOLDS,1):
   ax=fig.add_subplot(1,3,n,projection='3d');k,j,i=np.where(ds[-1]>thr);sc=ax.scatter(x[i],y[j],depth[k],c=ds[-1,k,j,i],vmin=0,vmax=vmax,s=8,alpha=.6,linewidths=0);ax.set_xlim(0,1000);ax.set_ylim(0,1000);ax.set_zlim(60,0);ax.set_title(f'ΔS > {thr:.2f}\n{len(i):,} cells');ax.set_xlabel('X, ft');ax.set_ylabel('Y, ft');ax.set_zlabel('Depth, ft')
  fig.colorbar(sc,ax=fig.axes[:3],shrink=.7,label='ΔS');fig.suptitle(f'D03 — 1000-day 3D plume threshold sensitivity | old B4 cutoff ≈ ΔS>{old_delta:.4f}');rendered+=save(fig,out,'D03_1000d_3D_DeltaS_Threshold_Sensitivity')
  stage='metrics'
  cell_bulk_m3=DX_FT*DY_FT*DZ_FT*(FT_TO_M**3);cell_pv_m3=cell_bulk_m3*POROSITY
  volume_rows=[]
  for d,sx in zip(days,ds):
   for thr in THRESHOLDS:
    n=int(np.count_nonzero(sx>thr));volume_rows.append({'day':float(d),'deltaS_threshold':float(thr),'active_cells':n,'active_cell_fraction':n/sx.size,'represented_pore_volume_m3':n*cell_pv_m3})
  write(out/'POSTV16_D1_Thresholded_Plume_Volume.csv',cb(volume_rows))
  fig,ax=plt.subplots(figsize=(9,6))
  for thr in THRESHOLDS:
   rr=[r for r in volume_rows if r['deltaS_threshold']==float(thr)];ax.plot([r['day'] for r in rr],[100*r['active_cell_fraction'] for r in rr],marker='o',label=f'ΔS>{thr:.2f}')
  ax.set_xlabel('Time, days');ax.set_ylabel('Reservoir cells above threshold, %');ax.set_title('D04 — Thresholded plume coverage versus time');ax.grid(alpha=.25);ax.legend();rendered+=save(fig,out,'D04_Thresholded_Plume_Coverage_vs_Time')
  # quintiles
  flatk=perm.ravel();edges=np.quantile(flatk,[0,.2,.4,.6,.8,1]);qbin=np.digitize(flatk,edges[1:-1],right=True)
  qrows=[]
  for d,sx in zip(days,ds):
   fs=sx.ravel()
   for q in range(5):
    m=qbin==q;qrows.append({'day':float(d),'permeability_quintile':q+1,'K_min_md':float(np.min(flatk[m])),'K_max_md':float(np.max(flatk[m])),'mean_deltaS':float(np.mean(fs[m])),'median_deltaS':float(np.median(fs[m]))})
  write(out/'POSTV16_D1_Permeability_Quintile_Response.csv',cb(qrows));fig,ax=plt.subplots(figsize=(9,6))
  for q in range(1,6):
   rr=[r for r in qrows if r['permeability_quintile']==q];ax.plot([r['day'] for r in rr],[r['mean_deltaS'] for r in rr],marker='o',label=f'K quintile {q}')
  ax.set_xlabel('Time, days');ax.set_ylabel('Mean ΔS');ax.set_title('D05 — Mean plume response by SGSim permeability quintile');ax.grid(alpha=.25);ax.legend(ncol=2);rendered+=save(fig,out,'D05_DeltaS_by_Permeability_Quintile')
  # correlations
  corr_rows=[];sel=[30.,100.,250.,1000.];fig,axes=plt.subplots(2,2,figsize=(11,9),constrained_layout=True);lk=np.log10(flatk)
  sample_idx=np.linspace(0,len(lk)-1,min(6000,len(lk))).astype(int)
  for ax,d in zip(axes.ravel(),sel):
   q=int(np.where(np.isclose(days,d))[0][0]);fv=ds[q].ravel();c_all=corr(lk,fv);m=fv>.01;c_active=corr(lk[m],fv[m]);corr_rows.append({'day':d,'pearson_log10K_deltaS_all_cells':c_all,'pearson_log10K_deltaS_deltaS_gt_0p01':c_active,'active_cells_deltaS_gt_0p01':int(np.count_nonzero(m))});ax.scatter(lk[sample_idx],fv[sample_idx],s=3,alpha=.18);ax.set_title(f'{d:.0f} d | r(all)={c_all:.3f}');ax.set_xlabel('log10 K (mD)');ax.set_ylabel('ΔS')
  fig.suptitle('D06 — Direct cellwise permeability–plume relationship');rendered+=save(fig,out,'D06_logK_vs_DeltaS_Correlation');write(out/'POSTV16_D1_Permeability_DeltaS_Correlations.csv',cb(corr_rows))
  # terminal TOF reconstruction exactly as B3R1
  stage='D07_terminal_tof_reconstruction';sg2=load_module(root/SOURCES['SG2'][0],'d1_sg2');sg3=load_module(root/SOURCES['SG3'][0],'d1_sg3');sg4=load_module(root/SOURCES['SG4'][0],'d1_sg4');sg5=load_module(root/SOURCES['SG5'][0],'d1_sg5');sg6=load_module(root/SOURCES['SG6'][0],'d1_sg6');r3=load_module(root/SOURCES['R3R2R1'][0],'d1_r3');r34=load_module(root/SOURCES['R3R4R1'][0],'d1_r34')
  term_sat=flow_sat[-1];term_p=flow_p[-1];kx,ky,kz=sg2.build_directional_permeability(perm);kfx,kfy,kfz=sg2.build_face_permeabilities(kx,ky,kz);tx0,ty0,tz0=sg3.construct_si_transmissibilities(kfx,kfy,kfz);mob=r3.phase_mobility_fields(term_sat);tx,ty,tz,_=r3.build_updated_transmissibilities(sg3,tx0,ty0,tz0,mob['lambda_total']);qx,qy,qz=sg4.compute_face_fluxes(term_p,tx,ty,tz);vx,vy,vz=sg5.construct_face_pore_velocities(qx,qy,qz);faces,seeds=sg5.build_seeds(qx,qy,qz);sl=sg5.trace_streamlines(seeds,vx,vy,vz);cap=[s for s in sl if s['status']=='PRODUCER'];gate('tof_all_captured',len(cap)==len(sl),(len(cap),len(sl)));conv=r34.convert_sg5_to_sg6_streamlines(sl);db=sg6.build_transport_database(conv);sg6.validate_transport(db);gridtof,tofw=grid_tof_from_db(db,perm.shape);visited=np.isfinite(gridtof);gate('tof_visited',np.count_nonzero(visited)>0,np.count_nonzero(visited));tof_corr=corr(np.log10(gridtof[visited]),ds[-1][visited])
  tof_rows=[{'visited_cells':int(np.count_nonzero(visited)),'visited_fraction':float(np.mean(visited)),'pearson_log10TOF_deltaS_visited':tof_corr,'terminal_tof_min_days':float(np.nanmin(gridtof)),'terminal_tof_max_days':float(np.nanmax(gridtof)),'streamline_count':len(sl)}];write(out/'POSTV16_D1_TOF_DeltaS_Response.csv',cb(tof_rows))
  fig,axes=plt.subplots(1,3,figsize=(15,4.8),constrained_layout=True);im=axes[0].imshow(gridtof[LAYER8_K],origin='lower',extent=[0,1000,0,1000]);axes[0].set_title('Layer 8 flux-weighted arrival TOF');fig.colorbar(im,ax=axes[0],label='TOF, days');im2=axes[1].imshow(ds[-1,LAYER8_K],origin='lower',extent=[0,1000,0,1000],vmin=0,vmax=float(np.max(ds)));axes[1].set_title('Layer 8 ΔS at 1000 d');fig.colorbar(im2,ax=axes[1],label='ΔS');m=np.isfinite(gridtof[LAYER8_K]);axes[2].scatter(gridtof[LAYER8_K][m],ds[-1,LAYER8_K][m],s=7,alpha=.35);axes[2].set_xscale('log');axes[2].set_xlabel('TOF, days');axes[2].set_ylabel('ΔS');axes[2].set_title(f'TOF vs ΔS | r(log TOF)={corr(np.log10(gridtof[LAYER8_K][m]),ds[-1,LAYER8_K][m]):.3f}');fig.suptitle('D07 — Does frozen flow heterogeneity appear more clearly in TOF than saturation?');rendered+=save(fig,out,'D07_TOF_vs_DeltaS_Response')
  # front metrics
  stage='D08';frows=[]
  for d,sx in zip(days,ds):
   for thr in [.05,.10]:
    axis,rcv,circ=front_metrics(sx[LAYER8_K]>thr,x,y);frows.append({'day':float(d),'deltaS_threshold':thr,'active_cells_layer8':int(np.count_nonzero(sx[LAYER8_K]>thr)),'principal_axis_ratio':axis,'radial_front_cv':rcv,'grid_circularity':circ})
  write(out/'POSTV16_D1_Front_Geometry_Metrics.csv',cb(frows));fig,axes=plt.subplots(1,2,figsize=(12,5),constrained_layout=True)
  for thr in [.05,.10]:
   rr=[r for r in frows if r['deltaS_threshold']==thr];axes[0].plot([r['day'] for r in rr],[r['principal_axis_ratio'] for r in rr],marker='o',label=f'ΔS>{thr:.2f}');axes[1].plot([r['day'] for r in rr],[r['radial_front_cv'] for r in rr],marker='o',label=f'ΔS>{thr:.2f}')
  axes[0].set_title('Principal-axis ratio');axes[0].set_ylabel('Major/minor spread ratio');axes[1].set_title('Radial front roughness');axes[1].set_ylabel('Front-radius coefficient of variation')
  for ax in axes:ax.set_xlabel('Time, days');ax.grid(alpha=.25);ax.legend()
  fig.suptitle('D08 — Layer-8 plume front anisotropy / roughness versus time');rendered+=save(fig,out,'D08_Front_Geometry_Anisotropy_vs_Time')
  gate('rendered_count',len(rendered)==16,len(rendered));gate('rendered_nonempty',all(r['bytes']>0 for r in rendered))
  # outcome evidence, no physical pass/fail threshold imposed
  term_q=[r for r in qrows if r['day']==1000.];qspread=float(term_q[-1]['mean_deltaS']-term_q[0]['mean_deltaS'])
  summary={'milestone':MILESTONE,'status':STATUS,'release_id':RELEASE_ID,'V16_frozen':True,'C1_visual_package_closed':True,'simulation_executed':False,'transport_rerun':False,'accepted_state_mutation':False,'initial_saturation':S_INITIAL,'porosity':POROSITY,'B4_absolute_saturation_threshold':old_thr,'B4_equivalent_deltaS_threshold':old_delta,'terminal_fraction_cells_above_B4_threshold':old_active,'terminal_highK_minus_lowK_mean_deltaS':qspread,'terminal_pearson_log10TOF_deltaS_visited':tof_corr,'diagnostic_figure_families':FIGS,'rendered_png_pdf_files':16,'next':NEXT}
  contract={'purpose':'Read-only post-freeze audit of whether SGSim heterogeneity is expressed in frozen V16 plume response and whether B4 rectangular appearance is threshold-driven.','frozen_inputs':['A1 permeability_md','A1 nine pre-refresh plume_saturation states','A1 terminal post-refresh pressure/saturation for authorized read-only TOF reconstruction'],'baseline_definition':'deltaS = frozen transport saturation - 0.20','no_V16_mutation':True,'no_training':True,'no_calibration':True,'no_transport_rerun':True,'no_release_replacement':True,'TOF_reconstruction':'same frozen terminal-flow + exact SG5 Pollock + SG6 coordinate path used by B3R1','interpretation_rule':'Metrics are diagnostic evidence only; no predeclared physical-response threshold is used to alter V16.'}
  captions=[{'figure_id':'D01','caption':'Absolute saturation compared directly with deltaS above the exact frozen initial saturation 0.20.'},{'figure_id':'D02','caption':'Layer-8 SGSim log-permeability with deltaS plume contours to expose preferential advancement.'},{'figure_id':'D03','caption':'1000-day 3D plume sensitivity to deltaS thresholds 0.02, 0.05, and 0.10, contrasted with the old B4 threshold.'},{'figure_id':'D04','caption':'Fraction of reservoir cells exceeding each deltaS threshold through the nine frozen observations.'},{'figure_id':'D05','caption':'Mean deltaS through time for five frozen SGSim permeability quintiles.'},{'figure_id':'D06','caption':'Cellwise log10 permeability versus deltaS at selected observation times, with full-grid correlations.'},{'figure_id':'D07','caption':'Read-only reconstructed terminal TOF compared with terminal deltaS to test whether heterogeneity is more evident in flow coordinates than saturation.'},{'figure_id':'D08','caption':'Layer-8 thresholded plume principal-axis ratio and radial-front roughness through time.'}]
  idx=[]
  stems=['D01_Absolute_Saturation_vs_DeltaS_Layer08','D02_Layer08_Permeability_DeltaS_Overlay','D03_1000d_3D_DeltaS_Threshold_Sensitivity','D04_Thresholded_Plume_Coverage_vs_Time','D05_DeltaS_by_Permeability_Quintile','D06_logK_vs_DeltaS_Correlation','D07_TOF_vs_DeltaS_Response','D08_Front_Geometry_Anisotropy_vs_Time']
  for fid,stem in zip(FIGS,stems):idx.append({'figure_id':fid,'stem':stem,'files':f'{stem}.png;{stem}.pdf','authority':'DERIVED_READ_ONLY_FROM_FROZEN_V16','release_id':RELEASE_ID})
  closure={'milestone':MILESTONE,'status':STATUS,'all_gates_passed':all(v['passed'] for v in g.values()),'gate_count':len(g),'read_only_frozen_arrays_used':True,'terminal_TOF_reconstruction_authorized_by_A1_contract':True,'accepted_simulation_state_modified':False,'V16_release_modified':False,'diagnostic_audit_complete':True,'next':NEXT}
  write(out/'POSTV16_D1_Figure_Index.csv',cb(idx));write(out/'POSTV16_D1_Figure_Captions.csv',cb(captions));write(out/'POSTV16_D1_Diagnostic_Contract.json',jb(contract));write(out/'PAD_Stream_POSTV16_D1_Summary.json',jb(summary));write(out/'POSTV16_D1_Final_Gate_Matrix.csv',cb([{'gate':k,**v} for k,v in g.items()]));write(out/'POSTV16_D1_Final_Closure.json',jb(closure))
  man=[]
  for p in sorted(out.iterdir()):
   if p.is_file() and p.name!='POSTV16_D1_Artifact_Manifest.csv':man.append({'file':p.name,'sha256':sha(p),'bytes':p.stat().st_size})
  write(out/'POSTV16_D1_Artifact_Manifest.csv',cb(man))
  print('\n'+'='*164);print('PAD-Stream POSTV16-D1: PASS');print('='*164);print(f"{'Status':72}: {STATUS}");print(f"{'B4 absolute display threshold':72}: {old_thr:.12f}");print(f"{'Equivalent deltaS threshold':72}: {old_delta:.12f}");print(f"{'1000d cells above old B4 threshold':72}: {100*old_active:.3f}%");print(f"{'1000d high-K minus low-K mean deltaS':72}: {qspread:.12f}");print(f"{'Terminal Pearson r(log10 TOF, deltaS), visited cells':72}: {tof_corr:.6f}");print(f"{'Diagnostic figures':72}: D01-D08 (16 PNG/PDF files)");print(f"{'Accepted simulation state modified':72}: False");print(f"{'V16 release modified':72}: False");print(f"{'Next':72}: {NEXT}");return 0
 except Exception as e:
  blocked.mkdir(parents=True,exist_ok=True);data=jb({'milestone':MILESTONE,'status':'POSTV16_HETEROGENEITY_PLUME_RESPONSE_DIAGNOSTIC_AUDIT_BLOCKED','failed_stage':stage,'exception':repr(e),'gates':g});p=blocked/'POSTV16_D1_Blocked_Report.json';p.write_bytes(data);print('\n'+'='*164);print('PAD-Stream POSTV16-D1: BLOCKED');print('='*164);print('Report:',p);print('Stage:',stage);print('Exception:',repr(e));return 2

def parse_args():
 p=argparse.ArgumentParser();p.add_argument('--project-root',type=Path,default=Path('.'));p.add_argument('--drive-root',type=Path,default=Path('/content/drive/MyDrive/PAD_Stream_Compute'));p.add_argument('--self-test',action='store_true');return p.parse_args()
if __name__=='__main__':
 a=parse_args()
 if a.self_test:self_test();raise SystemExit(0)
 raise SystemExit(main(a.project_root,a.drive_root))
