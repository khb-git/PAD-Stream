from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import shutil
import sys
import traceback
import numpy as np

# =============================================================================
# PAD-Stream V16E-22-R1
# Historical SG7E 100-Day Reference-Truth Lineage Reconstruction Audit
# =============================================================================
# NO CHANGE TO V16E-18-R1 FROZEN CANDIDATE OR V16E-19/V16E-20-R2/V16E-21.
# NO V16 CANDIDATE PERFORMANCE USED TO SELECT REFERENCE TRUTH.
# NO SG7E THRESHOLD CHANGE: historical authoritative plume threshold remains 0.5.
# 0.21 remains diagnostic-only and is not used here.
# NO DEPLOYMENT GATE EVALUATION.
# NO TRAINING / CHECKPOINT LOAD / MODEL INFERENCE.
# NO PRESSURE / DARCY / POLLOCK / TOF / MAP-BACK / TRANSPORT RECOMPUTATION.
#
# REPAIR SCOPE
# ------------
# Original V16E-22 blocked only because it asked the compact E21 summary for
# a 100-day-specific status string. E21 intentionally stores that detailed
# status in V16E21_Reference_Plume_Provenance_Status.json, while its compact
# summary stores a generic unresolved-lineage label. R1 reconciles those two
# immutable schema roles and changes no scientific contract.
#
# PURPOSE
# -------
# Bind actual historical V15 SG7E forensic outputs and reconstruct the exact
# 100-day truth snapshot from the already-persisted multi-time SG7A_corrected
# historical reference tensor. The 100-day snapshot is extracted by exact
# time-axis identity only, never by V16 performance.
#
# E22-R1 creates a reference-truth CANDIDATE only. It is not frozen until an
# independent V16E-23 validation closes.
# =============================================================================

ROOT = Path(__file__).resolve().parent
DRIVE = Path('/content/drive/MyDrive/PAD_Stream_Compute')
OUT = DRIVE / 'provenance/hybrid_dp/V16E22_R1_HISTORICAL_SG7E_100DAY_REFERENCE_TRUTH_LINEAGE_RECONSTRUCTION_AUDIT'
BLOCKED = DRIVE / 'provenance/hybrid_dp/V16E22_R1_BLOCKED_HISTORICAL_SG7E_100DAY_REFERENCE_TRUTH_LINEAGE_RECONSTRUCTION_AUDIT'

EXPECTED_GRID = (15, 50, 50)
EXPECTED_MULTI = (4, 15, 50, 50)
EXPECTED_TIMES = np.array([100.0, 250.0, 500.0, 1000.0], dtype=np.float64)
EXPECTED_THRESHOLD = 0.5
EXPECTED_REFERENCE_KEY = 'SG7A_corrected'
EXPECTED_FROZEN_SHA = 'd422dc1e56281c1baf0ae007c62ce4bd69677a232bd1448a5bd79d3177eafaea'

# Blocked V16E-22 parent evidence: R1 repairs ONLY the E21 reference-status
# schema interpretation gate. The original E22 runner and blocked report are
# immutable parent evidence.
E22_PARENT_RUNNER = ROOT / 'PAD_Stream_V16E22_Historical_SG7E_100Day_Reference_Truth_Lineage_Reconstruction_Audit.py'
E22_PARENT_RUNNER_SHA = 'eb3a6396f1e09beedd78e4c791be22e575cd758726871046a29ead34e4fb64cc'
E22_PARENT_BLOCKED_DIR = DRIVE / 'provenance/hybrid_dp/V16E22_BLOCKED_HISTORICAL_SG7E_100DAY_REFERENCE_TRUTH_LINEAGE_RECONSTRUCTION_AUDIT'
E22_PARENT_BLOCKED_JSON = E22_PARENT_BLOCKED_DIR / 'V16E22_Blocked_Historical_100Day_Reference_Truth_Lineage_Audit.json'
E22_PARENT_BLOCKED_SHA = '07b537f93c0e661047041911e99437e2fcecdc4c64c06ed25c61f9257ca9d645'
E22_PARENT_EXPECTED_FAILED_GATE = 'E21_reference_requires_100d_lineage'

