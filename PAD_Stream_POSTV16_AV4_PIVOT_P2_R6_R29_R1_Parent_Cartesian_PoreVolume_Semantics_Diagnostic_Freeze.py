#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, importlib.util, inspect, io, json, subprocess, sys
from pathlib import Path
from typing import Any
import numpy as np

M = "POSTV16-AV4-PIVOT-P2-R6-R29-R1"
NAME = "R29 Parent Cartesian Pore-Volume Semantics Diagnostic Freeze"

PASS = (
    "AV4PIVOTP2R6R29R1_PARENT_CARTESIAN_PORE_VOLUME_SEMANTICS_DIAGNOSTIC_"
    "PASS_HETEROGENEOUS_AV4_PARENT_VALID_NO_STATE_MUTATION"
)
BLOCK = "AV4PIVOTP2R6R29R1_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "6e142188c69d16dadce56492245c746076db55b5"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"

GRID = (15, 50, 50)
BACKGROUND = 0.20
INJECTED = 0.80
MAX_SG = 0.60
UNIFORM_PHI = 0.20
MASS_TOL = 1e-8

# --------------------------------------------------------------------------------------------------
# Immutable R29 SCIENTIFIC FAIL.
# --------------------------------------------------------------------------------------------------

R29_FAIL_REL = BASE / "POSTV16_AV4_PIVOT_P2_R6_R29_SCIENTIFIC_FAIL"
R29_FAIL = "POSTV16_AV4_PIVOT_P2_R6_R29_Scientific_Fail_Report.json"
R29_FAIL_STATUS = (
    "AV4PIVOTP2R6R29_CONTROLLED_POSTDAY375_FROZEN_FLOW_CAPACITY_LIMITED_"
    "SPLIT_STATE_TRANSPORT_CANDIDATE_SCIENTIFIC_FAIL_NO_AUTOMATIC_RERUN"
)
R29_FAIL_STAGE = "parent_cartesian_mass_inversion"
R29_FAIL_GATE = "parent_cartesian_mass_inversion"
R29_FAIL_DETAIL = "GateError('capillary_cell_mass_capacity_exceeded:1750.620691678921')"

# --------------------------------------------------------------------------------------------------
# Accepted parent state / pressure epoch.
# --------------------------------------------------------------------------------------------------

R25R3_REL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R25_R3_"
    "Controlled_Day375_CapacityLimited_ExactSupport_SplitState_"
    "Reprojection_Execution_Stage2_PresolveOff"
)
R25R3_STATE = "POSTV16_AV4_PIVOT_P2_R6_R25_R3_CapacityLimited_SplitState_Day375.npz"
R25R3_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R25_R3_Artifact_Manifest.csv"
R25R3_STATE_SHA256 = "9893e2476bce1d46213cdd1304e60ad93b49ea285e084d06743a2ffab25f721f"

CLOSURE_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_R1_R1_R1"
CLOSURE_REL = BASE / (
    CLOSURE_TOKEN
    + "_Comprehensive_Technical_Closure_and_Pressure_Refresh_Acceptance"
)
CLOSURE_SUMMARY = f"PAD_Stream_{CLOSURE_TOKEN}_Summary.json"
CLOSURE_MANIFEST = f"{CLOSURE_TOKEN}_Artifact_Manifest.csv"
PRESSURE_EPOCH = f"{CLOSURE_TOKEN}_Accepted_Day375_Pressure_Epoch.npz"
PRESSURE_EPOCH_SHA256 = "99d73cab1d33191a68578f29d3c03f9fac07ed77c39e124cc8eb5e5bf75aa84d"

A6E_REL = BASE_AV3 / "POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
A6E_STATE = "POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
A6E_STATE_SHA256 = "f9e3a7bd8c6dcc43d522e0cb99a0cede2bd212fd570085b4faf82dc71af8f803"

# --------------------------------------------------------------------------------------------------
# Repository source authorities.
# --------------------------------------------------------------------------------------------------

R29_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_"
    "Controlled_FrozenFlow_Transport_Candidate_Execution_NoTimeCommit.py"
)
R29_BLOB = "0bb9a8ce641a9769d5181503f737b1c976bc0ca2"

A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"

R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"

R5 = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_"
    "Controlled_SplitState_T1_PressureCapacity_Reconciliation_Execution.py"
)
R5_BLOB = "bfd1baff03c8670e627f526a8495a6a16d739519"

CLOSURE_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_R1_R1_R1_"
    "Comprehensive_Technical_Closure.py"
)
CLOSURE_BLOB = "ea1a26342e5367943bf459cefc5ff7aacefd0798"

