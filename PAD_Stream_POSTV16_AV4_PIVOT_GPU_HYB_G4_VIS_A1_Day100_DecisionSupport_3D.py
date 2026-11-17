#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,json,subprocess
from pathlib import Path
from typing import Any
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors
from PIL import Image,ImageDraw

M="POSTV16-AV4-PIVOT-GPU-HYB-G4-VIS-A1"
PASS="POSTV16AV4PIVOTGPUHYBG4VISA1_DAY100_DECISION_SUPPORT_3D_VISUALIZATION_PASS_NO_PHYSICS_MUTATION"
BLOCK="POSTV16AV4PIVOTGPUHYBG4VISA1_TECHNICAL_OR_AUTHORITY_BLOCK_NO_PHYSICS_MUTATION"
BRANCH="postv16-av4-pivot"
PARENT="3c5233b135ceb61f2b5a6c1c9c1c6d43e634a793"
RID="PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE=Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"
A8_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_A8"
A8_REL=BASE/(A8_TOKEN+"_Day100_Production_Trajectory_Validation")
A8_SUMMARY=f"PAD_Stream_{A8_TOKEN}_Summary.json"
A8_MANIFEST=f"{A8_TOKEN}_Artifact_Manifest.csv"
A8_SNAPS=f"{A8_TOKEN}_Refresh_Snapshots.npz"
A8_STATUS="POSTV16AV4PIVOTGPUHYBG4A8_DAY100_PRODUCTION_TRAJECTORY_VALIDATION_COMPLETE"
A9_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_A9_R1"
A9_REL=BASE/(A9_TOKEN+"_Historical_A8_Benchmark_Repair")
A9_SUMMARY=f"PAD_Stream_{A9_TOKEN}_Summary.json"
A9_MANIFEST=f"{A9_TOKEN}_Artifact_Manifest.csv"
A9_STATUS="POSTV16AV4PIVOTGPUHYBG4A9R1_HISTORICAL_A8_BENCHMARK_REPAIR_PASS"
GRID=(15,50,50);NZ,NY,NX=GRID
DX_FT=20.0;DY_FT=20.0;DZ_FT=4.0;LX_FT=1000.0;LY_FT=1000.0;LZ_FT=60.0
VERTICAL_EXAGGERATION=5.0;BACKGROUND=0.20;MAX_SAT=0.80
SAT_FILTER=0.25;DELTA_FILTER=0.02;MID_K=7;SLICE_K=(2,5,7,9,12)
INJ=(24,24);PRODS=((4,4),(45,4),(4,45),(45,45));COMPK=tuple(range(5,10))
OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_VIS_A1"
OUT_REL=BASE/(OUT_TOKEN+"_Day100_DecisionSupport_3D")
BLOCK_REL=BASE/(OUT_TOKEN+"_BLOCKED")
SUMMARY=f"PAD_Stream_{OUT_TOKEN}_Summary.json";INDEX=f"{OUT_TOKEN}_Visualization_Index.csv";METRICS=f"{OUT_TOKEN}_Metrics.csv";MANIFEST=f"{OUT_TOKEN}_Artifact_Manifest.csv"
class GateError(RuntimeError):pass

def sha(p:Path):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''):h.update(c)
 return h.hexdigest()
def gt(root:Path,*a):return subprocess.check_output(['git','-C',str(root),*a],text=True).strip()
def js(p:Path):return json.loads(p.read_text())
def rows(p:Path):
 with p.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def write_csv(p,rs):
 fs=[]
 for r in rs:
  for k in r:
   if k not in fs:fs.append(k)
 with p.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fs,lineterminator='\n');w.writeheader();w.writerows(rs)
def verify_manifest(d:Path,name:str):
 m={}
 for r in rows(d/name):
  p=d/r['file']
  if not p.is_file() or sha(p)!=r['sha256'] or p.stat().st_size!=int(r['bytes']):raise GateError('manifest:'+r['file'])
  m[p.name]=r['sha256']
 if not m:raise GateError('empty_manifest')
 return m

