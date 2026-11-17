#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import types
from pathlib import Path

MILESTONE = "POSTV16-AV4-PIVOT-GPU-HYB-G4-B1-R1"
BRANCH = "postv16-av4-pivot"
PARENT = "4815bd8499266f5e340305abe2950bf1d781dbb4"
B1_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_GPU_HYB_G4_B1_Route_Economics_Instrumentation.py"
B1_GIT_BLOB = "c1d74cc047bc719d6abeb4c81f346d6bfc2ede8d"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_REL = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
B1_TOKEN = "POSTV16_AV4_PIVOT_GPU_HYB_G4_B1"
B1_BLOCK_REL = BASE_REL / (B1_TOKEN + "_BLOCKED")
B1_BLOCK_REPORT = f"{B1_TOKEN}_Blocked_Report.json"
B1_BLOCK_STATUS = "POSTV16AV4PIVOTGPUHYBG4B1_TECHNICAL_OR_AUTHORITY_BLOCK"

R1_TOKEN = "POSTV16_AV4_PIVOT_GPU_HYB_G4_B1_R1"
R1_STATUS = "POSTV16AV4PIVOTGPUHYBG4B1R1_ALIGNED_MAPBACK_PARENT_STATE_RECONCILIATION_REPAIR_PASS"
R1_BLOCK = "POSTV16AV4PIVOTGPUHYBG4B1R1_TECHNICAL_OR_AUTHORITY_BLOCK"
R1_CLASSIFICATION = (
    "G4_B1_ALIGNED_MAPBACK_PARENT_STATE_RECONCILIATION_REPAIRED_"
    "CURRENT_HYBRID_FULL_EXACT_PRECEDES_OVERWRITE_"
    "FALLBACK_SUBSET_E37A_EQUIVALENCE_CERTIFIED_"
    "B2_TRUE_ACCELERATION_REDESIGN_AUTHORIZED"
)

class RepairError(RuntimeError):
    pass

def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def replace_once(source: str, old: str, new: str, label: str) -> str:
    n = source.count(old)
    if n != 1:
        raise RepairError(f"patch_anchor_{label}_count:{n}")
    return source.replace(old, new, 1)

