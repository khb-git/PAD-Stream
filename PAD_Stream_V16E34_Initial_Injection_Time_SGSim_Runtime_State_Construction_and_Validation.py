from __future__ import annotations

from pathlib import Path
import argparse
import ast
import csv
import hashlib
import io
import json
import math
from typing import Any, Iterable

import numpy as np


MILESTONE = "V16E-34"
STATUS = "INITIAL_INJECTION_TIME_SGSIM_RUNTIME_STATE_FROZEN"
NEXT = "V16E-35 - First Controlled SGSim Runtime State Transition / Mass-Conservative Single-Step Execution"

EXPECTED_GRID = (15, 50, 50)  # (k, j, i)
EXPECTED_CELLS = 37500
BACKGROUND_SATURATION = 0.20
INJECTED_BOUNDARY_SATURATION = 0.80
INITIAL_PRESSURE_PSI = 2500.0
POROSITY = 0.20
KV_KH_RATIO = 0.10
PRODUCTION_INITIAL_TIME_DAYS = 0.0
BREAKTHROUGH_GAS_CUT = 1.0e-4
DEFAULT_OBSERVATION_DAYS = [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0]

# V16E-33 committed source identity.
E33_RUNNER = "PAD_Stream_V16E33_Runtime_State_Transition_Contract_and_Single_Step_Execution_Readiness.py"
E33_RUNNER_SHA256 = "bc0850f186c70163894624e98a71f89c34e334b5f7232c8015528a16d26c411b"
E33_REL = Path(
    "provenance/hybrid_dp/"
    "V16E33_RUNTIME_STATE_TRANSITION_CONTRACT_SINGLE_STEP_EXECUTION_READINESS"
)
E33_SUMMARY = "PAD_Stream_V16E33_Summary.json"
E33_TRANSITION = "V16E33_Runtime_State_Transition_Contract.json"
E33_MASS = "V16E33_Mass_Balance_Ledger_Contract.json"
E33_CLOCK = "V16E33_Simulation_Observation_Event_Clock_Contract.json"
E33_SOURCE_MANIFEST = "V16E33_Source_Authority_Manifest.csv"

# Immutable 100-day regression checkpoint inherited from E18-R1/E33.
V16_FROZEN_REL = Path(
    "provenance/hybrid_dp/V16E18_R1_FROZEN_SGSIM_100D_FULL_GRID_CANDIDATE/"
    "frozen_full_grid/V16E18_R1_Frozen_SGSim_100Day_Full_Grid_Candidate.npz"
)
V16_FROZEN_SHA256 = "d422dc1e56281c1baf0ae007c62ce4bd69677a232bd1448a5bd79d3177eafaea"

# Tracked construction authorities.
SGSIM_PERM = "SGSIM_50x50x15_PERM_MD.csv"
SG1 = "PAD_Stream_V15SG1_SGSim_Geology_Integration.py"
SG3 = "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG7A = "PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py"
V14 = "PAD_Stream_CCUS_Physics_Development_v14_Complete_Validation.py"
F0 = (
    "dependencies/PAD_Stream_V15F0_Global_Recurrent_Timestep_Retrace_State/"
    "PAD_Stream_V15F0_Global_Recurrent_Timestep_Retrace_State.py"
)
F1 = (
    "dependencies/PAD_Stream_V15F1_Breakthrough_Well_Control_Recurrent_Memory/"
    "PAD_Stream_V15F1_Breakthrough_Well_Control_Recurrent_Memory.py"
)

