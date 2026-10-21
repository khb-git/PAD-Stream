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


MILESTONE = "POSTV16-AV4-F2"
PROTOCOL_ID = (
    "POSTV16_AV4_F2_CONTROLLED_DAY365_CONSERVATIVE_PARENT_STATE_"
    "NORMALIZED_TRANSPOSE_PROJECTION_EXECUTION_V1"
)

STATUS_PASS_CV_COMPLETE = (
    "AV4F2_DAY365_CONSERVATIVE_PARENT_STATE_PROJECTION_PASS_"
    "CV_COMPLETE_NUMERICAL_ZERO_RESIDUAL_GRID_MASS_NO_TIME_ADVANCE"
)
STATUS_PASS_SPLIT = (
    "AV4F2_DAY365_CONSERVATIVE_PARENT_STATE_PROJECTION_PASS_"
    "SPLIT_STATE_REQUIRED_PHYSICALLY_NONZERO_RESIDUAL_GRID_MASS_"
    "RETAINED_NO_TIME_ADVANCE"
)
STATUS_FAIL_CAPACITY = (
    "AV4F2_SCIENTIFIC_FAIL_PROJECTED_CV_COMPONENT_MASS_EXCEEDS_"
    "FROZEN_E37A_CAPACITY_NO_ADAPTATION_OR_AUTOMATIC_RERUN"
)
STATUS_BLOCKED = "AV4F2_TECHNICAL_EXECUTION_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_F1R2_COMMIT = "a90aff72c4cb70ca0415d77f39ed3b77d14748db"

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

R7R7D = (
    "PAD_Stream_POSTV16_AV1_D_R7_R7D_"
    "Horizontal_Face_Halo_Occupancy_Domain_Freeze.py"
)
R7R7D_BLOB = "bd2873f7fb6b98d4e857c98864b78e2da6f202a4"

R7R7E = (
    "PAD_Stream_POSTV16_AV1_D_R7_R7E_"
    "Frozen_Horizontal_Face_Halo_Occupancy_Domain_Execution.py"
)
R7R7E_BLOB = "9f99d9dcab649ba7ac911ad09ad79b4e0eb2ecc8"

SOURCE_BLOBS = {
    F1R2: F1R2_BLOB,
    A2E: A2E_BLOB,
    R2: R2_BLOB,
    E37A: E37A_BLOB,
    SG7D: SG7D_BLOB,
    R7R7D: R7R7D_BLOB,
    R7R7E: R7R7E_BLOB,
}

# --------------------------------------------------------------------------------------------------
# Frozen Drive authorities.
# --------------------------------------------------------------------------------------------------

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

F1R2_REL = BASE_AV4 / "POSTV16_AV4_F1_R2_Restart_State_and_Conservative_Parent_Projection_Freeze"
F1R2_SUMMARY = "PAD_Stream_POSTV16_AV4_F1_R2_Summary.json"
F1R2_PROJECTION = "POSTV16_AV4_F1_R2_Conservative_Grid_to_Streamline_Projection_Protocol.json"
F1R2_RESIDUAL = "POSTV16_AV4_F1_R2_Residual_Grid_State_Sidecar_Contract.json"
F1R2_TEMPORAL = "POSTV16_AV4_F1_R2_Restart_Temporal_Semantics_Contract.json"
F1R2_HANDOFF = "POSTV16_AV4_F1_R2_F2_Handoff_Contract.json"
F1R2_DECISION = "POSTV16_AV4_F1_R2_Decision_Contract.json"
F1R2_MANIFEST = "POSTV16_AV4_F1_R2_Artifact_Manifest.csv"
F1R2_STATUS = (
    "AV4F1R2_F1R1_TECHNICAL_CLOSURE_BOUND_E1R2_STRUCTURAL_RESTART_"
    "INCOMPATIBILITY_BOUND_RESTART_STATE_REPRESENTATION_CONSERVATIVE_"
    "SPLIT_PARENT_PROJECTION_AND_TEMPORAL_SEMANTICS_PROSPECTIVELY_"
    "FROZEN_NO_PROJECTION_EXECUTION"
)

A2E_REL = BASE_AV4 / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_SUMMARY = "PAD_Stream_POSTV16_AV4_A2_E_Summary.json"
A2E_EPOCH = "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_MANIFEST = "POSTV16_AV4_A2_E_Artifact_Manifest.csv"
A2E_STATUS = (
    "AV4A2E_AV3CR0003_DAY365_SAME_TIME_SPATIAL_MOBILITY_PRESSURE_SATURATION_"
    "REFRESH_DARCY_POLLOCK_TOF_GEOMETRY_EXECUTION_PASS"
)

