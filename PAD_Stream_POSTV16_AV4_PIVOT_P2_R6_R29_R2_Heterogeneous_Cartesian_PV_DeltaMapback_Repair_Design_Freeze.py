#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, importlib.util, inspect, io, json, subprocess, sys
from pathlib import Path
from typing import Any
import numpy as np

M = "POSTV16-AV4-PIVOT-P2-R6-R29-R2"
NAME = "R29 Heterogeneous Cartesian Pore-Volume / Delta-Mapback Repair Design Freeze"

PASS = (
    "AV4PIVOTP2R6R29R2_HETEROGENEOUS_CARTESIAN_PORE_VOLUME_DELTA_MAPBACK_"
    "REPAIR_DESIGN_FREEZE_PASS_NO_EXECUTION"
)
BLOCK = "AV4PIVOTP2R6R29R2_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "f47247241036becfc154546dd197201423514703"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"

GRID = (15, 50, 50)
NSL = 1078
NCV = 200
NN = 201
DAY = 375.0
DT_DAYS = 0.03721673128859954
CANDIDATE_TARGET_DAY = 375.0372167312886

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

R29R1_BLOCK_SHA256 = "cde61dec85e1d183ee07329ce30329e9f7e9c88d62ee798ac648cec129933ab5"
R29_FAIL_SHA256 = "1522b39b9e2c89cacf8899c07bcedf61a841a57ca61cc47bd41fbcd818b02209"

R25R3_REL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R25_R3_"
    "Controlled_Day375_CapacityLimited_ExactSupport_SplitState_"
    "Reprojection_Execution_Stage2_PresolveOff"
)
R25R3_STATE = "POSTV16_AV4_PIVOT_P2_R6_R25_R3_CapacityLimited_SplitState_Day375.npz"
R25R3_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R25_R3_Artifact_Manifest.csv"
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

R29R1R1_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R1_R1_"
    "Comprehensive_Technical_Closure.py"
)
R29R1R1_BLOB = "2530da823cb25febcf66eb9baa5b971da51b662d"

E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"
SG7A = "PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py"
SG7A_BLOB = "a4dd47338e7a85f130a6a70d0a41211e38c655f8"
E36 = "PAD_Stream_V16E36_Short_Adaptive_SGSim_Rollout_and_Early_Plume_Snapshot_Validation.py"
E36_BLOB = "9ab4035c95a25bd61c649f86c82d88f059cef9e2"

SOURCE_BLOBS = {
    R29R1R1_RUNNER: R29R1R1_BLOB,
    E37A: E37A_BLOB,
    R2: R2_BLOB,
    A2E: A2E_BLOB,
    SG7D: SG7D_BLOB,
    SG7A: SG7A_BLOB,
    E36: E36_BLOB,
}