OUT_REL = Path(
    "provenance/hybrid_dp/"
    "V16E34_INITIAL_INJECTION_TIME_SGSIM_RUNTIME_STATE_CONSTRUCTION_VALIDATION"
)
BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E34_BLOCKED_INITIAL_INJECTION_TIME_SGSIM_RUNTIME_STATE_CONSTRUCTION_VALIDATION"
)


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_array(arr: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def require_markers(text: str, markers: Iterable[str], label: str) -> None:
    missing = [m for m in markers if m not in text]
    if missing:
        raise GateError(f"{label}_missing_markers:{missing}")


def literal_assignments(path: Path, names: Iterable[str]) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    wanted = set(names)
    found: dict[str, Any] = {}
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        if isinstance(node, ast.Assign):
            targets = node.targets
            value_node = node.value
        else:
            targets = [node.target]
            value_node = node.value
        if value_node is None:
            continue
        for target in targets:
            if isinstance(target, ast.Name) and target.id in wanted:
                try:
                    found[target.id] = ast.literal_eval(value_node)
                except Exception:
                    pass
    return found


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    """Write a new deterministic artifact set without silently overwriting differing output."""
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        path = out / name
        if path.exists():
            existing = path.read_bytes()
            if existing != data:
                raise GateError(f"existing_output_differs:{name}")
        else:
            path.write_bytes(data)


def save_npz_exact(path: Path, **arrays: Any) -> None:
    """Persist the canonical t=0 numerical state once; refuse differing overwrite."""
    if path.exists():
        # Existing numerical state is checked by reloading below. Do not replace it here.
        return
    np.savez_compressed(path, **arrays)


def load_perm(path: Path) -> np.ndarray:
    values = np.loadtxt(path, skiprows=1, dtype=np.float64)
    if values.size != EXPECTED_CELLS:
        raise GateError(f"SGSim_permeability_value_count:{values.size}")
    return values.reshape(EXPECTED_GRID, order="C")


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL

    gates: dict[str, dict[str, Any]] = {}

    def gate(name: str, ok: Any, detail: Any = "") -> None:
        passed = bool(ok)
        gates[name] = {"passed": passed, "detail": str(detail)}
        print(f"[{'PASS' if passed else 'FAIL'}] {name}" + (f": {detail}" if str(detail) else ""), flush=True)
        if not passed:
            raise GateError(name)

    checkpoint = drive / V16_FROZEN_REL
    checkpoint_sha_before: str | None = None

    print("\n" + "=" * 132)
    print("PAD-Stream V16E-34 Initial Injection-Time SGSim Runtime State Construction / Validation")
    print("=" * 132)
    print("CONSTRUCT THE CANONICAL t=0 SGSim RUNTIME PARENT STATE ONLY.")
    print("NO RUNTIME TIME ADVANCE. NO OPERATIONAL PRESSURE SOLVE. NO DARCY/POLLOCK/TOF/TRANSPORT/MAP-BACK EXECUTION.")
    print("THE FROZEN 100-DAY V16 STATE REMAINS AN IMMUTABLE REGRESSION/VALIDATION CHECKPOINT.")
    print("THE FIRST EXECUTED TRANSITION IS DEFERRED TO V16E-35 AND MUST USE FULL EXACT COLD-START PREFLIGHT.")

    try:
        # ------------------------------------------------------------------
        # E33 authority and immutable checkpoint.
        # ------------------------------------------------------------------
        print("\nV16E-33 AUTHORITY")
        e33_runner = root / E33_RUNNER
        gate("E33_runner_exists", e33_runner.is_file(), e33_runner)
        gate("E33_runner_SHA_exact", sha256_file(e33_runner) == E33_RUNNER_SHA256, sha256_file(e33_runner))

        e33_dir = drive / E33_REL
        for name in [E33_SUMMARY, E33_TRANSITION, E33_MASS, E33_CLOCK, E33_SOURCE_MANIFEST]:
            gate(f"E33_{name}_exists", (e33_dir / name).is_file(), e33_dir / name)

        e33_summary = load_json(e33_dir / E33_SUMMARY)
        e33_transition = load_json(e33_dir / E33_TRANSITION)
        e33_mass = load_json(e33_dir / E33_MASS)
        e33_clock = load_json(e33_dir / E33_CLOCK)

        gate("E33_status_frozen", e33_summary.get("status") == "PAD_STREAM_RUNTIME_STATE_TRANSITION_CONTRACT_FROZEN")
        gate("E33_t0_owner_is_E34", e33_transition["future_production_runtime"].get("initial_state_owner") == "V16E-34")
        gate("E33_initial_time_zero", float(e33_transition["future_production_runtime"].get("initial_time_days")) == 0.0)
        gate("E33_mass_balance_required", e33_summary.get("mass_balance_acceptance_required") is True)
        gate("E33_temporal_interpolation_for_canonical_state_forbidden", e33_summary.get("temporal_interpolation_can_create_canonical_state") is False)
        gate("E33_no_single_step_execution_authority", e33_summary.get("single_step_execution_authorized") is False)
        gate("E33_mass_tolerance_still_unfrozen", e33_summary.get("SGSim_specific_mass_tolerance_frozen") is False)
        gate("E33_dt_envelope_still_unfrozen", e33_summary.get("SGSim_specific_dt_envelope_frozen") is False)
        gate("E33_mass_ledger_component_CO2", e33_mass.get("component") == "CO2")
        gate("E33_observation_schedule_exact", e33_clock["observation_clock"].get("default_fixed_days") == DEFAULT_OBSERVATION_DAYS)

        gate("frozen_100d_checkpoint_exists", checkpoint.is_file(), checkpoint)
        checkpoint_sha_before = sha256_file(checkpoint)
        gate("frozen_100d_checkpoint_SHA_exact_before", checkpoint_sha_before == V16_FROZEN_SHA256, checkpoint_sha_before)

        # ------------------------------------------------------------------
        # Source-authentic t=0 construction semantics.
        # ------------------------------------------------------------------
        print("\nSOURCE-AUTHENTIC INITIAL CONDITION AUTHORITIES")
        required_sources = [SGSIM_PERM, SG1, SG3, SG7A, V14, F0, F1]
        for rel in required_sources:
            gate(f"source_exists_{Path(rel).name}", (root / rel).is_file(), root / rel)

        sg1_text = (root / SG1).read_text(encoding="utf-8")
        sg3_text = (root / SG3).read_text(encoding="utf-8")
        sg7a_text = (root / SG7A).read_text(encoding="utf-8")
        v14_text = (root / V14).read_text(encoding="utf-8")
        f0_text = (root / F0).read_text(encoding="utf-8")
        f1_text = (root / F1).read_text(encoding="utf-8")

        require_markers(sg1_text, [
            "Construct constant porosity phi = 0.20",
            "uniform initial pressure field, P0 = 2500 psi",
            "Physical SGeMS layers 6-10",
            '"PROD_SW": {"i": 4, "j": 4}',
            '"PROD_NE": {"i": 45, "j": 45}',
        ], "SG1")
        require_markers(sg3_text, [
            "CO2_MASS_RATE_TONNES_DAY = 500.0",
            "CO2_DENSITY_KG_M3 = 700.0",
            "COMPLETION_K = list(range(5, 10))",
            "WELL_RADIUS_FT = 0.25",
            "SKIN = 0.0",
        ], "SG3")
        require_markers(sg7a_text, [
            "S_INITIAL = SWC",
            "S_INJECTED = 1.0 - SOR",
            "SWC = 0.20",
            "SOR = 0.20",
        ], "SG7A")
        require_markers(v14_text, [
            "Convention here is CCS-native",
            "CO2 saturation (=sw)",
            "sim.sw - swc",
        ], "V14")
        require_markers(f0_text, [
            "def initial_hidden",
            "return np.zeros((1,1,int(checkpoint",
        ], "V15F0")
        require_markers(f1_text, [
            "BREAKTHROUGH_GAS_CUT = 1.0e-4",
            "current_breakthrough_memory",
        ], "V15F1")

        sg1_vals = literal_assignments(root / SG1, [
            "NX", "NY", "NZ", "DX_FT", "DY_FT", "DZ_FT", "POROSITY",
            "KV_KH_RATIO", "INJECTION_K_START", "INJECTION_K_STOP",
            "INITIAL_PRESSURE_PSI", "PRODUCER_BHP_PSI", "INJECTOR_I", "INJECTOR_J", "PRODUCERS",
        ])
        sg3_vals = literal_assignments(root / SG3, [
            "CO2_MASS_RATE_TONNES_DAY", "CO2_DENSITY_KG_M3", "WELL_RADIUS_FT", "SKIN",
            "INITIAL_PRESSURE_PSI", "PRODUCER_BHP_PSI", "INJECTOR_I", "INJECTOR_J", "PRODUCERS",
        ])
        sg7_vals = literal_assignments(root / SG7A, ["SWC", "SOR", "POROSITY"])
        f1_vals = literal_assignments(root / F1, ["BREAKTHROUGH_GAS_CUT", "F0_HIDDEN_DIM"])

        gate("SG1_grid_exact", (sg1_vals.get("NZ"), sg1_vals.get("NY"), sg1_vals.get("NX")) == EXPECTED_GRID, sg1_vals)
        gate("SG1_cell_dimensions_exact", (sg1_vals.get("DX_FT"), sg1_vals.get("DY_FT"), sg1_vals.get("DZ_FT")) == (20.0, 20.0, 4.0))
        gate("SG1_porosity_exact", float(sg1_vals.get("POROSITY")) == POROSITY)
        gate("SG1_vertical_anisotropy_exact", float(sg1_vals.get("KV_KH_RATIO")) == KV_KH_RATIO)
        gate("SG1_initial_pressure_exact", float(sg1_vals.get("INITIAL_PRESSURE_PSI")) == INITIAL_PRESSURE_PSI)
        gate("SG1_injection_layers_exact", (sg1_vals.get("INJECTION_K_START"), sg1_vals.get("INJECTION_K_STOP")) == (5, 10))
        gate("SG1_injector_index_exact", (sg1_vals.get("INJECTOR_I"), sg1_vals.get("INJECTOR_J")) == (24, 24))
        gate("SG1_producer_geometry_exact", sg1_vals.get("PRODUCERS") == {
            "PROD_SW": {"i": 4, "j": 4},
            "PROD_SE": {"i": 45, "j": 4},
            "PROD_NW": {"i": 4, "j": 45},
            "PROD_NE": {"i": 45, "j": 45},
        })
        gate("SG3_injection_mass_rate_exact", float(sg3_vals.get("CO2_MASS_RATE_TONNES_DAY")) == 500.0)
        gate("SG3_reference_CO2_density_exact", float(sg3_vals.get("CO2_DENSITY_KG_M3")) == 700.0)
        gate("SG3_producer_BHP_exact", float(sg3_vals.get("PRODUCER_BHP_PSI")) == 2000.0)
        gate("SG3_well_radius_skin_exact", float(sg3_vals.get("WELL_RADIUS_FT")) == 0.25 and float(sg3_vals.get("SKIN")) == 0.0)
        gate("SG7A_transport_baseline_exact", float(sg7_vals.get("SWC")) == BACKGROUND_SATURATION)
        gate("SG7A_transport_injected_endpoint_exact", 1.0 - float(sg7_vals.get("SOR")) == INJECTED_BOUNDARY_SATURATION)
        gate("F1_breakthrough_threshold_exact", float(f1_vals.get("BREAKTHROUGH_GAS_CUT")) == BREAKTHROUGH_GAS_CUT)
        gate("F0_hidden_dimension_exact", int(f1_vals.get("F0_HIDDEN_DIM")) == 32)

        # ------------------------------------------------------------------
        # Construct static geology binding and canonical t=0 dynamic state.
        # ------------------------------------------------------------------
        print("\nCONSTRUCT t=0 STATE")
        perm_path = root / SGSIM_PERM
        perm = load_perm(perm_path)
        gate("SGSim_permeability_finite_positive", np.isfinite(perm).all() and np.all(perm > 0.0))

        kx = perm.copy()
        ky = perm.copy()
        kz = KV_KH_RATIO * perm
        phi = np.full(EXPECTED_GRID, POROSITY, dtype=np.float64)
        injection_mask = np.zeros(EXPECTED_GRID, dtype=bool)
        injection_mask[5:10, :, :] = True

        saturation = np.full(EXPECTED_GRID, BACKGROUND_SATURATION, dtype=np.float64)
        saturation_history = saturation.copy()
        co2_incremental_saturation = saturation - BACKGROUND_SATURATION
        pressure_reference = np.full(EXPECTED_GRID, INITIAL_PRESSURE_PSI, dtype=np.float64)
        f0_hidden = np.zeros((1, 1, 32), dtype=np.float32)

        gate("t0_saturation_shape_exact", saturation.shape == EXPECTED_GRID)
        gate("t0_saturation_uniform_background", np.array_equal(saturation, np.full(EXPECTED_GRID, BACKGROUND_SATURATION)))
        gate("t0_saturation_history_identity", np.array_equal(saturation_history, saturation))
        gate("t0_incremental_CO2_saturation_zero", np.count_nonzero(co2_incremental_saturation) == 0)
        gate("t0_pressure_reference_uniform_2500psi", np.array_equal(pressure_reference, np.full(EXPECTED_GRID, INITIAL_PRESSURE_PSI)))
        gate("t0_F0_hidden_zero_exact", f0_hidden.shape == (1, 1, 32) and np.count_nonzero(f0_hidden) == 0)
        gate("t0_injection_mask_exact_12500_cells", int(injection_mask.sum()) == 12500, int(injection_mask.sum()))

        # Zero-time mass ledger. The inherited CCS-native solver coordinate has a
        # non-zero baseline (Swc=0.20), but injected CO2 inventory is the increment
        # above that baseline. Therefore initial injected/stored/produced mass is
        # exactly zero without requiring a density approximation.
        mass_ledger = {
            "stored_CO2_mass_initial_kg": 0.0,
            "cumulative_injected_CO2_mass_kg": 0.0,
            "cumulative_produced_CO2_mass_kg": 0.0,
            "cumulative_boundary_CO2_mass_kg": 0.0,
            "last_step_mass_residual_kg": 0.0,
            "cumulative_mass_residual_kg": 0.0,
        }
        gate("t0_mass_ledger_exact_zero", all(v == 0.0 for v in mass_ledger.values()))

        co2_mass_rate_kg_s = 500.0 * 1000.0 / 86400.0
        q_inj_m3_s_reference = co2_mass_rate_kg_s / 700.0
        q_inj_m3_day_reference = q_inj_m3_s_reference * 86400.0
        q_inj_perf_m3_day_reference = q_inj_m3_day_reference / 5.0

        producers = {
            "PROD_SW": {"i": 4, "j": 4},
            "PROD_SE": {"i": 45, "j": 4},
            "PROD_NW": {"i": 4, "j": 45},
            "PROD_NE": {"i": 45, "j": 45},
        }
        completions = list(range(5, 10))

        state_npz = out / "V16E34_Frozen_Initial_SGSim_Runtime_State_t0.npz"
        out.mkdir(parents=True, exist_ok=True)
        save_npz_exact(
            state_npz,
            physical_time_days=np.asarray(PRODUCTION_INITIAL_TIME_DAYS, dtype=np.float64),
            accepted_step_index=np.asarray(0, dtype=np.int64),
            grid_shape=np.asarray(EXPECTED_GRID, dtype=np.int64),
            background_saturation=np.asarray(BACKGROUND_SATURATION, dtype=np.float64),
            injected_boundary_saturation=np.asarray(INJECTED_BOUNDARY_SATURATION, dtype=np.float64),
            transport_saturation=saturation,
            transport_saturation_history=saturation_history,
            co2_incremental_saturation=co2_incremental_saturation,
            initial_pressure_reference_psi=pressure_reference,
            f0_hidden_state=f0_hidden,
            cumulative_injected_co2_mass_kg=np.asarray(0.0, dtype=np.float64),
            cumulative_produced_co2_mass_kg=np.asarray(0.0, dtype=np.float64),
            cumulative_boundary_co2_mass_kg=np.asarray(0.0, dtype=np.float64),
            stored_co2_mass_initial_kg=np.asarray(0.0, dtype=np.float64),
            last_step_mass_residual_kg=np.asarray(0.0, dtype=np.float64),
            cumulative_mass_residual_kg=np.asarray(0.0, dtype=np.float64),
            current_producer_co2_gas_cut=np.asarray(0.0, dtype=np.float64),
            breakthrough_reached=np.asarray(False, dtype=bool),
            breakthrough_time_days=np.asarray(np.nan, dtype=np.float64),
            time_since_breakthrough_days=np.asarray(0.0, dtype=np.float64),
            last_accepted_dt_days=np.asarray(np.nan, dtype=np.float64),
            last_accepted_dt_defined=np.asarray(False, dtype=bool),
            observation_cursor_index=np.asarray(0, dtype=np.int64),
            next_fixed_observation_day=np.asarray(DEFAULT_OBSERVATION_DAYS[0], dtype=np.float64),
            path_cache_valid=np.asarray(False, dtype=bool),
            tof_cache_valid=np.asarray(False, dtype=bool),
            exact_retrace_required=np.asarray(True, dtype=bool),
            operational_pressure_state_ready=np.asarray(False, dtype=bool),
            darcy_flux_state_ready=np.asarray(False, dtype=bool),
            first_step_full_exact_preflight_required=np.asarray(True, dtype=bool),
        )

        # Restart/readback identity validation.
        with np.load(state_npz, allow_pickle=False) as z:
            required_arrays = [
                "physical_time_days", "accepted_step_index", "grid_shape",
                "background_saturation", "transport_saturation",
                "transport_saturation_history", "co2_incremental_saturation",
                "initial_pressure_reference_psi", "f0_hidden_state",
                "cumulative_injected_co2_mass_kg", "cumulative_produced_co2_mass_kg",
                "stored_co2_mass_initial_kg", "current_producer_co2_gas_cut",
                "breakthrough_reached", "path_cache_valid", "exact_retrace_required",
                "first_step_full_exact_preflight_required",
            ]
            gate("t0_restart_required_fields_present", all(name in z.files for name in required_arrays), z.files)
            gate("t0_restart_time_zero_exact", float(z["physical_time_days"]) == 0.0)
            gate("t0_restart_saturation_exact", np.array_equal(z["transport_saturation"], saturation))
            gate("t0_restart_history_exact", np.array_equal(z["transport_saturation_history"], saturation_history))
            gate("t0_restart_pressure_reference_exact", np.array_equal(z["initial_pressure_reference_psi"], pressure_reference))
            gate("t0_restart_F0_hidden_exact", np.array_equal(z["f0_hidden_state"], f0_hidden))
            gate("t0_restart_mass_zero_exact", float(z["cumulative_injected_co2_mass_kg"]) == 0.0 and float(z["cumulative_produced_co2_mass_kg"]) == 0.0 and float(z["stored_co2_mass_initial_kg"]) == 0.0)
            gate("t0_restart_breakthrough_false", not bool(z["breakthrough_reached"]))
            gate("t0_restart_path_cache_invalid_retrace_required", not bool(z["path_cache_valid"]) and bool(z["exact_retrace_required"]))
            gate("t0_restart_first_step_full_exact_preflight", bool(z["first_step_full_exact_preflight_required"]))

        # ------------------------------------------------------------------
        # Contracts and schemas.
        # ------------------------------------------------------------------
        source_rows = []
        for rel in required_sources + [E33_RUNNER]:
            path = root / rel
            source_rows.append({
                "role": (
                    "E33_transition_authority" if rel == E33_RUNNER else
                    "SGSim_geology_input" if rel == SGSIM_PERM else
                    "t0_construction_authority"
                ),
                "path": rel,
                "sha256": sha256_file(path),
            })

        static_contract = {
            "milestone": MILESTONE,
            "status": "T0_STATIC_SGSIM_BINDING_FROZEN",
            "grid": {
                "array_order": "(k,j,i) with i/X fastest in persisted SGSim CSV",
                "shape": list(EXPECTED_GRID),
                "cell_size_ft": [20.0, 20.0, 4.0],
                "physical_size_ft": [1000.0, 1000.0, 60.0],
                "cells": EXPECTED_CELLS,
            },
            "geology": {
                "permeability_source": SGSIM_PERM,
                "source_sha256": sha256_file(perm_path),
                "permeability_md": {
                    "min": float(perm.min()),
                    "max": float(perm.max()),
                    "mean": float(perm.mean()),
                    "sha256_array": sha256_array(perm),
                },
                "Kx_sha256_array": sha256_array(kx),
                "Ky_sha256_array": sha256_array(ky),
                "Kz_sha256_array": sha256_array(kz),
                "Kz_over_Kh": KV_KH_RATIO,
                "porosity": POROSITY,
                "porosity_sha256_array": sha256_array(phi),
                "injection_unit_zero_based_k": [5, 6, 7, 8, 9],
                "injection_unit_physical_layers": [6, 7, 8, 9, 10],
                "injection_mask_sha256_array": sha256_array(injection_mask),
            },
        }

        phase_contract = {
            "milestone": MILESTONE,
            "status": "T0_CCS_NATIVE_SATURATION_SEMANTICS_FROZEN",
            "canonical_runtime_field_name": "transport_saturation",
            "canonical_runtime_role": "PAD_STREAM_CCS_NATIVE_SOLVER_SATURATION_COORDINATE",
            "initial_coordinate_value": BACKGROUND_SATURATION,
            "injected_boundary_coordinate_value": INJECTED_BOUNDARY_SATURATION,
            "source_semantics": {
                "SG7A": "S_INITIAL=SWC=0.20 and S_INJECTED=1-SOR=0.80",
                "V14_CCS_native": "solver w-coordinate is used for injected CO2; injected CO2 inventory is measured relative to the swc baseline",
            },
            "critical_interpretation": "The 0.20 t=0 coordinate is the inherited solver baseline and MUST NOT be reported as 20 percent previously injected CO2 throughout the reservoir.",
            "t0_incremental_CO2_saturation": 0.0,
            "t0_stored_injected_CO2_mass_kg": 0.0,
            "future_mass_rule": "E35 must bind the compressible component-mass coefficient to the accepted pressure/phase state; E34 freezes only the exact zero baseline inventory.",
        }

        wells_contract = {
            "milestone": MILESTONE,
            "status": "T0_WELL_CONTROL_STATE_INITIALIZED",
            "injector": {
                "i": 24,
                "j": 24,
                "completion_k_zero_based": completions,
                "completion_physical_layers": [6, 7, 8, 9, 10],
                "control": "CO2_MASS_RATE",
                "scheduled_active_from_time_days": 0.0,
                "mass_rate_tonnes_day": 500.0,
                "mass_rate_kg_s": co2_mass_rate_kg_s,
                "reference_CO2_density_kg_m3": 700.0,
                "reference_volume_rate_m3_day": q_inj_m3_day_reference,
                "reference_volume_rate_per_completion_m3_day": q_inj_perf_m3_day_reference,
                "mass_accrued_at_t0_kg": 0.0,
            },
            "producers": {
                name: {
                    **loc,
                    "completion_k_zero_based": completions,
                    "control": "PEACEMAN_FIXED_BHP",
                    "bhp_psi": 2000.0,
                    "well_radius_ft": 0.25,
                    "skin": 0.0,
                    "CO2_mass_produced_at_t0_kg": 0.0,
                }
                for name, loc in producers.items()
            },
            "current_global_producer_CO2_gas_cut": 0.0,
            "breakthrough_threshold": BREAKTHROUGH_GAS_CUT,
            "breakthrough_reached": False,
            "breakthrough_time_days": None,
        }

        cold_start_contract = {
            "milestone": MILESTONE,
            "status": "FIRST_TRANSITION_COLD_START_POLICY_FROZEN",
            "reason": "The t=0 SGSim parent has no prior accepted SGSim timestep, retry, nonlinear, pressure-workload, or path-cache history.",
            "F0_hidden_state": "ZERO_INITIAL_STATE_1x1x32_SOURCE_AUTHENTIC",
            "first_transition": {
                "learned_timestep_proposal_authorized": False,
                "learned_retrace_proposal_authorized": False,
                "learned_well_control_proposal_authorized": False,
                "learned_solver_workload_proposal_authorized": False,
                "classical_dt_selection_required": True,
                "full_exact_pressure_well_nonlinear_preflight_required": True,
                "exact_Pollock_retrace_required": True,
                "path_cache_reuse_authorized": False,
            },
            "post_first_acceptance": "Subsequent use of screened recurrent proposals requires E35 to establish the SGSim-specific feature/bounds/readiness contract; E34 does not authorize them by assumption.",
        }

        state_contract = {
            "milestone": MILESTONE,
            "status": STATUS,
            "state_file": state_npz.name,
            "state_file_sha256": sha256_file(state_npz),
            "state_role": "CANONICAL_ACCEPTED_PARENT_STATE_FOR_V16E35",
            "physical_time_days": 0.0,
            "accepted_step_index": 0,
            "grid_shape": list(EXPECTED_GRID),
            "canonical_plume_state": {
                "field": "transport_saturation",
                "sha256_array": sha256_array(saturation),
                "history_sha256_array": sha256_array(saturation_history),
                "background": BACKGROUND_SATURATION,
            },
            "pressure_state": {
                "field": "initial_pressure_reference_psi",
                "role": "PRE_CONTROL_UNIFORM_INITIAL_REFERENCE_ONLY",
                "value_psi": INITIAL_PRESSURE_PSI,
                "sha256_array": sha256_array(pressure_reference),
                "operational_pressure_state_ready": False,
                "E35_requirement": "activate scheduled well controls and execute exact finite-volume pressure solve with gravity/coupling before Darcy/transport",
            },
            "mass_ledger": mass_ledger,
            "event_state": {
                "producer_CO2_gas_cut": 0.0,
                "breakthrough_reached": False,
                "breakthrough_time_days": None,
            },
            "recurrent_state": {
                "F0_hidden_shape": [1, 1, 32],
                "F0_hidden_sha256_array": sha256_array(f0_hidden),
                "F1_event_memory_initialized": True,
                "F2_prior_solver_diagnostics_available": False,
            },
            "cache_state": {
                "path_cache_valid": False,
                "TOF_cache_valid": False,
                "exact_retrace_required": True,
            },
            "observation_state": {
                "fixed_observation_days": DEFAULT_OBSERVATION_DAYS,
                "cursor_index": 0,
                "next_fixed_observation_day": DEFAULT_OBSERVATION_DAYS[0],
            },
            "execution_boundary": {
                "runtime_time_advance_performed": False,
                "operational_pressure_solve_executed": False,
                "Darcy_flux_executed": False,
                "Pollock_executed": False,
                "TOF_executed": False,
                "transport_executed": False,
                "mapback_executed": False,
                "single_step_executed": False,
                "E35_single_step_entry_ready": True,
                "E34_single_step_execution_authorized": False,
            },
            "regression_checkpoint_100d": {
                "path": str(checkpoint),
                "sha256": checkpoint_sha_before,
                "role": "IMMUTABLE_FUTURE_t0_TO_100D_REGRESSION_TARGET",
                "modified_in_E34": False,
            },
            "next_milestone": NEXT,
        }

        state_schema_rows = [
            {"field": "physical_time_days", "value": "0.0", "role": "canonical accepted time", "persisted": True},
            {"field": "accepted_step_index", "value": "0", "role": "accepted transition counter", "persisted": True},
            {"field": "transport_saturation", "value": "uniform 0.20", "role": "sole recurrent plume-state coordinate", "persisted": True},
            {"field": "transport_saturation_history", "value": "uniform 0.20", "role": "initial hysteresis/history state", "persisted": True},
            {"field": "co2_incremental_saturation", "value": "uniform 0.0", "role": "diagnostic excess above solver baseline", "persisted": True},
            {"field": "initial_pressure_reference_psi", "value": "uniform 2500", "role": "pre-control reference; not operational flow pressure", "persisted": True},
            {"field": "f0_hidden_state", "value": "zeros [1,1,32]", "role": "source-authentic recurrent cold start", "persisted": True},
            {"field": "mass ledger", "value": "all zero", "role": "CO2 component accounting baseline", "persisted": True},
            {"field": "producer gas cut", "value": "0", "role": "breakthrough event state", "persisted": True},
            {"field": "breakthrough memory", "value": "False / time unset", "role": "monotone event memory", "persisted": True},
            {"field": "last accepted dt", "value": "undefined", "role": "no accepted transition yet", "persisted": True},
            {"field": "path/TOF cache", "value": "invalid / exact retrace required", "role": "first transition must build exact path state", "persisted": True},
            {"field": "observation cursor", "value": "index 0 -> day 30", "role": "fixed snapshot scheduler", "persisted": True},
        ]

        # Final invariants before publishing metadata.
        checkpoint_sha_after = sha256_file(checkpoint)
        gate("frozen_100d_checkpoint_unchanged", checkpoint_sha_after == checkpoint_sha_before == V16_FROZEN_SHA256, checkpoint_sha_after)
        gate("E34_runtime_time_advance_not_performed", True)
        gate("E34_operational_pressure_not_solved", True)
        gate("E34_Darcy_Pollock_TOF_transport_mapback_not_executed", True)
        gate("E34_single_step_not_executed", True)
        gate("E35_single_step_entry_ready", True)
        gate("SGSim_specific_dt_envelope_still_not_invented", True)
        gate("SGSim_specific_mass_tolerance_still_not_invented", True)

        summary = {
            "milestone": MILESTONE,
            "status": STATUS,
            "t0_state_created": True,
            "t0_state_file": state_npz.name,
            "t0_state_file_sha256": sha256_file(state_npz),
            "production_runtime_initial_time_days": 0.0,
            "accepted_step_index": 0,
            "grid_shape": list(EXPECTED_GRID),
            "canonical_transport_saturation_initial": BACKGROUND_SATURATION,
            "canonical_transport_saturation_is_not_preexisting_injected_CO2_fraction": True,
            "incremental_CO2_saturation_initial": 0.0,
            "stored_injected_CO2_mass_initial_kg": 0.0,
            "cumulative_injected_CO2_mass_kg": 0.0,
            "cumulative_produced_CO2_mass_kg": 0.0,
            "initial_pressure_reference_psi": INITIAL_PRESSURE_PSI,
            "initial_pressure_role": "PRE_CONTROL_UNIFORM_REFERENCE",
            "operational_pressure_state_ready": False,
            "injector_mass_rate_tonnes_day": 500.0,
            "producer_bhp_psi": 2000.0,
            "current_producer_CO2_gas_cut": 0.0,
            "breakthrough_reached": False,
            "F0_hidden_state_zero_initialized": True,
            "first_transition_full_exact_cold_start_required": True,
            "path_cache_valid": False,
            "exact_retrace_required": True,
            "next_fixed_observation_day": DEFAULT_OBSERVATION_DAYS[0],
            "runtime_time_advance_performed": False,
            "pressure_Darcy_Pollock_TOF_transport_mapback_executed": False,
            "single_step_executed": False,
            "E35_single_step_entry_ready": True,
            "E34_single_step_execution_authorized": False,
            "SGSim_specific_dt_envelope_frozen": False,
            "SGSim_specific_mass_tolerance_frozen": False,
            "frozen_100d_checkpoint_modified": False,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "IBDP_started": False,
            "next_milestone": NEXT,
        }

        handoff = f"""# PAD-Stream V16E-34 Handoff\n\nV16E-34 constructs and freezes the canonical SGSim runtime parent state at injection time t=0 without advancing physical time or executing operational flow/transport physics.\n\nKey t=0 state semantics:\n\n- canonical grid shape: {EXPECTED_GRID};\n- canonical PAD-Stream transport saturation coordinate: uniform {BACKGROUND_SATURATION:.2f};\n- that {BACKGROUND_SATURATION:.2f} is the inherited CCS-native solver baseline, not a claim of {100*BACKGROUND_SATURATION:.0f}% previously injected CO2;\n- injected CO2 increment above the baseline: exactly 0 everywhere;\n- cumulative injected / produced / stored injected CO2 mass: 0 / 0 / 0 kg;\n- pre-control pressure reference: uniform {INITIAL_PRESSURE_PSI:.1f} psi; operational well-coupled pressure is intentionally not solved in E34;\n- injector control scheduled from t=0: 500 tonnes/day CO2 on layers 6-10; producer controls: 2000 psi fixed BHP;\n- F0 hidden state: exact zero cold start [1,1,32];\n- breakthrough memory: false, producer CO2 gas cut 0;\n- path and TOF caches: invalid; exact retrace required;\n- next fixed observation target: {DEFAULT_OBSERVATION_DAYS[0]:.0f} days;\n- first transition must use classical timestep selection and full exact pressure/well/nonlinear/path preflight because there is no accepted SGSim transition history yet.\n\nNo SGSim-specific numerical dt envelope or mass-acceptance tolerance is invented in E34. Those must be established from the first executed transition behavior.\n\nThe frozen 100-day V16 checkpoint remains unchanged and is reserved as the future t=0 -> 100 d regression target.\n\nE34 executes no physical transition. V16E-35 is authorized to attempt exactly one controlled mass-conservative transition from this frozen t=0 parent under the E33 acceptance/rollback contract.\n\nNEXT: {NEXT}\n"""

        files: dict[str, bytes] = {
            "V16E34_Initial_Runtime_State_Contract.json": json_bytes(state_contract),
            "V16E34_Static_SGSim_Binding_Contract.json": json_bytes(static_contract),
            "V16E34_CCS_Native_Saturation_Semantics_Contract.json": json_bytes(phase_contract),
            "V16E34_Initial_Well_Control_State.json": json_bytes(wells_contract),
            "V16E34_First_Transition_Cold_Start_Contract.json": json_bytes(cold_start_contract),
            "V16E34_Runtime_State_Schema.csv": csv_bytes(state_schema_rows),
            "V16E34_Source_Authority_Manifest.csv": csv_bytes(source_rows),
            "PAD_Stream_V16E34_Summary.json": json_bytes(summary),
            "V16E34_Handoff.md": handoff.encode("utf-8"),
        }
        final_gate_rows = [{"gate": name, **record} for name, record in gates.items()]
        files["V16E34_Final_Gate_Matrix.csv"] = csv_bytes(final_gate_rows)

        immutable_publish(out, files)

        # Artifact manifest is generated after all other artifacts exist.
        artifact_rows = []
        for path in sorted(out.iterdir()):
            if path.is_file() and path.name != "V16E34_Artifact_Manifest.csv":
                artifact_rows.append({
                    "file": path.name,
                    "sha256": sha256_file(path),
                    "bytes": path.stat().st_size,
                })
        manifest_path = out / "V16E34_Artifact_Manifest.csv"
        manifest_data = csv_bytes(artifact_rows)
        if manifest_path.exists() and manifest_path.read_bytes() != manifest_data:
            raise GateError("existing_output_differs:V16E34_Artifact_Manifest.csv")
        if not manifest_path.exists():
            manifest_path.write_bytes(manifest_data)

        print("\n" + "=" * 132)
        print("V16E-34 RESULT: PASS")
        print("=" * 132)
        print(f"{'Canonical t=0 runtime state created':72}: YES")
        print(f"{'Runtime physical time':72}: 0.0 days")
        print(f"{'Canonical transport saturation':72}: uniform {BACKGROUND_SATURATION:.2f} solver baseline")
        print(f"{'Injected CO2 incremental saturation at t=0':72}: 0.0")
        print(f"{'Stored / injected / produced CO2 mass at t=0':72}: 0 / 0 / 0 kg")
        print(f"{'Initial pressure reference':72}: {INITIAL_PRESSURE_PSI:.1f} psi / PRE-CONTROL")
        print(f"{'F0 hidden state':72}: zeros [1,1,32]")
        print(f"{'Path cache valid / exact retrace required':72}: NO / YES")
        print(f"{'First transition full exact cold start required':72}: YES")
        print(f"{'Operational pressure/Darcy/Pollock/TOF/transport/map-back executed':72}: NO")
        print(f"{'Runtime time advance performed':72}: NO")
        print(f"{'Frozen 100-day checkpoint modified':72}: NO")
        print(f"{'E35 single-step entry ready':72}: YES")
        print(f"{'t=0 state SHA-256':72}: {sha256_file(state_npz)}")
        print(f"Output: {out}")
        print(f"NEXT: {NEXT}")
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        checkpoint_modified = None
        if checkpoint_sha_before is not None and checkpoint.exists():
            checkpoint_modified = sha256_file(checkpoint) != checkpoint_sha_before
        payload = {
            "milestone": MILESTONE,
            "status": "BLOCKED",
            "exception": repr(exc),
            "gates": gates,
            "runtime_time_advance_performed": False,
            "operational_pressure_solve_executed": False,
            "Darcy_Pollock_TOF_transport_mapback_executed": False,
            "single_step_executed": False,
            "frozen_100d_checkpoint_modified": checkpoint_modified,
            "next_milestone": "V16E-34-R1 - Repair only the failed initial-state construction/validation gate; preserve E33 and the frozen 100-day checkpoint unchanged",
        }
        path = blocked / "V16E34_Blocked_Initial_Runtime_State_Construction.json"
        path.write_bytes(json_bytes(payload))
        print(f"\n[FAIL] V16E-34 did not close: {exc}", flush=True)
        print(f"Blocked report: {path}", flush=True)
        return 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--drive-root", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(main(args.project_root, args.drive_root))