def centers_edges():
 xc=(np.arange(NX)+.5)*DX_FT;yc=(np.arange(NY)+.5)*DY_FT;zc=(np.arange(NZ)+.5)*DZ_FT
 xe=np.arange(NX+1)*DX_FT;ye=np.arange(NY+1)*DY_FT;ze=np.arange(NZ+1)*DZ_FT
 return xc,yc,zc,xe,ye,ze

def wells3d(ax,labels=False):
 z0=(min(COMPK)+.5)*DZ_FT;z1=(max(COMPK)+.5)*DZ_FT
 xi=(INJ[0]+.5)*DX_FT;yi=(INJ[1]+.5)*DY_FT
 ax.plot([xi,xi],[yi,yi],[z0,z1],lw=3,color='black',label='Injector' if labels else None)
 first=True
 for i,j in PRODS:
  x=(i+.5)*DX_FT;y=(j+.5)*DY_FT
  ax.plot([x,x],[y,y],[z0,z1],lw=2,color='dimgray',label='Producers' if labels and first else None);first=False

def wellsmap(ax):
 xi=(INJ[0]+.5)*DX_FT;yi=(INJ[1]+.5)*DY_FT
 ax.scatter([xi],[yi],marker='*',s=120,c='black',label='Injector',zorder=20);first=True
 for i,j in PRODS:
  x=(i+.5)*DX_FT;y=(j+.5)*DY_FT
  ax.scatter([x],[y],marker='s',s=45,facecolors='white',edgecolors='black',label='Producers' if first else None,zorder=20);first=False

def fmt3d(ax,title):
 ax.set_title(title,fontsize=11,pad=12);ax.set_xlabel('X (ft)');ax.set_ylabel('Y (ft)');ax.set_zlabel('Z (ft)')
 ax.set_xlim(0,LX_FT);ax.set_ylim(0,LY_FT);ax.set_zlim(0,LZ_FT);ax.view_init(elev=24,azim=-58);ax.set_box_aspect((1,1,(LZ_FT/LX_FT)*VERTICAL_EXAGGERATION))
def tag(d):return f'D{d:09.4f}'.replace('.','p')
def save(fig,out,name,index,kind,day='',authority='A8_MIXED'):
 p=out/name;fig.savefig(p,dpi=200,bbox_inches='tight');plt.close(fig);index.append({'file':p.name,'sha256':sha(p),'bytes':p.stat().st_size,'kind':kind,'day':day,'authority':authority});return p

def sat3d(sat,day,out,index,title='Mixed',exact=False):
 _,_,_,xe,ye,ze=centers_edges();filled=sat.transpose(2,1,0)>=SAT_FILTER;xyz=sat.transpose(2,1,0);X,Y,Z=np.meshgrid(xe,ye,ze,indexing='ij')
 norm=colors.Normalize(BACKGROUND,MAX_SAT);cmap=plt.get_cmap('turbo');fc=cmap(norm(xyz));fc[...,3]=np.where(filled,.72,0)
 fig=plt.figure(figsize=(10.5,8.2));ax=fig.add_subplot(111,projection='3d');ax.voxels(X,Y,Z,filled,facecolors=fc,edgecolor=(0,0,0,.05),linewidth=.08,shade=False);wells3d(ax,True);fmt3d(ax,f'{title} Day {day:.3f}: CO2 saturation (Sg >= {SAT_FILTER:.2f}) - 5x vertical exaggeration')
 sm=plt.cm.ScalarMappable(norm=norm,cmap=cmap);sm.set_array([]);fig.colorbar(sm,ax=ax,pad=.08,shrink=.72,label='Gas saturation');ax.legend(loc='upper left',fontsize=8)
 return save(fig,out,f'{tag(day)}_{"Exact" if exact else "Mixed"}_Saturation_Geocellular_3D.png',index,'SATURATION_3D',f'{day:.12f}','A8_EXACT' if exact else 'A8_MIXED')