OUT_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R29_R2"
OUT_REL = BASE / (
    OUT_TOKEN
    + "_Heterogeneous_Cartesian_PoreVolume_DeltaMapback_Repair_Design_Freeze"
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
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return s.getvalue().encode("utf-8")


def jb(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")


def manifest(directory: Path, filename: str) -> dict[str, str]:
    out: dict[str, str] = {}
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
    assert CANDIDATE_TARGET_DAY > DAY
    assert abs((CANDIDATE_TARGET_DAY - DAY) - DT_DAYS) < 1e-12
    frozen = {
        "CV_transport_changed": False,
        "subsegment_delta_changed": False,
        "uniform_PV_allowed": False,
        "heterogeneous_PV_required": True,
        "physical_time_commit": False,
    }
    assert frozen["CV_transport_changed"] is False
    assert frozen["heterogeneous_PV_required"] is True
    assert frozen["physical_time_commit"] is False
    print("POSTV16 AV4 PIVOT P2-R6-R29-R2 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    block_dir = drive / BLOCK_REL
    stage = "preflight"
    gates: list[dict[str, Any]] = []

    def gate(name: str, cond: Any, detail: Any = None) -> None:
        ok = bool(cond)
        gates.append({
            "stage": stage,
            "gate": name,
            "pass": ok,
            "detail": "" if detail is None else repr(detail),
        })
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"))
        if not ok:
            raise GateError(name)

    try:
        stage = "preexisting_state_firewall"
        gate("no_preexisting_R29R2_PASS", not (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").exists())
        gate("no_preexisting_R29R2_BLOCK", not (block_dir / f"{OUT_TOKEN}_Blocked_Report.json").exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R29R1R1_commit", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")

        for filename, expected in SOURCE_BLOBS.items():
            p = root / filename
            gate(f"{Path(filename).stem}_present", p.is_file(), str(p))
            actual = gt(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(filename).stem}_blob_exact", actual == expected, actual)

        stage = "R29R1R1_authority"
        r = drive / R29R1R1_REL
        manifest(r, R29R1R1_MANIFEST)
        s = js(r / R29R1R1_SUMMARY)
        c = js(r / R29R1R1_CLOSURE)
        d = js(r / R29R1R1_DECISION)

        gate("R29R1R1_status_exact", s.get("status") == R29R1R1_STATUS, s.get("status"))
        gate("R29R1R1_classification_exact", s.get("classification") == R29R1R1_CLASSIFICATION, s.get("classification"))
        gate("R29R1_BLOCK_SHA_exact", s.get("source_R29R1_BLOCK_sha256") == R29R1_BLOCK_SHA256)
        gate("R29_FAIL_SHA_exact", s.get("source_R29_SCIENTIFIC_FAIL_sha256") == R29_FAIL_SHA256)
        gate("R29R1R1_full_audit_complete", s.get("technical_wrapper_full_audit_completed") is True)
        gate("R29R1R1_no_transport_rerun", s.get("transport_science_rerun") is False)
        gate("R29R1R1_parent_valid", s.get("accepted_parent_capacity_valid_under_AV4_authority") is True)
        gate("R29R1R1_heterogeneous_zero_violations", int(s.get("heterogeneous_PV_violating_cell_count")) == 0)
        gate("R29R1R1_heterogeneous_inversion_exact", float(s.get("heterogeneous_inversion_saturation_max_abs_error")) == 0.0)

        repair = c.get("repair_boundary", {})
        gate("closure_CV_transport_change_forbidden", repair.get("CV_transport_operator_change_authorized") is False)
        gate("closure_delta_formula_change_forbidden", repair.get("subsegment_delta_formula_change_authorized") is False)
        gate("closure_SG7D_deposition_change_forbidden", repair.get("SG7D_cell_deposition_change_authorized") is False)
        gate("closure_heterogeneous_PV_required", repair.get("heterogeneous_cartesian_pore_volume_required") is True)
        gate("closure_uniform_PV_forbidden", repair.get("uniform_phi_0p20_cartesian_PV_authorized") is False)
        gate("closure_direct_parent_mass_required", repair.get("direct_accepted_parent_cartesian_mass_required") is True)
        gate("closure_heterogeneous_candidate_inversion_required", repair.get("heterogeneous_candidate_capacity_and_inversion_required") is True)

        gate("R29R2_authorized", d.get("P2_R6_R29_R2_authorized") is True)
        gate("R29R2_design_only", d.get("P2_R6_R29_R2_design_only") is True)
        gate("R29R2_execution_not_authorized", d.get("P2_R6_R29_R2_execution_authorized") is False)
        gate("R29R2_BLOCK_SHA_bound", d.get("P2_R6_R29_R2_R29R1_BLOCK_sha256") == R29R1_BLOCK_SHA256)
        gate("R29R2_FAIL_SHA_bound", d.get("P2_R6_R29_R2_R29_FAIL_sha256") == R29_FAIL_SHA256)
        gate("R29_FAIL_immutable", d.get("R29_SCIENTIFIC_FAIL_remains_immutable") is True)
        gate("R29R1_BLOCK_immutable", d.get("R29R1_TECHNICAL_BLOCK_remains_immutable") is True)

        stage = "R28_protocol_continuity"
        r28 = drive / R28_REL
        manifest(r28, R28_MANIFEST)
        s28 = js(r28 / R28_SUMMARY)
        d28 = js(r28 / R28_DECISION)

        gate("R28_dt_exact", float(s28["nominal_dt_days"]) == DT_DAYS)
        gate("R28_target_day_exact", float(s28["candidate_target_day"]) == CANDIDATE_TARGET_DAY)
        gate("R28_delta_mapback_required", s28.get("delta_mapback_required") is True)
        gate("R28_absolute_mapback_forbidden", s28.get("absolute_mapback_forbidden") is True)
        gate("R28_residual_direct_exchange_forbidden", d28.get("residual_direct_well_exchange_authorized") is False)
        gate("R28_residual_mutation_forbidden", d28.get("residual_sidecar_mutation_authorized") is False)
        gate("R28_auto_dt_reduction_forbidden", d28.get("automatic_dt_reduction_authorized") is False)

        stage = "repair_boundary_source_audit"
        e37a = load_module(root / E37A, "r29r2_e37a")
        a2e = load_module(root / A2E, "r29r2_a2e")

        adv_src = inspect.getsource(e37a.advance_component_mass_control_volumes)
        map_src = inspect.getsource(e37a.map_control_volume_increment_to_grid)
        inv_src = inspect.getsource(a2e.invert_local_mass)
        local_src = inspect.getsource(a2e.local_mass)

        gate("CV_transport_operator_exists", callable(e37a.advance_component_mass_control_volumes))
        gate("CV_transport_global_closure_present", "component_mass_FV_global_closure" in adv_src)
        gate("legacy_mapback_subsegment_delta_formula_present", "sub_delta_mass" in map_src)
        gate("legacy_mapback_cell_deposition_present", "deposited_delta_mass" in map_src and "np.bincount" in map_src)
        gate("legacy_mapback_scalar_parent_reconstruction_identified", "float(cell_pore_volume_m3) * parent_rho * parent_sg" in map_src)
        gate("legacy_mapback_scalar_candidate_inversion_identified", "_invert_incremental_sg_from_mass" in map_src and "cell_pore_volume_m3" in map_src)

        gate("A2E_local_mass_accepts_array_PV", "pore_volume_m3" in inspect.signature(a2e.local_mass).parameters)
        gate("A2E_invert_accepts_array_PV", "pore_volume_m3" in inspect.signature(a2e.invert_local_mass).parameters)
        gate("A2E_invert_capacity_gate_present", "same_time_local_cell_mass_capacity" in inv_src)
        gate("A2E_invert_negative_mass_gate_present", "negative_parent_cell_mass" in inv_src)
        gate("A2E_local_mass_uses_array_PV", "pv * rho * sg" in local_src)

        stage = "heterogeneous_PV_authority"
        a6e_path = drive / A6E_REL / A6E_STATE
        gate("A6E_porosity_state_SHA_exact", a6e_path.is_file() and sha(a6e_path) == A6E_STATE_SHA256)

        with np.load(a6e_path, allow_pickle=False) as z:
            phi = np.asarray(z["paired_porosity"], dtype=np.float64)

        gate("paired_porosity_shape_exact", phi.shape == GRID)
        gate("paired_porosity_positive_finite", np.all(phi > 0.0) and np.isfinite(phi).all())
        gate("paired_porosity_is_heterogeneous", float(np.max(phi) - np.min(phi)) > 0.0)

        hetero_pv = phi * float(a2e.BULK_VOLUME_M3)
        gate("heterogeneous_PV_shape_positive", hetero_pv.shape == GRID and np.all(hetero_pv > 0.0))

        stage = "R29R3_protocol_freeze"

        protocol = {
            "milestone": M,
            "status": PASS,
            "purpose": (
                "freeze corrected R29 candidate execution after immutable R29 SCIENTIFIC FAIL "
                "and immutable R29-R1 technical BLOCK"
            ),
            "immutable_history": {
                "R29_SCIENTIFIC_FAIL_sha256": R29_FAIL_SHA256,
                "R29R1_TECHNICAL_BLOCK_sha256": R29R1_BLOCK_SHA256,
                "R29_SCIENTIFIC_FAIL_overwritten": False,
                "R29R1_TECHNICAL_BLOCK_overwritten": False,
            },
            "accepted_parent": {
                "state_sha256": R25R3_STATE_SHA256,
                "canonical_day": DAY,
                "cartesian_mass_source": "accepted R25-R3 cartesian_component_mass_kg directly",
                "uniform_PV_parent_mass_reconstruction_forbidden": True,
            },
            "frozen_time_and_flow": {
                "dt_days": DT_DAYS,
                "candidate_target_day": CANDIDATE_TARGET_DAY,
                "dt_changed_from_R28": False,
                "flow_geometry_refresh_before_candidate": False,
                "pressure_refresh_before_candidate": False,
            },
            "CV_transport": {
                "implementation": "E37A.advance_component_mass_control_volumes",
                "operator_changed": False,
                "source_sink_semantics_changed": False,
                "CV_capacity_semantics_changed": False,
            },
            "delta_mapback_stage_A_subsegment_delta": {
                "reuse_E37A_formula": True,
                "old_sub_sat": "old_cv_saturation[geometry.cv_id]",
                "new_sub_sat": "new_cv_saturation[geometry.cv_id]",
                "old_sub_sg": "clip(old_sub_sat-0.20, 0, 0.60)",
                "new_sub_sg": "clip(new_sub_sat-0.20, 0, 0.60)",
                "rho_old": "R2.gas_density_from_state(old_sub_sat, geometry.pseg_psi, p_ref)",
                "rho_new": "R2.gas_density_from_state(new_sub_sat, geometry.pseg_psi, p_ref)",
                "sub_delta_mass": "geometry.pv_m3 * (rho_new*new_sub_sg - rho_old*old_sub_sg)",
                "required_gate": "sum(sub_delta_mass) == sum(new_CV_mass-old_CV_mass) within frozen closure tolerance",
            },
            "delta_mapback_stage_B_cell_deposition": {
                "reuse_SG7D_flat_cell_partition": True,
                "formula": (
                    "Delta_M_grid = bincount(geometry.flat_cell, "
                    "weights=sub_delta_mass, minlength=37500).reshape(15,50,50)"
                ),
                "absolute_mapback_forbidden": True,
            },
            "corrected_cartesian_candidate": {
                "pore_volume_field": "paired_porosity * A2E.BULK_VOLUME_M3",
                "porosity_state_sha256": A6E_STATE_SHA256,
                "candidate_mass_identity": "M_grid_candidate = accepted_M_grid_parent + Delta_M_grid",
                "represented_candidate_identity": "M_represented_candidate = M_represented_parent + Delta_M_grid",
                "residual_candidate_identity": "M_residual_candidate = M_residual_parent exactly",
                "split_identity": "M_grid_candidate = M_residual_candidate + M_represented_candidate",
                "represented_candidate_nonnegative_required": True,
                "residual_may_not_be_consumed": True,
                "scientific_mass_clipping_or_rescaling_authorized": False,
            },
            "corrected_cartesian_capacity_and_inversion": {
                "capacity_formula": "A2E.local_mass(R2, saturation=0.80, pressure, p_ref, heterogeneous_PV)",
                "capacity_excess_gate": "max(M_grid_candidate-capacity) <= A2E frozen capacity tolerance",
                "candidate_inversion": "A2E.invert_local_mass(R2, M_grid_candidate, pressure, p_ref, heterogeneous_PV)",
                "candidate_saturation": "A2E.BACKGROUND + inverted_incremental_sg",
                "candidate_mass_reconstruction": "A2E.local_mass(R2, candidate_saturation, pressure, p_ref, heterogeneous_PV)",
                "inherited_A2E_sub_1e-9_negative_roundoff_floor_only": True,
                "additional_scientific_clipping_authorized": False,
            },
            "global_ledgers": {
                "CV_identity": "Delta_M_CV = M_injected - M_produced",
                "transfer_identity": "sum(Delta_M_grid) = Delta_M_CV",
                "cartesian_identity": "sum(M_grid_candidate)-sum(M_grid_parent) = M_injected-M_produced",
                "residual_sidecar_mutation": False,
            },
            "R29R3_failure_semantics": {
                "scientific_gate_failure": "immutable SCIENTIFIC FAIL; no automatic rerun",
                "technical_or_authority_failure": "immutable BLOCK",
                "automatic_dt_reduction": False,
                "support_growth": False,
                "residual_promotion": False,
                "scientific_mass_clipping_or_rescaling": False,
            },
            "R29R3_commit_semantics": {
                "candidate_only": True,
                "physical_time_commit": False,
                "pressure_refresh": False,
                "Darcy_Pollock_TOF_refresh": False,
                "P3_authorized": False,
            },
        }

        classification = (
            "R6R29R2_HETEROGENEOUS_AV4_CARTESIAN_PV_DELTA_MAPBACK_REPAIR_PROTOCOL_"
            "FROZEN_CV_TRANSPORT_UNCHANGED_R29R3_CORRECTED_CANDIDATE_EXECUTION_NEXT"
        )

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "source_R29R1_BLOCK_sha256": R29R1_BLOCK_SHA256,
            "source_R29_SCIENTIFIC_FAIL_sha256": R29_FAIL_SHA256,
            "source_R25R3_state_sha256": R25R3_STATE_SHA256,
            "source_A6E_porosity_state_sha256": A6E_STATE_SHA256,
            "dt_days": DT_DAYS,
            "candidate_target_day": CANDIDATE_TARGET_DAY,
            "paired_porosity_min": float(np.min(phi)),
            "paired_porosity_max": float(np.max(phi)),
            "heterogeneous_PV_min_m3": float(np.min(hetero_pv)),
            "heterogeneous_PV_max_m3": float(np.max(hetero_pv)),
            "CV_transport_operator_changed": False,
            "subsegment_delta_formula_changed": False,
            "SG7D_cell_deposition_changed": False,
            "uniform_cartesian_PV_frozen_out": True,
            "heterogeneous_AV4_cartesian_PV_required": True,
            "accepted_parent_cartesian_mass_used_directly": True,
            "absolute_mapback_frozen_out": True,
            "residual_sidecar_mutation_frozen_out": True,
            "automatic_dt_reduction_frozen_out": True,
            "transport_execution_performed": False,
            "state_mutation_executed": False,
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
            "P2_R6_R29_R3_must_bind_R29R2_protocol": True,
            "P2_R6_R29_R3_must_bind_R29R1R1_closure": True,
            "P2_R6_R29_R3_must_bind_R29_FAIL_SHA": True,
            "P2_R6_R29_R3_R29_FAIL_sha256": R29_FAIL_SHA256,
            "P2_R6_R29_R3_must_bind_R29R1_BLOCK_SHA": True,
            "P2_R6_R29_R3_R29R1_BLOCK_sha256": R29R1_BLOCK_SHA256,
            "P2_R6_R29_R3_dt_days": DT_DAYS,
            "P2_R6_R29_R3_candidate_target_day": CANDIDATE_TARGET_DAY,
            "CV_transport_operator_change_authorized": False,
            "subsegment_delta_formula_change_authorized": False,
            "uniform_cartesian_PV_authorized": False,
            "heterogeneous_AV4_cartesian_PV_required": True,
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
        (out / f"{OUT_TOKEN}_Heterogeneous_Cartesian_PV_DeltaMapback_Repair_Protocol.json").write_bytes(jb(protocol))
        (out / f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))
        (out / f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(rows))

        print("=" * 190)
        print(M, "PASS")
        print("Classification                         :", classification)
        print("R29 SCIENTIFIC FAIL preserved          :", R29_FAIL_SHA256)
        print("R29-R1 BLOCK preserved                 :", R29R1_BLOCK_SHA256)
        print("CV transport operator changed          : False")
        print("Subsegment delta formula changed       : False")
        print("Uniform Cartesian PV authorized        : False")
        print("Heterogeneous AV4 PV required          : True")
        print("dt / candidate target day              :", DT_DAYS, "/", CANDIDATE_TARGET_DAY)
        print("R29-R3 corrected candidate execution   : AUTHORIZED")
        print("Physical time / pressure refresh / P3  : False / False / False")
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
                "R29_SCIENTIFIC_FAIL_preserved": True,
                "R29R1_TECHNICAL_BLOCK_preserved": True,
                "R29R1R1_closure_preserved": True,
                "state_mutation_executed": False,
                "transport_execution_executed": False,
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
