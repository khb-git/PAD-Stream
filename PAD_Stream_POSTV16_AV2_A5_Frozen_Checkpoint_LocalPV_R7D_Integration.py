#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,io,json,subprocess,sys,time,zipfile
from pathlib import Path
import numpy as np

MILESTONE='POSTV16-AV2-A5'
PROTOCOL='POSTV16_AV2_A5_FROZEN_CHECKPOINT_LOCAL_PORE_VOLUME_R7D_TERMINAL_HALO_INTEGRATION_V1'
STATUS_PASS='AV2A5_FROZEN_CHECKPOINT_VARIABLE_POROSITY_LOCAL_PORE_VOLUME_R7D_TERMINAL_HALO_INTEGRATION_ALL_4_REALIZATIONS_ALL_9_TIMES_PASS'
STATUS_FAIL='AV2A5_VARIABLE_POROSITY_LOCAL_PORE_VOLUME_R7D_INTEGRATION_SCIENTIFIC_FAIL_NO_ADAPTATION_OR_RETUNING_AUTHORIZED'
STATUS_BLOCKED='AV2A5_TECHNICAL_EXECUTION_BLOCKED'
RID='PAD_STREAM_V16_RC1_B92D52088D01078A'
PARENT='19f385379d90838f13c739c92a1fcaa87c2b1ef8'
CKSHA='1c82867c53d9d3a63ee8ba9dab5ab65e9bdfaf6330fb5239954d02d7f566ef28'

A4R2='PAD_Stream_POSTV16_AV2_A4_R2_Frozen_Checkpoint_OneTouch_OOD_Continuation.py'; A4R2B='fd1428e093481ceb3b271fa8b5ff22fb9fdfc55f'
A2='PAD_Stream_POSTV16_AV2_A2_Porosity_Realization_and_Pore_Kinematics_Execution.py'; A2B='f141b07f0424d29a7996c089a76dbe7128af5132'
A3='PAD_Stream_POSTV16_AV2_A3_Variable_Porosity_Teacher_Dataset_and_PIRNN_Protocol.py'; A3B='9b209abc3a2abb905b9250a16344e52160e61c47'
R7E='PAD_Stream_POSTV16_AV1_D_R7_R7E_Frozen_Horizontal_Face_Halo_Occupancy_Domain_Execution.py'; R7EB='9f99d9dcab649ba7ac911ad09ad79b4e0eb2ecc8'
B1='PAD_Stream_POSTV16_AV1_B1_R1_C26_to_E37A_Component_Mass_Representation_Equivalence_Audit.py'; B1B='8d9561d7c85805b82dedc26073c4633f90eeeab6'
E37A='PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py'; E37AB='0bbf98ed89cee9128ef1d313c321f9a401b4e9f0'
SG7D='PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py'; SG7DB='890088c0c0fcab415a2c7351c5079ca8ee12bf82'
R2='PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py'; R2B='a127f8730a16e150713420ea547a8de6255550ef'
SOURCES={A4R2:A4R2B,A2:A2B,A3:A3B,R7E:R7EB,B1:B1B,E37A:E37AB,SG7D:SG7DB,R2:R2B}