def patched_b1_source(source: str) -> str:
    s = source
    replacements = [
        ('M="POSTV16-AV4-PIVOT-GPU-HYB-G4-B1"', 'M="POSTV16-AV4-PIVOT-GPU-HYB-G4-B1-R1"', 'milestone'),
        ('PASS="POSTV16AV4PIVOTGPUHYBG4B1_ROUTE_ECONOMICS_INSTRUMENTATION_PASS"', f'PASS="{R1_STATUS}"', 'pass_status'),
        ('BLOCK="POSTV16AV4PIVOTGPUHYBG4B1_TECHNICAL_OR_AUTHORITY_BLOCK"', f'BLOCK="{R1_BLOCK}"', 'block_status'),
        ('PARENT="2796b1bf5a20b44b020b8bd185bc9de400dcb35e"', f'PARENT="{PARENT}"', 'parent'),
        ('OUT_TOKEN="POSTV16_AV4_PIVOT_GPU_HYB_G4_B1"', f'OUT_TOKEN="{R1_TOKEN}"', 'output_token'),
        ('print("POSTV16 GPU-HYB-G4-B1 structural self-test: PASS")', 'print("POSTV16 GPU-HYB-G4-B1-R1 structural self-test: PASS")', 'selftest_label'),
        ('gate("parent_is_VIS_A2",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))', 'gate("parent_is_G4_B1_block_commit",gt(root,"rev-parse","HEAD^")==PARENT,gt(root,"rev-parse","HEAD^"))', 'parent_gate'),
        ('        parent_stored=scalar(state["stored_co2_mass_current_kg"])', '        parent_stored=scalar(refreshed["stored_co2_mass_current_kg"])', 'mapback_parent_ledger'),
    ]
    for old,new,label in replacements:
        s = replace_once(s, old, new, label)

    old_banner = (
        'print("G4-B1 — ROUTE ECONOMICS INSTRUMENTATION / DAY100 REPRESENTATIVE TRANSPORT-KERNEL AUDIT")\n'
        '        print("READ-ONLY SCIENTIFIC PROBE. NO CANONICAL STATE MUTATION. NO ROUTING POLICY CHANGE.")'
    )
    new_banner = (
        'print("G4-B1-R1 — ALIGNED MAPBACK PARENT-STATE RECONCILIATION REPAIR / ROUTE ECONOMICS INSTRUMENTATION")\n'
        '        print("REPAIR OF G4-B1 MAPBACK INSTRUMENTATION ONLY. READ-ONLY. NO PHYSICS, STATE, SCREEN, OR ROUTING-POLICY MUTATION.")'
    )
    s = replace_once(s, old_banner, new_banner, 'banner')

    artifact_anchor = '        stage="artifact_authority"\n        vis2d=drive/VIS2_REL'
    artifact_insert = '''        stage="artifact_authority"
        b1_block_path=drive/Path("post_v16")/RID/"POSTV16_AV4_Dynamic_Flow_Coupling"/("POSTV16_AV4_PIVOT_GPU_HYB_G4_B1"+"_BLOCKED")/"POSTV16_AV4_PIVOT_GPU_HYB_G4_B1_Blocked_Report.json"
        gate("B1_block_report_present",b1_block_path.is_file(),str(b1_block_path))
        b1_block=js(b1_block_path)
        gate("B1_block_status_exact",b1_block.get("status")=="POSTV16AV4PIVOTGPUHYBG4B1_TECHNICAL_OR_AUTHORITY_BLOCK",b1_block.get("status"))
        gate("B1_block_failed_stage_mapback_timing",b1_block.get("failed_stage")=="mapback_timing",b1_block.get("failed_stage"))
        gate("B1_block_exception_is_aligned_mapback_ledger",
             "aligned_mapback_component_ledger_residual" in str(b1_block.get("exception","")),
             b1_block.get("exception"))

        vis2d=drive/VIS2_REL'''
    s = replace_once(s, artifact_anchor, artifact_insert, 'B1_block_authority')

    flow_anchor = '''        gate("flow_rebuild_mass_preserved",
             abs(scalar(refreshed["stored_co2_mass_current_kg"])-scalar(state["stored_co2_mass_current_kg"]))<=
             max(1e-6,1e-10*abs(scalar(state["stored_co2_mass_current_kg"]))))

        vx,vy,vz=sg5.construct_face_pore_velocities(epoch["qx"],epoch["qy"],epoch["qz"])'''
    flow_insert = '''        gate("flow_rebuild_mass_preserved",
             abs(scalar(refreshed["stored_co2_mass_current_kg"])-scalar(state["stored_co2_mass_current_kg"]))<=
             max(1e-6,1e-10*abs(scalar(state["stored_co2_mass_current_kg"]))))

        # G4-B1-R1 repair: use the same-time mass-conservative reconciled
        # saturation-pressure parent pair for CV sampling and aligned mapback.
        parent_sat=np.asarray(refreshed["transport_saturation"],float)
        reconciled_pressure=np.asarray(epoch["pressure_psi"],float)
        refreshed_stored=scalar(refreshed["stored_co2_mass_current_kg"])
        refreshed_parent_mass=float(physics.stored_co2_mass_kg(
            parent_sat,reconciled_pressure,p_ref,cell_pv))
        refreshed_parent_mass_residual=refreshed_parent_mass-refreshed_stored
        refreshed_parent_mass_tol=max(1e-6,1e-10*max(abs(refreshed_stored),1.0))
        gate("reconciled_parent_state_matches_preserved_mass_ledger",
             abs(refreshed_parent_mass_residual)<=refreshed_parent_mass_tol,
             refreshed_parent_mass_residual)

        vx,vy,vz=sg5.construct_face_pore_velocities(epoch["qx"],epoch["qy"],epoch["qz"])'''
    s = replace_once(s, flow_anchor, flow_insert, 'reconciled_parent_state')

    summary_anchor = '            "classification":"CURRENT_HYBRID_EXECUTES_FULL_EXACT_TRANSPORT_BEFORE_OVERWRITE_FALLBACK_SUBSET_E37A_EQUIVALENCE_CERTIFIED_B2_TRUE_ACCELERATION_REDESIGN_AUTHORIZED",'
    summary_insert = (
        f'            "classification":"{R1_CLASSIFICATION}",\n'
        '            "B1_blocked_predecessor_bound":True,\n'
        '            "B1_original_failed_stage":b1_block.get("failed_stage"),\n'
        '            "B1_original_exception":b1_block.get("exception"),\n'
        '            "B1_R1_reconciled_parent_state_used_for_CV_sampling_and_mapback":True,\n'
        '            "reconciled_parent_mass_ledger_residual_kg":float(refreshed_parent_mass_residual),'
    )
    s = replace_once(s, summary_anchor, summary_insert, 'summary_classification')
    return s

