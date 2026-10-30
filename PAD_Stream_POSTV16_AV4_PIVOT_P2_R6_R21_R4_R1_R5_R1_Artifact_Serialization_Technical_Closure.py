#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

M = "POSTV16-AV4-PIVOT-P2-R6-R21-R4-R1-R5-R1"
NAME = "R5 Artifact Serialization Technical Closure and Day375 Pressure-Refresh Acceptance"

PASS = (
    "AV4PIVOTP2R6R21R4R1R5R1_R5_ARTIFACT_SERIALIZATION_TECHNICAL_CLOSURE_"
    "PASS_DAY375_PRESSURE_REFRESH_ACCEPTED_NO_SCIENCE_RERUN"
)
BLOCK = "AV4PIVOTP2R6R21R4R1R5R1_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "00980db1c9c743ebfebaeb9b9f76d0e91bba9a5d"

R5_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_"
    "Controlled_SplitState_T1_PressureCapacity_Reconciliation_Execution.py"
)
R5_BLOB = "bfd1baff03c8670e627f526a8495a6a16d739519"

A2E_RUNNER = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"
R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
SG2 = "PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"
SG2_BLOB = "7242012d3e758472abc3ee7f543831b92d2cf419"
SG3 = "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG3_BLOB = "66a379cd97ee9120f69e7e7e949171541e4918c3"
R3PHYS = "PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py"
R3PHYS_BLOB = "740c6da03e73906646bf0153633187e749449f31"
PERM = "SGSIM_50x50x15_PERM_MD.csv"
PERM_BLOB = "317dd47d458bc6f880c2e3dc4ec1f69eeb0dd314"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R5_OUT = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_"
    "Controlled_SplitState_T1_Day375_PressureCapacity_Reconciliation_Execution"
)
R5_BLOCK = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_BLOCKED/"
    "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_Blocked_Report.json"
)

R20 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R20_Day375_Globally_Reconciled_"
    "Provisional_State_Closure_and_Acceptance_Audit"
)
R20_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R20_Summary.json"
R20_ACCEPTANCE = "POSTV16_AV4_PIVOT_P2_R6_R20_Day375_State_Acceptance_Contract.json"
R20_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R20_Artifact_Manifest.csv"

BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"
A6E = BASE_AV3 / "POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
A6E_STATE = "POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
A6E_STATE_SHA = "f9e3a7bd8c6dcc43d522e0cb99a0cede2bd212fd570085b4faf82dc71af8f803"

R5_STATE = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_Accepted_PressureCompatible_Day375_State.npz"
R5_EPOCH = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_Accepted_Day375_Pressure_Epoch.npz"
R5_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_Summary.json"
R5_DECISION = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_Decision_Contract.json"
R5_CONTRACT = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_Accepted_Pressure_Refresh_Contract.json"

R5_BLOCK_STATUS = "AV4PIVOTP2R6R21R4R1R5_TECHNICAL_OR_AUTHORITY_BLOCK"
R5_BLOCK_STAGE = "artifact_publication"
R5_BLOCK_EXCEPTION = "ValueError('Object arrays cannot be saved when allow_pickle=False')"

REQUIRED_SCIENCE_GATES = (
    "final_pressure_linear_residual",
    "final_fixed_domain_capacity_consistency",
    "final_pressure_fixed_point_consistency",
    "final_saturation_fixed_point_consistency",
    "final_cellwise_mass_reconstruction",
    "final_global_mass_relative_closure",
    "final_saturation_bounds",
    "final_per_CV_sidecar_conservation",
    "final_global_sidecar_conservation",
    "final_pressure_compatible_mass_matches_sidecar_definition",
    "final_global_accepted_mass_unchanged",
    "final_residual_Cartesian_sidecar_immutable",
    "final_residual_Cartesian_sidecar_SHA_exact",
)

OUT = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_"
    "Artifact_Serialization_Technical_Closure_and_Pressure_Refresh_Acceptance"
)
BLK = BASE / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_BLOCKED"

GRID = (15, 50, 50)
DAY = 375.0
PRESSURE_TOL = 1e-10
SAT_TOL = 1e-10
LINEAR_TOL = 1e-8
CV_TOL = 1e-10
GLOBAL_TOL = 1e-10


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


def sha_array(a: np.ndarray) -> str:
    arr = np.ascontiguousarray(np.asarray(a))
    h = hashlib.sha256()
    h.update(str(arr.dtype).encode("utf-8"))
    h.update(repr(arr.shape).encode("utf-8"))
    h.update(arr.tobytes(order="C"))
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


