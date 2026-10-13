from __future__ import annotations
from pathlib import Path
import argparse,csv,hashlib,io,json,subprocess
from typing import Any

MILESTONE='V16VIS-C1'
STATUS='FINAL_V16_VISUAL_PACKAGE_INTEGRATED_AND_CLOSED'
NEXT='Post-V16 handoff - IBDP development may begin under a new versioned scope'
RELEASE_ID='PAD-STREAM-V16-RC1-B92D52088D01078A'
RID='PAD_STREAM_V16_RC1_B92D52088D01078A'
EXPECTED_IDS=['G01','G02','G03','G04','G05','F01','F02','F03','F04','F05','S01','S02','S03','S04','T01','T02','T03','P01','P02','P03','P04','P05','R01','R02','R03','R04','A01','A02','A03','A04','A05']
EXPECTED_VARIANTS=45; EXPECTED_FILES=90; EXPECTED_CAPTIONS=31
SOURCES={
'A1':('PAD_Stream_V16VIS_A1_Visual_Authority_Manifest_and_Data_Extraction.py','7ed31f0e69b63489f25a1833cdc3693f735b1233'),
'B1':('PAD_Stream_V16VIS_B1_Frozen_SGSim_Geology_and_Reservoir_Geometry_Visuals.py','5d8c785e189683c9b46f85b51a94297016c21af5'),
'B2':('PAD_Stream_V16VIS_B2_Frozen_V16_Pressure_and_Darcy_Flow_Visuals.py','414fd135a137bb3ad9df75cb1d22bb41e559e05d'),
'B3_FAILED':('PAD_Stream_V16VIS_B3_Frozen_V16_Pollock_Streamline_and_TOF_Visuals.py','b43201c73946665deafd8360add67a501ebe60ff'),
'B3R1':('PAD_Stream_V16VIS_B3R1_SG5_to_SG6_Interface_Repair.py','4bd5675efd0fba4e67634a5f5aab881a4118a52b'),
'B4':('PAD_Stream_V16VIS_B4_Frozen_V16_CO2_Plume_Evolution_Visuals.py','9f80237ce626c96ff9ec2f8e74f854f1ec7c779b'),
'B5':('PAD_Stream_V16VIS_B5_Frozen_V16_Runtime_and_Mass_Balance_Visuals.py','cfda1357973d9ae00214835e634e05258c49cab2'),
'B6':('PAD_Stream_V16VIS_B6_Frozen_V16_Architecture_and_Release_Visuals.py','2388402855aa53f982a121b8f9140ca40388a49c'),
'E49':('PAD_Stream_V16E49_Final_V16_Freeze_and_Release_Candidate_Assembly.py','15c7f9c749ba41f62f42003a3a12defcda7451d7')}
VIS=Path('visuals')/RID
A1=VIS/'Phase_A_Authority_and_Data_Extraction'
E49=Path('provenance/hybrid_dp/V16E49_FINAL_V16_FREEZE_AND_RELEASE_CANDIDATE')
OUT=VIS/'Phase_C1_Final_Visual_Package_Closeout'; BLOCKED=VIS/'Phase_C1_BLOCKED'
PHASES={
'B1':(VIS/'Phase_B1_Geology_and_Reservoir_Geometry','PAD_Stream_V16VIS_B1_Summary.json','V16VIS_B1_Final_Closure.json','V16VIS_B1_Artifact_Manifest.csv','V16VIS_B1_Figure_Index.csv','V16VIS_B1_Figure_Captions.csv','FROZEN_SGSIM_GEOLOGY_AND_RESERVOIR_GEOMETRY_VISUALS_VALIDATED',['G01','G02','G03','G04','G05'],10,20),
'B2':(VIS/'Phase_B2_Pressure_and_Darcy_Flow','PAD_Stream_V16VIS_B2_Summary.json','V16VIS_B2_Final_Closure.json','V16VIS_B2_Artifact_Manifest.csv','V16VIS_B2_Figure_Index.csv','V16VIS_B2_Figure_Captions.csv','FROZEN_V16_PRESSURE_AND_DARCY_FLOW_VISUALS_VALIDATED',['F01','F02','F03','F04','F05'],6,12),
'B3R1':(VIS/'Phase_B3R1_Pollock_Streamline_and_TOF_Interface_Repair','PAD_Stream_V16VIS_B3R1_Summary.json','V16VIS_B3R1_Final_Closure.json','V16VIS_B3R1_Artifact_Manifest.csv','V16VIS_B3R1_Figure_Index.csv','V16VIS_B3R1_Figure_Captions.csv','FROZEN_V16_POLLOCK_STREAMLINE_AND_TOF_VISUALS_VALIDATED_R1',['S01','S02','S03','S04','T01','T02','T03'],7,14),
'B4':(VIS/'Phase_B4_CO2_Plume_Evolution','PAD_Stream_V16VIS_B4_Summary.json','V16VIS_B4_Final_Closure.json','V16VIS_B4_Artifact_Manifest.csv','V16VIS_B4_Figure_Index.csv','V16VIS_B4_Figure_Captions.csv','FROZEN_V16_CO2_PLUME_EVOLUTION_VISUALS_VALIDATED',['P01','P02','P03','P04','P05'],13,26),
'B5':(VIS/'Phase_B5_Runtime_and_Mass_Balance','PAD_Stream_V16VIS_B5_Summary.json','V16VIS_B5_Final_Closure.json','V16VIS_B5_Artifact_Manifest.csv','V16VIS_B5_Figure_Index.csv','V16VIS_B5_Figure_Captions.csv','FROZEN_V16_RUNTIME_AND_MASS_BALANCE_VISUALS_VALIDATED',['R01','R02','R03','R04'],4,8),
'B6':(VIS/'Phase_B6_Architecture_and_Release','PAD_Stream_V16VIS_B6_Summary.json','V16VIS_B6_Final_Closure.json','V16VIS_B6_Artifact_Manifest.csv','V16VIS_B6_Figure_Index.csv','V16VIS_B6_Figure_Captions.csv','FROZEN_V16_ARCHITECTURE_AND_RELEASE_VISUALS_VALIDATED',['A01','A02','A03','A04','A05'],5,10)}
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
 fs=[]
 for r in rows:
  for k in r:
   if k not in fs:fs.append(k)
 s=io.StringIO(newline='');w=csv.DictWriter(s,fieldnames=fs,lineterminator='\n');w.writeheader();w.writerows(rows);return s.getvalue().encode()
