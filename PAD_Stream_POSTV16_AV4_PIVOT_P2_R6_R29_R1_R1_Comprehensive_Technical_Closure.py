#!/usr/bin/env python3
from __future__ import annotations

import argparse, ast, csv, hashlib, importlib.util, inspect, io, json, re, subprocess, sys
from pathlib import Path
from typing import Any
import numpy as np

M = "POSTV16-AV4-PIVOT-P2-R6-R29-R1-R1"
NAME = "R29-R1 Comprehensive Technical Closure — Pore-Volume Diagnostic Wrapper Recovery"

PASS = (
    "AV4PIVOTP2R6R29R1R1_COMPREHENSIVE_TECHNICAL_CLOSURE_PASS_"
    "R29R1_DIAGNOSTIC_RECOVERED_NO_SCIENCE_STATE_MUTATION"
)
BLOCK = "AV4PIVOTP2R6R29R1R1_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "b1d966e2b22526b7b05a725c561836f51ac8d9b9"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"

GRID = (15, 50, 50)
BACKGROUND = 0.20
INJECTED = 0.80
MAX_SG = 0.60
UNIFORM_PHI = 0.20

# --------------------------------------------------------------------------------------------------
# Immutable R29-R1 BLOCK.
# --------------------------------------------------------------------------------------------------

R29R1_BLOCK_REL = BASE / "POSTV16_AV4_PIVOT_P2_R6_R29_R1_BLOCKED"
R29R1_BLOCK = "POSTV16_AV4_PIVOT_P2_R6_R29_R1_Blocked_Report.json"
R29R1_BLOCK_STATUS = "AV4PIVOTP2R6R29R1_TECHNICAL_OR_AUTHORITY_BLOCK"
R29R1_BLOCK_STAGE = "uniform_vs_heterogeneous_capacity_diagnosis"
R29R1_BLOCK_EXCEPTION = "GateError('legacy_uniform_R2_failure_matches_R29')"

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
R29_EXPECTED_EXCESS_KG = 1750.620691678921

# --------------------------------------------------------------------------------------------------
# Accepted parent state / pressure epoch / porosity authority.
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

R29R1_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R1_"
    "Parent_Cartesian_PoreVolume_Semantics_Diagnostic_Freeze.py"
)
R29R1_BLOB = "766540b694adf65754a615047196eec2f8e88c1f"

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

CLOSURE_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_R1_R1_R1_"
    "Comprehensive_Technical_Closure.py"
)
CLOSURE_BLOB = "ea1a26342e5367943bf459cefc5ff7aacefd0798"

SOURCE_BLOBS = {
    R29R1_RUNNER: R29R1_BLOB,
    R29_RUNNER: R29_BLOB,
    A2E: A2E_BLOB,
    R2: R2_BLOB,
    E37A: E37A_BLOB,
    CLOSURE_RUNNER: CLOSURE_BLOB,
}

OUT_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R29_R1_R1"
OUT_REL = BASE / (
    OUT_TOKEN + "_Comprehensive_Technical_Closure_PoreVolume_Diagnostic"
)
BLOCK_REL = BASE / (OUT_TOKEN + "_BLOCKED")

REQUIRED_RECOVERED_GATES = (
    "uniform_PV_failure_reproduces_R29",
    "uniform_PV_has_capacity_violations",
    "heterogeneous_PV_parent_capacity_closed",
    "heterogeneous_PV_zero_violating_cells",
    "heterogeneous_capacity_matches_pressure_closure",
    "heterogeneous_inversion_reproduces_accepted_saturation",
    "heterogeneous_inversion_cellwise_mass_reconstruction",
    "legacy_uniform_R2_inversion_fails",
)

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


def normalize_gate_detail(detail: Any) -> str:
    s = str(detail)
    # R29-R1 stores repr(detail) in the gate matrix. If detail was itself a string,
    # the BLOCK report contains one extra quoting layer. Remove it safely.
    try:
        v = ast.literal_eval(s)
        if isinstance(v, str):
            s = v
    except Exception:
        pass
    return s


def parse_capacity_exception(text: str) -> float:
    s = normalize_gate_detail(text)
    m = re.search(
        r"capillary_cell_mass_capacity_exceeded:([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)",
        s,
    )
    if not m:
        raise GateError(f"capacity_exception_unparseable:{s}")
    return float(m.group(1))