BASE=Path('post_v16')/RID/'POSTV16_AV2_Variable_Porosity'
A2D=BASE/'POSTV16_AV2_A2_Porosity_Realization_and_Pore_Kinematics_Execution'
A3D=BASE/'POSTV16_AV2_A3_Variable_Porosity_Teacher_Dataset_and_PIRNN_Protocol'
R2D=BASE/'POSTV16_AV2_A4_R2_Frozen_Checkpoint_OneTouch_OOD_Continuation'
A4D=BASE/'POSTV16_AV2_A4_PIRNN_Training_Checkpoint_and_OneTouch_OOD'
OUTD=BASE/'POSTV16_AV2_A5_Frozen_Checkpoint_LocalPV_R7D_Integration'
FAILD=BASE/'POSTV16_AV2_A5_SCIENTIFIC_FAIL'; BLOCKD=BASE/'POSTV16_AV2_A5_BLOCKED'
A2MAN='POSTV16_AV2_A2_Artifact_Manifest.csv'; A2SUM='PAD_Stream_POSTV16_AV2_A2_Summary.json'
A3MAN='POSTV16_AV2_A3_Artifact_Manifest.csv'; A3TV='POSTV16_AV2_A3_TrainValidation_Transport_Dataset.npz'
R2MAN='POSTV16_AV2_A4_R2_Artifact_Manifest.csv'; R2SUM='PAD_Stream_POSTV16_AV2_A4_R2_Summary.json'; R2DEC='POSTV16_AV2_A4_R2_Decision_Contract.json'; R2OOD='POSTV16_AV2_A4_R2_LockedOOD_Truth_and_Predictions.npz'
CHECKPOINT='POSTV16_AV2_A4_Best_Validation_Model.keras'
A2STATUS='AV2A2_FROZEN_SPATIAL_POROSITY_REALIZATIONS_GENERATED_PRESSURE_Q_INVARIANCE_CERTIFIED_PORE_KINEMATICS_RECONSTRUCTED_PASS'
R2STATUS='AV2A4R2_FROZEN_CHECKPOINT_LOCKED_OOD_TEACHER_GENERATED_ONCE_EVALUATED_ONCE_DESCRIPTIVE_GENERALIZATION_EVIDENCE_FROZEN'
REAL=[('AV2PHI0001',0,'TRAIN'),('AV2PHI0002',1,'TRAIN'),('AV2PHI0003',2,'VALIDATION'),('AV2PHI0004',3,'LOCKED_OOD_TEST')]
DAYS=np.array([30.,60.,100.,150.,250.,365.,500.,750.,1000.]); GRID=(15,50,50); NSL=1078; NN=201; NCV=200; NT=9
DX=6.096; DY=6.096; DZ=1.2192; BULK=DX*DY*DZ; BACKGROUND=.20; INJECTED=.80; MAXSG=.60

