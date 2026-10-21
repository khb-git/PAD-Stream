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
import zipfile
from pathlib import Path
from typing import Any

import numpy as np


MILESTONE = "POSTV16-AV4-F2-R3"
PROTOCOL_ID = (
    "POSTV16_AV4_F2_R3_CONTROLLED_BOUNDED_PHYSICAL_OCCUPANCY_"
    "SPLIT_STATE_PARENT_PROJECTION_EXECUTION_V1"
)

STATUS_PASS = (
    "AV4F2R3_BOUNDED_PHYSICAL_OCCUPANCY_SPLIT_STATE_PARENT_PROJECTION_"
    "EXECUTION_PASS_CAPACITY_FEASIBLE_E37A_INVERSION_PASS_NO_TIME_ADVANCE"
)
STATUS_FAIL = (
    "AV4F2R3_SCIENTIFIC_FAIL_BOUNDED_PHYSICAL_OCCUPANCY_PARENT_"
    "PROJECTION_NOT_CAPACITY_FEASIBLE_NO_ADAPTATION_OR_AUTOMATIC_RERUN"
)
STATUS_BLOCKED = "AV4F2R3_TECHNICAL_EXECUTION_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_F2R2_COMMIT = "446857808850d421eab58b252d362cbe145d6691"

CONTROL_REALIZATION = "AV3CR0003"
CONTROL_POROSITY = "AV2PHI0003"
PARENT_DAY = 365.0
FIRST_CANDIDATE_TARGET_DAY = 500.0
FIRST_CANDIDATE_DELTA_DAY = 135.0

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
# Exact repository source authorities.
# --------------------------------------------------------------------------------------------------

F2R2 = "PAD_Stream_POSTV16_AV4_F2_R2_Bounded_Physical_Occupancy_Projection_Freeze.py"
F2R2_BLOB = "4cb29b3dd5a44e50434ec86c1cc9c26a986e367c"

F2R1 = "PAD_Stream_POSTV16_AV4_F2_R1_CV_Capacity_Failure_Localization.py"
F2R1_BLOB = "f8cb7c9ed63fa4610f3c24e7fed8f17bbaf5f14a"

F2 = "PAD_Stream_POSTV16_AV4_F2_Controlled_Day365_Conservative_Parent_State_Projection.py"
F2_BLOB = "0f286a834b1cb2306403a9b9fa76b38841a31a11"

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

SOURCE_BLOBS = {
    F2R2: F2R2_BLOB,
    F2R1: F2R1_BLOB,
    F2: F2_BLOB,
    A2E: A2E_BLOB,
    R2: R2_BLOB,
    E37A: E37A_BLOB,
    SG7D: SG7D_BLOB,
    R7R7E: R7R7E_BLOB,
}

# --------------------------------------------------------------------------------------------------
# Formal Drive authorities.
# --------------------------------------------------------------------------------------------------

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

F2R2_REL = BASE_AV4 / "POSTV16_AV4_F2_R2_Bounded_Physical_Occupancy_Projection_Freeze"
F2R2_SUMMARY = "PAD_Stream_POSTV16_AV4_F2_R2_Summary.json"
F2R2_PROTOCOL = "POSTV16_AV4_F2_R2_Bounded_Physical_Occupancy_Projection_Protocol.json"
F2R2_ARCH = "POSTV16_AV4_F2_R2_Restart_State_Architecture_Contract.json"
F2R2_HANDOFF = "POSTV16_AV4_F2_R2_F2R3_Execution_Handoff_Contract.json"
F2R2_DECISION = "POSTV16_AV4_F2_R2_Decision_Contract.json"
F2R2_MANIFEST = "POSTV16_AV4_F2_R2_Artifact_Manifest.csv"
F2R2_STATUS = (
    "AV4F2R2_F2R1_CAPACITY_LOCALIZATION_BOUND_SINGLE_BOUNDED_PHYSICAL_"
    "OCCUPANCY_SPLIT_STATE_PARENT_PROJECTION_PROSPECTIVELY_FROZEN_"
    "NO_REPAIR_EXECUTION"
)

A2E_REL = BASE_AV4 / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_SUMMARY = "PAD_Stream_POSTV16_AV4_A2_E_Summary.json"
A2E_EPOCH = "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_MANIFEST = "POSTV16_AV4_A2_E_Artifact_Manifest.csv"
A2E_STATUS = (
    "AV4A2E_AV3CR0003_DAY365_SAME_TIME_SPATIAL_MOBILITY_PRESSURE_SATURATION_"
    "REFRESH_DARCY_POLLOCK_TOF_GEOMETRY_EXECUTION_PASS"
)

OUT_REL = BASE_AV4 / "POSTV16_AV4_F2_R3_Bounded_Physical_Occupancy_Projection_Execution"
FAIL_REL = BASE_AV4 / "POSTV16_AV4_F2_R3_SCIENTIFIC_FAIL"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F2_R3_BLOCKED"


class GateError(RuntimeError):
    pass


class ScientificFail(RuntimeError):
    def __init__(self, gate: str, detail: Any = None):
        super().__init__(gate)
        self.gate = gate
        self.detail = detail


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