SOURCE_BLOBS = {
    R29_RUNNER: R29_BLOB,
    A2E: A2E_BLOB,
    R2: R2_BLOB,
    E37A: E37A_BLOB,
    R5: R5_BLOB,
    CLOSURE_RUNNER: CLOSURE_BLOB,
}

OUT_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R29_R1"
OUT_REL = BASE / (
    OUT_TOKEN
    + "_Parent_Cartesian_PoreVolume_Semantics_Diagnostic_Freeze"
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
    rows = csvr(directory / filename)
    out: dict[str, str] = {}
    for row in rows:
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
    assert OUT_REL.name.startswith(OUT_TOKEN + "_")
    assert UNIFORM_PHI == BACKGROUND
    semantics = {
        "CV_transport_unchanged": True,
        "subsegment_delta_deposition_unchanged": True,
        "uniform_cartesian_PV_forbidden": True,
        "heterogeneous_cartesian_PV_required": True,
    }
    assert semantics["uniform_cartesian_PV_forbidden"]
    print("POSTV16 AV4 PIVOT P2-R6-R29-R1 structural self-test: PASS")


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
        gate("no_preexisting_R29R1_PASS", not (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").exists())
        gate("no_preexisting_R29R1_BLOCK", not (block_dir / f"{OUT_TOKEN}_Blocked_Report.json").exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R29_commit", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")

        for filename, expected in SOURCE_BLOBS.items():
            p = root / filename
            gate(f"{Path(filename).stem}_present", p.is_file(), str(p))
            actual = gt(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(filename).stem}_blob_exact", actual == expected, actual)

        # ------------------------------------------------------------------------------------------
        # Bind immutable R29 scientific fail.
        # ------------------------------------------------------------------------------------------
        stage = "R29_scientific_fail_authority"

        fail_path = drive / R29_FAIL_REL / R29_FAIL
        gate("R29_FAIL_present", fail_path.is_file(), str(fail_path))
        f29 = js(fail_path)
        fail_sha = sha(fail_path)

        gate("R29_FAIL_status_exact", f29.get("status") == R29_FAIL_STATUS, f29.get("status"))
        gate("R29_FAIL_stage_exact", f29.get("failed_stage") == R29_FAIL_STAGE, f29.get("failed_stage"))
        gate("R29_FAIL_gate_exact", f29.get("failed_gate") == R29_FAIL_GATE, f29.get("failed_gate"))
        gate("R29_FAIL_detail_exact", f29.get("detail") == R29_FAIL_DETAIL, f29.get("detail"))
        gate("R29_FAIL_candidate_not_accepted", f29.get("candidate_state_accepted") is False)
        gate("R29_FAIL_time_not_committed", f29.get("physical_time_committed") is False)
        gate("R29_FAIL_no_auto_dt_reduction", f29.get("automatic_dt_reduction_authorized") is False)
        gate("R29_FAIL_no_auto_rerun", f29.get("automatic_rerun_authorized") is False)

        # ------------------------------------------------------------------------------------------
        # Accepted parent + pressure epoch + heterogeneous PV authority.
        # ------------------------------------------------------------------------------------------
        stage = "accepted_parent_and_PV_authority"

        r25 = drive / R25R3_REL
        m25 = manifest(r25, R25R3_MANIFEST)
        state_path = r25 / R25R3_STATE
        gate("R25R3_state_SHA_exact", m25.get(R25R3_STATE) == R25R3_STATE_SHA256 and sha(state_path) == R25R3_STATE_SHA256)

        closure = drive / CLOSURE_REL
        mc = manifest(closure, CLOSURE_MANIFEST)
        pressure_path = closure / PRESSURE_EPOCH
        gate("pressure_epoch_SHA_exact", mc.get(PRESSURE_EPOCH) == PRESSURE_EPOCH_SHA256 and sha(pressure_path) == PRESSURE_EPOCH_SHA256)
        sc = js(closure / CLOSURE_SUMMARY)
        gate("pressure_refresh_accepted", sc.get("pressure_refresh_accepted") is True)
        gate("closure_capacity_passed", float(sc["independent_cell_capacity_max_excess_kg"]) <= 1e-8, sc["independent_cell_capacity_max_excess_kg"])

        a6e_path = drive / A6E_REL / A6E_STATE
        gate("A6E_state_SHA_exact", a6e_path.is_file() and sha(a6e_path) == A6E_STATE_SHA256, sha(a6e_path) if a6e_path.is_file() else "missing")

        with np.load(state_path, allow_pickle=False) as z:
            parent_mass = np.asarray(z["cartesian_component_mass_kg"], dtype=np.float64)
        with np.load(pressure_path, allow_pickle=False) as z:
            pressure_mass = np.asarray(z["pressure_compatible_grid_mass_kg"], dtype=np.float64)
            pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            accepted_sat = np.asarray(z["reconciled_saturation"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
        with np.load(a6e_path, allow_pickle=False) as z:
            phi = np.asarray(z["paired_porosity"], dtype=np.float64)

        gate("parent_mass_shape_exact", parent_mass.shape == GRID)
        gate("pressure_shape_exact", pressure.shape == GRID)
        gate("accepted_saturation_shape_exact", accepted_sat.shape == GRID)
        gate("paired_porosity_shape_exact", phi.shape == GRID)
        gate("paired_porosity_positive_finite", np.all(phi > 0.0) and np.isfinite(phi).all())
        gate("R25R3_parent_mass_equals_pressure_epoch", np.array_equal(parent_mass, pressure_mass))

        a2e = load_module(root / A2E, "r29r1_a2e")
        r2 = load_module(root / R2, "r29r1_r2")
        e37a = load_module(root / E37A, "r29r1_e37a")

        hetero_pv = phi * float(a2e.BULK_VOLUME_M3)
        uniform_pv_scalar = float(UNIFORM_PHI * float(a2e.BULK_VOLUME_M3))
        uniform_pv = np.full(GRID, uniform_pv_scalar, dtype=np.float64)

        gate("heterogeneous_PV_shape_positive", hetero_pv.shape == GRID and np.all(hetero_pv > 0.0))
        gate(
            "heterogeneous_PV_not_uniform_0p20",
            float(np.max(np.abs(hetero_pv - uniform_pv))) > 1e-12,
            float(np.max(np.abs(hetero_pv - uniform_pv))),
        )

        # ------------------------------------------------------------------------------------------
        # Side-by-side capacity diagnosis.
        # ------------------------------------------------------------------------------------------
        stage = "uniform_vs_heterogeneous_capacity_diagnosis"

        full_sat = np.full(GRID, float(a2e.INJECTED), dtype=np.float64)
        rho_at_max = np.asarray(
            r2.gas_density_from_state(full_sat, pressure, p_ref),
            dtype=np.float64,
        )

        uniform_capacity = uniform_pv * rho_at_max * MAX_SG
        hetero_capacity = hetero_pv * rho_at_max * MAX_SG

        uniform_excess_arr = parent_mass - uniform_capacity
        hetero_excess_arr = parent_mass - hetero_capacity

        uniform_max_excess = float(np.max(uniform_excess_arr))
        hetero_max_excess = float(np.max(hetero_excess_arr))
        uniform_violating_count = int(np.count_nonzero(uniform_excess_arr > 1e-8))
        hetero_cap_tol = max(1e-8, 1e-12 * max(float(np.max(hetero_capacity)), 1.0))
        hetero_violating_count = int(np.count_nonzero(hetero_excess_arr > hetero_cap_tol))

        gate(
            "uniform_PV_failure_reproduces_R29",
            abs(uniform_max_excess - 1750.620691678921) <= 1e-9,
            uniform_max_excess,
        )
        gate("uniform_PV_has_capacity_violations", uniform_violating_count > 0, uniform_violating_count)
        gate(
            "heterogeneous_PV_parent_capacity_closed",
            hetero_max_excess <= hetero_cap_tol,
            [hetero_max_excess, hetero_cap_tol],
        )
        gate("heterogeneous_PV_zero_violating_cells", hetero_violating_count == 0, hetero_violating_count)
        gate(
            "heterogeneous_capacity_matches_pressure_closure",
            abs(hetero_max_excess - float(sc["independent_cell_capacity_max_excess_kg"]))
            <= max(1e-8, 1e-10 * max(abs(hetero_max_excess), 1.0)),
            [hetero_max_excess, sc["independent_cell_capacity_max_excess_kg"]],
        )

        # Exact heterogeneous inversion must reproduce the accepted Day375 saturation.
        sg_hetero = np.asarray(
            a2e.invert_local_mass(r2, parent_mass, pressure, p_ref, hetero_pv),
            dtype=np.float64,
        )
        sat_hetero = float(a2e.BACKGROUND) + sg_hetero
        sat_err = float(np.max(np.abs(sat_hetero - accepted_sat)))
        gate("heterogeneous_inversion_reproduces_accepted_saturation", sat_err <= 1e-10, sat_err)

        mass_reconstructed = np.asarray(
            a2e.local_mass(r2, sat_hetero, pressure, p_ref, hetero_pv),
            dtype=np.float64,
        )
        mass_err = float(np.max(np.abs(mass_reconstructed - parent_mass)))
        gate("heterogeneous_inversion_cellwise_mass_reconstruction", mass_err <= 1e-8, mass_err)

        # The legacy scalar R2 inversion must fail exactly as R29 did.
        uniform_failure = None
        try:
            r2._invert_incremental_sg_from_mass(
                parent_mass,
                pressure,
                p_ref,
                uniform_pv_scalar,
            )
        except Exception as exc:
            uniform_failure = repr(exc)

        gate("legacy_uniform_R2_inversion_fails", uniform_failure is not None, uniform_failure)
        gate(
            "legacy_uniform_R2_failure_matches_R29",
            uniform_failure == R29_FAIL_DETAIL,
            uniform_failure,
        )

        # ------------------------------------------------------------------------------------------
        # Audit the second latent uniform-PV dependency in E37A mapback.
        # ------------------------------------------------------------------------------------------
        stage = "E37A_cartesian_closure_semantics_audit"

        map_src = inspect.getsource(e37a.map_control_volume_increment_to_grid)
        gate("E37A_delta_deposition_logic_present", "deposited_delta_mass" in map_src and "np.bincount" in map_src)
        gate("E37A_CV_delta_transfer_closure_present", "CV_to_subsegment_component_transfer_closure" in map_src)
        gate(
            "E37A_legacy_scalar_parent_mass_reconstruction_present",
            "float(cell_pore_volume_m3) * parent_rho * parent_sg" in map_src,
        )
        gate(
            "E37A_legacy_scalar_candidate_inversion_present",
            "_invert_incremental_sg_from_mass" in map_src
            and "cell_pore_volume_m3" in map_src,
        )

        # ------------------------------------------------------------------------------------------
        # Freeze corrected semantics for the next design/execution child.
        # ------------------------------------------------------------------------------------------
        stage = "corrected_semantics_freeze"

        protocol = {
            "milestone": M,
            "status": PASS,
            "diagnosis": {
                "R29_FAIL_sha256": fail_sha,
                "R29_failed_stage": R29_FAIL_STAGE,
                "R29_failed_gate": R29_FAIL_GATE,
                "R29_uniform_PV_max_capacity_excess_kg": uniform_max_excess,
                "R29_uniform_PV_violating_cell_count": uniform_violating_count,
                "authoritative_heterogeneous_PV_max_capacity_excess_kg": hetero_max_excess,
                "authoritative_heterogeneous_PV_violating_cell_count": hetero_violating_count,
                "accepted_parent_state_is_capacity_valid_under_AV4_authority": True,
                "classification": (
                    "uniform-E35 Cartesian pore-volume semantics were incorrectly applied "
                    "to the heterogeneous AV4 accepted parent"
                ),
            },
            "unchanged_physics": {
                "CV_transport_operator": "E37A.advance_component_mass_control_volumes",
                "CV_transport_semantics_changed": False,
                "subsegment_delta_mass_formula_changed": False,
                "SG7D_flat_cell_deposition_changed": False,
                "injection_production_ledger_changed": False,
                "R28_residual_preservation_semantics_changed": False,
                "frozen_dt_changed": False,
            },
            "corrected_cartesian_authority": {
                "pore_volume_field": "paired_porosity * A2E.BULK_VOLUME_M3",
                "porosity_source": A6E_STATE,
                "porosity_source_sha256": A6E_STATE_SHA256,
                "uniform_phi_0p20_cartesian_PV_authorized": False,
                "parent_cartesian_mass_source": "accepted R25-R3 cartesian_component_mass_kg directly",
                "parent_cartesian_mass_may_be_reconstructed_from_uniform_PV_saturation": False,
                "parent_saturation_inversion": "A2E.invert_local_mass with heterogeneous pore-volume array",
                "candidate_capacity": "A2E.local_mass at saturation=0.80 with heterogeneous pore-volume array",
                "candidate_saturation_inversion": "A2E.invert_local_mass with heterogeneous pore-volume array",
            },
            "corrected_delta_mapback": {
                "reuse_E37A_subsegment_delta_construction": True,
                "reuse_SG7D_cell_deposition": True,
                "do_not_use_E37A_scalar_parent_mass_reconstruction": True,
                "do_not_use_E37A_scalar_candidate_grid_inversion": True,
                "candidate_cartesian_identity": "M_grid_candidate = accepted_M_grid_parent + Delta_M_grid",
                "represented_candidate_identity": "M_represented_candidate = M_represented_parent + Delta_M_grid",
                "residual_candidate_identity": "M_residual_candidate = M_residual_parent exactly",
                "split_identity": "M_grid_candidate = M_residual_candidate + M_represented_candidate",
            },
            "firewalls": {
                "automatic_rerun_of_R29": False,
                "automatic_dt_reduction": False,
                "support_growth": False,
                "residual_promotion": False,
                "mass_clipping_or_rescaling": False,
                "physical_time_commit": False,
                "P3_authorized": False,
            },
        }

        classification = (
            "R6R29R1_R29_PARENT_INVERSION_FAIL_ATTRIBUTED_TO_UNIFORM_E35_PORE_VOLUME_"
            "SEMANTICS_MISMATCH_AV4_HETEROGENEOUS_PARENT_CAPACITY_VALID_R29R2_REPAIR_DESIGN_NEXT"
        )

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "source_R29_SCIENTIFIC_FAIL_sha256": fail_sha,
            "source_R25R3_state_sha256": R25R3_STATE_SHA256,
            "source_pressure_epoch_sha256": PRESSURE_EPOCH_SHA256,
            "source_A6E_porosity_state_sha256": A6E_STATE_SHA256,
            "uniform_phi_used_by_R29": UNIFORM_PHI,
            "uniform_PV_scalar_m3": uniform_pv_scalar,
            "uniform_PV_max_capacity_excess_kg": uniform_max_excess,
            "uniform_PV_violating_cell_count": uniform_violating_count,
            "heterogeneous_porosity_min": float(np.min(phi)),
            "heterogeneous_porosity_max": float(np.max(phi)),
            "heterogeneous_PV_min_m3": float(np.min(hetero_pv)),
            "heterogeneous_PV_max_m3": float(np.max(hetero_pv)),
            "heterogeneous_PV_max_capacity_excess_kg": hetero_max_excess,
            "heterogeneous_PV_capacity_tolerance_kg": hetero_cap_tol,
            "heterogeneous_PV_violating_cell_count": hetero_violating_count,
            "heterogeneous_inversion_saturation_max_abs_error": sat_err,
            "heterogeneous_inversion_cellwise_mass_max_abs_error_kg": mass_err,
            "accepted_parent_capacity_valid_under_AV4_authority": True,
            "R29_transport_execution_reached": False,
            "state_mutation_executed": False,
            "physical_time_committed": False,
            "P3_authorized": False,
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "P2_R6_R29_R2_authorized": True,
            "P2_R6_R29_R2_name": (
                "R29 Heterogeneous Cartesian Pore-Volume / Delta-Mapback Repair Design Freeze"
            ),
            "P2_R6_R29_R2_design_only": True,
            "P2_R6_R29_R2_execution_authorized": False,
            "P2_R6_R29_R2_must_bind_R29_FAIL_SHA": True,
            "P2_R6_R29_R2_R29_FAIL_sha256": fail_sha,
            "R29_parent_scientific_FAIL_remains_immutable": True,
            "CV_transport_operator_change_authorized": False,
            "subsegment_delta_formula_change_authorized": False,
            "uniform_cartesian_PV_authorized": False,
            "heterogeneous_AV4_cartesian_PV_required": True,
            "automatic_dt_reduction_authorized": False,
            "support_growth_authorized": False,
            "physical_time_advance_authorized": False,
            "P3_authorized": False,
        }

        out.mkdir(parents=True, exist_ok=False)
        (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out / f"{OUT_TOKEN}_Cartesian_PoreVolume_Semantics_Repair_Protocol.json").write_bytes(jb(protocol))
        (out / f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))
        (out / f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(rows))

        print("=" * 190)
        print(M, "PASS")
        print("R29 SCIENTIFIC FAIL SHA256                  :", fail_sha)
        print("Uniform-PV max capacity excess kg           :", uniform_max_excess)
        print("Uniform-PV violating cells                  :", uniform_violating_count)
        print("Heterogeneous-PV max capacity excess kg     :", hetero_max_excess)
        print("Heterogeneous-PV violating cells            :", hetero_violating_count)
        print("Heterogeneous inversion saturation error    :", sat_err)
        print("Heterogeneous cellwise mass error kg        :", mass_err)
        print("Accepted parent valid under AV4 authority   : True")
        print("R29-R2 repair design authorized             : True")
        print("Execution / time / P3                       : False / False / False")
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
                "R29_FAIL_preserved": True,
                "R25R3_parent_state_preserved": True,
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
        print("R29 FAIL AND ACCEPTED PARENT STATE PRESERVED.")
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
