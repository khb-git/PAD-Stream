#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np


MILESTONE = "POSTV16-AV4-F2-R1"
STATUS_PASS = (
    "AV4F2R1_F2_CV_CAPACITY_SCIENTIFIC_FAIL_PRESERVED_LOCALIZED_"
    "NORMALIZED_TRANSPOSE_PROJECTION_GEOMETRY_AND_CAPACITY_MECHANISM_"
    "DIAGNOSED_NO_REPAIR_SELECTED"
)
STATUS_BLOCKED = "AV4F2R1_FAILURE_LOCALIZATION_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_F2_COMMIT = "3ba411059178c9e6d08cc43c1553e2c4fb6abdfc"

CONTROL_REALIZATION = "AV3CR0003"
CONTROL_POROSITY = "AV2PHI0003"
PARENT_DAY = 365.0

GRID = (15, 50, 50)
NZ, NY, NX = GRID
NCELL = NZ * NY * NX
NSL = 1078
NN = 201
NCV = 200
BACKGROUND = 0.20
INJECTED = 0.80
MAX_SG = 0.60
DAY_TO_S = 86400.0

# --------------------------------------------------------------------------------------------------
# Exact repository authorities.
# --------------------------------------------------------------------------------------------------

F2 = "PAD_Stream_POSTV16_AV4_F2_Controlled_Day365_Conservative_Parent_State_Projection.py"
F2_BLOB = "0f286a834b1cb2306403a9b9fa76b38841a31a11"

F1R2 = (
    "PAD_Stream_POSTV16_AV4_F1_R2_Corrected_Restart_State_and_"
    "Conservative_Parent_Projection_Freeze.py"
)
F1R2_BLOB = "51f86f3591bf66148ef468b304c18fb4fc668e77"

A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"

R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"

SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"

R7R7E = (
    "PAD_Stream_POSTV16_AV1_D_R7_R7E_"
    "Frozen_Horizontal_Face_Halo_Occupancy_Domain_Execution.py"
)
R7R7E_BLOB = "9f99d9dcab649ba7ac911ad09ad79b4e0eb2ecc8"

AV1_R7R1 = "PAD_Stream_POSTV16_AV1_D_R7_R1_E37A_Mapback_Capacity_Failure_Localization.py"
AV1_R7R1_BLOB = "734fe31b3ff3cc6d40c33ebb9b0162b02e99a368"

SOURCE_BLOBS = {
    F2: F2_BLOB,
    F1R2: F1R2_BLOB,
    A2E: A2E_BLOB,
    R2: R2_BLOB,
    E37A: E37A_BLOB,
    SG7D: SG7D_BLOB,
    R7R7E: R7R7E_BLOB,
    AV1_R7R1: AV1_R7R1_BLOB,
}

# --------------------------------------------------------------------------------------------------
# Drive authorities.
# --------------------------------------------------------------------------------------------------

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

F2_FAIL_REL = BASE_AV4 / "POSTV16_AV4_F2_SCIENTIFIC_FAIL_CV_CAPACITY"
F2_FAIL_REPORT = "POSTV16_AV4_F2_Scientific_Fail_Report.json"
F2_FAIL_STATUS = (
    "AV4F2_SCIENTIFIC_FAIL_PROJECTED_CV_COMPONENT_MASS_EXCEEDS_"
    "FROZEN_E37A_CAPACITY_NO_ADAPTATION_OR_AUTOMATIC_RERUN"
)

F2_PASS_REL = BASE_AV4 / "POSTV16_AV4_F2_Controlled_Day365_Conservative_Parent_State_Projection"
F2_PASS_SUMMARY = "PAD_Stream_POSTV16_AV4_F2_Summary.json"

A2E_REL = BASE_AV4 / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_EPOCH = "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_MANIFEST = "POSTV16_AV4_A2_E_Artifact_Manifest.csv"

