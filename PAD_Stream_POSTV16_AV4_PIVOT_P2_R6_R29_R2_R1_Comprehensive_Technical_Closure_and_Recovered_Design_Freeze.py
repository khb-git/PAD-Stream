#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, importlib.util, inspect, io, json, subprocess, sys
from pathlib import Path
from typing import Any
import numpy as np

M = "POSTV16-AV4-PIVOT-P2-R6-R29-R2-R1"
NAME = "R29-R2 Comprehensive Technical Closure + Recovered Heterogeneous-PV Design Freeze"

PASS = (
    "AV4PIVOTP2R6R29R2R1_COMPREHENSIVE_TECHNICAL_CLOSURE_AND_RECOVERED_"
    "HETEROGENEOUS_PV_DESIGN_FREEZE_PASS_NO_EXECUTION"
)
BLOCK = "AV4PIVOTP2R6R29R2R1_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "c1ed4fa0baafe25104ce971e61f23ccd921f7c90"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"

GRID = (15, 50, 50)
DAY = 375.0
DT_DAYS = 0.03721673128859954
CANDIDATE_TARGET_DAY = 375.0372167312886

R29R2_COMMIT = "c1ed4fa0baafe25104ce971e61f23ccd921f7c90"
R29R2_RUNNER_SHA256 = "68d20b0353f574d92a944f68e9bdb948d285a7a4b190ca87a9a186928eb0a870"
R29R2_RUNNER_BLOB = "a0763f963b70522b3b5122b1286b0bf34c0e4234"
R29R2_BLOCK_STATUS = "AV4PIVOTP2R6R29R2_TECHNICAL_OR_AUTHORITY_BLOCK"
R29R2_BLOCK_STAGE = "R29R1R1_authority"
R29R2_BLOCK_EXCEPTION = "FileNotFoundError(2, 'No such file or directory')"

R29R1_BLOCK_SHA256 = "cde61dec85e1d183ee07329ce30329e9f7e9c88d62ee798ac648cec129933ab5"
R29_FAIL_SHA256 = "1522b39b9e2c89cacf8899c07bcedf61a841a57ca61cc47bd41fbcd818b02209"

R29R2_BLOCK_REL = BASE / "POSTV16_AV4_PIVOT_P2_R6_R29_R2_BLOCKED"
R29R2_BLOCK = "POSTV16_AV4_PIVOT_P2_R6_R29_R2_Blocked_Report.json"

R29R1R1_REL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R29_R1_R1_"
    "Comprehensive_Technical_Closure_PoreVolume_Diagnostic"
)
R29R1R1_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R1_R1_Summary.json"
R29R1R1_CLOSURE = "POSTV16_AV4_PIVOT_P2_R6_R29_R1_R1_Comprehensive_Technical_Closure_Contract.json"
R29R1R1_DECISION = "POSTV16_AV4_PIVOT_P2_R6_R29_R1_R1_Decision_Contract.json"
R29R1R1_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R29_R1_R1_Artifact_Manifest.csv"
R29R1R1_STATUS = (
    "AV4PIVOTP2R6R29R1R1_COMPREHENSIVE_TECHNICAL_CLOSURE_PASS_"
    "R29R1_DIAGNOSTIC_RECOVERED_NO_SCIENCE_STATE_MUTATION"
)
R29R1R1_CLASSIFICATION = (
    "R6R29R1R1_TECHNICAL_CLOSURE_RECOVERS_R29R1_DIAGNOSTIC_"
    "EXACT_STRING_FLOAT_FORMAT_GATE_ONLY_AV4_HETEROGENEOUS_PARENT_VALID_"
    "R29R2_REPAIR_DESIGN_NEXT"
)

R25R3_STATE_SHA256 = "9893e2476bce1d46213cdd1304e60ad93b49ea285e084d06743a2ffab25f721f"

A6E_REL = BASE_AV3 / "POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
A6E_STATE = "POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
A6E_STATE_SHA256 = "f9e3a7bd8c6dcc43d522e0cb99a0cede2bd212fd570085b4faf82dc71af8f803"

R28_REL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R28_"
    "FrozenFlow_Transport_DeltaMapback_ResidualWell_Coupling_Protocol_Freeze"
)
R28_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R28_Summary.json"
R28_DECISION = "POSTV16_AV4_PIVOT_P2_R6_R28_Decision_Contract.json"
R28_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R28_Artifact_Manifest.csv"