def repository_preflight(root: Path) -> None:
    branch = git(root, "branch", "--show-current")
    head = git(root, "rev-parse", "HEAD")
    parent = git(root, "rev-parse", "HEAD^")
    clean = git(root, "status", "--porcelain") == ""
    b1 = root / B1_RUNNER
    b1_blob = git(root, "hash-object", str(b1)) if b1.is_file() else "MISSING"
    print("--- G4-B1-R1 REPOSITORY IDENTITY ---")
    print("Branch:", branch)
    print("HEAD  :", head)
    print("HEAD^ :", parent)
    print("Clean :", clean)
    print("B1 runner blob:", b1_blob)
    print("Expected      :", B1_GIT_BLOB)
    if branch != BRANCH: raise RepairError(f"branch:{branch}:{BRANCH}")
    if parent != PARENT: raise RepairError(f"parent:{parent}:{PARENT}")
    if not clean: raise RepairError("repository_not_clean")
    if b1_blob != B1_GIT_BLOB: raise RepairError(f"B1_blob:{b1_blob}:{B1_GIT_BLOB}")

def load_patched_module(root: Path) -> types.ModuleType:
    b1 = root / B1_RUNNER
    source = b1.read_text(encoding="utf-8")
    patched = patched_b1_source(source)
    compile(patched, f"<{R1_TOKEN}_patched_B1>", "exec")
    module = types.ModuleType("g4_b1_r1_patched_b1")
    module.__file__ = str(b1)
    module.__package__ = None
    sys.modules[module.__name__] = module
    exec(compile(patched, module.__file__, "exec"), module.__dict__)
    return module

def self_test(root: Path) -> None:
    repository_preflight(root)
    module = load_patched_module(root)
    required = ["main", "selftest", "OUT_TOKEN", "PASS", "BLOCK"]
    missing = [x for x in required if not hasattr(module, x)]
    if missing: raise RepairError(f"patched_module_missing:{missing}")
    if module.OUT_TOKEN != R1_TOKEN: raise RepairError(f"patched_OUT_TOKEN:{module.OUT_TOKEN}")
    if module.PASS != R1_STATUS: raise RepairError(f"patched_PASS:{module.PASS}")
    print("POSTV16 GPU-HYB-G4-B1-R1 structural/patch self-test: PASS")

def main(root: Path, drive: Path) -> int:
    root = root.resolve(); drive = drive.resolve()
    repository_preflight(root)
    block_path = drive / B1_BLOCK_REL / B1_BLOCK_REPORT
    if not block_path.is_file(): raise RepairError(f"missing_B1_BLOCK_report:{block_path}")
    block = json.loads(block_path.read_text(encoding="utf-8"))
    if block.get("status") != B1_BLOCK_STATUS: raise RepairError(f"B1_BLOCK_status:{block.get('status')}")
    if block.get("failed_stage") != "mapback_timing": raise RepairError(f"B1_BLOCK_stage:{block.get('failed_stage')}")
    if "aligned_mapback_component_ledger_residual" not in str(block.get("exception", "")):
        raise RepairError(f"B1_BLOCK_exception:{block.get('exception')}")
    module = load_patched_module(root)
    return int(module.main(root, drive))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, default=Path("."))
    ap.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    try:
        if args.self_test:
            self_test(args.project_root.resolve())
            raise SystemExit(0)
        raise SystemExit(main(args.project_root, args.drive_root))
    except Exception as exc:
        print(MILESTONE, "WRAPPER BLOCK")
        print("Exception:", repr(exc))
        raise