OUT_REL = BASE_AV4 / "POSTV16_AV4_F2_R1_CV_Capacity_Failure_Localization"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F2_R1_BLOCKED"


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git_text(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


def git_blob(path: Path, root: Path) -> str:
    return git_text(root, "hash-object", str(path))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def verify_manifest(directory: Path, name: str) -> dict[str, str]:
    rows = read_csv(directory / name)
    manifest = {r["file"]: r["sha256"] for r in rows}
    if not manifest:
        raise GateError("manifest_empty:" + name)
    for fn, expected in manifest.items():
        p = directory / fn
        if not p.is_file():
            raise GateError("manifest_missing:" + fn)
        if sha256_file(p) != expected:
            raise GateError("manifest_SHA_mismatch:" + fn)
    return manifest


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError("cannot_load_module:" + str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def json_bytes(obj: Any) -> bytes:
    return (
        json.dumps(obj, indent=2, sort_keys=True, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
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


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        if p.exists() and p.read_bytes() != data:
            raise GateError("existing_output_differs:" + name)
        if not p.exists():
            p.write_bytes(data)


def fsum_array(a: np.ndarray) -> float:
    return float(math.fsum(float(x) for x in np.asarray(a, dtype=np.float64).ravel()))


def percentile_dict(a: np.ndarray) -> dict[str, float]:
    x = np.asarray(a, dtype=np.float64)
    return {
        "min": float(np.min(x)),
        "p01": float(np.percentile(x, 1)),
        "p05": float(np.percentile(x, 5)),
        "p25": float(np.percentile(x, 25)),
        "median": float(np.median(x)),
        "p75": float(np.percentile(x, 75)),
        "p95": float(np.percentile(x, 95)),
        "p99": float(np.percentile(x, 99)),
        "max": float(np.max(x)),
    }


def self_test() -> None:
    parent = np.array([12.0, 8.0], dtype=np.float64)
    cell_pv = np.array([10.0, 4.0], dtype=np.float64)
    flat = np.array([0, 0, 1], dtype=np.int64)
    pv = np.array([1.0, 3.0, 2.0], dtype=np.float64)
    cv = np.array([0, 1, 1], dtype=np.int64)

    denom = np.bincount(flat, weights=pv, minlength=2)
    normalized = parent[flat] * pv / denom[flat]
    occupancy = parent[flat] * pv / cell_pv[flat]

    # Cell 0 coverage is only 40% of physical PV, so normalized-transpose
    # mass is 2.5x the physical-PV sampled mass on every one of its edges.
    ratio = normalized[:2] / occupancy[:2]
    assert np.allclose(ratio, 2.5)

    cv_mass = np.bincount(cv, weights=normalized, minlength=2)
    assert np.allclose(cv_mass, [3.0, 17.0])
    assert abs(np.sum(cv_mass) - np.sum(parent)) < 1.0e-14

    print("POSTV16-AV4-F2-R1 CV-capacity localization self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCK_REL

    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"

    def gate(name: str, passed: Any, value: Any = None) -> None:
        ok = bool(passed)
        gates[name] = {"passed": ok, "value": value}
        print(
            f"[{'PASS' if ok else 'FAIL'}] {name}"
            + (f" — {value}" if value is not None else "")
        )
        if not ok:
            raise GateError(name)

    print("=" * 214)
    print(
        "POSTV16-AV4-F2-R1 — F2 CV-CAPACITY SCIENTIFIC-FAIL "
        "LOCALIZATION / PROJECTION-GEOMETRY AUDIT"
    )
    print("=" * 214)
    print("DIAGNOSTIC ONLY. F2 SCIENTIFIC FAIL REMAINS IMMUTABLE.")
    print("NO REPAIR SELECTED. NO MASS REDISTRIBUTION. NO SUPPORT EXPANSION.")
    print("NO SATURATION-BOUND RELAXATION. NO RESCALING. NO TEACHER. NO MODEL INFERENCE.")
    print("NO PHYSICAL-TIME ADVANCE. NO MAPBACK. NO TRAINING. NO CMG.")
    print()

    try:
        # ------------------------------------------------------------------------------------------
        # Repository/source authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"

        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")
        gate("repository_parent_is_F2_commit", parent == PARENT_F2_COMMIT, parent)
        gate("repository_clean", status == "", repr(status))

        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        # ------------------------------------------------------------------------------------------
        # Bind and preserve formal F2 scientific fail.
        # ------------------------------------------------------------------------------------------
        stage = "F2_scientific_fail_binding"

        fail_path = drive / F2_FAIL_REL / F2_FAIL_REPORT
        gate("F2_scientific_fail_report_present", fail_path.is_file(), str(fail_path))
        f2fail = load_json(fail_path)
        fail_sha = sha256_file(fail_path)

        gate("F2_fail_status_exact", f2fail["status"] == F2_FAIL_STATUS, f2fail["status"])
        gate(
            "F2_fail_stage_exact",
            f2fail["failed_stage"] == "E37A_CV_capacity_and_mass_inversion",
            f2fail["failed_stage"],
        )
        gate(
            "F2_fail_gate_exact",
            f2fail["failed_gate"]
            == "projected_CV_component_mass_within_frozen_E37A_capacity",
            f2fail["failed_gate"],
        )
        detail = f2fail["detail"]
        gate(
            "F2_fail_detail_physically_over_capacity",
            float(detail["maximum_excess_kg"]) > 0.0
            and float(detail["target_mass_kg"]) > float(detail["capacity_kg"])
            and int(detail["worst_streamline"]) == 849
            and int(detail["worst_control_volume"]) == 157,
            detail,
        )
        gate(
            "F2_fail_projection_executed_but_inversion_not_executed",
            f2fail["scientific_execution_started"] is True
            and f2fail["projection_executed"] is True
            and f2fail["CV_mass_inversion_executed"] is False,
        )
        gate(
            "F2_fail_no_adaptation_or_downstream_authority",
            f2fail["support_domain_adaptation_performed"] is False
            and f2fail["F3_authorized"] is False
            and f2fail["A3_E2_authorized"] is False
            and f2fail["AV4_dynamic_transport_execution_authorized"] is False
            and f2fail["automatic_rerun_authorized"] is False,
        )
        gate(
            "no_F2_PASS_summary_published",
            not (drive / F2_PASS_REL / F2_PASS_SUMMARY).exists(),
            str(drive / F2_PASS_REL / F2_PASS_SUMMARY),
        )

        # ------------------------------------------------------------------------------------------
        # Bind A2-E parent epoch and source modules.
        # ------------------------------------------------------------------------------------------
        stage = "parent_epoch_and_module_binding"

        a2 = drive / A2E_REL
        gate("A2E_output_present", a2.is_dir(), str(a2))
        ma2 = verify_manifest(a2, A2E_MANIFEST)
        gate("A2E_epoch_manifested", A2E_EPOCH in ma2, A2E_EPOCH)

        with np.load(a2 / A2E_EPOCH, allow_pickle=False) as z:
            parent_mass = np.asarray(z["parent_component_mass_kg"], dtype=np.float64)
            parent_sat = np.asarray(z["reconciled_saturation"], dtype=np.float64)
            pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            cell_pv = np.asarray(z["pore_volume_m3"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
            tof_s = np.asarray(z["streamline_tof_s"], dtype=np.float64)
            weights_m3_s = np.asarray(z["streamline_weight_m3_s"], dtype=np.float64)

        gate(
            "A2E_shapes_exact_for_localization",
            parent_mass.shape == GRID
            and parent_sat.shape == GRID
            and pressure.shape == GRID
            and cell_pv.shape == GRID
            and xyz.shape == (NSL, NN, 3)
            and tof_s.shape == (NSL, NN)
            and weights_m3_s.shape == (NSL,),
        )

        r2 = load_module(root / R2, "postv16_av4_f2r1_r2")
        e37 = load_module(root / E37A, "postv16_av4_f2r1_e37a")
        sg7d = load_module(root / SG7D, "postv16_av4_f2r1_sg7d")
        r7e = load_module(root / R7R7E, "postv16_av4_f2r1_r7r7e")

        gate(
            "source_modules_exact_functions_present",
            hasattr(sg7d, "build_subsegment_operator")
            and hasattr(e37, "build_control_volume_geometry")
            and hasattr(e37, "cv_mass_from_saturation")
            and hasattr(r7e, "build_extended_halo_graph"),
        )

        # ------------------------------------------------------------------------------------------
        # Reproduce the exact F2 projection and capacity failure.
        # ------------------------------------------------------------------------------------------
        stage = "F2_failure_reproduction"

        operator = sg7d.build_subsegment_operator(
            xyz,
            tof_s / DAY_TO_S,
            weights_m3_s * DAY_TO_S,
        )
        stream = np.asarray(operator["streamline"], dtype=np.int64)
        node = np.asarray(operator["node"], dtype=np.int64)
        flat = np.asarray(operator["flat_cell"], dtype=np.int64)
        pv_sub = np.asarray(operator["pv_m3"], dtype=np.float64)
        cv_id = stream * NCV + node

        graph = r7e.build_extended_halo_graph(operator)
        s0 = np.asarray(graph["s0_nodes"], dtype=np.int64)

        parent_flat = parent_mass.reshape(-1)
        cell_pv_flat = cell_pv.reshape(-1)

        denom = np.bincount(flat, weights=pv_sub, minlength=NCELL)
        gate("S0_positive_coverage", np.all(denom[s0] > 0.0), float(np.min(denom[s0])))

        normalized_sub_mass = parent_flat[flat] * pv_sub / denom[flat]
        cv_mass = np.bincount(
            cv_id,
            weights=normalized_sub_mass,
            minlength=NSL * NCV,
        ).reshape(NSL, NCV)

        geometry = e37.build_control_volume_geometry(
            r2,
            operator,
            pressure,
            p_ref,
            NSL,
            NCV,
        )
        coeff = np.asarray(geometry["cv_pressure_mass_coeff"], dtype=np.float64)
        cv_pv = np.asarray(geometry["cv_pv_m3"], dtype=np.float64)
        capacity = np.asarray(
            e37.cv_mass_from_saturation(
                r2,
                np.full((NSL, NCV), INJECTED, dtype=np.float64),
                coeff,
            ),
            dtype=np.float64,
        )

        excess = cv_mass - capacity
        cap_tol = max(
            1.0e-9,
            1.0e-12 * max(float(np.max(np.abs(cv_mass))), 1.0),
        )
        overload = excess > cap_tol
        overload_count = int(np.sum(overload))
        worst_flat = int(np.argmax(excess))
        worst_sl = worst_flat // NCV
        worst_cv = worst_flat % NCV
        worst_excess = float(excess[worst_sl, worst_cv])
        worst_target = float(cv_mass[worst_sl, worst_cv])
        worst_capacity = float(capacity[worst_sl, worst_cv])

        gate("F2_capacity_failure_reproduced", overload_count > 0, overload_count)
        gate(
            "F2_worst_location_reproduced",
            worst_sl == int(detail["worst_streamline"])
            and worst_cv == int(detail["worst_control_volume"]),
            [worst_sl, worst_cv],
        )
        gate(
            "F2_worst_excess_reproduced",
            abs(worst_excess - float(detail["maximum_excess_kg"]))
            <= max(1.0e-6, 1.0e-10 * abs(float(detail["maximum_excess_kg"]))),
            worst_excess,
        )
        gate(
            "F2_worst_target_and_capacity_reproduced",
            abs(worst_target - float(detail["target_mass_kg"])) <= 1.0e-6
            and abs(worst_capacity - float(detail["capacity_kg"])) <= 1.0e-6,
            {"target": worst_target, "capacity": worst_capacity},
        )

        # ------------------------------------------------------------------------------------------
        # Global vs local capacity diagnosis.
        # ------------------------------------------------------------------------------------------
        stage = "global_local_capacity_diagnosis"

        s0_mass = fsum_array(parent_flat[s0])
        total_cv_capacity = fsum_array(capacity)
        total_projected = fsum_array(cv_mass)
        total_capacity_slack = total_cv_capacity - total_projected
        streamline_mass = np.sum(cv_mass, axis=1)
        streamline_capacity = np.sum(capacity, axis=1)
        overloaded_streamline = streamline_mass > streamline_capacity + cap_tol

        gate(
            "F2_projection_global_mass_equals_S0_mass",
            abs(total_projected - s0_mass)
            <= max(1.0e-8, 1.0e-12 * max(abs(s0_mass), 1.0)),
            total_projected - s0_mass,
        )

        global_capacity_sufficient = total_cv_capacity + cap_tol >= total_projected

        # ------------------------------------------------------------------------------------------
        # Coverage/concentration mechanism.
        # ------------------------------------------------------------------------------------------
        stage = "coverage_concentration_mechanism"

        coverage_ratio = denom[s0] / cell_pv_flat[s0]
        concentration_multiplier = cell_pv_flat[s0] / denom[s0]

        gate(
            "coverage_metrics_positive_finite",
            np.isfinite(coverage_ratio).all()
            and np.isfinite(concentration_multiplier).all()
            and np.all(coverage_ratio > 0.0)
            and np.all(concentration_multiplier > 0.0),
        )

        # Diagnostic comparator only:
        # mass represented by the literal subsegment PV fraction of each physical cell,
        # without renormalizing the represented fraction to 100% of the cell mass.
        occupancy_sub_mass = parent_flat[flat] * pv_sub / cell_pv_flat[flat]
        occupancy_cv_mass = np.bincount(
            cv_id,
            weights=occupancy_sub_mass,
            minlength=NSL * NCV,
        ).reshape(NSL, NCV)
        occupancy_excess = occupancy_cv_mass - capacity
        occupancy_overload_count = int(np.sum(occupancy_excess > cap_tol))
        occupancy_projected_mass = fsum_array(occupancy_cv_mass)

        # Exact identity: for every edge, normalized/occupancy mass ratio is cellPV/Wc,
        # excluding zero-parent-mass edges where both masses are zero.
        active_edges = occupancy_sub_mass > 0.0
        edge_ratio_error = 0.0
        if np.any(active_edges):
            observed_ratio = (
                normalized_sub_mass[active_edges]
                / occupancy_sub_mass[active_edges]
            )
            expected_ratio = (
                cell_pv_flat[flat[active_edges]]
                / denom[flat[active_edges]]
            )
            edge_ratio_error = float(
                np.max(np.abs(observed_ratio - expected_ratio))
            )
        gate(
            "normalized_to_physicalPV_sampling_ratio_identity",
            edge_ratio_error <= 1.0e-10,
            edge_ratio_error,
        )

        # ------------------------------------------------------------------------------------------
        # Worst-CV contributor localization.
        # ------------------------------------------------------------------------------------------
        stage = "worst_CV_contributor_localization"

        worst_mask = cv_id == worst_flat
        worst_cells = np.unique(flat[worst_mask])
        contributor_rows: list[dict[str, Any]] = []

        for cell in worst_cells:
            m = worst_mask & (flat == cell)
            assigned = fsum_array(normalized_sub_mass[m])
            occupancy_assigned = fsum_array(occupancy_sub_mass[m])
            k = int(cell // (NY * NX))
            rem = int(cell % (NY * NX))
            j = int(rem // NX)
            i = int(rem % NX)
            contributor_rows.append(
                {
                    "flat_cell": int(cell),
                    "k": k,
                    "j": j,
                    "i": i,
                    "parent_cell_mass_kg": float(parent_flat[cell]),
                    "parent_cell_saturation": float(parent_sat.reshape(-1)[cell]),
                    "physical_cell_pore_volume_m3": float(cell_pv_flat[cell]),
                    "SG7D_total_subsegment_PV_in_cell_m3": float(denom[cell]),
                    "coverage_to_physical_PV_ratio": float(denom[cell] / cell_pv_flat[cell]),
                    "normalized_transpose_concentration_multiplier": float(cell_pv_flat[cell] / denom[cell]),
                    "mass_assigned_to_worst_CV_kg": assigned,
                    "mass_assigned_to_worst_CV_fraction_of_target": assigned / max(worst_target, 1.0e-300),
                    "physicalPV_sampled_mass_to_worst_CV_kg": occupancy_assigned,
                    "subsegment_count_to_worst_CV": int(np.sum(m)),
                }
            )

        contributor_rows.sort(
            key=lambda r: float(r["mass_assigned_to_worst_CV_kg"]),
            reverse=True,
        )

        top_contributor_fraction = (
            float(contributor_rows[0]["mass_assigned_to_worst_CV_fraction_of_target"])
            if contributor_rows
            else 0.0
        )

        # ------------------------------------------------------------------------------------------
        # All overloaded CV audit.
        # ------------------------------------------------------------------------------------------
        stage = "overloaded_CV_population_audit"

        overloaded_rows: list[dict[str, Any]] = []
        inds = np.argwhere(overload)
        order = sorted(
            inds.tolist(),
            key=lambda q: float(excess[int(q[0]), int(q[1])]),
            reverse=True,
        )

        subcount_cv = np.bincount(
            cv_id,
            minlength=NSL * NCV,
        ).reshape(NSL, NCV)

        # Unique source-cell counts for overloaded CVs only.
        for sl, cvn in order:
            sl = int(sl)
            cvn = int(cvn)
            fid = sl * NCV + cvn
            mask = cv_id == fid
            cells = np.unique(flat[mask])
            overloaded_rows.append(
                {
                    "streamline": sl,
                    "control_volume": cvn,
                    "target_mass_kg": float(cv_mass[sl, cvn]),
                    "capacity_kg": float(capacity[sl, cvn]),
                    "excess_kg": float(excess[sl, cvn]),
                    "target_to_capacity_ratio": float(
                        cv_mass[sl, cvn] / max(capacity[sl, cvn], 1.0e-300)
                    ),
                    "CV_pore_volume_m3": float(cv_pv[sl, cvn]),
                    "subsegment_count": int(subcount_cv[sl, cvn]),
                    "unique_source_cell_count": int(len(cells)),
                    "physicalPV_sampled_target_mass_kg": float(
                        occupancy_cv_mass[sl, cvn]
                    ),
                    "physicalPV_sampled_capacity_excess_kg": float(
                        occupancy_excess[sl, cvn]
                    ),
                }
            )

        # ------------------------------------------------------------------------------------------
        # Mechanism classification — diagnostic evidence, no repair selection.
        # ------------------------------------------------------------------------------------------
        stage = "mechanism_classification"

        worst_ratio = worst_target / max(worst_capacity, 1.0e-300)
        undercovered_s0_cells = int(np.sum(coverage_ratio < 1.0 - 1.0e-12))
        overcovered_s0_cells = int(np.sum(coverage_ratio > 1.0 + 1.0e-12))
        unitcovered_s0_cells = int(len(s0) - undercovered_s0_cells - overcovered_s0_cells)

        worst_contrib_multipliers = np.array(
            [
                float(r["normalized_transpose_concentration_multiplier"])
                for r in contributor_rows
                if float(r["parent_cell_mass_kg"]) > 0.0
            ],
            dtype=np.float64,
        )

        evidence = {
            "milestone": MILESTONE,
            "F2_fail_report_sha256": fail_sha,
            "F2_failure_preserved": True,
            "overloaded_CV_count": overload_count,
            "worst_CV": {
                "streamline": worst_sl,
                "control_volume": worst_cv,
                "target_mass_kg": worst_target,
                "capacity_kg": worst_capacity,
                "excess_kg": worst_excess,
                "target_to_capacity_ratio": worst_ratio,
                "unique_source_cell_count": int(len(worst_cells)),
                "largest_single_cell_contribution_fraction": top_contributor_fraction,
            },
            "global_capacity": {
                "S0_parent_mass_kg": s0_mass,
                "total_projected_CV_mass_kg": total_projected,
                "total_CV_capacity_kg": total_cv_capacity,
                "total_capacity_slack_kg": total_capacity_slack,
                "total_capacity_sufficient_for_total_S0_mass": global_capacity_sufficient,
                "streamlines_with_aggregate_mass_over_capacity": int(np.sum(overloaded_streamline)),
            },
            "S0_coverage": {
                "S0_cell_count": int(len(s0)),
                "undercovered_vs_physical_cell_PV_count": undercovered_s0_cells,
                "approximately_unit_covered_count": unitcovered_s0_cells,
                "overcovered_vs_physical_cell_PV_count": overcovered_s0_cells,
                "coverage_ratio_Wc_over_cellPV": percentile_dict(coverage_ratio),
                "concentration_multiplier_cellPV_over_Wc": percentile_dict(concentration_multiplier),
            },
            "worst_CV_contributor_concentration_multiplier": (
                percentile_dict(worst_contrib_multipliers)
                if len(worst_contrib_multipliers)
                else None
            ),
            "diagnostic_physicalPV_sampling_comparator": {
                "accepted_projection": False,
                "repair_selected": False,
                "definition": "m_q_diag = M_parent[cell] * PV_q / physical_cell_PV",
                "projected_mass_kg": occupancy_projected_mass,
                "fraction_of_S0_parent_mass": occupancy_projected_mass / max(s0_mass, 1.0e-300),
                "overloaded_CV_count": occupancy_overload_count,
                "purpose": (
                    "diagnose the concentration introduced specifically by F2 normalization; "
                    "this comparator is not a frozen or authorized replacement operator"
                ),
            },
            "mechanism_interpretation": {
                "mass_conservation_failure": False,
                "A2E_parent_state_failure": False,
                "SG7D_geometry_failure": False,
                "E37A_capacity_definition_failure": False,
                "F2_normalized_transpose_local_capacity_incompatibility": True,
                "global_capacity_shortage_proven": not global_capacity_sufficient,
                "local_assignment_incompatibility_proven": overload_count > 0,
                "candidate_mechanism_to_test_in_next_design": (
                    "F2 normalizes each S0 cell's represented SG7D subsegment pore volume W_c "
                    "to 100% of that Cartesian cell's parent mass. Where W_c is smaller than the "
                    "physical cell pore volume, the edge mass density is multiplied by cellPV/W_c. "
                    "Multiple contributing cells may then aggregate into a single CV, producing a "
                    "capacity-infeasible parent CV state. This audit localizes those factors but "
                    "does not select a repair."
                ),
            },
        }

        # ------------------------------------------------------------------------------------------
        # Prospectively authorize design-only next step.
        # ------------------------------------------------------------------------------------------
        handoff = {
            "milestone": "POSTV16-AV4-F2-R2",
            "name": "Prospective Capacity-Feasible Parent-State Projection Design Freeze",
            "authorized": True,
            "execution": False,
            "purpose": (
                "design and freeze, without executing, a capacity-feasible conservative "
                "grid-to-refreshed-streamline parent-state representation informed by F2-R1"
            ),
            "must_preserve": [
                "F2 scientific FAIL as immutable",
                "A2-E exact Cartesian parent component mass as global recurrent authority",
                "E37A physical CV saturation/capacity bounds",
                "R7D no-reverse-halo semantics",
                "exact global component-mass ledger",
                "no clipping, no global rescaling, no saturation-bound relaxation",
                "no arbitrary residual-mass threshold",
            ],
            "questions_R2_must_resolve_before_execution": [
                "whether mass not represented by physical streamline-tube pore volume remains residual even inside S0",
                "how overlapping SG7D tube occupancy is reconciled without duplicating physical pore volume",
                "whether a bounded bipartite cell-to-CV allocation is required",
                "whether current refreshed CV support has sufficient feasible capacity under connectivity constraints",
                "how the residual-grid state couples to future restart transport",
            ],
            "F2_repair_execution_authorized": False,
            "F3_authorized": False,
            "teacher_execution_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "F2_scientific_FAIL_preserved": True,
            "failure_localized": True,
            "repair_selected": False,
            "support_domain_changed": False,
            "mass_redistributed": False,
            "saturation_bound_changed": False,
            "global_rescaling_performed": False,
            "teacher_transport_performed": False,
            "checkpoint_inference_performed": False,
            "physical_time_advanced": False,
            "F2R2_design_freeze_authorized": True,
            "F2R2_execution_authorized": False,
            "F3_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "F2_fail_report_sha256": fail_sha,
            "overloaded_CV_count": overload_count,
            "worst_streamline": worst_sl,
            "worst_control_volume": worst_cv,
            "worst_target_mass_kg": worst_target,
            "worst_capacity_kg": worst_capacity,
            "worst_excess_kg": worst_excess,
            "worst_target_to_capacity_ratio": worst_ratio,
            "global_CV_capacity_sufficient_for_total_S0_mass": global_capacity_sufficient,
            "total_CV_capacity_slack_kg": total_capacity_slack,
            "physicalPV_sampling_comparator_overloaded_CV_count": occupancy_overload_count,
            "repair_selected": False,
            "F2R2_design_freeze_authorized": True,
            "F3_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        output_files = {
            "PAD_Stream_POSTV16_AV4_F2_R1_Summary.json":
                json_bytes(summary),
            "POSTV16_AV4_F2_R1_F2_Failure_Preservation.json":
                json_bytes({
                    "F2_fail_report": str(fail_path),
                    "F2_fail_report_sha256": fail_sha,
                    "status": f2fail["status"],
                    "failed_stage": f2fail["failed_stage"],
                    "failed_gate": f2fail["failed_gate"],
                    "detail": detail,
                }),
            "POSTV16_AV4_F2_R1_Capacity_Mechanism_Diagnosis.json":
                json_bytes(evidence),
            "POSTV16_AV4_F2_R1_Overloaded_CV_Audit.csv":
                csv_bytes(overloaded_rows),
            "POSTV16_AV4_F2_R1_Worst_CV_Contributor_Cells.csv":
                csv_bytes(contributor_rows),
            "POSTV16_AV4_F2_R1_F2R2_Design_Handoff_Contract.json":
                json_bytes(handoff),
            "POSTV16_AV4_F2_R1_Decision_Contract.json":
                json_bytes(decision),
            "POSTV16_AV4_F2_R1_Final_Gate_Matrix.csv":
                csv_bytes(
                    [{"gate": name, **value} for name, value in gates.items()]
                ),
        }

        immutable_publish(out, output_files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV4_F2_R1_Artifact_Manifest.csv":
                manifest_rows.append(
                    {
                        "file": p.name,
                        "sha256": sha256_file(p),
                        "bytes": p.stat().st_size,
                    }
                )
        immutable_publish(
            out,
            {
                "POSTV16_AV4_F2_R1_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print()
        print("=" * 214)
        print(f"{MILESTONE}: CV-CAPACITY FAILURE LOCALIZATION PASS")
        print("=" * 214)
        print("F2 scientific FAIL                         : PRESERVED")
        print("Overloaded CV count                        :", overload_count)
        print("Worst CV                                   :", worst_sl, "/", worst_cv)
        print("Worst target / capacity kg                 :", worst_target, "/", worst_capacity)
        print("Worst target-to-capacity ratio             :", worst_ratio)
        print("Total S0 projected mass kg                 :", total_projected)
        print("Total CV capacity kg                       :", total_cv_capacity)
        print("Global CV capacity sufficient              :", global_capacity_sufficient)
        print("Streamlines aggregate-over-capacity        :", int(np.sum(overloaded_streamline)))
        print("S0 cells Wc < physical cell PV             :", undercovered_s0_cells, "/", len(s0))
        print("Physical-PV diagnostic overload count      :", occupancy_overload_count)
        print("Repair selected                            : False")
        print("POSTV16-AV4-F2-R2 design freeze            : AUTHORIZED")
        print("F2-R2 repair execution                     : NOT AUTHORIZED")
        print("F3 / A3-E2 / dynamic transport             : NOT AUTHORIZED")
        print("=" * 214)

        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "F2_scientific_FAIL_preserved": True,
            "repair_selected": False,
            "support_domain_changed": False,
            "mass_redistributed": False,
            "physical_time_advanced": False,
            "F2R2_authorized": False,
            "F3_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
            "automatic_rerun_authorized": False,
        }
        data = json_bytes(report)
        p = blocked / "POSTV16_AV4_F2_R1_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            suffix = hashlib.sha256(data).hexdigest()[:12]
            p = blocked / f"POSTV16_AV4_F2_R1_Blocked_Report_{suffix}.json"
        if not p.exists():
            p.write_bytes(data)

        print()
        print("=" * 214)
        print(f"{MILESTONE}: TECHNICAL / AUTHORITY BLOCK")
        print("=" * 214)
        print("Stage    :", stage)
        print("Exception:", repr(exc))
        print("F2 scientific FAIL remains immutable.")
        print("NO REPAIR / RERUN AUTHORIZED.")
        print("=" * 214)
        return 2


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", type=Path, default=Path("."))
    p.add_argument(
        "--drive-root",
        type=Path,
        default=Path("/content/drive/MyDrive/PAD_Stream_Compute"),
    )
    p.add_argument("--self-test", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root))