def deterministic_npz_bytes(arrays: dict[str, Any]) -> bytes:
    outer = io.BytesIO()
    with zipfile.ZipFile(outer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for key in sorted(arrays):
            arr = np.asarray(arrays[key])
            if arr.dtype == object:
                raise GateError(f"object_array_forbidden:{key}")
            b = io.BytesIO()
            np.save(b, arr, allow_pickle=False)
            info = zipfile.ZipInfo(f"{key}.npy", date_time=(1980,1,1,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, b.getvalue())
    return outer.getvalue()


def manifest(directory: Path, filename: str) -> None:
    for row in csvr(directory / filename):
        p = directory / row["file"]
        if not p.is_file():
            raise GateError(f"manifest_missing:{p.name}")
        if sha(p) != row["sha256"]:
            raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes:{p.name}")


def mod(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load:{path}")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def max_abs(a: np.ndarray) -> float:
    return float(np.max(np.abs(np.asarray(a, dtype=float))))


def relative_l2(new: np.ndarray, old: np.ndarray) -> float:
    a = np.asarray(new, dtype=float)
    b = np.asarray(old, dtype=float)
    return float(np.linalg.norm((a-b).ravel()) / max(float(np.linalg.norm(b.ravel())), 1e-30))


def normalize_producer_wi(
    producer_wi: dict[str, list[dict[str, float]]],
    sg3: Any,
) -> dict[str, np.ndarray]:
    rows = []
    for name in sorted(producer_wi):
        well = sg3.PRODUCERS[name]
        for item in producer_wi[name]:
            rows.append({
                "name": str(name),
                "i": int(well["i"]),
                "j": int(well["j"]),
                "k": int(item["k"]),
                "wi_si": float(item["wi_si"]),
                "wi_reference_si": float(item["wi_reference_si"]),
                "mobility_scale": float(item["mobility_scale"]),
                "re_m": float(item["re_m"]),
            })

    return {
        "producer_name": np.asarray([r["name"] for r in rows], dtype="U32"),
        "producer_i": np.asarray([r["i"] for r in rows], dtype=np.int64),
        "producer_j": np.asarray([r["j"] for r in rows], dtype=np.int64),
        "producer_k": np.asarray([r["k"] for r in rows], dtype=np.int64),
        "producer_wi_si": np.asarray([r["wi_si"] for r in rows], dtype=np.float64),
        "producer_wi_reference_si": np.asarray([r["wi_reference_si"] for r in rows], dtype=np.float64),
        "producer_mobility_scale": np.asarray([r["mobility_scale"] for r in rows], dtype=np.float64),
        "producer_re_m": np.asarray([r["re_m"] for r in rows], dtype=np.float64),
    }


def sidecar_conservation(cv: np.ndarray, mass: np.ndarray) -> tuple[float, float]:
    d: dict[int, float] = {}
    total = 0.0
    for c, m in zip(cv.tolist(), mass.tolist()):
        d[int(c)] = d.get(int(c), 0.0) + float(m)
        total += float(m)
    return max((abs(v) for v in d.values()), default=0.0), abs(total)


def selftest() -> None:
    class SG3:
        PRODUCERS = {
            "P1": {"i": 1, "j": 2},
            "P2": {"i": 3, "j": 4},
        }
    wi = {
        "P1": [{"k": 0, "wi_si": 1.0, "wi_reference_si": 0.5, "mobility_scale": 2.0, "re_m": 3.0}],
        "P2": [{"k": 1, "wi_si": 4.0, "wi_reference_si": 2.0, "mobility_scale": 2.0, "re_m": 3.0}],
    }
    arrs = normalize_producer_wi(wi, SG3)
    assert arrs["producer_name"].dtype.kind == "U"
    assert all(np.asarray(v).dtype != object for v in arrs.values())
    blob = deterministic_npz_bytes(arrs)
    assert len(blob) > 0
    print("POSTV16 AV4 PIVOT P2-R6-R21-R4-R1-R5-R1 structural self-test: PASS")


def main(root: Path, drive: Path) -> int:
    root = root.resolve()
    drive = drive.resolve()
    out = drive / OUT
    block = drive / BLK
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
        summary_path = out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_Summary.json"
        block_path = block / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_Blocked_Report.json"

        if summary_path.is_file():
            print("[PASS] formal R5-R1 PASS already exists; immutable closure preserved.")
            return 0
        gate("no_preexisting_R5R1_BLOCK", not block_path.exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R5", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")

        for filename, blob, label in [
            (R5_RUNNER, R5_BLOB, "R5"),
            (A2E_RUNNER, A2E_BLOB, "A2E"),
            (R2, R2_BLOB, "R2"),
            (SG2, SG2_BLOB, "SG2"),
            (SG3, SG3_BLOB, "SG3"),
            (R3PHYS, R3PHYS_BLOB, "R3R2R1"),
            (PERM, PERM_BLOB, "PERM"),
        ]:
            gate(f"{label}_blob_exact", gt(root, "hash-object", str(root / filename)) == blob)

        stage = "R5_BLOCK_authority"
        r5_block_path = drive / R5_BLOCK
        gate("R5_BLOCK_present", r5_block_path.is_file(), str(r5_block_path))
        r5_block_sha = sha(r5_block_path)
        b5 = js(r5_block_path)

        gate("R5_BLOCK_status_exact", b5.get("status") == R5_BLOCK_STATUS, b5.get("status"))
        gate("R5_BLOCK_stage_artifact_publication", b5.get("failed_stage") == R5_BLOCK_STAGE, b5.get("failed_stage"))
        gate("R5_BLOCK_exception_exact", b5.get("exception") == R5_BLOCK_EXCEPTION, b5.get("exception"))
        gate("R5_BLOCK_preserved_Day375_state", b5.get("accepted_Day375_state_preserved") is True)
        gate("R5_BLOCK_pressure_not_accepted", b5.get("pressure_refresh_accepted") is False)
        gate("R5_BLOCK_no_automatic_rerun", b5.get("automatic_rerun_authorized") is False)
        gate("R5_BLOCK_no_Darcy_Pollock_TOF", b5.get("Darcy_Pollock_TOF_regeneration_authorized") is False)
        gate("R5_BLOCK_no_time_advance", b5.get("time_advance_authorized") is False)

        completed = b5.get("gates_completed", [])
        gate("R5_BLOCK_gate_matrix_is_list", isinstance(completed, list), type(completed).__name__)
        by_name = {
            str(row.get("gate")): row
            for row in completed
            if isinstance(row, dict) and row.get("gate") is not None
        }
        missing_science = [g for g in REQUIRED_SCIENCE_GATES if g not in by_name]
        failed_science = [
            g for g in REQUIRED_SCIENCE_GATES
            if g in by_name and by_name[g].get("pass") is not True
        ]
        gate("all_required_final_science_gates_present", not missing_science, missing_science)
        gate("all_required_final_science_gates_PASS", not failed_science, failed_science)

        stage = "R5_partial_artifact_authority"
        r5out = drive / R5_OUT
        state_path = r5out / R5_STATE
        epoch_path = r5out / R5_EPOCH
        gate("R5_partial_pressure_compatible_state_present", state_path.is_file(), str(state_path))
        partial_state_sha = sha(state_path)

        # These must remain absent because R5 formally BLOCKED before publication completed.
        gate("R5_pressure_epoch_absent", not epoch_path.exists(), str(epoch_path))
        gate("R5_summary_absent", not (r5out / R5_SUMMARY).exists())
        gate("R5_decision_absent", not (r5out / R5_DECISION).exists())
        gate("R5_pressure_contract_absent", not (r5out / R5_CONTRACT).exists())

        with np.load(state_path, allow_pickle=False) as z:
            required = [
                "state_day",
                "source_R20_accepted_state_sha256",
                "base_accepted_grid_mass_kg",
                "pressure_reconciliation_sidecar_cv",
                "pressure_reconciliation_sidecar_cell",
                "pressure_reconciliation_sidecar_mass_kg",
                "pressure_compatible_grid_mass_kg",
                "residual_cartesian_sidecar_kg",
                "residual_cartesian_sidecar_sha256",
                "pressure_compatible_saturation",
                "refreshed_pressure_psi",
                "reference_gas_pressure_pa",
                "frozen_T1_domain_flat_cell",
                "pressure_refresh_accepted",
                "physical_time_advanced",
            ]
            missing = [k for k in required if k not in z.files]
            gate("R5_partial_state_schema_complete", not missing, missing)

            state_day = float(np.asarray(z["state_day"]).reshape(()))
            source_r20_sha = str(np.asarray(z["source_R20_accepted_state_sha256"]).reshape(()))
            base_mass = np.asarray(z["base_accepted_grid_mass_kg"], dtype=float)
            sidecar_cv = np.asarray(z["pressure_reconciliation_sidecar_cv"], dtype=np.int64).reshape(-1)
            sidecar_cell = np.asarray(z["pressure_reconciliation_sidecar_cell"], dtype=np.int64).reshape(-1)
            sidecar_mass = np.asarray(z["pressure_reconciliation_sidecar_mass_kg"], dtype=float).reshape(-1)
            final_mass = np.asarray(z["pressure_compatible_grid_mass_kg"], dtype=float)
            residual_cartesian = np.asarray(z["residual_cartesian_sidecar_kg"], dtype=float)
            residual_sha_embedded = str(np.asarray(z["residual_cartesian_sidecar_sha256"]).reshape(()))
            final_sat = np.asarray(z["pressure_compatible_saturation"], dtype=float)
            final_pressure = np.asarray(z["refreshed_pressure_psi"], dtype=float)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            frozen_domain = np.asarray(z["frozen_T1_domain_flat_cell"], dtype=np.int64).reshape(-1)
            embedded_pressure_marker = bool(np.asarray(z["pressure_refresh_accepted"]).reshape(()))
            physical_time_advanced = bool(np.asarray(z["physical_time_advanced"]).reshape(()))

        gate("R5_partial_state_day_375", state_day == DAY, state_day)
        gate("R5_partial_shapes_exact", all(
            a.shape == GRID for a in (base_mass, final_mass, residual_cartesian, final_sat, final_pressure)
        ))
        gate("R5_partial_sidecar_lengths_exact", len(sidecar_cv) == len(sidecar_cell) == len(sidecar_mass))
        gate("R5_partial_embedded_pressure_marker_true_historical_only", embedded_pressure_marker is True)
        gate("R5_partial_no_time_advance", physical_time_advanced is False)

        stage = "R20_accepted_base_authority"
        r20 = drive / R20
        manifest(r20, R20_MANIFEST)
        s20 = js(r20 / R20_SUMMARY)
        a20 = js(r20 / R20_ACCEPTANCE)
        accepted_sha = str(a20["accepted_Day375_state_sha256"])
        gate("R20_state_accepted", a20.get("accepted_Day375_state") is True)
        gate("R20_SHA_matches_summary", accepted_sha == s20["accepted_Day375_state_sha256"])
        gate("R5_partial_source_R20_SHA_exact", source_r20_sha == accepted_sha, source_r20_sha)

        stage = "R5_partial_split_state_revalidation"
        max_cv_sidecar, global_sidecar = sidecar_conservation(sidecar_cv, sidecar_mass)
        gate("partial_state_per_CV_sidecar_conservative", max_cv_sidecar <= CV_TOL, max_cv_sidecar)
        gate("partial_state_global_sidecar_conservative", global_sidecar <= GLOBAL_TOL, global_sidecar)

        sidecar_grid = np.bincount(sidecar_cell, weights=sidecar_mass, minlength=np.prod(GRID)).reshape(GRID)
        gate(
            "partial_state_pressure_compatible_mass_exact_from_base_plus_sidecar",
            max_abs(base_mass + sidecar_grid - final_mass) <= 1e-12,
            max_abs(base_mass + sidecar_grid - final_mass),
        )
        gate(
            "partial_state_global_mass_unchanged",
            abs(float(np.sum(final_mass) - np.sum(base_mass))) <= 1e-7,
            float(np.sum(final_mass) - np.sum(base_mass)),
        )
        gate(
            "partial_state_residual_SHA_exact",
            sha_array(residual_cartesian) == residual_sha_embedded,
            {"embedded": residual_sha_embedded, "actual": sha_array(residual_cartesian)},
        )

        stage = "independent_final_physics_revalidation"
        a2e = mod(root / A2E_RUNNER, "r5r1_a2e")
        r2 = mod(root / R2, "r5r1_r2")
        sg2 = mod(root / SG2, "r5r1_sg2")
        sg3 = mod(root / SG3, "r5r1_sg3")
        r3phys = mod(root / R3PHYS, "r5r1_r3phys")

        control_path = drive / A6E / A6E_STATE
        gate("A6E_state_SHA_exact", control_path.is_file() and sha(control_path) == A6E_STATE_SHA)
        with np.load(control_path, allow_pickle=False) as z:
            phi = np.asarray(z["paired_porosity"], dtype=float)
            nw = np.asarray(z["nw"], dtype=float)
            no = np.asarray(z["no"], dtype=float)
            krw_max = np.asarray(z["krw_max"], dtype=float)
            kro_max = np.asarray(z["kro_max"], dtype=float)

        pore_volume = phi * float(a2e.BULK_VOLUME_M3)
        permeability = np.loadtxt(root / PERM, skiprows=1, dtype=float).reshape(GRID, order="C")

        mobility = a2e.spatial_mobility(final_sat, nw, no, krw_max, kro_max)
        kx, ky, kz = sg2.build_directional_permeability(permeability)
        kfx, kfy, kfz = sg2.build_face_permeabilities(kx, ky, kz)
        tx_ref, ty_ref, tz_ref = sg3.construct_si_transmissibilities(kfx, kfy, kfz)
        tx, ty, tz, _face = r3phys.build_updated_transmissibilities(
            sg3, tx_ref, ty_ref, tz_ref, mobility["lambda_total"]
        )

        A, b, producer_wi = r3phys.assemble_updated_pressure_system(
            sg3, permeability, tx, ty, tz, mobility["lambda_total"]
        )
        _p_pa, pressure_check, linear_residual = r3phys.solve_updated_pressure(sg3, A, b)

        gate("independent_pressure_linear_residual", linear_residual < LINEAR_TOL, linear_residual)
        pressure_consistency = relative_l2(pressure_check, final_pressure)
        gate("independent_pressure_matches_partial_state", pressure_consistency <= PRESSURE_TOL, pressure_consistency)

        full_sat = np.full(GRID, float(a2e.INJECTED), dtype=float)
        capacity = np.asarray(
            a2e.local_mass(r2, full_sat, pressure_check, p_ref, pore_volume),
            dtype=float,
        )
        cap_tol = max(1e-8, 1e-12 * max(float(np.max(capacity)), 1.0))
        max_cap_excess = float(np.max(final_mass - capacity))
        gate(
            "independent_final_capacity_closed",
            max_cap_excess <= cap_tol,
            {"maximum_excess_kg": max_cap_excess, "tolerance_kg": cap_tol},
        )

        sg_check = a2e.invert_local_mass(r2, final_mass, pressure_check, p_ref, pore_volume)
        sat_check = float(a2e.BACKGROUND) + np.asarray(sg_check, dtype=float)
        saturation_consistency = max_abs(sat_check - final_sat)
        gate("independent_saturation_matches_partial_state", saturation_consistency <= SAT_TOL, saturation_consistency)

        reconstructed_mass = np.asarray(
            a2e.local_mass(r2, sat_check, pressure_check, p_ref, pore_volume),
            dtype=float,
        )
        cell_error = max_abs(reconstructed_mass - final_mass)
        cell_tol = max(1e-8, 1e-10 * max(float(np.max(base_mass)), 1.0))
        global_rel = abs(float(np.sum(reconstructed_mass) - np.sum(base_mass))) / max(abs(float(np.sum(base_mass))), 1.0)
        gate("independent_cellwise_mass_reconstruction", cell_error <= cell_tol, {"error": cell_error, "tol": cell_tol})
        gate("independent_global_mass_relative_closure", global_rel <= float(a2e.GLOBAL_MASS_REL_TOL), global_rel)
        gate(
            "independent_saturation_bounds",
            float(np.min(sat_check)) >= float(a2e.BACKGROUND) - 1e-12
            and float(np.max(sat_check)) <= float(a2e.INJECTED) + 1e-12,
            [float(np.min(sat_check)), float(np.max(sat_check))],
        )

        # Reconstruct the residual sidecar identity from the partial R5 artifact itself.
        # No CV attribution is invented and no transport state is rewritten.
        gate("residual_Cartesian_sidecar_remains_immutable", sha_array(residual_cartesian) == residual_sha_embedded)

        stage = "safe_numeric_pressure_epoch_serialization"
        producer_arrays = normalize_producer_wi(producer_wi, sg3)
        gate("producer_wi_serialized_without_object_dtype", all(
            np.asarray(v).dtype != object for v in producer_arrays.values()
        ))

        epoch_arrays = {
            "canonical_day": np.asarray(DAY, dtype=np.float64),
            "source_R5_partial_state_sha256": np.asarray(partial_state_sha, dtype="U64"),
            "source_R5_BLOCK_sha256": np.asarray(r5_block_sha, dtype="U64"),
            "refreshed_pressure_psi": np.asarray(pressure_check, dtype=np.float64),
            "reconciled_saturation": np.asarray(sat_check, dtype=np.float64),
            "pressure_compatible_grid_mass_kg": np.asarray(final_mass, dtype=np.float64),
            "reference_gas_pressure_pa": np.asarray(p_ref, dtype=np.float64),
            "Tx_dynamic": np.asarray(tx, dtype=np.float64),
            "Ty_dynamic": np.asarray(ty, dtype=np.float64),
            "Tz_dynamic": np.asarray(tz, dtype=np.float64),
            "lambda_total": np.asarray(mobility["lambda_total"], dtype=np.float64),
            "pressure_reconciliation_sidecar_cv": sidecar_cv,
            "pressure_reconciliation_sidecar_cell": sidecar_cell,
            "pressure_reconciliation_sidecar_mass_kg": sidecar_mass,
            "residual_cartesian_sidecar_sha256": np.asarray(residual_sha_embedded, dtype="U64"),
            "frozen_T1_domain_flat_cell": frozen_domain,
            "physical_time_advanced": np.asarray(False, dtype=np.bool_),
            "Darcy_Pollock_TOF_regenerated": np.asarray(False, dtype=np.bool_),
            **producer_arrays,
        }

        epoch_bytes = deterministic_npz_bytes(epoch_arrays)

        out.mkdir(parents=True, exist_ok=False)
        epoch_name = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_Accepted_Day375_Pressure_Epoch.npz"
        epoch_path_out = out / epoch_name
        epoch_path_out.write_bytes(epoch_bytes)
        epoch_sha = sha(epoch_path_out)

        closure = {
            "milestone": M,
            "status": PASS,
            "closure_type": "technical_artifact_serialization_closure_no_coupled_science_rerun",
            "source_R5_commit": PARENT,
            "source_R5_BLOCK_sha256": r5_block_sha,
            "source_R5_BLOCK_stage": R5_BLOCK_STAGE,
            "source_R5_BLOCK_exception": R5_BLOCK_EXCEPTION,
            "source_R5_partial_pressure_compatible_state_sha256": partial_state_sha,
            "all_required_R5_final_science_gates_PASS": True,
            "independent_final_state_revalidation_PASS": True,
            "serialization_repair": (
                "replace object-dtype producer_wi dictionary serialization with explicit "
                "Unicode/integer/float producer-completion arrays"
            ),
            "R5_coupled_fixed_point_rerun": False,
            "R5_partial_artifact_overwritten": False,
        }

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": (
                "R6R21R4R1R5R1_TECHNICAL_CLOSURE_PASS_DAY375_PRESSURE_REFRESH_"
                "ACCEPTED_R22_DARCY_POLLOCK_TOF_REGENERATION_NEXT"
            ),
            "source_R20_accepted_state_sha256": accepted_sha,
            "source_R5_BLOCK_sha256": r5_block_sha,
            "source_R5_partial_pressure_compatible_state_sha256": partial_state_sha,
            "accepted_pressure_epoch_sha256": epoch_sha,
            "residual_Cartesian_sidecar_sha256": residual_sha_embedded,
            "R5_science_rerun": False,
            "R5_final_science_gates_recovered_from_BLOCK_count": len(REQUIRED_SCIENCE_GATES),
            "independent_pressure_linear_relative_residual": float(linear_residual),
            "independent_pressure_fixed_point_consistency": pressure_consistency,
            "independent_saturation_fixed_point_consistency": saturation_consistency,
            "independent_cellwise_mass_reconstruction_error_kg": cell_error,
            "independent_global_mass_relative_error": global_rel,
            "independent_cell_capacity_max_excess_kg": max_cap_excess,
            "maximum_per_CV_sidecar_residual_kg": max_cv_sidecar,
            "global_sidecar_residual_kg": global_sidecar,
            "producer_completion_count": int(len(producer_arrays["producer_name"])),
            "pressure_refresh_accepted": True,
            "Darcy_Pollock_TOF_regeneration_executed": False,
            "physical_time_advance_executed": False,
            "P3_authorized": False,
        }

        contract = {
            "milestone": M,
            "status": PASS,
            "accepted_Day375_pressure_refresh": True,
            "authority_chain": {
                "accepted_transport_base_R20_sha256": accepted_sha,
                "R5_BLOCK_sha256": r5_block_sha,
                "R5_partial_pressure_compatible_state_sha256": partial_state_sha,
                "R5R1_accepted_pressure_epoch_sha256": epoch_sha,
            },
            "science_closure": {
                "R5_reached_artifact_publication_after_final_science_gates": True,
                "required_final_science_gates_all_PASS": True,
                "independent_final_state_revalidation_PASS": True,
                "coupled_science_rerun": False,
            },
            "split_state": {
                "residual_Cartesian_sidecar_sha256": residual_sha_embedded,
                "residual_Cartesian_sidecar_immutable": True,
                "maximum_per_CV_sidecar_residual_kg": max_cv_sidecar,
                "global_sidecar_residual_kg": global_sidecar,
                "reverse_H1_to_S0_pullback": False,
            },
            "serialization": {
                "object_arrays_present": False,
                "producer_wi_representation": (
                    "producer_name + producer_i/j/k + producer_wi_si + "
                    "producer_wi_reference_si + producer_mobility_scale + producer_re_m"
                ),
            },
            "downstream_firewall": {
                "Darcy_Pollock_TOF_regenerated": False,
                "physical_time_advanced": False,
                "P3_authorized": False,
            },
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": summary["classification"],
            "P2_R6_R22_authorized": True,
            "P2_R6_R22_name": "Controlled Day375 Accepted-State Darcy/Pollock/TOF Regeneration",
            "P2_R6_R22_must_bind_R5R1_pressure_epoch_SHA": True,
            "P2_R6_R22_Darcy_flux_regeneration_authorized": True,
            "P2_R6_R22_Pollock_streamline_regeneration_authorized": True,
            "P2_R6_R22_TOF_regeneration_authorized": True,
            "accepted_Day375_transport_state_remains_authoritative": True,
            "accepted_Day375_pressure_refresh": True,
            "physical_time_advance_authorized": False,
            "transport_time_advance_authorized": False,
            "P3_authorized": False,
            "P4_authorized": False,
            "P5_training_authorized": False,
        }

        (out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_Summary.json").write_bytes(jb(summary))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_Technical_Closure_Contract.json").write_bytes(jb(closure))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_Accepted_Pressure_Refresh_Contract.json").write_bytes(jb(contract))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_Decision_Contract.json").write_bytes(jb(decision))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                manifest_rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_Artifact_Manifest.csv").write_bytes(csvb(manifest_rows))

        print("=" * 190)
        print(M, "PASS")
        print("R5 BLOCK SHA256                            :", r5_block_sha)
        print("R5 partial pressure-compatible state SHA256:", partial_state_sha)
        print("Accepted R5-R1 pressure epoch SHA256       :", epoch_sha)
        print("Required final R5 science gates PASS       :", len(REQUIRED_SCIENCE_GATES))
        print("Coupled science rerun                      : False")
        print("Independent pressure residual              :", linear_residual)
        print("Pressure fixed-point consistency           :", pressure_consistency)
        print("Saturation fixed-point consistency         :", saturation_consistency)
        print("Cell capacity max excess kg                :", max_cap_excess)
        print("Max per-CV / global sidecar residual kg    :", max_cv_sidecar, "/", global_sidecar)
        print("Producer completions serialized numerically:", len(producer_arrays["producer_name"]))
        print("Pressure refresh accepted                  : True")
        print("Darcy/Pollock/TOF regenerated              : False")
        print("Physical time advanced                     : False")
        print("P2-R6-R22 authorized                       : True")
        print("P3 authorized                              : False")
        print("=" * 190)
        return 0

    except Exception as exc:
        block.mkdir(parents=True, exist_ok=True)
        p = block / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": BLOCK,
                "failed_stage": stage,
                "exception": repr(exc),
                "source_R5_BLOCK_preserved": True,
                "source_R5_partial_artifact_preserved": True,
                "coupled_science_rerun_authorized": False,
                "pressure_refresh_accepted": False,
                "Darcy_Pollock_TOF_regeneration_authorized": False,
                "time_advance_authorized": False,
                "P3_authorized": False,
                "gates_completed": gates,
            }))
        print(M, "BLOCKED")
        print("Stage:", stage)
        print("Exception:", repr(exc))
        return 2


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, default=Path("."))
    ap.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        selftest()
        raise SystemExit(0)
    raise SystemExit(main(a.project_root, a.drive_root))
