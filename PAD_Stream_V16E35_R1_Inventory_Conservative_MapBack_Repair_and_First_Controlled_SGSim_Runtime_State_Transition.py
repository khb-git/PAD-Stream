from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from typing import Any, Iterable

import numpy as np


MILESTONE = "V16E-35-R1"
STATUS = "FIRST_CONTROLLED_SGSIM_RUNTIME_STATE_TRANSITION_ACCEPTED_R1"
NEXT = "V16E-36 - Short Adaptive SGSim Rollout / Early Plume Snapshot Validation"

EXPECTED_GRID = (15, 50, 50)  # (k, j, i)
EXPECTED_CELLS = 37500
EXPECTED_STREAMLINES = 1078
EXPECTED_NXI = 201
BACKGROUND_SATURATION = 0.20
INJECTED_BOUNDARY_SATURATION = 0.80
MAX_INCREMENTAL_CO2_SATURATION = INJECTED_BOUNDARY_SATURATION - BACKGROUND_SATURATION
BREAKTHROUGH_GAS_CUT = 1.0e-4
DEFAULT_OBSERVATION_DAYS = [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0]

# E34 accepted parent.
E34_REL = Path(
    "provenance/hybrid_dp/"
    "V16E34_INITIAL_INJECTION_TIME_SGSIM_RUNTIME_STATE_CONSTRUCTION_VALIDATION"
)
E34_SUMMARY = "PAD_Stream_V16E34_Summary.json"
E34_STATE = "V16E34_Frozen_Initial_SGSim_Runtime_State_t0.npz"
E34_EXPECTED_STATUS = "INITIAL_INJECTION_TIME_SGSIM_RUNTIME_STATE_FROZEN"

# Failed E35 attempt retained as provenance. E35-R1 is a repair milestone, not
# an overwrite of the committed/failed V16E-35 execution.
E35_FAILED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E35_BLOCKED_FIRST_CONTROLLED_SGSIM_RUNTIME_STATE_TRANSITION"
)
E35_FAILED_REPORT = "V16E35_Blocked_First_Controlled_Transition.json"
E35_FAILED_EXCEPTION = (
    "GateError('bounded_projection_lambda_within_frozen_SG7D_flexibility_scale')"
)
E35_ORIGINAL_RUNNER = (
    "PAD_Stream_V16E35_First_Controlled_SGSim_Runtime_State_Transition_and_"
    "Mass_Conservative_Single_Step_Execution.py"
)
E35_ORIGINAL_RUNNER_SHA256 = (
    "175d5eb69422907c4de7d7df4965ecf2e98c0f4d06021b93e834a2c4045d710f"
)

# Immutable 100-day regression target.
V16_FROZEN_REL = Path(
    "provenance/hybrid_dp/V16E18_R1_FROZEN_SGSIM_100D_FULL_GRID_CANDIDATE/"
    "frozen_full_grid/V16E18_R1_Frozen_SGSim_100Day_Full_Grid_Candidate.npz"
)
V16_FROZEN_SHA256 = "d422dc1e56281c1baf0ae007c62ce4bd69677a232bd1448a5bd79d3177eafaea"

# Source-authentic physics authorities.
SGSIM_PERM = "SGSIM_50x50x15_PERM_MD.csv"
SG2 = "PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"
SG3 = "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG4 = "PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"
SG5 = "PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py"
SG6 = "PAD_Stream_V15SG6_TOF_Transport_Coordinates.py"
SG7A = "PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
V14 = "PAD_Stream_CCUS_Physics_Development_v14_Complete_Validation.py"

OUT_REL = Path(
    "provenance/hybrid_dp/"
    "V16E35_R1_FIRST_CONTROLLED_SGSIM_RUNTIME_STATE_TRANSITION_INVENTORY_MAPBACK_REPAIR"
)
BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E35_R1_BLOCKED_FIRST_CONTROLLED_SGSIM_RUNTIME_STATE_TRANSITION_INVENTORY_MAPBACK_REPAIR"
)

# Explicit-CCUS density/capillary coefficients from the Version-14 CCUS-native
# phase convention. The EOS reference pressure is anchored dynamically to the
# accepted injector gas-phase pressure so rho=700 kg/m3 at the injection source.
CO2_RHO_REF_KG_M3 = 700.0
CO2_COMPRESSIBILITY_1_PA = 1.0e-8
CAPILLARY_ENTRY_PRESSURE_PA = 2.0e6
CAPILLARY_LAMBDA = 2.0
IRREDUCIBLE_BRINE_SATURATION = 0.20