# V16E-21 exact authority
E21_RUNNER = ROOT / 'PAD_Stream_V16E21_Historical_SG7E_Plume_Threshold_and_Reference_Plume_Provenance_Reconciliation.py'
E21_RUNNER_SHA = '59cd2e6bd06ca19efc4f4ad94fee07a4f6bf53c55f9873abf912621157eecb91'
E21_DIR = DRIVE / 'provenance/hybrid_dp/V16E21_HISTORICAL_SG7E_PLUME_THRESHOLD_REFERENCE_PROVENANCE_RECONCILIATION'
E21_ARTIFACTS = {
    'V16E21_Historical_Plume_Threshold_Contract.json': 'dcb3e989298cfe01b1a90e96e71f0eeae420782cd5001f088d8dc625ba366d07',
    'V16E21_Reference_Plume_Provenance_Status.json': '12017feb7c20392247d776bc35848fc2ce0aa070e6cc16898dc587c6007ea67c',
    'PAD_Stream_V16E21_Summary.json': 'c6317abc9b88c0f87e52b61dda89977c7585f67274489000c1590454cc09737c',
    'V16E21_Handoff.md': '178e5ef2826ee7d1272c9b9abbe95e707d413cc279c774a3737d7fec0e520965',
    'V16E21_Threshold_Authority_Evidence.csv': '49ba7764528f091ad205d37e6583b121ee4debec137374adc5742a9f9083ff9d',
    'V16E21_Threshold_Role_Separation.csv': '213aa6ed4482e3a59949ecf758f6931be7ab35c6c4b213bdc5302544c2b96e37',
    'V16E21_Reference_Provenance_Evidence.csv': 'a6f94069c0b256615f75cfc49c2f90116c28bd1579bdc583806d288655897002',
    'V16E21_Evaluation_Prerequisite_Matrix.csv': 'e053c0b8b6888cd03a1cded6186198b71a9f193d63dd84a2bb6244f413293ec6',
    'V16E21_Final_Gate_Matrix.csv': '369cbf1a45fa571f3955a39639b7be4cc2d8ad6d6d9eb6390060e3e6f17851b0',
}

# Frozen V16 deployment candidate remains immutable.
E18_FROZEN = DRIVE / ('provenance/hybrid_dp/V16E18_R1_FROZEN_SGSIM_100D_FULL_GRID_CANDIDATE/'
                     'frozen_full_grid/V16E18_R1_Frozen_SGSim_100Day_Full_Grid_Candidate.npz')

# Historical source authorities (exact library/repository snapshots).
HIST_SOURCES = {
    'PAD_Stream_V15SG7E1R11_Top_SG7A_Corrected_Artifact_Lineage_Conflict_Audit.py':
        'a9014ff1dba0466a79f5dd78c0134aeb082a977c09b391b9a08511de814b18aa',
    'PAD_Stream_V15SG7E1R12_Historical_Reference_Time_Index_Snapshot_Resolution_Audit.py':
        'e02e5a149aaf59d04194947b44071db01854bbd4dd00c5cf0d6557a75dcaa796',
    'PAD_Stream_V15SG7E1R13_Per_Time_Metric_Snapshot_Correspondence_Audit.py':
        '055ed61246e30b06a9e0eb2492a2ac47af196b355002518ea3ea4a00aba136b7',
    'PAD_Stream_V15SG7E1R14_Multi_Time_Historical_Reference_Reconstruction_Contract_Audit.py':
        '514e6f5ebaf5346691d3194cb2eefe041528eb00b4bd452c657b5d23e5132a3a',
}

# Historical output records that bind ACTUAL execution, not just source branches.
R11_DIR = ROOT / 'output/V15_SG7E1R11'
R12_DIR = ROOT / 'output/V15_SG7E1R12'
R13_DIR = ROOT / 'output/V15_SG7E1R13'
R14_DIR = ROOT / 'output/V15_SG7E1R14'

R11_SUMMARY = R11_DIR / 'PAD_Stream_V15SG7E1R11_Summary.json'
R11_CONTRACT = R11_DIR / 'V15SG7E1R11_Top_SG7A_Corrected_Lineage_Contract.json'
R12_SUMMARY = R12_DIR / 'PAD_Stream_V15SG7E1R12_Summary.json'
R12_CONTRACT = R12_DIR / 'V15SG7E1R12_Historical_Reference_Time_Index_Contract.json'
R13_SUMMARY = R13_DIR / 'PAD_Stream_V15SG7E1R13_Summary.json'
R13_CONTRACT = R13_DIR / 'V15SG7E1R13_Per_Time_Snapshot_Correspondence_Contract.json'
R14_SUMMARY = R14_DIR / 'PAD_Stream_V15SG7E1R14_Summary.json'
R14_CONTRACT = R14_DIR / 'V15SG7E1R14_Multi_Time_Historical_Reference_Contract.json'
R14_NUMERICAL = R14_DIR / 'V15SG7E1R14_Multi_Time_Historical_Reference.npz'
R14_HASHES = R14_DIR / 'V15SG7E1R14_Per_Time_Reference_Hashes.csv'

# E22-R1 outputs
NUMERICAL_OUT = OUT / 'V16E22_R1_Historical_SG7E_100Day_Reference_Truth_Candidate.npz'
LINEAGE_JSON = OUT / 'V16E22_R1_Historical_100Day_Reference_Truth_Lineage_Contract.json'
AUDIT_JSON = OUT / 'V16E22_R1_Reference_Truth_Reconstruction_Audit.json'
SUMMARY_JSON = OUT / 'PAD_Stream_V16E22_R1_Summary.json'
HANDOFF_MD = OUT / 'V16E22_R1_Handoff.md'
SOURCE_CSV = OUT / 'V16E22_R1_Historical_Source_Authority.csv'
HIST_OUTPUT_CSV = OUT / 'V16E22_R1_Historical_Output_Identity.csv'
TIME_CSV = OUT / 'V16E22_R1_Reference_Time_Snapshot_Identity.csv'
GATE_CSV = OUT / 'V16E22_R1_Final_Gate_Matrix.csv'
BLOCKED_JSON = BLOCKED / 'V16E22_R1_Blocked_Historical_100Day_Reference_Truth_Lineage_Audit.json'


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def sha256_array(arr) -> str:
    a = np.ascontiguousarray(arr)
    return hashlib.sha256(a.tobytes()).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding='utf-8')


