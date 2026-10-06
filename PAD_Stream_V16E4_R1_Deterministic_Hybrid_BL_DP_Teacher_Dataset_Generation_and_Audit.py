#!/usr/bin/env python3
"""PAD-Stream V16E-4-R1: deterministic Hybrid BL-DP teacher dataset generation and audit.

Uses the successful V16E-3-R2 repaired BL teacher adapter while preserving the
unchanged V16E-3-R1 dataset/design contract.  No neural-network training or
checkpoint creation is performed.  Two independent complete generations must be
byte-identical before an accepted dataset is published.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import numpy as np

E3_R1_REL = Path('provenance/hybrid_dp/V16E3_R1_HYBRID_PROTOCOL_FREEZE')
E3_R2_REL = Path('provenance/hybrid_dp/V16E3_R2_NUMERICAL_TEACHER_REPAIR_PROTOCOL')
E2_REL = Path('provenance/hybrid_dp/V16E2_CONTROLLED_8LAYER_DP_REPRODUCTION')
OUT_REL = Path('datasets/hybrid_dp/V16E4_R1_DETERMINISTIC_TEACHER_DATASET')

E3_R1_PARENTS = {
    'protocol': ('V16E3_R1_Hybrid_BL_DP_Protocol.json', '57bcb2e74c68eb77ed8de69d75ddafc00b38d2f3c4e9b884bfc87676160db4a1'),
    'results': ('V16E3_R1_Hybrid_BL_DP_Protocol_Freeze_Results.json', '1b79394c2c15c44e72510f296e364cc8246d1e4e2310aca14534ef248a103acb'),
    'summary': ('PAD_Stream_V16E3_R1_Summary.json', 'b55d5fc2b0f8febc0bcb042678b95aa5b6a5767286630e1dd5ca11f28de2837a'),
    'handoff': ('V16E3_R1_Handoff.md', '253ec8c52dfedbcae5429f7ff6e30a3ea29888870e1fc4db8e9ab5a34fc99c0a'),
}
E3_R2_PARENTS = {
    'protocol': ('V16E3_R2_Numerical_Teacher_Repair_Protocol.json', '282e34c501280a678cbdbd89718a655f3cee97b1c8a1a6d8ee1155cc8f1928ac'),
    'results': ('V16E3_R2_Numerical_Teacher_Repair_Results.json', '2ab57532cec3959f6db7a7e383a4b0b1a5407de71d8269a1e4a5e113a77d7577'),
    'summary': ('PAD_Stream_V16E3_R2_Summary.json', 'c0e28e96cfffbfac75b6783c2319c25172c66c955d27cac7757381e6109277d0'),
    'handoff': ('V16E3_R2_Handoff.md', '0a474465d4444ec56d00b9fc34916f38010e4202d5fd66914f18cfcca4bf8117'),
}
E3_R1_RUNNER = (
    'PAD_Stream_V16E3_Prospective_Hybrid_BL_DP_Teacher_Dataset_Split_Objective_Model_Protocol_Freeze_R1.py',
    '302af914f33711be695bd606ceba954e0dcd3e8765a04704ffc8085631af1571',
)
E3_R2_RUNNER = (
    'PAD_Stream_V16E3_R2_Numerical_Teacher_Repair_Protocol.py',
    'd70e9b0daf6e52b52fa903beb7798e5b74d8fed91093312317f8864b5835a450',
)
ADAPTER = (
    'PAD_Stream_V16E3_R2_Repaired_BL_Teacher.py',
    '640a853fd0775c5efaf2922976d5c3843fa69ce9e5165245daffefdb3d4eac2a',
)
SOURCES = {
    'DP': ('PAD_Stream_CCUS_Physics_Development_v14_Complete_Validation.py', '45c3c8a26ff270df8d28dc6e67ed432a3de86255229f7046f5b0f3d1899d27f6'),
    'Hybrid10': ('PAD_Stream_Dykstra_Parsons_Hybrid_PIRNN_10Param.py', '2606f265d97ef1034a7555384daa79e4b3ddddef7c180b8d9f3fc3aedcc8d02f'),
    'Hybrid12': ('PAD_Stream_Dykstra_Parsons_Hybrid_PIRNN_12Param.py', '21116ddfd67f88585a0fc809075ece00008b09bd1f61536964ff03774ff8aae0'),
}
LF_SHA = {
    'Hybrid10': '65d017e590a500d527fba8f9e07e2dcc66a7bc34e0ad6ce14a44075cb0b8e87c',
    'Hybrid12': '7612e304c387c022f5bfd9937a45deb50d23f96c8efc464b7f5e1c63ea035897',
}
FEATURES10 = ['no', 'nw', 'swc', 'sor', 'mu_w', 'mu_o', 'phi', 'tD', 'xD_star', 'Sw_star']
FEATURES12 = FEATURES10[:7] + ['krw_max', 'kro_max'] + FEATURES10[7:]
DP_DEFINITIONS = ['_fw_se', '_dfw_dse', 'DPLayer', 'DykstraParsons', 'flow_storage_diagram',
                  'layered_flow_storage', 'dykstra_parsons_coefficient', '_probit',
                  '_v14_test_dykstra_parsons_behavior']

MILESTONE = 'V16E-4-R1'
SUCCESS = 'V16E4_R1_R2_REPAIRED_TEACHER_DATASET_GENERATED_AND_FULLY_AUDITED_TRAINING_NOT_AUTHORIZED'
BLOCKED = 'V16E4_R1_BLOCKED_DATASET_OR_NUMERICAL_AUDIT_FAILED_NO_ACCEPTED_DATASET'
NEXT = 'V16E-5 — Pre-Training Manifest Freeze; training remains unauthorized until V16E-5 passes'
PROHIBITIONS = [
    'NO NEURAL-NETWORK TRAINING.',
    'NO CHECKPOINT CREATION.',
    'NO HISTORICAL HYBRID CHECKPOINT CLAIM.',
    'NO SGSim MODIFICATION.',
    'NO POLLOCK/TOF RECOMPUTATION.',
    'NO B4 RETRAINING.',
    'NO OOD REOPENING.',
    'NO ROW-LEVEL SPLITTING.',
    'NO PERMEABILITY CONDITIONING IN THE PI-RNN.',
    'NO PARAMETER-DOMAIN SHRINKAGE OR CASE DROPPING.',
    'NO SPLIT CHANGE OR E3 TOLERANCE RELAXATION.',
    'NO EDIT TO THE HISTORICAL HYBRID SOURCE FILES.',
    'NO TEST-INFORMED MODEL OR TRAINING SELECTION.',
]


class AuditError(RuntimeError):
    pass


class NumericalFailure(AuditError):
    def __init__(self, detail):
        super().__init__(detail['failed_gate'])
        self.detail = detail


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def encoded(obj) -> bytes:
    return (json.dumps(obj, sort_keys=True, indent=2, allow_nan=False, ensure_ascii=False) + '\n').encode('utf-8')


def load_json(path: Path):
    def reject(value):
        raise AuditError('Nonfinite JSON literal: ' + value)
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), parse_constant=reject)


def gate(name, condition, detail=''):
    ok = bool(condition)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f': {detail}' if detail else ''), flush=True)
    if not ok:
        raise AuditError(name + (': ' + detail if detail else ''))


def exact_file(path: Path, wanted: str, label: str) -> str:
    path = Path(path)
    gate(label + '_exists', path.is_file(), str(path))
    actual = sha(path)
    gate(label + '_SHA_exact', actual == wanted, '' if actual == wanted else f'actual {actual}')
    return actual


def source_binding(path: Path, label: str):
    raw = Path(path).read_bytes()
    observed = digest(raw)
    authority = SOURCES[label][1]
    if label == 'DP':
        gate('DP_source_raw_SHA_exact', observed == authority)
        return {'authority_sha256': authority, 'observed_sha256': observed, 'representation': 'raw_exact'}
    gate(label + '_source_representation_SHA_exact', observed in [authority, LF_SHA[label]])
    restored = digest(raw.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
    gate(label + '_source_original_CRLF_SHA_exact', restored == authority)
    return {
        'authority_sha256': authority,
        'observed_sha256': observed,
        'representation': 'original_CRLF' if observed == authority else 'verified_Git_LF',
        'reconstructed_original_sha256': restored,
    }


def extract_dp_teacher(path: Path):
    tree = ast.parse(Path(path).read_text(encoding='utf-8-sig'))
    definitions = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    gate('DP_pure_definitions_present', set(DP_DEFINITIONS) <= set(definitions))
    ns = {'np': np, '__name__': '_v16e4_r1_dp_teacher'}
    module = ast.Module(
        body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)]
             + [definitions[n] for n in DP_DEFINITIONS],
        type_ignores=[],
    )
    exec(compile(ast.fix_missing_locations(module), str(path), 'exec'), ns)
    fingerprints = {n: digest(ast.dump(definitions[n], include_attributes=False).encode('utf-8')) for n in DP_DEFINITIONS}
    return ns, fingerprints


def load_adapter(path: Path):
    exact_file(path, ADAPTER[1], 'R2_adapter_project_copy')
    spec = importlib.util.spec_from_file_location('_v16e4_r1_adapter', path)
    if spec is None or spec.loader is None:
        raise AuditError('Could not load R2 adapter')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    gate('R2_adapter_identity_exact', getattr(module, 'ADAPTER_ID', None) == 'V16E3_R2_STABLE_COREY_ANALYTIC_WELGE_FAN_V1')
    return module


def bind_authority(project: Path, drive: Path):
    print('\nV16E-3-R2 NUMERICAL-TEACHER AUTHORITY', flush=True)
    r2_dir = drive / E3_R2_REL
    for label, (name, wanted) in E3_R2_PARENTS.items():
        exact_file(r2_dir / name, wanted, 'E3_R2_' + label)
    r2_protocol = load_json(r2_dir / E3_R2_PARENTS['protocol'][0])
    r2_results = load_json(r2_dir / E3_R2_PARENTS['results'][0])
    r2_summary = load_json(r2_dir / E3_R2_PARENTS['summary'][0])
    gate('E3_R2_milestone_exact', r2_protocol.get('milestone') == 'V16E-3-R2')
    gate('E3_R2_status_exact', r2_protocol.get('status') == 'V16E3_R2_NUMERICAL_TEACHER_REPAIR_PROTOCOL_FROZEN_E4_RERUN_AUTHORIZED_TRAINING_NOT_AUTHORIZED')
    gate('E3_R2_results_protocol_link', r2_results.get('protocol_sha256') == E3_R2_PARENTS['protocol'][1])
    gate('E3_R2_summary_protocol_link', r2_summary.get('protocol_sha256') == E3_R2_PARENTS['protocol'][1])
    gate('E3_R2_summary_results_link', r2_summary.get('results_sha256') == E3_R2_PARENTS['results'][1])
    gate('E3_R2_repair_frozen', r2_summary.get('numerical_teacher_repair_frozen') is True)
    gate('E3_R2_full_population_shock_qualified', r2_results.get('full_frozen_population_shock_qualified') is True)
    gate('E3_R2_fan_sentinel_qualified', r2_results.get('fan_sentinel_qualified') is True)
    gate('E3_R2_dataset_generation_authorized', r2_summary.get('E4_R1_dataset_generation_authorized') is True
         and r2_protocol['authorization']['E4_R1_dataset_generation_after_success'] is True)
    gate('E3_R2_training_closed', r2_results.get('training_authorized') is False
         and r2_protocol['authorization']['training_authorized'] is False)
    gate('E3_R2_checkpoints_closed', r2_protocol['authorization']['checkpoint_creation_authorized'] is False)
    gate('E3_R2_adapter_SHA_link', r2_results.get('adapter_sha256') == ADAPTER[1]
         and r2_summary.get('adapter_sha256') == ADAPTER[1]
         and r2_protocol['numerical_teacher_repair']['adapter_sha256'] == ADAPTER[1])
    exact_file(project / E3_R2_RUNNER[0], E3_R2_RUNNER[1], 'E3_R2_runner')
    gate('E3_R2_results_runner_link', r2_results.get('runner_sha256') == E3_R2_RUNNER[1])
    exact_file(r2_dir / ADAPTER[0], ADAPTER[1], 'E3_R2_adapter_frozen_copy')

    print('\nV16E-3-R1 DATASET-DESIGN AUTHORITY', flush=True)
    e3_dir = drive / E3_R1_REL
    for label, (name, wanted) in E3_R1_PARENTS.items():
        exact_file(e3_dir / name, wanted, 'E3_R1_' + label)
    protocol = load_json(e3_dir / E3_R1_PARENTS['protocol'][0])
    e3_results = load_json(e3_dir / E3_R1_PARENTS['results'][0])
    gate('E3_R1_parent_link_from_R2', r2_protocol.get('parent_V16E3_R1_protocol_sha256') == E3_R1_PARENTS['protocol'][1])
    gate('E3_R1_runner_results_link', e3_results.get('runner_sha256') == E3_R1_RUNNER[1])
    exact_file(project / E3_R1_RUNNER[0], E3_R1_RUNNER[1], 'E3_R1_runner')
    gate('features10_order_exact', protocol['experiments']['Hybrid10']['features'] == FEATURES10)
    gate('features12_order_exact', protocol['experiments']['Hybrid12']['features'] == FEATURES12)
    gate('population_exact', protocol['dataset_design']['base_families'] == 1000 and protocol['dataset_design']['layers_per_family'] == 8)
    gate('clock_count_exact', len(protocol['dataset_design']['positive_fan_clock_fractions']) == 20)
    gate('fan_grid_exact', protocol['model']['sequence_nodes'] == 201)
    gate('split_exact', protocol['split']['counts_base_families'] == {'train': 700, 'validation': 150, 'internal_test': 150})
    gate('loss_weights_still_unset', protocol['objective']['weights'] is None)
    gate('R2_unchanged_features10', r2_protocol['unchanged_contract']['features10'] == FEATURES10)
    gate('R2_unchanged_features12', r2_protocol['unchanged_contract']['features12'] == FEATURES12)
    gate('R2_unchanged_population', r2_protocol['unchanged_contract']['base_families'] == 1000
         and r2_protocol['unchanged_contract']['layers_per_family'] == 8)
    gate('R2_unchanged_split', r2_protocol['unchanged_contract']['family_split'] == protocol['split'])
    gate('R2_unchanged_tolerances', r2_protocol['qualification']['reuse_E3_E4_tolerances_without_relaxation'] == protocol['E4_required_audits'])
    for key in ['SGSim_modification_authorized', 'Pollock_TOF_recomputation_authorized', 'B4_retraining_authorized', 'OOD_reopening_authorized']:
        gate('R2_' + key + '_false', r2_protocol['authorization'][key] is False)

    print('\nREAD-ONLY SOURCE / ADAPTER AUTHORITY', flush=True)
    bindings = {label: source_binding(project / info[0], label) for label, info in SOURCES.items()}
    adapter = load_adapter(project / ADAPTER[0])
    dp, dp_fingerprints = extract_dp_teacher(project / SOURCES['DP'][0])

    e2_path = drive / E2_REL / 'V16E2_Controlled_8Layer_DP_Reproduction_Results.json'
    e2_wanted = protocol['provenance']['parents']['E2_RESULTS']['sha256']
    exact_file(e2_path, e2_wanted, 'E2_reference_results')
    e2 = load_json(e2_path)
    gate('canonical_rows_match_E2', protocol['benchmarks']['E2_canonical_rows_authoritative'] == e2['canonical_8_layer_table'])

    return protocol, r2_protocol, adapter, dp, bindings, dp_fingerprints, e2


def draw(family, field, layer, bounds):
    lo, hi = bounds
    u = int(digest(f'V16E3_GENERATOR_1604|{family}|{field}|{layer}'.encode('utf-8')), 16) / 2**256
    return float(lo + (hi - lo) * u)


def split_families(ids):
    ids = list(ids)
    if len(ids) != 1000 or len(set(ids)) != len(ids):
        raise AuditError('Frozen population requires 1000 unique family IDs')
    ranked = sorted(ids, key=lambda x: (digest(('V16E3_SPLIT_SEED_1603|' + x).encode('utf-8')), x))
    return {fid: 0 if i < 700 else 1 if i < 850 else 2 for i, fid in enumerate(ranked)}


def family_parameters(protocol, fid, label):
    bounds = protocol['dataset_design']['bounds']
    shared = {k: draw(fid, k, 'shared', bounds[k]) for k in ['no', 'nw', 'sor', 'mu_w_cP', 'mu_o_cP']}
    rows = []
    for i in range(8):
        lid = f'L{i + 1:02d}'
        row = dict(shared)
        row.update({k: draw(fid, k, lid, bounds[k]) for k in ['k_mD', 'h_ft', 'phi', 'swc']})
        row['mu_w'] = row.pop('mu_w_cP')
        row['mu_o'] = row.pop('mu_o_cP')
        if label == 'Hybrid10':
            row.update(protocol['experiments'][label]['fixed_endpoints'])
        else:
            row['krw_max'] = draw(fid, 'krw_max_Hybrid12', lid, bounds['krw_max_Hybrid12'])
            row['kro_max'] = draw(fid, 'kro_max_Hybrid12', lid, bounds['kro_max_Hybrid12'])
        rows.append(row)
    return rows


def canonical_parameters(protocol, label):
    rows = []
    for r in protocol['benchmarks']['E2_canonical_rows_authoritative']:
        p = {
            'no': 2.0, 'nw': 2.0, 'swc': r['Swc'], 'sor': r['Sor'],
            'mu_w': 0.5, 'mu_o': 0.7, 'k_mD': r['k_mD'], 'h_ft': r['h_ft'],
            'phi': r['phi'], 'krw_max': r['krw_max'], 'kro_max': r['kro_max'],
        }
        if label == 'Hybrid10':
            p.update(protocol['experiments'][label]['fixed_endpoints'])
        rows.append(p)
    return rows


def adapter_params(row):
    return {k: row[k] for k in ['no', 'nw', 'swc', 'sor', 'mu_w', 'mu_o', 'krw_max', 'kro_max']}


def numeric_require(ok, name, detail):
    if not ok:
        raise NumericalFailure(dict(detail, failed_gate=name))


def audit_layer(protocol, r2_protocol, adapter, row, context):
    """Full repaired-teacher audit for one frozen layer-parameter set."""
    tol = protocol['E4_required_audits']
    extra = r2_protocol['qualification']['additional_R2_gates']
    xi = np.arange(201, dtype=float) / 200.0
    fractions = np.asarray(protocol['dataset_design']['positive_fan_clock_fractions'], dtype=float)
    p = adapter_params(row)
    span = 1.0 - p['swc'] - p['sor']
    detail = {
        'context': context,
        'physical_parameters': row,
        'movable_saturation_span': span,
        'frozen_tolerances': tol,
        'R2_adapter_sha256': ADAPTER[1],
        'teacher_changed_from_R2': False,
    }

    shocks = {n: adapter.welge_shock(p, scan_nodes=n) for n in [4097, 8193]}
    for n, shock in shocks.items():
        ctx = dict(detail, shock_grid_nodes=n)
        numeric_require(shock['root_count'] == 1, 'exactly_one_physical_Welge_root', ctx)
        numeric_require(np.isfinite(shock['characteristic_speed']) and shock['characteristic_speed'] > 0.0,
                        'positive_finite_shock_speed', ctx)
        numeric_require(p['swc'] < shock['Sw_star'] < 1.0 - p['sor'], 'physical_shock_saturation', ctx)
        numeric_require(abs(shock['characteristic_speed'] - shock['chord_speed']) <= tol['identity_abs_tolerance'],
                        'Welge_tangent_identity', ctx)
        td_max = float(np.max(fractions) / shock['characteristic_speed'])
        numeric_require(td_max - span <= tol['preBT_inventory_abs_tolerance'],
                        'preBT_inventory_feasible_under_saturation_bounds',
                        dict(ctx, maximum_required_tD=td_max, movable_saturation_span=span))

    shock_sw_conv = abs(shocks[4097]['Sw_star'] - shocks[8193]['Sw_star'])
    shock_speed_conv = abs(shocks[4097]['characteristic_speed'] - shocks[8193]['characteristic_speed'])
    numeric_require(shock_sw_conv <= extra['shock_Sw_4097_vs_8193_abs_tolerance'],
                    'R2_shock_saturation_grid_convergence', dict(detail, observed=shock_sw_conv))
    numeric_require(shock_speed_conv <= extra['shock_speed_4097_vs_8193_abs_tolerance'],
                    'R2_shock_speed_grid_convergence', dict(detail, observed=shock_speed_conv))

    fans = {}
    maxima = {
        'shock_sw_convergence': shock_sw_conv,
        'shock_speed_convergence': shock_speed_conv,
        'grid_convergence': 0.0,
        'fan_endpoint': 0.0,
        'characteristic_residual': 0.0,
        'inventory_error': 0.0,
    }
    for n in [4097, 8193]:
        shock = shocks[n]
        y = adapter.fan_profile_from_shock(p, xi, shock, fan_nodes=n).astype(float)
        ctx = dict(detail, fan_grid_nodes=n)
        numeric_require(np.all(np.isfinite(y)), 'fan_finite', ctx)
        numeric_require(np.all(y >= p['swc'] - 1e-7) and np.all(y <= 1.0 - p['sor'] + 1e-7),
                        'saturation_physical_bounds', ctx)
        numeric_require(np.all(np.diff(y) <= 1e-7), 'monotone_fan', ctx)
        endpoint = max(abs(float(y[0]) - (1.0 - p['sor'])), abs(float(y[-1]) - shock['Sw_star']))
        residual = float(np.max(np.abs(adapter.dfw_dsw(y, p)[1:-1] - xi[1:-1] * shock['characteristic_speed'])))
        integral = float(np.trapezoid(y - p['swc'], xi))
        tD = fractions / shock['characteristic_speed']
        inventory_errors = np.abs(fractions * integral - tD)
        inventory = float(np.max(inventory_errors))
        numeric_require(endpoint <= tol['fan_endpoint_abs_tolerance'], 'fan_endpoint_consistency', dict(ctx, observed=endpoint))
        numeric_require(np.isfinite(residual) and residual <= tol['fan_characteristic_abs_residual_tolerance'],
                        'smooth_fan_characteristic_residual', dict(ctx, observed=residual))
        numeric_require(inventory <= tol['preBT_inventory_abs_tolerance'],
                        'preBT_inventory_identity', dict(ctx, observed=inventory))
        maxima['fan_endpoint'] = max(maxima['fan_endpoint'], endpoint)
        maxima['characteristic_residual'] = max(maxima['characteristic_residual'], residual)
        maxima['inventory_error'] = max(maxima['inventory_error'], inventory)
        fans[n] = {'y': y, 'integral': integral, 'tD': tD}

    grid_convergence = float(np.max(np.abs(fans[4097]['y'] - fans[8193]['y'])))
    numeric_require(grid_convergence <= tol['grid_convergence_max_Sw_difference'],
                    'teacher_grid_convergence', dict(detail, observed=grid_convergence))
    maxima['grid_convergence'] = grid_convergence

    reference = fans[4097]
    target = np.broadcast_to(reference['y'][None, :], (fractions.size, xi.size)).copy().astype(np.float32)
    clock_meta = np.column_stack([
        reference['tD'],
        fractions,
        np.full(fractions.size, shocks[4097]['Sw_star'], dtype=float),
    ])
    return {
        'target': target,
        'clock_meta': clock_meta,
        'tD_BT': float(1.0 / shocks[4097]['characteristic_speed']),
        'fan_excess_integrals': np.full(fractions.size, reference['integral'], dtype=float),
        'shock_reference': shocks[4097],
        'shock_audit': shocks[8193],
        'maxima': maxima,
    }


def dp_case(dp, rows, mode):
    return dp['DykstraParsons'](
        *[np.asarray([r[k] for r in rows]) for k in ['k_mD', 'h_ft', 'phi', 'swc']],
        rows[0]['sor'],
        np.asarray([r['krw_max'] for r in rows]),
        np.asarray([r['kro_max'] for r in rows]),
        rows[0]['mu_w'], rows[0]['mu_o'], mode,
    )


def canonical_dp_audit(protocol, dp, e2):
    passed, message, metrics = dp['_v14_test_dykstra_parsons_behavior']()
    gate('source_native_v14_DP_behavior', bool(passed), message)
    rows = canonical_parameters(protocol, 'Hybrid12')
    tol = protocol['E4_required_audits']['identity_abs_tolerance']
    gridinfo = e2['system_response']
    pvi = np.linspace(gridinfo['pvi_grid_start'], gridinfo['pvi_grid_end'], gridinfo['pvi_grid_count'])
    response = {}
    for mode in ['kh', 'kh_mob']:
        case = dp_case(dp, rows, mode)
        rec, wc = case.run(pvi)
        field = 'kh' if mode == 'kh' else 'kh_mob'
        gate('canonical_' + mode + '_recovery_endpoint', abs(float(rec[-1]) - gridinfo[field + '_final_recovery']) <= tol)
        gate('canonical_' + mode + '_watercut_endpoint', abs(float(wc[-1]) - gridinfo[field + '_final_watercut']) <= tol)
        gate('canonical_' + mode + '_rate_closure', abs(float(case.F.sum()) - 1.0) <= tol)
        response[mode] = {'pvi': pvi.tolist(), 'recovery': rec.tolist(), 'watercut': wc.tolist()}
    coeff = dp['dykstra_parsons_coefficient']([r['k_mD'] for r in rows])
    _, _, lorenz = dp['layered_flow_storage']([r['k_mD'] for r in rows], [r['h_ft'] for r in rows], [r['phi'] for r in rows])
    gate('canonical_DP_descriptor_exact', abs(coeff - e2['heterogeneity']['dykstra_parsons_coefficient']) <= tol)
    gate('canonical_Lorenz_descriptor_exact', abs(lorenz - e2['heterogeneity']['layered_lorenz_coefficient']) <= tol)
    return {
        'source_native_DP_behavior': metrics,
        'canonical_E2_DP_response': response,
        'DP_coefficient': float(coeff),
        'Lorenz': float(lorenz),
        'note': 'V14 DP response remains a distinct canonical allocation/aggregation reference; repaired variable-exponent BL labels come from the frozen R2 adapter.',
    }


def merge_maxima(maxima, values):
    for k, v in values.items():
        maxima[k] = max(maxima.get(k, 0.0), float(v))


def numerical_preflight(protocol, r2_protocol, adapter):
    print('NUMERICAL PREFLIGHT: R2 adapter; no bulk arrays allocated.', flush=True)
    maxima = {}
    audited = 0
    for label in ['Hybrid10', 'Hybrid12']:
        for i, row in enumerate(canonical_parameters(protocol, label)):
            a = audit_layer(protocol, r2_protocol, adapter, row,
                            {'population': 'public_canonical_anchor', 'experiment': label, 'layer_id': i + 1})
            merge_maxima(maxima, a['maxima'])
            audited += 1
    row = family_parameters(protocol, 'F000001', 'Hybrid10')[0]
    a = audit_layer(protocol, r2_protocol, adapter, row,
                    {'population': 'known_E4_counterexample', 'family_id': 'F000001', 'experiment': 'Hybrid10', 'layer_id': 1})
    merge_maxima(maxima, a['maxima'])
    audited += 1
    print(f'[PASS] R2 repaired teacher preflight: {audited} parameter sets.', flush=True)
    return {'audited_parameter_sets': audited, 'maxima': maxima}


def prepare_arrays(root, n, dim):
    root.mkdir(parents=True, exist_ok=True)
    shapes = {
        'conditioning': ((n, 2, 8, 20, dim), np.float32),
        'Sw_fan_teacher': ((n, 8, 20, 201), np.float32),
        'transport_states': ((n, 2, 8, 20, 5), np.float64),
        'layer_physics': ((n, 2, 8, 6), np.float64),
        'physical_parameters': ((n, 8, 11), np.float64),
        'DP_descriptors': ((n, 2, 2), np.float64),
        'common_time_system': ((n, 2, 20, 5), np.float64),
    }
    return {
        name: np.lib.format.open_memmap(root / (name + '.npy'), mode='w+', dtype=dtype, shape=shape)
        for name, (shape, dtype) in shapes.items()
    }


def duplicate_check(seen, key, fid, partition, label):
    if key in seen:
        other, other_partition = seen[key]
        if other != fid and other_partition != partition:
            raise AuditError(f'Cross-partition {label} duplicate: {other} and {fid}')
    else:
        seen[key] = (fid, partition)


def generate_pass(root, protocol, r2_protocol, adapter, dp, bindings, dp_fingerprints, e2, pass_number):
    ids = [f'F{i:06d}' for i in range(1000)]
    partitions = split_families(ids)
    counts = {name: sum(v == i for v in partitions.values()) for i, name in enumerate(['train', 'validation', 'internal_test'])}
    gate(f'pass{pass_number}_case_counts_exact', counts == protocol['split']['counts_base_families'])

    xi = np.arange(201, dtype=np.float64) / 200.0
    np.save(root / 'xi.npy', xi, allow_pickle=False)
    np.save(root / 'partition_codes.npy', np.asarray([partitions[fid] for fid in ids], dtype=np.uint8), allow_pickle=False)
    np.save(root / 'family_ids.npy', np.asarray(ids, dtype='U7'), allow_pickle=False)
    arrays = {
        label: prepare_arrays(root / label, 1000, len(FEATURES10 if label == 'Hybrid10' else FEATURES12))
        for label in ['Hybrid10', 'Hybrid12']
    }

    maxima = {}
    audited_layers = 0
    seen_physical = {}
    seen_transport = {}
    started = time.monotonic()
    anchors = {}

    for label in ['Hybrid10', 'Hybrid12']:
        anchor_rows = canonical_parameters(protocol, label)
        ys = []
        shocks = []
        for i, row in enumerate(anchor_rows):
            audited = audit_layer(protocol, r2_protocol, adapter, row,
                                  {'population': 'public_canonical_anchor', 'experiment': label, 'layer_id': i + 1})
            ys.append(audited['target'])
            shocks.append(audited['shock_reference'])
            merge_maxima(maxima, audited['maxima'])
            audited_layers += 1
        np.save(root / (label + '_public_anchor_Sw.npy'), np.asarray(ys), allow_pickle=False)
        anchors[label] = {
            'repaired_shock_reference': shocks,
            'label': 'E2 variable endpoints' if label == 'Hybrid12' else 'separately named fixed-0.8 counterpart',
        }

    print(f'Pass {pass_number}: canonical BL anchors audited; scanning frozen population.', flush=True)
    geo = protocol['dataset_design']['geometry']
    qtot = geo['q_total_reservoir_bbl_day']
    tol = protocol['E4_required_audits']['identity_abs_tolerance']

    for family_index, fid in enumerate(ids):
        family_rows = {label: family_parameters(protocol, fid, label) for label in ['Hybrid10', 'Hybrid12']}
        phys_sig = digest(encoded(family_rows))
        duplicate_check(seen_physical, phys_sig, fid, partitions[fid], 'physical-family')

        for label in ['Hybrid10', 'Hybrid12']:
            rows = family_rows[label]
            arr = arrays[label]
            layer_audits = []

            for i, row in enumerate(rows):
                audited = audit_layer(
                    protocol, r2_protocol, adapter, row,
                    {'population': 'synthetic', 'family_id': fid, 'family_index': family_index,
                     'experiment': label, 'layer_id': i + 1, 'partition_code': partitions[fid]},
                )
                layer_audits.append(audited)
                merge_maxima(maxima, audited['maxima'])
                audited_layers += 1
                arr['Sw_fan_teacher'][family_index, i] = audited['target']
                for y in audited['target']:
                    duplicate_check(seen_transport, digest(y.tobytes()), fid, partitions[fid], 'transport-profile')
                keys = ['no', 'nw', 'swc', 'sor', 'mu_w', 'mu_o', 'phi', 'k_mD', 'h_ft', 'krw_max', 'kro_max']
                arr['physical_parameters'][family_index, i] = [row[k] for k in keys]

            for mode_index, mode in enumerate(['kh', 'kh_mob']):
                case = dp_case(dp, rows, mode)
                F = case.F
                pv = case.PV * geo['width_ft'] * geo['length_ft'] / 5.615
                clock = F * pv.sum() / pv
                movable = pv * np.asarray([1.0 - r['swc'] - r['sor'] for r in rows])
                if abs(float(F.sum()) - 1.0) > tol or np.any(F <= 0.0) or np.any(pv <= 0.0):
                    raise AuditError('DP flow/PV closure failed')
                coeff = dp['dykstra_parsons_coefficient']([r['k_mD'] for r in rows])
                _, _, lorenz = dp['flow_storage_diagram'](pv / F, F)
                if not (0.0 <= coeff <= 1.0 and -tol <= lorenz <= 1.0 + tol):
                    raise AuditError('Nonphysical DP/Lorenz descriptor')
                arr['DP_descriptors'][family_index, mode_index] = [coeff, lorenz]

                bt_days = []
                for i, row in enumerate(rows):
                    info = layer_audits[i]
                    meta = info['clock_meta']
                    td = meta[:, 0]
                    xstar = meta[:, 1]
                    swstar = meta[:, 2]
                    days = td * pv[i] / (F[i] * qtot)
                    bt_day = info['tD_BT'] * pv[i] / (F[i] * qtot)
                    bt_days.append(bt_day)
                    actual_pvi = (F[i] * qtot * days) / pv[i]
                    total_pvi = qtot * days / pv.sum()
                    if np.max(np.abs(actual_pvi - td)) > tol or np.max(np.abs(clock[i] * total_pvi - td)) > tol:
                        raise AuditError('Reservoir clock / local-PVI identity failed')
                    arr['layer_physics'][family_index, mode_index, i] = [row['k_mD'], row['h_ft'], row['phi'], pv[i], F[i], clock[i]]
                    arr['transport_states'][family_index, mode_index, i] = np.column_stack([
                        days, td, xstar, swstar, np.full(20, bt_day),
                    ])
                    names = FEATURES10 if label == 'Hybrid10' else FEATURES12
                    features = np.column_stack([
                        np.full(20, row[k]) if k in row else td if k == 'tD' else xstar if k == 'xD_star' else swstar
                        for k in names
                    ])
                    arr['conditioning'][family_index, mode_index, i] = features.astype(np.float32)

                fractions = np.asarray(protocol['dataset_design']['positive_fan_clock_fractions'])
                common_days = fractions * min(bt_days)
                localtd = F[:, None] * qtot * common_days[None, :] / pv[:, None]
                speeds = np.asarray([1.0 / z['tD_BT'] for z in layer_audits])
                xstar = localtd * speeds[:, None]
                integrals = np.asarray([z['fan_excess_integrals'][9] for z in layer_audits])
                stored = pv[:, None] * xstar * integrals[:, None]
                rf = stored.sum(axis=0) / movable.sum()
                injected = qtot * common_days
                err = np.abs(stored.sum(axis=0) - injected) / pv.sum()
                if np.max(err) > protocol['E4_required_audits']['preBT_inventory_abs_tolerance']:
                    raise AuditError('Common-time aggregate inventory failed')
                arr['common_time_system'][family_index, mode_index] = np.column_stack([
                    common_days, qtot * common_days / pv.sum(), rf, np.zeros(20), np.zeros(20),
                ])

        if family_index % 25 == 0:
            print(f'Pass {pass_number}: families {family_index + 1}/1000; audited layer-parameter sets {audited_layers}; {time.monotonic() - started:.1f}s', flush=True)

    for group in arrays.values():
        for name, array in group.items():
            if not np.all(np.isfinite(array)):
                raise AuditError('Nonfinite dataset array: ' + name)
            array.flush()
    arrays.clear()

    dp_report = canonical_dp_audit(protocol, dp, e2)
    report = {
        'milestone': MILESTONE,
        'status': SUCCESS,
        'E3_R1_dataset_design_protocol_sha256': E3_R1_PARENTS['protocol'][1],
        'E3_R2_numerical_teacher_protocol_sha256': E3_R2_PARENTS['protocol'][1],
        'R2_adapter_sha256': ADAPTER[1],
        'runner_sha256': sha(Path(__file__)),
        'historical_source_bindings': bindings,
        'DP_definition_AST_sha256': dp_fingerprints,
        'family_counts': counts,
        'audited_layer_parameter_sets': audited_layers,
        'expected_audited_layer_parameter_sets': 16016,
        'logical_profiles_per_experiment': 1000 * 2 * 8 * 20,
        'sequence_nodes': 201,
        'maxima': maxima,
        'public_anchors': anchors,
        'DP_canonical_audit': dp_report,
        'duplicate_firewall': 'no cross-partition exact physical-family or saturation-profile duplicates',
        'factorization': 'Sw_fan_teacher[family,layer,time,xi] is shared by allocation modes at the same local transport clock; conditioning and physical clocks retain the mode axis',
        'R2_teacher_executed': True,
        'full_profile_population_certified_here': True,
        'neural_model_created': False,
        'training_authorized': False,
        'checkpoint_creation_authorized': False,
        'post_breakthrough_learned_targets_created': False,
        'full_physics_equivalence_claimed': False,
    }
    gate(f'pass{pass_number}_audited_layer_parameter_set_count_exact', audited_layers == 16016)
    (root / 'V16E4_R1_Numerical_Audit.json').write_bytes(encoded(report))

    cases = [
        {
            'family_id': fid,
            'family_index': i,
            'partition_code': partitions[fid],
            'partition': ['train', 'validation', 'internal_test'][partitions[fid]],
            'descendants': 'all layers, clocks, allocation modes and Hybrid endpoint variants inherit this assignment',
        }
        for i, fid in enumerate(ids)
    ]
    (root / 'V16E4_R1_Case_Manifest.json').write_bytes(encoded(cases))

    schema = {
        'allocation_modes': ['kh', 'kh_mob'],
        'conditioning_feature_order': {'Hybrid10': FEATURES10, 'Hybrid12': FEATURES12},
        'transport_states_columns': ['time_days', 'tD', 'xD_star', 'Sw_star', 'breakthrough_days'],
        'layer_physics_columns': ['k_mD', 'h_ft', 'phi', 'PV_reservoir_bbl', 'F_i', 'clock_per_total_PVI'],
        'physical_parameters_columns': ['no', 'nw', 'swc', 'sor', 'mu_w', 'mu_o', 'phi', 'k_mD', 'h_ft', 'krw_max', 'kro_max'],
        'DP_descriptors_columns': ['static_DP', 'allocation_mode_Lorenz'],
        'common_time_system_columns': ['time_days', 'total_PVI', 'RF', 'WC', 'WOR'],
        'model_inputs_only': ['xi.npy', 'conditioning.npy'],
        'primary_target': 'Sw_fan_teacher.npy',
        'loading': 'np.load(...,allow_pickle=False,mmap_mode="r")',
        'batch_mapping': 'family/mode/layer/time indexes conditioning; family/layer/time indexes Sw_fan_teacher; broadcast xi along batch',
        'units': 'reservoir bbl/day, reservoir bbl, days, feet, mD, cP; Bw=Bo=1',
        'normalization': 'none; raw conditioning as frozen; no fitted statistics',
        'teacher': 'V16E3_R2_STABLE_COREY_ANALYTIC_WELGE_FAN_V1',
        'teacher_sha256': ADAPTER[1],
        'scope': 'classical incompressible pre-BT fan only; no post-BT learned labels',
    }
    (root / 'V16E4_R1_Dataset_Schema.json').write_bytes(encoded(schema))

    inventory = {
        p.relative_to(root).as_posix(): {'sha256': sha(p), 'bytes': p.stat().st_size}
        for p in sorted(root.rglob('*')) if p.is_file()
    }
    manifest = {
        'E3_R1_parent_artifacts': {k: {'filename': v[0], 'sha256': v[1]} for k, v in E3_R1_PARENTS.items()},
        'E3_R2_parent_artifacts': {k: {'filename': v[0], 'sha256': v[1]} for k, v in E3_R2_PARENTS.items()},
        'R2_adapter': {'filename': ADAPTER[0], 'sha256': ADAPTER[1]},
        'artifacts': inventory,
        'runtime': {'python': sys.version.split()[0], 'numpy': np.__version__},
        'deterministic_scope': 'two independent complete generations on the same numerical runtime; no cross-version bitwise claim',
        'neural_training_authorized': False,
    }
    (root / 'V16E4_R1_Dataset_Manifest.json').write_bytes(encoded(manifest))
    return manifest


def tree_hashes(root):
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(Path(root).rglob('*')) if p.is_file()}


def publish_tree(stage, out):
    out = Path(out)
    if out.exists():
        if out.is_dir() and tree_hashes(out) == tree_hashes(stage):
            print('Existing identical E4-R1 output reused.', flush=True)
            return
        raise AuditError('Existing E4-R1 output differs; choose a new --output-dir. Nothing overwritten.')
    out.parent.mkdir(parents=True, exist_ok=True)
    sibling = Path(tempfile.mkdtemp(prefix='.v16e4-r1-publish-', dir=out.parent))
    try:
        for source in sorted(Path(stage).rglob('*')):
            if source.is_file():
                target = sibling / source.relative_to(stage)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
        if tree_hashes(stage) != tree_hashes(sibling):
            raise AuditError('Publication byte verification failed')
        sibling.rename(out)
    finally:
        if sibling.exists():
            shutil.rmtree(sibling)


def blocked_report(drive, detail, preflight=None, dp_audit=None):
    report = {
        'milestone': MILESTONE,
        'status': BLOCKED,
        'E3_R1_parent_artifacts': {k: {'filename': v[0], 'sha256': v[1]} for k, v in E3_R1_PARENTS.items()},
        'E3_R2_parent_artifacts': {k: {'filename': v[0], 'sha256': v[1]} for k, v in E3_R2_PARENTS.items()},
        'R2_adapter_sha256': ADAPTER[1],
        'runner_sha256': sha(Path(__file__)),
        'counterexample_or_failure': detail,
        'preflight': preflight,
        'canonical_DP_audit': dp_audit,
        'accepted_dataset_created': False,
        'partial_generation_published': False,
        'neural_model_created': False,
        'training_authorized': False,
        'checkpoint_creation_authorized': False,
        'parameter_domain_changed': False,
        'split_changed': False,
        'tolerances_changed': False,
        'next_milestone': 'Review V16E-4-R1 blocked audit under frozen R2 authority; no training is authorized.',
    }
    data = encoded(report)
    report_sha = digest(data)
    target = drive / 'provenance/hybrid_dp/V16E4_R1_BLOCKED_DATASET_AUDIT' / report_sha[:16]
    with tempfile.TemporaryDirectory(prefix='v16e4-r1-blocked-') as tmp:
        stage = Path(tmp)
        (stage / 'V16E4_R1_Blocked_Audit.json').write_bytes(data)
        summary = {
            'milestone': MILESTONE,
            'status': BLOCKED,
            'audit_report_sha256': report_sha,
            'accepted_dataset_created': False,
            'training_authorized': False,
            'next_milestone': report['next_milestone'],
        }
        (stage / 'PAD_Stream_V16E4_R1_Blocked_Summary.json').write_bytes(encoded(summary))
        handoff = f'''# PAD-Stream V16E-4-R1 — BLOCKED dataset/numerical audit\n\nNo accepted dataset, neural model or checkpoint was created. The R2 numerical-teacher\nauthority remains frozen. No parameter domain, split or tolerance was changed.\nSee the blocked audit JSON for the exact failing gate/context. Training remains unauthorized.\n\nAudit SHA: {report_sha}\nNEXT: {report['next_milestone']}\n'''
        (stage / 'V16E4_R1_Blocked_Handoff.md').write_text(handoff, encoding='utf-8')
        publish_tree(stage, target)
    print('\n' + '=' * 118 + '\nV16E-4-R1 RESULT: BLOCKED\n' + '=' * 118, flush=True)
    print('Failed gate:', detail.get('failed_gate', 'generation_or_dataset_audit'), flush=True)
    print('Context:', json.dumps(detail.get('context', {}), sort_keys=True), flush=True)
    print('Accepted dataset created: NO', flush=True)
    print('Training authorized: NO', flush=True)
    print('Audit report SHA:', report_sha, flush=True)
    print('Audit output:', target, flush=True)
    return 2


def run(project, drive, out):
    print('=' * 118 + '\nPAD-Stream V16E-4-R1\nDeterministic Hybrid BL-DP Teacher Dataset Generation and Full Audit\n' + '=' * 118, flush=True)
    print('\n'.join(PROHIBITIONS), flush=True)
    gate('NumPy_trapezoid_available', hasattr(np, 'trapezoid'), 'NumPy ' + np.__version__)

    protocol, r2_protocol, adapter, dp, bindings, dp_fingerprints, e2 = bind_authority(project, drive)
    print('\nCANONICAL DP NUMERICAL REPRODUCTION', flush=True)
    dp_audit = canonical_dp_audit(protocol, dp, e2)
    preflight = None
    try:
        preflight = numerical_preflight(protocol, r2_protocol, adapter)
        with tempfile.TemporaryDirectory(prefix='v16e4-r1-generation-') as temp:
            first = Path(temp) / 'pass1'
            second = Path(temp) / 'pass2'
            first.mkdir()
            second.mkdir()
            generate_pass(first, protocol, r2_protocol, adapter, dp, bindings, dp_fingerprints, e2, 1)
            generate_pass(second, protocol, r2_protocol, adapter, dp, bindings, dp_fingerprints, e2, 2)
            gate('two_complete_generations_byte_identical', tree_hashes(first) == tree_hashes(second))

            manifest_sha = sha(first / 'V16E4_R1_Dataset_Manifest.json')
            audit_sha = sha(first / 'V16E4_R1_Numerical_Audit.json')
            summary = {
                'milestone': MILESTONE,
                'status': SUCCESS,
                'E3_R1_dataset_design_protocol_sha256': E3_R1_PARENTS['protocol'][1],
                'E3_R2_numerical_teacher_protocol_sha256': E3_R2_PARENTS['protocol'][1],
                'R2_adapter_sha256': ADAPTER[1],
                'dataset_manifest_sha256': manifest_sha,
                'numerical_audit_sha256': audit_sha,
                'repeat_generation_byte_identical': True,
                'full_profile_population_certified': True,
                'accepted_dataset_created': True,
                'training_authorized': False,
                'checkpoint_creation_authorized': False,
                'next_milestone': NEXT,
            }
            (first / 'PAD_Stream_V16E4_R1_Summary.json').write_bytes(encoded(summary))
            handoff = f'''# PAD-Stream V16E-4-R1 — accepted repaired-teacher dataset\n\nThe exact V16E-3-R1 dataset-design authority and V16E-3-R2 numerical-teacher\nauthority were verified. The frozen R2 adapter was executed across both public\nanchors and every Hybrid10/Hybrid12 synthetic layer-parameter set. Full 4097/8193\nshock/fan convergence, endpoint, characteristic, inventory, physical-bound, family\nsplit, duplicate-firewall and two-pass deterministic-generation checks passed.\n\nDataset manifest SHA: {manifest_sha}\nNumerical audit SHA: {audit_sha}\nSummary SHA: {sha(first / 'PAD_Stream_V16E4_R1_Summary.json')}\nR2 adapter SHA: {ADAPTER[1]}\n\nNo neural model, training or checkpoint was created. The classical incompressible\npre-breakthrough scope remains in force; full compressible-capillary equivalence\nis not claimed. The internal test partition remains sealed from model selection.\nNumerical loss weights, framework, optimizer, learning rate, stopping/checkpoint\nselection rules and any normalization must be frozen prospectively in V16E-5\nbefore training is authorized.\n\nNEXT: {NEXT}\n'''
            (first / 'V16E4_R1_Handoff.md').write_text(handoff, encoding='utf-8')
            publish_tree(first, out)

            print('\n' + '=' * 118 + '\nV16E-4-R1 RESULT: PASS\n' + '=' * 118, flush=True)
            print('Accepted dataset created                     : YES', flush=True)
            print('Full profile population certified            : YES', flush=True)
            print('Two complete generations byte-identical      : YES', flush=True)
            print('Neural training / checkpoint creation        : NO / NO', flush=True)
            print('Dataset output:', out, flush=True)
            print('Dataset manifest SHA:', manifest_sha, flush=True)
            print('Numerical audit SHA:', audit_sha, flush=True)
            print('Summary SHA:', sha(out / 'PAD_Stream_V16E4_R1_Summary.json'), flush=True)
            print('Handoff SHA:', sha(out / 'V16E4_R1_Handoff.md'), flush=True)
            print('NEXT:', NEXT, flush=True)
    except NumericalFailure as exc:
        return blocked_report(drive, exc.detail, preflight, dp_audit)
    except AuditError as exc:
        return blocked_report(
            drive,
            {'failed_gate': str(exc), 'context': {'stage': 'generation_or_dataset_audit'}},
            preflight,
            dp_audit,
        )
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--drive-root', type=Path, default=Path('/content/drive/MyDrive/PAD_Stream_Compute'))
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args(argv)
    try:
        project = args.project_root.resolve()
        drive = args.drive_root.resolve()
        out = (args.output_dir or drive / OUT_REL).resolve()
        return run(project, drive, out)
    except (AuditError, OSError, ValueError, KeyError, TypeError, AssertionError, SyntaxError, ImportError) as exc:
        print('\n[FAIL] V16E-4-R1 did not close:', exc, file=sys.stderr, flush=True)
        print('No accepted dataset or training authority published.', file=sys.stderr, flush=True)
        return 2


if __name__ == '__main__':
    sys.exit(main())