PSI_TO_PA = 6894.757293168
FT_TO_M = 0.3048
DAY_TO_S = 86400.0
INJECTOR_MASS_RATE_KG_DAY = 500.0 * 1000.0
INJECTOR_I = 24
INJECTOR_J = 24
COMPLETION_K = list(range(5, 10))
PRODUCERS = {
    "PROD_SW": {"i": 4, "j": 4},
    "PROD_SE": {"i": 45, "j": 4},
    "PROD_NW": {"i": 4, "j": 45},
    "PROD_NE": {"i": 45, "j": 45},
}


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sha256_array(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


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


def deterministic_npz_bytes(arrays: dict[str, Any]) -> bytes:
    outer = io.BytesIO()
    with zipfile.ZipFile(outer, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for key in sorted(arrays):
            b = io.BytesIO()
            np.save(b, np.asarray(arrays[key]), allow_pickle=False)
            info = zipfile.ZipInfo(f"{key}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, b.getvalue())
    return outer.getvalue()


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        path = out / name
        if path.exists():
            if path.read_bytes() != data:
                raise GateError(f"existing_output_differs:{name}")
        else:
            path.write_bytes(data)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load_module:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run_source_stage(path: Path, cwd: Path, label: str) -> None:
    env = os.environ.copy()
    env.setdefault("MPLBACKEND", "Agg")
    proc = subprocess.run(
        [sys.executable, str(path)],
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if proc.returncode != 0:
        print(proc.stdout, flush=True)
        raise GateError(f"{label}_source_execution_failed")
    tail = "\n".join(proc.stdout.splitlines()[-10:])
    print(f"\n[{label}] source-authentic execution PASS")
    if tail:
        print(tail, flush=True)


def capillary_pressure_from_incremental_sg(sg: np.ndarray | float) -> np.ndarray:
    sg = np.asarray(sg, dtype=np.float64)
    sw = 1.0 - sg
    span = 1.0 - IRREDUCIBLE_BRINE_SATURATION
    se_w = np.clip((sw - IRREDUCIBLE_BRINE_SATURATION) / span, 1.0e-4, 1.0)
    return CAPILLARY_ENTRY_PRESSURE_PA * se_w ** (-1.0 / CAPILLARY_LAMBDA)


def gas_density_from_state(
    transport_saturation: np.ndarray,
    pressure_psi: np.ndarray,
    p_ref_pa: float,
) -> np.ndarray:
    sg = np.clip(
        np.asarray(transport_saturation, dtype=np.float64) - BACKGROUND_SATURATION,
        0.0,
        MAX_INCREMENTAL_CO2_SATURATION,
    )
    pc = capillary_pressure_from_incremental_sg(sg)
    p_g = np.asarray(pressure_psi, dtype=np.float64) * PSI_TO_PA + pc
    exponent = np.clip(
        CO2_COMPRESSIBILITY_1_PA * (p_g - float(p_ref_pa)),
        -50.0,
        50.0,
    )
    return CO2_RHO_REF_KG_M3 * np.exp(exponent)


def stored_co2_mass_kg(
    transport_saturation: np.ndarray,
    pressure_psi: np.ndarray,
    p_ref_pa: float,
    cell_pore_volume_m3: float,
) -> float:
    sg = np.clip(
        np.asarray(transport_saturation, dtype=np.float64) - BACKGROUND_SATURATION,
        0.0,
        MAX_INCREMENTAL_CO2_SATURATION,
    )
    rho = gas_density_from_state(transport_saturation, pressure_psi, p_ref_pa)
    return float(np.sum(float(cell_pore_volume_m3) * rho * sg))


def conservative_inventory_mapback_and_source_closure(
    segment_saturation: np.ndarray,
    operator: dict[str, np.ndarray],
    pressure_psi: np.ndarray,
    target_mass_kg: float,
    cell_pore_volume_m3: float,
    p_ref_pa: float,
) -> dict[str, Any]:
    """
    Convert the exact SG7D subsegment inventory directly into Cartesian
    cell saturation increments.

    Runtime conservation repair relative to the failed E35 attempt:

      delta_V_CO2,c =
          sum_{subsegments in c} PV_sub * (S_sub - S0)

      S_path,c =
          S0 + delta_V_CO2,c / PV_cell

    This avoids promoting a streamline-supported average saturation to an
    entire Cartesian cell before inventory closure.

    The SG7A inlet Dirichlet node is handled upstream as zero-volume. Any
    finite first-step mass not represented by downstream path inventory is
    source-local and may be placed only in the five injector completion
    cells. If the path-deposited mass already exceeds the available injected
    component mass by more than roundoff, the transition is rejected. There
    is no global plume rescaling and no unsupported-cell correction.
    """
    segment_saturation = np.asarray(segment_saturation, dtype=np.float64)
    flat_cell = np.asarray(operator["flat_cell"], dtype=np.int64)
    subsegment_pv = np.asarray(operator["pv_m3"], dtype=np.float64)

    if segment_saturation.shape != subsegment_pv.shape:
        raise GateError(
            f"segment_inventory_shape_mismatch:"
            f"{segment_saturation.shape}:{subsegment_pv.shape}"
        )

    segment_increment = np.clip(
        segment_saturation - BACKGROUND_SATURATION,
        0.0,
        MAX_INCREMENTAL_CO2_SATURATION,
    )

    ncell = int(np.prod(EXPECTED_GRID))
    deposited_increment_volume_m3 = np.bincount(
        flat_cell,
        weights=subsegment_pv * segment_increment,
        minlength=ncell,
    ).reshape(EXPECTED_GRID)

    path_supported = deposited_increment_volume_m3 > 0.0
    path_saturation = (
        BACKGROUND_SATURATION
        + deposited_increment_volume_m3 / float(cell_pore_volume_m3)
    )

    if np.any(~np.isfinite(path_saturation)):
        raise GateError("inventory_mapback_nonfinite_path_saturation")

    max_path_saturation = float(np.max(path_saturation))
    if max_path_saturation > INJECTED_BOUNDARY_SATURATION + 1.0e-10:
        raise GateError(
            "inventory_mapback_local_cell_capacity_exceeded:"
            f"{max_path_saturation}"
        )

    path_saturation = np.clip(
        path_saturation,
        BACKGROUND_SATURATION,
        INJECTED_BOUNDARY_SATURATION,
    )

    path_mass_kg = stored_co2_mass_kg(
        path_saturation,
        pressure_psi,
        p_ref_pa,
        cell_pore_volume_m3,
    )

    roundoff_mass_kg = max(
        1.0e-6,
        1.0e-12 * max(abs(target_mass_kg), 1.0),
    )
    excess_path_mass_kg = path_mass_kg - float(target_mass_kg)
    if excess_path_mass_kg > roundoff_mass_kg:
        raise GateError(
            "path_deposited_mass_exceeds_available_component_mass:"
            f"{path_mass_kg}:{target_mass_kg}:{excess_path_mass_kg}"
        )

    injector_mask = np.zeros(EXPECTED_GRID, dtype=bool)
    for k in COMPLETION_K:
        injector_mask[k, INJECTOR_J, INJECTOR_I] = True

    base = path_saturation.copy()

    def source_field(delta: float) -> np.ndarray:
        out = base.copy()
        out[injector_mask] = np.clip(
            out[injector_mask] + float(delta),
            BACKGROUND_SATURATION,
            INJECTED_BOUNDARY_SATURATION,
        )
        return out

    def source_mass(delta: float) -> float:
        return stored_co2_mass_kg(
            source_field(delta),
            pressure_psi,
            p_ref_pa,
            cell_pore_volume_m3,
        )

    missing_mass_kg = max(float(target_mass_kg) - path_mass_kg, 0.0)

    if missing_mass_kg <= roundoff_mass_kg:
        source_delta = 0.0
        corrected = base
    else:
        maximum_source_mass = source_mass(MAX_INCREMENTAL_CO2_SATURATION)
        if maximum_source_mass < float(target_mass_kg) - roundoff_mass_kg:
            raise GateError(
                "injector_source_local_mass_capacity_insufficient:"
                f"{maximum_source_mass}:{target_mass_kg}"
            )

        lower = 0.0
        upper = MAX_INCREMENTAL_CO2_SATURATION
        for _ in range(180):
            mid = 0.5 * (lower + upper)
            if source_mass(mid) < float(target_mass_kg):
                lower = mid
            else:
                upper = mid
        source_delta = 0.5 * (lower + upper)
        corrected = source_field(source_delta)

    final_mass_kg = stored_co2_mass_kg(
        corrected,
        pressure_psi,
        p_ref_pa,
        cell_pore_volume_m3,
    )
    residual_kg = final_mass_kg - float(target_mass_kg)

    active_mask = path_supported | injector_mask
    if np.any(
        np.abs(corrected[~active_mask] - BACKGROUND_SATURATION) > 1.0e-14
    ):
        raise GateError("inventory_mapback_modified_inactive_cells")

    source_correction = corrected - base
    return {
        "corrected": corrected,
        "active_mask": active_mask,
        "path_supported_mask": path_supported,
        "injector_mask": injector_mask,
        "deposited_increment_volume_m3": deposited_increment_volume_m3,
        "path_increment_volume_m3": float(np.sum(deposited_increment_volume_m3)),
        "path_mass_kg": float(path_mass_kg),
        "target_mass_kg": float(target_mass_kg),
        "missing_source_mass_before_closure_kg": float(missing_mass_kg),
        "source_delta_saturation": float(source_delta),
        "source_max_abs_correction": float(
            np.max(np.abs(source_correction[injector_mask]))
        ),
        "final_mass_kg": float(final_mass_kg),
        "residual_kg": float(residual_kg),
        "corrected_cells": int(
            np.sum(np.abs(corrected - base) > 1.0e-14)
        ),
        "path_supported_cells": int(np.sum(path_supported)),
        "active_cells": int(np.sum(active_mask)),
        "roundoff_mass_kg": float(roundoff_mass_kg),
    }


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

    parent_state_path = drive / E34_REL / E34_STATE
    frozen_100d = drive / V16_FROZEN_REL
    parent_sha_before: str | None = None
    frozen_100d_sha_before: str | None = None

    print("\n" + "=" * 136)
    print("PAD-Stream V16E-35 First Controlled SGSim Runtime State Transition / Mass-Conservative Single-Step Execution")
    print("=" * 136)
    print("EXECUTE EXACTLY ONE CONTROLLED TRANSITION FROM THE FROZEN E34 t=0 PARENT.")
    print("COLD START: NO LEARNED TIMESTEP OR RETRACE PROPOSAL IS USED.")
    print("EXACT SG2/SG3/SG4/SG5/SG6 FLOW/PATH AUTHORITIES ARE RE-EXECUTED IN AN ISOLATED TEMPORARY WORKSPACE.")
    print("THE FIRST GLOBAL DT IS DERIVED FROM THE SG7A DIMENSIONLESS CFL SCALE AND THE FASTEST EXACT SGSim TOF.")
    print("THE CHILD STATE IS COMMITTED ONLY AFTER PRESSURE/FLOW/PATH/TOF/TRANSPORT/MAP-BACK/MASS GATES PASS.")

    try:
        # ------------------------------------------------------------------
        # Parent authority.
        # ------------------------------------------------------------------
        print("\nV16E-34 ACCEPTED PARENT")
        e34_summary_path = drive / E34_REL / E34_SUMMARY
        gate("E34_summary_exists", e34_summary_path.is_file(), e34_summary_path)
        gate("E34_parent_state_exists", parent_state_path.is_file(), parent_state_path)
        e34_summary = load_json(e34_summary_path)
        gate("E34_status_frozen", e34_summary.get("status") == E34_EXPECTED_STATUS)
        gate("E34_E35_entry_ready", e34_summary.get("E35_single_step_entry_ready") is True)
        gate("E34_parent_time_zero", float(e34_summary.get("production_runtime_initial_time_days")) == 0.0)
        gate("E34_parent_step_not_executed", e34_summary.get("single_step_executed") is False)

        parent_sha_before = sha256_file(parent_state_path)
        gate(
            "E34_parent_state_SHA_matches_summary",
            parent_sha_before == e34_summary.get("t0_state_file_sha256"),
            parent_sha_before,
        )

        with np.load(parent_state_path, allow_pickle=False) as p:
            parent = {name: p[name].copy() for name in p.files}
        gate("parent_restart_time_zero", float(parent["physical_time_days"]) == 0.0)
        gate("parent_restart_step_index_zero", int(parent["accepted_step_index"]) == 0)
        gate("parent_transport_shape_exact", tuple(parent["transport_saturation"].shape) == EXPECTED_GRID)
        gate("parent_transport_uniform_background", np.array_equal(parent["transport_saturation"], np.full(EXPECTED_GRID, BACKGROUND_SATURATION)))
        gate("parent_first_exact_preflight_required", bool(parent["first_step_full_exact_preflight_required"]))
        gate("parent_exact_retrace_required", bool(parent["exact_retrace_required"]))
        gate("parent_operational_pressure_not_ready", not bool(parent["operational_pressure_state_ready"]))

        e35_failed_report_path = drive / E35_FAILED_REL / E35_FAILED_REPORT
        gate("E35_failed_report_exists", e35_failed_report_path.is_file(), e35_failed_report_path)
        e35_failed_report = load_json(e35_failed_report_path)
        gate(
            "E35_failed_status_exact",
            e35_failed_report.get("status")
            == "FIRST_CONTROLLED_SGSIM_RUNTIME_STATE_TRANSITION_BLOCKED",
            e35_failed_report.get("status"),
        )
        gate(
            "E35_failed_reason_exact",
            e35_failed_report.get("exception") == E35_FAILED_EXCEPTION,
            e35_failed_report.get("exception"),
        )
        gate(
            "E35_failed_child_not_published",
            e35_failed_report.get("accepted_child_published") is False,
        )
        gate(
            "E35_failed_time_not_committed",
            e35_failed_report.get("runtime_time_advance_committed") is False,
        )
        gate(
            "E35_failed_parent_not_mutated",
            e35_failed_report.get("parent_mutated") is False,
        )
        e35_original_runner_path = root / E35_ORIGINAL_RUNNER
        gate("E35_original_runner_exists", e35_original_runner_path.is_file(), e35_original_runner_path)
        gate(
            "E35_original_runner_SHA_exact",
            sha256_file(e35_original_runner_path) == E35_ORIGINAL_RUNNER_SHA256,
            sha256_file(e35_original_runner_path),
        )

        gate("frozen_100d_exists", frozen_100d.is_file(), frozen_100d)
        frozen_100d_sha_before = sha256_file(frozen_100d)
        gate("frozen_100d_SHA_exact_before", frozen_100d_sha_before == V16_FROZEN_SHA256, frozen_100d_sha_before)

        # ------------------------------------------------------------------
        # Source authority.
        # ------------------------------------------------------------------
        print("\nSOURCE AUTHORITIES")
        required = [SGSIM_PERM, SG2, SG3, SG4, SG5, SG6, SG7A, SG7D, V14]
        for rel in required:
            gate(f"source_exists_{Path(rel).name}", (root / rel).is_file(), root / rel)

        require_markers((root / SG3).read_text(encoding="utf-8"), [
            "CO2_MASS_RATE_TONNES_DAY = 500.0",
            "CO2_DENSITY_KG_M3 = 700.0",
            "PRODUCER_BHP_PSI = 2000.0",
            "COMPLETION_K = list(range(5, 10))",
            "def assemble_pressure_system",
        ], "SG3")
        require_markers((root / SG4).read_text(encoding="utf-8"), [
            "def compute_face_fluxes",
            "def validate_conservation",
        ], "SG4")
        require_markers((root / SG5).read_text(encoding="utf-8"), [
            "FACE_SUBDIVISIONS = 7",
            "def trace_streamlines",
            "def validate_streamlines",
        ], "SG5")
        require_markers((root / SG6).read_text(encoding="utf-8"), [
            "N_XI = 201",
            "def build_transport_database",
            "def validate_transport",
        ], "SG6")
        require_markers((root / SG7A).read_text(encoding="utf-8"), [
            "S_INITIAL = SWC",
            "S_INJECTED = 1.0 - SOR",
            "CFL = 0.40",
            "def build_master_solution",
            "def interpolate_master_profile",
        ], "SG7A")
        require_markers((root / SG7D).read_text(encoding="utf-8"), [
            "def build_subsegment_operator",
            "def build_coverage",
            "def raw_mapback",
            "S_INITIAL = 0.20",
            "S_MAX = 0.80",
        ], "SG7D")
        require_markers((root / V14).read_text(encoding="utf-8"), [
            "class CCUSFluid",
            "c_g: float = 1.0e-8",
            "rho_g_ref: float = 700.0",
            "def ccus_gas_density_from_phase_pressure",
        ], "V14")
        gate("source_semantic_markers_complete", True)

        # ------------------------------------------------------------------
        # Isolated source-authentic SG2->SG6 execution.
        # ------------------------------------------------------------------
        print("\nEXACT FLOW / PATH / TOF COLD-START EXECUTION")
        with tempfile.TemporaryDirectory(prefix="PAD_Stream_V16E35_R1_") as td:
            tmp = Path(td)
            for rel in [SGSIM_PERM, SG2, SG3, SG4, SG5, SG6, SG7A, SG7D]:
                shutil.copy2(root / rel, tmp / Path(rel).name)

            for label, script in [
                ("V15-SG2", SG2),
                ("V15-SG3", SG3),
                ("V15-SG4", SG4),
                ("V15-SG5", SG5),
                ("V15-SG6", SG6),
            ]:
                run_source_stage(tmp / Path(script).name, tmp, label)

            pressure_path = tmp / "output/V15_SG3/PRESSURE_PSI.npy"
            qx_path = tmp / "output/V15_SG4/QX_M3_S.npy"
            qy_path = tmp / "output/V15_SG4/QY_M3_S.npy"
            qz_path = tmp / "output/V15_SG4/QZ_M3_S.npy"
            sg3_summary_path = tmp / "output/V15_SG3/PAD_Stream_V15SG3_Summary.json"
            sg4_summary_path = tmp / "output/V15_SG4/PAD_Stream_V15SG4_Summary.json"
            sg6_path = tmp / "output/V15_SG6/STREAMLINE_TRANSPORT_COORDINATES.npz"

            for path in [pressure_path, qx_path, qy_path, qz_path, sg3_summary_path, sg4_summary_path, sg6_path]:
                gate(f"cold_start_output_exists_{path.name}", path.is_file(), path.name)

            pressure_psi = np.load(pressure_path).astype(np.float64)
            qx = np.load(qx_path).astype(np.float64)
            qy = np.load(qy_path).astype(np.float64)
            qz = np.load(qz_path).astype(np.float64)
            sg3_summary = load_json(sg3_summary_path)
            sg4_summary = load_json(sg4_summary_path)

            gate("operational_pressure_shape_exact", pressure_psi.shape == EXPECTED_GRID, pressure_psi.shape)
            gate("operational_pressure_finite", np.all(np.isfinite(pressure_psi)))
            gate("SG3_status_pass", sg3_summary.get("status") == "PASS")
            gate("SG3_pressure_linear_residual_pass", float(sg3_summary["injector_pressure"]["relative_linear_residual"]) < 1.0e-8, sg3_summary["injector_pressure"]["relative_linear_residual"])
            gate("SG3_global_volume_balance_pass", float(sg3_summary["injector_pressure"]["mass_balance_error_fraction"]) < 1.0e-3, sg3_summary["injector_pressure"]["mass_balance_error_fraction"])
            gate("SG4_status_pass", sg4_summary.get("status") == "PASS")
            conservation = sg4_summary.get("conservation", {})
            if conservation:
                gate("SG4_local_flux_conservation_pass", float(conservation.get("local_relative_l2_error", 1.0)) < 1.0e-8, conservation.get("local_relative_l2_error"))
                gate("SG4_global_flux_conservation_pass", float(conservation.get("global_relative_mismatch", 1.0)) < 1.0e-8, conservation.get("global_relative_mismatch"))

            with np.load(sg6_path, allow_pickle=False) as z:
                sg6 = {name: z[name].copy() for name in z.files}

            required_sg6 = ["xyz_m", "tau_s", "xi", "path_length_m", "weights_m3_s", "tau_end_s", "producer", "streamline_id"]
            gate("SG6_required_arrays_present", all(k in sg6 for k in required_sg6), list(sg6))
            gate("SG6_streamline_count_exact", len(sg6["tau_end_s"]) == EXPECTED_STREAMLINES, len(sg6["tau_end_s"]))
            gate("SG6_xi_count_exact", len(sg6["xi"]) == EXPECTED_NXI, len(sg6["xi"]))
            gate("SG6_all_terminal_TOF_positive", np.all(sg6["tau_end_s"] > 0.0))
            gate("SG6_weights_positive", np.all(sg6["weights_m3_s"] > 0.0))
            observed_producers = sorted(map(str, np.unique(sg6["producer"])))
            gate("SG6_all_four_producers_present", set(observed_producers) == set(PRODUCERS), observed_producers)

            qinj_m3_day_from_paths = float(np.sum(sg6["weights_m3_s"]) * DAY_TO_S)
            expected_qinj_m3_day = INJECTOR_MASS_RATE_KG_DAY / CO2_RHO_REF_KG_M3
            gate(
                "streamline_weight_total_matches_injection",
                abs(qinj_m3_day_from_paths - expected_qinj_m3_day) / expected_qinj_m3_day < 1.0e-10,
                f"{qinj_m3_day_from_paths:.12f} vs {expected_qinj_m3_day:.12f}",
            )

            # --------------------------------------------------------------
            # First runtime dt from exact SGSim TOF and SG7A dimensionless CFL.
            # --------------------------------------------------------------
            sg7a = load_module(tmp / Path(SG7A).name, "pad_stream_v16e35_sg7a")
            xi = np.asarray(sg6["xi"], dtype=np.float64)
            dxi = float(xi[1] - xi[0])
            sat_scan = np.linspace(sg7a.S_INITIAL, sg7a.S_INJECTED, 4001)
            max_df = float(np.max(np.abs(sg7a.df_dS(sat_scan))))
            xi_face = np.linspace(0.0, 1.0, len(xi) + 1)
            max_wave_speed = float(np.max(sg7a.u_dimensionless(xi_face)) * max_df)
            dtD_cfl = float(sg7a.CFL * dxi / (max_wave_speed + sg7a.EPS))
            tau_end_days = np.asarray(sg6["tau_end_s"], dtype=np.float64) / DAY_TO_S
            fastest_tau_days = float(np.min(tau_end_days))
            dt_days = float(dtD_cfl * fastest_tau_days)
            next_observation_day = float(parent["next_fixed_observation_day"])
            if dt_days > next_observation_day:
                dt_days = next_observation_day

            gate("first_dt_positive_finite", np.isfinite(dt_days) and dt_days > 0.0, dt_days)
            gate("first_dt_does_not_cross_next_observation", dt_days <= next_observation_day, dt_days)
            gate("first_dt_is_SGSim_physics_derived_not_V15_bound", True, f"dtD_CFL={dtD_cfl:.12e}, tau_min={fastest_tau_days:.12e} d")

            # --------------------------------------------------------------
            # Full-physics transport from the exact t=0 baseline to t=dt.
            # --------------------------------------------------------------
            max_tD = float(dt_days / fastest_tau_days)
            master_tD, master_S, master_diag = sg7a.build_master_solution(xi, max_tD)
            nstream = len(tau_end_days)
            streamline_sat = np.zeros((nstream, len(xi)), dtype=np.float64)
            dimensionless_time = dt_days / tau_end_days
            for s in range(nstream):
                streamline_sat[s] = sg7a.interpolate_master_profile(
                    float(dimensionless_time[s]), master_tD, master_S
                )

            gate("streamline_transport_finite", np.all(np.isfinite(streamline_sat)))
            gate("streamline_transport_lower_bound", float(np.min(streamline_sat)) >= BACKGROUND_SATURATION - 1.0e-10, np.min(streamline_sat))
            gate("streamline_transport_upper_bound", float(np.max(streamline_sat)) <= INJECTED_BOUNDARY_SATURATION + 1.0e-10, np.max(streamline_sat))
            gate("streamline_transport_changed_from_parent", float(np.max(streamline_sat - BACKGROUND_SATURATION)) > 0.0, np.max(streamline_sat - BACKGROUND_SATURATION))

            # --------------------------------------------------------------
            # Continuous producer CO2-cut and component production ledger.
            # --------------------------------------------------------------
            outlet = streamline_sat[:, -1]
            outlet_fractional_flow = np.asarray(sg7a.fractional_flow(outlet), dtype=np.float64)
            labels = np.asarray(sg6["producer"]).astype(str)
            weights_m3_s = np.asarray(sg6["weights_m3_s"], dtype=np.float64)

            producer_rows: list[dict[str, Any]] = []
            producer_mass_kg = 0.0
            qprod_total_m3_day = 0.0
            qprod_gas_weighted = 0.0

            # The accepted injection-density anchor is the exact source gas-phase
            # pressure at the five injector completions, evaluated at the injected
            # boundary saturation increment.
            injection_pc = float(capillary_pressure_from_incremental_sg(MAX_INCREMENTAL_CO2_SATURATION))
            injector_pw_pa = np.array(
                [pressure_psi[k, INJECTOR_J, INJECTOR_I] * PSI_TO_PA for k in COMPLETION_K],
                dtype=np.float64,
            )
            p_ref_gas_pa = float(np.mean(injector_pw_pa) + injection_pc)

            for name, loc in PRODUCERS.items():
                mask = labels == name
                w = weights_m3_s[mask]
                cut = float(np.sum(w * outlet_fractional_flow[mask]) / np.sum(w))
                qprod_m3_day = float(sg3_summary["producer_rates"][name]["m3_day"])
                qprod_total_m3_day += qprod_m3_day
                qprod_gas_weighted += qprod_m3_day * cut

                # Flow-weighted outlet saturation supplies the producer gas-phase
                # capillary/density state for component-mass accounting.
                sout = float(np.sum(w * outlet[mask]) / np.sum(w))
                sgout = max(0.0, min(MAX_INCREMENTAL_CO2_SATURATION, sout - BACKGROUND_SATURATION))
                pc_prod = float(capillary_pressure_from_incremental_sg(sgout))
                p_g_prod_pa = 2000.0 * PSI_TO_PA + pc_prod
                rho_prod = float(
                    CO2_RHO_REF_KG_M3
                    * math.exp(
                        max(
                            -50.0,
                            min(
                                50.0,
                                CO2_COMPRESSIBILITY_1_PA * (p_g_prod_pa - p_ref_gas_pa),
                            ),
                        )
                    )
                )
                gas_mass_rate_kg_day = qprod_m3_day * cut * rho_prod
                produced = gas_mass_rate_kg_day * dt_days
                producer_mass_kg += produced
                producer_rows.append({
                    "producer": name,
                    "volumetric_rate_m3_day": qprod_m3_day,
                    "CO2_cut": cut,
                    "outlet_transport_saturation": sout,
                    "CO2_density_kg_m3": rho_prod,
                    "CO2_mass_rate_kg_day": gas_mass_rate_kg_day,
                    "CO2_mass_this_step_kg": produced,
                })

            aggregate_gas_cut = (
                qprod_gas_weighted / qprod_total_m3_day
                if qprod_total_m3_day > 0.0 else 0.0
            )
            gate("producer_CO2_cut_finite_bounded", np.isfinite(aggregate_gas_cut) and 0.0 <= aggregate_gas_cut <= 1.0, aggregate_gas_cut)

            injected_mass_kg = INJECTOR_MASS_RATE_KG_DAY * dt_days
            produced_mass_kg = float(producer_mass_kg)
            target_stored_mass_kg = injected_mass_kg - produced_mass_kg
            gate("first_step_injected_mass_positive", injected_mass_kg > 0.0, injected_mass_kg)
            gate("first_step_produced_mass_nonnegative", produced_mass_kg >= 0.0, produced_mass_kg)
            gate("first_step_target_stored_mass_positive", target_stored_mass_kg > 0.0, target_stored_mass_kg)

            # --------------------------------------------------------------
            # Conservative segment/cell map-back and compressible mass closure.
            # --------------------------------------------------------------
            sg7d = load_module(tmp / Path(SG7D).name, "pad_stream_v16e35_sg7d")
            tof_days = np.asarray(sg6["tau_s"], dtype=np.float64) / DAY_TO_S
            weights_m3_day = weights_m3_s * DAY_TO_S
            operator = sg7d.build_subsegment_operator(
                np.asarray(sg6["xyz_m"], dtype=np.float64),
                tof_days,
                weights_m3_day,
            )
            coverage = sg7d.build_coverage(operator)

            # SG7A's first numerical node is the Dirichlet injection boundary
            # and is already S_INJECTED at tD=0. That boundary node has zero
            # physical source volume and must not create a fictitious finite
            # Cartesian CO2 inventory at t=0. Map only the evolved increment
            # above the exact tD=0 streamline profile; the source-cell inventory
            # is then closed locally through the five injector completion cells.
            streamline_t0_profile = np.full_like(
                streamline_sat, BACKGROUND_SATURATION, dtype=np.float64
            )
            streamline_t0_profile[:, 0] = INJECTED_BOUNDARY_SATURATION
            evolved_streamline_increment = np.maximum(
                streamline_sat - streamline_t0_profile, 0.0
            )
            mapback_streamline_sat = np.clip(
                BACKGROUND_SATURATION + evolved_streamline_increment,
                BACKGROUND_SATURATION,
                INJECTED_BOUNDARY_SATURATION,
            )

            segment_sat = sg7d.evaluate_subsegment_saturation(
                mapback_streamline_sat, operator
            )
            raw_grid = sg7d.raw_mapback(segment_sat, operator, coverage)

            coverage_weight = np.asarray(coverage["coverage_weight_m3"], dtype=np.float64)
            coverage_mask = np.asarray(coverage["coverage_mask"], dtype=bool)
            streamline_count = np.asarray(coverage["streamline_count"], dtype=np.int64)
            support_input = float(np.sum(operator["pv_m3"]))
            support_grid = float(np.sum(coverage_weight))
            support_rel = abs(support_grid - support_input) / max(abs(support_input), 1.0e-30)
            sat_measure_input = float(np.sum(operator["pv_m3"] * segment_sat))
            sat_measure_grid = float(np.sum(coverage_weight * raw_grid))
            sat_measure_rel = abs(sat_measure_grid - sat_measure_input) / max(abs(sat_measure_input), 1.0e-30)

            gate("mapback_support_closure", support_rel <= 1.0e-10, support_rel)
            gate("mapback_saturation_measure_closure", sat_measure_rel <= 1.0e-10, sat_measure_rel)
            gate("raw_mapback_bounds", float(np.min(raw_grid)) >= BACKGROUND_SATURATION - 1.0e-10 and float(np.max(raw_grid)) <= INJECTED_BOUNDARY_SATURATION + 1.0e-10, f"{np.min(raw_grid)}:{np.max(raw_grid)}")

            dx_m, dy_m, dz_m = 20.0 * FT_TO_M, 20.0 * FT_TO_M, 4.0 * FT_TO_M
            cell_pore_volume_m3 = 0.20 * dx_m * dy_m * dz_m

            # E35-R1 repair: use the exact subsegment pore-volume measure to
            # deposit incremental CO2 inventory directly into Cartesian cells.
            # The legacy raw_grid is retained only as an SG7D support/shape
            # diagnostic and is not promoted to full-cell inventory.
            projection = conservative_inventory_mapback_and_source_closure(
                segment_saturation=segment_sat,
                operator=operator,
                pressure_psi=pressure_psi,
                target_mass_kg=target_stored_mass_kg,
                cell_pore_volume_m3=cell_pore_volume_m3,
                p_ref_pa=p_ref_gas_pa,
            )
            child_sat = np.asarray(projection["corrected"], dtype=np.float64)
            child_hist = np.maximum(np.asarray(parent["transport_saturation_history"], dtype=np.float64), child_sat)
            child_increment = child_sat - BACKGROUND_SATURATION
            final_stored_mass_kg = float(projection["final_mass_kg"])
            step_mass_residual_kg = (
                final_stored_mass_kg
                - float(parent["stored_co2_mass_initial_kg"])
                - injected_mass_kg
                + produced_mass_kg
            )
            closure_numeric_tol_kg = max(
                1.0e-6,
                1.0e-10 * max(abs(target_stored_mass_kg), 1.0),
            )

            gate("child_grid_saturation_finite", np.all(np.isfinite(child_sat)))
            gate("child_grid_saturation_bounds", float(np.min(child_sat)) >= BACKGROUND_SATURATION - 1.0e-12 and float(np.max(child_sat)) <= INJECTED_BOUNDARY_SATURATION + 1.0e-12, f"{np.min(child_sat)}:{np.max(child_sat)}")
            gate("child_grid_state_changed", float(np.max(child_sat - parent["transport_saturation"])) > 0.0, np.max(child_sat - parent["transport_saturation"]))
            gate("inventory_mapback_did_not_modify_inactive_cells", np.allclose(child_sat[~projection["active_mask"]], BACKGROUND_SATURATION, atol=0.0, rtol=0.0))
            gate(
                "path_inventory_does_not_exceed_available_component_mass",
                projection["path_mass_kg"] <= target_stored_mass_kg + projection["roundoff_mass_kg"],
                f"{projection['path_mass_kg']:.12e} <= {target_stored_mass_kg:.12e} kg",
            )
            gate(
                "source_local_closure_only_in_injector_cells",
                projection["corrected_cells"] <= len(COMPLETION_K),
                projection["corrected_cells"],
            )
            gate(
                "source_local_saturation_correction_bounded",
                0.0 <= projection["source_delta_saturation"] <= MAX_INCREMENTAL_CO2_SATURATION + 1.0e-12,
                projection["source_delta_saturation"],
            )
            gate("compressible_CO2_mass_closure_numeric", abs(step_mass_residual_kg) <= closure_numeric_tol_kg, f"{step_mass_residual_kg:.12e} kg <= {closure_numeric_tol_kg:.12e} kg")
            gate("projection_mass_target_identity", abs(projection["residual_kg"]) <= closure_numeric_tol_kg, projection["residual_kg"])

            breakthrough = bool(aggregate_gas_cut >= BREAKTHROUGH_GAS_CUT)
            breakthrough_time = dt_days if breakthrough else np.nan
            next_obs_cursor = int(parent["observation_cursor_index"])
            next_obs_day = float(parent["next_fixed_observation_day"])

            # F0 remains present but is not advanced on this cold-start milestone:
            # the V15F0 feature/calibration contract was trained on the prototype
            # grid, and E35 deliberately does not fabricate SGSim-equivalent
            # recurrent diagnostics merely to force a hidden-state update.
            f0_hidden_child = np.asarray(parent["f0_hidden_state"], dtype=np.float32).copy()

            child_arrays = {
                "physical_time_days": np.asarray(dt_days, dtype=np.float64),
                "accepted_step_index": np.asarray(1, dtype=np.int64),
                "grid_shape": np.asarray(EXPECTED_GRID, dtype=np.int64),
                "background_saturation": np.asarray(BACKGROUND_SATURATION, dtype=np.float64),
                "injected_boundary_saturation": np.asarray(INJECTED_BOUNDARY_SATURATION, dtype=np.float64),
                "transport_saturation": child_sat.astype(np.float64),
                "transport_saturation_history": child_hist.astype(np.float64),
                "co2_incremental_saturation": child_increment.astype(np.float64),
                "initial_pressure_reference_psi": np.asarray(parent["initial_pressure_reference_psi"], dtype=np.float64),
                "accepted_pressure_psi": pressure_psi.astype(np.float64),
                "f0_hidden_state": f0_hidden_child,
                "cumulative_injected_co2_mass_kg": np.asarray(injected_mass_kg, dtype=np.float64),
                "cumulative_produced_co2_mass_kg": np.asarray(produced_mass_kg, dtype=np.float64),
                "cumulative_boundary_co2_mass_kg": np.asarray(0.0, dtype=np.float64),
                "stored_co2_mass_initial_kg": np.asarray(float(parent["stored_co2_mass_initial_kg"]), dtype=np.float64),
                "stored_co2_mass_current_kg": np.asarray(final_stored_mass_kg, dtype=np.float64),
                "last_step_mass_residual_kg": np.asarray(step_mass_residual_kg, dtype=np.float64),
                "cumulative_mass_residual_kg": np.asarray(step_mass_residual_kg, dtype=np.float64),
                "current_producer_co2_gas_cut": np.asarray(aggregate_gas_cut, dtype=np.float64),
                "breakthrough_reached": np.asarray(breakthrough, dtype=bool),
                "breakthrough_time_days": np.asarray(breakthrough_time, dtype=np.float64),
                "time_since_breakthrough_days": np.asarray(0.0, dtype=np.float64),
                "last_accepted_dt_days": np.asarray(dt_days, dtype=np.float64),
                "last_accepted_dt_defined": np.asarray(True, dtype=bool),
                "observation_cursor_index": np.asarray(next_obs_cursor, dtype=np.int64),
                "next_fixed_observation_day": np.asarray(next_obs_day, dtype=np.float64),
                "path_cache_valid": np.asarray(True, dtype=bool),
                "tof_cache_valid": np.asarray(True, dtype=bool),
                "exact_retrace_required": np.asarray(True, dtype=bool),
                "operational_pressure_state_ready": np.asarray(True, dtype=bool),
                "darcy_flux_state_ready": np.asarray(True, dtype=bool),
                "first_step_full_exact_preflight_required": np.asarray(False, dtype=bool),
                "first_transition_full_exact_cold_start_completed": np.asarray(True, dtype=bool),
                "f0_hidden_update_deferred_for_SGSim_feature_revalidation": np.asarray(True, dtype=bool),
                "co2_density_reference_pressure_pa": np.asarray(p_ref_gas_pa, dtype=np.float64),
                "co2_density_reference_kg_m3": np.asarray(CO2_RHO_REF_KG_M3, dtype=np.float64),
                "co2_compressibility_1_pa": np.asarray(CO2_COMPRESSIBILITY_1_PA, dtype=np.float64),
            }

            cache_arrays = {
                "physical_time_days": np.asarray(dt_days, dtype=np.float64),
                "accepted_pressure_psi": pressure_psi.astype(np.float64),
                "qx_m3_s": qx.astype(np.float64),
                "qy_m3_s": qy.astype(np.float64),
                "qz_m3_s": qz.astype(np.float64),
                "streamline_xyz_m": np.asarray(sg6["xyz_m"], dtype=np.float64),
                "streamline_tof_s": np.asarray(sg6["tau_s"], dtype=np.float64),
                "tau_end_s": np.asarray(sg6["tau_end_s"], dtype=np.float64),
                "streamline_weights_m3_s": weights_m3_s.astype(np.float64),
                "producer_labels": labels.astype("U32"),
                "streamline_saturation": streamline_sat.astype(np.float64),
                "streamline_dimensionless_time": dimensionless_time.astype(np.float64),
                "support_coverage_weight_m3": coverage_weight.astype(np.float64),
                "support_streamline_count": streamline_count.astype(np.int64),
                "support_mask": coverage_mask.astype(np.uint8),
            }

            # Child/cache bytes are created only after all physics acceptance gates.
            child_bytes = deterministic_npz_bytes(child_arrays)
            cache_bytes = deterministic_npz_bytes(cache_arrays)

            # Restart/readback validation is performed from the exact bytes that
            # will be committed, so no accepted artifact is published before the
            # restart contract passes.
            with np.load(io.BytesIO(child_bytes), allow_pickle=False) as c:
                gate("child_restart_time_exact", float(c["physical_time_days"]) == dt_days)
                gate("child_restart_step_index_exact", int(c["accepted_step_index"]) == 1)
                gate("child_restart_saturation_exact", np.array_equal(c["transport_saturation"], child_sat))
                gate("child_restart_mass_exact", float(c["stored_co2_mass_current_kg"]) == final_stored_mass_kg)
                gate("child_restart_last_dt_exact", float(c["last_accepted_dt_days"]) == dt_days)
                gate("child_restart_path_cache_valid", bool(c["path_cache_valid"]))
                gate("child_restart_next_retrace_required", bool(c["exact_retrace_required"]))

            # --------------------------------------------------------------
            # Final parent/checkpoint immutability before commit.
            # --------------------------------------------------------------
            gate("E34_parent_state_unchanged_before_commit", sha256_file(parent_state_path) == parent_sha_before)
            gate("frozen_100d_unchanged_before_commit", sha256_file(frozen_100d) == frozen_100d_sha_before)

            source_rows = [
                {"role": "physics_authority", "path": rel, "sha256": sha256_file(root / rel)}
                for rel in required
            ]
            source_rows.append({"role": "accepted_parent", "path": str(parent_state_path.relative_to(drive)), "sha256": parent_sha_before})
            source_rows.append({"role": "failed_parent_attempt", "path": str(e35_failed_report_path.relative_to(drive)), "sha256": sha256_file(e35_failed_report_path)})
            source_rows.append({"role": "failed_E35_runner", "path": E35_ORIGINAL_RUNNER, "sha256": sha256_file(e35_original_runner_path)})

            step_audit = {
                "milestone": MILESTONE,
                "status": STATUS,
                "parent": {
                    "milestone": "V16E-34",
                    "state_file": E34_STATE,
                    "state_sha256": parent_sha_before,
                    "physical_time_days": 0.0,
                    "accepted_step_index": 0,
                },
                "child": {
                    "physical_time_days": dt_days,
                    "accepted_step_index": 1,
                    "next_fixed_observation_day": next_obs_day,
                    "breakthrough_reached": breakthrough,
                    "breakthrough_time_days": None if not breakthrough else breakthrough_time,
                },
                "timestep": {
                    "selection": "CLASSICAL_SGSIM_SG7A_CFL_TIMES_FASTEST_EXACT_TOF",
                    "learned_F0_timestep_proposal_used": False,
                    "V15_numeric_dt_bounds_inherited": False,
                    "dimensionless_CFL_dt": dtD_cfl,
                    "fastest_terminal_TOF_days": fastest_tau_days,
                    "accepted_dt_days": dt_days,
                    "next_observation_day": next_observation_day,
                    "retry_count": 0,
                },
                "flow": {
                    "pressure_solver": "V15-SG3 source-authentic finite-volume five-spot cold-start pressure",
                    "darcy_flux": "V15-SG4 source-authentic conservative Darcy face flux",
                    "pollock": "V15-SG5 exact 3D Pollock, 7x7 face subdivisions",
                    "tof": "V15-SG6 normalized transport coordinates",
                    "streamlines": int(nstream),
                    "qinj_from_streamline_weights_m3_day": qinj_m3_day_from_paths,
                    "pressure_min_psi": float(np.min(pressure_psi)),
                    "pressure_max_psi": float(np.max(pressure_psi)),
                },
                "transport": {
                    "solver": "V15-SG7A classical full compressible+capillary streamline transport",
                    "parent_saturation_coordinate": BACKGROUND_SATURATION,
                    "child_saturation_min": float(np.min(child_sat)),
                    "child_saturation_max": float(np.max(child_sat)),
                    "maximum_saturation_change": float(np.max(child_sat - parent["transport_saturation"])),
                    "mapback": "V15-SG7D exact Cartesian subsegment geometry with E35-R1 direct incremental-inventory deposition plus injector-local component-mass closure",
                    "t0_boundary_node_volume_policy": "subtract exact tD=0 Dirichlet streamline profile before Cartesian deposition; source inventory closes only through injector completion cells plus evolved path support",
                    "support_fraction": float(np.mean(coverage_mask)),
                    "support_closure_relative": support_rel,
                    "saturation_measure_closure_relative": sat_measure_rel,
                    "path_increment_volume_m3": projection["path_increment_volume_m3"],
                    "path_supported_cells": projection["path_supported_cells"],
                    "source_local_missing_mass_before_closure_kg": projection["missing_source_mass_before_closure_kg"],
                    "source_local_delta_saturation": projection["source_delta_saturation"],
                    "source_local_max_abs_correction": projection["source_max_abs_correction"],
                    "source_local_corrected_cells": projection["corrected_cells"],
                },
                "mass": {
                    "density_model": "rho_g=rho_ref*exp(c_g*(p_g-p_ref)); p_g=p_w+Pc(Sg_increment)",
                    "rho_ref_kg_m3": CO2_RHO_REF_KG_M3,
                    "c_g_1_pa": CO2_COMPRESSIBILITY_1_PA,
                    "p_ref_pa": p_ref_gas_pa,
                    "p_ref_rule": "mean accepted injector gas-phase pressure at injected boundary saturation",
                    "injected_CO2_mass_kg": injected_mass_kg,
                    "produced_CO2_mass_kg": produced_mass_kg,
                    "target_stored_CO2_mass_kg": target_stored_mass_kg,
                    "path_deposited_stored_CO2_mass_kg": projection["path_mass_kg"],
                    "accepted_stored_CO2_mass_kg": final_stored_mass_kg,
                    "step_mass_residual_kg": step_mass_residual_kg,
                    "numerical_closure_check_kg": closure_numeric_tol_kg,
                    "SGSim_specific_runtime_mass_tolerance_frozen": False,
                },
                "producer_CO2_response": producer_rows,
                "recurrent_memory": {
                    "F0_hidden_state_preserved_zero": bool(np.count_nonzero(f0_hidden_child) == 0),
                    "F0_hidden_update_deferred": True,
                    "reason": "cold-start exact milestone does not fabricate SGSim equivalents of prototype-trained V15F0 recurrent diagnostic features",
                    "F0_learned_dt_proposal_authorized_for_this_step": False,
                },
                "rollback_contract": {
                    "accepted_child_published_only_after_all_gates": True,
                    "rejected_attempt_would_advance_time": False,
                    "rejected_attempt_would_mutate_parent": False,
                },
            }

            state_contract = {
                "milestone": MILESTONE,
                "status": "FIRST_ACCEPTED_CHILD_RUNTIME_STATE_CONTRACT",
                "canonical_recurrent_state": "conservative Cartesian grid transport_saturation",
                "parent_state": E34_STATE,
                "child_state": "V16E35_R1_First_Accepted_SGSim_Runtime_State_Step0001.npz",
                "cache_state": "V16E35_R1_First_Accepted_Physics_Cache_Step0001.npz",
                "persistent_state": [
                    "physical_time_days",
                    "accepted_step_index",
                    "transport_saturation",
                    "transport_saturation_history",
                    "cumulative injected/produced/boundary CO2 mass",
                    "stored CO2 mass",
                    "per-step/cumulative mass residual",
                    "producer CO2 gas cut",
                    "breakthrough memory",
                    "last accepted dt",
                    "F0 hidden state",
                    "observation cursor",
                ],
                "cache_state_role": "recomputable exact pressure/Darcy/Pollock/TOF/streamline transport bound to accepted child",
                "next_transition_retrace_required": True,
                "reason_next_retrace_required": "E35 establishes only the first cold-start flow/path state; E36 must re-evaluate pressure/path reuse after the accepted saturation change.",
            }

            summary = {
                "milestone": MILESTONE,
                "status": STATUS,
                "next_milestone": NEXT,
                "parent_milestone": "V16E-34",
                "parent_state_sha256": parent_sha_before,
                "accepted_step_index": 1,
                "parent_time_days": 0.0,
                "accepted_child_time_days": dt_days,
                "accepted_dt_days": dt_days,
                "classical_dt_selection_used": True,
                "learned_timestep_proposal_used": False,
                "V15_numeric_dt_bounds_inherited_without_revalidation": False,
                "SGSim_specific_dt_envelope_frozen": False,
                "SGSim_specific_mass_tolerance_frozen": False,
                "operational_pressure_solved": True,
                "Darcy_flux_executed": True,
                "Pollock_executed": True,
                "TOF_executed": True,
                "full_physics_transport_executed": True,
                "conservative_mapback_executed": True,
                "compressible_component_mass_projection_executed": True,
                "direct_inventory_mapback_repair_executed": True,
                "injector_local_mass_closure_executed": True,
                "single_step_executed": True,
                "single_step_accepted": True,
                "runtime_time_advance_performed": True,
                "new_saturation_field_created": True,
                "first_transition_full_exact_cold_start_completed": True,
                "path_cache_valid": True,
                "tof_cache_valid": True,
                "exact_retrace_required_for_next_transition": True,
                "streamlines": int(nstream),
                "transport_nodes": int(len(xi)),
                "producer_CO2_gas_cut": aggregate_gas_cut,
                "breakthrough_reached": breakthrough,
                "breakthrough_threshold": BREAKTHROUGH_GAS_CUT,
                "injected_CO2_mass_kg": injected_mass_kg,
                "produced_CO2_mass_kg": produced_mass_kg,
                "stored_CO2_mass_kg": final_stored_mass_kg,
                "step_mass_residual_kg": step_mass_residual_kg,
                "cumulative_mass_residual_kg": step_mass_residual_kg,
                "mass_numerical_closure_passed": abs(step_mass_residual_kg) <= closure_numeric_tol_kg,
                "F0_hidden_update_deferred": True,
                "E36_short_rollout_entry_ready": True,
                "frozen_100d_checkpoint_modified": False,
                "IBDP_started": False,
                "OOD_reopened": False,
                "internal_test_reopened": False,
            }

            handoff = f"""# PAD-Stream V16E-35-R1 Handoff

V16E-35-R1 repaired the failed E35 map-back inventory representation and accepted the first real SGSim runtime state transition from the frozen E34 t=0 parent.

Accepted child:
- step index: 1
- physical time: {dt_days:.12g} days
- accepted dt: {dt_days:.12g} days
- dt authority: SG7A dimensionless CFL multiplied by the fastest exact SGSim terminal TOF
- learned F0 dt proposal used: NO
- V15 prototype numerical dt limits inherited: NO

Exact cold-start execution:
- V15-SG2 anisotropic face permeability/transmissibility construction
- V15-SG3 operational five-spot pressure
- V15-SG4 conservative Darcy fluxes
- V15-SG5 exact 3D Pollock retrace
- V15-SG6 TOF coordinates / streamline weights
- V15-SG7A classical full compressible+capillary transport
- V15-SG7D exact subsegment/cell overlap geometry
- direct subsegment incremental-CO2 inventory deposition into Cartesian cell pore volume
- pressure-dependent source-local CO2 mass closure restricted to the five injector completion cells

CO2 ledger:
- injected: {injected_mass_kg:.12e} kg
- produced: {produced_mass_kg:.12e} kg
- stored: {final_stored_mass_kg:.12e} kg
- step residual: {step_mass_residual_kg:.12e} kg

E35-R1 performs no global saturation rescale. Path inventory is deposited directly from exact subsegment pore-volume measure, and only any inlet-boundary mass not represented downstream may be added in the five injector completion cells. If path deposition itself exceeds available injected component mass, the step rejects.

The first step does not activate the V15F0 learned timestep proposal or fabricate prototype-grid recurrent features. F0 hidden memory remains the exact E34 zero cold-start vector. E36 must establish the SGSim-compatible adaptive/recurrent continuation policy from accepted runtime diagnostics.

Neither the SGSim runtime dt envelope nor the final runtime mass-acceptance tolerance is frozen by E35-R1.

NEXT: {NEXT}
"""

            closure = {
                "milestone": MILESTONE,
                "status": STATUS,
                "all_runtime_gates_passed": all(v["passed"] for v in gates.values()),
                "gate_count": len(gates),
                "child_state_sha256": hashlib.sha256(child_bytes).hexdigest(),
                "physics_cache_sha256": hashlib.sha256(cache_bytes).hexdigest(),
                "parent_state_sha256": parent_sha_before,
                "frozen_100d_sha256": frozen_100d_sha_before,
            }

            files = {
                "V16E35_R1_First_Accepted_SGSim_Runtime_State_Step0001.npz": child_bytes,
                "V16E35_R1_First_Accepted_Physics_Cache_Step0001.npz": cache_bytes,
                "V16E35_R1_First_Controlled_Transition_Audit.json": json_bytes(step_audit),
                "V16E35_R1_Accepted_Runtime_State_Contract.json": json_bytes(state_contract),
                "V16E35_R1_Producer_CO2_Response.csv": csv_bytes(producer_rows),
                "V16E35_R1_Source_Authority_Manifest.csv": csv_bytes(source_rows),
                "V16E35_R1_Final_Gate_Matrix.csv": csv_bytes(
                    [{"gate": k, **v} for k, v in gates.items()]
                ),
                "PAD_Stream_V16E35_R1_Summary.json": json_bytes(summary),
                "V16E35_R1_Handoff.md": handoff.encode("utf-8"),
                "V16E35_R1_Final_Closure.json": json_bytes(closure),
            }

            # Publish only after every acceptance/restart/immutability gate has
            # passed. A differing pre-existing accepted artifact is never replaced.
            immutable_publish(out, files)

            artifact_rows = []
            for path in sorted(out.iterdir()):
                if path.is_file() and path.name != "V16E35_R1_Artifact_Manifest.csv":
                    artifact_rows.append({
                        "file": path.name,
                        "sha256": sha256_file(path),
                        "bytes": path.stat().st_size,
                    })
            immutable_publish(
                out,
                {"V16E35_R1_Artifact_Manifest.csv": csv_bytes(artifact_rows)},
            )

        print("\n" + "=" * 136)
        print("PAD-Stream V16E-35-R1 FIRST CONTROLLED TRANSITION: PASS")
        print("=" * 136)
        print(f"{'Accepted step index':74}: 1")
        print(f"{'Accepted child time':74}: {dt_days:.12g} days")
        print(f"{'Accepted dt':74}: {dt_days:.12g} days")
        print(f"{'Streamlines / transport nodes':74}: {nstream} / {len(xi)}")
        print(f"{'Producer CO2 gas cut':74}: {aggregate_gas_cut:.12e}")
        print(f"{'Injected CO2 mass':74}: {injected_mass_kg:.12e} kg")
        print(f"{'Produced CO2 mass':74}: {produced_mass_kg:.12e} kg")
        print(f"{'Stored CO2 mass':74}: {final_stored_mass_kg:.12e} kg")
        print(f"{'Step mass residual':74}: {step_mass_residual_kg:.12e} kg")
        print(f"{'SGSim runtime dt envelope frozen':74}: NO")
        print(f"{'SGSim runtime mass tolerance frozen':74}: NO")
        print(f"{'F0 learned timestep used':74}: NO")
        print(f"{'F0 hidden update deferred':74}: YES")
        print(f"{'E36 short adaptive rollout entry ready':74}: YES")
        print(f"NEXT: {NEXT}")
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": "FIRST_CONTROLLED_SGSIM_RUNTIME_STATE_TRANSITION_BLOCKED",
            "exception": repr(exc),
            "gates": gates,
            "parent_state": str(parent_state_path),
            "parent_state_sha256_before": parent_sha_before,
            "frozen_100d_sha256_before": frozen_100d_sha_before,
            "accepted_child_published": False,
            "runtime_time_advance_committed": False,
            "parent_mutated": False,
            "repair_of": "V16E-35",
            "original_E35_failure": E35_FAILED_EXCEPTION,
            "next_action": "Audit the failed gate; do not treat a trial state as accepted.",
        }
        path = blocked / "V16E35_R1_Blocked_First_Controlled_Transition.json"
        data = json_bytes(report)
        if path.exists() and path.read_bytes() != data:
            path = blocked / f"V16E35_R1_Blocked_First_Controlled_Transition_{hashlib.sha256(data).hexdigest()[:12]}.json"
        if not path.exists():
            path.write_bytes(data)
        print("\n" + "=" * 136)
        print("PAD-Stream V16E-35-R1 FIRST CONTROLLED TRANSITION: BLOCKED")
        print("=" * 136)
        print("Reason:", repr(exc))
        print("No accepted child state was committed by this failed execution path.")
        return 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--drive-root", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(main(args.project_root, args.drive_root))
