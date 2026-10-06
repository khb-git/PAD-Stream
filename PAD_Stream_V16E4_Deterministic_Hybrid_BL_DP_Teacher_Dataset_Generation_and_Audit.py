#!/usr/bin/env python3
"""PAD-Stream V16E-4: frozen teacher generation and audit, never training.

Requires NumPy >= 2.0. Run from the repository after the authenticated Colab pull.
Parent authority is the successful V16E-3-R1 run. No top-level legacy module is
imported: only SHA-bound, whitelisted pure teacher definitions are compiled.
If the frozen teacher fails, publish a BLOCKED audit report, no accepted dataset.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import numpy as np

E3_REL = Path('provenance/hybrid_dp/V16E3_R1_HYBRID_PROTOCOL_FREEZE')
E2_REL = Path('provenance/hybrid_dp/V16E2_CONTROLLED_8LAYER_DP_REPRODUCTION')
OUT_REL = Path('datasets/hybrid_dp/V16E4_DETERMINISTIC_TEACHER_DATASET')
PARENTS = {
 'protocol': ('V16E3_R1_Hybrid_BL_DP_Protocol.json','57bcb2e74c68eb77ed8de69d75ddafc00b38d2f3c4e9b884bfc87676160db4a1'),
 'results': ('V16E3_R1_Hybrid_BL_DP_Protocol_Freeze_Results.json','1b79394c2c15c44e72510f296e364cc8246d1e4e2310aca14534ef248a103acb'),
 'summary': ('PAD_Stream_V16E3_R1_Summary.json','b55d5fc2b0f8febc0bcb042678b95aa5b6a5767286630e1dd5ca11f28de2837a'),
 'handoff': ('V16E3_R1_Handoff.md','253ec8c52dfedbcae5429f7ff6e30a3ea29888870e1fc4db8e9ab5a34fc99c0a'),
}
E3_RUNNER = ('PAD_Stream_V16E3_Prospective_Hybrid_BL_DP_Teacher_Dataset_Split_Objective_Model_Protocol_Freeze_R1.py',
             '302af914f33711be695bd606ceba954e0dcd3e8765a04704ffc8085631af1571')
SOURCES = {
 'DP': ('PAD_Stream_CCUS_Physics_Development_v14_Complete_Validation.py','45c3c8a26ff270df8d28dc6e67ed432a3de86255229f7046f5b0f3d1899d27f6'),
 'Hybrid10': ('PAD_Stream_Dykstra_Parsons_Hybrid_PIRNN_10Param.py','2606f265d97ef1034a7555384daa79e4b3ddddef7c180b8d9f3fc3aedcc8d02f'),
 'Hybrid12': ('PAD_Stream_Dykstra_Parsons_Hybrid_PIRNN_12Param.py','21116ddfd67f88585a0fc809075ece00008b09bd1f61536964ff03774ff8aae0'),
}
LF_SHA = {'Hybrid10':'65d017e590a500d527fba8f9e07e2dcc66a7bc34e0ad6ce14a44075cb0b8e87c',
          'Hybrid12':'7612e304c387c022f5bfd9937a45deb50d23f96c8efc464b7f5e1c63ea035897'}
FEATURES10 = ['no','nw','swc','sor','mu_w','mu_o','phi','tD','xD_star','Sw_star']
FEATURES12 = FEATURES10[:7]+['krw_max','kro_max']+FEATURES10[7:]
BL_FUNCTIONS = ['validate_params','calculate_relative_permeability_np','fractional_flow_np',
                'dfw_dsw_np','welge_tangent','calculate_x_sw','profile_at_time',
                'build_fan_profiles','breakthrough_time_days']
DP_DEFINITIONS = ['_fw_se','_dfw_dse','DPLayer','DykstraParsons','flow_storage_diagram',
                  'layered_flow_storage','dykstra_parsons_coefficient','_probit',
                  '_v14_test_dykstra_parsons_behavior']
SUCCESS = 'V16E4_FROZEN_TEACHER_DATASET_GENERATED_AND_AUDITED_TRAINING_NOT_AUTHORIZED'
BLOCKED = 'V16E4_BLOCKED_FROZEN_NUMERICAL_TEACHER_AUDIT_FAILED_NO_ACCEPTED_DATASET'
PROHIBITIONS = ['NO NEURAL-NETWORK TRAINING.','NO CHECKPOINT CREATION.',
 'NO HISTORICAL HYBRID CHECKPOINT CLAIM.','NO SGSim MODIFICATION.',
 'NO POLLOCK/TOF RECOMPUTATION.','NO B4 RETRAINING.','NO OOD REOPENING.',
 'NO ROW-LEVEL SPLITTING.','NO PERMEABILITY CONDITIONING IN THE PI-RNN.',
 'NO AUTOMATIC TEACHER, DOMAIN OR TOLERANCE REPAIR.']


class AuditError(RuntimeError):
    pass


class NumericalFailure(AuditError):
    def __init__(self, detail):
        super().__init__(detail['failed_gate'])
        self.detail = detail


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):
            h.update(b)
    return h.hexdigest()


def encoded(obj):
    return (json.dumps(obj,sort_keys=True,indent=2,allow_nan=False,ensure_ascii=False)+'\n').encode()


def load_json(path):
    def reject(x):
        raise AuditError('Nonfinite JSON literal: '+x)
    return json.loads(Path(path).read_text(encoding='utf-8-sig'),parse_constant=reject)


def gate(name, ok, detail=''):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}"+(f': {detail}' if detail else ''),flush=True)
    if not ok:
        raise AuditError(name+(f': {detail}' if detail else ''))


def exact_file(path, expected, label):
    gate(label+'_exists',Path(path).is_file(),str(path))
    actual=sha(path)
    gate(label+'_SHA_exact',actual==expected,'' if actual==expected else 'actual '+actual)
    return actual


def source_binding(path, label):
    path=Path(path)
    gate(label+'_source_exists',path.is_file())
    b=path.read_bytes();observed=digest(b);authority=SOURCES[label][1]
    if label=='DP':
        gate('DP_source_raw_SHA_exact',observed==authority)
        return {'authority_sha256':authority,'observed_sha256':observed,'representation':'raw_exact'}
    gate(label+'_source_representation_SHA_exact',observed in [authority,LF_SHA[label]])
    restored=digest(b.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))
    gate(label+'_source_original_CRLF_SHA_exact',restored==authority)
    return {'authority_sha256':authority,'observed_sha256':observed,
            'representation':'original_CRLF' if observed==authority else 'verified_Git_LF',
            'reconstructed_original_sha256':restored}


def extract_teacher(path, names, expected_fingerprints=None, hybrid=False):
    """Execute only selected definitions after byte authority binding.

    Excludes imports, examples, inference/model loaders, plotting and main code.
    Effective last top-level definitions preserve source redefinition semantics.
    """
    tree=ast.parse(Path(path).read_text(encoding='utf-8-sig'))
    definitions={n.name:n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    if not set(names)<=set(definitions):
        raise AuditError('Missing whitelisted teacher definitions')
    fingerprints={n:digest(ast.dump(definitions[n],include_attributes=False).encode()) for n in names}
    for name,wanted in (expected_fingerprints or {}).items():
        if name in names and fingerprints[name]!=wanted:
            raise AuditError('Teacher AST authority mismatch: '+name)
    ns={'np':np,'__name__':'_v16e4_pure_teacher'}
    if hybrid:
        literals={}
        for node in tree.body:
            if isinstance(node,ast.Assign):
                for target in node.targets:
                    if isinstance(target,ast.Name) and target.id in ['EPS','FT3_PER_BBL','REQUIRED_KEYS']:
                        literals[target.id]=ast.literal_eval(node.value)
        if literals.get('EPS')!=1e-12 or literals.get('FT3_PER_BBL')!=5.615:
            raise AuditError('Unexpected source teacher constants')
        ns.update(literals)
    module=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)]
                           +[definitions[n] for n in names],type_ignores=[])
    exec(compile(ast.fix_missing_locations(module),str(path),'exec'),ns)
    return ns,fingerprints


def bind_authority(project, drive, parent):
    print('\nV16E-3-R1 PARENT AUTHORITY',flush=True)
    for key,(name,wanted) in PARENTS.items():
        exact_file(parent/name,wanted,'E3_R1_'+key)
    protocol=load_json(parent/PARENTS['protocol'][0])
    results=load_json(parent/PARENTS['results'][0])
    summary=load_json(parent/PARENTS['summary'][0])
    gate('E3_R1_protocol_milestone_exact',protocol.get('milestone')=='V16E-3-R1')
    gate('E3_R1_results_protocol_SHA_link',results.get('protocol_sha256')==PARENTS['protocol'][1])
    gate('E3_R1_summary_protocol_SHA_link',summary.get('protocol_sha256')==PARENTS['protocol'][1])
    gate('E3_R1_summary_results_SHA_link',summary.get('results_sha256')==PARENTS['results'][1])
    gate('E3_R1_successful_contract',results.get('all_gates_passed') is True and summary.get('protocol_frozen') is True)
    gate('E3_R1_dataset_generation_authorized',protocol['authorization']['dataset_generation_after_success'] is True
         and summary.get('dataset_generation_authorized') is True)
    gate('E3_R1_training_closed',protocol['authorization']['training_authorized'] is False and summary.get('training_authorized') is False)
    gate('E3_R1_checkpoints_closed',protocol['authorization']['checkpoint_creation_authorized'] is False)
    for key in ['SGSim_modification_authorized','Pollock_TOF_recomputation_authorized','B4_retraining_authorized','OOD_reopening_authorized']:
        gate(key+'_false',protocol['authorization'][key] is False)
    exact_file(project/E3_RUNNER[0],E3_RUNNER[1],'E3_R1_runner')
    gate('E3_R1_results_runner_SHA_link',results.get('runner_sha256')==E3_RUNNER[1])
    gate('features10_order_exact',protocol['experiments']['Hybrid10']['features']==FEATURES10)
    gate('features12_order_exact',protocol['experiments']['Hybrid12']['features']==FEATURES12)
    gate('physical_family_split_required',protocol['split']['unit']=='complete physical family')
    d=protocol['dataset_design'];g=d['geometry'];bl=protocol['teacher']['BL']
    gate('frozen_population_exact',d['base_families']==1000 and d['layers_per_family']==8)
    gate('frozen_fan_grid_exact',protocol['model']['sequence_nodes']==201)
    gate('frozen_teacher_grids_exact',bl['source_grid_default']==200 and bl['prospective_reference_grid']==4097 and bl['audit_grid']==8193)
    gate('incompressible_reservoir_units_exact',g['Bw']==1 and g['Bo']==1)
    gate('frozen_clock_count_exact',len(d['positive_fan_clock_fractions'])==20)
    print('\nREAD-ONLY SOURCE AUTHORITY',flush=True)
    bindings={label:source_binding(project/info[0],label) for label,info in SOURCES.items()}
    teachers={};fingerprints={}
    for label in ['Hybrid10','Hybrid12']:
        ev=protocol['provenance']['source_evidence'][label]
        teachers[label],fingerprints[label]=extract_teacher(project/SOURCES[label][0],BL_FUNCTIONS,
                                        ev['teacher_function_ast_sha256'],hybrid=True)
        gate(label+'_pure_teacher_AST_bound',True)
    teachers['DP'],fingerprints['DP']=extract_teacher(project/SOURCES['DP'][0],DP_DEFINITIONS)
    gate('DP_pure_definitions_extracted',True)
    # E2 numerical output remains the canonical reference, still byte-bound.
    e2_path=drive/E2_REL/'V16E2_Controlled_8Layer_DP_Reproduction_Results.json'
    e2_wanted=protocol['provenance']['parents']['E2_RESULTS']['sha256']
    exact_file(e2_path,e2_wanted,'E2_reference_results')
    e2=load_json(e2_path)
    gate('canonical_rows_match_E2',protocol['benchmarks']['E2_canonical_rows_authoritative']==e2['canonical_8_layer_table'])
    return protocol,teachers,bindings,fingerprints,e2


def draw(family, field, layer, bounds):
    lo,hi=bounds
    u=int(digest(f'V16E3_GENERATOR_1604|{family}|{field}|{layer}'.encode()),16)/2**256
    return float(lo+(hi-lo)*u)


def split_families(ids):
    ids=list(ids)
    if len(ids)!=1000 or len(set(ids))!=len(ids):
        raise AuditError('Frozen population requires 1000 unique family IDs')
    order=sorted(ids,key=lambda x:(digest(('V16E3_SPLIT_SEED_1603|'+x).encode()),x))
    return {fid:0 if i<700 else 1 if i<850 else 2 for i,fid in enumerate(order)}


def family_parameters(protocol, fid, label):
    bounds=protocol['dataset_design']['bounds']
    shared={k:draw(fid,k,'shared',bounds[k]) for k in ['no','nw','sor','mu_w_cP','mu_o_cP']}
    rows=[]
    for i in range(8):
        lid=f'L{i+1:02d}'
        r=dict(shared)
        r.update({k:draw(fid,k,lid,bounds[k]) for k in ['k_mD','h_ft','phi','swc']})
        r['mu_w']=r.pop('mu_w_cP');r['mu_o']=r.pop('mu_o_cP')
        if label=='Hybrid10':
            r.update(protocol['experiments'][label]['fixed_endpoints'])
        else:
            for k in ['krw_max','kro_max']:
                r[k]=draw(fid,k+'_Hybrid12',lid,bounds[k+'_Hybrid12'])
        rows.append(r)
    return rows


def canonical_parameters(protocol,label):
    rows=[]
    for r in protocol['benchmarks']['E2_canonical_rows_authoritative']:
        p={'no':2.,'nw':2.,'swc':r['Swc'],'sor':r['Sor'],'mu_w':.5,'mu_o':.7,
           'k_mD':r['k_mD'],'h_ft':r['h_ft'],'phi':r['phi'],
           'krw_max':r['krw_max'],'kro_max':r['kro_max']}
        if label=='Hybrid10':p.update(protocol['experiments'][label]['fixed_endpoints'])
        rows.append(p)
    return rows


def source_case(row, geometry, rate=1.):
    return {k:row[k] for k in ['no','nw','swc','sor','mu_w','mu_o','phi','krw_max','kro_max']}|{
       'A':geometry['width_ft']*row['h_ft'],'x_ip':geometry['length_ft'],
       'i_w':float(rate),'bw':1.,'bo':1.,'injector_at_left':True}


def curve_characterization(teacher,p,n):
    grid=np.linspace(p['swc'],1-p['sor'],n)
    df,fw=teacher['dfw_dsw_np'](grid,p)
    star,fwstar,chord,i=teacher['welge_tangent'](grid,fw,p['swc'])
    speed=float(df[i])
    chords=fw[1:]/(grid[1:]-p['swc']+teacher['EPS'])
    imax=int(np.argmax(chords)+1)
    report={'grid_nodes':n,'source_shock_index':int(i),'source_Sw_star':float(star),
            'source_fw_star':float(fwstar),'source_chord_speed':float(chord),
            'source_characteristic_speed':speed,
            'source_tD_BT':float(1/speed) if speed>0 else None,
            'global_chord_max_index_DIAGNOSTIC_ONLY':imax,
            'global_chord_max_Sw_DIAGNOSTIC_ONLY':float(grid[imax]),
            'global_chord_max_speed_DIAGNOSTIC_ONLY':float(chords[imax-1])}
    return grid,df,report


def independent_corey_derivative(y,p):
    # Diagnostic only. The dataset target remains the extracted source teacher.
    span=1-p['swc']-p['sor'];s=np.clip((np.asarray(y,dtype=float)-p['swc'])/span,0,1)
    a=p['krw_max']*s**p['nw']+1e-12
    b=(p['mu_w']/p['mu_o'])*p['kro_max']*(1-s)**p['no']
    da=p['krw_max']*p['nw']*s**(p['nw']-1)/span
    db=-(p['mu_w']/p['mu_o'])*p['kro_max']*p['no']*(1-s)**(p['no']-1)/span
    return (da*b-a*db)/(a+b)**2


def numeric_require(ok,name,detail):
    if not ok:
        raise NumericalFailure(dict(detail,failed_gate=name))


def interpolate_fan(fan, xi, tolerance, detail):
    x=np.asarray(fan['xi'],dtype=float);y=np.asarray(fan['Sw_fan_true'],dtype=float)
    numeric_require(np.all(np.isfinite(x)) and np.all(np.isfinite(y)), 'fan_finite',detail)
    numeric_require(np.all(np.diff(x)>=0), 'source_fan_sorted',detail)
    unique=[];values=[]
    for xx,yy in zip(x,y):
        if unique and xx==unique[-1]:
            numeric_require(abs(yy-values[-1])<=tolerance,'duplicate_xi_with_conflicting_saturation',detail)
        else:
            unique.append(float(xx));values.append(float(yy))
    numeric_require(len(unique)>1 and unique[0]==0 and abs(unique[-1]-1)<=1e-7,
                    'fan_covers_normalized_domain',detail)
    return np.interp(xi,unique,values).astype(np.float32)


def audit_layer(protocol,teacher,row,context):
    """Audit all frozen clocks; stop on the first violated frozen requirement."""
    geo=protocol['dataset_design']['geometry'];tol=protocol['E4_required_audits']
    p=source_case(row,geo);span=1-p['swc']-p['sor']
    grids={};curves={}
    for n in [200,4097,8193]:
        grid,_,report=curve_characterization(teacher,p,n)
        grids[n]=grid;curves[str(n)]=report
    detail={'context':context,'physical_parameters':row,'source_case_units':p,
            'movable_saturation_span':span,'source_grid_characterization':curves,
            'frozen_tolerances':tol,'teacher_changed':False}
    for n in [4097,8193]:
        r=curves[str(n)];speed=r['source_characteristic_speed']
        numeric_require(np.isfinite(speed) and speed>0,'positive_finite_shock_speed',detail)
        td_max=max(protocol['dataset_design']['positive_fan_clock_fractions'])/speed
        # A necessary consequence of the frozen inventory identity and saturation
        # bounds: a pre-BT profile cannot hold injected PVI greater than DeltaS.
        if td_max-span>tol['preBT_inventory_abs_tolerance']:
            raise NumericalFailure(dict(detail,
                failed_gate='preBT_inventory_impossible_under_saturation_bounds',
                failing_grid_nodes=n,required_preBT_injected_PVI=td_max,
                maximum_admissible_added_inventory_PV=span,
                minimum_possible_inventory_error=td_max-span,
                permitted_inventory_error=tol['preBT_inventory_abs_tolerance'],
                diagnosis='Source first-decrease Welge selection is near swc; fine-grid clock cannot satisfy the frozen inventory identity. Global chord maximum is diagnostic only, not a substituted teacher.'))
    xi=np.arange(201,dtype=float)/200
    fractions=np.asarray(protocol['dataset_design']['positive_fan_clock_fractions'])
    targets={};clock_meta={}
    maxima={'grid_convergence':0.,'fan_endpoint':0.,'characteristic_residual':0.,'inventory_error':0.,'default_vs_refined':0.}
    for n in [4097,8193]:
        r=curves[str(n)];td=fractions/r['source_characteristic_speed']
        days=td*p['phi']*p['A']*p['x_ip']/(teacher['FT3_PER_BBL']*p['i_w'])
        fans=teacher['build_fan_profiles'](days.tolist(),p,Sw_grid=grids[n])
        ys=[];meta=[]
        for j,fan in enumerate(fans):
            ctx=dict(detail,time_index=j,frozen_clock_fraction=float(fractions[j]),grid_nodes=n)
            y=interpolate_fan(fan,xi,tol['fan_endpoint_abs_tolerance'],ctx)
            xstar=float(fan['xD_star']);td_native=float(fan['t_D'])
            numeric_require(0<xstar<1 and td_native>0,'positive_preBT_local_clock',ctx)
            numeric_require(abs(td_native-td[j])<=tol['identity_abs_tolerance'], 'source_tD_reservoir_clock_identity',ctx)
            numeric_require(abs(xstar-fractions[j])<=tol['identity_abs_tolerance'],'source_front_clock_identity',ctx)
            numeric_require(np.all(y>=p['swc']-1e-7) and np.all(y<=1-p['sor']+1e-7),'saturation_physical_bounds',ctx)
            numeric_require(np.all(np.diff(y)<=1e-7),'monotone_fan',ctx)
            endpoint=max(abs(float(y[0])-(1-p['sor'])),abs(float(y[-1])-fan['Sw_star']))
            residual=float(np.max(np.abs(independent_corey_derivative(y,p)[1:-1]-xi[1:-1]*xstar/td_native)))
            inventory=abs(float(xstar*np.trapezoid(y.astype(float)-p['swc'],xi))-td_native)
            numeric_require(endpoint<=tol['fan_endpoint_abs_tolerance'],'fan_endpoint_consistency',dict(ctx,observed=endpoint))
            numeric_require(np.isfinite(residual) and residual<=tol['fan_characteristic_abs_residual_tolerance'],
                            'smooth_fan_characteristic_residual',dict(ctx,observed=residual))
            numeric_require(inventory<=tol['preBT_inventory_abs_tolerance'],'preBT_inventory_identity',dict(ctx,observed=inventory))
            maxima['fan_endpoint']=max(maxima['fan_endpoint'],endpoint)
            maxima['characteristic_residual']=max(maxima['characteristic_residual'],residual)
            maxima['inventory_error']=max(maxima['inventory_error'],inventory)
            ys.append(y);meta.append([td_native,xstar,float(fan['Sw_star'])])
        targets[n]=np.asarray(ys,dtype=np.float32);clock_meta[n]=np.asarray(meta,dtype=float)
    convergence=float(np.max(np.abs(targets[4097].astype(float)-targets[8193])))
    numeric_require(convergence<=tol['grid_convergence_max_Sw_difference'],'teacher_grid_convergence',dict(detail,observed=convergence))
    maxima['grid_convergence']=convergence
    # Required comparison with source-default resolution: diagnostic, not a
    # demand that a 200-node approximation meet fine-grid convergence tolerance.
    r=curves['200'];td=.5/r['source_characteristic_speed']
    days=td*p['phi']*p['A']*p['x_ip']/(5.615*p['i_w'])
    default=teacher['build_fan_profiles']([days],p,Sw_grid=grids[200])[0]
    y_default=interpolate_fan(default,xi,tol['fan_endpoint_abs_tolerance'],detail)
    reference=targets[4097][9]
    maxima['default_vs_refined']=float(np.max(np.abs(y_default.astype(float)-reference)))
    return {'target':targets[4097],'clock_meta':clock_meta[4097],
            'tD_BT':1/curves['4097']['source_characteristic_speed'],
            'fan_excess_integrals':np.trapezoid(targets[4097].astype(float)-p['swc'],xi,axis=-1),
            'source_default_comparison':curves,'maxima':maxima}


def dp_case(teacher,rows,mode):
    return teacher['DykstraParsons'](*[np.asarray([r[k] for r in rows]) for k in ['k_mD','h_ft','phi','swc']],
          rows[0]['sor'],np.asarray([r['krw_max'] for r in rows]),np.asarray([r['kro_max'] for r in rows]),
          rows[0]['mu_w'],rows[0]['mu_o'],mode)


def canonical_dp_audit(protocol,dp,e2):
    passed,message,metrics=dp['_v14_test_dykstra_parsons_behavior']()
    gate('source_native_v14_DP_behavior',bool(passed),message)
    rows=canonical_parameters(protocol,'Hybrid12');tol=protocol['E4_required_audits']['identity_abs_tolerance']
    gridinfo=e2['system_response']
    pvi=np.linspace(gridinfo['pvi_grid_start'],gridinfo['pvi_grid_end'],gridinfo['pvi_grid_count'])
    response={}
    for mode in ['kh','kh_mob']:
        case=dp_case(dp,rows,mode);rec,wc=case.run(pvi)
        field='kh' if mode=='kh' else 'kh_mob'
        gate('canonical_'+mode+'_recovery_endpoint',abs(float(rec[-1])-gridinfo[field+'_final_recovery'])<=tol)
        gate('canonical_'+mode+'_watercut_endpoint',abs(float(wc[-1])-gridinfo[field+'_final_watercut'])<=tol)
        gate('canonical_'+mode+'_rate_closure',abs(float(case.F.sum())-1)<=tol)
        response[mode]={'pvi':pvi.tolist(),'recovery':rec.tolist(),'watercut':wc.tolist()}
    coeff=dp['dykstra_parsons_coefficient']([r['k_mD'] for r in rows])
    _,_,lorenz=dp['layered_flow_storage']([r['k_mD'] for r in rows],[r['h_ft'] for r in rows],[r['phi'] for r in rows])
    gate('canonical_DP_descriptor_exact',abs(coeff-e2['heterogeneity']['dykstra_parsons_coefficient'])<=tol)
    gate('canonical_Lorenz_descriptor_exact',abs(lorenz-e2['heterogeneity']['layered_lorenz_coefficient'])<=tol)
    return {'source_native_DP_behavior':metrics,'canonical_E2_DP_response':response,
            'DP_coefficient':float(coeff),'Lorenz':float(lorenz),
            'note':'V14 DPLayer uses Corey exponents 2/2. Its recovery/WC is a distinct canonical reference; synthetic variable-exponent labels come from the Hybrid BL source.'}


def merge_maxima(maxima, values):
    for k,v in values.items():maxima[k]=max(maxima.get(k,0.),float(v))


def numerical_preflight(protocol,teachers):
    """Audit before allocating bulk dataset files. No case is skipped or repaired."""
    print('NUMERICAL PREFLIGHT: frozen teacher; no bulk arrays allocated.',flush=True)
    audited=0;maxima={}
    for label in ['Hybrid10','Hybrid12']:
        for i,row in enumerate(canonical_parameters(protocol,label)):
            a=audit_layer(protocol,teachers[label],row,
                          {'population':'public_canonical_anchor','experiment':label,'layer_id':i+1})
            merge_maxima(maxima,a['maxima']);audited+=1
    print('[PASS] Both eight-layer public BL anchors audited.',flush=True)
    for family_index in range(1000):
        fid=f'F{family_index:06d}'
        for label in ['Hybrid10','Hybrid12']:
            for i,row in enumerate(family_parameters(protocol,fid,label)):
                try:
                    a=audit_layer(protocol,teachers[label],row,
                                  {'population':'synthetic','family_id':fid,'family_index':family_index,
                                   'experiment':label,'layer_id':i+1})
                except NumericalFailure as exc:
                    exc.detail['parameter_sets_passed_before_counterexample']=audited
                    exc.detail['maxima_before_counterexample']=maxima
                    exc.detail['bulk_arrays_allocated']=False
                    raise
                merge_maxima(maxima,a['maxima']);audited+=1
        if family_index%25==0:
            print(f'Preflight: {family_index+1}/1000 families; {audited} parameter sets.',flush=True)
    return {'audited_parameter_sets':audited,'maxima':maxima}


def prepare_arrays(root,n,dim):
    root.mkdir(parents=True,exist_ok=True)
    shapes={'conditioning':((n,2,8,20,dim),np.float32),
            'Sw_fan_teacher':((n,8,20,201),np.float32),
            'transport_states':((n,2,8,20,5),np.float64),
            'layer_physics':((n,2,8,6),np.float64),
            'physical_parameters':((n,8,11),np.float64),
            'DP_descriptors':((n,2,2),np.float64),
            'common_time_system':((n,2,20,5),np.float64)}
    return {name:np.lib.format.open_memmap(root/(name+'.npy'),mode='w+',dtype=dtype,shape=shape)
            for name,(shape,dtype) in shapes.items()}


def duplicate_check(seen,key,fid,partition,label):
    if key in seen:
        other,other_partition=seen[key]
        if other!=fid and other_partition!=partition:
            raise AuditError(f'Cross-partition {label} duplicate: {other} and {fid}')
    else:seen[key]=(fid,partition)


def generate_pass(root,protocol,teachers,bindings,fingerprints,e2,pass_number):
    ids=[f'F{i:06d}' for i in range(1000)];partitions=split_families(ids)
    counts={name:sum(v==i for v in partitions.values()) for i,name in enumerate(['train','validation','internal_test'])}
    gate(f'pass{pass_number}_case_counts_exact',counts==protocol['split']['counts_base_families'])
    xi=np.arange(201,dtype=np.float64)/200
    np.save(root/'xi.npy',xi,allow_pickle=False)
    np.save(root/'partition_codes.npy',np.asarray([partitions[fid] for fid in ids],dtype=np.uint8),allow_pickle=False)
    np.save(root/'family_ids.npy',np.asarray(ids,dtype='U7'),allow_pickle=False)
    arrays={label:prepare_arrays(root/label,1000,len(FEATURES10 if label=='Hybrid10' else FEATURES12))
            for label in ['Hybrid10','Hybrid12']}
    maxima={};audited_layers=0;seen_physical={};seen_transport={};started=time.monotonic()
    # Both canonical anchors are public and outside the split population.
    anchors={}
    for label in ['Hybrid10','Hybrid12']:
        anchor_rows=canonical_parameters(protocol,label);ys=[];details=[]
        for i,row in enumerate(anchor_rows):
            a=audit_layer(protocol,teachers[label],row,{'population':'public_canonical_anchor','experiment':label,'layer_id':i+1})
            ys.append(a['target']);details.append(a['source_default_comparison']);merge_maxima(maxima,a['maxima'])
            audited_layers+=1
        np.save(root/(label+'_public_anchor_Sw.npy'),np.asarray(ys),allow_pickle=False)
        anchors[label]={'source_grid_comparisons':details,'label':'E2 variable endpoints' if label=='Hybrid12' else 'separately named fixed-0.8 counterpart'}
    print(f'Pass {pass_number}: canonical BL anchors audited; scanning frozen population.',flush=True)
    geo=protocol['dataset_design']['geometry'];qtot=geo['q_total_reservoir_bbl_day'];tol=protocol['E4_required_audits']['identity_abs_tolerance']
    for family_index,fid in enumerate(ids):
        family_rows={label:family_parameters(protocol,fid,label) for label in ['Hybrid10','Hybrid12']}
        phys_sig=digest(encoded(family_rows))
        duplicate_check(seen_physical,phys_sig,fid,partitions[fid],'physical-family')
        for label in ['Hybrid10','Hybrid12']:
            rows=family_rows[label];a=arrays[label];layer_audits=[]
            for i,row in enumerate(rows):
                audited=audit_layer(protocol,teachers[label],row,{'population':'synthetic','family_id':fid,'family_index':family_index,
                                       'experiment':label,'layer_id':i+1,'partition_code':partitions[fid]})
                layer_audits.append(audited);merge_maxima(maxima,audited['maxima']);audited_layers+=1
                a['Sw_fan_teacher'][family_index,i]=audited['target']
                for j,y in enumerate(audited['target']):
                    duplicate_check(seen_transport,digest(y.tobytes()),fid,partitions[fid],'transport-profile')
                keys=['no','nw','swc','sor','mu_w','mu_o','phi','k_mD','h_ft','krw_max','kro_max']
                a['physical_parameters'][family_index,i]=[row[k] for k in keys]
            for mode_index,mode in enumerate(['kh','kh_mob']):
                dp=dp_case(teachers['DP'],rows,mode)
                F=dp.F;pv=dp.PV*geo['width_ft']*geo['length_ft']/5.615
                clock=F*pv.sum()/pv;movable=pv*np.asarray([1-r['swc']-r['sor'] for r in rows])
                if abs(float(F.sum())-1)>tol or np.any(F<=0) or np.any(pv<=0):raise AuditError('DP flow/PV closure failed')
                coeff=teachers['DP']['dykstra_parsons_coefficient']([r['k_mD'] for r in rows])
                _,_,lorenz=teachers['DP']['flow_storage_diagram'](pv/F,F)
                if not (0<=coeff<=1 and -tol<=lorenz<=1+tol):raise AuditError('Nonphysical DP/Lorenz descriptor')
                a['DP_descriptors'][family_index,mode_index]=[coeff,lorenz]
                bt_days=[]
                for i,row in enumerate(rows):
                    info=layer_audits[i];meta=info['clock_meta'];td=meta[:,0];xstar=meta[:,1];swstar=meta[:,2]
                    days=td*pv[i]/(F[i]*qtot);bt_day=info['tD_BT']*pv[i]/(F[i]*qtot);bt_days.append(bt_day)
                    actual_pvi=(F[i]*qtot*days)/pv[i]
                    total_pvi=qtot*days/pv.sum()
                    if np.max(np.abs(actual_pvi-td))>tol or np.max(np.abs(clock[i]*total_pvi-td))>tol:
                        raise AuditError('Reservoir clock / local-PVI identity failed')
                    a['layer_physics'][family_index,mode_index,i]=[row['k_mD'],row['h_ft'],row['phi'],pv[i],F[i],clock[i]]
                    a['transport_states'][family_index,mode_index,i]=np.column_stack([days,td,xstar,swstar,np.full(20,bt_day)])
                    names=FEATURES10 if label=='Hybrid10' else FEATURES12
                    features=np.column_stack([np.full(20,row[k]) if k in row else
                            td if k=='tD' else xstar if k=='xD_star' else swstar for k in names])
                    a['conditioning'][family_index,mode_index,i]=features.astype(np.float32)
                fractions=np.asarray(protocol['dataset_design']['positive_fan_clock_fractions'])
                common_days=fractions*min(bt_days);localtd=F[:,None]*qtot*common_days[None,:]/pv[:,None]
                speeds=np.asarray([1/z['tD_BT'] for z in layer_audits])
                xstar=localtd*speeds[:,None]
                integrals=np.asarray([z['fan_excess_integrals'][9] for z in layer_audits])
                # Profiles are self-similar before BT; source-derived fan integral
                # is scaled by the analytical source characteristic front.
                stored=pv[:,None]*xstar*integrals[:,None]
                rf=stored.sum(axis=0)/movable.sum()
                injected=qtot*common_days
                err=np.abs(stored.sum(axis=0)-injected)/pv.sum()
                if np.max(err)>protocol['E4_required_audits']['preBT_inventory_abs_tolerance']:
                    raise AuditError('Common-time aggregate inventory failed')
                a['common_time_system'][family_index,mode_index]=np.column_stack([
                     common_days,qtot*common_days/pv.sum(),rf,np.zeros(20),np.zeros(20)])
        if family_index%25==0:
            print(f'Pass {pass_number}: families {family_index+1}/1000; audited layers {audited_layers}; {time.monotonic()-started:.1f}s',flush=True)
    for group in arrays.values():
        for name,array in group.items():
            if not np.all(np.isfinite(array)):raise AuditError('Nonfinite dataset array: '+name)
            array.flush()
    # Clear maps before publication/copy; no pickle/object arrays are used.
    arrays.clear()
    dp_report=canonical_dp_audit(protocol,teachers['DP'],e2)
    report={'milestone':'V16E-4','status':SUCCESS,'parent_protocol_sha256':PARENTS['protocol'][1],
            'runner_sha256':sha(Path(__file__)),'source_bindings':bindings,'teacher_AST_sha256':fingerprints,
            'family_counts':counts,'audited_layer_parameter_sets':audited_layers,
            'logical_profiles_per_experiment':1000*2*8*20,'sequence_nodes':201,
            'maxima':maxima,'public_anchors':anchors,'DP_canonical_audit':dp_report,
            'duplicate_firewall':'no cross-partition exact physical-family or saturation-profile duplicates',
            'factorization':'Sw_fan_teacher[family,layer,time,xi] is shared by allocation modes at the same local transport clock; conditioning and physical clocks retain the mode axis',
            'source_teacher_executed':True,'neural_model_created':False,'training_authorized':False,
            'post_breakthrough_learned_targets_created':False,'full_physics_equivalence_claimed':False}
    (root/'V16E4_Numerical_Audit.json').write_bytes(encoded(report))
    cases=[{'family_id':fid,'family_index':i,'partition_code':partitions[fid],
            'partition':['train','validation','internal_test'][partitions[fid]],
            'descendants':'all layers, clocks, allocations and Hybrid endpoint variants inherit this assignment'}
           for i,fid in enumerate(ids)]
    (root/'V16E4_Case_Manifest.json').write_bytes(encoded(cases))
    schema={'allocation_modes':['kh','kh_mob'],'conditioning_feature_order':{'Hybrid10':FEATURES10,'Hybrid12':FEATURES12},
            'transport_states_columns':['time_days','tD','xD_star','Sw_star','breakthrough_days'],
            'layer_physics_columns':['k_mD','h_ft','phi','PV_reservoir_bbl','F_i','clock_per_total_PVI'],
            'physical_parameters_columns':['no','nw','swc','sor','mu_w','mu_o','phi','k_mD','h_ft','krw_max','kro_max'],
            'DP_descriptors_columns':['static_DP','allocation_mode_Lorenz'],
            'common_time_system_columns':['time_days','total_PVI','RF','WC','WOR'],
            'model_inputs_only':['xi.npy','conditioning.npy'],'primary_target':'Sw_fan_teacher.npy',
            'loading':'np.load(...,allow_pickle=False,mmap_mode="r")',
            'batch_mapping':'family/mode/layer/time indexes conditioning; family/layer/time indexes Sw_fan_teacher; broadcast xi along the batch',
            'units':'reservoir bbl/day, reservoir bbl, days, feet, mD, cP; Bw=Bo=1',
            'normalization':'none; raw conditioning as frozen; no fitted statistics',
            'scope':'classical incompressible pre-BT fan only; no post-BT learned labels'}
    (root/'V16E4_Dataset_Schema.json').write_bytes(encoded(schema))
    inventory={p.relative_to(root).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size}
               for p in sorted(root.rglob('*')) if p.is_file()}
    manifest={'parent_artifacts':{k:{'filename':v[0],'sha256':v[1]} for k,v in PARENTS.items()},
              'artifacts':inventory,'runtime':{'python':sys.version.split()[0],'numpy':np.__version__},
              'deterministic_scope':'two independent complete generations on the same numerical runtime; no cross-version bitwise claim',
              'neural_training_authorized':False}
    (root/'V16E4_Dataset_Manifest.json').write_bytes(encoded(manifest))
    return manifest


def tree_hashes(root):
    return {p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def publish_tree(stage,out):
    """Never replace a differing accepted dataset. Transfer via sibling staging."""
    out=Path(out)
    if out.exists():
        if out.is_dir() and tree_hashes(out)==tree_hashes(stage):
            print('Existing identical accepted dataset reused.',flush=True)
            return
        raise AuditError('Existing accepted output differs; choose a new --output-dir. Nothing overwritten.')
    out.parent.mkdir(parents=True,exist_ok=True)
    sibling=Path(tempfile.mkdtemp(prefix='.v16e4-publish-',dir=out.parent))
    try:
        for source in sorted(stage.rglob('*')):
            if source.is_file():
                target=sibling/source.relative_to(stage);target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(source,target)
        if tree_hashes(stage)!=tree_hashes(sibling):raise AuditError('Publication byte verification failed')
        sibling.rename(out)
    finally:
        if sibling.exists():shutil.rmtree(sibling)


def blocked_report(drive,detail,bindings,fingerprints,canonical_dp=None):
    report={'milestone':'V16E-4','status':BLOCKED,'parent_artifacts':{k:{'filename':v[0],'sha256':v[1]} for k,v in PARENTS.items()},
            'runner_sha256':sha(Path(__file__)),'source_bindings':bindings,'teacher_AST_sha256':fingerprints,
            'counterexample':detail,'canonical_DP_audit':canonical_dp,
            'scope_of_audit':'stopped at first failing frozen source-teacher parameter set; full population not certified',
            'accepted_dataset_created':False,'partial_generation_published':False,
            'neural_model_created':False,'training_authorized':False,'checkpoint_creation_authorized':False,
            'teacher_changed':False,'domain_changed':False,'tolerances_changed':False,
            'next_milestone':'V16E-3-R2 numerical-teacher repair protocol; then rerun V16E-4 before any training'}
    data=encoded(report);report_sha=digest(data)
    target=drive/'provenance/hybrid_dp/V16E4_BLOCKED_TEACHER_AUDIT'/report_sha[:16]
    with tempfile.TemporaryDirectory(prefix='v16e4-blocked-') as tmp:
        stage=Path(tmp)
        (stage/'V16E4_Blocked_Teacher_Audit.json').write_bytes(data)
        summary={'milestone':'V16E-4','status':BLOCKED,'audit_report_sha256':report_sha,
                 'failed_gate':detail['failed_gate'],'accepted_dataset_created':False,'training_authorized':False,
                 'next_milestone':report['next_milestone']}
        (stage/'PAD_Stream_V16E4_Blocked_Summary.json').write_bytes(encoded(summary))
        handoff=f'''# PAD-Stream V16E-4 — BLOCKED numerical teacher audit

No accepted dataset or checkpoint was created. Full population certification is
not claimed. The frozen source teacher failed `{detail['failed_gate']}`.
See the audit JSON for the complete physical counterexample and 200/4097/8193
source shock selections. The global chord maximum is recorded for diagnosis
only; it was never substituted into the teacher. E3-R1 authority remains intact.
No source, grid, parameter domain, tolerance, SGSim, Pollock/TOF, B4 or OOD change
was made. A prospective numerical-teacher repair protocol is needed before an
E4 rerun can produce an accepted dataset. Training remains unauthorized.

Audit SHA: {report_sha}
NEXT: {report['next_milestone']}
'''
        (stage/'V16E4_Blocked_Handoff.md').write_text(handoff,encoding='utf-8')
        publish_tree(stage,target)
    print('\n'+'='*110+'\nV16E-4 RESULT: BLOCKED\n'+'='*110,flush=True)
    print('Failed gate:',detail['failed_gate'],flush=True)
    print('Context:',json.dumps(detail['context'],sort_keys=True),flush=True)
    print('Accepted dataset created: NO\nTraining authorized: NO',flush=True)
    print('Audit report SHA:',report_sha,'\nAudit output:',target,flush=True)
    print('NEXT:',report['next_milestone'],flush=True)
    return 2


def run(project,drive,parent,out):
    print('='*110+'\nPAD-Stream V16E-4\nDeterministic Hybrid BL-DP Teacher Dataset Generation and Audit\n'+'='*110,flush=True)
    print('\n'.join(PROHIBITIONS),flush=True)
    gate('NumPy_trapezoid_available',hasattr(np,'trapezoid'),'NumPy '+np.__version__)
    protocol,teachers,bindings,fingerprints,e2=bind_authority(project,drive,parent)
    print('\nCANONICAL DP NUMERICAL REPRODUCTION',flush=True)
    dp_audit=canonical_dp_audit(protocol,teachers['DP'],e2)
    try:
        numerical_preflight(protocol,teachers)
        # Both complete passes independently regenerate every array and manifest.
        # Temporary bytes are not accepted or persisted when any audit fails.
        with tempfile.TemporaryDirectory(prefix='v16e4-generation-') as temp:
            first=Path(temp)/'pass1';second=Path(temp)/'pass2';first.mkdir();second.mkdir()
            generate_pass(first,protocol,teachers,bindings,fingerprints,e2,1)
            generate_pass(second,protocol,teachers,bindings,fingerprints,e2,2)
            gate('two_complete_generations_byte_identical',tree_hashes(first)==tree_hashes(second))
            manifest_sha=sha(first/'V16E4_Dataset_Manifest.json')
            summary={'milestone':'V16E-4','status':SUCCESS,'parent_protocol_sha256':PARENTS['protocol'][1],
                     'dataset_manifest_sha256':manifest_sha,'repeat_generation_byte_identical':True,
                     'accepted_dataset_created':True,'training_authorized':False,'checkpoint_creation_authorized':False,
                     'next_milestone':'V16E-5 pre-training protocol and prospective Hybrid10 controlled training after explicit authority'}
            (first/'PAD_Stream_V16E4_Summary.json').write_bytes(encoded(summary))
            handoff=f'''# PAD-Stream V16E-4 — accepted teacher dataset

All frozen source-teacher, canonical DP, 4097/8193 convergence, fan physics,
inventory, family-split, duplicate and two-pass determinism checks passed.
Dataset manifest SHA: {manifest_sha}
Summary SHA: {sha(first/'PAD_Stream_V16E4_Summary.json')}
No neural model, training or checkpoint was created. E3-R1's classical pre-BT
scope remains in force. Full compressible-capillary equivalence is not claimed.
Numerical loss weights, framework and training execution settings still require
a prospectively frozen pre-training protocol. Test cannot select these settings.
'''
            (first/'V16E4_Handoff.md').write_text(handoff,encoding='utf-8')
            publish_tree(first,out)
            print('\nV16E-4 RESULT: PASS\nDataset output:',out,flush=True)
            print('Dataset manifest SHA:',manifest_sha,flush=True)
            print('Summary SHA:',sha(out/'PAD_Stream_V16E4_Summary.json'),flush=True)
            print('Handoff SHA:',sha(out/'V16E4_Handoff.md'),flush=True)
            print('Training authorized: NO',flush=True)
    except NumericalFailure as exc:
        return blocked_report(drive,exc.detail,bindings,fingerprints,dp_audit)
    except AuditError as exc:
        return blocked_report(drive,{'failed_gate':str(exc),'context':{'stage':'generation_or_dataset_audit'},
                                    'teacher_changed':False},bindings,fingerprints,dp_audit)
    return 0


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root',type=Path,default=Path(__file__).resolve().parent)
    parser.add_argument('--drive-root',type=Path,default=Path('/content/drive/MyDrive/PAD_Stream_Compute'))
    parser.add_argument('--parent-dir',type=Path)
    parser.add_argument('--output-dir',type=Path)
    args=parser.parse_args(argv)
    try:
        return run(args.project_root.resolve(),args.drive_root.resolve(),
                   (args.parent_dir or args.drive_root/E3_REL).resolve(),
                   (args.output_dir or args.drive_root/OUT_REL).resolve())
    except (AuditError,OSError,ValueError,KeyError,TypeError,AssertionError,SyntaxError) as exc:
        print('\n[FAIL] V16E-4 did not close:',exc,file=sys.stderr,flush=True)
        print('No accepted dataset or training authority published.',file=sys.stderr,flush=True)
        return 2


if __name__=='__main__':
    sys.exit(main())
