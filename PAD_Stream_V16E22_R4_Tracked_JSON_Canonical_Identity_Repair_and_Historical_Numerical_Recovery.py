from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import traceback
import zipfile
import numpy as np

# =============================================================================
# PAD-Stream V16E-22-R4
# Tracked-JSON Canonical Identity Repair / Historical R14 Numerical Recovery / 100-Day Reference-Truth Audit
# =============================================================================
# NO CHANGE TO V16E-18-R1 FROZEN CANDIDATE OR ANY E19/E20/E21 ARTIFACT.
# NO V16 PERFORMANCE USED TO SELECT REFERENCE TRUTH.
# NO SG7E THRESHOLD CHANGE: authoritative historical threshold remains S >= 0.5.
# 0.21 remains diagnostic-only.
# NO DEPLOYMENT GATE EVALUATION OR FULL-GRID PLUME CLAIM.
# NO TRAINING / CHECKPOINT LOAD / MODEL INFERENCE.
# NO PRESSURE / DARCY / POLLOCK / TOF / MAP-BACK / TRANSPORT RECOMPUTATION.
#
# REPAIR SCOPE
# ------------
# V16E-22-R3 authenticated the historical R14 NPZ contents, but its Colab audit
# blocked when it compared a Windows working-tree raw SHA for a tracked JSON file
# with the Linux fresh-clone working-tree raw SHA. Tracked text can undergo checkout
# newline conversion without changing the Git blob or parsed JSON semantics.
#
# R4 repairs ONLY that cross-platform tracked-text identity check. It:
#   1) binds tracked R14 JSON by exact Git-blob SHA-256, normalized-LF SHA-256, and
#      canonical parsed-JSON SHA-256; raw working-tree SHA is retained diagnostic-only;
#   2) keeps every R3 numerical tensor/time/mask/per-time hash check unchanged;
#   3) recovers the original ignored historical R14 NPZ without regeneration;
#   4) creates a 100-day reference-truth CANDIDATE only, still unfrozen pending E23.
# =============================================================================

EXPECTED_GRID = (15, 50, 50)
EXPECTED_MULTI = (4, 15, 50, 50)
EXPECTED_TIMES = np.array([100.0, 250.0, 500.0, 1000.0], dtype=np.float64)
EXPECTED_THRESHOLD = 0.5
EXPECTED_REFERENCE_KEY = 'SG7A_corrected'
EXPECTED_FROZEN_SHA = 'd422dc1e56281c1baf0ae007c62ce4bd69677a232bd1448a5bd79d3177eafaea'

# Parent V16E-22-R3 blocked evidence
E22R3_RUNNER_NAME = 'PAD_Stream_V16E22_R3_R14_PerTime_Hash_Schema_Repair_and_Historical_Numerical_Recovery.py'
E22R3_RUNNER_SHA = 'a0efc5d4b09f35341fe01475955f07b0dc0c14c745e388707064ea4df75ceed8'
E22R3_BLOCKED_REL = Path('provenance/hybrid_dp/V16E22_R3_BLOCKED_HISTORICAL_R14_NUMERICAL_RECOVERY_100DAY_REFERENCE_TRUTH_LINEAGE_RECONSTRUCTION_AUDIT/V16E22_R3_Blocked_Historical_R14_Numerical_Recovery_100Day_Reference_Truth_Audit.json')
E22R3_BLOCKED_SHA = 'f38adc8bfc12525afb477c5157c3f439c45614fa88feb921a998855a57833641'
E22R3_EXPECTED_FAILED_GATE = 'recovery_manifest_contract_SHA_matches_fresh_clone'


# Previous local V16E-22-R2 recovery-pack attempt (never committed because PACK blocked pre-copy/stage)
PREVIOUS_R2_LOCAL_RUNNER_SHA = '9bd00920b3a431491ea7b5e445f0c90c4d112ac9c456cf388607b5e628765386'
PREVIOUS_R2_LOCAL_FAILURE = 'contract_100d_snapshot_hash:6135585d5dadd02f6ba2bcd2dd860c9a681d006526823c4e391e40f9f7f9ddd6'

# Original V16E-22 parent retained for provenance
E22_RUNNER_NAME = 'PAD_Stream_V16E22_Historical_SG7E_100Day_Reference_Truth_Lineage_Reconstruction_Audit.py'
E22_RUNNER_SHA = 'eb3a6396f1e09beedd78e4c791be22e575cd758726871046a29ead34e4fb64cc'

# V16E-21 authority
E21_RUNNER_NAME = 'PAD_Stream_V16E21_Historical_SG7E_Plume_Threshold_and_Reference_Plume_Provenance_Reconciliation.py'
E21_RUNNER_SHA = '59cd2e6bd06ca19efc4f4ad94fee07a4f6bf53c55f9873abf912621157eecb91'
E21_DIR_REL = Path('provenance/hybrid_dp/V16E21_HISTORICAL_SG7E_PLUME_THRESHOLD_REFERENCE_PROVENANCE_RECONCILIATION')
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

# Historical exact source authorities
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

R11_SUMMARY_REL = Path('output/V15_SG7E1R11/PAD_Stream_V15SG7E1R11_Summary.json')
R11_CONTRACT_REL = Path('output/V15_SG7E1R11/V15SG7E1R11_Top_SG7A_Corrected_Lineage_Contract.json')
R12_SUMMARY_REL = Path('output/V15_SG7E1R12/PAD_Stream_V15SG7E1R12_Summary.json')
R12_CONTRACT_REL = Path('output/V15_SG7E1R12/V15SG7E1R12_Historical_Reference_Time_Index_Contract.json')
R13_SUMMARY_REL = Path('output/V15_SG7E1R13/PAD_Stream_V15SG7E1R13_Summary.json')
R13_CONTRACT_REL = Path('output/V15_SG7E1R13/V15SG7E1R13_Per_Time_Snapshot_Correspondence_Contract.json')
R14_SUMMARY_REL = Path('output/V15_SG7E1R14/PAD_Stream_V15SG7E1R14_Summary.json')
R14_CONTRACT_REL = Path('output/V15_SG7E1R14/V15SG7E1R14_Multi_Time_Historical_Reference_Contract.json')
R14_NUMERICAL_REL = Path('output/V15_SG7E1R14/V15SG7E1R14_Multi_Time_Historical_Reference.npz')

RECOVERY_MANIFEST_NAME = 'V16E22_R4_Recovery_Manifest.json'
RECOVERY_NUMERICAL_NAME = 'V15SG7E1R14_Multi_Time_Historical_Reference.npz'


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


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_lf_bytes(data: bytes) -> bytes:
    text = data.decode('utf-8')
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    return text.encode('utf-8')


def normalized_lf_sha256_file(path: Path) -> str:
    return sha256_bytes(normalize_lf_bytes(path.read_bytes()))