def deterministic_npz_bytes(arrays: dict[str, Any]) -> bytes:
    outer = io.BytesIO()
    with zipfile.ZipFile(
        outer,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as zf:
        for key in sorted(arrays):
            b = io.BytesIO()
            np.save(b, np.asarray(arrays[key]), allow_pickle=False)
            info = zipfile.ZipInfo(
                f"{key}.npy",
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, b.getvalue())
    return outer.getvalue()


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


def relative_l2(a: np.ndarray, b: np.ndarray) -> float:
    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)
    return float(
        np.linalg.norm((aa - bb).ravel())
        / max(float(np.linalg.norm(bb.ravel())), 1.0e-30)
    )


def self_test() -> None:
    parent = np.asarray([12.0, 8.0, 5.0], dtype=np.float64)
    cell_pv = np.asarray([10.0, 4.0, 7.0], dtype=np.float64)
    flat = np.asarray([0, 0, 1, 1], dtype=np.int64)
    pv_q = np.asarray([1.0, 3.0, 2.0, 4.0], dtype=np.float64)
    cv_id = np.asarray([0, 1, 1, 2], dtype=np.int64)

    W = np.bincount(flat, weights=pv_q, minlength=3)
    denom = np.maximum(cell_pv, W)
    sub_mass = parent[flat] * pv_q / denom[flat]
    mapped = np.bincount(flat, weights=sub_mass, minlength=3)
    alpha = np.minimum(1.0, W / cell_pv)
    expected = parent * alpha
    residual = parent - expected
    cv_mass = np.bincount(cv_id, weights=sub_mass, minlength=3)

    assert np.allclose(W, [4.0, 6.0, 0.0])
    assert np.allclose(mapped, [4.8, 8.0, 0.0])
    assert np.allclose(mapped, expected)
    assert np.allclose(residual, [7.2, 0.0, 5.0])
    assert np.all(residual >= 0.0)
    assert abs(float(np.sum(cv_mass)) + float(np.sum(residual)) - float(np.sum(parent))) < 1.0e-14

    diag = parent[flat] * pv_q / cell_pv[flat]
    assert np.all(sub_mass <= diag + 1.0e-14)

    print(
        "POSTV16-AV4-F2-R3 bounded physical-occupancy projection "
        "execution self-test: PASS"
    )


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()

    out = drive / OUT_REL
    failed = drive / FAIL_REL
    blocked = drive / BLOCK_REL

    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"
    projection_executed = False
    cv_inversion_executed = False

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
        "POSTV16-AV4-F2-R3 — CONTROLLED BOUNDED PHYSICAL-OCCUPANCY "
        "SPLIT-STATE PARENT-PROJECTION EXECUTION"
    )
    print("=" * 214)
    print("EXECUTE ONLY THE SINGLE F2-R2-FROZEN OPERATOR.")
    print("NO ALTERNATE CANDIDATE. NO REPAIR SEARCH. NO LP. NO SUPPORT EXPANSION.")
    print("NO CLIPPING. NO GLOBAL RESCALING. NO SATURATION-BOUND RELAXATION.")
    print("NO TEACHER. NO MODEL LOAD/INFERENCE. NO PHYSICAL-TIME ADVANCE.")
    print("NO FUTURE-STATE PREDICTION. NO FUTURE MAPBACK. NO TRAINING. NO CMG.")
    print()

    try:
        # ------------------------------------------------------------------------------------------
        # Repository authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"

        parent_commit = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")
        gate(
            "repository_parent_is_F2R2_commit",
            parent_commit == PARENT_F2R2_COMMIT,
            parent_commit,
        )
        gate("repository_clean", status == "", repr(status))

        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(
                f"{Path(fn).stem}_git_blob_exact",
                actual == expected,
                actual,
            )

        # ------------------------------------------------------------------------------------------
        # Bind formal F2-R2 protocol PASS / single-candidate handoff.
        # ------------------------------------------------------------------------------------------
        stage = "F2R2_protocol_binding"

        f2r2 = drive / F2R2_REL
        gate("F2R2_output_present", f2r2.is_dir(), str(f2r2))
        mf2r2 = verify_manifest(f2r2, F2R2_MANIFEST)
        gate("F2R2_manifest_exact_6", len(mf2r2) == 6, len(mf2r2))

        sf2r2 = load_json(f2r2 / F2R2_SUMMARY)
        pf2r2 = load_json(f2r2 / F2R2_PROTOCOL)
        af2r2 = load_json(f2r2 / F2R2_ARCH)
        hf2r2 = load_json(f2r2 / F2R2_HANDOFF)
        df2r2 = load_json(f2r2 / F2R2_DECISION)

        gate(
            "F2R2_status_exact",
            sf2r2["status"] == F2R2_STATUS,
            sf2r2["status"],
        )
        gate(
            "F2R2_single_candidate_operator_exact",
            int(pf2r2["candidate_count"]) == 1
            and pf2r2["bounded_projection"]["denominator"]
            == "D_c = max(PV_cell_c, W_c)"
            and pf2r2["bounded_projection"]["subsegment_mass"]
            == "m_q = M_parent[c(q)] * PV_q / D_c"
            and pf2r2["bounded_projection"]["cell_to_streamline_mass"]
            == "M_SL,c = M_parent,c * W_c / max(PV_cell_c, W_c)"
            and pf2r2["residual_grid_state"]["cell_residual"]
            == "R_c = M_parent,c - M_SL,c",
        )
        gate(
            "F2R2_capacity_monotonicity_evidence_exact",
            pf2r2[
                "capacity_monotonicity_relative_to_F2R1_diagnostic"
            ]["F2R1_diagnostic_overloaded_CV_count"] == 0
            and pf2r2[
                "capacity_monotonicity_relative_to_F2R1_diagnostic"
            ]["CV_mass_relation"]
            == "M_CV,r <= M_CV,r_diag elementwise for every CV",
        )
        gate(
            "F2R2_split_state_architecture_exact",
            af2r2["authoritative_global_state"]["role"]
            == "global recurrent physical authority"
            and af2r2["derived_transport_state"]["component_mass_CV"]
            == [NSL, NCV]
            and af2r2["residual_state"]["component_mass_grid_residual"]
            == list(GRID)
            and af2r2["residual_state"]["may_exist_inside_S0"] is True
            and af2r2["neural_input_dimension_frozen"] is False,
        )
        gate(
            "F2R2_F2R3_handoff_exact",
            hf2r2["milestone"] == MILESTONE
            and hf2r2["authorized"] is True
            and hf2r2["single_candidate_only"] is True
            and hf2r2["required_operator"]
            == "m_q = M_parent[c(q)] * PV_q / max(PV_cell_c, W_c)"
            and hf2r2["repair_search_authorized"] is False
            and hf2r2["alternate_candidate_authorized"] is False,
            hf2r2,
        )
        gate(
            "F2R2_downstream_firewalls_before_R3",
            df2r2["F2R3_authorized"] is True
            and df2r2["F2R3_execution_authorized"] is True
            and df2r2["F3_authorized"] is False
            and df2r2["A3_E2_authorized"] is False
            and df2r2["AV4_dynamic_transport_execution_authorized"] is False
            and df2r2["repair_execution_performed"] is False,
        )

        # ------------------------------------------------------------------------------------------
        # Bind exact A2-E Day365 parent epoch.
        # ------------------------------------------------------------------------------------------
        stage = "A2E_parent_epoch_binding"

        a2 = drive / A2E_REL
        gate("A2E_output_present", a2.is_dir(), str(a2))
        ma2 = verify_manifest(a2, A2E_MANIFEST)
        gate("A2E_manifest_exact_12", len(ma2) == 12, len(ma2))
        gate("A2E_epoch_manifested", A2E_EPOCH in ma2, A2E_EPOCH)

        sa2 = load_json(a2 / A2E_SUMMARY)
        gate("A2E_status_exact", sa2["status"] == A2E_STATUS, sa2["status"])
        gate(
            "A2E_control_case_exact",
            sa2["control_realization"] == CONTROL_REALIZATION
            and sa2["paired_porosity"] == CONTROL_POROSITY
            and float(sa2["canonical_day"]) == PARENT_DAY,
        )
        gate(
            "A2E_no_time_advance_or_checkpoint_reuse",
            sa2["PI_RNN_inference"] is False
            and sa2["physical_time_advance"] is False
            and sa2["AV3_checkpoint_committed_reuse"] is False,
        )

        with np.load(a2 / A2E_EPOCH, allow_pickle=False) as z:
            keys = set(z.files)
            parent_mass = np.asarray(z["parent_component_mass_kg"], dtype=np.float64)
            parent_sat = np.asarray(z["reconciled_saturation"], dtype=np.float64)
            pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            cell_pv = np.asarray(z["pore_volume_m3"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
            tof_s = np.asarray(z["streamline_tof_s"], dtype=np.float64)
            weights_m3_s = np.asarray(z["streamline_weight_m3_s"], dtype=np.float64)
            canonical_day = float(np.asarray(z["canonical_day"]).reshape(()))

        required = {
            "parent_component_mass_kg",
            "reconciled_saturation",
            "refreshed_pressure_psi",
            "pore_volume_m3",
            "reference_gas_pressure_pa",
            "streamline_xyz_m",
            "streamline_tof_s",
            "streamline_weight_m3_s",
            "canonical_day",
        }
        gate("A2E_required_arrays_present", required.issubset(keys), sorted(required))
        gate(
            "A2E_shapes_exact",
            parent_mass.shape == GRID
            and parent_sat.shape == GRID
            and pressure.shape == GRID
            and cell_pv.shape == GRID
            and xyz.shape == (NSL, NN, 3)
            and tof_s.shape == (NSL, NN)
            and weights_m3_s.shape == (NSL,),
        )
        gate(
            "A2E_arrays_finite",
            all(
                np.isfinite(a).all()
                for a in [
                    parent_mass,
                    parent_sat,
                    pressure,
                    cell_pv,
                    xyz,
                    tof_s,
                    weights_m3_s,
                ]
            )
            and np.isfinite(p_ref),
        )
        gate(
            "A2E_parent_mass_nonnegative",
            float(np.min(parent_mass)) >= -1.0e-12,
            float(np.min(parent_mass)),
        )
        gate(
            "A2E_parent_saturation_bounds",
            float(np.min(parent_sat)) >= BACKGROUND - 1.0e-12
            and float(np.max(parent_sat)) <= INJECTED + 1.0e-12,
            [float(np.min(parent_sat)), float(np.max(parent_sat))],
        )
        gate(
            "A2E_cell_pore_volume_positive",
            np.all(cell_pv > 0.0),
            [float(np.min(cell_pv)), float(np.max(cell_pv))],
        )
        gate("A2E_parent_day_exact", canonical_day == PARENT_DAY, canonical_day)

        # ------------------------------------------------------------------------------------------
        # Bind source-authentic EOS / CV / SG7D / support modules.
        # ------------------------------------------------------------------------------------------
        stage = "source_module_binding"

        r2 = load_module(root / R2, "postv16_av4_f2r3_r2")
        e37 = load_module(root / E37A, "postv16_av4_f2r3_e37a")
        sg7d = load_module(root / SG7D, "postv16_av4_f2r3_sg7d")
        r7e = load_module(root / R7R7E, "postv16_av4_f2r3_r7r7e")

        gate(
            "source_modules_exact_functions_present",
            hasattr(r2, "gas_density_from_state")
            and hasattr(e37, "build_control_volume_geometry")
            and hasattr(e37, "cv_mass_from_saturation")
            and hasattr(e37, "invert_cv_mass_to_saturation")
            and hasattr(sg7d, "build_subsegment_operator")
            and hasattr(r7e, "build_extended_halo_graph"),
        )

        # ------------------------------------------------------------------------------------------
        # Same-time parent mass/saturation consistency.
        # ------------------------------------------------------------------------------------------
        stage = "parent_mass_saturation_consistency"

        parent_total = fsum_array(parent_mass)
        gate("A2E_parent_total_mass_positive", parent_total > 0.0, parent_total)
        mass_tol = max(1.0e-8, 1.0e-12 * max(abs(parent_total), 1.0))

        sg_parent = np.clip(parent_sat - BACKGROUND, 0.0, MAX_SG)
        rho_parent = np.asarray(
            r2.gas_density_from_state(parent_sat, pressure, p_ref),
            dtype=np.float64,
        )
        reconstructed_parent_mass = cell_pv * rho_parent * sg_parent

        parent_rel_l2 = relative_l2(reconstructed_parent_mass, parent_mass)
        parent_global_residual = (
            fsum_array(reconstructed_parent_mass) - parent_total
        )
        gate(
            "A2E_reconciled_saturation_parent_mass_relative_L2",
            parent_rel_l2 <= 1.0e-10,
            parent_rel_l2,
        )
        gate(
            "A2E_reconciled_saturation_global_mass_closure",
            abs(parent_global_residual) <= mass_tol,
            {
                "residual_kg": parent_global_residual,
                "tolerance_kg": mass_tol,
            },
        )

        # ------------------------------------------------------------------------------------------
        # Rebuild exact refreshed SG7D operator and S0/H1/D1 diagnostics.
        # ------------------------------------------------------------------------------------------
        stage = "refreshed_operator_reconstruction"

        operator = sg7d.build_subsegment_operator(
            xyz,
            tof_s / DAY_TO_S,
            weights_m3_s * DAY_TO_S,
        )
        stream = np.asarray(operator["streamline"], dtype=np.int64)
        node = np.asarray(operator["node"], dtype=np.int64)
        flat = np.asarray(operator["flat_cell"], dtype=np.int64)
        pv_q = np.asarray(operator["pv_m3"], dtype=np.float64)
        cv_id = stream * NCV + node

        gate(
            "SG7D_operator_exact_shapes_and_bounds",
            len(flat) > 0
            and len(stream) == len(flat)
            and len(node) == len(flat)
            and len(pv_q) == len(flat)
            and np.isfinite(pv_q).all()
            and np.all(pv_q > 0.0)
            and int(np.min(stream)) == 0
            and int(np.max(stream)) == NSL - 1
            and int(np.min(node)) == 0
            and int(np.max(node)) == NCV - 1
            and int(np.min(flat)) >= 0
            and int(np.max(flat)) < NCELL,
            len(flat),
        )

        graph = r7e.build_extended_halo_graph(operator)
        s0 = np.asarray(graph["s0_nodes"], dtype=np.int64)
        h1 = np.asarray(graph["h1_nodes"], dtype=np.int64)
        d1 = np.asarray(graph["nodes"], dtype=np.int64)
        exact_s0 = np.unique(flat)

        gate("S0_exact_operator_support", np.array_equal(s0, exact_s0), len(s0))
        gate(
            "H1_disjoint_from_S0",
            len(np.intersect1d(s0, h1, assume_unique=True)) == 0,
            len(h1),
        )
        gate(
            "D1_exact_S0_H1_union",
            np.array_equal(np.sort(d1), np.sort(np.concatenate([s0, h1]))),
            len(d1),
        )

        # ------------------------------------------------------------------------------------------
        # Execute exactly one F2-R2 frozen bounded-occupancy operator.
        # ------------------------------------------------------------------------------------------
        stage = "bounded_physical_occupancy_projection"

        parent_flat = parent_mass.reshape(-1)
        cell_pv_flat = cell_pv.reshape(-1)

        W = np.bincount(flat, weights=pv_q, minlength=NCELL)
        denom = np.maximum(cell_pv_flat, W)
        gate(
            "bounded_denominator_positive_finite",
            np.isfinite(denom).all()
            and np.all(denom > 0.0),
            [float(np.min(denom)), float(np.max(denom))],
        )

        sub_mass = parent_flat[flat] * pv_q / denom[flat]
        gate(
            "bounded_subsegment_mass_nonnegative_finite",
            np.isfinite(sub_mass).all()
            and float(np.min(sub_mass)) >= -1.0e-12,
            [float(np.min(sub_mass)), float(np.max(sub_mass))],
        )

        mapped_cell = np.bincount(
            flat,
            weights=sub_mass,
            minlength=NCELL,
        )
        alpha = np.minimum(1.0, W / cell_pv_flat)
        expected_mapped_cell = parent_flat * alpha
        residual_flat = parent_flat - expected_mapped_cell

        cell_tol = max(
            1.0e-8,
            1.0e-12 * max(float(np.max(np.abs(parent_flat))), 1.0),
        )
        mapped_cell_error = float(
            np.max(np.abs(mapped_cell - expected_mapped_cell))
        )

        gate(
            "bounded_projection_cellwise_formula_closure",
            mapped_cell_error <= cell_tol,
            {
                "max_abs_residual_kg": mapped_cell_error,
                "tolerance_kg": cell_tol,
            },
        )
        gate(
            "bounded_projection_cellwise_mapped_not_above_parent",
            float(np.max(mapped_cell - parent_flat)) <= cell_tol,
            float(np.max(mapped_cell - parent_flat)),
        )
        gate(
            "bounded_projection_cellwise_residual_nonnegative",
            float(np.min(residual_flat)) >= -cell_tol,
            float(np.min(residual_flat)),
        )

        cv_mass = np.bincount(
            cv_id,
            weights=sub_mass,
            minlength=NSL * NCV,
        ).reshape(NSL, NCV)
        projection_executed = True

        mapped_total = fsum_array(cv_mass)
        residual_total = fsum_array(residual_flat)
        ledger_residual = mapped_total + residual_total - parent_total

        gate(
            "bounded_projection_global_split_state_ledger",
            abs(ledger_residual) <= mass_tol,
            {
                "residual_kg": ledger_residual,
                "tolerance_kg": mass_tol,
            },
        )

        s0_mask = np.zeros(NCELL, dtype=bool)
        h1_mask = np.zeros(NCELL, dtype=bool)
        d1_mask = np.zeros(NCELL, dtype=bool)
        s0_mask[s0] = True
        h1_mask[h1] = True
        d1_mask[d1] = True

        undercovered_mask = (W > 0.0) & (W < cell_pv_flat)
        unit_or_overcovered_mask = W >= cell_pv_flat

        residual_inside_s0 = fsum_array(residual_flat[s0])
        residual_h1 = fsum_array(residual_flat[h1])
        residual_outside_d1 = fsum_array(residual_flat[~d1_mask])

        gate(
            "residual_outside_S0_exact_parent_mass",
            np.array_equal(
                residual_flat[~s0_mask],
                parent_flat[~s0_mask],
            ),
        )
        gate(
            "unit_or_overcovered_cells_zero_residual",
            float(
                np.max(
                    np.abs(residual_flat[unit_or_overcovered_mask])
                )
            ) <= cell_tol
            if np.any(unit_or_overcovered_mask)
            else True,
        )

        # Capacity monotonicity comparator from F2-R1.
        diag_sub_mass = parent_flat[flat] * pv_q / cell_pv_flat[flat]
        gate(
            "bounded_edge_mass_not_above_physicalPV_diagnostic",
            float(np.max(sub_mass - diag_sub_mass)) <= cell_tol,
            float(np.max(sub_mass - diag_sub_mass)),
        )

        # ------------------------------------------------------------------------------------------
        # E37A capacity and mass-to-saturation inversion.
        # ------------------------------------------------------------------------------------------
        stage = "E37A_capacity_and_inversion"

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

        gate(
            "E37A_CV_geometry_positive_finite",
            coeff.shape == (NSL, NCV)
            and cv_pv.shape == (NSL, NCV)
            and np.isfinite(coeff).all()
            and np.isfinite(cv_pv).all()
            and np.all(coeff > 0.0)
            and np.all(cv_pv > 0.0),
        )

        cv_capacity = np.asarray(
            e37.cv_mass_from_saturation(
                r2,
                np.full((NSL, NCV), INJECTED, dtype=np.float64),
                coeff,
            ),
            dtype=np.float64,
        )
        excess = cv_mass - cv_capacity
        max_excess = float(np.max(excess))
        worst_flat = int(np.argmax(excess))
        worst_sl = worst_flat // NCV
        worst_cv = worst_flat % NCV
        capacity_tol = max(
            1.0e-9,
            1.0e-12 * max(float(np.max(np.abs(cv_mass))), 1.0),
        )
        overloaded_count = int(np.sum(excess > capacity_tol))

        capacity_detail = {
            "maximum_excess_kg": max_excess,
            "tolerance_kg": capacity_tol,
            "overloaded_CV_count": overloaded_count,
            "worst_streamline": worst_sl,
            "worst_control_volume": worst_cv,
            "target_mass_kg": float(cv_mass[worst_sl, worst_cv]),
            "capacity_kg": float(cv_capacity[worst_sl, worst_cv]),
        }

        if overloaded_count != 0 or max_excess > capacity_tol:
            raise ScientificFail(
                "bounded_projected_CV_mass_within_frozen_E37A_capacity",
                capacity_detail,
            )

        try:
            cv_sat = np.asarray(
                e37.invert_cv_mass_to_saturation(
                    r2,
                    cv_mass,
                    coeff,
                ),
                dtype=np.float64,
            )
        except Exception as exc:
            raise GateError(
                "E37A_CV_mass_inversion_unexpected_exception:" + repr(exc)
            ) from exc

        cv_inversion_executed = True

        reconstructed_cv_mass = np.asarray(
            e37.cv_mass_from_saturation(
                r2,
                cv_sat,
                coeff,
            ),
            dtype=np.float64,
        )
        inversion_max_abs = float(
            np.max(np.abs(reconstructed_cv_mass - cv_mass))
        )
        inversion_global_residual = (
            fsum_array(reconstructed_cv_mass) - mapped_total
        )
        inversion_tol = max(
            1.0e-6,
            1.0e-10 * max(float(np.max(np.abs(cv_mass))), 1.0),
        )

        gate(
            "E37A_CV_saturation_bounds",
            float(np.min(cv_sat)) >= BACKGROUND - 1.0e-12
            and float(np.max(cv_sat)) <= INJECTED + 1.0e-12,
            [float(np.min(cv_sat)), float(np.max(cv_sat))],
        )
        gate(
            "E37A_CV_mass_inversion_pointwise_closure",
            inversion_max_abs <= inversion_tol,
            {
                "max_abs_residual_kg": inversion_max_abs,
                "tolerance_kg": inversion_tol,
            },
        )
        gate(
            "E37A_CV_mass_inversion_global_closure",
            abs(inversion_global_residual) <= mass_tol,
            {
                "residual_kg": inversion_global_residual,
                "tolerance_kg": mass_tol,
            },
        )

        # ------------------------------------------------------------------------------------------
        # Accepted split-state diagnostics / publication.
        # ------------------------------------------------------------------------------------------
        stage = "accepted_split_state_publication"

        parent_active = parent_flat > 0.0
        residual_active = residual_flat > 0.0
        mapped_fraction = mapped_total / max(parent_total, 1.0e-300)
        residual_fraction = residual_total / max(parent_total, 1.0e-300)

        mass_rows = [
            {
                "domain": "TOTAL_PARENT_GRID",
                "mass_kg": parent_total,
                "fraction_of_parent_mass": 1.0,
                "active_mass_cells": int(np.sum(parent_active)),
                "cell_count": NCELL,
            },
            {
                "domain": "MAPPED_STREAMLINE_CV_STATE",
                "mass_kg": mapped_total,
                "fraction_of_parent_mass": mapped_fraction,
                "active_mass_cells": "",
                "cell_count": NSL * NCV,
            },
            {
                "domain": "TOTAL_GRID_RESIDUAL",
                "mass_kg": residual_total,
                "fraction_of_parent_mass": residual_fraction,
                "active_mass_cells": int(np.sum(residual_active)),
                "cell_count": NCELL,
            },
            {
                "domain": "RESIDUAL_INSIDE_S0",
                "mass_kg": residual_inside_s0,
                "fraction_of_parent_mass": residual_inside_s0 / max(parent_total, 1.0e-300),
                "active_mass_cells": int(np.sum(residual_flat[s0] > 0.0)),
                "cell_count": int(len(s0)),
            },
            {
                "domain": "RESIDUAL_IN_H1",
                "mass_kg": residual_h1,
                "fraction_of_parent_mass": residual_h1 / max(parent_total, 1.0e-300),
                "active_mass_cells": int(np.sum(residual_flat[h1] > 0.0)),
                "cell_count": int(len(h1)),
            },
            {
                "domain": "RESIDUAL_OUTSIDE_D1",
                "mass_kg": residual_outside_d1,
                "fraction_of_parent_mass": residual_outside_d1 / max(parent_total, 1.0e-300),
                "active_mass_cells": int(np.sum(residual_flat[~d1_mask] > 0.0)),
                "cell_count": int(np.sum(~d1_mask)),
            },
        ]

        occupancy_rows: list[dict[str, Any]] = []
        for cell in s0:
            k = int(cell // (NY * NX))
            rem = int(cell % (NY * NX))
            j = int(rem // NX)
            i = int(rem % NX)
            occupancy_rows.append(
                {
                    "flat_cell": int(cell),
                    "k": k,
                    "j": j,
                    "i": i,
                    "parent_mass_kg": float(parent_flat[cell]),
                    "physical_cell_pore_volume_m3": float(cell_pv_flat[cell]),
                    "SG7D_Wc_m3": float(W[cell]),
                    "coverage_ratio_Wc_over_cellPV": float(
                        W[cell] / cell_pv_flat[cell]
                    ),
                    "occupancy_fraction_alpha": float(alpha[cell]),
                    "mapped_mass_kg": float(mapped_cell[cell]),
                    "residual_mass_kg": float(residual_flat[cell]),
                    "regime": (
                        "UNDERCOVERED"
                        if W[cell] < cell_pv_flat[cell]
                        else "UNIT_OR_OVERCOVERED"
                    ),
                }
            )

        projection_audit = {
            "milestone": MILESTONE,
            "protocol_id": PROTOCOL_ID,
            "operator": (
                "m_q = M_parent[c(q)] * PV_q / max(PV_cell_c, W_c)"
            ),
            "parent_total_mass_kg": parent_total,
            "mapped_CV_mass_kg": mapped_total,
            "residual_grid_mass_kg": residual_total,
            "mapped_fraction_of_parent_mass": mapped_fraction,
            "residual_fraction_of_parent_mass": residual_fraction,
            "residual_inside_S0_kg": residual_inside_s0,
            "residual_H1_kg": residual_h1,
            "residual_outside_D1_kg": residual_outside_d1,
            "global_ledger_residual_kg": ledger_residual,
            "cellwise_formula_max_abs_residual_kg": mapped_cell_error,
            "S0_cell_count": int(len(s0)),
            "undercovered_S0_cell_count": int(np.sum(undercovered_mask[s0])),
            "unit_or_overcovered_S0_cell_count": int(
                np.sum(unit_or_overcovered_mask[s0])
            ),
            "support_domain_changed": False,
            "reverse_halo_pullback_performed": False,
            "LP_or_repair_search_performed": False,
        }

        capacity_audit = {
            "milestone": MILESTONE,
            **capacity_detail,
            "capacity_PASS": True,
            "CV_saturation_min": float(np.min(cv_sat)),
            "CV_saturation_max": float(np.max(cv_sat)),
            "CV_mass_inversion_max_abs_residual_kg": inversion_max_abs,
            "CV_mass_inversion_global_residual_kg": inversion_global_residual,
            "CV_mass_inversion_PASS": True,
        }

        f3_handoff = {
            "milestone": "POSTV16-AV4-F3",
            "name": (
                "Split-State Restart Model-Signature and Physics-Teacher "
                "Protocol Freeze"
            ),
            "authorized": True,
            "execution": True,
            "F2R3_status_required": STATUS_PASS,
            "accepted_parent_day": PARENT_DAY,
            "first_candidate_target_day": FIRST_CANDIDATE_TARGET_DAY,
            "first_candidate_delta_day": FIRST_CANDIDATE_DELTA_DAY,
            "accepted_parent_state": [
                "1078x200 parent_CV_component_mass_kg",
                "1078x200 parent_CV_saturation",
                "15x50x50 residual_grid_component_mass_kg",
                "15x50x50 occupancy_fraction_alpha",
                "A2-E refreshed Day365 flow/geometry conditioning",
            ],
            "F3_scope": [
                "freeze exact restartable neural state/model signature",
                "freeze explicit t_parent / t_target / delta_t feature semantics",
                "freeze how residual-grid parent mass participates in the one-step 365->500 teacher problem",
                "freeze physics-teacher execution contract and conservation accounting",
                "freeze training/validation/OOD firewalls for the restart-aware model",
            ],
            "teacher_execution_authorized_in_F3": False,
            "model_training_authorized_in_F3": False,
            "checkpoint_inference_authorized_in_F3": False,
            "physical_time_advance_authorized_in_F3": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "F2_scientific_FAIL_preserved": True,
            "F2R1_localization_preserved": True,
            "F2R2_protocol_preserved": True,
            "single_candidate_executed": True,
            "alternate_candidate_tested": False,
            "repair_search_performed": False,
            "projection_PASS": True,
            "capacity_PASS": True,
            "CV_mass_inversion_PASS": True,
            "accepted_split_state": True,
            "residual_inside_S0_allowed_and_observed": residual_inside_s0 > 0.0,
            "support_domain_changed": False,
            "mass_clipped_or_discarded": False,
            "global_rescaling_performed": False,
            "saturation_bound_changed": False,
            "teacher_transport_performed": False,
            "checkpoint_model_loaded": False,
            "checkpoint_inference_performed": False,
            "physical_time_advanced": False,
            "future_state_prediction_performed": False,
            "future_mapback_performed": False,
            "training_performed": False,
            "CMG_validation_performed": False,
            "F3_authorized": True,
            "F3_execution_authorized": True,
            "teacher_execution_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "control_realization": CONTROL_REALIZATION,
            "paired_porosity": CONTROL_POROSITY,
            "parent_day": PARENT_DAY,
            "parent_total_mass_kg": parent_total,
            "mapped_CV_mass_kg": mapped_total,
            "residual_grid_mass_kg": residual_total,
            "mapped_fraction_of_parent_mass": mapped_fraction,
            "residual_fraction_of_parent_mass": residual_fraction,
            "residual_inside_S0_kg": residual_inside_s0,
            "undercovered_S0_cell_count": int(np.sum(undercovered_mask[s0])),
            "overloaded_CV_count": overloaded_count,
            "maximum_CV_capacity_excess_kg": max_excess,
            "CV_saturation_min": float(np.min(cv_sat)),
            "CV_saturation_max": float(np.max(cv_sat)),
            "global_ledger_residual_kg": ledger_residual,
            "accepted_split_state": True,
            "projection_execution": True,
            "CV_mass_inversion_execution": True,
            "teacher_transport": False,
            "checkpoint_inference": False,
            "physical_time_advance": False,
            "F3_authorized": True,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        state_npz = deterministic_npz_bytes(
            {
                "parent_CV_component_mass_kg": cv_mass,
                "parent_CV_saturation": cv_sat,
                "parent_CV_capacity_kg": cv_capacity,
                "parent_CV_pore_volume_m3": cv_pv,
                "parent_CV_pressure_mass_coeff": coeff,
                "residual_grid_component_mass_kg": residual_flat.reshape(GRID),
                "occupancy_fraction_alpha": alpha.reshape(GRID),
                "SG7D_occupancy_pore_volume_Wc_m3": W.reshape(GRID),
                "physical_cell_pore_volume_m3": cell_pv,
                "mapped_grid_component_mass_kg": expected_mapped_cell.reshape(GRID),
                "S0_mask": s0_mask.reshape(GRID),
                "H1_mask": h1_mask.reshape(GRID),
                "D1_mask": d1_mask.reshape(GRID),
                "S0_flat_cells": s0,
                "H1_flat_cells": h1,
                "D1_flat_cells": d1,
                "subsegment_parent_mass_kg": sub_mass,
                "subsegment_flat_cell": flat,
                "subsegment_streamline": stream,
                "subsegment_control_volume": node,
                "subsegment_pore_volume_m3": pv_q,
                "parent_total_mass_kg": np.asarray(parent_total),
                "mapped_CV_mass_kg": np.asarray(mapped_total),
                "residual_grid_mass_kg": np.asarray(residual_total),
                "parent_day": np.asarray(PARENT_DAY),
            }
        )

        output_files = {
            "PAD_Stream_POSTV16_AV4_F2_R3_Summary.json":
                json_bytes(summary),
            "POSTV16_AV4_F2_R3_Accepted_Parent_Restart_State.npz":
                state_npz,
            "POSTV16_AV4_F2_R3_Domain_Mass_Audit.csv":
                csv_bytes(mass_rows),
            "POSTV16_AV4_F2_R3_S0_Occupancy_Audit.csv":
                csv_bytes(occupancy_rows),
            "POSTV16_AV4_F2_R3_Projection_Closure_Audit.json":
                json_bytes(projection_audit),
            "POSTV16_AV4_F2_R3_CV_Capacity_and_Inversion_Audit.json":
                json_bytes(capacity_audit),
            "POSTV16_AV4_F2_R3_F3_Handoff_Contract.json":
                json_bytes(f3_handoff),
            "POSTV16_AV4_F2_R3_Decision_Contract.json":
                json_bytes(decision),
            "POSTV16_AV4_F2_R3_Final_Gate_Matrix.csv":
                csv_bytes(
                    [{"gate": name, **value} for name, value in gates.items()]
                ),
        }

        immutable_publish(out, output_files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV4_F2_R3_Artifact_Manifest.csv":
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
                "POSTV16_AV4_F2_R3_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print()
        print("=" * 214)
        print(f"{MILESTONE}: BOUNDED PHYSICAL-OCCUPANCY SPLIT-STATE EXECUTION PASS")
        print("=" * 214)
        print("Parent total mass kg                    :", parent_total)
        print("Mapped CV mass kg                       :", mapped_total)
        print("Residual grid mass kg                   :", residual_total)
        print("Mapped / residual fractions             :", mapped_fraction, "/", residual_fraction)
        print("Residual inside S0 kg                   :", residual_inside_s0)
        print("Under-covered S0 cells                  :", int(np.sum(undercovered_mask[s0])), "/", len(s0))
        print("Global split-state ledger residual kg   :", ledger_residual)
        print("Overloaded CV count                     :", overloaded_count)
        print("Maximum CV capacity excess kg           :", max_excess)
        print("Parent CV saturation min / max          :", float(np.min(cv_sat)), "/", float(np.max(cv_sat)))
        print("Accepted split restart state            : True")
        print("Teacher / checkpoint inference          : False / False")
        print("Physical time advance                   : False")
        print("POSTV16-AV4-F3                          : AUTHORIZED (protocol freeze only)")
        print("Teacher execution / A3-E2 / dynamic AV4: NOT AUTHORIZED")
        print("=" * 214)

        return 0

    except ScientificFail as exc:
        if exc.gate != "bounded_projected_CV_mass_within_frozen_E37A_capacity":
            raise

        failed.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_FAIL,
            "failed_stage": stage,
            "failed_gate": exc.gate,
            "detail": exc.detail,
            "gates": gates,
            "projection_executed": projection_executed,
            "CV_mass_inversion_executed": cv_inversion_executed,
            "single_frozen_candidate_only": True,
            "alternate_candidate_tested": False,
            "repair_search_performed": False,
            "support_domain_changed": False,
            "mass_clipped_or_discarded": False,
            "global_rescaling_performed": False,
            "saturation_bound_changed": False,
            "teacher_transport_performed": False,
            "checkpoint_model_loaded": False,
            "checkpoint_inference_performed": False,
            "physical_time_advanced": False,
            "F3_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
            "automatic_rerun_authorized": False,
        }

        data = json_bytes(report)
        p = failed / "POSTV16_AV4_F2_R3_Scientific_Fail_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = failed / (
                "POSTV16_AV4_F2_R3_Scientific_Fail_Report_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        if not p.exists():
            p.write_bytes(data)

        print()
        print("=" * 214)
        print(f"{MILESTONE}: SCIENTIFIC FAIL — FROZEN BOUNDED CANDIDATE")
        print("=" * 214)
        print("Stage      :", stage)
        print("Failed gate:", exc.gate)
        print("Detail     :", exc.detail)
        print("NO ALTERNATE CANDIDATE OR AUTOMATIC RERUN AUTHORIZED.")
        print("F3 / A3-E2 / dynamic transport: NOT AUTHORIZED")
        print("=" * 214)
        return 3

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "projection_executed": projection_executed,
            "CV_mass_inversion_executed": cv_inversion_executed,
            "single_frozen_candidate_only": True,
            "alternate_candidate_tested": False,
            "repair_search_performed": False,
            "support_domain_changed": False,
            "mass_clipped_or_discarded": False,
            "physical_time_advanced": False,
            "F3_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
            "automatic_rerun_authorized": False,
        }

        data = json_bytes(report)
        p = blocked / "POSTV16_AV4_F2_R3_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV4_F2_R3_Blocked_Report_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        if not p.exists():
            p.write_bytes(data)

        print()
        print("=" * 214)
        print(f"{MILESTONE}: TECHNICAL / AUTHORITY BLOCK")
        print("=" * 214)
        print("Stage    :", stage)
        print("Exception:", repr(exc))
        print("NO ALTERNATE CANDIDATE OR AUTOMATIC RERUN AUTHORIZED.")
        print("F3 / A3-E2 / dynamic transport: NOT AUTHORIZED")
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