OUT_REL = BASE_AV4 / "POSTV16_AV4_F2_Controlled_Day365_Conservative_Parent_State_Projection"
FAIL_REL = BASE_AV4 / "POSTV16_AV4_F2_SCIENTIFIC_FAIL_CV_CAPACITY"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F2_BLOCKED"


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


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError("cannot_load_module:" + str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


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
    # Exact normalized-transpose partition across overlapping subsegments.
    parent = np.asarray([12.0, 8.0, 5.0], dtype=np.float64)
    flat = np.asarray([0, 0, 1], dtype=np.int64)
    pv = np.asarray([1.0, 3.0, 2.0], dtype=np.float64)
    cv = np.asarray([0, 1, 1], dtype=np.int64)

    denom = np.bincount(flat, weights=pv, minlength=3)
    sub_mass = parent[flat] * pv / denom[flat]
    cv_mass = np.bincount(cv, weights=sub_mass, minlength=2)
    cell_mass = np.bincount(flat, weights=sub_mass, minlength=3)

    assert np.allclose(cv_mass, [3.0, 17.0], rtol=0.0, atol=1.0e-14)
    assert np.allclose(cell_mass[:2], parent[:2], rtol=0.0, atol=1.0e-14)

    residual = parent.copy()
    residual[:2] = 0.0
    assert abs(float(np.sum(cv_mass)) + float(np.sum(residual)) - float(np.sum(parent))) < 1.0e-14
    assert FIRST_CANDIDATE_TARGET_DAY - PARENT_DAY == FIRST_CANDIDATE_DELTA_DAY

    print(
        "POSTV16-AV4-F2 conservative parent-state projection "
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
    scientific_execution_started = False
    projection_executed = False
    cv_inversion_executed = False

    diagnostics: dict[str, Any] = {}

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
        "POSTV16-AV4-F2 — CONTROLLED DAY365 CONSERVATIVE PARENT-STATE "
        "GRID→REFRESHED-STREAMLINE PROJECTION EXECUTION"
    )
    print("=" * 214)
    print("EXECUTE ONLY THE F1-R2-FROZEN PARENT-STATE PROJECTION.")
    print("NO TEACHER. NO CHECKPOINT LOAD/INFERENCE. NO PHYSICAL-TIME ADVANCE.")
    print("NO FUTURE-STATE PREDICTION. NO FUTURE MAPBACK. NO TRAINING. NO CMG.")
    print("NO SUPPORT-DOMAIN ADAPTATION AFTER OBSERVING THE RESULT.")
    print()

    try:
        # ------------------------------------------------------------------------------------------
        # Repository and source authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"

        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")
        gate(
            "repository_parent_is_F1R2_commit",
            parent == PARENT_F1R2_COMMIT,
            parent,
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
        # Bind formal F1-R2 protocol freeze and exact F2 handoff.
        # ------------------------------------------------------------------------------------------
        stage = "F1R2_protocol_binding"

        f1 = drive / F1R2_REL
        gate("F1R2_output_present", f1.is_dir(), str(f1))
        mf1 = verify_manifest(f1, F1R2_MANIFEST)
        gate("F1R2_manifest_exact_8", len(mf1) == 8, len(mf1))

        sf1 = load_json(f1 / F1R2_SUMMARY)
        pf1 = load_json(f1 / F1R2_PROJECTION)
        rf1 = load_json(f1 / F1R2_RESIDUAL)
        tf1 = load_json(f1 / F1R2_TEMPORAL)
        hf1 = load_json(f1 / F1R2_HANDOFF)
        df1 = load_json(f1 / F1R2_DECISION)

        gate("F1R2_status_exact", sf1["status"] == F1R2_STATUS, sf1["status"])
        gate(
            "F1R2_projection_contract_exact",
            pf1["execution_in_F1"] is False
            and pf1["normalized_transpose"]["cell_denominator"]
            == "W_c = sum_{q: c(q)=c} PV_q"
            and pf1["normalized_transpose"]["subsegment_mass_assignment"]
            == "m_q = M_parent[c(q)] * PV_q / W_c"
            and pf1["normalized_transpose"]["control_volume_mass"]
            == "M_cv[r] = sum_{q: r(q)=r} m_q"
            and pf1["residual_grid_sidecar"]["global_ledger"]
            == "sum(M_cv) + sum(R_grid) = sum(M_parent_grid)"
            and pf1["existing_E37A_sampler_role"]["production_parent_projection_authority"] is False,
        )
        gate(
            "F1R2_residual_outcome_contract_exact",
            rf1["no_post_hoc_residual_fraction_threshold"] is True
            and set(rf1["F2_outcome_classes"].keys())
            == {
                "F2_PASS_CV_COMPLETE",
                "F2_PASS_SPLIT_STATE_REQUIRED",
                "F2_SCIENTIFIC_FAIL_CV_CAPACITY",
                "F2_TECHNICAL_BLOCK",
            },
        )
        gate(
            "F1R2_restart_temporal_semantics_exact",
            float(tf1["restart_semantics"]["parent_time_days"]) == PARENT_DAY
            and float(tf1["restart_semantics"]["first_candidate_target_time_days"])
            == FIRST_CANDIDATE_TARGET_DAY
            and float(tf1["restart_semantics"]["first_candidate_delta_time_days"])
            == FIRST_CANDIDATE_DELTA_DAY
            and tf1["neural_input_dimension_frozen_in_F1"] is False,
        )
        gate(
            "F1R2_F2_handoff_exact",
            hf1["milestone"] == MILESTONE
            and hf1["authorized"] is True
            and hf1["execution"] is True
            and hf1["control_realization"] == CONTROL_REALIZATION
            and hf1["paired_porosity"] == CONTROL_POROSITY
            and float(hf1["parent_day"]) == PARENT_DAY,
            hf1,
        )
        gate(
            "F1R2_downstream_firewalls_before_F2",
            hf1["F3_teacher_or_restart_model_protocol_authorized"] is False
            and hf1["A3_E2_checkpoint_test_authorized"] is False
            and hf1["AV4_dynamic_transport_execution_authorized"] is False
            and df1["F2_authorized"] is True
            and df1["F2_execution_authorized"] is True
            and df1["F3_authorized"] is False
            and df1["A3_E2_authorized"] is False
            and df1["AV4_dynamic_transport_execution_authorized"] is False,
        )

        # ------------------------------------------------------------------------------------------
        # Bind A2-E exact parent-state epoch.
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
            epoch_keys = set(z.files)
            parent_mass = np.asarray(z["parent_component_mass_kg"], dtype=np.float64)
            parent_sat = np.asarray(z["reconciled_saturation"], dtype=np.float64)
            pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            porosity = np.asarray(z["paired_porosity"], dtype=np.float64)
            pore_volume = np.asarray(z["pore_volume_m3"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
            tof_s = np.asarray(z["streamline_tof_s"], dtype=np.float64)
            weights_m3_s = np.asarray(z["streamline_weight_m3_s"], dtype=np.float64)
            canonical_day = float(np.asarray(z["canonical_day"]).reshape(()))

        required = {
            "parent_component_mass_kg",
            "reconciled_saturation",
            "refreshed_pressure_psi",
            "paired_porosity",
            "pore_volume_m3",
            "reference_gas_pressure_pa",
            "streamline_xyz_m",
            "streamline_tof_s",
            "streamline_weight_m3_s",
            "canonical_day",
        }
        gate("A2E_required_arrays_present", required.issubset(epoch_keys), sorted(required))
        gate(
            "A2E_parent_and_geometry_shapes_exact",
            parent_mass.shape == GRID
            and parent_sat.shape == GRID
            and pressure.shape == GRID
            and porosity.shape == GRID
            and pore_volume.shape == GRID
            and xyz.shape == (NSL, NN, 3)
            and tof_s.shape == (NSL, NN)
            and weights_m3_s.shape == (NSL,),
            {
                "mass": parent_mass.shape,
                "saturation": parent_sat.shape,
                "pressure": pressure.shape,
                "porosity": porosity.shape,
                "pore_volume": pore_volume.shape,
                "xyz": xyz.shape,
                "tof": tof_s.shape,
                "weight": weights_m3_s.shape,
            },
        )
        gate(
            "A2E_parent_arrays_finite",
            all(
                np.isfinite(a).all()
                for a in [
                    parent_mass,
                    parent_sat,
                    pressure,
                    porosity,
                    pore_volume,
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
            "A2E_pore_volume_positive",
            np.all(pore_volume > 0.0),
            [float(np.min(pore_volume)), float(np.max(pore_volume))],
        )
        gate("A2E_parent_day_exact", canonical_day == PARENT_DAY, canonical_day)

        # ------------------------------------------------------------------------------------------
        # Load frozen source-authentic geometry / EOS / inversion modules.
        # ------------------------------------------------------------------------------------------
        stage = "source_module_binding"

        r2 = load_module(root / R2, "postv16_av4_f2_r2")
        e37 = load_module(root / E37A, "postv16_av4_f2_e37a")
        sg7d = load_module(root / SG7D, "postv16_av4_f2_sg7d")
        r7e = load_module(root / R7R7E, "postv16_av4_f2_r7r7e")

        gate(
            "R2_EOS_authority_present",
            hasattr(r2, "gas_density_from_state")
            and hasattr(r2, "capillary_pressure_from_incremental_sg")
            and float(r2.CO2_COMPRESSIBILITY_1_PA) == 1.0e-8,
        )
        gate(
            "E37A_CV_authority_present",
            hasattr(e37, "build_control_volume_geometry")
            and hasattr(e37, "cv_mass_from_saturation")
            and hasattr(e37, "invert_cv_mass_to_saturation"),
        )
        gate(
            "SG7D_operator_authority_present",
            hasattr(sg7d, "build_subsegment_operator"),
        )
        gate(
            "R7R7E_halo_geometry_authority_present",
            hasattr(r7e, "build_extended_halo_graph"),
        )

        # ------------------------------------------------------------------------------------------
        # Verify the accepted A2-E saturation is mass-consistent under the same refreshed state.
        # ------------------------------------------------------------------------------------------
        stage = "parent_mass_saturation_consistency"

        sg_parent = np.clip(parent_sat - BACKGROUND, 0.0, MAX_SG)
        rho_parent = np.asarray(
            r2.gas_density_from_state(parent_sat, pressure, p_ref),
            dtype=np.float64,
        )
        reconstructed_parent_mass = pore_volume * rho_parent * sg_parent

        parent_rel_l2 = relative_l2(reconstructed_parent_mass, parent_mass)
        parent_global_residual = (
            fsum_array(reconstructed_parent_mass) - fsum_array(parent_mass)
        )
        parent_total = fsum_array(parent_mass)
        gate("A2E_parent_total_mass_positive", parent_total > 0.0, parent_total)
        parent_mass_tol = max(1.0e-8, 1.0e-12 * max(abs(parent_total), 1.0))

        gate(
            "A2E_reconciled_saturation_parent_mass_relative_L2",
            parent_rel_l2 <= 1.0e-10,
            parent_rel_l2,
        )
        gate(
            "A2E_reconciled_saturation_global_mass_closure",
            abs(parent_global_residual) <= parent_mass_tol,
            {
                "residual_kg": parent_global_residual,
                "tolerance_kg": parent_mass_tol,
            },
        )

        # ------------------------------------------------------------------------------------------
        # Rebuild refreshed SG7D operator and exact S0/H1/D1 geometry.
        # ------------------------------------------------------------------------------------------
        stage = "refreshed_operator_and_domain_reconstruction"

        tof_days = tof_s / DAY_TO_S
        weights_m3_day = weights_m3_s * DAY_TO_S

        operator = sg7d.build_subsegment_operator(
            xyz,
            tof_days,
            weights_m3_day,
        )

        stream = np.asarray(operator["streamline"], dtype=np.int64)
        node = np.asarray(operator["node"], dtype=np.int64)
        flat = np.asarray(operator["flat_cell"], dtype=np.int64)
        pv_sub = np.asarray(operator["pv_m3"], dtype=np.float64)

        gate(
            "SG7D_refreshed_operator_nonempty_consistent",
            len(flat) > 0
            and len(stream) == len(flat)
            and len(node) == len(flat)
            and len(pv_sub) == len(flat)
            and np.isfinite(pv_sub).all()
            and np.all(pv_sub > 0.0),
            len(flat),
        )
        gate(
            "SG7D_refreshed_operator_index_bounds",
            int(np.min(stream)) == 0
            and int(np.max(stream)) == NSL - 1
            and int(np.min(node)) == 0
            and int(np.max(node)) == NCV - 1
            and int(np.min(flat)) >= 0
            and int(np.max(flat)) < NCELL,
            {
                "stream": [int(np.min(stream)), int(np.max(stream))],
                "node": [int(np.min(node)), int(np.max(node))],
                "flat": [int(np.min(flat)), int(np.max(flat))],
            },
        )

        graph = r7e.build_extended_halo_graph(operator)
        s0 = np.asarray(graph["s0_nodes"], dtype=np.int64)
        h1 = np.asarray(graph["h1_nodes"], dtype=np.int64)
        d1 = np.asarray(graph["nodes"], dtype=np.int64)

        exact_s0 = np.unique(flat)
        gate(
            "refreshed_S0_exactly_operator_support",
            np.array_equal(s0, exact_s0),
            {"S0_cells": int(len(s0))},
        )
        gate(
            "refreshed_H1_disjoint_nonempty",
            len(h1) > 0
            and len(np.intersect1d(s0, h1, assume_unique=True)) == 0,
            {"H1_cells": int(len(h1))},
        )
        gate(
            "refreshed_D1_exact_union",
            np.array_equal(np.sort(d1), np.sort(np.concatenate([s0, h1]))),
            {"D1_cells": int(len(d1))},
        )

        # ------------------------------------------------------------------------------------------
        # Scientific execution begins: exact normalized-transpose mass projection.
        # ------------------------------------------------------------------------------------------
        scientific_execution_started = True
        stage = "normalized_transpose_parent_mass_projection"

        parent_flat = parent_mass.reshape(-1)
        denom = np.bincount(flat, weights=pv_sub, minlength=NCELL)
        gate(
            "all_refreshed_S0_cells_have_positive_subsegment_weight",
            np.all(denom[s0] > 0.0),
            float(np.min(denom[s0])),
        )

        sub_mass = parent_flat[flat] * pv_sub / denom[flat]
        gate(
            "projected_subsegment_mass_nonnegative_finite",
            np.isfinite(sub_mass).all()
            and float(np.min(sub_mass)) >= -1.0e-12,
            [float(np.min(sub_mass)), float(np.max(sub_mass))],
        )

        cv_id = stream * NCV + node
        cv_mass = np.bincount(
            cv_id,
            weights=sub_mass,
            minlength=NSL * NCV,
        ).reshape(NSL, NCV)

        projected_cell_mass = np.bincount(
            flat,
            weights=sub_mass,
            minlength=NCELL,
        )
        projection_executed = True

        cell_tol = max(
            1.0e-9,
            1.0e-12 * max(float(np.max(np.abs(parent_flat[s0]))), 1.0),
        )
        cell_max_residual = float(
            np.max(np.abs(projected_cell_mass[s0] - parent_flat[s0]))
        )
        s0_parent_mass = fsum_array(parent_flat[s0])
        cv_total_mass = fsum_array(cv_mass)
        s0_projection_residual = cv_total_mass - s0_parent_mass

        gate(
            "normalized_transpose_cellwise_S0_mass_partition",
            cell_max_residual <= cell_tol,
            {
                "max_cell_residual_kg": cell_max_residual,
                "tolerance_kg": cell_tol,
            },
        )
        gate(
            "normalized_transpose_S0_global_mass_closure",
            abs(s0_projection_residual) <= parent_mass_tol,
            {
                "residual_kg": s0_projection_residual,
                "tolerance_kg": parent_mass_tol,
            },
        )

        # ------------------------------------------------------------------------------------------
        # Exact residual grid sidecar and global ledger.
        # ------------------------------------------------------------------------------------------
        stage = "residual_grid_sidecar_and_global_ledger"

        s0_mask = np.zeros(NCELL, dtype=bool)
        h1_mask = np.zeros(NCELL, dtype=bool)
        d1_mask = np.zeros(NCELL, dtype=bool)
        s0_mask[s0] = True
        h1_mask[h1] = True
        d1_mask[d1] = True
        outside_d1_mask = ~d1_mask

        residual_flat = parent_flat.copy()
        residual_flat[s0_mask] = 0.0
        residual_grid = residual_flat.reshape(GRID)

        h1_residual_mass = fsum_array(parent_flat[h1])
        outside_d1_residual_mass = fsum_array(parent_flat[outside_d1_mask])
        residual_total_mass = fsum_array(residual_flat)
        ledger_residual = cv_total_mass + residual_total_mass - parent_total

        gate(
            "global_split_state_mass_ledger_closure",
            abs(ledger_residual) <= parent_mass_tol,
            {
                "residual_kg": ledger_residual,
                "tolerance_kg": parent_mass_tol,
            },
        )
        gate(
            "residual_sidecar_exact_zero_on_S0",
            float(np.max(np.abs(residual_flat[s0]))) == 0.0,
        )
        gate(
            "residual_sidecar_exact_parent_mass_outside_S0",
            np.array_equal(
                residual_flat[~s0_mask],
                parent_flat[~s0_mask],
            ),
        )

        numerical_zero_tol = max(
            1.0e-8,
            1.0e-12 * max(abs(parent_total), 1.0),
        )

        # ------------------------------------------------------------------------------------------
        # E37A CV pressure coefficient, physical capacity, and exact mass inversion.
        # ------------------------------------------------------------------------------------------
        stage = "E37A_CV_capacity_and_mass_inversion"

        geometry = e37.build_control_volume_geometry(
            r2,
            operator,
            pressure,
            p_ref,
            NSL,
            NCV,
        )
        coeff = np.asarray(
            geometry["cv_pressure_mass_coeff"],
            dtype=np.float64,
        )
        cv_pv = np.asarray(
            geometry["cv_pv_m3"],
            dtype=np.float64,
        )

        gate(
            "E37A_refreshed_CV_geometry_shapes_positive",
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
        worst_stream = worst_flat // NCV
        worst_cv = worst_flat % NCV
        capacity_tol = max(
            1.0e-9,
            1.0e-12 * max(float(np.max(np.abs(cv_mass))), 1.0),
        )

        diagnostics["capacity"] = {
            "maximum_excess_kg": max_excess,
            "tolerance_kg": capacity_tol,
            "worst_streamline": worst_stream,
            "worst_control_volume": worst_cv,
            "target_mass_kg": float(cv_mass[worst_stream, worst_cv]),
            "capacity_kg": float(cv_capacity[worst_stream, worst_cv]),
        }

        if max_excess > capacity_tol:
            raise ScientificFail(
                "projected_CV_component_mass_within_frozen_E37A_capacity",
                diagnostics["capacity"],
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
            # A capacity failure should have been caught explicitly above.
            # Any other inversion exception is an implementation/numerical block,
            # not permission to adapt the scientific protocol.
            raise GateError(
                "E37A_CV_mass_inversion_unexpected_exception:"
                + repr(exc)
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
        inversion_total_residual = (
            fsum_array(reconstructed_cv_mass) - cv_total_mass
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
            abs(inversion_total_residual) <= parent_mass_tol,
            {
                "residual_kg": inversion_total_residual,
                "tolerance_kg": parent_mass_tol,
            },
        )

        # ------------------------------------------------------------------------------------------
        # Frozen outcome classification: no post-hoc residual-fraction threshold.
        # ------------------------------------------------------------------------------------------
        stage = "F2_outcome_classification"

        if residual_total_mass <= numerical_zero_tol:
            outcome = "F2_PASS_CV_COMPLETE"
            status_pass = STATUS_PASS_CV_COMPLETE
            split_state_required = False
            f3_name = (
                "CV-Complete Restart-State Model-Signature and Teacher Protocol Freeze"
            )
        else:
            outcome = "F2_PASS_SPLIT_STATE_REQUIRED"
            status_pass = STATUS_PASS_SPLIT
            split_state_required = True
            f3_name = (
                "Split-State Restart Model-Signature and Teacher Protocol Freeze"
            )

        mass_rows = [
            {
                "domain": "TOTAL_PARENT_GRID",
                "mass_kg": parent_total,
                "fraction_of_parent_mass": 1.0,
                "active_mass_cells": int(np.sum(parent_flat > 0.0)),
                "cell_count": NCELL,
            },
            {
                "domain": "S0_REFRESHED_EXACT_SUPPORT",
                "mass_kg": s0_parent_mass,
                "fraction_of_parent_mass": s0_parent_mass / max(parent_total, 1.0e-300),
                "active_mass_cells": int(np.sum(parent_flat[s0] > 0.0)),
                "cell_count": int(len(s0)),
            },
            {
                "domain": "H1_RESIDUAL_HALO",
                "mass_kg": h1_residual_mass,
                "fraction_of_parent_mass": h1_residual_mass / max(parent_total, 1.0e-300),
                "active_mass_cells": int(np.sum(parent_flat[h1] > 0.0)),
                "cell_count": int(len(h1)),
            },
            {
                "domain": "OUTSIDE_D1_RESIDUAL",
                "mass_kg": outside_d1_residual_mass,
                "fraction_of_parent_mass": outside_d1_residual_mass / max(parent_total, 1.0e-300),
                "active_mass_cells": int(np.sum(parent_flat[outside_d1_mask] > 0.0)),
                "cell_count": int(np.sum(outside_d1_mask)),
            },
            {
                "domain": "TOTAL_RESIDUAL_OUTSIDE_S0",
                "mass_kg": residual_total_mass,
                "fraction_of_parent_mass": residual_total_mass / max(parent_total, 1.0e-300),
                "active_mass_cells": int(np.sum(residual_flat > 0.0)),
                "cell_count": int(np.sum(~s0_mask)),
            },
            {
                "domain": "PROJECTED_CV_STATE",
                "mass_kg": cv_total_mass,
                "fraction_of_parent_mass": cv_total_mass / max(parent_total, 1.0e-300),
                "active_mass_cells": "",
                "cell_count": NSL * NCV,
            },
        ]

        projection_audit = {
            "milestone": MILESTONE,
            "outcome": outcome,
            "parent_total_mass_kg": parent_total,
            "S0_mass_kg": s0_parent_mass,
            "CV_projected_mass_kg": cv_total_mass,
            "H1_residual_mass_kg": h1_residual_mass,
            "outside_D1_residual_mass_kg": outside_d1_residual_mass,
            "total_residual_mass_kg": residual_total_mass,
            "residual_fraction_of_parent_mass": (
                residual_total_mass / max(parent_total, 1.0e-300)
            ),
            "numerical_zero_mass_tolerance_kg": numerical_zero_tol,
            "S0_cellwise_projection_max_abs_residual_kg": cell_max_residual,
            "S0_projection_global_residual_kg": s0_projection_residual,
            "global_split_state_ledger_residual_kg": ledger_residual,
            "subsegment_count": int(len(flat)),
            "S0_cell_count": int(len(s0)),
            "H1_cell_count": int(len(h1)),
            "D1_cell_count": int(len(d1)),
            "reverse_H1_to_S0_pullback_performed": False,
            "support_domain_adaptation_performed": False,
        }

        capacity_audit = {
            "milestone": MILESTONE,
            **diagnostics["capacity"],
            "CV_saturation_min": float(np.min(cv_sat)),
            "CV_saturation_max": float(np.max(cv_sat)),
            "CV_mass_inversion_max_abs_residual_kg": inversion_max_abs,
            "CV_mass_inversion_global_residual_kg": inversion_total_residual,
            "CV_mass_inversion_executed": True,
            "capacity_PASS": True,
        }

        # F3 is design/freeze only. No teacher/model execution is authorized here.
        handoff = {
            "milestone": "POSTV16-AV4-F3",
            "name": f3_name,
            "authorized": True,
            "execution": True,
            "F2_outcome": outcome,
            "split_state_required": split_state_required,
            "parent_day": PARENT_DAY,
            "first_candidate_target_day": FIRST_CANDIDATE_TARGET_DAY,
            "first_candidate_delta_day": FIRST_CANDIDATE_DELTA_DAY,
            "required_authorities": [
                "F2 accepted parent CV component-mass state",
                "F2 accepted parent CV saturation",
                "F2 exact residual Cartesian component-mass sidecar",
                "F1-R2 explicit parent/target/delta restart temporal semantics",
                "A2-E refreshed flow/geometry epoch",
            ],
            "F3_scope": (
                "freeze the restartable state-conditioned transport model signature "
                "and physics-teacher protocol; do not execute teacher transport in F3"
            ),
            "teacher_execution_authorized": False,
            "checkpoint_model_load_or_inference_authorized": False,
            "A3_E2_checkpoint_test_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        decision = {
            "milestone": MILESTONE,
            "status": status_pass,
            "outcome": outcome,
            "projection_PASS": True,
            "capacity_PASS": True,
            "CV_mass_inversion_PASS": True,
            "split_state_required": split_state_required,
            "CV_complete": not split_state_required,
            "residual_mass_decision_threshold": "numerical zero only",
            "residual_fraction_threshold_used": False,
            "support_domain_adaptation_authorized": False,
            "projection_executed": True,
            "CV_mass_inversion_executed": True,
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
            "status": status_pass,
            "protocol_id": PROTOCOL_ID,
            "outcome": outcome,
            "control_realization": CONTROL_REALIZATION,
            "paired_porosity": CONTROL_POROSITY,
            "parent_day": PARENT_DAY,
            "parent_total_mass_kg": parent_total,
            "CV_projected_mass_kg": cv_total_mass,
            "residual_grid_mass_kg": residual_total_mass,
            "residual_fraction_of_parent_mass": (
                residual_total_mass / max(parent_total, 1.0e-300)
            ),
            "H1_residual_mass_kg": h1_residual_mass,
            "outside_D1_residual_mass_kg": outside_d1_residual_mass,
            "transport_CV_mass_shape": list(cv_mass.shape),
            "transport_CV_saturation_shape": list(cv_sat.shape),
            "residual_grid_shape": list(residual_grid.shape),
            "split_state_required": split_state_required,
            "CV_complete": not split_state_required,
            "maximum_CV_capacity_excess_kg": max_excess,
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
                "residual_grid_component_mass_kg": residual_grid,
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
                "subsegment_pore_volume_m3": pv_sub,
                "parent_total_mass_kg": np.asarray(parent_total),
                "CV_projected_mass_kg": np.asarray(cv_total_mass),
                "residual_grid_mass_kg": np.asarray(residual_total_mass),
                "parent_day": np.asarray(PARENT_DAY),
            }
        )

        output_files = {
            "PAD_Stream_POSTV16_AV4_F2_Summary.json":
                json_bytes(summary),
            "POSTV16_AV4_F2_Parent_Restart_State.npz":
                state_npz,
            "POSTV16_AV4_F2_Domain_Mass_Audit.csv":
                csv_bytes(mass_rows),
            "POSTV16_AV4_F2_Projection_Closure_Audit.json":
                json_bytes(projection_audit),
            "POSTV16_AV4_F2_CV_Capacity_and_Inversion_Audit.json":
                json_bytes(capacity_audit),
            "POSTV16_AV4_F2_F3_Handoff_Contract.json":
                json_bytes(handoff),
            "POSTV16_AV4_F2_Decision_Contract.json":
                json_bytes(decision),
            "POSTV16_AV4_F2_Final_Gate_Matrix.csv":
                csv_bytes(
                    [{"gate": name, **value} for name, value in gates.items()]
                ),
        }

        immutable_publish(out, output_files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV4_F2_Artifact_Manifest.csv":
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
                "POSTV16_AV4_F2_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print()
        print("=" * 214)
        print(f"{MILESTONE}: {outcome}")
        print("=" * 214)
        print("Parent total mass kg                    :", parent_total)
        print("Projected CV mass kg                    :", cv_total_mass)
        print("Residual grid mass kg                   :", residual_total_mass)
        print("Residual fraction                       :", residual_total_mass / max(parent_total, 1.0e-300))
        print("H1 residual mass kg                     :", h1_residual_mass)
        print("Outside-D1 residual mass kg             :", outside_d1_residual_mass)
        print("Global split-state ledger residual kg   :", ledger_residual)
        print("Maximum CV capacity excess kg           :", max_excess)
        print("Parent CV saturation min / max          :", float(np.min(cv_sat)), "/", float(np.max(cv_sat)))
        print("Split state required                    :", split_state_required)
        print("Teacher / checkpoint inference          : False / False")
        print("Physical time advance                   : False")
        print("POSTV16-AV4-F3                          : AUTHORIZED (protocol freeze only)")
        print("Teacher execution / A3-E2 / dynamic AV4: NOT AUTHORIZED")
        print("=" * 214)

        return 0

    except ScientificFail as exc:
        if exc.gate != "projected_CV_component_mass_within_frozen_E37A_capacity":
            raise
        failed.mkdir(parents=True, exist_ok=True)

        report = {
            "milestone": MILESTONE,
            "status": STATUS_FAIL_CAPACITY,
            "failed_stage": stage,
            "failed_gate": exc.gate,
            "detail": exc.detail,
            "gates": gates,
            "scientific_execution_started": scientific_execution_started,
            "projection_executed": projection_executed,
            "CV_mass_inversion_executed": cv_inversion_executed,
            "teacher_transport_performed": False,
            "checkpoint_model_loaded": False,
            "checkpoint_inference_performed": False,
            "physical_time_advanced": False,
            "future_state_prediction_performed": False,
            "future_mapback_performed": False,
            "training_performed": False,
            "support_domain_adaptation_performed": False,
            "F3_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
            "automatic_rerun_authorized": False,
        }

        data = json_bytes(report)
        p = failed / "POSTV16_AV4_F2_Scientific_Fail_Report.json"
        if p.exists() and p.read_bytes() != data:
            suffix = hashlib.sha256(data).hexdigest()[:12]
            p = failed / f"POSTV16_AV4_F2_Scientific_Fail_Report_{suffix}.json"
        if not p.exists():
            p.write_bytes(data)

        print()
        print("=" * 214)
        print(f"{MILESTONE}: SCIENTIFIC FAIL — CV CAPACITY")
        print("=" * 214)
        print("Stage      :", stage)
        print("Failed gate:", exc.gate)
        print("Detail     :", exc.detail)
        print("Projection executed                    :", projection_executed)
        print("CV mass inversion executed             :", cv_inversion_executed)
        print("Support-domain adaptation              : False")
        print("F3 / A3-E2 / dynamic transport         : NOT AUTHORIZED")
        print("NO AUTOMATIC RERUN AUTHORIZED.")
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
            "scientific_execution_started": scientific_execution_started,
            "projection_executed": projection_executed,
            "CV_mass_inversion_executed": cv_inversion_executed,
            "teacher_transport_performed": False,
            "checkpoint_model_loaded": False,
            "checkpoint_inference_performed": False,
            "physical_time_advanced": False,
            "future_state_prediction_performed": False,
            "future_mapback_performed": False,
            "training_performed": False,
            "support_domain_adaptation_performed": False,
            "F3_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
            "automatic_rerun_authorized": False,
        }

        data = json_bytes(report)
        p = blocked / "POSTV16_AV4_F2_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            suffix = hashlib.sha256(data).hexdigest()[:12]
            p = blocked / f"POSTV16_AV4_F2_Blocked_Report_{suffix}.json"
        if not p.exists():
            p.write_bytes(data)

        print()
        print("=" * 214)
        print(f"{MILESTONE}: TECHNICAL / AUTHORITY BLOCK")
        print("=" * 214)
        print("Stage    :", stage)
        print("Exception:", repr(exc))
        print("Projection executed            :", projection_executed)
        print("CV mass inversion executed     :", cv_inversion_executed)
        print("F3 / A3-E2 / dynamic transport : NOT AUTHORIZED")
        print("NO AUTOMATIC RERUN AUTHORIZED.")
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