def pressure3d(p,day,out,index,pmin,pmax,title='Mixed',exact=False):
 xc,yc,_,_,_,_=centers_edges();XX,YY=np.meshgrid(xc,yc,indexing='xy');norm=colors.Normalize(pmin,pmax);cmap=plt.get_cmap('viridis')
 fig=plt.figure(figsize=(10.5,8.2));ax=fig.add_subplot(111,projection='3d')
 for k in SLICE_K:
  data=p[k];ZZ=np.full_like(XX,(k+.5)*DZ_FT);ax.plot_surface(XX,YY,ZZ,facecolors=cmap(norm(data)),shade=False,linewidth=0,antialiased=False,alpha=.72)
 wells3d(ax,True);fmt3d(ax,f'{title} Day {day:.3f}: pressure stacked slices - 5x vertical exaggeration');sm=plt.cm.ScalarMappable(norm=norm,cmap=cmap);sm.set_array([]);fig.colorbar(sm,ax=ax,pad=.08,shrink=.72,label='Pressure (psi)');ax.legend(loc='upper left',fontsize=8)
 return save(fig,out,f'{tag(day)}_{"Exact" if exact else "Mixed"}_Pressure_StackedSlices_3D.png',index,'PRESSURE_3D',f'{day:.12f}','A8_EXACT' if exact else 'A8_MIXED')

def player(p,day,out,index,pmin,pmax,title='Mixed',exact=False):
 xc,yc,_,xe,ye,_=centers_edges();data=p[MID_K];fig,ax=plt.subplots(figsize=(8.4,7.2));pc=ax.pcolormesh(xe,ye,data,cmap='viridis',vmin=pmin,vmax=pmax,shading='flat');levels=np.linspace(pmin,pmax,9)[1:-1]
 if levels.size:
  cs=ax.contour(xc,yc,data,levels=levels,colors='black',linewidths=.35,alpha=.45);ax.clabel(cs,fontsize=6,fmt='%.0f')
 wellsmap(ax);ax.set_aspect('equal');ax.set_xlim(0,LX_FT);ax.set_ylim(0,LY_FT);ax.set_xlabel('X (ft)');ax.set_ylabel('Y (ft)');ax.set_title(f'{title} Day {day:.3f}: pressure - physical layer 8');fig.colorbar(pc,ax=ax,pad=.02,label='Pressure (psi)');ax.legend(loc='upper right',fontsize=8)
 return save(fig,out,f'{tag(day)}_{"Exact" if exact else "Mixed"}_Pressure_Layer8.png',index,'PRESSURE_LAYER8',f'{day:.12f}','A8_EXACT' if exact else 'A8_MIXED')

def satdelta(m,e,out,index):
 d=m-e;mask=np.abs(d)>=DELTA_FILTER;_,_,_,xe,ye,ze=centers_edges();X,Y,Z=np.meshgrid(xe,ye,ze,indexing='ij');dxyz=d.transpose(2,1,0);filled=mask.transpose(2,1,0);mx=max(float(np.max(np.abs(d))),DELTA_FILTER);norm=colors.TwoSlopeNorm(vmin=-mx,vcenter=0,vmax=mx);cmap=plt.get_cmap('coolwarm');fc=cmap(norm(dxyz));fc[...,3]=np.where(filled,.75,0)
 fig=plt.figure(figsize=(10.5,8.2));ax=fig.add_subplot(111,projection='3d');ax.voxels(X,Y,Z,filled,facecolors=fc,edgecolor=(0,0,0,.05),linewidth=.08,shade=False);wells3d(ax,True);fmt3d(ax,f'Day 100: Mixed - Exact saturation (|dSg| >= {DELTA_FILTER:.2f}, display only)');sm=plt.cm.ScalarMappable(norm=norm,cmap=cmap);sm.set_array([]);fig.colorbar(sm,ax=ax,pad=.08,shrink=.72,label='dSg = Mixed - Exact');ax.legend(loc='upper left',fontsize=8)
 return save(fig,out,'Day0100_MixedMinusExact_SaturationDelta_3D.png',index,'SATURATION_DELTA_3D','100.0','A8_MIXED_MINUS_EXACT')

