#!/usr/bin/env python3
"""PAD-Stream V16E-3-R2: prospective numerical-teacher repair protocol freeze.

This milestone responds only to the V16E-4 blocked numerical teacher audit.
It preserves the V16E-3-R1 dataset/model/split/domain contract, binds the exact
blocked E4 evidence, qualifies a separately SHA-bound pure NumPy BL teacher
adapter across the complete frozen population, and freezes that adapter for a
new E4 rerun.  It does not generate the dataset or train a neural network.
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

E3_REL = Path('provenance/hybrid_dp/V16E3_R1_HYBRID_PROTOCOL_FREEZE')
E4_BLOCKED_REL = Path('provenance/hybrid_dp/V16E4_BLOCKED_TEACHER_AUDIT/1dd5b1b26aebc0fe')
R2_REL = Path('provenance/hybrid_dp/V16E3_R2_NUMERICAL_TEACHER_REPAIR_PROTOCOL')

E3_PARENTS = {
    'protocol': ('V16E3_R1_Hybrid_BL_DP_Protocol.json', '57bcb2e74c68eb77ed8de69d75ddafc00b38d2f3c4e9b884bfc87676160db4a1'),
    'results': ('V16E3_R1_Hybrid_BL_DP_Protocol_Freeze_Results.json', '1b79394c2c15c44e72510f296e364cc8246d1e4e2310aca14534ef248a103acb'),
    'summary': ('PAD_Stream_V16E3_R1_Summary.json', 'b55d5fc2b0f8febc0bcb042678b95aa5b6a5767286630e1dd5ca11f28de2837a'),
    'handoff': ('V16E3_R1_Handoff.md', '253ec8c52dfedbcae5429f7ff6e30a3ea29888870e1fc4db8e9ab5a34fc99c0a'),
}
E3_RUNNER = (
    'PAD_Stream_V16E3_Prospective_Hybrid_BL_DP_Teacher_Dataset_Split_Objective_Model_Protocol_Freeze_R1.py',
    '302af914f33711be695bd606ceba954e0dcd3e8765a04704ffc8085631af1571',
)
E4_RUNNER = (
    'PAD_Stream_V16E4_Deterministic_Hybrid_BL_DP_Teacher_Dataset_Generation_and_Audit.py',
    'fe5ad4041793dd81cdcf6c94b71e5e4bae103195ccbad0e322db91aaf24cd0d7',
)
E4_AUDIT = ('V16E4_Blocked_Teacher_Audit.json', '1dd5b1b26aebc0feec4b6129fc4c891fccd3a583dbdf5794e344f93f03d4082d')
ADAPTER = ('PAD_Stream_V16E3_R2_Repaired_BL_Teacher.py', '640a853fd0775c5efaf2922976d5c3843fa69ce9e5165245daffefdb3d4eac2a')

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
SOURCE_BL_FUNCTIONS = ['validate_params', 'calculate_relative_permeability_np', 'fractional_flow_np', 'dfw_dsw_np', 'welge_tangent']

MILESTONE = 'V16E-3-R2'
STATUS = 'V16E3_R2_NUMERICAL_TEACHER_REPAIR_PROTOCOL_FROZEN_E4_RERUN_AUTHORIZED_TRAINING_NOT_AUTHORIZED'
NEXT = 'V16E-4-R1 — Deterministic Hybrid BL-DP Teacher Dataset Generation and Audit using frozen R2 adapter'
PROHIBITIONS = [
    'NO NEURAL-NETWORK TRAINING.',
    'NO CHECKPOINT CREATION.',
    'NO HISTORICAL HYBRID CHECKPOINT CLAIM.',
    'NO SGSim MODIFICATION.',
    'NO POLLOCK/TOF RECOMPUTATION.',
    'NO B4 RETRAINING.',
    'NO OOD REOPENING.',
    'NO PARAMETER-DOMAIN SHRINKAGE.',
    'NO CASE DROPPING.',
    'NO SPLIT CHANGE.',
    'NO E3 TOLERANCE RELAXATION.',
    'NO EDIT TO THE HISTORICAL HYBRID SOURCE FILES.',
    'NO DATASET GENERATION IN R2.',
]


class FreezeError(RuntimeError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def encoded(value) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False, ensure_ascii=False) + '\n').encode('utf-8')


def load_json(path):
    def reject(value):
        raise FreezeError('Nonfinite JSON literal: ' + value)
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), parse_constant=reject)


def gate(name, condition, detail=''):
    ok = bool(condition)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f': {detail}' if detail else ''), flush=True)
    if not ok:
        raise FreezeError(name + (': ' + detail if detail else ''))


def exact_file(path, wanted, label):
    path = Path(path)
    gate(label + '_exists', path.is_file(), str(path))
    actual = sha(path)
    gate(label + '_SHA_exact', actual == wanted, '' if actual == wanted else f'actual {actual}')
    return actual


def bind_hybrid_source(path, label):
    raw = Path(path).read_bytes()
    observed = digest(raw)
    authority = SOURCES[label][1]
    gate(label + '_source_representation_SHA_exact', observed in [authority, LF_SHA[label]])
    restored = digest(raw.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
    gate(label + '_source_original_CRLF_SHA_exact', restored == authority)
    return {
        'authority_sha256': authority,
        'observed_sha256': observed,
        'representation': 'original_CRLF' if observed == authority else 'verified_Git_LF',
        'reconstructed_original_sha256': restored,
    }


def extract_source_teacher(path, expected_fingerprints):
    tree = ast.parse(Path(path).read_text(encoding='utf-8-sig'))
    defs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    gate('source_teacher_functions_present', all(name in defs for name in SOURCE_BL_FUNCTIONS))
    for name in SOURCE_BL_FUNCTIONS:
        observed = digest(ast.dump(defs[name], include_attributes=False).encode('utf-8'))
        if name in expected_fingerprints:
            gate('source_AST_' + name + '_exact', observed == expected_fingerprints[name])
    literals = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ['EPS', 'FT3_PER_BBL', 'REQUIRED_KEYS']:
                    literals[target.id] = ast.literal_eval(node.value)
    gate('source_EPS_exact', literals.get('EPS') == 1e-12)
    ns = {'np': np, '__name__': '_v16e3_r2_source_teacher'}
    ns.update(literals)
    module = ast.Module(
        body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)] + [defs[n] for n in SOURCE_BL_FUNCTIONS],
        type_ignores=[],
    )
    exec(compile(ast.fix_missing_locations(module), str(path), 'exec'), ns)
    return ns


def load_adapter(path):
    exact_file(path, ADAPTER[1], 'R2_adapter')
    spec = importlib.util.spec_from_file_location('_v16e3_r2_adapter', path)
    if spec is None or spec.loader is None:
        raise FreezeError('Could not load R2 adapter')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    gate('R2_adapter_identity_exact', getattr(module, 'ADAPTER_ID', None) == 'V16E3_R2_STABLE_COREY_ANALYTIC_WELGE_FAN_V1')
    return module


def draw(family, field, layer, bounds):
    lo, hi = bounds
    u = int(digest(f'V16E3_GENERATOR_1604|{family}|{field}|{layer}'.encode('utf-8')), 16) / 2**256
    return float(lo + (hi - lo) * u)


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


def source_characterization(teacher, row, n):
    p = {k: row[k] for k in ['no', 'nw', 'swc', 'sor', 'mu_w', 'mu_o', 'krw_max', 'kro_max']}
    grid = np.linspace(p['swc'], 1.0 - p['sor'], int(n))
    df, fw = teacher['dfw_dsw_np'](grid, p)
    star, fwstar, chord, idx = teacher['welge_tangent'](grid, fw, p['swc'])
    speed = float(df[idx])
    return {
        'grid_nodes': int(n), 'shock_index': int(idx), 'Sw_star': float(star),
        'fw_star': float(fwstar), 'chord_speed': float(chord),
        'characteristic_speed': speed,
        'tD_BT': float(1.0 / speed) if np.isfinite(speed) and speed > 0 else None,
    }


def reproduce_blocker(protocol, audit, source_teacher, adapter):
    print('\nE4 BLOCKER REPRODUCTION AND REPAIR', flush=True)
    c = audit['counterexample']
    gate('E4_blocker_gate_exact', c.get('failed_gate') == 'preBT_inventory_impossible_under_saturation_bounds')
    ctx = c.get('context', {})
    gate('E4_blocker_context_exact', ctx.get('experiment') == 'Hybrid10' and ctx.get('family_id') == 'F000001' and ctx.get('layer_id') == 1)
    row = c['physical_parameters']
    source = {str(n): source_characterization(source_teacher, row, n) for n in [200, 4097, 8193]}
    gate('source_blocker_indices_reproduced', source['200']['shock_index'] == 101 and source['4097']['shock_index'] == 1 and source['8193']['shock_index'] == 1)
    gate('source_blocker_extreme_clock_reproduced', source['4097']['tD_BT'] > 1e6 and source['8193']['tD_BT'] > 1e6)
    candidate = qualify_case(protocol, adapter, row, {'population': 'known_E4_counterexample', **ctx})
    gate('R2_repairs_known_E4_counterexample', candidate['max_inventory_error'] <= protocol['E4_required_audits']['preBT_inventory_abs_tolerance'])
    return {'source_reproduction': source, 'repaired_candidate': candidate}


def qualify_case(protocol, adapter, row, context):
    tol = protocol['E4_required_audits']
    xi = np.arange(201, dtype=float) / 200.0
    fractions = np.asarray(protocol['dataset_design']['positive_fan_clock_fractions'], dtype=float)
    p = {k: row[k] for k in ['no', 'nw', 'swc', 'sor', 'mu_w', 'mu_o', 'krw_max', 'kro_max']}
    span = 1.0 - p['swc'] - p['sor']

    shocks = {n: adapter.welge_shock(p, scan_nodes=n) for n in [4097, 8193]}
    for n, s in shocks.items():
        gate_name = f"{context.get('population','case')}_shock" if context.get('population') == 'known_E4_counterexample' else None
        if s['root_count'] != 1:
            raise FreezeError(f"multiple_or_missing_Welge_roots: {context}; grid={n}; roots={s['root_count']}")
        if not (p['swc'] < s['Sw_star'] < 1.0 - p['sor'] and s['characteristic_speed'] > 0.0):
            raise FreezeError(f"invalid_repaired_shock: {context}; grid={n}")
        if abs(s['characteristic_speed'] - s['chord_speed']) > tol['identity_abs_tolerance']:
            raise FreezeError(f"Welge_tangent_identity_failed: {context}; grid={n}")
    shock_sw_conv = abs(shocks[4097]['Sw_star'] - shocks[8193]['Sw_star'])
    shock_speed_conv = abs(shocks[4097]['characteristic_speed'] - shocks[8193]['characteristic_speed'])
    if shock_sw_conv > 1e-10 or shock_speed_conv > 1e-10:
        raise FreezeError(f"shock_grid_convergence_failed: {context}")

    fans = {}
    metrics = {}
    for n in [4097, 8193]:
        shock = shocks[n]
        y = adapter.fan_profile_from_shock(p, xi, shock, fan_nodes=n)
        if not np.all(np.isfinite(y)):
            raise FreezeError(f"nonfinite_repaired_fan: {context}; grid={n}")
        if np.any(y < p['swc'] - 1e-7) or np.any(y > 1.0 - p['sor'] + 1e-7):
            raise FreezeError(f"repaired_fan_bounds_failed: {context}; grid={n}")
        if np.any(np.diff(y) > 1e-7):
            raise FreezeError(f"repaired_fan_monotonicity_failed: {context}; grid={n}")
        endpoint = max(abs(float(y[0]) - (1.0 - p['sor'])), abs(float(y[-1]) - shock['Sw_star']))
        derivative = adapter.dfw_dsw(y, p)
        residual = float(np.max(np.abs(derivative[1:-1] - xi[1:-1] * shock['characteristic_speed'])))
        integral = float(np.trapezoid(y - p['swc'], xi))
        tD = fractions / shock['characteristic_speed']
        xD = fractions
        inventory_errors = np.abs(xD * integral - tD)
        max_inventory = float(np.max(inventory_errors))
        if endpoint > tol['fan_endpoint_abs_tolerance']:
            raise FreezeError(f"repaired_fan_endpoint_failed: {context}; observed={endpoint}")
        if residual > tol['fan_characteristic_abs_residual_tolerance']:
            raise FreezeError(f"repaired_fan_characteristic_failed: {context}; observed={residual}")
        if max_inventory > tol['preBT_inventory_abs_tolerance']:
            raise FreezeError(f"repaired_inventory_failed: {context}; observed={max_inventory}")
        if not (np.all(tD > 0.0) and np.all(tD < shock['tD_BT'])):
            raise FreezeError(f"repaired_preBT_clock_failed: {context}")
        fans[n] = y
        metrics[n] = {
            'fan_endpoint_error': float(endpoint),
            'characteristic_residual': residual,
            'max_inventory_error': max_inventory,
            'shock': shock,
        }

    convergence = float(np.max(np.abs(fans[4097] - fans[8193])))
    if convergence > tol['grid_convergence_max_Sw_difference']:
        raise FreezeError(f"repaired_teacher_grid_convergence_failed: {context}; observed={convergence}")
    return {
        'grid_convergence_max_Sw_difference': convergence,
        'max_fan_endpoint_error': max(metrics[n]['fan_endpoint_error'] for n in metrics),
        'max_characteristic_residual': max(metrics[n]['characteristic_residual'] for n in metrics),
        'max_inventory_error': max(metrics[n]['max_inventory_error'] for n in metrics),
        'shock_Sw_grid_difference': float(shock_sw_conv),
        'shock_speed_grid_difference': float(shock_speed_conv),
        'Sw_star': float(shocks[4097]['Sw_star']),
        'tD_BT': float(shocks[4097]['tD_BT']),
        'movable_saturation_span': float(span),
    }


def merge_maxima(maxima, metrics, context):
    for key in ['grid_convergence_max_Sw_difference', 'max_fan_endpoint_error', 'max_characteristic_residual',
                'max_inventory_error', 'shock_Sw_grid_difference', 'shock_speed_grid_difference']:
        value = float(metrics[key])
        if key not in maxima or value > maxima[key]['value']:
            maxima[key] = {'value': value, 'context': context}


def qualify_shock_only(protocol, adapter, row, context):
    """Fast full-domain gate for the exact E4 failure mechanism."""
    tol = protocol['E4_required_audits']
    fractions = np.asarray(protocol['dataset_design']['positive_fan_clock_fractions'], dtype=float)
    p = {k: row[k] for k in ['no', 'nw', 'swc', 'sor', 'mu_w', 'mu_o', 'krw_max', 'kro_max']}
    span = 1.0 - p['swc'] - p['sor']
    shock = adapter.welge_shock(p, scan_nodes=4097)
    if shock['root_count'] != 1:
        raise FreezeError(f"multiple_or_missing_Welge_roots: {context}; roots={shock['root_count']}")
    if not (p['swc'] < shock['Sw_star'] < 1.0 - p['sor'] and shock['characteristic_speed'] > 0.0):
        raise FreezeError(f"invalid_repaired_shock: {context}")
    tangent_error = abs(shock['characteristic_speed'] - shock['chord_speed'])
    if tangent_error > tol['identity_abs_tolerance']:
        raise FreezeError(f"Welge_tangent_identity_failed: {context}; observed={tangent_error}")
    td_max = float(np.max(fractions) / shock['characteristic_speed'])
    feasibility_excess = td_max - span
    if feasibility_excess > tol['preBT_inventory_abs_tolerance']:
        raise FreezeError(f"repaired_preBT_inventory_feasibility_failed: {context}; excess={feasibility_excess}")
    return {
        'Sw_star': float(shock['Sw_star']),
        'characteristic_speed': float(shock['characteristic_speed']),
        'tD_BT': float(shock['tD_BT']),
        'tangent_identity_error': float(tangent_error),
        'preBT_max_clock_inventory_feasibility_excess': float(feasibility_excess),
    }


def qualify_population(protocol, adapter):
    """Full shock feasibility + deterministic fan sentinel qualification.

    E4-R1 remains responsible for full 16k-layer fan/data certification before
    any dataset is accepted. R2 proves the repaired shock rule is admissible
    across every frozen layer-parameter set and exercises the complete fan audit
    on the public anchors, known blocker, and a deterministic spread of families.
    """
    print('\nR2 FULL FROZEN-POPULATION SHOCK QUALIFICATION', flush=True)
    shock_maxima = {}
    shock_count = 0
    for label in ['Hybrid10', 'Hybrid12']:
        for i, row in enumerate(canonical_parameters(protocol, label), 1):
            ctx = {'population': 'public_canonical_anchor', 'experiment': label, 'layer_id': i}
            m = qualify_shock_only(protocol, adapter, row, ctx)
            shock_count += 1
            for key in ['tangent_identity_error', 'preBT_max_clock_inventory_feasibility_excess']:
                value = float(m[key])
                if key not in shock_maxima or value > shock_maxima[key]['value']:
                    shock_maxima[key] = {'value': value, 'context': ctx}

    for family_index in range(1000):
        fid = f'F{family_index:06d}'
        for label in ['Hybrid10', 'Hybrid12']:
            for i, row in enumerate(family_parameters(protocol, fid, label), 1):
                ctx = {'population': 'synthetic', 'family_id': fid, 'family_index': family_index,
                       'experiment': label, 'layer_id': i}
                m = qualify_shock_only(protocol, adapter, row, ctx)
                shock_count += 1
                for key in ['tangent_identity_error', 'preBT_max_clock_inventory_feasibility_excess']:
                    value = float(m[key])
                    if key not in shock_maxima or value > shock_maxima[key]['value']:
                        shock_maxima[key] = {'value': value, 'context': ctx}
        if family_index % 50 == 0:
            print(f'R2 shock qualification: {family_index + 1}/1000 families; {shock_count} parameter sets.', flush=True)
    gate('R2_full_population_shock_parameter_set_count_exact', shock_count == 16016)

    print('\nR2 FAN / GRID / INVENTORY SENTINEL QUALIFICATION', flush=True)
    fan_maxima = {}
    fan_count = 0
    for label in ['Hybrid10', 'Hybrid12']:
        for i, row in enumerate(canonical_parameters(protocol, label), 1):
            ctx = {'population': 'public_canonical_anchor', 'experiment': label, 'layer_id': i}
            result = qualify_case(protocol, adapter, row, ctx)
            merge_maxima(fan_maxima, result, ctx)
            fan_count += 1
    print('[PASS] Repaired fan qualifies both public eight-layer anchors.', flush=True)

    sentinel_indices = list(range(0, 1000, 50))
    for family_index in sentinel_indices:
        fid = f'F{family_index:06d}'
        for label in ['Hybrid10', 'Hybrid12']:
            for i, row in enumerate(family_parameters(protocol, fid, label), 1):
                ctx = {'population': 'synthetic_R2_fan_sentinel', 'family_id': fid,
                       'family_index': family_index, 'experiment': label, 'layer_id': i}
                result = qualify_case(protocol, adapter, row, ctx)
                merge_maxima(fan_maxima, result, ctx)
                fan_count += 1
        print(f'R2 fan sentinel: {fid}; {fan_count} fan parameter sets.', flush=True)
    gate('R2_fan_sentinel_count_exact', fan_count == 336)
    return {
        'full_population_shock_qualified_parameter_sets': shock_count,
        'shock_maxima': shock_maxima,
        'fan_sentinel_family_indices': sentinel_indices,
        'fan_qualified_parameter_sets': fan_count,
        'fan_maxima': fan_maxima,
        'full_profile_certification_deferred_to_E4_R1': True,
    }

def bind_authority(project, drive):
    parent = drive / E3_REL
    print('\nV16E-3-R1 PARENT AUTHORITY', flush=True)
    for label, (name, wanted) in E3_PARENTS.items():
        exact_file(parent / name, wanted, 'E3_R1_' + label)
    protocol = load_json(parent / E3_PARENTS['protocol'][0])
    results = load_json(parent / E3_PARENTS['results'][0])
    summary = load_json(parent / E3_PARENTS['summary'][0])
    gate('E3_R1_milestone_exact', protocol.get('milestone') == 'V16E-3-R1')
    gate('E3_R1_protocol_results_link', results.get('protocol_sha256') == E3_PARENTS['protocol'][1])
    gate('E3_R1_protocol_summary_link', summary.get('protocol_sha256') == E3_PARENTS['protocol'][1])
    gate('E3_R1_results_summary_link', summary.get('results_sha256') == E3_PARENTS['results'][1])
    gate('E3_R1_dataset_generation_was_authorized', protocol['authorization']['dataset_generation_after_success'] is True)
    gate('E3_R1_training_still_closed', protocol['authorization']['training_authorized'] is False)
    exact_file(project / E3_RUNNER[0], E3_RUNNER[1], 'E3_R1_runner')
    gate('E3_R1_runner_results_link', results.get('runner_sha256') == E3_RUNNER[1])

    # Frozen scientific contract must remain unchanged in R2.
    gate('R2_features10_unchanged', protocol['experiments']['Hybrid10']['features'] == FEATURES10)
    gate('R2_features12_unchanged', protocol['experiments']['Hybrid12']['features'] == FEATURES12)
    gate('R2_population_unchanged', protocol['dataset_design']['base_families'] == 1000 and protocol['dataset_design']['layers_per_family'] == 8)
    gate('R2_clock_count_unchanged', len(protocol['dataset_design']['positive_fan_clock_fractions']) == 20)
    gate('R2_fan_grid_unchanged', protocol['model']['sequence_nodes'] == 201)
    gate('R2_split_unchanged', protocol['split']['counts_base_families'] == {'train': 700, 'validation': 150, 'internal_test': 150})
    gate('R2_loss_weights_remain_unset', protocol['objective']['weights'] is None)
    for key in ['training_authorized', 'checkpoint_creation_authorized', 'SGSim_modification_authorized',
                'Pollock_TOF_recomputation_authorized', 'B4_retraining_authorized', 'OOD_reopening_authorized']:
        gate('R2_parent_' + key + '_false', protocol['authorization'][key] is False)

    print('\nV16E-4 BLOCKED AUDIT AUTHORITY', flush=True)
    exact_file(project / E4_RUNNER[0], E4_RUNNER[1], 'E4_runner')
    audit_dir = drive / E4_BLOCKED_REL
    exact_file(audit_dir / E4_AUDIT[0], E4_AUDIT[1], 'E4_blocked_audit')
    audit = load_json(audit_dir / E4_AUDIT[0])
    gate('E4_blocked_status_exact', audit.get('status') == 'V16E4_BLOCKED_FROZEN_NUMERICAL_TEACHER_AUDIT_FAILED_NO_ACCEPTED_DATASET')
    gate('E4_blocked_runner_link', audit.get('runner_sha256') == E4_RUNNER[1])
    gate('E4_no_accepted_dataset', audit.get('accepted_dataset_created') is False)
    gate('E4_training_not_authorized', audit.get('training_authorized') is False)
    gate('E4_teacher_was_not_changed', audit.get('teacher_changed') is False)
    gate('E4_domain_was_not_changed', audit.get('domain_changed') is False)
    gate('E4_tolerances_were_not_changed', audit.get('tolerances_changed') is False)
    summary_path = audit_dir / 'PAD_Stream_V16E4_Blocked_Summary.json'
    handoff_path = audit_dir / 'V16E4_Blocked_Handoff.md'
    gate('E4_blocked_summary_exists', summary_path.is_file(), str(summary_path))
    gate('E4_blocked_handoff_exists', handoff_path.is_file(), str(handoff_path))
    blocked_summary = load_json(summary_path)
    gate('E4_blocked_summary_audit_link', blocked_summary.get('audit_report_sha256') == E4_AUDIT[1])

    print('\nREAD-ONLY HISTORICAL SOURCE AUTHORITY', flush=True)
    exact_file(project / SOURCES['DP'][0], SOURCES['DP'][1], 'DP_source')
    bindings = {'DP': {'authority_sha256': SOURCES['DP'][1], 'observed_sha256': SOURCES['DP'][1], 'representation': 'raw_exact'}}
    for label in ['Hybrid10', 'Hybrid12']:
        exact_file(project / SOURCES[label][0], sha(project / SOURCES[label][0]), label + '_source_observed')
        bindings[label] = bind_hybrid_source(project / SOURCES[label][0], label)
    source_teacher = extract_source_teacher(
        project / SOURCES['Hybrid10'][0],
        protocol['provenance']['source_evidence']['Hybrid10']['teacher_function_ast_sha256'],
    )
    return protocol, audit, bindings, {
        'blocked_summary_sha256': sha(summary_path),
        'blocked_handoff_sha256': sha(handoff_path),
    }, source_teacher


def build_protocol(parent, evidence):
    return {
        'schema_version': 1,
        'milestone': MILESTONE,
        'status': STATUS,
        'scope': 'prospective numerical-teacher repair only; all other V16E-3-R1 scientific, dataset, split, model and objective contracts remain unchanged',
        'parent_V16E3_R1_protocol_sha256': E3_PARENTS['protocol'][1],
        'blocking_V16E4_audit_sha256': E4_AUDIT[1],
        'historical_sources_modified': False,
        'unchanged_contract': {
            'features10': parent['experiments']['Hybrid10']['features'],
            'features12': parent['experiments']['Hybrid12']['features'],
            'base_families': parent['dataset_design']['base_families'],
            'layers_per_family': parent['dataset_design']['layers_per_family'],
            'parameter_bounds': parent['dataset_design']['bounds'],
            'sampling': parent['dataset_design']['sampling'],
            'family_ids': parent['dataset_design']['family_ids'],
            'positive_fan_clock_fractions': parent['dataset_design']['positive_fan_clock_fractions'],
            'fan_sequence_nodes': parent['model']['sequence_nodes'],
            'family_split': parent['split'],
            'objective': parent['objective'],
            'Hybrid10_fixed_endpoints': parent['experiments']['Hybrid10']['fixed_endpoints'],
            'Hybrid12_endpoint_rule': parent['experiments']['Hybrid12']['endpoints'],
            'teacher_scope': parent['scope']['transport_regime'],
            'target': parent['scope']['target'],
        },
        'numerical_teacher_repair': {
            'adapter_filename': ADAPTER[0],
            'adapter_sha256': ADAPTER[1],
            'adapter_id': 'V16E3_R2_STABLE_COREY_ANALYTIC_WELGE_FAN_V1',
            'physics_changed': False,
            'numerical_implementation_changed': True,
            'fractional_flow': 'same incompressible Corey mobility physics evaluated as lambda_w/(lambda_w+lambda_o); removes the source EPS perturbation of kro/(krw+EPS) near Swc',
            'derivative': 'closed-form analytic derivative of the same Corey fractional-flow law',
            'shock_rule': 'bracket all positive-to-negative roots of dfw/ds - fw/s = 0; bisection refinement; choose root with largest physical secant speed; full frozen domain must qualify with exactly one root',
            'shock_scan_nodes_reference': 4097,
            'shock_scan_nodes_audit': 8193,
            'shock_bisection_iterations': 64,
            'fan_rule': 'self-similar characteristic inversion on Sw in [Sw_star,1-Sor] using xi=dfw/dSw / shock_speed, then linear interpolation to the unchanged 201-node xi grid',
            'fan_nodes_reference': 4097,
            'fan_nodes_audit': 8193,
            'endpoint_semantics': {'xi_0': 'Sw=1-Sor', 'xi_1': 'Sw=Sw_star'},
            'clock_semantics': 'tD=fraction/shock_speed and xD_star=fraction for unchanged 20 positive pre-BT fractions',
        },
        'qualification': {
            'required_population': 'shock feasibility on both public anchors plus all 1000 frozen synthetic families (16016 layer-parameter sets); complete fan/grid/inventory audit on both public anchors plus 20 deterministic sentinel families; E4-R1 retains full-profile certification authority',
            'reuse_E3_E4_tolerances_without_relaxation': parent['E4_required_audits'],
            'additional_R2_gates': {
                'exactly_one_Welge_root_per_parameter_set': True,
                'shock_Sw_4097_vs_8193_abs_tolerance': 1e-10,
                'shock_speed_4097_vs_8193_abs_tolerance': 1e-10,
            },
            'known_counterexample_must_be_repaired': {'family_id': 'F000001', 'experiment': 'Hybrid10', 'layer_id': 1},
            'failure_policy': 'abort R2; do not publish a successful repair freeze; do not shrink domain, drop cases, change split or relax E3 tolerances',
        },
        'authorization': {
            'dataset_generation_in_R2': False,
            'E4_R1_dataset_generation_after_success': True,
            'training_authorized': False,
            'checkpoint_creation_authorized': False,
            'historical_checkpoint_claimed': False,
            'SGSim_modification_authorized': False,
            'Pollock_TOF_recomputation_authorized': False,
            'B4_retraining_authorized': False,
            'OOD_reopening_authorized': False,
        },
        'evidence_links': evidence,
        'prohibitions': PROHIBITIONS,
        'next_milestone': NEXT,
    }


def commit_outputs(out, payloads):
    out = Path(out)
    if out.exists():
        if not out.is_dir() or set(p.name for p in out.iterdir()) != set(payloads):
            raise FreezeError('Existing R2 output differs; choose a new --output-dir. Nothing overwritten.')
        if not all((out / name).read_bytes() == data for name, data in payloads.items()):
            raise FreezeError('Existing R2 output bytes differ; choose a new --output-dir. Nothing overwritten.')
        print('Existing identical R2 freeze reused.', flush=True)
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.v16e3-r2-', dir=out.parent))
    try:
        for name, data in payloads.items():
            with (staging / name).open('xb') as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        staging.rename(out)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def run(project, drive, out):
    print('=' * 118 + '\nPAD-Stream V16E-3-R2\nNumerical-Teacher Repair Protocol Freeze\n' + '=' * 118, flush=True)
    print('\n'.join(PROHIBITIONS), flush=True)
    gate('NumPy_trapezoid_available', hasattr(np, 'trapezoid'), 'NumPy ' + np.__version__)
    protocol, audit, bindings, blocked_files, source_teacher = bind_authority(project, drive)
    adapter = load_adapter(project / ADAPTER[0])

    blocker = reproduce_blocker(protocol, audit, source_teacher, adapter)
    qualification = qualify_population(protocol, adapter)

    evidence = {
        'E3_R1_artifacts': {k: {'filename': v[0], 'sha256': v[1]} for k, v in E3_PARENTS.items()},
        'E4_blocked_audit': {'path': str(E4_BLOCKED_REL / E4_AUDIT[0]), 'sha256': E4_AUDIT[1]},
        'E4_blocked_companion_files': blocked_files,
        'historical_source_bindings': bindings,
        'reproduced_blocker': blocker,
    }
    r2_protocol = build_protocol(protocol, evidence)
    protocol_bytes = encoded(r2_protocol)

    results = {
        'milestone': MILESTONE,
        'status': STATUS,
        'protocol_sha256': digest(protocol_bytes),
        'runner_sha256': sha(Path(__file__)),
        'adapter_sha256': ADAPTER[1],
        'qualification': qualification,
        'known_counterexample': blocker,
        'full_frozen_population_shock_qualified': qualification['full_population_shock_qualified_parameter_sets'] == 16016,
        'fan_sentinel_qualified': qualification['fan_qualified_parameter_sets'] == 336,
        'historical_sources_modified': False,
        'dataset_generated_here': False,
        'training_authorized': False,
        'checkpoint_creation_authorized': False,
        'runtime': {'python': sys.version.split()[0], 'numpy': np.__version__},
        'next_milestone': NEXT,
    }
    results_bytes = encoded(results)
    summary = {
        'milestone': MILESTONE,
        'status': STATUS,
        'protocol_sha256': digest(protocol_bytes),
        'results_sha256': digest(results_bytes),
        'adapter_sha256': ADAPTER[1],
        'blocked_E4_audit_sha256': E4_AUDIT[1],
        'numerical_teacher_repair_frozen': True,
        'full_frozen_population_shock_qualified': True,
        'fan_sentinel_qualified': True,
        'dataset_generated_here': False,
        'E4_R1_dataset_generation_authorized': True,
        'training_authorized': False,
        'checkpoint_creation_authorized': False,
        'next_milestone': NEXT,
    }
    summary_bytes = encoded(summary)
    handoff = f'''# PAD-Stream V16E-3-R2 — Numerical Teacher Repair Protocol Freeze

The exact V16E-3-R1 authority and exact blocked V16E-4 audit were verified.
The historical Hybrid10/Hybrid12 source files remain unchanged and SHA-bound.
R2 freezes a separate repaired BL teacher adapter with SHA `{ADAPTER[1]}`.

The repair changes numerical implementation only: stable Corey mobility-form
fractional flow, analytic derivative, bracketed Welge tangent root, and
self-similar characteristic fan inversion. The E3-R1 parameter domain, 1000
families, eight layers, feature vectors, 20 clocks, 201 xi nodes, family split,
objectives and all E4 numerical tolerances remain unchanged.

The F000001 / Hybrid10 / layer-1 counterexample was reproduced under the source
teacher and repaired under the frozen adapter. Both public anchors and every frozen Hybrid10/Hybrid12 layer-parameter set
passed the repaired shock-feasibility gate. The complete fan/grid/inventory
audit also passed both anchors and 20 deterministic sentinel families. Full
profile certification remains the responsibility of E4-R1 before any dataset
is accepted. No dataset, neural model or checkpoint was created.
Training remains unauthorized.

Protocol SHA: {digest(protocol_bytes)}
Results SHA: {digest(results_bytes)}
Summary SHA: {digest(summary_bytes)}
Adapter SHA: {ADAPTER[1]}
Blocked E4 audit SHA: {E4_AUDIT[1]}

NEXT: {NEXT}
'''.encode('utf-8')

    adapter_bytes = (project / ADAPTER[0]).read_bytes()
    payloads = {
        'V16E3_R2_Numerical_Teacher_Repair_Protocol.json': protocol_bytes,
        'V16E3_R2_Numerical_Teacher_Repair_Results.json': results_bytes,
        'PAD_Stream_V16E3_R2_Summary.json': summary_bytes,
        'V16E3_R2_Handoff.md': handoff,
        ADAPTER[0]: adapter_bytes,
    }
    commit_outputs(out, payloads)

    print('\n' + '=' * 118 + '\nV16E-3-R2 RESULT: PASS\n' + '=' * 118, flush=True)
    print('Historical Hybrid source files modified        : NO', flush=True)
    print('Parameter domain / split / tolerances changed  : NO / NO / NO', flush=True)
    print('Known E4 counterexample repaired               : YES', flush=True)
    print('Full frozen population shock-qualified         : YES (16016 parameter sets)', flush=True)
    print('Fan/grid/inventory sentinel qualified           : YES (336 parameter sets)', flush=True)
    print('Dataset generated / training authorized        : NO / NO', flush=True)
    for name, data in payloads.items():
        print(f'{name} SHA: {digest(data)}', flush=True)
    print('Output:', out, flush=True)
    print('NEXT:', NEXT, flush=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--drive-root', type=Path, default=Path('/content/drive/MyDrive/PAD_Stream_Compute'))
    parser.add_argument('--output-dir', type=Path, help='Default: V16E3_R2_NUMERICAL_TEACHER_REPAIR_PROTOCOL under --drive-root')
    args = parser.parse_args(argv)
    try:
        project = args.project_root.resolve()
        drive = args.drive_root.resolve()
        out = (args.output_dir or drive / R2_REL).resolve()
        return run(project, drive, out)
    except (FreezeError, OSError, ValueError, KeyError, TypeError, SyntaxError, ImportError) as exc:
        print('\n[FAIL] V16E-3-R2 did not close:', exc, file=sys.stderr, flush=True)
        print('No successful R2 freeze was published by this invocation.', file=sys.stderr, flush=True)
        return 2


if __name__ == '__main__':
    sys.exit(main())
