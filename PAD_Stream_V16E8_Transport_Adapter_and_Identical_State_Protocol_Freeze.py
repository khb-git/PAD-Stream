#!/usr/bin/env python3
"""
PAD-Stream V16E-8
Hybrid BL-DP PAD-Stream Transport Adapter and Identical-State Integration Protocol Freeze

NO TRAINING.
NO MODEL INFERENCE.
NO CHECKPOINT CREATION OR REPLACEMENT.
NO INTERNAL-TEST RE-EVALUATION.
NO OOD REOPENING.
NO SGSim DEPLOYMENT.
NO POLLOCK/TOF RECOMPUTATION.
NO PRESSURE/FLUX/VELOCITY RECOMPUTATION.
NO GRID MAP-BACK.
NO B4 RETRAINING.
NO BLIND FULL-PATH-xi -> FAN-xi SUBSTITUTION.

This milestone freezes the coordinate/state adapter and identical-state validation
protocol only. It does not execute a neural model or modify any frozen artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile

# -----------------------------------------------------------------------------
# Exact upstream authority
# -----------------------------------------------------------------------------
E7_REL = Path('provenance/hybrid_dp/V16E7_HYBRID_EVIDENCE_AND_DEPLOYMENT_ROLE_FREEZE')
E3_REL = Path('provenance/hybrid_dp/V16E3_R1_HYBRID_PROTOCOL_FREEZE')
OUT_REL = Path('provenance/hybrid_dp/V16E8_TRANSPORT_ADAPTER_IDENTICAL_STATE_PROTOCOL_FREEZE')

E7_ARTIFACTS = {
    'synthesis': ('V16E7_Hybrid10_Hybrid12_Evidence_Synthesis.json',
                  '92289d0f27d1e504fcee226256a8ae2ea5e3858039e0183d979bd4f3a98cd0b5'),
    'routing': ('V16E7_Deployment_Routing_Contract.json',
                '88d434ecc292c49b7cff58aa70223e76a2dc2ce6f8f7124c461867274407fcea'),
    'results': ('V16E7_Evidence_Synthesis_and_Deployment_Role_Results.json',
                '29111c31629f2740b45796ea3336d5c5c30bdf7c149112f9e6a9ccfa4bf2190c'),
    'summary': ('PAD_Stream_V16E7_Summary.json',
                '42925ab608b4a0424987bdd02fc3648b2ef87d098080983f82a670791cefd81e'),
    'handoff': ('V16E7_Handoff.md',
                '29dc61593c2af16ec34b96298692892b079837e6706d2e37132df9f01a9dbd25'),
}
E7_RUNNER = ('PAD_Stream_V16E7_Hybrid_Evidence_Synthesis_and_Deployment_Role_Freeze.py',
             'ade22b9f4e52e8c57785c8fcd556c240badb7b0ece6ef093d7a3acce392db5e1')
E3_PROTOCOL = ('V16E3_R1_Hybrid_BL_DP_Protocol.json',
               '57bcb2e74c68eb77ed8de69d75ddafc00b38d2f3c4e9b884bfc87676160db4a1')
R2_ADAPTER = ('PAD_Stream_V16E3_R2_Repaired_BL_Teacher.py',
              '640a853fd0775c5efaf2922976d5c3843fa69ce9e5165245daffefdb3d4eac2a')
V16C1_SOURCE = ('PAD_Stream_V16C1_Travel_Time_Hierarchy_Integration_Contract.py',
                 'c52971034547162eb1376de83975ac8ee7aa9872d7fe790eda281d7b566ebf29')

FEATURES10 = ['no','nw','swc','sor','mu_w','mu_o','phi','tD','xD_star','Sw_star']
FEATURES12 = ['no','nw','swc','sor','mu_w','mu_o','phi','krw_max','kro_max','tD','xD_star','Sw_star']
PARAM_BOUNDS = {
    'no': [2.0, 4.0], 'nw': [2.0, 4.0],
    'swc': [0.20, 0.45], 'sor': [0.10, 0.30],
    'mu_w_cP': [0.30, 1.0], 'mu_o_cP': [0.50, 5.0],
    'phi': [0.15, 0.25],
    'krw_max_Hybrid12': [0.05, 0.80],
    'kro_max_Hybrid12': [0.30, 0.80],
}
TOLS = {
    'identity_abs': 1e-12,
    'fan_endpoint_abs': 0.002,
    'fan_characteristic_rms': 0.005,
    'preBT_inventory_abs': 0.005,
    'monotonic_increment_positive_tol': 1e-7,
    'fixed_endpoint_identity_abs': 1e-12,
}
PROHIBITIONS = [
    'NO TRAINING OR GRADIENT UPDATE.',
    'NO MODEL INFERENCE OR CHECKPOINT LOAD.',
    'NO CHECKPOINT CREATION, SELECTION, REPLACEMENT, OR RETRAINING.',
    'NO INTERNAL-TEST RE-EVALUATION OR TEST-INFORMED MODEL SELECTION.',
    'NO OOD REOPENING.',
    'NO SGSim MODIFICATION OR DEPLOYMENT IN THIS MILESTONE.',
    'NO POLLOCK/TOF, PRESSURE, FLUX, OR VELOCITY RECOMPUTATION.',
    'NO GRID MAP-BACK OR SATURATION FIELD GENERATION.',
    'NO B4 RETRAINING.',
    'NO BLIND FULL-PATH NORMALIZED XI -> FAN-XI SUBSTITUTION.',
    'NO SILENT 0.8/0.8 ENDPOINT ASSUMPTION WHEN ENDPOINT METADATA IS ABSENT.',
    'NO ABSOLUTE PERMEABILITY CHANNEL ADDED TO THE PI-RNN.',
    'NO DP REALLOCATION ON TOP OF EXACT 3-D POLLOCK FLOW WEIGHTS.',
]

class FreezeError(RuntimeError):
    pass

class Gates:
    def __init__(self): self.items = {}
    def add(self, name, passed, detail=None):
        self.items[name] = {'passed': bool(passed), 'detail': detail}
        print(f"[{'PASS' if passed else 'FAIL'}] {name}" + (f": {detail}" if detail is not None else ''), flush=True)
        if not passed:
            raise FreezeError(name + (f': {detail}' if detail else ''))


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(obj) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode('utf-8')


def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def bind_file(g: Gates, label: str, path: Path, expected: str):
    g.add(label + '_exists', path.is_file(), str(path))
    actual = sha(path)
    g.add(label + '_SHA_exact', actual == expected, actual if actual != expected else None)
    return actual


def publish(out: Path, payloads: dict[str, bytes]):
    if out.exists():
        expected_names = set(payloads)
        found_names = {p.name for p in out.iterdir() if p.is_file()}
        if found_names != expected_names:
            raise FreezeError('Existing E8 output directory differs; nothing overwritten.')
        for name, data in payloads.items():
            if (out / name).read_bytes() != data:
                raise FreezeError('Existing E8 output bytes differ; nothing overwritten.')
        print('Existing identical V16E-8 freeze reused.', flush=True)
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.v16e8-', dir=out.parent))
    try:
        for name, data in payloads.items():
            p = stage / name
            with p.open('xb') as f:
                f.write(data); f.flush(); os.fsync(f.fileno())
        stage.rename(out)
    finally:
        if stage.exists(): shutil.rmtree(stage)


def protocol_contract():
    return {
        'milestone': 'V16E-8',
        'title': 'Hybrid BL-DP PAD-Stream Transport Adapter and Identical-State Integration Protocol Freeze',
        'scientific_scope': {
            'authorized_now': 'protocol/interface freeze only',
            'inference_authorized_here': False,
            'SGSim_deployment_authorized_here': False,
            'full_physics_equivalence_claimed': False,
            'learned_transport_role': 'PROPOSAL_ONLY',
            'exact_authorities': [
                'finite-volume pressure and conservative Darcy flux',
                'exact Pollock streamline geometry and TOF',
                'R2 analytical Corey/Welge shock inputs',
                'inventory/conservation screening',
                'conservative grid map-back',
            ],
        },
        'routing': {
            'Hybrid10': {
                'eligibility': 'endpoint metadata explicitly guarantees krw_max=0.8 and kro_max=0.8 within identity tolerance',
                'features': FEATURES10,
                'role': 'fixed-endpoint pre-breakthrough fan proposal',
            },
            'Hybrid12': {
                'eligibility': 'explicit krw_max and kro_max are present and inside frozen E3 bounds; Hybrid10 has precedence for exact 0.8/0.8',
                'features': FEATURES12,
                'role': 'variable-endpoint pre-breakthrough fan proposal',
            },
            'fallback': 'exact physics / screened fallback whenever required metadata is missing, ambiguous, outside domain, nonfinite, post-breakthrough, or a physics screen fails',
            'absolute_permeability_policy': 'k, h, streamline weight, DP, Lorenz, layer ID and grid indices remain metadata/physics; never PI-RNN conditioning channels',
        },
        'coordinate_adapter': {
            'authoritative_coordinate': 'Pollock time of flight tau_s at frozen streamline nodes',
            'do_not_confuse': {
                'full_path_coordinate': 'chi = tau/tau_end in [0,1]',
                'model_fan_coordinate': 'eta = tau/tau_star on invaded interval only, eta in [0,1]',
                'rule': 'full-path chi is NOT fed blindly as model fan eta',
            },
            'state_inputs_per_streamline': [
                'tau_nodes', 'tau_end', 'physical elapsed injection time t',
                'Corey/fluids/residual-saturation parameters',
                'explicit relative-permeability endpoints when Hybrid12 is eligible',
                'exact streamline flow weight for later conservative aggregation',
            ],
            'exact_shock_inputs': {
                'Sw_star': 'computed by frozen R2 analytical teacher; never predicted by Hybrid10/12',
                'fprime_star': "df_w/dSw evaluated analytically at Sw_star using the same endpoint/exponent/viscosity state",
                'tau_star': 't * fprime_star',
                't_breakthrough': 'tau_end / fprime_star',
            },
            'dimensionless_mapping': {
                'tD': 't / tau_end',
                'xD_star': 'tau_star / tau_end = tD * fprime_star',
                'eta_model_grid': 'j/200, j=0..200',
                'equivalence_identity': 'xD_star/tD = fprime_star',
                'pre_breakthrough_gate': '0 < t < t_breakthrough, equivalently 0 < xD_star < 1',
            },
            'projection_back_to_Pollock_nodes': {
                'invaded_nodes': 'tau <= tau_star: eta=tau/tau_star; interpolate learned 201-node fan proposal in eta',
                'downstream_nodes': 'tau > tau_star: retain initial saturation swc',
                'front': 'tau=tau_star corresponds to Sw_star',
                'injector': 'tau=0 corresponds to 1-sor',
            },
        },
        'deployment_domain_firewall': {
            'parameter_bounds': PARAM_BOUNDS,
            'sequence_nodes': 201,
            'pre_breakthrough_only': True,
            'absolute_profile_clock': 'physical elapsed time since injection start; not an arbitrary recurrent delta-state update',
            'post_breakthrough': 'not authorized for the current Hybrid fan checkpoints',
            'nonuniform_path_rock_fluid_state': 'direct SGSim use is NOT authorized by E8; piecewise/effective-state semantics require a later protocol',
        },
        'physics_screens_for_future_adapter_execution': {
            'finite_prediction': True,
            'saturation_bounds': 'swc <= Sw <= 1-sor',
            'injection_endpoint_abs_tol': TOLS['fan_endpoint_abs'],
            'shock_endpoint_abs_tol': TOLS['fan_endpoint_abs'],
            'characteristic_RMS_tol': TOLS['fan_characteristic_rms'],
            'dimensionless_inventory_identity': 'xD_star * integral_0^1 (Sw(eta)-swc) d eta = tD',
            'inventory_abs_tol': TOLS['preBT_inventory_abs'],
            'monotonicity': 'positive adjacent saturation increments may not exceed 1e-7',
            'failure_action': 'reject learned proposal and use exact physics fallback; do not silently repair or relax a tolerance',
        },
        'heterogeneity_and_weighting': {
            'controlled_layered_DP_role': 'training/reference mechanism for heterogeneous local clocks and layered response',
            '3D_PAD_Stream_role': 'exact Darcy/Pollock tau_end and exact streamline flow weights are authoritative heterogeneity carriers',
            'no_double_counting_rule': 'do not apply a new DP F_i allocation on top of exact 3D streamline weights',
            'neural_effect': 'heterogeneity enters Hybrid conditioning through tD/xD_star and local rock/fluid/endpoints, not through absolute k or DP scalar',
        },
        'identical_state_validation_protocol_for_next_milestone': {
            'purpose': 'prove adapter coordinate/state equivalence before any SGSim deployment',
            'data_access': 'public anchors plus TRAIN/VALIDATION families only; internal-test arrays are not re-evaluated and OOD remains closed',
            'family_selection': 'within TRAIN and VALIDATION separately, sort family IDs by SHA256("V16E8_IDENTICAL_STATE_1708|"+family_id); select first 16 from each partition',
            'layers': ['L01','L04','L08'],
            'clock_indices_zero_based': [0,4,9,14,19],
            'experiments': ['Hybrid10','Hybrid12'],
            'synthetic_tau_end_for_roundtrip': '1.0 arbitrary positive time unit; t=tD; tau_star=xD_star so the E4 state is reconstructed without changing the dimensionless physics',
            'required_gates': {
                'conditioning_roundtrip_abs_max': 1e-12,
                'tD_identity_abs_max': 1e-12,
                'xD_star_identity_abs_max': 1e-12,
                'shock_ratio_identity_abs_max': 1e-12,
                'adapter_vs_direct_model_same_input_abs_max': 1e-7,
                'downstream_initial_state_exact': True,
                'all_frozen_physics_screens_pass': True,
                'no_test_or_OOD_access': True,
            },
            'test_metrics_policy': 'sealed A-T/B-T metrics remain descriptive provenance only and may not choose, tune, or reroute models',
        },
        'future_PAD_Stream_flow': [
            'exact pressure / conservative Darcy flux',
            'exact Pollock geometry + TOF + flow weights',
            'endpoint/domain router',
            'R2 exact shock inputs and pre-BT eligibility',
            'Hybrid10 or Hybrid12 fan proposal on eta grid',
            'physics screen; exact fallback on failure',
            'projection to Pollock tau nodes',
            'exact conservative deposition/map-back',
            'global PAD-Stream state update',
        ],
        'next_milestone': 'V16E-9 — Hybrid Transport Adapter Implementation and Identical-State Equivalence Validation',
    }


def run(project: Path, drive: Path, out: Path):
    print('='*118)
    print('PAD-Stream V16E-8')
    print('Hybrid BL-DP PAD-Stream Transport Adapter and Identical-State Integration Protocol Freeze')
    print('='*118)
    print('\n'.join(PROHIBITIONS), flush=True)
    g = Gates()

    print('\nV16E-7 PARENT AUTHORITY')
    e7 = drive / E7_REL
    for label, (name, expected) in E7_ARTIFACTS.items():
        bind_file(g, 'E7_'+label, e7/name, expected)
    bind_file(g, 'E7_runner', project/E7_RUNNER[0], E7_RUNNER[1])

    print('\nFROZEN FEATURE / TEACHER AUTHORITY')
    e3 = drive / E3_REL / E3_PROTOCOL[0]
    bind_file(g, 'E3_protocol', e3, E3_PROTOCOL[1])
    p3 = read_json(e3)
    # Exact feature-order checks from frozen E3-R1.
    ptxt = json.dumps(p3, sort_keys=True)
    g.add('Hybrid10_feature_names_present', all(x in ptxt for x in FEATURES10))
    g.add('Hybrid12_endpoint_feature_names_present', 'krw_max' in ptxt and 'kro_max' in ptxt)
    bind_file(g, 'R2_adapter', project/R2_ADAPTER[0], R2_ADAPTER[1])

    print('\nPAD-STREAM TRANSPORT COORDINATE AUTHORITY')
    bind_file(g, 'V16C1_source', project/V16C1_SOURCE[0], V16C1_SOURCE[1])
    c1_text = (project/V16C1_SOURCE[0]).read_text(encoding='utf-8', errors='ignore')
    g.add('Pollock_authoritative_streamline_coordinate_present', 'AUTHORITATIVE_STREAMLINE_TRANSPORT_COORDINATE' in c1_text)
    g.add('FMM_not_forced_to_replace_Pollock', 'FMM replaces Pollock TOF' in c1_text)
    g.add('ADV_not_forced_to_replace_Pollock', 'ADV replaces Pollock TOF' in c1_text)

    print('\nV16E-8 ADAPTER CONTRACT')
    contract = protocol_contract()
    g.add('full_path_xi_and_fan_eta_distinguished', contract['coordinate_adapter']['do_not_confuse']['full_path_coordinate'] != contract['coordinate_adapter']['do_not_confuse']['model_fan_coordinate'])
    g.add('Pollock_TOF_retained_as_authority', contract['coordinate_adapter']['authoritative_coordinate'].startswith('Pollock'))
    g.add('R2_shock_inputs_remain_exact', 'R2' in contract['coordinate_adapter']['exact_shock_inputs']['Sw_star'])
    g.add('preBT_only_contract', contract['deployment_domain_firewall']['pre_breakthrough_only'])
    g.add('postBT_not_authorized', contract['deployment_domain_firewall']['post_breakthrough'].startswith('not authorized'))
    g.add('Hybrid10_fixed_endpoint_route', '0.8' in contract['routing']['Hybrid10']['eligibility'])
    g.add('Hybrid12_variable_endpoint_route', 'explicit krw_max and kro_max' in contract['routing']['Hybrid12']['eligibility'])
    g.add('ambiguous_metadata_falls_back_exact', 'exact physics' in contract['routing']['fallback'])
    g.add('no_absolute_k_neural_channel', 'never PI-RNN conditioning' in contract['routing']['absolute_permeability_policy'])
    g.add('no_DP_double_counting', 'do not apply a new DP F_i allocation' in contract['heterogeneity_and_weighting']['no_double_counting_rule'])
    g.add('SGSim_direct_deployment_deferred', 'NOT authorized' in contract['deployment_domain_firewall']['nonuniform_path_rock_fluid_state'])
    g.add('identical_state_excludes_test', 'TRAIN/VALIDATION' in contract['identical_state_validation_protocol_for_next_milestone']['data_access'])
    g.add('next_milestone_E9', contract['next_milestone'].startswith('V16E-9'))

    contract_bytes = encoded(contract)
    results = {
        'milestone': 'V16E-8',
        'status': 'PASS',
        'runner_sha256': sha(Path(__file__)),
        'parent_E7_artifacts': {k:{'filename':v[0],'sha256':v[1]} for k,v in E7_ARTIFACTS.items()},
        'E3_protocol_sha256': E3_PROTOCOL[1],
        'R2_adapter_sha256': R2_ADAPTER[1],
        'V16C1_source_sha256': V16C1_SOURCE[1],
        'contract_sha256': digest(contract_bytes),
        'acceptance_gates': g.items,
        'training_performed': False,
        'inference_performed': False,
        'checkpoint_loaded': False,
        'internal_test_reopened': False,
        'OOD_opened': False,
        'SGSim_deployed': False,
        'next_milestone': contract['next_milestone'],
    }
    results_bytes = encoded(results)
    summary = {
        'milestone': 'V16E-8',
        'status': 'PASS',
        'adapter_protocol_frozen': True,
        'Pollock_TOF_authoritative': True,
        'full_path_xi_not_equal_model_fan_eta': True,
        'Hybrid10_fixed_endpoint_branch': True,
        'Hybrid12_variable_endpoint_branch': True,
        'exact_fallback_required_for_ambiguous_or_OOD': True,
        'pre_breakthrough_absolute_fan_only': True,
        'SGSim_deployment_authorized': False,
        'training_or_inference_performed': False,
        'contract_sha256': digest(contract_bytes),
        'results_sha256': digest(results_bytes),
        'next_milestone': contract['next_milestone'],
    }
    summary_bytes = encoded(summary)
    handoff = f'''# PAD-Stream V16E-8 — Transport Adapter / Identical-State Protocol Freeze\n\nV16E-7 remains the deployment-role authority. Hybrid10 is the explicit fixed\n0.8/0.8 endpoint branch; Hybrid12 is the explicit variable-endpoint branch.\nAmbiguous, OOD, post-breakthrough, or failed-screen states use exact physics.\n\nPollock TOF remains the authoritative streamline coordinate. E8 explicitly\ndistinguishes full-path chi=tau/tau_end from the model fan coordinate\neta=tau/tau_star. For a pre-breakthrough state, tD=t/tau_end, exact R2 shock\nphysics supplies Sw_star and fprime_star, tau_star=t*fprime_star, and\nxD_star=tau_star/tau_end. The learned model is evaluated on its frozen 201-node\neta grid and only then projected to Pollock nodes. No blind coordinate substitution\nis authorized.\n\nThe current Hybrid checkpoints are absolute pre-breakthrough classical-fan\nproposals, not arbitrary recurrent state-to-state updates. Direct use on an\nSGSim streamline whose rock/fluid/endpoints vary along the path is not authorized\nby E8. Piecewise/effective-state semantics require later evidence. Exact 3-D\nstreamline flow weights must not be reallocated by DP a second time.\n\nE9 is authorized only to implement this adapter and prove identical-state\nequivalence using public anchors plus TRAIN/VALIDATION families. Internal test\nand OOD remain closed to E9. No SGSim deployment occurs until that interface\nequivalence closes successfully.\n\nContract SHA: {digest(contract_bytes)}\nResults SHA: {digest(results_bytes)}\nSummary SHA: {digest(summary_bytes)}\n\nNEXT: {contract['next_milestone']}\n'''.encode('utf-8')

    payloads = {
        'V16E8_Transport_Adapter_Contract.json': contract_bytes,
        'V16E8_Transport_Adapter_and_Identical_State_Results.json': results_bytes,
        'PAD_Stream_V16E8_Summary.json': summary_bytes,
        'V16E8_Handoff.md': handoff,
    }
    publish(out, payloads)

    print('\n' + '='*118)
    print('V16E-8 RESULT: PASS')
    print('='*118)
    print(f"{'Pollock TOF retained as authority':48}: YES")
    print(f"{'Full-path xi blindly used as fan coordinate':48}: NO")
    print(f"{'Hybrid10 / Hybrid12 routing frozen':48}: FIXED-ENDPOINT / VARIABLE-ENDPOINT")
    print(f"{'Exact fallback for ambiguous/OOD/post-BT':48}: YES")
    print(f"{'Training / inference performed':48}: NO / NO")
    print(f"{'Internal test / OOD reopened':48}: NO / NO")
    print(f"{'SGSim deployment authorized':48}: NO")
    for name, data in payloads.items():
        print(f'{name} SHA: {digest(data)}')
    print('Output:', out)
    print('NEXT:', contract['next_milestone'])
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parent)
    ap.add_argument('--drive-root', type=Path, default=Path('/content/drive/MyDrive/PAD_Stream_Compute'))
    ap.add_argument('--output-dir', type=Path)
    args = ap.parse_args(argv)
    try:
        project = args.project_root.resolve(); drive = args.drive_root.resolve()
        out = (args.output_dir or drive/OUT_REL).resolve()
        return run(project, drive, out)
    except (FreezeError, OSError, ValueError, KeyError, TypeError, AssertionError, json.JSONDecodeError) as exc:
        print('\n[FAIL] V16E-8 did not close:', exc, file=sys.stderr, flush=True)
        print('No successful adapter protocol or SGSim deployment authority was published.', file=sys.stderr, flush=True)
        return 2

if __name__ == '__main__':
    sys.exit(main())