def pdelta(m,e,out,index):
 _,_,_,xe,ye,_=centers_edges();d=(m-e)[MID_K];mx=max(float(np.max(np.abs(d))),1e-12);norm=colors.TwoSlopeNorm(vmin=-mx,vcenter=0,vmax=mx);fig,ax=plt.subplots(figsize=(8.4,7.2));pc=ax.pcolormesh(xe,ye,d,cmap='coolwarm',norm=norm,shading='flat');wellsmap(ax);ax.set_aspect('equal');ax.set_xlim(0,LX_FT);ax.set_ylim(0,LY_FT);ax.set_xlabel('X (ft)');ax.set_ylabel('Y (ft)');ax.set_title('Day 100: refreshed pressure difference - Mixed - Exact, layer 8');fig.colorbar(pc,ax=ax,pad=.02,label='dP (psi)');ax.legend(loc='upper right',fontsize=8)
 return save(fig,out,'Day0100_MixedMinusExact_PressureDelta_Layer8.png',index,'PRESSURE_DELTA_LAYER8','100.0','A8_MIXED_MINUS_EXACT')

def score(a8,a9,out,index):
 labels=['Saturation','Pressure','Flux','Stored mass','Produced mass'];vals=[100*float(a8['mixed_100d_vs_exact_saturation_relative_L2']),100*float(a8['mixed_vs_exact_100d_refreshed_pressure_relative_L2']),100*float(a8['mixed_vs_exact_100d_refreshed_flux_relative_L2']),100*float(a8['mixed_100d_stored_mass_relative_error']),100*float(a8['mixed_100d_cumulative_produced_mass_relative_error'])]
 ex=float(a9['original_A9_exact_wallclock_seconds'])/60;hy=float(a9['repaired_Hybrid_wallclock_seconds'])/60
 fig=plt.figure(figsize=(12,6.8));ax1=fig.add_axes([.08,.14,.52,.72]);y=np.arange(len(labels));bs=ax1.barh(y,vals);ax1.set_yticks(y,labels);ax1.invert_yaxis();ax1.set_xlabel('Error (%)');ax1.set_title('Day100 Hybrid vs exact')
 for b,v in zip(bs,vals):ax1.text(v+max(vals)*.015,b.get_y()+b.get_height()/2,f'{v:.2f}%',va='center',fontsize=9)
 ax2=fig.add_axes([.68,.18,.26,.62]);rb=ax2.bar(['Exact','Hybrid'],[ex,hy]);ax2.set_ylabel('Wall clock (min)');ax2.set_title('End-to-end runtime')
 for b,v in zip(rb,[ex,hy]):ax2.text(b.get_x()+b.get_width()/2,v+1,f'{v:.1f}',ha='center',fontsize=9)
 fig.suptitle(f'PAD-Stream Day100 scorecard - Hybrid wall time {hy/ex:.2f}x exact; plume support preserved',fontsize=12);fig.text(.08,.035,'A9-R1 timing is a salvaged engineering characterization; production remains locked.',fontsize=8)
 return save(fig,out,'Day0100_Performance_Accuracy_Scorecard.png',index,'SCORECARD','100.0','A8_PLUS_A9R1')