def selftest() -> None:
    sample = '"GateError(\'capillary_cell_mass_capacity_exceeded:1750.6206916789192\')"'
    x = parse_capacity_exception(sample)
    assert abs(x - 1750.6206916789192) < 1e-12
    assert REQUIRED_RECOVERED_GATES[-1] == "legacy_uniform_R2_inversion_fails"
    print("POSTV16 AV4 PIVOT P2-R6-R29-R1-R1 structural self-test: PASS")


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
        gate("no_preexisting_R29R1R1_PASS", not (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").exists())
        gate("no_preexisting_R29R1R1_BLOCK", not (block_dir / f"{OUT_TOKEN}_Blocked_Report.json").exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R29R1_commit", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for filename, expected in SOURCE_BLOBS.items():
            p = root / filename
            gate(f"{Path(filename).stem}_present", p.is_file(), str(p))
            actual = gt(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(filename).stem}_blob_exact", actual == expected, actual)

        # ------------------------------------------------------------------------------------------
        # Immutable R29-R1 BLOCK authority.
        # ------------------------------------------------------------------------------------------
        stage = "R29R1_BLOCK_authority"

        r29r1_block_path = drive / R29R1_BLOCK_REL / R29R1_BLOCK
        gate("R29R1_BLOCK_present", r29r1_block_path.is_file(), str(r29r1_block_path))
        b29r1 = js(r29r1_block_path)
        r29r1_block_sha = sha(r29r1_block_path)

        gate("R29R1_BLOCK_status_exact", b29r1.get("status") == R29R1_BLOCK_STATUS, b29r1.get("status"))
        gate("R29R1_BLOCK_stage_exact", b29r1.get("failed_stage") == R29R1_BLOCK_STAGE, b29r1.get("failed_stage"))
        gate("R29R1_BLOCK_exception_exact", b29r1.get("exception") == R29R1_BLOCK_EXCEPTION, b29r1.get("exception"))
        gate("R29R1_BLOCK_state_mutation_false", b29r1.get("state_mutation_executed") is False)
        gate("R29R1_BLOCK_time_advance_false", b29r1.get("physical_time_advance_executed") is False)
        gate("R29R1_BLOCK_auto_rerun_false", b29r1.get("automatic_rerun_authorized") is False)

        completed = b29r1.get("gates_completed")
        gate("R29R1_BLOCK_gate_matrix_present", isinstance(completed, list) and len(completed) > 0, len(completed) if isinstance(completed, list) else None)

        by_name = {str(row.get("gate")): row for row in completed}
        for name in REQUIRED_RECOVERED_GATES:
            gate(f"recover_{name}", name in by_name and by_name[name].get("pass") is True, by_name.get(name))

        failed_gate = by_name.get("legacy_uniform_R2_failure_matches_R29")
        gate(
            "failed_exact_string_gate_present_false",
            isinstance(failed_gate, dict) and failed_gate.get("pass") is False,
            failed_gate,
        )

        actual_exception_text = normalize_gate_detail(failed_gate.get("detail", ""))
        actual_exception_excess = parse_capacity_exception(actual_exception_text)

        gate(
            "failed_exception_numeric_semantics_match_R29",
            abs(actual_exception_excess - R29_EXPECTED_EXCESS_KG) <= 1e-9,
            [actual_exception_text, actual_exception_excess, R29_EXPECTED_EXCESS_KG],
        )
        gate(
            "technical_failure_is_float_string_format_only",
            actual_exception_text != f"GateError('capillary_cell_mass_capacity_exceeded:{R29_EXPECTED_EXCESS_KG}')",
            actual_exception_text,
        )

        # ------------------------------------------------------------------------------------------
        # Immutable R29 SCIENTIFIC FAIL authority.
        # ------------------------------------------------------------------------------------------
        stage = "R29_FAIL_authority"

        r29_fail_path = drive / R29_FAIL_REL / R29_FAIL
        gate("R29_FAIL_present", r29_fail_path.is_file(), str(r29_fail_path))
        f29 = js(r29_fail_path)
        r29_fail_sha = sha(r29_fail_path)

        gate("R29_FAIL_status_exact", f29.get("status") == R29_FAIL_STATUS, f29.get("status"))
        gate("R29_FAIL_stage_exact", f29.get("failed_stage") == R29_FAIL_STAGE, f29.get("failed_stage"))
        gate("R29_FAIL_gate_exact", f29.get("failed_gate") == R29_FAIL_GATE, f29.get("failed_gate"))
        gate("R29_FAIL_candidate_not_accepted", f29.get("candidate_state_accepted") is False)
        gate("R29_FAIL_time_not_committed", f29.get("physical_time_committed") is False)

        r29_fail_excess = parse_capacity_exception(str(f29.get("detail", "")))
        gate(
            "R29_FAIL_numeric_excess_exact",
            abs(r29_fail_excess - R29_EXPECTED_EXCESS_KG) <= 1e-12,
            r29_fail_excess,
        )
        gate(
            "R29R1_recovered_exception_matches_R29_FAIL_numerically",
            abs(actual_exception_excess - r29_fail_excess) <= 1e-9,
            [actual_exception_excess, r29_fail_excess],
        )

        # ------------------------------------------------------------------------------------------
        # Independent no-mutation numeric revalidation of the diagnostic.
        # ------------------------------------------------------------------------------------------
        stage = "independent_numeric_revalidation"

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

        gate("accepted_parent_mass_identity", np.array_equal(parent_mass, pressure_mass))
        gate("paired_porosity_shape_positive", phi.shape == GRID and np.all(phi > 0.0))

        a2e = load_module(root / A2E, "r29r1r1_a2e")
        r2 = load_module(root / R2, "r29r1r1_r2")
        e37a = load_module(root / E37A, "r29r1r1_e37a")

        hetero_pv = phi * float(a2e.BULK_VOLUME_M3)
        uniform_pv_scalar = float(UNIFORM_PHI * float(a2e.BULK_VOLUME_M3))
        uniform_pv = np.full(GRID, uniform_pv_scalar, dtype=np.float64)

        full_sat = np.full(GRID, float(a2e.INJECTED), dtype=np.float64)
        rho_at_max = np.asarray(r2.gas_density_from_state(full_sat, pressure, p_ref), dtype=np.float64)

        uniform_capacity = uniform_pv * rho_at_max * MAX_SG
        hetero_capacity = hetero_pv * rho_at_max * MAX_SG

        uniform_excess_arr = parent_mass - uniform_capacity
        hetero_excess_arr = parent_mass - hetero_capacity
        uniform_max_excess = float(np.max(uniform_excess_arr))
        hetero_max_excess = float(np.max(hetero_excess_arr))
        uniform_violating = int(np.count_nonzero(uniform_excess_arr > 1e-8))
        hetero_cap_tol = max(1e-8, 1e-12 * max(float(np.max(hetero_capacity)), 1.0))
        hetero_violating = int(np.count_nonzero(hetero_excess_arr > hetero_cap_tol))

        gate("uniform_capacity_excess_revalidated", abs(uniform_max_excess - R29_EXPECTED_EXCESS_KG) <= 1e-9, uniform_max_excess)
        gate("uniform_capacity_violating_cells_positive", uniform_violating > 0, uniform_violating)
        gate("heterogeneous_capacity_closed", hetero_max_excess <= hetero_cap_tol, [hetero_max_excess, hetero_cap_tol])
        gate("heterogeneous_capacity_zero_violating_cells", hetero_violating == 0, hetero_violating)

        sg_hetero = np.asarray(
            a2e.invert_local_mass(r2, parent_mass, pressure, p_ref, hetero_pv),
            dtype=np.float64,
        )
        sat_hetero = float(a2e.BACKGROUND) + sg_hetero
        sat_err = float(np.max(np.abs(sat_hetero - accepted_sat)))
        gate("heterogeneous_inversion_revalidates_accepted_saturation", sat_err <= 1e-10, sat_err)

        mass_reconstructed = np.asarray(
            a2e.local_mass(r2, sat_hetero, pressure, p_ref, hetero_pv),
            dtype=np.float64,
        )
        mass_err = float(np.max(np.abs(mass_reconstructed - parent_mass)))
        gate("heterogeneous_cellwise_mass_reconstruction_revalidated", mass_err <= 1e-8, mass_err)

        # ------------------------------------------------------------------------------------------
        # Comprehensive source/schema/semantic audit for downstream repair.
        # ------------------------------------------------------------------------------------------
        stage = "downstream_repair_semantic_audit"

        map_src = inspect.getsource(e37a.map_control_volume_increment_to_grid)
        adv_src = inspect.getsource(e37a.advance_component_mass_control_volumes)

        gate("E37A_CV_transport_operator_standalone", "cell_pore_volume_m3" not in inspect.signature(e37a.advance_component_mass_control_volumes).parameters)
        gate("E37A_CV_transport_source_sink_closure_present", "component_mass_FV_global_closure" in adv_src)
        gate("E37A_subsegment_delta_deposition_present", "sub_delta_mass" in map_src and "deposited_delta_mass" in map_src and "np.bincount" in map_src)
        gate("E37A_subsegment_transfer_closure_present", "CV_to_subsegment_component_transfer_closure" in map_src)
        gate("E37A_scalar_parent_mass_dependency_present", "float(cell_pore_volume_m3) * parent_rho * parent_sg" in map_src)
        gate("E37A_scalar_candidate_inversion_dependency_present", "_invert_incremental_sg_from_mass" in map_src and "cell_pore_volume_m3" in map_src)

        # Confirm intended repair can be isolated to Cartesian closure semantics.
        gate(
            "repair_boundary_CV_transport_unchanged",
            "cell_pore_volume_m3" not in inspect.signature(e37a.advance_component_mass_control_volumes).parameters,
        )
        gate(
            "repair_boundary_delta_deposition_reusable",
            all(token in map_src for token in ("cv_id", "flat_cell", "pv_m3", "pseg_psi", "sub_delta_mass", "deposited_delta_mass")),
        )

        # ------------------------------------------------------------------------------------------
        # Publish comprehensive technical closure.
        # ------------------------------------------------------------------------------------------
        stage = "technical_closure_publication"

        classification = (
            "R6R29R1R1_TECHNICAL_CLOSURE_RECOVERS_R29R1_DIAGNOSTIC_"
            "EXACT_STRING_FLOAT_FORMAT_GATE_ONLY_AV4_HETEROGENEOUS_PARENT_VALID_"
            "R29R2_REPAIR_DESIGN_NEXT"
        )

        closure_contract = {
            "milestone": M,
            "status": PASS,
            "closure_type": "comprehensive_technical_closure_no_transport_science_rerun",
            "source_R29R1_BLOCK": {
                "sha256": r29r1_block_sha,
                "status": R29R1_BLOCK_STATUS,
                "failed_stage": R29R1_BLOCK_STAGE,
                "exception": R29R1_BLOCK_EXCEPTION,
                "immutable": True,
            },
            "source_R29_SCIENTIFIC_FAIL": {
                "sha256": r29_fail_sha,
                "status": R29_FAIL_STATUS,
                "immutable": True,
            },
            "recovered_R29R1_diagnostic": {
                "all_preceding_scientific_diagnostic_gates_PASS": True,
                "recovered_gate_count": len(REQUIRED_RECOVERED_GATES),
                "failed_wrapper_gate": "legacy_uniform_R2_failure_matches_R29",
                "failure_type": "exact exception-string float formatting equality",
                "actual_exception_text": actual_exception_text,
                "actual_exception_excess_kg": actual_exception_excess,
                "R29_FAIL_excess_kg": r29_fail_excess,
                "numeric_semantics_match": True,
            },
            "independent_revalidation": {
                "uniform_PV_max_capacity_excess_kg": uniform_max_excess,
                "uniform_PV_violating_cell_count": uniform_violating,
                "heterogeneous_PV_max_capacity_excess_kg": hetero_max_excess,
                "heterogeneous_PV_capacity_tolerance_kg": hetero_cap_tol,
                "heterogeneous_PV_violating_cell_count": hetero_violating,
                "heterogeneous_inversion_saturation_max_abs_error": sat_err,
                "heterogeneous_cellwise_mass_max_abs_error_kg": mass_err,
                "accepted_parent_capacity_valid_under_AV4_authority": True,
            },
            "repair_boundary": {
                "CV_transport_operator_change_authorized": False,
                "subsegment_delta_formula_change_authorized": False,
                "SG7D_cell_deposition_change_authorized": False,
                "heterogeneous_cartesian_pore_volume_required": True,
                "uniform_phi_0p20_cartesian_PV_authorized": False,
                "direct_accepted_parent_cartesian_mass_required": True,
                "heterogeneous_candidate_capacity_and_inversion_required": True,
            },
            "firewalls": {
                "R29_FAIL_overwritten": False,
                "R29R1_BLOCK_overwritten": False,
                "automatic_rerun": False,
                "automatic_dt_reduction": False,
                "state_mutation": False,
                "physical_time_advance": False,
                "P3_authorized": False,
            },
        }

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "source_R29R1_BLOCK_sha256": r29r1_block_sha,
            "source_R29_SCIENTIFIC_FAIL_sha256": r29_fail_sha,
            "R29R1_failed_stage": R29R1_BLOCK_STAGE,
            "R29R1_failed_gate": "legacy_uniform_R2_failure_matches_R29",
            "R29R1_actual_exception_text": actual_exception_text,
            "R29R1_actual_exception_excess_kg": actual_exception_excess,
            "R29_FAIL_excess_kg": r29_fail_excess,
            "recovered_preceding_diagnostic_gate_count": len(REQUIRED_RECOVERED_GATES),
            "uniform_PV_max_capacity_excess_kg": uniform_max_excess,
            "uniform_PV_violating_cell_count": uniform_violating,
            "heterogeneous_PV_max_capacity_excess_kg": hetero_max_excess,
            "heterogeneous_PV_capacity_tolerance_kg": hetero_cap_tol,
            "heterogeneous_PV_violating_cell_count": hetero_violating,
            "heterogeneous_inversion_saturation_max_abs_error": sat_err,
            "heterogeneous_inversion_cellwise_mass_max_abs_error_kg": mass_err,
            "accepted_parent_capacity_valid_under_AV4_authority": True,
            "technical_wrapper_full_audit_completed": True,
            "transport_science_rerun": False,
            "state_mutation_executed": False,
            "physical_time_advance_executed": False,
            "P3_authorized": False,
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "P2_R6_R29_R2_authorized": True,
            "P2_R6_R29_R2_name": "R29 Heterogeneous Cartesian Pore-Volume / Delta-Mapback Repair Design Freeze",
            "P2_R6_R29_R2_design_only": True,
            "P2_R6_R29_R2_execution_authorized": False,
            "P2_R6_R29_R2_must_bind_R29R1_BLOCK_SHA": True,
            "P2_R6_R29_R2_R29R1_BLOCK_sha256": r29r1_block_sha,
            "P2_R6_R29_R2_must_bind_R29_FAIL_SHA": True,
            "P2_R6_R29_R2_R29_FAIL_sha256": r29_fail_sha,
            "R29_SCIENTIFIC_FAIL_remains_immutable": True,
            "R29R1_TECHNICAL_BLOCK_remains_immutable": True,
            "CV_transport_operator_change_authorized": False,
            "subsegment_delta_formula_change_authorized": False,
            "uniform_cartesian_PV_authorized": False,
            "heterogeneous_AV4_cartesian_PV_required": True,
            "automatic_dt_reduction_authorized": False,
            "automatic_rerun_authorized": False,
            "support_growth_authorized": False,
            "state_mutation_authorized": False,
            "physical_time_advance_authorized": False,
            "P3_authorized": False,
        }

        out.mkdir(parents=True, exist_ok=False)
        (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out / f"{OUT_TOKEN}_Comprehensive_Technical_Closure_Contract.json").write_bytes(jb(closure_contract))
        (out / f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))
        (out / f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(rows))

        print("=" * 190)
        print(M, "PASS")
        print("R29-R1 BLOCK SHA256                       :", r29r1_block_sha)
        print("R29 SCIENTIFIC FAIL SHA256                :", r29_fail_sha)
        print("Actual legacy exception                   :", actual_exception_text)
        print("Parsed exception excess kg                :", actual_exception_excess)
        print("Uniform-PV max excess kg                  :", uniform_max_excess)
        print("Heterogeneous-PV max excess kg            :", hetero_max_excess)
        print("Heterogeneous violating cells             :", hetero_violating)
        print("Accepted AV4 parent capacity valid        : True")
        print("Transport science rerun                   : False")
        print("R29-R2 repair design authorized           : True")
        print("State mutation / time / P3                : False / False / False")
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
                "R29R1_BLOCK_preserved": True,
                "R29_FAIL_preserved": True,
                "R25R3_parent_state_preserved": True,
                "transport_science_rerun": False,
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
        print("SOURCE BLOCK/FAIL AND ACCEPTED PARENT STATE PRESERVED.")
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