def canonical_json_bytes(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def canonical_json_sha256_obj(obj) -> str:
    return sha256_bytes(canonical_json_bytes(obj))


def canonical_json_sha256_file(path: Path) -> str:
    return canonical_json_sha256_obj(load_json(path))


def git_blob_bytes(root: Path, rel: Path) -> bytes:
    spec = f'HEAD:{rel.as_posix()}'
    proc = subprocess.run(
        ['git', '-C', str(root), 'show', spec],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )
    if proc.returncode != 0:
        raise GateError(f'git_blob_unavailable:{spec}:{proc.stderr.decode("utf-8", errors="replace")}')
    return proc.stdout


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
        for key in row:
            if key not in fields:
                fields.append(key)
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
    centroid = [None, None, None] if not len(pts) else [float(x) for x in pts.mean(axis=0)]
    return {
        'plume_cells': cells,
        'footprint_cells': footprint,
        'vertical_extent_layers': int(extent),
        'zmin_layer_zero_based': zmin,
        'zmax_layer_zero_based': zmax,
        'centroid_kji': centroid,
    }


def read_reference_npz(path: Path):
    with np.load(path, allow_pickle=False) as db:
        required = {'SG7A_corrected', 'times_days', 'plume_threshold', 'SG7A_reference_plume_mask'}
        missing = required.difference(db.files)
        if missing:
            raise GateError(f'recovery_npz_missing_arrays:{sorted(missing)}')
        ref = np.asarray(db['SG7A_corrected'])
        times = np.asarray(db['times_days'], dtype=np.float64).reshape(-1)
        threshold = np.asarray(db['plume_threshold'], dtype=np.float64).reshape(-1)
        masks = np.asarray(db['SG7A_reference_plume_mask'])
    return ref, times, threshold, masks


def verify_reference_against_contract(npz_path: Path, contract_path: Path):
    contract = load_json(contract_path)
    href = contract.get('historical_reference', {})
    ref, times, threshold, masks = read_reference_npz(npz_path)

    if ref.shape != EXPECTED_MULTI:
        raise GateError(f'reference_shape:{ref.shape}')
    if not np.array_equal(times, EXPECTED_TIMES):
        raise GateError(f'reference_times:{times.tolist()}')
    if threshold.size != 1 or float(threshold[0]) != EXPECTED_THRESHOLD:
        raise GateError(f'reference_threshold:{threshold.tolist()}')
    if masks.shape != EXPECTED_MULTI:
        raise GateError(f'reference_mask_shape:{masks.shape}')
    if not np.all((masks == 0) | (masks == 1)):
        raise GateError('reference_mask_not_binary')
    if not np.array_equal(masks.astype(bool), ref >= EXPECTED_THRESHOLD):
        raise GateError('reference_masks_not_thresholded_reference')

    ref_hash = sha256_array(ref)
    times_hash = sha256_array(times)
    mask_hash = sha256_array(masks.astype(np.uint8))
    if ref_hash != href.get('sha256'):
        raise GateError(f'reference_tensor_hash:{ref_hash}')
    if times_hash != href.get('times_sha256'):
        raise GateError(f'reference_times_hash:{times_hash}')
    if mask_hash != href.get('plume_mask_sha256'):
        raise GateError(f'reference_mask_hash:{mask_hash}')

    hits = np.where(times == 100.0)[0]
    if len(hits) != 1 or int(hits[0]) != 0:
        raise GateError(f'reference_100d_index:{hits.tolist()}')
    idx100 = int(hits[0])
    ref100 = np.ascontiguousarray(ref[idx100])
    mask100 = np.ascontiguousarray(masks[idx100].astype(np.uint8))
    snap_hash = sha256_array(ref100)
    mask100_hash = sha256_array(mask100)

    rows = contract.get('per_time_snapshots', [])
    if len(rows) != 4:
        raise GateError(f'contract_per_time_snapshot_count:{len(rows)}')
    if any('saturation_sha256' not in r for r in rows):
        raise GateError('contract_saturation_sha256_schema_missing')
    if any('snapshot_sha256' in r for r in rows):
        raise GateError('contract_unexpected_snapshot_sha256_schema')

    rows100 = [r for r in rows if abs(float(r.get('time_days')) - 100.0) < 1e-15]
    if len(rows100) != 1:
        raise GateError(f'contract_100d_snapshot_count:{len(rows100)}')
    row100 = rows100[0]
    if row100.get('saturation_sha256') != snap_hash:
        raise GateError(f'contract_100d_saturation_hash:{snap_hash}')
    if row100.get('plume_mask_sha256') != mask100_hash:
        raise GateError(f'contract_100d_plume_mask_hash:{mask100_hash}')

    return {
        'contract': contract,
        'href': href,
        'ref': ref,
        'times': times,
        'threshold': threshold,
        'masks': masks,
        'ref_hash': ref_hash,
        'times_hash': times_hash,
        'mask_hash': mask_hash,
        'idx100': idx100,
        'ref100': ref100,
        'mask100': mask100,
        'snap_hash': snap_hash,
        'mask100_hash': mask100_hash,
        'per_time_hash_field': 'saturation_sha256',
        'r2_wrong_field_absent': all('snapshot_sha256' not in r for r in rows),
        'historical_hash_field_present': all('saturation_sha256' in r for r in rows),
    }


def pack_mode(project_root: Path, output_zip: Path) -> int:
    root = project_root.resolve()
    r14_source = root / 'PAD_Stream_V15SG7E1R14_Multi_Time_Historical_Reference_Reconstruction_Contract_Audit.py'
    r14_summary = root / R14_SUMMARY_REL
    r14_contract = root / R14_CONTRACT_REL
    r14_numerical = root / R14_NUMERICAL_REL

    print('\n' + '=' * 128)
    print('V16E-22-R4 LOCAL HISTORICAL R14 NUMERICAL-ARTIFACT RECOVERY PACK')
    print('=' * 128)
    print('READ-ONLY VALIDATION OF EXISTING HISTORICAL R14 NUMERICAL TRUTH. NO REGENERATION.')

    if not r14_source.is_file():
        raise FileNotFoundError(r14_source)
    if sha256_file(r14_source) != HIST_SOURCES[r14_source.name]:
        raise GateError('R14_source_SHA_mismatch')
    print('[PASS] R14 historical source SHA exact')

    for p in (r14_summary, r14_contract):
        if not p.is_file():
            raise FileNotFoundError(p)
        print(f'[PASS] historical record exists: {p.relative_to(root)}')

    if not r14_numerical.is_file():
        raise FileNotFoundError(
            f'Missing ignored historical R14 numerical artifact: {r14_numerical}\n'
            'R4 will not regenerate or invent it. Locate the original local V15 output before continuing.'
        )
    print(f'[PASS] ignored historical R14 numerical artifact exists: {r14_numerical}')

    r14s = load_json(r14_summary)
    if r14s.get('status') != 'SG7E_MULTI_TIME_HISTORICAL_REFERENCE_CONTRACT_RECONSTRUCTED':
        raise GateError(f'R14_summary_status:{r14s.get("status")}')
    print('[PASS] R14 executed status reconstructed')

    # ------------------------------------------------------------------
    # Cross-platform tracked-JSON identity repair.
    # Raw worktree bytes are NOT authority because Git checkout filters may
    # normalize line endings differently on Windows vs Linux. Bind exact Git
    # blob content plus normalized-LF and canonical parsed JSON instead.
    # ------------------------------------------------------------------
    contract_obj_local = load_json(r14_contract)
    summary_obj_local = load_json(r14_summary)
    contract_blob = git_blob_bytes(root, R14_CONTRACT_REL)
    summary_blob = git_blob_bytes(root, R14_SUMMARY_REL)
    contract_obj_blob = json.loads(contract_blob.decode('utf-8'))
    summary_obj_blob = json.loads(summary_blob.decode('utf-8'))

    contract_local_lf = normalized_lf_sha256_file(r14_contract)
    contract_blob_lf = sha256_bytes(normalize_lf_bytes(contract_blob))
    summary_local_lf = normalized_lf_sha256_file(r14_summary)
    summary_blob_lf = sha256_bytes(normalize_lf_bytes(summary_blob))
    contract_local_canon = canonical_json_sha256_obj(contract_obj_local)
    contract_blob_canon = canonical_json_sha256_obj(contract_obj_blob)
    summary_local_canon = canonical_json_sha256_obj(summary_obj_local)
    summary_blob_canon = canonical_json_sha256_obj(summary_obj_blob)

    if contract_local_lf != contract_blob_lf:
        raise GateError('local_R14_contract_normalized_LF_differs_from_Git_blob')
    if summary_local_lf != summary_blob_lf:
        raise GateError('local_R14_summary_normalized_LF_differs_from_Git_blob')
    if contract_local_canon != contract_blob_canon:
        raise GateError('local_R14_contract_canonical_JSON_differs_from_Git_blob')
    if summary_local_canon != summary_blob_canon:
        raise GateError('local_R14_summary_canonical_JSON_differs_from_Git_blob')
    print('[PASS] R3 raw-working-tree SHA failure mechanism isolated from tracked Git-blob identity')
    print('[PASS] local R14 contract normalized-LF identity equals Git blob')
    print('[PASS] local R14 contract canonical JSON identity equals Git blob')
    print('[PASS] local R14 summary normalized-LF identity equals Git blob')
    print('[PASS] local R14 summary canonical JSON identity equals Git blob')

    verified = verify_reference_against_contract(r14_numerical, r14_contract)
    print('[PASS] R2 failure mechanism reproduced: R14 per-time contract uses saturation_sha256, not snapshot_sha256')
    print('[PASS] R3 schema repair reads historical saturation_sha256 exactly')
    print('[PASS] R14 numerical tensor/content exactly matches tracked historical contract')
    print(f'[PASS] historical 100-day saturation SHA exact: {verified["snap_hash"]}')
    print(f'[PASS] historical 100-day plume-mask SHA exact: {verified["mask100_hash"]}')

    manifest = {
        'milestone': 'V16E-22-R4',
        'bundle_role': 'LOCAL_IGNORED_R14_NUMERICAL_ARTIFACT_RECOVERY',
        'schema_repair': 'TRACKED_JSON_RAW_WORKTREE_SHA_TO_GIT_BLOB_NORMALIZED_LF_CANONICAL_JSON_PLUS_R14_PER_TIME_HASH_FIELD_REPAIR',
        'previous_R3_colab_failure': 'recovery_manifest_contract_SHA_matches_fresh_clone',
        'historical_per_time_hash_field': 'saturation_sha256',
        'source_relative_path': str(R14_NUMERICAL_REL).replace('\\', '/'),
        'source_file_sha256': sha256_file(r14_numerical),
        'source_contract_relative_path': str(R14_CONTRACT_REL).replace('\\', '/'),
        'source_contract_worktree_raw_sha256': sha256_file(r14_contract),
        'source_contract_normalized_lf_sha256': contract_local_lf,
        'source_contract_canonical_json_sha256': contract_local_canon,
        'source_contract_git_blob_sha256': sha256_bytes(contract_blob),
        'source_summary_relative_path': str(R14_SUMMARY_REL).replace('\\', '/'),
        'source_summary_worktree_raw_sha256': sha256_file(r14_summary),
        'source_summary_normalized_lf_sha256': summary_local_lf,
        'source_summary_canonical_json_sha256': summary_local_canon,
        'source_summary_git_blob_sha256': sha256_bytes(summary_blob),
        'reference_key': EXPECTED_REFERENCE_KEY,
        'shape': list(verified['ref'].shape),
        'times_days': [float(x) for x in verified['times']],
        'plume_threshold': EXPECTED_THRESHOLD,
        'multi_time_reference_array_sha256': verified['ref_hash'],
        'times_array_sha256': verified['times_hash'],
        'plume_mask_array_sha256': verified['mask_hash'],
        'reference_100d_snapshot_index': verified['idx100'],
        'reference_100d_snapshot_array_sha256': verified['snap_hash'],
        'reference_100d_plume_mask_array_sha256': verified['mask100_hash'],
        'constraints': {
            'numerical_truth_regenerated': False,
            'candidate_performance_used': False,
            'threshold_changed': False,
            'posthoc_alignment': False,
            'deployment_gate_evaluated': False,
        },
    }

    output_zip = output_zip.resolve()
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    if output_zip.exists():
        output_zip.unlink()

    with tempfile.TemporaryDirectory(prefix='V16E22_R4_pack_') as td:
        td = Path(td)
        manifest_path = td / RECOVERY_MANIFEST_NAME
        save_json(manifest_path, manifest)
        with zipfile.ZipFile(output_zip, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(manifest_path, arcname=RECOVERY_MANIFEST_NAME)
            zf.write(r14_numerical, arcname=RECOVERY_NUMERICAL_NAME)

    # Re-open bundle and prove exact two-member composition.
    with zipfile.ZipFile(output_zip, 'r') as zf:
        names = zf.namelist()
    if set(names) != {RECOVERY_MANIFEST_NAME, RECOVERY_NUMERICAL_NAME} or len(names) != 2:
        raise GateError(f'recovery_bundle_members:{names}')

    print('\n' + '=' * 128)
    print('V16E-22-R4 LOCAL RECOVERY PACK: PASS')
    print('=' * 128)
    print(f'Recovery bundle: {output_zip}')
    print(f'Recovery bundle SHA-256: {sha256_file(output_zip)}')
    print(f'Historical R14 numerical file SHA-256: {manifest["source_file_sha256"]}')
    print('NEXT: commit/push only the V16E-22-R4 runner, then upload this recovery ZIP in Colab.')
    return 0


def audit_mode(project_root: Path, drive_root: Path, recovery_zip: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    recovery_zip = recovery_zip.resolve()

    out = drive / 'provenance/hybrid_dp/V16E22_R4_HISTORICAL_R14_NUMERICAL_RECOVERY_100DAY_REFERENCE_TRUTH_LINEAGE_RECONSTRUCTION_AUDIT'
    blocked = drive / 'provenance/hybrid_dp/V16E22_R4_BLOCKED_HISTORICAL_R14_NUMERICAL_RECOVERY_100DAY_REFERENCE_TRUTH_LINEAGE_RECONSTRUCTION_AUDIT'
    blocked_json = blocked / 'V16E22_R4_Blocked_Historical_R14_Numerical_Recovery_100Day_Reference_Truth_Audit.json'
    e21_dir = drive / E21_DIR_REL
    e18_frozen = drive / ('provenance/hybrid_dp/V16E18_R1_FROZEN_SGSIM_100D_FULL_GRID_CANDIDATE/'
                          'frozen_full_grid/V16E18_R1_Frozen_SGSim_100Day_Full_Grid_Candidate.npz')
    e22r3_blocked = drive / E22R3_BLOCKED_REL

    numerical_out = out / 'V16E22_R4_Historical_SG7E_100Day_Reference_Truth_Candidate.npz'
    lineage_json = out / 'V16E22_R4_Historical_100Day_Reference_Truth_Lineage_Contract.json'
    audit_json = out / 'V16E22_R4_Reference_Truth_Reconstruction_Audit.json'
    summary_json = out / 'PAD_Stream_V16E22_R4_Summary.json'
    handoff_md = out / 'V16E22_R4_Handoff.md'
    source_csv = out / 'V16E22_R4_Historical_Source_Authority.csv'
    hist_output_csv = out / 'V16E22_R4_Historical_Output_Identity.csv'
    time_csv = out / 'V16E22_R4_Reference_Time_Snapshot_Identity.csv'
    gate_csv = out / 'V16E22_R4_Final_Gate_Matrix.csv'
    recovery_csv = out / 'V16E22_R4_Recovery_Bundle_Identity.csv'

    gates = {}

    def gate(name, condition, detail=''):
        ok = bool(condition)
        gates[name] = {'passed': ok, 'detail': str(detail)}
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f': {detail}' if detail else ''))
        if not ok:
            raise GateError(name)

    print('\n' + '=' * 132)
    print('PAD-Stream V16E-22-R4 Historical R14 Numerical Recovery / 100-Day Reference-Truth Lineage Reconstruction Audit')
    print('=' * 132)
    print('NO HISTORICAL NUMERICAL REGENERATION. RECOVERY IS BYTE/CONTENT VERIFIED AGAINST TRACKED R14 CONTRACT.')
    print('NO V16 PERFORMANCE USED TO SELECT REFERENCE TRUTH.')
    print('NO SG7E THRESHOLD CHANGE: AUTHORITATIVE HISTORICAL THRESHOLD REMAINS S >= 0.5.')
    print('0.21 REMAINS DIAGNOSTIC-ONLY. NO DEPLOYMENT GATE EVALUATION. NO REFERENCE FREEZE.')

    try:
        # ------------------------------------------------------------------
        # Parent R3 failure evidence
        # ------------------------------------------------------------------
        print('\nBLOCKED V16E-22-R3 PARENT EVIDENCE')
        e22r3_runner = root / E22R3_RUNNER_NAME
        gate('E22R3_parent_runner_exists', e22r3_runner.is_file(), e22r3_runner)
        gate('E22R3_parent_runner_SHA_exact', sha256_file(e22r3_runner) == E22R3_RUNNER_SHA)
        gate('E22R3_parent_blocked_report_exists', e22r3_blocked.is_file(), e22r3_blocked)
        gate('E22R3_parent_blocked_report_SHA_exact', sha256_file(e22r3_blocked) == E22R3_BLOCKED_SHA)
        parent = load_json(e22r3_blocked)
        gate('E22R3_parent_status_BLOCKED',
             parent.get('status') == 'V16E22_R3_HISTORICAL_R14_NUMERICAL_RECOVERY_100DAY_REFERENCE_TRUTH_LINEAGE_RECONSTRUCTION_BLOCKED')
        pgates = parent.get('gates', {})
        failed = [k for k, v in pgates.items() if not bool(v.get('passed', False))]
        gate('E22R3_parent_single_failed_gate', failed == [E22R3_EXPECTED_FAILED_GATE], failed)
        gate('E22R3_parent_exception_exact_gate',
             parent.get('exception') == "GateError('recovery_manifest_contract_SHA_matches_fresh_clone')",
             parent.get('exception'))
        gate('E22R3_parent_all_prior_recorded_gates_passed',
             all(bool(v.get('passed', False)) for k, v in pgates.items() if k != E22R3_EXPECTED_FAILED_GATE))
        gate('E22R3_parent_E21_not_modified', not bool(parent.get('E21_modified')))
        gate('E22R3_parent_frozen_candidate_not_modified', not bool(parent.get('frozen_candidate_modified')))
        gate('E22R3_parent_reference_candidate_not_frozen', not bool(parent.get('reference_candidate_frozen')))
        gate('E22R3_parent_no_deployment_evaluation', not bool(parent.get('deployment_pass_fail_evaluated')))
        gate('E22R3_parent_no_full_grid_plume_authorization', not bool(parent.get('full_grid_plume_authorized')))

        # ------------------------------------------------------------------
        # Immutable E21 and frozen candidate
        # ------------------------------------------------------------------
        print('\nV16E-21 / FROZEN V16 AUTHORITY')
        e21_runner = root / E21_RUNNER_NAME
        gate('E21_runner_exists', e21_runner.is_file(), e21_runner)
        gate('E21_runner_SHA_exact', sha256_file(e21_runner) == E21_RUNNER_SHA)
        for name, expected in E21_ARTIFACTS.items():
            p = e21_dir / name
            gate(f'E21_{name}_exists', p.is_file(), p)
            gate(f'E21_{name}_SHA_exact', sha256_file(p) == expected)
        e21_summary = load_json(e21_dir / 'PAD_Stream_V16E21_Summary.json')
        e21_thr = load_json(e21_dir / 'V16E21_Historical_Plume_Threshold_Contract.json')
        e21_ref = load_json(e21_dir / 'V16E21_Reference_Plume_Provenance_Status.json')
        gate('E21_summary_status_PASS', e21_summary.get('status') == 'PASS')
        gate('E21_authoritative_threshold_0p5', float(e21_summary.get('historical_authoritative_plume_threshold')) == 0.5)
        gate('E21_summary_reference_status_generic_exact',
             e21_summary.get('reference_truth_status') == 'UNRESOLVED_REQUIRES_LINEAGE_RECONSTRUCTION')
        gate('E21_reference_status_artifact_100d_lineage_exact',
             e21_ref.get('reference_truth_status') == 'UNRESOLVED_REQUIRES_HISTORICAL_100_DAY_TRUTH_LINEAGE_RECONSTRUCTION')
        gate('E21_threshold_contract_0p5', abs(float(e21_thr.get('authoritative_plume_threshold', 0.5)) - 0.5) < 1e-15)
        gate('E21_reference_unselected', not bool(e21_ref.get('reference_plume_selected', False)))
        gate('E21_no_deployment_evaluation', not bool(e21_summary.get('deployment_pass_fail_evaluated')))
        gate('E18R1_frozen_candidate_exists', e18_frozen.is_file(), e18_frozen)
        gate('E18R1_frozen_candidate_SHA_exact', sha256_file(e18_frozen) == EXPECTED_FROZEN_SHA)

        # ------------------------------------------------------------------
        # Historical source and tracked output authority
        # ------------------------------------------------------------------
        print('\nHISTORICAL V15 SG7E SOURCE / TRACKED OUTPUT AUTHORITY')
        source_rows = []
        for name, expected in HIST_SOURCES.items():
            p = root / name
            gate(f'{name}_exists', p.is_file(), p)
            actual = sha256_file(p)
            gate(f'{name}_SHA_exact', actual == expected, actual)
            source_rows.append({'file': name, 'sha256': actual, 'role': 'historical_reference_lineage_source'})

        hist_rels = [R11_SUMMARY_REL, R11_CONTRACT_REL, R12_SUMMARY_REL, R12_CONTRACT_REL,
                     R13_SUMMARY_REL, R13_CONTRACT_REL, R14_SUMMARY_REL, R14_CONTRACT_REL]
        hist_output_rows = []
        for rel in hist_rels:
            p = root / rel
            gate(f'historical_tracked_output_exists_{p.name}', p.is_file(), p)
            hist_output_rows.append({'path': str(rel).replace('\\', '/'), 'sha256': sha256_file(p), 'role': 'tracked_historical_output'})

        # Reproduce the R1 fresh-clone limitation, without treating it as loss of truth.
        fresh_clone_r14_numerical = root / R14_NUMERICAL_REL
        gate('R14_numerical_absent_from_fresh_clone_reproduced', not fresh_clone_r14_numerical.exists(), fresh_clone_r14_numerical)

        r11s = load_json(root / R11_SUMMARY_REL)
        r11c = load_json(root / R11_CONTRACT_REL)
        r12s = load_json(root / R12_SUMMARY_REL)
        r12c = load_json(root / R12_CONTRACT_REL)
        r13s = load_json(root / R13_SUMMARY_REL)
        r13c = load_json(root / R13_CONTRACT_REL)
        r14s = load_json(root / R14_SUMMARY_REL)
        r14c = load_json(root / R14_CONTRACT_REL)
        href = r14c.get('historical_reference', {})

        gate('R11_actual_status_resolved', r11s.get('status') == 'SG7E_TOP_ARTIFACT_LINEAGE_RESOLVED')
        gate('R11_actual_reference_key_exact', r11c.get('reference_key') == EXPECTED_REFERENCE_KEY)
        selected_artifact = r11s.get('selected_artifact') or r11c.get('top_lineage', {}).get('selected_artifact')
        gate('R11_selected_artifact_contract_path_exact',
             normpath_text(selected_artifact).endswith('output/v15_sg7e/v15sg7e_plume_coverage_validation.npz'), selected_artifact)
        gate('R11_no_candidate_performance_used', not bool(r11c.get('constraints', {}).get('candidate_performance_used')))

        gate('R12_actual_artifact_resolved', bool(r12s.get('artifact_resolved')))
        gate('R12_reference_key_exact', r12c.get('reference_key') == EXPECTED_REFERENCE_KEY)
        gate('R12_threshold_unchanged', not bool(r12s.get('threshold_changed')))

        gate('R13_actual_status_multi_time', r13s.get('status') == 'SG7E_HISTORICAL_REFERENCE_IS_MULTI_TIME_CONTRACT')
        gate('R13_actual_diagnosis_all_snapshots', r13s.get('diagnosis') == 'AUTHORITATIVE_SG7E_REFERENCE_METRICS_CONSUME_ALL_PERSISTED_SNAPSHOTS')
        gate('R13_actual_shape_exact', r13c.get('artifact', {}).get('shape') == list(EXPECTED_MULTI))
        gate('R13_actual_times_exact', same_times(r13c.get('time_axis', {}).get('values_days')))
        gate('R13_actual_threshold_0p5', abs(float(r13c.get('plume_threshold', {}).get('value')) - 0.5) < 1e-15)
        gate('R13_no_candidate_performance_used', not bool(r13c.get('constraints', {}).get('candidate_performance_used')))

        gate('R14_actual_status_reconstructed', r14s.get('status') == 'SG7E_MULTI_TIME_HISTORICAL_REFERENCE_CONTRACT_RECONSTRUCTED')
        gate('R14_actual_reference_key_exact', href.get('key') == EXPECTED_REFERENCE_KEY)
        gate('R14_actual_shape_exact', href.get('shape') == list(EXPECTED_MULTI))
        gate('R14_actual_times_exact', same_times(href.get('times_days')))
        gate('R14_actual_threshold_0p5', abs(float(href.get('plume_threshold')) - 0.5) < 1e-15)
        gate('R14_no_candidate_performance_used', not bool(r14c.get('constraints', {}).get('candidate_performance_used')))
        gate('R14_no_threshold_change', not bool(r14c.get('constraints', {}).get('threshold_changed')))

        # ------------------------------------------------------------------
        # Recovery bundle authority
        # ------------------------------------------------------------------
        print('\nLOCAL HISTORICAL R14 NUMERICAL RECOVERY BUNDLE')
        gate('recovery_zip_exists', recovery_zip.is_file(), recovery_zip)
        recovery_zip_sha = sha256_file(recovery_zip)
        with zipfile.ZipFile(recovery_zip, 'r') as zf:
            names = zf.namelist()
            gate('recovery_zip_exact_members',
                 len(names) == 2 and set(names) == {RECOVERY_MANIFEST_NAME, RECOVERY_NUMERICAL_NAME}, names)
            # Reject path traversal / nested names.
            gate('recovery_zip_flat_safe_members', all(Path(n).name == n for n in names), names)
            manifest = json.loads(zf.read(RECOVERY_MANIFEST_NAME).decode('utf-8'))
            with tempfile.TemporaryDirectory(prefix='V16E22_R4_recovery_') as td:
                td = Path(td)
                recovered_npz = td / RECOVERY_NUMERICAL_NAME
                recovered_npz.write_bytes(zf.read(RECOVERY_NUMERICAL_NAME))

                gate('recovery_manifest_milestone_exact', manifest.get('milestone') == 'V16E-22-R4')
                gate('recovery_manifest_role_exact', manifest.get('bundle_role') == 'LOCAL_IGNORED_R14_NUMERICAL_ARTIFACT_RECOVERY')
                gate('recovery_manifest_schema_repair_exact', manifest.get('schema_repair') == 'TRACKED_JSON_RAW_WORKTREE_SHA_TO_GIT_BLOB_NORMALIZED_LF_CANONICAL_JSON_PLUS_R14_PER_TIME_HASH_FIELD_REPAIR')
                gate('recovery_manifest_historical_hash_field_exact', manifest.get('historical_per_time_hash_field') == 'saturation_sha256')
                gate('recovery_manifest_source_path_exact', manifest.get('source_relative_path') == str(R14_NUMERICAL_REL).replace('\\', '/'))
                gate('recovery_manifest_contract_path_exact', manifest.get('source_contract_relative_path') == str(R14_CONTRACT_REL).replace('\\', '/'))
                fresh_contract = root / R14_CONTRACT_REL
                fresh_summary = root / R14_SUMMARY_REL
                fresh_contract_blob = git_blob_bytes(root, R14_CONTRACT_REL)
                fresh_summary_blob = git_blob_bytes(root, R14_SUMMARY_REL)
                fresh_contract_raw = sha256_file(fresh_contract)
                fresh_summary_raw = sha256_file(fresh_summary)
                fresh_contract_lf = normalized_lf_sha256_file(fresh_contract)
                fresh_summary_lf = normalized_lf_sha256_file(fresh_summary)
                fresh_contract_canon = canonical_json_sha256_file(fresh_contract)
                fresh_summary_canon = canonical_json_sha256_file(fresh_summary)

                gate('R3_failed_raw_contract_SHA_is_worktree_platform_dependent_diagnostic', True,
                     f"local_raw={manifest.get('source_contract_worktree_raw_sha256')} fresh_raw={fresh_contract_raw}")
                gate('recovery_manifest_contract_git_blob_SHA_matches_fresh_clone',
                     manifest.get('source_contract_git_blob_sha256') == sha256_bytes(fresh_contract_blob))
                gate('recovery_manifest_contract_normalized_LF_SHA_matches_fresh_clone',
                     manifest.get('source_contract_normalized_lf_sha256') == fresh_contract_lf)
                gate('recovery_manifest_contract_canonical_JSON_SHA_matches_fresh_clone',
                     manifest.get('source_contract_canonical_json_sha256') == fresh_contract_canon)
                gate('fresh_clone_contract_worktree_matches_Git_blob_canonical_JSON',
                     fresh_contract_canon == canonical_json_sha256_obj(json.loads(fresh_contract_blob.decode('utf-8'))))

                gate('R3_raw_summary_SHA_is_worktree_platform_dependent_diagnostic', True,
                     f"local_raw={manifest.get('source_summary_worktree_raw_sha256')} fresh_raw={fresh_summary_raw}")
                gate('recovery_manifest_summary_git_blob_SHA_matches_fresh_clone',
                     manifest.get('source_summary_git_blob_sha256') == sha256_bytes(fresh_summary_blob))
                gate('recovery_manifest_summary_normalized_LF_SHA_matches_fresh_clone',
                     manifest.get('source_summary_normalized_lf_sha256') == fresh_summary_lf)
                gate('recovery_manifest_summary_canonical_JSON_SHA_matches_fresh_clone',
                     manifest.get('source_summary_canonical_json_sha256') == fresh_summary_canon)
                gate('fresh_clone_summary_worktree_matches_Git_blob_canonical_JSON',
                     fresh_summary_canon == canonical_json_sha256_obj(json.loads(fresh_summary_blob.decode('utf-8'))))
                gate('recovery_numerical_file_SHA_matches_manifest',
                     sha256_file(recovered_npz) == manifest.get('source_file_sha256'), sha256_file(recovered_npz))
                gate('recovery_manifest_reference_key_exact', manifest.get('reference_key') == EXPECTED_REFERENCE_KEY)
                gate('recovery_manifest_shape_exact', manifest.get('shape') == list(EXPECTED_MULTI))
                gate('recovery_manifest_times_exact', same_times(manifest.get('times_days')))
                gate('recovery_manifest_threshold_0p5', abs(float(manifest.get('plume_threshold')) - 0.5) < 1e-15)
                constraints = manifest.get('constraints', {})
                gate('recovery_manifest_no_regeneration', not bool(constraints.get('numerical_truth_regenerated')))
                gate('recovery_manifest_no_candidate_performance', not bool(constraints.get('candidate_performance_used')))
                gate('recovery_manifest_no_threshold_change', not bool(constraints.get('threshold_changed')))
                gate('recovery_manifest_no_gate_evaluation', not bool(constraints.get('deployment_gate_evaluated')))

                verified = verify_reference_against_contract(recovered_npz, root / R14_CONTRACT_REL)
                gate('R2_failure_mechanism_wrong_snapshot_sha256_field_absent', verified['r2_wrong_field_absent'])
                gate('R3_historical_saturation_sha256_schema_present', verified['historical_hash_field_present'])
                gate('R3_historical_per_time_hash_field_exact', verified['per_time_hash_field'] == 'saturation_sha256')
                gate('recovered_R14_reference_tensor_hash_exact', verified['ref_hash'] == manifest.get('multi_time_reference_array_sha256'), verified['ref_hash'])
                gate('recovered_R14_times_hash_exact', verified['times_hash'] == manifest.get('times_array_sha256'), verified['times_hash'])
                gate('recovered_R14_mask_hash_exact', verified['mask_hash'] == manifest.get('plume_mask_array_sha256'), verified['mask_hash'])
                gate('recovered_R14_100d_snapshot_hash_exact', verified['snap_hash'] == manifest.get('reference_100d_snapshot_array_sha256'), verified['snap_hash'])
                gate('recovered_R14_100d_mask_hash_exact', verified['mask100_hash'] == manifest.get('reference_100d_plume_mask_array_sha256'), verified['mask100_hash'])
                gate('historical_100d_time_unique', verified['idx100'] == 0, verified['idx100'])

                ref100 = verified['ref100']
                mask100 = verified['mask100']
                snap_hash = verified['snap_hash']
                mask100_hash = verified['mask100_hash']

                out.mkdir(parents=True, exist_ok=True)
                np.savez_compressed(
                    numerical_out,
                    reference_truth_100d_native=ref100,
                    reference_plume_mask_100d_0p5=mask100,
                    physical_time_days=np.asarray(100.0, dtype=np.float64),
                    plume_threshold=np.asarray(0.5, dtype=np.float64),
                    source_reference_key=np.asarray(EXPECTED_REFERENCE_KEY),
                    source_multi_time_reference_array_sha256=np.asarray(verified['ref_hash']),
                    source_100d_snapshot_array_sha256=np.asarray(snap_hash),
                    source_R14_recovered_numerical_file_sha256=np.asarray(manifest.get('source_file_sha256')),
                    source_recovery_bundle_sha256=np.asarray(recovery_zip_sha),
                )

        gate('E22R4_reference_candidate_written', numerical_out.is_file(), numerical_out)
        with np.load(numerical_out, allow_pickle=False) as db2:
            out_ref = np.asarray(db2['reference_truth_100d_native'])
            out_mask = np.asarray(db2['reference_plume_mask_100d_0p5'])
        gate('E22R4_candidate_native_dtype_preserved', out_ref.dtype == ref100.dtype, f'{out_ref.dtype} vs {ref100.dtype}')
        gate('E22R4_candidate_snapshot_bitwise_exact', np.array_equal(out_ref, ref100))
        gate('E22R4_candidate_snapshot_hash_exact', sha256_array(out_ref) == snap_hash)
        gate('E22R4_candidate_mask_exact', np.array_equal(out_mask, mask100))

        # Firewalls
        gate('no_V16_candidate_performance_used_for_reference_selection', True)
        gate('no_authoritative_gate_evaluated_in_E22R4', True)
        gate('no_threshold_change_in_E22R4', True)
        gate('diagnostic_0p21_not_used_in_E22R4', True)
        gate('E22R4_reference_candidate_not_frozen', True)
        gate('independent_E23_validation_required_before_reference_freeze', True)
        gate('frozen_V16_candidate_not_modified', sha256_file(e18_frozen) == EXPECTED_FROZEN_SHA)
        gate('full_grid_plume_not_authorized', True)

        # Persist evidence
        save_csv(source_csv, source_rows)
        save_csv(hist_output_csv, hist_output_rows)
        save_csv(recovery_csv, [{
            'recovery_bundle_sha256': recovery_zip_sha,
            'historical_R14_numerical_file_sha256': manifest.get('source_file_sha256'),
            'historical_R14_contract_worktree_raw_sha256_diagnostic': manifest.get('source_contract_worktree_raw_sha256'),
            'historical_R14_contract_git_blob_sha256': manifest.get('source_contract_git_blob_sha256'),
            'historical_R14_contract_normalized_lf_sha256': manifest.get('source_contract_normalized_lf_sha256'),
            'historical_R14_contract_canonical_json_sha256': manifest.get('source_contract_canonical_json_sha256'),
            'historical_R14_summary_worktree_raw_sha256_diagnostic': manifest.get('source_summary_worktree_raw_sha256'),
            'historical_R14_summary_git_blob_sha256': manifest.get('source_summary_git_blob_sha256'),
            'historical_R14_summary_normalized_lf_sha256': manifest.get('source_summary_normalized_lf_sha256'),
            'historical_R14_summary_canonical_json_sha256': manifest.get('source_summary_canonical_json_sha256'),
            'multi_time_reference_array_sha256': verified['ref_hash'],
            'reference_100d_snapshot_array_sha256': snap_hash,
            'numerical_truth_regenerated': False,
        }])
        time_rows = []
        for i, t in enumerate(verified['times']):
            s = np.ascontiguousarray(verified['ref'][i])
            m = np.ascontiguousarray(verified['masks'][i].astype(np.uint8))
            time_rows.append({
                'snapshot_index': i,
                'time_days': float(t),
                'snapshot_sha256': sha256_array(s),
                'plume_mask_sha256_Sge0p5': sha256_array(m),
                'selected_for_V16_100day_reference_candidate': i == verified['idx100'],
            })
        save_csv(time_csv, time_rows)
        save_csv(gate_csv, [{'gate': k, **v} for k, v in gates.items()])

        morph = morphology(mask100.astype(bool))
        candidate_file_sha = sha256_file(numerical_out)
        lineage = {
            'milestone': 'V16E-22-R4',
            'status': 'V16E22_R4_HISTORICAL_100DAY_REFERENCE_TRUTH_LINEAGE_RECONSTRUCTED',
            'repair_scope': 'TRACKED_JSON_CANONICAL_IDENTITY_REPAIR_PLUS_R14_PER_TIME_HASH_SCHEMA_AND_GIT_IGNORED_NUMERICAL_RECOVERY',
            'previous_R2_local_runner_sha256': PREVIOUS_R2_LOCAL_RUNNER_SHA,
            'previous_R2_local_pack_failure': PREVIOUS_R2_LOCAL_FAILURE,
            'parent_R3_blocked_report_sha256': E22R3_BLOCKED_SHA,
            'parent_R3_failed_gate': E22R3_EXPECTED_FAILED_GATE,
            'historical_per_time_hash_field': 'saturation_sha256',
            'historical_reference_contract': {
                'scope': 'multi-time',
                'key': EXPECTED_REFERENCE_KEY,
                'shape': list(verified['ref'].shape),
                'times_days': [float(x) for x in verified['times']],
                'plume_threshold': 0.5,
                'source_R14_numerical_relative_path': str(R14_NUMERICAL_REL).replace('\\', '/'),
                'source_R14_numerical_file_sha256': manifest.get('source_file_sha256'),
                'recovery_bundle_sha256': recovery_zip_sha,
                'multi_time_reference_array_sha256': verified['ref_hash'],
                'numerical_truth_regenerated': False,
            },
            'v16_100day_reference_truth': {
                'selection_basis': 'exact recovered historical time-axis equality; no V16 performance',
                'snapshot_index': verified['idx100'],
                'time_days': 100.0,
                'shape': list(ref100.shape),
                'dtype': str(ref100.dtype),
                'snapshot_array_sha256': snap_hash,
                'plume_mask_array_sha256': mask100_hash,
                'plume_threshold': 0.5,
                'morphology': morph,
            },
            'candidate_file': {'path': str(numerical_out), 'sha256': candidate_file_sha, 'frozen': False},
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
        save_json(lineage_json, lineage)

        audit = {
            'milestone': 'V16E-22-R4',
            'status': 'PASS',
            'gates': gates,
            'parent_R3_runner_sha256': E22R3_RUNNER_SHA,
            'parent_R3_blocked_report_sha256': E22R3_BLOCKED_SHA,
            'parent_R3_failed_gate': E22R3_EXPECTED_FAILED_GATE,
            'recovery_bundle_sha256': recovery_zip_sha,
            'historical_R14_numerical_file_sha256': manifest.get('source_file_sha256'),
            'reference_tensor_sha256': verified['ref_hash'],
            'reference_100d_snapshot_sha256': snap_hash,
            'reference_100d_plume_mask_sha256': mask100_hash,
            'reference_candidate_file_sha256': candidate_file_sha,
            'frozen_candidate_sha256': EXPECTED_FROZEN_SHA,
            'historical_numerical_truth_regenerated': False,
            'frozen_candidate_modified': False,
            'reference_candidate_frozen': False,
            'deployment_pass_fail_evaluated': False,
            'full_grid_plume_authorized': False,
        }
        save_json(audit_json, audit)

        summary = {
            'milestone': 'V16E-22-R4',
            'status': 'PASS',
            'grid_shape': list(EXPECTED_GRID),
            'physical_time_days': 100.0,
            'historical_reference_scope': 'MULTI_TIME_100_250_500_1000_DAYS',
            'repair_scope': 'TRACKED_JSON_CANONICAL_IDENTITY_REPAIR_PLUS_LOCAL_IGNORED_R14_NUMERICAL_RECOVERY',
            'historical_reference_key': EXPECTED_REFERENCE_KEY,
            'historical_authoritative_plume_threshold': 0.5,
            'historical_100d_snapshot_index': verified['idx100'],
            'historical_100d_snapshot_sha256': snap_hash,
            'historical_100d_reference_dtype': str(ref100.dtype),
            'historical_100d_plume_cells': morph['plume_cells'],
            'historical_100d_footprint_cells': morph['footprint_cells'],
            'historical_100d_vertical_extent_layers': morph['vertical_extent_layers'],
            'historical_numerical_truth_regenerated': False,
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
        save_json(summary_json, summary)

        handoff_md.write_text(
            '# PAD-Stream V16E-22-R4 Handoff\n\n'
            'V16E-22-R4 repaired the R3 cross-platform tracked-JSON raw-byte identity check by binding Git-blob, normalized-LF, and canonical JSON identities; it retains the earlier per-time hash-field repair (`snapshot_sha256` -> historical `saturation_sha256`) and recovers the Git-ignored historical V15 SG7E1R14 numerical reference artifact '\
            'from the original local workspace only after verifying its complete tensor/time/mask hashes '\
            'against the tracked immutable R14 contract. No historical numerical truth was regenerated.\n\n'
            f'- Historical reference key: `{EXPECTED_REFERENCE_KEY}`\n'
            '- Historical reference times: `100, 250, 500, 1000 days`\n'
            '- Historical plume threshold: `S >= 0.5`\n'
            f'- 100-day snapshot SHA-256: `{snap_hash}`\n'
            f'- Recovery bundle SHA-256: `{recovery_zip_sha}`\n'
            f'- E22-R4 candidate file SHA-256: `{candidate_file_sha}`\n'
            '- Reference candidate is NOT frozen.\n'
            '- No deployment gate was evaluated.\n'
            '- V16 frozen candidate remains unchanged.\n\n'
            'Next: **V16E-23 — Independent Historical 100-Day Reference-Truth Reconstruction Validation / Freeze Readiness**.\n',
            encoding='utf-8'
        )

        print('\n' + '=' * 132)
        print('V16E-22-R4 RESULT: PASS')
        print('=' * 132)
        print(f'Historical reference contract                                    : SG7A_corrected @ [100,250,500,1000] days')
        print(f'Historical authoritative plume threshold                         : S >= {EXPECTED_THRESHOLD}')
        print(f'Historical R14 numerical artifact recovered from Git-ignored local output: YES')
        print(f'Historical numerical truth regenerated                            : NO')
        print(f'V16 100-day reference snapshot index                              : {verified["idx100"]}')
        print(f'100-day reference dtype                                           : {ref100.dtype}')
        print(f'100-day reference min / max / mean                                : {float(np.min(ref100)):.17g} / {float(np.max(ref100)):.17g} / {float(np.mean(ref100)):.17g}')
        print(f'100-day reference plume cells / footprint cells                   : {morph["plume_cells"]} / {morph["footprint_cells"]}')
        print(f'100-day reference vertical extent layers                          : {morph["vertical_extent_layers"]}')
        print(f'100-day snapshot array SHA-256                                    : {snap_hash}')
        print(f'Recovery bundle SHA-256                                           : {recovery_zip_sha}')
        print(f'E22-R4 reference candidate file SHA-256                           : {candidate_file_sha}')
        print('Reference candidate created                                       : YES')
        print('Reference candidate frozen                                        : NO')
        print('V16 candidate performance used for reference selection             : NO')
        print('Deployment pass/fail evaluated                                    : NO')
        print('V16 frozen candidate modified                                     : NO')
        print('Full-grid plume authorized                                         : NO')
        print('Internal test / OOD reopened                                      : NO / NO')
        for p in [lineage_json, audit_json, summary_json, handoff_md, source_csv, hist_output_csv, recovery_csv, time_csv, gate_csv]:
            print(f'{p.name} SHA: {sha256_file(p)}')
        print(f'Output: {out}')
        print('NEXT: V16E-23 - Independent Historical 100-Day Reference-Truth Reconstruction Validation / Freeze Readiness')
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        payload = {
            'milestone': 'V16E-22-R4',
            'status': 'V16E22_R4_HISTORICAL_R14_NUMERICAL_RECOVERY_100DAY_REFERENCE_TRUTH_LINEAGE_RECONSTRUCTION_BLOCKED',
            'exception': repr(exc),
            'gates': gates,
            'historical_numerical_truth_regenerated': False,
            'E21_modified': False,
            'frozen_candidate_modified': False,
            'reference_candidate_frozen': False,
            'deployment_pass_fail_evaluated': False,
            'full_grid_plume_authorized': False,
            'next_milestone': 'V16E-22-R5 - Repair only the failed V16E-22-R4 recovery/provenance gate; preserve E18-R1, E21, E22, E22-R1, and E22-R3 evidence unchanged',
            'traceback': traceback.format_exc(),
        }
        save_json(blocked_json, payload)
        print(f'\n[FAIL] V16E-22-R4 did not close: {exc}')
        print(f'Blocked report SHA: {sha256_file(blocked_json)}')
        print(f'Blocked output: {blocked}')
        return 2


def parse_args():
    p = argparse.ArgumentParser(description='PAD-Stream V16E-22-R4 tracked-JSON canonical identity repair')
    sub = p.add_subparsers(dest='mode', required=True)

    pp = sub.add_parser('pack', help='Verify and package the local Git-ignored historical R14 numerical artifact.')
    pp.add_argument('--project-root', required=True)
    pp.add_argument('--output-zip', required=True)

    pa = sub.add_parser('audit', help='Verify a recovery bundle in a fresh clone and reconstruct the exact 100-day reference candidate.')
    pa.add_argument('--project-root', required=True)
    pa.add_argument('--drive-root', required=True)
    pa.add_argument('--recovery-zip', required=True)
    return p.parse_args()


def main():
    args = parse_args()
    if args.mode == 'pack':
        return pack_mode(Path(args.project_root), Path(args.output_zip))
    return audit_mode(Path(args.project_root), Path(args.drive_root), Path(args.recovery_zip))


if __name__ == '__main__':
    raise SystemExit(main())