def gif(paths,labels,out):
 frames=[]
 for p,l in zip(paths,labels):
  im=Image.open(p).convert('RGB');im.thumbnail((1100,830));can=Image.new('RGB',(1100,880),'white');can.paste(im,((1100-im.width)//2,35+(800-im.height)//2));ImageDraw.Draw(can).text((20,10),l,fill='black');frames.append(can)
 frames[0].save(out,save_all=True,append_images=frames[1:],duration=900,loop=0,optimize=False)

def contact(paths,labels,out):
 sheet=Image.new('RGB',(1400,1140),'white')
 for idx,(p,l) in enumerate(zip(paths,labels)):
  im=Image.open(p).convert('RGB');im.thumbnail((680,520));tile=Image.new('RGB',(700,570),'white');tile.paste(im,((700-im.width)//2,35+(510-im.height)//2));ImageDraw.Draw(tile).text((15,10),l,fill='black');sheet.paste(tile,((idx%2)*700,(idx//2)*570))
 sheet.save(out)

def selftest():
 assert GRID==(15,50,50) and SAT_FILTER==.25 and DELTA_FILTER==.02 and VERTICAL_EXAGGERATION==5
 print('POSTV16 GPU-HYB-G4-VIS-A1 structural self-test: PASS')

def main(project_root:Path,drive_root:Path):
 root=project_root.resolve();drive=drive_root.resolve();out=drive/OUT_REL;blocked=drive/BLOCK_REL;gates=[];stage='preflight'
 def gate(n,c,d=None):
  ok=bool(c);gates.append({'stage':stage,'gate':n,'pass':ok,'detail':'' if d is None else repr(d)});print(f"[{'PASS' if ok else 'FAIL'}] {n}"+("" if d is None else f" -- {d}"),flush=True)
  if not ok:raise GateError(n)
 try:
  print('='*190);print('G4-VIS-A1 - DAY100 DECISION-SUPPORT 3D VISUALIZATION');print('READ-ONLY A8/A9-R1 POST-PROCESSING. NO PHYSICS OR STATE MUTATION.');print('='*190)
  stage='repository';gate('branch_exact',gt(root,'branch','--show-current')==BRANCH,gt(root,'branch','--show-current'));gate('parent_is_A9R1',gt(root,'rev-parse','HEAD^')==PARENT,gt(root,'rev-parse','HEAD^'));gate('repository_clean',gt(root,'status','--porcelain')=='')
  stage='A8_authority';a8d=drive/A8_REL;a8=js(a8d/A8_SUMMARY);gate('A8_status_exact',a8.get('status')==A8_STATUS,a8.get('status'));m8=verify_manifest(a8d,A8_MANIFEST);gate('A8_snapshot_manifested',A8_SNAPS in m8)
  with np.load(a8d/A8_SNAPS,allow_pickle=False) as z:
   times=np.asarray(z['refresh_time_days'],float);sat=np.asarray(z['mixed_refresh_saturation'],float);pressure=np.asarray(z['mixed_refresh_pressure_psi'],float);exact100=np.asarray(z['exact_100d_saturation'],float);exactp=np.asarray(z['exact_100d_refreshed_pressure_psi'],float)
  gate('snapshot_shapes',sat.shape[1:]==GRID and pressure.shape==sat.shape and times.shape==(sat.shape[0],),(times.shape,sat.shape));gate('final_day_100',abs(float(times[-1])-100)<1e-12,times[-1])
  mixed_file=a8['mixed_100d_observation_state_file'];gate('mixed100_manifested',mixed_file in m8,mixed_file)
  with np.load(a8d/mixed_file,allow_pickle=False) as z:mixed100=np.asarray(z['transport_saturation'],float)
  stage='A9R1_authority';a9d=drive/A9_REL;a9=js(a9d/A9_SUMMARY);gate('A9R1_status_exact',a9.get('status')==A9_STATUS,a9.get('status'));gate('visualization_authorized',a9.get('3D_decision_support_visualization_authorized') is True);gate('production_locked',a9.get('integrated_GPU_runtime_production_authorized') is False);verify_manifest(a9d,A9_MANIFEST)
  stage='render';gate('output_absent',not out.exists(),str(out));out.mkdir(parents=True);index=[];metrics=[];pmin=float(np.min(pressure));pmax=float(np.max(pressure));sps=[];pps=[]
  for n,d in enumerate(times.tolist()):
   sps.append(sat3d(sat[n],d,out,index));pps.append(pressure3d(pressure[n],d,out,index,pmin,pmax));player(pressure[n],d,out,index,pmin,pmax);metrics.append({'day':d,'visible_cell_count_Sg_ge_0p25':int(np.sum(sat[n]>=SAT_FILTER)),'saturation_max':float(np.max(sat[n])),'pressure_min_psi':float(np.min(pressure[n])),'pressure_max_psi':float(np.max(pressure[n]))})
  exacts=sat3d(exact100,100,out,index,'Exact pre-refresh',True);exactpp=pressure3d(exactp,100,out,index,pmin,pmax,'Exact refreshed',True);player(exactp,100,out,index,pmin,pmax,'Exact refreshed',True);ds=satdelta(mixed100,exact100,out,index);dp=pdelta(pressure[-1],exactp,out,index);sc=score(a8,a9,out,index)
  stage='animations';sg=out/'Mixed_Saturation_Refresh_Evolution_3D.gif';gif(sps,[f'Mixed saturation - Day {d:.3f}' for d in times],sg);index.append({'file':sg.name,'sha256':sha(sg),'bytes':sg.stat().st_size,'kind':'SATURATION_3D_GIF','day':'','authority':'A8_MIXED'});pg=out/'Mixed_Pressure_Refresh_Evolution_3D.gif';gif(pps,[f'Mixed pressure - Day {d:.3f}' for d in times],pg);index.append({'file':pg.name,'sha256':sha(pg),'bytes':pg.stat().st_size,'kind':'PRESSURE_3D_GIF','day':'','authority':'A8_MIXED'});ct=out/'Day0100_DecisionSupport_ContactSheet.png';contact([sps[-1],exacts,ds,sc],['Mixed Day100 plume','Exact Day100 plume','Mixed - Exact saturation','Performance + accuracy'],ct);index.append({'file':ct.name,'sha256':sha(ct),'bytes':ct.stat().st_size,'kind':'CONTACT_SHEET','day':'100.0','authority':'A8_PLUS_A9R1'})
  stage='publication';write_csv(out/INDEX,index);write_csv(out/METRICS,metrics);summary={'milestone':M,'status':PASS,'classification':'READ_ONLY_INDUSTRY_STYLE_DAY100_INTEGRATED_PAD_STREAM_DECISION_SUPPORT_3D_VISUALIZATION_COMPLETE','refresh_snapshot_count':int(len(times)),'refresh_days':[float(x) for x in times],'saturation_3D_frame_count':len(sps),'pressure_3D_frame_count':len(pps),'Day100_exact_plume_visual_created':True,'Day100_saturation_delta_3D_created':True,'Day100_pressure_delta_layer8_created':True,'performance_accuracy_scorecard_created':True,'saturation_animation_created':True,'pressure_animation_created':True,'visualization_filter_Sg':SAT_FILTER,'visualization_filter_abs_delta_Sg':DELTA_FILTER,'visualization_filters_are_not_scientific_thresholds':True,'vertical_exaggeration':VERTICAL_EXAGGERATION,'A8_Day100_saturation_relative_L2':float(a8['mixed_100d_vs_exact_saturation_relative_L2']),'A8_Day100_refreshed_pressure_relative_L2':float(a8['mixed_vs_exact_100d_refreshed_pressure_relative_L2']),'A8_Day100_refreshed_flux_relative_L2':float(a8['mixed_vs_exact_100d_refreshed_flux_relative_L2']),'A9R1_exact_wallclock_seconds':float(a9['original_A9_exact_wallclock_seconds']),'A9R1_Hybrid_wallclock_seconds':float(a9['repaired_Hybrid_wallclock_seconds']),'A9R1_exact_over_Hybrid_speedup':float(a9['exact_over_Hybrid_speedup']),'production_authorization_changed':False,'physics_mutation_performed':False,'state_mutation_performed':False,'cadence_optimization_next_main_spine_authorized':True,'P4_authorized':False};(out/SUMMARY).write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n');write_csv(out/MANIFEST,[{'file':p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.iterdir()) if p.is_file() and p.name!=MANIFEST]);print(M,'PASS');print('Refresh snapshots:',len(times));print('Cadence optimization next: AUTHORIZED');return 0
 except Exception as exc:
  blocked.mkdir(parents=True,exist_ok=True);(blocked/f'{OUT_TOKEN}_Blocked_Report.json').write_text(json.dumps({'milestone':M,'status':BLOCK,'failed_stage':stage,'exception':repr(exc),'gates':gates,'physics_mutation_performed':False,'state_mutation_performed':False,'P4_authorized':False},indent=2,sort_keys=True)+'\n');print(M,'BLOCK');print('Stage:',stage);print('Exception:',repr(exc));return 2

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--project-root',type=Path,default=Path('.'));ap.add_argument('--drive-root',type=Path,default=Path('/content/drive/MyDrive/PAD_Stream_Compute'));ap.add_argument('--self-test',action='store_true');a=ap.parse_args();
 if a.self_test:selftest();raise SystemExit(0)
 raise SystemExit(main(a.project_root,a.drive_root))