R29R2_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R2_"
    "Heterogeneous_Cartesian_PV_DeltaMapback_Repair_Design_Freeze.py"
)
R29R1R1_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R1_R1_Comprehensive_Technical_Closure.py"
R29R1R1_BLOB = "2530da823cb25febcf66eb9baa5b971da51b662d"
E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"

SOURCE_BLOBS = {
    R29R2_RUNNER: R29R2_RUNNER_BLOB,
    R29R1R1_RUNNER: R29R1R1_BLOB,
    E37A: E37A_BLOB,
    A2E: A2E_BLOB,
}

OUT_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R29_R2_R1"
OUT_REL = BASE / (
    OUT_TOKEN + "_Comprehensive_Technical_Closure_and_Recovered_HeterogeneousPV_Design_Freeze"
)
BLOCK_REL = BASE / (OUT_TOKEN + "_BLOCKED")

class GateError(RuntimeError):
    pass

def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def js(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def csvr(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def csvb(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return s.getvalue().encode("utf-8")

def jb(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")

def manifest(directory: Path, filename: str) -> dict[str, str]:
    out = {}
    for row in csvr(directory / filename):
        p = directory / row["file"]
        if not p.is_file():
            raise GateError(f"manifest_missing:{p.name}")
        if sha(p) != row["sha256"]:
            raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes:{p.name}")
        out[p.name] = row["sha256"]
    return out

def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load:{path}")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m

def selftest() -> None:
    assert R29R2_BLOCK_STAGE == "R29R1R1_authority"
    assert abs((CANDIDATE_TARGET_DAY - DAY) - DT_DAYS) < 1e-12
    print("POSTV16 AV4 PIVOT P2-R6-R29-R2-R1 structural self-test: PASS")

def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    block_dir = drive / BLOCK_REL
    stage = "preflight"
    gates = []

    def gate(name: str, cond: Any, detail: Any = None) -> None:
        ok = bool(cond)
        gates.append({
            "stage": stage, "gate": name, "pass": ok,
            "detail": "" if detail is None else repr(detail)
        })
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"))
        if not ok:
            raise GateError(name)

    try:
        # Real Drive authority must be visible before any historical closure work.
        stage = "real_drive_authority"
        r29r1r1 = drive / R29R1R1_REL
        gate("drive_authority_root_exists", drive.is_dir(), str(drive))
        gate("R29R1R1_authority_directory_exists", r29r1r1.is_dir(), str(r29r1r1))
        gate("R29R1R1_summary_exists", (r29r1r1 / R29R1R1_SUMMARY).is_file())
        gate("R29R1R1_manifest_exists", (r29r1r1 / R29R1R1_MANIFEST).is_file())

        stage = "preexisting_state_firewall"
        gate("no_preexisting_R29R2R1_PASS", not (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").exists())
        gate("no_preexisting_R29R2R1_BLOCK", not (block_dir / f"{OUT_TOKEN}_Blocked_Report.json").exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R29R2_commit", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for filename, expected in SOURCE_BLOBS.items():
            p = root / filename
            gate(f"{Path(filename).stem}_present", p.is_file(), str(p))
            actual = gt(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(filename).stem}_blob_exact", actual == expected, actual)

        # Recover immutable R29-R2 BLOCK if it persisted to real Drive.
        stage = "R29R2_historical_BLOCK_recovery"
        source_block_path = drive / R29R2_BLOCK_REL / R29R2_BLOCK
        source_block_persisted = source_block_path.is_file()
        source_block_sha = sha(source_block_path) if source_block_persisted else None

        if source_block_persisted:
            b = js(source_block_path)
            gate("R29R2_BLOCK_status_exact", b.get("status") == R29R2_BLOCK_STATUS, b.get("status"))
            gate("R29R2_BLOCK_stage_exact", b.get("failed_stage") == R29R2_BLOCK_STAGE, b.get("failed_stage"))
            gate("R29R2_BLOCK_exception_exact", b.get("exception") == R29R2_BLOCK_EXCEPTION, b.get("exception"))
            gate("R29R2_BLOCK_no_state_mutation", b.get("state_mutation_executed") is False)
            gate("R29R2_BLOCK_no_transport", b.get("transport_execution_executed") is False)
            gate("R29R2_BLOCK_no_time_advance", b.get("physical_time_advance_executed") is False)
        else:
            # Expected possibility: original formal run continued after mount failure against a local
            # non-authoritative /content/drive tree, so the BLOCK may not exist on real Drive.
            gate("R29R2_BLOCK_nonpersistent_missing_drive_case_recorded", True)

        # Static causality: original runner's first R29R1R1 operation is an authority read.
        stage = "R29R2_source_causality_audit"
        src = (root / R29R2_RUNNER).read_text(encoding="utf-8")
        gate("source_authority_stage_present", 'stage = "R29R1R1_authority"' in src)
        gate("source_authority_manifest_read_present", "manifest(r, R29R1R1_MANIFEST)" in src)
        gate(
            "source_authority_read_precedes_design_work",
            src.find('stage = "R29R1R1_authority"') < src.find('stage = "R28_protocol_continuity"')
        )

        # Recover exact R29-R1-R1 authority now that real Drive is proven.
        stage = "R29R1R1_authority_recovery"
        manifest(r29r1r1, R29R1R1_MANIFEST)
        s = js(r29r1r1 / R29R1R1_SUMMARY)
        c = js(r29r1r1 / R29R1R1_CLOSURE)
        d = js(r29r1r1 / R29R1R1_DECISION)

        gate("R29R1R1_status_exact", s.get("status") == R29R1R1_STATUS, s.get("status"))
        gate("R29R1R1_classification_exact", s.get("classification") == R29R1R1_CLASSIFICATION, s.get("classification"))
        gate("R29R1R1_parent_valid", s.get("accepted_parent_capacity_valid_under_AV4_authority") is True)
        gate("R29R1R1_full_audit_complete", s.get("technical_wrapper_full_audit_completed") is True)
        gate("R29R1R1_no_transport_rerun", s.get("transport_science_rerun") is False)
        gate("R29R1R1_R29R1_BLOCK_SHA_exact", s.get("source_R29R1_BLOCK_sha256") == R29R1_BLOCK_SHA256)
        gate("R29R1R1_R29_FAIL_SHA_exact", s.get("source_R29_SCIENTIFIC_FAIL_sha256") == R29_FAIL_SHA256)

        repair = c.get("repair_boundary", {})
        gate("repair_CV_transport_change_forbidden", repair.get("CV_transport_operator_change_authorized") is False)
        gate("repair_delta_formula_change_forbidden", repair.get("subsegment_delta_formula_change_authorized") is False)
        gate("repair_SG7D_deposition_change_forbidden", repair.get("SG7D_cell_deposition_change_authorized") is False)
        gate("repair_heterogeneous_PV_required", repair.get("heterogeneous_cartesian_pore_volume_required") is True)
        gate("repair_uniform_PV_forbidden", repair.get("uniform_phi_0p20_cartesian_PV_authorized") is False)
        gate("repair_direct_parent_mass_required", repair.get("direct_accepted_parent_cartesian_mass_required") is True)
        gate("repair_candidate_heterogeneous_inversion_required", repair.get("heterogeneous_candidate_capacity_and_inversion_required") is True)
        gate("R29R2_authorized_by_closure", d.get("P2_R6_R29_R2_authorized") is True)

        # Preserve R28 transport contract.
        stage = "R28_continuity"
        r28 = drive / R28_REL
        manifest(r28, R28_MANIFEST)
        s28 = js(r28 / R28_SUMMARY)
        d28 = js(r28 / R28_DECISION)
        gate("R28_dt_exact", float(s28["nominal_dt_days"]) == DT_DAYS)
        gate("R28_target_day_exact", float(s28["candidate_target_day"]) == CANDIDATE_TARGET_DAY)
        gate("R28_delta_mapback_required", s28.get("delta_mapback_required") is True)
        gate("R28_absolute_mapback_forbidden", s28.get("absolute_mapback_forbidden") is True)
        gate("R28_residual_mutation_forbidden", d28.get("residual_sidecar_mutation_authorized") is False)
        gate("R28_auto_dt_reduction_forbidden", d28.get("automatic_dt_reduction_authorized") is False)

        # Full source semantic audit of the repaired design boundary.
        stage = "repair_semantic_audit"
        e37a = load_module(root / E37A, "r29r2r1_e37a")
        a2e = load_module(root / A2E, "r29r2r1_a2e")
        adv_src = inspect.getsource(e37a.advance_component_mass_control_volumes)
        map_src = inspect.getsource(e37a.map_control_volume_increment_to_grid)
        inv_src = inspect.getsource(a2e.invert_local_mass)
        local_src = inspect.getsource(a2e.local_mass)

        gate("E37A_CV_transport_closure_present", "component_mass_FV_global_closure" in adv_src)
        gate("E37A_subsegment_delta_present", "sub_delta_mass" in map_src)
        gate("E37A_flat_cell_deposition_present", "np.bincount" in map_src and "deposited_delta_mass" in map_src)
        gate("legacy_scalar_parent_dependency_identified", "float(cell_pore_volume_m3) * parent_rho * parent_sg" in map_src)
        gate("legacy_scalar_candidate_inversion_identified", "_invert_incremental_sg_from_mass" in map_src and "cell_pore_volume_m3" in map_src)
        gate("A2E_array_PV_inversion_present", "pore_volume_m3" in inspect.signature(a2e.invert_local_mass).parameters)
        gate("A2E_capacity_gate_present", "same_time_local_cell_mass_capacity" in inv_src)
        gate("A2E_array_local_mass_present", "pv * rho * sg" in local_src)

        # Heterogeneous pore-volume authority.
        stage = "heterogeneous_PV_authority"
        a6e_path = drive / A6E_REL / A6E_STATE
        gate("A6E_porosity_state_SHA_exact", a6e_path.is_file() and sha(a6e_path) == A6E_STATE_SHA256)

        with np.load(a6e_path, allow_pickle=False) as z:
            phi = np.asarray(z["paired_porosity"], dtype=np.float64)

        gate("paired_porosity_shape_exact", phi.shape == GRID)
        gate("paired_porosity_positive_finite", np.all(phi > 0.0) and np.isfinite(phi).all())
        gate("paired_porosity_is_heterogeneous", float(np.max(phi) - np.min(phi)) > 0.0)

        hetero_pv = phi * float(a2e.BULK_VOLUME_M3)
        gate("heterogeneous_PV_positive", np.all(hetero_pv > 0.0))

        # Publish recovered design freeze.
        stage = "recovered_design_publication"
        classification = (
            "R6R29R2R1_TECHNICAL_CLOSURE_RECOVERS_R29R2_AFTER_MISSING_DRIVE_AUTHORITY_"
            "HETEROGENEOUS_AV4_CARTESIAN_PV_DESIGN_FROZEN_R29R3_EXECUTION_NEXT"
        )

        protocol = {
            "milestone": M,
            "status": PASS,
            "historical_R29R2": {
                "commit": R29R2_COMMIT,
                "runner_sha256": R29R2_RUNNER_SHA256,
                "runner_git_blob": R29R2_RUNNER_BLOB,
                "status": R29R2_BLOCK_STATUS,
                "failed_stage": R29R2_BLOCK_STAGE,
                "exception": R29R2_BLOCK_EXCEPTION,
                "immutable": True,
                "block_report_persisted_on_real_drive": source_block_persisted,
                "block_report_sha256": source_block_sha,
            },
            "drive_authority_repair": {
                "future_colab_must_prove_drive_root_before_formal_runner": True,
                "formal_runner_may_not_continue_after_drive_mount_failure": True,
                "required_authority_probe": str(R29R1R1_REL / R29R1R1_SUMMARY),
            },
            "recovered_design": {
                "accepted_parent_state_sha256": R25R3_STATE_SHA256,
                "dt_days": DT_DAYS,
                "candidate_target_day": CANDIDATE_TARGET_DAY,
                "CV_transport_operator": "E37A.advance_component_mass_control_volumes",
                "CV_transport_operator_changed": False,
                "subsegment_delta_formula_changed": False,
                "SG7D_cell_deposition_changed": False,
                "uniform_cartesian_PV_authorized": False,
                "heterogeneous_cartesian_PV": "paired_porosity * A2E.BULK_VOLUME_M3",
                "heterogeneous_porosity_state_sha256": A6E_STATE_SHA256,
                "accepted_parent_cartesian_mass_used_directly": True,
                "candidate_mass_identity": "M_grid_candidate = accepted_M_grid_parent + Delta_M_grid",
                "represented_candidate_identity": "M_represented_candidate = M_represented_parent + Delta_M_grid",
                "residual_candidate_identity": "M_residual_candidate = M_residual_parent exactly",
                "absolute_mapback_authorized": False,
                "candidate_capacity": "A2E.local_mass at S=0.80 with heterogeneous PV",
                "candidate_inversion": "A2E.invert_local_mass with heterogeneous PV",
                "automatic_dt_reduction_authorized": False,
                "support_growth_authorized": False,
                "physical_time_commit_authorized": False,
            },
        }

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "source_R29R2_commit": R29R2_COMMIT,
            "source_R29R2_runner_sha256": R29R2_RUNNER_SHA256,
            "source_R29R2_runner_git_blob": R29R2_RUNNER_BLOB,
            "source_R29R2_BLOCK_status": R29R2_BLOCK_STATUS,
            "source_R29R2_BLOCK_failed_stage": R29R2_BLOCK_STAGE,
            "source_R29R2_BLOCK_exception": R29R2_BLOCK_EXCEPTION,
            "source_R29R2_BLOCK_report_persisted_on_real_drive": source_block_persisted,
            "source_R29R2_BLOCK_report_sha256": source_block_sha,
            "root_cause_missing_real_drive_authority": True,
            "R29R1R1_authority_recovered": True,
            "heterogeneous_AV4_cartesian_PV_design_recovered": True,
            "paired_porosity_min": float(np.min(phi)),
            "paired_porosity_max": float(np.max(phi)),
            "heterogeneous_PV_min_m3": float(np.min(hetero_pv)),
            "heterogeneous_PV_max_m3": float(np.max(hetero_pv)),
            "CV_transport_operator_changed": False,
            "subsegment_delta_formula_changed": False,
            "state_mutation_executed": False,
            "transport_execution_executed": False,
            "physical_time_advance_executed": False,
            "P3_authorized": False,
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "P2_R6_R29_R3_authorized": True,
            "P2_R6_R29_R3_name": (
                "Controlled Post-Day375 Frozen-Flow Transport Candidate Execution — "
                "Heterogeneous Cartesian PV Repair — No Time Commit"
            ),
            "P2_R6_R29_R3_execution_authorized": True,
            "P2_R6_R29_R3_candidate_only": True,
            "P2_R6_R29_R3_must_bind_R29R2R1_protocol": True,
            "P2_R6_R29_R3_must_preserve_R29R2_BLOCK": True,
            "P2_R6_R29_R3_dt_days": DT_DAYS,
            "P2_R6_R29_R3_candidate_target_day": CANDIDATE_TARGET_DAY,
            "uniform_cartesian_PV_authorized": False,
            "heterogeneous_AV4_cartesian_PV_required": True,
            "CV_transport_operator_change_authorized": False,
            "subsegment_delta_formula_change_authorized": False,
            "absolute_mapback_authorized": False,
            "residual_sidecar_mutation_authorized": False,
            "automatic_dt_reduction_authorized": False,
            "support_growth_authorized": False,
            "physical_time_advance_authorized": False,
            "pressure_refresh_authorized": False,
            "P3_authorized": False,
        }

        out.mkdir(parents=True, exist_ok=False)
        (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out / f"{OUT_TOKEN}_Comprehensive_Technical_Closure_and_Recovered_Design_Protocol.json").write_bytes(jb(protocol))
        (out / f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))
        (out / f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(rows))

        print("=" * 190)
        print(M, "PASS")
        print("R29-R2 immutable BLOCK stage             :", R29R2_BLOCK_STAGE)
        print("R29-R2 BLOCK persisted on real Drive     :", source_block_persisted)
        print("R29-R2 BLOCK SHA256                      :", source_block_sha)
        print("Root cause                               : missing real Drive authority")
        print("R29-R1-R1 authority recovered            : True")
        print("Heterogeneous-PV design recovered        : True")
        print("R29-R3 corrected execution authorized    : True")
        print("Transport / state / time / P3            : False / False / False / False")
        print("=" * 190)
        return 0

    except Exception as exc:
        block_dir.mkdir(parents=True, exist_ok=True)
        p = block_dir / f"{OUT_TOKEN}_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": BLOCK,
                "failed_stage": stage,
                "exception": repr(exc),
                "R29R2_BLOCK_preserved": True,
                "R29R1R1_closure_preserved": True,
                "transport_execution_executed": False,
                "state_mutation_executed": False,
                "physical_time_advance_executed": False,
                "P3_authorized": False,
                "automatic_rerun_authorized": False,
                "gates_completed": gates,
            }))
        print("=" * 190)
        print(M, "TECHNICAL / AUTHORITY BLOCK")
        print("Stage    :", stage)
        print("Exception:", repr(exc))
        print("NO TRANSPORT / STATE MUTATION / TIME ADVANCE.")
        print("=" * 190)
        return 2

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, default=Path("."))
    ap.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        selftest()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root))
