#!/usr/bin/env python3
"""PAD-Stream V16E-3: prospective protocol freeze; standard library only.

Place beside the recovered project sources and run in PyCharm or Colab.
No source module is imported or executed. No dataset/model/checkpoint is made.
Missing or changed authority aborts before any successful freeze is written.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile

E2_SUBDIR = Path('provenance/hybrid_dp/V16E2_CONTROLLED_8LAYER_DP_REPRODUCTION')
E3_SUBDIR = Path('provenance/hybrid_dp/V16E3_HYBRID_PROTOCOL_FREEZE')
PARENTS = {
    'E2_RESULTS': ('V16E2_Controlled_8Layer_DP_Reproduction_Results.json',
                   'b77c35a00ea01616e7f6bd258d16c8fcc3852310d02aa836780b3199e4524248'),
    'E2_SUMMARY': ('PAD_Stream_V16E2_Summary.json',
                   '5d134986c12ed2ed484b42f33dc23e67a1896f1952df9b7f19d150ad0cbca291'),
    'E2_HANDOFF': ('V16E2_Handoff.md',
                   'f716642efc8cf506ef97939df01f757ec017481f38d2c8ebe2e61440fa0bd4e5'),
}
SOURCES = {
    'DP': ('PAD_Stream_CCUS_Physics_Development_v14_Complete_Validation.py',
           '45c3c8a26ff270df8d28dc6e67ed432a3de86255229f7046f5b0f3d1899d27f6'),
    'Hybrid10': ('PAD_Stream_Dykstra_Parsons_Hybrid_PIRNN_10Param.py',
                 '2606f265d97ef1034a7555384daa79e4b3ddddef7c180b8d9f3fc3aedcc8d02f'),
    'Hybrid12': ('PAD_Stream_Dykstra_Parsons_Hybrid_PIRNN_12Param.py',
                 '21116ddfd67f88585a0fc809075ece00008b09bd1f61536964ff03774ff8aae0'),
}
E2_STATUS = ('V16E_CONTROLLED_8LAYER_DP_PHYSICS_REPRODUCED_'
             'PROSPECTIVE_HYBRID_BL_DP_INTERFACE_FROZEN_'
             'HISTORICAL_HYBRID_NOT_CLAIMED_'
             'PROSPECTIVE_TEACHER_PROTOCOL_DESIGN_AUTHORIZED_TRAINING_NOT_YET_AUTHORIZED')
STATUS = ('V16E3_PROSPECTIVE_HYBRID_BL_DP_CLASSICAL_FAN_TEACHER_DATASET_SPLIT_'
          'OBJECTIVE_MODEL_PROTOCOL_FROZEN_DATASET_GENERATION_AUTHORIZED_TRAINING_NOT_AUTHORIZED')
NEXT = 'V16E-4 — Deterministic Hybrid BL-DP Teacher Dataset Generation and Audit'
FEATURES10 = ['no', 'nw', 'swc', 'sor', 'mu_w', 'mu_o', 'phi', 'tD', 'xD_star', 'Sw_star']
FEATURES12 = FEATURES10[:7] + ['krw_max', 'kro_max'] + FEATURES10[7:]
CANONICAL = {
    'k_mD': [174., 103., 487., 100., 141., 904., 1223., 160.],
    'h_ft': [50., 48., 54., 44., 42., 48., 50., 40.],
    'phi': [0.22, 0.18, 0.21, 0.15, 0.20, 0.21, 0.20, 0.20],
    'Swc': [0.37, 0.41, 0.35, 0.42, 0.39, 0.34, 0.32, 0.42],
    'Sor': [0.2] * 8,
    'krw_max': [0.05, 0.15, 0.20, 0.33, 0.20, 0.30, 0.40, 0.17],
    'kro_max': [0.40, 0.45, 0.55, 0.70, 0.30, 0.65, 0.80, 0.60],
}
TEACHER_FUNCTIONS = ['calculate_relative_permeability_np', 'fractional_flow_np',
                     'dfw_dsw_np', 'welge_tangent', 'calculate_x_sw',
                     'profile_at_time', 'build_fan_profiles', 'breakthrough_time_days']
PROHIBITIONS = [
    'NO NEURAL-NETWORK TRAINING.', 'NO CHECKPOINT CREATION.',
    'NO HISTORICAL CHECKPOINT CLAIM.', 'NO SGSim MODIFICATION.',
    'NO POLLOCK/TOF RECOMPUTATION.', 'NO B4 RETRAINING.', 'NO OOD REOPENING.',
    'NO DATASET ROW-LEVEL SPLITTING.', 'NO PERMEABILITY CONDITIONING IN THE PI-RNN.',
    'NO MODEL SELECTION FROM TEST DATA.',
]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def encoded(value) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False,
                       ensure_ascii=False) + '\n').encode('utf-8')


class FreezeError(RuntimeError):
    pass


class Gates:
    def __init__(self):
        self.items = {}

    def check(self, name, condition, detail=''):
        ok = bool(condition)
        self.items[name] = {'passed': ok, 'detail': detail}
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f': {detail}' if detail else ''))
        if not ok:
            raise FreezeError(name + (': ' + detail if detail else ''))


def bind_file(gates, label, path, expected):
    gates.check(label + '_exists', path.is_file(), str(path))
    actual = sha(path)
    gates.check(label + '_SHA_exact', actual == expected,
                '' if actual == expected else f'expected {expected}; actual {actual}')


def read_json(path):
    def reject(value):
        raise FreezeError('Nonfinite JSON literal: ' + value)
    return json.loads(path.read_text(encoding='utf-8-sig'), parse_constant=reject)


def functions(tree):
    # Source contains redefinitions. The final top-level definition is effective.
    return {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def assigned_literal(node, name):
    for child in ast.walk(node):
        if isinstance(child, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name
                                                 for t in child.targets):
            try:
                return ast.literal_eval(child.value)
            except (ValueError, TypeError):
                continue
    raise FreezeError('Missing literal assignment: ' + name)


def feature_order(node, array_name):
    for child in ast.walk(node):
        if isinstance(child, ast.Assign) and any(isinstance(t, ast.Name) and t.id == array_name
                                                 for t in child.targets):
            if not isinstance(child.value, ast.Call):
                break
            return [ast.unparse(x) for x in child.value.args[0].elts[0].elts]
    raise FreezeError('Feature vector not found: ' + array_name)


def inspect_hybrid(path, identity, gates):
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    fn = functions(tree)
    gates.check(identity + '_teacher_definitions_present', all(k in fn for k in TEACHER_FUNCTIONS))
    gates.check(identity + '_inference_definition_present', 'predict_saturation_profile_pirnn' in fn)
    dimension = 10 if identity == 'Hybrid10' else 12
    features = FEATURES10 if dimension == 10 else FEATURES12
    expected_expr = ['shared.no', 'shared.nw', 'layer.swc', 'shared.sor', 'shared.mu_w',
                     'shared.mu_o', 'layer.phi']
    if dimension == 12:
        expected_expr += ['layer.krw_max', 'layer.kro_max']
    expected_expr += ['t_D', 'xD_star', 'Sw_star']
    actual = feature_order(fn['predict_saturation_profile_pirnn'], 'p' + str(dimension))
    gates.check(identity + '_dimension_exact', len(actual) == dimension)
    gates.check(identity + '_order_exact', actual == expected_expr)
    gates.check(identity + '_absolute_permeability_excluded', all('k_md' not in x for x in actual))
    model = fn['load_pirnn_model']
    defaults = {k: assigned_literal(model, k) for k in
                ['seq_length', 'param_dim', 'hidden_units', 'num_layers']}
    gates.check(identity + '_model_param_dim_exact', defaults['param_dim'] == dimension)
    calls = {ast.unparse(n.func) for n in ast.walk(model) if isinstance(n, ast.Call)}
    gates.check(identity + '_recurrent_family_source_bound',
                {'tf.keras.layers.LSTM', 'tf.keras.layers.RepeatVector',
                 'tf.keras.layers.Concatenate', 'tf.keras.layers.TimeDistributed',
                 'tf.math.sigmoid'} <= calls)
    evidence = {k: digest(ast.dump(fn[k], include_attributes=False).encode('utf-8'))
                for k in TEACHER_FUNCTIONS + ['load_pirnn_model', 'predict_saturation_profile_pirnn']}
    raw_table = assigned_literal(fn['build_layers_from_formation'], 'data')
    return {'filename': path.name, 'sha256': sha(path), 'feature_order': features,
            'source_feature_expressions': actual, 'source_model_defaults': defaults,
            'teacher_function_ast_sha256': evidence, 'legacy_table_for_comparison_only': raw_table}


def validate_parent(results, summary, gates):
    for label, obj in [('E2_results', results), ('E2_summary', summary)]:
        gates.check(label + '_milestone_exact', obj.get('milestone') == 'V16E-2')
        gates.check(label + '_status_exact', obj.get('status') == E2_STATUS)
        gates.check(label + '_DP_source_exact', obj.get('DP_source_sha256') == SOURCES['DP'][1])
    requirements = {'results_sha256': PARENTS['E2_RESULTS'][1],
                    'source_native_DP_behavior_passed': True, 'DP_8_layer_physics_reproduced': True,
                    'Hybrid_BL_DP_interface_frozen': True, 'historical_Hybrid_DP_claimed': False,
                    'prospective_Hybrid_protocol_design_authorized': True, 'training_authorized': False}
    for key, value in requirements.items():
        got = summary.get(key)
        gates.check('E2_summary_' + key, got == value and type(got) is type(value))
    forward = results.get('forward_decision', {})
    gates.check('E2_design_authority_exact', forward.get('prospective_Hybrid_teacher_protocol_design_authorized') is True)
    gates.check('E2_training_authority_closed', forward.get('training_authorized_now') is False)
    contract = results.get('hybrid_contract', {})
    gates.check('E2_historical_checkpoint_not_claimed',
                contract.get('provenance', {}).get('historical_Hybrid_DP_claim_permitted') is False)
    gates.check('E2_full_physics_lineage_preserved',
                contract.get('exact_teacher', {}).get('BL_transport_lineage') ==
                'B4B full compressible-capillary BL + reconciled Pollock/TOF adapter')
    rows = results.get('canonical_8_layer_table', [])
    gates.check('E2_canonical_eight_layers_exact', len(rows) == 8)
    gates.check('E2_canonical_layer_order_exact', [r.get('layer') for r in rows] == list(range(1, 9)))
    for key, expected in CANONICAL.items():
        actual = [r.get(key) for r in rows]
        gates.check('E2_canonical_' + key + '_exact', actual == expected)
    return rows


def split_families(family_ids):
    """Pure protocol utility; called by E4 after a complete case manifest exists.

    Input is one ID per physical family. Layers/times/variants reuse its split.
    Exact 70/15/15 counts require a population divisible by 20.
    """
    ids = list(family_ids)
    if not ids or len(set(ids)) != len(ids) or len(ids) % 20:
        raise FreezeError('Unique family IDs and a population divisible by 20 required')
    if any(not isinstance(x, str) or not x for x in ids):
        raise FreezeError('Family IDs must be nonempty strings')
    ranked = sorted(ids, key=lambda x: (digest(('V16E3_SPLIT_SEED_1603|' + x).encode('utf-8')), x))
    ntrain, nval = len(ids) * 70 // 100, len(ids) * 15 // 100
    return {x: ('train' if i < ntrain else 'validation' if i < ntrain + nval else 'internal_test')
            for i, x in enumerate(ranked)}


def build_protocol(rows, evidence):
    """Design-only JSON. Values below are prospective choices, not old training facts."""
    bounds = {'no': [2., 4.], 'nw': [2., 4.], 'swc': [0.20, 0.45],
              'sor': [0.10, 0.30], 'mu_w_cP': [0.30, 1.], 'mu_o_cP': [0.50, 5.],
              'phi': [0.15, 0.25], 'k_mD': [50., 1250.], 'h_ft': [20., 60.],
              'krw_max_Hybrid12': [0.05, 0.80], 'kro_max_Hybrid12': [0.30, 0.80]}
    return {
        'schema_version': 1, 'milestone': 'V16E-3', 'status': STATUS,
        'scope': {
            'experiment': 'NEW_V16E_PROSPECTIVE_HYBRID_BL_DP_CLASSICAL_FAN',
            'transport_regime': 'incompressible immiscible Corey/Welge BL; no gravity or capillarity in this teacher',
            'target': 'left rarefaction fan saturation on xi = x_D / xD_star',
            'sequence_axis': 'space within a profile, not physical time',
            'time_domain': 'positive pre-breakthrough local clocks only; 0 < xD_star < 1',
            'integration_lineage_preserved': 'B4B full compressible-capillary BL + reconciled Pollock/TOF adapter',
            'full_physics_equivalence_claimed': False,
            'full_physics_extension_requires': 'a new feature/residual/teacher protocol with pressure, compressibility and capillary semantics; these 10/12 features do not establish it',
            'DP_role': 'layered allocation/aggregation authority; SGSim/pressure/Darcy/Pollock retain 3-D authority',
            'learned_transport_role': 'proposal subject to exact physics, inventory and conservative map-back acceptance',
        },
        'provenance': {'parents': {k: {'filename': v[0], 'sha256': v[1]} for k, v in PARENTS.items()},
                       'sources': {k: {'filename': v[0], 'sha256': v[1]} for k, v in SOURCES.items()},
                       'source_evidence': evidence, 'historical_checkpoint_claimed': False},
        'experiments': {
            'Hybrid10': {'experiment_id': 'V16E-HYBRID10-CLASSICAL-FAN-PROSPECTIVE-001',
                         'features': FEATURES10, 'param_dim': 10, 'fixed_endpoints': {'krw_max': 0.8, 'kro_max': 0.8}},
            'Hybrid12': {'experiment_id': 'V16E-HYBRID12-CLASSICAL-FAN-PROSPECTIVE-001',
                         'features': FEATURES12, 'param_dim': 12, 'endpoints': 'layer-specific within frozen bounds'},
        },
        'teacher': {
            'DP': {'authority': 'E2 SHA-bound V14 DykstraParsons', 'modes': ['kh', 'kh_mob'],
                   'identities': ['sum(F_i)=1', 'PVI_i=F_i*(PV_total/PV_i)*PVI_total',
                                  'WC_total=sum(F_i*fw_out_i)',
                                  'RF_total=sum(PV_i*DeltaS_i*RF_i)/sum(PV_i*DeltaS_i)'],
                   'recovery_note': 'E2 classical DP displacement response and BL fan-derived response are distinct teacher quantities; do not require artificial equality'},
            'BL': {'authority': 'final effective definitions in SHA-bound Hybrid10/Hybrid12 source',
                   'functions': TEACHER_FUNCTIONS, 'analytical_basis': 'Corey fractional flow and Welge shock/fan',
                   'implementation': 'finite saturation-grid gradients, tangent selection, interpolation; finite resolution, not a symbolic exact solver',
                   'source_grid_default': 200, 'prospective_reference_grid': 4097,
                   'audit_grid': 8193, 'interpolation': 'ascending fan xi; linear; duplicate xi rejected unless equal saturation within tolerance',
                   'primary_target': 'Sw_fan_teacher',
                   'shock_inputs': 'xD_star and Sw_star supplied by deterministic exact-physics branch at inference as well as training',
                   'shock_not_learned': True,
                   'zero_time': 'excluded from learned fan; exact initial Sw=swc imposed separately',
                   'post_breakthrough': 'excluded until an unclipped outlet/fan teacher extension is derived and audited'},
            'clock_units': {'x_D': 'x/L', 'xi': 'x_D/xD_star', 'tD': 'q_res*t/PV_i, dimensionless',
                            'q_res': 'reservoir volumetric rate; q_total and PV use consistent units',
                            'source_native_tD': 'FT3_PER_BBL*i_w*t_days/(phi*A*x_ip); source profile omits Bw',
                            'source_native_BT': 'breakthrough_time_days uses PV_rb/Bw; not silently identified with profile tD',
                            'prospective_rule': 'Bw=Bo=1 for this incompressible benchmark; no stock-tank conversion; DP PV proportional to phi*h for common footprint',
                            'source_case_adapter': 'A_i=common_width*h_i; x_ip=common_length; i_w is layer reservoir rate in reservoir bbl/day; k remains DP-only'},
            'derived_validation': ['layer_inventory', 'layer_produced_displaced_volume', 'RF', 'WC', 'WOR', 'breakthrough_clocks'],
            'derived_output_scope': 'pre-BT fan supports inventory/recovery; full water-cut evolution and post-BT production remain exact-physics diagnostics or a future teacher extension',
            'WOR_policy': 'undefined/infinite when oil rate is zero; use validity mask, never hide with denominator clipping',
        },
        'benchmarks': {
            'E2_canonical_rows_authoritative': rows,
            'canonical_reference_partition': 'public development/acceptance anchor; outside 70/15/15; never called unseen',
            'Hybrid12_anchor': 'exact E2 layer table with its variable endpoints',
            'Hybrid10_anchor': 'E2 k/h/phi/swc with krw_max=kro_max=0.8; separately named fixed-endpoint counterpart, not E2 exact reproduction',
            'legacy_tables': 'audit differences only; never overwrite E2 from a Hybrid source table',
            'comparison': 'compare both models on shared fixed-0.8 endpoint cases; report variable-endpoint Hybrid12 cases separately',
        },
        'dataset_design': {
            'design_values_are_prospective': True,
            'base_families': 1000, 'layers_per_family': 8,
            'future_N_layer_population': 'requires a subsequent dataset version; eight layers do not limit PAD-Stream architecture',
            'bounds': bounds, 'sampling': 'independent uniform values using deterministic hash draws; no fitted distribution',
            'draw_algorithm': 'u=int(SHA256(UTF8("V16E3_GENERATOR_1604|"+family_id+"|"+field+"|"+layer_id)),16)/2**256; value=lo+(hi-lo)*u',
            'family_ids': 'F000000 through F000999; shared across Hybrid10/12, allocation modes and all variants',
            'shared_per_family': ['no', 'nw', 'sor', 'mu_w_cP', 'mu_o_cP'],
            'layer_specific': ['k_mD', 'h_ft', 'phi', 'swc', 'Hybrid12 krw_max', 'Hybrid12 kro_max'],
            'shared_draw_layer_id': 'shared', 'layer_draw_ids': 'L01 through L08',
            'geometry': {'width_ft': 80., 'length_ft': 2000., 'q_total_reservoir_bbl_day': 1000., 'Bw': 1., 'Bo': 1.},
            'positive_fan_clock_fractions': [0.05 + 0.90 * j / 19 for j in range(20)],
            'clock_selection': 'each fraction times local shock arrival tD_BT=1/fprime(Sw_star); both allocation modes recorded; common physical-time system diagnostics generated separately',
            'schema': {'case_manifest': ['family_id', 'case_id', 'experiment_id', 'allocation_mode', 'physical_parameters', 'units', 'source_sha256'],
                       'profile': ['family_id', 'case_id', 'layer_id', 'time_id', 'partition', 'tD', 'xD_star', 'Sw_star', 'xi', 'conditioning', 'Sw_fan_teacher'],
                       'physics_metadata': ['k_mD', 'h_ft', 'PV_i', 'F_i', 'PVI_i', 'DP', 'Lorenz', 'layer_breakthrough']},
            'network_metadata_firewall': 'only xi and ordered conditioning enter NN; no k, h, F, DP, Lorenz, layer ID or partition channel',
            'normalization': 'xi and raw physical conditioning as in source; bounded output reads raw swc/sor; any later scaling must be separately frozen using TRAIN only',
        },
        'split': {
            'unit': 'complete physical family', 'ratios_percent': [70, 15, 15],
            'counts_base_families': {'train': 700, 'validation': 150, 'internal_test': 150},
            'algorithm': 'sort unique family IDs by (SHA256("V16E3_SPLIT_SEED_1603|"+ID),ID); first 70%, next 15%, remaining test',
            'all_descendants_inherit': ['layers', 'times', 'xi nodes', 'allocation modes', 'endpoint variants', 'rate/permeability rescalings'],
            'duplicate_audit': 'detect identical physical or transport-equivalent profiles across families; abort on cross-partition duplicates; regenerate/re-freeze before training, never silently move rows',
            'train_role': 'parameter fitting and any normalization statistics',
            'validation_role': 'loss/hyperparameter/model selection; final selections locked before internal-test evaluation',
            'test_role': 'sealed dataset partition; teacher-integrity audit allowed, no model selection; one final evaluation per frozen experiment',
            'OOD': 'existing V16 OOD/EXP-CS1 contract unopened; geology0029 never relabeled unseen',
        },
        'model': {
            'family': 'repeat conditioning along xi, concatenate, two LSTM layers, time-distributed Dense(1)',
            'hidden_units': 64, 'layers': 2, 'return_sequences': True,
            'sequence_nodes': 201, 'xi_nodes': 'j/200 for j=0..200',
            'sequence_length_choice': 'new prospective shared 201-node fan grid; not a recovered checkpoint dimension or proof of Pollock/TOF adapter equivalence',
            'source_length_conflict': 'Hybrid10 defaults 112; Hybrid12 loader defaults 143 while inference defaults 145; neither reused as checkpoint authority',
            'output': 'swc+(1-swc-sor)*sigmoid(z)',
            'framework': 'deferred to pre-training execution manifest; mathematical family fixed',
            'checkpoint_policy': 'new identity, source/dataset/protocol/config SHA manifest; no historical relabeling',
        },
        'objective': {
            'structure': 'lambda_data*L_Sw + lambda_bc*L_BC + lambda_front*L_front + lambda_phys*L_phys + lambda_mono*L_mono',
            'L_Sw': 'case-balanced mean squared Sw error, equal layer/time weights within each family',
            'L_BC': 'mean square of (Sw_hat(xi=0)-(1-sor))',
            'L_front': 'mean square of (Sw_hat(xi=1)-Sw_star); analytical shock position remains a supplied coordinate',
            'L_phys': 'fan interior mean square of (fprime(Sw_hat)-xi*xD_star/tD); exclude endpoints and zero-time; Corey derivative in the admissible smooth fan',
            'L_mono': 'mean square positive adjacent increments max(Sw_hat[j+1]-Sw_hat[j],0)',
            'range': 'hard bounded saturation map, not an independent unconstrained output loss',
            'physics_scope': 'self-similar pre-BT incompressible BL fan relation; never a full compressible/capillary or arbitrary time-dependent PDE residual',
            'weights': None, 'weight_policy': 'freeze numerical values/search space on TRAIN/VALIDATION in pre-training protocol; no test-informed tuning',
        },
        'E4_required_audits': {
            'authority': 'verify this protocol/results/summary/handoff SHA before generation; no teacher code module import with top-level side effects',
            'teacher_implementation': 'extract audited pure teacher definitions or reviewed adapter; retain source AST fingerprints; compare source default-resolution and refined teacher on the canonical cases',
            'grid_convergence_max_Sw_difference': 0.002,
            'fan_endpoint_abs_tolerance': 0.002,
            'fan_characteristic_abs_residual_tolerance': 0.005,
            'preBT_inventory_abs_tolerance': 0.005,
            'identity_abs_tolerance': 1e-12,
            'checks': ['finite arrays', 'strict ascending xi', 'physical bounds', 'monotone fan', 'shock and fan endpoint consistency',
                       'all local clocks positive and pre-BT', 'PV/rate closure', 'clock/unit equivalence at Bw=1',
                       'numerical grid convergence', 'pre-BT inventory: xD_star*integral_0^1(Sw-swc)dxi=tD',
                       'case/family leakage firewall', 'transport-equivalent duplicate firewall', 'counts and feature order',
                       'repeated generation produces identical array and manifest hashes'],
            'failure_policy': 'abort; no automatic tolerance/domain changes; any revision needs a new protocol before training',
            'diagnostic_audit_not_model_selection': True,
        },
        'authorization': {'dataset_generation_after_success': True, 'training_authorized': False,
                          'checkpoint_creation_authorized': False, 'historical_checkpoint_claimed': False,
                          'SGSim_modification_authorized': False, 'Pollock_TOF_recomputation_authorized': False,
                          'B4_retraining_authorized': False, 'OOD_reopening_authorized': False,
                          'future_training_requires': 'E4 successful dataset audit plus explicit next-milestone training protocol/authority'},
        'prohibitions': PROHIBITIONS, 'next_milestone': NEXT,
    }


def validate_protocol(p, gates):
    for label, expected in [('Hybrid10', FEATURES10), ('Hybrid12', FEATURES12)]:
        gates.check(label + '_feature_contract_frozen', p['experiments'][label]['features'] == expected)
    gates.check('Hybrid10_fixed_kr_endpoints', p['experiments']['Hybrid10']['fixed_endpoints'] == {'krw_max': 0.8, 'kro_max': 0.8})
    gates.check('canonical_reference_preserved', len(p['benchmarks']['E2_canonical_rows_authoritative']) == 8)
    gates.check('saturation_primary_target_frozen', p['teacher']['BL']['primary_target'] == 'Sw_fan_teacher')
    gates.check('source_native_vs_full_physics_scope_explicit', p['scope']['full_physics_equivalence_claimed'] is False)
    gates.check('case_level_split_frozen', p['split']['unit'] == 'complete physical family')
    gates.check('split_counts_exact', sum(p['split']['counts_base_families'].values()) == p['dataset_design']['base_families'])
    gates.check('objective_terms_defined', all(k in p['objective'] for k in ['L_Sw', 'L_BC', 'L_front', 'L_phys', 'L_mono']))
    gates.check('numerical_loss_weights_not_claimed', p['objective']['weights'] is None)
    gates.check('bounded_saturation_model_required', p['model']['output'] == 'swc+(1-swc-sor)*sigmoid(z)')
    gates.check('experiments_distinct', p['experiments']['Hybrid10']['experiment_id'] != p['experiments']['Hybrid12']['experiment_id'])
    for key in ['training_authorized', 'checkpoint_creation_authorized', 'historical_checkpoint_claimed',
                'SGSim_modification_authorized', 'Pollock_TOF_recomputation_authorized',
                'B4_retraining_authorized', 'OOD_reopening_authorized']:
        gates.check(key + '_false', p['authorization'][key] is False)
    gates.check('prospective_teacher_domain_admissible',
                p['dataset_design']['bounds']['swc'][1] + p['dataset_design']['bounds']['sor'][1] < 1)
    gates.check('source_teacher_not_executed', True, 'AST inspection only; E4 must audit numerical teacher')


def commit_outputs(out, payloads):
    """Publish the complete freeze directory; refuse to replace differing output."""
    if out.exists():
        if not out.is_dir() or set(x.name for x in out.iterdir()) != set(payloads):
            raise FreezeError('Existing output differs; choose a new --output-dir. Nothing replaced.')
        if not all((out / name).read_bytes() == data for name, data in payloads.items()):
            raise FreezeError('Existing output bytes differ; choose a new --output-dir. Nothing replaced.')
        print('Existing identical freeze reused.')
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.v16e3-', dir=out.parent))
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


def run(project, parent_dir, out):
    print('=' * 118 + '\nPAD-Stream V16E-3\nProspective Hybrid BL-DP Teacher-Dataset / Split / Objective / Model-Protocol Freeze\n' + '=' * 118)
    print('\n'.join(PROHIBITIONS))
    gates = Gates()
    print('\nV16E-2 PARENT AUTHORITY')
    for label, (name, expected) in PARENTS.items():
        bind_file(gates, label, parent_dir / name, expected)
    e2, summary = read_json(parent_dir / PARENTS['E2_RESULTS'][0]), read_json(parent_dir / PARENTS['E2_SUMMARY'][0])
    rows = validate_parent(e2, summary, gates)
    print('\nHYBRID SOURCE AUTHORITY (READ ONLY)')
    for label, (name, expected) in SOURCES.items():
        bind_file(gates, label + '_source', project / name, expected)
    evidence = {label: inspect_hybrid(project / SOURCES[label][0], label, gates)
                for label in ['Hybrid10', 'Hybrid12']}
    p = build_protocol(rows, evidence)
    print('\nTEACHER / FEATURE / SPLIT / OBJECTIVE / MODEL CONTRACT')
    validate_protocol(p, gates)
    protocol_bytes = encoded(p)
    results = {'milestone': 'V16E-3', 'status': STATUS, 'protocol_sha256': digest(protocol_bytes),
               'runner_sha256': sha(Path(__file__)), 'parent_artifacts': p['provenance']['parents'],
               'sources': p['provenance']['sources'], 'acceptance_gates': gates.items,
               'evidence_kind': 'parent authority verification plus prospective contract/static source audit; no E4 numerical teacher audit',
               'all_gates_passed': all(v['passed'] for v in gates.items.values()),
               'authorization': p['authorization'], 'next_milestone': NEXT}
    result_bytes = encoded(results)
    summary3 = {'milestone': 'V16E-3', 'status': STATUS, 'protocol_sha256': digest(protocol_bytes),
                'results_sha256': digest(result_bytes), 'protocol_frozen': True,
                'dataset_generated_here': False, 'model_created_here': False,
                'training_authorized': False, 'checkpoint_creation_authorized': False,
                'historical_Hybrid_claimed': False, 'dataset_generation_authorized': True,
                'full_physics_equivalence_claimed': False, 'next_milestone': NEXT}
    summary_bytes = encoded(summary3)
    handoff = f'''# PAD-Stream V16E-3 — Prospective Hybrid BL-DP Protocol Freeze

The exact V16E-2 results/summary/handoff and DP/Hybrid source bytes were verified.
Teacher roles, prospective dataset domain, physical-family splits, objectives,
feature order and recurrent model family are frozen in the accompanying protocol.

This is a classical incompressible pre-breakthrough BL fan experiment. The source
implements a finite-grid Corey/Welge teacher; E4 must audit convergence and physics.
It is not proof of B4B compressible-capillary equivalence. B4B/Pollock/TOF lineage
and the exact 3-D backbone remain authorities for later integration.

E2 owns the canonical table. Hybrid10 uses a separately named fixed-0.8 endpoint
counterpart. Hybrid12 uses E2 variable endpoints. Legacy Hybrid tables do not
replace E2. The 201-node fan grid is a new prospective design choice; source
Hybrid12's 143/145 length conflict does not establish a checkpoint identity.

The network learns fan saturation with analytical shock inputs. Post-breakthrough
learning, full water-cut evolution and full-physics extensions need a subsequent
teacher contract. DP reference response and BL-derived response remain distinct.

No dataset, neural model or checkpoint was created. No SGSim, Pollock/TOF, B4 or
OOD work was performed. E4 dataset generation/audit is authorized by this successful
freeze. Neural training and checkpoint creation remain unauthorized.

Loss definitions are frozen; numerical weights/framework/training settings need
a pre-training manifest after E4 acceptance. Test cannot select these settings.

Protocol SHA: {digest(protocol_bytes)}
Results SHA: {digest(result_bytes)}
Summary SHA: {digest(summary_bytes)}

NEXT: {NEXT}
'''.encode('utf-8')
    payloads = {'V16E3_Hybrid_BL_DP_Protocol.json': protocol_bytes,
                'V16E3_Hybrid_BL_DP_Protocol_Freeze_Results.json': result_bytes,
                'PAD_Stream_V16E3_Summary.json': summary_bytes,
                'V16E3_Handoff.md': handoff}
    commit_outputs(out, payloads)
    print('\n' + '=' * 118 + '\nV16E-3 RESULT\n' + '=' * 118)
    for label in ['V16E-2 parent authority bound', 'DP teacher role frozen', 'Source-bound BL fan teacher role frozen',
                  'Hybrid10 / Hybrid12 contracts frozen', 'Physical-family split protocol frozen', 'Model-family protocol frozen']:
        print(f'{label:48}: YES')
    print(f'{"Dataset generated / training authorized":48}: NO / NO')
    print(f'{"Full compressible-capillary equivalence claimed":48}: NO')
    for name, data in payloads.items():
        print(f'{name} SHA: {digest(data)}')
    print('Output:', out)
    print('NEXT:', NEXT)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--drive-root', type=Path, default=Path('/content/drive/MyDrive/PAD_Stream_Compute'))
    parser.add_argument('--parent-dir', type=Path, help='Exact E2 output directory; default uses --drive-root')
    parser.add_argument('--output-dir', type=Path, help='New E3 output directory; default uses --drive-root')
    args = parser.parse_args(argv)
    try:
        return run(args.project_root.resolve(), (args.parent_dir or args.drive_root / E2_SUBDIR).resolve(),
                   (args.output_dir or args.drive_root / E3_SUBDIR).resolve())
    except (FreezeError, OSError, ValueError, KeyError, TypeError, SyntaxError) as exc:
        print('\n[FAIL] V16E-3 did not close:', exc, file=sys.stderr)
        print('No new successful freeze published by this invocation.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