def write(p,d):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists() and p.read_bytes()!=d:raise GateError('existing_output_differs:'+str(p))
 if not p.exists():p.write_bytes(d)
def manifest(base,name,gate):
 p=base/name;gate('manifest_exists_'+base.name,p.is_file(),p);rows=cl(p);gate('manifest_nonempty_'+base.name,len(rows)>0,len(rows));seen=set()
 for r in rows:
  n=r['file'];gate('manifest_unique_'+base.name+'_'+n,n not in seen,n);seen.add(n);q=base/n;gate('artifact_exists_'+base.name+'_'+n,q.is_file(),q);a=sha(q);gate('artifact_sha_'+base.name+'_'+n,a==r['sha256'],a);gate('artifact_size_'+base.name+'_'+n,q.stat().st_size==int(r['bytes']),q.stat().st_size)
 return rows
def splitf(x):return [z.strip() for z in str(x).split(';') if z.strip()]
def self_test():
 if RELEASE_ID!='PAD-STREAM-V16-RC1-B92D52088D01078A':raise RuntimeError('release')
 if len(EXPECTED_IDS)!=31 or len(set(EXPECTED_IDS))!=31:raise RuntimeError('ids')
 if sum(v[-2] for v in PHASES.values())!=45 or sum(v[-1] for v in PHASES.values())!=90:raise RuntimeError('totals')
 if [x for v in PHASES.values() for x in v[-3]]!=EXPECTED_IDS:raise RuntimeError('order')
 print('PAD-Stream V16VIS-C1 final visual package integration / closeout self-test: PASS')