def save_csv(path: Path, rows):
    if not rows:
        path.write_text('', encoding='utf-8')
        return
    fields = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def normpath_text(x) -> str:
    return str(x or '').replace('\\', '/').lower()


def same_times(values) -> bool:
    try:
        a = np.asarray(values, dtype=np.float64).reshape(-1)
    except Exception:
        return False
    return a.shape == EXPECTED_TIMES.shape and np.array_equal(a, EXPECTED_TIMES)


def morphology(mask):
    mask = np.asarray(mask, dtype=bool)
    cells = int(mask.sum())
    footprint = int(np.any(mask, axis=0).sum())
    layers = np.where(np.any(mask, axis=(1, 2)))[0]
    if len(layers):
        zmin, zmax = int(layers[0]), int(layers[-1])
        extent = zmax - zmin + 1
    else:
        zmin = zmax = -1
        extent = 0
    pts = np.argwhere(mask)
    if len(pts):
        c = pts.mean(axis=0)
        centroid = [float(c[0]), float(c[1]), float(c[2])]
    else:
        centroid = [None, None, None]
    return {
        'plume_cells': cells,
        'footprint_cells': footprint,
        'vertical_extent_layers': int(extent),
        'zmin_layer_zero_based': zmin,
        'zmax_layer_zero_based': zmax,
        'centroid_kji': centroid,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    gates = {}

    def gate(name, condition, detail=''):
        ok = bool(condition)
        gates[name] = {'passed': ok, 'detail': str(detail)}
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ''))
        if not ok:
            raise GateError(name)

    print('\n' + '=' * 132)
    print('PAD-Stream V16E-22-R1 E21 Reference-Status Schema Repair / Historical SG7E 100-Day Reference-Truth Lineage Reconstruction Audit')
    print('=' * 132)
    print('NO CHANGE TO V16E-18-R1 FROZEN CANDIDATE OR V16E-19/V16E-20-R2/V16E-21 ARTIFACTS.')
    print('NO V16 PERFORMANCE USED TO SELECT REFERENCE TRUTH.')
    print('NO SG7E THRESHOLD CHANGE: AUTHORITATIVE HISTORICAL THRESHOLD REMAINS S >= 0.5.')
    print('0.21 REMAINS DIAGNOSTIC-ONLY.')
    print('NO DEPLOYMENT GATE EVALUATION OR FULL-GRID PLUME CLAIM.')
    print('NO TRAINING / MODEL INFERENCE / PRESSURE / DARCY / POLLOCK / TOF / MAP-BACK / TRANSPORT RECOMPUTATION.')

    try:
        # ------------------------------------------------------------------
        # Blocked V16E-22 parent evidence
        # ------------------------------------------------------------------
        print('\nBLOCKED V16E-22 PARENT EVIDENCE')
        gate('E22_parent_runner_exists', E22_PARENT_RUNNER.is_file(), E22_PARENT_RUNNER)
        gate('E22_parent_runner_SHA_exact', sha256_file(E22_PARENT_RUNNER) == E22_PARENT_RUNNER_SHA)
        gate('E22_parent_blocked_report_exists', E22_PARENT_BLOCKED_JSON.is_file(), E22_PARENT_BLOCKED_JSON)
        gate('E22_parent_blocked_report_SHA_exact', sha256_file(E22_PARENT_BLOCKED_JSON) == E22_PARENT_BLOCKED_SHA)
        e22_parent_blocked = load_json(E22_PARENT_BLOCKED_JSON)
        gate('E22_parent_status_BLOCKED',
             e22_parent_blocked.get('status') == 'V16E22_HISTORICAL_100DAY_REFERENCE_TRUTH_LINEAGE_RECONSTRUCTION_BLOCKED')
        parent_gates = e22_parent_blocked.get('gates', {})
        parent_failed = [k for k, v in parent_gates.items() if not bool(v.get('passed', False))]
        gate('E22_parent_single_failed_gate',
             parent_failed == [E22_PARENT_EXPECTED_FAILED_GATE], parent_failed)
        gate('E22_parent_exception_exact_gate',
             e22_parent_blocked.get('exception') == "GateError('E21_reference_requires_100d_lineage')",
             e22_parent_blocked.get('exception'))
        gate('E22_parent_all_prior_recorded_gates_passed',
             all(bool(v.get('passed', False))
                 for k, v in parent_gates.items()
                 if k != E22_PARENT_EXPECTED_FAILED_GATE))
        gate('E22_parent_E21_not_modified', not bool(e22_parent_blocked.get('E21_modified')))
        gate('E22_parent_frozen_candidate_not_modified', not bool(e22_parent_blocked.get('frozen_candidate_modified')))
        gate('E22_parent_reference_candidate_not_frozen', not bool(e22_parent_blocked.get('reference_candidate_frozen')))
        gate('E22_parent_no_deployment_evaluation', not bool(e22_parent_blocked.get('deployment_pass_fail_evaluated')))
        gate('E22_parent_no_full_grid_plume_authorization', not bool(e22_parent_blocked.get('full_grid_plume_authorized')))

        # ------------------------------------------------------------------
        # E21 authority
        # ------------------------------------------------------------------
        print('\nV16E-21 THRESHOLD / REFERENCE-PROVENANCE AUTHORITY')
        gate('E21_runner_exists', E21_RUNNER.is_file(), E21_RUNNER)
        gate('E21_runner_SHA_exact', sha256_file(E21_RUNNER) == E21_RUNNER_SHA)
        for name, expected in E21_ARTIFACTS.items():
            p = E21_DIR / name
            gate(f'E21_{name}_exists', p.is_file(), p)
            gate(f'E21_{name}_SHA_exact', sha256_file(p) == expected)

        e21_summary = load_json(E21_DIR / 'PAD_Stream_V16E21_Summary.json')
        e21_thr = load_json(E21_DIR / 'V16E21_Historical_Plume_Threshold_Contract.json')
        e21_ref = load_json(E21_DIR / 'V16E21_Reference_Plume_Provenance_Status.json')
        gate('E21_summary_status_PASS', e21_summary.get('status') == 'PASS')
        gate('E21_authoritative_threshold_0p5', float(e21_summary.get('historical_authoritative_plume_threshold')) == 0.5)
        gate('E21_reference_unresolved', not bool(e21_summary.get('reference_plume_selected')))
        # E22 originally read only the compact E21 summary. That summary stores
        # the generic state UNRESOLVED_REQUIRES_LINEAGE_RECONSTRUCTION, while
        # the dedicated immutable reference-status artifact stores the more
        # specific 100-day lineage requirement. R1 binds BOTH records instead
        # of demanding the detailed wording from the compact summary.
        gate('E21_summary_reference_status_generic_exact',
             e21_summary.get('reference_truth_status') == 'UNRESOLVED_REQUIRES_LINEAGE_RECONSTRUCTION',
             e21_summary.get('reference_truth_status'))
        gate('E21_reference_status_artifact_100d_lineage_exact',
             e21_ref.get('reference_truth_status') ==
             'UNRESOLVED_REQUIRES_HISTORICAL_100_DAY_TRUTH_LINEAGE_RECONSTRUCTION',
             e21_ref.get('reference_truth_status'))
        gate('E21_reference_requires_100d_lineage_repaired_schema',
             (e21_summary.get('reference_truth_status') == 'UNRESOLVED_REQUIRES_LINEAGE_RECONSTRUCTION'
              and e21_ref.get('reference_truth_status') ==
              'UNRESOLVED_REQUIRES_HISTORICAL_100_DAY_TRUTH_LINEAGE_RECONSTRUCTION'))
        gate('E21_no_deployment_evaluation', not bool(e21_summary.get('deployment_pass_fail_evaluated')))
        gate('E21_frozen_candidate_unchanged', not bool(e21_summary.get('frozen_candidate_modified')))
        gate('E21_full_grid_plume_not_authorized', not bool(e21_summary.get('full_grid_plume_authorized')))
        gate('E21_threshold_contract_0p5', abs(float(e21_thr.get('authoritative_plume_threshold', 0.5)) - 0.5) < 1e-15)
        gate('E21_reference_status_unselected', not bool(e21_ref.get('reference_plume_selected', False)))

        gate('E18R1_frozen_candidate_exists', E18_FROZEN.is_file(), E18_FROZEN)
        gate('E18R1_frozen_candidate_SHA_exact', sha256_file(E18_FROZEN) == EXPECTED_FROZEN_SHA)

        # ------------------------------------------------------------------
        # Historical source authority
        # ------------------------------------------------------------------
        print('\nHISTORICAL V15 SG7E REFERENCE-LINEAGE SOURCE AUTHORITY')
        source_rows = []
        for name, expected in HIST_SOURCES.items():
            p = ROOT / name
            gate(f'{name}_exists', p.is_file(), p)
            actual = sha256_file(p)
            gate(f'{name}_SHA_exact', actual == expected, actual)
            source_rows.append({'file': name, 'sha256': actual, 'role': 'historical_reference_lineage_source'})

        s11 = (ROOT / list(HIST_SOURCES.keys())[0]).read_text(encoding='utf-8', errors='ignore')
        s12 = (ROOT / list(HIST_SOURCES.keys())[1]).read_text(encoding='utf-8', errors='ignore')
        s13 = (ROOT / list(HIST_SOURCES.keys())[2]).read_text(encoding='utf-8', errors='ignore')
        s14 = (ROOT / list(HIST_SOURCES.keys())[3]).read_text(encoding='utf-8', errors='ignore')
        gate('R11_SG7A_corrected_reference_key_semantics', 'SG7A_corrected' in s11)
        gate('R11_resolved_artifact_semantics', 'SG7E_TOP_ARTIFACT_LINEAGE_RESOLVED' in s11)
        gate('R12_time_index_provenance_semantics', 'Candidate performance is prohibited from snapshot selection.' in s12)
        gate('R13_multi_time_contract_semantics', 'SG7E_HISTORICAL_REFERENCE_IS_MULTI_TIME_CONTRACT' in s13)
        gate('R13_all_persisted_snapshots_semantics', 'AUTHORITATIVE_SG7E_REFERENCE_METRICS_CONSUME_ALL_PERSISTED_SNAPSHOTS' in s13)
        gate('R14_reference_key_semantics', 'REFERENCE_KEY = "SG7A_corrected"' in s14)
        gate('R14_expected_times_semantics', '100.0, 250.0, 500.0, 1000.0' in s14)
        gate('R14_threshold_0p5_semantics', 'EXPECTED_THRESHOLD = 0.5' in s14)
        gate('R14_persists_multi_time_reference_semantics', 'V15SG7E1R14_Multi_Time_Historical_Reference.npz' in s14)

        # ------------------------------------------------------------------
        # Actual historical output records
        # ------------------------------------------------------------------
        print('\nACTUAL HISTORICAL V15 SG7E FORENSIC OUTPUT RECORDS')
        hist_paths = [R11_SUMMARY, R11_CONTRACT, R12_SUMMARY, R12_CONTRACT,
                      R13_SUMMARY, R13_CONTRACT, R14_SUMMARY, R14_CONTRACT,
                      R14_NUMERICAL, R14_HASHES]
        hist_output_rows = []
        for p in hist_paths:
            gate(f'historical_output_exists_{p.name}', p.is_file(), p)
            h = sha256_file(p)
            hist_output_rows.append({'path': str(p.relative_to(ROOT)), 'sha256': h})

        r11s = load_json(R11_SUMMARY)
        r11c = load_json(R11_CONTRACT)
        r12s = load_json(R12_SUMMARY)
        r12c = load_json(R12_CONTRACT)
        r13s = load_json(R13_SUMMARY)
        r13c = load_json(R13_CONTRACT)
        r14s = load_json(R14_SUMMARY)
        r14c = load_json(R14_CONTRACT)

        gate('R11_actual_status_resolved', r11s.get('status') == 'SG7E_TOP_ARTIFACT_LINEAGE_RESOLVED')
        gate('R11_actual_diagnosis_unique_authoritative', r11s.get('diagnosis') == 'ONE_TOP_SG7A_CORRECTED_ARTIFACT_HAS_UNIQUE_AUTHORITATIVE_LINEAGE')
        gate('R11_actual_reference_key_exact', r11c.get('reference_key') == EXPECTED_REFERENCE_KEY)
        selected_artifact = r11s.get('selected_artifact') or r11c.get('top_lineage', {}).get('selected_artifact')
        gate('R11_selected_artifact_contract_path_exact',
             normpath_text(selected_artifact).endswith('output/v15_sg7e/v15sg7e_plume_coverage_validation.npz'), selected_artifact)
        gate('R11_no_candidate_performance_used', not bool(r11c.get('constraints', {}).get('candidate_performance_used')))

        gate('R12_actual_artifact_resolved', bool(r12s.get('artifact_resolved')))
        gate('R12_selected_artifact_matches_R11', normpath_text(r12s.get('selected_artifact')).endswith('output/v15_sg7e/v15sg7e_plume_coverage_validation.npz'))
        gate('R12_threshold_unchanged', not bool(r12s.get('threshold_changed')))
        gate('R12_reference_key_exact', r12c.get('reference_key') == EXPECTED_REFERENCE_KEY)

        gate('R13_actual_status_multi_time', r13s.get('status') == 'SG7E_HISTORICAL_REFERENCE_IS_MULTI_TIME_CONTRACT')
        gate('R13_actual_diagnosis_all_snapshots', r13s.get('diagnosis') == 'AUTHORITATIVE_SG7E_REFERENCE_METRICS_CONSUME_ALL_PERSISTED_SNAPSHOTS')
        gate('R13_actual_reference_key_exact', r13c.get('reference_key') == EXPECTED_REFERENCE_KEY)
        gate('R13_actual_shape_exact', r13c.get('artifact', {}).get('shape') == list(EXPECTED_MULTI))
        gate('R13_actual_times_exact', same_times(r13c.get('time_axis', {}).get('values_days')))
        gate('R13_actual_threshold_0p5', abs(float(r13c.get('plume_threshold', {}).get('value')) - 0.5) < 1e-15)
        gate('R13_no_candidate_performance_used', not bool(r13c.get('constraints', {}).get('candidate_performance_used')))
        gate('R13_no_reference_field_frozen', not bool(r13c.get('constraints', {}).get('reference_field_frozen')))

        gate('R14_actual_status_reconstructed', r14s.get('status') == 'SG7E_MULTI_TIME_HISTORICAL_REFERENCE_CONTRACT_RECONSTRUCTED')
        href = r14c.get('historical_reference', {})
        gate('R14_actual_reference_key_exact', href.get('key') == EXPECTED_REFERENCE_KEY)
        gate('R14_actual_shape_exact', href.get('shape') == list(EXPECTED_MULTI))
        gate('R14_actual_times_exact', same_times(href.get('times_days')))
        gate('R14_actual_threshold_0p5', abs(float(href.get('plume_threshold')) - 0.5) < 1e-15)
        gate('R14_no_candidate_performance_used', not bool(r14c.get('constraints', {}).get('candidate_performance_used')))
        gate('R14_no_threshold_change', not bool(r14c.get('constraints', {}).get('threshold_changed')))

        # ------------------------------------------------------------------
        # Exact persisted historical reference tensor
        # ------------------------------------------------------------------
        print('\nEXACT HISTORICAL MULTI-TIME REFERENCE TENSOR / 100-DAY EXTRACTION')
        with np.load(R14_NUMERICAL, allow_pickle=False) as db:
            required = {'SG7A_corrected', 'times_days', 'plume_threshold', 'SG7A_reference_plume_mask'}
            gate('R14_numerical_required_arrays_present', required.issubset(set(db.files)), sorted(db.files))
            ref = np.asarray(db['SG7A_corrected'])
            times = np.asarray(db['times_days'], dtype=np.float64).reshape(-1)
            thr_arr = np.asarray(db['plume_threshold'], dtype=np.float64).reshape(-1)
            masks = np.asarray(db['SG7A_reference_plume_mask'])

        gate('R14_reference_tensor_shape_exact', ref.shape == EXPECTED_MULTI, ref.shape)
        gate('R14_times_array_exact', np.array_equal(times, EXPECTED_TIMES), times.tolist())
        gate('R14_threshold_array_singleton', thr_arr.size == 1)
        gate('R14_threshold_array_exact_0p5', float(thr_arr[0]) == 0.5)
        gate('R14_mask_shape_exact', masks.shape == EXPECTED_MULTI, masks.shape)
        gate('R14_mask_binary', np.all((masks == 0) | (masks == 1)))
        gate('R14_masks_equal_thresholded_reference', np.array_equal(masks.astype(bool), ref >= 0.5))

        ref_hash = sha256_array(ref)
        times_hash = sha256_array(times)
        mask_hash = sha256_array(masks.astype(np.uint8))
        gate('R14_reference_tensor_hash_matches_contract', ref_hash == href.get('sha256'), ref_hash)
        gate('R14_times_hash_matches_contract', times_hash == href.get('times_sha256'), times_hash)
        gate('R14_mask_hash_matches_contract', mask_hash == href.get('plume_mask_sha256'), mask_hash)

        hits = np.where(times == 100.0)[0]
        gate('historical_100d_time_unique', len(hits) == 1, hits.tolist())
        idx100 = int(hits[0])
        gate('historical_100d_index_exact_zero', idx100 == 0, idx100)

        ref100 = np.ascontiguousarray(ref[idx100])
        mask100 = np.ascontiguousarray(masks[idx100].astype(np.uint8))
        gate('historical_100d_reference_shape_exact', ref100.shape == EXPECTED_GRID, ref100.shape)
        gate('historical_100d_reference_all_finite', np.all(np.isfinite(ref100)))
        gate('historical_100d_mask_exact_threshold', np.array_equal(mask100.astype(bool), ref100 >= 0.5))
        snap_hash = sha256_array(ref100)
        mask100_hash = sha256_array(mask100)

        # R14 contract per-time hash must independently identify 100 d.
        rows = r14c.get('per_time_snapshots', [])
        rows100 = [r for r in rows if abs(float(r.get('time_days')) - 100.0) < 1e-15]
        gate('R14_contract_has_unique_100d_snapshot', len(rows100) == 1, len(rows100))
        gate('historical_100d_snapshot_hash_matches_R14_contract', rows100[0].get('snapshot_sha256') == snap_hash, snap_hash)

        # Preserve native dtype; no precision conversion in canonical candidate.
        np.savez_compressed(
            NUMERICAL_OUT,
            reference_truth_100d_native=ref100,
            reference_plume_mask_100d_0p5=mask100,
            physical_time_days=np.asarray(100.0, dtype=np.float64),
            plume_threshold=np.asarray(0.5, dtype=np.float64),
            source_reference_key=np.asarray(EXPECTED_REFERENCE_KEY),
            source_multi_time_reference_array_sha256=np.asarray(ref_hash),
            source_100d_snapshot_array_sha256=np.asarray(snap_hash),
            source_R14_numerical_file_sha256=np.asarray(sha256_file(R14_NUMERICAL)),
        )
        gate('E22_reference_candidate_written', NUMERICAL_OUT.is_file(), NUMERICAL_OUT)
        with np.load(NUMERICAL_OUT, allow_pickle=False) as db2:
            out_ref = np.asarray(db2['reference_truth_100d_native'])
            out_mask = np.asarray(db2['reference_plume_mask_100d_0p5'])
        gate('E22_candidate_native_dtype_preserved', out_ref.dtype == ref100.dtype, f'{out_ref.dtype} vs {ref100.dtype}')
        gate('E22_candidate_snapshot_bitwise_exact', np.array_equal(out_ref, ref100))
        gate('E22_candidate_snapshot_hash_exact', sha256_array(out_ref) == snap_hash)
        gate('E22_candidate_mask_exact', np.array_equal(out_mask, mask100))

        # No V16 comparison/performance evaluation is permitted.
        gate('no_V16_candidate_performance_used_for_reference_selection', True)
        gate('no_authoritative_gate_evaluated_in_E22', True)
        gate('no_threshold_change_in_E22', True)
        gate('diagnostic_0p21_not_used_in_E22', True)
        gate('E22_reference_candidate_not_frozen', True)
        gate('independent_E23_validation_required_before_reference_freeze', True)
        gate('frozen_V16_candidate_not_modified', sha256_file(E18_FROZEN) == EXPECTED_FROZEN_SHA)
        gate('full_grid_plume_not_authorized', True)

        # ------------------------------------------------------------------
        # Persist E22 evidence
        # ------------------------------------------------------------------
        OUT.mkdir(parents=True, exist_ok=True)
        save_csv(SOURCE_CSV, source_rows)
        save_csv(HIST_OUTPUT_CSV, hist_output_rows)

        time_rows = []
        for i, t in enumerate(times):
            s = np.ascontiguousarray(ref[i])
            m = np.ascontiguousarray(masks[i].astype(np.uint8))
            time_rows.append({
                'snapshot_index': i,
                'time_days': float(t),
                'snapshot_sha256': sha256_array(s),
                'plume_mask_sha256_Sge0p5': sha256_array(m),
                'selected_for_V16_100day_reference_candidate': i == idx100,
            })
        save_csv(TIME_CSV, time_rows)
        save_csv(GATE_CSV, [{'gate': k, **v} for k, v in gates.items()])

        morph = morphology(mask100.astype(bool))
        candidate_file_sha = sha256_file(NUMERICAL_OUT)
        r14_file_sha = sha256_file(R14_NUMERICAL)

        lineage = {
            'milestone': 'V16E-22-R1',
            'status': 'V16E22_R1_HISTORICAL_100DAY_REFERENCE_TRUTH_LINEAGE_RECONSTRUCTED',
            'historical_reference_contract': {
                'scope': 'multi-time',
                'key': EXPECTED_REFERENCE_KEY,
                'shape': list(ref.shape),
                'times_days': [float(x) for x in times],
                'plume_threshold': 0.5,
                'source_R14_numerical_file': str(R14_NUMERICAL.relative_to(ROOT)),
                'source_R14_numerical_file_sha256': r14_file_sha,
                'multi_time_reference_array_sha256': ref_hash,
            },
            'v16_100day_reference_truth': {
                'selection_basis': 'exact persisted time-axis equality; no V16 performance; E21 status read from dedicated reference-status artifact',
                'snapshot_index': idx100,
                'time_days': 100.0,
                'shape': list(ref100.shape),
                'dtype': str(ref100.dtype),
                'snapshot_array_sha256': snap_hash,
                'plume_mask_array_sha256': mask100_hash,
                'plume_threshold': 0.5,
                'morphology': morph,
            },
            'candidate_file': {
                'path': str(NUMERICAL_OUT),
                'sha256': candidate_file_sha,
                'frozen': False,
            },
            'constraints': {
                'candidate_performance_used': False,
                'threshold_changed': False,
                'diagnostic_0p21_used': False,
                'deployment_gate_evaluated': False,
                'posthoc_alignment': False,
                'reference_candidate_frozen': False,
                'V16_frozen_candidate_modified': False,
                'full_grid_plume_authorized': False,
            },
            'next_milestone': 'V16E-23 - Independent Historical 100-Day Reference-Truth Reconstruction Validation / Freeze Readiness',
        }
        save_json(LINEAGE_JSON, lineage)

        audit = {
            'milestone': 'V16E-22-R1',
            'status': 'PASS',
            'gates': gates,
            'historical_output_identities': hist_output_rows,
            'parent_E22_runner_sha256': E22_PARENT_RUNNER_SHA,
            'parent_E22_blocked_report_sha256': E22_PARENT_BLOCKED_SHA,
            'parent_E22_failed_gate': E22_PARENT_EXPECTED_FAILED_GATE,
            'reference_tensor_sha256': ref_hash,
            'reference_100d_snapshot_sha256': snap_hash,
            'reference_100d_plume_mask_sha256': mask100_hash,
            'reference_candidate_file_sha256': candidate_file_sha,
            'frozen_candidate_sha256': EXPECTED_FROZEN_SHA,
            'frozen_candidate_modified': False,
            'reference_candidate_frozen': False,
            'deployment_pass_fail_evaluated': False,
            'full_grid_plume_authorized': False,
        }
        save_json(AUDIT_JSON, audit)

        summary = {
            'milestone': 'V16E-22-R1',
            'status': 'PASS',
            'grid_shape': list(EXPECTED_GRID),
            'physical_time_days': 100.0,
            'historical_reference_scope': 'MULTI_TIME_100_250_500_1000_DAYS',
            'E22_R1_repair_scope': 'E21_REFERENCE_STATUS_SCHEMA_ROLE_ONLY',
            'parent_E22_blocked_report_sha256': E22_PARENT_BLOCKED_SHA,
            'historical_reference_key': EXPECTED_REFERENCE_KEY,
            'historical_authoritative_plume_threshold': 0.5,
            'historical_100d_snapshot_index': idx100,
            'historical_100d_snapshot_sha256': snap_hash,
            'historical_100d_reference_dtype': str(ref100.dtype),
            'historical_100d_plume_cells': morph['plume_cells'],
            'historical_100d_footprint_cells': morph['footprint_cells'],
            'historical_100d_vertical_extent_layers': morph['vertical_extent_layers'],
            'reference_candidate_created': True,
            'reference_candidate_frozen': False,
            'reference_candidate_file_sha256': candidate_file_sha,
            'candidate_performance_used_for_reference_selection': False,
            'deployment_pass_fail_evaluated': False,
            'V16_frozen_candidate_modified': False,
            'full_grid_plume_authorized': False,
            'internal_test_reopened': False,
            'OOD_reopened': False,
            'next_milestone': 'V16E-23 - Independent Historical 100-Day Reference-Truth Reconstruction Validation / Freeze Readiness',
        }
        save_json(SUMMARY_JSON, summary)

        HANDOFF_MD.write_text(
            '# PAD-Stream V16E-22-R1 Handoff\n\n'
            'V16E-22-R1 reconstructed the exact historical 100-day SG7E reference-truth candidate '\
            'from the persisted V15 SG7E1R14 multi-time `SG7A_corrected` reference tensor.\n\n'
            f'- Historical reference scope: 100/250/500/1000 days\n'
            f'- Selected V16 evaluation time: 100 days (exact time-axis identity)\n'
            f'- Reference key: `{EXPECTED_REFERENCE_KEY}`\n'
            f'- Historical plume threshold: `S >= 0.5`\n'
            f'- 100-day snapshot SHA-256: `{snap_hash}`\n'
            f'- E22 candidate file SHA-256: `{candidate_file_sha}`\n'
            '- Candidate performance was not used for selection.\n'
            '- Reference candidate is NOT frozen in E22.\n'
            '- No deployment gate was evaluated.\n'
            '- V16 frozen candidate remains unchanged.\n\n'
            'Next: **V16E-23 — Independent Historical 100-Day Reference-Truth Reconstruction Validation / Freeze Readiness**.\n',
            encoding='utf-8'
        )

        print('\n' + '=' * 132)
        print('V16E-22-R1 RESULT: PASS')
        print('=' * 132)
        print(f'Historical reference contract                                    : SG7A_corrected @ [100,250,500,1000] days')
        print(f'Historical authoritative plume threshold                         : S >= {EXPECTED_THRESHOLD}')
        print(f'V16 100-day reference snapshot index                              : {idx100}')
        print(f'100-day reference dtype                                           : {ref100.dtype}')
        print(f'100-day reference min / max / mean                                : {float(np.min(ref100)):.17g} / {float(np.max(ref100)):.17g} / {float(np.mean(ref100)):.17g}')
        print(f'100-day reference plume cells / footprint cells                   : {morph["plume_cells"]} / {morph["footprint_cells"]}')
        print(f'100-day reference vertical extent layers                          : {morph["vertical_extent_layers"]}')
        print(f'100-day snapshot array SHA-256                                    : {snap_hash}')
        print(f'E22 reference candidate file SHA-256                              : {candidate_file_sha}')
        print('Reference candidate created                                       : YES')
        print('Reference candidate frozen                                        : NO')
        print('V16 candidate performance used for reference selection             : NO')
        print('Deployment pass/fail evaluated                                    : NO')
        print('V16 frozen candidate modified                                     : NO')
        print('Full-grid plume authorized                                         : NO')
        print('Internal test / OOD reopened                                      : NO / NO')
        for p in [LINEAGE_JSON, AUDIT_JSON, SUMMARY_JSON, HANDOFF_MD, SOURCE_CSV, HIST_OUTPUT_CSV, TIME_CSV, GATE_CSV]:
            print(f'{p.name} SHA: {sha256_file(p)}')
        print(f'Output: {OUT}')
        print('NEXT: V16E-23 - Independent Historical 100-Day Reference-Truth Reconstruction Validation / Freeze Readiness')
        return 0

    except Exception as exc:
        BLOCKED.mkdir(parents=True, exist_ok=True)
        # Preserve partial gate state; do not modify any upstream artifact.
        payload = {
            'milestone': 'V16E-22-R1',
            'status': 'V16E22_R1_HISTORICAL_100DAY_REFERENCE_TRUTH_LINEAGE_RECONSTRUCTION_BLOCKED',
            'exception': repr(exc),
            'gates': gates,
            'E21_modified': False,
            'frozen_candidate_modified': False,
            'reference_candidate_frozen': False,
            'deployment_pass_fail_evaluated': False,
            'full_grid_plume_authorized': False,
            'next_milestone': 'V16E-22-R2 - Repair only a newly failed V16E-22-R1 provenance/reconstruction gate; preserve E18-R1, E21, and V16E-22 parent evidence unchanged',
            'traceback': traceback.format_exc(),
        }
        save_json(BLOCKED_JSON, payload)
        print(f'\n[FAIL] V16E-22-R1 did not close: {exc}')
        print(f'Blocked report SHA: {sha256_file(BLOCKED_JSON)}')
        print(f'Blocked output: {BLOCKED}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