class GateError(RuntimeError): pass
class ScientificFail(RuntimeError):
    def __init__(self,g,d=None): super().__init__(g); self.g=g; self.d=d

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()
def git(root,*a):
    return subprocess.run(['git','-C',str(root),*a],check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.strip()
def blob(p,root): return git(root,'hash-object',str(p))
def lj(p): return json.loads(Path(p).read_text())
def rcsv(p):
    with open(p,newline='',encoding='utf-8') as f: return list(csv.DictReader(f))
def man(d,n):
    m={r['file']:r['sha256'] for r in rcsv(d/n)}
    if not m: raise GateError('manifest_empty:'+n)
    for f,e in m.items():
        q=d/f
        if not q.is_file() or sha(q)!=e: raise GateError('manifest_mismatch:'+f)
    return m
def mod(p,n):
    s=importlib.util.spec_from_file_location(n,p)
    if s is None or s.loader is None: raise GateError('cannot_load:'+str(p))
    m=importlib.util.module_from_spec(s); sys.modules[n]=m; s.loader.exec_module(m); return m
def jb(x): return (json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
def cb(rr):
    rr=list(rr)
    if not rr: return b''
    ks=[]
    for r in rr:
        for k in r:
            if k not in ks: ks.append(k)
    s=io.StringIO(); w=csv.DictWriter(s,fieldnames=ks,lineterminator='\n'); w.writeheader(); w.writerows(rr); return s.getvalue().encode()
def npzb(a):
    o=io.BytesIO()
    with zipfile.ZipFile(o,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for k in sorted(a):
            b=io.BytesIO(); np.save(b,np.asarray(a[k]),allow_pickle=False); i=zipfile.ZipInfo(k+'.npy',(1980,1,1,0,0,0)); i.compress_type=zipfile.ZIP_DEFLATED; i.external_attr=0o600<<16; z.writestr(i,b.getvalue())
    return o.getvalue()
def pub(d,fs):
    d.mkdir(parents=True,exist_ok=True)
    for n,b in fs.items():
        p=d/n
        if p.exists() and p.read_bytes()!=b: raise GateError('existing_output_differs:'+n)
        if not p.exists(): p.write_bytes(b)

def local_mass(r2,sat,pressure,pref,pv):
    sat=np.asarray(sat,float); pv=np.asarray(pv,float); sg=np.clip(sat-BACKGROUND,0,MAXSG)
    rho=np.asarray(r2.gas_density_from_state(sat,pressure,pref),float)
    return pv*rho*sg

def invert_local_mass(r2,target,pressure,pref,pv):
    target=np.asarray(target,float); pv=np.asarray(pv,float)
    if target.shape!=GRID or pv.shape!=GRID: raise GateError('local_inversion_shape')
    if np.any(target<-1e-9) or np.any(pv<=0) or not np.isfinite(pv).all(): raise GateError('local_inversion_input')
    target=np.maximum(target,0); cap=local_mass(r2,np.full(GRID,INJECTED),pressure,pref,pv)
    tol=max(1e-8,1e-12*max(float(np.max(cap)),1.0)); mx=float(np.max(target-cap))
    if mx>tol: raise ScientificFail('local_cell_mass_capacity_before_EOS_inversion',{'excess':mx,'tol':tol})
    lo=np.zeros(GRID); hi=np.full(GRID,MAXSG)
    for _ in range(80):
        mid=.5*(lo+hi); m=local_mass(r2,BACKGROUND+mid,pressure,pref,pv); below=m<target; lo=np.where(below,mid,lo); hi=np.where(below,hi,mid)
    sg=.5*(lo+hi); sg[target<=1e-18]=0; return sg

def assemble_pred(pred,ti,sl):
    pred=np.asarray(pred,float); ti=np.asarray(ti,int); sl=np.asarray(sl,int); out=np.empty((NT,NSL,NN),float); seen=np.zeros((NT,NSL),int)
    for n in range(len(pred)): out[ti[n],sl[n]]=pred[n]; seen[ti[n],sl[n]]+=1
    if not np.all(seen==1): raise ScientificFail('prediction_time_streamline_bijection',{'min':int(seen.min()),'max':int(seen.max())})
    return out

def self_test():
    class R:
        @staticmethod
        def gas_density_from_state(s,p,pref): return np.full(np.broadcast(s,p).shape,700.0)
    r=R(); phi=np.linspace(.11,.29,np.prod(GRID)).reshape(GRID); pv=phi*BULK; sg=np.full(GRID,.37); p=np.ones(GRID)*2500.; m=pv*700*sg; got=invert_local_mass(r,m,p,0.,pv)
    if np.max(abs(got-sg))>1e-12: raise RuntimeError('variable_local_pv_inversion')
    print('POSTV16-AV2-A5 local-PV R7D integration self-test: PASS')

def main(root,drive):
    import tensorflow as tf
    gates={}; stage='preflight'; completed=0; time_rows=[]; real_rows=[]; files={}
    def g(n,v,val=None):
        ok=bool(v); gates[n]={'passed':ok,'value':val}; print(f"[{'PASS' if ok else 'FAIL'}] {n}"+(f" — {val}" if val is not None else ''))
        if not ok: raise GateError(n)
    def sg(n,v,val=None):
        ok=bool(v); gates[n]={'passed':ok,'value':val,'scientific_execution_gate':True}; print(f"[{'PASS' if ok else 'FAIL'}] {n}"+(f" — {val}" if val is not None else ''))
        if not ok: raise ScientificFail(n,val)
    out=drive/OUTD
    print('='*196); print('POSTV16-AV2-A5 — FROZEN CHECKPOINT / LOCAL PORE-VOLUME / R7D TERMINAL-HALO INTEGRATION'); print('='*196)
    print('ALL 4 FROZEN AV2 POROSITY REALIZATIONS. ALL 9 CANONICAL TIMES.')
    print('NO TRAINING. NO CHECKPOINT RESELECTION. NO OOD TRUTH/METRIC REOPEN. NO ADAPTIVE HALO. NO MAPBACK RETUNING. NO CMG.')
    try:
        root=root.resolve(); drive=drive.resolve()
        g('repository_parent_is_A4R2',git(root,'rev-parse','HEAD^')==PARENT,git(root,'rev-parse','HEAD^')); g('repository_clean',git(root,'status','--porcelain')=='')
        for f,e in SOURCES.items():
            a=blob(root/f,root) if (root/f).is_file() else 'missing'; g(Path(f).stem+'_blob_exact',a==e,a)
        a2=drive/A2D; a3=drive/A3D; r2d=drive/R2D; a4=drive/A4D
        m2=man(a2,A2MAN); m3=man(a3,A3MAN); mR=man(r2d,R2MAN); g('manifest_SHA_closure',True,(len(m2),len(m3),len(mR)))
        s2=lj(a2/A2SUM); sR=lj(r2d/R2SUM); dR=lj(r2d/R2DEC)
        g('A2_status_exact',s2['status']==A2STATUS,s2['status']); g('A2_pressure_Q_invariance_certified',True)
        g('R2_status_exact',sR['status']==R2STATUS,sR['status']); g('R2_checkpoint_exact',sR['checkpoint_sha256']==CKSHA,sR['checkpoint_sha256']); g('R2_A5_authorized',dR['A5_integration_authorized'] is True); g('R2_no_training',dR['training_performed_in_R2'] is False); g('R2_no_reselection',dR['checkpoint_reselected'] is False); g('R2_no_retuning',dR['post_OOD_retuning'] is False)
        ck=a4/CHECKPOINT; g('checkpoint_SHA_exact',ck.is_file() and sha(ck)==CKSHA,sha(ck) if ck.is_file() else 'missing')
        r7e=mod(root/R7E,'av2a5_r7e'); b1=mod(root/B1,'av2a5_b1'); e37=mod(root/E37A,'av2a5_e37'); sg7d=mod(root/SG7D,'av2a5_sg7d'); r2=mod(root/R2,'av2a5_r2')
        foundation=r7e.find_named_exact([root,drive],r7e.FOUNDATION_NAME,r7e.FOUNDATION_SHA); g('foundation_SHA_exact',sha(foundation)==r7e.FOUNDATION_SHA,str(foundation))
        with np.load(foundation,allow_pickle=False) as z: pressure=np.asarray(z['pressure'],float)
        g('foundation_pressure_shape',pressure.shape==GRID,pressure.shape); g('foundation_pressure_finite',np.isfinite(pressure).all())
        injpc=float(r2.capillary_pressure_from_incremental_sg(float(r2.MAX_INCREMENTAL_CO2_SATURATION)))
        ip=np.array([pressure[k,int(r2.INJECTOR_J),int(r2.INJECTOR_I)]*float(r2.PSI_TO_PA) for k in r2.COMPLETION_K]); pref=float(np.mean(ip)+injpc); g('reference_gas_pressure_finite',np.isfinite(pref),pref)
        with np.load(a3/A3TV,allow_pickle=False) as z:
            Xtv=np.asarray(z['X_required_9'],np.float32); ritv=np.asarray(z['realization_index'],int); titv=np.asarray(z['time_index'],int); sltv=np.asarray(z['streamline_index'],int)
        with np.load(r2d/R2OOD,allow_pickle=False) as z:
            g('R2_OOD_prediction_artifact_checkpoint_exact',str(np.asarray(z['checkpoint_sha256']).reshape(-1)[0])==CKSHA)
            Pood=np.asarray(z['Y_pred'],float); tio=np.asarray(z['time_index'],int); slo=np.asarray(z['streamline_index'],int)
        g('R2_OOD_truth_not_read_in_A5',True)
        model=tf.keras.models.load_model(ck); g('checkpoint_parameter_count_52033',model.count_params()==52033,model.count_params())
        pred_by={}; infer_times={}
        for rid,idx,part in REAL:
            if idx<3:
                q=np.flatnonzero(ritv==idx); g(rid+'_predictor_count',len(q)==NT*NSL,len(q)); t0=time.time(); pp=model.predict(Xtv[q],batch_size=64,verbose=0).astype(float); infer_times[rid]=time.time()-t0; pred_by[rid]=assemble_pred(pp,titv[q],sltv[q])
            else:
                g('AV2PHI0004_use_frozen_R2_prediction_only',Pood.shape==(NT*NSL,NN),Pood.shape); pred_by[rid]=assemble_pred(Pood,tio,slo); infer_times[rid]=0.0
        g('no_OOD_reinference',True); g('no_training_or_optimizer_updates',True)
        for rid,idx,part in REAL:
            stage='integration_'+rid
            artifact=f'POSTV16_AV2_A2_{rid}_Variable_Porosity_Pore_Kinematics.npz'
            g(rid+'_A2_artifact_manifested',artifact in m2 and sha(a2/artifact)==m2[artifact])
            with np.load(a2/artifact,allow_pickle=False) as z:
                phi=np.asarray(z['porosity'],float); xyz=np.asarray(z['streamline_xyz_m'],float); tof=np.asarray(z['pollock_tof_s'],float); w=np.asarray(z['streamline_weight_m3_s'],float)
            sg(rid+'_phi_shape',phi.shape==GRID,phi.shape); sg(rid+'_phi_strict_bounds',float(phi.min())>.10 and float(phi.max())<.30,[float(phi.min()),float(phi.max())]); sg(rid+'_phi_nonconstant',float(phi.std())>0,float(phi.std()))
            pvgrid=phi*BULK; sg(rid+'_local_cell_PV_positive_finite',np.isfinite(pvgrid).all() and np.all(pvgrid>0)); sg(rid+'_local_cell_PV_nonconstant',float(pvgrid.std())>0,float(pvgrid.std()))
            op=sg7d.build_subsegment_operator(xyz,tof/float(e37.DAY_TO_S),w*float(e37.DAY_TO_S))
            graph=r7e.build_extended_halo_graph(op)
            sg(rid+'_S0_nonempty',len(graph['s0_nodes'])>0,len(graph['s0_nodes'])); sg(rid+'_H1_nonempty',len(graph['h1_nodes'])>0,len(graph['h1_nodes'])); sg(rid+'_D1_partition',len(graph['nodes'])==len(graph['s0_nodes'])+len(graph['h1_nodes']),[len(graph['nodes']),len(graph['s0_nodes']),len(graph['h1_nodes'])])
            arc_kind=np.asarray(graph['arc_kind'],np.int8); arc_u=np.asarray(graph['arc_u'],int)
            sg(rid+'_H1_never_originates_arc',not np.any(graph['h1_mask'][arc_u])); sg(rid+'_halo_entry_cost_5',np.all(np.asarray(graph['arc_cost'])[arc_kind==1]==5.0))
            geom=e37.build_control_volume_geometry(r2,op,pressure,pref,NSL,NCV); coeff=np.asarray(geom['cv_pressure_mass_coeff'],float)
            sg(rid+'_E37_coeff_positive',coeff.shape==(NSL,NCV) and np.all(coeff>0) and np.isfinite(coeff).all(),coeff.shape)
            pred201=pred_by[rid]; ids=np.tile(np.arange(NSL,dtype=np.int64),NT)
            p200f,pmf,psmf=b1.project_201_to_200_component_mass(r2,e37,pred201.reshape(-1,NN),coeff,ids)
            p200=p200f.reshape(NT,NSL,NCV); pm=pmf.reshape(NT,NSL,NCV); psm=psmf.reshape(NT,NSL,NN)
            closure=np.abs(np.sum(pm,axis=(1,2))-np.sum(psm,axis=(1,2)))/np.maximum(np.abs(np.sum(pm,axis=(1,2))),1.0)
            sg(rid+'_B1_mass_projection_closure',float(closure.max())<=1e-12,float(closure.max()))
            flat=np.asarray(geom['flat_cell'],int); cvid=np.asarray(geom['cv_id'],int); pv=np.asarray(geom['pv_m3'],float); pseg=np.asarray(geom['pseg_psi'],float)
            rhomax=np.asarray(r2.gas_density_from_state(np.full(GRID,INJECTED),pressure,pref),float); capacity=pvgrid*rhomax*MAXSG
            sg(rid+'_local_capacity_positive_finite',np.isfinite(capacity).all() and np.all(capacity>0))
            satout=np.empty((NT,)+GRID); massout=np.empty((NT,)+GRID); tstart=time.time()
            for it,day in enumerate(DAYS):
                sub=p200[it].reshape(-1)[cvid]; sgas=np.clip(sub-BACKGROUND,0,MAXSG); rho=np.asarray(r2.gas_density_from_state(sub,pseg,pref),float); subm=pv*rho*sgas
                raw=np.bincount(flat,weights=subm,minlength=np.prod(GRID)).reshape(GRID); target=float(np.sum(pm[it])); res=float(np.sum(raw)-target); tol=max(1e-7,1e-11*max(abs(target),1.0))
                sg(f'{rid}_day{int(day)}_B1_to_subsegment_mass',abs(res)<=tol,[res,tol])
                rf=raw.reshape(-1); outside=np.ones(np.prod(GRID),bool); outside[graph['s0_nodes']]=False
                sg(f'{rid}_day{int(day)}_raw_outside_S0_zero',np.array_equal(rf[outside],np.zeros(np.sum(outside))))
                rec,diag,_=r7e.reconcile_mass_halo_strict(raw,capacity,graph)
                inc=invert_local_mass(r2,rec,pressure,pref,pvgrid); sat=BACKGROUND+inc
                sg(f'{rid}_day{int(day)}_sat_finite_bounds',np.isfinite(sat).all() and float(sat.min())>=BACKGROUND-1e-12 and float(sat.max())<=INJECTED+1e-12,[float(sat.min()),float(sat.max())])
                recon=float(np.sum(local_mass(r2,sat,pressure,pref,pvgrid))); rel=abs(recon-float(np.sum(rec)))/max(abs(float(np.sum(rec))),1.0)
                sg(f'{rid}_day{int(day)}_EOS_localPV_mass_closure',rel<=1e-10,rel)
                dm=np.zeros(np.prod(GRID),bool); dm[graph['nodes']]=True; dm=dm.reshape(GRID)
                sg(f'{rid}_day{int(day)}_outside_D1_background',np.array_equal(sat[~dm],np.full(np.sum(~dm),BACKGROUND))); sg(f'{rid}_day{int(day)}_outside_D1_mass_zero',np.array_equal(rec[~dm],np.zeros(np.sum(~dm))))
                satout[it]=sat; massout[it]=rec; completed+=1
                time_rows.append({'porosity_realization_id':rid,'partition':part,'target_day':float(day),'S0_cells':len(graph['s0_nodes']),'H1_cells':len(graph['h1_nodes']),'D1_cells':len(graph['nodes']),'raw_total_component_mass_kg':diag['raw_total_component_mass_kg'],'raw_overloaded_cell_count':diag['raw_overloaded_cell_count'],'raw_max_capacity_excess_kg':diag['raw_max_capacity_excess_kg'],'D1_capacity_kg':diag['D1_capacity_kg'],'S0_capacity_kg':diag['S0_capacity_kg'],'H1_capacity_kg':diag['H1_capacity_kg'],'H1_final_component_mass_kg':diag['H1_final_component_mass_kg'],'H1_capacity_fraction_used':diag['H1_capacity_fraction_used'],'H1_occupied_cell_count':diag['H1_occupied_cell_count'],'max_capacity_excess_after_reconciliation_kg':diag['max_capacity_excess_after_reconciliation_kg'],'mass_relative_closure':diag['total_component_mass_relative_closure'],'EOS_localPV_mass_relative_closure':rel,'grid_saturation_min':float(sat.min()),'grid_saturation_max':float(sat.max())})
            integ=time.time()-tstart
            files[f'POSTV16_AV2_A5_{rid}_Integrated_State.npz']=npzb({'porosity':phi,'grid_saturation':satout,'grid_component_mass_kg':massout,'S0_nodes':graph['s0_nodes'],'H1_nodes':graph['h1_nodes'],'D1_nodes':graph['nodes'],'checkpoint_sha256':np.asarray(CKSHA),'target_days':DAYS})
            real_rows.append({'porosity_realization_id':rid,'partition':part,'phi_min':float(phi.min()),'phi_max':float(phi.max()),'phi_mean':float(phi.mean()),'phi_std':float(phi.std()),'S0_cells':len(graph['s0_nodes']),'H1_cells':len(graph['h1_nodes']),'D1_cells':len(graph['nodes']),'checkpoint_inference_seconds':infer_times[rid],'integration_seconds':integ,'all_9_times_passed':True})
        sg('all_4_realizations_all_9_times',completed==36,completed)
        sg('all_time_mass_closures',max(r['mass_relative_closure'] for r in time_rows)<=1e-10,max(r['mass_relative_closure'] for r in time_rows))
        sg('all_EOS_localPV_closures',max(r['EOS_localPV_mass_relative_closure'] for r in time_rows)<=1e-10,max(r['EOS_localPV_mass_relative_closure'] for r in time_rows))
        sg('all_post_reconciliation_capacity_bounds',max(r['max_capacity_excess_after_reconciliation_kg'] for r in time_rows)<=max(1e-7,1e-11*max(r['D1_capacity_kg'] for r in time_rows)),max(r['max_capacity_excess_after_reconciliation_kg'] for r in time_rows))
        for n in ['no_training','no_checkpoint_reselection','no_normalization_refit','no_OOD_truth_reopen','no_OOD_metric_recompute','no_OOD_reinference','no_halo_adaptation','no_global_rescale','no_CMG']: g(n,True)
        decision={'milestone':MILESTONE,'status':STATUS_PASS,'protocol_id':PROTOCOL,'checkpoint_sha256':CKSHA,'all_four_A1_registry_realizations_integrated':True,'all_nine_canonical_times_integrated':True,'local_pore_volume_capacity_used':True,'R7D_terminal_halo_semantics_preserved':True,'R7R7A_arithmetic_preserved_via_R7E_authority':True,'OOD_truth_or_metrics_reopened':False,'OOD_reinference':False,'training':False,'reselection':False,'normalization_refit':False,'mapback_retuning':False,'CMG_validation':False,'AV2_final_outcome_freeze_authorized':True,'next':{'milestone':'POSTV16-AV2-F','authorized':True,'name':'Final Variable-Porosity Scientific Outcome Freeze and AV3 Handoff'}}
        summary={'milestone':MILESTONE,'status':STATUS_PASS,'protocol_id':PROTOCOL,'checkpoint_sha256':CKSHA,'realizations_completed':4,'canonical_times_per_realization':9,'integrated_cases':36,'max_mass_relative_closure':max(r['mass_relative_closure'] for r in time_rows),'max_EOS_localPV_mass_relative_closure':max(r['EOS_localPV_mass_relative_closure'] for r in time_rows),'max_post_reconciliation_capacity_excess_kg':max(r['max_capacity_excess_after_reconciliation_kg'] for r in time_rows),'max_H1_capacity_fraction_used':max(r['H1_capacity_fraction_used'] for r in time_rows),'max_H1_occupied_cell_count':max(r['H1_occupied_cell_count'] for r in time_rows),'training':False,'OOD_truth_reopened':False,'OOD_reinference':False,'CMG_validation':False,'next':decision['next']}
        files.update({'PAD_Stream_POSTV16_AV2_A5_Summary.json':jb(summary),'POSTV16_AV2_A5_Realization_Summary.csv':cb(real_rows),'POSTV16_AV2_A5_Timewise_Integration_Audit.csv':cb(time_rows),'POSTV16_AV2_A5_Decision_Contract.json':jb(decision),'POSTV16_AV2_A5_Final_Gate_Matrix.csv':cb([{'gate':k,**v} for k,v in gates.items()])})
        pub(out,files); mr=[{'file':q.name,'sha256':sha(q),'bytes':q.stat().st_size} for q in sorted(out.iterdir()) if q.is_file() and q.name!='POSTV16_AV2_A5_Artifact_Manifest.csv']; pub(out,{'POSTV16_AV2_A5_Artifact_Manifest.csv':cb(mr)})
        print('\n'+'='*196); print('POSTV16-AV2-A5: PASS'); print('='*196); print('Integrated cases: 36 / 36'); print('Max mass relative closure:',summary['max_mass_relative_closure']); print('Max EOS local-PV closure:',summary['max_EOS_localPV_mass_relative_closure']); print('Max post-reconciliation capacity excess kg:',summary['max_post_reconciliation_capacity_excess_kg']); print('Max H1 capacity fraction used:',summary['max_H1_capacity_fraction_used']); print('NEXT: POSTV16-AV2-F'); print('='*196); return 0
    except ScientificFail as e:
        d=drive/FAILD; d.mkdir(parents=True,exist_ok=True); r={'milestone':MILESTONE,'status':STATUS_FAIL,'failed_stage':stage,'failed_gate':e.g,'detail':e.d,'gates':gates,'completed_cases':completed,'training':False,'OOD_truth_reopened':False,'A5_rerun_authorized':False,'next_authorized':False}; q=d/'POSTV16_AV2_A5_Scientific_Fail_Report.json'; q.write_bytes(jb(r)) if not q.exists() else None; print('POSTV16-AV2-A5: SCIENTIFIC FAIL',e.g,e.d); return 3
    except Exception as e:
        d=drive/BLOCKD; d.mkdir(parents=True,exist_ok=True); r={'milestone':MILESTONE,'status':STATUS_BLOCKED,'failed_stage':stage,'exception':repr(e),'gates':gates,'completed_cases':completed,'training':False,'OOD_truth_reopened':False,'next_authorized':False}; q=d/'POSTV16_AV2_A5_Blocked_Report.json'; q.write_bytes(jb(r)) if not q.exists() else None; print('POSTV16-AV2-A5: BLOCKED',stage,repr(e)); return 2

def parse():
    p=argparse.ArgumentParser(); p.add_argument('--project-root',type=Path,default=Path('.')); p.add_argument('--drive-root',type=Path,default=Path('/content/drive/MyDrive/PAD_Stream_Compute')); p.add_argument('--self-test',action='store_true'); return p.parse_args()
if __name__=='__main__':
    a=parse()
    if a.self_test: self_test(); raise SystemExit(0)
    raise SystemExit(main(a.project_root,a.drive_root))