def main(project_root:Path,drive_root:Path)->int:
 root=Path(project_root).resolve();drive=Path(drive_root).resolve();out=drive/OUT;blocked=drive/BLOCKED;g={};stage=None
 def gate(n,ok,d=''):
  g[n]={'passed':bool(ok),'detail':str(d)}
  if not ok:raise GateError(n)
 try:
  print('\n'+'='*164);print('PAD-Stream V16VIS-C1 — Final V16 Visual Package Integration and Closeout Audit');print('='*164)
  print('Release                    :',RELEASE_ID);print('Simulation                  : none');print('Accepted-state mutation     : none');print('New scientific plots        : none');print('Closeout target             : 31 IDs / 45 variants / 90 PNG-PDF files')
  stage='repository_source_binding';srows=[]
  for role,(fn,exp) in SOURCES.items():
   p=root/fn;gate(role+'_exists',p.is_file(),p);a=blob(p,root);gate(role+'_blob_exact',a==exp,a);srows.append({'role':role,'filename':fn,'expected_git_blob':exp,'actual_git_blob':a})
  stage='A1_authority';a1=drive/A1
  for n in ['PAD_Stream_V16VIS_A1_Summary.json','V16VIS_A1_Final_Closure.json','V16VIS_A1_Visual_Authority_Manifest.csv','V16VIS_A1_Artifact_Manifest.csv']:gate('A1_'+n,(a1/n).is_file(),a1/n)
  manifest(a1,'V16VIS_A1_Artifact_Manifest.csv',gate);asum=jl(a1/'PAD_Stream_V16VIS_A1_Summary.json');ac=jl(a1/'V16VIS_A1_Final_Closure.json');auth=cl(a1/'V16VIS_A1_Visual_Authority_Manifest.csv')
  gate('A1_status',asum.get('status')=='V16_VISUAL_AUTHORITY_MANIFEST_AND_DATA_EXTRACTION_VALIDATED',asum.get('status'));gate('A1_release',asum.get('release_id')==RELEASE_ID);gate('A1_closed',ac.get('all_gates_passed') is True);gate('A1_count',len(auth)==31,len(auth));gate('A1_ids',[r['figure_id'] for r in auth]==EXPECTED_IDS)
  stage='E49_release';e49=drive/E49
  for n in ['PAD_Stream_V16E49_Summary.json','V16E49_Final_Closure.json','PAD_Stream_V16_Final_Freeze_Contract.json','PAD_Stream_V16_Release_Certificate.json','V16E49_Artifact_Manifest.csv']:gate('E49_'+n,(e49/n).is_file(),e49/n)
  manifest(e49,'V16E49_Artifact_Manifest.csv',gate);es=jl(e49/'PAD_Stream_V16E49_Summary.json');ec=jl(e49/'V16E49_Final_Closure.json');fr=jl(e49/'PAD_Stream_V16_Final_Freeze_Contract.json');cert=jl(e49/'PAD_Stream_V16_Release_Certificate.json')
  gate('E49_status',es.get('status')=='FINAL_V16_FREEZE_AND_RELEASE_CANDIDATE_ASSEMBLED',es.get('status'));gate('E49_release',es.get('release_id')==RELEASE_ID);gate('E49_closed',ec.get('all_gates_passed') is True);gate('E49_frozen',fr.get('V16_frozen') is True and cert.get('V16_frozen') is True);gate('IBDP_not_before_visual_closeout',fr['post_freeze_scope']['IBDP_work_begins_before_visual_closeout'] is False);gate('runtime_immutable',fr['immutability_policy']['frozen_runtime_physics_modification_authorized'] is False);gate('obs_immutable',fr['immutability_policy']['frozen_observation_states_modification_authorized'] is False)
  stage='phase_integration'
  if out.exists() and any(out.iterdir()):raise GateError('C1_output_directory_not_empty')
  (out/'figures'/'PNG').mkdir(parents=True,exist_ok=True);(out/'figures'/'PDF').mkdir(parents=True,exist_ok=True)
  master=[];caps=[];cover=[];ff=[];dest_seen=set();variants=0;files_total=0
  for phase,cfg in PHASES.items():
   rel,sn,cn,mn,ixn,capn,estatus,ids,ev,ef=cfg;base=drive/rel
   for n in [sn,cn,mn,ixn,capn]:gate(phase+'_'+n,(base/n).is_file(),base/n)
   ar=manifest(base,mn,gate);am={r['file']:r for r in ar};s=jl(base/sn);c=jl(base/cn);ix=cl(base/ixn);cp=cl(base/capn)
   gate(phase+'_status',s.get('status')==estatus,s.get('status'));gate(phase+'_release',s.get('release_id')==RELEASE_ID,s.get('release_id'));gate(phase+'_closed',c.get('all_gates_passed') is True);gate(phase+'_unmodified',c.get('accepted_simulation_state_modified') is False,c.get('accepted_simulation_state_modified'));gate(phase+'_variants',int(s.get('rendered_variants'))==ev,s.get('rendered_variants'));gate(phase+'_rendered',int(s.get('rendered_files_png_pdf'))==ef,s.get('rendered_files_png_pdf'));gate(phase+'_index_count',len(ix)==ev,len(ix));gate(phase+'_index_ids',set(r['figure_id'] for r in ix)==set(ids));gate(phase+'_caption_count',len(cp)==len(ids),len(cp));gate(phase+'_caption_ids',set(r['figure_id'] for r in cp)==set(ids))
   indexed=[]
   for j,r in enumerate(ix,1):
    fs=splitf(r.get('files',''));gate(phase+f'_row{j}_two_files',len(fs)==2,fs);gate(phase+f'_row{j}_png_pdf',sorted(Path(x).suffix.lower() for x in fs)==['.pdf','.png'])
    outpaths={}
    for fn in fs:
     gate(phase+'_manifest_contains_'+fn,fn in am,fn);src=base/fn;gate(phase+'_src_'+fn,src.is_file(),src);ss=sha(src);gate(phase+'_srcsha_'+fn,ss==am[fn]['sha256'],ss);gate('unique_dest_'+fn,fn not in dest_seen,fn);dest_seen.add(fn);sub='PNG' if src.suffix.lower()=='.png' else 'PDF';dst=out/'figures'/sub/fn;write(dst,src.read_bytes());gate('copysha_'+fn,sha(dst)==ss,sha(dst));outpaths[src.suffix.lower().lstrip('.')]=str(dst.relative_to(out).as_posix());indexed.append(fn);ff.append({'phase':phase,'figure_id':r['figure_id'],'source_relative_path':str((rel/fn).as_posix()),'final_relative_path':str(dst.relative_to(out).as_posix()),'file':fn,'format':src.suffix.lower().lstrip('.'),'sha256':sha(dst),'bytes':dst.stat().st_size})
    mr={'phase':phase};mr.update(r);mr['source_phase_path']=str(rel.as_posix());mr['final_png']=outpaths.get('png','');mr['final_pdf']=outpaths.get('pdf','');master.append(mr)
   manifestfig=[r['file'] for r in ar if Path(r['file']).suffix.lower() in {'.png','.pdf'}];gate(phase+'_manifest_figure_count',len(manifestfig)==ef,len(manifestfig));gate(phase+'_index_covers_manifest_figures',set(indexed)==set(manifestfig))
   for r in cp:q={'phase':phase};q.update(r);caps.append(q)
   for fid in ids:cover.append({'figure_id':fid,'phase':phase,'variant_count':sum(1 for r in ix if r['figure_id']==fid),'caption_present':sum(1 for r in cp if r['figure_id']==fid)==1,'a1_registered':fid in [x['figure_id'] for x in auth],'complete':True})
   variants+=len(ix);files_total+=len(indexed)
  stage='global_reconciliation';gate('variants_45',variants==45,variants);gate('files_90',files_total==90,files_total);gate('master_45',len(master)==45,len(master));gate('captions_31',len(caps)==31,len(caps));gate('finalfilemanifest_90',len(ff)==90,len(ff));gate('png45',sum(r['format']=='png' for r in ff)==45);gate('pdf45',sum(r['format']=='pdf' for r in ff)==45);gate('coverage31',len(cover)==31,len(cover));gate('coverage_ids',[r['figure_id'] for r in cover]==EXPECTED_IDS);gate('coverage_complete',all(r['complete'] and r['caption_present'] and r['a1_registered'] for r in cover))
  stage='B3_provenance';fb=root/SOURCES['B3_FAILED'][0];gate('failed_B3_preserved',fb.is_file() and blob(fb,root)==SOURCES['B3_FAILED'][1]);gate('only_B3R1_final',all(r['phase']!='B3' for r in ff))
  stage='closeout_metadata';authmap={r['figure_id']:r for r in auth};snap=[]
  for fid in EXPECTED_IDS:
   rr=dict(authmap[fid]);cv=next(x for x in cover if x['figure_id']==fid);rr['integrated_phase']=cv['phase'];rr['integrated_variant_count']=cv['variant_count'];snap.append(rr)
  readme=("# PAD-Stream V16 Final Visual Package\\n\\n"+"Release: "+RELEASE_ID+"\\n\\n"+"Validated closeout: 31 figure IDs, 45 variants, 45 PNG, 45 PDF, 90 rendered files.\\n\\n"+"Final phase chain: B1, B2, B3R1, B4, B5, B6. The original failed B3 runner is preserved in provenance but contributes no validated final figures.\\n\\n"+"No simulation, training, calibration, state mutation, or E49 release-contract modification occurs in C1.\\n")
  certificate={'milestone':MILESTONE,'status':STATUS,'release_id':RELEASE_ID,'V16_frozen':True,'visual_package_closed':True,'A1_registered_figure_ids':31,'validated_visual_variants':45,'validated_png_files':45,'validated_pdf_files':45,'validated_rendered_files_total':90,'phase_chain':['B1','B2','B3R1','B4','B5','B6'],'original_B3_failure_preserved_in_provenance':True,'original_B3_used_as_final_visual_authority':False,'B3R1_used_as_final_streamline_TOF_visual_authority':True,'accepted_state_mutation':False,'E49_release_contract_modified':False,'IBDP_before_visual_closeout_prohibition_satisfied':True,'new_V16_development_authorized':False,'next':NEXT}
  summary={'milestone':MILESTONE,'status':STATUS,'release_id':RELEASE_ID,'visual_package_closed':True,'registered_figure_ids':31,'validated_variants':45,'rendered_png_pdf_files':90,'png_files':45,'pdf_files':45,'phase_chain':['B1','B2','B3R1','B4','B5','B6'],'terminal_day':cert['runtime_closed_through_day'],'terminal_step':cert['terminal_step'],'terminal_restart_sha256':cert['terminal_restart_sha256'],'production_policy':cert['production_policy'],'accepted_state_mutation':False,'next':NEXT}
  closure={'milestone':MILESTONE,'status':STATUS,'all_gates_passed':all(v['passed'] for v in g.values()),'gate_count':len(g),'all_31_figure_ids_covered':True,'all_45_variants_integrated':True,'all_90_png_pdf_files_hash_verified_and_copied':True,'all_31_family_captions_integrated':True,'failed_B3_provenance_preserved':True,'B3R1_repair_is_final_streamline_TOF_authority':True,'E49_freeze_immutability_preserved':True,'accepted_simulation_state_modified':False,'V16_visual_package_formally_closed':True,'IBDP_timing_dependency_on_visual_closeout_satisfied':True,'new_V16_simulation_development_authorized':False,'next':NEXT}
  write(out/'V16VIS_C1_Master_Figure_Index.csv',cb(master));write(out/'V16VIS_C1_Master_Figure_Captions.csv',cb(caps));write(out/'V16VIS_C1_Figure_Family_Coverage.csv',cb(cover));write(out/'V16VIS_C1_A1_Authority_Snapshot.csv',cb(snap));write(out/'V16VIS_C1_Source_Bindings.csv',cb(srows));write(out/'V16VIS_C1_Final_Figure_File_Manifest.csv',cb(ff));write(out/'V16VIS_C1_Final_Visual_Package_Certificate.json',jb(certificate));write(out/'PAD_Stream_V16VIS_C1_Summary.json',jb(summary));write(out/'V16VIS_C1_Final_Gate_Matrix.csv',cb([{'gate':k,**v} for k,v in g.items()]));write(out/'V16VIS_C1_Final_Closure.json',jb(closure));write(out/'README_V16_FINAL_VISUAL_PACKAGE.md',readme.encode())
  pkgmanifest=[]
  for p in sorted(out.rglob('*')):
   if p.is_file() and p.name!='V16VIS_C1_Artifact_Manifest.csv':pkgmanifest.append({'relative_path':str(p.relative_to(out).as_posix()),'sha256':sha(p),'bytes':p.stat().st_size})
  write(out/'V16VIS_C1_Artifact_Manifest.csv',cb(pkgmanifest))
  print('\n'+'='*164);print('PAD-Stream V16VIS-C1: PASS');print('='*164);print(f"{'Status':72}: {STATUS}");print(f"{'Release ID':72}: {RELEASE_ID}");print(f"{'A1 registered figure IDs':72}: 31");print(f"{'Integrated visual variants':72}: 45");print(f"{'Integrated PNG/PDF files':72}: 90");print(f"{'PNG / PDF':72}: 45 / 45");print(f"{'Master captions':72}: 31");print(f"{'Final phase chain':72}: B1, B2, B3R1, B4, B5, B6");print(f"{'Original B3 failure preserved':72}: True");print(f"{'Accepted simulation state modified':72}: False");print(f"{'E49 freeze contract modified':72}: False");print(f"{'V16 visual package formally closed':72}: True");print(f"{'IBDP visual-closeout timing dependency satisfied':72}: True");print(f"{'Next':72}: {NEXT}")
  return 0
 except Exception as e:
  blocked.mkdir(parents=True,exist_ok=True);data=jb({'milestone':MILESTONE,'status':'FINAL_V16_VISUAL_PACKAGE_INTEGRATION_BLOCKED','failed_stage':stage,'exception':repr(e),'gates':g});p=blocked/'V16VIS_C1_Blocked_Report.json';p.write_bytes(data);print('\n'+'='*164);print('PAD-Stream V16VIS-C1: BLOCKED');print('='*164);print('Report      :',p);print('Failed stage:',stage);print('Exception   :',repr(e));return 2

def parse_args():
 p=argparse.ArgumentParser();p.add_argument('--project-root',type=Path,default=Path('.'));p.add_argument('--drive-root',type=Path,default=Path('/content/drive/MyDrive/PAD_Stream_Compute'));p.add_argument('--self-test',action='store_true');return p.parse_args()
if __name__=='__main__':
 a=parse_args()
 if a.self_test:self_test();raise SystemExit(0)
 raise SystemExit(main(a.project_root,a.drive_root))
